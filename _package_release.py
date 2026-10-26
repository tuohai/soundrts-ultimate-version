"""Package the cx_Freeze build into the release zip.

Version-agnostic: reads VERSION from soundrts/version.py, so it never needs
editing when the version is bumped.

Input : %TEMP%\\soundrts-<VERSION>-windows
Output: %TEMP%\\soundrts-<VERSION>-ultimate.version-windows.zip

The zip stays in TEMP -- it is NOT written into the repo's artifacts/ folder.
"""

from __future__ import annotations

import os
import re
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# Release asset name: lower-case "soundrts", literal "ultimate.version",
# no "-x64" suffix. The in-game auto-updater prefers this name.
RELEASE_SUFFIX = "ultimate.version-windows"


def read_version() -> str:
    text = (ROOT / "soundrts" / "version.py").read_text(encoding="utf-8")
    match = re.search(r'^VERSION\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
    if not match:
        raise SystemExit("FATAL: could not read VERSION from soundrts/version.py")
    return match.group(1)


def main() -> int:
    version = read_version()
    tmp = Path(os.environ["TEMP"])
    src = tmp / f"soundrts-{version}-windows"
    stage = tmp / f"soundrts-{version}-{RELEASE_SUFFIX}"
    zip_path = tmp / f"soundrts-{version}-{RELEASE_SUFFIX}.zip"

    if not (src / "soundrts.exe").is_file():
        print(f"FATAL: build output not found: {src}\\soundrts.exe")
        print("Run _build_cxfreeze.cmd first.")
        return 1

    print(f"[package] version : {version}")
    print(f"[package] source  : {src}")
    print(f"[package] staging : {stage}")

    if stage.exists():
        shutil.rmtree(stage)
    shutil.move(str(src), str(stage))
    if not (stage / "soundrts.exe").is_file():
        print("FATAL: staging rename failed")
        return 1

    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(stage.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(stage.parent))
    print(f"[package] created : {zip_path} ({zip_path.stat().st_size} bytes)")
    print(f"[package] upload  : gh release upload {version} \"{zip_path}\" --clobber")
    return 0


if __name__ == "__main__":
    sys.exit(main())
