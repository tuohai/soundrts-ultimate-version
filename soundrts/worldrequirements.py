"""requirements 列表的解析与判定。

支持两种写法（可混用）::

    requirements stables workshop
    requirements castle_age any_buildings 2 castle_age_buildings

``any_buildings <n> <group>_buildings``：玩家至少拥有该分组中的 ``<n>`` 种
不同建筑（``player.has``，含 ``is_a``）。

分组键 = 去掉 ``_buildings`` 后缀（``castle_age_buildings`` → ``castle_age``）。
成员 = 所有 ``class building`` 且其*简单* requirements 中包含该键的类型
（例如马厩写 ``requirements castle_age`` 即进入 ``castle_age_buildings``）。

请写 ``*_buildings`` 后缀，避免与 phase 名直接混淆。
子句参数不会触发 ``units_auto_upgrade``。
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Tuple, Union

ANY_BUILDINGS = "any_buildings"
BUILDINGS_GROUP_SUFFIX = "_buildings"

# ("has", type_name) | ("any_buildings", count, group_name)
RequirementClause = Union[
    Tuple[str, str],
    Tuple[str, int, str],
]

_buildings_of_group_cache: dict = {}


def clear_caches():
    _buildings_of_group_cache.clear()


def resolve_building_group(group_name: str) -> str:
    """``castle_age_buildings`` → ``castle_age``；无后缀则原样返回。"""
    name = str(group_name)
    if name.endswith(BUILDINGS_GROUP_SUFFIX) and len(name) > len(BUILDINGS_GROUP_SUFFIX):
        return name[: -len(BUILDINGS_GROUP_SUFFIX)]
    return name


def parse_requirement_clauses(tokens: Optional[Sequence]) -> List[RequirementClause]:
    """把 requirements 原始 token 列表解析为子句列表。"""
    if not tokens:
        return []
    result: List[RequirementClause] = []
    i = 0
    n = len(tokens)
    while i < n:
        tok = tokens[i]
        if tok == ANY_BUILDINGS:
            if i + 2 >= n:
                i += 1
                continue
            count_tok = tokens[i + 1]
            group = tokens[i + 2]
            try:
                count = int(count_tok)
            except (TypeError, ValueError):
                i += 1
                continue
            if count < 0:
                count = 0
            result.append((ANY_BUILDINGS, count, str(group)))
            i += 3
        else:
            result.append(("has", str(tok)))
            i += 1
    return result


def simple_requirement_names(tokens: Optional[Sequence]) -> List[str]:
    """仅返回简单类型名要求（不含 any_buildings 子句及其参数）。"""
    return [c[1] for c in parse_requirement_clauses(tokens) if c[0] == "has"]


def has_phase_as_simple_requirement(tokens: Optional[Sequence], phase_name: str) -> bool:
    """目标形态是否把某时代名写成简单 requirement（用于 units_auto_upgrade）。"""
    return phase_name in simple_requirement_names(tokens)


def buildings_of_group(group_name: str) -> List[str]:
    """按分组名收集建筑：简单 requirements 含该键的 building（稳定排序）。"""
    from . import definitions

    rules = definitions.rules
    key = resolve_building_group(group_name)
    cache_key = (id(rules), key)
    cached = _buildings_of_group_cache.get(cache_key)
    if cached is not None:
        return list(cached)

    names = []
    for name in rules.classnames():
        cls = rules.unit_class(name)
        if cls is None:
            continue
        if not getattr(cls, "is_a_building", False):
            continue
        reqs = getattr(cls, "requirements", ()) or ()
        if key in simple_requirement_names(reqs):
            names.append(name)
    names.sort()
    _buildings_of_group_cache[cache_key] = tuple(names)
    return list(names)


def buildings_of_phase(phase_name: str) -> List[str]:
    """兼容旧名：与 buildings_of_group 相同。"""
    return buildings_of_group(phase_name)


def count_owned_buildings_of_group(player, group_name: str) -> int:
    owned = 0
    for name in buildings_of_group(group_name):
        if player.has(name):
            owned += 1
    return owned


def clause_is_satisfied(player, clause: RequirementClause) -> bool:
    kind = clause[0]
    if kind == "has":
        return player.has(clause[1])
    if kind == ANY_BUILDINGS:
        _, count, group = clause
        return count_owned_buildings_of_group(player, group) >= count
    return False


def requirements_satisfied(player, tokens: Optional[Sequence]) -> bool:
    for clause in parse_requirement_clauses(tokens):
        if not clause_is_satisfied(player, clause):
            return False
    return True


def missing_requirement_clauses(
    player, tokens: Optional[Sequence]
) -> List[RequirementClause]:
    return [
        c for c in parse_requirement_clauses(tokens) if not clause_is_satisfied(player, c)
    ]


def format_clause_titles(clause: RequirementClause) -> list:
    """把一个子句格式化为 voice/title 片段列表（不含 'requires' / 'and'）。"""
    from .definitions import style
    from .lib.msgs import nb2msg

    kind = clause[0]
    if kind == "has":
        return list(style.get(clause[1], "title") or [])
    if kind == ANY_BUILDINGS:
        _, count, group = clause
        key = resolve_building_group(group)
        msg = []
        msg += style.get("parameters", "any") or []
        msg += nb2msg(count)
        msg += style.get("parameters", "buildings_of") or []
        group_title = style.get(group, "title", warn_if_not_found=False) or []
        if group_title:
            msg += list(group_title)
        else:
            msg += style.get(key, "title") or []
        return msg
    return []


def belonging_phase_names(model) -> List[str]:
    """从简单 requirements 中取出时代（phase）名，供属性界面显示「所属时代」。"""
    from . import definitions
    from .worldphase import is_a_phase

    rules = definitions.rules
    names = []
    for req in simple_requirement_names(getattr(model, "requirements", ()) or ()):
        cls = rules.unit_class(req)
        if is_a_phase(cls):
            names.append(req)
    return names


def format_belonging_phase_titles(model) -> list:
    """所属时代的语音标题片段（可多时代，用空列表表示无）。"""
    from .definitions import style

    msg = []
    for phase in belonging_phase_names(model):
        title = style.get(phase, "title") or []
        if title:
            if msg:
                msg += style.get("parameters", "and") or []
            msg += list(title)
    return msg


def iter_unmet_building_candidates(player, group_name: str) -> Iterable[str]:
    """AI 用：尚未拥有的该分组建筑，按总成本升序。"""
    from . import definitions

    rules = definitions.rules
    missing = []
    for name in buildings_of_group(group_name):
        if player.has(name):
            continue
        cls = rules.unit_class(name)
        cost = sum(getattr(cls, "cost", ()) or ()) if cls is not None else 0
        missing.append((cost, name))
    missing.sort()
    for _, name in missing:
        yield name
