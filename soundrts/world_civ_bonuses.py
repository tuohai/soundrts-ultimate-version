"""Rules-driven civilization / team bonuses (no civ type-name hardcoding).

Race fields::

    team_on_phase <phase> <effect bonus args> [unit types…]
    grant_tech_on_phase <phase> <tech> [tech…]
    team_farm_food_pct 10
    reveal_enemy_town_centers town_center
    team_conversion_channel_bonus_pct 50
    team_share_research <tech> [host types…]
    herdable_steal_ignore_guards 1
    herdable_steal_protected 1
    research_cost_zero_slot 1 wheelbarrow hand_cart …
    research_time_percent -50% wheelbarrow hand_cart …

``team_on_phase`` is ``on_phase`` applied to every ``allied_victory`` member
(including self). ``grant_tech_on_phase`` instant-researches those upgrades
when the phase is reached. ``team_share_research`` unlocks listed techs on
allied buildings (optional host types). Steal flags are race integers via
``faction_int_attr`` — no civilization type-name checks.
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


def apply_farm_food_team_pct(building, food_amount):
    """Multiply farm food by allied team_farm_food_pct. Returns int amount."""
    player = getattr(building, "player", None)
    pct = team_farm_food_pct(player) if player is not None else 0
    if pct <= 0:
        return int(food_amount)
    return int(int(food_amount) * (100 + pct) / 100)


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


def merge_pool_cost_for_type(player, type_cls, modified_cost):
    """Apply pooled on_phase ``cost`` bonuses matching ``type_cls``."""
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
    """Race ``research_cost_zero_slot <index> tech…`` (Vietnamese eco techs)."""
    if player is None or not modified_cost or tech_type is None:
        return
    faction = getattr(player, "faction", None)
    raw = rules.get(faction, "research_cost_zero_slot") if faction else None
    if not raw:
        return
    tokens = [str(x) for x in raw]
    try:
        slot = int(tokens[0])
    except (TypeError, ValueError):
        return
    names = set(tokens[1:])
    tname = getattr(tech_type, "type_name", None) or getattr(tech_type, "__name__", "")
    expanded = set(getattr(tech_type, "expanded_is_a", ()) or ())
    if tname not in names and not (expanded & names):
        return
    if 0 <= slot < len(modified_cost):
        modified_cost[slot] = 0


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
