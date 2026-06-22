"""get_stat_tts_name：采集类属性应动态组合 style 标题，而非硬编码果园/尸体。"""

import sys
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)
sys.argv = ["pytest"]

from soundrts import msgparts as mp
from soundrts.attributes.utils import get_stat_tts_name
from soundrts.level_up_stats import LEVEL_UP_STAT_ATTRS


def test_gather_time_orchard_uses_deposit_title():
    name = get_stat_tts_name("gather_time_orchard")
    assert mp.GATHER_TIME[0] in name
    assert "_" in name
    assert 4661 in name  # orchard title in res/ui/style.txt
    assert 5108 not in name


def test_gather_time_food_carcass_uses_deposit_title():
    name = get_stat_tts_name("gather_time_food_carcass")
    assert mp.GATHER_TIME[0] in name
    assert 4932 in name  # food_carcass title
    assert 5107 not in name


def test_gather_time_unknown_deposit_falls_back_to_type_name():
    name = get_stat_tts_name("gather_time_granary")
    assert mp.GATHER_TIME[0] in name
    assert "granary" in name


def test_gather_qty_food_carcass_uses_deposit_title():
    name = get_stat_tts_name("gather_qty_food_carcass")
    assert mp.GATHER_QTY[0] in name
    assert 4932 in name
    assert 5109 not in name


def test_food_deposit_qty_uses_resource3_and_deposit_qty_suffix():
    name = get_stat_tts_name("food_deposit_qty")
    assert 137 in name  # resource3 title (food)
    assert mp.FOOD_DEPOSIT_QTY[0] in name


def test_level_up_stats_use_message_ids_not_raw_names():
    for stat in LEVEL_UP_STAT_ATTRS:
        name = get_stat_tts_name(stat)
        assert isinstance(name, list) and name, stat
        assert isinstance(name[0], int), f"{stat} -> {name!r}"


def test_revival_time_and_charge_mdg_per_level_labels():
    assert get_stat_tts_name("revival_time") == mp.REVIVAL_TIME
    assert get_stat_tts_name("charge_mdg") == mp.CHARGE_MDG


def test_level_up_tts_localized_in_major_language_packs():
    from pathlib import Path

    from soundrts import msgparts as mp

    def load_tts(path: Path) -> dict[str, str]:
        table: dict[str, str] = {}
        if not path.exists():
            return table
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith(";"):
                continue
            parts = line.split(None, 1)
            if len(parts) == 2 and parts[0].isdigit():
                table[parts[0]] = parts[1]
        return table

    ids: set[str] = set()
    for stat in LEVEL_UP_STAT_ATTRS:
        for mid in get_stat_tts_name(stat):
            if isinstance(mid, int):
                ids.add(str(mid))
    for mid in mp.PER_LEVEL + mp.GROWTH:
        ids.add(str(mid))

    root = Path(__file__).resolve().parents[2] / "res"
    en = load_tts(root / "ui" / "tts.txt")
    for lang_dir in ("ui-zh", "ui-fr", "ui-de", "ui-ru"):
        merged = dict(en)
        merged.update(load_tts(root / lang_dir / "tts.txt"))
        missing = [msg_id for msg_id in ids if msg_id not in merged]
        assert not missing, f"{lang_dir} missing level-up TTS ids: {missing[:5]}"
        assert "_" not in merged["4717"], lang_dir
