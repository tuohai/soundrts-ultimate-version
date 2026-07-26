"""Large maps keep preferred cell size and pan (AoE-style), not shrink-to-fit."""

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
    # 当前格应大致落在主视口中部
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
