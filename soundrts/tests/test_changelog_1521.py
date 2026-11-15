# -*- coding: utf-8 -*-
"""审计：1.5.2.1 — 移除回滚快照网络协议，回到确定性锁步。

1.5.2.1 发布的内容是：
  * 删除整个 ``soundrts/net/`` 包（``rollback.py``、``snapshot.py``、
    ``session.py``、``input_stream.py``、``headless.py``）；
  * 删除协议协商与协议修订号（``negotiate_protocol``）；
  * 删除 ``input`` 命令、客户端预测与快照回滚循环；
  * 删除 ``use_rollback_netcode`` 配置项；
  * 删除「与对手不同步」的告警与结束本局路径；
  * **保留**回放格式的三个修复（每条指令独占一行、时间戳单调、
    读取端按时间排序并缓冲），因为它们与协议无关；
  * **保留** 1.5.1.9 的全部 AI 改动。

这些测试断言五种语言的发行说明都如实记录了上述内容，并且引擎侧确实
已经回到纯锁步。
"""

from __future__ import annotations

from pathlib import Path

from soundrts.version import VERSION

_LANGS = ("zh", "en", "es", "it", "pt-BR")

# 每个条目都必须在这五种语言的 1.5.2.1 段落里被点名。
_TOPICS = (
    # 被移除的东西
    "rollback",
    "lockstep",
    "soundrts/net/",
    "rollback.py",
    "snapshot.py",
    "session.py",
    "input_stream.py",
    "headless.py",
    "negotiate_protocol",
    "use_rollback_netcode",
    # 保留的东西
    "replay_read_line",
    "all_orders",
    "fpct",
    # 实测数字（逗号作小数点的语言单独处理）
    "260",
    "64",
    "300",
    # 测试
    "test_net_protocol.py",
    "test_net_lockstep_end_to_end.py",
)

# 小数：西班牙语 / 意大利语 / 葡萄牙语用逗号。
_DECIMALS = ("48.4", "10.9")


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_1521(lang: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("\n1.5.2.1\n")
    rest = text[start:]
    next_idx = rest.find("\n1.5.2.0\n")
    return rest if next_idx == -1 else rest[:next_idx]


def test_version_is_at_least_1521():
    """当前 VERSION 必须 >= 1.5.2.1。"""
    assert tuple(int(x) for x in VERSION.split(".")) >= (1, 5, 2, 1)


def test_all_relnotes_have_1521_before_1520_in_all_five_languages():
    """五种语言都必须有 1.5.2.1 段落，而且排在 1.5.2.0 之前。"""
    for lang in _LANGS:
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert "\n1.5.2.1\n" in src, (lang, "missing 1.5.2.1 header")
        assert src.index("\n1.5.2.1\n") < src.index("\n1.5.2.0\n"), lang
        assert src.index("\n1.5.2.0\n") < src.index("\n1.5.1.9\n"), lang


def test_relnotes_1521_document_every_session_topic():
    """五种语言的 1.5.2.1 段落都必须点名本次发布的每一项改动。"""
    for lang in _LANGS:
        section = _section_1521(lang)
        for topic in _TOPICS:
            assert topic in section, (lang, topic)
        # 小数点：西班牙语 / 意大利语 / 葡萄牙语用逗号。
        for number in _DECIMALS:
            assert number in section or number.replace(".", ",") in section, (
                lang,
                number,
            )


def test_relnotes_1521_document_the_measured_cost():
    """发行说明必须写明移除回滚的实测依据。"""
    for lang in _LANGS:
        section = _section_1521(lang)
        # 西班牙语 / 意大利语 / 葡萄牙语用逗号作小数点。
        assert "48.4" in section or "48,4" in section, lang
        assert "260" in section, lang
        assert "10.9" in section or "10,9" in section, lang
def test_the_rollback_package_is_gone():
    """整个 ``soundrts/net/`` 包必须已经删除。"""
    root = Path(__file__).resolve().parents[2]
    assert not (root / "soundrts" / "net").exists()


def test_the_protocol_negotiation_is_gone():
    """协议协商与协议修订号必须已经删除。"""
    version = _source("soundrts", "version.py")
    for name in (
        "LOCKSTEP_PROTOCOL",
        "ROLLBACK_PROTOCOL",
        "SUPPORTED_PROTOCOLS",
        "PROTOCOL_REVISIONS",
        "def protocol_revision(",
        "def protocol_token(",
        "def parse_protocol_token(",
        "def client_protocol(",
        "def client_protocol_token(",
        "def negotiate_protocol(",
    ):
        assert name not in version, name


def test_the_input_command_is_gone():
    """``input`` 命令必须已经删除。"""
    serverclient = _source("soundrts", "serverclient.py")
    assert "def cmd_input(" not in serverclient

    serverroom = _source("soundrts", "serverroom.py")
    assert '"input"' not in serverroom
    # 允许的命令里只剩锁步那套。
    assert '"orders"' in serverroom
    assert '"quit_game"' in serverroom


def test_the_rollback_setting_is_gone():
    """``use_rollback_netcode`` 配置项必须已经删除。"""
    config = _source("soundrts", "config.py")
    assert "use_rollback_netcode" not in config


def test_the_lockstep_path_is_intact():
    """锁步这条路的两个关键部件必须还在。"""
    serverroom = _source("soundrts", "serverroom.py")
    assert "class Orders" in serverroom
    assert "def are_ready(self" in serverroom
    assert "def pop_and_pack(self" in serverroom
    assert "all_orders" in serverroom

    worldclient = _source("soundrts", "worldclient.py")
    assert "def _give_all_orders(self" in worldclient
    assert "def orders_are_ready(self" in worldclient


def test_the_replay_format_fixes_are_kept():
    """回放格式的修复必须保留 —— 它们与协议无关。"""
    worldclient = _source("soundrts", "worldclient.py")
    assert "def _parse_replay_record(" in worldclient
    assert "def _parse_continuation(" in worldclient
    assert "for order in orders.split(\"\\n\"):" in worldclient
    assert "REPLAY_ORDER_KEYWORDS" in worldclient

    game = _source("soundrts", "game.py")
    assert "def replay_read_line(self)" in game


def test_the_ai_features_are_kept():
    """1.5.1.9 的 AI 改动必须原封不动地保留。"""
    economy = _source("soundrts", "world_ai_economy.py")
    for name in ("def balancing_tier(", "def expansion_headroom(",
                 "def population_is_pressured(", "def multi_queue_limit(",
                 "def extra_queue_budget(", "def read_bool_attr(",
                 "def read_int_attr("):
        assert name in economy, name

    computer = _source("soundrts", "worldplayercomputer.py")
    assert "def _blind_attack_targets(" in computer
    assert "world.random.choice" not in computer, (
        "the opening plan must not draw from the shared world RNG any more")


def test_the_benches_are_kept():
    """两个基准工具必须还在。"""
    root = Path(__file__).resolve().parents[2]
    assert (root / "bench_ai_features.py").exists()
    assert (root / "bench_jl1_sweep.py").exists()


def test_the_end_to_end_lockstep_test_exists():
    """端到端的锁步测试必须真的存在。"""
    root = Path(__file__).resolve().parents[2]
    assert (root / "soundrts" / "tests" / "test_net_lockstep_end_to_end.py").exists()
    assert (root / "soundrts" / "tests" / "test_net_protocol.py").exists()


def test_the_relative_import_guard_is_kept():
    """越出顶层包的相对导入检查必须常驻。"""
    root = Path(__file__).resolve().parents[2]
    guard = root / "soundrts" / "tests" / "test_relative_imports.py"
    assert guard.exists()
    text = guard.read_text(encoding="utf-8")
    assert "ast.ImportFrom" in text
    assert "node.level" in text
