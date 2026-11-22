"""Regression tests for computer-slot / alliance alignment.

Background (user-reported bug, 2026-11-21):
  In ``mods/aoe2/single/Joan of Arc/2.txt`` the Blois camp was split
  over THREE ``computer_only`` lines (e2 town center, e3 army, e3
  monastery) while the map only declared ``trigger computer1`` ..
  ``trigger computer9``.  ``trigger computerN`` binds positionally to
  the N-th ``computer_only`` line, so the extra line shifted every
  later slot by one:

    * the Orleans h7 garrison (slot 5) got ``alliance 2`` -- the
      ENEMY alliance -- while keeping the ``neutral`` keyword, so the
      UI drew it as "Neutral" but its militia and watch tower
      (``agro_on_sight 1``, ``formations 1``) attacked the player;
    * the Burgundy f3 outpost (slot 3) got ``alliance 1`` -- the
      player's own alliance -- so it never attacked;
    * the Blois monastery got ``alliance 2``;
    * the English l6 outwork (slot 9) had no trigger at all and
      stayed on the default ``ai`` alliance.

  Attacking the neutral h7 camp also flipped its label from
  "Neutral" to "Franks": ``note_combat_with`` clears ``neutral``
  once the camp has been struck, and the slot's faction is
  ``franks``.  Faction and alliance are independent -- two Frankish
  factions can be enemies.

Fix:
  * the map now has exactly NINE ``computer_only`` slots again;
  * every slot carries a ``name <alias>`` and every trigger
    references the alias, so an insertion/removal can no longer
    silently shift an alliance onto the wrong base;
  * the engine gained load-time diagnostics that warn about a
    misaligned ``trigger computerN`` and about a slot whose alliance
    contradicts its own ``neutral`` / hostile nature.

These tests assert the map's slot->square->alliance intent, and the
engine's diagnostics.
"""
from __future__ import annotations

import re
from pathlib import Path

JOAN = Path("mods/aoe2/single/Joan of Arc")


def _read(name: str) -> str:
    return (JOAN / name).read_text(encoding="utf-8")


def _strip_comment(line: str) -> str:
    return line.split(";", 1)[0].strip()


def _computer_slots(text: str) -> list[tuple[str, str, bool]]:
    """Return [(alias, square, neutral)] for each ``computer_only`` line.

    ``computer_only <gold> <wood> <food> <stone> [neutral] [faction X]
    [name <alias>] <square> <unit> <count> ...``
    """
    slots = []
    for raw in text.splitlines():
        line = _strip_comment(raw)
        if not line.startswith("computer_only "):
            continue
        tokens = line.split()
        assert tokens[0] == "computer_only"
        neutral = "neutral" in tokens
        alias = None
        square = None
        i = 1
        # Skip the 4 resource numbers.
        while i < len(tokens) and re.fullmatch(r"\d+", tokens[i]):
            i += 1
        while i < len(tokens):
            tok = tokens[i]
            if tok == "name" and i + 1 < len(tokens):
                alias = tokens[i + 1]
                i += 2
                continue
            if tok == "faction" and i + 1 < len(tokens):
                i += 2
                continue
            if tok in ("neutral", "non_neutral"):
                i += 1
                continue
            # First non-keyword token after the resources = the square.
            square = tok
            break
        assert alias is not None, (
            f"every computer_only line must carry a 'name <alias>', got: {line!r}"
        )
        assert square is not None, (
            f"computer_only line has no square, got: {line!r}"
        )
        slots.append((alias, square, neutral))
    return slots


# ---------------------------------------------------------------------------
# The map itself
# ---------------------------------------------------------------------------

def test_ch2_has_exactly_nine_computer_slots():
    """The map must declare exactly nine computer slots.

    A tenth slot would shift every ordinal ``trigger computerN``
    after it -- the bug this whole file guards against."""
    slots = _computer_slots(_read("2.txt"))
    assert len(slots) == 9, (
        f"ch2 must have exactly 9 computer_only slots, got {len(slots)}: {slots!r}"
    )


def test_ch2_every_slot_has_a_unique_alias():
    aliases = [a for a, _sq, _n in _computer_slots(_read("2.txt"))]
    assert len(set(aliases)) == len(aliases), (
        f"ch2 computer slot aliases must be unique, got {aliases!r}"
    )


def test_ch2_no_ordinal_computer_triggers_remain():
    """All triggers must address slots by alias.

    An ordinal ``trigger computerN`` is legal but fragile: it silently
    re-binds when a ``computer_only`` line is added or removed."""
    text = _read("2.txt")
    offenders = [
        _strip_comment(line)
        for line in text.splitlines()
        if re.match(r"^trigger\s+computer\d+\s", _strip_comment(line))
    ]
    assert not offenders, (
        "ch2 must address computer slots by alias, not by ordinal. "
        f"Found ordinal triggers: {offenders!r}"
    )


def test_ch2_slot_square_alliance_intent():
    """Every slot's alliance must match the map's intent.

    The expected table below IS the intent of AoE2 DE ch. 2:

      * Blois (e2, e3)  -- French army camp, friendly (neutral)
      * Burgundy (f3)  -- enemy (hostile outwork on the bridge)
      * Orleans (h6, h7) -- French city, friendly (neutral), handed
                             over to the player on objective 2
      * English (k5, k6, l5, l6) -- enemies
    """
    expected = {
        "blois_e2": ("e2", 1),
        "blois_e3": ("e3", 1),
        "burgundy_f3": ("f3", 2),
        "orleans_h6": ("h6", 1),
        "orleans_h7": ("h7", 1),
        "english_k5": ("k5", 2),
        "english_k6": ("k6", 2),
        "english_l5": ("l5", 2),
        "english_l6": ("l6", 2),
    }
    slots = dict((a, (sq, n)) for a, sq, n in _computer_slots(_read("2.txt")))
    assert set(slots) == set(expected), (
        f"ch2 slots must be exactly {sorted(expected)}, got {sorted(slots)}"
    )
    for alias, (square, alliance) in expected.items():
        got_square, _neutral = slots[alias]
        assert got_square == square, (
            f"ch2 slot {alias!r} must sit on {square}, got {got_square}"
        )
        trigger = re.search(
            r"^trigger\s+%s\s+\(timer 0\)\s+\(alliance (\d+)\)" % re.escape(alias),
            _read("2.txt"),
            re.MULTILINE,
        )
        assert trigger, (
            f"ch2 slot {alias!r} must have a (timer 0) (alliance N) trigger"
        )
        assert int(trigger.group(1)) == alliance, (
            f"ch2 slot {alias!r} ({square}) must be on alliance {alliance}, "
            f"got alliance {trigger.group(1)}"
        )


def test_ch2_neutral_flag_matches_alliance():
    """``neutral`` and ``alliance`` must not contradict each other.

    A *neutral* slot on the ENEMY alliance is drawn as "Neutral" in the
    UI but its units still see the player as an enemy and open fire --
    exactly the reported h7 behaviour.  A *hostile* slot (no
    ``neutral``) on the player's OWN alliance is the mirror image: it
    never attacks but is presented as an enemy base.
    """
    text = _read("2.txt")
    player_alliances = set(re.findall(
        r"^trigger\s+player1\s+\(timer 0\)\s+\(alliance (\d+)\)",
        text, re.MULTILINE,
    ))
    assert player_alliances == {"1"}, (
        f"ch2 player must be on alliance 1, got {player_alliances}"
    )
    for alias, square, neutral in _computer_slots(text):
        m = re.search(
            r"^trigger\s+%s\s+\(timer 0\)\s+\(alliance (\d+)\)" % re.escape(alias),
            text, re.MULTILINE,
        )
        assert m, f"ch2 slot {alias!r} has no alliance trigger"
        alliance = m.group(1)
        if neutral:
            assert alliance == "1", (
                f"ch2 neutral slot {alias!r} ({square}) must be on the "
                f"player's alliance 1, got {alliance}"
            )
        else:
            assert alliance == "2", (
                f"ch2 hostile slot {alias!r} ({square}) must be on the enemy "
                f"alliance 2, got {alliance}"
            )


def test_ch2_no_slot_lacks_an_alliance():
    """Every slot needs exactly one alliance trigger.

    A slot without one stays on the default ``ai`` alliance and
    belongs to nobody (that was the state of the English l6 outwork)."""
    text = _read("2.txt")
    aliases = [a for a, _sq, _n in _computer_slots(text)]
    for alias in aliases:
        count = len(re.findall(
            r"^trigger\s+%s\s+\(timer 0\)\s+\(alliance \d+\)" % re.escape(alias),
            text, re.MULTILINE,
        ))
        assert count == 1, (
            f"ch2 slot {alias!r} must have exactly one alliance trigger, "
            f"got {count}"
        )


def test_ch2_difficulty_triggers_target_the_right_bases():
    """The per-difficulty ``remove_unit`` triggers must name the base
    they actually modify."""
    text = _read("2.txt")
    expected_towers = [
        ("burgundy_f3", "f3"),
        ("english_k5", "k5"),
        ("english_k6", "k6"),
        ("english_l5", "l5"),
        ("english_l6", "l6"),
    ]
    for alias, square in expected_towers:
        assert re.search(
            r"^trigger\s+%s\s+\(difficulty story\)\s+\(remove_unit %s scouttower\)"
            % (re.escape(alias), re.escape(square)),
            text, re.MULTILINE,
        ), (
            f"ch2 must remove one watch tower from {alias!r} ({square}) "
            f"on the story tier"
        )


def test_ch2_h7_garrison_is_a_french_ally():
    """The reported bug, stated as an assertion.

    The Orleans h7 garrison must be a NEUTRAL French ally (alliance 1)
    -- not a hostile base disguised as neutral.
    """
    text = _read("2.txt")
    slots = dict((a, (sq, n)) for a, sq, n in _computer_slots(text))
    assert "orleans_h7" in slots
    square, neutral = slots["orleans_h7"]
    assert square == "h7"
    assert neutral, (
        "the h7 garrison must be declared neutral (a passive French camp)"
    )
    assert re.search(
        r"^trigger\s+orleans_h7\s+\(timer 0\)\s+\(alliance 1\)",
        text, re.MULTILINE,
    ), (
        "the h7 garrison must be on the player's alliance 1 (French ally); "
        "on alliance 2 it is drawn as neutral yet attacks the player"
    )


# ---------------------------------------------------------------------------
# Engine: named computer slots
# ---------------------------------------------------------------------------

def _world_map_mixin():
    """Return a bare ``WorldMapMixin`` instance, or skip the test."""
    from soundrts.world import world_map
    m = world_map.WorldMapMixin.__new__(world_map.WorldMapMixin)
    m.computers_starts = []
    m.players_starts = []
    m.computers_names = {}
    m.computers_factions = []
    m.name_to_square = {}
    m.nb_res = 4
    return m


def _make_slot(square, units, neutral=False, triggers=None):
    """Build a ``computers_starts`` entry in the engine's real layout.

    Layout: ``[resources, units, triggers, neutral, population, ...]``
    where ``units`` is a list of ``(square, cls, multiplicity)`` tuples.
    """
    return [
        [0, 0],
        [(square, u, 1) for u in units],
        list(triggers or []),
        neutral,
    ]


def _capture_warnings(fn):
    """Run ``fn`` and return the map warnings it produced."""
    from soundrts.world import world_core

    messages = []
    original = world_core.map_warning
    world_core.map_warning = lambda line, msg, *a, **kw: messages.append(
        "%s: %s" % (line, msg)
    )
    try:
        fn()
    finally:
        world_core.map_warning = original
    return messages


def test_engine_strips_name_keyword_from_computer_items():
    """``name <alias>`` must be consumed by the map parser, not treated
    as a unit name or a square."""
    from soundrts.world import world_map

    items = [
        "0", "0", "0", "0", "neutral", "faction", "franks",
        "name", "blois_e2", "e2", "town_center", "1", "house",
    ]
    filtered, name = world_map.WorldMapMixin._strip_slot_name_from_items(
        None, items
    )
    assert name == "blois_e2"
    assert "name" not in filtered
    assert "blois_e2" not in filtered
    assert filtered == [
        "0", "0", "0", "0", "neutral", "faction", "franks",
        "e2", "town_center", "1", "house",
    ]


def test_engine_named_computer_slot_is_resolvable_at_runtime():
    """A map that names its slots must let triggers and runtime
    references address them by alias."""
    from soundrts.world import world_map

    m = _world_map_mixin()
    m._add_start("computer_only", [
        "computer_only", "0", "0", "0", "0", "neutral", "faction",
        "franks", "name", "blois_e2", "e2", "town_center", "1",
    ])
    assert m.computers_names == {"blois_e2": 0}

    # The alias must be usable as a trigger owner.
    m._add_trigger(
        "blois_e2 (timer 0) (alliance 1)".replace("(", " ( ").replace(")", " ) ").split()
    )
    assert len(m.computers_starts[0][2]) == 1, (
        "the alias trigger must land on the named slot"
    )


def test_engine_diagnostics_warn_on_misaligned_trigger():
    """A ``trigger computerN`` that mentions another slot's square must
    be reported."""
    m = _world_map_mixin()
    m.computers_starts = [
        _make_slot("e2", ["town_center"], triggers=[
            [None, ["remove_unit", "f3", "scouttower"], None],
        ]),
        _make_slot("f3", ["scouttower"]),
    ]

    messages = _capture_warnings(m._warn_on_computer_slot_misalignment)

    assert messages, (
        "a trigger that mentions another slot's square must be reported"
    )
    assert "f3" in messages[0]
    assert "slot(s) 2" in messages[0], (
        "the warning must name the slot that actually owns the square"
    )


def test_engine_diagnostics_silent_on_aligned_trigger():
    """A trigger that mentions its OWN slot's square must not warn."""
    m = _world_map_mixin()
    m.computers_starts = [
        _make_slot("e2", ["town_center"], triggers=[
            [None, ["remove_unit", "e2", "scouttower"], None],
        ]),
        _make_slot("f3", ["scouttower"]),
    ]

    messages = _capture_warnings(m._warn_on_computer_slot_misalignment)

    assert not messages, (
        f"an aligned trigger must not warn, got: {messages!r}"
    )


def test_engine_diagnostics_warn_on_alliance_contradiction():
    """A NEUTRAL slot on the enemy alliance must be reported."""
    m = _world_map_mixin()
    m.players_starts = [[
        [0, 0], [],
        [[None, ["alliance", "1"], None]],
        False,
    ]]
    m.computers_starts = [
        _make_slot("h7", ["scouttower"], neutral=True, triggers=[
            [None, ["alliance", "2"], None],
        ]),
    ]

    messages = _capture_warnings(m._warn_on_alliance_slot_mismatch)

    assert messages, (
        "a neutral slot on the enemy alliance must be reported"
    )
    assert "NEUTRAL" in messages[0]
    assert "alliance 2" in messages[0]


def test_engine_diagnostics_warn_on_hostile_slot_on_friendly_alliance():
    """The mirror contradiction: a HOSTILE slot on the player's own
    alliance must be reported too."""
    m = _world_map_mixin()
    m.players_starts = [[
        [0, 0], [],
        [[None, ["alliance", "1"], None]],
        False,
    ]]
    m.computers_starts = [
        _make_slot("f3", ["scouttower"], neutral=False, triggers=[
            [None, ["alliance", "1"], None],
        ]),
    ]

    messages = _capture_warnings(m._warn_on_alliance_slot_mismatch)

    assert messages, (
        "a hostile slot on the player's own alliance must be reported"
    )
    assert "HOSTILE" in messages[0]


def test_engine_diagnostics_silent_on_a_consistent_map():
    """A consistent map must produce no warning at all."""
    m = _world_map_mixin()
    m.players_starts = [[
        [0, 0], [],
        [[None, ["alliance", "1"], None]],
        False,
    ]]
    m.computers_starts = [
        _make_slot("e2", ["town_center"], neutral=True, triggers=[
            [None, ["alliance", "1"], None],
        ]),
        _make_slot("f3", ["scouttower"], neutral=False, triggers=[
            [None, ["alliance", "2"], None],
        ]),
    ]

    messages = _capture_warnings(
        lambda: (
            m._warn_on_alliance_slot_mismatch(),
            m._warn_on_computer_slot_misalignment(),
        )
    )

    assert not messages, (
        f"a consistent map must not warn, got: {messages!r}"
    )


def test_ch2_map_loads_without_slot_warnings():
    """Loading the real ch2 map must not produce any slot warning.

    This is the end-to-end guard: it parses the actual file through the
    engine's own map parser and asserts that neither the misalignment
    nor the alliance-contradiction diagnostic fires.
    """
    from soundrts.world.world_map import WorldMapMixin

    text = _read("2.txt")

    m = WorldMapMixin.__new__(WorldMapMixin)
    m.computers_starts = []
    m.players_starts = []
    m.computers_names = {}
    m.computers_factions = []
    m.name_to_square = {}
    m.nb_res = 4

    messages = _capture_warnings(lambda: _parse_ch2(m, text))

    assert not messages, (
        f"ch2 must load without any computer-slot warning, got: {messages!r}"
    )


def test_ch2_ordinal_variant_loads_without_slot_warnings():
    """The same map written with ORDINAL triggers must also be clean.

    Ordinal triggers stay legal (older maps use them), so the
    diagnostic must not fire on a correctly ordered ordinal map.
    """
    from soundrts.world.world_map import WorldMapMixin

    text = _read("2.txt")
    ordinal = text
    for alias, n in [
        ("blois_e2", 1), ("blois_e3", 2), ("burgundy_f3", 3),
        ("orleans_h6", 4), ("orleans_h7", 5), ("english_k5", 6),
        ("english_k6", 7), ("english_l5", 8), ("english_l6", 9),
    ]:
        ordinal = ordinal.replace(
            "trigger %s " % alias, "trigger computer%d " % n
        )

    m = WorldMapMixin.__new__(WorldMapMixin)
    m.computers_starts = []
    m.players_starts = []
    m.computers_names = {}
    m.computers_factions = []
    m.name_to_square = {}
    m.nb_res = 4

    messages = _capture_warnings(lambda: _parse_ch2(m, ordinal))

    assert not messages, (
        "a correctly ordered ordinal map must not warn, got: %r" % (messages,)
    )


def test_engine_diagnostics_fire_when_a_slot_is_inserted():
    """Inserting a ``computer_only`` line must shift every later ordinal
    trigger -- and the engine must say so.

    This is the exact failure that produced the reported h7 bug.
    """
    from soundrts.world.world_map import WorldMapMixin

    text = _read("2.txt")
    ordinal = text
    for alias, n in [
        ("blois_e2", 1), ("blois_e3", 2), ("burgundy_f3", 3),
        ("orleans_h6", 4), ("orleans_h7", 5), ("english_k5", 6),
        ("english_k6", 7), ("english_l5", 8), ("english_l6", 9),
    ]:
        ordinal = ordinal.replace(
            "trigger %s " % alias, "trigger computer%d " % n
        )
    shifted = ordinal.replace(
        "computer_only 0 0 0 0 faction britons name english_k6 k6",
        "computer_only 0 0 0 0 faction britons name extra_base j6 "
        "scouttower 1 militia\n"
        "computer_only 0 0 0 0 faction britons name english_k6 k6",
    )
    assert shifted != ordinal

    m = WorldMapMixin.__new__(WorldMapMixin)
    m.computers_starts = []
    m.players_starts = []
    m.computers_names = {}
    m.computers_factions = []
    m.name_to_square = {}
    m.nb_res = 4

    messages = _capture_warnings(lambda: _parse_ch2(m, shifted))

    assert messages, (
        "an inserted computer_only line must shift the later ordinal "
        "triggers, and the engine must report it"
    )
    assert any("k6" in msg for msg in messages), (
        f"the warning must name the square that moved, got: {messages!r}"
    )


def _parse_ch2(m, text):
    """Parse the ch2 map text through the engine's real parser.

    The full ``_parse_map`` needs a lot of map state (terrain, paths,
    meadows, ...); this helper drives the pieces the slot diagnostics
    depend on: the ``computer_only`` slots and the ``trigger`` lines.

    It mirrors ``_parse_map``'s preprocessing (parentheses become
    separate tokens) so the trigger lines reach ``_add_trigger`` in
    exactly the shape the engine produces.
    """
    for raw in text.splitlines():
        line = raw.split(";", 1)[0].strip()
        if not line:
            continue
        line = line.replace("(", " ( ").replace(")", " ) ")
        words = line.split()
        if not words:
            continue
        if words[0] in ("computer_only", "computer"):
            m._add_start(words[0], words)
        elif words[0] == "player":
            m._add_start("player", words)
        elif words[0] == "trigger":
            # ``_add_trigger`` expects the words AFTER the "trigger"
            # keyword, exactly like ``_parse_map`` passes them.
            m._add_trigger(words[1:])
    m._warn_on_computer_slot_misalignment()
    m._warn_on_alliance_slot_mismatch()
    m._warn_on_computer_slot_misalignment()
    m._warn_on_alliance_slot_mismatch()
