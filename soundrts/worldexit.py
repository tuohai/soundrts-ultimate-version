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
        return d

    @property
    def other_side(self):
        return self.world.objects[self._other_side_id]

    is_blocked_by_forests = False

    def is_blocked(self, o=None, ignore_enemy_walls=False, ignore_forests=False):
        """D-Phase 2: 仍保留原 try/except 控制流 (4.2M calls / 5min,
        try/except 的成本 + 缓存读写 已平衡, 改用 try-free 流反而退化).
        getattr fallback 仅用 b.is_a_gate (Entity class default False).
        """
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
                if key in cache:
                    return cache[key]
        except Exception:
            cache = None
        # 快速路径：森林阻塞
        if not ignore_forests and self.is_blocked_by_forests:
            result = True
            if cache is not None:
                cache[key] = result
            return result
        # 本侧阻塞者
        blockers = self._blockers
        if blockers:
            for b in blockers:
                if ignore_enemy_walls and (o is None or o.is_an_enemy(b)):
                    continue
                if not b.is_a_gate or (o is None or o.is_an_enemy(b)):
                    result = True
                    if cache is not None:
                        cache[key] = result
                    return result
        # 另一侧阻塞者
        other = getattr(self, 'other_side', None)
        if other is not None:
            other_blockers = getattr(other, '_blockers', None)
            if other_blockers:
                for b in other_blockers:
                    if ignore_enemy_walls and (o is None or o.is_an_enemy(b)):
                        continue
                    if not b.is_a_gate or (o is None or o.is_an_enemy(b)):
                        result = True
                        if cache is not None:
                            cache[key] = result
                        return result
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
        self.place.exits.remove(self)
        if self.other_side:
            self.other_side.other_side = None
            self.other_side.delete()
        Entity.delete(self)


def passage(places, exit_type):
    place1, place2, is_a_portal = places
    if place1[0].is_water != place2[0].is_water and not (place1[0].is_ground and place2[0].is_ground):
#        warning(f"removed dangerous path between {place1[0]} and {place2[0]}")
        return
    exit1 = Exit(place1, exit_type, is_a_portal)
    exit2 = Exit(place2, exit_type, is_a_portal)
    exit1._other_side_id = exit2.id
    exit2._other_side_id = exit1.id
