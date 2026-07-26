"""Visual backpack / equipment HUD wiring."""

from pathlib import Path


def test_gear_hud_module_exists():
    text = Path("soundrts/clientgame/game_gear_hud.py").read_text(encoding="utf-8")
    assert "def draw_gear_hud(" in text
    assert "def handle_gear_click(" in text
    assert "def draw_gear_open_buttons(" in text
    assert "cmd_toggle_gear_screen" in text


def test_hud_and_input_wire_gear():
    hud = Path("soundrts/clientgame/game_hud.py").read_text(encoding="utf-8")
    assert "draw_gear_hud" in hud
    assert "open_inv" in hud
    assert "open_eq" in hud
    inp = Path("soundrts/clientgame/game_input_handler.py").read_text(encoding="utf-8")
    assert "gear_screen_active" in inp
    assert "handle_gear_click" in inp
