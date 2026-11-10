# -*- coding: utf-8 -*-
"""攻击暴露隐形单位（AoE3 风格「攻击即破隐」）。

机制：
* ``reveal_stealth_on_attack 1``（rules, int）：单位在隐形/隐身状态下
  发动攻击时会被暴露。
* ``stealth_reveal_time N``（rules, precision-scaled 秒）：暴露持续时间，
  默认 3 秒。0 = 永久暴露。
* 暴露期间单位以实例属性覆盖 ``is_invisible`` / ``is_cloaked`` /
  ``is_cloakable``，因此 Python 与 Cython 两条感知路径都能立刻看到它，
  同时隐身装置（cloaker）无法在这段时间内把它重新隐身。
* 暴露窗口结束后恢复原本状态。
"""

from __future__ import annotations

import logging
import os
import sys
import warnings
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

saved = sys.argv
sys.argv = [saved[0] if saved else "pytest"]
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from soundrts import config
    from soundrts.definitions import Rules, rules
    from soundrts.lib.nofloat import PRECISION
    from soundrts.lib.resource import res
    from soundrts.world import World
    from soundrts.world.world_game import WorldGameMixin
    from soundrts.worldclient import DirectClient, DummyClient
    from soundrts.worldentity import Entity
sys.argv = saved

ROOT = Path(__file__).resolve().parents[2]
JL1 = ROOT / "res" / "multi" / "jl1.txt"


# ---------------------------------------------------------------------------
# 1. rules 解析
# ---------------------------------------------------------------------------

def test_rules_parse_stealth_knobs():
    r = Rules()
    r.read(
        "def spy\n"
        "class soldier\n"
        "is_invisible 1\n"
        "reveal_stealth_on_attack 1\n"
        "stealth_reveal_time 5\n"
    )
    d = r._dict["spy"]
    assert d["reveal_stealth_on_attack"] == 1
    # stealth_reveal_time 是 precision 属性：5 秒 -> 5000 ms
    assert d["stealth_reveal_time"] == 5 * PRECISION


def test_stealth_knobs_are_registered_in_definitions():
    from soundrts import definitions

    assert "reveal_stealth_on_attack" in definitions.rules.int_properties
    assert "stealth_reveal_time" in definitions.rules.precision_properties


# ---------------------------------------------------------------------------
# 2. Entity 层面的破隐逻辑
# ---------------------------------------------------------------------------

class _U(Entity):
    """最小化的隐形单位（只需要 stealth 相关属性）。"""

    def __init__(self):
        # Entity.__init__ 需要一个 place（会读 place.world 并移动单位），
        # 这里直接绕过：stealth 逻辑不依赖 world/place。
        self.world = None
        self.place = None
        self.x = 0
        self.y = 0


def _make_unit(*, invisible=False, cloakable=False, cloaked=False,
               reveal=True, reveal_time=None):
    u = _U()
    u.is_invisible = invisible
    u.is_cloakable = cloakable
    u.is_cloaked = cloaked
    u.reveal_stealth_on_attack = 1 if reveal else 0
    u.stealth_reveal_time = (
        3 * PRECISION if reveal_time is None else reveal_time
    )
    return u


def test_attack_exposes_invisible_unit():
    u = _make_unit(invisible=True)
    assert u._reveal_stealth(1000) is True
    assert u.is_invisible is False
    assert u._stealth_revealed_until == 1000 + 3 * PRECISION


def test_attack_exposes_cloaked_unit_and_blocks_recloaking():
    u = _make_unit(cloakable=True, cloaked=True)
    assert u._reveal_stealth(1000) is True
    assert u.is_cloaked is False
    # 隐身装置在这段时间内无法重新隐身它
    assert u.is_cloakable is False


def test_reveal_expires_and_restores_natural_state():
    u = _make_unit(invisible=True)
    u._reveal_stealth(1000)
    assert u._end_stealth_reveal() is True
    assert u.is_invisible is True
    assert u._stealth_revealed_until == 0
    # 再次结束是空操作
    assert u._end_stealth_reveal() is False


def test_second_attack_refreshes_the_timer():
    u = _make_unit(invisible=True)
    u._reveal_stealth(1000)
    u._reveal_stealth(1500)
    assert u._stealth_revealed_until == 1500 + 3 * PRECISION
    assert u.is_invisible is False


def test_units_without_the_flag_do_not_reveal():
    u = _make_unit(invisible=True, reveal=False)
    assert u._reveal_stealth(1000) is False
    assert u.is_invisible is True
    assert u._stealth_revealed_until == 0


def test_non_stealthed_units_are_unaffected():
    u = _make_unit()
    assert u._reveal_stealth(1000) is False
    assert u.is_invisible is False
    assert u.is_cloaked is False
    assert u._stealth_revealed_until == 0


def test_zero_reveal_time_means_forever():
    u = _make_unit(invisible=True, reveal_time=0)
    u._reveal_stealth(1000)
    assert u._stealth_revealed_until > 1000 + 1000000


# ---------------------------------------------------------------------------
# 3. 世界层：暴露窗口到期后自动恢复
# ---------------------------------------------------------------------------

class _FakeWorld(WorldGameMixin):
    def __init__(self, time=0):
        self.time = time
        self.players = []


def test_world_expires_reveal_and_restores_stealth():
    u = _make_unit(invisible=True)
    world = _FakeWorld(time=0)
    world.players = [SimpleNamespace(units=[u], allied=[])]

    u._reveal_stealth(0)
    assert u.is_invisible is False

    # 窗口内：仍然暴露
    world.time = 3 * PRECISION - 1
    world._update_cloaking()
    assert u.is_invisible is False

    # 窗口结束：恢复隐形
    world.time = 3 * PRECISION
    world._update_cloaking()
    assert u.is_invisible is True
    assert u._stealth_revealed_until == 0


def test_world_does_not_recloak_a_revealed_unit():
    """暴露期间，隐身装置不能把它重新隐身。"""
    u = _make_unit(cloakable=True, cloaked=True)
    world = _FakeWorld(time=0)
    world.players = [SimpleNamespace(units=[u], allied=[])]

    u._reveal_stealth(0)
    world._update_cloaking()
    assert u.is_cloaked is False
    assert u.is_cloakable is False


# ---------------------------------------------------------------------------
# 4. 攻击管线集成（真实世界 + 真实单位）
# ---------------------------------------------------------------------------

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
    # 让目标进入攻击者的感知（can_attack 需要）
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


def test_attacking_a_stealthed_unit_exposes_it(res_loaded):
    """真实单位开火 → 隐形被破除。"""
    world, p1, p2 = _build_world()
    attacker = _soldier(p1)
    target = _soldier(p2)
    assert attacker is not None and target is not None

    _prepare_attack(attacker, target)

    attacker.is_invisible = True
    attacker.reveal_stealth_on_attack = 1
    attacker.stealth_reveal_time = 3 * PRECISION

    attacker.aim(target)
    assert attacker.is_invisible is False, "攻击后应被暴露"
    assert attacker._stealth_revealed_until > world.time


def test_attack_does_not_reveal_when_flag_is_off(res_loaded):
    world, p1, p2 = _build_world()
    attacker = _soldier(p1)
    target = _soldier(p2)
    assert attacker is not None and target is not None

    _prepare_attack(attacker, target)

    attacker.is_invisible = True
    attacker.reveal_stealth_on_attack = 0

    attacker.aim(target)
    assert attacker.is_invisible is True


def test_charge_attack_also_exposes_the_unit(res_loaded):
    """冲锋攻击同样会破隐。"""
    world, p1, p2 = _build_world()
    attacker = _soldier(p1)
    target = _soldier(p2)
    assert attacker is not None and target is not None

    _prepare_attack(attacker, target)

    attacker.is_invisible = True
    attacker.reveal_stealth_on_attack = 1
    attacker.stealth_reveal_time = 3 * PRECISION

    # 让冲锋分支成立
    attacker.mdg = 5 * PRECISION
    attacker.rdg = 0
    attacker.charge_mdg = 2 * PRECISION
    attacker.charge_mdg_cd = 0
    attacker.charge_mdg_dist = 0
    attacker.charge_mdg_min_dist = 0
    attacker._can_charge_attack = lambda target, is_melee=True: True
    attacker._get_charge_damage = lambda target, is_melee=True: 3 * PRECISION

    attacker.aim(target)
    assert attacker.is_invisible is False, "冲锋也应破隐"
