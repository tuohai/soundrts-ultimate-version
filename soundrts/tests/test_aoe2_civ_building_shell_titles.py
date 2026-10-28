# -*- coding: utf-8 -*-
"""Every AoE2 civ-specific shell must be speakable and reachable by hotkey.

Regression test for: "玩骡马文明时，让村民建造完兵营后，按 w 切到兵营的时候
不播报" (playing as Romans, building a barracks and pressing W announced
nothing).

Cause: ``rules.txt`` gives every civ its own shell — a building shell
(``barracks roman_barracks``) or a unit skin (``knight japanese_knight``) —
but ``mods/aoe2/ui/style.txt`` only had style definitions for britons..turks.
A shell with no style definition inherits nothing, so it had:

* no ``title``    -> the unit/building had no name to speak, and
* no ``keyboard`` -> the W / soldier hotkeys never reached it.

The fix adds ``def <shell>`` + ``is_a <semantic base>`` entries so both the
spoken title and the keyboard slot are inherited from the base type.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

# Rule classes that make a type a selectable entity on the map. A civ shell
# with one of these classes must be speakable and hotkey-reachable.
# ("phase" — feudal_age / imperial_age — is an age upgrade, not a unit, so it
# is deliberately excluded.)
UNIT_CLASSES = frozenset({"building", "soldier", "worker"})

# Rule classes that are buildings (used to tell a building shell from a unit
# skin when auditing the civ race table).
BUILDING_ROOTS = frozenset(
    {
        "building",
        "house",
        "wall",
        "gate",
        "wonder",
        "outpost",
        "barracks",
        "townhall",
    }
)

# Race-table keys that are not "this civ's version of unit X" slots.
NON_SLOT_KEYS = frozenset({"is_a", "expanded_is_a", "class"})


@pytest.fixture(scope="module")
def aoe2_loaded():
    from soundrts import config
    from soundrts.clientgameorder import update_orders_list
    from soundrts.definitions import rules, style
    from soundrts.lib.resource import res

    # Restore from ``res.mods`` (the resource layers actually in effect), not
    # from ``config.mods``: other test modules set ``config.mods = "aoe2"``
    # without restoring it, so ``config.mods`` may already be polluted when
    # this fixture runs. Trusting it would leave the aoe2 rules loaded for
    # every later test module (e.g. the bridge tests, which need the base
    # ``res/rules.txt`` classes).
    old_mods = res.mods or ""
    old_config_mods = getattr(config, "mods", "")
    config.mods = "aoe2"
    res.set_mods("aoe2")
    res.load_rules_and_ai()
    res.load_style()
    update_orders_list()
    yield rules, style
    config.mods = old_config_mods
    res.set_mods(old_mods)
    # Always reload the base rules/style (not only when a mod was active) and
    # rebuild the cached order list, which is derived from style's "index"
    # attributes — a stale cache makes later tests see the wrong menu.
    res.load_rules_and_ai()
    res.load_style()
    update_orders_list()


def _ancestry(rules, name, seen=None):
    """All rule classes *name* inherits from (including itself)."""
    seen = seen if seen is not None else set()
    if name in seen or name not in rules._dict:
        return frozenset()
    seen.add(name)
    out = {name}
    for parent in rules._dict[name].get("is_a") or ():
        out |= _ancestry(rules, parent, seen)
    return frozenset(out)


def _is_building(rules, name):
    return bool(_ancestry(rules, name) & BUILDING_ROOTS)


def _is_map_unit(rules, name):
    """True for a type that exists on the map (building / soldier / worker)."""
    classes = rules._dict.get(name, {}).get("class") or ()
    if isinstance(classes, str):
        classes = (classes,)
    return bool(set(classes) & UNIT_CLASSES)


def _civ_shells(rules):
    """Yield (civ, slot, shell, is_building) for every civ-specific shell.

    The civ race table (``def japanese`` / ``class race``) maps a semantic
    slot (``barracks``, ``knight``, ...) to that civ's own type name. Those
    type names are the shells: they exist in ``rules.txt`` but used to be
    missing from ``style.txt``.
    """
    for civ in rules.factions:
        race = rules._dict.get(civ) or {}
        for slot, raw in race.items():
            if slot in NON_SLOT_KEYS:
                continue
            if not isinstance(raw, (list, tuple)) or not raw:
                continue
            shell = raw[0]
            if not isinstance(shell, str) or shell not in rules._dict:
                continue
            if not _is_map_unit(rules, shell):
                # Ages / phases are not map entities — they have no title to
                # speak and no hotkey slot.
                continue
            yield civ, slot, shell, _is_building(rules, shell)


def _civ_building_shells(rules):
    for civ, slot, shell, is_building in _civ_shells(rules):
        if is_building:
            yield civ, slot, shell


def _civ_unit_shells(rules):
    for civ, slot, shell, is_building in _civ_shells(rules):
        if not is_building:
            yield civ, slot, shell


def test_every_civ_building_shell_has_a_spoken_title(aoe2_loaded):
    """A civ shell must resolve a title, else the building is silent."""
    rules, style = aoe2_loaded
    missing = [
        (civ, slot, shell)
        for civ, slot, shell in _civ_building_shells(rules)
        if not style.get(shell, "title", warn_if_not_found=False)
    ]
    assert not missing, (
        "style.txt missing title for civ building shells: %s "
        "(add `def <shell>` + `is_a <base>` to mods/aoe2/ui/style.txt)" % missing
    )


def test_every_civ_building_shell_has_a_keyboard_slot(aoe2_loaded):
    """A civ shell must resolve a keyboard slot, else W cannot select it."""
    rules, style = aoe2_loaded
    missing = [
        (civ, slot, shell)
        for civ, slot, shell in _civ_building_shells(rules)
        if not style.get(shell, "keyboard", warn_if_not_found=False)
    ]
    assert not missing, (
        "style.txt missing keyboard for civ building shells: %s" % missing
    )


def test_every_civ_unit_shell_has_a_spoken_title(aoe2_loaded):
    """A civ unit skin (e.g. japanese_knight) must resolve a title too."""
    rules, style = aoe2_loaded
    missing = [
        (civ, slot, shell)
        for civ, slot, shell in _civ_unit_shells(rules)
        if not style.get(shell, "title", warn_if_not_found=False)
    ]
    assert not missing, (
        "style.txt missing title for civ unit shells: %s "
        "(add `def <shell>` + `is_a <base>` to mods/aoe2/ui/style.txt)" % missing
    )


def test_every_civ_unit_shell_has_a_keyboard_slot(aoe2_loaded):
    """A civ unit skin must resolve a keyboard slot, else it is unreachable."""
    rules, style = aoe2_loaded
    missing = [
        (civ, slot, shell)
        for civ, slot, shell in _civ_unit_shells(rules)
        if not style.get(shell, "keyboard", warn_if_not_found=False)
    ]
    assert not missing, "style.txt missing keyboard for civ unit shells: %s" % missing


def test_roman_barracks_is_announced_and_w_reachable(aoe2_loaded):
    """The reported bug: Romans (骡马 / 罗马) barracks must speak on W."""
    from soundrts.clientgame.game_unit_control import _arrange

    rules, style = aoe2_loaded
    shell = rules.get("romans", "barracks")[0]
    assert shell == "roman_barracks"

    title = style.get(shell, "title", warn_if_not_found=False)
    assert title, "roman_barracks has no title"
    # The spoken name is the generic 兵营, same as every other civ.
    assert title == style.get("barracks", "title")

    keyboard = style.get(shell, "keyboard", warn_if_not_found=False)
    assert "building" in keyboard

    types_, _local, _idle, _even = _arrange(("building",))
    assert shell in types_, "W (select_unit 1 building) cannot reach roman_barracks"


@pytest.mark.parametrize(
    "civ,shell",
    [
        ("romans", "roman_barracks"),
        ("bulgarians", "bulgarian_barracks"),
        ("khmer", "khmer_barracks"),
        ("armenians", "armenian_barracks"),
        ("georgians", "georgian_barracks"),
        ("lithuanians", "lithuanian_barracks"),
        ("incas", "incan_barracks"),
        ("tatars", "tartar_barracks"),
        ("berbers", "berber_barracks"),
        ("ethiopians", "ethiopian_barracks"),
        ("malays", "malay_barracks"),
        ("burmese", "burmese_barracks"),
        ("burgundians", "burgundian_barracks"),
        ("sicilians", "sicilian_barracks"),
    ],
)
def test_late_added_civ_barracks_share_the_generic_title(aoe2_loaded, civ, shell):
    """Late-added civs speak the same 兵营 as britons, with a W slot."""
    rules, style = aoe2_loaded
    assert rules.get(civ, "barracks")[0] == shell
    assert style.get(shell, "title", warn_if_not_found=False) == style.get(
        "barracks", "title"
    )
    assert "building3" in style.get(shell, "keyboard", warn_if_not_found=False)


@pytest.mark.parametrize(
    "civ,shell",
    [
        ("japanese", "japanese_knight"),
        ("turks", "turk_knight"),
        ("vikings", "viking_knight"),
        ("persians", "persian_knight"),
        ("slavs", "slav_knight"),
        ("magyars", "magyar_knight"),
        ("koreans", "korean_knight"),
        ("italians", "italian_knight"),
        ("bohemians", "bohemian_knight"),
        ("cumans", "cuman_knight"),
        ("huns", "hun_knight"),
        ("hindustanis", "hindustani_knight"),
        ("poles", "polish_knight"),
        ("portuguese", "portuguese_knight"),
        ("spanish", "spanish_knight"),
        ("vietnamese", "vietnamese_knight"),
    ],
)
def test_civ_knight_shells_share_the_generic_title(aoe2_loaded, civ, shell):
    """Per-civ knight skins speak the same 骑士 and sit in the soldier3 slot."""
    rules, style = aoe2_loaded
    assert rules.get(civ, "knight")[0] == shell
    assert style.get(shell, "title", warn_if_not_found=False) == style.get(
        "aoe_knight", "title"
    )
    assert "soldier3" in style.get(shell, "keyboard", warn_if_not_found=False)


def test_civ_building_shell_titles_exist_in_the_tts_tables(aoe2_loaded):
    """Every title id a civ shell uses must have text in the zh / en tables."""

    rules, style = aoe2_loaded

    def load(path):
        table = {}
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.split(";", 1)[0].strip()
                m = re.match(r"^(\d+)\s+(.*)$", line)
                if m:
                    table[int(m.group(1))] = m.group(2)
        return table

    zh = load(ROOT / "mods" / "aoe2" / "ui-zh" / "tts.txt")
    en = load(ROOT / "mods" / "aoe2" / "ui" / "tts.txt")

    missing = []
    for _civ, _slot, shell, _is_bld in _civ_shells(rules):
        for raw in style.get(shell, "title", warn_if_not_found=False) or []:
            if not str(raw).isdigit():
                continue
            tid = int(raw)
            if tid not in zh or tid not in en:
                missing.append((shell, tid))
    assert not missing, "civ shell titles missing from tts.txt: %s" % missing
