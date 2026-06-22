def ground_or_air(t):
    """返回 'ground' 或 'air'。如果 t == 'water'，则认为是 'ground'。"""
    return "ground" if t == "water" else t


def to_float(s) -> float:
    """
    将字符串 s 转为 float，如果异常则返回 0.0
    """
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0


DIPLOMACY_TAGS = frozenset({"enemy", "allied", "neutral", "non_neutral"})


def split_target_tags(target_type):
    """将 target_type 拆成包含标签与排除标签（-tag）。"""
    if not target_type:
        return [], []
    inclusions = []
    exclusions = []
    for t in target_type:
        if not isinstance(t, str):
            inclusions.append(t)
            continue
        if t.startswith("-") and len(t) > 1:
            exclusions.append(t[1:])
        elif t.startswith("-"):
            continue
        else:
            inclusions.append(t)
    return inclusions, exclusions


def _target_has_positive_tag(target, tag):
    """目标是否匹配单个正向标签（类型名或类别）。"""
    if getattr(target, "type_name", "") == tag:
        return True
    if tag == "healable" and getattr(target, "is_healable", False):
        return True
    if tag == "repairable" and getattr(target, "is_repairable", False):
        return True
    if tag == "building" and getattr(target, "is_a_building", False):
        return True
    if tag in ("air", "ground"):
        return ground_or_air(getattr(target, "airground_type", "ground")) == tag
    if tag == "water":
        return getattr(target, "airground_type", "ground") == "water"
    if tag == "unit" and getattr(target, "is_a_unit", False):
        return True
    if tag == "undead" and getattr(target, "is_undead", False):
        return True
    return False


def _inclusion_tag_fails(target, tag):
    """AND 型包含列表：某一类别约束不满足时返回 True。"""
    if (
        tag == "healable"
        and not getattr(target, "is_healable", False)
        or tag == "repairable"
        and not getattr(target, "is_repairable", False)
        or tag == "building"
        and not getattr(target, "is_a_building", False)
        or tag in ("air", "ground")
        and ground_or_air(getattr(target, "airground_type", "ground")) != tag
        or tag == "unit"
        and not getattr(target, "is_a_unit", False)
        or tag == "undead"
        and not getattr(target, "is_undead", False)
    ):
        return True
    return False


def has_target_type(target, target_type, source=None):
    # 如果target_type为空，则认为匹配任何目标
    if not target_type:
        return True

    inclusions, exclusions = split_target_tags(target_type)
    target_type_name = getattr(target, "type_name", "")
    type_inclusions = [t for t in inclusions if t not in DIPLOMACY_TAGS]

    if type_inclusions:
        if target_type_name in type_inclusions:
            pass
        else:
            for t in type_inclusions:
                if _inclusion_tag_fails(target, t):
                    return False

    for ex in exclusions:
        if ex in DIPLOMACY_TAGS:
            continue
        if _target_has_positive_tag(target, ex):
            return False
    return True


def matches_attack_targets(target, targets, airground_target_type=None):
    """mdg_targets / rdg_targets：正向标签 OR 匹配，排除标签 -tag 过滤。"""
    if not targets:
        return True

    inclusions, exclusions = split_target_tags(targets)
    ag = (
        airground_target_type
        if airground_target_type is not None
        else ground_or_air(getattr(target, "airground_type", "ground"))
    )
    target_type_name = getattr(target, "type_name", "")
    type_inclusions = [t for t in inclusions if t not in DIPLOMACY_TAGS]

    if type_inclusions:
        matched = (
            ag in type_inclusions
            or ("building" in type_inclusions and getattr(target, "is_a_building", False))
            or ("unit" in type_inclusions and getattr(target, "is_a_unit", False))
            or target_type_name in type_inclusions
            or ("healable" in type_inclusions and getattr(target, "is_healable", False))
            or ("undead" in type_inclusions and getattr(target, "is_undead", False))
            or (
                "water" in type_inclusions
                and getattr(target, "airground_type", "ground") == "water"
            )
            or ("repairable" in type_inclusions and getattr(target, "is_repairable", False))
        )
        if not matched:
            return False

    for ex in exclusions:
        if ex in DIPLOMACY_TAGS:
            continue
        if _target_has_positive_tag(target, ex):
            return False
    return True


def matches_heal_targets(target, targets):
    """heal_target_type：正向标签 OR 匹配，排除 -tag；使用原始 airground_type。"""
    if not targets:
        return True
    ag = getattr(target, "airground_type", "ground")
    return matches_attack_targets(target, targets, airground_target_type=ag)


def _player_is_hostile(source_player, other_player):
    return (
        source_player is not None
        and other_player is not None
        and source_player.player_is_a_hostile_enemy(other_player)
    )


def passes_harm_diplomacy_filter(harm_target_type, source_player, other_player):
    """harm_target_type 中的外交标签：enemy/non_neutral=非中立敌对，neutral=中立，allied=友军。"""
    if not harm_target_type:
        return True
    inclusions, exclusions = split_target_tags(harm_target_type)

    if "allied" in inclusions:
        if source_player is None or other_player is None:
            return False
        if source_player.player_is_an_enemy(other_player):
            return False
    wants_hostile = "enemy" in inclusions or "non_neutral" in inclusions
    wants_neutral = "neutral" in inclusions
    if wants_hostile or wants_neutral:
        if other_player is None:
            return False
        is_neutral = bool(getattr(other_player, "neutral", False))
        is_hostile = _player_is_hostile(source_player, other_player)
        if wants_hostile and wants_neutral:
            if not (is_hostile or is_neutral):
                return False
        elif wants_hostile:
            if not is_hostile:
                return False
        elif wants_neutral:
            if not is_neutral:
                return False

    for ex in exclusions:
        if ex == "allied":
            if (
                source_player is not None
                and other_player is not None
                and not source_player.player_is_an_enemy(other_player)
            ):
                return False
        elif ex in ("enemy", "non_neutral"):
            if _player_is_hostile(source_player, other_player):
                return False
        elif ex == "neutral":
            if other_player is not None and getattr(other_player, "neutral", False):
                return False
    return True


def skill_can_harm(caster, skill_cls, victim):
    """技能 harm_target_type 过滤：未配置时保持旧行为（仅敌人）。"""
    if victim is None or not getattr(victim, "is_vulnerable", False):
        return False
    if getattr(victim, "player", None) is None or victim.hp <= 0:
        return False

    tags = getattr(skill_cls, "harm_target_type", ()) or ()
    if not tags:
        return hasattr(caster, "is_an_enemy") and caster.is_an_enemy(victim)

    if not passes_harm_diplomacy_filter(
        tags,
        getattr(caster, "player", None),
        getattr(victim, "player", None),
    ):
        return False

    if "water" in tags and getattr(victim, "airground_type", "ground") == "water":
        return True

    return has_target_type(victim, tags)
