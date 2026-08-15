# -*- coding: utf-8 -*-
"""AoE2 market / trade smoke tests."""
from __future__ import annotations

import inspect
from pathlib import Path


def test_commodity_market_buy_sell_tax():
    from soundrts.worldmarket import WorldCommodityMarket, TAX_DEFAULT, TAX_GUILDS

    m = WorldCommodityMarket({1: 100, 2: 100, 3: 100})
    buy = m.buy_gold_cost(2, TAX_DEFAULT)  # food
    sell = m.sell_gold_gain(2, TAX_DEFAULT)
    assert buy == 130  # 100 * 1.3
    assert sell == 70  # 100 * 0.7
    m.after_buy(2)
    assert m.base_prices[2] == 102
    buy_g = m.buy_gold_cost(2, TAX_GUILDS)
    assert buy_g == int(__import__("math").ceil(102 * 1.15))


def test_parse_and_menu_labels():
    from soundrts.worldmarket import menu_label_for_resource, parse_commodity_pairs, parse_resource_index

    assert parse_resource_index("resource2") == 1
    assert parse_resource_index("wood") == 1
    assert parse_commodity_pairs(["resource2", "100", "resource3", "80"]) == {1: 100, 2: 80}
    # Without rules loaded, menu label falls back to resourceN
    assert menu_label_for_resource(1) == "resource2"


def test_trade_reward_indices_from_unit():
    from soundrts.worldmarket import trade_reward_indices

    class U:
        is_trade_unit = 1
        trade_rewards = ("resource1", "resource2")

    assert trade_reward_indices(U()) == [0, 1]


def test_trade_gold_scales_with_distance():
    from soundrts.worldmarket import trade_gold_for_trip

    # Adjacent / same-room style distances must not mint millions of gold.
    assert trade_gold_for_trip(0) == 0
    assert trade_gold_for_trip(1) == 0
    assert trade_gold_for_trip(20) > trade_gold_for_trip(5)
    assert trade_gold_for_trip(20) <= 517


def test_count_squares_uses_hops_not_world_coords():
    from soundrts.lib.nofloat import PRECISION
    from soundrts.worldmarket import count_squares_heuristic, trade_gold_for_trip

    class _W:
        square_width = 15 * PRECISION
        nb_columns = 7
        nb_lines = 7

    class _Sq:
        def __init__(self, col, row, world):
            self.col = col
            self.row = row
            self.world = world
            self.x = col * world.square_width + world.square_width // 2
            self.y = row * world.square_width + world.square_width // 2

        def shortest_path_distance_to(self, other, player=None, plane="ground", avoid=False):
            # World-unit distance between centers (as real Square pathing does).
            return abs(self.x - other.x) + abs(self.y - other.y)

    class _U:
        def __init__(self, place):
            self.place = place

    w = _W()
    a = _U(_Sq(0, 0, w))
    b = _U(_Sq(1, 0, w))
    hops = count_squares_heuristic(a, b)
    assert 0.9 <= hops <= 1.1
    gold = trade_gold_for_trip(hops, map_edge_squares=7)
    assert gold == 0


def test_orders_registered():
    from soundrts.worldorders import ORDERS_DICT

    for k in ("market_buy", "market_sell", "tribute", "trade"):
        assert k in ORDERS_DICT


def test_upgrade_attrs():
    from soundrts.worldupgrade.base import Upgrade

    assert hasattr(Upgrade, "market_tax_guilds")
    assert hasattr(Upgrade, "tribute_fee_permille")


def test_aoe2_rules_market_block():
    text = (
        Path(__file__).resolve().parents[2] / "mods" / "aoe2" / "rules.txt"
    ).read_text(encoding="utf-8")
    for name in (
        "def market",
        "def trade_cart",
        "def caravan",
        "def guilds",
        "def coinage",
        "def banking",
        "def feitoria",
        "is_market 1",
        "is_trade_unit 1",
        "trade_hubs market",
        "trade_rewards resource1",
        "market_commodities resource2",
        "market_currency resource1",
        "market_tax_guilds 1",
        "tribute_fee_permille 200",
        "production_rates 0.7 1.0 1.6 0.3",
        "can_train trade_cart",
        "requirements market feudal_age",
        "def mongol_market",
        "market mongol_market",
    ):
        assert name in text, name


def test_aoe2_mongol_market_requires_town_center_not_mill():
    """Mongols have no mill; market is remapped to mongol_market (TC + Feudal)."""
    from types import SimpleNamespace

    from soundrts.definitions import Rules, rules as global_rules
    from soundrts.world_build_rules import resolve_buildable_type

    root = Path(__file__).resolve().parents[2]
    base = (root / "res" / "rules.txt").read_text(encoding="utf-8")
    mod = (root / "mods" / "aoe2" / "rules.txt").read_text(encoding="utf-8")
    r = Rules()
    r.load(base, mod)

    mongol = r.unit_class("mongol_market")
    assert mongol is not None
    reqs = list(getattr(mongol, "requirements", None) or [])
    assert "mill" not in reqs
    assert "town_center" in reqs
    assert "feudal_age" in reqs

    generic = r.unit_class("market")
    gen_reqs = list(getattr(generic, "requirements", None) or [])
    assert "mill" in gen_reqs  # other civs still need mill

    saved = global_rules._dict
    saved_c = getattr(global_rules, "classes", None)
    global_rules._dict = r._dict
    global_rules.classes = r.classes
    try:
        player = SimpleNamespace(faction="mongols")
        assert resolve_buildable_type(player, "market") == "mongol_market"

        # Tab 播报须用重映射后的需求，不能仍读通用 market 的磨坊
        from soundrts.clientgameorder import OrderTypeView, update_orders_list

        update_orders_list()
        villager = SimpleNamespace(
            player=player,
            can_build=("market",),
            can_train=(),
            can_research=(),
            basic_skills=(),
            orders=[],
        )
        view = OrderTypeView("build market", villager)
        assert "mill" not in view.requirements
        assert "town_center" in view.requirements
        assert "feudal_age" in view.requirements
    finally:
        global_rules._dict = saved
        if saved_c is not None:
            global_rules.classes = saved_c


def test_aoe2_market_menu_includes_train_trade_cart():
    """Feudal market must expose train trade_cart (and buy/sell) in the order menu."""
    import os
    import sys
    import warnings

    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    saved = sys.argv
    sys.argv = [saved[0] if saved else "pytest"]
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from soundrts import config
            from soundrts.clientgame.game_orders import orders as build_order_views
            from soundrts.clientgameentity import EntityView
            from soundrts.clientgameorder import get_orders_list, update_orders_list
            from soundrts.definitions import rules
            from soundrts.lib.resource import res
            from soundrts.world import World
            from soundrts.worldclient import DirectClient
            from soundrts.world_build_rules import effective_can_research, effective_can_train
            from soundrts.worldorders.production import TrainOrder
            from soundrts.worldrequirements import requirements_satisfied
    finally:
        sys.argv = saved

    old_mods = getattr(config, "mods", "")
    try:
        config.mods = "aoe2"
        res.set_mods("aoe2")
        res.load_rules_and_ai()
        update_orders_list()

        MAP = """
title 1
square_width 12
nb_columns 3
nb_lines 3
west_east_paths 1,1 2,1 1,2 2,2
south_north_paths 1,1 2,1 1,2 2,2
nb_players_min 1
nb_players_max 1
starting_squares 2,2
starting_units town_center
nb_meadows_by_square 8
"""
        world = World([], 42)
        world._parse_map(MAP)
        world._build_map()
        human = DirectClient("p1", None)
        human.faction = "britons"
        world.populate_map([human], random_starts=False)
        player = world.players[0]
        player.upgrades = list(dict.fromkeys(list(player.upgrades) + ["feudal_age"]))
        tc_place = player.units[0].place
        for key, sq in world.grid.items():
            if sq is tc_place:
                continue
            player.lang_add_units([key, "market"], notify=False)
            if any(u.type_name == "market" for u in player.units):
                break
        market = next(u for u in player.units if u.type_name == "market")
        assert "trade_cart" in market.can_train
        assert "train trade_cart" in TrainOrder.menu(market, strict=True)

        class _Iface:
            def __init__(self, player, units):
                self.player = player
                self.scouted_squares = set()
                self.dobjets = {}
                self.group = []
                self.order = None
                for u in units:
                    self.dobjets[u.id] = EntityView(self, u)

        iface = _Iface(player, player.units)
        ev = iface.dobjets[market.id]
        assert "train trade_cart" in ev.menu
        assert any(x.startswith("market_buy ") for x in ev.menu)

        # Classic/layered ``a`` builds OrderTypeView for every menu line; commodity
        # args (resource2/…) must not crash (was AttributeError on requirements).
        iface.group = [market.id]
        views = build_order_views(iface, inactive_included=True)
        keywords = [(v.cls.keyword, v.type) for v in views]
        assert ("train", "trade_cart") in keywords
        assert ("market_buy", "resource2") in keywords
    finally:
        config.mods = old_mods
        res.set_mods(old_mods or "")
        if old_mods:
            res.load_rules_and_ai()


def test_perception_world_has_commodity_init():
    src = inspect.getsource(
        __import__("soundrts.world.world_core", fromlist=["World"]).World.__init__
    )
    assert "commodity_market" in src
