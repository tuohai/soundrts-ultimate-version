"""Browseable square terrain info overlay (CTRL+SHIFT+F7 / map I)."""

from .. import msgparts as mp
from ..clientmedia import voice
from ..definitions import style
from ..lib.bindings import Bindings
from ..lib.msgs import localize_voice_msg, nb2msg, nb2msg_float
from ..lib.nofloat import PRECISION


def _terrain_xy(interface):
    if getattr(interface, "zoom_mode", False) and getattr(interface, "zoom", None):
        z = interface.zoom
        return (z.xmin + z.xmax) / 2.0, (z.ymin + z.ymax) / 2.0
    return None, None


def _is_scouted(interface, place):
    if getattr(interface, "cheatmode", False):
        return True
    return place in getattr(interface, "scouted_before_squares", ()) or place in getattr(
        interface, "scouted_squares", ()
    )


def _vs_nav_items(raw):
    """Build navigable voice items from ``unit value unit value ...``."""
    if not raw:
        return []
    tokens = list(raw)
    items = []
    i = 0
    while i + 1 < len(tokens):
        unit_type = tokens[i]
        value = tokens[i + 1]
        i += 2
        title = style.get(unit_type, "title") or [str(unit_type)]
        if isinstance(title, str):
            title = [title]
        try:
            value_float = float(value)
        except (TypeError, ValueError):
            continue
        items.append(list(title) + mp.VERSUS + nb2msg_float(value_float))
    return items


def build_square_info_attrs(interface, place, x=None, y=None):
    """Return attribute tuples ``(key, label_msg, value)`` for the square-info screen.

    *value* is either a voice-msg list, or ``("VS_ITEMS", [item, ...])`` for
    left/right browsing of ``*_vs`` entries.
    """
    from ..lib.square_terrain_rules import resolve_square_layers, terrain_property
    from .game_navigation import _square_terrain

    attrs = []
    if place is None:
        return attrs

    terrain_voice = _square_terrain(place, x, y)
    if terrain_voice:
        while terrain_voice and terrain_voice[: len(mp.COMMA)] == mp.COMMA:
            terrain_voice = terrain_voice[len(mp.COMMA) :]
        attrs.append(("", mp.RMG_TERRAIN, terrain_voice))

    if x is not None and y is not None and hasattr(place, "high_ground_at"):
        height = 1 if place.high_ground_at(x, y) else 0
    else:
        height = getattr(place, "height", 0)
    attrs.append(("", mp.HEIGHT, nb2msg(height)))

    width_m = max(0, (place.xmax - place.xmin) // PRECISION)
    attrs.append(("", mp.SQUARE_WIDTH, nb2msg(width_m) + mp.METERS))

    if hasattr(place, "terrain_speed_at") and x is not None:
        speed = place.terrain_speed_at(x, y)
    else:
        speed = getattr(place, "terrain_speed", (100, 100))
    if speed and speed != (100, 100):
        attrs.append(
            (
                "",
                mp.SPEED,
                nb2msg(speed[0]) + ["%"] + [" "] + nb2msg(speed[1]) + ["%"],
            )
        )

    if hasattr(place, "terrain_cover_at") and x is not None:
        cover = place.terrain_cover_at(x, y)
    else:
        cover = getattr(place, "terrain_cover", (0, 0))
    if cover and cover != (0, 0):
        attrs.append(
            (
                "",
                mp.TERRAIN_COVER,
                nb2msg(cover[0]) + ["%"] + [" "] + nb2msg(cover[1]) + ["%"],
            )
        )

    layers = resolve_square_layers(place, x, y)
    terrain_name = layers.get("type_name") or ""
    vs_props = (
        ("speed_vs", mp.SPEED_VS),
        ("cover_vs", mp.COVER_VS),
        ("dodge_vs", mp.DODGE_VS),
        ("mdg_vs", mp.MDG_VS),
        ("rdg_vs", mp.RDG_VS),
        ("mdg_cd_vs", mp.MDG_CD_VS),
        ("rdg_cd_vs", mp.RDG_CD_VS),
    )
    for prop, label in vs_props:
        items = _vs_nav_items(terrain_property(terrain_name, prop, ()))
        if not items:
            continue
        if len(items) == 1:
            attrs.append(("", label, items[0]))
        else:
            attrs.append(("", label, ("VS_ITEMS", items)))
    return attrs


def _display_current(interface, show_name=True):
    attrs = getattr(interface, "_square_info_attrs", []) or []
    idx = getattr(interface, "_square_info_index", 0)
    if not attrs or idx < 0 or idx >= len(attrs):
        return
    _, name, value = attrs[idx]
    if isinstance(value, tuple) and len(value) == 2 and value[0] == "VS_ITEMS":
        items = value[1]
        interface._square_info_sub_items = items
        sub = getattr(interface, "_square_info_sub_index", 0)
        if sub >= len(items):
            sub = 0
        elif sub < 0:
            sub = len(items) - 1
        interface._square_info_sub_index = sub
        current = items[sub]
        counter = [f" ({sub + 1}/{len(items)})"]
        if show_name:
            voice.item(localize_voice_msg(name + mp.COLON + current + mp.COMMA + counter))
        else:
            voice.item(localize_voice_msg(current + mp.COMMA + counter))
        return

    interface._square_info_sub_items = []
    if show_name:
        voice.item(localize_voice_msg(name + mp.COLON + value))
    else:
        voice.item(localize_voice_msg(value))


def _setup_bindings(interface):
    bindings_str = (
        "UP: _square_info_prev\n"
        "DOWN: _square_info_next\n"
        "LEFT: _square_info_sub_prev\n"
        "RIGHT: _square_info_sub_next\n"
        "ESCAPE: _exit_square_info_screen\n"
        "F5: history_previous\n"
        "F6: history_next\n"
        "LALT: history_stop_primary\n"
        "RALT: history_stop_secondary\n"
    )
    interface._bindings = Bindings()
    interface._bindings.load(bindings_str, interface)


def _close_other_overlays(interface):
    if getattr(interface, "_in_inventory_screen", False):
        interface.inventory_screen.cmd__inventory_escape()
    if getattr(interface, "_in_equipment_screen", False):
        interface.equipment_screen.cmd__equipment_escape()
    if getattr(interface, "_in_attributes_screen", False):
        interface.cmd__exit_attributes_screen()
    if getattr(interface, "_in_square_info_screen", False):
        cmd__exit_square_info_screen(interface)


def open_square_info_screen(interface):
    """Open browseable square terrain info for the current place."""
    place = getattr(interface, "place", None)
    if place is None:
        voice.item(mp.NOTHING)
        return

    if not _is_scouted(interface, place):
        voice.item(localize_voice_msg(list(place.title) + mp.COMMA + mp.UNKNOWN))
        return

    x, y = _terrain_xy(interface)
    attrs = build_square_info_attrs(interface, place, x, y)
    if not attrs:
        voice.item(mp.NO_ATTRIBUTES)
        return

    _close_other_overlays(interface)

    if getattr(interface, "_original_bindings", None) is None:
        interface._original_bindings = interface._bindings

    interface._square_info_attrs = attrs
    interface._square_info_index = 0
    interface._square_info_sub_index = 0
    interface._square_info_sub_items = []
    interface._in_square_info_screen = True

    voice.item(
        localize_voice_msg(
            list(place.title)
            + mp.COMMA
            + mp.HOTKEY_SAY_SQUARE_INFO
            + mp.COMMA
            + mp.PRESS_ESC_TO_EXIT
        )
    )
    _setup_bindings(interface)
    _display_current(interface)


def cmd_say_square_info(interface):
    """Hotkey entry: open square terrain info screen."""
    if getattr(interface, "_in_square_info_screen", False):
        cmd__exit_square_info_screen(interface, announce_exit=False)
    open_square_info_screen(interface)


def cmd__exit_square_info_screen(interface, announce_exit=True):
    if not getattr(interface, "_in_square_info_screen", False):
        return
    interface._in_square_info_screen = False
    interface._square_info_attrs = []
    interface._square_info_index = 0
    interface._square_info_sub_index = 0
    interface._square_info_sub_items = []
    if announce_exit:
        voice.item(mp.EXITING_ATTRIBUTES_SCREEN)
    if getattr(interface, "_original_bindings", None) is not None:
        from .interface_modes import restore_active_bindings

        restore_active_bindings(interface)
        interface._original_bindings = None


def cmd__square_info_prev(interface):
    attrs = getattr(interface, "_square_info_attrs", []) or []
    if not attrs:
        return
    idx = getattr(interface, "_square_info_index", 0)
    interface._square_info_index = idx - 1 if idx > 0 else len(attrs) - 1
    interface._square_info_sub_index = 0
    _display_current(interface)


def cmd__square_info_next(interface):
    attrs = getattr(interface, "_square_info_attrs", []) or []
    if not attrs:
        return
    idx = getattr(interface, "_square_info_index", 0)
    interface._square_info_index = idx + 1 if idx < len(attrs) - 1 else 0
    interface._square_info_sub_index = 0
    _display_current(interface)


def cmd__square_info_sub_prev(interface):
    items = getattr(interface, "_square_info_sub_items", []) or []
    if len(items) <= 1:
        voice.item(mp.BEEP)
        return
    sub = getattr(interface, "_square_info_sub_index", 0)
    interface._square_info_sub_index = sub - 1 if sub > 0 else len(items) - 1
    _display_current(interface, show_name=False)


def cmd__square_info_sub_next(interface):
    items = getattr(interface, "_square_info_sub_items", []) or []
    if len(items) <= 1:
        voice.item(mp.BEEP)
        return
    sub = getattr(interface, "_square_info_sub_index", 0)
    interface._square_info_sub_index = sub + 1 if sub < len(items) - 1 else 0
    _display_current(interface, show_name=False)


def process_keyboard_event(interface, e):
    """Return True if the square-info screen consumed the key event."""
    if not getattr(interface, "_in_square_info_screen", False):
        return False
    try:
        return bool(interface._bindings.process_keydown_event(e))
    except Exception:
        return False
