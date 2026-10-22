"""Variables, if/else, loops, and repeatable map triggers."""
from __future__ import annotations

from soundrts.trigger_script import (
    add_global,
    add_var,
    apply_on_death_script,
    apply_var_effect,
    eval_var_condition,
    get_global,
    get_var,
    parse_trigger_tree,
    set_var,
    should_fire_repeat,
    unpack_trigger,
)
from soundrts.worldplayerbase.triggers import TriggersMixin
from soundrts.worldskill import Skill


class _World:
    def __init__(self):
        self.time = 0
        self.timer_coefficient = 1


class _Player(TriggersMixin):
    def __init__(self):
        self.has_victory = False
        self.has_been_defeated = False
        self.triggers = []
        self.world = _World()
        self.actions = []
        # lang_count / lang_has need the player's unit and upgrade lists.
        self.units = []
        self.upgrades = []

    @property
    def is_playing(self):
        return not (self.has_victory or self.has_been_defeated)

    def check_type(self, o, t):
        """Stub of Player.check_type: match on type_name.

        The real implementation (soundrts/worldplayerbase/base.py) also
        matches line-upgraded units through ``expanded_is_a``; the stub
        units below only carry a plain ``type_name``.
        """
        return getattr(o, "type_name", None) == t

    def lang_mark(self, args):
        self.actions.append(tuple(args))


def test_parse_repeat_modifier_and_cooldown():
    owners, cond, action, meta = parse_trigger_tree(
        ["player1", "repeat", "10", ["true"], ["add_var", "wave", "1"]]
    )
    assert owners == "player1"
    assert cond == ["true"]
    assert action == ["add_var", "wave", "1"]
    assert meta["repeat"] is True
    assert meta["cooldown"] == 10.0


def test_parse_plain_trigger_has_no_meta():
    owners, cond, action, meta = parse_trigger_tree(
        ["players", ["timer", "0"], ["victory"]]
    )
    assert owners == "players"
    assert meta is None
    assert unpack_trigger([cond, action])[2] is None


def test_player_vars_and_comparison():
    p = _Player()
    set_var(p, "gold", 3)
    add_var(p, "gold", 2)
    assert get_var(p, "gold") == 5
    assert eval_var_condition(p, p.world, ["gold", ">=", "5"]) is True
    assert eval_var_condition(p, p.world, ["gold", "<", "5"]) is False
    set_var(p, "need", 5)
    assert eval_var_condition(p, p.world, ["gold", ">=", "var", "need"]) is True


def test_or_if_else_and_repeat_action():
    p = _Player()
    assert p.my_eval(["or", ["false"], ["true"]]) is True
    p.my_eval(["if", ["true"], ["mark", "then"], ["mark", "else"]])
    p.my_eval(["if", ["false"], ["mark", "then"], ["mark", "else"]])
    p.my_eval(["repeat", "3", ["mark", "x"]])
    assert p.actions == [("then",), ("else",), ("x",), ("x",), ("x",)]


def test_while_increments_until_limit():
    p = _Player()
    p.my_eval(
        [
            "while",
            ["var", "n", "<", "4"],
            ["add_var", "n", "1"],
            ["mark", "tick"],
        ]
    )
    assert get_var(p, "n") == 4
    assert p.actions == [("tick",)] * 4


def test_repeatable_rising_edge():
    p = _Player()
    meta = {"repeat": True, "cooldown": 0.0, "was_true": False, "next_ok": 0}
    p.triggers = [[["var", "ready"], ["mark", "go"], meta]]
    p.run_triggers()
    assert p.actions == []
    set_var(p, "ready", 1)
    p.run_triggers()
    p.run_triggers()
    assert p.actions == [("go",)]
    set_var(p, "ready", 0)
    p.run_triggers()
    set_var(p, "ready", 1)
    p.run_triggers()
    assert p.actions == [("go",), ("go",)]


def test_repeatable_cooldown_while_true():
    p = _Player()
    p.world.time = 0
    meta = {"repeat": True, "cooldown": 5.0, "was_true": False, "next_ok": 0}
    p.triggers = [[["true"], ["mark", "wave"], meta]]
    p.run_triggers()
    p.run_triggers()
    assert p.actions == [("wave",)]
    p.world.time = 4999
    p.run_triggers()
    assert p.actions == [("wave",)]
    p.world.time = 5000
    p.run_triggers()
    assert p.actions == [("wave",), ("wave",)]


def test_should_fire_repeat_helper():
    meta = {"repeat": True, "cooldown": 0.0, "was_true": False, "next_ok": 0}
    assert should_fire_repeat(meta, True, 0) is True
    assert should_fire_repeat(meta, True, 1) is False
    assert should_fire_repeat(meta, False, 2) is False
    assert should_fire_repeat(meta, True, 3) is True


def test_on_death_add_global_and_skill_effect():
    world = _World()
    killer = _Player()
    killer.world = world
    victim = type("U", (), {})()
    victim.world = world
    victim.player = None
    victim.on_death_script = [["add_global", "wolves", 1]]
    attacker = type("A", (), {"player": killer, "world": world})()
    apply_on_death_script(victim, attacker)
    assert get_global(world, "wolves") == 1

    class _Skill(Skill):
        effect = ["add_var", "casts", 2]
        type_name = "s"

    assert _Skill._execute_add_var(attacker, None, world) is True
    assert get_var(killer, "casts") == 2
    assert apply_var_effect(attacker, world, "set_global", "wave", 9) is True
    assert get_global(world, "wave") == 9


# ---------------------------------------------------------------------------
# Comparison / count operators: count / lt / gt / le / ge / not
#
# These power map triggers such as the Joan of Arc chapter 2 supply-limit
# check:  trigger player1 (and (timer 600) (lt (count trade_cart) 6)) (defeat)
# ---------------------------------------------------------------------------


class _MockUnit:
    """Minimal stub unit for lang_count / lang_has tests."""

    def __init__(self, type_name):
        self.type_name = type_name


def test_lang_count_empty():
    p = _Player()
    p.units = []
    assert p.lang_count(["trade_cart"]) == 0
    assert p.lang_count(["militia"]) == 0


def test_lang_count_with_units():
    p = _Player()
    p.units = [
        _MockUnit("trade_cart"),
        _MockUnit("trade_cart"),
        _MockUnit("militia"),
    ]
    assert p.lang_count(["trade_cart"]) == 2
    assert p.lang_count(["militia"]) == 1
    assert p.lang_count(["aoe_knight"]) == 0


def test_lang_lt_with_numeric_operands():
    p = _Player()
    assert p.lang_lt([3, 5]) is True
    assert p.lang_lt([5, 3]) is False
    assert p.lang_lt([5, 5]) is False


def test_lang_lt_with_count_operands():
    p = _Player()
    p.units = [_MockUnit("trade_cart") for _ in range(5)]
    assert p.lang_lt([["count", "trade_cart"], 6]) is True   # 5 < 6
    assert p.lang_lt([["count", "trade_cart"], 5]) is False  # 5 < 5
    assert p.lang_lt([["count", "aoe_knight"], 10]) is True  # 0 < 10


def test_lang_gt():
    p = _Player()
    p.units = [_MockUnit("militia") for _ in range(7)]
    assert p.lang_gt([["count", "militia"], 5]) is True    # 7 > 5
    assert p.lang_gt([["count", "militia"], 7]) is False   # 7 > 7


def test_lang_le():
    p = _Player()
    p.units = [_MockUnit("aoe_archer") for _ in range(4)]
    assert p.lang_le([["count", "aoe_archer"], 4]) is True   # 4 <= 4
    assert p.lang_le([["count", "aoe_archer"], 5]) is True   # 4 <= 5
    assert p.lang_le([["count", "aoe_archer"], 3]) is False  # 4 <= 3


def test_lang_ge():
    p = _Player()
    p.units = [_MockUnit("man_at_arms") for _ in range(8)]
    assert p.lang_ge([["count", "man_at_arms"], 8]) is True   # 8 >= 8
    assert p.lang_ge([["count", "man_at_arms"], 7]) is True   # 8 >= 7
    assert p.lang_ge([["count", "man_at_arms"], 9]) is False  # 8 >= 9


def test_lang_not():
    p = _Player()
    assert p.lang_not(["true"]) is False
    assert p.lang_not(["false"]) is True
    assert p.lang_not([["count", "nonexistent"]]) is True  # 0 is falsy


def test_lang_or_multi():
    p = _Player()
    assert p.lang_or([["false"], ["true"]]) is True
    assert p.lang_or([["false"], ["false"]]) is False


def test_comparison_chain_lt_and_or():
    """(lt (count trade_cart) 6) OR <other condition> -- the Joan ch2 shape."""
    p = _Player()
    p.units = [_MockUnit("trade_cart") for _ in range(5)]
    # 5 < 6 -> True, so the whole (or ...) -> True
    assert p.lang_or([["lt", ["count", "trade_cart"], 6], ["false"]]) is True
