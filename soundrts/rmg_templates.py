"""Load player/mod-authored random map templates and rules-driven RMG terrain."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

_TEMPLATE_MARKER = "random_map_template"

_BUILTIN_LAYOUTS = {"grid", "lanes"}


def _is_truthy(value) -> bool:
    if value is None:
        return False
    if isinstance(value, (list, tuple)):
        return _is_truthy(value[0] if value else None)
    if isinstance(value, str):
        return value.strip().lower() not in ("", "0", "false", "no")
    return bool(value)


def _parse_int_list(tokens: Sequence[str]) -> Tuple[int, ...]:
    return tuple(int(t) for t in tokens)


def _parse_tier_pairs(tokens: Sequence[str]) -> Tuple[Tuple[int, int], ...]:
    if len(tokens) < 2:
        return ()
    values = [int(t) for t in tokens]
    if len(values) % 2:
        values = values[:-1]
    return tuple((values[i], values[i + 1]) for i in range(0, len(values), 2))


def _parse_title_voice(value: str) -> List:
    parts = value.split()
    if parts and all(p.isdigit() for p in parts):
        return [int(p) for p in parts]
    return list(value)


@dataclass(frozen=True)
class RmgTemplateSpec:
    layout: str
    starting_units: str
    starting_resources: Tuple[int, int]
    start_mine_qty: int
    tiers_balanced: Tuple[Tuple[int, int], ...]
    tiers_clustered: Tuple[Tuple[int, int], ...]
    population_limit: int
    meadows_per_square: int
    creep_multiplier: float
    center_bridges: bool
    terrain_modes: Tuple[str, ...] = ()  # empty = random/grass + all rmg_terrain from rules
    water_terrain: str = "lake"
    ford_terrain: str = "ford"
    skip_terrain_menu: bool = False
    skip_water_menu: bool = False


@dataclass
class RmgTemplateEntry:
    name: str
    spec: RmgTemplateSpec
    title_voice: List = field(default_factory=list)
    source: str = ""


_TEMPLATE_FIELD_ALIASES = {
    "name": "name",
    "template": "name",
    "extends": "extends",
    "title": "title",
    "layout": "layout",
    "starting_units": "starting_units",
    "starting_resources": "starting_resources",
    "start_mine_qty": "start_mine_qty",
    "population_limit": "population_limit",
    "meadows_per_square": "meadows_per_square",
    "creep_multiplier": "creep_multiplier",
    "center_bridges": "center_bridges",
    "terrain_modes": "terrain_modes",
    "water_terrain": "water_terrain",
    "ford_terrain": "ford_terrain",
    "skip_terrain_menu": "skip_terrain_menu",
    "skip_water_menu": "skip_water_menu",
    "tiers_balanced": "tiers_balanced",
    "tiers_clustered": "tiers_clustered",
    "monster_weak": "monster_weak",
    "monster_medium": "monster_medium",
    "monster_strong": "monster_strong",
}


def _template_search_paths() -> List[Path]:
    paths: List[Path] = [
        Path("cfg/randommap"),
        Path("res/randommap"),
    ]
    try:
        from . import config
    except Exception:
        config = None
    if config is not None:
        for mod_name in (n.strip() for n in config.mods.split(",") if n.strip()):
            for base in (Path("mods"), Path("res/mods")):
                mod_dir = base / mod_name / "randommap"
                if mod_dir.is_dir():
                    paths.append(mod_dir)
                    break
    return paths


def _iter_template_files() -> Iterable[Path]:
    seen: set[str] = set()
    for directory in _template_search_paths():
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.txt")):
            key = str(path.resolve()).lower()
            if key in seen:
                continue
            seen.add(key)
            yield path


def _base_spec(name: str, builtin_specs: Dict[str, RmgTemplateSpec]) -> RmgTemplateSpec | None:
    if name in builtin_specs:
        return builtin_specs[name]
    entry = _CUSTOM_REGISTRY.get(name)
    if entry is not None:
        return entry.spec
    return None


def _parse_monster_preset(tokens: Sequence[str]) -> List[Tuple[int, str]]:
    pairs: List[Tuple[int, str]] = []
    idx = 0
    while idx + 1 < len(tokens):
        pairs.append((int(tokens[idx]), tokens[idx + 1]))
        idx += 2
    return pairs


def parse_template_text(
    text: str,
    *,
    source: str = "",
    builtin_specs: Dict[str, RmgTemplateSpec] | None = None,
) -> RmgTemplateEntry:
    lines = text.splitlines()
    while lines and (not lines[0].strip() or lines[0].strip().startswith(";")):
        lines.pop(0)
    if not lines or lines[0].strip() != _TEMPLATE_MARKER:
        raise ValueError("not a random_map_template file")

    builtin_specs = builtin_specs or {}
    data: dict = {}
    title_voice: List = []
    monster_presets: Dict[str, List[Tuple[int, str]]] = {}

    for line in lines[1:]:
        stripped = line.strip()
        if not stripped or stripped.startswith(";"):
            continue
        parts = stripped.split()
        key = parts[0].lower()
        value_tokens = parts[1:]
        field_name = _TEMPLATE_FIELD_ALIASES.get(key)
        if field_name is None:
            continue
        if field_name == "title":
            title_voice = _parse_title_voice(stripped.split(None, 1)[1] if len(parts) > 1 else "")
            continue
        if field_name.startswith("monster_"):
            monster_presets[field_name] = _parse_monster_preset(value_tokens)
            continue
        if field_name in ("terrain_modes",):
            data[field_name] = tuple(value_tokens)
            continue
        if field_name in ("starting_resources",):
            ints = _parse_int_list(value_tokens)
            if len(ints) >= 2:
                data[field_name] = (ints[0], ints[1])
            continue
        if field_name in ("tiers_balanced", "tiers_clustered"):
            data[field_name] = _parse_tier_pairs(value_tokens)
            continue
        if field_name in (
            "start_mine_qty",
            "population_limit",
            "meadows_per_square",
        ):
            if value_tokens:
                data[field_name] = int(value_tokens[0])
            continue
        if field_name == "creep_multiplier":
            if value_tokens:
                data[field_name] = float(value_tokens[0])
            continue
        if field_name in ("center_bridges", "skip_terrain_menu", "skip_water_menu"):
            data[field_name] = _is_truthy(value_tokens[0] if value_tokens else "1")
            continue
        if value_tokens:
            data[field_name] = value_tokens[0] if field_name != "starting_units" else " ".join(value_tokens)

    name = data.get("name")
    if not name:
        raise ValueError("random_map_template requires name")
    extends = data.pop("extends", None)
    base = _base_spec(extends, builtin_specs) if extends else None
    if extends and base is None:
        raise ValueError(f"unknown extends template: {extends}")

    spec_kwargs = {}
    if base is not None:
        spec_kwargs = {
            "layout": base.layout,
            "starting_units": base.starting_units,
            "starting_resources": base.starting_resources,
            "start_mine_qty": base.start_mine_qty,
            "tiers_balanced": base.tiers_balanced,
            "tiers_clustered": base.tiers_clustered,
            "population_limit": base.population_limit,
            "meadows_per_square": base.meadows_per_square,
            "creep_multiplier": base.creep_multiplier,
            "center_bridges": base.center_bridges,
            "terrain_modes": base.terrain_modes,
            "water_terrain": base.water_terrain,
            "ford_terrain": base.ford_terrain,
            "skip_terrain_menu": base.skip_terrain_menu,
            "skip_water_menu": base.skip_water_menu,
        }
    for key, value in data.items():
        if key == "name":
            continue
        if key in spec_kwargs or key in RmgTemplateSpec.__dataclass_fields__:
            spec_kwargs[key] = value

    layout = spec_kwargs.get("layout", "grid")
    if layout not in _BUILTIN_LAYOUTS:
        raise ValueError(f"unsupported layout: {layout}")

    spec = RmgTemplateSpec(**spec_kwargs)
    if not title_voice:
        title_voice = _parse_title_voice(name.replace("_", " "))
    entry = RmgTemplateEntry(name=name, spec=spec, title_voice=title_voice, source=source)
    if monster_presets:
        entry.monster_presets = monster_presets  # type: ignore[attr-defined]
    return entry


_CUSTOM_REGISTRY: Dict[str, RmgTemplateEntry] = {}
_CUSTOM_MONSTER_PRESETS: Dict[str, Dict[str, List[Tuple[int, str]]]] = {}
_LOADED = False


def reload_custom_templates(builtin_specs: Dict[str, RmgTemplateSpec] | None = None) -> None:
    global _LOADED
    _CUSTOM_REGISTRY.clear()
    _CUSTOM_MONSTER_PRESETS.clear()
    for path in _iter_template_files():
        try:
            entry = parse_template_text(
                path.read_text(encoding="utf-8"),
                source=str(path),
                builtin_specs=builtin_specs,
            )
        except Exception:
            continue
        if entry.name in _CUSTOM_REGISTRY:
            continue
        _CUSTOM_REGISTRY[entry.name] = entry
        presets = getattr(entry, "monster_presets", None)
        if presets:
            _CUSTOM_MONSTER_PRESETS[entry.name] = presets
    _LOADED = True


def ensure_loaded(builtin_specs: Dict[str, RmgTemplateSpec] | None = None) -> None:
    if not _LOADED:
        reload_custom_templates(builtin_specs)


def custom_template_names() -> Tuple[str, ...]:
    ensure_loaded()
    return tuple(sorted(_CUSTOM_REGISTRY))


def custom_template_entry(name: str) -> RmgTemplateEntry | None:
    ensure_loaded()
    return _CUSTOM_REGISTRY.get(name)


def template_title_voice(name: str, builtin_titles: Dict[str, List]) -> List:
    ensure_loaded()
    if name in builtin_titles:
        return list(builtin_titles[name])
    entry = _CUSTOM_REGISTRY.get(name)
    if entry is not None and entry.title_voice:
        return list(entry.title_voice)
    return _parse_title_voice(name.replace("_", " "))


def all_template_names(builtin_names: Sequence[str]) -> Tuple[str, ...]:
    ensure_loaded()
    names = list(builtin_names)
    for name in custom_template_names():
        if name not in names:
            names.append(name)
    return tuple(names)


def get_template_spec(name: str, builtin_specs: Dict[str, RmgTemplateSpec]) -> RmgTemplateSpec:
    ensure_loaded(builtin_specs)
    if name in builtin_specs:
        return builtin_specs[name]
    entry = _CUSTOM_REGISTRY.get(name)
    if entry is not None:
        return entry.spec
    return builtin_specs["standard"]


def template_monster_presets(name: str, default_presets: Dict[str, List[Tuple[int, str]]]) -> Dict[str, List[Tuple[int, str]]]:
    ensure_loaded()
    custom = _CUSTOM_MONSTER_PRESETS.get(name)
    if not custom:
        return default_presets
    merged = dict(default_presets)
    for key, value in custom.items():
        strength = key.replace("monster_", "")
        merged[strength] = value
    return merged


def _rules_snapshot():
    from .definitions import rules

    return rules


def _terrain_rules_flag(name: str, prop: str) -> bool:
    rules = _rules_snapshot()
    if rules.get(name, "class") != ["terrain"]:
        return False
    return _is_truthy(rules.get(name, prop))


def rmg_placeable_terrains() -> Tuple[str, ...]:
    rules = _rules_snapshot()
    names = []
    for name in rules.classnames():
        if rules.get(name, "class") != ["terrain"]:
            continue
        if _is_truthy(rules.get(name, "rmg_terrain")):
            names.append(name)
    if names:
        return tuple(names)
    for fallback in ("marsh", "mountain"):
        if rules.get(fallback, "class") == ["terrain"]:
            names.append(fallback)
    return tuple(names)


def rmg_water_terrain(default: str = "lake") -> str:
    rules = _rules_snapshot()
    for name in rules.classnames():
        if rules.get(name, "class") != ["terrain"]:
            continue
        if _is_truthy(rules.get(name, "rmg_water")):
            return name
    if rules.get(default, "class") == ["terrain"]:
        return default
    for name in rules.classnames():
        if rules.get(name, "class") == ["terrain"] and _is_truthy(rules.get(name, "is_water")):
            return name
    return default


def rmg_ford_terrain(default: str = "ford") -> str:
    rules = _rules_snapshot()
    for name in rules.classnames():
        if rules.get(name, "class") != ["terrain"]:
            continue
        if _is_truthy(rules.get(name, "rmg_ford")):
            return name
    if rules.get(default, "class") == ["terrain"]:
        return default
    return default


def terrain_uses_border_style(name: str) -> bool:
    if not name or name in ("grass", "random"):
        return False
    if _terrain_rules_flag(name, "rmg_border"):
        return True
    if _terrain_rules_flag(name, "blocks_path"):
        return True
    return name == "mountain"


def terrain_speed_line(name: str) -> str | None:
    from .lib.square_terrain_rules import terrain_default_speed

    speed = terrain_default_speed(name)
    if speed is None:
        return None
    ground = speed[0] / 100
    air = speed[1] / 100
    if ground == 1 and air == 1:
        return None
    if float(ground).is_integer():
        ground_text = str(int(ground))
    else:
        ground_text = str(ground)
    if float(air).is_integer():
        air_text = str(int(air))
    else:
        air_text = str(air)
    return f"speed {ground_text} {air_text}"


def terrain_menu_voice(name: str) -> List:
    if name == "random":
        from . import msgparts as mp

        return list(mp.RMG_RANDOM)
    if name == "grass":
        from . import msgparts as mp

        return list(mp.RMG_GRASS)
    try:
        from .definitions import style

        title = style.get(name, "title", warn_if_not_found=False)
        if title:
            return list(title)
    except Exception:
        pass
    return _parse_title_voice(name.replace("_", " "))


def default_terrain_menu_modes() -> Tuple[str, ...]:
    """Menu entries for built-in templates: random, grass, then every rmg_terrain def."""
    seen: set[str] = set()
    ordered: List[str] = []
    for name in ("random", "grass") + rmg_placeable_terrains():
        if name in seen:
            continue
        seen.add(name)
        ordered.append(name)
    return tuple(ordered)


def terrain_modes_for_template(template_name: str, builtin_specs: Dict[str, RmgTemplateSpec]) -> Tuple[str, ...]:
    spec = get_template_spec(template_name, builtin_specs)
    if spec.terrain_modes:
        return spec.terrain_modes
    return default_terrain_menu_modes()


def normalize_terrain_mode(mode: str, template_name: str, builtin_specs: Dict[str, RmgTemplateSpec]) -> str:
    allowed = set(terrain_modes_for_template(template_name, builtin_specs))
    if mode in allowed:
        return mode
    if mode in rmg_placeable_terrains():
        return mode
    if mode == "random":
        return "random"
    return "random"


def resolve_random_terrain(rng, template_name: str, builtin_specs: Dict[str, RmgTemplateSpec]) -> str:
    candidates = [
        name
        for name in terrain_modes_for_template(template_name, builtin_specs)
        if name not in ("random", "grass")
    ]
    if not candidates:
        candidates = list(rmg_placeable_terrains())
    if not candidates:
        return "grass"
    return rng.choice(candidates)


def is_builtin_template(name: str, builtin_names: Sequence[str]) -> bool:
    return name in builtin_names
