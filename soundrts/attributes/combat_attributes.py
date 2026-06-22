"""
战斗属性显示模块
处理攻击、防御、vs属性、地形修正、自爆等战斗相关属性
"""

from .. import msgparts as mp
from ..lib.nofloat import PRECISION
from ..lib.msgs import nb2msg, nb2msg_float
from ..definitions import style


class CombatAttributes:
    def __init__(self, main_interface):
        self.main_interface = main_interface
    
    def add_attack_defense_attributes(self, u, attrs):
        """添加攻击防御相关属性"""
        # 攻击间隔
        self.main_interface._add_bonus_attribute(attrs, u, "mdg_cd", "a", mp.MDG_CD, True)
        self.main_interface._add_bonus_attribute(attrs, u, "rdg_cd", "a", mp.RDG_CD, True)
        
        # 攻击射程
        self.main_interface._add_bonus_attribute(attrs, u, "mdg_range", "m", mp.MDG_RANGE, True)
        self.main_interface._add_bonus_attribute(attrs, u, "rdg_range", "r", mp.RANGED_RANGE, True)
        
        # 命中率和闪避率
        self.main_interface._add_bonus_attribute(attrs, u, "mdg_cover", "", mp.MDG_COVER, True)
        self.main_interface._add_bonus_attribute(attrs, u, "rdg_cover", "", mp.RDG_COVER, True)
        self.main_interface._add_bonus_attribute(attrs, u, "mdg_dodge", "", mp.MDG_DODGE, True)
        self.main_interface._add_bonus_attribute(attrs, u, "rdg_dodge", "", mp.RDG_DODGE, True)
        
        # 溅射伤害
        self.main_interface._add_bonus_attribute(attrs, u, "mdg_splash", "", mp.MDG_SPLASH, True)
        self.main_interface._add_bonus_attribute(attrs, u, "rdg_splash", "", mp.RDG_SPLASH, True)
        self.main_interface._add_bonus_attribute(attrs, u, "mdg_radius", "", mp.MDG_RADIUS, True)
        self.main_interface._add_bonus_attribute(attrs, u, "rdg_radius", "", mp.RDG_RADIUS, True)
    
    def add_charge_attributes(self, u, attrs):
        """添加冲锋相关属性"""
        # 冲锋伤害
        self.main_interface._add_bonus_attribute(attrs, u, "charge_mdg", "", mp.CHARGE_MDG, True)
        self.main_interface._add_bonus_attribute(attrs, u, "charge_rdg", "", mp.CHARGE_RDG, True)
        self.main_interface._add_bonus_attribute(attrs, u, "charge_mdg_cd", "", mp.CHARGE_MDG_CD, True)
        self.main_interface._add_bonus_attribute(attrs, u, "charge_rdg_cd", "", mp.CHARGE_RDG_CD, True)
        
        # 冲锋距离
        if hasattr(u.model, "charge_mdg_dist") and u.model.charge_mdg_dist > 0:
            charge_mdg_dist_text = nb2msg_float(u.model.charge_mdg_dist / 1000)  # 转换为格子单位
            attrs.append(("", mp.CHARGE_MDG_DIST, charge_mdg_dist_text))
        
        if hasattr(u.model, "charge_rdg_dist") and u.model.charge_rdg_dist > 0:
            charge_rdg_dist_text = nb2msg_float(u.model.charge_rdg_dist / 1000)  # 转换为格子单位
            attrs.append(("", mp.CHARGE_RDG_DIST, charge_rdg_dist_text))
        
        # 冲锋溅射
        self.main_interface._add_bonus_attribute(attrs, u, "charge_mdg_splash", "", mp.CHARGE_MDG_SPLASH, True)
        self.main_interface._add_bonus_attribute(attrs, u, "charge_rdg_splash", "", mp.CHARGE_RDG_SPLASH, True)
        
        # 冲锋半径
        if hasattr(u.model, "charge_mdg_radius") and u.model.charge_mdg_radius > 0:
            charge_mdg_radius_text = nb2msg_float(u.model.charge_mdg_radius / 1000)  # 转换为格子单位
            attrs.append(("", mp.CHARGE_MDG_RADIUS, charge_mdg_radius_text))
        
        if hasattr(u.model, "charge_rdg_radius") and u.model.charge_rdg_radius > 0:
            charge_rdg_radius_text = nb2msg_float(u.model.charge_rdg_radius / 1000)  # 转换为格子单位
            attrs.append(("", mp.CHARGE_RDG_RADIUS, charge_rdg_radius_text))
        
        # 冲锋溅射衰减最小值
        self.main_interface._add_bonus_attribute(attrs, u, "charge_mdg_splash_decay_min", "", mp.CHARGE_MDG_SPLASH_DECAY_MIN, True)
        self.main_interface._add_bonus_attribute(attrs, u, "charge_rdg_splash_decay_min", "", mp.CHARGE_RDG_SPLASH_DECAY_MIN, True)
        
        # 反冲锋
        self.main_interface._add_bonus_attribute(attrs, u, "op_charge_mdg", "", mp.OP_CHARGE_MDG, True)
        self.main_interface._add_bonus_attribute(attrs, u, "op_charge_rdg", "", mp.OP_CHARGE_RDG, True)
    
    def add_explode_attributes(self, u, attrs):
        """添加自爆相关属性"""
        # 处理自爆相关属性 - 按照原始代码实现
        # 近战自爆
        if hasattr(u.model, "mdg_explode") and u.model.mdg_explode:
            attrs.append(("", mp.MDG_EXPLODE, mp.YES))
        
        # 远程自爆
        if hasattr(u.model, "rdg_explode") and u.model.rdg_explode:
            attrs.append(("", mp.RDG_EXPLODE, mp.YES))
        
        # 自爆扣血百分比
        if hasattr(u.model, "exp_hp_cost") and u.model.exp_hp_cost > 0:
            exp_hp_cost_text = nb2msg_float(u.model.exp_hp_cost / 1000) + ["%"]
            attrs.append(("", mp.EXP_HP_COST, exp_hp_cost_text))
        
        # 爆炸伤害系数
        if hasattr(u.model, "exp_dgf") and u.model.exp_dgf > 0:
            exp_dgf_text = nb2msg_float(u.model.exp_dgf / 1000)
            attrs.append(("", mp.EXP_DGF, exp_dgf_text))
    
    def add_explode_vs_attributes(self, u, attrs):
        """添加自爆vs属性"""
        vs = self.main_interface.vs_handler
        if hasattr(u.model, "mdg_explode_vs") and u.model.mdg_explode_vs:
            vs.add_boolean_vs_attribute(attrs, u.model.mdg_explode_vs, mp.MDG_EXPLODE + mp.VERSUS)
        if hasattr(u.model, "rdg_explode_vs") and u.model.rdg_explode_vs:
            vs.add_boolean_vs_attribute(attrs, u.model.rdg_explode_vs, mp.RDG_EXPLODE + mp.VERSUS)
        if hasattr(u.model, "exp_dgf_vs") and u.model.exp_dgf_vs:
            vs.add_grouped_vs_attribute(
                attrs,
                u.model.exp_dgf_vs,
                mp.EXP_DGF + mp.VERSUS,
                min_positive=True,
            )
    
    def add_target_attributes(self, u, attrs):
        """添加攻击目标类型属性"""
        # 处理攻击目标类型
        # 近战攻击目标（只有单位有近战攻击能力时才显示）
        if (hasattr(u.model, "mdg") and u.model.mdg > 0 and 
            hasattr(u.model, "mdg_targets") and u.model.mdg_targets):
            targets_text = []
            for target_type in u.model.mdg_targets:
                if target_type == "ground":
                    targets_text.extend(mp.TARGET_GROUND)
                elif target_type == "air":
                    targets_text.extend(mp.TARGET_AIR)
                elif target_type == "building":
                    targets_text.extend(mp.TARGET_BUILDING)
                elif target_type == "unit":
                    targets_text.extend(mp.TARGET_UNIT)
                else:
                    # 如果是具体的单位类型名称，尝试获取其标题
                    type_title = style.get(target_type, "title")
                    if type_title:
                        targets_text.extend(type_title)
                    else:
                        targets_text.append(target_type)
                targets_text.extend(mp.COMMA)
            
            if targets_text:
                targets_text = targets_text[:-1]  # 移除最后一个逗号
                attrs.append(("", mp.MDG_TARGETS, targets_text))
        
        # 远程攻击目标（只有单位有远程攻击能力时才显示）
        if (hasattr(u.model, "rdg") and u.model.rdg > 0 and 
            hasattr(u.model, "rdg_targets") and u.model.rdg_targets):
            targets_text = []
            for target_type in u.model.rdg_targets:
                if target_type == "ground":
                    targets_text.extend(mp.TARGET_GROUND)
                elif target_type == "air":
                    targets_text.extend(mp.TARGET_AIR)
                elif target_type == "building":
                    targets_text.extend(mp.TARGET_BUILDING)
                elif target_type == "unit":
                    targets_text.extend(mp.TARGET_UNIT)
                else:
                    # 如果是具体的单位类型名称，尝试获取其标题
                    type_title = style.get(target_type, "title")
                    if type_title:
                        targets_text.extend(type_title)
                    else:
                        targets_text.append(target_type)
                targets_text.extend(mp.COMMA)
            
            if targets_text:
                targets_text = targets_text[:-1]  # 移除最后一个逗号
                attrs.append(("", mp.RDG_TARGETS, targets_text))
    
    def add_minimal_range_attributes(self, u, attrs):
        """添加最小射程相关属性"""
        # 最小射程属性
        if hasattr(u.model, "mdg_minimal_range") and u.model.mdg_minimal_range > 0:
            mdg_minimal_range_text = nb2msg_float(u.model.mdg_minimal_range / 1000)  # 转换为格子单位
            if hasattr(mp, 'MDG_MINIMAL_RANGE'):
                attrs.append(("", mp.MDG_MINIMAL_RANGE, mdg_minimal_range_text))
            else:
                attrs.append(("", ["近战最小射程"], mdg_minimal_range_text))
        
        if hasattr(u.model, "mdg_minimal_range_vs") and u.model.mdg_minimal_range_vs:
            vs_msg = mp.MDG_MINIMAL_RANGE_VS if hasattr(mp, "MDG_MINIMAL_RANGE_VS") else ["近战最小射程VS"]
            self.main_interface.vs_handler.add_grouped_vs_attribute(
                attrs,
                u.model.mdg_minimal_range_vs,
                vs_msg,
                divide_by_1000=True,
                round_digits=1,
            )
        
        if hasattr(u.model, "rdg_minimal_range") and u.model.rdg_minimal_range > 0:
            rdg_minimal_range_text = nb2msg_float(u.model.rdg_minimal_range / 1000)  # 转换为格子单位
            if hasattr(mp, 'RDG_MINIMAL_RANGE'):
                attrs.append(("", mp.RDG_MINIMAL_RANGE, rdg_minimal_range_text))
            else:
                attrs.append(("", ["远程最小射程"], rdg_minimal_range_text))
        
        if hasattr(u.model, "rdg_minimal_range_vs") and u.model.rdg_minimal_range_vs:
            vs_msg = mp.RDG_MINIMAL_RANGE_VS if hasattr(mp, "RDG_MINIMAL_RANGE_VS") else ["远程最小射程VS"]
            self.main_interface.vs_handler.add_grouped_vs_attribute(
                attrs,
                u.model.rdg_minimal_range_vs,
                vs_msg,
                divide_by_1000=True,
                round_digits=1,
            )
    
    def add_ready_attributes(self, u, attrs):
        """添加攻击前摇相关属性"""
        # 攻击准备时间
        if hasattr(u.model, "mdg_ready") and u.model.mdg_ready > 0:
            mdg_ready_text = nb2msg_float(u.model.mdg_ready / 1000) + mp.SECONDS
            attrs.append(("", mp.MDG_READY, mdg_ready_text))
        
        if hasattr(u.model, "mdg_ready_vs") and u.model.mdg_ready_vs:
            vs_msg = mp.MDG_READY_VS if hasattr(mp, "MDG_READY_VS") else ["近战攻击前摇VS"]
            self.main_interface.vs_handler.add_grouped_vs_attribute(
                attrs,
                u.model.mdg_ready_vs,
                vs_msg,
                divide_by_1000=True,
                round_digits=1,
                value_suffix_fn=lambda v: nb2msg_float(v) + mp.SECONDS,
            )
        
        if hasattr(u.model, "rdg_ready") and u.model.rdg_ready > 0:
            rdg_ready_text = nb2msg_float(u.model.rdg_ready / 1000) + mp.SECONDS
            attrs.append(("", mp.RDG_READY, rdg_ready_text))
        
        if hasattr(u.model, "rdg_ready_vs") and u.model.rdg_ready_vs:
            vs_msg = mp.RDG_READY_VS if hasattr(mp, "RDG_READY_VS") else ["远程攻击前摇VS"]
            self.main_interface.vs_handler.add_grouped_vs_attribute(
                attrs,
                u.model.rdg_ready_vs,
                vs_msg,
                divide_by_1000=True,
                round_digits=1,
                value_suffix_fn=lambda v: nb2msg_float(v) + mp.SECONDS,
            )
    
    def add_splash_decay_attributes(self, u, attrs):
        """添加溅射衰减相关属性"""
        # 溅射衰减最小值
        if hasattr(u.model, "mdg_splash_decay_min") and u.model.mdg_splash_decay_min > 0:
            mdg_splash_decay_min_text = nb2msg_float(u.model.mdg_splash_decay_min / PRECISION) + ["%"]
            attrs.append(("", mp.MDG_SPLASH_DECAY_MIN, mdg_splash_decay_min_text))
        
        if hasattr(u.model, "rdg_splash_decay_min") and u.model.rdg_splash_decay_min > 0:
            rdg_splash_decay_min_text = nb2msg_float(u.model.rdg_splash_decay_min / PRECISION) + ["%"]
            attrs.append(("", mp.RDG_SPLASH_DECAY_MIN, rdg_splash_decay_min_text))
    
    def add_splash_decay_vs_attributes(self, u, attrs):
        """添加溅射衰减vs属性"""
        vs = self.main_interface.vs_handler
        if hasattr(u.model, "mdg_splash_decay_min_vs") and u.model.mdg_splash_decay_min_vs:
            vs_msg = (
                mp.MDG_SPLASH_DECAY_MIN_VS
                if hasattr(mp, "MDG_SPLASH_DECAY_MIN_VS")
                else ["近战溅射衰减最小值VS"]
            )
            vs.add_grouped_vs_attribute(
                attrs,
                u.model.mdg_splash_decay_min_vs,
                vs_msg,
                precision_divide=True,
                value_suffix_fn=lambda v: nb2msg_float(v) + ["%"],
            )
        if hasattr(u.model, "rdg_splash_decay_min_vs") and u.model.rdg_splash_decay_min_vs:
            vs_msg = (
                mp.RDG_SPLASH_DECAY_MIN_VS
                if hasattr(mp, "RDG_SPLASH_DECAY_MIN_VS")
                else ["远程溅射衰减最小值VS"]
            )
            vs.add_grouped_vs_attribute(
                attrs,
                u.model.rdg_splash_decay_min_vs,
                vs_msg,
                precision_divide=True,
                value_suffix_fn=lambda v: nb2msg_float(v) + ["%"],
            )
    
    def add_terrain_modifier_attributes(self, u, attrs):
        """添加地形修正相关属性"""
        # 地形命中/闪避修正
        if hasattr(u.model, "mdg_cover_on_terrain") and u.model.mdg_cover_on_terrain:
            terrain_dict = u.model.mdg_cover_on_terrain
            if terrain_dict:
                terrain_text = []
                for terrain_type, modifier in terrain_dict.items():
                    terrain_title = style.get(terrain_type, "title")
                    if terrain_title:
                        if isinstance(terrain_title, list):
                            terrain_text.extend(terrain_title)
                        else:
                            terrain_text.append(str(terrain_title))
                    else:
                        terrain_text.append(str(terrain_type))
                    
                    terrain_text.extend(mp.COLON)
                    terrain_text.extend(nb2msg_float(modifier / PRECISION))
                    terrain_text.extend(mp.COMMA)
                
                if terrain_text:
                    # 移除最后一个逗号
                    terrain_text = terrain_text[:-1]
                    attrs.append(("", mp.MDG_COVER_ON_TERRAIN, terrain_text))
        
        if hasattr(u.model, "rdg_cover_on_terrain") and u.model.rdg_cover_on_terrain:
            rdg_terrain_list = getattr(u.model, "rdg_cover_on_terrain", [])
            if rdg_terrain_list:
                terrain_text = []
                for terrain_type, modifier in rdg_terrain_list.items():
                    terrain_title = style.get(terrain_type, "title")
                    if terrain_title:
                        if isinstance(terrain_title, list):
                            terrain_text.extend(terrain_title)
                        else:
                            terrain_text.append(str(terrain_title))
                    else:
                        terrain_text.append(str(terrain_type))
                    
                    terrain_text.extend(mp.COLON)
                    terrain_text.extend(nb2msg_float(modifier / PRECISION))
                    terrain_text.extend(mp.COMMA)
                
                if terrain_text:
                    terrain_text = terrain_text[:-1]  # 移除最后一个逗号
                    attrs.append(("", mp.RDG_COVER_ON_TERRAIN, terrain_text))