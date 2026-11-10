# -*- coding: utf-8 -*-
"""基础版 res 里的示例单位：亡灵骑士 undead_knight（攻击即破隐）。

``res/rules.txt`` 里定义了一个演示「攻击即破隐」的示例单位：

* 平时隐形（``is_invisible 1``）；
* 一旦发动攻击（近战 / 远程 / 冲锋）就会被暴露
  ``stealth_reveal_time`` 秒，之后可以重新隐匿；
* 由亡灵陵墓（necropolis）训练，需要帝王时代。

本模块锁定这三条：规则里必须有它、它必须真的能从亡灵陵墓训练出来、
它真的会在开火后暴露自己、菜单里必须能念出它的名字。
"""

from __future__ import annotations

import logging
import os
import sys
import warnings
from pathlib import Path

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

saved = sys.argv
sys.argv = [saved[0] if saved else "pytest"]
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from soundrts import config
    from soundrts.definitions import rules
    from soundrts.lib.nofloat import PRECISION
    from soundrts.lib.resource import res
    from soundrts.world import World
    from soundrts.worldclient import DirectClient, DummyClient
sys.argv = saved

ROOT = Path(__file__).resolve().parents[2]
JL1 = ROOT / "res" / "multi" / "jl1.txt"


@pytest.fixture
def res_loaded():
    logging.disable(logging.WARNING)
    old = getattr(config, "mods", "")
    config.mods = ""
    res.set_mods("")
    res.load_rules_and_ai()
    yield
    config.mods = old
    res.set_mods(old or "")
    if old:
        res.load_rules_and_ai()
    logging.disable(logging.NOTSET)


def _build_world(seed=42):
    faction = rules.factions[0] if rules.factions else "human_faction"
    world = World([], seed)
    world._parse_map(JL1.read_text(encoding="utf-8"))
    world.square_width = int(world.square_width * PRECISION)
    world._build_map()

    class _StubInterface:
        def queue_srv_event(self, *args, **kwargs):
            pass

        def __getattr__(self, name):
            return lambda *a, **k: None

    human = DirectClient("idle_human", None)
    human.faction = faction
    human.alliance = "1"
    human.interface = _StubInterface()
    cpu = DummyClient("intermediate")
    cpu.faction = faction
    cpu.alliance = "2"
    world.populate_map([human, cpu], random_starts=False)
    players = list(world.players)
    assert len(players) == 2, players
    return world, players[0], players[1]


def _soldier(player):
    for u in player.units:
        if getattr(u, "mdg", 0) > 0 or getattr(u, "rdg", 0) > 0:
            return u
    return None


def _prepare_attack(attacker, target):
    """把双方摆到可以真的开火的状态。"""
    target.place = attacker.place
    target.x = attacker.x + 500
    target.y = attacker.y
    attacker.x = target.x - 500
    try:
        attacker.player.perception.add(target)
    except Exception:
        pass
    attacker.mdg_next_attack_time = 0
    attacker.rdg_next_attack_time = 0
    attacker.mdg_prep_end_time = 0
    attacker.rdg_prep_end_time = 0
    attacker.mdg_ready = 0
    attacker.rdg_ready = 0
    # 目标只当"挨打的木桩"：血量拉满，避免它被打死 ->
    # delete() -> place.leave() 报错（目标没有真正进入过 place.objects）。
    target.hp_max = max(target.hp_max, 10 ** 7)
    target.hp = target.hp_max


def _spawn_undead_knight(player):
    """在玩家附近真的造一个亡灵骑士出来（用真实的 rules 类）。"""
    cls = rules.unit_class("undead_knight")
    assert cls is not None, "res/rules.txt must define undead_knight"
    place = player.units[0].place
    before = {id(u) for u in player.units}
    player.add_unit(cls, place)
    spawned = [u for u in player.units if id(u) not in before]
    assert spawned, "could not spawn undead_knight"
    return spawned[0]


# ---------------------------------------------------------------------------
# 1. 规则定义
# ---------------------------------------------------------------------------

def test_base_res_defines_the_undead_knight_example_unit():
    """基础版 res 必须提供「亡灵骑士」这个演示单位。"""
    src = (ROOT / "res" / "rules.txt").read_text(encoding="utf-8")
    assert "def undead_knight" in src
    block = src.split("def undead_knight", 1)[1]
    block = block.split("\ndef ", 1)[0]
    assert "is_invisible 1" in block
    assert "reveal_stealth_on_attack 1" in block
    assert "stealth_reveal_time 3" in block


def test_undead_knight_is_trainable_from_the_necropolis(res_loaded):
    _build_world()
    cls = rules.unit_class("undead_knight")
    assert cls.reveal_stealth_on_attack == 1
    assert cls.stealth_reveal_time == 3 * PRECISION
    assert cls.is_invisible == 1

    necro = rules.unit_class("necropolis")
    trainable = rules.class_rules_attr(necro, "can_train", ())
    assert "undead_knight" in trainable


# ---------------------------------------------------------------------------
# 2. 真实单位的行为
# ---------------------------------------------------------------------------

def test_undead_knight_reveals_itself_when_it_attacks(res_loaded):
    """真实单位：亡灵骑士开火后被暴露，窗口结束后恢复隐形。"""
    world, p1, p2 = _build_world()
    attacker = _spawn_undead_knight(p1)
    target = _soldier(p2)
    assert target is not None

    _prepare_attack(attacker, target)

    # 单位从 rules 继承了隐形 + 破隐开关，无需手工设置。
    assert attacker.is_invisible == 1
    assert attacker.reveal_stealth_on_attack == 1
    assert attacker.stealth_reveal_time == 3 * PRECISION

    attacker.aim(target)
    assert attacker.is_invisible is False, "亡灵骑士攻击后应被暴露"
    assert attacker._stealth_revealed_until > world.time

    # 窗口到期 -> 恢复隐形（恢复成规则里的原始值 1）
    world.time = attacker._stealth_revealed_until
    world._update_cloaking()
    assert attacker.is_invisible == 1


def test_undead_knight_has_a_spoken_title_in_every_locale():
    """菜单里必须能念出单位名，否则训练按钮是哑的。"""
    from soundrts.definitions import Style

    st = Style()
    st.load((ROOT / "res" / "ui" / "style.txt").read_text(encoding="utf-8"))
    assert st.get("undead_knight", "title") == ["7800"]

    for ui_dir in sorted((ROOT / "res").glob("ui*")):
        tts = ui_dir / "tts.txt"
        if not tts.exists():
            continue
        text = tts.read_text(encoding="utf-8")
        assert "\n7800\t" in "\n" + text, "%s: missing title 7800" % ui_dir.name
