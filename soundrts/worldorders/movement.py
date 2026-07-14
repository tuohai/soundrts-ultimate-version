from ..worldaction import AttackAction
from ..world_build_rules import go_target_for_flying_building_addon
from ..worldroom import Square
from .base import BasicOrder, _order_target_square


def _herd_attach_range_met(herder, animal):
    """牧民进入羊所在方格（或已贴身）才可绑定驱赶。"""
    if getattr(herder, "place", None) is None or getattr(animal, "place", None) is None:
        return False
    if herder.place is animal.place:
        return True
    return herder._near_enough(animal)


def _attach_herd(animal, herder):
    animal._herd_leader = herder
    animal._herd_player = herder.player
    animal.last_attacker = None
    animal._herd_follow_place = getattr(herder, "place", None)


class GoOrder(BasicOrder):

    keyword = "go"
    nb_args = 1

    def __eq__(self, other):
        # smart units with the same "go" order will behave as a group
        # (cf move_to_or_fail)
        return (
            self.__class__ == other.__class__
            and getattr(self.target, "id", None) == getattr(other.target, "id", None)
            and self._creation_time == other._creation_time
        )

    def on_queued(self):
        self._creation_time = self.world.time
        self.target = self.player.get_object_by_id(self.args[0])
        if self.target is None:
            self.mark_as_impossible()
            return
        if hasattr(self.target, "other_side"):  # target is an exit
            # the new target is the square on the other side
            self.target = self.target.other_side.place
        else:
            self.target = go_target_for_flying_building_addon(self.unit, self.target)
        if self._reject_if_terrain_impassable(self.target):
            return
        # 在RPG模式下（强制性命令）不播放order_ok音效
        if not self.is_imperative:
            self.unit.notify("order_ok")

    def _try_attach_herd_on_arrival(self):
        if not getattr(self.target, "herdable", 0):
            return
        if "herd" not in self.unit.basic_skills:
            return
        if not _herd_attach_range_met(self.unit, self.target):
            return
        _attach_herd(self.target, self.unit)
        self.unit.stop()
        self.unit.notify("herd_ok")

    def execute(self):
        self.update_target()
        if self.target is None:
            self.mark_as_impossible()
        elif self.unit.is_in_position(self.target):  # square or subsquare
            self.unit.hold(self.target)
            self._try_attach_herd_on_arrival()
            self.mark_as_complete()
        elif self.unit._near_enough(self.target):
            try:
                if self.target.have_enough_space(self.unit):
                    self.target.load(self.unit)
            except AttributeError:
                pass
            self._try_attach_herd_on_arrival()
            self.mark_as_complete()
        elif self.unit.is_idle:
            self.move_to_or_fail(self.target)


class HerdOrder(BasicOrder):

    keyword = "herd"
    nb_args = 1

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        return cls.keyword in unit.basic_skills

    def on_queued(self):
        self.target = self.player.get_object_by_id(self.args[0])
        if self.target is None:
            self.mark_as_impossible()
            return
        if not getattr(self.target, "herdable", 0):
            self.mark_as_impossible()
            return
        if getattr(self.target, "hp", 0) <= 0:
            self.mark_as_impossible()
            return
        self.unit.notify("order_ok")

    def execute(self):
        self.update_target()
        if self.target is None or getattr(self.target, "hp", 0) <= 0:
            self.mark_as_impossible()
            return
        if not getattr(self.target, "herdable", 0):
            self.mark_as_impossible()
            return
        if _herd_attach_range_met(self.unit, self.target):
            _attach_herd(self.target, self.unit)
            self.unit.stop()
            self.unit.notify("herd_ok")
            self.mark_as_complete()
            return
        # 仅在空闲时重新寻路；跨格移动中 action_target 往往是出口而非羊，不能每帧重置路径
        if self.unit.is_idle:
            self.move_to_or_fail(self.target)


class AttackOrder(BasicOrder):

    keyword = "attack"
    nb_args = 1

    def on_queued(self):
        self.target = self.player.get_object_by_id(self.args[0])
        if self.target is None:
            self.mark_as_impossible()
            return
        self.unit.notify("order_ok")

    def execute(self):
        # 条约期拦截：禁止对敌对单位执行攻击
        try:
            if getattr(self.world, "treaty_until_time", 0) > 0 and self.world.time < self.world.treaty_until_time:
                # 如果目标有玩家且为敌对，则拦截
                if getattr(self.target, "player", None) is not None:
                    if self.player.player_is_an_enemy(self.target.player):
                        self.mark_as_impossible("treaty")
                        # 给本地人类提示
                        for p in self.world.players:
                            if p.is_local_human() and p is self.player:
                                from soundrts import msgparts as mp
                                p.push("msg", "***".join(map(str, mp.TREATY_ACTIVE)))
                        return
        except Exception:
            pass
        self.update_target()
        if self.target is None or getattr(self.target, "hp", 0) <= 0:
            # 目标消失/死亡通常表示已击杀（如狩猎动物），属攻击成功而非失败。
            # 旧逻辑会 mark_as_impossible → 退格杀完动物后滴一声 order_impossible。
            self.mark_as_complete()
            return
        if (
            hasattr(self.unit, "is_an_enemy")
            and not self.unit.is_an_enemy(self.target)
            and not getattr(self, "is_imperative", False)
        ):
            # 夺取阈值 100：目标已被己方/盟友占领后，命令视为完成，避免 order_impossible 滴声
            if getattr(self.target, "capture_hp_threshold", 0) == 100:
                self.mark_as_complete()
                return
            self.mark_as_impossible()
            return
        if not getattr(self.target, "is_vulnerable", False):
            self.mark_as_impossible()
            return
        if self.unit._near_enough_to_aim(self.target):
            action = AttackAction(self.unit, self.target)
            if getattr(self, "is_imperative", False):
                action.is_imperative = True
            self.unit.action = action
        elif self.unit.is_idle:
            self.move_to_or_fail(self.target)


class CaptureOrder(AttackOrder):
    """移动至夺取阈值 100 的敌方目标并直接占领（不造成伤害）。"""

    keyword = "capture"
    nb_args = 1

    @classmethod
    def is_allowed(cls, unit, target_id=None):
        if "attack" not in unit.basic_skills:
            return False
        if not bool(getattr(unit, "can_capture", 1)):
            return False
        if target_id is None:
            return True
        target = unit.player.get_object_by_id(target_id)
        if target is None:
            return False
        return (
            target is not unit
            and getattr(target, "hp", 0) > 0
            and getattr(target, "is_vulnerable", False)
            and unit.is_an_enemy(target)
            and getattr(target, "capture_hp_threshold", 0) == 100
        )


class PatrolOrder(BasicOrder):

    keyword = "patrol"
    nb_args = 1

    def on_queued(self):
        self.target = self.player.get_object_by_id(self.args[0])
        square = _order_target_square(self.target)
        if square is None:
            try:
                square = self.player.get_object_by_id(self.target.place.id)
            except AttributeError:
                self.mark_as_impossible()
                return
        self.target = square
        if self._reject_if_terrain_impassable(self.target):
            return
        self.unit.notify("order_ok")
        if (
            self.unit.orders
            and self.unit.orders[0].keyword == "patrol"
            and hasattr(self.unit.orders[0], "targets")
        ):
            self.unit.orders[0].targets.append(self.target)
            self.mark_as_complete()
        else:
            self.targets = [self.unit.place, self.target]
            self.mode = 0

    def execute(self):
        if self.unit.place == self.targets[self.mode]:
            self.mode += 1
            self.mode %= len(self.targets)
            self.unit.deploy()
        elif self.unit.is_idle:
            self.move_to_or_fail(self.targets[self.mode])


class BlockOrder(BasicOrder):

    keyword = "block"
    nb_args = 1
    is_imperative = True

    def on_queued(self):
        self.target = self.player.get_object_by_id(self.args[0])
        if not getattr(self.target, "is_an_exit", False):
            self.mark_as_impossible()
            return
        # 检查水上单位是否意外上岸，如果是则不允许阻挡
        if hasattr(self.unit, 'is_water_unit_on_land') and self.unit.is_water_unit_on_land():
            self.mark_as_impossible()
            return
        self.unit.notify("order_ok")
        self.mode = "go_block"

    def execute(self):
        self.update_target()
        if self.mode == "go_block":
            if self.unit._near_enough(self.target):
                self.mode = "block"
                self.unit.stop()
                self.unit.move_on_border(self.target)
            elif self.unit.is_idle:
                self.move_to_or_fail(self.target)
        elif self.mode == "block":
            self.unit.block(self.target)


class RepairOrder(BasicOrder):

    keyword = "repair"
    nb_args = 1

    def on_queued(self):
        self.target = self.player.get_object_by_id(self.args[0])
        if not getattr(self.target, "is_repairable", False):
            self.mark_as_impossible()
            return
        
        # 检查工人是否有修理权限
        if not getattr(self.unit, "can_repair", 0):
            self.mark_as_impossible()
            return
        
        # 检查是否是船只修理，如果是则需要验证can_repair_ships权限
        if (hasattr(self.target, "airground_type") and 
            self.target.airground_type == "water" and
            hasattr(self.target, "can_be_repaired_by_worker_from_shore") and
            self.target.can_be_repaired_by_worker_from_shore(self.unit)):
            # 这是船只修理，检查单位是否有修理船只的权限
            if not getattr(self.unit, "can_repair_ships", 0):
                self.mark_as_impossible()
                return
        
        # 检查是否可以进行靠岸修理
        if (hasattr(self.target, "can_be_repaired_by_worker_from_shore") and 
            self.target.can_be_repaired_by_worker_from_shore(self.unit)):
            self.unit.notify("order_ok")
            self.mode = "go_build"
            return
        
        self.unit.notify("order_ok")
        self.mode = "go_build"

    def execute(self):
        self.update_target()
        if (self.target is None or self.target.is_fully_repaired):
            self.mark_as_complete()
            self.unit.stop()
        elif self.mode == "go_build":
            # 检查是否在建筑物附近
            if self.unit._near_enough(self.target):
                self.mode = "build"
                self.unit.stop()
            # 检查是否可以从岸上修理靠岸的船只
            elif (hasattr(self.target, "can_be_repaired_by_worker_from_shore") and 
                  self.target.can_be_repaired_by_worker_from_shore(self.unit)):
                self.mode = "build"
                self.unit.stop()
            # 如果是出口建筑，检查是否在出口任意一侧且足够近
            elif (hasattr(self.target, "blocked_exit") and 
                  self.target.blocked_exit and
                  (self.unit.place is self.target.blocked_exit.place or
                   self.unit.place is self.target.blocked_exit.other_side.place) and
                  self.unit._near_enough(self.target)):
                self.mode = "build"
                self.unit.stop()
            elif self.unit.is_idle:
                from ..world_build_rules import (
                    is_scaffold_water_build_target,
                    nearest_reachable_land_for_water_build,
                    water_only_build_square_for,
                )

                if is_scaffold_water_build_target(self.target):
                    self.move_to_or_fail(self.target)
                else:
                    water_sq = water_only_build_square_for(self.target)
                    if water_sq is not None:
                        staging = nearest_reachable_land_for_water_build(
                            self.unit, water_sq
                        )
                        if staging is not None:
                            self.move_to_or_fail(staging)
                        else:
                            self.mark_as_impossible()
                            self.unit.stop()
                    else:
                        self.move_to_or_fail(self.target)
        elif self.mode == "build":
            # 检查是否仍然可以修理
            repair_possible = False

            # 检查常规修理条件
            if self.unit._near_enough(self.target):
                repair_possible = True
            
            # 检查靠岸修理条件
            elif (hasattr(self.target, "can_be_repaired_by_worker_from_shore") and 
                  self.target.can_be_repaired_by_worker_from_shore(self.unit)):
                # 对于船只修理，额外检查权限
                if (hasattr(self.target, "airground_type") and 
                    self.target.airground_type == "water"):
                    if getattr(self.unit, "can_repair_ships", 0):
                        repair_possible = True
                else:
                    repair_possible = True
            
            if repair_possible:
                self.target.be_built(self.unit)
            else:
                # 如果无法修理，切换回移动模式
                self.mode = "go_build"
                self.unit.stop()


class BuildPhaseTwoOrder(RepairOrder):

    keyword = "build_phase_two"