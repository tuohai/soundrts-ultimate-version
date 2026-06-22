"""Persistent hero state for single-player campaigns (rules-driven)."""

from __future__ import annotations

from typing import Dict, List, Optional

from .lib.log import warning

_HERO_STATE_KEYS = ("xp", "level", "inventory")


def _hero_prefix(persist_id: str) -> str:
    return f"hero_{persist_id}_"


def _rules_flag(value) -> bool:
    if value in (1, "1", True):
        return True
    if isinstance(value, list) and value:
        return str(value[0]) in ("1", "true", "True")
    return False


def carryover_id_for_type(type_name: str) -> Optional[str]:
    """Return storage id for a unit type with ``campaign_carryover 1``, or None."""
    if not type_name:
        return None
    from .definitions import rules

    seen: set[str] = set()

    def _is_a_names(name: str) -> List[str]:
        is_a = rules.get(name, "is_a") or []
        if isinstance(is_a, str):
            is_a = is_a.split()
        return list(is_a)

    def _persist_id(name: str) -> str:
        custom = rules.get(name, "campaign_carryover_id")
        if isinstance(custom, list):
            custom = custom[0] if custom else None
        return str(custom) if custom else name

    def walk(name: str) -> Optional[str]:
        if not name or name in seen:
            return None
        seen.add(name)
        if _rules_flag(rules.get(name, "campaign_carryover")):
            parents = _is_a_names(name)
            if not any(_rules_flag(rules.get(p, "campaign_carryover")) for p in parents):
                return _persist_id(name)
        for parent in _is_a_names(name):
            found = walk(parent)
            if found:
                return found
        return None

    return walk(type_name)


def _carryover_root_type(persist_id: str) -> Optional[str]:
    """Find the rules def that owns ``persist_id`` storage."""
    if not persist_id:
        return None
    from .definitions import rules

    def _is_root_declarer(name: str) -> bool:
        if not _rules_flag(rules.get(name, "campaign_carryover")):
            return False
        is_a = rules.get(name, "is_a") or []
        if isinstance(is_a, str):
            is_a = is_a.split()
        return not any(_rules_flag(rules.get(p, "campaign_carryover")) for p in is_a)

    if _is_root_declarer(persist_id):
        return persist_id

    try:
        names = rules.classnames()
    except ValueError:
        names = list(getattr(rules, "_dict", {}).keys())
    for name in names:
        if carryover_id_for_type(name) != persist_id:
            continue
        if _is_root_declarer(name):
            return name
    return None


def carryover_modes_for_id(persist_id: str) -> tuple[bool, bool]:
    """Return ``(stats, inventory)`` enabled for a persist id (defaults: both on)."""
    root = _carryover_root_type(persist_id)
    if root is None:
        return True, True
    from .definitions import rules

    stats_val = rules.get(root, "campaign_carryover_stats")
    inv_val = rules.get(root, "campaign_carryover_inventory")
    stats_on = _rules_flag(stats_val) if stats_val is not None else True
    inv_on = _rules_flag(inv_val) if inv_val is not None else True
    return stats_on, inv_on


def carryover_modes_for_unit(unit) -> tuple[bool, bool]:
    persist_id = carryover_id_for_unit(unit)
    if not persist_id:
        return False, False
    return carryover_modes_for_id(persist_id)


def carryover_id_for_unit(unit) -> Optional[str]:
    return carryover_id_for_type(getattr(unit, "type_name", None))


def _read_campaign_ini(campaign):
    from .paths import CAMPAIGNS_CONFIG_PATH
    import configparser

    c = configparser.ConfigParser()
    c.read(CAMPAIGNS_CONFIG_PATH, encoding="utf-8")
    section = campaign._id()
    if not c.has_section(section):
        c.add_section(section)
    return c, section


def _write_campaign_ini(c):
    from .paths import CAMPAIGNS_CONFIG_PATH

    with open(CAMPAIGNS_CONFIG_PATH, "w", encoding="utf-8") as f:
        c.write(f)


def list_persisted_hero_ids(campaign) -> List[str]:
    if campaign is None:
        return []
    c, section = _read_campaign_ini(campaign)
    ids: set[str] = set()
    prefix = "hero_"
    for opt in c.options(section):
        if not opt.startswith(prefix):
            continue
        rest = opt[len(prefix) :]
        for suffix in ("_xp", "_level", "_inventory"):
            if rest.endswith(suffix):
                ids.add(rest[: -len(suffix)])
                break
    return sorted(ids)


def _read_int(campaign, persist_id: str, key: str, default: int = 0) -> int:
    c, section = _read_campaign_ini(campaign)
    raw = c.get(section, _hero_prefix(persist_id) + key, fallback="")
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _read_inventory(campaign, persist_id: str) -> List[str]:
    c, section = _read_campaign_ini(campaign)
    raw = c.get(section, _hero_prefix(persist_id) + "inventory", fallback="")
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def load_hero_snapshot(campaign, persist_id: str) -> Optional[dict]:
    """Return saved hero state for ``persist_id``, or None if missing."""
    if campaign is None or not persist_id:
        return None
    xp = _read_int(campaign, persist_id, "xp", -1)
    level = _read_int(campaign, persist_id, "level", -1)
    inventory = _read_inventory(campaign, persist_id)
    if xp < 0 and level < 0 and not inventory:
        return None
    return {
        "xp": max(0, xp) if xp >= 0 else 0,
        "level": max(1, level) if level >= 0 else 1,
        "inventory": inventory,
    }


def save_hero_snapshot(campaign, unit, persist_id: str | None = None) -> None:
    """Persist hero unit state after a victorious mission."""
    if campaign is None or unit is None:
        return
    if not persist_id:
        persist_id = carryover_id_for_unit(unit)
    if not persist_id:
        return

    stats_on, inv_on = carryover_modes_for_id(persist_id)
    inv = []
    if inv_on:
        for item in getattr(unit, "inventory", []) or []:
            name = getattr(item, "type_name", None)
            if name:
                inv.append(str(name))
    c, section = _read_campaign_ini(campaign)
    prefix = _hero_prefix(persist_id)
    if stats_on:
        c.set(section, prefix + "xp", str(int(getattr(unit, "xp", 0))))
        c.set(section, prefix + "level", str(int(getattr(unit, "level", 1))))
    else:
        for key in ("xp", "level"):
            if c.has_option(section, prefix + key):
                c.remove_option(section, prefix + key)
    if inv_on:
        c.set(section, prefix + "inventory", ",".join(inv))
    elif c.has_option(section, prefix + "inventory"):
        c.remove_option(section, prefix + "inventory")
    _write_campaign_ini(c)


def clear_hero_snapshot(campaign, persist_id: str | None = None) -> None:
    if campaign is None:
        return
    c, section = _read_campaign_ini(campaign)
    if not c.has_section(section):
        return
    ids = [persist_id] if persist_id else list_persisted_hero_ids(campaign)
    changed = False
    for pid in ids:
        for key in _HERO_STATE_KEYS:
            opt = _hero_prefix(pid) + key
            if c.has_option(section, opt):
                c.remove_option(section, opt)
                changed = True
    if changed:
        _write_campaign_ini(c)


def chapter_min_level(chapter_number: int, campaign=None) -> int:
    """Minimum hero level for this chapter (from ``campaign.txt`` ``hero_min_level``)."""
    thresholds: Dict[int, int] = {}
    if campaign is not None:
        thresholds = getattr(campaign, "hero_min_level", None) or {}
    best = 1
    for ch, lv in thresholds.items():
        if chapter_number >= ch:
            best = max(best, lv)
    return best


def _apply_level_stats(unit, target_level: int) -> None:
    """Apply cumulative per-level bonuses up to target_level (base stats unchanged)."""
    from .level_up_stats import apply_level_up_to

    apply_level_up_to(unit, target_level, notify=False)


def _restore_one_hero(
    human,
    persist_id: str,
    snapshot: dict,
    min_level: int,
    *,
    stats_on: bool = True,
    inv_on: bool = True,
) -> None:
    from .definitions import rules

    heroes = [
        u
        for u in list(human.units)
        if carryover_id_for_unit(u) == persist_id
    ]
    if not heroes:
        warning(
            "campaign_hero: no carryover hero (%s) on map to restore",
            persist_id,
        )
        return
    hero = heroes[0]
    for extra in heroes[1:]:
        extra.delete()

    if stats_on:
        target_level = max(snapshot.get("level", 1), min_level)
        target_xp = max(snapshot.get("xp", 0), 0)
        _apply_level_stats(hero, target_level)
        hero.xp = max(target_xp, getattr(hero, "xp", 0))
        hero.hp = hero.hp_max

    if inv_on:
        for item in list(getattr(hero, "inventory", []) or []):
            if hasattr(item, "delete"):
                item.delete()
        hero.inventory = []

        place = getattr(hero, "place", None)
        x = getattr(hero, "x", 0)
        y = getattr(hero, "y", 0)
        for item_type in snapshot.get("inventory", []):
            cls = rules.unit_class(item_type)
            if cls is None:
                continue
            try:
                item = cls(place, x, y)
                item.move_to(None, 0, 0)
                hero.inventory.append(item)
                if hasattr(item, "equip"):
                    item.equip(hero)
            except Exception as e:
                warning("campaign_hero: could not restore item %s: %s", item_type, e)


def restore_hero_on_world(world, campaign, chapter_number: int) -> None:
    """Apply saved hero snapshots for all ``campaign_carryover`` types."""
    if campaign is None or getattr(world, "is_campaign", False) is False:
        return
    if getattr(world, "campaign", None) is None:
        # Co-op: no cross-chapter hero persistence
        return

    human = None
    for p in world.players:
        if getattr(p, "is_human", False):
            human = p
            break
    if human is None:
        return

    min_level = chapter_min_level(chapter_number, campaign)
    for persist_id in list_persisted_hero_ids(campaign):
        snapshot = load_hero_snapshot(campaign, persist_id)
        if snapshot is None:
            continue
        stats_on, inv_on = carryover_modes_for_id(persist_id)
        _restore_one_hero(
            human,
            persist_id,
            snapshot,
            min_level,
            stats_on=stats_on,
            inv_on=inv_on,
        )


def save_hero_after_victory(game) -> None:
    if not game.has_victory():
        return
    chapter = getattr(game, "chapter", None)
    if chapter is None:
        return
    campaign = getattr(chapter, "campaign", None)
    if campaign is None:
        return
    client = getattr(game, "local_client", None)
    if client is None or not hasattr(client, "player"):
        return
    saved: set[str] = set()
    for unit in client.player.units:
        persist_id = carryover_id_for_unit(unit)
        if persist_id and persist_id not in saved:
            save_hero_snapshot(campaign, unit, persist_id)
            saved.add(persist_id)
