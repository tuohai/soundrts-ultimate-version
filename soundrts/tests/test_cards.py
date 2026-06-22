"""Card definitions (phase 2) tests."""

from __future__ import annotations

from soundrts import cards as card_mod


def _load_sample():
    card_mod.load_cards("""
        def card_infantry
        title 5322
        tags infantry
        spawn footman 3
        grant_charges 2

        def card_resource_gold
        title 5320
        resource resource1 100
    """)


def test_load_cards_parses_spawn_and_resource():
    _load_sample()
    defs = card_mod.get_card_defs()
    assert "card_infantry" in defs
    inf = defs["card_infantry"]
    assert inf.title == [5322]
    assert inf.tags == ["infantry"]
    assert inf.spawns == [("footman", 3)]
    assert inf.grant_charges == 2
    assert inf.delay == 0

    gold = defs["card_resource_gold"]
    assert gold.resources


def test_load_cards_parses_delay():
    card_mod.load_cards("""
        def card_late
        title 5333
        spawn footman 1
        delay 90

        def card_late_minutes
        title 5333
        delay_minutes 10
    """)
    defs = card_mod.get_card_defs()
    assert defs["card_late"].delay == 90
    assert defs["card_late_minutes"].delay == 600


def test_load_cards_parses_tech():
    card_mod.load_cards("""
        def card_tech
        title 5334
        tech melee_weapon melee_armor
    """)
    defs = card_mod.get_card_defs()
    assert defs["card_tech"].techs == ["melee_weapon", "melee_armor"]


def test_load_cards_parses_train_bonus():
    card_mod.load_cards("""
        def card_train
        title 5396
        train_bonus footman 3
    """)
    defs = card_mod.get_card_defs()
    assert defs["card_train"].train_bonuses == [("footman", 3)]


def test_base_cards_file_loads_with_rules():
    from soundrts.lib.resource import res

    res.load_rules_and_ai()
    order = card_mod.get_card_order()
    assert "card_infantry" in order
    assert card_mod.card_exists("card_dragon")


def test_tiered_cards_load_from_rules():
    from soundrts.lib.resource import res

    res.load_rules_and_ai()
    from soundrts import cards as card_mod

    assert card_mod.card_exists("card_infantry_small")
    assert card_mod.card_exists("card_infantry_large")
    inf_s = card_mod.get_card("card_infantry_small")
    inf_l = card_mod.get_card("card_infantry_large")
    assert inf_s.spawns == [("footman", 2)]
    assert inf_l.spawns == [("footman", 6)]
    assert inf_s.title == [5457]
    assert inf_l.title == [5459]


def test_hero_raynor_card_loads_with_rules():
    from soundrts.definitions import rules
    from soundrts.lib.resource import res

    res.load_rules_and_ai()
    from soundrts import cards as card_mod

    assert card_mod.card_exists("card_hero_raynor")
    hero = card_mod.get_card("card_hero_raynor")
    assert hero.title == [5485]
    assert hero.tags == ["hero"]
    assert hero.spawns == [("raynor7", 1)]
    assert hero.min_rank == "rank_general"
    assert rules.unit_class("raynor7") is not None


def test_clear_resets_cards():
    _load_sample()
    card_mod.load_cards("clear")
    assert card_mod.get_card_order() == []
