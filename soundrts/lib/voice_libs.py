"""Mist-World-style dual voice libraries (primary + secondary).

主语音库 (primary): player ops / menus (classic SoundRTS2, no wx).
  When a dedicated screen reader is active, AO2 (争渡/NVDA/…) takes over
  primary duties so Nuance/SAPI primary does not fight the reader.
副语音库 (secondary): passive game events (discoveries, casualties, alerts)

F9–F12 adjust primary; Shift+F9–F12 adjust secondary:
  F9  cycle output sound card for this library
  F10 cycle parameter type (volume / pitch / rate / voice)
  F11 decrease / previous value of current parameter
  F12 increase / next value of current parameter
  Left Shift+C  copy last text spoken by primary library
  Right Shift+C copy last text spoken by secondary library
  Left Shift+B  append primary last utterance to clipboard
  Right Shift+B append secondary last utterance to clipboard
"""

from __future__ import annotations

from typing import List, Tuple

from .log import exception

PRIMARY = "primary"
SECONDARY = "secondary"

PARAM_VOLUME = 0
PARAM_PITCH = 1
PARAM_RATE = 2
PARAM_VOICE = 3
# Fallback labels if tts.txt is missing an id
PARAM_NAMES = ("音量", "音调", "语速", "语音")
PARAM_KEYS = ("volume", "pitch", "rate", "voice")
PARAM_COUNT = 4

DEVICE_DEFAULT = "default"

_STEP = 5

_profiles = {
    PRIMARY: {
        "voice": "auto",
        "rate": 80,
        "volume": 80,
        "pitch": 50,
        "device": DEVICE_DEFAULT,
        "param": PARAM_VOLUME,
    },
    SECONDARY: {
        "voice": "auto",
        "rate": 80,
        "volume": 80,
        "pitch": 50,
        "device": DEVICE_DEFAULT,
        "param": PARAM_VOLUME,
    },
}


def _clamp(v: int, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, int(v)))


def profile(which: str) -> dict:
    which = PRIMARY if which == PRIMARY else SECONDARY
    return _profiles[which]


def get_voice(which: str) -> str:
    return str(profile(which).get("voice") or "auto")


def get_rate(which: str) -> int:
    return _clamp(profile(which).get("rate", 80))


def get_volume(which: str) -> int:
    return _clamp(profile(which).get("volume", 80))


def get_pitch(which: str) -> int:
    return _clamp(profile(which).get("pitch", 50))


def get_device(which: str) -> str:
    d = str(profile(which).get("device") or DEVICE_DEFAULT).strip()
    return d or DEVICE_DEFAULT


def get_param(which: str) -> int:
    return int(profile(which).get("param", PARAM_VOLUME)) % PARAM_COUNT


def sapi_rate_from_100(rate_100: int) -> int:
    """Map MW-style 0..100 onto SAPI Rate -10..10."""
    return _clamp(round((_clamp(rate_100) - 50) / 5), -10, 10)


def load_from_config() -> None:
    try:
        from .. import config

        legacy = (getattr(config, "game_voice", "auto") or "auto").strip() or "auto"
        legacy_rate = int(getattr(config, "game_voice_rate", 0) or 0)
        legacy_100 = _clamp(50 + legacy_rate * 5)

        def _read(prefix, fallback_voice, fallback_rate):
            voice = (getattr(config, f"{prefix}_voice", "") or "").strip()
            if not voice:
                voice = fallback_voice
            rate = getattr(config, f"{prefix}_rate", None)
            if rate is None or rate == "":
                rate = fallback_rate
            volume = getattr(config, f"{prefix}_volume", 80)
            pitch = getattr(config, f"{prefix}_pitch", 50)
            device = (getattr(config, f"{prefix}_device", "") or "").strip() or DEVICE_DEFAULT
            param = getattr(config, f"{prefix}_param", PARAM_VOLUME)
            return {
                "voice": voice,
                "rate": _clamp(rate),
                "volume": _clamp(volume),
                "pitch": _clamp(pitch),
                "device": device,
                "param": int(param) % PARAM_COUNT,
            }

        _profiles[PRIMARY] = _read("primary", "auto", 80)
        _profiles[SECONDARY] = _read("secondary", legacy, legacy_100)
    except Exception:
        exception("voice_libs load_from_config failed")


def save_to_config() -> None:
    try:
        from .. import config

        for which, prefix in ((PRIMARY, "primary"), (SECONDARY, "secondary")):
            p = profile(which)
            setattr(config, f"{prefix}_voice", p["voice"])
            setattr(config, f"{prefix}_rate", int(p["rate"]))
            setattr(config, f"{prefix}_volume", int(p["volume"]))
            setattr(config, f"{prefix}_pitch", int(p["pitch"]))
            setattr(config, f"{prefix}_device", str(p.get("device") or DEVICE_DEFAULT))
            setattr(config, f"{prefix}_param", int(p["param"]) % PARAM_COUNT)
        config.game_voice = get_voice(SECONDARY)
        config.game_voice_rate = sapi_rate_from_100(get_rate(SECONDARY))
        config.save()
    except Exception:
        exception("voice_libs save_to_config failed")


def list_all_voices() -> List[str]:
    """auto / default / SAPI descriptions / pack:folder / nuance:Name."""
    from . import game_tts, nuance_tts, voice_packs

    out = ["auto", "default"]
    installed: List[str] = []
    try:
        installed = list(game_tts.list_sapi_voices() or [])
        for v in installed:
            if v and v not in out:
                out.append(v)
    except Exception:
        pass
    try:
        # Friendly packs whose SAPI engine is actually installed.
        for pid in voice_packs.list_selectable_ids(installed_sapi=installed):
            if pid and pid not in out:
                out.append(pid)
        # Also surface packs that are present but not installed, so the user
        # can hear why selection fails (set_voice / announce).
        for p in voice_packs.scan_packs():
            if p["id"] not in out:
                out.append(p["id"])
    except Exception:
        pass
    try:
        for v in game_tts.list_nuance_voices() or []:
            if v and v not in out:
                out.append(v)
    except Exception:
        pass
    for which in (PRIMARY, SECONDARY):
        cur = get_voice(which)
        if cur and cur not in out:
            out.append(cur)
    return out


def display_voice(voice_id: str) -> str:
    from . import nuance_tts, voice_packs

    v = (voice_id or "auto").strip() or "auto"
    if v == "auto":
        return "自动"
    if v == "default":
        return "系统默认"
    if voice_packs.is_pack_voice(v) or voice_packs.packs_by_sapi().get(v.lower()):
        title = voice_packs.display_name(v)
        try:
            from . import game_tts

            installed = game_tts.list_sapi_voices() or []
            sapi, pack = voice_packs.resolve_sapi(v)
            if pack and not voice_packs.pack_installed(pack, installed):
                return f"{title}（未安装系统语音）"
        except Exception:
            pass
        return title
    if nuance_tts.is_nuance_voice(v):
        return nuance_tts.display_name(nuance_tts.nuance_voice_name(v))
    return v


def list_audio_devices() -> List[str]:
    """default + playback device names (SAPI / system)."""
    from . import game_tts

    out = [DEVICE_DEFAULT]
    try:
        for name in game_tts.list_audio_outputs() or []:
            n = (name or "").strip()
            if n and n not in out:
                out.append(n)
    except Exception:
        pass
    try:
        from . import nuance_tts

        for name in nuance_tts.list_audio_devices() or []:
            n = (name or "").strip()
            if n and n not in out:
                out.append(n)
    except Exception:
        pass
    for which in (PRIMARY, SECONDARY):
        cur = get_device(which)
        if cur and cur not in out:
            out.append(cur)
    return out


def display_device(device_id: str) -> str:
    d = (device_id or DEVICE_DEFAULT).strip() or DEVICE_DEFAULT
    if d == DEVICE_DEFAULT:
        return "系统默认声卡"
    return d


def cycle_voice(which: str, *, step: int = 1) -> str:
    voices = list_all_voices()
    if not voices:
        return get_voice(which)
    cur = get_voice(which)
    try:
        idx = voices.index(cur)
    except ValueError:
        idx = 0
    idx = (idx + int(step)) % len(voices)
    profile(which)["voice"] = voices[idx]
    save_to_config()
    _apply_engine(which)
    return voices[idx]


def cycle_device(which: str, *, step: int = 1) -> str:
    devices = list_audio_devices()
    if not devices:
        return get_device(which)
    cur = get_device(which)
    try:
        idx = devices.index(cur)
    except ValueError:
        idx = 0
    idx = (idx + int(step)) % len(devices)
    profile(which)["device"] = devices[idx]
    save_to_config()
    _apply_engine(which)
    return devices[idx]


def cycle_param(which: str, *, step: int = 1) -> int:
    p = profile(which)
    p["param"] = (get_param(which) + int(step)) % PARAM_COUNT
    save_to_config()
    return p["param"]


def nudge_param(which: str, delta: int) -> Tuple[int, object]:
    """Adjust current parameter. Voice steps by ±1; numbers by delta."""
    p = profile(which)
    param = get_param(which)
    if param == PARAM_VOICE:
        voice = cycle_voice(which, step=1 if int(delta) > 0 else -1)
        return param, voice
    key = PARAM_KEYS[param]
    p[key] = _clamp(int(p.get(key, 50)) + int(delta))
    save_to_config()
    _apply_engine(which)
    return param, int(p[key])


def param_type_text(which: str) -> str:
    """Localized name for the current F10 parameter type."""
    idx = get_param(which)
    try:
        from .. import msgparts as mp
        from .sound_cache import sounds

        parts = (
            mp.VOICE_LIB_VOLUME,
            mp.VOICE_LIB_PITCH,
            mp.VOICE_LIB_RATE,
            mp.VOICE_LIB_VOICE_PARAM,
        )[idx]
        # Classic UI: resolve TTS txt strings without wxui.
        bits = []
        for p in parts:
            if isinstance(p, str):
                bits.append(p)
            else:
                try:
                    t = sounds.text(str(int(p)))
                    if t:
                        bits.append(str(t))
                except Exception:
                    pass
        text = "".join(bits).strip()
        if text:
            return text
    except Exception:
        pass
    return PARAM_NAMES[idx]


def param_value_text(which: str) -> str:
    """Short feedback for F11/F12."""
    param = get_param(which)
    if param == PARAM_VOICE:
        return display_voice(get_voice(which))
    name = param_type_text(which)
    key = PARAM_KEYS[param]
    return f"{name} {int(profile(which).get(key, 50))}"


def status_text(which: str) -> str:
    """Longer status (clipboard / options menu)."""
    label = "主语音库" if which == PRIMARY else "副语音库"
    p = profile(which)
    return (
        f"{label} {display_voice(p['voice'])}，"
        f"声卡 {display_device(p.get('device'))}，"
        f"{param_value_text(which)}"
    )


_last_announce_text = ""
_last_announce_time = 0.0
_COPY_HOTKEY_WINDOW_S = 120.0


def last_announce_text() -> str:
    return _last_announce_text or ""


def announce_is_fresh(window_s: float = _COPY_HOTKEY_WINDOW_S) -> bool:
    if not _last_announce_text:
        return False
    try:
        import time

        return (time.time() - _last_announce_time) <= float(window_s)
    except Exception:
        return bool(_last_announce_text)


def _clipboard_get() -> str:
    try:
        from ..clientmenu import _clipboard_get_text

        return _clipboard_get_text() or ""
    except Exception:
        pass
    try:
        import wx

        if not wx.TheClipboard.Open():
            return ""
        try:
            if wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_UNICODETEXT)):
                data = wx.TextDataObject()
                if wx.TheClipboard.GetData(data):
                    return data.GetText() or ""
        finally:
            wx.TheClipboard.Close()
    except Exception:
        pass
    return ""


def _clipboard_set(text: str) -> bool:
    try:
        from ..clientmenu import _clipboard_set_text

        if _clipboard_set_text(text):
            return True
    except Exception:
        pass
    try:
        import wx

        if not wx.TheClipboard.Open():
            return False
        try:
            wx.TheClipboard.SetData(wx.TextDataObject(text))
            return True
        finally:
            wx.TheClipboard.Close()
    except Exception:
        return False


def which_from_shift_mod(mod: int) -> str:
    """Left Shift → primary; Right Shift alone → secondary.

    Prefer pygame L/R bits when present. Only use Win32 when the event has
    generic SHIFT but lost the L/R distinction (wx→pygame injection).
    """
    try:
        from pygame.locals import KMOD_LSHIFT, KMOD_RSHIFT, KMOD_SHIFT
    except Exception:
        return PRIMARY
    left = bool(mod & KMOD_LSHIFT)
    right = bool(mod & KMOD_RSHIFT)
    if (mod & KMOD_SHIFT) and not left and not right:
        try:
            import ctypes

            win_left = bool(ctypes.windll.user32.GetKeyState(0xA0) & 0x8000)  # VK_LSHIFT
            win_right = bool(ctypes.windll.user32.GetKeyState(0xA1) & 0x8000)  # VK_RSHIFT
            if win_left or win_right:
                left, right = win_left, win_right
        except Exception:
            pass
    if right and not left:
        return SECONDARY
    return PRIMARY


def _clipboard_feedback(ok: bool, *, append: bool = False) -> None:
    try:
        from .. import msgparts as mp
        from ..clientmedia import voice
        from .msgs import literal_text_msg

        if ok:
            tip = "已追加到剪贴板" if append else "已复制到剪贴板"
            voice.item(literal_text_msg(tip))
        else:
            voice.item(mp.BEEP)
    except Exception:
        pass


def copy_voice_info(which: str, *, append: bool = False) -> bool:
    """Copy (or append) the last text spoken on this voice library."""
    try:
        from . import game_tts

        text = (game_tts.last_spoken(which) or "").strip()
    except Exception:
        text = ""
    if not text:
        try:
            from .. import msgparts as mp
            from ..clientmedia import voice

            voice.item(mp.BEEP)
        except Exception:
            pass
        return True
    if append:
        prev = _clipboard_get().rstrip()
        out = f"{prev}\n{text}" if prev else text
    else:
        out = text
    ok = _clipboard_set(out)
    _clipboard_feedback(ok, append=append)
    return True


def copy_last_announce(*, append: bool = False) -> bool:
    """Append (or overwrite) last voice-library status announcement (F9–F12)."""
    text = (_last_announce_text or "").strip()
    if not text:
        try:
            from .. import msgparts as mp
            from ..clientmedia import voice

            voice.item(mp.BEEP)
        except Exception:
            pass
        return True
    if append:
        prev = _clipboard_get().rstrip()
        out = f"{prev}\n{text}" if prev else text
    else:
        out = text
    ok = _clipboard_set(out)
    _clipboard_feedback(ok, append=append)
    return True


def parse_voice_lib_which(arg, mod: int = 0) -> str:
    """Resolve binding arg or fall back to L/R Shift from ``mod``."""
    if arg is None or arg == "":
        return which_from_shift_mod(mod)
    s = str(arg).strip().lower()
    if s in ("1", "secondary", "sec", "副", "副库"):
        return SECONDARY
    if s in ("0", "primary", "pri", "主", "主库"):
        return PRIMARY
    return which_from_shift_mod(mod)


def _remember_announce(text: str) -> None:
    global _last_announce_text, _last_announce_time
    _last_announce_text = text
    try:
        import time

        _last_announce_time = time.time()
    except Exception:
        pass


def _speak_line(text: str, which: str) -> None:
    """Speak a short line on the library channel (classic UI / game_tts)."""
    _remember_announce(text)
    try:
        from . import game_tts

        game_tts.speak(text, interrupt=True, channel=which)
    except Exception:
        pass


def announce(which: str, extra: str = "") -> None:
    """Speak full status (options menu / explicit callers)."""
    text = status_text(which)
    if extra:
        text = f"{extra}，{text}"
    _speak_line(text, which)


def announce_param_type(which: str) -> None:
    """F10: only the parameter name (音量 / 音调 / 语速 / 音库)."""
    _speak_line(param_type_text(which), which)


def announce_param_value(which: str) -> None:
    """F11/F12: current value (or voice name)."""
    _speak_line(param_value_text(which), which)


def announce_device(which: str) -> None:
    """F9: current sound card name."""
    _speak_line(display_device(get_device(which)), which)


def _apply_engine(which: str) -> None:
    """Push profile onto game_tts / Nuance for this channel."""
    try:
        from . import game_tts

        game_tts.apply_library_profile(which)
    except Exception:
        pass


def toggle_secondary_voice_enabled(*, announce: bool = True) -> bool:
    """Flip ``config.secondary_voice_enabled``. Return the new enabled state.

    Menu-only helper (F3 / 语音库设置). When turning off, stop secondary TTS
    only if it is actually speaking (avoids a multi-second Nuance idle wait).
    """
    from .. import config
    from .. import msgparts as mp
    from . import game_tts

    enabled = int(getattr(config, "secondary_voice_enabled", 1))
    config.secondary_voice_enabled = 0 if enabled else 1
    config.save()
    if not config.secondary_voice_enabled:
        try:
            from ..clientmedia import voice

            if game_tts.is_speaking(game_tts.SECONDARY):
                voice.channel.stop(tts_channel=game_tts.SECONDARY)
        except Exception:
            pass
    if announce:
        try:
            from ..clientmedia import voice

            # Preempt current menu speech so the status line is immediate.
            voice.channel.stop()
            if config.secondary_voice_enabled:
                voice.item(mp.VOICE_LIB_SECONDARY_ON)
            else:
                voice.item(mp.VOICE_LIB_SECONDARY_OFF)
        except Exception:
            pass
    return bool(config.secondary_voice_enabled)


def handle_hotkey(key: int, mod: int) -> bool:
    """Handle F9–F12 / Shift+F9–F12 and L/R Shift+C / Shift+B."""
    try:
        from pygame.locals import (
            K_F9,
            K_F10,
            K_F11,
            K_F12,
            K_b,
            K_c,
            KMOD_CTRL,
            KMOD_SHIFT,
        )
    except Exception:
        return False
    if mod & KMOD_CTRL:
        return False
    if (mod & KMOD_SHIFT) and key == K_c:
        return copy_voice_info(which_from_shift_mod(mod))
    if (mod & KMOD_SHIFT) and key == K_b:
        return copy_voice_info(which_from_shift_mod(mod), append=True)
    which = SECONDARY if (mod & KMOD_SHIFT) else PRIMARY
    if key == K_F9:
        cycle_device(which, step=1)
        announce_device(which)
        return True
    if key == K_F10:
        cycle_param(which, step=1)
        announce_param_type(which)
        return True
    if key == K_F11:
        nudge_param(which, -_STEP)
        announce_param_value(which)
        return True
    if key == K_F12:
        nudge_param(which, _STEP)
        announce_param_value(which)
        return True
    return False


def apply_all() -> None:
    load_from_config()
    _apply_engine(PRIMARY)
    _apply_engine(SECONDARY)
