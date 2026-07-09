"""Tests for vanilla layered battle shout audio."""

from types import SimpleNamespace

from soundrts.clientgameentity.battle_shout_audio import (
    SHOUT_COOLDOWN_GLOBAL_MS,
    battle_qualifies_for_shouts,
    clash_unit_count,
    mark_battle_shout_played,
    scaled_shout_burst,
    shout_bg_burst_cap,
    try_battle_shout_gates,
)


def test_battle_qualifies_for_skirmish():
    assert not battle_qualifies_for_shouts(4, 4)
    assert battle_qualifies_for_shouts(5, 1)
    assert battle_qualifies_for_shouts(2, 8)


def test_shout_burst_nonzero_for_skirmish():
    assert scaled_shout_burst(10, "shout_unit") >= 1
    assert shout_bg_burst_cap(10) >= 1


def test_shout_gates():
    place = object()
    interface = SimpleNamespace(_last_global_battle_shout_ms=0, _battle_shout_place_times={})
    t0 = 100_000
    assert try_battle_shout_gates(interface, place, t0)
    mark_battle_shout_played(interface, place, t0)
    assert not try_battle_shout_gates(interface, place, t0 + 1000)
    assert try_battle_shout_gates(interface, place, t0 + SHOUT_COOLDOWN_GLOBAL_MS + 1)


def test_should_play_battle_shout_five_units():
    from soundrts.clientgameentity import EntityView

    place = object()
    p1, p2 = object(), object()

    def _unit(player):
        model = SimpleNamespace(
            troop_size=1,
            hp=100,
            hp_max=100,
            menace=1,
            place=place,
            player=player,
            type_name="footman",
        )
        return model

    units = []
    for i in range(5):
        view = EntityView.__new__(EntityView)
        view.model = _unit(p1)
        units.append(view)
    attacker = EntityView.__new__(EntityView)
    attacker.model = _unit(p2)
    defender = units[0]
    defender.interface = SimpleNamespace(
        dobjets={i: units[i] for i in range(5)} | {5: attacker},
        _last_global_battle_shout_ms=0,
        _battle_shout_place_times={},
    )
    attacker.interface = defender.interface
    for u in units:
        u.interface = defender.interface
    assert defender._should_play_battle_shout(5, 100_000) == 1


def test_clash_unit_count():
    place = object()
    p1, p2 = object(), object()

    def _view(i, player):
        model = SimpleNamespace(menace=1, place=place, player=player)
        return SimpleNamespace(id=i, place=place, player=player, model=model)

    interface = SimpleNamespace(
        dobjets={0: _view(0, p1), 1: _view(1, p1), 2: _view(2, p2)}
    )
    assert clash_unit_count(interface.dobjets[0], interface.dobjets[2], interface) == 3
