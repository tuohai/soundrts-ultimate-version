"""Sub-cell terrain within a map square (e.g. high ground on a1/2,2 only).

The grid size is defined per map by ``subcell_precision`` (default 3, range 2–20),
using the same N×N subdivision as F8 zoom mode when zoom precision matches.
"""

import re

DEFAULT_SUBCELL_PRECISION = 3
MIN_SUBCELL_PRECISION = 2
MAX_SUBCELL_PRECISION = 20

_SUBCELL_SUFFIX_RE = re.compile(r"^(.+)/(\d+)\s*,\s*(\d+)$")


def parse_location_token(token, max_precision=MAX_SUBCELL_PRECISION):
    """Parse ``square`` or ``square/sub_x,sub_y`` (sub coords are 1-based).

    Returns ``(square_key, subcell_or_none)`` where subcell is ``(cx, cy)`` 0-based.
    Coordinates are validated against *max_precision* (full allowed range at parse time).
    """
    if not isinstance(token, str):
        return token, None
    t = token.strip()
    m = _SUBCELL_SUFFIX_RE.match(t)
    if not m:
        return t, None
    square_key = m.group(1).strip()
    cx = int(m.group(2)) - 1
    cy = int(m.group(3)) - 1
    if cx < 0 or cy < 0 or cx >= max_precision or cy >= max_precision:
        raise ValueError(
            "sub-cell coordinates must be 1..%d, got %s"
            % (max_precision, m.group(0).split("/", 1)[1])
        )
    return square_key, (cx, cy)


def subcell_index(place, x, y, precision=None):
    """Return 0-based sub-cell index ``(cx, cy)`` for world coords in *place*."""
    if precision is None:
        try:
            precision = place.world.subcell_precision
        except AttributeError:
            precision = DEFAULT_SUBCELL_PRECISION
    xmin = place.xmin
    ymin = place.ymin
    xmax = place.xmax
    ymax = place.ymax
    sub_w = (xmax - xmin) / precision
    sub_h = (ymax - ymin) / precision
    if sub_w <= 0 or sub_h <= 0:
        return 0, 0
    cx = int((x - xmin) // sub_w)
    cy = int((y - ymin) // sub_h)
    cx = min(max(cx, 0), precision - 1)
    cy = min(max(cy, 0), precision - 1)
    return cx, cy


def subcell_center(place, cx, cy, precision=None):
    """World coords of the center of sub-cell ``(cx, cy)`` (0-based)."""
    if precision is None:
        try:
            precision = place.world.subcell_precision
        except AttributeError:
            precision = DEFAULT_SUBCELL_PRECISION
    sub_w = (place.xmax - place.xmin) / precision
    sub_h = (place.ymax - place.ymin) / precision
    x = place.xmin + (cx + 0.5) * sub_w
    y = place.ymin + (cy + 0.5) * sub_h
    return int(x), int(y)


def format_subcell_suffix(cx, cy):
    """Format 0-based sub-cell as map suffix ``/x,y`` (1-based)."""
    return "/%d,%d" % (cx + 1, cy + 1)


def zoom_subcell_index(zoom):
    """Map RPG zoom cursor to 0-based sub-cell index using the square's precision."""
    place = zoom.parent.place
    precision = getattr(place.world, "subcell_precision", DEFAULT_SUBCELL_PRECISION)
    rel_x = (zoom.sub_x + zoom.half_precision + 0.5) / zoom.precision
    rel_y = (zoom.sub_y + zoom.half_precision + 0.5) / zoom.precision
    cx = int(rel_x * precision)
    cy = int(rel_y * precision)
    cx = min(max(cx, 0), precision - 1)
    cy = min(max(cy, 0), precision - 1)
    return cx, cy


class SubCellOverlay:
    """Per-square overrides for terrain properties on the map sub-grid."""

    __slots__ = (
        "_high_ground",
        "_type_name",
        "_terrain_speed",
        "_terrain_cover",
        "_is_water",
        "_is_ground",
        "_is_air",
    )

    def __init__(self):
        self._high_ground = {}
        self._type_name = {}
        self._terrain_speed = {}
        self._terrain_cover = {}
        self._is_water = {}
        self._is_ground = {}
        self._is_air = {}

    def has_any(self):
        return bool(
            self._high_ground
            or self._type_name
            or self._terrain_speed
            or self._terrain_cover
            or self._is_water
            or self._is_ground
            or self._is_air
        )

    def _cell(self, square, x, y):
        return subcell_index(square, x, y)

    def set_high_ground(self, cx, cy, value=True):
        self._high_ground[(cx, cy)] = bool(value)

    def set_type_name(self, cx, cy, value):
        self._type_name[(cx, cy)] = value

    def set_terrain_speed(self, cx, cy, value):
        self._terrain_speed[(cx, cy)] = value

    def set_terrain_cover(self, cx, cy, value):
        self._terrain_cover[(cx, cy)] = value

    def set_is_water(self, cx, cy, value=True):
        self._is_water[(cx, cy)] = bool(value)

    def set_is_ground(self, cx, cy, value):
        self._is_ground[(cx, cy)] = bool(value)

    def set_is_air(self, cx, cy, value):
        self._is_air[(cx, cy)] = bool(value)

    def apply_palette(self, palette, cx, cy):
        """Apply an editor palette entry to one sub-cell."""
        if palette.get("style"):
            self.set_type_name(cx, cy, palette["style"])
        self.set_is_water(cx, cy, palette.get("water", False))
        self.set_is_ground(cx, cy, palette.get("ground", True))
        self.set_is_air(cx, cy, palette.get("air", True))
        self.set_high_ground(cx, cy, palette.get("high_ground", False))
        if "speed" in palette:
            self.set_terrain_speed(cx, cy, palette["speed"])
        if "cover" in palette:
            self.set_terrain_cover(cx, cy, palette["cover"])

    def high_ground_at(self, square, x, y):
        mapping = self._high_ground
        if not mapping:
            return square.high_ground
        cx, cy = self._cell(square, x, y)
        if (cx, cy) in mapping:
            return mapping[(cx, cy)]
        return square.high_ground

    def type_name_at(self, square, x, y):
        mapping = self._type_name
        if not mapping:
            return square.type_name
        cx, cy = self._cell(square, x, y)
        if (cx, cy) in mapping:
            return mapping[(cx, cy)]
        return square.type_name

    def terrain_speed_at(self, square, x, y):
        mapping = self._terrain_speed
        if not mapping:
            return square.terrain_speed
        cx, cy = self._cell(square, x, y)
        if (cx, cy) in mapping:
            return mapping[(cx, cy)]
        return square.terrain_speed

    def terrain_cover_at(self, square, x, y):
        mapping = self._terrain_cover
        if not mapping:
            return square.terrain_cover
        cx, cy = self._cell(square, x, y)
        if (cx, cy) in mapping:
            return mapping[(cx, cy)]
        return square.terrain_cover

    def is_water_at(self, square, x, y):
        mapping = self._is_water
        if not mapping:
            return square.is_water
        cx, cy = self._cell(square, x, y)
        if (cx, cy) in mapping:
            return mapping[(cx, cy)]
        return square.is_water

    def is_ground_at(self, square, x, y):
        mapping = self._is_ground
        if not mapping:
            return square.is_ground
        cx, cy = self._cell(square, x, y)
        if (cx, cy) in mapping:
            return mapping[(cx, cy)]
        return square.is_ground

    def is_air_at(self, square, x, y):
        mapping = self._is_air
        if not mapping:
            return square.is_air
        cx, cy = self._cell(square, x, y)
        if (cx, cy) in mapping:
            return mapping[(cx, cy)]
        return square.is_air

    def iter_high_ground(self):
        for cell, value in self._high_ground.items():
            yield cell, value

    def iter_type_names(self):
        for cell, value in self._type_name.items():
            yield cell, value

    def iter_terrain_speeds(self):
        for cell, value in self._terrain_speed.items():
            yield cell, value

    def iter_terrain_covers(self):
        for cell, value in self._terrain_cover.items():
            yield cell, value

    def iter_is_water(self):
        for cell, value in self._is_water.items():
            yield cell, value

    def iter_is_ground(self):
        for cell, value in self._is_ground.items():
            yield cell, value

    def iter_is_air(self):
        for cell, value in self._is_air.items():
            yield cell, value
