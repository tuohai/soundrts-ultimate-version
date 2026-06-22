"""开局观察者位置应跟随首个出生单位，而非按单位名排序。"""

from pathlib import Path


def _source(*parts):
    return (Path(__file__).resolve().parents[2].joinpath(*parts)).read_text(
        encoding="utf-8"
    )


def test_initial_observer_place_uses_spawn_order_not_sort():
    src = _source("soundrts", "clientgame", "game_navigation.py")
    assert "def _initial_observer_place(interface):" in src
    block = src.split("def _initial_observer_place(interface):")[1].split(
        "def set_obs_pos(interface):"
    )[0]
    assert "units(interface)" in block
    assert "sort=True" not in block
    obs_block = src.split("def set_obs_pos(interface):")[1].split(
        "def _follow_if_needed(interface):"
    )[0]
    assert "_initial_observer_place(interface)" in obs_block
    assert "units(interface, sort=True)" not in obs_block
