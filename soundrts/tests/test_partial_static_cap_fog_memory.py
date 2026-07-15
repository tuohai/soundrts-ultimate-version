"""Partial-sight bulk static cap must still fog-memorize overflow (1.3.8.1).

Regression: when many static objects sit on partially observed squares, the
visibility check is capped at 100. Uncapped meadows/mines used to be dropped
entirely (neither perception nor memory), while exits could still appear via
``_memorize_unseen_exit_pairs`` — fog squares showed only exits until a unit
arrived.

Performance: overflow uses ``_ensure_static_fog_memory`` so already-memorized
statics are not re-copied every forced perception tick.
"""
from __future__ import annotations

from soundrts.worldplayerbase.perception import PerceptionMixin


class _Sq:
    __slots__ = ("id", "objects")

    def __init__(self, sid):
        self.id = sid
        self.objects = []

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return isinstance(other, _Sq) and self.id == other.id


class _Static:
    __slots__ = (
        "id",
        "player",
        "place",
        "speed",
        "is_a_building_land",
        "is_an_exit",
        "is_invisible",
        "is_cloaked",
        "other_side",
    )

    def __init__(self, uid, place, *, building_land=False, is_exit=False):
        self.id = uid
        self.player = None
        self.place = place
        self.speed = 0
        self.is_a_building_land = building_land
        self.is_an_exit = is_exit
        self.is_invisible = False
        self.is_cloaked = False
        self.other_side = None
        place.objects.append(self)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return isinstance(other, _Static) and self.id == other.id


class _Player(PerceptionMixin):
    def __init__(self):
        self.memory = set()
        self._memory_index = {}
        self._memory_by_place = {}
        self._memory_by_place_count = 0
        self.perception = set()
        self.observed_squares = set()
        self.world = type("W", (), {"time": 1000})()
        self._bulk_calls = []

    def _bulk_memorize(self, objects):
        objs = list(objects)
        self._bulk_calls.append(objs)
        for obj in objs:
            self._memory_index[obj] = obj
            self.memory.add(obj)


def test_partial_static_cap_overflow_is_fog_memorized():
    """>100 partial statics: overflow meadows must still enter fog memory."""
    p = _Player()
    squares = [_Sq(i) for i in range(30)]
    meadows = []
    for i, sq in enumerate(squares):
        for j in range(4):
            meadows.append(_Static(i * 10 + j, sq, building_land=True))
    assert len(meadows) == 120

    objects_to_check = set(meadows)
    _BULK_STATIC_CAP = 100
    capped = [o for o in objects_to_check if o.is_a_building_land]
    capped.sort(key=lambda o: o.id)
    capped = capped[:_BULK_STATIC_CAP]
    visibility_set = set(capped)
    overflow_to_memory = objects_to_check - visibility_set
    # Cap path: visibility-unseen + overflow → ensure (same as production)
    memory_objects = set(visibility_set)  # all unseen in this stub
    to_ensure = memory_objects | overflow_to_memory
    p._ensure_static_fog_memory(to_ensure)

    assert len(overflow_to_memory) == 20
    assert {o.id for o in p._memory_index} == {o.id for o in meadows}


def test_ensure_static_fog_memory_skips_already_memorized():
    """Second ensure must not re-bulk_memorize already indexed statics."""
    p = _Player()
    sq = _Sq(0)
    meadows = [_Static(i, sq, building_land=True) for i in range(5)]
    p._ensure_static_fog_memory(meadows)
    assert len(p._bulk_calls) == 1
    assert len(p._bulk_calls[0]) == 5

    p._ensure_static_fog_memory(meadows)
    assert len(p._bulk_calls) == 1  # no second bulk

    # Only the one missing object is memorized.
    extra = _Static(99, sq, building_land=True)
    p._ensure_static_fog_memory(meadows + [extra])
    assert len(p._bulk_calls) == 2
    assert p._bulk_calls[1] == [extra]


def test_source_partial_cap_uses_ensure_for_overflow():
    """Source contract: overflow path uses ensure, not full bulk every tick."""
    from pathlib import Path

    src = Path(__file__).resolve().parents[1].joinpath(
        "worldplayerbase", "perception.py"
    ).read_text(encoding="utf-8")
    assert "overflow_to_memory" in src
    assert "_ensure_static_fog_memory" in src
    assert "to_ensure = set(memory_objects) | overflow_to_memory" in src
    assert 'not getattr(o, "speed", 0)' in src
