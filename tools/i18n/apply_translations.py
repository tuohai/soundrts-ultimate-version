#!/usr/bin/env python
"""Apply LLM- (or human-) authored translations to an i18n/tts-<lang>.po catalog.

Each translation batch is a plain Python file defining:
    TRANSLATIONS = {"<msgctxt>": "<translated text>", ...}

Using a .py dict literal (rather than JSON) avoids escaping headaches for
dialogue-heavy text -- use the target language's native quotation marks
(e.g. German „...", French «...») instead of ASCII " and there is nothing to
escape.

Usage:
    # sanity-check a batch against what dump_missing.py reported as missing,
    # without touching the .po file
    python tools/i18n/apply_translations.py --lang de --check /tmp/tang.json batch_tang.py

    # merge one or more batches into i18n/tts-de.po (never overwrites an
    # existing non-empty msgstr unless --force is given)
    python tools/i18n/apply_translations.py --lang de batch_tang.py batch_raynor.py
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from potts import DATA_DIR, parse_po, read_text, write_po  # noqa: E402


def load_translations(py_path: str) -> dict:
    path = Path(py_path)
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return dict(module.TRANSLATIONS)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", required=True, help="language code, e.g. fr")
    parser.add_argument("batches", nargs="+",
                         help="translation .py file(s), each defining TRANSLATIONS = {...}")
    parser.add_argument("--check", metavar="DUMP_JSON",
                         help="verify the batches exactly cover the msgctxt keys in this "
                              "dump_missing.py JSON file, then exit without writing anything")
    parser.add_argument("--force", action="store_true",
                         help="overwrite existing non-empty msgstr values instead of skipping them")
    args = parser.parse_args()

    all_translations: dict = {}
    for batch_path in args.batches:
        batch = load_translations(batch_path)
        overlap = set(batch) & set(all_translations)
        conflicting = {k for k in overlap if batch[k] != all_translations[k]}
        if conflicting:
            print(f"error: {batch_path} conflicts with an earlier batch on "
                  f"{len(conflicting)} key(s):", file=sys.stderr)
            for k in list(conflicting)[:10]:
                print(f"  {k}", file=sys.stderr)
            sys.exit(1)
        all_translations.update(batch)

    empty = [k for k, v in all_translations.items() if not v.strip()]
    if empty:
        print(f"error: {len(empty)} translation(s) are empty:", file=sys.stderr)
        for k in empty[:10]:
            print(f"  {k}", file=sys.stderr)
        sys.exit(1)

    if args.check:
        wanted = {item["msgctxt"] for item in json.loads(Path(args.check).read_text(encoding="utf-8"))}
        have = set(all_translations)
        missing = wanted - have
        extra = have - wanted
        print(f"want: {len(wanted)}  have: {len(have)}")
        if missing:
            print(f"MISSING {len(missing)} translation(s):")
            for k in list(missing)[:20]:
                print(f"  {k}")
        if extra:
            print(f"EXTRA {len(extra)} translation(s) not in the dump:")
            for k in list(extra)[:20]:
                print(f"  {k}")
        if not missing and not extra:
            print("OK: batches exactly cover the dump.")
        sys.exit(1 if (missing or extra) else 0)

    po_path = DATA_DIR / f"tts-{args.lang}.po"
    if not po_path.exists():
        print(f"no {po_path} found", file=sys.stderr)
        sys.exit(1)
    entries = parse_po(read_text(po_path))

    applied = skipped = 0
    unmatched = set(all_translations)
    for e in entries:
        if e.msgctxt not in all_translations:
            continue
        unmatched.discard(e.msgctxt)
        if e.msgstr and not args.force:
            skipped += 1
            continue
        e.msgstr = all_translations[e.msgctxt]
        applied += 1

    if unmatched:
        print(f"warning: {len(unmatched)} msgctxt key(s) not found in {po_path}:", file=sys.stderr)
        for k in list(unmatched)[:10]:
            print(f"  {k}", file=sys.stderr)

    po_path.write_text(write_po(entries), encoding="utf-8")
    print(f"applied {applied}, skipped {skipped} (already translated), "
          f"{len(unmatched)} not found in the catalog. wrote {po_path}")


if __name__ == "__main__":
    main()
