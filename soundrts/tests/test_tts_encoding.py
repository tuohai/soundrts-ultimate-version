"""tts.txt 编码：严格解码，避免静默替换为 U+FFFD。"""

import logging
import sys

import pytest

from soundrts.lib import encoding
from soundrts.lib.package import FolderPackage


def test_decode_tts_bytes_utf8_strict():
    raw = "; coding: utf-8\n12801 明光甲\n".encode("utf-8")
    text = encoding.decode_tts_bytes(raw, "ui-zh/tts.txt")
    assert "明光甲" in text


def test_decode_tts_bytes_defaults_to_utf8_without_coding_line(caplog):
    raw = "12801 明光甲\n".encode("utf-8")
    with caplog.at_level(logging.WARNING):
        text = encoding.decode_tts_bytes(raw, "ui-zh/tts.txt")
    assert "明光甲" in text
    assert encoding.encoding(raw, "ui-zh/tts.txt") == "utf-8"
    assert not any("no encoding specified" in r.message for r in caplog.records)


def test_decode_tts_bytes_gbk_legacy():
    raw = "; coding: gbk\n12801 明光甲\n".encode("gbk")
    text = encoding.decode_tts_bytes(raw, "ui-zh/tts.txt")
    assert "明光甲" in text


def test_decode_tts_bytes_rejects_wrong_encoding():
    # 声明 utf-8 但正文按 GBK 保存 — 以前会被 replace 成 U+FFFD
    raw = ("; coding: utf-8\n12801 明光甲\n").encode("gbk")
    with pytest.raises(UnicodeDecodeError):
        encoding.decode_tts_bytes(raw, "ui-zh/tts.txt")


def test_validate_tts_text_warns_on_replacement_char(caplog):
    with caplog.at_level(logging.WARNING):
        encoding.validate_tts_text("12801 明\uFFFD甲\n", "ui-zh/tts.txt")
    assert any("U+FFFD" in r.message for r in caplog.records)


def test_package_open_text_tts_uses_strict_decode(tmp_path):
    sys.argv = ["pytest"]
    tts_path = tmp_path / "ui-zh" / "tts.txt"
    tts_path.parent.mkdir(parents=True)
    tts_path.write_bytes("; coding: utf-8\n12801 测试\n".encode("utf-8"))
    pkg = FolderPackage(str(tmp_path))
    with pkg.open_text("ui-zh/tts.txt") as f:
        assert "测试" in f.read()


def test_package_open_text_non_tts_still_strict(tmp_path):
    sys.argv = ["pytest"]
    rules = tmp_path / "rules.txt"
    rules.write_text("def x\n", encoding="utf-8")
    pkg = FolderPackage(str(tmp_path))
    with pkg.open_text("rules.txt") as f:
        assert f.read().startswith("def x")
