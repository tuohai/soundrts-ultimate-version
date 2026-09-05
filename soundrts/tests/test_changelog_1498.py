"""审计：1.4.9.8 — 城镇钟、别人被淘汰/外交/目标/信号弹/集结/人口满音效。"""
from __future__ import annotations

from pathlib import Path


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_1498(lang: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("1.4.9.8")
    rest = text[start:]
    next_idx = rest.find("\n1.4.9.7")
    return rest if next_idx == -1 else rest[:next_idx]


def test_version_is_1498():
    # 1.4.9.8 notes remain after later bumps; current VERSION is owned by 1.4.9.9+.
    assert "1.4.9.8" in _source("doc_src", "src", "zh", "relnotes.rst")


def test_all_relnotes_have_1498_heading():
    for lang in ("zh", "en", "es", "it", "pt-BR"):
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert src.index("1.4.9.8") < src.index("1.4.9.7"), lang


def test_zh_relnotes_1498_session_topics():
    s = _section_1498("zh")
    assert "town_bell" in s
    assert "town_bell_range" in s
    assert "town_bell_units" in s
    assert "world_town_bell.py" in s
    assert "worldcreature.py" in s
    assert "player_defeated" in s
    assert "diplomacy_change" in s
    assert "objective_change" in s
    assert "signal_flare" in s
    assert "gather_point" in s
    assert "population_limit" in s
    assert "test_town_bell.py" in s


def test_en_es_it_pt_relnotes_1498_session_topics():
    for lang in ("en", "es", "it", "pt-BR"):
        s = _section_1498(lang)
        assert "town_bell" in s, lang
        assert "town_bell_range" in s, lang
        assert "town_bell_units" in s, lang
        assert "world_town_bell.py" in s, lang
        assert "worldcreature.py" in s, lang
        assert "player_defeated" in s, lang
        assert "diplomacy_change" in s, lang
        assert "objective_change" in s, lang
        assert "signal_flare" in s, lang
        assert "gather_point" in s, lang
        assert "population_limit" in s, lang
        assert "test_town_bell.py" in s, lang


def test_engine_wires_parameter_sfx_and_flare():
    base = _source("soundrts", "worldplayerbase", "base.py")
    trig = _source("soundrts", "worldplayerbase", "triggers.py")
    cmd = _source("soundrts", "worldplayerbase", "commands.py")
    events = _source("soundrts", "clientgameentity", "events.py")
    audio = _source("soundrts", "clientgame", "game_audio.py")
    res = _source("soundrts", "clientgame", "game_resources.py")
    iface = _source("soundrts", "clientgame", "game_interface_base.py")
    style = _source("mods", "aoe2", "ui", "style.txt")
    assert "def play_parameter_sfx" in base
    assert "player_defeated" in trig
    assert "diplomacy_change" in base
    assert "objective_change" in trig
    assert "def cmd_flare" in cmd
    assert "def cmd_flare" in audio
    assert "def srv_flare" in res
    assert "def srv_play_parameter_sfx" in iface
    assert "def on_rallying_point" in events
    assert "population_limit" in events
    assert "player_defeated playerdefeated" in style
    assert "diplomacy_change diplomacy_change" in style
    assert "objective_change objective_change" in style
    assert "signal_flare signal_flare" in style
    assert "population_limit population_limit" in style
    assert "rallying_point gather_point" in style
    bind = _source("res", "ui", "global_bindings.txt")
    assert "flare" in bind
    tts = _source("res", "ui", "tts.txt")
    assert "\n5840\t" in tts
    assert "\n5841\t" in tts
    assert "\n5842\t" in tts
