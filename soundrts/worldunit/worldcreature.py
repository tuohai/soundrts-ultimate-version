from .world_attributes import CreatureAttributes
from .world_movement import CreatureMovement
from ..combat import  CreatureAttack
from .world_status_update import CreatureStatusUpdate
from .world_ai_decision import CreatureAIDecision
from .world_order import CreatureOrders
# D-Phase 2 PR1: CreatureProductionAndBuilding 已合并到 Creature 类体 (见下方 be_built);
# 旧的 mixin 文件 world_production_and_building.py 保留为兼容 stub.
from .world_transport import CreatureTransport
import math
import random
import re
from typing import List, Optional, Set, Tuple

from ..definitions import MAX_NB_OF_RESOURCE_TYPES, VIRTUAL_TIME_INTERVAL, rules
from ..level_up_stats import LEVEL_UP_STAT_ATTRS
from ..lib.log import warning, debug
from ..lib.nofloat import (
    PRECISION,
    int_angle,
    int_cos_1000,
    int_distance,
    int_sin_1000,
    square_of_distance,
    to_int,
)
from ..worldaction import Action, AttackAction, MoveAction, MoveXYAction
from ..worldentity import Entity
from ..worldorders import (
    ORDERS_DICT,
    BuildPhaseTwoOrder,
    GoOrder,
    RallyingPointOrder,
    UpgradeToOrder,
    ProducingOrder,
    StartProduceOrder,
)
from ..worldresource import Corpse, Deposit
from ..worldroom import Square, Inside, ZoomTarget

# 单位可用的 AI 模式（开局默认模式必须是其中之一）。
# 与 world_ai_decision.immediate_order_toggle_ai_mode 的循环列表保持一致。
VALID_AI_MODES = ("offensive", "defensive", "guard", "chase")

_allied_control_controller_for_fn = None


def _allied_control_controller_for(unit):
    global _allied_control_controller_for_fn
    if _allied_control_controller_for_fn is None:
        from ..worldplayerbase.allied_control import allied_control_controller_for
        _allied_control_controller_for_fn = allied_control_controller_for
    return _allied_control_controller_for_fn(unit)


class Creature(CreatureAttributes, CreatureMovement, CreatureAttack, CreatureStatusUpdate,
               CreatureAIDecision, CreatureOrders, CreatureTransport):
    # 新版字段
    # 新增的近战/远程伤害与修正
    mdg_vs: dict = dict()  # 近战伤害 vs 某些单位
    rdg_vs: dict = dict()  # 远程伤害 vs 某些单位
    menace_vs: dict = dict()  # 对观察者类型的绝对威胁（选敌用）
    menace_mult_vs: dict = dict()  # 对观察者类型的威胁权重（当前伤害 × 权重）
    charge_mdg_vs: dict = dict()
    charge_rdg_vs: dict = dict()
    # 新增反冲锋相关属性
    op_charge_mdg: int = 0  # 近战反冲锋倍率
    op_charge_rdg: int = 0  # 远程反冲锋倍率
    op_charge_mdg_vs: dict = dict()  # 对特定单位的近战反冲锋倍率
    op_charge_rdg_vs: dict = dict()  # 对特定单位的远程反冲锋倍率
    op_charge_mdg_cd: int = 0  # 近战反冲锋冷却时间
    op_charge_rdg_cd: int = 0  # 远程反冲锋冷却时间
    op_charge_mdg_dist: int = 0  # 近战反冲锋有效距离
    op_charge_rdg_dist: int = 0  # 远程反冲锋有效距离
    op_charge_mdg_next_time: int = 0  # 下一次可用近战反冲锋时间
    op_charge_rdg_next_time: int = 0  # 下一次可用远程反冲锋时间
    op_charge_mdg_ready: bool = True  # 近战反冲锋就绪状态
    op_charge_rdg_ready: bool = True  # 远程反冲锋就绪状态
    last_op_charge_mdg_target_id = None  # 上次近战反冲锋的目标ID
    last_op_charge_rdg_target_id = None  # 上次远程反冲锋的目标ID
    # 新增暴击类修正
    mdg_crit_vs: dict = dict()  # 对特定单位的近战暴击倍率
    rdg_crit_vs: dict = dict()  # 对特定单位的远程暴击倍率
    mdg_crit_rate_vs: dict = dict()  # 对特定单位的近战暴击几率
    rdg_crit_rate_vs: dict = dict()  # 对特定单位的远程暴击几率
    mdg_piercing_vs: dict = dict()  # 对特定单位的近战穿甲
    rdg_piercing_vs: dict = dict()  # 对特定单位的远程穿甲
    mdg_piercing_rate_vs: dict = dict()  # 对特定单位的近战穿甲几率
    rdg_piercing_rate_vs: dict = dict()  # 对特定单位的远程穿甲几率
    mdf_vs: dict = dict()
    rdf_vs: dict = dict()
    # 新增冲锋攻击相关属性
    charge_mdg: int = 0  # 近战冲锋伤害
    charge_rdg: int = 0  # 远程冲锋伤害
    charge_mdg_vs: dict = dict()  # 对特定单位的近战冲锋伤害
    charge_rdg_vs: dict = dict()  # 对特定单位的远程冲锋伤害
    charge_mdg_splash: int = 0  # 近战冲锋溅射伤害
    charge_rdg_splash: int = 0  # 远程冲锋溅射伤害
    charge_mdg_radius: int = 0  # 近战冲锋溅射半径
    charge_rdg_radius: int = 0  # 远程冲锋溅射半径
    charge_mdg_splash_decay_min: float = 0  # 近战冲锋溅射最小衰减 (0.0-1.0)
    charge_rdg_splash_decay_min: float = 0  # 远程冲锋溅射最小衰减 (0.0-1.0)
    charge_mdg_splash_vs: dict = dict()  # 对特定单位类型的近战冲锋溅射伤害加成
    charge_rdg_splash_vs: dict = dict()  # 对特定单位类型的远程冲锋溅射伤害加成
    charge_mdg_radius_vs: dict = dict()  # 对特定单位类型的近战冲锋溅射半径加成
    charge_rdg_radius_vs: dict = dict()  # 对特定单位类型的远程冲锋溅射半径加成
    charge_mdg_splash_decay_min_vs: dict = dict()  # 对特定单位类型的近战冲锋溅射最小衰减加成
    charge_rdg_splash_decay_min_vs: dict = dict()  # 对特定单位类型的远程冲锋溅射最小衰减加成
    # 新增冲锋状态跟踪属性
    charge_mdg_ready: bool = True  # 近战冲锋就绪状态
    charge_rdg_ready: bool = True  # 远程冲锋就绪状态
    last_charge_mdg_target_id = None  # 上次近战冲锋的目标ID
    last_charge_rdg_target_id = None  # 上次远程冲锋的目标ID
    # 自爆相关属性
    mdg_explode = False  # 近战自爆标志
    rdg_explode = False  # 远程自爆标志
    mdg_explode_vs: dict = dict()  # 针对特定单位的近战自爆
    rdg_explode_vs: dict = dict()  # 针对特定单位的远程自爆
    exp_hp_cost = 0  # 自爆扣血百分比(默认0%)
    exp_dgf = 0  # 爆炸伤害系数
    exp_dgf_vs: dict = dict()  # 对特定单位的额外爆炸伤害系数
    # 抗暴击修正
    mdf_crit_rate_vs: dict = dict()  # 抵抗特定单位的近战暴击几率
    rdf_crit_rate_vs: dict = dict()  # 抵抗特定单位的远程暴击几率
    # 抗穿甲修正
    mdf_piercing_vs: dict = dict()  # 抵抗特定单位的近战穿甲
    rdf_piercing_vs: dict = dict()  # 抵抗特定单位的远程穿甲
    # 奖励相关属性
    resource_rewards = [0, 0]  # 默认奖励资源数量[资源1, 资源2]
    # 冷却、前摇、射程、最小射程、命中/闪避等 vs 修正
    mdg_cd_vs: dict = dict()
    rdg_cd_vs: dict = dict()
    mdg_ready_vs: dict = dict()
    rdg_ready_vs: dict = dict()
    mdg_range_vs: dict = dict()
    rdg_range_vs: dict = dict()
    mdg_minimal_range_vs: dict = dict()
    rdg_minimal_range_vs: dict = dict()
    mdg_cover_vs: dict = dict()
    rdg_cover_vs: dict = dict()
    mdg_dodge_vs: dict = dict()
    rdg_dodge_vs: dict = dict()
    speed_vs: dict = dict()
    mdg_splash_vs: dict = dict()
    rdg_splash_vs: dict = dict()
    mdg_splash_decay_min_vs: dict = dict()
    rdg_splash_decay_min_vs: dict = dict()
    mdg_radius_vs: dict = dict()
    rdg_radius_vs: dict = dict()

    type_name: Optional[str] = None
    is_a_unit = False
    is_a_building = False
    is_creature = True
    stat_type = None
    can_gather = None  # 修改：从空列表[]改为None，表示未定义状态

    @classmethod
    def interpret(cls, d):
        """解析单位的所有属性，包括vs属性"""
        # 首先解析vs字典属性（在调用父类方法前）
        cls._interpret_vs_attributes(d)
        
        # 然后调用父类的interpret方法（如果有的话）
        super().interpret(d) if hasattr(super(), 'interpret') else None
    
    @classmethod
    def _interpret_vs_attributes(cls, d):
        """解析所有vs相关的属性，将字符串格式转换为父类期望的列表格式"""
        vs_attributes = [
            # 基本伤害vs
            "mdg_vs", "rdg_vs",
            # 防御vs
            "mdf_vs", "rdf_vs",
            # 暴击vs
            "mdg_crit_vs", "rdg_crit_vs",
            "mdg_crit_rate_vs", "rdg_crit_rate_vs",
            # 暴击抗性vs
            "mdf_crit_rate_vs", "rdf_crit_rate_vs",
            # 穿甲vs
            "mdg_piercing_vs", "rdg_piercing_vs",
            "mdg_piercing_rate_vs", "rdg_piercing_rate_vs",
            # 穿甲抗性vs
            "mdf_piercing_vs", "rdf_piercing_vs",
            # 自爆vs
            "mdg_explode_vs", "rdg_explode_vs",
            "exp_dgf_vs",
            # 其他属性vs
            "mdg_cd_vs", "rdg_cd_vs",
            "mdg_ready_vs", "rdg_ready_vs",
            "mdg_range_vs", "rdg_range_vs",
            "mdg_minimal_range_vs", "rdg_minimal_range_vs",
            "mdg_cover_vs", "rdg_cover_vs",
            "mdg_dodge_vs", "rdg_dodge_vs",
            "mdg_splash_vs", "rdg_splash_vs",
            "mdg_splash_decay_min_vs", "rdg_splash_decay_min_vs",
            "mdg_radius_vs", "rdg_radius_vs",
            # 冲锋相关vs
            "charge_mdg_vs", "charge_rdg_vs",
            "charge_mdg_splash_vs", "charge_rdg_splash_vs",
            "charge_mdg_radius_vs", "charge_rdg_radius_vs",
            "charge_mdg_splash_decay_min_vs", "charge_rdg_splash_decay_min_vs",
            # 反冲锋vs
            "op_charge_mdg_vs", "op_charge_rdg_vs",
            # 速度vs
            "speed_vs",
            # 选敌威胁 vs
            "menace_vs",
            "menace_mult_vs",
        ]
        
        for attr in vs_attributes:
            if attr in d:
                vs_data = d[attr]
                
                # 如果是字符串格式，转换为列表格式供父类处理
                if isinstance(vs_data, str):
                    # 格式: "unit1 value1 unit2 value2" -> ["unit1", "value1", "unit2", "value2"]
                    parts = vs_data.split()
                    d[attr] = parts
                elif isinstance(vs_data, dict):
                    # 如果已经是字典格式，转换为列表格式
                    list_format = []
                    for unit_type, value in vs_data.items():
                        list_format.extend([unit_type, str(value)])
                    d[attr] = list_format
                elif isinstance(vs_data, (list, tuple)):
                    # 如果已经是列表/元组格式，转换为列表
                    d[attr] = list(vs_data)
                else:
                    # 未知格式，设置为空列表
                    from ..lib.log import warning
                    warning(f"Unknown format for {attr}: {type(vs_data)} - {vs_data}")
                    d[attr] = []

    def reset_charge_state(self, force=False):
        """
        重置冲锋状态，用于以下情况：
        1. 单位死亡或被摧毁时（force=True）
        2. 单位更换目标时（force=True）
        3. 单位离开战斗状态时（force=False，软重置）
        4. 单位移动到新位置超过一定距离时（force=True 或 False）

        Args:
            force: True 为硬重置（清空所有冲锋/反冲锋状态包括 ready、cooldown 记录、
                  上次目标 id）；False 为软重置（仅清"上次目标"记录，保留 ready/cooldown，
                  允许同目标在距离恢复后重新进入冲锋判定）。
        """
        if force:
            # 硬重置：恢复到初始状态
            self.charge_mdg_ready = True
            self.charge_rdg_ready = True
            self.last_charge_mdg_target_id = None
            self.last_charge_rdg_target_id = None
            # 同时重置反冲锋状态
            self.op_charge_mdg_ready = True
            self.op_charge_rdg_ready = True
            self.last_op_charge_mdg_target_id = None
            self.last_op_charge_rdg_target_id = None
        else:
            # 软重置：仅清除"上次目标"记录，保留 ready 与冷却计时器
            # 攻击结束/停止移动后允许后续逻辑对同目标重新判定，但仍受冷却约束
            self.last_charge_mdg_target_id = None
            self.last_charge_rdg_target_id = None
        
    def move_to(self, place, x, y, o=None, distance_sq=None):
        """移动单位到指定位置"""
        old_place = self.place
        old_x = self.x
        old_y = self.y
        if old_place is place:
            old_dist_sq = (x - old_x) ** 2 + (y - old_y) ** 2
            # 如果移动距离超过冲锋距离的平方，重置冲锋状态
            charge_dist_threshold = max(self.charge_mdg_dist, self.charge_rdg_dist) if hasattr(self, 'charge_mdg_dist') else 0
            if charge_dist_threshold > 0 and old_dist_sq > charge_dist_threshold**2:
                self.reset_charge_state(force=True)

        # 如果o为None，使用默认值90
        if o is None:
            o = 90
            
        # 调用Entity的move_to方法，但不传递distance_sq参数
        Entity.move_to(self, place, x, y, o)
        
        # 如果移动到了不同的地方，也重置冲锋状态
        if old_place is not place and (self.charge_mdg_dist > 0 or self.charge_rdg_dist > 0):
            self.reset_charge_state(force=True)
    
    def _cancel_attacks_against(self):
        """令所有正在攻击/追击本单位的友敌单位停手。"""
        for player in getattr(self.world, "players", []):
            units = list(getattr(player, "units", []))
            if hasattr(player, "allied_control_units"):
                units.extend(player.allied_control_units)
            seen = set()
            for unit in units:
                if unit in seen or not getattr(unit, "presence", True):
                    continue
                seen.add(unit)
                target = getattr(unit, "action_target", None)
                if target is None:
                    action = getattr(unit, "action", None)
                    if action is not None:
                        target = getattr(action, "target", None)
                if target is None and getattr(unit, "orders", None):
                    order = unit.orders[0]
                    if getattr(order, "keyword", None) in ("attack", "go"):
                        target = getattr(order, "target", None)
                if target is not self:
                    continue
                unit.action_target = None
                if hasattr(unit, "orders") and unit.orders and hasattr(
                    unit, "cancel_all_orders"
                ):
                    unit.cancel_all_orders(unpay=False)
                elif hasattr(unit, "stop"):
                    unit.stop()
                if hasattr(unit, "last_attacker"):
                    unit.last_attacker = None

    def _yield_instead_of_death(self, attacker=None):
        """战败投降：保留少量生命并停止战斗，供战役比武收服等剧情使用。"""
        if getattr(self, "_has_yielded", False):
            return
        self._has_yielded = True
        self.hp = max(1, int(self.hp_max) // 10)
        self.is_vulnerable = False
        self.last_attacker = None
        self.counterattack_enabled = False
        if hasattr(self, "orders") and hasattr(self, "cancel_all_orders"):
            self.cancel_all_orders(unpay=False)
        self.action_target = None
        if hasattr(self, "stop"):
            self.stop()
        self._cancel_attacks_against()
        if attacker is not None and attacker.player is not None:
            self.killer_id = attacker.player.id
        recorders = []
        if attacker is not None and getattr(attacker, "player", None) is not None:
            recorders.append(attacker.player)
        for player in self.world.players:
            if getattr(player, "is_human", False) and player not in recorders:
                recorders.append(player)
        for player in recorders:
            if hasattr(player, "record_unit_yielded"):
                player.record_unit_yielded(self, attacker)
        self.notify("yield")

    def release_yield_invulnerability(self):
        """结盟决定后结束认输无敌，恢复可受伤、可战斗。"""
        if not getattr(self, "_has_yielded", False):
            return
        self._has_yielded = False
        self.is_vulnerable = True
        self.yield_on_defeat = 0

    def die(self, attacker=None, notify_death=True):
        """
        处理单位死亡
        attacker: 击杀者（如果是被击杀）
        notify_death: 是否发送死亡通知(被击杀时为True)
        """
        if getattr(self, "_has_yielded", False):
            return
        if getattr(self, "yield_on_defeat", 0) and not getattr(self, "_has_yielded", False):
            self._yield_instead_of_death(attacker)
            return
        if self.place is None:
            return
        # 记录击杀者ID - 用于游戏失败条件判断
        if attacker is not None and attacker.player is not None and self.player is not None:
            # 记录单位被谁击杀
            self.killer_id = attacker.player.id
        
        # 重置冲锋状态
        self.reset_charge_state(force=True)
        
        # remove all buffs
        for b in self._buffs:
            b.stop(self)
        self._buffs = []
        # remove transported units
        if self.inside:
            # 防御性检查：确保 Inside 对象有 objects 属性
            if not hasattr(self.inside, 'objects') or self.inside.objects is None:
                self.inside.objects = []
            
            for o in self.inside.objects[:]:
                o.move_to(self.place, self.x, self.y)
                if o.place is self.inside:  # not enough space
                    o.collision = 0
                    o.move_to(self.place, self.x, self.y)
                if self.airground_type != "ground":
                    o.die(attacker)

        # 处理资源奖励 - 确保只有敌方单位击杀时才给予资源奖励，盟友击杀不给予奖励
        if (attacker is not None and attacker.player is not None and
                self.player is not None and attacker.player.player_is_an_enemy(self.player)):  # 确保是敌方单位，排除盟友
            # 获取奖励资源数量
            if hasattr(self, "resource_rewards"):
                # 解析奖励资源，格式为"resource1 resource2"或者一个包含多个元素的列表
                if isinstance(self.resource_rewards, str):
                    rewards = self.resource_rewards.split()
                else:
                    rewards = self.resource_rewards

                # 添加资源到击杀者的玩家
                if attacker.player is not None:
                    # 处理所有可能的资源类型
                    for i, reward in enumerate(rewards):
                        try:
                            resource_amount = int(reward) * 1000  # 转换为游戏内部单位
                            resource_type = f"resource{i+1}"  # 资源类型名称，如resource1, resource2...
                            
                            if resource_amount > 0:
                                # 存储资源
                                attacker.player.store(resource_type, resource_amount)
                                # 发送特定类型的资源奖励通知
                                attacker.player.send_event(attacker, f"{resource_type}_reward")
                        except (ValueError, IndexError):
                            pass  # 忽略无效的资源数据


        # 在通知和删除前处理经验值奖励 - 确保attacker能获得经验
        if attacker is not None and hasattr(self, 'xp_reward') and self.xp_reward > 0:
            attacker.claim_rewards(self)

        hunt_info = None
        food_deposit_name = getattr(type(self), "food_deposit", None)
        food_qty = getattr(type(self), "food_deposit_qty", 0)
        if food_deposit_name and food_qty and self.place is not None:
            hunt_info = (food_deposit_name, food_qty, self.place, self.x, self.y)

        # 只在被击杀时发送死亡通知和处理统计
        if notify_death:
            self.notify("death")
            if hasattr(self.player, 'stats'):
                self.player.stats.add("lost", self.stat_type)
            if attacker is not None:
                self.notify("death_by,%s" % attacker.id)
                self.player.on_unit_attacked(self, attacker)
                if hasattr(attacker.player, 'stats'):
                    attacker.player.stats.add("killed", self.stat_type)
                # 记录单位被击杀，用于触发"杀死目标单位"胜利条件或失败条件
                if hasattr(attacker.player, 'record_unit_killed'):
                    attacker.player.record_unit_killed(self)

        if self.player is not None:
            self.player.observed_objects.pop(self, None)
            self.player.perception.discard(self)

        self.delete()

        if hunt_info is not None and attacker is not None:
            player = getattr(attacker, "player", None)
            source_type_name = getattr(self, "type_name", None)
            deposit = self._create_hunt_food_deposit(
                self.world, *hunt_info, player=player, source_type_name=source_type_name
            )
            if deposit is not None:
                self._queue_hunt_gather(attacker, deposit)

    @staticmethod
    def _create_hunt_food_deposit(
        world, deposit_name, qty, place, x, y, player=None, source_type_name=None
    ):
        """狩猎动物死亡后在原地留下可采集的食物尸体。"""
        deposit_cls = world.unit_class(deposit_name)
        if deposit_cls is None:
            warning("unknown hunt food deposit type: %s", deposit_name)
            return None
        try:
            base_qty = int(qty) if not isinstance(qty, str) else int(float(qty))
            if player is not None:
                base_qty += int(getattr(player, "food_deposit_qty_bonus", 0) or 0)
            deposit = deposit_cls(place, str(base_qty))
            deposit.type_name = deposit_name
            if source_type_name:
                deposit.carcass_of = source_type_name
            deposit.collision = 0
            deposit.move_to(place, x, y)
            return deposit
        except Exception as e:
            warning("couldn't spawn hunt food deposit %s: %s", deposit_name, e)
            return None

    @staticmethod
    def _queue_hunt_gather(hunter, deposit):
        """猎人击杀动物后自动采集留下的食物尸体。"""
        from .worldworker import Worker
        if not Worker.has_gather_permissions(hunter):
            return
        if not hasattr(hunter, "_can_gather_target"):
            return
        if not hunter._can_gather_target(deposit):
            return
        if hunter.orders and hunter.orders[0].keyword == "attack":
            hunter.orders[0].mark_as_complete()
        hunter.take_order(["gather", deposit.id], forget_previous=False)
    def set_action_target(self, value):
        if isinstance(value, tuple):
            self.action = MoveXYAction(self, value)
        elif isinstance(value, ZoomTarget):
            self.action = MoveXYAction(self, (value.x, value.y))
        elif self.is_an_enemy(value):
            # 中立在「非明确攻击命令」下 is_an_enemy 仍可能为 True（外交上的敌方）。
            # 普通 go 跟随时必须 MoveAction，否则会挂 AttackAction：界面显示攻击却无伤害。
            if (
                self._is_neutral_target(value)
                and not self._player_ordered_attack_on(value)
            ):
                self.action = MoveAction(self, value)
            else:
                self.action = AttackAction(self, value)
        elif value is not None:
            self.action = MoveAction(self, value)
        else:
            self.action = Action(self, value)
    def _put_building_site(self, type, target, addon_host=None):
        from ..world_build_rules import (
            addon_build_target_coords,
            building_sacrifices_worker,
            building_self_constructs,
            is_addon_type,
            worker_place_and_leave,
        )

        # if the target is a memory, get the true object instead
        if getattr(target, "is_memory", False):
            target = target.initial_model
        
        # 检查目标对象是否仍然有效（未被删除）
        if target.place is None and not hasattr(target, "find_free_space_for"):
            # target 是一个已删除的对象，无法建造
            warning(f"Cannot build on deleted target {target}, cancelling build order")
            # 取消当前建造命令
            if hasattr(self, 'orders') and self.orders:
                self.orders[0].cancel(unpay=True)  # 返还资源
            return
        
        # remember before deletion
        place, x, y, _id = target.place, target.x, target.y, target.id
        # 如果 target 本身就是一个地点（有 find_free_space_for 方法），使用 target
        # 否则使用 target.place
        if hasattr(target, "find_free_space_for"):  # target is a square or similar place
            place = target
        if is_addon_type(type) and addon_host is not None:
            place = addon_host.place
            x, y = addon_build_target_coords(addon_host, type, place)
        from ..worldresource import Deposit
        from ..world_build_rules import requires_deposit_type

        build_on_deposit = (
            isinstance(target, Deposit)
            and requires_deposit_type(type) is not None
            and getattr(target, "type_name", None) == requires_deposit_type(type)
        )
        if build_on_deposit:
            remember_land = False
        elif not (
            getattr(target, "is_an_exit", False)
            or type.is_buildable_anywhere
            or getattr(type, "is_buildable_on_water_only", False)
        ):
            if not is_addon_type(type):
                target.delete()  # remove the meadow replaced by the building
            remember_land = not is_addon_type(type)
        else:
            remember_land = False
        site = BuildingSite(self.player, place, x, y, type)
        if remember_land:
            site.building_land = target
        if build_on_deposit:
            site.build_deposit = target
        if getattr(target, "is_an_exit", False):
            site.block(target)
        if addon_host is not None:
            site.addon_host = addon_host

        if getattr(type, "is_buildable_on_water_only", False):
            from ..world_build_rules import (
                is_pure_water_square,
                refresh_scaffold_passage,
                worker_can_place_water_build,
            )

            if (
                worker_can_place_water_build(self, place)
                and self.place is not place
                and is_pure_water_square(place)
                and not is_pure_water_square(self.place)
            ):
                site.shore_land = self.place
                refresh_scaffold_passage(site)

        sacrifice = building_sacrifices_worker(type, self)
        self_constructs = building_self_constructs(type) or sacrifice
        leave_after_place = worker_place_and_leave(self, type)
        order = self.orders[0]

        if sacrifice:
            order.mark_as_complete()
            self.stop()
            self.delete()
        elif leave_after_place:
            order.mark_as_complete()
            self.stop()

        if not self_constructs:
            for unit in self.player.units:
                if unit is self or unit.place is None:
                    continue
                for n in range(len(unit.orders)):
                    if unit.orders[n] == order:
                        unit.orders[n] = BuildPhaseTwoOrder(unit, [site.id])
                        unit.orders[n].on_queued()
            if not sacrifice and not leave_after_place:
                self.orders[0] = BuildPhaseTwoOrder(self, [site.id])
                self.orders[0].on_queued()
    def is_an_enemy(self, c):
        # Fast reject: most callers pass Creature; avoid full isinstance when possible.
        if not getattr(c, "is_creature", False) and not isinstance(c, Creature):
            return False
        # 玩家已对目标下达攻击命令时视为敌人（普通 attack，或强制 go）。
        # 仅检查队首命令类型，避免 gather/build 路径上无谓查目标。
        orders = self.orders
        if orders:
            order = orders[0]
            kw = getattr(order, "keyword", None)
            if kw == "attack" or (
                getattr(order, "is_imperative", False) and kw == "go"
            ):
                if self._player_ordered_attack_on(c):
                    return True

        world = self.world
        # Common multiplayer path: no allied-control transfer in effect.
        # Skip controller lookup + unit_under_allied_control megacalls.
        if world is not None:
            if not getattr(world, "_allied_control_scanned", False):
                from ..worldplayerbase.allied_control import _world_has_allied_control

                world._allied_control_active = _world_has_allied_control(world)
                world._allied_control_scanned = True
            if not getattr(world, "_allied_control_active", False):
                p = self.player
                return bool(p) and p.player_is_an_enemy(c.player)

        ctrl = _allied_control_controller_for(self)
        if ctrl is not None:
            if ctrl.unit_under_allied_control(c):
                return False
            cp = c.player
            if cp is not None and (cp is ctrl or cp in getattr(ctrl, "allied", ())):
                return False
            if cp is not None:
                return ctrl.player_is_an_enemy(cp)
            return False
        ctrl_other = _allied_control_controller_for(c)
        if ctrl_other is not None and self.player is not None:
            if self.player is ctrl_other or self.player in getattr(
                ctrl_other, "allied", ()
            ):
                return False
        return bool(self.player) and self.player.player_is_an_enemy(c.player)
    def get_action_target(self):
        if self.action:
            return self.action.target
    def get_default_order(self, target_id):
        from ..worldresource import Deposit
        from ..worlditem import Item  # 导入Item类
        
        target = self.player.get_object_by_id(target_id)
        if not target:
            return
        elif getattr(target, "is_an_exit", False):
            return "block"
        elif getattr(target, "player", None) is self.player and self.have_enough_space(
                target
        ):
            return "load"
        elif getattr(target, "player", None) is self.player and target.have_enough_space(self):
            return "enter"
        # 检查是否是物品
        elif isinstance(target, Item) and self.have_inventory_space:
            return "pickup"

        # 携带物品时，右键能接收所携带物品的单位（含NPC/中立单位）= 交给该单位
        elif (
            getattr(target, "player", None) is not None
            and target is not self
            and not getattr(target, "is_a_building", False)
            and getattr(self, "inventory", None)
            and callable(getattr(target, "accepts_item", None))
            and any(target.accepts_item(it, self) for it in self.inventory)
        ):
            return "give"

        elif (
            getattr(target, "herdable", 0)
            and "herd" in self.basic_skills
            and getattr(target, "hp", 0) > 0
        ):
            return "herd"

        elif (
            getattr(target, "is_huntable", 0)
            and "attack" in self.basic_skills
            and getattr(target, "hp", 0) > 0
        ):
            return "attack"

        capture_order = self._capture_on_contact_default_order(target)
        if capture_order:
            return capture_order

        elif "gather" in self.basic_skills and isinstance(target, Deposit):
            from .worldworker import Worker
            if not Worker.has_gather_permissions(self):
                return "go"
            if hasattr(self, "_can_gather_target") and not self._can_gather_target(target):
                return "go"
            return "gather"
        elif (
                isinstance(target, BuildingSite)
                and target.type.__name__ in self.can_build
                or hasattr(target, "is_repairable")
                and target.is_repairable
                and target.hp < target.hp_max
                and self.can_build
        ) and not self.is_an_enemy(target):
            return "repair"
        # 检查靠岸的船只是否可以修理
        elif (hasattr(target, "can_be_repaired_by_worker_from_shore") and 
              target.can_be_repaired_by_worker_from_shore(self) and
              self.can_build and
              self.can_repair_ships and
              not self.is_an_enemy(target)):
            return "repair"
        elif RallyingPointOrder.is_allowed(self):
            return "rallying_point"
        elif GoOrder.is_allowed(self):
            return "go"
    action_target = property(get_action_target, set_action_target)
    distance_to_goal = float("inf")
    hp_start = 0
    hp_max = 0
    hp_max_per_level = 0
    hp_regen = 0
    hp_regen_per_level = 0
    mana_max = 0
    mana_start = 0
    mana_regen = 0
    walked: List[Tuple[Optional[Square], int, int, int]] = []
    xp_reward = 0
    xp_reward_per_xp = 0
    xp_thresholds: List[int] = []
    xp = 0
    level = 1
    level_up_heal_full = 0  # 1 = 每次升级后 hp/mana 回满（rules.txt: level_up_heal_full 1）
    level_up_reset_xp = 0  # 1 = 每次升级后当前经验清零（rules.txt: level_up_reset_xp 1）
    cost = (0,) * MAX_NB_OF_RESOURCE_TYPES
    time_cost = 0
    change_time = 0
    morph_as_train = 0  # can_upgrade_to / can_change_to 均按目标单位训练成本/时间计费
    population_cost = 0
    population_provided = 0
    ai_mode: Optional[str] = None
    can_switch_ai_mode = False
    # 开局是否自动探索；可由 rules.txt 配置（auto_explore 1/0），默认关闭。
    # 仅对可移动单位生效，行为由 decide() 发起 auto_explore 标准命令驱动。
    auto_explore = False
    # 该单位的命令菜单里是否提供"启用/禁用自动探索"选项；可由 rules.txt
    # 配置（can_auto_explore 1/0），默认关闭。作者可只给特定单位（如 knight）
    # 开放该选项，其它单位则看不到自动探索命令。
    can_auto_explore = False
    storable_resource_types = ()
    storage_bonus = ()
    is_buildable_anywhere = True
    provides_build_field = ""
    requires_build_field = ""
    requires_deposit = ""
    bridge_terrain = ""
    build_field_radius = 0
    build_field_radius_m = 0
    build_field_persists = 0
    build_field_spreads = 0
    build_field_spread_squares = 0
    requires_build_field_on_square = 0
    loses_power_without_field = 0
    self_constructs = 0
    build_sacrifices_worker = 0
    is_addon = 0
    addon_host_types = ()
    can_have_addon = ()
    addon_max = 1
    addon_offset_x = 0
    addon_grants_train = ()
    addon_grants_train_barracks = ()
    addon_grants_train_factory = ()
    addon_grants_train_starport = ()
    addon_grants_research = ()
    addon_train_multiplier = 0
    inside = None
    inventory_capacity = 0
    no_number = 0  # 1=同类型仅1个时不报序号，2个及以上才报（默认0=始终报序号）
    receive_items = 0  # 是否接收其他单位交给的物品（1接收/0不接收，默认0）
    accepted_items = ()  # 仅接收这些物品类型（type_name，支持 is_a 继承）；空=接收任意物品
    accept_from = ()  # 仅接收来自这些关系的给予者：self/ally/neutral/enemy；空=不限关系
    accept_givers = ()  # 仅接收这些单位类型（type_name，支持 is_a 继承）交来的物品；空=不限单位
    transport_capacity = 0
    transport_volume = 1
    requirements = ()
    is_a = ()
    can_build = ()
    can_train = ()
    can_use = ()
    can_use_tech = ()
    can_use_skill = ()
    level_skills = ()  # 升级自动解锁：level_skills 10 skill_a
    learn_level_skills = ()  # 单位侧技能书门槛（可选，与物品 learn_level 取较高者）
    active_trigger_skills = ()
    passive_trigger_skills = ()
    attack_trigger_skills = ()
    attack_replace_skills = ()
    attack_trigger_buffs = ()
    attack_trigger_debuffs = ()
    attack_replace_buffs = ()
    attack_replace_debuffs = ()
    can_research = ()
    can_advance = ()
    can_upgrade_to = ()
    can_change_to = ()
    can_repair_ships = 0  # 0表示不允许修理船只，1表示允许
    mdg = 0  # 近战基础伤害
    rdg = 0  # 远程基础伤害
    charge_mdg = 0
    charge_rdg = 0
    mdf = 0  # 近战防御
    rdf = 0  # 远程防御
    mdf_crit_rate = 0  # 近战暴击抗性，抵抗暴击几率。
    rdf_crit_rate = 0  # 远程暴击抗性，抵抗暴击几率。
    mdf_piercing = 0  # 近战穿甲抗性，抵抗穿透程度
    rdf_piercing = 0  # 远程穿甲抗性，抵抗穿透程度
    mdg_crit = 0  # 近战暴击倍率
    rdg_crit = 0  # 远程暴击倍率
    mdg_crit_rate = 0  # 近战暴击几率
    rdg_crit_rate = 0  # 远程暴击几率
    mdg_piercing = 0  # 近战穿透程度
    rdg_piercing = 0  # 远程穿透程度
    mdg_piercing_rate = 0  # 近战穿甲几率
    rdg_piercing_rate = 0  # 远程穿甲几率
    mdg_level = 0
    rdg_level = 0
    mdg_per_level = 0
    rdg_per_level = 0
    mdf_per_level = 0
    rdf_per_level = 0
    debuffs: List[str] = []
    weapons = []
    armor = None  # 护甲名称
    buffs = ()
    mdg_minimal_damage = 0
    rdg_minimal_damage = 0
    auto_weapon_switch = False  # 是否启用自动武器切换
    spawn_weapons_equipped = 1  # 出厂时是否自动装备武器
    spawn_armor_equipped = 1  # 出厂时是否自动装备护甲
    weapon_switch_strategy = "distance"  # 武器切换策略：distance(距离优先), damage(伤害优先), range(射程优先)
    weapon_priority = []  # 武器优先级列表，优先级高的武器会被优先选择
    basic_skills: Set[str] = set()
    is_vulnerable = True
    is_healable = True
    is_a_gate = False
    provides_survival = False
    mdg_range = 0
    rdg_range = 0
    mdg_minimal_range = 0
    rdg_minimal_range = 0
    charge_mdg_dist = 0
    charge_rdg_dist = 0
    charge_mdg_min_dist = 0
    charge_rdg_min_dist = 0
    mdg_projectile = 0  # 近战攻击是否为投射物
    rdg_projectile = 0  # 远程攻击是否为投射物
    mdg_targets = ["ground"]
    rdg_targets = ["ground"]
    mdg_bang_targets = ["ground"]
    rdg_bang_targets = ["ground"]
    passenger_attack_types = []  # 容器内可攻击外部目标的单位类型列表
    load_bonus = {}  # 每装载一名单位 → 容器获得的属性加成
    passenger_bonus = {}  # 进入容器后 → 乘客获得的属性加成
    _bonus_stats = {}  # 容器装载加成的累计值（卸载时回滚）
    allow_attack_inside = False  # 是否允许攻击载具内部单位
    attack_inside_chance = 0  # 外部攻击命中容器内乘客的几率（0-100，仅对容器生效）
    capture_hp_threshold = 0  # 默认为0表示不可夺取
    yield_on_defeat = 0  # 战败后投降（不死亡），用于比武收服等剧情
    _last_capture_time = 0  # 上次夺取尝试的时间
    _capture_cooldown = 10000  # 10秒冷却时间(毫秒)
    mdg_delay = 0  # 近战伤害弹道
    rdg_delay = 0  # 远程伤害弹道
    mdg_radius = 0
    rdg_radius = 0
    mdg_splash = 0
    rdg_splash = 0
    mdg_splash_decay_min = 0  # 近战默认最小衰减
    rdg_splash_decay_min = 0  # 远程默认最小衰减
    mdg_cd = 0
    rdg_cd = 0
    charge_mdg_cd = 0
    charge_rdg_cd = 0
    charge_mdg_splash = 0  # 近战冲锋溅射伤害
    charge_rdg_splash = 0  # 远程冲锋溅射伤害
    charge_mdg_radius = 0  # 近战冲锋溅射半径
    charge_rdg_radius = 0  # 远程冲锋溅射半径
    charge_mdg_splash_decay_min = 0  # 近战冲锋溅射最小衰减 (0.0-1.0)
    charge_rdg_splash_decay_min = 0  # 远程冲锋溅射最小衰减 (0.0-1.0)
    mdg_next_attack_time = 0
    rdg_next_attack_time = 0
    mdg_prep_end_time = 0
    rdg_prep_end_time = 0
    mdg_ready = 0
    rdg_ready = 0
    mdg_cover = 0
    rdg_cover = 0
    mdg_dodge = 0
    rdg_dodge = 0
    mdg_status_duration = 0  # 近战伤害持续时间
    rdg_status_duration = 0  # 远程伤害持续时间
    damage_seq = None  # 攻击序列
    mdg_seq_times: int = 1  # 近战攻击次数
    mdg_seq_damages: List[int] = []  # 近战伤害序列
    mdg_seq_interval: float = 0  # 近战攻击间隔
    rdg_seq_times: int = 1  # 远程攻击次数
    rdg_seq_damages: List[int] = []  # 远程伤害序列
    rdg_seq_interval: float = 0  # 远程攻击间隔
    speed = 0
    # 添加自爆相关
    mdg_explode = False
    rdg_explode = False
    player = None
    last_player = None
    number = None
    expanded_is_a = ()
    # Round 4: _bulk_visibility_check 用 unit-level 视野 cache
    _cached_observed_squares = None
    _cached_observed_time = 0
    rallying_point = None
    corpse = 1
    is_huntable = 0
    can_capture = 1  # 1=对夺取阈值100的目标使用默认占领命令，0=普通攻击/移动
    food_deposit = None
    food_deposit_qty = 0
    flee_on_hit = 0
    herdable = 0
    herd_leash_range = 12000
    wander_range = 0
    _herd_leader = None
    _herd_follow_place = None
    decay = 0
    presence = 1
    count_limit = 0
    group = None
    global_count_limit = 0
    is_revivable = 0
    campaign_carryover = 0
    campaign_carryover_stats = 0
    campaign_carryover_inventory = 0
    revival_time = 0
    revival_time_per_level = 0
    # --- Army/Troops ---
    troop_size = 1  # 士兵数量（>1 表示单位为编队）
    hp_soldier_max = 0  # 每名士兵的最大生命
    def _notify_units_in_place(self, place, attacker):
        """通知指定区域中的友军单位"""
        for unit in place.objects:
            if (unit != self and
                    unit.player == self.player and
                    isinstance(unit, Creature) and
                    unit.ai_mode == "guard" and
                    getattr(unit, 'counterattack_enabled', False)):
                unit.last_attacker = attacker
    def add_cooldown(self, t):
        # 如果cooldown是列表，取第一个值
        if hasattr(t, 'cooldown'):
            if isinstance(t.cooldown, list) and t.cooldown:
                self._cooldowns[t] = self.world.time + int(t.cooldown[0])
            else:
                self._cooldowns[t] = self.world.time + t.cooldown
        else:
            # 如果没有cooldown属性，默认设置1秒冷却时间
            self._cooldowns[t] = self.world.time + 1000
    def has_cooldown(self, t):
        return t in self._cooldowns
    @property
    def have_inventory_space(self):
        """检查单位是否有足够的库存空间来拾取物品"""
        # 处理inventory_capacity可能是列表的情况
        inventory_capacity = self.inventory_capacity
        if isinstance(inventory_capacity, (list, tuple)):
            # 如果是列表或元组，取第一个值
            inventory_capacity = inventory_capacity[0] if inventory_capacity else 0
        
        # 确保是整数
        try:
            inventory_capacity = int(inventory_capacity)
        except (ValueError, TypeError):
            inventory_capacity = 0
            
        if inventory_capacity <= 0:
            return False
        return len(self.inventory) < inventory_capacity

    @property
    def can_receive_items(self):
        """单位是否接收其他单位交给的物品（由 rules.txt 的 receive_items 控制，默认0）。

        注意：这是"总开关"（粗粒度）。具体某件物品能否被接收，还要看
        ``accepted_items``（物品白名单）、``accept_from``（给予者关系白名单）、
        ``accept_givers``（给予者单位类型白名单），见 :meth:`accepts_item`。
        """
        receive_items = getattr(self, "receive_items", 0)
        # 处理 receive_items 可能是列表的情况（与 inventory_capacity 一致）
        if isinstance(receive_items, (list, tuple)):
            receive_items = receive_items[0] if receive_items else 0
        try:
            return int(receive_items) != 0
        except (ValueError, TypeError):
            return False

    # 给予者关系标准化：把各种写法归一到 self/ally/neutral/enemy
    _RELATION_ALIASES = {
        "self": "self", "own": "self", "mine": "self", "me": "self",
        "ally": "ally", "allies": "ally", "allied": "ally", "friend": "ally", "friendly": "ally",
        "neutral": "neutral", "neutrals": "neutral",
        "enemy": "enemy", "enemies": "enemy", "hostile": "enemy", "foe": "enemy",
    }

    def relation_to(self, giver):
        """返回本单位（接收者）相对于 giver（给予者）的关系：
        ``self`` / ``ally`` / ``neutral`` / ``enemy``。

        优先级：自己 > 盟友 > 中立 > 敌人（已结盟的中立按盟友处理）。
        """
        giver_player = getattr(giver, "player", None)
        my_player = getattr(self, "player", None)
        if giver_player is None or my_player is None:
            return "enemy"
        if my_player is giver_player:
            return "self"
        allied = getattr(giver_player, "allied", None)
        if allied is not None and my_player in allied:
            return "ally"
        if getattr(my_player, "neutral", False):
            return "neutral"
        return "enemy"

    def _item_in_whitelist(self, item, whitelist):
        for t in whitelist:
            if getattr(item, "type_name", None) == t:
                return True
            is_a_type = getattr(item, "is_a_type", None)
            if callable(is_a_type) and is_a_type(t):
                return True
        return False

    def _giver_in_whitelist(self, giver, whitelist):
        for t in whitelist:
            if getattr(giver, "type_name", None) == t:
                return True
            is_a_type = getattr(giver, "is_a_type", None)
            if callable(is_a_type) and is_a_type(t):
                return True
        return False

    def accepts_item(self, item, giver=None):
        """精细判断本单位是否接收 giver 交来的 item。

        依次校验：
        1. ``receive_items`` 总开关（默认0=不接收）；
        2. ``accepted_items`` 物品白名单（为空则接收任意物品，支持 is_a 继承）；
        3. ``accept_from`` 给予者关系白名单（为空则不限关系）；
        4. ``accept_givers`` 给予者单位类型白名单（为空则不限单位类型，支持 is_a 继承）。
        """
        if not self.can_receive_items:
            return False

        whitelist = getattr(self, "accepted_items", ()) or ()
        if whitelist and not self._item_in_whitelist(item, whitelist):
            return False

        accept_from = getattr(self, "accept_from", ()) or ()
        if accept_from and giver is not None:
            allowed = {
                self._RELATION_ALIASES.get(str(r).lower(), str(r).lower())
                for r in accept_from
            }
            if self.relation_to(giver) not in allowed:
                return False

        accept_givers = getattr(self, "accept_givers", ()) or ()
        if accept_givers:
            if giver is None:
                return False
            if not self._giver_in_whitelist(giver, accept_givers):
                return False

        return True


    def _resolve_default_ai_mode(self, fallback):
        """返回该单位开局应使用的 AI 模式。

        优先采用 rules.txt 中为该单位类型定义的 ``ai_mode``（会成为生成单位
        类的类属性）。若未定义或取值非法，则回退到 ``fallback``。
        """
        mode = type(self).ai_mode
        if mode in VALID_AI_MODES:
            return mode
        if mode is not None:
            warning(
                "%s: invalid ai_mode %r (expected one of %s); using %r",
                getattr(type(self), "type_name", type(self).__name__),
                mode,
                "/".join(VALID_AI_MODES),
                fallback,
            )
        return fallback

    def __init__(self, player, place, x, y, o=90):
        super().__init__(place, x, y, o)
        # 开局默认 AI 模式：优先使用 rules.txt 中为该单位类型定义的 ai_mode
        # （生成的单位类会带上该类属性），未定义或非法时回退到 offensive。
        self.ai_mode = self._resolve_default_ai_mode("offensive")
        self.counterattack_enabled = False  # 默认关闭反击
        self.last_attacker = None  # 初始化最后攻击者
        # 1. 从类属性读取配置值（冷却时长、伤害等）
        self.mdg = type(self).mdg
        self.rdg = type(self).rdg
        self.mdf = type(self).mdf
        self.rdf = type(self).rdf
        
        # 初始化冲锋攻击相关属性
        self.charge_mdg = type(self).charge_mdg
        self.charge_rdg = type(self).charge_rdg
        self.charge_mdg_cd = type(self).charge_mdg_cd
        self.charge_rdg_cd = type(self).charge_rdg_cd
        self.charge_mdg_dist = type(self).charge_mdg_dist
        self.charge_rdg_dist = type(self).charge_rdg_dist
        self.charge_mdg_min_dist = type(self).charge_mdg_min_dist
        self.charge_rdg_min_dist = type(self).charge_rdg_min_dist
        self.charge_mdg_next_time = 0  # 初始可立即使用
        self.charge_rdg_next_time = 0  # 初始可立即使用
        # 初始化冲锋溅射相关属性
        self.charge_mdg_splash = getattr(type(self), 'charge_mdg_splash', 0)
        self.charge_rdg_splash = getattr(type(self), 'charge_rdg_splash', 0)
        self.charge_mdg_radius = getattr(type(self), 'charge_mdg_radius', 0)
        self.charge_rdg_radius = getattr(type(self), 'charge_rdg_radius', 0)
        self.charge_mdg_splash_decay_min = getattr(type(self), 'charge_mdg_splash_decay_min', 0.5)
        self.charge_rdg_splash_decay_min = getattr(type(self), 'charge_rdg_splash_decay_min', 0.5)
        # 初始化冲锋就绪状态和上次冲锋目标
        self.charge_mdg_ready = True  # 初始状态下可用
        self.charge_rdg_ready = True  # 初始状态下可用
        self.last_charge_mdg_target_id = None  # 上次近战冲锋的目标ID
        self.last_charge_rdg_target_id = None  # 上次远程冲锋的目标ID
        
        # 初始化反冲锋相关属性
        self.op_charge_mdg = type(self).op_charge_mdg
        self.op_charge_rdg = type(self).op_charge_rdg
        self.op_charge_mdg_cd = type(self).op_charge_mdg_cd
        self.op_charge_rdg_cd = type(self).op_charge_rdg_cd
        self.op_charge_mdg_dist = type(self).op_charge_mdg_dist
        self.op_charge_rdg_dist = type(self).op_charge_rdg_dist
        self.op_charge_mdg_next_time = 0  # 初始可立即使用
        self.op_charge_rdg_next_time = 0  # 初始可立即使用
        self.op_charge_mdg_ready = True  # 初始状态下可用
        self.op_charge_rdg_ready = True  # 初始状态下可用
        self.last_op_charge_mdg_target_id = None  # 上次近战反冲锋的目标ID
        self.last_op_charge_rdg_target_id = None  # 上次远程反冲锋的目标ID
        
        # 初始化自动武器切换属性
        self.auto_weapon_switch = getattr(type(self), 'auto_weapon_switch', False)
        self.weapon_switch_strategy = getattr(type(self), 'weapon_switch_strategy', "distance")
        self.weapon_priority = getattr(type(self), 'weapon_priority', [])
        
        # 初始化冲锋VS属性
        self.charge_mdg_vs = dict(type(self).charge_mdg_vs)
        self.charge_rdg_vs = dict(type(self).charge_rdg_vs)
        # 初始化冲锋溅射相关的VS属性
        self.charge_mdg_splash_vs = dict(getattr(type(self), 'charge_mdg_splash_vs', {}))
        self.charge_rdg_splash_vs = dict(getattr(type(self), 'charge_rdg_splash_vs', {}))
        self.charge_mdg_radius_vs = dict(getattr(type(self), 'charge_mdg_radius_vs', {}))
        self.charge_rdg_radius_vs = dict(getattr(type(self), 'charge_rdg_radius_vs', {}))
        self.charge_mdg_splash_decay_min_vs = dict(getattr(type(self), 'charge_mdg_splash_decay_min_vs', {}))
        self.charge_rdg_splash_decay_min_vs = dict(getattr(type(self), 'charge_rdg_splash_decay_min_vs', {}))
        
        # 初始化反冲锋VS属性
        self.op_charge_mdg_vs = dict(type(self).op_charge_mdg_vs)
        self.op_charge_rdg_vs = dict(type(self).op_charge_rdg_vs)
        
        # 初始化武器相关的实例属性（确保每个单位实例都有独立的武器设置）
        self.auto_weapon_switch = getattr(type(self), 'auto_weapon_switch', False)
        
        self.weapon_switch_strategy = getattr(type(self), 'weapon_switch_strategy', 'distance')
        self.weapon_priority = list(getattr(type(self), 'weapon_priority', []))

        # 初始化暴击属性
        self.mdg_crit = type(self).mdg_crit
        self.rdg_crit = type(self).rdg_crit
        self.mdg_crit_rate = type(self).mdg_crit_rate
        self.rdg_crit_rate = type(self).rdg_crit_rate
        # 初始化穿甲属性
        self.mdg_piercing = type(self).mdg_piercing
        self.rdg_piercing = type(self).rdg_piercing
        self.mdg_piercing_rate = type(self).mdg_piercing_rate
        self.rdg_piercing_rate = type(self).rdg_piercing_rate
        # 初始化抗暴击
        self.mdf_crit_rate = type(self).mdf_crit_rate
        self.rdf_crit_rate = type(self).rdf_crit_rate
        # 初始化抗穿甲
        self.mdf_piercing = type(self).mdf_piercing
        self.rdf_piercing = type(self).rdf_piercing

        # 初始化射程
        self.mdg_range = type(self).mdg_range
        self.rdg_range = type(self).rdg_range
        self.mdg_minimal_range = type(self).mdg_minimal_range
        self.rdg_minimal_range = type(self).rdg_minimal_range
        self.mdg_radius = type(self).mdg_radius
        self.rdg_radius = type(self).rdg_radius
        self.mdg_splash = type(self).mdg_splash
        self.rdg_splash = type(self).rdg_splash
        self.mdg_delay = type(self).mdg_delay
        self.rdg_delay = type(self).rdg_delay
        self.mdg_cd = type(self).mdg_cd  # 冷却时长（毫秒）
        self.rdg_cd = type(self).rdg_cd
        self.mdg_ready = type(self).mdg_ready
        self.rdg_ready = type(self).rdg_ready
        self.mdg_status_duration = type(self).mdg_status_duration
        self.rdg_status_duration = type(self).rdg_status_duration
        self.mdg_cover = type(self).mdg_cover
        self.rdg_cover = type(self).rdg_cover
        self.mdg_dodge = type(self).mdg_dodge
        self.rdg_dodge = type(self).rdg_dodge

        # 复制vs属性
        self.mdg_vs = dict(type(self).mdg_vs)
        self.rdg_vs = dict(type(self).rdg_vs)
        self.menace_vs = dict(type(self).menace_vs)
        self.menace_mult_vs = dict(type(self).menace_mult_vs)
        self.mdf_vs = dict(type(self).mdf_vs)
        self.rdf_vs = dict(type(self).rdf_vs)
        self.mdg_cover_vs = dict(type(self).mdg_cover_vs)  # 确保复制vs属性
        self.rdg_cover_vs = dict(type(self).rdg_cover_vs)  # 确保复制vs属性
        self.mdg_dodge_vs = dict(type(self).mdg_dodge_vs)
        self.rdg_dodge_vs = dict(type(self).rdg_dodge_vs)
        # 复制穿甲和暴击的vs属性
        self.mdg_crit_vs = dict(type(self).mdg_crit_vs)
        self.rdg_crit_vs = dict(type(self).rdg_crit_vs)
        self.mdg_crit_rate_vs = dict(type(self).mdg_crit_rate_vs)
        self.rdg_crit_rate_vs = dict(type(self).rdg_crit_rate_vs)
        self.mdg_piercing_vs = dict(type(self).mdg_piercing_vs)
        self.rdg_piercing_vs = dict(type(self).rdg_piercing_vs)
        self.mdg_piercing_rate_vs = dict(type(self).mdg_piercing_rate_vs)
        self.rdg_piercing_rate_vs = dict(type(self).rdg_piercing_rate_vs)

        # 添加自爆相关属性的初始化
        self.mdg_explode = type(self).mdg_explode  # 近战自爆标志
        self.rdg_explode = type(self).rdg_explode  # 远程自爆标志
        self.mdg_explode_vs = dict(type(self).mdg_explode_vs)  # 针对特定单位的近战自爆
        self.rdg_explode_vs = dict(type(self).rdg_explode_vs)  # 针对特定单位的远程自爆
        self.exp_hp_cost = type(self).exp_hp_cost  # 自爆扣血百分比
        self.exp_dgf = type(self).exp_dgf  # 爆炸伤害系数
        self.exp_dgf_vs = dict(type(self).exp_dgf_vs)  # 对特定单位的额外爆炸伤害系数

        # 初始化expanded_is_a集合
        if not hasattr(self, 'expanded_is_a') or not self.expanded_is_a:
            self.expanded_is_a = set()
            # 确保调用_expand_is_a来初始化expanded_is_a属性
            if hasattr(type(self), 'is_a'):
                self._expand_is_a(type(self).is_a)

        # 2. 初始化动态变化的实例属性（冷却计时器、前摇结束时间等）
        self.mdg_next_attack_time = 0
        self.rdg_next_attack_time = 0
        self.mdg_prep_end_time = 0
        self.rdg_prep_end_time = 0

        # 3. 其他实例属性初始化
        self._actual_speed = 0
        self.override_damage = None

        if self.transport_capacity:
            self.inside = Inside(self)

        # 确保坐标为整数
        x = int(float(x))  # 支持浮点数输入
        y = int(float(y))
        o = int(float(o))

        # 将类属性复制到实例属性（深拷贝避免修改类属性）
        self.hp_max = getattr(self, 'hp_max', 0)  # 配置中的hp_max：单兵生命
        self.hp_start = getattr(self, 'hp_start', 0)  # 配置中的hp_start：单兵起始生命

        # --- Troop HP aggregation ---
        # 当 troop_size>1 时，将hp视为每名士兵的hp，并聚合为单位总hp
        try:
            troop_sz = int(getattr(self, 'troop_size', 1))
        except Exception:
            troop_sz = 1
        if troop_sz > 1:
            per_soldier_max = int(self.hp_max)
            if per_soldier_max < 0:
                per_soldier_max = 0
            self.hp_soldier_max = per_soldier_max
            per_soldier_start = int(self.hp_start) if int(self.hp_start) > 0 else per_soldier_max
            # 聚合后的单位hp
            self.hp_max = per_soldier_max * troop_sz
            self.hp_start = per_soldier_start * troop_sz
            # 初始化生命值
            self.hp = self.hp_start if self.hp_start > 0 else self.hp_max
        else:
            # 单体单位保持原逻辑
            self.hp_soldier_max = int(self.hp_max)
            if hasattr(self, 'hp_start') and self.hp_start > 0:
                self.hp = self.hp_start
            else:
                self.hp = self.hp_max

        # 确保生命值是整数
        self.hp = int(self.hp)

        self.position_to_hold = place
        self.orders = []
        self._buffs = []
        self._cooldowns = {}

        # attributes required by transports and shelters (inside)
        self.inventory = []
        self.objects = []
        self.world = place.world
        self.neighbors = []
        self.title = []

        self.set_player(player)

        # 初始生命/魔法
        if self.hp_start > 0:
            self.hp = self.hp_start
        else:
            self.hp = self.hp_max
        if self.mana_start > 0:
            self.mana = self.mana_start
        else:
            self.mana = self.mana_max

        # rules.txt 中的初始等级/经验（需同时定义 xp_thresholds）
        target_level = getattr(type(self), "level", 1)
        if target_level > 1 and getattr(type(self), "xp_thresholds", None):
            self.level = 1
            from ..level_up_stats import apply_level_up_to

            apply_level_up_to(self, target_level, notify=False)
        elif target_level < 1:
            self.level = target_level
        cls_xp = getattr(type(self), "xp", 0)
        if cls_xp:
            self.xp = cls_xp

        # 合作战役难度：在敌方单位生成时缩放生命（含开局单位与后续触发器增援）。
        self._apply_coop_difficulty_hp()
        # 电脑 AI（ai.txt unit_hp）：在合作难度之后再缩放。
        self._apply_ai_unit_hp()

        # 最小伤害
        self.minimal_damage = rules.get("parameters", "minimal_damage")
        if self.minimal_damage is None:
            self.minimal_damage = int(0.17 * PRECISION)

        # 处理生命衰减
        if self.decay:
            self.time_limit = self.world.time + self.decay
        # 添加持续伤害状态追踪
        self.mdg_dot_end_time = 0  # 近战持续伤害结束时间
        self.rdg_dot_end_time = 0  # 远程持续伤害结束时间
        self.mdg_dot_damage = 0  # 每次近战持续伤害量
        self.rdg_dot_damage = 0  # 每次远程持续伤害量

        # 初始化资源量
        if hasattr(self, 'resource_volume_max') and self.resource_volume_max > 0:
            # 如果定义了初始资源量，则使用初始资源量；否则使用最大资源量
            if hasattr(self, 'resource_volume_start') and self.resource_volume_start > 0:
                self.resource_qty = self.resource_volume_start
            else:
                self.resource_qty = self.resource_volume_max
            # 确保在初始化后通知客户端
            self.notify(f"qty_update,{self.resource_qty}")

        self._apply_level_skills_up_to(notify=False)

    def _is_coop_difficulty_enemy(self) -> bool:
        """该单位是否应受合作战役难度影响（敌方：非人类且非中立的玩家所有）。

        合作战役里人类玩家结盟为一队，敌人都是非人类电脑。以"非人类且非中立"
        作为判据，可同时覆盖被 (ai ...) 升格、login 仍是 ai_timers 的电脑。
        """
        p = self.player
        if p is None:
            return False
        if getattr(p, "is_human", False):
            return False
        if getattr(p, "neutral", False):
            return False
        return True

    def _apply_coop_difficulty_hp(self) -> None:
        """按世界难度缩放敌方单位生命（整数运算，确定性安全）。"""
        factor = getattr(self.world, "enemy_hp_factor", 100)
        if factor == 100 or not self._is_coop_difficulty_enemy():
            return
        try:
            self.hp_max = max(1, int(self.hp_max) * factor // 100)
            self.hp = max(1, int(self.hp) * factor // 100)
            if getattr(self, "hp_soldier_max", 0):
                self.hp_soldier_max = max(1, int(self.hp_soldier_max) * factor // 100)
        except (TypeError, ValueError):
            pass

    def _apply_ai_unit_hp(self) -> None:
        """按 ai.txt ``unit_hp`` 缩放电脑玩家单位生命（整数运算，确定性安全）。"""
        p = self.player
        if p is None or not getattr(p, "is_computer_player", False):
            return
        if getattr(p, "neutral", False):
            return
        pct = getattr(p, "ai_unit_hp_percent", 100)
        if pct == 100:
            return
        try:
            if pct <= 0:
                self.hp_max = 1
                self.hp = 1
                if getattr(self, "hp_soldier_max", 0):
                    self.hp_soldier_max = 1
                return
            self.hp_max = max(1, int(self.hp_max) * int(pct) // 100)
            self.hp = max(1, int(self.hp) * int(pct) // 100)
            if getattr(self, "hp_soldier_max", 0):
                self.hp_soldier_max = max(1, int(self.hp_soldier_max) * int(pct) // 100)
        except (TypeError, ValueError):
            pass

    # --- Troop helpers ---
    def get_soldiers_alive(self) -> int:
        """返回当前存活士兵数量（向上取整）。单位死亡时为0。"""
        try:
            troop_sz = int(getattr(self, 'troop_size', 1))
        except Exception:
            troop_sz = 1
        if troop_sz <= 1:
            return 0 if self.hp <= 0 else 1
        per_max = int(getattr(self, 'hp_soldier_max', 0))
        if per_max <= 0:
            return 0 if self.hp <= 0 else troop_sz
        hp_total = max(0, int(self.hp))
        alive = (hp_total + per_max - 1) // per_max
        if alive < 0:
            alive = 0
        if alive > troop_sz:
            alive = troop_sz
        return alive

    def get_per_soldier_hp(self) -> int:
        """返回每名士兵的平均生命（用于显示）。"""
        try:
            troop_sz = int(getattr(self, 'troop_size', 1))
        except Exception:
            troop_sz = 1
        if troop_sz <= 1:
            return int(self.hp)
        if troop_sz <= 0:
            return 0
        return max(0, int(self.hp)) // troop_sz

    def do_auto_explore(self) -> None:
        # 执行一次"自动探索"步进（持续探索由 AutoExploreOrder 每帧调用驱动）。
        # 注意：方法名不能再叫 auto_explore，否则会与布尔属性 auto_explore
        # （rules.txt 可配置的开局默认状态）发生命名冲突。
        assert self.player is not None
        if not self.action_target:
            if self.place is not self._destination:
                self.action_target = self.next_stage(self._destination, avoid=True)
                if self.action_target is not None:
                    return
            for place in self.player.unknown_starting_squares:
                self.action_target = self.next_stage(place, avoid=True)
                if self.action_target is not None:
                    self._destination = place
                    return
            for place in self.player.unknown_squares[:10]:
                self.action_target = self.next_stage(place, avoid=True)
                if self.action_target is not None:
                    self._destination = place
                    return
            for place in self.player.squares_to_watch[:10]:
                self.action_target = self.next_stage(place, avoid=True)
                if self.action_target is not None:
                    self._destination = place
                    return
            # any square
            self._destination = self.world.random.choice(self.world.squares)
            self.action_target = self.next_stage(self._destination)
        elif self.player.is_very_dangerous(self.action_target):
            if not self.player.is_very_dangerous(self.place):
                self.action_target = None
        elif self.player.is_very_dangerous(self.place):
            retreat = self._previous_square
            if getattr(retreat, "is_inside_place", False):
                retreat = getattr(retreat, "outside", None)
            if retreat is not None and not self.player.is_very_dangerous(retreat):
                self.start_moving_to(retreat)

    def start_moving_to(self, target, avoid=False):
        # note: it can be an attack
        # note: several calls might be necessary
        self.action_target = self.next_stage(target, avoid=avoid)

    def _next_stage_to_enemy(self):
        for e in self.place.exits:
            if e.other_side.place.contains_enemy(self.player):
                return e
        return self.next_stage(self.world.random.choice(self.world.squares))

    def start_moving_to_enemy(self):
        if self.place.contains_enemy(self.player):
            self._choose_enemy(self.place)
        else:
            self.action_target = self._next_stage_to_enemy()

    # D-Phase 2 PR1: 从 CreatureProductionAndBuilding mixin 合并而来 (worldunit/world_production_and_building.py).
    # `_delta` 不需要合并 — CreatureAttributes._delta MRO 在前已覆盖, 原 mixin 内的副本是 dead code.
    # `be_built` 是建筑/可修理实体被工人修理时的回调; 仅在 worldorders/movement.py:236 通过
    # `self.target.be_built(self.unit)` 调用, 调用频率冷 (修理时才触发).
    def be_built(self, actor):
        if self.hp < self.hp_max:
            result = actor.check_if_enough_resources(self.repair_cost)
            if result is not None:
                actor.notify("order_impossible,%s" % result)
                actor.orders[0].mark_as_complete()
            else:
                actor.player.pay(self.repair_cost)
                self.hp = min(self.hp + self.hp_delta, self.hp_max)

    def __getstate__(self):
        from ..save_pickle import CREATURE_STRIP_ON_SAVE, pop_keys

        state = self.__dict__.copy()
        pop_keys(state, CREATURE_STRIP_ON_SAVE)
        state["walked"] = []
        return state


for _level_up_stat in LEVEL_UP_STAT_ATTRS:
    _pl_attr = f"{_level_up_stat}_per_level"
    if not hasattr(Creature, _pl_attr):
        setattr(Creature, _pl_attr, 0)


class _Building(Creature):
    ai_mode = "offensive"
    can_switch_ai_mode = False  # never flee

    is_repairable = True  # or buildable (in the case of a BuildingSite)
    is_healable = False
    is_a_building = True

    transport_volume = 99

    corpse = 0

    def die(self, attacker=None):
        from ..world_build_rules import cleanup_build_rules_on_death

        cleanup_build_rules_on_death(self)
        place, x, y = self.place, self.x, self.y
        Creature.die(self, attacker)
        if self.building_land:
            self.building_land.move_to(place, x, y)

class BuildingSite(_Building):
    type_name = "buildingsite"
    basic_skills = {"cancel_building"}

    def __init__(self, player, place, x, y, building_type):
        super().__init__(player, place, x, y)
        player.pay(building_type.cost)
        self.type = building_type
        self.hp_max = building_type.hp_max
        self._starting_hp = building_type.hp_max * 5 // 100
        self.hp = self._starting_hp
        # Prefer scaled time_cost (ai.txt build_time) over the raw type value.
        self.timer = self.time_cost // VIRTUAL_TIME_INTERVAL
        self.damage_during_construction = 0
        self.addon_host = None
        self.build_deposit = None
        self.shore_land = None
        from ..world_build_rules import building_self_constructs

        self._self_construct = (
            building_self_constructs(building_type)
            or getattr(building_type, "build_sacrifices_worker", 0)
        )
        self.notify("placed")

    def receive_hit(self, attacker, *args, **kargs):
        """接收来自攻击者的伤害"""
        # 判断是近战还是远程攻击
        is_melee = attacker.in_melee_range(self) if hasattr(attacker, 'in_melee_range') else True

        # 根据攻击类型获取伤害值
        if is_melee and hasattr(attacker, 'mdg'):
            damage = attacker.mdg
        elif not is_melee and hasattr(attacker, 'rdg'):
            damage = attacker.rdg
        else:
            damage = 0

        self.damage_during_construction += damage
        _Building.receive_hit(self, attacker, *args, **kargs)

    @property
    def is_buildable_anywhere(self):
        return self.type.is_buildable_anywhere

    @property
    def is_buildable_on_exits_only(self):
        return self.type.is_buildable_on_exits_only

    @property
    def is_buildable_near_water_only(self):
        return self.type.is_buildable_near_water_only

    @property
    def is_buildable_on_water_only(self):
        return self.type.is_buildable_on_water_only

    @property
    def is_a_gate(self):
        return self.type.is_a_gate

    @property
    def time_cost(self):
        base = self.type.time_cost
        player = getattr(self, "player", None)
        pct = getattr(player, "ai_build_time_percent", 100) if player else 100
        if pct == 100:
            return base
        if pct <= 0:
            return 0
        return max(0, int(base) * int(pct) // 100)

    @property
    def hp_delta(self):
        return self._delta(self.hp_max - self._starting_hp, 100)

    def be_built(self, actor):
        self._construction_tick()

    def _has_active_builder(self):
        world = getattr(self, "world", None)
        if world is None:
            return False
        my_id = self.id
        for player in getattr(world, "players", ()):
            for unit in getattr(player, "units", ()):
                if unit.place is None:
                    continue
                try:
                    order = unit.orders[0]
                except IndexError:
                    continue
                if getattr(order, "mode", None) != "build":
                    continue
                target = getattr(order, "target", None)
                if target is self or getattr(target, "id", None) == my_id:
                    return True
        return False

    @property
    def activity(self):
        if self.timer <= 0:
            return
        if self._has_active_builder():
            return "building"
        if self._self_construct:
            from ..world_build_rules import construction_can_progress

            if construction_can_progress(self):
                return "building"

    def can_be_repaired_by_worker_from_shore(self, worker):
        if getattr(self.type, "is_buildable_on_water_only", False):
            return False
        return super().can_be_repaired_by_worker_from_shore(worker)

    def delete(self):
        from ..world_build_rules import clear_scaffold_passage

        if getattr(self, "shore_land", None) is not None:
            clear_scaffold_passage(self)
        super().delete()

    def slow_update(self):
        if self._self_construct and self.timer > 0:
            from ..world_build_rules import construction_can_progress

            if construction_can_progress(self):
                self._construction_tick()
        if self.place is not None:
            super().slow_update()

    def _construction_tick(self):
        self.hp = min(self.hp + self.hp_delta, self.hp_max)
        self.timer -= 1
        if self.timer == 0:
            self._complete_construction()

    def _complete_construction(self):
        from ..world_build_rules import clear_scaffold_passage, finalize_new_building

        player, place, x, y = self.player, self.place, self.x, self.y
        blocked_exit = self.blocked_exit
        building_land = self.building_land
        build_deposit = getattr(self, "build_deposit", None)
        addon_host = getattr(self, "addon_host", None)
        if getattr(self, "shore_land", None) is not None:
            clear_scaffold_passage(self)
        self.delete()
        building = self.type(player, place, x, y)
        building.building_land = building_land
        if build_deposit is not None and getattr(build_deposit, "place", None) is not None:
            build_deposit.delete()
        if blocked_exit:
            building.block(blocked_exit)
        building.hp = self.type.hp_max - self.damage_during_construction
        site_stub = type("SiteStub", (), {"addon_host": addon_host})()
        finalize_new_building(building, site_stub)
        building.notify("complete")

    @property
    def is_fully_repaired(self):
        return False


class Building(_Building):
    is_buildable_anywhere = False
    is_buildable_on_exits_only = False
    is_buildable_near_water_only = False
    is_buildable_on_water_only = False
    provides_survival = True
    stat_type = "building"
    auto_production = 0  # 默认不可生产
    manual_production = 0  # 默认不启用手动生产模式
    auto_cultivate = 0  # 默认不可耕种（auto_production的别名）
    manual_cultivate = 0  # 默认不启用手动耕种模式（manual_production的别名）
    is_gather = 0  # 默认不将产出的资源添加到建筑自身
    production_type = "resource1"  # 默认生产资源类型为resource1（金子）
    production_item = None  # 生产的物品类型（落地供拾取）
    production_cost = (0, 0)  # 默认不消耗资源
    production_time = 0  # 默认生产时间为0
    production_qty = 0  # 默认产量为0
    larva_cap = 0  # 主巢：同格幼虫上限（异虫 mod）
    larva_spawn_time = 0  # 主巢：幼虫生成间隔（秒）
    is_producing = False  # 当前是否正在生产
    production_progress = 0  # 当前生产进度
    resource_volume_max = 0  # 最大资源量
    resource_volume_start = 0  # 初始资源量
    resource_qty = 0  # 当前资源量
    # 添加采集所需的类属性
    resource_type = None  # 资源类型
    extraction_time = 0  # 开采时间
    extraction_qty = 0  # 开采量
    resource_regen = 0 # 资源再生
    can_repair_ships = 0  # 0表示不允许修理船只，1表示允许
    _last_repair_time = 0  # 上次修理时间，用于控制修理频率

    @property
    def can_train(self):
        from ..world_build_rules import effective_can_train

        return effective_can_train(self)

    @property
    def can_research(self):
        from ..world_build_rules import effective_can_research

        return effective_can_research(self)

    def __init__(self, player, place, x, y, o=90):
        super().__init__(player, place, x, y, o)
        self.attached_addons = []
        self.attached_host = None
        from ..world_build_rules import finalize_new_building

        finalize_new_building(self)
        # 初始化资源量
        if hasattr(self, 'resource_volume_max') and self.resource_volume_max > 0:
            # 如果定义了初始资源量，则使用初始资源量；否则使用最大资源量
            if hasattr(self, 'resource_volume_start') and self.resource_volume_start > 0:
                self.resource_qty = self.resource_volume_start
            else:
                self.resource_qty = self.resource_volume_max
            # 确保在初始化后通知客户端
            self.notify(f"qty_update,{self.resource_qty}")
        
        # 初始化修理船只相关属性
        self.can_repair_ships = getattr(type(self), 'can_repair_ships', 0)
        self._last_repair_time = 0

    def next_stage(self, target, avoid=False):
        """为Building类添加next_stage方法，用于向后兼容
        
        这主要是为了支持td2地图中peasant定义为class building但期望有移动能力的情况
        """
        if self.is_inside:
            return
        if target is None or target.place is None:
            return None
        if not isinstance(target, Square):
            if self.place == target.place:
                return target
            place = target.place
        else:
            if self.place == target:
                return None
            place = target
        if not isinstance(place, Square):
            return None
        nxt, self.distance_to_goal = self.place._shortest_path_to(
            place, self.airground_type, self.player, avoid=avoid
        )
        return nxt

    def decide(self):
        """建筑物的决策逻辑，包括自动修理船只功能"""
        # 如果建筑物可以修理船只，执行自动修理逻辑
        if self.can_repair_ships and self.player is not None:
            self._auto_repair_ships()
        
        # 调用父类的决策逻辑（主要用于其他功能）
        super().decide()

    def _auto_repair_ships(self):
        """自动修理距离4格以内的受损船只"""
        # 控制修理频率，每2秒检查一次
        current_time = self.world.time
        if current_time - self._last_repair_time < 2000:  # 2秒间隔
            return
        
        self._last_repair_time = current_time
        
        # 使用距离4格的修理范围
        from ..lib.nofloat import int_distance
        max_repair_distance = 8 * 1000  # 8格的距离（以毫米为单位）
        
        # 在整个地图范围内查找需要修理的友方船只
        for p in self.player.allied:
            for obj in p.units:
                # 检查是否是友方的受损船只
                if (hasattr(obj, 'airground_type') and obj.airground_type == "water" and
                    hasattr(obj, 'is_repairable') and obj.is_repairable and
                    hasattr(obj, 'hp') and hasattr(obj, 'hp_max') and
                    obj.hp < obj.hp_max and obj.hp > 0):
                    
                    # 计算距离
                    distance = int_distance(self.x, self.y, obj.x, obj.y)
                    
                    # 如果在修理范围内，执行修理
                    if distance <= max_repair_distance:
                        self._repair_ship(obj)
                        # 一次只修理一艘船只，避免过于频繁
                        return

    def _repair_ship(self, ship):
        """修理指定的船只"""
        if not ship or ship.hp >= ship.hp_max:
            return
        
        # 计算修理量（每次修理10%的最大生命值）
        repair_amount = max(1, ship.hp_max // 10)
        
        # 计算修理后的生命值，不超过最大值
        new_hp = min(ship.hp + repair_amount, ship.hp_max)
        
        # 应用修理
        old_hp = ship.hp
        ship.hp = new_hp
        
        # 发送修理通知
        if new_hp > old_hp:
            ship.notify("repaired")
            # 可以添加修理音效
            self.notify("repair_ship")

    def extract_resource(self, qty):
        """从建筑物中提取资源
        
        Args:
            qty: 提取的资源量（游戏内部单位，已乘以1000）
            
        Returns:
            int: 实际提取的资源量（游戏内部单位）
        """
        # 确保建筑物有资源可以提取
        if not hasattr(self, 'resource_qty'):
            self.resource_qty = 0
            
        # 只有当建筑物有资源类型且资源量大于0时才能提取
        if hasattr(self, 'resource_type') and self.resource_type and self.resource_qty > 0:
            # 计算可提取的资源量
            # 注意：resource_qty是普通单位（1），而qty是游戏内部单位（1000）
            # 为了保持一致，我们将resource_qty乘以1000转换为游戏内部单位
            resource_qty_internal = self.resource_qty * 1000
            actual_qty = min(qty, resource_qty_internal)
            
            # 从建筑物中减去相应的资源量（转换回普通单位）
            self.resource_qty -= actual_qty // 1000
            
            # 发送资源量更新通知
            self.notify(f"qty_update,{self.resource_qty}")
            
            # 如果资源耗尽，发送耗尽通知
            if self.resource_qty <= 0:
                self.notify("exhausted")
                # 如果定义了resource_volume_max小于等于0，说明资源是无限的，重置资源量
                if hasattr(self, 'resource_volume_max') and self.resource_volume_max < 0:
                    self.resource_qty = 1000  # 设置一个较大的默认值
                    return actual_qty  # 返回工人实际获得的量（内部单位）
                else:
                    # 资源确实耗尽了
                    self.resource_qty = 0
            
            return actual_qty  # 返回工人实际获得的量（内部单位）
        return 0

    @property
    def can_start_produce(self):
        """检查建筑物是否具有生产能力，用于生产逻辑而非显示命令"""
        return getattr(self, "auto_production", 0) == 1 or getattr(self, "manual_production", 0) == 1

    _destination = None


    @classmethod
    def interpret(cls, d):
        """处理Building属性解析"""
        # 处理父类属性
        super().interpret(d)
        
        # 处理can_repair_ships参数 - 不要直接修改基类，而是设置到字典中
        # 这样每个建筑类型都会有自己的can_repair_ships属性
        if "can_repair_ships" in d:
            # 将属性设置到字典中，而不是直接修改基类
            d["can_repair_ships"] = int(d["can_repair_ships"])