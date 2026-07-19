import os
import re
import sys
import time
from pathlib import Path

import pygame
from pygame.locals import (
    K_BACKSPACE,
    K_DELETE,
    K_DOWN,
    K_END,
    K_EQUALS,
    K_ESCAPE,
    K_F1,
    K_F2,
    K_F3,
    K_F5,
    K_F6,
    K_F7,
    K_F8,
    K_F9,
    K_F10,
    K_F11,
    K_F12,
    K_HOME,
    K_a,
    K_c,
    K_i,
    K_KP_ENTER,
    K_KP_MINUS,
    K_KP_PLUS,
    K_LALT,
    K_LEFT,
    K_LCTRL,
    K_LSHIFT,
    K_m,
    K_MINUS,
    K_RALT,
    K_RCTRL,
    K_RETURN,
    K_RIGHT,
    K_RSHIFT,
    K_TAB,
    K_UP,
    K_v,
    K_x,
    K_z,
    KEYDOWN,
    KMOD_ALT,
    KMOD_CTRL,
    KMOD_SHIFT,
    QUIT,
    TEXTINPUT,
    USEREVENT,
)

from . import msgparts as mp
from .clienthelp import help_msg
from .clientmedia import modify_volume, sounds, toggle_fullscreen, voice
from .lib.log import warning
from .lib.msgs import LITERAL_TEXT_PREFIX, NB_ENCODE_SHIFT, literal_text_msg, nb2msg
from .lib.sound import psounds, toggle_music, adjust_music_volume, get_music_status
from .paths import TMP_PATH
from .definitions import style
from .lib.resource import res

# 从 style.txt 中读取菜单音效配置，如果没有配置则返回None
def get_menu_sound(sound_name, default_value=None):
    sound_value = style.get("parameters", sound_name, warn_if_not_found=False)
    if sound_value and sound_value:
        try:
            # 尝试转换为整数，如果失败则作为字符串音效ID处理
            try:
                return int(sound_value[0])
            except (ValueError, TypeError):
                # 如果无法转换为整数，则直接返回字符串作为音效ID
                return sound_value[0]
        except Exception:
            warning(f"Invalid {sound_name} value in style.txt: {sound_value}.")
    return default_value

# 获取当前mod名称
def get_current_mod():
    from .paths import BASE_PACKAGE_PATH
    from .lib.resource import res
    
    # 如果未加载任何mod，则返回base mod
    if not res.mods:
        return Path(BASE_PACKAGE_PATH).name
        
    # 如果有多个mod，返回第一个（主要的）mod
    return res.mods.split(",")[0].strip()

# 主菜单音效
def get_main_menu_select_sound():
    return get_menu_sound("main_menu_select_sound", get_menu_sound("select_sound"))

def get_main_menu_confirm_sound():
    return get_menu_sound("main_menu_confirm_sound", get_menu_sound("confirm_sound"))

def get_main_menu_return_sound():
    return get_menu_sound("main_menu_return_sound", get_menu_sound("return_sound"))

# 子菜单音效
def get_submenu_select_sound():
    # 首先尝试获取子菜单特定的选择音效
    submenu_sound = get_menu_sound("submenu_select_sound")
    # 如果子菜单没有特定音效，则使用主菜单的选择音效
    if submenu_sound is None:
        return get_main_menu_select_sound()
    return submenu_sound

def get_submenu_confirm_sound():
    # 首先尝试获取子菜单特定的确认音效
    submenu_sound = get_menu_sound("submenu_confirm_sound")
    # 如果子菜单没有特定音效，则使用主菜单的确认音效
    if submenu_sound is None:
        return get_main_menu_confirm_sound()
    return submenu_sound

def get_submenu_return_sound():
    # 首先尝试获取子菜单特定的返回音效
    submenu_sound = get_menu_sound("submenu_return_sound")
    # 如果子菜单没有特定音效，则使用主菜单的返回音效
    if submenu_sound is None:
        return get_main_menu_return_sound()
    return submenu_sound


def string_to_msg(s, spell=True):
    if not spell:
        return [s]
    l = []
    for c in s:
        if c == ".":
            l.extend(mp.DOT)
        elif c in "0123456789":
            l.extend(nb2msg(c))
        else:
            l.extend(c)
    return l


def _filter_chars_by_pattern(text, pattern):
    return "".join(c for c in text if re.match(pattern, c) is not None)


_clipboard_ready = False


def _ensure_clipboard():
    global _clipboard_ready
    if _clipboard_ready:
        return True
    try:
        import pygame.scrap as scrap

        if hasattr(scrap, "get_text"):
            if not scrap.get_init():
                try:
                    scrap.init()
                except Exception:
                    pass
            _clipboard_ready = True
            return True
        if not scrap.get_init():
            scrap.init()
        _clipboard_ready = True
        return True
    except Exception:
        return False


def _clipboard_get_text():
    if not _ensure_clipboard():
        return ""
    try:
        import pygame.scrap as scrap

        if hasattr(scrap, "get_text"):
            return scrap.get_text() or ""
        raw = scrap.get(getattr(scrap, "SCRAP_TEXT", "text/plain"))
        if not raw:
            return ""
        if isinstance(raw, bytes):
            return raw.decode("utf-8", errors="replace")
        return str(raw)
    except Exception:
        return ""


def _clipboard_set_text(text):
    if not _ensure_clipboard():
        return False
    try:
        import pygame.scrap as scrap

        if hasattr(scrap, "put_text"):
            scrap.put_text(text)
            return True
        scrap.put(getattr(scrap, "SCRAP_TEXT", "text/plain"), text.encode("utf-8"))
        return True
    except Exception:
        return False


# Windows 上 Ctrl+字母 有时上报为控制字符 (1–26) 且 mod 为 0；但 8/9/13/27 等也是
# 退格、Tab、回车、Esc 的键码，不能一律当作 Ctrl 组合键。
_STANDALONE_CTRL_CHAR_KEYS = frozenset(range(1, 27)) - frozenset({8, 9, 10, 13, 27})


def _input_key_mod(e):
    """合并事件 mod 与实时按键状态；Windows 上 Ctrl 组合键可能 mod 为 0。"""
    mod = getattr(e, "mod", 0)
    try:
        mod |= pygame.key.get_mods()
    except pygame.error:
        pass
    key = getattr(e, "key", 0)
    if key in _STANDALONE_CTRL_CHAR_KEYS:
        mod |= KMOD_CTRL
    return mod


def _input_key_code(key, mod):
    """将 Ctrl+字母 的控制字符 (1–26) 映射为 K_a..K_z。"""
    if mod & KMOD_CTRL and 1 <= key <= 26:
        return ord("a") + key - 1
    return key


class _EditableTextBuffer:
    """可编辑文本缓冲：光标、选区、撤销/重做。"""

    def __init__(self, text="", max_length=None):
        self.s = text
        self.cursor = len(text)
        self.sel_anchor = self.cursor
        self.max_length = max_length
        self._undo = []
        self._redo = []

    def snapshot(self):
        return (self.s, self.cursor, self.sel_anchor)

    def _restore(self, snap):
        self.s, self.cursor, self.sel_anchor = snap

    def push_undo(self):
        self._undo.append(self.snapshot())
        self._redo.clear()

    def undo(self):
        if not self._undo:
            return False
        self._redo.append(self.snapshot())
        self._restore(self._undo.pop())
        return True

    def redo(self):
        if not self._redo:
            return False
        self._undo.append(self.snapshot())
        self._restore(self._redo.pop())
        return True

    def selection_range(self):
        if self.sel_anchor == self.cursor:
            return None
        return sorted((self.sel_anchor, self.cursor))

    def replace_range(self, start, end, insert, *, record_undo=True):
        if record_undo:
            self.push_undo()
        if self.max_length is not None:
            room = max(0, self.max_length - (len(self.s) - (end - start)))
            insert = insert[:room]
        self.s = self.s[:start] + insert + self.s[end:]
        self.cursor = start + len(insert)
        self.sel_anchor = self.cursor

    def delete_selection(self, *, record_undo=True):
        sel = self.selection_range()
        if sel is None:
            return False
        self.replace_range(sel[0], sel[1], "", record_undo=record_undo)
        return True

    def selected_text(self):
        sel = self.selection_range()
        if sel is None:
            return self.s
        return self.s[sel[0] : sel[1]]

    def insert_filtered(self, text, filter_fn, *, record_undo=True):
        filtered = filter_fn(text)
        if not filtered:
            return False
        sel = self.selection_range()
        if sel is None:
            self.replace_range(self.cursor, self.cursor, filtered, record_undo=record_undo)
        else:
            self.replace_range(sel[0], sel[1], filtered, record_undo=record_undo)
        return True

    def handle_ctrl_key(self, key, mod, filter_fn, announce):
        if key == K_a:
            self.sel_anchor = 0
            self.cursor = len(self.s)
            announce(self.s)
            return True
        if key == K_z:
            if mod & KMOD_SHIFT:
                if self.redo():
                    announce(self.s)
            elif self.undo():
                announce(self.s)
            return True
        if key == K_c:
            _clipboard_set_text(self.selected_text())
            return True
        if key == K_x:
            text = self.selected_text()
            if text:
                _clipboard_set_text(text)
                if self.selection_range() is None:
                    self.replace_range(0, len(self.s), "")
                else:
                    self.delete_selection()
                announce(self.s)
            return True
        if key == K_v:
            pasted = _clipboard_get_text()
            if pasted and self.insert_filtered(pasted, filter_fn):
                announce(self.s)
            return True
        return False


def _announce_typed_text(text):
    voice.item(literal_text_msg(text))


def _input_string_announce(s, spell=True, prefix=None):
    if prefix is not None:
        voice.item(prefix + mp.PERIOD + literal_text_msg(s))
    elif s:
        _announce_typed_text(s)
    else:
        voice.item([])


def input_string(msg=[], pattern="^[a-zA-Z0-9]$", default="", spell=True, max_length=None):
    # 用 item 而非 menu：menu 会阻塞到提示音播完，控制台/聊天输入无法立刻键入。
    voice.item(list(msg))
    buf = _EditableTextBuffer(default, max_length)
    filter_fn = lambda text: _filter_chars_by_pattern(text, pattern)

    def announce(_s):
        _input_string_announce(buf.s, spell)

    pygame.event.clear([KEYDOWN, TEXTINPUT])
    while True:
        e = pygame.event.poll()
        if e.type == QUIT:
            sys.exit()
        elif e.type == KEYDOWN:
            if e.key in [K_LSHIFT, K_RSHIFT, K_LALT, K_RALT]:
                continue
            mod = _input_key_mod(e)
            key = _input_key_code(e.key, mod)
            if e.key in (K_RETURN, K_KP_ENTER):
                _announce_typed_text(buf.s)
                return buf.s
            elif e.key == K_ESCAPE:
                return None
            elif mod & KMOD_CTRL:
                if buf.handle_ctrl_key(key, mod, filter_fn, announce):
                    continue
            elif e.key == K_BACKSPACE:
                if not buf.delete_selection():
                    if buf.cursor > 0:
                        buf.replace_range(buf.cursor - 1, buf.cursor, "")
                announce(buf.s)
            elif e.key == K_DELETE:
                if not buf.delete_selection():
                    if buf.cursor < len(buf.s):
                        buf.replace_range(buf.cursor, buf.cursor + 1, "")
                announce(buf.s)
            elif getattr(e, "unicode", "") and re.match(pattern, e.unicode) is not None:
                try:
                    buf.insert_filtered(e.unicode, filter_fn)
                    _announce_typed_text(buf.s)
                except Exception:
                    warning("error reading character from keyboard")
                    voice.item(mp.BEEP + mp.PERIOD + literal_text_msg(buf.s))
            elif e.key not in (K_LCTRL, K_RCTRL):
                voice.item(mp.BEEP + mp.PERIOD + literal_text_msg(buf.s))
        elif e.type == USEREVENT:
            voice.update()
        voice.update()  # useful for SAPI


# 文件名中禁用的字符（Windows/常见跨平台）。
_FORBIDDEN_FILENAME_CHARS = set('\\/:*?"<>|\0')


def _is_valid_filename_char(ch):
    """允许的字符：可打印（含中文等多字节字符），且不在禁用列表中。"""
    if not ch:
        return False
    if ch in _FORBIDDEN_FILENAME_CHARS:
        return False
    # 过滤控制字符（\t、\r、\n 等都不应该出现在文件名中）。
    if not ch.isprintable():
        return False
    return True



def _is_valid_chat_char(ch):
    if not ch:
        return False
    if ch in "\n\r\t\0":
        return False
    return ch.isprintable()


def input_text(msg=None, default="", max_length=80, char_filter=None):
    """让玩家输入一段任意语言的文本（支持中文等通过 IME 输入的字符）。

    - 回车 / 小键盘回车：确认，返回当前文本
    - Esc：取消，返回 None
    - Ctrl+A 全选、Ctrl+Z 撤销、Ctrl+Shift+Z 重做
    - 退格 / Delete：删除字符或选区
    - 其它可打印字符：在光标处插入（支持 IME TEXTINPUT）
    """
    import time as _time
    if char_filter is None:
        char_filter = _is_valid_filename_char
    if msg is None:
        msg = []
    voice.item(list(msg) + ([default] if default else []))
    buf = _EditableTextBuffer(default, max_length)
    filter_fn = lambda text: "".join(c for c in text if char_filter(c))

    def announce(_s):
        _announce_typed_text(buf.s)

    pygame.event.clear([KEYDOWN, TEXTINPUT])
    try:
        pygame.key.start_text_input()
    except Exception:
        pass
    expected_queue: list[str] = []
    try:
        while True:
            e = pygame.event.poll()
            if e.type == QUIT:
                sys.exit()
            elif e.type == KEYDOWN:
                mod = _input_key_mod(e)
                key = _input_key_code(e.key, mod)
                if e.key in (K_RETURN, K_KP_ENTER):
                    _announce_typed_text(buf.s)
                    return buf.s
                elif e.key == K_ESCAPE:
                    return None
                elif mod & KMOD_CTRL:
                    expected_queue.clear()
                    if buf.handle_ctrl_key(key, mod, filter_fn, announce):
                        continue
                elif e.key == K_BACKSPACE:
                    expected_queue.clear()
                    if not buf.delete_selection():
                        if buf.cursor > 0:
                            buf.replace_range(buf.cursor - 1, buf.cursor, "")
                    announce(buf.s)
                elif e.key == K_DELETE:
                    expected_queue.clear()
                    if not buf.delete_selection():
                        if buf.cursor < len(buf.s):
                            buf.replace_range(buf.cursor, buf.cursor + 1, "")
                    announce(buf.s)
                elif (
                    getattr(e, "unicode", "")
                    and char_filter(e.unicode)
                ):
                    if not expected_queue:
                        buf.push_undo()
                    if buf.insert_filtered(e.unicode, filter_fn, record_undo=False):
                        expected_queue.append(e.unicode)
                        announce(buf.s)
                    else:
                        voice.item(mp.BEEP + literal_text_msg(buf.s))
                elif e.key not in (K_LCTRL, K_RCTRL, K_LSHIFT, K_RSHIFT):
                    voice.item(mp.BEEP + literal_text_msg(buf.s))
            elif e.type == TEXTINPUT:
                ch = getattr(e, "text", "") or ""
                if not ch:
                    continue
                filtered = filter_fn(ch)
                if not filtered:
                    voice.item(mp.BEEP + literal_text_msg(buf.s))
                    continue
                matched = False
                if expected_queue:
                    n = len(filtered)
                    if (
                        len(expected_queue) >= n
                        and "".join(expected_queue[:n]) == filtered
                    ):
                        del expected_queue[:n]
                        matched = True
                if matched:
                    continue
                if expected_queue:
                    n = len(expected_queue)
                    start = max(0, buf.cursor - n)
                    buf.s = buf.s[:start] + buf.s[buf.cursor:]
                    buf.cursor = start
                    buf.sel_anchor = start
                    expected_queue.clear()
                else:
                    buf.push_undo()
                if not buf.insert_filtered(filtered, filter_fn, record_undo=False):
                    voice.item(mp.BEEP + literal_text_msg(buf.s))
                    continue
                announce(buf.s)
            elif e.type == USEREVENT:
                voice.update()
            voice.update()
            _time.sleep(0.005)
    finally:
        try:
            pygame.key.stop_text_input()
        except Exception:
            pass


def confirm_yes_no(prompt_msg):
    """显示一个确认提示并等待玩家按回车（确认）或 Esc（取消）。

    返回 True 表示玩家确认，False 表示取消。

    使用 voice.menu 而不是 voice.alert：这样玩家在提示朗读过程中按下回车 / Esc
    可以立刻打断并被识别（voice.alert 会丢弃这些键），从而让"按回车确认、按 Esc 取消"
    的体验更加灵敏。
    """
    # 先把可能误触的旧键事件清空，但 voice.menu 会保留新按下的键给我们处理。
    pygame.event.clear([KEYDOWN, TEXTINPUT])
    voice.menu(prompt_msg)
    while True:
        e = pygame.event.poll()
        if e.type == QUIT:
            sys.exit()
        elif e.type == KEYDOWN:
            if e.key in (K_RETURN, K_KP_ENTER):
                return True
            elif e.key == K_ESCAPE:
                return False
            # 其它键不退出循环，等待明确的回车或 Esc。
        elif e.type == USEREVENT:
            voice.update()
        voice.update()


def _remember_path(menu_name):
    return os.path.join(TMP_PATH, menu_name + ".txt")


CLOSE_MENU = 1


def _first_letter(choice):
    """首字母用于菜单按键跳转。

    地图标题形如 ``['m1', 5012, 3001]``：必须以 ``m1`` 的 ``m`` 为准。
    不可对这类字符串走 ``translate_sound_number`` —— 其 ``_global_lookup_text``
    会扫描全部战役 tts，在百级地图列表上单次跳转可达约 1 秒。
    """
    if not choice or not choice[0]:
        return None

    for sound_number in choice[0]:
        try:
            if isinstance(sound_number, str):
                if sound_number.startswith(LITERAL_TEXT_PREFIX):
                    text = sound_number[len(LITERAL_TEXT_PREFIX) :]
                    if text:
                        return text[0].lower()
                # Map names / literal labels (“m1”, “pm1”, …)：直接取首字符。
                if sound_number and not sound_number.isdigit():
                    return sound_number[0].lower()
            # nb2msg(n) → 1000000+n：战役章节等数字前缀，本地解码，不走全局 TTS。
            key = "%s" % sound_number
            if key.isdigit() and int(key) >= NB_ENCODE_SHIFT:
                return str(int(key) - NB_ENCODE_SHIFT)[0].lower()
            # 数字 TTS id（如随机地图 5033）：只查本地层，避免全局扫描。
            t = sounds.text(key)
            if t:
                return str(t)[0].lower()
        except Exception:
            pass
    return None


class Menu:

    server = None

    def __init__(self, title=None, choices=None, default_choice_index=0, remember=None, menu_type="main"):
        if title is None:
            title = []
        self.title = title
        if choices is None:
            choices = []
        self.choices = choices
        self.choice_index = None
        self.default_choice_index = default_choice_index
        self.remember = remember
        self.end_loop = False
        # 标记菜单类型，默认为主菜单
        self.menu_type = menu_type
        # 每个菜单项可以附带 rename / delete 回调（用于存档、回放等列表）。
        # 以选项在 self.choices 中的索引为 key，存储 {"rename": fn, "delete": fn}。
        self._choice_extras = {}
        if self.remember is not None:
            try:
                with open(_remember_path(remember), encoding="utf-8") as f:
                    self._remembered_choice = f.read()
            except Exception:
                self._remembered_choice = ""
        # 初始化按键绑定处理器
        from .lib.bindings import Bindings
        self._bindings = Bindings()
        try:
            # 只加载菜单类支持的按键绑定
            # 当前支持：toggle_music, music_volume_up, music_volume_down
            bindings_text = """
; 音乐控制快捷键
ALT m: toggle_music
ALT HOME: music_volume_up
ALT KP_PLUS: music_volume_up
ALT EQUALS: music_volume_up
ALT END: music_volume_down
ALT KP_MINUS: music_volume_down
ALT MINUS: music_volume_down
"""
            self._bindings.load(bindings_text, self)
        except Exception as e:
            from .lib.log import warning
            warning(f"无法加载菜单按键绑定: {e}")

    def _say_choice(self):
        # 根据菜单类型选择不同的选择音效
        sound_id = get_submenu_select_sound() if self.menu_type == "submenu" else get_main_menu_select_sound()
        if sound_id is not None:
            # 获取当前mod名称
            current_mod = get_current_mod()
            # 只从当前mod加载音效
            sound = sounds.get_sound(sound_id, warn=False, restrict_to_mod=current_mod)
            if sound:
                psounds.play_stereo(sound)
        choice = self.choices[self.choice_index]
        msg = list(choice[0])
        if len(choice) > 2:
            msg += mp.COMMA + choice[2]
        voice.item(msg)

    def _choice_exists(self):
        return self.choice_index is not None and 0 <= self.choice_index < len(
            self.choices
        )

    def _select_next_choice(self, first_letter=None, inc=1):
        if not self.choices:
            return
        n = len(self.choices)
        if first_letter:
            letter = first_letter.lower()
            step = 1 if inc >= 0 else -1
            if self.choice_index is None:
                # Fresh menu: always land on the first matching item in list
                # order (or last when searching backwards). Do not start from
                # default/remembered index — that would skip e.g. m1 to m2 when
                # the remembered map also starts with "m".
                start = 0 if step > 0 else n - 1
                for i in range(n):
                    idx = (start + i * step) % n
                    if _first_letter(self.choices[idx]) == letter:
                        self.choice_index = idx
                        self._say_choice()
                        return
                return
            # Already on an item: cycle to the next match after the current one.
            for i in range(1, n + 1):
                idx = (self.choice_index + i * step) % n
                if _first_letter(self.choices[idx]) == letter:
                    self.choice_index = idx
                    self._say_choice()
                    return
            return
        if self.choice_index is None:
            self.choice_index = self.default_choice_index
            if inc == -1:
                self.choice_index -= 1
                self.choice_index %= n
        else:
            self.choice_index = (self.choice_index + inc) % n
        self._say_choice()

    def _confirm_choice(self):
        # 根据菜单类型选择不同的确认音效
        sound_id = get_submenu_confirm_sound() if self.menu_type == "submenu" else get_main_menu_confirm_sound()
        if sound_id is not None:
            # 获取当前mod名称
            current_mod = get_current_mod()
            # 只从当前mod加载音效
            sound = sounds.get_sound(sound_id, warn=False, restrict_to_mod=current_mod)
            if sound:
                psounds.play_stereo(sound)
        if self._choice_exists() and self.choices[self.choice_index]:
            voice.confirmation(self.choices[self.choice_index][0])
            self.choice_done = True

    def _process_keydown(self, e):

        # In order to avoid the accumulation of repeated KEYDOWN events
        # (this glitch happens when building the menu takes too much time),
        # remove additional KEYDOWN events from the queue.
        pygame.event.clear([KEYDOWN])

        # 首先尝试通过按键绑定处理事件
        try:
            if self._bindings.process_keydown_event(e):
                return  # 如果按键绑定已处理，则不再继续处理
        except Exception as e:
            from .lib.log import warning
            warning(f"处理按键绑定时出错: {e}")

        # 以下是传统的硬编码按键处理

        # Shift+Enter：重命名当前菜单项（仅当该项注册了 on_rename 时生效）。
        if (
            e.key in (K_RETURN, K_KP_ENTER)
            and (e.mod & KMOD_SHIFT)
            and self._choice_exists()
        ):
            extras = self._choice_extras.get(self.choice_index)
            if extras and extras.get("rename"):
                try:
                    extras["rename"]()
                except Exception as ex:
                    from .lib.log import exception as _log_exception
                    _log_exception("rename handler failed: %s" % ex)
                    voice.alert(mp.BEEP)
                return

        # Delete：删除当前菜单项；按住 Shift 时直接删除不询问。
        if e.key == K_DELETE and self._choice_exists():
            extras = self._choice_extras.get(self.choice_index)
            if extras and extras.get("delete"):
                immediate = bool(e.mod & KMOD_SHIFT)
                try:
                    extras["delete"](immediate=immediate)
                except Exception as ex:
                    from .lib.log import exception as _log_exception
                    _log_exception("delete handler failed: %s" % ex)
                    voice.alert(mp.BEEP)
                return

        if e.key in [K_ESCAPE, K_LEFT]:
            # 播放返回音效，根据菜单类型选择不同的返回音效
            sound_id = get_submenu_return_sound() if self.menu_type == "submenu" else get_main_menu_return_sound()
            if sound_id is not None:
                # 获取当前mod名称
                current_mod = get_current_mod()
                # 只从当前mod加载音效
                sound = sounds.get_sound(sound_id, warn=False, restrict_to_mod=current_mod)
                if sound:
                    psounds.play_stereo(sound)
            # 设置选项为最后一项，通常是"返回"选项
            self.choice_index = len(self.choices) - 1
            # 确认选择，但不播放确认音效
            if self._choice_exists() and self.choices[self.choice_index]:
                voice.confirmation(self.choices[self.choice_index][0])
                self.choice_done = True
            return
        elif e.key == K_TAB and e.mod & KMOD_SHIFT or e.key == K_UP:
            self._select_next_choice(inc=-1)
        elif e.key in [K_TAB, K_DOWN]:
            self._select_next_choice()
        elif e.key in (K_RETURN, K_KP_ENTER, K_RIGHT):
            return self._confirm_choice()
        elif e.key == K_F2 and e.mod & KMOD_CTRL:
            toggle_fullscreen()
        elif e.key == K_F1 and e.mod & KMOD_SHIFT or e.key == K_F2:
            voice.item(help_msg("menu", -1))
        elif e.key == K_F1:
            voice.item(help_msg("menu"))
        elif e.key == K_F3 and not (
            e.mod & (KMOD_CTRL | KMOD_ALT | KMOD_SHIFT)
        ):
            # Menu only: enable/disable secondary voice (not available in-match).
            try:
                from .lib import voice_libs

                voice_libs.toggle_secondary_voice_enabled(announce=True)
            except Exception:
                voice.item(mp.BEEP)
        elif e.key == K_F5:
            voice.previous()
        elif e.key == K_LALT:
            voice.say_next(tts_channel="primary")
        elif e.key == K_RALT:
            voice.say_next(tts_channel="secondary")
        elif e.key == K_F6:
            voice.say_next(history_only=True)
        elif e.key in (K_F9, K_F10, K_F11, K_F12) or (
            e.key in (K_c, K_a, ord("C"), ord("A"))
            and (e.mod & KMOD_SHIFT)
            and not (e.mod & KMOD_CTRL)
        ):
            # Dual voice libraries: F9–F12 / Shift+F9–F12; L/R Shift+C copy
            try:
                from .lib import voice_libs

                key = e.key
                if key in (ord("C"), ord("A")):
                    key = ord(chr(key).lower())
                if voice_libs.handle_hotkey(key, e.mod):
                    return
            except Exception:
                voice.item(mp.BEEP)
        elif e.key in [K_HOME, K_KP_PLUS]:
            modify_volume(1)
        elif e.key in [K_END, K_KP_MINUS]:
            modify_volume(-1)
        elif e.key == K_F7:
            if self.server is None:
                voice.item(mp.BEEP)
            else:
                msg = input_text(
                    msg=mp.ENTER_MESSAGE,
                    max_length=200,
                    char_filter=_is_valid_chat_char,
                )
                if msg:
                    self.server.write_line("say %s" % msg)
        elif e.unicode and e.mod & KMOD_SHIFT:
            self._select_next_choice(e.unicode, -1)
            # Drop auto-repeat / duplicate KEYDOWNs so one physical press
            # cannot advance from the first match (m1) to the second (m2).
            pygame.event.clear([KEYDOWN])
        elif e.unicode:
            self._select_next_choice(e.unicode)
            pygame.event.clear([KEYDOWN])
        elif e.key not in [K_LSHIFT, K_RSHIFT]:
            voice.item(mp.SELECT_AND_CONFIRM_EXPLANATION)

    def append(self, label, action, explanation=None, on_rename=None, on_delete=None):
        if explanation is None:
            explanation = []
        self.choices.append((label, action, explanation))
        idx = len(self.choices) - 1
        if on_rename is not None or on_delete is not None:
            self._choice_extras[idx] = {"rename": on_rename, "delete": on_delete}
        if self.remember is not None and self._remembered_choice == repr(label):
            # Remember last choice by default index — do not insert a duplicate
            # at the front (that made letter-jump hit the remembered map first,
            # e.g. last played m2 → pressing "m" selected m2 instead of m1).
            self.default_choice_index = idx

    def clear_choices(self):
        """清空所有菜单项和附加回调，便于在 rename/delete 后重新填充菜单。"""
        self.choices = []
        self._choice_extras = {}
        self.choice_index = None

    # 添加音乐控制命令
    def cmd_toggle_music(self):
        """开关音乐"""
        from . import config
        from .lib.sound import toggle_music
        music_enabled = toggle_music()
        config.save_audio_settings()

        # 语音反馈
        if music_enabled:
            voice.item(mp.MUSIC_ON)
            # 不需要再次调用play_menu_music，因为toggle_music已经根据当前菜单类型播放了相应的音乐
        else:
            voice.item(mp.MUSIC_OFF)
    
    def cmd_music_volume_up(self):
        """增加音乐音量"""
        from .lib.sound import adjust_music_volume
        from . import msgparts as mp
        
        # 停止当前所有语音播报，确保音量播报能立即听到
        from .lib import sound
        sound.stop()
        
        # 调整音量并获取百分比值（与主音量处理方式保持一致，传递1而不是0.1）
        volume_percent = adjust_music_volume(1)
        from . import config
        config.save_audio_settings()

        # 播报音量（与主音量处理方式保持一致）
        voice.item(nb2msg(volume_percent) + mp.PERCENT_VOLUME)
    
    def cmd_music_volume_down(self):
        """减小音乐音量"""
        from .lib.sound import adjust_music_volume
        from . import msgparts as mp
        
        # 停止当前所有语音播报，确保音量播报能立即听到
        from .lib import sound
        sound.stop()
        
        # 调整音量并获取百分比值（与主音量处理方式保持一致，传递-1而不是-0.1）
        volume_percent = adjust_music_volume(-1)
        from . import config
        config.save_audio_settings()

        # 播报音量（与主音量处理方式保持一致）
        voice.item(nb2msg(volume_percent) + mp.PERCENT_VOLUME)

    def update_menu(self, menu):
        old_title = self.title
        old_choices = self.choices
        try:
            old_choice = self.choices[self.choice_index]
        except (IndexError, TypeError):
            old_choice = None
        self.title, self.choices = menu.title, menu.choices
        if self.title and self.title != old_title:
            voice.menu(self.title)
        if self.choices != old_choices:
            self.choice_index = None
            if old_choice in self.choices:
                self.choice_index = self.choices.index(old_choice)

    def _execute_choice(self):
        label, action = self.choices[self.choice_index][:2]

        def cmd():
            pass

        args = ()
        if hasattr(action, "run"):
            cmd = action.run
        elif callable(action):
            cmd = action
        elif isinstance(action, tuple):
            cmd = action[0]
            args = action[1:]
        elif action == CLOSE_MENU:

            def cmd():
                return CLOSE_MENU

        if cmd(*args) == CLOSE_MENU:
            self.end_loop = True
        if self.remember is not None and action is not None:
            open(_remember_path(self.remember), "w").write(repr(label))
            # default_choice_index might be useful soon
            # for example: ServerMenu._get_creation_submenu()
            self.default_choice_index = self.choice_index
        else:
            self.default_choice_index = 0
        self.choice_index = None

    def _try_to_get_choice(self, e):
        if e.type == QUIT:
            sys.exit()
        if e.type == USEREVENT:
            voice.update()
        elif e.type == KEYDOWN:
            self._process_keydown(e)
        voice.update()  # useful for SAPI

    def _get_choice_from_static_menu(self):
        self.choice_done = False
        while not self.choice_done:
            self._try_to_get_choice(pygame.event.poll())
            time.sleep(0.01)

    def step(self):
        self.choice_done = False
        self._try_to_get_choice(pygame.event.poll())
        if self.choice_done:
            self._execute_choice()

    def run(self):
        if self.title:
            voice.menu(self.title)
        else:
            voice.menu(mp.MAKE_A_SELECTION2)
        self._get_choice_from_static_menu()
        self._execute_choice()

    def loop(self):
        self.end_loop = False
        while not self.end_loop:
            self.run()
