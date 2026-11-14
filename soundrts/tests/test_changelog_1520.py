"""审计：1.5.2.0 — 回滚快照 / 分叉告警 / 回放格式的四个缺陷修复。

1.5.2.0 发布的内容是：
  * 修复"回滚倒回第 0 帧时游戏永久卡死"——快照把尚未初始化的计数器记成
    ``None``，还原后 ``None`` 遮蔽类属性，下一次模拟抛 ``TypeError``；
  * 修复"客户端悄悄与其他玩家分叉"——``unrecoverable_desync`` 标记了
    但没人读，现在会语音告警并结束本局；
  * 修复"回滚对局的回放根本放不出来"——多行指令写成了单行，读取时抛
    ``ValueError: invalid literal for int()``；
  * 修复"回放会在第一次回滚处卡住"——时间戳改为由帧号推导（单调），
    读取端改为按时间排序并施加"时间 ≤ 世界时间"的记录；
  * 新增 16 个回归测试 ``soundrts/tests/test_rollback_defects_regression.py``。

这些测试断言五种语言的发行说明都如实记录了上述内容，并且引擎侧确实
落地了对应的实现。
"""

from __future__ import annotations

from pathlib import Path

from soundrts.version import VERSION

_LANGS = ("zh", "en", "es", "it", "pt-BR")

# 每个条目都必须在这五种语言的 1.5.2.0 段落里被点名。
_TOPICS = (
    # 快照中毒
    "None",
    "_last_full_terrain_update",
    "_last_perception_cleanup",
    "previous_previous_state",
    "snapshot.py",
    "world_core.py",
    "TypeError",
    # 分叉告警
    "unrecoverable_desync",
    "worldclient.py",
    "game_interface_base.py",
    "game_input_handler.py",
    "64",
    # 回放格式
    "ValueError",
    "replay_read_line",
    "game.py",
    # 回归测试
    "test_rollback_defects_regression.py",
)


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_1520(lang: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("\n1.5.2.0\n")
    rest = text[start:]
    next_idx = rest.find("\n1.5.1.9\n")
    return rest if next_idx == -1 else rest[:next_idx]


def test_version_is_at_least_1520():
    """当前 VERSION 必须 >= 1.5.2.0。"""
    assert tuple(int(x) for x in VERSION.split(".")) >= (1, 5, 2, 0)


def test_all_relnotes_have_1520_before_1519_in_all_five_languages():
    """五种语言都必须有 1.5.2.0 段落，而且排在 1.5.1.9 之前。"""
    for lang in _LANGS:
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert "\n1.5.2.0\n" in src, (lang, "missing 1.5.2.0 header")
        assert src.index("\n1.5.2.0\n") < src.index("\n1.5.1.9\n"), lang
        assert src.index("\n1.5.1.9\n") < src.index("\n1.5.1.8\n"), lang


def test_relnotes_1520_document_every_session_topic():
    """五种语言的 1.5.2.0 段落都必须点名本次发布的每一项改动。"""
    for lang in _LANGS:
        section = _section_1520(lang)
        for topic in _TOPICS:
            assert topic in section, (lang, topic)


def test_relnotes_1520_document_the_snapshot_poison_fix():
    """快照中毒的修复必须写进发行说明。"""
    for lang in _LANGS:
        section = _section_1520(lang)
        assert "_last_full_terrain_update" in section, lang
        assert "_last_perception_cleanup" in section, lang
        assert "TypeError" in section, lang


def test_relnotes_1520_document_the_desync_alert():
    """分叉告警必须写进发行说明。"""
    for lang in _LANGS:
        section = _section_1520(lang)
        assert "unrecoverable_desync" in section, lang


def test_relnotes_1520_document_the_replay_fixes():
    """回放的两个修复必须写进发行说明。"""
    for lang in _LANGS:
        section = _section_1520(lang)
        assert "ValueError" in section, lang
        assert "replay_read_line" in section, lang


def test_engine_does_not_capture_missing_attributes():
    """快照不得把缺失的属性记成 ``None``。"""
    snapshot = _source("soundrts", "net", "snapshot.py")
    assert "if value is None:\n            continue" in snapshot
    # 还原那一侧也必须过滤 ``None``。
    assert "world.__dict__.pop(name, None)" in snapshot


def test_engine_ships_the_class_level_defaults():
    """按需初始化的计数器必须有类级默认值。"""
    world_core = _source("soundrts", "world", "world_core.py")
    assert "_last_full_terrain_update = 0" in world_core
    assert "_last_perception_cleanup = 0" in world_core
    assert "previous_previous_state = (0, b\"\")" in world_core


def test_engine_exposes_the_unrecoverable_desync():
    """协调器必须把分叉标记暴露出来。"""
    worldclient = _source("soundrts", "worldclient.py")
    assert "def has_unrecoverable_desync(" in worldclient
    assert "def unrecoverable_desync_stats(" in worldclient

    interface = _source("soundrts", "clientgame", "game_interface_base.py")
    assert "def check_unrecoverable_desync(" in interface
    assert "def _announce_desync(" in interface

    handler = _source("soundrts", "clientgame", "game_input_handler.py")
    assert "check_unrecoverable_desync" in handler


def test_engine_writes_one_replay_line_per_order():
    """回放写入端必须每条指令独占一行。"""
    worldclient = _source("soundrts", "worldclient.py")
    assert "for order in orders.split(\"\\n\"):" in worldclient
    assert "frame * VIRTUAL_TIME_INTERVAL" in worldclient
    assert "REPLAY_ORDER_KEYWORDS" in worldclient

    game = _source("soundrts", "game.py")
    assert "def replay_read_line(self)" in game


def test_the_regression_test_file_exists():
    """回归测试文件必须真的存在。"""
    root = Path(__file__).resolve().parents[2]
    assert (root / "soundrts" / "tests" / "test_rollback_defects_regression.py").exists()
