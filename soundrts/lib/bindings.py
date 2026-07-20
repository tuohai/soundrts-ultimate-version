import re

import pygame
from pygame import (
    K_LALT,
    K_LCTRL,
    K_LSHIFT,
    K_RALT,
    K_RCTRL,
    K_RSHIFT,
    KMOD_ALT,
    KMOD_CTRL,
    KMOD_LSHIFT,
    KMOD_RSHIFT,
    KMOD_SHIFT,
)

from .defs import preprocess
from .log import warning


class _Error(Exception):
    pass


# SHIFT = either side; LSHIFT / RSHIFT = that side only (must not mix with SHIFT).
_allowed_mods = ("CTRL", "ALT", "SHIFT", "LSHIFT", "RSHIFT")
_SHIFT_SIDE_MODS = frozenset({"SHIFT", "LSHIFT", "RSHIFT"})


# These constants are missing in some pygame builds.
pygame.KSCAN_QUOTE = 52
pygame.KSCAN_BACKQUOTE = 53

# 与键盘布局无关：按物理键位（SDL scancode）匹配，而非字符 keycode。
# 例如 AZERTY 的 ² 与 QWERTY 的 ` 在同一物理键位（scancode 53）。
_SCANCODE_KEY_NAMES = {
    "BACKQUOTE": pygame.KSCAN_BACKQUOTE,
    "QUOTE": pygame.KSCAN_QUOTE,
}


def _normalized_key(s):
    words = s.split()
    mods = words[:-1]
    for mod in mods:
        if mod not in _allowed_mods:
            raise _Error("'%s' is not an allowed key modifier" % mod)
    shift_sides = [m for m in mods if m in _SHIFT_SIDE_MODS]
    if len(shift_sides) > 1:
        raise _Error("use only one of SHIFT, LSHIFT, RSHIFT")
    normalized_mods = tuple(1 if m in mods else 0 for m in _allowed_mods)
    key_name = words[-1]

    if key_name in _SCANCODE_KEY_NAMES:
        return normalized_mods, _SCANCODE_KEY_NAMES[key_name], True

    # 特殊字符处理
    if len(key_name) == 1:
        # 对于单个字符，使用字符的ASCII码值
        key = ord(key_name.upper())
    else:
        # 对于非单个字符的按键名称，尝试使用pygame常量
        try:
            key = getattr(pygame, "K_" + key_name)
        except AttributeError:
            try:
                # 尝试使用scan code
                key = getattr(pygame, "KSCAN_" + key_name)
            except AttributeError:
                raise _Error("'%s' is not a key" % key_name)

    return normalized_mods, key, False


_modifiers_as_keys = (K_LCTRL, K_LALT, K_LSHIFT, K_RCTRL, K_RALT, K_RSHIFT)


def _live_shift_sides(mod):
    """Return (any_shift, left, right).

    Prefer pygame L/R bits when present. Only consult Win32 when the event
    has generic SHIFT but neither KMOD_LSHIFT nor KMOD_RSHIFT (wx / some
    pygame paths lose the side).
    """
    left = bool(mod & KMOD_LSHIFT)
    right = bool(mod & KMOD_RSHIFT)
    if (mod & KMOD_SHIFT) and not left and not right:
        try:
            import ctypes

            win_left = bool(ctypes.windll.user32.GetKeyState(0xA0) & 0x8000)
            win_right = bool(ctypes.windll.user32.GetKeyState(0xA1) & 0x8000)
            if win_left or win_right:
                left, right = win_left, win_right
        except Exception:
            pass
    any_shift = bool(mod & KMOD_SHIFT) or left or right
    return any_shift, left, right


def _normalized_event(e):
    if e.key in _modifiers_as_keys:
        # modifiers never modify another modifier
        return (0, 0, 0, 0, 0), e.key

    ctrl = 1 if e.mod & KMOD_CTRL else 0
    alt = 1 if e.mod & KMOD_ALT else 0
    any_shift, left, right = _live_shift_sides(e.mod)
    # Event tuple always records live L/R; lookup tries specific then SHIFT.
    mods = (ctrl, alt, 1 if any_shift else 0, 1 if left else 0, 1 if right else 0)

    # 修复：正确处理pygame按键常量到ASCII字符的转换
    # 对于字母按键，需要直接映射到对应的ASCII大写字母
    if pygame.K_a <= e.key <= pygame.K_z:  # 字母按键范围
        # 将pygame字母按键转换为对应的ASCII大写字母
        key = ord("A") + (e.key - pygame.K_a)  # A=65, B=66, ...
    else:
        key = e.key  # 使用原始key代码

    return mods, key


def _binding_mod_candidates(event_mods):
    """Prefer LSHIFT/RSHIFT bindings, then generic SHIFT, then no-shift.

    event_mods: (ctrl, alt, any_shift, left, right)
    binding mods: (ctrl, alt, SHIFT, LSHIFT, RSHIFT) flags from _allowed_mods.
    """
    ctrl, alt, any_shift, left, right = event_mods
    out = []
    if left and not right:
        out.append((ctrl, alt, 0, 1, 0))  # LSHIFT
    if right and not left:
        out.append((ctrl, alt, 0, 0, 1))  # RSHIFT
    if left and right:
        # both held: try left-specific then right-specific
        out.append((ctrl, alt, 0, 1, 0))
        out.append((ctrl, alt, 0, 0, 1))
    if any_shift:
        out.append((ctrl, alt, 1, 0, 0))  # SHIFT (either)
    if not any_shift:
        out.append((ctrl, alt, 0, 0, 0))
    # de-dupe while preserving order
    seen = set()
    uniq = []
    for m in out:
        if m not in seen:
            seen.add(m)
            uniq.append(m)
    return uniq


class Bindings:
    def __init__(self):
        self._bindings = {}
        self._scan_bindings = {}
        self._definitions = dict()

    def _apply_definitions(self, line):
        # "\w" means "alphanumeric character (or the underscore)"
        # "(?<!\w)" means "no '\w' before"
        # "(?!\w)" means "no '\w' after"
        for name, value in list(self._definitions.items()):
            # replace name with value
            line = re.sub(r"(?<!\w)%s(?!\w)" % name, value, line)
        return line

    def _add_definition(self, line):
        try:
            _, name, value = line.strip().split(" ", 2)
        except ValueError:
            raise _Error("the defined value is missing")
        self._definitions[name] = value

    def _add_binding(self, line, command_from_name):
        key_string, command_string = line.strip().split(":", 1)
        normalized_mods, key, is_scancode = _normalized_key(key_string)
        try:
            command_name, args = command_string.split(None, 1)
        except ValueError:
            command_name = command_string.strip()
            args = ""
        # Note: maybe the client should interpret the args string
        # and eventually provide a preformatter and a validator
        # for each command. For example to avoid splitting then joining again.
        command = command_from_name(command_name), args.split()
        target = self._scan_bindings if is_scancode else self._bindings
        target[(normalized_mods, key)] = command

    def _process_line(self, line, command_from_name):
        if line.startswith("#define "):
            self._add_definition(line)
        elif ":" in line:
            self._add_binding(line, command_from_name)
        elif line:
            raise _Error("the line must be a binding or a definition")

    def load(self, s, client, prefix="cmd"):
        # 每次加载前重置内部状态，避免重复加载或反序列化后残留的定义影响解析
        # 这可修复存档恢复后绑定被错误拓展为宏名（如 SOLDIER）的问题
        self._bindings = {}
        self._scan_bindings = {}
        self._definitions = dict()
        def command_from_name(name):
            try:
                return getattr(client, prefix + "_" + name)
            except AttributeError:
                raise _Error("'%s' is not a command" % name)

        for line in preprocess(s).splitlines():
            try:
                line = self._apply_definitions(line)
                self._process_line(line, command_from_name)
            except _Error as err:
                warning("error in bindings.txt (line ignored):\n%s\n(%s)", line, err)

    def _run_binding(self, table, mods, key):
        entry = table.get((mods, key))
        if entry is None:
            return False
        cmd, args = entry
        cmd(*args)
        return True

    def process_keydown_event(self, e):
        # 尝试找到绑定的命令并执行
        try:
            event_mods, key = _normalized_event(e)
            scancode = getattr(e, "scancode", None)
            for mods in _binding_mod_candidates(event_mods):
                if scancode is not None and self._run_binding(
                    self._scan_bindings, mods, scancode
                ):
                    return True
                if self._run_binding(self._bindings, mods, key):
                    return True
            return False
        except (KeyError, AttributeError) as err:
            # 该键没有绑定
            from .log import debug
            debug(f"未找到键绑定: {e.key}, 错误: {err}")
            return False
