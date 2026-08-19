# -*- coding: utf-8 -*-
"""Generic commodity market + route-trade helpers (rules-driven).

Mods configure via ``def parameters`` and per-unit attributes — no AoE2 names
are required. AoE2 wires DE behavior through those keys.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

from .lib.nofloat import PRECISION

# Soft defaults when a mod enables markets but omits parameters.
_DEFAULT_BATCH = 100
_DEFAULT_TAX_PERILLE = 300
_DEFAULT_GUILDS_TAX_PERILLE = 150
_DEFAULT_TRIBUTE_FEE_PERILLE = 300
_DEFAULT_PRICE_MIN = 20
_DEFAULT_PRICE_MAX = 9999
_DEFAULT_PRICE_STEP = 2
_DEFAULT_TRADE_CAP = 517
_DEFAULT_TRADE_TILE_SCALE = 6.0
_DEFAULT_TRADE_SHRINK = 5.0


def _rules():
    from . import definitions

    return definitions.rules


def _as_list(val) -> list:
    if val is None:
        return []
    if isinstance(val, (list, tuple)):
        return list(val)
    return [val]


def parse_resource_index(token) -> Optional[int]:
    """``resource3`` / ``3`` / ``2`` (0-based) → index; None if unknown."""
    if token is None:
        return None
    if isinstance(token, int):
        return token if token >= 0 else None
    s = str(token).strip().lower()
    if not s:
        return None
    if s.startswith("resource") and s[8:].isdigit():
        return int(s[8:]) - 1
    if s.isdigit():
        return int(s)
    # Common aliases (optional convenience; mods may also use style titles)
    aliases = {
        "gold": 0,
        "wood": 1,
        "food": 2,
        "stone": 3,
    }
    if s in aliases:
        return aliases[s]
    try:
        return _rules().parse_resource_type(s)
    except Exception:
        return None


def resource_label(index: int) -> str:
    """Stable order-arg token for menus (``resource1`` …)."""
    return f"resource{int(index) + 1}"


def canonical_resource_name(token) -> Optional[str]:
    """Normalize ``resource1`` / ``gold`` / ``0`` → ``resourceN``; None if unknown."""
    idx = parse_resource_index(token)
    if idx is None:
        return None
    return resource_label(idx)


def resource_or_type_key(token) -> str:
    """``wood`` / ``resource2`` → ``resource2``; unknown deposit names stay as-is."""
    if token is None:
        return ""
    return canonical_resource_name(token) or str(token)


def unpack_gather_byproduct_entry(entry, default_product="resource1"):
    """Return ``(rate, product_resourceN, mode)``.

    ``mode`` is ``None`` (rate per second) or ``per_food`` (rate × food gathered).
    """
    mode = None
    if isinstance(entry, dict):
        rate = entry.get("rate", 0)
        product = entry.get("resource") or default_product
        mode = entry.get("mode")
    elif isinstance(entry, (list, tuple)) and len(entry) >= 3:
        rate, product, mode = entry[0], entry[1], entry[2]
    elif isinstance(entry, (list, tuple)) and len(entry) >= 2:
        rate, product = entry[0], entry[1]
    else:
        rate, product = entry, default_product
    try:
        rate_f = float(rate)
    except (TypeError, ValueError):
        rate_f = 0.0
    product_key = canonical_resource_name(product) or str(product or default_product)
    mode_s = str(mode).lower() if mode else None
    if mode_s not in ("per_food", "ratio"):
        mode_s = None
    return rate_f, product_key, mode_s


def menu_label_for_resource(index: int) -> str:
    """Order-arg token shown in menus (may be a style-friendly alias).

    Configure with ``market_menu_labels resource2 wood resource3 food …``.
    Tokens must be ``resourceN`` (not aliases) so pairs parse unambiguously.
    """
    raw = _param("market_menu_labels", None)
    if raw:
        items = _as_list(raw)
        i = 0
        while i < len(items):
            tok = str(items[i]).strip().lower()
            idx = None
            if tok.startswith("resource") and tok[8:].isdigit():
                idx = int(tok[8:]) - 1
            elif tok.isdigit():
                idx = int(tok)
            if idx is None:
                i += 1
                continue
            if i + 1 < len(items) and idx == int(index):
                return str(items[i + 1])
            i += 2 if i + 1 < len(items) else 1
    return resource_label(index)


def _param(name, default=None):
    try:
        v = _rules().get("parameters", name, default)
    except Exception:
        return default
    return default if v is None else v


def _param_int(name, default: int) -> int:
    v = _param(name, default)
    try:
        if isinstance(v, (list, tuple)):
            v = v[0] if v else default
        return int(v)
    except (TypeError, ValueError):
        return int(default)


def _param_float(name, default: float) -> float:
    v = _param(name, default)
    try:
        if isinstance(v, (list, tuple)):
            v = v[0] if v else default
        return float(v)
    except (TypeError, ValueError):
        return float(default)


def parse_commodity_pairs(tokens: Sequence) -> Dict[int, int]:
    """Parse ``resource2 100 resource3 100`` → ``{1: 100, 2: 100}``."""
    out: Dict[int, int] = {}
    items = list(tokens or ())
    i = 0
    while i < len(items):
        idx = parse_resource_index(items[i])
        if idx is None:
            i += 1
            continue
        price = 100
        if i + 1 < len(items):
            try:
                price = int(float(items[i + 1]))
                i += 2
            except (TypeError, ValueError):
                i += 1
        else:
            i += 1
        out[idx] = price
    return out


def market_currency_index(host=None) -> int:
    if host is not None:
        raw = getattr(host, "market_currency", None)
        if raw not in (None, (), ""):
            tok = raw[0] if isinstance(raw, (list, tuple)) else raw
            idx = parse_resource_index(tok)
            if idx is not None:
                return idx
    idx = parse_resource_index(_param("market_currency", "resource1"))
    return 0 if idx is None else idx


def market_batch_size(host=None) -> int:
    if host is not None:
        v = getattr(host, "market_batch", None)
        if v not in (None, (), ""):
            try:
                if isinstance(v, (list, tuple)):
                    v = v[0]
                n = int(v)
                if n > 0:
                    return n
            except (TypeError, ValueError):
                pass
    return max(1, _param_int("market_batch", _DEFAULT_BATCH))


def tribute_batch_size() -> int:
    return max(1, _param_int("tribute_batch", _param_int("market_batch", _DEFAULT_BATCH)))


def market_tax_rate(player, host=None) -> float:
    """Buyer/seller tax as fraction (0.30 = 30%)."""
    if player is not None and int(getattr(player, "market_tax_guilds", 0) or 0):
        pm = _param_int("market_tax_guilds_permille", _DEFAULT_GUILDS_TAX_PERILLE)
    else:
        pm = _param_int("market_tax_permille", _DEFAULT_TAX_PERILLE)
    if host is not None:
        override = getattr(host, "market_tax_permille", None)
        if override not in (None, (), "", -1):
            try:
                if isinstance(override, (list, tuple)):
                    override = override[0]
                pm = int(override)
            except (TypeError, ValueError):
                pass
    return max(0.0, float(pm) / 1000.0)


def player_tribute_fee(player) -> float:
    fee = getattr(player, "tribute_fee", None) if player is not None else None
    if fee is None:
        pm = _param_int("tribute_fee_permille", _DEFAULT_TRIBUTE_FEE_PERILLE)
        return max(0.0, float(pm) / 1000.0)
    try:
        return float(fee)
    except (TypeError, ValueError):
        return float(_DEFAULT_TRIBUTE_FEE_PERILLE) / 1000.0


def commodities_for(host=None) -> Dict[int, int]:
    """Resource index → base price (per batch, display units)."""
    if host is not None:
        raw = getattr(host, "market_commodities", None)
        if raw:
            pairs = parse_commodity_pairs(_as_list(raw))
            if pairs:
                return pairs
    raw = _param("market_commodities", None)
    if raw:
        pairs = parse_commodity_pairs(_as_list(raw))
        if pairs:
            return pairs
    return {}


def tribute_resource_indices() -> List[int]:
    raw = _param("tribute_resources", None)
    if raw:
        out = []
        for tok in _as_list(raw):
            idx = parse_resource_index(tok)
            if idx is not None and idx not in out:
                out.append(idx)
        if out:
            return out
    # Fallback: currency + all commodities from global table
    cur = market_currency_index()
    out = [cur]
    for i in commodities_for():
        if i not in out:
            out.append(i)
    return out or [0]


def trade_reward_indices(unit) -> List[int]:
    """Resources a trade unit may earn from route trade."""
    raw = getattr(unit, "trade_rewards", None) if unit is not None else None
    out = []
    for tok in _as_list(raw):
        idx = parse_resource_index(tok)
        if idx is not None and idx not in out:
            out.append(idx)
    if out:
        return out
    # Legacy: trade units without trade_rewards earn currency (usually gold)
    if unit is not None and is_trade_unit(unit):
        return [market_currency_index()]
    return []


class WorldCommodityMarket:
    """Shared buy/sell price table for one game world."""

    def __init__(self, base_prices: Optional[dict] = None):
        self.base_prices: Dict[int, int] = dict(base_prices or {})
        self.price_min = _param_int("market_price_min", _DEFAULT_PRICE_MIN)
        self.price_max = _param_int("market_price_max", _DEFAULT_PRICE_MAX)
        self.price_step = _param_int("market_price_step", _DEFAULT_PRICE_STEP)

    def ensure_commodity(self, commodity_index: int, default_price: int = 100) -> None:
        if commodity_index not in self.base_prices:
            self.base_prices[commodity_index] = int(default_price)

    def buy_cost(self, commodity_index: int, tax: float) -> int:
        base = self.base_prices.get(commodity_index)
        if base is None:
            return 0
        return max(1, int(math.ceil(base * (1.0 + float(tax)))))

    def sell_gain(self, commodity_index: int, tax: float) -> int:
        base = self.base_prices.get(commodity_index)
        if base is None:
            return 0
        return max(0, int(math.floor(base * (1.0 - float(tax)))))

    # Back-compat aliases
    def buy_gold_cost(self, commodity_index: int, tax: float) -> int:
        return self.buy_cost(commodity_index, tax)

    def sell_gold_gain(self, commodity_index: int, tax: float) -> int:
        return self.sell_gain(commodity_index, tax)

    def _clamp(self, p: int) -> int:
        return max(self.price_min, min(self.price_max, int(p)))

    def after_buy(self, commodity_index: int) -> None:
        if commodity_index in self.base_prices:
            self.base_prices[commodity_index] = self._clamp(
                self.base_prices[commodity_index] + self.price_step
            )

    def after_sell(self, commodity_index: int) -> None:
        if commodity_index in self.base_prices:
            self.base_prices[commodity_index] = self._clamp(
                self.base_prices[commodity_index] - self.price_step
            )


def ensure_world_market(world, host=None) -> WorldCommodityMarket:
    m = getattr(world, "commodity_market", None)
    if m is None:
        m = WorldCommodityMarket(commodities_for(host))
        world.commodity_market = m
    # Merge any newly defined commodities (e.g. building override)
    for idx, price in commodities_for(host).items():
        m.ensure_commodity(idx, price)
    return m


def trade_reward_for_trip(distance_squares: float, map_edge_squares: float = 20.0) -> int:
    """Distance-scaled route-trade payout (display units)."""
    d_raw = max(0.0, float(distance_squares))
    scale = _param_float("trade_tile_scale", _DEFAULT_TRADE_TILE_SCALE)
    shrink = _param_float("trade_shrink", _DEFAULT_TRADE_SHRINK)
    cap = _param_int("trade_reward_cap", _DEFAULT_TRADE_CAP)
    d = max(0.0, d_raw * scale - shrink)
    if d < 0.1:
        return 0
    edge = max(8.0, float(map_edge_squares) * scale)
    raw = 0.46 * d * (d / edge + 0.3)
    return max(0, min(cap, int(raw)))


# Back-compat name
trade_gold_for_trip = trade_reward_for_trip


def _square_width_world(place) -> float:
    world = getattr(place, "world", None)
    sw = getattr(world, "square_width", None) if world is not None else None
    try:
        sw = float(sw)
    except (TypeError, ValueError):
        sw = 0.0
    if sw <= 0:
        sw = float(12 * PRECISION)
    return sw


def count_squares_heuristic(a, b) -> float:
    """Distance between two entities in *square hops* (adjacent = ~1)."""
    pa = getattr(a, "place", None)
    pb = getattr(b, "place", None)
    if pa is None or pb is None:
        return 0.0
    if pa is pb:
        return 0.0
    try:
        ca, ra = int(pa.col), int(pa.row)
        cb, rb = int(pb.col), int(pb.row)
        if hasattr(pa, "shortest_path_distance_to"):
            d = pa.shortest_path_distance_to(pb)
            if d is not None and d < 1e8:
                sw = _square_width_world(pa)
                if sw > 0:
                    return max(0.0, float(d) / sw)
        return float(abs(ca - cb) + abs(ra - rb))
    except Exception:
        pass
    try:
        if hasattr(pa, "shortest_path_distance_to"):
            d = pa.shortest_path_distance_to(pb)
            if d is not None and d < 1e8:
                sw = _square_width_world(pa)
                if sw > 0:
                    return max(0.0, float(d) / sw)
    except Exception:
        pass
    return 5.0


def map_edge_squares(world) -> float:
    cols = float(getattr(world, "nb_columns", 0) or 0)
    rows = float(getattr(world, "nb_lines", 0) or 0)
    edge = max(cols, rows)
    if edge <= 0:
        n = len(getattr(world, "squares", ()) or ())
        edge = max(8.0, float(n) ** 0.5)
    return max(8.0, edge)


def first_allied_player(player):
    allied = getattr(player, "allied", None) or ()
    for p in allied:
        if p is player:
            continue
        if getattr(p, "neutral", False):
            continue
        if getattr(p, "has_been_defeated", False):
            continue
        return p
    vision = getattr(player, "allied_vision", None) or ()
    for p in vision:
        if p is player:
            continue
        if getattr(p, "neutral", False):
            continue
        if getattr(p, "has_been_defeated", False):
            continue
        return p
    return None


def is_market_building(obj) -> bool:
    if obj is None:
        return False
    if int(getattr(obj, "is_market", 0) or 0):
        return True
    name = getattr(obj, "type_name", None) or getattr(
        getattr(obj, "__class__", None), "__name__", ""
    )
    return name == "market"


def is_dock_building(obj) -> bool:
    if obj is None:
        return False
    if int(getattr(obj, "is_dock", 0) or 0):
        return True
    name = getattr(obj, "type_name", None) or getattr(
        getattr(obj, "__class__", None), "__name__", ""
    )
    return name == "shipyard"


def _hub_token_matches(obj, token: str) -> bool:
    tok = str(token).strip()
    if not tok:
        return False
    name = getattr(obj, "type_name", None) or ""
    if name == tok:
        return True
    if tok.startswith("is_") and int(getattr(obj, tok, 0) or 0):
        return True
    # ``market`` also matches ``is_market``
    flag = f"is_{tok}"
    if int(getattr(obj, flag, 0) or 0):
        return True
    return False


def is_trade_hub_for(unit, obj) -> bool:
    """True if ``obj`` is a valid route-trade hub for ``unit``."""
    if obj is None or unit is None:
        return False
    hubs = _as_list(getattr(unit, "trade_hubs", None))
    if hubs:
        return any(_hub_token_matches(obj, h) for h in hubs)
    # Legacy fallback when trade_hubs unset
    name = getattr(unit, "type_name", None) or ""
    if name == "trade_cog" or (
        int(getattr(unit, "is_trade_unit", 0) or 0)
        and getattr(unit, "airground_type", None) == "water"
    ):
        return is_dock_building(obj)
    if name == "trade_cart" or int(getattr(unit, "is_trade_unit", 0) or 0):
        return is_market_building(obj)
    return is_market_building(obj) or is_dock_building(obj)


def is_trade_unit(obj) -> bool:
    if obj is None:
        return False
    if int(getattr(obj, "is_trade_unit", 0) or 0):
        return True
    name = getattr(obj, "type_name", None) or ""
    return name in ("trade_cart", "trade_cog")


# Deprecated module-level constants (tests / old imports)
COMMODITY_INDICES = (1, 2, 3)
BATCH = _DEFAULT_BATCH
TAX_DEFAULT = _DEFAULT_TAX_PERILLE / 1000.0
TAX_GUILDS = _DEFAULT_GUILDS_TAX_PERILLE / 1000.0
TRIBUTE_FEE_DEFAULT = _DEFAULT_TRIBUTE_FEE_PERILLE / 1000.0


def player_market_tax(player) -> float:
    return market_tax_rate(player)
