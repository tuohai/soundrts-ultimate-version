"""
SoundRTS 客户端游戏接口模块

这个模块将原来庞大的clientgame.py拆分成了8个子模块：
- game_interface_base: 基础接口类和初始化
- game_input_handler: 输入处理模块  
- game_unit_control: 单位控制模块
- game_navigation: 地图导航模块
- game_orders: 指令管理模块
- game_display: 显示和渲染模块
- game_audio: 音频和语音模块
- game_resources: 资源和状态管理模块
"""

# 导入基础接口类
from .game_interface_base import GameInterface

# 导入各个模块的函数
from . import game_input_handler
from . import game_unit_control  
from . import game_navigation
from . import game_orders
from . import game_display
from . import game_audio
from . import game_resources
from . import interface_modes

# 将方法绑定到GameInterface类
# 输入处理方法
GameInterface._process_events = game_input_handler._process_events
GameInterface._process_fullscreen_mode_mouse_event = game_input_handler._process_fullscreen_mode_mouse_event
GameInterface._execute_order_shortcut = game_input_handler._execute_order_shortcut
GameInterface._handle_zoom_input = game_input_handler._handle_zoom_input
GameInterface._start_zoom_input_mode = game_input_handler._start_zoom_input_mode
GameInterface._process_zoom_input = game_input_handler._process_zoom_input
GameInterface._loop = game_input_handler._loop

# 单位控制方法
GameInterface.say_target = game_unit_control.say_target
GameInterface.cmd_examine = game_unit_control.cmd_examine
GameInterface.cmd_select_target = game_unit_control.cmd_select_target
GameInterface.update_group = game_unit_control.update_group
GameInterface.units = game_unit_control.units
GameInterface.summary = game_unit_control.summary
GameInterface.place_summary = game_unit_control.place_summary
GameInterface.say_group = game_unit_control.say_group
GameInterface.tell_enemies_in_square = game_unit_control.tell_enemies_in_square
GameInterface.units_alert = game_unit_control.units_alert
GameInterface.units_alert_if_needed = game_unit_control.units_alert_if_needed
GameInterface.command_unit = game_unit_control.command_unit
GameInterface.cmd_command_unit = game_unit_control.cmd_command_unit
GameInterface.cmd_unit_status = game_unit_control.cmd_unit_status
GameInterface.cmd_unit_hp_status = game_unit_control.cmd_unit_hp_status
GameInterface.cmd_group = game_unit_control.cmd_group
GameInterface.cmd_ungroup = game_unit_control.cmd_ungroup
GameInterface.cmd_select_unit = game_unit_control.cmd_select_unit
GameInterface.cmd_select_units = game_unit_control.cmd_select_units
GameInterface.cmd_set_group = game_unit_control.cmd_set_group
GameInterface.cmd_append_group = game_unit_control.cmd_append_group
GameInterface.cmd_recall_group = game_unit_control.cmd_recall_group
GameInterface.send_order = game_unit_control.send_order
GameInterface.send_menu_alerts_if_needed = game_unit_control.send_menu_alerts_if_needed
GameInterface.is_visible = game_unit_control.is_visible
GameInterface.is_selectable = game_unit_control.is_selectable
GameInterface._object_choices = game_unit_control._object_choices
GameInterface._remove_duplicates = game_unit_control._remove_duplicates
GameInterface._priority = game_unit_control._priority
GameInterface._next_choice = game_unit_control._next_choice

# 地图导航方法  
GameInterface.toggle_immersion = game_navigation.toggle_immersion
GameInterface.cmd_immersion = game_navigation.cmd_immersion
GameInterface.cmd_escape = game_navigation.cmd_escape
GameInterface.cmd_ui_escape = game_navigation.cmd_ui_escape
GameInterface.cmd_rotate_left = game_navigation.cmd_rotate_left
GameInterface.cmd_rotate_right = game_navigation.cmd_rotate_right
GameInterface.cmd_turn_around = game_navigation.cmd_turn_around
GameInterface.say_compass = game_navigation.say_compass
GameInterface.cmd_move_forward = game_navigation.cmd_move_forward
GameInterface.cmd_move_backward = game_navigation.cmd_move_backward
GameInterface.cmd_move_left = game_navigation.cmd_move_left
GameInterface.cmd_move_right = game_navigation.cmd_move_right
GameInterface.cmd_toggle_zoom = game_navigation.cmd_toggle_zoom
GameInterface._select_and_say_square = game_navigation._select_and_say_square
GameInterface.move_to_square = game_navigation.move_to_square
GameInterface.say_square = game_navigation.say_square
GameInterface.cmd_select_square = game_navigation.cmd_select_square
GameInterface.cmd_select_scouted_square = game_navigation.cmd_select_scouted_square
GameInterface.cmd_select_conflict_square = game_navigation.cmd_select_conflict_square
GameInterface.cmd_select_unknown_square = game_navigation.cmd_select_unknown_square
GameInterface.cmd_select_resource_square = game_navigation.cmd_select_resource_square
GameInterface.cmd_select_deposit = game_unit_control.cmd_select_deposit
GameInterface.cmd_select_meadow = game_unit_control.cmd_select_meadow
GameInterface.cmd_select_passage = game_unit_control.cmd_select_passage
GameInterface.set_obs_pos = game_navigation.set_obs_pos
GameInterface._follow_if_needed = game_navigation._follow_if_needed
GameInterface.update_fog_of_war = game_navigation.update_fog_of_war
GameInterface.scout_info_if_needed = game_navigation.scout_info_if_needed
GameInterface.squares_alert_if_needed = game_navigation.squares_alert_if_needed
GameInterface.coords_in_map = game_navigation.coords_in_map
GameInterface.square_postfix = game_navigation.square_postfix
GameInterface._check_exit_connection = game_navigation._check_exit_connection
GameInterface._get_prefix_and_collision = game_navigation._get_prefix_and_collision
GameInterface._shouldnt_collide = game_navigation._shouldnt_collide

# 指令管理方法
GameInterface.orders = game_orders.orders
GameInterface._select_order = game_orders._select_order
GameInterface.cmd_select_order = game_orders.cmd_select_order
GameInterface.cmd_select_order_index = game_orders.cmd_select_order_index
GameInterface.cmd_order_shortcut = game_orders.cmd_order_shortcut
GameInterface.cmd_do_again = game_orders.cmd_do_again
GameInterface.cmd_skill = game_orders.cmd_skill
GameInterface.cmd_validate = game_orders.cmd_validate
GameInterface._say_default_confirmation = game_orders._say_default_confirmation
GameInterface.cmd_default = game_orders.cmd_default
GameInterface.cmd_rpg_skill_1 = game_orders.cmd_rpg_skill_1
GameInterface.cmd_rpg_skill_2 = game_orders.cmd_rpg_skill_2
GameInterface.cmd_rpg_skill_3 = game_orders.cmd_rpg_skill_3
GameInterface.cmd_rpg_skill_4 = game_orders.cmd_rpg_skill_4
GameInterface.cmd_rpg_skill_5 = game_orders.cmd_rpg_skill_5
GameInterface.cmd_rpg_skill_6 = game_orders.cmd_rpg_skill_6
GameInterface.cmd_rpg_skill_7 = game_orders.cmd_rpg_skill_7
GameInterface.cmd_rpg_skill_8 = game_orders.cmd_rpg_skill_8
GameInterface.cmd_rpg_skill_9 = game_orders.cmd_rpg_skill_9
GameInterface.cmd_rpg_skill_0 = game_orders.cmd_rpg_skill_0
GameInterface.cmd_rpg_skill_10 = game_orders.cmd_rpg_skill_10
GameInterface.cmd_rpg_skill_11 = game_orders.cmd_rpg_skill_11
GameInterface.cmd_rpg_skill_list = game_orders.cmd_rpg_skill_list
GameInterface.cmd_rpg_auto_attack = game_orders.cmd_rpg_auto_attack
GameInterface._rpg_use_skill_by_index = game_orders._rpg_use_skill_by_index

# 显示和渲染方法
GameInterface.display = game_display.display
GameInterface.display_metrics = game_display.display_metrics
GameInterface._display_target_info = game_display._display_target_info
GameInterface._animate_objects = game_display._animate_objects
GameInterface._animate_terrain = game_display._animate_terrain
GameInterface._check_battle_status = game_display._check_battle_status
GameInterface._check_rpg_unit_place_change = game_display._check_rpg_unit_place_change
GameInterface.cmd_fullscreen = game_display.cmd_fullscreen

# 音频和语音方法
GameInterface.cmd_say = game_audio.cmd_say
GameInterface.cmd_say_players = game_audio.cmd_say_players
GameInterface.cmd_say_time = game_audio.cmd_say_time
GameInterface.cmd_toggle_music = game_audio.cmd_toggle_music
GameInterface.cmd_music_volume_up = game_audio.cmd_music_volume_up
GameInterface.cmd_music_volume_down = game_audio.cmd_music_volume_down
GameInterface.cmd_volume = game_audio.cmd_volume
GameInterface.cmd_history_previous = game_audio.cmd_history_previous
GameInterface.cmd_history_stop = game_audio.cmd_history_stop
GameInterface.cmd_history_next = game_audio.cmd_history_next
GameInterface.cmd_select_sound = game_audio.cmd_select_sound
GameInterface.cmd_sound_volume = game_audio.cmd_sound_volume
GameInterface.cmd_toggle_talking_clock = game_audio.cmd_toggle_talking_clock
GameInterface.cmd_toggle_tick = game_audio.cmd_toggle_tick
GameInterface.srv_restore_music = game_audio.srv_restore_music
GameInterface.srv_resume_music = game_audio.srv_resume_music
GameInterface.cmd_move_forward_zoom = game_audio.cmd_move_forward_zoom
GameInterface.cmd_move_backward_zoom = game_audio.cmd_move_backward_zoom
GameInterface.cmd_move_left_zoom = game_audio.cmd_move_left_zoom
GameInterface.cmd_move_right_zoom = game_audio.cmd_move_right_zoom
GameInterface.cmd_change_zoom_precision = game_audio.cmd_change_zoom_precision
GameInterface.cmd_get_zoom_precision = game_audio.cmd_get_zoom_precision
# 动态联盟命令绑定
GameInterface.cmd_select_alliance_candidate = game_audio.cmd_select_alliance_candidate
GameInterface.cmd_alliance_request = game_audio.cmd_alliance_request
GameInterface.cmd_alliance_accept = game_audio.cmd_alliance_accept
GameInterface.cmd_alliance_decline_or_cancel = game_audio.cmd_alliance_decline_or_cancel
GameInterface.cmd_toggle_selection_mode = interface_modes.cmd_toggle_selection_mode
GameInterface.cmd_toggle_action_mode = interface_modes.cmd_toggle_action_mode
GameInterface.cmd_enter_help_mode = interface_modes.cmd_enter_help_mode
GameInterface.cmd_enter_diplomacy_mode = interface_modes.cmd_enter_diplomacy_mode
GameInterface.cmd_enter_map_mode = interface_modes.cmd_enter_map_mode
GameInterface.cmd_exit_overlay_mode = interface_modes.cmd_exit_overlay_mode
GameInterface.cmd_toggle_gear_screen = interface_modes.cmd_toggle_gear_screen
GameInterface._check_zoom_movement_collision = game_audio._check_zoom_movement_collision
GameInterface._get_target_zoom_by_orientation = game_audio._get_target_zoom_by_orientation

# 资源和状态管理方法
GameInterface.cmd_resource_status = game_resources.cmd_resource_status
GameInterface.cmd_population_status = game_resources.cmd_population_status
GameInterface.send_resource_alerts_if_needed = game_resources.send_resource_alerts_if_needed
GameInterface.cmd_toggle_side_filter = game_resources.cmd_toggle_side_filter
GameInterface.cmd_toggle_type_filter = game_resources.cmd_toggle_type_filter
GameInterface.cmd_gamemenu = game_resources.cmd_gamemenu
GameInterface.cmd_toggle_cheatmode = game_resources.cmd_toggle_cheatmode
GameInterface.cmd_cmd = game_resources.cmd_cmd
GameInterface.cmd_console = game_resources.cmd_console
GameInterface.cmd_reload_parameters = game_resources.cmd_reload_parameters
GameInterface.cmd_change_player = game_resources.cmd_change_player
GameInterface.cmd_objectives = game_resources.cmd_objectives
GameInterface.cmd_help = game_resources.cmd_help
GameInterface.direction_to_msg = game_resources.direction_to_msg
GameInterface.launch_alert = game_resources.launch_alert
GameInterface.srv_alert = game_resources.srv_alert
GameInterface.send_msg_if_playing = game_resources.send_msg_if_playing
GameInterface._execute_command = game_resources._execute_command

# 游戏菜单方法绑定
GameInterface.gm_quit = game_resources.gm_quit
GameInterface.gm_slow_speed = game_resources.gm_slow_speed
GameInterface.gm_normal_speed = game_resources.gm_normal_speed
GameInterface.gm_fast_speed = game_resources.gm_fast_speed
GameInterface.gm_very_fast_speed = game_resources.gm_very_fast_speed
GameInterface.gm_save = game_resources.gm_save
GameInterface.gm_toggle_music = game_resources.gm_toggle_music
GameInterface.gm_music_volume_up = game_resources.gm_music_volume_up
GameInterface.gm_music_volume_down = game_resources.gm_music_volume_down

# 设置属性（properties）
GameInterface.resources = property(lambda self: game_resources.resources(self))
GameInterface.available_population = property(lambda self: game_resources.available_population(self))
GameInterface.used_population = property(lambda self: game_resources.used_population(self))
GameInterface.place_xy = property(lambda self: game_navigation.place_xy(self))
GameInterface.xcmax = property(lambda self: game_navigation.xcmax(self))
GameInterface.ycmax = property(lambda self: game_navigation.ycmax(self))
GameInterface.ui_target = property(lambda self: game_orders.ui_target(self))
GameInterface.an_order_not_requiring_a_target_is_selected = property(lambda self: game_orders.an_order_not_requiring_a_target_is_selected(self))
GameInterface.an_order_requiring_a_target_is_selected = property(lambda self: game_orders.an_order_requiring_a_target_is_selected(self))

# 设置一些缺失的属性
GameInterface.target = None
GameInterface.order = None
GameInterface._previous_order = None
GameInterface.follow_mode = False
GameInterface.immersion = False
GameInterface.end_loop = False
GameInterface.already_asked_to_quit = False
GameInterface.forced_quit = False
GameInterface.zoom_mode = False
GameInterface.zoom = None
GameInterface._world_reference = None
GameInterface.auto = []
GameInterface._editor = False
GameInterface._sound = None
GameInterface._must_display_target_info = False
GameInterface.previous_animation = 0
GameInterface._terrain_noises = []
GameInterface._build_field_noises = []

# 从原来的模块导入一些必要的函数和常量
def direction_to_msgpart(o):
    """方向角度转换为消息部分"""
    from .. import msgparts as mp
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

def load_palette():
    """加载调色板（编辑器用）"""
    p = []
    with open("res/ui/editor_palette.txt") as f:
        for s in f:
            s = s.strip()
            if s and not s.startswith(";"):
                if s.startswith("def"):
                    k = s.split()[1]
                    t = dict()
                    p.append((k, t))
                    t["style"] = k
                    t["water"] = False
                    t["ground"] = True
                    t["air"] = True
                    t["high_ground"] = False
                    t["meadows"] = 0
                    t["woods"] = (0, "75")
                    t["goldmines"] = (0, "150")
                    t["speed"] = (100, 100)
                    t["cover"] = (0, 0)
                else:
                    k = s.split()[0]
                    v = s.split()[1:]
                    if k in ["air", "ground", "water", "high_ground", "meadows"]:
                        v = int(v[0])
                    elif k == "style":
                        if v:
                            v = v[0]
                        else:
                            v = None
                    elif k in ["water", "ground", "air", "high_ground"]:
                        v = bool(v)
                    elif k in ["woods", "goldmines"]:
                        v = int(v[0]), v[1]
                    elif k in ["speed", "cover"]:
                        v = tuple([int(float(x) * 100) for x in v[:2]])
                    t[k] = v
    return p

# 导出主要的类
__all__ = ['GameInterface', 'direction_to_msgpart', 'load_palette']