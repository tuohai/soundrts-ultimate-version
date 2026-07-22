"""时代（phase）系统模块

提供类似帝国时代中"时代推进"的机制：
- 研究后立即将 phase bonus 应用到玩家所有（或 phase_targets 指定的）单位
- 可选地把"与本时代绑定"的单位形态瞬时升级到其 can_upgrade_to 目标
  （绑定方式：把本时代名作为*简单* requirement 写入目标形态；
  ``any_buildings N <group>_buildings`` 子句里的分组名不计入）
- 时代名进入 player.upgrades，便于后续 phase 的 requirements 链式约束

``requirements`` 支持 ``any_buildings <n> <group>_buildings``：收集简单
requirements 含该键的建筑，玩家至少拥有 n 种即可。
DSL 示例（rules.txt）::

    def 城堡时代
    class phase
    cost 10 5 3
    time_cost 60
    requirements barracks 封建时代
    phase bonus mdg 5 rdg 3 sight_range 2 cost -5 -3 -2 time_cost -10 population_cost -1
    units_auto_upgrade 1                ; 仅升级把"城堡时代"写入 requirements 的形态
    can_upgrade_to 帝王时代

    ; 把某形态绑定到城堡时代（升级到城堡时代时自动取代旧形态）::
    def 长剑兵
    class soldier
    requirements 城堡时代               ; 关键：把时代名写入 requirements
    is_a 步兵
    ; ...
    def 步兵
    can_upgrade_to 长剑兵               ; 旧形态指向新形态

    ; 仅强化某类单位的"专精时代"示例：
    def 海洋时代
    class phase
    cost 100 50
    time_cost 60
    phase_targets boat destroyer        ; 仅这些类型/继承链匹配的单位
    phase_targets -building             ; 除建筑外的所有单位
    phase bonus speed 0.5 hp_max 10
"""

from .definitions import MAX_NB_OF_RESOURCE_TYPES
from .lib.log import warning, debug
from .lib.nofloat import PRECISION
from .worldupgrade import Upgrade


# 与 Unit._clear_weapon_attributes / _clear_armor_attributes 保持一致：
# 列出所有"会被武器/护甲重置回 base"的统计字段。phase bonus 一旦改写了
# 这些字段，紧接着的 weapon/armor 应用就会把它们清回去；因此武器/护甲
# 应用之后，需要从玩家的 _phase_bonus_pool 中再叠回这些字段，避免 phase
# 加成在装备/切换/科技刷新时被无声丢失（这是带 weapon/armor 的单位享受
# 不到 phase 攻防加成的根因）。
WEAPON_CLEARED_STATS = frozenset({
    "mdg", "rdg",
    "mdg_range", "rdg_range",
    "mdg_minimal_range", "rdg_minimal_range",
    "mdg_cd", "rdg_cd",
    "mdg_crit", "rdg_crit",
    "mdg_crit_rate", "rdg_crit_rate",
    "mdg_piercing", "rdg_piercing",
    "mdg_piercing_rate", "rdg_piercing_rate",
    "mdg_splash", "rdg_splash",
    "mdg_radius", "rdg_radius",
    "mdg_bonus", "rdg_bonus",
    "mdg_crit_bonus", "rdg_crit_bonus",
    "mdg_piercing_bonus", "rdg_piercing_bonus",
})

ARMOR_CLEARED_STATS = frozenset({
    "mdf", "rdf",
    "mdf_crit_rate", "rdf_crit_rate",
    "mdf_piercing", "rdf_piercing",
    "mdf_bonus", "rdf_bonus",
    "mdf_crit_rate_bonus", "rdf_crit_rate_bonus",
    "mdf_piercing_bonus", "rdf_piercing_bonus",
})

# phase type_name -> already warned about cost + positive phase_targets
_PHASE_COST_TARGET_WARNED = set()


class Phase(Upgrade):
    """时代类——一种特殊的升级。

    若未设置 phase_targets，则 phase bonus 作用于该玩家的所有现有及未来单位；
    若设置了 phase_targets，则只作用于匹配（按 type_name、is_a 链或类别）的单位。
    前缀 ``-`` 表示排除（如 ``-building`` = 除建筑外全部）；可与正向项混用。
    注意：cost/time_cost/population_cost/production_* 等成本类加成始终作用于
    玩家级别（不受 phase_targets 限制），因为这些字段在引擎中本就是玩家全局聚合的。
    """

    phase_bonus = ()
    phase_targets = ()
    units_auto_upgrade = 0
    can_upgrade_to = ()

    @staticmethod
    def _targets_have_positive_includes(targets):
        """phase_targets 是否包含正向匹配项（非 ``-`` 排除项）。"""
        return any(not str(t).startswith("-") for t in targets)

    @staticmethod
    def _unit_matches_single_target(unit, target):
        """判定 unit 是否匹配单个 phase_targets 项。"""
        type_name = getattr(unit, "type_name", "")
        expanded = getattr(unit, "expanded_is_a", ()) or ()
        cls_name = getattr(getattr(unit, "cls", None), "__name__", "").lower()
        t_str = str(target)
        if type_name == t_str:
            return True
        if t_str in expanded:
            return True
        if cls_name and cls_name == t_str.lower():
            return True
        return False

    @staticmethod
    def _unit_matches_targets(unit, targets):
        """判定 unit 是否匹配 phase_targets 列表。

        正向项（任一命中即可）：
        1. 精确 type_name 匹配
        2. is_a 继承链匹配（包括 expanded_is_a）
        3. 基类类别匹配（如 worker/soldier/building/effect）

        排除项以 ``-`` 前缀书写（如 ``-building``）：命中排除项的单位不匹配。
        仅写排除项时（如 ``phase_targets -building``），表示除排除项外的所有单位。
        正向项与排除项可同时使用（如 ``phase_targets soldier -footman``）。
        """
        if not targets:
            return True
        try:
            includes = []
            excludes = []
            for t in targets:
                t_str = str(t)
                if t_str.startswith("-"):
                    excludes.append(t_str[1:])
                else:
                    includes.append(t_str)
            if includes and not any(
                Phase._unit_matches_single_target(unit, t) for t in includes
            ):
                return False
            if excludes and any(
                Phase._unit_matches_single_target(unit, t) for t in excludes
            ):
                return False
            return True
        except Exception:
            return False

    @classmethod
    def upgrade_player(cls, player):
        """研究完成时被 ResearchOrder 调用。"""
        bonus_args = list(getattr(cls, "phase_bonus", ()) or ())
        targets = list(getattr(cls, "phase_targets", ()) or ())

        if bonus_args:
            # 若设置了正向 phase_targets 且 bonus 中有成本类项目，给一次性警告。
            # 仅写排除项（如 ``phase_targets -building``）是常见写法：全局减费 +
            # 仅对非建筑叠战斗属性，不算配置错误。
            if targets and cls._targets_have_positive_includes(targets):
                cost_stats = {
                    "cost", "production_cost", "time_cost", "population_cost",
                    "production_time", "production_qty",
                }
                cost_items = [
                    bonus_args[i] for i in range(0, len(bonus_args), 2)
                    if i < len(bonus_args) and bonus_args[i] in cost_stats
                ]
                if cost_items and cls.type_name not in _PHASE_COST_TARGET_WARNED:
                    _PHASE_COST_TARGET_WARNED.add(cls.type_name)
                    warning(
                        "phase %s: phase_targets is set but cost-type bonuses "
                        "(%s) are applied at player level globally and are NOT "
                        "filtered by phase_targets",
                        cls.type_name, ",".join(cost_items),
                    )

            cls._apply_phase_bonus_to_player(player, bonus_args)
            cls._apply_phase_bonus_to_existing_units(player, bonus_args, targets)

            if not hasattr(player, "_phase_bonus_pool"):
                player._phase_bonus_pool = []
            # 同时把 targets 一起存入，以便新加入的单位也能正确过滤
            player._phase_bonus_pool.append((bonus_args, targets))

        if cls.type_name not in player.upgrades:
            player.upgrades.append(cls.type_name)
        player.current_phase = cls.type_name

        if int(getattr(cls, "units_auto_upgrade", 0) or 0):
            cls._auto_upgrade_units(player)

        try:
            for unit in list(player.units):
                if hasattr(unit, "update_weapons"):
                    unit.update_weapons()
                if hasattr(unit, "update_armors"):
                    unit.update_armors()
        except Exception as e:
            warning("Error refreshing weapons/armors after phase %s: %s",
                    cls.type_name, str(e))

    @classmethod
    def _apply_phase_bonus_to_existing_units(cls, player, bonus_args, targets=()):
        """把 phase bonus 中的非成本项应用到所有现有（可选过滤后的）单位。"""
        non_cost_args = cls._filter_out_cost_args(bonus_args)
        if not non_cost_args:
            return
        for unit in list(player.units):
            if targets and not cls._unit_matches_targets(unit, targets):
                continue
            try:
                cls.effect_bonus(unit, 0, *non_cost_args)
            except Exception as e:
                warning("Error applying phase bonus to unit %s: %s",
                        getattr(unit, "type_name", unit), str(e))

    @classmethod
    def _apply_phase_bonus_to_player(cls, player, bonus_args):
        """把 phase_bonus 中的成本类项目累积到 player 级别属性。

        非成本项（mdg/rdg/sight_range 等）由 _apply_phase_bonus_to_existing_units
        调用 effect_bonus 处理。这里仅处理 cost / time_cost / population_cost /
        production_cost / production_time / production_qty。

        cost / time_cost / population_cost 写入 phase_* 专用字段，供 ComplexOrder
        与各订单在无 can_use 关联时仍能应用；避免与科技累加到 cost_bonus 的通路重复计算。
        """
        if not hasattr(player, "phase_cost_bonus"):
            player.phase_cost_bonus = [0] * MAX_NB_OF_RESOURCE_TYPES
        if not hasattr(player, "phase_cost_percent_bonus"):
            player.phase_cost_percent_bonus = [0.0] * MAX_NB_OF_RESOURCE_TYPES

        i = 0
        while i < len(bonus_args):
            stat = bonus_args[i]
            if i + 1 >= len(bonus_args):
                break
            value = bonus_args[i + 1]

            if stat == "cost":
                cls._add_list_bonus_to_player(
                    player, "phase_cost_bonus", "phase_cost_percent_bonus",
                    value, scale=PRECISION
                )
            elif stat == "production_cost":
                if not hasattr(player, "production_cost_bonus"):
                    player.production_cost_bonus = [0] * MAX_NB_OF_RESOURCE_TYPES
                if not hasattr(player, "production_cost_percent_bonus"):
                    player.production_cost_percent_bonus = [0.0] * MAX_NB_OF_RESOURCE_TYPES
                cls._add_list_bonus_to_player(
                    player, "production_cost_bonus",
                    "production_cost_percent_bonus", value, scale=PRECISION
                )
            elif stat == "time_cost":
                cls._add_scalar_bonus_to_player(
                    player, "phase_time_cost_bonus", "phase_time_cost_percent_bonus", value
                )
            elif stat == "population_cost":
                cls._add_scalar_bonus_to_player(
                    player, "phase_population_cost_bonus",
                    "phase_population_cost_percent_bonus", value
                )
            elif stat == "production_time":
                cls._add_scalar_bonus_to_player(
                    player, "production_time_bonus",
                    "production_time_percent_bonus", value
                )
            elif stat == "production_qty":
                cls._add_scalar_bonus_to_player(
                    player, "production_qty_bonus",
                    "production_qty_percent_bonus", value
                )
            i += 2

    @staticmethod
    def _filter_out_cost_args(bonus_args):
        """从 phase_bonus 参数列表中剔除已被 _apply_phase_bonus_to_player 处理的项。"""
        cost_stats = {
            "cost", "production_cost", "time_cost", "population_cost",
            "production_time", "production_qty",
        }
        result = []
        i = 0
        while i < len(bonus_args):
            stat = bonus_args[i]
            if i + 1 >= len(bonus_args):
                break
            value = bonus_args[i + 1]
            if stat not in cost_stats:
                result.extend([stat, value])
            i += 2
        return result

    @staticmethod
    def _add_list_bonus_to_player(player, abs_attr, percent_attr, value, scale=1):
        """为列表型属性（如 player.cost_bonus）加上多资源加成值。"""
        try:
            value_str = str(value)
            is_percent = value_str.endswith("%")
            if is_percent:
                tokens = value_str.rstrip("%").split()
                values = [float(v) / 100.0 for v in tokens]
                target = getattr(player, percent_attr)
            else:
                tokens = value_str.split()
                if scale == PRECISION:
                    values = [int(float(v) * PRECISION) for v in tokens]
                else:
                    values = [int(float(v)) for v in tokens]
                target = getattr(player, abs_attr)

            for j, v in enumerate(values):
                if j < len(target):
                    target[j] += v
        except (ValueError, TypeError) as e:
            warning("Error in phase player-level list bonus %s: %s", abs_attr, str(e))

    @staticmethod
    def _add_scalar_bonus_to_player(player, abs_attr, percent_attr, value):
        """为标量型属性（如 player.time_cost_bonus）累加加成值。"""
        try:
            value_str = str(value)
            if value_str.endswith("%"):
                if not hasattr(player, percent_attr):
                    setattr(player, percent_attr, 0.0)
                pv = float(value_str.rstrip("%")) / 100.0
                setattr(player, percent_attr, getattr(player, percent_attr) + pv)
            else:
                if not hasattr(player, abs_attr):
                    setattr(player, abs_attr, 0)
                v = int(float(value_str))
                setattr(player, abs_attr, getattr(player, abs_attr) + v)
        except (ValueError, TypeError) as e:
            warning("Error in phase player-level scalar bonus %s: %s", abs_attr, str(e))

    @staticmethod
    def _filter_args_by_stats(bonus_args, allowed_stats=None, denied_stats=None):
        """从 bonus_args（[stat1, val1, stat2, val2, ...]）里筛选出
        ``stat`` 命中 ``allowed_stats``（若给定）且未命中 ``denied_stats``
        （若给定）的项，按原顺序返回新的扁平列表。
        """
        result = []
        i = 0
        while i < len(bonus_args):
            stat = bonus_args[i]
            if i + 1 >= len(bonus_args):
                break
            value = bonus_args[i + 1]
            if allowed_stats is not None and stat not in allowed_stats:
                i += 2
                continue
            if denied_stats is not None and stat in denied_stats:
                i += 2
                continue
            result.extend([stat, value])
            i += 2
        return result

    @classmethod
    def _iter_pool_entries(cls, unit):
        """遍历 unit.player._phase_bonus_pool，yield 出适用于本单位、且
        已剥离成本类项目的 (non_cost_args,) 列表（元组）。
        """
        player = getattr(unit, "player", None)
        if player is None:
            return
        pool = getattr(player, "_phase_bonus_pool", None)
        if not pool:
            return
        for entry in pool:
            # 兼容老格式：直接是 list；新格式：(bonus_args, targets)
            if isinstance(entry, tuple) and len(entry) == 2:
                bonus_args, targets = entry
            else:
                bonus_args, targets = entry, ()

            if targets and not cls._unit_matches_targets(unit, targets):
                continue

            non_cost_args = cls._filter_out_cost_args(list(bonus_args))
            if not non_cost_args:
                continue
            yield non_cost_args

    @classmethod
    def apply_pool_to_unit(cls, unit):
        """供 Player.add() 调用：为新加入的单位应用所有已激活时代的非成本、
        且非"武器/护甲会重置"的加成。

        武器/护甲会重置的字段（mdg、rdg、mdf、rdf、相关 cd/range/crit 等）
        交给单位自己的 ``update_weapons`` / ``update_armors``（实际是
        :meth:`apply_pool_weapon_subset_to_unit` /
        :meth:`apply_pool_armor_subset_to_unit`）在装备/刷新时叠加，
        以避免后续每次刷新装备就把 phase 加成无声丢掉，也避免新单位双重加成。

        每个 pool 条目是 (bonus_args, targets) 元组；若 targets 非空，仅当单位
        匹配时才应用。也兼容老格式（裸列表表示无 targets）。
        """
        denied = WEAPON_CLEARED_STATS | ARMOR_CLEARED_STATS
        for non_cost_args in cls._iter_pool_entries(unit):
            filtered = cls._filter_args_by_stats(non_cost_args, denied_stats=denied)
            if not filtered:
                continue
            try:
                cls.effect_bonus(unit, 0, *filtered)
            except Exception as e:
                warning("Error applying pooled phase bonus to %s: %s",
                        getattr(unit, "type_name", unit), str(e))

    @classmethod
    def apply_pool_weapon_subset_to_unit(cls, unit):
        """供 ``Unit.update_weapons`` / 武器装备/切换流程在末尾调用：
        重新把已激活时代的"武器相关"加成叠加到单位上。

        因为 :meth:`Unit._clear_weapon_attributes` 会把 ``mdg``/``rdg`` 等
        清回 base，再由武器自己 ``apply_to_unit`` 涂上武器值，
        所以紧接着把 pool 中的对应字段加回来，phase 加成才不会被擦除。
        """
        for non_cost_args in cls._iter_pool_entries(unit):
            filtered = cls._filter_args_by_stats(
                non_cost_args, allowed_stats=WEAPON_CLEARED_STATS
            )
            if not filtered:
                continue
            try:
                cls.effect_bonus(unit, 0, *filtered)
            except Exception as e:
                warning(
                    "Error re-applying weapon-subset phase bonus to %s: %s",
                    getattr(unit, "type_name", unit), str(e),
                )

    @classmethod
    def apply_pool_armor_subset_to_unit(cls, unit):
        """供 ``Unit.update_armors`` / 护甲装备流程在末尾调用：
        重新把已激活时代的"护甲相关"加成（``mdf``/``rdf`` 等）叠加到单位上。
        """
        for non_cost_args in cls._iter_pool_entries(unit):
            filtered = cls._filter_args_by_stats(
                non_cost_args, allowed_stats=ARMOR_CLEARED_STATS
            )
            if not filtered:
                continue
            try:
                cls.effect_bonus(unit, 0, *filtered)
            except Exception as e:
                warning(
                    "Error re-applying armor-subset phase bonus to %s: %s",
                    getattr(unit, "type_name", unit), str(e),
                )

    @classmethod
    def _auto_upgrade_units(cls, player):
        """对与本次时代关联的单位执行瞬时形态升级。

        判定规则（避免误升纯手动建造的形态链，如 townhall→keep→castle、
        scouttower→guardtower 等）：
          - 单位必须有 ``can_upgrade_to`` 列表；
          - 仅当 ``can_upgrade_to`` 中存在某个目标，其 ``requirements`` 列表
            显式包含本次研究完成的时代名（``cls.type_name``）时，才视为
            "该形态升级与本次时代推进绑定"，进而免费瞬时升级。
          - 若多个目标命中，按 ``can_upgrade_to`` 中出现的先后顺序选择
            第一个命中的目标。
          - 若设置了 ``phase_targets``，仍按既有规则先做单位过滤。

        这样做后，把某个形态升级"挂"到时代上的方式很直观：在目标形态的
        ``requirements`` 里追加本时代名即可（例如让 ``swordsman`` 在
        ``castle_age`` 后自动取代 ``footman``：在 ``swordsman`` 上写
        ``requirements castle_age``）。
        """
        from .definitions import rules
        phase_name = cls.type_name
        targets = list(getattr(cls, "phase_targets", ()) or ())
        for unit in list(player.units):
            if targets and not cls._unit_matches_targets(unit, targets):
                continue
            target_names = getattr(unit, "can_upgrade_to", ()) or ()
            if not target_names:
                continue
            if not isinstance(target_names, (list, tuple)):
                target_names = [target_names]

            chosen_cls = None
            chosen_name = None
            for target_name in target_names:
                candidate = rules.unit_class(target_name)
                if candidate is None:
                    continue
                from .worldrequirements import has_phase_as_simple_requirement

                requirements = getattr(candidate, "requirements", ()) or ()
                if has_phase_as_simple_requirement(requirements, phase_name):
                    chosen_cls = candidate
                    chosen_name = target_name
                    break

            if chosen_cls is None:
                # 该单位的形态升级与本时代无关，不做处理。
                continue
            try:
                cls._instant_morph(unit, chosen_cls)
            except Exception as e:
                warning("Error auto-upgrading %s to %s: %s",
                        getattr(unit, "type_name", unit), chosen_name, str(e))

    @staticmethod
    def _instant_morph(unit, target_cls):
        """瞬时把单位变形为 target_cls，跳过资源/时间消耗。

        参考 UpgradeToOrder.complete() 的实现，但不收取任何代价。
        """
        player = unit.player
        place = unit.place
        x, y = unit.x, unit.y
        old_hp = getattr(unit, "hp", 0)
        old_hp_max = getattr(unit, "hp_max", 0) or 1
        hp_ratio = max(0.0, min(1.0, old_hp / old_hp_max))
        try:
            blocked_exit = getattr(unit, "blocked_exit", None)
        except Exception:
            blocked_exit = None

        try:
            unit.notify("upgrade_to,%s" % unit.world.get_next_id(increment=False))
        except Exception:
            pass
        old_unit = unit
        old_unit.delete()

        new_unit = target_cls(player, place, x, y)
        try:
            if blocked_exit and hasattr(new_unit, "block"):
                new_unit.block(blocked_exit)
        except Exception:
            pass
        try:
            new_unit.hp = max(1, int(new_unit.hp_max * hp_ratio))
        except Exception:
            pass
        # 把旧单位携带的物品转移到新单位（避免时代升级后物品消失）
        try:
            if hasattr(old_unit, "transfer_inventory_to"):
                old_unit.transfer_inventory_to(new_unit)
        except Exception:
            pass
        try:
            new_unit.notify("complete")
        except Exception:
            pass
        return new_unit


def is_a_phase(o):
    """Phase 探测器，类似 worldupgrade.is_an_upgrade。"""
    return isinstance(o, type) and issubclass(o, Phase)
