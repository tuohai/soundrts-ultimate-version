"""审计：1.5.1.9 — 回滚网络协议、AI 流水线补兵 / 经济调度 / 基地管理。

1.5.1.9 发布的内容是：
  * 新的主机权威回滚网络协议（分 0-6 阶段），取代"等最慢玩家"的锁步，
    并且成为默认协议；
  * 分层世界快照与强摘要（``soundrts/net/snapshot.py``）；
  * 协议协商与协议修订号（``<protocol>/<revision>``）；
  * 回滚协议下的实时旁观模式；
  * 修复玩家退出后客户端与服务器 / 旁观者分叉的四个缺陷；
  * 修复越出顶层包的相对导入（"建立服务器时提示连接错误"）；
  * 修复地图文件句柄泄漏；
  * 修复热键测试依赖本机物理 Shift 键状态；
  * AI 同时让多个生产建筑忙起来（多队列）；
  * AI 把工人分散到各个采集来源；
  * AI 自动管理主基地数量；
  * 新增规则驱动的 AI 经济策略模块 ``soundrts/world_ai_economy.py``；
  * 修复人口压力判断从来没有触发过；
  * 修复多队列上限把"总数"当成了"额外队列数"；
  * AI 从未见过敌人时也能主动进攻（盲攻回退）；
  * AI 的开局分支不再被"是否派村民探索"随机重掷；
  * 两个无头基准工具与网络协议计划文档。

这些测试断言五种语言的发行说明都如实记录了上述内容，并且引擎侧确实
落地了对应的实现。
"""

from __future__ import annotations

from pathlib import Path

from soundrts.version import VERSION

_LANGS = ("zh", "en", "es", "it", "pt-BR")

# 每个条目都必须在这五种语言的 1.5.1.9 段落里被点名。
_TOPICS = (
    # 回滚网络协议
    "rollback",
    "lockstep",
    "use_rollback_netcode",
    "strong_digest",
    "negotiate_protocol",
    "snapshot.py",
    "SpectatorSession",
    # 网络修复
    "attempted relative import beyond top-level package",
    "mapfile.py",
    "test_hotkey_editor.py",
    # AI 经济
    "world_ai_economy.py",
    "effective_can_train",
    "multi_queue_limit",
    "expansion_headroom",
    "population_is_pressured",
    "ai_base_worth_expanding",
    "balancing_tier",
    # AI 进攻时机
    "_blind_attack_targets",
    "_map_start_square",
    "goto_random",
    "auto_explore",
    # 工具与文档
    "bench_ai_features.py",
    "bench_jl1_sweep.py",
    "_NET_ROLLBACK_PLAN.md",
    # 新测试
    "test_net_rollback_live.py",
    "test_ai_economy_scheduling.py",
    "test_ai_jl1_blind_attack.py",
    "test_ai_plan_rng_decoupled.py",
)


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_1519(lang: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("\n1.5.1.9\n")
    rest = text[start:]
    next_idx = rest.find("\n1.5.1.8\n")
    return rest if next_idx == -1 else rest[:next_idx]


def test_version_is_at_least_1519():
    """当前 VERSION 必须 >= 1.5.1.9。"""
    assert tuple(int(x) for x in VERSION.split(".")) >= (1, 5, 1, 9)


def test_all_relnotes_have_1519_before_1518_in_all_five_languages():
    """五种语言都必须有 1.5.1.9 段落，而且排在 1.5.1.8 之前。"""
    for lang in _LANGS:
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert "\n1.5.1.9\n" in src, (lang, "missing 1.5.1.9 header")
        assert src.index("\n1.5.1.9\n") < src.index("\n1.5.1.8\n"), lang
        assert src.index("\n1.5.1.8\n") < src.index("\n1.5.1.7\n"), lang


def test_relnotes_1519_document_every_session_topic():
    """五种语言的 1.5.1.9 段落都必须点名本次发布的每一项改动。"""
    for lang in _LANGS:
        section = _section_1519(lang)
        for topic in _TOPICS:
            assert topic in section, (lang, topic)


def test_relnotes_1519_document_the_rollback_netcode():
    """回滚网络协议必须写进发行说明。"""
    for lang in _LANGS:
        section = _section_1519(lang)
        assert "rollback" in section, lang
        assert "lockstep" in section, lang
        assert "use_rollback_netcode" in section, lang


def test_relnotes_1519_document_the_ai_economy_features():
    """三项新的 AI 经济特性必须写进发行说明。"""
    for lang in _LANGS:
        section = _section_1519(lang)
        assert "effective_can_train" in section, lang
        assert "expansion_headroom" in section, lang
        assert "ai_base_worth_expanding" in section, lang


def test_relnotes_1519_document_the_ai_attack_timing_fixes():
    """AI 进攻时机的两个修复必须写进发行说明。"""
    for lang in _LANGS:
        section = _section_1519(lang)
        assert "_blind_attack_targets" in section, lang
        assert "goto_random" in section, lang


def test_engine_ships_the_rollback_protocol():
    """引擎必须真的实现了回滚协议。"""
    version = _source("soundrts", "version.py")
    assert 'ROLLBACK_PROTOCOL = "rollback"' in version
    assert 'LOCKSTEP_PROTOCOL = "lockstep"' in version
    assert "PROTOCOL_REVISIONS" in version
    assert "def negotiate_protocol(" in version

    config = _source("soundrts", "config.py")
    assert '"use_rollback_netcode", 1' in config

    root = Path(__file__).resolve().parents[2] / "soundrts" / "net"
    for name in ("snapshot.py", "rollback.py", "session.py", "input_stream.py",
                 "headless.py"):
        assert (root / name).exists(), name


def test_engine_ships_the_ai_economy_policy_module():
    """AI 经济策略模块必须真的存在。"""
    path = Path(__file__).resolve().parents[2] / "soundrts" / "world_ai_economy.py"
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    for name in ("def balancing_tier(", "def expansion_headroom(",
                 "def population_is_pressured(", "def multi_queue_limit(",
                 "def extra_queue_budget(", "def read_bool_attr(",
                 "def read_int_attr("):
        assert name in text, name


def test_engine_ships_the_blind_attack_fallback():
    """盲攻回退必须真的在引擎里。"""
    computer = _source("soundrts", "worldplayercomputer.py")
    assert "def _blind_attack_targets(" in computer
    assert "_blind_attack_targets()" in computer


def test_engine_draws_the_opening_plan_from_the_ai_stream():
    """开局分支必须从 AI 自己的随机流里抽取。"""
    computer = _source("soundrts", "worldplayercomputer.py")
    assert "world.random.choice" not in computer, (
        "the opening plan must not draw from the shared world RNG any more")


def test_the_benches_exist():
    """两个基准工具与计划文档必须真的存在。"""
    root = Path(__file__).resolve().parents[2]
    assert (root / "bench_ai_features.py").exists()
    assert (root / "bench_jl1_sweep.py").exists()
    assert (root / "_NET_ROLLBACK_PLAN.md").exists()
