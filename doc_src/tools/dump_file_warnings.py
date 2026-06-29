#!/usr/bin/env python3
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
target = sys.argv[1] if len(sys.argv) > 1 else "unit-default-behavior.rst"
r = subprocess.run(
    [sys.executable, "-c", "import builddoc; builddoc._SETTINGS['report_level']=2; builddoc.build()"],
    cwd=ROOT,
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
)
for line in r.stderr.splitlines():
    if target not in line:
        continue
    m = re.match(r"^(.+?):(\d+): \(WARNING/2\) (.+)$", line)
    if not m:
        continue
    n = int(m.group(2))
    t = (ROOT / m.group(1)).read_text(encoding="utf-8").splitlines()[n - 1]
    print(n, m.group(3))
    print(" ", t[:140])

