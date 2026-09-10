"""审计：1.5 / 1.5.0.1–1.5.0.4 — 野兽警报、信号弹、触发器、条约、阵型、命中率/闪避率改名。"""
from __future__ import annotations

from pathlib import Path

_FOLDED_VERSIONS = (
    "1.5.0.5",
    "1.5.0.6",
    "1.5.0.7",
    "1.5.0.8",
    "1.5.0.9",
    "1.5.0.10",
    "1.4.9.10",
    "1.4.9.11",
    "1.4.9.12",
    "1.4.9.13",
    "1.4.9.14",
)


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_between(lang: str, start_heading: str, end_heading: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("\n" + start_heading + "\n")
    rest = text[start:]
    next_idx = rest.find("\n" + end_heading + "\n")
    return rest if next_idx == -1 else rest[:next_idx]


def _section_1504(lang: str) -> str:
    return _section_between(lang, "1.5.0.4", "1.5.0.3")


def _section_1503(lang: str) -> str:
    return _section_between(lang, "1.5.0.3", "1.5.0.2")


def _section_1502(lang: str) -> str:
    return _section_between(lang, "1.5.0.2", "1.5.0.1")


def _section_1501(lang: str) -> str:
    return _section_between(lang, "1.5.0.1", "1.5")


def _section_15(lang: str) -> str:
    return _section_between(lang, "1.5", "1.4.9.9")


def test_version_is_1504():
    assert 'VERSION = "1.5.0.4"' in _source("soundrts", "version.py")


def test_all_relnotes_have_1504_then_1503_then_1502_then_1501_then_15_before_1499():
    for lang in ("zh", "en", "es", "it", "pt-BR"):
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert src.index("\n1.5.0.4\n") < src.index("\n1.5.0.3\n"), lang
        assert src.index("\n1.5.0.3\n") < src.index("\n1.5.0.2\n"), lang
        assert src.index("\n1.5.0.2\n") < src.index("\n1.5.0.1\n"), lang
        assert src.index("\n1.5.0.1\n") < src.index("\n1.5\n"), lang
        assert src.index("\n1.5\n") < src.index("\n1.4.9.9"), lang
        for folded in _FOLDED_VERSIONS:
            assert f"\n{folded}\n" not in src, (lang, folded)
        top = _section_1504(lang)
        for folded in _FOLDED_VERSIONS:
            assert folded not in top, (lang, folded)


def test_zh_relnotes_1504_formation_ranks_rule_driven():
    s = _section_1504("zh")
    assert "formation_ranks" in s
    assert "formation_rank_" in s
    assert "formation_default_rank" in s
    assert "formation_range_rank" in s
    assert "formation_front_rank" in s
    assert "rdg_range" in s
    assert "mdg_range" in s
    assert "world_formation.py" in s
    assert "definitions.py" in s
    assert "mods/aoe2/rules.txt" in s
    assert "test_world_formation.py" in s
    assert "test_changelog_15.py" in s
    assert "modding.rst" in s


def test_en_es_it_pt_relnotes_1504_formation_ranks_rule_driven():
    for lang in ("en", "es", "it", "pt-BR"):
        s = _section_1504(lang)
        assert "formation_ranks" in s, lang
        assert "formation_rank_" in s, lang
        assert "formation_default_rank" in s, lang
        assert "formation_range_rank" in s, lang
        assert "formation_front_rank" in s, lang
        assert "rdg_range" in s, lang
        assert "mdg_range" in s, lang
        assert "world_formation.py" in s, lang
        assert "definitions.py" in s, lang
        assert "mods/aoe2/rules.txt" in s, lang
        assert "test_world_formation.py" in s, lang
        assert "test_changelog_15.py" in s, lang
        assert "modding.rst" in s, lang


def test_modding_docs_mention_formation_ranks():
    for lang in ("zh", "en", "es", "it", "pt-BR"):
        modding = _source("doc_src", "src", lang, "mod", "modding.rst")
        assert "formation_ranks" in modding, lang
        assert "formation_default_rank" in modding, lang
        assert "formation_range_rank" in modding, lang
        assert "formation_front_rank" in modding, lang
        assert "formation_rank_" in modding, lang


def test_zh_relnotes_1504_hit_rate_rename():
    s = _section_1504("zh")
    assert "mdg_hit_rate" in s
    assert "rdg_hit_rate" in s
    assert "mdg_cover" in s
    assert "rdg_cover" in s
    assert "cover_vs" in s
    assert "hit_miss.py" in s
    assert "definitions.py" in s
    assert "mods/aoe2/rules.txt" in s
    assert "i18n/tts.pot" in s
    assert "tts-*.po" in s
    assert "msgid" in s
    assert "test_unit_vs_params_runtime.py" in s
    assert "test_changelog_15.py" in s
    assert "modding.rst" in s


def test_en_es_it_pt_relnotes_1504_hit_rate_rename():
    for lang in ("en", "es", "it", "pt-BR"):
        s = _section_1504(lang)
        assert "mdg_hit_rate" in s, lang
        assert "rdg_hit_rate" in s, lang
        assert "mdg_cover" in s, lang
        assert "rdg_cover" in s, lang
        assert "cover_vs" in s, lang
        assert "hit_miss.py" in s, lang
        assert "definitions.py" in s, lang
        assert "mods/aoe2/rules.txt" in s, lang
        assert "i18n/tts.pot" in s, lang
        assert "tts-*.po" in s, lang
        assert "msgid" in s, lang
        assert "test_unit_vs_params_runtime.py" in s, lang
        assert "test_changelog_15.py" in s, lang
        assert "modding.rst" in s, lang


def test_engine_uses_hit_rate_not_cover_alias():
    defs = _source("soundrts", "definitions.py")
    hit = _source("soundrts", "combat", "hit_miss.py")
    aoe2 = _source("mods", "aoe2", "rules.txt")
    assert '"mdg_hit_rate"' in defs
    assert '"rdg_hit_rate"' in defs
    assert "mdg_cover" not in defs
    assert "rdg_cover" not in defs
    assert "_get_melee_hit_rate_vs" in hit
    assert "_get_ranged_hit_rate_vs" in hit
    assert "_get_melee_cover_vs" not in hit
    assert "mdg_cover" not in hit
    assert "rdg_hit_rate" in aoe2
    assert "rdg_cover" not in aoe2
    pot = _source("i18n", "tts.pot")
    assert 'msgid "mdg_hit_rate_vs"' in pot
    assert 'msgid "rdg_hit_rate_vs"' in pot
    assert 'msgid "mdg_hit_rate_on_terrain"' in pot
    assert 'msgid "rdg_hit_rate_on_terrain"' in pot
    assert 'msgid "mdg_cover_vs"' not in pot
    assert 'msgid "rdg_cover_vs"' not in pot
    assert 'msgid "mdg_cover_on_terrain"' not in pot
    assert 'msgid "rdg_cover_on_terrain"' not in pot
    tts = _source("res", "ui", "tts.txt")
    assert "mdg_hit_rate_on_terrain" in tts
    assert "rdg_hit_rate_on_terrain" in tts
    assert "mdg_cover_on_terrain" not in tts
    for name in (
        "tts-zh.po", "tts-vi.po", "tts-sk.po", "tts-ru.po", "tts-pt-BR.po",
        "tts-pl.po", "tts-it.po", "tts-fr.po", "tts-es.po", "tts-de.po",
        "tts-cs.po", "tts-be.po",
    ):
        po = _source("i18n", name)
        assert 'msgid "mdg_hit_rate_vs"' in po, name
        assert 'msgid "mdg_cover_vs"' not in po, name
        assert "#. MDG_COVER_VS" in po, name
    for lang in ("zh", "en", "es", "it", "pt-BR"):
        modding = _source("doc_src", "src", lang, "mod", "modding.rst")
        assert "mdg_hit_rate" in modding, lang
        assert "mdg_cover" in modding, lang


def test_zh_relnotes_1504_dodge_rate_rename():
    s = _section_1504("zh")
    assert "mdg_dodge_rate" in s
    assert "rdg_dodge_rate" in s
    assert "mdg_dodge" in s
    assert "rdg_dodge" in s
    assert "dodge_vs" in s
    assert "MDG_DODGE" in s
    assert "hit_miss.py" in s
    assert "definitions.py" in s
    assert "worldweapon.py" in s
    assert "i18n/tts.pot" in s
    assert "tts-*.po" in s
    assert "msgid" in s
    assert "test_unit_vs_params_runtime.py" in s
    assert "test_changelog_15.py" in s
    assert "modding.rst" in s


def test_en_es_it_pt_relnotes_1504_dodge_rate_rename():
    for lang in ("en", "es", "it", "pt-BR"):
        s = _section_1504(lang)
        assert "mdg_dodge_rate" in s, lang
        assert "rdg_dodge_rate" in s, lang
        assert "mdg_dodge" in s, lang
        assert "rdg_dodge" in s, lang
        assert "dodge_vs" in s, lang
        assert "MDG_DODGE" in s, lang
        assert "hit_miss.py" in s, lang
        assert "definitions.py" in s, lang
        assert "worldweapon.py" in s, lang
        assert "i18n/tts.pot" in s, lang
        assert "tts-*.po" in s, lang
        assert "msgid" in s, lang
        assert "test_unit_vs_params_runtime.py" in s, lang
        assert "test_changelog_15.py" in s, lang
        assert "modding.rst" in s, lang


def test_engine_uses_dodge_rate_not_dodge_alias():
    defs = _source("soundrts", "definitions.py")
    hit = _source("soundrts", "combat", "hit_miss.py")
    assert '"mdg_dodge_rate"' in defs
    assert '"rdg_dodge_rate"' in defs
    assert '"mdg_dodge"' not in defs
    assert '"rdg_dodge"' not in defs
    assert "mdg_dodge_rate" in hit
    assert "rdg_dodge_rate" in hit
    assert "mdg_dodge_rate_vs" in hit
    assert "rdg_dodge_rate_vs" in hit
    assert "mdg_dodge_rate_on_terrain" in hit
    assert "rdg_dodge_rate_on_terrain" in hit
    pot = _source("i18n", "tts.pot")
    assert 'msgid "mdg_dodge_rate_vs"' in pot
    assert 'msgid "rdg_dodge_rate_vs"' in pot
    assert 'msgid "mdg_dodge_rate_on_terrain"' in pot
    assert 'msgid "rdg_dodge_rate_on_terrain"' in pot
    assert 'msgid "mdg_dodge_vs"' not in pot
    assert 'msgid "rdg_dodge_vs"' not in pot
    assert 'msgid "mdg_dodge_on_terrain"' not in pot
    assert 'msgid "rdg_dodge_on_terrain"' not in pot
    tts = _source("res", "ui", "tts.txt")
    assert "mdg_dodge_rate_on_terrain" in tts
    assert "rdg_dodge_rate_on_terrain" in tts
    assert "mdg_dodge_on_terrain" not in tts
    style = _source("res", "ui", "style.txt")
    assert "rdg_dodge 1040" in style
    for name in (
        "tts-zh.po", "tts-vi.po", "tts-sk.po", "tts-ru.po", "tts-pt-BR.po",
        "tts-pl.po", "tts-it.po", "tts-fr.po", "tts-es.po", "tts-de.po",
        "tts-cs.po", "tts-be.po",
    ):
        po = _source("i18n", name)
        assert 'msgid "mdg_dodge_rate_vs"' in po, name
        assert 'msgid "mdg_dodge_vs"' not in po, name
        assert "#. MDG_DODGE_VS" in po, name
    for lang in ("zh", "en", "es", "it", "pt-BR"):
        modding = _source("doc_src", "src", lang, "mod", "modding.rst")
        assert "mdg_dodge_rate" in modding, lang
        assert "mdg_dodge" in modding, lang


def test_zh_relnotes_1503_formation_formed_bonuses():
    s = _section_1503("zh")
    assert "formation_ranks_formed" in s
    assert "FORMATION_SLOT_ARRIVE_MM" in s
    assert "keep_pace" in s
    assert "world_formation.py" in s
    assert "world_attributes.py" in s
    assert "world_movement.py" in s
    assert "test_world_formation.py" in s
    assert "test_changelog_15.py" in s


def test_en_es_it_pt_relnotes_1503_formation_formed_bonuses():
    for lang in ("en", "es", "it", "pt-BR"):
        s = _section_1503(lang)
        assert "formation_ranks_formed" in s, lang
        assert "FORMATION_SLOT_ARRIVE_MM" in s, lang
        assert "keep_pace" in s, lang
        assert "world_formation.py" in s, lang
        assert "world_attributes.py" in s, lang
        assert "world_movement.py" in s, lang
        assert "test_world_formation.py" in s, lang
        assert "test_changelog_15.py" in s, lang


def test_zh_relnotes_1503_agro_on_sight():
    s = _section_1503("zh")
    assert "agro_on_sight" in s
    assert "formation_stand_ground" in s
    assert "unit_agro_on_sight" in s
    assert "_notify_units_in_place" in s
    assert "last_attacker" in s
    assert "pursue_attacker" in s
    assert "test_hunting.py" in s
    assert "definitions.py" in s


def test_en_es_it_pt_relnotes_1503_agro_on_sight():
    for lang in ("en", "es", "it", "pt-BR"):
        s = _section_1503(lang)
        assert "agro_on_sight" in s, lang
        assert "formation_stand_ground" in s, lang
        assert "unit_agro_on_sight" in s, lang
        assert "_notify_units_in_place" in s, lang
        assert "last_attacker" in s, lang
        assert "pursue_attacker" in s, lang
        assert "test_hunting.py" in s, lang
        assert "definitions.py" in s, lang


def test_hunting_and_modding_docs_mention_agro_on_sight():
    for lang in ("zh", "en", "es", "it", "pt-BR"):
        hunting = _source("doc_src", "src", lang, "player", "hunting.rst")
        modding = _source("doc_src", "src", lang, "mod", "modding.rst")
        assert "agro_on_sight" in hunting, lang
        assert "agro_on_sight" in modding, lang


def test_zh_relnotes_1503_formation_counters():
    s = _section_1503("zh")
    assert "mdg_vs" in s
    assert "rdf_vs" in s
    assert "formation_wedge" in s
    assert "cone" in s
    assert "class formation" in s
    assert "world_formation.py" in s
    assert "damage_calculation.py" in s
    assert "formation_detail.py" in s
    assert "test_world_formation.py" in s
    assert "test_changelog_15.py" in s


def test_en_es_it_pt_relnotes_1503_formation_counters():
    for lang in ("en", "es", "it", "pt-BR"):
        s = _section_1503(lang)
        assert "mdg_vs" in s, lang
        assert "rdf_vs" in s, lang
        assert "formation_wedge" in s, lang
        assert "cone" in s, lang
        assert "class formation" in s, lang
        assert "world_formation.py" in s, lang
        assert "damage_calculation.py" in s, lang
        assert "formation_detail.py" in s, lang
        assert "test_world_formation.py" in s, lang
        assert "test_changelog_15.py" in s, lang


def test_zh_relnotes_1502_treaty_and_formations():
    s = _section_1502("zh")
    assert "TREATY_MINUTE_CHOICES" in s
    assert "90" in s
    assert "treaty.py" in s
    assert "parse_custom_treaty_minutes" in s
    assert "ENTER_TREATY_MINUTES" in s
    assert "formations 1" in s
    assert "class formation" in s
    assert "shape" in s
    assert "ring" in s
    assert "arc" in s
    assert "circle" in s
    assert "radius" in s
    assert "arc_span" in s
    assert "set_formation" in s
    assert "cycle_formation" in s
    assert "CTRL SHIFT f" in s
    assert "hotkey_catalogs.py" in s
    assert "apply_combat_formation" in s
    assert "AttackAction" in s
    assert "_formation_speed_cap" in s
    assert "actual_speed" in s
    assert "chase" in s
    assert "formation_blocker" in s
    assert "break_formation_hold" in s
    assert "_near_enough_to_aim" in s
    assert "guard" in s
    assert "offensive" in s
    assert "apply_idle_rearrange" in s
    assert "_units_grouped_by_place" in s
    assert "mdg" in s
    assert "rdf" in s
    assert "mdg_vs" in s
    assert "20%" in s
    assert "speed" in s
    assert "keep_pace" in s
    assert "damage_calculation.py" in s
    assert "world_formation.py" in s
    assert "test_world_formation.py" in s
    assert "test_formation_combat.py" in s
    assert "AVAILABLE_FORMATIONS" in s
    assert "formation_detail.py" in s
    assert "test_formation_attributes_ui.py" in s
    assert "hp 20% cavalry" in s
    assert "test_hp_max_bonus_current_hp.py" in s
    assert "set_var" not in s
    assert "layered_hotkeys" not in s


def test_en_es_it_pt_relnotes_1502_treaty_and_formations():
    for lang in ("en", "es", "it", "pt-BR"):
        s = _section_1502(lang)
        assert "TREATY_MINUTE_CHOICES" in s, lang
        assert "90" in s, lang
        assert "treaty.py" in s, lang
        assert "parse_custom_treaty_minutes" in s, lang
        assert "ENTER_TREATY_MINUTES" in s, lang
        assert "formations 1" in s, lang
        assert "class formation" in s, lang
        assert "shape" in s, lang
        assert "ring" in s, lang
        assert "arc" in s, lang
        assert "circle" in s, lang
        assert "radius" in s, lang
        assert "arc_span" in s, lang
        assert "set_formation" in s, lang
        assert "cycle_formation" in s, lang
        assert "CTRL SHIFT f" in s, lang
        assert "hotkey_catalogs.py" in s, lang
        assert "apply_combat_formation" in s, lang
        assert "AttackAction" in s, lang
        assert "_formation_speed_cap" in s, lang
        assert "actual_speed" in s, lang
        assert "chase" in s, lang
        assert "formation_blocker" in s, lang
        assert "break_formation_hold" in s, lang
        assert "_near_enough_to_aim" in s, lang
        assert "guard" in s, lang
        assert "offensive" in s, lang
        assert "apply_idle_rearrange" in s, lang
        assert "_units_grouped_by_place" in s, lang
        assert "mdg" in s, lang
        assert "rdf" in s, lang
        assert "mdg_vs" in s, lang
        assert "20%" in s, lang
        assert "speed" in s, lang
        assert "keep_pace" in s, lang
        assert "damage_calculation.py" in s, lang
        assert "world_formation.py" in s, lang
        assert "test_world_formation.py" in s, lang
        assert "test_formation_combat.py" in s, lang
        assert "AVAILABLE_FORMATIONS" in s, lang
        assert "formation_detail.py" in s, lang
        assert "test_formation_attributes_ui.py" in s, lang
        assert "hp 20% cavalry" in s, lang
        assert "test_hp_max_bonus_current_hp.py" in s, lang
        assert "set_var" not in s, lang
        assert "layered_hotkeys" not in s, lang


def test_zh_relnotes_1501_session_topics():
    s = _section_1501("zh")
    assert "set_var" in s
    assert "trigger_loop_limit" in s
    assert "on_death_add_var" in s
    assert "trigger_script.py" in s
    assert "test_trigger_script.py" in s
    assert "layered_hotkeys" in s
    assert "经典" in s
    assert "TREATY_MINUTE_CHOICES" not in s
    assert "treaty.py" not in s


def test_en_es_it_pt_relnotes_1501_session_topics():
    for lang in ("en", "es", "it", "pt-BR"):
        s = _section_1501(lang)
        assert "set_var" in s, lang
        assert "trigger_loop_limit" in s, lang
        assert "on_death_add_var" in s, lang
        assert "trigger_script.py" in s, lang
        assert "test_trigger_script.py" in s, lang
        assert "layered_hotkeys" in s, lang
        assert "TREATY_MINUTE_CHOICES" not in s, lang
        assert "treaty.py" not in s, lang


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
    assert "set_var" not in s
    assert "layered_hotkeys" not in s


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
        assert "set_var" not in s, lang
        assert "layered_hotkeys" not in s, lang


def test_layered_hotkeys_defaults_to_classic():
    assert '("general", "layered_hotkeys", 0, int)' in _source("soundrts", "config.py")
    he = _source("soundrts", "hotkey_editor.py")
    block = he.split("def get_layered_hotkeys_scheme")[1].split("\ndef ")[0]
    assert 'getattr(config, "layered_hotkeys", 0)' in block
    assert "return 0" in block


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


def test_engine_wires_trigger_script():
    script = _source("soundrts", "trigger_script.py")
    triggers = _source("soundrts", "worldplayerbase", "triggers.py")
    world_map = _source("soundrts", "world", "world_map.py")
    assert "parse_trigger_tree" in script
    assert "should_fire_repeat" in script
    assert "lang_set_var" in triggers or "lang_set_global" in triggers
    assert "parse_trigger_tree" in world_map
