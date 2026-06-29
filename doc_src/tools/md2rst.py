"""Convert project Markdown guides to reStructuredText for builddoc."""
from __future__ import annotations

import re
from pathlib import Path


def _underline(title: str, char: str) -> str:
    return f"{title}\n{char * len(title)}\n"


def md_link_to_rst(text: str) -> str:
    def repl(m: re.Match) -> str:
        label, url = m.group(1), m.group(2)
        if url.endswith(".md"):
            url = url[:-3] + ".htm"
        if url.startswith("../") or url.startswith("http"):
            return f"`{label} <{url}>`_"
        return f"`{label} <{url}>`_"

    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", repl, text)


def convert_md_to_rst(md: str) -> str:
    lines = md.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    i = 0
    in_code = False
    code_lang = ""
    code_lines: list[str] = []
    table_buf: list[str] = []

    def flush_table() -> None:
        nonlocal table_buf
        if not table_buf:
            return
        rows = [r for r in table_buf if re.match(r"^\|.+\|$", r.strip())]
        if len(rows) >= 2 and re.match(r"^\|[\s\-:|]+\|$", rows[1].strip()):
            header = [c.strip() for c in rows[0].strip().strip("|").split("|")]
            sep = ["-" * max(3, len(c)) for c in header]
            out.append("")
            out.append("+" + "+".join("-" * (len(c) + 2) for c in header) + "+")
            out.append("| " + " | ".join(header) + " |")
            out.append("+" + "+".join("=" * (len(c) + 2) for c in header) + "+")
            for row in rows[2:]:
                cells = [c.strip() for c in row.strip().strip("|").split("|")]
                while len(cells) < len(header):
                    cells.append("")
                out.append("| " + " | ".join(cells[: len(header)]) + " |")
                out.append("+" + "+".join("-" * (len(c) + 2) for c in header) + "+")
            out.append("")
        else:
            out.extend(table_buf)
        table_buf = []

    while i < len(lines):
        line = lines[i]

        if in_code:
            if line.strip().startswith("```"):
                block = "\n".join(code_lines)
                lang = code_lang or "text"
                out.append(f".. code-block:: {lang}")
                out.append("")
                out.extend("   " + ln for ln in block.split("\n"))
                out.append("")
                in_code = False
                code_lines = []
                code_lang = ""
            else:
                code_lines.append(line)
            i += 1
            continue

        if line.strip().startswith("```"):
            flush_table()
            fence = line.strip()[3:].strip()
            in_code = True
            code_lang = fence or "text"
            i += 1
            continue

        if line.strip().startswith("|"):
            table_buf.append(line)
            i += 1
            continue
        flush_table()

        if line.strip() == "---":
            out.append("")
            out.append("----")
            out.append("")
            i += 1
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            level = len(m.group(1))
            title = md_link_to_rst(m.group(2).strip())
            chars = ["=", "-", "~", "^", '"', "'"]
            out.append(_underline(title, chars[min(level - 1, len(chars) - 1)]))
            i += 1
            continue

        if line.startswith(">"):
            text = md_link_to_rst(line.lstrip("> ").strip())
            out.append(f".. epigraph:: {text}")
            out.append("")
            i += 1
            continue

        stripped = line.strip()
        if stripped.startswith("- ") or stripped.startswith("* "):
            out.append(md_link_to_rst(stripped))
            i += 1
            continue

        if re.match(r"^\d+\.\s", stripped):
            out.append(md_link_to_rst(stripped))
            i += 1
            continue

        if stripped.startswith("```"):
            i += 1
            continue

        if not stripped:
            out.append("")
        else:
            text = md_link_to_rst(line)
            text = re.sub(r"\*\*([^*]+)\*\*", r"**\1**", text)
            text = re.sub(r"`([^`]+)`", r"``\1``", text)
            out.append(text)
        i += 1

    flush_table()
    if in_code and code_lines:
        out.append(f".. code-block:: {code_lang or 'text'}")
        out.append("")
        out.extend("   " + ln for ln in code_lines)
        out.append("")
    return "\n".join(out).strip() + "\n"


def migrate_tree(src_root: Path, dst_root: Path, sub: str) -> list[Path]:
    created: list[Path] = []
    src = src_root / sub
    if not src.is_dir():
        return created
    for md in sorted(src.rglob("*.md")):
        if md.name.upper() == "README.MD" or md.name == "README.md":
            continue
        rel = md.relative_to(src)
        rst_path = dst_root / sub / rel.with_suffix(".rst")
        rst_path.parent.mkdir(parents=True, exist_ok=True)
        rst_path.write_text(convert_md_to_rst(md.read_text(encoding="utf-8")), encoding="utf-8")
        created.append(rst_path)
    return created
