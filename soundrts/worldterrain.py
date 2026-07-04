"""Rules metadata for ``class terrain`` definitions (not a map entity)."""


class TerrainRules:
    is_dynamic = 1
    is_high_ground = 0
    is_water = 0
    is_ground = 1
    is_air = 1
    height = 0
    blocks_path = 0
    passable_units = ()  # unset in rules -> use is_ground/is_air/is_water
    speed = ()  # optional ground/air multipliers, e.g. .5 1
    rmg_terrain = 0
    rmg_border = 0
    rmg_water = 0
    rmg_ford = 0
