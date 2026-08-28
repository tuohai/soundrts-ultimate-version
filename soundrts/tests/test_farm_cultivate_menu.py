"""Farm auto-cultivate command menu: only stop while auto mode is active."""

import types

from soundrts.worldorders.production import AutoCultivateOrder, StopCultivateOrder


def _farm(**overrides):
    farm = types.SimpleNamespace(
        auto_cultivate=1,
        manual_cultivate=0,
        is_gather=1,
        is_producing=False,
        resource_volume_max=50,
        resource_qty=25,
        orders=[],
        current_production_mode=None,
    )
    for key, value in overrides.items():
        setattr(farm, key, value)
    return farm


def test_auto_cultivate_start_hidden_while_auto_mode_active():
    farm = _farm(current_production_mode="auto")
    assert AutoCultivateOrder.is_allowed(farm) is False
    assert StopCultivateOrder.is_allowed(farm) is True


def test_auto_cultivate_start_shown_when_not_yet_in_auto_mode():
    farm = _farm(current_production_mode=None)
    assert AutoCultivateOrder.is_allowed(farm) is True
    assert StopCultivateOrder.is_allowed(farm) is False


def test_auto_cultivate_start_shown_after_user_stopped():
    farm = _farm(current_production_mode=None, _user_manually_stopped=True)
    assert AutoCultivateOrder.is_allowed(farm) is True
    assert StopCultivateOrder.is_allowed(farm) is False
