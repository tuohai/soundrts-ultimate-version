import time

from .. import config
from .. import msgparts as mp
from ..clientgameentity import EntityView
from ..clientgameentity.properties import (
    is_wildlife_unit,
    player_is_wildlife_only,
    summary_omit_single_count,
)
from ..clientgameorder import OrderTypeView
from ..clientmedia import voice
from ..definitions import style
from ..lib import group
from ..lib.log import exception
from ..open_container import container_visible_from_place, inside_unit_visible_from_place
from ..lib.msgs import nb2msg, nb2msg_float
from ..lib.sound import angle, distance, stereo


def _dedupe_key(item):
    if isinstance(item, list):
        return tuple(_dedupe_key(x) for x in item)
    if isinstance(item, tuple):
        return tuple(_dedupe_key(x) for x in item)
    return item


def _remove_duplicates(l):
    seen = set()
    m = []
    for i in l:
        key = _dedupe_key(i)
        if key not in seen:
            seen.add(key)
            m.append(i)
    return m


def _is_ground_item(o):
    return (
        getattr(o, "default_order", None) == "pickup"
        and getattr(o, "player", None) is None
    )


def _square_has_ground_items(interface):
    for o in interface.dobjets.values():
        if is_selectable(interface, o) and _is_ground_item(o):
            return True
    return False


def _priority(interface, o, prioritize_items=False):
    p = 10
    if interface.an_order_requiring_a_target_is_selected:
        if interface.order.cls.keyword == "build":
            from ..definitions import rules
            from ..world_build_rules import requires_deposit_type
            from ..worldresource import Deposit

            required_deposit = None
            if getattr(interface.order, "type", None):
                building_cls = rules.unit_class(interface.order.type)
                if building_cls is not None:
                    required_deposit = requires_deposit_type(building_cls)
            if required_deposit:
                if (
                    isinstance(getattr(o, "model", None), Deposit)
                    and getattr(o, "type_name", None) == required_deposit
                ):
                    p = 0
                else:
                    p = 10
            elif o.is_a_building_land:
                if o.is_an_exit:
                    p = 0.5
                else:
                    p = 0
    else:
        if prioritize_items and _is_ground_item(o):
            p = 0.25
        elif interface.player.is_an_enemy(o):
            p = 0.5
        # 检查是否是可开采的资源点或可开采的建筑物
        elif (o.qty > 0) or (hasattr(o, "is_a_building") and o.is_a_building and 
                            hasattr(o, "resource_type") and o.resource_type and 
                            hasattr(o, "resource_qty") and o.resource_qty > 0):
            # 将字符串资源类型转换为数字
            if hasattr(o, "resource_type"):
                resource_id = None
                if isinstance(o.resource_type, str):
                    if o.resource_type.startswith("resource"):
                        try:
                            # 从resource3这样的格式中提取数字
                            resource_id = int(o.resource_type[8:]) - 1
                        except (ValueError, AttributeError):
                            resource_id = 99  # 默认最低优先级
                    else:
                        try:
                            # 处理字符串形式的整数
                            resource_id = int(o.resource_type)
                        except (ValueError, AttributeError):
                            resource_id = 99  # 默认最低优先级
                else:
                    # 处理直接整数
                    resource_id = o.resource_type
                p = 1 + resource_id / 100.0
            else:
                p = 1
        elif o.is_repairable and o.hp < o.hp_max:
            p = 2
        elif o.is_a_building_land:
            p = 3
        elif hasattr(o, "other_side"):
            p = 4
    return [p, len(o.title), interface.distance(o)]


def is_visible(interface, o):
    if interface.zoom_mode and not interface.zoom.contains(o):
        return False
        
    # 处理容器内单位的可见性
    if hasattr(o, 'is_inside') and o.is_inside:
        if inside_unit_visible_from_place(o, interface.place):
            return True
        return False
            
    # 检查单位是否在当前区域（用 short_title：雾中记忆对象 title 含战云但 short_title 为空时不应 Tab 选中）
    if not o.is_in(interface.place) or not o.short_title:
        return False

    # 从未探索过的空白格：不可 Tab / 选中任何对象。
    # （感知系统会把小径对侧出口预写入记忆，否则会在未知区域 Tab 出「向南小径」等）
    place = interface.place
    if place is not None:
        scouted = getattr(interface, "scouted_squares", None) or ()
        scouted_before = getattr(interface, "scouted_before_squares", None) or ()
        if place not in scouted and place not in scouted_before:
            return False
        
    if interface.immersion:
        if o.id in interface.group:
            return False
        else:
            a = angle(interface.x, interface.y, o.x, o.y, interface.o)
            # 第一人称RPG模式使用360度全方位视野
            # 这样可以感知到所有方向的对象，包括后方
            return True
            
    if o.is_an_exit and o.is_blocked():
        return False
        
    return True


def is_selectable(interface, o):
    return is_visible(interface, o)


def _square_allows_passage_tab(place):
    """Bridge/scaffold squares: Tab may cycle passage exits even with ``no_exit``."""
    if place is None:
        return False
    return bool(
        getattr(place, "_bridge_terrain_voice", None)
        or getattr(place, "_scaffold_terrain_voice", None)
    )


def _object_choices(interface, inc, types):
    choices = []
    no_exit = "no_exit" in types
    if no_exit:
        types = list(types)
        types.remove("no_exit")
    allow_passage_tab = no_exit and _square_allows_passage_tab(interface.place)
    for o in list(interface.dobjets.values()):
        if no_exit and getattr(getattr(o, "model", None), "is_an_exit", False):
            if not allow_passage_tab:
                continue
        # 根据方向过滤
        if interface._side_filter != "all":
            if interface._side_filter == "ally":
                if o.player and o.player.player_is_an_enemy(interface.player):
                    continue  # 跳过敌方单位
            elif interface._side_filter == "enemy":
                if not (o.player and o.player.player_is_an_enemy(interface.player)):
                    continue  # 跳过非敌方单位
        
        # 根据类型过滤
        if interface._type_filter != "all":
            if interface._type_filter == "building":
                if not getattr(o, "is_a_building", False):
                    continue  # 跳过非建筑
            elif interface._type_filter == "unit":
                if getattr(o, "is_a_building", False) or not getattr(o, "player", None):
                    continue  # 跳过建筑和非单位
            elif interface._type_filter == "element":
                if getattr(o, "player", None):
                    continue  # 跳过所有有玩家属性的对象（单位和建筑）
        
        if is_selectable(interface, o) and (
            not types
            or getattr(o, "type_name", None) in types
            or "useful" in types
            and o.is_a_useful_target()
        ):
            choices.append(o)
    prioritize_items = _square_has_ground_items(interface)
    choices.sort(key=lambda x: _priority(interface, x, prioritize_items))
    if inc == -1:
        choices.reverse()
    return choices


def say_target(interface):
    # 对于其他类型的目标，使用原来的逻辑
    # 获取标题和位置信息（不包含描述部分）
    title = interface.target.title
    direction = interface.target._direction_msg()
    
    # 在第一人称RPG模式下添加距离信息
    distance_info = []
    if interface.immersion:
        distance_info = mp.AT2 + nb2msg(int(interface.distance(interface.target))) + mp.METERS
    
    # 如果需要显示指令信息
    order_info = []
    if interface.an_order_requiring_a_target_is_selected:
        order_info = mp.COMMA + interface.order.title
    
    # 构建初始消息（标题+距离+方向）
    d = title + distance_info + direction
    
    # 资源量信息（优先播报）
    resource_info = []
    if (hasattr(interface.target, "is_a_building") and interface.target.is_a_building and
        hasattr(interface.target, "resource_type") and interface.target.resource_type):
        # 如果同时有最大资源量，播报当前资源量和最大资源量
        if hasattr(interface.target, "resource_volume_max") and interface.target.resource_volume_max > 0:
            resource_info = (
                mp.COMMA
                + mp.CONTAINS
                + nb2msg(int(interface.target.resource_qty))
                + mp.ON
                + nb2msg(int(interface.target.resource_volume_max))
                + style.get("parameters", f"{interface.target.resource_type}_title")
            )
        # 没有最大资源量或为零，只播报当前资源量
        elif hasattr(interface.target, "resource_qty") and interface.target.resource_qty > 0:
            resource_info = (
                mp.COMMA
                + mp.CONTAINS
                + nb2msg(int(interface.target.resource_qty))
                + style.get("parameters", f"{interface.target.resource_type}_title")
            )
    
    # 其他描述信息（HP等）
    other_info = []
    if hasattr(interface.target, "description"):
        other_info = interface.target.description
    
    # 组合所有信息，按照：标题+距离+方向+资源信息+其他信息+指令
    d = d + resource_info + other_info + order_info
    
    vol = stereo(interface.x, interface.y, interface.target.x, interface.target.y, interface.o, no_distance=True)
    if max(vol) < 0.2:
        vol = 0.2, 0.2
    voice.item(mp.POSITIONAL_BEEP + d, *vol)


def _next_choice(choice, choices):
    sel = 0
    try:
        sel = choices.index(choice) + 1
    except ValueError:
        pass
    if sel >= len(choices):
        sel = 0
    return choices[sel]


def cmd_examine(interface):
    if interface.target:
        say_target(interface)
    elif interface.zoom_mode:
        # 在缩放模式下查看时，包含主方格名称
        interface.zoom.say(prefix=interface.zoom.current_main_square.title + [" "])
    else:
        from .game_navigation import say_square
        say_square(interface, interface.place)


def cmd_select_target(interface, inc, *types):
    inc = int(inc)
    choices = _object_choices(interface, inc, types)
    if choices:
        interface.target = _next_choice(interface.target, choices)
        say_target(interface)
    else:
        voice.item(mp.NOTHING)
        interface.target = None


def _cycle_square_target(interface, inc, predicate):
    """在当前方格内按条件循环选择目标（类似 TAB，但限定类型）。"""
    inc = int(inc)
    choices = []
    for o in list(interface.dobjets.values()):
        if is_selectable(interface, o) and predicate(o):
            choices.append(o)
    if not choices:
        voice.item(mp.NOTHING)
        interface.target = None
        return
    prioritize_items = _square_has_ground_items(interface)
    choices.sort(key=lambda x: _priority(interface, x, prioritize_items))
    if inc < 0:
        choices.reverse()
    interface.target = _next_choice(interface.target, choices)
    from .interface_modes import save_map_browse_target
    save_map_browse_target(interface)
    say_target(interface)


def cmd_select_deposit(interface, inc, resource_type):
    """在当前方格内含指定资源的矿点之间浏览。"""
    resource_type = str(resource_type)

    def ok(o):
        return (
            getattr(o, "resource_type", None) == resource_type
            and getattr(o, "qty", 0) > 0
        )

    _cycle_square_target(interface, inc, ok)


def cmd_select_meadow(interface, inc):
    """在当前方格内的草地之间浏览。"""
    def ok(o):
        return getattr(o, "type_name", None) == "meadow"

    _cycle_square_target(interface, inc, ok)


def cmd_select_passage(interface, inc):
    """在当前方格内的通道、桥梁之间浏览。"""
    def ok(o):
        if getattr(o, "is_an_exit", False):
            return True
        name = getattr(o, "type_name", None)
        if name == "wooden_bridge":
            return True
        if name == "buildingsite":
            model = getattr(o, "model", None)
            if model is not None and getattr(model, "shore_land", None) is not None:
                return True
        return name in ("bridge", "passage", "gate")

    _cycle_square_target(interface, inc, ok)


def _note_selected_unit_removed(interface, unit_id):
    """记录已选中单位被移除，以便稍后通过 upgrade_to 事件恢复选中。"""
    if unit_id not in interface.group:
        return
    interface.group.remove(unit_id)
    removals = getattr(interface, "_pending_selection_removals", None)
    if removals is None:
        removals = set()
        interface._pending_selection_removals = removals
    removals.add(unit_id)
    interface.previous_group = None


def transfer_group_selection_on_upgrade(interface, old_id, new_id):
    """单位升级变形后，把选中状态从旧 ID 迁移到新 ID。"""
    pending = getattr(interface, "_pending_upgrade_selections", None)
    if pending is None:
        pending = {}
        interface._pending_upgrade_selections = pending
    pending[old_id] = new_id

    if old_id in interface.group:
        interface.group[interface.group.index(old_id)] = new_id
        interface.previous_group = None
        return

    removals = getattr(interface, "_pending_selection_removals", None)
    if removals and old_id in removals:
        removals.discard(old_id)
        pending.pop(old_id, None)
        if new_id not in interface.group:
            interface.group.append(new_id)
        interface.previous_group = None


def apply_pending_upgrade_selections(interface):
    """在视野同步后，补全因事件顺序导致的延迟选中迁移。"""
    pending = getattr(interface, "_pending_upgrade_selections", None)
    removals = getattr(interface, "_pending_selection_removals", None)
    if not pending or not removals:
        return
    changed = False
    for old_id in list(removals):
        new_id = pending.get(old_id)
        if new_id is None or new_id not in interface.dobjets:
            continue
        removals.discard(old_id)
        del pending[old_id]
        if new_id not in interface.group:
            interface.group.append(new_id)
            changed = True
    if changed:
        interface.previous_group = None


def update_group(interface):
    apply_pending_upgrade_selections(interface)
    # 过滤有效的单位ID并去除重复项，保持顺序
    valid_units = [
        u
        for u in interface.group
        if u in interface.dobjets
        and interface.player.unit_under_allied_control(interface.dobjets[u].model)
    ]
    # 使用dict.fromkeys()去重，保持插入顺序
    interface.group = list(dict.fromkeys(valid_units))


def units(interface, even_if_no_menu=True, sort=False):
    def short_title_and_number(o):
        return (o.short_title, o.number)

    result = [
        interface.dobjets[u.id]
        for u in interface.player.allied_control_units
        if (
            even_if_no_menu
            or u.can_train
            or u.can_upgrade_to
            or u.orders
            or u.basic_skills
            or u.id in interface.dobjets
            and interface.dobjets[u.id].menu
        )
        and not getattr(u, "is_inside", False)
        and u.id in interface.dobjets
    ]
    if sort:
        result.sort(key=short_title_and_number)
    return result


def _summary_entries(group):
    entries = []
    for item in group:
        if isinstance(item, tuple) and len(item) == 2:
            title, omit_single_count = item
            entries.append((title, bool(omit_single_count)))
        else:
            entries.append((item, False))
    return entries


def summary(interface, group, brief=False):
    entries = _summary_entries(group)
    types = _remove_duplicates([e[0] for e in entries])
    if brief and len(types) > 2:
        return nb2msg(len(entries))
    result = []
    for t in types:
        if t == types[-1] and len(types) > 1:
            result += mp.AND
        elif t != types[0]:
            result += mp.COMMA
        matching = [e for e in entries if e[0] == t]
        count = len(matching)
        omit_single_count = matching[0][1] if matching else False
        if omit_single_count and count == 1:
            result += t
        else:
            result += nb2msg(count) + t
    return result


def place_summary(interface, place, me=True, zoom=None, brief=False):
    # 从未探索过的方格视为空白：不汇总小径/资源等（即使对侧出口曾被预记忆）
    scouted = getattr(interface, "scouted_squares", None) or ()
    scouted_before = getattr(interface, "scouted_before_squares", None) or ()
    if (
        place is not None
        and place not in scouted
        and place not in scouted_before
    ):
        return []

    enemies = []
    neutrals = []  # 中立 creep（computer_only ... neutral）单独归类，标注为"中立"而不是"敌人"
    animals = []  # 狩猎动物（鹿、羊等），标注为"动物"而非"中立/NPC"
    allies = []
    units_list = []
    resources = []

    def _is_neutral_unit(model):
        # neutral player 的单位 → 归入"中立"而不是"敌人"
        return getattr(getattr(model, "player", None), "neutral", False)

    def _unit_bucket(model):
        if is_wildlife_unit(model):
            return animals
        if _is_neutral_unit(model):
            return neutrals
        return enemies

    def _append_unit_title(bucket, obj, obj_title):
        bucket.append((obj_title, summary_omit_single_count(obj.model)))

    def _hostile_script_creep_among_ai_allies(model):
        owner = getattr(model, "player", None)
        observer = interface.player
        return (
            owner is not None
            and owner in observer.allied
            and owner is not observer
            and getattr(observer, "is_script_npc", False)
            and getattr(owner, "is_script_npc", False)
            and not getattr(owner, "neutral", False)
            and not player_is_wildlife_only(owner)
        )

    for obj in list(interface.dobjets.values()):
    # 检查对象是否在指定的place中
        if not obj.is_in(place):
            continue
        
    # 检查缩放模式
        if zoom and not zoom.contains(obj):
            continue
        
        if not obj.short_title:
            continue
        
        # 在第一人称RPG模式下为对象标题添加距离信息
        obj_title = obj.short_title[:]  # 复制标题
        if interface.immersion:
            distance_to_obj = int(interface.distance(obj))
            obj_title = obj_title + nb2msg(distance_to_obj) + mp.METERS
        
        # 处理容器内的单位
        if hasattr(obj, 'is_inside') and obj.is_inside:
            container = obj.place.container
            if container_visible_from_place(container, place):
                if obj.model.player is interface.player:
                    _append_unit_title(units_list, obj, obj_title)
                elif is_wildlife_unit(obj.model):
                    _append_unit_title(animals, obj, obj_title)
                elif _hostile_script_creep_among_ai_allies(obj.model):
                    _append_unit_title(enemies, obj, obj_title)
                elif interface.player.is_an_enemy(obj.model):
                    _append_unit_title(_unit_bucket(obj.model), obj, obj_title)
                elif obj.model.player in interface.player.allied and obj.model.player is not interface.player:
                    _append_unit_title(allies, obj, obj_title)
                continue

        # 处理普通单位
        if obj.is_in(place):
            if obj.model.player is interface.player:
                _append_unit_title(units_list, obj, obj_title)
            elif is_wildlife_unit(obj.model):
                _append_unit_title(animals, obj, obj_title)
            elif _hostile_script_creep_among_ai_allies(obj.model):
                _append_unit_title(enemies, obj, obj_title)
            elif interface.player.is_an_enemy(obj.model):
                _append_unit_title(_unit_bucket(obj.model), obj, obj_title)
            elif obj.model.player in interface.player.allied and obj.model.player is not interface.player:
                _append_unit_title(allies, obj, obj_title)
            elif getattr(obj.model, "resource_type", None) is not None:
                resources.append(obj_title)
            elif getattr(obj.model, "default_order", None) == "pickup":
                resources.append(obj_title)

# 构建结果字符串
    result = []
    if enemies:
        result += mp.COMMA + summary(interface, enemies, brief=brief) + mp.ENEMY
    if animals:
        result += mp.COMMA + summary(interface, animals, brief=brief) + mp.ANIMAL
    if neutrals:
        # 中立放在敌人之后、盟友之前；用 mp.NEUTRAL 取代 mp.ENEMY
        result += mp.COMMA + summary(interface, neutrals, brief=brief) + mp.NEUTRAL
    if me and allies:
        result += mp.COMMA + summary(interface, allies) + mp.ALLY
    if me and units_list:
        result += mp.COMMA + summary(interface, units_list)
    if resources and (not enemies or not brief):
        result += mp.COMMA + summary(interface, resources)
    return result


def _orders_txt_has_content(orders_txt):
    """``orders_txt`` 末尾总带 COMMA；无实质命令时只有 COMMA token。"""
    if not orders_txt:
        return False
    trimmed = list(orders_txt)
    comma = mp.COMMA[0] if mp.COMMA else None
    while trimmed and comma is not None and trimmed[-1] == comma:
        trimmed.pop()
    return bool(trimmed)



def _multi_unit_titles_msg(interface, group_ids):
    """同型多选时直接拼数量+标题，避免为每个单位建 summary 条目。"""
    if not group_ids:
        return []
    first = interface.dobjets[group_ids[0]]
    type_name = first.type_name
    short_title = first.short_title
    omit = summary_omit_single_count(first.model)
    for uid in group_ids[1:]:
        unit = interface.dobjets[uid]
        if (
            unit.type_name != type_name
            or summary_omit_single_count(unit.model) != omit
        ):
            titles = [
                (
                    interface.dobjets[x].short_title,
                    summary_omit_single_count(interface.dobjets[x].model),
                )
                for x in group_ids
            ]
            return summary(interface, titles)
    count = len(group_ids)
    if omit and count == 1:
        return short_title
    return nb2msg(count) + short_title


def _ids_matching_types(interface, types, local, idle):
    """单次遍历世界单位模型，不经过 units()/menu/sort。"""
    type_set = set(types)
    local_place = interface.place
    ids = []
    for u in interface.player.allied_control_units:
        if u.type_name not in type_set:
            continue
        if getattr(u, "is_inside", False) or u.id not in interface.dobjets:
            continue
        ev = interface.dobjets[u.id]
        if local:
            if interface.zoom_mode:
                if not interface.zoom.contains(ev):
                    continue
            elif not ev.is_in(local_place):
                continue
        if idle and u.orders:
            continue
        ids.append(u.id)
    return ids


def _group_has_single_title_type(interface, group_ids):
    if not group_ids:
        return False
    first = interface.dobjets[group_ids[0]]
    type_name = first.type_name
    omit = summary_omit_single_count(first.model)
    for uid in group_ids[1:]:
        unit = interface.dobjets[uid]
        if unit.type_name != type_name or summary_omit_single_count(unit.model) != omit:
            return False
    return True


def say_group(interface, prefix=[]):
    update_group(interface)
    if len(interface.group) == 1:
        u = interface.dobjets[interface.group[0]]
        voice.item(prefix + mp.YOU_CONTROL + u.ext_title + u.orders_txt)
    elif len(interface.group) > 1:
        group_ids = [x for x in interface.group if x in interface.dobjets]
        orders = [interface.dobjets[x].orders_txt for x in group_ids]
        titles_msg = _multi_unit_titles_msg(interface, group_ids)
        msg = list(prefix)
        if prefix:
            msg += mp.COMMA
        msg += mp.YOU_CONTROL + titles_msg
        if len(_remove_duplicates(orders)) == 1:
            if _orders_txt_has_content(orders[0]):
                msg += mp.COMMA + orders[0]
        else:
            if _group_has_single_title_type(interface, group_ids):
                msg += mp.COMMA + summary(interface, orders)
        voice.item(msg)
    else:
        msg = list(prefix)
        if prefix:
            msg += mp.COMMA
        voice.item(msg + mp.NO_UNIT_CONTROLLED)


def tell_enemies_in_square(interface, place):
    enemies = []
    neutrals = []
    animals = []
    for x in list(interface.dobjets.values()):
        if not (x.is_in(place) and interface.player.is_an_enemy(x.model)):
            continue
        entry = (x.short_title, summary_omit_single_count(x.model))
        if is_wildlife_unit(x.model):
            animals.append(entry)
        elif getattr(getattr(x.model, "player", None), "neutral", False):
            neutrals.append(entry)
        else:
            enemies.append(entry)
    if enemies:
        voice.info(
            summary(interface, enemies, brief=True) + mp.ENEMY + mp.AT + place.title
        )
    if animals:
        voice.info(
            summary(interface, animals, brief=True) + mp.ANIMAL + mp.AT + place.title
        )
    if neutrals:
        voice.info(
            summary(interface, neutrals, brief=True) + mp.NEUTRAL + mp.AT + place.title
        )


def units_alert(interface, units_list, msg_end, brief=True):
    places = {x[1] for x in units_list if x[1] is not None}
    for place in places:
        units_in_place = [
            (x[0], x[2] if len(x) > 2 else False)
            for x in units_list
            if x[1] is place
        ]
        s = summary(interface, units_in_place, brief=brief)
        if s:
            voice.info(s + msg_end + mp.AT + place.title)
    while units_list:
        units_list.pop()


def units_alert_if_needed(interface, place=None):
    if (interface.neutralized_units or interface.lost_units or interface.new_enemy_units) and (
        getattr(interface, 'previous_units_alert', None) is None
        or time.time() > interface.previous_units_alert + 10
    ):
        units_alert(interface, interface.neutralized_units, mp.NEUTRALIZED, brief=False)
        units_alert(interface, interface.lost_units, mp.LOST)
        units_alert(interface, interface.new_enemy_units, mp.ENEMY)
        if place:
            tell_enemies_in_square(interface, place)  # if lost fight
        interface.previous_units_alert = time.time()


def command_unit(interface, unit, silent=False):
    if not silent:
        voice.item(unit.ext_title + unit.orders_txt + mp.AWAITING_YOUR_ORDERS)
    interface.group = [unit.id]


def cmd_command_unit(interface):
    if interface.target in units(interface):
        command_unit(interface, interface.target)


def _select_unit(interface, inc, types, local, idle, even_if_no_menu, silent=False):
    units_list = units(interface, even_if_no_menu=even_if_no_menu, sort=True)
    if types:
        units_list = [x for x in units_list if x.type_name in types]
    if local:
        if interface.zoom_mode:
            units_list = [x for x in units_list if interface.zoom.contains(x)]
        else:
            units_list = [x for x in units_list if x.is_in(interface.place)]
    if idle:
        units_list = [x for x in units_list if not x.orders]
    if not units_list:
        interface.group = []
        return
    sel = -1  # if next (+1) => 0, if previous (-1) => -2 < 0 => last
    for i, u in enumerate(units_list):
        if u.id in interface.group:
            sel = i
            break
    sel += inc
    if sel < 0:
        sel = len(units_list) - 1
    if sel >= len(units_list):
        sel = 0
    command_unit(interface, units_list[sel], silent=silent)
    interface.order = None


def _is_building_keyboard_slot(name):
    if name == "building":
        return True
    if name.startswith("building"):
        suffix = name[8:]
        return suffix.isdigit() and 1 <= int(suffix) <= 16
    return False


def _effective_keyboard_query(keyboard_types):
    """Classic ``building`` also matches numbered building1–building16 slots."""
    wanted = set(keyboard_types)
    if "building" in wanted:
        wanted.update(f"building{i}" for i in range(1, 17))
    return wanted


def _unit_matches_keyboard_type(unit_type, keyboard_types):
    unit_keys = style.get(unit_type, "keyboard") or []
    return bool(set(unit_keys) & _effective_keyboard_query(keyboard_types))


def _arrange(args):
    local = "local" in args
    idle = "idle" in args
    even_if_no_menu = "even_if_no_menu" in args
    keyboard_types = [
        x for x in args if x not in ("local", "idle", "even_if_no_menu")
    ]
    if not even_if_no_menu and any(
        k != "building" and _is_building_keyboard_slot(k) for k in keyboard_types
    ):
        # building1–16：纯建筑（如星际孵化场）往往无菜单，须跳过菜单过滤
        # 通用 building（经典 W）：仍过滤无命令建筑；CTRL+W 显式 even_if_no_menu
        even_if_no_menu = True
    types = [
        x
        for x in style.classnames()
        if style.has(x, "keyboard")
        and _unit_matches_keyboard_type(x, keyboard_types)
    ]
    if (
        keyboard_types and not types
    ):  # no keyboard type actually exists in the style
        types = [None]  # will select nothing
    return types, local, idle, even_if_no_menu


def _regroup(interface, portion, types, local, idle, unused__even_if_no_menu):
    update_group(interface)
    if interface.group:
        initial_unit = interface.dobjets[interface.group[0]]
        if initial_unit.is_in(interface.place):
            local_place = interface.place
        else:
            local_place = initial_unit.place
        if not types:
            types = []
            for _id in interface.group:
                if interface.dobjets[_id].type_name not in types:
                    types.append(interface.dobjets[_id].type_name)
        interface.group = []
        units_list = units(interface)
        for t in types:
            m = [
                x.id
                for x in units_list
                if x.type_name == t
                and (
                    not local
                    or interface.zoom_mode
                    and interface.zoom.contains(x)
                    or not interface.zoom_mode
                    and x.is_in(local_place)
                )
                and (not idle or not x.orders)
            ]
            interface.group += m[: len(m) // portion]
        if initial_unit.id not in interface.group and initial_unit.type_name in types:
            if interface.group:
                interface.group.pop()
            interface.group.append(initial_unit.id)
    say_group(interface)


def cmd_unit_status(interface):
    if interface.group:
        place_title = interface.dobjets[interface.group[0]].place.title
    else:
        place_title = getattr(interface.place, "title", [])
    say_group(interface, place_title)
    if interface.group:
        interface.follow_mode = True
        from .game_navigation import _follow_if_needed
        _follow_if_needed(interface)


def cmd_unit_hp_status(interface):
    if len(interface.group) == 1:
        u = interface.dobjets[interface.group[0]]
        voice.item(u.description)


def cmd_group(interface, portion, *args):
    portion = int(portion)
    _regroup(interface, portion, *_arrange(args))


def cmd_ungroup(interface):
    if len(interface.group) > 1:
        interface.group = [interface.group[0]]
    say_group(interface)


def cmd_select_unit(interface, inc, *args):
    inc = int(inc)
    _select_unit(interface, inc, *_arrange(args))


def cmd_select_units(interface, *args):
    types, local, idle, even_if_no_menu = _arrange(args)
    if types == [None]:
        interface.group = []
        interface.order = None
        say_group(interface)
        return
    if not local:
        # Classic Ctrl+D (global worker): one model scan, no seed/regroup/units().
        interface.group = _ids_matching_types(interface, types, local, idle)
        interface.order = None
        interface.previous_group = None
        say_group(interface)
        return
    _select_unit(interface, 1, types, local, idle, True, silent=True)
    _regroup(interface, 1, types, local, idle, even_if_no_menu)


def cmd_set_group(interface, name, *args):
    send_order(interface, "reset_group", name, args)
    send_order(interface, "join_group", name, args)


def cmd_append_group(interface, name, *args):
    send_order(interface, "join_group", name, args)


def cmd_recall_group(interface, name, *args):
    if name in interface.player.groups:
        interface.group = [u.id for u in interface.player.groups[name]]
    else:
        interface.group = []
    say_group(interface)


def send_order(interface, order, target, args):
    from ..lib import group as group_module
    queue_order = int("queue_order" in args)
    imperative = int("imperative" in args)
    # send the order only to the concerned members of the group
    # (to avoid (precedently) unnecessary "order impossible" alerts
    #  or (now) a "wrong order" warning,
    #  and for the assertion in _group_has_enough_mana() in worldunit.py)
    if order in ("default", "join_group"):
        g = interface.group
    else:
        g = [uid for uid in interface.group if order in interface.dobjets[uid].menu]
    if g != getattr(interface, 'previous_group', None):  # to save bandwidth
        interface.server.write_line("control " + group_module.encode(g))
        # make a copy to make sure that it is not modified later
        interface.previous_group = g[:]
    if target is not None:
        order = f"{order} {target}"
    interface.server.write_line("order {} {} {}".format(queue_order, imperative, order))


def _entity_map_square(entity):
    """实体所在地图格（站在草地上时返回父方格，而非草地本身）。"""
    if entity is None:
        return None
    place = getattr(entity, "place", None)
    if place is None:
        return None
    if getattr(place, "type_name", None) == "meadow":
        return getattr(place, "place", None)
    return place


def send_inventory_order(interface, order, item_id, unit_id=None):
    """向指定单位发送背包相关命令（不经过命令菜单过滤）。"""
    from ..lib import group as group_module
    if unit_id is None:
        unit_id = getattr(interface, "_inventory_screen_unit_id", None)
        if unit_id is None:
            unit_id = getattr(interface, "_equipment_screen_unit_id", None)
    if unit_id is None and interface.group:
        unit_id = interface.group[0]
    if unit_id is None:
        return
    g = [unit_id]
    interface.server.write_line("control " + group_module.encode(g))
    interface.previous_group = g[:]
    parts = [order, str(item_id)]
    if order == "drop":
        nav_square = getattr(interface, "place", None)
        unit_obj = interface.dobjets.get(unit_id)
        unit_square = _entity_map_square(unit_obj)
        if (
            nav_square is not None
            and getattr(nav_square, "id", None) is not None
            and unit_square is not nav_square
        ):
            parts.append(str(nav_square.id))
    interface.server.write_line("order 0 0 " + " ".join(parts))


def send_gear_order(interface, order, unit_id=None, *args):
    """向指定单位发送装备栏相关命令（可无额外参数）。"""
    from ..lib import group as group_module
    if unit_id is None:
        unit_id = getattr(interface, "_equipment_screen_unit_id", None)
        if unit_id is None:
            unit_id = getattr(interface, "_inventory_screen_unit_id", None)
    if unit_id is None and interface.group:
        unit_id = interface.group[0]
    if unit_id is None:
        return
    g = [unit_id]
    interface.server.write_line("control " + group_module.encode(g))
    interface.previous_group = g[:]
    parts = [order] + [str(a) for a in args]
    interface.server.write_line("order 0 0 " + " ".join(parts))


# 菜单警报相关功能
def _get_relevant_menu(menu):
    _m = menu[:]
    for x in [
        "stop",
        "cancel_training",
        "cancel_upgrading",
        "cancel_building",
        "mode_offensive",
        "mode_defensive",
        "load",
        "load_all",
        "unload",
        "unload_all",
    ]:
        if x in _m:
            _m.remove(x)
    return _m


def _menu_has_increased(interface, type_name, menu):
    for i in _get_relevant_menu(menu):
        if i not in interface.previous_menus[type_name]:
            return True
    return False


def _remember_menu(interface, type_name, menu):
    for i in _get_relevant_menu(menu):
        if i not in interface.previous_menus[type_name]:
            interface.previous_menus[type_name].append(i)


def _send_menu_alert_if_needed(interface, type_name, menu, title):
    if type_name not in interface.previous_menus:
        interface.previous_menus[type_name] = []
    elif _menu_has_increased(interface, type_name, menu):
        # Check if the unit type is a resource-producing building
        # For units like gold_house which have auto_production=1 and production_type=resource*
        is_resource_producer = False
        for u in interface.player.units:
            if u.type_name == type_name and hasattr(u, "auto_production") and u.auto_production:
                # Check if production_type is a resource type (starts with "resource")
                if hasattr(u, "production_type") and isinstance(u.production_type, str) and u.production_type.startswith("resource"):
                    is_resource_producer = True
                    break
        
        # Only send menu alert if it's not a resource producer
        if not is_resource_producer:
            voice.info(mp.MENU_OF + title + mp.CHANGED)
    _remember_menu(interface, type_name, menu)


def send_menu_alerts_if_needed(interface):
    if "menu_changed" not in config.verbosity:
        return
    done = []
    for u in interface.player.units:
        u = EntityView(interface, u)
        if u.type_name not in done:
            _send_menu_alert_if_needed(
                interface, u.type_name, u.strict_menu, u.short_title
            )
            done.append(u.type_name)


# 导出的函数供其他模块使用
__all__ = [
    'say_target', 'cmd_examine', 'cmd_select_target',
    'cmd_select_deposit', 'cmd_select_meadow', 'cmd_select_passage',
    'update_group', 
    'units', 'summary', 'place_summary', 'say_group', 'tell_enemies_in_square',
    'units_alert', 'units_alert_if_needed', 'command_unit', 'cmd_command_unit',
    'cmd_unit_status', 'cmd_unit_hp_status', 'cmd_group', 'cmd_ungroup',
    'cmd_select_unit', 'cmd_select_units', 'cmd_set_group', 'cmd_append_group',
    'cmd_recall_group', 'send_order', 'send_menu_alerts_if_needed',
    'is_visible', 'is_selectable', '_is_ground_item', '_square_has_ground_items',
    '_object_choices', '_remove_duplicates', '_priority', '_next_choice'
]