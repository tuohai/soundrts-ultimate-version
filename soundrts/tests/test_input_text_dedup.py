"""验证 ``clientmenu.input_text`` 在 KEYDOWN + TEXTINPUT 双路捕获下能正确去重.

历史 bug (用户报告 2026-05-26):
    在 Windows + pygame-ce 2.5.3 环境下, ``input_text`` 只用 SDL2 TEXTINPUT
    事件取字符. 但用户机器上 TEXTINPUT 不触发 → 按 Shift+Enter 打开输入框,
    输入 ``replay1`` 或拼音中文, 按 Enter 后 ``s`` 都是空 → ``_sanitize_filename``
    返回 None → 报 INVALID_NAME (用户称 "不可以的警报声").

修复后策略:
    1. KEYDOWN.e.unicode 即时进 ``s`` (保底 ASCII / 数字), 也入队 ``expected_queue``.
    2. TEXTINPUT 触发时, 若其文本是队头前缀 → dedup (出队, 不再加 s).
    3. TEXTINPUT 不匹配 → IME 提交场景, 把队列对应的 KEYDOWN 字符从 s 撤回,
       追加 TEXTINPUT 文本.

本测试通过 monkey-patch ``pygame.event.poll`` 喂事件流, 覆盖所有 4 个分支:
    case1: 只有 KEYDOWN (TEXTINPUT 不触发, 用户实际环境)
    case2: KEYDOWN + 匹配 TEXTINPUT (典型 SDL2 双触发, 需要 dedup)
    case3: KEYDOWN (IME 拼音) + 不匹配 TEXTINPUT (IME 提交, 需要撤回)
    case4: 只有 TEXTINPUT (IME 直接输出, 不经 KEYDOWN)
"""
from __future__ import annotations

import os
import sys
import types

import pytest

# 在导入 pygame 之前设置 dummy video driver, 避免 CI 上无显卡报错.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

# soundrts.options 在 import 时会 parse sys.argv. pytest 会传 -v / -q 等
# argparse 不认识的参数, 这里临时把 argv 改成只剩 prog name, 让 import 走完.
# 也要临时抑制 DeprecationWarning (pytest.ini 把 warning 升级成 error,
# 而 soundrts.lib.resource 在 import 时调了已 deprecated 的 locale.getdefaultlocale).
import warnings as _warnings
_saved_argv = sys.argv
sys.argv = [sys.argv[0]]
with _warnings.catch_warnings():
    _warnings.simplefilter("ignore")
    try:
        import pygame
        from pygame.locals import (
            KEYDOWN, K_BACKSPACE, K_ESCAPE, K_RETURN, TEXTINPUT,
        )
        # 提前 import 一次, 触发 options 模块的 argv 解析 (此时 argv 干净).
        from soundrts import clientmenu as _preload_clientmenu  # noqa: F401
    finally:
        sys.argv = _saved_argv


# ---------------------------------------------------------------------------
# 测试工具
# ---------------------------------------------------------------------------

def _make_event(event_type: int, **fields):
    """构造一个伪 pygame 事件 (有 .type / 字段属性即可)."""
    e = types.SimpleNamespace()
    e.type = event_type
    for k, v in fields.items():
        setattr(e, k, v)
    return e


def _keydown(key: int, unicode: str = "") -> object:
    return _make_event(KEYDOWN, key=key, unicode=unicode)


def _textinput(text: str) -> object:
    return _make_event(TEXTINPUT, text=text)


@pytest.fixture
def stub_input_env(monkeypatch):
    """Stub pygame.event.poll + voice + key.start/stop_text_input.

    返回一个函数 ``feed(events)``: 安排一串事件供 ``input_text`` 消费,
    序列耗尽后自动以 ``KEYDOWN K_RETURN`` 兜底, 让循环退出.
    """
    from soundrts import clientmenu

    queue: list[object] = []

    NOEVENT = _make_event(0)

    def fake_poll():
        if queue:
            return queue.pop(0)
        # 兜底: 强制返回 K_RETURN 让 input_text 退出, 避免死循环.
        return _keydown(K_RETURN)

    monkeypatch.setattr(pygame.event, "poll", fake_poll)
    monkeypatch.setattr(pygame.event, "clear", lambda *a, **k: None)
    monkeypatch.setattr(pygame.key, "start_text_input", lambda: None, raising=False)
    monkeypatch.setattr(pygame.key, "stop_text_input", lambda: None, raising=False)

    # voice stub: 静音 + 不依赖 pygame mixer.
    voice_stub = types.SimpleNamespace(
        menu=lambda *a, **k: None,
        item=lambda *a, **k: None,
        update=lambda *a, **k: None,
    )
    monkeypatch.setattr(clientmenu, "voice", voice_stub)

    def feed(events):
        queue.extend(events)

    return feed


# ---------------------------------------------------------------------------
# Case 1: 只有 KEYDOWN, TEXTINPUT 不触发 (用户实际环境)
# ---------------------------------------------------------------------------

def test_keydown_only_ascii(stub_input_env):
    """ASCII ``replay1`` 全部走 KEYDOWN.unicode, 应正确返回."""
    from soundrts.clientmenu import input_text

    events = [
        _keydown(0x72, unicode="r"),  # K_r
        _keydown(0x65, unicode="e"),  # K_e
        _keydown(0x70, unicode="p"),  # K_p
        _keydown(0x6c, unicode="l"),  # K_l
        _keydown(0x61, unicode="a"),  # K_a
        _keydown(0x79, unicode="y"),  # K_y
        _keydown(0x31, unicode="1"),  # K_1
        _keydown(K_RETURN),
    ]
    stub_input_env(events)
    result = input_text()
    assert result == "replay1"


def test_keydown_only_chinese_input_loses_data_gracefully(stub_input_env):
    """KEYDOWN.unicode 是拼音字母, 但没有 TEXTINPUT 提交 IME.

    这种情况现在无法恢复成中文 (Pygame 没给我们任何中文字符), 但至少
    不应该崩溃, 也不应该把字符全部丢掉 (要么留拼音, 要么留空).
    """
    from soundrts.clientmenu import input_text

    events = [
        _keydown(0x6e, unicode="n"),
        _keydown(0x69, unicode="i"),
        _keydown(K_RETURN),
    ]
    stub_input_env(events)
    result = input_text()
    # IME 没工作, 用户至少看到拼音 (聊胜于无).
    assert result == "ni"


# ---------------------------------------------------------------------------
# Case 2: KEYDOWN + 匹配 TEXTINPUT (典型 SDL2 双触发, 需要 dedup)
# ---------------------------------------------------------------------------

def test_keydown_and_matching_textinput_dedup(stub_input_env):
    """SDL2 标准行为: KEYDOWN 'a' 后跟 TEXTINPUT 'a'. 应只算一次."""
    from soundrts.clientmenu import input_text

    events = [
        _keydown(0x61, unicode="a"),
        _textinput("a"),
        _keydown(0x62, unicode="b"),
        _textinput("b"),
        _keydown(0x63, unicode="c"),
        _textinput("c"),
        _keydown(K_RETURN),
    ]
    stub_input_env(events)
    result = input_text()
    assert result == "abc"


def test_fast_typing_burst_then_textinput_burst(stub_input_env):
    """快速输入: 3 个 KEYDOWN 连发, 然后 3 个 TEXTINPUT 连发. 不应重复."""
    from soundrts.clientmenu import input_text

    events = [
        _keydown(0x61, unicode="a"),
        _keydown(0x62, unicode="b"),
        _keydown(0x63, unicode="c"),
        _textinput("a"),
        _textinput("b"),
        _textinput("c"),
        _keydown(K_RETURN),
    ]
    stub_input_env(events)
    result = input_text()
    assert result == "abc"


# ---------------------------------------------------------------------------
# Case 3: IME 拼音 (KEYDOWN 拼音字母 + 不匹配的 TEXTINPUT 提交字符)
# ---------------------------------------------------------------------------

def test_ime_commit_replaces_pinyin_keydowns(stub_input_env):
    """IME 拼音 'n' 'i' 'h' 'a' 'o' 后 commit '你好'.

    用户期望最终是 '你好', 而不是 'nihao你好'.
    """
    from soundrts.clientmenu import input_text

    events = [
        _keydown(0x6e, unicode="n"),
        _keydown(0x69, unicode="i"),
        _keydown(0x68, unicode="h"),
        _keydown(0x61, unicode="a"),
        _keydown(0x6f, unicode="o"),
        _textinput("你好"),  # IME 提交, 单事件多字符
        _keydown(K_RETURN),
    ]
    stub_input_env(events)
    result = input_text()
    assert result == "你好"


def test_mixed_ascii_then_ime(stub_input_env):
    """前缀 ASCII + 后续 IME 中文: ``a`` + IME ``你`` → ``a你``."""
    from soundrts.clientmenu import input_text

    events = [
        _keydown(0x61, unicode="a"),
        _textinput("a"),  # ASCII 双触发
        _keydown(0x6e, unicode="n"),
        _keydown(0x69, unicode="i"),
        _textinput("你"),  # IME 提交
        _keydown(K_RETURN),
    ]
    stub_input_env(events)
    result = input_text()
    assert result == "a你"


# ---------------------------------------------------------------------------
# Case 4: 只有 TEXTINPUT, 没有 KEYDOWN (某些 IME 直接走 TEXTINPUT)
# ---------------------------------------------------------------------------

def test_textinput_only(stub_input_env):
    from soundrts.clientmenu import input_text

    events = [
        _textinput("你好"),
        _keydown(K_RETURN),
    ]
    stub_input_env(events)
    result = input_text()
    assert result == "你好"


# ---------------------------------------------------------------------------
# Case 5: 控制键
# ---------------------------------------------------------------------------

def test_esc_returns_none(stub_input_env):
    from soundrts.clientmenu import input_text

    events = [
        _keydown(0x61, unicode="a"),
        _keydown(K_ESCAPE),
    ]
    stub_input_env(events)
    assert input_text() is None


def test_backspace_keydown_then_dedup(stub_input_env):
    """KEYDOWN 'a' 后 backspace, 再 'b'.

    backspace 必须把 expected_queue 也 pop, 否则后续 TEXTINPUT 'b' 会被
    认成 'a' 的重复 (因为队头还是 'a') → 漏掉 'b'.
    """
    from soundrts.clientmenu import input_text

    events = [
        _keydown(0x61, unicode="a"),
        _keydown(K_BACKSPACE),
        _keydown(0x62, unicode="b"),
        _textinput("b"),
        _keydown(K_RETURN),
    ]
    stub_input_env(events)
    result = input_text()
    assert result == "b"


def test_empty_return(stub_input_env):
    """没输入直接回车, 返回空串 (调用方再决定取消还是 INVALID_NAME)."""
    from soundrts.clientmenu import input_text

    stub_input_env([_keydown(K_RETURN)])
    assert input_text() == ""


# ---------------------------------------------------------------------------
# Case 6: 文件名禁用字符过滤
# ---------------------------------------------------------------------------

def test_forbidden_char_via_textinput_rejected(stub_input_env):
    """TEXTINPUT 给了 '/', 应被过滤掉."""
    from soundrts.clientmenu import input_text

    events = [
        _keydown(0x61, unicode="a"),
        _textinput("a"),
        _textinput("/"),  # 禁用字符
        _keydown(0x62, unicode="b"),
        _textinput("b"),
        _keydown(K_RETURN),
    ]
    stub_input_env(events)
    result = input_text()
    assert result == "ab"


# ---------------------------------------------------------------------------
# Case 7: max_length 截断
# ---------------------------------------------------------------------------

def test_max_length_via_keydown(stub_input_env):
    from soundrts.clientmenu import input_text

    events = [_keydown(0x61, unicode="a") for _ in range(10)]
    events.append(_keydown(K_RETURN))
    stub_input_env(events)
    result = input_text(max_length=5)
    assert result == "aaaaa"
