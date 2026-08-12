"""Announce resolved faction after random roll; Alt+C faction_status."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from soundrts import msgparts as mp
from soundrts.faction_announce import (
    announce_resolved_faction,
    name_with_faction_msgs,
    owner_label_with_faction_msgs,
    player_faction_label_msgs,
    player_faction_you_are_msgs,
)


def test_you_are_msgs_only_after_random_roll(monkeypatch):
    monkeypatch.setattr(
        "soundrts.faction_progress.faction_title_msgs",
        lambda fid: [f"title:{fid}"],
    )
    monkeypatch.setattr(
        "soundrts.definitions.rules",
        SimpleNamespace(factions=["britons", "franks", "chinese"]),
    )
    p = SimpleNamespace(
        faction="britons",
        faction_was_random=True,
        _is_pure_spectator=False,
    )
    msgs = player_faction_you_are_msgs(p)
    assert msgs[: len(mp.YOU_ARE)] == list(mp.YOU_ARE)
    assert "title:britons" in msgs


def test_you_are_msgs_skip_manual_pick(monkeypatch):
    monkeypatch.setattr(
        "soundrts.faction_progress.faction_title_msgs",
        lambda fid: [f"title:{fid}"],
    )
    monkeypatch.setattr(
        "soundrts.definitions.rules",
        SimpleNamespace(factions=["britons", "franks", "chinese"]),
    )
    assert (
        player_faction_you_are_msgs(
            SimpleNamespace(
                faction="britons",
                faction_was_random=False,
                _is_pure_spectator=False,
            )
        )
        is None
    )
    # Missing flag (old saves / stubs) counts as manual.
    assert (
        player_faction_you_are_msgs(
            SimpleNamespace(faction="britons", _is_pure_spectator=False)
        )
        is None
    )


def test_you_are_msgs_skip_unresolved_random_and_spectator(monkeypatch):
    monkeypatch.setattr(
        "soundrts.faction_progress.faction_title_msgs",
        lambda fid: [f"title:{fid}"],
    )
    monkeypatch.setattr(
        "soundrts.definitions.rules",
        SimpleNamespace(factions=["britons", "franks"]),
    )
    assert (
        player_faction_you_are_msgs(
            SimpleNamespace(faction="random_faction", faction_was_random=True)
        )
        is None
    )
    assert (
        player_faction_you_are_msgs(
            SimpleNamespace(
                faction="chinese",
                faction_was_random=True,
                _is_pure_spectator=True,
            )
        )
        is None
    )


def test_you_are_msgs_skip_single_faction_even_if_random(monkeypatch):
    monkeypatch.setattr(
        "soundrts.faction_progress.faction_title_msgs",
        lambda fid: [f"title:{fid}"],
    )
    monkeypatch.setattr(
        "soundrts.definitions.rules",
        SimpleNamespace(factions=["human_faction"]),
    )
    assert (
        player_faction_you_are_msgs(
            SimpleNamespace(
                faction="human_faction",
                faction_was_random=True,
                _is_pure_spectator=False,
            )
        )
        is None
    )


def test_announce_calls_voice_info(monkeypatch):
    called = []
    flushed = []

    class V:
        def info(self, msgs):
            called.append(list(msgs))

        def flush(self):
            flushed.append(True)

    monkeypatch.setattr(
        "soundrts.faction_progress.faction_title_msgs",
        lambda fid: ["Chinese"],
    )
    monkeypatch.setattr(
        "soundrts.definitions.rules",
        SimpleNamespace(factions=["chinese", "britons"]),
    )
    announce_resolved_faction(
        SimpleNamespace(faction="chinese", faction_was_random=True),
        voice=V(),
    )
    assert called and called[0][: len(mp.YOU_ARE)] == list(mp.YOU_ARE)
    assert "Chinese" in called[0]
    assert flushed


def test_announce_silent_when_manual(monkeypatch):
    called = []

    class V:
        def info(self, msgs):
            called.append(list(msgs))

        def flush(self):
            pass

    monkeypatch.setattr(
        "soundrts.definitions.rules",
        SimpleNamespace(factions=["chinese", "britons"]),
    )
    announce_resolved_faction(
        SimpleNamespace(faction="chinese", faction_was_random=False),
        voice=V(),
    )
    assert not called


def test_faction_label_multi_civ(monkeypatch):
    monkeypatch.setattr(
        "soundrts.faction_progress.faction_title_msgs",
        lambda fid: [f"title:{fid}"],
    )
    monkeypatch.setattr(
        "soundrts.definitions.rules",
        SimpleNamespace(factions=["britons", "franks"]),
    )
    assert player_faction_label_msgs(SimpleNamespace(faction="franks")) == [
        "title:franks"
    ]
    label = owner_label_with_faction_msgs(
        SimpleNamespace(faction="franks"), ["cpu1"]
    )
    assert "title:franks" in label
    assert "cpu1" in label


def test_faction_label_silent_single_faction(monkeypatch):
    monkeypatch.setattr(
        "soundrts.definitions.rules",
        SimpleNamespace(factions=["human_faction"]),
    )
    assert (
        player_faction_label_msgs(SimpleNamespace(faction="human_faction")) is None
    )


def test_name_with_faction_for_diplomacy(monkeypatch):
    monkeypatch.setattr(
        "soundrts.faction_progress.faction_title_msgs",
        lambda fid: [f"title:{fid}"],
    )
    monkeypatch.setattr(
        "soundrts.definitions.rules",
        SimpleNamespace(factions=["britons", "chinese"]),
    )
    msgs = name_with_faction_msgs(
        SimpleNamespace(faction="britons", name=["拓海"])
    )
    assert msgs[0] == "拓海"
    assert "title:britons" in msgs
    # single-faction: name only
    monkeypatch.setattr(
        "soundrts.definitions.rules",
        SimpleNamespace(factions=["human_faction"]),
    )
    msgs2 = name_with_faction_msgs(
        SimpleNamespace(faction="human_faction", name=["拓海"])
    )
    assert msgs2 == ["拓海"] + list(mp.COMMA)


def test_say_players_and_diplo_use_faction_helper():
    audio = Path("soundrts/clientgame/game_audio.py").read_text(encoding="utf-8")
    assert "name_with_faction_msgs" in audio
    assert "def cmd_say_players" in audio
    assert "def cmd_select_alliance_candidate" in audio
    nav = Path("soundrts/clientgame/game_navigation.py").read_text(encoding="utf-8")
    assert "enqueue_enemy_faction_first_sight" not in nav


def test_announce_runs_after_opening_objective():
    text = Path("soundrts/clientgame/game_interface_base.py").read_text(encoding="utf-8")
    body = text.split("def _run_game_body_with_narratives", 1)[1]
    obj_i = body.find("play_scrolling_line(")
    fac_i = body.find("announce_resolved_faction(")
    assert obj_i >= 0 and fac_i >= 0
    assert fac_i > obj_i
    assert "faction_announce" in body


def test_bindings_have_faction_status():
    found = False
    for rel in ("res/ui/global_bindings.txt", "mods/aoe2/ui/global_bindings.txt"):
        p = Path(rel)
        if not p.is_file():
            continue
        found = True
        assert "faction_status" in p.read_text(encoding="utf-8")
    assert found, "expected at least one global_bindings.txt with faction_status"
