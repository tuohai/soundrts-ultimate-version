"""Nuance helper jars must resolve next to the game, not only via __file__."""

import os
from pathlib import Path

from soundrts.lib import nuance_tts


def test_discover_helper_dir_finds_tools_nuance_ve():
    d = nuance_tts.discover_helper_dir()
    assert d, "expected tools/nuance_ve with jars in the checkout"
    jar, jna = nuance_tts._helper_jar_pair(d)
    assert Path(jar).is_file()
    assert Path(jna).is_file()


def test_discover_helper_dir_prefers_cwd_tools(tmp_path, monkeypatch):
    tools = tmp_path / "tools" / "nuance_ve"
    tools.mkdir(parents=True)
    (tools / "nuance_ve_helper.jar").write_bytes(b"jar")
    (tools / "jna.jar").write_bytes(b"jna")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        nuance_tts,
        "local_helper_dir",
        lambda: str(tmp_path / "missing_helper"),
    )
    found = nuance_tts.discover_helper_dir()
    assert Path(found).resolve() == tools.resolve()


def test_prefer_javaw_when_present(tmp_path):
    bin_dir = tmp_path / "jre" / "bin"
    bin_dir.mkdir(parents=True)
    java = bin_dir / "java.exe"
    javaw = bin_dir / "javaw.exe"
    java.write_bytes(b"j")
    javaw.write_bytes(b"jw")
    assert Path(nuance_tts._prefer_javaw(str(java))).resolve() == javaw.resolve()
    assert nuance_tts._prefer_javaw(str(javaw)) == str(javaw)


def test_popen_kwargs_hides_console_on_windows():
    kw = nuance_tts._popen_kwargs()
    if os.name != "nt":
        assert kw == {}
        return
    assert "creationflags" in kw
    assert kw["creationflags"] & 0x08000000  # CREATE_NO_WINDOW
    assert "startupinfo" in kw
