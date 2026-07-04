"""Menu flow for configuring and launching a procedurally generated map."""
from __future__ import annotations

from .clientmenu import CLOSE_MENU, Menu, input_string
from .clientmedia import voice
from . import msgparts as mp
from .lib.msgs import nb2msg
from .randommap import (
    RandomMapConfig,
    config_voice_summary,
    decode_share_code,
    get_rmg_template_spec,
    map_generated_voice_msg,
    make_map,
    menu_title_for_config,
    refresh_rmg_templates,
    server_create_command,
    terrain_choices_for_template,
)
from .rmg_templates import custom_template_names, template_title_voice, terrain_menu_voice


class RandomMapMenu:
    """Step-through submenu: template → size → … → seed → treaty → launch."""

    def __init__(self, on_ready, server_mode=None):
        self._on_ready = on_ready
        self._server_mode = server_mode
        self._config = RandomMapConfig()
        self._speed = server_mode.get("speed", "1.0") if server_mode else "1.0"
        self._is_public = server_mode.get("is_public", "") if server_mode else ""

    def run(self):
        self._open_template_menu()

    def _open_template_menu(self):
        refresh_rmg_templates()
        menu = Menu(mp.RMG_RANDOM_MAP + mp.RMG_TEMPLATE, menu_type="submenu")
        menu.append(mp.RMG_IMPORT_CODE, self._prompt_import_share_code)
        menu.append(mp.RMG_TEMPLATE_STANDARD, (self._set_template, "standard"))
        menu.append(mp.RMG_TEMPLATE_FAST + mp.RMG_CONTEST_CENTER, (self._set_template, "fast"))
        menu.append(mp.RMG_TEMPLATE_MACRO + mp.RMG_ECONOMIC, (self._set_template, "macro"))
        menu.append(mp.RMG_TEMPLATE_LANES + mp.RMG_LANES_DESC, (self._set_template, "lanes"))
        from .randommap import _TEMPLATE_TITLE

        for name in custom_template_names():
            menu.append(
                template_title_voice(name, _TEMPLATE_TITLE),
                (self._set_template, name),
            )
        menu.append(mp.CANCEL, CLOSE_MENU)
        menu.run()

    def _prompt_import_share_code(self):
        value = input_string(
            list(mp.RMG_ENTER_SHARE_CODE),
            pattern=r"^[a-zA-Z0-9:./\-]$",
            default="",
            spell=False,
            max_length=80,
        )
        if value is None:
            return
        try:
            self._config = decode_share_code(value)
        except Exception:
            voice.alert(mp.RMG_INVALID_SHARE_CODE)
            self._open_template_menu()
            return
        self._announce_preview()
        self._open_treaty_menu()

    def _set_template(self, template):
        self._config.template = template
        self._open_size_menu()

    def _open_size_menu(self):
        menu = Menu(mp.RMG_RANDOM_MAP + mp.RMG_MAP_SIZE, menu_type="submenu")
        menu.append(mp.RMG_SIZE_SMALL, (self._set_size, "small"))
        menu.append(mp.RMG_SIZE_MEDIUM, (self._set_size, "medium"))
        menu.append(mp.RMG_SIZE_LARGE, (self._set_size, "large"))
        menu.append(mp.CANCEL, CLOSE_MENU)
        menu.run()

    def _set_size(self, size):
        self._config.size = size
        self._open_players_menu()

    def _open_players_menu(self):
        menu = Menu(mp.RMG_RANDOM_MAP + mp.RMG_PLAYER_COUNT, menu_type="submenu")
        for n in (2, 3, 4):
            menu.append(nb2msg(n) + mp.RMG_PLAYERS, (self._set_players, n))
        menu.append(mp.CANCEL, CLOSE_MENU)
        menu.run()

    def _set_players(self, n):
        self._config.nb_players = n
        if n == 4:
            self._open_team_menu()
        else:
            self._config.team_mode = "ffa"
            self._open_monster_menu()

    def _open_team_menu(self):
        menu = Menu(mp.RMG_RANDOM_MAP + mp.RMG_TEAM_MODE, menu_type="submenu")
        menu.append(mp.RMG_FFA, (self._set_team, "ffa"))
        menu.append(mp.RMG_TEAMS_2V2, (self._set_team, "teams_2v2"))
        menu.append(mp.CANCEL, CLOSE_MENU)
        menu.run()

    def _set_team(self, team_mode):
        self._config.team_mode = team_mode
        self._open_monster_menu()

    def _open_monster_menu(self):
        menu = Menu(mp.RMG_RANDOM_MAP + mp.RMG_MONSTER_STRENGTH, menu_type="submenu")
        menu.append(mp.RMG_WEAK, (self._set_monster, "weak"))
        menu.append(mp.RMG_STRENGTH_MEDIUM, (self._set_monster, "medium"))
        menu.append(mp.RMG_STRONG, (self._set_monster, "strong"))
        menu.append(mp.CANCEL, CLOSE_MENU)
        menu.run()

    def _set_monster(self, strength):
        self._config.monster_strength = strength
        self._open_resource_menu()

    def _open_resource_menu(self):
        menu = Menu(mp.RMG_RANDOM_MAP + mp.RMG_RESOURCE_LAYOUT, menu_type="submenu")
        menu.append(mp.RMG_BALANCED, (self._set_resource, "balanced"))
        menu.append(mp.RMG_CLUSTERED, (self._set_resource, "clustered"))
        menu.append(mp.CANCEL, CLOSE_MENU)
        menu.run()

    def _set_resource(self, layout):
        self._config.resource_layout = layout
        refresh_rmg_templates()
        spec = get_rmg_template_spec(self._config.template)
        if spec.skip_terrain_menu:
            self._config.water = "none"
            self._open_treasure_menu()
        else:
            self._open_terrain_menu()

    def _open_terrain_menu(self):
        refresh_rmg_templates()
        menu = Menu(mp.RMG_RANDOM_MAP + mp.RMG_TERRAIN, menu_type="submenu")
        for terrain in terrain_choices_for_template(self._config.template):
            menu.append(terrain_menu_voice(terrain), (self._set_terrain, terrain))
        menu.append(mp.CANCEL, CLOSE_MENU)
        menu.run()

    def _set_terrain(self, terrain):
        self._config.terrain = terrain
        self._open_water_menu()

    def _open_water_menu(self):
        menu = Menu(mp.RMG_RANDOM_MAP + mp.RMG_WATER, menu_type="submenu")
        menu.append(mp.RMG_NO_WATER, (self._set_water, "none"))
        menu.append(mp.RMG_LAKE, (self._set_water, "lake"))
        menu.append(mp.RMG_RIVER, (self._set_water, "river"))
        menu.append(mp.CANCEL, CLOSE_MENU)
        menu.run()

    def _set_water(self, water):
        self._config.water = water
        self._open_treasure_menu()

    def _open_treasure_menu(self):
        menu = Menu(mp.RMG_RANDOM_MAP + mp.RMG_TREASURE, menu_type="submenu")
        menu.append(mp.RMG_TREASURE_NONE, (self._set_treasure, "none"))
        menu.append(mp.RMG_TREASURE_LOW, (self._set_treasure, "low"))
        menu.append(mp.RMG_TREASURE_HIGH, (self._set_treasure, "high"))
        menu.append(mp.CANCEL, CLOSE_MENU)
        menu.run()

    def _set_treasure(self, treasure):
        self._config.treasure = treasure
        self._open_victory_menu()

    def _open_victory_menu(self):
        menu = Menu(mp.RMG_RANDOM_MAP + mp.RMG_VICTORY_MODE, menu_type="submenu")
        menu.append(mp.RMG_VICTORY_CONQUEST, (self._set_victory, "conquest"))
        menu.append(mp.RMG_VICTORY_ECONOMIC, (self._set_victory, "economic"))
        menu.append(mp.RMG_VICTORY_EXPLORATION, (self._set_victory, "exploration"))
        menu.append(mp.RMG_VICTORY_SURVIVAL, (self._set_victory, "survival"))
        menu.append(mp.CANCEL, CLOSE_MENU)
        menu.run()

    def _set_victory(self, mode):
        self._config.victory_mode = mode
        self._open_seed_menu()

    def _open_seed_menu(self):
        menu = Menu(mp.RMG_RANDOM_MAP + mp.RMG_SEED, menu_type="submenu")
        menu.append(mp.RMG_SEED_RANDOM, (self._set_seed_random,))
        menu.append(mp.RMG_SEED_CUSTOM, self._prompt_custom_seed)
        menu.append(mp.CANCEL, CLOSE_MENU)
        menu.run()

    def _set_seed_random(self):
        self._config.seed = None
        self._announce_preview()
        self._open_treaty_menu()

    def _prompt_custom_seed(self):
        value = input_string(list(mp.RMG_ENTER_SEED), pattern="^[0-9]$", default="", spell=True)
        if value is None:
            return
        if not value:
            voice.alert(mp.BEEP)
            self._open_seed_menu()
            return
        self._config.seed = int(value) % 100000
        self._announce_preview()
        self._open_treaty_menu()

    def _announce_preview(self):
        seed_hint = self._config.seed if self._config.seed else None
        voice.info(mp.RMG_PREVIEW + config_voice_summary(self._config, seed_hint))

    def _open_treaty_menu(self):
        menu = Menu(menu_title_for_config(self._config) + mp.TREATY, menu_type="submenu")
        menu.append(mp.TREATY + [":"] + mp.NO_TREATY, (self._finish, 0))
        for minutes in (5, 10, 15, 20):
            menu.append(mp.TREATY + nb2msg(minutes) + mp.MINUTES, (self._finish, minutes))
        menu.append(mp.CANCEL, CLOSE_MENU)
        menu.run()

    def _finish(self, treaty_minutes):
        if self._server_mode:
            cmd = server_create_command(
                self._config,
                self._speed,
                is_public=bool(self._is_public),
                treaty_minutes=treaty_minutes,
            )
            self._server_mode["write_line"](cmd)
            return
        m, seed = make_map(self._config)
        voice.important(map_generated_voice_msg(self._config, seed))
        self._on_ready(m, seed, treaty_minutes)
