from ..worldentity import Entity
from ..lib.nofloat import (
    PRECISION,
    int_angle,
    int_cos_1000,
    int_distance,
    int_sin_1000,
    square_of_distance,
    to_int,
)

# 速度和战斗属性在内部以 ×1000 存储
_SCALED_TRANSPORT_STATS = frozenset({
    'speed',
    'mdg', 'rdg', 'mdf', 'rdf', 'mdg_vs', 'rdg_vs', 'mdf_vs', 'rdf_vs',
    'mdg_delay', 'rdg_delay',
    'mdg_cd', 'rdg_cd', 'mdg_cd_vs', 'rdg_cd_vs',
    'mdg_ready', 'rdg_ready', 'mdg_ready_vs', 'rdg_ready_vs',
    'mdg_range', 'rdg_range', 'mdg_range_vs', 'rdg_range_vs',
    'mdg_minimal_range', 'rdg_minimal_range',
    'mdg_minimal_range_vs', 'rdg_minimal_range_vs',
    'mdg_splash', 'rdg_splash',
    'mdg_radius', 'rdg_radius',
})


def _normalize_bonus_dict(bonus):
    """将 key-value 属性加成配置规范化为 {stat: float}。"""
    if isinstance(bonus, dict):
        return {str(stat): float(value) for stat, value in bonus.items()}
    if isinstance(bonus, list):
        result = {}
        i = 0
        while i < len(bonus):
            if i + 1 < len(bonus):
                result[str(bonus[i])] = float(bonus[i + 1])
            i += 2
        return result
    return {}


def _bonus_amount(stat, value):
    if stat in _SCALED_TRANSPORT_STATS:
        return float(value) * 1000
    return float(value)


def _apply_transport_bonus(unit, bonus, stats_tracker):
    """对 unit 应用属性加成，并记录到 stats_tracker 以便卸载时回滚。"""
    for stat, value in _normalize_bonus_dict(bonus).items():
        if not hasattr(unit, stat):
            continue
        current_value = getattr(unit, stat)
        if not isinstance(current_value, (int, float)):
            continue
        bonus_value = _bonus_amount(stat, value)
        stats_tracker[stat] = stats_tracker.get(stat, 0) + bonus_value
        setattr(unit, stat, current_value + bonus_value)


def _remove_transport_bonus(unit, stats_tracker):
    """按 stats_tracker 回滚 unit 上的属性加成。"""
    for stat, total_bonus in list(stats_tracker.items()):
        current_value = getattr(unit, stat, 0)
        if isinstance(current_value, (int, float)):
            setattr(unit, stat, current_value - total_bonus)
    stats_tracker.clear()


class CreatureTransport(Entity):
    def have_enough_space(self, target):
        if self.inside:
            return self.inside.have_enough_space(target)

    def load(self, target):
        # 防止容器装载自己
        if target is self:
            return False

        # 检查目标玩家是否为同一玩家，如果不是则退出
        if target.player is not self.player:
            return False

        # 检查地形限制
        if not self._can_load_from_terrain(target, target.place):
            return False

        if self.inside and not self.inside.have_enough_space(target):
            return False

        # 记录原始位置
        original_place = target.place
        original_x = target.x
        original_y = target.y

        # 保存原始坐标到目标对象
        target.original_x = original_x
        target.original_y = original_y

        # 每装载一名单位，给容器本身加属性
        load_bonus = getattr(self, 'load_bonus', None)
        if load_bonus:
            if not hasattr(self, '_bonus_stats'):
                self._bonus_stats = {}
            _apply_transport_bonus(self, load_bonus, self._bonus_stats)

        # 进入容器后，给乘客加属性
        passenger_bonus = getattr(self, 'passenger_bonus', None)
        if passenger_bonus:
            if not hasattr(target, '_passenger_bonus_stats'):
                target._passenger_bonus_stats = {}
            _apply_transport_bonus(target, passenger_bonus, target._passenger_bonus_stats)

        # 取消所有命令并移动到运输单位内
        target.cancel_all_orders()
        target.notify("enter")
        target.move_to(self.inside, 0, 0)

        # 在原位置生成草地,但先检查是否已存在
        if not target.is_buildable_anywhere:
            # 检查该位置是否已有草地
            has_meadow = False
            for obj in original_place.objects:
                if (obj.is_a_building_land and
                        obj.x == original_x and
                        obj.y == original_y):
                    has_meadow = True
                    break

            # 只在没有草地时创建新的
            if not has_meadow:
                from ..worldresource import recreate_building_land

                consumed = getattr(target, "building_land", None)
                recreate_building_land(
                    original_place, original_x, original_y, consumed=consumed
                )
        return True

    def load_all(self, place=None):
        if place is None:
            place = self.place
        loaded = 0
        for u in sorted(
                self.player.units, key=lambda x: x.transport_volume, reverse=True
        ):
            if u is self:  # 防止容器装载自己
                continue
            if u.place is place and self.have_enough_space(u):
                # 检查地形限制
                if self._can_load_from_terrain(u, place):
                    if self.load(u):
                        loaded += 1
        return loaded

    def _can_load_from_terrain(self, target, place):
        """检查是否可以从指定地形载入目标单位"""
        # 空中载具不受地形限制
        if self.airground_type == "air":
            return True

        # 地面载具不能载入水面单位
        if self.airground_type == "ground" and target.airground_type == "water":
            return False

        # 水面载具不能载入陆地上的水面单位
        if (self.airground_type == "water" and target.airground_type == "water"
            and not getattr(place, 'is_water', False)):
            return False

        return True

    def unload_all(self, place=None):
        if place is None:
            place = self.place
            x = self.x
            y = self.y
        else:
            x = place.x
            y = place.y

        inside = getattr(self, "inside", None)
        if inside is None or not inside.objects:
            return 0

        # 移除容器自身的装载加成
        if getattr(self, 'load_bonus', None) and getattr(self, '_bonus_stats', None):
            _remove_transport_bonus(self, self._bonus_stats)

        # 检查是否有需要草地的建筑
        has_building_needs_meadow = False
        for obj in inside.objects:
            if not obj.is_buildable_anywhere:
                has_building_needs_meadow = True
                break

        meadows = []
        # 如果有需要草地的建筑，检查目标位置是否有草地
        if has_building_needs_meadow:
            for obj in place.objects:
                if obj.is_a_building_land:
                    meadows.append(obj)
            if not meadows:
                return 0

        unloaded = 0
        # 执行卸载
        for obj in inside.objects[:]:
            # 检查地形限制 - 地面单位不能卸载到水区域
            if (obj.airground_type == "ground" and getattr(place, 'is_water', False)):
                continue

            # 检查地形限制 - 水面单位不能卸载到陆地区域
            if (obj.airground_type == "water" and not getattr(place, 'is_water', False)):
                continue
            if not obj.is_buildable_anywhere:
                # 如果是建筑，选择一个可用的草地
                available_meadows = [m for m in meadows if m in place.objects]
                if not available_meadows:
                    continue
                meadow = available_meadows[0]  # 取第一个可用的草地
                obj_x = meadow.x
                obj_y = meadow.y
                meadow.delete()
            else:
                # 如果是普通单位，寻找空闲位置
                # 检查place是否有find_free_space_for方法，如果没有则使用find_free_space
                if hasattr(place, 'find_free_space_for'):
                    obj_x, obj_y = place.find_free_space_for(obj, x, y)
                else:
                    # 临时释放空间检查
                    obj.free_space()
                    obj_x, obj_y = place.find_free_space(obj.airground_type, x, y)
                    obj.occupy_space()

                if obj_x is None:
                    # 如果没有找到空闲位置，尝试在附近找一个位置
                    for dx in range(-1, 2):
                        for dy in range(-1, 2):
                            test_x = x + dx
                            test_y = y + dy
                            if place.contains(test_x, test_y):
                                if hasattr(place, 'find_free_space_for'):
                                    obj_x, obj_y = place.find_free_space_for(obj, test_x, test_y)
                                else:
                                    # 临时释放空间检查
                                    obj.free_space()
                                    obj_x, obj_y = place.find_free_space(obj.airground_type, test_x, test_y)
                                    obj.occupy_space()
                                if obj_x is not None:
                                    break
                        if obj_x is not None:
                            break

                    if obj_x is None:
                        # 如果还是找不到位置，跳过这个单位
                        continue

            # 移除乘客在容器内获得的属性加成
            passenger_stats = getattr(obj, '_passenger_bonus_stats', None)
            if passenger_stats:
                _remove_transport_bonus(obj, passenger_stats)

            # 移动对象到目标位置
            obj.move_to(place, obj_x, obj_y)
            obj.notify("exit")
            unloaded += 1
        return unloaded

    def contains_enemy(self, player):
        return False

    def nearest_water(self):
        places = [sq for sq in self.place.strict_neighbors if sq.is_water]
        if places:
            return min(
                places, key=lambda sq: square_of_distance(sq.x, sq.y, self.x, self.y)
            )

    def get_observed_squares(self, strict=False):
        """获取单位能观察到的方格列表

        Args:
            strict: 是否严格限制视野范围。当为True时，只返回完全可见的区域；
                   当为False时，返回完全和部分可见的区域。

        Returns:
            list: 可观察到的方格列表
        """
        if self.is_inside or self.place is None:
            return []
        result = [self.place]
        if strict and self.sight_range < self.world.square_width:
            return result
        for sq in self.place.neighbors:  # 改为neighbors以包含对角方向
            if (
                self.height > sq.height
                or self.height == sq.height
                and (
                    self._can_go(sq, ignore_forests=True)
                    or sq.is_water
                    or self.place.is_water
                )
            ):
                result.append(sq)
        return result

    def get_observed_squares_optimized(self):
        """获取单位能观察到的方格的优化版本

        同时计算严格和非严格模式的观察方格，避免重复计算

        Returns:
            dict: 包含两个键'strict'和'all'的字典，分别表示严格模式和非严格模式的观察方格集合
        """
        # 使用原始版本的简单逻辑
        strict_squares = set(self.get_observed_squares(strict=True))
        all_squares = set(self.get_observed_squares(strict=False))

        return {'strict': strict_squares, 'all': all_squares}
