"""Unit level-up stat bonuses: every combat stat can define ``<stat>_per_level`` in rules."""

# Life / mana / revival stats.
_LEVEL_UP_BASE_STATS = (
    "hp_max",
    "hp_regen",
    "revival_time",
    "mana_max",
    "mana_regen",
)

# Regen / heal / harm timing and range (PRECISION, milliseconds or distance).
_LEVEL_UP_REGEN_HEAL_STATS = (
    "hp_regen_cd",
    "hp_regen_ready",
    "mana_regen_cd",
    "mana_regen_ready",
    "heal_cd",
    "heal_radius",
    "heal_range",
    "heal_ready",
    "harm_cd",
    "harm_radius",
    "harm_range",
    "harm_ready",
)

# Numeric combat stats (excluding *_vs dicts, booleans, and lists).
_LEVEL_UP_COMBAT_STATS = (
    "mdg",
    "rdg",
    "mdf",
    "rdf",
    "minimal_damage",
    "minimal_mdg",
    "minimal_rdg",
    "mdg_minimal_damage",
    "rdg_minimal_damage",
    "mdg_crit",
    "rdg_crit",
    "mdg_range",
    "rdg_range",
    "mdg_minimal_range",
    "rdg_minimal_range",
    "mdg_splash",
    "rdg_splash",
    "mdg_radius",
    "rdg_radius",
    "mdg_splash_decay_min",
    "rdg_splash_decay_min",
    "mdg_cd",
    "rdg_cd",
    "mdg_ready",
    "rdg_ready",
    "mdg_cover",
    "rdg_cover",
    "mdg_dodge",
    "rdg_dodge",
    "mdg_delay",
    "rdg_delay",
    "mdg_status_duration",
    "rdg_status_duration",
    "charge_mdg",
    "charge_rdg",
    "charge_mdg_dist",
    "charge_rdg_dist",
    "charge_mdg_min_dist",
    "charge_rdg_min_dist",
    "charge_mdg_cd",
    "charge_rdg_cd",
    "charge_mdg_splash",
    "charge_rdg_splash",
    "charge_mdg_radius",
    "charge_rdg_radius",
    "charge_mdg_splash_decay_min",
    "charge_rdg_splash_decay_min",
    "op_charge_mdg",
    "op_charge_rdg",
    "op_charge_mdg_dist",
    "op_charge_rdg_dist",
    "op_charge_mdg_cd",
    "op_charge_rdg_cd",
    "exp_dgf",
    "exp_hp_cost",
    "forced_damage",
)

# Integer (non-PRECISION) stats — per_level uses plain int increments.
LEVEL_UP_INT_STAT_ATTRS = (
    "heal_level",
    "harm_level",
    "mdg_crit_rate",
    "rdg_crit_rate",
    "mdg_piercing",
    "rdg_piercing",
    "mdf_piercing",
    "rdf_piercing",
    "mdg_piercing_rate",
    "rdg_piercing_rate",
    "mdf_crit_rate",
    "rdf_crit_rate",
)

LEVEL_UP_STAT_ATTRS = (
    _LEVEL_UP_BASE_STATS
    + _LEVEL_UP_REGEN_HEAL_STATS
    + _LEVEL_UP_COMBAT_STATS
    + LEVEL_UP_INT_STAT_ATTRS
)


def apply_level_stat_bonuses(unit) -> None:
    """Apply one level's worth of ``*_per_level`` bonuses to *unit*."""
    for attr in LEVEL_UP_STAT_ATTRS:
        bonus = getattr(unit, f"{attr}_per_level", 0)
        if not bonus:
            continue
        setattr(unit, attr, getattr(unit, attr, 0) + bonus)
        if not getattr(unit, "level_up_heal_full", 0):
            if attr == "hp_max":
                unit.hp = getattr(unit, "hp", 0) + bonus
            elif attr == "mana_max":
                unit.mana = getattr(unit, "mana", 0) + bonus
    if getattr(unit, "level_up_heal_full", 0):
        unit.hp = getattr(unit, "hp_max", getattr(unit, "hp", 0))
        mana_max = getattr(unit, "mana_max", 0)
        if mana_max:
            unit.mana = mana_max


def apply_level_up_to(unit, target_level: int, *, notify: bool = False) -> None:
    """Raise *unit* from its current level to *target_level* with per-level bonuses."""
    max_level = getattr(unit, "max_level", 99)
    target_level = max(1, min(int(target_level), max_level))
    while unit.level < target_level and unit.level < max_level:
        unit.level += 1
        apply_level_stat_bonuses(unit)
    if hasattr(unit, "_apply_level_skills_up_to"):
        unit._apply_level_skills_up_to(target_level, notify=notify)
