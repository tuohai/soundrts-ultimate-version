"""各界面层热键映射目录（主绑定列表与显示名）。"""

from __future__ import annotations

from typing import List, Tuple

from . import msgparts as mp
from .lib.msgs import nb2msg

Catalog = List[Tuple[str, list]]

# 与 interface_modes.MODE_FILES 的 key 一致
LAYER_ORDER = (
    "global",
    "unit",
    "building",
    "command",
    "skill",
    "rpg",
    "help",
    "map",
    "diplomacy",
)

# 经典单文件方案下，按键映射菜单顶层仅列 classic；第一人称在 classic 子菜单内
CLASSIC_MAPPING_LAYERS = ("classic",)


def _msgs(*parts: list) -> list:
    out: list = []
    for part in parts:
        out.extend(part)
    return out


def keyboard_slot_label(keyboard_slot: str) -> list:
    """keyboard 槽位的通用显示名（不绑定某阵营具体单位 title）。"""
    if keyboard_slot == "worker":
        return list(mp.HOTKEY_SLOT_WORKER)
    if keyboard_slot == "building":
        return list(mp.HOTKEY_SLOT_BUILDING)
    if keyboard_slot.startswith("soldier"):
        try:
            n = int(keyboard_slot[7:])
            return list(mp.HOTKEY_SLOT_SOLDIER) + nb2msg(n)
        except ValueError:
            pass
    if keyboard_slot.startswith("building"):
        try:
            n = int(keyboard_slot[8:])
            return list(mp.HOTKEY_SLOT_BUILDING) + nb2msg(n)
        except ValueError:
            pass
    return [keyboard_slot]


def _local_select(slot_msgs: list) -> list:
    return _msgs(slot_msgs, mp.HOTKEY_LOCAL_SELECT_ALL)


def _cycle_unit(slot_msgs: list) -> list:
    return _msgs(slot_msgs, mp.HOTKEY_CYCLE_UNIT)


def _group_selection_catalog_items(prefix: str) -> Catalog:
    """group 1–5 local 与 recall_group 6–9 的显示名（按实际游戏语义）。"""
    return [
        (
            f"{prefix}.group.1.local",
            _msgs(mp.HOTKEY_SELECT_UNITS, mp.HOTKEY_SELECT_ALL),
        ),
        (
            f"{prefix}.group.2.local",
            _msgs(mp.HOTKEY_SELECT_UNITS, mp.HOTKEY_SELECT_HALF),
        ),
        (
            f"{prefix}.group.3.local",
            _msgs(mp.HOTKEY_SELECT_UNITS, mp.HOTKEY_SELECT_THIRD),
        ),
        (
            f"{prefix}.group.4.local",
            _msgs(mp.HOTKEY_SELECT_UNITS, mp.HOTKEY_SELECT_QUARTER),
        ),
        (
            f"{prefix}.group.5.local",
            _msgs(mp.HOTKEY_SELECT_UNITS, mp.HOTKEY_SELECT_FIFTH),
        ),
        (f"{prefix}.ungroup", list(mp.HOTKEY_UNGROUP)),
        (f"{prefix}.recall_group.6", list(mp.HOTKEY_CONTROL_GROUP_1)),
        (f"{prefix}.recall_group.7", list(mp.HOTKEY_CONTROL_GROUP_2)),
        (f"{prefix}.recall_group.8", list(mp.HOTKEY_CONTROL_GROUP_3)),
        (f"{prefix}.recall_group.9", list(mp.HOTKEY_CONTROL_GROUP_4)),
    ]


def _visual_immersion() -> list:
    return list(mp.HOTKEY_VISUAL_IMMERSION)


def _visual_fullscreen() -> list:
    return list(mp.HOTKEY_VISUAL_TOGGLE)


def _group_store_catalog_items(prefix: str) -> Catalog:
    items: Catalog = []
    for slot, num in ((6, 1), (7, 2), (8, 3), (9, 4)):
        items.append(
            (
                f"{prefix}.set_group.{slot}",
                list(mp.HOTKEY_SAVE_GROUP) + nb2msg(num),
            )
        )
        items.append(
            (
                f"{prefix}.append_group.{slot}",
                list(mp.HOTKEY_APPEND_TO_GROUP) + nb2msg(num),
            )
        )
    return items


def _group_map_catalog_items(prefix: str) -> Catalog:
    portions = [
        (1, mp.HOTKEY_SELECT_ALL),
        (2, mp.HOTKEY_SELECT_HALF),
        (3, mp.HOTKEY_SELECT_THIRD),
        (4, mp.HOTKEY_SELECT_QUARTER),
        (5, mp.HOTKEY_SELECT_FIFTH),
    ]
    items: Catalog = []
    for n, portion in portions:
        items.append((f"{prefix}.group.{n}", _msgs(mp.HOTKEY_GROUP_ON_MAP, portion)))
    return items


def _classic_supplement_catalog() -> Catalog:
    """classic 方案 legacy_bindings 中其余可映射主绑定。"""
    items: Catalog = [
        ("classic.objectives.-1", list(mp.HOTKEY_OBJECTIVES_PREV)),
        ("classic.help.-1", list(mp.HOTKEY_HELP_PREV)),
        ("classic.history_next", list(mp.HOTKEY_HISTORY_NEXT)),
        ("classic.history_stop", list(mp.HOTKEY_HISTORY_STOP)),
        ("classic.history_stop_primary", list(mp.HOTKEY_HISTORY_STOP_PRIMARY)),
        ("classic.history_stop_secondary", list(mp.HOTKEY_HISTORY_STOP_SECONDARY)),
        (
            "classic.select_alliance_candidate.-1",
            list(mp.HOTKEY_ALLIANCE_CANDIDATE_PREV),
        ),
        ("classic.toggle_cheatmode", list(mp.HOTKEY_TOGGLE_CHEATMODE)),
        ("classic.toggle_tick", list(mp.HOTKEY_TOGGLE_TICK)),
        ("classic.reload_parameters", list(mp.HOTKEY_RELOAD_PARAMETERS)),
        ("classic.music_volume_up", list(mp.HOTKEY_MUSIC_VOLUME_UP)),
        ("classic.music_volume_down", list(mp.HOTKEY_MUSIC_VOLUME_DOWN)),
        ("classic.get_zoom_precision", list(mp.HOTKEY_QUERY_ZOOM_PRECISION)),
        (
            "classic.change_zoom_precision.-1",
            list(mp.HOTKEY_ZOOM_PRECISION_DECREASE),
        ),
        (
            "classic.change_zoom_precision.1",
            list(mp.HOTKEY_ZOOM_PRECISION_INCREASE),
        ),
        (
            "classic.select_target.1.useful",
            list(mp.HOTKEY_SELECT_USEFUL_TARGET_NEXT),
        ),
        (
            "classic.select_target.-1.useful",
            list(mp.HOTKEY_SELECT_USEFUL_TARGET_PREV),
        ),
        (
            "classic.select_order.-1.inactive_included",
            list(mp.HOTKEY_BROWSE_PREV_ORDER),
        ),
        (
            "classic.select_order.1.inactive_only",
            list(mp.HOTKEY_ORDER_INACTIVE_ONLY),
        ),
        (
            "classic.select_order.-1.inactive_only",
            _msgs(mp.HOTKEY_BROWSE_PREV_ORDER, mp.HOTKEY_ORDER_INACTIVE_ONLY),
        ),
        (
            "classic.toggle_side_filter.-1",
            list(mp.HOTKEY_TOGGLE_SIDE_FILTER_BACK),
        ),
        (
            "classic.toggle_type_filter.-1",
            list(mp.HOTKEY_TOGGLE_TYPE_FILTER_BACK),
        ),
        (
            "classic.validate.queue_order",
            _msgs(mp.HOTKEY_VALIDATE_COMMAND, mp.HOTKEY_VALIDATE_QUEUE),
        ),
        (
            "classic.validate.imperative",
            _msgs(mp.HOTKEY_VALIDATE_COMMAND, mp.HOTKEY_VALIDATE_IMPERATIVE),
        ),
        (
            "classic.validate.imperative.queue_order",
            _msgs(
                mp.HOTKEY_VALIDATE_COMMAND,
                mp.HOTKEY_VALIDATE_IMPERATIVE,
                mp.HOTKEY_ORDER_IN_QUEUE,
            ),
        ),
        (
            "classic.default.queue_order",
            _msgs(mp.HOTKEY_DEFAULT_COMMAND, mp.HOTKEY_ORDER_IN_QUEUE),
        ),
        (
            "classic.default.imperative",
            _msgs(mp.HOTKEY_DEFAULT_COMMAND, mp.HOTKEY_VALIDATE_IMPERATIVE),
        ),
        (
            "classic.default.imperative.queue_order",
            _msgs(
                mp.HOTKEY_DEFAULT_COMMAND,
                mp.HOTKEY_VALIDATE_IMPERATIVE,
                mp.HOTKEY_ORDER_IN_QUEUE,
            ),
        ),
        (
            "classic.do_again.now.queue_order",
            _msgs(mp.HOTKEY_DO_AGAIN_NOW, mp.HOTKEY_DO_AGAIN_QUEUE),
        ),
        ("classic.select_units.worker", _msgs(mp.HOTKEY_SLOT_WORKER, mp.HOTKEY_GLOBAL_SELECT_ALL)),
        (
            "classic.select_units.soldier1.soldier2.soldier3.soldier4.soldier5.soldier6.soldier7",
            _msgs(mp.HOTKEY_ALL_SOLDIERS, mp.HOTKEY_GLOBAL_SELECT_ALL),
        ),
    ]
    for i in range(1, 8):
        slot = f"soldier{i}"
        label = keyboard_slot_label(slot)
        items.append(
            (
                f"classic.select_units.{slot}",
                _msgs(label, mp.HOTKEY_GLOBAL_SELECT_ALL),
            )
        )
    return items


def _move_square_label(x: int, y: int, no_collision: bool) -> list:
    if y > 0:
        parts = list(mp.HOTKEY_MOVE_NORTH)
    elif y < 0:
        parts = list(mp.HOTKEY_MOVE_SOUTH)
    elif x < 0:
        parts = list(mp.HOTKEY_MOVE_WEST)
    else:
        parts = list(mp.HOTKEY_MOVE_EAST)
    if abs(x) == 5 or abs(y) == 5:
        parts.extend(mp.HOTKEY_FIVE_SQUARES)
    if no_collision:
        parts.extend(mp.HOTKEY_NO_COLLISION)
    return parts


def _cycle_back(slot_msgs: list) -> list:
    return _msgs(slot_msgs, mp.HOTKEY_CYCLE_UNIT_BACK)


def _local_idle_select(slot_msgs: list) -> list:
    return _msgs(slot_msgs, mp.HOTKEY_LOCAL_SELECT_ALL, mp.HOTKEY_IDLE_UNITS)


def _global_idle_select(slot_msgs: list) -> list:
    return _msgs(slot_msgs, mp.HOTKEY_GLOBAL_SELECT_ALL, mp.HOTKEY_IDLE_UNITS)


def _classic_advanced_movement_catalog() -> Catalog:
    items: Catalog = []
    for x, y, no_collision in (
        (0, 5, False),
        (0, -5, False),
        (-5, 0, False),
        (5, 0, False),
        (0, 5, True),
        (0, -5, True),
        (-5, 0, True),
        (5, 0, True),
        (0, 1, True),
        (0, -1, True),
        (-1, 0, True),
        (1, 0, True),
    ):
        bid = f"classic.select_square.{x}.{y}"
        if no_collision:
            bid += ".no_collision"
        items.append((bid, _move_square_label(x, y, no_collision)))
    return items


def _classic_advanced_unit_catalog() -> Catalog:
    items: Catalog = [
        (
            "classic.select_unit.1",
            _msgs(mp.HOTKEY_CYCLE_UNIT, mp.HOTKEY_SCOPE_GLOBAL),
        ),
        (
            "classic.select_unit.-1",
            _msgs(mp.HOTKEY_CYCLE_UNIT_BACK, mp.HOTKEY_SCOPE_GLOBAL),
        ),
        (
            "classic.select_unit.-1.local",
            _msgs(mp.HOTKEY_LOCAL_UNIT, mp.HOTKEY_CYCLE_UNIT_BACK),
        ),
        (
            "classic.select_unit.1.building.even_if_no_menu",
            _msgs(
                mp.HOTKEY_SLOT_BUILDING,
                mp.HOTKEY_CYCLE_UNIT,
                mp.HOTKEY_INCLUDE_NO_MENU,
            ),
        ),
        (
            "classic.select_unit.1.building.idle",
            _msgs(
                mp.HOTKEY_SLOT_BUILDING,
                mp.HOTKEY_CYCLE_UNIT,
                mp.HOTKEY_IDLE_UNITS,
            ),
        ),
        (
            "classic.select_unit.1.worker.idle",
            _msgs(
                mp.HOTKEY_SLOT_WORKER,
                mp.HOTKEY_CYCLE_UNIT,
                mp.HOTKEY_IDLE_UNITS,
            ),
        ),
        (
            "classic.select_unit.-1.worker.idle",
            _msgs(
                mp.HOTKEY_SLOT_WORKER,
                mp.HOTKEY_CYCLE_UNIT_BACK,
                mp.HOTKEY_IDLE_UNITS,
            ),
        ),
        (
            "classic.select_unit.-1.building",
            _cycle_back(list(mp.HOTKEY_SLOT_BUILDING)),
        ),
        (
            "classic.select_unit.-1.worker",
            _cycle_back(list(mp.HOTKEY_SLOT_WORKER)),
        ),
        (
            "classic.select_units.local.worker.soldier1.soldier2.soldier3.soldier4."
            "soldier5.soldier6.soldier7",
            _msgs(mp.HOTKEY_WORKER_AND_ALL_SOLDIERS, mp.HOTKEY_LOCAL_SELECT_ALL),
        ),
        (
            "classic.select_units.worker.soldier1.soldier2.soldier3.soldier4."
            "soldier5.soldier6.soldier7",
            _msgs(mp.HOTKEY_WORKER_AND_ALL_SOLDIERS, mp.HOTKEY_GLOBAL_SELECT_ALL),
        ),
    ]
    for i in range(1, 8):
        slot = f"soldier{i}"
        label = keyboard_slot_label(slot)
        items.append((f"classic.select_unit.-1.{slot}", _cycle_back(label)))
        items.append((f"classic.select_units.{slot}.idle", _global_idle_select(label)))
        items.append(
            (f"classic.select_units.{slot}.local.idle", _local_idle_select(label))
        )
    items.append(
        (
            "classic.select_units.worker.idle",
            _global_idle_select(list(mp.HOTKEY_SLOT_WORKER)),
        )
    )
    items.append(
        (
            "classic.select_units.worker.local.idle",
            _local_idle_select(list(mp.HOTKEY_SLOT_WORKER)),
        )
    )
    return items


def _classic_advanced_catalog() -> Catalog:
    """classic 方案高级变体（五格移动、反向切换、空闲单位等）。"""
    items: Catalog = []
    items.extend(_classic_advanced_movement_catalog())
    items.extend(_classic_advanced_unit_catalog())
    return items


def _build_unit_catalog() -> Catalog:
    items: Catalog = []
    worker = keyboard_slot_label("worker")
    items.append(("unit.select_units.local.worker", _local_select(worker)))
    items.append(("unit.select_unit.1.worker", _cycle_unit(worker)))
    items.append(("unit.select_units.worker.local.idle", _local_idle_select(worker)))
    items.append(("unit.select_units.worker.idle", _global_idle_select(worker)))
    items.append(
        (
            "unit.select_unit.1.worker.idle",
            _msgs(worker, mp.HOTKEY_CYCLE_UNIT, mp.HOTKEY_IDLE_UNITS),
        )
    )
    items.append(
        (
            "unit.select_unit.-1.worker.idle",
            _msgs(worker, mp.HOTKEY_CYCLE_UNIT_BACK, mp.HOTKEY_IDLE_UNITS),
        )
    )
    for i in range(1, 9):
        slot = f"soldier{i}"
        label = keyboard_slot_label(slot)
        items.append((f"unit.select_units.local.{slot}", _local_select(label)))
        items.append((f"unit.select_unit.1.{slot}", _cycle_unit(label)))
        items.append((f"unit.select_units.{slot}.local.idle", _local_idle_select(label)))
        items.append((f"unit.select_units.{slot}.idle", _global_idle_select(label)))
    items.append(
        (
            "unit.select_units.local.SOLDIER",
            list(mp.HOTKEY_ALL_SOLDIERS_LOCAL_SELECT),
        )
    )
    items.extend(
        [
            ("unit.select_unit.1.local", _cycle_unit(list(mp.HOTKEY_LOCAL_UNIT))),
            ("unit.command_unit", list(mp.HOTKEY_COMMAND_UNIT)),
            ("unit.order_shortcut", list(mp.HOTKEY_ORDER_SHORTCUT)),
            ("unit.toggle_side_filter.1", list(mp.HOTKEY_TOGGLE_SIDE_FILTER)),
            ("unit.toggle_type_filter.1", list(mp.HOTKEY_TOGGLE_TYPE_FILTER)),
        ]
    )
    items.extend(_group_selection_catalog_items("unit"))
    items.extend(_group_store_catalog_items("unit"))
    items.extend(_group_map_catalog_items("unit"))
    return items


def _build_building_catalog() -> Catalog:
    items: Catalog = [
        (
            "building.select_unit.1.building.even_if_no_menu",
            _cycle_unit(list(mp.HOTKEY_GENERIC_BUILDING)),
        ),
    ]
    for i in range(1, 17):
        slot = f"building{i}"
        label = keyboard_slot_label(slot)
        items.append((f"building.select_unit.1.{slot}", _cycle_unit(label)))
    items.extend(
        [
            ("building.toggle_side_filter.1", list(mp.HOTKEY_TOGGLE_SIDE_FILTER)),
            ("building.toggle_type_filter.1", list(mp.HOTKEY_TOGGLE_TYPE_FILTER)),
            ("building.command_unit", list(mp.HOTKEY_COMMAND_BUILDING)),
        ]
    )
    items.extend(_group_selection_catalog_items("building"))
    items.extend(_group_store_catalog_items("building"))
    return items


def _build_command_catalog() -> Catalog:
    items: Catalog = [
        (
            "command.select_order.1.inactive_included",
            list(mp.HOTKEY_BROWSE_NEXT_ORDER),
        ),
        ("command.do_again", list(mp.HOTKEY_DO_AGAIN)),
        ("command.do_again.now", list(mp.HOTKEY_DO_AGAIN_NOW)),
    ]
    for i in range(1, 31):
        items.append(
            (
                f"command.select_order_index.{i}.inactive_included",
                list(mp.HOTKEY_ORDER_LABEL) + nb2msg(i),
            )
        )
    return items


def _build_skill_catalog() -> Catalog:
    return [
        (
            "skill.select_order.1.inactive_included",
            list(mp.HOTKEY_BROWSE_NEXT_SKILL),
        ),
        (
            "skill.select_order.-1.inactive_included",
            list(mp.HOTKEY_BROWSE_PREV_ORDER),
        ),
    ]


def _build_rpg_catalog() -> Catalog:
    items: Catalog = []
    for i in range(1, 10):
        items.append(
            (f"rpg.rpg_skill_{i}", list(mp.HOTKEY_SKILL_LABEL) + nb2msg(i))
        )
    items.append(("rpg.rpg_skill_0", list(mp.HOTKEY_SKILL_LABEL) + nb2msg(10)))
    items.append(("rpg.rpg_skill_10", list(mp.HOTKEY_SKILL_LABEL) + nb2msg(11)))
    items.append(("rpg.rpg_skill_11", list(mp.HOTKEY_SKILL_LABEL) + nb2msg(12)))
    items.extend(
        [
            ("rpg.rpg_skill_list", list(mp.HOTKEY_SKILL_LIST)),
            ("rpg.rpg_auto_attack", list(mp.HOTKEY_AUTO_ATTACK)),
            (
                "rpg.change_zoom_precision.1",
                list(mp.HOTKEY_ZOOM_PRECISION_INCREASE),
            ),
            (
                "rpg.change_zoom_precision.-1",
                list(mp.HOTKEY_ZOOM_PRECISION_DECREASE),
            ),
            ("rpg.get_zoom_precision", list(mp.HOTKEY_QUERY_ZOOM_PRECISION)),
        ]
    )
    return items


def _build_help_catalog() -> Catalog:
    return [
        ("help.help.1", list(mp.HOTKEY_HELP_NEXT)),
        ("help.help.-1", list(mp.HOTKEY_HELP_PREV)),
        ("help.say_time", list(mp.HOTKEY_SAY_TIME)),
        ("help.say", list(mp.HOTKEY_SAY)),
        ("help.toggle_tick", list(mp.HOTKEY_TOGGLE_TICK)),
        ("help.exit_overlay_mode", list(mp.HOTKEY_EXIT_HELP)),
    ]


def _build_map_catalog() -> Catalog:
    return [
        ("map.select_deposit.1.resource1", list(mp.HOTKEY_DEPOSIT_R1_NEXT)),
        ("map.select_deposit.-1.resource1", list(mp.HOTKEY_DEPOSIT_R1_PREV)),
        ("map.select_deposit.1.resource2", list(mp.HOTKEY_DEPOSIT_R2_NEXT)),
        ("map.select_deposit.-1.resource2", list(mp.HOTKEY_DEPOSIT_R2_PREV)),
        ("map.select_deposit.1.resource3", list(mp.HOTKEY_DEPOSIT_R3_NEXT)),
        ("map.select_deposit.-1.resource3", list(mp.HOTKEY_DEPOSIT_R3_PREV)),
        ("map.select_meadow.1", list(mp.HOTKEY_MEADOW_NEXT)),
        ("map.select_meadow.-1", list(mp.HOTKEY_MEADOW_PREV)),
        ("map.select_passage.1", list(mp.HOTKEY_PASSAGE_NEXT)),
        ("map.select_passage.-1", list(mp.HOTKEY_PASSAGE_PREV)),
        ("map.toggle_zoom", list(mp.HOTKEY_TOGGLE_ZOOM)),
        ("map.exit_overlay_mode", list(mp.HOTKEY_EXIT_MAP)),
    ]


def _build_diplomacy_catalog() -> Catalog:
    return [
        (
            "diplomacy.select_alliance_candidate.1",
            list(mp.HOTKEY_ALLIANCE_CANDIDATE),
        ),
        ("diplomacy.alliance_request", list(mp.HOTKEY_ALLIANCE_REQUEST)),
        ("diplomacy.alliance_accept", list(mp.HOTKEY_ALLIANCE_ACCEPT)),
        (
            "diplomacy.alliance_decline_or_cancel",
            list(mp.HOTKEY_ALLIANCE_DECLINE),
        ),
        ("diplomacy.exit_overlay_mode", list(mp.HOTKEY_EXIT_DIPLOMACY)),
    ]


def _build_classic_catalog() -> Catalog:
    """经典单文件热键（legacy_bindings.txt）主绑定目录。"""
    items: Catalog = [
        ("classic.resource_status.resource1", list(mp.HOTKEY_RESOURCE1_STATUS)),
        ("classic.resource_status.resource2", list(mp.HOTKEY_RESOURCE2_STATUS)),
        ("classic.resource_status.resource3", list(mp.HOTKEY_RESOURCE3_STATUS)),
        ("classic.population_status", list(mp.HOTKEY_POPULATION_STATUS)),
        ("classic.unit_attributes_screen", list(mp.HOTKEY_ATTRIBUTES_SCREEN)),
        ("classic.toggle_gear_screen", list(mp.HOTKEY_TOGGLE_GEAR_SCREEN)),
        ("classic.unit_hp_status", list(mp.HOTKEY_UNIT_HP_STATUS)),
        ("classic.examine", list(mp.HOTKEY_EXAMINE)),
        ("classic.unit_status", list(mp.HOTKEY_UNIT_STATUS)),
        ("classic.select_square.0.1", list(mp.HOTKEY_MOVE_NORTH)),
        ("classic.select_square.0.-1", list(mp.HOTKEY_MOVE_SOUTH)),
        ("classic.select_square.-1.0", list(mp.HOTKEY_MOVE_WEST)),
        ("classic.select_square.1.0", list(mp.HOTKEY_MOVE_EAST)),
        ("classic.select_scouted_square.1", list(mp.HOTKEY_SCOUTED_SQUARE_NEXT)),
        ("classic.select_scouted_square.-1", list(mp.HOTKEY_SCOUTED_SQUARE_PREV)),
        ("classic.select_conflict_square.1", list(mp.HOTKEY_CONFLICT_SQUARE_NEXT)),
        (
            "classic.select_conflict_square.-1",
            list(mp.HOTKEY_CONFLICT_SQUARE_PREV),
        ),
        ("classic.select_unknown_square.1", list(mp.HOTKEY_UNKNOWN_SQUARE_NEXT)),
        ("classic.select_unknown_square.-1", list(mp.HOTKEY_UNKNOWN_SQUARE_PREV)),
        ("classic.select_resource_square.1", list(mp.HOTKEY_RESOURCE_SQUARE_NEXT)),
        (
            "classic.select_resource_square.-1",
            list(mp.HOTKEY_RESOURCE_SQUARE_PREV),
        ),
        ("classic.toggle_zoom", list(mp.HOTKEY_TOGGLE_ZOOM)),
        ("classic.select_target.1", list(mp.HOTKEY_SELECT_TARGET_NEXT)),
        ("classic.select_target.-1", list(mp.HOTKEY_SELECT_TARGET_PREV)),
        ("classic.toggle_side_filter.1", list(mp.HOTKEY_TOGGLE_SIDE_FILTER)),
        ("classic.toggle_type_filter.1", list(mp.HOTKEY_TOGGLE_TYPE_FILTER)),
        (
            "classic.select_order.1.inactive_included",
            list(mp.HOTKEY_BROWSE_NEXT_ORDER),
        ),
        ("classic.order_shortcut", list(mp.HOTKEY_ORDER_SHORTCUT)),
        ("classic.validate", list(mp.HOTKEY_VALIDATE_COMMAND)),
        ("classic.default", list(mp.HOTKEY_DEFAULT_COMMAND)),
        ("classic.do_again", list(mp.HOTKEY_DO_AGAIN)),
        ("classic.do_again.now", list(mp.HOTKEY_DO_AGAIN_NOW)),
    ]
    worker = keyboard_slot_label("worker")
    items.append(("classic.select_units.local.worker", _local_select(worker)))
    items.append(("classic.select_unit.1.worker", _cycle_unit(worker)))
    for i in range(1, 8):
        slot = f"soldier{i}"
        label = keyboard_slot_label(slot)
        items.append((f"classic.select_units.local.{slot}", _local_select(label)))
        items.append((f"classic.select_unit.1.{slot}", _cycle_unit(label)))
    items.append(
        (
            "classic.select_units.local.soldier1.soldier2.soldier3.soldier4."
            "soldier5.soldier6.soldier7",
            list(mp.HOTKEY_ALL_SOLDIERS_LOCAL_SELECT),
        )
    )
    building = keyboard_slot_label("building")
    items.extend(
        [
            ("classic.select_unit.1.building", _cycle_unit(building)),
            ("classic.select_unit.1.local", _cycle_unit(list(mp.HOTKEY_LOCAL_UNIT))),
            ("classic.command_unit", list(mp.HOTKEY_COMMAND_UNIT)),
        ]
    )
    items.extend(_group_selection_catalog_items("classic"))
    items.extend(_group_store_catalog_items("classic"))
    items.extend(_group_map_catalog_items("classic"))
    items.extend(_classic_supplement_catalog())
    items.extend(_classic_advanced_catalog())
    items.extend(
        [
            ("classic.escape", list(mp.HOTKEY_CANCEL_COMMAND)),
            ("classic.help.1", list(mp.HOTKEY_HELP_NEXT)),
            ("classic.say_time", list(mp.HOTKEY_SAY_TIME)),
            ("classic.say", list(mp.HOTKEY_SAY)),
            ("classic.objectives.1", list(mp.HOTKEY_OBJECTIVES_NEXT)),
            ("classic.gamemenu", list(mp.HOTKEY_GAME_MENU)),
            ("classic.say_players", list(mp.HOTKEY_SAY_PLAYERS)),
            (
                "classic.select_alliance_candidate.1",
                list(mp.HOTKEY_ALLIANCE_CANDIDATE),
            ),
            ("classic.alliance_request", list(mp.HOTKEY_ALLIANCE_REQUEST)),
            ("classic.alliance_accept", list(mp.HOTKEY_ALLIANCE_ACCEPT)),
            (
                "classic.alliance_decline_or_cancel",
                list(mp.HOTKEY_ALLIANCE_DECLINE),
            ),
            ("classic.history_previous", list(mp.HOTKEY_HISTORY_PREV)),
            ("classic.volume", list(mp.HOTKEY_VOLUME_UP)),
            ("classic.volume.-1", list(mp.HOTKEY_VOLUME_DOWN)),
            ("classic.immersion", _visual_immersion()),
            ("classic.console", list(mp.HOTKEY_CONSOLE)),
            ("classic.toggle_music", list(mp.HOTKEY_TOGGLE_MUSIC)),
            ("classic.fullscreen", _visual_fullscreen()),
            ("classic.toggle_talking_clock", list(mp.HOTKEY_TOGGLE_TALKING_CLOCK)),
            ("classic.change_player", list(mp.HOTKEY_CHANGE_PLAYER)),
            ("classic.change_zoom_precision", list(mp.HOTKEY_CHANGE_ZOOM_PRECISION)),
        ]
    )
    return items


_LAYER_BUILDERS = {
    "unit": _build_unit_catalog,
    "building": _build_building_catalog,
    "command": _build_command_catalog,
    "skill": _build_skill_catalog,
    "rpg": _build_rpg_catalog,
    "help": _build_help_catalog,
    "map": _build_map_catalog,
    "diplomacy": _build_diplomacy_catalog,
}


def get_layer_catalog(layer: str) -> Catalog:
    if layer == "global":
        from .hotkey_editor import GLOBAL_PRIMARY_CATALOG

        return list(GLOBAL_PRIMARY_CATALOG)
    if layer == "classic":
        return _build_classic_catalog()
    builder = _LAYER_BUILDERS.get(layer)
    if builder is None:
        return []
    return builder()


def mapping_layers_for_current_scheme():
    """当前热键方案下，按键映射菜单应列出的层。"""
    from .clientgame.interface_modes import layered_hotkeys_enabled

    if layered_hotkeys_enabled():
        return LAYER_ORDER
    return CLASSIC_MAPPING_LAYERS


def label_for_binding_id(binding_id: str, layer: str) -> list:
    """任意 binding_id 的显示标签（主 catalog 或高级变体）。"""
    for bid, label in get_layer_catalog(layer):
        if bid == binding_id:
            return list(label)
    return variant_label_for_binding_id(binding_id, layer)


def variant_label_for_binding_id(binding_id: str, layer: str) -> list:
    """为不在主 catalog 中的 binding_id 生成标签。"""
    import re

    if not binding_id.startswith(layer + "."):
        return [binding_id]
    suffix = binding_id[len(layer) + 1 :]

    simple = {
        "history_stop": list(mp.HOTKEY_HISTORY_STOP),
        "history_stop_primary": list(mp.HOTKEY_HISTORY_STOP_PRIMARY),
        "history_stop_secondary": list(mp.HOTKEY_HISTORY_STOP_SECONDARY),
        "reload_parameters": list(mp.HOTKEY_RELOAD_PARAMETERS),
        "music_volume_up": list(mp.HOTKEY_MUSIC_VOLUME_UP),
        "music_volume_down": list(mp.HOTKEY_MUSIC_VOLUME_DOWN),
        "get_zoom_precision": list(mp.HOTKEY_QUERY_ZOOM_PRECISION),
        "change_zoom_precision": list(mp.HOTKEY_CHANGE_ZOOM_PRECISION),
        "change_zoom_precision.-1": list(mp.HOTKEY_ZOOM_PRECISION_DECREASE),
        "change_zoom_precision.1": list(mp.HOTKEY_ZOOM_PRECISION_INCREASE),
        "select_alliance_candidate.-1": list(mp.HOTKEY_ALLIANCE_CANDIDATE_PREV),
        "toggle_side_filter.-1": list(mp.HOTKEY_TOGGLE_SIDE_FILTER_BACK),
        "toggle_type_filter.-1": list(mp.HOTKEY_TOGGLE_TYPE_FILTER_BACK),
        "select_order.-1.inactive_included": list(mp.HOTKEY_BROWSE_PREV_ORDER),
        "select_order.1.inactive_only": list(mp.HOTKEY_ORDER_INACTIVE_ONLY),
        "select_order.-1.inactive_only": _msgs(
            mp.HOTKEY_BROWSE_PREV_ORDER, mp.HOTKEY_ORDER_INACTIVE_ONLY
        ),
        "do_again.now.queue_order": _msgs(
            mp.HOTKEY_DO_AGAIN_NOW, mp.HOTKEY_DO_AGAIN_QUEUE
        ),
        "select_units.SOLDIER": list(mp.HOTKEY_ALL_SOLDIERS),
        "select_units.worker.SOLDIER": _msgs(
            mp.HOTKEY_SLOT_WORKER, mp.HOTKEY_ALL_SOLDIERS
        ),
        "select_units.local.worker.SOLDIER": _msgs(
            mp.HOTKEY_WORKER_AND_ALL_SOLDIERS, mp.HOTKEY_LOCAL_SELECT_ALL
        ),
    }
    if suffix in simple:
        return simple[suffix]

    if suffix.endswith(".imperative.queue_order"):
        base = suffix[: -len(".imperative.queue_order")]
        if base == "validate":
            return _msgs(
                mp.HOTKEY_VALIDATE_COMMAND,
                mp.HOTKEY_VALIDATE_IMPERATIVE,
                mp.HOTKEY_ORDER_IN_QUEUE,
            )
        if base == "default":
            return _msgs(
                mp.HOTKEY_DEFAULT_COMMAND,
                mp.HOTKEY_VALIDATE_IMPERATIVE,
                mp.HOTKEY_ORDER_IN_QUEUE,
            )
    if suffix.endswith(".imperative"):
        base = suffix[: -len(".imperative")]
        if base == "validate":
            return _msgs(mp.HOTKEY_VALIDATE_COMMAND, mp.HOTKEY_VALIDATE_IMPERATIVE)
        if base == "default":
            return _msgs(mp.HOTKEY_DEFAULT_COMMAND, mp.HOTKEY_VALIDATE_IMPERATIVE)
    if suffix.endswith(".queue_order"):
        base = suffix[: -len(".queue_order")]
        if base == "validate":
            return _msgs(mp.HOTKEY_VALIDATE_COMMAND, mp.HOTKEY_VALIDATE_QUEUE)
        if base == "default":
            return _msgs(mp.HOTKEY_DEFAULT_COMMAND, mp.HOTKEY_ORDER_IN_QUEUE)

    m = re.fullmatch(r"select_square\.(-?\d+)\.(-?\d+)(?:\.no_collision)?", suffix)
    if m:
        x, y = int(m.group(1)), int(m.group(2))
        no_collision = suffix.endswith(".no_collision")
        return _move_square_label(x, y, no_collision)

    m = re.fullmatch(r"group\.(\d+)", suffix)
    if m:
        n = int(m.group(1))
        portions = {
            1: mp.HOTKEY_SELECT_ALL,
            2: mp.HOTKEY_SELECT_HALF,
            3: mp.HOTKEY_SELECT_THIRD,
            4: mp.HOTKEY_SELECT_QUARTER,
            5: mp.HOTKEY_SELECT_FIFTH,
        }
        portion = portions.get(n, mp.HOTKEY_SELECT_ALL)
        return _msgs(mp.HOTKEY_GROUP_ON_MAP, portion)

    m = re.fullmatch(r"select_unit\.-1\.(.+?)(?:\.idle)?", suffix)
    if m:
        slot = m.group(1)
        label = keyboard_slot_label(slot)
        if suffix.endswith(".idle"):
            return _msgs(label, mp.HOTKEY_CYCLE_UNIT_BACK, mp.HOTKEY_IDLE_UNITS)
        if slot == "building.even_if_no_menu" or slot.endswith(".even_if_no_menu"):
            base_slot = slot.replace(".even_if_no_menu", "")
            return _msgs(
                keyboard_slot_label(base_slot),
                mp.HOTKEY_CYCLE_UNIT_BACK,
                mp.HOTKEY_INCLUDE_NO_MENU,
            )
        return _cycle_back(label)

    if suffix == "select_unit.1":
        return _msgs(mp.HOTKEY_CYCLE_UNIT, mp.HOTKEY_SCOPE_GLOBAL)
    if suffix == "select_unit.-1":
        return _msgs(mp.HOTKEY_CYCLE_UNIT_BACK, mp.HOTKEY_SCOPE_GLOBAL)
    if suffix == "select_unit.-1.local":
        return _msgs(mp.HOTKEY_LOCAL_UNIT, mp.HOTKEY_CYCLE_UNIT_BACK)
    if suffix == "select_unit.1.worker.idle":
        return _msgs(
            mp.HOTKEY_SLOT_WORKER, mp.HOTKEY_CYCLE_UNIT, mp.HOTKEY_IDLE_UNITS
        )

    m = re.fullmatch(r"select_units\.(\w+)\.local\.idle", suffix)
    if m:
        return _local_idle_select(keyboard_slot_label(m.group(1)))
    m = re.fullmatch(r"select_units\.(\w+)\.idle", suffix)
    if m:
        return _global_idle_select(keyboard_slot_label(m.group(1)))
    m = re.fullmatch(r"select_units\.(\w+)", suffix)
    if m:
        slot = m.group(1)
        if slot == "worker":
            return _msgs(mp.HOTKEY_SLOT_WORKER, mp.HOTKEY_GLOBAL_SELECT_ALL)
        return _msgs(keyboard_slot_label(slot), mp.HOTKEY_GLOBAL_SELECT_ALL)

    if suffix == "default":
        return list(mp.HOTKEY_DEFAULT_COMMAND)

    return [binding_id]


def get_layer_variant_catalog(layer: str) -> Catalog:
    """bindings 文件中存在、但不在主 catalog 中的高级变体。"""
    from .hotkey_editor import parse_bindings_text, _read_bindings_source

    # rpg_bindings.txt 含大量与全局重复的键，高级变体仅保留主 catalog。
    if layer == "rpg":
        return []

    primary_ids = {bid for bid, _ in get_layer_catalog(layer)}
    text = _read_bindings_source(layer)
    if not text:
        return []
    seen: set = set()
    items: Catalog = []
    for entry in parse_bindings_text(text, layer):
        if entry.binding_id in primary_ids or entry.binding_id in seen:
            continue
        seen.add(entry.binding_id)
        items.append(
            (entry.binding_id, variant_label_for_binding_id(entry.binding_id, layer))
        )
    return items
