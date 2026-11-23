"""牲口（羊/牛等）的死亡不该污染「阵亡」与「消灭」统计。

背景：
  玩家用 ``claim``（靠近即归属）或 ``herd``（驱赶绑定）把中立牲口收归
  自己时，该牲口的 ``produced`` 统计**从未**被记过——因为
  ``CreatureAttributes.set_player`` 只给「原本无主」的单位记 produced。

  但牲口死亡时，``Creature.die`` 依旧会：
    * 给主人记 ``lost``   → 主人的「阵亡」凭空多出，生存率评分被拉低；
    * 给击杀者记 ``killed`` → 杀一只羊就算「消灭了敌人」，战斗评分虚高。

  这两个统计都要排除动物。
"""

from __future__ import annotations

import os
import sys
import types

import pytest

import soundrts.worldunit  # noqa: F401


class _Stats:
    def __init__(self):
        self._d = {}

    def add(self, event, target, inc=1):
        if target is not None:
            self._d[(event, target)] = self._d.get((event, target), 0) + inc

    def get(self, event, target):
        return self._d.get((event, target), 0)


def _player(name, neutral=False):
    p = types.SimpleNamespace(
        id=name,
        neutral=neutral,
        allied=[],
        faction=name,
        stats=_Stats(),
        units=[],
        observed_objects={},
        perception=types.SimpleNamespace(discard=lambda o: None),
        nb_units_lost=0,
        nb_units_killed=0,
        has_victory=False,
    )
    p.allied = [p]
    p.player_is_an_enemy = lambda other: other is not None and other not in p.allied
    p.on_unit_attacked = lambda unit, attacker: None
    p.observe = lambda other: None
    p.note_combat_with = lambda other: None
    p.add = lambda unit: None
    p.remove = lambda unit: None
    return p


def _make_unit(player, unit_id=6, type_name="knight", produced=False, **attrs):
    """造一个 ``Unit`` 实例（覆盖 ``worldbase.Unit.die`` 的 nb_units_lost）。

    ``produced=True`` 表示该单位被记过 ``produced``（主人自己造出来的）。
    """
    from soundrts.worldunit.worldbase import Unit

    class _U(Unit):
        claimable = 0
        herdable = 0
        stat_type = "unit"
        is_a_building = False
        is_vulnerable = True
        food_deposit = None
        food_deposit_qty = 0
        corpse = 0
        xp_reward = 0
        drop_loot = 0
        is_inside = False
        expanded_is_a = ()
        airground_type = "ground"
        collision = 1
        radius = 500
        speed = 10
        basic_skills = ()

        def stop(self):
            pass

        def cancel_all_orders(self, unpay=False):
            pass

        def notify(self, ev):
            pass

        def delete(self):
            pass

        def reset_charge_state(self, force=False):
            pass

        def _trigger_death_skills(self, attacker):
            pass

        def claim_rewards(self, attacker):
            pass

    unit = object.__new__(_U)
    unit.type_name = type_name
    unit.player = player
    unit.place = types.SimpleNamespace(objects=[], neighbors=[], id="a", x=0, y=0)
    unit.x = 0
    unit.y = 0
    unit.hp = 10
    unit.inside = None
    unit._buffs = []
    unit.inventory = []
    unit.id = unit_id
    unit.last_player = None
    unit.flee_on_hit = 0
    unit._herd_leader = None
    unit.world = types.SimpleNamespace(unit_class=lambda _name: None, time=0)
    for key, value in attrs.items():
        setattr(unit, key, value)
    if produced:
        unit._stats_counted_produced = True
    return unit


def _make_livestock(player, unit_id=77, type_name="sheep", produced=False):
    """一只牲口（羊/牛）。"""
    unit = _make_unit(
        player,
        unit_id=unit_id,
        type_name=type_name,
        produced=produced,
        claimable=1,
        herdable=1,
        claim_range=0,
    )
    return unit


def _make_deer(player, unit_id=88):
    """一只纯野生动物（鹿）：可狩猎，但没有主人。"""
    unit = _make_unit(player, unit_id=unit_id, type_name="deer", is_huntable=1)
    unit.food_deposit = "food_carcass"
    unit.food_deposit_qty = 10
    return unit


def _make_killer(player, unit_id=9):
    """一个作为击杀者的敌方单位（不需要完整的 Unit 行为）。"""
    class _Killer:
        basic_skills = ()

        def __init__(self):
            self.player = player
            self.place = types.SimpleNamespace(objects=[], neighbors=[], id="a")
            self.x = 1
            self.y = 0
            self.hp = 20
            self.inside = None
            self.id = unit_id
            self.last_player = None
            self.type_name = "knight"
            self.expanded_is_a = ()

        def notify(self, ev):
            pass

    return _Killer()


# ---------------------------------------------------------------------------
# is_livestock_unit / is_animal_unit / is_livestock_loss
# ---------------------------------------------------------------------------


def test_is_livestock_unit_detects_herdable_and_claimable():
    from soundrts.worldplayerbase.base import is_livestock_unit

    assert is_livestock_unit(types.SimpleNamespace(herdable=1, claimable=0)) is True
    assert is_livestock_unit(types.SimpleNamespace(herdable=0, claimable=1)) is True
    assert is_livestock_unit(types.SimpleNamespace(herdable=0, claimable=0)) is False


def test_is_livestock_unit_ignores_pure_wildlife():
    """鹿这类纯野生动物（is_huntable）不是牲口：不属于任何玩家。"""
    from soundrts.worldplayerbase.base import is_livestock_unit

    assert is_livestock_unit(types.SimpleNamespace(is_huntable=1, herdable=0, claimable=0)) is False


def test_is_livestock_unit_handles_missing_attributes():
    from soundrts.worldplayerbase.base import is_livestock_unit

    assert is_livestock_unit(object()) is False


def test_is_animal_unit_covers_livestock_and_wildlife():
    from soundrts.worldplayerbase.base import is_animal_unit

    assert is_animal_unit(types.SimpleNamespace(is_huntable=1, herdable=0, claimable=0)) is True
    assert is_animal_unit(types.SimpleNamespace(is_huntable=0, herdable=1, claimable=0)) is True
    assert is_animal_unit(types.SimpleNamespace(is_huntable=0, herdable=0, claimable=1)) is True
    assert is_animal_unit(types.SimpleNamespace(is_huntable=0, herdable=0, claimable=0)) is False
    assert is_animal_unit(object()) is False


def test_counts_in_unit_stats_excludes_livestock():
    """牲口不属于「单位」统计口径。"""
    from soundrts.worldplayerbase.base import counts_in_unit_stats

    assert counts_in_unit_stats(types.SimpleNamespace(herdable=1, claimable=0)) is False
    assert counts_in_unit_stats(types.SimpleNamespace(herdable=0, claimable=1)) is False


def test_counts_in_unit_stats_includes_military_units():
    from soundrts.worldplayerbase.base import counts_in_unit_stats

    assert counts_in_unit_stats(types.SimpleNamespace(herdable=0, claimable=0)) is True


def test_counts_in_unit_stats_ignores_stale_produced_flag():
    """归属来的羊可能带着**前任主人**的生产标记，不能据此判定「自己造的兵」。

    真实存档（``user/saves/aoe2/测试击杀羊``）里就是这样：羊先由中立
    野生动物玩家生成（``_stats_counted_produced = True``），再被玩家归属，
    标记没有跟着归属清除。
    """
    from soundrts.worldplayerbase.base import counts_in_unit_stats

    stale = types.SimpleNamespace(
        herdable=1,
        claimable=1,
        _stats_counted_produced=True,
        _stats_produced_for=object(),
    )
    assert counts_in_unit_stats(stale) is False


# ---------------------------------------------------------------------------
# die()：统计行为
# ---------------------------------------------------------------------------


def test_claimed_livestock_death_is_not_counted_as_owner_loss():
    """归属来的羊被敌人杀了 → 不算主人的阵亡。"""
    owner = _player("owner")
    enemy = _player("enemy")
    sheep = _make_livestock(owner)

    sheep.die(_make_killer(enemy))

    assert owner.stats.get("lost", "unit") == 0
    assert owner.nb_units_lost == 0


def test_killing_livestock_is_not_counted_as_enemy_neutralized():
    """杀羊不算「消灭敌人」。"""
    owner = _player("owner")
    enemy = _player("enemy")
    sheep = _make_livestock(owner)

    sheep.die(_make_killer(enemy))

    assert enemy.stats.get("killed", "unit") == 0


def test_killing_neutral_wildlife_is_not_counted_as_enemy_neutralized():
    """打鹿也不该算「消灭敌人」（鹿是中立野生动物，不是玩家的兵）。"""
    wildlife = _player("wildlife", neutral=True)
    hunter = _player("hunter")
    deer = _make_deer(wildlife)

    deer.die(_make_killer(hunter))

    assert hunter.stats.get("killed", "unit") == 0


def test_military_unit_death_still_counts_as_loss_and_kill():
    """回归保护：普通作战单位的阵亡/消灭统计必须保持原样。"""
    owner = _player("owner")
    enemy = _player("enemy")
    knight = _make_unit(owner, unit_id=6, type_name="knight", produced=True)

    knight.die(_make_killer(enemy))

    assert owner.stats.get("lost", "unit") == 1
    assert owner.nb_units_lost == 1
    assert enemy.stats.get("killed", "unit") == 1


def test_owner_produced_livestock_death_does_not_count_as_loss():
    """牧场自己产出的羊死亡也不算阵亡——「生产/阵亡/消灭」三者口径一致。"""
    owner = _player("owner")
    enemy = _player("enemy")
    sheep = _make_livestock(owner, produced=True)

    sheep.die(_make_killer(enemy))

    assert owner.stats.get("lost", "unit") == 0
    assert owner.nb_units_lost == 0
    # 杀牲口也不算消灭敌人。
    assert enemy.stats.get("killed", "unit") == 0


def test_livestock_is_not_counted_as_produced():
    """牲口不计入「生产」：牧场产的羊也不会让单位的生产数虚高。"""
    from soundrts.worldunit.world_attributes import CreatureAttributes

    class _Animal(CreatureAttributes):
        stat_type = "unit"
        herdable = 1
        claimable = 1
        player = None
        inside = None

        def stop(self):
            pass

        def cancel_all_orders(self, unpay=False):
            pass

    owner = _player("owner")
    animal = object.__new__(_Animal)
    animal.set_player(owner)

    assert owner.stats.get("produced", "unit") == 0


def test_military_unit_is_still_counted_as_produced():
    """回归保护：作战单位照旧计入「生产」。"""
    from soundrts.worldunit.world_attributes import CreatureAttributes

    class _Soldier(CreatureAttributes):
        stat_type = "unit"
        herdable = 0
        claimable = 0
        player = None
        inside = None

        def stop(self):
            pass

        def cancel_all_orders(self, unpay=False):
            pass

    owner = _player("owner")
    unit = object.__new__(_Soldier)
    unit.set_player(owner)

    assert owner.stats.get("produced", "unit") == 1


def test_claim_clears_stale_produced_flag():
    """归属转移必须清掉前任主人的生产标记。"""
    from soundrts.worldunit.world_attributes import CreatureAttributes

    class _Animal(CreatureAttributes):
        stat_type = "unit"
        herdable = 1
        claimable = 1
        player = None
        inside = None

        def stop(self):
            pass

        def cancel_all_orders(self, unpay=False):
            pass

    wildlife = _player("wildlife", neutral=True)
    owner = _player("owner")

    animal = object.__new__(_Animal)
    animal.set_player(wildlife)
    assert getattr(animal, "_stats_counted_produced", False) is False

    # 手工模拟旧存档里的脏标记：羊由中立方生成时留下的。
    animal._stats_counted_produced = True
    animal._stats_produced_for = wildlife

    animal.set_player(owner)

    assert getattr(animal, "_stats_counted_produced", False) is False
    assert getattr(animal, "_stats_produced_for", None) is None
    assert owner.stats.get("produced", "unit") == 0


def test_claim_then_kill_never_exceeds_produced():
    """端到端：归属 -> 被杀，主人的「阵亡」数不会超过「生产」数。"""
    from soundrts.worldunit.world_status_update import CreatureStatusUpdate

    wildlife = _player("wildlife", neutral=True)
    owner = _player("owner")
    enemy = _player("enemy")

    sheep = _make_livestock(wildlife)
    sheep.set_player = lambda p: setattr(sheep, "player", p)

    place = types.SimpleNamespace(objects=[], neighbors=[], id="a", x=0, y=0)
    sheep.place = place
    claimer = _make_killer(owner, unit_id=3)
    claimer.place = place
    place.objects = [sheep, claimer]

    assert sheep._try_auto_claim() is True
    assert sheep.player is owner
    assert owner.stats.get("produced", "unit") == 0

    sheep.die(_make_killer(enemy))

    assert owner.stats.get("lost", "unit") == 0
    assert owner.stats.get("lost", "unit") <= owner.stats.get("produced", "unit")


def test_livestock_death_with_no_attacker_does_not_count_as_loss():
    """环境死亡（无击杀者）同样不该把牲口算成阵亡。"""
    owner = _player("owner")
    sheep = _make_livestock(owner)

    sheep.die(None)

    assert owner.stats.get("lost", "unit") == 0
    assert owner.nb_units_lost == 0


def test_killing_animal_does_not_inflate_combat_score():
    """杀动物不应抬高战斗评分（消灭数 / 敌人生产数）。"""
    from soundrts.worldplayerstats import Stats

    enemy = _player("enemy")
    hunter = _player("hunter")
    hunter.world = types.SimpleNamespace(
        players=[hunter, enemy],
        ex_players=[],
        map_deposit_capacity=[1000, 0],
        time=0,
    )
    hunter.resources = [0, 0]
    hunter._starting_resources = [0, 0]
    enemy.resources = [0, 0]
    enemy._starting_resources = [0, 0]

    stats = Stats(hunter)
    hunter.stats = stats
    enemy.stats = Stats(enemy)
    enemy.stats.add("produced", "unit", 10)

    deer = _make_deer(enemy)
    deer.die(_make_killer(hunter))

    assert stats.get("killed", "unit") == 0
    assert stats.score_breakdown()["combat"] == 0


# ---------------------------------------------------------------------------
# 真实存档回归：user/saves/aoe2/测试击杀羊
# ---------------------------------------------------------------------------

_SAVE_PATH = os.path.join("user", "saves", "aoe2", "测试击杀羊")


def _load_sheep_save():
    """加载真实存档；没有存档就跳过。"""
    if not os.path.isfile(_SAVE_PATH):
        pytest.skip("save '测试击杀羊' not present")
    import cloudpickle

    from soundrts.game import pickle_recursion_limit_for_file_size
    from soundrts.lib.resource import res
    from soundrts.save_pickle import rebuild_world_after_load, restore_world_pickle_targets

    res.set_mods("aoe2")
    limit = pickle_recursion_limit_for_file_size(os.path.getsize(_SAVE_PATH))
    saved_limit = sys.getrecursionlimit()
    sys.setrecursionlimit(max(saved_limit, limit))
    try:
        with open(_SAVE_PATH, "rb") as f:
            f.readline()
            game = cloudpickle.load(f)
    finally:
        sys.setrecursionlimit(saved_limit)

    world = game.world
    rebuild_world_after_load(world)
    restore_world_pickle_targets(world)

    class _StubInterface:
        def queue_srv_event(self, *a, **k):
            pass

        def __getattr__(self, name):
            return lambda *a, **k: None

    for p in world.players:
        client = getattr(p, "client", None)
        if client is not None and getattr(client, "interface", None) is None:
            client.interface = _StubInterface()
    return world


def test_real_save_claimed_sheep_death_is_not_a_loss():
    """真实存档回归：斥候骑兵杀掉归属我方的羊后，结算里不能多出「1 阵亡」。

    存档里的羊是这样来的：先由中立野生动物玩家生成（于是羊身上带着
    ``_stats_counted_produced = True``），再被玩家归属。旧代码没有在归属
    转移时清掉这个标记，于是羊被敌人杀死时，主人凭空多出 1 个阵亡，
    结算显示成「4 单位 生产, 1 阵亡, 0 被消灭」。
    """
    world = _load_sheep_save()

    human = next(p for p in world.players if getattr(p, "is_human", False))
    enemy = next(p for p in world.players if p.faction == "ethiopians")
    sheep = next(
        u for u in human.units if getattr(u, "type_name", None) == "sheep"
    )
    killer = next(
        u for u in enemy.units if getattr(u, "type_name", None) == "scout_cavalry"
    )

    produced_before = human.stats.get("produced", "unit")
    lost_before = human.stats.get("lost", "unit")
    killed_before = enemy.stats.get("killed", "unit")

    sheep.die(killer)

    assert human.stats.get("lost", "unit") == lost_before
    assert human.nb_units_lost == 0
    assert enemy.stats.get("killed", "unit") == killed_before
    # 「阵亡」不能多于「生产」。
    assert human.stats.get("lost", "unit") <= human.stats.get("produced", "unit")
    assert produced_before == human.stats.get("produced", "unit")


def test_real_save_sheep_is_not_counted_as_produced():
    """真实存档回归：归属来的羊不该出现在主人的「生产」数里。"""
    world = _load_sheep_save()

    human = next(p for p in world.players if getattr(p, "is_human", False))
    produced = human.stats.get("produced", "unit")
    military = [
        u
        for u in human.units
        if not getattr(u, "is_a_building", False)
        and not getattr(u, "herdable", 0)
        and not getattr(u, "claimable", 0)
    ]
    # 「生产」数只覆盖军事单位，牲口不计入。
    assert produced == len(military)

