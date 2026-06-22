"""合作战役：公开房间 + 邀请真人时替换 AI 队友。"""
from __future__ import annotations

from pathlib import Path

import pytest

from soundrts.serverroom import Game, _Computer


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2]
        .joinpath(*path_parts)
        .read_text(encoding="utf-8")
    )


class _FakeMap:
    nb_players_max = 2
    nb_players_min = 1
    name = "The Legend of Raynor/1"


class _FakeAdmin:
    login = "host"
    alliance = 1
    faction = "random_faction"

    def notify(self, *args):
        pass


class _FakeServer:
    parameters = {}

    def available_players(self, client=None):
        return []


class _FakeClient:
    login = "guest"
    game = None
    alliance = 0
    faction = "random_faction"

    def notify(self, *args):
        pass


def _coop_game():
    admin = _FakeAdmin()
    admin.alliance = 1
    game = Game.__new__(Game)
    game.scenario = _FakeMap()
    game.started = False
    game.is_coop_campaign = True
    game.server = _FakeServer()
    game.admin = admin
    game.players = [admin]
    game.guests = []
    game.spectators = []
    game.notify = lambda *args: None
    return game


def test_coop_menu_offers_public_and_private_room():
    src = _source("soundrts", "clientservermenu.py")
    assert "_select_visibility" in src
    assert "mp.COOP_PUBLIC_ROOM" in src
    assert "mp.COOP_PRIVATE_ROOM" in src
    assert '"public", "0", difficulty' in src


def test_create_campaign_public_flag_wired():
    src = _source("soundrts", "serverclient.py")
    block = src.split("def cmd_create_campaign")[1].split("\n    def ")[0]
    assert 'tokens[-1] == "public"' in block
    assert "_create_game(" in block
    assert "is_public" in block.split("_create_game", 1)[1]


def test_invite_clears_coop_ai_slot():
    src = _source("soundrts", "serverclient.py")
    block = src.split("def cmd_invite(self, args):")[1].split("\n    def ")[0]
    assert "prepare_coop_slot_for_human" in block


def test_can_register_when_partner_slot_is_ai():
    game = _coop_game()
    game.players.append(_Computer("aggressive", coop_partner=True))
    game.players[-1].alliance = 2
    assert game.can_register() is True


def test_register_coop_replaces_ai_at_slot_2():
    game = _coop_game()
    ai = _Computer("aggressive", coop_partner=True)
    ai.alliance = 2
    game.players.append(ai)
    guest = _FakeClient()
    assert game.register(guest) is True
    assert guest.alliance == 2
    assert not any(
        isinstance(p, _Computer) and getattr(p, "coop_partner", False)
        for p in game.players
    )
    assert guest in game.players


def test_prepare_coop_slot_for_human_removes_ai():
    game = _coop_game()
    ai = _Computer("aggressive", coop_partner=True)
    ai.alliance = 2
    game.players.append(ai)
    assert game.prepare_coop_slot_for_human(2) is True
    assert game._player_at_alliance(2) is None


def test_admin_menu_allows_invite_when_slot_has_ai():
    src = _source("soundrts", "clientservermenu.py")
    assert "_can_invite_coop_partner" in src
    assert "_coop_slot_has_ai_partner" in src
