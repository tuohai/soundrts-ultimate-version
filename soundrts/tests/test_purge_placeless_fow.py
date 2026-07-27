"""Placeless models must not linger in FOW views (Ctrl+F2 place-is-None spam)."""

from soundrts.clientgame.game_navigation import (
    _purge_placeless_world_models,
    _world_model_is_placed,
)


class _Model:
    def __init__(self, place, is_inside=False):
        self.place = place
        self.is_inside = is_inside


class _Remembrance:
    def __init__(self, model):
        self.initial_model = model


class _Player:
    def __init__(self):
        self.observed_objects = {}
        self.forgotten = []

    def _forget(self, rem):
        self.forgotten.append(rem)


class _Interface:
    def __init__(self, player, perception, memory):
        self.player = player
        self.perception = perception
        self.memory = memory


def test_world_model_is_placed_allows_inside_without_place():
    assert _world_model_is_placed(_Model(None, is_inside=True))
    assert not _world_model_is_placed(_Model(None))
    assert _world_model_is_placed(_Model(object()))


def test_purge_placeless_removes_from_perception_and_memory():
    square = object()
    live = _Model(square)
    dead = _Model(None)
    rem = _Remembrance(_Model(None))
    player = _Player()
    player.observed_objects = {dead: 1, live: 1}
    interface = _Interface(player, {live, dead}, {rem})

    _purge_placeless_world_models(interface)

    assert dead not in interface.perception
    assert live in interface.perception
    assert dead not in player.observed_objects
    assert player.forgotten == [rem]
