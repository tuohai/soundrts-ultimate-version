# -*- coding: utf-8 -*-
"""AI must deploy detectors to hunt hidden (invisible / cloaked) enemies.

crazyMod's Zerg hatchery (``couveuse``) has ``is_invisible 1``.  The AI
destroyed every visible structure but never noticed the invisible hatchery,
so the game deadlocked forever.

The AI must:
1. notice that a hostile player is still alive while it sees nothing, and
2. send its ``is_a_detector`` units out to sweep for the hidden enemy.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from soundrts.definitions import rules
from soundrts.worldplayercomputer import Computer
from soundrts.worldunit import Soldier


def _make_comp(**kwargs):
    comp = Computer.__new__(Computer)
    comp.world = SimpleNamespace(players=[], time=0, turn=0)
    comp.units = []
    comp.memory = set()
    comp.perception = set()
    comp._enemy_presence = []
    comp._detector_units = []
    comp._hidden_enemy_sweep_active = False
    comp._ever_saw_enemy = True
    for k, v in kwargs.items():
        setattr(comp, k, v)
    return comp


class _Building:
    """An enemy building as the AI perceives it."""

    def __init__(self, name="townhall"):
        self.type_name = name
        self.is_a_building = True
        self.id = name
        self.place = None


class _Unit:
    def __init__(self, name, *, is_detector=False, speed=1.0, airground="ground"):
        self.type_name = name
        self.id = name
        self.is_a_detector = is_detector
        self.speed = speed
        self.airground_type = airground
        self.is_inside = False
        self.orders = []
        self.place = None

    def cancel_all_orders(self):
        self.orders = []

    def take_order(self, order, **kwargs):
        self.orders.append(
            SimpleNamespace(
                keyword=order[0], target=order[1] if len(order) > 1 else None
            )
        )


class _Place:
    def __init__(self, pid):
        self.id = pid
        self.is_inside_place = False

    def __repr__(self):
        return f"<Place {self.id}>"


def test_sweep_detector_units_filters_immobile_and_water():
    comp = _make_comp()
    mobile = _Unit("capteur_mobile", is_detector=True)
    radar = _Unit("tour_radar", is_detector=True, speed=0)
    boat = _Unit("bateau", is_detector=True, airground="water")
    comp._detector_units = [mobile, radar, boat]
    assert comp._sweep_detector_units() == [mobile]


def test_hidden_enemy_needs_sweep_when_enemy_alive_but_invisible():
    enemy = SimpleNamespace(units=[object()], is_playing=True, neutral=False)
    comp = _make_comp()
    comp.world.players = [comp, enemy]
    comp.player_is_a_hostile_enemy = lambda p: p is not comp
    comp._detector_units = [_Unit("capteur_mobile", is_detector=True)]
    assert comp._hidden_enemy_needs_sweep() is True


def test_no_sweep_when_an_enemy_building_is_visible():
    """An enemy building is visible → nothing hidden to hunt for."""
    enemy = SimpleNamespace(units=[object()], is_playing=True, neutral=False)
    comp = _make_comp()
    comp.world.players = [comp, enemy]
    comp.player_is_a_hostile_enemy = lambda p: p is not comp
    comp.is_an_enemy = lambda o: True
    comp._detector_units = [_Unit("capteur_mobile", is_detector=True)]
    comp.perception = {_Building()}
    assert comp._hidden_enemy_needs_sweep() is False


def test_sweep_when_only_enemy_units_are_visible():
    """The real crazyMod case: enemy units visible, hatchery invisible."""
    enemy = SimpleNamespace(units=[object()], is_playing=True, neutral=False)
    comp = _make_comp()
    comp.world.players = [comp, enemy]
    comp.player_is_a_hostile_enemy = lambda p: p is not comp
    comp.is_an_enemy = lambda o: True
    comp._detector_units = [_Unit("capteur_mobile", is_detector=True)]
    comp._enemy_presence = [object()]  # enemy units are seen
    comp.perception = set()
    assert comp._hidden_enemy_needs_sweep() is True


def test_no_sweep_when_enemy_is_really_dead():
    enemy = SimpleNamespace(units=[], is_playing=True, neutral=False)
    comp = _make_comp()
    comp.world.players = [comp, enemy]
    comp.player_is_a_hostile_enemy = lambda p: p is not comp
    comp._detector_units = [_Unit("capteur_mobile", is_detector=True)]
    assert comp._hidden_enemy_needs_sweep() is False


def test_no_sweep_without_detectors():
    """The situation still calls for a sweep — the AI must build a detector."""
    enemy = SimpleNamespace(units=[object()], is_playing=True, neutral=False)
    comp = _make_comp()
    comp.world.players = [comp, enemy]
    comp.player_is_a_hostile_enemy = lambda p: p is not comp
    comp._detector_units = []
    assert comp._hidden_enemy_needs_sweep() is True


def test_sweep_is_not_needed_when_a_detector_cannot_be_built():
    """No detector and none obtainable → the AI must not spin forever."""
    enemy = SimpleNamespace(units=[object()], is_playing=True, neutral=False)
    comp = _make_comp()
    comp.world.players = [comp, enemy]
    comp.player_is_a_hostile_enemy = lambda p: p is not comp
    comp._detector_units = []
    comp._mobile_detector_candidates_cache = []
    comp._ensure_mobile_detector = lambda: False
    assert comp._maintain_hidden_enemy_sweep() is False
    assert comp._sweeping_for_hidden_enemy() is False


def test_no_sweep_before_the_enemy_was_ever_seen():
    """Opening of the match: the scout's job, not the detectors'."""
    enemy = SimpleNamespace(units=[object()], is_playing=True, neutral=False)
    comp = _make_comp()
    comp.world.players = [comp, enemy]
    comp.player_is_a_hostile_enemy = lambda p: p is not comp
    comp._detector_units = [_Unit("capteur_mobile", is_detector=True)]
    comp._ever_saw_enemy = False
    assert comp._hidden_enemy_needs_sweep() is False


def test_enemy_is_known_records_that_the_enemy_was_seen():
    comp = _make_comp()
    comp._ever_saw_enemy = False
    comp._enemy_presence = []
    assert comp._enemy_is_known() is False
    assert comp._ever_saw_enemy is False
    comp._enemy_presence = [object()]
    assert comp._enemy_is_known() is True
    assert comp._ever_saw_enemy is True


def test_maintain_sweep_dispatches_detector(monkeypatch):
    enemy = SimpleNamespace(units=[object()], is_playing=True, neutral=False)
    comp = _make_comp()
    comp.world.players = [comp, enemy]
    comp.player_is_a_hostile_enemy = lambda p: p is not comp
    detector = _Unit("capteur_mobile", is_detector=True)
    comp._detector_units = [detector]
    comp.is_an_enemy = lambda o: True
    comp._world_place_for_pathfinding = lambda p: p
    comp.memory = set()
    comp._ensure_mobile_detector = lambda: True
    monkeypatch.setattr(
        type(comp), "unknown_starting_squares", property(lambda self: [])
    )
    monkeypatch.setattr(
        type(comp), "squares_to_watch", property(lambda self: [_Place("sq1")])
    )

    assert comp._maintain_hidden_enemy_sweep() is True
    assert detector.orders
    assert detector.orders[0].keyword == "go"
    assert comp._sweeping_for_hidden_enemy() is True


def test_sweep_assignment_is_stable(monkeypatch):
    """The detector must keep the same target, or it never arrives.

    The candidate list is rebuilt every turn from the AI's memory (a set,
    whose iteration order changes), so an unstable assignment makes the
    detectors oscillate in the middle of the map.
    """
    enemy = SimpleNamespace(units=[object()], is_playing=True, neutral=False)
    comp = _make_comp()
    comp.world.players = [comp, enemy]
    comp.player_is_a_hostile_enemy = lambda p: p is not comp
    detector = _Unit("capteur_mobile", is_detector=True)
    comp._detector_units = [detector]
    comp.is_an_enemy = lambda o: True
    comp._world_place_for_pathfinding = lambda p: p
    comp.memory = set()
    comp._ensure_mobile_detector = lambda: True
    monkeypatch.setattr(
        type(comp), "unknown_starting_squares", property(lambda self: [])
    )
    monkeypatch.setattr(
        type(comp), "squares_to_watch", property(lambda self: [_Place("sq1")])
    )

    comp._maintain_hidden_enemy_sweep()
    first = comp._sweep_assignment_for(detector, [_Place("sq1")])
    # The same place object must keep the assignment.
    place = first
    assert comp._sweep_assignment_for(detector, [place]) is place


def test_ensure_mobile_detector_orders_a_detector():
    """With no detector, the AI must ask its factory for one."""
    enemy = SimpleNamespace(units=[object()], is_playing=True, neutral=False)
    comp = _make_comp()
    comp.world.players = [comp, enemy]
    comp.player_is_a_hostile_enemy = lambda p: p is not comp
    comp._detector_units = []
    factory = _Unit("usine_robotique")
    comp.units = [factory]
    comp.nb = lambda name: 1 if name == "usine_robotique" else 0
    comp._mobile_detector_candidates_cache = [
        ("capteur_mobile", ("usine_robotique",)),
    ]
    comp.gather = lambda cost, pop: True
    comp._invalidate_play_derived_counts = lambda: None

    from soundrts import worldplayercomputer as wpc

    original = wpc.find_train_host
    original_unit_class = wpc.rules.unit_class

    def _fake_find_train_host(ai, makers, train_name):
        if train_name == "capteur_mobile":
            return factory
        return original(ai, makers, train_name)

    class _FakeCls:
        cost = (8, 0)
        population_cost = 0

    def _fake_unit_class(name):
        if name == "capteur_mobile":
            return _FakeCls
        return original_unit_class(name)

    wpc.find_train_host = _fake_find_train_host
    wpc.rules.unit_class = _fake_unit_class
    try:
        assert comp._ensure_mobile_detector() is True
    finally:
        wpc.find_train_host = original
        wpc.rules.unit_class = original_unit_class
    assert factory.orders
    assert factory.orders[0].keyword == "train"


def test_sweep_stops_when_enemy_becomes_visible():
    enemy = SimpleNamespace(units=[object()], is_playing=True, neutral=False)
    comp = _make_comp()
    comp.world.players = [comp, enemy]
    comp.player_is_a_hostile_enemy = lambda p: p is not comp
    comp.is_an_enemy = lambda o: True
    comp._detector_units = [_Unit("capteur_mobile", is_detector=True)]
    comp._hidden_enemy_sweep_active = True
    comp.perception = {_Building()}
    assert comp._maintain_hidden_enemy_sweep() is False
    assert comp._sweeping_for_hidden_enemy() is False


def test_play_body_calls_the_sweep():
    """The sweep must be wired into the AI turn."""
    from pathlib import Path

    src = Path("soundrts/worldplayercomputer.py").read_text(encoding="utf-8")
    body = src.split("def _play_body(self):", 1)[1].split("\n    def ", 1)[0]
    assert "_maintain_hidden_enemy_sweep()" in body
    # The sweep must run before _send_explorer, otherwise the detectors get
    # recalled home right after being sent out.
    assert body.find("_maintain_hidden_enemy_sweep()") < body.find("_send_explorer()")


def test_sweep_detectors_are_not_recalled_by_explorer():
    """A sweeping detector must not be pulled home by the scout recall."""
    from pathlib import Path

    src = Path("soundrts/worldplayercomputer.py").read_text(encoding="utf-8")
    block = src.split("def _send_explorer(self):", 1)[1].split("\n    def ", 1)[0]
    assert "sweep_units" in block
    assert "u not in sweep_units" in block


# ---------------------------------------------------------------------------
# 暴雪等价机制：句柄记忆 + 永久"可疑基地位置"表
# ---------------------------------------------------------------------------


class _HiddenBuilding:
    """An invisible enemy building (crazyMod's ``couveuse``)."""

    def __init__(self, name, place, bid, is_a=()):
        self.type_name = name
        self.is_a_building = True
        self.is_invisible = True
        self.id = bid
        self.place = place
        self.hp = 100
        # The ``is_a`` blood line: crazyMod's Zerg upgrades its hatchery
        # ``couveuse → pouponniere → laboratorio_larvaire``, and each
        # upgraded form has the previous one in its ``expanded_is_a``.
        self.expanded_is_a = set(is_a)


def _make_enemy_player(building):
    enemy = SimpleNamespace(units=[building], is_playing=True, neutral=False)
    return enemy


def test_hidden_building_notes_are_keyed_per_building_not_per_square():
    """Two invisible buildings on the SAME square must be tracked separately.

    crazyMod's Zerg base can hold ``couveuse`` *and* ``termitiere`` on the
    same square.  Keying the note by the square alone made the second one
    overwrite the first, so the AI only ever attacked the last building it
    detected and the rest of the hidden base survived forever.
    """
    comp = _make_comp()
    place = _Place("sq2")
    hatchery = _HiddenBuilding("couveuse", place, "b1")
    termite = _HiddenBuilding("termitiere", place, "b2")
    enemy = _make_enemy_player(hatchery)
    enemy.units.append(termite)
    comp.world.players = [comp, enemy]
    comp.player_is_a_hostile_enemy = lambda p: p is not comp
    comp.is_an_enemy = lambda o: True
    comp.detected_units = {hatchery, termite}

    comp._remember_detected_hidden_buildings()

    alive = comp._hidden_building_notes_alive()
    assert len(alive) == 2
    assert {b.type_name for b in alive} == {"couveuse", "termitiere"}


def test_hidden_building_note_survives_when_a_sibling_is_destroyed():
    """Destroying one hidden building must not drop the other's note."""
    comp = _make_comp()
    place = _Place("sq2")
    hatchery = _HiddenBuilding("couveuse", place, "b1")
    termite = _HiddenBuilding("termitiere", place, "b2")
    enemy = _make_enemy_player(hatchery)
    enemy.units.append(termite)
    comp.world.players = [comp, enemy]
    comp.player_is_a_hostile_enemy = lambda p: p is not comp
    comp.is_an_enemy = lambda o: True
    comp.detected_units = {hatchery, termite}

    comp._remember_detected_hidden_buildings()

    # The hatchery dies.
    enemy.units.remove(hatchery)
    comp.detected_units = set()

    alive = comp._hidden_building_notes_alive()
    assert [b.type_name for b in alive] == ["termitiere"]


def test_suspect_square_is_remembered_after_the_building_is_destroyed():
    """暴雪等价机制：AI 有一张永久的"可疑基地位置"表。

    The Zerg rebuilds its invisible hatchery on the very same square.  If the
    AI forgets the square as soon as the first building dies, the rebuilt
    invisible base can never be found again — the match deadlocks.
    """
    comp = _make_comp()
    place = _Place("sq2")
    hatchery = _HiddenBuilding("couveuse", place, "b1")
    enemy = _make_enemy_player(hatchery)
    comp.world.players = [comp, enemy]
    comp.player_is_a_hostile_enemy = lambda p: p is not comp
    comp.is_an_enemy = lambda o: True
    comp.detected_units = {hatchery}

    comp._remember_detected_hidden_buildings()
    assert [p.id for p in comp._hidden_base_suspect_places()] == ["sq2"]

    # The hatchery dies: the *note* is dropped, but the *suspect square*
    # must remain, because the enemy rebuilds there.
    enemy.units.remove(hatchery)
    comp.detected_units = set()
    assert comp._hidden_building_notes_alive() == []
    assert [p.id for p in comp._hidden_base_suspect_places()] == ["sq2"]


def test_sweep_continues_while_a_suspect_square_exists():
    """A visible enemy building must not stop the sweep when the AI still
    suspects an invisible base on another square."""
    enemy = SimpleNamespace(units=[object()], is_playing=True, neutral=False)
    comp = _make_comp()
    comp.world.players = [comp, enemy]
    comp.player_is_a_hostile_enemy = lambda p: p is not comp
    comp.is_an_enemy = lambda o: True
    comp._detector_units = [_Unit("capteur_mobile", is_detector=True)]
    comp.perception = {_Building()}
    assert comp._hidden_enemy_needs_sweep() is False

    # ...but once a square is known to have held an invisible building, the
    # detector must keep watching it.
    comp._hidden_base_suspects = {id(_Place("sq2")): (_Place("sq2"), 0, "couveuse")}
    assert comp._hidden_enemy_needs_sweep() is True


def test_detector_prerequisites_are_built_before_training():
    """暴雪等价机制：AI 会先补齐前置科技/建筑，而不是静默放弃。

    crazyMod's ``capteur_mobile`` requires ``modulateur_de_signal``, which
    the robot build script never constructs.  ``TrainOrder.is_allowed``
    rejects the order when the requirement is unmet, so every attempt to
    train a detector was a silent no-op and the AI ended up with zero
    detectors.
    """
    comp = _make_comp()
    comp.units = []
    comp.has = lambda name: name == "usine_robotique"
    comp.has_all = lambda reqs: "modulateur_de_signal" not in reqs
    comp.future_nb = lambda names: 0
    built = []
    comp._get = lambda nb, name: built.append(name) or True

    class _FakeCls:
        requirements = ("modulateur_de_signal",)

    assert comp._ensure_detector_prerequisites(_FakeCls) is False
    assert built == ["modulateur_de_signal"]


# ---------------------------------------------------------------------------
# Regression tests for the crazyMod ``z5`` deadlock (seed 42)
# ---------------------------------------------------------------------------
#
# Measured facts (see _tools/probe_crazy_real.py and the report):
#
#   * The neutral ``technique`` army at sq ``1,2`` has 120 units including
#     20 ``catapults`` that deal 14000 damage per shot.
#   * The robot's ``tireur_magnetique`` / ``capteur_mobile`` have
#     ``hp_max`` 8~10 — one catapult shot kills them.
#   * The ground route from the robot base (sq ``2,0``) to the Zerg base
#     (sq ``0,0``) crosses sq ``1,1`` and ``1,2``.
#
# Four separate fixes came out of that diagnosis:
#
#   1. the strike group must be strong enough before it is committed;
#   2. the AI must not spend its last gold on pure-defense towers;
#   3. detectors must not walk into enemy fire (they were dying in
#      batches: 54 built, all dead);
#   4. the detector's *route* must be safe, not just its destination.


class _TestSoldier(Soldier):
    """A ``Soldier`` with settable combat attributes (the real ones are
    read-only properties computed from the unit's stats).

    The AI filters its strike units with ``isinstance(u, Soldier)``, so the
    test double has to be a real ``Soldier`` subclass — but ``menace`` and
    ``is_inside`` are read-only properties, so they are overridden here as
    plain class attributes.
    """

    menace = 100
    is_inside = False
    is_a_building = False
    speed = 1.0
    mdg = 1
    rdg = 0
    airground_type = "ground"
    hp = 10
    hp_max = 10
    type_name = "tireur_magnetique"
    id = "u1"
    orders = ()
    place = None

    def __init__(self, name, menace=100, airground="ground", speed=1.0):
        self.type_name = name
        self.id = name
        self.menace = menace
        self.airground_type = airground
        self.speed = speed


def _make_soldier(name, menace=100, airground="ground", speed=1.0):
    """A real ``Soldier`` instance (the AI filters on ``isinstance``)."""
    return _TestSoldier(name, menace=menace, airground=airground, speed=speed)


class _FakeSquare:
    """A square that can carry an id and a name."""

    def __init__(self, sid, name=None):
        self.id = sid
        self.name = name or str(sid)
        self.x = 0
        self.y = 0

    def shortest_path_distance_to(self, dest, player=None, plane="ground",
                                 avoid=False):
        return 1

    def __repr__(self):
        return f"<Square {self.name}>"


def test_strike_group_of_one_unit_is_not_committed():
    """A single unit is not a strike group — it would just die."""
    comp = _make_comp()
    target = _FakeSquare(2, "0,0")
    building = _HiddenBuilding("couveuse", target, "b1")
    comp._hidden_building_notes_alive = lambda: [building]
    comp._unit_path = lambda unit, dest, places=False, avoid=False: [target]
    comp._enemy_menace = {target: 100000}

    one = [_make_soldier("tireur_magnetique", menace=1584)]
    assert comp._hidden_enemy_strike_group_ready(one, [building]) is False


def test_strike_group_is_committed_when_it_outmatches_the_route():
    """暴雪等价机制：成建制的编队才被投入攻击。"""
    comp = _make_comp()
    target = _FakeSquare(2, "0,0")
    building = _HiddenBuilding("couveuse", target, "b1")
    comp._hidden_building_notes_alive = lambda: [building]
    comp._unit_path = lambda unit, dest, places=False, avoid=False: [target]
    comp._enemy_menace = {target: 5000}

    group = [_make_soldier("canon_magnetique", menace=3000) for _ in range(2)]
    assert comp._hidden_enemy_strike_group_ready(group, [building]) is True


def test_strike_group_is_committed_when_the_route_is_clear():
    """An air route that bypasses the enemy army has no threat to match."""
    comp = _make_comp()
    target = _FakeSquare(2, "0,0")
    building = _HiddenBuilding("couveuse", target, "b1")
    comp._hidden_building_notes_alive = lambda: [building]
    comp._unit_path = lambda unit, dest, places=False, avoid=False: [target]
    comp._enemy_menace = {}

    group = [_make_soldier("vaisseau_laser", menace=100, airground="air")]
    assert comp._hidden_enemy_strike_group_ready(group, [building]) is True


def test_pure_defense_building_is_detected_by_shape():
    """``tour_laser`` trains nothing and researches nothing → pure defense."""
    comp = _make_comp()
    names = getattr(rules, "classnames", None)
    if not callable(names):
        pytest.skip("rules not loaded")
    found = False
    for name in names():
        cls = rules.unit_class(name)
        if cls is None:
            continue
        if rules.class_rules_attr(cls, "can_train", ()):
            continue
        if rules.class_rules_attr(cls, "can_research", ()):
            continue
        if rules.class_rules_attr(cls, "is_a_building", False):
            found = True
            break
    assert found, "the ruleset must contain at least one pure-defense building"


def test_defense_building_is_deferred_while_the_army_is_small():
    """资源不足以训练部队时，不要把钱花在防御塔上。"""
    comp = _make_comp()
    comp._hidden_strike_force_min_units = 4
    comp._is_pure_defense_building_type = lambda name: name == "tour_laser"
    comp._owned_trainable_type_names = lambda: ("tireur_magnetique",)
    comp.units = [_make_soldier("tireur_magnetique")]

    assert comp._defense_building_deferred_for_need("tour_laser") is True
    # A combat unit is never deferred.
    assert comp._defense_building_deferred_for_need("tireur_magnetique") is False


def test_defense_building_is_built_once_the_army_exists():
    """暴雪等价机制：主力部队成型后，防御塔照常建造。"""
    comp = _make_comp()
    comp._hidden_strike_force_min_units = 4
    comp._is_pure_defense_building_type = lambda name: name == "tour_laser"
    comp._owned_trainable_type_names = lambda: ("tireur_magnetique",)
    comp.units = [_make_soldier("tireur_magnetique") for _ in range(4)]

    assert comp._defense_building_deferred_for_need("tour_laser") is False


def test_defense_building_is_not_deferred_without_a_producer():
    """No producer → building the tower is the only option; do not block it."""
    comp = _make_comp()
    comp._hidden_strike_force_min_units = 4
    comp._is_pure_defense_building_type = lambda name: name == "tour_laser"
    comp._owned_trainable_type_names = lambda: ()
    comp.units = []

    assert comp._defense_building_deferred_for_need("tour_laser") is False


def test_sweep_drops_targets_under_enemy_fire():
    """探测器不进敌军的火力范围。"""
    comp = _make_comp()
    dangerous = _FakeSquare(7, "1,2")
    safe = _FakeSquare(2, "0,0")
    comp._enemy_menace = {dangerous: 311400}
    comp.square_is_dangerous = lambda p: p in comp._enemy_menace

    kept = comp._filter_sweep_targets_for_survival([dangerous, safe])
    assert safe in kept
    assert dangerous not in kept


def test_sweep_keeps_targets_when_everything_is_dangerous():
    """宁可损失探测器，也不能永远找不到隐形基地（死锁）。"""
    comp = _make_comp()
    only = _FakeSquare(7, "1,2")
    comp._enemy_menace = {only: 311400}
    comp.square_is_dangerous = lambda p: p in comp._enemy_menace

    assert comp._filter_sweep_targets_for_survival([only]) == [only]


def test_detector_route_is_rejected_when_it_crosses_enemy_fire():
    """探测器的**路径**也不能穿过敌军的火力范围。

    The 6 detectors of the crazyMod run died at sq ``1,1`` (catapult
    range) while walking to the enemy base at sq ``0,0`` — the
    destination was safe, the *route* was not.
    """
    comp = _make_comp()
    danger = _FakeSquare(6, "1,1")
    goal = _FakeSquare(2, "0,0")
    comp._enemy_menace = {danger: 5000}
    comp.square_is_dangerous = lambda p: p in comp._enemy_menace
    comp._unit_path = lambda unit, dest, places=False, avoid=False: [danger, goal]

    detector = _make_soldier("capteur_mobile")
    assert comp._detector_route_is_safe(detector, goal) is False


def test_detector_route_is_accepted_when_it_is_clear():
    comp = _make_comp()
    goal = _FakeSquare(2, "0,0")
    comp._enemy_menace = {}
    comp.square_is_dangerous = lambda p: p in comp._enemy_menace
    comp._unit_path = lambda unit, dest, places=False, avoid=False: [goal]

    detector = _make_soldier("capteur_mobile")
    assert comp._detector_route_is_safe(detector, goal) is True


# ---------------------------------------------------------------------------
# Regression tests for the crazyMod ``z5`` deadlock (seed 3)
# ---------------------------------------------------------------------------
#
# Measured facts:
#
#   * The invisible hatchery (``couveuse``) stands on the enemy start square
#     ``0,0``.  The only *ground* route from the robot base (``2,0``) to
#     ``0,0`` crosses sq ``1,2`` — the neutral army's square with 20
#     catapults.  ``shortest_path_to(..., avoid=True)`` returns an EMPTY
#     path: there is no safe ground route at all.
#   * The *air* route (``2,0`` → ``1,0`` → ``0,0``) is completely clear.
#   * ``drone`` is an air detector built by ``usine_robotique`` (which the
#     robot AI already owns), with ``is_a_detector 1``.
#   * ``priest`` (the robot's starting unit) also carries ``is_a_detector
#     1``, but it is a slow ground fighter: it cannot reach ``0,0``.
#
# Before the fix the AI treated the priest as its scout squad, never built
# a real detector, and the invisible base survived forever.


def test_hidden_enemy_base_squares_exclude_the_own_start_square():
    """AI 不会把自己的出生点当成"敌方基地"。"""
    comp = _make_comp()
    own = _FakeSquare(8, "2,0")
    enemy_base = _FakeSquare(2, "0,0")
    comp.world.starting_squares = ["0,0", "2,0"]
    comp.world.grid = {"0,0": enemy_base, "2,0": own}
    comp.number = 2
    comp._default_start_place = lambda: own
    comp._hidden_building_notes_alive = lambda: []
    comp._hidden_base_suspect_places = lambda: []

    bases = comp._hidden_enemy_base_squares()
    assert enemy_base in bases
    assert own not in bases


def test_detector_that_cannot_reach_the_base_is_not_a_scout():
    """走不到隐形基地的探测器不算侦察兵。"""
    comp = _make_comp()
    base = _FakeSquare(2, "0,0")
    danger = _FakeSquare(6, "1,1")
    comp._enemy_menace = {danger: 5000}
    comp.square_is_dangerous = lambda p: p in comp._enemy_menace
    comp._unit_path = lambda unit, dest, places=False, avoid=False: [danger, base]

    ground = _make_soldier("capteur_mobile")
    assert comp._detector_reaches_base(ground, [base]) is False


def test_air_detector_reaching_the_base_is_a_scout():
    """空中探测器能绕过地面火力圈。"""
    comp = _make_comp()
    base = _FakeSquare(2, "0,0")
    comp._enemy_menace = {}
    comp.square_is_dangerous = lambda p: p in comp._enemy_menace
    comp._unit_path = lambda unit, dest, places=False, avoid=False: [base]

    air = _make_soldier("drone", airground="air")
    assert comp._detector_reaches_base(air, [base]) is True


def test_ensure_mobile_detector_ignores_a_generic_detector_that_cannot_reach():
    """``priest`` 带探测器标签但到不了隐形基地 —— AI 必须再造一个。"""
    comp = _make_comp()
    base = _FakeSquare(2, "0,0")
    danger = _FakeSquare(6, "1,1")
    comp._enemy_menace = {danger: 5000}
    comp.square_is_dangerous = lambda p: p in comp._enemy_menace
    comp._unit_path = lambda unit, dest, places=False, avoid=False: [danger, base]
    comp._hidden_building_notes_alive = lambda: []
    comp._hidden_base_suspect_places = lambda: []
    comp.world.starting_squares = ["0,0"]
    comp.world.grid = {"0,0": base}
    comp.number = 2
    comp._default_start_place = lambda: _FakeSquare(8, "2,0")

    priest = _make_soldier("priest")
    comp._detector_units = [priest]
    assert comp._dedicated_detector_units() == []

    # The squad is not satisfied by the priest.
    comp._mobile_detector_candidates_ordered = lambda: []
    assert comp._ensure_detector_squad() is False


def test_ensure_mobile_detector_keeps_a_reachable_detector():
    """走得到的探测器就够用，不必再造。"""
    comp = _make_comp()
    base = _FakeSquare(2, "0,0")
    comp._enemy_menace = {}
    comp.square_is_dangerous = lambda p: p in comp._enemy_menace
    comp._unit_path = lambda unit, dest, places=False, avoid=False: [base]
    comp._hidden_building_notes_alive = lambda: []
    comp._hidden_base_suspect_places = lambda: []
    comp.world.starting_squares = ["0,0"]
    comp.world.grid = {"0,0": base}
    comp.number = 2
    comp._default_start_place = lambda: _FakeSquare(8, "2,0")

    drone = _make_soldier("drone", airground="air")
    comp._detector_units = [drone]
    assert comp._dedicated_detector_units() == [drone]
    assert comp._ensure_mobile_detector() is True


def test_sweep_assignment_prefers_a_reachable_target():
    """分配目标时要挑这个探测器**走得到**的那一格。

    地面探测器到不了 ``0,0``（唯一通路穿过攻城炮阵地），如果把
    ``0,0`` 分给它，隐形基地就永远不会被发现。
    """
    comp = _make_comp()
    unreachable = _FakeSquare(2, "0,0")
    reachable = _FakeSquare(5, "2,2")
    danger = _FakeSquare(6, "1,1")
    comp._enemy_menace = {danger: 5000}
    comp.square_is_dangerous = lambda p: p in comp._enemy_menace
    comp._unit_path = lambda unit, dest, places=False, avoid=False: (
        [danger, unreachable] if dest is unreachable else [reachable]
    )

    ground = _make_soldier("capteur_mobile")
    target = comp._sweep_assignment_for(ground, [unreachable, reachable])
    assert target is reachable


def test_sweep_assignment_keeps_the_previous_target():
    """分配必须稳定，否则探测器会在地图上来回振荡。"""
    comp = _make_comp()
    first = _FakeSquare(5, "2,2")
    other = _FakeSquare(2, "0,0")
    comp._enemy_menace = {}
    comp.square_is_dangerous = lambda p: p in comp._enemy_menace
    comp._unit_path = lambda unit, dest, places=False, avoid=False: [dest]

    ground = _make_soldier("capteur_mobile")
    assert comp._sweep_assignment_for(ground, [first, other]) is first
    assert comp._sweep_assignment_for(ground, [first, other]) is first


# ---------------------------------------------------------------------------
# Regression tests for the crazyMod ``z5`` deadlock (seed 5, nondeterministic)
# ---------------------------------------------------------------------------
#
# Measured facts (``_tools/probe_crazy_fail.py``, 30 min virtual time):
#
#   * The Zerg upgrades ``couveuse`` → ``pouponniere``.  The engine's
#     ``UpgradeToOrder.complete`` **deletes the old building and creates a
#     new object with a new handle** — so the AI's "hidden building" note,
#     which is keyed by the building handle, dies with the old object.
#   * The AI's *suspect square* table survives (it is keyed by the square),
#     so the AI knows an invisible base stands at ``0,0`` / ``0,1`` — but
#     the notes list is empty, hence ``_hidden_enemy_attack_targets()`` is
#     empty, hence the strike group is empty and the ``pouponniere`` sits
#     there at full HP (100000) until the timeout.
#   * To recover the new handle the AI needs the detector to **re-detect**
#     the building.  But the regular attack machinery called
#     ``_send_units`` every tick, which called ``cancel_all_orders()`` on
#     the detector and pulled it away from its "go <suspect square>" order.
#     The detector oscillated between ``0,0`` / ``0,1`` / ``2,1`` and never
#     arrived.
#
# Two fixes came out of that:
#
#   1. a note must **follow the upgrade** (same square + same ``is_a``
#      blood line) instead of dying with the old handle;
#   2. a detector that is **on a sweep / park mission** must not have its
#      order cancelled by the ordinary "move to that square" machinery.


def test_hidden_building_note_follows_an_upgrade_to_a_new_handle():
    """暴雪等价机制：升级不改变 AI 的记忆。

    ``couveuse`` → ``pouponniere`` is an upgrade: the engine deletes the old
    building and creates a new object with a new handle.  The AI's note must
    be re-bound to the new building, otherwise the hidden base becomes
    untouchable the moment the enemy upgrades it.
    """
    comp = _make_comp()
    place = _Place("sq2")
    hatchery = _HiddenBuilding("couveuse", place, "b1")
    enemy = _make_enemy_player(hatchery)
    comp.world.players = [comp, enemy]
    comp.player_is_a_hostile_enemy = lambda p: p is not comp
    comp.is_an_enemy = lambda o: True
    comp.detected_units = {hatchery}

    comp._remember_detected_hidden_buildings()
    assert [b.type_name for b in comp._hidden_building_notes_alive()] == [
        "couveuse"
    ]

    # The upgrade: the old building is gone, a new one takes its place.
    enemy.units.remove(hatchery)
    upgraded = _HiddenBuilding("pouponniere", place, "b2", is_a=("couveuse",))
    enemy.units.append(upgraded)
    comp.detected_units = set()

    alive = comp._hidden_building_notes_alive()
    assert [b.type_name for b in alive] == ["pouponniere"]
    # The note now points at the *new* handle.
    assert alive[0] is upgraded


def test_hidden_building_note_is_dropped_when_the_square_is_emptied():
    """A rebuilt base is re-detected, but a genuinely empty square drops out."""
    comp = _make_comp()
    place = _Place("sq2")
    hatchery = _HiddenBuilding("couveuse", place, "b1")
    enemy = _make_enemy_player(hatchery)
    comp.world.players = [comp, enemy]
    comp.player_is_a_hostile_enemy = lambda p: p is not comp
    comp.is_an_enemy = lambda o: True
    comp.detected_units = {hatchery}

    comp._remember_detected_hidden_buildings()
    enemy.units.remove(hatchery)
    comp.detected_units = set()

    assert comp._hidden_building_notes_alive() == []


def test_hidden_building_note_does_not_jump_to_an_unrelated_building():
    """Only a building of the same blood line may inherit the note."""
    comp = _make_comp()
    place = _Place("sq2")
    hatchery = _HiddenBuilding("couveuse", place, "b1")
    enemy = _make_enemy_player(hatchery)
    comp.world.players = [comp, enemy]
    comp.player_is_a_hostile_enemy = lambda p: p is not comp
    comp.is_an_enemy = lambda o: True
    comp.detected_units = {hatchery}

    comp._remember_detected_hidden_buildings()
    enemy.units.remove(hatchery)
    # Something completely different now stands on the square.
    other = _HiddenBuilding("tour_radar", place, "b9")
    other.is_invisible = False
    enemy.units.append(other)
    comp.detected_units = set()

    assert comp._hidden_building_notes_alive() == []


def test_a_sweeping_detector_keeps_its_sweep_order():
    """普通"移动到格子"指令不能打断正在执行扫荡任务的探测器。

    暴雪等价机制：被指派了侦察任务的单位不会被普通移动指令打断。
    """
    comp = _make_comp()
    suspect = _FakeSquare(2, "0,0")
    detector = _make_soldier("drone", airground="air")
    detector.is_a_detector = True
    detector.orders = [SimpleNamespace(keyword="go", target=suspect)]
    comp._detector_units = [detector]
    comp._hidden_enemy_sweep_targets = lambda: [suspect]

    assert comp._is_sweeping_detector(detector) is True


def test_a_detector_without_a_mission_can_be_moved():
    """刚造出来、还没派任务的探测器仍然可以被普通指令调走。"""
    comp = _make_comp()
    detector = _make_soldier("drone", airground="air")
    detector.is_a_detector = True
    detector.orders = []
    comp._detector_units = [detector]
    comp._hidden_enemy_sweep_targets = lambda: [_FakeSquare(2, "0,0")]

    assert comp._is_sweeping_detector(detector) is False


def test_a_non_detector_is_never_treated_as_sweeping():
    comp = _make_comp()
    soldier = _make_soldier("tireur_magnetique")
    soldier.orders = [SimpleNamespace(keyword="go", target=_FakeSquare(2, "0,0"))]
    comp._detector_units = []
    comp._hidden_enemy_sweep_targets = lambda: [_FakeSquare(2, "0,0")]

    assert comp._is_sweeping_detector(soldier) is False


def test_send_units_does_not_cancel_a_sweeping_detector():
    """``_send_units`` 必须放过正在扫荡的探测器。

    这就是 seed=5 偶发失败（30 分钟超时、pouponniere 满血存活）的直接
    原因：普通进攻指令每 tick 都把探测器从 "go <可疑格>" 上拉走，
    探测器永远到不了可疑格，也就永远无法重新侦测升级后的隐形建筑。
    """
    comp = _make_comp()
    suspect = _FakeSquare(2, "0,0")
    elsewhere = _FakeSquare(8, "2,0")
    detector = _make_soldier("drone", airground="air")
    detector.is_a_detector = True
    detector.orders = [SimpleNamespace(keyword="go", target=suspect)]
    detector.place = elsewhere
    comp._detector_units = [detector]
    comp._hidden_enemy_sweep_targets = lambda: [suspect]
    comp._world_place_for_pathfinding = lambda p: p
    comp._has_handle_bound_attack = lambda u: False
    comp._teleportation_users = []
    comp._cataclysm_users = []
    comp._send_unit_to_place = lambda u, place, teleport, enemies: None

    comp._send_units([detector], elsewhere)

    # The detector kept its sweep order.
    assert detector.orders[0].keyword == "go"
    assert detector.orders[0].target is suspect

