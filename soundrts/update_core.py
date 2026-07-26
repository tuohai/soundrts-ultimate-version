"""Stdlib-only update helpers for the standalone updater process.

This module must NOT import ``config``, ``paths``, ``version``, pygame, or TTS —
those imports hang or pull the full game into ``soundrts.exe --soundrts-update``.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

_USER_AGENT = "SoundRTS-AutoUpdate"
_SKIP_DIR_NAMES = frozenset({"user"})
_CLIENT_EXE_NAMES = ("soundrts.exe", "SoundRTS.exe")


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


def find_game_root(extract_dir: Path) -> Path | None:
    """Locate the folder that contains the client executable after extract."""
    extract_dir = extract_dir.resolve()
    for name in _CLIENT_EXE_NAMES:
        direct = extract_dir / name
        if direct.is_file():
            return extract_dir
    matches: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(extract_dir):
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
    user_agent: str = _USER_AGENT,
) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    req = urllib.request.Request(
        info.download_url,
        headers={"User-Agent": user_agent},
    )
    with urllib.request.urlopen(req, timeout=120) as resp, open(dest, "wb") as out:
        total = int(resp.headers.get("Content-Length") or info.size or 0)
        done = 0
        last_report = -1
        last_bytes_report = 0
        while True:
            chunk = resp.read(256 * 1024)
            if not chunk:
                break
            out.write(chunk)
            done += len(chunk)
            if not progress_callback:
                continue
            if total > 0:
                pct = min(100, int(done * 100 / total))
                if pct >= last_report + 1 or pct == 100:
                    last_report = pct
                    progress_callback(pct, done, total)
            elif done >= last_bytes_report + 1024 * 1024:
                last_bytes_report = done
                progress_callback(0, done, 0)
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
    tmp_dir: Path,
) -> Path:
    """Write a minimal Windows batch that applies the staged update after exit."""
    tmp_dir = Path(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    script_path = tmp_dir / "soundrts_apply_update.bat"
    log_path = tmp_dir / "soundrts_apply_update.log"
    cleanup_lines = []
    for p in cleanup_paths:
        if not p:
            continue
        path = Path(p)
        if not str(path):
            continue
        cleanup_lines.append(
            f"if exist {_bat_quote(path)} rmdir /s /q {_bat_quote(path)} 2>nul"
        )
        cleanup_lines.append(
            f"if exist {_bat_quote(path)} del /f /q {_bat_quote(path)} 2>nul"
        )
    cleanup_block = "\n".join(cleanup_lines)
    # Do NOT use `find` here: Git for Windows ships GNU find.exe ahead of
    # System32 on many PATHs, which breaks `tasklist | find "pid"` and can
    # spam a console with `find "12345"`.
    content = f"""@echo off
setlocal EnableExtensions
set "LOG={log_path}"
echo SoundRTS update apply started > "%LOG%"
echo waiting for pid {pid} >> "%LOG%"
:wait
set "STILL="
for /f "tokens=2 delims=," %%A in ('tasklist /FI "PID eq {pid}" /FO CSV /NH 2^>NUL') do (
  if "%%~A"=="{pid}" set "STILL=1"
)
if defined STILL (
  ping -n 2 127.0.0.1 >NUL
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
    # ASCII-only batch avoids cmd.exe misreading UTF-8 and ignoring @echo off.
    script_path.write_text(content, encoding="ascii", errors="replace")
    return script_path


def launch_apply_and_exit(script_path: Path) -> None:
    creationflags = 0
    if sys.platform == "win32":
        # Prefer a hidden console; DETACHED alone still flashes a cmd window
        # on some systems and can surface wait-loop noise.
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        if not creationflags:
            creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(
                subprocess, "DETACHED_PROCESS", 0x00000008
            )
    subprocess.Popen(
        ["cmd.exe", "/c", str(script_path)],
        cwd=str(Path(script_path).parent),
        close_fds=True,
        creationflags=creationflags,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
