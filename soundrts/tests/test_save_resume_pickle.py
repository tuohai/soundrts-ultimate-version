"""Regression: resume save must not embed pygame.mixer.Channel."""

import pickle
from pathlib import Path
from unittest.mock import MagicMock


def test_sound_source_getstate_clears_channel():
    from soundrts.lib.sound import SoundSource

    src = SoundSource(None, 1, 0, 0, 0)
    src.channel = MagicMock(name="pygame_channel")

    state = src.__getstate__()
    assert state["channel"] is None
    pickle.dumps(state)


def test_game_interface_save_strips_ambient_noises():
    text = Path("soundrts/clientgame/game_interface_base.py").read_text(
        encoding="utf-8"
    )
    assert "_stop_unpicklable_audio" in text
    assert 'odict["_terrain_noises"] = []' in text
    assert 'odict["_build_field_noises"] = []' in text


def test_voicechannel_getstate_omits_mixer_channel():
    text = Path("soundrts/lib/voicechannel.py").read_text(encoding="utf-8")
    assert "def __getstate__(self):" in text
    assert 'state.pop("c", None)' in text
    assert "def __setstate__(self, state):" in text


def test_save_rejects_oversized_world_before_pickle():
    from soundrts.game import SAVE_RECURSION_LIMIT_BASE, pickle_recursion_limit_for_squares
    from soundrts.save_pickle import WORLD_STRIP_ON_SAVE, rebuild_world_after_load

    assert pickle_recursion_limit_for_squares(10000) == 50000
    assert pickle_recursion_limit_for_squares(100) == SAVE_RECURSION_LIMIT_BASE
    assert "g" in WORLD_STRIP_ON_SAVE
    assert "grid" in WORLD_STRIP_ON_SAVE
    assert callable(rebuild_world_after_load)


def test_game_interface_recreated_on_restore():
    text = Path("soundrts/game.py").read_text(encoding="utf-8")
    assert "def _ensure_interface_for_restore(self):" in text
    assert "self.interface = clientgame.GameInterface(self.local_client" in text
    block = text[text.index("def run_on(self):"):text.index("class TrainingGame")]
    assert "_ensure_interface_for_restore()" in block


def test_action_pickle_always_has_target_attr():
    from soundrts.save_pickle import restore_target_after_pickle, strip_target_for_pickle
    from soundrts.worldaction import Action

    class _Unit:
        world = None

    action = Action(_Unit(), None)
    state = action.__getstate__()
    assert "target" not in state
    restored = Action.__new__(Action)
    restored.__setstate__(state)
    assert restored.target is None

    action2 = Action.__new__(Action)
    action2.__dict__.update({"unit": _Unit()})
    strip_target_for_pickle(action2.__dict__)
    restore_target_after_pickle(action2)
    assert action2.target is None


def test_action_pickle_defers_target_until_world_objects_ready():
    from soundrts.save_pickle import _restore_target_with_world, restore_target_after_pickle
    from soundrts.worldaction import Action

    class _WorldPartial:
        pass

    class _Unit:
        pass

    world = _WorldPartial()
    target = type("T", (), {"id": "t1"})()
    unit = _Unit()
    unit.world = world

    action = Action.__new__(Action)
    action.__dict__.update({"unit": unit, "_pickle_target_id": "t1"})
    restore_target_after_pickle(action)
    assert action._pickle_target_id == "t1"
    assert action.target is None

    world.objects = {target.id: target}
    _restore_target_with_world(action, world)
    assert action.target is target


def test_rebuild_revives_blank_square_and_exit():
    """Regression: wiped Square/Exit __dict__ must not crash resume load."""
    from soundrts.save_pickle import rebuild_world_after_load
    from soundrts.worldexit import Exit
    from soundrts.worldroom import Square

    class _World:
        square_width = 15000
        square_cities = {}
        square_districts = {}
        square_names = {}
        players = []
        _ecs = None

        def _create_graphs(self):
            self.g = {"ground": {}, "air": {}, "water": {}}

    world = _World()
    world.objects = {}
    world.squares = []

    # Intact neighbor square 10,1 with exit facing east toward 11,1
    sq10 = Square.__new__(Square)
    sq10.__dict__.update(
        {
            "col": 10,
            "row": 1,
            "name": "10,1",
            "id": "35",
            "world": world,
            "place": world,
            "xmin": 150000,
            "ymin": 15000,
            "xmax": 165000,
            "ymax": 30000,
            "x": 157500,
            "y": 22500,
            "is_inside_place": False,
            "high_ground": False,
            "type_name": "",
            "terrain_speed": (100, 100),
            "terrain_cover": (0, 0),
            "title": [],
            "objects": [],
            "exits": [],
            "subcells": None,
        }
    )
    world.squares.append(sq10)
    world.objects["35"] = sq10

    partner = Exit.__new__(Exit)
    partner.__dict__.update(
        {
            "type_name": "path",
            "is_a_portal": False,
            "world": world,
            "x": 164999,
            "y": 22500,
            "o": 180,
            "place": sq10,
            "id": "322",
            "_other_side_id": "323",
            "_blockers": [],
            "is_blocked_by_forests": False,
            "action_target": None,
            "_previous_square": None,
        }
    )
    sq10.objects.append(partner)
    sq10.exits.append(partner)
    world.objects["322"] = partner

    # Blank square 11,1 and its wiped exit (as in a corrupted resume save)
    blank = Square.__new__(Square)
    world.squares.append(blank)
    world.objects["36"] = blank

    blank_exit = Exit.__new__(Exit)
    world.objects["323"] = blank_exit

    # Unit still sitting on the blank square with real map coords
    unit = type("U", (), {})()
    unit.place = blank
    unit.x = 177750
    unit.y = 22500
    unit.id = "400"
    world.objects["400"] = unit

    rebuild_world_after_load(world)

    assert blank.name == "11,1"
    assert world.grid["11,1"] is blank
    assert world.grid[(11, 1)] is blank
    assert blank_exit.place is blank
    assert blank_exit._other_side_id == "322"
    assert partner.other_side is blank_exit
    assert blank_exit in blank.exits


def test_cw1_mm_save_roundtrip():
    """Regression: 100x100 cw1-mm must save/load without stack overflow."""
    import os
    import sys
    import warnings
    from io import BytesIO

    import cloudpickle
    import pytest

    from soundrts.game import TrainingGame, cloudpickle_dump_game
    from soundrts.mapfile import Map
    from soundrts.world import World

    map_path = os.path.join("res", "multi", "cw1-mm.txt")
    if not os.path.exists(map_path):
        pytest.skip("cw1-mm map not bundled")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ResourceWarning)
        m = Map(map_path)
        game = TrainingGame(m, ["test", "easy"], ["human", "orc"], ["1", "2"])
        game.record_replay = False
        game.world = World(game.default_triggers, game.seed)
        game.world.load_and_build_map(m)
        game.world.populate_map(game.players, equivalents=True)

        buf = BytesIO()
        cloudpickle_dump_game(game, buf, square_count=len(game.world.squares))
    assert buf.tell() > 1024 * 1024

    saved = sys.getrecursionlimit()
    sys.setrecursionlimit(max(saved, 50000))
    try:
        buf.seek(0)
        loaded = cloudpickle.load(buf)
    finally:
        sys.setrecursionlimit(saved)
    assert len(loaded.world.squares) == 10000

