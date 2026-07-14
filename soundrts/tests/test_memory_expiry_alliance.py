from soundrts.worldplayerbase.perception import PerceptionMixin


class _World:
    def __init__(self, time):
        self.time = time
        self.units = []


class _Unit:
    def __init__(self, place, speed=1):
        self.place = place
        self.speed = speed
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
        self.units = []
        self.memory = {memory}
        self.perception = {unit}
        self._memory_index = {unit: memory}
        self.observed_squares = set()
        self.observed_before_squares = set()
        self._last_memory_cleanup = 0
        self._memory_scan_cursor = 0
        self._memory_list = []
        self._memory_list_snapshot_time = -1_000_000
        self.detected_units = set()

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


def test_observed_square_forgets_memory_of_unit_that_left():
    """Standing on a square must clear war-cloud ghosts of units that left."""
    here = object()
    elsewhere = object()
    unit = _Unit(elsewhere)
    memory = _Memory(unit, 60_000, here)  # fresh memory, still within duration
    player = _Player(_World(120_000), memory, unit)
    player.perception = set()
    player.observed_squares = {here}

    player._forget_memories_on_observed_squares()

    assert memory not in player.memory
    assert unit not in player._memory_index


def test_observed_square_forgets_memory_when_live_unit_perceived():
    here = object()
    unit = _Unit(here)
    memory = _Memory(unit, 60_000, here)
    player = _Player(_World(120_000), memory, unit)
    player.perception = {unit}
    player.observed_squares = {here}

    player._lightweight_memory_update()

    assert memory not in player.memory


def test_observed_square_forgets_stale_ghost_even_if_not_yet_perceived():
    """Re-scout must drop war-cloud entries; live unit may arrive next tick."""
    here = object()
    unit = _Unit(here)
    memory = _Memory(unit, 60_000, here)
    player = _Player(_World(120_000), memory, unit)
    player.perception = set()
    player.observed_squares = {here}

    player._forget_memories_on_observed_squares()

    assert memory not in player.memory


def test_observed_square_keeps_undetected_cloaked_memory():
    here = object()
    unit = _Unit(here)
    unit.is_cloaked = True
    memory = _Memory(unit, 60_000, here)
    player = _Player(_World(120_000), memory, unit)
    player.perception = set()
    player.observed_squares = {here}
    player.detected_units = set()

    player._forget_memories_on_observed_squares()

    assert memory in player.memory
