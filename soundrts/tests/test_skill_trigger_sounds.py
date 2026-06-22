from soundrts.clientgameentity import events as events_module
from soundrts.clientgameentity.events import EntityViewEvents


class _FakeStyle:
    def __init__(self, entries):
        self.entries = entries

    def get(self, obj, attr, warn_if_not_found=True):
        return self.entries.get((obj, attr), [])


class _View(EntityViewEvents):
    def __init__(self):
        self.played = []

    def launch_event(self, sound, *args, **kwargs):
        self.played.append(("event", sound))

    def launch_event_style(self, attr, *args, **kwargs):
        self.played.append(("style", attr))

    def launch_alert(self, sound):
        self.played.append(("alert", sound))


def test_skill_triggered_prefers_skill_triggered_sound(monkeypatch):
    monkeypatch.setattr(
        events_module,
        "style",
        _FakeStyle(
            {
                ("skill_fire", "triggered"): ["fire_trigger"],
                ("skill_fire", "alert"): ["fire_alert"],
            }
        ),
    )
    view = _View()

    view.on_skill_triggered("skill_fire", "123")

    assert view.played == [("alert", "fire_trigger")]


def test_skill_triggered_falls_back_to_skill_alert_sound(monkeypatch):
    monkeypatch.setattr(
        events_module,
        "style",
        _FakeStyle({("skill_fire", "alert"): ["fire_alert"]}),
    )
    view = _View()

    view.on_skill_triggered("skill_fire", "123")

    assert view.played == [("alert", "fire_alert")]


def test_skill_triggered_without_alert_is_silent(monkeypatch):
    monkeypatch.setattr(events_module, "style", _FakeStyle({}))
    view = _View()

    view.on_skill_triggered("skill_without_sound")

    assert view.played == []


def test_skill_ready_uses_skill_ready_sound(monkeypatch):
    monkeypatch.setattr(
        events_module,
        "style",
        _FakeStyle({("skill_fire", "ready"): ["fire_ready"]}),
    )
    view = _View()

    view.on_skill_ready("skill_fire")

    assert view.played == [("alert", "fire_ready")]


def test_skill_ready_without_ready_sound_is_silent(monkeypatch):
    monkeypatch.setattr(events_module, "style", _FakeStyle({}))
    view = _View()

    view.on_skill_ready("skill_without_sound")

    assert view.played == []


def test_buff_triggered_uses_buff_specific_triggered_sound(monkeypatch):
    monkeypatch.setattr(
        events_module,
        "style",
        _FakeStyle({("debuff_mark", "triggered"): ["mark_proc"]}),
    )
    view = _View()

    view.on_buff_triggered("debuff_mark", "456")

    assert view.played == [("event", "mark_proc")]


def test_buff_triggered_without_triggered_sound_is_silent(monkeypatch):
    monkeypatch.setattr(events_module, "style", _FakeStyle({}))
    view = _View()

    view.on_buff_triggered("buff_without_sound")

    assert view.played == []
