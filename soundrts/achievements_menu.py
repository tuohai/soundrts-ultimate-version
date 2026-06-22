"""主菜单：成就与军械库（第二期，只读浏览）。"""

from . import msgparts as mp
from .achievements import (
    achievement_requirement_msgs,
    achievements_enabled,
    get_achievement_defs,
    get_achievement_order,
    load_unlock_state,
)
from .card_loadout import card_armory_explanation
from .cards import get_card, get_card_order
from .clientmenu import CLOSE_MENU, Menu
from .definitions import rules
from .faction_progress import (
    achievements_per_faction_enabled,
    definition_matches_faction,
    faction_title_msgs,
    normalize_faction_key,
    select_faction_menu,
    set_view_faction,
)
from .lib.msgs import nb2msg
from .lib.resource import res
from .meta_progress import (
    META_MENU_KEY,
    count_factions_achievement_id_contains,
    count_factions_with_any_progress,
    load_faction_snapshots,
    load_meta_state,
    meta_enabled,
)
from .titles import (
    get_current_rank,
    get_loadout_slots,
    get_next_rank,
    get_title,
    medals_until_next_rank,
    rank_at_least,
)


def _achievement_label(defn, unlocked_entry):
    title = list(defn.title) if defn.title else [defn.id]
    if unlocked_entry:
        return title + mp.COMMA + mp.ACHIEVEMENT_STATUS_UNLOCKED
    return title + mp.COMMA + mp.ACHIEVEMENT_STATUS_LOCKED


def build_achievement_menu_entries(faction=None):
    """返回 [(label_msgs, unlocked_bool, explanation_msgs), ...] — 便于测试。"""
    defs = get_achievement_defs()
    order = get_achievement_order()
    state = load_unlock_state(faction)
    unlocked = state.get("unlocked", {})
    entries = []
    for aid in order:
        defn = defs.get(aid)
        if defn is None:
            continue
        if defn.scope == "meta":
            continue
        if not definition_matches_faction(defn.faction, faction, defn.scope):
            continue
        is_unlocked = aid in unlocked
        explanation = [] if is_unlocked else achievement_requirement_msgs(defn)
        entries.append((_achievement_label(defn, unlocked.get(aid)), is_unlocked, explanation))
    return entries


def build_meta_achievement_menu_entries():
    """Cross-faction meta achievements for _meta.json progress."""
    defs = get_achievement_defs()
    order = get_achievement_order()
    state = load_meta_state()
    unlocked = state.get("unlocked", {})
    entries = []
    for aid in order:
        defn = defs.get(aid)
        if defn is None or defn.scope != "meta":
            continue
        is_unlocked = aid in unlocked
        explanation = [] if is_unlocked else achievement_requirement_msgs(defn)
        entries.append((_achievement_label(defn, unlocked.get(aid)), is_unlocked, explanation))
    return entries


def build_meta_armory_menu_entries():
    state = load_meta_state()
    medals = int(state.get("medals", 0))
    honors = state.get("honors", [])
    entries = []
    snapshots = load_faction_snapshots()
    active = count_factions_with_any_progress(snapshots)
    total = len(rules.factions)
    entries.append(
        (
            mp.META_PROGRESS
            + mp.COMMA
            + mp.ACHIEVEMENT_AT_LEAST
            + nb2msg(active)
            + mp.SCORE_OUT_OF
            + nb2msg(total)
            + list(mp.META_FACTIONS),
            "summary",
            [],
        )
    )
    map_done = count_factions_achievement_id_contains(snapshots, "_map_")
    entries.append(
        (
            mp.META_MAP_MILESTONE
            + mp.COMMA
            + nb2msg(map_done)
            + mp.SCORE_OUT_OF
            + nb2msg(total)
            + list(mp.META_FACTIONS),
            "maps",
            [],
        )
    )
    entries.append((mp.ARMORY_MEDALS + nb2msg(medals), "medals", []))
    for honor_id in honors:
        honor = get_title(honor_id)
        if honor and honor.title:
            entries.append((list(honor.title), honor_id, []))
    return entries


def select_faction_or_meta_menu(caption_msgs=None):
    """Pick a faction, meta progress hub, or cancel."""
    factions = rules.factions
    if not factions:
        return None
    if len(factions) == 1 and not meta_enabled():
        return factions[0]

    picked = {"choice": None}

    def choose_faction(faction_id):
        def _action():
            picked["choice"] = faction_id
        return _action

    def choose_meta():
        def _action():
            picked["choice"] = META_MENU_KEY
        return _action

    menu = Menu(caption_msgs or mp.ACHIEVEMENTS, menu_type="submenu")
    if meta_enabled():
        menu.append(mp.META_PROGRESS, choose_meta())
    for faction_id in factions:
        menu.append(faction_title_msgs(faction_id), choose_faction(faction_id))
    menu.append(mp.CANCEL, CLOSE_MENU)
    menu.run()
    return picked["choice"]


def meta_achievements_list_menu():
    entries = build_meta_achievement_menu_entries()
    menu = Menu(mp.META_PROGRESS, menu_type="submenu")
    if not entries:
        menu.append(mp.ACHIEVEMENTS_EMPTY, None)
    else:
        for label, _, explanation in entries:
            menu.append(label, None, explanation)
    menu.append(mp.BACK, CLOSE_MENU)
    menu.run()


def meta_armory_menu():
    entries = build_meta_armory_menu_entries()
    menu = Menu(mp.ARMORY, menu_type="submenu")
    if not entries:
        menu.append(mp.ARMORY_EMPTY, None)
    else:
        for label, _, explanation in entries:
            menu.append(label, None, explanation)
    menu.append(mp.BACK, CLOSE_MENU)
    menu.run()


def _run_meta_hub_menu():
    menu = Menu(mp.META_PROGRESS, menu_type="submenu")
    menu.append(mp.ACHIEVEMENT_LIST, meta_achievements_list_menu, mp.ACHIEVEMENT_LIST_EXPLANATION)
    menu.append(mp.ARMORY, meta_armory_menu, mp.ARMORY_EXPLANATION)
    menu.append(mp.BACK, CLOSE_MENU)
    menu.loop()


def build_armory_menu_entries(faction=None):
    """返回 [(label_msgs, entry_id_or_none, explanation_msgs), ...] — 便于测试。"""
    state = load_unlock_state(faction)
    medals = int(state.get("medals", 0))
    card_inventory = state.get("cards", {})
    honors = state.get("honors", [])
    entries = []

    if achievements_per_faction_enabled() and faction:
        entries.append((faction_title_msgs(faction), "faction", []))

    rank = get_current_rank(medals, faction)
    if rank and rank.title:
        entries.append((mp.ARMORY_RANK + list(rank.title), "rank", []))

    slots = get_loadout_slots(medals, faction)
    entries.append((mp.ARMORY_LOADOUT_SLOTS + nb2msg(slots), "slots", []))

    for honor_id in honors:
        honor = get_title(honor_id)
        if honor is None:
            continue
        if not honor.faction and achievements_per_faction_enabled():
            continue
        if not definition_matches_faction(honor.faction, faction):
            continue
        if honor.title:
            entries.append((list(honor.title), honor_id, []))

    remaining = medals_until_next_rank(medals, faction)
    nxt = get_next_rank(medals, faction)
    if remaining is not None and nxt and nxt.title:
        entries.append(
            (
                mp.ARMORY_RANK_PROGRESS
                + list(nxt.title)
                + mp.ARMORY_RANK_PROGRESS_NEED
                + nb2msg(remaining)
                + mp.ARMORY_MEDAL_UNIT,
                "next_rank",
                [],
            )
        )

    entries.append((mp.ARMORY_MEDALS + nb2msg(medals), "medals", []))

    for card_id in get_card_order(faction):
        inv = card_inventory.get(card_id)
        if not inv:
            continue
        charges = int(inv.get("charges", 0))
        if charges <= 0 and int(inv.get("total_earned", 0)) <= 0:
            continue
        card = get_card(card_id)
        title = list(card.title) if card and card.title else [card_id]
        label = title + mp.COMMA + mp.ARMORY_CHARGES + nb2msg(charges)
        if card and card.min_rank and not rank_at_least(medals, card.min_rank, faction):
            req = get_title(card.min_rank)
            if req and req.title:
                label = label + mp.COMMA + mp.ARMORY_REQUIRES_RANK + list(req.title)
        entries.append((label, card_id, card_armory_explanation(card_id, medals, faction)))
    return entries


def _resolve_faction_for_menu(faction=None):
    if faction is not None:
        return faction
    if achievements_per_faction_enabled() and len(rules.factions) > 1:
        return select_faction_menu(mp.ACHIEVEMENTS)
    if len(rules.factions) == 1:
        return rules.factions[0]
    return None


def achievements_list_menu(faction=None):
    res.load_rules_and_ai()
    faction = _resolve_faction_for_menu(faction)
    if achievements_per_faction_enabled() and len(rules.factions) > 1 and faction is None:
        return
    set_view_faction(faction)
    entries = build_achievement_menu_entries(faction)
    menu = Menu(mp.ACHIEVEMENT_LIST, menu_type="submenu")
    if not entries:
        menu.append(mp.ACHIEVEMENTS_EMPTY, None)
    else:
        for label, _, explanation in entries:
            menu.append(label, None, explanation)
    menu.append(mp.BACK, CLOSE_MENU)
    menu.run()


def armory_menu(faction=None):
    res.load_rules_and_ai()
    faction = _resolve_faction_for_menu(faction)
    if achievements_per_faction_enabled() and len(rules.factions) > 1 and faction is None:
        return
    set_view_faction(faction)
    entries = build_armory_menu_entries(faction)
    menu = Menu(mp.ARMORY, menu_type="submenu")
    if not entries:
        menu.append(mp.ARMORY_EMPTY, None)
    else:
        for label, _, explanation in entries:
            menu.append(label, None, explanation)
    menu.append(mp.BACK, CLOSE_MENU)
    menu.run()


def _run_faction_hub_menu(faction):
    """成就列表 / 军械库；返回后由上层再次打开阵营选择。"""
    set_view_faction(faction)
    menu = Menu(mp.ACHIEVEMENTS, menu_type="submenu")
    menu.append(mp.ACHIEVEMENT_LIST, lambda: achievements_list_menu(faction), mp.ACHIEVEMENT_LIST_EXPLANATION)
    menu.append(mp.ARMORY, lambda: armory_menu(faction), mp.ARMORY_EXPLANATION)
    menu.append(mp.BACK, CLOSE_MENU)
    menu.loop()


def achievements_menu():
    """主菜单入口：成就列表 + 军械库。"""
    res.load_rules_and_ai()
    if not achievements_enabled():
        return
    if achievements_per_faction_enabled() and len(rules.factions) > 1:
        while True:
            choice = select_faction_or_meta_menu(mp.ACHIEVEMENTS)
            if choice is None:
                return
            if choice == META_MENU_KEY:
                _run_meta_hub_menu()
                continue
            _run_faction_hub_menu(choice)
        return
    menu = Menu(mp.ACHIEVEMENTS, menu_type="submenu")
    menu.append(mp.ACHIEVEMENT_LIST, achievements_list_menu, mp.ACHIEVEMENT_LIST_EXPLANATION)
    menu.append(mp.ARMORY, armory_menu, mp.ARMORY_EXPLANATION)
    menu.append(mp.BACK, CLOSE_MENU)
    menu.loop()


def resolve_training_faction(faction):
    """Ensure a concrete faction before per-faction loadout / saves."""
    if normalize_faction_key(faction) is not None:
        return faction
    if not achievements_per_faction_enabled() or len(rules.factions) <= 1:
        return faction
    picked = select_faction_menu(mp.LOADOUT_SELECT_FACTION)
    return picked or faction
