"""
生产属性计算模块
"""


class ProductionCalculator:
    def __init__(self, parent):
        self.parent = parent

    def _calculate_modified_production_time(self, unit):
        """计算经过科技修正后的生产时间"""
        if not hasattr(unit.model, "production_time") or unit.model.production_time is None:
            return None
            
        # 首先尝试从单位类获取基础值（与StartProduceOrder保持一致）
        unit_class = type(unit)
        base_time = getattr(unit_class, "production_time", 0)
        
        # 如果单位类没有production_time属性，则从model获取
        if base_time <= 0:
            base_time = unit.model.production_time
        
        if base_time <= 0:
            return None
            
        modified_time = base_time
        
        # 应用玩家的科技加成
        if hasattr(unit, 'player') and unit.player:
            player = unit.player
            
            # 应用固定值修正
            if hasattr(player, 'production_time_bonus'):
                modified_time += player.production_time_bonus
            
            # 应用百分比修正
            if hasattr(player, 'production_time_percent_bonus') and player.production_time_percent_bonus != 0:
                # 正确的百分比计算：-50% 意味着时间变为原来的 50%
                final_multiplier = 1.0 + player.production_time_percent_bonus
                modified_time = int(modified_time * final_multiplier)
        
        # 确保生产时间不为负
        modified_time = max(1, modified_time)
        
        return modified_time

    def _calculate_modified_production_qty(self, unit):
        """计算经过科技修正后的生产数量"""
        if not hasattr(unit.model, "production_qty") or unit.model.production_qty is None:
            return None
            
        # 首先尝试从单位类获取基础值（与StartProduceOrder保持一致）
        unit_class = type(unit)
        base_qty = getattr(unit_class, "production_qty", 0)
        
        # 如果单位类没有production_qty属性，则从model获取
        if base_qty <= 0:
            base_qty = unit.model.production_qty
        
        if base_qty <= 0:
            return None
            
        modified_qty = base_qty
        
        # 应用玩家的科技加成
        if hasattr(unit, 'player') and unit.player:
            player = unit.player
            
            # 应用固定值修正
            if hasattr(player, 'production_qty_bonus'):
                modified_qty += player.production_qty_bonus
            
            # 应用百分比修正
            if hasattr(player, 'production_qty_percent_bonus') and player.production_qty_percent_bonus != 0:
                # 正确的百分比计算：+50% 意味着数量变为原来的 150%
                final_multiplier = 1.0 + player.production_qty_percent_bonus
                modified_qty = int(modified_qty * final_multiplier)
        
        # 确保产量不为负
        modified_qty = max(0, modified_qty)
        
        return modified_qty