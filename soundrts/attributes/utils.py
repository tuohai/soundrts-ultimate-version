"""
工具函数和辅助方法模块
"""

from .. import msgparts as mp
from ..definitions import style, rules, _raw_class_attr


def display_class_names(type_class, context, rules=None):
    """解析属性详情界面应显示的 class 名称列表。

    可装备物品（rules 里 class item + equippable_as_weapon/armor）在武器/护甲
    详情中应显示 weapon/armor，而不是 item。
    """
    if context == "weapon" and getattr(type_class, "equippable_as_weapon", 0):
        return ["weapon"]
    if context == "armor" and getattr(type_class, "equippable_as_armor", 0):
        return ["armor"]

    raw = getattr(type_class, "class", None)
    if isinstance(raw, (list, tuple)):
        names = list(raw)
    elif raw:
        names = [raw]
    else:
        names = []

    if names and names != ["item"]:
        return names

    if rules is not None:
        is_a = getattr(type_class, "is_a", ()) or ()
        if not isinstance(is_a, (list, tuple)):
            is_a = [is_a]
        for parent in is_a:
            parent_class = rules.get(parent, "class")
            if not parent_class:
                continue
            parent_name = (
                parent_class[0]
                if isinstance(parent_class, (list, tuple))
                else parent_class
            )
            if parent_name in ("weapon", "armor"):
                return [parent_name]

    return names


def format_class_text(type_class, context, rules=None):
    """将 class 名称列表格式化为属性界面用的语音文本。"""
    class_names = display_class_names(type_class, context, rules)
    if not class_names:
        return []

    class_text = []
    for class_type in class_names:
        class_title = style.get(class_type, "title")
        if class_title:
            if isinstance(class_title, list):
                class_text.extend(class_title)
            else:
                class_text.append(str(class_title))
        else:
            class_text.append(str(class_type))
        class_text.extend(mp.COMMA)
    if class_text and class_text[-1] in mp.COMMA:
        class_text = class_text[:-1]
    return class_text


STAT_TTS_NAMES = {
    "hp": mp.HIT_POINTS,
    "hp_max": mp.MAX_HIT_POINTS,
    "hp_regen": mp.HP_REGEN_NAME,
    "mdg": mp.MELEE_DAMAGE_NAME,
    "rdg": mp.RANGED_DAMAGE_NAME,
    "mdf": mp.MELEE_DEFENSE_NAME,
    "rdf": mp.RANGED_DEFENSE_NAME,
    "menace": mp.MENACE,
    "menace_mult": mp.MENACE_MULT,
    "speed": mp.MOVE_SPEED,
    "sight_range": mp.SIGHT_RANGE_NAME,
    "mdg_range": mp.MELEE_RANGE_NAME,
    "rdg_range": mp.RANGED_RANGE_NAME,
    "mdg_cd": mp.MELEE_COOLDOWN_NAME,
    "rdg_cd": mp.RANGED_COOLDOWN_NAME,
            "mdg_ready": mp.MDG_READY,
    "rdg_ready": mp.RDG_READY,
    "damage_seq": mp.DAMAGE_SEQ_RDG,
    "mdg_seq_times": mp.DAMAGE_SEQ_MDG,
    "rdg_seq_times": mp.DAMAGE_SEQ_RDG,
    "mdg_cover": mp.MDG_COVER,
    "rdg_cover": mp.RDG_COVER,
    "mdg_dodge": mp.MDG_DODGE,
    "rdg_dodge": mp.RDG_DODGE,
    "mdg_minimal_range": mp.MDG_MINIMAL_RANGE,
    "rdg_minimal_range": mp.RDG_MINIMAL_RANGE,
    "mdg_splash": mp.MDG_SPLASH,
    "rdg_splash": mp.RDG_SPLASH,
    "mdg_splash_decay_min": mp.MDG_SPLASH_DECAY_MIN,
    "rdg_splash_decay_min": mp.RDG_SPLASH_DECAY_MIN,
    "mdg_radius": mp.MDG_RADIUS,
    "rdg_radius": mp.RDG_RADIUS,
    "minimal_mdg": mp.MDG_MINIMAL_DAMAGE,
    "minimal_rdg": mp.RDG_MINIMAL_DAMAGE,
    "minimal_damage": mp.MINIMAL_DAMAGE,
    "mana": mp.MANA_NAME,
    "mana_max": mp.MAX_MANA_NAME,
    "mana_regen": mp.MANA_REGEN_NAME,
    "gather_time": mp.GATHER_TIME_NAME,
    "gather_qty": mp.GATHER_QUANTITY_NAME,
    "gather_rate": mp.GATHER_RATE_NAME,
    "carry_capacity": mp.CARRY_CAPACITY_NAME,
    "production_type": mp.PRODUCTION_TYPE,
    "production_time": mp.PRODUCTION_TIME_NAME,
    "production_qty": mp.PRODUCTION_QUANTITY_NAME,
    "production_cost": mp.COST,
    "resource_type": mp.RESOURCE_TYPE,
    "extraction_time": mp.EXTRACTION_TIME,
    "extraction_qty": mp.EXTRACTION_QTY,
    "resource_volume_max": mp.RESOURCE_VOLUME_MAX,
    "resource_volume_start": mp.RESOURCE_VOLUME_START,
    "resource_regen": mp.RESOURCE_REGEN,
    "cost": mp.COST_NAME,
    "time_cost": mp.TIME_COST_NAME,
    "population_cost": mp.POPULATION_COST_NAME,
    "population_provided": mp.POPULATION_PROVIDED,
    "space": mp.SPACE,
    "heal": mp.HEAL_LEVEL,
    "heal_level": mp.HEAL_LEVEL,
    "heal_cd": mp.HEAL_CD,
    "heal_radius": mp.HEAL_RADIUS,
    "heal_range": mp.HEAL_RANGE,
    "heal_ready": mp.HEAL_READY,
    "harm": mp.HARM_LEVEL,
    "harm_level": mp.HARM_LEVEL,
    "harm_cd": mp.HARM_CD,
    "harm_radius": mp.HARM_RADIUS,
    "harm_range": mp.HARM_RANGE,
    "harm_ready": mp.HARM_READY,
    "hp_regen_cd": mp.HP_REGEN_CD,
    "hp_regen_ready": mp.HP_REGEN_READY,
    "mana_regen_cd": mp.MANA_REGEN_CD,
    "mana_regen_ready": mp.MANA_REGEN_READY,
    "buff_radius": mp.BUFF_RADIUS,
    "armor": mp.MELEE_DEFENSE,
    "damage": mp.MELEE_DAMAGE,
    "range": mp.RANGED_RANGE,
    "provides_build_field": mp.PROVIDES_BUILD_FIELD,
    "requires_build_field": mp.REQUIRES_BUILD_FIELD,
    "build_field_radius": mp.BUILD_FIELD_RADIUS,
    "build_mode": mp.BUILD_MODE,
    "self_constructs": mp.SELF_CONSTRUCTS,
    "build_sacrifices_worker": mp.BUILD_SACRIFICES_WORKER,
    "is_buildable_anywhere": mp.IS_BUILDABLE_ANYWHERE,
    "is_addon": mp.IS_ADDON,
    "addon_host_types": mp.ADDON_HOST_TYPES,
    "can_have_addon": mp.CAN_HAVE_ADDON,
    "addon_max": mp.ADDON_MAX,
    "build_field_persists": mp.BUILD_FIELD_PERSISTS,
    "build_field_spreads": mp.BUILD_FIELD_SPREADS,
    "build_field_spread_squares": mp.BUILD_FIELD_SPREAD_SQUARES,
    "requires_build_field_on_square": mp.REQUIRES_BUILD_FIELD_ON_SQUARE,
    "loses_power_without_field": mp.LOSES_POWER_WITHOUT_FIELD,
    "requires_deposit": mp.REQUIRES_DEPOSIT,
    # 等级成长属性（LEVEL_UP_STAT_ATTRS）
    "revival_time": mp.REVIVAL_TIME,
    "mdg_crit": mp.MDG_CRIT,
    "rdg_crit": mp.RDG_CRIT,
    "mdg_minimal_damage": mp.MDG_MINIMAL_DAMAGE,
    "rdg_minimal_damage": mp.RDG_MINIMAL_DAMAGE,
    "mdg_delay": mp.MDG_DELAY,
    "rdg_delay": mp.RDG_DELAY,
    "projectile_speed": mp.PROJECTILE_SPEED,
    "mdg_projectile_speed": mp.MDG_PROJECTILE_SPEED,
    "rdg_projectile_speed": mp.RDG_PROJECTILE_SPEED,
    "mdg_status_duration": mp.MDG_STATUS_DURATION,
    "rdg_status_duration": mp.RDG_STATUS_DURATION,
    "charge_mdg": mp.CHARGE_MDG,
    "charge_rdg": mp.CHARGE_RDG,
    "charge_mdg_dist": mp.CHARGE_MDG_DIST,
    "charge_rdg_dist": mp.CHARGE_RDG_DIST,
    "charge_mdg_min_dist": mp.CHARGE_MDG_MIN_DIST,
    "charge_rdg_min_dist": mp.CHARGE_RDG_MIN_DIST,
    "charge_mdg_cd": mp.CHARGE_MDG_CD,
    "charge_rdg_cd": mp.CHARGE_RDG_CD,
    "charge_mdg_splash": mp.CHARGE_MDG_SPLASH,
    "charge_rdg_splash": mp.CHARGE_RDG_SPLASH,
    "charge_mdg_radius": mp.CHARGE_MDG_RADIUS,
    "charge_rdg_radius": mp.CHARGE_RDG_RADIUS,
    "charge_mdg_splash_decay_min": mp.CHARGE_MDG_SPLASH_DECAY_MIN,
    "charge_rdg_splash_decay_min": mp.CHARGE_RDG_SPLASH_DECAY_MIN,
    "op_charge_mdg": mp.OP_CHARGE_MDG,
    "op_charge_rdg": mp.OP_CHARGE_RDG,
    "op_charge_mdg_dist": mp.OP_CHARGE_MDG_DIST,
    "op_charge_rdg_dist": mp.OP_CHARGE_RDG_DIST,
    "op_charge_mdg_cd": mp.OP_CHARGE_MDG_CD,
    "op_charge_rdg_cd": mp.OP_CHARGE_RDG_CD,
    "exp_dgf": mp.EXP_DGF,
    "exp_hp_cost": mp.EXP_HP_COST,
    "forced_damage": mp.FORCED_DAMAGE,
    "mdg_crit_rate": mp.MDG_CRIT_RATE,
    "rdg_crit_rate": mp.RDG_CRIT_RATE,
    "mdg_piercing": mp.MDG_PIERCING,
    "rdg_piercing": mp.RDG_PIERCING,
    "mdf_piercing": mp.MDF_PIERCING,
    "rdf_piercing": mp.RDF_PIERCING,
    "mdg_piercing_rate": mp.MDG_PIERCING_RATE,
    "rdg_piercing_rate": mp.RDG_PIERCING_RATE,
    "mdf_crit_rate": mp.MDF_CRIT_RATE,
    "rdf_crit_rate": mp.RDF_CRIT_RATE,
    "mdg_vs": mp.MDG_VS,
    "rdg_vs": mp.RDG_VS,
    "mdf_vs": mp.MDF_VS,
    "rdf_vs": mp.RDF_VS,
    "mdg_range_vs": mp.MDG_RANGE_VS,
    "rdg_range_vs": mp.RDG_RANGE_VS,
    "mdg_minimal_range_vs": mp.MDG_MINIMAL_RANGE_VS,
    "rdg_minimal_range_vs": mp.RDG_MINIMAL_RANGE_VS,
    "mdg_ready_vs": mp.MDG_READY_VS,
    "rdg_ready_vs": mp.RDG_READY_VS,
    "mdg_cd_vs": mp.MDG_CD_VS,
    "rdg_cd_vs": mp.RDG_CD_VS,
    "mdg_cover_vs": mp.MDG_COVER_VS,
    "rdg_cover_vs": mp.RDG_COVER_VS,
    "mdg_dodge_vs": mp.MDG_DODGE_VS,
    "rdg_dodge_vs": mp.RDG_DODGE_VS,
    "speed_vs": mp.SPEED_VS,
    "mdg_crit_vs": mp.MDG_CRIT_VS,
    "rdg_crit_vs": mp.RDG_CRIT_VS,
    "mdg_crit_rate_vs": mp.MDG_CRIT_RATE_VS,
    "rdg_crit_rate_vs": mp.RDG_CRIT_RATE_VS,
    "mdf_crit_rate_vs": mp.MDF_CRIT_RATE_VS,
    "rdf_crit_rate_vs": mp.RDF_CRIT_RATE_VS,
    "mdg_piercing_vs": mp.MDG_PIERCING_VS,
    "rdg_piercing_vs": mp.RDG_PIERCING_VS,
    "mdg_piercing_rate_vs": mp.MDG_PIERCING_RATE_VS,
    "rdg_piercing_rate_vs": mp.RDG_PIERCING_RATE_VS,
    "mdf_piercing_vs": mp.MDF_PIERCING_VS,
    "rdf_piercing_vs": mp.RDF_PIERCING_VS,
    "charge_mdg_vs": mp.CHARGE_MDG_VS,
    "charge_rdg_vs": mp.CHARGE_RDG_VS,
    "charge_mdg_splash_vs": mp.CHARGE_MDG_SPLASH_VS,
    "charge_rdg_splash_vs": mp.CHARGE_RDG_SPLASH_VS,
    "charge_mdg_splash_decay_min_vs": mp.CHARGE_MDG_SPLASH_DECAY_MIN_VS,
    "charge_rdg_splash_decay_min_vs": mp.CHARGE_RDG_SPLASH_DECAY_MIN_VS,
    "charge_mdg_radius_vs": mp.CHARGE_MDG_RADIUS_VS,
    "charge_rdg_radius_vs": mp.CHARGE_RDG_RADIUS_VS,
    "op_charge_mdg_vs": mp.OP_CHARGE_MDG_VS,
    "op_charge_rdg_vs": mp.OP_CHARGE_RDG_VS,
    "menace_vs": mp.MENACE_VS,
    "menace_mult_vs": mp.MENACE_MULT_VS,
    "cover_vs": mp.COVER_VS,
    "dodge_vs": mp.DODGE_VS,
    "kill_resource": mp.KILL_RESOURCE,
    "kill_resource_vs": mp.KILL_RESOURCE_VS,
}


def _normalize_title_part(part):
    text = str(part)
    if text.isdigit():
        return int(text)
    return text


def _style_title_msg(type_name):
    """将 rules/style 类型名转为 TTS 消息列表。"""
    title = style.get(type_name, "title")
    if title:
        if isinstance(title, list):
            return [_normalize_title_part(part) for part in title]
        return [_normalize_title_part(title)]
    return [str(type_name)]


def get_stat_tts_name(stat):
    """将属性名转换为 TTS 消息 ID 列表（具体语言由 ui/tts.txt 决定）。"""
    if stat in STAT_TTS_NAMES:
        return STAT_TTS_NAMES[stat]
    # ``mdg_vs.building`` / ``rdg_vs.ship`` — load_bonus / passenger_bonus dotted vs
    if isinstance(stat, str) and "." in stat:
        base, target = stat.split(".", 1)
        if base.endswith("_vs") and target:
            vs_const = getattr(mp, base.upper(), None)
            if vs_const is not None:
                vs_label = list(vs_const)
            else:
                root = base[:-3]
                root_name = STAT_TTS_NAMES.get(root, [root])
                vs_label = list(root_name) + list(mp.VERSUS)
            return vs_label + [" "] + _style_title_msg(target)
    # Plain ``mdg_vs`` / ``rdg_vs`` (effect bonus rows) — same labels as dotted form.
    if isinstance(stat, str) and stat.endswith("_vs"):
        vs_const = getattr(mp, stat.upper(), None)
        if vs_const is not None:
            return list(vs_const)
        root = stat[:-3]
        root_name = STAT_TTS_NAMES.get(root, [root])
        return list(root_name) + list(mp.VERSUS)
    if stat.startswith("gather_time_") and stat != "gather_time":
        deposit_type = stat[len("gather_time_"):]
        return list(mp.GATHER_TIME) + ["_"] + _style_title_msg(deposit_type)
    if stat.startswith("gather_qty_") and stat != "gather_qty":
        deposit_type = stat[len("gather_qty_"):]
        return list(mp.GATHER_QTY) + ["_"] + _style_title_msg(deposit_type)
    if stat.startswith("gather_rate_") and stat != "gather_rate":
        deposit_type = stat[len("gather_rate_"):]
        return list(mp.GATHER_RATE) + ["_"] + _style_title_msg(deposit_type)
    if stat.startswith("carry_capacity_") and stat != "carry_capacity":
        deposit_type = stat[len("carry_capacity_"):]
        return list(mp.CARRY_CAPACITY) + ["_"] + _style_title_msg(deposit_type)
    if stat == "food_deposit_qty":
        return _style_title_msg("resource3") + list(mp.FOOD_DEPOSIT_QTY)
    return [stat]


class AttributeUtils:
    def __init__(self, parent):
        self.parent = parent

    def _get_stat_tts_name(self, stat):
        """将属性名转换为 TTS 消息 ID 列表。"""
        return get_stat_tts_name(stat)

    def _is_precision_stat(self, stat):
        """判断属性是否需要除以PRECISION来显示正确数值"""
        # 这些属性在游戏内部以PRECISION为单位存储，显示时需要除以PRECISION
        precision_stats = {
            "hp", "hp_max", "mana", "mana_max",
            "mdg", "rdg", "mdf", "rdf",
            "mdg_range", "rdg_range",
            "speed", "sight_range",
            "gather_qty", "production_qty",
            "minimal_damage",
            "mdg_crit", "rdg_crit",
            "mdg_piercing", "rdg_piercing",
            "mdg_cover", "rdg_cover",
            "mdg_dodge", "rdg_dodge",
        }
        if isinstance(stat, str):
            base = stat.split(".", 1)[0] if "." in stat else stat
            # ``*_vs`` / ``mdg_vs.building``: match effect_bonus_parse (root in
            # rules.precision_properties → stored × PRECISION).
            if base.endswith("_vs"):
                from ..worldupgrade.effect_bonus_parse import _rules_stat_sets

                precision, _ = _rules_stat_sets()
                return base[:-3] in precision
            if base in precision_stats:
                return True
        return stat in precision_stats


RULES_DETAIL_ATTRS = (
    "can_train",
    "can_build",
    "can_upgrade_to",
    "can_research",
    "can_advance",
    "can_use_tech",
    "can_use_skill",
    "can_gather_deposit",
    "can_gather_building",
)


def class_attr_for_detail(unit_class, attr):
    """从 rules 类读取详情界面需要的能力属性（避开 Building 上的 @property）。"""
    if attr == "can_train":
        return rules.class_can_train(unit_class)
    if attr in RULES_DETAIL_ATTRS:
        return _raw_class_attr(unit_class, attr, ())
    value = getattr(unit_class, attr, None)
    if isinstance(value, property):
        return None
    return value


def gather_type_names(unit):
    """矿床与可采集建筑类型名合并列表（与属性界面显示顺序一致）。"""
    model = getattr(unit, "model", unit)
    deposits = list(getattr(model, "can_gather_deposit", None) or [])
    buildings = list(getattr(model, "can_gather_building", None) or [])
    if "all" in deposits and "all" in buildings:
        return ["all"]
    seen = set()
    merged = []
    for name in deposits + buildings:
        if name not in seen:
            seen.add(name)
            merged.append(name)
    return merged


NAVIGABLE_ITEM_TYPES = frozenset({
    "CAN_TRAIN_ITEMS",
    "CAN_BUILD_ITEMS",
    "CAN_USE_TECH_ITEMS",
    "CAN_USE_SKILL_ITEMS",
    "CAN_RESEARCH_ITEMS",
    "CAN_ADVANCE_ITEMS",
    "CAN_UPGRADE_TO_ITEMS",
    "CAN_GATHER_ITEMS",
    "CAN_GATHER_DEPOSIT_ITEMS",
    "CAN_GATHER_BUILDING_ITEMS",
    "AVAILABLE_WEAPONS_ITEMS",
    "INVENTORY_ITEMS",
    "VS_ITEMS",
    "EFFECT_ITEMS",
})


def _is_comma_tts_part(part):
    return part == mp.COMMA or part == mp.COMMA[0]


def normalize_nav_item(item):
    """可左右导航子项：内容内用空格分隔，逗号仅留给 (n/m) 计数。"""
    if not isinstance(item, list):
        return [str(item)]
    result = []
    for part in item:
        if _is_comma_tts_part(part):
            if result and result[-1] != " ":
                result.append(" ")
        elif part == " ":
            if result and result[-1] != " ":
                result.append(" ")
        elif isinstance(part, list):
            nested = normalize_nav_item(part)
            if nested:
                if result and result[-1] != " ":
                    result.append(" ")
                result.extend(nested)
        else:
            result.append(part)
    while result and result[0] == " ":
        result.pop(0)
    while result and result[-1] == " ":
        result.pop()
    return result