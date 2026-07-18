"""Opening objective uses cut-scene Enter/Esc controls."""

from pathlib import Path


def test_announce_opening_objectives_wired():
    text = Path("soundrts/clientgame/game_interface_base.py").read_text(encoding="utf-8")
    assert "def _announce_opening_objectives(self, game):" in text
    assert "self._announce_opening_objectives(game)" in text
    assert "play_cutscene_line(mp.OBJECTIVE + game.world.objective)" in text
