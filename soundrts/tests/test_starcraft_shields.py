"""Shield layer regression tests (StarCraft plasma shields / SC2 shields)."""

from pathlib import Path

from soundrts.definitions import Rules
from soundrts.lib.nofloat import PRECISION


def _starcraft_rules_text():
    return Path("mods/starcraft/rules.txt").read_text(encoding="utf-8")


class _ShieldUnit:
    """Minimal stand-in for a unit carrying a shield pool."""

    shield_max = 100 * PRECISION
    shield = 100 * PRECISION
    shield_pierce = 0
    shield_regen = 5 * PRECISION
    shield_regen_cd = 0
    shield_regen_ready = 0
    shield_regen_next_time = 0
    shield_regen_prep_end_time = 0

    def notify(self, *_args, **_kwargs):
        pass


def test_shield_keywords_load_from_rules():
    rules = Rules()
    rules.load(
        """
def zealot
class soldier
shield_max 40
shield_regen 2
shield_regen_cd 3
shield_regen_ready 1
"""
    )
    zealot = rules.unit_class("zealot")
    assert zealot.shield_max == 40 * PRECISION
    assert zealot.shield_regen == 2 * PRECISION
    assert zealot.shield_regen_cd == 3 * PRECISION
    assert zealot.shield_regen_ready == 1 * PRECISION


def test_shield_absorbs_damage_before_hp():
    from soundrts.combat.damage_effects import DamageEffectsMixin

    unit = _ShieldUnit()
    remaining = DamageEffectsMixin._absorb_with_shield(unit, 30 * PRECISION)
    assert remaining == 0
    assert unit.shield == 70 * PRECISION

    # Overflow reaches HP.
    remaining = DamageEffectsMixin._absorb_with_shield(unit, 90 * PRECISION)
    assert remaining == 20 * PRECISION
    assert unit.shield == 0


def test_shield_pierce_damage_ignores_the_pool():
    """``shield_pierce`` belongs to the *attacker*.

    A psi storm (piercing damage) must hit the shield and the HP alike,
    so the flag is read from the attacker, not from the defender.
    """
    from soundrts.combat.damage_effects import DamageEffectsMixin

    unit = _ShieldUnit()

    class PiercingAttacker:
        shield_pierce = 1

    class NormalAttacker:
        shield_pierce = 0

    remaining = DamageEffectsMixin._absorb_with_shield(
        unit, 30 * PRECISION, PiercingAttacker()
    )
    assert remaining == 30 * PRECISION
    assert unit.shield == 100 * PRECISION

    # A normal attacker still eats the shield.
    remaining = DamageEffectsMixin._absorb_with_shield(
        unit, 30 * PRECISION, NormalAttacker()
    )
    assert remaining == 0
    assert unit.shield == 70 * PRECISION


def test_a_defender_with_shield_pierce_is_not_protected_by_its_own_pool():
    """The defender's own ``shield_pierce`` never shields it."""
    from soundrts.combat.damage_effects import DamageEffectsMixin

    unit = _ShieldUnit()
    unit.shield_pierce = 1
    remaining = DamageEffectsMixin._absorb_with_shield(unit, 30 * PRECISION)
    assert remaining == 30 * PRECISION
    assert unit.shield == 100 * PRECISION


def test_unit_without_shield_is_untouched():
    from soundrts.combat.damage_effects import DamageEffectsMixin

    class Unit:
        shield_max = 0
        shield = 0

    unit = Unit()
    remaining = DamageEffectsMixin._absorb_with_shield(unit, 30 * PRECISION)
    assert remaining == 30 * PRECISION


def test_shield_hit_resets_the_regeneration_timer():
    from soundrts.combat.damage_effects import DamageEffectsMixin

    unit = _ShieldUnit()
    unit.shield_regen_next_time = 999999
    DamageEffectsMixin._absorb_with_shield(unit, 10 * PRECISION)
    assert unit.shield_regen_next_time == 0


def test_shield_regeneration_fills_the_pool():
    from soundrts.worldunit.world_status_update import CreatureStatusUpdate

    unit = _ShieldUnit()
    unit.shield = 10 * PRECISION
    CreatureStatusUpdate._regenerate_shield(unit, 1000)
    assert unit.shield == 15 * PRECISION
    # Never exceeds the maximum.
    unit.shield = 100 * PRECISION
    CreatureStatusUpdate._regenerate_shield(unit, 2000)
    assert unit.shield == 100 * PRECISION


def test_shield_regeneration_respects_the_cooldown():
    from soundrts.worldunit.world_status_update import CreatureStatusUpdate

    unit = _ShieldUnit()
    unit.shield = 10 * PRECISION
    unit.shield_regen_cd = 3 * PRECISION
    CreatureStatusUpdate._regenerate_shield(unit, 1000)
    assert unit.shield == 15 * PRECISION
    # Too soon for the next tick.
    CreatureStatusUpdate._regenerate_shield(unit, 2000)
    assert unit.shield == 15 * PRECISION
    # After the cooldown.
    CreatureStatusUpdate._regenerate_shield(unit, 1000 + 3 * PRECISION)
    assert unit.shield == 20 * PRECISION


def test_shield_max_bonus_grows_the_pool():
    from soundrts.worldupgrade.attribute_effects import AttributeEffectsMixin

    unit = _ShieldUnit()
    AttributeEffectsMixin._handle_shield_max_bonus(unit, 10 * PRECISION)
    assert unit.shield_max == 110 * PRECISION
    assert unit.shield == 110 * PRECISION


def test_starcraft_mod_declares_shields():
    """The StarCraft mod must actually use the new shield layer."""
    rules = Rules()
    rules.load(_starcraft_rules_text())
    zealot = rules.unit_class("zealot")
    assert getattr(zealot, "shield_max", 0) > 0
    dragoon = rules.unit_class("dragoon")
    assert getattr(dragoon, "shield_max", 0) > 0
    # Terran and Zerg units have no shield pool.
    marine = rules.unit_class("marine")
    assert getattr(marine, "shield_max", 0) == 0
    zergling = rules.unit_class("zergling")
    assert getattr(zergling, "shield_max", 0) == 0


def test_plasma_shield_upgrade_adds_shield():
    rules = Rules()
    rules.load(_starcraft_rules_text())
    text = _starcraft_rules_text()
    assert "effect bonus shield_max" in text
    upgrade = rules.unit_class("protoss_plasma_shields")
    assert upgrade is not None
    rows = upgrade.effect
    assert any("shield_max" in row for row in rows)


def test_no_rules_keyword_lives_in_two_property_sets():
    """A keyword must belong to exactly ONE property set.

    ``read()`` checks ``int_properties`` before ``precision_properties``,
    so a keyword listed in both would parse differently depending on the
    path: a direct ``shield_pierce 1`` row yielded 1, while
    ``effect bonus shield_pierce 1`` was PRECISION-scaled to 1000 by
    ``split_effect_bonus_parse.split_effect_bonus_args``.  The two must
    agree, which is only possible when the sets are disjoint.
    """
    from soundrts.definitions import rules as global_rules

    sets = {
        "precision": global_rules.precision_properties,
        "int": global_rules.int_properties,
        "string": global_rules.string_properties,
        "string_list": global_rules.string_list_properties,
        "int_list": global_rules.int_list_properties,
        "precision_list": global_rules.precision_list_properties,
    }
    names = list(sets)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            overlap = sets[names[i]] & sets[names[j]]
            assert not overlap, (
                f"{sorted(overlap)} is in both {names[i]} and {names[j]}"
            )


def test_shield_pierce_is_a_plain_boolean_flag():
    """``shield_pierce`` is a flag: it must parse as 1, never PRECISION-scaled."""
    from soundrts.definitions import rules as global_rules
    from soundrts.worldupgrade.effect_bonus_parse import split_effect_bonus_args

    assert "shield_pierce" in global_rules.int_properties
    assert "shield_pierce" not in global_rules.precision_properties

    rules = Rules()
    rules.read(
        """
def psi_storm
class soldier
shield_pierce 1
"""
    )
    assert rules.get("psi_storm", "shield_pierce", 0) == 1

    # The effect-bonus path must produce the very same scale.
    bonus, targets = split_effect_bonus_args(["shield_pierce", "1"])
    assert bonus == ["shield_pierce", "1"]
    assert targets == []
