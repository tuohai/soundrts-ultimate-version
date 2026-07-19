import threading
import time
from typing import List

import pygame
from pygame.locals import K_LALT, K_RALT, KEYDOWN, KMOD_ALT

from .message import Message
from .sound import DEFAULT_VOLUME
from .voicechannel import VoiceChannel


class _Voice:

    msgs: List[Message] = []  # said and unsaid messages
    active = False  # currently talking (not just self.item())
    history = False  # in "history" mode
    muted = False  # suppress all speech (used during spectator catch-up fast-forward)
    current = 0  # index of the message currently said
    # == len(self.msgs) if no message

    def get_unsaid(
        self,
    ):  # index of the first never said message (== len(self.msgs) if no unsaid message)
        for i, m in enumerate(self.msgs):
            if not m.said:
                return i
        return len(self.msgs)

    unsaid = property(get_unsaid)

    def init(self, *args, **kwargs):
        self.lock = threading.Lock()
        self.channel = VoiceChannel(*args, **kwargs)

    def _start_current(self):
        # Full stop (incl. secondary) — used by Alt history skip / F5.
        self.channel.stop()
        self.active = False
        self.update()

    def previous(self):
        self.history = True
        if self.current > 0:
            self.current -= 1
        self._start_current()

    def _current_message_is_unsaid(self):
        return self._exists(self.current) and not self.msgs[self.current].said

    def _queue_msg_channel(self, msg) -> str:
        """Resolve which library a queued Message uses."""
        from . import game_tts as _game_tts

        ch = getattr(msg, "tts_channel", None) or _game_tts.passive_channel()
        if ch not in (_game_tts.PRIMARY, _game_tts.SECONDARY):
            return _game_tts.passive_channel()
        return ch

    def say_next(self, history_only=False, *, tts_channel=None):
        """Advance / stop the current queue line for one voice library.

        ``tts_channel``:
        - ``primary``: Left Alt — skip/stop the primary library only
        - ``secondary``: Right Alt — skip/stop the secondary library only
        - ``None``: legacy (treat as secondary in-match; full stop out of match)
        """
        from . import game_tts as _game_tts

        target = (
            tts_channel
            if tts_channel in (_game_tts.PRIMARY, _game_tts.SECONDARY)
            else None
        )
        if target is None and not history_only:
            # Unspecified Alt: keep old in-match meaning (filter secondary).
            target = (
                _game_tts.SECONDARY if _game_tts.in_match() else _game_tts.PRIMARY
            )
        # Secondary off: everything speaks on primary — both Alts skip primary.
        if (
            target == _game_tts.SECONDARY
            and (not _game_tts.in_match() or not _game_tts.secondary_voice_enabled())
        ):
            target = _game_tts.PRIMARY

        if self.active and self._exists(self.current):
            cur_ch = self._queue_msg_channel(self.msgs[self.current])
            if target is not None and cur_ch != target:
                # Wrong Alt for the active queue line: only silence that library
                # (e.g. Left Alt while a secondary enemy alert is speaking).
                self.channel.stop(tts_channel=target)
                return
            if self._current_message_is_unsaid():
                if history_only:
                    return
                self._mark_current_as_said()
                self.current += 1
            else:
                self.current += 1
            # Stop only the filtered library, then continue the queue.
            if target is not None:
                self.channel.stop(tts_channel=target)
                self.active = False
                self.update()
            else:
                self._start_current()
        elif self.history and history_only:
            # F6 after the current history line finished: keep browsing.
            if self.current + 1 < len(self.msgs):
                self.current += 1
                self._start_current()
            else:
                self.history = False
        elif not history_only:
            # No active queue line: stop leftover TTS on the filtered library.
            try:
                self.channel.stop(tts_channel=target or _game_tts.SECONDARY)
            except Exception:
                self.channel.stop()
            self.history = False

    def _exists(self, index):
        return index < len(self.msgs)

    def _unsaid_exists(self):
        return self._exists(self.unsaid)

    def alert(self, *args, **keywords):
        # Passive events → secondary in-match only; menus/lobby → primary.
        if "tts_channel" not in keywords:
            from . import game_tts as _game_tts

            keywords["tts_channel"] = _game_tts.passive_channel()
        self._say_now(interruptible=False, *args, **keywords)

    def important(self, *args, **keywords):
        if "tts_channel" not in keywords:
            from . import game_tts as _game_tts

            keywords["tts_channel"] = _game_tts.passive_channel()
        self._say_now(*args, **keywords)

    def confirmation(self, *args, **keywords):
        keywords.setdefault("tts_channel", "primary")
        self._say_now(keep_key=True, *args, **keywords)

    def menu(self, *args, **keywords):
        keywords.setdefault("tts_channel", "primary")
        self._say_now(keep_key=True, *args, **keywords)

    def info(self, list_of_sound_numbers, *args, **keywords):
        """Say sooner or later.

        By default the info queue uses the passive library (secondary in-match).
        Pass ``tts_channel="primary"`` for player-economy feedback that should
        not use the secondary library (unit/building complete, research,
        resources, menu-changed, …).
        """
        if self.muted:
            return
        if list_of_sound_numbers:
            self.msgs.append(Message(list_of_sound_numbers, *args, **keywords))
            self.update()

    def _say_now(
        self,
        list_of_sound_numbers,
        lv=DEFAULT_VOLUME,
        rv=DEFAULT_VOLUME,
        interruptible=True,
        keep_key=False,
        *,
        tts_channel=None,
    ):
        """Say now (give up saying sentences not said yet) until the end or a keypress.

        In-match: Right Alt may interrupt secondary; Left Alt may interrupt
        primary blocking lines. Other keys still interrupt primary (menus/ops).
        """
        if self.muted:
            return
        if list_of_sound_numbers:
            with self.lock:
                self._give_up_current_if_partially_said()
                from . import game_tts as _game_tts

                ch = (
                    tts_channel
                    if tts_channel in (_game_tts.PRIMARY, _game_tts.SECONDARY)
                    else _game_tts.PRIMARY
                )
                secondary_line = ch == _game_tts.SECONDARY and _game_tts.in_match()
                primary_line = ch == _game_tts.PRIMARY and _game_tts.in_match()
                self.channel.play(
                    Message(list_of_sound_numbers, lv, rv), tts_channel=ch
                )
                while self.channel.get_busy():
                    if interruptible:
                        if secondary_line:
                            if self._right_alt_hit(keep_key=keep_key):
                                self.channel.stop(tts_channel=_game_tts.SECONDARY)
                                break
                            # Left Alt: silence primary without abandoning secondary.
                            if self._left_alt_hit(keep_key=False):
                                self.channel.stop(tts_channel=_game_tts.PRIMARY)
                        elif primary_line:
                            if self._right_alt_hit(keep_key=keep_key):
                                if _game_tts.secondary_voice_enabled():
                                    self.channel.stop(
                                        tts_channel=_game_tts.SECONDARY
                                    )
                                else:
                                    # Secondary off: Right Alt also skips primary.
                                    self.channel.stop(
                                        tts_channel=_game_tts.PRIMARY
                                    )
                                    break
                            if self._left_alt_hit(keep_key=keep_key):
                                self.channel.stop(tts_channel=_game_tts.PRIMARY)
                                break
                            if self._non_alt_key_hit(keep_key=keep_key):
                                self.channel.stop(tts_channel=_game_tts.PRIMARY)
                                break
                        elif self._key_hit(keep_key=keep_key):
                            # Out-of-match / menus: any key skips and silences
                            # (1.3.8.1 only broke the wait; audio could linger).
                            self.channel.stop()
                            break
                    # Short sleep so opening-objective skip stays responsive.
                    time.sleep(0.02)
                    self.channel.update()
                if not interruptible:
                    pygame.event.get([KEYDOWN])
                self.msgs.append(Message(list_of_sound_numbers, lv, rv, said=True))
                self._go_to_next_unsaid()  # or next_current?
                self.active = False

    #                self.update()

    def _mark_current_as_said(self):
        self.msgs[self.current].said = True

    def _mark_unsaid_as_said(self):
        self.msgs[self.unsaid].said = True

    def _go_to_next_unsaid(self):
        self.current = self.unsaid

    def _give_up_current_if_partially_said(self):  # to avoid to many repetitions
        if self._current_message_is_unsaid() and self.channel.is_almost_done():
            self._mark_current_as_said()

    def item(self, list_of_sound_numbers, lv=DEFAULT_VOLUME, rv=DEFAULT_VOLUME):
        """Say now without recording (player ops → primary library).

        In-match with secondary enabled: ops speak on primary **alongside**
        secondary and must not stop/restart the secondary library (only Alt /
        history_stop may). When secondary is disabled (or out of match):
        classic preempt on the shared primary channel.
        """
        if self.muted:
            return
        if list_of_sound_numbers:
            with self.lock:
                from . import game_tts as _game_tts

                secondary_active = (
                    _game_tts.in_match()
                    and _game_tts.secondary_voice_enabled()
                    and self.active
                    and getattr(self.channel, "_tts_channel", None)
                    == _game_tts.SECONDARY
                    and self.channel.get_busy()
                )
                if secondary_active:
                    self.channel.play(
                        Message(list_of_sound_numbers, lv, rv),
                        tts_channel=_game_tts.PRIMARY,
                        parallel_primary=True,
                    )
                    self.history = False
                    return

                self._give_up_current_if_partially_said()
                self._go_to_next_unsaid()
                self.channel.play(
                    Message(list_of_sound_numbers, lv, rv),
                    tts_channel=_game_tts.PRIMARY,
                )
                self.active = False
                self.history = False

    def _expired(self, index):
        msg = self.msgs[index]
        if msg.has_expired():
            return True
        # look for a more recent message of the same type
        if msg.update_type is not None:
            for m in self.msgs[index + 1 :]:
                if m.update_type == msg.update_type:
                    return True
        # look for a more recent, identical message
        for m in self.msgs[index + 1 :]:
            if msg.list_of_sound_numbers == m.list_of_sound_numbers:
                return True
        return False

    def _mark_expired_messages_as_said(self):
        for i, m in enumerate(self.msgs):
            if not m.said and self._expired(i):
                m.said = True
        # limit the size of history
        if len(self.msgs) > 200:
            # truncate the list in place
            del self.msgs[:100]
            self.current -= 100
            self.current = max(0, self.current)

    def update(self):
        if self.channel.get_busy():
            self.channel.update()
        else:
            self._mark_expired_messages_as_said()
            if self.active:  # one message from the queue has just finished
                self._mark_current_as_said()
                self.current += 1
            if not self.history:
                self._go_to_next_unsaid()
            if self._exists(self.current):
                from . import game_tts as _game_tts

                msg = self.msgs[self.current]
                # Default: passive (secondary in-match). Per-message override
                # for primary-library economy / production feedback.
                ch = getattr(msg, "tts_channel", None) or _game_tts.passive_channel()
                if ch not in (_game_tts.PRIMARY, _game_tts.SECONDARY):
                    ch = _game_tts.passive_channel()
                self.channel.play(msg, tts_channel=ch)
                self.active = True
            else:
                self.active = False
                self.history = False

    def silent_flush(self):
        self.channel.stop()
        self.active = False
        self.current = len(self.msgs)
        for m in self.msgs:
            m.said = True

    def flush(self, interruptible=True):
        while True:
            self.update()
            if not (self._unsaid_exists() or self.channel.get_busy()):
                break
            elif (
                interruptible and self._key_hit()
            ):  # keep_key=False? (and remove next line?)
                if self._unsaid_exists():
                    self.say_next()
                    pygame.event.get([KEYDOWN])  # consequence: _key_hit() == False
                else:
                    break
            time.sleep(0.1)
        if not interruptible:
            pygame.event.get([KEYDOWN])

    def _key_hit(self, keep_key=True):
        l = pygame.event.get([KEYDOWN])
        if keep_key and l:
            # Only re-queue the first KEYDOWN. Keyboard auto-repeat (and some
            # IME stacks) can leave several KEYDOWNs in the queue while a menu
            # title is spoken; posting them all back would jump twice on one
            # physical press (e.g. m1 then immediately m2).
            pygame.event.post(l[0])
        return len(l) != 0

    def _non_alt_key_hit(self, keep_key=True) -> bool:
        """True if a non-Alt KEYDOWN arrived (Alt is handled separately)."""
        events = pygame.event.get([KEYDOWN])
        alts = [e for e in events if e.key in (K_LALT, K_RALT)]
        others = [e for e in events if e not in alts]
        for e in alts:
            pygame.event.post(e)
        if keep_key and others:
            pygame.event.post(others[0])
            for e in others[1:]:
                pygame.event.post(e)
        elif others:
            for e in others[1:]:
                pygame.event.post(e)
        return bool(others)

    def _alt_side_hit(self, *, left: bool, keep_key=True) -> bool:
        """True if the matching Alt was pressed; re-queue other KEYDOWNs."""
        want = K_LALT if left else K_RALT
        events = pygame.event.get([KEYDOWN])
        hit = [e for e in events if e.key == want]
        other = [e for e in events if e not in hit]
        for e in other:
            pygame.event.post(e)
        if keep_key and hit:
            pygame.event.post(hit[0])
        return bool(hit)

    def _left_alt_hit(self, keep_key=True) -> bool:
        """Left Alt — filter / interrupt the primary library."""
        return self._alt_side_hit(left=True, keep_key=keep_key)

    def _right_alt_hit(self, keep_key=True) -> bool:
        """Right Alt — filter / interrupt the secondary library."""
        return self._alt_side_hit(left=False, keep_key=keep_key)

    def _alt_hit(self, keep_key=True):
        """True if either Alt was pressed (legacy helper)."""
        events = pygame.event.get([KEYDOWN])
        alt_events = [
            e
            for e in events
            if e.key in (K_LALT, K_RALT) or (getattr(e, "mod", 0) & KMOD_ALT)
        ]
        other = [e for e in events if e not in alt_events]
        for e in other:
            pygame.event.post(e)
        if keep_key and alt_events:
            pygame.event.post(alt_events[0])
        return bool(alt_events)


voice = _Voice()
