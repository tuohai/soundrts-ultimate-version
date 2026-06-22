"""地图浏览目标在界面切换后应保持选中。"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_map_browse_target_save_restore_helpers_exist():
    src = (ROOT / "soundrts" / "clientgame" / "interface_modes.py").read_text(
        encoding="utf-8"
    )
    assert "def save_map_browse_target" in src
    assert "def restore_map_browse_target" in src
    assert 'if old == "map" and mode != "map"' in src
    assert "save_map_browse_target(interface)" in src


def test_map_mode_entry_announces_square_overview():
    src = (ROOT / "soundrts" / "clientgame" / "interface_modes.py").read_text(
        encoding="utf-8"
    )
    assert "def _announce_map_mode_entry" in src
    assert "say_square" in src.split("def _announce_map_mode_entry")[1].split("\ndef ")[0]


def test_map_mode_entry_silent_restore_then_square_overview():
    src = (ROOT / "soundrts" / "clientgame" / "interface_modes.py").read_text(
        encoding="utf-8"
    )
    block = src.split("def _set_mode")[1].split("\ndef ")[0]
    assert "restore_map_browse_target(interface, announce=False)" in block
    assert "_announce_map_mode_entry(interface)" in block
    assert "restore_map_browse_target(interface, announce=True)" not in block
    map_branch = block.split('if mode == "map"')[1].split("elif announce")[0]
    assert "say_target" not in map_branch


def test_f9_f11_in_global_bindings():
    text = (ROOT / "res" / "ui" / "global_bindings.txt").read_text(encoding="utf-8")
    assert "F9: objectives 1" in text
    assert "F11: say_players" in text
    help_text = (ROOT / "res" / "ui" / "help_bindings.txt").read_text(encoding="utf-8")
    assert "F9: objectives" not in help_text
    assert "F11: say_players" not in help_text


def test_escape_no_longer_clears_target_before_map():
    src = (ROOT / "soundrts" / "clientgame" / "interface_modes.py").read_text(
        encoding="utf-8"
    )
    handle = src.split("def handle_escape")[1].split("\ndef ")[0]
    assert "_select_and_say_square" not in handle
    assert "cmd_enter_map_mode(interface)" in handle


def test_cycle_square_target_saves_browse_selection():
    src = (ROOT / "soundrts" / "clientgame" / "game_unit_control.py").read_text(
        encoding="utf-8"
    )
    block = src.split("def _cycle_square_target")[1].split("def cmd_select_deposit")[0]
    assert "save_map_browse_target" in block
