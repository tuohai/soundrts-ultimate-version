"""审计：1.5.1.9 发行说明里的「回滚架构在本品类中的位置」一段。

这一段说明的是 SoundRTS 采用的网络架构在即时战略品类中的位置：

  * 经典即时战略游戏（帝国时代 1/2/4、星际争霸 1/2）历来使用确定性锁步；
  * 回滚源自格斗游戏，进入即时战略品类是近年的事（Mushroom Wars 2、
    Stormgate）；
  * SoundRTS 从 1.5.1.9 起采用主机权威 + 客户端预测 + 快照回滚；
  * 回滚需要「历史窗口」，这个概念在锁步里根本不存在。

这些测试断言五种语言的发行说明都写清了上述内容，数字与引擎里的
真实常量一致，并且**不会**出现「经典作品用的是回滚」这种错误说法。
"""

from __future__ import annotations

from pathlib import Path

_LANGS = ("zh", "en", "es", "it", "pt-BR")

# 每种语言都必须点名的词条（与语言无关的部分）。
_COMMON_TOPICS = (
    "lockstep",
    "GGPO",
    "Mushroom Wars 2",
    "Stormgate",
    "2016",
    "2023",
    "1.5.1.9",
    "64",
    "300",
)

# 经典作品的名字：中文版用中文名，其余语言用英文名。
_GAME_NAMES = {
    "zh": ("帝国时代 1/2/4", "星际争霸 1/2"),
    "en": ("Age of Empires 1/2/4", "StarCraft 1/2"),
    "es": ("Age of Empires 1/2/4", "StarCraft 1/2"),
    "it": ("Age of Empires 1/2/4", "StarCraft 1/2"),
    "pt-BR": ("Age of Empires 1/2/4", "StarCraft 1/2"),
}


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


def test_relnotes_1519_document_the_rollback_genre_position():
    """五种语言的 1.5.1.9 段落都必须点名这一段的每一个要素。"""
    for lang in _LANGS:
        section = _section_1519(lang)
        for topic in _COMMON_TOPICS:
            assert topic in section, (lang, topic)
        for name in _GAME_NAMES[lang]:
            assert name in section, (lang, name)


def test_relnotes_1519_state_that_classic_rts_used_lockstep():
    """发行说明必须说清楚经典作品用的是锁步，而不是回滚。

    这一条是反回归测试：曾经有过一份错误的对比结论说「帝国时代和
    星际争霸用的是回滚快照」，那会把这段说明的方向整个弄反。
    """
    for lang in _LANGS:
        section = _section_1519(lang)
        # 经典作品必须被描述成锁步。
        assert "lockstep" in section, lang
        # 不得出现「经典作品 + 回滚」这种错误搭配。
        for wrong in (
            "Age of Empires 1/2/4 uses rollback",
            "StarCraft 1/2 uses rollback",
            "AoE2 uses rollback",
            "SC2 uses rollback",
            "帝国时代 1/2/4 使用回滚",
            "星际争霸 1/2 使用回滚",
        ):
            assert wrong not in section, (lang, wrong)


def test_the_history_window_numbers_match_the_engine():
    """发行说明里的窗口数字必须和引擎里的常量一致。"""
    from soundrts.definitions import VIRTUAL_TIME_INTERVAL
    from soundrts.net.rollback import RollbackManager

    assert VIRTUAL_TIME_INTERVAL == 300

    manager = RollbackManager(
        local_player="p1",
        players=("p1", "p2"),
        world=object(),
        step=lambda: None,
        apply_inputs=lambda inputs: None,
    )
    # 窗口是 64 帧 → 19.2 秒。
    assert manager.history_size == 64
    assert 64 * 300 == 19200

    for lang in _LANGS:
        section = _section_1519(lang)
        assert "64" in section, lang
        assert "300" in section, lang
        # 西班牙语 / 意大利语 / 葡萄牙语用逗号作小数点。
        assert "19.2" in section or "19,2" in section, lang


def test_the_engine_really_ships_the_rollback_architecture():
    """这一段描述的架构必须真的在引擎里。"""
    snapshot = _source("soundrts", "net", "snapshot.py")
    assert "host-authoritative input + client prediction + rollback" in snapshot

    rollback = _source("soundrts", "net", "rollback.py")
    assert "history_size: int = 64" in rollback
    assert "def unrecoverable_desync(self)" in rollback

    # 经典协议名必须还在（回滚是默认，但旧客户端仍要能连）。
    version = _source("soundrts", "version.py")
    assert 'ROLLBACK_PROTOCOL = "rollback"' in version
    assert 'LOCKSTEP_PROTOCOL = "lockstep"' in version


def test_the_new_block_is_in_the_1519_section_only():
    """这一段必须落在 1.5.1.9 里，不能跑到别的版本段落去。"""
    for lang in _LANGS:
        text = _source("doc_src", "src", lang, "relnotes.rst")
        assert text.count("Mushroom Wars 2") == 1, lang
        assert text.count("Stormgate") == 1, lang
