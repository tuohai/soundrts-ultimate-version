# -*- coding: utf-8 -*-
"""The bugs that the rollback protocol's wiring used to have.

Each test here reproduces a bug that made a rollback match crash, desync,
or silently disconnect the players.  They are written as regression tests:
if the fix is undone, the test fails again.
"""
from __future__ import annotations

import time
import types

import pytest

from soundrts.net.session import RollbackSession
from soundrts.version import LOCKSTEP_PROTOCOL, ROLLBACK_PROTOCOL


# ---------------------------------------------------------------------------
# The client used to crash on the second communication turn
# ---------------------------------------------------------------------------


def _coordinator(**kwargs):
    """A Coordinator with just enough surroundings to dispatch orders."""
    from soundrts.worldclient import Coordinator

    session = types.SimpleNamespace(humans=[], record_replay=False)
    coord = Coordinator(
        "host",
        types.SimpleNamespace(write_line=lambda s: None),
        session,
    )
    coord.interface = types.SimpleNamespace(real_speed=1, next_update=time.time())
    coord.world = types.SimpleNamespace(
        time=0, players=[], previous_state=(0, b""), random=None
    )
    for key, value in kwargs.items():
        setattr(coord, key, value)
    return coord


def test_the_client_does_not_crash_when_there_are_no_all_orders():
    """The rollback protocol never receives an "all_orders" message.

    The lockstep protocol pops the pending turn from ``all_orders``; in
    rollback mode there is no such message, so the pop used to raise an
    IndexError on the second communication turn.
    """
    coord = _coordinator(rollback_enabled=True)
    # No server ever sends an "all_orders" message in rollback mode.
    coord.all_orders = [[1]]

    # Several communication turns in a row must not raise.
    for _ in range(5):
        coord.sub_turn = 0
        coord._dispatch_orders()

    assert coord.all_orders == [[1]]


def test_the_client_knows_its_frames_per_turn_without_the_server():
    """``fpct`` used to be set only by the lockstep "all_orders" message.

    In rollback mode that message never arrives, so ``self.sub_turn %= self.fpct``
    raised an AttributeError.
    """
    coord = _coordinator(rollback_enabled=True)
    assert coord.fpct >= 1
    # And it survives a dispatch, which uses it.
    coord.sub_turn = 0
    coord._dispatch_orders()
    assert coord.sub_turn == 0


def test_the_lockstep_protocol_still_uses_the_all_orders_message():
    """The fix must not break the legacy protocol."""
    coord = _coordinator(rollback_enabled=False)
    coord.all_orders = [[2, "host/"]]
    coord.sub_turn = 0
    coord._dispatch_orders()
    # The turn was consumed.
    assert coord.all_orders == []


# ---------------------------------------------------------------------------
# The server used to disconnect everybody
# ---------------------------------------------------------------------------


def _game(protocol):
    """A minimal Game, with just the timeout machinery."""
    from soundrts.serverroom import Game

    game = Game.__new__(Game)
    game.protocol = protocol
    game._timeout_reference = None
    game._input_stream = None
    game._orders = types.SimpleNamespace(players_without_orders=lambda: [])
    # ``human_players`` is a read-only property (it filters ``game.players``),
    # so the fake players go in ``players``.
    game.players = []
    return game


def test_the_rollback_protocol_does_not_disconnect_the_players():
    """In rollback mode the clients send "input", never "orders".

    The lockstep timeout looks at the order queue, which is therefore
    always empty in rollback mode: every player looked idle and the server
    disconnected the first one after the timeout.
    """
    class FakePlayer:
        def __init__(self, login):
            self.login = login
            self.closed = False

        def handle_close(self):
            self.closed = True

    game = _game(ROLLBACK_PROTOCOL)
    game._input_stream = types.SimpleNamespace(last_input_time={})
    host = FakePlayer("host")
    game.players = [host]

    # The timeout window starts.
    game.check_timeout()
    assert game._timeout_reference is not None

    # Pretend the timeout expired.
    game._timeout_reference = time.time() - 1000
    game.check_timeout()
    # The player had never sent an input, so it gets the grace period
    # rather than being disconnected right away.
    assert host.closed is False


def test_the_lockstep_timeout_still_uses_the_order_queue():
    """The fix must not break the legacy protocol."""
    game = _game(LOCKSTEP_PROTOCOL)
    game.check_timeout()
    assert game._timeout_reference is not None


def test_a_silent_player_is_disconnected_in_rollback_mode():
    """A player that stops sending inputs is the one that gets disconnected."""
    from soundrts.serverroom import InputStreamGame

    class FakeStream:
        players = ["host", "guest"]

    class FakePlayer:
        login = "guest"

        def __init__(self):
            self.closed = False

        def handle_close(self):
            self.closed = True

    game = _game(ROLLBACK_PROTOCOL)
    stream = InputStreamGame.__new__(InputStreamGame)
    stream.stream = FakeStream()
    # The host is playing, but the guest has been silent for a long time.
    stream.last_input_time = {
        "host": time.time(),
        "guest": time.time() - 1000,
    }
    game._input_stream = stream

    guest = FakePlayer()
    game.players = [guest]

    game._timeout_reference = time.time() - 1000
    game.check_timeout()

    assert guest.closed is True


def test_a_playing_player_is_not_disconnected_because_another_one_stalled():
    """One stalled player must not take the others down with it."""
    from soundrts.serverroom import InputStreamGame

    class FakeStream:
        players = ["host", "guest"]

    class FakePlayer:
        def __init__(self, login):
            self.login = login
            self.closed = False

        def handle_close(self):
            self.closed = True

    game = _game(ROLLBACK_PROTOCOL)
    stream = InputStreamGame.__new__(InputStreamGame)
    stream.stream = FakeStream()
    # Both players were playing, but only the host is still sending inputs.
    stream.last_input_time = {
        "host": time.time(),
        "guest": time.time() - 1000,
    }
    game._input_stream = stream

    host = FakePlayer("host")
    guest = FakePlayer("guest")
    game.players = [host, guest]

    game._timeout_reference = time.time() - 1000
    game.check_timeout()

    # The host keeps playing, so it is not disconnected.  The guest stalled,
    # so it is.
    assert host.closed is False
    assert guest.closed is True


# ---------------------------------------------------------------------------
# The orders of the local player used to be lost in a race
# ---------------------------------------------------------------------------


def test_the_local_orders_survive_a_concurrent_submission():
    """The interface thread and the world thread share the local inputs.

    The interface thread submits the orders (the player pressed a key) while
    the world thread trims the history (it steps the simulation).  Without a
    lock, the world thread iterated the dict while the interface thread
    added an entry to it, which raises "dictionary changed size during
    iteration" — and loses the order.
    """
    import threading

    from soundrts.net.rollback import RollbackManager

    class FakeWorld:
        def __init__(self):
            self.time = 0

        def update(self):
            self.time += 1

    world = FakeWorld()
    manager = RollbackManager(
        local_player="p1",
        players=["p1", "p2"],
        world=world,
        step=world.update,
        apply_inputs=lambda inputs: None,
        capture=lambda: object(),
        restore=lambda snap: None,
        history_size=4,
    )

    errors = []
    stop = threading.Event()

    def submitter():
        while not stop.is_set():
            try:
                manager.submit_local("order 0 0 go 1")
            except Exception as exc:  # pragma: no cover - the failure mode
                errors.append(exc)
            manager.advance()

    thread = threading.Thread(target=submitter)
    thread.start()
    try:
        for _ in range(2000):
            manager.advance()
    finally:
        stop.set()
        thread.join()

    assert errors == []


def test_the_local_orders_are_applied_to_the_frame_they_were_sent_for():
    """The frame the client tells the server about must be the applied one.

    The server orders the inputs by frame number: if the client said "frame
    5" but applied them at frame 6, the two sides would apply the orders
    at different moments, and the match would desync.
    """
    sent = []
    session = RollbackSession(
        world=types.SimpleNamespace(time=0, update=lambda: None),
        local_player="p1",
        players=["p1", "p2"],
        step=lambda: None,
        apply_inputs=lambda inputs: None,
        capture=lambda: object(),
        restore=lambda snap: None,
        on_local_input=lambda frame, orders: sent.append((frame, orders)),
    )

    session.step()
    session.submit_local("attack")
    session.step()

    # The server was told about the frame the orders were applied at.
    assert sent == [(1, "attack")]
    assert session.manager.local_inputs[1] == "attack"
