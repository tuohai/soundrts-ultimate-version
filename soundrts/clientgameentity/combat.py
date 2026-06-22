"""战斗相关模块 - 攻击、受伤、武器、战斗音效等"""

import random
import time

from ..definitions import style, rules
from ..lib.sound import distance


class EntityViewCombat:
    """EntityView的战斗相关方法"""

    def _get_battle_shout_volume(self, defender_units, attacker_units):
        """计算喊杀声的音量"""
        total_units = max(defender_units, attacker_units)
        volume_increase = min((total_units - self._min_units_for_shout) // self._units_per_volume, 
                            self._max_volume_increase)
        return self._base_volume + (volume_increase * 1)  # 每次增加1音量

    def _should_play_battle_shout(self, attacker_id, current_time):
        """判断是否应该播放喊杀音效,返回音量"""
        # 检查冷却时间
        if current_time - self.__class__._last_shout_time < self.__class__._shout_cooldown:
            return 0
            
        # 获取攻击者
        attacker = self.interface.dobjets.get(attacker_id)
        if not attacker:
            return 0
        
        # 位置与玩家健壮性校验
        place = getattr(self, 'place', None)
        if place is None:
            return 0
        
        # 计算双方参战单位数量（安全访问）
        defender_units = 0
        player = getattr(self, 'player', None)
        if player is not None and hasattr(player, 'units'):
            defender_units = sum(
                1 for u in player.units
                if getattr(u, 'place', None) is place and getattr(u, 'menace', 0)
            )
        
        attacker_units = 0
        att_player = getattr(attacker, 'player', None)
        if att_player is not None and hasattr(att_player, 'units'):
            attacker_units = sum(
                1 for u in att_player.units
                if getattr(u, 'place', None) is place and getattr(u, 'menace', 0)
            )
                            
        # 当任意一方单位数量达到要求时触发
        if (defender_units >= self.__class__._min_units_for_shout or 
            attacker_units >= self.__class__._min_units_for_shout):
            return self._get_battle_shout_volume(defender_units, attacker_units)
        return 0

    def _set_battle_mode(self, is_battle):
        """设置战斗模式并播放相应音乐
        
        Args:
            is_battle: 是否处于战斗状态
        """
        from soundrts.lib import sound
        
        # 获取当前音乐状态
        status = sound.get_music_status()
        
        # 如果状态相同，不做改变
        if status["in_battle"] == is_battle:
            return
            
        # 根据状态播放相应音乐
        if is_battle:
            # 获取地图战斗音乐（如果存在）
            map_battle_music = None
            if hasattr(self.interface, '_world_reference') and self.interface._world_reference:
                map_battle_music = getattr(self.interface._world_reference, 'map_battle_music', None)
            sound.play_battle_music(map_battle_music)
        else:
            # 在停止战斗音乐前，再次检查视野内是否还有敌人
            # 中立电脑（neutral）的单位是被动 creep，不算"还在战斗"——
            # 否则地图上常驻的 creep 会让音乐永远停不下来。
            has_enemies = False

            # 遍历所有可见区域
            for place in self.interface.scouted_squares:
                # 检查该区域中的所有对象
                for obj in place.objects:
                    # 检查是否是敌方单位（且非中立 creep）
                    if (hasattr(obj, 'player') and obj.player and
                        self.interface.player.player_is_an_enemy(obj.player) and
                        not getattr(obj.player, 'neutral', False)):
                        has_enemies = True
                        break
                
                if has_enemies:
                    break
            
            # 只有在视野内确实没有敌人时才停止战斗音乐
            if not has_enemies:
                sound.stop_battle_music()

    def _check_battle_status_for_music(self):
        """检查当前地区是否还有战斗，如果没有则停止战斗音乐"""
        # 检查此区域是否还有敌对单位
        from soundrts.lib import sound
        
        # 如果当前地点没有战斗单位，检查是否要停止战斗音乐
        if hasattr(self, 'place') and self.place:
            # 获取音乐状态
            status = sound.get_music_status()
            
            # 如果当前不在战斗音乐状态，不需要检查
            if not status["in_battle"]:
                return
                
            # 检查该区域中是否有敌方单位
            # 中立 creep 不算"还在战斗"，与 _set_battle_mode 的过滤规则一致。
            has_enemies = False

            for obj in self.place.objects:
                # 检查是否是敌方单位（且非中立 creep）
                if (hasattr(obj, 'player') and obj.player and
                    self.interface.player.player_is_an_enemy(obj.player) and
                    not getattr(obj.player, 'neutral', False)):
                    has_enemies = True
                    break
            
            # 如果当前区域没有敌人，将检查委托给GameInterface._check_battle_status方法
            if not has_enemies:
                # 将检查委托给GameInterface._check_battle_status方法
                self.interface._check_battle_status(force_check=True)

    def unit_attacked_alert(self):
        self.interface.alert_squares[self.place] = time.time()
        self.interface.squares_alert_if_needed()
        if (
            self.interface.previous_unit_attacked_alert is None
            or time.time() > self.interface.previous_unit_attacked_alert + 10
        ):
            self.launch_event_style("alert", alert=True)
            self.interface.previous_unit_attacked_alert = time.time()

    def _is_melee_attack(self, attacker_type, attacker_id=None):
        """判断是否为近战攻击，考虑当前装备的武器"""
        # 首先尝试通过攻击者的当前武器来判断
        if attacker_id:
            attacker = self.interface.dobjets.get(attacker_id)
            if attacker and hasattr(attacker, 'model') and hasattr(attacker.model, 'current_weapon'):
                current_weapon = getattr(attacker.model, 'current_weapon', None)
                if current_weapon:
                    # 检查武器是否有远程攻击音效，如果有则认为是远程武器
                    if (style.has(current_weapon, "launch_rdg") or 
                        style.has(current_weapon, "rdg_hit") or 
                        style.has(current_weapon, "rdg_hit_lv_1")):
                        return False  # 远程攻击
                    # 检查武器是否有近战攻击音效，如果有则认为是近战武器
                    elif (style.has(current_weapon, "mdg_hit") or 
                          style.has(current_weapon, "mdg_hit_lv_1")):
                        return True  # 近战攻击
        
        # 如果无法通过武器判断，回退到原来的单位类型判断
        unit = rules.unit_class(attacker_type)
        # 如果单位有远程攻击范围，则认为是远程单位
        if hasattr(unit, 'rdg_range') and unit.rdg_range > 0:
            return False
        return True  # 默认为近战

    def _get_melee_hit_sound(self, attacker_type, attacker_id=None):
        """获取近战命中音效"""
        # 尝试从攻击者的武器中获取音效
        weapon_sound = self._get_weapon_sound(attacker_type, "mdg_hit", attacker_id)
        if weapon_sound:
            return weapon_sound
        
        # 如果武器没有音效，使用单位的音效
        # 1. 先查找针对特定单位类型的音效
        vs_sound = self._get_hit_vs_sound(attacker_type, "mdg_hit_vs")
        if vs_sound:
            return vs_sound
            
        # 2. 再查找通用近战命中音效
        try:
            s = style.get(attacker_type, "mdg_hit")
            if s:
                return random.choice(s)
        except:
            pass
        
        return None

    def _get_ranged_hit_sound(self, attacker_type, attacker_id=None):
        """获取远程命中音效"""
        # 尝试从攻击者的武器中获取音效
        weapon_sound = self._get_weapon_sound(attacker_type, "rdg_hit", attacker_id)
        if weapon_sound:
            return weapon_sound
        
        # 如果武器没有音效，使用单位的音效
        # 1. 先查找针对特定单位类型的音效
        vs_sound = self._get_hit_vs_sound(attacker_type, "rdg_hit_vs")
        if vs_sound:
            return vs_sound
            
        # 2. 再查找通用远程命中音效
        try:
            s = style.get(attacker_type, "rdg_hit")
            if s:
                return random.choice(s)
        except:
            pass
        
        return None

    def _get_level_hit_sound(self, attacker_type, level, is_melee, attacker_id=None):
        """获取等级相关命中音效"""
        prefix = "mdg" if is_melee else "rdg"
        
        # 尝试从攻击者的武器中获取音效
        weapon_sound = self._get_weapon_sound(attacker_type, f"{prefix}_hit_lv_{level}", attacker_id)
        if weapon_sound:
            return weapon_sound
        
        # 如果武器没有等级音效，尝试普通武器音效
        weapon_sound = self._get_weapon_sound(attacker_type, f"{prefix}_hit", attacker_id)
        if weapon_sound:
            return weapon_sound
        
        # 如果武器没有音效，使用单位的音效
        # 1. 先获取普通等级音效和普通命中音效作为基础
        base_level_sound = None
        base_hit_sound = None
        
        try:
            s = style.get(attacker_type, f"{prefix}_hit_lv_{level}")
            if s:
                base_level_sound = random.choice(s)
        except:
            pass
            
        try:
            s = style.get(attacker_type, f"{prefix}_hit")
            if s:
                base_hit_sound = random.choice(s)
        except:
            pass
            
        # 2. 检查特殊等级音效
        vs_sound = self._get_hit_vs_sound(attacker_type, f"{prefix}_hit_lv_{level}_vs")
        if vs_sound:
            return vs_sound
            
        # 3. 如果没有特殊等级音效，检查普通特定音效
        vs_sound = self._get_hit_vs_sound(attacker_type, f"{prefix}_hit_vs")
        if vs_sound:
            return vs_sound
            
        # 4. 如果没有任何特定音效，优先使用普通等级音效，其次是普通命中音效
        return base_level_sound or base_hit_sound

    def _target_hit_vs_types(self):
        result = [self.type_name]
        result.extend(t for t in getattr(self, "expanded_is_a", ()) if t not in result)
        try:
            buffs = getattr(self.model, "_buffs", None) or ()
        except AttributeError:
            buffs = ()
        for buff in buffs:
            buff_type = getattr(buff, "type_name", None)
            if buff_type is None and isinstance(buff, tuple) and buff:
                buff_type = buff[0]
            if buff_type and buff_type not in result:
                result.append(buff_type)
        return result

    def _get_hit_vs_sound(self, attacker_type, sound_attr):
        try:
            vs_sounds = style.get(attacker_type, sound_attr)
            if vs_sounds and len(vs_sounds) >= 2 and vs_sounds[0] in self._target_hit_vs_types():
                return random.choice(vs_sounds[1:])
        except:
            pass
        return None

    def _get_weapon_inheritance_chain(self, weapon_type):
        """获取武器的继承链，用于查找音效
        
        Args:
            weapon_type: 武器类型名称
            
        Returns:
            list: 继承链列表，从具体类型到基类
        """
        try:
            inheritance_chain = [weapon_type]
            added_types = {weapon_type}
            
            def add_parents(type_name):
                # 直接访问 rules._dict 来获取武器定义
                weapon_def = rules._dict.get(type_name)
                if weapon_def and "is_a" in weapon_def:
                    parents = []
                    is_a = weapon_def['is_a']
                    if isinstance(is_a, str):
                        parents = [is_a]
                    elif isinstance(is_a, (list, tuple)):
                        parents = list(is_a)
                    
                    # 先添加直接父类
                    current_level_parents = []
                    for parent in parents:
                        if parent not in added_types:
                            inheritance_chain.append(parent)
                            added_types.add(parent)
                            current_level_parents.append(parent)
                    
                    # 然后递归添加父类的父类
                    for parent in current_level_parents:
                        add_parents(parent)
        
            add_parents(weapon_type)
            
        except (AttributeError, ImportError):
            # 如果无法获取继承信息，只使用原始类型
            pass
        
        return inheritance_chain

    def _get_weapon_sound_from_inheritance_chain(self, weapon_name, sound_param):
        """从武器继承链中查找音效
        
        Args:
            weapon_name: 武器名称
            sound_param: 音效参数名称（如'weapon_switched'）
            
        Returns:
            list: 音效ID列表，如果没有找到则返回None
        """
        # 获取武器继承链
        inheritance_chain = self._get_weapon_inheritance_chain(weapon_name)
        
        # 按继承链顺序查找音效
        for weapon_type in inheritance_chain:
            if style.has(weapon_type, sound_param):
                weapon_sound_id = style.get(weapon_type, sound_param)
                # style.get()返回的是列表，返回整个列表以支持随机播放
                if weapon_sound_id and len(weapon_sound_id) > 0:
                    return weapon_sound_id
        
        return None

    def _get_weapon_sound(self, attacker_type, sound_type, attacker_id=None):
        """从攻击者的当前装备武器中获取音效
        
        Args:
            attacker_type: 攻击者类型
            sound_type: 音效类型 (如 "mdg_hit", "rdg_hit", "launch_mdg" 等)
            attacker_id: 攻击者ID（可选）
            
        Returns:
            音效ID或None
        """
        # 尝试通过攻击者ID获取攻击者单位对象
        attacker = None
        if attacker_id:
            attacker = self.interface.dobjets.get(attacker_id)
        
        # 如果没有攻击者ID，尝试通过类型获取同类型的单位
        if not attacker:
            for unit in self.interface.dobjets.values():
                if hasattr(unit, 'type_name') and unit.type_name == attacker_type:
                    attacker = unit
                    break
        
        # 如果找不到攻击者单位，返回None
        if not attacker:
            return None
        
        # 获取攻击者当前装备的武器
        if not hasattr(attacker, 'model') or not hasattr(attacker.model, 'current_weapon'):
            return None
        
        current_weapon = getattr(attacker.model, 'current_weapon', None)
        if not current_weapon:
            return None
        
        # 从当前武器定义中获取音效，支持继承链
        weapon_type = current_weapon
        
        # 1. 先尝试查找针对特定目标类型的武器音效（vs类型）
        vs_sound_type = f"{sound_type}_vs"
        weapon_vs_sound_list = self._get_weapon_sound_from_inheritance_chain(weapon_type, vs_sound_type)
        if weapon_vs_sound_list and len(weapon_vs_sound_list) >= 2:
            target_type = weapon_vs_sound_list[0]
            # 检查目标类型及其继承链
            if (self.type_name == target_type or 
                target_type in getattr(self, 'expanded_is_a', [])):
                # 返回vs音效列表中除了第一个元素（目标类型）之外的音效
                sound_choices = weapon_vs_sound_list[1:]
                if sound_choices:
                    return random.choice(sound_choices)
        
        # 2. 如果没有找到vs音效，查找通用武器音效
        weapon_sound_list = self._get_weapon_sound_from_inheritance_chain(weapon_type, sound_type)
        if weapon_sound_list:
            # 从音效列表中随机选择一个返回
            return random.choice(weapon_sound_list)
        
        return None

    def _get_dodge_sound(self, attacker_type, is_melee):
        """获取闪避音效"""
        prefix = "mdg" if is_melee else "rdg"
        
        # 1. 先查找针对特定攻击者类型的闪避音效
        try:
            vs_sounds = style.get(self.type_name, f"{prefix}_dodge_vs")
            if vs_sounds and len(vs_sounds) >= 2:
                target_type = vs_sounds[0]
                sound_id = vs_sounds[1]
                # 检查攻击者类型及其继承链
                if attacker_type == target_type or target_type in getattr(self, 'expanded_is_a', []):
                    return sound_id
        except:
            pass
        
        # 2. 再查找通用闪避音效
        try:
            s = style.get(self.type_name, f"{prefix}_dodge")
            if s:
                return random.choice(s)
        except:
            pass
        
        return None