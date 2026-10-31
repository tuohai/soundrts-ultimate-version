# -*- coding: utf-8 -*-
"""AoE2 ``rules.txt`` alignment with the official Definitive Edition data.

The 42 DE civilizations each have two unique technologies and one or two
unique units.  This module checks that ``mods/aoe2/rules.txt``:

    * defines every DE unique technology,
    * defines every DE unique unit,
    * makes every DE unique technology reachable (a civ's building or
      one of its units may research / use it).

The reference is ``_ut_canonical.json`` (AoE2 DB + aoe2.is), which was
itself cross-checked against the official DE civ blurbs.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RULES = ROOT / "mods" / "aoe2" / "rules.txt"
CANON = ROOT / "_ut_canonical.json"

pytestmark = pytest.mark.skipif(
    not CANON.exists(),
    reason="_ut_canonical.json not available",
)


def _load_blocks(path: Path) -> dict[str, list[str]]:
    """{name: [lines]} for every ``def <name>`` block in rules.txt."""
    blocks: dict[str, list[str]] = {}
    current: str | None = None
    for raw in path.read_text(encoding="utf-8").split("\n"):
        line = raw.strip()
        m = re.match(r"^def\s+(\S+)", line)
        if m:
            current = m.group(1)
            blocks.setdefault(current, [])
            continue
        if current is None:
            continue
        if not line:
            current = None
            continue
        if line.startswith(";"):
            continue
        blocks[current].append(line)
    return blocks


def _variants(name: str) -> set[str]:
    """The plausible rules.txt ids of a DE display name."""
    base = re.sub(r"[''`]", "", name)
    out: set[str] = set()
    for s in (name, base):
        out.add(re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_"))
        out.add(re.sub(r"[^a-z0-9]+", "", s.lower()))
    return out


@pytest.fixture(scope="module")
def canonical():
    return json.loads(CANON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def blocks():
    return _load_blocks(RULES)


def _resolve(blocks, name: str):
    vs = _variants(name)
    for b in blocks:
        if b in vs:
            return b
    return None


def test_canonical_covers_all_42_civs(canonical):
    assert len(canonical) == 42


def test_every_de_unique_technology_is_defined(canonical, blocks):
    missing = []
    for civ, techs in sorted(canonical.items()):
        for tech in techs:
            if _resolve(blocks, tech["name"]) is None:
                missing.append(f"{civ}: {tech['name']}")
    assert not missing, "missing DE unique technologies: %s" % missing


def test_every_de_unique_unit_is_defined(canonical, blocks):
    missing = []
    for civ, techs in sorted(canonical.items()):
        for tech in techs:
            for unit in tech.get("units", []):
                if unit.lower().startswith("elite "):
                    continue
                if _resolve(blocks, unit) is None:
                    missing.append(f"{civ}: {unit}")
    assert not missing, "missing DE unique units: %s" % missing


def test_every_de_unique_technology_is_reachable(canonical, blocks):
    unreachable = []
    for civ, techs in sorted(canonical.items()):
        ids = [_resolve(blocks, t["name"]) for t in techs]
        ids = [i for i in ids if i]
        granted = set()
        for lines in blocks.values():
            for line in lines:
                if line.startswith("can_research") or line.startswith("can_use_tech"):
                    granted.update(line.split()[1:])
        for i in ids:
            if i not in granted:
                unreachable.append(f"{civ}: {i}")
    assert not unreachable, "unreachable DE unique technologies: %s" % unreachable
