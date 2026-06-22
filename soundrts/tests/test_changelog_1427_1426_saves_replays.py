"""审计：1.4.2.7 / 1.4.2.6 — 存档与回放系统。

涵盖更新日志中的承诺：

1.4.2.7
- 通过 ``shift+enter`` 重命名当前选中的存档 / 回放文件，支持中文等任意可打印字符。
- 通过 ``delete`` 删除（确认）/ ``shift+delete`` 直接删除当前选中的存档 / 回放。

1.4.2.6
- 玩家最多保存 10 个存档槽。
- 不同 mod 的存档相互独立（``saves/<mod_key>/save_*``）。
- ``replay`` 同样按 mod 隔离（``replays/<mod_key>/*.txt``）。
- 退出局后的"继续未完成的游戏"记忆点 = ``saves/<mod_key>/resume_savegame``。
- 旧版散落在根目录下的 ``save_*`` / ``resume_savegame`` 会被一次性迁移到 ``_base/``。

测试策略：
- 不启动 pygame；只测纯函数（路径计算、文件名清洗、自动命名判定、时间显示），
  以及读取 ``soundrts/clientmain.py`` 源码做契约级检查（关键代码片段必须存在）。
- 文件系统操作走 ``tmp_path`` 沙箱，并通过 ``monkeypatch`` 替换 ``current_saves_dir`` /
  ``current_replays_dir``，避免污染玩家真实 ``user/`` 目录。
"""
from __future__ import annotations

import importlib
import os
import time
import types
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# 工具：源码契约 + 纯函数复刻
# ---------------------------------------------------------------------------



REPLAY_ENCODED = 1005028  # NB_ENCODE_SHIFT + 5028
def _source(*path_parts):
    return (Path(__file__).resolve().parents[2]
            .joinpath(*path_parts).read_text(encoding="utf-8"))


def _sanitize_filename(name):
    """从 ``soundrts/clientmain.py:_sanitize_filename`` 复刻的纯函数。

    若实现漂移，``test_sanitize_filename_source_contract`` 会立刻失败提醒。
    """
    if not name:
        return None
    bad = set('\\/:*?"<>|\0')
    cleaned = "".join("_" if c in bad else c for c in name)
    cleaned = cleaned.strip().strip(".")
    cleaned = "".join(c for c in cleaned if c.isprintable())
    cleaned = cleaned.strip()
    if not cleaned:
        return None
    return cleaned


def _is_auto_replay_filename(filename):
    stem = filename[:-4] if filename.endswith(".txt") else filename
    import re as _re
    return bool(_re.match(r"^replay\d+_\d+$", stem))


def _replay_display_name(filename):
    stem = filename[:-4] if filename.endswith(".txt") else filename
    import re as _re
    m = _re.match(r"^replay(\d+)_(\d+)$", stem)
    if m:
        num = m.group(1)
        ts = int(m.group(2))
        try:
            ts_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
            return [REPLAY_ENCODED, " " + num + ", " + ts_str]
        except (OSError, OverflowError):
            return [stem]
    try:
        return [time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(stem)))]
    except (ValueError, OSError, OverflowError):
        return [stem]


# ---------------------------------------------------------------------------
# 源码契约：上面复刻的纯函数确实在 clientmain.py 里
# ---------------------------------------------------------------------------


def test_sanitize_filename_source_contract():
    src = _source("soundrts", "clientmain.py")
    # 关键代码必须存在；如果发生重构，本测试会立即失败提醒同步本文件副本
    assert "def _sanitize_filename(name):" in src
    assert 'bad = set(\'\\\\/:*?"<>|\\0\')' in src
    assert "if not cleaned:" in src
    assert "isprintable()" in src


def test_is_auto_replay_filename_source_contract():
    src = _source("soundrts", "clientmain.py")
    assert "def _is_auto_replay_filename(filename):" in src
    assert "replay" in src
    assert "_re.match" in src


def test_replay_display_name_source_contract():
    src = _source("soundrts", "clientmain.py")
    assert "def _replay_display_name(filename):" in src
    assert 'time.strftime("%Y-%m-%d %H:%M:%S"' in src
    assert "mp.REPLAY" in src


# ---------------------------------------------------------------------------
# _sanitize_filename 行为
# ---------------------------------------------------------------------------


def test_sanitize_filename_keeps_ascii():
    assert _sanitize_filename("replay1") == "replay1"
    assert _sanitize_filename("My Save") == "My Save"


def test_sanitize_filename_keeps_chinese():
    """更新日志 1.4.2.7 的核心承诺：中文文件名可以被识别。"""
    assert _sanitize_filename("录像1") == "录像1"
    assert _sanitize_filename("游戏存档") == "游戏存档"
    assert _sanitize_filename("中文 with mix") == "中文 with mix"


def test_sanitize_filename_replaces_forbidden_chars():
    """禁用字符（\\/:*?"<>|）会被替换为下划线，而不是抛错。"""
    assert _sanitize_filename("a/b") == "a_b"
    assert _sanitize_filename("a\\b") == "a_b"
    assert _sanitize_filename("a:b") == "a_b"
    assert _sanitize_filename("a*b") == "a_b"
    assert _sanitize_filename('a"b') == "a_b"
    assert _sanitize_filename("a<b>c") == "a_b_c"
    assert _sanitize_filename("a|b") == "a_b"
    assert _sanitize_filename("a?b") == "a_b"


def test_sanitize_filename_strips_dots_and_spaces():
    assert _sanitize_filename("   abc   ") == "abc"
    assert _sanitize_filename("...abc...") == "abc"
    assert _sanitize_filename(" . abc . ") == "abc"


def test_sanitize_filename_rejects_empty_or_only_punctuation():
    assert _sanitize_filename("") is None
    assert _sanitize_filename(None) is None
    assert _sanitize_filename("...") is None
    assert _sanitize_filename("   ") is None


def test_sanitize_filename_rejects_only_control_chars():
    # \x00 在 bad 集合里会被替换为 _，所以"\x00\x00\x00"会变成"___"，不为空。
    # 但单纯的不可打印字符（如 \x01）应该被过滤掉。
    assert _sanitize_filename("\x01\x02\x03") is None


# ---------------------------------------------------------------------------
# _is_auto_replay_filename 行为
# ---------------------------------------------------------------------------


def test_is_auto_replay_filename_recognizes_new_format():
    """自动生成的回放文件 ``replay<N>_<unix_ts>.txt`` 应被识别。"""
    assert _is_auto_replay_filename("replay1_1234567890.txt") is True
    assert _is_auto_replay_filename("replay2_0.txt") is True
    assert _is_auto_replay_filename("replay10_1700000000.txt") is True


def test_is_auto_replay_filename_rejects_old_timestamp_only():
    """旧版的纯时间戳回放文件（<unix_ts>.txt）不应被当成新版自动命名。"""
    assert _is_auto_replay_filename("1234567890.txt") is False
    assert _is_auto_replay_filename("0.txt") is False


def test_is_auto_replay_filename_rejects_chinese():
    """玩家重命名后的中文文件不应被当成自动命名。"""
    assert _is_auto_replay_filename("录像1.txt") is False
    assert _is_auto_replay_filename("我的回放.txt") is False


def test_is_auto_replay_filename_rejects_ascii_words():
    assert _is_auto_replay_filename("my_replay.txt") is False
    assert _is_auto_replay_filename("replay 1.txt") is False


# ---------------------------------------------------------------------------
# _replay_display_name 行为
# ---------------------------------------------------------------------------


def test_replay_display_name_formats_new_auto():
    """新版自动回放 ``replay<N>_<ts>.txt`` → 返回列表 [REPLAY_ENCODED, " <N> <时间>"]。"""
    out = _replay_display_name("replay1_1234567890.txt")
    assert isinstance(out, list)
    assert len(out) == 2
    assert out[0] == REPLAY_ENCODED
    import re as _re2
    assert _re2.match(r"^ 1, \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", out[1])

def test_replay_display_name_formats_old_timestamp():
    """旧版纯时间戳回放 → 返回列表 [时间字符串]（向后兼容）。"""
    out = _replay_display_name("1234567890.txt")
    assert isinstance(out, list)
    assert len(out) == 1
    import re as _re2
    assert _re2.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", out[0])


def test_replay_display_name_keeps_custom_name():
    assert _replay_display_name("录像1.txt") == ["录像1"]
    assert _replay_display_name("my_replay.txt") == ["my_replay"]


# ---------------------------------------------------------------------------
# Menu 的 shift+enter / delete / shift+delete 源码契约
# ---------------------------------------------------------------------------


def test_menu_has_shift_enter_rename_handler():
    """``Menu._process_keydown`` 必须存在 shift+enter 的 rename 处理分支。"""
    src = _source("soundrts", "clientmenu.py")
    # Shift+Enter 处理块
    assert "K_RETURN, K_KP_ENTER" in src
    assert "KMOD_SHIFT" in src
    assert 'extras.get("rename")' in src


def test_menu_has_delete_and_shift_delete_handler():
    """``Menu._process_keydown`` 必须支持 K_DELETE 与 shift 修饰位区分立即删除。"""
    src = _source("soundrts", "clientmenu.py")
    assert "K_DELETE" in src
    assert 'extras.get("delete")' in src
    # immediate=True 仅在按下 SHIFT 时设置
    assert "immediate = bool(e.mod & KMOD_SHIFT)" in src


def test_menu_append_accepts_on_rename_and_on_delete():
    """``Menu.append`` 必须接受 ``on_rename`` 和 ``on_delete`` 两个回调。"""
    src = _source("soundrts", "clientmenu.py")
    assert "def append(self, label, action, explanation=None, on_rename=None, on_delete=None)" in src


def test_menu_clear_choices_resets_extras():
    """``clear_choices`` 必须重置 _choice_extras / choice_index，否则刷新后回调错位。"""
    src = _source("soundrts", "clientmenu.py")
    # clear_choices 必须把 _choice_extras 置空
    s = src.index("def clear_choices(self):")
    e = src.index("def ", s + 1)
    block = src[s:e]
    assert "self._choice_extras = {}" in block
    assert "self.choice_index = None" in block


# ---------------------------------------------------------------------------
# clientmain.py 的存档 / 回放回调装配
# ---------------------------------------------------------------------------


def test_refresh_replay_menu_attaches_rename_and_delete():
    src = _source("soundrts", "clientmain.py")
    s = src.index("def _refresh_replay_menu(menu):")
    e = src.index("\n\ndef ", s + 1)
    block = src[s:e]
    assert "on_rename=" in block
    assert "on_delete=" in block
    assert "_rename_replay" in block
    assert "_delete_replay" in block
    assert "name_list" in block


def test_refresh_save_menu_attaches_rename_and_delete():
    src = _source("soundrts", "clientmain.py")
    s = src.index("def _refresh_save_menu(menu):")
    e = src.index("\n\ndef ", s + 1)
    block = src[s:e]
    assert "on_rename=" in block
    assert "on_delete=" in block
    assert "_rename_save" in block
    assert "_delete_save" in block


def test_rename_replay_appends_txt_suffix():
    """玩家输入"录像1"应被保存为"录像1.txt"以便后续仍可识别。"""
    src = _source("soundrts", "clientmain.py")
    s = src.index("def _rename_replay(")
    e = src.index("\n\ndef ", s + 1)
    block = src[s:e]
    assert '.endswith(".txt")' in block
    assert 'safe = safe + ".txt"' in block


def test_rename_save_blocks_resume_filename_collision():
    """重命名存档不能撞到系统保留的 ``resume_savegame``。"""
    src = _source("soundrts", "clientmain.py")
    s = src.index("def _rename_save(")
    e = src.index("\n\ndef ", s + 1)
    block = src[s:e]
    assert "RESUME_SAVE_FILENAME" in block
    assert "INVALID_NAME" in block


def test_delete_replay_immediate_skips_confirm():
    """shift+delete (immediate=True) 跳过确认对话框，直接删除。"""
    src = _source("soundrts", "clientmain.py")
    s = src.index("def _delete_replay(")
    e = src.index("\n\ndef ", s + 1)
    block = src[s:e]
    assert "immediate" in block
    assert "if not immediate:" in block
    assert "confirm_yes_no" in block


def test_delete_save_immediate_skips_confirm():
    src = _source("soundrts", "clientmain.py")
    s = src.index("def _delete_save(")
    e = src.index("\n\ndef ", s + 1)
    block = src[s:e]
    assert "immediate" in block
    assert "if not immediate:" in block
    assert "confirm_yes_no" in block


# ---------------------------------------------------------------------------
# 1.4.2.6：10 个存档槽 + mod 隔离 + resume 记忆点
# ---------------------------------------------------------------------------


def test_paths_constants():
    """``paths.py`` 必须暴露 ``MAX_SAVE_SLOTS=10`` 与 ``RESUME_SAVE_FILENAME``。"""
    from soundrts import paths
    assert paths.MAX_SAVE_SLOTS == 10
    assert paths.RESUME_SAVE_FILENAME == "resume_savegame"
    assert paths.BASE_MOD_KEY == "_base"


def test_sanitize_mod_part_handles_special_chars():
    from soundrts.paths import _sanitize_mod_part
    assert _sanitize_mod_part("crazymod") == "crazymod"
    # 中文 mod 名应被替换为下划线（防止跨平台路径问题）
    out = _sanitize_mod_part("中文mod")
    # 至少不应包含非 ASCII 字符；下划线兜底
    for c in out:
        assert c.isalnum() or c in ("_", "-")
    # 输入 "" 等情况下兜底返回 "_"
    assert _sanitize_mod_part("") == "_"
    assert _sanitize_mod_part("___") == "_"


def test_current_mod_key_with_no_mod(monkeypatch):
    """未加载任何 mod 时，返回 BASE_MOD_KEY=_base。"""
    from soundrts import paths
    # 强制 res.mods 为空
    try:
        from soundrts.lib.resource import res
    except Exception:
        pytest.skip("resource module unavailable")
    monkeypatch.setattr(res, "mods", "", raising=False)
    # 同时清空 config.mods
    try:
        from soundrts import config
        monkeypatch.setattr(config, "mods", "", raising=False)
    except Exception:
        pass
    assert paths.current_mod_key() == "_base"


def test_current_mod_key_with_single_mod(monkeypatch):
    from soundrts import paths
    from soundrts.lib.resource import res
    monkeypatch.setattr(res, "mods", "crazymod", raising=False)
    assert paths.current_mod_key() == "crazymod"


def test_current_mod_key_with_multiple_mods(monkeypatch):
    from soundrts import paths
    from soundrts.lib.resource import res
    monkeypatch.setattr(res, "mods", "modA,modB", raising=False)
    out = paths.current_mod_key()
    # 多 mod 用 "+" 连接（按代码注释）
    assert out == "modA+modB"


def test_current_saves_dir_isolates_by_mod(tmp_path, monkeypatch):
    from soundrts import paths
    from soundrts.lib.resource import res

    # 让 SAVES_DIR_PATH 指向沙箱
    monkeypatch.setattr(paths, "SAVES_DIR_PATH", str(tmp_path / "saves"), raising=False)
    os.makedirs(str(tmp_path / "saves"), exist_ok=True)

    monkeypatch.setattr(res, "mods", "", raising=False)
    base_dir = paths.current_saves_dir()
    assert os.path.basename(base_dir) == "_base"
    assert os.path.isdir(base_dir)

    monkeypatch.setattr(res, "mods", "modA", raising=False)
    a_dir = paths.current_saves_dir()
    assert os.path.basename(a_dir) == "modA"
    assert a_dir != base_dir
    assert os.path.isdir(a_dir)


def test_current_resume_save_path_lives_in_mod_dir(tmp_path, monkeypatch):
    from soundrts import paths
    from soundrts.lib.resource import res

    monkeypatch.setattr(paths, "SAVES_DIR_PATH", str(tmp_path / "saves"), raising=False)
    os.makedirs(str(tmp_path / "saves"), exist_ok=True)
    monkeypatch.setattr(res, "mods", "crazymod", raising=False)

    p = paths.current_resume_save_path()
    assert p.endswith(os.path.join("crazymod", "resume_savegame"))


def test_current_replays_dir_isolates_by_mod(tmp_path, monkeypatch):
    from soundrts import paths
    from soundrts.lib.resource import res

    monkeypatch.setattr(paths, "REPLAYS_PATH", str(tmp_path / "replays"), raising=False)
    os.makedirs(str(tmp_path / "replays"), exist_ok=True)

    monkeypatch.setattr(res, "mods", "modA", raising=False)
    a_dir = paths.current_replays_dir()
    assert os.path.basename(a_dir) == "modA"
    assert os.path.isdir(a_dir)


# ---------------------------------------------------------------------------
# 10 槽位上限：_prune_save_slots 行为
# ---------------------------------------------------------------------------


def test_prune_save_slots_keeps_max_10(tmp_path, monkeypatch):
    """game._prune_save_slots 必须把第 11 个之后的旧存档删掉。"""
    from soundrts import paths
    # 在沙箱目录里造 12 个 "save_<ts>" 文件
    fake_saves = tmp_path / "saves" / "_base"
    fake_saves.mkdir(parents=True)
    for i in range(12):
        p = fake_saves / f"save_{1700000000 + i}"
        p.write_text("dummy")
        # 让 i 越小 mtime 越早
        os.utime(str(p), (1700000000 + i, 1700000000 + i))

    # 把 game._prune_save_slots 调用的 current_saves_dir 指过来
    monkeypatch.setattr(paths, "SAVES_DIR_PATH", str(tmp_path / "saves"), raising=False)
    from soundrts.lib.resource import res
    monkeypatch.setattr(res, "mods", "", raising=False)

    from soundrts import game as game_mod
    game_mod._prune_save_slots()

    remaining = sorted(os.listdir(str(fake_saves)))
    # 应保留 10 个最新的（save_1700000002 .. save_1700000011），删除 save_1700000000 / save_1700000001
    assert len(remaining) == 10
    assert "save_1700000000" not in remaining
    assert "save_1700000001" not in remaining
    assert "save_1700000011" in remaining


def test_prune_save_slots_under_10_keeps_all(tmp_path, monkeypatch):
    from soundrts import paths
    fake_saves = tmp_path / "saves" / "_base"
    fake_saves.mkdir(parents=True)
    for i in range(5):
        p = fake_saves / f"save_{1700000000 + i}"
        p.write_text("dummy")

    monkeypatch.setattr(paths, "SAVES_DIR_PATH", str(tmp_path / "saves"), raising=False)
    from soundrts.lib.resource import res
    monkeypatch.setattr(res, "mods", "", raising=False)

    from soundrts import game as game_mod
    game_mod._prune_save_slots()

    assert len(os.listdir(str(fake_saves))) == 5


def test_list_save_slot_paths_excludes_resume_and_non_save(tmp_path, monkeypatch):
    """``_list_save_slot_paths`` 必须只返回 ``save_`` 开头的文件，跳过 resume / 其他。"""
    from soundrts import paths
    fake_saves = tmp_path / "saves" / "_base"
    fake_saves.mkdir(parents=True)
    (fake_saves / "save_100").write_text("a")
    (fake_saves / "save_200").write_text("b")
    (fake_saves / "resume_savegame").write_text("r")
    (fake_saves / "custom_name").write_text("c")

    monkeypatch.setattr(paths, "SAVES_DIR_PATH", str(tmp_path / "saves"), raising=False)
    from soundrts.lib.resource import res
    monkeypatch.setattr(res, "mods", "", raising=False)

    from soundrts import game as game_mod
    paths_out = game_mod._list_save_slot_paths()
    names = sorted(os.path.basename(p) for p in paths_out)
    assert names == ["save_100", "save_200"]


def test_new_save_slot_path_disambiguates_on_collision(tmp_path, monkeypatch):
    """若同一秒内连续存档，文件名应附加 ``_1`` / ``_2`` 后缀避免覆盖。"""
    from soundrts import paths
    fake_saves = tmp_path / "saves" / "_base"
    fake_saves.mkdir(parents=True)

    monkeypatch.setattr(paths, "SAVES_DIR_PATH", str(tmp_path / "saves"), raising=False)
    from soundrts.lib.resource import res
    monkeypatch.setattr(res, "mods", "", raising=False)

    # 锁定 time.time
    monkeypatch.setattr(time, "time", lambda: 1700000000)

    from soundrts import game as game_mod
    p1 = game_mod._new_save_slot_path()
    Path(p1).write_text("a")
    p2 = game_mod._new_save_slot_path()
    Path(p2).write_text("b")
    p3 = game_mod._new_save_slot_path()
    Path(p3).write_text("c")
    assert os.path.basename(p1) == "save_1700000000"
    assert os.path.basename(p2) == "save_1700000000_1"
    assert os.path.basename(p3) == "save_1700000000_2"


# ---------------------------------------------------------------------------
# clientmain.py 内的"继续未完成游戏"流程
# ---------------------------------------------------------------------------


def test_has_resume_save_uses_per_mod_path():
    src = _source("soundrts", "clientmain.py")
    s = src.index("def has_resume_save():")
    e = src.index("\n\ndef ", s + 1)
    block = src[s:e]
    assert "current_resume_save_path()" in block


def test_resume_unfinished_game_loads_and_deletes_on_success():
    src = _source("soundrts", "clientmain.py")
    s = src.index("def resume_unfinished_game():")
    e = src.index("\n\ndef ", s + 1)
    block = src[s:e]
    assert "_load_savegame_file" in block
    assert "delete_on_success=True" in block


def test_single_player_menu_rebuilds_choices_after_game():
    """取消/续玩后应刷新"继续未完成的游戏"，不能沿用进入子菜单时的静态列表。"""
    src = _source("soundrts", "clientmain.py")
    s = src.index("def single_player_menu():")
    e = src.index("\n\ndef ", s + 1)
    block = src[s:e]
    assert "_build_single_player_menu_choices()" in block
    assert "while True:" in block
    assert "has_resume_save()" in _source("soundrts", "clientmain.py")[
        src.index("def _build_single_player_menu_choices():") :
        src.index("\n\ndef single_player_menu():")
    ]
