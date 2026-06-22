"""
StarCraft 风格建造规则属性显示
provides_build_field / requires_build_field / build_mode / self_constructs 等
"""

from .. import definitions
from .. import msgparts as mp
from ..lib.msgs import nb2msg
from ..lib.nofloat import PRECISION
from ..world_build_rules import (
    build_field_radius_meters,
    build_field_radius_squares,
    build_field_spread_squares,
)


class BuildRulesAttributes:
    def __init__(self, main_interface):
        self.main_interface = main_interface

    def _model(self, u):
        return getattr(u, "model", u)

    def _format_build_field(self, value):
        """建造场类型显示名：mod 在 style.txt 定义 build_field_<类型> 的 title。"""
        if not value or value == "0":
            return None
        title = definitions.style.get(
            f"build_field_{value}", "title", warn_if_not_found=False
        )
        if title:
            if isinstance(title, list):
                return list(title)
            return [str(title)]
        return [str(value)]

    def _format_build_mode(self, value):
        modes = {
            "assisted": mp.BUILD_MODE_ASSISTED,
            "place_and_leave": mp.BUILD_MODE_PLACE_AND_LEAVE,
            "sacrifice": mp.BUILD_MODE_SACRIFICE,
        }
        return list(modes.get(value, [str(value)]))

    def _format_type_list(self, names):
        if not names:
            return None
        if isinstance(names, str):
            names = (names,)
        text = []
        for name in names:
            title = definitions.style.get(name, "title")
            if title:
                if isinstance(title, list):
                    text.extend(title)
                else:
                    text.append(str(title))
            else:
                text.append(str(name))
            text.extend(mp.COMMA)
        if text and text[-1] in mp.COMMA:
            text = text[:-1]
        return text or None

    def add_build_rules_attributes(self, u, attrs):
        """添加星际争霸风格建造规则相关属性。"""
        model = self._model(u)

        provides = getattr(model, "provides_build_field", "") or ""
        if provides and provides != "0":
            field_text = self._format_build_field(provides)
            if field_text:
                attrs.append(("", mp.PROVIDES_BUILD_FIELD, field_text))

        requires = getattr(model, "requires_build_field", "") or ""
        if requires and requires != "0":
            field_text = self._format_build_field(requires)
            if field_text:
                attrs.append(("", mp.REQUIRES_BUILD_FIELD, field_text))

        radius_m = build_field_radius_meters(model)
        if radius_m > 0:
            attrs.append(
                ("", mp.BUILD_FIELD_RADIUS, nb2msg(radius_m // PRECISION))
            )
        else:
            radius = getattr(model, "build_field_radius", 0) or 0
            if radius:
                radius_squares = build_field_radius_squares(model)
                if radius_squares > 0:
                    attrs.append(("", mp.BUILD_FIELD_RADIUS, nb2msg(radius_squares)))

        build_mode = getattr(model, "build_mode", "") or ""
        if build_mode:
            attrs.append(("", mp.BUILD_MODE, self._format_build_mode(build_mode)))

        if getattr(model, "self_constructs", 0):
            attrs.append(("", mp.SELF_CONSTRUCTS, mp.YES))

        if getattr(model, "build_sacrifices_worker", 0):
            attrs.append(("", mp.BUILD_SACRIFICES_WORKER, mp.YES))

        if getattr(model, "build_field_persists", 0):
            attrs.append(("", mp.BUILD_FIELD_PERSISTS, mp.YES))

        if getattr(model, "build_field_spreads", 0):
            attrs.append(("", mp.BUILD_FIELD_SPREADS, mp.YES))
            spread_squares = build_field_spread_squares(model)
            if spread_squares > 0:
                attrs.append(("", mp.BUILD_FIELD_SPREAD_SQUARES, nb2msg(spread_squares)))

        if getattr(model, "requires_build_field_on_square", 0):
            attrs.append(("", mp.REQUIRES_BUILD_FIELD_ON_SQUARE, mp.YES))

        if getattr(model, "loses_power_without_field", 0):
            attrs.append(("", mp.LOSES_POWER_WITHOUT_FIELD, mp.YES))

        requires_deposit = getattr(model, "requires_deposit", "") or ""
        if requires_deposit and requires_deposit != "0":
            deposit_text = self._format_type_list((requires_deposit,))
            if deposit_text:
                attrs.append(("", mp.REQUIRES_DEPOSIT, deposit_text))

        unit_classes = getattr(model, "class", ()) or ()
        if getattr(model, "is_buildable_anywhere", 0) and "building" in unit_classes:
            attrs.append(("", mp.IS_BUILDABLE_ANYWHERE, mp.YES))

        if getattr(model, "is_addon", 0):
            attrs.append(("", mp.IS_ADDON, mp.YES))

        host_types = getattr(model, "addon_host_types", ()) or ()
        host_text = self._format_type_list(host_types)
        if host_text:
            attrs.append(("", mp.ADDON_HOST_TYPES, host_text))

        can_have = getattr(model, "can_have_addon", ()) or ()
        can_have_text = self._format_type_list(can_have)
        if can_have_text:
            attrs.append(("", mp.CAN_HAVE_ADDON, can_have_text))

        addon_max = getattr(model, "addon_max", 0) or 0
        if addon_max > 1:
            attrs.append(("", mp.ADDON_MAX, nb2msg(addon_max)))
