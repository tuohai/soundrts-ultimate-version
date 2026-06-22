"""卡牌定义加载（第二期）。战前使用见第三期。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .definitions import preprocess, rules
from .faction_progress import achievements_per_faction_enabled, definition_matches_faction
from .lib.log import warning

SpawnEntry = Tuple[str, int]
ResourceEntry = Tuple[int, int]
TrainBonusEntry = Tuple[str, int]


@dataclass
class CardDef:
    id: str
    title: List[int] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    spawns: List[SpawnEntry] = field(default_factory=list)
    resources: List[ResourceEntry] = field(default_factory=list)
    grant_charges: int = 1
    min_rank: Optional[str] = None
    faction: Optional[str] = None
    delay: int = 0  # 游戏时间（秒）；0 表示开局立即生效
    techs: List[str] = field(default_factory=list)
    train_bonuses: List[TrainBonusEntry] = field(default_factory=list)


_cards: Dict[str, CardDef] = {}
_card_order: List[str] = []


def load_cards(*strings):
    global _cards, _card_order
    _cards = {}
    _card_order = []
    for s in strings:
        if s and s.strip():
            _read_cards_layer(s)


def get_card_defs() -> Dict[str, CardDef]:
    return dict(_cards)


def get_card_order(faction=None) -> List[str]:
    if not achievements_per_faction_enabled():
        return list(_card_order)
    return [
        card_id
        for card_id in _card_order
        if definition_matches_faction(get_card(card_id).faction if get_card(card_id) else None, faction)
    ]


def get_card(card_id: str) -> Optional[CardDef]:
    return _cards.get(card_id)


def _read_cards_layer(s: str):
    s = preprocess(s)
    current: Optional[CardDef] = None
    for line in s.split("\n"):
        words = line.split()
        if not words:
            continue
        if words[0] == "clear":
            _cards.clear()
            _card_order.clear()
            current = None
            continue
        if words[0] == "def":
            if len(words) < 2:
                warning("card def missing id")
                continue
            current = CardDef(id=words[1])
            _cards[current.id] = current
            if current.id not in _card_order:
                _card_order.append(current.id)
            continue
        if current is None:
            warning("'def <card_id>' is missing (check cards.txt)")
            continue
        if words[0] == "title":
            if len(words) >= 2 and words[1].isdigit():
                current.title = [int(words[1])]
        elif words[0] == "tags":
            current.tags = words[1:]
        elif words[0] == "spawn":
            if len(words) >= 3 and words[-1].isdigit():
                qty = int(words[-1])
                unit = " ".join(words[1:-1])
                current.spawns.append((unit, qty))
        elif words[0] == "train_bonus":
            if len(words) >= 3 and words[-1].isdigit():
                qty = int(words[-1])
                unit = " ".join(words[1:-1])
                current.train_bonuses.append((unit, qty))
        elif words[0] == "resource":
            if len(words) >= 3:
                index = rules.parse_resource_type(words[1])
                if index is None:
                    try:
                        index = int(words[1])
                    except ValueError:
                        warning("card resource: bad index %s", words[1])
                        continue
                if words[2].isdigit():
                    current.resources.append((index, int(words[2])))
        elif words[0] == "grant_charges" and len(words) >= 2 and words[1].isdigit():
            current.grant_charges = max(1, int(words[1]))
        elif words[0] == "min_rank" and len(words) >= 2:
            current.min_rank = words[1]
        elif words[0] in ("faction", "race") and len(words) >= 2:
            current.faction = words[1]
        elif words[0] == "delay" and len(words) >= 2 and words[1].isdigit():
            current.delay = max(0, int(words[1]))
        elif words[0] == "delay_minutes" and len(words) >= 2 and words[1].isdigit():
            current.delay = max(0, int(words[1]) * 60)
        elif words[0] == "tech" and len(words) >= 2:
            current.techs.extend(words[1:])


def card_exists(card_id: str) -> bool:
    return card_id in _cards
