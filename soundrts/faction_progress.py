"""Per-faction achievement / card / rank progress (scheme D)."""

from __future__ import annotations

import re
from typing import List, Optional

from .definitions import rules
from .paths import _sanitize_mod_part

_VIEW_FACTION: Optional[str] = None


def normalize_faction_key(faction) -> Optional[str]:
    if faction is None:
        return None
    if hasattr(faction, "type_name"):
        faction = faction.type_name
    faction = str(faction).strip()
    if not faction or faction == "random_faction":
        return None
    return _sanitize_mod_part(faction) or None


def achievements_per_faction_enabled() -> bool:
    value = rules.get("parameters", "achievements_per_faction", 0)
    if value in (0, "0", False):
        return False
    if isinstance(value, list) and value:
        return str(value[0]) not in ("0", "false", "False")
    return True


def definition_matches_faction(
    defn_faction: Optional[str],
    active_faction,
    scope: Optional[str] = None,
) -> bool:
    if scope == "meta":
        return False
    if not achievements_per_faction_enabled():
        return True
    if not defn_faction:
        return scope is None
    active_key = normalize_faction_key(active_faction)
    if not active_key:
        return False
    return normalize_faction_key(defn_faction) == active_key


def set_view_faction(faction) -> Optional[str]:
    global _VIEW_FACTION
    _VIEW_FACTION = normalize_faction_key(faction)
    return _VIEW_FACTION


def get_view_faction() -> Optional[str]:
    return _VIEW_FACTION


def resolve_menu_faction(faction=None) -> Optional[str]:
    if faction is not None:
        return normalize_faction_key(faction)
    if _VIEW_FACTION:
        return _VIEW_FACTION
    factions = rules.factions
    if len(factions) == 1:
        return normalize_faction_key(factions[0])
    return None


def faction_title_msgs(faction_id: str) -> list:
    from .definitions import style

    title = style.get(faction_id, "title")
    if title:
        return list(title)
    return [faction_id]


def faction_intro_msgs(faction_id: str) -> list:
    """Optional ``intro`` from ``ui/style.txt`` (civ bonuses, unique unit/techs).

    Empty when the style has no intro. Used to decide whether G opens a blurb.
    """
    from .definitions import style

    intro = style.get(faction_id, "intro", warn_if_not_found=False)
    if intro:
        return list(intro)
    return []


_INTRO_SENTENCE_SPLIT = re.compile(r"(?<=[。．.；;!?！？])\s*")


def _intro_part_to_text(part) -> str:
    """Resolve one style intro token to display/speech text."""
    from .lib.sound_cache import sounds

    if part is None:
        return ""
    if isinstance(part, str) and not part.isdigit():
        return part.strip()
    key = str(part).strip()
    if not key:
        return ""
    text = sounds.text(key)
    if text:
        return str(text).strip()
    return key


def faction_intro_lines(faction_id: str) -> List[str]:
    """Lines for the G submenu.

    Prefer author line breaks (``\\n`` from indented tts.txt continuations).
    If a part is still one long paragraph, fall back to sentence punctuation.
    """
    lines: List[str] = []
    for part in faction_intro_msgs(faction_id):
        text = _intro_part_to_text(part)
        if not text:
            continue
        if "\n" in text:
            chunks = text.split("\n")
        else:
            chunks = _INTRO_SENTENCE_SPLIT.split(text)
        for chunk in chunks:
            s = chunk.strip()
            if s:
                lines.append(s)
    return lines


def show_faction_intro_menu(faction_id: str) -> None:
    """Blocking submenu: one sentence per item; Esc returns to the faction picker."""
    from .clientmenu import CLOSE_MENU, Menu
    from . import msgparts as mp
    from .clientmedia import voice
    from .lib.msgs import literal_text_msg

    lines = faction_intro_lines(faction_id)
    if not lines:
        voice.item(mp.BEEP)
        return

    menu = Menu(faction_title_msgs(faction_id), menu_type="submenu")
    for line in lines:
        menu.append(literal_text_msg(line), None)
    menu.append(mp.CANCEL, CLOSE_MENU)
    menu.run()


def select_faction_menu(caption_msgs: Optional[List] = None) -> Optional[str]:
    """Blocking submenu: pick a faction id, or None if cancelled."""
    from .clientmenu import CLOSE_MENU, Menu
    from . import msgparts as mp

    factions = rules.factions
    if not factions:
        return None
    if len(factions) == 1:
        return factions[0]

    picked = {"faction": None}

    def choose(faction_id):
        def _action():
            picked["faction"] = faction_id
        return _action

    menu = Menu(caption_msgs or mp.ACHIEVEMENTS, menu_type="submenu")
    for faction_id in factions:
        on_info = None
        if faction_intro_msgs(faction_id):
            on_info = lambda _fid=faction_id: show_faction_intro_menu(_fid)
        menu.append(
            faction_title_msgs(faction_id),
            choose(faction_id),
            on_info=on_info,
        )
    menu.append(mp.CANCEL, CLOSE_MENU)
    menu.run()
    return picked["faction"]
