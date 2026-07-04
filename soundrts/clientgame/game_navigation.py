import math
import time

from .. import config
from .. import msgparts as mp
from .. import parameters
from ..clientgameentity import EntityView
from ..clientgameentity.properties import summary_omit_single_count
from ..clientgamefocus import Zoom
from ..clientmedia import voice
from ..lib.sound import psounds
from ..definitions import style
from ..lib.log import exception, debug
from ..lib.msgs import localize_voice_msg, nb2msg
from ..lib.sound import distance, stereo
from ..worldroom import Square


# 第一人称RPG模式相关功能
def toggle_immersion(interface):
    interface.immersion = not interface.immersion
    
    if interface.immersion:
        # 保存当前键位绑定
        interface._original_bindings = interface._bindings
        
        # 创建新的键位绑定对象并加载RPG模式的键位绑定
        from ..lib.bindings import Bindings
        interface._bindings = Bindings()
        
        try:
            # 先加载基础绑定
            base_bindings = interface.get_bindings()
            
            from .interface_modes import rpg_bindings_with_overrides

            rpg_bindings_text = rpg_bindings_with_overrides()
            if rpg_bindings_text.strip():
                combined_bindings = (
                    base_bindings + "\n\n; RPG Mode Overrides\n" + rpg_bindings_text
                )
                interface._bindings.load(combined_bindings, interface)
            else:
                interface._bindings.load(base_bindings, interface)
            
            from .game_unit_control import cmd_unit_status
            cmd_unit_status(interface)
            voice.item(mp.FIRST_PERSON_MODE if hasattr(mp, "FIRST_PERSON_MODE") else ["第一人称模式"])
            
        except Exception as e:
            # 如果加载失败，回退到原来的键位绑定
            from ..lib.log import warning, exception as log_exception
            log_exception(f"无法加载RPG模式键位绑定: {e}")
            interface._bindings = interface._original_bindings
            interface._original_bindings = None
    else:
        # 恢复原来的键位绑定
        if hasattr(interface, "_original_bindings") and interface._original_bindings:
            interface._bindings = interface._original_bindings
            interface._original_bindings = None
        else:
            from .interface_modes import restore_active_bindings
            restore_active_bindings(interface)
        voice.item(mp.MAP_MODE if hasattr(mp, "MAP_MODE") else ["地图模式"])
    interface.follow_mode = interface.immersion


def cmd_immersion(interface):
    if not interface.immersion:
        toggle_immersion(interface)


def cmd_escape(interface):
    from .interface_modes import handle_escape
    handle_escape(interface)


def cmd_ui_escape(interface):
    from .interface_modes import handle_escape
    handle_escape(interface)


# 旋转相关功能
def cmd_rotate_left(interface):
    if interface.group:
        interface.dobjets[interface.group[0]].o += 45
        interface.o += 45
        say_compass(interface)
        psounds.update()


def cmd_rotate_right(interface):
    if interface.group:
        interface.dobjets[interface.group[0]].o -= 45
        interface.o -= 45
        say_compass(interface)
        psounds.update()


def cmd_turn_around(interface):
    """180度转身（掉头）"""
    if interface.group:
        interface.dobjets[interface.group[0]].o += 180
        interface.o += 180
        say_compass(interface)
        psounds.update()


def direction_to_msgpart(o):
    o = round(o / 45) * 45
    while o >= 360:
        o -= 360
    while o < 0:
        o += 360
    if o == 0:
        return mp.EAST
    elif o == 45:
        return mp.NORTHEAST
    elif o == 90:
        return mp.NORTH
    elif o == 135:
        return mp.NORTHWEST
    elif o == 180:
        return mp.WEST
    elif o == 225:
        return mp.SOUTHWEST
    elif o == 270:
        return mp.SOUTH
    elif o == 315:
        return mp.SOUTHEAST


def say_compass(interface):
    compass = direction_to_msgpart(interface.o)
    if compass != getattr(interface, '_previous_compass', None):
        voice.item(compass)
        interface._previous_compass = compass


# RPG移动功能
def cmd_move_forward(interface):
    """第一人称模式下向前移动"""
    if not interface.immersion or not interface.group:
        voice.item(mp.BEEP)
        return
    
    # 获取当前选中的单位
    unit_id = interface.group[0]
    if unit_id not in interface.dobjets:
        voice.item(mp.BEEP)
        return
        
    unit = interface.dobjets[unit_id]
    current_orientation = unit.o
    
    # 计算前进方向的目标方格
    target_square = _get_target_square_by_orientation(interface, current_orientation)
    if target_square:
        # 检查路径连通性和边界
        if _check_rpg_movement_collision(interface, target_square):
            # 发送强制移动命令
            from .game_unit_control import send_order
            send_order(interface, "go", target_square.id, ["imperative"])
        # 如果被阻挡，_check_rpg_movement_collision已经播放了阻挡音效
    else:
        # 移动到地图边界外，播放与浏览地图一致的阻挡声音
        voice.item(style.get("parameters", "no_path_in_this_direction"))


def cmd_move_backward(interface):
    """第一人称模式下向后移动"""
    if not interface.immersion or not interface.group:
        voice.item(mp.BEEP)
        return
    
    # 获取当前选中的单位
    unit_id = interface.group[0]
    if unit_id not in interface.dobjets:
        voice.item(mp.BEEP)
        return
        
    unit = interface.dobjets[unit_id]
    current_orientation = unit.o
    
    # 计算后退方向的目标方格（与前进相反）
    backward_orientation = (current_orientation + 180) % 360
    target_square = _get_target_square_by_orientation(interface, backward_orientation)
    if target_square:
        # 检查路径连通性和边界
        if _check_rpg_movement_collision(interface, target_square):
            # 发送强制移动命令
            from .game_unit_control import send_order
            send_order(interface, "go", target_square.id, ["imperative"])
        # 如果被阻挡，_check_rpg_movement_collision已经播放了阻挡音效
    else:
        # 移动到地图边界外，播放与浏览地图一致的阻挡声音
        voice.item(style.get("parameters", "no_path_in_this_direction"))


def cmd_move_left(interface):
    """第一人称模式下向左移动"""
    if not interface.immersion or not interface.group:
        voice.item(mp.BEEP)
        return
    
    # 获取当前选中的单位
    unit_id = interface.group[0]
    if unit_id not in interface.dobjets:
        voice.item(mp.BEEP)
        return
        
    unit = interface.dobjets[unit_id]
    current_orientation = unit.o
    
    # 计算左移方向的目标方格（向左90度）
    left_orientation = (current_orientation + 90) % 360
    target_square = _get_target_square_by_orientation(interface, left_orientation)
    if target_square:
        # 检查路径连通性和边界
        if _check_rpg_movement_collision(interface, target_square):
            # 发送强制移动命令
            from .game_unit_control import send_order
            send_order(interface, "go", target_square.id, ["imperative"])
        # 如果被阻挡，_check_rpg_movement_collision已经播放了阻挡音效
    else:
        # 移动到地图边界外，播放与浏览地图一致的阻挡声音
        voice.item(style.get("parameters", "no_path_in_this_direction"))


def cmd_move_right(interface):
    """第一人称模式下向右移动"""
    if not interface.immersion or not interface.group:
        voice.item(mp.BEEP)
        return
    
    # 获取当前选中的单位
    unit_id = interface.group[0]
    if unit_id not in interface.dobjets:
        voice.item(mp.BEEP)
        return
        
    unit = interface.dobjets[unit_id]
    current_orientation = unit.o
    
    # 计算右移方向的目标方格（向右90度）
    right_orientation = (current_orientation - 90) % 360
    target_square = _get_target_square_by_orientation(interface, right_orientation)
    if target_square:
        # 检查路径连通性和边界
        if _check_rpg_movement_collision(interface, target_square):
            # 发送强制移动命令
            from .game_unit_control import send_order
            send_order(interface, "go", target_square.id, ["imperative"])
        # 如果被阻挡，_check_rpg_movement_collision已经播放了阻挡音效
    else:
        # 移动到地图边界外，播放与浏览地图一致的阻挡声音
        voice.item(style.get("parameters", "no_path_in_this_direction"))


def _check_rpg_movement_collision(interface, target_square):
    """检查普通RPG移动时的路径连通性和边界限制
    
    参数:
        target_square: 目标方格对象
        
    返回:
        bool: True表示可以移动，False表示被阻挡
    """
    # 检查目标是否为当前方格
    if target_square == interface.place:
        # 试图移动到同一个方格，被阻挡
        voice.item(style.get("parameters", "no_path_in_this_direction"))
        return False
    
    # 计算移动方向
    current_col, current_row = coords_in_map(interface, interface.place)
    target_col, target_row = coords_in_map(interface, target_square)
    
    dxc = target_col - current_col
    dyc = target_row - current_row
    
    # 检查是否超出地图边界
    if (target_col < 0 or target_col > interface.xcmax or 
        target_row < 0 or target_row > interface.ycmax):
        # 超出地图边界
        voice.item(style.get("parameters", "no_path_in_this_direction"))
        return False
    
    # 使用新的路径检查逻辑
    has_exit = _check_exit_connection(interface, interface.place, target_square)
    
    if not has_exit:
        # 没有出口连接，使用浏览地图的阻挡声音
        prefix, _ = _get_prefix_and_collision(interface, target_square, dxc, dyc)
        voice.item(prefix)
        return False
    else:
        # 路径畅通，可以移动
        return True


def _get_target_square_by_orientation(interface, orientation):
    """根据朝向角度计算目标方格"""
    if not interface.place:
        return None
        
    # 获取当前方格坐标
    current_col, current_row = coords_in_map(interface, interface.place)
    
    # 将角度转换为方格偏移量
    # 游戏中0度是东，90度是北，180度是西，270度是南
    # 但我们使用标准的数学角度系统
    
    # 标准化角度到0-360范围
    orientation = orientation % 360
    
    # 计算目标方格的偏移量
    delta_col = 0
    delta_row = 0
    
    # 根据朝向确定移动方向
    if 315 <= orientation or orientation < 45:  # 东 (0度方向)
        delta_col = 1
    elif 45 <= orientation < 135:  # 北 (90度方向)
        delta_row = 1
    elif 135 <= orientation < 225:  # 西 (180度方向)
        delta_col = -1
    elif 225 <= orientation < 315:  # 南 (270度方向)
        delta_row = -1
    
    # 计算目标坐标
    target_col = current_col + delta_col
    target_row = current_row + delta_row
    
    # 检查目标坐标是否在地图范围内
    if (0 <= target_col <= interface.xcmax and 
        0 <= target_row <= interface.ycmax):
        
        target_square = interface.world.grid.get((target_col, target_row))
        return target_square
    
    return None


def _check_exit_connection(interface, current_square, target_square):
    """直接检查两个方格之间是否有未被阻挡的出口连接
    在缩放模式下，还会检查用户当前位置是否接近出口
    
    参数:
        current_square: 当前方格
        target_square: 目标方格
        
    返回:
        bool: True表示有出口连接，False表示没有
    """
    # 检查基本条件
    if current_square is None or target_square is None:
        return False
    
    if current_square == target_square:
        return True
    
    # 如果在未探索的区域或水域，允许移动（与_get_prefix_and_collision逻辑一致）
    if (current_square not in interface.scouted_before_squares
        or (current_square.is_water or target_square.is_water)
        and current_square.height == target_square.height
        or _shouldnt_collide(interface)):
        return True
    
    # 获取可用的出口
    from .game_unit_control import is_selectable
    exits = [
        o for o in list(interface.dobjets.values())
        if o.is_in(current_square)
        and is_selectable(interface, o)
        and o.is_an_exit
        and not o.is_blocked(interface.player)
    ]
    
    # 计算移动方向
    current_col, current_row = coords_in_map(interface, current_square)
    target_col, target_row = coords_in_map(interface, target_square)
    dxc = target_col - current_col
    dyc = target_row - current_row
    
    # 如果不在缩放模式下，使用原来的逻辑（基于方格中心）
    if not (interface.immersion and interface.zoom_mode):
        # 使用方格中心作为参考点
        x, y = (current_col + 0.5) * interface.square_width, (current_row + 0.5) * interface.square_width
    else:
        # 在缩放模式下，使用用户当前的精确位置
        if interface.group and interface.group[0] in interface.dobjets:
            unit = interface.dobjets[interface.group[0]]
            x, y = unit.x, unit.y
        else:
            # 如果没有控制的单位，回退到缩放区域的中心
            x, y = interface.zoom.obs_pos()
            x *= 1000.0  # 转换回游戏坐标系统
            y *= 1000.0
    
    # 检查出口是否在移动方向上且连接到目标方格
    for o in exits:
        # 首先检查出口是否连接到目标方格
        exit_connects_to_target = False
        if (hasattr(o, 'other_side') and o.other_side and 
            o.other_side.place is target_square):
            exit_connects_to_target = True
            
        if not exit_connects_to_target:
            continue
            
        # 检查出口是否在移动方向上
        direction_correct = False
        if (dxc == 1 and o.x > x or
            dxc == -1 and o.x < x or
            dyc == 1 and o.y > y or
            dyc == -1 and o.y < y):
            direction_correct = True
            
        # 在缩放模式下，还要检查用户是否足够接近出口
        if interface.immersion and interface.zoom_mode and direction_correct:
            # 计算用户到出口的距离
            distance_to_exit = ((x - o.x) ** 2 + (y - o.y) ** 2) ** 0.5
            
            # 获取缩放精细度，计算允许的最大距离
            precision = getattr(interface, '_zoom_precision', 3)
            # 计算子区域的大小（以游戏单位为准）
            sub_width = (current_square.xmax - current_square.xmin) / precision
            sub_height = (current_square.ymax - current_square.ymin) / precision
            max_sub_size = max(sub_width, sub_height)
            
            # 允许的最大距离为子区域大小的一半再加上一点容差
            # 这确保只有当用户在出口附近的子区域时才能使用出口
            max_allowed_distance = max_sub_size * 0.7  # 70%的子区域大小作为阈值
            
            if distance_to_exit <= max_allowed_distance:
                return True
        elif direction_correct and not (interface.immersion and interface.zoom_mode):
            # 非缩放模式下，只要方向正确就允许通过
            return True
    
    # 没有找到可用的出口连接
    return False


# 缩放模式功能
def cmd_toggle_zoom(interface):
    if not interface.place:
        return
    interface.zoom_mode = not interface.zoom_mode
    if interface.zoom_mode:
        interface.zoom = Zoom(interface)
        interface.target = None
        interface.zoom.say(prefix=mp.ZOOM + mp.IS_NOW_ON + mp.COMMA)
    else:
        _select_and_say_square(
            interface, interface.place, prefix=mp.ZOOM + mp.IS_NOW_OFF + mp.COMMA
        )


# 方格选择和移动功能
def _select_and_say_square(interface, square, prefix=[]):
    # 注意：是否跨越主区域的判断应在调用方完成，并将主区域前缀合入 prefix
    move_to_square(interface, square)
    interface.target = None
    say_square(interface, square, prefix)
    interface.follow_mode = False


def move_to_square(interface, square):
    if square.__class__.__name__ == "Inside":
        square = square.outside
    if interface.place is not square and coords_in_map(interface, square) != (-1, -1):
        interface.place = square
        if parameters.d.get("silence_previous_square", True):
            _silence_square(interface)
        from .game_display import display
        display(interface)


def _silence_square(interface):
    for o in list(interface.dobjets.values()):
        if not o.is_in(interface.place):
            o.stop()
    from ..lib import sound
    sound.stop(stop_voice_too=False)  # cut the long non-looping environment sounds


def _square_has_building_land(place):
    for o in getattr(place, "objects", ()):
        if getattr(o, "is_a_building_land", False) and not getattr(o, "is_an_exit", False):
            return True
    return False


def _building_land_terrain_type_name(place):
    from ..lib.square_terrain_rules import winning_building_land_terrain_entry

    entry = winning_building_land_terrain_entry(getattr(place, "objects", ()))
    return entry["name"] if entry else None


def _square_is_water(place, x=None, y=None):
    if x is not None and y is not None and hasattr(place, "is_water_at"):
        return place.is_water_at(x, y)
    return getattr(place, "is_water", False)


def _append_terrain_title(result, terrain_name):
    if not terrain_name:
        return
    title = style.get(terrain_name, "title")
    if title:
        result += mp.COMMA + title


def _square_terrain(place, x=None, y=None):
    from ..lib.square_terrain_rules import resolve_square_layers

    result = []
    layers = resolve_square_layers(place, x, y)
    for name in layers["static_voices"]:
        _append_terrain_title(result, name)
    if layers["dynamic_voice"]:
        _append_terrain_title(result, layers["dynamic_voice"])
    if layers["feature_voice"]:
        _append_terrain_title(result, layers["feature_voice"])
    if layers["high_ground_voice"]:
        _append_terrain_title(result, layers["high_ground_voice"])
    if layers["building_land_voice"]:
        _append_terrain_title(result, layers["building_land_voice"])
    return result


def square_postfix(interface, place, zoom=None):
    postfix = []
    terrain_x = terrain_y = None
    if zoom is not None:
        terrain_x = (zoom.xmin + zoom.xmax) / 2.0
        terrain_y = (zoom.ymin + zoom.ymax) / 2.0
    if place in interface.scouted_squares:
        postfix += _square_terrain(place, terrain_x, terrain_y)
        from .build_field_voice import square_build_field_msgs
        fields = square_build_field_msgs(interface, place)
        if fields:
            postfix += mp.COMMA + fields
    elif place in interface.scouted_before_squares:
        postfix += _square_terrain(place, terrain_x, terrain_y)
        postfix += mp.COMMA + mp.IN_THE_FOG
    else:
        postfix += mp.COMMA + mp.UNKNOWN
    return postfix


def say_square(interface, place, prefix=[]):
    if place is None:
        return
    postfix = square_postfix(interface, place)
    from .game_unit_control import place_summary
    voice.item(
        localize_voice_msg(
            prefix + place.title + postfix + place_summary(interface, place)
        )
    )


def place_xy(interface):
    return interface.place.x / 1000.0, interface.place.y / 1000.0


def xcmax(interface):
    return interface.world.nb_columns - 1


def ycmax(interface):
    return interface.world.nb_lines - 1


def coords_in_map(interface, square):
    if square is not None:
        return square.col, square.row
    return -1, -1


def _compute_move(interface, dxc, dyc):
    xc, yc = coords_in_map(interface, interface.place)
    xc += dxc
    if xc < 0:
        xc = interface.xcmax
    if xc > interface.xcmax:
        xc = 0
    yc += dyc
    if yc < 0:
        yc = interface.ycmax
    if yc > interface.ycmax:
        yc = 0
    return interface.world.grid[(xc, yc)]


def _shouldnt_collide(interface):
    for x in interface.group:
        if x in interface.dobjets and interface.dobjets[x].airground_type == "air":
            return True
    if interface.order and interface.order.nb_args and interface.order.target_shouldnt_collide:
        return True


def _get_prefix_and_collision(interface, new_square, dxc, dyc):
    if new_square is interface.place:
        return style.get("parameters", "no_path_in_this_direction"), True
    if (
        interface.place not in interface.scouted_before_squares
        or (interface.place.is_water or new_square.is_water)
        and interface.place.height == new_square.height
        or _shouldnt_collide(interface)
    ):
        return [], False
    
    from .game_unit_control import is_selectable
    exits = [
        o
        for o in list(interface.dobjets.values())
        if o.is_in(interface.place)
        and is_selectable(interface, o)
        and o.is_an_exit
        and not o.is_blocked(interface.player)
    ]
    prefix = style.get("parameters", "no_path_in_this_direction")
    collision = True
    xc, yc = coords_in_map(interface, interface.place)
    x, y = (xc + 0.5) * interface.square_width, (yc + 0.5) * interface.square_width
    for o in exits:
        if (
            dxc == 1
            and o.x > x
            or dxc == -1
            and o.x < x
            or dyc == 1
            and o.y > y
            or dyc == -1
            and o.y < y
        ):
            if parameters.d.get("play_movement_sound", True):
                prefix = o.when_moving_through
            else:
                prefix = []
            collision = False
            break
    return prefix, collision


def cmd_select_square(interface, dxc, dyc, *args):
    dxc = int(dxc)
    dyc = int(dyc)
    no_collision = "no_collision" in args
    if interface.immersion:
        # 在第一人称模式下，方向键用于移动，shift+方向键用于转向
        if "turn" in args:
            # shift+方向键用于转向
            if (dxc, dyc) == (-1, 0):
                cmd_rotate_left(interface)
            elif (dxc, dyc) == (1, 0):
                cmd_rotate_right(interface)
            else:
                voice.item(mp.BEEP)
        else:
            # 普通方向键用于移动
            # 如果同时处于缩放模式，则在缩放区域内进行精细移动
            if interface.zoom_mode:
                # 缩放模式下的RPG移动
                if (dxc, dyc) == (0, 1):  # UP - 前进
                    from .game_audio import cmd_move_forward_zoom
                    cmd_move_forward_zoom(interface)
                elif (dxc, dyc) == (0, -1):  # DOWN - 后退
                    from .game_audio import cmd_move_backward_zoom
                    cmd_move_backward_zoom(interface)
                elif (dxc, dyc) == (-1, 0):  # LEFT - 左移
                    from .game_audio import cmd_move_left_zoom
                    cmd_move_left_zoom(interface)
                elif (dxc, dyc) == (1, 0):  # RIGHT - 右移
                    from .game_audio import cmd_move_right_zoom
                    cmd_move_right_zoom(interface)
                else:
                    voice.item(mp.BEEP)
            else:
                # 普通RPG移动
                if (dxc, dyc) == (0, 1):  # UP - 前进
                    cmd_move_forward(interface)
                elif (dxc, dyc) == (0, -1):  # DOWN - 后退
                    cmd_move_backward(interface)
                elif (dxc, dyc) == (-1, 0):  # LEFT - 左移
                    cmd_move_left(interface)
                elif (dxc, dyc) == (1, 0):  # RIGHT - 右移
                    cmd_move_right(interface)
                else:
                    voice.item(mp.BEEP)
    elif interface.zoom_mode:
        # 记录切换前的主方格
        prev_main_square = interface.zoom.current_main_square if hasattr(interface, 'zoom') else None
        main_square_changed = interface.zoom.move(dxc, dyc, no_collision=no_collision)
        
        # 如果主方格切换失败（由于路径阻挡），不执行后续操作
        if main_square_changed is None:
            return  # move方法已经播报了阻挡信息
            
        interface.zoom.select()
        
        # 根据是否切换了主方格来决定播报内容
        if main_square_changed:
            # 省级与二级区域首次进入播报（缩放模式主方格切换）
            province_prefix = []
            city_prefix = []
            try:
                sq = interface.zoom.current_main_square
                if isinstance(sq, Square):
                    world = interface.world
                    key_new = f"{sq.col},{sq.row}"
                    province_name = getattr(world, 'square_provinces', {}).get(key_new)
                    city_name = getattr(world, 'square_cities', {}).get(key_new)
                    if province_name:
                        prev_key = None
                        if isinstance(prev_main_square, Square):
                            prev_key = f"{prev_main_square.col},{prev_main_square.row}"
                        prev_province = getattr(world, 'square_provinces', {}).get(prev_key) if prev_key else None
                        # 仅当跨越主区域边界时播报
                        if prev_province != province_name:
                            province_prefix = [province_name] + mp.COMMA
                    # 二级区域边界播报
                    if True:
                        prev_key = None
                        if isinstance(prev_main_square, Square):
                            prev_key = f"{prev_main_square.col},{prev_main_square.row}"
                        prev_city = getattr(world, 'square_cities', {}).get(prev_key) if prev_key else None
                        if city_name and city_name != prev_city:
                            city_prefix = [city_name] + mp.COMMA
            except Exception:
                pass
            # 播报主区域（如需）+ 二级区域（如需）+ 新主方格名称 + 子区域信息
            interface.zoom.say(prefix=province_prefix + city_prefix + interface.zoom.current_main_square.title + [" "])
        else:
            # 在同一主方格内移动，只播报子区域信息
            interface.zoom.say()
    elif interface.place is not None:
        if int(math.copysign(dxc + dyc, 1)) > 1:  # several squares at a time
            # assertion: dxc == 0 or dyc == 0
            if dxc:
                step = int(math.copysign(1, dxc)), 0
            else:
                step = 0, int(math.copysign(1, dyc))
            prefixes = []
            inserted_region_prefix = False
            inserted_city_prefix = False
            for _ in range(int(math.copysign(dxc + dyc, 1))):
                new_square = _compute_move(interface, *step)
                prefix, collision = _get_prefix_and_collision(
                    interface, new_square, *step
                )
                # 如果这一步将进入新的主区域，准备插入主区域前缀
                region_prefix = []
                city_prefix = []
                try:
                    if isinstance(interface.place, Square) and isinstance(new_square, Square):
                        world = interface.world
                        key_prev = f"{interface.place.col},{interface.place.row}"
                        key_new = f"{new_square.col},{new_square.row}"
                        prev_region = getattr(world, 'square_provinces', {}).get(key_prev)
                        new_region = getattr(world, 'square_provinces', {}).get(key_new)
                        if (not inserted_region_prefix) and new_region and new_region != prev_region:
                            region_prefix = [new_region] + mp.COMMA
                        prev_city = getattr(world, 'square_cities', {}).get(key_prev)
                        new_city = getattr(world, 'square_cities', {}).get(key_new)
                        if (not inserted_city_prefix) and new_city and new_city != prev_city:
                            city_prefix = [new_city] + mp.COMMA
                except Exception:
                    pass

                if not no_collision:
                    # 先加入通行音效，确保通行音效立即播放
                    if prefix:
                        prefixes += prefix
                    # 再加入区域前缀，避免遮挡通行音效
                    if region_prefix and not inserted_region_prefix:
                        prefixes = prefixes + region_prefix
                        inserted_region_prefix = True
                    if city_prefix and not inserted_city_prefix:
                        prefixes = prefixes + city_prefix
                        inserted_city_prefix = True
                else:
                    # 即使不收集路径音效，也要收集一次主区域前缀
                    if region_prefix and not inserted_region_prefix:
                        prefixes = prefixes + region_prefix
                        inserted_region_prefix = True
                    if city_prefix and not inserted_city_prefix:
                        prefixes = prefixes + city_prefix
                        inserted_city_prefix = True

                if not collision or no_collision:
                    move_to_square(interface, new_square)
                else:
                    break
            _select_and_say_square(interface, interface.place, prefixes)
        elif no_collision:  # one square at a time without collision
            new_square = _compute_move(interface, dxc, dyc)
            # 计算主区域跨越前缀
            province_prefix = []
            city_prefix = []
            try:
                if isinstance(interface.place, Square) and isinstance(new_square, Square):
                    world = interface.world
                    key_prev = f"{interface.place.col},{interface.place.row}"
                    key_new = f"{new_square.col},{new_square.row}"
                    prev_region = getattr(world, 'square_provinces', {}).get(key_prev)
                    new_region = getattr(world, 'square_provinces', {}).get(key_new)
                    if new_region and new_region != prev_region:
                        province_prefix = [new_region] + mp.COMMA
                    prev_city = getattr(world, 'square_cities', {}).get(key_prev)
                    new_city = getattr(world, 'square_cities', {}).get(key_new)
                    if new_city and new_city != prev_city:
                        city_prefix = [new_city] + mp.COMMA
            except Exception:
                pass
            move_to_square(interface, new_square)
            _select_and_say_square(interface, interface.place, province_prefix + city_prefix)
        else:  # one square at a time with collision
            new_square = _compute_move(interface, dxc, dyc)
            prefix, collision = _get_prefix_and_collision(interface, new_square, dxc, dyc)
            if not collision:
                # 计算主区域跨越前缀
                province_prefix = []
                city_prefix = []
                try:
                    if isinstance(interface.place, Square) and isinstance(new_square, Square):
                        world = interface.world
                        key_prev = f"{interface.place.col},{interface.place.row}"
                        key_new = f"{new_square.col},{new_square.row}"
                        prev_region = getattr(world, 'square_provinces', {}).get(key_prev)
                        new_region = getattr(world, 'square_provinces', {}).get(key_new)
                        if new_region and new_region != prev_region:
                            province_prefix = [new_region] + mp.COMMA
                        prev_city = getattr(world, 'square_cities', {}).get(key_prev)
                        new_city = getattr(world, 'square_cities', {}).get(key_new)
                        if new_city and new_city != prev_city:
                            city_prefix = [new_city] + mp.COMMA
                except Exception:
                    pass
                move_to_square(interface, new_square)
                # 先播放通行音效，再播报地名，避免通行音效被延后
                prefix = prefix + province_prefix + city_prefix
            _select_and_say_square(interface, interface.place, prefix)


def _select_square_from_list(interface, increment, squares):
    squares = [s for s in squares if isinstance(s, Square)]
    if squares:
        if interface.immersion:
            toggle_immersion(interface)
        if interface.zoom_mode:
            cmd_toggle_zoom(interface)
        _squares = list(squares)  # make a copy
        if isinstance(interface.place, Square) and interface.place not in _squares:
            _squares.append(interface.place)
        if interface.player.units:
            u = interface.player.units[0]
            _squares.sort(key=lambda s: distance(s.x, s.y, u.x, u.y))
        try:
            index = _squares.index(interface.place) + int(increment)
        except ValueError:
            index = 0
        if index < 0:
            index = len(_squares) - 1
        elif index == len(_squares):
            index = 0
        _select_and_say_square(interface, _squares[index])
    else:
        voice.item(mp.NOTHING)


def cmd_select_scouted_square(interface, increment):
    _select_square_from_list(interface, increment, interface.scouted_squares)


def cmd_select_conflict_square(interface, increment):
    enemy_units = [
        o
        for o in list(interface.dobjets.values())
        if o.player and o.player.player_is_an_enemy(interface.player)
    ]
    conflict_squares = []
    for u in enemy_units:
        if u.place not in conflict_squares:
            conflict_squares.append(u.place)
    _select_square_from_list(interface, increment, conflict_squares)


def cmd_select_unknown_square(interface, increment):
    unknown_squares = [
        p for p in interface.player.world.squares if p not in interface.scouted_before_squares
    ]
    _select_square_from_list(interface, increment, unknown_squares)


def cmd_select_resource_square(interface, increment):
    resource_squares = []
    for o in list(interface.dobjets.values()):
        if getattr(o, "resource_type", None) is not None:
            if o.place not in resource_squares:
                resource_squares.append(o.place)
    _select_square_from_list(interface, increment, resource_squares)


def _initial_observer_place(interface):
    """Return the square where the observer should start.

    Use spawn order (first controllable unit), not alphabetical order, so the
    camera opens on the main base rather than auxiliary units on other squares
    (e.g. peasant/footman at a wood square while townhall is at the base).
    """
    from .game_unit_control import units

    unit_list = units(interface)
    if not unit_list:
        return None
    return unit_list[0].place


# 观察者位置设置
def set_obs_pos(interface):
    if interface.place is None:  # first position
        first_place = _initial_observer_place(interface)
        if first_place is not None:
            # 初始进入：如目标方格有主区域，则先播主区域名
            province_prefix = []
            city_prefix = []
            try:
                if isinstance(first_place, Square):
                    key_new = f"{first_place.col},{first_place.row}"
                    new_region = getattr(interface.world, 'square_provinces', {}).get(key_new)
                    if new_region:
                        province_prefix = [new_region] + mp.COMMA
                    new_city = getattr(interface.world, 'square_cities', {}).get(key_new)
                    if new_city:
                        city_prefix = [new_city] + mp.COMMA
            except Exception:
                pass
            _select_and_say_square(interface, first_place, province_prefix + city_prefix)
    _follow_if_needed(interface)
    if interface.immersion and interface.group and interface.group[0] in interface.dobjets:
        interface.x = interface.dobjets[interface.group[0]].x
        interface.y = interface.dobjets[interface.group[0]].y
        interface.o = interface.dobjets[interface.group[0]].o
    elif interface.zoom_mode:
        interface.x, interface.y = interface.zoom.obs_pos()
    else:
        xc, yc = coords_in_map(interface, interface.place)
        x = interface.square_width * (xc + 0.5)
        y = interface.square_width * (yc + 1 / 8.0)
        if (x, y) != (interface.x, interface.y):
            k = min((time.time() - interface.previous_animation) * parameters.d.get("observer_reactivity", 1000), 1)
            interface.x += (x - interface.x) * k
            interface.y += (y - interface.y) * k
    if not interface.immersion:
        interface.o = 90
    from ..lib.sound import psounds
    psounds.update()


# 跟随模式
def _follow_if_needed(interface):
    from .game_unit_control import update_group
    update_group(interface)
    if (
        interface.follow_mode
        and interface.group
        and not interface.an_order_requiring_a_target_is_selected
    ):
        group_head = min(interface.group, key=lambda u: interface.dobjets[u].distance_to_goal)
        if interface.zoom_mode:
            if not interface.zoom.contains(interface.dobjets[group_head]):
                interface.zoom.move_to(interface.dobjets[group_head])
                if not voice.channel.get_busy():  # low priority: don't interrupt
                    interface.zoom.say()
        elif not interface.dobjets[group_head].is_in(interface.place):
            move_to_square(interface, interface.dobjets[group_head].place)
            if not voice.channel.get_busy():  # low priority: don't interrupt
                voice.item(localize_voice_msg(interface.place.title))
            if interface.immersion:
                interface.target = None  # unselect current object


# 雾战更新相关功能
def update_fog_of_war(interface):
    # updates dobjets (the dictionary of view objects)
    found_new_enemy = False
    
    # add or update objects
    for m in interface.memory:
        if m.id in interface.dobjets and not interface.dobjets[m.id].is_memory:
            _delete_object(interface, m.id)  # memory will replace perception
        if m.id not in interface.dobjets:
            interface.dobjets[m.id] = EntityView(interface, m)
            if interface.target and m.id == interface.target.id:  # keep target
                interface.target = interface.dobjets[m.id]
            if _must_report_resource(interface, m):
                interface.scout_info.add(m.place)
        else:
            interface.dobjets[m.id].model = m
    for m in interface.perception:
        if m.id not in interface.dobjets:
            # 中立电脑（`computer_only ... neutral`）的单位是被动 creep，不视为
            # 主动敌人——不进"新敌人提示"，也不触发战斗音乐。它们仍走 is_an_enemy
            # 真值路径（保留视野/自动开火/伤害逻辑），但 UI 提示与音乐采用更弱的语义。
            if interface.player.is_an_enemy(m) and not getattr(
                getattr(m, "player", None), "neutral", False
            ):
                interface.new_enemy_units.append(
                    [
                        EntityView(interface, m).short_title,
                        m.place,
                        summary_omit_single_count(m),
                    ]
                )
                found_new_enemy = True
            if _must_report_resource(interface, m):
                interface.scout_info.add(m.place)
        elif interface.dobjets[m.id].is_memory:
            _delete_object(interface, m.id)  # perception will replace memory
        if m.id not in interface.dobjets:
            interface.dobjets[m.id] = EntityView(interface, m)
            if interface.target and m.id == interface.target.id:  # keep target
                interface.target = interface.dobjets[m.id]
        else:
            interface.dobjets[m.id].model = m

    # remove missing objects
    pm = {o.id for o in interface.memory}
    pm.update(o.id for o in interface.perception)
    for i in list(interface.dobjets.keys()):
        if i in pm:
            continue
        _delete_object(interface, i)
        if interface.target and i == interface.target.id:
            interface.target = None
    
    from ..version import IS_DEV_VERSION
    from ..lib.log import warning
    if IS_DEV_VERSION:
        for m in interface.perception.union(interface.memory):
            if m.place is None:
                warning(
                    "%s.model is in memory or perception "
                    "and yet its place is None",
                    m.type_name,
                )
                
    # 如果发现新敌人，触发战斗音乐
    if found_new_enemy:
        from ..lib import sound
        
        # 确保玩家阵营信息正确设置
        player_faction = None
        if hasattr(interface.player, 'faction') and interface.player.faction:
            player_faction = interface.player.faction
            
        # 如果玩家阵营不是字符串（而是对象），尝试获取类型名称
        if player_faction and not isinstance(player_faction, str):
            if hasattr(player_faction, 'type_name'):
                player_faction = player_faction.type_name
                
        # 设置玩家阵营全局变量
        if player_faction:
            sound.set_player_faction(player_faction)
        
        # 获取当前音乐状态
        status = sound.get_music_status()
        
        # 如果当前不在战斗状态，播放战斗音乐
        if not status["in_battle"]:
            # 获取地图战斗音乐（如果存在）
            map_battle_music = None
            if hasattr(interface, '_world_reference') and interface._world_reference:
                map_battle_music = getattr(interface._world_reference, 'map_battle_music', None)
            sound.play_battle_music(map_battle_music)


def _delete_object(interface, _id):
    interface.dobjets[_id].stop()
    del interface.dobjets[_id]
    from .game_unit_control import _note_selected_unit_removed
    _note_selected_unit_removed(interface, _id)


def _is_ground_item(m):
    return (
        getattr(m, "default_order", None) == "pickup"
        and getattr(m, "player", None) is None
    )


def _must_report_resource(interface, m):
    resource_type = getattr(m, "resource_type", None)
    if resource_type is not None and m.place not in interface._known_resource_places:
        interface._known_resource_places.add(m.place)
        return True
    if _is_ground_item(m) and m.id not in interface._known_item_ids:
        interface._known_item_ids.add(m.id)
        return True
    return False


def scout_info_if_needed(interface):
    if "scout_info" not in config.verbosity:
        return
    if interface.scout_info and (
        getattr(interface, 'previous_scout_info', None) is None
        or time.time() > interface.previous_scout_info + 10
    ):
        for place in interface.scout_info:
            from .game_unit_control import place_summary
            s = place_summary(interface, place, me=False, brief=True)
            if s:
                voice.info(s + mp.AT + place.title)
        interface.scout_info = set()
        interface.previous_scout_info = time.time()


def squares_alert_if_needed(interface):
    if interface.alert_squares and (
        getattr(interface, 'previous_squares_alert', None) is None
        or time.time() > interface.previous_squares_alert + 10
    ):
        titles = sorted(
            [
                sq.title
                for sq, t in list(interface.alert_squares.items())
                if time.time() < t + 5
            ],
            key=lambda parts: " ".join(map(str, parts)),
        )  # recent attacks only; normalize for mixed int/str
        if len(titles) > 1:
            titles.insert(-1, mp.AND)
        if titles:
            voice.info(sum(titles, mp.ALERT + mp.AT))
            interface.previous_squares_alert = time.time()
        interface.alert_squares = {}


# 导出的函数供其他模块使用
__all__ = [
    'toggle_immersion', 'cmd_immersion', 'cmd_escape',
    'cmd_rotate_left', 'cmd_rotate_right', 'cmd_turn_around', 'say_compass',
    'cmd_move_forward', 'cmd_move_backward', 'cmd_move_left', 'cmd_move_right',
    'cmd_toggle_zoom', '_select_and_say_square', 'move_to_square', 'say_square',
    'cmd_select_square', 'cmd_select_scouted_square', 'cmd_select_conflict_square',
    'cmd_select_unknown_square', 'cmd_select_resource_square',
    'cmd_ui_escape',
    'set_obs_pos', '_follow_if_needed', 'update_fog_of_war', 'scout_info_if_needed',
    'squares_alert_if_needed', 'coords_in_map', 'square_postfix',
    '_check_exit_connection', '_get_prefix_and_collision', '_shouldnt_collide',
    'place_xy', 'xcmax', 'ycmax'
]