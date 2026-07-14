from .lib.nofloat import square_of_distance

def should_capture_on_contact(unit, target):
    """夺取阈值 100 且目标仍为真实敌方（非强制攻击下的伪敌人）。"""
    if getattr(target, "capture_hp_threshold", 0) != 100:
        return False
    if not bool(getattr(unit, "can_capture", 1)):
        return False
    target_player = getattr(target, "player", None)
    unit_player = getattr(unit, "player", None)
    return (
        unit_player is not None
        and target_player is not None
        and unit_player.player_is_an_enemy(target_player)
    )


class Action:
    def __init__(self, unit, target):
        self.unit = unit
        self.target = target

    @property
    def target(self):
        return self.__dict__.get("target")

    @target.setter
    def target(self, value):
        self.__dict__["target"] = value

    def __getstate__(self):
        from .save_pickle import strip_target_for_pickle

        state = self.__dict__.copy()
        strip_target_for_pickle(state)
        return state

    def __setstate__(self, state):
        from .save_pickle import restore_target_after_pickle

        self.__dict__.update(state)
        restore_target_after_pickle(self)

    def complete(self):
        self.unit.walked = []
        self.unit.action = None

    def update(self):
        pass


class MoveAction(Action):
    def update(self):
        target = self.target
        if target is None:
            if getattr(self, "_pickle_target_id", None):
                return
            self.complete()
            return
        if getattr(target, "other_side", None) is not None:
            if self.unit.place is not target.place:
                self.unit.action_reach_and_stop()
            else:
                self.unit.go_to_xy(
                    target.other_side.place.x, target.other_side.place.y
                )
        elif getattr(target, "place", None) is self.unit.place:
            self.unit.action_reach_and_stop()
        elif self.unit.airground_type in ["air", "water"]:
            # 检查目标对象是否有x和y属性，如果没有则计算中心点
            if hasattr(target, "x") and hasattr(target, "y"):
                target_x = target.x
                target_y = target.y
            elif hasattr(target, "xmin") and hasattr(target, "xmax") and hasattr(target, "ymin") and hasattr(target, "ymax"):
                # 目标是Square对象但缺少x,y属性，计算中心点
                target_x = (target.xmin + target.xmax) // 2
                target_y = (target.ymin + target.ymax) // 2
            else:
                # 无法确定目标位置，完成动作
                self.complete()
                return
                
            self.unit.go_to_xy(target_x, target_y)
        else:
            self.complete()


class MoveXYAction(Action):
    def update(self):
        x, y = self.target
        u = self.unit
        subsquare = u.world.get_subsquare_id_from_xy
        if subsquare(x, y) != subsquare(u.x, u.y):
            if u.go_to_xy(x, y):
                self.complete()
        else:
            # try as long as the distance is decreasing
            previous_d2 = square_of_distance(x, y, u.x, u.y)
            if u.go_to_xy(x, y) or square_of_distance(x, y, u.x, u.y) > previous_d2:
                self.complete()


class AttackAction(Action):
    def update(self):
        unit = self.unit
        target = self.target
        if (
            target is None
            or getattr(target, "place", None) is None
            or getattr(target, "hp", 0) <= 0
        ):
            self.complete()
            return
        # 夺取阈值为 100 的敌方建筑“接触即占领”：直接占领而非攻击。
        # 单位移动到目标处后直接转变其阵营，全程不造成伤害、不播放攻击动作/音效。
        if should_capture_on_contact(unit, target):
            if unit.speed and target in unit.place.objects:
                if unit.action_reach_and_capture(target):
                    self.complete()
            elif unit.can_attack(target):
                unit._perform_capture(target)
                self.complete()
            else:
                self.complete()
            return
        # 同格：靠近并瞄准
        if unit.speed and unit.place is not None and target in unit.place.objects:
            unit.action_reach_and_aim()
            return
        # 跨格但仍在射程内（远程等）：直接开火
        if unit.can_attack(target):
            unit.aim(target)
            return
        # 追击模式：保持 AttackAction，经出口路径持续跟随，不下 go 命令
        if (
            getattr(unit, "ai_mode", None) == "chase"
            and unit.speed > 0
            and hasattr(unit, "is_an_enemy")
            and unit.is_an_enemy(target)
        ):
            if self._chase_toward(unit, target):
                return
        self.complete()

    def _chase_toward(self, unit, target):
        """跨格追击：用 next_stage 走出口，不替换当前 AttackAction。"""
        next_stage = getattr(unit, "next_stage", None)
        if not callable(next_stage):
            return False
        stage = next_stage(target)
        if stage is None:
            return False
        if stage is target:
            if unit.place is not None and target in unit.place.objects:
                unit.action_reach_and_aim()
                return True
            return False
        # 与下达 go 时 stop() 清 hold 同效：否则 position_to_hold 会禁止离开当前格
        if getattr(unit, "position_to_hold", None) is not None:
            unit.position_to_hold = None
        # 出口：与 MoveAction 相同，朝对面格中心走以完成跨格
        other_side = getattr(stage, "other_side", None)
        if other_side is not None:
            if unit.place is getattr(stage, "place", None):
                destination = getattr(other_side, "place", None)
                if destination is None:
                    return False
                unit.go_to_xy(destination.x, destination.y)
                return True
            # 出口不在当前格时，尽量朝出口坐标靠近
            if hasattr(stage, "x") and hasattr(stage, "y"):
                unit.go_to_xy(stage.x, stage.y)
                return True
            return False
        if hasattr(stage, "x") and hasattr(stage, "y"):
            unit.go_to_xy(stage.x, stage.y)
            return True
        return False

    def complete(self):
        # 重置冲锋状态，但保持冲锋的距离条件限制
        if hasattr(self.unit, 'reset_charge_state'):
            self.unit.reset_charge_state(force=False)
        
        # 攻击结束后切换回默认武器
        if hasattr(self.unit, 'switch_to_default_weapon'):
            self.unit.switch_to_default_weapon()

        captured_on_contact = (
            getattr(self.target, "capture_hp_threshold", 0) == 100
            and getattr(self.target, "player", None) is getattr(self.unit, "player", None)
        )
        
        super().complete()

        if captured_on_contact and self.unit.orders:
            order = self.unit.orders[0]
            if getattr(order, "keyword", None) in ("capture", "attack"):
                order.mark_as_complete()
