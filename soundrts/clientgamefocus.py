from . import msgparts as mp
from .lib.log import warning
from .lib.nofloat import PRECISION
from .lib.voice import voice
from .lib.msgs import nb2msg

_subzone_name = {
    (0, 0): mp.AT_THE_CENTER,
    (0, 1): mp.NORTH,
    (0, -1): mp.SOUTH,
    (1, 0): mp.EAST,
    (-1, 0): mp.WEST,
    (1, 1): mp.NORTHEAST,
    (-1, 1): mp.NORTHWEST,
    (1, -1): mp.SOUTHEAST,
    (-1, -1): mp.SOUTHWEST,
}


class Zoom:

    sub_x = 0
    sub_y = 0

    def __init__(self, parent):
        self.parent = parent
        sq = self.parent.place
        map_precision = getattr(sq.world, "subcell_precision", None)
        if map_precision:
            self.parent._zoom_precision = map_precision
        self.precision = getattr(parent, '_zoom_precision', 3)  # 默认3x3
        # 对于偶数精细度，我们需要特殊处理边界
        self.half_precision = self.precision // 2
        self.xstep = (sq.xmax - sq.xmin) / self.precision
        self.ystep = (sq.ymax - sq.ymin) / self.precision
        self.update_coords()
        
        # 跟踪当前主方格，用于检测方格切换
        self.current_main_square = sq

    @property
    def id(self):
        from .worldroom import format_zoom_target_id

        sq = self.parent.place
        rel_x = (self.sub_x + self.half_precision + 0.5) / self.precision
        rel_y = (self.sub_y + self.half_precision + 0.5) / self.precision
        center_x = sq.xmin + rel_x * (sq.xmax - sq.xmin)
        center_y = sq.ymin + rel_y * (sq.ymax - sq.ymin)
        return format_zoom_target_id(sq.id, center_x, center_y, self.precision)

    @property
    def title(self):
        # 子方格坐标采用 x.y 的表述（1基），如 1.1、2.3
        x_index = self.sub_x + self.precision // 2 + 1  # 1-based
        y_index = self.sub_y + self.precision // 2 + 1  # 1-based
        return nb2msg(int(x_index)) + mp.DOT + nb2msg(int(y_index))

    def move(self, dx, dy, no_collision=False):
        self.parent.follow_mode = False  # or set_obs_pos() will cause trouble
        
        # 更新精细度设置（以防用户在缩放模式中更改了精细度）
        new_precision = getattr(self.parent, '_zoom_precision', 3)
        if new_precision != self.precision:
            self._update_precision(new_precision)
        
        # 保存原始坐标，用于路径阻挡时的恢复
        original_sub_x = self.sub_x
        original_sub_y = self.sub_y
        
        self.sub_x += dx
        self.sub_y += dy
        
        # 根据当前精细度计算边界
        main_square_changed = False
        target_square = None
        move_direction = (0, 0)
        
        # 对于偶数精细度，边界需要特殊处理
        if self.precision % 2 == 0:
            # 偶数精细度的边界
            max_coord = self.half_precision - 1
            min_coord = -self.half_precision
        else:
            # 奇数精细度的边界
            max_coord = self.half_precision
            min_coord = -self.half_precision
        
        def _neighbor(dc: int, dr: int):
            cur = self.parent.place
            if cur is None:
                return None
            col = cur.col + dc
            row = cur.row + dr
            # 环绕
            xcmax = self.parent.world.nb_columns - 1
            ycmax = self.parent.world.nb_lines - 1
            if col < 0:
                col = xcmax
            elif col > xcmax:
                col = 0
            if row < 0:
                row = ycmax
            elif row > ycmax:
                row = 0
            return self.parent.world.grid.get((col, row))

        if self.sub_x > max_coord:
            target_square = _neighbor(1, 0)
            move_direction = (1, 0)
            main_square_changed = True
        elif self.sub_x < min_coord:
            target_square = _neighbor(-1, 0)
            move_direction = (-1, 0)
            main_square_changed = True
        elif self.sub_y > max_coord:
            target_square = _neighbor(0, 1)
            move_direction = (0, 1)
            main_square_changed = True
        elif self.sub_y < min_coord:
            target_square = _neighbor(0, -1)
            move_direction = (0, -1)
            main_square_changed = True
            
        # 如果需要切换主方格：在缩放模式下也要遵守与普通模式相同的连通性阻挡规则
        if main_square_changed and target_square:
            try:
                prefix, collision = self.parent._get_prefix_and_collision(
                    target_square, *move_direction
                )
            except Exception:
                prefix, collision = [], False

            # 若无出口连接（被阻挡）且不忽略碰撞，则回退并播报阻挡提示
            if collision and not no_collision:
                if prefix:
                    try:
                        self.parent._play_movement_sfx(prefix)
                    except Exception:
                        voice.item(prefix)
                # 回退子坐标到原位置
                self.sub_x = original_sub_x
                self.sub_y = original_sub_y
                self.update_coords()
                self.parent.set_obs_pos()
                return None

            # 未被阻挡或显式忽略碰撞：环绕子坐标并切换主方格
            if self.sub_x > max_coord:
                self.sub_x = min_coord
            elif self.sub_x < min_coord:
                self.sub_x = max_coord
            elif self.sub_y > max_coord:
                self.sub_y = min_coord
            elif self.sub_y < min_coord:
                self.sub_y = max_coord

            self.parent.place = target_square
            self.current_main_square = target_square
            # Pass SFX alongside the upcoming zoom.say() coordinate speech.
            if prefix and not no_collision:
                try:
                    self.parent._play_movement_sfx(prefix)
                except Exception:
                    pass
        
        self.update_coords()
        self.parent.set_obs_pos()
        
        # 返回是否发生了主方格切换
        return main_square_changed

    def _update_precision(self, new_precision):
        """更新精细度设置"""
        if new_precision == self.precision:
            return
            
        # 计算当前位置在新精细度下的对应坐标
        # 保持相对位置不变
        old_rel_x = self.sub_x / self.half_precision if self.half_precision > 0 else 0
        old_rel_y = self.sub_y / self.half_precision if self.half_precision > 0 else 0
        
        self.precision = new_precision
        self.half_precision = new_precision // 2
        
        # 重新计算步长
        sq = self.parent.place
        self.xstep = (sq.xmax - sq.xmin) / self.precision
        self.ystep = (sq.ymax - sq.ymin) / self.precision
        
        # 计算新的子区域坐标
        self.sub_x = round(old_rel_x * self.half_precision)
        self.sub_y = round(old_rel_y * self.half_precision)
        
        # 确保坐标在有效范围内
        self.sub_x = max(-self.half_precision, min(self.half_precision, self.sub_x))
        self.sub_y = max(-self.half_precision, min(self.half_precision, self.sub_y))

    def move_to(self, o):
        self.parent.place = o.place
        self.precision = getattr(self.parent, "_zoom_precision", 3)
        self.half_precision = self.precision // 2
        sq = self.parent.place
        self.xstep = (sq.xmax - sq.xmin) / self.precision
        self.ystep = (sq.ymax - sq.ymin) / self.precision
        self.current_main_square = self.parent.place

        obj_x = o.model.x if hasattr(o, "model") else o.x
        obj_y = o.model.y if hasattr(o, "model") else o.y
        self.move_to_world(obj_x, obj_y)
        if not self.contains(o):
            # Fallback: scan subcells
            if self.precision % 2 == 0:
                max_coord = self.half_precision - 1
                min_coord = -self.half_precision
            else:
                max_coord = self.half_precision
                min_coord = -self.half_precision
            found = False
            for sub_y in range(min_coord, max_coord + 1):
                for sub_x in range(min_coord, max_coord + 1):
                    self.sub_x = sub_x
                    self.sub_y = sub_y
                    self.update_coords()
                    if self.contains(o):
                        found = True
                        break
                if found:
                    break
            if not found:
                self.sub_x = 0
                self.sub_y = 0
                self.update_coords()
                warning(
                    "zoom: couldn't find suitable subarea for object, defaulting to center"
                )
        self.parent.set_obs_pos()

    def move_to_world(self, world_x, world_y):
        """Move zoom focus to the sub-cell containing world (x, y) in the current square.

        Returns True if sub_x/sub_y changed.
        """
        self.precision = getattr(self.parent, "_zoom_precision", 3)
        self.half_precision = self.precision // 2
        sq = self.parent.place
        if sq is None:
            return False
        self.xstep = (sq.xmax - sq.xmin) / self.precision
        self.ystep = (sq.ymax - sq.ymin) / self.precision
        self.current_main_square = sq

        if self.precision % 2 == 0:
            max_coord = self.half_precision - 1
            min_coord = -self.half_precision
        else:
            max_coord = self.half_precision
            min_coord = -self.half_precision

        rel_x = (world_x - sq.xmin) / max(sq.xmax - sq.xmin, 1e-9)
        rel_y = (world_y - sq.ymin) / max(sq.ymax - sq.ymin, 1e-9)
        grid_x = rel_x * self.precision - self.half_precision - 0.5
        grid_y = rel_y * self.precision - self.half_precision - 0.5
        best_sub_x = max(min_coord, min(max_coord, int(round(grid_x))))
        best_sub_y = max(min_coord, min(max_coord, int(round(grid_y))))

        old = (self.sub_x, self.sub_y)
        self.sub_x = best_sub_x
        self.sub_y = best_sub_y
        self.update_coords()
        self.parent.set_obs_pos()
        return old != (self.sub_x, self.sub_y)

    def select(self):
        self.parent.target = None
        self.parent.follow_mode = False

    def say(self, prefix=[]):
        from .lib.msgs import localize_voice_msg

        postfix = self.parent.square_postfix(self.parent.place, zoom=self)
        summary = self.parent.place_summary(self.parent.place, zoom=self)
        voice.item(
            localize_voice_msg(prefix + mp.COMMA + self.title + postfix + summary)
        )

    def update_coords(self):
        sq = self.parent.place
        # 使用更精确的坐标计算方法
        # 计算子区域在整个方格中的相对位置
        rel_x = (self.sub_x + self.half_precision + 0.5) / self.precision
        rel_y = (self.sub_y + self.half_precision + 0.5) / self.precision
        
        # 计算子区域的边界
        sub_width = (sq.xmax - sq.xmin) / self.precision
        sub_height = (sq.ymax - sq.ymin) / self.precision
        
        # 计算子区域中心点
        center_x = sq.xmin + rel_x * (sq.xmax - sq.xmin)
        center_y = sq.ymin + rel_y * (sq.ymax - sq.ymin)
        
        # 设置子区域边界（以中心点为基准）
        self.xmin = center_x - sub_width / 2
        self.xmax = center_x + sub_width / 2
        self.ymin = center_y - sub_height / 2
        self.ymax = center_y + sub_height / 2

    def contains(self, obj):
        # 获取对象的坐标
        obj_x = obj.model.x if hasattr(obj, 'model') else obj.x
        obj_y = obj.model.y if hasattr(obj, 'model') else obj.y
        
        # 使用更宽松的包含检测，考虑对象可能在边界上
        margin = min(self.xmax - self.xmin, self.ymax - self.ymin) * 0.01  # 1%的边界容差
        
        return (
            self.xmin - margin <= obj_x <= self.xmax + margin
            and self.ymin - margin <= obj_y <= self.ymax + margin
        )

    def obs_pos(self):
        x = (self.xmin + self.xmax) / 2.0
        y = self.ymin + (self.ymax - self.ymin) / 8.0
        return x / PRECISION, y / PRECISION
