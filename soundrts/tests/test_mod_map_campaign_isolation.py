"""Active mods must not fall back to base res maps/campaigns."""
from __future__ import annotations

import os
import sys
import warnings

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

saved_argv = sys.argv
sys.argv = [saved_argv[0] if saved_argv else "pytest"]
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    try:
        from soundrts.lib import resource as resource_mod
        from soundrts.lib.resource import res
    finally:
        sys.argv = saved_argv


@pytest.fixture(autouse=True)
def _restore_mods():
    prev = res.mods
    res._multi_maps = None
    res._campaigns = None
    yield
    res.set_mods(prev or "")
    res._multi_maps = None
    res._campaigns = None


def test_active_mod_names_split():
    prev = res.mods
    try:
        res.mods = "aoe2, starcraft"
        assert resource_mod._active_mod_names() == ["aoe2", "starcraft"]
        res.mods = ""
        assert resource_mod._active_mod_names() == []
        res.mods = "  "
        assert resource_mod._active_mod_names() == []
    finally:
        res.mods = prev


def test_mod_without_content_lists_no_res_maps_or_campaigns(monkeypatch):
    """Even with an empty mod folder, never fall back to res/multi or res/single."""
    monkeypatch.setattr(resource_mod, "_active_mod_names", lambda: ["___empty_isolation_mod___"])
    res._multi_maps = None
    res._campaigns = None
    assert resource_mod._get_multi_maps() == []
    assert resource_mod._campaigns() == []


def test_vanilla_still_lists_res_maps_and_campaigns(monkeypatch):
    monkeypatch.setattr(resource_mod, "_active_mod_names", lambda: [])
    res._multi_maps = None
    res._campaigns = None
    maps = resource_mod._get_multi_maps()
    campaigns = resource_mod._campaigns()
    assert maps, "vanilla should still see res/multi"
    assert campaigns, "vanilla should still see res/single"
    assert any(getattr(m, "official", False) for m in maps)


@pytest.mark.skipif(not os.path.isdir("mods/aoe2"), reason="aoe2 mod not present")
def test_aoe2_lists_wallace_campaign_not_res(monkeypatch):
    """aoe2 single/ lists Wallace; must not fall back to Raynor from res/single."""
    from soundrts import config

    monkeypatch.setattr(config, "mods", "aoe2")
    res.set_mods("aoe2")
    res._campaigns = None
    res._multi_maps = None
    campaigns = res.campaigns()
    names = [c.name for c in campaigns]
    assert any("Wallace" in n for n in names), names
    assert not any("Raynor" in n for n in names), names
    assert res.multiplayer_maps(), "aoe2 multi/ should still list mod maps"
    assert all(getattr(m, "mod_specific", False) for m in res.multiplayer_maps())


@pytest.mark.skipif(not os.path.isdir("mods/aoe2/single/William Wallace"), reason="Wallace campaign missing")
def test_wallace_campaign_has_seven_missions(monkeypatch):
    from soundrts import config
    from soundrts.campaign import MissionChapter

    monkeypatch.setattr(config, "mods", "aoe2")
    res.set_mods("aoe2")
    res._campaigns = None
    wallace = next(c for c in res.campaigns() if "Wallace" in c.name)
    assert getattr(wallace, "default_faction", None) == "celts"
    mission_nums = [ch.number for ch in wallace.chapters if isinstance(ch, MissionChapter)]
    assert mission_nums == [1, 2, 3, 4, 5, 6, 7], mission_nums
