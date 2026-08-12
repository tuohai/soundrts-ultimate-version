"""Parse ``effect bonus`` / ``effect_bonus_targets`` argument lists.

Rules style::

    effect bonus rdg 1 rdg_range 1
    effect_bonus_targets aoe_archer skirmisher -building

``effect bonus`` is **stats/values only** (``*_vs`` is three tokens; list stats
like ``cost -50% 0`` keep every numeric slot). It must never list unit types.

Unit filters belong only on ``effect_bonus_targets`` (supports ``-`` exclusions,
same rules as ``phase_bonus_targets``). At load time those targets are appended
after the bonus tokens for storage; ``split_effect_bonus_args`` peels them back
apart when applying. Aliases ``tech_effect_targets`` / ``effect_targets`` still
work when parsing rules.
"""

from __future__ import annotations

from ..lib.nofloat import to_int

# Stats that are not in Rules.precision/int but still valid effect bonus keys.
_EXTRA_EFFECT_STATS = frozenset(
    {
        "cost",
        "time_cost",
        "population_cost",
        "production_cost",
        "production_time",
        "production_qty",
        "storage_bonus",
        "can_train",
        "food_deposit_qty",
        "resource_rewards",
        "resource_volume_max",
        "auto_production",
        "manual_production",
        "auto_cultivate",
        "manual_cultivate",
        "carry_capacity",
        "passenger_attack_types",
        "rdg_seq_times",
        "mdg_seq_times",
        "rdg_seq_secondary",
        "mdg_seq_secondary",
        "rdg_seq_secondary_live",
        "mdg_seq_secondary_live",
        "rdg_seq_interval",
        "mdg_seq_interval",
        "rdg_seq_secondary_rdg",
        "rdg_seq_secondary_mdg",
        "mdg_seq_secondary_rdg",
        "mdg_seq_secondary_mdg",
        "unpack_time",
        "kill_gold_vs",
        "gather_byproduct",
    }
)

# Multi-resource (or multi-slot) values: ``cost -50% 0``, ``storage_bonus 0 1``
_LIST_VALUE_STATS = frozenset(
    {
        "cost",
        "production_cost",
        "storage_bonus",
        "resource_rewards",
    }
)


def _rules_stat_sets():
    try:
        from ..definitions import rules

        precision = set(getattr(rules, "precision_properties", ()) or ())
        ints = set(getattr(rules, "int_properties", ()) or ())
    except Exception:
        precision, ints = set(), set()
    if not precision:
        precision = {
            "rdg",
            "mdg",
            "rdg_range",
            "mdg_range",
            "hp",
            "hp_max",
            "sight_range",
            "speed",
            "mdf",
            "rdf",
            "rdg_cd",
            "mdg_cd",
            "rdg_splash",
            "mdg_splash",
            "mdg_cover",
            "rdg_cover",
            "mdg_dodge",
            "rdg_dodge",
        }
    return precision, ints


def is_effect_bonus_stat(stat) -> bool:
    s = str(stat)
    if s == "can_train":
        return True
    if s.endswith("_vs") or s.endswith("_targets"):
        return True
    if s.startswith(("gather_time", "gather_qty", "gather_rate", "transport_", "carry_capacity")):
        return True
    if s in _EXTRA_EFFECT_STATS:
        return True
    precision, ints = _rules_stat_sets()
    return s in precision or s in ints


def _looks_numeric(tok) -> bool:
    t = str(tok)
    if t.endswith("%"):
        t = t[:-1]
    try:
        float(t)
        return True
    except (TypeError, ValueError):
        return False


def split_effect_bonus_args(args):
    """Return ``(bonus_tokens, target_names)``.

    ``bonus_tokens``: flat attr/value (or ``*_vs`` triples) list.
    ``target_names``: trailing tokens after the last complete bonus pair —
    these are stored by ``effect_bonus_targets``, not by inline ``effect bonus``.
    """
    args = list(args)
    bonus = []
    i = 0
    precision, _ints = _rules_stat_sets()
    while i < len(args):
        stat = args[i]
        st = str(stat)
        if st == "can_train":
            bonus.extend(args[i:])
            return bonus, []
        if i + 1 >= len(args):
            return bonus, [str(x) for x in args[i:]]
        if not is_effect_bonus_stat(stat):
            return bonus, [str(x) for x in args[i:]]
        if st.endswith("_vs") or st in ("kill_gold_vs", "gather_byproduct"):
            if i + 2 >= len(args) or not _looks_numeric(args[i + 2]):
                return bonus, [str(x) for x in args[i:]]
            target = args[i + 1]
            value = args[i + 2]
            # PRECISION-scale vs bonuses whose root is a precision property
            # (mdg_vs, mdf_vs, mdg_cover_vs, …). Keep percents as strings.
            root = st[:-3] if st.endswith("_vs") else ""
            if (
                root
                and root in precision
                and isinstance(value, str)
                and not value.endswith("%")
            ):
                try:
                    value = to_int(value)
                except (TypeError, ValueError, AssertionError):
                    pass
            bonus.extend([stat, target, value])
            i += 3
            continue
        value = args[i + 1]
        if st == "time_cost" and isinstance(value, str) and value.endswith("%"):
            bonus.extend([stat, value])
            i += 2
            continue
        if (
            st in precision
            and isinstance(value, str)
            and not value.endswith("%")
        ):
            try:
                value = to_int(value)
            except (TypeError, ValueError, AssertionError):
                pass
        if st in _LIST_VALUE_STATS:
            # ``cost -50% 0`` / ``storage_bonus 0 1``: keep all numeric slots
            # (same shape cost_effects.py expects on effect_parts).
            values = [value]
            i += 2
            while i < len(args) and _looks_numeric(args[i]) and not is_effect_bonus_stat(args[i]):
                values.append(args[i])
                i += 1
            bonus.extend([stat, *values])
            continue
        bonus.extend([stat, value])
        i += 2
    return bonus, []


def unit_matches_effect_types(unit, type_names) -> bool:
    """True if unit should receive a filtered effect bonus (empty = all).

    Supports ``-type`` exclusions and category names, same as ``phase_bonus_targets``.
    """
    if not type_names:
        return True
    from ..worldphase import Phase

    return Phase._unit_matches_targets(unit, type_names)
