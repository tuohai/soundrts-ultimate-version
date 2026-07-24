"""Opening objective always scrolls; cut-scenes still use play_narrative_line."""

from pathlib import Path


def test_announce_opening_objectives_wired():
    text = Path("soundrts/clientgame/game_interface_base.py").read_text(encoding="utf-8")
    assert "flatten_objective_description(game.world.objective)" in text
    # Opening objective: always scroll (re-check via Objectives button / hotkey).
    assert "play_scrolling_line(" in text
    body = text.split("if game.world.objective:", 1)[1]
    body = body.split("else:", 1)[0]
    assert "play_scrolling_line(" in body
    assert "play_narrative_line(" not in body
    assert "set_must_scroll_narratives" in text
    assert "_game_needs_scroll_narratives" in text


def test_play_narrative_line_dispatches():
    text = Path("soundrts/lib/voice.py").read_text(encoding="utf-8")
    assert "def play_narrative_line(" in text
    assert "def play_scrolling_line(" in text
    block = text.split("def play_narrative_line(", 1)[1]
    nxt = block.find("\n    def ")
    if nxt != -1:
        block = block[:nxt]
    assert "must_scroll_narratives" in block
    assert "play_scrolling_line" in block
    assert "play_cutscene_line" in block


def test_play_cutscene_line_ends_narrative_on_next():
    text = Path("soundrts/lib/voice.py").read_text(encoding="utf-8")
    block = text.split("def play_cutscene_line(", 1)[1]
    nxt = block.find("\n    def ")
    if nxt != -1:
        block = block[:nxt]
    # Every exit path that returns next/skip must clear the overlay.
    assert block.count("end_narrative()") >= 4


def test_opening_objective_clears_narrative():
    text = Path("soundrts/clientgame/game_interface_base.py").read_text(encoding="utf-8")
    body = text.split("play_scrolling_line(", 1)[1][:500]
    assert "end_narrative()" in body
