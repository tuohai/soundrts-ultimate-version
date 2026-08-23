"""Item-pickup buff TTS must use display units, not millihp."""
from soundrts.lib.nofloat import PRECISION
from soundrts.worldbuff import buff_stat_display_value


def test_td2_sword_mdg_announces_7000_not_7_million():
    # td2 ``b_sword``: ``stat mdg`` / ``v 7000`` → to_int → 7_000_000 stored.
    stored = 7000 * PRECISION
    assert buff_stat_display_value("mdg", stored, temporary=True) == 7000


def test_precision_hp_bonus_is_divided():
    assert buff_stat_display_value("hp_max", 2000, temporary=True) == 2


def test_non_precision_stat_keeps_display_units():
    # ``_apply_variation`` already // PRECISION for stats outside the set.
    assert buff_stat_display_value("heal_level", 5, temporary=True) == 5


def test_permanent_buff_divides_to_int_v():
    assert buff_stat_display_value("mdg", 7000 * PRECISION, temporary=False) == 7000
