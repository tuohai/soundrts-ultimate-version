#! .venv\Scripts\python.exe
"""SoundRTS Cython extension build entry point.

Usage:
    # Developer machines: build .pyd / .so files in place next to .py files.
    python setup_cython.py build_ext --inplace

    # Generate C sources only for Cython debugging.
    python setup_cython.py build_ext --inplace --build-cython-only

Design notes:
1. Automatically discover ``soundrts/**/*.pyx`` files, excluding archived
   ``soundrts/old versions/`` content. New .pyx files need no script changes.
2. If Cython is missing or compilation fails, the caller decides whether to
   fall back to .py modules.
3. Keep this script independent from cx_Freeze.
4. Optimize for game-loop hot paths by disabling selected runtime checks.
"""

from __future__ import annotations

import os
import platform
import sys
from glob import glob


def _openmp_flags() -> tuple[list[str], list[str]]:
    """Return (extra_compile_args, extra_link_args) for enabling OpenMP.

    Windows + MSVC: ``/openmp``; no extra linker argument is needed.
    Linux/macOS + GCC/Clang: ``-fopenmp`` for both compile and link.
    macOS Apple Clang does not provide OpenMP by default. The CI workflow
    installs Homebrew GCC and sets CC/CXX accordingly.

    Set ``SOUNDRTS_NO_OPENMP=1`` to disable OpenMP for unsupported toolchains.
    """
    if os.environ.get("SOUNDRTS_NO_OPENMP", "").strip() in ("1", "true", "True"):
        return [], []
    if platform.system() == "Windows":
        return ["/openmp"], []
    return ["-fopenmp"], ["-fopenmp"]


def _find_pyx_files(root: str = "soundrts") -> list[str]:
    """Discover all .pyx files recursively in deterministic order."""
    pattern = os.path.join(root, "**", "*.pyx")
    files = sorted(glob(pattern, recursive=True))
    return [p for p in files if f"{os.sep}老版本{os.sep}" not in p]


def _cython_directives() -> dict:
    """Global Cython compiler directives."""
    return {
        "language_level": 3,
        "boundscheck": False,
        "wraparound": False,
        "cdivision": True,
        "initializedcheck": False,
        "infer_types": True,
        "embedsignature": True,
    }


def build(inplace: bool = True, force: bool = False) -> list[str]:
    """Compile all .pyx files and return their paths.

    Raises ImportError if Cython is missing; the caller decides whether that is
    fatal.
    """
    try:
        from Cython.Build import cythonize
        from setuptools import setup
    except ImportError as e:
        raise ImportError(
            "Cython compilation requires 'Cython' and 'setuptools'. "
            "Run: pip install -r requirements-build.txt"
        ) from e

    pyx_files = _find_pyx_files()
    if not pyx_files:
        print("[setup_cython] No .pyx files found; skipping compilation.")
        return []

    print(f"[setup_cython] Compiling {len(pyx_files)} .pyx modules:")
    for p in pyx_files:
        print(f"  - {p}")

    saved_argv = sys.argv[:]
    try:
        argv = ["setup_cython.py", "build_ext"]
        if inplace:
            argv.append("--inplace")
        if force:
            argv.append("--force")
        sys.argv = argv

        cython_build_dir = os.environ.get("SOUNDRTS_CYTHON_BUILD_DIR") or None
        ext_modules = cythonize(
            pyx_files,
            compiler_directives=_cython_directives(),
            force=force,
            annotate=False,
            build_dir=cython_build_dir,
        )

        omp_cflags, omp_ldflags = _openmp_flags()
        if omp_cflags:
            for ext in ext_modules:
                ext.extra_compile_args = list(ext.extra_compile_args or []) + omp_cflags
                ext.extra_link_args = list(ext.extra_link_args or []) + omp_ldflags
            print(f"[setup_cython] OpenMP enabled: cflags={omp_cflags} ldflags={omp_ldflags}")
        else:
            print("[setup_cython] OpenMP disabled (SOUNDRTS_NO_OPENMP=1)")

        setup(name="soundrts-cython", ext_modules=ext_modules)
    finally:
        sys.argv = saved_argv

    return pyx_files


def find_compiled_outputs(root: str = "soundrts") -> list[str]:
    """Return compiled output paths (.pyd / .so) for packagers."""
    out: list[str] = []
    for ext in ("*.pyd", "*.so"):
        for path in sorted(glob(os.path.join(root, "**", ext), recursive=True)):
            if f"{os.sep}老版本{os.sep}" not in path:
                out.append(path)
    return out


def main():
    inplace = "--inplace" in sys.argv or "-i" in sys.argv
    force = "--force" in sys.argv or "-f" in sys.argv
    if not inplace and "build_ext" not in sys.argv:
        sys.argv.append("build_ext")
        sys.argv.append("--inplace")
        inplace = True

    try:
        pyx_files = build(inplace=inplace, force=force)
    except ImportError as e:
        print(f"[setup_cython] Error: {e}", file=sys.stderr)
        sys.exit(1)

    if pyx_files:
        outputs = find_compiled_outputs()
        print(f"\n[setup_cython] Compilation finished. Outputs: {len(outputs)}")
        for o in outputs:
            print(f"  - {o}")


if __name__ == "__main__":
    main()
