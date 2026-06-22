""""use integers to make sure that any computer will give the same results

本模块同时是 Cython 加速点：若 ``soundrts.lib.nofloat_fast``（.pyd / .so）
存在且未通过环境变量禁用，会在文件末尾用 Cython 实现覆盖以下纯 Python 函数：
``int_cos_1000``、``int_sin_1000``、``square_of_distance``、``int_sqrt``、
``int_distance``、``int_angle``、``to_int``。

数值结果保证与纯 Python 实现完全一致（RTS 必须 deterministic），
设 ``SOUNDRTS_NO_CYTHON=1`` 可强制走纯 Python 路径用于 bug 比对。
"""

import math
import os
from typing import Dict, List, Tuple
from .log import warning

PRECISION = 1000
MAP_SIZE = 1000  # 地图大小，单位为格子数

# tables used to make sure that every computer gives the same results

class TrigTables:
    """三角函数查找表生成器"""
    
    @staticmethod
    def generate_cos_table(precision: int = PRECISION) -> Tuple[int, ...]:
        """生成余弦查找表"""
        return tuple(
            int(math.cos(math.radians(a)) * precision)
            for a in range(360)
        )
    
    @staticmethod
    def generate_sin_table(precision: int = PRECISION) -> Tuple[int, ...]:
        """生成正弦查找表"""
        return tuple(
            int(math.sin(math.radians(a)) * precision)
            for a in range(360)
        )
    
    @staticmethod
    def generate_acos_table(precision: int = 100) -> Dict[int, int]:
        """生成反余弦查找表"""
        return {
            c: int(math.degrees(math.acos(c / precision)))
            for c in range(-precision, precision + 1)
        }
    
    @classmethod
    def generate_all(cls) -> str:
        """生成所有查找表的代码字符串"""
        cos_table = cls.generate_cos_table()
        sin_table = cls.generate_sin_table()
        acos_table = cls.generate_acos_table()
        
        return f"""
# Auto-generated trigonometric tables
_COS_TABLE = {cos_table}
_SIN_TABLE = {sin_table}
_ACOS_TABLE = {acos_table}
"""

def make_tables():
    """生成查找表代码并打印"""
    print(TrigTables.generate_all())

# 使用生成的表替换原有的硬编码表
_COS_TABLE = TrigTables.generate_cos_table()
_SIN_TABLE = TrigTables.generate_sin_table() 
_ACOS_TABLE = TrigTables.generate_acos_table()

def to_int(s):
    """convert a string to an integer with PRECISION

    Cython 编译期要求每个名字只能定义一次，原文件曾有两个同名 to_int 函数，
    第二个覆盖了第一个；这里只保留实际生效的 PRECISION 版本。
    """
    assert isinstance(s, str)  # don't convert twice!
    result = int(float(s) * PRECISION)
    return result


def int_cos_1000(angle):
    """angle in degrees; result = cos(angle) * 1000"""
    assert isinstance(angle, int)
    return _COS_TABLE[angle % 360]


def int_sin_1000(angle):
    """angle in degrees; result = sin(angle) * 1000"""
    assert isinstance(angle, int)
    return _SIN_TABLE[angle % 360]


def square_of_distance(x1, y1, x2, y2):
    dx = x2 - x1
    dy = y2 - y1
    return dx * dx + dy * dy


def int_distance(x1, y1, x2, y2):
    return int_sqrt(square_of_distance(x1, y1, x2, y2))


def int_sqrt(x):
    """should return the same integer square root on any computer"""
    r = int(math.sqrt(x))
    while r * r > x:
        warning(f"sqrt({x}): removing 1 to {r}")
        r -= 1
    while (r + 1) * (r + 1) < x:
        warning(f"sqrt({x}): adding 1 to {r}")
        r += 1
    return r


def int_angle(x1, y1, x2, y2):
    """return the angle with the x-axis (in degrees)"""
    d = int_distance(x1, y1, x2, y2)
    if d == 0:
        return 0
    c = (x2 - x1) * 100 // d  # 100 for the table
    ac = _ACOS_TABLE[c]
    if y2 - y1 > 0:
        return ac
    else:
        return -ac


# --- Cython 加速绑定 ---------------------------------------------------
# 若编译产物可用且未禁用，则覆盖上述纯 Python 实现。
# 注意：必须放在所有函数定义之后，否则会被纯 Python 版本覆盖。

CYTHON_ACCELERATED = False

if os.environ.get("SOUNDRTS_NO_CYTHON", "").strip() not in ("1", "true", "True"):
    try:
        from . import nofloat_fast as _fast

        int_cos_1000 = _fast.int_cos_1000
        int_sin_1000 = _fast.int_sin_1000
        square_of_distance = _fast.square_of_distance
        int_sqrt = _fast.int_sqrt
        int_distance = _fast.int_distance
        int_angle = _fast.int_angle
        to_int = _fast.to_int
        CYTHON_ACCELERATED = True
    except ImportError:
        # 未编译 .pyx 时静默回退到纯 Python 实现
        pass
