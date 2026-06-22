"""The Legend of Raynor chapter 29 random-map campaign file."""
from __future__ import annotations

import os
import sys
import warnings
from pathlib import Path

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from soundrts import config

config.debug_mode = 0
config.mods = ""

_saved_argv = sys.argv
try:
    sys.argv = [_saved_argv[0]] if _saved_argv else ["pytest"]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from soundrts.campaign import Campaign, RandomMapMissionChapter
        from soundrts.lib.package import FolderPackage
finally:
    sys.argv = _saved_argv

_CAMPAIGN_DIR = (
    Path(__file__).resolve().parents[2] / "res" / "single" / "The Legend of Raynor"
)


def test_raynor_chapter_29_is_random_map_mission():
    campaign = Campaign(FolderPackage(str(_CAMPAIGN_DIR)), "The Legend of Raynor")
    chapter = campaign.chapter(29)
    assert isinstance(chapter, RandomMapMissionChapter)
    assert chapter.title == [4271, 3029]
    assert chapter._config.size == "medium"
    assert chapter._config.template == "standard"
    assert chapter._config.seed is None
    assert "raynor7" in chapter._overlay
    assert "7748" in chapter._overlay
    assert "7750" in chapter._overlay

    m = chapter.build_map()
    assert "random_starts 0" in m.definition
    assert "objective 145 88" in m.definition
