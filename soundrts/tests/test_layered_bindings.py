"""分层界面热键绑定测试。"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

MODE_FILES = (
    "global_bindings.txt",
    "unit_bindings.txt",
    "building_bindings.txt",
    "command_bindings.txt",
    "skill_bindings.txt",
    "rpg_bindings.txt",
    "help_bindings.txt",
    "map_bindings.txt",
    "diplomacy_bindings.txt",
)


def test_layered_binding_files_exist():
    ui = ROOT / "res" / "ui"
    for name in MODE_FILES:
        assert (ui / name).exists(), name


def test_skill_bindings_browse_only():
    text = (ROOT / "res" / "ui" / "skill_bindings.txt").read_text(encoding="utf-8")
    assert "select_order 1 inactive_included" in text
    assert "rpg_skill" not in text


def test_rpg_bindings_skill_hotkeys():
    text = (ROOT / "res" / "ui" / "rpg_bindings.txt").read_text(encoding="utf-8")
    assert "rpg_skill_1" in text
    assert "rpg_skill_list" in text
    assert "rpg_auto_attack" in text


def test_rpg_bindings_with_overrides_wired():
    src = (ROOT / "soundrts" / "clientgame" / "game_navigation.py").read_text(
        encoding="utf-8"
    )
    assert "rpg_bindings_with_overrides" in src
    modes = (ROOT / "soundrts" / "clientgame" / "interface_modes.py").read_text(
        encoding="utf-8"
    )
    assert 'def rpg_bindings_with_overrides' in modes
    assert '"rpg": "rpg_bindings.txt"' in modes


def test_global_bindings_direction_keys():
    text = (ROOT / "res" / "ui" / "global_bindings.txt").read_text(encoding="utf-8")
    assert "UP: select_square 0 1" in text
    assert "CTRL SHIFT RIGHT: select_square 5 0 no_collision" in text
    map_text = (ROOT / "res" / "ui" / "map_bindings.txt").read_text(encoding="utf-8")
    assert "UP: select_square" not in map_text


def test_command_bindings_index_hotkeys():
    text = (ROOT / "res" / "ui" / "command_bindings.txt").read_text(encoding="utf-8")
    assert "s: select_order_index 1 inactive_included" in text
    assert "SEMICOLON: select_order_index 9" in text
    assert "w: select_order_index 10" in text
    assert "p: select_order_index 18" in text
    assert "1: select_order_index 19 inactive_included" in text
    assert "EQUALS: select_order_index 30 inactive_included" in text
    src = (ROOT / "soundrts" / "clientgame" / "game_orders.py").read_text(encoding="utf-8")
    assert "def cmd_select_order_index" in src


def test_building_bindings_keyboard_slots():
    text = (ROOT / "res" / "ui" / "building_bindings.txt").read_text(encoding="utf-8")
    assert "#define BUILDING building1" in text
    assert "building16" in text
    assert "d: select_unit 1 building1" in text
    assert "e: select_unit 1 building9" in text
    assert "p: select_unit 1 building16" in text
    assert "select_units" not in text


def test_unit_worker_on_s_not_d():
    text = (ROOT / "res" / "ui" / "unit_bindings.txt").read_text(encoding="utf-8")
    assert "s: select_units local worker" in text
    assert "d: select_units local soldier1" in text
    assert "e: select_unit 1 soldier1" in text
    assert "q: select_unit 1 local" in text


def test_map_deposit_bindings_present():
    text = (ROOT / "res" / "ui" / "map_bindings.txt").read_text(encoding="utf-8")
    assert "select_deposit 1 resource1" in text
    assert "select_meadow 1" in text
    assert "select_passage 1" in text
    assert "当前方格" in text


def test_square_target_cycle_lives_in_unit_control():
    src = (ROOT / "soundrts" / "clientgame" / "game_unit_control.py").read_text(
        encoding="utf-8"
    )
    assert "_cycle_square_target" in src
    assert "def cmd_select_deposit" in src
    assert "_select_square_from_list" not in src.split("def cmd_select_deposit")[1].split(
        "def cmd_select_meadow"
    )[0]


def test_get_bindings_text_loads_unit_layer_from_resource_stack():
    src = (ROOT / "soundrts" / "clientgame" / "interface_modes.py").read_text(
        encoding="utf-8"
    )
    assert "def _read_bindings_layer" in src
    assert "res.texts(f\"ui/{stem}\"" in src
    block = src.split("def get_bindings_text")[1].split("\ndef ")[0]
    assert "_global_bindings_with_overrides()" in block
    assert "_bindings_layer_with_overrides(mode)" in block


def test_coop_campaign_skips_faction_equivalents():
    src = (ROOT / "soundrts" / "game.py").read_text(encoding="utf-8")
    block = src.split("def run(self, speed=config.speed):")[1].split("\n    def ")[0]
    assert 'getattr(self, "is_coop_campaign", False)' in block
    assert "use_equivalents = False" in block


def test_arrange_building_slots_enable_even_if_no_menu():
    src = (ROOT / "soundrts" / "clientgame" / "game_unit_control.py").read_text(
        encoding="utf-8"
    )
    assert "def _is_building_keyboard_slot" in src
    block = src.split("def _arrange")[1].split("\ndef ")[0]
    assert "_is_building_keyboard_slot(k)" in block
    assert "even_if_no_menu = True" in block
    assert 'k != "building"' in block
    assert "def _effective_keyboard_query" in src
    assert "def _unit_matches_keyboard_type" in src
    assert "_unit_matches_keyboard_type(x, keyboard_types)" in block


def test_effective_keyboard_query_expands_generic_building():
    src = (ROOT / "soundrts" / "clientgame" / "game_unit_control.py").read_text(
        encoding="utf-8"
    )
    block = src.split("def _effective_keyboard_query")[1].split("\ndef ")[0]
    assert 'if "building" in wanted' in block
    assert "range(1, 17)" in block


def test_unit_matches_keyboard_type_multi_slot():
    from soundrts.definitions import Style

    style = Style()
    style.load((ROOT / "res" / "ui" / "style.txt").read_text(encoding="utf-8"))

    def effective_query(keyboard_types):
        wanted = set(keyboard_types)
        if "building" in wanted:
            wanted.update(f"building{i}" for i in range(1, 17))
        return wanted

    def matches(unit_type, keyboard_types):
        unit_keys = style.get(unit_type, "keyboard") or []
        return bool(set(unit_keys) & effective_query(keyboard_types))

    assert style.get("townhall", "keyboard") == ["building", "building1"]
    assert matches("townhall", ["building"])
    assert matches("townhall", ["building1"])
    assert not matches("townhall", ["building2"])
    assert matches("blacksmith", ["building"])
    assert not matches("blacksmith", ["building1"])
    # buildingN-only slot still matches generic building via query expansion
    only_slot = Style()
    only_slot.load("def th\nkeyboard building1\n")

    def matches_loaded(st, unit_type, keyboard_types):
        unit_keys = st.get(unit_type, "keyboard") or []
        return bool(set(unit_keys) & effective_query(keyboard_types))

    assert matches_loaded(only_slot, "th", ["building"])
    assert matches_loaded(only_slot, "th", ["building1"])
    assert not matches_loaded(only_slot, "th", ["building2"])


def test_base_style_townhall_has_dual_building_keyboard():
    text = (ROOT / "res" / "ui" / "style.txt").read_text(encoding="utf-8")
    assert "keyboard building building1" in text
    assert "keyboard building building3" in text
    assert "keyboard building building5" in text
    assert "keyboard building2" in text
    assert "keyboard building building2" not in text
    assert "keyboard building4" in text
    assert "keyboard building building4" not in text


def test_mod_style_files_have_layered_keyboard_slots():
    """Each mod style.txt should declare worker/soldier/building keyboard slots."""
    mods = ROOT / "mods"
    style_files = [
        p
        for p in sorted(mods.rglob("style.txt"))
        if not (len(p.relative_to(mods).parts) >= 2 and p.relative_to(mods).parts[1].startswith("ui-"))
    ]
    assert style_files, "expected mod style.txt files"
    for path in style_files:
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(ROOT).as_posix()
        if "tang campaign" in rel and "def parameters" in text and "keyboard " not in text:
            continue
        if "pirate_fol" in rel:
            assert "keyboard soldier6" in text, rel
            continue
        assert "keyboard worker" in text or "keyboard soldier" in text or "keyboard building" in text, rel
        if "orc/ui/style.txt" in rel:
            assert "keyboard building1" in text
            assert "keyboard worker" in text
            assert "keyboard soldier1" in text
        if "starcraft/ui/style.txt" in rel:
            assert "keyboard building1" in text
            assert "keyboard worker" in text
            assert "keyboard soldier1" in text


def test_interface_mode_msgparts_and_tts():
    from soundrts import msgparts as mp

    ids = (
        mp.UNIT_SELECTION_INTERFACE[0],
        mp.BUILDING_SELECTION_INTERFACE[0],
        mp.COMMAND_INTERFACE[0],
        mp.SKILL_INTERFACE[0],
        mp.HELP_QUERY_INTERFACE[0],
        mp.DIPLOMACY_INTERFACE[0],
        mp.EMPTY_BACKPACK[0],
    )
    assert ids == (5209, 5210, 5211, 5212, 5213, 5214, 5215)
    src = (ROOT / "soundrts" / "clientgame" / "interface_modes.py").read_text(
        encoding="utf-8"
    )
    assert "mp.UNIT_SELECTION_INTERFACE" in src
    assert "mp.DIPLOMACY_INTERFACE" in src
    for tid in ids:
        en = (ROOT / "res" / "ui" / "tts.txt").read_text(encoding="utf-8")
        zh = (ROOT / "res" / "ui-zh" / "tts.txt").read_text(encoding="utf-8")
        assert f"\n{tid} " in ("\n" + en), f"ui/tts.txt missing {tid}"
        assert f"\n{tid} " in ("\n" + zh), f"ui-zh/tts.txt missing {tid}"


def test_game_interface_wires_mode_commands():
    src = (ROOT / "soundrts" / "clientgame" / "__init__.py").read_text(encoding="utf-8")
    for cmd in (
        "cmd_toggle_selection_mode",
        "cmd_toggle_action_mode",
        "cmd_enter_help_mode",
        "cmd_enter_diplomacy_mode",
        "cmd_ui_escape",
        "cmd_select_deposit",
    ):
        assert f"GameInterface.{cmd}" in src


def test_legacy_bindings_file_exists():
    path = ROOT / "res" / "ui" / "legacy_bindings.txt"
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "layered_hotkeys=0" in text
    assert "F4: alliance_request" in text
    assert "toggle_selection_mode" not in text


def test_layered_hotkeys_config_option():
    src = (ROOT / "soundrts" / "config.py").read_text(encoding="utf-8")
    assert '("general", "layered_hotkeys", 1, int)' in src
    modes = (ROOT / "soundrts" / "clientgame" / "interface_modes.py").read_text(
        encoding="utf-8"
    )
    assert "def layered_hotkeys_enabled" in modes
    assert "def get_legacy_bindings_text" in modes


def test_init_interface_modes_legacy_branch():
    src = (ROOT / "soundrts" / "clientgame" / "interface_modes.py").read_text(
        encoding="utf-8"
    )
    block = src.split("def init_interface_modes")[1].split("\ndef ")[0]
    assert "not layered_hotkeys_enabled()" in block
    assert "_layered_bindings_active = False" in block
    assert "get_legacy_bindings_text()" in block


def test_handle_escape_legacy_skips_map_mode():
    src = (ROOT / "soundrts" / "clientgame" / "interface_modes.py").read_text(
        encoding="utf-8"
    )
    handle = src.split("def handle_escape")[1].split("\ndef ")[0]
    legacy = src.split("def legacy_handle_escape")[1].split("\ndef ")[0]
    assert "not layered_hotkeys_enabled()" in handle
    assert "legacy_handle_escape(interface)" in handle
    assert "cmd_enter_map_mode" not in legacy


def test_options_menu_hotkeys_scheme():
    src = (ROOT / "soundrts" / "clientmain.py").read_text(encoding="utf-8")
    options = src.split("def options_menu")[1].split("\ndef ")[0]
    assert "mp.HOTKEYS_MENU" in options
    assert "hotkeys_menu" in options
    assert "mp.HOTKEY_MAPPING" in options
    assert "hotkey_mapping_menu" in options
    hotkeys = src.split("def hotkeys_menu")[1].split("\ndef ")[0]
    build = src.split("def _build_hotkeys_menu_choices")[1].split("\ndef ")[0]
    assert "mp.LAYERED_HOTKEYS" in build
    assert "mp.CLASSIC_HOTKEYS" in build
    assert "_hotkey_scheme_status_msgs" in build
    assert "mp.HOTKEY_MAPPING" not in hotkeys
    refresh = src.split("def _refresh_hotkeys_menu")[1].split("\ndef ")[0]
    assert "update_menu" in refresh
    assert "_say_choice()" in refresh
    set_scheme = src.split("def hotkeys_menu")[1].split("\ndef ")[0]
    assert "set_layered_hotkeys_scheme" in set_scheme
    assert "config.save()" not in set_scheme
    assert "_refresh_hotkeys_menu" in set_scheme


def test_hotkeys_menu_tts():
    from soundrts import msgparts as mp

    ids = (
        mp.HOTKEYS_MENU[0],
        mp.LAYERED_HOTKEYS[0],
        mp.CLASSIC_HOTKEYS[0],
        mp.HOTKEYS_SCHEME_APPLIED[0],
        mp.HOTKEY_SCHEME_ACTIVE[0],
        mp.HOTKEY_SCHEME_INACTIVE[0],
    )
    en = (ROOT / "res" / "ui" / "tts.txt").read_text(encoding="utf-8")
    zh = (ROOT / "res" / "ui-zh" / "tts.txt").read_text(encoding="utf-8")
    for tid in ids:
        assert f"\n{tid} " in ("\n" + en), f"ui/tts.txt missing {tid}"
        assert f"\n{tid} " in ("\n" + zh), f"ui-zh/tts.txt missing {tid}"


def test_submenu_focuses_active_hotkey_scheme():
    hotkeys = (ROOT / "soundrts" / "clientmain.py").read_text(encoding="utf-8")
    block = hotkeys.split("def hotkeys_menu")[1].split("\ndef ")[0]
    assert "default_choice_index=0 if layered_active else 1" in block
    run = (ROOT / "soundrts" / "clientmenu.py").read_text(encoding="utf-8").split(
        "def run(self):"
    )[1].split("\n    def ")[0]
    assert "self._say_choice()" not in run
