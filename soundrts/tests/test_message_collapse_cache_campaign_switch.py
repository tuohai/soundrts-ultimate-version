"""Switching campaigns must not reuse Message collapse cache for shared IDs."""


def test_collapse_cache_cleared_on_campaign_switch():
    import os

    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    os.environ.setdefault("SOUNDRTS_UI_BACKEND", "pygame")

    from soundrts import config

    config.load()
    from soundrts.clientmedia import minimal_init

    minimal_init()
    from soundrts.lib.message import Message, is_text
    from soundrts.lib.resource import res
    from soundrts.lib.sound_cache import Sound, sounds

    raynor = next(
        c
        for c in res.campaigns()
        if "Raynor" in c.name or "raynor" in c.name.lower()
    )
    nathan = next(c for c in res.campaigns() if "nathan" in c.name.lower())

    res.set_campaign(raynor)
    raynor_parts = Message([7501]).translate_and_collapse()
    assert raynor_parts and is_text(raynor_parts[0])
    assert "雷诺" in raynor_parts[0] or "Raynor" in raynor_parts[0]

    res.set_campaign(nathan)
    nathan_parts = Message([7501]).translate_and_collapse()
    assert nathan_parts
    assert isinstance(nathan_parts[0], Sound), (
        "nathan prologue must play ui/7501.ogg, not cached Raynor TTS text"
    )
    assert sounds.has_sound("7501")
