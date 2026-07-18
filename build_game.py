"""Build SoundRTS distributable CI artifacts with PyInstaller."""

from __future__ import annotations

import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
import sysconfig
import tarfile
import tempfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parent
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"
ARTIFACTS_DIR = ROOT / "artifacts"
BUNDLE_NAME = "SoundRTS"
RESOURCE_DIRS = ("cfg", "res", "mods", "doc")
# Redistributable Nuance helper (jars only; voice data stays in user/voices).
NUANCE_HELPER_SRC = ROOT / "tools" / "nuance_ve"
NUANCE_HELPER_JARS = ("nuance_ve_helper.jar", "jna.jar")
SAPI32_HELPER_SRC = ROOT / "tools" / "sapi32"
SAPI32_HELPER_FILES = ("helper.ps1",)


def _run(command: list[str], **kwargs) -> None:
    print("+", " ".join(command), flush=True)
    kwargs.setdefault("cwd", ROOT)
    subprocess.run(command, check=True, **kwargs)


def _git_describe() -> str:
    try:
        return subprocess.check_output(
            ["git", "describe", "--tags", "--always", "--dirty"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return f"{_version()}-unknown"


def _version() -> str:
    version_py = ROOT / "soundrts" / "version.py"
    match = re.search(
        r'^VERSION\s*=\s*["\']([^"\']+)["\']',
        version_py.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    if not match:
        raise RuntimeError(f"Could not read VERSION from {version_py}")
    return match.group(1)


def _default_artifact_suffix() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()
    arch = {
        "amd64": "x64",
        "x86_64": "x64",
        "aarch64": "arm64",
        "arm64": "arm64",
    }.get(machine, machine or "unknown")
    system_name = {
        "darwin": "macos",
        "linux": "linux",
        "windows": "windows",
    }.get(system, system or "unknown")
    return f"{system_name}-{arch}"


def _bundle_dir() -> Path:
    return DIST_DIR / BUNDLE_NAME


def _client_executable(bundle_dir: Path) -> Path:
    exe_name = "SoundRTS.exe" if platform.system() == "Windows" else "SoundRTS"
    return bundle_dir / exe_name


def _server_executable(bundle_dir: Path) -> Path:
    exe_name = "SoundRTS-server.exe" if platform.system() == "Windows" else "SoundRTS-server"
    return bundle_dir / exe_name


def _clean() -> None:
    for path in (DIST_DIR, BUILD_DIR, ARTIFACTS_DIR):
        if path.exists():
            shutil.rmtree(path)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


def _build_docs() -> None:
    import builddoc

    print("[build] Building documentation...")
    builddoc.build()


def _build_cython() -> None:
    print("[build] Building Cython extensions...")
    env = os.environ.copy()
    env["SOUNDRTS_CYTHON_BUILD_DIR"] = str(BUILD_DIR / "cythonized")
    _run([sys.executable, "setup_cython.py", "build_ext", "--inplace"], env=env)
    outputs = _compiled_extension_outputs()
    if not outputs:
        raise RuntimeError("Cython build produced no extension modules for this Python.")
    print(f"[build] Cython outputs: {len(outputs)}")


def _compiled_extension_outputs() -> list[Path]:
    suffix = sysconfig.get_config_var("EXT_SUFFIX")
    if not suffix:
        return []
    return sorted((ROOT / "soundrts").rglob(f"*{suffix}"))


def _build_pyinstaller() -> None:
    print("[build] Building PyInstaller bundle...")
    _run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "soundrts.spec"])


def _expose_resources(bundle_dir: Path) -> None:
    """Move application resources next to the executables on every platform."""
    internal = bundle_dir / "_internal"
    if not internal.is_dir():
        raise RuntimeError(f"Bundle is missing the contents directory: {internal}")
    for name in RESOURCE_DIRS:
        source = internal / name
        target = bundle_dir / name
        if not source.exists():
            raise RuntimeError(f"Bundle is missing required internal resource path: {source}")
        if target.exists():
            raise RuntimeError(f"Cannot expose resource path because it already exists: {target}")
        shutil.move(source, target)


def _copy_nuance_helper(bundle_dir: Path) -> None:
    """Ship Java helper jars next to the exe so packed builds can use Apple voices."""
    missing = [n for n in NUANCE_HELPER_JARS if not (NUANCE_HELPER_SRC / n).is_file()]
    if missing:
        print(
            f"[build] WARNING: skipping Nuance helper (missing {', '.join(missing)} "
            f"under {NUANCE_HELPER_SRC})",
            flush=True,
        )
        return
    dest = bundle_dir / "tools" / "nuance_ve"
    dest.mkdir(parents=True, exist_ok=True)
    for name in NUANCE_HELPER_JARS:
        shutil.copy2(NUANCE_HELPER_SRC / name, dest / name)
    readme = NUANCE_HELPER_SRC / "README.md"
    if readme.is_file():
        shutil.copy2(readme, dest / "README.md")
    print(f"[build] Copied Nuance helper jars to {dest}", flush=True)


def _copy_sapi32_helper(bundle_dir: Path) -> None:
    """Ship 32-bit SAPI helper (VW Julie etc. only visible to SysWOW64)."""
    missing = [n for n in SAPI32_HELPER_FILES if not (SAPI32_HELPER_SRC / n).is_file()]
    if missing:
        print(
            f"[build] WARNING: skipping sapi32 helper (missing {', '.join(missing)})",
            flush=True,
        )
        return
    dest = bundle_dir / "tools" / "sapi32"
    dest.mkdir(parents=True, exist_ok=True)
    for name in SAPI32_HELPER_FILES:
        shutil.copy2(SAPI32_HELPER_SRC / name, dest / name)
    print(f"[build] Copied sapi32 helper to {dest}", flush=True)


def _write_full_version(bundle_dir: Path) -> None:
    lib_dir = bundle_dir / "lib"
    lib_dir.mkdir(parents=True, exist_ok=True)
    (lib_dir / "full_version.txt").write_text(_git_describe(), encoding="utf-8")


def _validate_bundle(bundle_dir: Path) -> None:
    required_paths = (
        "cfg",
        "cfg/parameters.toml",
        "res",
        "mods",
        "doc",
        "lib/full_version.txt",
    )
    missing = [name for name in required_paths if not (bundle_dir / name).exists()]
    if missing:
        raise RuntimeError(f"Bundle is missing required resource paths: {', '.join(missing)}")
    extension_patterns = ("*.pyd", "*.so", "*.dylib")
    runtime_root = bundle_dir / "_internal"
    if not runtime_root.is_dir():
        raise RuntimeError(f"Bundle is missing the contents directory: {runtime_root}")
    extensions = [
        path
        for pattern in extension_patterns
        for path in (runtime_root / "soundrts").rglob(pattern)
    ]
    if not extensions:
        raise RuntimeError("Bundle is missing compiled Cython extension modules.")
    exe = _client_executable(bundle_dir)
    if not exe.exists():
        raise RuntimeError(f"Bundle is missing client executable: {exe}")
    server_exe = _server_executable(bundle_dir)
    if not server_exe.exists():
        raise RuntimeError(f"Bundle is missing server executable: {server_exe}")
    print(f"[build] Bundle validation passed with {len(extensions)} compiled extensions.")


def _smoke_test(bundle_dir: Path) -> None:
    exe = _server_executable(bundle_dir)
    env = os.environ.copy()
    env.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    env.setdefault("SDL_VIDEODRIVER", "dummy")
    env.setdefault("SDL_AUDIODRIVER", "dummy")
    tmp = tempfile.mkdtemp(prefix="soundrts-smoke-")
    env["HOME"] = tmp
    if platform.system() == "Windows":
        env["APPDATA"] = tmp
    try:
        _run([str(exe), "--help"], env=env, cwd=tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _archive_zip(bundle_dir: Path, target: Path) -> None:
    with ZipFile(target, "w", compression=ZIP_DEFLATED) as zip_file:
        for path in bundle_dir.rglob("*"):
            if path.is_file():
                zip_file.write(path, path.relative_to(bundle_dir.parent))


def _archive_tar_gz(bundle_dir: Path, target: Path) -> None:
    with tarfile.open(target, "w:gz") as tar:
        tar.add(bundle_dir, arcname=bundle_dir.name)


def _archive(bundle_dir: Path, artifact_suffix: str) -> Path:
    base_name = f"SoundRTS-{_version()}-{artifact_suffix}"
    if artifact_suffix.startswith("linux-"):
        target = ARTIFACTS_DIR / f"{base_name}.tar.gz"
        _archive_tar_gz(bundle_dir, target)
    else:
        target = ARTIFACTS_DIR / f"{base_name}.zip"
        _archive_zip(bundle_dir, target)
    print(f"[build] Created artifact: {target}")
    return target


def main() -> None:
    os.chdir(ROOT)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-suffix", default=_default_artifact_suffix())
    parser.add_argument("--skip-smoke-test", action="store_true")
    args = parser.parse_args()

    _clean()
    _build_cython()
    _build_docs()
    _build_pyinstaller()

    bundle_dir = _bundle_dir()
    _expose_resources(bundle_dir)
    _copy_nuance_helper(bundle_dir)
    _copy_sapi32_helper(bundle_dir)
    _write_full_version(bundle_dir)
    _validate_bundle(bundle_dir)
    if not args.skip_smoke_test:
        _smoke_test(bundle_dir)
    _archive(bundle_dir, args.artifact_suffix)


if __name__ == "__main__":
    main()
