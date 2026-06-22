"""can_train upgrade bonus: building can_use_tech + effective_can_train merge."""

from types import SimpleNamespace

from soundrts.definitions import rules
from soundrts.world_build_rules import effective_can_train


def _load_rules():
    with open("res/rules.txt", encoding="utf-8") as f:
        rules.load(f.read())


def test_effective_can_train_merges_player_type_override():
    _load_rules()
    barracks_cls = rules.unit_class("barracks")
    player = SimpleNamespace(
        _can_train_overrides_by_type={
            "barracks": {"footman": 2, "archer": 2, "knight": 2},
        }
    )
    barracks = SimpleNamespace(
        player=player,
        type_name="barracks",
        type=barracks_cls,
        attached_addons=[],
    )
    assert effective_can_train(barracks) == {
        "footman": 2,
        "archer": 2,
        "knight": 2,
    }


def test_dsb_upgrade_bonus_applies_to_barracks_not_footman():
    _load_rules()
    barracks_cls = rules.unit_class("barracks")
    footman_cls = rules.unit_class("footman")
    player = SimpleNamespace(units=[], upgrades=["dsb"])
    player.level = lambda name: 1 if name == "dsb" else 0
    barracks = SimpleNamespace(
        player=player,
        type_name="barracks",
        type=barracks_cls,
        attached_addons=[],
        can_use_tech=("dsb",),
        can_use=(),
        can_use_skill=(),
        _applied_upgrade_effects=set(),
    )
    footman = SimpleNamespace(
        player=player,
        type_name="footman",
        type=footman_cls,
        attached_addons=[],
        can_use_tech=("melee_weapon", "melee_armor"),
        can_use=(),
        can_use_skill=(),
        _applied_upgrade_effects=set(),
    )
    player.units = [barracks, footman]

    upgrade_cls = rules.unit_class("dsb")
    upgrade_cls._apply_effects_to_unit(barracks, player)
    upgrade_cls._apply_effects_to_unit(footman, player)

    assert player._can_train_overrides_by_type["barracks"] == {
        "footman": 5,
        "archer": 3,
        "knight": 2,
    }
    assert effective_can_train(barracks) == {
        "footman": 5,
        "archer": 3,
        "knight": 2,
    }
    assert "footman" not in getattr(player, "_can_train_overrides_by_type", {})


def test_apply_starting_upgrades_applies_dsb_to_barracks():
    _load_rules()
    barracks_cls = rules.unit_class("barracks")
    player = SimpleNamespace(
        upgrades=["dsb"],
        units=[],
    )
    player.level = lambda type_name: player.upgrades.count(type_name)
    barracks = SimpleNamespace(
        player=player,
        type_name="barracks",
        type=barracks_cls,
        attached_addons=[],
        can_use_tech=("dsb",),
        can_use=(),
        can_use_skill=(),
        _applied_upgrade_effects=set(),
    )
    player.units = [barracks]

    from soundrts.worldplayerbase.base import Player

    Player._apply_starting_upgrades(player)

    assert player._can_train_overrides_by_type["barracks"] == {
        "footman": 5,
        "archer": 3,
        "knight": 2,
    }
    assert effective_can_train(barracks) == {
        "footman": 5,
        "archer": 3,
        "knight": 2,
    }


def test_effect_bonus_can_train_line_parsed_without_dropping_last_pair():
    from soundrts.definitions import rules as rules_mod

    rules_mod.load(
        """
def batch_test
class upgrade
effect bonus can_train footman 5 archer 3 knight 2
"""
    )
    effect = rules_mod.get("batch_test", "effect")
    assert effect == ["bonus", "can_train", "footman", "5", "archer", "3", "knight", "2"]


def test_loaded_batch_upgrade_applies_all_train_counts():
    from soundrts.definitions import rules as rules_mod

    with open("res/rules.txt", encoding="utf-8") as f:
        base_rules = f.read()
    rules_mod.load(
        base_rules,
        """
def batch_test
class upgrade
effect bonus can_train footman 5 archer 3 knight 2
""",
    )
    barracks_cls = rules_mod.unit_class("barracks")
    player = SimpleNamespace(units=[], upgrades=["batch_test"])
    player.level = lambda type_name: player.upgrades.count(type_name)
    barracks = SimpleNamespace(
        player=player,
        type_name="barracks",
        type=barracks_cls,
        attached_addons=[],
        can_use_tech=("batch_test",),
        can_use=(),
        can_use_skill=(),
        _applied_upgrade_effects=set(),
    )
    player.units = [barracks]
    upgrade_cls = rules_mod.unit_class("batch_test")
    upgrade_cls._apply_effects_to_unit(barracks, player)
    assert effective_can_train(barracks) == {
        "footman": 5,
        "archer": 3,
        "knight": 2,
    }
