package soundrts.nuance;

import com.sun.jna.Callback;
import com.sun.jna.Library;
import com.sun.jna.Pointer;
import com.sun.jna.Structure;
import com.sun.jna.WString;
import com.sun.jna.ptr.ShortByReference;
import java.util.Arrays;
import java.util.List;

/** Nuance Vocalizer Expressive (ve.dll / nuan_platform.dll) JNA bindings. */
public final class VeApi {
    private VeApi() {}

    public interface PlatformLib extends Library {
        int vplatform_GetInterfaces(VeInstall.ByRef install, PlatformInstall.ByRef platform);
        int vplatform_ReleaseInterfaces(VeInstall.ByRef install);
    }

    public interface VeLib extends Library {
        int ve_ttsInitialize(VeInstall.ByRef install, Handle.ByRef outClass);
        int ve_ttsUnInitialize(Handle.ByVal hClass);
        int ve_ttsOpen(Handle.ByVal hClass, Pointer hHeap, Pointer hLog, Handle.ByRef outSpeech, Pointer reserved);
        int ve_ttsClose(Handle.ByVal hSpeech);
        int ve_ttsProcessText2Speech(Handle.ByVal hSpeech, TextIn.ByRef text);
        int ve_ttsStop(Handle.ByVal hSpeech);
        int ve_ttsPause(Handle.ByVal hSpeech);
        int ve_ttsResume(Handle.ByVal hSpeech);
        int ve_ttsSetParamList(Handle.ByVal hSpeech, Param[] params, short count);
        int ve_ttsGetParamList(Handle.ByVal hSpeech, Param[] params, short count);
        int ve_ttsGetLanguageList(Handle.ByVal hClass, Language[] list, ShortByReference count);
        int ve_ttsGetVoiceList(Handle.ByVal hClass, String language, int flags, Voice[] list, ShortByReference count);
        int ve_ttsSetOutDevice(Handle.ByVal hSpeech, OutDevice.ByRef device);
    }

    public static class Handle extends Structure {
        public Pointer pHandleData;
        public int u32Check;

        public static class ByRef extends Handle implements Structure.ByReference {}
        public static class ByVal extends Handle implements Structure.ByValue {}

        @Override
        protected List<String> getFieldOrder() {
            return Arrays.asList("pHandleData", "u32Check");
        }
    }

    public static class HeapBlock extends Structure {
        public Pointer start;
        public int cByte;
        public int cFlags;

        public static class ByVal extends HeapBlock implements Structure.ByValue {}

        @Override
        protected List<String> getFieldOrder() {
            return Arrays.asList("start", "cByte", "cFlags");
        }
    }

    public static class VeInstall extends Structure {
        public short fmtVersion;
        public String pBinBrokerInfo;
        public Pointer pIHeap;
        public Pointer hHeap;
        public Pointer pICritSec;
        public Pointer hCSClass;
        public Pointer pIDataStream;
        public Pointer pIDataMapping;
        public Pointer hDataClass;
        public Pointer pILog;
        public Pointer hLog;

        public static class ByRef extends VeInstall implements Structure.ByReference {}

        @Override
        protected List<String> getFieldOrder() {
            return Arrays.asList(
                    "fmtVersion",
                    "pBinBrokerInfo",
                    "pIHeap",
                    "hHeap",
                    "pICritSec",
                    "hCSClass",
                    "pIDataStream",
                    "pIDataMapping",
                    "hDataClass",
                    "pILog",
                    "hLog");
        }
    }

    public static class PlatformInstall extends Structure {
        public short fmtVersion;
        public short u16NbrOfDataInstall;
        public Pointer apDataInstall;
        public HeapBlock.ByVal stHeap;
        public Pointer pDatPtr_Table;
        public String licenseToken;
        public int licenseTokenLen;
        public int licensor;
        public String sessionKey;
        public int sessionKeyLen;
        public WString szBinaryBroker;
        public WString szFileListFile;
        public int rfu1;
        public int rfu2;

        public static class ByRef extends PlatformInstall implements Structure.ByReference {}

        @Override
        protected List<String> getFieldOrder() {
            return Arrays.asList(
                    "fmtVersion",
                    "u16NbrOfDataInstall",
                    "apDataInstall",
                    "stHeap",
                    "pDatPtr_Table",
                    "licenseToken",
                    "licenseTokenLen",
                    "licensor",
                    "sessionKey",
                    "sessionKeyLen",
                    "szBinaryBroker",
                    "szFileListFile",
                    "rfu1",
                    "rfu2");
        }
    }

    public static class Language extends Structure {
        public byte[] szLanguage = new byte[128];
        public byte[] szLanguageTLW = new byte[4];
        public byte[] szVersion = new byte[128];
        public short u16LangId;

        @Override
        protected List<String> getFieldOrder() {
            return Arrays.asList("szLanguage", "szLanguageTLW", "szVersion", "u16LangId");
        }
    }

    public static class Voice extends Structure {
        public byte[] szVersion = new byte[128];
        public byte[] szLanguage = new byte[128];
        public byte[] szVoiceName = new byte[128];
        public byte[] szVoiceAge = new byte[128];
        public byte[] szVoiceType = new byte[128];
        public short u16LangId;

        @Override
        protected List<String> getFieldOrder() {
            return Arrays.asList(
                    "szVersion", "szLanguage", "szVoiceName", "szVoiceAge", "szVoiceType", "u16LangId");
        }
    }

    public static class Param extends Structure {
        public int ID;
        public byte[] uValue = new byte[128];

        @Override
        protected List<String> getFieldOrder() {
            return Arrays.asList("ID", "uValue");
        }
    }

    public static class TextIn extends Structure {
        public int eTextFormat;
        public int ulTextLength;
        public WString szInText;

        public static class ByRef extends TextIn implements Structure.ByReference {}

        @Override
        protected List<String> getFieldOrder() {
            return Arrays.asList("eTextFormat", "ulTextLength", "szInText");
        }
    }

    public interface OutCallback extends Callback {
        int callback(Handle.ByVal hSpeech, Pointer userData, Msg.ByRef msg, Pointer reserved);
    }

    public static class OutDevice extends Structure {
        public Pointer hOutDevInstance;
        public OutCallback pfOutNotify;

        public static class ByRef extends OutDevice implements Structure.ByReference {}

        @Override
        protected List<String> getFieldOrder() {
            return Arrays.asList("hOutDevInstance", "pfOutNotify");
        }
    }

    public static class PcmBuf extends Structure {
        public int eAudioFormat;
        public int ulPcmBufLen;
        public Pointer pOutPcmBuf;
        public int ulMrkListLen;
        public Pointer pMrkList;

        public static class ByRef extends PcmBuf implements Structure.ByReference {}

        @Override
        protected List<String> getFieldOrder() {
            return Arrays.asList("eAudioFormat", "ulPcmBufLen", "pOutPcmBuf", "ulMrkListLen", "pMrkList");
        }
    }

    public static class Msg extends Structure {
        public int eMessage;
        public int uParam;
        public PcmBuf.ByRef pParam;

        public static class ByRef extends Msg implements Structure.ByReference {}

        @Override
        protected List<String> getFieldOrder() {
            return Arrays.asList("eMessage", "uParam", "pParam");
        }
    }

    public static class Marker extends Structure {
        public int ulMrkInfo;
        public int eMrkType;
        public int ulSrcPos;
        public int ulSrcTextLen;
        public int ulDestPos;
        public int ulDestLen;
        public short usPhoneme;
        public int ulMrkId;
        public int ulParam;
        public String szPromptID;

        @Override
        protected List<String> getFieldOrder() {
            return Arrays.asList(
                    "ulMrkInfo",
                    "eMrkType",
                    "ulSrcPos",
                    "ulSrcTextLen",
                    "ulDestPos",
                    "ulDestLen",
                    "usPhoneme",
                    "ulMrkId",
                    "ulParam",
                    "szPromptID");
        }
    }

    public static String cString(byte[] bytes) {
        int n = 0;
        while (n < bytes.length && bytes[n] != 0) {
            n++;
        }
        try {
            return new String(bytes, 0, n, "UTF-8");
        } catch (Exception e) {
            return new String(bytes, 0, n);
        }
    }
}
