"""Round-trip and correctness tests for tools/i18n (tts.txt <-> gettext PO
bridge). These don't touch the game's runtime tts loading at all -- they
only cover the translator-facing tooling in tools/i18n/potts.py.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "i18n"))

from potts import (  # noqa: E402
    PoEntry,
    format_tts,
    load_msgparts_context,
    parse_po,
    parse_tts,
    write_po,
)


def test_parse_format_roundtrip_numeric_and_phrase_keys():
    entries = {
        "0": "nothing!",
        "5232": "total score",
        "objective be to eliminate the enemy": "目标为消灭敌人",
    }
    rebuilt = parse_tts(format_tts(entries))
    assert rebuilt == entries


def test_format_tts_phrase_key_uses_equals_form():
    text = format_tts({"a phrase key": "some value"})
    # a plain "key\tvalue" would let TextTable's split(None, 1) cut the key
    # in half; phrase keys must use "key = value" instead.
    assert "a phrase key = some value" in text
    assert "a phrase key\tsome value" not in text


def test_parse_tts_strips_leading_bom():
    text = "﻿; coding: utf-8\n0\tnothing!\n"
    assert parse_tts(text) == {"0": "nothing!"}


def test_parse_tts_ignores_comments_and_blank_lines():
    text = "; a comment\n\n0\tnothing!\n// also a comment\n"
    assert parse_tts(text) == {"0": "nothing!"}


def test_po_write_parse_roundtrip_with_special_characters():
    entries = [
        PoEntry(
            msgctxt="5232",
            msgid='He said "hi"\nand left.',
            msgstr="Er sagte \"hi\"\\und ging.",
            comments=["SCORE_TOTAL"],
            references=["res/ui/tts.txt:5232", "res/single/x/ui/tts.txt:5232"],
        ),
        PoEntry(msgctxt="0", msgid="nothing!", msgstr="Rien !"),
    ]
    rebuilt = parse_po(write_po(entries))
    assert len(rebuilt) == len(entries)
    for original, got in zip(entries, rebuilt):
        assert got.msgctxt == original.msgctxt
        assert got.msgid == original.msgid
        assert got.msgstr == original.msgstr
        assert got.comments == original.comments
        assert got.references == original.references


def test_parse_po_skips_obsolete_entries():
    po_text = (
        'msgid ""\nmsgstr ""\n\n'
        '#~ msgctxt "999"\n#~ msgid "old"\n#~ msgstr "alt"\n\n'
        'msgctxt "1"\nmsgid "keep"\nmsgstr "behalten"\n'
    )
    entries = parse_po(po_text)
    assert len(entries) == 1
    assert entries[0].msgctxt == "1"


def test_msgparts_context_maps_known_constants():
    context = load_msgparts_context()
    assert "SCORE_TOTAL" in context.get("5232", [])
    assert any(label.startswith("BEEP") for label in context.get("1029", []))
