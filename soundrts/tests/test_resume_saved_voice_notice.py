"""手动取消游戏时，"已保留进度" 提示必须完整播完。

回归：``voice.discard_pending()`` 会把整个语音队列（含 primary）标记为
已播并丢掉。手动取消游戏时 ``_try_save_resume()`` 刚刚排入队列的
"已保留进度，下次可继续未完成的游戏"（mp.RESUME_SAVED）因此被截断，
玩家听不到任何保存成功的反馈，以为没有保存。
"""
from __future__ import annotations

import os
import sys
import threading
import warnings

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

_saved_argv = sys.argv
sys.argv = [sys.argv[0]]
try:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from soundrts.lib.voice import _Voice
        from soundrts.lib.message import Message
finally:
    sys.argv = _saved_argv

import soundrts.lib.game_tts as game_tts


class _FakeChannel:
    """记录 play/stop 调用的假 VoiceChannel。"""

    def __init__(self):
        self.stopped = []
        self.played = []
        self._tts_channel = game_tts.PRIMARY

    def play(self, msg, *, tts_channel=None, parallel_primary=False):
        self.played.append(tts_channel)
        self._tts_channel = tts_channel or game_tts.PRIMARY

    def stop(self, *, tts_channel=None):
        self.stopped.append(tts_channel)
        if tts_channel == self._tts_channel:
            self._tts_channel = game_tts.PRIMARY

    def get_busy(self):
        return False

    def update(self):
        pass

    def is_almost_done(self):
        return True


def _voice():
    v = _Voice.__new__(_Voice)
    v.lock = threading.Lock()
    v.channel = _FakeChannel()
    v.msgs = []
    v.active = False
    v.history = False
    v.muted = False
    v.speech_enabled = True
    v.current = 0
    # pygame 未初始化时 flush() 的按键检测会抛错，这里直接屏蔽。
    v._key_hit = lambda *a, **k: False
    return v


# ---------------------------------------------------------------- flush_primary


def test_flush_primary_speaks_the_primary_message():
    v = _voice()
    v.msgs = [Message([4993], said=False, tts_channel=game_tts.PRIMARY)]
    v.current = 0

    v.flush_primary()

    assert v.channel.played == [game_tts.PRIMARY]
    assert all(m.said for m in v.msgs)


def test_flush_primary_drops_the_passive_backlog():
    v = _voice()
    v.msgs = [Message([1], said=False)] * 30  # passive → secondary in-match
    v.msgs.append(Message([4993], said=False, tts_channel=game_tts.PRIMARY))
    v.current = 0

    old = game_tts.in_match()
    try:
        game_tts.set_in_match(True)
        v.flush_primary()
    finally:
        game_tts.set_in_match(old)

    # 只播了 primary 那一条，30 条 passive 战斗播报被丢掉。
    assert v.channel.played == [game_tts.PRIMARY]
    assert v.msgs[-1].said is True


def test_flush_primary_stops_only_the_secondary_library():
    v = _voice()
    v.msgs = [Message([4993], said=False, tts_channel=game_tts.PRIMARY)]
    v.current = 0

    v.flush_primary()

    assert v.channel.stopped == [game_tts.SECONDARY]


def test_flush_primary_drops_passive_messages_that_arrive_during_the_flush():
    """播报期间新到的 passive 战斗播报必须被丢掉，不能拖慢退出。"""
    v = _voice()
    v.msgs = [Message([4993], said=False, tts_channel=game_tts.PRIMARY)]
    v.current = 0

    real_update = v.update
    calls = {"n": 0}

    def _update():
        real_update()
        calls["n"] += 1
        # 第一次 update 之后，对局线程又塞进来一条 passive 消息。
        if calls["n"] == 1:
            v.msgs.append(Message([1], said=False))

    v.update = _update

    old = game_tts.in_match()
    try:
        game_tts.set_in_match(True)
        v.flush_primary(interruptible=False)
    finally:
        game_tts.set_in_match(old)

    # 只有 primary 那一条被播了。
    assert v.channel.played == [game_tts.PRIMARY]
    # 新塞进来的 passive 消息被标为已播（丢弃）。
    assert v.msgs[-1].said is True


def test_flush_primary_does_nothing_without_primary_messages():
    v = _voice()
    v.msgs = [Message([1], said=False)]
    v.current = 0

    old = game_tts.in_match()
    try:
        game_tts.set_in_match(True)
        v.flush_primary()
    finally:
        game_tts.set_in_match(old)

    assert v.channel.played == []


# -------------------------------------------------------------- say_primary_now


def test_say_primary_now_speaks_on_the_primary_library():
    v = _voice()

    v.say_primary_now([4993])

    assert v.channel.played == [game_tts.PRIMARY]
    assert all(m.said for m in v.msgs)


def test_say_primary_now_drops_the_passive_backlog_first():
    """先停 secondary 再排队：secondary 占着 Nuance 嘴时 primary 会被跳过。"""
    v = _voice()
    v.msgs = [Message([1], said=False)] * 30  # passive → secondary in-match
    v.current = 0

    old = game_tts.in_match()
    try:
        game_tts.set_in_match(True)
        v.say_primary_now([4993])
    finally:
        game_tts.set_in_match(old)

    # 只播了 primary 那一条。
    assert v.channel.played == [game_tts.PRIMARY]
    # 30 条 passive 战斗播报被丢掉（且没有 secondary 被播）。
    assert all(m.said for m in v.msgs)
    assert game_tts.SECONDARY not in v.channel.played


def test_say_primary_now_stops_the_secondary_library_before_queueing():
    v = _voice()

    v.say_primary_now([4993])

    # stop(SECONDARY) 必须在 play(PRIMARY) 之前发生。
    assert game_tts.SECONDARY in v.channel.stopped
    assert v.channel.stopped.index(game_tts.SECONDARY) == 0
    assert v.channel.played == [game_tts.PRIMARY]


def test_say_primary_now_uses_the_primary_channel_by_default():
    v = _voice()
    v.say_primary_now([4993])
    assert v.msgs[-1].tts_channel == game_tts.PRIMARY


# ------------------------------------------------------------- discard_pending


def test_discard_pending_still_drops_everything():
    """discard_pending() 保持原语义：整条队列丢掉（失败后快速退出）。"""
    v = _voice()
    v.msgs = [Message([4993], said=False, tts_channel=game_tts.PRIMARY)]
    v.current = 0

    v.discard_pending()

    assert all(m.said for m in v.msgs)
    assert v.current == len(v.msgs)


# ------------------------------------------------------------------- 源码检查


def test_resume_saved_notice_is_spoken_synchronously_on_primary():
    """``_try_save_resume`` 必须同步播完 primary 提示。"""
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    src = (root / "clientgame" / "game_resources.py").read_text(encoding="utf-8")
    block = src.split("def _try_save_resume", 1)[1].split("\ndef ", 1)[0]
    assert "_speak_resume_saved_notice()" in block

    notice = src.split("def _speak_resume_saved_notice", 1)[1].split("\ndef ", 1)[0]
    assert "mp.RESUME_SAVED" in notice
    assert "voice.say_primary_now(mp.RESUME_SAVED)" in notice


def test_gm_quit_speaks_the_notice_before_asking_the_server_to_quit():
    """播完提示之后才让服务端退出，否则 srv_quit 会把提示丢掉。"""
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    src = (root / "clientgame" / "game_resources.py").read_text(encoding="utf-8")
    block = src.split("def gm_quit", 1)[1].split("\ndef ", 1)[0]
    assert block.index("_try_save_resume(interface)") < block.index('write_line("quit")')
