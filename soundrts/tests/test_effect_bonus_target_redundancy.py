# -*- coding: utf-8 -*-
"""``effect_bonus_targets`` must not name a base class next to its subclass.

The target matcher (:meth:`Phase._unit_matches_single_target`) resolves three
things for a candidate type:

1. an exact ``type_name`` match,
2. a match in the ``is_a`` chain (including ``expanded_is_a``),
3. a match on the base class name.

So a target list that names *both* a base class and one of its descendants
is redundant — and harmful, because the base class drags in every other
descendant as well.

The canonical example is the Goths' *Anarchy*::

    effect bonus can_train huskarl 1
    effect_bonus_targets goth_barracks barracks

``goth_barracks`` is ``is_a barracks``, and *every* civ's Barracks is too
(41 of them).  Naming ``barracks`` therefore made the row match all 41 civ
Barracks.  Naming the derived type alone is both correct and
sufficient.

Under the universal target-as-authorisation model this rule became even
more important: a filtered row's target list *is* its authorisation, so a
stray base class would leak the row to every one of its descendants.

This module guards that rule against regressions.
"""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def aoe2_rules():
    from soundrts.definitions import Rules

    r = Rules()
    r.load(
        (ROOT / "res" / "rules.txt").read_text(encoding="utf-8"),
        (ROOT / "mods" / "aoe2" / "rules.txt").read_text(encoding="utf-8"),
    )
    return r


def _proxy(rules, name):
    cls = rules.unit_class(name)
    return type(
        "P",
        (),
        {
            "type_name": name,
            "expanded_is_a": set(getattr(cls, "expanded_is_a", ()) or ()),
            "cls": cls,
        },
    )()


def _descendants(rules, base):
    """All types whose ``is_a`` chain contains *base*."""
    out = []
    for name in rules.classnames():
        cls = rules.unit_class(name)
        if base in set(getattr(cls, "expanded_is_a", ()) or ()):
            out.append(name)
    return sorted(out)


def _matches(unit, targets):
    """The engine's own target matcher (avoids a circular import at module load)."""
    from soundrts.worldphase import Phase

    return Phase._unit_matches_targets(unit, targets)


# ---------------------------------------------------------------------------
# 1. The concrete case: Anarchy
# ---------------------------------------------------------------------------


def test_anarchy_targets_only_the_goth_barracks(aoe2_rules):
    """Anarchy must name ``goth_barracks`` and nothing broader."""
    from soundrts.worldupgrade.effect_bonus_parse import tech_target_rows

    rows = list(tech_target_rows(aoe2_rules.unit_class("anarchy")))
    assert rows, "anarchy declares no targeted effect row"
    for _bonus, targets in rows:
        assert list(targets) == ["goth_barracks"], targets


def test_anarchy_no_longer_reaches_other_civ_barracks(aoe2_rules):
    """The row must match exactly one type: the Goth Barracks."""
    from soundrts.worldphase import Phase

    targets = ["goth_barracks"]
    matched = [
        name
        for name in aoe2_rules.classnames()
        if Phase._unit_matches_targets(_proxy(aoe2_rules, name), targets)
    ]
    assert matched == ["goth_barracks"], matched


def test_the_generic_barracks_would_have_matched_all_civ_barracks(aoe2_rules):
    """Documents *why* the base class must not be listed.

    This is the regression that the fix removes: naming ``barracks`` pulls
    in all 41 civ Barracks.
    """
    from soundrts.worldphase import Phase

    matched = [
        name
        for name in aoe2_rules.classnames()
        if Phase._unit_matches_targets(_proxy(aoe2_rules, name), ["barracks"])
    ]
    assert len(matched) > 30, matched
    assert "goth_barracks" in matched
    assert "briton_barracks" in matched


def test_goth_barracks_is_the_type_the_goths_actually_build(aoe2_rules):
    """The faction table maps the Goths' Barracks to ``goth_barracks``.

    The rows below ``def goths`` are the faction table: ``barracks
    goth_barracks`` means "a Goth builds ``goth_barracks``".
    """
    mapped = aoe2_rules.get("goths", "barracks")
    assert mapped, "the Goths have no Barracks mapping"
    assert "goth_barracks" in mapped


def test_anarchy_still_reaches_the_goth_barracks_at_runtime(aoe2_rules):
    """End-to-end: researching Anarchy adds the Huskarl to the Goth Barracks."""
    from soundrts.worldupgrade import Upgrade

    tech_cls = aoe2_rules.unit_class("anarchy")
    assert issubclass(tech_cls, Upgrade)

    barracks_cls = aoe2_rules.unit_class("goth_barracks")

    class _Player:
        upgrades = ["anarchy"]
        units = []
        faction = "goths"
        allied_victory = ()

        def level(self, name):
            return 1 if name in self.upgrades else 0

    player = _Player()
    barracks = barracks_cls.__new__(barracks_cls)
    barracks.player = player
    barracks._applied_upgrade_effects = set()
    player.units = [barracks]

    tech_cls.upgrade_player(player)

    from soundrts.world_build_rules import effective_can_train

    assert "huskarl" in list(effective_can_train(barracks)), effective_can_train(
        barracks
    )


# ---------------------------------------------------------------------------
# 2. The general rule
# ---------------------------------------------------------------------------


def test_a_named_base_class_never_drags_in_unauthorised_types(aoe2_rules):
    """A named base class must not reach another civ's units.

    This is the real invariant behind the redundancy rule.  Naming a base
    class in ``effect_bonus_targets`` pulls in *all* of its descendants,
    even those the row's author never had in mind.

    The Goths' *Anarchy* was the textbook case: its filter named
    ``goth_barracks barracks``, and ``barracks`` is the base of all 41 civ
    Barracks.  Its fix (naming only ``goth_barracks``) is what this test
    guards.

    Under the universal target-as-authorisation model the target list *is*
    the authorisation, so a stray base class would leak the row to every
    descendant — the rule is therefore even more important than before.

    The check is *civilisation-aware*: a descendant that only one civ owns
    is a leak when that civ cannot research the tech.  Types no civ trains
    (dead shells, e.g. ``imperial_skirmisher``) are ignored, and so are
    civ-specific unique units (``is_a unique_unit``) — each of them belongs
    to exactly one civilisation and can never show up in another civ's army.
    """
    from soundrts.worldupgrade.effect_bonus_parse import split_effect_bonus_args

    factions = list(aoe2_rules.factions)
    building_keys = (
        "barracks",
        "archery_range",
        "stables",
        "blacksmith",
        "university",
        "aoe_castle",
        "workshop",
        "shipyard",
        "townhall",
        "monastery",
    )

    def _is_unique(type_name):
        cls = aoe2_rules.unit_class(type_name)
        return "unique_unit" in set(getattr(cls, "expanded_is_a", ()) or ())

    def _trainable_by(civ):
        """Every type the civ can train, with its ``is_a`` descendants."""
        out = set()
        for key in building_keys:
            for building in aoe2_rules.get(civ, key) or ():
                cls = aoe2_rules.unit_class(building)
                if cls is None:
                    continue
                for unit in aoe2_rules.class_rules_attr(cls, "can_train", ()) or {}:
                    out.add(unit)
                    out.update(_descendants(aoe2_rules, unit))
        return out

    def _researchable_by(civ):
        out = set()
        for key in building_keys:
            for building in aoe2_rules.get(civ, key) or ():
                cls = aoe2_rules.unit_class(building)
                if cls is None:
                    continue
                out.update(aoe2_rules.class_rules_attr(cls, "can_research", ()) or ())
        return out

    trainable = {civ: _trainable_by(civ) for civ in factions}
    researchable = {civ: _researchable_by(civ) for civ in factions}

    offenders = []
    for name in aoe2_rules.classnames():
        cls = aoe2_rules.unit_class(name)
        effect = getattr(cls, "effect", None)
        if not effect:
            continue
        # The civs that can actually research this tech.
        owners = {civ for civ in factions if name in researchable[civ]}
        if not owners:
            # Nobody can research it — a different defect, reported by
            # ``test_techs_whose_targeted_effect_reaches_nobody``.
            continue
        rows = (
            effect
            if isinstance(effect, list) and effect and isinstance(effect[0], list)
            else [effect]
        )
        for row in rows:
            if not row or row[0] != "bonus":
                continue
            _bonus, targets = split_effect_bonus_args(list(row[1:]))
            if len(targets) < 2:
                continue
            for base in targets:
                children = [
                    d for d in _descendants(aoe2_rules, base) if d in targets
                ]
                if not children:
                    # The base is not paired with one of its own children —
                    # it is used on its own, which is a different (and legal)
                    # pattern.
                    continue
                for descendant in _descendants(aoe2_rules, base):
                    if descendant in targets or _is_unique(descendant):
                        continue
                    leaked_to = {
                        civ for civ in factions if descendant in trainable[civ]
                    }
                    if not leaked_to:
                        # No civ trains it (a dead shell) — nothing leaks.
                        continue
                    if leaked_to & owners:
                        # The civs that own it can also research the tech.
                        continue
                    offenders.append(
                        (
                            name,
                            list(targets),
                            base,
                            descendant,
                            sorted(leaked_to),
                            sorted(owners),
                        )
                    )

    assert not offenders, offenders


def test_techs_whose_targeted_effect_reaches_nobody(aoe2_rules):
    """Every tech with a targeted effect row must reach at least one type.

    A tech whose ``effect_bonus_targets`` names types that nothing matches
    has an effect that never fires.

    Under the universal target-as-authorisation model this used to be a
    long list of "dead" techs (23 of them: marauders, kamandaran,
    szlachta_privileges, atheism, detinets, …).  The model removed the
    second gate, so every filtered row now reaches the types it names —
    and the list of dead techs is empty.
    """
    from soundrts.worldupgrade.effect_bonus_parse import split_effect_bonus_args

    dead = []
    for name in aoe2_rules.classnames():
        cls = aoe2_rules.unit_class(name)
        effect = getattr(cls, "effect", None)
        if not effect:
            continue
        rows = (
            effect
            if isinstance(effect, list) and effect and isinstance(effect[0], list)
            else [effect]
        )
        targeted = []
        for row in rows:
            if not row or row[0] != "bonus":
                continue
            _bonus, targets = split_effect_bonus_args(list(row[1:]))
            if targets:
                targeted.append(targets)
        if not targeted:
            continue
        effective = set()
        for targets in targeted:
            for other in aoe2_rules.classnames():
                if _matches(_proxy(aoe2_rules, other), targets):
                    effective.add(other)
        if not effective:
            dead.append(name)

    known_dead: set[str] = set()

    assert set(dead) == known_dead, sorted(set(dead) ^ known_dead)
