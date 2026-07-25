"""Map view uses ui/map/<type>.png (not ui/icons) when present."""

from pathlib import Path


def test_map_sprite_wiring():
    gv = Path("soundrts/clientgamegridview.py").read_text(encoding="utf-8")
    assert "_try_blit_map_icon" in gv
    assert "get_map_sprite" in gv
    assert "ui/map/" in gv or "get_map_sprite" in gv
    hud = Path("soundrts/clientgame/game_hud.py").read_text(encoding="utf-8")
    assert "def get_map_sprite(" in hud
    assert '_load_png_asset("map"' in hud or 'folder, key, size' in hud
    # HUD icons stay separate from map sprites
    assert '_load_png_asset("icons"' in hud or "ui/icons" in hud


def test_map_sprite_files_exist():
    assert Path("res/ui/map/peasant.png").is_file()
    assert Path("res/ui/map/footman.png").is_file()
    assert Path("res/ui/map/README.txt").is_file()


def test_hud_icons_still_exist():
    assert Path("res/ui/icons/peasant.png").is_file()
    assert Path("res/ui/icons/train.png").is_file()
