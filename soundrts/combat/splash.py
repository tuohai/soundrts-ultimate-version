import math
import os

from ..lib.nofloat import square_of_distance as _square_of_distance_fn

# 尝试加载 Cython 加速器；失败时回退到 Python 实现
_cf = None
if os.environ.get("SOUNDRTS_NO_CYTHON", "").strip() not in ("1", "true", "True"):
    try:
        from . import combat_fast as _cf  # type: ignore[import-not-found,no-redef]
    except ImportError:
        _cf = None


def _type_map_bonus(obj, vs_map):
    """Bonus from a *_vs map keyed by the object's type_name / is_a."""
    if not vs_map:
        return 0
    name = getattr(obj, "type_name", None)
    if name and name in vs_map:
        return vs_map[name]
    for t in getattr(obj, "expanded_is_a", None) or ():
        if t in vs_map:
            return vs_map[t]
    return 0


def _as_decay_min(raw):
    if isinstance(raw, list) and raw:
        return float(raw[0])
    return float(raw)


class SplashMixin:
    """
    处理溅射伤害相关的功能
    """

    def _splash_dist_factor(self, dist2, splash_range, decay_min_value):
        decay_min_value = _as_decay_min(decay_min_value)
        if _cf is not None:
            return _cf.calc_splash_factor(dist2, splash_range, decay_min_value)
        decay_range = 1.0 - decay_min_value
        return 1.0 - (math.sqrt(dist2) / splash_range * decay_range)

    def _explode_vs_bonus(self, obj):
        """exp_dgf_vs for the unit actually hit by splash (not the aim target)."""
        vs = getattr(self, "exp_dgf_vs", None)
        if not vs:
            return 0
        bonus = _type_map_bonus(obj, vs)
        if bonus:
            return bonus
        if hasattr(obj, "get_current_armor_name"):
            armor_name = obj.get_current_armor_name()
            if armor_name and armor_name in vs:
                return vs[armor_name]
        armor = getattr(obj, "_armor_instance", None)
        if armor is not None:
            expanded = getattr(armor, "expanded_is_a", None)
            if expanded:
                for armor_type in armor.expanded_is_a:
                    if armor_type in vs:
                        return vs[armor_type]
            elif hasattr(armor, "is_a"):
                for armor_type in armor.is_a:
                    if armor_type in vs:
                        return vs[armor_type]
        return 0

    def splash_aim(self, target, is_melee=False):
        """
        溅射：基础 mdg_splash / rdg_splash 仍随机分摊；
        mdg_splash_vs / mdg_splash_decay_min_vs 按被溅到的单位结算，不改整池。
        """
        if target.place is None or target.place.objects is None:
            return

        if is_melee:
            if hasattr(target, "type_name") and target.type_name in self.mdg_radius_vs:
                splash_range = self.mdg_radius_vs[target.type_name]
            elif hasattr(target, "expanded_is_a"):
                for t in target.expanded_is_a:
                    if t in self.mdg_radius_vs:
                        splash_range = self.mdg_radius_vs[t]
                        break
                else:
                    splash_range = self.mdg_radius
            else:
                splash_range = self.mdg_radius

            total_splash = self.mdg_splash
            splash_decay_min = self.mdg_splash_decay_min
            splash_vs = getattr(self, "mdg_splash_vs", None) or {}
            decay_min_vs = getattr(self, "mdg_splash_decay_min_vs", None) or {}
            exploding = bool(getattr(self, "mdg_explode", 0))
        else:
            if hasattr(target, "type_name") and target.type_name in self.rdg_radius_vs:
                splash_range = self.rdg_radius_vs[target.type_name]
            elif hasattr(target, "expanded_is_a"):
                for t in target.expanded_is_a:
                    if t in self.rdg_radius_vs:
                        splash_range = self.rdg_radius_vs[t]
                        break
                else:
                    splash_range = self.rdg_radius
            else:
                splash_range = self.rdg_radius

            total_splash = self.rdg_splash
            splash_decay_min = self.rdg_splash_decay_min
            splash_vs = getattr(self, "rdg_splash_vs", None) or {}
            decay_min_vs = getattr(self, "rdg_splash_decay_min_vs", None) or {}
            exploding = bool(getattr(self, "rdg_explode", 0))

        if exploding and hasattr(self, 'exp_dgf'):
            total_splash += self.exp_dgf

        if splash_range <= 0:
            return
        if total_splash <= 0 and not splash_vs and not (exploding and getattr(self, "exp_dgf_vs", None)):
            return

        radius2 = splash_range * splash_range

        if not hasattr(target.place, "objects") or target.place.objects is None:
            target.place.objects = []

        victims_with_factors = []
        from ..worldunit import Creature

        for obj in target.place.objects[:]:
            if obj is self or obj is target:
                continue
            if not self.is_an_enemy(obj) or not isinstance(obj, Creature):
                continue

            dist2 = _square_of_distance_fn(target.x, target.y, obj.x, obj.y)
            if dist2 > radius2:
                continue

            decay_min_value = splash_decay_min + _type_map_bonus(obj, decay_min_vs)
            dist_factor = self._splash_dist_factor(dist2, splash_range, decay_min_value)
            extra = _type_map_bonus(obj, splash_vs)
            if exploding:
                extra += self._explode_vs_bonus(obj)
            victims_with_factors.append((obj, dist_factor, extra))

        if not victims_with_factors:
            return

        n = len(victims_with_factors)
        rands = []
        for _, factor, _extra in victims_with_factors:
            rand_max = 0.5 + (factor * 0.5)  # 0.5 ~ 1.0
            rands.append(self.world.random.random() * rand_max)

        sumRand = sum(rands)

        if sumRand == 0:
            for (victim, factor, extra), _ in zip(victims_with_factors, rands):
                damage = int(round(total_splash * factor / n)) + int(round(extra * factor))
                if damage > 0:
                    victim.receive_hit(damage, self, notify=False)
                    victim.notify("splash_hit")
        else:
            distributedSum = 0
            last_i = n - 1
            for i, ((victim, factor, extra), rand) in enumerate(
                zip(victims_with_factors, rands)
            ):
                portion = int(round(rand / sumRand * total_splash * factor))
                extra_hit = int(round(extra * factor))
                distributedSum += portion
                damage = portion + extra_hit
                if damage > 0:
                    victim.receive_hit(damage, self, notify=(i == last_i))
                    victim.notify("splash_hit")

            leftover = total_splash - distributedSum
            if leftover > 0:
                closest_victim = max(victims_with_factors, key=lambda x: x[1])[0]
                closest_victim.receive_hit(leftover, self, notify=True)

    def _square_of_distance(self, x1, y1, x2, y2):
        """计算两点间距离的平方（委托给 nofloat 的 Cython 加速版本）"""
        return _square_of_distance_fn(x1, y1, x2, y2)
