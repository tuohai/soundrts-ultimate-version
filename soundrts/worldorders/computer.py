from .base import Order


class ComputerOnlyOrder(Order):
    @classmethod
    def is_allowed(cls, unit, *unused_args):
        return not unit.player.is_human


class AutoAttackOrder(ComputerOnlyOrder):

    keyword = "auto_attack"
    is_imperative = True

    def on_queued(self):
        if self.unit.is_idle:
            self.unit.start_moving_to_enemy()


class AutoExploreOrder(ComputerOnlyOrder):

    keyword = "auto_explore"
    is_imperative = True

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        # 计算机单位始终可下达自动探索；人类单位需显式开启 auto_explore
        # （通过 rules.txt 默认配置或玩家手动开启 enable_auto_explore）。
        if not unit.player.is_human:
            return True
        return bool(getattr(unit, "auto_explore", False))

    def on_queued(self):
        player = self.unit.player
        world = player.world
        if getattr(player, "_places_to_explore", None) is None:
            player._places_to_explore = [
                world.grid[name] for name in world.starting_squares
            ]
            world.random.shuffle(player._places_to_explore)
            player._already_explored = set()

    def execute(self):
        self.unit.do_auto_explore()


class WaitOrder(ComputerOnlyOrder):

    keyword = "wait"
    nb_args = 1
    is_imperative = True

    def on_queued(self):
        self._must_deploy = True
        self.target = self.player.get_object_by_id(self.args[0])

    def execute(self):
        if self._must_deploy:
            self.unit.deploy()
            self._must_deploy = False
        if self.player.time_has_come(self.target):
            self.mark_as_complete()