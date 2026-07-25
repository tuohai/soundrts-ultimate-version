"""Optional unit anim packs: Spine (if available) → spritesheet → icons → shapes."""

from pathlib import Path

from soundrts.clientgame.game_unit_anim import (
    AnimPack,
    clear_anim_caches,
    get_anim_pack,
    infer_anim_name,
    try_blit_unit_anim,
)


def test_infer_anim_name_defaults_idle():
    class _E:
        model = type("M", (), {"orders": []})()

    assert infer_anim_name(_E()) == "idle"


def test_infer_anim_gather_order():
    class _O:
        keyword = "gather"

    class _E:
        model = type("M", (), {"orders": [_O()]})()

    assert infer_anim_name(_E()) == "gather"


def test_missing_pack_returns_none():
    clear_anim_caches()
    assert get_anim_pack("definitely_no_such_unit_type_zz") is None


def test_gridview_anim_fallback_wired():
    text = Path("soundrts/clientgamegridview.py").read_text(encoding="utf-8")
    assert "_try_blit_map_anim" in text
    assert "try_blit_unit_anim" in text
    assert "_try_blit_map_icon" in text


def test_anim_pack_blit_without_assets_fails_soft():
    clear_anim_caches()
    pack = AnimPack("x", {"backend": "spritesheet", "sheet": "nope.png"}, "ui/anims/x")
    screen = __import__("pygame").Surface((64, 64))
    assert pack.blit(screen, "1", "idle", 32, 32, 24) is False
