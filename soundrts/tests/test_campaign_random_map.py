"""Campaign chapters that use procedural random maps."""
from __future__ import annotations

import os
import sys
import textwrap
import warnings

import pytest

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from soundrts import config

config.debug_mode = 0
config.mods = ""

_saved_argv = sys.argv
try:
    sys.argv = [_saved_argv[0]] if _saved_argv else ["pytest"]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from soundrts.campaign import Campaign, RandomMapMissionChapter, ensure_chapter_map
        from soundrts.lib.package import FolderPackage
        from soundrts.randommap import (
            RandomMapConfig,
            make_campaign_map,
            merge_campaign_overlay,
            parse_campaign_random_chapter,
        )
finally:
    sys.argv = _saved_argv


SAMPLE_CHAPTER = textwrap.dedent(
    """\
    random_map_chapter
    title 8500
    size small
    players 2
    template standard
    monster medium
    layout balanced

    trigger player1 (timer 60) (victory)
    """
)


def test_parse_campaign_random_chapter():
    cfg, title, overlay = parse_campaign_random_chapter(SAMPLE_CHAPTER)
    assert cfg.size == "small"
    assert cfg.nb_players == 2
    assert cfg.template == "standard"
    assert cfg.monster_strength == "medium"
    assert cfg.resource_layout == "balanced"
    assert cfg.seed is None
    assert title == [8500]
    assert "trigger player1 (timer 60) (victory)" in overlay


def test_parse_campaign_seed_fixed_and_random():
    fixed = "random_map_chapter\nseed 4242\n"
    cfg, _, _ = parse_campaign_random_chapter(fixed)
    assert cfg.seed == 4242

    random_seed = "random_map_chapter\nseed random\n"
    cfg2, _, _ = parse_campaign_random_chapter(random_seed)
    assert cfg2.seed is None


def test_merge_campaign_overlay_strips_rmg_headers():
    generated = "title random_map standard seed_1\nobjective 145 88\n\nnb_columns 7\n"
    merged = merge_campaign_overlay(generated, "trigger player1 (victory)")
    assert "title random_map" not in merged
    assert "objective 145 88" not in merged
    assert "trigger player1 (victory)" in merged
    assert "nb_columns 7" in merged


def test_merge_campaign_overlay_replaces_starting_units():
    generated = (
        "title random_map standard seed_1\n"
        "starting_units townhall 4 house 10 peasant\n"
        "nb_columns 7\n"
    )
    overlay = "starting_units townhall 2 house 5 peasant 1 raynor7"
    merged = merge_campaign_overlay(generated, overlay)
    assert merged.count("starting_units ") == 1
    assert "raynor7" in merged
    assert "house 10" not in merged


def test_make_campaign_map_pins_spawn_slot_for_triggers():
    overlay = "trigger player1 (timer 0) (add_objective 1 1)"
    cfg = RandomMapConfig(size="small", nb_players=2, seed=42)
    m, _ = make_campaign_map(cfg, overlay, "demo", 1)
    assert "random_starts 0" in m.definition
    assert "random_starts 1" not in m.definition


def test_make_campaign_map_differs_without_fixed_seed():
    overlay = "trigger player1 (timer 1) (victory)"
    cfg = RandomMapConfig(size="small", nb_players=2, seed=None)
    map_a, seed_a = make_campaign_map(cfg, overlay, "demo", 1)
    map_b, seed_b = make_campaign_map(cfg, overlay, "demo", 1)
    assert map_a.definition != map_b.definition or seed_a != seed_b


def test_make_campaign_map_is_deterministic_with_fixed_seed():
    overlay = "trigger player1 (timer 1) (victory)"
    cfg = RandomMapConfig(size="small", nb_players=2, seed=99)
    map_a, seed_a = make_campaign_map(cfg, overlay, "demo", 1)
    map_b, seed_b = make_campaign_map(cfg, overlay, "demo", 1)
    assert seed_a == seed_b == 99
    assert map_a.definition == map_b.definition


def test_campaign_loads_random_map_chapter(tmp_path):
    campaign_dir = tmp_path / "rmg_demo"
    campaign_dir.mkdir()
    (campaign_dir / "campaign.txt").write_text("title 9000\n", encoding="utf-8")
    (campaign_dir / "0.txt").write_text(SAMPLE_CHAPTER, encoding="utf-8")

    campaign = Campaign(FolderPackage(str(campaign_dir)), "rmg_demo")
    chapter = campaign.chapter(0)
    assert isinstance(chapter, RandomMapMissionChapter)
    assert chapter.title == [8500]
    assert chapter.map is None

    map_ = ensure_chapter_map(chapter)
    assert map_.name == "rmg_demo/0"
    assert "trigger player1 (timer 60) (victory)" in map_.definition
    assert chapter.last_seed is not None


def test_random_map_chapter_regenerates_on_each_build(tmp_path):
    campaign_dir = tmp_path / "rmg_demo"
    campaign_dir.mkdir()
    (campaign_dir / "0.txt").write_text(
        "random_map_chapter\nsize small\nplayers 2\n", encoding="utf-8"
    )
    campaign = Campaign(FolderPackage(str(campaign_dir)), "rmg_demo")
    chapter = campaign.chapter(0)
    first = ensure_chapter_map(chapter).definition
    second = chapter.build_map().definition
    assert first != second


def test_campaign_random_map_always_keeps_player1_triggers():
    import os
    import sys
    import warnings

    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    saved_argv = sys.argv
    try:
        sys.argv = ["pytest"]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from soundrts.lib.resource import res
            from soundrts.world import World
            from soundrts.worldclient import DirectClient
    finally:
        sys.argv = saved_argv

    overlay = "trigger player1 (timer 0) (add_objective 1 1)"
    cfg = RandomMapConfig(size="small", nb_players=2, seed=42)
    m, _ = make_campaign_map(cfg, overlay, "demo", 1)
    res.set_map(m)
    res.load_rules_and_ai()
    for seed in range(20):
        world = World(seed=seed)
        world.load_and_build_map(m)
        client = DirectClient("p1", None)
        world.populate_map([client])
        assert len(world.players[0].triggers) == 1


def test_parse_rejects_non_marker():
    with pytest.raises(ValueError):
        parse_campaign_random_chapter("title 1\n")
