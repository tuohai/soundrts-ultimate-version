"""Rules-driven economy rules for the computer player.

This module holds the parts of the AI's economy that are *policy*, not
mechanics: how the workers are spread over the available sources, and
when the AI is allowed to open another base.

Two rules live here, and both of them are expressed in terms of rules
attributes, never in terms of unit names.  A mod that calls its worker
``serf`` and its base ``mairie`` (CrazyMod) or its base ``command_center``
(StarCraft) gets the same behaviour as a mod that calls them ``peasant``
and ``town_center`` (AoE2), because nothing here mentions either name.

Load balancing
---------------

The AI picks a gather target with the sort key
``(need_ratio, renewable, distance)``.  Two workers that want the same
resource therefore pick the *same* target -- the nearest one -- and all
of them pile onto it, while the second-best source stays empty.

The fix is one more term in that key: the number of workers already
assigned to the candidate.  Among the candidates that are equally needed,
the one with the fewest workers wins.

Difficulty
----------

The balancing is graded, because the pile-up is not equally bad at every
difficulty:

* ``beginner`` / ``timers`` pile up on purpose.  A beginner AI that
  spreads its villagers over four farms is simply harder to kill, and the
  point of the beginner tier is to be killable.
* ``intermediate`` balances, but only between the sources that are
  *needed*: a source nobody needs stays empty.
* ``advanced`` and above balance across all the candidates of the needed
  resource.

Base expansion
--------------

The AI used to open extra bases only when ``ai.txt`` said ``expand N``,
which no mod ships.  Now the AI decides by itself, from four
*measurable* conditions:

1. the population is close to the limit (the base's housing is nearly
   full);
2. the cost is affordable right now;
3. there is room to build it (the world is not wall-to-wall base);
4. the base is worth having -- it is either a different *kind* of base
   (a mod may have several), or the AI is short of housing.

Every condition is optional and degrades to "no expansion" when the
rules do not tell us.  A mod that has no population limit, or no buildable
base, simply never expands.
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# Difficulty grading
# ---------------------------------------------------------------------------

# The tiers that spread their workers.  The tiers above it spread them
# *across every candidate*; the tiers below never spread them at all.
BALANCING_TIERS = ("intermediate", "advanced", "expert", "nightmare")

# The tiers that balance only between the sources that are actually
# needed.  The tiers above it balance across every candidate of the
# needed resource, including the ones the need-ratio ranks lower.
STRICT_BALANCING_TIERS = ("advanced", "expert", "nightmare")

# The legacy tier names, for mods whose ai.txt still uses them.
_LEGACY_TIERS = ("easy", "aggressive")


def balancing_tier(ai_type: Optional[str]) -> str:
    """The balancing behaviour tier for an AI difficulty.

    Returns one of ``"none"`` (pile up), ``"needed"`` (balance between
    the sources that are needed) or ``"all"`` (balance across every
    candidate of the needed resource).
    """
    name = str(ai_type or "").strip().lower()
    if not name:
        return "none"
    if name in ("timers", "beginner"):
        return "none"
    if name in _LEGACY_TIERS:
        # "easy" was the old name of the quiet beginner tier and
        # "aggressive" of the intermediate one.
        return "none" if name == "easy" else "needed"
    if name in STRICT_BALANCING_TIERS:
        return "all"
    if name in BALANCING_TIERS:
        return "needed"
    # An unknown tier (a mod's own difficulty name): balance, but do not
    # assume it is better than the standard tiers.
    return "needed"


def balances_workers(ai_type: Optional[str]) -> bool:
    """True when this difficulty spreads its workers over the sources."""
    return balancing_tier(ai_type) != "none"


def balances_strictly(ai_type: Optional[str]) -> bool:
    """True when the balancing also considers the less-needed sources."""
    return balancing_tier(ai_type) == "all"


# ---------------------------------------------------------------------------
# Load balancing
# ---------------------------------------------------------------------------


def worker_load(target) -> int:
    """How many workers are already assigned to *target*.

    Falls back to 0 for anything that cannot answer, so a missing
    attribute never breaks the AI.
    """
    if target is None:
        return 0
    try:
        from .world_extractor import count_workers_assigned_to_gather_target

        return int(count_workers_assigned_to_gather_target(target) or 0)
    except Exception:
        return 0


def worker_loads(targets, world=None) -> dict:
    """How many workers are assigned to each of *targets*, in one pass.

    ``worker_load`` walks every unit of every player, so calling it once
    per candidate would be O(candidates x units).  This variant does a
    single walk and fills in the counts, which is what the AI's gather
    loop needs (it asks about every candidate at once).

    ``world`` is the world to look in.  When it is not given, the world
    is looked up on the targets themselves -- but the caller (the AI)
    always knows it, and passing it explicitly is both faster and more
    reliable.

    The result maps each target to its count; targets with no worker are
    present with the count 0.
    """
    result = {}
    try:
        target_list = list(targets)
    except TypeError:
        return result
    for t in target_list:
        result[t] = 0
    if not result:
        return result
    if world is None:
        for t in target_list:
            place = getattr(t, "place", None)
            world = getattr(place, "world", None) if place is not None else None
            if world is None:
                world = getattr(t, "world", None)
            if world is not None:
                break
    if world is None:
        return result
    for player in getattr(world, "players", ()) or ():
        for unit in getattr(player, "units", ()) or ():
            orders = getattr(unit, "orders", None) or []
            if not orders:
                continue
            order = orders[0]
            if getattr(order, "keyword", None) != "gather":
                continue
            target = getattr(order, "target", None)
            if target in result:
                result[target] += 1
    return result


def balanced_order_key(
    ai_type: Optional[str],
    need_ratio: float,
    renewable_rank: int,
    load: int,
    distance: float,
) -> Tuple:
    """The sort key that spreads the workers.

    The key is ``(need_ratio, load, renewable_rank, distance)`` for the
    tiers that balance, and the caller's own key otherwise.

    ``load`` comes *before* ``renewable_rank`` on purpose: sending the
    second worker to a renewable farm instead of to the crowded nearby
    orchard is the whole point.  But it comes *after* ``need_ratio``:
    a worker must never be sent to a source the AI does not need, just
    because that source is less crowded.
    """
    if not balances_workers(ai_type):
        return (need_ratio, renewable_rank, distance)
    return (need_ratio, load, renewable_rank, distance)


# ---------------------------------------------------------------------------
# Base expansion
# ---------------------------------------------------------------------------


def expansion_headroom(ai_type: Optional[str]) -> int:
    """How many extra bases this difficulty may open.

    ``0`` means "never on its own" -- the base is then only opened when
    ``ai.txt`` explicitly asks for it with ``expand N``.
    """
    name = str(ai_type or "").strip().lower()
    if name in ("timers", "beginner"):
        return 0
    if name == "easy":
        return 0
    if name in ("aggressive", "intermediate"):
        return 1
    if name == "advanced":
        return 2
    if name in ("expert", "nightmare"):
        return 3
    # Unknown tier: one base is a safe default.
    return 1


def population_is_pressured(
    housing_capacity: int,
    population_used: int,
    *,
    threshold: float = 0.75,
) -> bool:
    """True when the AI's *own* housing is nearly full.

    ``housing_capacity`` is what the AI's buildings provide (a town
    center gives 5, a house gives 5 …) and ``population_used`` is how
    many population the AI's units consume.  The AI must open a new
    base when its own housing is running out.

    The world's ``population_limit`` is deliberately **not** used here:
    that is the *global* cap shared by every player (AoE2's cw1 map
    uses 1999), and comparing the AI's housing against it would never
    report any pressure.

    A capacity of 0 (or less) means the rules give no housing at all:
    there is no pressure to relieve, so no expansion.
    """
    try:
        capacity = int(housing_capacity or 0)
        used = int(population_used or 0)
    except (TypeError, ValueError):
        return False
    if capacity <= 0:
        return False
    if used < 0:
        used = 0
    # The headroom is what matters: a full house means the AI cannot
    # train the next unit.  The threshold is a fraction of the capacity,
    # so an AI with 20 housing and 14 units is under pressure.
    headroom = capacity - used
    if headroom <= 0:
        return True
    return headroom <= capacity * (1.0 - threshold)


def expansion_is_worthwhile(
    *,
    owned_base_count: int,
    target_base_count: int,
    population_pressured: bool,
    resources_ready: bool,
    has_room_to_build: bool,
    housing_needed: bool,
) -> bool:
    """The decision to open one more base.

    All the conditions are computed by the caller; this function only
    combines them, so the policy is testable on its own.
    """
    if target_base_count <= 0:
        return False
    if owned_base_count >= target_base_count:
        return False
    if not resources_ready:
        return False
    if not has_room_to_build:
        return False
    # Either the housing is running out, or the base is a different kind
    # of base (the caller decides which case applies by asking for
    # ``housing_needed``).
    return bool(population_pressured or housing_needed)


# ---------------------------------------------------------------------------
# Rules attributes
# ---------------------------------------------------------------------------


def read_bool_attr(rules, type_name: str, attr: str, default: bool = False) -> bool:
    """Read a boolean attribute of a rules class.

    Returns *default* when the class does not exist or does not declare
    the attribute.
    """
    raw = _read_attr(rules, type_name, attr)
    if raw is None:
        return default
    if isinstance(raw, str):
        return raw.strip().lower() in ("1", "true", "yes", "on")
    return bool(raw)


def read_int_attr(rules, type_name: str, attr: str, default: int = 0) -> int:
    """Read an integer attribute of a rules class."""
    raw = _read_attr(rules, type_name, attr)
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _read_attr(rules, type_name: str, attr: str, keep_list: bool = False):
    """The raw value of a rules attribute, or None when it is not declared.

    ``rules.get`` returns ``[]`` for an attribute the rules do not
    declare, and warns about it in debug mode.  The AI's own attributes
    are optional, so the lookup is done without the warning.

    A list value is unwrapped to its first element, because a single
    rules attribute (``ai_base_worth_expanding 1``) is stored as a
    one-element list.  Pass ``keep_list=True`` for the attributes that
    really are lists (``ai_base_supplies resource1 resource2``).
    """
    if rules is None or not type_name:
        return None
    try:
        cls = rules.unit_class(type_name)
    except Exception:
        cls = None
    if cls is None:
        return None
    raw = None
    try:
        raw = rules.get(cls, attr, warn_if_not_found=False)
    except TypeError:
        # A rules object that does not know the keyword.
        try:
            raw = rules.get(cls, attr)
        except Exception:
            raw = None
    except Exception:
        raw = None
    if raw is None:
        try:
            raw = getattr(cls, attr, None)
        except Exception:
            raw = None
    if raw is None:
        return None
    if isinstance(raw, (list, tuple)):
        if not raw:
            return None
        if keep_list:
            return tuple(raw)
        raw = raw[0]
    if raw is None:
        return None
    if isinstance(raw, str) and not raw.strip():
        return None
    return raw


def base_supplies(rules, type_name: str) -> Tuple[str, ...]:
    """The resources this base type supplies.

    The rules attribute is ``ai_base_supplies``: a list of resource
    slots the base makes available (its own storage, its gather slots).
    An empty list means "the base supplies nothing special", and the
    caller then treats it as a plain base.
    """
    if rules is None or not type_name:
        return ()
    try:
        cls = rules.unit_class(type_name)
    except Exception:
        cls = None
    if cls is None:
        return ()
    raw = _read_attr(rules, type_name, "ai_base_supplies", keep_list=True)
    if raw is None:
        return ()
    if isinstance(raw, str):
        raw = [raw]
    out = []
    for item in raw:
        text = str(item).strip()
        if text:
            out.append(text)
    return tuple(out)


def base_is_worth_expanding(rules, type_name: str, default: bool = True) -> bool:
    """Whether the AI may open more bases of this type.

    The rules attribute is ``ai_base_worth_expanding``.  When it is
    absent the base is worth expanding (the usual case), so a mod does
    not have to declare anything to get the behaviour.
    """
    return read_bool_attr(rules, type_name, "ai_base_worth_expanding", default)


# ---------------------------------------------------------------------------
# Multi-queue reinforcement (多线补兵)
# ---------------------------------------------------------------------------

# The tiers that keep every owned production building busy at the same
# time.  Below this tier the AI keeps a single queue going, which is
# enough for a beginner opponent and much cheaper to compute.
MULTI_QUEUE_TIERS = ("advanced", "expert", "nightmare")

# How many production buildings a tier may run at once.  The tier names
# are the difficulty, so the mapping is a policy, not a rules fact.
MULTI_QUEUE_LIMITS = {
    "advanced": 2,
    "expert": 3,
    "nightmare": 4,
}


def multi_queue_limit(ai_type: Optional[str]) -> int:
    """How many *extra* production queues this difficulty may open.

    ``0`` means "one queue only": the AI trains through a single host
    and leaves the other factories idle, exactly like before.

    The number is *additional* queues on top of the one the regular
    plan path always uses, so ``intermediate`` (1) really does open a
    second queue.  It is a *policy* graded by difficulty, like the
    worker balancing, and it is always capped by what the AI actually
    owns, so a tier never builds extra buildings just to fill its
    quota.
    """
    name = str(ai_type or "").strip().lower()
    if name in ("timers", "beginner", "easy"):
        return 0
    limit = MULTI_QUEUE_LIMITS.get(name)
    if limit is not None:
        return limit
    if name == "aggressive":
        return 1
    if name == "intermediate":
        return 1
    # An unknown tier (a mod's own difficulty name): one extra queue is
    # a safe default.
    return 1


def multi_queue_tier(ai_type: Optional[str]) -> str:
    """The multi-queue tier name for a difficulty.

    ``"none"`` (one queue), ``"one"`` (one extra queue) or ``"all"``
    (every owned production building).
    """
    limit = multi_queue_limit(ai_type)
    if limit <= 0:
        return "none"
    if limit >= 4:
        return "all"
    return "one"


def should_open_extra_queue(ai_type: Optional[str]) -> bool:
    """True when this difficulty may run more than one production queue."""
    return multi_queue_limit(ai_type) > 0


def production_queue_depth(host) -> int:
    """How many production orders *host* already has queued.

    A building that is already training three units is not a candidate
    for another order, even though its queue is not "full" (the engine
    allows ten orders).  This is what makes the multi-queue behaviour
    "one order per building at a time" instead of "ten orders on the
    first building".
    """
    if host is None:
        return 0
    depth = 0
    for order in getattr(host, "orders", None) or ():
        keyword = getattr(order, "keyword", None)
        if keyword in ("train", "upgrade_to", "research", "advance"):
            depth += 1
    return depth


def can_queue_on_host(host, queue_depth: Optional[int] = None) -> bool:
    """True when *host* can take one more production order.

    Only production orders count: a building that is busy doing
    something else (a worker is building inside it, an addon is being
    attached) is still a valid host.
    """
    if host is None:
        return False
    if not getattr(host, "is_a_building", False):
        return False
    depth = production_queue_depth(host) if queue_depth is None else queue_depth
    return depth == 0


def balanced_production_key(
    ai_type: Optional[str],
    load: int,
    queue_depth: int,
    threat: float,
    name: str,
) -> Tuple:
    """The sort key that spreads production over the owned buildings.

    The key is ``(load, queue_depth, -threat, name)`` for the tiers
    that balance, so the *least loaded* building gets the order first.

    ``name`` is the last tie-breaker: the decision must be
    reproducible across runs, and the unit id (like the object address)
    is not stable.
    """
    if not should_open_extra_queue(ai_type):
        return (queue_depth, -threat, name)
    return (load, queue_depth, -threat, name)


def extra_queue_budget(ai_type: Optional[str], owned_hosts: int) -> int:
    """How many hosts this difficulty may use *besides* the first one.

    ``owned_hosts`` is the number of production buildings the AI owns.
    The result is clamped to what is actually available, so a tier
    never invents buildings to fill its quota.
    """
    limit = multi_queue_limit(ai_type)
    if limit <= 0:
        return 0
    try:
        owned = int(owned_hosts or 0)
    except (TypeError, ValueError):
        owned = 0
    if owned <= 1:
        return 0
    return min(limit, owned - 1)
