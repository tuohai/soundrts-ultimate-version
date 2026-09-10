#! .venv\Scripts\python.exe
"""SoundRTS Cython build entry.

Usage:
    python setup_cython.py build_ext --inplace

Discovers soundrts/**/*.pyx automatically (skips archived 老版本 folders).
"""

from __future__ import annotations

import os
import platform
import sys
from glob import glob


def _openmp_flags() -> tuple[list[str], list[str]]:
    """Return (extra_compile_args, extra_link_args) for OpenMP."""
    if os.environ.get("SOUNDRTS_NO_OPENMP", "").strip() in ("1", "true", "True"):
        return [], []
    if platform.system() == "Windows":
        return ["/openmp"], []
    return ["-fopenmp"], ["-fopenmp"]


def _find_pyx_files(root: str = "soundrts") -> list[str]:
    """Find all .pyx files, sorted for reproducible builds."""
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
    """Compile all .pyx files. Returns list of .pyx paths compiled."""
    try:
        from Cython.Build import cythonize
        from setuptools import setup
    except ImportError as e:
        raise ImportError(
            "Cython build requires 'Cython' and 'setuptools'. "
            "Install: pip install -r requirements-build.txt"
        ) from e

    pyx_files = _find_pyx_files()
    if not pyx_files:
        print("[setup_cython] No .pyx files found, skip.")
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

        ext_modules = cythonize(
            pyx_files,
            compiler_directives=_cython_directives(),
            force=force,
            annotate=False,
        )

        omp_cflags, omp_ldflags = _openmp_flags()
        if omp_cflags:
            for ext in ext_modules:
                ext.extra_compile_args = list(ext.extra_compile_args or []) + omp_cflags
                ext.extra_link_args = list(ext.extra_link_args or []) + omp_ldflags
            print(
                f"[setup_cython] OpenMP on: cflags={omp_cflags} ldflags={omp_ldflags}"
            )
        else:
            print("[setup_cython] OpenMP off (SOUNDRTS_NO_OPENMP=1)")

        setup(name="soundrts-cython", ext_modules=ext_modules)
    finally:
        sys.argv = saved_argv

    return pyx_files


def find_compiled_outputs(root: str = "soundrts") -> list[str]:
    """Return compiled .pyd / .so paths for cx_Freeze include_files."""
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
        print(f"[setup_cython] error: {e}", file=sys.stderr)
        sys.exit(1)

    if pyx_files:
        outputs = find_compiled_outputs()
        print(f"\n[setup_cython] done. {len(outputs)} outputs:")
        for o in outputs:
            print(f"  - {o}")


if __name__ == "__main__":
    main()
