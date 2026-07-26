"""GitHub release auto-updater for packaged Windows builds.

Flow: check latest release → prompt → download/extract in-process →
write a short apply.bat that waits for this process to exit, copies files
(skipping ``user``), relaunches the game, then cleans up.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from . import config
from .lib.log import warning
from .paths import TMP_PATH
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
_SKIP_DIR_NAMES = frozenset({"user"})
_CLIENT_EXE_NAMES = ("soundrts.exe", "SoundRTS.exe")

_lock = threading.Lock()
_check_done = False
_pending: "ReleaseInfo | None" = None
_check_error: str | None = None


@dataclass(frozen=True)
class ReleaseInfo:
    version: str
    tag_name: str
    html_url: str
    body: str
    asset_name: str
    download_url: str
    size: int
    digest: str  # "" or "sha256:hex"


def parse_version(text: str) -> tuple[int, ...]:
    """Parse ``1.4.6.3`` / ``v1.4.6.3`` into a comparable tuple."""
    s = (text or "").strip()
    if s.lower().startswith("v") and len(s) > 1 and s[1].isdigit():
        s = s[1:]
    parts: list[int] = []
    for piece in s.split("."):
        m = re.match(r"(\d+)", piece)
        parts.append(int(m.group(1)) if m else 0)
    return tuple(parts) if parts else (0,)


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
    # Prefer names that look like the game package.
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


def find_game_root(extract_dir: Path) -> Path | None:
    """Locate the folder that contains the client executable after extract."""
    extract_dir = extract_dir.resolve()
    for name in _CLIENT_EXE_NAMES:
        direct = extract_dir / name
        if direct.is_file():
            return extract_dir
    matches: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(extract_dir):
        # Do not descend into nested user trees while searching.
        dirnames[:] = [d for d in dirnames if d.lower() not in _SKIP_DIR_NAMES]
        lower = {f.lower() for f in filenames}
        if "soundrts.exe" in lower:
            matches.append(Path(dirpath))
    if not matches:
        return None
    matches.sort(key=lambda p: (len(p.parts), str(p).lower()))
    return matches[0]


def _verify_digest(path: Path, digest: str) -> bool:
    if not digest:
        return True
    kind, _, hexdigest = digest.partition(":")
    if kind.lower() != "sha256" or not hexdigest:
        return True
    h = sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest().lower() == hexdigest.lower()


def download_release(
    info: ReleaseInfo,
    dest: Path,
    progress_callback=None,
) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    req = urllib.request.Request(
        info.download_url,
        headers={"User-Agent": _USER_AGENT},
    )
    with urllib.request.urlopen(req, timeout=120) as resp, open(dest, "wb") as out:
        total = int(resp.headers.get("Content-Length") or info.size or 0)
        done = 0
        last_report = -1
        while True:
            chunk = resp.read(256 * 1024)
            if not chunk:
                break
            out.write(chunk)
            done += len(chunk)
            if progress_callback and total > 0:
                pct = min(100, int(done * 100 / total))
                if pct >= last_report + 10 or pct == 100:
                    last_report = pct
                    progress_callback(pct, done, total)
    if not _verify_digest(dest, info.digest):
        dest.unlink(missing_ok=True)
        raise ValueError("download digest mismatch")
    return dest


def extract_zip(zip_path: Path, dest_dir: Path) -> Path:
    if dest_dir.exists():
        shutil.rmtree(dest_dir, ignore_errors=True)
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            name = member.filename.replace("\\", "/")
            if ".." in name.split("/"):
                continue
            zf.extract(member, dest_dir)
    root = find_game_root(dest_dir)
    if root is None:
        raise FileNotFoundError("client executable not found in archive")
    return root


def _bat_quote(path: str | Path) -> str:
    return f'"{path}"'


def write_apply_script(
    staging_root: Path,
    target_dir: Path,
    exe_name: str,
    pid: int,
    cleanup_paths: list[Path],
) -> Path:
    """Write a minimal Windows batch that applies the staged update after exit."""
    script_path = Path(TMP_PATH) / "soundrts_apply_update.bat"
    log_path = Path(TMP_PATH) / "soundrts_apply_update.log"
    cleanup_lines = []
    for p in cleanup_paths:
        cleanup_lines.append(f'if exist {_bat_quote(p)} rmdir /s /q {_bat_quote(p)} 2>nul')
        cleanup_lines.append(f'if exist {_bat_quote(p)} del /f /q {_bat_quote(p)} 2>nul')
    cleanup_block = "\n".join(cleanup_lines)
    content = f"""@echo off
setlocal EnableExtensions
set "LOG={log_path}"
echo SoundRTS update apply started > "%LOG%"
echo waiting for pid {pid} >> "%LOG%"
:wait
tasklist /FI "PID eq {pid}" 2>NUL | find "{pid}" >NUL
if not errorlevel 1 (
  timeout /t 1 /nobreak >NUL
  goto wait
)
echo copying from {staging_root} to {target_dir} >> "%LOG%"
robocopy {_bat_quote(staging_root)} {_bat_quote(target_dir)} /E /XD user /R:2 /W:1 /NFL /NDL /NJH /NJS /NC /NS /NP
set "RC=%ERRORLEVEL%"
echo robocopy exit %RC% >> "%LOG%"
if %RC% GEQ 8 (
  echo copy failed >> "%LOG%"
  exit /b 1
)
echo launching {exe_name} >> "%LOG%"
start "" {_bat_quote(target_dir / exe_name)}
{cleanup_block}
del /f /q {_bat_quote(script_path)} >nul 2>&1
endlocal
"""
    script_path.write_text(content, encoding="utf-8")
    return script_path


def launch_apply_and_exit(script_path: Path) -> None:
    creationflags = 0
    if sys.platform == "win32":
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(
            subprocess, "DETACHED_PROCESS", 0x00000008
        )
    subprocess.Popen(
        ["cmd.exe", "/c", str(script_path)],
        cwd=str(script_path.parent),
        close_fds=True,
        creationflags=creationflags,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def prepare_and_apply(info: ReleaseInfo, progress_callback=None) -> Path:
    """Download, extract, write apply script. Returns the script path."""
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


def get_pending(wait_timeout: float = 0.0) -> ReleaseInfo | None:
    deadline = time.time() + max(0.0, wait_timeout)
    while True:
        with _lock:
            done = _check_done
            pending = _pending
        if done or time.time() >= deadline:
            return pending
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
