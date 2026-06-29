#!/usr/bin/env python3
"""Fix internal doc links after player/mod restructure."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "doc_src" / "src"

REPL = [
    ("player-guide.htm", "player/index.htm"),
    ("mod-author-guide.htm", "mod/index.htm"),
    ("guides/player/", "player/"),
    ("guides/mod/", "mod/"),
    ("../player/入门指南.htm", "../player/getting-started.htm"),
    ("../mod/入门指南.htm", "../mod/getting-started.htm"),
    ("`manual.htm`", "`player/manual.htm`"),
    ("<manual.htm>", "<player/manual.htm>"),
    ("`modding.htm`", "`mod/modding.htm`"),
    ("<modding.htm>", "<mod/modding.htm>"),
    ("`mapmaking.htm`", "`mod/mapmaking.htm`"),
    ("<mapmaking.htm>", "<mod/mapmaking.htm>"),
    ("`randommap.htm`", "`mod/randommap.htm`"),
    ("`aimaking.htm`", "`mod/aimaking.htm`"),
    ("`server.htm`", "`mod/server.htm`"),
    ("`skills-and-effects.htm`", "`mod/skills-and-effects.htm`"),
    ("doc/zh/manual.htm", "doc/zh/player/manual.htm"),
    ("doc/zh/modding.htm", "doc/zh/mod/modding.htm"),
    ("doc/zh/mapmaking.htm", "doc/zh/mod/mapmaking.htm"),
    ("doc/zh/randommap.htm", "doc/zh/mod/randommap.htm"),
    ("doc_src/src/zh/modding.rst", "mod/modding.rst"),
    ("doc_src/src/en/modding.rst", "mod/modding.rst"),
    ("doc_src/src/zh/mapmaking.rst", "mod/mapmaking.rst"),
    ("doc_src/src/en/mapmaking.rst", "mod/mapmaking.rst"),
    ("doc_src/src/zh/manual.rst", "player/manual.rst"),
    ("doc_src/src/en/manual.rst", "player/manual.rst"),
    ("doc_src/src/zh/randommap.rst", "mod/randommap.rst"),
    ("guides/mod/寻找物品", "mod/campaign/find-item"),
    ("guides/mod/给NPC", "mod/campaign/give-to-npc"),
    ("guides/mod/指定序号", "mod/campaign/unit-index"),
    ("guides/mod/渐进式", "mod/campaign/progressive-objectives"),
    ("guides/mod/战役跨章", "mod/campaign/hero-carryover"),
    ("guides/mod/coop-campaign", "mod/campaign/coop"),
    ("guides/player/分层热键", "player/layered-hotkeys"),
    ("guides/player/随机地图", "player/random-map-play"),
    ("guides/player/英雄无敌", "player/homm-civ5-play"),
    ("../developer/", "../mod/"),
    ("../guides/mod/", "../mod/"),
    ("../guides/player/", "../player/"),
]


def fix(text: str) -> str:
    for old, new in REPL:
        text = text.replace(old, new)
    text = re.sub(r"mod/mod/mod/", "mod/", text)
    text = re.sub(r"player/player/", "player/", text)
    return text


def main() -> None:
    n = 0
    for lang in ("zh", "en"):
        base = ROOT / lang
        if not base.is_dir():
            continue
        for rst in base.rglob("*.rst"):
            if "pt-BR" in rst.parts:
                continue
            try:
                t = rst.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            nt = fix(t)
            if nt != t:
                rst.write_text(nt, encoding="utf-8")
                n += 1
    print(f"patched {n} files")


if __name__ == "__main__":
    main()
