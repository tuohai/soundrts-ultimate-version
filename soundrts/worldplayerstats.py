from . import msgparts as mp
from soundrts.lib.nofloat import PRECISION, to_int
from .definitions import ai_player_label, get_ai_defeat_score, style
from .lib.msgs import nb2msg


# 胜负权重 ×2；其余六项各 0–100，基础满分 800；击败电脑另计奖励分。
SCORE_BASE_MAX = 800
SCORE_MAX = SCORE_BASE_MAX
OUTCOME_MAX = 200
CATEGORY_MAX = 100
DEFEAT_GRADE_MAX_TOTAL = 479  # 失败局字母评级最高 D（C 门槛 480）

_GRADE_TABLE = (
    (720, mp.SCORE_GRADE_S),
    (640, mp.SCORE_GRADE_A),
    (560, mp.SCORE_GRADE_B),
    (480, mp.SCORE_GRADE_C),
    (400, mp.SCORE_GRADE_D),
    (0, mp.SCORE_GRADE_E),
)

MINING_REFERENCE_GATHER = to_int("1000")  # 无 map_deposit_capacity 时的采集参照量

_AI_NON_SCORING = frozenset({"timers", "ai2", ""})


def _clamp_score(value, maximum=CATEGORY_MAX):
    return max(0, min(maximum, int(value)))


class Stats:
    _game_duration = None

    def __init__(self, player):
        self._stats = {}
        self.player = player

    @property
    def game_duration(self):
        if self._game_duration is not None:
            return self._game_duration
        else:
            return self.player.world.time

    def freeze(self):
        self._game_duration = self.player.world.time

    def add(self, event, target, inc=1):
        if target is not None:
            stat = (event, target)
            try:
                self._stats[stat] += inc
            except KeyError:
                self._stats[stat] = inc

    def get(self, event, target):
        return self._stats.get((event, target), 0)

    def consumed(self, i):
        return self.get("gathered", i) - self.player.resources[i]

    def _starting_resources(self):
        return getattr(self.player, "_starting_resources", None) or [0] * len(
            self.player.resources
        )

    def _resource_capacity(self, i):
        caps = getattr(self.player.world, "map_deposit_capacity", None) or []
        if i < len(caps):
            return caps[i]
        return 0

    def _map_resource_capacity(self):
        caps = getattr(self.player.world, "map_deposit_capacity", None)
        if not caps:
            return 0
        return sum(caps)

    def _map_resources_gathered(self):
        total = 0
        starting = self._starting_resources()
        for i, _ in enumerate(self.player.resources):
            total += max(0, self.get("gathered", i) - starting[i])
        return total

    def _total_gathered(self):
        return sum(self.get("gathered", i) for i, _ in enumerate(self.player.resources))

    def _total_consumed(self):
        return sum(self.consumed(i) for i, _ in enumerate(self.player.resources))

    def _all_world_players(self):
        world = self.player.world
        return list(world.players) + list(getattr(world, "ex_players", []))

    def _is_enemy_player(self, other):
        if other is self.player:
            return False
        if other in getattr(self.player, "allied", ()):
            return False
        if getattr(other, "neutral", False):
            return False
        return True

    def _enemy_units_produced(self):
        total = 0
        for p in self._all_world_players():
            if self._is_enemy_player(p):
                total += p.stats.get("produced", "unit")
        return total

    def _is_scoring_computer(self, other):
        if not self._is_enemy_player(other):
            return False
        if not getattr(other, "has_been_defeated", False):
            return False
        ai_type = getattr(other, "AI_type", "") or ""
        if ai_type in _AI_NON_SCORING:
            return False
        if get_ai_defeat_score(ai_type) <= 0:
            return False
        return getattr(other, "is_computer_player", False)

    def _defeated_computer_entries(self, enemy_ids=None):
        grouped = {}
        for p in self._all_world_players():
            if enemy_ids is not None and p.id not in enemy_ids:
                continue
            if not self._is_scoring_computer(p):
                continue
            ai_type = p.AI_type
            points = get_ai_defeat_score(ai_type)
            if points <= 0:
                continue
            if ai_type not in grouped:
                grouped[ai_type] = {"ai_type": ai_type, "count": 0, "points": 0}
            grouped[ai_type]["count"] += 1
            grouped[ai_type]["points"] += points
        return sorted(grouped.values(), key=lambda e: -e["points"])

    def _defeated_computer_score(self, enemy_ids=None):
        return sum(entry["points"] for entry in self._defeated_computer_entries(enemy_ids))

    def _mining_score_for_resource(self, i):
        capacity = self._resource_capacity(i)
        starting = self._starting_resources()
        mined = max(0, self.get("gathered", i) - starting[i])
        if capacity > 0:
            return _clamp_score(mined * CATEGORY_MAX / capacity)
        if mined <= 0:
            return 0
        if self._map_resource_capacity() > 0:
            return 0
        return _clamp_score(mined * CATEGORY_MAX / MINING_REFERENCE_GATHER)

    def _mining_score(self):
        capacity = self._map_resource_capacity()
        if capacity <= 0:
            world = self.player.world
            if getattr(world, "is_campaign", False):
                return CATEGORY_MAX if self.player.has_victory else 0
            mined = self._map_resources_gathered()
            if mined <= 0:
                return 0
            return _clamp_score(mined * CATEGORY_MAX / MINING_REFERENCE_GATHER)
        mined = self._map_resources_gathered()
        return _clamp_score(mined * CATEGORY_MAX / capacity)

    def score_breakdown(self, effective_victory=None, scored_enemy_ids=None):
        """多维度评分：胜负 0–200，其余六项各 0–100，满分 800。"""
        victory = (
            self.player.has_victory
            if effective_victory is None
            else effective_victory
        )
        outcome = OUTCOME_MAX if victory else 0
        mining = self._mining_score()

        gathered = self._total_gathered()
        consumed = self._total_consumed()
        efficiency_mode = "utilization"
        if gathered > 0:
            ratio = consumed / gathered
            utilization_percent = _clamp_score(ratio * 100, maximum=100)
            if victory and ratio < 0.5:
                efficiency = _clamp_score((1 - ratio) * 100)
                efficiency_mode = "frugal"
            else:
                efficiency = _clamp_score(ratio * 100)
        else:
            utilization_percent = 0
            efficiency = 0

        produced_units = self.get("produced", "unit")
        lost_units = self.get("lost", "unit")
        if produced_units > 0:
            survival = _clamp_score(
                (produced_units - lost_units) * 100 / produced_units
            )
        else:
            survival = 0

        building_defense = max(0, 100 - self.get("lost", "building") * 5)

        units_killed = self.get("killed", "unit")
        enemy_units = self._enemy_units_produced()
        if enemy_units > 0:
            combat = _clamp_score(units_killed * 100 / enemy_units)
        else:
            combat = _clamp_score(units_killed * 5)

        demolition = _clamp_score(self.get("killed", "building") * 5)
        ai_defeat = self._defeated_computer_score(scored_enemy_ids)

        base_total = (
            outcome
            + mining
            + efficiency
            + survival
            + building_defense
            + combat
            + demolition
        )
        total = base_total + ai_defeat
        percent = _clamp_score(base_total * 100 / SCORE_BASE_MAX, maximum=100)
        grade_total = self._grade_total(total)
        return {
            "outcome": outcome,
            "mining": mining,
            "mining_by_resource": [
                self._mining_score_for_resource(i)
                for i, _ in enumerate(self.player.resources)
            ],
            "efficiency": efficiency,
            "efficiency_mode": efficiency_mode,
            "utilization_percent": utilization_percent,
            "survival": survival,
            "building_defense": building_defense,
            "combat": combat,
            "demolition": demolition,
            "unit_line": survival + combat,
            "building_line": building_defense + demolition,
            "ai_defeat": ai_defeat,
            "ai_defeat_entries": self._defeated_computer_entries(scored_enemy_ids),
            "base_total": base_total,
            "total": total,
            "grade_total": grade_total,
            "percent": percent,
            "max": SCORE_BASE_MAX,
        }

    def _grade_total(self, total):
        if self.player.has_victory:
            return total
        return min(total, DEFEAT_GRADE_MAX_TOTAL)

    def score_grade_msg(self, total=None):
        if total is None:
            total = self.score_breakdown()["grade_total"]
        else:
            total = self._grade_total(total)
        for threshold, grade_msg in _GRADE_TABLE:
            if total >= threshold:
                return grade_msg
        return mp.SCORE_GRADE_E

    def score_grade_letter(self, total=None):
        if total is None:
            total = self.score_breakdown()["grade_total"]
        else:
            total = self._grade_total(total)
        if total >= 720:
            return "S"
        if total >= 640:
            return "A"
        if total >= 560:
            return "B"
        if total >= 480:
            return "C"
        if total >= 400:
            return "D"
        return "E"

    def score(self):
        return self.score_breakdown()["total"]

    def game_duration_in_minutes_seconds(self):
        t = self.game_duration // 1000
        m = int(t // 60)
        s = int(t - m * 60)
        return m, s

    def _score_plus(self, points):
        return mp.COMMA + mp.SCORE_PLUS + nb2msg(points) + mp.SCORE_POINTS

    def score_msgs(self, effective_victory=None, scored_enemy_ids=None):
        breakdown = self.score_breakdown(
            effective_victory=effective_victory,
            scored_enemy_ids=scored_enemy_ids,
        )
        victory = (
            self.player.has_victory
            if effective_victory is None
            else effective_victory
        )
        if victory:
            victory_or_defeat = mp.VICTORY
        else:
            victory_or_defeat = mp.DEFEAT
        minutes, seconds = self.game_duration_in_minutes_seconds()
        msgs = [
            victory_or_defeat
            + mp.AT
            + nb2msg(minutes)
            + mp.MINUTES
            + nb2msg(seconds)
            + mp.SECONDS
            + self._score_plus(breakdown["outcome"])
        ]
        msgs.append(
            nb2msg(self.get("produced", "unit"))
            + mp.UNITS
            + mp.PRODUCED_F
            + mp.COMMA
            + nb2msg(self.get("lost", "unit"))
            + mp.LOST
            + mp.COMMA
            + nb2msg(self.get("killed", "unit"))
            + mp.NEUTRALIZED
            + self._score_plus(breakdown["unit_line"])
        )
        msgs.append(
            nb2msg(self.get("produced", "building"))
            + mp.BUILDINGS
            + mp.PRODUCED_M
            + mp.COMMA
            + nb2msg(self.get("lost", "building"))
            + mp.LOST
            + mp.COMMA
            + nb2msg(self.get("killed", "building"))
            + mp.NEUTRALIZED
            + self._score_plus(breakdown["building_line"])
        )
        for i, _ in enumerate(self.player.resources):
            msgs.append(
                nb2msg(self.get("gathered", i) // PRECISION)
                + style.get("parameters", f"resource{i+1}_title")
                + mp.GATHERED
                + mp.COMMA
                + nb2msg(self.consumed(i) // PRECISION)
                + mp.CONSUMED
                + self._score_plus(breakdown["mining_by_resource"][i])
            )
        efficiency_label = (
            mp.SCORE_FRUGAL_EFFICIENCY
            if breakdown["efficiency_mode"] == "frugal"
            else mp.SCORE_EFFICIENCY
        )
        msgs.append(
            efficiency_label
            + nb2msg(breakdown["utilization_percent"])
            + mp.PERCENT
            + self._score_plus(breakdown["efficiency"])
        )
        for entry in breakdown["ai_defeat_entries"]:
            msg = mp.SCORE_DEFEATED + ai_player_label(entry["ai_type"])
            if entry["count"] > 1:
                msg += mp.COMMA + nb2msg(entry["count"])
            msgs.append(msg + self._score_plus(entry["points"]))
        msgs.append(
            mp.SCORE_TOTAL
            + nb2msg(breakdown["total"])
            + mp.COMMA
            + mp.SCORE_OUT_OF
            + nb2msg(breakdown["max"])
            + mp.COMMA
            + nb2msg(breakdown["percent"])
            + mp.PERCENT
        )
        msgs.append(
            mp.SCORE_GRADE + self.score_grade_msg(breakdown["total"]) + mp.HISTORY_EXPLANATION
        )
        return msgs
