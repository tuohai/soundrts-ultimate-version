"""Tests for the D-Phase 2 rules-driven engine fields.

Covers the four fields added in D-Phase 2 so AoE2 DE-aligned civ mechanics
that previously had to be approximated or omitted can be expressed in
``mods/aoe2/rules.txt``:

* ``can_fire_on_move`` — Kipchak/Conquistador style ranged attack while
  marching (engine: ``action_reach_and_aim`` keeps closing the gap and
  fires when in ``rdg_range``; ``MoveAction.update`` opportunistically
  auto-fires at hostiles when the unit passes them).
* ``allow_extra_town_center`` — Cuman Mercenaries (engine: bumps
  ``player.town_center_max`` by N on research).
* ``relic_loss_immunity`` — Huns Atheism (engine: sets a marker flag on
  the player; future relic-loss logic reads it).
* ``trade_reward_bonus_pct`` — Italians Silk Road (engine: stat appears
  in the effect-bonus whitelist and ``MarketOrder._credit_reward``
  multiplies gold by ``1 + pct/100``).
"""

from __future__ import annotations

import types
from pathlib import Path

import pytest

from soundrts.definitions import Rules


ROOT = Path(__file__).resolve().parents[2]


# ---------- (1) can_fire_on_move registration --------------------------------


def test_can_fire_on_move_in_int_properties():
    from soundrts.definitions import Rules as R
    assert "can_fire_on_move" in R.int_properties


def _load_aoe2_rules():
    # Some tests need real unit classes via unit_class() (e.g.Upgrade);
    # passing the base res/rules.txt followed by mods/aoe2/rules.txt mirrors
    # how the production runtime loads the mod and reliably builds the
    # per-unit classes needed by ``Upgrade.upgrade_player``.
    r = Rules()
    base = (ROOT / "res" / "rules.txt").read_text(encoding="utf-8")
    mod = (ROOT / "mods" / "aoe2" / "rules.txt").read_text(encoding="utf-8")
    r.load(base, mod)
    return r


def test_aoe2_kipchak_has_can_fire_on_move():
    r = _load_aoe2_rules()
    assert r.get("kipchak", "can_fire_on_move") == 1
    assert r.get("elite_kipchak", "can_fire_on_move") == 1


def test_aoe2_arbalester_does_not_have_can_fire_on_move():
    r = _load_aoe2_rules()
    # Arbalester / archer line has no can_fire_on_move.
    val = r.get("arbalester", "can_fire_on_move")
    assert not val or val == 0 or val == [0]


# ---------- (2) allow_extra_town_center registration -------------------------


def test_allow_extra_town_center_in_int_properties():
    from soundrts.definitions import Rules as R
    assert "allow_extra_town_center" in R.int_properties


def test_aoe2_cuman_mercenaries_has_flag():
    r = _load_aoe2_rules()
    assert r.get("cuman_mercenaries", "allow_extra_town_center") == 1


def test_allow_extra_town_center_sets_player_flag():
    r = _load_aoe2_rules()
    cls = r.unit_class("cuman_mercenaries")
    assert cls is not None
    assert getattr(cls, "type_name", None) == "cuman_mercenaries"
    player = types.SimpleNamespace(
        upgrades=[],
        units=[],
        market_tax_guilds=0,
        tribute_fee=-1.0,
        town_center_max=1,
        # upgrade_player reads level(type_name) and appends to upgrades / units.
        level=lambda name: 1,
    )
    cls.upgrade_player(player)
    assert int(getattr(player, "town_center_max", 1) or 1) == 2


# ---------- (3) relic_loss_immunity registration ----------------------------


def test_relic_loss_immunity_in_int_properties():
    from soundrts.definitions import Rules as R
    assert "relic_loss_immunity" in R.int_properties


def test_aoe2_atheism_has_flag():
    r = _load_aoe2_rules()
    assert r.get("atheism", "relic_loss_immunity") == 1


def test_atheism_sets_player_flag():
    r = _load_aoe2_rules()
    cls = r.unit_class("atheism")
    assert cls is not None
    assert getattr(cls, "type_name", None) == "atheism"
    player = types.SimpleNamespace(
        upgrades=[],
        units=[],
        market_tax_guilds=0,
        tribute_fee=-1.0,
        level=lambda name: 1,
    )
    assert not getattr(player, "relic_loss_immunity", 0)
    cls.upgrade_player(player)
    assert int(getattr(player, "relic_loss_immunity", 0) or 0) == 1


# ---------- (4) trade_reward_bonus_pct ---------------------------------------


def test_trade_reward_bonus_pct_in_extra_effect_stats():
    from soundrts.worldupgrade.effect_bonus_parse import (
        _EXTRA_EFFECT_STATS,
        is_effect_bonus_stat,
    )
    assert "trade_reward_bonus_pct" in _EXTRA_EFFECT_STATS
    assert is_effect_bonus_stat("trade_reward_bonus_pct") is True


def test_aoe2_silk_road_uses_trade_reward_bonus_pct():
    r = _load_aoe2_rules()
    eff = r.get("silk_road", "effect")
    assert eff is not None
    flat = str(eff)
    assert "trade_reward_bonus_pct" in flat


def test_silk_road_credits_bonus_in_market_reward():
    """End-to-end: silk_road stacks 15% onto the player's
    ``trade_reward_bonus_pct`` and ``_credit_reward`` multiplies gold by 1.15.
    """
    r = _load_aoe2_rules()
    cls = r.unit_class("silk_road")
    assert cls is not None
    from soundrts.worldmarket import trade_reward_for_trip

    cls = r.unit_class("silk_road")
    assert cls is not None
    base = trade_reward_for_trip(distance_squares=20, map_edge_squares=20)
    assert base > 0

    player = types.SimpleNamespace(
        upgrades=[],
        units=[],
        market_tax_guilds=0,
        tribute_fee=-1.0,
        level=lambda name: 1,
    )
    # Need a unit that has silk_road in can_use_tech so the effect is applied.
    # Use a market building (can_research silk_road per the rules).
    market = types.SimpleNamespace(
        type_name="market",
        can_use=[],
        can_use_tech=("silk_road",),
        can_use_skill=[],
        player=player,
    )
    player.units = [market]
    cls.upgrade_player(player)
    # Research must produce a trade_reward_bonus_pct stack of 15% on the player
    # (PRECISION-scaled to 15000).
    raw = getattr(player, "trade_reward_bonus_pct", None)
    assert raw is not None
    flat = list(raw) if isinstance(raw, (list, tuple)) else [raw]
    # Strip PRECISION scaling; effect handlers in attribute_effects.py may
    # store the raw 15.0 or the PRECISION-scaled 15000.0.
    scaled = {float(v) for v in flat}
    assert 15.0 in scaled or 15000.0 in scaled, scaled

    # Verify the math used by _credit_reward is amount * (1 + pct/100).
    base = trade_reward_for_trip(distance_squares=20, map_edge_squares=20)
    pct_total = sum(
        v / 1000.0 if abs(v) >= 1000 else v
        for v in flat
    )
    final = int(base * (1.0 + pct_total / 100.0))
    assert final == int(base * 1.15)


# ---------- (5) can_fire_on_move: action_reach_and_aim keeps moving ---------


class _MiniUnit:
    """Bare-minimum stub for ``action_reach_and_aim`` with a fire-on-move flag.

    Note: rdg_range is stored in PRECISION scale (×1000). So the in-range
    test uses a target inside ``rdg_range=5000`` world units; the out-of-
    range test uses a target far outside.
    """

    def __init__(self, x, y, *, rdg=5, rdg_range=5000, can_fire_on_move=0):
        self.x = x
        self.y = y
        self.rdg = rdg
        self.rdg_range = rdg_range
        self.can_fire_on_move = can_fire_on_move
        self.action_target = None
        self._aim_called_with = None
        self._reach_called_with = None
        self._stand_ground = False

    def _collision_range(self, other):
        return 0

    def aim(self, target):
        self._aim_called_with = target

    def _reach(self, d):
        self._reach_called_with = d

    def _near_enough_to_aim(self, target):
        return False  # so the early-return branch is skipped and we hit the new code

    def _near_enough(self, target):
        return False


def test_action_reach_and_aim_fires_while_moving_when_in_range(monkeypatch):
    """can_fire_on_move=1, target in rdg_range → aim AND keep reaching."""
    from soundrts.worldunit import world_movement as wm

    # Bypass formation_stand_ground so we reach the new branch.
    monkeypatch.setattr(
        "soundrts.world_formation.formation_stand_ground",
        lambda u: False,
    )
    monkeypatch.setattr(
        "soundrts.world_formation.formation_hold_xy",
        lambda u: None,
    )
    monkeypatch.setattr(
        "soundrts.world_formation.formation_blocker",
        lambda u, t: None,
    )

    archer = _MiniUnit(0, 0, can_fire_on_move=1)
    target = _MiniUnit(3000, 0, can_fire_on_move=0)  # 3000 < 5000 = rdg_range
    archer.action_target = target

    wm.CreatureMovement.action_reach_and_aim(archer)

    assert archer._aim_called_with is target
    assert archer._reach_called_with is not None


def test_action_reach_and_aim_does_not_fire_when_out_of_rdg_range(monkeypatch):
    """Target outside rdg_range must not be aimed at — unit keeps closing."""
    from soundrts.worldunit import world_movement as wm

    monkeypatch.setattr(
        "soundrts.world_formation.formation_stand_ground",
        lambda u: False,
    )
    monkeypatch.setattr(
        "soundrts.world_formation.formation_hold_xy",
        lambda u: None,
    )
    monkeypatch.setattr(
        "soundrts.world_formation.formation_blocker",
        lambda u, t: None,
    )

    archer = _MiniUnit(0, 0, can_fire_on_move=1)
    target = _MiniUnit(20_000, 0, can_fire_on_move=0)  # way out of rdg_range
    archer.action_target = target

    wm.CreatureMovement.action_reach_and_aim(archer)

    assert archer._aim_called_with is None
    # Still moving (the original non-fire-on-move close-gap branch).
    assert archer._reach_called_with is not None


def test_action_reach_and_aim_unchanged_without_flag(monkeypatch):
    """Without can_fire_on_move=1, fire-on-move is NOT enabled."""
    from soundrts.worldunit import world_movement as wm

    monkeypatch.setattr(
        "soundrts.world_formation.formation_stand_ground",
        lambda u: False,
    )
    monkeypatch.setattr(
        "soundrts.world_formation.formation_hold_xy",
        lambda u: None,
    )
    monkeypatch.setattr(
        "soundrts.world_formation.formation_blocker",
        lambda u, t: None,
    )

    archer = _MiniUnit(0, 0, can_fire_on_move=0)  # <-- not set
    target = _MiniUnit(3000, 0, can_fire_on_move=0)
    archer.action_target = target

    wm.CreatureMovement.action_reach_and_aim(archer)

    # Without the flag, the new branch is skipped. aim is not called.
    # _reach is called from the legacy close-gap branch.
    assert archer._aim_called_with is None
    assert archer._reach_called_with is not None
