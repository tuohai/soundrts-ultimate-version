# read/write the config file

import configparser
import os
import shutil
import sys

from .lib.log import info, warning
from .paths import CONFIG_FILE_PATH

DEFAULT_LOGIN = "player"

debug_mode: int
mods: str
soundpacks: str
wait_delay_per_character: float
main_volume: float
sfx_volume: float
music_volume: float
music_enabled: int
secondary_voice_enabled: int

_LOGIN_FORBIDDEN_CHARS = set('\\/:*?"<>|\0')
_LOGIN_MAX_LENGTH = 20


def login_char_is_valid(ch):
    if not ch or not ch.isprintable() or ch.isspace():
        return False
    return ch not in _LOGIN_FORBIDDEN_CHARS


def login_is_valid(login):
    if not isinstance(login, str):
        return False
    if not login or len(login) > _LOGIN_MAX_LENGTH:
        return False
    if login.startswith("ai_"):
        return False
    return all(login_char_is_valid(c) for c in login)


def login_type(s):
    assert isinstance(s, str)
    if not login_is_valid(s):
        raise ValueError
    return s


def volume_type(s):
    return max(0.0, min(1.0, float(s)))


def game_voice_rate_type(s):
    v = int(s)
    if v < -10 or v > 10:
        raise ValueError
    return v


def voice_lib_pct_type(s):
    v = int(s)
    if v < 0 or v > 100:
        raise ValueError
    return v


def voice_lib_param_type(s):
    return int(s) % 4


_options = [
    ("general", "login", DEFAULT_LOGIN, login_type),
    ("general", "mods", ""),
    ("general", "soundpacks", ""),
    ("general", "num_channels", 16),
    ("general", "speed", 1),
    (
        "general",
        "verbosity",
        "menu_changed,unit_added,unit_complete,scout_info,food,resources,resource_exhausted,enemy",
    ),
    ("general", "debug_mode", 0),
    ("general", "layered_hotkeys", 1, int),
    ("server", "timeout", 60.0),
    # fpct must be as small as possible while respecting test_fpct()
    ("server", "fpct_coef", 2.3),
    ("server", "fpct_max", 3),
    ("server", "require_humans", 0),
    ("tts", "wait_delay_per_character", 0.1),
    # Game VoiceChannel: auto | default | SAPI description | nuance:Ting-Ting
    ("tts", "game_voice", "auto", str),
    ("tts", "game_voice_rate", 0, game_voice_rate_type),
    ("tts", "nuance_vl_path", "", str),
    ("tts", "nuance_java", "", str),
    # MW-style dual libraries (主/副)
    ("tts", "primary_voice", "auto", str),
    ("tts", "primary_rate", 80, voice_lib_pct_type),
    ("tts", "primary_volume", 80, voice_lib_pct_type),
    ("tts", "primary_pitch", 50, voice_lib_pct_type),
    ("tts", "primary_device", "default", str),
    ("tts", "primary_param", 0, voice_lib_param_type),
    ("tts", "secondary_voice", "auto", str),
    ("tts", "secondary_rate", 80, voice_lib_pct_type),
    ("tts", "secondary_volume", 80, voice_lib_pct_type),
    ("tts", "secondary_pitch", 50, voice_lib_pct_type),
    ("tts", "secondary_device", "default", str),
    ("tts", "secondary_param", 0, voice_lib_param_type),
    # 1 = dual voice (副库播被动事件); 0 = primary handles everything (E-style)
    ("tts", "secondary_voice_enabled", 1, int),
    ("audio", "main_volume", 0.5, volume_type),
    ("audio", "sfx_volume", 0.5, volume_type),
    ("audio", "music_volume", 0.5, volume_type),
    ("audio", "music_enabled", 1, int),
]


def add_converter(option):
    if len(option) == 4:
        return option
    return option + (type(option[2]),)


_options = [add_converter(o) for o in _options]

_module = sys.modules[__name__]


def save(name=CONFIG_FILE_PATH):
    c = configparser.ConfigParser()
    for section, option, _, _ in _options:
        if not c.has_section(section):
            c.add_section(section)
        c.set(section, option, str(getattr(_module, option)))
    with open(name, "w", encoding="utf-8") as f:
        c.write(f)


def make_a_copy(name):
    try:
        shutil.copy(name, name + ".old")
        warning("made a copy of the old config file")
    except:
        warning("could not make a copy of the old config file")


def _copy_to_module(c):
    error = False
    for section, option, default, converter in _options:
        try:
            # Check if environment variable exists for this option
            env_value = os.getenv(option.upper())
            if env_value is not None:
                raw_value = env_value
            else:
                raw_value = c.get(section, option)
        except configparser.Error:
            info("%r option is missing (will be: %r)", option, default)
            value = default
            error = True
        else:
            try:
                value = converter(raw_value)
            except ValueError:
                warning("%s will be %r instead of %r", option, default, raw_value)
                value = default
                error = True
        setattr(_module, option, value)
    return error


def load(name=CONFIG_FILE_PATH):
    if os.path.isfile(name):
        c = configparser.ConfigParser()
        with open(name, encoding="utf-8") as _f:
            c.read_file(_f)
        error = _copy_to_module(c)
        if error:
            warning("Error in %s.", name)
            make_a_copy(name)
            warning("Rewriting %s...", name)
            save(name)
    else:
        init()
        save(name)


def init():
    for _, option, default, _ in _options:
        setattr(_module, option, default)


def apply_audio_settings():
    """Apply persisted audio settings to the sound module."""
    from .lib import sound

    sound.main_volume = main_volume
    sound.sfx_volume = sfx_volume
    sound.music_volume = music_volume
    sound.music_enabled = bool(music_enabled)


def sync_audio_settings():
    """Copy current sound settings back to config module attributes."""
    from .lib import sound

    _module.main_volume = sound.main_volume
    _module.sfx_volume = sound.sfx_volume
    _module.music_volume = sound.music_volume
    _module.music_enabled = int(sound.music_enabled)


def save_audio_settings(name=CONFIG_FILE_PATH):
    sync_audio_settings()
    save(name)


init()
