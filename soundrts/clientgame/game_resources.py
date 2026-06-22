import re
import time

from .. import config
from .. import msgparts as mp
from .. import parameters
from ..clientgamenews import must_be_said
from ..clienthelp import help_msg
from ..clientmedia import voice, sounds
from ..lib.sound import psounds
from ..clientmenu import Menu, input_string
from ..definitions import style
from ..lib.log import exception, warning
from ..lib.msgs import nb2msg, nb2msg_float
from ..objective_announce import (
    collect_objective_entries,
    navigate_objective_index,
)
from ..lib.nofloat import PRECISION
from ..lib.screen import set_game_mode
from ..lib.sound import distance


# 资源管理功能
def resources(interface):
    return [int(x / PRECISION) for x in interface.player.resources]


def available_population(interface):
    return interface.player.available_population


def used_population(interface):
    return interface.player.used_population


def cmd_resource_status(interface, resource_type):
    """显示资源状态"""
    # 获取资源ID和标题
    resource_id = None
    
    # 处理输入参数，支持字符串形式的"resource1"和整数形式的"0"或0
    if isinstance(resource_type, str):
        if resource_type.startswith("resource"):
            try:
                # 从resource3这样的格式中提取数字
                resource_id = int(resource_type[8:]) - 1  # 跳过"resource"这8个字符
            except ValueError:
                voice.item(mp.BEEP)
                return
        else:
            try:
                # 处理字符串形式的整数索引，比如"0"，"1"
                resource_id = int(resource_type)
            except ValueError:
                voice.item(mp.BEEP)
                return
    else:
        # 处理直接整数索引，比如0，1
        resource_id = resource_type
        
    # 获取资源标题键名
    title_key = f"resource{resource_id + 1}_title"
        
    # 获取资源数量
    try:
        qty = resources(interface)[resource_id]
        # 使用整数显示资源数量
        voice.item(
            nb2msg(qty) +
            style.get("parameters", title_key)
        )
    except (IndexError, KeyError):
        voice.item(mp.BEEP)


def cmd_population_status(interface):
    """显示人口状态"""
    voice.item(
        nb2msg(interface.used_population)
        + mp.ON
        + nb2msg_float(interface.available_population)
        + style.get("parameters", "population_title")
    )


def send_msg_if_playing(interface, msg, update_type=None):
    # say only if game started
    if interface.last_virtual_time != 0:
        voice.info(msg, expiration_delay=1.5, update_type=update_type)


def send_resource_alerts_if_needed(interface):
    """发送资源警报"""
    # 观战者不需要资源警报
    if hasattr(interface.player, '_is_pure_spectator') and interface.player._is_pure_spectator:
        return
        
    # 安全地获取当前资源，如果是观战者可能资源数组为空或长度不匹配
    current_resources = interface.resources
    
    if getattr(interface, '_previous_resources', None) is None:
        interface._previous_resources = current_resources[:]
    
    # 确保两个数组长度一致，防止索引越界
    if len(current_resources) != len(interface._previous_resources):
        interface._previous_resources = current_resources[:]
        return  # 第一次同步，不发送警报
        
    for i, r in enumerate(current_resources):
        # 资源显示为整数
        if i < len(interface._previous_resources) and r != interface._previous_resources[i]:
            interface._previous_resources[i] = r
            if "resources" in config.verbosity and must_be_said(r):
                send_msg_if_playing(
                    interface,
                    nb2msg(r) + style.get("parameters", f"resource{i+1}_title"),
                    update_type=f"resource_{i}",
                )
    # 观战者不需要人口警报
    if not (hasattr(interface.player, '_is_pure_spectator') and interface.player._is_pure_spectator):
        prev_available = getattr(interface, '_previous_available_population', 0)
        prev_used = getattr(interface, '_previous_used_population', 0)
        
        if (
            interface.available_population != prev_available
            or interface.used_population > prev_used
            or interface.used_population < prev_used == interface.available_population
        ):
            if (
                "population" in config.verbosity
                and 0
                <= interface.available_population - interface.used_population
                <= interface.available_population * 0.20
            ):
                send_msg_if_playing(
                    interface,
                    nb2msg(interface.used_population)
                    + mp.ON
                    + nb2msg_float(interface.available_population)
                    + style.get("parameters", "population_title"),
                    update_type="population",
                )
            interface._previous_available_population = interface.available_population
            interface._previous_used_population = interface.used_population


# 过滤器管理
def cmd_toggle_side_filter(interface, direction=1):
    """在己方和敌方之间切换（通过m和shift+m键）
    参数:
        direction: 1表示向前切换，-1表示向后切换
    """
    options = ["ally", "enemy", "all"]
    current_index = options.index(interface._side_filter)
    new_index = (current_index + int(direction)) % len(options)
    interface._side_filter = options[new_index]
    
    # 语音提示当前筛选模式
    if interface._side_filter == "ally":
        voice.item(mp.ALLY_FILTER if hasattr(mp, "ALLY_FILTER") else ["己方过滤"])
    elif interface._side_filter == "enemy":
        voice.item(mp.ENEMY_FILTER if hasattr(mp, "ENEMY_FILTER") else ["敌方过滤"])
    else:
        voice.item(mp.ALL_FILTER if hasattr(mp, "ALL_FILTER") else ["全部过滤"])


def cmd_toggle_type_filter(interface, direction=1):
    """在建筑、单位和元素之间切换（通过n和shift+n键）
    参数:
        direction: 1表示向前切换，-1表示向后切换
    """
    options = ["building", "unit", "element", "all"]
    current_index = options.index(interface._type_filter)
    new_index = (current_index + int(direction)) % len(options)
    interface._type_filter = options[new_index]
    
    # 语音提示当前筛选模式
    if interface._type_filter == "building":
        voice.item(mp.BUILDING_FILTER if hasattr(mp, "BUILDING_FILTER") else ["建筑过滤"])
    elif interface._type_filter == "unit":
        voice.item(mp.UNIT_FILTER if hasattr(mp, "UNIT_FILTER") else ["单位过滤"])
    elif interface._type_filter == "element":
        voice.item(mp.ELEMENT_FILTER if hasattr(mp, "ELEMENT_FILTER") else ["元素过滤"])
    else:
        voice.item(mp.ALL_TYPE_FILTER if hasattr(mp, "ALL_TYPE_FILTER") else ["全部类型过滤"])


# 游戏菜单功能
def cmd_gamemenu(interface):
    """显示游戏菜单"""
    voice.silent_flush()
    from ..lib import sound
    from ..lib.screen import set_game_mode
    sound.stop()
    menu = Menu(mp.MENU, menu_type="submenu")  # 指定这是子菜单
    menu.append(mp.CANCEL_GAME, lambda: gm_quit(interface))
    if interface.is_admin():
        menu.append(mp.SET_SPEED_TO_SLOW, lambda: gm_slow_speed(interface))
        menu.append(mp.SET_SPEED_TO_NORMAL, lambda: gm_normal_speed(interface))
        menu.append(mp.SET_SPEED_TO_FAST, lambda: gm_fast_speed(interface))
        menu.append(mp.SET_SPEED_TO_FAST + nb2msg(4), lambda: gm_very_fast_speed(interface))
    if interface.can_save():
        menu.append(mp.SAVE, lambda: gm_save(interface))
    menu.append(mp.CONTINUE_GAME, None)
    set_game_mode(False)
    menu.run()
    set_game_mode(True)


# 游戏菜单处理函数
def _try_save_resume(interface):
    """尝试在玩家退出时自动保留游戏进度，以便下次主菜单中继续未完成的游戏。"""
    try:
        # 仅在该客户端支持存档（即单人/战役游戏）时才保存
        if hasattr(interface.server, "save_resume"):
            interface.server.save_resume()
            voice.info(mp.RESUME_SAVED)
    except Exception as exc:
        from ..game import SaveTooLargeError

        if isinstance(exc, SaveTooLargeError):
            warning(
                "auto save resume skipped: world too large (%s squares)",
                exc.square_count,
            )
        else:
            exception("auto save resume game failed")


def gm_quit(interface):
    """退出游戏"""
    # 检查是否为旁观者，如果是则直接退出
    if (hasattr(interface.player, 'is_spectator') and interface.player.is_spectator) or \
       (hasattr(interface.player, '_is_pure_spectator') and interface.player._is_pure_spectator):
        # 旁观者直接发送quit_spectating命令，一次就能退出
        interface.server.write_line("quit_spectating")
        interface.srv_quit()  # 直接退出
        interface.forced_quit = True
        return
        
    # 普通玩家的退出逻辑保持不变
    if getattr(interface, '_editor', False):
        interface.world.save_map("user/multi/editor_autosave.txt")
        interface.srv_quit()  # forced quit
        interface.forced_quit = True
    elif not getattr(interface, 'already_asked_to_quit', False):
        # 在真正退出之前，把当前进度自动保留为"继续未完成的游戏"存档
        _try_save_resume(interface)
        interface.next_update = time.time()  # useful if the game is paused
        interface.server.write_line("quit")
        import pygame
        pygame.event.clear()
        interface.already_asked_to_quit = True
    else:
        interface.srv_quit()  # forced quit
        interface.forced_quit = True


def _set_speed(interface, speed):
    interface.server.write_line("speed %s" % speed)


def gm_slow_speed(interface):
    _set_speed(interface, 0.5)


def gm_normal_speed(interface):
    _set_speed(interface, 1.0)


def gm_fast_speed(interface):
    _set_speed(interface, 2.0)


def gm_very_fast_speed(interface):
    _set_speed(interface, 4.0)


def gm_save(interface):
    """保存游戏"""
    try:
        interface.server.save_game()
        voice.info(mp.OK)
    except:
        exception("save game failed")
        voice.alert(mp.BEEP)


# 游戏菜单音乐控制功能
def gm_toggle_music(interface):
    """在游戏菜单中开关音乐"""
    from . import game_audio
    game_audio.cmd_toggle_music(interface)
    return None  # 不要退出菜单


def gm_music_volume_up(interface):
    """在游戏菜单中增加音乐音量"""
    from . import game_audio
    game_audio.cmd_music_volume_up(interface)
    return None  # 不要退出菜单


def gm_music_volume_down(interface):
    """在游戏菜单中减小音乐音量"""
    from . import game_audio
    game_audio.cmd_music_volume_down(interface)
    return None  # 不要退出菜单


# 作弊和调试功能
def cmd_toggle_cheatmode(interface):
    """切换作弊模式"""
    if interface.server.allow_cheatmode:
        interface.server.write_line("toggle_cheatmode")
        if interface.player.cheatmode:
            voice.item(mp.CHEATMODE + mp.IS_NOW_OFF)
        else:
            voice.item(mp.CHEATMODE + mp.IS_NOW_ON)
    else:
        voice.item(mp.BEEP)


def _execute_command(interface, cmd):
    """执行作弊命令"""
    if cmd.startswith("s "):
        interface.speed = float(cmd.split(" ")[1])
        interface.next_update = time.time()
    elif cmd == "p":
        if interface.speed >= 1:
            interface.speed /= 10000.0
        else:
            interface.speed *= 10000.0
            interface.next_update = time.time()
    elif cmd == "m":
        for u in interface.player.units:
            u.mana_regen *= 1000
    elif cmd == "h":
        voice.item(
            [
                "p: pause/unpause, s: set speed, r: get 1000 resources, t: get all techs, m: infinite mana, a: add units, v: instant victory"
            ]
        )
    elif cmd == "r":
        interface.player.resources = [
            n + 1000 * PRECISION for n in interface.player.resources
        ]
    elif cmd == "t":
        interface.player.has = lambda x: True
    elif cmd == "edit":
        interface._editor = not getattr(interface, '_editor', False)
        if interface._editor:
            interface.player.cheatmode = True
            for p in interface.world.players:
                p.triggers = []
            from ..lib.bindings import Bindings
            interface._bindings = Bindings()
            interface._bindings.load(open("res/ui/editor_bindings.txt").read(), interface)
            voice.item(["editor"])
        else:
            voice.item(mp.BEEP)
    elif cmd == "sm":
        def next_available_filename(name):
            import os.path
            n = 0
            while os.path.exists(name % n):
                n += 1
            return name % n
        interface.world.save_map(next_available_filename("user/multi/editor%s.txt"))
    elif cmd.startswith("te "):
        delta = list(map(int, cmd.split(" ")[1:3]))
        if interface.place.toggle_path(*delta):
            voice.item(["path"])
        else:
            voice.item(["obstacle"])
    elif cmd.startswith("st "):
        from ..clientgame import load_palette
        pal = load_palette()
        name = cmd.split(" ")[1]
        if name in ["1", "-1"]:
            try:
                i = [d for k, d in pal].index(getattr(interface, '_editor_terrain', {})) + int(name)
                i %= len(pal)
            except:
                i = 0
            interface._editor_terrain = pal[i][1]
            voice.item([pal[i][0]])
        else:
            for k, d in pal:
                if k == name:
                    interface._editor_terrain = d
                    voice.item([name])
                    return
            voice.item(mp.BEEP)
    elif cmd == "at":
        try:
            d = interface._editor_terrain
        except AttributeError:
            voice.item(mp.BEEP)
            return
        p = interface.place
        if getattr(interface, "zoom_mode", False) and hasattr(interface, "zoom"):
            from ..lib.subcell_terrain import zoom_subcell_index
            cx, cy = zoom_subcell_index(interface.zoom)
            p.subcells.apply_palette(d, cx, cy)
        else:
            p.type_name = d["style"]

            # trigger the update of terrain noises
            terrain_noises = getattr(interface, '_terrain_noises', [])
            for n in terrain_noises[:]:
                n.stop()
            interface._terrain_noises = []

            p.is_water = d["water"]
            p.is_ground = d["ground"]
            p.is_air = d["air"]
            p.high_ground = d["high_ground"]
            for p2 in p.strict_neighbors:
                if p.is_ground and p2.is_ground and p.high_ground == p2.high_ground:
                    p.ensure_path(p2)
                else:
                    p.ensure_nopath(p2)
            p.ensure_resources("goldmine", *d["goldmines"])
            p.ensure_resources("wood", *d["woods"])
            p.ensure_meadows(d["meadows"])
            p.terrain_speed = d["speed"]
            p.terrain_cover = d["cover"]
        if d["style"]:
            voice.item([d["style"]])
    elif cmd == "dti":
        interface._must_display_target_info = not getattr(interface, '_must_display_target_info', False)
    elif cmd:
        cmd = re.sub("^a ", "add_units %s " % getattr(interface.place, "name", ""), cmd)
        cmd = re.sub("^v$", "victory", cmd)
        interface.server.write_line("cmd " + cmd)


def cmd_cmd(interface, *split_cmd):
    """执行作弊命令"""
    if interface.server.allow_cheatmode:
        cmd = " ".join(split_cmd)
        _execute_command(interface, cmd)
    else:
        voice.item(mp.BEEP)


def cmd_console(interface):
    """打开控制台"""
    if interface.server.allow_cheatmode:
        cmd = input_string(
            msg=mp.ENTER_COMMAND,
            pattern="^[a-zA-Z0-9 .,'@#$%^&*()_+-=?!]$",
            spell=False,
        )
        if cmd is None:
            return
        _execute_command(interface, cmd)
    else:
        voice.item(mp.BEEP)


def cmd_reload_parameters(interface):
    """重新加载参数"""
    parameters.load()
    sounds.update_volumes()


def _next_player(interface, player):
    players = interface.world.players
    index = (players.index(player) + 1) % len(players)
    return players[index]


def _change_player(interface, new_player):
    new_player.client.login, interface.server.player.client.login = (
        interface.server.player.client.login,
        new_player.client.login,
    )
    interface.server.player.client = new_player.client
    interface.server.player = new_player
    interface.server.player.client = interface.server
    game = getattr(interface.server, "game_session", None)
    if game is not None:
        game._change_player_used = True
        game._record_change_player_baseline()
    from .game_navigation import update_fog_of_war
    update_fog_of_war(interface)


def cmd_change_player(interface):
    """切换玩家（观察模式）"""
    if interface.server.allow_cheatmode:
        _change_player(interface, _next_player(interface, interface.player))
        p = interface.player
        from ..clientgameentity.properties import player_is_wildlife_only

        if player_is_wildlife_only(p):
            voice.item(mp.YOU_ARE + mp.ANIMAL)
        # 触发器脚本电脑（无具体身份）统一播报为 NPC，并加上中立/非中立限定，
        # 而不是读出内部 login（如 "ai_timers" / "中立 1"）。判据集中在
        # Player.is_script_npc：覆盖战役电脑（含被升格的）与普通地图（如 td2）里的
        # timers 脚本 AI。这正是 td2 按 Ctrl+Shift+F4 切视角误读 "ai_timers" 的修复点。
        elif getattr(p, "is_script_npc", False):
            from ..clientgameentity.base import compute_title

            qualifier = mp.NEUTRAL if getattr(p, "neutral", False) else mp.NON_NEUTRAL
            voice.item(mp.YOU_ARE + qualifier + compute_title("ai_timers"))
        else:
            voice.item(mp.YOU_ARE + p.name)
    else:
        voice.item(mp.BEEP)


# 其他功能
def cmd_objectives(interface, inc=1):
    """逐条播报任务目标。F9 下一条，Shift+F9 上一条。"""
    entries = collect_objective_entries(interface.world, interface.player)
    if not entries:
        voice.item(mp.BEEP)
        return

    count = len(entries)
    if getattr(interface, "_objective_view_count", None) != count:
        interface._objective_view_index = -1
        interface._objective_view_count = count

    current = getattr(interface, "_objective_view_index", -1)
    new_index = navigate_objective_index(current, int(inc), count)
    interface._objective_view_index = new_index
    voice.item(entries[new_index])


def cmd_help(interface, incr):
    """显示帮助"""
    incr = int(incr)
    voice.item(help_msg("game", incr))


def direction_to_msg(interface, o):
    """计算方向信息"""
    from .game_navigation import place_xy
    import math
    from ..lib.sound import angle
    x, y = place_xy(interface)
    d = distance(x, y, o.x, o.y)
    if d < interface.square_width / 3 / 2:
        return mp.AT_THE_CENTER
    direction = math.degrees(angle(x, y, o.x, o.y, 0))
    from .game_navigation import direction_to_msgpart
    mp_direction = direction_to_msgpart(direction)
    if mp_direction == mp.EAST:
        return mp.TO_THE_EAST  # special case in French
    if mp_direction == mp.WEST:
        return mp.TO_THE_WEST  # special case in French
    return mp.TO_THE + mp_direction


def _minimap_stereo(interface, place):
    """小地图立体声定位"""
    from .game_navigation import coords_in_map
    from ..lib.sound import stereo
    x, y = coords_in_map(interface, place)
    flattening_factor = 2.0
    xc, yc = coords_in_map(interface, interface.place)
    dx = (x - xc) * 6.0 / (interface.xcmax + 1)
    dy = (y - yc) * 6.0 / (interface.ycmax + 1) / flattening_factor
    return stereo(0, 0, dx, dy, 90)


def launch_alert(interface, place, sound_id):
    """发起警报"""
    psounds.play_stereo(
        sounds.get_sound(sound_id), vol=_minimap_stereo(interface, place), limit=0.5
    )


def srv_alert(interface, s):
    """处理服务器警报"""
    id_place, sound_id = s.split(",")
    place = interface.player.get_object_by_id(int(id_place))
    launch_alert(interface, place, int(sound_id))


# 导出的函数供其他模块使用
__all__ = [
    'resources', 'available_population', 'used_population',
    'cmd_resource_status', 'cmd_population_status', 'send_resource_alerts_if_needed',
    'cmd_toggle_side_filter', 'cmd_toggle_type_filter', 'cmd_gamemenu',
    'cmd_toggle_cheatmode', 'cmd_cmd', 'cmd_console', 'cmd_reload_parameters',
    'cmd_change_player', 'cmd_objectives', 'cmd_help', 'direction_to_msg',
    'launch_alert', 'srv_alert', 'send_msg_if_playing',
    'gm_quit', 'gm_slow_speed', 'gm_normal_speed', 'gm_fast_speed',
    'gm_very_fast_speed', 'gm_save', '_execute_command'
]