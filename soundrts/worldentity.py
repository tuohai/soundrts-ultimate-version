from .lib.log import warning
from .lib.nofloat import PRECISION

COLLISION_RADIUS = 175  # millimeters # 350 / 2


class NotEnoughSpaceError(Exception):
    pass


class Entity:

    collision = 1
    place = None
    x = 0
    y = 0
    o = 0
    player = None
    menace = 0
    airground_type = "ground"
    bonus_height = 0
    activity = None
    blocked_exit = None
    building_land = None
    time_limit = None
    harm_level = 0
    
    # 新增heal/harm自定义属性
    heal_radius = 6 * PRECISION  # 治疗半径，默认6格
    harm_radius = 6 * PRECISION  # 伤害半径，默认6格
    heal_range = 0  # 治疗射程（单体瞄准），默认0表示不使用单体瞄准
    harm_range = 0  # 伤害射程（单体瞄准），默认0表示不使用单体瞄准
    heal_cd = 0  # 治疗冷却时间，默认0（持续治疗）
    harm_cd = 0  # 伤害冷却时间，默认0（持续伤害）
    heal_ready = 0  # 治疗前摇时间，默认0
    harm_ready = 0  # 伤害前摇时间，默认0
    # 生命回复冷却和前摇
    hp_regen_cd = 0  # 生命回复冷却时间，默认0（持续回复）
    hp_regen_ready = 0  # 生命回复前摇时间，默认0
    # 法力回复冷却和前摇
    mana_regen_cd = 0  # 法力回复冷却时间，默认0（持续回复）
    mana_regen_ready = 0  # 法力回复前摇时间，默认0
    # 治疗目标类型
    heal_target_type = ()  # 可治疗的目标类型，默认空（可治疗任何友军单位，但不包括建筑）

    qty = 0
    is_vulnerable = False
    is_repairable = False
    is_healable = False
    is_undead = False
    is_teleportable = False

    # Round 4: 给所有 Entity 子类 (Creature/Resource/Item/...) 提供
    # hp 默认值, 让 hot-path 的 hasattr(obj, 'hp') 永远 True;
    # 子类按需 override.
    # NB: is_inside 由后面的 @property 定义; class default = False 会被
    # descriptor 遮蔽, 因此不在此处声明, 但 hasattr(obj, 'is_inside') 永远 True.
    hp = 0

    is_a_building_land = False

    # D-Phase 2: Entity 上提 class-level defaults, 让所有非 Creature 实体
    # (Resource/Item/Corpse 等) 也能直接 LOAD_ATTR 走类属性, 替代 hot path 上
    # 大量 getattr(o, '...', default) 的慢路径. Creature 子类自带 override.
    is_a_unit = False
    is_a_building = False
    is_creature = False
    _allied_control_controller_cache = None
    type_name = None
    is_a_gate = False  # worldexit.is_blocked 检查所有 blockers; 默认 False
    # minimal_damage 在 Creature.__init__ 从 rules 注入实例属性; 非 Creature
    # 实体 (Resource/Item) 不会调用 self.minimal_damage, 但 hot-path 的
    # getattr(self, 'minimal_damage', 0) 会查询类层默认 → 0, 避免 fallback.
    minimal_damage = 0
    # auto_weapon_switch on Creature only; Entity default avoids attack_action
    # _should_auto_switch_weapon 的 getattr fallback (~876k calls / 5min).
    auto_weapon_switch = False

    transport_capacity = 0
    transport_volume = 99

    is_invisible = False
    is_cloakable = False
    is_cloaked = False
    sight_range = 85 * PRECISION // 10
    is_a_detector = False
    detection_range = 85 * PRECISION // 10
    is_a_cloaker = False
    cloaking_range = 6 * PRECISION

    # class-level 默认: 让 getattr(x, 'is_an_exit', False) 在热路径上
    # (worldplayercomputer2.play 29M calls) 直接命中类属性, 而不是触发
    # __getattribute__ + AttributeError 慢路径. Exit 子类 override 为 True.
    is_an_exit = False

    # Round 5: combat/targeting.py:229 调 `target.get_current_armor_name()`
    # 在 5min bench 的中后期触发 -- target 是 building (e.g. house) 时,
    # `get_current_armor_name` / `_armor_instance` 只在 Unit.__init__ 才
    # 初始化, building 不走那条路, AttributeError 在 do_hit/ranged_range
    # 里被 world.loop 吃掉, 让弹道命中静默丢. 在 Entity 设 class-level
    # 默认: 非 Unit 实体 armor_name = None, _armor_instance = None.
    # Unit.__init__ 会覆盖 _armor_instance 为实例属性, 实际装备护甲的单位
    # 仍按原逻辑工作.
    _armor_instance = None
    # D-Phase 2: armor 是 Creature 上的 class default None; 上提到 Entity 让
    # damage_calculation hot path 上的 getattr(target, 'armor', None) 改为直接
    # 属性访问 (12.88M + 12.74M melee/ranged calls / 5min).
    armor = None

    def get_current_armor_name(self):
        """Round 5 默认: 非 Unit 实体没有护甲, 返回 None."""
        return self.armor

    id = None

    speed = 0
    speed_on_terrain = ()
    mdg_cover_on_terrain = ()  # 添加近战命中修正
    rdg_cover_on_terrain = ()  # 添加远程命中修正
    mdg_dodge_on_terrain = ()  # 添加近战闪避修正
    rdg_dodge_on_terrain = ()  # 添加远程闪避修正
    mdg_on_terrain = ()  # 攻击者所在地形上的近战攻击力修正
    rdg_on_terrain = ()  # 攻击者所在地形上的远程攻击力修正
    mdg_cd_on_terrain = ()  # 攻击者所在地形上的近战攻击冷却修正
    rdg_cd_on_terrain = ()  # 攻击者所在地形上的远程攻击冷却修正
    charge_mdg_terrain = ()  # 攻击者所在地形上的近战冲锋伤害修正
    charge_rdg_terrain = ()  # 攻击者所在地形上的远程冲锋伤害修正
    charge_mdg_cd_on_terrain = ()  # 攻击者所在地形上的近战冲锋冷却修正
    charge_rdg_cd_on_terrain = ()  # 攻击者所在地形上的远程冲锋冷却修正
    # Per-unit cache for attacker terrain lookups (place/x/y).
    _attacker_terrain_place = None
    _attacker_terrain_x = None
    _attacker_terrain_y = None
    _attacker_terrain_type = None
    is_moving = False

    def __repr__(self):
        return "%s()" % self.__class__.__name__

    @property
    def is_memory(self):
        return hasattr(self, "time_stamp")

    @property
    def is_near_water(self):
        return getattr(self.place, "is_near_water", False)

    def is_ship_near_shore(self):
        """
        检测船只是否靠岸（水上单位是否接近陆地）
        如果该单位是水上单位且在水域中，检查相邻区域是否有陆地
        """
        if (self.airground_type != "water" or 
            not self.place or 
            not hasattr(self.place, 'is_water') or 
            not self.place.is_water):
            return False
        
        # 检查相邻区域是否有陆地
        if hasattr(self.place, 'strict_neighbors'):
            for neighbor in self.place.strict_neighbors:
                # 如果邻居是陆地且是地面（不是高地），则认为是靠岸
                if (hasattr(neighbor, 'is_ground') and neighbor.is_ground and 
                    hasattr(neighbor, 'is_water') and not neighbor.is_water and
                    not getattr(neighbor, 'high_ground', False)):
                    return True
        
        return False

    def is_water_unit_on_land(self):
        """
        检查当前单位是否是水上单位但位于陆地上
        如果是水上单位但在陆地上，返回True，否则返回False
        """
        # 检查是否是水上单位
        if self.airground_type != "water":
            return False
        
        # 检查当前位置是否在陆地上（不是水域）
        if not self.place:
            return False
        
        # 如果当前位置不是水域，则认为是在陆地上
        if not getattr(self.place, 'is_water', False):
            return True
        
        return False

    def can_be_repaired_by_worker_from_shore(self, worker):
        """
        检测这个单位是否可以被岸上的工人修理
        适用于船只靠岸修理的情况
        修理距离为4格
        """
        # 检查基本修理条件
        if (not getattr(self, 'is_repairable', False) or 
            not hasattr(self, 'hp') or 
            not hasattr(self, 'hp_max') or 
            self.hp >= self.hp_max):
            return False
        
        # 检查是否是水上单位且靠岸
        if not self.is_ship_near_shore():
            return False
        
        # 检查工人是否在相邻的陆地上
        if (not worker or 
            not worker.place or 
            worker.airground_type != "ground"):
            return False
        
        # 检查工人是否在靠近水域的陆地上
        if not worker.is_near_water:
            return False
        
        # 检查工人与船只的距离（允许距离为4）
        if hasattr(worker, 'place') and hasattr(self, 'place'):
            # 使用BFS算法查找距离为4以内的路径
            from .lib.nofloat import int_distance
            
            # 直接计算坐标距离
            distance = int_distance(worker.x, worker.y, self.x, self.y)
            max_repair_distance = 6 * 1000  # 6格的距离（以毫米为单位）
            
            if distance <= max_repair_distance:
                return True
        
        return False

    _previous_square = None

    def move_to(self, new_place, x=None, y=None, o=90):
        if x is None:
            x = new_place.x
            y = new_place.y
        
        # 确保坐标为整数
        x = int(float(x))
        y = int(float(y))
        o = int(float(o))

        # 确保对象不是记忆体
        if self.is_memory:
            warning("Will move the real object instead of its memorized version.")
            self.initial_model.move_to(new_place, x, y, o)
            return

        # 检查空间是否足够
        if new_place and self.collision:
            x, y = new_place.find_free_space_for(self, x, y)
            if x is None:
                if self.place:
                    return
                else:
                    raise NotEnoughSpaceError

        # 执行移动
        if self.collision:
            self.free_space()
        self.x = x
        self.y = y
        self.o = o
        if new_place is not self.place:
            self._move_to_new_place(new_place)
        if self.collision:
            self.occupy_space()
        if self.speed:
            self.is_moving = True

    def _move_to_new_place(self, new_place):
        if self.place:
            self.place.leave(self)
            if not new_place:
                self.place.world.unregister_entity(self)
        self._previous_square = self.place
        self.place = new_place
        if new_place:
            new_place.enter(self)
            # reactions
            self.action_target = None

    def occupy_space(self):
        if self.place:
            self.place.add(self)

    def free_space(self):
        if self.place:
            self.place.remove(self)

    def delete(self):
        self.unblock()
        self.move_to(None, 0, 0)

    def __init__(self, place, x=None, y=None, o=90):
        self.world = place.world
        self.move_to(place, x, y, o)

    @property
    def is_inside(self):
        # 极简快速路径：通过位置对象上的布尔标记判断
        # Round 4: _Space.is_inside_place = False 是 class default; 直接 LOAD_ATTR
        # 比 getattr 慢路径快 (28M calls/5min → ~3-4s).
        p = self.place
        return False if p is None else p.is_inside_place

    @property
    def radius(self):
        if self.collision:
            return COLLISION_RADIUS
        else:
            return 0

    def clean(self):
        self.__dict__ = {}

    def is_an_enemy(self, a):
        return False

    def notify(self, event, universal=False):
        # 移除 harm 调试输出
        # 对于攻击相关事件和死亡事件，直接由单位本身发出
        if event.startswith(("launch_mdg", "launch_rdg", "attack", "death")):
            emitter = self
        else:
        # 其他事件保持原有逻辑
            emitter = self.place.container if self.is_inside else self
        
        if emitter.place:
            for player in emitter.place.world.players:
                if emitter in player.perception or universal:
                    player.send_event(emitter, event)

    def would_collide_if(self, x, y):
        # optimization: same collision radius for every entity with collision
        if self.collision:
            return self.place.would_collide(self, x, y)

    def contains(self, x, y):
        return True

    def block(self, e):
        # 如果是水上单位意外上岸了，不允许阻挡
        if self.is_water_unit_on_land():
            return
        self.blocked_exit = e
        e.add_blocker(self)

    def unblock(self):
        if self.blocked_exit:
            # 检查对象是否在阻塞者列表中，避免ValueError
            if self in self.blocked_exit._blockers:
                self.blocked_exit.remove_blocker(self)
            self.blocked_exit = None

    @property
    def any_land(self):
        for s in self.place.subsquares:
            if s.contains(self.x, self.y):
                return s.any_land
