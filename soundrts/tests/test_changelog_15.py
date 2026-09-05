"""审计：1.5.0.0 — 野兽警报、信号弹快捷键/语音/规则、无背包不报空。"""
from __future__ import annotations

from pathlib import Path


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_15(lang: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("\n1.5.0.0\n")
    rest = text[start:]
    next_idx = rest.find("\n1.4.9.9")
    return rest if next_idx == -1 else rest[:next_idx]


def test_version_is_15():
    assert 'VERSION = "1.5.0.0"' in _source("soundrts", "version.py")


def test_all_relnotes_have_15_heading_before_1499():
    for lang in ("zh", "en", "es", "it", "pt-BR"):
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert src.index("\n1.5.0.0\n") < src.index("\n1.4.9.9"), lang
        top = _section_15(lang)
        for folded in ("1.4.9.10", "1.4.9.11", "1.4.9.12", "1.4.9.13", "1.4.9.14"):
            assert folded not in top, (lang, folded)


def test_zh_relnotes_15_session_topics():
    s = _section_15("zh")
    assert "alert_animal" in s
    assert "attack_warning_wild_animal" in s
    assert "test_wild_attack_alert.py" in s
    assert "CTRL SHIFT n: flare" in s
    assert "signal_flare 1" in s
    assert "signal_flare_title" in s
    assert "SIGNAL_FLARE" in s
    assert "flare_announce.py" in s
    assert "test_flare_announce.py" in s
    assert "hotkey_editor.py" in s
    assert "inventory_capacity" in s
    assert "EMPTY_BACKPACK" in s
    assert "unit_has_inventory" in s
    assert "test_inventory_backpack.py" in s
    assert "test_changelog_15.py" in s


def test_en_es_it_pt_relnotes_15_session_topics():
    for lang in ("en", "es", "it", "pt-BR"):
        s = _section_15(lang)
        assert "alert_animal" in s, lang
        assert "attack_warning_wild_animal" in s, lang
        assert "test_wild_attack_alert.py" in s, lang
        assert "CTRL SHIFT n: flare" in s, lang
        assert "signal_flare 1" in s, lang
        assert "signal_flare_title" in s, lang
        assert "SIGNAL_FLARE" in s, lang
        assert "flare_announce.py" in s, lang
        assert "test_flare_announce.py" in s, lang
        assert "hotkey_editor.py" in s, lang
        assert "inventory_capacity" in s, lang
        assert "EMPTY_BACKPACK" in s, lang
        assert "unit_has_inventory" in s, lang
        assert "test_inventory_backpack.py" in s, lang
        assert "test_changelog_15.py" in s, lang


def test_engine_wires_alert_animal_style():
    combat = _source("soundrts", "clientgameentity", "combat.py")
    events = _source("soundrts", "clientgameentity", "events.py")
    creature = _source("soundrts", "worldunit", "worldcreature.py")
    defs = _source("soundrts", "definitions.py")
    style = _source("mods", "aoe2", "ui", "style.txt")
    rules = _source("mods", "aoe2", "rules.txt")
    assert "def attacker_style_lineage" in combat
    assert "alert_%s" in combat
    assert "self.unit_attacked_alert(attacker_type, attacker_id)" in events
    assert "wild_attack_alert" not in creature
    assert "wild_attack_alert" not in defs
    assert "def animal" in style
    assert "alert_animal attack_warning_wild_animal" in style
    assert "wild_attack_alert" not in rules


def test_aoe2_overlay_binds_flare():
    for name in ("global_bindings.txt", "legacy_bindings.txt", "rpg_bindings.txt"):
        text = _source("mods", "aoe2", "ui", name)
        assert "CTRL SHIFT n: flare" in text, name


def test_hotkey_catalogs_list_flare():
    from soundrts.hotkey_catalogs import _build_classic_catalog, _build_map_catalog
    from soundrts.hotkey_editor import GLOBAL_PRIMARY_CATALOG, get_default_key
    from soundrts import msgparts as mp

    global_ids = [bid for bid, _ in GLOBAL_PRIMARY_CATALOG]
    assert "global.flare" in global_ids
    classic_ids = [bid for bid, _ in _build_classic_catalog()]
    assert "classic.flare" in classic_ids
    map_ids = [bid for bid, _ in _build_map_catalog()]
    assert "map.flare" in map_ids
    assert mp.HOTKEY_SIGNAL_FLARE == [5842]
    assert get_default_key("global.flare") == "CTRL SHIFT n"


def test_engine_wires_flare_voice():
    cmd = _source("soundrts", "worldplayerbase", "commands.py")
    res = _source("soundrts", "clientgame", "game_resources.py")
    announce = _source("soundrts", "flare_announce.py")
    assert 'player.push("flare", square_id, getattr(self, "number", None))' in cmd
    assert "flare_voice_msg" in res
    assert "voice.info" in res
    assert "def flare_voice_msg" in announce
    assert "mp.SIGNAL_FLARE" in announce
    assert "mp.AT" in announce


def test_aoe2_rules_and_style_configure_flare():
    rules = _source("mods", "aoe2", "rules.txt")
    style = _source("mods", "aoe2", "ui", "style.txt")
    defs = _source("soundrts", "definitions.py")
    announce = _source("soundrts", "flare_announce.py")
    assert "signal_flare 1" in rules
    assert "signal_flare signal_flare" in style
    assert "signal_flare_title 5842" in style
    assert '"signal_flare"' in defs
    assert "def signal_flare_enabled" in announce
    assert "def flare_title_msgs" in announce
    cmd = _source("soundrts", "worldplayerbase", "commands.py")
    assert "signal_flare_enabled" in cmd


def test_engine_gates_gear_screens_on_capacity():
    inv = _source("soundrts", "attributes", "inventory_screen.py")
    eq = _source("soundrts", "attributes", "equipment_screen.py")
    hud = _source("soundrts", "clientgame", "game_gear_hud.py")
    assert "def unit_has_inventory" in inv
    assert "if not unit_has_inventory(u):" in inv
    assert "if not unit_has_inventory(u):" in eq
    assert "unit_has_inventory" in hud
