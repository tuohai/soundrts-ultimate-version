"""验证地面物品进入感知时会触发 scout_info 播报（与资源点一致）。"""

from pathlib import Path


def _source(*path_parts):
    return (Path(__file__).resolve().parents[1].joinpath(*path_parts)).read_text(
        encoding="utf-8"
    )


def test_scout_info_tracks_ground_items():
    src = _source("clientgame", "game_navigation.py")
    assert "def _is_ground_item(m):" in src
    assert 'getattr(m, "default_order", None) == "pickup"' in src
    assert "interface._known_item_ids" in src


def test_game_interface_initializes_known_item_ids():
    src = _source("clientgame", "game_interface_base.py")
    assert "self._known_item_ids = set()" in src


def test_place_summary_includes_ground_items():
    src = _source("clientgame", "game_unit_control.py")
    assert 'getattr(obj.model, "default_order", None) == "pickup"' in src


class _StubPlace:
    def __init__(self, name="b3"):
        self.name = name


class _StubInterface:
    def __init__(self):
        self._known_resource_places = set()
        self._known_item_ids = set()


def _is_ground_item(m):
    return (
        getattr(m, "default_order", None) == "pickup"
        and getattr(m, "player", None) is None
    )


def _must_report_resource(interface, m):
    place = getattr(m, "place", None)
    if place is None:
        return False
    resource_type = getattr(m, "resource_type", None)
    if resource_type is not None and place not in interface._known_resource_places:
        interface._known_resource_places.add(place)
        return True
    if _is_ground_item(m) and m.id not in interface._known_item_ids:
        interface._known_item_ids.add(m.id)
        return True
    return False


class _StubModel:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


def test_must_report_resource_announces_new_ground_item():
    interface = _StubInterface()
    place = _StubPlace()
    item = _StubModel(id=42, place=place, default_order="pickup", player=None)

    assert _must_report_resource(interface, item) is True
    assert place in interface._known_resource_places or 42 in interface._known_item_ids


def test_must_report_resource_skips_already_known_item():
    interface = _StubInterface()
    place = _StubPlace()
    item = _StubModel(id=42, place=place, default_order="pickup", player=None)

    assert _must_report_resource(interface, item) is True
    assert _must_report_resource(interface, item) is False


def test_must_report_resource_announces_each_new_item_at_same_place():
    interface = _StubInterface()
    place = _StubPlace()
    health = _StubModel(
        id=1, place=place, default_order="pickup", player=None, type_name="health_potion"
    )
    mana = _StubModel(
        id=2, place=place, default_order="pickup", player=None, type_name="mana_potion"
    )

    assert _must_report_resource(interface, health) is True
    assert _must_report_resource(interface, mana) is True


def test_must_report_resource_skips_inventory_item_with_owner():
    interface = _StubInterface()
    place = _StubPlace()
    owned = _StubModel(
        id=3, place=place, default_order="pickup", player=object()
    )

    assert _must_report_resource(interface, owned) is False


def test_must_report_resource_skips_missing_place():
    interface = _StubInterface()
    item = _StubModel(id=7, place=None, default_order="pickup", player=None)
    deposit = _StubModel(id=8, place=None, resource_type="resource1")

    assert _must_report_resource(interface, item) is False
    assert _must_report_resource(interface, deposit) is False


def test_scout_info_if_needed_skips_none_place():
    from types import SimpleNamespace

    from soundrts.clientgame.game_navigation import scout_info_if_needed

    spoken = []

    class Place:
        title = ["a1"]

    interface = SimpleNamespace(
        scout_info={None, Place()},
        previous_scout_info=None,
    )

    import soundrts.clientgame.game_navigation as nav
    import soundrts.config as config
    import soundrts.clientgame.game_unit_control as uc

    orig_summary = uc.place_summary
    orig_info = nav.voice.info
    orig_verbosity = config.verbosity
    try:
        config.verbosity = "scout_info"
        uc.place_summary = lambda *_a, **_k: ["goldmine"]
        nav.voice.info = lambda msg, *a, **k: spoken.append(msg)
        scout_info_if_needed(interface)
    finally:
        uc.place_summary = orig_summary
        nav.voice.info = orig_info
        config.verbosity = orig_verbosity

    assert len(spoken) == 1
    assert interface.scout_info == set()
