#!/usr/bin/env python
"""Regenerate every ui-<lang>/tts.txt from the consolidated i18n/tts-<lang>.po.

Run this after pulling updated translations (e.g. from Crowdin) to produce
the tts.txt files the game actually loads at runtime -- the output format is
unchanged from what soundrts/lib/sound_cache.py already parses, so nothing
else needs to change; just commit the regenerated tts.txt files as usual.

Each po entry's "#:" reference lines say exactly which physical
<root>/ui/tts.txt:key it belongs to; this script fans a single po file back
out to every affected ui-<lang>/tts.txt across res/single/*, mods/**, etc.

Usage:
    python tools/i18n/build_tts.py [--lang xx]
"""
import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from potts import (  # noqa: E402
    DATA_DIR,
    REPO_ROOT,
    format_tts,
    lang_dir_for,
    parse_po,
    parse_reference,
    read_text,
)


def build_lang(po_path: Path, lang: str) -> None:
    entries = parse_po(read_text(po_path))
    by_lang_dir: "dict[Path, dict[str, str]]" = defaultdict(dict)
    for e in entries:
        if not e.msgstr:
            continue  # untranslated: falls back to the base-language text as today
        for ref in e.references:
            base_ui_dir, key = parse_reference(ref)
            by_lang_dir[lang_dir_for(base_ui_dir, lang)][key] = e.msgstr

    for lang_dir, translated in sorted(by_lang_dir.items()):
        lang_dir.mkdir(parents=True, exist_ok=True)
        tts_path = lang_dir / "tts.txt"
        tts_path.write_text(format_tts(translated), encoding="utf-8")
        print(f"wrote {tts_path.relative_to(REPO_ROOT)} ({len(translated)} strings)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", help="only rebuild this language code, e.g. fr")
    args = parser.parse_args()

    if not DATA_DIR.is_dir():
        print(f"no {DATA_DIR} directory -- run extract_pot.py first", file=sys.stderr)
        sys.exit(1)

    po_files = sorted(DATA_DIR.glob("tts-*.po"))
    if args.lang:
        po_files = [p for p in po_files if p.stem == f"tts-{args.lang}"]
        if not po_files:
            print(f"no i18n/tts-{args.lang}.po found", file=sys.stderr)
            sys.exit(1)

    for po_path in po_files:
        lang = po_path.stem[len("tts-"):]
        build_lang(po_path, lang)


if __name__ == "__main__":
    main()
