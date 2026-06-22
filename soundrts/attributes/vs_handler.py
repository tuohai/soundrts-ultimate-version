"""
VS属性处理模块
"""

from .. import msgparts as mp
from ..lib.nofloat import PRECISION
from ..lib.msgs import nb2msg_float
from ..definitions import style


class VsHandler:
    def __init__(self, parent):
        self.parent = parent

    @staticmethod
    def _target_type_tts(target_type):
        target_title = style.get(target_type, "title")
        if target_title:
            if isinstance(target_title, list):
                return list(target_title)
            return [str(target_title)]
        return [str(target_type)]

    def _build_vs_item(self, target_types, value_suffix):
        combined = []
        for index, target_type in enumerate(target_types):
            if index > 0:
                combined.append(" ")
            combined.extend(self._target_type_tts(target_type))
        item = list(mp.VERSUS)
        if combined:
            item.append(" ")
            item.extend(combined)
        if value_suffix:
            item.append(" ")
            if isinstance(value_suffix, list):
                item.extend(value_suffix)
            else:
                item.append(str(value_suffix))
        return item

    def _group_vs_dict(
        self,
        vs_dict,
        precision_divide=False,
        divide_by_1000=False,
        min_positive=True,
        round_digits=None,
    ):
        grouped_targets = {}
        for target_type, value in vs_dict.items():
            if precision_divide:
                value_float = value / PRECISION
            elif divide_by_1000:
                value_float = value / 1000
            else:
                value_float = value
            if round_digits is not None:
                value_float = round(value_float, round_digits)
            if min_positive and value_float <= 0:
                continue
            if not min_positive and not value_float:
                continue
            if value_float not in grouped_targets:
                grouped_targets[value_float] = []
            grouped_targets[value_float].append(target_type)
        return grouped_targets

    def _append_vs_items(self, attrs, vs_msg, items):
        if not items:
            return
        if len(items) == 1:
            attrs.append(("", vs_msg, items[0]))
        else:
            attrs.append(("", vs_msg, ("VS_ITEMS", items)))

    @staticmethod
    def _vs_msg_for_attr(attr_name):
        if "mdg" in attr_name:
            vs_msg = mp.MDG_VS
        elif "rdg" in attr_name:
            vs_msg = mp.RDG_VS
        elif "mdf" in attr_name:
            vs_msg = mp.MDF_VS
        elif "rdf" in attr_name:
            vs_msg = mp.RDF_VS
        else:
            vs_msg = mp.VERSUS
        if "bonus" in attr_name:
            vs_msg = vs_msg + [" "] + mp.BONUS
        return vs_msg

    def add_grouped_vs_attribute(
        self,
        attrs,
        vs_dict,
        vs_msg,
        precision_divide=False,
        divide_by_1000=False,
        round_digits=None,
        value_suffix_fn=None,
        min_positive=True,
    ):
        """按数值分组的目标 vs 属性，多项时用左右键浏览。"""
        grouped = self._group_vs_dict(
            vs_dict,
            precision_divide=precision_divide,
            divide_by_1000=divide_by_1000,
            round_digits=round_digits,
            min_positive=min_positive,
        )
        items = []
        for value_float, target_types in grouped.items():
            if value_suffix_fn is not None:
                suffix = value_suffix_fn(value_float)
            else:
                suffix = nb2msg_float(value_float)
            items.append(self._build_vs_item(target_types, suffix))
        self._append_vs_items(attrs, vs_msg, items)

    def add_boolean_vs_attribute(self, attrs, vs_dict, vs_msg):
        """值为 True 的目标类型，每项单独一条。"""
        items = []
        for target_type, enabled in vs_dict.items():
            if not enabled:
                continue
            items.append(list(mp.VERSUS) + [" "] + self._target_type_tts(target_type))
        self._append_vs_items(attrs, vs_msg, items)

    def _add_vs_attribute(self, attrs, vs_dict, attr_name, precision_divide=False, divide_by_1000=False):
        """处理 mdg_vs / rdg_vs 等标准数值 vs 属性。

        负值用于 SC2 风格的护甲克制惩罚（例如对 sc_massive 的 -4），必须照常
        显示，因此这里 min_positive=False：只过滤 0，保留正负两种数值。
        """
        vs_msg = self._vs_msg_for_attr(attr_name)
        self.add_grouped_vs_attribute(
            attrs,
            vs_dict,
            vs_msg,
            precision_divide=precision_divide,
            divide_by_1000=divide_by_1000,
            min_positive=False,
        )
