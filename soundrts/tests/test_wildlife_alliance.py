"""狩猎动物电脑在引擎里不得与任何玩家结盟。"""
from __future__ import annotations

import os
import sys
import warnings

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import soundrts.worldunit  # noqa: F401 — 解开循环导入

from soundrts import config

config.debug_mode = 0
config.mods = ""

_saved_argv = sys.argv
try:
    sys.argv = [_saved_argv[0]] if _saved_argv else ["pytest"]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from soundrts.mapfile import Map
        from soundrts.randommap import RandomMapConfig, generate_definition
        from soundrts.world import World
        from soundrts.worldclient import DirectClient
finally:
    sys.argv = _saved_argv


class _DeerCls:
    is_huntable = 1
    herdable = 0


class _SheepCls:
    is_huntable = 1
    herdable = 1


class _FootCls:
    is_huntable = 0
    herdable = 0


def _load_rules():
    from soundrts.definitions import rules

    with open("res/rules.txt", encoding="utf-8") as f:
        rules.load(f.read())
    return rules


def test_computer_start_is_wildlife_only_detects_deer_slot():
    from soundrts.worldplayerbase.base import computer_start_is_wildlife_only

    assert computer_start_is_wildlife_only(
        [[], [("a1", _DeerCls, 3)], [], True]
    )
    assert computer_start_is_wildlife_only(
        [[], [("a1", _SheepCls, 2)], [], True]
    )
    assert not computer_start_is_wildlife_only(
        [[], [("a1", _FootCls, 3), ("a1", _DeerCls, 2)], [], True]
    )
    assert not computer_start_is_wildlife_only(
        [[], [("a1", _FootCls, 3)], [], False]
    )


def test_wildlife_owners_are_not_allied_with_creep_or_human():
    from soundrts.worldplayerbase.base import player_is_wildlife_only

    _load_rules()

    text, _ = generate_definition(RandomMapConfig(seed=42))
    m = Map.loads(text.encode("utf-8"), "random_42.txt")
    world = World(seed=42)
    world.load_and_build_map(m)
    client = DirectClient("p1", None)
    world.populate_map([client], random_starts=False)

    human = world.players[0]
    wildlife_owners = [p for p in world.players if player_is_wildlife_only(p)]
    creep_owners = [
        p
        for p in world.players
        if p is not human
        and not player_is_wildlife_only(p)
        and any(getattr(u, "type_name", None) == "footman" for u in p.units)
    ]

    assert wildlife_owners, "expected hunting spawns on random map"
    assert creep_owners, "expected center creep on random map"

    for owner in wildlife_owners:
        assert owner.client.alliance is None
        assert owner.allied == [owner]
        assert owner not in human.allied
        assert human not in owner.allied
        for creep in creep_owners:
            assert owner not in creep.allied
            assert creep not in owner.allied
