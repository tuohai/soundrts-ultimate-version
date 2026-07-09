"""属性和描述相关模块 - 标题、描述、菜单等显示相关方法"""

import math
from ..clientgameorder import get_orders_list
from ..definitions import style
from ..lib.log import exception
from ..lib.msgs import nb2msg
from .. import msgparts as mp
from .base import compute_title


def deposit_qty_unit_title(type_name=None, resource_type=None):
    """矿床「含有 N X」中的 X：优先 style.qty_unit_title（肉/果子），否则仓库资源名（食物）。"""
    if type_name:
        custom = style.get(type_name, "qty_unit_title", warn_if_not_found=False)
        if custom:
            return custom
    if resource_type:
        return style.get("parameters", f"{resource_type}_title")
    return []


def carcass_short_title(model, type_name=None):
    """狩猎尸体：有来源动物时显示「鹿的尸体」，否则回退为 deposit 类型名。"""
    type_name = type_name or getattr(model, "type_name", None)
    carcass_of = getattr(model, "carcass_of", None)
    if type_name == "food_carcass" and carcass_of:
        return compute_title(carcass_of) + mp.CORPSE
    return compute_title(type_name)


def unit_has_no_number(model):
    return bool(getattr(model, "no_number", 0))


def count_player_units_of_type(player, type_name):
    if not player:
        return 0
    return sum(
        1
        for u in player.units
        if getattr(u, "type_name", None) == type_name and getattr(u, "presence", True)
    )


def unit_should_show_number(model):
    if not getattr(model, "number", 0):
        return False
    if not unit_has_no_number(model):
        return True
    player = getattr(model, "player", None)
    type_name = getattr(model, "type_name", None)
    if not player or not type_name:
        return False
    return count_player_units_of_type(player, type_name) > 1


def summary_omit_single_count(model):
    if not unit_has_no_number(model):
        return False
    return not unit_should_show_number(model)


def unit_should_show_number_at_death(model):
    if not unit_has_no_number(model):
        return True
    player = getattr(model, "player", None)
    type_name = getattr(model, "type_name", None)
    if not player or not type_name:
        return False
    return (
        sum(
            1
            for u in player.units
            if getattr(u, "type_name", None) == type_name
            and (u is model or getattr(u, "presence", True))
        )
        > 1
    )


def summary_omit_single_count_at_death(model):
    if not unit_has_no_number(model):
        return False
    return not unit_should_show_number_at_death(model)


def is_wildlife_unit(model):
    """狩猎/畜牧动物（鹿、羊、野猪等），播报时用「动物」而非「中立/NPC」。"""
    if getattr(model, "is_huntable", 0) or getattr(model, "herdable", 0):
        return True
    unit_type = type(model)
    return bool(
        getattr(unit_type, "is_huntable", 0) or getattr(unit_type, "herdable", 0)
    )


def player_is_wildlife_only(player):
    """玩家名下所有存活单位均为野生动物时，切视角播报「你是动物」。"""
    units = [u for u in getattr(player, "units", []) if getattr(u, "presence", True)]
    if not units:
        return False
    return all(is_wildlife_unit(u) for u in units)


class EntityViewProperties:
    """EntityView的属性和描述相关方法"""

    @property
    def ext_title(self):
        try:
            # 在缩放模式下，包含主方格名称和坐标信息
            if self.interface.zoom_mode and hasattr(self.interface, 'zoom'):
                zoom = self.interface.zoom
                # 检查单位是否在当前缩放区域内
                if zoom.contains(self):
                    # 获取主方格名称
                    main_square_title = zoom.current_main_square.title
                    # 获取缩放坐标
                    zoom_coords_title = zoom.title
                    # 返回格式："单位名称 在 主方格名称, 缩放坐标"
                    return self.title + mp.AT + main_square_title + mp.COMMA + zoom_coords_title
                else:
                    # 单位不在当前缩放区域，使用单位所在地点的标题
                    return self.title + mp.AT + self.place.title
            else:
                # 非缩放模式，使用原来的逻辑
                return self.title + mp.AT + self.place.title
        except:
            exception("problem with %s.ext_title", self.type_name)

    def _menu(self, strict=False):
        menu = []
        try:  # TODO: remove this "try... except" when rules.txt checking is implemented
            for order_class in get_orders_list():
                menu.extend(order_class.menu(self, strict=strict))
        except:
            exception("problem with %s.menu() of %s", order_class, self.type_name)
        return menu

    @property
    def menu(self):
        return self._menu()

    @property
    def strict_menu(self):
        return self._menu(strict=True)

    @property
    def orders_txt(self):
        t = []
        model = getattr(self, "model", None)
        if model is not None:
            from .base import _attack_action_title_msg

            orders = getattr(model, "orders", None) or []
            attack_msg = _attack_action_title_msg(self.interface, model)
            if attack_msg:
                if not orders:
                    return attack_msg + mp.COMMA
                if getattr(orders[0], "keyword", None) != "attack":
                    t += attack_msg

        prev = None
        nb = 0
        
        # 处理不同命令类型
        for i, o in enumerate(self.orders):
            # 如果是巡逻命令，不再显示后续命令
            if o.keyword == "patrol":
                if prev:
                    from .base import _order_title_msg
                    t += _order_title_msg(prev, self.interface, nb)
                    prev = None
                    nb = 0
                from .base import _order_title_msg
                t += _order_title_msg(o, self.interface)
                break
                
            # 处理训练命令的队列
            if o.keyword == "train":
                # 如果前一个命令也是训练命令并且类型相同，增加计数
                if prev and prev.keyword == "train" and prev.type == o.type:
                    nb += 1
                else:
                    # 先添加前一个命令（如果有）
                    if prev:
                        from .base import _order_title_msg
                        t += _order_title_msg(prev, self.interface, nb)
                    # 更新当前命令为新的训练命令
                    prev = o
                    nb = 1
            else:
                # 非训练命令，先处理之前累积的训练命令（如果有）
                if prev:
                    from .base import _order_title_msg
                    t += _order_title_msg(prev, self.interface, nb)
                    prev = None
                    nb = 0
                # 添加当前非训练命令
                from .base import _order_title_msg
                t += _order_title_msg(o, self.interface)
        
        # 处理最后一个训练命令（如果有）
        if prev:
            from .base import _order_title_msg
            t += _order_title_msg(prev, self.interface, nb)
            
        return t + mp.COMMA

    @property
    def title(self):
        title = self.short_title[:]
        if self.player:
            if self.player == self.interface.player:
                if self.number and unit_should_show_number(self.model):
                    title += nb2msg(self.number)
            else:
                # 触发器脚本电脑（无具体身份）播报其归属时统一用 "NPC"，而不是读出
                # 内部 login "ai_timers"。判据集中在 Player.is_script_npc：覆盖战役
                # 电脑（含被升格的）与普通地图（如 td2）里的 timers 脚本 AI。
                is_npc = getattr(self.player, "is_script_npc", False)
                owner_name = compute_title("ai_timers") if is_npc else self.player.name
                # 狩猎动物优先于外交关系：同一 ai 联盟里的多个 computer_only 电脑
                # 彼此互为盟友，但鹿/羊/野猪仍应播报为「动物」，不能标成「联盟/NPC」。
                if is_wildlife_unit(self.model) or player_is_wildlife_only(self.player):
                    title += mp.COMMA + mp.ANIMAL + mp.COMMA
                elif (
                    self.player in self.interface.player.allied
                    and getattr(self.interface.player, "is_script_npc", False)
                    and getattr(self.player, "is_script_npc", False)
                    and not getattr(self.player, "neutral", False)
                    and not player_is_wildlife_only(self.player)
                ):
                    # 随机地图敌对 creep 与狩猎电脑同属 alliance "ai"，切到
                    # 某个电脑视角时彼此会进 allied；仍应播报为敌人而非联盟。
                    title += mp.ENEMY + mp.COMMA + owner_name + mp.COMMA
                elif self.player in self.interface.player.allied:
                    title += mp.ALLY + mp.COMMA + owner_name + mp.COMMA
                elif getattr(self.player, "neutral", False):
                    # `computer_only ... neutral` 的电脑：标注为"中立"而非"敌人"，
                    # 与 guard+counterattack 的被动 creep 行为保持一致。
                    # 中立的 ai_timers 在"中立"后再补一句 "NPC"。
                    title += mp.NEUTRAL + mp.COMMA
                    if is_npc:
                        title += owner_name + mp.COMMA
                else:
                    title += mp.ENEMY + mp.COMMA + owner_name + mp.COMMA
        if self.is_memory:
            title += mp.IN_THE_FOG + mp.COMMA
            if self.speed:
                s = (self.world.time - self.time_stamp) // 1000
                m = s // 60
                if m:
                    title += nb2msg(m) + mp.MINUTES
                elif s:
                    title += nb2msg(s) + mp.SECONDS
                title += mp.COMMA
        return title

    @property
    def short_title(self):
        if self.type_name == "buildingsite":
            return compute_title(self.type.type_name) + compute_title(self.type_name)
        if self.model is not None:
            carcass_of = getattr(self.model, "carcass_of", None)
            if self.type_name == "food_carcass" and carcass_of:
                return carcass_short_title(self.model)
        return compute_title(self.type_name)

    @property
    def hp_status(self):
        return nb2msg(self.hp) + mp.HITPOINTS_ON + nb2msg(self.hp_max)

    @property
    def mana_status(self):
        if self.mana_max > 0:
            return nb2msg(self.mana) + mp.MANA_POINTS_ON + nb2msg(self.mana_max)
        else:
            return []

    @property
    def upgrades_status(self):
        result = []
        for u in self.upgrades:
            result += style.get(u, "title")
        return result

    @property
    def current_age_status(self):
        """对于可以推进时代（phase）的单位/建筑，返回"当前时代：XX"形式的状态。

        判定条件：单位的 ``can_advance`` 列表中包含任何属于 phase 类型的项。
        （为兼容旧地图，若 ``can_advance`` 为空但 ``can_research`` 中含有
        phase，则仍按 phase 处理。）
        当前时代来源：单位所属玩家的 ``current_phase`` 字段（即最近推进完成
        或起始时代）。若该字段为空（未推进任何时代且未在起始 upgrades 中
        指定时代），则不显示，避免误导。
        """
        try:
            from ..worldphase import is_a_phase
            from ..definitions import rules as _rules
            has_phase = False
            can_advance = getattr(self, "can_advance", None) or ()
            for tech_name in can_advance:
                if is_a_phase(_rules.unit_class(tech_name)):
                    has_phase = True
                    break
            if not has_phase:
                can_research = getattr(self, "can_research", None) or ()
                for tech_name in can_research:
                    if is_a_phase(_rules.unit_class(tech_name)):
                        has_phase = True
                        break
            if not has_phase:
                return []
            player = getattr(self, "player", None)
            current_phase = getattr(player, "current_phase", None) if player else None
            if not current_phase:
                return []
            return mp.CURRENT_AGE + style.get(current_phase, "title")
        except Exception:
            return []

    @property
    def description(self):
        d = []
        try:
            if hasattr(self, "qty") and self.qty:
                d += (
                    mp.COMMA
                    + mp.CONTAINS
                    + nb2msg(self.qty)
                    + deposit_qty_unit_title(self.type_name, self.resource_type)
                )
            if hasattr(self, "hp"):
                d += mp.COMMA + self.hp_status
            if hasattr(self, "mana"):
                d += mp.COMMA + self.mana_status
            # 添加等级显示（有 xp_thresholds 的英雄含 1 级也显示）
            if hasattr(self, "level") and (
                self.level > 1 or getattr(self, "xp_thresholds", None)
            ):
                d += mp.COMMA + mp.LEVEL + nb2msg(self.level)
            # 添加经验值显示
            if hasattr(self, "xp") and hasattr(self, "xp_thresholds") and self.xp_thresholds:
                # level 0 时 level-1 为 -1，不能用作下标（否则会取到最后一个阈值）
                current_level_index = max(0, self.level - 1)
                # 如果还有下一级可以升级
                if current_level_index < len(self.xp_thresholds):
                    next_level_xp = self.xp_thresholds[current_level_index]
                    d += mp.COMMA + mp.XP + nb2msg(self.xp) + mp.ON + nb2msg(next_level_xp)
                else:
                    # 已达到最高等级
                    d += mp.COMMA + mp.XP + nb2msg(self.xp) + mp.MAX_LEVEL
            # 显示复活时间（如果单位可复活）
            if hasattr(self, "is_revivable") and self.is_revivable:
                d += mp.COMMA + mp.REVIVAL_TIME + nb2msg(int(self.revival_time / 1000)) + mp.SECONDS
            if hasattr(self, "upgrades"):
                d += mp.COMMA + self.upgrades_status
            # 对可研究时代的建筑，附加显示"当前时代"
            current_age_msg = self.current_age_status
            if current_age_msg:
                d += mp.COMMA + current_age_msg
            # 添加当前buff名称显示
            buff_names = self._get_buff_names()
            if buff_names:
                d += mp.COMMA + buff_names
            if getattr(self, "is_invisible", 0) or getattr(self, "is_cloaked", 0):
                d += mp.COMMA + mp.INVISIBLE
            if getattr(self, "is_a_detector", 0):
                d += mp.COMMA + mp.DETECTOR
            if getattr(self, "is_a_cloaker", 0):
                d += mp.COMMA + mp.CLOAKER
        except:
            pass  # a warning is given by style.get()
        return d

    def _get_buff_names(self):
        """获取当前单位的所有buff名称"""
        buff_names = []
        try:
            if hasattr(self.model, '_buffs') and self.model._buffs:
                for buff in self.model._buffs:
                    # 获取buff的标题
                    buff_title = style.get(buff.type_name, "title", warn_if_not_found=False)
                    if buff_title:
                        if isinstance(buff_title, list):
                            buff_names.extend(buff_title)
                        else:
                            buff_names.append(str(buff_title))
                        buff_names.extend(mp.COMMA)  # 在每个buff名称后添加逗号
                
                # 移除最后一个逗号
                if buff_names and len(buff_names) > 0:
                    # 检查最后一个元素是否是逗号
                    if buff_names[-1:] == mp.COMMA:
                        buff_names = buff_names[:-1]
        except:
            pass  # 忽略错误，避免影响正常的状态显示
        
        return buff_names

    def _direction_msg(self):
        from ..lib.sound import distance, angle
        x, y = self.interface.place_xy
        d = distance(x, y, self.x, self.y)
        if d < self.interface.square_width / 3 / 2:
            return mp.AT_THE_CENTER
        direction = math.degrees(angle(x, y, self.x, self.y, 0))
        from .base import direction_to_msgpart
        mp_direction = direction_to_msgpart(direction)
        if mp_direction == mp.EAST:
            return mp.TO_THE_EAST  # special case in French
        if mp_direction == mp.WEST:
            return mp.TO_THE_WEST  # special case in French
        return mp.TO_THE + mp_direction

    @property
    def positional_description(self):
        d = self.title
        if self.interface.immersion:
            d += mp.AT2 + nb2msg(self.interface.distance(self)) + mp.METERS
        return d + self._direction_msg() + self.description