"""Regression tests for Joan of Arc ch2 objective semantics.

Background (user-reported bug, 2026-10-17):
  ch2 objective 1 (tts 8822 = "训练 8 个民兵鼓舞奥尔良") used to
  trigger on ``(has_entered b2 monk)`` -- a single monk walking
  to b2 was enough to complete the goal, regardless of militia
  training.  The same trigger also relied on a bare ``monk`` unit
  even though the chapter was supposed to start with Joan (the
  hero unit ``npc_joan``).

  ch2 objective 2 (tts 8823 = "打破围城——消灭全部英军") used to
  trigger on ``(has_entered d4 monk)`` -- a movement check that
  had no relationship to actually breaking the English siege.

  Defeat on ``key_unit_killed monk`` would also fire on any monk
  death (e.g. the La Hire camp's defender) rather than on Joan's
  death -- a story-critical regression.

Fix:
  * ch2 player line now starts with ``npc_joan`` (Joan) instead of
    a bare ``monk``.
  * Objective 1 now uses ``(has 8 militia)`` -- the player must
    train 8 militia (rallying the citizens).
  * Objective 2 now uses ``(no_enemy_left)`` -- break the siege by
    destroying all English forces.
  * Defeat on ``(key_unit_killed npc_joan)`` -- only Joan's death
    ends the campaign.

ch3 / ch4 / ch5 are also brought into consistency so the same
hero unit appears in every Joan chapter and ``key_unit_killed``
always refers to ``npc_joan`` (ch1, ch2) or to the hero where
present (ch3, ch4, ch5).  ch6 is Burgundian-attacker, no Joan.
"""
from __future__ import annotations

from pathlib import Path

JOAN = Path("mods/aoe2/single/Joan of Arc")


import pytest


def _read(name: str) -> str:
    return (JOAN / name).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# ch2 — DE AoE2 ch. 2 "The Maid of Orleans" faithful rewrite
# ---------------------------------------------------------------------------

def test_ch2_player_starts_with_joan_and_duke():
    """ch2 player must start with npc_joan (Joan) and npc_d_alencon
    (Duke d'Alençon), matching the AoE2 DE ch. 2 starting force."""
    text = _read("2.txt")
    for line in text.splitlines():
        if line.startswith("player ") and " a1 " in line:
            assert "npc_joan" in line, (
                f"ch2 player line must include npc_joan (Joan hero), got: {line!r}"
            )
            assert "npc_d_alencon" in line, (
                f"ch2 player line must include npc_d_alencon (Duke d'Alençon, "
                f"DE ch. 2 starting unit), got: {line!r}"
            )
            return
    raise AssertionError("No ch2 player line found")


def test_ch2_player_starts_with_de_escort():
    """ch2 player must start with the DE ch. 2 escort: 1 scout_cavalry,
    2 man_at_arms (two-handed swordsmen), 4 aoe_knight, and 6 trade_cart."""
    text = _read("2.txt")
    for line in text.splitlines():
        if line.startswith("player ") and " a1 " in line:
            tokens = line.split()
            assert "scout_cavalry" in tokens, (
                "ch2 player must have 1 scout_cavalry (DE ch. 2), got: " + line
            )
            assert "man_at_arms" in tokens, (
                "ch2 player must have 2 man_at_arms (DE ch. 2), got: " + line
            )
            assert "aoe_knight" in tokens, (
                "ch2 player must have 4 aoe_knight (DE ch. 2), got: " + line
            )
            assert "trade_cart" in tokens, (
                "ch2 player must have 6 trade_cart (DE ch. 2 supply run), got: " + line
            )
            return
    raise AssertionError("No ch2 player line found")


def test_ch2_imperial_age_forbidden():
    """ch2 must forbid imperial_age (DE ch. 2 is capped at Castle Age,
    population 125).  parse_assets reads "-<type_name>" as a forbidden_tech."""
    text = _read("2.txt")
    for line in text.splitlines():
        if line.startswith("player ") and " a1 " in line:
            assert "-imperial_age" in line, (
                "ch2 player line must end with '-imperial_age' (forbidden tech) "
                "to cap the chapter at Castle Age, got: " + line
            )
            return
    raise AssertionError("No ch2 player line found")


def test_ch2_blois_grants_escort():
    """When Joan reaches the Blois camp (e2 or e3), the (add_units) trigger
    must give the player the French army: 8 aoe_knight + 12 aoe_archer.
    This mirrors ch. 1 Baudricourt's escort pattern."""
    text = _read("2.txt")
    assert ("has_entered e2 npc_joan" in text or
            "has_entered e3 npc_joan" in text), (
        "ch2 must trigger when Joan enters the Blois camp (e2 or e3)"
    )
    import re
    m = re.search(
        r"add_units\s+(?:e2|e3)\s+(.+?)\)",
        text,
    )
    assert m, "ch2 must have an (add_units e2/e3 …) trigger for the Blois escort"
    arg = m.group(1)
    assert "aoe_knight" in arg, (
        "Blois escort must include aoe_knight units (DE ch. 2), got: " + arg
    )
    assert "aoe_archer" in arg, (
        "Blois escort must include aoe_archer units (DE ch. 2), got: " + arg
    )


def test_ch2_orleans_hand_over():
    """When Joan + 6 trade_carts reach the Orleans TC (h6), the
    Orleans camp (computer4/computer5) must be transferred to the player
    via (transfer_units)."""
    text = _read("2.txt")
    assert "has_entered h6 npc_joan" in text, (
        "ch2 must trigger when Joan enters Orleans TC (h6)"
    )
    assert "transfer_units computer4 player1" in text, (
        "ch2 must transfer Orleans camp (computer4) to player1 "
        "when Joan + trade_carts arrive"
    )
    assert "transfer_units computer5 player1" in text, (
        "ch2 must transfer Orleans garrison (computer5) to player1 "
        "when Joan + trade_carts arrive"
    )


def test_ch2_objective_3_requires_castle_age():
    """Objective 3 (reach Castle Age) must use (has castle_age) as the
    completion condition."""
    text = _read("2.txt")
    assert "has castle_age" in text, (
        "ch2 must use (has castle_age) for objective 3 (Castle Age), got: " + text[:500]
    )


def test_ch2_objective_4_english_castle_destroyed():
    """Objective 4 (destroy 1 English Castle) must use
    (enemy_building_destroyed k5 aoe_castle) OR
    (enemy_building_destroyed l5 aoe_castle)."""
    text = _read("2.txt")
    assert ("enemy_building_destroyed k5 aoe_castle" in text or
            "enemy_building_destroyed l5 aoe_castle" in text), (
        "ch2 must use (enemy_building_destroyed k5/l5 aoe_castle) for "
        "objective 4 (destroy 1 English Castle)"
    )


def test_ch2_defeat_on_npc_joan_killed():
    """Defeat must trigger on npc_joan (Joan) death."""
    text = _read("2.txt")
    assert "key_unit_killed npc_joan" in text, (
        "ch2 must defeat the player on npc_joan (Joan) being killed"
    )


def test_ch2_trade_cart_protection():
    """At timer 600 the player must still have 6 trade_carts alive
    (lt (count trade_cart) 6 triggers defeat)."""
    text = _read("2.txt")
    assert "lt (count trade_cart)" in text, (
        "ch2 must use (lt (count trade_cart) 6) at timer 600 "
        "to protect the 6 trade_carts (DE ch. 2 hard fail)"
    )
    assert "defeat" in text, (
        "ch2 must trigger defeat if trade_carts are lost before timer 600"
    )


def test_ch2_cut_scene_for_blois_arrival():
    """The Blois arrival cut_scene must use tts id 8835
    (new, unused id for 'Joan reaches Blois' dialogue)."""
    text = _read("2.txt")
    assert "cut_scene 8835" in text, (
        "ch2 must use cut_scene 8835 for the Blois arrival dialogue"
    )


def test_ch2_cut_scene_for_orleans_hand_over():
    """The Orleans hand-over cut_scene must use tts id 8836
    (new, unused id for 'Orleans is yours' dialogue)."""
    text = _read("2.txt")
    assert "cut_scene 8836" in text, (
        "ch2 must use cut_scene 8836 for the Orleans hand-over dialogue"
    )


def test_ch2_cut_scene_for_victory():
    """The victory cut_scene must use tts id 8838
    (new, unused id for 'Victory — English castle destroyed')."""
    text = _read("2.txt")
    assert "cut_scene 8838" in text, (
        "ch2 must use cut_scene 8838 for the victory dialogue"
    )


# ---------------------------------------------------------------------------
# ch3 / ch4 / ch5 — same hero unit, same defeat semantics
# ---------------------------------------------------------------------------

def _assert_has_npc_joan_in_player_and_defeat(text: str, ch: str) -> None:
    """Each Joan chapter (3/4/5) must include npc_joan in the player
    line and must trigger defeat on key_unit_killed npc_joan."""
    for line in text.splitlines():
        if line.startswith("player ") and not line.startswith("player_is"):
            assert "npc_joan" in line, (
                f"{ch} player line must include npc_joan (Joan), got: {line!r}"
            )
            break
    else:
        raise AssertionError(f"No {ch} player line found")
    assert "key_unit_killed npc_joan" in text, (
        f"{ch} must trigger defeat on npc_joan (Joan) being killed"
    )
    assert "key_unit_killed monk" not in text, (
        f"{ch} must NOT trigger defeat on a bare monk (Joan is the hero)"
    )


def test_ch3_has_npc_joan_and_defeat_on_hero():
    _assert_has_npc_joan_in_player_and_defeat(_read("3.txt"), "ch3")


def test_ch4_has_npc_joan_and_defeat_on_hero():
    _assert_has_npc_joan_in_player_and_defeat(_read("4.txt"), "ch4")


def test_ch5_has_npc_joan_and_defeat_on_hero():
    _assert_has_npc_joan_in_player_and_defeat(_read("5.txt"), "ch5")


def test_ch4_goal2_escorts_dauphin_to_reims():
    """ch4's second objective escorts the Dauphin to Reims (c5).

    (ch4 was rewritten to the DE-faithful "The Rising" layout: the
    objective is the coronation at Reims, not a walk to Compiegne.)"""
    text = _read("4.txt")
    assert "has_entered c5 npc_dauphin" in text, (
        "ch4 must complete objective 2 on (has_entered c5 npc_dauphin)"
    )
    assert "has_entered d4 monk" not in text, (
        "ch4 must NOT complete objective 2 on a bare monk entering d4"
    )


# ---------------------------------------------------------------------------
# ch6 is the Compiègne DEFENCE mission: the player is the French
# garrison and must have BOTH heroes on the field.
# ---------------------------------------------------------------------------

def test_ch6_player_defends_with_joan_and_dauphin():
    """ch6 is a defence mission: the player commands the French
    garrison at the Compiègne citadel, with Joan AND the Dauphin
    present (both are key units -- losing either one loses)."""
    text = _read("6.txt")
    assert "npc_joan" in text, (
        "ch6 must include npc_joan (the player escorts Joan to safety)"
    )
    assert "npc_dauphin" in text, (
        "ch6 must include npc_dauphin (the man who becomes Charles VII)"
    )
    assert "key_unit_killed npc_joan" in text, (
        "ch6 must trigger defeat when Joan is killed"
    )
    assert "key_unit_killed npc_dauphin" in text, (
        "ch6 must trigger defeat when the Dauphin is killed"
    )


def test_ch6_besiegers_are_enemies_not_allies():
    """The English siege ring must be a HOSTILE computer, not an ally.

    Regression: the previous version of ch6 declared the besiegers
    with ``alliance 1`` (ally), so the "hold Compiègne" objective made
    no sense and the player was fighting nobody.
    """
    text = _read("6.txt")
    for line in text.splitlines():
        s = line.split(";", 1)[0].strip()
        if not s.startswith("computer_only "):
            continue
        assert "alliance" not in s, (
            f"ch6 besieger must be an enemy, but found: {line!r}"
        )
        assert "non_neutral" in s, (
            f"ch6 besieger must be non_neutral (hostile), "
            f"but found: {line!r}"
        )


def test_ch6_player_starts_at_compiègne_citadel():
    """The player must start at e6 (5,6) -- the Compiègne citadel."""
    text = _read("6.txt")
    player_lines = [
        line.split(";", 1)[0].strip()
        for line in text.splitlines()
        if line.split(";", 1)[0].strip().startswith("player ")
    ]
    assert len(player_lines) == 1, (
        f"ch6 must have exactly one player line, got {player_lines!r}"
    )
    tokens = player_lines[0].split()
    # player <gold> <wood> <food> <stone> <square> ...
    assert tokens[5] == "e6", (
        f"ch6 player must start at e6 (the citadel), got {tokens[5]!r}"
    )


def test_ch6_has_starting_squares_for_ai_exploration():
    """``starting_squares`` must list every spawn slot.

    Without it ``world.starting_squares`` is empty, the AI's
    auto_explore has no destination, and the besiegers never attack.
    """
    text = _read("6.txt")
    assert "starting_squares " in text, (
        "ch6 must declare starting_squares so the besieger AI can explore"
    )
    squares = []
    for line in text.splitlines():
        s = line.split(";", 1)[0].strip()
        if s.startswith("starting_squares "):
            squares = s.split()[1:]
            break
    for sq in ("e6", "c2", "h1", "a1"):
        assert sq in squares, (
            f"ch6 starting_squares must include {sq}, got {squares!r}"
        )


def test_ch6_has_coronation_countdown_and_escape_objective():
    """The coronation must be a concrete countdown, and the chapter
    must end with a real escape objective across the bridge."""
    text = _read("6.txt")
    assert "(timer 12)" in text, (
        "ch6 must contain a (timer 12) coronation countdown trigger"
    )
    assert "(objective_complete 1)" in text, (
        "ch6 must complete objective 1 (hold until crowned) on coronation"
    )
    assert "(has_entered e4 npc_joan)" in text, (
        "ch6 must complete objective 2 when Joan reaches the bridge e4"
    )
    assert "(victory)" in text, (
        "ch6 must grant victory when Joan escapes across the bridge"
    )


def test_ch6_besiegers_get_real_ai():
    """A ``computer_only`` slot defaults to a do-nothing trigger AI.

    Without ``(ai intermediate)`` the besiegers would never attack.
    """
    text = _read("6.txt")
    assert "trigger computer1 (timer 0) (ai intermediate)" in text, (
        "ch6 English besiegers must switch to a real attacking AI"
    )
    assert "trigger computer2 (timer 0) (ai intermediate)" in text, (
        "ch6 Burgundian besiegers must switch to a real attacking AI"
    )


def test_ch6_besiegers_have_an_economy():
    """The besiegers need a farm, production buildings and a gold mine.

    Without them the besieger AI burns through its starting food during
    the first wave, hits food = 0 and stalls on its get-line forever:
    it attacks once and then sits there, which makes the defence
    trivial again (the exact bug the user reported).
    """
    text = _read("6.txt")
    comp_lines = [
        line.split(";", 1)[0].strip()
        for line in text.splitlines()
        if line.split(";", 1)[0].strip().startswith("computer_only ")
    ]
    assert len(comp_lines) == 3, (
        f"ch6 must have three besieger bases, got {comp_lines!r}"
    )
    # computer1 (English ring) and computer2 (Burgundians) are the
    # attackers -- they need the full economy kit.
    for line in comp_lines[:2]:
        for needed in ("farm", "barracks", "archery_range", "stables",
                       "peasant", "house"):
            assert needed in line, (
                f"ch6 besieger must start with {needed!r} to keep "
                f"attacking, got: {line!r}"
            )
    # Gold: the player owns the only mine at e6, so the besiegers need
    # one of their own or their gold never grows past the starting
    # amount and they can never train knights.
    mines = [
        line.split(";", 1)[0].strip()
        for line in text.splitlines()
        if line.split(";", 1)[0].strip().startswith("goldmines ")
    ]
    assert len(mines) >= 2, (
        f"ch6 needs gold mines for the besiegers too, got {mines!r}"
    )


def test_ch6_player_has_a_real_citadel():
    """The player needs a fortress, not a bare town centre.

    The besiegers run a ``constant_attacks 1`` AI; without a castle and
    towers they simply walk over the garrison and the chapter is
    unwinnable before the coronation countdown ends.
    """
    text = _read("6.txt")
    player_lines = [
        line.split(";", 1)[0].strip()
        for line in text.splitlines()
        if line.split(";", 1)[0].strip().startswith("player ")
    ]
    assert len(player_lines) == 1
    line = player_lines[0]
    for needed in ("aoe_castle", "scouttower", "militia", "aoe_archer"):
        assert needed in line, (
            f"ch6 player must start with {needed!r} to hold the citadel, "
            f"got: {line!r}"
        )


def test_ch6_announces_the_coronation_countdown():
    """The wait must be legible: the player must be told how long
    the siege still has to last."""
    text = _read("6.txt")
    for cut in ("8897", "8898", "8899"):
        assert f"(cut_scene {cut})" in text, (
            f"ch6 must announce the countdown step {cut}"
        )
    # The tts ids must exist in every language folder.
    base = Path("mods") / "aoe2" / "single" / "Joan of Arc"
    for lang_dir in sorted(base.glob("ui*")):
        tts = lang_dir / "tts.txt"
        if not tts.exists():
            continue
        ids = {
            int(line.split()[0])
            for line in tts.read_text(encoding="utf-8").splitlines()
            if line[:1].isdigit() and len(line.split()[0]) >= 4
        }
        for cut in (8893, 8894, 8895, 8896, 8897, 8898, 8899):
            assert cut in ids, (
                f"{tts} is missing tts id {cut} (ch6 text)"
            )


# ---------------------------------------------------------------------------
# square_name labels must match the actual occupants of the squares.
#
# Background (user-reported bug, 2026-10-17):
#   ch2 used to label d4 (the allied French Orleans citadel at
#   4,4) as "8886 = 英军城堡" (English keep).  Players hovering
#   that tile would see "英军城堡" over what is actually a French
#   town with French militia and French archers.  The same file
#   also did not label the actual English outposts at c4 / e3 /
#   e4 / f4 (the latter two are part of the original chapter
#   notes' "Fort on the north bank" but had no buildings).
#
#   ch3 mis-labeled d4 (player base) as 8886 "英军城堡" instead of
#   8885 "法军驻军".
#
#   ch4 mis-labeled e4 (English reinforcement) as 8878 "贡比涅要塞"
#   (that's d4) and labeled the empty d5 as 8879 "勃艮第埋伏"
#   (that's c5).
#
#   ch5 mis-labeled c3 (Loire river) and a2 (empty player meadow)
#   as 8884 / 8881 even though only a1 (Meung) and d3 (Beaugency)
#   hold those garrisoned towns.
#
#   ch6 mis-labeled d4 (French Comiègne citadel) as 8876
#   "英军围城圈" and a1 (French forward outpost) as 8877
#   "贡比涅南岸".
# ---------------------------------------------------------------------------

# (chapter, square (col,row), must_be_labeled_as, must_NOT_be_labeled_as)
# must_be_labeled_as = the tts ID of the place that actually lives there
# must_NOT_be_labeled_as = the tts ID we used to mislabel it with
CH2_SQUARE_LABELS = [
    # (1,1) = a1 = Chinon (player start) = 8871 Vaucouleurs
    ("2.txt", "1,1", "8871", None),
    # (5,2) = e2 = Blois French army camp = 8873
    ("2.txt", "5,2", "8873", None),
    # (5,3) = e3 = Blois (monastery) = 8873
    ("2.txt", "5,3", "8873", None),
    # (8,6) = h6 = Orleans citadel = 8885
    ("2.txt", "8,6", "8885", None),
    # (8,7) = h7 = Orleans (scouttower) = 8885
    ("2.txt", "8,7", "8885", None),
    # (11,5) = k5 = North English keep = 8886
    ("2.txt", "11,5", "8886", None),
    # (12,5) = l5 = Outer English fortification = 8886
    ("2.txt", "12,5", "8886", None),
]

CH3_SQUARE_LABELS = [
    # (1,1) = a1 = English Fort St. Loup (圣卢普堡)
    ("3.txt", "1,1", "8874", None),
    # (6,5) = f5 = English Les Tourelles (图雷尔)
    ("3.txt", "6,5", "8875", None),
    # (4,4) = d4 = player base (奥尔良 / 法军驻军),
    # NOT the English keep (8886 = 英军城堡)
    ("3.txt", "4,4", "8885", "8886"),
    # (5,5) = e5 = English reinforcement camp (英军围城圈)
    ("3.txt", "5,5", "8876", None),
]

CH4_SQUARE_LABELS = [
    # ch4 was rewritten to the DE-faithful layout ("The Rising"):
    # a1 = Chinon (French base), c5 = Reims cathedral, f4 = English
    # burghers at Meaux, e2 = Burgundian main camp.
    # (1,1) = a1 = Chinon, French base (希农 / 法军基地)
    ("4.txt", "1,1", "8872", None),
    # (3,5) = c5 = Reims cathedral (兰斯大教堂)
    ("4.txt", "3,5", "8846", None),
    # (5,2) = e2 = Burgundian main camp (勃艮第大营)
    ("4.txt", "5,2", "8847", None),
    # (6,4) = f4 = English burghers at Meaux (默城英军堡),
    # NOT 8888 "巴黎" (Paris is not on this map)
    ("4.txt", "6,4", "8886", "8888"),
]

CH5_SQUARE_LABELS = [
    # (1,1) = a1 = English Meung-sur-Loire (默恩)
    ("5.txt", "1,1", "8884", None),
    # (6,5) = f5 = English Jallains (雅兰)
    ("5.txt", "6,5", "8882", None),
    # (4,3) = d3 = English Beaugency (博让西)
    ("5.txt", "4,3", "8881", None),
    # c3 (col 3 row 3) is the Loire river -- must NOT be labeled
    # as any English town. a2 is empty player meadow.
    ("5.txt", "3,3", None, "8881"),
    ("5.txt", "2,1", None, "8884"),
]

CH6_SQUARE_LABELS = [
    # ch6 was rewritten as a 10x8 defence mission: the PLAYER is the
    # French garrison defending the Compiègne citadel at e6 (5,6),
    # the English siege ring sits on the south bank at c2 (3,2),
    # and the Oise bridge is at e4 (5,4).
    # (5,6) = e6 = French Compiègne citadel (贡比涅要塞),
    # NOT 8876 "英军围城圈"
    ("6.txt", "5,6", "8890", "8876"),
    # (3,2) = c2 = English siege ring (英军围城圈) -- an ENEMY base
    ("6.txt", "3,2", "8894", None),
    # (5,4) = e4 = the Oise bridge (瓦兹河桥), the only crossing
    ("6.txt", "5,4", "8893", None),
]


def _square_label_test(chapter: str, square: str, must_be: str | None,
                       must_not_be: str | None) -> None:
    """Verify a single ``square_name`` line correctly (or does not)
    label the given square with the given tts id."""
    text = _read(chapter)
    matching = [
        line for line in text.splitlines()
        if line.startswith("square_name ") and f" {square}" in line.split("#")[0]
    ]
    if must_be is None:
        # Nothing should label this square.
        assert not matching, (
            f"{chapter} square {square} must NOT be labeled, "
            f"but found: {matching!r}"
        )
        return
    assert matching, (
        f"{chapter} square {square} must be labeled with {must_be}, "
        f"but no square_name line covers it"
    )
    # The first square_name line that mentions this square must carry
    # the required alias.  (We don't allow two aliases on the same
    # square, but the engine doesn't either.)
    label_line = matching[0]
    # Format: ``square_name <alias> <coords...>``
    # alias is the first non-comment token after ``square_name``.
    tokens = label_line.split()
    assert tokens[0] == "square_name"
    assert tokens[1] == must_be, (
        f"{chapter} square {square} must be labeled with {must_be} "
        f"(tts id), got {tokens[1]!r} in line: {label_line!r}"
    )
    if must_not_be is not None:
        # Make sure no OTHER square_name line on this file labels
        # this square with the old (wrong) tts id.
        for line in text.splitlines():
            if not line.startswith("square_name "):
                continue
            if f" {square}" not in line.split("#")[0]:
                continue
            tokens = line.split()
            if len(tokens) >= 2 and tokens[1] == must_not_be:
                raise AssertionError(
                    f"{chapter} square {square} must NOT be labeled "
                    f"with {must_not_be} (mislabel), but found in: {line!r}"
                )



@pytest.mark.parametrize("chapter,square,must_be,must_not_be", [
    *CH2_SQUARE_LABELS,
    *CH3_SQUARE_LABELS,
    *CH4_SQUARE_LABELS,
    *CH5_SQUARE_LABELS,
    *CH6_SQUARE_LABELS,
])
def test_square_name_matches_actual_occupant(chapter, square, must_be, must_not_be):
    """square_name labels must match what actually lives on the tile.

    Regression: d4 in ch2 / ch3 was mislabeled as the English keep
    (8886 = 英军城堡) even though it was a French allied town."""
    _square_label_test(chapter, square, must_be, must_not_be)


# ---------------------------------------------------------------------------
# Meadows (build land) must not be dropped on river / water squares.
#
# Background (user-reported bug, 2026-10-17):
#   ch2 used ``nb_meadows_by_square 3`` + ``additional_meadows a1``.
#   ``nb_meadows_by_square`` is interpreted as "3 meadows on every
#   single square of the map" (river row included), so the 6 river
#   tiles (a3..f3) ended up with 3 build sites each sitting on top
#   of the river.  The previous workflow's only escape hatch was
#   ``remove_meadows X`` which subtracts ONE meadow, so the author
#   could never fully clean up a 3-deep default.
#
#   jl7 (aoe2 multi) avoids this by using ``nb_meadows_by_square 0``
#   and then explicitly listing land squares on multiple
#   ``additional_meadows`` lines (each line = 1 meadow per listed
#   square).  We follow the same pattern here.
# ---------------------------------------------------------------------------

# (chapter, square) pairs that must NOT receive a meadow because
# they are river / water.  Column is 1-based, row is 1-based.
JOAN_WATER_SQUARES = [
    # ch2: 12x8, row 4 is Loire river (a4..l4) except f4 (6,4) is bridge
    ("2.txt", "1,4"), ("2.txt", "2,4"), ("2.txt", "3,4"),
    ("2.txt", "4,4"), ("2.txt", "5,4"),
    # f4 (6,4) is bridge land -- DO NOT list here
    ("2.txt", "7,4"), ("2.txt", "8,4"), ("2.txt", "9,4"),
    ("2.txt", "10,4"), ("2.txt", "11,4"), ("2.txt", "12,4"),
    # ch3: row 3 river + row 2 water (a2..f2, b2..f2, col 1..6)
    ("3.txt", "1,3"), ("3.txt", "2,3"), ("3.txt", "3,3"),
    ("3.txt", "4,3"), ("3.txt", "5,3"), ("3.txt", "6,3"),
    ("3.txt", "1,2"), ("3.txt", "2,2"), ("3.txt", "3,2"),
    ("3.txt", "4,2"), ("3.txt", "5,2"), ("3.txt", "6,2"),
    # ch4: row 3 river (a3..e3, 5-col grid)
    ("4.txt", "1,3"), ("4.txt", "2,3"), ("4.txt", "3,3"),
    ("4.txt", "4,3"), ("4.txt", "5,3"),
    # ch5: row 3 river + row 2 water (a3..f3, a2..f2, col 1..6)
    ("5.txt", "1,3"), ("5.txt", "2,3"), ("5.txt", "3,3"),
    ("5.txt", "4,3"), ("5.txt", "5,3"), ("5.txt", "6,3"),
    ("5.txt", "1,2"), ("5.txt", "2,2"), ("5.txt", "3,2"),
    ("5.txt", "4,2"), ("5.txt", "5,2"), ("5.txt", "6,2"),
    # ch6: 10x8, row 4 is the Oise river (a4..j4) except e4 (5,4)
    # which is the bridge -- DO NOT list the bridge here.
    ("6.txt", "1,4"), ("6.txt", "2,4"), ("6.txt", "3,4"),
    ("6.txt", "4,4"), ("6.txt", "6,4"), ("6.txt", "7,4"),
    ("6.txt", "8,4"), ("6.txt", "9,4"), ("6.txt", "10,4"),
]


def _nb_meadows_on_square(text: str, square: str) -> int:
    """Return how many meadows ``text`` (a parsed map file) drops
    on ``square`` (col,row 1-based).

    The engine adds ``nb_meadows_by_square`` per square plus
    ``additional_meadows`` (one per occurrence in the file)."""
    # nb_meadows_by_square is global; if a chapter is in jl7-style
    # (``nb_meadows_by_square 0``) the global is 0.
    nb_global = 0
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("nb_meadows_by_square"):
            try:
                nb_global = int(s.split()[1])
            except (IndexError, ValueError):
                pass
            break
    if nb_global > 0:
        # Pre-jl7-style: every square (incl. river) gets nb_global
        # meadows, modulo remove_meadows.  The bug we're guarding
        # against: nb_global >= 1 on a river tile with no
        # remove_meadows counter-measure.
        return nb_global
    # jl7-style: count additional_meadows lines that list this square.
    n = 0
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("additional_meadows"):
            continue
        for tok in s.split()[1:]:
            if tok == square:
                n += 1
    return n


@pytest.mark.parametrize("chapter,square", JOAN_WATER_SQUARES)
def test_no_meadow_on_river_square(chapter, square):
    """Water / river squares must not have meadows (build sites).

    Regression: ch2 had ``nb_meadows_by_square 3`` with no
    remove_meadows, so 3 build sites sat on every river tile.
    Followed jl7's pattern: ``nb_meadows_by_square 0`` plus
    explicit additional_meadows on land squares only."""
    text = _read(chapter)
    n = _nb_meadows_on_square(text, square)
    assert n == 0, (
        f"{chapter} river/water square {square} must have 0 meadows, "
        f"got {n}.  Either nb_meadows_by_square is non-zero (legacy) or "
        f"additional_meadows lists the square.  See jl7.txt for the "
        f"jl7-style pattern: nb_meadows_by_square 0 plus explicit "
        f"additional_meadows on land squares only."
    )


@pytest.mark.parametrize("chapter", ["2.txt", "3.txt", "4.txt", "5.txt", "6.txt"])
def test_chapter_uses_jl7_meadow_pattern(chapter):
    """Every Joan chapter with a river should follow jl7's meadow
    pattern: ``nb_meadows_by_square 0`` plus explicit
    ``additional_meadows`` on land squares.

    This prevents the old ``nb_meadows_by_square 3`` global from
    re-leaking meadows into the river row."""
    text = _read(chapter)
    # If the chapter has no river at all, skip the assertion.
    has_river = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("terrain river") or s.startswith("water "):
            has_river = True
            break
    if not has_river:
        return
    # Find the nb_meadows_by_square line.
    nb_line = None
    for line in text.splitlines():
        if line.strip().startswith("nb_meadows_by_square"):
            nb_line = line.strip()
            break
    assert nb_line is not None, (
        f"{chapter} has a river but no nb_meadows_by_square line; "
        f"add ``nb_meadows_by_square 0`` plus explicit additional_meadows"
    )
    assert nb_line.split()[1] == "0", (
        f"{chapter} uses {nb_line!r} which would drop meadows on "
        f"every river tile.  Use ``nb_meadows_by_square 0`` plus "
        f"explicit additional_meadows on land squares (jl7 pattern)."
    )