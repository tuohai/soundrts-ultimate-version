"""Adaptive AI plan helpers: scout conditions, counter-priority get lines,
utility goals, and a small behavior tree.

The Computer class still owns the economy/combat "hands". This module only
decides *which plan tokens to try first*, whether a scout/attack condition
is true, and *which hand to use this tick*. The tree is a selector: first
matching node wins. All randomness stays in ``world.random`` at the call site.
"""
from __future__ import annotations

import re

from .combat.damage_calculation import _vs_lookup
from .definitions import rules


def parse_get_pairs(words):
    """Parse ``get`` arguments into ``(count, type_name)`` pairs.

    Same rules as the historic ``_follow_plan`` loop: a number applies to the
    next type name; a bare name means count 1.
    """
    pairs = []
    n = 1
    for w in words:
        if re.match("^[0-9]+$", w):
            n = int(w)
        else:
            pairs.append((n, w))
            n = 1
    return pairs


def unit_matches_type(unit, type_name, equivalent=None):
    """True if *unit* is *type_name* or inherits it (``expanded_is_a``)."""
    names = {type_name}
    if callable(equivalent):
        try:
            mapped = equivalent(type_name)
        except Exception:
            mapped = type_name
        if mapped:
            names.add(mapped)
    tn = getattr(unit, "type_name", None)
    if tn in names:
        return True
    expanded = getattr(unit, "expanded_is_a", ()) or ()
    return any(n in expanded for n in names)


def iter_known_enemies(player):
    """Enemy units in perception or memory, sorted by id (lockstep-safe)."""
    seen = set()
    out = []
    is_enemy = getattr(player, "is_an_enemy", None)
    for bucket in (
        getattr(player, "perception", None),
        getattr(player, "memory", None),
    ):
        if not bucket:
            continue
        for obj in bucket:
            oid = getattr(obj, "id", None)
            if oid is not None and oid in seen:
                continue
            if getattr(obj, "place", None) is None:
                continue
            if callable(is_enemy):
                try:
                    if not is_enemy(obj):
                        continue
                except Exception:
                    continue
            else:
                continue
            if oid is not None:
                seen.add(oid)
            out.append(obj)
    out.sort(key=lambda o: getattr(o, "id", 0))
    return out


def sees_enemy_type(player, type_name):
    """True if any known enemy matches *type_name* (including ``is_a``)."""
    equivalent = getattr(player, "equivalent", None)
    for enemy in iter_known_enemies(player):
        if unit_matches_type(enemy, type_name, equivalent=equivalent):
            return True
    return False


def _unit_class_for_token(type_name, equivalent=None):
    names = [type_name]
    if callable(equivalent):
        try:
            mapped = equivalent(type_name)
        except Exception:
            mapped = type_name
        if mapped and mapped != type_name:
            names.append(mapped)
    for name in names:
        cls = rules.unit_class(name)
        if cls is not None:
            return cls
    return None


def token_counter_score(type_name, enemies, equivalent=None):
    """Best ``mdg_vs`` / ``rdg_vs`` bonus of *type_name* against *enemies*."""
    if not enemies:
        return 0
    cls = _unit_class_for_token(type_name, equivalent=equivalent)
    if cls is None:
        return 0
    mdg_vs = getattr(cls, "mdg_vs", None) or {}
    rdg_vs = getattr(cls, "rdg_vs", None) or {}
    best = 0
    for enemy in enemies:
        et = getattr(enemy, "type_name", None)
        expanded = getattr(enemy, "expanded_is_a", ()) or ()
        for vs_dict in (mdg_vs, rdg_vs):
            v = _vs_lookup(vs_dict, et, expanded)
            if v is not None and v > best:
                best = v
    return best


def token_is_army(type_name, equivalent=None):
    """True if *type_name* is a fighter, not a worker, building, or ferry."""
    cls = _unit_class_for_token(type_name, equivalent=equivalent)
    if cls is None:
        return False
    if getattr(cls, "is_a_building", False):
        return False
    if getattr(cls, "transport_capacity", 0):
        return False
    try:
        from .worldunit.worldworker import Worker

        if issubclass(cls, Worker):
            return False
    except TypeError:
        pass
    return True


def combat_enemies(enemies):
    """Known enemies that are not buildings (army-vs-army scoring)."""
    return [e for e in enemies if not getattr(e, "is_a_building", False)]


def _army_count_hint(pairs, is_army):
    hint = 4
    for count, name in pairs:
        if is_army(name):
            hint = max(hint, min(int(count), 8))
    return hint


def inject_counter_pairs(pairs, enemies, trainable_names, equivalent=None, is_army=None):
    """Append one owned trainable that counters scouted fighters.

    Does nothing when the current ``get`` line has no army tokens (dark-age
    villager lines stay eco). Never duplicates a type already on the line.
    """
    if not pairs or not enemies or not trainable_names:
        return list(pairs)
    if is_army is None:

        def is_army(name):
            return token_is_army(name, equivalent=equivalent)

    if not any(is_army(name) for _n, name in pairs):
        return list(pairs)
    already = {name for _n, name in pairs}
    best_name = None
    best_score = 0
    for name in trainable_names:
        if name in already or not is_army(name):
            continue
        score = token_counter_score(name, enemies, equivalent=equivalent)
        if score > best_score:
            best_score = score
            best_name = name
    if not best_name or best_score <= 0:
        return list(pairs)
    extra = _army_count_hint(pairs, is_army)
    return list(pairs) + [(extra, best_name)]


def reorder_get_pairs(pairs, enemies, equivalent=None):
    """Stable-sort military ``get`` tokens so better counters come first.

    Workers, buildings and anything with no vs bonus keep their relative
    order among themselves; only tokens with a positive counter score bubble
    ahead of other military tokens. Completion of the line is unchanged:
    every pair still has to be satisfied before the plan advances.
    """
    if not pairs or not enemies:
        return list(pairs)
    scored = []
    for index, (count, name) in enumerate(pairs):
        score = token_counter_score(name, enemies, equivalent=equivalent)
        scored.append((index, count, name, score))
    # High counter first; original index breaks ties (deterministic).
    military = [row for row in scored if row[3] > 0]
    rest = [row for row in scored if row[3] <= 0]
    military.sort(key=lambda row: (-row[3], row[0]))
    rest.sort(key=lambda row: row[0])
    return [(count, name) for _i, count, name, _s in military + rest]


# Highest score wins; equal scores keep this order (lockstep-safe).
UTILITY_GOALS = ("defend", "age", "eco", "scout", "produce", "attack")

# After 6 workers, wait this long for a combat sighting before training army.
# Short so expert rush is not stalled if the map never meets.
SCOUT_THEN_PRODUCE_MS = 60 * 1000


def iter_home_places(player):
    """Town-hall (primary-worker trainer) squares, sorted by place id."""
    names = ()
    fn = getattr(player, "_main_base_type_names", None)
    if callable(fn):
        try:
            names = tuple(fn() or ())
        except Exception:
            names = ()
    seen = set()
    out = []
    for u in getattr(player, "units", ()) or ():
        if names and getattr(u, "type_name", None) not in names:
            continue
        if not names:
            continue
        place = getattr(u, "place", None)
        if place is None:
            continue
        pid = id(place)
        if pid in seen:
            continue
        seen.add(pid)
        out.append(place)
    out.sort(key=lambda p: getattr(p, "id", 0))
    return out


def _call_flag(player, name):
    fn = getattr(player, name, None)
    if not callable(fn):
        return False
    try:
        return bool(fn())
    except Exception:
        return False


def home_is_threatened(player):
    """True if attacked this play, or a known enemy stands on a town-hall square."""
    if getattr(player, "_attacked_this_play", False) or getattr(
        player, "_attacked_places", None
    ):
        return True
    home = set(iter_home_places(player))
    if not home:
        return False
    for enemy in iter_known_enemies(player):
        if getattr(enemy, "place", None) in home:
            return True
    return False


def _worker_counts(player):
    n_workers = len(getattr(player, "_workers", ()) or ())
    target = int(getattr(player, "nb_workers_to_get", 10) or 10)
    return n_workers, target


def _tree_defend(player):
    return home_is_threatened(player)


def _tree_opening_eco(player):
    n_workers, _target = _worker_counts(player)
    return n_workers < 6


def _tree_age(player):
    return _call_flag(player, "_saving_food_for_age") or _call_flag(
        player, "_age_up_needs_food"
    )


def _tree_boom_eco(player):
    n_workers, target = _worker_counts(player)
    return n_workers < target


def _has_known_combat_enemy(player):
    return bool(combat_enemies(iter_known_enemies(player)))


def _tree_scout(player):
    """True until we have seen a fighter or the scout wait times out."""
    n_workers, _target = _worker_counts(player)
    if n_workers < 6:
        return False
    if _has_known_combat_enemy(player):
        return False
    now = int(getattr(getattr(player, "world", None), "time", 0) or 0)
    started = getattr(player, "_scout_sequence_started", None)
    if started is None:
        started = now
    try:
        limit = int(
            getattr(player, "_scout_then_train_ms", SCOUT_THEN_PRODUCE_MS)
            or SCOUT_THEN_PRODUCE_MS
        )
    except Exception:
        limit = SCOUT_THEN_PRODUCE_MS
    return now - int(started) < limit


def _tree_attack(player):
    if not getattr(player, "constant_attacks", 0):
        return False
    return bool(getattr(player, "_enemy_presence", None) or ())


def _tree_produce(_player):
    return True


# Selector: first true condition wins. Lockstep-safe (no random, fixed order).
BEHAVIOR_TREE = (
    ("defend", _tree_defend),
    ("eco", _tree_opening_eco),
    ("age", _tree_age),
    ("scout", _tree_scout),
    ("eco", _tree_boom_eco),
    ("attack", _tree_attack),
    ("produce", _tree_produce),
)


def tick_behavior_tree(player):
    """Run the selector tree; return the hand name of the first matching node."""
    for name, pred in BEHAVIOR_TREE:
        try:
            if pred(player):
                return name
        except Exception:
            continue
    return "produce"


def score_utility_goals(player):
    """Integer scores for this tick's hands. Higher = more urgent."""
    scores = {name: 0 for name in UTILITY_GOALS}
    attacked = bool(
        getattr(player, "_attacked_this_play", False)
        or getattr(player, "_attacked_places", None)
    )
    if attacked:
        scores["defend"] = 100
    else:
        home = set(iter_home_places(player))
        if home:
            threat = 0
            for enemy in iter_known_enemies(player):
                if getattr(enemy, "place", None) in home:
                    threat += 1
            if threat:
                scores["defend"] = min(90, 50 + threat * 10)
    if _call_flag(player, "_saving_food_for_age"):
        scores["age"] = 80
    elif _call_flag(player, "_age_up_needs_food"):
        scores["age"] = 70
    n_workers, target = _worker_counts(player)
    if n_workers < 6:
        scores["eco"] = 95
    elif n_workers < target:
        scores["eco"] = min(70, 30 + (target - n_workers) * 3)
    if (
        n_workers >= 6
        and not _has_known_combat_enemy(player)
        and _tree_scout(player)
    ):
        scores["scout"] = 50
    scores["produce"] = 40
    if getattr(player, "constant_attacks", 0):
        presence = getattr(player, "_enemy_presence", None) or ()
        scores["attack"] = 55 if presence else 35
    return scores


def choose_utility_goal(player):
    """Hand to use this tick: selector tree (not raw score max)."""
    return tick_behavior_tree(player)


# At most two simultaneous attack fronts. A third would peel the blob too thin.
MAX_ATTACK_FRONTS = 2


def _place_threat_key(place, enemy_menace):
    try:
        threat = int(enemy_menace(place))
    except Exception:
        threat = 0
    try:
        pid = int(getattr(place, "id", 0) or 0)
    except Exception:
        pid = 0
    return (threat, -pid)


def _unit_id(unit):
    return getattr(unit, "id", id(unit))


def _unit_holds_home(unit, home):
    """True if the unit is on ``home`` or already walking there."""
    if home is None:
        return False
    if getattr(unit, "place", None) is home:
        return True
    orders = getattr(unit, "orders", None) or ()
    if not orders:
        return False
    target = getattr(orders[0], "target", None)
    return target is home


def _sticky_guard_order(units, home, prefer_ids=None):
    """Stationed / heading-home first, then last tick's guard, then the rest.

    Each bucket keeps the caller's order (lockstep). Extra stationed units
    still go to leftover once home is covered, so a turtle can sortie.
    """
    prefer = set(prefer_ids or ())
    stationed = []
    preferred = []
    others = []
    for u in units:
        if _unit_holds_home(u, home):
            stationed.append(u)
        elif _unit_id(u) in prefer:
            preferred.append(u)
        else:
            others.append(u)
    return stationed + preferred + others


def peel_home_guard(
    home_places, units, menace_of, enemy_menace, ratio, prefer_ids=None
):
    """Peel a home garrison before any raid.

    Returns ``(home, guard, leftover)``. ``home`` is None when there is no
    hall. Empty ``leftover`` means the army cannot cover home: everyone stays.
    A quiet hall (need 0) still takes one unit with menace > 0 as a token
    guard. Units already on (or walking to) ``home``, then ``prefer_ids``,
    fill the guard before anyone else so a new idle recruit does not yank
    the sentry into the raid. Lockstep: each bucket keeps the given order.
    """
    if not home_places or not units:
        return None, [], list(units or [])
    home = max(home_places, key=lambda p: _place_threat_key(p, enemy_menace))
    try:
        need = int(enemy_menace(home)) * int(ratio) // 100
    except Exception:
        need = 0
    picked = []
    menace = 0
    leftover = []
    for u in _sticky_guard_order(units, home, prefer_ids):
        if menace > need:
            leftover.append(u)
            continue
        try:
            m = int(menace_of(u) or 0)
        except Exception:
            m = 0
        if m <= 0:
            leftover.append(u)
            continue
        picked.append(u)
        menace += m
    if not picked or menace <= need:
        return home, list(units), []
    return home, picked, leftover


def assign_attack_groups(places, units, menace_of, enemy_menace, ratio, max_fronts=None):
    """Split idle fighters across places only when each front still beats ratio.

    ``ratio`` is the same percent ``_is_powerful_enough`` uses. A second (or
    later) front is opened only if leftover menace is strictly greater than
    ``enemy_menace(place) * ratio // 100``. Units that cannot cover another
    front fold back into the first group so the AI never 1v1 two squares.
    At most ``MAX_ATTACK_FRONTS`` groups (or ``max_fronts`` if given).
    Lockstep: units are taken in the given order (caller sorts by id).
    """
    cap = MAX_ATTACK_FRONTS if max_fronts is None else max(0, int(max_fronts))
    if not places or not units or cap <= 0:
        return []
    remaining = list(units)
    groups = []
    for place in places:
        if len(groups) >= cap:
            break
        try:
            need = int(enemy_menace(place)) * int(ratio) // 100
        except Exception:
            continue
        picked = []
        menace = 0
        leftover = []
        for u in remaining:
            if menace > need:
                leftover.append(u)
                continue
            try:
                m = int(menace_of(u) or 0)
            except Exception:
                m = 0
            if m <= 0:
                leftover.append(u)
                continue
            picked.append(u)
            menace += m
        if menace <= need or not picked:
            continue
        groups.append((place, picked))
        remaining = leftover
        if not remaining:
            break
    if groups and remaining:
        first_place, first_units = groups[0]
        groups[0] = (first_place, list(first_units) + remaining)
    return groups


def assign_attack_groups_with_home(
    places, units, menace_of, enemy_menace, ratio, home_places, prefer_ids=None
):
    """Garrison a town-hall square, then raid with at most one leftover front.

    Home always counts as one of the ``MAX_ATTACK_FRONTS`` destinations, so a
    raid never also two-way splits. Raid leftovers fold into the raid, not
    the guard. If the army cannot hold home, everyone stays and there is no
    raid. No halls: same as ``assign_attack_groups``. ``prefer_ids`` keeps
    last tick's sentry instead of peeling a new recruit into the guard.
    """
    if not home_places:
        return assign_attack_groups(places, units, menace_of, enemy_menace, ratio)
    home, guard, leftover = peel_home_guard(
        home_places, units, menace_of, enemy_menace, ratio, prefer_ids=prefer_ids
    )
    if home is None:
        return assign_attack_groups(places, units, menace_of, enemy_menace, ratio)
    groups = [(home, guard)]
    if not leftover:
        return groups
    home_ids = {id(p) for p in home_places}
    raid_places = [p for p in places if id(p) not in home_ids]
    if not raid_places:
        groups[0] = (home, list(guard) + leftover)
        return groups
    raids = assign_attack_groups(
        raid_places,
        leftover,
        menace_of,
        enemy_menace,
        ratio,
        max_fronts=max(0, MAX_ATTACK_FRONTS - 1),
    )
    if not raids:
        groups[0] = (home, list(guard) + leftover)
        return groups
    return groups + raids
