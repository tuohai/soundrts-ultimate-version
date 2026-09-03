"""Adaptive AI brain: get-token order, scout matching, counter scores."""
from __future__ import annotations

from types import SimpleNamespace

from soundrts.ai_brain import (
    BEHAVIOR_TREE,
    MAX_ATTACK_FRONTS,
    SCOUT_THEN_PRODUCE_MS,
    assign_attack_groups,
    assign_attack_groups_with_home,
    choose_utility_goal,
    combat_enemies,
    inject_counter_pairs,
    iter_known_enemies,
    parse_get_pairs,
    peel_home_guard,
    reorder_get_pairs,
    score_utility_goals,
    sees_enemy_type,
    tick_behavior_tree,
    token_counter_score,
    token_is_army,
    unit_matches_type,
)


def test_parse_get_pairs_numbers_and_bare_names():
    assert parse_get_pairs(["8", "peasant", "5", "footman", "archer"]) == [
        (8, "peasant"),
        (5, "footman"),
        (1, "archer"),
    ]


def test_unit_matches_type_via_expanded_is_a():
    knight = SimpleNamespace(type_name="knight", expanded_is_a=("cavalry", "soldier"))
    assert unit_matches_type(knight, "knight")
    assert unit_matches_type(knight, "cavalry")
    assert not unit_matches_type(knight, "archer")


def test_iter_known_enemies_sorts_by_id_and_skips_friends():
    friend = SimpleNamespace(id=9, place=object(), type_name="footman")
    late = SimpleNamespace(id=7, place=object(), type_name="knight")
    early = SimpleNamespace(id=3, place=object(), type_name="archer")
    dead = SimpleNamespace(id=1, place=None, type_name="mage")
    player = SimpleNamespace(
        perception=[late, friend, dead],
        memory=[early],
        is_an_enemy=lambda o: o is not friend,
    )
    enemies = iter_known_enemies(player)
    assert [e.id for e in enemies] == [3, 7]


def test_sees_enemy_type_uses_is_a():
    knight = SimpleNamespace(
        id=1, place=object(), type_name="knight", expanded_is_a=("cavalry",)
    )
    player = SimpleNamespace(
        perception=[knight],
        memory=[],
        is_an_enemy=lambda _o: True,
        equivalent=lambda tn: tn,
    )
    assert sees_enemy_type(player, "cavalry")
    assert not sees_enemy_type(player, "dragon")


def test_reorder_get_pairs_puts_counter_ahead(monkeypatch):
    class _Spear:
        mdg_vs = {"knight": 20}
        rdg_vs = {}

    class _Archer:
        mdg_vs = {}
        rdg_vs = {"footman": 7}

    class _Peasant:
        mdg_vs = {}
        rdg_vs = {}

    def _unit_class(name):
        return {"spearman": _Spear, "archer": _Archer, "peasant": _Peasant}.get(name)

    monkeypatch.setattr("soundrts.ai_brain.rules.unit_class", _unit_class)
    knight = SimpleNamespace(type_name="knight", expanded_is_a=("cavalry",))
    pairs = [(8, "peasant"), (10, "archer"), (12, "spearman")]
    out = reorder_get_pairs(pairs, [knight], equivalent=lambda tn: tn)
    assert out[0] == (12, "spearman")
    assert (8, "peasant") in out
    assert out.index((8, "peasant")) > 0


def test_token_counter_score_zero_without_enemies(monkeypatch):
    monkeypatch.setattr("soundrts.ai_brain.rules.unit_class", lambda _n: None)
    assert token_counter_score("spearman", []) == 0


def test_token_is_army_skips_buildings_and_ferries(monkeypatch):
    class _Hall:
        is_a_building = True
        transport_capacity = 0

    class _Boat:
        is_a_building = False
        transport_capacity = 8

    class _Sword:
        is_a_building = False
        transport_capacity = 0

    def _unit_class(name):
        return {"hall": _Hall, "boat": _Boat, "sword": _Sword}.get(name)

    monkeypatch.setattr("soundrts.ai_brain.rules.unit_class", _unit_class)
    assert not token_is_army("hall")
    assert not token_is_army("boat")
    assert token_is_army("sword")


def test_combat_enemies_skips_buildings():
    hall = SimpleNamespace(type_name="townhall", is_a_building=True)
    knight = SimpleNamespace(type_name="knight", is_a_building=False)
    assert combat_enemies([hall, knight]) == [knight]


def test_inject_skips_villager_only_get_line(monkeypatch):
    class _Spear:
        mdg_vs = {"cavalry": 15}
        rdg_vs = {}
        is_a_building = False
        transport_capacity = 0

    monkeypatch.setattr(
        "soundrts.ai_brain.rules.unit_class",
        lambda n: _Spear if n == "spearman" else None,
    )
    knight = SimpleNamespace(type_name="knight", expanded_is_a=("cavalry",))
    out = inject_counter_pairs(
        [(8, "peasant")],
        [knight],
        ["spearman"],
        is_army=lambda n: n != "peasant",
    )
    assert out == [(8, "peasant")]


def test_inject_adds_best_counter_from_owned_trainers(monkeypatch):
    class _Spear:
        mdg_vs = {"cavalry": 15}
        rdg_vs = {}
        is_a_building = False
        transport_capacity = 0

    class _Skirm:
        mdg_vs = {}
        rdg_vs = {"archer_unit": 3}
        is_a_building = False
        transport_capacity = 0

    class _Foot:
        mdg_vs = {}
        rdg_vs = {}
        is_a_building = False
        transport_capacity = 0

    def _unit_class(name):
        return {
            "spearman": _Spear,
            "skirmisher": _Skirm,
            "footman": _Foot,
            "archer": _Foot,
        }.get(name)

    monkeypatch.setattr("soundrts.ai_brain.rules.unit_class", _unit_class)
    knight = SimpleNamespace(type_name="knight", expanded_is_a=("cavalry",))
    pairs = [(4, "footman"), (4, "archer")]
    out = inject_counter_pairs(
        pairs,
        [knight],
        ["skirmisher", "spearman"],
        is_army=lambda n: n not in ("peasant",),
    )
    assert out[-1] == (4, "spearman")
    assert (4, "footman") in out
    assert (4, "archer") in out


def test_inject_does_not_duplicate_type_already_on_line(monkeypatch):
    class _Spear:
        mdg_vs = {"cavalry": 15}
        rdg_vs = {}
        is_a_building = False
        transport_capacity = 0

    monkeypatch.setattr(
        "soundrts.ai_brain.rules.unit_class",
        lambda n: _Spear if n == "spearman" else None,
    )
    knight = SimpleNamespace(type_name="knight", expanded_is_a=("cavalry",))
    pairs = [(4, "spearman")]
    out = inject_counter_pairs(
        pairs,
        [knight],
        ["spearman"],
        is_army=lambda n: True,
    )
    assert out == [(4, "spearman")]


def test_utility_defend_beats_eco_when_attacked():
    player = SimpleNamespace(
        _attacked_this_play=True,
        _attacked_places=[],
        _workers=[object()] * 3,
        nb_workers_to_get=24,
        constant_attacks=1,
        _enemy_presence=["x"],
        units=[],
        perception=[],
        memory=[],
        is_an_enemy=lambda _o: True,
        _saving_food_for_age=lambda: False,
        _age_up_needs_food=lambda: False,
        _main_base_type_names=lambda: (),
    )
    assert choose_utility_goal(player) == "defend"
    assert score_utility_goals(player)["defend"] == 100


def test_utility_eco_when_few_workers_and_safe():
    player = SimpleNamespace(
        _attacked_this_play=False,
        _attacked_places=[],
        _workers=[object()] * 4,
        nb_workers_to_get=16,
        constant_attacks=1,
        _enemy_presence=["x"],
        units=[],
        perception=[],
        memory=[],
        is_an_enemy=lambda _o: True,
        _saving_food_for_age=lambda: False,
        _age_up_needs_food=lambda: False,
        _main_base_type_names=lambda: (),
    )
    assert choose_utility_goal(player) == "eco"


def test_utility_age_beats_attack_when_saving():
    player = SimpleNamespace(
        _attacked_this_play=False,
        _attacked_places=[],
        _workers=[object()] * 12,
        nb_workers_to_get=12,
        constant_attacks=1,
        _enemy_presence=["x"],
        units=[],
        perception=[],
        memory=[],
        is_an_enemy=lambda _o: True,
        _saving_food_for_age=lambda: True,
        _age_up_needs_food=lambda: True,
        _main_base_type_names=lambda: (),
    )
    assert choose_utility_goal(player) == "age"


def test_behavior_tree_node_order():
    assert [name for name, _pred in BEHAVIOR_TREE] == [
        "defend",
        "eco",
        "age",
        "scout",
        "eco",
        "attack",
        "produce",
    ]


def _tree_player(**kwargs):
    base = dict(
        _attacked_this_play=False,
        _attacked_places=[],
        _workers=[object()] * 8,
        nb_workers_to_get=16,
        constant_attacks=1,
        _enemy_presence=["x"],
        units=[],
        perception=[],
        memory=[],
        is_an_enemy=lambda _o: True,
        _saving_food_for_age=lambda: False,
        _age_up_needs_food=lambda: False,
        _main_base_type_names=lambda: (),
        world=SimpleNamespace(time=0),
        _scout_sequence_started=None,
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_tree_scouts_before_produce_when_no_army_seen():
    assert choose_utility_goal(_tree_player()) == "scout"


def test_tree_stops_scout_when_combat_enemy_seen():
    enemy = SimpleNamespace(
        id=1, place=object(), type_name="knight", is_a_building=False
    )
    player = _tree_player(perception=[enemy], is_an_enemy=lambda o: o is enemy)
    assert choose_utility_goal(player) == "eco"


def test_tree_stops_scout_after_timeout():
    player = _tree_player(
        world=SimpleNamespace(time=SCOUT_THEN_PRODUCE_MS),
        _scout_sequence_started=0,
        nb_workers_to_get=8,
        _workers=[object()] * 8,
        constant_attacks=0,
    )
    assert choose_utility_goal(player) == "produce"


def test_tree_opening_eco_still_beats_scout():
    player = _tree_player(_workers=[object()] * 4)
    assert choose_utility_goal(player) == "eco"


def test_tree_defends_home_even_with_few_workers():
    place = object()
    hall = SimpleNamespace(type_name="townhall", place=place)
    enemy = SimpleNamespace(id=1, place=place, type_name="knight")
    player = SimpleNamespace(
        _attacked_this_play=False,
        _attacked_places=[],
        _workers=[object()] * 3,
        nb_workers_to_get=24,
        constant_attacks=1,
        _enemy_presence=["x"],
        units=[hall],
        perception=[enemy],
        memory=[],
        is_an_enemy=lambda o: o is enemy,
        _saving_food_for_age=lambda: False,
        _age_up_needs_food=lambda: False,
        _main_base_type_names=lambda: ("townhall",),
    )
    assert tick_behavior_tree(player) == "defend"
    assert choose_utility_goal(player) == "defend"


def _u(uid, menace=10):
    return SimpleNamespace(id=uid, menace=menace)


def test_assign_attack_groups_splits_when_each_front_beats_ratio():
    a = SimpleNamespace(id=1)
    b = SimpleNamespace(id=2)
    units = [_u(1), _u(2), _u(3), _u(4)]
    groups = assign_attack_groups(
        [a, b],
        units,
        menace_of=lambda u: u.menace,
        enemy_menace=lambda _p: 15,
        ratio=100,
    )
    assert len(groups) == 2
    assert groups[0][0] is a
    assert [u.id for u in groups[0][1]] == [1, 2]
    assert groups[1][0] is b
    assert [u.id for u in groups[1][1]] == [3, 4]
    ids = [u.id for _p, grp in groups for u in grp]
    assert ids == [1, 2, 3, 4]


def test_assign_attack_groups_does_not_open_weak_second_front():
    a = SimpleNamespace(id=1)
    b = SimpleNamespace(id=2)
    units = [_u(1), _u(2), _u(3)]
    groups = assign_attack_groups(
        [a, b],
        units,
        menace_of=lambda u: u.menace,
        enemy_menace=lambda _p: 15,
        ratio=100,
    )
    assert len(groups) == 1
    assert groups[0][0] is a
    assert [u.id for u in groups[0][1]] == [1, 2, 3]


def test_assign_attack_groups_skips_uncoverable_first_place():
    a = SimpleNamespace(id=1)
    b = SimpleNamespace(id=2)
    units = [_u(1), _u(2)]
    groups = assign_attack_groups(
        [a, b],
        units,
        menace_of=lambda u: u.menace,
        enemy_menace=lambda p: 25 if p is a else 10,
        ratio=100,
    )
    assert len(groups) == 1
    assert groups[0][0] is b


def test_assign_attack_groups_caps_at_two_fronts():
    places = [SimpleNamespace(id=i) for i in (1, 2, 3)]
    units = [_u(i) for i in range(1, 7)]
    groups = assign_attack_groups(
        places,
        units,
        menace_of=lambda u: u.menace,
        enemy_menace=lambda _p: 15,
        ratio=100,
    )
    assert len(groups) == MAX_ATTACK_FRONTS
    leftover_ids = {u.id for u in groups[0][1]} | {u.id for u in groups[1][1]}
    assert leftover_ids == {1, 2, 3, 4, 5, 6}
    assert len(groups[0][1]) == 4
    assert len(groups[1][1]) == 2


def test_assign_attack_groups_max_fronts_one_folds_leftover():
    a = SimpleNamespace(id=1)
    b = SimpleNamespace(id=2)
    units = [_u(1), _u(2), _u(3), _u(4)]
    groups = assign_attack_groups(
        [a, b],
        units,
        menace_of=lambda u: u.menace,
        enemy_menace=lambda _p: 15,
        ratio=100,
        max_fronts=1,
    )
    assert len(groups) == 1
    assert groups[0][0] is a
    assert [u.id for u in groups[0][1]] == [1, 2, 3, 4]


def test_peel_home_guard_token_unit_when_home_quiet():
    home = SimpleNamespace(id=1)
    units = [_u(1), _u(2), _u(3)]
    h, guard, leftover = peel_home_guard(
        [home],
        units,
        menace_of=lambda u: u.menace,
        enemy_menace=lambda _p: 0,
        ratio=100,
    )
    assert h is home
    assert [u.id for u in guard] == [1]
    assert [u.id for u in leftover] == [2, 3]


def test_peel_home_guard_all_stay_when_cannot_hold():
    home = SimpleNamespace(id=1)
    units = [_u(1), _u(2)]
    h, guard, leftover = peel_home_guard(
        [home],
        units,
        menace_of=lambda u: u.menace,
        enemy_menace=lambda _p: 25,
        ratio=100,
    )
    assert h is home
    assert leftover == []
    assert [u.id for u in guard] == [1, 2]


def test_peel_home_guard_picks_threatened_hall():
    quiet = SimpleNamespace(id=1)
    hot = SimpleNamespace(id=2)
    units = [_u(1), _u(2), _u(3)]
    h, guard, leftover = peel_home_guard(
        [quiet, hot],
        units,
        menace_of=lambda u: u.menace,
        enemy_menace=lambda p: 15 if p is hot else 0,
        ratio=100,
    )
    assert h is hot
    assert [u.id for u in guard] == [1, 2]
    assert [u.id for u in leftover] == [3]


def test_peel_home_guard_keeps_stationed_unit_not_lowest_id():
    home = SimpleNamespace(id=1)
    barracks = SimpleNamespace(id=2)
    recruit = _u(1)
    recruit.place = barracks
    sentry = _u(9)
    sentry.place = home
    h, guard, leftover = peel_home_guard(
        [home],
        [recruit, sentry],
        menace_of=lambda u: u.menace,
        enemy_menace=lambda _p: 0,
        ratio=100,
    )
    assert h is home
    assert [u.id for u in guard] == [9]
    assert [u.id for u in leftover] == [1]


def test_peel_home_guard_keeps_unit_walking_home():
    home = SimpleNamespace(id=1)
    field = SimpleNamespace(id=2)
    recruit = _u(1)
    recruit.place = field
    walker = _u(9)
    walker.place = field
    walker.orders = [SimpleNamespace(target=home)]
    _h, guard, leftover = peel_home_guard(
        [home],
        [recruit, walker],
        menace_of=lambda u: u.menace,
        enemy_menace=lambda _p: 0,
        ratio=100,
    )
    assert [u.id for u in guard] == [9]
    assert [u.id for u in leftover] == [1]


def test_peel_home_guard_prefer_ids_when_nobody_on_square_yet():
    home = SimpleNamespace(id=1)
    units = [_u(1), _u(9)]
    _h, guard, leftover = peel_home_guard(
        [home],
        units,
        menace_of=lambda u: u.menace,
        enemy_menace=lambda _p: 0,
        ratio=100,
        prefer_ids=(9,),
    )
    assert [u.id for u in guard] == [9]
    assert [u.id for u in leftover] == [1]


def test_peel_home_guard_stationed_extras_still_sortie():
    home = SimpleNamespace(id=1)
    units = [_u(1), _u(2), _u(3)]
    for u in units:
        u.place = home
    _h, guard, leftover = peel_home_guard(
        [home],
        units,
        menace_of=lambda u: u.menace,
        enemy_menace=lambda _p: 0,
        ratio=100,
    )
    assert [u.id for u in guard] == [1]
    assert [u.id for u in leftover] == [2, 3]


def test_with_home_does_not_raid_when_cannot_hold():
    home = SimpleNamespace(id=1)
    raid = SimpleNamespace(id=2)
    groups = assign_attack_groups_with_home(
        [raid],
        [_u(1), _u(2)],
        menace_of=lambda u: u.menace,
        enemy_menace=lambda p: 25 if p is home else 10,
        ratio=100,
        home_places=[home],
    )
    assert len(groups) == 1
    assert groups[0][0] is home
    assert [u.id for u in groups[0][1]] == [1, 2]


def test_with_home_peels_token_and_one_raid():
    home = SimpleNamespace(id=0)
    raid = SimpleNamespace(id=1)
    groups = assign_attack_groups_with_home(
        [raid],
        [_u(1), _u(2), _u(3), _u(4)],
        menace_of=lambda u: u.menace,
        enemy_menace=lambda p: 0 if p is home else 15,
        ratio=100,
        home_places=[home],
    )
    assert len(groups) == 2
    assert groups[0][0] is home
    assert [u.id for u in groups[0][1]] == [1]
    assert groups[1][0] is raid
    assert [u.id for u in groups[1][1]] == [2, 3, 4]


def test_with_home_does_not_two_way_split_raids():
    home = SimpleNamespace(id=0)
    a = SimpleNamespace(id=1)
    b = SimpleNamespace(id=2)
    groups = assign_attack_groups_with_home(
        [a, b],
        [_u(i) for i in range(1, 7)],
        menace_of=lambda u: u.menace,
        enemy_menace=lambda p: 0 if p is home else 15,
        ratio=100,
        home_places=[home],
    )
    assert len(groups) == 2
    assert groups[0][0] is home
    assert [u.id for u in groups[0][1]] == [1]
    assert groups[1][0] is a
    assert [u.id for u in groups[1][1]] == [2, 3, 4, 5, 6]


def test_with_home_folds_uncoverable_raid_back_home():
    home = SimpleNamespace(id=0)
    raid = SimpleNamespace(id=1)
    groups = assign_attack_groups_with_home(
        [raid],
        [_u(1), _u(2), _u(3)],
        menace_of=lambda u: u.menace,
        enemy_menace=lambda p: 0 if p is home else 25,
        ratio=100,
        home_places=[home],
    )
    assert len(groups) == 1
    assert groups[0][0] is home
    assert [u.id for u in groups[0][1]] == [1, 2, 3]
