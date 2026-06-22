from typing import Set
from .worldbase import Unit

class Effect(Unit):
    collision = 0
    corpse = 0
    food_cost = 0
    is_vulnerable = False
    presence = 0
    _basic_skills: Set[str] = set()
    harm_level = 0
    decay = 10000  # 默认10秒
    time_limit = 0  # 创建后自动消失的时间
    
    # 新增buffs和debuffs关键字
    buffs: Set[str] = set()  # 增益效果关键字集合
    debuffs: Set[str] = set()  # 减益效果关键字集合
    
    # buff/debuff 应用配置
    buff_radius = 0  # buff作用半径，0表示不使用范围buff
    debuff_radius = 0  # debuff作用半径，0表示不使用范围debuff
    target_allies = True  # 是否对友军应用buff
    target_enemies = True  # 是否对敌军应用debuff
    target_neutrals = False  # 是否对中立单位应用效果
    apply_buffs_on_creation = False  # 是否在创建时立即应用buff
    continuous_application = True  # 是否持续应用效果
    application_interval = 1000  # 应用间隔（毫秒）
    
    @classmethod
    def interpret(cls, d):
        # 调用父类的interpret方法
        super().interpret(d)
        
        # 解析buffs和debuffs
        for key in ["buffs", "debuffs"]:
            if key in d:
                if isinstance(d[key], str):
                    # 如果是字符串，按空格分割为列表
                    d[key] = d[key].split()
                elif not isinstance(d[key], list):
                    # 如果不是列表，转换为包含单个元素的列表
                    d[key] = [d[key]]
        
        # 处理数值参数
        for k, f in [
            ("buff_radius", int),
            ("debuff_radius", int),
            ("application_interval", int),
        ]:
            if k in d:
                if isinstance(d[k], list) and len(d[k]) > 0:
                    d[k] = f(d[k][0])
                elif d[k] is not None:
                    d[k] = f(d[k])
        
        # 处理布尔参数
        for k in ["target_allies", "target_enemies", "target_neutrals",
                  "apply_buffs_on_creation", "continuous_application"]:
            if k in d:
                if isinstance(d[k], list) and len(d[k]) > 0:
                    value = str(d[k][0]).lower()
                    d[k] = value not in ["0", "false", "no"]
                elif d[k] is not None:
                    value = str(d[k]).lower()
                    d[k] = value not in ["0", "false", "no"]
    
    def __init__(self, player, place, x, y, o=90):
        Unit.__init__(self, player, place, x, y, o)
        # 初始化buffs和debuffs
        self.buffs = set()
        self.debuffs = set()
        
        # 如果类定义了buffs和debuffs，复制到实例
        if hasattr(self.__class__, 'buffs') and self.__class__.buffs:
            if isinstance(self.__class__.buffs, (list, tuple)):
                self.buffs = set(self.__class__.buffs)
            elif isinstance(self.__class__.buffs, set):
                self.buffs = self.__class__.buffs.copy()
                
        if hasattr(self.__class__, 'debuffs') and self.__class__.debuffs:
            if isinstance(self.__class__.debuffs, (list, tuple)):
                self.debuffs = set(self.__class__.debuffs)
            elif isinstance(self.__class__.debuffs, set):
                self.debuffs = self.__class__.debuffs.copy()
        
        # 初始化应用相关属性
        self.last_application_time = 0
        
        # 设置自动消失时间
        if self.decay > 0:
            self.time_limit = self.world.time + self.decay
            
        # 在创建时应用buff（如果配置了）
        if getattr(self, 'apply_buffs_on_creation', False):
            self.apply_buffs_to_allies()

    def decide(self):
        # 检查是否需要持续应用效果
        if getattr(self, 'continuous_application', True):
            current_time = self.world.time
            if current_time - self.last_application_time >= getattr(self, 'application_interval', 1000):
                # 重新应用效果到友军
                self.apply_buffs_to_allies()
                self.last_application_time = current_time
        
        # 检查是否超时
        if self.time_limit > 0 and self.world.time >= self.time_limit:
            self.die()
            return

    def harm_nearby_units(self):
        """重写harm_nearby_units方法，集成buff/debuff应用功能"""
        from ..lib.nofloat import PRECISION
        
        # 调用父类原有的harm逻辑，但在造成伤害后添加buff/debuff处理
        # 检查冷却时间
        current_time = self.world.time
        harm_next_time = getattr(self, 'harm_next_time', 0)
        if current_time < harm_next_time:
            return
            
        # 检查前摇时间
        harm_ready = getattr(self, 'harm_ready', 0)
        harm_prep_end_time = getattr(self, 'harm_prep_end_time', 0)
        if harm_ready > 0:
            if current_time < harm_prep_end_time:
                return
            # 如果还没开始前摇，开始前摇
            if harm_prep_end_time == 0:
                self.harm_prep_end_time = current_time + harm_ready
                return
        
        # 伤害量计算：如果有冷却时间则一次伤害完整量，否则按原始逻辑
        harm_cd = getattr(self, 'harm_cd', 0)
        if harm_cd > 0:
            # 有冷却时间：一次性造成完整的harm_level伤害
            hp = self.harm_level * PRECISION
        else:
            # 无冷却时间：维持原始的分帧伤害逻辑（每25帧伤害完整量）
            hp = self.harm_level * PRECISION // 25
        
        # 使用自定义的伤害范围（与1.3.8.1一致，默认6格）
        harm_radius = getattr(self, 'harm_radius', 0) or 6 * PRECISION
        harm_range = getattr(self, 'harm_range', 0)
        
        # 记录被攻击的敌人，用于应用debuff
        attacked_enemies = []
        
        # 如果设置了单体射程，使用瞄准模式
        if harm_range > 0:
            # 单体瞄准伤害模式
            attacked_enemy = self._harm_targeted_unit_with_effects(hp, harm_range)
            if attacked_enemy:
                attacked_enemies.append(attacked_enemy)
        else:
            # 范围伤害模式
            attacked_enemies = self._harm_area_units_with_effects(hp, harm_radius)
        
        # 对被攻击的敌人应用debuff
        if attacked_enemies:
            self.apply_debuffs_to_enemies(attacked_enemies)
            
        # 同时对附近友军应用buff
        self.apply_buffs_to_allies()
        
        # 设置下次伤害时间（如果harm_cd为0则不设置冷却）
        if harm_cd > 0:
            self.harm_next_time = current_time + harm_cd
        self.harm_prep_end_time = 0  # 重置前摇时间

    def _harm_area_units_with_effects(self, hp, radius):
        """范围伤害模式（返回被攻击的敌人列表）"""
        attacked_enemies = []

        units = self.world.get_objects2(
            self.x,
            self.y,
            radius,
            filter=lambda x: x.is_vulnerable and self._can_harm(x),
            skip_cache=True,
        )
        
        for u in units:
            if u.player is None or u.hp <= 0:
                continue
            
            # 与1.3.8.1一致：直接伤害且不发送受伤通知，减少事件与音频开销
            if u.player:
                u.player.observe(self)
                u.last_attacker = self
            u.hp -= hp
            if u.hp <= 0:
                u.die(self)
            
            # 记录被攻击的敌人
            if self.is_valid_enemy_target(u):
                attacked_enemies.append(u)
                
        return attacked_enemies

    def _harm_targeted_unit_with_effects(self, hp, range_limit):
        """单体瞄准伤害模式（返回被攻击的敌人或None）"""
        # 查找最近的敌方单位
        from ..lib.nofloat import square_of_distance, PRECISION
        
        best_target = None
        best_distance = float('inf')
        
        # 在稍大范围内搜索目标
        search_radius = max(range_limit * 2, 10 * PRECISION)
        units = self.world.get_objects2(
            self.x,
            self.y,
            search_radius,
            filter=lambda x: x.is_vulnerable and self._can_harm(x),
            skip_cache=True,
        )
        
        # 找到射程内最近的敌方单位
        for u in units:
            distance = square_of_distance(self.x, self.y, u.x, u.y)
            max_distance = (range_limit + self.radius + u.radius) ** 2
            
            if distance <= max_distance and distance < best_distance:
                best_target = u
                best_distance = distance
        
        # 伤害目标
        if best_target:
            if best_target.player is None or best_target.hp <= 0:
                return None

            # 与1.3.8.1一致：直接伤害且不发送受伤通知
            if best_target.player:
                best_target.player.observe(self)
                best_target.last_attacker = self
            best_target.hp -= hp
            if best_target.hp <= 0:
                best_target.die(self)
            
            # 返回被攻击的敌人（如果是有效的敌人目标）
            if self.is_valid_enemy_target(best_target):
                return best_target
                
        return None

    def apply_debuffs_to_enemies(self, enemies):
        """对敌人应用debuff"""
        if not self.debuffs or not enemies:
            return
            
        for enemy in enemies:
            for debuff_name in self.debuffs:
                enemy.add_buff(debuff_name, self)

    def apply_buffs_to_allies(self):
        """对附近的友军应用buff"""
        if not self.buffs:
            return
            
        # 确定buff作用半径
        buff_radius = getattr(self, 'buff_radius', 0)
        if buff_radius == 0:
            buff_radius = 6 * 1000  # 默认6格范围
            
        # 查找范围内的友军
        units = self.world.get_objects2(
            self.x,
            self.y,
            buff_radius,
            filter=lambda x: (x.is_vulnerable and 
                            self.is_valid_ally_target(x)),
            skip_cache=True,
        )
        
        # 对每个友军应用buff
        for unit in units:
            for buff_name in self.buffs:
                unit.add_buff(buff_name, self)

    def is_valid_enemy_target(self, unit):
        """检查单位是否是有效的敌人目标"""
        if not getattr(self, 'target_enemies', True):
            return False
        return unit.player != self.player and unit.player is not None

    def is_valid_ally_target(self, unit):
        """检查单位是否是有效的友军目标"""
        if not getattr(self, 'target_allies', True):
            return False
        return unit.player == self.player and unit != self  # 不对自己应用

    def _can_harm(self, other):
        """检查是否可以伤害目标单位"""
        if not other.is_vulnerable:
            return False
        from .world_public_method import passes_harm_diplomacy_filter

        harm_target_type = getattr(self, "harm_target_type", ()) or ()
        if not passes_harm_diplomacy_filter(
            harm_target_type,
            getattr(self, "player", None),
            getattr(other, "player", None),
        ):
            return False
        if not harm_target_type:
            return True
        return self.world.can_harm(self.type_name, other.type_name)

    def die(self, attacker=None):
        self.delete()