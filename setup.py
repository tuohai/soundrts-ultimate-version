#! .venv\Scripts\python.exe
"""
From the command-line, type: py setup.py build
Or activate the virtual environment and type: python setup.py build

Warning: the py launcher ignores the virtual environment if a "#!" line is specified!
(see PEP 486)

本脚本在 cx_Freeze 打包前会先用 setup_cython.py 编译所有 .pyx 模块，
产物 (.pyd / .so) 会作为 include_files 一并打入发布目录。
若 Cython 未安装或编译失败，会回退到纯 Python 模式（功能完整、速度较慢）。
可通过环境变量 SOUNDRTS_SKIP_CYTHON=1 显式跳过 Cython 构建。
"""

import os
import platform
import re
import shutil
import sys
from pathlib import Path
from subprocess import Popen, check_output

from cx_Freeze import Executable, setup

import setup_cython

# Read VERSION from source text — do NOT import soundrts.* before Cython build.
# Importing soundrts.version loads pygame + combat_fast.pyd into this process,
# which locks the .pyd on Windows and makes inplace rebuild fail with Access Denied.
_version_py = Path(__file__).resolve().parent / "soundrts" / "version.py"
_match = re.search(
    r'^VERSION\s*=\s*["\']([^"\']+)["\']',
    _version_py.read_text(encoding="utf-8"),
    re.MULTILINE,
)
if not _match:
    raise RuntimeError(f"Could not read VERSION from {_version_py}")
VERSION = _match.group(1)

if platform.system() == "Windows" and ".venv" not in sys.executable:
    print(f"WARNING: {sys.executable} (not a virtual environment?)")
    print("Activate first:  .\\.venv\\Scripts\\Activate.ps1")
    print("Or run:          .\\.venv\\Scripts\\python.exe setup.py build")
    input("[press Enter to continue; press Control+C to stop]")

try:
    full_version = check_output(["git", "describe", "--tags"]).strip().decode()
except FileNotFoundError:
    print("WARNING: couldn't get version from git.")
    full_version = f"{VERSION}-unknown"

skip_cython = os.environ.get("SOUNDRTS_SKIP_CYTHON", "").strip() not in ("", "0", "false", "False")
cython_outputs: list[str] = []
if skip_cython:
    print("[setup] SOUNDRTS_SKIP_CYTHON 已设置，跳过 Cython 预编译。")
else:
    try:
        print("[setup] 开始 Cython 预编译 ...")
        setup_cython.build(inplace=True, force=False)
        cython_outputs = setup_cython.find_compiled_outputs()
        print(f"[setup] Cython 预编译完成，产物 {len(cython_outputs)} 个。")
    except ImportError as e:
        print(f"[setup] WARNING: 跳过 Cython（未安装）：{e}")
    except Exception as e:
        print(f"[setup] WARNING: Cython 编译失败，回退纯 Python：{e}")

import builddoc  # after Cython: may import game modules

TMP = os.environ["TMP"]
destination = rf"{TMP}\soundrts-{VERSION}-windows"

# Campaigns live under res/single (not a top-level single/ directory).
include_files = ["res", "mods", "cfg", "doc"]
for compiled in cython_outputs:
    include_files.append((compiled, compiled))


def _add_tkinter_runtime(files: list) -> None:
    """Ship Tcl/Tk so ``soundrts.exe --soundrts-update`` can show a progress window."""
    root = Path(sys.base_prefix)
    tcl_root = root / "tcl"
    for name in ("tcl8.6", "tk8.6", "tcl8"):
        src = tcl_root / name
        if src.is_dir():
            files.append((str(src), name))
    dlls = root / "DLLs"
    for name in ("tcl86t.dll", "tk86t.dll", "_tkinter.pyd"):
        src = dlls / name
        if src.is_file():
            files.append((str(src), f"lib/{name}"))
    print(f"[setup] tkinter runtime files: {len([f for f in files if 'tcl' in str(f).lower() or 'tk' in str(f).lower()])}")


_add_tkinter_runtime(include_files)

build_exe_options = {
    "build_exe": destination,
    "optimize": 1,
    "silent": True,
    "packages": ["tkinter"],
    "excludes": ["Cython", "scipy", "numpy"],
    "include_files": include_files,
    "replace_paths": [("*", f"{full_version}:")],
}
executables = [
    Executable("soundrts.py", base="Win32GUI"),
    Executable("server.py", base=None),
]

builddoc.build()
if os.path.exists(destination):
    print(f"{destination} already exists. Deleting...")
    shutil.rmtree(destination)
setup(
    options={"build_exe": build_exe_options},
    executables=executables,
    name="SoundRTS",
    version=VERSION.replace("-dev", ".9999"),
)
print("Creating empty user folder...")
os.mkdir(rf"{destination}\user")
print(r"Resetting cfg\language.txt ...")
open(rf"{destination}\cfg\language.txt", "w").write("")
print("Adding full_version.txt ...")
with open(rf"{destination}\lib\full_version.txt", "w") as t:
    t.write(full_version)

# chardet 7.x / charset_normalizer ship mypyc .pyds that crash (0xc0000005) under
# cx_Freeze on Windows. Prefer pure-Python fallbacks for a launchable build.
def _strip_fragile_mypyc(dest: str) -> None:
    lib = Path(dest) / "lib"
    removed = 0
    for pattern in ("*__mypyc*.pyd", "chardet/pipeline/*.cp311*.pyd", "chardet/pipeline/*.pyd"):
        for pyd in lib.glob(pattern):
            try:
                pyd.unlink()
                removed += 1
            except OSError as e:
                print(f"[setup] WARNING: could not remove {pyd}: {e}")
    # Ensure chardet.pipeline has .py sources (cx_Freeze may only copy .pyd).
    try:
        import chardet

        src_pipe = Path(chardet.__file__).resolve().parent / "pipeline"
        dst_pipe = lib / "chardet" / "pipeline"
        if src_pipe.is_dir() and dst_pipe.is_dir():
            for py in src_pipe.glob("*.py"):
                target = dst_pipe / py.name
                if not target.exists():
                    shutil.copy2(py, target)
                    print(f"[setup] restored {target.relative_to(lib)}")
    except Exception as e:
        print(f"[setup] WARNING: could not restore chardet.pipeline .py: {e}")
    print(f"[setup] stripped {removed} fragile mypyc/native chardet modules.")


_strip_fragile_mypyc(destination)


def _copy_nuance_helper(dest: str) -> None:
    """Ship Java helper jars so packaged builds can use Apple / Nuance voices."""
    src = Path(__file__).resolve().parent / "tools" / "nuance_ve"
    jars = ("nuance_ve_helper.jar", "jna.jar")
    missing = [n for n in jars if not (src / n).is_file()]
    if missing:
        print(
            f"[setup] WARNING: skipping Nuance helper (missing {', '.join(missing)} "
            f"under {src})"
        )
        return
    out = Path(dest) / "tools" / "nuance_ve"
    out.mkdir(parents=True, exist_ok=True)
    for name in jars:
        shutil.copy2(src / name, out / name)
    readme = src / "README.md"
    if readme.is_file():
        shutil.copy2(readme, out / "README.md")
    print(f"[setup] Copied Nuance helper jars to {out}")


def _copy_nuance_voices(dest: str) -> None:
    """Ship local user/voices/nuance if present (required for Nuance TTS)."""
    src = Path(__file__).resolve().parent / "user" / "voices" / "nuance"
    if not src.is_dir():
        print(f"[setup] WARNING: no {src}; Nuance voice data not bundled.")
        return
    out = Path(dest) / "user" / "voices" / "nuance"
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(src, out)
    print(f"[setup] Copied Nuance voice data to {out}")


_copy_nuance_helper(destination)
_copy_nuance_voices(destination)
Popen(rf'explorer /select,"{destination}"')
