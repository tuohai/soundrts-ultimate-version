"""单位数量上限：count_limit / global_count_limit 与训练命令 enforcement。"""

import types

from soundrts.worldorders.production import TrainOrder
from soundrts.worldplayerbase.base import Player


def _unit(type_name):
    return types.SimpleNamespace(type_name=type_name, orders=())


def _train_order(unit_type_name, train_count=1):
    unit_type = types.SimpleNamespace(
        __name__=unit_type_name,
        type_name=unit_type_name,
        cost=(100,),
        population_cost=0,
        time_cost=1000,
        airground_type="ground",
        can_use=(),
        can_use_tech=(),
        can_use_skill=(),
    )
    order = types.SimpleNamespace(
        keyword="train",
        type=unit_type,
        train_count=train_count,
    )
    return order


def test_effective_count_limit_prefers_count_limit(monkeypatch):
    footman_cls = types.SimpleNamespace(count_limit=2, global_count_limit=5, type_name="footman")

    def fake_unit_class(name):
        return footman_cls if name == "footman" else None

    monkeypatch.setattr("soundrts.worldplayerbase.base.rules.unit_class", fake_unit_class)
    assert Player.effective_count_limit("footman") == 2


def test_effective_count_limit_uses_global_count_limit(monkeypatch):
    hero_cls = types.SimpleNamespace(count_limit=0, global_count_limit=1, type_name="hero")

    def fake_unit_class(name):
        return hero_cls if name == "hero" else None

    monkeypatch.setattr("soundrts.worldplayerbase.base.rules.unit_class", fake_unit_class)
    assert Player.effective_count_limit("hero") == 1


def test_future_count_includes_train_count(monkeypatch):
    player = Player.__new__(Player)
    barracks = types.SimpleNamespace(
        type_name="barracks",
        orders=[_train_order("footman", train_count=3)],
    )
    player.units = [_unit("footman"), barracks]

    def fake_unit_class(name):
        return types.SimpleNamespace(type_name=name)

    monkeypatch.setattr("soundrts.worldplayerbase.base.rules.unit_class", fake_unit_class)
    assert player.future_count("footman") == 4


def test_check_count_limit_blocks_when_alive_unit_exists(monkeypatch):
    player = Player.__new__(Player)
    player.units = [_unit("footman")]

    footman_cls = types.SimpleNamespace(count_limit=1, global_count_limit=0, type_name="footman")

    def fake_unit_class(name):
        return footman_cls if name == "footman" else types.SimpleNamespace(type_name=name)

    monkeypatch.setattr("soundrts.worldplayerbase.base.rules.unit_class", fake_unit_class)
    assert player.check_count_limit("footman") is False


def test_check_count_limit_allows_after_unit_removed(monkeypatch):
    player = Player.__new__(Player)
    player.units = []

    footman_cls = types.SimpleNamespace(count_limit=1, global_count_limit=0, type_name="footman")

    def fake_unit_class(name):
        return footman_cls if name == "footman" else types.SimpleNamespace(type_name=name)

    monkeypatch.setattr("soundrts.worldplayerbase.base.rules.unit_class", fake_unit_class)
    assert player.check_count_limit("footman") is True


def _make_train_order(*, alive=0, limit=1, requested=1, use_global=False):
    unit_type = types.SimpleNamespace(
        __name__="footman",
        type_name="footman",
        cost=(10000,),
        population_cost=0,
        time_cost=1000,
        airground_type="ground",
        can_use=(),
        can_use_tech=(),
        can_use_skill=(),
    )
    if use_global:
        unit_type.count_limit = 0
        unit_type.global_count_limit = limit
    else:
        unit_type.count_limit = limit
        unit_type.global_count_limit = 0

    player = types.SimpleNamespace(
        resources=[100000],
        used_population=0,
        available_population=10,
        upgrades=[],
        population_cost_bonus=0,
        population_cost_percent_bonus=0.0,
        phase_population_cost_bonus=0,
        phase_population_cost_percent_bonus=0.0,
        pay=lambda cost: None,
        world=types.SimpleNamespace(population_limit=200),
    )
    player.units = [_unit("footman") for _ in range(alive)]
    player.future_count = lambda type_name, exclude_order=None: Player.future_count(
        player, type_name, exclude_order=exclude_order
    )

    building = types.SimpleNamespace(
        player=player,
        can_train={"footman": requested},
        orders=[],
        place=types.SimpleNamespace(find_free_space=lambda *args: (0, 0)),
        rallying_point=None,
        is_buildable_near_water_only=False,
        x=0,
        y=0,
        check_if_enough_resources=lambda cost, food=0: None,
        notify=lambda *args, **kwargs: None,
    )

    order = TrainOrder(building, ["footman"])
    order.type = unit_type
    building.orders = [order]
    return order


def test_train_order_rejects_when_count_limit_reached(monkeypatch):
    footman_cls = types.SimpleNamespace(count_limit=1, global_count_limit=0, type_name="footman")

    def fake_unit_class(name):
        return footman_cls if name == "footman" else None

    monkeypatch.setattr("soundrts.worldplayerbase.base.rules.unit_class", fake_unit_class)
    notifications = []
    order = _make_train_order(alive=1, limit=1)
    order.unit.notify = lambda msg: notifications.append(msg)
    order.on_queued()
    assert order.is_impossible
    assert "order_impossible,count_limit_reached" in notifications


def test_train_order_allows_when_under_count_limit(monkeypatch):
    footman_cls = types.SimpleNamespace(count_limit=1, global_count_limit=0, type_name="footman")

    def fake_unit_class(name):
        return footman_cls if name == "footman" else None

    monkeypatch.setattr("soundrts.worldplayerbase.base.rules.unit_class", fake_unit_class)
    order = _make_train_order(alive=0, limit=1)
    order.on_queued()
    assert not order.is_impossible
    assert order.train_count == 1


def test_train_order_respects_global_count_limit(monkeypatch):
    footman_cls = types.SimpleNamespace(count_limit=0, global_count_limit=1, type_name="footman")

    def fake_unit_class(name):
        return footman_cls if name == "footman" else None

    monkeypatch.setattr("soundrts.worldplayerbase.base.rules.unit_class", fake_unit_class)
    notifications = []
    order = _make_train_order(alive=1, limit=1, use_global=True)
    order.unit.notify = lambda msg: notifications.append(msg)
    order.on_queued()
    assert order.is_impossible
    assert "order_impossible,count_limit_reached" in notifications
