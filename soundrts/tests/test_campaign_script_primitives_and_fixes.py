# -*- coding: utf-8 -*-
"""Regression tests for the Joan of Arc / William Wallace campaign fixes
and for the new scriptable trigger primitives.

Covered here:

**Engine primitives** (new ``lang_*`` actions in
``soundrts/worldplayerbase/triggers.py``)

  * ``camera``     -- server pushes the square id to the client;
  * ``flash``      -- server pushes the square id + colour;
  * ``reveal_map`` / ``reveal_area`` -- permanent fog reveal;
  * ``tribute``    -- resource transfer between two players, including
    the explicit ``from`` / ``to`` direction form;
  * ``my_eval``    -- an unknown keyword is *warned about*, not silently
    dropped.

**Map fixes**

  * Wallace ch. 7 -- no premature ``(victory)`` on ``(has aoe_castle)``;
  * Wallace ch. 5 / 6 / 7 -- the English get a real AI and an economy;
  * Wallace ch. 6 -- the market exists and the ally pays a tribute;
  * Joan ch. 1 -- two objectives (8820 / 8821);
  * Joan ch. 2 -- the trade-cart deadline is 600 s, pop cap is 125;
  * Joan ch. 4 -- ``(defeat)`` instead of the no-op ``(campaign_defeat)``,
    objective 2 is 8904, the relic cutscene is 8905.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

JOAN = ROOT / "mods" / "aoe2" / "single" / "Joan of Arc"
WALLACE = ROOT / "mods" / "aoe2" / "single" / "William Wallace"

JOAN_LANGS = (
    "ui",
    "ui-zh",
    "ui-de",
    "ui-fr",
    "ui-es",
    "ui-it",
    "ui-pl",
    "ui-pt-BR",
    "ui-ru",
    "ui-sk",
    "ui-cs",
    "ui-be",
    "ui-vi",
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _statements(text: str) -> list[str]:
    """Map text with comments stripped, one statement per line."""
    out = []
    for raw in text.splitlines():
        line = raw.split(";", 1)[0].strip()
        if line:
            out.append(line)
    return out


def _read(folder: Path, name: str) -> str:
    return (folder / name).read_text(encoding="utf-8")


def _has_trigger(text: str, needle: str) -> bool:
    for line in _statements(text):
        if line.startswith("trigger ") and needle in line:
            return True
    return False


def _col_index(token: str) -> int:
    idx = 0
    for ch in token.lower():
        idx = idx * 26 + (ord(ch) - ord("a") + 1)
    return idx


def _square_key(token: str) -> str:
    m = re.match(r"^([a-z]+)([0-9]+)$", token)
    assert m, f"not a square token: {token!r}"
    return f"{_col_index(m.group(1)) - 1},{int(m.group(2)) - 1}"


def _build_world(folder: Path, chapter: str, faction: str = "celts", time_ms: int = 0):
    """Load a campaign chapter into a headless world."""
    from soundrts import config
    from soundrts.definitions import rules
    from soundrts.lib.resource import res
    from soundrts.world import World
    from soundrts.worldclient import DirectClient

    config.mods = "aoe2"
    res.set_mods("aoe2")
    res.load_rules_and_ai()
    rules.load(res.text("rules", append=True), _read(folder, "rules.txt"))

    world = World([], 42)
    world.scenario_difficulty = "standard"
    world._parse_map(_read(folder, chapter))
    world.square_width = int(world.square_width * 1000)
    world._build_map()
    client = DirectClient("player1", None)
    client.faction = faction
    client.alliance = None
    client.interface = type("I", (), {"queue_srv_event": lambda *a, **k: None})()
    world.populate_map([client], random_starts=False)
    world._update_buckets()
    world.time = time_ms
    return world


def _run(folder: Path, chapter: str, faction: str = "celts", time_ms: int = 0):
    from soundrts.lib import sound

    sound.pause_music = lambda *a, **k: None
    world = _build_world(folder, chapter, faction, time_ms)
    for player in world.players:
        player.run_triggers()
    return world


def _player(world):
    return next(p for p in world.players if getattr(p, "is_human", False))


def _computers(world):
    return [p for p in world.players if not getattr(p, "is_human", False)]


# ---------------------------------------------------------------------------
# 1. the new trigger primitives exist
# ---------------------------------------------------------------------------
def test_new_trigger_actions_exist():
    from soundrts.worldplayerbase.triggers import TriggersMixin

    for name in (
        "lang_camera",
        "lang_flash",
        "lang_reveal_map",
        "lang_reveal_area",
        "lang_tribute",
    ):
        assert hasattr(TriggersMixin, name), f"the trigger action {name} must exist"


def test_unknown_trigger_keyword_is_warned_about(monkeypatch, caplog):
    """An unknown keyword must be logged, not silently dropped."""
    import logging

    from soundrts.worldplayerbase.triggers import TriggersMixin

    warnings = []
    monkeypatch.setattr(
        "soundrts.worldplayerbase.triggers.warning",
        lambda *args: warnings.append(args[0] % args[1:] if len(args) > 1 else args[0]),
    )

    player = TriggersMixin.__new__(TriggersMixin)
    result = player.my_eval(["campaign_defeat"])
    assert result is False
    assert warnings, "an unknown trigger keyword must produce a warning"
    assert "campaign_defeat" in warnings[0]


def test_unknown_trigger_keyword_warns_only_once():
    """A repeating trigger must not spam the log."""
    from soundrts.worldplayerbase.triggers import TriggersMixin

    calls = []

    class _Mixin(TriggersMixin):
        pass

    player = _Mixin.__new__(_Mixin)
    import soundrts.worldplayerbase.triggers as trig

    original = trig.warning
    try:
        trig.warning = lambda *a: calls.append(a[0] % a[1:] if len(a) > 1 else a[0])
        for _ in range(5):
            player.my_eval(["campaign_defeat"])
    finally:
        trig.warning = original
    assert len(calls) == 1, f"expected exactly one warning, got {len(calls)}"


# ---------------------------------------------------------------------------
# 2. camera / flash push the right payload
# ---------------------------------------------------------------------------
class _FakeClient:
    def __init__(self):
        self.events = []

    def push(self, *args):
        self.events.append(args)


def _trigger_player(world):
    """The human player, with a recording client."""
    p = _player(world)
    p.client = _FakeClient()
    return p


def test_camera_pushes_the_square_id():
    world = _build_world(WALLACE, "5.txt")
    p = _trigger_player(world)
    square = world.grid[_square_key("e4")]
    p.lang_camera(["e4"])
    assert p.client.events == [("camera", square.id)]


def test_camera_with_an_unknown_square_warns_only():
    world = _build_world(WALLACE, "5.txt")
    p = _trigger_player(world)
    p.lang_camera(["zz9"])
    assert p.client.events == [], "an unknown square must not push anything"


def test_flash_pushes_the_square_id_and_colour():
    world = _build_world(WALLACE, "5.txt")
    p = _trigger_player(world)
    square = world.grid[_square_key("e4")]
    p.lang_flash(["e4"])
    assert p.client.events == [("flash", square.id, "255,220,90")]
    p.client.events.clear()
    p.lang_flash(["e4", "10", "20", "30"])
    assert p.client.events == [("flash", square.id, "10,20,30")]


# ---------------------------------------------------------------------------
# 3. reveal_map / reveal_area
# ---------------------------------------------------------------------------
def test_reveal_map_reveals_every_square():
    world = _build_world(WALLACE, "5.txt")
    p = _player(world)
    before = set(p.observed_before_squares)
    p.lang_reveal_map([])
    after = set(p.observed_before_squares)
    assert after > before
    assert len(after) >= len(world.squares)


def test_reveal_area_reveals_a_neighbourhood():
    world = _build_world(WALLACE, "5.txt")
    p = _player(world)
    centre = world.grid[_square_key("e4")]
    p.lang_reveal_area(["e4", "1"])
    assert centre in p.observed_before_squares
    # the 3x3 neighbourhood around the centre is revealed
    for token in ("d3", "e3", "f3", "d4", "f4", "d5", "e5", "f5"):
        square = world.grid.get(_square_key(token))
        if square is None:
            continue
        assert square in p.observed_before_squares, f"{token} must be revealed"


def test_reveal_area_radius_zero_reveals_only_the_square():
    world = _build_world(WALLACE, "5.txt")
    p = _player(world)
    centre = world.grid[_square_key("e4")]
    neighbour = world.grid.get(_square_key("d4"))
    p.lang_reveal_area(["e4", "0"])
    assert centre in p.observed_before_squares
    if neighbour is not None:
        assert neighbour not in p.observed_before_squares


# ---------------------------------------------------------------------------
# 4. tribute
# ---------------------------------------------------------------------------
def test_tribute_moves_resources_between_players():
    from soundrts.lib.nofloat import PRECISION

    world = _build_world(WALLACE, "5.txt")
    p = _player(world)
    computer = _computers(world)[0]
    p.resources[0] = 1000 * PRECISION
    computer.resources[0] = 0
    p.lang_tribute(["gold", "300", "computer1"])
    assert p.resources[0] == 700 * PRECISION
    assert computer.resources[0] == 300 * PRECISION


def test_tribute_never_goes_below_zero():
    from soundrts.lib.nofloat import PRECISION

    world = _build_world(WALLACE, "5.txt")
    p = _player(world)
    computer = _computers(world)[0]
    p.resources[0] = 100 * PRECISION
    computer.resources[0] = 0
    p.lang_tribute(["gold", "300", "computer1"])
    assert p.resources[0] == 0
    assert computer.resources[0] == 100 * PRECISION


def test_tribute_from_form_moves_resources_from_the_named_payer():
    """``(tribute from computer1 gold 200 player1)`` pays the PLAYER."""
    from soundrts.lib.nofloat import PRECISION

    world = _build_world(WALLACE, "5.txt")
    p = _player(world)
    computer = _computers(world)[0]
    computer.resources[0] = 1000 * PRECISION
    p.resources[0] = 0
    p.lang_tribute(["from", "computer1", "gold", "200", "player1"])
    assert computer.resources[0] == 800 * PRECISION
    assert p.resources[0] == 200 * PRECISION


def test_tribute_with_an_unknown_resource_is_ignored():
    world = _build_world(WALLACE, "5.txt")
    p = _player(world)
    computer = _computers(world)[0]
    before_player = p.resources[0]
    before_computer = computer.resources[0]
    p.lang_tribute(["not_a_resource", "300", "computer1"])
    assert p.resources[0] == before_player
    assert computer.resources[0] == before_computer


# ---------------------------------------------------------------------------
# 5. Wallace map fixes
# ---------------------------------------------------------------------------
def test_wallace_ch7_has_no_premature_victory():
    text = _read(WALLACE, "7.txt")
    assert "register_objective 1 2" in text
    # The victory must come from the objective manager, not from a
    # premature (victory) on "has aoe_castle".
    for line in _statements(text):
        if line.startswith("trigger ") and "has aoe_castle" in line:
            assert "victory" not in line, (
                "ch7 must not fire a victory as soon as the player has a castle: "
                f"offending line: {line!r}"
            )


def test_wallace_ch7_registers_both_objectives():
    text = _read(WALLACE, "7.txt")
    assert _has_trigger(text, "add_objective 1 8626")
    assert _has_trigger(text, "add_objective 2 8627")
    assert _has_trigger(text, "objective_complete 1")
    assert _has_trigger(text, "objective_complete 2")


@pytest.mark.parametrize("chapter", ["1", "4", "5", "6", "7"])
def test_wallace_enemies_get_a_real_ai(chapter):
    text = _read(WALLACE, f"{chapter}.txt")
    assert _has_trigger(text, "(ai intermediate)"), (
        f"ch{chapter}: the English must get a real AI, otherwise they never fight"
    )


@pytest.mark.parametrize("chapter", ["5", "6", "7"])
def test_wallace_enemies_have_an_economy(chapter):
    text = _read(WALLACE, f"{chapter}.txt")
    for line in _statements(text):
        if line.startswith("computer_only") and "britons" in line:
            resources = line.split()[1:5]
            assert all(int(r) > 0 for r in resources), (
                f"ch{chapter}: the English must start with resources, got {resources}"
            )
            assert "town_center" in line, (
                f"ch{chapter}: the English need a town center to have an economy"
            )
            break
    else:
        pytest.fail(f"ch{chapter}: no British computer_only line found")


def test_wallace_enemy_ai_is_active_in_the_engine():
    """The ``(ai intermediate)`` trigger really switches the AI over."""
    for chapter in ("5", "6", "7"):
        world = _run(WALLACE, f"{chapter}.txt")
        enemies = [c for c in _computers(world) if c.faction == "britons"]
        assert enemies, f"ch{chapter}: no British computer found"
        for enemy in enemies:
            assert enemy.AI_type == "intermediate", (
                f"ch{chapter}: the British AI is {enemy.AI_type!r}, "
                "expected 'intermediate'"
            )


def test_wallace_ch6_has_a_market_and_a_trade_cart():
    text = _read(WALLACE, "6.txt")
    assert re.search(r"^player .*\bmarket\b", text, re.MULTILINE), (
        "ch6 must give the player a market so the trade / tribute UI works"
    )
    assert re.search(r"^player .*\btrade_cart\b", text, re.MULTILINE), (
        "ch6 must give the player a trade cart"
    )


def test_wallace_ch6_pays_a_tribute_for_the_relics():
    text = _read(WALLACE, "6.txt")
    assert _has_trigger(text, "tribute"), (
        "ch6 must pay the player a tribute for the relics"
    )
    assert _has_trigger(text, "tribute from computer1 gold")


def test_wallace_ch6_tribute_reaches_the_player():
    """The tribute really moves gold from the ally into the player's purse."""
    from soundrts.lib.nofloat import PRECISION

    world = _run(WALLACE, "6.txt")
    player = _player(world)
    ally = _computers(world)[0]
    ally.resources[0] = 1000 * PRECISION
    player.resources[0] = 0
    # the map action fires once per delivered relic
    player.lang_tribute(["from", "computer1", "gold", "200", "player1"])
    assert player.resources[0] == 200 * PRECISION
    assert ally.resources[0] == 800 * PRECISION


# ---------------------------------------------------------------------------
# 6. Joan of Arc map fixes
# ---------------------------------------------------------------------------
def test_joan_ch1_has_two_distinct_objectives():
    text = _read(JOAN, "1.txt")
    assert "register_objective 1 2" in text
    assert _has_trigger(text, "add_objective 1 8820")
    assert _has_trigger(text, "add_objective 2 8821")
    # The two story beats must complete the two objectives separately.
    assert _has_trigger(text, "objective_complete 1")
    assert _has_trigger(text, "objective_complete 2")


def test_joan_ch2_trade_cart_deadline_is_600_seconds():
    """``(timer 15)`` x ``timer_coefficient 40`` = 600 game seconds.

    The old ``(timer 600)`` evaluated to 600 * 40 = 24 000 s (400
    minutes), so the deadline was effectively dead code.
    """
    text = _read(JOAN, "2.txt")
    assert "timer_coefficient 40" in text
    timers = {
        tok
        for line in _statements(text)
        for tok in re.findall(r"\(timer (\d+)\)", line)
    }
    assert "15" in timers, "ch2 must use (timer 15) for the 600 s deadline"
    assert "600" not in timers, (
        "ch2 must not use (timer 600): with timer_coefficient 40 that is "
        "24 000 game seconds"
    )
    assert _has_trigger(text, "lt (count trade_cart) 6")


def test_joan_ch2_has_the_castle_age_population_cap():
    text = _read(JOAN, "2.txt")
    assert "global_population_limit 125" in text, (
        "ch2 must cap the population at 125 (the Castle Age limit)"
    )


def test_joan_ch4_uses_the_real_defeat_action():
    text = _read(JOAN, "4.txt")
    for line in _statements(text):
        assert "campaign_defeat" not in line, (
            "ch4 must not use the no-op (campaign_defeat) action: "
            f"offending line: {line!r}"
        )
    assert _has_trigger(text, "key_unit_killed npc_joan")
    for line in _statements(text):
        if "key_unit_killed npc_joan" in line:
            assert "(defeat)" in line, f"offending line: {line!r}"
        if "key_unit_killed npc_dauphin" in line:
            assert "(defeat)" in line, f"offending line: {line!r}"


def test_joan_ch4_objective_two_and_cutscene_ids():
    text = _read(JOAN, "4.txt")
    assert _has_trigger(text, "add_objective 2 8904"), (
        "ch4 objective 2 must use the dedicated id 8904"
    )
    for line in _statements(text):
        assert "8828" not in line, (
            "ch4 must not use the mismatched 8828 ('Defeat ambush'): "
            f"offending line: {line!r}"
        )
    assert _has_trigger(text, "cut_scene 8905"), (
        "ch4 must play the Reims altar cutscene 8905 on relic delivery"
    )
    for line in _statements(text):
        assert "8837" not in line, (
            "ch4 must not reuse the Orleans Castle Age cutscene 8837: "
            f"offending line: {line!r}"
        )


@pytest.mark.parametrize("lang", JOAN_LANGS)
def test_joan_tts_has_the_new_ids_in_every_language(lang):
    tts = _read(JOAN / lang, "tts.txt")
    ids = set()
    for line in tts.splitlines():
        m = re.match(r"^(\d+)\s", line)
        if m:
            ids.add(int(m.group(1)))
    assert 8904 in ids, f"{lang}: tts is missing the objective id 8904"
    assert 8905 in ids, f"{lang}: tts is missing the cutscene id 8905"


@pytest.mark.parametrize("lang", JOAN_LANGS)
def test_joan_ch2_intro_text_matches_the_de_chapter(lang):
    """The ch2 intro must describe Blois / the convoy / the Castle Age."""
    tts = _read(JOAN / lang, "tts.txt")
    line = None
    for raw in tts.splitlines():
        if raw.startswith("8811 "):
            line = raw
            break
    assert line is not None, f"{lang}: tts is missing the intro id 8811"
    assert "watch tower" not in line.lower(), (
        f"{lang}: the ch2 intro still describes the legacy watch-tower siege"
    )
    assert "8812" not in line


def test_joan_ch2_intro_mentions_blois_and_the_convoy_in_english():
    tts = _read(JOAN / "ui", "tts.txt")
    line = [x for x in tts.splitlines() if x.startswith("8811 ")][0]
    assert "Blois" in line
    assert "Orleans" in line
    assert "125" in line


# ---------------------------------------------------------------------------
# 7. the whole Joan / Wallace campaigns still build
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("chapter", ["1", "2", "3", "4", "5", "6"])
def test_joan_chapters_build(chapter):
    world = _run(JOAN, f"{chapter}.txt", faction="franks")
    assert world.players, f"ch{chapter}: the world has no players"


@pytest.mark.parametrize("chapter", ["1", "2", "3", "4", "5", "6", "7"])
def test_wallace_chapters_build(chapter):
    world = _run(WALLACE, f"{chapter}.txt", faction="celts")
    assert world.players, f"ch{chapter}: the world has no players"


# ---------------------------------------------------------------------------
# 8. the documentation
# ---------------------------------------------------------------------------
DOC_LANGS = ("zh", "en", "es", "it", "pt-BR")


def _doc(*parts):
    return ROOT.joinpath("doc_src", "src", *parts).read_text(encoding="utf-8")


@pytest.mark.parametrize("lang", DOC_LANGS)
def test_mapmaking_docs_document_the_new_primitives(lang):
    """All five documented languages must describe the new actions."""
    text = _doc(lang, "mod", "mapmaking.rst")
    for keyword in (
        "(camera",
        "(flash",
        "(reveal_map",
        "(reveal_area",
        "(tribute",
    ):
        assert keyword in text, (lang, keyword)


@pytest.mark.parametrize("lang", DOC_LANGS)
def test_mapmaking_docs_mention_the_unknown_keyword_warning(lang):
    """The docs must tell the map maker what the new warning means."""
    text = _doc(lang, "mod", "mapmaking.rst").lower()
    assert "campaign_defeat" in text, lang


@pytest.mark.parametrize("lang", DOC_LANGS)
def test_relnotes_1523_document_the_campaign_fixes_and_primitives(lang):
    """The 1.5.2.3 release notes must name every topic of this batch."""
    text = _doc(lang, "relnotes.rst")
    start = text.index("\n1.5.2.3\n")
    rest = text[start:]
    next_idx = rest.find("\n1.5.2.2\n")
    section = rest if next_idx == -1 else rest[:next_idx]
    for topic in (
        "camera",
        "flash",
        "reveal_map",
        "reveal_area",
        "tribute",
        "campaign_defeat",
        "timer 15",
        "8811",
        "8904",
        "8905",
        "ai intermediate",
        "test_campaign_script_primitives_and_fixes.py",
    ):
        assert topic in section, (lang, topic)
