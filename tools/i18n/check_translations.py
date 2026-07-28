#!/usr/bin/env python
"""Report missing/stale translations across the consolidated i18n/tts-<lang>.po
files, relative to i18n/tts.pot.

Usage:
    python tools/i18n/check_translations.py [--strict] [--lang xx]

--strict makes the script exit with status 1 if anything is missing or
stale, so it can be used as a CI gate.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from potts import DATA_DIR, REPO_ROOT, parse_po, read_text  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--lang", help="only check this language code, e.g. fr")
    args = parser.parse_args()

    pot_path = DATA_DIR / "tts.pot"
    if not pot_path.exists():
        print(f"no {pot_path} -- run extract_pot.py first", file=sys.stderr)
        return 1

    pot_entries = parse_po(read_text(pot_path))
    pot_keys = {(e.msgctxt, e.msgid) for e in pot_entries}
    total = len(pot_keys)

    po_files = sorted(DATA_DIR.glob("tts-*.po"))
    if args.lang:
        po_files = [p for p in po_files if p.stem == f"tts-{args.lang}"]
        if not po_files:
            print(f"no {DATA_DIR}/tts-{args.lang}.po found", file=sys.stderr)
            return 1

    problems = 0
    for po_path in po_files:
        lang = po_path.stem[len("tts-"):]
        entries = parse_po(read_text(po_path))
        po_keys = {(e.msgctxt, e.msgid) for e in entries}
        translated_keys = {(e.msgctxt, e.msgid) for e in entries if e.msgstr}

        missing = pot_keys - translated_keys
        stale = po_keys - pot_keys
        pct = 100 * len(translated_keys) / total if total else 100

        print(f"[{lang}] {len(translated_keys)}/{total} ({pct:.0f}%)"
              f"{f', {len(missing)} missing' if missing else ''}"
              f"{f', {len(stale)} stale' if stale else ''}")
        if missing or stale:
            problems += 1

    if args.strict and problems:
        print(f"\n{problems} language(s) with missing or stale translations", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
