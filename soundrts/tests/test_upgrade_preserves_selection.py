"""升级后应保留客户端选中状态（源码契约测试）。"""

from pathlib import Path


def _source(*parts):
    return (Path(__file__).resolve().parents[2].joinpath(*parts)).read_text(
        encoding="utf-8"
    )


def test_upgrade_to_transfers_group_selection():
    src = _source("soundrts", "clientgameentity", "events.py")
    assert "transfer_group_selection_on_upgrade" in src
    assert "on_change_to" in src


def test_change_to_notifies_new_id_before_delete():
    src = _source("soundrts", "worldorders", "production.py")
    block = src.split("class ChangeToOrder")[1].split("class BuildOrder")[0]
    assert 'notify("change_to,%s"' in block
    assert block.index('notify("change_to,%s"') < block.index("old_unit.delete()")


def test_delete_object_records_pending_selection_removal():
    src = _source("soundrts", "clientgame", "game_navigation.py")
    assert "_note_selected_unit_removed" in src


def test_update_group_applies_pending_upgrade_selections():
    src = _source("soundrts", "clientgame", "game_unit_control.py")
    assert "apply_pending_upgrade_selections" in src
    assert "def update_group(interface):" in src
    assert src.index("apply_pending_upgrade_selections") < src.index(
        "def update_group(interface):"
    )
