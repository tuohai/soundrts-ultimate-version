"""Conservative attack split: second front only when leftover still beats ratio."""
from __future__ import annotations

from types import SimpleNamespace

from soundrts.worldplayercomputer import Computer


def _fighter(uid, menace=10, place=None):
    return SimpleNamespace(
        id=uid,
        menace=menace,
        speed=1,
        place=place,
        orders=[],
        time_limit=None,
    )


def _attack_computer(menace_by_id, fighters, ratio=100, monkeypatch=None):
    c = Computer.__new__(Computer)
    c.world = SimpleNamespace(population_limit=200)
    c.used_population = 0
    c._attack_ratio = ratio
    c.enemy_menace = lambda p: menace_by_id[id(p)]
    c._attack_place_sort_key = lambda p, _units: (getattr(p, "id", 0),)
    c._units_should_attack = lambda _units, _place: True
    c._cataclysm_users = []
    c._friendly_presence = lambda _p: True
    c.perception = []
    c.memory = []
    sent = []
    c._send_units = lambda units, place: sent.append((list(units), place))
    object.__setattr__(c, "_fighters_for_test", fighters)
    monkeypatch.setattr(
        Computer,
        "_idle_fighters",
        property(lambda self: getattr(self, "_fighters_for_test", [])),
    )
    return c, sent


def test_eventually_attack_splits_two_coverable_fronts(monkeypatch):
    a = SimpleNamespace(id=1)
    b = SimpleNamespace(id=2)
    c, sent = _attack_computer(
        {id(a): 15, id(b): 15},
        [_fighter(i) for i in range(1, 5)],
        monkeypatch=monkeypatch,
    )
    c._eventually_attack([b, a])
    assert len(sent) == 2
    assert sent[0][1] is a
    assert [u.id for u in sent[0][0]] == [1, 2]
    assert sent[1][1] is b
    assert [u.id for u in sent[1][0]] == [3, 4]


def test_eventually_attack_peels_home_guard_before_raid(monkeypatch):
    home = SimpleNamespace(id=0)
    raid = SimpleNamespace(id=1)
    c, sent = _attack_computer(
        {id(home): 0, id(raid): 15},
        [_fighter(i) for i in range(1, 5)],
        monkeypatch=monkeypatch,
    )
    c._home_base_places = lambda: [home]
    c._eventually_attack([raid])
    assert len(sent) == 2
    assert sent[0][1] is home
    assert [u.id for u in sent[0][0]] == [1]
    assert sent[1][1] is raid
    assert [u.id for u in sent[1][0]] == [2, 3, 4]


def test_eventually_attack_stays_home_when_cannot_hold(monkeypatch):
    home = SimpleNamespace(id=0)
    raid = SimpleNamespace(id=1)
    c, sent = _attack_computer(
        {id(home): 25, id(raid): 10},
        [_fighter(i) for i in range(1, 3)],
        monkeypatch=monkeypatch,
    )
    c._home_base_places = lambda: [home]
    c._eventually_attack([raid])
    assert len(sent) == 1
    assert sent[0][1] is home
    assert [u.id for u in sent[0][0]] == [1, 2]


def test_eventually_attack_does_not_split_raids_when_guarding(monkeypatch):
    home = SimpleNamespace(id=0)
    a = SimpleNamespace(id=1)
    b = SimpleNamespace(id=2)
    c, sent = _attack_computer(
        {id(home): 0, id(a): 15, id(b): 15},
        [_fighter(i) for i in range(1, 7)],
        monkeypatch=monkeypatch,
    )
    c._home_base_places = lambda: [home]
    c._eventually_attack([a, b])
    assert len(sent) == 2
    assert sent[0][1] is home
    assert [u.id for u in sent[0][0]] == [1]
    assert sent[1][1] is a
    assert [u.id for u in sent[1][0]] == [2, 3, 4, 5, 6]


def test_eventually_attack_keeps_stationed_guard_not_new_recruit(monkeypatch):
    home = SimpleNamespace(id=0)
    raid = SimpleNamespace(id=1)
    recruits = [_fighter(1), _fighter(2)]
    sentry = _fighter(9, place=home)
    c, sent = _attack_computer(
        {id(home): 0, id(raid): 15},
        recruits + [sentry],
        monkeypatch=monkeypatch,
    )
    c._home_base_places = lambda: [home]
    c._eventually_attack([raid])
    assert sent[0][1] is home
    assert [u.id for u in sent[0][0]] == [9]
    assert sent[1][1] is raid
    assert [u.id for u in sent[1][0]] == [1, 2]
    sent.clear()
    extra = _fighter(0)
    object.__setattr__(c, "_fighters_for_test", [extra] + recruits + [sentry])
    c._eventually_attack([raid])
    home_sent = next(units for units, p in sent if p is home)
    raid_sent = next(units for units, p in sent if p is raid)
    assert [u.id for u in home_sent] == [9]
    assert [u.id for u in raid_sent] == [0, 1, 2]


def test_eventually_attack_prefer_ids_when_sentry_not_on_square(monkeypatch):
    home = SimpleNamespace(id=0)
    raid = SimpleNamespace(id=1)
    recruits = [_fighter(1), _fighter(2)]
    sentry = _fighter(9)
    c, sent = _attack_computer(
        {id(home): 0, id(raid): 15},
        recruits + [sentry],
        monkeypatch=monkeypatch,
    )
    c._home_base_places = lambda: [home]
    c._home_guard_ids = (9,)
    c._eventually_attack([raid])
    assert sent[0][1] is home
    assert [u.id for u in sent[0][0]] == [9]
    assert sent[1][1] is raid
    assert [u.id for u in sent[1][0]] == [1, 2]


def test_eventually_attack_keeps_blob_when_second_front_is_weak(monkeypatch):
    a = SimpleNamespace(id=1)
    b = SimpleNamespace(id=2)
    c, sent = _attack_computer(
        {id(a): 15, id(b): 15},
        [_fighter(i) for i in range(1, 4)],
        monkeypatch=monkeypatch,
    )
    c._eventually_attack([a, b])
    assert len(sent) == 1
    assert sent[0][1] is a
    assert [u.id for u in sent[0][0]] == [1, 2, 3]
