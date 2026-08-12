"""Rules-driven inventory hold-all victory + production bonus."""

import types

from soundrts import msgparts as mp
from soundrts.worlditem import (
    apply_inventory_production_rates,
    player_inventory_production_bonus_pct,
)
from soundrts.world_inventory_victory import (
    controlling_team,
    inventory_victory_time_seconds,
    item_counts_for_inventory_victory,
    update_inventory_victory,
)


def test_aoe2_parameters_and_relic_victory_flags():
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "mods" / "aoe2" / "rules.txt"
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    for needle in (
        "inventory_victory_time 1000",
        "inventory_victory 1",
        "def aztecs",
        "team_inventory_production_bonus_pct 33",
        "def jaguar_warrior",
        "def atlatl",
        "def garland_wars",
        "def aztec_castle",
        "starting_resources 150 200 200 200",
    ):
        assert needle in text, needle


def test_production_bonus_pct_from_team_attr(monkeypatch):
    class _P:
        faction = "aztecs"
        allied_victory = None
        upgrades = ()

        def __init__(self):
            self.allied_victory = [self]

    monkeypatch.setattr(
        "soundrts.definitions.rules.get",
        lambda faction, key, *a, **k: 33
        if key == "team_inventory_production_bonus_pct"
        else None,
    )
    p = _P()
    assert player_inventory_production_bonus_pct(p) == 33


def test_apply_rates_scales_with_bonus(monkeypatch):
    monkeypatch.setattr(
        "soundrts.worlditem.player_inventory_production_bonus_pct",
        lambda player: 33,
    )

    class _Player:
        def __init__(self):
            self.resources = [0, 0, 0, 0]

    class _Item:
        inventory_production_rates = (500, 0, 0, 0)

    class _Host:
        apply_inventory_production = 1
        inventory = [_Item()]

        def __init__(self):
            self.player = _Player()

    h = _Host()
    apply_inventory_production_rates(h)
    # 500 * 133 // 100 = 665
    assert h.player.resources[0] == 665


def _make_player(pid="p1"):
    voice = []
    player = types.SimpleNamespace(
        id=pid,
        name=[f"player-{pid}"],
        has_victory=False,
        is_playing=True,
        units=[],
        voice=voice,
    )
    player.allied_victory = [player]
    player.is_local_human = lambda: True
    player.send_voice_important = lambda msg: voice.append(list(msg))
    player.victory = lambda: setattr(player, "has_victory", True)
    return player


def test_inventory_victory_timer_and_cancel(monkeypatch):
    monkeypatch.setattr(
        "soundrts.world_inventory_victory.inventory_victory_time_seconds",
        lambda: 100,
    )

    class _Item:
        def __init__(self, iid):
            self.id = iid
            self.inventory_victory = 1
            self.place = None

    p1 = _make_player("a")
    p2 = _make_player("b")
    relic = _Item(1)
    mon = types.SimpleNamespace(inventory=[relic], player=p1)
    p1.units = [mon]

    world = types.SimpleNamespace(
        time=0,
        timer_coefficient=1,
        players=[p1, p2],
        objects={1: relic},
        inventory_victory_state=None,
    )
    team, holder = controlling_team(world)
    assert team is not None and holder is p1

    update_inventory_victory(world)
    assert world.inventory_victory_state["deadline"] == 100000
    assert any(mp.VICTORY_TIMER_STARTED[0] in msg for msg in p1.voice)

    # Drop control: move relic to ground
    mon.inventory = []
    relic.place = object()
    update_inventory_victory(world)
    assert world.inventory_victory_state["deadline"] is None
    assert any(mp.VICTORY_TIMER_CANCELLED[0] in msg for msg in p1.voice)


def test_item_flag_helper():
    assert item_counts_for_inventory_victory(
        types.SimpleNamespace(inventory_victory=1)
    )
    assert not item_counts_for_inventory_victory(
        types.SimpleNamespace(inventory_victory=0)
    )
