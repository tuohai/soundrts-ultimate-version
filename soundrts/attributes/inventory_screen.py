"""
背包（库存）界面模块
SHIFT+V 打开；箭头键浏览；g 简介；Enter 使用/装备；Shift+Enter 卸下；
Delete 确认丢弃；Shift+Delete 直接丢弃；Esc 退出。
"""

from .. import msgparts as mp
from ..lib.bindings import Bindings
from ..lib.msgs import nb2msg
from ..clientmedia import voice
from ..definitions import style, rules


class InventoryScreen:
    def __init__(self, parent):
        self.parent = parent

    def _get_unit(self):
        unit_id = getattr(self.parent, "_inventory_screen_unit_id", None)
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

    def _is_consumable_item(self, item):
        if self._is_weapon_item(item) or self._is_armor_item(item):
            return False
        if getattr(item, "is_consumable_item", False):
            return True
        cls = self._item_class(getattr(item, "type_name", None))
        if cls is None:
            return False
        rewards = getattr(cls, "resource_rewards", None) or ()
        return bool(
            getattr(cls, "use_effect", None)
            or getattr(cls, "skills", None)
            or getattr(cls, "buffs", None)
            or (getattr(cls, "use_square", None) and any(r > 0 for r in rewards))
        )

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

    def _is_equipped(self, item):
        model = self._model()
        if model is None:
            return False
        if getattr(model, "is_inventory_weapon_item", None):
            if model.is_inventory_weapon_item(item):
                return True
        if getattr(model, "is_inventory_armor_item", None):
            if model.is_inventory_armor_item(item):
                return True
        return False

    def _send_inventory_order(self, order_keyword, item_id):
        from ..clientgame.game_unit_control import send_inventory_order
        send_inventory_order(self.parent.interface, order_keyword, item_id)

    def _setup_bindings(self):
        bindings_str = (
            "LEFT: _inventory_prev\n"
            "RIGHT: _inventory_next\n"
            "UP: _inventory_prev\n"
            "DOWN: _inventory_next\n"
            "g: _inventory_intro\n"
            "G: _inventory_intro\n"
            "RETURN: _inventory_use\n"
            "KP_ENTER: _inventory_use\n"
            "SHIFT RETURN: _inventory_unequip\n"
            "SHIFT KP_ENTER: _inventory_unequip\n"
            "DELETE: _inventory_drop_confirm\n"
            "SHIFT DELETE: _inventory_drop_now\n"
            "ESCAPE: _inventory_escape\n"
            "SHIFT V: toggle_gear_screen\n"
        )
        self.parent.interface._bindings = Bindings()
        self.parent.interface._bindings.load(bindings_str, self.parent.interface)

    def cmd_unit_inventory_screen(self):
        """SHIFT+V：打开当前选中单位的背包。"""
        interface = self.parent.interface
        if getattr(self.parent, "_in_inventory_screen", False):
            return
        if getattr(self.parent, "_in_equipment_screen", False):
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
        inventory = getattr(u, "inventory", None) or []
        if not inventory:
            voice.item(mp.EMPTY_BACKPACK)
            return
        self.parent._inventory_screen_unit_id = unit_id
        self.parent._inventory_item_index = 0
        self.parent._inventory_confirm_drop = False
        self.parent._in_inventory_screen = True
        if self.parent._original_bindings is None:
            self.parent._original_bindings = interface._bindings
        self._setup_bindings()
        voice.item(mp.BACKPACK + mp.COMMA + mp.PRESS_ESC_TO_EXIT)
        self._display_current_item()

    def _display_current_item(self):
        items = self._get_inventory_items()
        if not items:
            self._exit_inventory_screen()
            voice.item(mp.EMPTY_BACKPACK)
            return
        idx = self.parent._inventory_item_index
        if idx >= len(items):
            idx = len(items) - 1
            self.parent._inventory_item_index = idx
        item = items[idx]
        msg = self._item_title(item)[:]
        if self._is_equipped(item):
            msg += mp.EQUIPPED_MARK
        msg += mp.COMMA + nb2msg(idx + 1) + ["共"] + nb2msg(len(items))
        voice.item(msg)

    def _current_item(self):
        items = self._get_inventory_items()
        if not items:
            return None
        idx = self.parent._inventory_item_index
        if idx < 0 or idx >= len(items):
            return None
        return items[idx]

    def cmd__inventory_prev(self):
        items = self._get_inventory_items()
        if len(items) <= 1:
            voice.item(mp.BEEP)
            return
        if self.parent._inventory_item_index > 0:
            self.parent._inventory_item_index -= 1
        else:
            self.parent._inventory_item_index = len(items) - 1
        self.parent._inventory_confirm_drop = False
        self._display_current_item()

    def cmd__inventory_next(self):
        items = self._get_inventory_items()
        if len(items) <= 1:
            voice.item(mp.BEEP)
            return
        if self.parent._inventory_item_index < len(items) - 1:
            self.parent._inventory_item_index += 1
        else:
            self.parent._inventory_item_index = 0
        self.parent._inventory_confirm_drop = False
        self._display_current_item()

    def cmd__inventory_intro(self):
        if self.parent._inventory_confirm_drop:
            voice.item(mp.BEEP)
            return
        item = self._current_item()
        if item is None:
            voice.item(mp.BEEP)
            return
        type_name = getattr(item, "type_name", None)
        intro = style.get(type_name, "intro") if type_name else None
        if intro:
            voice.item(intro if isinstance(intro, list) else [str(intro)])
        else:
            voice.item(mp.NO_INTRO)

    def cmd__inventory_use(self):
        if self.parent._inventory_confirm_drop:
            self.cmd__inventory_drop_execute()
            return
        item = self._current_item()
        if item is None:
            voice.item(mp.BEEP)
            return
        item_id = getattr(item, "id", None)
        if item_id is None:
            voice.item(mp.BEEP)
            return
        if self._is_weapon_item(item):
            if not self._can_equip_item_weapon():
                voice.item(mp.CANNOT_EQUIP_ITEM_WITH_BUILTIN)
                return
            self._send_inventory_order("equip_weapon", item_id)
            voice.item(self._item_title(item) + mp.EQUIPPED_WEAPON)
        elif self._is_armor_item(item):
            if not self._can_equip_item_armor():
                voice.item(mp.CANNOT_EQUIP_ITEM_WITH_BUILTIN)
                return
            self._send_inventory_order("equip_armor", item_id)
            voice.item(self._item_title(item) + mp.EQUIPPED_ARMOR)
        elif self._is_consumable_item(item):
            self._send_inventory_order("use_item", item_id)
        else:
            voice.item(mp.CANNOT_USE_ITEM)

    def cmd__inventory_unequip(self):
        if self.parent._inventory_confirm_drop:
            voice.item(mp.BEEP)
            return
        item = self._current_item()
        if item is None or not self._is_equipped(item):
            voice.item(mp.CANNOT_UNEQUIP)
            return
        item_id = getattr(item, "id", None)
        if item_id is None:
            voice.item(mp.BEEP)
            return
        if self._is_weapon_item(item):
            self._send_inventory_order("unequip_weapon", item_id)
            voice.item(self._item_title(item) + mp.UNEQUIPPED_WEAPON)
        elif self._is_armor_item(item):
            self._send_inventory_order("unequip_armor", item_id)
            voice.item(self._item_title(item) + mp.UNEQUIPPED_ARMOR)
        else:
            voice.item(mp.CANNOT_UNEQUIP)

    def cmd__inventory_drop_confirm(self):
        item = self._current_item()
        if item is None:
            voice.item(mp.BEEP)
            return
        self.parent._inventory_confirm_drop = True
        voice.item(
            mp.CONFIRM_DROP + self._item_title(item) + mp.CONFIRM_DROP_HINT
        )

    def cmd__inventory_drop_now(self):
        self.parent._inventory_confirm_drop = False
        self.cmd__inventory_drop_execute()

    def cmd__inventory_drop_execute(self):
        item = self._current_item()
        if item is None:
            voice.item(mp.BEEP)
            self.parent._inventory_confirm_drop = False
            return
        item_id = getattr(item, "id", None)
        if item_id is None:
            voice.item(mp.BEEP)
            self.parent._inventory_confirm_drop = False
            return
        title = self._item_title(item)
        self._send_inventory_order("drop", item_id)
        self.parent._inventory_confirm_drop = False
        voice.item(title + mp.DROPPED_ITEM)
        items = self._get_inventory_items()
        if not items:
            self._exit_inventory_screen()
        elif self.parent._inventory_item_index >= len(items):
            self.parent._inventory_item_index = max(0, len(items) - 1)
            self._display_current_item()

    def cmd__inventory_escape(self):
        if self.parent._inventory_confirm_drop:
            self.parent._inventory_confirm_drop = False
            voice.item(mp.DROP_CANCELLED)
            return
        self._exit_inventory_screen()

    def _exit_inventory_screen(self):
        self.parent._in_inventory_screen = False
        self.parent._inventory_confirm_drop = False
        self.parent._inventory_screen_unit_id = None
        voice.item(mp.EXITING_ATTRIBUTES_SCREEN)
        if self.parent._original_bindings is not None:
            from ..clientgame.interface_modes import restore_active_bindings
            restore_active_bindings(self.parent.interface)
            self.parent._original_bindings = None

    def _process_keyboard_event(self, e):
        if not getattr(self.parent, "_in_inventory_screen", False):
            return False
        try:
            return self.parent.interface._bindings.process_keydown_event(e)
        except Exception:
            return False
