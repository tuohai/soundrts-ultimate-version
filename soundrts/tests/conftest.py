"""Shared pytest setup for the SoundRTS test suite.

Importing ``soundrts`` triggers ``soundrts.options._parse_options()`` at module
import time, which calls ``optparse.parse_args()`` on the real ``sys.argv``.
When pytest is invoked with its own flags (``-q``, ``--tb=line``, a specific
test id, ...) optparse raises ``SystemExit`` on the unknown options, which
aborts collection for any test module that imports ``soundrts`` before another
module has already cached ``soundrts.options``.

To make the suite robust regardless of invocation or collection order, we
sanitize ``sys.argv`` (keeping only the program name) before the first import
happens, then restore it. We also silence the noisy ``locale.getdefaultlocale``
deprecation warning emitted while importing ``soundrts.lib.resource``.
"""
import os
import sys
import warnings

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

_saved_argv = sys.argv
sys.argv = [sys.argv[0]]
try:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        import soundrts.options  # noqa: F401  (triggers the one-time arg parse)
finally:
    sys.argv = _saved_argv

import pytest


@pytest.fixture(autouse=True)
def _isolate_resource_mods():
    """Restore res.mods after tests that switch mods (e.g. crazyMod9beta10).

    Per-faction mod titles leave get_current_rank() without faction as None;
    leaking mods breaks tests expecting base res/titles.txt ranks.
    """
    from soundrts.lib.resource import res

    saved_mods = res.mods
    yield
    if res.mods != saved_mods:
        res.set_mods(saved_mods)
