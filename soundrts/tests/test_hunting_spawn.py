"""狩猎尸体生成：动物死后必须在原地留下可采集矿床。"""
from __future__ import annotations

import sys
import types

sys.argv = ["pytest"]

import soundrts.worldunit  # noqa: F401

from soundrts.definitions import rules
from soundrts.worldresource import Deposit
from soundrts.worldunit.worldcreature import Creature


class _Square:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.objects = []
        self.is_inside_place = False
        self.world = types.SimpleNamespace(
            unit_class=lambda name: rules.unit_class(name),
            unregister_entity=lambda _e: None,
        )

    def enter(self, obj):
        self.objects.append(obj)

    def leave(self, obj):
        if obj in self.objects:
            self.objects.remove(obj)

    def add(self, obj):
        if obj not in self.objects:
            self.objects.append(obj)

    def remove(self, obj):
        if obj in self.objects:
            self.objects.remove(obj)

    def find_free_space_for(self, *_args, **_kwargs):
        return None, None


def _load_rules():
    with open("res/rules.txt", encoding="utf-8") as f:
        rules.load(f.read())


def test_create_hunt_food_deposit_on_animal_position():
    _load_rules()
    sq = _Square()
    deposit = Creature._create_hunt_food_deposit(
        sq.world, "food_carcass", 35, sq, 1200, 2400, source_type_name="deer"
    )
    assert deposit is not None
    assert isinstance(deposit, Deposit)
    assert deposit.qty == 35000
    assert deposit.x == 1200
    assert deposit.y == 2400
    assert deposit.place is sq
    assert deposit.collision == 0
    assert deposit.carcass_of == "deer"
    assert deposit in sq.objects


def test_die_spawns_deposit_after_unit_removed():
    _load_rules()
    sq = _Square()

    class _Deer(Creature):
        type_name = "deer"
        food_deposit = "food_carcass"
        food_deposit_qty = 35
        corpse = 0
        is_vulnerable = True
        stat_type = "unit"

        def __init__(self):
            self.world = sq.world
            self.place = sq
            self.x = 500
            self.y = 600
            self.player = types.SimpleNamespace(
                stats=types.SimpleNamespace(add=lambda *a: None),
                on_unit_attacked=lambda *a: None,
            )
            self._buffs = []
            self.inside = None
            self.hp = 0
            self.id = 7
            self.notify = lambda *a, **k: None
            self.delete = lambda: setattr(self, "place", None)

    deer = _Deer()
    hunter = types.SimpleNamespace(
        player=types.SimpleNamespace(
            id="hunter",
            player_is_an_enemy=lambda _p: False,
            stats=types.SimpleNamespace(add=lambda *a: None),
            record_unit_killed=lambda *a: None,
        ),
        can_gather_deposit=["food_carcass"],
        orders=[],
        take_order=lambda *a, **k: None,
        _can_gather_target=lambda d: True,
    )
    deer.die(attacker=hunter, notify_death=False)

    deposits = [o for o in sq.objects if isinstance(o, Deposit)]
    assert len(deposits) == 1
    assert deposits[0].qty == 35000
    assert deposits[0].x == 500
    assert deposits[0].y == 600
    assert deposits[0].carcass_of == "deer"


def test_carcass_short_title_includes_source_animal():
    _load_rules()
    from types import SimpleNamespace
    from soundrts import msgparts as mp
    from soundrts.clientgameentity.properties import carcass_short_title

    deposit = SimpleNamespace(type_name="food_carcass", carcass_of="deer")
    title = carcass_short_title(deposit)
    assert any(str(p) == "4930" for p in title)
    assert mp.CORPSE[0] in title

    plain = carcass_short_title(SimpleNamespace(type_name="food_carcass"))
    assert any(str(p) == "4932" for p in plain)
