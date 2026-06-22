#! .venv\Scripts\python.exe
from typing import Set

from soundrts.lib import log
from soundrts.lib.package import Package
from soundrts.paths import BASE_PACKAGE_PATH

log.add_console_handler()

from soundrts.definitions import Rules


class RulesForDoc(Rules):
    # 从 definitions.py 更新所有属性集合
    precision_properties: Set[str] = Rules.precision_properties.copy()
    precision_list_properties: Set[str] = Rules.precision_list_properties.copy()
    string_properties = Rules.string_properties.copy()
    int_properties = Rules.int_properties.copy()
    int_list_properties = Rules.int_list_properties.copy()
    string_list_properties = Rules.string_list_properties.copy()
    
    # 保持向后兼容的属性合并
    precision_properties.update(Rules.string_properties)


_s = ""
"""
stats
=====

.. contents::


"""


def pr(s=""):
    global _s
    _s += s + "\n\n"


def name(c, link=True):
    if rules.get(c, "name"):
        r = " ".join(rules.get(c, "name"))
    else:
        r = c
    if link:
        return "`" + r + "`_"
    return r


def desc(c):
    if rules.get(c, "desc"):
        return (" ".join(rules.get(c, "desc"))).replace(r"\n", "\n\n")
    else:
        return ""


def comma_join(lst, p):
    return p + " " + ", ".join(lst)


def _list(p, n, lst=None):
    if lst is None:
        lst = rules.get(c, n)
    if lst:
        return comma_join([name(_) for _ in lst], p)
    else:
        return ""


def cost(p, n):
    v = rules.get(c, n)
    if v:
        s = p
        lst = []
        if v[0]:
            lst += ["%s gold" % v[0]]
        if len(v) > 1 and v[1]:
            lst += ["%s wood" % v[1]]
        # 支持更多资源类型
        resource_names = ["gold", "wood", "stone", "food", "iron", "gems", "research", "energy"]
        for i in range(2, min(len(v), len(resource_names))):
            if v[i]:
                lst += ["%s %s" % (v[i], resource_names[i])]
        return s + " " + ", ".join(lst)
    else:
        return ""


def nb(u, n):
    n = float(n)
    if isinstance(u, tuple):
        if n <= 1:
            return u[0]
        else:
            return u[1]
    if n <= 1:
        if u.endswith("s"):
            return u[:-1]
    return u


def _int(p, n, u):
    v = rules.get(c, n)
    if v:
        s = p
        s += " {} {}".format(v, nb(u, v))
        return s
    else:
        return ""


def _sint(p, n, u):
    v = rules.get(c, n)
    if v:
        s = p
        s += " %i %s" % (v, nb(u, v))
        return s
    else:
        return ""


def _res(p, n):
    v = rules.get(c, n)
    if v:
        resource_names = ["gold", "wood", "stone", "food", "iron", "gems", "research", "energy"]
        parts = []
        for res in rules.get(c, n):
            if isinstance(res, int):
                parts.append(
                    resource_names[res]
                    if res < len(resource_names)
                    else f"resource{res + 1}"
                )
            else:
                parts.append(str(res))
        return p + " " + ", ".join(parts)
    else:
        return ""


def _percentage(p, n):
    """处理百分比属性"""
    v = rules.get(c, n)
    if v:
        if isinstance(v, str) and v.endswith('%'):
            return p + " " + v
        else:
            return p + " " + str(v)
    else:
        return ""


def _damage_info(damage_type="mdg"):
    """生成伤害信息描述"""
    damage = rules.get(c, damage_type)
    cooldown = rules.get(c, f"{damage_type}_cd")
    range_val = rules.get(c, f"{damage_type}_range")
    radius = rules.get(c, f"{damage_type}_radius")
    
    if damage:
        info = f"- {damage_type} attack: {damage} damage"
        if cooldown:
            info += f" every {cooldown} seconds"
        if range_val:
            info += f", range {range_val} meters"
        if radius:
            info += f", radius {radius} meters"
        return info
    return ""


def _armor_info():
    """生成护甲信息描述"""
    armor_name = rules.get(c, "armor")
    mdf = rules.get(c, "mdf")
    rdf = rules.get(c, "rdf")
    
    info = []
    if armor_name:
        info.append(f"- armor type: {armor_name}")
    if mdf:
        info.append(f"- melee defense: {mdf}")
    if rdf:
        info.append(f"- ranged defense: {rdf}")
    
    return "\n".join(info) if info else ""


def _special_abilities():
    """生成特殊能力描述"""
    abilities = []
    
    # 检查各种特殊能力
    if rules.get(c, "is_invisible"):
        abilities.append("invisible")
    if rules.get(c, "is_a_detector"):
        abilities.append("detects invisible units")
    if rules.get(c, "is_cloakable"):
        abilities.append("can cloak")
    if rules.get(c, "is_a_cloaker"):
        abilities.append("can cloak other units")
    if rules.get(c, "is_teleportable"):
        abilities.append("can be teleported")
    if rules.get(c, "is_a_gate"):
        abilities.append("teleportation gate")
    if rules.get(c, "can_repair"):
        abilities.append("can repair buildings")
    if rules.get(c, "can_repair_ships"):
        abilities.append("can repair ships")
    if rules.get(c, "auto_gather"):
        abilities.append("automatically gathers resources")
    if rules.get(c, "auto_repair"):
        abilities.append("automatically repairs buildings")
    
    return "- special abilities: " + ", ".join(abilities) if abilities else ""


def underline(s, u=","):
    return s + "\n" + u * len(s)


def kcost(c):
    r = 0
    if rules.get(c, "cost"):
        cost_list = rules.get(c, "cost")
        if len(cost_list) > 0:
            r += float(cost_list[0])
        if len(cost_list) > 1:
            r += float(cost_list[1]) * 1.01
    if not r:  # special units
        r += 1000  # end of list
    return (r, name(c))  # name as a secondary key


def trained_by(c):
    r = []
    for k in rules.classnames():
        can_train = rules.get(k, "can_train")
        if can_train:
            # 处理新的can_train字典格式
            if isinstance(can_train, dict):
                if c in can_train:
                    r.append(k)
            elif isinstance(can_train, list) and c in can_train:
                r.append(k)
    return sorted(r, key=kcost)


def can_use(c, t):
    if not rules.get(c, "can_use"):
        return []
    r = [k for k in rules.get(c, "can_use") if rules.get(k, "class") == [t]]
    return sorted(r, key=kcost)


def get_class_type(c):
    """获取对象的类型"""
    class_info = rules.get(c, "class")
    if class_info:
        return class_info[0] if isinstance(class_info, list) else class_info
    return "unknown"


rules = RulesForDoc()
base = Package.from_path(BASE_PACKAGE_PATH)
rules.load(base.open_text("rules.txt").read(), base.open_text("ui/rules_doc.txt").read())

# 更新分类以包含新的对象类型
for cat in (
    ("1. Units", ("worker", "soldier")),
    ("2. Buildings", ("building",)),
    ("3. Skills", ("skill",)),  # 将 ability 改为 skill
    ("4. Upgrades and research", ("upgrade",)),
    ("5. Items", ("item",)),  # 新增物品分类
    ("6. Weapons", ("weapon",)),  # 新增武器分类
    ("7. Armor", ("armor",)),  # 新增护甲分类
    ("8. Buffs", ("buff",)),  # 新增增益分类
    ("9. Ages (phases)", ("phase",)),
):
    pr(underline(cat[0], "^"))
    for c in sorted(rules.classnames(), key=kcost):
        class_type = get_class_type(c)
        if class_type not in cat[1]:
            continue
        pr(underline(name(c, link=False)))
        pr(desc(c))
        pr()
        pr(_list("- trained by: ", None, trained_by(c)))
        pr(_list("- requires:", "requirements"))
        pr(_int("- mana cost:", "mana_cost", "mana points"))
        pr(cost("- total cost:", "cost"))
        pr(_sint("- total food cost:", "food_cost", "rations"))
        pr(_int("- total time cost:", "time_cost", "seconds"))
        pr(_percentage("- time cost modifier:", "time_cost"))

        # 处理效果信息
        if rules.get(c, "effect"):
            effect = rules.get(c, "effect")
            if isinstance(effect, list) and len(effect) > 0:
                if effect[0] == "bonus":
                    pr("- effect: {} + {}".format(effect[1], effect[2]))
                elif effect[0] == "apply_bonus":
                    pr("- effect: applies the %s upgrade bonus of the unit" % effect[1])
                # 处理多个效果
                elif isinstance(effect[0], list):
                    for eff in effect:
                        if eff[0] == "bonus":
                            pr("- effect: {} + {}".format(eff[1], eff[2]))

        # 生命值和防御信息
        pr(_int("- health: ", "hp_max", "hit points"))
        pr(_int("- health regeneration: ", "hp_regen", "hit points per second"))
        pr(_int("- mana: ", "mana_max", "mana points"))
        pr(_int("- mana regeneration: ", "mana_regen", "mana points per second"))
        
        # 护甲信息
        armor_info = _armor_info()
        if armor_info:
            pr(armor_info)

        # 攻击信息
        mdg_info = _damage_info("mdg")
        if mdg_info:
            pr(mdg_info)
        rdg_info = _damage_info("rdg")
        if rdg_info:
            pr(rdg_info)

        # 其他属性
        pr(_int("- speed: ", "speed", ("meter per second", "meters per second")))
        pr(_int("- sight range: ", "sight_range", "meters"))
        pr(_sint("- population cost:", "population_cost", "units"))
        pr(_sint("- population provided:", "population_provided", "units"))
        pr(_sint("- transport capacity:", "transport_capacity", "units"))
        pr(_sint("- inventory capacity:", "inventory_capacity", "items"))
        pr(_res("- can store: ", "storable_resource_types"))
        
        # 建造和训练信息
        pr(_list("- can build:", "can_build"))
        can_train = rules.get(c, "can_train")
        if can_train:
            if isinstance(can_train, dict):
                train_list = [f"{unit} (x{count})" for unit, count in can_train.items()]
                pr("- can train: " + ", ".join(train_list))
            else:
                pr(_list("- can train:", "can_train"))
        
        pr(_list("- can research:", "can_research"))
        pr(_list("- can upgrade to:", "can_upgrade_to"))
        pr(_list("- can gather:", "can_gather"))
        pr(_list("- can change to:", "can_change_to"))
        pr(_list("- special abilities: ", None, can_use(c, "skill")))  # 更新为 skill
        
        # 特殊能力
        special_abilities = _special_abilities()
        if special_abilities:
            pr(special_abilities)
        
        # 高度奖励
        if rules.get(c, "bonus_height") == 1:
            pr("- have a height bonus (useful for sight and eventually attack range)")
        
        # 升级信息
        pr(_list("- potential improvements: ", None, can_use(c, "upgrade")))

stats = _s
