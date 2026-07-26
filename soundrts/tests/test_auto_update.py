"""Unit tests for GitHub auto-update helpers."""

import zipfile
from pathlib import Path

from soundrts import auto_update
from soundrts.auto_update import ReleaseInfo


def test_parse_version_strips_v_prefix():
    assert auto_update.parse_version("v1.4.6.3") == (1, 4, 6, 3)
    assert auto_update.parse_version("1.4.6.3") == (1, 4, 6, 3)


def test_is_newer_compares_full_version():
    assert auto_update.is_newer("1.4.6.3", "1.4.6.2")
    assert not auto_update.is_newer("1.4.6.2", "1.4.6.2")
    assert not auto_update.is_newer("1.4.6.1", "1.4.6.2")
    assert auto_update.is_newer("1.4.7.0", "1.4.6.9")


def test_select_windows_asset_prefers_game_zip():
    assets = [
        {"name": "source.zip", "size": 10, "browser_download_url": "u0"},
        {
            "name": "soundrts-1.4.6.3-ultimate.version-windows.zip",
            "size": 100,
            "browser_download_url": "u1",
        },
        {
            "name": "SoundRTS-1.4.6.3-windows-x64.zip",
            "size": 90,
            "browser_download_url": "u2",
        },
    ]
    chosen = auto_update.select_windows_asset(assets)
    assert chosen["browser_download_url"] == "u1"


def test_select_windows_asset_returns_none_without_windows_zip():
    assert auto_update.select_windows_asset([{"name": "notes.txt", "size": 1}]) is None
    assert (
        auto_update.select_windows_asset(
            [{"name": "soundrts-src-windows-source.zip", "size": 1}]
        )
        is None
    )


def test_find_game_root_nested(tmp_path: Path):
    root = tmp_path / "soundrts-1.4.6.3-ultimate version-windows"
    root.mkdir()
    (root / "soundrts.exe").write_bytes(b"mz")
    (root / "cfg").mkdir()
    (root / "user" / "voices").mkdir(parents=True)
    (root / "user" / "voices" / "x.exe").write_bytes(b"x")
    found = auto_update.find_game_root(tmp_path)
    assert found == root


def test_extract_zip_and_find_root(tmp_path: Path):
    bundle = tmp_path / "bundle"
    game = bundle / "pack"
    game.mkdir(parents=True)
    (game / "soundrts.exe").write_bytes(b"exe")
    (game / "readme.txt").write_text("ok", encoding="utf-8")
    zip_path = tmp_path / "update.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(game / "soundrts.exe", "pack/soundrts.exe")
        zf.write(game / "readme.txt", "pack/readme.txt")
    extract_dir = tmp_path / "out"
    root = auto_update.extract_zip(zip_path, extract_dir)
    assert root.name == "pack"
    assert (root / "soundrts.exe").is_file()


def test_write_apply_script_contains_robocopy_and_skip_user(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(auto_update, "TMP_PATH", str(tmp_path))
    staging = tmp_path / "stage"
    staging.mkdir()
    (staging / "soundrts.exe").write_bytes(b"x")
    target = tmp_path / "install"
    target.mkdir()
    script = auto_update.write_apply_script(
        staging_root=staging,
        target_dir=target,
        exe_name="soundrts.exe",
        pid=12345,
        cleanup_paths=[tmp_path / "update.zip"],
    )
    text = script.read_text(encoding="utf-8")
    assert "robocopy" in text.lower()
    assert "/XD user" in text
    assert "12345" in text
    assert "soundrts.exe" in text


def test_run_background_check_respects_config(monkeypatch):
    auto_update.reset_check_state_for_tests()
    from soundrts import config

    old = getattr(config, "check_updates_on_start", 1)
    try:
        config.check_updates_on_start = 0
        auto_update.run_background_check()
        assert auto_update.get_pending(wait_timeout=0) is None
    finally:
        config.check_updates_on_start = old
        auto_update.reset_check_state_for_tests()


def test_run_background_check_stores_newer_release(monkeypatch):
    auto_update.reset_check_state_for_tests()
    from soundrts import config

    info = ReleaseInfo(
        version="9.9.9.9",
        tag_name="9.9.9.9",
        html_url="https://example.test/r",
        body="notes",
        asset_name="soundrts-9.9.9.9-windows.zip",
        download_url="https://example.test/a.zip",
        size=12,
        digest="",
    )

    old = getattr(config, "check_updates_on_start", 1)
    try:
        config.check_updates_on_start = 1
        monkeypatch.setattr(auto_update, "check_for_update", lambda: info)
        auto_update.run_background_check()
        pending = auto_update.get_pending(wait_timeout=0)
        assert pending is not None
        assert pending.version == "9.9.9.9"
    finally:
        config.check_updates_on_start = old
        auto_update.reset_check_state_for_tests()


def test_fetch_latest_release_parses_api_payload(monkeypatch):
    payload = {
        "tag_name": "v1.4.6.9",
        "html_url": "https://github.com/example/releases/tag/v1.4.6.9",
        "body": "hello",
        "assets": [
            {
                "name": "soundrts-1.4.6.9-ultimate.version-windows.zip",
                "browser_download_url": "https://example.test/file.zip",
                "size": 42,
                "digest": "sha256:abc",
            }
        ],
    }
    monkeypatch.setattr(auto_update, "_http_json", lambda url: payload)
    info = auto_update.fetch_latest_release()
    assert info is not None
    assert info.version == "1.4.6.9"
    assert info.download_url.endswith("file.zip")
    assert info.digest == "sha256:abc"
