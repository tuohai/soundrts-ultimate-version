# -*- coding: utf-8 -*-
"""No module may import from *above* its own package.

``from ..version import ...`` inside ``soundrts/clientservermenu.py`` means
"one level above ``soundrts``", which does not exist.  The import is only
evaluated when the statement runs, so such a bug can sit in the tree for
months and then kill a real game session: it happened when a host created
a game and the client died with

    ImportError: attempted relative import beyond top-level package

while the menu reported "error during connection to server".

The same mistake existed in three other places, all of them latent runtime
bombs (``soundrts/worldaction.py``, ``soundrts/attributes/key_bindings.py``,
``soundrts/worldunit/world_status_update.py``).

This test scans the whole package with the AST and fails on any relative
import that goes above the package it lives in, so the class of bug
cannot come back.
"""
from __future__ import annotations

import ast
from pathlib import Path


def test_no_relative_import_escapes_its_package():
    """No module may import from *above* its own package.

    The package depth is what decides: ``soundrts`` is 1, so a module
    directly in it may use ``from .x import y`` but not ``from ..x import
    y``; ``soundrts/worldunit`` is 2, so it may use ``..`` but not
    ``...``.
    """
    root = Path(__file__).resolve().parents[1]  # the "soundrts" package
    offenders = []
    for path in root.rglob("*.py"):
        rel = path.relative_to(root).parts
        if rel[0] == "tests":
            continue
        # The package depth: "soundrts" is 1, "soundrts/worldunit" is 2.
        depth = len(rel)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            if node.level and node.level > depth:
                offenders.append(
                    "%s:%d  from %s"
                    % (
                        path.relative_to(root),
                        node.lineno,
                        "." * node.level + (node.module or ""),
                    )
                )

    assert not offenders, (
        "relative imports that escape their package:\n  " + "\n  ".join(offenders)
    )
