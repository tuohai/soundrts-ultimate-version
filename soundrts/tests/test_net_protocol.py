# -*- coding: utf-8 -*-
"""The legacy lockstep path of the multiplayer netcode.

The rollback netcode was removed from this build, so the multiplayer
protocol is the classic deterministic lockstep one: the server waits for
every player to answer a communication turn, and only then broadcasts the
whole turn.

These tests pin that behaviour down, so that it cannot regress silently.
"""
from __future__ import annotations

import logging
import os
import sys
import time
import warnings

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

saved = sys.argv
sys.argv = [saved[0] if saved else "pytest"]
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from soundrts.serverclient import ConnectionToClient
    from soundrts.servermain import Server
    from soundrts.serverroom import (
        Game,
        InTheLobby,
        Orders,
        Playing,
        pack,
    )

sys.argv = saved


# ---------------------------------------------------------------------------
# The server side
# ---------------------------------------------------------------------------


class _FakeMap:
    name = "jl1"
    nb_players_min = 1
    nb_players_max = 8


def _fake_client(login, server):
    client = ConnectionToClient.__new__(ConnectionToClient)
    client.login = login
    client.server = server
    client.game = None
    client.state = InTheLobby()
    client.alliance = 1
    client.faction = "human_faction"
    client.is_disconnected = False
    client.t1 = time.time()
    client.address = ("127.0.0.1", 1234)
    client.notes = []
    client.notify = lambda *args: client.notes.append(args)
    client.push = lambda *args: None
    return client


def _make_server():
    server = Server.__new__(Server)
    server.clients = []
    server.games = []
    server.nb_clients_max = 40
    server.login = "testserver"
    server.update_menus = lambda: None
    server.log_status = lambda: None
    server._cleanup = lambda: None
    return server


def _game_with(server, *humans):
    game = Game.__new__(Game)
    game.id = 7
    game.scenario = _FakeMap()
    game.admin = humans[0] if humans else None
    game.password = ""
    game.started = True
    game.time = 0
    game._start_time = time.time()
    game.server = server
    game.players = list(humans)
    game.guests = []
    game.spectators = []
    game.seed = 42
    game.treaty_minutes = 0
    game.speed = 1
    game.real_speed = 1
    game.ping = 0
    game.delay = 0
    game._order_history = []
    game._initial_players_pack = ";".join(pack(p) for p in humans)
    game._coop_enemy_hp = 100
    game._coop_enemy_damage = 100
    game._orders = Orders.__new__(Orders)
    game._orders.all_orders = {h: [] for h in humans}
    for h in humans:
        h.game = game
        h.state = Playing()
        h.alliance = humans.index(h) + 1
        h.faction = "human_faction"
    server.games.append(game)
    return game


def test_the_login_line_still_works():
    """The login line is ``<version> <login>``; the protocol is gone."""
    server = _make_server()
    client = _fake_client("host", server)

    client.cmd_login(["15-abcdef", "host"])

    assert client.login == "host"


def test_the_lockstep_barrier_still_waits_for_every_player():
    """The server waits for every player and broadcasts the whole turn."""
    server = _make_server()
    p1 = _fake_client("host", server)
    p2 = _fake_client("guest", server)
    server.clients.extend([p1, p2])
    game = _game_with(server, p1, p2)

    # Only one player has sent their orders: nothing is broadcast yet.
    game.orders(p1, "order,0,0,go,42")
    assert not [n for n in p2.notes if n[0] == "all_orders"]

    # The second player answers: now the turn is broadcast.
    game.orders(p2, "")
    broadcasts = [n for n in p2.notes if n[0] == "all_orders"]
    assert len(broadcasts) == 1
    assert "host/order,0,0,go,42" in broadcasts[0][2]
    assert "guest/" in broadcasts[0][2]
