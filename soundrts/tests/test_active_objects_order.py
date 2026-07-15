"""active_objects order dirty-flag: sort only when membership changes."""
from __future__ import annotations

import types


def test_active_objects_snapshot_sorts_only_when_dirty():
    from soundrts.world.world_core import World

    # Minimal stand-in: copy register/unregister/snapshot behavior onto a stub.
    class _W:
        def __init__(self):
            self.active_objects = []
            self._active_objects_order_dirty = True
            self.objects = {}
            self._next_id = 0
            self._ecs = None

        get_next_id = World.get_next_id
        register_entity = World.register_entity
        unregister_entity = World.unregister_entity
        _active_objects_snapshot = World._active_objects_snapshot

    w = _W()
    a = types.SimpleNamespace(update=lambda: None)
    b = types.SimpleNamespace(update=lambda: None)
    w.register_entity(a)
    w.register_entity(b)
    assert w._active_objects_order_dirty is True
    s1 = w._active_objects_snapshot()
    assert w._active_objects_order_dirty is False
    assert [o.id for o in s1] == sorted(o.id for o in s1)
    s2 = w._active_objects_snapshot()
    assert s1 == s2
    w.unregister_entity(a)
    assert w._active_objects_order_dirty is True
    s3 = w._active_objects_snapshot()
    assert [o.id for o in s3] == [b.id]
