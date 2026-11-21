"""Burning structures (StarCraft) — low-HP buildings catch fire.

In StarCraft 1 and 2 a building whose hit points drop below a threshold
starts burning: it loses hit points over time and finally explodes.
This is a real gameplay mechanic, not just a visual: a building under
attack can be finished off before the attacker is killed.

The rules side is fully data-driven (the engine hardcodes no unit name):

``burn_hp_threshold_pct``
    The building starts burning when its HP falls below this percentage
    of its maximum (default 33, matching StarCraft's "one third").
``burn_damage``
    HP lost per burn tick, on the same scale as ``hp_max``.
``burn_interval``
    Milliseconds between two burn ticks (default 1000, i.e. one second).

The burn starts once (the threshold is crossed) and never stops on its
own; the building dies when its HP reaches zero.
"""

from .lib.log import info


def _first(value, default=0):
    """Take the first item of a list-like rules value (or the value)."""
    if isinstance(value, (list, tuple)):
        return value[0] if value else default
    return value


def burn_threshold_pct(building):
    """The HP percentage below which the building starts burning."""
    value = _first(getattr(building, "burn_hp_threshold_pct", None), 33)
    try:
        value = int(float(value))
    except (TypeError, ValueError):
        return 33
    if value <= 0:
        return 33
    if value > 100:
        return 100
    return value


def burn_damage(building):
    """HP lost per burn tick (0 = the building does not burn).

    ``burn_damage`` is a PRECISION property, so it is on the same scale
    as ``hp_max``.
    """
    value = _first(getattr(building, "burn_damage", None), 0)
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def burn_interval(building):
    """Milliseconds between two burn ticks.

    ``burn_interval`` is a PRECISION property (like ``hp_regen_cd``), so
    the rules value is already scaled to milliseconds.  The default is
    one second.
    """
    from .lib.nofloat import PRECISION

    value = _first(getattr(building, "burn_interval", None), 0)
    try:
        value = int(float(value))
    except (TypeError, ValueError):
        return PRECISION
    if value <= 0:
        return PRECISION
    return value


def can_burn(building):
    """True when the building is allowed to burn at all."""
    if not getattr(building, "is_a_building", False):
        return False
    return burn_damage(building) > 0


def is_burning(building):
    """True when the building has caught fire."""
    return bool(getattr(building, "_is_burning", False))


def should_start_burning(building):
    """True when the building just crossed the burn threshold."""
    if not can_burn(building):
        return False
    if is_burning(building):
        return False
    hp_max = int(getattr(building, "hp_max", 0) or 0)
    hp = int(getattr(building, "hp", 0) or 0)
    if hp_max <= 0 or hp <= 0:
        return False
    return hp * 100 <= hp_max * burn_threshold_pct(building)


def start_burning(building):
    """Set the building on fire."""
    if is_burning(building):
        return False
    building._is_burning = True
    building._burn_next_time = 0
    try:
        building.notify("burning")
    except Exception:
        pass
    info("building burning: %s", getattr(building, "type_name", building))
    return True


def burn_tick(building, current_time):
    """Apply one burn tick to the building.

    Returns True when the building was damaged by the fire.
    """
    if not is_burning(building):
        return False
    damage = burn_damage(building)
    if damage <= 0:
        return False
    next_time = int(getattr(building, "_burn_next_time", 0) or 0)
    if current_time < next_time:
        return False
    hp = int(getattr(building, "hp", 0) or 0)
    if hp <= 0:
        return False
    building.hp = max(0, hp - damage)
    building._burn_next_time = current_time + burn_interval(building)
    try:
        building.notify("hp_update")
    except Exception:
        pass
    if building.hp <= 0:
        try:
            building.die(None)
        except Exception:
            pass
    return True


def update_burning(building, current_time):
    """Start the fire if needed, then apply the burn tick."""
    if should_start_burning(building):
        start_burning(building)
    return burn_tick(building, current_time)
