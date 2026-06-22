import types

from soundrts import animation
from soundrts.clientgameentity import audio as audio_module
from soundrts.clientgameentity.audio import EntityViewAudio
from soundrts.definitions import parse_noise


class _FakeStyle:
    def __init__(self, entries):
        self.entries = entries

    def get(self, obj, attr, warn_if_not_found=True):
        return self.entries.get((obj, attr), [])


class _FakeNoise:
    def __init__(self, obj, style):
        self.obj = obj
        self.style = style
        self.updates = 0
        self.stopped = False

    def update(self):
        self.updates += 1

    def stop(self):
        self.stopped = True


class _View(EntityViewAudio):
    def __init__(self, buffs):
        self.model = types.SimpleNamespace(_buffs=buffs)
        self._buff_noises = None
        self._noise = None
        self.x = 0
        self.y = 0
        self.fow = False

    def get_style(self, attr):
        return []


def test_single_sound_noise_keeps_existing_empty_parse():
    assert parse_noise(["6121"]) == ()


def test_explicit_loop_noise_is_supported():
    assert parse_noise(["loop", "6121"]) == ("loop", "6121", 1, False)


def test_buff_noise_starts_updates_and_stops(monkeypatch):
    buff = types.SimpleNamespace(type_name="b_slow")
    noise_style = ("loop", "6121", 1, False)
    monkeypatch.setattr(
        audio_module,
        "style",
        _FakeStyle({("b_slow", "noise"): noise_style}),
    )
    monkeypatch.setattr(animation, "noise", lambda obj, style: _FakeNoise(obj, style))
    view = _View([buff])

    view._update_buff_noises()
    created = view._buff_noises["b_slow"]
    view._update_buff_noises()

    assert created.obj is view
    assert created.updates == 2

    view.model._buffs = []
    view._update_buff_noises()

    assert created.stopped is True
    assert view._buff_noises == {}
