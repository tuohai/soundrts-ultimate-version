"""Menu first-letter jump must land on the first match, not skip to the second.

Regression: pressing "m" selected m2 (and "p" selected pm2) because
(1) key-repeat / keep_key re-queued multiple KEYDOWNs, and/or
(2) a remembered map duplicate at index 0 shadowed the real first match.
"""
from __future__ import annotations

import os
import sys
import warnings as _warnings

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

_saved_argv = sys.argv
sys.argv = [sys.argv[0]]
with _warnings.catch_warnings():
    _warnings.simplefilter("ignore")
    try:
        from soundrts import clientmenu as cm
    finally:
        sys.argv = _saved_argv


class _FakeSounds:
    def translate_sound_number(self, sn):
        return str(sn)


def _silent_menu(choices, default_choice_index=0):
    menu = cm.Menu(choices=choices, default_choice_index=default_choice_index)
    menu._say_choice = lambda: None  # type: ignore[method-assign]
    return menu


def test_first_letter_from_fresh_lands_on_first_match(monkeypatch):
    monkeypatch.setattr(cm, "sounds", _FakeSounds())
    choices = [
        (["random"], None),
        (["jl1"], None),
        (["m1"], None),
        (["m2"], None),
        (["pm1"], None),
        (["pm2"], None),
        (["quit"], None),
    ]
    menu = _silent_menu(choices)

    menu._select_next_choice("m")
    assert choices[menu.choice_index][0][0] == "m1"

    menu.choice_index = None
    menu._select_next_choice("p")
    assert choices[menu.choice_index][0][0] == "pm1"


def test_first_letter_does_not_prefer_remembered_default(monkeypatch):
    """Even if default is a later 'm' map, first 'm' press still selects m1."""
    monkeypatch.setattr(cm, "sounds", _FakeSounds())
    choices = [
        (["random"], None),
        (["m1"], None),
        (["m2"], None),
        (["quit"], None),
    ]
    menu = _silent_menu(choices, default_choice_index=2)  # m2 remembered

    menu._select_next_choice("m")
    assert choices[menu.choice_index][0][0] == "m1"


def test_repeated_letter_cycles_to_next_match(monkeypatch):
    monkeypatch.setattr(cm, "sounds", _FakeSounds())
    choices = [
        (["m1"], None),
        (["m2"], None),
        (["m3"], None),
    ]
    menu = _silent_menu(choices)

    menu._select_next_choice("m")
    assert choices[menu.choice_index][0][0] == "m1"
    menu._select_next_choice("m")
    assert choices[menu.choice_index][0][0] == "m2"
    menu._select_next_choice("m")
    assert choices[menu.choice_index][0][0] == "m3"


def test_first_letter_uses_map_name_without_tts_lookup(monkeypatch):
    """Map titles start with the filename; must not call translate_sound_number."""
    calls = []

    class _BoomSounds(_FakeSounds):
        def translate_sound_number(self, sn):
            calls.append(sn)
            raise AssertionError("translate_sound_number should not be used")

        def text(self, key):
            return None

    monkeypatch.setattr(cm, "sounds", _BoomSounds())
    assert cm._first_letter((["pm1"], None)) == "p"
    assert cm._first_letter((["m1", 5012, 3001], None)) == "m"
    assert calls == []


def test_remember_sets_default_index_without_duplicate(tmp_path, monkeypatch):
    monkeypatch.setattr(cm, "sounds", _FakeSounds())
    path = tmp_path / "mapmenu.txt"
    path.write_text(repr(["m2"]), encoding="utf-8")
    monkeypatch.setattr(cm, "_remember_path", lambda _name: str(path))

    menu = cm.Menu(remember="mapmenu")
    menu._say_choice = lambda: None  # type: ignore[method-assign]
    menu.append(["random"], None)
    menu.append(["m1"], None)
    menu.append(["m2"], None)

    assert len(menu.choices) == 3
    assert menu.default_choice_index == 2
    assert menu.choices[0][0][0] == "random"

    menu._select_next_choice("m")
    assert menu.choices[menu.choice_index][0][0] == "m1"


def test_soundrts2_first_letter_decodes_nb2msg_chapter_prefix(monkeypatch):
    """soundrts2 campaign chapters use nb2msg(n); digit keys must jump by number."""
    import warnings

    _saved = sys.argv
    sys.argv = [sys.argv[0]]
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            import soundrts2.clientmenu as cm2
            from soundrts2.lib.msgs import nb2msg
    finally:
        sys.argv = _saved

    class _LocalSounds(_FakeSounds):
        def text(self, key):
            if key in ("4271", "3001"):
                return "章节"
            return None

    monkeypatch.setattr(cm2, "sounds", _LocalSounds())
    choices = [
        (nb2msg(1) + [4271, 3001], None),
        (nb2msg(2) + [4271, 3001], None),
        (nb2msg(10) + [4271, 3001], None),
    ]
    menu = cm2.Menu(choices=choices, default_choice_index=0)
    menu._say_choice = lambda: None  # type: ignore[method-assign]
    menu._select_next_choice("2")
    assert menu.choice_index == 1
    menu.choice_index = None
    menu._select_next_choice("1")
    assert menu.choice_index == 0
    menu._select_next_choice("1")
    assert menu.choice_index == 2
