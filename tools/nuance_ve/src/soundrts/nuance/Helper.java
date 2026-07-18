package soundrts.nuance;

import com.sun.jna.Memory;
import com.sun.jna.Native;
import com.sun.jna.Pointer;
import com.sun.jna.StringArray;
import com.sun.jna.WString;
import com.sun.jna.ptr.ShortByReference;
import java.io.BufferedReader;
import java.io.File;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import javax.sound.sampled.AudioFormat;
import javax.sound.sampled.AudioSystem;
import javax.sound.sampled.DataLine;
import javax.sound.sampled.Mixer;
import javax.sound.sampled.SourceDataLine;

/**
 * 32-bit helper process for Nuance Vocalizer Expressive (MW Apple voices).
 *
 * Stdin: one JSON command per line (minimal parser, no external deps).
 * Stdout: one JSON response per line.
 *
 * Commands:
 *   {"cmd":"init","vl":"E:/rj/yx/mw/vl"}
 *   {"cmd":"list"}
 *   {"cmd":"speak","voice":"Ting-Ting","text":"...","rate":80,"volume":80,"pitch":50}
 *   {"cmd":"stop"}
 *   {"cmd":"quit"}
 */
public final class Helper {
    private static final short VE_INSTALL_FMT = 1312;
    private static final short PLATFORM_FMT = 512;
    private static final int MSG_DONE = 2;
    private static final int MSG_BUFREQ = 8;
    private static final int MSG_BUFDONE = 16;
    private static final int MSG_STOP = 64;
    private static final int MSG_RESUME = 128;
    private static final int STOP_BUSY = 0x80000807; // approx; MW returns -2147481593

    private final Memory pcmScratch = new Memory(8192);
    private final VeApi.Marker markerProto = new VeApi.Marker();
    private final VeApi.Marker[] markers = (VeApi.Marker[]) markerProto.toArray(100);

    private VeApi.PlatformLib platform;
    private VeApi.VeLib ve;
    private VeApi.VeInstall.ByRef install;
    private VeApi.Handle.ByRef classHandle;
    private final Map<String, VeApi.Handle.ByVal> speechByVoice = new HashMap<String, VeApi.Handle.ByVal>();
    private volatile VeApi.Handle.ByVal currentSpeech;
    private volatile boolean pauseGate;
    private SourceDataLine line;
    private String currentDevice = "default";
    private final AudioFormat pcmFmt =
            new AudioFormat(AudioFormat.Encoding.PCM_SIGNED, 22050f, 16, 2, 4, 22050f, false);
    private float gainL = 1.0f;
    private float gainR = 1.0f;
    private String vlPath;
    private boolean ready;

    private volatile boolean speaking;
    private Thread speakThread;
    private final Object speakLock = new Object();

    private final VeApi.OutCallback callback =
            new VeApi.OutCallback() {
                @Override
                public int callback(
                        VeApi.Handle.ByVal hSpeech,
                        Pointer userData,
                        VeApi.Msg.ByRef msg,
                        Pointer reserved) {
                    try {
                        int code = msg.eMessage;
                        if (currentSpeech == null && code != MSG_DONE) {
                            return STOP_BUSY;
                        }
                        VeApi.PcmBuf.ByRef pcm = msg.pParam;
                        if (code == MSG_BUFREQ) {
                            pcm.pOutPcmBuf = pcmScratch;
                            pcm.ulPcmBufLen = 8192;
                            pcm.pMrkList = markers[0].getPointer();
                            pcm.ulMrkListLen = 4000;
                            return 0;
                        }
                        if (code == MSG_BUFDONE) {
                            if (pcm.ulPcmBufLen > 0 && line != null) {
                                short[] samples = pcm.pOutPcmBuf.getShortArray(0, pcm.ulPcmBufLen / 2);
                                byte[] stereo = new byte[samples.length * 4];
                                for (int i = 0; i < samples.length; i++) {
                                    short l = (short) (samples[i] * gainL);
                                    short r = (short) (samples[i] * gainR);
                                    stereo[i * 4] = (byte) (l & 0xff);
                                    stereo[i * 4 + 1] = (byte) ((l >> 8) & 0xff);
                                    stereo[i * 4 + 2] = (byte) (r & 0xff);
                                    stereo[i * 4 + 3] = (byte) ((r >> 8) & 0xff);
                                }
                                line.write(stereo, 0, stereo.length);
                            }
                            if (pauseGate) {
                                line.stop();
                                while (pauseGate) {
                                    try {
                                        Thread.sleep(1);
                                    } catch (InterruptedException ignored) {
                                    }
                                }
                            }
                            return 0;
                        }
                        if (code == MSG_STOP) {
                            pauseGate = true;
                            return 0;
                        }
                        if (code == MSG_RESUME) {
                            if (line != null) {
                                line.start();
                            }
                            pauseGate = false;
                            return 0;
                        }
                        if (code == MSG_DONE) {
                            if (line != null) {
                                try {
                                    line.drain();
                                } catch (Exception ignored) {
                                }
                                line.stop();
                                line.flush();
                            }
                            currentSpeech = null;
                            return 0;
                        }
                    } catch (Exception ignored) {
                    }
                    return 0;
                }
            };

    public static void main(String[] args) throws Exception {
        Helper helper = new Helper();
        BufferedReader in =
                new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8));
        String line;
        while ((line = in.readLine()) != null) {
            line = line.trim();
            if (line.isEmpty()) {
                continue;
            }
            try {
                Map<String, String> cmd = parseJson(line);
                String name = str(cmd, "cmd", "");
                if ("init".equals(name)) {
                    helper.init(str(cmd, "vl", ""));
                    emitOk("init", null);
                } else if ("list".equals(name)) {
                    List<String> voices = helper.listVoices();
                    emitOk("list", voices);
                } else if ("list_devices".equals(name)) {
                    emitOkDevices("list_devices", helper.listDevices());
                } else if ("set_device".equals(name)) {
                    helper.setDevice(str(cmd, "device", "default"));
                    emitOk("set_device", null);
                } else if ("speak".equals(name)) {
                    // Start synthesis on a worker thread so stdin can still
                    // receive stop/quit (otherwise menu browse queues forever).
                    helper.startSpeak(
                            str(cmd, "voice", "Ting-Ting"),
                            str(cmd, "text", ""),
                            intval(cmd, "rate", 80),
                            intval(cmd, "volume", 80),
                            intval(cmd, "pitch", 50));
                    emitOk("speak", null);
                } else if ("stop".equals(name)) {
                    helper.stop();
                    emitOk("stop", null);
                } else if ("busy".equals(name)) {
                    System.out.println(
                            "{\"ok\":true,\"cmd\":\"busy\",\"busy\":"
                                    + (helper.isSpeaking() ? "true" : "false")
                                    + "}");
                    System.out.flush();
                } else if ("quit".equals(name)) {
                    helper.shutdown();
                    emitOk("quit", null);
                    break;
                } else {
                    emitErr("unknown cmd: " + name);
                }
            } catch (Exception e) {
                emitErr(e.getMessage() == null ? e.toString() : e.getMessage());
            }
        }
    }

    private synchronized void init(String vl) throws Exception {
        if (ready) {
            return;
        }
        File dir = new File(vl).getAbsoluteFile();
        if (!dir.isDirectory()) {
            throw new Exception("vl path not found: " + dir);
        }
        File veDll = new File(dir, "ve.dll");
        File platDll = new File(dir, "nuan_platform.dll");
        if (!veDll.isFile() || !platDll.isFile()) {
            throw new Exception("ve.dll / nuan_platform.dll missing under " + dir);
        }
        this.vlPath = dir.getAbsolutePath();

        // Data install root is the vl folder itself (contains mnc/cah/mnt).
        platform = (VeApi.PlatformLib) Native.loadLibrary(platDll.getAbsolutePath(), VeApi.PlatformLib.class);
        ve = (VeApi.VeLib) Native.loadLibrary(veDll.getAbsolutePath(), VeApi.VeLib.class);

        install = new VeApi.VeInstall.ByRef();
        install.fmtVersion = VE_INSTALL_FMT;
        install.pBinBrokerInfo = null;

        VeApi.PlatformInstall.ByRef plat = new VeApi.PlatformInstall.ByRef();
        plat.fmtVersion = PLATFORM_FMT;
        plat.licenseToken = null;
        plat.u16NbrOfDataInstall = 1;
        plat.apDataInstall = new StringArray(new String[] {vlPath}, true);
        plat.pDatPtr_Table = null;
        plat.stHeap = new VeApi.HeapBlock.ByVal();

        int rc = platform.vplatform_GetInterfaces(install, plat);
        if (rc != 0) {
            throw new Exception("vplatform_GetInterfaces 0x" + Integer.toHexString(rc));
        }
        classHandle = new VeApi.Handle.ByRef();
        rc = ve.ve_ttsInitialize(install, classHandle);
        if (rc != 0) {
            throw new Exception("ve_ttsInitialize 0x" + Integer.toHexString(rc));
        }

        AudioFormat fmt = pcmFmt;
        openLine(fmt, "default");
        ready = true;
    }

    private synchronized List<String> listDevices() {
        List<String> out = new ArrayList<String>();
        out.add("default");
        Mixer.Info[] mixers = AudioSystem.getMixerInfo();
        for (int i = 0; i < mixers.length; i++) {
            Mixer mixer = AudioSystem.getMixer(mixers[i]);
            DataLine.Info info = new DataLine.Info(SourceDataLine.class, pcmFmt);
            if (!mixer.isLineSupported(info)) {
                continue;
            }
            String name = mixers[i].getName();
            if (name != null && name.length() > 0 && !out.contains(name)) {
                out.add(name);
            }
        }
        return out;
    }

    private synchronized void setDevice(String device) throws Exception {
        ensureReady();
        String name = device == null || device.length() == 0 ? "default" : device;
        if (name.equals(currentDevice) && line != null && line.isOpen()) {
            return;
        }
        openLine(pcmFmt, name);
    }

    private void openLine(AudioFormat fmt, String device) throws Exception {
        if (line != null) {
            try {
                line.stop();
                line.flush();
                line.close();
            } catch (Exception ignored) {
            }
            line = null;
        }
        DataLine.Info info = new DataLine.Info(SourceDataLine.class, fmt);
        if (device == null || device.length() == 0 || "default".equals(device)) {
            line = (SourceDataLine) AudioSystem.getLine(info);
            currentDevice = "default";
        } else {
            Mixer.Info[] mixers = AudioSystem.getMixerInfo();
            Mixer.Info match = null;
            for (int i = 0; i < mixers.length; i++) {
                if (device.equals(mixers[i].getName())) {
                    match = mixers[i];
                    break;
                }
            }
            if (match == null) {
                for (int i = 0; i < mixers.length; i++) {
                    String n = mixers[i].getName();
                    if (n != null && n.indexOf(device) >= 0) {
                        match = mixers[i];
                        break;
                    }
                }
            }
            if (match == null) {
                line = (SourceDataLine) AudioSystem.getLine(info);
                currentDevice = "default";
            } else {
                Mixer mixer = AudioSystem.getMixer(match);
                line = (SourceDataLine) mixer.getLine(info);
                currentDevice = match.getName();
            }
        }
        line.open(fmt, 16384);
    }

    private synchronized List<String> listVoices() throws Exception {
        ensureReady();
        List<String> out = new ArrayList<String>();
        VeApi.Handle.ByVal h = copyHandle(classHandle);
        ShortByReference count = new ShortByReference();
        int rc = ve.ve_ttsGetLanguageList(h, null, count);
        if (rc != 0) {
            throw new Exception("getLanguageList1 0x" + Integer.toHexString(rc));
        }
        VeApi.Language[] langs = (VeApi.Language[]) new VeApi.Language().toArray(count.getValue());
        rc = ve.ve_ttsGetLanguageList(h, langs, count);
        if (rc != 0) {
            throw new Exception("getLanguageList2 0x" + Integer.toHexString(rc));
        }
        for (int i = 0; i < langs.length; i++) {
            String lang = VeApi.cString(langs[i].szLanguage);
            rc = ve.ve_ttsGetVoiceList(h, lang, 0, null, count);
            if (rc != 0) {
                throw new Exception("getVoiceList1 0x" + Integer.toHexString(rc));
            }
            VeApi.Voice[] voices = (VeApi.Voice[]) new VeApi.Voice().toArray(count.getValue());
            rc = ve.ve_ttsGetVoiceList(h, lang, 0, voices, count);
            if (rc != 0) {
                throw new Exception("getVoiceList2 0x" + Integer.toHexString(rc));
            }
            for (int j = 0; j < count.getValue(); j++) {
                out.add(VeApi.cString(voices[j].szVoiceName));
            }
        }
        return out;
    }

    private void startSpeak(
            final String voice, final String text, final int rate, final int volume, final int pitch)
            throws Exception {
        ensureReady();
        if (text == null || text.isEmpty()) {
            return;
        }
        stop();
        speaking = true;
        speakThread =
                new Thread(
                        new Runnable() {
                            @Override
                            public void run() {
                                try {
                                    speakBlocking(voice, text, rate, volume, pitch);
                                } catch (Exception e) {
                                    emitErr(e.getMessage() == null ? e.toString() : e.getMessage());
                                } finally {
                                    speaking = false;
                                    System.out.println("{\"ok\":true,\"cmd\":\"speak_done\"}");
                                    System.out.flush();
                                }
                            }
                        },
                        "nuance-speak");
        speakThread.setDaemon(true);
        speakThread.start();
    }

    private void speakBlocking(String voice, String text, int rate, int volume, int pitch)
            throws Exception {
        VeApi.Handle.ByVal speech;
        synchronized (speakLock) {
            speech = speechByVoice.get(voice);
            if (speech == null) {
                speech = openVoice(voice);
                speechByVoice.put(voice, speech);
            }
            setNumericParams(speech, rate, volume, pitch);
            currentSpeech = speech;
            gainL = 1.0f;
            gainR = 1.0f;
            pauseGate = false;
            line.start();
        }

        String cleaned = text.replace("\u001b", "");
        VeApi.TextIn.ByRef tin = new VeApi.TextIn.ByRef();
        tin.eTextFormat = 0;
        tin.szInText = new WString(cleaned);
        tin.ulTextLength = cleaned.length() * 2;
        int rc = ve.ve_ttsProcessText2Speech(speech, tin);
        synchronized (speakLock) {
            if (currentSpeech == speech) {
                currentSpeech = null;
            }
        }
        if (rc != 0) {
            throw new Exception("ProcessText2Speech 0x" + Integer.toHexString(rc));
        }
    }

    boolean isSpeaking() {
        return speaking;
    }

    private VeApi.Handle.ByVal openVoice(String voice) throws Exception {
        VeApi.Handle.ByRef out = new VeApi.Handle.ByRef();
        VeApi.Handle.ByVal cls = copyHandle(classHandle);
        int rc = ve.ve_ttsOpen(cls, install.hHeap, install.hLog, out, null);
        if (rc != 0) {
            throw new Exception("ve_ttsOpen 0x" + Integer.toHexString(rc));
        }
        VeApi.Handle.ByVal speech = copyHandle(out);
        // Defaults from MW: voice name + marker/audio options
        int[][] base =
                new int[][] {
                    {12, 1},
                    {13, 12},
                    {5, 1},
                    {14, 1},
                    {11, 1}
                };
        setParams(speech, voice, base);
        VeApi.OutDevice.ByRef device = new VeApi.OutDevice.ByRef();
        device.hOutDevInstance = null;
        device.pfOutNotify = callback;
        rc = ve.ve_ttsSetOutDevice(speech, device);
        if (rc != 0) {
            throw new Exception("ve_ttsSetOutDevice 0x" + Integer.toHexString(rc));
        }
        return speech;
    }

    private void setNumericParams(VeApi.Handle.ByVal speech, int rate, int volume, int pitch)
            throws Exception {
        // MW / VE: ID 2 = volume, ID 3 = speech rate, ID 4 = pitch.
        // UI 100 ≈ old UI 50 (engine ~100); previous high half went to 400 and was too loud.
        int volMapped = 50 + volume / 2;
        int pitchMapped = pitch <= 50 ? pitch + 50 : ((pitch - 50) << 1) + 100;
        // Faster than old *2 curve; UI 100 → 400. Cap avoids *7→415 silence.
        int rateMapped = rate <= 50 ? rate + 50 : (rate - 50) * 6 + 100;
        if (rateMapped > 400) {
            rateMapped = 400;
        }
        int[][] nums = new int[][] {{2, volMapped}, {3, rateMapped}, {4, pitchMapped}};
        setParams(speech, null, nums);
    }

    private void setParams(VeApi.Handle.ByVal speech, String voiceName, int[][] nums) throws Exception {
        int extra = (voiceName != null && voiceName.length() > 0) ? 1 : 0;
        VeApi.Param[] params = (VeApi.Param[]) new VeApi.Param().toArray(nums.length + extra);
        int i = 0;
        if (extra == 1) {
            params[0].ID = 8;
            byte[] raw = voiceName.getBytes("UTF-8");
            System.arraycopy(raw, 0, params[0].uValue, 0, Math.min(raw.length, 127));
            i = 1;
        }
        for (int n = 0; n < nums.length; n++) {
            params[i].ID = nums[n][0];
            int val = nums[n][1];
            params[i].uValue[0] = (byte) (val % 256);
            params[i].uValue[1] = (byte) (val / 256);
            i++;
        }
        int rc = ve.ve_ttsSetParamList(speech, params, (short) params.length);
        if (rc != 0) {
            throw new Exception("ve_ttsSetParamList 0x" + Integer.toHexString(rc));
        }
    }

    private void stop() {
        VeApi.Handle.ByVal cur;
        synchronized (speakLock) {
            cur = currentSpeech;
            speaking = false;
        }
        if (cur != null && ve != null) {
            try {
                ve.ve_ttsStop(cur);
            } catch (Exception ignored) {
            }
        }
        if (line != null) {
            try {
                line.stop();
                line.flush();
            } catch (Exception ignored) {
            }
        }
        pauseGate = false;
        synchronized (speakLock) {
            currentSpeech = null;
        }
    }

    private synchronized void shutdown() {
        stop();
        Thread t = speakThread;
        if (t != null) {
            try {
                t.join(2000);
            } catch (InterruptedException ignored) {
            }
        }
        for (VeApi.Handle.ByVal h : speechByVoice.values()) {
            try {
                ve.ve_ttsClose(h);
            } catch (Exception ignored) {
            }
        }
        speechByVoice.clear();
        if (classHandle != null && ve != null) {
            try {
                ve.ve_ttsUnInitialize(copyHandle(classHandle));
            } catch (Exception ignored) {
            }
        }
        if (install != null && platform != null) {
            try {
                platform.vplatform_ReleaseInterfaces(install);
            } catch (Exception ignored) {
            }
        }
        if (line != null) {
            try {
                line.close();
            } catch (Exception ignored) {
            }
        }
        ready = false;
    }

    private void ensureReady() throws Exception {
        if (!ready) {
            throw new Exception("not initialized; send init first");
        }
    }

    private static VeApi.Handle.ByVal copyHandle(VeApi.Handle src) {
        VeApi.Handle.ByVal h = new VeApi.Handle.ByVal();
        h.pHandleData = src.pHandleData;
        h.u32Check = src.u32Check;
        return h;
    }

    private static void emitOk(String cmd, List<String> voices) {
        StringBuilder sb = new StringBuilder();
        sb.append("{\"ok\":true,\"cmd\":\"").append(esc(cmd)).append("\"");
        if (voices != null) {
            sb.append(",\"voices\":[");
            for (int i = 0; i < voices.size(); i++) {
                if (i > 0) {
                    sb.append(',');
                }
                sb.append('"').append(esc(voices.get(i))).append('"');
            }
            sb.append(']');
        }
        sb.append('}');
        System.out.println(sb.toString());
        System.out.flush();
    }

    private static void emitOkDevices(String cmd, List<String> devices) {
        StringBuilder sb = new StringBuilder();
        sb.append("{\"ok\":true,\"cmd\":\"").append(esc(cmd)).append("\"");
        if (devices != null) {
            sb.append(",\"devices\":[");
            for (int i = 0; i < devices.size(); i++) {
                if (i > 0) {
                    sb.append(',');
                }
                sb.append('"').append(esc(devices.get(i))).append('"');
            }
            sb.append(']');
        }
        sb.append('}');
        System.out.println(sb.toString());
        System.out.flush();
    }

    private static void emitErr(String msg) {
        System.out.println("{\"ok\":false,\"error\":\"" + esc(msg == null ? "" : msg) + "\"}");
        System.out.flush();
    }

    private static String esc(String s) {
        return s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "");
    }

    private static Map<String, String> parseJson(String line) {
        // Minimal {"k":"v",...} parser for our command dialect.
        Map<String, String> map = new HashMap<String, String>();
        String body = line.trim();
        if (body.startsWith("{")) {
            body = body.substring(1);
        }
        if (body.endsWith("}")) {
            body = body.substring(0, body.length() - 1);
        }
        int i = 0;
        while (i < body.length()) {
            while (i < body.length() && (body.charAt(i) == ',' || Character.isWhitespace(body.charAt(i)))) {
                i++;
            }
            if (i >= body.length()) {
                break;
            }
            if (body.charAt(i) != '"') {
                break;
            }
            i++;
            int k0 = i;
            while (i < body.length() && body.charAt(i) != '"') {
                i++;
            }
            String key = body.substring(k0, i);
            i++;
            while (i < body.length() && body.charAt(i) != ':') {
                i++;
            }
            i++;
            while (i < body.length() && Character.isWhitespace(body.charAt(i))) {
                i++;
            }
            String val;
            if (i < body.length() && body.charAt(i) == '"') {
                i++;
                StringBuilder vb = new StringBuilder();
                while (i < body.length()) {
                    char c = body.charAt(i++);
                    if (c == '\\' && i < body.length()) {
                        char n = body.charAt(i++);
                        if (n == 'n') {
                            vb.append('\n');
                        } else if (n == 'r') {
                            vb.append('\r');
                        } else if (n == 't') {
                            vb.append('\t');
                        } else {
                            vb.append(n);
                        }
                    } else if (c == '"') {
                        break;
                    } else {
                        vb.append(c);
                    }
                }
                val = vb.toString();
            } else {
                int v0 = i;
                while (i < body.length() && body.charAt(i) != ',') {
                    i++;
                }
                val = body.substring(v0, i).trim();
            }
            map.put(key, val);
        }
        return map;
    }

    private static String str(Map<String, String> m, String k, String d) {
        String v = m.get(k);
        return v == null ? d : v;
    }

    private static int intval(Map<String, String> m, String k, int d) {
        try {
            return Integer.parseInt(str(m, k, Integer.toString(d)));
        } catch (Exception e) {
            return d;
        }
    }
}
