#!/usr/bin/env python3
"""Migrate docs/zh and docs/en markdown into doc_src/src/{lang}/guides/."""
from pathlib import Path

from md2rst import migrate_tree

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    docs = ROOT / "docs"
    for lang in ("zh", "en"):
        src = docs / lang
        dst = ROOT / "doc_src" / "src" / lang / "guides"
        player = migrate_tree(src, dst, "player")
        mod = migrate_tree(src, dst, "mod")
        print(f"{lang}: {len(player)} player + {len(mod)} mod-author guides")


if __name__ == "__main__":
    main()
