"""Rules-driven AoE2 DE team bonuses: engine-side helpers.

The AoE2 DE "team bonus" of a civilisation applies to *the player and all of
their allies*.  The rules file stores each bonus on the civilisation's race
definition (``mods/aoe2/rules.txt``); the engine reads it here.

Two families live here:

1. **Declarative** bonuses that are already expressible with the generic
   ``team_on_phase <phase> <stat> <value> [targets…]`` row are handled by
   :func:`soundrts.worldphase.apply_parsed_on_phase_bonus` — nothing to do
   here.

2. **Special** bonuses that need dedicated engine support because they cannot
   be expressed as a plain attribute delta on the affected units:

   ==========================================  ================================
   AoE2 DE team bonus                           engine support
   ==========================================  ================================
   Building repairs cost -25% (Georgians)       ``team_repair_cost_pct``
   Military buildings provide +5 population      ``team_military_building_pop``
   Outposts cost no stone (Ethiopians)          ``team_free_stone_buildings``
   Start with a free Llama (Incas)              ``team_start_free_llama``
   Relics generate food too (Burgundians)       ``team_relic_food``
   Relics visible at game start (Burmese)       ``team_relic_visible``
   Units train faster (Magyars / Turks)         ``team_train_speed_pct``
   ==========================================  ================================

Every helper reads the *best* value among ``player.allied_victory`` so that a
player with several allies picks up the strongest version of each bonus.
"""

from __future__ import annotations

from types import SimpleNamespace

from .definitions import MAX_NB_OF_RESOURCE_TYPES, rules
from .lib.log import warning
from .lib.nofloat import PRECISION
from .worlditem import faction_int_attr
from .worldupgrade.attribute_effects import AttributeEffectsMixin
from .worldupgrade.effect_bonus_parse import split_effect_bonus_args


def _entries(faction, key):
    if not faction:
        return []
    raw = rules.get(faction, key) or []
    if not raw:
        raw = (rules._dict.get(faction, {}) or {}).get(key) or []
    return raw


def _as_token_lists(raw):
    out = []
    for entry in raw:
        if not entry:
            continue
        if isinstance(entry[0], list):
            out.append(list(entry))
        else:
            out.append(list(entry))
    return out


def _type_proxy(type_cls):
    """Minimal object for ``Phase._unit_matches_targets``."""
    if type_cls is None:
        return None
    name = getattr(type_cls, "type_name", None) or getattr(type_cls, "__name__", "")
    expanded = getattr(type_cls, "expanded_is_a", None) or ()
    return SimpleNamespace(
        type_name=name,
        expanded_is_a=set(expanded) if not isinstance(expanded, set) else expanded,
        cls=type_cls,
    )


def _parse_bonus_and_targets(rest):
    if not rest:
        return [], []
    return split_effect_bonus_args(rest)


def apply_grant_tech_on_phase(player, phase_name):
    """Instant-research race ``grant_tech_on_phase <phase> tech…``."""
    from .worldupgrade import Upgrade
    from .worldphase import is_a_phase

    faction = getattr(player, "faction", None)
    if not faction or not phase_name:
        return
    for entry in _as_token_lists(_entries(faction, "grant_tech_on_phase")):
        if not entry or str(entry[0]) != str(phase_name):
            continue
        for tech_name in entry[1:]:
            tech_name = str(tech_name)
            if not tech_name:
                continue
            if tech_name in (getattr(player, "upgrades", None) or ()):
                continue
            cls = rules.unit_class(tech_name)
            if cls is None or not isinstance(cls, type):
                continue
            if is_a_phase(cls):
                continue
            try:
                if hasattr(cls, "upgrade_player") and issubclass(cls, Upgrade):
                    cls.upgrade_player(player)
            except Exception as e:
                warning(
                    "grant_tech_on_phase %s %s for %s failed: %s",
                    phase_name,
                    tech_name,
                    faction,
                    str(e),
                )


def apply_faction_team_on_phase_effects(source_player, phase_name):
    """Apply source civ ``team_on_phase`` to every allied_victory member."""
    from .worldphase import apply_parsed_on_phase_bonus

    faction = getattr(source_player, "faction", None)
    if not faction or not phase_name:
        return
    allies = list(getattr(source_player, "allied_victory", None) or (source_player,))
    entries = _as_token_lists(_entries(faction, "team_on_phase_effects"))
    for idx, entry in enumerate(entries):
        if not entry or str(entry[0]) != str(phase_name):
            continue
        rest = entry[1:]
        bonus_args, unit_types = _parse_bonus_and_targets(rest)
        if not bonus_args:
            continue
        for ally in allies:
            if ally is None:
                continue
            seen = getattr(ally, "_team_on_phase_keys", None)
            if seen is None:
                seen = set()
                ally._team_on_phase_keys = seen
            key = (id(source_player), str(phase_name), idx)
            if key in seen:
                continue
            seen.add(key)
            try:
                apply_parsed_on_phase_bonus(
                    ally, bonus_args, unit_types, phase_name, faction
                )
            except Exception as e:
                warning(
                    "team_on_phase %s from %s onto %s failed: %s",
                    phase_name,
                    faction,
                    getattr(ally, "faction", ally),
                    str(e),
                )


def team_farm_food_pct(player):
    """Best allied ``team_farm_food_pct`` (Chinese farms +10%, etc.)."""
    best = 0
    allies = getattr(player, "allied_victory", None) or (player,)
    for ally in allies:
        best = max(best, faction_int_attr(ally, "team_farm_food_pct", 0))
    return best


def team_supplies_pct(player):
    """Best allied ``team_supplies_pct`` (AoE2 Slavs: +10% to allies' barracks).

    Generic: stored on the race def via ``team_supplies_pct N``. Engine reads
    it in production rate math (production_qty / production_time path).
    """
    best = 0
    allies = getattr(player, "allied_victory", None) or (player,)
    for ally in allies:
        best = max(best, faction_int_attr(ally, "team_supplies_pct", 0))
    return best


def team_trade_capacity_pct(player):
    """Best allied ``team_trade_capacity_pct`` (AoE2 Magyars: +50% trade cart
    gold capacity for the player and all allies).

    Generic: stored on the race def via ``team_trade_capacity_pct N``.
    Engine reads it in market settlement (mirrors trade_reward_bonus_pct).
    """
    best = 0
    allies = getattr(player, "allied_victory", None) or (player,)
    for ally in allies:
        best = max(best, faction_int_attr(ally, "team_trade_capacity_pct", 0))
    return best


def team_share_steppe_lancer(player):
    """Best allied ``team_share_steppe_lancer`` (AoE2 Cumans: each Castle
    owned by any ally grants +N steppe_lancer training slot).

    Generic: stored on the race def via ``team_share_steppe_lancer N``.
    Engine reads it in steppe_lancer / elite_steppe_lancer train-time
    allow checks (positive N → allow even if the player's own Castle
    count is below the unit's normal cap).
    """
    best = 0
    allies = getattr(player, "allied_victory", None) or (player,)
    for ally in allies:
        best = max(best, faction_int_attr(ally, "team_share_steppe_lancer", 0))
    return best


def team_free_unit_cost_for_type(player, type_cls):
    """Check if any allied player grants ``team_free_unit`` for ``type_cls``.

    AoE2 Italian Condottiero team bonus: any ally whose race def contains
    ``race_grants_team_free_unit condottiero`` makes condottiero cost 0 for
    all allied players (including self).

    Returns the modified cost tuple (zeroed) if the unit is team-free, else
    the input cost unchanged.
    """
    if player is None or type_cls is None:
        return None
    # Accept either a class with .type_name or a raw type-name string.
    if isinstance(type_cls, str):
        type_name = type_cls
    else:
        type_name = getattr(type_cls, "type_name", None) or getattr(
            type_cls, "__name__", None
        )
    if not type_name:
        return None
    # Only applies when the unit declares itself team-free
    if not rules.get(type_name, "team_free_unit"):
        return None
    allies = getattr(player, "allied_victory", None) or (player,)
    for ally in allies:
        faction = getattr(ally, "faction", None)
        if not faction:
            continue
        raw = _entries(faction, "race_grants_team_free_unit")
        if not raw:
            continue
        # raw is a list of lists of unit type-name strings
        for entry in raw:
            if not entry:
                continue
            # entry is e.g. ['condottiero']; flatten in case of nested lists
            names = entry
            if entry and isinstance(entry[0], list):
                names = [n for sub in entry for n in (sub or [])]
            if str(type_name) in {str(n) for n in names}:
                return (0,) * 16  # zero all resource slots
    return None


def apply_farm_food_team_pct(building, food_amount):
    """Multiply farm food by allied team_farm_food_pct. Returns int amount."""
    player = getattr(building, "player", None)
    pct = team_farm_food_pct(player) if player is not None else 0
    if pct <= 0:
        return int(food_amount)
    return int(int(food_amount) * (100 + pct) / 100)


def apply_supplies_team_pct(building, amount):
    """Apply allied ``team_supplies_pct`` (AoE2 Slavs: +10% to allies' barracks
    production) to a production_qty / production_time value.

    Generic: stacked on top of the unit's own production math; if no allies
    have the bonus, returns the input amount unchanged.
    """
    player = getattr(building, "player", None)
    pct = team_supplies_pct(player) if player is not None else 0
    if pct <= 0:
        return int(amount)
    return int(int(amount) * (100 + pct) / 100)


def reveal_enemy_type_names(player):
    """Race ``reveal_enemy_town_centers <type> [type…]`` — empty means off."""
    faction = getattr(player, "faction", None) if player is not None else None
    if not faction:
        return ()
    raw = _entries(faction, "reveal_enemy_town_centers")
    names = []
    if not isinstance(raw, (list, tuple)):
        raw = [raw]
    for item in raw:
        tokens = item if isinstance(item, (list, tuple)) else (item,)
        for tok in tokens:
            s = str(tok).strip()
            if s:
                names.append(s)
    return tuple(names)


def _unit_matches_reveal_types(unit, types):
    if not types:
        return False
    name = getattr(unit, "type_name", "") or ""
    if name in types:
        return True
    expanded = getattr(unit, "expanded_is_a", ()) or ()
    return any(t in expanded for t in types)


def reveal_enemy_town_centers(player):
    """Fog-memory of hostile units whose types are listed on the race."""
    if player is None:
        return
    types = set(reveal_enemy_type_names(player))
    if not types:
        return
    world = getattr(player, "world", None)
    if world is None:
        return
    allied = set(getattr(player, "allied_victory", None) or (player,))
    squares = []
    statics = []
    for other in getattr(world, "players", ()) or ():
        if other is None or other in allied:
            continue
        if getattr(other, "neutral", False):
            continue
        for unit in list(getattr(other, "units", ()) or ()):
            if not _unit_matches_reveal_types(unit, types):
                continue
            place = getattr(unit, "place", None)
            if place is not None:
                squares.append(place)
            statics.append(unit)
    if not squares:
        return
    try:
        player.observed_before_squares.update(squares)
        player.strictly_observed_before_squares.update(squares)
        if statics and hasattr(player, "_ensure_static_fog_memory"):
            player._ensure_static_fog_memory(statics)
        elif statics and hasattr(player, "_bulk_memorize"):
            player._bulk_memorize(statics)
    except Exception as e:
        warning("reveal_enemy_town_centers failed: %s", e)


def reveal_team_relics(player, relic_types=("relic",)):
    """AoE2 DE Burmese team bonus — "Relics visible on the map at the start".

    The bonus applies to the player *and all of their allies*.  Every relic
    lying on the map is fog-memorised for the affected players so it is
    visible from the start.
    """
    if player is None:
        return
    if not team_relic_visible(player):
        return
    world = getattr(player, "world", None)
    if world is None:
        return
    types = set(relic_types or ())
    squares = []
    statics = []
    for square in getattr(world, "squares", ()) or ():
        for obj in getattr(square, "objects", ()) or ():
            name = getattr(obj, "type_name", None)
            if name not in types:
                continue
            squares.append(square)
            statics.append(obj)
    if not squares:
        return
    try:
        player.observed_before_squares.update(squares)
        player.strictly_observed_before_squares.update(squares)
        if statics and hasattr(player, "_ensure_static_fog_memory"):
            player._ensure_static_fog_memory(statics)
        elif statics and hasattr(player, "_bulk_memorize"):
            player._bulk_memorize(statics)
    except Exception as e:
        warning("reveal_team_relics failed: %s", e)


def merge_pool_cost_for_type(player, type_cls, modified_cost):
    if player is None or not modified_cost or type_cls is None:
        return
    pool = getattr(player, "_phase_bonus_pool", None) or []
    if not pool:
        return
    from .worldphase import Phase

    proxy = _type_proxy(type_cls)
    if proxy is None:
        return
    for entry in pool:
        if isinstance(entry, tuple) and len(entry) == 2:
            bonus_args, targets = entry
        else:
            bonus_args, targets = entry, ()
        if targets and not Phase._unit_matches_targets(proxy, targets):
            continue
        _apply_cost_tokens_to_list(bonus_args, modified_cost)


def merge_pool_time_for_type(player, type_cls, time_cost):
    """Apply pooled on_phase ``time_cost`` bonuses matching ``type_cls``."""
    if player is None or type_cls is None:
        return time_cost
    pool = getattr(player, "_phase_bonus_pool", None) or []
    if not pool:
        return time_cost
    from .worldphase import Phase

    proxy = _type_proxy(type_cls)
    if proxy is None:
        return time_cost
    result = int(time_cost or 0)
    for entry in pool:
        if isinstance(entry, tuple) and len(entry) == 2:
            bonus_args, targets = entry
        else:
            bonus_args, targets = entry, ()
        if targets and not Phase._unit_matches_targets(proxy, targets):
            continue
        result = _apply_time_tokens(bonus_args, result)
    return result


def _apply_cost_tokens_to_list(bonus_args, modified_cost):
    i = 0
    args = list(bonus_args or ())
    while i < len(args):
        stat = str(args[i])
        if stat != "cost" or i + 1 >= len(args):
            i += 1
            continue
        values, next_i = AttributeEffectsMixin._take_list_bonus_values(args, i)
        is_percent, slots = AttributeEffectsMixin._parse_cost_like_bonus_parts(values)
        while len(slots) < len(modified_cost):
            slots.append(0.0 if is_percent else 0)
        for j, slot in enumerate(slots):
            if j >= len(modified_cost) or not slot:
                continue
            if is_percent:
                modified_cost[j] += int(modified_cost[j] * slot)
            else:
                # ``to_int`` already PRECISION-scaled flat bonuses
                modified_cost[j] += int(slot)
        i = next_i


def _apply_time_tokens(bonus_args, time_cost):
    i = 0
    args = list(bonus_args or ())
    result = int(time_cost or 0)
    while i + 1 < len(args):
        stat = str(args[i])
        if stat != "time_cost":
            i += 1
            continue
        value = args[i + 1]
        try:
            if str(value).endswith("%"):
                result += int(result * (float(str(value).rstrip("%")) / 100.0))
            else:
                result += int(float(value))
        except (TypeError, ValueError):
            pass
        i += 2
    return max(0, result)


def apply_research_cost_modifiers(player, tech_type, modified_cost):
    """Apply two types of research cost modifiers:

    1. Race ``research_cost_zero_slot <index> tech…`` (Vietnamese eco techs).
       Zeroes the given resource slot for matching techs.

    2. Player ``research_cost_tech_discount_entries`` — populated by
       ``effect_bonus research_cost_tech_discount <slot> <pct> <flat> <tech>…``
       in on_phase chains (AoE2 Bulgarians Mill-tech -50% food cost).

    Rules example for Bulgarians::

        on_phase dark_age research_cost_tech_discount 0 -50% 0 horse_collar heavy_plow crop_rotation

    Both modifiers are additive (stacks with each other).
    """
    if player is None or not modified_cost or tech_type is None:
        return

    tname = getattr(tech_type, "type_name", None) or getattr(tech_type, "__name__", "")
    expanded = set(getattr(tech_type, "expanded_is_a", ()) or ())

    # --- 1. research_cost_zero_slot (existing Vietnamese-style) ---
    faction = getattr(player, "faction", None)
    raw = rules.get(faction, "research_cost_zero_slot") if faction else None
    if raw:
        tokens = [str(x) for x in raw]
        try:
            slot = int(tokens[0])
        except (TypeError, ValueError):
            slot = None
        if slot is not None:
            names = set(tokens[1:])
            if tname in names or (expanded & names):
                if 0 <= slot < len(modified_cost):
                    modified_cost[slot] = 0

    # --- 2. research_cost_tech_discount_entries (Bulgarians Mill-tech) ---
    entries = getattr(player, "research_cost_tech_discount_entries", None)
    if entries:
        for slot_raw, pct_str, flat_str, tech_names in entries:
            if tname not in tech_names and not (expanded & tech_names):
                continue
            try:
                slot = int(slot_raw)
            except (TypeError, ValueError):
                continue
            if not (0 <= slot < len(modified_cost)):
                continue
            # Parse percent: e.g. "-50%" → -0.5 → multiply by (1 + pct)
            pct_str = str(pct_str)
            if pct_str.endswith("%"):
                try:
                    pct = float(pct_str.rstrip("%")) / 100.0
                except (TypeError, ValueError):
                    continue
            else:
                try:
                    pct = float(pct_str) / 100.0
                except (TypeError, ValueError):
                    continue
            # Apply percent discount: new_cost = old_cost * (1 + pct)
            # e.g. pct=-0.5 → new_cost = old_cost * 0.5 (50% of original)
            old_cost = modified_cost[slot]
            new_cost = int(old_cost * (1.0 + pct))
            # Add flat reduction if non-zero
            if flat_str not in ("0", "0.0", ""):
                try:
                    flat = int(float(flat_str))
                    new_cost = max(0, new_cost - flat)
                except (TypeError, ValueError):
                    pass
            modified_cost[slot] = max(0, new_cost)


def apply_research_time_modifiers(player, tech_type, time_cost):
    """Race ``research_time_percent -50% tech…`` plus player.research_time_percent_bonus."""
    result = int(time_cost or 0)
    if player is None:
        return result
    global_pct = float(getattr(player, "research_time_percent_bonus", 0.0) or 0.0)
    if global_pct:
        result += int(result * global_pct)
    faction = getattr(player, "faction", None)
    raw = rules.get(faction, "research_time_percent") if faction else None
    if raw and tech_type is not None:
        tokens = [str(x) for x in raw]
        if tokens:
            try:
                first = tokens[0]
                pct = (
                    float(first.rstrip("%")) / 100.0
                    if first.endswith("%")
                    else float(first) / 100.0
                )
            except (TypeError, ValueError):
                pct = 0.0
            names = set(tokens[1:])
            tname = getattr(tech_type, "type_name", None) or getattr(
                tech_type, "__name__", ""
            )
            expanded = set(getattr(tech_type, "expanded_is_a", ()) or ())
            if tname in names or (expanded & names):
                result += int(result * pct)
    return max(0, result)


def apply_player_level_bonus_args(player, bonus_args):
    """Handle ``research_time -20%`` stored on the player (Portuguese team)."""
    if player is None or not bonus_args:
        return False
    handled = False
    i = 0
    args = list(bonus_args)
    while i + 1 < len(args):
        stat = str(args[i])
        value = args[i + 1]
        if stat in ("research_time", "research_time_percent"):
            try:
                if str(value).endswith("%"):
                    pct = float(str(value).rstrip("%")) / 100.0
                else:
                    pct = float(value) / 100.0
            except (TypeError, ValueError):
                pct = 0.0
            prev = float(getattr(player, "research_time_percent_bonus", 0.0) or 0.0)
            player.research_time_percent_bonus = prev + pct
            handled = True
            i += 2
            continue
        i += 1
    return handled


def team_conversion_channel_bonus_pct(player):
    best = faction_int_attr(player, "conversion_channel_bonus_pct", 0)
    allies = getattr(player, "allied_victory", None) or (player,)
    for ally in allies:
        best = max(
            best, faction_int_attr(ally, "team_conversion_channel_bonus_pct", 0)
        )
    return best


def _team_conversion_interval_bonus(player, self_attr, team_attr):
    if player is None:
        return 0
    best = faction_int_attr(player, self_attr, 0)
    allies = getattr(player, "allied_victory", None) or (player,)
    for ally in allies:
        best = max(best, faction_int_attr(ally, team_attr, 0))
    return best


def team_conversion_min_intervals_bonus(player):
    return _team_conversion_interval_bonus(
        player, "conversion_min_intervals_bonus", "team_conversion_min_intervals_bonus"
    )


def team_conversion_max_intervals_bonus(player):
    return _team_conversion_interval_bonus(
        player, "conversion_max_intervals_bonus", "team_conversion_max_intervals_bonus"
    )


def herdable_steal_ignore_guards(player):
    """Race ``herdable_steal_ignore_guards 1``: steal even if a unit stands by the flock."""
    return bool(faction_int_attr(player, "herdable_steal_ignore_guards", 0))


def herdable_steal_protected(player):
    """Race ``herdable_steal_protected 1``: own flock ignores steal-through-guards."""
    return bool(faction_int_attr(player, "herdable_steal_protected", 0))


def _share_research_rows(raw):
    """Normalize stored ``team_share_research`` to ``[[tech, host...], ...]``."""
    out = []
    if not raw:
        return out
    first = raw[0]
    if isinstance(first, (list, tuple)):
        for entry in raw:
            if entry:
                out.append([str(x) for x in entry if x is not None and str(x)])
        return [row for row in out if row]
    return [[str(x)] for x in raw if x is not None and str(x)]


def team_share_research_entries(player):
    """``[(tech, host_types_tuple), ...]`` from self + ``allied_victory``."""
    rows = []
    seen = set()
    allies = getattr(player, "allied_victory", None) or (player,)
    for ally in allies:
        faction = getattr(ally, "faction", None)
        if not faction:
            continue
        raw = rules.get(faction, "team_share_research") or []
        if not raw:
            raw = (rules._dict.get(faction, {}) or {}).get("team_share_research") or []
        for row in _share_research_rows(raw):
            tech = row[0]
            hosts = tuple(row[1:])
            key = (tech, hosts)
            if key in seen:
                continue
            seen.add(key)
            rows.append((tech, hosts))
    return rows


def team_share_research_names(player):
    """Tech names allies may research (first token of each ``team_share_research`` row)."""
    names = []
    seen = set()
    for tech, _hosts in team_share_research_entries(player):
        if tech in seen:
            continue
        seen.add(tech)
        names.append(tech)
    return names


def team_share_train_entries(player):
    """``[(unit_type, host_types_tuple), ...]`` from self + ``allied_victory``.

    AoE2 Italian team bonus: every player allied with an Italian can train
    the Condottiero at its Barracks.  The race def carries the rows as
    ``team_share_train condottiero barracks``.
    """
    rows = []
    seen = set()
    allies = getattr(player, "allied_victory", None) or (player,)
    for ally in allies:
        faction = getattr(ally, "faction", None)
        if not faction:
            continue
        raw = rules.get(faction, "team_share_train") or []
        if not raw:
            raw = (rules._dict.get(faction, {}) or {}).get("team_share_train") or []
        for row in _share_research_rows(raw):
            unit_type = row[0]
            hosts = tuple(row[1:])
            key = (unit_type, hosts)
            if key in seen:
                continue
            seen.add(key)
            rows.append((unit_type, hosts))
    return rows


# ---------------------------------------------------------------------------
# AoE2 DE team bonuses that need dedicated engine support
# ---------------------------------------------------------------------------


def _best_allied_int_attr(player, attr):
    """Highest integer value of ``attr`` among the player and its allies.

    Negative values (discounts, e.g. the Georgians' ``team_repair_cost_pct
    -25``) are supported: the *most negative* value wins, because a larger
    discount is the stronger bonus.  A plain ``max`` against 0 would silently
    drop every discount.
    """
    if player is None:
        return 0
    allies = getattr(player, "allied_victory", None) or (player,)
    best = 0
    seen = False
    for ally in allies:
        value = faction_int_attr(ally, attr, 0)
        if not value:
            continue
        if not seen:
            best = value
            seen = True
        elif value < 0 and best < 0:
            best = min(best, value)
        elif value < 0:
            best = value
        else:
            best = max(best, value)
    return best


def team_repair_cost_pct(player):
    """AoE2 DE Georgians — "Building repairs cost -25%".

    Rules: ``team_repair_cost_pct -25`` on the Georgians race def.  The value
    is a percent (negative = cheaper).  Engine reads it in the repair cost
    path (``worldunit/world_attributes.py::repair_cost``).
    """
    return _best_allied_int_attr(player, "team_repair_cost_pct")


def team_military_building_pop(player):
    """AoE2 DE Slavs — "Military buildings (except Castles) provide +5 population space".

    Rules: ``team_military_building_pop 5 barracks archery_range …``.  The
    first token is the bonus headroom, the rest are the building type-names
    it applies to.  Castles are *not* in that list (the DE wording excludes
    them explicitly).
    """
    if player is None:
        return 0
    best = 0
    allies = getattr(player, "allied_victory", None) or (player,)
    for ally in allies:
        faction = getattr(ally, "faction", None)
        if not faction:
            continue
        raw = rules.get(faction, "team_military_building_pop") or []
        if not raw:
            raw = (
                (rules._dict.get(faction, {}) or {}).get("team_military_building_pop")
                or []
            )
        for entry in raw:
            tokens = [
                str(x)
                for x in (entry if isinstance(entry, (list, tuple)) else (entry,))
            ]
            if not tokens:
                continue
            try:
                best = max(best, int(float(tokens[0])))
            except (TypeError, ValueError):
                continue
    return best


def team_military_building_names(player):
    """Building type-names the Slavs team bonus applies to (union over allies)."""
    if player is None:
        return ()
    allies = getattr(player, "allied_victory", None) or (player,)
    names = []
    for ally in allies:
        faction = getattr(ally, "faction", None)
        if not faction:
            continue
        raw = rules.get(faction, "team_military_building_pop") or []
        if not raw:
            raw = (
                (rules._dict.get(faction, {}) or {}).get("team_military_building_pop")
                or []
            )
        for entry in raw:
            tokens = [
                str(x)
                for x in (entry if isinstance(entry, (list, tuple)) else (entry,))
            ]
            for tok in tokens[1:]:
                s = tok.strip()
                if s and s not in names:
                    names.append(s)
    return tuple(names)


def is_military_building(unit_or_type, names=None):
    """True if the building is one of the Slavs team-bonus military buildings.

    The list is rules-driven (``team_military_building_pop 5 <building>…``);
    when ``names`` is not given the rules of the player's own faction are
    consulted.  Castles are excluded by the DE wording.
    """
    if unit_or_type is None:
        return False
    tname = (
        getattr(unit_or_type, "type_name", None)
        or getattr(unit_or_type, "__name__", None)
        or ""
    )
    if not tname:
        return False
    if tname in ("aoe_castle", "castle"):
        return False
    if names is None:
        names = team_military_building_names(None)
    if not names:
        return False
    names = set(names)
    if tname in names:
        return True
    expanded = set(getattr(unit_or_type, "expanded_is_a", ()) or ())
    if expanded & names:
        return True
    try:
        from .definitions import rules as _rules

        cls = _rules.unit_class(tname)
        if cls is not None:
            return bool(set(getattr(cls, "expanded_is_a", ()) or ()) & names)
    except Exception:
        pass
    return False


def team_military_building_pop_for_unit(player, unit):
    """Extra population space the Slavs team bonus grants for ``unit``."""
    if player is None or unit is None:
        return 0
    bonus = team_military_building_pop(player)
    if not bonus:
        return 0
    if not is_military_building(unit, team_military_building_names(player)):
        return 0
    return bonus


def team_free_stone_buildings(player):
    """AoE2 DE Ethiopians — "Outposts cost no stone".

    Rules: ``team_free_stone_buildings outpost``.  Returns the tuple of
    building type-names whose stone cost is zeroed.
    """
    if player is None:
        return ()
    allies = getattr(player, "allied_victory", None) or (player,)
    names = []
    for ally in allies:
        faction = getattr(ally, "faction", None)
        if not faction:
            continue
        raw = rules.get(faction, "team_free_stone_buildings") or []
        if not raw:
            raw = (rules._dict.get(faction, {}) or {}).get(
                "team_free_stone_buildings"
            ) or []
        for entry in raw:
            tokens = entry if isinstance(entry, (list, tuple)) else (entry,)
            for tok in tokens:
                s = str(tok).strip()
                if s and s not in names:
                    names.append(s)
    return tuple(names)


def team_relic_food(player):
    """AoE2 DE Burgundians — "Relics generate food in addition to gold".

    Rules: ``team_relic_food 1``.  The engine adds a food production rate to
    every relic carried in an inventory.
    """
    return _best_allied_int_attr(player, "team_relic_food")


def team_relic_visible(player):
    """AoE2 DE Burmese — "Relics visible on the map at the start of the game".

    Rules: ``team_relic_visible 1``.
    """
    return _best_allied_int_attr(player, "team_relic_visible")


def team_start_free_llama(player):
    """AoE2 DE Incas — "Start with a free Llama".

    Rules: ``team_start_free_llama 1``.  The engine spawns one extra
    ``llama`` next to the player's starting town center.
    """
    return _best_allied_int_attr(player, "team_start_free_llama")


def team_train_speed_pct(player, type_cls):
    """AoE2 DE Magyars / Turks — "Mounted Archers / Gunpowder Units train +25% faster".

    Rules: ``team_train_speed_pct 25 cavalry_archer heavy_cavalry_archer …``.
    Returns the percent (positive = faster) that applies to ``type_cls``,
    or 0 when the unit is not covered.
    """
    if player is None or type_cls is None:
        return 0
    tname = getattr(type_cls, "type_name", None) or getattr(type_cls, "__name__", "")
    expanded = set(getattr(type_cls, "expanded_is_a", ()) or ())
    allies = getattr(player, "allied_victory", None) or (player,)
    best = 0
    for ally in allies:
        faction = getattr(ally, "faction", None)
        if not faction:
            continue
        raw = rules.get(faction, "team_train_speed_pct") or []
        if not raw:
            raw = (rules._dict.get(faction, {}) or {}).get("team_train_speed_pct") or []
        for entry in raw:
            tokens = [str(x) for x in (entry if isinstance(entry, (list, tuple)) else (entry,))]
            if not tokens:
                continue
            try:
                pct = int(float(tokens[0]))
            except (TypeError, ValueError):
                continue
            names = set(tokens[1:])
            if not names:
                continue
            if tname in names or (expanded & names):
                best = max(best, pct)
    return best
