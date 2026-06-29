#!/usr/bin/env python3
"""Repair malformed grid tables in migrated RST guides."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUIDES = ROOT / "doc_src" / "src"


def _pipe_table_to_list_table(rows: list[list[str]]) -> list[str]:
    if not rows:
        return []
    header = rows[0]
    body = rows[1:]
    lines = [".. list-table::", "   :header-rows: 1", ""]
    lines.append("   * - " + header[0])
    for cell in header[1:]:
        lines.append("     - " + cell)
    for row in body:
        lines.append("   * - " + (row[0] if row else ""))
        for cell in row[1:]:
            lines.append("     - " + cell)
    lines.append("")
    return lines


def fix_tables(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("+") and re.match(r"^\+[-=:]+\+", line):
            block = [line]
            i += 1
            while i < len(lines) and (
                lines[i].startswith("|") or re.match(r"^\+[-=:]+\+", lines[i])
            ):
                block.append(lines[i])
                i += 1
            rows: list[list[str]] = []
            for bl in block:
                if bl.startswith("|"):
                    cells = [c.strip() for c in bl.strip().strip("|").split("|")]
                    rows.append(cells)
            if rows:
                out.extend(_pipe_table_to_list_table(rows))
            else:
                out.extend(block)
            continue
        out.append(line)
        i += 1
    return "\n".join(out) + "\n"


def bulk_doc_paths(text: str) -> str:
    reps = [
        ("docs/zh/player/", "guides/player/"),
        ("docs/zh/developer/", "guides/mod/"),
        ("docs/en/player/", "guides/player/"),
        ("docs/en/developer/", "guides/mod/"),
        ("docs/zh/", "guides/"),
        ("docs/en/", "guides/"),
        ("docs/README.md", "help-index.htm"),
        ("GENERIC_SKILL_SYSTEM.md", "skills-and-effects.htm"),
        ("HEAL_HARM_自定义功能说明.md", "skills-and-effects.htm"),
        ("EFFECT_BUFF_SYSTEM_说明.md", "skills-and-effects.htm"),
    ]
    for old, new in reps:
        text = text.replace(old, new)
    text = re.sub(r"\.md(?=[)`\"])", ".htm", text)
    return text


def main() -> None:
    n = 0
    for rst in GUIDES.rglob("*.rst"):
        if "pt-BR" in rst.parts:
            continue
        try:
            text = rst.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        new = bulk_doc_paths(fix_tables(text))
        if new != text:
            rst.write_text(new, encoding="utf-8")
            n += 1
    print(f"fixed {n} files")


if __name__ == "__main__":
    main()
