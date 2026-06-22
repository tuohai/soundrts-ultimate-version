"""

效果描述格式化模块

"""



import re



from .. import msgparts as mp

from ..lib.nofloat import PRECISION

from ..lib.msgs import nb2msg, nb2msg_float, format_signed_number

from ..definitions import style, rules
from ..worldskill import Skill
from .utils import normalize_nav_item





class EffectFormatter:

    def __init__(self, parent):

        self.parent = parent



    @staticmethod

    def _msg(*parts):

        result = []

        for part in parts:

            if isinstance(part, list):

                result.extend(part)

            else:

                result.append(part)

        return result



    def _append_effect_stat(self, parts, stat, value, precision=False):
        if value is None or value == 0 or value == "":
            return
        parts.extend(self.parent._get_stat_tts_name(stat))
        if precision:
            parts.extend(nb2msg_float(value / PRECISION))
        elif isinstance(value, (int, float)):
            parts.extend(nb2msg_float(value))
        else:
            parts.append(str(value))
        parts.extend(mp.COMMA)

    @staticmethod
    def _strip_trailing_comma(parts):
        if parts and parts[-1] in mp.COMMA:
            return parts[:-1]
        return parts

    @staticmethod
    def _join_effect_segments(segments):
        if not segments:
            return []
        result = segments[0][:]
        for segment in segments[1:]:
            result.extend(mp.COMMA)
            result.extend(segment)
        return result

    def _effect_stat_segment(self, stat, value, precision=False):
        parts = []
        self._append_effect_stat(parts, stat, value, precision)
        return self._strip_trailing_comma(parts)

    def _format_deploy_effect_items(self, effect_args):
        """部署 class effect：每项参数单独一条，供属性界面逐项播报。"""
        parsed = Skill.parse_deploy_args(effect_args)
        if parsed is None:
            return []
        duration, nb, effect_type = parsed
        effect_cls = Skill._get_deploy_effect_class(effect_type)
        if effect_cls is None:
            return []

        items = []
        header = list(mp.PLACE_EFFECT)
        title = style.get(effect_type, "title")
        if title:
            header.extend(title)
        else:
            header.append(str(effect_type))
        if nb > 1:
            header.extend(["×"] + nb2msg(nb))
        items.append(header)

        harm_level = getattr(effect_cls, "harm_level", 0) or 0
        heal_level = getattr(effect_cls, "heal_level", 0) or 0
        if harm_level > 0:
            items.append(self._effect_stat_segment("harm_level", harm_level, precision=False))
            harm_radius = getattr(effect_cls, "harm_radius", 0) or 0
            if harm_radius:
                items.append(self._effect_stat_segment("harm_radius", harm_radius, precision=True))
            harm_ready = getattr(effect_cls, "harm_ready", 0) or 0
            if harm_ready:
                items.append(self._effect_stat_segment("harm_ready", harm_ready / 1000))
        elif heal_level > 0:
            items.append(self._effect_stat_segment("heal_level", heal_level, precision=False))
            heal_radius = getattr(effect_cls, "heal_radius", 0) or 0
            if heal_radius:
                items.append(self._effect_stat_segment("heal_radius", heal_radius, precision=True))

        if duration:
            items.append(
                list(mp.LASTING)
                + nb2msg_float(duration / PRECISION)
                + mp.SECONDS
            )
        return items

    def _format_deploy_effect(self, effect_args):
        return self._join_effect_segments(self._format_deploy_effect_items(effect_args))

    def _format_deploy_effect_attribute_rows(self, effect_args):
        parsed = Skill.parse_deploy_args(effect_args)
        if parsed is None:
            return []
        duration, nb, effect_type = parsed
        effect_cls = Skill._get_deploy_effect_class(effect_type)
        if effect_cls is None:
            return []

        header = list(mp.PLACE_EFFECT)
        title = style.get(effect_type, "title")
        if title:
            header.extend(title)
        else:
            header.append(str(effect_type))
        if nb > 1:
            header.extend(["×"] + nb2msg(nb))

        rows = [("", header, ())]
        harm_level = getattr(effect_cls, "harm_level", 0) or 0
        heal_level = getattr(effect_cls, "heal_level", 0) or 0
        if harm_level > 0:
            rows.append(("", mp.HARM_LEVEL, nb2msg_float(harm_level)))
            harm_radius = getattr(effect_cls, "harm_radius", 0) or 0
            if harm_radius:
                rows.append(("", mp.HARM_RADIUS, nb2msg_float(harm_radius / PRECISION)))
            harm_ready = getattr(effect_cls, "harm_ready", 0) or 0
            if harm_ready:
                rows.append(("", mp.HARM_READY, nb2msg_float(harm_ready / 1000) + mp.SECONDS))
        elif heal_level > 0:
            rows.append(("", mp.HEAL_LEVEL, nb2msg_float(heal_level)))
            heal_radius = getattr(effect_cls, "heal_radius", 0) or 0
            if heal_radius:
                rows.append(("", mp.HEAL_RADIUS, nb2msg_float(heal_radius / PRECISION)))
        if duration:
            rows.append(("", ["持续"], nb2msg_float(duration / PRECISION) + mp.SECONDS))
        return rows

    @staticmethod
    def _coerce_bonus_value(value):
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            text = value.strip()
            if not text or " " in text:
                return None
            if text.endswith("%"):
                return float(text[:-1])
            try:
                return int(text) if "." not in text else float(text)
            except ValueError:
                return None
        return None

    @staticmethod
    def _coerce_int(value, default=0):
        """Rules effect 参数常以字符串存储，比较/运算前需转为整数。"""
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return default
            try:
                return int(float(text))
            except ValueError:
                return default
        return default

    def _format_bonus_value_parts(self, stat, value):
        if stat in ("cost", "production_cost") and isinstance(value, str) and " " in value.strip():
            return self._format_list_resource_bonus_parts(stat, value)
        coerced = self._coerce_bonus_value(value)
        if coerced is None or coerced == 0:
            return []
        if stat in ("time_cost", "production_time"):
            value_text = format_signed_number(coerced / 1000, as_float=True) + mp.SECONDS
        elif self.parent._is_precision_stat(stat):
            value_text = format_signed_number(coerced / PRECISION, as_float=True)
        else:
            value_text = format_signed_number(int(coerced))
        if coerced > 0:
            return ["+"] + value_text
        return value_text

    def _format_list_resource_bonus_parts(self, stat, value):
        parts = []
        for i, token in enumerate(value.split()):
            coerced = self._coerce_bonus_value(token)
            if coerced is None or coerced == 0:
                continue
            resource_title = style.get(f"resource{i + 1}", "title")
            if resource_title:
                if isinstance(resource_title, list):
                    parts.extend(resource_title)
                else:
                    parts.append(str(resource_title))
            if coerced > 0:
                parts.extend(["+"])
            parts.extend(format_signed_number(int(coerced)))
        return parts

    def _format_apply_bonus_effect_attribute_rows(self, effect_args):
        rows = []
        for stat in effect_args:
            if not stat:
                continue
            stat_name = self.parent._get_stat_tts_name(stat)
            text = list(mp.APPLY) + stat_name + list(mp.BONUS)
            rows.append(("", text, ()))
        return rows

    def _format_bonus_effect_attribute_rows(self, effect_args):
        rows = []
        for i in range(0, len(effect_args), 2):
            if i + 1 >= len(effect_args):
                break
            stat = effect_args[i]
            value = effect_args[i + 1]
            stat_name = self.parent._get_stat_tts_name(stat)
            value_parts = self._format_bonus_value_parts(stat, value)
            if value_parts:
                rows.append(("", stat_name, value_parts))
        return rows

    def _format_phase_bonus_attribute_rows(self, phase_bonus):
        return self._format_bonus_effect_attribute_rows(list(phase_bonus or []))

    def _phase_target_title_msg(self, token):
        from .utils import _style_title_msg
        return _style_title_msg(token)

    def _format_phase_targets_text(self, phase_targets):
        if not phase_targets:
            return None
        segments = []
        for target in phase_targets:
            token = str(target)
            excluded = token.startswith("-")
            if excluded:
                token = token[1:]
            title = self._phase_target_title_msg(token)
            if excluded:
                segments.append(list(mp.PHASE_EXCEPT_PREFIX) + title + list(mp.PHASE_EXCEPT_SUFFIX))
            else:
                segments.append(title)
        text = []
        for index, segment in enumerate(segments):
            if index > 0:
                text.extend(mp.COMMA)
            text.extend(segment)
        return text or None

    def _format_summon_effect_segments(self, effect_args):
        if len(effect_args) < 2:
            return []
        duration = effect_args[0]
        try:
            duration_display = int(duration) if not isinstance(duration, int) else duration
        except (TypeError, ValueError):
            duration_display = duration
        segments = []
        nb = 1
        i = 1
        while i < len(effect_args):
            token = effect_args[i]
            if re.match(r"^[0-9]+$", str(token)):
                nb = int(token)
                i += 1
                continue
            unit_type = token
            unit_title = style.get(unit_type, "title")
            segment = []
            if unit_title:
                segment.extend(unit_title)
            else:
                segment.append(str(unit_type))
            segment.extend(["×"] + nb2msg(nb))
            if duration_display:
                segment.extend(mp.LASTING + nb2msg(duration_display) + mp.SECONDS)
            segments.append(segment)
            nb = 1
            i += 1
        return segments

    def _format_summon_effect_attribute_rows(self, effect_args):
        segments = self._format_summon_effect_segments(effect_args)
        return [("", mp.SUMMON, segment) for segment in segments]

    def _format_buff_effect_segment(self, buff_name):
        buff_cls = rules.unit_class(buff_name)
        buff_title = style.get(buff_name, "title")
        name = buff_title if buff_title else [str(buff_name)]
        value = []
        if buff_cls is not None:
            stat = getattr(buff_cls, "stat", "") or ""
            stats = stat if isinstance(stat, (list, tuple)) else [stat]
            percentages = getattr(buff_cls, "percentage", 0)
            if not isinstance(percentages, (list, tuple)):
                percentages = [percentages] * len(stats)
            for idx, stat_name in enumerate(stats):
                if not stat_name:
                    continue
                pct = self._coerce_int(percentages[idx] if idx < len(percentages) else 0)
                if pct:
                    if value:
                        value.extend(mp.COMMA)
                    value.extend(self.parent._get_stat_tts_name(stat_name))
                    value.extend(["+" if pct > 0 else "-"])
                    value.extend(nb2msg(abs(int(pct))))
                    value.append("%")
            duration = getattr(buff_cls, "duration", 0) or 0
            if duration:
                if value:
                    value.extend(mp.COMMA)
                value.extend(
                    mp.LASTING + nb2msg(int(duration) // PRECISION) + mp.SECONDS
                )
        return name, value if value else name

    def _format_buffs_effect_attribute_rows(self, effect_args):
        rows = []
        for buff_name in effect_args:
            name, value = self._format_buff_effect_segment(buff_name)
            rows.append(("", name, value if value else name))
        return rows

    @staticmethod
    def effect_attribute_rows_to_items(effect_rows):
        """将效果属性行转为左右导航子项列表。"""
        items = []
        for _, name, value in effect_rows:
            item = []
            if name:
                if isinstance(name, list):
                    item.extend(name)
                else:
                    item.append(str(name))
            if value:
                if item:
                    item.append(" ")
                if isinstance(value, list):
                    item.extend(value)
                else:
                    item.append(str(value))
            if item:
                items.append(normalize_nav_item(item))
        return items

    def _format_effect_attribute_rows(self, effect_def):
        """技能/科技/时代详情：将单条效果定义拆为多行属性（供左右导航）。"""
        if not effect_def or not isinstance(effect_def, list) or not effect_def:
            return []
        try:
            effect_type = effect_def[0]
            effect_args = effect_def[1:]
            if effect_type == "deploy":
                return self._format_deploy_effect_attribute_rows(effect_args)
            if effect_type == "bonus":
                return self._format_bonus_effect_attribute_rows(effect_args)
            if effect_type == "summon":
                return self._format_summon_effect_attribute_rows(effect_args)
            if effect_type == "buffs":
                return self._format_buffs_effect_attribute_rows(effect_args)
            if effect_type == "apply_bonus":
                return self._format_apply_bonus_effect_attribute_rows(effect_args)
            flat = self._format_effect_description(effect_def)
            if flat:
                return [("", flat, ())]
        except Exception:
            pass
        return []

    def _format_summon_effect(self, effect_args):

        """与 lang_add_units / _execute_summon 一致：duration 后接 数量 单位 …"""

        segments = self._format_summon_effect_segments(effect_args)
        if not segments:
            return []
        result = list(mp.SUMMON) + segments[0]
        for extra in segments[1:]:
            result.extend(mp.COMMA)
            result.extend(list(mp.SUMMON) + extra)
        return result



    def _format_buffs_effect(self, effect_args):

        parts = []

        for buff_name in effect_args:

            buff_cls = rules.unit_class(buff_name)

            buff_title = style.get(buff_name, "title")

            if buff_title:

                parts.extend(buff_title)

            else:

                parts.append(str(buff_name))

            if buff_cls is not None:

                stat = getattr(buff_cls, "stat", "") or ""

                stats = stat if isinstance(stat, (list, tuple)) else [stat]

                percentages = getattr(buff_cls, "percentage", 0)

                if not isinstance(percentages, (list, tuple)):

                    percentages = [percentages] * len(stats)

                for idx, stat_name in enumerate(stats):

                    if not stat_name:

                        continue

                    pct = self._coerce_int(percentages[idx] if idx < len(percentages) else 0)

                    if pct:

                        parts.extend(self.parent._get_stat_tts_name(stat_name))

                        parts.extend(["+" if pct > 0 else "-"])

                        parts.extend(nb2msg(abs(int(pct))))

                        parts.append("%")

                duration = getattr(buff_cls, "duration", 0) or 0

                if duration:

                    parts.extend(

                        mp.LASTING

                        + nb2msg(int(duration) // PRECISION)

                        + mp.SECONDS

                    )

            if buff_name != effect_args[-1]:

                parts.extend(mp.COMMA)

        return parts


    def _format_burst_effect(self, effect_def):
        parsed = Skill.parse_burst_args(effect_def)
        if parsed is None:
            return []
        attack_type, times, _interval, window, delays = parsed
        parts = ["连击"] + nb2msg(times) + ["次"]
        parts.extend(mp.COMMA)
        parts.extend(self.parent._get_stat_tts_name(attack_type))
        if window:
            parts.extend(mp.COMMA)
            parts.extend(["持续"])
            parts.extend(nb2msg_float(window))
            parts.extend(mp.SECONDS)
        if delays:
            parts.extend(mp.COMMA)
            parts.extend(["自定义节奏"])
        return parts



    def _format_effect_description(self, effect_def):

        """格式化效果描述为可读的文本"""

        if not effect_def:

            return []



        try:

            if isinstance(effect_def, list) and len(effect_def) > 0:

                effect_type = effect_def[0]

                effect_args = effect_def[1:]



                if effect_type == "bonus":

                    bonus_text = []

                    for i in range(0, len(effect_args), 2):

                        if i + 1 < len(effect_args):

                            stat = effect_args[i]

                            value = effect_args[i + 1]



                            stat_name = self.parent._get_stat_tts_name(stat)
                            value_parts = self._format_bonus_value_parts(stat, value)
                            if value_parts:
                                bonus_text.extend(stat_name)
                                bonus_text.extend(value_parts)

                            if i + 2 < len(effect_args):

                                bonus_text.extend(mp.COMMA)

                    return bonus_text



                elif effect_type == "deploy":

                    return self._format_deploy_effect(effect_args)

                elif effect_type == "summon":

                    return self._format_summon_effect(effect_args)



                elif effect_type == "buffs":

                    return self._format_buffs_effect(effect_args)


                elif effect_type == "burst":

                    return self._format_burst_effect(effect_def)



                elif effect_type == "heal":

                    if len(effect_args) >= 1:

                        heal_amount = self._coerce_int(effect_args[0])

                        display_amount = heal_amount * 1000

                        amount_text = nb2msg_float(display_amount)

                        return list(mp.HEAL) + ["+"] + amount_text



                elif effect_type == "damage":

                    if len(effect_args) >= 1:

                        damage_amount = self._coerce_int(effect_args[0])

                        display_amount = damage_amount * 1000

                        amount_text = nb2msg_float(display_amount)

                        return list(mp.DAMAGE) + amount_text



                elif effect_type == "resurrection":

                    if len(effect_args) >= 1:

                        count = self._coerce_int(effect_args[0])

                        return list(mp.RESURRECT_MAX) + nb2msg(count) + list(mp.UNITS)



                elif effect_type == "raise_dead":

                    if len(effect_args) >= 1:

                        duration = self._coerce_int(effect_args[0])

                        unit_types = effect_args[1:] if len(effect_args) > 1 else []

                        result = list(mp.RAISE_DEAD)

                        if unit_types:

                            result.extend(mp.TYPE_COLON)

                            unique_types = []

                            for unit_type in unit_types:

                                if unit_type not in unique_types:

                                    unique_types.append(unit_type)

                            result.extend([", ".join(unique_types)])

                        if duration > 0:

                            result.extend(mp.LASTING + nb2msg(duration // 60) + mp.MINUTES)

                        return result



                elif effect_type == "conversion":

                    return list(mp.CONVERT_ENEMY)



                elif effect_type == "apply_bonus":
                    parts = []
                    for stat in effect_args:
                        if not stat:
                            continue
                        stat_name = self.parent._get_stat_tts_name(stat)
                        segment = list(mp.APPLY) + stat_name + list(mp.BONUS)
                        if parts:
                            parts.append(" ")
                        parts.extend(segment)
                    return parts



                else:

                    result = [effect_type.replace("_", " ")]

                    if effect_args:

                        limited_args = effect_args[:3]

                        for arg in limited_args:

                            if isinstance(arg, (int, float)) and arg > 0:

                                result.extend(nb2msg(arg))

                            else:

                                result.append(str(arg))

                        if len(effect_args) > 3:

                            result.append("...")

                    return result



            return []



        except Exception as e:

            print(f"Error formatting effect description: {e}")

            return [str(effect_def)]


