"""Projectile pierce-through along the shot line (rules-driven).

AoE2 scorpion-style: a projectile can damage additional enemies whose
positions lie near the segment from the shooter to the aim point.

Rules (``int_properties`` / ``precision_properties``)::

    rdg_pierce_line 1          ; enable for ranged (0/1)
    mdg_pierce_line 1          ; enable for melee projectiles (0/1)
    rdg_pierce_width 0.5       ; half-width in tiles (PRECISION); default 0.5
    mdg_pierce_width 0.5
    rdg_pierce_max 0           ; max extra hits (0 = unlimited)
    mdg_pierce_max 0
    rdg_pierce_decay 50        ; extra-hit damage percent after armor (0 = 100)
    mdg_pierce_decay 50
"""

from __future__ import annotations

from ..lib.nofloat import PRECISION, square_of_distance


def _point_segment_dist2(px, py, ax, ay, bx, by):
    """Squared distance from point P to segment AB (integer PRECISION coords)."""
    abx = bx - ax
    aby = by - ay
    apx = px - ax
    apy = py - ay
    ab2 = abx * abx + aby * aby
    if ab2 <= 0:
        return apx * apx + apy * apy
    # t in [0, 1] as fraction; use integer math with PRECISION scale
    t_num = apx * abx + apy * aby
    if t_num <= 0:
        return apx * apx + apy * apy
    if t_num >= ab2:
        bpx = px - bx
        bpy = py - by
        return bpx * bpx + bpy * bpy
    # closest = A + (t_num/ab2) * AB
    # dist2 = |AP|^2 - (t_num^2 / ab2)
    ap2 = apx * apx + apy * apy
    return ap2 - (t_num * t_num) // ab2


class PierceLineMixin:
    """Apply bonus hits along a projectile path."""

    def apply_projectile_pierce_line(
        self, aim_x, aim_y, primary_target, is_melee=False, damage=None
    ):
        """Damage enemies near the shot segment (excluding *primary_target*)."""
        if is_melee:
            enabled = int(getattr(self, "mdg_pierce_line", 0) or 0)
            width = int(getattr(self, "mdg_pierce_width", 0) or 0)
            max_extra = int(getattr(self, "mdg_pierce_max", 0) or 0)
            decay = int(getattr(self, "mdg_pierce_decay", 0) or 0)
        else:
            enabled = int(getattr(self, "rdg_pierce_line", 0) or 0)
            width = int(getattr(self, "rdg_pierce_width", 0) or 0)
            max_extra = int(getattr(self, "rdg_pierce_max", 0) or 0)
            decay = int(getattr(self, "rdg_pierce_decay", 0) or 0)
        if not enabled:
            return

        if width <= 0:
            width = PRECISION // 2  # 0.5 tile
        width2 = width * width

        ax, ay = self.x, self.y
        bx, by = aim_x, aim_y

        from ..worldunit import Creature

        places = []
        place = getattr(self, "place", None)
        if place is not None:
            places.append(place)
            for n in getattr(place, "neighbors", ()) or ():
                if n is not None and n not in places:
                    places.append(n)
        tplace = getattr(primary_target, "place", None)
        if tplace is not None and tplace not in places:
            places.append(tplace)
            for n in getattr(tplace, "neighbors", ()) or ():
                if n is not None and n not in places:
                    places.append(n)

        candidates = []
        for pl in places:
            for obj in list(getattr(pl, "objects", None) or ()):
                if obj is self or obj is primary_target:
                    continue
                if not isinstance(obj, Creature):
                    continue
                if getattr(obj, "hp", 0) <= 0:
                    continue
                if not self.is_an_enemy(obj):
                    continue
                dist2 = _point_segment_dist2(obj.x, obj.y, ax, ay, bx, by)
                if dist2 <= width2:
                    along = square_of_distance(ax, ay, obj.x, obj.y)
                    candidates.append((along, obj))

        if not candidates:
            return

        candidates.sort(key=lambda t: t[0])
        if max_extra > 0:
            candidates = candidates[:max_extra]

        for _, victim in candidates:
            if is_melee:
                hit_damage = (
                    damage
                    if damage is not None
                    else self._get_melee_damage_vs(victim)
                )
            else:
                hit_damage = (
                    damage
                    if damage is not None
                    else self._get_ranged_damage_vs(victim)
                )
            if not hit_damage and hit_damage != 0:
                continue
            # receive_hit applies armor first; hit_scale is AoE2 stray (50% extras).
            scale = decay if 0 < decay < 100 else 100
            victim.receive_hit(
                hit_damage,
                self,
                notify=True,
                is_melee=is_melee,
                hit_scale=scale,
            )
