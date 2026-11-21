"""Attack-move (StarCraft 2 "A-move") regression tests."""

from pathlib import Path

from soundrts.definitions import Rules
from soundrts.worldorders import ORDERS_DICT


def _starcraft_rules_text():
    return Path("mods/starcraft/rules.txt").read_text(encoding="utf-8")


def test_attack_move_order_is_registered():
    assert "attack_move" in ORDERS_DICT
    order_cls = ORDERS_DICT["attack_move"]
    assert order_cls.keyword == "attack_move"
    assert order_cls.nb_args == 1


def test_can_attack_move_is_a_known_rule_keyword():
    from soundrts.definitions import rules as global_rules

    assert "can_attack_move" in global_rules.int_properties


def test_can_attack_move_loads_from_rules():
    rules = Rules()
    rules.load(
        """
def marine
class soldier
can_attack_move 0

def firebat
class soldier
can_attack_move 1
"""
    )
    assert rules.unit_class("marine").can_attack_move == 0
    assert rules.unit_class("firebat").can_attack_move == 1


def test_soldier_defaults_to_allowing_attack_move():
    from soundrts.worldunit.worldsoldier import Soldier

    assert Soldier.can_attack_move == 1


def test_attack_move_is_in_the_order_menu():
    """The order needs a style entry with an index, else it never shows up."""
    from soundrts.definitions import style

    assert style.has("attack_move", "index")
    assert style.has("attack_move", "title")


def test_attack_move_uses_the_dedicated_tts_entry():
    """The style title must point at a real attack-move phrase in tts.txt."""
    from soundrts import msgparts as mp
    from soundrts.definitions import style

    title = style.get("attack_move", "title")
    assert [str(x) for x in title] == [str(x) for x in mp.ATTACK_MOVE]

    tts = Path("res/ui/tts.txt").read_text(encoding="utf-8")
    for msg_id in mp.ATTACK_MOVE:
        assert "\n%s\t" % msg_id in "\n" + tts
    assert "attack-move" in tts


def test_starcraft_mod_uses_attack_move():
    """The StarCraft mod's combat units must be able to A-move."""
    rules = Rules()
    rules.load(_starcraft_rules_text())
    for name in ("marine", "zealot", "zergling", "ghost"):
        unit = rules.unit_class(name)
        assert unit is not None, name
        assert int(getattr(unit, "can_attack_move", 0) or 0) == 1, name
    # Workers must not A-move into a fight.
    for name in ("scv", "probe", "drone"):
        unit = rules.unit_class(name)
        assert unit is not None, name
        assert int(getattr(unit, "can_attack_move", 0) or 0) == 0, name


def test_attack_move_menu_requires_both_skills():
    from soundrts.worldorders.movement import AttackMoveOrder

    class Unit:
        can_attack_move = 1
        basic_skills = {"go", "attack"}

    assert AttackMoveOrder.is_allowed(Unit()) is True

    class Worker(Unit):
        can_attack_move = 0

    assert AttackMoveOrder.is_allowed(Worker()) is False

    class NoAttack(Unit):
        basic_skills = {"go"}

    assert AttackMoveOrder.is_allowed(NoAttack()) is False
