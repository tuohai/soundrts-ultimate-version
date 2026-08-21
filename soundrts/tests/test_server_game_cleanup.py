"""Finished multiplayer rooms must leave server.games / list_games."""
from __future__ import annotations

from pathlib import Path

from soundrts.serverclient import ConnectionToClient
from soundrts.servermain import Server
from soundrts.serverroom import (
    Game,
    InTheLobby,
    Orders,
    Playing,
    _Computer,
)


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2]
        .joinpath(*path_parts)
        .read_text(encoding="utf-8")
    )


class _FakeMap:
    name = "testmap"
    nb_players_min = 1
    nb_players_max = 8


def _fake_client(login, server, state=None):
    client = ConnectionToClient.__new__(ConnectionToClient)
    client.login = login
    client.server = server
    client.game = None
    client.state = state if state is not None else Playing()
    client.alliance = 1
    client.faction = "human_faction"
    client.notify = lambda *args: None
    client.push = lambda *args: None
    return client


def _started_game(server, *humans):
    game = Game.__new__(Game)
    game.id = 1
    game.scenario = _FakeMap()
    game.started = True
    game.time = 3
    game._start_time = 0
    game.server = server
    game.players = list(humans)
    game.guests = []
    game.spectators = []
    game._orders = Orders.__new__(Orders)
    game._orders.all_orders = {h: [] for h in humans}
    game.real_speed = 1
    game.ping = 0
    game.delay = 0
    game.speed = 1
    game._order_history = []
    game.notify = lambda *args: None
    for h in humans:
        h.game = game
        h.state = Playing()
    server.games.append(game)
    return game


def test_last_human_quit_removes_started_game():
    server = Server.__new__(Server)
    server.clients = []
    server.games = []
    server.update_menus = lambda: None
    server.log_status = lambda: None
    human = _fake_client("p1", server)
    server.clients.append(human)
    game = _started_game(server, human)

    human.cmd_quit_game([])

    assert game not in server.games
    assert isinstance(human.state, InTheLobby)
    assert human.game is None


def test_quit_game_still_closes_if_orders_raise():
    server = Server.__new__(Server)
    server.clients = []
    server.games = []
    server.update_menus = lambda: None
    server.log_status = lambda: None
    human = _fake_client("p1", server)
    server.clients.append(human)
    game = _started_game(server, human)

    def _boom(*args, **kwargs):
        raise KeyError("missing orders slot")

    game.orders = _boom
    human.cmd_quit_game([])

    assert game not in server.games
    assert isinstance(human.state, InTheLobby)


def test_stale_started_game_removed_when_humans_left_lobby():
    server = Server.__new__(Server)
    server.clients = []
    server.games = []
    server.update_menus = lambda: None
    server.log_status = lambda: None
    human = _fake_client("p1", server, state=InTheLobby())
    server.clients.append(human)
    game = _started_game(server, human)
    human.state = InTheLobby()
    game.players.append(_Computer("easy"))

    server._cleanup_stale_games()

    assert game not in server.games


def test_lobby_command_from_playing_leaves_stale_room():
    server = Server.__new__(Server)
    server.clients = []
    server.games = []
    server.update_menus = lambda: None
    server.log_status = lambda: None
    human = _fake_client("p1", server)
    notes = []
    human.notify = lambda *args: notes.append(args)
    server.clients.append(human)
    game = _started_game(server, human)

    human._execute_command(b"list_games")

    assert game not in server.games
    assert isinstance(human.state, InTheLobby)
    assert notes and notes[-1][0] == "no_running_games"


def test_duplicate_quit_game_from_lobby_is_silent(caplog):
    server = Server.__new__(Server)
    server.clients = []
    server.games = []
    server.update_menus = lambda: None
    server.log_status = lambda: None
    human = _fake_client("p1", server)
    server.clients.append(human)
    game = _started_game(server, human)

    human.cmd_quit_game([])
    human._execute_command(b"quit_game")

    assert game not in server.games
    assert isinstance(human.state, InTheLobby)
    assert "action not allowed" not in caplog.text


def test_post_run_sends_quit_game_before_score():
    src = _source("soundrts", "game.py")
    block = src.split("class MultiplayerGame", 1)[1].split("def post_run(self):", 1)[1]
    block = block.split("\n    def ", 1)[0]
    assert block.find('write_line("quit_game")') < block.find("_Game.post_run(self)")


def test_srv_start_game_always_sends_quit_game():
    src = _source("soundrts", "clientservermenu.py")
    block = src.split("def srv_start_game", 1)[1].split("class GameAdminMenu", 1)[0]
    assert 'write_line("quit_game")' in block.split("finally:", 1)[1]
