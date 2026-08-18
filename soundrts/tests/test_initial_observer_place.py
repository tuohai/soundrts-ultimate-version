"""开局观察者位置应跟随首个出生单位，而非按单位名排序。"""

from pathlib import Path
from types import SimpleNamespace

from soundrts.clientgame import game_navigation as nav


def _source(*parts):
    return (Path(__file__).resolve().parents[2].joinpath(*parts)).read_text(
        encoding="utf-8"
    )


def test_initial_observer_place_uses_spawn_order_not_sort():
    src = _source("soundrts", "clientgame", "game_navigation.py")
    assert "def _initial_observer_place(interface):" in src
    block = src.split("def _initial_observer_place(interface):")[1].split(
        "def set_obs_pos(interface"
    )[0]
    assert "units(interface)" in block
    assert "sort=True" not in block
    obs_block = src.split("def set_obs_pos(interface")[1].split(
        "def _follow_if_needed(interface):"
    )[0]
    assert "_initial_observer_place(interface)" in obs_block
    assert "units(interface, sort=True)" not in obs_block
    assert "flush_pending_square_announce" in src


def test_pending_opening_square_is_spoken_from_game_loop(monkeypatch):
    spoken = []
    place = object()
    monkeypatch.setattr(nav, "say_square", lambda iface, p, prefix=[]: spoken.append((p, list(prefix))))
    iface = SimpleNamespace(
        place=place,
        _pending_square_announce={"place": place, "prefix": ["town"]},
    )
    nav.flush_pending_square_announce(iface)
    assert spoken == [(place, ["town"])]
    assert iface._pending_square_announce is None
    nav.flush_pending_square_announce(iface)
    assert spoken == [(place, ["town"])]
