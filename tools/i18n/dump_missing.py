#!/usr/bin/env python
"""Dump missing (msgctxt, msgid) pairs for a language, grouped by source, so an
LLM (or a human translator) can work through them in batches that share
context -- e.g. one campaign or one mod at a time, so character names, place
names, and terminology stay consistent within a batch.

Usage:
    python tools/i18n/dump_missing.py --lang de --list-groups
    python tools/i18n/dump_missing.py --lang de --group "mod:tang" -o /tmp/tang.json
    python tools/i18n/dump_missing.py --lang de -o /tmp/all_missing.json
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from potts import DATA_DIR, parse_po, read_text  # noqa: E402


def source_group(entry) -> str:
    """Bucket an entry by the tree it came from: 'base', 'single:<campaign>',
    'mod:<name>', or the raw reference directory as a fallback."""
    if not entry.references:
        return "?"
    ref = entry.references[0]
    if ref.startswith("res/single/"):
        return "single:" + ref.split("/")[2]
    if ref.startswith("mods/"):
        return "mod:" + ref.split("/")[1]
    if ref.startswith("res/ui/"):
        return "base"
    return ref.rsplit("/", 1)[0]


def missing_entries(lang: str):
    pot_path = DATA_DIR / "tts.pot"
    po_path = DATA_DIR / f"tts-{lang}.po"
    if not pot_path.exists():
        print(f"no {pot_path} -- run extract_pot.py first", file=sys.stderr)
        sys.exit(1)
    if not po_path.exists():
        print(f"no {po_path} found", file=sys.stderr)
        sys.exit(1)
    pot_entries = parse_po(read_text(pot_path))
    translated = {(e.msgctxt, e.msgid) for e in parse_po(read_text(po_path)) if e.msgstr}
    return [e for e in pot_entries if (e.msgctxt, e.msgid) not in translated]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", required=True, help="language code, e.g. fr")
    parser.add_argument("--group", help="only dump this source group (see --list-groups for names)")
    parser.add_argument("--list-groups", action="store_true",
                         help="print missing-entry counts per source group and exit")
    parser.add_argument("-o", "--output", help="write JSON here instead of stdout")
    args = parser.parse_args()

    missing = missing_entries(args.lang)

    if args.list_groups:
        counts = Counter(source_group(e) for e in missing)
        for group, count in sorted(counts.items(), key=lambda kv: -kv[1]):
            print(f"{count}\t{group}")
        return

    if args.group:
        missing = [e for e in missing if source_group(e) == args.group]

    data = [{"msgctxt": e.msgctxt, "msgid": e.msgid} for e in missing]
    text = json.dumps(data, ensure_ascii=False, indent=1)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"wrote {len(data)} entries to {args.output}")
    else:
        print(text)


if __name__ == "__main__":
    main()
