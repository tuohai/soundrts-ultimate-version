# -*- coding: utf-8 -*-
"""is_admin must not warn after a standalone defeat."""
from __future__ import annotations

import logging
import os
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from soundrts.clientgame.game_interface_base import GameInterface


def _iface(player):
    gi = GameInterface.__new__(GameInterface)
    gi.server = SimpleNamespace(player=player)
    return gi


def test_is_admin_true_when_first_in_world_players():
    human = SimpleNamespace()
    human.world = SimpleNamespace(players=[human])
    assert _iface(human).is_admin() is True


def test_is_admin_false_when_not_first():
    human = SimpleNamespace()
    other = SimpleNamespace()
    human.world = SimpleNamespace(players=[other, human])
    assert _iface(human).is_admin() is False


def test_is_admin_after_defeat_no_player_does_not_warn(caplog):
    with caplog.at_level(logging.WARNING):
        assert _iface(None).is_admin() is True
    assert "couldn't be sure if this client is the admin" not in caplog.text


def test_is_admin_after_quit_empty_players_does_not_warn(caplog):
    human = SimpleNamespace()
    human.world = SimpleNamespace(players=[])
    with caplog.at_level(logging.WARNING):
        assert _iface(human).is_admin() is True
    assert "couldn't be sure if this client is the admin" not in caplog.text
