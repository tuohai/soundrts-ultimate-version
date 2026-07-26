"""Selected-unit stats panel on Ctrl+F2 HUD."""

from pathlib import Path

from soundrts.clientgame.game_hud import _prec_num
from soundrts.lib.nofloat import PRECISION


def test_prec_num_formats_precision_values():
    assert _prec_num(30 * PRECISION) == "30"
    assert _prec_num(15 * PRECISION // 10) == "1.5"


def test_selection_stats_wired_into_hud():
    hud = Path("soundrts/clientgame/game_hud.py").read_text(encoding="utf-8")
    assert "def _draw_selection_stats(" in hud
    assert "_draw_selection_stats(" in hud.split("def draw_hud", 1)[1]
    assert "ATK" in hud
    assert "DEF" in hud
