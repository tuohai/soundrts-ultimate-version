import time
from typing import Any, List, Optional, Tuple

import pygame

from .. import version
from . import game_tts, sound
from .message import is_text

DEBUG_MODE = version.IS_DEV_VERSION


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
            self.c.stop()
            self._queue = []

    def update(self):
        # Advance the *active* library's part queue; ignore the other library's TTS.
        if not self.c.get_busy() and not game_tts.is_speaking(self._tts_channel):
            if self._queue:
                self._play_next_msg_part()

    def _play_next_msg_part(self):
        s, lv, rv = self._queue.pop(0)
        if is_text(s):
            ch = getattr(self, "_tts_channel", None) or game_tts.passive_channel()
            game_tts.speak(s, channel=ch)
        else:
            self._play(s, lv, rv)

    def get_busy(self):
        return (
            self.c.get_busy()
            or self._queue
            or (self.c.get_queue() is not None)
            or game_tts.is_speaking(self._tts_channel)
        )

    def _play(self, s, lv, rv):
        # note: set_volume() doesn't seem to work with queued sounds
        v = sound.main_volume * sound.voice_volume
        self.c.set_volume(lv * v, rv * v)
        self.c.play(s)
        self.c.set_endevent(pygame.locals.USEREVENT)

    def __getstate__(self):
        state = self.__dict__.copy()
        state.pop("c", None)
        state.pop("_ops_channel", None)
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.c = pygame.mixer.Channel(0)
        self._ops_channel = None
        try:
            n = pygame.mixer.get_num_channels()
            if n > 2:
                self._ops_channel = pygame.mixer.Channel(n - 1)
        except Exception:
            self._ops_channel = None
