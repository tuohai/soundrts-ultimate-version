"""format_signed_number / nb2msg 应支持负整数 TTS。"""

import sys
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)
sys.argv = ["pytest"]

from soundrts.attributes.effect_formatter import EffectFormatter
from soundrts.lib.msgs import LITERAL_TEXT_PREFIX, format_signed_number, nb2msg


def test_nb2msg_negative_is_not_empty():
    result = nb2msg(-5)
    assert result
    assert LITERAL_TEXT_PREFIX + "-5" in result


def test_format_signed_number_negative_integer():
    result = format_signed_number(-10)
    assert result
    assert LITERAL_TEXT_PREFIX + "-10" in result


def test_format_signed_number_positive_integer_uses_encoding():
    result = format_signed_number(5)
    assert result
    assert result[0] > 1000000


def test_bonus_effect_negative_gather_time():
    class _Parent:
        def _get_stat_tts_name(self, stat):
            from soundrts.attributes.utils import get_stat_tts_name
            return get_stat_tts_name(stat)

        def _is_precision_stat(self, stat):
            return False

    formatter = EffectFormatter(_Parent())
    rows = formatter._format_bonus_effect_attribute_rows(["gather_time_orchard", -1])
    assert len(rows) == 1
    value_parts = rows[0][2]
    assert any("-1" in str(part) for part in value_parts)
    assert "+" not in value_parts
