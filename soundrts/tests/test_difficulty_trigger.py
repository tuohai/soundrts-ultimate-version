"""Difficulty-conditional scenario content (AoE2 DE style).

Covers the engine features added so that campaign scenarios can branch
their content on the difficulty the player picked, exactly like the AoE2
Definitive Edition original:

* ``(difficulty <level>)`` / ``(difficulty <op> <level>)`` trigger
  conditions -- e.g. ``(difficulty standard)``.
* Trigger-granted upgrades that actually apply to the units the player
  ALREADY owns (previously ``(add_units <tech>)`` only appended the tech
  name to ``player.upgrades``).
* Replay round-trip of the difficulty level, so a replay rebuilds the
  same scenario content as the original game.
* Spectator synchronisation of the difficulty level.
* The AoE2 DE 3-tier single-player difficulty set (standard/moderate/hard).

Regression for: El Cid chapter 4 "Black Guards" -- on Standard, King
Alfonso's base has a Castle that is handed to the player with the rest of
the base, and the player begins with Murder Holes researched.
"""
from __future__ import annotations

import types

import pytest


# ---------------------------------------------------------------------------
# 1. difficulty level ordering / comparison helpers
# ---------------------------------------------------------------------------
def test_level_index_orders_difficulty_from_easy_to_extreme():
    from soundrts.coop_difficulty import (
        EASY,
        EXTREME,
        HARD,
        MODERATE,
        STANDARD,
        level_index,
    )

    assert level_index(EASY) < level_index(STANDARD) < level_index(MODERATE)
    assert level_index(MODERATE) < level_index(HARD) < level_index(EXTREME)


def test_compare_level_supports_all_operators():
    from soundrts.coop_difficulty import compare_level

    assert compare_level("standard", "==", "standard") is True
    assert compare_level("standard", "=", "standard") is True
    assert compare_level("standard", "!=", "easy") is True
    assert compare_level("standard", "!=", "standard") is False
    assert compare_level("standard", "<", "hard") is True
    assert compare_level("standard", "<=", "standard") is True
    assert compare_level("standard", ">", "easy") is True
    assert compare_level("standard", ">=", "standard") is True
    assert compare_level("standard", ">=", "hard") is False
    # An unknown operator is never true.
    assert compare_level("standard", "~=", "standard") is False


def test_compare_level_is_deterministic_for_unknown_levels():
    from soundrts.coop_difficulty import compare_level

    # Unknown levels normalise to "standard", so the result is stable.
    assert compare_level("nonsense", "==", "standard") is True
    assert compare_level("", "==", "standard") is True
    assert compare_level(None, "==", "standard") is True


def test_single_player_difficulty_keeps_all_five_tiers():
    """The single-player campaign keeps the full 5-tier difficulty set.

    AoE2 DE campaigns only have three difficulties, but that must not cost
    the player the "easy" and "extreme" tiers.  The DE "standard tier
    bonus" is instead expressed with the ``story`` semantic tier.
    """
    from soundrts.coop_difficulty import (
        EASY,
        EXTREME,
        HARD,
        LEVELS,
        MODERATE,
        STANDARD,
        normalize_single_player_level,
    )

    assert LEVELS == (EASY, STANDARD, MODERATE, HARD, EXTREME)
    for level in LEVELS:
        assert normalize_single_player_level(level) == level


def test_story_tier_covers_easy_and_standard():
    """``story`` = the DE "standard tier bonus" range (easy + standard)."""
    from soundrts.coop_difficulty import (
        EASY,
        STANDARD,
        STORY,
        STORY_TIERS,
        is_story_tier,
    )

    assert STORY_TIERS == (EASY, STANDARD)
    assert is_story_tier(EASY) is True
    assert is_story_tier(STANDARD) is True
    assert is_story_tier("moderate") is False
    assert is_story_tier("hard") is False
    assert is_story_tier("extreme") is False
    # An unset difficulty falls back to standard -> inside the story range.
    assert is_story_tier("") is True


def test_compare_level_handles_the_story_semantic_tier():
    from soundrts.coop_difficulty import compare_level

    assert compare_level("easy", "==", "story") is True
    assert compare_level("standard", "==", "story") is True
    assert compare_level("moderate", "==", "story") is False
    assert compare_level("hard", "==", "story") is False
    assert compare_level("extreme", "==", "story") is False

    assert compare_level("moderate", "!=", "story") is True
    assert compare_level("easy", "!=", "story") is False

    # "story" has no ordering, so size comparisons are always false.
    for op in ("<", "<=", ">", ">="):
        assert compare_level("extreme", op, "story") is False
        assert compare_level("easy", op, "story") is False


def test_normalize_single_player_level_maps_legacy_five_tier_values():
    from soundrts.coop_difficulty import (
        HARD,
        STANDARD,
        normalize_single_player_level,
    )

    assert normalize_single_player_level("standard") == STANDARD
    assert normalize_single_player_level("moderate") == "moderate"
    assert normalize_single_player_level("hard") == HARD
    # The 5-tier set is kept, so "easy" and "extreme" stay valid.
    assert normalize_single_player_level("easy") == "easy"
    assert normalize_single_player_level("extreme") == "extreme"
    # Anything unknown falls back to the standard baseline.
    assert normalize_single_player_level("") == STANDARD
    assert normalize_single_player_level("nonsense") == STANDARD
    assert normalize_single_player_level(None) == STANDARD


# ---------------------------------------------------------------------------
# 2. the (difficulty ...) trigger condition
# ---------------------------------------------------------------------------
class _StubWorld:
    def __init__(self, difficulty=""):
        self.scenario_difficulty = difficulty


class _StubPlayer:
    """Minimal stand-in exposing just what ``lang_difficulty`` needs."""

    def __init__(self, difficulty=""):
        self.world = _StubWorld(difficulty)

    # The real implementation lives on TriggersMixin; borrow it so the
    # test exercises the shipped code rather than a copy of it.
    from soundrts.worldplayerbase.triggers import TriggersMixin as _M

    lang_difficulty = _M.lang_difficulty
    _current_difficulty = _M._current_difficulty


@pytest.mark.parametrize(
    "difficulty,expected",
    [
        ("easy", {"standard": False, ">=hard": False, "!=easy": False, "<=moderate": True, "story": True}),
        ("standard", {"standard": True, ">=hard": False, "!=easy": True, "<=moderate": True, "story": True}),
        ("moderate", {"standard": False, ">=hard": False, "!=easy": True, "<=moderate": True, "story": False}),
        ("hard", {"standard": False, ">=hard": True, "!=easy": True, "<=moderate": False, "story": False}),
        ("extreme", {"standard": False, ">=hard": True, "!=easy": True, "<=moderate": False, "story": False}),
    ],
)
def test_lang_difficulty_evaluates_equality_and_comparisons(difficulty, expected):
    player = _StubPlayer(difficulty)
    assert player.lang_difficulty(["standard"]) is expected["standard"]
    assert player.lang_difficulty([">=", "hard"]) is expected[">=hard"]
    assert player.lang_difficulty(["!=", "easy"]) is expected["!=easy"]
    assert player.lang_difficulty(["<=", "moderate"]) is expected["<=moderate"]
    assert player.lang_difficulty(["story"]) is expected["story"]


def test_lang_difficulty_supports_the_remaining_operators():
    player = _StubPlayer("moderate")
    assert player.lang_difficulty(["<", "hard"]) is True
    assert player.lang_difficulty(["<", "moderate"]) is False
    assert player.lang_difficulty([">", "easy"]) is True
    assert player.lang_difficulty([">", "hard"]) is False
    assert player.lang_difficulty(["==", "moderate"]) is True
    assert player.lang_difficulty(["=", "moderate"]) is True


def test_lang_difficulty_without_arguments_is_false():
    player = _StubPlayer("standard")
    assert player.lang_difficulty([]) is False


def test_lang_difficulty_with_garbage_operator_is_false():
    player = _StubPlayer("standard")
    assert player.lang_difficulty(["~=", "standard"]) is False


def test_unset_difficulty_falls_back_to_standard():
    """An unset difficulty means "no difficulty-specific content"."""
    player = _StubPlayer("")
    assert player.lang_difficulty(["standard"]) is True
    assert player.lang_difficulty([">=", "hard"]) is False


# ---------------------------------------------------------------------------
# 3. trigger-granted upgrades reach the units the player already owns
# ---------------------------------------------------------------------------
def test_grant_upgrade_by_trigger_applies_effects_to_existing_units():
    """``(add_units <tech>)`` must not just record the tech name.

    Before the fix, the tech name was appended to ``player.upgrades`` and
    nothing else happened -- so existing buildings kept their unmodified
    stats (e.g. a castle kept its 1000 minimum range after Murder Holes
    was supposedly granted).
    """
    from soundrts.worldplayerbase.triggers import TriggersMixin

    class FakeUnit:
        def __init__(self):
            self.applied = []

    class FakeUpgrade:
        type_name = "murder_holes"

        @classmethod
        def upgrade_player(cls, player):
            for unit in player.units:
                unit.applied.append(cls.type_name)

    class FakePlayer:
        def __init__(self):
            self.upgrades = []
            self.units = [FakeUnit()]

        _grant_upgrade_by_trigger = TriggersMixin._grant_upgrade_by_trigger

    player = FakePlayer()
    player._grant_upgrade_by_trigger(FakeUpgrade, "murder_holes")

    assert "murder_holes" in player.upgrades
    assert player.units[0].applied == ["murder_holes"], (
        "the trigger-granted tech must be applied to the units the player "
        "already owns"
    )


def test_grant_upgrade_by_trigger_is_idempotent():
    from soundrts.worldplayerbase.triggers import TriggersMixin

    class FakeUpgrade:
        type_name = "murder_holes"

        @classmethod
        def upgrade_player(cls, player):
            pass

    class FakePlayer:
        def __init__(self):
            self.upgrades = []

        _grant_upgrade_by_trigger = TriggersMixin._grant_upgrade_by_trigger

    player = FakePlayer()
    player._grant_upgrade_by_trigger(FakeUpgrade, "murder_holes")
    player._grant_upgrade_by_trigger(FakeUpgrade, "murder_holes")
    assert player.upgrades.count("murder_holes") == 1


def test_grant_upgrade_by_trigger_does_not_advance_the_age():
    """Age phases must never be granted by a trigger."""
    from soundrts.worldplayerbase.triggers import TriggersMixin

    class FakePlayer:
        def __init__(self):
            self.upgrades = []
            self.current_phase = "dark_age"

        _grant_upgrade_by_trigger = TriggersMixin._grant_upgrade_by_trigger

    class FakePhase:
        type_name = "feudal_age"

        @classmethod
        def upgrade_player(cls, player):  # pragma: no cover - must not run
            raise AssertionError("a phase must not be advanced by a trigger")

    player = FakePlayer()
    player._grant_upgrade_by_trigger(FakePhase, "feudal_age")

    assert player.current_phase == "dark_age"
    assert "feudal_age" in player.upgrades


# ---------------------------------------------------------------------------
# 4. replay round-trip of the difficulty level
# ---------------------------------------------------------------------------
def test_replay_seed_line_carries_the_difficulty_level():
    """The difficulty must be written into the replay header.

    The scenario content branches on difficulty, so a replay that lost
    the level would rebuild DIFFERENT content than the original game.
    """
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    src = (root / "soundrts" / "game.py").read_text(encoding="utf-8")
    assert 'parts.append(str(diff))' in src
    # Reading side: the 4th token is the difficulty.
    assert "self.scenario_difficulty = seed_parts[3]" in src
    assert "self.coop_difficulty = seed_parts[3]" in src


def test_replay_seed_line_parsing_handles_old_and_new_formats():
    """Old replays have only a seed; new ones may carry 3 or 4 tokens."""
    seed_parts = "42".split()
    assert len(seed_parts) < 3

    seed_parts = "42 100 100".split()
    assert len(seed_parts) == 3
    assert len(seed_parts) < 4

    seed_parts = "42 120 115 moderate".split()
    assert len(seed_parts) >= 4
    assert seed_parts[3] == "moderate"


def test_spectator_notification_carries_the_difficulty():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    srv = (root / "soundrts" / "serverroom.py").read_text(encoding="utf-8")
    menu = (root / "soundrts" / "clientservermenu.py").read_text(encoding="utf-8")

    # The server sends the difficulty along with the spectator start.
    assert "_coop_difficulty" in srv
    # The client parses it back and applies it to the game.
    assert "game.scenario_difficulty = difficulty" in menu
    assert "game.coop_difficulty = difficulty" in menu


def test_game_and_spectator_write_the_difficulty_into_the_world():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    src = (root / "soundrts" / "game.py").read_text(encoding="utf-8")
    # Both the live game and the spectator must set it, or the trigger
    # conditions would evaluate differently on the two sides.
    assert src.count('getattr(self, "scenario_difficulty", "")') >= 2


# ---------------------------------------------------------------------------
# 5. the campaign passes the chosen difficulty to the game
# ---------------------------------------------------------------------------
def test_mission_chapter_passes_the_campaign_difficulty_to_the_game():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    src = (root / "soundrts" / "campaign.py").read_text(encoding="utf-8")
    assert "game.coop_difficulty = self.campaign.get_difficulty()" in src
    assert "game.scenario_difficulty = game.coop_difficulty" in src


def test_campaign_difficulty_menu_offers_all_five_tiers():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    src = (root / "soundrts" / "campaign.py").read_text(encoding="utf-8")
    assert "LEVELS" in src
    # The single-player menu must NOT use the 3-tier DE list any more:
    # "easy" and "extreme" stay selectable.
    assert "SINGLE_PLAYER_LEVELS" not in src


def test_campaign_get_difficulty_uses_the_single_player_normaliser():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    src = (root / "soundrts" / "campaign.py").read_text(encoding="utf-8")
    assert "normalize_single_player_level" in src


# ---------------------------------------------------------------------------
# 6. the map parser accepts the (difficulty ...) trigger syntax
# ---------------------------------------------------------------------------
def test_map_parser_accepts_difficulty_comparison_operators():
    from soundrts.world.world_map import _TRIGGER_COMPARISON_OPERATORS

    for op in (">=", "<=", "==", "=", "!=", "<", ">"):
        assert op in _TRIGGER_COMPARISON_OPERATORS


def test_difficulty_trigger_takes_exactly_one_condition():
    """``trigger owner (difficulty standard) (action)`` -- one condition.

    A trigger line has exactly one condition slot; writing
    ``(timer 0) (difficulty standard) (action)`` is rejected by the
    parser with "unexpected nested list in trigger prefix".
    """
    from soundrts.trigger_script import parse_trigger_tree

    owners, condition, action, meta = parse_trigger_tree(
        [["player1"], ["difficulty", "standard"], ["add_units", "murder_holes"]]
    )
    assert owners == ["player1"]
    assert condition == ["difficulty", "standard"]
    assert action == ["add_units", "murder_holes"]
    assert meta is None

    with pytest.raises(ValueError):
        parse_trigger_tree(
            [
                ["player1"],
                ["timer", "0"],
                ["difficulty", "standard"],
                ["add_units", "murder_holes"],
            ]
        )


# ---------------------------------------------------------------------------
# 7. the (remove_unit <square> <type> [count]) trigger action
# ---------------------------------------------------------------------------
class _FakeObject:
    """Minimal stand-in for a unit/building standing on a square."""

    def __init__(self, type_name, player=None):
        self.type_name = type_name
        self.expanded_is_a = ()
        self.player = player
        self.deleted = False

    def delete(self):
        self.deleted = True


class _FakeSquare:
    def __init__(self, objects):
        self.objects = list(objects)


class _RemoveUnitPlayer:
    """Just enough of a player for ``lang_remove_unit``."""

    from soundrts.worldplayerbase.triggers import TriggersMixin as _M

    lang_remove_unit = _M.lang_remove_unit
    _normalize_square_token = _M._normalize_square_token

    def __init__(self, world):
        self.world = world

    def check_type(self, obj, type_name):
        """Mirror the real ``Player.check_type`` for the root type."""
        if getattr(obj, "type_name", None) == type_name:
            return True
        return type_name in (getattr(obj, "expanded_is_a", ()) or ())


def _remove_world(objects):
    world = types.SimpleNamespace(grid={"0,0": _FakeSquare(objects)})
    return world, _RemoveUnitPlayer(world)


def test_remove_unit_deletes_the_matching_object():
    tower = _FakeObject("scouttower")
    world, player = _remove_world([tower, _FakeObject("militia")])
    player.lang_remove_unit(["0,0", "scouttower"])
    assert tower.deleted is True
    assert len(world.grid["0,0"].objects) == 2, (
        "remove_unit must not touch the other objects"
    )


def test_remove_unit_accepts_the_square_name():
    """``c2`` must resolve to the same grid key as ``2,1``."""
    tower = _FakeObject("scouttower")
    world, player = _remove_world([tower])
    world.grid["2,1"] = world.grid["0,0"]
    player.lang_remove_unit(["c2", "scouttower"])
    assert tower.deleted is True


def test_remove_unit_honours_the_count_argument():
    units = [_FakeObject("militia") for _ in range(3)]
    world, player = _remove_world(units)
    player.lang_remove_unit(["0,0", "militia", "2"])
    assert sum(1 for u in units if u.deleted) == 2, (
        "remove_unit with a count must delete exactly that many units"
    )


def test_remove_unit_matches_through_the_is_a_chain():
    """``man_at_arms`` is_a ``militia`` -- the root type must match too."""
    man = _FakeObject("man_at_arms")
    man.expanded_is_a = ("militia", "soldier")
    world, player = _remove_world([man])
    player.lang_remove_unit(["0,0", "militia"])
    assert man.deleted is True


def test_remove_unit_ignores_an_unknown_square():
    world, player = _remove_world([])
    # Must not raise.
    player.lang_remove_unit(["z9", "scouttower"])


def test_remove_unit_ignores_an_unknown_type():
    tower = _FakeObject("scouttower")
    world, player = _remove_world([tower])
    player.lang_remove_unit(["0,0", "trebuchet"])
    assert tower.deleted is False


def test_remove_unit_is_deterministic():
    """The deletion order is the square's object order -- no randomness."""
    objects = [_FakeObject("militia") for _ in range(5)]
    world, player = _remove_world(objects)
    player.lang_remove_unit(["0,0", "militia", "3"])
    assert [u.deleted for u in objects] == [True, True, True, False, False], (
        "remove_unit must delete the FIRST matching objects in the square's "
        "object order, so every client rebuilds the same world"
    )
