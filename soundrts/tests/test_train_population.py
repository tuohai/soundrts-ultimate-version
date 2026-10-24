"""训练命令：人口不足时按剩余人口训练尽可能多的单位。"""

import types

from soundrts.worldorders.production import TrainOrder


def _make_train_order(*, requested=3, headroom=2, resources=(10000,)):
    # 训练价按"线根"结算：引擎会沿升级线找到根单位（这里的名字是
    # "footman"），取那个根单位在 rules.txt 里的 cost，而不是本桩对象上
    # 的 cost 字段。桩若与真实 rules 里的 cost 不一致，断言就会算错。
    # 所以这里用一个 rules.txt 里不存在的名字，让线根查找落空、直接使用
    # 桩自己的 cost，期望值才和 total_cost 一致。
    unit_type = types.SimpleNamespace(
        __name__="test_train_population_dummy",
        cost=resources,
        population_cost=1,
        time_cost=1000,
        airground_type="ground",
        can_use=(),
        can_use_tech=(),
        can_use_skill=(),
    )

    player = types.SimpleNamespace(
        resources=list(resources),
        used_population=10 - headroom,
        available_population=10,
        upgrades=[],
        population_cost_bonus=0,
        population_cost_percent_bonus=0.0,
        phase_population_cost_bonus=0,
        phase_population_cost_percent_bonus=0.0,
    )
    player.pay = lambda cost: None
    player.world = types.SimpleNamespace(population_limit=200)

    building = types.SimpleNamespace(
        player=player,
        can_train={unit_type.__name__: requested},
        orders=[],
        place=types.SimpleNamespace(),
        rallying_point=None,
        is_a_building=False,
        check_if_enough_resources=lambda cost, food=0: None,
        notify=lambda *args, **kwargs: None,
    )

    order = TrainOrder(building, [unit_type.__name__])
    order.type = unit_type
    return order


def test_train_order_reduces_count_to_population_headroom():
    order = _make_train_order(requested=3, headroom=2)
    order.on_queued()
    assert order.train_count == 2
    assert order.total_population_cost == 2
    assert order.total_cost == (20000,)


def test_train_order_rejects_when_no_population_headroom():
    order = _make_train_order(requested=3, headroom=0)
    order.on_queued()
    assert order.is_impossible
    assert order.train_count == 3


def test_train_order_keeps_full_count_when_enough_population():
    order = _make_train_order(requested=3, headroom=5)
    order.on_queued()
    assert order.train_count == 3
    assert order.total_population_cost == 3
