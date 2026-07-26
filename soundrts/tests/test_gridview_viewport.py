"""Large maps keep preferred cell size and free-pan (AoE edge scroll), not shrink-to-fit."""

from soundrts.clientgamegridview import GridView, _PREFERRED_CELL_PX


class _Place:
    def __init__(self, col, row):
        self.col = col
        self.row = row


class _W:
    square_width = 12000


class _I:
    def __init__(self, cols, rows, place=None):
        self.world = _W()
        self.xcmax = cols - 1
        self.ycmax = rows - 1
        self.square_width = 12.0
        self.zoom_mode = False
        self.place = place


def test_small_map_still_fits_and_centers(monkeypatch):
    import soundrts.clientgamegridview as gv

    class _S:
        def get_width(self):
            return 960

        def get_height(self):
            return 640

    monkeypatch.setattr(gv, "get_screen", lambda: _S())
    g = GridView(_I(4, 3))
    g._update_coefs()
    assert g.square_view_width >= _PREFERRED_CELL_PX
    assert g._viewport_panned is False


def test_large_map_uses_preferred_cell_and_pans(monkeypatch):
    import soundrts.clientgamegridview as gv

    class _S:
        def get_width(self):
            return 960

        def get_height(self):
            return 640

    monkeypatch.setattr(gv, "get_screen", lambda: _S())
    place = _Place(12, 10)
    g = GridView(_I(24, 24, place=place))
    g._update_coefs()
    assert g.square_view_width == _PREFERRED_CELL_PX
    assert g._viewport_panned is True
    # 当前格应大致落在主视口中部（首次居中）
    left, top, vw, vh = g._view_rect
    cx = g._map_origin[0] + place.col * g.square_view_width + g.square_view_width // 2
    cy = (
        g._map_origin[1]
        + g.ymax
        - place.row * g.square_view_height
        - g.square_view_height // 2
    )
    assert left + vw * 0.2 <= cx <= left + vw * 0.8
    assert top + vh * 0.2 <= cy <= top + vh * 0.8


def test_place_change_does_not_move_free_camera(monkeypatch):
    """鼠标划过选格不再跳屏：place 变了镜头仍停在原处。"""
    import soundrts.clientgamegridview as gv

    class _S:
        def get_width(self):
            return 960

        def get_height(self):
            return 640

    monkeypatch.setattr(gv, "get_screen", lambda: _S())
    iface = _I(24, 24, place=_Place(12, 10))
    g = GridView(iface)
    g._update_coefs()
    origin_before = g._map_origin
    iface.place = _Place(20, 20)
    g._update_coefs()
    assert g._map_origin == origin_before


def test_pan_camera_and_edge_scroll(monkeypatch):
    import soundrts.clientgamegridview as gv

    class _S:
        def get_width(self):
            return 960

        def get_height(self):
            return 640

    monkeypatch.setattr(gv, "get_screen", lambda: _S())
    monkeypatch.setattr(gv.pygame.mouse, "get_pos", lambda: (8, 300))
    g = GridView(_I(24, 24, place=_Place(12, 10)))
    g._update_coefs()
    assert g._viewport_panned is True
    ox0 = g._map_origin[0]
    assert g.pan_camera(40, 0) is True
    assert g._map_origin[0] == ox0 + 40
    # 左边缘持续滚屏
    assert g.update_edge_scroll(0.05) is True


def test_wheel_zoom_in_enlarges_cell(monkeypatch):
    import soundrts.clientgamegridview as gv

    class _S:
        def get_width(self):
            return 960

        def get_height(self):
            return 640

    monkeypatch.setattr(gv, "get_screen", lambda: _S())
    g = GridView(_I(24, 24, place=_Place(12, 10)))
    g._update_coefs()
    old = g.square_view_width
    left, top, vw, vh = g._view_rect
    pos = (left + vw // 2, top + vh // 2)
    assert g.zoom_at_mouse(pos, True) is True
    assert g.square_view_width > old
