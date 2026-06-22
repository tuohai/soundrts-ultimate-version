"""D-Phase 2 PR1: CreatureProductionAndBuilding mixin 已合并到 Creature 类体.

原始 mixin (committed before D-Phase 2) 只有 2 个方法:
- `_delta`: 与 CreatureAttributes._delta 完全相同, 因 MRO 顺序 CreatureAttributes 在前
  覆盖, 故是 dead code, 合并时直接删除.
- `be_built`: 已搬到 `worldcreature.Creature.be_built`.

本文件保留为兼容性 stub, 防止任何 mod/外部代码 `from .world_production_and_building import CreatureProductionAndBuilding` 时报错.
新版直接从 Creature 继承得到 be_built; 不应该再继承 CreatureProductionAndBuilding.
"""

from ..worldentity import Entity


class CreatureProductionAndBuilding(Entity):
    """已废弃 (D-Phase 2 PR1). 仅留作向后兼容的空 stub. 实际 `be_built` 已移到 Creature."""
    pass
