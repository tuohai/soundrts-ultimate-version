"""阵型详情：当前/可用阵型列表，以及 class formation 的形状与效果。"""

from .. import msgparts as mp
from ..clientmedia import voice
from ..definitions import style
from ..lib.msgs import format_signed_number, nb2msg, nb2msg_float
from ..lib.nofloat import PRECISION
from ..world_formation import (
    _bonus_set,
    _layout_kind,
    _parse_bonus,
    formation_spec,
    formation_type_names,
    formations_enabled,
    unit_can_form,
    unit_formation_name,
    unit_formation_rank,
)

_SHAPE_TTS = {
    "line": [5845],
    "box": [5846],
    "staggered": [5847],
    "flank": [5848],
    "ring": mp.FORMATION_SHAPE_RING,
    "arc": mp.FORMATION_SHAPE_ARC,
}
_RANK_TTS = {
    "melee": mp.FORMATION_RANK_MELEE,
    "ranged": mp.FORMATION_RANK_RANGED,
    "siege": mp.FORMATION_RANK_SIEGE,
}
_VS_LABELS = (
    ("mdg_vs", mp.MDG_VS),
    ("rdg_vs", mp.RDG_VS),
    ("mdf_vs", mp.MDF_VS),
    ("rdf_vs", mp.RDF_VS),
)
_FLAT_LABELS = (
    ("mdg", mp.MELEE_DAMAGE),
    ("rdg", mp.RANGE_DAMAGE),
    ("mdf", mp.MELEE_DEFENSE),
    ("rdf", mp.RANGE_DEFENSE),
    ("speed", mp.SPEED),
)


def style_title_parts(name):
    title = style.get(name, "title") if name else None
    if title:
        if isinstance(title, list):
            return list(title)
        return [str(title)]
    return [str(name or "")]


def format_formation_bonus(bonus):
    """Return spoken parts for an absolute PRECISION value or ``('pct', n)``."""
    parsed = _parse_bonus(bonus)
    if not _bonus_set(parsed):
        return None
    if isinstance(parsed, tuple) and parsed[0] == "pct":
        n = int(parsed[1])
        sign = "+" if n > 0 else ""
        return [f"{sign}{n}%"]
    return format_signed_number(parsed / PRECISION, as_float=True)


def _meters(value):
    return nb2msg_float(int(value or 0) / PRECISION)


def _rank_parts(rank):
    label = _RANK_TTS.get(str(rank or "").strip().lower())
    if label:
        return list(label)
    return style_title_parts(rank)


def _shape_parts(shape):
    kind = str(shape or "line").strip().lower()
    return list(_SHAPE_TTS.get(kind, [kind]))


def formation_nav_items(names=None):
    names = list(names if names is not None else formation_type_names())
    return [style_title_parts(name) for name in names]


def build_formation_detail_attrs(type_name):
    """Attribute rows for one ``class formation`` (shape, spacing, combat/speed)."""
    spec = formation_spec(type_name)
    if spec is None:
        return []
    attrs = []
    title = style_title_parts(spec.get("name") or type_name)
    attrs.append(("", mp.CURRENT_FORMATION, title))
    intro = style.get(type_name, "intro")
    if intro:
        if isinstance(intro, list):
            attrs.append(("?", mp.INTRO, intro))
        else:
            attrs.append(("?", mp.INTRO, [str(intro)]))
    kind = _layout_kind(spec)
    attrs.append(("", mp.FORMATION_SHAPE, _shape_parts(kind)))
    attrs.append(("", mp.FORMATION_SPACING, _meters(spec.get("spacing"))))
    attrs.append(("", mp.FORMATION_RANK_GAP, _meters(spec.get("rank_gap"))))
    if kind == "flank" or int(spec.get("flank_gap") or 0) > 0:
        attrs.append(("", mp.FORMATION_FLANK_GAP, _meters(spec.get("flank_gap"))))
    radius = int(spec.get("radius") or 0)
    if radius > 0:
        attrs.append(("", mp.FORMATION_RADIUS, _meters(radius)))
    rings = int(spec.get("rings") or 0)
    if rings > 1:
        attrs.append(("", mp.FORMATION_RINGS, nb2msg(rings)))
    ring_gap = int(spec.get("ring_gap") or 0)
    if ring_gap > 0:
        attrs.append(("", mp.FORMATION_RING_GAP, _meters(ring_gap)))
    if kind in ("ring", "arc") or int(spec.get("arc_span") or 0):
        span = int(spec.get("arc_span") or 0) or (360 if kind == "ring" else 180)
        attrs.append(("", mp.FORMATION_ARC_SPAN, nb2msg(span)))
    ring_rank = str(spec.get("ring_rank") or "in").lower()
    if kind in ("ring", "arc"):
        inner = ring_rank in ("out", "outer", "outside")
        attrs.append(
            (
                "",
                mp.FORMATION_RING_RANK,
                list(mp.FORMATION_OUTER if inner else mp.FORMATION_INNER),
            )
        )
    rank_parts = []
    for rank in spec.get("ranks") or ():
        if rank_parts:
            rank_parts.extend(mp.COMMA)
        rank_parts.extend(_rank_parts(rank))
    if rank_parts:
        attrs.append(("", mp.FORMATION_RANK, rank_parts))
    attrs.append(
        ("", mp.FORMATION_KEEP_PACE, list(mp.YES if spec.get("keep_pace") else mp.NO))
    )
    for key, label in _FLAT_LABELS:
        spoken = format_formation_bonus(spec.get(key, 0))
        if spoken:
            attrs.append(("", label, spoken))
    for key, label in _VS_LABELS:
        vs = spec.get(key) or {}
        items = []
        for target, bonus in vs.items():
            spoken = format_formation_bonus(bonus)
            if not spoken:
                continue
            item = list(mp.VERSUS) + [" "] + style_title_parts(target) + [" "] + spoken
            items.append(item)
        if not items:
            continue
        if len(items) == 1:
            attrs.append(("", label, items[0]))
        else:
            attrs.append(("", label, ("VS_ITEMS", items)))
    return attrs


def add_formation_attributes(u, attrs):
    """Current formation, navigable available types, and this unit's rank."""
    try:
        if not formations_enabled() or not unit_can_form(u):
            return
    except Exception:
        return
    names = formation_type_names()
    if not names:
        return
    current = unit_formation_name(u)
    attrs.append(("", mp.CURRENT_FORMATION, style_title_parts(current)))
    items = formation_nav_items(names)
    if items:
        attrs.append(("", mp.AVAILABLE_FORMATIONS, ("AVAILABLE_FORMATIONS_ITEMS", items)))
    attrs.append(("", mp.FORMATION_RANK, _rank_parts(unit_formation_rank(u))))


class FormationDetail:
    def __init__(self, parent):
        self.parent = parent

    def _show_formation_detail(self, type_name):
        attrs = build_formation_detail_attrs(type_name)
        if not attrs:
            voice.item(mp.NO_SUCH_ATTRIBUTE)
            return
        self.parent._saved_attributes_state = {
            "unit": self.parent._attributes_screen_unit,
            "attrs": self.parent._attributes_screen_attrs,
            "index": self.parent._current_attribute_index,
            "sub_index": self.parent._current_sub_item_index,
            "sub_items": self.parent._current_attribute_sub_items,
        }
        self.parent._in_detail_attributes_screen = True
        self.parent._attributes_screen_attrs = attrs
        self.parent._current_attribute_index = 0
        self.parent._current_sub_item_index = 0
        self.parent._current_attribute_sub_items = []
        title = style_title_parts(type_name)
        voice.item(title + mp.ATTRIBUTES)
        self.parent.main_display._display_current_attribute()
        self.parent.key_bindings._setup_attributes_screen_bindings()
