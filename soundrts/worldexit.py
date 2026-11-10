from .lib.log import warning
from .worldentity import Entity


class Exit(Entity):

    other_side: "Exit"
    collision = 0
    is_a_building_land = False
    is_an_exit = True
    _other_side_id = None
    # D-Phase 2: class-level defaults 替代 hot-path getattr.
    # is_blocked 4.2M calls / 5min, 每 call 4-5 个 getattr.
    is_a_gate = False
    _blocked_cache = None
    _blockers = ()  # 实例 __init__ 会覆盖为 list

    def __init__(self, place, type_name, is_a_portal):
        self.type_name = type_name
        self.is_a_portal = is_a_portal
        place, x, y, o = place
        Entity.__init__(self, place, x, y, o)
        place.exits.append(self)
        self._blockers = []

    def __repr__(self):
        try:
            return "<Exit to '%s'>" % self.other_side.place.name
        except AttributeError:
            return "<Exit to nowhere>"

    def __getstate__(self):
        d = self.__dict__.copy()
        d.pop("_blocked_cache", None)
        # ``_other_side`` is a live reference to the partner Exit. Pickling it
        # would restore a *copy* of the partner instead of the live object in
        # ``world.objects``; the ``_other_side_id`` fallback in the
        # ``other_side`` property re-links the pair after a load.
        d.pop("_other_side", None)
        return d

    def __setstate__(self, state):
        # Empty state = Entity.clean() wiped __dict__; revive in rebuild_world_after_load.
        if not state:
            return
        self.__dict__.update(state)

    @property
    def other_side(self):
        # Hot path: 44M calls / 40min cw1 profile. The id->object lookup
        # (``self.world.objects[self._other_side_id]``) is two dict/index
        # operations behind a property descriptor on every single call.
        # The partner Exit is immutable for the lifetime of the pair (only
        # ``Exit.delete`` unlinks it, and that clears ``_other_side_id``),
        # so we keep a direct reference and fall back to the id lookup when
        # the cached partner is gone (e.g. right after a delete).
        partner = self._other_side
        if partner is not None:
            return partner
        oid = self._other_side_id
        if oid is None:
            return None
        return self.world.objects.get(oid)

    _other_side = None

    is_blocked_by_forests = False

    def is_blocked(self, o=None, ignore_enemy_walls=False, ignore_forests=False):
        """Is this exit blocked for *o*?

        Hot path: 56.4M calls / 40min cw1 profile (40.9s tottime, 101s
        cumtime). Two optimisations:

        1. **Fast path** — an exit with no blockers on either side is never
           blocked (a wall/gate is what blocks an exit, and those are rare
           compared to the ~50k plain exits of a map). The original code
           built a 4-tuple cache key and did two dict lookups *before*
           discovering that; this returns immediately instead.
        2. The remaining (rare) blocked case keeps the original time-bucketed
           cache so repeated queries inside one 250ms window stay cheap.
        """
        # 快速路径：森林阻塞
        if not ignore_forests and self.is_blocked_by_forests:
            return True

        blockers = self._blockers
        # ``getattr(self, 'other_side', None)`` in the original also swallowed
        # an AttributeError raised *inside* the property (e.g. an Exit whose
        # world is gone). Keep that behaviour.
        try:
            other = self.other_side
        except AttributeError:
            other = None
        if other is not None:
            other_blockers = getattr(other, "_blockers", None)
        else:
            other_blockers = None
        if not blockers and not other_blockers:
            # Nothing blocks this exit — the result cannot change until a
            # blocker is added/removed, so no caching is needed.
            return False

        # Slow path: there is at least one blocker, so consult the cache.
        cache = None
        key = None
        try:
            if ignore_enemy_walls:
                tb = self.world.time // 250
                viewer_id = o.id if o is not None else None
                key = (viewer_id, ignore_enemy_walls, ignore_forests, tb)
                cache = self._blocked_cache
                if cache is None:
                    self._blocked_cache = {}
                    cache = self._blocked_cache
                hit = cache.get(key)
                if hit is not None:
                    return hit
        except Exception:
            cache = None
        # 本侧阻塞者
        for b in blockers:
            if ignore_enemy_walls and (o is None or o.is_an_enemy(b)):
                continue
            if not b.is_a_gate or (o is None or o.is_an_enemy(b)):
                if cache is not None:
                    cache[key] = True
                return True
        # 另一侧阻塞者
        for b in other_blockers:
            if ignore_enemy_walls and (o is None or o.is_an_enemy(b)):
                continue
            if not b.is_a_gate or (o is None or o.is_an_enemy(b)):
                if cache is not None:
                    cache[key] = True
                return True
        # 无阻塞
        if cache is not None:
            cache[key] = False
        return False

    @property
    def blockers(self):
        return self._blockers + getattr(self.other_side, "_blockers", [])

    def add_blocker(self, o):
        self._blockers.append(o)

    def remove_blocker(self, o):
        self._blockers.remove(o)

    def delete(self):
        other_id = self._other_side_id
        self._other_side_id = None
        # Drop the cached partner reference too, otherwise ``other_side``
        # would keep returning a deleted Exit.
        self._other_side = None
        place = self.place
        if place is not None:
            if self in place.exits:
                place.exits.remove(self)
            if self in place.objects:
                place.objects.remove(self)
        if self.id is not None:
            self.world.objects.pop(self.id, None)
        self.world.unregister_entity(self)
        self.place = None
        if other_id is None:
            return
        other = self.world.objects.get(other_id)
        if other is None or other is self:
            return
        other._other_side_id = None
        other._other_side = None
        other_place = other.place
        if other_place is not None:
            if other in other_place.exits:
                other_place.exits.remove(other)
            if other in other_place.objects:
                other_place.objects.remove(other)
        if other.id is not None:
            self.world.objects.pop(other.id, None)
        self.world.unregister_entity(other)
        other.place = None


def passage(places, exit_type):
    place1, place2, is_a_portal = places
    if place1[0].is_water != place2[0].is_water and not (place1[0].is_ground and place2[0].is_ground):
#        warning(f"removed dangerous path between {place1[0]} and {place2[0]}")
        return
    exit1 = Exit(place1, exit_type, is_a_portal)
    exit2 = Exit(place2, exit_type, is_a_portal)
    exit1._other_side_id = exit2.id
    exit2._other_side_id = exit1.id
    # Keep a direct reference to the partner Exit as well: ``other_side`` is
    # read 44M times / 40min cw1 profile and the id->object dict lookup
    # was the whole cost of that property.
    exit1._other_side = exit2
    exit2._other_side = exit1
