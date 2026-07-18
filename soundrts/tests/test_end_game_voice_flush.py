"""End-of-game voice: do not discard queued alerts on quit."""

from pathlib import Path


def test_srv_quit_flushes_voice_queue():
    text = Path("soundrts/clientgame/game_interface_base.py").read_text(encoding="utf-8")
    quit_block = text.split("def srv_quit(self):", 1)[1].split("\n    def ", 1)[0]
    assert "voice.flush()" in quit_block
    # Must not silently discard alerts before settlement.
    assert "voice.silent_flush()" not in quit_block.split("except", 1)[0]


def test_run_game_flushes_before_post_run():
    text = Path("soundrts/clientgame/game_interface_base.py").read_text(encoding="utf-8")
    assert "voice.flush()" in text
    assert "game.post_run()" in text
    # flush appears before post_run in run_game
    run_tail = text.split("def run_game", 1)[1]
    assert run_tail.find("voice.flush()") < run_tail.find("game.post_run()")
