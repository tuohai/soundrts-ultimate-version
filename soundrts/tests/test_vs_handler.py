"""vs_handler：多项 vs 应拆为 VS_ITEMS 左右子项。"""



import sys



sys.argv = ["pytest"]



from soundrts import msgparts as mp

from soundrts.attributes.vs_handler import VsHandler





class _Parent:

    pass





def test_add_vs_attribute_uses_vs_items_for_multiple_groups():

    attrs = []

    vs = VsHandler(_Parent())

    vs._add_vs_attribute(

        attrs,

        {"footman": 1500, "knight": 1500, "archer": 2000},

        "mdg",

        precision_divide=True,

    )

    assert len(attrs) == 1

    key, name, value = attrs[0]

    assert name == mp.MDG_VS

    assert value[0] == "VS_ITEMS"

    items = value[1]

    assert len(items) == 2

    assert mp.VERSUS[0] in items[0]

    assert mp.VERSUS[0] in items[1]





def test_add_vs_attribute_single_group_no_vs_items_wrapper():

    attrs = []

    vs = VsHandler(_Parent())

    vs._add_vs_attribute(attrs, {"footman": 1500}, "mdg", precision_divide=True)

    assert len(attrs) == 1

    _, name, value = attrs[0]

    assert name == mp.MDG_VS

    assert not isinstance(value, tuple)

    assert mp.VERSUS[0] in value





def test_boolean_vs_attribute_splits_targets():

    attrs = []

    vs = VsHandler(_Parent())

    vs.add_boolean_vs_attribute(

        attrs,

        {"footman": True, "archer": False, "knight": True},

        mp.MDG_EXPLODE + mp.VERSUS,

    )

    assert attrs[0][2][0] == "VS_ITEMS"

    assert len(attrs[0][2][1]) == 2


