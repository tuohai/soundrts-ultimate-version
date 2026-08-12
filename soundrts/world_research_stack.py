"""Rules-driven HP stack when researching flagged upgrades.

Upgrade::

    research_stack_hp 1

Race::

    research_stack_hp_bonus 5 monk

Each time the player completes an upgrade with ``research_stack_hp 1``, apply
``effect bonus hp <N>`` to matching units and store the same bonus in
``_phase_bonus_pool`` for future trains. No civ/tech type-name hardcoding.
"""

from __future__ import annotations

from .definitions import rules
from .lib.log import warning
from .lib.nofloat import PRECISION


def _as_int(val, default=0):
    if isinstance(val, (list, tuple)):
        val = val[0] if val else default
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def parse_research_stack_hp_bonus(faction):
    """Return (hp_delta_internal, unit_type_names) or (0, ())."""
    if not faction:
        return 0, ()
    raw = rules.get(faction, "research_stack_hp_bonus")
    if not raw:
        return 0, ()
    if isinstance(raw, (list, tuple)):
        tokens = list(raw)
    else:
        tokens = str(raw).split()
    if not tokens:
        return 0, ()
    # Display HP (15) → internal PRECISION units, matching effect bonus hp parsing.
    display = _as_int(tokens[0], 0)
    if display <= 0:
        return 0, ()
    types = tuple(str(t) for t in tokens[1:] if t)
    return display * PRECISION, types


def upgrade_has_research_stack_hp(upgrade_cls) -> bool:
    return _as_int(getattr(upgrade_cls, "research_stack_hp", 0), 0) > 0


def apply_research_stack_hp_on_complete(player, upgrade_cls):
    """Call after ``player.upgrades`` gains this upgrade."""
    if player is None or upgrade_cls is None:
        return
    if not upgrade_has_research_stack_hp(upgrade_cls):
        return
    faction = getattr(player, "faction", None)
    delta, unit_types = parse_research_stack_hp_bonus(faction)
    if delta <= 0 or not unit_types:
        return

    if getattr(player, "_phase_bonus_pool", None) is None:
        player._phase_bonus_pool = []
    bonus_args = ["hp", delta]
    player._phase_bonus_pool.append((list(bonus_args), list(unit_types)))

    from .worldupgrade import Upgrade
    from .worldphase import _unit_matches_type_names

    for unit in list(getattr(player, "units", ()) or ()):
        if not _unit_matches_type_names(unit, unit_types):
            continue
        try:
            Upgrade.effect_bonus(unit, 0, *bonus_args)
        except Exception as e:
            warning(
                "research_stack_hp on %s failed for %s: %s",
                getattr(upgrade_cls, "type_name", upgrade_cls),
                getattr(unit, "type_name", unit),
                e,
            )
