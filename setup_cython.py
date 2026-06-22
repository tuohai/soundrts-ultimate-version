#! .venv\Scripts\python.exe
"""SoundRTS Cython 模块编译入口

用法：
    # 开发者本机：原地编译 .pyd / .so（与 .py 同目录），便于运行
    python setup_cython.py build_ext --inplace

    # 仅生成 C 源码（不编译），用于调试 Cython 代码
    python setup_cython.py build_ext --inplace --build-cython-only

设计原则：
1. 全自动发现 ``soundrts/**/*.pyx``（排除 ``soundrts/老版本/`` 归档），新增 .pyx 无需改本脚本。
2. 失败时退化：如果 Cython 未安装或编译失败，调用方应负责走 .py fallback。
3. 与 cx_Freeze 解耦：setup.py 调用本脚本前置编译，本脚本不依赖 cx_Freeze。
4. 编译选项以"游戏循环热点"为目标，关掉 boundscheck/wraparound 等运行时检查。
"""

from __future__ import annotations

import os
import platform
import sys
from glob import glob


def _openmp_flags() -> tuple[list[str], list[str]]:
    """返回 (extra_compile_args, extra_link_args)，用于启用 OpenMP。

    Windows + MSVC：``/openmp``，链接器不需要额外参数。
    Linux/macOS + GCC/Clang：``-fopenmp`` 同时给 compile 和 link。
    macOS 的 Apple Clang 默认不带 OpenMP，需要 ``brew install libomp`` 并改
    ``-Xpreprocessor -fopenmp -lomp``；这里先按通用 GCC 写，macOS 编译失败
    时调用方应自行调整。

    可通过环境变量 ``SOUNDRTS_NO_OPENMP=1`` 关掉 OpenMP（用于不支持 OpenMP
    的工具链，例如 macOS Apple Clang 默认状态）。
    """
    if os.environ.get("SOUNDRTS_NO_OPENMP", "").strip() in ("1", "true", "True"):
        return [], []
    if platform.system() == "Windows":
        return ["/openmp"], []
    return ["-fopenmp"], ["-fopenmp"]


def _find_pyx_files(root: str = "soundrts") -> list[str]:
    """递归发现所有 .pyx 文件，按字典序排序以保证可重复构建。"""
    pattern = os.path.join(root, "**", "*.pyx")
    files = sorted(glob(pattern, recursive=True))
    return [p for p in files if f"{os.sep}老版本{os.sep}" not in p]


def _cython_directives() -> dict:
    """全局 Cython 编译指令。"""
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
    """编译所有 .pyx 文件。返回成功编译的 .pyx 路径列表。

    若 Cython 未安装，抛出 ImportError，调用方决定是否致命。
    """
    try:
        from Cython.Build import cythonize
        from setuptools import setup
    except ImportError as e:
        raise ImportError(
            "Cython 编译需要 'Cython' 和 'setuptools'。"
            "请先运行: pip install -r requirements-build.txt"
        ) from e

    pyx_files = _find_pyx_files()
    if not pyx_files:
        print("[setup_cython] 未发现任何 .pyx 文件，跳过编译。")
        return []

    print(f"[setup_cython] 将编译 {len(pyx_files)} 个 .pyx 模块：")
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
            print(f"[setup_cython] OpenMP 已启用：cflags={omp_cflags} ldflags={omp_ldflags}")
        else:
            print("[setup_cython] OpenMP 已禁用（SOUNDRTS_NO_OPENMP=1）")

        setup(name="soundrts-cython", ext_modules=ext_modules)
    finally:
        sys.argv = saved_argv

    return pyx_files


def find_compiled_outputs(root: str = "soundrts") -> list[str]:
    """返回所有编译产物路径（.pyd / .so），供 cx_Freeze include_files 使用。"""
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
        print(f"[setup_cython] 错误: {e}", file=sys.stderr)
        sys.exit(1)

    if pyx_files:
        outputs = find_compiled_outputs()
        print(f"\n[setup_cython] 编译完成。产物 {len(outputs)} 个：")
        for o in outputs:
            print(f"  - {o}")


if __name__ == "__main__":
    main()
