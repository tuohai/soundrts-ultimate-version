from ..worldroom import Square
from .base import Order
from .immediate import ImmediateOrder


class TransportOrder(Order):
    @classmethod
    def is_allowed(cls, unit, *unused_args):
        return unit.transport_capacity > 0

    def _mark_load_invalid(self):
        self.mark_as_impossible("load_invalid")

    def _mark_load_failed(self):
        self.mark_as_impossible("load_failed")

    def _mark_unload_invalid(self):
        self.mark_as_impossible("unload_invalid")

    def _mark_unload_failed(self):
        self.mark_as_impossible("unload_failed")

    def _inside_count(self):
        inside = getattr(self.unit, "inside", None)
        if inside is None:
            return 0
        return len(inside.objects)


class LoadOrder(TransportOrder):

    keyword = "load"
    nb_args = 1

    def on_queued(self):
        self.target = self.player.get_object_by_id(self.args[0])
        if self.target is None or self.unit.player is not getattr(
            self.target, "player", None
        ):
            self._mark_load_invalid()
            return
        self.unit.notify("order_ok")

    def execute(self):
        self.update_target()
        if self.target is None:
            self._mark_load_invalid()
            return
        if not self.unit.have_enough_space(self.target):
            self._mark_load_failed()
            return
        if self.unit.airground_type == "water":
            if (
                self.target.place in self.unit.place.strict_neighbors
                and not self.target.place.high_ground
            ):
                if self.unit.load(self.target):
                    self.mark_as_complete()
                else:
                    return
            else:
                return
            return
        if self.unit.place != self.target.place:
            if self.unit.speed:
                self.move_to_or_fail(self.target.place)
            else:
                self.mark_as_complete()
        else:
            if self.unit.load(self.target):
                self.mark_as_complete()
            else:
                self._mark_load_failed()


class EnterOrder(ImmediateOrder):

    keyword = "enter"
    nb_args = 1

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        return True

    def immediate_action(self):
        self.target = self.player.get_object_by_id(self.args[0])
        if self.target is None or self.target.player is not self.unit.player:
            self.unit.notify("order_impossible,load_invalid")
            return

        self.target.take_order(["load", self.unit.id], forget_previous=False)
        if not (
            self.unit.airground_type == "ground"
            and self.target.airground_type == "water"
        ):
            self.unit.take_order(["go", self.target.id])


class LoadAllOrder(TransportOrder):

    keyword = "load_all"
    nb_args = 1

    def on_queued(self):
        self.target = self.player.get_object_by_id(self.args[0])
        if not isinstance(self.target, Square) and hasattr(self.target, "place"):
            self.target = self.target.place
        if self.target is None:
            self._mark_load_invalid()
            return
        self.unit.notify("order_ok")

    def execute(self):
        self.update_target()
        if self.target is None:
            self._mark_load_invalid()
            return
        if self.unit.airground_type == "water":
            if self.target in self.unit.place.strict_neighbors and not self.target.high_ground:
                loaded = self.unit.load_all(self.target)
                if loaded:
                    self.mark_as_complete()
                else:
                    return
            else:
                return
            return
        if self.unit.place != self.target:
            if hasattr(self.unit, "blocked_exit") and self.unit.blocked_exit:
                exit = self.unit.blocked_exit
                if (self.target is exit.place or
                    self.target is exit.other_side.place):
                    loaded = self.unit.load_all(self.target)
                    if loaded:
                        self.mark_as_complete()
                    else:
                        self._mark_load_invalid()
                    return
            self.move_to_or_fail(self.target)
            return
        loaded = self.unit.load_all()
        if loaded:
            self.mark_as_complete()
        else:
            self._mark_load_invalid()


class UnloadAllOrder(TransportOrder):

    keyword = "unload_all"
    nb_args = 1

    def on_queued(self):
        self.target = self.player.get_object_by_id(self.args[0])
        if not isinstance(self.target, Square) and hasattr(self.target, "place"):
            self.target = self.target.place
        if self.target is None:
            self._mark_unload_invalid()
            return
        if self._inside_count() == 0:
            self._mark_unload_invalid()
            return
        self.unit.notify("order_ok")

    def execute(self):
        self.update_target()
        if self.target is None:
            self._mark_unload_invalid()
            return
        if self._inside_count() == 0:
            self._mark_unload_invalid()
            return
        if self.unit.airground_type == "water":
            if (self.target in self.unit.place.strict_neighbors and
                self.target.is_ground and not self.target.high_ground):
                has_ground_units = any(
                    obj.airground_type == "ground" for obj in self.unit.inside.objects
                )
                has_water_units = any(
                    obj.airground_type == "water" for obj in self.unit.inside.objects
                )
                if has_ground_units or not has_water_units:
                    before = self._inside_count()
                    unloaded = self.unit.unload_all(self.target)
                    if unloaded:
                        self.mark_as_complete()
                    elif before:
                        self._mark_unload_failed()
                    else:
                        self._mark_unload_invalid()
                else:
                    self._mark_unload_failed()
            else:
                self._mark_unload_failed()
            return
        if self.unit.place != self.target:
            if hasattr(self.unit, "blocked_exit") and self.unit.blocked_exit:
                exit = self.unit.blocked_exit
                if (self.target is exit.place or
                    self.target is exit.other_side.place):
                    before = self._inside_count()
                    unloaded = self.unit.unload_all(self.target)
                    if unloaded:
                        self.mark_as_complete()
                    elif before:
                        self._mark_unload_failed()
                    else:
                        self._mark_unload_invalid()
                    return
            self.move_to_or_fail(self.target)
            return
        before = self._inside_count()
        unloaded = self.unit.unload_all()
        if unloaded:
            self.mark_as_complete()
        elif before:
            self._mark_unload_failed()
        else:
            self._mark_unload_invalid()
