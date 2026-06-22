from .. import msgparts as mp
from ..clientgameorder import OrderTypeView
from ..clientmedia import voice, sounds
from ..lib.sound import psounds
from ..definitions import style
from ..lib.msgs import nb2msg
from ..lib.sound import distance


# 指令管理核心功能
def orders(interface, inactive_only=False, inactive_included=False):
    if inactive_included:
        menu_type = "menu"
        ok = lambda o, u: True
    elif inactive_only:
        menu_type = "menu"
        ok = lambda o, u: o not in u.strict_menu
    else:
        menu_type = "strict_menu"
        ok = lambda o, u: True
    menu = []
    done = []
    for u in interface.group:
        if u in interface.dobjets:
            u = interface.dobjets[u]
            for o in getattr(u, menu_type):
                if o not in done and ok(o, u):
                    menu.append(OrderTypeView(o, u))
                    done.append(o)
    # sort the menu by index
    menu.sort(key=lambda x: x.index)
    return menu


def an_order_not_requiring_a_target_is_selected(interface):
    return interface.order and interface.order.nb_args == 0


def an_order_requiring_a_target_is_selected(interface):
    return interface.order and interface.order.nb_args


def _select_order(interface, order, help=True):
    interface.order = order
    # say the new current order
    msg = interface.order.title + mp.COMMA + interface.order.full_comment
    if help:
        if interface.order.nb_args == 0:
            msg += mp.COMMA + mp.CONFIRM
        else:
            msg += mp.COMMA + mp.SELECT_TARGET_AND_CONFIRM
    voice.item(msg)


def _orders_list(interface, *args):
    return orders(
        interface,
        inactive_only="inactive_only" in args,
        inactive_included="inactive_included" in args,
    )


def cmd_select_order(interface, inc, *args):
    inc = int(inc)
    orders_list = _orders_list(interface, *args)
    # if no menu then do nothing
    if not orders_list:
        voice.item(mp.NOTHING)
        interface.order = None
        return
    # select the next/previous order
    if interface.order is None:
        index = -1
    else:
        try:
            index = orders_list.index(interface.order)
        except ValueError:  # order not found
            index = -1
    index += inc
    if index < 0:
        index = len(orders_list) - 1
    elif index >= len(orders_list):
        index = 0
    _select_order(interface, orders_list[index], help="inactive_only" not in args)


def cmd_select_order_index(interface, index, *args):
    """按菜单序号直接选择命令（1 为第一条）。"""
    slot = int(index) - 1
    orders_list = _orders_list(interface, *args)
    if not orders_list or slot < 0 or slot >= len(orders_list):
        voice.item(mp.NOTHING)
        interface.order = None
        return
    _select_order(interface, orders_list[slot], help="inactive_only" not in args)


def cmd_order_shortcut(interface):
    if interface.group:
        msg = []
        for o in orders(interface):
            shortcut = o.shortcut
            if shortcut:
                msg += [str(shortcut)] + o.title + mp.COMMA
        if msg:
            interface.shortcut_mode = True
            voice.item(msg)
            return
    voice.item(mp.BEEP)


def cmd_do_again(interface, *args):
    if getattr(interface, '_previous_order', None) is not None and interface.group:
        _select_order(interface, interface._previous_order)
        if "now" in args and interface.order.nb_args == 0:
            args = [a for a in args if a in ("queue_order", "imperative")]
            cmd_validate(interface, *args)


def cmd_skill(interface, skill):
    for o in orders(interface):
        if o.is_skill(skill):
            _select_order(interface, o)
            return
    voice.item(mp.BEEP)


# 指令验证和执行
def ui_target(interface):
    if interface.target is not None:
        return interface.target
    else:
        if interface.zoom_mode:
            return interface.zoom
        else:
            return interface.place


def cmd_validate(interface, *args):
    if not interface.group:
        voice.item(mp.NO_UNIT_CONTROLLED)
    elif interface.order is None:  # nothing to validate
        from .game_unit_control import cmd_command_unit
        cmd_command_unit(interface)
    elif an_order_not_requiring_a_target_is_selected(interface):
        from .game_unit_control import send_order
        send_order(interface, interface.order.encode, None, args)
        voice.item(interface.order.title)  # confirmation
        interface._previous_order = interface.order
    elif an_order_requiring_a_target_is_selected(interface):
        if interface.order not in orders(interface):
            # the order is not in the menu anymore
            psounds.play_stereo(sounds.get_sound(mp.BEEP[0]))
        elif ui_target(interface).id is not None:
            from .game_unit_control import send_order
            send_order(interface, interface.order.encode, ui_target(interface).id, args)
            # confirmation
            voice.item(interface.order.title + ui_target(interface).title)
            interface._previous_order = interface.order
    interface.order = None


def _say_default_confirmation(interface):
    # If the group contains different units with different default orders,
    # tell the various default orders.
    # For example, if the target is a goldmine and the group contains
    # workers and soldiers, then the interface will say:
    # "exploit a goldmine, move to a goldmine".
    msgs = []
    for u in interface.group:
        if u in interface.dobjets:
            u = interface.dobjets[u]
            order = u.model.get_default_order(ui_target(interface).id)
            if order is not None:
                msg = OrderTypeView(order, u).title + ui_target(interface).title
                if msg not in msgs:
                    msgs.append(msg)
    confirmation = []
    for msg in msgs:
        confirmation += msg + mp.COMMA
    if confirmation:
        voice.item(confirmation)
    else:
        voice.item(mp.BEEP)


def cmd_default(interface, *args):
    if not interface.group:
        voice.item(mp.NO_UNIT_CONTROLLED)
    elif ui_target(interface).id is not None:
        from .game_unit_control import send_order
        send_order(interface, "default", ui_target(interface).id, args)
        _say_default_confirmation(interface)
    interface.order = None


# RPG技能系统
def cmd_rpg_skill_1(interface):
    """RPG模式下按1键释放第1个技能"""
    _rpg_use_skill_by_index(interface, 0)


def cmd_rpg_skill_2(interface):
    """RPG模式下按2键释放第2个技能"""
    _rpg_use_skill_by_index(interface, 1)


def cmd_rpg_skill_3(interface):
    """RPG模式下按3键释放第3个技能"""
    _rpg_use_skill_by_index(interface, 2)


def cmd_rpg_skill_4(interface):
    """RPG模式下按4键释放第4个技能"""
    _rpg_use_skill_by_index(interface, 3)


def cmd_rpg_skill_5(interface):
    """RPG模式下按5键释放第5个技能"""
    _rpg_use_skill_by_index(interface, 4)


def cmd_rpg_skill_6(interface):
    """RPG模式下按6键释放第6个技能"""
    _rpg_use_skill_by_index(interface, 5)


def cmd_rpg_skill_7(interface):
    """RPG模式下按7键释放第7个技能"""
    _rpg_use_skill_by_index(interface, 6)


def cmd_rpg_skill_8(interface):
    """RPG模式下按8键释放第8个技能"""
    _rpg_use_skill_by_index(interface, 7)


def cmd_rpg_skill_9(interface):
    """RPG模式下按9键释放第9个技能"""
    _rpg_use_skill_by_index(interface, 8)


def cmd_rpg_skill_0(interface):
    """技能界面按 0 键释放第 10 个技能"""
    _rpg_use_skill_by_index(interface, 9)


def cmd_rpg_skill_10(interface):
    """技能界面按 - 键释放第 11 个技能"""
    _rpg_use_skill_by_index(interface, 10)


def cmd_rpg_skill_11(interface):
    """技能界面按 = 键释放第 12 个技能"""
    _rpg_use_skill_by_index(interface, 11)


def _rpg_use_skill_by_index(interface, skill_index):
    """RPG模式下根据索引使用技能"""
    # 检查是否在RPG模式
    if not interface.immersion:
        voice.item(mp.BEEP)
        return
        
    # 检查是否有选中的单位
    if not interface.group:
        voice.item(mp.NO_UNIT_CONTROLLED)
        return
        
    # 获取当前单位的所有可用技能
    orders_list = orders(interface)
    
    # 过滤出技能类型的命令
    skills = []
    for o in orders_list:
        # 检查是否是技能（通过检查是否有is_skill方法或特定的属性）
        if hasattr(o, 'cls') and hasattr(o.cls, 'keyword'):
            # 如果是use命令，说明是技能
            if o.cls.keyword == "use":
                skills.append(o)
            # 或者检查是否有特定的技能标识
            elif hasattr(o, 'is_skill') and hasattr(o, 'skill_name'):
                skills.append(o)
    
    # 检查技能索引是否有效
    if skill_index >= len(skills):
        voice.item(mp.BEEP)
        return
        
    # 选择并使用技能
    skill = skills[skill_index]
    _select_order(interface, skill, help=False)  # 不播放帮助信息
    
    # 如果技能不需要目标，直接释放
    if skill.nb_args == 0:
        cmd_validate(interface)
        # 播放技能名称确认
        voice.item(skill.title)
    else:
        # 如果技能需要目标，播放提示信息
        voice.item(skill.title + mp.COMMA + mp.SELECT_TARGET_AND_CONFIRM)


def cmd_rpg_skill_list(interface):
    """RPG模式下列出当前单位的所有技能"""
    if not interface.immersion:
        voice.item(mp.BEEP)
        return
        
    if not interface.group:
        voice.item(mp.NO_UNIT_CONTROLLED)
        return
        
    # 获取当前单位的所有可用技能
    orders_list = orders(interface)
    
    # 过滤出技能类型的命令
    skills = []
    for o in orders_list:
        if hasattr(o, 'cls') and hasattr(o.cls, 'keyword') and o.cls.keyword == "use":
            skills.append(o)
    
    if not skills:
        voice.item(mp.NO_SKILLS if hasattr(mp, "NO_SKILLS") else ["没有可用技能"])
        return
        
    # 播报技能列表
    msg = ["可用技能："]
    for i, skill in enumerate(skills[:10]):  # 最多显示10个技能
        msg.append(f"{i+1 if i < 9 else 0}键：")
        msg.extend(skill.title)
        if i < len(skills) - 1:
            msg.append("，")
    
    voice.item(msg)


def cmd_rpg_auto_attack(interface):
    """RPG模式下自动攻击最近的敌人"""
    if not interface.immersion:
        voice.item(mp.BEEP)
        return
        
    if not interface.group:
        voice.item(mp.NO_UNIT_CONTROLLED)
        return
        
    # 寻找视野内最近的敌人
    nearest_enemy = None
    min_distance = float('inf')
    
    from .game_unit_control import is_visible
    for obj in list(interface.dobjets.values()):
        if (is_visible(interface, obj) and obj.player and 
            interface.player.is_an_enemy(obj.model)):
            
            unit = interface.dobjets[interface.group[0]]
            dist = distance(unit.x, unit.y, obj.x, obj.y)
            
            if dist < min_distance:
                min_distance = dist
                nearest_enemy = obj
    
    if nearest_enemy:
        # 设置目标并发送攻击命令
        interface.target = nearest_enemy
        from .game_unit_control import send_order
        send_order(interface, "default", nearest_enemy.id, [])
        voice.item(mp.ATTACKING + nearest_enemy.title)
    else:
        voice.item(mp.NO_ENEMY_IN_SIGHT if hasattr(mp, "NO_ENEMY_IN_SIGHT") else ["视野内没有敌人"])


# 导出的函数供其他模块使用
__all__ = [
    'orders', 'an_order_not_requiring_a_target_is_selected', 
    'an_order_requiring_a_target_is_selected', '_select_order',
    'cmd_select_order', 'cmd_select_order_index', 'cmd_order_shortcut',
    'cmd_do_again', 'cmd_skill',
    'ui_target', 'cmd_validate', '_say_default_confirmation', 'cmd_default',
    'cmd_rpg_skill_1', 'cmd_rpg_skill_2', 'cmd_rpg_skill_3', 'cmd_rpg_skill_4',
    'cmd_rpg_skill_5', 'cmd_rpg_skill_6', 'cmd_rpg_skill_7', 'cmd_rpg_skill_8',
    'cmd_rpg_skill_9', 'cmd_rpg_skill_0', 'cmd_rpg_skill_10', 'cmd_rpg_skill_11',
    'cmd_rpg_skill_list', 'cmd_rpg_auto_attack',
    '_rpg_use_skill_by_index'
]