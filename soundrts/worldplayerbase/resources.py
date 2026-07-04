"""玩家资源和单位管理模块"""

from ..definitions import rules, MAX_NB_OF_RESOURCE_TYPES
from ..lib.nofloat import PRECISION
from ..lib.log import warning


class ResourcesManager:
    """资源和单位管理器"""
    
    def __init__(self, player):
        self.player = player

    def free_project_resources_if_no_worker_on_project(self):
        for project in self.player.budget:
            if self._no_worker_on_project(project):
                self.player.free_resources(project)

    def _no_worker_on_project(self, project):
        for u in self.player.units:
            if u.must_build(project):
                return False
        return True


class ResourcesMixin:
    """资源管理相关的方法混入类"""

    def _update_storage_bonus(self):
        self.storage_bonus = [0] * MAX_NB_OF_RESOURCE_TYPES
        for u in self.units:
            for res, bonus in enumerate(u.storage_bonus):
                self.storage_bonus[res] = max(self.storage_bonus[res], bonus)

    def _update_allied_upgrades(self):
        for p in self.allied:
            for upgrade_name in p.upgrades:
                while self.level(upgrade_name) < p.level(upgrade_name):
                    rules.unit_class(upgrade_name).upgrade_player(self)

    def _update_menace(self):
        from ..worldunit import Soldier
        self._menace = sum(
            u.menace for u in self.units if u.speed > 0 and isinstance(u, Soldier)
        )

    def _update_actual_speed(self):
        from ..worldaction import AttackAction
        from .base import VERY_SLOW
        from ..lib.nofloat import to_int
        
        for u in self.units:
            try:
                # 获取基础速度
                base_speed = u.speed

                # 如果单位正在攻击目标，检查是否有速度修正
                if isinstance(u.action, AttackAction) and u.action.target:
                    base_speed = u._get_speed_vs(u.action.target)

                # 应用地形修正
                if u.place.type_name in u.speed_on_terrain:
                    u.actual_speed = to_int(
                        u.speed_on_terrain[
                            u.speed_on_terrain.index(u.place.type_name) + 1
                        ]
                    )
                elif u.airground_type == "water":
                    u.actual_speed = base_speed
                else:
                    u.actual_speed = (
                        base_speed
                        * u.place.terrain_speed[
                            0 if u.airground_type == "ground" else 1
                        ]
                        // 100
                    )
                if base_speed:
                    u.actual_speed = max(u.actual_speed, VERY_SLOW)  # never stuck
            except:
                u.actual_speed = base_speed

            # 更新编组速度
            for g in list(self.groups.values()):
                if g:
                    actual_speed = min(u.actual_speed for u in g)
                    for u in g:
                        u.actual_speed = actual_speed

    def _update_drowning(self):
        for u in self.units[:]:
            if getattr(u, "is_a_building", False):
                continue
            if (
                u.is_vulnerable
                and u.airground_type == "ground"
                and not getattr(u.place, "is_ground", True)
            ):
                u.die()

    def pay(self, cost):
        for i, c in enumerate(cost):
            self.resources[i] -= c

    def unpay(self, cost):
        self.pay([-c for c in cost])

    def _reserve_resources(self, project):
        self.pay(project.cost)
        self.budget.append(project)

    def resources_are_reserved(self, project):
        return project in self.budget

    def reserve_resources_if_needed(self, project):
        if not self.resources_are_reserved(project):
            self._reserve_resources(project)

    def free_resources(self, project):
        if project in self.budget:
            self.unpay(project.cost)
            self.budget.remove(project)

    def store(self, resource_type, qty):
        """将资源添加到玩家库存
        
        resource_type: 可以是字符串形式(如"resource1")或整数形式(如0)
        qty: 资源数量，内部单位(已乘以1000)
        """
        # 检查参数有效性
        if resource_type is None or qty is None:
            return
            
        # 解析资源类型
        resource_index = rules.parse_resource_type(resource_type)
        if resource_index is None:
            resource_index = 0  # 默认为resource1 (金子)
            
        # 应用存储加成并更新资源
        storage_bonus = self.storage_bonus[resource_index]
        
        # 添加到玩家资源
        self.resources[resource_index] += qty + storage_bonus
        # 更新统计信息 - 保持内部单位一致性
        self.stats.add("gathered", resource_index, qty + storage_bonus)

    def consumed_resources(self):
        return [
            self.gathered_resources[i] - self.resources[i]
            for i, c in enumerate(self.resources)
        ]

    def update_resources(self):
        """更新资源相关状态"""
        self._update_storage_bonus()
        self._update_allied_upgrades()
        self._update_actual_speed()
        self._update_menace()
        self._update_drowning()

    def _update_counterattacks(self):
        nearby_attacker_places = {}
        for attacker_place in self._counterattack_places:
            for neighbor in attacker_place.neighbors:
                if neighbor not in self._counterattack_places:
                    nearby_attacker_places[neighbor] = attacker_place
        self._counterattack_places = []
        for unit in self.units:
            if unit.place in nearby_attacker_places:
                unit.counterattack(nearby_attacker_places[unit.place])

    def on_unit_attacked(self, unit, attacker):
        if attacker in self.perception and attacker.place not in self._counterattack_places:
            self._counterattack_places.append(attacker.place)

    def send_alert(self, square, sound):
        self.push("alert", square.id, sound)