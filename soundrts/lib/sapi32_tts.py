"""32-bit SAPI helper for voices only registered under WOW6432Node (e.g. VW Julie).

64-bit Python's ``SAPI.SpVoice.GetVoices()`` cannot see 32-bit-only engines that
still appear in ``sapi.cpl``. This module talks to SysWOW64 PowerShell running
``tools/sapi32/helper.ps1``.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from typing import List, Optional

from .log import exception, warning

_proc: Optional[subprocess.Popen] = None
_lock = threading.Lock()
_io_lock = threading.Lock()
_ready = False
_reader_started = False
_pending: dict = {}
_voices_cache: List[str] = []
_speaking = False
_speak_end = 0.0


def _popen_kwargs() -> dict:
    kw: dict = {}
    if os.name == "nt":
        flag = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        kw["creationflags"] = flag
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = getattr(subprocess, "SW_HIDE", 0)
        kw["startupinfo"] = si
    return kw


def _install_roots() -> list[str]:
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
    here = os.path.dirname(os.path.abspath(__file__))
    roots.append(os.path.normpath(os.path.join(here, "..", "..")))
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


def discover_helper_script() -> str:
    for root in _install_roots():
        p = os.path.join(root, "tools", "sapi32", "helper.ps1")
        if os.path.isfile(p):
            return p
    return ""


def discover_powershell32() -> str:
    windir = os.environ.get("WINDIR") or r"C:\Windows"
    p = os.path.join(windir, "SysWOW64", "WindowsPowerShell", "v1.0", "powershell.exe")
    return p if os.path.isfile(p) else ""


def available() -> bool:
    return bool(discover_powershell32() and discover_helper_script())


def _ensure_reader() -> None:
    global _reader_started
    if _reader_started:
        return
    _reader_started = True

    def _loop():
        global _speaking
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
                line = raw.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                resp = json.loads(line)
            except Exception:
                continue
            cmd = str(resp.get("cmd") or "")
            ev = _pending.get(cmd)
            if isinstance(ev, threading.Event):
                _pending[cmd] = resp
                ev.set()

    threading.Thread(target=_loop, name="sapi32-reader", daemon=True).start()


def _send(obj: dict, *, wait_cmd: str = "", timeout: float = 15.0) -> Optional[dict]:
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
        exception("sapi32 write failed")
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


def _ensure_proc() -> bool:
    global _proc, _ready
    with _lock:
        if _proc is not None and _proc.poll() is None and _ready:
            return True
        _shutdown_unlocked()
        ps = discover_powershell32()
        script = discover_helper_script()
        if not (ps and script):
            warning("sapi32 helper unavailable (ps=%r script=%r)", bool(ps), script)
            return False
        try:
            _proc = subprocess.Popen(
                [
                    ps,
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    script,
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,
                **_popen_kwargs(),
            )
        except Exception:
            exception("failed to start sapi32 helper")
            _proc = None
            return False
        _ensure_reader()
        # Give PowerShell a moment to create SAPI.SpVoice before first command.
        time.sleep(0.35)
        resp = _send({"cmd": "init"}, wait_cmd="init", timeout=20.0)
        if not resp or not resp.get("ok"):
            warning("sapi32 init failed: %r", resp)
            _shutdown_unlocked()
            return False
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


def shutdown() -> None:
    with _lock:
        _shutdown_unlocked()


def list_voices() -> list[str]:
    global _voices_cache
    if not available():
        return list(_voices_cache)
    if not _ensure_proc():
        return list(_voices_cache)
    resp = _send({"cmd": "list"}, wait_cmd="list", timeout=15.0)
    if resp and resp.get("ok"):
        _voices_cache = [str(v) for v in (resp.get("voices") or []) if v]
    return list(_voices_cache)


def list_wow6432_token_names() -> list[str]:
    """Fast registry scan for 32-bit voice token display names (no helper)."""
    if os.name != "nt":
        return []
    try:
        import winreg

        key_path = r"SOFTWARE\WOW6432Node\Microsoft\Speech\Voices\Tokens"
        out: list[str] = []
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as root:
            i = 0
            while True:
                try:
                    sub = winreg.EnumKey(root, i)
                except OSError:
                    break
                i += 1
                try:
                    with winreg.OpenKey(root, sub) as tok:
                        try:
                            name, _ = winreg.QueryValueEx(tok, "409")
                        except OSError:
                            name = sub
                        if name:
                            out.append(str(name))
                except OSError:
                    continue
        return out
    except Exception:
        return []


def speak(
    text: str,
    *,
    voice: str = "",
    rate: int = 0,
    volume: int = 100,
    interrupt: bool = True,
) -> bool:
    global _speaking, _speak_end
    if not text:
        return False
    if not _ensure_proc():
        return False
    resp = _send(
        {
            "cmd": "speak",
            "text": text,
            "voice": voice or "",
            "rate": int(rate),
            "volume": int(volume),
            "interrupt": bool(interrupt),
        },
        wait_cmd="speak",
        timeout=10.0,
    )
    ok = bool(resp and resp.get("ok"))
    if ok:
        _speaking = True
        # Rough busy hold; helper Speak is async.
        _speak_end = time.time() + max(0.4, min(60.0, 0.06 * len(text) + 0.3))
    return ok


def stop() -> None:
    global _speaking, _speak_end
    if _proc is None:
        _speaking = False
        return
    _send({"cmd": "stop"}, wait_cmd="stop", timeout=5.0)
    _speaking = False
    _speak_end = 0.0


def is_speaking() -> bool:
    global _speaking
    if _speaking and time.time() < _speak_end:
        return True
    if _proc is None:
        _speaking = False
        return False
    resp = _send({"cmd": "busy"}, wait_cmd="busy", timeout=2.0)
    busy = bool(resp and resp.get("ok") and resp.get("busy"))
    _speaking = busy
    return busy
