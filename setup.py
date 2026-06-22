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
import shutil
import sys
from subprocess import Popen, check_output

from cx_Freeze import Executable, setup

import builddoc
import setup_cython
from soundrts.version import VERSION

if platform.system() == "Windows" and ".venv" not in sys.executable:
    print(f"WARNING: {sys.executable} (not a virtual environment?)")
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

TMP = os.environ["TMP"]
destination = rf"{TMP}\soundrts-{VERSION}-windows"

include_files = ["res", "single", "mods", "cfg", "doc"]
for compiled in cython_outputs:
    include_files.append((compiled, compiled))

build_exe_options = {
    "build_exe": destination,
    "optimize": 1,
    "silent": True,
    "packages": [],
    "excludes": ["Cython", "scipy", "numpy", "tkinter"],
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
Popen(rf'explorer /select,"{destination}"')
print("Adding full_version.txt ...")
with open(rf"{destination}\lib\full_version.txt", "w") as t:
    t.write(full_version)
