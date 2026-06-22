"""狩猎动物播报：用「动物」标识，不用「中立/NPC」。"""
from __future__ import annotations

import types
from pathlib import Path

import pytest

from soundrts import msgparts as mp


def _is_wildlife_unit(model):
    return bool(getattr(model, "is_huntable", 0) or getattr(model, "herdable", 0))


def _player_is_wildlife_only(player):
    units = [u for u in getattr(player, "units", []) if getattr(u, "presence", True)]
    if not units:
        return False
    return all(_is_wildlife_unit(u) for u in units)


class _Deer:
    is_huntable = 1
    herdable = 0
    presence = True


class _Sheep:
    is_huntable = 1
    herdable = 1
    presence = True


class _QuestNpc:
    is_huntable = 0
    herdable = 0
    presence = True


def test_is_wildlife_unit_detects_huntable_and_herdable():
    assert _is_wildlife_unit(_Deer()) is True
    assert _is_wildlife_unit(_Sheep()) is True
    assert _is_wildlife_unit(_QuestNpc()) is False


def test_player_is_wildlife_only_pure_animal_player():
    player = types.SimpleNamespace(units=[_Deer(), _Sheep()])
    assert _player_is_wildlife_only(player) is True


def test_player_is_wildlife_only_mixed_player():
    player = types.SimpleNamespace(units=[_Deer(), _QuestNpc()])
    assert _player_is_wildlife_only(player) is False


def test_player_is_wildlife_only_empty_player():
    player = types.SimpleNamespace(units=[])
    assert _player_is_wildlife_only(player) is False


def test_title_uses_animal_not_neutral_npc_for_wildlife():
    src = Path("soundrts/clientgameentity/properties.py").read_text(encoding="utf-8")
    assert "def is_wildlife_unit(model):" in src
    assert "def player_is_wildlife_only(player):" in src
    assert "is_wildlife_unit(self.model) or player_is_wildlife_only(self.player)" in src
    assert "title += mp.COMMA + mp.ANIMAL + mp.COMMA" in src
    assert src.index("is_wildlife_unit(self.model)") < src.index(
        "self.player in self.interface.player.allied"
    )


def test_change_player_announces_animal_for_wildlife_player():
    src = Path("soundrts/clientgame/game_resources.py").read_text(encoding="utf-8")
    assert "player_is_wildlife_only" in src
    assert "voice.item(mp.YOU_ARE + mp.ANIMAL)" in src
    assert src.index("player_is_wildlife_only") < src.index('getattr(p, "is_script_npc", False)')


def test_place_summary_has_animals_bucket():
    src = Path("soundrts/clientgame/game_unit_control.py").read_text(encoding="utf-8")
    assert "animals = []" in src
    assert "summary(interface, animals, brief=brief) + mp.ANIMAL" in src
    assert "is_wildlife_unit(x.model)" in src


def test_animal_msgpart_defined():
    src = Path("soundrts/msgparts.py").read_text(encoding="utf-8")
    assert "ANIMAL = [5083]" in src
    tts = Path("res/ui-zh/tts.txt").read_text(encoding="utf-8")
    assert "5083 动物" in tts


def _stub_client_modules():
    import sys

    if "soundrts.clientgamenews" not in sys.modules:
        news = types.ModuleType("soundrts.clientgamenews")
        news.update_group = lambda *a, **kw: None
        sys.modules["soundrts.clientgamenews"] = news
    if "soundrts.clientgameorder" not in sys.modules:
        co = types.ModuleType("soundrts.clientgameorder")
        co.get_orders_list = lambda: []
        co.substitute_args = lambda *a, **kw: None
        sys.modules["soundrts.clientgameorder"] = co
    if "soundrts.lib.sound" not in sys.modules:
        s = types.ModuleType("soundrts.lib.sound")
        s.distance = lambda *a, **kw: 0
        s.psounds = None
        s.angle = lambda *a, **kw: 0
        sys.modules["soundrts.lib.sound"] = s


def _load_entity_view_properties():
    import sys

    _stub_client_modules()
    argv = sys.argv[:]
    sys.argv = ["soundrts-test"]
    try:
        from soundrts.clientgameentity.properties import EntityViewProperties

        return EntityViewProperties
    except Exception:
        return None
    finally:
        sys.argv = argv


def test_title_allied_wildlife_says_animal_not_ally_npc():
    evp = _load_entity_view_properties()
    if evp is None:
        pytest.skip("EntityViewProperties unavailable in test env")

    class _DeerModel:
        is_huntable = 1
        herdable = 0
        type_name = "deer"
        number = 1

        def __init__(self, player):
            self.player = player

    class _WildlifeOwner:
        neutral = True
        is_script_npc = True
        name = ["NPC"]

        def __init__(self):
            self.units = []

    owner = _WildlifeOwner()
    model = _DeerModel(owner)
    owner.units.append(model)
    observer = types.SimpleNamespace(neutral=False, is_script_npc=True)
    observer.allied = [observer, owner]

    class _StubEntityView(evp):
        is_memory = False
        speed = 0

        def __init__(self):
            self.interface = types.SimpleNamespace(player=observer)
            self.model = model
            self.player = owner
            self.number = 1
            self.type_name = "deer"

        @property
        def short_title(self):
            return ["deer_title"]

    title = _StubEntityView().title
    assert mp.ANIMAL[0] in title
    assert mp.ALLY[0] not in title
