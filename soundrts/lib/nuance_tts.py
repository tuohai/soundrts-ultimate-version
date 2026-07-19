"""Nuance Vocalizer Expressive (Apple voices) via 32-bit Java helper.

Voice data and a 32-bit JRE live under ``user/voices/nuance/`` (imported once
from Mist World). Runtime no longer needs to point at the MW install.

``ve.dll`` is 32-bit, so 64-bit Python talks to a small Java helper over JSON.
Helper jars live in ``tools/nuance_ve`` (dev / next to the packed exe) and may
also be copied under ``user/voices/nuance/helper`` after import.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import time
from typing import List, Optional, Tuple

from .log import exception, warning

PREFIX = "nuance:"

_proc: Optional[subprocess.Popen] = None
_lock = threading.Lock()
_io_lock = threading.Lock()
_ready = False
_vl_path = ""
_speaking = False
_speak_end = 0.0
_voices_cache: List[str] = []
_pending: dict = {}
_reader_started = False
_speak_gen = 0


def is_nuance_voice(name: str) -> bool:
    return (name or "").strip().lower().startswith(PREFIX)


def nuance_voice_name(name: str) -> str:
    s = (name or "").strip()
    if s.lower().startswith(PREFIX):
        return s[len(PREFIX) :].strip()
    return s


def display_name(voice: str) -> str:
    return f"Nuance {voice}"


def voice_id(voice: str) -> str:
    return PREFIX + voice


def local_nuance_root() -> str:
    """``user/voices/nuance`` — SoundRTS-owned Apple voice pack."""
    try:
        from ..paths import NUANCE_VOICE_PATH

        return NUANCE_VOICE_PATH
    except Exception:
        return os.path.join("user", "voices", "nuance")


def local_vl_path() -> str:
    return os.path.join(local_nuance_root(), "vl")


def local_java_path() -> str:
    """Prefer windowless ``javaw.exe`` when the JRE ships it."""
    bin_dir = os.path.join(local_nuance_root(), "jre", "bin")
    return _prefer_javaw(os.path.join(bin_dir, "java.exe"))


def _prefer_javaw(java_exe: str) -> str:
    """Use ``javaw.exe`` (no console) when present next to ``java.exe``."""
    if not java_exe:
        return java_exe
    base = os.path.basename(java_exe).lower()
    if base == "java.exe":
        javaw = os.path.join(os.path.dirname(java_exe), "javaw.exe")
        if os.path.isfile(javaw):
            return javaw
    return java_exe


def local_helper_dir() -> str:
    """Jars shipped with / copied next to the local Apple voice pack."""
    return os.path.join(local_nuance_root(), "helper")


def local_pack_installed() -> bool:
    return os.path.isfile(os.path.join(local_vl_path(), "ve.dll")) and os.path.isfile(
        local_java_path()
    )


def _helper_jar_pair(directory: str) -> Tuple[str, str]:
    jar = os.path.join(directory, "nuance_ve_helper.jar")
    jna = os.path.join(directory, "jna.jar")
    return jar, jna


def _is_helper_dir(directory: str) -> bool:
    if not directory:
        return False
    jar, jna = _helper_jar_pair(directory)
    return os.path.isfile(jar) and os.path.isfile(jna)


def _install_root_candidates() -> list[str]:
    """Dirs that may contain ``tools/nuance_ve`` after packaging or in a checkout."""
    roots: list[str] = []
    try:
        roots.append(os.getcwd())
    except Exception:
        pass
    try:
        import sys

        if getattr(sys, "frozen", False):
            roots.append(os.path.dirname(os.path.abspath(sys.executable)))
    except Exception:
        pass
    # Source tree: soundrts/lib/nuance_tts.py → repo root
    here = os.path.dirname(os.path.abspath(__file__))
    roots.append(os.path.normpath(os.path.join(here, "..", "..")))
    # Dedupe while preserving order
    out: list[str] = []
    seen = set()
    for r in roots:
        if not r:
            continue
        key = os.path.normcase(os.path.abspath(r))
        if key in seen:
            continue
        seen.add(key)
        out.append(os.path.abspath(r))
    return out


def discover_helper_dir() -> str:
    """Find ``nuance_ve_helper.jar`` + ``jna.jar``.

    Packaged builds must not rely on ``__file__`` alone: under PyInstaller the
    module lives in ``_internal/``, while ``tools/nuance_ve`` sits next to the
    exe (cwd). Prefer that, then the voice-pack ``helper/`` copy, then the
    source-tree ``tools/nuance_ve``.
    """
    cands = [local_helper_dir()]
    for root in _install_root_candidates():
        cands.append(os.path.join(root, "tools", "nuance_ve"))
    for d in cands:
        if _is_helper_dir(d):
            return os.path.abspath(d)
    return ""


def _repo_tools_dir() -> str:
    """Back-compat alias used by older call sites / tests."""
    return discover_helper_dir() or os.path.join("tools", "nuance_ve")


def _default_vl_candidates() -> list[str]:
    """Prefer SoundRTS-local pack; optional config override only."""
    cands = [local_vl_path()]
    try:
        from .. import config

        p = (getattr(config, "nuance_vl_path", "") or "").strip()
        if p:
            cands.insert(0, p)
    except Exception:
        pass
    return cands


def discover_vl_path() -> str:
    for p in _default_vl_candidates():
        if p and os.path.isfile(os.path.join(p, "ve.dll")):
            return os.path.abspath(p)
    return ""


def discover_java() -> str:
    try:
        from .. import config

        p = (getattr(config, "nuance_java", "") or "").strip()
        if p and os.path.isfile(p):
            return _prefer_javaw(p)
    except Exception:
        pass
    env = (os.environ.get("SOUNDRTS_NUANCE_JAVA") or "").strip()
    if env and os.path.isfile(env):
        return _prefer_javaw(env)
    local = local_java_path()
    if os.path.isfile(local):
        _ensure_client_jvm(os.path.dirname(local))
        return local
    vl = discover_vl_path()
    if vl:
        sibling = os.path.normpath(os.path.join(vl, "..", "jre", "bin", "java.exe"))
        if os.path.isfile(sibling):
            _ensure_client_jvm(os.path.dirname(sibling))
            return _prefer_javaw(sibling)
    return ""


def _ensure_client_jvm(java_bin_dir: str) -> None:
    """Some MW JREs only ship server/jvm.dll; java.exe still looks for client/."""
    client = os.path.join(java_bin_dir, "client", "jvm.dll")
    server = os.path.join(java_bin_dir, "server", "jvm.dll")
    if os.path.isfile(client) or not os.path.isfile(server):
        return
    try:
        os.makedirs(os.path.join(java_bin_dir, "client"), exist_ok=True)
        shutil.copy2(server, client)
    except Exception:
        pass


def _install_helper_jars(dest_root: str | None = None) -> bool:
    """Copy helper jars into ``user/voices/nuance/helper`` when available."""
    dest = os.path.join(dest_root or local_nuance_root(), "helper")
    if _is_helper_dir(dest):
        return True
    src = ""
    for root in _install_root_candidates():
        cand = os.path.join(root, "tools", "nuance_ve")
        if _is_helper_dir(cand):
            src = cand
            break
    if not src:
        return False
    try:
        os.makedirs(dest, exist_ok=True)
        for name in ("nuance_ve_helper.jar", "jna.jar"):
            shutil.copy2(os.path.join(src, name), os.path.join(dest, name))
        return _is_helper_dir(dest)
    except Exception:
        exception("failed to install Nuance helper jars")
        return False


def available() -> bool:
    return bool(
        discover_vl_path() and discover_java() and discover_helper_dir()
    )


def find_mist_world_roots() -> list[str]:
    """Candidate Mist World install dirs that still contain ``vl/ve.dll``."""
    cands = []
    for root in (
        r"E:\rj\yx\mw",
        r"D:\rj\yx\mw",
        r"C:\rj\yx\mw",
        os.path.join(os.path.expanduser("~"), "mw"),
    ):
        if os.path.isfile(os.path.join(root, "vl", "ve.dll")):
            cands.append(os.path.abspath(root))
    return cands


def import_from_mist_world(
    mw_root: str = "",
    *,
    progress=None,
) -> Tuple[bool, str]:
    """Copy ``vl`` + 32-bit ``jre`` from Mist World into ``user/voices/nuance``.

    After a successful import, SoundRTS uses only the local copy.
    ``progress`` is an optional ``callable(str)`` for status lines.
    """

    def _say(msg: str) -> None:
        if progress:
            try:
                progress(msg)
            except Exception:
                pass

    roots = [mw_root] if mw_root else find_mist_world_roots()
    roots = [r for r in roots if r and os.path.isdir(r)]
    if not roots:
        return False, "未找到迷雾世界目录（需要其中的 vl 与 jre）"
    src_root = os.path.abspath(roots[0])
    src_vl = os.path.join(src_root, "vl")
    src_jre = os.path.join(src_root, "jre")
    if not os.path.isfile(os.path.join(src_vl, "ve.dll")):
        return False, f"缺少 ve.dll：{src_vl}"
    if not os.path.isfile(os.path.join(src_jre, "bin", "java.exe")):
        return False, f"缺少 32 位 jre：{src_jre}"

    dest_root = local_nuance_root()
    dest_vl = local_vl_path()
    dest_jre = os.path.join(dest_root, "jre")
    os.makedirs(dest_root, exist_ok=True)

    try:
        _say("正在复制苹果音库 vl …")
        if os.path.isdir(dest_vl):
            shutil.rmtree(dest_vl)
        shutil.copytree(src_vl, dest_vl)
        _say("正在复制 32 位 Java 运行库 …")
        if os.path.isdir(dest_jre):
            shutil.rmtree(dest_jre)
        shutil.copytree(src_jre, dest_jre)
        _ensure_client_jvm(os.path.join(dest_jre, "bin"))
        _install_helper_jars(dest_root)
        marker = os.path.join(dest_root, "README.txt")
        with open(marker, "w", encoding="utf-8") as f:
            f.write(
                "SoundRTS 本地苹果音库（Nuance Vocalizer）\n"
                "====================================\n\n"
                f"从迷雾世界导入：{src_root}\n"
                "目录结构：\n"
                "  vl/     — ve.dll 与语音数据\n"
                "  jre/    — 32 位 Java（助手进程用）\n"
                "  helper/ — nuance_ve_helper.jar + jna.jar\n\n"
                "运行时只使用本目录，不再依赖迷雾世界安装路径。\n"
                "请勿把本目录再分发给他人（授权属于你自己的迷雾世界拷贝）。\n"
            )
    except Exception as e:
        exception("import Nuance pack failed")
        return False, str(e)

    shutdown()
    try:
        from .. import config

        if (getattr(config, "nuance_vl_path", "") or "").strip():
            config.nuance_vl_path = ""
        if (getattr(config, "nuance_java", "") or "").strip():
            config.nuance_java = ""
        config.save()
    except Exception:
        pass

    if not local_pack_installed():
        return False, "复制完成但校验失败"
    _say("导入完成")
    return True, dest_root


def _ensure_reader() -> None:
    global _reader_started
    if _reader_started:
        return
    _reader_started = True

    def _loop():
        global _speaking, _speak_end
        while True:
            proc = _proc
            if proc is None or proc.stdout is None:
                time.sleep(0.05)
                continue
            try:
                raw = proc.stdout.readline()
            except Exception:
                time.sleep(0.05)
                continue
            if not raw:
                time.sleep(0.05)
                continue
            try:
                msg = json.loads(raw.decode("utf-8", errors="replace").strip())
            except Exception:
                continue
            cmd = msg.get("cmd") or ""
            if cmd == "speak_done":
                _speaking = False
                _speak_end = time.time()
            ev = _pending.get(cmd)
            if isinstance(ev, threading.Event):
                _pending[cmd] = msg
                ev.set()

    threading.Thread(target=_loop, name="nuance-reader", daemon=True).start()


def _send(obj: dict, *, wait_cmd: str = "", timeout: float = 30.0) -> Optional[dict]:
    if _proc is None or _proc.stdin is None:
        return None
    _ensure_reader()
    wait_event = None
    if wait_cmd:
        wait_event = threading.Event()
        _pending[wait_cmd] = wait_event
    try:
        with _io_lock:
            payload = (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8")
            _proc.stdin.write(payload)
            _proc.stdin.flush()
    except Exception:
        exception("Nuance write failed")
        if wait_cmd:
            _pending.pop(wait_cmd, None)
        return None
    if not wait_event:
        return {"ok": True}
    if not wait_event.wait(timeout):
        _pending.pop(wait_cmd, None)
        return None
    resp = _pending.pop(wait_cmd, None)
    return resp if isinstance(resp, dict) else None


def _popen_kwargs() -> dict:
    """Hide the Java helper console under windowed (-w) PyInstaller builds.

    Without CREATE_NO_WINDOW, ``java.exe`` pops a cmd window; closing that
    window kills the helper and Nuance speech starts stuttering on restart.
    """
    kw: dict = {}
    if os.name == "nt":
        # Python 3.7+: subprocess.CREATE_NO_WINDOW == 0x08000000
        flag = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        kw["creationflags"] = flag
        # Keep stderr piped (already) so nothing attaches to a console.
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = getattr(subprocess, "SW_HIDE", 0)
        kw["startupinfo"] = si
    return kw


def _ensure_proc() -> bool:
    global _proc, _ready, _vl_path
    with _lock:
        if _proc is not None and _proc.poll() is None and _ready:
            return True
        _shutdown_unlocked()
        java = discover_java()
        vl = discover_vl_path()
        tools = discover_helper_dir()
        jar, jna = _helper_jar_pair(tools) if tools else ("", "")
        if not (java and vl and tools and os.path.isfile(jar) and os.path.isfile(jna)):
            warning(
                "Nuance helper unavailable (java=%r vl=%r helper=%r)",
                java,
                vl,
                tools,
            )
            return False
        _ensure_client_jvm(os.path.dirname(java))
        cwd = os.path.dirname(vl)
        cp = jar + os.pathsep + jna
        try:
            _proc = subprocess.Popen(
                [java, "-cp", cp, "soundrts.nuance.Helper"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd,
                bufsize=0,
                **_popen_kwargs(),
            )
        except Exception:
            exception("failed to start Nuance helper")
            _proc = None
            return False
        _ensure_reader()
        resp = _send({"cmd": "init", "vl": vl.replace("\\", "/")}, wait_cmd="init", timeout=20.0)
        if not resp or not resp.get("ok"):
            warning("Nuance init failed: %r", resp)
            _shutdown_unlocked()
            return False
        _vl_path = vl
        _ready = True
        return True


def _shutdown_unlocked() -> None:
    global _proc, _ready, _speaking
    if _proc is not None:
        try:
            if _proc.poll() is None and _proc.stdin:
                with _io_lock:
                    line = (json.dumps({"cmd": "quit"}) + "\n").encode("utf-8")
                    _proc.stdin.write(line)
                    _proc.stdin.flush()
                _proc.wait(timeout=2)
        except Exception:
            pass
        try:
            if _proc.poll() is None:
                _proc.kill()
        except Exception:
            pass
    _proc = None
    _ready = False
    _speaking = False


def list_voices() -> list[str]:
    global _voices_cache
    if not _ensure_proc():
        return list(_voices_cache)
    resp = _send({"cmd": "list"}, wait_cmd="list", timeout=20.0)
    if resp and resp.get("ok"):
        _voices_cache = list(resp.get("voices") or [])
    return list(_voices_cache)


def list_audio_devices() -> list[str]:
    """Playback mixers known to the Nuance Java helper (may be empty)."""
    if not _ensure_proc():
        return []
    resp = _send({"cmd": "list_devices"}, wait_cmd="list_devices", timeout=10.0)
    if resp and resp.get("ok"):
        return [d for d in (resp.get("devices") or []) if d]
    return []


def set_audio_device(device: str) -> None:
    """Route Nuance PCM output to a mixer (``default`` = system default)."""
    name = (device or "default").strip() or "default"
    if not _ensure_proc():
        return
    _send({"cmd": "set_device", "device": name}, wait_cmd="set_device", timeout=10.0)


def _sapi_rate_to_nuance(rate: int) -> int:
    rate = max(-10, min(10, int(rate)))
    return max(0, min(100, 80 + rate * 2))


def speak(
    text: str,
    voice: str = "Ting-Ting",
    rate: int = 80,
    interrupt: bool = True,
    volume: int = 80,
    pitch: int = 50,
    lv: float = 1.0,
    rv: float = 1.0,
) -> None:
    """Start Nuance speech (non-blocking). New speak interrupts the previous one.

    ``rate`` / ``volume`` / ``pitch`` are MW-style 0..100.
    ``lv`` / ``rv`` (0..1) pan synthesized PCM left/right in the Java helper.
    """
    global _speaking, _speak_end, _speak_gen
    if not text:
        return
    voice = nuance_voice_name(voice) or "Ting-Ting"
    if not _ensure_proc():
        return
    if interrupt:
        stop()
    _speak_gen += 1
    gen = _speak_gen
    _speaking = True
    _speak_end = time.time() + max(0.4, len(text) * 0.08)
    try:
        gain_l = max(0.0, min(1.0, float(lv)))
        gain_r = max(0.0, min(1.0, float(rv)))
    except Exception:
        gain_l, gain_r = 1.0, 1.0
    resp = _send(
        {
            "cmd": "speak",
            "voice": voice,
            "text": text,
            "rate": max(0, min(100, int(rate))),
            "volume": max(0, min(100, int(volume))),
            "pitch": max(0, min(100, int(pitch))),
            "lv": gain_l,
            "rv": gain_r,
        },
        wait_cmd="speak",
        timeout=10.0,
    )
    if not resp or not resp.get("ok"):
        if gen == _speak_gen:
            _speaking = False
            _speak_end = time.time()
        warning("Nuance speak failed: %r", resp)


def set_pan(lv: float = 1.0, rv: float = 1.0) -> None:
    """Update stereo gains for the utterance currently playing (no ACK wait)."""
    if _proc is None:
        return
    try:
        gain_l = max(0.0, min(1.0, float(lv)))
        gain_r = max(0.0, min(1.0, float(rv)))
    except Exception:
        return
    _send({"cmd": "set_pan", "lv": gain_l, "rv": gain_r}, wait_cmd="", timeout=0)


def stop() -> None:
    global _speaking, _speak_end, _speak_gen
    was_busy = bool(_speaking) or (bool(_speak_end) and _speak_end > time.time())
    _speak_gen += 1
    _speaking = False
    _speak_end = time.time()
    if _proc is None:
        return
    if not was_busy:
        # Idle: do not block the UI thread waiting for a Java ACK (menu F3
        # disable was ~2s because stop always waited even when silent).
        _send({"cmd": "stop"}, wait_cmd="", timeout=0)
        return
    _send({"cmd": "stop"}, wait_cmd="stop", timeout=5.0)


def is_speaking() -> bool:
    # Prefer live flag (cleared on speak_done); fall back to estimate hold.
    if _speaking:
        return True
    return bool(_speak_end) and _speak_end > time.time()


def shutdown() -> None:
    with _lock:
        _shutdown_unlocked()
