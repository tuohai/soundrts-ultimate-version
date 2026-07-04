"""Map editor terrain palette application."""

from .square_terrain_rules import (
    apply_terrain_map_flags,
    is_terrain_def,
    resolve_square_type_name,
    terrain_blocks_path,
    terrain_is_dynamic,
)


def apply_palette_to_square(square, palette):
    """Apply one ``editor_palette.txt`` entry to a whole square."""
    style = palette.get("style")

    square.ensure_resources("goldmine", *palette["goldmines"])
    square.ensure_resources("wood", *palette["woods"])
    square.ensure_meadows(palette["meadows"])

    if style and is_terrain_def(style):
        apply_terrain_map_flags(square, style)

    square.is_water = palette["water"]
    square.is_ground = palette["ground"]
    square.is_air = palette["air"]
    square.high_ground = palette["high_ground"]

    if style and is_terrain_def(style):
        if terrain_is_dynamic(style):
            square.fixed_terrain = False
            square.type_name = ""
            square.update_terrain()
            if not resolve_square_type_name(square):
                square.fixed_terrain = True
                square.type_name = style
        else:
            square.fixed_terrain = True
            square.type_name = style
    else:
        square.fixed_terrain = False
        square.type_name = ""
        square.update_terrain()

    square.terrain_speed = palette["speed"]
    square.terrain_cover = palette["cover"]

    type_name = resolve_square_type_name(square)
    if terrain_blocks_path(type_name):
        for neighbor in square.strict_neighbors:
            if terrain_blocks_path(neighbor.type_name):
                square.ensure_blocked_path(neighbor)
            else:
                square.ensure_free_path(neighbor)
    else:
        for neighbor in square.strict_neighbors:
            if (
                square.is_ground
                and neighbor.is_ground
                and square.high_ground == neighbor.high_ground
            ):
                square.ensure_path(neighbor)
            else:
                square.ensure_nopath(neighbor)

    return type_name or style
