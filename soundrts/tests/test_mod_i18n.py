"""mod.txt title、模组菜单标签与全局 TTS 扫描回归测试。"""
from __future__ import annotations

import os
import sys
import warnings as _warnings

_warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    message=r".*getdefaultlocale.*",
)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

_saved_argv = sys.argv
sys.argv = [sys.argv[0]]
with _warnings.catch_warnings():
    _warnings.simplefilter("ignore")
    try:
        from soundrts.lib import resource as _preload_resource  # noqa: F401
    finally:
        sys.argv = _saved_argv

import pytest

from soundrts.lib.package import PackageStack, mod_menu_label
from soundrts.lib.resource import res
from soundrts.lib.sound_cache import sounds


class TestModMetadata:
    def test_mod_txt_title_and_mods(self, tmp_path):
        mod_dir = tmp_path / "mods" / "samplemod"
        mod_dir.mkdir(parents=True)
        (mod_dir / "mod.txt").write_text(
            "mods dep1,dep2\ntitle 7100\n",
            encoding="utf-8",
        )
        (mod_dir / "ui").mkdir()
        (mod_dir / "ui" / "tts.txt").write_text("7100 Sample Mod\n", encoding="utf-8")
        (mod_dir / "ui-zh").mkdir()
        (mod_dir / "ui-zh" / "tts.txt").write_text(
            "; coding: utf-8\n7100 \u793a\u4f8b\u6a21\u7ec4\n",
            encoding="utf-8",
        )

        stack = PackageStack([str(tmp_path)])
        mod = stack.mod("samplemod")
        assert mod is not None
        assert mod.mods == ["dep1", "dep2"]
        assert mod.menu_title == ["7100"]
        assert mod_menu_label(stack, "samplemod") == ["7100"]
        assert mod_menu_label(stack, "missing") == ["missing"]

    def test_mod_txt_title_crlf(self, tmp_path):
        mod_dir = tmp_path / "mods" / "crlfmod"
        mod_dir.mkdir(parents=True)
        (mod_dir / "mod.txt").write_bytes(b"title 7100\r\n")
        (mod_dir / "ui").mkdir()
        (mod_dir / "ui" / "tts.txt").write_text("7100 CRLF Mod\n", encoding="utf-8")

        stack = PackageStack([str(tmp_path)])
        assert mod_menu_label(stack, "crlfmod") == ["7100"]

    def test_mod_without_title_uses_folder_name(self, tmp_path):
        mod_dir = tmp_path / "mods" / "plainmod"
        mod_dir.mkdir(parents=True)
        stack = PackageStack([str(tmp_path)])
        mod = stack.mod("plainmod")
        assert mod is not None
        assert getattr(mod, "menu_title", None) is None
        assert mod_menu_label(stack, "plainmod") == ["plainmod"]


class TestModGlobalTtsLookup:
    def test_global_lookup_finds_mod_root_tts(self, tmp_path, monkeypatch):
        mods_root = tmp_path / "mods" / "titlemod"
        (mods_root / "ui").mkdir(parents=True)
        (mods_root / "ui" / "tts.txt").write_text("7100 English Title\n", encoding="utf-8")
        (mods_root / "ui-zh").mkdir()
        (mods_root / "ui-zh" / "tts.txt").write_text(
            "; coding: utf-8\n7100 \u4e2d\u6587\u6807\u9898\n",
            encoding="utf-8",
        )
        (mods_root / "mod.txt").write_text("title 7100\n", encoding="utf-8")

        stack = PackageStack([str(tmp_path)])
        monkeypatch.setattr(res, "packages", stack)

        res.language = "en"
        sounds.load_default(res)
        sounds._global_text_cache = {}
        assert sounds.translate_sound_number("7100") == "English Title"

        res.language = "zh"
        sounds.load_default(res)
        sounds._global_text_cache = {}
        assert sounds.translate_sound_number("7100") == "\u4e2d\u6587\u6807\u9898"

    def test_orc_mod_title_from_repo_if_present(self):
        mod = res.packages.mod("orc")
        if mod is None:
            pytest.skip("orc mod not in this install")
        label = mod_menu_label(res.packages, "orc")
        assert label == ["orc"] or label == ["7754"]

    def test_soundpack_menu_labels(self):
        res.language = "zh"
        sounds.load_default(res)
        for name, tid, zh in (
            ("soundpack", "7752", "\u4f18\u8d28\u97f3\u6548\u5305"),
            ("soundpack2", "7753", "\u91d1\u54c1\u97f3\u6548\u5305"),
        ):
            mod = res.packages.mod(name)
            if mod is None:
                pytest.skip(f"{name} not in this install")
            assert mod.is_a_soundpack()
            assert mod_menu_label(res.packages, name) == [tid]
            sounds._global_text_cache = {}
            assert sounds.translate_sound_number(tid) == zh
