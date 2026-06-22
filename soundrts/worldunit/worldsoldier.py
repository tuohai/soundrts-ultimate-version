from .worldbase import Unit

class Soldier(Unit):

    ground_form = ""
    ai_mode = "offensive"
    can_switch_ai_mode = True
    _basic_skills = {"go", "attack", "patrol", "block", "join_group", "pickup", "drop"}
    is_teleportable = True
    stat_type = "unit"