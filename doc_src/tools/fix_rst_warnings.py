#!/usr/bin/env python3
"""Fix common RST markup issues that produce docutils WARNING messages."""
from __future__ import annotations

import io
import re
from pathlib import Path

from docutils.core import publish_string

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "doc_src" / "src"

UNDERLINE_CHARS = set('=-~^"')


def _probe_underline_len(title: str, char: str) -> int:
    for n in range(len(title), len(title) + 40):
        err = io.StringIO()
        publish_string(
            f"{title}\n{char * n}\n\nx\n",
            writer_name="html",
            settings_overrides={"warning_stream": err, "report_level": 2},
        )
        if "Title underline too short" not in err.getvalue():
            return n
    return len(title) + 40


def _fix_md_link_literals(text: str) -> str:
    patterns = [
        (r"```([^`\n]+?)`` <([^>\n]+?)>``_", r"`\1 <\2>`_"),
        (r"``([^`\n]+?)` <([^>\n]+?)>`_", r"`\1 <\2>`_"),
        (r"``([^`\n]+?) <([^>\n]+?)>``_", r"`\1 <\2>`_"),
        (r"``([^`\n]+?)\.md <([^>\n]+?)>``_", r"`\1 <\2>`_"),
        (r"``([^`\n]+?)` <([^>\n]+?)>``_", r"`\1 <\2>`_"),
        (r"```([^`\n]+?)`` <([^>\n]+?)>`?_", r"``\1``"),
    ]
    for pat, repl in patterns:
        text = re.sub(pat, repl, text)
    return text


def _fix_legacy_paths(text: str) -> str:
    reps = [
        ("../player/achievements.md", "../player/achievements.htm"),
        ("../../en/developer/", "../../en/mod/"),
        ("../../zh/developer/", "../../zh/mod/"),
        ("guides/player/", "player/"),
        ("guides/mod/", "mod/"),
        ("developer/", "mod/"),
        ("campaign-secret-letter-alliance.md", "campaign-northern-arc.htm"),
        ("hunting-system.md", "hunting.htm"),
        ("starcraft-terran-addons.md", "starcraft-terran.htm"),
        ("starcraft-resources-vespene.md", "starcraft-resources.htm"),
        ("achievements.md", "achievements.htm"),
        ("score-grading-system.md", "score-grading-system.htm"),
        ("delayed-card-loadout.md", "delayed-card-loadout.htm"),
    ]
    for old, new in reps:
        text = text.replace(old, new)
    return text


def _escape_literal_inner(inner: str) -> str:
    if "<" in inner or ">" in inner:
        inner = re.sub(r"(?<!\\)<", r"\\<", inner)
        inner = re.sub(r"(?<!\\)>", r"\\>", inner)
    inner = re.sub(r"(?<![\\a-zA-Z0-9])_(?=[a-zA-Z])", r"\\_", inner)
    return inner


def _fix_double_backtick_literals(text: str) -> str:
    def repl(m: re.Match[str]) -> str:
        inner = m.group(1)
        if "\\<" in inner and "\\>" in inner:
            return m.group(0)
        if "<" in inner or ">" in inner or re.search(r"(?:^|[/ ])_", inner):
            return f"``{_escape_literal_inner(inner)}``"
        return m.group(0)

    return re.sub(r"``([^`\n]+?)``", repl, text)


def _repair_corrupted_table_rows(text: str) -> str:
    """Undo accidental double-application on list-table first-column cells."""
    text = re.sub(
        r"^(\s+\* - )``\s+\* - ``([^`\n]+)$",
        r"\1``\2``",
        text,
        flags=re.M,
    )
    return text


def _fix_table_cell_backticks(text: str) -> str:
    def repl(m: re.Match[str]) -> str:
        return f"{m.group(1)}``{m.group(2)}``"

    return re.sub(
        r"^(\s+\* - )`([^`\n]+)`\s*$",
        repl,
        text,
        flags=re.M,
    )


def _fix_extra_backticks(text: str) -> str:
    text = re.sub(r"``([^`\n]+?)```+", r"``\1``", text)
    text = re.sub(r":strong:```([^`\n]+?)```", r"``\1``", text)
    text = re.sub(r"`([^`\n]+?) <([^>\n]+?)>``_`+", r"`\1 <\2>`_", text)
    text = re.sub(r"``computer1```", r"``computer1``", text)
    return text


def _fix_literal_adjacent_punctuation(text: str) -> str:
    text = re.sub(r"``([^`\n]+?)``\(", r"``\1`` (", text)
    text = re.sub(r"``([^`\n]+?)``\+", r"``\1`` +", text)
    return text


def _fix_unclosed_bold(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if line.count("**") == 1:
            line = line.replace("**", "", 1)
        lines.append(line)
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def _fix_paren_command_literals(text: str) -> str:
    return re.sub(
        r"^(     - [^`\n]*?)`(\([^`\n]+?)`",
        r"\1``\2``",
        text,
        flags=re.M,
    )


def _fix_mismatched_double_backticks(text: str) -> str:
    """``word` -> ``word`` when closing uses a single backtick."""
    return re.sub(r"``([^`\n]{1,120})`(?=[\s,;.)]|$|（|、)", r"``\1``", text)


def _fix_literal_before_cjk_punctuation(text: str) -> str:
    """Insert space after ``literal`` before CJK opening punctuation.

    docutils treats ``word``（ as an unclosed literal; a space fixes parsing.
    """
    text = re.sub(
        r"``([^`\n]+?)``([（「『【])",
        r"``\1`` \2",
        text,
    )
    text = re.sub(r"`(\d+)`（", r"``\1``（", text)
    return text


def _fix_literal_footnote_suffix(text: str) -> str:
    return re.sub(r"``([^`\n]+?)``_", r"``\1``", text)


def _fix_table_short_literals(text: str) -> str:
    text = re.sub(r"^(\s+- )`([01])`", r"\1``\2``", text, flags=re.M)
    text = re.sub(r"^(\s+- )`([01])` / `([01])`", r"\1``\2`` / ``\3``", text, flags=re.M)
    return text


def _fix_enumerated_sublist(text: str) -> str:
    """Insert blank line + indent when numbered item is followed by top-level bullets."""
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        if re.match(r"^\d+\.\s", line) and line.rstrip().endswith("："):
            if i + 1 < len(lines) and re.match(r"^-\s", lines[i + 1]):
                out.append("")
                j = i + 1
                while j < len(lines) and re.match(r"^-\s", lines[j]):
                    out.append("   " + lines[j])
                    j += 1
                i = j
                continue
        i += 1
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


def _fix_epigraph_lines(text: str) -> str:
    """Convert fragile .. epigraph:: blocks to plain paragraphs."""
    if ".. epigraph::" not in text:
        return text
    out: list[str] = []
    skip_blank = False
    for line in text.splitlines():
        if line.strip().startswith(".. epigraph::"):
            content = line.split(".. epigraph::", 1)[1].strip()
            if content.startswith("- "):
                content = content[2:]
            out.append("")
            out.append(content)
            skip_blank = True
            continue
        if skip_blank and not line.strip():
            skip_blank = False
            continue
        skip_blank = False
        out.append(line)
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


def _fix_inline_identifiers(text: str) -> str:
    """`spawn` in prose -> ``spawn``; skip `label <url>`_ links."""
    return re.sub(
        r"(?<![`<:])`([a-zA-Z_][a-zA-Z0-9_]*)`(?!\s*<)",
        r"``\1``",
        text,
    )


def _fix_strong_markers(text: str) -> str:
    text = re.sub(
        r":strong:``([^`\n]+?) <([^>\n]+?)>``_",
        r"`\1 <\2>`_",
        text,
    )
    text = re.sub(r":strong:``([^`\n]+?)`", r"``\1``", text)
    text = re.sub(r":strong:`([^`\n]+?)``", r"``\1``", text)
    text = re.sub(r":strong:`([^`\n]+?)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    return text


def _fix_title_underlines(text: str) -> str:
    lines = text.splitlines()
    for i in range(len(lines) - 1):
        title = lines[i]
        ul = lines[i + 1]
        if not title.strip():
            continue
        if not ul or ul[0] not in UNDERLINE_CHARS:
            continue
        if not all(c in UNDERLINE_CHARS for c in ul):
            continue
        need = _probe_underline_len(title, ul[0])
        if len(ul) < need:
            lines[i + 1] = ul[0] * need
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def _fix_list_before_code_block(text: str) -> str:
    text = re.sub(
        r"(\n(?:[ \t]*[-*+].+\n)+[ \t]*[-*+][^\n]+\n)(\.\. code-block::)",
        r"\1\n\2",
        text,
    )
    text = re.sub(
        r"(\n(?:[ \t]*\d+\..+\n)+[ \t]*\d+\.[^\n]+\n)(\.\. code-block::)",
        r"\1\n\2",
        text,
    )
    return text


def _fix_epigraph_bold(text: str) -> str:
    out: list[str] = []
    in_epigraph = False
    for line in text.splitlines():
        if line.strip().startswith(".. epigraph::"):
            in_epigraph = True
            line = re.sub(r"\*\*([^*]+)\*\*", r"\1", line)
        elif in_epigraph and line and not line[0].isspace():
            in_epigraph = False
        elif in_epigraph:
            line = re.sub(r"\*\*([^*]+)\*\*", r"\1", line)
        out.append(line)
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


def _fix_inline_phrase_refs(text: str) -> str:
    """`scope meta` and similar space-containing identifiers."""
    return re.sub(
        r"(?<![`<:])`([a-zA-Z_][a-zA-Z0-9_ ]*)`(?!\s*<)",
        lambda m: f"``{m.group(1)}``" if " " in m.group(1) else m.group(0),
        text,
    )


def _fix_link_spacing(text: str) -> str:
    text = re.sub(r"`>_([（\u4e00-\u9fff])", r"`>_ \1", text)
    text = re.sub(r"`_（", r"`_ （", text)
    text = re.sub(r"``([^`\n]+?)``%", r"``\1`` %", text)
    text = re.sub(r"`(\[[^\]]+\][^`]*)`", r"``\1``", text)
    return text


def _fix_code_block_lexers(text: str) -> str:
    text = text.replace(".. code-block:: txt", ".. code-block:: text")
    text = text.replace(".. code-block:: mermaid", ".. code-block:: text")
    return text


def fix_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    orig = text
    text = _fix_legacy_paths(text)
    text = _repair_corrupted_table_rows(text)
    text = _fix_md_link_literals(text)
    text = _fix_code_block_lexers(text)
    text = _fix_double_backtick_literals(text)
    text = _fix_mismatched_double_backticks(text)
    text = _fix_extra_backticks(text)
    text = _fix_literal_adjacent_punctuation(text)
    text = _fix_unclosed_bold(text)
    text = _fix_paren_command_literals(text)
    text = _fix_literal_before_cjk_punctuation(text)
    text = _fix_literal_footnote_suffix(text)
    text = _fix_table_short_literals(text)
    text = _fix_enumerated_sublist(text)
    text = _fix_epigraph_lines(text)
    text = _fix_table_cell_backticks(text)
    text = _fix_inline_identifiers(text)
    text = _fix_inline_phrase_refs(text)
    text = _fix_strong_markers(text)
    text = _fix_title_underlines(text)
    text = _fix_list_before_code_block(text)
    text = _fix_epigraph_bold(text)
    text = _fix_link_spacing(text)
    if text != orig:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> None:
    n = 0
    for rst in sorted(SRC.rglob("*.rst")):
        if "pt-BR" in rst.parts:
            continue
        if fix_file(rst):
            n += 1
            print("fixed", rst.relative_to(ROOT))
    print(f"updated {n} files")


if __name__ == "__main__":
    main()
