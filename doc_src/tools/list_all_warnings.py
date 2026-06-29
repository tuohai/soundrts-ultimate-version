#!/usr/bin/env python3
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
r = subprocess.run(
    [sys.executable, "-c", "import builddoc; builddoc._SETTINGS['report_level']=2; builddoc.build()"],
    cwd=ROOT,
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
)
for line in r.stderr.splitlines():
    if "WARNING/2" not in line:
        continue
    m = re.match(r"^(.+?):(\d+): \(WARNING/2\) (.+)$", line)
    if not m:
        print(line)
        continue
    path, num, msg = m.group(1), int(m.group(2)), m.group(3)
    text = (ROOT / path).read_text(encoding="utf-8").splitlines()[num - 1]
    print(f"{path}:{num}: {msg}")
    print(f"  {text[:120]}")
