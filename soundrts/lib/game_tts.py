"""Game voice TTS — Nuance / SAPI libraries.

Two MW-style libraries (see ``voice_libs``):
- primary: player ops / out-of-match (unless a screen reader is active)
- secondary: in-match passive events (VoiceChannel info/alerts), when enabled

``config.secondary_voice_enabled`` (default 1): when 0, primary carries all
speech (E-style single channel). When 1, in-match alerts/info use secondary.

When ``tts.using_screen_reader()`` is true, **primary** utterances are
delegated to AO2 (争渡/NVDA/…) so the reader owns primary duties and does
not fight Nuance/SAPI. Secondary still uses this module when enabled.
"""

from __future__ import annotations

import os
import sys
import tempfile
import threading
import time
from queue import Queue
from typing import Optional

from .log import exception, warning

# SVSFlagsAsync | SVSFPurgeBeforeSpeak
_ASYNC = 1
_PURGE_ASYNC = 1 | 2

AUTO = "auto"
DEFAULT = "default"
PRIMARY = "primary"
SECONDARY = "secondary"

_voice = None
_lock = threading.Lock()
_end_time: Optional[float] = None
_pending = 0
_is_speaking = False
_wait_delay = 0.05
_queue: Queue = Queue()
_available = False
_init_event = threading.Event()
# Active profile snapshot used by the SAPI worker (secondary by default)
_configured_voice = AUTO
_configured_rate = 0
_configured_volume = 80
_configured_audio_output = "default"
_active_channel = SECONDARY
_channel_speaking = {PRIMARY: False, SECONDARY: False}
# Last text actually spoken on each library (for Left/Right Shift+C copy).
_last_spoken = {PRIMARY: "", SECONDARY: ""}
_last_spoken_time = {PRIMARY: 0.0, SECONDARY: 0.0}
# Secondary library is reserved for in-match passive lines only.
_in_match = False


def set_in_match(active: bool) -> None:
    """Enable/disable in-match mode (secondary library for passive events)."""
    global _in_match
    _in_match = bool(active)


def in_match() -> bool:
    return bool(_in_match)


def secondary_voice_enabled() -> bool:
    """True when the secondary library may carry in-match passive speech."""
    try:
        from .. import config

        return bool(int(getattr(config, "secondary_voice_enabled", 1)))
    except Exception:
        return True


def passive_channel() -> str:
    """Channel for alerts / info queue: secondary in-match (if enabled), else primary."""
    if _in_match and secondary_voice_enabled():
        return SECONDARY
    return PRIMARY


def _pick_chinese_voice(spvoice) -> bool:
    """Select first Chinese SAPI voice. Return True if one was found."""
    try:
        voices = spvoice.GetVoices()
        for i in range(int(voices.Count)):
            tok = voices.Item(i)
            desc = str(tok.GetDescription())
            low = desc.lower()
            if any(
                k in desc or k in low
                for k in (
                    "中文",
                    "汉语",
                    "chinese",
                    "zh-cn",
                    "zh_cn",
                    "huihui",
                    "yaoyao",
                    "kangkang",
                    "hanhan",
                    "lili",
                )
            ):
                spvoice.Voice = tok
                return True
    except Exception:
        pass
    return False


def _apply_voice_token(spvoice, name: str) -> bool:
    """Apply voice selection. ``name`` is auto / default / SAPI description."""
    if spvoice is None:
        return False
    name = (name or AUTO).strip() or AUTO
    if name == AUTO:
        _pick_chinese_voice(spvoice)
        return True
    if name == DEFAULT:
        try:
            import win32com.client

            fresh = win32com.client.Dispatch("SAPI.SpVoice")
            spvoice.Voice = fresh.Voice
            return True
        except Exception:
            return False
    try:
        voices = spvoice.GetVoices()
        name_low = name.lower()
        for i in range(int(voices.Count)):
            tok = voices.Item(i)
            desc = str(tok.GetDescription())
            if desc == name or desc.lower() == name_low or name_low in desc.lower():
                spvoice.Voice = tok
                return True
    except Exception:
        exception("failed to set SAPI voice %r", name)
    return False


def _apply_rate(spvoice, rate: int) -> None:
    try:
        spvoice.Rate = max(-10, min(10, int(rate)))
    except Exception:
        pass


def _apply_audio_output(spvoice, name: str) -> bool:
    """Set SpVoice playback device. ``default`` / empty → system default."""
    if spvoice is None:
        return False
    name = (name or "default").strip() or "default"
    try:
        if name == "default":
            spvoice.AudioOutput = None
            return True
        outs = spvoice.GetAudioOutputs()
        for i in range(int(outs.Count)):
            tok = outs.Item(i)
            if str(tok.GetDescription()) == name:
                spvoice.AudioOutput = tok
                return True
    except Exception:
        exception("failed to set SAPI AudioOutput %r", name)
    return False


def _create_voice_on_this_thread():
    """Create SpVoice on the calling thread (must be the game-tts worker)."""
    if sys.platform != "win32":
        return None
    try:
        import pythoncom
        import win32com.client

        pythoncom.CoInitialize()
        return win32com.client.Dispatch("SAPI.SpVoice")
    except Exception:
        exception("SAPI SpVoice unavailable; game voice text will be silent")
        return None


def available() -> bool:
    _init_event.wait(timeout=2.0)
    return bool(_available)


def is_speaking(channel: str | None = None) -> bool:
    """True while utterance is in progress or within estimated hold time.

    Classic AO2 TTS kept busy for ``len(text) * wait_delay`` so VoiceChannel
    queues and F5/F6 history could not race ahead. Nuance ``speak()`` returns
    after the start ACK; keep busy until ``speak_done`` (and/or ``_end_time``).
    When the screen reader owns primary, also wait on AO2 busy.

    ``channel``: ``None`` = any library; ``primary`` / ``secondary`` = that library only.
    """
    if channel is not None:
        channel = PRIMARY if channel == PRIMARY else SECONDARY
        if channel == PRIMARY:
            try:
                from . import tts as _ao2

                if _ao2.using_screen_reader() and _ao2.is_speaking():
                    return True
            except Exception:
                pass
            with _lock:
                if _channel_speaking[PRIMARY]:
                    return True
                if _active_channel == PRIMARY:
                    if _pending > 0:
                        return True
                    if _end_time is not None and _end_time > time.time():
                        return True
                    return bool(_is_speaking) and _active_channel == PRIMARY
            return False
        # secondary — prefer explicit channel flag; keep Nuance if it still owns it.
        if _channel_speaking[SECONDARY]:
            return True
        try:
            from . import nuance_tts

            if _active_channel == SECONDARY and nuance_tts.is_speaking():
                return True
        except Exception:
            pass
        with _lock:
            if _active_channel == SECONDARY:
                if _pending > 0:
                    return True
                if _end_time is not None and _end_time > time.time():
                    return True
                return bool(_is_speaking)
        return False

    if _pending > 0:
        return True
    try:
        from . import tts as _ao2

        if _ao2.using_screen_reader() and _ao2.is_speaking():
            return True
    except Exception:
        pass
    try:
        from . import nuance_tts

        if nuance_tts.is_speaking():
            return True
    except Exception:
        pass
    with _lock:
        if any(_channel_speaking.values()):
            return True
        if _end_time is not None and _end_time > time.time():
            return True
        # Read-only here — _loop2 clears _is_speaking when the hold expires.
        return bool(_is_speaking)


def _estimate_duration(text: str) -> float:
    # Floor so short lines still hold the VoiceChannel (queue / F5 pacing).
    delay = max(0.05, float(_wait_delay or 0.05))
    duration = len(text) * delay
    nb_digits = sum(c.isdigit() for c in text)
    try:
        from .. import parameters

        digit_bonus = parameters.d.get("tts_digit_coefficient", 1) - 1
        duration += nb_digits * digit_bonus * delay
    except Exception:
        pass
    return max(0.5, duration)


def _speak(text: str, interrupt: bool = True, volume: int = 80) -> None:
    global _pending, _end_time, _is_speaking
    try:
        if _voice is None:
            return
        try:
            try:
                from . import sound as _sound

                base = max(0, min(100, int(float(_sound.voice_volume) * 100)))
            except Exception:
                base = 100
            _voice.Volume = max(0, min(100, int(base * max(0, min(100, volume)) / 100)))
            flags = _PURGE_ASYNC if interrupt else _ASYNC
            _voice.Speak(str(text), flags)
        except Exception:
            exception("error during SAPI Speak(%r)", text)
            return
        now = time.time()
        dur = _estimate_duration(text)
        with _lock:
            if interrupt or _end_time is None or _end_time < now:
                _end_time = now + dur
            else:
                _end_time += dur
            _is_speaking = True
    finally:
        with _lock:
            _pending = max(0, _pending - 1)


def remember_spoken(channel: str, text: str) -> None:
    """Record the last utterance for Left/Right Shift+C (no speech)."""
    if not text:
        return
    channel = PRIMARY if channel == PRIMARY else SECONDARY
    _last_spoken[channel] = str(text).strip()
    try:
        _last_spoken_time[channel] = time.time()
    except Exception:
        pass


def last_spoken(channel: str) -> str:
    channel = PRIMARY if channel == PRIMARY else SECONDARY
    return _last_spoken.get(channel, "") or ""


def _clamp_pan(lv: float | None, rv: float | None) -> tuple[float, float]:
    try:
        gain_l = 1.0 if lv is None else max(0.0, min(1.0, float(lv)))
    except Exception:
        gain_l = 1.0
    try:
        gain_r = 1.0 if rv is None else max(0.0, min(1.0, float(rv)))
    except Exception:
        gain_r = 1.0
    return gain_l, gain_r


def set_pan(lv: float, rv: float) -> None:
    """Live-update Nuance stereo pan for the active secondary/primary utterance."""
    from . import nuance_tts

    gain_l, gain_r = _clamp_pan(lv, rv)
    try:
        nuance_tts.set_pan(gain_l, gain_r)
    except Exception:
        pass


def speak(
    text: str,
    interrupt: bool = True,
    *,
    channel: str | None = None,
    lv: float | None = None,
    rv: float | None = None,
) -> None:
    """Speak on a game voice library (or AO2 when primary + screen reader).

    Optional ``lv`` / ``rv`` (0..1) pan Nuance PCM. For SAPI, prefer
    ``synthesize_sound`` + pygame ``Channel.set_volume`` when pan is needed.
    """
    global _pending, _is_speaking, _end_time, _active_channel, _configured_voice
    global _configured_rate, _configured_volume, _configured_audio_output
    if not text:
        return
    assert isinstance(text, str)
    if channel is None:
        channel = passive_channel()
    else:
        channel = PRIMARY if channel == PRIMARY else SECONDARY
    remember_spoken(channel, text)
    gain_l, gain_r = _clamp_pan(lv, rv)

    # Dedicated SR owns primary duties — do not also drive Nuance/SAPI primary.
    if channel == PRIMARY:
        try:
            from . import tts as _ao2

            if _ao2.using_screen_reader():
                if interrupt:
                    try:
                        _ao2.stop()
                    except Exception:
                        pass
                    # Do not stop Nuance/secondary — in-match ops must not
                    # interrupt the secondary library (only Alt does).
                # Do not steal secondary's _active_channel / _end_time hold.
                if not is_speaking(SECONDARY):
                    with _lock:
                        _active_channel = PRIMARY
                        _is_speaking = True
                        _end_time = time.time() + _estimate_duration(text)
                _ao2.speak(text, interrupt=interrupt)
                return
        except Exception:
            pass

    from . import nuance_tts, voice_libs

    voice_libs.load_from_config()
    voice_id = voice_libs.get_voice(channel)
    rate_100 = voice_libs.get_rate(channel)
    volume = voice_libs.get_volume(channel)
    pitch = voice_libs.get_pitch(channel)
    device = voice_libs.get_device(channel)
    sapi_rate = voice_libs.sapi_rate_from_100(rate_100)

    # Same Nuance mouth cannot overlap: skip primary TTS while secondary holds it.
    if (
        channel == PRIMARY
        and interrupt
        and is_speaking(SECONDARY)
        and nuance_tts.is_nuance_voice(voice_id)
        and nuance_tts.is_nuance_voice(voice_libs.get_voice(SECONDARY))
    ):
        return

    if interrupt:
        # Only stop the same channel's backend path; never kill the other library.
        stop(channel=channel)

    _active_channel = channel
    _configured_voice = voice_id
    _configured_rate = sapi_rate
    _configured_volume = volume
    _configured_audio_output = device

    if nuance_tts.is_nuance_voice(voice_id):
        # Track in-flight Nuance helper; busy hold also uses _end_time.
        _channel_speaking[channel] = True
        with _lock:
            _is_speaking = True
            _end_time = time.time() + _estimate_duration(text)

        def _nu():
            try:
                try:
                    nuance_tts.set_audio_device(device)
                except Exception:
                    pass
                nuance_tts.speak(
                    text,
                    voice=voice_id,
                    rate=rate_100,
                    interrupt=True,
                    volume=volume,
                    pitch=pitch,
                    lv=gain_l,
                    rv=gain_r,
                )
            finally:
                _channel_speaking[channel] = False
                # Do not clear _end_time / _is_speaking here — keep VoiceChannel
                # busy for the estimated duration (classic AO2 pacing).

        threading.Thread(target=_nu, name=f"game-tts-{channel}", daemon=True).start()
        return

    # 32-bit-only SAPI (VW Julie, …): route through SysWOW64 helper.
    from . import voice_packs

    sapi_voice_id, _pack = voice_packs.resolve_sapi(voice_id)
    if not sapi_voice_id:
        sapi_voice_id = voice_id
    if needs_sapi32(sapi_voice_id):
        from . import sapi32_tts

        _channel_speaking[channel] = True
        with _lock:
            _is_speaking = True
            _end_time = time.time() + _estimate_duration(text)

        def _s32():
            try:
                sapi32_tts.speak(
                    text,
                    voice=sapi_voice_id,
                    rate=sapi_rate,
                    volume=int(volume),
                    interrupt=True,
                )
            finally:
                _channel_speaking[channel] = False

        threading.Thread(target=_s32, name=f"game-tts32-{channel}", daemon=True).start()
        return

    # SAPI path: busy is _pending + _end_time (classic AO2), not _channel_speaking.
    def _prep(spvoice):
        if spvoice is None:
            return False
        _apply_audio_output(spvoice, device)
        _apply_voice_token(spvoice, sapi_voice_id)
        _apply_rate(spvoice, sapi_rate)
        return True

    _run_on_worker(_prep)
    with _lock:
        _pending += 1
        _is_speaking = True
    _queue.put((_speak, [text, interrupt, volume]))


def synthesize_sound(text: str, *, channel: str | None = None):
    """Render SAPI TTS to a ``pygame.mixer.Sound`` for stereo pan.

    Returns ``None`` when the active library cannot render to a buffer
    (Nuance, screen reader, or helper failure). Caller should fall back to
    ``speak(..., lv=, rv=)`` for Nuance pan, or plain ``speak`` otherwise.
    """
    if not text:
        return None
    if channel is None:
        channel = passive_channel()
    else:
        channel = PRIMARY if channel == PRIMARY else SECONDARY
    remember_spoken(channel, text)

    if channel == PRIMARY:
        try:
            from . import tts as _ao2

            if _ao2.using_screen_reader():
                return None
        except Exception:
            pass

    from . import nuance_tts, voice_libs

    voice_libs.load_from_config()
    voice_id = voice_libs.get_voice(channel)
    if nuance_tts.is_nuance_voice(voice_id):
        return None

    rate_100 = voice_libs.get_rate(channel)
    volume = voice_libs.get_volume(channel)
    sapi_rate = voice_libs.sapi_rate_from_100(rate_100)
    from . import voice_packs

    sapi_voice_id, _pack = voice_packs.resolve_sapi(voice_id)
    if not sapi_voice_id:
        sapi_voice_id = voice_id
    if needs_sapi32(sapi_voice_id):
        try:
            from . import sapi32_tts

            path = sapi32_tts.speak_to_file(
                text,
                voice=sapi_voice_id,
                rate=sapi_rate,
                volume=int(volume),
            )
            if not path:
                return None
            try:
                import pygame

                return pygame.mixer.Sound(path)
            finally:
                try:
                    os.remove(path)
                except Exception:
                    pass
        except Exception:
            exception("sapi32 synthesize_sound failed")
            return None

    def _render(spvoice):
        if spvoice is None:
            return None
        import pygame
        import win32com.client

        fd, path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        stream = None
        prev_stream = None
        try:
            _apply_voice_token(spvoice, sapi_voice_id)
            _apply_rate(spvoice, sapi_rate)
            try:
                from . import sound as _sound

                base = max(0, min(100, int(float(_sound.voice_volume) * 100)))
            except Exception:
                base = 100
            spvoice.Volume = max(
                0, min(100, int(base * max(0, min(100, int(volume))) / 100))
            )
            stream = win32com.client.Dispatch("SAPI.SpFileStream")
            # SSFMCreateForWrite = 3
            stream.Open(path, 3)
            try:
                prev_stream = spvoice.AudioOutputStream
            except Exception:
                prev_stream = None
            spvoice.AudioOutputStream = stream
            # Synchronous speak into the WAV file.
            spvoice.Speak(str(text), 0)
            try:
                spvoice.AudioOutputStream = prev_stream
            except Exception:
                pass
            try:
                stream.Close()
            except Exception:
                pass
            stream = None
            return pygame.mixer.Sound(path)
        except Exception:
            exception("SAPI synthesize_sound failed for %r", text[:80])
            return None
        finally:
            if stream is not None:
                try:
                    spvoice.AudioOutputStream = prev_stream
                except Exception:
                    pass
                try:
                    stream.Close()
                except Exception:
                    pass
            try:
                os.remove(path)
            except Exception:
                pass

    return _run_on_worker(_render, timeout=60.0)


def _stop() -> None:
    global _is_speaking, _end_time
    if _voice is not None:
        try:
            _voice.Speak("", _PURGE_ASYNC)
        except Exception:
            pass
    with _lock:
        _is_speaking = False
        _end_time = None


def stop(channel: str | None = None) -> None:
    """Stop game voice. ``channel=None`` stops both libraries' engines.

    Per-channel stop must not silence the other library (in-match: ops on
    primary must leave secondary running until Alt / explicit secondary stop).
    """
    global _is_speaking, _end_time, _pending
    from . import nuance_tts

    if channel is None:
        try:
            from . import tts as _ao2

            if _ao2.using_screen_reader():
                _ao2.stop()
        except Exception:
            pass
        _channel_speaking[PRIMARY] = False
        _channel_speaking[SECONDARY] = False
        nuance_tts.stop()
        try:
            from . import sapi32_tts

            sapi32_tts.stop()
        except Exception:
            pass
        _queue.put((_stop, []))
        return

    channel = PRIMARY if channel == PRIMARY else SECONDARY
    _channel_speaking[channel] = False

    # Stop 32-bit helper only when this channel owns a 32-bit-only voice.
    try:
        from . import sapi32_tts, voice_libs

        voice_libs.load_from_config()
        if needs_sapi32(voice_libs.get_voice(channel)):
            sapi32_tts.stop()
    except Exception:
        pass

    if channel == PRIMARY:
        try:
            from . import tts as _ao2

            if _ao2.using_screen_reader():
                _ao2.stop()
        except Exception:
            pass

        # Drop busy hold immediately so VoiceChannel.get_busy() can exit
        # (e.g. opening-objective any-key skip). Mirror the secondary path.
        with _lock:
            if _active_channel == PRIMARY:
                _is_speaking = False
                _end_time = None
                _pending = 0

        # Shared Nuance mouth: stop only when secondary is not mid-utterance.
        try:
            from . import voice_libs

            voice_libs.load_from_config()
            if nuance_tts.is_nuance_voice(voice_libs.get_voice(PRIMARY)):
                if not _channel_speaking[SECONDARY]:
                    nuance_tts.stop()
        except Exception:
            pass

        def _purge_sapi_primary() -> None:
            if _voice is not None and _active_channel == PRIMARY:
                try:
                    _voice.Speak("", _PURGE_ASYNC)
                except Exception:
                    pass

        _queue.put((_purge_sapi_primary, []))
        return

    # secondary: stop Nuance and clear secondary busy hold
    nuance_tts.stop()

    def _purge_sapi_secondary() -> None:
        if _voice is not None and _active_channel == SECONDARY:
            try:
                _voice.Speak("", _PURGE_ASYNC)
            except Exception:
                pass

    _queue.put((_purge_sapi_secondary, []))
    with _lock:
        if _active_channel == SECONDARY:
            _is_speaking = False
            _end_time = None


def apply_library_profile(channel: str) -> None:
    """Apply saved primary/secondary profile (voice + rate + device) onto engines."""
    global _configured_voice, _configured_rate, _configured_volume, _configured_audio_output
    from . import nuance_tts, voice_libs

    voice_libs.load_from_config()
    channel = PRIMARY if channel == PRIMARY else SECONDARY
    voice_id = voice_libs.get_voice(channel)
    rate_100 = voice_libs.get_rate(channel)
    sapi_rate = voice_libs.sapi_rate_from_100(rate_100)
    device = voice_libs.get_device(channel)
    _configured_audio_output = device
    if channel == SECONDARY:
        _configured_voice = voice_id
        _configured_rate = sapi_rate
        _configured_volume = voice_libs.get_volume(channel)
    try:
        nuance_tts.set_audio_device(device)
    except Exception:
        pass
    if nuance_tts.is_nuance_voice(voice_id):
        return

    # 32-bit-only voices are applied on each speak() via sapi32 helper.
    try:
        if needs_sapi32(voice_id):
            return
    except Exception:
        pass

    def _apply(spvoice):
        if spvoice is None:
            return False
        _apply_audio_output(spvoice, device)
        _apply_voice_token(spvoice, voice_id)
        _apply_rate(spvoice, sapi_rate)
        return True

    _run_on_worker(_apply)


def _run_on_worker(fn, *args, timeout: float = 2.0):
    """Run ``fn(_voice, *args)`` on the SAPI thread and return its result."""
    if not _init_event.wait(timeout=timeout):
        return None
    done = threading.Event()
    box: dict = {"value": None}

    def _cmd():
        try:
            box["value"] = fn(_voice, *args)
        except Exception:
            exception("game_tts worker call failed")
            box["value"] = None
        finally:
            done.set()

    _queue.put((_cmd, []))
    done.wait(timeout=timeout)
    return box["value"]


def list_audio_outputs() -> list[str]:
    """Installed SAPI/Windows playback device descriptions."""

    def _list(spvoice):
        if spvoice is None:
            return []
        names = []
        try:
            outs = spvoice.GetAudioOutputs()
            for i in range(int(outs.Count)):
                names.append(str(outs.Item(i).GetDescription()))
        except Exception:
            exception("list SAPI audio outputs failed")
        return names

    return _run_on_worker(_list) or []


def set_audio_output(name: str) -> None:
    global _configured_audio_output
    _configured_audio_output = (name or "default").strip() or "default"
    _run_on_worker(_apply_audio_output, _configured_audio_output)


def list_sapi_voices() -> list[str]:
    """Return installed SAPI voice descriptions (64-bit + 32-bit-only)."""

    def _list(spvoice):
        if spvoice is None:
            return []
        names = []
        voices = spvoice.GetVoices()
        for i in range(int(voices.Count)):
            names.append(str(voices.Item(i).GetDescription()))
        return names

    names = list(_run_on_worker(_list) or [])
    # VW Julie etc. register under WOW6432Node only — merge 32-bit names.
    try:
        from . import sapi32_tts

        extra = []
        if sapi32_tts.available():
            try:
                extra = sapi32_tts.list_voices() or []
            except Exception:
                extra = sapi32_tts.list_wow6432_token_names()
        else:
            extra = sapi32_tts.list_wow6432_token_names()
        have = {n.lower() for n in names}
        for n in extra:
            if n and n.lower() not in have:
                names.append(n)
                have.add(n.lower())
    except Exception:
        pass
    return names


def needs_sapi32(voice_name: str) -> bool:
    """True when ``voice_name`` is only available via the 32-bit SAPI helper."""
    name = (voice_name or "").strip()
    if not name or name in (AUTO, DEFAULT):
        return False
    try:
        from . import voice_packs

        resolved, _pack = voice_packs.resolve_sapi(name)
        if resolved:
            name = resolved
    except Exception:
        pass
    name_low = name.lower()

    def _has_native(spvoice):
        if spvoice is None:
            return False
        try:
            voices = spvoice.GetVoices()
            for i in range(int(voices.Count)):
                desc = str(voices.Item(i).GetDescription())
                if (
                    desc == name
                    or desc.lower() == name_low
                    or name_low in desc.lower()
                    or desc.lower() in name_low
                ):
                    return True
        except Exception:
            return False
        return False

    if _run_on_worker(_has_native):
        return False
    try:
        from . import sapi32_tts

        for n in sapi32_tts.list_wow6432_token_names() or []:
            low = (n or "").lower()
            if name_low == low or name_low in low or low in name_low:
                return True
        if sapi32_tts.available():
            for n in sapi32_tts.list_voices() or []:
                low = (n or "").lower()
                if name_low == low or name_low in low or low in name_low:
                    return True
    except Exception:
        pass
    return False


def list_voices() -> list[str]:
    """SAPI descriptions only (menu also calls ``list_nuance_voices``)."""
    return list_sapi_voices()


def list_nuance_voices() -> list[str]:
    """Return Nuance voice ids like ``nuance:Ting-Ting`` (may be empty)."""
    from . import nuance_tts

    if not nuance_tts.available():
        return []
    try:
        return [nuance_tts.voice_id(v) for v in (nuance_tts.list_voices() or [])]
    except Exception:
        exception("list Nuance voices failed")
        return []


def current_voice() -> str:
    """Return the active configured voice id / SAPI description."""
    from . import nuance_tts

    if nuance_tts.is_nuance_voice(_configured_voice):
        return _configured_voice

    def _cur(spvoice):
        if spvoice is None:
            return ""
        try:
            return str(spvoice.Voice.GetDescription())
        except Exception:
            return ""

    return _run_on_worker(_cur) or ""


def get_configured_voice() -> str:
    return _configured_voice


def get_configured_rate() -> int:
    return _configured_rate


def set_voice(name: str, *, preview: bool = False) -> bool:
    """Select voice: ``auto``, ``default``, SAPI description, ``pack:…``, or ``nuance:Name``."""
    global _configured_voice
    from . import nuance_tts, voice_packs

    name = (name or AUTO).strip() or AUTO
    if nuance_tts.is_nuance_voice(name):
        _configured_voice = name
        if preview:
            speak("SoundRTS 语音测试", interrupt=True)
        return True

    # Resolve user/voices/*/voice.ini packs to a real SAPI description.
    sapi_name = name
    pack = None
    if voice_packs.is_pack_voice(name) or name.lower() not in (
        AUTO,
        DEFAULT,
    ):
        sapi_name, pack = voice_packs.resolve_sapi(name)
        if voice_packs.is_pack_voice(name) and not sapi_name:
            warning("voice pack not found: %r", name)
            return False
        if pack is not None:
            name = pack["id"]  # store stable pack id
            sapi_name = pack["sapi"]

    # 32-bit-only engines (VW Julie): accept selection without native SpVoice.
    if needs_sapi32(sapi_name):
        _configured_voice = name
        if preview:
            speak("SoundRTS 语音测试", interrupt=True)
        return True

    def _set(spvoice, n):
        if spvoice is None:
            return False
        ok = _apply_voice_token(spvoice, n)
        if ok:
            _apply_rate(spvoice, _configured_rate)
            if preview:
                try:
                    spvoice.Speak("SoundRTS 语音测试", _PURGE_ASYNC)
                except Exception:
                    pass
        return ok

    ok = bool(_run_on_worker(_set, sapi_name))
    if ok:
        _configured_voice = name
    elif pack is not None:
        warning(
            "voice pack %r needs installed SAPI voice matching %r",
            pack.get("title") or name,
            sapi_name,
        )
    return ok


def set_rate(rate: int, *, preview: bool = False) -> None:
    """Set rate (-10..10). Applies to SAPI immediately; Nuance uses it on next speak."""
    global _configured_rate
    from . import nuance_tts

    rate = max(-10, min(10, int(rate)))
    _configured_rate = rate
    if nuance_tts.is_nuance_voice(_configured_voice):
        if preview:
            speak("语速测试", interrupt=True)
        return

    def _set(spvoice, r):
        if spvoice is None:
            return False
        _apply_rate(spvoice, r)
        if preview:
            try:
                spvoice.Speak("语速测试", _PURGE_ASYNC)
            except Exception:
                pass
        return True

    _run_on_worker(_set, rate)


def apply_config(voice_name: str = AUTO, rate: int = 0) -> None:
    """Apply saved config after init (or when the user changes options)."""
    global _configured_voice, _configured_rate
    from . import nuance_tts

    _configured_voice = (voice_name or AUTO).strip() or AUTO
    _configured_rate = max(-10, min(10, int(rate)))
    if nuance_tts.is_nuance_voice(_configured_voice):
        return

    def _apply(spvoice):
        if spvoice is None:
            return False
        _apply_voice_token(spvoice, _configured_voice)
        _apply_rate(spvoice, _configured_rate)
        return True

    _run_on_worker(_apply)


def preview(text: str = "SoundRTS 语音测试") -> None:
    """Speak a short preview on the game voice."""
    speak(text or "SoundRTS 语音测试", interrupt=True)


def _apply_voice_token(spvoice, name: str) -> bool:
    if spvoice is None:
        return False
    name = (name or AUTO).strip() or AUTO
    if name == AUTO:
        _pick_chinese_voice(spvoice)
        return True
    if name == DEFAULT:
        try:
            import win32com.client

            fresh = win32com.client.Dispatch("SAPI.SpVoice")
            spvoice.Voice = fresh.Voice
            return True
        except Exception:
            return False
    try:
        from . import voice_packs

        resolved, _pack = voice_packs.resolve_sapi(name)
        if resolved:
            name = resolved
    except Exception:
        pass
    try:
        voices = spvoice.GetVoices()
        name_low = name.lower()
        for i in range(int(voices.Count)):
            tok = voices.Item(i)
            desc = str(tok.GetDescription())
            if desc == name or desc.lower() == name_low or name_low in desc.lower():
                spvoice.Voice = tok
                return True
    except Exception:
        exception("failed to set SAPI voice %r", name)
    return False


def _apply_rate(spvoice, rate: int) -> None:
    try:
        spvoice.Rate = max(-10, min(10, int(rate)))
    except Exception:
        pass


def _loop() -> None:
    global _voice, _available, _pending
    _voice = _create_voice_on_this_thread()
    _available = _voice is not None
    if _voice is None and sys.platform == "win32":
        warning("game voice SAPI init failed — important text may be silent")
    try:
        _apply_voice_token(_voice, _configured_voice)
        _apply_rate(_voice, _configured_rate)
    except Exception:
        pass
    _init_event.set()
    while True:
        cmd, args = _queue.get()
        if not _queue.empty() and cmd is _speak and (not args or args[-1] is True):
            with _lock:
                _pending = max(0, _pending - 1)
            continue
        try:
            cmd(*args)
        except Exception:
            exception("")


def _loop2() -> None:
    global _is_speaking
    while True:
        time.sleep(0.1)
        with _lock:
            timed_out = _end_time is None or _end_time <= time.time()
            engines_idle = not any(_channel_speaking.values())
            if _is_speaking and timed_out and _pending <= 0 and engines_idle:
                _is_speaking = False


def init(wait_delay_per_character: float = 0.05) -> None:
    global _lock, _pending, _is_speaking, _wait_delay, _end_time
    if _init_event.is_set():
        _wait_delay = float(wait_delay_per_character or 0.05)
        return
    _wait_delay = float(wait_delay_per_character or 0.05)
    _lock = threading.Lock()
    _pending = 0
    _is_speaking = False
    _end_time = None
    t = threading.Thread(target=_loop, name="game-tts", daemon=True)
    t.start()
    t = threading.Thread(target=_loop2, name="game-tts-watch", daemon=True)
    t.start()
    _init_event.wait(timeout=2.0)


def apply_config_from_module() -> None:
    """Read dual voice libraries from config and apply."""
    try:
        from . import voice_libs

        voice_libs.apply_all()
    except Exception:
        try:
            from .. import config

            apply_config(
                getattr(config, "game_voice", AUTO) or AUTO,
                getattr(config, "game_voice_rate", 0) or 0,
            )
        except Exception:
            apply_config(AUTO, 0)
