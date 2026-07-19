"""事件处理模块 - 各种on_开头的事件处理方法"""

import random
import time
import pygame

from .. import config
from ..clientmedia import voice
from ..clientgameorder import substitute_args
from ..definitions import style
from ..lib import game_tts
from ..lib.log import exception
from ..lib.msgs import nb2msg, nb2msg_float
from .. import msgparts as mp
from ..attributes.utils import get_stat_tts_name
from .properties import summary_omit_single_count_at_death
from .battle_shout_audio import clash_unit_count

# Player economy / production feedback → primary library (not secondary).
_PRIMARY = dict(tts_channel=game_tts.PRIMARY)


class EntityViewEvents:
    """EntityView的事件处理相关方法"""

    def on_disappear(self):
        """处理单位消失的音效"""
        self.launch_event_style("disappear")

    def on_death(self):
        """处理单位死亡的音效"""
        self.launch_event_style("death")
        falling_sound = self._get_falling_sound()
        
        if falling_sound:
            falling_delay = 0
            # 检查是否有延迟配置
            delay_config = self.get_style("falling_delay")
            if delay_config and len(delay_config) > 0:
                try:
                    falling_delay = float(delay_config[0])
                except (ValueError, TypeError):
                    falling_delay = 0
                    
            if falling_delay > 0:
                # 创建一个唯一的事件ID用于倒地音效
                falling_event_id = pygame.USEREVENT + 100 + random.randint(1, 9999)
                
                # 将回调函数存储在接口对象中
                self.interface._falling_callbacks[falling_event_id] = {
                    'sound': random.choice(falling_sound),
                    'obj': self
                }
                
                # 设置定时器
                pygame.time.set_timer(falling_event_id, int(falling_delay * 1000), True)
            else:
                # 如果没有延迟，立即播放
                self.launch_event(random.choice(falling_sound))

    def notify(self, event_and_args):
        """处理实体事件通知"""
        e_a = event_and_args.split(",")
        event = e_a[0]
        args = e_a[1:]
        
        # 特殊处理攻击音效
        if event in ["launch_mdg", "launch_rdg"]:
            # 如果有额外参数（单位类型和ID），使用这些参数
            if len(args) >= 2:
                unit_type = args[0]
                unit_id = args[1]
                # 尝试从武器中获取音效
                weapon_sound = self._get_weapon_sound(unit_type, event)
                if weapon_sound:
                    self.launch_event(weapon_sound)
                else:
                    # 如果武器没有音效，使用单位的音效
                    self.launch_event_style(event)
            else:
                # 使用自己的音效
                self.launch_event_style(event)
        # 处理资源生产完成通知
        elif event.startswith("produced_"):
            # 例如: produced_1,50 (生产了50个金子)
            resource_type = "resource" + event.split("_")[1]
            qty = int(args[0]) if args and args[0].isdigit() else 0
            self.on_produced(resource_type, qty)
        # 处理资源生产完成事件（只播放声音，不显示提示）
        elif event == "resource_complete":
            self.on_resource_complete()
        # 处理升级事件
        elif event == "level_up":
            # 检查是否有参数（单位类型、ID、等级）
            if len(args) >= 3:
                unit_type, unit_id, level = args[0], args[1], args[2]
                self.on_level_up(unit_type, unit_id, int(level))
            else:
                # 如果没有参数，只播放音效
                self.launch_event_style("level_up", alert=True, priority=10)
        # 处理复活事件
        elif event == "resurrected":
            # 确保参数完整
            if len(args) >= 2:
                unit_type, unit_id = args[0], args[1]
                self.on_resurrected(unit_type, unit_id)
            else:
                # 如果参数不足，使用默认值
                self.launch_event_style("resurrected")
        # 处理具有对应on_方法的事件
        elif hasattr(self, "on_" + event):
            handler = getattr(self, "on_" + event)
            # 确保handler不是None并且可调用
            if handler is not None and callable(handler):
                # 传递所有参数
                handler(*args)
            else:
                # 如果handler无效，使用事件样式
                self.launch_event_style(event)
        # 默认情况 - 使用事件样式
        else:
            self.launch_event_style(event)

    def on_level_up(self, unit_type, unit_id, level):
        """处理单位升级事件"""
        # 播放升级音效
        self.launch_event_style("level_up", alert=True, priority=10)
        
        # 只为己方单位或盟友单位播放升级通知
        if self.player == self.interface.player or self.player in self.interface.player.allied:
            # 播放单位名称 + "等级" + 数字
            msg = []
            title = style.get(self.type_name, "title")
            if isinstance(title, list):
                msg.extend(title)
            else:
                msg.append(title)
            msg.append(4605)  # "等级"消息ID  
            msg.extend(nb2msg(level))
            
            # 使用voice.info播放消息
            voice.info(msg)

    def _transfer_selection_after_morph(self, new_id):
        from ..clientgame.game_unit_control import transfer_group_selection_on_upgrade
        transfer_group_selection_on_upgrade(self.interface, self.id, new_id)

    def on_upgrade_to(self, new_id):
        # 播放升级音效（不需要参数的版本）
        self.launch_event_style("level_up", alert=True, priority=10)
        self._transfer_selection_after_morph(new_id)

    def on_change_to(self, new_id):
        self.launch_event_style("change_to", alert=True, priority=10)
        self._transfer_selection_after_morph(new_id)

    def on_resurrected(self, unit_type, unit_id):
        """处理单位复活事件"""
        # 播放复活音效
        self.launch_event_style("resurrected")
        
        # 只为己方单位或盟友单位播放复活通知
        if self.player == self.interface.player or self.player in self.interface.player.allied:
            # 直接使用voice.item播放复活通知，而不是发送msg命令
            msg = []
            title = style.get(self.type_name, "title")
            if isinstance(title, list):
                msg.extend(title)
            msg.append(4606)  # RESURRECTED 消息ID
            
            # 使用voice.item直接播放消息
            voice.item(msg)

    def on_collision(self):
        self.launch_event_style("blocked")  # "blocked" is more precise than "collision"

    def on_attack(self):
        # 获取当前时间
        current_time = int(time.time() * 1000)
        
        # 判断目标是否为自己人，若是则不播放战斗音乐
        # 这里假设self.attack_target为当前攻击目标（如有不同请调整）
        target = getattr(self, 'attack_target', None)
        if target and hasattr(target, 'player'):
            # 判断是否同一玩家、同一阵营，或攻击者/目标任一方是中立 creep。
            # 中立 creep 的战斗（玩家打 creep 或 creep 反击）不算"剧情战"，
            # 不应触发战斗音乐——与"中立 = 被动 creep"的整体语义一致。
            target_player = target.player
            is_neutral_involved = (
                getattr(target_player, 'neutral', False) or
                getattr(getattr(self, 'player', None), 'neutral', False)
            )
            if (target_player == self.player or
                not self.interface.player.player_is_an_enemy(target_player) or
                is_neutral_involved):
                pass  # 不播放战斗音乐
            else:
                self._set_battle_mode(True)
        else:
            self._set_battle_mode(True)
        
        # 检查是否应该播放攻击音效（间隔控制）
        if current_time - self.__class__._last_attack_sound_time < self.__class__._attack_sound_cooldown:
            return
        
        # 播放攻击音效
        self.launch_event_style("attack")
        self.__class__._last_attack_sound_time = current_time

    def on_wounded(self, attacker_type, attacker_id, level, is_crit="0", is_charge="0"):
        current_time = int(time.time() * 1000)
        self._play_layered_battle_shouts(attacker_id, current_time)
        
        # 触发战斗音乐（受到攻击时），但攻击者是自己人时不播放
        attacker = self.interface.dobjets.get(attacker_id)
        if attacker and hasattr(attacker, 'player'):
            # 判断是否同一玩家、同一阵营，或攻击者/被攻击者任一方是中立 creep。
            # 中立 creep 的战斗不应触发战斗音乐（与 on_attack 一致）。
            attacker_player = attacker.player
            is_neutral_involved = (
                getattr(attacker_player, 'neutral', False) or
                getattr(getattr(self, 'player', None), 'neutral', False)
            )
            if (attacker_player == self.player or
                not self.interface.player.player_is_an_enemy(attacker_player) or
                is_neutral_involved):
                pass  # 不播放战斗音乐
            else:
                self._set_battle_mode(True)
        else:
            self._set_battle_mode(True)
        
        if self.player == self.interface.player:
            self.unit_attacked_alert()
        
        # 1. 确定是近战还是远程攻击
        is_melee = self._is_melee_attack(attacker_type, attacker_id)

        # 2. 获取攻击等级
        try:
            level = int(level)
        except (ValueError, TypeError):
            level = 0
        
        # 转换暴击标志为布尔值
        is_crit = is_crit == "1"
        
        # 转换冲锋标志为布尔值
        is_charge = is_charge == "1"
        attacker_view = self.interface.dobjets.get(attacker_id)
        clash_count = clash_unit_count(self, attacker_view, self.interface)
        
        # 如果是冲锋攻击，优先播放冲锋攻击音效
        if is_charge:
            # 检查是否有冲锋攻击音效
            charge_sound = None
            if is_melee:
                charge_sound = style.get(attacker_type, "charge_mdg_hit")
            else:
                charge_sound = style.get(attacker_type, "charge_rdg_hit")
                
            # 播放冲锋攻击音效
            if charge_sound:
                self.launch_event(random.choice(charge_sound))
                self._play_shout_event(attacker_id, clash_count, burst_cap=1)
            else:
                # 如果没有特定的冲锋攻击音效，使用通用的攻击音效
                if is_melee:
                    hit_sound = self._get_melee_hit_sound(attacker_type, attacker_id)
                else:
                    hit_sound = self._get_ranged_hit_sound(attacker_type, attacker_id)
                
                if hit_sound:
                    self.launch_event(hit_sound)
        else:
            # 3. 根据等级决定播放哪个音效
            if level > 0:
                # 播放等级音效
                level_sound = self._get_level_hit_sound(attacker_type, level, is_melee, attacker_id)
                if level_sound:
                    self.launch_event(level_sound)
            else:
                # 播放基础音效
                if is_melee:
                    hit_sound = self._get_melee_hit_sound(attacker_type, attacker_id)
                else:
                    hit_sound = self._get_ranged_hit_sound(attacker_type, attacker_id)
                
                if hit_sound:
                    self.launch_event(hit_sound)
                
        # 如果是暴击，播放暴击音效
        if is_crit:
            self.launch_event("critical_hit")
            self._play_shout_event(attacker_id, clash_count, burst_cap=1)

        # 4. 显示攻击效果
        if self.interface.display_is_active and attacker_id in self.interface.dobjets:
            self.interface.grid_view.display_attack(attacker_id, self)

    def on_flee(self):
        self.launch_event_style("flee", alert=True)
        # 检查是否需要停止战斗音乐
        self._check_battle_status_for_music()

    def on_store(self, resource_type):
        self.launch_event_style(f"store_{resource_type}")

    def on_order_ok(self):
        if self.player is not self.interface.player:
            return
        self.launch_event_style("order_ok", alert=True)

    def on_order_impossible(self, reason=None, *extra):
        if self.player is not self.interface.player:
            return
        self.launch_event_style("order_impossible", alert=True)
        if reason is not None:
            # 确保reason是字符串类型而不是列表
            if isinstance(reason, list):
                reason = str(reason[0]) if reason else ""
            from ..clientgame.build_field_voice import (
                voice_missing_build_field,
                voice_missing_deposit,
            )
            if reason == "passable_units_denied" and extra:
                unit_type = extra[0]
                msg = []
                title = style.get(unit_type, "title", warn_if_not_found=False)
                if title:
                    if isinstance(title, list):
                        msg.extend(title)
                    else:
                        msg.append(title)
                denied = style.get(
                    "messages", "passable_units_denied", warn_if_not_found=False
                )
                if denied:
                    if isinstance(denied, list):
                        msg.extend(denied)
                    else:
                        msg.append(denied)
                if msg:
                    voice.info(msg)
                return
            if not voice_missing_build_field(reason) and not voice_missing_deposit(reason):
                voice.info(style.get("messages", reason))

    def on_production_deferred(self):
        voice.info(style.get("messages", "production_deferred"))

    def on_win_fight(self):
        self.launch_event_style("win_fight", alert=True)
        self.interface.units_alert_if_needed()

    def on_lose_fight(self):
        self.launch_event_style("lose_fight", alert=True)
        self.interface.units_alert_if_needed(place=self.place)

    def on_death_by(self, attacker_id):
        attacker = self.interface.dobjets.get(attacker_id)
        if self.player is self.interface.player:
            self.interface.lost_units.append(
                [
                    self.short_title,
                    self.place,
                    summary_omit_single_count_at_death(self.model),
                ]
            )
        if getattr(attacker, "player", None) is self.interface.player:
            self.interface.neutralized_units.append(
                [
                    self.short_title,
                    self.place,
                    summary_omit_single_count_at_death(self.model),
                ]
            )  # TODO: "de " self.player.name
        friends = [
            u for u in self.player.units if u.place is self.place and u.id != self.id
        ]
        friend_soldiers = [u for u in friends if u.menace]
        # two cases requires an alert:
        # - the last soldier died (no more protection)
        # - the last "non soldier" unit died (no more unit at all)
        if not friend_soldiers and self.menace or not friends:
            if self.player == self.interface.player:
                self.on_lose_fight()
            if getattr(attacker, "player", None) == self.interface.player:
                attacker.on_win_fight()
                
            # 检查是否需要停止战斗音乐
            self._check_battle_status_for_music()

    def on_dodge(self, attacker_type, is_melee):
        """处理闪避事件"""
        # 将字符串转换为布尔值 - 更宽松的判断
        is_melee = str(is_melee).lower() in ('true', '1', 'yes')
        
        # 获取闪避音效
        dodge_sound = self._get_dodge_sound(attacker_type, is_melee)
        if dodge_sound:
            self.launch_event(dodge_sound)

    def on_missed(self, attacker_type, is_melee):
        """处理被打空事件"""
        # 将字符串转换为布尔值 - 更宽松的判断
        is_melee = str(is_melee).lower() in ('true', '1', 'yes')
        
        # 获取打空音效
        if is_melee:
            # 尝试从攻击者的武器中获取音效
            weapon_sound = self._get_weapon_sound(attacker_type, "mdg_missed")
            if weapon_sound:
                self.launch_event(weapon_sound)
                return
            
            # 如果武器没有音效，使用单位的音效
            s = style.get(attacker_type, "mdg_missed")  # 获取攻击者的近战落空音效
        else:
            # 尝试从攻击者的武器中获取音效
            weapon_sound = self._get_weapon_sound(attacker_type, "rdg_missed")
            if weapon_sound:
                self.launch_event(weapon_sound)
                return
            
            # 如果武器没有音效，使用单位的音效
            s = style.get(attacker_type, "rdg_missed")  # 获取攻击者的远程落空音效
        
        if s:
            self.launch_event(random.choice(s))

    def on_exhausted(self):
        self.launch_event_style("exhausted")
        if "resource_exhausted" in config.verbosity:
            voice.info(self.title + mp.EXHAUSTED)

    def on_produced(self, resource_type, qty):
        """处理资源生产完成"""
        if self.player is not self.interface.player:
            return
            
        # 获取资源类型的本地化名称
        resource_title = style.get("parameters", f"{resource_type}_title")
        
        # 播放生产完成的提示音效
        self.launch_event_style("production", alert=True)
        
        # 发送通知消息
        if "resources_produced" in config.verbosity:
            voice.info(substitute_args(
                style.get("produced_%s" % resource_type, title="%s"),
                [qty]
            ))
            
        # 发送菜单更新通知
        self.interface.send_menu_alerts_if_needed()

    def on_completeness(self, s):  # building train or upgrade
        self.launch_event_style("production")
        self.launch_event_style("proportion_%s" % s)
        
        # 为资源生产进度添加语音提示
        if hasattr(self, "is_producing") and self.is_producing and s.isdigit():
            progress = int(s)
            if progress in [2, 5, 7]:  # 在20%, 50%, 70%的时候播放进度提示
                if "production_progress" in config.verbosity:
                    voice.info(mp.PRODUCTION + str(progress * 10) + mp.PERCENT)

    def on_complete(self, *args):
        if self.player is not self.interface.player:
            return
        self.launch_event_style("complete", alert=True)
        if "unit_complete" in config.verbosity:
            from ..clientgamenews import must_be_said
            if must_be_said(self.number):
                # 检查是否有数量参数（多单位训练的情况）
                count = 1
                try:
                    # 优先使用直接传递的参数
                    if args and args[0].isdigit():
                        count = int(args[0])
                    # 如果没有直接参数，尝试使用存储的notify_args
                    elif hasattr(self.model, "notify_args") and len(self.model.notify_args) > 0 and self.model.notify_args[0].isdigit():
                        count = int(self.model.notify_args[0])
                except (ValueError, AttributeError, IndexError):
                    # 如果参数处理出错，使用默认值1
                    count = 1
                    
                # 如果是多个单位，在标题前添加数量
                if count > 1:
                    # 构建带数量的标题
                    title_with_count = nb2msg(count) + self.title
                    voice.info(
                        substitute_args(self.get_style("complete_msg"), [title_with_count]),
                        **_PRIMARY,
                    )
                else:
                    voice.info(
                        substitute_args(self.get_style("complete_msg"), [self.title]),
                        **_PRIMARY,
                    )
        self.interface.send_menu_alerts_if_needed()  # not necessary for "on_repair_complete" (if it existed)
        
    def on_resource_complete(self):
        """资源生产完成事件处理，只播放声音，不显示提示"""
        if self.player is not self.interface.player:
            return
        # 只播放声音，不显示提示信息
        self.launch_event_style("complete", alert=False)
        # 不需要调用send_menu_alerts_if_needed，避免菜单变化提示
    
    def on_qty_update(self, qty):
        """更新资源点显示的资源量"""
        try:
            # 更新模型中的数量
            if hasattr(self.model, "qty"):
                self.model.qty = int(qty)
            # 更新建筑物中的资源量
            elif hasattr(self.model, "resource_qty"):
                self.model.resource_qty = int(qty)
        except (ValueError, AttributeError):
            pass
    
    def on_research_complete(self):
        voice.info(self.get_style("research_complete_msg"), **_PRIMARY)
        self.interface.send_menu_alerts_if_needed()

    def on_upgrade_complete(self):
        voice.info(self.get_style("upgrade_complete_msg"), **_PRIMARY)
        self.interface.send_menu_alerts_if_needed()

    def on_added(self):
        self.launch_event_style("added", alert=True)
        if "unit_added" in config.verbosity:
            from ..clientgamenews import must_be_said
            if must_be_said(self.number):
                voice.info(
                    substitute_args(self.get_style("added_msg"), [self.ext_title]),
                    **_PRIMARY,
                )

    def on_placed(self):
        """Play sound when a building site is placed."""
        if self.type_name != "buildingsite":
            return
        building_type = getattr(self, "type", None)
        if building_type is None:
            return
        st = style.get(building_type.type_name, "placed", warn_if_not_found=False)
        if st:
            self.launch_event(random.choice(st))

    def on_buff(self, event, buff, msg=None):
        st = style.get(buff, event)
        if st:
            s = random.choice(st)
            self.launch_event(s)
        
        # 当添加或删除buff时，不播报buff名称，只播报效果信息（如果有）
        if event in ["add", "del"] and self.player is self.interface.player:
            if msg:
                # 有具体效果信息时，播报效果
                localized_msg = self._localize_buff_message(msg)
                if isinstance(localized_msg, list):
                    voice.info(localized_msg)
                else:
                    voice.info([localized_msg])
            # 注意：不再播报buff的title（名称）
        elif msg and self.player is self.interface.player:
            # 处理属性本地化，将英文属性名转换为中文
            localized_msg = self._localize_buff_message(msg)
            # 如果localized_msg是一个列表，直接传递，否则包装为列表
            if isinstance(localized_msg, list):
                voice.info(localized_msg)
            else:
                voice.info([localized_msg])

    def _localize_buff_message(self, msg):
        """将 buff 消息中的属性名替换为 TTS 消息 ID（语言由 tts.txt 决定）。"""
        if not msg:
            return msg

        pairs = EntityViewEvents._parse_buff_stat_pairs(msg)
        if not pairs:
            return [msg]

        result = []
        for index, (stat_name, value_part) in enumerate(pairs):
            result.extend(EntityViewEvents._format_buff_stat_bonus(stat_name, value_part))
            if index + 1 < len(pairs):
                result.extend(mp.COMMA)
        return result

    @staticmethod
    def _parse_buff_stat_pairs(msg):
        """解析 buff 消息中的属性加成，例如 heal_level +1 heal_cd +7.5。"""
        parts = msg.split()
        pairs = []
        index = 0
        while index < len(parts):
            stat_name = parts[index]
            if index + 1 < len(parts) and parts[index + 1][:1] in "+-":
                pairs.append((stat_name, parts[index + 1]))
                index += 2
            else:
                index += 1
        return pairs

    @staticmethod
    def _format_buff_stat_bonus(stat_name, value_part):
        """格式化单个属性加成的 TTS 播报。"""
        stat_msg = get_stat_tts_name(stat_name)
        if isinstance(stat_msg, list):
            result = list(stat_msg)
        else:
            result = [str(stat_msg)]

        try:
            if value_part[:1] in "+-":
                sign = value_part[0]
                number = float(value_part[1:])
                result.append(sign)
                if number == int(number):
                    result.extend(nb2msg(int(number)))
                else:
                    result.extend(nb2msg_float(number))
                return result
        except (ValueError, IndexError):
            pass

        result.append(value_part)
        return result

    def on_cooldown_end(self, skill):
        if self.player is self.interface.player:
            st = style.get(skill, "cooldown_end")
            if st:
                s = random.choice(st)
                self.launch_event(s)

    def on_skill_ready(self, skill):
        """Play a skill-specific ready sound when its preparation starts."""
        st = style.get(skill, "ready", warn_if_not_found=False)
        if st:
            self.launch_alert(random.choice(st))

    def on_skill_triggered(self, skill, target_id=None):
        """Play the triggered sound for an automatic skill, falling back to alert."""
        st = style.get(skill, "triggered", warn_if_not_found=False)
        if not st:
            st = style.get(skill, "alert")
        if st:
            self.launch_alert(random.choice(st))

    def on_buff_triggered(self, buff, target_id=None):
        """Play an extra trigger sound for a buff or debuff when configured."""
        st = style.get(buff, "triggered", warn_if_not_found=False)
        if st:
            self.launch_event(random.choice(st))

    def on_charge_success(self):
        """处理冲锋攻击成功事件"""
        # 播放冲锋攻击成功音效
        self.launch_event_style("charge_success", alert=True)

    def _play_type_sound(self, type_name, sound_param, fallback_event, alert=False):
        """从类型继承链查找音效并播放，找不到则回退到单位默认样式。"""
        sound_list = self._get_weapon_sound_from_inheritance_chain(type_name, sound_param)
        if not sound_list:
            sound_list = self._get_item_sound_from_inheritance_chain(type_name, sound_param)
        if sound_list:
            self.launch_event(random.choice(sound_list), priority=0)
        else:
            self.launch_event_style(fallback_event, alert=alert)

    def on_weapon_switched(self, weapon_name):
        """处理武器切换事件"""
        self._play_type_sound(weapon_name, "weapon_switched", "weapon_switched", alert=True)

        # 播放武器名称
        if self.player == self.interface.player:
            weapon_title = style.get(weapon_name, "title")
            if weapon_title:
                # 使用voice播放武器名称
                voice.item(weapon_title)

    def on_weapon_unequipped(self, weapon_name):
        """处理卸下武器事件"""
        self._play_type_sound(weapon_name, "weapon_unequipped", "weapon_unequipped", alert=True)

    def on_armor_equipped(self, armor_name):
        """处理装备盔甲事件"""
        self._play_type_sound(armor_name, "armor_equipped", "armor_equipped", alert=True)

    def on_armor_unequipped(self, armor_name):
        """处理卸下盔甲事件"""
        self._play_type_sound(armor_name, "armor_unequipped", "armor_unequipped", alert=True)

    def _get_item_inheritance_chain(self, item_type):
        """获取物品的继承链，用于音效查找
        
        Args:
            item_type: 物品类型名称
            
        Returns:
            list: 继承链列表，按优先级排序（具体类型 -> 直接父类 -> 间接父类）
        """
        inheritance_chain = [item_type]  # 从具体类型开始
        added_types = {item_type}  # 用于避免重复
        
        try:
            from ..definitions import rules
            # 递归获取继承链
            def add_parents(type_name):
                # 直接访问 rules._dict 来获取物品定义
                if hasattr(rules, '_dict') and type_name in rules._dict:
                    item_def = rules._dict[type_name]
                    if 'is_a' in item_def and item_def['is_a']:
                        # 处理is_a可能是字符串、列表或元组的情况
                        parents = []
                        is_a = item_def['is_a']
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
            
            add_parents(item_type)
            
        except (AttributeError, ImportError):
            # 如果无法获取继承信息，只使用原始类型
            pass
        
        return inheritance_chain

    def _get_item_sound_from_inheritance_chain(self, item_name, sound_param):
        """从物品继承链中查找音效
        
        Args:
            item_name: 物品名称
            sound_param: 音效参数名称（如'on_pickup', 'on_drop'等）
            
        Returns:
            list: 音效ID列表，如果没有找到则返回None
        """
        # 获取物品继承链
        inheritance_chain = self._get_item_inheritance_chain(item_name)
        
        # 按继承链顺序查找音效
        for item_type in inheritance_chain:
            if style.has(item_type, sound_param):
                item_sound_id = style.get(item_type, sound_param)
                # style.get()返回的是列表，返回整个列表以支持随机播放
                if item_sound_id and len(item_sound_id) > 0:
                    return item_sound_id
        
        return None

    def on_pickup(self, item_type):
        """处理物品拾取事件并播放对应音效"""
        # 首先尝试从物品本身的定义中查找音效（支持继承链）
        item_sound_list = self._get_item_sound_from_inheritance_chain(item_type, "on_pickup")
        if item_sound_list:
            # 从音效列表中随机选择一个播放
            item_sound = random.choice(item_sound_list)
            self.launch_event(item_sound)
            return
        
        # 如果物品本身没有定义音效，使用单位配置的音效
        # 获取物品的继承链
        inheritance_chain = self._get_item_inheritance_chain(item_type)
        
        # 按继承链顺序查找音效：从具体类型到基类型
        for type_name in inheritance_chain:
            pickup_sound_param = f"pickup_{type_name}"
            pickup_sound = style.get(self.type_name, pickup_sound_param, warn_if_not_found=False)
            
            if pickup_sound:
                # 找到了特定类型的拾取音效，播放该音效
                self.launch_event(random.choice(pickup_sound))
                return
        
        # 如果没有找到任何特定音效，使用通用的pickup音效
        self.launch_event_style("pickup")

    def on_drop(self, item_type):
        """处理物品丢弃事件并播放对应音效"""
        # 首先尝试从物品本身的定义中查找音效（支持继承链）
        item_sound_list = self._get_item_sound_from_inheritance_chain(item_type, "on_drop")
        if item_sound_list:
            # 从音效列表中随机选择一个播放
            item_sound = random.choice(item_sound_list)
            self.launch_event(item_sound)
            return
        
        # 如果物品本身没有定义音效，使用单位配置的音效
        # 获取物品的继承链
        inheritance_chain = self._get_item_inheritance_chain(item_type)
        
        # 按继承链顺序查找音效：从具体类型到基类型
        for type_name in inheritance_chain:
            drop_sound_param = f"drop_{type_name}"
            drop_sound = style.get(self.type_name, drop_sound_param, warn_if_not_found=False)
            
            if drop_sound:
                # 找到了特定类型的丢弃音效，播放该音效
                self.launch_event(random.choice(drop_sound))
                return
        
        # 如果没有找到任何特定音效，使用通用的drop音效
        self.launch_event_style("drop")

    def _play_item_use_sound(self, item_type):
        """播放物品使用音效（支持 on_use / use 及单位侧 use_<item> 配置）。"""
        for param in ("on_use", "use"):
            item_sound_list = self._get_item_sound_from_inheritance_chain(
                item_type, param
            )
            if item_sound_list:
                self.launch_event(random.choice(item_sound_list))
                return True
        inheritance_chain = self._get_item_inheritance_chain(item_type)
        for type_name in inheritance_chain:
            use_sound = style.get(
                self.type_name, f"use_{type_name}", warn_if_not_found=False
            )
            if use_sound:
                self.launch_event(random.choice(use_sound))
                return True
        self.launch_event_style("item_used")
        return False

    def on_use(self, item_type):
        """背包中成功使用（消耗）物品：播放音效，普通消耗品再朗读名称。"""
        self._play_item_use_sound(item_type)
        if self.player is not self.interface.player:
            return
        try:
            from ..definitions import rules
            cls = rules.unit_class(item_type)
            if cls is not None and getattr(cls, "skills", None):
                return
        except Exception:
            pass
        title = style.get(item_type, "title")
        if title:
            msg = title if isinstance(title, list) else [str(title)]
            voice.item(msg + mp.USED_ITEM)

    def on_skill_unlock(self, skill_name, unit_id=None):
        """永久学会技能时的语音反馈。"""
        if self.player is not self.interface.player:
            return
        msg = []
        title = style.get(skill_name, "title")
        if title:
            msg.extend(title if isinstance(title, list) else [str(title)])
        else:
            msg.append(skill_name)
        learned = style.get("messages", "skill_learned", warn_if_not_found=False)
        if learned:
            msg.extend(learned if isinstance(learned, list) else [str(learned)])
        voice.info(msg)

    def on_give(self, item_type=None):
        """处理把物品交给其他单位的事件（复用drop音效）。"""
        if item_type:
            item_sound_list = self._get_item_sound_from_inheritance_chain(item_type, "on_drop")
            if item_sound_list:
                self.launch_event(random.choice(item_sound_list))
                return
        self.launch_event_style("drop")

    def on_received(self, item_type=None):
        """处理某单位收到物品的事件（复用pickup音效）。"""
        if item_type:
            item_sound_list = self._get_item_sound_from_inheritance_chain(item_type, "on_pickup")
            if item_sound_list:
                self.launch_event(random.choice(item_sound_list))
                return
        self.launch_event_style("pickup")

    def on_auto_weapon_switched(self, weapon_name):
        """处理自动武器切换事件（播放音效但不播报武器名）"""
        self._play_type_sound(weapon_name, "weapon_switched", "weapon_switched", alert=True)

    def on_debug_info(self, info_text):
        """处理调试信息事件"""
        if self.player == self.interface.player:
            # 播放调试信息
            voice.info([info_text])

    def on_attributes_changed(self):
        """处理属性变化事件"""
        interface = getattr(self, "interface", None)
        if interface is None:
            return
        if not getattr(interface, "_in_attributes_screen", False):
            return
        unit = getattr(interface, "_attributes_screen_unit", None)
        if unit is None:
            return
        # 当前属性单位（或其 model）与本实体匹配时刷新
        if unit is not self and getattr(unit, "model", None) is not self.model:
            if getattr(unit, "id", None) != getattr(self, "id", None):
                return
        display = getattr(getattr(interface, "main_display", None), "display_interface", None)
        if display is None:
            return
        # 强制按新地形/属性重建
        interface._attrs_terrain_type = object()
        if display.refresh_attributes_for_terrain_if_needed():
            display._display_current_attribute()

    def on_launch_charge_mdg(self, *args):
        """处理发起近战冲锋攻击
        
        Args:
            *args: 附加参数，通常是单位类型和ID
        """
        # 检查是否有额外参数（单位类型和ID）
        if len(args) >= 2:
            unit_type = args[0]
            unit_id = args[1]
            # 这里可以使用单位类型和ID做额外的处理
        
        # 播放冲锋攻击音效
        self.launch_event_style("launch_charge_mdg")
        
    def on_launch_charge_rdg(self, *args):
        """处理发起远程冲锋攻击
        
        Args:
            *args: 附加参数，通常是单位类型和ID
        """
        # 检查是否有额外参数（单位类型和ID）
        if len(args) >= 2:
            unit_type = args[0]
            unit_id = args[1]
            # 这里可以使用单位类型和ID做额外的处理
        
        # 播放冲锋攻击音效
        self.launch_event_style("launch_charge_rdg")