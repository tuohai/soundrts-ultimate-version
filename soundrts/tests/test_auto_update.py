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
    # Git's find.exe breaks `tasklist | find "pid"`; wait must not use find.
    assert "| find " not in text.lower()
    assert "tasklist" in text.lower()


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
        assert auto_update.is_check_done()
    finally:
        config.check_updates_on_start = old
        auto_update.reset_check_state_for_tests()


def test_get_pending_timeout_before_done_is_not_up_to_date():
    """A short wait must not be treated as 'no update available'."""
    auto_update.reset_check_state_for_tests()
    assert auto_update.get_pending(wait_timeout=0.05) is None
    assert not auto_update.is_check_done()


def test_offer_pending_update_sync_fallback_when_bg_slow(monkeypatch):
    """If the background check has not finished, fall back to a sync check."""
    from soundrts import clientversion
    from soundrts import config

    info = ReleaseInfo(
        version="9.9.9.9",
        tag_name="9.9.9.9",
        html_url="https://example.test/r",
        body="",
        asset_name="x.zip",
        download_url="https://example.test/a.zip",
        size=1,
        digest="",
    )
    offered = []
    auto_update.reset_check_state_for_tests()
    clientversion._update_prompt_done = False
    old = getattr(config, "check_updates_on_start", 1)
    try:
        config.check_updates_on_start = 1
        # Simulate: wait expires, check still not done.
        monkeypatch.setattr(auto_update, "get_pending", lambda wait_timeout=0.0: None)
        monkeypatch.setattr(auto_update, "is_check_done", lambda: False)
        monkeypatch.setattr(auto_update, "check_for_update", lambda: info)
        monkeypatch.setattr(auto_update, "set_pending", lambda i, error=None: None)
        monkeypatch.setattr(clientversion, "offer_update", lambda i: offered.append(i))
        clientversion.offer_pending_update(timeout=0.0)
        assert offered == [info]
        assert clientversion._update_prompt_done is True
    finally:
        config.check_updates_on_start = old
        clientversion._update_prompt_done = False
        auto_update.reset_check_state_for_tests()


def test_offer_pending_update_uses_bg_result(monkeypatch):
    from soundrts import clientversion
    from soundrts import config

    info = ReleaseInfo(
        version="9.9.9.9",
        tag_name="9.9.9.9",
        html_url="https://example.test/r",
        body="",
        asset_name="x.zip",
        download_url="https://example.test/a.zip",
        size=1,
        digest="",
    )
    offered = []
    sync_calls = []
    auto_update.reset_check_state_for_tests()
    clientversion._update_prompt_done = False
    old = getattr(config, "check_updates_on_start", 1)
    try:
        config.check_updates_on_start = 1
        monkeypatch.setattr(auto_update, "get_pending", lambda wait_timeout=0.0: info)
        monkeypatch.setattr(auto_update, "is_check_done", lambda: True)
        monkeypatch.setattr(
            auto_update,
            "check_for_update",
            lambda: sync_calls.append(1) or None,
        )
        monkeypatch.setattr(clientversion, "offer_update", lambda i: offered.append(i))
        clientversion.offer_pending_update(timeout=0.0)
        assert offered == [info]
        assert sync_calls == []
    finally:
        config.check_updates_on_start = old
        clientversion._update_prompt_done = False
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


def test_check_for_updates_now_up_to_date(monkeypatch):
    from soundrts import clientversion
    from soundrts import msgparts as mp

    spoken = []
    monkeypatch.setattr(clientversion.voice, "alert", lambda msg: spoken.append(msg))
    monkeypatch.setattr(auto_update, "check_for_update", lambda: None)
    monkeypatch.setattr(
        "soundrts.lib.pygame_ui.ensure_window_for_ui", lambda: None, raising=False
    )
    monkeypatch.setattr(
        "soundrts.lib.pygame_ui.show_status_banner", lambda *a, **k: None, raising=False
    )
    monkeypatch.setattr(
        "soundrts.lib.pygame_ui.end_narrative", lambda: None, raising=False
    )
    monkeypatch.setattr(
        "soundrts.lib.pygame_ui.msgparts_to_text", lambda p: "x", raising=False
    )
    clientversion.check_for_updates_now()
    assert spoken[0] == mp.CHECKING_FOR_UPDATES
    assert spoken[-1] == mp.UPDATE_UP_TO_DATE


def test_check_for_updates_now_offers_when_newer(monkeypatch):
    from soundrts import clientversion

    info = ReleaseInfo(
        version="9.9.9.9",
        tag_name="9.9.9.9",
        html_url="https://example.test/r",
        body="",
        asset_name="x.zip",
        download_url="https://example.test/a.zip",
        size=1,
        digest="",
    )
    offered = []
    monkeypatch.setattr(clientversion.voice, "alert", lambda msg: None)
    monkeypatch.setattr(auto_update, "check_for_update", lambda: info)
    monkeypatch.setattr(clientversion, "offer_update", lambda i: offered.append(i))
    monkeypatch.setattr(
        "soundrts.lib.pygame_ui.ensure_window_for_ui", lambda: None, raising=False
    )
    monkeypatch.setattr(
        "soundrts.lib.pygame_ui.show_status_banner", lambda *a, **k: None, raising=False
    )
    monkeypatch.setattr(
        "soundrts.lib.pygame_ui.end_narrative", lambda: None, raising=False
    )
    monkeypatch.setattr(
        "soundrts.lib.pygame_ui.msgparts_to_text", lambda p: "x", raising=False
    )
    clientversion.check_for_updates_now()
    assert offered == [info]


def test_check_for_updates_now_reports_failure(monkeypatch):
    from soundrts import clientversion
    from soundrts import msgparts as mp

    spoken = []
    monkeypatch.setattr(clientversion.voice, "alert", lambda msg: spoken.append(msg))
    monkeypatch.setattr(
        auto_update, "check_for_update", lambda: (_ for _ in ()).throw(RuntimeError("net"))
    )
    monkeypatch.setattr(
        "soundrts.lib.pygame_ui.ensure_window_for_ui", lambda: None, raising=False
    )
    monkeypatch.setattr(
        "soundrts.lib.pygame_ui.show_status_banner", lambda *a, **k: None, raising=False
    )
    monkeypatch.setattr(
        "soundrts.lib.pygame_ui.end_narrative", lambda: None, raising=False
    )
    monkeypatch.setattr(
        "soundrts.lib.pygame_ui.msgparts_to_text", lambda p: "x", raising=False
    )
    clientversion.check_for_updates_now()
    assert spoken[-1] == mp.UPDATE_CHECK_FAILED


def test_check_for_updates_now_ignores_startup_toggle(monkeypatch):
    from soundrts import clientversion
    from soundrts import config
    from soundrts import msgparts as mp

    old = getattr(config, "check_updates_on_start", 1)
    alerts = []
    try:
        config.check_updates_on_start = 0
        monkeypatch.setattr(clientversion.voice, "alert", lambda msg: alerts.append(msg))
        monkeypatch.setattr(auto_update, "check_for_update", lambda: None)
        monkeypatch.setattr(clientversion, "offer_update", lambda info: None)
        monkeypatch.setattr(
            "soundrts.lib.pygame_ui.ensure_window_for_ui", lambda: None, raising=False
        )
        monkeypatch.setattr(
            "soundrts.lib.pygame_ui.show_status_banner",
            lambda *a, **k: None,
            raising=False,
        )
        monkeypatch.setattr(
            "soundrts.lib.pygame_ui.end_narrative", lambda: None, raising=False
        )
        monkeypatch.setattr(
            "soundrts.lib.pygame_ui.msgparts_to_text", lambda p: "x", raising=False
        )
        clientversion.check_for_updates_now()
        assert mp.UPDATE_UP_TO_DATE in alerts
    finally:
        config.check_updates_on_start = old


def test_options_menu_has_manual_check_for_updates():
    src = Path("soundrts/clientmain.py").read_text(encoding="utf-8")
    block = src.split("def options_menu")[1].split("\ndef ")[0]
    assert "CHECK_FOR_UPDATES_NOW" in block
    assert "check_for_updates_now" in block
    assert "CHECK_UPDATES_ON_START" in block


def test_write_update_job_roundtrip(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(auto_update, "TMP_PATH", str(tmp_path))
    monkeypatch.setattr(auto_update, "install_dir", lambda: tmp_path / "game")
    monkeypatch.setattr(auto_update, "client_executable_name", lambda directory=None: "soundrts.exe")
    info = ReleaseInfo(
        version="1.4.6.4",
        tag_name="1.4.6.4",
        html_url="https://example.test/r",
        body="",
        asset_name="pack.zip",
        download_url="https://example.test/pack.zip",
        size=99,
        digest="sha256:abc",
    )
    job_path = auto_update.write_update_job(info, wait_pid=4242)
    data = __import__("json").loads(job_path.read_text(encoding="utf-8"))
    assert data["version"] == "1.4.6.4"
    assert data["wait_pid"] == 4242
    assert data["download_url"].endswith("pack.zip")
    assert data["tmp_dir"]


def test_offer_update_launches_external_then_exits(monkeypatch):
    from soundrts import clientversion
    from soundrts import msgparts as mp
    import soundrts.clientmenu as clientmenu

    info = ReleaseInfo(
        version="9.9.9.9",
        tag_name="9.9.9.9",
        html_url="https://example.test/r",
        body="",
        asset_name="x.zip",
        download_url="https://example.test/a.zip",
        size=1,
        digest="",
    )
    alerts = []
    launched = []
    monkeypatch.setattr(clientversion.voice, "alert", lambda msg: alerts.append(msg))
    monkeypatch.setattr(clientmenu, "confirm_yes_no", lambda *_a, **_k: True)
    monkeypatch.setattr(auto_update, "is_packaged_install", lambda: True)
    monkeypatch.setattr(auto_update, "write_update_job", lambda i: Path("job.json"))
    monkeypatch.setattr(
        auto_update, "launch_external_updater", lambda p: launched.append(str(p))
    )
    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setattr(
        "soundrts.clientmedia.close_media", lambda: None, raising=False
    )
    monkeypatch.setattr(
        "soundrts.lib.pygame_ui.ensure_window_for_ui", lambda: None, raising=False
    )
    monkeypatch.setattr(
        "soundrts.lib.pygame_ui.show_status_banner", lambda *a, **k: None, raising=False
    )
    monkeypatch.setattr(
        "soundrts.lib.pygame_ui.msgparts_to_text", lambda p: "x", raising=False
    )

    try:
        clientversion.offer_update(info)
        assert False, "expected SystemExit"
    except SystemExit as e:
        assert e.code in (0, None)
    assert mp.UPDATE_LAUNCHING_EXTERNAL in alerts
    assert launched == ["job.json"]


def test_offer_update_speaks_changelog_body(monkeypatch):
    """Release notes must be spoken as a flat literal list via blocking menu."""
    from soundrts import clientversion
    from soundrts.lib.msgs import LITERAL_TEXT_PREFIX
    import soundrts.clientmenu as clientmenu

    info = ReleaseInfo(
        version="9.9.9.9",
        tag_name="9.9.9.9",
        html_url="https://example.test/r",
        body="fixed gas depletes",
        asset_name="x.zip",
        download_url="https://example.test/a.zip",
        size=1,
        digest="",
    )
    spoken = []
    monkeypatch.setattr(clientmenu, "confirm_yes_no", lambda *_a, **_k: True)
    monkeypatch.setattr(
        clientversion.voice, "menu", lambda msg, *a, **k: spoken.append(msg)
    )
    monkeypatch.setattr(clientversion.voice, "alert", lambda msg: None)
    monkeypatch.setattr(auto_update, "is_packaged_install", lambda: False)
    monkeypatch.setattr(auto_update, "open_release_page", lambda i: None)
    monkeypatch.setattr(
        "soundrts.lib.pygame_ui.ensure_window_for_ui", lambda: None, raising=False
    )
    monkeypatch.setattr(
        "soundrts.lib.pygame_ui.show_narrative", lambda *a, **k: None, raising=False
    )
    monkeypatch.setattr(
        "soundrts.lib.pygame_ui.show_status_banner", lambda *a, **k: None, raising=False
    )
    monkeypatch.setattr(
        "soundrts.lib.pygame_ui.end_narrative", lambda: None, raising=False
    )
    monkeypatch.setattr(
        "soundrts.lib.pygame_ui.msgparts_to_text",
        lambda parts: "fixed gas depletes",
        raising=False,
    )

    clientversion.offer_update(info)

    assert spoken, "changelog should be spoken"
    assert spoken[0] == [LITERAL_TEXT_PREFIX + "fixed gas depletes"]
    # Must not nest the literal list: [["文本: ..."]]
    assert not isinstance(spoken[0][0], list)


def test_confirm_yes_no_uses_visual_prompt():
    src = Path("soundrts/clientmenu.py").read_text(encoding="utf-8")
    block = src.split("def confirm_yes_no", 1)[1].split("\ndef ", 1)[0]
    assert "show_confirm" in block
    assert "confirm_button_at" in block
    assert "draw_confirm" in block


def test_pygame_ui_has_confirm_helpers():
    src = Path("soundrts/lib/pygame_ui.py").read_text(encoding="utf-8")
    assert "def show_confirm" in src
    assert "def draw_confirm" in src
    assert "def confirm_button_at" in src
    assert "def raise_game_window" in src


def test_soundrts_entry_handles_update_flag():
    entry = Path("soundrts.py").read_text(encoding="utf-8")
    assert "--soundrts-update" in entry
    assert "update_window" in entry


def test_update_window_pid_helper():
    from soundrts.update_window import _pid_alive

    assert _pid_alive(0) is False
    assert _pid_alive(-1) is False


def test_update_window_uses_ui_queue():
    src = Path("soundrts/update_window.py").read_text(encoding="utf-8")
    assert "queue.Queue" in src
    assert "_poll_ui" in src


def test_update_window_has_tkinter_fallback():
    src = Path("soundrts/update_window.py").read_text(encoding="utf-8")
    assert "except ImportError" in src
    assert "run_update_headless" in src
    assert "if tk is None" in src
    assert "_ensure_tcl_env" in src
    assert 'base / "share" / "tcl8.6"' in src


def test_setup_py_does_not_exclude_tkinter():
    src = Path("setup.py").read_text(encoding="utf-8")
    start = src.index('"excludes"')
    end = src.index("]", start)
    excludes = src[start:end]
    assert "tkinter" not in excludes
    assert '"packages": ["tkinter"]' in src or '"tkinter"' in src.split("packages")[1].split("excludes")[0]
    # cx_Freeze already copies Tcl/Tk into share/; do not duplicate at install root.
    assert "_add_tkinter_runtime" not in src
    assert 'for name in ("tcl8.6", "tk8.6", "tcl8")' not in src


def test_update_window_avoids_auto_update_import():
    """Updater process must not import auto_update (config/resource hang)."""
    src = Path("soundrts/update_window.py").read_text(encoding="utf-8")
    assert "from . import auto_update" not in src
    assert "import auto_update\n" not in src
    assert "update_core" in src
