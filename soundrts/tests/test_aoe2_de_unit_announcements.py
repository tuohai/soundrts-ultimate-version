# -*- coding: utf-8 -*-
"""AoE2 DE: every unit / technology the player can select must be speakable.

Player-visible bug
------------------
The Frankish Castle technology **Ordonnance Companies** (DE tech 1496)
silenced the order menu: focusing it announced nothing, even though the
player could read its name in the Castle's properties panel.

Cause: ``mods/aoe2/ui/style.txt`` had no ``def ordonnance_companies``
entry.  ``ClientGameOrder._get_title()`` does::

    t2 = style.get(self.type, "title")

and a type with no style definition inherits nothing, so ``t2`` came back
empty and the spoken order name was blank.

A full audit of the mod's ruleset found **11** types in the same state —
every one of them was a DE unit or technology the player can actually
train / research, so every one of them was silent in the menu:

    mounted_crossbowman        heavy_mounted_crossbowman
    flemish_militia            warrior_priest
    dragon_ship                savar
    flaming_camel              bulgarian_mill
    ordonnance_companies       cranequins
    pirotechnia

This module locks the fix down: each of them must resolve a spoken
``title``, that title must exist in **every** shipped locale's
``tts.txt``, and the Chinese title must equal the Chinese name used in
the civilization description (so the menu and the civ intro never
disagree).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "mods" / "aoe2"

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

# type name -> expected title id.  The ids are the ones allocated in
# mods/aoe2/ui*/tts.txt (9122-9131); ``bulgarian_mill`` deliberately
# reuses the generic mill title (8314) so every mill sounds the same.
NEW_STYLE_TYPES = {
    "ordonnance_companies": 9122,
    "cranequins": 9123,
    "pirotechnia": 9124,
    "mounted_crossbowman": 9125,
    "heavy_mounted_crossbowman": 9126,
    "flemish_militia": 9127,
    "flaming_camel": 9128,
    "warrior_priest": 9129,
    "dragon_ship": 9130,
    "savar": 9131,
    "bulgarian_mill": 8314,
}

# The units among the above must also be reachable through the layered
# hotkey pages, otherwise the player could not select them at all.
UNIT_HOTKEYS = {
    "mounted_crossbowman": "soldier3",
    "heavy_mounted_crossbowman": "soldier3",
    "flemish_militia": "soldier1",
    "flaming_camel": "soldier4",
    "warrior_priest": "soldier6",
    "dragon_ship": "soldier7",
    "savar": "soldier3",
}


def _read_tts(path: Path) -> dict[int, str]:
    table: dict[int, str] = {}
    for raw in path.read_text(encoding="utf-8").split("\n"):
        line = raw.split(";", 1)[0].strip()
        m = re.match(r"^(\d+)\s+(.*)$", line)
        if m:
            table.setdefault(int(m.group(1)), m.group(2))
    return table


@pytest.fixture(scope="module")
def aoe2_style():
    from soundrts import config
    from soundrts.definitions import style
    from soundrts.lib.resource import res

    old_mods = res.mods or ""
    old_config_mods = getattr(config, "mods", "")
    config.mods = "aoe2"
    res.set_mods("aoe2")
    res.load_rules_and_ai()
    res.load_style()
    yield style
    config.mods = old_config_mods
    res.set_mods(old_mods)
    res.load_rules_and_ai()
    res.load_style()


@pytest.mark.parametrize("type_name,title_id", sorted(NEW_STYLE_TYPES.items()))
def test_every_new_type_has_a_spoken_title(aoe2_style, type_name, title_id):
    """The regression: a missing style def meant a silent order menu."""
    title = aoe2_style.get(type_name, "title", warn_if_not_found=False)
    assert title, "%s has no spoken title in style.txt" % type_name
    assert list(title) == [str(title_id)], (type_name, title, title_id)


@pytest.mark.parametrize("locale", LOCALES)
def test_every_new_title_exists_in_every_locale(locale):
    """A title id without text would still be silent in that language."""
    table = _read_tts(MOD / locale / "tts.txt")
    missing = [
        (name, tid)
        for name, tid in NEW_STYLE_TYPES.items()
        if tid not in table or not table[tid].strip()
    ]
    assert not missing, "%s: missing titles %s" % (locale, missing)


@pytest.mark.parametrize("type_name", sorted(UNIT_HOTKEYS))
def test_every_new_unit_is_hotkey_reachable(aoe2_style, type_name):
    """The unit must be selectable through the layered hotkey pages."""
    keyboard = aoe2_style.get(type_name, "keyboard", warn_if_not_found=False)
    assert keyboard, "%s has no keyboard slot" % type_name
    assert UNIT_HOTKEYS[type_name] in keyboard, (type_name, keyboard)


def test_ordonnance_companies_is_the_frank_castle_tech():
    """It is a real Frankish Castle-age technology, not a phantom entry."""
    from soundrts.definitions import Rules

    r = Rules()
    r.load(
        (ROOT / "res" / "rules.txt").read_text(encoding="utf-8"),
        (MOD / "rules.txt").read_text(encoding="utf-8"),
    )
    assert r.unit_class("ordonnance_companies") is not None
    assert "ordonnance_companies" in (r.get("frank_castle", "can_research") or [])


def test_chinese_menu_titles_match_the_civ_description():
    """The Chinese menu label must equal the name in the civ intro.

    This is the same rule the Goths/Huskarl test enforces, extended to the
    seven civs that advertise one of the new DE units or technologies.
    """
    en_blocks: dict[int, str] = {}
    zh_blocks: dict[int, str] = {}
    en_tts = _read_tts(MOD / "ui" / "tts.txt")
    zh_tts = _read_tts(MOD / "ui-zh" / "tts.txt")

    def blocks(path: Path) -> dict[int, str]:
        out: dict[int, str] = {}
        current: int | None = None
        for raw in path.read_text(encoding="utf-8").split("\n"):
            stripped = raw.strip()
            if not stripped or stripped.startswith(";"):
                continue
            head = re.match(r"^(\d{4})\s+(.*)$", raw)
            if head:
                current = int(head.group(1))
                out.setdefault(current, head.group(2).strip())
                continue
            if raw[:1] in " \t" and current is not None:
                out[current] += " " + stripped
            else:
                current = None
        return out

    en_blocks = blocks(MOD / "ui" / "tts.txt")
    zh_blocks = blocks(MOD / "ui-zh" / "tts.txt")

    EN_UNIT = re.compile(r"Unique units?\s+(.+?)\.", re.S)
    EN_TECH = re.compile(r"Unique techs?\s+(.+?)\.", re.S)
    ZH_UNIT = re.compile(r"独特单位：(.+?)。")
    ZH_TECH = re.compile(r"独特科技：(.+?)。")
    ZH_SPLIT = re.compile(r"[、,，/]")

    name_to_tid: dict[str, int] = {}
    for tid, label in en_tts.items():
        name_to_tid.setdefault(label.strip().lower(), tid)

    mismatches = []
    for cid in sorted(en_blocks):
        if not 8520 <= cid <= 8567:
            continue
        for en_rx, zh_rx in ((EN_UNIT, ZH_UNIT), (EN_TECH, ZH_TECH)):
            me = en_rx.search(en_blocks[cid])
            mz = zh_rx.search(zh_blocks.get(cid, ""))
            if not me or not mz:
                continue
            en_names = [n.strip() for n in re.split(r",| and ", me.group(1)) if n.strip()]
            zh_names = [n.strip() for n in ZH_SPLIT.split(mz.group(1)) if n.strip()]
            if len(en_names) != len(zh_names):
                continue
            for en, zh in zip(en_names, zh_names):
                tid = name_to_tid.get(en.lower())
                if tid is None:
                    continue
                menu = zh_tts.get(tid, "")
                if menu != zh:
                    mismatches.append(
                        "tts %d (%s): description says %r, menu says %r"
                        % (tid, en, zh, menu)
                    )
    assert not mismatches, "\n".join(mismatches)
