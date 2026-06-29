#!/usr/bin/env python3
import collections
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
lines = [l for l in r.stderr.splitlines() if "WARNING/2" in l]
ctr = collections.Counter()
for line in lines:
    m = re.search(r"\(WARNING/2\) (.+)$", line)
    if m:
        ctr[m.group(1)] += 1
for msg, n in ctr.most_common(15):
    print(f"{n:4d}  {msg}")
print(f"total warnings: {len(lines)}")
