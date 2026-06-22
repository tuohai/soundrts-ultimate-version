"""localize_voice_msg must resolve place-name keys to text without breaking sounds."""
from __future__ import annotations

import os
import sys
import warnings

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

_saved_argv = sys.argv
try:
    sys.argv = [_saved_argv[0]] if _saved_argv else ["pytest"]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        import pygame

        pygame.mixer.init()
        from soundrts import config

        config.debug_mode = 0
        from soundrts.campaign import Campaign
        from soundrts.lib.message import Message
        from soundrts.lib.msgs import localize_voice_msg
        from soundrts.lib.package import FolderPackage
        from soundrts.lib.resource import res
        from soundrts.lib.sound_cache import Sound, sounds
        from soundrts.mapfile import Map
finally:
    sys.argv = _saved_argv


@pytest.fixture()
def raynor_ch1_resources():
    camp = Campaign(
        FolderPackage("res/single/The Legend of Raynor"), "The Legend of Raynor"
    )
    res.set_campaign(camp)
    with open("res/single/The Legend of Raynor/1.txt", "rb") as f:
        m = Map.load(f, "1.txt")
    res.set_map(m)
    yield
    res.set_map()
    res.set_campaign()


def test_localize_voice_msg_resolves_place_name_to_text(raynor_ch1_resources):
    parts = localize_voice_msg(["loc_ch01_marsh_ford", 1000002, 1000003])
    assert parts[0] == "沼泽浅滩"
    assert parts[1] == 1000002
    assert parts[2] == 1000003


def test_movement_sound_not_turned_into_repr_on_second_pass(raynor_ch1_resources):
    prefix = sounds.translate_sound_number("1091")
    assert isinstance(prefix, Sound)

    parts = localize_voice_msg([prefix, "loc_ch01_marsh_ford", 1000002, 1000003])
    assert isinstance(parts[0], Sound)

    collapsed = Message(parts).translate_and_collapse()
    text_parts = [p for p in collapsed if isinstance(p, str)]
    assert text_parts
    assert "Sound object" not in text_parts[0]
    assert "沼泽浅滩" in text_parts[0]
    assert "2" in text_parts[0]
    assert "3" in text_parts[0]
    assert isinstance(collapsed[0], Sound)


def test_translate_sound_number_passes_sound_through():
    snd = sounds.translate_sound_number("1091")
    assert isinstance(snd, Sound)
    assert sounds.translate_sound_number(snd) is snd
