"""Title / rank ladder tests."""

from __future__ import annotations

from soundrts import titles as title_mod


def _load_sample_ranks():
    title_mod.load_titles("""
        def rank_recruit
        kind rank
        title 5400
        medals 0

        def rank_private
        kind rank
        title 5401
        medals 35

        def rank_sergeant
        kind rank
        title 5403
        medals 150
        loadout_slots 0

        def rank_lieutenant
        kind rank
        title 5404
        medals 200
        loadout_slots 1

        def honor_test
        kind honor
        title 5420
    """)


def test_current_rank_from_medals():
    _load_sample_ranks()
    assert title_mod.get_current_rank(0).id == "rank_recruit"
    assert title_mod.get_current_rank(34).id == "rank_recruit"
    assert title_mod.get_current_rank(35).id == "rank_private"
    assert title_mod.get_current_rank(100).id == "rank_private"
    assert title_mod.get_current_rank(150).id == "rank_sergeant"


def test_medals_until_next_rank():
    _load_sample_ranks()
    assert title_mod.medals_until_next_rank(0) == 35
    assert title_mod.medals_until_next_rank(35) == 115
    assert title_mod.medals_until_next_rank(150) == 50


def test_ranks_newly_reached():
    _load_sample_ranks()
    crossed = title_mod.ranks_newly_reached(30, 90)
    assert [r.id for r in crossed] == ["rank_private"]


def test_loadout_slots_from_rank():
    _load_sample_ranks()
    assert title_mod.get_loadout_slots(0) == 0
    assert title_mod.get_loadout_slots(200) == 1
    assert title_mod.rank_at_least(200, "rank_lieutenant") is True


def test_rank_at_least():
    _load_sample_ranks()
    assert title_mod.rank_at_least(100, "rank_private") is True
    assert title_mod.rank_at_least(100, "rank_lieutenant") is False


def test_base_titles_load_with_rules():
    from soundrts.lib.resource import res

    res.set_mods("")
    res.load_rules_and_ai()
    assert title_mod.get_current_rank(0).id == "rank_recruit"
    assert title_mod.title_exists("honor_nightmare_slayer")
