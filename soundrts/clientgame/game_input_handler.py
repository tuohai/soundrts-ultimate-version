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


def _process_events(interface):
    """处理用户输入事件"""
    # Warning: only sound/voice/keyboard events here, no server event.
    # Because a bad loop might occur when called from a function
    # waiting for a combat sound to end.
    for e in pygame.event.get():
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
            # 首先检查是否在缩放输入模式
            if interface._zoom_input_mode:
                if _handle_zoom_input(interface, e):
                    continue  # 输入已处理，跳过其他处理
            
            # 然后尝试属性界面的键盘处理
            if hasattr(interface, "_process_keyboard_event") and interface._process_keyboard_event(e):
                continue
                
            if interface.shortcut_mode:
                _execute_order_shortcut(interface, e)
                interface.shortcut_mode = False
            else:
                # L/R Shift+C copy last utterance; Shift+A append when fresh
                try:
                    from pygame.locals import K_a, K_c
                    from ..lib import voice_libs

                    key = e.key
                    if key in (ord("C"), ord("A")):
                        key = ord(chr(key).lower())
                    if (
                        (e.mod & KMOD_SHIFT)
                        and not (e.mod & KMOD_CTRL)
                        and key in (K_a, K_c)
                        and (key == K_c or voice_libs.announce_is_fresh())
                        and voice_libs.handle_hotkey(key, e.mod)
                    ):
                        continue
                except Exception:
                    pass
                try:
                    interface._bindings.process_keydown_event(e)
                except KeyError:
                    voice.item(mp.BEEP)
        elif interface.display_is_active:
            _process_fullscreen_mode_mouse_event(interface, e)


def _process_fullscreen_mode_mouse_event(interface, e):
    """处理全屏模式下的鼠标事件"""
    if e.type == MOUSEMOTION:
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
                _select_and_say_square(interface, square)
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
            if interface.mouse_select_origin == e.pos:
                if interface.grid_view.object_from_mousepos(e.pos):
                    from .game_unit_control import cmd_command_unit
                    cmd_command_unit(interface)
            elif interface.mouse_select_origin:
                interface.group = interface.grid_view.units_from_mouserect(
                    interface.mouse_select_origin, e.pos
                )
                from .game_unit_control import say_group
                say_group(interface)
            interface.mouse_select_origin = None


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
    '_process_events',
    '_process_fullscreen_mode_mouse_event', 
    '_execute_order_shortcut',
    '_handle_zoom_input',
    '_start_zoom_input_mode',
    '_process_zoom_input',
    '_loop'
]