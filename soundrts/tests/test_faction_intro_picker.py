# -*- coding: utf-8 -*-
"""Faction picker: G opens intro submenu (one sentence per item)."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from soundrts.faction_progress import faction_intro_lines, faction_intro_msgs

ROOT = Path(__file__).resolve().parents[2]
AOE2_CIVS = (
    "britons",
    "franks",
    "chinese",
    "mongols",
    "byzantines",
    "japanese",
    "teutons",
    "vikings",
    "vietnamese",
    "portuguese",
    "aztecs",
    "celts",
)


def test_faction_intro_msgs_from_style(monkeypatch):
    monkeypatch.setattr(
        "soundrts.definitions.style.get",
        lambda obj, attr, warn_if_not_found=True: (
            [8520] if obj == "britons" and attr == "intro" else []
        ),
    )
    assert faction_intro_msgs("britons") == [8520]
    assert faction_intro_msgs("random_faction") == []


def test_faction_intro_lines_prefer_newlines(monkeypatch):
    monkeypatch.setattr(
        "soundrts.definitions.style.get",
        lambda obj, attr, warn_if_not_found=True: (
            ["blob"] if obj == "britons" and attr == "intro" else []
        ),
    )
    monkeypatch.setattr(
        "soundrts.faction_progress._intro_part_to_text",
        lambda part: "行一。\n行二。\n行三。" if part == "blob" else "",
    )
    assert faction_intro_lines("britons") == ["行一。", "行二。", "行三。"]


def test_faction_intro_lines_fallback_sentence_split(monkeypatch):
    monkeypatch.setattr(
        "soundrts.definitions.style.get",
        lambda obj, attr, warn_if_not_found=True: (
            ["blob"] if obj == "britons" and attr == "intro" else []
        ),
    )
    monkeypatch.setattr(
        "soundrts.faction_progress._intro_part_to_text",
        lambda part: "第一句。第二句。第三句。" if part == "blob" else "",
    )
    assert faction_intro_lines("britons") == ["第一句。", "第二句。", "第三句。"]


def test_tts_continuation_lines_join_with_newline():
    from soundrts.lib.sound_cache import TextTable

    table = TextTable.__new__(TextTable)
    dict.__init__(table)
    table.phrase_translations = {}
    table._update_from_text(
        "8520 Unique unit Longbowman.\n"
        "  Unique techs Yeomen.\n"
        "  No Thumb Ring.\n"
        "8521 Other civ.\n"
    )
    assert table["8520"] == (
        "Unique unit Longbowman.\nUnique techs Yeomen.\nNo Thumb Ring."
    )
    assert table["8521"] == "Other civ."


def test_select_faction_menu_uses_on_info_not_explanation(monkeypatch):
    from soundrts import faction_progress as fp

    captured = []

    class FakeMenu:
        def __init__(self, *args, **kwargs):
            pass

        def append(self, label, action, explanation=None, on_info=None, **kwargs):
            captured.append(
                {
                    "label": label,
                    "explanation": explanation,
                    "on_info": on_info,
                }
            )

        def run(self):
            pass

    monkeypatch.setattr(fp, "rules", SimpleNamespace(factions=["britons", "franks"]))
    monkeypatch.setattr(fp, "faction_title_msgs", lambda fid: [f"title:{fid}"])
    monkeypatch.setattr(
        fp,
        "faction_intro_msgs",
        lambda fid: [f"intro:{fid}"] if fid == "britons" else [],
    )
    monkeypatch.setattr("soundrts.clientmenu.Menu", FakeMenu)
    monkeypatch.setattr("soundrts.clientmenu.CLOSE_MENU", object())

    assert fp.select_faction_menu() is None
    by_id = {
        row["label"][0]: row
        for row in captured
        if row["label"] and str(row["label"][0]).startswith("title:")
    }
    assert by_id["title:britons"]["explanation"] in (None, [])
    assert callable(by_id["title:britons"]["on_info"])
    assert by_id["title:franks"]["on_info"] is None


def test_show_faction_intro_menu_opens_sentence_items(monkeypatch):
    from soundrts import faction_progress as fp

    captured = {"title": None, "items": []}

    class FakeMenu:
        def __init__(self, title=None, *args, **kwargs):
            captured["title"] = title

        def append(self, label, action, explanation=None, **kwargs):
            captured["items"].append((label, action))

        def run(self):
            pass

    monkeypatch.setattr(
        fp,
        "faction_intro_lines",
        lambda fid: ["句一。", "句二。"] if fid == "britons" else [],
    )
    monkeypatch.setattr(fp, "faction_title_msgs", lambda fid: [f"title:{fid}"])
    monkeypatch.setattr("soundrts.clientmenu.Menu", FakeMenu)
    monkeypatch.setattr("soundrts.clientmenu.CLOSE_MENU", object())

    fp.show_faction_intro_menu("britons")
    assert captured["title"] == ["title:britons"]
    assert len(captured["items"]) == 3  # two sentences + cancel
    assert captured["items"][0][1] is None
    assert captured["items"][1][1] is None


def test_update_menu_copies_choice_extras():
    """Inviting AI rebuilds the players menu; extras must follow new indices."""
    from soundrts.clientmenu import Menu

    live = Menu(menu_type="submenu")
    live.append(["old0"], None, on_info=lambda: "old0")
    live.append(["old1"], None, on_info=lambda: "old1")
    assert live._choice_extras[0]["info"]() == "old0"

    rebuilt = Menu(menu_type="submenu")
    rebuilt.append(["pad"], None)  # shifts later indices (like invite-AI rows)
    rebuilt.append(["britons"], None, on_info=lambda: "britons")
    rebuilt.append(["byzantines"], None, on_info=lambda: "byzantines")

    live.update_menu(rebuilt)
    assert live._choice_extras.get(0) is None or live._choice_extras[0].get("info") is None
    assert live._choice_extras[1]["info"]() == "britons"
    assert live._choice_extras[2]["info"]() == "byzantines"


def _tts_ids(path: Path) -> set[str]:
    ids = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith(";"):
            continue
        parts = line.split(None, 1)
        if parts and parts[0].isdigit():
            ids.add(parts[0])
    return ids


@pytest.mark.skipif(
    not (ROOT / "mods" / "aoe2" / "ui" / "style.txt").is_file(),
    reason="aoe2 mod not present",
)
def test_aoe2_civs_have_intro_style_and_tts():
    style = (ROOT / "mods" / "aoe2" / "ui" / "style.txt").read_text(encoding="utf-8")
    en_ids = _tts_ids(ROOT / "mods" / "aoe2" / "ui" / "tts.txt")
    zh_ids = _tts_ids(ROOT / "mods" / "aoe2" / "ui-zh" / "tts.txt")
    current = None
    intros = {}
    for raw in style.splitlines():
        line = raw.strip()
        if line.startswith("def "):
            current = line.split()[1]
        elif current and line.startswith("intro "):
            intros[current] = line.split()[1]
    for civ in AOE2_CIVS:
        tid = intros.get(civ)
        assert tid, f"missing intro for {civ}"
        assert tid in en_ids, f"en tts missing {tid} ({civ})"
        assert tid in zh_ids, f"zh tts missing {tid} ({civ})"
    locale_tts = [ROOT / "mods" / "aoe2" / "ui" / "tts.txt"]
    locale_tts.extend(sorted((ROOT / "mods" / "aoe2").glob("ui-*/tts.txt")))
    for path in locale_tts:
        ids = _tts_ids(path)
        for civ in AOE2_CIVS:
            tid = intros[civ]
            assert tid in ids, f"{path.parent.name} tts missing {tid} ({civ})"
