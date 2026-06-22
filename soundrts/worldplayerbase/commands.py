"""玩家命令处理和控制模块"""

from .. import msgparts as mp
from ..lib import group
from ..lib.log import exception, warning


class CommandsMixin:
    """命令处理和控制相关的方法混入类"""

    def cmd_toggle_cheatmode(self, unused_args=None):
        if self.cheatmode:
            self.cheatmode = False
        else:
            self.cheatmode = True
        # 强制下次更新时刷新感知系统
        self._force_full_update = True

    def cmd_cmd(self, args):
        self.my_eval(args)

    def cmd_speed(self, args):
        if self._is_admin():
            for p in self.world.players:
                p.push("speed", float(args[0]))
        else:
            warning("non admin client tried to change game speed")

    def cmd_quit(self, unused_args):
        self.defeat(force_quit=True)

    def cmd_neutral_quit(self, unused_args):
        if self in self.world.players:
            self.quit_game()

    def _reset_group(self, name):
        if name in self.groups:
            for u in self.groups[name]:
                u.group = None
            self.groups[name] = []

    def cmd_order(self, args):
        self.group_had_enough_mana = False
        try:
            order_id = (
                self.world.get_next_order_id()
            )  # used when several workers must create the same construction site
            forget_previous = args[0] == "0"
            del args[0]
            imperative = args[0] == "1"
            del args[0]
            if args[0] == "reset_group":
                self._reset_group(args[1])
                return
            for u in self.group:
                if u.group is not None and u.group != self.group:
                    if u in u.group:
                        u.group.remove(u)
                    u.group = None
                if self.unit_under_allied_control(u):
                    try:
                        if args[0] == "default":
                            u.take_default_order(
                                args[1], forget_previous, imperative, order_id
                            )
                        else:
                            u.take_order(args, forget_previous, imperative, order_id)
                    except:
                        exception("problem with order: %s" % args)
        except:
            exception("problem with order: %s" % args)

    def cmd_control(self, args):
        self.group = []
        for obj_id in group.decode(" ".join(args)):
            for u in self.allied_control_units:
                if u.id == obj_id:
                    self.group.append(u)
                    break

    def cmd_say(self, args):
        msg = self.name + mp.SAYS + [" ".join(args)]
        self.broadcast_to_others_only(msg)