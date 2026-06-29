#!/usr/bin/env python3
"""Print sample files for each RST warning type."""
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
by_msg: dict[str, list[str]] = collections.defaultdict(list)
for line in r.stderr.splitlines():
    m = re.match(r"^(.+?):\d+: \(WARNING/2\) (.+)$", line)
    if m:
        by_msg[m.group(2)].append(m.group(1))
for msg, files in sorted(by_msg.items(), key=lambda x: -len(x[1])):
    print(f"\n=== {msg} ({len(files)}) ===")
    for f in files[:8]:
        print(" ", f)
