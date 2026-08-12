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
        # Percent bonuses (``hp_max 10%``, ``speed -15%``): show +10%, never /PRECISION.
        if isinstance(value, str) and value.strip().endswith("%"):
            text = value.strip()
            try:
                pct = float(text[:-1])
            except ValueError:
                return []
            if pct == 0:
                return []
            # Keep one decimal only when needed (87.5%).
            if abs(pct - int(pct)) < 1e-9:
                num = format_signed_number(int(abs(pct)))
            else:
                num = format_signed_number(abs(pct), as_float=True)
            if pct > 0:
                return ["+"] + num + list(mp.PERCENT)
            return ["-"] + num + list(mp.PERCENT)
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
            if isinstance(token, str) and token.endswith("%"):
                try:
                    pct = float(token[:-1])
                except ValueError:
                    continue
                if pct == 0:
                    continue
                resource_title = style.get(f"resource{i + 1}", "title")
                if resource_title:
                    if isinstance(resource_title, list):
                        parts.extend(resource_title)
                    else:
                        parts.append(str(resource_title))
                if pct > 0:
                    parts.extend(["+"])
                else:
                    parts.extend(["-"])
                parts.extend(format_signed_number(int(abs(pct))))
                parts.extend(list(mp.PERCENT))
                continue
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
        from ..worldupgrade.effect_bonus_parse import split_effect_bonus_args

        # Drop trailing unit filters (``building`` etc.) appended from effect_bonus_targets.
        bonus_args, _targets = split_effect_bonus_args(list(effect_args or []))
        rows = []
        i = 0
        while i < len(bonus_args):
            stat = bonus_args[i]
            st = str(stat)
            if st.endswith("_vs"):
                if i + 2 >= len(bonus_args):
                    break
                target = bonus_args[i + 1]
                value = bonus_args[i + 2]
                stat_name = self.parent._get_stat_tts_name(stat)
                target_title = style.get(target, "title") or [str(target)]
                if not isinstance(target_title, list):
                    target_title = [str(target_title)]
                value_parts = self._format_bonus_value_parts(stat, value)
                if value_parts:
                    rows.append(("", list(stat_name) + list(mp.COMMA) + list(target_title), value_parts))
                i += 3
                continue
            if i + 1 >= len(bonus_args):
                break
            value = bonus_args[i + 1]
            # Applied at runtime; UI description comes from ``effect info`` (avoid "+1" noise).
            if st == "projectile_lead":
                i += 2
                continue
            # Multi-slot cost: ``cost -50% 0`` already in bonus_args as [cost, -50%, 0]?
            # split keeps them; _format_bonus_value_parts handles space-joined via list path
            # only when value is a string with spaces — cost slots are separate tokens.
            if st in ("cost", "production_cost", "storage_bonus", "resource_rewards"):
                values = [value]
                j = i + 2
                while j < len(bonus_args):
                    tok = bonus_args[j]
                    # next token looks like a value, not a new stat
                    from ..worldupgrade.effect_bonus_parse import is_effect_bonus_stat

                    if is_effect_bonus_stat(tok):
                        break
                    values.append(tok)
                    j += 1
                joined = " ".join(str(v) for v in values)
                stat_name = self.parent._get_stat_tts_name(stat)
                value_parts = self._format_bonus_value_parts(stat, joined)
                if value_parts:
                    rows.append(("", stat_name, value_parts))
                i = j
                continue
            stat_name = self.parent._get_stat_tts_name(stat)
            value_parts = self._format_bonus_value_parts(stat, value)
            if value_parts:
                rows.append(("", stat_name, value_parts))
            i += 2
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
            if effect_type == "info":
                return self._format_info_effect_attribute_rows(effect_args)
            flat = self._format_effect_description(effect_def)
            if flat:
                return [("", flat, ())]
        except Exception:
            pass
        return []

    def _format_info_effect_attribute_rows(self, effect_args):
        """Display-only tech/skill blurb: ``effect info <tts_id>…`` (no runtime apply)."""
        parts = []
        for arg in effect_args or []:
            if arg is None or arg == "":
                continue
            try:
                parts.append(int(str(arg)))
            except (TypeError, ValueError):
                title = style.get(arg, "title", warn_if_not_found=False)
                if title:
                    if isinstance(title, list):
                        parts.extend(title)
                    else:
                        parts.append(title)
                else:
                    parts.append(str(arg))
        if not parts:
            return []
        return [("", parts, ())]

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

                elif effect_type == "info":
                    rows = self._format_info_effect_attribute_rows(effect_args)
                    return rows[0][1] if rows else []

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


