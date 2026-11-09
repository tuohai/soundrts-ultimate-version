"""End-of-game voice: the statistics screen must not wait for the backlog.

Regression for the 1.5.1.3 regression: ``srv_quit`` used ``voice.flush()``,
which recited every passive combat alert still queued before the match
ended, delaying the transition to the statistics by minutes.
"""

from pathlib import Path


def test_srv_quit_discards_pending_voice():
    text = Path("soundrts/clientgame/game_interface_base.py").read_text(encoding="utf-8")
    quit_block = text.split("def srv_quit(self):", 1)[1].split("\n    def ", 1)[0]
    assert "voice.discard_pending()" in quit_block
    # Must not drain the passive backlog before settlement.
    assert "voice.flush()" not in quit_block
    assert "voice.silent_flush()" not in quit_block


def test_srv_events_stop_after_quit():
    """After 'quit', further events must not re-queue passive alerts."""
    text = Path("soundrts/clientgame/game_interface_base.py").read_text(encoding="utf-8")
    block = text.split("def _process_srv_events(self):", 1)[1].split("\n    def ", 1)[0]
    assert 'e[0] == "quit"' in block


def test_run_game_discards_before_post_run():
    text = Path("soundrts/clientgame/game_interface_base.py").read_text(encoding="utf-8")
    assert "voice.discard_pending()" in text
    assert "game.post_run()" in text
    run_tail = text.split("def run_game", 1)[1]
    assert run_tail.find("voice.discard_pending()") < run_tail.find("game.post_run()")


def test_discard_pending_keeps_primary_library():
    """discard_pending() must only silence the secondary (passive) library."""
    voice_text = Path("soundrts/lib/voice.py").read_text(encoding="utf-8")
    block = voice_text.split("def discard_pending(self):", 1)[1].split("\n    def ", 1)[0]
    assert "SECONDARY" in block
    # A full stop (channel=None) would also silence the primary library,
    # which carries the post-match statistics.
    assert "self.channel.stop()" not in block
