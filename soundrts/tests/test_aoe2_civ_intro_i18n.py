# -*- coding: utf-8 -*-
"""AoE2 civ-intro (TTS 8520-8567) alignment across every locale.

The 42 Definitive Edition civilizations each have a spoken intro block:
  * 8520-8533 - the original DE "Return of Rome" era civilizations
  * 8540-8567 - the Lords of the West / Mountain Royals era civilizations

Every locale in ``mods/aoe2/ui*`` must ship all 42 blocks, must not leave
any line in English, and must parse cleanly through the game's own
``TextTable`` parser.
"""
from __future__ import annotations

import io
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
AOE2 = ROOT / "mods" / "aoe2"

INTRO_IDS = list(range(8520, 8534)) + list(range(8540, 8568))

LOCALES = [
    "ui",
    "ui-zh",
    "ui-be",
    "ui-cs",
    "ui-de",
    "ui-es",
    "ui-fr",
    "ui-it",
    "ui-pl",
    "ui-pt-BR",
    "ui-ru",
    "ui-sk",
    "ui-vi",
]

# Every known way of saying "team bonus" in the shipped locales.
TEAM_BONUS_RE = re.compile(
    r"(team bonus"
    r"|bonus d['’]équipe"
    r"|bonus de"
    r"|bonus di squadra"
    r"|bônus de equipe"
    r"|бонус команды"
    r"|бонус каманды"
    r"|bonus týmu"
    r"|bonus tímu"
    r"|bonus družyny"
    r"|bonus drużyny"
    r"|bonus družiny"
    r"|bonus družiny"
    r"|thưởng đội"
    r"|bonificación de equipo"
    r"|组队"
    r"|týmový bonus"
    r"|tímový bonus"
    r"|bonus drużynowy"
    r"|дружба"
    r"|team)",
    re.IGNORECASE,
)


def _read(locale: str) -> str:
    return (AOE2 / locale / "tts.txt").read_text(encoding="utf-8")


def _parse_blocks(text: str) -> dict[int, list[str]]:
    """Split a tts.txt into ``{id: [line, ...]}`` for the civ-intro ids."""
    blocks: dict[int, list[str]] = {}
    current: int | None = None
    for raw in text.split("\n"):
        stripped = raw.strip()
        if not stripped or stripped.startswith(";"):
            continue
        head = re.match(r"^(\d{4})\s+(.*\S)$", raw)
        if head:
            current = int(head.group(1))
            if current in INTRO_IDS:
                blocks.setdefault(current, []).append(head.group(2).strip())
            continue
        if raw[:1] in " \t" and current in INTRO_IDS:
            blocks[current].append(stripped)
        else:
            current = None
    return blocks


@pytest.fixture(scope="module")
def english_blocks():
    return _parse_blocks(_read("ui"))


@pytest.mark.parametrize("locale", LOCALES)
def test_locale_file_exists_and_is_utf8(locale):
    raw = (AOE2 / locale / "tts.txt").read_bytes()
    raw.decode("utf-8")  # raises on invalid UTF-8
    assert b"\x00" not in raw
    assert raw.endswith(b"\n")
    assert b"\r\n" not in raw


@pytest.mark.parametrize("locale", LOCALES)
def test_all_42_intro_blocks_present(locale):
    blocks = _parse_blocks(_read(locale))
    assert sorted(blocks) == INTRO_IDS, f"{locale}: intro id set mismatch"


@pytest.mark.parametrize("locale", LOCALES)
def test_intro_blocks_have_full_content(locale):
    blocks = _parse_blocks(_read(locale))
    for intro_id, lines in blocks.items():
        assert len(lines) >= 4, f"{locale}/{intro_id}: only {len(lines)} lines"
        assert all(line.strip() for line in lines), f"{locale}/{intro_id}: blank line"
        assert TEAM_BONUS_RE.search(lines[-1]), (
            f"{locale}/{intro_id}: last line is not the team bonus -> {lines[-1]!r}"
        )


@pytest.mark.parametrize("locale", LOCALES)
def test_no_placeholder_lines(locale):
    # These markers are locale-independent, so they are checked in every
    # locale.
    banned = ("see english", "english intro", "tbd", "fixme",
              "placeholder", "lorem ipsum")
    banned_re = re.compile(
        r"\b(%s)\b" % "|".join(re.escape(b) for b in banned), re.IGNORECASE)
    for intro_id, lines in _parse_blocks(_read(locale)).items():
        for line in lines:
            assert not banned_re.search(line), f"{locale}/{intro_id}: {line!r}"
            # "todo" is only a placeholder marker in English: in Spanish
            # and Portuguese it is the ordinary word "all" and appears in
            # the official DE text ("todo el equipo", "todo o mapa").
            if locale == "ui":
                assert not re.search(r"\btodo\b", line, re.IGNORECASE), (
                    f"{locale}/{intro_id}: {line!r}"
                )


@pytest.mark.parametrize("locale", [loc for loc in LOCALES if loc != "ui"])
def test_no_line_left_in_english(locale, english_blocks):
    """Every localised line must differ from the English source line."""
    blocks = _parse_blocks(_read(locale))
    for intro_id, lines in blocks.items():
        source = english_blocks[intro_id]
        assert len(lines) == len(source), (
            f"{locale}/{intro_id}: {len(lines)} lines vs English {len(source)}"
        )
        for line, english in zip(lines, source):
            assert line.strip() != english.strip(), (
                f"{locale}/{intro_id}: untranslated line -> {line!r}"
            )


@pytest.mark.parametrize("locale", LOCALES)
def test_game_parser_reads_every_intro(locale):
    """The shipped TextTable parser must join the multi-line blocks."""
    from soundrts.lib.sound_cache import TextTable

    text = _read(locale)

    class _Res:
        def texts(self, name, localize=True, root=None):
            return [text]

    table = TextTable(_Res(), None)
    for intro_id in INTRO_IDS:
        value = table[str(intro_id)]
        assert value, f"{locale}/{intro_id}: parser produced nothing"
        lines = [ln for ln in value.split("\n") if ln.strip()]
        assert len(lines) >= 4, f"{locale}/{intro_id}: parser kept {len(lines)} lines"


@pytest.mark.parametrize("locale", LOCALES)
def test_no_doubled_team_bonus_prefix(locale):
    """Guards against 'Bonus týmu: Tým: …' style double prefixes."""
    for intro_id, lines in _parse_blocks(_read(locale)).items():
        last = lines[-1]
        # a doubled prefix repeats the marker word twice in the same line
        markers = len(re.findall(r"(bonus|tým|tím|команд|thưởng|组队|дружб)", last, re.I))
        assert markers <= 2, f"{locale}/{intro_id}: doubled prefix -> {last!r}"
