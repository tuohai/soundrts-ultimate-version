from ..worldaction import Action, AttackAction, MoveAction, MoveXYAction
import math
from ..lib.nofloat import (
    PRECISION,
    int_angle,
    int_cos_1000,
    int_distance,
    int_sin_1000,
    square_of_distance,
    to_int,
)
from ..lib.log import warning, debug
import re
from ..definitions import MAX_NB_OF_RESOURCE_TYPES, VIRTUAL_TIME_INTERVAL, rules
from ..worldentity import Entity
class CreatureAttributes(Entity):

    @property
    def actual_speed(self):
        return self._actual_speed

    @actual_speed.setter
    def actual_speed(self, val):
        self._actual_speed = val

    @property
    def current_speed(self) -> int:
        """只读，始终根据状态动态返回"当前真实移动速度"""
        if isinstance(self.action, AttackAction) and self.action.target:
            return self._get_speed_vs(self.action.target)
        else:
            return self._actual_speed

    @property
    def is_melee(self) -> bool:
        """
        若我们认定 "近战" 表示: 具有mdg_range>0 并且没有rdg_range(或rdg_range=0)
        """
        return (self.mdg_range > 0) and (self.rdg_range <= 0)

    @property
    def actual_speed(self):
        return self._actual_speed
    @property
    def current_speed(self) -> int:
        """只读，始终根据状态动态返回"当前真实移动速度"""
        if isinstance(self.action, AttackAction) and self.action.target:
            return self._get_speed_vs(self.action.target)
        else:
            return self._actual_speed

    @property
    def upgrades(self):
        result = [u for u in self.can_use if u in self.player.upgrades]
        # 添加can_use_tech中的科技
        if hasattr(self, 'can_use_tech'):
            result.extend([u for u in self.can_use_tech if u in self.player.upgrades])
        return result
    @property
    def height(self):
        # D-Phase 2: place / bonus_height / place.height 都是 Entity / _Space
        # 的 class-level defaults (Entity.place=None, Entity.bonus_height=0,
        # _Space.high_ground=False, Square.height @property). 移除 getattr.
        # 10.83M calls / 5min, 原版每 call 3 个 getattr.
        if self.airground_type == "air":
            return 2
        place = self.place
        if place is None:
            return self.bonus_height
        if hasattr(place, "high_ground_at"):
            h = 1 if place.high_ground_at(self.x, self.y) else 0
        else:
            h = place.height
        return h + self.bonus_height
    # Round 4: class-level cache 默认值, 消除 hasattr 检查
    # menace 是单位 @property, 每帧调几百万次, 原版每 call 2 hasattr + 3 getattr
    _cached_menace = 0
    _menace_cache_timestamp = -1_000_000

    @property
    def menace(self):
        """Calculate unit's menace value - 优化版：添加5秒缓存

        Returns:
            int: Menace value based on:
            1. If unit has melee or ranged damage, menace equals the higher value
            2. If unit has transport capacity, menace equals transport_capacity * PRECISION * 2
            3. If none of above, menace equals 0

        Round 4: mdg/rdg/transport_capacity 在 Creature 类已有 class-level default (=0),
        _cached_menace / _menace_cache_timestamp 也由本类提供 default;
        hasattr/getattr 全部删除, 直接属性访问.
        """
        current_time = self.world.time

        # 检查缓存是否有效（5秒内）
        if current_time - self._menace_cache_timestamp < 5000:
            return self._cached_menace

        # 重新计算威胁度
        mdg = self.mdg
        rdg = self.rdg
        damage = mdg if mdg > rdg else rdg

        if damage:
            menace = damage
        elif self.transport_capacity:
            menace = self.transport_capacity * PRECISION * 2
        else:
            menace = 0

        # 缓存结果
        self._cached_menace = menace
        self._menace_cache_timestamp = current_time

        return menace

    @property
    def activity(self):
        try:
            o = self.orders[0]
        except IndexError:
            return
        # 优化9：缓存命令对象的属性检查
        if not hasattr(o, '_cached_has_mode'):
            o._cached_has_mode = hasattr(o, "mode")
        
        if o._cached_has_mode and o.mode == "build":
            return "building"
        if o._cached_has_mode and o.mode == "gather":
            # 缓存target的type_name属性检查 - 添加空值检查
            if o.target is not None:
                if not hasattr(o.target, '_cached_has_type_name'):
                    o.target._cached_has_type_name = hasattr(o.target, "type_name")
                if o.target._cached_has_type_name:
                    return "exploiting_%s" % o.target.type_name
    @property
    def is_dead(self):
        return self.hp <= 0
    @property
    def max_level(self):
        return len(self.xp_thresholds) + 1

    def _delta(self, total, percentage):
        # Initial formula (reordered for a better precision):
        # delta = (percentage / 100) * total / (self.time_cost / VIRTUAL_TIME_INTERVAL)
        try:
            delta = int(
                total * percentage * VIRTUAL_TIME_INTERVAL // self.time_cost // 100
            )
        except ZeroDivisionError:
            delta = int(total * percentage * VIRTUAL_TIME_INTERVAL // 100)
        if delta == 0 and total != 0:
            warning("insufficient precision (delta: %s total: %s)", delta, total)
        return delta

    @property
    def hp_delta(self):
        return self._delta(self.hp_max, 70)

    @property
    def repair_cost(self):  # per turn
        return (self._delta(c, 30) for c in self.cost)
    @property
    def is_fully_repaired(self):
        return getattr(self, "is_repairable", False) and self.hp == self.hp_max
    @property
    def is_idle(self):
        return self.action_target is None
    @classmethod
    def interpret_vs_attributes(cls, d, attrs):
        """
        通用 vs 属性解析函数，例如将:
        ["footman", "2", "knight", "4", "archer", "3"]
        解析为 { "footman":2, "knight":4, "archer":3 }。
        """
        for attr in attrs:
            items = d.get(attr, [])
            d[attr] = dict()
            targets = []
            for s in items:
                try:
                    n = to_int(s)
                    for t in targets:
                        # 只设置单数形式，不自动处理复数形式
                        d[attr][t] = n
                    targets = []
                except ValueError:
                    targets.append(s)
    @classmethod
    def interpret(cls, d):
        """
        不再处理旧的 damage/damage_vs，仅解析新字段
        """
        vs_attributes = [
            # "armor_vs",
            "mdg_vs",
            "rdg_vs",
            "mdf_vs",
            "rdf_vs",
            "mdg_cd_vs",
            "rdg_cd_vs",
            "mdg_ready_vs",
            "rdg_ready_vs",
            "mdg_range_vs",
            "rdg_range_vs",
            "mdg_minimal_range_vs",
            "rdg_minimal_range_vs",
            "speed_vs",
            "mdg_cover_vs",
            "rdg_cover_vs",
            "mdg_dodge_vs",
            "rdg_dodge_vs",
            "mdg_splash_vs",
            "rdg_splash_vs",
            "mdg_splash_decay_min_vs",
            "rdg_splash_decay_min_vs",
            "mdg_radius_vs",
            "rdg_radius_vs",
            "mdg_crit_vs",
            "rdg_crit_vs",
            "mdg_crit_rate_vs",
            "rdg_crit_rate_vs",
            "mdg_piercing_vs",
            "rdg_piercing_vs",
            "mdg_piercing_rate_vs",
            "rdg_piercing_rate_vs",
            "mdg_explode_vs",
            "rdg_explode_vs",
            "exp_dgf_vs",
            "mdf_crit_rate_vs",
            "rdf_crit_rate_vs",
            "mdf_piercing_vs",
            "rdf_piercing_vs",
            "charge_mdg_vs",
            "charge_rdg_vs",
            "op_charge_mdg_vs",
            "op_charge_rdg_vs",
            "charge_mdg_splash_vs",
            "charge_rdg_splash_vs",
            "charge_mdg_radius_vs",
            "charge_rdg_radius_vs",
            "charge_mdg_splash_decay_min_vs",
            "charge_rdg_splash_decay_min_vs",
        ]
        cls.interpret_vs_attributes(d, vs_attributes)

        # 解析属性效果
        #        cls.interpret_prop_effects(d, "mdg_prop")

        # 解析harm_target_type
        harm_targets_val = d.get("harm_target_type", "")
        if isinstance(harm_targets_val, list):
            cls.harm_target_type = harm_targets_val
        else:
            cls.harm_target_type = harm_targets_val.replace(";", "").strip().split()

        # 解析heal_target_type
        heal_targets_val = d.get("heal_target_type", "")
        if isinstance(heal_targets_val, list):
            cls.heal_target_type = heal_targets_val
        else:
            cls.heal_target_type = heal_targets_val.replace(";", "").strip().split()

        # 解析是否允许攻击内部目标
        if "allow_attack_inside" in d:
            cls.allow_attack_inside = int(d["allow_attack_inside"]) == 1

        # 注意：can_gather属性已移至Worker.interpret方法中处理，避免影响其他单位类型

        # 解析奖励资源数量
        if "resource_rewards" in d:
            rewards = d["resource_rewards"]
            if isinstance(rewards, str):
                # 如果是字符串，尝试分割
                rewards = rewards.split()

            # 确保有至少两个值
            if len(rewards) >= 2:
                try:
                    # 转换为整数列表
                    cls.resource_rewards = [int(rewards[0]), int(rewards[1])]
                except (ValueError, IndexError):
                    # 保持默认值
                    pass
        else:
            # 如果没有明确定义，确保重置为默认值
            cls.resource_rewards = [0, 0]

        # 解析夺取占领 - 只在明确定义时设置
        if "capture_hp_threshold" in d:
            cls.capture_hp_threshold = int(d["capture_hp_threshold"])
        else:
            cls.capture_hp_threshold = 0  # 默认不可夺取

        if "yield_on_defeat" in d:
            cls.yield_on_defeat = int(d["yield_on_defeat"])
        else:
            cls.yield_on_defeat = 0

        # 解析允   许攻击的单位类型
        if "allow_units_attack" in d:
            if "all" in d["allow_units_attack"]:
                cls.allow_units_attack = ["all"]
            else:
                cls.allow_units_attack = d["allow_units_attack"]
        else:
            cls.allow_units_attack = []

        # 解析属性加成
        if "allow_units_add" in d:
            cls.allow_units_add = {}
            items = d.get("allow_units_add", [])
            if not items:
                return

            # 如果是列表，每两个元素组成一对
            i = 0
            while i < len(items):
                if i + 1 >= len(items):
                    break
                try:
                    stat = str(items[i])
                    value = float(items[i + 1])
                    cls.allow_units_add[stat] = value
                    i += 2
                except (ValueError, IndexError):
                    i += 1

        # 解析近战溅射衰减
        if "mdg_splash_decay" in d:
            try:
                decay_str = d["mdg_splash_decay"]
                if "-" in decay_str:
                    min_val = float(decay_str.split("-")[0])
                    cls.mdg_splash_decay_min = min_val
                else:
                    cls.mdg_splash_decay_min = float(decay_str)
            except (ValueError, IndexError):
                warning(f"Invalid mdg_splash_decay format: {decay_str}")

        # 解析远程溅射衰减
        if "rdg_splash_decay" in d:
            try:
                decay_str = d["rdg_splash_decay"]
                if "-" in decay_str:
                    min_val = float(decay_str.split("-")[0])
                    cls.rdg_splash_decay_min = min_val
                else:
                    cls.rdg_splash_decay_min = float(decay_str)
            except (ValueError, IndexError):
                warning(f"Invalid rdg_splash_decay format: {decay_str}")

        # 解析 status_damage
        if "status_damage" in d:
            status_str = d["status_damage"]

            # 情况1: 统一设置两种伤害持续时间
            # 例如: "status_damage 2"
            if status_str.isdigit():
                duration = float(status_str)
                cls.mdg_status_duration = duration
                cls.rdg_status_duration = duration
                return

            # 情况2: 分别设置
            parts = status_str.split()
            i = 0
            while i < len(parts):
                if parts[i] == "melee_damage":
                    if i + 1 < len(parts) and parts[i + 1].replace(".", "").isdigit():
                        cls.mdg_status_duration = float(parts[i + 1])
                        i += 2
                    else:
                        i += 1
                elif parts[i] == "range_damage":
                    if i + 1 < len(parts) and parts[i + 1].replace(".", "").isdigit():
                        cls.rdg_status_duration = float(parts[i + 1])
                        i += 2
                    else:
                        i += 1
                else:
                    i += 1

        if "damage_seq" in d:
            seq_str = d["damage_seq"]

            # 解析攻击类型和次数
            match = re.search(r'(mdg|rdg)\s+(\d+)', seq_str)
            if match:
                damage_type = match.group(1)
                times = int(match.group(2))

                # 解析伤害序列
                damage_match = re.search(r'\(damage\s+([0-9\s]+)\)', seq_str)
                interval_match = re.search(r'\(interval\s+([\d\.]+)\)', seq_str)
                interval = float(interval_match.group(1)) if interval_match else 0.0
                base_prec = d.get(damage_type, 0)
                damages = None

                if damage_match:
                    damages = [int(x) * PRECISION for x in damage_match.group(1).split()]
                    times = len(damages)
                elif base_prec > 0 and times > 0:
                    per_shot = base_prec // times
                    remainder = base_prec % times
                    damages = [
                        per_shot + (1 if i < remainder else 0)
                        for i in range(times)
                    ]

                if damages and sum(damages) == base_prec:
                    if damage_type == "mdg":
                        cls.mdg_seq_times = times
                        cls.mdg_seq_damages = damages
                        cls.mdg_seq_interval = interval
                    else:
                        cls.rdg_seq_times = times
                        cls.rdg_seq_damages = damages
                        cls.rdg_seq_interval = interval

        # 解析近战目标
        mdg_targets_val = d.get("mdg_targets", "")
        if isinstance(mdg_targets_val, list):
            cls.mdg_targets = mdg_targets_val
        else:
            cls.mdg_targets = mdg_targets_val.replace(";", "").strip().split() or ["ground"]

        # 解析远程目标
        rdg_targets_val = d.get("rdg_targets", "")
        if isinstance(rdg_targets_val, list):
            cls.rdg_targets = rdg_targets_val
        else:
            cls.rdg_targets = rdg_targets_val.replace(";", "").strip().split() or ["ground"]
        
        # 解析自动武器切换设置
        if "auto_weapon_switch" in d:
            cls.auto_weapon_switch = int(d["auto_weapon_switch"]) == 1
        else:
            # 如果没有在rules.txt中明确设置，强制设为False
            cls.auto_weapon_switch = False
        
        # 解析武器切换策略
        if "weapon_switch_strategy" in d:
            value = d["weapon_switch_strategy"]
            # 如果是列表，取第一个元素
            if isinstance(value, list):
                value = value[0] if value else "distance"
            cls.weapon_switch_strategy = value
        
        # 解析武器优先级
        if "weapon_priority" in d:
            if isinstance(d["weapon_priority"], list):
                cls.weapon_priority = d["weapon_priority"]
            else:
                cls.weapon_priority = d["weapon_priority"].split()
    def _expand_is_a(self, is_a_list):
        """展开并记录所有继承关系"""
        if not is_a_list:
            return

        for base_type in is_a_list:
            if base_type not in self.expanded_is_a:
                self.expanded_is_a.add(base_type)
                # 递归处理基类的继承
                base_class = rules.get(base_type)
                if base_class and hasattr(base_class, 'is_a'):
                    self._expand_is_a(base_class.is_a)
    def next_free_number(self):
        numbers = [
            u.number
            for u in self.player.units
            if u.type_name == self.type_name and u is not self
        ]
        n = 1
        while n in numbers:
            n += 1
        return n
    def set_player(self, player):
        self.stop()
        self.cancel_all_orders(unpay=False)
        if self.player:
            self.player.remove(self)
        elif player:
            player.stats.add("produced", self.stat_type)
        self.player = player
        if player:
            player.add(self)
        if self.inside:
            for o in self.inside.objects:
                o.set_player(player)
    @classmethod
    def create_from_nowhere(cls):
        return cls.__new__(cls)

    def _parse_level_skill_pairs(self, attr_name):
        """Parse ``level skill [level skill ...]`` pairs from a unit attribute."""
        return CreatureAttributes._parse_level_skill_pairs_raw(
            getattr(self, attr_name, ()) or ()
        )

    @staticmethod
    def _parse_level_skill_pairs_raw(raw):
        if isinstance(raw, str):
            raw = raw.split()
        result = {}
        i = 0
        while i + 1 < len(raw):
            try:
                lvl = int(raw[i])
            except (ValueError, TypeError):
                i += 1
                continue
            skill = raw[i + 1]
            result.setdefault(lvl, []).append(skill)
            i += 2
        return result

    def _get_level_skills_map(self):
        """Skills granted automatically when the unit reaches each level."""
        return self._parse_level_skill_pairs("level_skills")

    def _get_learn_level_skills_map(self):
        """Minimum level required to learn each skill from a skill book."""
        return self._parse_level_skill_pairs("learn_level_skills")

    def _ensure_can_use_skill_list(self):
        if not hasattr(self, "can_use_skill") or self.can_use_skill is None:
            self.can_use_skill = []
        elif isinstance(self.can_use_skill, tuple):
            self.can_use_skill = list(self.can_use_skill)
        elif not isinstance(self.can_use_skill, list):
            self.can_use_skill = list(self.can_use_skill)

    def _skill_class(self, skill_name):
        from ..definitions import rules
        world = getattr(self, "world", None)
        if world is not None and hasattr(world, "unit_class"):
            cls = world.unit_class(skill_name)
            if cls is not None:
                return cls
        return rules.unit_class(skill_name)

    def _known_skill_names(self):
        """All skill ids the unit currently has (manual + auto sources, deduped)."""
        names = []
        seen = set()
        for seq in (
            getattr(self, "can_use_skill", ()) or (),
            getattr(self, "active_trigger_skills", ()) or (),
        ):
            for name in seq:
                if name and name not in seen:
                    seen.add(name)
                    names.append(name)
        return names

    def _skill_trigger_timing(self, skill_name, *, legacy_list_attr=None):
        """Return when an auto skill fires: on_hit / on_attack / on_attack_replace / on_damaged."""
        cls = self._skill_class(skill_name)
        if cls is not None:
            timing = getattr(cls, "trigger_timing", "on_hit") or "on_hit"
            return str(timing)
        if legacy_list_attr == "active_trigger_skills":
            return "on_hit"
        if legacy_list_attr == "attack_trigger_skills":
            return "on_attack"
        if legacy_list_attr == "attack_replace_skills":
            return "on_attack_replace"
        if legacy_list_attr == "passive_trigger_skills":
            return "on_damaged"
        return "on_hit"

    def iter_skills_with_trigger_timing(self, timing):
        """Yield learned/legacy skills that auto-fire at the given trigger point."""
        legacy_attr = {
            "on_hit": "active_trigger_skills",
            "on_attack": "attack_trigger_skills",
            "on_attack_replace": "attack_replace_skills",
            "on_damaged": "passive_trigger_skills",
        }.get(timing)
        seen = set()
        if legacy_attr:
            for name in getattr(self, legacy_attr, ()) or ():
                if name not in seen:
                    seen.add(name)
                    yield name
        for name in getattr(self, "can_use_skill", ()) or ():
            if name in seen:
                continue
            cls = self._skill_class(name)
            if cls is None or not getattr(cls, "auto_trigger", 0):
                continue
            skill_timing = getattr(cls, "trigger_timing", "on_hit") or "on_hit"
            if skill_timing == timing:
                seen.add(name)
                yield name

    def iter_auto_trigger_skill_names(self):
        """Skills that fire after a successful hit (legacy: active_trigger_skills)."""
        yield from self.iter_skills_with_trigger_timing("on_hit")

    def iter_attack_trigger_skill_names(self):
        """Skills that fire when an attack starts; normal attack still continues."""
        yield from self.iter_skills_with_trigger_timing("on_attack")

    def iter_attack_replace_skill_names(self):
        """Skills that fire when an attack starts and replace the normal attack."""
        yield from self.iter_skills_with_trigger_timing("on_attack_replace")

    def iter_passive_trigger_skill_names(self):
        """Skills that fire when this unit is hit by an enemy."""
        yield from self.iter_skills_with_trigger_timing("on_damaged")

    def iter_manual_skill_names(self):
        """Skills that may appear in the manual command menu."""
        seen = set()
        can_use = getattr(self, "can_use_skill", ()) or ()
        active = getattr(self, "active_trigger_skills", ()) or ()
        for name in can_use:
            if name in seen:
                continue
            cls = self._skill_class(name)
            if cls is None or getattr(cls, "manual_use", 1):
                seen.add(name)
                yield name
        for name in active:
            if name in seen:
                continue
            # Legacy: active_trigger_skills alone enables both auto and manual.
            seen.add(name)
            yield name

    def _required_level_for_skill(self, skill_name, item=None):
        """Minimum level to learn from a skill book (unit + item rules, strictest wins)."""
        reqs = []
        unit_req = None
        for lvl, skills in self._get_learn_level_skills_map().items():
            if skill_name in skills:
                unit_req = lvl if unit_req is None else max(unit_req, lvl)
        if unit_req is not None:
            reqs.append(unit_req)
        if item is not None:
            learn_level = getattr(item, "learn_level", 0) or 0
            try:
                learn_level = int(learn_level)
            except (TypeError, ValueError):
                learn_level = 0
            if learn_level > 0:
                reqs.append(learn_level)
            for lvl, skills in CreatureAttributes._parse_level_skill_pairs_raw(
                getattr(item, "learn_level_skills", ()) or ()
            ).items():
                if skill_name in skills:
                    reqs.append(lvl)
        if not reqs:
            return None
        return max(reqs)

    def _try_learn_skill(self, skill_name, *, item=None, notify=True):
        """Permanently learn a skill. Returns (ok, failure_reason)."""
        self._ensure_can_use_skill_list()
        if skill_name in self.can_use_skill:
            return False, "skill_already_known"
        req = self._required_level_for_skill(skill_name, item=item)
        if req is not None and self.level < req:
            return False, "skill_level_too_low"
        self.can_use_skill.append(skill_name)
        if notify:
            self.notify(f"skill_unlock,{skill_name},{self.id}")
        return True, None

    def _unlock_level_skills(self, level, *, notify=True):
        """Add skills defined for the given level to can_use_skill."""
        skills = self._get_level_skills_map().get(level, [])
        if not skills:
            return
        self._ensure_can_use_skill_list()
        for skill in skills:
            if skill not in self.can_use_skill:
                self.can_use_skill.append(skill)
                if notify:
                    self.notify(f"skill_unlock,{skill},{self.id}")

    def _apply_level_skills_up_to(self, level=None, *, notify=False):
        """Unlock all level_skills for levels up to and including level."""
        if level is None:
            level = self.level
        level_map = self._get_level_skills_map()
        if not level_map:
            return
        for lvl in sorted(l for l in level_map if l <= level):
            self._unlock_level_skills(lvl, notify=notify)

    def upgrade_to_player_level(self):
        """将单位升级到玩家的科技等级

        逐个应用所有可用科技的效果，确保单位拥有所有已研究科技的加成。
        支持原始的can_use以及新增的can_use_tech和can_use_skill属性。
        """
        # 如果单位没有玩家或者玩家没有升级，直接返回
        if not self.player or not hasattr(self.player, 'upgrades') or not self.player.upgrades:
            return

        debug(f"将单位 {self.type_name}({self.id}) 升级到玩家科技等级")

        # 收集单位可以使用的所有科技类型
        tech_sources = [
            ('can_use', getattr(self, 'can_use', [])),
            ('can_use_tech', getattr(self, 'can_use_tech', [])),
            ('can_use_skill', getattr(self, 'can_use_skill', []))
        ]

        # 对每一种科技类型进行处理
        for source_name, techs in tech_sources:
            if not techs:
                continue

            debug(f"处理 {source_name} 中的科技: {techs}")

            # 处理每一个科技
            for tech_name in techs:
                # 检查该科技是否已被研究
                if tech_name in self.player.upgrades:
                    # 获取科技等级
                    tech_level = self.player.level(tech_name)
                    debug(f"应用科技 {tech_name} (等级 {tech_level}) 到单位 {self.type_name}({self.id})")

                    # 应用科技效果
                    tech_class = rules.unit_class(tech_name)
                    if tech_class:
                        tech_class.upgrade_unit_to_player_level(self)
        
        # 升级单位装备的武器
        if hasattr(self, 'update_weapons'):
            self.update_weapons()
        
        # 升级单位装备的护甲
        if hasattr(self, 'update_armors'):
            self.update_armors()
    @actual_speed.setter
    def actual_speed(self, val):
        self._actual_speed = val