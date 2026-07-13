# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for SoundRTS client and server bundles."""

from glob import glob
import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

RESOURCE_DIRS = ("cfg", "res", "mods", "doc")
datas = [(name, name) for name in RESOURCE_DIRS if os.path.isdir(name)]

binaries = []
for pattern in ("**/*.pyd", "**/*.so", "**/*.dylib"):
    for path in sorted(glob(f"soundrts/{pattern}", recursive=True)):
        if f"{os.sep}老版本{os.sep}" in path:
            continue
        binaries.append((path, str(Path(path).parent)))

hiddenimports = collect_submodules("soundrts") + [
    "accessible_output2",
    "pygame",
    "cloudpickle",
    "websockets",
    "cryptography",
    "chardet",
    "upnpclient",
    "tomli",
    "docutils",
    "Pygments",
]

analysis_kwargs = dict(
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=["pyinstaller_runtime_hook.py"],
    excludes=["Cython", "scipy", "numpy", "tkinter", "pytest", "cx_Freeze"],
    noarchive=False,
    optimize=1,
)

client_a = Analysis(["soundrts.py"], **analysis_kwargs)
server_a = Analysis(["server.py"], **analysis_kwargs)

MERGE(
    (client_a, "soundrts", "SoundRTS/SoundRTS"),
    (server_a, "server", "SoundRTS/SoundRTS-server"),
)

client_pyz = PYZ(client_a.pure, client_a.zipped_data, cipher=block_cipher)
client_exe = EXE(
    client_pyz,
    client_a.scripts,
    [],
    exclude_binaries=True,
    name="SoundRTS",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    contents_directory=".",
)

server_pyz = PYZ(server_a.pure, server_a.zipped_data, cipher=block_cipher)
server_exe = EXE(
    server_pyz,
    server_a.scripts,
    [],
    exclude_binaries=True,
    name="SoundRTS-server",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    contents_directory=".",
)

coll = COLLECT(
    client_exe,
    server_exe,
    client_a.binaries,
    client_a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="SoundRTS",
)
