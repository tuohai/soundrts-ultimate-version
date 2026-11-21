"""Warp-in / Nydus canal: summon units straight onto the battlefield.

StarCraft 2 has two "summon from elsewhere" mechanics:

* **Protoss Warp Gate** — a Protoss building that, once charged, warps in
  units at a remote location (the warp-in matrix).  The units appear
  instantly with a bright flash.
* **Zerg Nydus Canal** — a Zerg building that lets units crawl out of the
  ground at a remote location.

Both are the same engine primitive: *a player-owned building that can
teleport a set of unit types onto a target square chosen by the player*.

Rules side (all optional, all data-driven — the engine hardcodes no unit
name):

``warp_in_types``
    Space-separated list of unit type names this building can summon.
``warp_in_charge``
    How many units may be warped in before the building must recharge.
``warp_in_recharge``
    Milliseconds between two charges.  ``0`` means "recharge instantly".
``warp_in_needs_field``
    The build field the target square must carry (e.g. ``psi`` for the
    Protoss warp gate, ``creep`` for the nydus).  Empty = no requirement.
``warp_in_field_radius_m``
    Radius (meters) of the field the building projects; the warp-in
    destination must be inside it.
``warp_in_effect``
    Name of the effect class deployed at the destination for the duration
    of the warp-in animation (optional).

The rules.txt entry for a warp gate therefore reads:

```
def warp_gate
class protoss_building
warp_in_types zealot dragoon stalker
warp_in_charge 2
warp_in_recharge 45
warp_in_needs_field psi
warp_in_field_radius_m 20
"""

from .lib.nofloat import PRECISION, to_int
from .lib.log import info, warning


def _as_int(value, default=0):
    """Coerce a rules value to an int.

    Rules values may arrive as a plain int (``warp_in_charge 2`` stored on
    the class) or as a one-element list (the generic parser stores some
    numeric fields that way), so both forms must be accepted.
    """
    if value is None:
        return default
    if isinstance(value, (list, tuple)):
        if not value:
            return default
        value = value[0]
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _as_text(value, default=""):
    """Coerce a rules value to a string (lists become their first item)."""
    if value is None:
        return default
    if isinstance(value, (list, tuple)):
        if not value:
            return default
        value = value[0]
    return str(value).strip()


def warp_in_types(building):
    """The unit type names this building can warp in, as a list."""
    raw = getattr(building, "warp_in_types", None) or ""
    names = []
    if isinstance(raw, (list, tuple)):
        for item in raw:
            names.extend(str(item).replace(";", " ").split())
    else:
        names = str(raw).replace(";", " ").split()
    return [n for n in names if n and n != "0"]


def is_warp_in_building(building):
    """True when the building declares at least one warp-in unit type."""
    return bool(warp_in_types(building))


def warp_in_charge_max(building):
    """How many units may be warped in before a recharge is needed."""
    value = _as_int(getattr(building, "warp_in_charge", 0), 0)
    if value > 0:
        return value
    # Fall back on the rules class so a building that got its charge from
    # an upgrade still sees the base value.
    unit_type = getattr(building, "type_name", None)
    if unit_type:
        try:
            from .definitions import rules

            cls = rules.unit_class(unit_type)
            if cls is not None:
                return _as_int(getattr(cls, "warp_in_charge", 0), 0)
        except Exception:
            pass
    return 0


def warp_in_recharge_time(building):
    """Milliseconds needed to recharge one warp-in charge.

    ``warp_in_recharge`` is a PRECISION property (like ``hp_regen_cd``), so
    the rules value is already scaled to milliseconds -- the unit of the
    world clock.
    """
    value = _as_int(getattr(building, "warp_in_recharge", 0), 0)
    if value <= 0:
        unit_type = getattr(building, "type_name", None)
        if unit_type:
            try:
                from .definitions import rules

                cls = rules.unit_class(unit_type)
                if cls is not None:
                    value = _as_int(getattr(cls, "warp_in_recharge", 0), 0)
            except Exception:
                pass
    return value


def warp_in_field_name(building):
    """The build field the destination must carry ("" = no requirement)."""
    raw = _as_text(getattr(building, "warp_in_needs_field", None), "")
    if not raw or raw == "0":
        return ""
    return raw


def warp_in_field_radius(building):
    """Radius (in PRECISION units) of the field the building projects.

    ``warp_in_field_radius_m`` is expressed in meters, like
    ``build_field_radius_m``; the internal value uses the same PRECISION
    scale as the other range fields.
    """
    value = _as_int(getattr(building, "warp_in_field_radius_m", 0), 0)
    if value <= 0:
        unit_type = getattr(building, "type_name", None)
        if unit_type:
            try:
                from .definitions import rules

                cls = rules.unit_class(unit_type)
                if cls is not None:
                    value = _as_int(getattr(cls, "warp_in_field_radius_m", 0), 0)
            except Exception:
                value = 0
    return value


def warp_in_charges_left(building):
    """Charges currently available on the building."""
    max_charges = warp_in_charge_max(building)
    if max_charges <= 0:
        return 0
    used = int(getattr(building, "_warp_in_used", 0) or 0)
    return max(0, max_charges - used)


def warp_in_ready_time(building):
    """World time at which the building is charged again (``0`` = now)."""
    return int(getattr(building, "_warp_in_ready_time", 0) or 0)


def warp_in_is_ready(building):
    """True when the building may warp a unit in right now."""
    if warp_in_charges_left(building) <= 0:
        return False
    world = getattr(building, "world", None)
    now = int(getattr(world, "time", 0) or 0) if world is not None else 0
    return now >= warp_in_ready_time(building)


def warp_in_consume_charge(building):
    """Spend one charge and start the recharge timer."""
    max_charges = warp_in_charge_max(building)
    used = int(getattr(building, "_warp_in_used", 0) or 0)
    used += 1
    building._warp_in_used = used
    recharge = warp_in_recharge_time(building)
    world = getattr(building, "world", None)
    now = int(getattr(world, "time", 0) or 0) if world is not None else 0
    if recharge > 0:
        building._warp_in_ready_time = now + recharge
    elif used >= max_charges:
        # No recharge time: the building is usable again right away.
        building._warp_in_used = 0
        building._warp_in_ready_time = 0


def warp_in_recharge_tick(building):
    """Restore charges once the recharge timer has elapsed."""
    if warp_in_charge_max(building) <= 0:
        return
    world = getattr(building, "world", None)
    now = int(getattr(world, "time", 0) or 0) if world is not None else 0
    if now < warp_in_ready_time(building):
        return
    if int(getattr(building, "_warp_in_used", 0) or 0):
        building._warp_in_used = 0
    building._warp_in_ready_time = 0


def warp_in_destination_square(building, target):
    """Resolve the square a warp-in should land on.

    ``target`` may be a square, a unit, or a building.  Returns ``None``
    when the destination is not usable.
    """
    if target is None:
        return None
    if hasattr(target, "neighbors") and hasattr(target, "x"):
        return target
    place = getattr(target, "place", None)
    if place is not None and hasattr(place, "neighbors"):
        return place
    return None


def warp_in_field_ok(building, square, world=None):
    """Check that *square* carries the build field the building needs.

    Returns ``(ok, reason)``.
    """
    field = warp_in_field_name(building)
    if not field:
        return True, None
    if square is None:
        return False, "cannot_build_here"
    try:
        from .world_build_rules import (
            _square_for_build_target,
            has_build_field_on_square,
        )

        player = getattr(building, "player", None)
        real_square = _square_for_build_target(
            world or getattr(building, "world", None), square,
            getattr(square, "x", 0), getattr(square, "y", 0),
        )
        if real_square is None:
            return False, "cannot_build_here"
        if not has_build_field_on_square(world, real_square, player, field):
            return False, f"missing_build_field.{field}"
    except Exception:
        # Never hard-fail on an unexpected terrain API change.
        return True, None
    return True, None


def warp_in_in_field_radius(building, square):
    """True when *square* lies inside the field the building projects."""
    radius = warp_in_field_radius(building)
    if radius <= 0:
        return True
    place = getattr(building, "place", None)
    if place is None or square is None:
        return False
    origin = getattr(building, "x", 0), getattr(building, "y", 0)
    if getattr(place, "x", None) is None:
        return True
    try:
        from .lib.nofloat import square_of_distance

        # The radius is in PRECISION units (meters x 1000), the same scale
        # as the other range fields.
        return square_of_distance(
            building.x, building.y, square.x, square.y
        ) <= radius * radius
    except Exception:
        return True


def warp_in_unit_types(building):
    """The unit types that may be warped in, filtered to real unit classes."""
    from .definitions import rules

    result = []
    for name in warp_in_types(building):
        try:
            cls = rules.unit_class(name)
        except Exception:
            cls = None
        if cls is None:
            warning("warp_in_types: unknown unit type %s", name)
            continue
        result.append((name, cls))
    return result


def warp_in_place_unit(building, unit_cls, square):
    """Place one unit of *unit_cls* on *square*.

    Returns the new unit, or ``None`` when there was no room.
    """
    place = getattr(square, "place", None) or square
    x, y = getattr(square, "x", 0), getattr(square, "y", 0)
    if hasattr(place, "find_free_space"):
        found = place.find_free_space("ground", x, y)
        if found and found[0] is not None:
            x, y = found[0], found[1]
    try:
        unit = unit_cls(building.player, place, x, y)
    except Exception:
        warning("warp-in could not create %s", getattr(unit_cls, "__name__", unit_cls))
        return None
    try:
        unit.notify("added")
    except Exception:
        pass
    return unit


def warp_in_deploy_effect(building, square):
    """Deploy the configured warp-in effect at the destination."""
    effect_name = getattr(building, "warp_in_effect", None) or ""
    if isinstance(effect_name, (list, tuple)):
        effect_name = effect_name[0] if effect_name else ""
    effect_name = str(effect_name).strip()
    if not effect_name or effect_name == "0":
        return None
    try:
        from .definitions import rules

        effect_cls = rules.unit_class(effect_name)
        if effect_cls is None:
            return None
        from .worldunit import Effect

        if getattr(effect_cls, "cls", None) is not Effect:
            return None
        effect = Effect(
            building.player,
            getattr(square, "place", None) or square,
            getattr(square, "x", 0),
            getattr(square, "y", 0),
        )
        for attr in ("harm_level", "harm_target_type", "decay"):
            if hasattr(effect_cls, attr):
                setattr(effect, attr, getattr(effect_cls, attr))
        return effect
    except Exception:
        return None


def perform_warp_in(building, unit_type_name, square):
    """Warp one unit of *unit_type_name* onto *square*.

    Returns ``(ok, reason)``.  ``ok`` is False when the destination is not
    usable, the building is not charged, or there was no room.
    """
    if not is_warp_in_building(building):
        return False, "cannot_build_here"
    if not warp_in_is_ready(building):
        return False, "not_ready"
    square = warp_in_destination_square(building, square)
    if square is None:
        return False, "cannot_build_here"
    ok, reason = warp_in_field_ok(building, square)
    if not ok:
        return False, reason
    if not warp_in_in_field_radius(building, square):
        return False, "out_of_range"
    available = dict(warp_in_unit_types(building))
    unit_cls = available.get(str(unit_type_name))
    if unit_cls is None:
        return False, "cannot_build_here"
    unit = warp_in_place_unit(building, unit_cls, square)
    if unit is None:
        return False, "not_enough_space"
    warp_in_deploy_effect(building, square)
    warp_in_consume_charge(building)
    info("warp-in: %s at %s", unit_type_name, getattr(square, "x", 0))
    return True, None
