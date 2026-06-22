"""Post-game multi-dimensional score breakdown."""

from types import SimpleNamespace

from soundrts import msgparts as mp
from soundrts.lib.nofloat import to_int
from soundrts.worldplayerstats import OUTCOME_MAX, SCORE_BASE_MAX, SCORE_MAX, Stats


class _Player:
    def __init__(
        self,
        *,
        victory=False,
        resources=None,
        starting=None,
        allied=None,
        is_campaign=False,
        map_capacity=None,
    ):
        self.has_victory = victory
        self.resources = list(resources or [0, 0])
        self._starting_resources = list(starting if starting is not None else self.resources)
        self.allied = allied or [self]
        self.neutral = False
        self.world = SimpleNamespace(
            players=[self],
            ex_players=[],
            map_deposit_capacity=list(map_capacity or [to_int("1000"), 0]),
            time=120000,
            is_campaign=is_campaign,
        )
        self.stats = None


class _Enemy(_Player):
    pass


class _ComputerEnemy(_Player):
    is_computer_player = True

    def __init__(self, ai_type, defeated=True, **kwargs):
        super().__init__(**kwargs)
        self.AI_type = ai_type
        self.has_been_defeated = defeated


def _stats(**kwargs):
    player = _Player(**kwargs)
    stats = Stats(player)
    player.stats = stats
    return stats


def test_victory_outcome_score():
    stats = _stats(victory=True)
    assert stats.score_breakdown()["outcome"] == OUTCOME_MAX


def test_defeat_outcome_score():
    stats = _stats(victory=False)
    assert stats.score_breakdown()["outcome"] == 0


def test_mining_score_from_map_capacity():
    stats = _stats(victory=True, resources=[0, 0], starting=[0, 0])
    stats.add("gathered", 0, to_int("500"))
    breakdown = stats.score_breakdown()
    assert breakdown["mining"] == 50


def test_mining_excludes_starting_resources():
    stats = _stats(victory=True, resources=[to_int("200"), 0], starting=[to_int("200"), 0])
    stats.add("gathered", 0, to_int("500"))
    breakdown = stats.score_breakdown()
    assert breakdown["mining"] == 30


def test_campaign_victory_without_deposits_full_mining_score():
    stats = _stats(victory=True, map_capacity=[0, 0], is_campaign=True)
    assert stats.score_breakdown()["mining"] == 100


def test_campaign_defeat_without_deposits_zero_mining_score():
    stats = _stats(victory=False, map_capacity=[0, 0], is_campaign=True)
    assert stats.score_breakdown()["mining"] == 0


def test_mining_without_map_capacity_zero_if_no_gather():
    stats = _stats(victory=True, map_capacity=[0, 0])
    assert stats.score_breakdown()["mining"] == 0


def test_mining_without_map_capacity_proportional_to_gather():
    stats = _stats(victory=True, resources=[0, 0], starting=[0, 0], map_capacity=[0, 0])
    stats.add("gathered", 0, to_int("500"))
    assert stats.score_breakdown()["mining"] == 50


def test_survival_zero_without_unit_production():
    stats = _stats(victory=True)
    assert stats.score_breakdown()["survival"] == 0


def test_percent_based_on_base_total_not_ai_bonus():
    player = _stats(victory=True)
    enemy = _ComputerEnemy("nightmare")
    enemy.stats = Stats(enemy)
    player.player.allied = [player.player]
    player.player.world.players = [player.player, enemy]
    breakdown = player.score_breakdown()
    assert breakdown["ai_defeat"] == 200
    assert breakdown["total"] == breakdown["base_total"] + 200
    assert breakdown["max"] == SCORE_BASE_MAX
    assert breakdown["percent"] == min(100, breakdown["base_total"] * 100 // SCORE_BASE_MAX)


def test_frugal_victory_boosts_efficiency():
    stats = _stats(victory=True, resources=[to_int("950"), 0], starting=[0, 0])
    stats.add("gathered", 0, to_int("1000"))
    breakdown = stats.score_breakdown()
    assert breakdown["utilization_percent"] == 5
    assert breakdown["efficiency"] == 95
    assert breakdown["efficiency_mode"] == "frugal"


def test_utilization_efficiency_mode_on_defeat():
    stats = _stats(victory=False, resources=[to_int("500"), 0], starting=[0, 0])
    stats.add("gathered", 0, to_int("1000"))
    breakdown = stats.score_breakdown()
    assert breakdown["efficiency_mode"] == "utilization"
    assert breakdown["efficiency"] == 50


def test_building_defense_penalty():
    stats = _stats(victory=True)
    stats.add("lost", "building", 3)
    assert stats.score_breakdown()["building_defense"] == 85


def test_demolition_score():
    stats = _stats(victory=True)
    stats.add("killed", "building", 4)
    assert stats.score_breakdown()["demolition"] == 20


def test_combat_relative_to_enemy_production():
    player = _stats(victory=True)
    enemy = _Enemy(victory=False, resources=[0, 0], starting=[0, 0])
    enemy.stats = Stats(enemy)
    enemy.stats.add("produced", "unit", 10)
    player.player.allied = [player.player]
    player.player.world.players = [player.player, enemy]
    player.add("killed", "unit", 5)
    assert player.score_breakdown()["combat"] == 50


def test_total_score_is_sum_of_categories():
    stats = _stats(victory=True)
    stats.add("gathered", 0, to_int("1000"))
    stats.add("produced", "unit", 10)
    stats.add("lost", "unit", 2)
    stats.add("killed", "unit", 3)
    stats.add("killed", "building", 1)
    breakdown = stats.score_breakdown()
    assert breakdown["total"] == breakdown["base_total"] + breakdown["ai_defeat"]
    assert breakdown["base_total"] == sum(
        breakdown[k]
        for k in (
            "outcome",
            "mining",
            "efficiency",
            "survival",
            "building_defense",
            "combat",
            "demolition",
        )
    )
    assert breakdown["max"] == SCORE_BASE_MAX


def test_defeated_beginner_computer_adds_ten_points():
    player = _stats(victory=True)
    enemy = _ComputerEnemy("beginner")
    enemy.stats = Stats(enemy)
    player.player.allied = [player.player]
    player.player.world.players = [player.player, enemy]
    breakdown = player.score_breakdown()
    assert breakdown["ai_defeat"] == 10
    assert breakdown["total"] == breakdown["base_total"] + 10
    assert breakdown["max"] == SCORE_BASE_MAX
    assert breakdown["percent"] == min(100, breakdown["base_total"] * 100 // SCORE_BASE_MAX)


def test_defeated_computer_in_ex_players_still_counts():
    player = _stats(victory=True)
    enemy = _ComputerEnemy("beginner")
    enemy.stats = Stats(enemy)
    player.player.allied = [player.player]
    player.player.world.ex_players = [enemy]
    player.player.world.players = [player.player]
    breakdown = player.score_breakdown()
    assert breakdown["ai_defeat"] == 10


def test_defeated_nightmare_computer_adds_two_hundred_points():
    player = _stats(victory=True)
    enemy = _ComputerEnemy("nightmare")
    enemy.stats = Stats(enemy)
    player.player.allied = [player.player]
    player.player.world.players = [player.player, enemy]
    breakdown = player.score_breakdown()
    assert breakdown["ai_defeat"] == 200


def test_campaign_timer_ai_does_not_add_defeat_bonus():
    player = _stats(victory=True)
    enemy = _ComputerEnemy("timers")
    enemy.stats = Stats(enemy)
    player.player.allied = [player.player]
    player.player.world.players = [player.player, enemy]
    assert player.score_breakdown()["ai_defeat"] == 0


def test_allied_computer_does_not_add_defeat_bonus():
    player = _stats(victory=True)
    ally = _ComputerEnemy("expert")
    ally.stats = Stats(ally)
    player.player.allied = [player.player, ally]
    player.player.world.players = [player.player, ally]
    assert player.score_breakdown()["ai_defeat"] == 0


def test_grade_s_for_high_total():
    stats = _stats(victory=True)
    assert stats.score_grade_msg(720) == mp.SCORE_GRADE_S
    assert stats.score_grade_msg(800) == mp.SCORE_GRADE_S


def test_grade_a_for_solid_total():
    stats = _stats(victory=True)
    assert stats.score_grade_msg(640) == mp.SCORE_GRADE_A
    assert stats.score_grade_msg(719) == mp.SCORE_GRADE_A


def test_grade_e_for_low_total():
    stats = _stats(victory=False)
    assert stats.score_grade_msg(100) == mp.SCORE_GRADE_E


def test_defeat_caps_grade_at_d():
    defeat = _stats(victory=False)
    victory = _stats(victory=True)
    assert defeat.score_grade_letter(600) == "D"
    assert victory.score_grade_letter(600) == "B"


def test_defeat_grade_total_capped_in_breakdown():
    stats = _stats(victory=False)
    stats.add("gathered", 0, to_int("1000"))
    stats.add("produced", "unit", 10)
    stats.add("killed", "unit", 10)
    stats.add("killed", "building", 10)
    breakdown = stats.score_breakdown()
    assert breakdown["total"] >= 480
    assert breakdown["grade_total"] == min(breakdown["total"], 479)
    assert stats.score_grade_letter() == "D"


def test_defeat_at_479_is_d():
    stats = _stats(victory=False)
    assert stats.score_grade_letter(479) == "D"


def test_defeat_at_480_raw_total_still_grade_d():
    stats = _stats(victory=False)
    assert stats.score_grade_letter(480) == "D"
    assert stats.score_grade_letter(600) == "D"


def test_score_msgs_uses_frugal_label():
    stats = _stats(victory=True, resources=[to_int("950"), 0], starting=[0, 0])
    stats.add("gathered", 0, to_int("1000"))
    flat = []
    for msg in stats.score_msgs():
        flat.extend(msg if isinstance(msg, list) else [msg])
    assert mp.SCORE_FRUGAL_EFFICIENCY[0] in flat
    assert mp.SCORE_EFFICIENCY[0] not in flat


def test_per_resource_mining_score():
    stats = _stats(victory=True, resources=[0, 0], starting=[0, 0])
    stats.add("gathered", 0, to_int("500"))
    breakdown = stats.score_breakdown()
    assert breakdown["mining_by_resource"][0] == 50
    assert breakdown["mining_by_resource"][1] == 0


def test_unit_and_building_line_scores():
    stats = _stats(victory=False)
    stats.add("produced", "unit", 1)
    stats.add("produced", "building", 2)
    stats.add("killed", "unit", 3)
    stats.add("killed", "building", 1)
    breakdown = stats.score_breakdown()
    assert breakdown["unit_line"] == breakdown["survival"] + breakdown["combat"]
    assert breakdown["building_line"] == breakdown["building_defense"] + breakdown["demolition"]
