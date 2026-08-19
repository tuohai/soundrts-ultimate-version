"""Standalone update UI (separate process, no game window).

Started as::

    soundrts.exe --soundrts-update <job.json>

The game writes the job, launches this process, then exits. This window waits
for the game PID, downloads/extracts with a visible progress bar, then hands
off to a short apply.bat so the install folder (including this exe) can be
overwritten safely.
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path


def _ensure_tcl_env() -> None:
    """Point Tcl/Tk at files shipped next to a frozen exe."""
    if not getattr(sys, "frozen", False):
        return
    base = Path(sys.executable).resolve().parent
    candidates = (
        (base / "tcl8.6", base / "tk8.6"),
        (base / "lib" / "tcl8.6", base / "lib" / "tk8.6"),
        (base / "tcl" / "tcl8.6", base / "tcl" / "tk8.6"),
    )
    for tcl, tk in candidates:
        if tcl.is_dir():
            os.environ.setdefault("TCL_LIBRARY", str(tcl))
        if tk.is_dir():
            os.environ.setdefault("TK_LIBRARY", str(tk))


_ensure_tcl_env()

try:
    import tkinter as tk
    from tkinter import ttk
except ImportError:  # packaged builds used to exclude tkinter
    tk = None
    ttk = None


def _log(tmp_dir: Path | str | None, message: str) -> None:
    try:
        base = Path(tmp_dir) if tmp_dir else Path(".")
        base.mkdir(parents=True, exist_ok=True)
        path = base / "soundrts_update_ui.log"
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%H:%M:%S')} {message}\n")
    except Exception:
        pass


def _load_job(path: str | Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    required = (
        "version",
        "download_url",
        "target_dir",
        "exe_name",
        "wait_pid",
        "tmp_dir",
    )
    for key in required:
        if key not in data:
            raise ValueError(f"update job missing {key}")
    return data


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform != "win32":
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    try:
        out = subprocess.check_output(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            text=True,
            errors="ignore",
        )
        line = (out or "").strip()
        if not line or line.lower().startswith("info:") or "没有" in line:
            return False
        # CSV: "name","pid","session","..."
        parts = [p.strip().strip('"') for p in line.split(",")]
        return len(parts) >= 2 and parts[1] == str(pid)
    except Exception:
        return False


def _wait_for_pid(pid: int, status_cb, poll: float = 0.4) -> None:
    status_cb("Waiting for the game to exit… / 正在等待游戏退出…")
    waited = 0.0
    while _pid_alive(pid):
        time.sleep(poll)
        waited += poll
        if int(waited) % 3 == 0:
            status_cb(
                f"Waiting for the game to exit… ({int(waited)}s) / "
                f"正在等待游戏退出…（{int(waited)}秒）"
            )


def run_update_job(job: dict, status_cb, progress_cb) -> None:
    """Download, extract, write apply script. Raises on failure."""
    tmp_dir = Path(job["tmp_dir"])
    wait_pid = int(job["wait_pid"])
    version = str(job["version"])

    status_cb("Waiting for the game to exit… / 正在等待游戏退出…")
    _wait_for_pid(wait_pid, status_cb)
    _log(tmp_dir, f"game pid {wait_pid} exited")

    # Stdlib-only module — do NOT import auto_update (pulls config/resource and hangs).
    status_cb("Preparing download… / 正在准备下载…")
    from . import update_core
    from .update_core import ReleaseInfo

    _log(tmp_dir, "update_core imported")

    tmp_dir.mkdir(parents=True, exist_ok=True)
    stamp = version.replace(".", "_")
    zip_path = tmp_dir / f"soundrts_update_{stamp}.zip"
    extract_dir = tmp_dir / f"soundrts_update_{stamp}_extract"
    target_dir = Path(job["target_dir"])
    exe_name = str(job["exe_name"])

    info = ReleaseInfo(
        version=version,
        tag_name=str(job.get("tag_name") or version),
        html_url=str(job.get("html_url") or ""),
        body="",
        asset_name=str(job.get("asset_name") or ""),
        download_url=str(job["download_url"]),
        size=int(job.get("size") or 0),
        digest=str(job.get("digest") or ""),
    )

    status_cb(f"Downloading {version}… / 正在下载 {version}…")
    progress_cb(0)
    _log(tmp_dir, f"download start {info.download_url}")

    def _on_progress(pct, done, total):
        progress_cb(pct)
        if total:
            status_cb(f"Downloading… {pct}% / 正在下载… {pct}%")
        else:
            mb = done / (1024 * 1024)
            status_cb(f"Downloading… {mb:.1f} MB / 正在下载… {mb:.1f} MB")

    update_core.download_release(info, zip_path, progress_callback=_on_progress)
    progress_cb(100)
    _log(tmp_dir, "download done")

    status_cb("Extracting… / 正在解压…")
    staging_root = update_core.extract_zip(zip_path, extract_dir)
    _log(tmp_dir, f"extracted to {staging_root}")

    status_cb("Preparing install… / 正在准备安装…")
    cleanup_paths = [zip_path, extract_dir]
    job_file = job.get("job_path")
    if job_file:
        cleanup_paths.append(Path(job_file))
    script = update_core.write_apply_script(
        staging_root=staging_root,
        target_dir=target_dir,
        exe_name=exe_name,
        pid=os.getpid(),
        cleanup_paths=cleanup_paths,
        tmp_dir=tmp_dir,
    )
    update_core.launch_apply_and_exit(script)
    status_cb("Installing and restarting… / 正在安装并重启…")
    _log(tmp_dir, f"apply script launched {script}")
    # Apply.bat waits for this PID; exit hard so robocopy is not blocked by Tk.
    time.sleep(0.25)
    os._exit(0)


def _win_message(title: str, text: str, *, error: bool = False) -> None:
    if sys.platform != "win32":
        print(f"{title}: {text}", file=sys.stderr if error else sys.stdout)
        return
    try:
        import ctypes

        flags = 0x00000010 if error else 0x00000040
        ctypes.windll.user32.MessageBoxW(None, str(text), str(title), flags)
    except Exception:
        pass


def run_update_headless(job_path: str) -> int:
    """Apply the update with no Tk window (log + MessageBox on failure)."""
    tmp_hint = None

    def status_cb(text: str) -> None:
        _log(tmp_hint, text)

    def progress_cb(pct: int) -> None:
        _log(tmp_hint, f"progress {pct}")

    try:
        job = _load_job(job_path)
        job["job_path"] = str(Path(job_path).resolve())
        tmp_hint = job.get("tmp_dir")
        _log(tmp_hint, f"headless updater job={job_path}")
        run_update_job(job, status_cb, progress_cb)
        return 0
    except Exception as e:
        _log(tmp_hint, "ERROR " + traceback.format_exc())
        _win_message("SoundRTS Update", f"Update failed / 更新失败:\n{e}", error=True)
        return 1


def run_update_ui(job_path: str) -> int:
    """Show progress window and run the update job. Returns process exit code."""
    if tk is None or ttk is None:
        return run_update_headless(job_path)

    root = tk.Tk()
    root.title("SoundRTS Update")
    root.geometry("420x160")
    root.resizable(False, False)
    root.attributes("-topmost", True)

    status_var = tk.StringVar(value="Starting… / 正在启动…")
    progress_var = tk.DoubleVar(value=0.0)
    ui_q: queue.Queue = queue.Queue()

    frm = ttk.Frame(root, padding=12)
    frm.pack(fill=tk.BOTH, expand=True)
    ttk.Label(frm, textvariable=status_var, wraplength=390).pack(anchor=tk.W)
    ttk.Progressbar(frm, maximum=100, variable=progress_var, length=390).pack(pady=12)
    err_box_holder: dict = {"btn": None}
    result: dict = {"ok": False, "error": "", "done": False}

    def status_cb(text: str) -> None:
        ui_q.put(("status", text))

    def progress_cb(pct: int) -> None:
        ui_q.put(("progress", float(pct)))

    def _poll_ui() -> None:
        try:
            while True:
                kind, payload = ui_q.get_nowait()
                if kind == "status":
                    status_var.set(str(payload))
                elif kind == "progress":
                    progress_var.set(float(payload))
                elif kind == "error_button":
                    if err_box_holder["btn"] is None:
                        err_box_holder["btn"] = ttk.Button(
                            frm, text="Close / 关闭", command=root.destroy
                        )
                        err_box_holder["btn"].pack()
                elif kind == "destroy":
                    root.destroy()
                    return
        except queue.Empty:
            pass
        if not result["done"]:
            root.after(100, _poll_ui)

    def worker() -> None:
        tmp_hint = None
        try:
            status_cb("Reading update job… / 正在读取更新任务…")
            job = _load_job(job_path)
            job["job_path"] = str(Path(job_path).resolve())
            tmp_hint = job.get("tmp_dir")
            _log(tmp_hint, f"ui started job={job_path}")
            run_update_job(job, status_cb, progress_cb)
            result["ok"] = True
            result["done"] = True
            ui_q.put(("destroy", None))
        except Exception as e:
            result["error"] = str(e)
            result["done"] = True
            _log(tmp_hint, "ERROR " + traceback.format_exc())
            status_cb(f"Update failed / 更新失败: {e}")
            ui_q.put(("error_button", None))

    threading.Thread(target=worker, daemon=True).start()
    root.after(100, _poll_ui)
    root.mainloop()
    return 0 if result["ok"] else 1


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--soundrts-update" in args:
        i = args.index("--soundrts-update")
        args = args[i + 1 :]
    if not args:
        print("usage: --soundrts-update <job.json>", file=sys.stderr)
        return 2
    return run_update_ui(args[0])


if __name__ == "__main__":
    raise SystemExit(main())
