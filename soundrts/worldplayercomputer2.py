from .lib.nofloat import PRECISION
from .worldorders import ORDERS_DICT
from .worldplayerbase import Player

orders = sorted(ORDERS_DICT.keys())  # sort to avoid desync
orders.remove("enter")  # later
orders.remove("stop")
orders.remove("attack")
orders.remove("patrol")
orders.remove("wait")
orders.remove("auto_explore")
orders.remove("auto_attack")
orders.remove("block")
orders.remove("join_group")
orders.remove("cancel_building")
orders.remove("cancel_training")
orders.remove("cancel_upgrading")
orders.remove("rallying_point")


import operator

# Round 4: operator.attrgetter 是 C 实现, 比 Python 函数 ~2-3x 快.
# 此 key 函数在 Computer2.play() 中作 sort key, ~24M 次调用.
_id = operator.attrgetter('id')


def _has(x):
    return True


class Computer2(Player):

    name = ["ai2"]

    def __init__(self, *args, **kargs):
        Player.__init__(self, *args)
        self._ai2_targets_cache = None
        self._ai2_targets_sig = None

    def __repr__(self):
        return "Computer2(%s)" % self.client

    def _random_order(self, unit, targets):
        order = ORDERS_DICT[self.world.random.choice(orders)]
        args = order.nb_args
        menu = order.menu(unit, strict=True)
        if menu:
            order = self.world.random.choice(menu).split()
            if args:
                order.append(self.world.random.choice(targets).id)
            return order

    def play(self):
        self.cheat()
        # sort to avoid desync；按感知版本缓存，避免每 turn 全量重建+排序
        # (cw1 上 Computer2.play 的 sort 约 3.7s)
        sig = (
            getattr(self, "_perception_version", 0),
            len(self.perception),
            len(self.memory),
        )
        if self._ai2_targets_sig != sig or self._ai2_targets_cache is None:
            targets = [x for x in self.perception if not x.is_an_exit]
            targets.extend(x for x in self.memory if not x.is_an_exit)
            targets.sort(key=_id)
            self._ai2_targets_cache = targets
            self._ai2_targets_sig = sig
        else:
            targets = self._ai2_targets_cache
        if not targets:
            return
        for u in self.units:
            if not u.orders:
                order = self._random_order(u, targets)
                if order:
                    u.take_order(order)

    def cheat(self):
        self.has = _has
        self.resources = [1000 * PRECISION for _ in self.resources]
