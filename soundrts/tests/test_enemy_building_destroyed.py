"""Tests for ``lang_enemy_building_destroyed`` trigger condition.

Covers all 5 syntax variants, friendly/hostile discrimination, the
"natural count fallback" path (syntax 1 with implicit index 1), and
the fact that ``building_lost`` and ``enemy_building_destroyed`` are
fully independent: a condition on self's own building is unaffected
by the enemy trigger and vice versa.

The stubs here lean on real ``TriggersMixin`` (which the campaign
alliance-transfer test file already established as loadable in
isolation). We give the owner a ``player_is_a_hostile_enemy`` method
because ``_is_hostile_to_self`` consults that API; everything else
is self-contained.
"""
from __future__ import annotations

import types

import soundrts.worldunit  # noqa: F401  -- resolve circular imports

from soundrts.worldplayerbase.triggers import TriggersMixin


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------

class _Building:
    def __init__(self, type_name, player, *, sq_key="0,0", global_index=1,
                 local_index=1, bid=None, expanded_is_a=None):
        self.type_name = type_name
        self.player = player
        self.provides_survival = True
        # ``map_select_*`` attrs match what real game Bookkeeping writes
        # (see _find_unit_by_map_select / _find_unit_by_global_map_select).
        self.map_select_square = sq_key
        self.map_select_global_index = global_index
        self.map_select_index = local_index
        self.map_select_type = type_name
        self.id = bid if bid is not None else f"{type_name}_{global_index}"
        self.expanded_is_a = list(expanded_is_a or [])


class _Player:
    """A minimal player stand-in: just enough surface for _is_hostile_to_self.

    ``units`` is plain; ``client.alliance`` lets us tell apart enemy / ally.
    ``is_human`` and ``neutral`` are honoured by ``player_is_a_hostile_enemy``.
    """

    def __init__(self, *, name, is_human=False, neutral=False):
        self.units = []
        self.is_human = is_human
        self.neutral = neutral
        self.name = name
        self.id = name
        self.client = types.SimpleNamespace(alliance=name)
        self.allied = [self]
        # match combat.CombatMixin.player_is_a_hostile_enemy contract
        self.player_is_an_enemy = self._player_is_an_enemy

    def _player_is_an_enemy(self, other):
        if other is None or other is self:
            return False
        return self.client.alliance != other.client.alliance

    def player_is_a_hostile_enemy(self, other):
        if other is None or other is self:
            return False
        if getattr(other, "neutral", False):
            return False
        return self.client.alliance != other.client.alliance

    def update_alliance(self):
        # Recompute ``allied`` based on shared client.alliance string.
        allies = [self]
        for p in getattr(self, "_world_players", []):
            if p is self:
                continue
            if p.client.alliance == self.client.alliance:
                allies.append(p)
        self.allied = allies


class _Owner(TriggersMixin):
    """The trigger owner; mixed with TriggersMixin and given a minimal API.

    The campaign-alliance test file established that ``TriggersMixin`` can
    be used standalone once you populate the few attributes the trigger
    method actually touches (``units``, ``world``, ``client``, ``allied``).
    """

    def __init__(self, world_players, own_units, *, name="h", is_human=True):
        self.units = list(own_units)
        self.world = types.SimpleNamespace(
            players=list(world_players), ex_players=[],
            grid={"f4": "f4", "a1": "a1", "e4": "e4", "b2": "b2"},
        )
        self.is_playing = True
        self.time = 0
        self.is_human = is_human
        self.name = name
        self.id = name
        self.client = types.SimpleNamespace(alliance=name)
        self.allied = [self]
        self._enemy_players_cache_time = -1
        self._enemy_units_cache = set()
        self._cached_enemy_units = set()
        self._cached_enemy_units_time = -1
        self._world_players = list(world_players)
        # Re-implement player_is_a_hostile_enemy here too, since
        # ``_is_hostile_to_self`` reads it off ``self``.
        self.player_is_a_hostile_enemy = self._player_is_a_hostile_enemy
        self.player_is_an_enemy = self._player_is_an_enemy

    def _player_is_an_enemy(self, other):
        if other is None or other is self:
            return False
        return self.client.alliance != other.client.alliance

    def _player_is_a_hostile_enemy(self, other):
        if other is None or other is self:
            return False
        if getattr(other, "neutral", False):
            return False
        return self.client.alliance != other.client.alliance


# ---------------------------------------------------------------------------
# Syntax 1: (enemy_building_destroyed <方格> <类型>)  -- natural count fallback
# ---------------------------------------------------------------------------

def test_syntax1_returns_true_when_enemy_building_on_square_dead():
    enemy = _Player(name="e1", neutral=False)
    enemy.units = [_Building("castle", enemy, sq_key="f4", global_index=1)]
    owner = _Owner([owner_p := _Player(name="h", is_human=True), enemy], [])
    # Enemy castle is alive on (f4) -> condition must be False
    assert owner.lang_enemy_building_destroyed(["f4", "castle"]) is False
    # Kill the enemy castle -> condition must be True
    enemy.units.clear()
    assert owner.lang_enemy_building_destroyed(["f4", "castle"]) is True


def test_syntax1_letter_square_also_works():
    """``a1`` letter squares must resolve to the same grid key."""
    enemy = _Player(name="e1")
    enemy.units = [_Building("castle", enemy, sq_key="0,0", global_index=1)]
    owner = _Owner([_Player(name="h", is_human=True), enemy], [])
    assert owner.lang_enemy_building_destroyed(["a1", "castle"]) is True


def test_syntax1_ignores_friendly_building():
    """Friendly buildings on the same square do not block Syntax 1.

    Syntax 1 says: "no enemy building of this type on this square". An
    allied castle still satisfies the condition (it's not an enemy
    building) -- the result must be True ("destroyed" from the
    enemy-counter perspective).
    """
    ally = _Player(name="ally")
    ally.client.alliance = "h"  # same alliance as the human
    ally.units = [_Building("castle", ally, sq_key="f4", global_index=1, local_index=1)]
    h = _Player(name="h", is_human=True)
    h.client.alliance = "h"
    owner = _Owner([h, ally], [])
    # The only castle on f4 is a friendly castle -> "no enemy castle here"
    # so the enemy-Building-destroyed condition fires.
    assert owner.lang_enemy_building_destroyed(["f4", "castle"]) is True


def test_syntax1_ignores_neutral_creep():
    """A neutral creep's building must NOT count as enemy (player_is_a_hostile_enemy excludes neutral).

    So the condition fires (destroyed=True) -- there is no enemy castle
    on f4, just a neutral creep one.
    """
    neutral = _Player(name="n", neutral=True)
    neutral.units = [_Building("castle", neutral, sq_key="f4", global_index=1, local_index=1)]
    owner = _Owner([_Player(name="h", is_human=True), neutral], [])
    assert owner.lang_enemy_building_destroyed(["f4", "castle"]) is True


def test_syntax1_ignores_friendly_building_keeps_enemy_alive():
    """If an enemy castle IS on f4, Syntax 1 must NOT fire even if a friendly
    castle is also on the same square."""
    ally = _Player(name="ally")
    ally.client.alliance = "h"
    ally.units = [_Building("castle", ally, sq_key="f4", global_index=1, local_index=1)]
    enemy = _Player(name="e1")
    enemy.units = [_Building("castle", enemy, sq_key="f4", global_index=2, local_index=1)]
    h = _Player(name="h", is_human=True)
    h.client.alliance = "h"
    owner = _Owner([h, ally, enemy], [])
    # An enemy castle is alive on f4 -> NOT destroyed
    assert owner.lang_enemy_building_destroyed(["f4", "castle"]) is False


def test_syntax1_ignores_neutral_creep_keeps_enemy_alive():
    """Neutral creep + enemy on same square: Syntax 1 still sees the enemy."""
    neutral = _Player(name="n", neutral=True)
    neutral.units = [_Building("castle", neutral, sq_key="f4", global_index=1, local_index=1)]
    enemy = _Player(name="e1")
    enemy.units = [_Building("castle", enemy, sq_key="f4", global_index=2, local_index=1)]
    owner = _Owner([_Player(name="h", is_human=True), neutral, enemy], [])
    assert owner.lang_enemy_building_destroyed(["f4", "castle"]) is False


# ---------------------------------------------------------------------------
# Syntax 2: (enemy_building_destroyed <方格> <序号> <类型>)
# ---------------------------------------------------------------------------

def test_syntax2_index_out_of_range_means_destroyed():
    enemy = _Player(name="e1")
    enemy.units = [_Building("castle", enemy, sq_key="f4", global_index=1)]
    owner = _Owner([_Player(name="h", is_human=True), enemy], [])
    # 5th castle on (f4) is logically destroyed (only 1 exists)
    assert owner.lang_enemy_building_destroyed(["f4", "5", "castle"]) is True


def test_syntax2_index_in_range_means_alive():
    enemy = _Player(name="e1")
    enemy.units = [
        _Building("castle", enemy, sq_key="f4", global_index=1, local_index=1),
        _Building("castle", enemy, sq_key="f4", global_index=2, local_index=2),
    ]
    owner = _Owner([_Player(name="h", is_human=True), enemy], [])
    assert owner.lang_enemy_building_destroyed(["f4", "1", "castle"]) is False
    # Kill first
    enemy.units.pop(0)
    assert owner.lang_enemy_building_destroyed(["f4", "1", "castle"]) is True
    assert owner.lang_enemy_building_destroyed(["f4", "2", "castle"]) is False


# ---------------------------------------------------------------------------
# Syntax 3: (enemy_building_destroyed <序号> <类型>)
# ---------------------------------------------------------------------------

def test_syntax3_global_index_counts_across_enemy_players():
    e1 = _Player(name="e1")
    e2 = _Player(name="e2")
    e1.units = [_Building("castle", e1, sq_key="f4", global_index=1, local_index=1)]
    e2.units = [_Building("castle", e2, sq_key="6,3", global_index=2, local_index=1)]
    owner = _Owner(
        [h := _Player(name="h", is_human=True), e1, e2], []
    )
    # 3rd enemy castle globally is logically destroyed (only 2 exist)
    assert owner.lang_enemy_building_destroyed(["3", "castle"]) is True
    # 1st enemy castle globally is alive
    assert owner.lang_enemy_building_destroyed(["1", "castle"]) is False
    # 2nd enemy castle globally is alive
    assert owner.lang_enemy_building_destroyed(["2", "castle"]) is False


# ---------------------------------------------------------------------------
# Syntax 4: (enemy_building_destroyed <类型>)
# ---------------------------------------------------------------------------

def test_syntax4_all_destroyed_returns_true():
    e1 = _Player(name="e1")
    e2 = _Player(name="e2")
    e1.units = [_Building("castle", e1, sq_key="f4", global_index=1)]
    e2.units = [_Building("castle", e2, sq_key="6,3", global_index=1)]
    owner = _Owner(
        [h := _Player(name="h", is_human=True), e1, e2], []
    )
    # Two castles alive -> not all destroyed
    assert owner.lang_enemy_building_destroyed(["castle"]) is False
    # Kill one
    e1.units.clear()
    # Still one alive
    assert owner.lang_enemy_building_destroyed(["castle"]) is False
    # Kill the other
    e2.units.clear()
    # All destroyed
    assert owner.lang_enemy_building_destroyed(["castle"]) is True


def test_syntax4_different_types_dont_interfere():
    """``(enemy_building_destroyed castle)`` should not be triggered by barracks dying."""
    enemy = _Player(name="e1")
    enemy.units = [
        _Building("castle", enemy, sq_key="f4", global_index=1),
        _Building("barracks", enemy, sq_key="6,3", global_index=1),
    ]
    owner = _Owner([_Player(name="h", is_human=True), enemy], [])
    # Kill the barracks, leave the castle alive
    enemy.units = [u for u in enemy.units if u.type_name == "castle"]
    # Castle still alive -> enemy_building_destroyed castle = False
    assert owner.lang_enemy_building_destroyed(["castle"]) is False
    # But the barracks type is "all destroyed"
    assert owner.lang_enemy_building_destroyed(["barracks"]) is True


# ---------------------------------------------------------------------------
# Syntax 5: (enemy_building_destroyed <建筑ID>)
# ---------------------------------------------------------------------------

def test_syntax5_specific_building_id():
    e1 = _Player(name="e1")
    e2 = _Player(name="e2")
    e1.units = [_Building("castle", e1, sq_key="f4", global_index=1, local_index=1, bid="101")]
    e2.units = [_Building("castle", e2, sq_key="6,3", global_index=2, local_index=1, bid="102")]
    owner = _Owner(
        [h := _Player(name="h", is_human=True), e1, e2], []
    )
    assert owner.lang_enemy_building_destroyed(["101"]) is False
    assert owner.lang_enemy_building_destroyed(["102"]) is False
    # Kill the one with id=101
    e1.units.clear()
    assert owner.lang_enemy_building_destroyed(["101"]) is True
    assert owner.lang_enemy_building_destroyed(["102"]) is False


def test_syntax5_ignores_own_building_id():
    """A building ID belonging to self must not be matched as enemy."""
    h = _Player(name="h", is_human=True)
    h.units = [_Building("castle", h, sq_key="0,0", global_index=1, local_index=1, bid="555")]
    owner = _Owner([h], list(h.units))
    # The owner's own castle must not be considered an enemy building.
    assert owner.lang_enemy_building_destroyed(["555"]) is True


# ---------------------------------------------------------------------------
# building_lost and enemy_building_destroyed are independent
# ---------------------------------------------------------------------------

def test_building_lost_does_not_count_enemy():
    """``building_lost`` only looks at self.units."""
    h = _Player(name="h", is_human=True)
    enemy = _Player(name="e1")
    # owner has zero town_centers; enemy has one alive
    h.units = []
    enemy.units = [_Building("town_center", enemy, sq_key="f4", global_index=1)]
    owner = _Owner([h, enemy], [])
    # building_lost("town_center") -> True (none in self.units)
    assert owner.lang_building_lost(["town_center"]) is True
    # enemy_building_destroyed("town_center") -> False (enemy one still alive)
    assert owner.lang_enemy_building_destroyed(["town_center"]) is False


def test_enemy_building_destroyed_does_not_count_self():
    """``enemy_building_destroyed`` only looks at enemy units."""
    h = _Player(name="h", is_human=True)
    h.units = [_Building("town_center", h, sq_key="0,0", global_index=1)]
    enemy = _Player(name="e1")
    enemy.units = []  # no enemy buildings
    owner = _Owner([h, enemy], list(h.units))
    # Self's town_center is alive -> building_lost is False
    assert owner.lang_building_lost(["town_center"]) is False
    # No enemy town_center at all -> enemy_building_destroyed is True
    assert owner.lang_enemy_building_destroyed(["town_center"]) is True


# ---------------------------------------------------------------------------
# Helper-level tests: _is_hostile_to_self and _iter_enemy_buildings
# ---------------------------------------------------------------------------

def test_is_hostile_to_self_excludes_self():
    h = _Player(name="h", is_human=True)
    owner = _Owner([h], [])
    assert owner._is_hostile_to_self(h) is False
    assert owner._is_hostile_to_self(None) is False


def test_is_hostile_to_self_excludes_neutral():
    h = _Player(name="h", is_human=True)
    n = _Player(name="n", neutral=True)
    owner = _Owner([h, n], [])
    assert owner._is_hostile_to_self(n) is False


def test_is_hostile_to_self_true_for_enemy():
    h = _Player(name="h", is_human=True)
    e = _Player(name="e")
    owner = _Owner([h, e], [])
    assert owner._is_hostile_to_self(e) is True


def test_iter_enemy_buildings_only_enemy():
    h = _Player(name="h", is_human=True)
    ally = _Player(name="ally")
    ally.client.alliance = "h"
    e = _Player(name="e")
    n = _Player(name="n", neutral=True)
    h.units = [_Building("town_center", h, sq_key="0,0", global_index=1)]
    ally.units = [_Building("town_center", ally, sq_key="0,1", global_index=1)]
    e.units = [
        _Building("town_center", e, sq_key="f4", global_index=1),
        _Building("barracks", e, sq_key="f4", global_index=2),
    ]
    n.units = [_Building("town_center", n, sq_key="6,3", global_index=1)]
    h.client.alliance = "h"
    owner = _Owner([h, ally, e, n], list(h.units))
    found = sorted(b.type_name for _p, b in owner._iter_enemy_buildings())
    assert found == ["barracks", "town_center"]  # only e's units, not ally/n/h
    only_tc = [b for _p, b in owner._iter_enemy_buildings(type_name="town_center")]
    assert len(only_tc) == 1
    assert only_tc[0].type_name == "town_center"
