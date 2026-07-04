import copy

from .definitions import rules
from .lib.nofloat import PRECISION, to_int
from .worldentity import Entity


class Deposit(Entity):

    resource_type = None
    resource_regen = 0
    extraction_time = None  # 提取时间
    extraction_qty = None  # 提取量
    type_name = "deposit"  # 添加type_name属性

    def __init__(self, square, qty, x=None, y=None):
        if isinstance(qty, str):
            self.qty = to_int(qty)
        elif isinstance(qty, int):
            self.qty = qty if qty >= PRECISION else qty * PRECISION
        else:
            self.qty = 0
        self.qty_max = self.qty
        Entity.__init__(self, square, x, y)
        self._register_map_capacity()

    def _register_map_capacity(self, qty=None):
        world = getattr(self, "world", None)
        if world is None:
            return
        caps = getattr(world, "map_deposit_capacity", None)
        if caps is None:
            return
        resource_index = rules.parse_resource_type(self.resource_type)
        if resource_index is None:
            resource_index = 0
        amount = self.qty_max if qty is None else qty
        if 0 <= resource_index < len(caps) and amount > 0:
            caps[resource_index] += amount

    def _register_regen_capacity(self, qty):
        self._register_map_capacity(qty)

    def extract_resource(self, qty):
        actual_qty = min(qty, self.qty)
        self.qty -= actual_qty
        self.notify(f"qty_update,{self.qty}")
        if self.qty <= 0:
            self.die()
        return actual_qty

    def die(self):
        place, x, y = self.place, self.x, self.y
        self.notify("exhausted")
        self.delete()
        if self.building_land:
            self.building_land.move_to(place, x, y)

    def update(self):
        pass  # necessary to allow slow update

    def slow_update(self):
        if self.resource_regen and self.qty < self.qty_max:
            old_qty = self.qty
            self.qty = min(self.qty + self.resource_regen, self.qty_max)
            self._register_regen_capacity(self.qty - old_qty)
        if hasattr(self, 'time_limit') and self.time_limit is not None and self.place.world.time >= self.time_limit:
            self.delete()
        if hasattr(self, 'unit') and hasattr(self.unit, 'is_revivable') and self.unit.is_revivable:
            if not hasattr(self, '_revival_debug_printed'):
                self._revival_debug_printed = True

            if self.place.world.time >= self._time_of_revival:
                if hasattr(self.unit, 'altar') and self.unit.altar:
                    self.move_to(self.unit.altar)
                self.resurrect()
                return


class BuildingLand(Entity):

    is_a_building_land = True
    collision = 0


from .lib.building_land import (  # noqa: E402
    building_land_class,
    building_land_type_names,
    building_land_types,
    create_building_land,
    default_building_land_type,
    is_building_land,
    nb_by_square_land_type,
    normalize_building_land_type_name,
    recreate_building_land,
)


class Corpse(Entity):

    type_name = "corpse"
    collision = 0

    def __init__(self, unit):
        self.unit = copy.copy(unit)
        if hasattr(self.unit, "_corpse_created"):
            try:
                delattr(self.unit, "_corpse_created")
            except Exception:
                pass
        Entity.__init__(self, unit.place, unit.x, unit.y)
        self.time_limit = self.place.world.time + 300 * PRECISION
        if self.unit.is_revivable:
            self.time_limit = float("inf")
            self._time_of_revival = (
                self.place.world.time + unit.revival_time
            )
        else:
            self.time_limit = self.place.world.time + unit.corpse_decay

    def update(self):
        pass  # necessary to allow slow update

    def slow_update(self):
        if hasattr(self, 'unit') and hasattr(self.unit, 'is_revivable') and self.unit.is_revivable:
            if not hasattr(self, '_revival_debug_printed'):
                self._revival_debug_printed = True

            player_in_game = True
            if hasattr(self.unit, 'player') and self.unit.player is not None:
                if not self.unit.player.is_playing:
                    player_in_game = False

            if player_in_game and self.place.world.time >= self._time_of_revival:
                if hasattr(self.unit, 'altar') and self.unit.altar:
                    self.move_to(self.unit.altar)
                self.resurrect()
                return
            elif not player_in_game and self.time_limit == float("inf"):
                self.time_limit = self.place.world.time + 300 * PRECISION

        if self.time_limit is not None and self.place.world.time >= self.time_limit:
            self.delete()

    def die(self, attacker):
        pass

    def resurrect(self):
        if hasattr(self, 'unit') and self.unit:
            self.unit.resurrect(self)
        else:
            print("无法复活：尸体没有关联单位")
            self.delete()
