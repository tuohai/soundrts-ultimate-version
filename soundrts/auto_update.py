"""GitHub release auto-updater for packaged Windows builds.

Flow: check latest release → prompt in game → launch a separate update
window process → game exits → updater downloads/extracts with a progress
UI → apply.bat overwrites install (skipping ``user``) and relaunches.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

from . import config
from .lib.log import warning
from .paths import TMP_PATH
from .update_core import (
    ReleaseInfo,
    download_release,
    extract_zip,
    find_game_root,
    launch_apply_and_exit,
    write_apply_script as _write_apply_script_core,
)
from .version import VERSION

GITHUB_OWNER = "tuohai"
GITHUB_REPO = "soundrts-ultimate-version"
GITHUB_API_LATEST = (
    f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
)
GITHUB_RELEASES_PAGE = (
    f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
)
_USER_AGENT = f"SoundRTS-AutoUpdate/{VERSION}"
_CLIENT_EXE_NAMES = ("soundrts.exe", "SoundRTS.exe")
UPDATE_JOB_NAME = "soundrts_update_job.json"

_lock = threading.Lock()
_check_done = False
_pending: "ReleaseInfo | None" = None
_check_error: str | None = None

# Re-export for tests / callers.
__all__ = [
    "ReleaseInfo",
    "download_release",
    "extract_zip",
    "find_game_root",
    "launch_apply_and_exit",
    "write_apply_script",
]


def parse_version(text: str) -> tuple[int, ...]:
    """Parse ``1.4.6.3`` / ``v1.4.6.3`` / ``1.5`` into a 4-part comparable tuple."""
    s = (text or "").strip()
    if s.lower().startswith("v") and len(s) > 1 and s[1].isdigit():
        s = s[1:]
    parts: list[int] = []
    for piece in s.split("."):
        m = re.match(r"(\d+)", piece)
        parts.append(int(m.group(1)) if m else 0)
    if not parts:
        parts = [0]
    while len(parts) < 4:
        parts.append(0)
    return tuple(parts)


def is_newer(remote: str, local: str = VERSION) -> bool:
    return parse_version(remote) > parse_version(local)


def is_packaged_install() -> bool:
    return bool(getattr(sys, "frozen", False))


def install_dir() -> Path:
    if is_packaged_install():
        return Path(sys.executable).resolve().parent
    return Path(os.getcwd()).resolve()


def client_executable_name(directory: Path | None = None) -> str:
    root = directory or install_dir()
    for name in _CLIENT_EXE_NAMES:
        if (root / name).is_file():
            return name
    if sys.platform == "win32":
        return "soundrts.exe"
    return "SoundRTS"


def select_windows_asset(assets: list[dict]) -> dict | None:
    """Pick the Windows game zip from a GitHub release assets list."""
    candidates = []
    for asset in assets or []:
        name = str(asset.get("name") or "")
        lower = name.lower()
        if not lower.endswith(".zip"):
            continue
        if "windows" not in lower:
            continue
        if "source" in lower or "src" in lower:
            continue
        candidates.append(asset)
    if not candidates:
        return None
    candidates.sort(
        key=lambda a: (
            0 if "ultimate" in str(a.get("name") or "").lower() else 1,
            -int(a.get("size") or 0),
        )
    )
    return candidates[0]


def _http_json(url: str, timeout: float = 20.0) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": _USER_AGENT,
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_latest_release() -> ReleaseInfo | None:
    data = _http_json(GITHUB_API_LATEST)
    tag = str(data.get("tag_name") or "").strip()
    if not tag:
        return None
    asset = select_windows_asset(data.get("assets") or [])
    if not asset:
        return None
    version = tag[1:] if tag.lower().startswith("v") and len(tag) > 1 else tag
    return ReleaseInfo(
        version=version,
        tag_name=tag,
        html_url=str(data.get("html_url") or GITHUB_RELEASES_PAGE),
        body=str(data.get("body") or "").strip(),
        asset_name=str(asset.get("name") or ""),
        download_url=str(asset.get("browser_download_url") or ""),
        size=int(asset.get("size") or 0),
        digest=str(asset.get("digest") or ""),
    )


def check_for_update() -> ReleaseInfo | None:
    """Return release info when remote is newer than local; else None."""
    info = fetch_latest_release()
    if info is None:
        return None
    if not is_newer(info.version, VERSION):
        return None
    return info


def write_apply_script(
    staging_root: Path,
    target_dir: Path,
    exe_name: str,
    pid: int,
    cleanup_paths: list[Path],
    tmp_dir: Path | None = None,
) -> Path:
    return _write_apply_script_core(
        staging_root=staging_root,
        target_dir=target_dir,
        exe_name=exe_name,
        pid=pid,
        cleanup_paths=cleanup_paths,
        tmp_dir=Path(tmp_dir) if tmp_dir is not None else Path(TMP_PATH),
    )


def write_update_job(info: ReleaseInfo, wait_pid: int | None = None) -> Path:
    """Persist release info for the external updater process."""
    job_path = Path(TMP_PATH) / UPDATE_JOB_NAME
    payload = {
        "version": info.version,
        "tag_name": info.tag_name,
        "html_url": info.html_url,
        "asset_name": info.asset_name,
        "download_url": info.download_url,
        "size": int(info.size or 0),
        "digest": info.digest or "",
        "target_dir": str(install_dir()),
        "exe_name": client_executable_name(),
        "wait_pid": int(wait_pid if wait_pid is not None else os.getpid()),
        "tmp_dir": str(Path(TMP_PATH).resolve()),
    }
    job_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return job_path


def launch_external_updater(job_path: Path) -> None:
    """Start the standalone update window, then the caller should exit the game."""
    if sys.platform != "win32":
        raise RuntimeError("external updater is only supported on Windows")
    job_path = Path(job_path).resolve()
    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(
        subprocess, "DETACHED_PROCESS", 0x00000008
    )
    if is_packaged_install():
        cmd = [sys.executable, "--soundrts-update", str(job_path)]
        cwd = str(install_dir())
    else:
        entry = Path(sys.argv[0]).resolve()
        if entry.suffix.lower() == ".py":
            cmd = [sys.executable, str(entry), "--soundrts-update", str(job_path)]
        else:
            cmd = [sys.executable, "-m", "soundrts.update_window", str(job_path)]
        cwd = str(install_dir())
    subprocess.Popen(
        cmd,
        cwd=cwd,
        close_fds=True,
        creationflags=creationflags,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def prepare_and_apply(info: ReleaseInfo, progress_callback=None) -> Path:
    """Legacy in-process download/extract (tests / fallback). Prefer external UI."""
    if sys.platform != "win32":
        raise RuntimeError("in-place auto-update is only supported on Windows")
    if not is_packaged_install():
        raise RuntimeError("in-place auto-update requires a packaged build")
    stamp = info.version.replace(".", "_")
    zip_path = Path(TMP_PATH) / f"soundrts_update_{stamp}.zip"
    extract_dir = Path(TMP_PATH) / f"soundrts_update_{stamp}_extract"
    download_release(info, zip_path, progress_callback=progress_callback)
    staging_root = extract_zip(zip_path, extract_dir)
    target = install_dir()
    exe_name = client_executable_name(staging_root)
    script = write_apply_script(
        staging_root=staging_root,
        target_dir=target,
        exe_name=exe_name,
        pid=os.getpid(),
        cleanup_paths=[zip_path, extract_dir],
    )
    return script


def open_release_page(info: ReleaseInfo | None = None) -> None:
    import webbrowser

    webbrowser.open((info.html_url if info else None) or GITHUB_RELEASES_PAGE)


def set_pending(info: ReleaseInfo | None, error: str | None = None) -> None:
    global _pending, _check_done, _check_error
    with _lock:
        _pending = info
        _check_error = error
        _check_done = True


def is_check_done() -> bool:
    with _lock:
        return _check_done


def get_pending(wait_timeout: float = 0.0) -> ReleaseInfo | None:
    """Return the background-check result, waiting up to ``wait_timeout``.

    If the timeout expires before the check finishes, returns ``None`` and
    ``is_check_done()`` stays false — callers must not treat that as
    "already up to date".
    """
    deadline = time.time() + max(0.0, wait_timeout)
    while True:
        with _lock:
            done = _check_done
            pending = _pending
        if done:
            return pending
        if time.time() >= deadline:
            return None
        time.sleep(0.05)


def run_background_check() -> None:
    """Fetch latest release and store it when newer than local."""
    global _check_done
    with _lock:
        _check_done = False
    try:
        if not int(getattr(config, "check_updates_on_start", 1)):
            set_pending(None)
            return
        info = check_for_update()
        set_pending(info)
    except Exception as e:
        warning("auto-update check failed: %s", e)
        set_pending(None, error=str(e))


def reset_check_state_for_tests() -> None:
    global _check_done, _pending, _check_error
    with _lock:
        _check_done = False
        _pending = None
        _check_error = None
