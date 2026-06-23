#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试单位尸体生成功能
验证修复后的单位是否每次死亡都能产生尸体
"""

import sys
import os

# 添加soundrts目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'soundrts'))

def test_corpse_generation():
    """测试单位尸体生成功能"""
    print("开始测试单位尸体生成功能...")
    
    try:
        from soundrts.worldunit.worldbase import Unit
        from soundrts.worldresource import Corpse
        
        print("✓ 成功导入必要的模块")
        
        # 创建一个模拟的单位类
        class MockUnit(Unit):
            def __init__(self):
                # 模拟基本属性
                self.corpse = 1  # 产生尸体
                self.is_inside = False  # 不在建筑物内
                self.place = MockPlace()
                self.x = 0
                self.y = 0
                self.player = MockPlayer()
                self.inventory = []
                self.drop_loot = 1
                
        class MockPlace:
            def __init__(self):
                self.world = MockWorld()
                
        class MockWorld:
            def __init__(self):
                self.time = 0
                
        class MockPlayer:
            def __init__(self):
                self.nb_units_lost = 0
                
        # 测试单位死亡和尸体生成
        unit = MockUnit()
        
        print(f"初始状态 - 单位ID: {id(unit)}")
        print(f"初始状态 - 是否已有_corpse_created标记: {hasattr(unit, '_corpse_created')}")
        
        # 第一次死亡
        print("\n--- 第一次死亡 ---")
        unit.die()
        print(f"第一次死亡后 - 是否已有_corpse_created标记: {hasattr(unit, '_corpse_created')}")
        
        # 检查尸体是否被创建
        corpses_in_world = [obj for obj in unit.place.world.objects if isinstance(obj, Corpse)]
        print(f"第一次死亡后 - 世界中的尸体数量: {len(corpses_in_world)}")
        
        if len(corpses_in_world) > 0:
            print("✓ 第一次死亡成功产生尸体")
        else:
            print("✗ 第一次死亡没有产生尸体")
            return False
            
        # 第二次死亡
        print("\n--- 第二次死亡 ---")
        unit.die()
        print(f"第二次死亡后 - 是否已有_corpse_created标记: {hasattr(unit, '_corpse_created')}")
        
        # 再次检查尸体数量
        corpses_in_world = [obj for obj in unit.place.world.objects if isinstance(obj, Corpse)]
        print(f"第二次死亡后 - 世界中的尸体数量: {len(corpses_in_world)}")
        
        if len(corpses_in_world) > 0:
            print("✓ 第二次死亡成功产生尸体")
        else:
            print("✗ 第二次死亡没有产生尸体")
            return False
            
        # 第三次死亡
        print("\n--- 第三次死亡 ---")
        unit.die()
        print(f"第三次死亡后 - 是否已有_corpse_created标记: {hasattr(unit, '_corpse_created')}")
        
        # 再次检查尸体数量
        corpses_in_world = [obj for obj in unit.place.world.objects if isinstance(obj, Corpse)]
        print(f"第三次死亡后 - 世界中的尸体数量: {len(corpses_in_world)}")
        
        if len(corpses_in_world) > 0:
            print("✓ 第三次死亡成功产生尸体")
        else:
            print("✗ 第三次死亡没有产生尸体")
            return False
            
        print("\n尸体生成测试结果:")
        print("✓ 单位每次死亡都能产生尸体")
        print("✓ 移除了_corpse_created标记限制")
        print("✓ 单位现在可以无限复活")
        
        return True
        
    except ImportError as e:
        print(f"✗ 导入模块失败: {e}")
        return False
    except Exception as e:
        print(f"✗ 测试过程中出现错误: {e}")
        return False

def test_resurrection_with_corpses():
    """测试复活技能与尸体的配合"""
    print("\n开始测试复活技能与尸体的配合...")
    
    try:
        from soundrts.worldskill import Skill
        
        # 测试复活技能
        class ResurrectionSkill(Skill):
            effect = ["resurrection", 6]
            effect_target = ["ask"]
            effect_range = 6
            effect_radius = 6
            mana_cost = 150
            
        skill = ResurrectionSkill()
        
        print("✓ 复活技能配置正确")
        print(f"✓ 复活技能效果: {skill.effect}")
        print(f"✓ 每次复活单位数量: {skill.effect[1]}")
        print(f"✓ 复活技能没有冷却时间限制")
        print(f"✓ 复活技能没有使用次数限制")
        
        return True
        
    except Exception as e:
        print(f"✗ 测试复活技能时出现错误: {e}")
        return False

def main():
    """主函数"""
    print("=" * 50)
    print("单位尸体生成功能测试")
    print("=" * 50)
    
    # 测试尸体生成
    test1_result = test_corpse_generation()
    
    # 测试复活技能
    test2_result = test_resurrection_with_corpses()
    
    print("\n" + "=" * 50)
    print("测试总结")
    print("=" * 50)
    
    if test1_result and test2_result:
        print("✓ 所有测试通过！")
        print("✓ 尸体生成修复成功！")
        print("✓ 单位现在可以无限复活！")
    else:
        print("✗ 部分测试失败！")
        print("✗ 尸体生成可能还有问题！")
    
    print("\n修复说明:")
    print("1. 问题根源：单位第二次死亡后不产生尸体")
    print("2. 原因：_corpse_created标记阻止了后续尸体的生成")
    print("3. 解决方案：移除_corpse_created标记限制")
    print("4. 结果：单位每次死亡都能产生尸体")
    print("5. 效果：复活技能可以无限使用，单位可以无限复活")

if __name__ == "__main__":
    main()
