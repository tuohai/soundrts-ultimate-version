"""成就系统（第一期）：定义加载、条件判定、按 mod 本地存档、结算播报。

详见 docs/zh/achievement-system.md
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from . import msgparts as mp
from .cards import card_exists, get_card
from .definitions import get_ai_defeat_score, preprocess, rules
from .definitions import AI_DIFFICULTIES, DEFAULT_AI_DEFEAT_SCORE
from .titles import (
    KIND_HONOR,
    get_current_rank,
    get_loadout_slots,
    get_title,
    medals_until_next_rank,
    ranks_newly_reached,
    title_exists,
)
from .lib.log import warning
from .lib.msgs import nb2msg
from .meta_progress import save_meta_state
from .paths import CONFIG_DIR_PATH, current_mod_key
from .faction_progress import (
    achievements_per_faction_enabled,
    definition_matches_faction,
    normalize_faction_key,
)

Condition = Tuple

_VICTORY_MODE_MSGPARTS = {
    "conquest": mp.RMG_VICTORY_CONQUEST,
    "economic": mp.RMG_VICTORY_ECONOMIC,
    "exploration": mp.RMG_VICTORY_EXPLORATION,
    "survival": mp.RMG_VICTORY_SURVIVAL,
}

_achievements: Dict[str, "AchievementDef"] = {}
_achievements_order: List[str] = []


@dataclass
class AchievementDef:
    id: str
    title: List = field(default_factory=list)
    conditions: List[Condition] = field(default_factory=list)
    once_mode: str = "once"
    rewards: List[Tuple] = field(default_factory=list)
    repeat_medal: int = 0
    faction: Optional[str] = None
    scope: str = "faction"


@dataclass
class AchievementContext:
    victory: bool
    grade: str
    utilization_percent: int
    survival: int
    building_defense: int
    map_name: str
    defeated_ai_types: List[str]
    primary_enemy_ai: Optional[str]
    is_random_map: bool = False
    victory_mode: str = "conquest"


def achievements_enabled() -> bool:
    """Whether the current mod keeps achievements, cards, ranks, and loadout."""
    value = rules.get("parameters", "achievements_enabled", 1)
    if value in (0, "0", False):
        return False
    if isinstance(value, list) and value:
        return str(value[0]) not in ("0", "false", "False")
    return True


def load_achievements(*strings):
    """加载 achievements.txt（多层 append，与 ai.txt 相同）。"""
    global _achievements, _achievements_order
    _achievements = {}
    _achievements_order = []
    for s in strings:
        if s and s.strip():
            _read_achievements_layer(s)


def get_achievement_defs() -> Dict[str, AchievementDef]:
    return dict(_achievements)


def get_achievement_order() -> List[str]:
    return list(_achievements_order)


def _parse_condition(words: List[str]) -> Optional[Condition]:
    if not words:
        return None
    if words[0] == "grade" and len(words) >= 2:
        return ("grade", words[1].upper())
    if words[0] == "victory":
        return ("victory",)
    if words[0] == "utilization_below" and len(words) >= 2 and words[1].isdigit():
        return ("utilization_below", int(words[1]))
    if words[0] == "defeated_ai" and len(words) >= 2:
        return ("defeated_ai", tuple(words[1:]))
    if words[0] == "map" and len(words) >= 2:
        return ("map", tuple(words[1:]))
    if words[0] == "defeated_ai_total_at_least" and len(words) >= 3 and words[1].isdigit():
        return ("defeated_ai_total_at_least", int(words[1]), tuple(words[2:]))
    if words[0] == "defeated_ai_map_at_least" and len(words) >= 4 and words[2].isdigit():
        return ("defeated_ai_map_at_least", words[1], int(words[2]), tuple(words[3:]))
    if words[0] == "survival_at_least" and len(words) >= 2 and words[1].isdigit():
        return ("survival_at_least", int(words[1]))
    if words[0] == "building_defense_at_least" and len(words) >= 2 and words[1].isdigit():
        return ("building_defense_at_least", int(words[1]))
    if words[0] == "random_map":
        return ("random_map",)
    if words[0] == "victory_mode" and len(words) >= 2:
        return ("victory_mode", words[1].lower())
    if words[0] == "achievement" and len(words) >= 2:
        return ("achievement", words[1])
    if words[0] == "factions_unlocked_at_least" and len(words) >= 3 and words[1].isdigit() and words[2].isdigit():
        return ("factions_unlocked_at_least", int(words[1]), int(words[2]))
    if words[0] == "factions_medals_at_least" and len(words) >= 3 and words[1].isdigit() and words[2].isdigit():
        return ("factions_medals_at_least", int(words[1]), int(words[2]))
    if words[0] == "factions_honors_at_least" and len(words) >= 3 and words[1].isdigit() and words[2].isdigit():
        return ("factions_honors_at_least", int(words[1]), int(words[2]))
    if words[0] == "factions_achievement_id_contains_at_least" and len(words) >= 3 and words[1].isdigit():
        return ("factions_achievement_id_contains_at_least", int(words[1]), words[2])
    warning("unknown achievement condition: %s", " ".join(words))
    return None


def _read_achievements_layer(s: str):
    s = preprocess(s)
    current: Optional[AchievementDef] = None
    for line in s.split("\n"):
        words = line.split()
        if not words:
            continue
        if words[0] == "clear":
            _achievements.clear()
            _achievements_order.clear()
            current = None
            continue
        if words[0] == "def":
            if len(words) < 2:
                warning("achievement def missing id")
                continue
            current = AchievementDef(id=words[1])
            _achievements[current.id] = current
            if current.id not in _achievements_order:
                _achievements_order.append(current.id)
            continue
        if current is None:
            warning("'def <achievement_id>' is missing (check achievements.txt)")
            continue
        if words[0] == "title":
            if len(words) >= 2 and words[1].isdigit():
                current.title = [int(words[1])]
            else:
                current.title = [int(w) for w in words[1:] if w.isdigit()]
        elif words[0] == "condition":
            cond = _parse_condition(words[1:])
            if cond is not None:
                current.conditions.append(cond)
        elif words[0] == "once":
            current.once_mode = "once"
        elif words[0] == "once_per" and len(words) >= 2:
            current.once_mode = words[1]
        elif words[0] == "reward":
            reward = _parse_reward(words[1:])
            if reward is not None:
                current.rewards.append(reward)
        elif words[0] == "repeat_medal" and len(words) >= 2 and words[1].isdigit():
            current.repeat_medal = max(0, int(words[1]))
        elif words[0] in ("faction", "race") and len(words) >= 2:
            current.faction = words[1]
        elif words[0] == "scope" and len(words) >= 2:
            current.scope = words[1]


def _parse_reward(words: List[str]) -> Optional[Tuple]:
    if not words:
        return None
    if words[0] == "medal" and len(words) >= 2 and words[1].isdigit():
        return ("medal", int(words[1]))
    if words[0] == "card" and len(words) >= 2:
        card_id = words[1]
        times = 1
        if len(words) >= 3 and words[2].isdigit():
            times = max(1, int(words[2]))
        return ("card", card_id, times)
    if words[0] == "title" and len(words) >= 2:
        return ("title", words[1])
    warning("unknown achievement reward: %s", " ".join(words))
    return None


def achievements_save_path(faction=None) -> str:
    directory = os.path.join(CONFIG_DIR_PATH, "achievements")
    try:
        os.makedirs(directory, exist_ok=True)
    except OSError:
        pass
    mod_key = current_mod_key()
    if achievements_per_faction_enabled():
        faction_key = normalize_faction_key(faction) or "_default"
        faction_dir = os.path.join(directory, mod_key)
        try:
            os.makedirs(faction_dir, exist_ok=True)
        except OSError:
            pass
        return os.path.join(faction_dir, f"{faction_key}.json")
    return os.path.join(directory, f"{mod_key}.json")


def load_unlock_state(faction=None) -> dict:
    path = achievements_save_path(faction)
    if not os.path.isfile(path):
        return _empty_unlock_state()
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        warning("couldn't read achievements save: %s", path)
        return _empty_unlock_state()
    return _normalize_unlock_state(data)


def _empty_unlock_state() -> dict:
    return {
        "unlocked": {},
        "once_keys": {},
        "medals": 0,
        "cards": {},
        "honors": [],
        "ai_defeats": {},
        "map_ai_defeats": {},
    }


_AI_SCRIPT_TO_TIER: Dict[str, str] = {}
_AI_SCRIPT_RULES_ID: Optional[int] = None


def _legacy_tier_alias(ai_type: str) -> str:
    if ai_type == "easy":
        return "beginner"
    if ai_type == "aggressive":
        return "intermediate"
    return ai_type


def _build_ai_script_to_tier() -> None:
    global _AI_SCRIPT_TO_TIER, _AI_SCRIPT_RULES_ID
    rules_id = id(rules)
    if _AI_SCRIPT_TO_TIER and _AI_SCRIPT_RULES_ID == rules_id:
        return
    _AI_SCRIPT_TO_TIER = {}
    _AI_SCRIPT_RULES_ID = rules_id
    for faction in rules.factions:
        for tier in AI_DIFFICULTIES + ["easy", "aggressive"]:
            mapped = rules.get(faction, tier)
            if not mapped or not mapped[0]:
                continue
            script = mapped[0]
            canonical = _legacy_tier_alias(tier)
            _AI_SCRIPT_TO_TIER.setdefault(script, canonical)


def _tier_from_defeat_score(ai_type: str) -> Optional[str]:
    score = get_ai_defeat_score(ai_type)
    if score <= 0:
        return None
    for tier in reversed(AI_DIFFICULTIES):
        if score >= DEFAULT_AI_DEFEAT_SCORE.get(tier, 0):
            return tier
    return None


def _normalize_defeat_tier(ai_type: str) -> str:
    aliased = _legacy_tier_alias(ai_type)
    if aliased in AI_DIFFICULTIES:
        return aliased
    _build_ai_script_to_tier()
    mapped = _AI_SCRIPT_TO_TIER.get(ai_type)
    if mapped:
        return mapped
    by_score = _tier_from_defeat_score(ai_type)
    if by_score:
        return by_score
    return aliased


def _countable_defeat_tier(ai_type: str) -> Optional[str]:
    tier = _normalize_defeat_tier(ai_type)
    if tier in AI_DIFFICULTIES or tier in ("easy", "aggressive"):
        return tier
    if get_ai_defeat_score(tier) > 0:
        return tier
    return None


def _defeat_total(state: dict, tiers: Tuple[str, ...]) -> int:
    totals = state.get("ai_defeats") or {}
    keys = {_normalize_defeat_tier(t) for t in tiers}
    return sum(int(totals.get(key, 0)) for key in keys)


def _map_defeat_total(state: dict, map_id: str, tiers: Tuple[str, ...]) -> int:
    per_map = state.get("map_ai_defeats") or {}
    entry = per_map.get(map_id) or {}
    keys = {_normalize_defeat_tier(t) for t in tiers}
    return sum(int(entry.get(key, 0)) for key in keys)


def record_defeat_progress(ctx: AchievementContext, state: dict) -> bool:
    """On victory, add defeated computer tiers to cumulative counters."""
    if not ctx.victory:
        return False
    tier_counts: Dict[str, int] = {}
    for ai_type in ctx.defeated_ai_types:
        tier = _countable_defeat_tier(ai_type)
        if tier is None:
            continue
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
    if not tier_counts:
        return False
    ai_defeats = state.setdefault("ai_defeats", {})
    map_ai_defeats = state.setdefault("map_ai_defeats", {})
    map_entry = map_ai_defeats.setdefault(ctx.map_name, {}) if ctx.map_name else {}
    changed = False
    for tier, qty in tier_counts.items():
        ai_defeats[tier] = int(ai_defeats.get(tier, 0)) + qty
        changed = True
        if ctx.map_name:
            map_entry[tier] = int(map_entry.get(tier, 0)) + qty
    return changed


def _migrate_defeat_counters(state: dict) -> bool:
    """Merge legacy faction AI script keys into canonical difficulty tiers."""
    changed = False
    for bucket_key in ("ai_defeats",):
        bucket = state.get(bucket_key) or {}
        if not bucket:
            continue
        migrated: Dict[str, int] = {}
        for tier, count in bucket.items():
            canonical = _normalize_defeat_tier(str(tier))
            migrated[canonical] = int(migrated.get(canonical, 0)) + int(count)
        if migrated != bucket:
            state[bucket_key] = migrated
            changed = True
    per_map = state.get("map_ai_defeats") or {}
    if per_map:
        new_per_map: Dict[str, Dict[str, int]] = {}
        for map_id, entry in per_map.items():
            migrated: Dict[str, int] = {}
            for tier, count in (entry or {}).items():
                canonical = _normalize_defeat_tier(str(tier))
                migrated[canonical] = int(migrated.get(canonical, 0)) + int(count)
            new_per_map[map_id] = migrated
        if new_per_map != per_map:
            state["map_ai_defeats"] = new_per_map
            changed = True
    return changed


def _normalize_unlock_state(data: dict) -> dict:
    if "unlocked" not in data:
        data["unlocked"] = {}
    if "once_keys" not in data:
        data["once_keys"] = {}
    if "medals" not in data:
        data["medals"] = 0
    if "cards" not in data:
        data["cards"] = {}
    if "honors" not in data:
        data["honors"] = []
    elif not isinstance(data["honors"], list):
        data["honors"] = list(data["honors"])
    if "ai_defeats" not in data:
        data["ai_defeats"] = {}
    if "map_ai_defeats" not in data:
        data["map_ai_defeats"] = {}
    _migrate_defeat_counters(data)
    return data


def save_unlock_state(data: dict, faction=None):
    path = achievements_save_path(faction)
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, path)
    except OSError:
        warning("couldn't write achievements save: %s", path)


def _primary_enemy_ai(entries) -> Optional[str]:
    best_name = None
    best_score = -1
    for entry in entries or []:
        ai_type = entry.get("ai_type")
        if not ai_type:
            continue
        score = get_ai_defeat_score(ai_type)
        if score > best_score:
            best_score = score
            best_name = ai_type
    return best_name


def build_context(player, game) -> AchievementContext:
    stats = player.stats
    scoring_victory = (
        game.scoring_victory()
        if game is not None and hasattr(game, "scoring_victory")
        else bool(getattr(player, "has_victory", False))
    )
    scored_enemy_ids = (
        game.scored_enemy_ids()
        if game is not None and hasattr(game, "scored_enemy_ids")
        else None
    )
    try:
        breakdown = stats.score_breakdown(
            effective_victory=scoring_victory,
            scored_enemy_ids=scored_enemy_ids,
        )
    except TypeError:
        breakdown = stats.score_breakdown()
    grade = stats.score_grade_letter(breakdown["total"])
    entries = breakdown.get("ai_defeat_entries") or []
    defeated = []
    for entry in entries:
        defeated.extend([entry["ai_type"]] * int(entry.get("count", 1)))
    map_obj = getattr(game, "map", None)
    map_name = getattr(map_obj, "name", "") or ""
    definition = getattr(map_obj, "definition", "") or ""
    from .randommap import parse_random_map_meta

    is_random_map, victory_mode = parse_random_map_meta(definition)
    return AchievementContext(
        victory=scoring_victory,
        grade=grade,
        utilization_percent=int(breakdown.get("utilization_percent", 0)),
        survival=int(breakdown.get("survival", 0)),
        building_defense=int(breakdown.get("building_defense", 0)),
        map_name=map_name,
        defeated_ai_types=defeated,
        primary_enemy_ai=_primary_enemy_ai(entries),
        is_random_map=is_random_map,
        victory_mode=victory_mode,
    )


def _meta_condition_met(cond: Condition, snapshots: Optional[dict] = None) -> bool:
    from .meta_progress import (
        count_factions_achievement_id_contains,
        count_factions_honors_at_least,
        count_factions_medals_at_least,
        count_factions_unlocked_at_least,
    )

    if snapshots is None:
        return False
    kind = cond[0]
    if kind == "factions_unlocked_at_least":
        needed, min_unlocked = cond[1], cond[2]
        return count_factions_unlocked_at_least(snapshots, min_unlocked) >= needed
    if kind == "factions_medals_at_least":
        needed, min_medals = cond[1], cond[2]
        return count_factions_medals_at_least(snapshots, min_medals) >= needed
    if kind == "factions_honors_at_least":
        needed, min_honors = cond[1], cond[2]
        return count_factions_honors_at_least(snapshots, min_honors) >= needed
    if kind == "factions_achievement_id_contains_at_least":
        needed, substring = cond[1], cond[2]
        return count_factions_achievement_id_contains(snapshots, substring) >= needed
    return False


def _meta_achievement_met(defn: AchievementDef, snapshots: dict) -> bool:
    if not defn.conditions:
        return False
    return all(_meta_condition_met(c, snapshots) for c in defn.conditions)


def _condition_met(cond: Condition, ctx: AchievementContext, state: Optional[dict] = None) -> bool:
    kind = cond[0]
    if kind == "grade":
        return ctx.grade == cond[1]
    if kind == "victory":
        return ctx.victory
    if kind == "utilization_below":
        return ctx.victory and ctx.utilization_percent < cond[1]
    if kind == "defeated_ai":
        targets = cond[1] if isinstance(cond[1], tuple) else (cond[1],)
        normalized = {_normalize_defeat_tier(t) for t in targets}
        return any(_normalize_defeat_tier(t) in normalized for t in ctx.defeated_ai_types)
    if kind == "map":
        targets = cond[1] if isinstance(cond[1], tuple) else (cond[1],)
        return ctx.map_name in targets
    if kind == "defeated_ai_total_at_least":
        if state is None:
            return False
        needed, tiers = cond[1], cond[2]
        if not isinstance(tiers, tuple):
            tiers = (tiers,)
        return _defeat_total(state, tiers) >= needed
    if kind == "defeated_ai_map_at_least":
        if state is None:
            return False
        map_id, needed, tiers = cond[1], cond[2], cond[3]
        if not isinstance(tiers, tuple):
            tiers = (tiers,)
        return _map_defeat_total(state, map_id, tiers) >= needed
    if kind == "survival_at_least":
        return ctx.survival >= cond[1]
    if kind == "building_defense_at_least":
        return ctx.building_defense >= cond[1]
    if kind == "random_map":
        return ctx.is_random_map
    if kind == "victory_mode":
        return ctx.is_random_map and ctx.victory_mode == cond[1]
    if kind == "achievement":
        if state is None:
            return False
        return cond[1] in (state.get("unlocked") or {})
    if kind.startswith("factions_"):
        return False
    return False


def _achievement_met(defn: AchievementDef, ctx: AchievementContext, state: Optional[dict] = None) -> bool:
    if not defn.conditions:
        return False
    return all(_condition_met(c, ctx, state) for c in defn.conditions)


def _once_key(defn: AchievementDef, ctx: AchievementContext) -> str:
    if defn.once_mode == "map":
        return f"{defn.id}|map:{ctx.map_name}"
    if defn.once_mode == "map_ai":
        ai = ctx.primary_enemy_ai or "none"
        return f"{defn.id}|map:{ctx.map_name}|ai:{ai}"
    return defn.id


def _already_awarded(defn: AchievementDef, state: dict, ctx: AchievementContext) -> bool:
    once_keys = state.get("once_keys") or {}
    return bool(once_keys.get(_once_key(defn, ctx)))


def _mark_awarded(defn: AchievementDef, state: dict, ctx: AchievementContext) -> List[str]:
    once_keys = state.setdefault("once_keys", {})
    once_keys[_once_key(defn, ctx)] = True
    unlocked = state.setdefault("unlocked", {})
    entry = unlocked.setdefault(defn.id, {"count": 0, "first_at": None, "last_at": None})
    now = int(time.time())
    entry["count"] = int(entry.get("count", 0)) + 1
    if not entry.get("first_at"):
        entry["first_at"] = now
    entry["last_at"] = now
    return _apply_rewards(defn, state)


def grant_card(state: dict, card_id: str, times: int = 1) -> int:
    """Grant inventory charges; returns charges actually added (0 if unknown card)."""
    if not card_exists(card_id):
        warning("unknown reward card: %s", card_id)
        return 0
    card = get_card(card_id)
    if card is None:
        return 0
    added = card.grant_charges * max(1, times)
    cards = state.setdefault("cards", {})
    entry = cards.setdefault(card_id, {"charges": 0, "total_earned": 0})
    entry["charges"] = int(entry.get("charges", 0)) + added
    entry["total_earned"] = int(entry.get("total_earned", 0)) + added
    return added


def grant_honor(state: dict, title_id: str, achievement_title: Optional[List] = None) -> bool:
    """Grant an honor title; returns True if newly added."""
    if not title_exists(title_id):
        warning("unknown reward title: %s", title_id)
        return False
    title = get_title(title_id)
    if title is None or title.kind != KIND_HONOR:
        warning("reward title is not an honor: %s", title_id)
        return False
    if achievement_title and title.title and tuple(title.title) == tuple(achievement_title):
        return False
    honors = state.setdefault("honors", [])
    if title_id in honors:
        return False
    honors.append(title_id)
    return True


def _apply_rewards(defn: AchievementDef, state: dict) -> List[str]:
    """Apply rewards; returns honor title ids newly granted."""
    new_honors = []
    for reward in defn.rewards:
        if reward[0] == "medal":
            state["medals"] = int(state.get("medals", 0)) + int(reward[1])
        elif reward[0] == "card":
            grant_card(state, reward[1], reward[2] if len(reward) > 2 else 1)
        elif reward[0] == "title":
            if grant_honor(state, reward[1], defn.title):
                new_honors.append(reward[1])
    return new_honors


def _grade_msgpart(letter: str) -> list:
    parts = {
        "S": mp.SCORE_GRADE_S,
        "A": mp.SCORE_GRADE_A,
        "B": mp.SCORE_GRADE_B,
        "C": mp.SCORE_GRADE_C,
        "D": mp.SCORE_GRADE_D,
        "E": mp.SCORE_GRADE_E,
    }
    key = str(letter).upper()
    if key in parts:
        return list(parts[key])
    return nb2msg(letter)


def _map_label_msgs(map_id: str) -> List:
    try:
        from .lib.resource import res

        for map_obj in res.maps():
            if getattr(map_obj, "name", None) == map_id:
                title = getattr(map_obj, "title", None)
                if title:
                    return list(title)
    except Exception:
        pass
    return [map_id.replace("_", " ")]


def _condition_requirement_msgs(cond: Condition) -> List[list]:
    kind = cond[0]
    if kind == "grade":
        return list(mp.ACHIEVEMENT_REQUIRES) + list(mp.SCORE_GRADE) + list(_grade_msgpart(cond[1]))
    if kind == "victory":
        return list(mp.ACHIEVEMENT_REQUIRES) + list(mp.ACHIEVEMENT_REQ_VICTORY)
    if kind == "utilization_below":
        return (
            list(mp.ACHIEVEMENT_REQUIRES)
            + list(mp.SCORE_EFFICIENCY)
            + list(mp.ACHIEVEMENT_BELOW)
            + nb2msg(int(cond[1]))
            + list(mp.PERCENT)
        )
    if kind == "defeated_ai":
        targets = cond[1] if isinstance(cond[1], tuple) else (cond[1],)
        from .definitions import ai_player_label

        parts = list(mp.ACHIEVEMENT_REQUIRES) + list(mp.SCORE_DEFEATED)
        for index, ai_type in enumerate(targets):
            if index:
                parts += list(mp.ACHIEVEMENT_OR)
            parts += list(ai_player_label(ai_type))
        return parts
    if kind == "map":
        targets = cond[1] if isinstance(cond[1], tuple) else (cond[1],)
        parts = list(mp.ACHIEVEMENT_REQUIRES) + list(mp.ACHIEVEMENT_ON_MAP)
        for index, map_id in enumerate(targets):
            if index:
                parts += list(mp.ACHIEVEMENT_OR)
            parts += _map_label_msgs(map_id)
        return parts
    if kind == "defeated_ai_total_at_least":
        needed, tiers = cond[1], cond[2]
        if not isinstance(tiers, tuple):
            tiers = (tiers,)
        from .definitions import ai_player_label

        parts = list(mp.ACHIEVEMENT_REQUIRES) + list(mp.SCORE_DEFEATED)
        for index, ai_type in enumerate(tiers):
            if index:
                parts += list(mp.ACHIEVEMENT_OR)
            parts += list(ai_player_label(ai_type))
        parts += list(mp.ACHIEVEMENT_AT_LEAST) + nb2msg(int(needed)) + list(mp.ACHIEVEMENT_TIMES)
        return parts
    if kind == "defeated_ai_map_at_least":
        map_id, needed, tiers = cond[1], cond[2], cond[3]
        if not isinstance(tiers, tuple):
            tiers = (tiers,)
        from .definitions import ai_player_label

        parts = list(mp.ACHIEVEMENT_REQUIRES) + list(mp.ACHIEVEMENT_ON_MAP) + _map_label_msgs(map_id)
        parts += list(mp.SCORE_DEFEATED)
        for index, ai_type in enumerate(tiers):
            if index:
                parts += list(mp.ACHIEVEMENT_OR)
            parts += list(ai_player_label(ai_type))
        parts += list(mp.ACHIEVEMENT_AT_LEAST) + nb2msg(int(needed)) + list(mp.ACHIEVEMENT_TIMES)
        return parts
    if kind == "survival_at_least":
        return (
            list(mp.ACHIEVEMENT_REQUIRES)
            + list(mp.SCORE_SURVIVAL)
            + list(mp.ACHIEVEMENT_AT_LEAST)
            + nb2msg(int(cond[1]))
            + list(mp.SCORE_POINTS)
        )
    if kind == "building_defense_at_least":
        return (
            list(mp.ACHIEVEMENT_REQUIRES)
            + list(mp.SCORE_BUILDING_DEFENSE)
            + list(mp.ACHIEVEMENT_AT_LEAST)
            + nb2msg(int(cond[1]))
            + list(mp.SCORE_POINTS)
        )
    if kind == "random_map":
        return list(mp.ACHIEVEMENT_REQUIRES) + list(mp.RMG_RANDOM_MAP)
    if kind == "victory_mode":
        mode = cond[1]
        parts = list(mp.ACHIEVEMENT_REQUIRES) + list(mp.ACHIEVEMENT_ON_RANDOM_MAP)
        mode_msgs = _VICTORY_MODE_MSGPARTS.get(mode)
        if mode_msgs:
            parts += list(mode_msgs)
        else:
            parts += nb2msg(mode)
        return parts
    if kind == "achievement":
        aid = cond[1]
        defn = _achievements.get(aid)
        title = list(defn.title) if defn and defn.title else nb2msg(aid)
        return list(mp.ACHIEVEMENT_PREREQ) + title
    if kind == "factions_unlocked_at_least":
        needed, min_unlocked = cond[1], cond[2]
        return (
            list(mp.ACHIEVEMENT_REQUIRES)
            + list(mp.ACHIEVEMENT_AT_LEAST)
            + nb2msg(int(needed))
            + list(mp.META_FACTIONS)
            + list(mp.META_EACH_UNLOCK_AT_LEAST)
            + nb2msg(int(min_unlocked))
            + list(mp.META_ACHIEVEMENT_ITEMS)
        )
    if kind == "factions_medals_at_least":
        needed, min_medals = cond[1], cond[2]
        return (
            list(mp.ACHIEVEMENT_REQUIRES)
            + list(mp.ACHIEVEMENT_AT_LEAST)
            + nb2msg(int(needed))
            + list(mp.META_FACTIONS)
            + list(mp.META_MEDALS_AT_LEAST)
            + nb2msg(int(min_medals))
            + list(mp.REWARD_MEDAL)
        )
    if kind == "factions_honors_at_least":
        needed, min_honors = cond[1], cond[2]
        parts = (
            list(mp.ACHIEVEMENT_REQUIRES)
            + list(mp.ACHIEVEMENT_AT_LEAST)
            + nb2msg(int(needed))
            + list(mp.META_FACTIONS)
            + list(mp.META_EACH_HAS_HONOR)
        )
        if int(min_honors) > 1:
            parts += list(mp.ACHIEVEMENT_AT_LEAST) + nb2msg(int(min_honors))
        return parts
    if kind == "factions_achievement_id_contains_at_least":
        needed, _substring = cond[1], cond[2]
        return (
            list(mp.ACHIEVEMENT_REQUIRES)
            + list(mp.ACHIEVEMENT_AT_LEAST)
            + nb2msg(int(needed))
            + list(mp.META_FACTIONS)
            + list(mp.META_MAP_MILESTONE)
        )
    return []


def achievement_requirement_msgs(defn: AchievementDef) -> List[list]:
    """TTS requirement summary for locked achievements in the list menu."""
    if not defn.conditions:
        return []
    parts: List[list] = []
    for index, cond in enumerate(defn.conditions):
        chunk = _condition_requirement_msgs(cond)
        if not chunk:
            continue
        if parts:
            parts += list(mp.AND)
        # Drop repeated leading ACHIEVEMENT_REQUIRES on subsequent conditions.
        if index and chunk[:1] == list(mp.ACHIEVEMENT_REQUIRES):
            chunk = chunk[len(mp.ACHIEVEMENT_REQUIRES) :]
        parts += chunk
    return parts


def evaluate_new_unlocks(
    ctx: AchievementContext,
    state: Optional[dict] = None,
    faction=None,
) -> Tuple[List[AchievementDef], List[str]]:
    if state is None:
        state = load_unlock_state(faction)
    newly = []
    new_honors = []
    for aid in _achievements_order:
        defn = _achievements.get(aid)
        if defn is None:
            continue
        if defn.scope == "meta":
            continue
        if not definition_matches_faction(defn.faction, faction, defn.scope):
            continue
        if _already_awarded(defn, state, ctx):
            continue
        if not _achievement_met(defn, ctx, state):
            continue
        new_honors.extend(_mark_awarded(defn, state, ctx))
        newly.append(defn)
    return newly, new_honors


def _empty_meta_context() -> AchievementContext:
    return AchievementContext(
        victory=True,
        grade="",
        utilization_percent=0,
        survival=0,
        building_defense=0,
        map_name="",
        defeated_ai_types=[],
        primary_enemy_ai=None,
    )


def evaluate_meta_unlocks(snapshots: Optional[dict] = None) -> Tuple[List[AchievementDef], List[str], dict, bool]:
    """Evaluate cross-faction meta achievements; returns (newly, honors, state, changed)."""
    from .meta_progress import load_faction_snapshots, load_meta_state, meta_enabled

    if not meta_enabled():
        return [], [], load_meta_state(), False
    if snapshots is None:
        snapshots = load_faction_snapshots()
    state = load_meta_state()
    ctx = _empty_meta_context()
    newly = []
    new_honors = []
    for aid in _achievements_order:
        defn = _achievements.get(aid)
        if defn is None or defn.scope != "meta":
            continue
        if _already_awarded(defn, state, ctx):
            continue
        if not _meta_achievement_met(defn, snapshots):
            continue
        new_honors.extend(_mark_awarded(defn, state, ctx))
        newly.append(defn)
    return newly, new_honors, state, bool(newly)


def evaluate_repeat_completions(
    ctx: AchievementContext,
    state: dict,
    faction=None,
) -> List[AchievementDef]:
    """Achievements already awarded for this once-key but met again with repeat_medal > 0."""
    repeats = []
    for aid in _achievements_order:
        defn = _achievements.get(aid)
        if defn is None or defn.repeat_medal <= 0:
            continue
        if defn.scope == "meta":
            continue
        if not definition_matches_faction(defn.faction, faction, defn.scope):
            continue
        if not _already_awarded(defn, state, ctx):
            continue
        if not _achievement_met(defn, ctx, state):
            continue
        repeats.append(defn)
    return repeats


def apply_repeat_medals(repeats: List[AchievementDef], state: dict) -> int:
    total = sum(max(0, int(defn.repeat_medal)) for defn in repeats)
    if total:
        state["medals"] = int(state.get("medals", 0)) + total
    return total


def repeat_medal_msgs(repeats: List[AchievementDef]) -> List[list]:
    msgs = []
    for defn in repeats:
        amount = int(defn.repeat_medal)
        if amount <= 0:
            continue
        title = list(defn.title) if defn.title else nb2msg(defn.id)
        msgs.append(
            mp.REPEAT_ACHIEVEMENT
            + title
            + mp.COMMA
            + mp.REWARD_MEDAL_GAINED
            + nb2msg(amount)
            + mp.REWARD_MEDAL
        )
    return msgs


def achievement_unlock_msgs(newly: List[AchievementDef]) -> List[list]:
    msgs = []
    for defn in newly:
        title = defn.title or nb2msg(defn.id)
        msgs.append(mp.ACHIEVEMENT_UNLOCKED + title)
    return msgs


def achievement_reward_msgs(newly: List[AchievementDef], state: dict, new_honors: Optional[List[str]] = None) -> List[list]:
    """Reward lines for this unlock batch (read state after apply)."""
    msgs = []
    for defn in newly:
        for reward in defn.rewards:
            if reward[0] == "title":
                title_id = reward[1]
                if title_id not in (new_honors or []):
                    continue
                honor = get_title(title_id)
                if honor and honor.title:
                    msgs.append(mp.REWARD_HONOR_GAINED + list(honor.title))
                continue
            if reward[0] == "medal":
                msgs.append(
                    mp.REWARD_MEDAL_GAINED + nb2msg(int(reward[1])) + mp.REWARD_MEDAL
                )
            elif reward[0] == "card":
                card_id = reward[1]
                card = get_card(card_id)
                title = list(card.title) if card and card.title else nb2msg(card_id)
                charges = state.get("cards", {}).get(card_id, {}).get("charges", 0)
                msgs.append(
                    mp.REWARD_CARD_GAINED
                    + title
                    + mp.COMMA
                    + mp.REWARD_CARD_CHARGES
                    + nb2msg(charges)
                )
    return msgs


def rank_promotion_msgs(medals_before: int, medals_after: int, faction=None) -> List[list]:
    msgs = []
    for rank in ranks_newly_reached(medals_before, medals_after, faction):
        if rank.title:
            msgs.append(mp.RANK_PROMOTED + list(rank.title))
        prev_slots = get_loadout_slots(max(0, rank.medals - 1), faction)
        new_slots = int(rank.loadout_slots)
        if new_slots > prev_slots:
            msgs.append(
                mp.LOADOUT_SLOTS_INCREASED
                + nb2msg(new_slots)
                + mp.LOADOUT_SLOT_SUFFIX
            )
    return msgs


def _is_campaign_game(game) -> bool:
    if game is None:
        return False
    checker = getattr(game, "is_campaign_session", None)
    if callable(checker):
        return bool(checker())
    if getattr(game, "is_coop_campaign", False):
        return True
    if getattr(game, "game_type_name", "") == "mission":
        return True
    world = getattr(game, "world", None)
    return bool(getattr(world, "is_campaign", False))


def _is_multiplayer_game(game) -> bool:
    if game is None:
        return False
    return getattr(game, "game_type_name", "") == "multiplayer"


def process_game_end_achievements(game, player) -> List[list]:
    """本局结束后判定成就；返回应播报的消息列表（不含 flush）。"""
    if not achievements_enabled():
        return []
    if _is_campaign_game(game):
        return []
    if _is_multiplayer_game(game):
        ctx = build_context(player, game)
        if not ctx.is_random_map:
            return []
    if player is None:
        return []
    if getattr(player, "is_spectator", False):
        return []
    if not hasattr(player, "stats"):
        return []
    faction = getattr(player, "faction", None)
    ctx = build_context(player, game)
    state = load_unlock_state(faction)
    medals_before = int(state.get("medals", 0))
    progress_changed = record_defeat_progress(ctx, state)
    newly, new_honors = evaluate_new_unlocks(ctx, state, faction)
    repeats = evaluate_repeat_completions(ctx, state, faction)
    repeat_total = apply_repeat_medals(repeats, state)
    medals_after = int(state.get("medals", 0))
    msgs = achievement_unlock_msgs(newly)
    if newly:
        msgs.extend(achievement_reward_msgs(newly, state, new_honors))
    if repeats:
        msgs.extend(repeat_medal_msgs(repeats))
    msgs.extend(rank_promotion_msgs(medals_before, medals_after, faction))
    faction_changed = bool(newly or repeat_total > 0 or progress_changed)
    if faction_changed:
        save_unlock_state(state, faction)

    meta_msgs: List[list] = []
    meta_newly, meta_honors, meta_state, meta_changed = evaluate_meta_unlocks()
    if meta_changed:
        save_meta_state(meta_state)
        meta_msgs = achievement_unlock_msgs(meta_newly)
        meta_msgs.extend(achievement_reward_msgs(meta_newly, meta_state, meta_honors))

    return msgs + meta_msgs


def build_current_rank_msgs(faction=None) -> List[list]:
    """Menu / intro line: current rank from saved medals."""
    if not achievements_enabled():
        return []
    if achievements_per_faction_enabled() and len(rules.factions) > 1 and normalize_faction_key(faction) is None:
        return []
    state = load_unlock_state(faction)
    medals = int(state.get("medals", 0))
    rank = get_current_rank(medals, faction)
    if rank is None or not rank.title:
        return []
    return [mp.ARMORY_RANK + list(rank.title)]


def get_inventory_summary(faction=None) -> dict:
    state = load_unlock_state(faction)
    medals = int(state.get("medals", 0))
    rank = get_current_rank(medals, faction)
    return {
        "medals": medals,
        "cards": dict(state.get("cards", {})),
        "honors": list(state.get("honors", [])),
        "rank_id": rank.id if rank else None,
        "medals_to_next_rank": medals_until_next_rank(medals),
    }
