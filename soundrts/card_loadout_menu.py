"""战前卡牌选择菜单（第三期，仅 TrainingMenu 调用）。"""



from __future__ import annotations



from typing import List, Optional



from . import msgparts as mp

from .achievements import achievements_enabled, load_unlock_state

from .achievements_menu import resolve_training_faction

from .card_loadout import (
    available_charges,
    card_loadout_label,
    list_loadout_candidates,
    loadout_available,
    validate_loadout,
)

from .clientmedia import voice

from .clientmenu import CLOSE_MENU, Menu

from .faction_progress import achievements_per_faction_enabled, set_view_faction

from .lib.msgs import nb2msg

from .lib.resource import res

from .titles import get_loadout_slots



_STOP = object()

_ABORT = object()





def select_card_loadout(faction: Optional[str] = None) -> List[str]:

    """Blocking menu flow; returns validated card ids (may be empty)."""

    res.load_rules_and_ai()

    if not achievements_enabled():

        return []

    faction = resolve_training_faction(faction)
    if faction is None:
        return []

    set_view_faction(faction)

    if not loadout_available(faction):
        return []

    state = load_unlock_state(faction)
    medals = int(state.get("medals", 0))
    slots = get_loadout_slots(medals, faction)
    if not list_loadout_candidates(state, medals, faction):
        voice.menu(mp.LOADOUT_NO_CARDS)
        return []

    selected: List[str] = []

    for slot_index in range(1, slots + 1):

        picked = _pick_slot_menu(slot_index, state, medals, selected, faction)

        if picked is _ABORT:

            return validate_loadout(selected, state, faction)

        if picked is _STOP:

            break

        if picked:

            selected.append(picked)

    return validate_loadout(selected, state, faction)





def _pick_slot_menu(slot_index, state, medals, selected, faction) -> object | str | None:

    result: dict = {"card_id": None}



    def pick(card_id):

        def _action():

            result["card_id"] = card_id

        return _action



    def skip_slot():

        pass



    def start_now():

        result["card_id"] = _STOP



    def cancel_loadout():

        result["card_id"] = _ABORT



    menu = Menu(

        mp.LOADOUT_SELECT_SLOT + nb2msg(slot_index) + mp.LOADOUT_SLOT_SUFFIX,

        menu_type="submenu",

    )

    for card_id in list_loadout_candidates(state, medals, faction):

        if available_charges(state, medals, card_id, selected, faction) <= 0:

            continue

        menu.append(

            card_loadout_label(card_id, state, medals, selected, faction),

            pick(card_id),

        )

    menu.append(mp.LOADOUT_SKIP_SLOT, skip_slot)

    menu.append(mp.LOADOUT_START_NOW, start_now)

    menu.append(mp.CANCEL, cancel_loadout)

    menu.run()



    value = result["card_id"]

    if value is _STOP:

        return _STOP

    return value


