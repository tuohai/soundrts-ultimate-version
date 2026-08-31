"""Projectile bounce to nearby enemies (rules-driven).

StarCraft Mutalisk-style: after the primary hit, the shot hops to the
nearest other enemy within bounce range, then again, with damage decaying
each hop.

Rules (``int_properties`` / ``precision_properties``)::

    rdg_bounce 2              ; extra hops after the primary (0 = off)
    mdg_bounce 2              ; melee / melee-projectile variant
    rdg_bounce_range 3        ; max hop distance in tiles (PRECISION);
                              ; 0 = use rdg_range / mdg_range
    mdg_bounce_range 3
    rdg_bounce_decay 33       ; percent of previous hop remaining (round-nearest);
                              ; 0 with bounce > 0 defaults to 33 (9→3→1)
    mdg_bounce_decay 33

Bounce only runs if the primary hit. Allies are not hit. A unit is never
hit twice by the same bounce chain. Target filters follow ``rdg_targets`` /
``mdg_targets`` (air / ground etc.).
"""

from __future__ import annotations

from ..lib.nofloat import square_of_distance


DEFAULT_BOUNCE_DECAY = 33


def scale_bounce_damage(base, decay_pct, hops):
    """Apply *decay_pct* (0–100 remaining) *hops* times, round-to-nearest.

    9 damage with decay 33 and 1 hop → 3; a second hop → 1 (Mutalisk).
    """
    dmg = int(base or 0)
    pct = int(decay_pct or 0)
    for _ in range(int(hops or 0)):
        dmg = (dmg * pct + 50) // 100
    return dmg


def _bounce_places(origin, extra=None):
    places = []
    place = getattr(origin, "place", None)
    if place is not None:
        places.append(place)
        for n in getattr(place, "neighbors", ()) or ():
            if n is not None and n not in places:
                places.append(n)
    if extra is not None and extra not in places:
        places.append(extra)
        for n in getattr(extra, "neighbors", ()) or ():
            if n is not None and n not in places:
                places.append(n)
    return places


class BounceMixin:
    """Hop extra hits to nearby enemies after a successful primary hit."""

    def apply_projectile_bounce(self, primary_target, is_melee=False):
        """Damage nearest unused enemies in a chain from *primary_target*."""
        if primary_target is None:
            return
        if is_melee:
            extra = int(getattr(self, "mdg_bounce", 0) or 0)
            hop_range = int(getattr(self, "mdg_bounce_range", 0) or 0)
            decay = int(getattr(self, "mdg_bounce_decay", 0) or 0)
            targets_filter = getattr(self, "mdg_targets", None) or ["ground"]
            get_damage = getattr(self, "_get_melee_damage_vs", None)
        else:
            extra = int(getattr(self, "rdg_bounce", 0) or 0)
            hop_range = int(getattr(self, "rdg_bounce_range", 0) or 0)
            decay = int(getattr(self, "rdg_bounce_decay", 0) or 0)
            targets_filter = getattr(self, "rdg_targets", None) or ["ground"]
            get_damage = getattr(self, "_get_ranged_damage_vs", None)
        if extra <= 0 or get_damage is None:
            return
        if hop_range <= 0:
            hop_range = int(
                getattr(self, "mdg_range" if is_melee else "rdg_range", 0) or 0
            )
        if hop_range <= 0:
            return
        if decay <= 0:
            decay = DEFAULT_BOUNCE_DECAY

        from ..worldunit import Creature
        from ..worldunit.world_public_method import (
            ground_or_air,
            matches_attack_targets,
        )

        range2 = hop_range * hop_range
        hit = {primary_target}
        current = primary_target
        origin_place = getattr(self, "place", None)

        for hop in range(1, extra + 1):
            cx = getattr(current, "x", None)
            cy = getattr(current, "y", None)
            if cx is None or cy is None:
                return
            places = _bounce_places(current, extra=origin_place)
            best = None
            best_d2 = None
            best_id = None
            for pl in places:
                for obj in list(getattr(pl, "objects", None) or ()):
                    if obj is self or obj in hit:
                        continue
                    if not isinstance(obj, Creature):
                        continue
                    if getattr(obj, "hp", 0) <= 0:
                        continue
                    if not self.is_an_enemy(obj):
                        continue
                    ag = ground_or_air(
                        getattr(obj, "airground_type", "ground")
                    )
                    if not matches_attack_targets(obj, targets_filter, ag):
                        continue
                    d2 = square_of_distance(cx, cy, obj.x, obj.y)
                    if d2 > range2:
                        continue
                    oid = getattr(obj, "id", 0) or 0
                    if (
                        best is None
                        or d2 < best_d2
                        or (d2 == best_d2 and oid < best_id)
                    ):
                        best = obj
                        best_d2 = d2
                        best_id = oid
            if best is None:
                return
            base = get_damage(best)
            hit_damage = scale_bounce_damage(base, decay, hop)
            if hit_damage <= 0:
                return
            best.receive_hit(hit_damage, self, notify=True, is_melee=is_melee)
            hit.add(best)
            current = best
