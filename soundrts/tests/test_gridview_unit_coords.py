"""Main-map unit coords must match 1.3.8.1 (client-scale + flipped Y)."""

from soundrts.clientgamegridview import GridView


class _W:
    square_width = 12000
    nb_columns = 3
    nb_lines = 4


class _I:
    def __init__(self):
        self.world = _W()
        self.xcmax = 2
        self.ycmax = 3
        self.square_width = 12.0  # raw / 1000, same as GameInterface
        self.zoom_mode = False
        self.place = None


def test_view_coords_match_1381_contract():
    gv = GridView(_I())
    gv._map_origin = (0, 0)
    gv.square_view_width = 100
    gv.square_view_height = 100
    gv.ymax = 400  # 4 rows * 100

    # EntityView / interface scale (raw/1000): square (0,0) center
    x, y = gv._get_view_coords_from_world_coords(6.0, 6.0)
    assert x == 50
    assert y == 350  # ymax - 0.5*cell

    # Raw milliseconds via _xy_coords (1.3.8.1)
    assert gv._xy_coords(6000, 6000) == (x, y)

    # Higher world Y → higher on screen (smaller screen y)
    _, y_high = gv._get_view_coords_from_world_coords(6.0, 30.0)
    assert y_high < y
