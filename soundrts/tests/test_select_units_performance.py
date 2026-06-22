"""批量选择单位（Ctrl+D/E）的客户端性能修复契约与行为测试。"""

from pathlib import Path
from types import SimpleNamespace

import pytest


def _source(*parts):
    return (Path(__file__).resolve().parents[1] / Path(*parts)).read_text(
        encoding="utf-8"
    )


def test_global_select_fast_path():
    src = _source("clientgame", "game_unit_control.py")
    block = src.split("def cmd_select_units")[1].split("\ndef ")[0]
    assert "if not local:" in block
    assert "_ids_matching_types(interface, types, local, idle)" in block


def test_say_group_uses_orders_txt_dedupe():
    src = _source("clientgame", "game_unit_control.py")
    block = src.split("def say_group")[1].split("\ndef ")[0]
    assert "_remove_duplicates(orders)" in block
    assert "_orders_txt_has_content" in block


def test_message_collapse_cache():
    from soundrts.lib.message import Message

    msg = Message([1, 2, 3])
    first = msg.translate_and_collapse()
    second = msg.translate_and_collapse()
    assert first == second


def test_global_cmd_select_units_skips_regroup(monkeypatch):
    from soundrts.clientgame import game_unit_control as guc

    calls = {"regroup": 0, "ids": None}

    monkeypatch.setattr(
        guc,
        "_ids_matching_types",
        lambda iface, types, local, idle: calls.__setitem__("ids", (types, local, idle)) or [1, 2],
    )
    monkeypatch.setattr(guc, "_regroup", lambda *a, **k: calls.__setitem__("regroup", calls["regroup"] + 1))
    monkeypatch.setattr(guc, "_arrange", lambda args: (["peasant"], False, False, False))
    monkeypatch.setattr(guc, "say_group", lambda *a, **k: None)

    interface = SimpleNamespace(group=[], order=None, previous_group=None)
    guc.cmd_select_units(interface, "worker")

    assert interface.group == [1, 2]
    assert calls["regroup"] == 0
