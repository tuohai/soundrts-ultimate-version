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


class SplashMixin:
    """
    处理溅射伤害相关的功能
    """
    def splash_aim(self, target, is_melee=False):
        """
        改进的溅射伤害计算:
        1. 根据距离计算衰减
        2. 随机分配伤害
        3. 添加溅射效果通知
        4. 支持目标已死亡的情况
        """
        if target.place is None or target.place.objects is None:
            return

        # 获取溅射属性
        if is_melee:
            # 检查是否有针对目标类型的近战溅射半径修正
            if hasattr(target, "type_name") and target.type_name in self.mdg_radius_vs:
                splash_range = self.mdg_radius_vs[target.type_name]
            elif hasattr(target, 'expanded_is_a'):
                # 检查继承类型
                for t in target.expanded_is_a:
                    if t in self.mdg_radius_vs:
                        splash_range = self.mdg_radius_vs[t]
                        break
                else:
                    splash_range = self.mdg_radius
            else:
                splash_range = self.mdg_radius

            # 检查是否有针对目标类型的近战溅射伤害修正
            if hasattr(target, "type_name") and target.type_name in self.mdg_splash_vs:
                total_splash = self.mdg_splash + self.mdg_splash_vs[target.type_name]
            elif hasattr(target, 'expanded_is_a'):
                # 检查继承类型
                for t in target.expanded_is_a:
                    if t in self.mdg_splash_vs:
                        total_splash = self.mdg_splash + self.mdg_splash_vs[t]
                        break
                else:
                    total_splash = self.mdg_splash
            else:
                total_splash = self.mdg_splash

            # 检查是否有针对目标类型的近战溅射衰减修正
            # 初始化为基础衰减值
            splash_decay_min = self.mdg_splash_decay_min
            if hasattr(target, "type_name") and target.type_name in self.mdg_splash_decay_min_vs:
                # 修改：添加特定单位的溅射衰减值，而不是替换
                splash_decay_min += self.mdg_splash_decay_min_vs[target.type_name]
            elif hasattr(target, 'expanded_is_a'):
                # 检查继承类型
                for t in target.expanded_is_a:
                    if t in self.mdg_splash_decay_min_vs:
                        # 修改：添加特定单位的溅射衰减值，而不是替换
                        splash_decay_min += self.mdg_splash_decay_min_vs[t]
                        break

            # 检查是否有自爆单位，如果是自爆单位，加入额外爆炸伤害系数
            if hasattr(self, 'mdg_explode') and self.mdg_explode:
                # 加入基础爆炸伤害系数
                if hasattr(self, 'exp_dgf'):
                    total_splash += self.exp_dgf

                # 检查是否有针对目标类型的额外爆炸伤害系数
                if hasattr(self, 'exp_dgf_vs') and hasattr(target, 'type_name') and target.type_name in self.exp_dgf_vs:
                    total_splash += self.exp_dgf_vs[target.type_name]
                elif hasattr(self, 'exp_dgf_vs') and hasattr(target, 'expanded_is_a'):
                    # 检查继承类型
                    for t in target.expanded_is_a:
                        if t in self.exp_dgf_vs:
                            total_splash += self.exp_dgf_vs[t]
                            break
                # 检查对目标护甲类型的vs
                elif hasattr(self, 'exp_dgf_vs') and hasattr(target, 'get_current_armor_name'):
                    armor_name = target.get_current_armor_name()
                    if armor_name and armor_name in self.exp_dgf_vs:
                        total_splash += self.exp_dgf_vs[armor_name]
                # 检查对目标护甲继承类型的vs
                elif hasattr(self, 'exp_dgf_vs') and hasattr(target, '_armor_instance') and target._armor_instance:
                    armor = target._armor_instance
                    if hasattr(armor, 'expanded_is_a'):
                        for armor_type in armor.expanded_is_a:
                            if armor_type in self.exp_dgf_vs:
                                total_splash += self.exp_dgf_vs[armor_type]
                                break
                    # 也检查护甲的直接is_a
                    elif hasattr(armor, 'is_a'):
                        for armor_type in armor.is_a:
                            if armor_type in self.exp_dgf_vs:
                                total_splash += self.exp_dgf_vs[armor_type]
                                break
        else:
            # 检查是否有针对目标类型的远程溅射半径修正
            if hasattr(target, "type_name") and target.type_name in self.rdg_radius_vs:
                splash_range = self.rdg_radius_vs[target.type_name]
            elif hasattr(target, 'expanded_is_a'):
                # 检查继承类型
                for t in target.expanded_is_a:
                    if t in self.rdg_radius_vs:
                        splash_range = self.rdg_radius_vs[t]
                        break
                else:
                    splash_range = self.rdg_radius
            else:
                splash_range = self.rdg_radius

            # 检查是否有针对目标类型的远程溅射伤害修正
            if hasattr(target, "type_name") and target.type_name in self.rdg_splash_vs:
                total_splash = self.rdg_splash + self.rdg_splash_vs[target.type_name]
            elif hasattr(target, 'expanded_is_a'):
                # 检查继承类型
                for t in target.expanded_is_a:
                    if t in self.rdg_splash_vs:
                        total_splash = self.rdg_splash + self.rdg_splash_vs[t]
                        break
                else:
                    total_splash = self.rdg_splash
            else:
                total_splash = self.rdg_splash

            # 检查是否有针对目标类型的远程溅射衰减修正
            # 初始化为基础衰减值
            splash_decay_min = self.rdg_splash_decay_min
            if hasattr(target, "type_name") and target.type_name in self.rdg_splash_decay_min_vs:
                # 修改：添加特定单位的溅射衰减值，而不是替换
                splash_decay_min += self.rdg_splash_decay_min_vs[target.type_name]
            elif hasattr(target, 'expanded_is_a'):
                # 检查继承类型
                for t in target.expanded_is_a:
                    if t in self.rdg_splash_decay_min_vs:
                        # 修改：添加特定单位的溅射衰减值，而不是替换
                        splash_decay_min += self.rdg_splash_decay_min_vs[t]
                        break

            # 检查是否有自爆单位，如果是自爆单位，加入额外爆炸伤害系数
            if hasattr(self, 'rdg_explode') and self.rdg_explode:
                # 加入基础爆炸伤害系数
                if hasattr(self, 'exp_dgf'):
                    total_splash += self.exp_dgf

                # 检查是否有针对目标类型的额外爆炸伤害系数
                if hasattr(self, 'exp_dgf_vs') and hasattr(target, 'type_name') and target.type_name in self.exp_dgf_vs:
                    total_splash += self.exp_dgf_vs[target.type_name]
                elif hasattr(self, 'exp_dgf_vs') and hasattr(target, 'expanded_is_a'):
                    # 检查继承类型
                    for t in target.expanded_is_a:
                        if t in self.exp_dgf_vs:
                            total_splash += self.exp_dgf_vs[t]
                            break
                # 检查对目标护甲类型的vs
                elif hasattr(self, 'exp_dgf_vs') and hasattr(target, 'get_current_armor_name'):
                    armor_name = target.get_current_armor_name()
                    if armor_name and armor_name in self.exp_dgf_vs:
                        total_splash += self.exp_dgf_vs[armor_name]
                # 检查对目标护甲继承类型的vs
                elif hasattr(self, 'exp_dgf_vs') and hasattr(target, '_armor_instance') and target._armor_instance:
                    armor = target._armor_instance
                    if hasattr(armor, 'expanded_is_a'):
                        for armor_type in armor.expanded_is_a:
                            if armor_type in self.exp_dgf_vs:
                                total_splash += self.exp_dgf_vs[armor_type]
                                break
                    # 也检查护甲的直接is_a
                    elif hasattr(armor, 'is_a'):
                        for armor_type in armor.is_a:
                            if armor_type in self.exp_dgf_vs:
                                total_splash += self.exp_dgf_vs[armor_type]
                                break

        if splash_range <= 0 or total_splash <= 0:
            return

        radius2 = splash_range * splash_range

        # 防御性检查：确保 Square 对象有 objects 属性
        if not hasattr(target.place, 'objects') or target.place.objects is None:
            target.place.objects = []

        # 收集范围内目标并计算距离系数
        victims_with_factors = []
        for obj in target.place.objects[:]:
            if obj is self or obj is target:
                continue
            from ..worldunit import Creature
            if not self.is_an_enemy(obj) or not isinstance(obj, Creature):
                continue

            # 修改：使用target为中心计算距离，而不是以攻击者self为中心
            dist2 = _square_of_distance_fn(target.x, target.y, obj.x, obj.y)
            if dist2 <= radius2:
                # 使用对应类型的衰减系数
                # 确保splash_decay_min是浮点数
                decay_min_value = splash_decay_min
                if isinstance(decay_min_value, list) and decay_min_value:
                    # 如果是列表，使用第一个元素
                    decay_min_value = float(decay_min_value[0])
                else:
                    # 确保是浮点数
                    decay_min_value = float(decay_min_value)
                # 距离衰减因子：Cython 路径用 combat_fast.calc_splash_factor，否则纯 Python
                if _cf is not None:
                    dist_factor = _cf.calc_splash_factor(dist2, splash_range, decay_min_value)
                else:
                    decay_range = 1.0 - decay_min_value
                    dist_factor = 1.0 - (math.sqrt(dist2) / splash_range * decay_range)
                victims_with_factors.append((obj, dist_factor))

        if not victims_with_factors:
            return

        # 生成随机权重，但考虑距离因素
        n = len(victims_with_factors)
        rands = []
        for _, factor in victims_with_factors:
            # 距离越近，随机范围越大
            rand_max = 0.5 + (factor * 0.5)  # 0.5 ~ 1.0
            rands.append(self.world.random.random() * rand_max)

        sumRand = sum(rands)

        if sumRand == 0:
            # 平均分配，但考虑距离衰减
            for (victim, factor), _ in zip(victims_with_factors, rands):
                damage = int(round(total_splash * factor / n))
                if damage > 0:
                    victim.receive_hit(damage, self, notify=False)
                    victim.notify("splash_hit")
        else:
            # 随机分配，但受距离影响
            distributedSum = 0
            for (victim, factor), rand in zip(victims_with_factors, rands):
                portion = int(round(rand / sumRand * total_splash * factor))
                distributedSum += portion
                if portion > 0:
                    victim.receive_hit(portion, self, notify=False)
                    victim.notify("splash_hit")

            # 处理剩余伤害
            leftover = total_splash - distributedSum
            if leftover > 0:
                # 优先补给最近的目标
                closest_victim = max(victims_with_factors, key=lambda x: x[1])[0]
                closest_victim.receive_hit(leftover, self, notify=True)
                
    def _square_of_distance(self, x1, y1, x2, y2):
        """计算两点间距离的平方（委托给 nofloat 的 Cython 加速版本）"""
        return _square_of_distance_fn(x1, y1, x2, y2)
