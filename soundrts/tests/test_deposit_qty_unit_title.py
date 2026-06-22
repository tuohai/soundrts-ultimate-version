"""矿床储量播报：qty_unit_title 与仓库资源名分离。"""

import sys
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)
sys.argv = ["pytest"]

from soundrts.clientgameentity.properties import deposit_qty_unit_title


def _reset_base_game_rules():
    """Restore base-game rules/style in the global singletons.

    deposit_qty_unit_title reads the global ``style``; other test modules may
    leave the starcraft mod loaded there, so reset to base for isolation.
    """
    from soundrts import config
    from soundrts.lib.resource import res

    config.mods = ""
    res.set_map()
    res.set_mods("")
    res.load_rules_and_ai()
    res.load_style()


def test_food_carcass_qty_unit_is_meat_not_food():
    title = deposit_qty_unit_title("food_carcass", "resource3")
    assert any(str(p) == "5115" for p in title)
    assert not any(str(p) == "137" for p in title)


def test_orchard_qty_unit_is_fruit_not_food():
    title = deposit_qty_unit_title("orchard", "resource3")
    assert any(str(p) == "5116" for p in title)
    assert not any(str(p) == "137" for p in title)


def test_without_qty_unit_title_falls_back_to_stockpile_resource():
    _reset_base_game_rules()
    title = deposit_qty_unit_title("goldmine", "resource1")
    assert any(str(p) == "131" for p in title)
