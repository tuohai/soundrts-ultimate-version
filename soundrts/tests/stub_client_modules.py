"""Names of the client modules that tests may stub out.

Several tests need to import ``soundrts.clientgameentity.properties``
without dragging in the whole pygame-facing UI stack.  They do that by
installing stub modules into ``sys.modules`` for the names listed here.

The stubs are only valid while the import is happening.  If they are left
in ``sys.modules`` afterwards, every later ``from soundrts.clientmenu
import ...`` resolves against the empty stub and fails with "cannot import
name 'CLOSE_MENU' (unknown location)" -- a failure that surfaces in an
unrelated test.  Use :func:`stub_client_modules` together with
:func:`restore_client_modules` so the stubs never leak.
"""

from __future__ import annotations

import sys
import types


STUBBED_MODULE_NAMES = (
    "soundrts.clientmedia",
    "soundrts.clientmenu",
    "soundrts.animation",
    "soundrts.clientgamenews",
    "soundrts.clientgameorder",
    "soundrts.lib.sound",
)


def stub_client_modules():
    """Install stub modules for the client stack and return the saved state.

    The returned value is what :func:`restore_client_modules` expects.
    """
    saved = {name: sys.modules.get(name) for name in STUBBED_MODULE_NAMES}

    if "soundrts.clientmedia" not in sys.modules:
        stub = types.ModuleType("soundrts.clientmedia")
        stub.sounds = None
        stub.voice = None
        sys.modules["soundrts.clientmedia"] = stub
    if "soundrts.clientmenu" not in sys.modules:
        sys.modules["soundrts.clientmenu"] = types.ModuleType("soundrts.clientmenu")
    if "soundrts.animation" not in sys.modules:
        ani = types.ModuleType("soundrts.animation")
        ani.noise = lambda *a, **kw: None
        sys.modules["soundrts.animation"] = ani
    if "soundrts.clientgamenews" not in sys.modules:
        news = types.ModuleType("soundrts.clientgamenews")
        news.must_be_said = lambda *a, **kw: False
        sys.modules["soundrts.clientgamenews"] = news
    if "soundrts.clientgameorder" not in sys.modules:
        co = types.ModuleType("soundrts.clientgameorder")
        co.get_orders_list = lambda: []
        co.substitute_args = lambda *a, **kw: None
        sys.modules["soundrts.clientgameorder"] = co
    if "soundrts.lib.sound" not in sys.modules:
        s = types.ModuleType("soundrts.lib.sound")
        s.distance = lambda *a, **kw: 0
        s.psounds = None
        s.angle = lambda *a, **kw: 0
        s.MUSIC_FORMATS = [".mp3", ".ogg", ".wav"]
        sys.modules["soundrts.lib.sound"] = s

    return saved


def restore_client_modules(saved):
    """Undo :func:`stub_client_modules` using the state it returned."""
    for name, module in saved.items():
        if module is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = module
