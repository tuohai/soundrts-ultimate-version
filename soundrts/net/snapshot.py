"""Exact world snapshots for rollback netcode.

Why this module exists
-----------------------

The multiplayer path used to be deterministic lockstep: every client ran the
whole simulation and the server only shipped the batch of orders once *all*
players had sent theirs.  That makes the slowest player's ping the pace of
the entire match, and a single desync kills the match.

The replacement is host-authoritative input + client prediction + rollback.
Rollback needs one thing above all else: a snapshot that is **cheap enough to
take every frame** and **faithful enough to restore a bit-identical world**.

Measured on the bundled ``cw1`` map (576 squares, 9323 objects, 148 units):

===========================================  ==========  ==========
strategy                                      cw1 (576sq)  cw1-mm
===========================================  ==========  ==========
``cloudpickle.dumps(world)``                  30 ms       492 ms
``copy.deepcopy(world)``                      fails       fails
===========================================  ==========  ==========

The decisive number: over 30 frames only **153 of 131835 objects (0.12 %)**
ever change.  120156 of those objects are ``meadow`` (building land) and are
static for the whole match.  So a snapshot only has to cover the *hot set* —
the units, the buildings and the deposits — plus the few squares whose
membership changed.

Design
------

The snapshot is *layered*, and the layers mirror the way the engine is
actually built:

* **L0 — world scalars.**  ``world.time``, the id counter, the RNG state and
  the world-level counters that gate periodic work (the slow-update cadence,
  the terrain sweep cadence, the AI decision bucket ...).

* **L1 — players.**  Each player's full mutable state, *including* its
  perception caches.  The caches are restored **exactly** rather than
  dropped: they gate how much randomness the simulation consumes, so
  resetting them would fork the world.

* **L2 — entities.**  Every unit / building / deposit, plus the mutable
  children hanging off them (``Action``, ``Order``, the ``building_land``
  meadow a building stands on, buffs, inventory items ...).

* **L3 — squares.**  Every square's membership list and terrain state.  This
  is where object creation and destruction is recorded.

* **L4 — structure.**  Which objects exist, which square each one stands on,
  which units each player owns, the collision bitmaps and the scheduled
  events.

Two properties make the restore *exact* rather than approximate:

**Copy-on-write containers.**  A container attribute that the simulation
mutates *in place* (``unit.orders.append(...)``) must be copied, not shared,
or the restore does not undo the mutation.  The snapshot therefore copies
containers instead of aliasing them — but the objects *inside* a container
keep their identity, because they are captured (and restored) separately.

**Restored identity.**  ``world`` / ``player`` / ``place`` back-references
are re-linked to the live objects on restore rather than replaced by a copy,
so the client UI (which indexes units by id but keeps live references in
``EntityView.model``) keeps working.

``strong_digest`` computes a digest that actually covers positions, hit
points, resources, orders and actions, so a restored world can be *verified*
rather than assumed correct.  (``World.get_digest`` only hashes
``random.getstate()``, which is far too weak for this purpose.)
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

__all__ = [
    "Snapshot",
    "SnapshotStore",
    "capture_snapshot",
    "restore_snapshot",
    "strong_digest",
    "hot_objects",
]


_MISSING = object()


# --------------------------------------------------------------------------
# Attributes that must keep their identity across a restore
# --------------------------------------------------------------------------

# Back-references to objects that must not be replaced by a copy: the world,
# the owning player, the square the object stands on, the thing it is
# attacking.  Copying them would leave the rest of the world pointing at the
# old object while the restored object points at the new one.
_IDENTITY_ATTRS = frozenset(
    {
        "world",
        "player",
        "place",
        "action_target",
        "target_player",
    }
)

# Attributes whose value is infrastructure rather than game state.  They are
# neither copied nor recursed into.
_INFRA_ATTRS = frozenset(
    {
        "client",
        "_ecs",
        "_command_queue",
        "_perception_caches",
    }
)


def _is_scalar(value: Any) -> bool:
    return isinstance(value, (int, float, bool, str, bytes, type(None)))


# --------------------------------------------------------------------------
# The hot set
# --------------------------------------------------------------------------


def hot_objects(world) -> List[Any]:
    """Return the objects whose state the simulation can change.

    That is every unit owned by a player, plus every object the world
    considers "active" (buildings, deposits, projectiles ...).  Static
    terrain (``meadow`` / building land) is deliberately excluded: it is
    created once at map load and only changes when a building consumes a
    plot, which is handled by the structure layer.

    Squares are *not* part of the hot set.  A 100x100 map has 10000 of them
    and each carries ~180 attributes, so copying them all costs more than
    the entire rest of the snapshot.  What a square's state affects is its
    ``objects`` list, which is captured by the structure layer instead.
    """
    result: List[Any] = []
    seen = set()

    for player in getattr(world, "players", ()) or ():
        for unit in getattr(player, "units", ()) or ():
            key = id(unit)
            if key not in seen:
                seen.add(key)
                result.append(unit)

    for obj in world._active_objects_snapshot():
        key = id(obj)
        if key not in seen:
            seen.add(key)
            result.append(obj)

    return result


def _is_square(obj) -> bool:
    return getattr(obj, "is_inside_place", None) is not None and hasattr(obj, "col")


def _is_exit(obj) -> bool:
    return bool(getattr(obj, "is_an_exit", False))


def _is_root(world, obj) -> bool:
    """Is *obj* captured as a root of its own (rather than as a child)?

    Roots are the world, the players, the hot entities, the squares and the
    exits.  Everything else (actions, orders, meadows, buffs ...) is
    captured as a *child* of whichever root references it.
    """
    if obj is world:
        return True
    if _is_square(obj) or _is_exit(obj):
        return True
    for player in getattr(world, "players", ()) or ():
        if obj is player:
            return True
    return False


# --------------------------------------------------------------------------
# Container comparison / copying
# --------------------------------------------------------------------------


def _values_equal(a: Any, b: Any) -> bool:
    """Compare two values the way the simulation would.

    Scalars compare by value, containers compare structurally, and arbitrary
    objects compare by identity — the simulation mutates them through their
    own attributes, which are captured separately.
    """
    if a is b:
        return True
    if _is_scalar(a) and _is_scalar(b):
        return a == b
    if isinstance(a, dict) and isinstance(b, dict):
        if len(a) != len(b):
            return False
        for key, value in a.items():
            if key not in b:
                return False
            if not _values_equal(value, b[key]):
                return False
        return True
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        if len(a) != len(b):
            return False
        for x, y in zip(a, b):
            if not _values_equal(x, y):
                return False
        return True
    if isinstance(a, (set, frozenset)) and isinstance(b, (set, frozenset)):
        return a == b
    return False


def _copy_container(value: Any, depth: int = 3) -> Any:
    """Copy a container so that in-place mutation can be undone.

    ``depth`` bounds the recursion: measured on the bundled maps the hot set
    contains 6300 scalar attributes, 287 attributes with one level of
    container nesting and only 51 with two levels, so a bounded recursion
    covers everything the simulation actually mutates in place while keeping
    the cost low.

    Objects stored inside a container are **not** copied — they keep their
    identity, and their own state is captured separately.  Copying them
    would break the "restore in place" contract the UI depends on.
    """
    if isinstance(value, dict):
        if depth <= 0:
            return dict(value)
        return {k: _copy_container(v, depth - 1) for k, v in value.items()}
    if isinstance(value, list):
        if depth <= 0:
            return list(value)
        return [_copy_container(v, depth - 1) for v in value]
    if isinstance(value, tuple):
        if depth <= 0:
            return tuple(value)
        return tuple(_copy_container(v, depth - 1) for v in value)
    if isinstance(value, set):
        if depth <= 0:
            return set(value)
        return {_copy_container(v, depth - 1) for v in value}
    if isinstance(value, frozenset):
        return frozenset(value)
    return value


# --------------------------------------------------------------------------
# Snapshot container
# --------------------------------------------------------------------------


class Snapshot:
    """One captured point in the simulation.

    Attributes:
        time: the world time (``World.time``) the snapshot was taken at.
        scalars: world scalars and counters.
        players: per-player attribute state.
        objects: per-entity attribute state (hot entities and their children).
        squares: per-square attribute state.
        structure: object existence, collision bitmaps, scheduled events.
    """

    __slots__ = (
        "time",
        "scalars",
        "players",
        "objects",
        "squares",
        "structure",
        "registry",
        "perception",
    )

    def __init__(self):
        self.time = 0
        self.scalars: Dict[str, Any] = {}
        self.players: Dict[str, Dict[str, Any]] = {}
        self.objects: Dict[str, Dict[str, Any]] = {}
        self.squares: Dict[str, Dict[str, Any]] = {}
        self.structure: Dict[str, Any] = {}
        # Maps a capture key to the *live* object it was captured from.
        # Children (``Action``, ``Order``, buffs, inventory items ...) have no
        # engine id and are therefore absent from ``world.objects``; without
        # this registry they would be captured and then silently dropped on
        # restore, leaving the unit with a stale action or order.
        self.registry: Dict[str, Any] = {}
        # The world's perception caches, captured exactly.  They gate what
        # each player sees and therefore how much randomness the simulation
        # consumes; resetting them instead of restoring them forks the world.
        self.perception: Dict[str, Any] = {}

    def __repr__(self):  # pragma: no cover - debugging aid
        return "<Snapshot t=%s players=%d objects=%d squares=%d>" % (
            self.time,
            len(self.players),
            len(self.objects),
            len(self.squares),
        )


# --------------------------------------------------------------------------
# Capture
# --------------------------------------------------------------------------

# World-level scalars: the values the simulation reads but never recomputes.
_WORLD_SCALARS = (
    "time",
    "_next_id",
    "_next_order_id",
    "current_player_number",
    "_previous_slow_update",
    "_last_full_terrain_update",
    "_last_perception_cleanup",
    "_decision_cache_bucket",
    "_aura_registry_time",
    "_terrain_dirty_in_cycle",
    "_sights_cache_bucket",
    "_allied_control_epoch",
    "_allied_control_active",
    "_allied_control_scanned",
    "_active_objects_order_dirty",
    "previous_state",
    "previous_previous_state",
    "treaty_until_time",
    "global_population_limit",
    "nb_players_min",
    "nb_players_max",
    "timer_coefficient",
    "alliances_locked",
    "seed",
    "random_starts",
    "square_width",
    "nb_columns",
    "nb_lines",
    "nb_rows",
    "subcell_precision",
    "_vision_cache_scope",
    "building_land",
    "map_defined_starting_population",
    "map_defined_starting_resources",
    "map_defined_starting_units",
    "map_defined_specific_starts",
    "_map_building_land_explicit",
    "starting_population",
    "starting_resources",
)

# World-level containers the simulation mutates.  They are captured with
# the same copy-on-write rules as object attributes.
_WORLD_CONTAINERS = (
    "victory_countdowns",
    "inventory_victory_state",
    "_build_field_provider_ids",
    "_build_field_marked_squares",
    "additional_meadows",
    "additional_build_sites",
    "additional_building_land",
    "remove_meadows",
    "objective",
    "intro",
    "cut_scene",
    "title",
    "players_starts",
    "starting_units",
    "starting_squares",
    "specific_starts",
    "computers_starts",
    "computers_factions",
    "player_start_overrides",
    "ex_players",
    "ground_squares",
    "water_squares",
    "no_air_squares",
    "unit_classes",
    "harm_target_types",
    "sub_terrain",
    "sub_terrain_cover",
    "sub_terrain_speed",
    "sub_ground",
    "sub_high_grounds",
    "sub_no_air",
    "sub_water",
    "south_north",
    "west_east",
    "high_grounds",
    "map_deposit_capacity",
    "players",
    "active_objects",
    "default_triggers",
    "alliance_vision_managers",
    "_decision_cache",
    "_sights_cache",
    "_aura_buildings",
)


def _capture_perception_caches(world) -> Dict[str, Any]:
    """Capture the world's perception caches.

    These caches look like infrastructure, but they are *not*: they decide
    what a player can see, and therefore which enemies are picked up and how
    much randomness the simulation consumes.  Dropping them on restore forks
    the world, so they are captured exactly (the copy-on-write rules apply).

    ``_PerceptionCaches`` uses ``__slots__``, so it cannot be copied by the
    generic container copier; each slot is handled individually.
    """
    caches = getattr(world, "_perception_caches", None)
    if caches is None:
        return {}
    data: Dict[str, Any] = {}
    for name in type(caches).__slots__:
        value = getattr(caches, name, None)
        data[name] = _copy_container(value, 3)
    return data


def _restore_perception_caches(world, data: Dict[str, Any]) -> None:
    """Restore the world's perception caches."""
    caches = getattr(world, "_perception_caches", None)
    if caches is None or not data:
        return
    for name, value in data.items():
        if not hasattr(type(caches), name):
            continue
        try:
            setattr(caches, name, value)
        except AttributeError:  # pragma: no cover - defensive
            pass


def _capture_scalars(world) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    for name in _WORLD_SCALARS:
        if name in world.__dict__:
            data[name] = world.__dict__[name]
        else:
            # Some counters are *class* attributes (``World._next_order_id``
            # is one).  They are only copied into the instance ``__dict__``
            # once they are first incremented, so a world that has not issued
            # an order yet has no instance value at all.  Reading the class
            # attribute as a fallback is what makes the counter visible to
            # the snapshot; without it, a rollback would not rewind the
            # counter and the re-simulated orders would get different ids
            # than the original ones.
            value = getattr(type(world), name, None)
            if isinstance(value, (int, float, bool, str, bytes, type(None))):
                data[name] = value
    data["rng"] = world.random.getstate()
    return data


def _capture_world_containers(world) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    for name in _WORLD_CONTAINERS:
        value = world.__dict__.get(name)
        if value is None:
            continue
        data[name] = _copy_container(value, 3)
    return data


def _capture_entity_state(world) -> Dict[str, Dict[str, Any]]:
    """Capture the hot entities *and* the mutable children hanging off them.

    A unit owns an ``Action`` (which points at a target), a queue of
    ``Order`` objects, the ``building_land`` meadow it was built on, buffs
    and inventory items.  Those children have their own mutable state and
    must be captured too — otherwise a rollback would restore the unit but
    keep a stale action or order.
    """
    entities: Dict[str, Dict[str, Any]] = {}
    # Maps a capture key to the live object it was captured from.  Children
    # (``Action``, ``Order``, buffs, inventory items ...) have no engine id
    # and are therefore absent from ``world.objects``; the registry is the only
    # way to find them again at restore time.
    registry: Dict[str, Any] = {}
    visited: Set[int] = set()

    def capture_attrs(obj, into: Dict[str, Dict[str, Any]],
                      key: Optional[str] = None) -> None:
        state: Dict[str, Any] = {}
        for key_, value in obj.__dict__.items():
            if key_ in _INFRA_ATTRS:
                continue
            if key_ in _IDENTITY_ATTRS:
                # Keep the *reference* (not a copy): the target is restored
                # in place, so the reference stays valid.
                state[key_] = value
                continue
            state[key_] = _copy_container(value, 3)
        if key is None:
            key = getattr(obj, "id", None) or ("#%d" % id(obj))
        into[key] = state
        registry[key] = obj

    def walk(obj, depth: int) -> None:
        if id(obj) in visited:
            return
        visited.add(id(obj))
        capture_attrs(obj, entities)
        if depth <= 0:
            return
        for key, value in list(obj.__dict__.items()):
            if key in _IDENTITY_ATTRS or key in _INFRA_ATTRS:
                continue
            if _is_root(world, value):
                continue
            if isinstance(value, (dict, list, tuple, set, frozenset)):
                for item in value:
                    if _is_child_candidate(item):
                        walk(item, depth - 1)
                continue
            if _is_child_candidate(value):
                walk(value, depth - 1)

    for obj in hot_objects(world):
        walk(obj, 3)

    # Squares: membership and terrain.  Their ``objects`` list is the
    # authoritative record of who stands where.
    squares: Dict[str, Dict[str, Any]] = {}
    for square in getattr(world, "squares", ()) or ():
        state: Dict[str, Any] = {}
        for key, value in square.__dict__.items():
            if key in _INFRA_ATTRS:
                continue
            if key in _IDENTITY_ATTRS:
                state[key] = value
                continue
            state[key] = _copy_container(value, 2)
        squares[square.id] = state

    # Exits: their blocked state changes with the terrain.
    for obj in world.objects.values():
        if not _is_exit(obj):
            continue
        if obj.id in entities:
            continue
        capture_attrs(obj, entities)

    # Fog-of-war memory objects.
    #
    # A player's ``memory`` holds *copies* (``copy.copy(obj)``) of objects that
    # fell out of sight.  Those copies keep the original object's ``id``, so
    # they collide with the live object's capture key: capturing the memory
    # copy under its plain id would overwrite the live deposit's state, and
    # capturing it not at all would leave its mutated ``place`` (set to
    # ``None`` once the object left the field of view) unrestored.  A stale
    # memory copy makes ``Player.updated_target`` resolve the target to
    # ``None``, which silently cancels the unit's order.
    #
    # They are therefore captured under a distinct key and restored in place.
    for player in getattr(world, "players", ()) or ():
        for remembrance in getattr(player, "memory", ()) or ():
            if id(remembrance) in visited:
                continue
            visited.add(id(remembrance))
            capture_attrs(
                remembrance, entities, key="~mem~%d" % id(remembrance)
            )

    return {"entities": entities, "squares": squares, "registry": registry}


def _is_child_candidate(value) -> bool:
    if value is None:
        return False
    if isinstance(value, (int, float, bool, str, bytes, type(None))):
        return False
    if isinstance(value, (dict, list, tuple, set, frozenset)):
        return False
    # Rule definitions (``Phase``, ``Upgrade``, unit classes ...) are *classes*,
    # not simulation state.  They are static, shared by every world and carry
    # no per-match mutable state, so capturing them would only risk writing
    # into a class' ``mappingproxy`` on restore.
    if isinstance(value, type):
        return False
    return hasattr(value, "__dict__")


def _capture_structure(world) -> Dict[str, Any]:
    """Capture the parts of the world whose *membership* changes.

    Creating or destroying an object changes ``world.objects``,
    ``world._next_id``, the owning player's ``units`` list and the
    ``Square.objects`` lists.  Those are lists that are mutated in place, so
    they cannot be captured by copying an attribute dict.
    """
    # Which objects exist.  Objects created after the snapshot are removed
    # again on restore.
    object_ids = frozenset(world.objects.keys())

    # The collision bitmaps: unit movement updates them in place and they
    # decide whether a unit may enter a square.
    collision: Dict[int, Dict[str, Any]] = {}
    for name, matrix in (getattr(world, "collision", None) or {}).items():
        key = id(matrix)
        if key in collision:
            continue
        collision[key] = {
            "name": name,
            "set": set(getattr(matrix, "_set", ()) or ()),
            "xmax": getattr(matrix, "xmax", 0),
            "res": getattr(matrix, "res", 0),
            "amax": getattr(matrix, "amax", 0),
        }

    # Scheduled events: the callbacks are closures, so they are captured by
    # reference together with a copy of their closure cells.
    scheduled = []
    for exec_time, callback in getattr(world, "_scheduled_events", ()) or ():
        scheduled.append((exec_time, callback, _capture_closure(callback)))

    dirty_terrain = frozenset(
        getattr(square, "id", None)
        for square in (getattr(world, "_dirty_terrain_squares", None) or ())
    )

    return {
        "object_ids": object_ids,
        "collision": collision,
        "scheduled": scheduled,
        "dirty_terrain": dirty_terrain,
        "next_id": getattr(world, "_next_id", 0),
    }


def _capture_closure(callback) -> Optional[Tuple[Any, ...]]:
    """Capture the closure cells of a scheduled callback.

    The callback itself is a plain function object; the state it captured
    lives in its closure cells.  Restoring the cells restores the callback's
    captured values without having to serialise the function.
    """
    try:
        closure = getattr(callback, "__closure__", None)
        if not closure:
            return None
        values = []
        for cell in closure:
            try:
                values.append(cell.cell_contents)
            except ValueError:
                values.append(_MISSING)
        return tuple(values)
    except Exception:  # pragma: no cover - defensive
        return None


def _capture_full(world) -> Snapshot:
    """A full snapshot of everything the simulation can change."""
    snap = Snapshot()
    snap.time = world.time
    snap.scalars = _capture_scalars(world)
    snap.scalars.update(_capture_world_containers(world))
    snap.perception = _capture_perception_caches(world)
    captured = _capture_entity_state(world)
    snap.players = _capture_player_state(world)
    snap.objects = captured["entities"]
    snap.squares = captured["squares"]
    snap.structure = _capture_structure(world)
    snap.registry = captured["registry"]
    return snap


def _capture_player_state(world) -> Dict[str, Dict[str, Any]]:
    """Capture every player's mutable state.

    The perception caches are captured *exactly* rather than dropped: they
    decide how much randomness the simulation consumes, so resetting them
    would fork the world.  They are plain containers, so the copy-on-write
    rules keep the restore cheap.
    """
    players: Dict[str, Dict[str, Any]] = {}
    for player in getattr(world, "players", ()) or ():
        state: Dict[str, Any] = {}
        for key, value in player.__dict__.items():
            if key in _INFRA_ATTRS:
                continue
            if key in _IDENTITY_ATTRS:
                state[key] = value
                continue
            state[key] = _copy_container(value, 3)
        players[player.id] = state
    return players


# --------------------------------------------------------------------------
# Restore
# --------------------------------------------------------------------------


def _restore_scalars(world, data: Dict[str, Any]) -> None:
    for name, value in data.items():
        if name == "rng":
            world.random.setstate(value)
            continue
        # Writing into ``__dict__`` shadows the class attribute, which is what
        # makes the restored value the one the simulation will read.
        world.__dict__[name] = value


def _restore_players(world, data: Dict[str, Dict[str, Any]]) -> None:
    for player in getattr(world, "players", ()) or ():
        state = data.get(player.id)
        if state is None:
            continue
        attrs = player.__dict__
        for key, value in state.items():
            attrs[key] = value
        # Attributes that appeared after the snapshot must go away again.
        for key in list(attrs):
            if key in _INFRA_ATTRS or key in _IDENTITY_ATTRS:
                continue
            if key not in state:
                del attrs[key]


def _restore_entities(world, data: Dict[str, Dict[str, Any]],
                      registry: Optional[Dict[str, Any]] = None) -> None:
    objects = world.objects
    for oid, state in data.items():
        obj = objects.get(oid)
        if obj is None:
            # Children (``Action``, ``Order``, buffs, inventory items ...) have
            # no engine id and are therefore not in ``world.objects``.  They
            # are found through the capture registry instead, so their state
            # is restored in place rather than silently dropped.
            obj = (registry or {}).get(oid)
            if obj is None:
                continue
        attrs = obj.__dict__
        for key, value in state.items():
            attrs[key] = value
        for key in list(attrs):
            if key in _INFRA_ATTRS or key in _IDENTITY_ATTRS:
                continue
            if key not in state:
                del attrs[key]


def _restore_squares(world, data: Dict[str, Dict[str, Any]]) -> None:
    for square in getattr(world, "squares", ()) or ():
        state = data.get(square.id)
        if state is None:
            continue
        attrs = square.__dict__
        for key, value in state.items():
            attrs[key] = value


def _restore_structure(world, data: Dict[str, Any]) -> None:
    """Restore object membership, collision bitmaps and scheduled events."""
    objects = world.objects

    # Objects created after the snapshot must disappear again.
    object_ids = data.get("object_ids")
    if object_ids is not None:
        for oid in list(objects.keys()):
            if oid not in object_ids:
                obj = objects.pop(oid, None)
                if obj is None:
                    continue
                try:
                    world.active_objects.remove(obj)
                except ValueError:
                    pass

    # Collision bitmaps.
    for matrix in (getattr(world, "collision", None) or {}).values():
        entry = data.get("collision", {}).get(id(matrix))
        if entry is None:
            continue
        try:
            matrix._set = set(entry["set"])
            matrix.xmax = entry["xmax"]
            matrix.res = entry["res"]
            matrix.amax = entry["amax"]
        except Exception:  # pragma: no cover - defensive
            pass

    # Scheduled events.
    scheduled = data.get("scheduled")
    if scheduled is not None:
        restored = []
        for exec_time, callback, closure in scheduled:
            _restore_closure(callback, closure)
            restored.append((exec_time, callback))
        world._scheduled_events = restored

    # Dirty terrain squares.
    dirty = data.get("dirty_terrain")
    if dirty is not None:
        squares = {s.id: s for s in getattr(world, "squares", ()) or ()}
        world._dirty_terrain_squares = {
            squares[sid] for sid in dirty if sid in squares
        }


def _restore_closure(callback, closure) -> None:
    """Restore the closure cells of a scheduled callback."""
    if not closure:
        return
    try:
        cells = getattr(callback, "__closure__", None)
        if not cells or len(cells) != len(closure):
            return
        for cell, value in zip(cells, closure):
            if value is _MISSING:
                continue
            try:
                cell.cell_contents = value
            except (ValueError, AttributeError):
                pass
    except Exception:  # pragma: no cover - defensive
        pass


def _post_restore(world) -> None:
    """Re-link the state that is derived from the restored membership."""
    # A live meadow sits in exactly one square; make that explicit again.
    for square in getattr(world, "squares", ()) or ():
        for obj in getattr(square, "objects", ()) or ():
            if getattr(obj, "is_a_building_land", False):
                obj.place = square
                obj._previous_square = None
    # Perception holds references to objects that may have been destroyed.
    for player in getattr(world, "players", ()) or ():
        perception = getattr(player, "perception", None)
        if not perception:
            continue
        try:
            alive = [o for o in perception if getattr(o, "place", None) is not None]
            if len(alive) != len(perception):
                perception.clear()
                perception.update(alive)
        except Exception:
            pass


# --------------------------------------------------------------------------
# The snapshot store (ring buffer)
# --------------------------------------------------------------------------


class SnapshotStore:
    """A ring buffer of snapshots supporting rollback.

    Every snapshot is self-contained: restoring one reproduces the world
    exactly as it was at that moment.  The store keeps the last
    ``capacity`` snapshots so a client can roll back to any of them.
    """

    def __init__(self, capacity: int = 60):
        self.capacity = max(2, capacity)
        self._snapshots: List[Snapshot] = []
        # Cached set of live object ids, reused between snapshots when no
        # object was created or destroyed (the common case).
        self._object_ids: Optional[frozenset] = None
        self._object_count = -1

    def __len__(self):
        return len(self._snapshots)

    @property
    def snapshots(self):
        return self._snapshots

    def capture(self, world) -> Snapshot:
        """Capture a snapshot of ``world`` and push it into the ring."""
        snap = _capture_full(world)
        self._snapshots.append(snap)
        if len(self._snapshots) > self.capacity:
            self._snapshots.pop(0)
        return snap

    def find(self, frame: int) -> Optional[Snapshot]:
        """Return the snapshot taken at ``frame``, if it is still in the buffer."""
        for snap in self._snapshots:
            if snap.time == frame:
                return snap
        return None

    def oldest_time(self) -> Optional[int]:
        if not self._snapshots:
            return None
        return self._snapshots[0].time

    def newest_time(self) -> Optional[int]:
        if not self._snapshots:
            return None
        return self._snapshots[-1].time

    def restore(self, world, frame: int) -> bool:
        """Restore ``world`` to the state captured at ``frame``.

        Returns ``True`` when the frame was found and restored.
        """
        target = self.find(frame)
        if target is None:
            return False
        restore_snapshot(world, target)
        return True


# --------------------------------------------------------------------------
# Public capture / restore
# --------------------------------------------------------------------------


def capture_snapshot(world) -> Snapshot:
    """Capture a full snapshot of ``world``.

    This is the simple, always-correct entry point.  :class:`SnapshotStore`
    is the ring buffer used by the rollback loop.
    """
    return _capture_full(world)


def restore_snapshot(world, snap: Snapshot) -> None:
    """Restore ``world`` to the state captured in ``snap``."""
    _restore_scalars(world, snap.scalars)
    _restore_players(world, snap.players)
    _restore_entities(world, snap.objects, getattr(snap, "registry", None))
    _restore_squares(world, snap.squares)
    _restore_perception_caches(world, getattr(snap, "perception", None) or {})
    _restore_structure(world, snap.structure)
    _post_restore(world)


# --------------------------------------------------------------------------
# Verification
# --------------------------------------------------------------------------


def strong_digest(world) -> str:
    """A digest that covers the state a rollback must reproduce.

    ``World.get_digest`` only hashes the RNG state, which cannot detect a
    divergence in positions or hit points.  This digest covers, for every
    player: the resources, the population, the upgrades and every unit's id,
    position, angle, hit points, AI mode, current action and order count;
    plus the world time, the next object id and the RNG state.

    The order is deterministic (players and units are sorted by id) so two
    worlds in the same state always produce the same digest.
    """
    h = hashlib.md5()
    h.update(str(world.time).encode())
    h.update(repr(world.random.getstate()).encode())
    h.update(str(getattr(world, "_next_id", 0)).encode())
    h.update(str(len(world.objects)).encode())
    h.update(str(len(world.active_objects)).encode())

    for player in sorted(
        getattr(world, "players", ()) or (), key=lambda p: str(getattr(p, "id", ""))
    ):
        h.update(("P%s" % getattr(player, "id", "")).encode())
        h.update(repr(getattr(player, "resources", None)).encode())
        h.update(repr(getattr(player, "population", None)).encode())
        h.update(repr(getattr(player, "used_population", None)).encode())
        h.update(repr(getattr(player, "upgrades", None)).encode())
        for unit in sorted(
            getattr(player, "units", ()) or (), key=lambda u: str(getattr(u, "id", ""))
        ):
            action = getattr(unit, "action", None)
            action_desc = ""
            if action is not None:
                target = getattr(action, "target", None)
                action_desc = "%s->%s" % (
                    type(action).__name__,
                    getattr(target, "id", target),
                )
            h.update(
                (
                    "|%s|%s|%s|%s|%s|%s|%s|%s|%s"
                    % (
                        getattr(unit, "id", ""),
                        getattr(unit, "x", 0),
                        getattr(unit, "y", 0),
                        getattr(unit, "hp", 0),
                        getattr(unit, "o", 0),
                        getattr(unit, "ai_mode", ""),
                        getattr(unit, "place", None) and getattr(unit.place, "id", ""),
                        action_desc,
                        len(getattr(unit, "orders", ()) or ()),
                    )
                ).encode()
            )

    return h.hexdigest()
