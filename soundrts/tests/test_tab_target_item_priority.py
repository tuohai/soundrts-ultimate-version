"""Tab 切换目标时，当前方格有地面物品应优先选中物品。"""

from pathlib import Path


def _source(*path_parts):
    return (Path(__file__).resolve().parents[1].joinpath(*path_parts)).read_text(
        encoding="utf-8"
    )


def test_tab_target_prioritizes_ground_items_when_square_has_items():
    src = _source("clientgame", "game_unit_control.py")
    assert "def _is_ground_item(o):" in src
    assert 'getattr(o, "default_order", None) == "pickup"' in src
    assert "def _square_has_ground_items(interface):" in src
    assert "prioritize_items = _square_has_ground_items(interface)" in src
    assert "prioritize_items and _is_ground_item(o)" in src
    assert "p = 0.25" in src
    assert "_priority(interface, x, prioritize_items)" in src
