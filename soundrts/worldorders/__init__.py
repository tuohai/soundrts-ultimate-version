# Base classes
from .base import Order, ComplexOrder, BasicOrder, ORDERS_QUEUE_LIMIT

# Immediate orders
from .immediate import (
    ImmediateOrder,
    ToggleCounterattackOrder,
    EnableCounterattack,
    DisableCounterattack,
    AttackKeyOrder,
    SwitchWeaponOrder,
    SwitchToWeaponOrder,
    ToggleAutoWeaponSwitchOrder,
    EnableAutoWeaponSwitchOrder,
    DisableAutoWeaponSwitchOrder,
    StopOrder,
    ImmediateCancelOrder,
    CancelTrainingOrder,
    CancelUpgradingOrder,
    CancelChangingOrder,
    CancelBuildingOrder,
    EnableAutoGather,
    DisableAutoGather,
    EnableAutoRepair,
    DisableAutoRepair,
    EnableAutoExplore,
    DisableAutoExplore,
    ModeOffensive,
    ModeDefensive,
    ModeGuard,
    ModeChase,
    ModeToggle,
    RallyingPointOrder,
    JoinGroupOrder,
    EquipWeaponOrder,
    UnequipWeaponOrder,
    EquipArmorOrder,
    UnequipArmorOrder,
    EquipBuiltinArmorOrder,
    UseItemOrder,
)

# Production orders
from .production import (
    ProductionOrder,
    StartProduceOrder,
    AutoProduceOrder,
    ManualProduceOrder,
    AutoCultivateOrder,
    ManualCultivateOrder,
    PlowingOrder,
    ProducingOrder,
    StopProduceOrder,
    StopCultivateOrder,
    TrainOrder,
    ResearchOrder,
    AdvanceOrder,
    UpgradeToOrder,
    ChangeToOrder,
    BuildOrder,
)

# Movement orders
from .movement import (
    GoOrder,
    HerdOrder,
    AttackOrder,
    CaptureOrder,
    PatrolOrder,
    BlockOrder,
    RepairOrder,
    BuildPhaseTwoOrder,
)

# Gathering orders
from .gathering import (
    GatherOrder,
)

# Transport orders
from .transport import (
    TransportOrder,
    LoadOrder,
    EnterOrder,
    LoadAllOrder,
    UnloadAllOrder,
)

# Computer orders
from .computer import (
    ComputerOnlyOrder,
    AutoAttackOrder,
    AutoExploreOrder,
    WaitOrder,
)

# Skill orders
from .skills import (
    UseOrder,
    PickupOrder,
    DropOrder,
    GiveOrder,
)

# Build a dictionary containing order classes
# for example: ORDERS_DICT["go"] == GoOrder
ORDERS_DICT = {}

# Collect all Order subclasses from all modules
import inspect

# Get all classes from this module's namespace
for name, obj in list(globals().items()):
    if (inspect.isclass(obj) and 
        issubclass(obj, Order) and 
        obj is not Order and 
        hasattr(obj, 'keyword')):
        ORDERS_DICT[obj.keyword] = obj

# Export the main classes and constants
__all__ = [
    'Order',
    'ComplexOrder', 
    'BasicOrder',
    'ORDERS_QUEUE_LIMIT',
    'ORDERS_DICT',
    # All order classes are also available for direct import
]