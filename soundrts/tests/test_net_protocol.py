# -*- coding: utf-8 -*-
"""The negotiation of the netcode protocol.

The rollback protocol and the legacy lockstep protocol have to coexist: an
old client must still be able to play against a new server.  The rule is
simple: the rollback protocol is only used when *every* player speaks it,
because the clients have to agree on which inputs are authoritative.
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
    from soundrts.version import (
        DEFAULT_PROTOCOL,
        LOCKSTEP_PROTOCOL,
        ROLLBACK_PROTOCOL,
        negotiate_protocol,
    )

sys.argv = saved


# ---------------------------------------------------------------------------
# The negotiation itself
# ---------------------------------------------------------------------------


def test_everybody_speaking_rollback_gives_rollback():
    assert negotiate_protocol([ROLLBACK_PROTOCOL, ROLLBACK_PROTOCOL]) == (
        ROLLBACK_PROTOCOL
    )


def test_one_old_client_falls_back_to_lockstep():
    """An old client must still be able to play."""
    assert negotiate_protocol([ROLLBACK_PROTOCOL, LOCKSTEP_PROTOCOL]) == (
        LOCKSTEP_PROTOCOL
    )


def test_everybody_old_gives_lockstep():
    assert negotiate_protocol([LOCKSTEP_PROTOCOL, LOCKSTEP_PROTOCOL]) == (
        LOCKSTEP_PROTOCOL
    )


def test_no_client_gives_the_default():
    assert negotiate_protocol([]) == DEFAULT_PROTOCOL
    assert DEFAULT_PROTOCOL == LOCKSTEP_PROTOCOL


def test_a_lone_rollback_client_uses_rollback():
    """With a single human, there is nobody to disagree with.

    The computer players are simulated locally by the client, so a game
    with one human is entirely under that client's control.
    """
    assert negotiate_protocol([ROLLBACK_PROTOCOL]) == ROLLBACK_PROTOCOL


# ---------------------------------------------------------------------------
# The server side
# ---------------------------------------------------------------------------


class _FakeMap:
    name = "jl1"
    nb_players_min = 1
    nb_players_max = 8


def _fake_client(login, server, protocol=LOCKSTEP_PROTOCOL):
    client = ConnectionToClient.__new__(ConnectionToClient)
    client.login = login
    client.server = server
    client.game = None
    client.state = InTheLobby()
    client.alliance = 1
    client.faction = "human_faction"
    client.is_disconnected = False
    client.protocol = protocol
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
    game._input_stream = InputStreamGame(game)
    game.protocol = negotiate_protocol([h.protocol for h in humans])
    for h in humans:
        h.game = game
        h.state = Playing()
        h.alliance = humans.index(h) + 1
        h.faction = "human_faction"
    server.games.append(game)
    return game


def test_the_login_line_carries_the_protocol():
    server = _make_server()
    client = _fake_client("host", server)

    client.cmd_login(["15-abcdef", "host", ROLLBACK_PROTOCOL])

    assert client.login == "host"
    assert client.protocol == ROLLBACK_PROTOCOL


def test_an_old_client_that_sends_no_protocol_gets_lockstep():
    """An old client does not send the protocol at all."""
    server = _make_server()
    client = _fake_client("host", server)

    client.cmd_login(["15-abcdef", "host"])

    assert client.login == "host"
    assert client.protocol == LOCKSTEP_PROTOCOL


def test_an_unknown_protocol_falls_back_to_lockstep():
    server = _make_server()
    client = _fake_client("host", server)

    client.cmd_login(["15-abcdef", "host", "something-else"])

    assert client.protocol == LOCKSTEP_PROTOCOL


def test_the_game_uses_rollback_only_when_everybody_speaks_it():
    server = _make_server()
    p1 = _fake_client("host", server, ROLLBACK_PROTOCOL)
    p2 = _fake_client("guest", server, ROLLBACK_PROTOCOL)
    server.clients.extend([p1, p2])
    game = _game_with(server, p1, p2)
    assert game.protocol == ROLLBACK_PROTOCOL

    server2 = _make_server()
    q1 = _fake_client("host", server2, ROLLBACK_PROTOCOL)
    q2 = _fake_client("guest", server2, LOCKSTEP_PROTOCOL)
    server2.clients.extend([q1, q2])
    game2 = _game_with(server2, q1, q2)
    assert game2.protocol == LOCKSTEP_PROTOCOL


def test_the_lockstep_path_is_untouched_by_the_rollback_work():
    """The legacy path must still work exactly as before.

    The rollback protocol is additive: when it is not enabled, the server
    still waits for every player and broadcasts the whole turn.
    """
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


# ---------------------------------------------------------------------------
# The client side: the "protocol" line the server sends
# ---------------------------------------------------------------------------


def _menu():
    """A ``_ServerMenu`` that is not connected to anything.

    The menu is built without ``__init__`` because the real one wants a
    server and a pygame screen; ``srv_protocol`` only touches the two
    attributes it sets, so the bare object is enough.
    """
    from soundrts.clientservermenu import _ServerMenu

    return _ServerMenu.__new__(_ServerMenu)


def test_the_client_accepts_the_protocol_the_server_negotiates():
    """The "protocol" line must not blow up.

    The server announces the protocol before ``start_game``; the client
    handles it in ``srv_protocol``.  This test exists because that
    handler once used a relative import (``from ..version import ...``)
    that went *above* the ``soundrts`` package: the import only fails
    when the line is actually received, so nothing noticed it until a
    host created a game and the client died with
    "attempted relative import beyond top-level package".
    """
    menu = _menu()

    menu.srv_protocol([ROLLBACK_PROTOCOL + "/1"])

    assert menu._protocol == ROLLBACK_PROTOCOL
    assert menu._protocol_revision == 1


def test_the_client_accepts_a_bare_protocol_name():
    """An older server announces just the name; that means revision 1."""
    menu = _menu()

    menu.srv_protocol([LOCKSTEP_PROTOCOL])

    assert menu._protocol == LOCKSTEP_PROTOCOL
    assert menu._protocol_revision == 1


def test_the_client_ignores_an_unknown_protocol():
    """An unknown protocol is not fatal: the client falls back."""
    menu = _menu()

    menu.srv_protocol(["something-else/3"])

    assert menu._protocol == DEFAULT_PROTOCOL


# ---------------------------------------------------------------------------
# No relative import may escape its package
# ---------------------------------------------------------------------------


def test_no_relative_import_escapes_its_package():
    """No module may import from *above* its own package.

    ``from ..version import ...`` inside ``soundrts/clientservermenu.py``
    means "one level above ``soundrts``", which does not exist.  The
    import is only evaluated when the statement runs, so such a bug can
    sit in the tree for months and then kill a real game session.

    This test scans the whole package and fails on any relative import
    that goes above the package it lives in.
    """
    import ast
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]  # the "soundrts" package
    offenders = []
    for path in root.rglob("*.py"):
        rel = path.relative_to(root).parts
        if rel[0] == "tests":
            continue
        # The package depth: "soundrts" is 1, "soundrts/worldunit" is 2.
        depth = len(rel)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            if node.level and node.level > depth:
                offenders.append(
                    "%s:%d  from %s"
                    % (
                        path.relative_to(root),
                        node.lineno,
                        "." * node.level + (node.module or ""),
                    )
                )

    assert not offenders, (
        "relative imports that escape their package:\n  " + "\n  ".join(offenders)
    )
