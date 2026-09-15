"""Optional unit anim packs: Spine (if available) → spritesheet → icons → shapes."""

from pathlib import Path

import pygame

from soundrts.clientgame.game_unit_anim import (
    AnimPack,
    clear_anim_caches,
    get_anim_pack,
    infer_anim_name,
    try_blit_unit_anim,
    _facing_dir_index,
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


def test_infer_go_order():
    class _O:
        keyword = "go"

    class _E:
        model = type("M", (), {"orders": [_O()]})()

    assert infer_anim_name(_E()) == "walk"


def test_facing_dir_index_quadrants():
    assert _facing_dir_index(0, 4) == 0
    assert _facing_dir_index(90, 4) == 1
    assert _facing_dir_index(180, 4) == 2
    assert _facing_dir_index(270, 4) == 3
    assert _facing_dir_index(180, 1) == 0


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
    screen = pygame.Surface((64, 64))
    assert pack.blit(screen, "1", "idle", 32, 32, 24) is False


def test_spritesheet_blit_with_fake_sheet(monkeypatch):
    clear_anim_caches()
    sheet = pygame.Surface((128, 32), pygame.SRCALPHA)
    sheet.fill((200, 40, 40, 255))

    def fake_load(rel):
        if rel.endswith("sheet.png"):
            return sheet.copy()
        return None

    monkeypatch.setattr(
        "soundrts.clientgame.game_unit_anim._load_surface", fake_load
    )
    meta = {
        "backend": "spritesheet",
        "sheet": "sheet.png",
        "frame_w": 32,
        "frame_h": 32,
        "fps": 8,
        "animations": {"idle": {"row": 0, "frames": 4}},
    }
    pack = AnimPack("t", meta, "ui/anims/t")
    screen = pygame.Surface((64, 64))
    assert pack.blit(screen, "1", "idle", 32, 32, 24) is True


def test_spine_falls_back_to_spritesheet(monkeypatch):
    clear_anim_caches()
    sheet = pygame.Surface((128, 32), pygame.SRCALPHA)
    sheet.fill((40, 200, 40, 255))

    def fake_load(rel):
        if rel.endswith("sheet.png"):
            return sheet.copy()
        return None

    monkeypatch.setattr(
        "soundrts.clientgame.game_unit_anim._load_surface", fake_load
    )
    meta = {
        "backend": "spine",
        "spine": {"skeleton": "skeleton.json", "atlas": "skeleton.atlas"},
        "sheet": "sheet.png",
        "frame_w": 32,
        "frame_h": 32,
        "fps": 8,
        "animations": {"idle": {"row": 0, "frames": 4}},
    }
    pack = AnimPack("sp", meta, "ui/anims/sp")
    screen = pygame.Surface((64, 64))
    assert pack.backend == "spine"
    assert pack.blit(screen, "1", "idle", 32, 32, 24) is True
    assert pack.backend == "spritesheet"


def _activate_all_mods():
    """Enable all non-soundpack mods so that mod-layer anims resolve during tests."""
    try:
        from soundrts.lib.resource import res
        available = res.packages.mods()
        non_soundpacks = [m.name for m in available if not m.is_a_soundpack()]
        current = (res.mods or "").split(",")
        missing = [m for m in non_soundpacks if m not in current]
        if missing:
            res.mods = ",".join(current + missing)
            res._reload()
    except Exception:
        pass


def _anim_exists(rel: str) -> bool:
    """Match runtime lookup: try mod layers first, then res/."""
    _activate_all_mods()
    try:
        from soundrts.lib.resource import res
        for _root, _path in res.paths(rel, localize=False):
            try:
                if _root.isfile(_path):
                    return True
            except Exception:
                pass
    except Exception:
        pass
    return Path(os.path.join("res", rel.replace("/", os.sep))).is_file()


def _read_meta_text(rel: str) -> str:
    """Read a resource via runtime paths (cwd-independent)."""
    _activate_all_mods()
    try:
        from soundrts.lib.resource import res
        for _root, _path in res.paths(rel, localize=False):
            try:
                if not _root.isfile(_path):
                    continue
                with _root.open_binary(_path) as fh:
                    return fh.read().decode("utf-8")
            except Exception:
                continue
    except Exception:
        pass
    p = Path(os.path.join("res", rel.replace("/", os.sep)))
    if p.is_file():
        return p.read_text(encoding="utf-8")
    return ""


def test_starter_anim_packs_exist():
    # Match runtime resolution via the resource stack (all mods → res/).
    assert _anim_exists("ui/anims/peasant/meta.json")
    assert _anim_exists("ui/anims/peasant/sheet.png")
    assert _anim_exists("ui/anims/footman/sheet.png")
    assert _anim_exists("ui/anims/militia/sheet.png")
    # Meta content: prefer mod layer, fall back to res/
    meta_text = _read_meta_text("ui/anims/peasant/meta.json")
    assert meta_text, "peasant meta.json must resolve via mods or res/"
    assert '"dirs": 4' in meta_text
    assert Path("tools/gen_unit_anims.py").is_file()
