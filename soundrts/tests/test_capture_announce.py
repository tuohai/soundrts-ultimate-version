"""Capture TTS: own building lost vs own capture success."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from soundrts.lib.msgs import nb2msg


def _capture_view(local, owner, monkeypatch, spoken, played):
    import soundrts.clientgameentity.events as ev
    from soundrts.clientgameentity.events import EntityViewEvents

    class _V(EntityViewEvents):
        def launch_event_style(self, attr, alert=False, priority=0):
            played.append((attr, alert))

        def get_style(self, attr):
            if attr == "captured_lost":
                return ["1856"]
            if attr == "captured_success":
                return ["1855"]
            if attr == "captured_lost_msg":
                return ["$1", "4371"]
            if attr == "captured_success_msg":
                return ["$1", "5799"]
            return None

        type_name = "footman"
        number = 1

    v = _V()
    v.player = owner
    v.interface = SimpleNamespace(player=local)
    monkeypatch.setattr(ev.voice, "info", lambda msg, **k: spoken.append(list(msg)))
    monkeypatch.setattr(
        ev.style,
        "get",
        lambda type_name, key, warn_if_not_found=True: (
            ["8300"]
            if type_name == "town_center" and key == "title"
            else ["8301"]
            if type_name == "barracks" and key == "title"
            else None
        ),
    )
    return v


def test_captured_lost_speaks_building_number_then_been_captured(monkeypatch):
    spoken = []
    played = []
    local = SimpleNamespace(allied=[])
    local.allied = [local]
    v = _capture_view(local, local, monkeypatch, spoken, played)
    v.on_captured_lost("town_center", "1")
    assert played == [("captured_lost", True)]
    assert spoken[0] == nb2msg(1) + ["8300"] + ["4371"]


def test_captured_success_speaks_number_then_building_captured(monkeypatch):
    spoken = []
    played = []
    local = SimpleNamespace(allied=[])
    local.allied = [local]
    v = _capture_view(local, local, monkeypatch, spoken, played)
    v.on_captured_success("town_center", "1")
    assert played == [("captured_success", True)]
    assert spoken[0] == nb2msg(1) + ["8300"] + ["5799"]


def test_captured_lost_silent_tts_for_enemy_building(monkeypatch):
    spoken = []
    played = []
    local = SimpleNamespace(allied=[])
    local.allied = [local]
    enemy = SimpleNamespace(allied=[], neutral=False)
    v = _capture_view(local, enemy, monkeypatch, spoken, played)
    v.on_captured_lost("town_center")
    assert played == [("captured_lost", True)]
    assert spoken == []


def test_captured_success_silent_tts_for_enemy_capturer(monkeypatch):
    spoken = []
    played = []
    local = SimpleNamespace(allied=[])
    local.allied = [local]
    enemy = SimpleNamespace(allied=[], neutral=False)
    v = _capture_view(local, enemy, monkeypatch, spoken, played)
    v.on_captured_success("town_center")
    assert played == [("captured_success", True)]
    assert spoken == []


def test_captured_lost_speaks_for_ally_building(monkeypatch):
    spoken = []
    played = []
    local = SimpleNamespace(allied=[])
    ally = SimpleNamespace(allied=[], neutral=False)
    local.allied = [local, ally]
    v = _capture_view(local, ally, monkeypatch, spoken, played)
    v.on_captured_lost("town_center")
    assert spoken[0] == nb2msg(1) + ["8300"] + ["4371"]


def test_two_lost_barracks_speak_count(monkeypatch):
    from soundrts.clientgameentity.events import flush_pending_capture_tts

    spoken = []
    played = []
    local = SimpleNamespace(allied=[])
    local.allied = [local]
    v = _capture_view(local, local, monkeypatch, spoken, played)
    v.interface._srv_queue = object()
    v.interface._pending_capture_tts = None
    v.on_captured_lost("barracks", "1")
    v.on_captured_lost("barracks", "3")
    assert spoken == []
    assert played == [("captured_lost", True), ("captured_lost", True)]
    flush_pending_capture_tts(v.interface)
    assert spoken[0] == nb2msg(2) + ["8301"] + ["4371"]


def test_two_captured_barracks_speak_count(monkeypatch):
    from soundrts.clientgameentity.events import flush_pending_capture_tts

    spoken = []
    played = []
    local = SimpleNamespace(allied=[])
    local.allied = [local]
    v = _capture_view(local, local, monkeypatch, spoken, played)
    v.interface._srv_queue = object()
    v.interface._pending_capture_tts = None
    v.on_captured_success("barracks", "1")
    v.on_captured_success("barracks", "2")
    assert spoken == []
    flush_pending_capture_tts(v.interface)
    assert spoken[0] == nb2msg(2) + ["8301"] + ["5799"]


def test_no_number_unique_building_omits_count(monkeypatch):
    spoken = []
    played = []
    local = SimpleNamespace(allied=[], units=[])
    local.allied = [local]
    v = _capture_view(local, local, monkeypatch, spoken, played)
    v.model = SimpleNamespace(
        no_number=1,
        number=1,
        player=local,
        type_name="town_center",
        presence=True,
    )
    local.units = [v.model]
    v.on_captured_lost("town_center", "1")
    assert spoken[0] == ["8300", "4371"]


def test_tts_5799_in_all_ui_languages():
    root = Path(__file__).resolve().parents[2] / "res"
    files = [root / "ui" / "tts.txt"]
    files.extend(sorted(root.glob("ui-*/tts.txt")))
    assert len(files) >= 12
    for path in files:
        text = "\n" + path.read_text(encoding="utf-8")
        assert "\n5799\t" in text or "\n5799 " in text, path
        assert "4371" in text, path
