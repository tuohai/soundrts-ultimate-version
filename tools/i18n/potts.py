"""Shared library for the tts.txt <-> gettext PO/POT translation tooling.

This does not change the runtime translation scheme at all: the numeric (or
symbolic) IDs, the tts.txt format, the audio files and mod/campaign
compatibility stay exactly as read by TextTable in
soundrts/lib/sound_cache.py. This module only adds a translator-facing PO
layer on top, so tools like Crowdin/Poedit can be used instead of editing
raw "<id> <text>" lines by hand.

extract_pot.py uses this to turn tts.txt into tts.pot/tts.po.
build_tts.py uses this to turn an edited tts.po back into tts.txt.
check_translations.py uses this to diff keys across languages.
"""
import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
MSGPARTS_PATH = REPO_ROOT / "soundrts" / "msgparts.py"

# Where the consolidated, translator-facing catalog lives: ONE tts.pot and
# ONE tts-<lang>.po for the whole repository, so a translator only ever has
# to open a single file per language (no hunting across res/single/*,
# mods/**, etc.) -- the physical tts.txt files stay exactly where they are.
DATA_DIR = REPO_ROOT / "i18n"

TTS_FILENAME = "tts.txt"
POT_FILENAME = "tts.pot"
PO_FILENAME = "tts.po"

_LANG_DIR_RE = re.compile(r"^ui-(.+)$")


def read_text(path: Path) -> str:
    """Read a tts.txt/po file, transparently stripping a leading UTF-8 BOM
    if present (a few existing tts.txt files have one)."""
    return path.read_text(encoding="utf-8-sig")


# ---------------------------------------------------------------------------
# tts.txt parsing / formatting
# (mirrors TextTable._update_from_text in soundrts/lib/sound_cache.py)
# ---------------------------------------------------------------------------


def parse_tts(text: str) -> Dict[str, str]:
    """Parse tts.txt content into an ordered {key: value} dict.

    Accepts both the "key<whitespace>value" and "key = value" forms, same as
    the runtime TextTable parser. Phrase keys (containing a space) are kept
    alongside numeric keys -- they are just as translatable.
    """
    entries: Dict[str, str] = {}
    text = text.lstrip("﻿")  # strip a leading BOM, some tts.txt files have one
    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line or line.startswith(";") or line.startswith("//"):
            continue
        if "=" in line:
            key, value = line.split("=", 1)
            key, value = key.strip(), value.strip()
        else:
            try:
                key, value = line.split(None, 1)
            except ValueError:
                continue
            value = value.strip()
        if key and value:
            entries[key] = value
    return entries


def format_tts(entries: Dict[str, str]) -> str:
    """Serialize {key: value} back into runtime-parseable tts.txt content.

    Phrase keys (containing a space) must use the "key = value" form: the
    runtime parser splits plain "key value" lines on the first whitespace,
    which would otherwise cut a multi-word key in half.
    """
    lines = ["; coding: utf-8", ""]
    for key, value in entries.items():
        if " " in key:
            lines.append(f"{key} = {value}")
        else:
            lines.append(f"{key}\t{value}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# discovering ui/ui-<lang> directory pairs anywhere under a root
# ---------------------------------------------------------------------------


#: generated/packaged copies of res/mods -- never treat these as sources
EXCLUDED_DIR_NAMES = {"build", "dist", "__pycache__", ".git"}


def find_ui_dirs(root: Path) -> List[Path]:
    """Return every 'ui' or 'ui-<lang>' directory under root that has a
    tts.txt, tts.pot or tts.po file (covers freshly-added languages that
    don't have a tts.txt yet). Skips build/dist/packaged output so those
    duplicated copies don't get treated as extra sources."""
    found = set()
    for filename in (TTS_FILENAME, POT_FILENAME, PO_FILENAME):
        for p in root.rglob(filename):
            if EXCLUDED_DIR_NAMES & set(p.parts):
                continue
            name = p.parent.name
            if name == "ui" or name.startswith("ui-"):
                found.add(p.parent)
    return sorted(found)


def make_reference(ui_dir: Path, key: str) -> str:
    """Build a stable "relative/path/ui/tts.txt:key" reference tying a
    catalog entry back to the physical tts.txt (and key within it) it came
    from. Always posix-style (forward slashes) so references are portable
    and stay readable inside the po file."""
    rel = ui_dir.relative_to(REPO_ROOT).as_posix()
    return f"{rel}/{TTS_FILENAME}:{key}"


def parse_reference(ref: str):
    """Inverse of make_reference: returns (ui_dir: Path, key: str)."""
    path_str, key = ref.rsplit(":", 1)
    ui_dir = (REPO_ROOT / path_str[: -(len(TTS_FILENAME) + 1)]).resolve()
    return ui_dir, key


def lang_dir_for(ui_dir: Path, lang: str) -> Path:
    """Sibling '<parent>/ui-<lang>' directory for a base '<parent>/ui' dir."""
    return ui_dir.parent / f"ui-{lang}"


def group_by_base(ui_dirs: List[Path]) -> Dict[Path, Dict[str, Path]]:
    """Group ui/ui-<lang> dirs by their shared parent directory.

    Returns {parent_dir: {"": Path(.../ui), "fr": Path(.../ui-fr), ...}}
    """
    groups: Dict[Path, Dict[str, Path]] = {}
    for d in ui_dirs:
        parent = d.parent
        if d.name == "ui":
            lang = ""
        else:
            m = _LANG_DIR_RE.match(d.name)
            lang = m.group(1) if m else d.name
        groups.setdefault(parent, {})[lang] = d
    return groups


# ---------------------------------------------------------------------------
# msgparts.py -> translator context (symbolic constant name + comment)
# ---------------------------------------------------------------------------


def load_msgparts_context() -> Dict[str, List[str]]:
    """Map each tts key referenced in msgparts.py to its symbolic constant
    name(s), including any inline "# comment", for use as PO translator
    context (the "#." comment lines)."""
    if not MSGPARTS_PATH.exists():
        return {}
    source = MSGPARTS_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(MSGPARTS_PATH))
    lines = source.split("\n")
    context: Dict[str, List[str]] = {}

    def record(key: str, const_name: str, lineno: int) -> None:
        comment = ""
        line = lines[lineno - 1]
        if "#" in line:
            comment = line.split("#", 1)[1].strip()
        label = const_name if not comment else f"{const_name}: {comment}"
        context.setdefault(key, []).append(label)

    for node in ast.walk(tree):
        if not (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)):
            continue
        const_name = node.targets[0].id
        value = node.value
        if not isinstance(value, ast.List):
            continue  # skip aliases like ARMORY_CARD_HINT = ARMORY_CARD_HINT_PREFIX
        for elt in value.elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, int):
                record(str(elt.value), const_name, node.lineno)
    return context


# ---------------------------------------------------------------------------
# minimal gettext PO/POT read/write (msgctxt = tts key, msgid = source text)
# ---------------------------------------------------------------------------


@dataclass
class PoEntry:
    msgctxt: str
    msgid: str
    msgstr: str = ""
    comments: List[str] = field(default_factory=list)  # translator ("#.") comments
    references: List[str] = field(default_factory=list)  # ("#:") source tts.txt:key locations


def _po_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _po_unescape(s: str) -> str:
    out = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            nxt = s[i + 1]
            if nxt == "n":
                out.append("\n")
                i += 2
                continue
            if nxt in ('"', "\\"):
                out.append(nxt)
                i += 2
                continue
        out.append(c)
        i += 1
    return "".join(out)


_STRING_LINE_RE = re.compile(r'^(msgctxt|msgid|msgstr)\s+"(.*)"$')
_CONT_LINE_RE = re.compile(r'^"(.*)"$')


def write_po(entries: List[PoEntry]) -> str:
    parts = ['msgid ""\nmsgstr ""\n"Content-Type: text/plain; charset=UTF-8\\n"']
    for e in entries:
        block = [f"#. {c}" for c in e.comments]
        block += [f"#: {r}" for r in e.references]
        block.append(f'msgctxt "{_po_escape(e.msgctxt)}"')
        block.append(f'msgid "{_po_escape(e.msgid)}"')
        block.append(f'msgstr "{_po_escape(e.msgstr)}"')
        parts.append("\n".join(block))
    return "\n\n".join(parts) + "\n"


def parse_po(text: str) -> List[PoEntry]:
    """Parse standard PO block syntax (comments, optional msgctxt, msgid,
    msgstr, separated by blank lines). Obsolete ("#~") blocks are skipped."""
    entries: List[PoEntry] = []
    for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n")):
        lines = [l for l in block.split("\n") if l.strip()]
        if not lines or any(l.strip().startswith("#~") for l in lines):
            continue
        comments: List[str] = []
        references: List[str] = []
        fields = {"msgctxt": None, "msgid": None, "msgstr": None}
        current = None
        for line in lines:
            s = line.strip()
            if s.startswith("#."):
                comments.append(s[2:].strip())
                continue
            if s.startswith("#:"):
                references.append(s[2:].strip())
                continue
            if s.startswith("#"):
                continue
            m = _STRING_LINE_RE.match(s)
            if m:
                kind, value = m.group(1), _po_unescape(m.group(2))
                fields[kind] = value
                current = kind
                continue
            m2 = _CONT_LINE_RE.match(s)
            if m2 and current:
                fields[current] = (fields[current] or "") + _po_unescape(m2.group(1))
        msgid = fields["msgid"]
        if msgid is None or (msgid == "" and fields["msgctxt"] is None):
            continue  # header block or malformed entry
        entries.append(PoEntry(
            msgctxt=fields["msgctxt"] or "",
            msgid=msgid,
            msgstr=fields["msgstr"] or "",
            comments=comments,
            references=references,
        ))
    return entries
