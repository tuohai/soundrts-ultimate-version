"""审计：1.4.2.9e — 启动崩溃修复：非 tts 资源文件的遗留编码回退。

现象：启用某些第三方 mod（如 crazyMod9beta10，其 rules.txt / ai.txt /
ui/style.txt 为 cp1252/latin-1，含 0xe9='é' 且未声明 `; coding:`）时，
``Package.open_text`` 以严格 UTF-8 解码非 tts 文件，导致游戏在启动加载规则时
直接抛 UnicodeDecodeError 崩溃。

修复：非 tts 文件先按检测编码（utf-8）严格解码；失败时回退到 cp1252 容错解码
并告警，避免整个游戏因一个 mod 的注释/单位名编码而无法启动。tts 仍走严格分支。
"""
from __future__ import annotations

import io

from soundrts.lib.package import Package


class _FakePackage(Package):
    """最小 Package：直接以给定字节回应 open_binary，用于测试 open_text 解码。"""

    def __init__(self, raw: bytes):
        self._raw = raw

    def open_binary(self, name):
        return io.BytesIO(self._raw)


def test_non_tts_latin1_falls_back_to_cp1252_without_crashing():
    # rules.txt 含 cp1252 的 'é' (0xe9)，未声明编码
    pkg = _FakePackage(b"; commentaire e\xe9\nfootman\n")
    text = pkg.open_text("rules.txt").read()
    assert "\u00e9" in text  # 0xe9 按 cp1252 解码为 'é'
    assert "footman" in text


def test_valid_utf8_non_tts_unchanged():
    pkg = _FakePackage("; café\nfootman\n".encode("utf-8"))
    text = pkg.open_text("rules.txt").read()
    assert "café" in text


def test_tts_files_still_strict():
    import pytest

    # tts 仍严格解码：坏字节必须抛错，绝不静默回退/替换（避免损坏译文）
    pkg = _FakePackage(b"100 caf\xe9\n")
    with pytest.raises(UnicodeDecodeError):
        pkg.open_text("tts.txt").read()


def test_open_text_has_cp1252_fallback_in_source():
    from pathlib import Path

    src = (Path(__file__).resolve().parents[2]
           / "soundrts" / "lib" / "package.py").read_text(encoding="utf-8")
    s = src.index("def open_text(self, name):")
    e = src.index("\n    def ", s + 1)
    block = src[s:e]
    assert 'raw.decode(enc, errors="strict")' in block
    assert 'raw.decode("cp1252", errors="replace")' in block
    # tts 仍严格
    assert "decode_tts_bytes" in block
