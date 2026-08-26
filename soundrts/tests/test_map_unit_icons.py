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
    assert "_png_name_candidates" in hud
    assert "architecture_set_for_entity" in gv
    # HUD icons stay separate from map sprites
    assert '_load_png_asset("icons"' in hud or "ui/icons" in hud


def test_map_sprite_files_exist():
    assert Path("res/ui/map/peasant.png").is_file()
    assert Path("res/ui/map/footman.png").is_file()
    assert Path("res/ui/map/README.txt").is_file()


def test_hud_icons_still_exist():
    assert Path("res/ui/icons/peasant.png").is_file()
    assert Path("res/ui/icons/train.png").is_file()


def test_aoe2_map_and_hud_icons_exist():
    assert Path("mods/aoe2/ui/map/town_center.png").is_file()
    assert Path("mods/aoe2/ui/map/militia.png").is_file()
    assert Path("mods/aoe2/ui/map/briton_knight.png").is_file()
    assert Path("mods/aoe2/ui/map/README.txt").is_file()
    assert Path("mods/aoe2/ui/icons/town_center.png").is_file()
    assert Path("mods/aoe2/ui/icons/militia.png").is_file()
    assert Path("mods/aoe2/ui/icons/train.png").is_file()
    assert Path("mods/aoe2/ui/icons/README.txt").is_file()


def test_architecture_parser_accepts_compact_lines():
    from soundrts.lib.arch_set import parse_architecture

    mapping, sets, neutral = parse_architecture(
        "neutral goldmine\nfoo_set alpha beta\n"
    )
    assert mapping["alpha"] == mapping["beta"] == "foo_set"
    assert "alpha" in sets["foo_set"]["civs"]
    assert "goldmine" in neutral


def test_aoe2_architecture_sets_match_de():
    from soundrts.lib.arch_set import parse_architecture

    text = Path("mods/aoe2/ui/architecture.txt").read_text(encoding="utf-8")
    mapping, sets, _neutral = parse_architecture(text)
    assert mapping["britons"] == mapping["franks"] == mapping["celts"]
    assert mapping["britons"] == "western_european"
    assert "britons" in sets["western_european"]["civs"]
    gen = Path("tools/gen_aoe2_hud_icons.py").read_text(encoding="utf-8")
    assert "ARCH_STYLES" not in gen
    assert "load_arch_packs" in gen
    assert mapping["chinese"] == mapping["japanese"] == "east_asian"
    assert mapping["aztecs"] == "mesoamerican"
    assert mapping["malians"] == "african"
    assert mapping["teutons"] == mapping["vikings"] == "central_european"
    assert mapping["byzantines"] == mapping["portuguese"] == "mediterranean"
    assert mapping["vietnamese"] == "southeast_asian"
    assert mapping["britons"] != mapping["chinese"]
    west = Path("mods/aoe2/ui/map/western_european/militia.png").read_bytes()
    east = Path("mods/aoe2/ui/map/east_asian/militia.png").read_bytes()
    meso = Path("mods/aoe2/ui/map/mesoamerican/militia.png").read_bytes()
    assert west != east
    assert west != meso
    assert Path("mods/aoe2/ui/map/western_european/militia.png").is_file()
    assert not Path("mods/aoe2/ui/map/britons/militia.png").is_file()
    hud = Path("soundrts/clientgame/game_hud.py").read_text(encoding="utf-8")
    assert "reversed(hits)" in hud
    anim = Path("soundrts/clientgame/game_unit_anim.py").read_text(encoding="utf-8")
    assert "reversed(hits)" in anim
