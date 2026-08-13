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


def test_dotted_vs_stat_uses_vs_msg_and_target_title():
    name = get_stat_tts_name("mdg_vs.building")
    assert name[: len(mp.MDG_VS)] == list(mp.MDG_VS)
    assert "mdg_vs.building" not in name
    # building has a style title in base ui
    assert name[-1] != "mdg_vs.building"


def test_plain_mdg_vs_uses_translated_msg():
    """effect bonus rows use plain mdg_vs (not dotted); must not speak the raw key."""
    assert get_stat_tts_name("mdg_vs") == list(mp.MDG_VS)
    assert get_stat_tts_name("rdg_vs") == list(mp.RDG_VS)
    assert "mdg_vs" not in get_stat_tts_name("mdg_vs")


def test_other_plain_vs_stats_use_translated_msg():
    assert get_stat_tts_name("mdf_vs") == list(mp.MDF_VS)
    assert get_stat_tts_name("rdf_vs") == list(mp.RDF_VS)
    assert get_stat_tts_name("mdg_cover_vs") == list(mp.MDG_COVER_VS)
    assert get_stat_tts_name("rdg_dodge_vs") == list(mp.RDG_DODGE_VS)
    for raw in ("mdf_vs", "rdf_vs", "mdg_cover_vs", "rdg_dodge_vs"):
        assert raw not in get_stat_tts_name(raw)


def test_kill_resource_vs_uses_translated_msg():
    """Chieftains-style kill_resource_vs must not speak the raw key."""
    assert get_stat_tts_name("kill_resource_vs") == list(mp.KILL_RESOURCE_VS)
    assert "kill_resource" not in "".join(str(x) for x in get_stat_tts_name("kill_resource_vs"))
    assert "kill_gold" not in get_stat_tts_name("kill_resource_vs")
    assert get_stat_tts_name("kill_resource") == list(mp.KILL_RESOURCE)


def test_all_msgparts_vs_constants_resolve_without_raw_keys():
    """Cooldown/ready/range/crit/pierce/charge *_vs must map to message IDs."""
    from soundrts.attributes.utils import AttributeUtils
    from soundrts.worldupgrade.effect_bonus_parse import (
        _rules_stat_sets,
        split_effect_bonus_args,
    )

    vs_names = sorted(
        n.lower()
        for n in dir(mp)
        if n.endswith("_VS") and isinstance(getattr(mp, n), list)
    )
    assert "mdg_cd_vs" in vs_names
    assert "mdg_ready_vs" in vs_names
    assert "mdg_range_vs" in vs_names
    assert "mdg_crit_vs" in vs_names
    assert "mdg_piercing_vs" in vs_names
    assert "charge_mdg_vs" in vs_names
    utils = AttributeUtils(None)
    precision, _ = _rules_stat_sets()
    for name in vs_names:
        label = get_stat_tts_name(name)
        assert label == list(getattr(mp, name.upper())), name
        assert name not in label, name
        # kill_resource_vs is a 4-token form: type, resource, amount
        if name == "kill_resource_vs":
            bonus, _ = split_effect_bonus_args(
                [name, "peasant", "resource1", "5"]
            )
            assert bonus == [name, "peasant", "resource1", "5"]
            assert utils._is_precision_stat(name) is False
            continue
        root = name[:-3]
        bonus, _ = split_effect_bonus_args([name, "building", "2"])
        stored = bonus[2]
        if root in precision:
            assert stored == 2000, (name, stored)
            assert utils._is_precision_stat(name) is True, name
        else:
            # rates / int bonuses stay as raw "2"
            assert stored in (2, "2"), (name, stored)
            assert utils._is_precision_stat(name) is False, name


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
