"""claimable proximity claim + pasture spawn_player_cap (rules-driven)."""
from __future__ import annotations

import types

import pytest


def test_on_claim_ok_plays_style_and_voice(monkeypatch):
    """Client claim feedback: confirmation sound + TTS (animal + claimed)."""
    import soundrts.clientgameentity.events as ev
    from soundrts.clientgameentity.events import EntityViewEvents

    played = []
    spoken = []

    class _V(EntityViewEvents):
        def launch_event_style(self, attr, alert=False, priority=0):
            played.append((attr, alert))

        def get_style(self, attr):
            if attr == "claim_ok":
                return ["1194"]
            if attr == "claim_ok_msg":
                return ["$1", "4937"]
            return None

    v = _V()
    monkeypatch.setattr(ev.voice, "info", lambda msg, **k: spoken.append(list(msg)))
    monkeypatch.setattr(
        ev.style,
        "get",
        lambda type_name, key, warn_if_not_found=True: (
            ["4931"] if type_name == "sheep" and key == "title" else None
        ),
    )
    v.on_claim_ok("sheep")
    assert played == [("claim_ok", True)]
    assert spoken and "4937" in spoken[0] and "4931" in spoken[0]
    from soundrts.definitions import Rules

    assert "claimable" in Rules.int_properties
    assert "claim_range" in Rules.int_properties
    assert "spawn_player_cap" in Rules.int_properties
    assert "spawn_immediate" in Rules.int_properties


def test_aoe2_sheep_is_claimable_and_pasture_spawns_sheep():
    from pathlib import Path

    path = Path("mods/aoe2/rules.txt")
    if not path.is_file():
        pytest.skip("aoe2 rules not present")
    text = path.read_text(encoding="utf-8")
    sheep = text.split("def sheep", 1)[1].split("def ", 1)[0]
    assert "claimable 1" in sheep
    assert "claim_range 12000" in sheep
    assert "herdable 1" in sheep
    pasture = text.split("def pasture", 1)[1].split("def ", 1)[0]
    assert "spawns_unit sheep" in pasture
    assert "spawn_player_cap 30" in pasture
    assert "spawn_immediate 1" in pasture
    herdsman = text.split("def mongol_herdsman", 1)[1].split("def ", 1)[0]
    assert "pasture" in herdsman
    assert "can_build house farm" not in herdsman
    build_line = next(
        ln for ln in herdsman.splitlines() if ln.strip().startswith("can_build ")
    )
    assert "pasture" in build_line
    assert " mill " not in f" {build_line} ".replace(" lumbermill ", " ")
    tech_line = next(
        ln for ln in herdsman.splitlines() if ln.strip().startswith("can_use_tech ")
    )
    assert "horse_collar" not in tech_line
    assert "requirements mill" not in pasture
    assert "storable_resource_types resource3" in pasture
    assert "requirements town_center" in pasture


def test_base_sheep_is_claimable():
    from pathlib import Path

    path = Path("res/rules.txt")
    if not path.is_file():
        pytest.skip("res rules not present")
    sheep = path.read_text(encoding="utf-8").split("def sheep", 1)[1].split("def ", 1)[0]
    assert "claimable 1" in sheep
    assert "claim_range 12000" in sheep
    assert "herdable 1" in sheep


def test_try_auto_claim_transfers_to_non_neutral_player():
    import soundrts.worldunit  # noqa: F401
    from soundrts.worldunit.world_status_update import CreatureStatusUpdate

    claimed = []
    events = []

    place = types.SimpleNamespace(objects=[], neighbors=[], id="a", x=0, y=0)
    scout_player = types.SimpleNamespace(neutral=False, allied=[])
    wildlife = types.SimpleNamespace(neutral=True, remove=lambda u: None, add=lambda u: None)

    class _Animal(CreatureStatusUpdate):
        claimable = 1
        claim_range = 0
        herdable = 1
        type_name = "sheep"

        def set_player(self, player):
            claimed.append(player)
            self.player = player

        def stop(self):
            pass

        def cancel_all_orders(self, unpay=False):
            pass

    class _Scout:
        basic_skills = ()

        def notify(self, ev):
            events.append(ev)

    animal = object.__new__(_Animal)
    animal.player = wildlife
    animal.flee_on_hit = 1
    animal.place = place
    animal.x = 0
    animal.y = 0
    animal.hp = 10
    animal.inside = None
    scout = _Scout()
    scout.place = place
    scout.x = 100
    scout.y = 0
    scout.hp = 20
    scout.player = scout_player
    place.objects = [animal, scout]

    assert animal._try_auto_claim() is True
    assert claimed == [scout_player]
    assert animal.player is scout_player
    assert animal.flee_on_hit == 0
    assert events == ["claim_ok,sheep"]
    assert animal.flee_on_hit == 0
    assert events == ["claim_ok,sheep"]
    assert animal.flee_on_hit == 0


def test_try_auto_claim_ignores_neutral_neighbors():
    import soundrts.worldunit  # noqa: F401
    from soundrts.worldunit.world_status_update import CreatureStatusUpdate

    place = types.SimpleNamespace(objects=[], neighbors=[], id="a")
    wildlife_a = types.SimpleNamespace(neutral=True)
    wildlife_b = types.SimpleNamespace(neutral=True)

    class _Animal(CreatureStatusUpdate):
        claimable = 1
        claim_range = 0

        def set_player(self, _p):
            raise AssertionError("must not claim")

    animal = object.__new__(_Animal)
    animal.player = wildlife_a
    animal.place = place
    animal.x = 0
    animal.y = 0
    animal.hp = 10
    other = types.SimpleNamespace(place=place, x=1, y=0, hp=5, player=wildlife_b)
    place.objects = [animal, other]
    assert animal._try_auto_claim() is False


def test_spawn_player_cap_blocks_further_spawns(monkeypatch):
    from soundrts import world_build_rules as wbr

    host_player = types.SimpleNamespace(units=[])
    place = types.SimpleNamespace(
        objects=[],
        find_free_space=lambda *_a, **_k: (10, 10),
    )
    host = types.SimpleNamespace(
        spawns_unit="sheep",
        larva_cap=8,
        spawn_player_cap=2,
        spawn_immediate=1,
        player=host_player,
        place=place,
        x=0,
        y=0,
        type_name="pasture",
        hp=100,
    )

    class _FakeSheep:
        def __init__(self, player, place, x, y):
            self.type_name = "sheep"
            self.player = player
            self.place = place
            self.hp = 10
            self.x = x
            self.y = y
            player.units.append(self)
            place.objects.append(self)

        def notify(self, _ev):
            pass

    monkeypatch.setattr(wbr.rules, "unit_class", lambda name: _FakeSheep if name == "sheep" else None)

    assert wbr.spawn_unit_at_host(host, 1) == 1
    assert wbr.spawn_unit_at_host(host, 1) == 1
    assert wbr.count_spawned_for_player(host) == 2
    assert wbr.spawn_unit_at_host(host, 1) == 0


def test_tick_spawn_immediate_spawns_first_unit(monkeypatch):
    from soundrts import world_build_rules as wbr

    host_player = types.SimpleNamespace(units=[], is_playing=True)
    place = types.SimpleNamespace(
        objects=[],
        find_free_space=lambda *_a, **_k: (5, 5),
    )
    host = types.SimpleNamespace(
        spawns_unit="sheep",
        larva_cap=8,
        larva_spawn_time=112000,
        spawn_player_cap=30,
        spawn_immediate=1,
        player=host_player,
        place=place,
        x=0,
        y=0,
        type_name="pasture",
        hp=100,
        _unit_spawn_time=None,
    )
    host_player.units = [host]

    class _FakeSheep:
        def __init__(self, player, place, x, y):
            self.type_name = "sheep"
            self.player = player
            self.place = place
            self.hp = 10
            player.units.append(self)
            place.objects.append(self)

        def notify(self, _ev):
            pass

    monkeypatch.setattr(wbr.rules, "unit_class", lambda name: _FakeSheep if name == "sheep" else None)
    world = types.SimpleNamespace(time=1000, players=[host_player])
    wbr.tick_unit_spawns(world)
    assert sum(1 for u in host_player.units if getattr(u, "type_name", None) == "sheep") == 1
    assert host._unit_spawn_time == 1000


def test_init_spawn_immediate_does_not_fill_larva_cap(monkeypatch):
    """Pasture complete must not dump larva_cap sheep at once (hatchery fill is separate)."""
    from soundrts import world_build_rules as wbr

    host_player = types.SimpleNamespace(units=[], world=types.SimpleNamespace(time=5000))
    place = types.SimpleNamespace(
        objects=[],
        find_free_space=lambda *_a, **_k: (3, 3),
    )
    host = types.SimpleNamespace(
        spawns_unit="sheep",
        larva_cap=8,
        spawn_player_cap=30,
        spawn_immediate=1,
        player=host_player,
        place=place,
        x=0,
        y=0,
        type_name="pasture",
        hp=100,
        _unit_spawn_time=None,
    )
    host_player.units = [host]

    class _FakeSheep:
        def __init__(self, player, place, x, y):
            self.type_name = "sheep"
            self.player = player
            self.place = place
            self.hp = 10
            player.units.append(self)
            place.objects.append(self)

        def notify(self, _ev):
            pass

    monkeypatch.setattr(wbr.rules, "unit_class", lambda name: _FakeSheep if name == "sheep" else None)
    wbr.init_spawn_host_on_ready(host, notify=False)
    assert sum(1 for u in host_player.units if getattr(u, "type_name", None) == "sheep") == 1
    assert host._unit_spawn_time == 5000


def test_init_spawn_immediate_idempotent_on_double_finalize(monkeypatch):
    """Building.__init__ + BuildingSite complete both finalize; must stay at 1 sheep."""
    from soundrts import world_build_rules as wbr

    host_player = types.SimpleNamespace(units=[], world=types.SimpleNamespace(time=7000))
    place = types.SimpleNamespace(
        objects=[],
        find_free_space=lambda *_a, **_k: (2, 2),
    )
    host = types.SimpleNamespace(
        spawns_unit="sheep",
        larva_cap=8,
        spawn_player_cap=30,
        spawn_immediate=1,
        player=host_player,
        place=place,
        x=0,
        y=0,
        type_name="pasture",
        hp=100,
        _unit_spawn_time=None,
    )
    host_player.units = [host]

    class _FakeSheep:
        def __init__(self, player, place, x, y):
            self.type_name = "sheep"
            self.player = player
            self.place = place
            self.hp = 10
            player.units.append(self)
            place.objects.append(self)

        def notify(self, _ev):
            pass

    monkeypatch.setattr(wbr.rules, "unit_class", lambda name: _FakeSheep if name == "sheep" else None)
    wbr.init_spawn_host_on_ready(host, notify=False)
    wbr.init_spawn_host_on_ready(host, notify=False)
    assert sum(1 for u in host_player.units if getattr(u, "type_name", None) == "sheep") == 1
    assert host._unit_spawn_time == 7000


def test_init_without_immediate_still_fills_cap(monkeypatch):
    """Hatchery-style hosts still fill to larva_cap on ready."""
    from soundrts import world_build_rules as wbr

    host_player = types.SimpleNamespace(units=[])
    place = types.SimpleNamespace(
        objects=[],
        find_free_space=lambda *_a, **_k: (1, 1),
    )
    host = types.SimpleNamespace(
        spawns_unit="larva",
        larva_cap=3,
        spawn_player_cap=0,
        spawn_immediate=0,
        player=host_player,
        place=place,
        x=0,
        y=0,
        type_name="hatchery",
        hp=100,
    )
    host_player.units = [host]

    class _FakeLarva:
        def __init__(self, player, place, x, y):
            self.type_name = "larva"
            self.player = player
            self.place = place
            self.hp = 10
            player.units.append(self)
            place.objects.append(self)

        def notify(self, _ev):
            pass

    monkeypatch.setattr(wbr.rules, "unit_class", lambda name: _FakeLarva if name == "larva" else None)
    wbr.init_spawn_host_on_ready(host, notify=False)
    assert sum(1 for u in host_player.units if getattr(u, "type_name", None) == "larva") == 3


def test_owned_sheep_does_not_flee_from_owner_attack():
    import soundrts.worldunit  # noqa: F401
    from soundrts.worldunit.world_ai_decision import CreatureAIDecision

    owner = types.SimpleNamespace(neutral=False, allied=[])
    owner.allied = [owner]
    orders = []

    class _Sheep(CreatureAIDecision):
        flee_on_hit = 1
        speed = 10
        place = types.SimpleNamespace(exits=[], id="a")
        x = 0
        y = 0
        player = owner

        def take_order(self, cmd, imperative=False):
            orders.append(cmd)

        def notify(self, _ev):
            pass

    sheep = object.__new__(_Sheep)
    sheep.player = owner
    sheep.flee_on_hit = 1
    sheep.speed = 10
    sheep.place = types.SimpleNamespace(exits=[], id="a")
    sheep.x = 0
    sheep.y = 0
    villager = types.SimpleNamespace(player=owner, place=sheep.place, x=1, y=0)
    sheep.last_attacker = villager
    assert sheep._attacker_is_owner_or_ally() is True
    assert sheep._flee_from_attacker() is False
    assert sheep.last_attacker is None
    assert orders == []


def test_claimable_neutral_default_order_is_go_not_attack():
    import soundrts.worldunit  # noqa: F401
    from soundrts.worldunit.worldsoldier import Soldier

    sheep = types.SimpleNamespace(
        claimable=1,
        is_huntable=1,
        herdable=1,
        hp=4,
        player=types.SimpleNamespace(neutral=True),
    )
    soldier = Soldier.__new__(Soldier)
    soldier._basic_skills = {"go", "attack", "patrol"}
    soldier.orders = []
    soldier.player = types.SimpleNamespace(get_object_by_id=lambda _id: sheep)
    assert soldier.get_default_order(1) == "go"
    # Imperative: attack neutrals (Ctrl+Backspace / imperative go)
    assert soldier.resolve_imperative_go_order(1) == "attack"
    assert soldier.get_resolved_default_order(1, imperative=True) == "attack"


def test_foreign_huntable_defaults_to_go_even_if_not_neutral():
    """Wild sheep without reliable player.neutral must still default to go."""
    import soundrts.worldunit  # noqa: F401
    from soundrts.worldunit.worldsoldier import Soldier

    me = types.SimpleNamespace(neutral=False)
    sheep = types.SimpleNamespace(
        claimable=1,
        is_huntable=1,
        herdable=1,
        hp=4,
        player=types.SimpleNamespace(neutral=False),
    )
    soldier = Soldier.__new__(Soldier)
    soldier._basic_skills = {"go", "attack", "patrol"}
    soldier.orders = []
    soldier.player = me
    me.get_object_by_id = lambda _id: sheep
    assert soldier.get_default_order(1) == "go"


def test_neutral_unit_default_order_is_go():
    import soundrts.worldunit  # noqa: F401
    from soundrts.worldunit.worldsoldier import Soldier

    npc = types.SimpleNamespace(
        claimable=0,
        is_huntable=0,
        herdable=0,
        hp=10,
        player=types.SimpleNamespace(neutral=True),
    )
    soldier = Soldier.__new__(Soldier)
    soldier._basic_skills = {"go", "attack", "patrol"}
    soldier.orders = []
    soldier.player = types.SimpleNamespace(get_object_by_id=lambda _id: npc)
    assert soldier.get_default_order(1) == "go"


def test_owned_huntable_default_order_is_go():
    """Own sheep: default is go; slaughter needs imperative attack."""
    import soundrts.worldunit  # noqa: F401
    from soundrts.worldunit.worldsoldier import Soldier

    owner = types.SimpleNamespace(neutral=False)
    sheep = types.SimpleNamespace(
        claimable=1,
        is_huntable=1,
        herdable=1,
        hp=4,
        player=owner,
        have_enough_space=lambda _u: False,
    )
    owner.get_object_by_id = lambda _id: sheep
    soldier = Soldier.__new__(Soldier)
    soldier._basic_skills = {"go", "attack", "patrol"}
    soldier.orders = []
    soldier.player = owner
    soldier.have_enough_space = lambda _t: False
    assert soldier.get_default_order(1) == "go"
    assert soldier.get_resolved_default_order(1, imperative=True) == "attack"


def test_imperative_go_attacks_claimable_neutral():
    import soundrts.worldunit  # noqa: F401
    from soundrts.worldunit.world_order import CreatureOrders

    sheep = types.SimpleNamespace(
        claimable=1,
        hp=4,
        player=types.SimpleNamespace(neutral=True),
        is_vulnerable=True,
    )
    recorded = []

    class _Unit(CreatureOrders):
        is_inside = False
        orders = []
        basic_skills = {"go", "attack"}

        def __init__(self):
            self.player = types.SimpleNamespace(get_object_by_id=lambda _id: sheep)

        def notify(self, *_a, **_k):
            pass

        def cancel_all_orders(self):
            pass

    unit = _Unit()

    class _GoCls:
        never_forget_previous = False

        @classmethod
        def is_allowed(cls, *_a, **_k):
            return True

        def __init__(self, u, args):
            recorded.append(("go", list(args)))

        def immediate_action(self):
            pass

    class _AttackCls:
        never_forget_previous = False

        @classmethod
        def is_allowed(cls, *_a, **_k):
            return True

        def __init__(self, u, args):
            recorded.append(("attack", list(args)))

        def immediate_action(self):
            pass

    import soundrts.worldunit.world_order as wo

    old = dict(wo.ORDERS_DICT)
    try:
        wo.ORDERS_DICT["go"] = _GoCls
        wo.ORDERS_DICT["attack"] = _AttackCls
        unit.take_order(["go", "sheep1"], imperative=True)
    finally:
        wo.ORDERS_DICT.clear()
        wo.ORDERS_DICT.update(old)

    assert recorded and recorded[0][0] == "attack"


def _make_claim_animal(place, owner, CreatureStatusUpdate):
    class _Animal(CreatureStatusUpdate):
        claimable = 1
        claim_range = 0
        herdable = 1
        type_name = "sheep"
        is_a_building = False

        def set_player(self, player):
            self.player = player

        def stop(self):
            pass

        def cancel_all_orders(self, unpay=False):
            pass

    animal = object.__new__(_Animal)
    animal.player = owner
    animal.flee_on_hit = 1
    animal.place = place
    animal.x = 0
    animal.y = 0
    animal.hp = 10
    animal.inside = None
    animal._herd_leader = None
    return animal


def _make_unit(place, player, x=1, y=0):
    u = types.SimpleNamespace(
        place=place,
        x=x,
        y=y,
        hp=20,
        player=player,
        inside=None,
        is_a_building=False,
        herdable=0,
        claimable=0,
        basic_skills=(),
    )
    u.notify = lambda ev: None
    return u


def test_unguarded_owned_sheep_can_be_stolen():
    import soundrts.worldunit  # noqa: F401
    from soundrts.worldunit.world_status_update import CreatureStatusUpdate

    place = types.SimpleNamespace(objects=[], neighbors=[], id="a")
    owner = types.SimpleNamespace(neutral=False, allied=[], faction="britons")
    thief = types.SimpleNamespace(neutral=False, allied=[], faction="franks")
    animal = _make_claim_animal(place, owner, CreatureStatusUpdate)
    scout = _make_unit(place, thief)
    place.objects = [animal, scout]
    assert animal._try_steal_owned_herdable() is True
    assert animal.player is thief


def test_guarded_owned_sheep_blocks_without_ignore_flag(monkeypatch):
    import soundrts.worldunit  # noqa: F401
    from soundrts.worldunit.world_status_update import CreatureStatusUpdate
    import soundrts.world_civ_bonuses as wcb

    monkeypatch.setattr(wcb, "herdable_steal_ignore_guards", lambda p: False)
    monkeypatch.setattr(wcb, "herdable_steal_protected", lambda p: False)

    place = types.SimpleNamespace(objects=[], neighbors=[], id="a")
    owner = types.SimpleNamespace(neutral=False, allied=[])
    thief = types.SimpleNamespace(neutral=False, allied=[])
    animal = _make_claim_animal(place, owner, CreatureStatusUpdate)
    guard = _make_unit(place, owner, x=2)
    scout = _make_unit(place, thief, x=3)
    place.objects = [animal, guard, scout]
    assert animal._try_steal_owned_herdable() is False
    assert animal.player is owner


def test_ignore_guards_steals_unguarded_flag_owner(monkeypatch):
    import soundrts.worldunit  # noqa: F401
    from soundrts.worldunit.world_status_update import CreatureStatusUpdate
    import soundrts.world_civ_bonuses as wcb

    monkeypatch.setattr(
        wcb, "herdable_steal_ignore_guards", lambda p: bool(getattr(p, "ignore_guards", False))
    )
    monkeypatch.setattr(
        wcb, "herdable_steal_protected", lambda p: bool(getattr(p, "flock_protected", False))
    )

    place = types.SimpleNamespace(objects=[], neighbors=[], id="a")
    owner = types.SimpleNamespace(neutral=False, allied=[], flock_protected=False)
    thief = types.SimpleNamespace(neutral=False, allied=[], ignore_guards=True)
    animal = _make_claim_animal(place, owner, CreatureStatusUpdate)
    guard = _make_unit(place, owner, x=2)
    scout = _make_unit(place, thief, x=3)
    place.objects = [animal, guard, scout]
    assert animal._try_steal_owned_herdable() is True
    assert animal.player is thief


def test_protected_flock_stays_when_guarded(monkeypatch):
    import soundrts.worldunit  # noqa: F401
    from soundrts.worldunit.world_status_update import CreatureStatusUpdate
    import soundrts.world_civ_bonuses as wcb

    monkeypatch.setattr(wcb, "herdable_steal_ignore_guards", lambda p: True)
    monkeypatch.setattr(
        wcb, "herdable_steal_protected", lambda p: bool(getattr(p, "flock_protected", False))
    )

    place = types.SimpleNamespace(objects=[], neighbors=[], id="a")
    owner = types.SimpleNamespace(neutral=False, allied=[], flock_protected=True)
    thief = types.SimpleNamespace(neutral=False, allied=[], ignore_guards=True)
    animal = _make_claim_animal(place, owner, CreatureStatusUpdate)
    guard = _make_unit(place, owner, x=2)
    scout = _make_unit(place, thief, x=3)
    place.objects = [animal, guard, scout]
    assert animal._try_steal_owned_herdable() is False
    assert animal.player is owner
