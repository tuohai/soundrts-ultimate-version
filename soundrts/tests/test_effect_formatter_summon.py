"""effect_formatter：召唤描述不应污染 msgparts.SUMMON。"""

from soundrts import msgparts as mp
from soundrts.attributes.effect_formatter import EffectFormatter


class _Parent:
    def _get_stat_tts_name(self, stat):
        return [stat]

    def _is_precision_stat(self, stat):
        return False


def test_summon_description_does_not_mutate_mp_summon():
    before = list(mp.SUMMON)
    ef = EffectFormatter(_Parent())
    ef._format_effect_description(["summon", "1", "3", "zergling"])
    ef._format_effect_description(["summon", "0", "creep_tumor"])
    assert mp.SUMMON == before
