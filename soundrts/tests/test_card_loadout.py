"""Phase 3 card loadout tests."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from soundrts import achievements as ach
from soundrts import card_loadout as loadout
from soundrts import cards as card_mod
from soundrts import titles as title_mod


@pytest.fixture
def card_state(tmp_path, monkeypatch):
    monkeypatch.setattr(ach, "achievements_save_path", lambda faction=None: str(tmp_path / "s.json"))
    card_mod.load_cards("""
        def card_resource_gold
        title 5320
        resource resource1 100

        def card_infantry
        title 5322
        spawn footman 2

        def card_dragon
        title 5326
        spawn dragon 1
        min_rank rank_lieutenant
    """)
    title_mod.load_titles("""
        def rank_recruit
        kind rank
        title 5400
        medals 0
        loadout_slots 0
        def rank_lieutenant
        kind rank
        title 5404
        medals 200
        loadout_slots 2
    """)
    state = ach._empty_unlock_state()
    state["medals"] = 250
    ach.grant_card(state, "card_resource_gold", 1)
    ach.grant_card(state, "card_infantry", 2)
    ach.grant_card(state, "card_dragon", 1)
    return state


def test_validate_loadout_respects_slots_and_rank(card_state):
    validated = loadout.validate_loadout(
        ["card_infantry", "card_infantry", "card_dragon", "card_resource_gold"],
        card_state,
    )
    assert validated == ["card_infantry", "card_infantry"]


def test_consume_loadout_reduces_charges(card_state, tmp_path, monkeypatch):
    monkeypatch.setattr(ach, "achievements_save_path", lambda faction=None: str(tmp_path / "s.json"))
    assert loadout.consume_loadout(card_state, ["card_infantry"]) is True
    assert card_state["cards"]["card_infantry"]["charges"] == 1


def test_apply_card_adds_resources_and_spawns(monkeypatch):
    from soundrts.lib.nofloat import PRECISION

    card_mod.load_cards("""
        def card_resource_gold
        title 5320
        resource resource1 10
        def card_infantry
        title 5322
        spawn footman 1
    """)
    added = []

    class Place:
        def find_and_remove_meadow(self, type_):
            return 1, 2, None

        def find_free_space(self, airground_type, x, y):
            return x, y

    class UnitCls:
        airground_type = "ground"

        def __init__(self, player, place, x, y):
            self.place = place
            added.append("unit")

    monkeypatch.setattr(
        "soundrts.card_loadout.rules.unit_class",
        lambda name: UnitCls if name == "footman" else None,
    )

    player = SimpleNamespace(
        resources=[0, 0],
        units=[],
        number=1,
        world=SimpleNamespace(
            players_starts=[[[0], [("a1", UnitCls, 1)], []]],
            grid={"a1": Place()},
            squares=[Place()],
        ),
        stats=SimpleNamespace(add=lambda *a, **k: None),
    )
    player.add_unit = lambda cls, place, population_cost=None: added.append(
        ("spawn", population_cost)
    ) or player.units.append(SimpleNamespace(place=place))

    assert loadout.apply_card_to_player(player, "card_resource_gold") is True
    assert player.resources[0] == 10 * PRECISION
    assert loadout.apply_card_to_player(player, "card_infantry") is True
    assert ("spawn", None) in added


def test_card_spawn_uses_default_population(monkeypatch):
    card_mod.load_cards("""
        def card_infantry
        title 5322
        spawn footman 2
    """)
    calls = []

    class Place:
        def find_and_remove_meadow(self, type_):
            return 1, 2, None

        def find_free_space(self, airground_type, x, y):
            return x, y

    class UnitCls:
        airground_type = "ground"
        population_cost = 1

        def __init__(self, player, place, x, y):
            self.population_cost = 1
            player.units.append(self)
            player.used_population += 1

    monkeypatch.setattr(
        "soundrts.card_loadout.rules.unit_class",
        lambda name: UnitCls if name == "footman" else None,
    )

    place = Place()
    player = SimpleNamespace(
        resources=[0, 0],
        units=[],
        number=1,
        faction="human",
        world=SimpleNamespace(
            players_starts=[[[0], [("a1", UnitCls, 1)], []]],
            grid={"a1": place},
            squares=[place],
        ),
        stats=SimpleNamespace(add=lambda *a, **k: None),
        used_population=0,
    )

    def add_unit(cls, place, population_cost=None):
        calls.append(population_cost)
        UnitCls(player, place, 0, 0)

    player.add_unit = add_unit
    loadout.apply_card_to_player(player, "card_infantry")
    # No population_cost override: units use their normal population_cost.
    assert calls == [None, None]


def test_apply_training_loadout_only_for_training_game(card_state, tmp_path, monkeypatch):
    monkeypatch.setattr(ach, "achievements_save_path", lambda faction=None: str(tmp_path / "s.json"))
    ach.save_unlock_state(card_state)

    class Player:
        def __init__(self):
            self.resources = [0, 0]
            self.units = []
            self.number = 1
            self.is_human = True
            self.world = SimpleNamespace(players_starts=[], grid={}, squares=[])

        def is_local_human(self):
            return False

        def add_unit(self, *a, **k):
            pass

        stats = SimpleNamespace(add=lambda *a, **k: None)

    player = Player()
    local_client = SimpleNamespace(player=player)
    game = SimpleNamespace(
        game_type_name="mission",
        local_client=local_client,
        world=SimpleNamespace(players=[player]),
    )
    assert loadout.apply_training_loadout(game, ["card_resource_gold"]) == []

    game.game_type_name = "training"
    monkeypatch.setattr(loadout, "apply_card_to_player", lambda p, cid: cid == "card_resource_gold")
    applied = loadout.apply_training_loadout(game, ["card_resource_gold"])
    assert applied == ["card_resource_gold"]
    reloaded = ach.load_unlock_state()
    assert reloaded["cards"]["card_resource_gold"]["charges"] == 0


def test_loadout_available_requires_slots_and_cards(card_state, tmp_path, monkeypatch):
    monkeypatch.setattr(ach, "achievements_save_path", lambda faction=None: str(tmp_path / "s.json"))
    ach.save_unlock_state(card_state)
    monkeypatch.setattr(loadout, "achievements_enabled", lambda: True)
    assert loadout.loadout_available() is True

    empty = ach._empty_unlock_state()
    monkeypatch.setattr(loadout, "load_unlock_state", lambda faction=None: empty)
    assert loadout.loadout_available() is False


def test_resolve_training_faction_uses_faction_caption(monkeypatch):
    from soundrts import achievements_menu as ach_menu
    from soundrts import msgparts as mp

    captured = {}

    def fake_select(caption):
        captured["caption"] = caption
        return "traditionnel"

    monkeypatch.setattr(ach_menu, "select_faction_menu", fake_select)
    monkeypatch.setattr(
        ach_menu,
        "achievements_per_faction_enabled",
        lambda: True,
    )
    monkeypatch.setattr(
        ach_menu,
        "rules",
        type("R", (), {"factions": ["traditionnel", "orc"]})(),
    )
    assert ach_menu.resolve_training_faction("random_faction") == "traditionnel"
    assert captured["caption"] == mp.LOADOUT_SELECT_FACTION


def test_card_armory_explanation_includes_spawn(monkeypatch):
    card_mod.load_cards("""
        def card_infantry
        title 5322
        spawn footman 3
    """)
    monkeypatch.setattr(
        "soundrts.card_loadout.style.get",
        lambda key, attr, **kw: ["86"] if key == "footman" and attr == "title" else None,
    )
    from soundrts import msgparts as mp

    explanation = loadout.card_armory_explanation("card_infantry", medals=300)
    assert mp.ARMORY_CARD_HINT_PREFIX[0] in explanation
    assert mp.ARMORY_CARD_HINT_INSTANT[0] in explanation
    assert mp.ARMORY_CARD_SPAWN_NEAR_START[0] in explanation
    assert "86" in explanation or 86 in explanation
    assert 1000003 in explanation


def test_delayed_card_schedules_spawn(monkeypatch):
    card_mod.load_cards("""
        def card_late
        title 5333
        spawn footman 2
        delay 60
    """)
    scheduled = []
    spawn_calls = []

    class Place:
        def find_and_remove_meadow(self, type_):
            return 1, 2, None

        def find_free_space(self, airground_type, x, y):
            return x, y

    class UnitCls:
        airground_type = "ground"

    class World:
        timer_coefficient = 1
        players = []

        def schedule_after(self, delay_ms, callback):
            scheduled.append((delay_ms, callback))

    world = World()
    player = SimpleNamespace(
        id="1",
        resources=[0, 0],
        units=[],
        number=1,
        faction="human",
        world=world,
        stats=SimpleNamespace(add=lambda *a, **k: None),
    )
    world.players = [player]

    def add_unit(cls, place, population_cost=None):
        spawn_calls.append((population_cost, place))
        player.units.append(SimpleNamespace(place=place))

    player.add_unit = add_unit
    player.is_local_human = lambda: True
    player.pushed = []
    player.push = lambda typ, msg: player.pushed.append((typ, msg))

    monkeypatch.setattr(
        "soundrts.card_loadout.rules.unit_class",
        lambda name: UnitCls if name == "footman" else None,
    )
    monkeypatch.setattr(
        loadout,
        "_spawn_place",
        lambda p: Place(),
    )

    assert loadout.apply_card_to_player(player, "card_late") is True
    assert spawn_calls == []
    assert scheduled == [(60000, scheduled[0][1])]

    scheduled[0][1]()
    assert len(spawn_calls) == 2
    assert all(call[0] is None for call in spawn_calls)
    assert player.pushed


def test_delayed_card_armory_explanation(monkeypatch):
    card_mod.load_cards("""
        def card_late
        title 5333
        spawn footman 3
        delay_minutes 10
    """)
    from soundrts import msgparts as mp

    monkeypatch.setattr(
        "soundrts.card_loadout.style.get",
        lambda key, attr, **kw: ["86"] if key == "footman" and attr == "title" else None,
    )
    explanation = loadout.card_armory_explanation("card_late", medals=300)
    assert mp.ARMORY_CARD_HINT_PREFIX[0] in explanation
    assert mp.ARMORY_CARD_HINT_INSTANT[0] not in explanation
    assert mp.LOADOUT_CARD_DELAY_AFTER[0] in explanation
    assert mp.ARMORY_CARD_SPAWN_DELAYED[0] in explanation
    assert mp.ARMORY_CARD_SPAWN_NEAR_START[0] not in explanation
    assert 1000010 in explanation


def test_loadout_applied_msgs_for_delayed_card():
    card_mod.load_cards("""
        def card_late
        title 5333
        spawn footman 1
        delay_minutes 10
    """)
    from soundrts import msgparts as mp

    msgs = loadout.loadout_applied_msgs(["card_late"])
    assert len(msgs) == 1
    assert mp.LOADOUT_CARD_APPLIED[0] in msgs[0]
    assert mp.LOADOUT_CARD_DELAY_AFTER[0] in msgs[0]
    assert 5333 in msgs[0]
    assert 1000010 in msgs[0]


def test_apply_card_grants_tech(monkeypatch):
    card_mod.load_cards("""
        def card_tech
        title 5334
        tech melee_weapon
    """)
    granted = []

    class UpgradeCls:
        type_name = "melee_weapon"

        @classmethod
        def upgrade_player(cls, player):
            granted.append(cls.type_name)
            player.upgrades.append(cls.type_name)

    monkeypatch.setattr(
        loadout,
        "_resolve_upgrade_class",
        lambda name, faction: UpgradeCls if name == "melee_weapon" else None,
    )

    player = SimpleNamespace(
        resources=[0, 0],
        units=[],
        upgrades=[],
        faction="human",
        stats=SimpleNamespace(add=lambda *a, **k: None),
    )

    assert loadout.apply_card_to_player(player, "card_tech") is True
    assert granted == ["melee_weapon"]
    assert player.upgrades == ["melee_weapon"]


def test_delayed_card_schedules_tech(monkeypatch):
    card_mod.load_cards("""
        def card_late_tech
        title 5334
        tech melee_weapon
        delay 60
    """)
    scheduled = []
    granted = []

    class UpgradeCls:
        type_name = "melee_weapon"

        @classmethod
        def upgrade_player(cls, player):
            granted.append(cls.type_name)
            player.upgrades.append(cls.type_name)

    class World:
        timer_coefficient = 1
        players = []

        def schedule_after(self, delay_ms, callback):
            scheduled.append((delay_ms, callback))

    world = World()
    player = SimpleNamespace(
        id="1",
        resources=[0, 0],
        units=[],
        upgrades=[],
        faction="human",
        world=world,
        stats=SimpleNamespace(add=lambda *a, **k: None),
    )
    world.players = [player]
    player.is_local_human = lambda: True
    player.pushed = []
    player.push = lambda typ, msg: player.pushed.append((typ, msg))

    monkeypatch.setattr(
        loadout,
        "_resolve_upgrade_class",
        lambda name, faction: UpgradeCls if name == "melee_weapon" else None,
    )

    assert loadout.apply_card_to_player(player, "card_late_tech") is True
    assert granted == []
    assert scheduled == [(60000, scheduled[0][1])]

    scheduled[0][1]()
    assert granted == ["melee_weapon"]
    assert player.pushed


def test_delayed_card_armory_explanation_includes_tech(monkeypatch):
    card_mod.load_cards("""
        def card_late_tech
        title 5334
        tech melee_weapon
        delay_minutes 20
    """)
    from soundrts import msgparts as mp

    monkeypatch.setattr(
        "soundrts.card_loadout.style.get",
        lambda key, attr, **kw: ["86"] if key == "melee_weapon" and attr == "title" else None,
    )
    explanation = loadout.card_armory_explanation("card_late_tech", medals=300)
    assert mp.ARMORY_CARD_TECH[0] in explanation
    assert mp.LOADOUT_CARD_DELAY_AFTER[0] in explanation
    assert 1000020 in explanation


def test_train_bonus_card_registers_on_apply(monkeypatch):
    card_mod.load_cards("""
        def card_train
        title 5396
        train_bonus footman 3
    """)
    player = SimpleNamespace(
        faction="human",
        resources=[0, 0],
        stats=SimpleNamespace(add=lambda *a, **k: None),
        units=[],
        used_population=0,
    )
    footman_cls = SimpleNamespace(type_name="footman", airground_type="ground", population_cost=1)

    monkeypatch.setattr(
        loadout,
        "_resolve_unit_class",
        lambda name, faction: footman_cls if name == "footman" else None,
    )
    assert loadout.apply_card_to_player(player, "card_train") is True
    assert player._loadout_train_bonuses == {"footman": 3}


def test_apply_train_bonus_spawns_extra_units(monkeypatch):
    card_mod.load_cards("""
        def card_train
        title 5396
        train_bonus footman 3
    """)
    created = []

    class Footman:
        type_name = "footman"
        airground_type = "ground"
        population_cost = 1

        def __init__(self, player, place, x, y):
            self.player = player
            self.place = place
            self.x = x
            self.y = y
            created.append(self)

        def notify(self, *args):
            pass

        def take_default_order(self, *args):
            pass

    place = SimpleNamespace()

    def find_free_space(airground_type, x, y):
        return x + 100, y

    place.find_free_space = find_free_space

    player = SimpleNamespace(
        faction="human",
        _loadout_train_bonuses={"footman": 3},
        used_population=3,
    )
    monkeypatch.setattr(loadout, "_resolve_unit_class", lambda name, faction: Footman)
    spawned = loadout.apply_train_bonus_for_unit(player, Footman, place, 1000, 1000, None)
    assert spawned == 3
    assert len(created) == 3
    # Bonus units keep their normal population cost (no refund to used_population).
    assert player.used_population == 3
    assert loadout.apply_train_bonus_for_unit(player, Footman, place, 1000, 1000, None) == 0
    assert len(created) == 3


def test_loadout_applied_msgs_for_train_bonus_card():
    from soundrts import msgparts as mp

    card_mod.load_cards("""
        def card_train
        title 5396
        train_bonus footman 3
    """)
    msgs = loadout.loadout_applied_msgs(["card_train"])
    flat = []
    for msg in msgs:
        flat.extend(msg if isinstance(msg, list) else [msg])
    assert mp.LOADOUT_CARD_TRAIN_BONUS_ACTIVE[0] in flat
    assert mp.ARMORY_CARD_TRAIN_BONUS[0] in flat
    assert 5396 in flat


def test_train_bonus_armory_explanation(monkeypatch):
    from soundrts import msgparts as mp

    card_mod.load_cards("""
        def card_train
        title 5396
        train_bonus footman 3
    """)
    monkeypatch.setattr(
        loadout.style,
        "get",
        lambda key, attr, **kw: ["86"] if key == "footman" and attr == "title" else None,
    )
    explanation = loadout.card_armory_explanation("card_train", medals=300)
    assert mp.ARMORY_CARD_HINT_PREFIX[0] in explanation
    assert mp.ARMORY_CARD_HINT_INSTANT[0] not in explanation
    assert mp.ARMORY_CARD_TRAIN_BONUS[0] in explanation
    assert "86" in explanation
