# -*- coding: utf-8 -*-
"""Market orders: buy/sell, tribute, route trade (rules-driven)."""
from __future__ import annotations

from ..lib.nofloat import PRECISION
from ..worldmarket import (
    commodities_for,
    count_squares_heuristic,
    ensure_world_market,
    first_allied_player,
    is_market_building,
    is_trade_hub_for,
    is_trade_unit,
    map_edge_squares,
    market_batch_size,
    market_currency_index,
    market_tax_rate,
    menu_label_for_resource,
    parse_resource_index,
    player_tribute_fee,
    trade_reward_for_trip,
    trade_reward_indices,
    tribute_batch_size,
    tribute_resource_indices,
)
from .base import BasicOrder
from .immediate import ImmediateOrder


def _title_for_resource(index: int) -> str:
    return menu_label_for_resource(index)


class _MarketTradeImmediate(ImmediateOrder):
    """Buy or sell one batch of a configured commodity at a market building."""

    nb_args = 1
    is_buy = True

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        return bool(getattr(unit, "is_a_building", False)) and is_market_building(unit)

    @classmethod
    def menu(cls, unit, strict=False):
        if not cls.is_allowed(unit):
            return []
        table = commodities_for(unit)
        if not table:
            return []
        verb = "market_buy" if cls.is_buy else "market_sell"
        return [f"{verb} {_title_for_resource(i)}" for i in sorted(table)]

    def immediate_action(self):
        commodity = parse_resource_index(self.args[0] if self.args else None)
        table = commodities_for(self.unit)
        if commodity is None or commodity not in table:
            self.unit.notify("order_impossible")
            return
        player = self.unit.player
        world = self.unit.world
        market = ensure_world_market(world, self.unit)
        market.ensure_commodity(commodity, table.get(commodity, 100))
        tax = market_tax_rate(player, self.unit)
        currency = market_currency_index(self.unit)
        batch = market_batch_size(self.unit)
        batch_internal = batch * PRECISION

        if currency == commodity:
            self.unit.notify("order_impossible")
            return

        if self.is_buy:
            need = market.buy_cost(commodity, tax) * PRECISION
            if player.resources[currency] < need:
                self.unit.notify(f"order_impossible,not_enough_resource{currency + 1}")
                return
            player.resources[currency] -= need
            player.resources[commodity] += batch_internal
            market.after_buy(commodity)
            self.unit.notify(f"market_bought,{_title_for_resource(commodity)},{batch}")
        else:
            if player.resources[commodity] < batch_internal:
                self.unit.notify(f"order_impossible,not_enough_resource{commodity + 1}")
                return
            gain = market.sell_gain(commodity, tax) * PRECISION
            player.resources[commodity] -= batch_internal
            player.resources[currency] += gain
            market.after_sell(commodity)
            self.unit.notify(f"market_sold,{_title_for_resource(commodity)},{batch}")
        self.unit.notify("order_ok")


class MarketBuyOrder(_MarketTradeImmediate):
    keyword = "market_buy"
    is_buy = True


class MarketSellOrder(_MarketTradeImmediate):
    keyword = "market_sell"
    is_buy = False


class TributeOrder(ImmediateOrder):
    """Send a batch of a configured resource to the first allied player."""

    keyword = "tribute"
    nb_args = 1

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        if not (getattr(unit, "is_a_building", False) and is_market_building(unit)):
            return False
        return first_allied_player(unit.player) is not None

    @classmethod
    def menu(cls, unit, strict=False):
        if not cls.is_allowed(unit):
            return []
        return [f"tribute {_title_for_resource(i)}" for i in tribute_resource_indices()]

    def immediate_action(self):
        idx = parse_resource_index(self.args[0] if self.args else None)
        if idx is None or idx not in tribute_resource_indices():
            self.unit.notify("order_impossible")
            return
        ally = first_allied_player(self.unit.player)
        if ally is None:
            self.unit.notify("order_impossible")
            return
        batch = tribute_batch_size()
        amount = batch * PRECISION
        if self.unit.player.resources[idx] < amount:
            self.unit.notify(f"order_impossible,not_enough_resource{idx + 1}")
            return
        fee = player_tribute_fee(self.unit.player)
        received = int(amount * (1.0 - fee))
        self.unit.player.resources[idx] -= amount
        ally.resources[idx] += max(0, received)
        self.unit.notify(f"tribute_sent,{_title_for_resource(idx)},{batch}")
        self.unit.notify("order_ok")


class TradeOrder(BasicOrder):
    """Route trade: shuttle between hubs; credit configured reward resource(s).

    Menu forms:
      - ``trade`` — single reward from ``trade_rewards`` / currency fallback
      - ``trade resource1`` — pick among multiple ``trade_rewards``
    Server args: ``[target_id]`` or ``[resource_token, target_id]``.
    """

    keyword = "trade"
    nb_args = 1

    def __init__(self, unit, args):
        args = list(args or ())
        self._reward_token = None
        if args:
            tok = str(args[0]).strip().lower()
            # Never treat a bare object id (digits) as a reward resource token.
            if not tok.isdigit():
                cand = parse_resource_index(args[0])
                allowed = trade_reward_indices(unit)
                if cand is not None and (not allowed or cand in allowed):
                    self._reward_token = args[0]
                    args = args[1:]
        super().__init__(unit, args)
        self._home = None
        self._dest = None
        self._going_to_dest = True
        self._trip_distance = 0.0
        self._reward_index = parse_resource_index(self._reward_token)

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        return is_trade_unit(unit) and bool(trade_reward_indices(unit))

    @classmethod
    def menu(cls, unit, strict=False):
        if not is_trade_unit(unit):
            return []
        rewards = trade_reward_indices(unit)
        if not rewards:
            return []
        if len(rewards) == 1:
            return [cls.keyword]
        return [f"{cls.keyword} {_title_for_resource(i)}" for i in rewards]

    def _resolve_reward_index(self):
        rewards = trade_reward_indices(self.unit)
        if not rewards:
            return None
        if self._reward_index in rewards:
            return self._reward_index
        return rewards[0]

    def on_queued(self):
        target_id = self.args[0] if self.args else None
        target = self.player.get_object_by_id(target_id) if target_id is not None else None
        if target is None or not is_trade_hub_for(self.unit, target):
            self.mark_as_impossible()
            return
        self._reward_index = self._resolve_reward_index()
        if self._reward_index is None:
            self.mark_as_impossible()
            return
        home = None
        place = getattr(self.unit, "place", None)
        if place is not None:
            for o in getattr(place, "objects", ()) or ():
                if is_trade_hub_for(self.unit, o) and getattr(o, "player", None) is self.player:
                    home = o
                    break
        if home is None:
            best = None
            best_d = 1e9
            for u in self.player.units:
                if not is_trade_hub_for(self.unit, u):
                    continue
                d = count_squares_heuristic(self.unit, u)
                if d < best_d:
                    best_d = d
                    best = u
            home = best
        if home is None or home is target:
            self.mark_as_impossible()
            return
        self._home = home
        self._dest = target
        self._going_to_dest = True
        self._trip_distance = count_squares_heuristic(home, target)
        self.target = target
        self.unit.notify("order_ok")

    def _credit_reward(self):
        idx = self._reward_index
        if idx is None:
            idx = self._resolve_reward_index()
        if idx is None:
            return
        world = self.world
        edge = map_edge_squares(world)
        amount = trade_reward_for_trip(self._trip_distance, edge)
        if amount <= 0:
            return
        self.player.resources[idx] += amount * PRECISION
        label = _title_for_resource(idx)
        self.unit.notify(f"trade_reward,{label},{amount}")
        # legacy event name (AoE2 TTS / listeners)
        self.unit.notify(f"trade_gold,{amount}")

    def _arrived_at(self, hub) -> bool:
        if hub is None:
            return False
        if self.unit._near_enough(hub):
            return True
        return getattr(self.unit, "place", None) is getattr(hub, "place", None)

    def execute(self):
        self.update_target()
        dest = self._dest if self._going_to_dest else self._home
        if dest is None or getattr(dest, "place", None) is None:
            self.mark_as_impossible()
            return
        self.target = dest
        if self._arrived_at(dest):
            if self._going_to_dest:
                self._credit_reward()
                self._going_to_dest = False
                next_hub = self._home
            else:
                self._going_to_dest = True
                next_hub = self._dest
            if next_hub is None or getattr(next_hub, "place", None) is None:
                self.mark_as_impossible()
                return
            self.target = next_hub
            self.unit.start_moving_to(next_hub)
            if self.unit.is_idle:
                self.mark_as_impossible()
            return
        if self.unit.is_idle:
            self.move_to_or_fail(self.target)
