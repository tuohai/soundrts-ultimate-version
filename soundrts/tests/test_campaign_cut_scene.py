"""Campaign cut-scene chapters (CRLF-safe first-line detection)."""
from __future__ import annotations

import os
import sys
import warnings

import pytest

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
        from soundrts.campaign import Campaign, CutSceneChapter
        from soundrts.lib.package import FolderPackage
finally:
    sys.argv = _saved_argv


def test_cut_scene_chapter_detected_with_crlf_first_line(tmp_path):
    campaign_dir = tmp_path / "demo"
    campaign_dir.mkdir()
    # Windows editors often save CRLF; first-line check must use strip().
    (campaign_dir / "0.txt").write_bytes(
        b"cut_scene_chapter\r\ntitle 7276\r\nsequence 7552 7553 7279\r\n"
    )
    campaign = Campaign(FolderPackage(str(campaign_dir)), "demo")
    chapter = campaign.chapter(0)
    assert isinstance(chapter, CutSceneChapter)
    assert chapter.sequence == [7552, 7553, 7279]
