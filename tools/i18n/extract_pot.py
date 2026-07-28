#!/usr/bin/env python
"""Generate a single, consolidated tts.pot/tts-<lang>.po pair per language
from every tts.txt found in the repo (res/ui, res/single/*, mods/**).

Design goal: a translator opens exactly ONE file per language (i18n/tts-
<lang>.po), like NVDA's or LibreSVIP's single per-language catalog -- not a
dozen scattered tts.txt/po files across res/single/* and mods/**. Each
catalog entry's msgid is the actual source string from its own tree (not a
bare number); "#:" reference comments say exactly which tts.txt:key it came
from.

Every tree (res/ui, each res/single/<campaign>, each mods/<name>/**) gets
its own namespace -- entries are never merged across trees, even when two
trees happen to reuse the same numeric key. Two independent mods can (and
do) use the same key for unrelated content; merging them by key+text alone
previously caused one tree's translation to silently overwrite another's.
Base-game (res/ui) entries keep a plain numeric msgctxt; every other tree's
msgctxt is suffixed with its path so it's visually obvious which is which.

This script is read-only with respect to tts.txt: it only ever writes the
generated files under i18n/. Runtime behaviour, the tts.txt format, sound
files and mod/campaign compatibility are all untouched. Run build_tts.py to
turn edited .po files back into tts.txt.

Usage:
    python tools/i18n/extract_pot.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from potts import (  # noqa: E402
    DATA_DIR,
    REPO_ROOT,
    TTS_FILENAME,
    PoEntry,
    find_ui_dirs,
    group_by_base,
    load_msgparts_context,
    make_reference,
    parse_tts,
    read_text,
    write_po,
)

BASE_TREE_LABEL = "res/ui"  # only this tree's keys get msgparts.py context comments,
                            # and keep a plain (unsuffixed) msgctxt


class MergedEntry:
    __slots__ = ("msgid", "comments", "references", "translations")

    def __init__(self, msgid: str):
        self.msgid = msgid
        self.comments: list = []
        self.references: list = []
        self.translations: dict = {}  # lang -> msgstr


def collect() -> "dict[tuple, MergedEntry]":
    """Walk every ui/ui-<lang> tts.txt pair in the repo, keyed by
    (group_label, key) where group_label is the owning tree's relative
    "ui" path (e.g. "res/ui", "mods/tang/ui") -- so entries are always
    scoped to the tree they came from and never accidentally merge with an
    unrelated tree's entry for the same numeric key.

    A translation file occasionally defines a key that its own tree's base
    ui/tts.txt does not have (e.g. a campaign overriding just the French
    wording of a base-game phrase, without touching its own English text).
    These "orphan" keys are still kept in the catalog -- using the wider
    repo's base text for that key as msgid where available -- so
    round-tripping through build_tts.py never silently drops them.
    """
    context = load_msgparts_context()
    groups = group_by_base(find_ui_dirs(REPO_ROOT))

    base_by_group = {}
    global_base_texts: "dict[str, str]" = {}
    for base_dir, langs in groups.items():
        if "" not in langs:
            continue  # no base/source-language tree here, nothing to extract
        base_path = langs[""] / TTS_FILENAME
        if not base_path.exists():
            continue
        base_entries = parse_tts(read_text(base_path))
        if not base_entries:
            continue
        base_by_group[base_dir] = (langs, base_entries)
        for key, text in base_entries.items():
            global_base_texts.setdefault(key, text)

    merged: "dict[tuple, MergedEntry]" = {}

    for base_dir, (langs, base_entries) in sorted(base_by_group.items()):
        base_ui_dir = langs[""]
        group_label = base_ui_dir.relative_to(REPO_ROOT).as_posix()
        is_core = group_label == BASE_TREE_LABEL

        for key, source_text in base_entries.items():
            entry = merged.setdefault((group_label, key), MergedEntry(source_text))
            entry.references.append(make_reference(base_ui_dir, key))
            if is_core:
                for label in context.get(key, []):
                    if label not in entry.comments:
                        entry.comments.append(label)

        for lang, ui_dir in langs.items():
            if lang == "":
                continue
            lang_path = ui_dir / TTS_FILENAME
            if not lang_path.exists():
                continue
            lang_entries = parse_tts(read_text(lang_path))
            for key, translation in lang_entries.items():
                if not translation:
                    continue
                if key in base_entries:
                    merged[(group_label, key)].translations[lang] = translation
                else:
                    # orphan: only this language layer defines the key.
                    fallback_msgid = global_base_texts.get(key, translation)
                    entry = merged.setdefault((group_label, key), MergedEntry(fallback_msgid))
                    if not entry.references:
                        entry.references.append(make_reference(base_ui_dir, key))
                        entry.comments.append(
                            f"only defined in a translation layer under {group_label}, "
                            "no matching key in that tree's own ui/tts.txt"
                        )
                    entry.translations[lang] = translation

    # stable order, grouped by where the entry came from
    return dict(sorted(merged.items(), key=lambda kv: kv[1].references[0]))


def po_key(group_label: str, key: str) -> str:
    return key if group_label == BASE_TREE_LABEL else f"{key}@{group_label}"


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    merged = collect()

    all_langs = sorted({lang for e in merged.values() for lang in e.translations})

    pot_entries = [
        PoEntry(msgctxt=po_key(group, key), msgid=e.msgid, comments=e.comments, references=e.references)
        for (group, key), e in merged.items()
    ]
    pot_path = DATA_DIR / "tts.pot"
    pot_path.write_text(write_po(pot_entries), encoding="utf-8")
    print(f"wrote {pot_path.relative_to(REPO_ROOT)} ({len(pot_entries)} strings)")

    for lang in all_langs:
        po_entries = [
            PoEntry(
                msgctxt=po_key(group, key),
                msgid=e.msgid,
                msgstr=e.translations.get(lang, ""),
                comments=e.comments,
                references=e.references,
            )
            for (group, key), e in merged.items()
        ]
        translated = sum(1 for pe in po_entries if pe.msgstr)
        po_path = DATA_DIR / f"tts-{lang}.po"
        po_path.write_text(write_po(po_entries), encoding="utf-8")
        print(f"wrote {po_path.relative_to(REPO_ROOT)} ({translated}/{len(po_entries)} translated)")


if __name__ == "__main__":
    main()
