from soundrts.worldplayerbase.perception import PerceptionMixin


class _World:
    def __init__(self, time):
        self.time = time
        self.units = []


class _Unit:
    def __init__(self, place):
        self.place = place
        self.speed = 1
        self.is_invisible = False
        self.is_cloaked = False


class _Memory:
    def __init__(self, unit, time_stamp, place):
        self.initial_model = unit
        self.time_stamp = time_stamp
        self.place = place


class _Player(PerceptionMixin):
    memory_duration = 3 * 60 * 1000
    display_memory_duration = memory_duration

    def __init__(self, world, memory, unit):
        self.world = world
        self.memory = {memory}
        self.perception = {unit}
        self._memory_index = {unit: memory}
        self.observed_squares = set()
        self.observed_before_squares = set()
        self._last_memory_cleanup = 0
        self._memory_scan_cursor = 0
        self._memory_list = []
        self._memory_list_snapshot_time = -1_000_000

    def _is_seeing(self, unit):
        return False


def test_expired_memory_removes_stale_perception_entry():
    place = object()
    unit = _Unit(place)
    memory = _Memory(unit, 0, place)
    player = _Player(_World(3 * 60 * 1000 + 1), memory, unit)

    player._update_memory(previous_perception={unit})

    assert memory not in player.memory
    assert unit not in player.perception
    assert unit not in player._memory_index


def test_lightweight_expired_memory_removes_stale_perception_entry():
    place = object()
    unit = _Unit(place)
    memory = _Memory(unit, 0, place)
    player = _Player(_World(3 * 60 * 1000 + 1), memory, unit)

    player._lightweight_memory_update()

    assert memory not in player.memory
    assert unit not in player.perception
    assert unit not in player._memory_index


class _AiViewPlayer(_Player):
    memory_duration = 36000000
    display_memory_duration = 3 * 60 * 1000


def test_ai_view_display_expiry_keeps_internal_memory_but_hides_stale_enemy():
    place = object()
    unit = _Unit(place)
    memory = _Memory(unit, 0, place)
    player = _AiViewPlayer(_World(3 * 60 * 1000 + 1), memory, unit)

    player._update_memory(previous_perception={unit})

    assert memory in player.memory
    assert unit in player._memory_index
    assert memory.time_stamp == 0
    assert unit not in player.perception


def test_ai_view_sends_only_unexpired_display_memory():
    place = object()
    unit = _Unit(place)
    memory = _Memory(unit, 0, place)
    player = _AiViewPlayer(_World(3 * 60 * 1000 + 1), memory, unit)

    assert memory in player.memory
    assert player.memory_for_display() == set()
