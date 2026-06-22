"""按 mod 隔离的热键映射存储。"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_mods_use_separate_override_files(tmp_path, monkeypatch):
    from soundrts import hotkey_editor as he

    mod_dir = tmp_path / "hotkey_overrides"
    mod_dir.mkdir()
    base_path = mod_dir / "_base.json"
    sc_path = mod_dir / "starcraft.json"

    monkeypatch.setattr(he, "HOTKEY_OVERRIDES_DIR", str(mod_dir))
    monkeypatch.setattr(he, "get_hotkey_overrides_path", lambda: str(base_path))
    monkeypatch.setattr(he, "current_hotkey_overrides_mod_key", lambda: "_base")
    monkeypatch.setattr(
        he, "current_hotkey_overrides_path", lambda: str(base_path)
    )

    he.set_layer_override("global", "global.resource_status.resource1", "y")

    monkeypatch.setattr(he, "get_hotkey_overrides_path", lambda: str(sc_path))
    monkeypatch.setattr(he, "current_hotkey_overrides_mod_key", lambda: "starcraft")
    monkeypatch.setattr(
        he, "current_hotkey_overrides_path", lambda: str(sc_path)
    )

    he.set_layer_override("global", "global.resource_status.resource1", "q")
    assert he.get_layer_overrides("global") == {
        "global.resource_status.resource1": "q"
    }

    monkeypatch.setattr(he, "get_hotkey_overrides_path", lambda: str(base_path))
    assert he.get_layer_overrides("global") == {
        "global.resource_status.resource1": "y"
    }


def test_legacy_single_file_migrates_to_base(tmp_path, monkeypatch):
    from soundrts import hotkey_editor as he

    mod_dir = tmp_path / "hotkey_overrides"
    legacy = tmp_path / "hotkey_overrides.json"
    legacy.write_text(
        json.dumps(
            {
                "version": 1,
                "overrides": {"global": {"global.resource_status.resource1": "q"}},
            }
        ),
        encoding="utf-8",
    )
    base_path = mod_dir / "_base.json"

    monkeypatch.setattr(he, "HOTKEY_OVERRIDES_DIR", str(mod_dir))
    monkeypatch.setattr(he, "LEGACY_HOTKEY_OVERRIDES_PATH", str(legacy))
    monkeypatch.setattr(he, "current_hotkey_overrides_mod_key", lambda: "_base")
    monkeypatch.setattr(
        he, "current_hotkey_overrides_path", lambda: str(base_path)
    )
    monkeypatch.setattr(he, "get_hotkey_overrides_path", lambda: str(base_path))

    data = he.load_overrides_data()
    assert base_path.exists()
    assert data["overrides"]["global"]["global.resource_status.resource1"] == "q"


def test_paths_current_hotkey_overrides_path():
    from soundrts import paths

    assert paths.current_hotkey_overrides_path().endswith(".json")
    assert "hotkey_overrides" in paths.current_hotkey_overrides_path()


def test_hotkey_mapping_announces_mod():
    src = (ROOT / "soundrts" / "hotkey_remapping_menu.py").read_text(encoding="utf-8")
    assert "HOTKEY_OVERRIDES_FOR_MOD" in src
    assert "current_hotkey_overrides_mod_key" in src
    assert "hotkey_mod_label_msgs" in src


def test_mods_use_separate_hotkey_schemes(tmp_path, monkeypatch):
    from soundrts import hotkey_editor as he

    mod_dir = tmp_path / "hotkey_overrides"
    mod_dir.mkdir()
    base_path = mod_dir / "_base.json"
    sc_path = mod_dir / "starcraft.json"

    monkeypatch.setattr(he, "HOTKEY_OVERRIDES_DIR", str(mod_dir))
    monkeypatch.setattr(he, "get_hotkey_overrides_path", lambda: str(base_path))
    monkeypatch.setattr(he, "current_hotkey_overrides_mod_key", lambda: "_base")
    monkeypatch.setattr(
        he, "current_hotkey_overrides_path", lambda: str(base_path)
    )

    he.set_layered_hotkeys_scheme(0)
    assert he.get_layered_hotkeys_scheme() == 0

    monkeypatch.setattr(he, "get_hotkey_overrides_path", lambda: str(sc_path))
    monkeypatch.setattr(he, "current_hotkey_overrides_mod_key", lambda: "starcraft")
    monkeypatch.setattr(
        he, "current_hotkey_overrides_path", lambda: str(sc_path)
    )

    assert he.get_layered_hotkeys_scheme() == 1
    he.set_layered_hotkeys_scheme(0)
    assert he.get_layered_hotkeys_scheme() == 0

    monkeypatch.setattr(he, "get_hotkey_overrides_path", lambda: str(base_path))
    assert he.get_layered_hotkeys_scheme() == 0


def test_base_mod_falls_back_to_ini_layered_hotkeys(tmp_path, monkeypatch):
    from soundrts import config
    from soundrts import hotkey_editor as he

    mod_dir = tmp_path / "hotkey_overrides"
    mod_dir.mkdir()
    base_path = mod_dir / "_base.json"

    monkeypatch.setattr(he, "HOTKEY_OVERRIDES_DIR", str(mod_dir))
    monkeypatch.setattr(he, "get_hotkey_overrides_path", lambda: str(base_path))
    monkeypatch.setattr(he, "current_hotkey_overrides_mod_key", lambda: "_base")
    monkeypatch.setattr(
        he, "current_hotkey_overrides_path", lambda: str(base_path)
    )

    old = int(getattr(config, "layered_hotkeys", 1))
    try:
        config.layered_hotkeys = 0
        assert he.get_layered_hotkeys_scheme() == 0
        he.set_layered_hotkeys_scheme(1)
        assert he.get_layered_hotkeys_scheme() == 1
        config.layered_hotkeys = 0
        assert he.get_layered_hotkeys_scheme() == 1
    finally:
        config.layered_hotkeys = old


def test_hotkeys_menu_announces_mod():
    src = (ROOT / "soundrts" / "clientmain.py").read_text(encoding="utf-8")
    assert "def hotkeys_menu" in src
    block = src.split("def hotkeys_menu")[1].split("\ndef ")[0]
    assert "announce_hotkey_overrides_mod" in block
    assert "set_layered_hotkeys_scheme" in block
    assert "config.save()" not in block
    remapping = (ROOT / "soundrts" / "hotkey_remapping_menu.py").read_text(
        encoding="utf-8"
    )
    assert "def announce_hotkey_overrides_mod" in remapping
    announce = remapping.split("def announce_hotkey_overrides_mod")[1].split("\ndef ")[0]
    assert "voice.menu" in announce
    assert "voice.item" not in announce
    mapping = remapping.split("def hotkey_mapping_menu")[1].split("\ndef ")[0]
    assert "announce_hotkey_overrides_mod()" in mapping
