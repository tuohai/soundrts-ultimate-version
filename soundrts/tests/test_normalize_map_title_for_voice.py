"""合作战役邀请/地图标题：章节号须按数值朗读，不能命中 tts.txt 的 "1" 等条目。"""

from soundrts import msgparts as mp
from soundrts.lib.msgs import NB_ENCODE_SHIFT, normalize_map_title_for_voice
from soundrts.randommap import (
    RandomMapConfig,
    generate_definition,
    map_voice_title,
    map_voice_title_from_parts,
)


def test_coop_chapter_title_from_network_strings():
    title = normalize_map_title_for_voice(["1", "4271", "3001"])
    assert title[0] == NB_ENCODE_SHIFT + 1
    assert title[1:] == [4271, 3001]


def test_coop_chapter_title_uses_map_name():
    title = normalize_map_title_for_voice(
        ["1", 4271, 3001], "The Legend of Raynor/1"
    )
    assert title[0] == NB_ENCODE_SHIFT + 1
    assert title[1:] == [4271, 3001]


def test_regular_map_title_unchanged():
    assert normalize_map_title_for_voice(["m1"]) == ["m1"]
    assert normalize_map_title_for_voice(["m1", 1234]) == ["m1", 1234]


def test_already_normalized_title_unchanged():
    encoded = [NB_ENCODE_SHIFT + 2, 4271, 3002]
    assert normalize_map_title_for_voice(encoded) == encoded


def test_random_map_title_converted_to_voice_tokens():
    raw = ["random_9762", "random_map", "lanes", "seed_9762"]
    title = normalize_map_title_for_voice(raw, "random_9762")
    assert title == mp.RMG_RANDOM_MAP + mp.RMG_TEMPLATE_LANES + mp.RMG_SEED + [
        NB_ENCODE_SHIFT + 9762
    ]


def test_random_map_voice_title_keeps_tts_ids():
    voice = [5033, 5059, 5058, NB_ENCODE_SHIFT + 9762]
    assert normalize_map_title_for_voice(voice, "random_9762") == voice


def test_map_voice_title_from_generated_definition():
    text, seed = generate_definition(
        RandomMapConfig(template="lanes", size="medium", seed=9762)
    )
    from soundrts.mapfile import Map

    m = Map.loads(text.encode("utf-8"), f"random_{seed}.txt")
    assert map_voice_title(m) == mp.RMG_RANDOM_MAP + mp.RMG_TEMPLATE_LANES + mp.RMG_SEED + [
        NB_ENCODE_SHIFT + seed
    ]


def test_map_voice_title_from_parts_parses_seed_prefix():
    title = map_voice_title_from_parts(
        ["random_9762", "random_map", "lanes", "seed_9762"],
        "random_9762",
    )
    assert title == mp.RMG_RANDOM_MAP + mp.RMG_TEMPLATE_LANES + mp.RMG_SEED + [
        NB_ENCODE_SHIFT + 9762
    ]


def test_server_send_invitations_normalizes_title():
    src = (
        __import__("pathlib").Path(__file__).resolve().parents[2]
        / "soundrts"
        / "serverclient.py"
    ).read_text(encoding="utf-8")
    block = src.split("def send_invitations(self):")[1].split("\n    def ")[0]
    assert "normalize_map_title_for_voice" in block
