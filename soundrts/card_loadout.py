"""战前卡牌携带（第三期）：单机对战电脑。"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from . import msgparts as mp
from .achievements import achievements_enabled, load_unlock_state, save_unlock_state
from .cards import CardDef, get_card, get_card_defs, get_card_order
from .definitions import rules
from .lib.log import warning
from .lib.msgs import encode_msg, nb2msg
from .lib.nofloat import to_int
from .definitions import style
from .titles import get_loadout_slots, get_title, rank_at_least
from .worldupgrade import is_an_upgrade


def _card_inventory(state: dict) -> dict:
    return state.get("cards") or {}


def available_charges(state: dict, medals: int, card_id: str, reserved: Sequence[str], faction=None) -> int:
    if not rank_at_least(medals, getattr(get_card(card_id), "min_rank", None), faction):
        return 0
    inv = _card_inventory(state).get(card_id) or {}
    charges = int(inv.get("charges", 0))
    charges -= list(reserved).count(card_id)
    return max(0, charges)


def list_loadout_candidates(state: Optional[dict] = None, medals: Optional[int] = None, faction=None) -> List[str]:
    """Returns card ids with at least one usable charge and rank met."""
    if state is None:
        state = load_unlock_state(faction)
    if medals is None:
        medals = int(state.get("medals", 0))
    result = []
    for card_id in get_card_order(faction):
        if available_charges(state, medals, card_id, [], faction) > 0:
            result.append(card_id)
    return result


def loadout_available(faction=None) -> bool:
    """True when the player has loadout slots and at least one usable card."""
    if not achievements_enabled():
        return False
    state = load_unlock_state(faction)
    medals = int(state.get("medals", 0))
    if get_loadout_slots(medals, faction) <= 0:
        return False
    return bool(list_loadout_candidates(state, medals, faction))


def validate_loadout(card_ids: Sequence[str], state: Optional[dict] = None, faction=None) -> List[str]:
    if state is None:
        state = load_unlock_state(faction)
    medals = int(state.get("medals", 0))
    slots = get_loadout_slots(medals, faction)
    selected: List[str] = []
    for card_id in card_ids:
        if len(selected) >= slots:
            break
        if get_card(card_id) is None:
            continue
        if available_charges(state, medals, card_id, selected, faction) <= 0:
            continue
        selected.append(card_id)
    return selected


def consume_loadout(state: dict, card_ids: Sequence[str]) -> bool:
    """Deduct one charge per selected card; returns True if state changed."""
    changed = False
    cards = state.setdefault("cards", {})
    for card_id in card_ids:
        entry = cards.get(card_id)
        if not entry:
            warning("loadout consume missing card inventory: %s", card_id)
            continue
        charges = int(entry.get("charges", 0))
        if charges <= 0:
            warning("loadout consume with no charges: %s", card_id)
            continue
        entry["charges"] = charges - 1
        changed = True
    return changed


def _spawn_place(player):
    for unit in player.units:
        if getattr(unit, "place", None) is not None:
            return unit.place
    try:
        start_index = (player.number - 1) if player.number is not None else 0
        if 0 <= start_index < len(player.world.players_starts):
            start_entry = player.world.players_starts[start_index]
            for item in start_entry[1]:
                if isinstance(item, (list, tuple)) and item and item[0]:
                    place = player.world.grid.get(item[0])
                    if place is not None:
                        return place
    except Exception:
        pass
    if getattr(player.world, "squares", None):
        return player.world.squares[0]
    return None


def _resolve_unit_class(unit_name: str, faction):
    unit_cls = rules.unit_class(unit_name)
    if unit_cls is None:
        return None
    faction_name = faction or "human"
    return rules.equivalent_type(unit_cls, faction_name)


def _resolve_upgrade_class(tech_name: str, faction):
    upgrade_cls = rules.unit_class(tech_name)
    if upgrade_cls is None or not is_an_upgrade(upgrade_cls):
        return None
    faction_name = faction or "human"
    return rules.equivalent_type(upgrade_cls, faction_name)


def _card_has_effects(card: CardDef) -> bool:
    return bool(card.resources or card.spawns or card.techs or card.train_bonuses)


def _card_delay_ms(world, delay_seconds: int) -> int:
    coeff = getattr(world, "timer_coefficient", 1) or 1
    return int(delay_seconds * 1000 * coeff)


def _delay_time_parts(delay_seconds: int) -> list:
    if delay_seconds >= 60 and delay_seconds % 60 == 0:
        return nb2msg(delay_seconds // 60) + mp.MINUTES
    return nb2msg(delay_seconds) + mp.SECONDS


def _player_by_id(world, player_id):
    for player in getattr(world, "players", []):
        if getattr(player, "id", None) == player_id:
            return player
    return None


def _apply_card_resources(player, card: CardDef) -> bool:
    applied = False
    for index, qty in card.resources:
        if index < 0 or index >= len(player.resources):
            continue
        amount = to_int(str(qty))
        player.resources[index] += amount
        player.stats.add("gathered", index, amount)
        applied = True
    return applied


def _apply_card_spawns(player, card: CardDef) -> bool:
    if not card.spawns:
        return False
    place = _spawn_place(player)
    if place is None and card.spawns:
        warning("loadout spawn has no place for card %s", card.id)
        return False
    applied = False
    faction = getattr(player, "faction", None)
    units_before = len(getattr(player, "units", []))
    for unit_name, count in card.spawns:
        unit_cls = _resolve_unit_class(unit_name, faction)
        if unit_cls is None:
            warning("loadout spawn unknown unit %s for card %s", unit_name, card.id)
            continue
        if place is None:
            break
        for _ in range(max(1, int(count))):
            player.add_unit(unit_cls, place, population_cost=0)
    if len(getattr(player, "units", [])) > units_before:
        applied = True
    return applied


def _apply_card_techs(player, card: CardDef) -> bool:
    applied = False
    faction = getattr(player, "faction", None)
    upgrades = getattr(player, "upgrades", None)
    if upgrades is None:
        return False
    for tech_name in card.techs:
        upgrade_cls = _resolve_upgrade_class(tech_name, faction)
        if upgrade_cls is None:
            warning("loadout tech unknown upgrade %s for card %s", tech_name, card.id)
            continue
        type_name = upgrade_cls.type_name
        if type_name in upgrades:
            continue
        upgrade_cls.upgrade_player(player)
        applied = True
    return applied


def _apply_card_train_bonuses(player, card: CardDef) -> bool:
    if not card.train_bonuses:
        return False
    applied = False
    faction = getattr(player, "faction", None)
    bonuses = getattr(player, "_loadout_train_bonuses", None)
    if bonuses is None:
        bonuses = {}
        player._loadout_train_bonuses = bonuses
    for unit_name, count in card.train_bonuses:
        unit_cls = _resolve_unit_class(unit_name, faction)
        if unit_cls is None:
            warning("loadout train_bonus unknown unit %s for card %s", unit_name, card.id)
            continue
        type_name = unit_cls.type_name
        bonuses[type_name] = bonuses.get(type_name, 0) + max(0, int(count))
        applied = True
    return applied


def _spawn_train_bonus_unit(player, unit_type, place, near_x, near_y, rally_point):
    x, y = place.find_free_space(unit_type.airground_type, near_x, near_y)
    if x is None:
        return None
    unit = unit_type(player, place, x, y)
    try:
        base_pop = max(0, int(getattr(unit_type, "population_cost", 0)))
        if base_pop > 0:
            unit.effective_population_cost = 0
            player.used_population -= base_pop
    except Exception:
        pass
    unit.notify("complete")
    if rally_point is not None:
        unit.take_default_order(rally_point)
    return unit


def apply_train_bonus_for_unit(player, unit_type, place, x, y, rally_point) -> int:
    """After one unit finishes training, spawn loadout bonus units once per type per game."""
    bonuses = getattr(player, "_loadout_train_bonuses", None)
    if not bonuses:
        return 0
    type_name = getattr(unit_type, "type_name", None) or getattr(unit_type, "__name__", "")
    bonus_count = int(bonuses.get(type_name, 0))
    if bonus_count <= 0:
        return 0
    del bonuses[type_name]
    spawned = 0
    ref_x, ref_y = x, y
    for _ in range(bonus_count):
        unit = _spawn_train_bonus_unit(player, unit_type, place, ref_x, ref_y, rally_point)
        if unit is None:
            break
        spawned += 1
        ref_x, ref_y = unit.x, unit.y
    return spawned


def get_train_bonus_count(player, unit_type) -> int:
    bonuses = getattr(player, "_loadout_train_bonuses", None) or {}
    type_name = getattr(unit_type, "type_name", None) or getattr(unit_type, "__name__", "")
    return int(bonuses.get(type_name, 0))


def _apply_card_effects(player, card: CardDef) -> bool:
    applied = _apply_card_resources(player, card)
    applied = _apply_card_spawns(player, card) or applied
    applied = _apply_card_techs(player, card) or applied
    applied = _apply_card_train_bonuses(player, card) or applied
    return applied


def _schedule_card_effects(player, card_id: str, card: CardDef) -> bool:
    world = getattr(player, "world", None)
    if world is None or not hasattr(world, "schedule_after"):
        warning("loadout delay requires world.schedule_after for card %s", card_id)
        return False
    if not _card_has_effects(card):
        return False
    player_id = getattr(player, "id", None)
    if player_id is None:
        warning("loadout delay requires player id for card %s", card_id)
        return False
    delay_ms = _card_delay_ms(world, card.delay)

    def _fire():
        target = _player_by_id(world, player_id)
        if target is None:
            warning("loadout delayed card %s: player %s missing", card_id, player_id)
            return
        if not _apply_card_effects(target, card):
            warning("loadout delayed card %s: no effect applied", card_id)
            return
        for msg in loadout_triggered_msgs([card_id]):
            for p in getattr(world, "players", []):
                if p is target and p.is_local_human():
                    p.push("msg", encode_msg(msg))

    world.schedule_after(delay_ms, _fire)
    return True


def apply_card_to_player(player, card_id: str) -> bool:
    card = get_card(card_id)
    if card is None:
        warning("unknown loadout card: %s", card_id)
        return False
    if card.delay > 0:
        return _schedule_card_effects(player, card_id, card)
    return _apply_card_effects(player, card)


def _local_human_player(game):
    """Resolve the local human player before GameInterface exists."""
    local_client = getattr(game, "local_client", None)
    player = getattr(local_client, "player", None) if local_client is not None else None
    if player is not None:
        return player
    world = getattr(game, "world", None)
    if world is None:
        return None
    for p in world.players:
        if getattr(p, "is_human", False) and not getattr(p, "is_spectator", False):
            return p
    return None


def _is_train_bonus_only_card(card) -> bool:
    return bool(card.train_bonuses) and not (
        card.resources or card.spawns or card.techs or card.delay > 0
    )


def _armory_card_hint_msgs(card) -> List:
    """Opening hint: carry requirement + when the card actually takes effect."""
    from . import msgparts as mp

    msgs = list(mp.ARMORY_CARD_HINT_PREFIX)
    if card.delay > 0:
        msgs += (
            mp.LOADOUT_CARD_DELAY_AFTER
            + _delay_time_parts(card.delay)
            + mp.LOADOUT_CARD_DELAY_SUFFIX
        )
    elif not _is_train_bonus_only_card(card):
        msgs += list(mp.ARMORY_CARD_HINT_INSTANT)
    return msgs


def card_armory_explanation(card_id: str, medals: Optional[int] = None, faction=None) -> List[list]:
    """Build TTS explanation for a card in the armory menu."""
    from . import msgparts as mp

    card = get_card(card_id)
    if card is None:
        return []
    msgs = _armory_card_hint_msgs(card)
    delayed = card.delay > 0
    for index, qty in card.resources:
        res_title = style.get("parameters", f"resource{index + 1}_title")
        if not res_title:
            res_title = style.get(f"resource{index + 1}", "title")
        if delayed:
            msgs += mp.ARMORY_CARD_RESOURCE_DELAYED
        else:
            msgs += mp.ARMORY_CARD_EXTRA_RESOURCE
        if res_title:
            msgs += list(res_title)
        msgs += nb2msg(qty)
    for unit_name, count in card.spawns:
        unit_title = style.get(unit_name, "title") or [unit_name]
        if delayed:
            msgs += mp.ARMORY_CARD_SPAWN_DELAYED
        else:
            msgs += mp.ARMORY_CARD_SPAWN_NEAR_START
        msgs += nb2msg(max(1, int(count))) + list(unit_title)
    for unit_name, count in card.train_bonuses:
        unit_title = style.get(unit_name, "title") or [unit_name]
        msgs += mp.ARMORY_CARD_TRAIN_BONUS + nb2msg(max(1, int(count))) + list(unit_title)
    for tech_name in card.techs:
        tech_title = style.get(tech_name, "title") or [tech_name]
        msgs += mp.ARMORY_CARD_TECH + list(tech_title)
    if card.min_rank:
        if medals is None:
            medals = int(load_unlock_state(faction).get("medals", 0))
        if not rank_at_least(medals, card.min_rank, faction):
            req = get_title(card.min_rank)
            if req and req.title:
                msgs += mp.ARMORY_REQUIRES_RANK + list(req.title)
    return msgs


def apply_loadout_to_player(player, card_ids: Sequence[str]) -> List[str]:
    """Apply cards in order; returns ids actually applied."""
    applied = []
    for card_id in card_ids:
        if apply_card_to_player(player, card_id):
            applied.append(card_id)
    return applied


def loadout_applied_msgs(card_ids: Sequence[str]) -> List[list]:
    msgs = []
    for card_id in card_ids:
        card = get_card(card_id)
        if card and card.title:
            if card.delay > 0:
                msgs.append(
                    mp.LOADOUT_CARD_APPLIED
                    + list(card.title)
                    + mp.COMMA
                    + mp.LOADOUT_CARD_DELAY_AFTER
                    + _delay_time_parts(card.delay)
                    + mp.LOADOUT_CARD_DELAY_SUFFIX
                )
            elif card.train_bonuses and not (card.resources or card.spawns or card.techs):
                msg = mp.LOADOUT_CARD_APPLIED + list(card.title) + mp.COMMA + mp.LOADOUT_CARD_TRAIN_BONUS_ACTIVE
                for unit_name, count in card.train_bonuses:
                    unit_title = style.get(unit_name, "title") or [unit_name]
                    msg += mp.ARMORY_CARD_TRAIN_BONUS + nb2msg(max(1, int(count))) + list(unit_title)
                msgs.append(msg)
            else:
                msgs.append(mp.LOADOUT_CARD_APPLIED + list(card.title))
    return msgs


def loadout_triggered_msgs(card_ids: Sequence[str]) -> List[list]:
    msgs = []
    for card_id in card_ids:
        card = get_card(card_id)
        if card and card.title:
            msgs.append(mp.LOADOUT_CARD_TRIGGERED + list(card.title))
    return msgs


def apply_training_loadout(game, card_ids: Sequence[str], faction=None) -> List[str]:
    """Apply loadout for local human in a training/skirmish game."""
    if not achievements_enabled():
        return []
    if getattr(game, "game_type_name", "") != "training":
        return []
    if not card_ids:
        return []
    world = getattr(game, "world", None)
    if world is None:
        return []
    player = _local_human_player(game)
    if player is None:
        return []
    if faction is None:
        faction = getattr(player, "faction", None)
    state = load_unlock_state(faction)
    validated = validate_loadout(card_ids, state, faction)
    if not validated:
        return []
    applied = apply_loadout_to_player(player, validated)
    if applied and consume_loadout(state, applied):
        save_unlock_state(state, faction)
    return applied


def card_loadout_label(card_id: str, state: dict, medals: int, reserved: Sequence[str], faction=None) -> list:
    card = get_card(card_id)
    title = list(card.title) if card and card.title else [card_id]
    charges = available_charges(state, medals, card_id, reserved, faction)
    label = title + mp.COMMA + mp.ARMORY_CHARGES + nb2msg(charges)
    if card and card.min_rank and not rank_at_least(medals, card.min_rank, faction):
        from .titles import get_title

        req = get_title(card.min_rank)
        if req and req.title:
            label = label + mp.COMMA + mp.ARMORY_REQUIRES_RANK + list(req.title)
    return label
