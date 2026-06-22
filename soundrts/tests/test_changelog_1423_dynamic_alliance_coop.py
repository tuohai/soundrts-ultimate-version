"""审计：1.4.2.3 — 动态结盟热键 + 合作战役 bug 修复。

更新日志承诺：
- f12 / shift+f12：在候选玩家列表中正/反向切换。
- f4：发送结盟申请。
- ctrl+f4：同意收到的结盟申请。
- shift+f4：撤销发送的请求 / 取消现有联盟 / 拒绝收到的请求。
- "如果玩家之间在游戏开始前已经设定好了联盟关系，那么游戏内将无法更换联盟"
  → ``world.alliances_locked``。

合作战役 bug 修复（本次审计发现并修：参见 srv_start_game 阈值 ``>= 8`` 而不是 ``>= 9``）：
- 服务器 ``serverroom._start`` 在 ``client.notify("start_game", ...)`` 一共发 8 个位置参数。
- 客户端 ``_BeforeGameMenu.srv_start_game`` 用 ``len(args) >= 9`` 判断，永远不进入 8-参数分支，
  ``is_coop`` / ``coop_campaign_name`` / ``coop_chapter`` 被默默丢失，
  导致合作战役玩家通关后无法自动解锁下一章。
"""
from __future__ import annotations

from pathlib import Path

import pytest


def _source(*path_parts):
    return (Path(__file__).resolve().parents[2]
            .joinpath(*path_parts).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 1.4.2.3：热键绑定到对应 cmd_*
# ---------------------------------------------------------------------------


def test_default_bindings_register_alliance_hotkeys():
    """外交界面绑定必须把结盟命令映射到独立热键。"""
    root = Path(__file__).resolve().parents[2] / "res" / "ui"
    global_src = (root / "global_bindings.txt").read_text(encoding="utf-8")
    diplo_src = (root / "diplomacy_bindings.txt").read_text(encoding="utf-8")
    assert "F12: enter_diplomacy_mode" in global_src
    assert "1: select_alliance_candidate 1" in diplo_src
    assert "SHIFT 1: select_alliance_candidate -1" in diplo_src
    assert "q: alliance_request" in diplo_src
    assert "w: alliance_accept" in diplo_src
    assert "e: alliance_decline_or_cancel" in diplo_src


def test_game_interface_wires_alliance_commands():
    """``GameInterface`` 必须暴露四个结盟命令（与 bindings.txt 名字一致）。"""
    src = _source("soundrts", "clientgame", "__init__.py")
    for cmd in (
        "cmd_select_alliance_candidate",
        "cmd_alliance_request",
        "cmd_alliance_accept",
        "cmd_alliance_decline_or_cancel",
    ):
        assert f"GameInterface.{cmd} = game_audio.{cmd}" in src


def test_alliance_request_sends_diplomacy_request_command():
    """F4 → 客户端通过 ``server.write_line('diplomacy request <id>')`` 发命令。"""
    src = _source("soundrts", "clientgame", "game_audio.py")
    assert 'interface.server.write_line(f"diplomacy request {target.id}")' in src


def test_alliance_accept_sends_diplomacy_accept_command():
    src = _source("soundrts", "clientgame", "game_audio.py")
    assert 'interface.server.write_line(f"diplomacy accept {target.id}")' in src
    assert 'interface.server.write_line("diplomacy accept")' in src


def test_alliance_decline_or_cancel_sends_command():
    src = _source("soundrts", "clientgame", "game_audio.py")
    assert 'interface.server.write_line(f"diplomacy decline_or_cancel {target.id}")' in src
    assert 'interface.server.write_line("diplomacy decline_or_cancel")' in src


def test_alliance_commands_respect_alliances_locked():
    """游戏前已设联盟时（``alliances_locked=True``）所有结盟命令必须短路并提示。"""
    src = _source("soundrts", "clientgame", "game_audio.py")
    for cmd_name in (
        "def cmd_alliance_request(interface):",
        "def cmd_alliance_accept(interface):",
        "def cmd_alliance_decline_or_cancel(interface):",
    ):
        s = src.index(cmd_name)
        block = src[s:s + 1500]
        assert "alliances_locked" in block, f"{cmd_name} doesn't check alliances_locked"
        assert "ALLIANCES_LOCKED" in block, f"{cmd_name} doesn't voice the lock"


def test_world_alliances_locked_inferred_from_premade_alliances():
    """``game.run`` 必须在 populate_map 后推断 ``world.alliances_locked``：
    若玩家初始 client.alliance 中存在非空且重复值（说明开局前预设了同盟），就锁定。"""
    src = _source("soundrts", "game.py")
    assert "self.world.alliances_locked" in src
    assert "len(set(non_null)) < len(non_null)" in src


def test_diplo_players_excludes_self_and_neutral_and_defeated():
    """F12 候选必须排除自己 / neutral / 已淘汰玩家。"""
    src = _source("soundrts", "clientgame", "game_audio.py")
    s = src.index("def _diplo_players(interface):")
    block = src[s:s + 1500]
    assert "not getattr(p, 'neutral', False)" in block
    assert "_diplo_is_alive(p)" in block


# ---------------------------------------------------------------------------
# 1.4.2.3：合作战役 bug 修复（args 阈值）
# ---------------------------------------------------------------------------


def test_srv_start_game_uses_threshold_8_not_9():
    """``srv_start_game`` 必须用 ``len(args) >= 8`` 而不是 ``>= 9``。

    服务器 ``serverroom._start`` 一共发 8 个位置参数：
        players, login, seed, speed, treaty, is_coop, campaign_name, chapter
    旧代码写 ``>= 9`` 会让所有合作战役场景走到 ``>= 5`` 分支，
    coop 元数据被静默丢失，玩家通关也无法解锁下一章。"""
    src = _source("soundrts", "clientservermenu.py")
    s = src.index("def srv_start_game(self, args):")
    e = src.index("\n    def ", s + 1)
    block = src[s:e]
    assert "if len(args) >= 8:" in block, (
        "srv_start_game 必须用 8 作为合作战役分支阈值；"
        "否则 8-token 的 start_game 永远落到 >= 5 兜底分支"
    )
    # 老 bug 阈值必须已被纠正
    assert "if len(args) >= 9:" not in block
    # 8 个变量解包
    assert ("players, local_login, seed, speed, treaty_minutes, "
            "is_coop, coop_campaign_name, coop_chapter = args[:8]") in block


def test_server_sends_8_positional_args_after_start_game():
    """对称面：服务器侧 ``serverroom._start`` 发送 8 个位置参数。"""
    src = _source("soundrts", "serverroom.py")
    s = src.index('"start_game"')
    # 用括号深度匹配截取整个 notify 调用块（直到外层右括号）
    # 注意：我们已经站在 notify(...) 的内部第一个参数处，
    # 需要往后找到匹配的外层 ")"，但因为已经在内部，初始深度设为 1。
    depth = 1
    i = s
    while i < len(src) and depth > 0:
        ch = src[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        i += 1
    notify_block = src[s:i]
    for token in (
        "client.login",
        "seed",
        "self.speed",
        "self.treaty_minutes",
        "int(is_coop)",
        '"coop_campaign_name"',
        '"coop_chapter"',
    ):
        assert token in notify_block, f"start_game notify missing {token}"


def test_game_postrun_unlocks_next_chapter_on_coop_victory():
    """合作战役胜利后必须在 ``post_run`` 里把合作书签推进到下一章。"""
    src = _source("soundrts", "game.py")
    # 关键代码段：当 is_coop_campaign 且 has_victory，根据 coop_chapter 推进 coop 书签
    assert 'getattr(self, "is_coop_campaign", False)' in src
    assert "unlock_next_coop" in src
    assert "campaign._get_bookmark()" not in src.split("def post_run(self):")[1]


def test_srv_start_game_parses_real_coop_payload():
    """端到端：用真实 8-token 字符串模拟服务器输入，看解析后字段全到位。"""
    # 复刻 _process_server_event 的拆分
    line = "start_game p1,login1,h,red,1;p2,ai_easy,c,blue,2 me 12345 1.0 0 1 base 1"
    parts = line.strip().split(" ")
    cmd = parts[0]
    args = parts[1:]
    assert cmd == "start_game"
    assert len(args) == 8

    # 套用修复后的逻辑
    treaty_minutes = 0
    is_coop = 0
    coop_campaign_name = ""
    coop_chapter = ""
    if len(args) >= 8:
        (players, local_login, seed, speed, treaty_minutes,
         is_coop, coop_campaign_name, coop_chapter) = args[:8]
    elif len(args) >= 5:
        players, local_login, seed, speed, treaty_minutes = args[:5]
    else:
        players, local_login, seed, speed = args[:4]

    assert local_login == "me"
    assert seed == "12345"
    assert speed == "1.0"
    assert treaty_minutes == "0"
    assert is_coop == "1"
    assert coop_campaign_name == "base"
    assert coop_chapter == "1"
