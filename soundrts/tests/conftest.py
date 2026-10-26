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

from .stub_client_modules import STUBBED_MODULE_NAMES


@pytest.fixture(autouse=True)
def _purge_injected_module_stubs():
    """Remove stub modules that a test injected into ``sys.modules``.

    A few tests stub out the pygame-facing client modules so that importing
    ``clientgameentity.properties`` does not drag in the whole UI stack.
    Those stubs were installed with a plain ``sys.modules[name] = ...`` and
    never removed, so they stayed visible to every test that ran afterwards.
    A later ``from soundrts.clientmenu import CLOSE_MENU`` then hit the
    empty stub and failed with "cannot import name 'CLOSE_MENU' (unknown
    location)" -- a failure that had nothing to do with the test that
    reported it.

    Here we snapshot the stub names before the test and drop any that were
    added during it, so the stub never leaks past the test that needed it.

    This is a safety net for stubs injected *during* a test.  Stubs injected
    at module import time (as ``test_neutral_passive_creep.py`` does) are
    handled by ``stub_client_modules.restore_client_modules`` at their
    source instead.
    """
    before = {name for name in STUBBED_MODULE_NAMES if name in sys.modules}
    yield
    for name in STUBBED_MODULE_NAMES:
        if name not in before and name in sys.modules:
            del sys.modules[name]


@pytest.fixture(scope="module", autouse=True)
def _isolate_module_rules():
    """Restore the global ``rules`` singleton after each test module.

    Many test modules call ``rules.load(...)`` on the process-wide singleton
    (e.g. to load the AoE2 mod rules).  ``rules.load`` replaces
    ``rules._dict`` wholesale, so those rules stay visible to every module
    that runs afterwards.  AoE2 sets ``achievements_enabled 0``, which made
    ``test_card_loadout`` see an empty loadout even though it passed in
    isolation.

    This fixture is module-scoped and autouse, so it is set up before the
    module's own fixtures (which do the ``rules.load``) and torn down after
    them, restoring the base rules the suite started with.
    """
    from soundrts.definitions import rules

    saved = (
        rules._dict,
        getattr(rules, "classes", None),
        getattr(rules, "_factions_cache", None),
        getattr(rules, "_race_equiv_index", None),
    )
    yield
    rules._dict = saved[0]
    if saved[1] is not None:
        rules.classes = saved[1]
    rules._factions_cache = saved[2]
    rules._race_equiv_index = saved[3]


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
