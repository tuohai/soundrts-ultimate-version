"""登录名与聊天应支持中文等 Unicode 字符。"""
from __future__ import annotations

from soundrts import config


def test_login_is_valid_accepts_chinese():
    assert config.login_is_valid("玩家")
    assert config.login_is_valid("玩家123")
    assert config.login_is_valid("abc中文")


def test_login_is_valid_rejects_invalid():
    assert not config.login_is_valid("")
    assert not config.login_is_valid("a" * 21)
    assert not config.login_is_valid("有 空格")
    assert not config.login_is_valid("ai_easy")
    assert not config.login_is_valid("ai_玩家")
