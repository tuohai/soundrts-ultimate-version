"""
装备栏界面模块
CTRL+V 打开；箭头键浏览；g 简介；Enter 装备；Shift+Enter 卸下；
Delete 确认丢弃；Shift+Delete 直接丢弃；Esc 退出。
显示内置武器/护甲及背包中的武器/护甲物品。
"""

from .. import msgparts as mp
from ..lib.bindings import Bindings
from ..lib.msgs import nb2msg
from ..clientmedia import voice
from ..definitions import style, rules


class EquipmentScreen:
    def __init__(self, parent):
        self.parent = parent

    def _get_unit(self):
        unit_id = getattr(self.parent, "_equipment_screen_unit_id", None)
        if unit_id is None:
            return None
        return self.parent.interface.dobjets.get(unit_id)

    def _get_inventory_items(self):
        u = self._get_unit()
        if u is None:
            return []
        inventory = getattr(u, "inventory", None)
        if not inventory:
            return []
        return list(inventory)

    @staticmethod
    def _item_title(item):
        type_name = getattr(item, "type_name", None)
        title = style.get(type_name, "title") if type_name else None
        if title:
            return title if isinstance(title, list) else [str(title)]
        return [type_name or "?"]

    @staticmethod
    def _type_title(type_name):
        if not type_name:
            return ["?"]
        title = style.get(type_name, "title")
        if title:
            return title if isinstance(title, list) else [str(title)]
        return [type_name]

    @staticmethod
    def _item_class(type_name):
        if not type_name:
            return None
        try:
            return rules.unit_class(type_name)
        except Exception:
            return None

    def _is_weapon_item(self, item):
        if getattr(item, "is_weapon_item", False):
            return True
        cls = self._item_class(getattr(item, "type_name", None))
        return bool(cls and getattr(cls, "equippable_as_weapon", 0))

    def _is_armor_item(self, item):
        if getattr(item, "is_armor_item", False):
            return True
        cls = self._item_class(getattr(item, "type_name", None))
        return bool(cls and getattr(cls, "equippable_as_armor", 0))

    def _is_weapon_from_inventory(self, weapon_name):
        u = self._get_unit()
        if u is None or u.model is None:
            return False
        return weapon_name in getattr(u.model, "_inventory_weapon_items", {})

    def _is_armor_from_inventory(self):
        u = self._get_unit()
        if u is None or u.model is None:
            return False
        return getattr(u.model, "_inventory_armor_item", None) is not None

    @staticmethod
    def _is_item_gear_type(type_name, gear_kind):
        """rules 中同名 class item 可装备物不应显示为内置武器/护甲。"""
        from ..worldunit.worldbase import Unit
        return Unit._is_item_gear_class(type_name, gear_kind)

    def _can_drop_entry(self, kind, data):
        """背包物品及已装备的武器/护甲可丢弃；传统内置装备不可丢弃。"""
        if kind in ("builtin_weapon", "builtin_armor"):
            return False
        if kind != "inventory":
            return False
        return getattr(data, "id", None) is not None

    def _drop_blocked_message(self, kind, data):
        return mp.CANNOT_DROP_BUILTIN_GEAR

    def _model(self):
        u = self._get_unit()
        if u is None:
            return None
        return u.model if u.model is not None else u

    def _can_equip_item_weapon(self):
        model = self._model()
        if model is None:
            return False
        checker = getattr(model, "can_equip_item_weapon", None)
        return checker() if checker else True

    def _can_equip_item_armor(self):
        model = self._model()
        if model is None:
            return False
        checker = getattr(model, "can_equip_item_armor", None)
        return checker() if checker else True

    def _can_switch_to_weapon(self, weapon_name):
        model = self._model()
        if model is None:
            return False
        current_weapon = getattr(model, "current_weapon", None)
        checker = getattr(model, "_can_switch_between_weapons", None)
        if not checker:
            return True
        if not current_weapon:
            return True
        return checker(current_weapon, weapon_name)

    def _get_equipment_entries(self):
        """返回 (kind, data) 列表。kind: builtin_weapon / builtin_armor / inventory。"""
        u = self._get_unit()
        if u is None:
            return []

        entries = []

        weapons = getattr(u, "weapons", None) or []
        if isinstance(weapons, str):
            weapons = [weapons]
        for weapon_name in weapons:
            if not weapon_name or self._is_weapon_from_inventory(weapon_name):
                continue
            if self._is_item_gear_type(weapon_name, "weapon"):
                continue
            entries.append(("builtin_weapon", weapon_name))

        armor = getattr(u, "armor", None)
        if armor and not self._is_armor_from_inventory():
            if isinstance(armor, (list, tuple)):
                for armor_name in armor:
                    if armor_name and not self._is_item_gear_type(armor_name, "armor"):
                        entries.append(("builtin_armor", armor_name))
            elif not self._is_item_gear_type(armor, "armor"):
                entries.append(("builtin_armor", armor))

        seen = set()
        for item in self._get_inventory_items():
            if self._is_weapon_item(item) or self._is_armor_item(item):
                entries.append(("inventory", item))
                seen.add(id(item))
        if u.model is not None:
            for item in getattr(u.model, "_inventory_weapon_items", {}).values():
                if id(item) not in seen:
                    entries.append(("inventory", item))
                    seen.add(id(item))
            armor_item = getattr(u.model, "_inventory_armor_item", None)
            if armor_item is not None and id(armor_item) not in seen:
                entries.append(("inventory", armor_item))

        return entries

    def _current_weapon_name(self, u):
        """与属性界面一致：优先 current_weapon，否则回退到 weapons[0]。"""
        current = getattr(u, "current_weapon", None)
        if not current and u.model is not None:
            current = getattr(u.model, "current_weapon", None)
        if not current:
            weapons = getattr(u, "weapons", None) or []
            if isinstance(weapons, str):
                weapons = [weapons]
            if weapons:
                current = weapons[0]
        return current

    def _is_equipped_entry(self, kind, data):
        u = self._get_unit()
        if u is None:
            return False
        if kind == "builtin_weapon":
            model = u.model if u.model is not None else u
            return getattr(model, "current_weapon", None) == data
        if kind == "builtin_armor":
            model = u.model
            if model is not None and getattr(model, "_is_builtin_armor_applied", None):
                return model._is_builtin_armor_applied()
            return data == getattr(u, "armor", None)
        if kind == "inventory":
            if u.model is None:
                return False
            model = u.model
            if getattr(model, "is_inventory_weapon_item", None):
                if model.is_inventory_weapon_item(data):
                    return True
            if getattr(model, "is_inventory_armor_item", None):
                if model.is_inventory_armor_item(data):
                    return True
        return False

    def _send_equipment_order(self, order_keyword, item_id):
        from ..clientgame.game_unit_control import send_inventory_order
        send_inventory_order(
            self.parent.interface, order_keyword, item_id,
            unit_id=getattr(self.parent, "_equipment_screen_unit_id", None),
        )

    def _send_gear_order(self, order_keyword, *args):
        from ..clientgame.game_unit_control import send_gear_order
        send_gear_order(
            self.parent.interface, order_keyword,
            getattr(self.parent, "_equipment_screen_unit_id", None),
            *args,
        )

    def _setup_bindings(self):
        bindings_str = (
            "LEFT: _equipment_prev\n"
            "RIGHT: _equipment_next\n"
            "UP: _equipment_prev\n"
            "DOWN: _equipment_next\n"
            "g: _equipment_intro\n"
            "G: _equipment_intro\n"
            "RETURN: _equipment_use\n"
            "KP_ENTER: _equipment_use\n"
            "SHIFT RETURN: _equipment_unequip\n"
            "SHIFT KP_ENTER: _equipment_unequip\n"
            "DELETE: _equipment_drop_confirm\n"
            "SHIFT DELETE: _equipment_drop_now\n"
            "ESCAPE: _equipment_escape\n"
            "SHIFT V: toggle_gear_screen\n"
        )
        self.parent.interface._bindings = Bindings()
        self.parent.interface._bindings.load(bindings_str, self.parent.interface)

    def cmd_unit_equipment_screen(self):
        """CTRL+V：打开当前选中单位的装备栏。"""
        interface = self.parent.interface
        if getattr(self.parent, "_in_equipment_screen", False):
            return
        if getattr(self.parent, "_in_inventory_screen", False):
            voice.item(mp.BEEP)
            return
        if getattr(self.parent, "_in_attributes_screen", False):
            self.parent.key_bindings.cmd__exit_attributes_screen()
        if not interface.group:
            voice.item(mp.NO_UNIT_CONTROLLED)
            return
        if len(interface.group) != 1:
            voice.item(str(len(interface.group)) + mp.UNITS_SELECTED)
            return
        unit_id = interface.group[0]
        u = interface.dobjets.get(unit_id)
        if u is None:
            voice.item(mp.NO_UNIT_CONTROLLED)
            return
        self.parent._equipment_screen_unit_id = unit_id
        entries = self._get_equipment_entries()
        if not entries:
            voice.item(mp.EMPTY_EQUIPMENT)
            self.parent._equipment_screen_unit_id = None
            return
        self.parent._equipment_item_index = 0
        self.parent._equipment_confirm_drop = False
        self.parent._in_equipment_screen = True
        if self.parent._original_bindings is None:
            self.parent._original_bindings = interface._bindings
        self._setup_bindings()
        voice.item(mp.EQUIPMENT_BAR + mp.COMMA + mp.PRESS_ESC_TO_EXIT)
        self._display_current_entry()

    def _entry_title(self, kind, data):
        if kind == "inventory":
            return self._item_title(data)[:]
        return self._type_title(data)[:]

    def _display_current_entry(self):
        entries = self._get_equipment_entries()
        if not entries:
            self._exit_equipment_screen()
            voice.item(mp.EMPTY_EQUIPMENT)
            return
        idx = self.parent._equipment_item_index
        if idx >= len(entries):
            idx = len(entries) - 1
            self.parent._equipment_item_index = idx
        kind, data = entries[idx]
        msg = self._entry_title(kind, data)[:]
        if self._is_equipped_entry(kind, data):
            msg += mp.EQUIPPED_MARK
        if kind == "builtin_weapon":
            msg += mp.COMMA + mp.BUILTIN_WEAPON
        elif kind == "builtin_armor":
            msg += mp.COMMA + mp.BUILTIN_ARMOR
        msg += mp.COMMA + nb2msg(idx + 1) + ["共"] + nb2msg(len(entries))
        voice.item(msg)

    def _current_entry(self):
        entries = self._get_equipment_entries()
        if not entries:
            return None
        idx = self.parent._equipment_item_index
        if idx < 0 or idx >= len(entries):
            return None
        return entries[idx]

    def cmd__equipment_prev(self):
        entries = self._get_equipment_entries()
        if len(entries) <= 1:
            voice.item(mp.BEEP)
            return
        if self.parent._equipment_item_index > 0:
            self.parent._equipment_item_index -= 1
        else:
            self.parent._equipment_item_index = len(entries) - 1
        self.parent._equipment_confirm_drop = False
        self._display_current_entry()

    def cmd__equipment_next(self):
        entries = self._get_equipment_entries()
        if len(entries) <= 1:
            voice.item(mp.BEEP)
            return
        if self.parent._equipment_item_index < len(entries) - 1:
            self.parent._equipment_item_index += 1
        else:
            self.parent._equipment_item_index = 0
        self.parent._equipment_confirm_drop = False
        self._display_current_entry()

    def cmd__equipment_intro(self):
        if self.parent._equipment_confirm_drop:
            voice.item(mp.BEEP)
            return
        entry = self._current_entry()
        if entry is None:
            voice.item(mp.BEEP)
            return
        kind, data = entry
        if kind == "inventory":
            type_name = getattr(data, "type_name", None)
        else:
            type_name = data
        intro = style.get(type_name, "intro") if type_name else None
        if intro:
            voice.item(intro if isinstance(intro, list) else [str(intro)])
        else:
            voice.item(mp.NO_INTRO)

    def cmd__equipment_use(self):
        if self.parent._equipment_confirm_drop:
            self.cmd__equipment_drop_execute()
            return
        entry = self._current_entry()
        if entry is None:
            voice.item(mp.BEEP)
            return
        kind, data = entry
        if kind == "builtin_weapon":
            if self._is_equipped_entry(kind, data):
                voice.item(mp.CANNOT_MODIFY_BUILTIN_GEAR)
                return
            if not self._can_switch_to_weapon(data):
                voice.item(mp.CANNOT_SWITCH_MIXED_GEAR)
                return
            self._send_gear_order("switch_to_weapon", data)
            voice.item(self._type_title(data) + mp.EQUIPPED_WEAPON)
            return
        if kind == "builtin_armor":
            if self._is_equipped_entry(kind, data):
                voice.item(mp.CANNOT_MODIFY_BUILTIN_GEAR)
                return
            self._send_gear_order("equip_builtin_armor")
            voice.item(self._type_title(data) + mp.EQUIPPED_ARMOR)
            return
        if kind != "inventory":
            voice.item(mp.CANNOT_MODIFY_BUILTIN_GEAR)
            return
        item = data
        item_id = getattr(item, "id", None)
        if item_id is None:
            voice.item(mp.BEEP)
            return
        if self._is_weapon_item(item):
            if not self._can_equip_item_weapon():
                voice.item(mp.CANNOT_EQUIP_ITEM_WITH_BUILTIN)
                return
            self._send_equipment_order("equip_weapon", item_id)
            voice.item(self._item_title(item) + mp.EQUIPPED_WEAPON)
        elif self._is_armor_item(item):
            if not self._can_equip_item_armor():
                voice.item(mp.CANNOT_EQUIP_ITEM_WITH_BUILTIN)
                return
            self._send_equipment_order("equip_armor", item_id)
            voice.item(self._item_title(item) + mp.EQUIPPED_ARMOR)
        else:
            voice.item(mp.CANNOT_USE_ITEM)

    def cmd__equipment_unequip(self):
        if self.parent._equipment_confirm_drop:
            voice.item(mp.BEEP)
            return
        entry = self._current_entry()
        if entry is None:
            voice.item(mp.BEEP)
            return
        kind, data = entry
        if kind != "inventory":
            voice.item(mp.CANNOT_MODIFY_BUILTIN_GEAR)
            return
        item = data
        if not self._is_equipped_entry(kind, item):
            voice.item(mp.CANNOT_UNEQUIP)
            return
        item_id = getattr(item, "id", None)
        if item_id is None:
            voice.item(mp.BEEP)
            return
        if self._is_weapon_item(item):
            self._send_equipment_order("unequip_weapon", item_id)
            voice.item(self._item_title(item) + mp.UNEQUIPPED_WEAPON)
        elif self._is_armor_item(item):
            self._send_equipment_order("unequip_armor", item_id)
            voice.item(self._item_title(item) + mp.UNEQUIPPED_ARMOR)
        else:
            voice.item(mp.CANNOT_UNEQUIP)

    def cmd__equipment_drop_confirm(self):
        entry = self._current_entry()
        if entry is None:
            voice.item(mp.BEEP)
            return
        kind, data = entry
        if not self._can_drop_entry(kind, data):
            self.parent._equipment_confirm_drop = False
            voice.item(self._drop_blocked_message(kind, data))
            return
        self.parent._equipment_confirm_drop = True
        voice.item(
            mp.CONFIRM_DROP + self._entry_title(kind, data) + mp.CONFIRM_DROP_HINT
        )

    def cmd__equipment_drop_now(self):
        entry = self._current_entry()
        if entry is None:
            voice.item(mp.BEEP)
            return
        kind, data = entry
        if not self._can_drop_entry(kind, data):
            self.parent._equipment_confirm_drop = False
            voice.item(self._drop_blocked_message(kind, data))
            return
        self.parent._equipment_confirm_drop = False
        self.cmd__equipment_drop_execute()

    def cmd__equipment_drop_execute(self):
        entry = self._current_entry()
        if entry is None:
            voice.item(mp.BEEP)
            self.parent._equipment_confirm_drop = False
            return
        kind, data = entry
        if not self._can_drop_entry(kind, data):
            voice.item(self._drop_blocked_message(kind, data))
            self.parent._equipment_confirm_drop = False
            return
        item = data
        item_id = getattr(item, "id", None)
        if item_id is None:
            voice.item(mp.BEEP)
            self.parent._equipment_confirm_drop = False
            return
        title = self._item_title(item)
        self._send_equipment_order("drop", item_id)
        self.parent._equipment_confirm_drop = False
        voice.item(title + mp.DROPPED_ITEM)
        entries = self._get_equipment_entries()
        if not entries:
            self._exit_equipment_screen()
        elif self.parent._equipment_item_index >= len(entries):
            self.parent._equipment_item_index = max(0, len(entries) - 1)
            self._display_current_entry()

    def cmd__equipment_escape(self):
        if self.parent._equipment_confirm_drop:
            self.parent._equipment_confirm_drop = False
            voice.item(mp.DROP_CANCELLED)
            return
        self._exit_equipment_screen()

    def _exit_equipment_screen(self):
        self.parent._in_equipment_screen = False
        self.parent._equipment_confirm_drop = False
        self.parent._equipment_screen_unit_id = None
        voice.item(mp.EXITING_ATTRIBUTES_SCREEN)
        if self.parent._original_bindings is not None:
            from ..clientgame.interface_modes import restore_active_bindings
            restore_active_bindings(self.parent.interface)
            self.parent._original_bindings = None

    def _process_keyboard_event(self, e):
        if not getattr(self.parent, "_in_equipment_screen", False):
            return False
        try:
            return self.parent.interface._bindings.process_keydown_event(e)
        except Exception:
            return False
