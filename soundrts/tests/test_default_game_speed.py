"""Default game speed option (SoundRTS.ini speed)."""
from __future__ import annotations

from pathlib import Path

import pytest

from soundrts import config


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2]
        .joinpath(*path_parts)
        .read_text(encoding="utf-8")
    )


def test_game_speed_type_presets_and_custom():
    assert config.game_speed_type("1") == 1.0
    assert config.game_speed_type("1.5") == 1.5
    assert config.game_speed_type(2.5) == 2.5
    assert config.game_speed_type("4") == 4.0
    assert config.PRESET_GAME_SPEEDS == (1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0)


def test_game_speed_type_rejects_out_of_range():
    with pytest.raises(ValueError):
        config.game_speed_type("0")
    with pytest.raises(ValueError):
        config.game_speed_type("11")
    with pytest.raises(ValueError):
        config.game_speed_type("-1")


def test_config_speed_uses_float_converter():
    src = _source("soundrts", "config.py")
    assert '("general", "speed", 1.0, game_speed_type)' in src


def test_game_run_reads_live_config_speed():
    """Options may change speed after import; run() must not freeze config.speed."""
    src = _source("soundrts", "game.py")
    assert "def run(self, speed=config.speed):" not in src
    assert src.count("def run(self, speed=None):") >= 2
    first = src.split("def run(self, speed=None):")[1].split("\n    def ")[0]
    assert "current_game_speed" in first
    iface = _source("soundrts", "clientgame", "game_interface_base.py")
    assert "def __init__(self, server, speed=config.speed):" not in iface
    assert "current_game_speed" in iface.split("def __init__(self, server, speed=None):")[1].split("\n    def ")[0]


def test_options_menu_has_default_game_speed():
    options = _source("soundrts", "clientmain.py").split("def options_menu")[1].split("\ndef ")[0]
    assert "mp.DEFAULT_GAME_SPEED" in options
    assert "default_game_speed_menu" in options
    menu = _source("soundrts", "clientmain.py").split("def default_game_speed_menu")[1].split("\ndef ")[0]
    assert "PRESET_GAME_SPEEDS" in menu
    assert "CUSTOM_GAME_SPEED" in menu
    assert "_prompt_custom_default_game_speed" in _source("soundrts", "clientmain.py")


def test_options_menu_has_speech_and_display_toggles():
    options = _source("soundrts", "clientmain.py").split("def options_menu")[1].split("\ndef ")[0]
    assert "mp.ACCESSIBILITY_VOICE" in options
    assert "toggle_speech_enabled" in options
    assert "mp.DISPLAY_TOGGLE" in options
    assert "toggle_fullscreen" in options
    assert "DISPLAY_TOGGLE = [5838]" in _source("soundrts", "msgparts.py")
    zh = _source("res", "ui-zh", "tts.txt")
    assert "5838" in zh and "图像显示" in zh
    refresh = options.split("menu.choices")[1]
    assert "_speech_status," in refresh
    assert "_speech_status()" not in refresh
    assert "_display_status," in refresh
    assert "_display_status()" not in refresh


def test_choice_status_callable_is_live():
    from soundrts.lib.pygame_ui import _menu_explanation_text, resolve_choice_status

    flag = {"on": False}

    def status():
        return "on" if flag["on"] else "off"

    choice = (["label"], None, status)
    assert resolve_choice_status(choice) == "off"
    assert _menu_explanation_text(choice) == "off"
    flag["on"] = True
    assert resolve_choice_status(choice) == "on"
    assert _menu_explanation_text(choice) == "on"


def test_say_choice_resolves_callable_status(monkeypatch):
    import os

    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    from soundrts import clientmenu as cm

    spoken = []
    monkeypatch.setattr(cm, "get_submenu_select_sound", lambda: None)
    monkeypatch.setattr(cm, "get_main_menu_select_sound", lambda: None)
    monkeypatch.setattr(cm.voice, "item", lambda msg, *a, **k: spoken.append(list(msg)))
    flag = {"on": False}
    menu = cm.Menu(
        title=["t"],
        choices=[(["label"], None, lambda: [5741] if flag["on"] else [5742])],
        menu_type="submenu",
    )
    menu._draw_menu = lambda: None
    menu.choice_index = 0
    menu._say_choice()
    assert 5742 in spoken[-1]
    flag["on"] = True
    menu._say_choice()
    assert 5741 in spoken[-1]
    assert 5742 not in spoken[-1]


def test_tts_default_game_speed_ids():
    assert "DEFAULT_GAME_SPEED = [5835]" in _source("soundrts", "msgparts.py")
    assert "CUSTOM_GAME_SPEED = [5836]" in _source("soundrts", "msgparts.py")
    assert "ENTER_GAME_SPEED = [5837]" in _source("soundrts", "msgparts.py")
    zh = _source("res", "ui-zh", "tts.txt")
    assert "5835" in zh and "默认游戏速度" in zh
    assert "5836" in zh and "自定义" in zh
    assert "5837" in zh and "请输入游戏速度" in zh
