"""Procedural random map generator for SoundRTS.

Generates valid map definition text from template parameters (size, players,
monster strength, resource layout, map template, terrain, team layout, water).
Maps load through the normal ``Map`` / ``World.load_and_build_map`` pipeline.
"""
from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set, Tuple

from .mapfile import Map

from . import msgparts as mp
from .lib.msgs import nb2msg
from .rmg_templates import (
    RmgTemplateSpec,
    all_template_names,
    get_template_spec,
    normalize_terrain_mode,
    reload_custom_templates,
    resolve_random_terrain,
    rmg_ford_terrain,
    rmg_water_terrain,
    template_monster_presets,
    template_title_voice,
    terrain_speed_line,
    terrain_cover_line,
    terrain_uses_border_style,
)

_TEMPLATE_TITLE = {
    "standard": mp.RMG_TEMPLATE_STANDARD,
    "fast": mp.RMG_TEMPLATE_FAST,
    "macro": mp.RMG_TEMPLATE_MACRO,
    "lanes": mp.RMG_TEMPLATE_LANES,
}

_SIZE_TITLE = {
    "small": mp.RMG_SIZE_SMALL,
    "medium": mp.RMG_SIZE_MEDIUM,
    "large": mp.RMG_SIZE_LARGE,
}

_TREASURE_TITLE = {
    "none": mp.RMG_TREASURE_NONE,
    "low": mp.RMG_TREASURE_LOW,
    "high": mp.RMG_TREASURE_HIGH,
}

_WATER_TITLE = {
    "none": mp.RMG_NO_WATER,
    "lake": mp.RMG_LAKE,
    "river": mp.RMG_RIVER,
}

_SHARE_ABBR = {
    "template": {"standard": "s", "fast": "f", "macro": "m", "lanes": "l"},
    "size": {"small": "s", "medium": "m", "large": "l"},
    "monster_strength": {"weak": "w", "medium": "med", "strong": "s"},
    "resource_layout": {"balanced": "b", "clustered": "c"},
    "terrain": {"random": "r", "grass": "g", "marsh": "a", "mountain": "t"},
    "team_mode": {"ffa": "f", "teams_2v2": "t", "one_vs_many": "o"},
    "water": {"none": "n", "lake": "l", "river": "v"},
    "treasure": {"none": "n", "low": "lo", "high": "hi"},
    "victory_mode": {
        "conquest": "c",
        "economic": "e",
        "exploration": "x",
        "survival": "s",
    },
}

SIZE_PRESETS = {
    "small": (7, 7),
    "medium": (11, 11),
    "large": (15, 15),
}

LANE_COLUMN_PRESETS = {
    "small": 9,
    "medium": 15,
    "large": 21,
}

LANE_LINES = 3
# Buildable meadows placed on each player start (lanes use nb_meadows_by_square 0).
LANE_START_MEADOWS = 4

MONSTER_PRESETS = {
    "weak": [(2, "footman")],
    "medium": [(4, "footman"), (2, "archer")],
    "strong": [(6, "footman"), (4, "archer"), (1, "knight")],
}

TEMPLATES = ("standard", "fast", "macro", "lanes")

TERRAIN_BASE_MODES = ("random", "grass")


def terrain_choices_for_template(template: str) -> Tuple[str, ...]:
    _refresh_custom_templates()
    from .rmg_templates import terrain_modes_for_template

    return terrain_modes_for_template(template, _builtin_rmg_specs())


# Backward-compatible alias used by tests and share-code abbreviations.
TERRAIN_MODES = TERRAIN_BASE_MODES + ("marsh", "mountain")

TEAM_MODES = ("ffa", "teams_2v2", "one_vs_many")


def team_modes_for_players(nb_players: int) -> Tuple[str, ...]:
    """Return team-mode choices valid for the given player count."""
    n = max(2, min(4, int(nb_players)))
    if n < 3:
        return ("ffa",)
    if n == 3:
        return ("ffa", "one_vs_many")
    return ("ffa", "teams_2v2", "one_vs_many")

WATER_MODES = ("none", "lake", "river")

TREASURE_MODES = ("none", "low", "high")

VICTORY_MODES = ("conquest", "economic", "exploration", "survival")

_OBJECTIVE_VICTORY_MODE = {
    145: "conquest",
    5430: "exploration",
    5435: "economic",
    5436: "survival",
}


def _append_random_map_meta_lines(lines_out: List[str], cfg: RandomMapConfig) -> None:
    """Embed skirmish metadata for achievements and other post-game logic."""
    lines_out.append("random_map 1")
    mode = cfg.victory_mode if cfg.victory_mode in VICTORY_MODES else "conquest"
    lines_out.append(f"victory_mode {mode}")


def parse_random_map_meta(definition: str) -> Tuple[bool, str]:
    """Return ``(is_random_map, victory_mode)`` parsed from map definition text."""
    if not definition:
        return False, "conquest"
    is_random_map = False
    victory_mode = "conquest"
    for line in definition.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(";"):
            continue
        words = stripped.split()
        if words[0] == "random_map":
            if len(words) >= 2 and words[1] in ("0", "false", "no"):
                is_random_map = False
            else:
                is_random_map = True
        elif words[0] == "victory_mode" and len(words) >= 2:
            mode = words[1].lower()
            if mode in VICTORY_MODES:
                victory_mode = mode
        elif words[0] == "title" and len(words) >= 2 and words[1] == "random_map":
            is_random_map = True
        elif words[0] == "objective" and len(words) >= 2:
            try:
                objective_id = int(words[1])
            except ValueError:
                continue
            mode = _OBJECTIVE_VICTORY_MODE.get(objective_id)
            if mode is not None:
                victory_mode = mode
    return is_random_map, victory_mode


_VICTORY_TITLE = {
    "conquest": mp.RMG_VICTORY_CONQUEST,
    "economic": mp.RMG_VICTORY_ECONOMIC,
    "exploration": mp.RMG_VICTORY_EXPLORATION,
    "survival": mp.RMG_VICTORY_SURVIVAL,
}

_SHARE_CODE_PREFIX = "RMG1"
_SHARE_CODE_PREFIX_V2 = "RMG2"

_RESOURCE_TIERS_BALANCED = [(400, 400), (200, 200), (150, 150)]
_RESOURCE_TIERS_CLUSTERED = [(800, 800), (600, 600), (300, 300)]


@dataclass(frozen=True)
class _TemplateSpec:
    layout: str  # grid | lanes
    starting_units: str
    starting_resources: Tuple[int, int]
    start_mine_qty: int
    tiers_balanced: Tuple[Tuple[int, int], ...]
    tiers_clustered: Tuple[Tuple[int, int], ...]
    population_limit: int
    meadows_per_square: int
    creep_multiplier: float
    center_bridges: bool
    terrain_modes: Tuple[str, ...] = ()  # empty = auto from rules (see rmg_templates)
    water_terrain: str = "lake"
    ford_terrain: str = "ford"
    skip_terrain_menu: bool = False
    skip_water_menu: bool = False


def _template_spec_to_rmg(spec: _TemplateSpec) -> RmgTemplateSpec:
    return RmgTemplateSpec(
        layout=spec.layout,
        starting_units=spec.starting_units,
        starting_resources=spec.starting_resources,
        start_mine_qty=spec.start_mine_qty,
        tiers_balanced=spec.tiers_balanced,
        tiers_clustered=spec.tiers_clustered,
        population_limit=spec.population_limit,
        meadows_per_square=spec.meadows_per_square,
        creep_multiplier=spec.creep_multiplier,
        center_bridges=spec.center_bridges,
        terrain_modes=spec.terrain_modes,
        water_terrain=spec.water_terrain,
        ford_terrain=spec.ford_terrain,
        skip_terrain_menu=spec.skip_terrain_menu,
        skip_water_menu=spec.skip_water_menu,
    )


def _builtin_rmg_specs() -> Dict[str, RmgTemplateSpec]:
    return {name: _template_spec_to_rmg(spec) for name, spec in _TEMPLATE_SPECS.items()}


def _all_templates() -> Tuple[str, ...]:
    return all_template_names(TEMPLATES)


def _refresh_custom_templates() -> None:
    reload_custom_templates(_builtin_rmg_specs())


_TEMPLATE_SPECS: Dict[str, _TemplateSpec] = {
    "standard": _TemplateSpec(
        layout="grid",
        starting_units="townhall 4 house 10 peasant 1 scouttower",
        starting_resources=(100, 100),
        start_mine_qty=1000,
        tiers_balanced=tuple(_RESOURCE_TIERS_BALANCED),
        tiers_clustered=tuple(_RESOURCE_TIERS_CLUSTERED),
        population_limit=4000,
        meadows_per_square=4,
        creep_multiplier=1.0,
        center_bridges=False,
    ),
    "fast": _TemplateSpec(
        layout="grid",
        starting_units="townhall 3 house 8 peasant 12 footman",
        starting_resources=(120, 120),
        start_mine_qty=800,
        tiers_balanced=((500, 500), (350, 350), (250, 250)),
        tiers_clustered=((1000, 1000), (700, 700), (400, 400)),
        population_limit=3500,
        meadows_per_square=3,
        creep_multiplier=1.25,
        center_bridges=True,
    ),
    "macro": _TemplateSpec(
        layout="grid",
        starting_units="townhall 5 house 12 peasant 2 scouttower",
        starting_resources=(200, 200),
        start_mine_qty=1500,
        tiers_balanced=((600, 600), (400, 400), (300, 300), (200, 200)),
        tiers_clustered=((900, 900), (700, 700), (500, 500)),
        population_limit=8000,
        meadows_per_square=6,
        creep_multiplier=0.75,
        center_bridges=False,
    ),
    "lanes": _TemplateSpec(
        layout="lanes",
        starting_units="townhall 3 house 8 peasant 8 footman",
        starting_resources=(120, 120),
        start_mine_qty=750,
        tiers_balanced=((350, 350), (200, 200)),
        tiers_clustered=((600, 600), (400, 400)),
        population_limit=3500,
        meadows_per_square=0,
        creep_multiplier=1.1,
        center_bridges=False,
        skip_terrain_menu=True,
        skip_water_menu=True,
    ),
}


_refresh_custom_templates()


def refresh_rmg_templates() -> None:
    """Reload custom templates from cfg/randommap, res/randommap, and active mods."""
    _refresh_custom_templates()


def get_rmg_template_spec(template_name: str) -> RmgTemplateSpec:
    refresh_rmg_templates()
    return get_template_spec(template_name, _builtin_rmg_specs())


@dataclass
class RandomMapConfig:
    size: str = "medium"
    nb_players: int = 2
    monster_strength: str = "medium"
    resource_layout: str = "balanced"
    template: str = "standard"
    terrain: str = "random"
    team_mode: str = "ffa"
    water: str = "none"
    treasure: str = "none"
    victory_mode: str = "conquest"
    seed: int | None = None

    def resolved_seed(self) -> int:
        if self.seed is not None and int(self.seed) > 0:
            return int(self.seed) % 100000
        return random.randint(0, 10000)

    def normalized(self) -> RandomMapConfig:
        _refresh_custom_templates()
        size = self.size if self.size in SIZE_PRESETS else "medium"
        nb_players = max(2, min(4, int(self.nb_players)))
        monster = self.monster_strength if self.monster_strength in MONSTER_PRESETS else "medium"
        layout = self.resource_layout if self.resource_layout in ("balanced", "clustered") else "balanced"
        template = self.template if self.template in _all_templates() else "standard"
        terrain = normalize_terrain_mode(self.terrain, template, _builtin_rmg_specs())
        team_mode = self.team_mode if self.team_mode in TEAM_MODES else "ffa"
        allowed = team_modes_for_players(nb_players)
        if team_mode not in allowed:
            team_mode = "ffa"
        water = self.water if self.water in WATER_MODES else "none"
        spec = get_template_spec(template, _builtin_rmg_specs())
        if spec.layout == "lanes" or spec.skip_water_menu:
            water = "none"
        treasure = self.treasure if self.treasure in TREASURE_MODES else "none"
        victory_mode = (
            self.victory_mode if self.victory_mode in VICTORY_MODES else "conquest"
        )
        seed = self.seed
        if seed is not None and int(seed) <= 0:
            seed = None
        return RandomMapConfig(
            size=size,
            nb_players=nb_players,
            monster_strength=monster,
            resource_layout=layout,
            template=template,
            terrain=terrain,
            team_mode=team_mode,
            water=water,
            treasure=treasure,
            victory_mode=victory_mode,
            seed=seed,
        )


def _sq(x: int, y: int) -> str:
    return f"{x},{y}"


def _player_starts(cols: int, lines: int, nb_players: int) -> List[Tuple[int, int]]:
    margin = 2
    corners = [
        (margin, margin),
        (cols - margin + 1, margin),
        (margin, lines - margin + 1),
        (cols - margin + 1, lines - margin + 1),
    ]
    if nb_players == 2:
        return [corners[0], corners[3]]
    if nb_players == 3:
        return [corners[0], corners[1], (cols // 2 + 1, lines - margin + 1)]
    return corners


def _lane_starts(cols: int, nb_players: int) -> List[Tuple[int, int]]:
    if nb_players == 2:
        return [(1, 2), (cols, 2)]
    if nb_players == 3:
        return [(1, 2), (cols // 2 + 1, 2), (cols, 2)]
    inset = max(2, cols // 7)
    return [
        (inset, 1),
        (cols - inset + 1, 1),
        (inset, LANE_LINES),
        (cols - inset + 1, LANE_LINES),
    ]


def _mirror(x: int, y: int, cols: int, lines: int) -> Tuple[int, int]:
    return cols + 1 - x, lines + 1 - y


def _symmetric_pairs(
    rng: random.Random,
    cols: int,
    lines: int,
    starts: Sequence[Tuple[int, int]],
    count: int,
) -> List[Tuple[int, int]]:
    blocked = set(starts)
    for sx, sy in starts:
        blocked.add(_mirror(sx, sy, cols, lines))
    margin = 2
    candidates = [
        (x, y)
        for x in range(margin, cols - margin + 2)
        for y in range(margin, lines - margin + 2)
        if (x, y) not in blocked
    ]
    rng.shuffle(candidates)
    pairs: List[Tuple[int, int]] = []
    used = set(blocked)
    for x, y in candidates:
        mx, my = _mirror(x, y, cols, lines)
        if (x, y) in used or (mx, my) in used:
            continue
        if (x, y) <= (mx, my):
            pairs.append((x, y))
            used.add((x, y))
            used.add((mx, my))
        if len(pairs) >= count:
            break
    return pairs


def _cluster_squares(cols: int, lines: int, starts: Sequence[Tuple[int, int]], count: int) -> List[Tuple[int, int]]:
    cx, cy = cols // 2 + 1, lines // 2 + 1
    blocked = set(starts)
    offsets = [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)]
    squares = []
    for dx, dy in offsets:
        x, y = cx + dx, cy + dy
        if 1 <= x <= cols and 1 <= y <= lines and (x, y) not in blocked:
            squares.append((x, y))
        if len(squares) >= count:
            break
    return squares


def _grid_paths(cols: int, lines: int, water: Set[Tuple[int, int]]) -> Tuple[List[str], List[str]]:
    we: List[str] = []
    for y in range(1, lines + 1):
        for x in range(1, cols):
            if (x, y) not in water and (x + 1, y) not in water:
                we.append(_sq(x, y))
    sn: List[str] = []
    for x in range(1, cols + 1):
        for y in range(1, lines):
            if (x, y) not in water and (x, y + 1) not in water:
                sn.append(_sq(x, y))
    return we, sn


def _lane_paths(
    cols: int,
    starts: Sequence[Tuple[int, int]],
) -> Tuple[List[str], List[str]]:
    """Full horizontal lanes plus vertical links at starts and center crossings."""
    we: List[str] = []
    for y in range(1, LANE_LINES + 1):
        for x in range(1, cols):
            we.append(_sq(x, y))
    sn_cols: Set[int] = {
        max(1, cols // 4),
        max(1, cols // 2),
        min(cols, (3 * cols) // 4),
    }
    for x, _y in starts:
        sn_cols.add(x)
    sn: List[str] = []
    for c in sorted(sn_cols):
        for y in range(1, LANE_LINES):
            sn.append(_sq(c, y))
    return we, sn


def _append_lane_start_meadows(
    lines_out: List[str],
    starts: Sequence[Tuple[int, int]],
) -> None:
    tokens: List[str] = []
    for x, y in starts:
        tokens.extend([_sq(x, y)] * LANE_START_MEADOWS)
    if tokens:
        lines_out.append(f"additional_meadows {' '.join(tokens)}")


def _lake_squares(
    rng: random.Random,
    cols: int,
    lines: int,
    starts: Sequence[Tuple[int, int]],
) -> Set[Tuple[int, int]]:
    if cols < 7 or lines < 7:
        return set()
    blocked = set(starts)
    for sx, sy in starts:
        blocked.add(_mirror(sx, sy, cols, lines))
    cx, cy = cols // 2 + 1, lines // 2 + 1
    radius = 1 if cols <= 9 else 2
    lake = _blob(cx, cy, cols, lines, radius, blocked)
    # Keep a bridge lane on the center row.
    for x in range(max(1, cx - 1), min(cols, cx + 1) + 1):
        lake.discard((x, cy))
    return lake


def _river_squares(
    cols: int,
    lines: int,
    starts: Sequence[Tuple[int, int]],
) -> Set[Tuple[int, int]]:
    if cols < 7 or lines < 7:
        return set()
    blocked = set(starts)
    for sx, sy in starts:
        blocked.add(_mirror(sx, sy, cols, lines))
    cx, cy = cols // 2 + 1, lines // 2 + 1
    river_cols = [cx]
    if cols >= 11:
        river_cols = [cx - 1, cx]
    cells: Set[Tuple[int, int]] = set()
    for x in river_cols:
        for y in range(2, lines):
            if (x, y) not in blocked:
                cells.add((x, y))
    for x in river_cols:
        cells.discard((x, cy))
    return cells


def _river_bridge_lines(cols: int, lines: int, water: Set[Tuple[int, int]]) -> List[str]:
    cy = lines // 2 + 1
    out: List[str] = []
    for x in range(1, cols):
        if (x, cy) not in water and (x + 1, cy) not in water:
            out.append(f"west_east_bridges {_sq(x, cy)}")
            break
    return out


def _water_squares_for_cfg(
    cfg: RandomMapConfig,
    rng: random.Random,
    cols: int,
    lines: int,
    starts: Sequence[Tuple[int, int]],
) -> Set[Tuple[int, int]]:
    if cfg.water == "lake":
        return _lake_squares(rng, cols, lines, starts)
    if cfg.water == "river":
        return _river_squares(cols, lines, starts)
    return set()


def _loot_item_types_in_rules_text(text: str) -> List[str]:
    if not text.strip():
        return []
    try:
        from .definitions import Rules, _get_base_classes

        snapshot = Rules()
        snapshot.load(text, base_classes=_get_base_classes())
        return sorted(
            name
            for name in snapshot.classnames()
            if snapshot.get(name, "class") == ["item"]
        )
    except Exception:
        return []


def _loot_item_types() -> List[str]:
    """Pickable items from active mod rules, or base rules when no mod is active."""
    return _loot_item_types_in_rules_text(_wildlife_rules_text())


def _is_truthy_rules_flag(value) -> bool:
    if value in (1, "1", True):
        return True
    if isinstance(value, list) and value:
        return str(value[0]) in ("1", "true", "True")
    return False


_DEFAULT_DEPOSIT_KEYWORDS: Dict[str, str] = {
    "resource1": "goldmines",
    "resource2": "woods",
}
# Base deposits kept only as fallback; not preferred when a mod defines its own.
_FALLBACK_DEPOSIT_NAMES = frozenset({"goldmine", "wood", "food_carcass"})


def _nb_resource_slots() -> int:
    try:
        from .definitions import rules

        return max(1, int(rules.get("parameters", "nb_of_resource_types", 2) or 2))
    except Exception:
        return 2


def _resource_slot_names() -> List[str]:
    return [f"resource{i}" for i in range(1, _nb_resource_slots() + 1)]


def _deposit_map_keyword(resource_slot: str) -> str | None:
    """Return the plural map keyword for one resource slot, if any."""
    try:
        from .definitions import rules

        preferred: str | None = None
        fallback: str | None = None
        for name in rules.classnames():
            if rules.get(name, "class") != ["deposit"]:
                continue
            rt = rules.get(name, "resource_type")
            if isinstance(rt, list):
                rt = rt[0] if rt else None
            if rt != resource_slot:
                continue
            keyword = name + "s"
            if name in _FALLBACK_DEPOSIT_NAMES:
                fallback = keyword
            else:
                preferred = keyword
        default = _DEFAULT_DEPOSIT_KEYWORDS.get(resource_slot)
        return preferred or fallback or default
    except Exception:
        return _DEFAULT_DEPOSIT_KEYWORDS.get(resource_slot)


def _deposit_map_keywords() -> Tuple[str, ...]:
    """Return plural map keywords for every configured resource slot."""
    return tuple(
        kw
        for slot in _resource_slot_names()
        if (kw := _deposit_map_keyword(slot)) is not None
    )


def _mod_rules_file_paths() -> List[Path]:
    try:
        from . import config
    except Exception:
        return []
    paths: List[Path] = []
    for name in (n.strip() for n in config.mods.split(",") if n.strip()):
        for base in (Path("mods"), Path("res/mods")):
            path = base / name / "rules.txt"
            if path.is_file():
                paths.append(path)
                break
    return paths


def _wildlife_rules_text() -> str:
    """Mod rules when mods are active; otherwise base ``res/rules.txt``."""
    mod_paths = _mod_rules_file_paths()
    if mod_paths:
        return "\n".join(path.read_text(encoding="utf-8") for path in mod_paths)
    base_rules = Path("res/rules.txt")
    if base_rules.is_file():
        return base_rules.read_text(encoding="utf-8")
    return ""


def _huntable_animal_types_in_rules_text(text: str) -> List[str]:
    if not text.strip():
        return []
    try:
        from .definitions import Rules, _get_base_classes

        snapshot = Rules()
        snapshot.load(text, base_classes=_get_base_classes())
        return [
            name
            for name in snapshot.classnames()
            if snapshot.get(name, "class") == ["soldier"]
            and _is_truthy_rules_flag(snapshot.get(name, "is_huntable"))
        ]
    except Exception:
        return []


def _huntable_animal_types() -> List[str]:
    return _huntable_animal_types_in_rules_text(_wildlife_rules_text())


def _hunting_available() -> bool:
    """Spawn wildlife only when the active mod rules define huntable animals."""
    return bool(_huntable_animal_types())


def _orchard_available_in_rules_text(text: str) -> bool:
    if not text.strip():
        return False
    try:
        from .definitions import Rules, _get_base_classes

        snapshot = Rules()
        snapshot.load(text, base_classes=_get_base_classes())
        return snapshot.get("orchard", "class") == ["deposit"]
    except Exception:
        return False


def _orchard_available() -> bool:
    """Spawn orchards only when the active mod rules define orchard."""
    return _orchard_available_in_rules_text(_wildlife_rules_text())


def _tier_quantities(tier: Tuple[int, ...], slot_count: int) -> Tuple[int, ...]:
    if slot_count <= 0:
        return ()
    if not tier:
        return (100,) * slot_count
    if len(tier) >= slot_count:
        return tier[:slot_count]
    return tier + (tier[-1],) * (slot_count - len(tier))


def _deposit_spot_qty(keyword: str, tier_qty: int) -> int:
    """Build-site deposits (no worker extraction) use qty 1; others use tier quantity."""
    singular = keyword[:-1] if keyword.endswith("s") else keyword
    try:
        from .definitions import rules

        if rules.get(singular, "class") == ["deposit"]:
            has_extraction = bool(rules.get(singular, "extraction_time")) or bool(
                rules.get(singular, "extraction_qty")
            )
            if not has_extraction:
                return 1
    except Exception:
        if singular == "geyser":
            return 1
    return tier_qty


def _pad_starting_resources(values: Sequence[int]) -> List[int]:
    nb = _nb_resource_slots()
    padded = list(values)
    while len(padded) < nb:
        padded.append(padded[-1] if padded else 0)
    return padded[:nb]


def _append_hunting(
    lines_out: List[str],
    cfg: RandomMapConfig,
    rng: random.Random,
    cols: int,
    lines: int,
    starts: Sequence[Tuple[int, int]],
) -> None:
    if not _hunting_available():
        return
    animals = _huntable_animal_types()
    if not animals:
        return
    spots = _symmetric_pairs(rng, cols, lines, starts, 2)
    food_qty = 200 if cfg.treasure == "high" else 120
    for x, y in spots:
        for sx, sy in ((x, y), _mirror(x, y, cols, lines)):
            sq = _sq(sx, sy)
            if _orchard_available() and rng.random() < 0.4:
                lines_out.append(f"orchard {food_qty} {sq}")
            animal = rng.choice(animals)
            count = rng.randint(2, 4)
            lines_out.append(f"computer_only 0 0 neutral {sq} {count} {animal}")


def _append_treasure(
    lines_out: List[str],
    cfg: RandomMapConfig,
    rng: random.Random,
    cols: int,
    lines: int,
    starts: Sequence[Tuple[int, int]],
) -> None:
    if cfg.treasure == "none":
        return
    spot_count = 1 if cfg.treasure == "low" else 2
    gold_qty = 500 if cfg.treasure == "low" else 900
    spots = _symmetric_pairs(rng, cols, lines, starts, spot_count)
    items = _loot_item_types()
    use_orchard = _orchard_available()
    for x, y in spots:
        for sx, sy in ((x, y), _mirror(x, y, cols, lines)):
            if cfg.treasure == "high" and items and rng.random() < 0.45:
                lines_out.append(f"{rng.choice(items)} {_sq(sx, sy)}")
            elif cfg.treasure == "high" and use_orchard and rng.random() < 0.35:
                lines_out.append(f"orchard {gold_qty} {_sq(sx, sy)}")
            else:
                keywords = _deposit_map_keywords()
                if keywords:
                    lines_out.append(f"{keywords[0]} {gold_qty} {_sq(sx, sy)}")


def _invert_abbr(table: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    return {key: {v: k for k, v in mapping.items()} for key, mapping in table.items()}


_SHARE_REV = _invert_abbr(_SHARE_ABBR)


def _uses_compact_share_code(cfg: RandomMapConfig) -> bool:
    return (
        cfg.template in _SHARE_ABBR["template"]
        and cfg.terrain in _SHARE_ABBR["terrain"]
    )


def encode_share_code(config: RandomMapConfig, seed: int | None = None) -> str:
    cfg = config.normalized()
    seed_val = int(seed if seed is not None else (cfg.seed or 0))
    if _uses_compact_share_code(cfg):
        parts = [
            _SHARE_CODE_PREFIX,
            _SHARE_ABBR["template"][cfg.template],
            _SHARE_ABBR["size"][cfg.size],
            str(cfg.nb_players),
            _SHARE_ABBR["monster_strength"][cfg.monster_strength],
            _SHARE_ABBR["resource_layout"][cfg.resource_layout],
            _SHARE_ABBR["terrain"][cfg.terrain],
            _SHARE_ABBR["team_mode"][cfg.team_mode],
            _SHARE_ABBR["water"][cfg.water],
            _SHARE_ABBR["treasure"][cfg.treasure],
            _SHARE_ABBR["victory_mode"][cfg.victory_mode],
            str(seed_val),
        ]
        return ":".join(parts)
    parts = [
        _SHARE_CODE_PREFIX_V2,
        cfg.template,
        cfg.size,
        str(cfg.nb_players),
        cfg.monster_strength,
        cfg.resource_layout,
        cfg.terrain,
        cfg.team_mode,
        cfg.water,
        cfg.treasure,
        cfg.victory_mode,
        str(seed_val),
    ]
    return ":".join(parts)


def decode_share_code(code: str) -> RandomMapConfig:
    text = code.strip()
    prefix = _SHARE_CODE_PREFIX
    if text.lower().startswith(_SHARE_CODE_PREFIX_V2.lower() + ":"):
        prefix = _SHARE_CODE_PREFIX_V2
        text = text.split(":", 1)[1]
    elif text.lower().startswith(_SHARE_CODE_PREFIX.lower() + ":"):
        text = text.split(":", 1)[1]
    tokens = [t for t in text.replace("/", ":").split(":") if t]
    if prefix == _SHARE_CODE_PREFIX_V2:
        if len(tokens) != 11:
            raise ValueError("invalid RMG share code")
        seed_raw = int(tokens[10])
        return RandomMapConfig(
            template=tokens[0],
            size=tokens[1],
            nb_players=int(tokens[2]),
            monster_strength=tokens[3],
            resource_layout=tokens[4],
            terrain=tokens[5],
            team_mode=tokens[6],
            water=tokens[7],
            treasure=tokens[8],
            victory_mode=tokens[9],
            seed=seed_raw if seed_raw > 0 else None,
        ).normalized()
    if len(tokens) not in (10, 11):
        raise ValueError("invalid RMG share code")
    rev = _SHARE_REV
    if len(tokens) == 10:
        seed_raw = int(tokens[9])
        victory = "conquest"
    else:
        seed_raw = int(tokens[10])
        victory = rev["victory_mode"][tokens[9]]
    return RandomMapConfig(
        template=rev["template"][tokens[0]],
        size=rev["size"][tokens[1]],
        nb_players=int(tokens[2]),
        monster_strength=rev["monster_strength"][tokens[3]],
        resource_layout=rev["resource_layout"][tokens[4]],
        terrain=rev["terrain"][tokens[5]],
        team_mode=rev["team_mode"][tokens[6]],
        water=rev["water"][tokens[7]],
        treasure=rev["treasure"][tokens[8]],
        victory_mode=victory,
        seed=seed_raw if seed_raw > 0 else None,
    ).normalized()


def config_voice_summary(config: RandomMapConfig, seed: int | None = None) -> list:
    cfg = config.normalized()
    parts = menu_title_for_config(cfg)
    parts += _WATER_TITLE[cfg.water]
    if cfg.treasure != "none":
        parts += _TREASURE_TITLE[cfg.treasure]
    if cfg.victory_mode != "conquest":
        parts += _VICTORY_TITLE[cfg.victory_mode]
    if cfg.victory_mode == "economic":
        parts += nb2msg(_economic_goal(cfg)) + [131]
    if seed is not None:
        parts += mp.RMG_SEED + nb2msg(seed)
    return parts


def share_code_voice_msg(share: str) -> list:
    result = []
    for c in share:
        if c == ".":
            result.extend(mp.DOT)
        elif c in "0123456789":
            result.extend(nb2msg(c))
        else:
            result.extend(c)
    return result


def map_generated_voice_msg(config: RandomMapConfig, seed: int) -> list:
    """Voice message for map generation; includes F5/F6 history hint."""
    cfg = config.normalized()
    return (
        mp.RMG_MAP_GENERATED
        + mp.RMG_SEED
        + nb2msg(seed)
        + mp.RMG_SHARE_CODE
        + share_code_voice_msg(encode_share_code(cfg, seed))
        + mp.HISTORY_EXPLANATION
    )


def _chunks(items: Sequence[str], width: int = 16) -> Iterable[str]:
    for i in range(0, len(items), width):
        yield " ".join(items[i : i + width])


def _scaled_creep(strength: str, multiplier: float, template: str) -> List[Tuple[int, str]]:
    presets = template_monster_presets(template, MONSTER_PRESETS)
    result = []
    for qty, unit_type in presets[strength]:
        scaled = max(1, int(round(qty * multiplier)))
        result.append((scaled, unit_type))
    return result


def _blob(
    cx: int,
    cy: int,
    cols: int,
    lines: int,
    radius: int,
    blocked: Set[Tuple[int, int]],
) -> Set[Tuple[int, int]]:
    cells: Set[Tuple[int, int]] = set()
    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            if abs(dx) + abs(dy) > radius:
                continue
            x, y = cx + dx, cy + dy
            if 1 <= x <= cols and 1 <= y <= lines and (x, y) not in blocked:
                cells.add((x, y))
    return cells


def _resolve_terrain_mode(
    rng: random.Random,
    terrain: str,
    template: str,
) -> str:
    if terrain != "random":
        return terrain
    return resolve_random_terrain(rng, template, _builtin_rmg_specs())


def _terrain_lines(
    rng: random.Random,
    cols: int,
    lines: int,
    starts: Sequence[Tuple[int, int]],
    terrain_mode: str,
    water: Set[Tuple[int, int]],
    template: str,
) -> List[str]:
    mode = _resolve_terrain_mode(rng, terrain_mode, template)
    if mode == "grass":
        return []

    blocked = set(starts) | water
    for sx, sy in starts:
        blocked.add(_mirror(sx, sy, cols, lines))
    cx, cy = cols // 2 + 1, lines // 2 + 1
    blocked.add((cx, cy))
    blocked.add(_mirror(cx, cy, cols, lines))

    terrain_cells: Set[Tuple[int, int]] = set()
    if terrain_uses_border_style(mode):
        margin = 1
        for x in range(1, cols + 1):
            for y in range(1, lines + 1):
                if x <= margin or y <= margin or x > cols - margin or y > lines - margin:
                    if (x, y) not in blocked:
                        terrain_cells.add((x, y))
    else:
        patch_count = 2 if cols <= 9 else 3
        seeds = _symmetric_pairs(rng, cols, lines, list(blocked), patch_count)
        for px, py in seeds:
            terrain_cells |= _blob(px, py, cols, lines, 1, blocked)
            mx, my = _mirror(px, py, cols, lines)
            terrain_cells |= _blob(mx, my, cols, lines, 1, blocked)
    if not terrain_cells:
        return []
    tokens = sorted(_sq(x, y) for x, y in terrain_cells)
    out = [f"terrain {mode} {' '.join(tokens)}"]
    speed_line = terrain_speed_line(mode)
    if speed_line:
        out.append(f"{speed_line} {' '.join(tokens)}")
    cover_line = terrain_cover_line(mode)
    if cover_line:
        out.append(f"{cover_line} {' '.join(tokens)}")
    return out


def _water_lines(water: Set[Tuple[int, int]], water_terrain: str) -> List[str]:
    if not water:
        return []
    tokens = sorted(_sq(x, y) for x, y in water)
    return [
        f"water {' '.join(tokens)}",
        f"terrain {water_terrain} {' '.join(tokens)}",
    ]


def _center_bridge_lines(cols: int, lines: int, water: Set[Tuple[int, int]]) -> List[str]:
    cx, cy = cols // 2 + 1, lines // 2 + 1
    out: List[str] = []
    if cx > 1 and (cx - 1, cy) not in water and (cx, cy) not in water:
        out.append(f"west_east_bridges {_sq(cx - 1, cy)}")
    if cy > 1 and (cx, cy - 1) not in water and (cx, cy) not in water:
        out.append(f"south_north_bridges {_sq(cx, cy - 1)}")
    return out


def _lane_ford_lines(cols: int, ford_terrain: str) -> List[str]:
    fords = {_sq(c, 2) for c in (max(1, cols // 4), max(1, cols // 2), min(cols, (3 * cols) // 4))}
    tokens = sorted(fords)
    out = [f"terrain {ford_terrain} {' '.join(tokens)}"]
    speed_line = terrain_speed_line(ford_terrain)
    if speed_line:
        out.append(f"{speed_line} {' '.join(tokens)}")
    cover_line = terrain_cover_line(ford_terrain)
    if cover_line:
        out.append(f"{cover_line} {' '.join(tokens)}")
    return out


def _team_trigger_lines(nb_players: int, team_mode: str) -> List[str]:
    """Emit opening alliance triggers for the selected team mode.

    - ``ffa``: each player gets a unique alliance (true free-for-all).
    - ``one_vs_many``: player1 alone vs all other players allied.
    - ``teams_2v2``: players 1+3 vs 2+4 (4 players only).
    """
    mode = team_mode if team_mode in TEAM_MODES else "ffa"
    if mode not in team_modes_for_players(nb_players):
        mode = "ffa"
    if mode == "teams_2v2":
        return [
            "trigger player1 (timer 0) (alliance 1)",
            "trigger player3 (timer 0) (alliance 1)",
            "trigger player2 (timer 0) (alliance 2)",
            "trigger player4 (timer 0) (alliance 2)",
        ]
    if mode == "one_vs_many":
        lines = ["trigger player1 (timer 0) (alliance 1)"]
        for i in range(2, nb_players + 1):
            lines.append(f"trigger player{i} (timer 0) (alliance 2)")
        return lines
    # ffa: everyone independent (overrides TrainingGame's default "all AIs ally")
    return [
        f"trigger player{i} (timer 0) (alliance {i})"
        for i in range(1, nb_players + 1)
    ]




def _default_skirmish_trigger_lines(cfg: RandomMapConfig) -> List[str]:
    """Defeat triggers for all modes; conquest victory only in conquest mode."""
    lines: List[str] = []
    if cfg.victory_mode == "conquest":
        lines.append("trigger players (no_enemy_player_left) (victory)")
    lines.extend(
        [
            "trigger players (no_building_left) (defeat)",
            "trigger computers (no_unit_left) (defeat)",
        ]
    )
    return lines


def _economic_goal(cfg: RandomMapConfig) -> int:
    goals = {
        "fast": 2000,
        "standard": 3000,
        "macro": 5000,
        "lanes": 2500,
    }
    return goals.get(cfg.template, 3000)


def _survival_seconds(cfg: RandomMapConfig) -> int:
    return 600 if cfg.template == "fast" else 900


def _objective_line_for_victory_mode(cfg: RandomMapConfig) -> str:
    mode = cfg.victory_mode
    if mode == "economic":
        goal = _economic_goal(cfg)
        return f"objective 5435 {goal} 131"
    if mode == "exploration":
        return "objective 5430"
    if mode == "survival":
        minutes = _survival_seconds(cfg) // 60
        return f"objective 5436 {minutes} 5437 5452"
    return "objective 5451"


def _victory_mode_trigger_lines(cfg: RandomMapConfig, ruin_flags: Sequence[str] | None = None) -> List[str]:
    mode = cfg.victory_mode
    if mode == "economic":
        goal = _economic_goal(cfg)
        return [
            f"trigger players (timer 60 60) (if (has_gathered {goal} resource1) (victory))",
        ]
    if mode == "survival":
        seconds = _survival_seconds(cfg)
        return [
            "trigger players "
            f"(timer {seconds}) (if (not (no_building_left)) (personal_victory))"
        ]
    if mode == "exploration" and ruin_flags:
        flags = " ".join(ruin_flags)
        return [
            "trigger players (timer 30 30) "
            f"(if (rmg_all_ruins_discovered_by_allies {flags}) (victory))",
        ]
    return []


def _next_computer_id(lines_out: List[str]) -> str:
    """Return ``computerN`` matching the next ``computer_only`` line index."""
    n = sum(1 for ln in lines_out if ln.startswith("computer_only")) + 1
    return f"computer{n}"


def _append_skirmish_triggers(
    lines_out: List[str],
    cfg: RandomMapConfig,
    ruin_flags: Sequence[str] | None = None,
) -> None:
    mode_lines = _victory_mode_trigger_lines(cfg, ruin_flags)
    default_lines = _default_skirmish_trigger_lines(cfg)
    if not mode_lines and not default_lines:
        return
    lines_out.append("")
    lines_out.append("; skirmish victory / defeat triggers")
    lines_out.extend(mode_lines)
    lines_out.extend(default_lines)


_EXPLORATION_BRIEFING_VARIANTS: Tuple[Tuple[int, ...], ...] = (
    (5487,),
    (5488,),
    (5489,),
    (5487, 5488),
    (5488, 5489),
    (5487, 5489),
)


def _briefing_intro_line(cfg: RandomMapConfig, rng: random.Random) -> str:
    """Seed-driven mission briefing for exploration victory mode."""
    if cfg.victory_mode != "exploration":
        return ""
    variant = rng.choice(_EXPLORATION_BRIEFING_VARIANTS)
    ids = (5486,) + variant + (5428,)
    return "intro " + " ".join(str(i) for i in ids)


def _append_briefing_intro(
    lines_out: List[str],
    cfg: RandomMapConfig,
    rng: random.Random,
) -> None:
    line = _briefing_intro_line(cfg, rng)
    if line:
        lines_out.append(line)


def _adjacent_squares(
    x: int, y: int, cols: int, lines: int
) -> List[Tuple[int, int]]:
    result: List[Tuple[int, int]] = []
    for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        nx, ny = x + dx, y + dy
        if 1 <= nx <= cols and 1 <= ny <= lines:
            result.append((nx, ny))
    return result


def _pick_depth_neighbor(
    rng: random.Random,
    x: int,
    y: int,
    cols: int,
    lines: int,
    starts: Sequence[Tuple[int, int]],
    blocked: Set[Tuple[int, int]],
) -> Tuple[int, int] | None:
    start_set = set(starts)
    candidates = [
        coord
        for coord in _adjacent_squares(x, y, cols, lines)
        if coord not in start_set and coord not in blocked and coord != (x, y)
    ]
    if not candidates:
        return None
    return rng.choice(candidates)


def _poi_pair_count(cfg: RandomMapConfig) -> int:
    if cfg.size == "small":
        base = 1
    elif cfg.size == "large":
        base = 2
    else:
        base = 2
    if cfg.victory_mode == "exploration":
        return base + 1
    return base


def _append_exploration_poi(
    lines_out: List[str],
    cfg: RandomMapConfig,
    rng: random.Random,
    cols: int,
    lines: int,
    starts: Sequence[Tuple[int, int]],
) -> List[str]:
    """Place ancient ruins, depth chambers, and reward triggers. Returns map_flag names."""
    if not _rules_has_type("ancient_ruin"):
        return []
    pair_count = _poi_pair_count(cfg)
    spots = _symmetric_pairs(rng, cols, lines, starts, pair_count)
    reward_gold = 300 if cfg.template == "fast" else 500
    reward_wood = 150 if cfg.template == "fast" else 250
    depth_gold = 150 if cfg.template == "fast" else 250
    depth_wood = 75 if cfg.template == "fast" else 125
    is_exploration = cfg.victory_mode == "exploration"

    placements: List[Tuple[str, str, int, int]] = []
    poi_index = 0
    for x, y in spots:
        for sx, sy in ((x, y), _mirror(x, y, cols, lines)):
            flag = f"rmg_ruin_{poi_index}"
            poi_index += 1
            placements.append((_sq(sx, sy), flag, sx, sy))

    ruin_flags = [flag for _, flag, _, _ in placements]
    flags_str = " ".join(ruin_flags)
    ruin_coords = {(sx, sy) for _, _, sx, sy in placements}
    blocked = ruin_coords | set(starts)

    for sq, flag, sx, sy in placements:
        lines_out.append(f"computer_only 0 0 neutral {sq} 1 ancient_ruin")
        reward_flag = f"{flag}_reward"
        announce = ""
        if is_exploration and flags_str:
            announce = f" (rmg_announce_ruins_remaining {flags_str})"
        lines_out.append(
            f"trigger players (has_entered {sq}) "
            f"(if (not (rmg_ruin_discovered_by_self {flag})) "
            f"(do (rmg_mark_ruin_discovered {flag}) "
            f"(if (not (map_flag {reward_flag})) "
            f"(do (set_map_flag {reward_flag}) "
            f"(cut_scene 5433) "
            f"(grant_resources {reward_gold} resource1 {reward_wood} resource2))) "
            f"(cut_scene 5490){announce}))"
        )
        neighbor = _pick_depth_neighbor(rng, sx, sy, cols, lines, starts, blocked)
        if neighbor is None:
            continue
        depth_sq = _sq(*neighbor)
        lines_out.append(
            f"trigger players (has_entered {depth_sq}) "
            f"(if (and (rmg_ruin_discovered_by_self {flag}) "
            f"(not (rmg_ruin_depth_claimed_by_self {flag}))) "
            f"(do (rmg_claim_ruin_depth {flag}) "
            f"(cut_scene 5491) "
            f"(grant_resources {depth_gold} resource1 {depth_wood} resource2)))"
        )
    return ruin_flags


def _append_capturable_dwelling(
    lines_out: List[str],
    cfg: RandomMapConfig,
    rng: random.Random,
    cols: int,
    lines: int,
    starts: Sequence[Tuple[int, int]],
) -> None:
    if not _rules_has_type("captured_barracks"):
        return
    dwell_pairs = 1 if cfg.size == "small" else 2
    if cfg.victory_mode == "exploration":
        dwell_pairs += 1
    spots = _symmetric_pairs(rng, cols, lines, starts, dwell_pairs)
    guards = [(2, "footman"), (1, "archer")]
    guard_parts: List[str] = []
    for qty, unit in guards:
        guard_parts.extend([str(qty), unit])
    for x, y in spots:
        for sx, sy in ((x, y), _mirror(x, y, cols, lines)):
            sq = _sq(sx, sy)
            flag = f"rmg_dwelling_{sq.replace(',', '_')}"
            comp = _next_computer_id(lines_out)
            lines_out.append(
                f"computer_only 0 0 {sq} 1 captured_barracks {' '.join(guard_parts)}"
            )
            lines_out.append(
                f"trigger {comp} (timer 5 5) "
                f"(if (and (not (map_flag {flag})) (unit_lost {sq} 1 captured_barracks)) "
                f"(do (set_map_flag {flag}) (cut_scene 5434)))"
            )
            lines_out.append(
                f"trigger {comp} (timer 300 600) "
                f"(if (and (not (map_flag {flag})) (not (unit_lost {sq} 1 captured_barracks))) "
                f"(add_units {sq} 2 footman))"
            )


def _rules_has_type(type_name: str) -> bool:
    try:
        from .definitions import rules

        return rules.unit_class(type_name) is not None
    except Exception:
        return False


def _append_resources(
    lines_out: List[str],
    spec: _TemplateSpec,
    cfg: RandomMapConfig,
    rng: random.Random,
    cols: int,
    lines: int,
    starts: Sequence[Tuple[int, int]],
) -> None:
    slots = _resource_slot_names()
    keywords = [_deposit_map_keyword(slot) for slot in slots]
    active_keywords = [kw for kw in keywords if kw]
    if not active_keywords:
        return

    start_tokens = [_sq(x, y) for x, y in starts]
    for kw in active_keywords:
        qty = _deposit_spot_qty(kw, spec.start_mine_qty)
        lines_out.append(f"{kw} {qty} {' '.join(start_tokens)}")

    tiers = list(spec.tiers_clustered if cfg.resource_layout == "clustered" else spec.tiers_balanced)
    if cfg.resource_layout == "clustered":
        spots = _cluster_squares(cols, lines, starts, len(tiers))
    else:
        spots = _symmetric_pairs(rng, cols, lines, starts, len(tiers))

    parts: Dict[str, Dict[int, List[str]]] = {
        kw: defaultdict(list) for kw in active_keywords
    }
    meadow_tokens: List[str] = []
    for tier, (x, y) in zip(tiers, spots):
        mx, my = _mirror(x, y, cols, lines)
        tier_qtys = _tier_quantities(tier, len(slots))
        for kw, slot_qty in zip(keywords, tier_qtys):
            if not kw:
                continue
            spot_qty = _deposit_spot_qty(kw, slot_qty)
            for sx, sy in ((x, y), (mx, my)):
                parts[kw][spot_qty].append(_sq(sx, sy))
        meadow_tokens.extend([_sq(x, y)] * 4)
        meadow_tokens.extend([_sq(mx, my)] * 4)

    if any(parts[kw] for kw in active_keywords):
        for kw in active_keywords:
            for qty, squares in parts[kw].items():
                if squares:
                    lines_out.append(f"{kw} {qty} {' '.join(squares)}")
        if meadow_tokens:
            lines_out.append(f"additional_meadows {' '.join(meadow_tokens)}")


def _append_player_block(
    lines_out: List[str],
    spec: _TemplateSpec,
    cfg: RandomMapConfig,
    start_tokens: Sequence[str],
) -> None:
    starting_resources = _pad_starting_resources(spec.starting_resources)
    lines_out.append("")
    lines_out.append(f"nb_meadows_by_square {spec.meadows_per_square}")
    lines_out.append(f"nb_players_min {cfg.nb_players}")
    lines_out.append(f"nb_players_max {cfg.nb_players}")
    lines_out.append(f"starting_squares {' '.join(start_tokens)}")
    lines_out.append(f"starting_units {spec.starting_units}")
    lines_out.append(f"starting_resources {' '.join(str(n) for n in starting_resources)}")
    lines_out.append(f"global_population_limit {spec.population_limit}")
    lines_out.append("random_starts 1")
    lines_out.append("")


def _append_creep(
    lines_out: List[str],
    cfg: RandomMapConfig,
    spec: RmgTemplateSpec,
    creep_squares: Sequence[str],
) -> None:
    creep_parts: List[str] = []
    for qty, unit_type in _scaled_creep(cfg.monster_strength, spec.creep_multiplier, cfg.template):
        creep_parts.extend([str(qty), unit_type])
    lines_out.append(
        f"computer_only 0 0 {' '.join(creep_squares)} {' '.join(creep_parts)}"
    )


def _generate_grid_definition(
    cfg: RandomMapConfig,
    spec: RmgTemplateSpec,
    seed: int,
    rng: random.Random,
) -> str:
    cols, lines = SIZE_PRESETS[cfg.size]
    starts = _player_starts(cols, lines, cfg.nb_players)
    cx, cy = cols // 2 + 1, lines // 2 + 1

    water_set: Set[Tuple[int, int]] = _water_squares_for_cfg(cfg, rng, cols, lines, starts)

    lines_out: List[str] = []
    lines_out.append(f"title random_map {cfg.template} seed_{seed}")
    _append_random_map_meta_lines(lines_out, cfg)
    _append_briefing_intro(lines_out, cfg, rng)
    lines_out.append(_objective_line_for_victory_mode(cfg))
    lines_out.append("")
    lines_out.append("square_width 12")
    lines_out.append(f"nb_columns {cols}")
    lines_out.append(f"nb_lines {lines}")
    lines_out.append("")

    we, sn = _grid_paths(cols, lines, water_set)
    lines_out.append("; auto-generated paths")
    for chunk in _chunks(we):
        lines_out.append(f"west_east_paths {chunk}")
    for chunk in _chunks(sn):
        lines_out.append(f"south_north_paths {chunk}")
    bridge_lines = _center_bridge_lines(cols, lines, water_set)
    if cfg.water == "river":
        bridge_lines = _river_bridge_lines(cols, lines, water_set)
    elif spec.center_bridges:
        bridge_lines = bridge_lines or _center_bridge_lines(cols, lines, set())
    if bridge_lines:
        lines_out.extend(bridge_lines)
    lines_out.append("")

    if water_set:
        water_terrain = rmg_water_terrain(spec.water_terrain)
        lines_out.extend(_water_lines(water_set, water_terrain))
        lines_out.append("")

    terrain_out = _terrain_lines(rng, cols, lines, starts, cfg.terrain, water_set, cfg.template)
    if terrain_out:
        lines_out.extend(terrain_out)
        lines_out.append("")

    _append_resources(lines_out, spec, cfg, rng, cols, lines, starts)
    _append_treasure(lines_out, cfg, rng, cols, lines, starts)
    _append_hunting(lines_out, cfg, rng, cols, lines, starts)
    start_tokens = [_sq(x, y) for x, y in starts]
    _append_player_block(lines_out, spec, cfg, start_tokens)

    creep_squares = [_sq(cx, cy)]
    mx, my = _mirror(cx, cy, cols, lines)
    if (mx, my) != (cx, cy):
        creep_squares.append(_sq(mx, my))
    _append_creep(lines_out, cfg, spec, creep_squares)

    ruin_flags = _append_exploration_poi(
        lines_out, cfg, rng, cols, lines, starts
    )
    _append_capturable_dwelling(
        lines_out, cfg, rng, cols, lines, starts
    )

    team_lines = _team_trigger_lines(cfg.nb_players, cfg.team_mode)
    if team_lines:
        lines_out.append("")
        lines_out.extend(team_lines)

    _append_skirmish_triggers(lines_out, cfg, ruin_flags or None)

    return "\n".join(lines_out) + "\n"


def _generate_lanes_definition(
    cfg: RandomMapConfig,
    spec: RmgTemplateSpec,
    seed: int,
    rng: random.Random,
) -> str:
    cols = LANE_COLUMN_PRESETS[cfg.size]
    lines = LANE_LINES
    starts = _lane_starts(cols, cfg.nb_players)
    cx = cols // 2 + 1

    lines_out: List[str] = []
    lines_out.append(f"title random_map lanes seed_{seed}")
    _append_random_map_meta_lines(lines_out, cfg)
    _append_briefing_intro(lines_out, cfg, rng)
    lines_out.append(_objective_line_for_victory_mode(cfg))
    lines_out.append("")
    lines_out.append("square_width 12")
    lines_out.append(f"nb_columns {cols}")
    lines_out.append(f"nb_lines {lines}")
    lines_out.append("")

    we, sn = _lane_paths(cols, starts)
    lines_out.append("; lanes template paths")
    for chunk in _chunks(we):
        lines_out.append(f"west_east_paths {chunk}")
    for chunk in _chunks(sn):
        lines_out.append(f"south_north_paths {chunk}")
    lines_out.append("")
    lines_out.extend(_lane_ford_lines(cols, rmg_ford_terrain(spec.ford_terrain)))
    lines_out.append("")

    _append_resources(lines_out, spec, cfg, rng, cols, lines, starts)
    _append_treasure(lines_out, cfg, rng, cols, lines, starts)
    _append_hunting(lines_out, cfg, rng, cols, lines, starts)
    _append_lane_start_meadows(lines_out, starts)
    start_tokens = [_sq(x, y) for x, y in starts]
    _append_player_block(lines_out, spec, cfg, start_tokens)

    creep_squares = [_sq(cx, 2)]
    _append_creep(lines_out, cfg, spec, creep_squares)

    ruin_flags = _append_exploration_poi(
        lines_out, cfg, rng, cols, lines, starts
    )
    _append_capturable_dwelling(
        lines_out, cfg, rng, cols, lines, starts
    )

    team_lines = _team_trigger_lines(cfg.nb_players, cfg.team_mode)
    if team_lines:
        lines_out.append("")
        lines_out.extend(team_lines)

    _append_skirmish_triggers(lines_out, cfg, ruin_flags or None)

    return "\n".join(lines_out) + "\n"


def generate_definition(config: RandomMapConfig) -> Tuple[str, int]:
    """Return (map definition text, seed used)."""
    _refresh_custom_templates()
    cfg = config.normalized()
    spec = get_template_spec(cfg.template, _builtin_rmg_specs())
    seed = cfg.resolved_seed()
    rng = random.Random(seed)
    if spec.layout == "lanes":
        return _generate_lanes_definition(cfg, spec, seed, rng), seed
    return _generate_grid_definition(cfg, spec, seed, rng), seed


def map_voice_title_from_parts(title, map_name="", definition=""):
    """Convert a random map name/definition title to TTS message tokens."""
    if isinstance(title, list) and title:
        if isinstance(title[0], int) and title[0] >= 5000:
            return list(title)

    seed = None
    template = "standard"

    if definition:
        for line in definition.splitlines():
            stripped = line.strip()
            if not stripped.startswith("title "):
                continue
            parts = stripped.split()[1:]
            if not parts or parts[0] != "random_map":
                break
            if len(parts) >= 2 and parts[1] in _TEMPLATE_TITLE:
                template = parts[1]
            for part in parts[2:]:
                if part.startswith("seed_"):
                    try:
                        seed = int(part[5:])
                    except ValueError:
                        pass
            break

    for part in title or []:
        if not isinstance(part, str):
            continue
        if part in _TEMPLATE_TITLE:
            template = part
        elif part.startswith("seed_"):
            try:
                seed = int(part[5:])
            except ValueError:
                pass
        elif part.startswith("random_"):
            try:
                seed = int(part.split("_", 1)[1])
            except ValueError:
                pass

    if seed is None and isinstance(map_name, str) and map_name.startswith("random_"):
        try:
            seed = int(map_name.split("_", 1)[1])
        except ValueError:
            return None

    if seed is None:
        return None

    return (
        mp.RMG_RANDOM_MAP
        + _TEMPLATE_TITLE.get(template, mp.RMG_TEMPLATE_STANDARD)
        + mp.RMG_SEED
        + nb2msg(seed)
    )


def map_voice_title(map_obj) -> list | None:
    """Return TTS message tokens for a random map lobby/display title."""
    map_name = getattr(map_obj, "name", "") or ""
    if not map_name.startswith("random_"):
        return None
    return map_voice_title_from_parts(
        getattr(map_obj, "title", None) or [],
        map_name,
        getattr(map_obj, "definition", "") or "",
    )


def make_map(config: RandomMapConfig) -> Tuple[Map, int]:
    """Build a ``Map`` instance ready for ``World.load_and_build_map``."""
    definition, seed = generate_definition(config)
    map_name = f"random_{seed}.txt"
    m = Map.loads(definition.encode("utf-8"), map_name)
    voice_title = map_voice_title(m)
    if voice_title:
        m.title = voice_title
    return m, seed


def menu_title_for_config(config: RandomMapConfig) -> list:
    """Voice-menu title tokens for a config (before generation)."""
    _refresh_custom_templates()
    cfg = config.normalized()
    parts = (
        mp.RMG_RANDOM_MAP
        + template_title_voice(cfg.template, _TEMPLATE_TITLE)
        + _SIZE_TITLE[cfg.size]
        + nb2msg(cfg.nb_players)
        + mp.RMG_PLAYERS
    )
    if cfg.team_mode == "teams_2v2":
        parts += mp.RMG_TEAMS_2V2
    elif cfg.team_mode == "one_vs_many":
        parts += mp.RMG_ONE_VS_MANY
    elif cfg.nb_players >= 3 and cfg.team_mode == "ffa":
        parts += mp.RMG_FFA
    if cfg.water != "none":
        parts += _WATER_TITLE[cfg.water]
    if cfg.treasure != "none":
        parts += _TREASURE_TITLE[cfg.treasure]
    if cfg.victory_mode != "conquest":
        parts += _VICTORY_TITLE[cfg.victory_mode]
    return parts


def server_create_command(
    config: RandomMapConfig,
    speed: float | str,
    is_public: bool = False,
    treaty_minutes: int = 0,
) -> str:
    """Build a ``create_random`` server command from RMG settings."""
    cfg = config.normalized()
    seed_token = int(cfg.seed) if cfg.seed is not None and int(cfg.seed) > 0 else 0
    parts = [
        "create_random",
        cfg.size,
        str(cfg.nb_players),
        cfg.monster_strength,
        cfg.resource_layout,
        cfg.template,
        cfg.terrain,
        cfg.team_mode,
        cfg.water,
        cfg.treasure,
        cfg.victory_mode,
        str(seed_token),
        str(speed),
    ]
    if is_public:
        parts.append("public")
    parts.append(str(int(treaty_minutes)))
    return " ".join(parts)


def parse_server_create_args(
    args: Sequence[str],
) -> Tuple[RandomMapConfig, float, bool, int]:
    """Parse ``create_random`` tokens (without the command name)."""
    tokens = list(args)
    if len(tokens) < 5:
        raise ValueError("create_random requires at least 5 arguments")
    treaty_minutes = 0
    if tokens and tokens[-1].isdigit() and len(tokens) >= 6:
        treaty_minutes = int(tokens.pop())
    is_public = False
    if tokens and tokens[-1] == "public":
        is_public = True
        tokens.pop()
    speed = float(tokens.pop())

    template = "standard"
    terrain = "random"
    team_mode = "ffa"
    water = "none"
    treasure = "none"
    victory_mode = "conquest"
    seed: int | None = None

    if len(tokens) >= 11:
        seed_raw = int(tokens.pop())
        seed = seed_raw if seed_raw > 0 else None
        victory_mode = tokens.pop()
        treasure = tokens.pop()
        water = tokens.pop()
        team_mode = tokens.pop()
        terrain = tokens.pop()
        template = tokens.pop()
    elif len(tokens) >= 10:
        seed_raw = int(tokens.pop())
        seed = seed_raw if seed_raw > 0 else None
        treasure = tokens.pop()
        water = tokens.pop()
        team_mode = tokens.pop()
        terrain = tokens.pop()
        template = tokens.pop()
    elif len(tokens) >= 9:
        seed_raw = int(tokens.pop())
        seed = seed_raw if seed_raw > 0 else None
        water = tokens.pop()
        team_mode = tokens.pop()
        terrain = tokens.pop()
        template = tokens.pop()
    elif len(tokens) >= 6:
        terrain = tokens.pop()
        template = tokens.pop()

    layout = tokens.pop()
    monster = tokens.pop()
    nb_players = int(tokens.pop())
    size = tokens.pop()
    if tokens:
        raise ValueError("unexpected extra create_random arguments")
    return (
        RandomMapConfig(
            size=size,
            nb_players=nb_players,
            monster_strength=monster,
            resource_layout=layout,
            template=template,
            terrain=terrain,
            team_mode=team_mode,
            water=water,
            treasure=treasure,
            victory_mode=victory_mode,
            seed=seed,
        ),
        speed,
        is_public,
        treaty_minutes,
    )


_CAMPAIGN_CHAPTER_MARKER = "random_map_chapter"

_CAMPAIGN_CONFIG_ALIASES = {
    "size": "size",
    "nb_players": "nb_players",
    "players": "nb_players",
    "monster_strength": "monster_strength",
    "monster": "monster_strength",
    "resource_layout": "resource_layout",
    "layout": "resource_layout",
    "template": "template",
    "terrain": "terrain",
    "team_mode": "team_mode",
    "teams": "team_mode",
    "water": "water",
    "treasure": "treasure",
    "seed": "seed",
}


def _parse_title_tokens(value: str) -> list:
    parts = []
    for part in value.split():
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(part)
    return parts


def _parse_campaign_seed(value: str) -> int | None:
    token = value.strip().lower()
    if not token or token in ("random", "0"):
        return None
    seed = int(token)
    return seed if seed > 0 else None


def parse_campaign_random_chapter(text: str) -> Tuple[RandomMapConfig, list, str]:
    """Parse a ``random_map_chapter`` campaign file.

    Returns ``(config, title_tokens, overlay_text)``. RMG settings are single-line
    ``key value`` pairs; every other non-empty line (``intro``, ``trigger``, …)
    is appended to the generated map definition when the chapter starts.
    """
    lines = text.splitlines()
    while lines and (not lines[0].strip() or lines[0].strip().startswith(";")):
        lines.pop(0)
    if not lines or lines[0].strip() != _CAMPAIGN_CHAPTER_MARKER:
        raise ValueError("not a random_map_chapter file")

    config_data: dict = {}
    title: list = []
    overlay_lines: list[str] = []

    for line in lines[1:]:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(";"):
            overlay_lines.append(line)
            continue
        parts = stripped.split(None, 1)
        key = parts[0].lower()
        value = parts[1] if len(parts) > 1 else ""

        if key == "title":
            title = _parse_title_tokens(value)
            continue

        field = _CAMPAIGN_CONFIG_ALIASES.get(key)
        if field is None:
            overlay_lines.append(line)
            continue

        if field == "seed":
            config_data["seed"] = _parse_campaign_seed(value)
        elif field == "nb_players":
            config_data["nb_players"] = int(value)
        else:
            config_data[field] = value

    if not title:
        title = [mp.RMG_RANDOM_MAP[0] if mp.RMG_RANDOM_MAP else "random_map"]

    cfg = RandomMapConfig(**config_data).normalized()
    return cfg, title, "\n".join(overlay_lines)


def _pin_campaign_spawn_slot(definition: str) -> str:
    """Single-player campaign must use spawn slot 0 (player1 triggers live there)."""
    lines: list[str] = []
    replaced = False
    for line in definition.splitlines():
        if line.strip().startswith("random_starts "):
            lines.append("random_starts 0")
            replaced = True
        else:
            lines.append(line)
    if not replaced:
        lines.append("random_starts 0")
    return "\n".join(lines) + "\n"


def merge_campaign_overlay(definition: str, overlay: str) -> str:
    """Append campaign overlay lines and drop RMG skirmish title/objective headers."""
    overlay = overlay.strip()
    if not overlay:
        return definition

    overlay_has_starting_units = any(
        ln.strip().startswith("starting_units ") for ln in overlay.splitlines()
    )
    skipped_title = False
    skipped_objective = False
    skipped_starting_units = False
    kept: list[str] = []
    for line in definition.splitlines():
        stripped = line.strip()
        if not skipped_title and stripped.startswith("title "):
            skipped_title = True
            continue
        if not skipped_objective and stripped.startswith("objective "):
            skipped_objective = True
            continue
        if (
            overlay_has_starting_units
            and not skipped_starting_units
            and stripped.startswith("starting_units ")
        ):
            skipped_starting_units = True
            continue
        kept.append(line)

    kept.append("")
    kept.append("; campaign overlay")
    kept.extend(overlay.splitlines())
    return "\n".join(kept) + "\n"


def make_campaign_map(
    config: RandomMapConfig,
    overlay: str,
    campaign_name: str,
    chapter_number: int,
) -> Tuple[Map, int]:
    """Build a campaign chapter map (fresh random seed when config.seed is unset)."""
    cfg = config.normalized()
    definition, seed = generate_definition(cfg)
    merged = merge_campaign_overlay(definition, overlay)
    merged = _pin_campaign_spawn_slot(merged)
    buffer_name = f"{chapter_number}.txt"
    m = Map.loads(merged.encode("utf-8"), buffer_name)
    m.name = f"{campaign_name}/{chapter_number}"
    return m, seed


def is_random_map_chapter_text(text: str) -> bool:
    line = text.splitlines()[0].strip() if text.splitlines() else ""
    return line == _CAMPAIGN_CHAPTER_MARKER
