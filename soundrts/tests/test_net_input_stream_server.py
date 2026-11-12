# -*- coding: utf-8 -*-
"""The server side of the rollback protocol.

The legacy protocol is *lockstep*: the server waits until every player has
sent the orders for a communication turn, and only then broadcasts the whole
turn.  The slowest player's ping therefore sets the pace of the whole match.

The rollback protocol removes that barrier: the server stamps every input
with an authoritative sequence number the moment it arrives, and broadcasts
it straight away.  These tests lock that behaviour in.
"""
from __future__ import annotations

import logging
import os
import sys
import time
import warnings

import pytest

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
        InputStreamGame,
        Orders,
        Playing,
        pack,
    )
    from soundrts.net.input_stream import decode_input, pack_orders

sys.argv = saved


class _FakeMap:
    name = "jl1"
    nb_players_min = 1
    nb_players_max = 8


def _fake_client(login, server, state=None):
    client = ConnectionToClient.__new__(ConnectionToClient)
    client.login = login
    client.server = server
    client.game = None
    client.state = state if state is not None else InTheLobby()
    client.alliance = 1
    client.faction = "human_faction"
    client.is_disconnected = False
    client.notes = []
    client.notify = lambda *args: client.notes.append(args)
    client.push = lambda *args: None
    return client


def _make_server():
    server = Server.__new__(Server)
    server.clients = []
    server.games = []
    server.update_menus = lambda: None
    server.log_status = lambda: None
    server._cleanup = lambda: None
    return server


def _started_game(server, *humans, seed=42):
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
    game.seed = seed
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
    game._input_stream = InputStreamGame(game)
    for h in humans:
        h.game = game
        h.state = Playing()
        h.alliance = humans.index(h) + 1
        h.faction = "human_faction"
    server.games.append(game)
    return game


# ---------------------------------------------------------------------------
# The server stamps and broadcasts every input straight away
# ---------------------------------------------------------------------------


def test_the_server_broadcasts_an_input_without_waiting_for_the_other_player():
    """This is the whole point: no lockstep barrier."""
    server = _make_server()
    p1 = _fake_client("host", server)
    p2 = _fake_client("guest", server)
    server.clients.extend([p1, p2])
    game = _started_game(server, p1, p2)

    p1.cmd_input(["3", pack_orders("order 0 0 go 42")])

    # The guest learns about the host's move *right away*, without the guest
    # having sent anything itself.
    assert p2.notes, "the other player was not told about the input"
    kind, message = p2.notes[-1]
    assert kind == "input"

    frame, player_id, seq, orders = decode_input(message)
    assert frame == 3
    assert player_id == "host"
    assert orders == "order 0 0 go 42"


def test_the_server_does_not_echo_an_input_back_to_its_author():
    """The author already knows what it did; echoing is pure bandwidth."""
    server = _make_server()
    p1 = _fake_client("host", server)
    p2 = _fake_client("guest", server)
    server.clients.extend([p1, p2])
    game = _started_game(server, p1, p2)

    p1.cmd_input(["0", ""])

    assert not [n for n in p1.notes if n[0] == "input"]
    assert [n for n in p2.notes if n[0] == "input"]


def test_the_sequence_numbers_are_monotonic_and_authoritative():
    """The sequence number fixes the order in which inputs are applied."""
    server = _make_server()
    p1 = _fake_client("host", server)
    p2 = _fake_client("guest", server)
    server.clients.extend([p1, p2])
    game = _started_game(server, p1, p2)

    p1.cmd_input(["0", "a"])
    p2.cmd_input(["0", "b"])
    p1.cmd_input(["1", "c"])

    seen = {}
    for client in (p1, p2):
        for kind, message in client.notes:
            if kind == "input":
                frame, player_id, seq, orders = decode_input(message)
                seen.setdefault((frame, player_id), (seq, orders))

    # Every input got a distinct stamp, and the stamps follow the order in
    # which the inputs arrived.  (The stamps are not contiguous: the server
    # also stamps the *completion* of a frame, which consumes a number.)
    seqs = sorted(seq for seq, _ in seen.values())
    assert len(set(seqs)) == len(seqs)
    assert seqs == sorted(seqs)

    # The order of the stamps matches the order of arrival: the host's
    # first input was stamped before the guest's, and the host's second
    # input (frame 1) last.
    by_key = {(frame, player): seq for (frame, player), (seq, _) in seen.items()}
    assert by_key[(0, "host")] < by_key[(0, "guest")] < by_key[(1, "host")]


def test_a_duplicate_input_is_ignored():
    """A retransmission must never change an input that was broadcast."""
    server = _make_server()
    p1 = _fake_client("host", server)
    p2 = _fake_client("guest", server)
    server.clients.extend([p1, p2])
    game = _started_game(server, p1, p2)

    p1.cmd_input(["0", "first"])
    p1.cmd_input(["0", "second"])

    inputs = [n for n in p2.notes if n[0] == "input"]
    assert len(inputs) == 1
    _, _, _, orders = decode_input(inputs[0][1])
    assert orders == "first"


def test_a_frame_is_confirmed_once_every_player_answered():
    server = _make_server()
    p1 = _fake_client("host", server)
    p2 = _fake_client("guest", server)
    server.clients.extend([p1, p2])
    game = _started_game(server, p1, p2)

    p1.cmd_input(["0", ""])
    assert game.confirmed_frames() == []

    p2.cmd_input(["0", ""])
    confirmed = game.confirmed_frames()
    assert [f.frame for f in confirmed] == [0]


def test_an_input_far_ahead_is_rejected():
    """A client running away from the server is not trusted."""
    server = _make_server()
    p1 = _fake_client("host", server)
    p2 = _fake_client("guest", server)
    server.clients.extend([p1, p2])
    game = _started_game(server, p1, p2)

    p1.cmd_input(["0", ""])
    p1.cmd_input(["100000", ""])

    # The absurd frame was dropped: the guest never heard about it.
    assert not [n for n in p2.notes if n[0] == "input" and "100000" in n[1]]


def test_a_malformed_input_frame_is_ignored():
    server = _make_server()
    p1 = _fake_client("host", server)
    p2 = _fake_client("guest", server)
    server.clients.extend([p1, p2])
    game = _started_game(server, p1, p2)

    p1.cmd_input(["not-a-number", "x"])

    assert not [n for n in p2.notes if n[0] == "input"]


def test_a_player_that_is_not_in_the_game_cannot_submit():
    server = _make_server()
    p1 = _fake_client("host", server)
    p2 = _fake_client("guest", server)
    stranger = _fake_client("stranger", server)
    server.clients.extend([p1, p2, stranger])
    game = _started_game(server, p1, p2)

    stranger.cmd_input(["0", "x"])

    assert not [n for n in p1.notes if n[0] == "input"]
    assert not [n for n in p2.notes if n[0] == "input"]


def test_the_orders_survive_the_round_trip_unchanged():
    """The packed orders must reach the other client byte for byte."""
    server = _make_server()
    p1 = _fake_client("host", server)
    p2 = _fake_client("guest", server)
    server.clients.extend([p1, p2])
    game = _started_game(server, p1, p2)

    orders = "control 9206\norder 0 0 go 8834"
    p1.cmd_input(["7", pack_orders(orders)])

    _, message = [n for n in p2.notes if n[0] == "input"][0]
    _, _, _, received = decode_input(message)
    assert received == orders
