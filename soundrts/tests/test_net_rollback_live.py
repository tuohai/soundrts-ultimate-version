# -*- coding: utf-8 -*-
"""Live multiplayer tests: real sockets, real server, real rollback.

The other rollback tests drive the pieces in-process, one at a time.
They are precise, but they never exercise the *whole* chain: a real TCP
socket, the real server, the real wire format, and two clients simulating
at the same time.

These tests do.  They run the whole stack headless — no Pygame window, no
sound, no human — over the loopback interface:

1. **baseline convergence** — two clients play a match over real sockets
   and end up bit-exact;
2. **high latency** — the remote inputs arrive late, so the clients have
   to predict, then roll back and re-simulate, and they still converge;
3. **disconnect** — a player drops mid-match; the survivor keeps playing
   and stays consistent;
4. **spectator** — a spectator joins a running match, replays the history
   the server gives it, and keeps up with the live match.

The harness that makes this possible is :mod:`soundrts.net.headless`.
"""
from __future__ import annotations

import logging
import os
import sys
import warnings

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

saved = sys.argv
sys.argv = [saved[0] if saved else "pytest"]
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from soundrts.net.headless import HeadlessMatch

sys.argv = saved


JL1 = os.path.join("res", "multi", "jl1.txt")


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def quiet():
    """Keep the server's chatter out of the test output."""
    logging.disable(logging.WARNING)
    yield
    logging.disable(logging.NOTSET)


@pytest.fixture
def match(quiet):
    """A two-player match on a small map, over real loopback sockets."""
    if not os.path.isfile(JL1):
        pytest.skip("jl1 map not present")
    instance = HeadlessMatch(map_name="jl1", logins=("host", "guest"))
    try:
        instance.connect("host")
        instance.connect("guest")
        instance.setup_room()
        instance.build_worlds()
        yield instance
    finally:
        instance.close()


def move_order(client) -> str:
    """An order that moves one of *client*'s units.

    It is the same order the real interface sends: ``control`` selects the
    unit, ``order 0 0 go <target>`` moves it.
    """
    player = client.coordinator.player
    for unit in player.units:
        exits = list(getattr(unit.place, "exits", ()) or ())
        if exits:
            return "control %s\norder 0 0 go %s" % (unit.id, exits[0].id)
    return ""


def orders_for(match, frame: int):
    """The orders of every player, for *frame*."""
    return {
        frame: {
            login: move_order(match.clients[login]) for login in match.logins
        }
    }


# ---------------------------------------------------------------------------
# 1. Baseline convergence
# ---------------------------------------------------------------------------


def test_two_clients_converge_over_real_sockets(match):
    """Two clients, one TCP connection each, one identical world.

    This is the smoke test of the whole stack: the handshake, the room
    creation, the map transfer, the world construction, the input stream
    and the simulation all have to work, and the two worlds have to end up
    bit-exact.

    Without any latency, no rollback may happen: the remote input always
    arrives before the frame is simulated, so there is nothing to correct.
    """
    before = match.digests()
    assert before["host"] == before["guest"], "the worlds differ before any frame"

    match.run_frames(20, orders_for(match, 3))

    digests = match.digests()
    assert digests["host"] == digests["guest"], "the two clients diverged"

    # The match really happened: the frames were simulated.
    for login in match.logins:
        assert match.clients[login].frame == 20
        assert match.clients[login].stats.frames_simulated == 20

    # And no rollback was needed: the remote input arrived in time.
    for login in match.logins:
        stats = match.clients[login].stats
        assert stats.rollbacks == 0
        assert stats.unrecoverable_desyncs == 0


def test_the_world_really_moves(match):
    """The orders are applied, not silently dropped.

    A digest equality alone would also hold if *nothing* happened.  The
    test therefore checks that the clients' digest changed, and that it
    changed to the same value on both sides.
    """
    before = match.digests()["host"]
    match.run_frames(20, orders_for(match, 3))
    after = match.digests()
    assert after["host"] != before, "the orders had no effect at all"
    assert after["host"] == after["guest"]


# ---------------------------------------------------------------------------
# 2. High latency: the rollback
# ---------------------------------------------------------------------------


def test_high_latency_rolls_back_and_still_converges(quiet):
    """A slow link forces the rollback, and the clients still converge.

    The remote inputs are held back for several frames, so the client
    simulates them as "the remote player did nothing" — and has to roll
    back when the truth arrives.  That is the whole point of the rollback
    netcode.

    The latency is injected in *frames*, not in seconds, so the test is
    exactly reproducible: the same run always produces the same rollback.
    """
    if not os.path.isfile(JL1):
        pytest.skip("jl1 map not present")
    instance = HeadlessMatch(
        map_name="jl1",
        logins=("host", "guest"),
        incoming_delay_frames=3,
        outgoing_delay_frames=3,
    )
    try:
        instance.connect("host")
        instance.connect("guest")
        instance.setup_room()
        instance.build_worlds()

        instance.run_frames(20, orders_for(instance, 3))
        instance.drain()

        digests = instance.digests()
        assert digests["host"] == digests["guest"], "the two clients diverged"

        for login in instance.logins:
            stats = instance.clients[login].stats
            # The rollback actually happened.
            assert stats.rollbacks >= 1, "no rollback happened: %r" % stats.as_dict()
            assert stats.frames_resimulated >= 1
            assert stats.max_rollback_depth >= 1
            # And it was repaired: the client is not holding a desynced world.
            assert stats.unrecoverable_desyncs == 0
            assert stats.desync_detected >= 1
    finally:
        instance.close()


def test_the_rollback_repairs_the_world_exactly(quiet):
    """After a rollback, the two worlds are bit-exact again.

    The rollback is only useful if it lands on the *same* state the other
    client has.  This test checks the state after the repair, not the
    counters.
    """
    if not os.path.isfile(JL1):
        pytest.skip("jl1 map not present")
    instance = HeadlessMatch(
        map_name="jl1",
        logins=("host", "guest"),
        incoming_delay_frames=4,
        outgoing_delay_frames=4,
    )
    try:
        instance.connect("host")
        instance.connect("guest")
        instance.setup_room()
        instance.build_worlds()

        # Several orders, spread over the match: each of them forces a
        # rollback, because the remote input arrives after the frame that
        # used it was simulated.
        orders = {}
        for frame in (2, 6, 10, 14):
            orders.update(orders_for(instance, frame))
        instance.run_frames(20, orders)
        instance.drain()

        digests = instance.digests()
        assert digests["host"] == digests["guest"]
        assert instance.clients["guest"].stats.rollbacks >= 1
    finally:
        instance.close()


# ---------------------------------------------------------------------------
# 3. Disconnect
# ---------------------------------------------------------------------------


def test_a_player_that_disconnects_does_not_stall_the_match(match):
    """The survivor keeps playing, and the server closes the open frames.

    A player that quits will never answer the frames it was supposed to
    answer.  If nothing else happened, every later frame would stay
    incomplete and the whole match would freeze.

    The server closes those frames with the quitter's empty share, and
    tells the other clients, which then stop waiting for it.
    """
    match.run_frames(6, orders_for(match, 2))
    survivor = "host"

    match.disconnect("guest")

    # The match goes on.
    match.run_frames(10, orders_for(match, 8))
    match.drain()

    client = match.clients[survivor]
    assert client.frame == 16, "the survivor stopped simulating"
    assert client.stats.unrecoverable_desyncs == 0
    # The client was told the player is gone, so it does not wait for it.
    assert "guest" not in client.rollback_session.manager.players


def test_the_survivor_is_not_desynced_by_the_disconnect(quiet):
    """The disconnect does not fork the world.

    The quitter's frames are closed with an empty input, so the survivor's
    world stays the one the server agreed on.  This test checks the state
    after the disconnect, against a reference run in which nobody left.

    The two runs use the same seed, so the survivors have to end up on the
    same digest.
    """

    def run(with_disconnect):
        if not os.path.isfile(JL1):
            pytest.skip("jl1 map not present")
        instance = HeadlessMatch(map_name="jl1", logins=("host", "guest"))
        try:
            instance.connect("host")
            instance.connect("guest")
            instance.setup_room()
            instance.build_worlds()
            instance.run_frames(4, orders_for(instance, 2))
            if with_disconnect:
                instance.disconnect("guest")
                instance.run_frames(6, orders_for(instance, 6))
            else:
                instance.run_frames(6, orders_for(instance, 6))
            instance.drain()
            return instance.clients["host"].digest()
        finally:
            instance.close()

    assert run(True) == run(False)


# ---------------------------------------------------------------------------
# 4. Spectator
# ---------------------------------------------------------------------------


def test_a_spectator_catches_up_with_the_live_match(match):
    """A spectator that joins mid-match rebuilds the past and keeps up.

    The spectator gets the whole authoritative input history from the
    server, replays it frame by frame, and then follows the live match.
    It never predicts, so it never rolls back: it simply waits for the
    frames it has not received yet.
    """
    match.run_frames(8, orders_for(match, 2))

    spectator = match.add_spectator("watcher")

    # The history was replayed.
    replayed = match.catch_up_spectator("watcher")
    assert replayed >= 8, "the spectator did not replay the history"
    assert spectator.frame == match.clients["host"].frame

    # And it stays in sync with the live match.
    match.run_frames(8, orders_for(match, 12))
    assert spectator.frame == match.clients["host"].frame

    digests = match.digests()
    assert digests["host"] == digests["guest"]
    assert digests["watcher"] == digests["host"], "the spectator is out of sync"


def test_the_spectator_replays_the_history_it_received(match):
    """The spectator's world is rebuilt from the history, frame by frame.

    The spectator's world starts empty and is rebuilt by replaying the
    authoritative inputs.  If the replay were wrong, the digest would
    differ from the one of the players — which is what this test checks.
    """
    match.run_frames(10, orders_for(match, 3))
    spectator = match.add_spectator("watcher")
    match.catch_up_spectator("watcher")

    assert spectator.frame == 10
    digests = match.digests()
    assert digests["watcher"] == digests["host"]
    assert digests["watcher"] == digests["guest"]


def test_the_spectator_keeps_up_while_the_match_goes_on(match):
    """A spectator that joined late does not freeze.

    The server broadcasts the inputs to the spectators too, so a
    spectator that caught up keeps receiving them and keeps replaying.
    This test checks that it does not fall behind.
    """
    match.run_frames(4)
    spectator = match.add_spectator("watcher")
    match.catch_up_spectator("watcher")

    for step in range(4):
        match.run_frames(3, orders_for(match, 5 + step * 3))
        match.catch_up_spectator("watcher")
        assert spectator.frame == match.clients["host"].frame, (
            "the spectator fell behind at step %d" % step
        )

    digests = match.digests()
    assert digests["watcher"] == digests["host"]
