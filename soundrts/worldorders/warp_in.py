"""Orders that summon units onto a remote square (warp-in / nydus).

See ``soundrts/world_warp_in.py`` for the rules-side description.  Two
orders live here:

``warp_in <unit_type> <target>``
    WARP IN: pick the unit type first, then click the destination.
``nydus_in <unit_type> <target>``
    NYDUS: the Zerg flavour of the same primitive (a unit crawls out of
    the ground at the destination).

Both are two-argument orders, so the client needs to remember the chosen
unit type between the two clicks.  The client's order machinery handles
the ``nb_args == 2`` case by asking for the type first; see
``worldorders/base.py`` for how ``ComplexOrder`` binds ``args[0]``.
"""

from ..world_warp_in import (
    is_warp_in_building,
    perform_warp_in,
    warp_in_is_ready,
    warp_in_unit_types,
)
from .base import BasicOrder


class WarpInOrder(BasicOrder):
    """Warp a unit onto a remote square (Protoss Warp Gate / Zerg Nydus).

    The order takes two arguments: the unit type to summon and the id of
    the destination object.  The building must be charged; otherwise the
    order is rejected with ``order_impossible``.
    """

    keyword = "warp_in"
    nb_args = 2
    is_imperative = True

    def __init__(self, unit, args):
        # ``args`` is [unit_type, target_id]; BasicOrder keeps args[1:].
        BasicOrder.__init__(self, unit, list(args[1:]) if len(args) > 1 else [])
        self.type_name = args[0] if args else ""

    @classmethod
    def _menu_types(cls, unit):
        """The unit types this building may currently warp in."""
        if unit is None or not getattr(unit, "is_a_building", False):
            return []
        if not is_warp_in_building(unit):
            return []
        return [name for name, _cls in warp_in_unit_types(unit)]

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        if unit is None:
            return False
        if not getattr(unit, "is_a_building", False):
            return False
        if not is_warp_in_building(unit):
            return False
        return "warp_in" in getattr(unit, "basic_skills", ())

    @classmethod
    def menu(cls, unit, strict=False):
        if not cls.is_allowed(unit):
            return []
        return [cls.keyword + " " + name for name in cls._menu_types(unit)]

    def on_queued(self):
        # args[0] is the destination id, args[1] the unit type — the order
        # is sent as "warp_in <unit_type> <target_id>".
        self.target = None
        if len(self.args) >= 2:
            self.target = self.player.get_object_by_id(self.args[1])
        if self.target is None:
            self.mark_as_impossible("cannot_build_here")
            return
        self.type_name = self.args[0]
        if self.type_name not in self._menu_types(self.unit):
            self.mark_as_impossible("cannot_build_here")
            return
        if not warp_in_is_ready(self.unit):
            self.mark_as_impossible("not_ready")
            return
        self.unit.notify("order_ok")

    def execute(self):
        if self.target is None:
            self.mark_as_complete()
            return
        ok, _reason = perform_warp_in(self.unit, self.type_name, self.target)
        if ok:
            self.mark_as_complete()
            self.unit.notify("order_ok")
        else:
            self.mark_as_impossible(_reason)


class NydusInOrder(WarpInOrder):
    """Nydus canal: the Zerg flavour of the warp-in order.

    Same primitive as :class:`WarpInOrder`, different keyword so the UI
    and the voice feedback say "nydus" instead of "warp-in".
    """

    keyword = "nydus_in"
    nb_args = 2
    is_imperative = True

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        if unit is None:
            return False
        if not getattr(unit, "is_a_building", False):
            return False
        if not is_warp_in_building(unit):
            return False
        return "nydus_in" in getattr(unit, "basic_skills", ())
