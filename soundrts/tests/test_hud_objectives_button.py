"""Ctrl+F2 HUD: clickable Objectives button (same as objectives hotkey)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pygame

from soundrts.clientgame.game_hud import handle_hud_click, hit_test_hud


def test_hud_objectives_button_wired_in_source():
    hud = Path("soundrts/clientgame/game_hud.py").read_text(encoding="utf-8")
    assert "_draw_objectives_button" in hud
    assert '"objectives"' in hud
    assert "cmd_objectives" in hud


@patch("soundrts.clientgame.game_resources.cmd_objectives")
def test_handle_hud_click_objectives_next(cmd_objectives):
    interface = MagicMock()
    interface._hud_hits = [(pygame.Rect(8, 8, 80, 28), "objectives", None)]
    interface.group = []
    assert hit_test_hud(interface, (20, 20)) == ("objectives", None)
    assert handle_hud_click(interface, (20, 20), mods=0) is True
    cmd_objectives.assert_called_once_with(interface, 1)


@patch("soundrts.clientgame.game_resources.cmd_objectives")
def test_handle_hud_click_objectives_prev_with_shift(cmd_objectives):
    interface = MagicMock()
    interface._hud_hits = [(pygame.Rect(8, 8, 80, 28), "objectives", None)]
    interface.group = []
    assert handle_hud_click(interface, (20, 20), mods=pygame.KMOD_SHIFT) is True
    cmd_objectives.assert_called_once_with(interface, -1)
