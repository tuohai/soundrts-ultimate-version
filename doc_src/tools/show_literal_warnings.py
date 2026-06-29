#!/usr/bin/env python3
import re
import subprocess
import sys
from collections import Counter
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
ctr = Counter()
samples = []
for line in r.stderr.splitlines():
    m = re.match(r"^(.+?):(\d+): \(WARNING/2\) (.+)$", line)
    if not m:
        continue
    path, num, msg = m.group(1), int(m.group(2)), m.group(3)
    ctr[path] += 1
    if len(samples) < 20 and "literal" in msg:
        p = ROOT / path
        text = p.read_text(encoding="utf-8").splitlines()[num - 1]
        samples.append((path, num, text))

print("Top files:")
for path, n in ctr.most_common(10):
    print(n, path)
print("\nSample literal lines:")
for path, num, text in samples:
    print(f"{path}:{num}: {text[:100]}")
