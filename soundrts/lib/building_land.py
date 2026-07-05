"""Building land type registry (defs use ``class building_land`` in rules.txt)."""

from ..definitions import rules


def building_land_type_names():
    return [
        name
        for name in rules.classnames()
        if rules.get(name, "class") == ["building_land"]
    ]


def building_land_types():
    return set(building_land_type_names())


def default_building_land_type():
    val = rules.get("parameters", "default_building_land", None)
    if isinstance(val, list) and val:
        name = str(val[0])
        if name in building_land_types():
            return name
    if "meadow" in building_land_types():
        return "meadow"
    names = building_land_type_names()
    return names[0] if names else "meadow"


_NB_BY_SQUARE_PREFIX = "nb_"
_NB_BY_SQUARE_SUFFIX = "_by_square"
_LEGACY_NB_MEADOWS_BY_SQUARE = "nb_meadows_by_square"


def nb_by_square_land_type(keyword):
    """Return building_land type from ``nb_<type>_by_square`` (not legacy ``nb_meadows_by_square``)."""
    if keyword == _LEGACY_NB_MEADOWS_BY_SQUARE:
        return None
    if not keyword.startswith(_NB_BY_SQUARE_PREFIX) or not keyword.endswith(
        _NB_BY_SQUARE_SUFFIX
    ):
        return None
    inner = keyword[len(_NB_BY_SQUARE_PREFIX) : -len(_NB_BY_SQUARE_SUFFIX)]
    return inner or None


def normalize_building_land_type_name(name):
    if name.isascii():
        return name.lower()
    return name


def is_building_land(obj):
    return getattr(obj, "is_a_building_land", False) and not getattr(
        obj, "is_an_exit", False
    )


def building_land_is_a_type(type_name, parent_name):
    """Whether *type_name* is *parent_name* or inherits it via ``is_a``."""
    if not type_name or not parent_name:
        return False
    if type_name == parent_name:
        return True
    if rules.get(type_name, "class") != ["building_land"]:
        return False
    is_a = rules.get(type_name, "is_a", []) or []
    if parent_name in is_a:
        return True
    expanded = rules.get(type_name, "expanded_is_a", []) or []
    return parent_name in expanded


def building_land_class(type_name=None):
    from ..worldresource import BuildingLand

    if type_name is None:
        type_name = default_building_land_type()
    cls = rules.unit_class(type_name)
    if cls is not None and rules.get(type_name, "class") == ["building_land"]:
        return cls
    fallback = rules.unit_class(default_building_land_type())
    if fallback is not None:
        return fallback
    return BuildingLand


def create_building_land(place, x=None, y=None, type_name=None):
    if type_name is None:
        world = getattr(place, "world", None)
        type_name = getattr(world, "building_land", None) or default_building_land_type()
    cls = building_land_class(type_name)
    if x is not None and y is not None:
        return cls(place, x, y)
    return cls(place)


def recreate_building_land(place, x, y, consumed=None):
    type_name = getattr(consumed, "type_name", None)
    return create_building_land(place, x, y, type_name=type_name)
