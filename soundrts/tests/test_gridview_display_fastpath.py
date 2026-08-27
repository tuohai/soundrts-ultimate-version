"""Ctrl+F2 map view: fast path must keep 1.3.8.1 coords and skip double visibility."""

from types import SimpleNamespace

from soundrts.clientgamegridview import GridView, _kind_from_model


class _W:
    square_width = 12000
    nb_columns = 3
    nb_lines = 4
    grid = {}


class _I:
    def __init__(self):
        self.world = _W()
        self.xcmax = 2
        self.ycmax = 3
        self.square_width = 12.0
        self.zoom_mode = False
        self.place = None
        self.player = SimpleNamespace(
            allied=[],
            observed_squares=set(),
            observed_before_squares=set(),
            world=_W(),
        )
        self.group = []
        self.dobjets = {}


class _Model:
    def __init__(self, *, x, y, place, kind="unit", player=None):
        self.x = x
        self.y = y
        self.place = place
        self.is_inside = False
        self.id = id(self)
        self.player = player
        self.resource_type = 0 if kind == "resource" else None
        self.is_a_building = kind == "building"
        self.is_a_building_land = kind == "land"
        self.type_name = kind
        self.hp = 100000
        self.hp_max = 100000
        self.orders = []
        self.airground_type = "ground"


class _View:
    def __init__(self, model):
        self.model = model
        self.id = model.id


def test_kind_from_model():
    assert _kind_from_model(_Model(x=0, y=0, place=object(), kind="resource")) == "resource"
    assert _kind_from_model(_Model(x=0, y=0, place=object(), kind="building")) == "building"
    assert _kind_from_model(_Model(x=0, y=0, place=object(), kind="land")) == "land"
    assert _kind_from_model(_Model(x=0, y=0, place=object(), kind="unit")) == "unit"


def test_xy_coords_cached_match_uncached():
    gv = GridView(_I())
    gv._map_origin = (0, 0)
    gv.square_view_width = 100
    gv.square_view_height = 100
    gv.ymax = 400
    slow = gv._get_view_coords_from_world_coords(6.0, 6.0)
    gv._sw = 12.0
    gv._w2px = 100 / 12000.0
    gv._h2px = 100 / 12000.0
    fast = gv._xy_coords(6000, 6000)
    assert fast == slow == (50, 350)


def test_display_objects_uses_model_and_skips_offscreen(monkeypatch):
    import soundrts.clientgamegridview as gmod

    class _S:
        def get_width(self):
            return 200

        def get_height(self):
            return 200

    monkeypatch.setattr(gmod, "get_screen", lambda: _S())
    iface = _I()
    gv = GridView(iface)
    gv._map_origin = (0, 0)
    gv.square_view_width = 100
    gv.square_view_height = 100
    gv.ymax = 200
    gv._sw = 12.0
    gv._w2px = 100 / 12000.0
    gv._h2px = 100 / 12000.0
    gv._scr_w = 200
    gv._scr_h = 200
    gv._vis_margin = 24

    place = SimpleNamespace(col=0, row=0)
    # 6000,6000 → (50, 150) with ymax=200
    onscreen = _Model(x=6000, y=6000, place=place)
    offscreen = _Model(x=500000, y=500000, place=place)
    iface.dobjets = {1: _View(onscreen), 2: _View(offscreen)}

    painted = []

    def _paint(self, o, model, kind, xy, *args, **kwargs):
        painted.append(model)

    monkeypatch.setattr(GridView, "_paint_object", _paint)
    gv.display_objects()
    assert onscreen in painted
    assert offscreen not in painted


def test_paint_skips_lerp_for_static_kinds(monkeypatch):
    iface = _I()
    gv = GridView(iface)
    gv.square_view_width = 16
    lerped = []

    def _lerp(self, oid, xy, snap_dist=80.0):
        lerped.append(oid)
        return xy

    monkeypatch.setattr(type(gv.fx), "lerped_screen_pos", _lerp)
    monkeypatch.setattr(
        "soundrts.clientgamegridview.pygame.draw.circle", lambda *a, **k: None
    )
    monkeypatch.setattr(
        "soundrts.clientgamegridview.pygame.draw.rect", lambda *a, **k: None
    )
    monkeypatch.setattr(
        "soundrts.clientgamegridview.pygame.draw.polygon", lambda *a, **k: None
    )
    monkeypatch.setattr(
        "soundrts.clientgamegridview.pygame.draw.line", lambda *a, **k: None
    )
    monkeypatch.setattr(
        "soundrts.clientgamegridview.get_screen",
        lambda: type("S", (), {"get_width": lambda s: 64, "get_height": lambda s: 64})(),
    )
    place = object()
    building = _Model(x=1000, y=1000, place=place, kind="building")
    resource = _Model(x=1000, y=1000, place=place, kind="resource")
    unit = _Model(x=1000, y=1000, place=place, kind="unit")
    gv._paint_object(_View(building), building, "building", (10, 10))
    gv._paint_object(_View(resource), resource, "resource", (10, 10))
    gv._paint_object(_View(unit), unit, "unit", (10, 10))
    assert lerped == [unit.id]


def test_display_objects_paints_selected_after_unselected(monkeypatch):
    import soundrts.clientgamegridview as gmod

    class _S:
        def get_width(self):
            return 200

        def get_height(self):
            return 200

    monkeypatch.setattr(gmod, "get_screen", lambda: _S())
    iface = _I()
    gv = GridView(iface)
    gv._map_origin = (0, 0)
    gv.square_view_width = 100
    gv.square_view_height = 100
    gv.ymax = 200
    gv._sw = 12.0
    gv._w2px = 100 / 12000.0
    gv._h2px = 100 / 12000.0
    gv._scr_w = 200
    gv._scr_h = 200
    gv._vis_margin = 24

    place = SimpleNamespace(col=0, row=0)
    a = _Model(x=6000, y=6000, place=place, kind="unit")
    b = _Model(x=6100, y=6100, place=place, kind="unit")
    a.id = 1
    b.id = 2
    iface.group = [2]
    iface.dobjets = {1: _View(a), 2: _View(b)}
    order = []

    def _paint(self, o, model, kind, xy, *args, **kwargs):
        order.append(model.id)

    monkeypatch.setattr(GridView, "_paint_object", _paint)
    gv.display_objects()
    assert order == [1, 2]


def test_stamp_map_view_cache_sets_kind_and_type():
    from soundrts.clientgamegridview import stamp_map_view_cache

    view = _View(_Model(x=0, y=0, place=object(), kind="resource"))
    stamp_map_view_cache(view, view.model)
    assert view._map_kind == "resource"
    assert view._map_type_name == "resource"
    assert view._map_air is False
    assert view.is_memory is False


def test_display_objects_uses_cached_kind(monkeypatch):
    import soundrts.clientgamegridview as gmod

    class _S:
        def get_width(self):
            return 200

        def get_height(self):
            return 200

    monkeypatch.setattr(gmod, "get_screen", lambda: _S())
    iface = _I()
    gv = GridView(iface)
    gv._map_origin = (0, 0)
    gv.square_view_width = 100
    gv.square_view_height = 100
    gv.ymax = 200
    gv._sw = 12.0
    gv._w2px = 100 / 12000.0
    gv._h2px = 100 / 12000.0
    gv._scr_w = 200
    gv._scr_h = 200
    gv._vis_margin = 24

    place = SimpleNamespace(col=0, row=0)
    model = _Model(x=6000, y=6000, place=place)
    view = _View(model)
    view._map_kind = "unit"
    iface.dobjets = {1: view}
    kinds = []

    def _kind(model):
        kinds.append(model)
        return "unit"

    monkeypatch.setattr(gmod, "_kind_from_model", _kind)

    painted = []

    def _paint(self, o, model, kind, xy, *args, **kwargs):
        painted.append(kind)

    monkeypatch.setattr(GridView, "_paint_object", _paint)
    gv.display_objects()
    assert painted == ["unit"]
    assert kinds == []


def test_fog_keeps_same_memory_view_and_stamps_kind():
    from soundrts.clientgame.game_navigation import update_fog_of_war

    class _Mem:
        def __init__(self):
            self.id = 7
            self.place = object()
            self.is_inside = False
            self.initial_model = self
            self.hp = 3
            self.time_stamp = 1
            self.resource_type = None
            self.is_a_building = False
            self.is_a_building_land = False
            self.type_name = "footman"
            self.airground_type = "ground"
            self.player = None

    class _V:
        def __init__(self, m):
            self.model = m
            self.is_memory = True

        def stop(self):
            pass

    m = _Mem()
    v = _V(m)
    iface = SimpleNamespace(
        memory={m},
        perception=set(),
        dobjets={7: v},
        player=SimpleNamespace(
            observed_objects={},
            _forget=None,
            is_an_enemy=lambda _u: False,
        ),
        target=None,
        scout_info=set(),
        new_enemy_units=[],
    )
    update_fog_of_war(iface)
    assert iface.dobjets[7] is v
    assert v.model is m
    assert v._map_kind == "unit"
    assert v._map_type_name == "footman"
