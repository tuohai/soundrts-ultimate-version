import re
import sys
import time

import pygame
from pygame.locals import (
    KEYDOWN,
    KMOD_CTRL,
    KMOD_SHIFT,
    MOUSEBUTTONDOWN,
    MOUSEBUTTONUP,
    MOUSEMOTION,
    MOUSEWHEEL,
    QUIT,
    USEREVENT,
    K_RETURN,
    K_KP_ENTER,
    K_ESCAPE,
    K_BACKSPACE,
)

from .. import msgparts as mp
from ..clientmedia import voice
from ..clientmenu import _announce_typed_text
from ..lib.log import exception
from ..lib.sound import psounds
from ..lib.msgs import literal_text_msg
from ..lib.mouse import set_cursor
from ..lib.screen import get_screen, set_game_mode

# Ctrl+F2 鼠标：双击判定
_MOUSE_DOUBLE_CLICK_MS = 400
_MOUSE_CLICK_TOLERANCE_PX = 5


def _collapse_keydown_repeats(events):
    """同一批次里同键的重复 KEYDOWN 只保留第一次。

    作弊模式 / 大地图下 ``select_square`` 很重时，pygame key-repeat 会在
    一次物理按键期间往队列塞入多个 KEYDOWN；若本帧 ``event.get()`` 一次
    取到整串，就会连续跳多格（a1→b1→c1→d1）。菜单侧用
    ``pygame.event.clear([KEYDOWN])`` 解决；游戏循环还需折叠已取出的批次。
    """
    seen_keys = set()
    out = []
    for e in events:
        if getattr(e, "type", None) == KEYDOWN:
            key = getattr(e, "key", None)
            if key in seen_keys:
                continue
            seen_keys.add(key)
        out.append(e)
    return out


def _mouse_is_click(origin, pos, tol=_MOUSE_CLICK_TOLERANCE_PX):
    if origin is None or pos is None:
        return False
    return abs(origin[0] - pos[0]) <= tol and abs(origin[1] - pos[1]) <= tol


def _mouse_is_double_click(interface, type_name, pos):
    now = pygame.time.get_ticks()
    last_t = getattr(interface, "_mouse_dbl_t", -10**9)
    last_type = getattr(interface, "_mouse_dbl_type", None)
    last_pos = getattr(interface, "_mouse_dbl_pos", None)
    ok = (
        now - last_t <= _MOUSE_DOUBLE_CLICK_MS
        and last_type == type_name
        and last_pos is not None
        and _mouse_is_click(last_pos, pos, tol=12)
    )
    interface._mouse_dbl_t = now
    interface._mouse_dbl_type = type_name
    interface._mouse_dbl_pos = pos
    return ok


def _process_events(interface):
    """处理用户输入事件"""
    # Warning: only sound/voice/keyboard events here, no server event.
    # Because a bad loop might occur when called from a function
    # waiting for a combat sound to end.
    for e in _collapse_keydown_repeats(pygame.event.get()):
        if e.type == USEREVENT:
            voice.update()
        elif e.type == USEREVENT + 1:
            psounds.update()
        # 处理倒地音效定时器事件
        elif e.type in interface._falling_callbacks:
            falling_data = interface._falling_callbacks.pop(e.type)
            falling_data['obj'].launch_event(falling_data['sound'])
            pygame.time.set_timer(e.type, 0)  # 停止定时器
        elif e.type == QUIT:
            sys.exit()
        elif e.type == KEYDOWN:
            # F9 目标字幕：Esc 关闭（开场目标播完后本就不该残留）
            if e.key == K_ESCAPE:
                try:
                    from ..lib import pygame_ui

                    if pygame_ui.narrative_is_active():
                        pygame_ui.end_narrative()
                        from .game_display import display

                        display(interface)
                        pygame.event.clear([KEYDOWN])
                        continue
                except Exception:
                    pass
            # 首先检查是否在缩放输入模式
            if interface._zoom_input_mode:
                if _handle_zoom_input(interface, e):
                    pygame.event.clear([KEYDOWN])
                    continue  # 输入已处理，跳过其他处理
            
            # 然后尝试属性界面的键盘处理
            if hasattr(interface, "_process_keyboard_event") and interface._process_keyboard_event(e):
                pygame.event.clear([KEYDOWN])
                continue
                
            if interface.shortcut_mode:
                _execute_order_shortcut(interface, e)
                interface.shortcut_mode = False
            else:
                # L/R Shift+C copy; L/R Shift+B append (primary / secondary)
                try:
                    from pygame.locals import K_b, K_c
                    from ..lib import voice_libs

                    key = e.key
                    if key in (ord("C"), ord("B")):
                        key = ord(chr(key).lower())
                    if (
                        (e.mod & KMOD_SHIFT)
                        and not (e.mod & KMOD_CTRL)
                        and key in (K_b, K_c)
                        and voice_libs.handle_hotkey(key, e.mod)
                    ):
                        pygame.event.clear([KEYDOWN])
                        continue
                except Exception:
                    pass
                try:
                    interface._bindings.process_keydown_event(e)
                except KeyError:
                    voice.item(mp.BEEP)
            # 处理可能很慢（作弊全图 + 大地图 select_square / TTS）。
            # 清掉处理期间 key-repeat 再塞进队列的 KEYDOWN，否则下一帧
            # 会连续跳多格。与 Menu._process_keydown 同模式。
            pygame.event.clear([KEYDOWN])
        elif interface.display_is_active:
            _process_fullscreen_mode_mouse_event(interface, e)


def _process_fullscreen_mode_mouse_event(interface, e):
    """处理全屏模式下的鼠标事件"""
    # 背包 / 装备栏覆盖层打开时拦截鼠标，避免误点地图
    try:
        from .game_gear_hud import gear_screen_active, handle_gear_click, hit_test_gear

        if gear_screen_active(interface):
            if e.type in (MOUSEBUTTONDOWN, MOUSEBUTTONUP) and e.button == 1:
                if hit_test_gear(interface, e.pos) is not None and e.type == MOUSEBUTTONDOWN:
                    mods = pygame.key.get_mods()
                    handle_gear_click(interface, e.pos, mods)
                    from .game_display import display

                    display(interface)
                if e.type == MOUSEBUTTONUP:
                    interface.mouse_select_origin = None
                return
            if e.type == MOUSEBUTTONDOWN:
                return
    except Exception:
        pass

    # 第二阶段 HUD：先吃掉命令条/队列点击，避免误点地图
    if e.type in (MOUSEBUTTONDOWN, MOUSEBUTTONUP) and e.button == 1:
        try:
            from .game_hud import handle_hud_click, hit_test_hud

            if hit_test_hud(interface, e.pos) is not None:
                if e.type == MOUSEBUTTONDOWN:
                    mods = pygame.key.get_mods()
                    handle_hud_click(interface, e.pos, mods)
                    from .game_display import display

                    display(interface)
                # DOWN 已处理则忽略成对的 UP，避免再走框选
                if e.type == MOUSEBUTTONUP:
                    interface.mouse_select_origin = None
                return
        except Exception:
            pass

    # 小地图点击：跳格（非缩放模式）
    if e.type == MOUSEBUTTONDOWN and e.button in (1, 3):
        try:
            sq = interface.grid_view.minimap_square_from_mousepos(e.pos)
        except Exception:
            sq = None
        if sq is not None:
            from .game_navigation import _select_and_say_square
            from .game_display import display

            if e.button == 1:
                interface.group = []
                interface.order = None
                interface.target = None
                _select_and_say_square(interface, sq, center_view=True)
                display(interface)
                return
            # 右键：跳到该格并作为默认命令目标
            _select_and_say_square(interface, sq, center_view=True)
            interface.target = None
            mods = pygame.key.get_mods()
            args = []
            if mods & KMOD_SHIFT:
                args += ["queue_order"]
            if mods & KMOD_CTRL:
                args += ["imperative"]
            from .game_orders import cmd_default

            cmd_default(interface, *args)
            display(interface)
            return

    if getattr(interface, "zoom_mode", False):
        _process_zoom_mode_mouse_event(interface, e)
        return

    # 滚轮：主地图放大/缩小（以鼠标位置为锚）
    if e.type == MOUSEWHEEL:
        if interface.grid_view.zoom_at_mouse(pygame.mouse.get_pos(), e.y > 0):
            from .game_display import display

            display(interface)
        return
    if e.type == MOUSEBUTTONDOWN and e.button in (4, 5):
        # 兼容部分环境仍发 button 4/5
        if interface.grid_view.zoom_at_mouse(e.pos, e.button == 4):
            from .game_display import display

            display(interface)
        return

    if e.type == MOUSEMOTION:
        # 悬停在 HUD 上时不跳格/读目标
        try:
            from .game_hud import hit_test_hud

            if hit_test_hud(interface, e.pos) is not None:
                return
        except Exception:
            pass
        square = interface.grid_view.square_from_mousepos(e.pos)
        target = interface.grid_view.object_from_mousepos(e.pos)
        if target is not None:
            if target != interface.target:
                interface.target = target
                from .game_unit_control import say_target
                say_target(interface)
                from .game_display import display
                display(interface)
                if interface.an_order_requiring_a_target_is_selected:
                    if interface.order.cls.keyword == "build":
                        set_cursor("square")
                    else:
                        set_cursor("target")
                else:
                    set_cursor("diamond")
        elif square is not None:
            if square != interface.place or interface.target is not None:
                from .game_navigation import _select_and_say_square
                # 划过选格不带动镜头，避免大地图无法玩
                _select_and_say_square(interface, square, center_view=False)
                interface.target = target
                if interface.an_order_requiring_a_target_is_selected:
                    if interface.order.cls.keyword == "build":
                        set_cursor("square")
                    else:
                        set_cursor("target")
                else:
                    set_cursor("tri_left")
    elif e.type == MOUSEBUTTONDOWN:
        if e.button == 1:  # left mouse button
            if interface.an_order_requiring_a_target_is_selected:
                mods = pygame.key.get_mods()
                args = []
                if mods & KMOD_SHIFT:
                    args += ["queue_order"]
                if mods & KMOD_CTRL:
                    args += ["imperative"]
                from .game_orders import cmd_validate
                cmd_validate(interface, *args)
            else:
                interface.mouse_select_origin = e.pos
        elif e.button == 3:  # right mouse button
            # HUD 上右键不发默认命令
            try:
                from .game_hud import hit_test_hud

                if hit_test_hud(interface, e.pos) is not None:
                    return
            except Exception:
                pass
            # do nothing if the mouse is pointing on nothing
            if interface.grid_view.square_from_mousepos(e.pos) is not None:
                mods = pygame.key.get_mods()
                args = []
                if mods & KMOD_SHIFT:
                    args += ["queue_order"]
                if mods & KMOD_CTRL:
                    args += ["imperative"]
                from .game_orders import cmd_default
                cmd_default(interface, *args)
    elif e.type == MOUSEBUTTONUP:
        if e.button == 1:  # left mouse button
            _handle_left_mouse_up(interface, e)


def _process_zoom_mode_mouse_event(interface, e):
    """F8 缩放 + Ctrl+F2：鼠标操作当前大方格的子格与单位。"""
    try:
        from .game_hud import hit_test_hud

        if e.type == MOUSEMOTION and hit_test_hud(interface, e.pos) is not None:
            return
        if e.type == MOUSEBUTTONDOWN and e.button == 3:
            if hit_test_hud(interface, e.pos) is not None:
                return
    except Exception:
        pass

    from .game_display import display

    if e.type == MOUSEMOTION:
        target = interface.grid_view.object_from_mousepos(e.pos)
        if target is not None:
            if target != interface.target:
                interface.target = target
                from .game_unit_control import say_target

                say_target(interface)
                display(interface)
            if interface.an_order_requiring_a_target_is_selected:
                set_cursor(
                    "square"
                    if interface.order.cls.keyword == "build"
                    else "target"
                )
            else:
                set_cursor("diamond")
            return

        # 空地：移动子格焦点（变了才播报）
        if interface.grid_view.world_from_mousepos(e.pos) is None:
            return
        changed = interface.grid_view.move_zoom_to_mousepos(e.pos)
        if changed:
            interface.target = None
            interface.zoom.select()
            interface.zoom.say()
            display(interface)
        if interface.an_order_requiring_a_target_is_selected:
            set_cursor(
                "square" if interface.order.cls.keyword == "build" else "target"
            )
        else:
            set_cursor("tri_left")
        return

    if e.type == MOUSEBUTTONDOWN:
        if e.button == 1:
            if interface.an_order_requiring_a_target_is_selected:
                # 先对准点击的子格 / 单位，再确认命令
                obj = interface.grid_view.object_from_mousepos(e.pos)
                if obj is not None:
                    interface.target = obj
                else:
                    interface.grid_view.move_zoom_to_mousepos(e.pos)
                    interface.target = None
                mods = pygame.key.get_mods()
                args = []
                if mods & KMOD_SHIFT:
                    args += ["queue_order"]
                if mods & KMOD_CTRL:
                    args += ["imperative"]
                from .game_orders import cmd_validate

                cmd_validate(interface, *args)
                display(interface)
            else:
                interface.mouse_select_origin = e.pos
        elif e.button == 3:
            obj = interface.grid_view.object_from_mousepos(e.pos)
            if obj is not None:
                interface.target = obj
            else:
                if interface.grid_view.world_from_mousepos(e.pos) is None:
                    return
                interface.grid_view.move_zoom_to_mousepos(e.pos)
                interface.target = None
            mods = pygame.key.get_mods()
            args = []
            if mods & KMOD_SHIFT:
                args += ["queue_order"]
            if mods & KMOD_CTRL:
                args += ["imperative"]
            from .game_orders import cmd_default

            cmd_default(interface, *args)
            display(interface)
        return

    if e.type == MOUSEBUTTONUP and e.button == 1:
        _handle_left_mouse_up_zoom(interface, e)


def _handle_left_mouse_up_zoom(interface, e):
    """缩放模式下左键抬起：点选单位 / 框选 / 点击子格。"""
    origin = interface.mouse_select_origin
    interface.mouse_select_origin = None
    if origin is None:
        return
    if interface.an_order_requiring_a_target_is_selected:
        return

    from .game_unit_control import (
        command_unit,
        mouse_add_units_to_group,
        mouse_select_same_type,
        mouse_toggle_unit_in_group,
        say_group,
        units as controllable_units,
    )
    from .game_display import display

    mods = pygame.key.get_mods()
    shift = bool(mods & KMOD_SHIFT)

    if _mouse_is_click(origin, e.pos):
        obj = interface.grid_view.object_from_mousepos(e.pos)
        controllable = set(controllable_units(interface))
        if obj is not None and obj in controllable:
            if shift:
                mouse_toggle_unit_in_group(interface, obj)
            elif _mouse_is_double_click(interface, obj.type_name, e.pos):
                mouse_select_same_type(interface, obj)
            else:
                interface._mouse_dbl_t = pygame.time.get_ticks()
                interface._mouse_dbl_type = obj.type_name
                interface._mouse_dbl_pos = e.pos
                command_unit(interface, obj)
                interface.order = None
            interface.target = obj
            # 焦点跟到单位所在子格
            try:
                interface.zoom.move_to(obj)
            except Exception:
                pass
            display(interface)
            return

        if interface.grid_view.world_from_mousepos(e.pos) is None:
            return
        if not shift:
            interface.group = []
            interface.order = None
        interface.grid_view.move_zoom_to_mousepos(e.pos)
        interface.target = None if obj is None else obj
        interface._mouse_dbl_t = -(10**9)
        interface._mouse_dbl_type = None
        interface.zoom.select()
        interface.zoom.say()
        display(interface)
        return

    ids = interface.grid_view.units_from_mouserect(origin, e.pos)
    if shift:
        mouse_add_units_to_group(interface, ids)
    else:
        interface.group = ids
        interface.order = None
        say_group(interface)
    display(interface)


def _handle_left_mouse_up(interface, e):
    """左键抬起：点选 / 双击同类型 / Shift 加选 / 框选 / 空地点格跳转。"""
    origin = interface.mouse_select_origin
    interface.mouse_select_origin = None
    if origin is None:
        return
    if interface.an_order_requiring_a_target_is_selected:
        return

    from .game_unit_control import (
        command_unit,
        mouse_add_units_to_group,
        mouse_select_same_type,
        mouse_toggle_unit_in_group,
        say_group,
        units as controllable_units,
    )
    from .game_display import display

    mods = pygame.key.get_mods()
    shift = bool(mods & KMOD_SHIFT)

    if _mouse_is_click(origin, e.pos):
        obj = interface.grid_view.object_from_mousepos(e.pos)
        controllable = set(controllable_units(interface))
        if obj is not None and obj in controllable:
            if shift:
                mouse_toggle_unit_in_group(interface, obj)
            elif _mouse_is_double_click(interface, obj.type_name, e.pos):
                mouse_select_same_type(interface, obj)
            else:
                # 记录单击，供下一次双击判定；并点选该单位
                interface._mouse_dbl_t = pygame.time.get_ticks()
                interface._mouse_dbl_type = obj.type_name
                interface._mouse_dbl_pos = e.pos
                command_unit(interface, obj)
                interface.order = None
            interface.target = obj
            display(interface)
            return

        # 点空地 / 非可控目标：跳转到该格（传统 RTS 左键空地也取消选择）
        square = interface.grid_view.square_from_mousepos(e.pos)
        if square is not None:
            if not shift:
                interface.group = []
                interface.order = None
            from .game_navigation import _select_and_say_square

            _select_and_say_square(interface, square, center_view=False)
            interface.target = None if obj is None else obj
            # 空地点击不算单位双击
            interface._mouse_dbl_t = -10**9
            interface._mouse_dbl_type = None
            display(interface)
        return

    # 框选
    ids = interface.grid_view.units_from_mouserect(origin, e.pos)
    if shift:
        mouse_add_units_to_group(interface, ids)
    else:
        interface.group = ids
        interface.order = None
        say_group(interface)
    display(interface)


def _execute_order_shortcut(interface, e):
    """执行指令快捷键"""
    from .game_orders import orders, _select_order, cmd_validate
    for o in orders(interface):
        if o.shortcut == e.unicode:
            _select_order(interface, o)
            if o.nb_args == 0:
                cmd_validate(interface)
            return
    voice.item(mp.BEEP)


def _handle_zoom_input(interface, e):
    """处理缩放比例输入"""
    if e.type == KEYDOWN:
        if e.key in (K_RETURN, K_KP_ENTER):
            # 用户按回车确认输入
            _process_zoom_input(interface)
            interface._zoom_input_mode = False
            return True
        elif e.key == K_ESCAPE:
            # 用户取消输入
            interface._zoom_input_mode = False
            voice.item(["已取消"])
            return True
        elif e.key == K_BACKSPACE:
            # 删除字符
            if interface._zoom_input_string:
                interface._zoom_input_string = interface._zoom_input_string[:-1]
                _announce_typed_text(
                    interface._zoom_input_string if interface._zoom_input_string else "空"
                )
            return True
        elif e.unicode and re.match("^[0-9x]$", e.unicode):
            # 有效字符
            interface._zoom_input_string += e.unicode
            _announce_typed_text(interface._zoom_input_string)
            return True
        else:
            # 无效字符
            voice.item(mp.BEEP)
            return True
    return False


def _start_zoom_input_mode(interface):
    """启动非阻塞的缩放比例输入模式"""
    interface._zoom_input_mode = True
    interface._zoom_input_string = ""
    voice.item(["请输入缩放比例，格式如3x3或4x4"])


def _process_zoom_input(interface):
    """处理用户输入的缩放比例"""
    try:
        if not interface._zoom_input_string:
            voice.item(["输入为空"])
            return
            
        # 解析输入格式
        parts = interface._zoom_input_string.lower().split('x')
        if len(parts) != 2:
            voice.item(["格式错误，请使用如3x3的格式"])
            return
            
        width, height = int(parts[0]), int(parts[1])
        
        # 验证是否为方形网格
        if width != height:
            voice.item(["只支持方形网格，如3x3或4x4"])
            return
            
        # 验证范围
        if width < 2 or width > 20:
            voice.item(mp.ZOOM_RANGE_ERROR if hasattr(mp, "ZOOM_RANGE_ERROR") else ["缩放范围错误"])
            return
            
        interface._zoom_precision = width
        voice.item(literal_text_msg(f"{interface._zoom_precision}x{interface._zoom_precision}"))
        
    except ValueError:
        voice.item(["输入格式错误"])


def _loop(interface):
    """主游戏循环"""
    from ..clientserver import ConnectionAbortedError

    set_game_mode(True)
    pygame.event.clear()
    interface.next_update = time.time()
    interface.end_loop = False
    interface._last_edge_scroll_t = time.time()
    while not interface.end_loop:
        try:
            if 0 and interface.display_is_active:
                # updated often (for total delay)
                from .game_display import display
                display(interface)
            interface.server.update()
            if (
                interface._time_to_ask_for_next_update()
                and interface.server.orders_are_ready()
            ):
                interface._ask_for_update()
            from .game_display import _animate_objects
            _animate_objects(interface)
            _process_events(interface)
            # 帝国式边缘滚屏：每帧根据鼠标贴边平移镜头
            if (
                interface.display_is_active
                and not getattr(interface, "zoom_mode", False)
            ):
                now = time.time()
                dt = now - getattr(interface, "_last_edge_scroll_t", now)
                interface._last_edge_scroll_t = now
                try:
                    if interface.grid_view.update_edge_scroll(dt):
                        from .game_display import display

                        display(interface)
                except Exception:
                    pass
            if interface.auto:
                if interface.auto[0].run(interface):
                    del interface.auto[0]
            interface._process_srv_events()
            voice.update()  # useful for SAPI
            time.sleep(0.001)
        except SystemExit:
            raise
        except ConnectionAbortedError:
            raise
        except:
            exception("error in clientgame loop")
    set_game_mode(False)


# 导出的函数供其他模块使用
__all__ = [
    '_collapse_keydown_repeats',
    '_process_events',
    '_process_fullscreen_mode_mouse_event',
    '_process_zoom_mode_mouse_event',
    '_handle_left_mouse_up',
    '_handle_left_mouse_up_zoom',
    '_execute_order_shortcut',
    '_handle_zoom_input',
    '_start_zoom_input_mode',
    '_process_zoom_input',
    '_loop'
]