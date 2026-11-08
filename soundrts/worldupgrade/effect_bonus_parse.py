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

from types import SimpleNamespace

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
        "pack_time",
        "kill_resource_vs",
        "gather_byproduct",
        "research_time",
        "research_time_percent",
        # D-Phase 3: AoE2 Bulgarians Mill-tech discount; other civs may follow.
        # Stored per-player; consumed by apply_research_cost_modifiers.
        # Rules: ``research_cost_tech_discount <slot> <pct> <flat> <tech_name>…``
        #   slot  = resource index (0=gold,1=wood,2=food,3=stone)
        #   pct   = percent discount, e.g. -50%  (negative = reduce cost)
        #   flat  = flat reduction per slot, e.g. 0  (not currently used)
        #   techs = one or more tech type-names this applies to
        # NB: do NOT name this ``research_cost_discount`` — that field already
        # means "per-age global research discount" (e.g. Chinese -5% feudal).
        "research_cost_tech_discount",
        # D-Phase 2: trade-cart reward scaling (AoE2 Italians Silk Road etc.)
        "trade_reward_bonus_pct",
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
            "mdg_hit_rate",
            "rdg_hit_rate",
            "mdg_dodge_rate",
            "rdg_dodge_rate",
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


def _split_can_train_args(args):
    """Split a ``can_train`` row into ``(bonus_tokens, target_names)``.

    ``args`` starts with the literal ``can_train``.  The accepted shapes are

    * ``can_train <count>`` — a uniform increment for every unit the host
      already trains;
    * ``can_train <unit> <count> [<unit> <count> …]`` — explicit pairs;
    * ``can_train <unit>… <count>`` — one count for the listed units.

    The trailing ``effect_bonus_targets`` (stored after the bonus tokens at
    load time) must be peeled off, otherwise the target names are mistaken
    for further trainable units.  That leak had a real effect: the AoE2
    Goths' *Anarchy* (``effect bonus can_train huskarl 1`` with
    ``effect_bonus_targets goth_barracks barracks``) offered "goth_barracks"
    and "barracks" as trainable units at every building that listed the
    technology.

    The split is done by *shape*, not by looking the names up in the rule
    set: a group of unit names is always followed by its count, so any
    trailing names that are not followed by a count are the target list.
    That keeps the parse independent of which rule set happens to be
    installed.
    """
    args = list(args)
    if not args or str(args[0]) != "can_train":
        return list(args), []

    body = args[1:]
    pending = []
    pos = 0
    while pos < len(body):
        tok = body[pos]
        if _looks_numeric(tok):
            if pending:
                # ``pending`` names + this count form one bonus group.
                pos += 1
                pending = []
                continue
            # A bare count: a uniform increment for every trainable unit.
            pos += 1
            continue
        pending.append(tok)
        pos += 1

    # Whatever is still pending has no count behind it: those are the
    # ``effect_bonus_targets`` names.
    boundary = len(body) - len(pending)
    return ["can_train"] + list(body[:boundary]), [str(t) for t in body[boundary:]]


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
            # ``can_train`` has a variable shape:
            #   can_train <count>
            #   can_train <unit> <count> [<unit> <count> …]
            #   can_train <unit>… <count>
            # It must be parsed here rather than by the generic pair loop,
            # because the unit names are not stats.  The trailing
            # ``effect_bonus_targets`` (stored after the bonus tokens) has to
            # be peeled off here, otherwise the target names are treated as
            # further trainable units and the effect leaks to every building
            # that lists the technology in ``can_use_tech``.
            bonus_tokens, targets = _split_can_train_args(args[i:])
            bonus.extend(bonus_tokens)
            return bonus, targets
        if i + 1 >= len(args):
            return bonus, [str(x) for x in args[i:]]
        if not is_effect_bonus_stat(stat):
            return bonus, [str(x) for x in args[i:]]
        if st == "kill_resource_vs":
            # kill_resource_vs <victim_type> <resource> <amount>
            if i + 3 >= len(args) or not _looks_numeric(args[i + 3]):
                return bonus, [str(x) for x in args[i:]]
            bonus.extend([stat, args[i + 1], args[i + 2], args[i + 3]])
            i += 4
            continue
        if st == "research_cost_tech_discount":
            # Greedily consume: stat slot pct flat [tech_name…]
            # Tech names are not stat names so consume them all here.
            bonus.extend([str(a) for a in args[i:]])
            i = len(args)
            continue
        if st == "gather_byproduct":
            # 4-token: source product rate  |  3-token: source rate (product=resource1)
            # Optional trailing per_food / ratio = wood per food gathered.
            if (
                i + 3 < len(args)
                and _looks_numeric(args[i + 3])
                and not _looks_numeric(args[i + 2])
            ):
                if (
                    i + 4 < len(args)
                    and str(args[i + 4]).lower() in ("per_food", "ratio")
                ):
                    bonus.extend(
                        [stat, args[i + 1], args[i + 2], args[i + 3], "per_food"]
                    )
                    i += 5
                    continue
                bonus.extend([stat, args[i + 1], args[i + 2], args[i + 3]])
                i += 4
                continue
            if i + 2 >= len(args) or not _looks_numeric(args[i + 2]):
                return bonus, [str(x) for x in args[i:]]
            bonus.extend([stat, args[i + 1], args[i + 2]])
            i += 3
            continue
        if st.endswith("_vs"):
            if i + 2 >= len(args) or not _looks_numeric(args[i + 2]):
                return bonus, [str(x) for x in args[i:]]
            target = args[i + 1]
            value = args[i + 2]
            # PRECISION-scale vs bonuses whose root is a precision property
            # (mdg_vs, mdf_vs, mdg_hit_rate_vs, …). Keep percents as strings.
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


# ---------------------------------------------------------------------------
# Gate 1 (authorisation) vs Gate 2 (row filter)
# ---------------------------------------------------------------------------
#
# A filtered ``effect bonus`` row reaches a unit through two independent ways:
#
#   Gate 1 — authorisation: the tech is listed in the unit's ``can_use`` /
#            ``can_use_tech`` / ``can_use_skill``.  This is also what the UI
#            shows as "可使用的科技" and what the order layer aggregates when
#            it collects the techs that may lower a unit's build/train cost.
#
#   Gate 2 — row filter: ``effect_bonus_targets`` restricts the row to
#            matching unit types (exact name, ``is_a`` chain, base class, or
#            ``-type`` exclusions).
#
# For a *filtered* row the target list is the **sole definition of reach**:
# a unit that matches the row's target list enjoys the row whether or not
# it repeats the tech in ``can_use_tech``.  That is not a special case — it
# is exactly how the cost/time rows already work in
# ``soundrts/worldorders/base.py``, where a filtered cost effect is matched
# by target alone (``Phase._unit_matches_targets``).
#
# The target list belongs to the *row*, not to the tech: one tech may carry
# several rows with different targets (AoE2 Heavy Plow: +125 farm capacity
# *and* +1 villager carry capacity).
#
# Because the target list now grants reach on its own, it must never name a
# base class next to one of its descendants: the base drags in *every*
# descendant.  The canonical example is the Goths' *Anarchy*, whose filter
# must name ``goth_barracks`` alone — ``barracks`` is the ancestor of all 41
# civ Barracks.  See ``soundrts/tests/test_effect_bonus_target_redundancy.py``.


def tech_target_rows(tech_cls):
    """Yield ``(bonus_tokens, targets)`` for the tech's filtered effect rows.

    Only rows that actually carry a target list are returned; rows without
    one are unfiltered and are governed by Gate 1 alone.
    """
    effect = getattr(tech_cls, "effect", None)
    if not effect:
        return
    if isinstance(effect, list) and effect and isinstance(effect[0], list):
        rows = effect
    elif isinstance(effect, list) and effect and effect[0] == "bonus":
        rows = [effect]
    else:
        return
    for row in rows:
        if not row or row[0] != "bonus":
            continue
        bonus, targets = split_effect_bonus_args(list(row[1:]))
        if not targets:
            continue
        yield bonus, targets


def _cached_tech_target_rows(tech_cls):
    """The filtered rows of *tech_cls*, parsed once and cached on the class.

    Parsing an effect row splits its tokens apart, which is not free; the
    result never changes for a given rules class, so it is memoised on the
    class itself (a rules reload creates fresh classes, so the cache is
    invalidated automatically).
    """
    effect = getattr(tech_cls, "effect", None)
    cache = getattr(tech_cls, "_effect_target_rows_cache", None)
    if cache is not None and cache[0] is effect:
        return cache[1]
    rows = tuple(
        (tuple(bonus), tuple(targets))
        for bonus, targets in tech_target_rows(tech_cls)
    )
    try:
        tech_cls._effect_target_rows_cache = (effect, rows)
    except Exception:
        pass
    return rows


def unit_matches_tech_targets(unit, tech_cls) -> bool:
    """True if *unit* matches any of *tech_cls*'s filtered effect rows.

    The target list of a filtered row is the sole definition of its reach:
    a matching unit enjoys that row whether or not it lists the tech in
    ``can_use_tech``.
    """
    for _bonus, targets in _cached_tech_target_rows(tech_cls):
        if unit_matches_effect_types(unit, targets):
            return True
    return False


def type_proxy(type_cls):
    """Minimal proxy for matching a *type* against ``effect_bonus_targets``.

    The order layer works on classes (``order.type``) rather than on unit
    instances, but ``Phase._unit_matches_targets`` only needs the type name,
    the ``is_a`` chain and the base class.
    """
    if type_cls is None:
        return None
    name = getattr(type_cls, "type_name", None) or getattr(type_cls, "__name__", "")
    expanded = getattr(type_cls, "expanded_is_a", None) or ()
    return SimpleNamespace(
        type_name=name,
        expanded_is_a=set(expanded) if not isinstance(expanded, set) else expanded,
        cls=type_cls,
    )


def type_matches_tech_targets(type_cls, tech_cls) -> bool:
    """True if the *type* matches any of *tech_cls*'s filtered effect rows.

    The class-level counterpart of :func:`unit_matches_tech_targets`, used by
    the order layer (cost / population / time aggregation).
    """
    proxy = type_proxy(type_cls)
    if proxy is None:
        return False
    return unit_matches_tech_targets(proxy, tech_cls)


def researched_techs_for_unit(unit, researched):
    """The researched techs whose filtered effect rows target *unit*.

    A filtered ``effect bonus`` row's ``effect_bonus_targets`` list is the
    sole definition of its reach (see the module docstring in
    ``soundrts/worldupgrade/base.py``): a unit that matches the list enjoys
    the row even though the unit does not repeat the tech in
    ``can_use_tech``.

    This helper is the *display* counterpart of that rule: it answers
    "which of the techs this player has researched actually apply to this
    unit?", so the status readout (the ``v`` key) and the attribute panel
    can list them (e.g. the AoE2 farm listing 马轭 / 重犁 / 轮作 after they
    were researched in the mill).

    *researched* is the list of tech names the player has (usually
    ``player.upgrades``).  The result preserves that order and never repeats
    a name.
    """
    if not researched:
        return []
    try:
        from ..definitions import rules as _rules
    except Exception:
        return []

    result = []
    seen = set()
    for tech_name in researched:
        if not tech_name or tech_name in seen:
            continue
        seen.add(tech_name)
        tech_cls = _rules.unit_class(tech_name)
        if tech_cls is None:
            continue
        try:
            if unit_matches_tech_targets(unit, tech_cls):
                result.append(tech_name)
        except Exception:
            continue
    return result
