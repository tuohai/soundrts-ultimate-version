"""Tests for procedural random map generation."""
from __future__ import annotations

import os
import sys
import warnings

import pytest

from soundrts.randommap import (
    MONSTER_PRESETS,
    TEMPLATES,
    TERRAIN_MODES,
    RandomMapConfig,
    SIZE_PRESETS,
    _loot_item_types,
    decode_share_code,
    encode_share_code,
    generate_definition,
    make_map,
    parse_random_map_meta,
    parse_server_create_args,
    server_create_command,
)


def _reset_base_game_rules():
    """Restore base-game rules/ai/style/map in the global singletons.

    Some test modules (e.g. test_build_rules) load the starcraft mod into the
    global resource/rules/style state and do not restore it. Tests that depend
    on base-game data call this to become order-independent.
    """
    from soundrts import config
    from soundrts.lib.resource import res

    config.mods = ""
    res.set_map()
    res.set_mods("")
    res.load_rules_and_ai()
    res.load_style()


def _load_world():
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

    from soundrts import config

    config.debug_mode = 0
    config.mods = ""

    saved_argv = sys.argv
    try:
        sys.argv = [saved_argv[0]] if saved_argv else ["pytest"]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from soundrts.world import World

            return World
    finally:
        sys.argv = saved_argv


def test_generate_is_deterministic_for_same_seed():
    cfg = RandomMapConfig(size="medium", nb_players=2, seed=4242)
    text_a, seed_a = generate_definition(cfg)
    text_b, seed_b = generate_definition(cfg)
    assert seed_a == seed_b == 4242
    assert text_a == text_b


def test_generate_differs_for_different_seeds():
    a, _ = generate_definition(RandomMapConfig(seed=1))
    b, _ = generate_definition(RandomMapConfig(seed=2))
    assert a != b


def test_make_map_header():
    m, seed = make_map(RandomMapConfig(size="small", nb_players=2, seed=99))
    assert seed == 99
    assert m.nb_players_min == 2
    assert m.nb_players_max == 2
    assert "nb_columns 7" in m.definition
    assert "nb_lines 7" in m.definition
    assert "starting_squares 2,2 6,6" in m.definition


def test_fast_template_adds_center_bridges():
    text, _ = generate_definition(RandomMapConfig(template="fast", size="medium", seed=100))
    assert "west_east_bridges" in text
    assert "south_north_bridges" in text


def test_lanes_template_is_three_rows():
    text, _ = generate_definition(RandomMapConfig(template="lanes", size="medium", seed=200))
    assert "nb_columns 15" in text
    assert "nb_lines 3" in text
    assert "terrain ford" in text
    assert "starting_squares 1,2 15,2" in text


def test_lanes_starts_have_meadows_and_paths():
    World = _load_world()
    from soundrts.randommap import LANE_START_MEADOWS

    for nb_players in (2, 3, 4):
        m, _ = make_map(
            RandomMapConfig(template="lanes", size="medium", nb_players=nb_players, seed=200)
        )
        world = World([], 200)
        world.load_and_build_map(m)
        for sq_name in world.starting_squares:
            sq = world.grid[sq_name]
            assert sq.nb_meadows >= LANE_START_MEADOWS, sq_name
            assert sq.exits, sq_name


def test_lanes_middle_row_has_full_horizontal_paths():
    text, _ = generate_definition(
        RandomMapConfig(template="lanes", size="medium", nb_players=2, seed=200)
    )
    assert "1,2 2,2" in text
    assert "14,2" in text
    assert "1,1 1,2" in text.replace("\n", " ")
    assert "15,1 15,2" in text.replace("\n", " ")


def test_lake_water_on_grid_map():
    text, _ = generate_definition(
        RandomMapConfig(template="standard", size="medium", water="lake", seed=300)
    )
    assert "water " in text
    assert "terrain lake" in text


def test_teams_2v2_adds_alliance_triggers():
    text, _ = generate_definition(
        RandomMapConfig(size="medium", nb_players=4, team_mode="teams_2v2", seed=400)
    )
    assert "trigger player1 (timer 0) (alliance 1)" in text
    assert "trigger player4 (timer 0) (alliance 2)" in text
    assert "trigger players (no_enemy_player_left) (victory)" in text


def test_victory_mode_economic_adds_resource_trigger():
    text, _ = generate_definition(
        RandomMapConfig(victory_mode="economic", template="standard", seed=50)
    )
    assert "random_map 1" in text
    assert "victory_mode economic" in text
    assert "has_gathered 3000 resource1" in text
    assert "objective 5435 3000 131" in text


def test_parse_random_map_meta_from_generated_definition():
    text, _ = generate_definition(
        RandomMapConfig(victory_mode="exploration", template="standard", seed=77)
    )
    is_rmg, mode = parse_random_map_meta(text)
    assert is_rmg is True
    assert mode == "exploration"


def test_parse_random_map_meta_fallback_from_objective_only():
    legacy = "title random_map standard seed_1\nobjective 5436 15 5437\n"
    is_rmg, mode = parse_random_map_meta(legacy)
    assert is_rmg is True
    assert mode == "survival"


def test_victory_mode_survival_adds_timer_victory():
    text, _ = generate_definition(
        RandomMapConfig(victory_mode="survival", template="fast", seed=51)
    )
    assert "trigger players (timer 600) (if (not (no_building_left)) (personal_victory))" in text
    assert "objective 5436 10 5437 5452" in text


def test_victory_mode_exploration_adds_ruin_triggers():
    _reset_base_game_rules()
    text, _ = generate_definition(
        RandomMapConfig(victory_mode="exploration", size="medium", seed=52)
    )
    assert "ancient_ruin" in text
    assert "rmg_ruin_" in text
    assert "rmg_mark_ruin_discovered" in text
    assert "trigger players (no_enemy_player_left) (victory)" not in text
    assert "rmg_all_ruins_discovered_by_allies" in text


def test_victory_mode_conquest_objective():
    text, _ = generate_definition(
        RandomMapConfig(victory_mode="conquest", template="standard", seed=53)
    )
    assert "objective 5451" in text


def test_victory_mode_economic_has_no_conquest_victory():
    text, _ = generate_definition(
        RandomMapConfig(victory_mode="economic", template="standard", seed=50)
    )
    assert "trigger players (no_enemy_player_left) (victory)" not in text


def test_victory_mode_survival_has_no_conquest_victory():
    text, _ = generate_definition(
        RandomMapConfig(victory_mode="survival", template="fast", seed=51)
    )
    assert "trigger players (no_enemy_player_left) (victory)" not in text
    assert "personal_victory" in text


def test_rmg_multiplayer_skips_melee_default_triggers():
    from soundrts.game import MultiplayerGame
    from soundrts.world import World

    cfg = RandomMapConfig(victory_mode="economic", size="small", nb_players=2, seed=42)
    m, _ = make_map(cfg)
    game = MultiplayerGame(m, [], "host", None, 42, 1.0)
    assert game._world_default_triggers() == []


def test_rmg_exploration_ruin_reward_only_once():
    text, _ = generate_definition(
        RandomMapConfig(victory_mode="exploration", size="medium", seed=52)
    )
    assert "(if (not (rmg_ruin_discovered_by_self rmg_ruin_" in text
    assert "rmg_mark_ruin_discovered" in text
    assert "rmg_ruin_0_reward" in text or "rmg_ruin_1_reward" in text


def test_exploration_mode_emits_intro_briefing():
    exploration, _ = generate_definition(
        RandomMapConfig(victory_mode="exploration", size="medium", seed=77)
    )
    conquest, _ = generate_definition(
        RandomMapConfig(victory_mode="conquest", size="medium", seed=77)
    )
    assert "intro 5486" in exploration
    assert "5428" in exploration.split("intro")[1].split("\n")[0]
    assert "intro 5486" not in conquest


def test_exploration_ruin_depth_triggers():
    _reset_base_game_rules()
    text, _ = generate_definition(
        RandomMapConfig(victory_mode="exploration", size="medium", seed=52)
    )
    assert "rmg_ruin_discovered_by_self" in text
    assert "rmg_ruin_depth_claimed_by_self" in text
    assert "rmg_claim_ruin_depth" in text
    assert "(cut_scene 5490)" in text
    assert "(cut_scene 5491)" in text
    assert "rmg_announce_ruins_remaining" in text


def test_exploration_briefing_deterministic():
    cfg = RandomMapConfig(victory_mode="exploration", size="medium", seed=4242)
    text_a, _ = generate_definition(cfg)
    text_b, _ = generate_definition(cfg)
    intro_a = next(line for line in text_a.splitlines() if line.startswith("intro "))
    intro_b = next(line for line in text_b.splitlines() if line.startswith("intro "))
    assert intro_a == intro_b


def test_conquest_ruin_depth_without_progress_announce():
    _reset_base_game_rules()
    text, _ = generate_definition(
        RandomMapConfig(victory_mode="conquest", size="medium", seed=52)
    )
    assert "(cut_scene 5490)" in text
    assert "rmg_announce_ruins_remaining" not in text
    assert "intro 5486" not in text


def test_training_game_pre_run_plays_intro_once(monkeypatch):
    from soundrts.game import TrainingGame

    calls = []

    def fake_play_sequence(names):
        calls.append(list(names))

    monkeypatch.setattr("soundrts.game.play_sequence", fake_play_sequence)
    monkeypatch.setattr(
        "soundrts.lib.sound.stop_music",
        lambda: None,
    )
    game = TrainingGame.__new__(TrainingGame)
    game.world = type("W", (), {"intro": [5486, 5488, 5428]})()
    game.pre_run()
    assert len(calls) == 1
    assert calls[0] == [5486, 5488, 5428]


def test_server_create_command_all_victory_modes():
    for mode in ("conquest", "economic", "exploration", "survival"):
        cfg = RandomMapConfig(victory_mode=mode, size="small", nb_players=2, seed=99)
        cmd = server_create_command(cfg, "1.0", treaty_minutes=0)
        parsed, speed, is_public, treaty = parse_server_create_args(cmd.split()[1:])
        assert parsed.victory_mode == mode
        assert speed == 1.0
        assert treaty == 0


def test_capturable_dwelling_triggers_match_computer_only_slots():
    _reset_base_game_rules()
    cfg = RandomMapConfig(
        victory_mode="exploration",
        template="lanes",
        size="large",
        nb_players=4,
        treasure="high",
        seed=6325,
    )
    text, _ = generate_definition(cfg)
    computer_count = sum(
        1 for line in text.splitlines() if line.startswith("computer_only")
    )
    import re

    for line in text.splitlines():
        if "rmg_dwelling_" not in line or not line.startswith("trigger computer"):
            continue
        match = re.match(r"^trigger computer(\d+)\b", line)
        assert match, line
        assert int(match.group(1)) <= computer_count, line


def test_rmg_map_loads_without_unknown_computer_triggers(caplog):
    import logging

    _reset_base_game_rules()
    from soundrts.world import World

    cfg = RandomMapConfig(
        victory_mode="exploration",
        template="lanes",
        size="large",
        nb_players=4,
        treasure="high",
        seed=6325,
    )
    m, _ = make_map(cfg)
    caplog.set_level(logging.WARNING)
    w = World([], 6325)
    w.load_and_build_map(m)
    unknown = [
        r.message
        for r in caplog.records
        if "is unknown" in r.message and "computer" in r.message
    ]
    assert unknown == []


def test_capturable_dwelling_uses_hostile_computer_not_neutral():
    _reset_base_game_rules()
    text, _ = generate_definition(RandomMapConfig(size="medium", seed=77))
    barracks_lines = [
        line
        for line in text.splitlines()
        if line.startswith("computer_only") and "captured_barracks" in line
    ]
    assert barracks_lines
    for line in barracks_lines:
        assert " neutral " not in line
        assert line.startswith("computer_only 0 0 ")
        assert "footman" in line
        assert "archer" in line


def test_captured_barracks_has_capture_threshold():
    from soundrts.definitions import rules

    cls = rules.unit_class("captured_barracks")
    assert cls is not None
    assert cls.capture_hp_threshold == 100


def test_capturable_dwelling_uses_unit_lost_not_transfer():
    _reset_base_game_rules()
    text, _ = generate_definition(RandomMapConfig(size="medium", seed=78))
    assert "transfer_units" not in text
    assert "unit_lost" in text and "captured_barracks" in text
    assert "cut_scene 5434" in text


def test_share_code_with_victory_mode_roundtrip():
    cfg = RandomMapConfig(
        template="fast",
        size="medium",
        nb_players=2,
        monster_strength="strong",
        resource_layout="clustered",
        terrain="marsh",
        team_mode="ffa",
        water="lake",
        treasure="high",
        victory_mode="economic",
        seed=4242,
    )
    code = encode_share_code(cfg, 4242)
    assert ":e:" in code or code.endswith(":4242") is False
    restored = decode_share_code(code)
    assert restored.normalized() == cfg.normalized()


def test_river_water_on_grid_map():
    text, _ = generate_definition(
        RandomMapConfig(template="standard", size="medium", water="river", seed=301)
    )
    assert "water " in text
    assert "west_east_bridges" in text


def test_center_creep_is_hostile_not_neutral():
    text, _ = generate_definition(
        RandomMapConfig(template="standard", size="medium", monster_strength="medium", seed=500)
    )
    assert "computer_only 0 0 neutral 6,6" not in text
    assert "computer_only 0 0 6,6 4 footman 2 archer" in text


def test_loot_item_types_includes_treasure_chest():
    _load_world()
    assert "treasure_chest" in _loot_item_types()


def test_high_treasure_can_spawn_treasure_chest():
    _load_world()
    text, _ = generate_definition(
        RandomMapConfig(template="standard", size="medium", treasure="high", seed=1)
    )
    assert "treasure_chest" in text


def test_treasure_adds_extra_goldmines():
    _load_world()
    # Other test modules may load the starcraft mod into the global rules
    # singleton; restore base-game rules so resource1 deposits are "goldmines".
    _reset_base_game_rules()
    text, _ = generate_definition(
        RandomMapConfig(template="standard", size="medium", treasure="low", seed=302)
    )
    assert text.count("goldmines") >= 3


def test_resource_deposit_lines_have_valid_coordinates():
    from soundrts.randommap import _deposit_map_keywords

    deposit_keywords = set(_deposit_map_keywords())
    text, _ = generate_definition(
        RandomMapConfig(template="standard", size="medium", seed=4242)
    )
    for line in text.splitlines():
        words = line.split()
        if not words or words[0] not in deposit_keywords:
            continue
        assert words[1].isdigit(), line
        for tok in words[2:]:
            assert "," in tok, f"invalid deposit coordinate token {tok!r} in {line!r}"


def test_random_map_loads_all_resource_deposits():
    World = _load_world()
    m, _ = make_map(RandomMapConfig(template="standard", size="medium", seed=4242))
    world = World([], 4242)
    world.load_and_build_map(m)
    for z, cls, _ in world.map_objects:
        assert z in world.grid, f"{z} missing from grid for {cls}"


def test_starcraft_mod_uses_mineral_field_and_geyser():
    import os
    import sys
    import warnings

    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

    saved_argv = sys.argv
    try:
        sys.argv = [saved_argv[0]] if saved_argv else ["pytest"]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from soundrts import config
            from soundrts.lib.resource import res

            config.debug_mode = 0
            config.mods = "starcraft"
            res.set_mods("starcraft")
            res.load_rules_and_ai()
            text, _ = generate_definition(RandomMapConfig(seed=42))
    finally:
        sys.argv = saved_argv
        try:
            from soundrts import config
            from soundrts.lib.resource import res

            config.mods = ""
            res.set_mods("")
        except Exception:
            pass

    assert "mineral_fields" in text
    assert "geysers" in text
    assert "goldmines" not in text
    assert "woods" not in text
    assert "geysers 1 " in text


def test_starcraft_mod_random_map_has_no_hunting_animals():
    import os
    import sys
    import warnings

    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

    saved_argv = sys.argv
    try:
        sys.argv = [saved_argv[0]] if saved_argv else ["pytest"]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from soundrts import config
            from soundrts.lib.resource import res

            config.debug_mode = 0
            config.mods = "starcraft"
            res.set_mods("starcraft")
            res.load_rules_and_ai()
            text, _ = generate_definition(
                RandomMapConfig(template="lanes", size="medium", seed=200)
            )
            assert _loot_item_types() == []
            text_high, _ = generate_definition(
                RandomMapConfig(
                    template="lanes", size="medium", seed=201, treasure="high"
                )
            )
    finally:
        sys.argv = saved_argv
        try:
            from soundrts import config
            from soundrts.lib.resource import res

            config.mods = ""
            res.set_mods("")
        except Exception:
            pass

    for animal in ("deer", "sheep", "boar"):
        assert animal not in text
    assert "treasure_chest" not in text_high
    assert "orchard" not in text
    assert "orchard" not in text_high


_CUSTOM_DEPOSIT_RULES = """
def parameters
nb_of_resource_types 2

def iron_mine
class deposit
resource_type resource1
extraction_time 3
extraction_qty 1

def aluminum_mine
class deposit
resource_type resource2
extraction_time 3
extraction_qty 1
"""

_MULTI_RESOURCE_RULES = """
def parameters
nb_of_resource_types 4

def iron_mine
class deposit
resource_type resource1
extraction_time 3
extraction_qty 1

def aluminum_mine
class deposit
resource_type resource2
extraction_time 3
extraction_qty 1

def copper_mine
class deposit
resource_type resource3
extraction_time 3
extraction_qty 1

def tin_mine
class deposit
resource_type resource4
extraction_time 3
extraction_qty 1
"""


def _load_rules_with_custom_deposits():
    from pathlib import Path

    from soundrts.definitions import _get_base_classes, rules

    base = Path("res/rules.txt").read_text(encoding="utf-8")
    rules.load(base, _CUSTOM_DEPOSIT_RULES, base_classes=_get_base_classes())
    return rules


def test_expand_deposit_plurals_supports_custom_deposits():
    _load_rules_with_custom_deposits()
    from soundrts.lib.map_tokens import expand_deposit_plurals

    text = "iron_mines 500 a1\naluminum_mines 300 b1"
    expanded = expand_deposit_plurals(text)
    assert "iron_mine 500 a1" in expanded
    assert "aluminum_mine 300 b1" in expanded
    assert "iron_mines" not in expanded


def test_custom_deposit_random_map_generates_and_loads():
    _load_rules_with_custom_deposits()
    from soundrts.randommap import _deposit_map_keywords

    assert _deposit_map_keywords() == ("iron_mines", "aluminum_mines")

    text, _ = generate_definition(RandomMapConfig(size="small", nb_players=2, seed=42))
    assert "iron_mines" in text
    assert "aluminum_mines" in text
    assert "goldmines" not in text

    World = _load_world()
    from soundrts.definitions import rules
    from soundrts.lib.resource import res
    from soundrts.mapfile import Map

    m = Map.loads(text.encode("utf-8"), "custom_deposit_rmg.txt")
    world = World([], 42)
    res.set_map(m)
    _load_rules_with_custom_deposits()
    world._parse_map(m.definition)

    parsed_deposits = {cls for _, cls, _ in world.map_objects}
    assert "iron_mine" in parsed_deposits
    assert "aluminum_mine" in parsed_deposits
    assert "goldmine" not in parsed_deposits


def test_mod_rules_without_animals_disables_hunting():
    from soundrts.randommap import _huntable_animal_types_in_rules_text

    assert not _huntable_animal_types_in_rules_text(_MULTI_RESOURCE_RULES)


def test_mod_rules_without_items_disables_loot():
    from soundrts.randommap import _loot_item_types_in_rules_text

    assert _loot_item_types_in_rules_text(_MULTI_RESOURCE_RULES) == []
    assert _loot_item_types_in_rules_text(
        "def parameters\n"
        "def mystery_box\nclass item\nconsume_on_pickup 1\n"
    ) == ["mystery_box"]


def test_mod_rules_without_orchard_disables_orchard_treasure():
    from soundrts.randommap import _orchard_available_in_rules_text

    assert not _orchard_available_in_rules_text(_MULTI_RESOURCE_RULES)
    assert _orchard_available_in_rules_text(
        "def orchard\nclass deposit\nresource_type resource3\n"
    )


def test_four_resource_mod_places_all_deposit_types():
    from pathlib import Path

    from soundrts.definitions import _get_base_classes, rules
    from soundrts.lib.map_tokens import expand_deposit_plurals
    from soundrts.randommap import _deposit_map_keywords, _pad_starting_resources

    base = Path("res/rules.txt").read_text(encoding="utf-8")
    rules.load(base, _MULTI_RESOURCE_RULES, base_classes=_get_base_classes())

    assert _deposit_map_keywords() == (
        "iron_mines",
        "aluminum_mines",
        "copper_mines",
        "tin_mines",
    )
    assert _pad_starting_resources((50, 60)) == [50, 60, 60, 60]

    text, _ = generate_definition(RandomMapConfig(size="small", nb_players=2, seed=7))
    assert "copper_mines" in text
    assert "tin_mines" in text
    assert "starting_resources 100 100 100 100" in text

    expanded = expand_deposit_plurals(text)
    assert "copper_mine " in expanded
    assert "tin_mine " in expanded


def test_share_code_roundtrip():
    cfg = RandomMapConfig(
        template="fast",
        size="medium",
        nb_players=2,
        monster_strength="strong",
        resource_layout="clustered",
        terrain="marsh",
        team_mode="ffa",
        water="lake",
        treasure="high",
        seed=4242,
    )
    code = encode_share_code(cfg, 4242)
    assert code.startswith("RMG1:")
    restored = decode_share_code(code)
    assert restored.normalized() == cfg.normalized()


def test_custom_seed_is_used():
    _, seed = generate_definition(RandomMapConfig(seed=7777))
    assert seed == 7777


@pytest.mark.parametrize("template", list(TEMPLATES))
@pytest.mark.parametrize("terrain", list(TERRAIN_MODES))
@pytest.mark.parametrize("size", list(SIZE_PRESETS))
@pytest.mark.parametrize("nb_players", (2, 3, 4))
@pytest.mark.parametrize("monster_strength", list(MONSTER_PRESETS))
@pytest.mark.parametrize("resource_layout", ("balanced", "clustered"))
def test_generated_map_loads_in_world(
    template, terrain, size, nb_players, monster_strength, resource_layout
):
    World = _load_world()
    cfg = RandomMapConfig(
        size=size,
        nb_players=nb_players,
        monster_strength=monster_strength,
        resource_layout=resource_layout,
        template=template,
        terrain=terrain,
        seed=12345,
    )
    m, _ = make_map(cfg)
    world = World([], cfg.seed)
    world.load_and_build_map(m)
    if template == "lanes":
        assert world.nb_lines == 3
    else:
        assert world.nb_columns == SIZE_PRESETS[size][0]
        assert world.nb_lines == SIZE_PRESETS[size][1]
    assert len(world.players_starts) == nb_players


def test_config_normalization_clamps_invalid_values():
    cfg = RandomMapConfig(
        size="huge",
        nb_players=9,
        monster_strength="extreme",
        resource_layout="weird",
        template="unknown",
        terrain="volcano",
        team_mode="bad",
        water="ocean",
        treasure="junk",
        seed=-5,
    )
    norm = cfg.normalized()
    assert norm.size == "medium"
    assert norm.nb_players == 4
    assert norm.monster_strength == "medium"
    assert norm.resource_layout == "balanced"
    assert norm.template == "standard"
    assert norm.terrain == "random"
    assert norm.team_mode == "ffa"
    assert norm.water == "none"
    assert norm.treasure == "none"
    assert norm.seed is None


def test_server_create_command_roundtrip():
    cfg = RandomMapConfig(
        size="large",
        nb_players=4,
        monster_strength="strong",
        resource_layout="clustered",
        template="fast",
        terrain="marsh",
        team_mode="teams_2v2",
        water="lake",
        treasure="high",
        seed=4242,
    )
    cmd = server_create_command(cfg, "1.0", is_public=True, treaty_minutes=10)
    assert cmd == "create_random large 4 strong clustered fast marsh teams_2v2 lake high conquest 4242 1.0 public 10"
    parsed, speed, is_public, treaty = parse_server_create_args(cmd.split()[1:])
    assert parsed.normalized() == cfg.normalized()
    assert speed == 1.0
    assert is_public is True
    assert treaty == 10


def test_server_create_legacy_format_without_template():
    args = ["medium", "2", "medium", "balanced", "1.0", "0"]
    parsed, speed, is_public, treaty = parse_server_create_args(args)
    assert parsed.template == "standard"
    assert parsed.terrain == "random"
    assert parsed.team_mode == "ffa"
    assert parsed.water == "none"
    assert parsed.treasure == "none"
    assert parsed.seed is None
    assert speed == 1.0
    assert treaty == 0


def test_rmg_msgparts_constants_exist():
    from soundrts import msgparts as mp

    assert mp.RMG_RANDOM_MAP == [5033]
    assert mp.RMG_TEMPLATE_LANES == [5059]
    assert mp.RMG_LAKE == [5070]
    assert mp.RMG_SHARE_CODE == [5076]


def test_map_generated_voice_msg_includes_history_hint():
    from soundrts import msgparts as mp
    from soundrts.randommap import RandomMapConfig, map_generated_voice_msg

    cfg = RandomMapConfig(seed=4242)
    msg = map_generated_voice_msg(cfg, 4242)
    assert mp.RMG_MAP_GENERATED[0] in msg
    assert mp.HISTORY_EXPLANATION[0] in msg
    assert mp.RMG_SHARE_CODE[0] in msg


def test_custom_template_loads_and_generates(tmp_path):
    from soundrts.rmg_templates import parse_template_text, reload_custom_templates
    from soundrts.randommap import _builtin_rmg_specs, refresh_rmg_templates

    template_dir = tmp_path / "cfg" / "randommap"
    template_dir.mkdir(parents=True)
    (template_dir / "desert.txt").write_text(
        "random_map_template\n"
        "name desert_skirmish\n"
        "extends fast\n"
        "title desert skirmish\n"
        "terrain_modes random grass marsh\n",
        encoding="utf-8",
    )
    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        reload_custom_templates(_builtin_rmg_specs())
        entry = parse_template_text(
            (template_dir / "desert.txt").read_text(encoding="utf-8"),
            builtin_specs=_builtin_rmg_specs(),
        )
        assert entry.name == "desert_skirmish"
        assert entry.spec.starting_units.startswith("townhall 3")
        text, _ = generate_definition(
            RandomMapConfig(template="desert_skirmish", terrain="marsh", seed=101)
        )
        assert "terrain marsh" in text
        assert "starting_units townhall 3" in text
    finally:
        os.chdir(old_cwd)
        refresh_rmg_templates()


def test_custom_template_share_code_rmg2(tmp_path):
    template_dir = tmp_path / "cfg" / "randommap"
    template_dir.mkdir(parents=True)
    (template_dir / "desert.txt").write_text(
        "random_map_template\nname desert_skirmish\nextends fast\n",
        encoding="utf-8",
    )
    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        from soundrts.randommap import refresh_rmg_templates

        refresh_rmg_templates()
        cfg = RandomMapConfig(template="desert_skirmish", terrain="marsh", seed=4242)
        code = encode_share_code(cfg, 4242)
        assert code.startswith("RMG2:")
        restored = decode_share_code(code)
        assert restored.template == "desert_skirmish"
        assert restored.terrain == "marsh"
        assert restored.seed == 4242
    finally:
        os.chdir(old_cwd)
        from soundrts.randommap import refresh_rmg_templates

        refresh_rmg_templates()


def test_terrain_choices_include_rules_rmg_terrains():
    from pathlib import Path

    from soundrts.definitions import _get_base_classes, rules
    from soundrts.randommap import terrain_choices_for_template

    _reset_base_game_rules()
    choices = terrain_choices_for_template("standard")
    assert "random" in choices
    assert "grass" in choices
    assert "marsh" in choices
    assert "mountain" in choices

    base = Path("res/rules.txt").read_text(encoding="utf-8")
    rules.load(
        base,
        "def rocky_plain\nclass terrain\nis_dynamic 1\nrmg_terrain 1\n",
        base_classes=_get_base_classes(),
    )
    choices = terrain_choices_for_template("standard")
    assert "rocky_plain" in choices
