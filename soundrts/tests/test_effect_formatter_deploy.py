"""effect_formatter：deploy 应显示战场效果参数，而非「召唤」。"""



import sys

import warnings



warnings.filterwarnings("ignore", category=DeprecationWarning)

sys.argv = ["pytest"]



from soundrts import msgparts as mp

from soundrts.attributes.effect_formatter import EffectFormatter

from soundrts.definitions import rules, style





class _Parent:

    def _get_stat_tts_name(self, stat):

        from soundrts.attributes.utils import get_stat_tts_name



        return get_stat_tts_name(stat)



    def _is_precision_stat(self, stat):

        return stat in ("speed", "sight_range")





def _load_starcraft_rules():

    from pathlib import Path



    root = Path(".")

    rules.load((root / "mods/starcraft/rules.txt").read_text(encoding="utf-8"))

    base_style = (root / "res/ui/style.txt").read_text(encoding="utf-8")

    mod_style = (root / "mods/starcraft/ui/style.txt").read_text(encoding="utf-8")

    style.load(base_style + "\n" + mod_style)





def test_deploy_description_uses_place_effect_not_summon():

    _load_starcraft_rules()

    ef = EffectFormatter(_Parent())

    text = ef._format_effect_description(["deploy", "5", "sc_nuclear_blast"])

    assert mp.PLACE_EFFECT[0] in text

    assert mp.SUMMON[0] not in text

    assert "7696" in text  # sc_nuclear_blast title id





def test_deploy_description_includes_harm_stats():

    _load_starcraft_rules()

    ef = EffectFormatter(_Parent())

    text = ef._format_effect_description(["deploy", "5", "sc_nuclear_blast"])

    assert mp.HARM_LEVEL[0] in text

    assert mp.HARM_RADIUS[0] in text

    assert mp.SECONDS[0] in text





def test_deploy_attribute_rows_duration_in_seconds():

    from soundrts.definitions import rules as rules_mod

    from soundrts.lib.msgs import nb2msg_float



    rules_mod.load(

        "def sc_blast\nclass effect\nharm_level 1\n"

        "def a_nuke\nclass skill\neffect deploy 15 sc_blast\n"

    )

    ef = EffectFormatter(_Parent())

    rows = ef._format_effect_attribute_rows(["deploy", "15", "sc_blast"])

    duration_row = rows[-1]

    assert duration_row[1] == ["持续"]

    assert nb2msg_float(15)[0] in duration_row[2]

    assert nb2msg_float(15000)[0] not in duration_row[2]





def test_deploy_attribute_rows_are_separate():

    _load_starcraft_rules()

    ef = EffectFormatter(_Parent())

    rows = ef._format_effect_attribute_rows(["deploy", "5", "sc_nuclear_blast"])

    assert len(rows) >= 3

    # 行结构为 (键, 标签, 值)；键列统一为空字符串，PLACE_EFFECT 作为首行标签。
    assert rows[0][0] == ""

    assert mp.PLACE_EFFECT[0] in rows[0][1]

    assert rows[1][1] == mp.HARM_LEVEL





def test_bonus_attribute_rows_split_stats():

    from soundrts.definitions import rules as rules_mod



    rules_mod.load(

        "def u_test\nclass upgrade\neffect bonus mdg 2000 speed 1500\n"

    )

    ef = EffectFormatter(_Parent())

    rows = ef._format_effect_attribute_rows(["bonus", "mdg", 2000, "speed", 1500])

    assert len(rows) == 2

    from soundrts.attributes.utils import get_stat_tts_name

    assert rows[0][1] == get_stat_tts_name("mdg")

    assert rows[1][1] == get_stat_tts_name("speed")

    assert "+" in rows[0][2]





def test_summon_attribute_rows_split_units():

    _load_starcraft_rules()

    ef = EffectFormatter(_Parent())

    rows = ef._format_effect_attribute_rows(["summon", "0", "3", "larva", "2", "egg"])

    assert len(rows) == 2

    assert rows[0][1] == mp.SUMMON

    assert rows[1][1] == mp.SUMMON





def test_summon_still_uses_summon_for_units():

    _load_starcraft_rules()

    ef = EffectFormatter(_Parent())

    text = ef._format_effect_description(["summon", "0", "3", "larva"])

    assert mp.SUMMON[0] in text

    assert mp.PLACE_EFFECT[0] not in text


def test_burst_effect_description_hides_internal_args():
    ef = EffectFormatter(_Parent())
    text = ef._format_effect_description(
        ["burst", "mdg", "5", "(delays", "0", "0.55", "1.10", "1.40", "1.65)", "(window", "2)"]
    )
    joined = " ".join(str(x) for x in text)
    assert "连击" in joined
    assert "自定义节奏" in joined
    assert "delays" not in joined
    assert "0.55" not in joined


def test_string_effect_args_are_coerced():
    """rules 解析后 effect 数值常为字符串，格式化时不应抛 TypeError。"""
    ef = EffectFormatter(_Parent())
    raise_dead = ef._format_effect_description(["raise_dead", "600", "zombie"])
    assert raise_dead
    assert str(raise_dead[0]) != "['raise_dead', '600', 'zombie']"
    heal = ef._format_effect_description(["heal", "5"])
    assert heal
    assert heal[1] == "+"

