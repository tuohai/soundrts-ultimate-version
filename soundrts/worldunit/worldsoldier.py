from .worldbase import Unit

class Soldier(Unit):

    ground_form = ""
    ai_mode = "offensive"
    can_switch_ai_mode = True
    _basic_skills = {"go", "attack", "patrol", "block", "join_group", "pickup", "drop"}
    is_teleportable = True
    stat_type = "unit"
    # D-Phase 2: rules-driven "fire on the move" toggle. 0 = default stop-and-aim
    # behaviour; 1 = ranged units keep advancing while firing (AoE2 Kipchak /
    # Conquistador). The rules parser enforces the int_properties membership,
    # but we set the default here so Soldier and its descendants answer
    # ``hasattr(..., 'can_fire_on_move')`` correctly.
    can_fire_on_move = 0