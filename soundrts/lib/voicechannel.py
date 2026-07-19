import threading
import time
from typing import Any, Callable, List, Optional, Tuple

import pygame

from .. import version
from . import game_tts, sound
from .message import is_text
from .sound import DEFAULT_VOLUME

DEBUG_MODE = version.IS_DEV_VERSION

PanFn = Callable[[], Tuple[float, float]]


def _wants_spatial_tts(lv: float, rv: float, pan_fn=None) -> bool:
    """True when message volumes imply a directional (non-centered) cue."""
    if pan_fn is not None:
        return True
    try:
        left = float(lv)
        right = float(rv)
    except Exception:
        return False
    return abs(left - right) > 0.02 or min(left, right) < DEFAULT_VOLUME - 0.05


def _clamp_pan(lv: float, rv: float) -> Tuple[float, float]:
    try:
        left = max(0.0, min(1.0, float(lv)))
    except Exception:
        left = DEFAULT_VOLUME
    try:
        right = max(0.0, min(1.0, float(rv)))
    except Exception:
        right = DEFAULT_VOLUME
    return left, right


class VoiceChannel:
    _queue: List[Tuple[Any, float, float]] = []  # sounds of the message currently said
    _starting_time = 0
    _total_duration = 0
    _tts_channel = game_tts.PRIMARY
    _ops_channel: Optional[pygame.mixer.Channel] = None

    def __init__(self, config=None):
        self.c = pygame.mixer.Channel(0)
        # Ops SFX alongside secondary: use the *last* mixer channel so we do
        # not collide with psounds (menu browse SFX starts at channel 1).
        self._ops_channel = None
        try:
            n = pygame.mixer.get_num_channels()
            if n > 2:
                self._ops_channel = pygame.mixer.Channel(n - 1)
        except Exception:
            self._ops_channel = None
        delay = getattr(config, "wait_delay_per_character", 0.05) if config else 0.05
        # Classic dual libraries: game_tts for text; keep AO2 tts for helpers.
        from . import tts

        game_tts.init(delay)
        tts.init(delay)
        self._tts_channel = game_tts.PRIMARY
        self._spatial_gen = 0
        self._spatial_busy = False
        self._spatial_ready: Optional[Tuple[Any, float, float]] = None
        self._active_pan_fn: Optional[PanFn] = None
        # "pygame_tts" | "pygame_sfx" | "nuance" | None
        self._live_pan_backend: Optional[str] = None
        self._last_live_pan: Optional[Tuple[float, float]] = None

    def play(self, msg, *, tts_channel: str | None = None, parallel_primary: bool = False):
        if DEBUG_MODE:
            msg.display()
        # Primary = ops / out-of-match; secondary = in-match passive only.
        if tts_channel is None:
            tts_channel = game_tts.passive_channel()
        want_primary = tts_channel == game_tts.PRIMARY
        # In-match: ops (primary) must not stop an active secondary line.
        if (
            parallel_primary
            and want_primary
            and self._tts_channel == game_tts.SECONDARY
            and self.get_busy()
        ):
            self._play_primary_parallel(msg)
            return
        self.stop()
        self._tts_channel = (
            game_tts.PRIMARY if want_primary else game_tts.SECONDARY
        )
        self._active_pan_fn = getattr(msg, "pan_fn", None)
        for p in msg.translate_and_collapse():
            self._queue.append((p, msg.lv, msg.rv))
        self.update()
        self._starting_time = time.time()

    def _play_primary_parallel(self, msg) -> None:
        """Speak primary ops without clearing the secondary VoiceChannel queue."""
        for p in msg.translate_and_collapse():
            if is_text(p):
                game_tts.speak(p, channel=game_tts.PRIMARY)
            else:
                self._play_ops_sfx(p, msg.lv, msg.rv)

    def _play_ops_sfx(self, s, lv, rv) -> None:
        ch = self._ops_channel or self.c
        v = sound.main_volume * sound.voice_volume
        try:
            ch.set_volume(lv * v, rv * v)
            ch.play(s)
        except Exception:
            self._play(s, lv, rv)

    def is_almost_done(self):
        duration = time.time() - self._starting_time
        if duration > 1:  # >1s
            return True
        else:
            return False

    def _cancel_spatial(self) -> None:
        self._spatial_gen += 1
        self._spatial_busy = False
        self._spatial_ready = None
        self._active_pan_fn = None
        self._live_pan_backend = None
        self._last_live_pan = None

    def stop(self, *, tts_channel: str | None = None):
        """Stop mixer queue and TTS.

        ``tts_channel=None``: stop voice channel 0 + all TTS (legacy).
        Do **not** stop ``_ops_channel`` here — it sits in the SFX pool
        (channels 1+). Stopping it on every ``play()`` killed menu browse
        SFX that had just started on channel 1.

        ``tts_channel=primary|secondary``: stop that library only; clear the
        part queue only when it belongs to that library.
        """
        if tts_channel is None:
            self._cancel_spatial()
            self.c.stop()
            game_tts.stop()
            self._queue = []
            return
        ch = (
            game_tts.PRIMARY
            if tts_channel == game_tts.PRIMARY
            else game_tts.SECONDARY
        )
        game_tts.stop(channel=ch)
        if ch == game_tts.PRIMARY and self._ops_channel is not None:
            try:
                self._ops_channel.stop()
            except Exception:
                pass
        if self._tts_channel == ch:
            self._cancel_spatial()
            self.c.stop()
            self._queue = []

    def update(self):
        self._refresh_live_pan()
        # Finish a background SAPI render before advancing the part queue.
        if self._spatial_ready is not None and not self.c.get_busy():
            snd, lv, rv = self._spatial_ready
            self._spatial_ready = None
            self._spatial_busy = False
            # Re-resolve pan at playback start (player may have moved while rendering).
            if self._active_pan_fn is not None:
                try:
                    lv, rv = self._active_pan_fn()
                except Exception:
                    pass
            self._play_spatial_tts(snd, lv, rv)
            return
        # Advance the *active* library's part queue; ignore the other library's TTS.
        if (
            not self.c.get_busy()
            and not self._spatial_busy
            and not game_tts.is_speaking(self._tts_channel)
        ):
            if self._queue:
                self._play_next_msg_part()

    def _resolve_part_pan(self, lv: float, rv: float) -> Tuple[float, float]:
        if self._active_pan_fn is not None:
            try:
                return _clamp_pan(*self._active_pan_fn())
            except Exception:
                pass
        return _clamp_pan(lv, rv)

    def _refresh_live_pan(self) -> None:
        """Update left/right gains while an utterance is still playing."""
        if self._active_pan_fn is None or self._live_pan_backend is None:
            return
        busy = self.c.get_busy() or game_tts.is_speaking(self._tts_channel)
        if not busy and not self._spatial_busy:
            return
        try:
            lv, rv = _clamp_pan(*self._active_pan_fn())
        except Exception:
            return
        prev = self._last_live_pan
        if (
            prev is not None
            and abs(prev[0] - lv) < 0.02
            and abs(prev[1] - rv) < 0.02
        ):
            return
        self._last_live_pan = (lv, rv)
        backend = self._live_pan_backend
        if backend == "pygame_tts" and self.c.get_busy():
            self.c.set_volume(lv, rv)
        elif backend == "pygame_sfx" and self.c.get_busy():
            v = sound.main_volume * sound.voice_volume
            self.c.set_volume(lv * v, rv * v)
        elif backend == "nuance":
            try:
                game_tts.set_pan(lv, rv)
            except Exception:
                pass

    def _play_next_msg_part(self):
        s, lv, rv = self._queue.pop(0)
        lv, rv = self._resolve_part_pan(lv, rv)
        if is_text(s):
            ch = getattr(self, "_tts_channel", None) or game_tts.passive_channel()
            if _wants_spatial_tts(lv, rv, self._active_pan_fn):
                self._play_spatial_text(s, ch, lv, rv)
            else:
                self._live_pan_backend = None
                game_tts.speak(s, channel=ch)
        else:
            self._play(s, lv, rv)

    def _play_spatial_text(self, text: str, channel: str, lv: float, rv: float) -> None:
        """Pan TTS: Nuance via helper gains; SAPI via background WAV + pygame."""
        try:
            from . import nuance_tts, voice_libs

            voice_libs.load_from_config()
            voice_id = voice_libs.get_voice(channel)
            if nuance_tts.is_nuance_voice(voice_id):
                self._live_pan_backend = "nuance"
                self._last_live_pan = (lv, rv)
                game_tts.speak(text, channel=channel, lv=lv, rv=rv)
                return
        except Exception:
            pass

        # SAPI / sapi32: synthesize off the UI thread, then pan on channel 0.
        self._spatial_gen += 1
        gen = self._spatial_gen
        self._spatial_busy = True
        self._spatial_ready = None
        self._live_pan_backend = "pygame_tts"

        def _work():
            snd = None
            try:
                snd = game_tts.synthesize_sound(text, channel=channel)
            except Exception:
                snd = None
            if gen != self._spatial_gen:
                return
            if snd is not None:
                # Pan may be refreshed again in update() before play.
                self._spatial_ready = (snd, lv, rv)
            else:
                self._spatial_busy = False
                self._live_pan_backend = None
                game_tts.speak(text, channel=channel)

        threading.Thread(target=_work, name="spatial-tts", daemon=True).start()

    def get_busy(self):
        return (
            self.c.get_busy()
            or self._spatial_busy
            or self._spatial_ready is not None
            or self._queue
            or (self.c.get_queue() is not None)
            or game_tts.is_speaking(self._tts_channel)
        )

    def _play(self, s, lv, rv):
        # note: set_volume() doesn't seem to work with queued sounds
        if self._active_pan_fn is not None:
            self._live_pan_backend = "pygame_sfx"
            self._last_live_pan = (lv, rv)
        else:
            self._live_pan_backend = None
        v = sound.main_volume * sound.voice_volume
        self.c.set_volume(lv * v, rv * v)
        self.c.play(s)
        self.c.set_endevent(pygame.locals.USEREVENT)

    def _play_spatial_tts(self, s, lv, rv):
        """Play a pre-rendered TTS buffer with stereo pan.

        Volume is already baked into the WAV (same as live SAPI Speak), so only
        apply left/right balance here — not ``main_volume * voice_volume`` again.
        """
        lv, rv = _clamp_pan(lv, rv)
        self._live_pan_backend = "pygame_tts"
        self._last_live_pan = (lv, rv)
        self.c.set_volume(lv, rv)
        self.c.play(s)
        self.c.set_endevent(pygame.locals.USEREVENT)

    def __getstate__(self):
        state = self.__dict__.copy()
        state.pop("c", None)
        state.pop("_ops_channel", None)
        state.pop("_spatial_ready", None)
        state.pop("_active_pan_fn", None)
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.c = pygame.mixer.Channel(0)
        self._ops_channel = None
        self._spatial_gen = 0
        self._spatial_busy = False
        self._spatial_ready = None
        self._active_pan_fn = None
        self._live_pan_backend = None
        self._last_live_pan = None
        try:
            n = pygame.mixer.get_num_channels()
            if n > 2:
                self._ops_channel = pygame.mixer.Channel(n - 1)
        except Exception:
            self._ops_channel = None
