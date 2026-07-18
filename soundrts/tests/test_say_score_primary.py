"""End-of-game score / achievements must use primary voice (or SR), not secondary."""

from pathlib import Path


def test_say_score_uses_primary_channel():
    text = Path("soundrts/game.py").read_text(encoding="utf-8")
    score = text.split("def say_score(self):", 1)[1].split("\n    def ", 1)[0]
    assert "tts_channel=game_tts.PRIMARY" in score
    assert "voice.important" in score
    assert "voice.info" not in score


def test_say_achievements_uses_primary_channel():
    text = Path("soundrts/game.py").read_text(encoding="utf-8")
    block = text.split("def _say_achievements(self):", 1)[1].split("\n    def ", 1)[0]
    assert "tts_channel=game_tts.PRIMARY" in block
    assert "voice.important" in block
