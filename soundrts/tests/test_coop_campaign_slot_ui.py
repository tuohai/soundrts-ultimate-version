"""合作战役：帝国时代决定版式槽位 UI（非遭遇战 invite_ai 难度）。"""
from __future__ import annotations

from pathlib import Path


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2]
        .joinpath(*path_parts)
        .read_text(encoding="utf-8")
    )


def test_coop_campaign_passes_flag_via_game_admin_menu():
    src = _source("soundrts", "serverclient.py")
    s = src.index("def _create_game(")
    block = src[s : s + 1200]
    assert 'self.push("game_admin_menu 1\\n")' in block
    assert 'self.push("coop_campaign' not in block

    src2 = _source("soundrts", "clientservermenu.py")
    s2 = src2.index("def srv_game_admin_menu(self, args):")
    block2 = src2[s2 : s2 + 400]
    assert "_is_coop_campaign" in block2


def test_coop_admin_menu_uses_slot_ui_not_skirmish_ai():
    src = _source("soundrts", "clientservermenu.py")
    s = src.index("class GameAdminMenu(_BeforeGameMenu):")
    block = src[s : s + 4500]
    assert "_add_coop_slot_entries" in block
    assert "_open_coop_slot_menu" in block
    assert "mp.COOP_SET_AI_PARTNER" in block
    assert "mp.COOP_SET_OPEN" in block
    assert 'set_coop_slot' in block
    assert "get_menu_ai_difficulties()" not in block.split("_add_coop_slot_entries")[1].split(
        "elif len(self.registered_players)"
    )[0]


def test_skirmish_invite_ai_blocked_in_coop_campaign():
    src = _source("soundrts", "serverclient.py")
    s = src.index("def cmd_invite_ai(self, args):")
    block = src[s : s + 500]
    assert "is_coop_campaign" in block
    assert "invite_computer_error" in block

    src2 = _source("soundrts", "serverroom.py")
    s2 = src2.index("def invite_computer(self, level):")
    block2 = src2[s2 : s2 + 400]
    assert "is_coop_campaign" in block2


def test_coop_ai_partner_uses_dedicated_login():
    src = _source("soundrts", "serverroom.py")
    assert '"ai_coop"' in src
    assert "coop_partner=True" in src

    src2 = _source("soundrts", "game.py")
    assert 'if level == "coop":' in src2
    assert 'level = "aggressive"' in src2


def test_set_coop_slot_command_on_server():
    src = _source("soundrts", "serverclient.py")
    assert "def cmd_set_coop_slot(self, args):" in src
    assert "set_coop_slot_ai" in src
    assert "clear_coop_slot" in src

    src2 = _source("soundrts", "serverroom.py")
    assert "def set_coop_slot_ai(self, alliance):" in src2
    assert "def clear_coop_slot(self, alliance):" in src2
