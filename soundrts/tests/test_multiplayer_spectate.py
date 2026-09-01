# -*- coding: utf-8 -*-
"""Headless multiplayer spectator: server protocol + deterministic world rebuild."""
from __future__ import annotations

import logging
import os
import sys
import time
import warnings
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

saved = sys.argv
sys.argv = [saved[0] if saved else "pytest"]
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from soundrts import config
    from soundrts.definitions import VIRTUAL_TIME_INTERVAL, rules
    from soundrts.game import SpectatorGame
    from soundrts.lib.resource import res
    from soundrts.serverclient import ConnectionToClient
    from soundrts.servermain import Server
    from soundrts.serverroom import (
        Game,
        InTheLobby,
        Orders,
        OrganizingAGame,
        Playing,
        Spectating,
        pack,
    )
    from soundrts.world import World
    from soundrts.worldclient import Coordinator, DummyClient, RemoteClient

sys.argv = saved


@pytest.fixture
def res_loaded():
    logging.disable(logging.WARNING)
    old = getattr(config, "mods", "")
    config.mods = ""
    res.set_mods("")
    res.load_rules_and_ai()
    yield
    config.mods = old
    res.set_mods(old or "")
    if old:
        res.load_rules_and_ai()
    logging.disable(logging.NOTSET)


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


def _started_game(server, *humans, seed=42, treaty=0):
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
    game.treaty_minutes = treaty
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


# ---------------------------------------------------------------------------
# Server protocol
# ---------------------------------------------------------------------------


def test_list_games_shows_started_match_for_spectator():
    server = _make_server()
    p1 = _fake_client("host", server)
    p2 = _fake_client("guest", server)
    observer = _fake_client("watcher", server)
    server.clients.extend([p1, p2, observer])
    _started_game(server, p1, p2)

    observer.cmd_list_games([])

    assert observer.notes
    assert observer.notes[-1][0] == "rooms"
    from urllib.parse import unquote
    payload = unquote(observer.notes[-1][1])
    assert payload.startswith("7,")
    assert "host" in payload and "guest" in payload


def test_list_games_empty_when_no_started_match():
    server = _make_server()
    observer = _fake_client("watcher", server)
    server.clients.append(observer)

    observer.cmd_list_games([])

    assert observer.notes[-1] == ("no_rooms",)


def test_spectate_replays_seed_and_order_history():
    server = _make_server()
    p1 = _fake_client("host", server)
    p2 = _fake_client("guest", server)
    observer = _fake_client("watcher", server)
    server.clients.extend([p1, p2, observer])
    game = _started_game(server, p1, p2, seed=1234, treaty=5)
    game._order_history = [
        (1, "host/order,0,0,default,a1 guest/"),
        (1, "host/ guest/order,0,0,default,b2"),
    ]

    observer.cmd_spectate(["7"])

    kinds = [n[0] for n in observer.notes]
    assert "spectate_success" in kinds
    assert "start_spectating" in kinds
    start = [n for n in observer.notes if n[0] == "start_spectating"][0]
    assert start[1] == game._initial_players_pack
    assert start[2] == "jl1"
    assert int(start[4]) == 1234
    assert int(start[5]) == 5
    history = [n for n in observer.notes if n[0] == "all_orders"]
    assert len(history) == 2
    assert history[0][1:] == (1, "host/order,0,0,default,a1 guest/")
    assert isinstance(observer.state, Spectating)
    assert observer in game.spectators
    joined = [n for n in p1.notes if n[0] == "spectator_joined"]
    assert joined and joined[-1][1] == "watcher"


def test_spectate_errors_and_unstarted_waits_for_host():
    server = _make_server()
    observer = _fake_client("watcher", server)
    server.clients.append(observer)

    observer.cmd_spectate([])
    assert observer.notes[-1][0] == "spectate_error"

    observer.cmd_spectate(["not-a-number"])
    assert observer.notes[-1][0] == "spectate_error"

    observer.cmd_spectate(["99"])
    assert observer.notes[-1][0] == "spectate_error"

    p1 = _fake_client("host", server)
    game = _started_game(server, p1)
    game.started = False
    p1.state = OrganizingAGame()
    observer.notes.clear()
    observer.cmd_spectate(["7"])
    kinds = [n[0] for n in observer.notes]
    assert "waiting_to_spectate" in kinds
    assert "start_spectating" not in kinds
    assert "spectate_success" not in kinds
    assert observer in game.spectators
    assert isinstance(observer.state, Spectating)
    joined = [n for n in p1.notes if n[0] == "spectator_joined"]
    assert joined and joined[-1][1] == "watcher"

    observer.notes.clear()
    game._start()
    kinds = [n[0] for n in observer.notes]
    assert "start_spectating" in kinds
    assert game.started is True


def test_quit_waiting_spectator_notifies_quit():
    server = _make_server()
    p1 = _fake_client("host", server)
    observer = _fake_client("watcher", server)
    game = _started_game(server, p1)
    game.started = False
    game.add_spectator(observer)
    observer.notes.clear()
    observer.cmd_quit_spectating([])
    assert observer not in game.spectators
    assert "quit" in [n[0] for n in observer.notes]


def test_live_orders_recorded_and_forwarded_to_spectator():
    server = _make_server()
    p1 = _fake_client("host", server)
    p2 = _fake_client("guest", server)
    observer = _fake_client("watcher", server)
    game = _started_game(server, p1, p2)
    game.add_spectator(observer)

    game.orders(p1, "order,0,0,default,a1", check="0-0.0-x", ping=0, delay=0, real_speed=1)
    game.orders(p2, "", check="0-0.0-x", ping=0, delay=0, real_speed=1)

    assert game._order_history == [(1, "host/order,0,0,default,a1 guest/")]
    forwarded = [n for n in observer.notes if n[0] == "all_orders"]
    assert forwarded[-1][1:] == (1, "host/order,0,0,default,a1 guest/")
    assert "all_orders" in [n[0] for n in p1.notes]


def test_quit_spectating_returns_to_lobby_and_notifies():
    server = _make_server()
    p1 = _fake_client("host", server)
    observer = _fake_client("watcher", server)
    game = _started_game(server, p1)
    game.add_spectator(observer)

    observer.cmd_quit_spectating([])

    assert observer not in game.spectators
    assert isinstance(observer.state, InTheLobby)
    assert observer.game is None
    left = [n for n in p1.notes if n[0] == "spectator_left"]
    assert left and left[-1][1] == "watcher"


def test_spectator_is_not_a_human_player_slot():
    server = _make_server()
    p1 = _fake_client("host", server)
    observer = _fake_client("watcher", server)
    game = _started_game(server, p1)
    game.add_spectator(observer)
    assert observer not in game.human_players
    assert observer not in game.players


def test_initial_players_pack_survives_midgame_quit():
    server = _make_server()
    p1 = _fake_client("host", server)
    p2 = _fake_client("guest", server)
    game = _started_game(server, p1, p2)
    packed = game._initial_players_pack
    game.players.remove(p2)
    observer = _fake_client("watcher", server)
    assert game.start_spectating(observer) is True
    start = [n for n in observer.notes if n[0] == "start_spectating"][0]
    assert start[1] == packed
    assert "guest" in packed


# ---------------------------------------------------------------------------
# SpectatorGame / Coordinator
# ---------------------------------------------------------------------------


def test_spectator_game_humans_include_remote_clients_not_ai():
    """SpectatorGame.humans must expose real players so orders are not dropped.

    Do not call SpectatorGame.__init__: that scans every multiplayer map file
    and leaves unclosed handles that pytest treats as unraisable errors.
    """
    session = SpectatorGame.__new__(SpectatorGame)
    session.seed = 42
    session.treaty_minutes = 0
    session.speed = 1
    session.main_server = SimpleNamespace(login="watcher", write_line=lambda s: None)
    session.local_client = Coordinator(
        session.main_server.login, session.main_server, session
    )
    session.players = []
    for login, alliance, faction in (
        ("host", "1", "human_faction"),
        ("guest", "2", "human_faction"),
        ("ai_beginner", "3", "human_faction"),
    ):
        if login.startswith("ai_"):
            c = DummyClient(login[3:])
        else:
            c = RemoteClient(login)
        c.alliance = alliance
        c.faction = faction
        session.players.append(c)
    session.spectator_client = session.local_client

    logins = [c.login for c in session.humans]
    assert logins == ["host", "guest"]
    assert all(c.__class__ is RemoteClient for c in session.humans)
    assert session.is_spectator_session is True
    assert session.local_client.login == "watcher"
    assert session.local_client not in session.players


def test_coordinator_silently_ignores_spectate_success(caplog):
    coord = Coordinator(
        "watcher",
        SimpleNamespace(write_line=lambda s: None, read_line=lambda: "spectate_success"),
        SimpleNamespace(is_spectator_session=True),
    )
    coord.interface = SimpleNamespace(next_update=time.time())
    coord._previous_update = time.time()
    coord.update()
    assert "ignored data" not in caplog.text


def test_coordinator_forwards_spectator_joined(caplog):
    pushed = []
    coord = Coordinator(
        "watcher",
        SimpleNamespace(
            write_line=lambda s: None,
            read_line=lambda: "spectator_joined 拓海",
        ),
        SimpleNamespace(is_spectator_session=True),
    )
    coord.interface = SimpleNamespace(next_update=time.time())
    coord._previous_update = time.time()
    coord.push = lambda *args: pushed.append(args)
    coord.update()
    assert pushed == [("spectator_joined", "拓海")]
    assert "ignored data" not in caplog.text


def test_catch_up_announces_spectating_only_once(monkeypatch):
    from soundrts import msgparts as mp
    from soundrts.clientgame.game_interface_base import GameInterface
    import soundrts.clientgame.game_interface_base as gib
    import soundrts.lib.sound as soundmod

    spoken = []
    monkeypatch.setattr(gib.voice, "alert", lambda msg: spoken.append(list(msg)))
    monkeypatch.setattr(gib.voice, "info", lambda msg: spoken.append(("info", list(msg))))
    monkeypatch.setattr(gib.voice, "silent_flush", lambda: None)
    monkeypatch.setattr(soundmod, "main_volume", 1.0)

    server = SimpleNamespace(_is_spectator=True, all_orders=[[]] * 5, catch_up_buffer=3)
    iface = SimpleNamespace(
        server=server,
        _catch_up_muted=False,
        _announced_spectating=False,
        _saved_main_volume=1.0,
    )
    GameInterface._update_catch_up_audio(iface)
    assert iface._catch_up_muted is True
    assert spoken == []

    # Live spectating typically keeps 2–3 pending turns; that must unmute.
    server.all_orders = [[]] * 2
    GameInterface._update_catch_up_audio(iface)
    assert iface._catch_up_muted is False
    assert spoken == [list(mp.YOU_ARE_SPECTATING)]

    server.all_orders = [[]] * 5
    GameInterface._update_catch_up_audio(iface)
    assert iface._catch_up_muted is True
    server.all_orders = [[]] * 2
    GameInterface._update_catch_up_audio(iface)
    assert iface._catch_up_muted is False
    assert spoken == [list(mp.YOU_ARE_SPECTATING)]


def test_coordinator_does_not_send_orders_or_timeout_while_spectating():
    sent = []
    session = SimpleNamespace(is_spectator_session=True, humans=[], world=SimpleNamespace())
    coord = Coordinator("watcher", SimpleNamespace(write_line=sent.append), session)
    coord.interface = SimpleNamespace(real_speed=1, next_update=time.time())
    coord.world = session.world
    coord.all_orders = [["1", "host/"]]
    coord.fpct = 1
    coord.sub_turn = 0
    coord._previous_update = 0.0

    coord._dispatch_orders()
    assert sent == []

    coord.main_server.read_line = lambda: None
    coord.update()
    assert sent == []


def test_coordinator_routes_human_orders_via_humans_not_empty_list():
    host = RemoteClient("host")
    guest = RemoteClient("guest")
    queued = []
    session = SimpleNamespace(
        is_spectator_session=True,
        humans=[host, guest],
        world=SimpleNamespace(),
    )
    coord = Coordinator("watcher", SimpleNamespace(write_line=lambda s: None), session)
    coord.queue_command = lambda player, order: queued.append((player, order))
    host.player = object()
    guest.player = object()

    coord.all_orders = [["1", "host/order,0,0,default,a1", "guest/"]]
    coord._give_all_orders()

    assert queued == [(host.player, "order 0 0 default a1")]
    assert coord.get_client_by_login("host") is host
    assert coord.get_client_by_login("watcher") is None


def test_catch_up_backlog_only_for_spectator_session():
    spec = Coordinator("w", SimpleNamespace(), SimpleNamespace(is_spectator_session=True))
    live = Coordinator("h", SimpleNamespace(), SimpleNamespace(is_spectator_session=False))
    spec.all_orders = [[]] * 5
    live.all_orders = [[]] * 5
    assert spec.has_catch_up_backlog() is True
    assert live.has_catch_up_backlog() is False
    spec.all_orders = [[]] * 2
    assert spec.has_catch_up_backlog() is False


# ---------------------------------------------------------------------------
# World reconstruction vs live match
# ---------------------------------------------------------------------------


def _fingerprint(player):
    units = []
    for u in sorted(player.units, key=lambda x: str(getattr(x, "id", ""))):
        units.append(
            (
                str(u.id),
                getattr(u, "type_name", None),
                int(getattr(u, "hp", 0) or 0),
                int(getattr(u, "x", 0) or 0),
                int(getattr(u, "y", 0) or 0),
            )
        )
    return (
        getattr(player.client, "login", "?"),
        tuple(int(x) for x in (player.resources or [])),
        tuple(units),
    )


def _non_spec_players(world):
    return [
        p
        for p in world.players
        if not getattr(p, "_is_pure_spectator", False)
    ]


_JL1 = Path(__file__).resolve().parents[2] / "res" / "multi" / "jl1.txt"


def _build_match_world(seed, with_spectator=False):
    from soundrts.lib.nofloat import PRECISION as P

    if not _JL1.is_file():
        pytest.skip("res jl1 map not present")
    faction = rules.factions[0] if rules.factions else "human_faction"
    p1 = DummyClient("beginner")
    p1.faction = faction
    p1.alliance = "1"
    p2 = DummyClient("beginner")
    p2.faction = faction
    p2.alliance = "2"
    world = World([], seed)
    world._parse_map(_JL1.read_text(encoding="utf-8"))
    world.square_width = int(world.square_width * P)
    world._build_map()
    world.populate_map([p1, p2], random_starts=False)
    spectator = None
    if with_spectator:
        session = SimpleNamespace(
            world=world,
            spectator_client=None,
            local_client=None,
        )
        spec_client = Coordinator(
            "watcher", SimpleNamespace(login="watcher", write_line=lambda s: None), session
        )
        session.spectator_client = spec_client
        session.local_client = spec_client
        SpectatorGame._create_spectator_player(session)
        spectator = spec_client.player
    return world, p1.player, p2.player, spectator


def test_spectator_player_has_no_units_and_is_excluded_from_match(res_loaded):
    world, p1, p2, spec = _build_match_world(42, with_spectator=True)
    assert spec is not None
    assert spec.is_spectator is True
    assert spec._is_pure_spectator is True
    assert spec.cheatmode is True
    assert spec.neutral is True
    assert spec.units == []
    assert spec not in world.true_players()
    assert spec not in world.true_playing_players
    assert spec not in world.match_participating_players
    assert world.current_nb_human_players() == 0  # DummyClient AIs are not human
    before = len(p1.units)
    spec.add_unit(type(p1.units[0]), p1.units[0].place)
    assert spec.units == []
    assert len(p1.units) == before


def test_spectator_rebuild_stays_in_sync_with_live_match(res_loaded):
    """Same seed + spectator injected after populate must not fork the sim."""
    live, *_ = _build_match_world(42, with_spectator=False)
    spec_world, *_rest = _build_match_world(42, with_spectator=True)

    live_ids0 = [u.id for p in _non_spec_players(live) for u in p.units]
    spec_ids0 = [u.id for p in _non_spec_players(spec_world) for u in p.units]
    assert live_ids0 == spec_ids0
    assert live.random.getstate() == spec_world.random.getstate(), (
        "creating the spectator player consumed world.random"
    )

    ticks = int(45 * 1000 / VIRTUAL_TIME_INTERVAL)
    for _ in range(ticks):
        live.update()
        spec_world.update()

    assert live.time == spec_world.time
    assert live.random.getstate() == spec_world.random.getstate(), (
        "spectator world RNG diverged after simulated combat/economy"
    )
    live_fp = [_fingerprint(p) for p in _non_spec_players(live)]
    spec_fp = [_fingerprint(p) for p in _non_spec_players(spec_world)]
    assert live_fp == spec_fp
    spec_player = [p for p in spec_world.players if getattr(p, "_is_pure_spectator", False)]
    assert len(spec_player) == 1
    assert spec_player[0].units == []


def test_new_units_keep_same_ids_after_spectator_is_injected(res_loaded):
    """Orders target entity ids. Spectator must not steal the next id."""
    live, live_p1, *_ = _build_match_world(7, with_spectator=False)
    spec_world, spec_p1, *_rest = _build_match_world(7, with_spectator=True)

    utype = type(live_p1.units[0])
    place_live = live_p1.units[0].place
    place_spec = spec_p1.units[0].place
    live_p1.add_unit(utype, place_live)
    spec_p1.add_unit(utype, place_spec)

    live_ids = sorted(str(u.id) for u in live_p1.units)
    spec_ids = sorted(str(u.id) for u in spec_p1.units)
    assert live_ids == spec_ids, (
        f"spectator shifted entity ids; live={live_ids} spec={spec_ids}"
    )
    assert live._next_id == spec_world._next_id
