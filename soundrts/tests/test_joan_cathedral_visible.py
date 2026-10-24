"""Regression tests for the Joan of Arc quest receivers.

Background
----------
The Reims cathedral (``npc_reims_cathedral``, Joan of Arc ch. 4 "The
Rising") is the receiver of the three holy relics.  The user reported
that no cathedral — nor any NPC able to receive items — was visible at
Reims c5.

The root cause was not cosmetic.  Three separate defects stacked:

1. **No style entry.**  ``mods/aoe2/single/Joan of Arc/ui/style.txt``
   had no ``def npc_reims_cathedral``, so ``style.get(type, "title")``
   returned ``[]``.  ``EntityView.short_title`` is built from that
   title, and ``is_visible()``
   (soundrts/clientgame/game_unit_control.py) rejects any object whose
   ``short_title`` is empty.  The cathedral was therefore neither
   Tab-selectable nor click-targetable, so the ``give`` order could not
   reach it and the chapter objective was unreachable.

2. **No map sprite.**  There is no ``ui/map/npc_reims_cathedral.png``,
   so the grid view fell back to a flat coloured rectangle.

3. **Painted as an enemy.**  The cathedral is owned by a *neutral*
   player (``computer_only ... neutral`` in 4.txt).  The grid view's
   ``_color_from_model`` consulted ``player_is_an_enemy()``, which only
   looks at alliances — so neutral owners were painted enemy red
   (230, 70, 60) and looked like an enemy stronghold.

These tests pin all three fixes, plus the engine-level fallbacks that
make them work.

Note: ``npc_cathedral`` (Orleans, ch. 2) and ``npc_d_alencon`` had the
same missing-title defect and are covered here too.
"""
from __future__ import annotations

import re
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
JOAN = REPO_ROOT / "mods/aoe2/single/Joan of Arc"
JOAN_STYLE = JOAN / "ui/style.txt"

CAMPAIGN_LANGS = (
    "ui",
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
    "ui-zh",
)

# Campaign NPC types that must have a title (i.e. be selectable).
NPC_TYPES = (
    "npc_joan",
    "npc_baudricourt",
    "npc_dauphin",
    "npc_d_alencon",
    "npc_cathedral",
    "npc_reims_cathedral",
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _style_defs() -> dict[str, dict[str, list[str]]]:
    """Parse the campaign style.txt into ``{type: {attr: [values]}}``."""
    defs: dict[str, dict[str, list[str]]] = {}
    current = None
    for raw in JOAN_STYLE.read_text(encoding="utf-8").splitlines():
        line = raw.split(";")[0].strip()
        if not line:
            continue
        m = re.match(r"^def (\w+)$", line)
        if m:
            current = m.group(1)
            defs.setdefault(current, {})
            continue
        if current is None:
            continue
        parts = line.split()
        defs[current].setdefault(parts[0], []).extend(parts[1:])
    return defs


def _tts_ids(path: Path) -> dict[int, str]:
    ids: dict[int, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split(";")[0].strip()
        if not line:
            continue
        parts = line.split()
        if parts and parts[0].isdigit():
            ids[int(parts[0])] = " ".join(parts[1:])
    return ids


def _load_aoe2():
    """Load the AoE2 mod + the Joan of Arc campaign layer.

    The cathedral's style entry (``is_a monastery``) lives in the
    *campaign* style.txt, so the campaign must be active — otherwise
    the is_a chain is empty and no sprite resolves.
    """
    import pygame

    pygame.init()
    pygame.display.set_mode((64, 64))
    from soundrts.lib.resource import res

    res.set_mods("aoe2")
    campaign = res.find_campaign("Joan of Arc")
    res.set_campaign(campaign)
    res.load_style()


# ---------------------------------------------------------------------------
# 1. the style entries exist and give every NPC a title
# ---------------------------------------------------------------------------


def test_campaign_style_defines_every_campagn_npc():
    """Every campaign NPC must have a style def with a title.

    A missing title means ``short_title == []``, which makes
    ``is_visible()`` return False — the object cannot be selected.
    """
    defs = _style_defs()
    for tn in NPC_TYPES:
        assert tn in defs, f"{tn} has no style def in the campaign style.txt"
        assert defs[tn].get("title"), (
            f"{tn} has no title -> it is not selectable "
            f"(is_visible() requires a non-empty short_title)"
        )


def test_reims_cathedral_is_a_monastery():
    """The cathedrals are monastery-class buildings.

    Besides the building behaviour, ``is_a monastery`` is what lets the
    engine's ``is_a`` sprite fallback give them the monastery artwork
    (neither cathedral has a dedicated ui/map PNG).
    """
    defs = _style_defs()
    assert "monastery" in defs["npc_reims_cathedral"].get("is_a", [])
    assert "monastery" in defs["npc_cathedral"].get("is_a", [])


def test_reims_cathedral_title_matches_its_tts_id():
    """The title id must resolve to a real tts entry saying 'cathedral'."""
    defs = _style_defs()
    title_id = int(defs["npc_reims_cathedral"]["title"][0])
    en = _tts_ids(JOAN / "ui/tts.txt")
    assert title_id in en, f"tts id {title_id} missing from ui/tts.txt"
    assert "cathedral" in en[title_id].lower()


@pytest.mark.parametrize("lang", CAMPAIGN_LANGS)
def test_every_campaign_language_defines_the_npc_titles(lang):
    """Each language's tts.txt must define the ids the style refers to.

    Otherwise the screen reader announces nothing (or the raw English
    identifier) in that language.
    """
    defs = _style_defs()
    ids = _tts_ids(JOAN / lang / "tts.txt")
    for tn in NPC_TYPES:
        title_id = int(defs[tn]["title"][0])
        assert title_id in ids, (
            f"{lang}/tts.txt is missing id {title_id} (needed by {tn})"
        )
        assert ids[title_id].strip(), f"{lang} id {title_id} is empty"


@pytest.mark.parametrize("lang", CAMPAIGN_LANGS)
def test_campaign_tts_files_have_unique_ids(lang):
    """The ids we added must not collide with an existing entry."""
    path = JOAN / lang / "tts.txt"
    seen: dict[int, int] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split(";")[0].strip()
        if not line:
            continue
        parts = line.split()
        if not parts or not parts[0].isdigit():
            continue
        tid = int(parts[0])
        seen[tid] = seen.get(tid, 0) + 1
    dupes = {tid: n for tid, n in seen.items() if n > 1}
    assert not dupes, f"{lang}/tts.txt has duplicate ids: {dupes}"


# ---------------------------------------------------------------------------
# 2. the engine-level sprite fallback
# ---------------------------------------------------------------------------


def test_get_map_sprite_falls_back_to_is_a_ancestors():
    """A type with no own PNG inherits the artwork of its is_a parent.

    ``get_map_sprite`` used to return None for any type without a
    dedicated ui/map/<type>.png, which left 569 of the 863 AoE2 rule
    types drawn as plain rectangles.
    """
    _load_aoe2()
    from soundrts.clientgame.game_hud import get_map_sprite

    # monastery itself resolves directly
    assert get_map_sprite("monastery", 16) is not None
    # a type that only exists via is_a resolves through the chain
    assert get_map_sprite("briton_barracks", 16) is not None


def test_map_sprite_fallback_helper_walks_the_is_a_chain():
    """The fallback walks style.txt's is_a chain breadth-first."""
    _load_aoe2()
    from soundrts.clientgame.game_hud import _load_map_sprite_from_ancestors

    # ``npc_reims_cathedral`` has no PNG of its own, but its style
    # is_a monastery does.
    assert _load_map_sprite_from_ancestors(
        "npc_reims_cathedral", 16, None
    ) is not None
    # an unknown type with no ancestors resolves to None (no crash)
    assert _load_map_sprite_from_ancestors("definitely_not_a_type", 16,
                                            None) is None


def test_get_map_sprite_still_prefers_its_own_png():
    """The fallback must not override a type's own artwork."""
    _load_aoe2()
    from soundrts.clientgame.game_hud import get_map_sprite

    own = get_map_sprite("monastery", 16)
    via_parent = get_map_sprite("briton_barracks", 16)
    assert own is not None and via_parent is not None
    # different types, different artwork
    assert own.get_size() == via_parent.get_size()


def test_cathedral_npc_gets_the_monastery_artwork():
    """The Reims cathedral has no PNG of its own but must be drawn.

    It inherits the monastery artwork through the style is_a chain.
    """
    _load_aoe2()
    from soundrts.clientgame.game_hud import get_map_sprite

    assert get_map_sprite("npc_reims_cathedral", 16) is not None
    assert get_map_sprite("npc_cathedral", 16) is not None


# ---------------------------------------------------------------------------
# 3. the neutral colour fix
# ---------------------------------------------------------------------------


def test_neutral_owner_is_not_painted_enemy_red():
    """Neutral-owned objects use the neutral colour, not enemy red.

    ``player_is_an_enemy`` only compares alliances, so it returns True
    for a neutral player.  The grid view has to check ``neutral`` first,
    otherwise neutral buildings (the Reims cathedral, neutral towns,
    neutral wildlife) are painted enemy red.
    """
    from soundrts.clientgamegridview import GridView

    class _Player:
        def __init__(self, neutral):
            self.neutral = neutral
            self.allied = [self]

        def player_is_an_enemy(self, other):
            # alliances only — neutral players are "enemies" by this test
            return other not in self.allied

    class _Model:
        def __init__(self, player):
            self.player = player
            self.id = 1

    gv = GridView.__new__(GridView)
    gv.interface = types.SimpleNamespace(player=_Player(neutral=False))
    gv._team_color_by_pid = {}
    gv._arch_by_player = {}

    neutral_owner = _Player(neutral=True)
    colour = gv._color_from_model(_Model(neutral_owner))
    assert colour == (180, 180, 80), (
        f"neutral owner painted {colour}, expected the neutral colour"
    )
    assert colour != (230, 70, 60)


def test_real_enemy_is_still_painted_enemy_red():
    """The neutral fix must not disarm the enemy colour."""
    from soundrts.clientgamegridview import GridView

    class _Player:
        def __init__(self):
            self.neutral = False
            self.allied = [self]

        def player_is_an_enemy(self, other):
            return other not in self.allied

    class _Model:
        def __init__(self, player):
            self.player = player
            self.id = 1

    gv = GridView.__new__(GridView)
    gv.interface = types.SimpleNamespace(player=_Player())
    gv._team_color_by_pid = {}
    gv._arch_by_player = {}

    enemy_owner = _Player()
    assert gv._color_from_model(_Model(enemy_owner)) == (230, 70, 60)


# ---------------------------------------------------------------------------
# 4. the wiring in the source files
# ---------------------------------------------------------------------------


def test_grid_view_checks_neutral_before_enemy():
    """The neutral check must come *before* the enemy check."""
    src = (REPO_ROOT / "soundrts/clientgamegridview.py").read_text(
        encoding="utf-8"
    )
    s = src.index("def _color_from_model(")
    block = src[s:s + 1600]
    assert 'getattr(p, "neutral", False)' in block
    assert block.index('getattr(p, "neutral", False)') < block.index(
        "player_is_an_enemy(me)"
    )


def test_hud_sprite_fallback_is_wired():
    """get_map_sprite must consult the is_a fallback."""
    src = (REPO_ROOT / "soundrts/clientgame/game_hud.py").read_text(
        encoding="utf-8"
    )
    s = src.index("def get_map_sprite(")
    block = src[s:s + 1200]
    assert "_load_map_sprite_from_ancestors" in block
