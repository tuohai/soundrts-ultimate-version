"""任务目标语音前缀（F9 与 add_objective 共用）。"""
from . import msgparts as mp
from .lib.msgs import nb2msg


def collect_planned_objective_numbers(triggers):
    """从地图触发器树中统计计划添加的主要/可选目标编号。"""
    primary = set()
    secondary = set()

    def walk(node):
        if not node:
            return
        if isinstance(node, (list, tuple)):
            if node and isinstance(node[0], str):
                cmd = node[0]
                if cmd == "add_objective" and len(node) >= 2:
                    primary.add(str(node[1]))
                elif cmd == "register_objective":
                    for n in node[1:]:
                        primary.add(str(n))
                elif cmd == "add_secondary_objective" and len(node) >= 2:
                    secondary.add(str(node[1]))
            for item in node:
                walk(item)

    for trigger in triggers or ():
        if not trigger:
            continue
        if isinstance(trigger, (list, tuple)) and len(trigger) >= 2:
            walk(trigger[0])
            walk(trigger[1])
        else:
            walk(trigger)
    return primary, secondary


def should_announce_objective_number(player, optional=False):
    """多个同类型目标时才读出序号。"""
    if optional:
        planned = getattr(player, "_planned_secondary_objective_numbers", set()) or set()
        if len(planned) > 1:
            return True
        objectives = list(getattr(player, "objectives", {}).values())
        visible_secondary = sum(
            1 for o in objectives if getattr(o, "optional", False)
        )
        return visible_secondary > 1

    planned = getattr(player, "_planned_primary_objective_numbers", set()) or set()
    if len(planned) > 1:
        return True

    registered_primary = len(
        getattr(player, "_required_objective_numbers", set()) or set()
    )
    if registered_primary > 1:
        return True
    objectives = list(getattr(player, "objectives", {}).values())
    visible_primary = sum(
        1 for o in objectives if not getattr(o, "optional", False)
    )
    return visible_primary > 1


def objective_prefix_msg(prefix, number, show_number):
    msg = list(prefix)
    if show_number:
        try:
            msg += nb2msg(int(number))
        except (TypeError, ValueError):
            pass
    msg += mp.COLON
    return msg


def objective_sort_key(objective):
    number = getattr(objective, "number", "")
    try:
        number_key = int(number)
    except (TypeError, ValueError):
        number_key = number
    return (getattr(objective, "optional", False), number_key)


def flatten_objective_description(items):
    """将目标描述转为可播报的消息片段。"""
    result = []
    items = items or []
    all_digits = all(isinstance(x, str) and x.isdigit() for x in items)
    if all_digits:
        return list(items)

    for it in items:
        if isinstance(it, str) and it.isdigit():
            result += nb2msg(int(it))
        elif isinstance(it, list):
            inner = it
            inner_all_digits = all(isinstance(s, str) and s.isdigit() for s in inner)
            if inner_all_digits:
                result.extend(inner)
            else:
                for sub in inner:
                    if isinstance(sub, str) and sub.isdigit():
                        result += nb2msg(int(sub))
                    else:
                        result.append(sub)
        else:
            result.append(it)
    return result


def collect_objective_entries(world, player):
    """收集 F9 可逐条浏览的全部任务目标（地图目标 + 玩家目标）。"""
    entries = []
    world_objective = getattr(world, "objective", None)
    if world_objective:
        entries.append(
            mp.OBJECTIVE
            + flatten_objective_description(world_objective)
            + mp.PERIOD
        )

    objectives = getattr(player, "objectives", None) or {}
    if objectives:
        for o in sorted(objectives.values(), key=objective_sort_key):
            optional = getattr(o, "optional", False)
            prefix = mp.SECONDARY_OBJECTIVE if optional else mp.PRIMARY_OBJECTIVE
            show_number = should_announce_objective_number(player, optional=optional)
            entries.append(
                objective_prefix_msg(prefix, o.number, show_number)
                + flatten_objective_description(o.description)
            )
    return entries


def navigate_objective_index(current, inc, count):
    """F9 / Shift+F9 循环浏览目标。current=-1 表示尚未开始浏览。"""
    if count <= 0:
        return -1
    if current < 0:
        return 0 if inc > 0 else count - 1
    return (current + inc) % count
