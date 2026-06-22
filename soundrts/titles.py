"""头衔定义：奖章军衔阶梯 + 成就荣誉头衔（模组可覆盖 titles.txt）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .definitions import preprocess
from .faction_progress import achievements_per_faction_enabled, normalize_faction_key
from .lib.log import warning

KIND_RANK = "rank"
KIND_HONOR = "honor"


@dataclass
class TitleDef:
    id: str
    title: List[int] = field(default_factory=list)
    kind: str = KIND_RANK
    medals: int = 0
    loadout_slots: int = 0
    faction: Optional[str] = None


_titles: Dict[str, TitleDef] = {}
_title_order: List[str] = []
_rank_ladder: List[TitleDef] = []


def load_titles(*strings):
    global _titles, _title_order, _rank_ladder
    _titles = {}
    _title_order = []
    _rank_ladder = []
    for s in strings:
        if s and s.strip():
            _read_titles_layer(s)
    _rebuild_rank_ladder()


def get_title_defs() -> Dict[str, TitleDef]:
    return dict(_titles)


def get_title_order() -> List[str]:
    return list(_title_order)


def get_title(title_id: str) -> Optional[TitleDef]:
    return _titles.get(title_id)


def title_exists(title_id: str) -> bool:
    return title_id in _titles


def _ladder_for_faction(faction=None) -> List[TitleDef]:
    if not achievements_per_faction_enabled():
        return list(_rank_ladder)
    faction_key = normalize_faction_key(faction)
    faction_ranks = [
        rank
        for rank in _rank_ladder
        if rank.faction and normalize_faction_key(rank.faction) == faction_key
    ]
    if faction_ranks:
        return faction_ranks
    return [rank for rank in _rank_ladder if not rank.faction]


def get_rank_ladder(faction=None) -> List[TitleDef]:
    return list(_ladder_for_faction(faction))


def get_current_rank(medals: int, faction=None) -> Optional[TitleDef]:
    current = None
    for rank in _ladder_for_faction(faction):
        if medals >= rank.medals:
            current = rank
        else:
            break
    return current


def get_next_rank(medals: int, faction=None) -> Optional[TitleDef]:
    for rank in _ladder_for_faction(faction):
        if medals < rank.medals:
            return rank
    return None


def medals_until_next_rank(medals: int, faction=None) -> Optional[int]:
    nxt = get_next_rank(medals, faction)
    if nxt is None:
        return None
    return max(0, nxt.medals - medals)


def get_loadout_slots(medals: int, faction=None) -> int:
    rank = get_current_rank(medals, faction)
    if rank is None:
        return 0
    return max(0, int(rank.loadout_slots))


def get_rank_index(rank_id: str, faction=None) -> int:
    for index, rank in enumerate(_ladder_for_faction(faction)):
        if rank.id == rank_id:
            return index
    return -1


def rank_at_least(medals: int, required_rank_id: Optional[str], faction=None) -> bool:
    if not required_rank_id:
        return True
    required = get_title(required_rank_id)
    if required is None or required.kind != KIND_RANK:
        return True
    current = get_current_rank(medals, faction)
    if current is None:
        return False
    return get_rank_index(current.id, faction) >= get_rank_index(required_rank_id, faction)


def ranks_newly_reached(medals_before: int, medals_after: int, faction=None) -> List[TitleDef]:
    if medals_after <= medals_before:
        return []
    result = []
    for rank in _ladder_for_faction(faction):
        if rank.medals <= 0:
            continue
        if medals_before < rank.medals <= medals_after:
            result.append(rank)
    return result


def _rebuild_rank_ladder():
    global _rank_ladder
    ranks = [t for t in _titles.values() if t.kind == KIND_RANK]
    ranks.sort(key=lambda t: (t.medals, _title_order.index(t.id) if t.id in _title_order else 999))
    _rank_ladder = ranks


def _read_titles_layer(s: str):
    s = preprocess(s)
    current: Optional[TitleDef] = None
    for line in s.split("\n"):
        words = line.split()
        if not words:
            continue
        if words[0] == "clear":
            _titles.clear()
            _title_order.clear()
            current = None
            continue
        if words[0] == "def":
            if len(words) < 2:
                warning("title def missing id")
                continue
            current = TitleDef(id=words[1])
            _titles[current.id] = current
            if current.id not in _title_order:
                _title_order.append(current.id)
            continue
        if current is None:
            warning("'def <title_id>' is missing (check titles.txt)")
            continue
        if words[0] == "title" and len(words) >= 2 and words[1].isdigit():
            current.title = [int(words[1])]
        elif words[0] == "kind" and len(words) >= 2:
            if words[1] in (KIND_RANK, KIND_HONOR):
                current.kind = words[1]
        elif words[0] == "medals" and len(words) >= 2 and words[1].isdigit():
            current.medals = int(words[1])
            current.kind = KIND_RANK
        elif words[0] == "loadout_slots" and len(words) >= 2 and words[1].isdigit():
            current.loadout_slots = int(words[1])
        elif words[0] in ("faction", "race") and len(words) >= 2:
            current.faction = words[1]
