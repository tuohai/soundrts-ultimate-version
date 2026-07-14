"""is_very_dangerous must tolerate Inside places (transport/building interiors)."""
from types import SimpleNamespace

from soundrts.worldplayerbase.combat import CombatMixin
from soundrts.worldroom import Square


class _Player(CombatMixin):
    def __init__(self):
        self._enemy_menace = {}
        self._enemy_presence = []


def test_is_very_dangerous_with_inside_does_not_raise():
    player = _Player()
    outside = Square.__new__(Square)
    player._enemy_menace[outside] = 10
    player._enemy_presence = [outside]
    inside = SimpleNamespace(is_inside_place=True, outside=outside)

    # Must not AttributeError on missing other_side
    assert player.is_very_dangerous(inside) is True

    safe_outside = Square.__new__(Square)
    safe_inside = SimpleNamespace(is_inside_place=True, outside=safe_outside)
    assert player.is_very_dangerous(safe_inside) is False


def test_is_very_dangerous_none_and_unknown():
    player = _Player()
    assert player.is_very_dangerous(None) is False
    assert player.is_very_dangerous(SimpleNamespace()) is False


def test_exit_is_dangerous_without_other_side():
    player = _Player()
    assert player.exit_is_dangerous(SimpleNamespace()) is False
    assert player.exit_is_dangerous(SimpleNamespace(other_side=None)) is False
