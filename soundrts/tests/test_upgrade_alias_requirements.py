"""Frank free farm-tech aliases must satisfy parent upgrade requirements."""
from __future__ import annotations

import types

from soundrts.worldrequirements import requirements_satisfied


def test_has_treats_upgrade_alias_as_parent():
    """frank_horse_collar in upgrades ⇒ has('horse_collar')."""

    class _FakeRules:
        @staticmethod
        def unit_class(name):
            if name == "frank_horse_collar":
                return types.SimpleNamespace(
                    type_name="frank_horse_collar",
                    is_a=["horse_collar"],
                    expanded_is_a=["horse_collar"],
                )
            if name == "frank_heavy_plow":
                return types.SimpleNamespace(
                    type_name="frank_heavy_plow",
                    is_a=["heavy_plow"],
                    expanded_is_a=["heavy_plow"],
                )
            return None

    from soundrts import definitions
    from soundrts.worldplayerbase.base import Player

    saved = definitions.rules
    definitions.rules = _FakeRules()
    try:
        player = Player.__new__(Player)
        player.upgrades = ["frank_horse_collar"]
        player.units = []
        assert player.has("frank_horse_collar") is True
        assert player.has("horse_collar") is True
        assert player.has("heavy_plow") is False
        player.upgrades.append("frank_heavy_plow")
        assert player.has("heavy_plow") is True
    finally:
        definitions.rules = saved


def test_frank_heavy_plow_requirements_after_frank_horse_collar():
    """Inherited req horse_collar is satisfied by researching frank_horse_collar."""

    class _FakeRules:
        @staticmethod
        def unit_class(name):
            if name == "frank_horse_collar":
                return types.SimpleNamespace(
                    type_name="frank_horse_collar",
                    is_a=["horse_collar"],
                    expanded_is_a=["horse_collar"],
                )
            return None

    from soundrts import definitions
    from soundrts.worldplayerbase.base import Player

    saved = definitions.rules
    definitions.rules = _FakeRules()
    try:
        player = Player.__new__(Player)
        player.upgrades = ["frank_horse_collar", "feudal_age", "castle_age"]
        player.units = [
            types.SimpleNamespace(type_name="frank_mill", expanded_is_a=["mill", "building"])
        ]
        # Same requirements as heavy_plow / frank_heavy_plow
        assert requirements_satisfied(
            player, ["mill", "castle_age", "horse_collar"]
        )
        assert not requirements_satisfied(
            player, ["mill", "imperial_age", "heavy_plow"]
        )
    finally:
        definitions.rules = saved
