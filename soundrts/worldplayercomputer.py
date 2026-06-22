import re

from soundrts.lib.nofloat import square_of_distance
from soundrts.worldorders import UseOrder, ORDERS_DICT

from .definitions import filter_ai_executable_plan, get_ai, parse_ai_start_settings, rules
from .lib.log import exception, info, warning
from .world_build_rules import (
    building_can_operate,
    effective_can_train,
    is_addon_type,
    requires_build_field_type,
)
from .worldplayercomputer_sc_build import (
    build_worker_count,
    choose_build_target,
    choose_house_build_target,
    choose_near_water_build_target,
    ensure_field_provider_before_build,
    find_train_host,
    maintain_terran_recombine,
    resolve_build_target,
    worker_can_build,
    worker_can_repair,
)
from .worldplayercomputer_water import (
    find_amphibious_crossing,
    movement_target_for_unit,
    path_plane,
)
from .version import IS_DEV_VERSION
from .worldupgrade.base import is_an_upgrade
from .worldplayerbase import Player
from .worldresource import Deposit, Meadow
from .worldunit import BuildingSite
from .worldunit import Soldier
from .worldunit import Worker


def value_as_an_explorer(u):
    air = 1 if u.airground_type == "air" else 0
    return ((air, u.speed, u.hp), u.id)


def is_ground_worker(unit):
    """Land peasants only — excludes boat and other water/air workers."""
    if not isinstance(unit, Worker):
        return False
    return getattr(unit, "airground_type", "ground") == "ground"


def is_water_worker(unit):
    """Water gatherers (e.g. boat) — not used for land economy."""
    if not isinstance(unit, Worker):
        return False
    return getattr(unit, "airground_type", "ground") == "water"


class Computer(Player):

    is_computer_player = True

    # the AI might need a longer memory than the player
    memory_duration = 36000000  # 36000 seconds of world time
    _sensible_building = None

    # Tunable parameters, overridable per AI from ai.txt (see _follow_plan).
    _target_townhalls = 0  # extra bases to maintain (ai.txt: "expand <n>")
    _attack_ratio = 180  # % of enemy menace needed to attack ("attack_ratio")
    counter_skill = 100  # 0-100: how well units use mdg_vs/rdg_vs ("counter_skill")
    _wait_deadline = None  # internal state for the "wait <seconds>" command

    def __init__(self, world, client):
        self._attacked_places = []
        self._orders = {}
        self._previous_choose = {}
        self.neutral = client.neutral
        Player.__init__(self, world, client)
        self.set_ai(client.AI_type)

    def __repr__(self):
        return "Computer(%s)" % self.client

    def init_position(self, parsed_start):
        super().init_position(parsed_start)
        self._apply_ai_start_settings()

    def _default_start_place(self):
        for u in self.units:
            place = getattr(u, "place", None)
            if place is not None:
                return place
        try:
            start_index = (self.number - 1) if self.number is not None else 0
            if 0 <= start_index < len(self.world.starting_squares):
                sq = self.world.starting_squares[start_index]
                return self.world.grid.get(sq)
        except Exception:
            pass
        squares = getattr(self.world, "squares", None)
        if squares:
            return squares[0]
        return None

    def _apply_ai_start_settings(self):
        if self.AI_type == "timers" or self.neutral:
            return
        script_name = self.faction_ai_type(self.AI_type)
        resource_bonus, unit_tokens, population_bonus = parse_ai_start_settings(script_name)
        if resource_bonus:
            for index, qty in enumerate(resource_bonus):
                if not qty or index >= len(self.resources):
                    continue
                self.resources[index] += qty
                self.stats.add("gathered", index, qty)
        if unit_tokens:
            self._apply_ai_start_units(unit_tokens)
        if population_bonus:
            self.population += population_bonus

    def _apply_ai_start_units(self, unit_tokens):
        place = self._default_start_place()
        if place is None:
            warning("AI starting_units: no start place for %s", self.AI_type)
            return
        multiplicator = 1
        for token in unit_tokens:
            if token.startswith("-"):
                self.forbidden_techs.append(token[1:])
                multiplicator = 1
            elif re.match("^[0-9]+$", token):
                multiplicator = int(token)
            else:
                type_name = self.equivalent(token)
                unit_cls = rules.unit_class(type_name)
                if unit_cls is None:
                    warning("AI starting_units: unknown unit '%s' (in ai.txt)", token)
                    multiplicator = 1
                    continue
                if is_an_upgrade(unit_cls):
                    if unit_cls.type_name not in self.upgrades:
                        self.upgrades.append(unit_cls.type_name)
                else:
                    for _ in range(multiplicator):
                        self.add_unit(unit_cls, place, population_cost=0)
                multiplicator = 1

    @property
    def is_cpu_intensive(self):
        return self.AI_type != "timers"

    @property
    def smart_units(self):
        return self.AI_type != "timers"

    def faction_ai_type(self, ai_type):
        if rules.get(self.faction, ai_type):
            result = rules.get(self.faction, ai_type)[0]
        else:
            result = ai_type
        return result

    def set_ai(self, ai_type):
        self.AI_type = ai_type
        if self.AI_type != "timers":
            self._plan = filter_ai_executable_plan(
                get_ai(self.faction_ai_type(ai_type))
            )
            # set or reset default values
            self._line_nb = 0
            self.watchdog = 0
            self.constant_attacks = 0
            self.research = 0
            # tunable economy / aggression parameters (overridable from ai.txt)
            self.nb_workers_to_get = type(self).nb_workers_to_get
            self._target_townhalls = type(self)._target_townhalls
            self._attack_ratio = type(self)._attack_ratio
            self.counter_skill = type(self).counter_skill
            self._wait_deadline = None
            self._update_effect_users_and_workers()  # required by some tests

    _previous_linechange = 0
    __line_nb = 0
    ##    _prev_line_nb = None

    def get_line_nb(self):
        return self.__line_nb

    def set_line_nb(self, value):
        self.__line_nb = value
        self._previous_linechange = self.world.time

    _line_nb = property(get_line_nb, set_line_nb)

    def _follow_plan(self):
        if not self._plan:
            return
        if (
            self.watchdog
            and self.world.time > self._previous_linechange + self.watchdog * 1000
        ):
            self._line_nb += 1
        self._line_nb %= len(self._plan)
        line = self._plan[self._line_nb]
        cmd = line.split()
        if cmd:
            if cmd[0] == "goto":
                if re.match("^[+-][0-9]+$", cmd[1]):
                    self._line_nb += int(cmd[1])
                elif "label " + cmd[1] in self._plan:
                    self._line_nb = self._plan.index("label " + cmd[1])
                elif re.match("^[0-9]+$", cmd[1]):
                    self._line_nb = int(cmd[1])
                else:
                    warning("goto: wrong destination: %s", cmd[1])
                    self._line_nb += 1
            elif cmd[0] == "label":
                self._line_nb += 1
                info(cmd[1])
            elif cmd[0] == "goto_random":
                dest = self.world.random.choice(cmd[1:])
                if "label " + dest in self._plan:
                    self._line_nb = self._plan.index("label " + dest)
                else:
                    warning("goto_random: label not found: %s", dest)
                    self._line_nb += 1
            elif cmd[0] == "attack":
                self.constant_attacks = 1
                self._line_nb += 1
            elif cmd[0] in ("watchdog", "constant_attacks", "research"):
                setattr(self, cmd[0], int(cmd[1]))
                self._line_nb += 1
            elif cmd[0] in ("workers", "expand", "attack_ratio", "counter_skill"):
                if len(cmd) > 1 and re.match("^[0-9]+$", cmd[1]):
                    value = int(cmd[1])
                    if cmd[0] == "workers":
                        self.nb_workers_to_get = value
                    elif cmd[0] == "expand":
                        self._target_townhalls = value
                    elif cmd[0] == "counter_skill":
                        self.counter_skill = max(0, min(100, value))
                    else:  # attack_ratio
                        self._attack_ratio = max(1, value)
                else:
                    warning("%s: expected a number (in ai.txt)", cmd[0])
                self._line_nb += 1
            elif cmd[0] == "wait":
                # Stay on this line until the delay (in seconds) has elapsed.
                # A non-zero "watchdog" still overrides it as a safety net.
                if self._wait_deadline is None:
                    seconds = (
                        int(cmd[1])
                        if len(cmd) > 1 and re.match("^[0-9]+$", cmd[1])
                        else 0
                    )
                    self._wait_deadline = self.world.time + seconds * 1000
                if self.world.time >= self._wait_deadline:
                    self._wait_deadline = None
                    self._line_nb += 1
            elif cmd[0] == "get":
                n = 1
                done = True
                for w in cmd[1:]:
                    if re.match("^[0-9]+$", w):
                        n = int(w)
                    elif w in rules.classnames():
                        if not self.get(n, self.equivalent(w)):
                            done = False
                            break
                        n = 1
                    else:
                        warning("get: unknown unit: '%s' (in ai.txt)", w)
                        n = 1
                if done:
                    self._line_nb += 1
            else:
                warning("unknown command: '%s' (in ai.txt)", cmd[0])
                self._line_nb += 1

    def _best_warehouse(self, place=None):
        return rules.unit_class(self.equivalent("townhall"))

    def _warehouse_economy_enabled(self):
        wh = self._best_warehouse()
        return wh is not None and bool(getattr(wh, "storable_resource_types", None))

    def _auto_warehouse_expansion_enabled(self):
        """Only build extra warehouse buildings when they are not the main base."""
        wh_type = self._best_warehouse()
        if wh_type is None:
            return False
        townhall = self.equivalent("townhall")
        if wh_type.type_name == townhall and self.nb([townhall]) >= 1:
            return False
        return True

    def _issue_build(self, type_name, target, workers=None):
        cls = rules.unit_class(type_name)
        maker_cls = rules.unit_class(self.equivalent("peasant"))
        if cls is None or maker_cls is None:
            return False
        if workers is None:
            workers = self._workers
        target_id = target.id if hasattr(target, "id") else target
        limit = build_worker_count(maker_cls, cls)
        issued = 0
        for w in workers:
            if issued >= limit:
                break
            if worker_can_build(w, type_name):
                w.take_order(["build", type_name, target_id])
                issued += 1
        return issued > 0

    def _build_a_warehouse_for(self, deposit):
        def nearby_workers():
            return [
                v
                for v in self._workers
                if (
                    v.place is deposit.place
                    or v.orders
                    and v.orders[0].keyword == "gather"
                    and (
                        v.orders[0].target is None
                        or v.orders[0].target.place is deposit.place
                    )
                )
            ]

        nearby_workers = nearby_workers()
        if not nearby_workers:
            return
        # 2秒时间桶缓存“就近仓库”结果，避免在同一时间窗口内重复最短路计算
        try:
            current_time = self.world.time
            tb = current_time // 2000
            if not hasattr(self, '_nearest_wh_cache'):
                self._nearest_wh_cache = {}
                self._nearest_wh_bucket = -1
            if self._nearest_wh_bucket != tb:
                self._nearest_wh_cache.clear()
                self._nearest_wh_bucket = tb
            wh_key = (deposit.place.id, deposit.resource_type, True)
            wh = self._nearest_wh_cache.get(wh_key)
            if wh is None:
                wh = self.nearest_warehouse(
                    deposit.place, deposit.resource_type, include_building_sites=True
                )
                self._nearest_wh_cache[wh_key] = wh
        except Exception:
            wh = self.nearest_warehouse(
                deposit.place, deposit.resource_type, include_building_sites=True
            )
        if isinstance(wh, BuildingSite):
            if getattr(wh, "_self_construct", False):
                return
            for v in nearby_workers:
                if worker_can_repair(v):
                    v.take_order(["repair", wh.id])
                    return
        elif (
            wh is None
            or deposit.place.shortest_path_distance_to(wh.place, self, avoid=True)
            > self.world.square_width
        ):
            wh_type = self._best_warehouse(deposit.place)
            meadow = choose_build_target(
                self, wh_type, starting_place=deposit.place
            ) or self.choose(Meadow, starting_place=deposit.place)
            if meadow:
                self._issue_build(wh_type.type_name, meadow, nearby_workers)

    def _maintain_expansions(self):
        """Build extra town halls (new bases) up to the ``expand`` target.

        The starting town hall counts toward the total, so ``expand 2`` makes
        the AI build a single additional base. Disabled by default (``0``).
        """
        if self._target_townhalls <= 0:
            return
        townhall = self.equivalent("townhall")
        cls = rules.unit_class(townhall)
        if cls is None:
            return
        if self.future_nb([townhall]) >= self._target_townhalls:
            return
        if self.missing_resources(cls.cost):
            return
        self.build_or_train_or_upgradeto_or_summon(townhall)

    def _build_a_warehouse_if_useful(self):
        if not self._warehouse_economy_enabled() or not self._auto_warehouse_expansion_enabled():
            return
        warehouse = self._best_warehouse()
        if warehouse is None or self.missing_resources(warehouse.cost):
            return
        for deposit in [
            o.target
            for u in self._workers
            for o in u.orders
            if o.keyword == "gather"
            and o.target is not None
            and o.target.place is not None
        ]:
            self._build_a_warehouse_for(deposit)

    def idle_buildings_research(self):
        for u in self.units:
            if u.orders:
                continue
            # 普通科技：can_research / research
            for t in u.can_research:
                unit_type = self.unit_class(t)
                if unit_type is None:  # 跳过无效的研究类型
                    continue
                if (
                    not self.future_nb([t])
                    and not self.missing_resources(unit_type.cost)
                    and self.potential(unit_type.cost) > 3
                ):
                    u.take_order(["research", t])
            # 时代推进：can_advance / advance（与科技通道完全分离）
            for t in getattr(u, "can_advance", ()) or ():
                unit_type = self.unit_class(t)
                if unit_type is None:
                    continue
                if (
                    not self.future_nb([t])
                    and not self.missing_resources(unit_type.cost)
                    and self.potential(unit_type.cost) > 3
                ):
                    u.take_order(["advance", t])

    def _is_powerful_enough(self, units, place):
        # sometimes population limit prevents units with more than 1 population cost
        # _attack_ratio is the % of enemy menace required before attacking; a
        # lower value (set from ai.txt) makes the AI commit to fights sooner.
        if self.used_population < self.world.population_limit - 5:
            ratio = self._attack_ratio
        else:
            ratio = min(100, self._attack_ratio)
        return (
            sum(u.menace for u in units if u.speed > 0 and isinstance(u, Soldier))
            > self.enemy_menace(place) * ratio // 100
        )

    def _send_workers_to_forgotten_building_sites(self):
        for site in self._building_sites:
            if getattr(site, "_self_construct", False):
                continue
            if not getattr(site, "is_repairable", False):
                continue
            if not any(worker_can_repair(u) for u in self._workers):
                continue
            if not [
                u for u in self._workers if u.orders and u.orders[0].target == site
            ]:
                self.order(4, Worker, ["repair", site.id], requisition=True, near=site)
                break

    def _can_afford_production_cost(self, unit_or_class):
        if hasattr(unit_or_class, "type"):
            unit_class = unit_or_class.type
        else:
            unit_class = unit_or_class
        cost = getattr(unit_class, "production_cost", None)
        if not cost:
            return True
        return not self.missing_resources(cost)

    def _deposit_resource_index(self, deposit):
        if not isinstance(deposit, Deposit):
            return None
        resource_type = getattr(deposit, "resource_type", None)
        if resource_type == "resource1":
            return 0
        if resource_type == "resource2":
            return 1
        if resource_type == "resource3":
            return 2
        if resource_type and resource_type.startswith("resource"):
            try:
                return int(resource_type[8:]) - 1
            except ValueError:
                return None
        return None

    def _worker_can_gather_deposit(self, worker, deposit):
        allowed = getattr(worker, "can_gather_deposit", None) or []
        if "all" in allowed:
            return True
        type_name = getattr(deposit, "type_name", None)
        return type_name in allowed

    def _worker_origin_for_gather(self):
        origin = self._builders_place()
        if origin is None:
            for u in self._workers:
                origin = self._world_place_for_unit(u)
                if origin is not None:
                    break
        return origin

    def _reachable_deposits(self, from_place, resource_index=None, worker=None):
        if from_place is None:
            return []
        found = []
        for o in self.perception.union(self.memory):
            if not isinstance(o, Deposit) or not self._gather_target_ok(o):
                continue
            idx = self._deposit_resource_index(o)
            if resource_index is not None and idx != resource_index:
                continue
            if worker is not None and not self._worker_can_gather_deposit(worker, o):
                continue
            dist = from_place.shortest_path_distance_to(o.place, self, avoid=True)
            if dist is not None and dist < float("inf"):
                found.append((dist, o, "ground"))
            elif find_amphibious_crossing(from_place, o.place, self):
                found.append((float("inf"), o, "amphibious"))
        found.sort(key=lambda x: (0 if x[2] == "ground" else 1, x[0]))
        return [(o, mode) for _, o, mode in found]

    def _has_reachable_deposit(self, resource_index):
        return bool(self._reachable_deposits(self._worker_origin_for_gather(), resource_index))

    def _resource_low_threshold(self, resource_index):
        return 20 if resource_index == 2 else 40

    def _storage_type_for_resource(self, resource_index):
        if resource_index == 1:
            return self.equivalent("lumbermill")
        return self.equivalent("townhall")

    def _ensure_deposit_supply(self, resource_index):
        storage = self._storage_type_for_resource(resource_index)
        if storage and self.nb(storage) == 0 and self.future_nb(storage) == 0:
            self.get(1, storage)
        self._try_remote_deposit_expansion(resource_index)

    def _send_workers_to_gather_amphibious(self, workers, deposit):
        if not workers or deposit is None:
            return []
        sent = self._send_ground_units_amphibious(workers, deposit.place)
        for u in sent:
            u.take_order(["gather", deposit.id], forget_previous=False)
        return sent

    def _try_send_worker_to_gather_amphibious(self, worker, target):
        if not isinstance(target, Deposit):
            return False
        if not self._worker_can_gather_deposit(worker, target):
            return False
        origin = self._world_place_for_unit(worker)
        if origin is None:
            return False
        dist = origin.shortest_path_distance_to(target.place, self, avoid=True)
        if dist is not None and dist < float("inf"):
            return False
        if not find_amphibious_crossing(origin, target.place, self):
            return False
        if not self._available_water_transports():
            return False
        return bool(self._send_workers_to_gather_amphibious([worker], target))

    def _try_remote_deposit_expansion(self, resource_index):
        """Ferry peasants across water when a resource is low but only offshore."""
        if not self._map_has_water():
            return False
        if self.resources[resource_index] >= self._resource_low_threshold(resource_index):
            return False
        origin = self._worker_origin_for_gather()
        if origin is None:
            return False
        deposits = self._reachable_deposits(origin, resource_index)
        if any(mode == "ground" for _, mode in deposits):
            return False
        amphib = [(o, m) for o, m in deposits if m == "amphibious"]
        if not amphib or not self._available_water_transports():
            return False
        deposit = amphib[0][0]
        idle = [
            u
            for u in self._workers
            if is_ground_worker(u)
            and not u.orders
            and self._worker_can_gather_deposit(u, deposit)
        ]
        if not idle:
            return False
        if not self._send_workers_to_gather_amphibious(idle[:4], deposit):
            return False
        storage = self._storage_type_for_resource(resource_index)
        if storage and self.nb(storage) == 0 and self.future_nb(storage) == 0:
            self.get(1, storage)
        return True

    def _resource_building_types(self, resource_type):
        """Return buildable building type names that produce the given resource."""
        result = []
        peasant_class = rules.unit_class(self.equivalent("peasant"))
        if peasant_class is None:
            return result
        for name in rules.class_rules_attr(peasant_class, "can_build", ()):
            uc = rules.unit_class(name)
            if uc is None:
                continue
            if getattr(uc, "production_type", None) != resource_type:
                continue
            if not (
                getattr(uc, "auto_cultivate", 0)
                or getattr(uc, "auto_production", 0)
            ):
                continue
            result.append(name)
        return result

    def _target_resource_building_count(self, resource_index):
        workers = max(1, len(self._workers))
        if resource_index == 2:
            return max(2, workers // 4)
        if resource_index == 0:
            return max(1, workers // 8)
        return 1

    def _maintain_resource_buildings(self):
        low = []
        for i, amount in enumerate(self.resources):
            threshold = self._resource_low_threshold(i)
            if amount >= threshold:
                continue
            if i == 2:
                farm_cls = rules.unit_class("farm")
                if farm_cls and not (
                    self._can_afford_production_cost(farm_cls)
                    or self._has_reachable_deposit(1)
                ):
                    continue
            low.append(i)
        if low:
            self._ensure_resource_buildings(low)

    def _ensure_resource_buildings(self, missing_indices):
        for i in missing_indices:
            self._ensure_deposit_supply(i)
        for i in missing_indices:
            resource_type = f"resource{i + 1}"
            target = self._target_resource_building_count(i)
            for type_name in self._resource_building_types(resource_type):
                t = rules.unit_class(type_name)
                if t is None:
                    continue
                if self.future_nb([type_name]) >= target:
                    continue
                if self.missing_resources(t.cost):
                    continue
                self.build_or_train_or_upgradeto_or_summon(t)
                return

    def _idle_resource_buildings_produce(self):
        for u in self.units:
            if not getattr(u, "is_a_building", False) or getattr(u, "is_producing", False):
                continue
            if u.orders:
                continue
            if getattr(u, "auto_cultivate", 0):
                if not self._can_afford_production_cost(u):
                    continue
                u.take_order(["start_automatic_cultivate"])
            elif getattr(u, "auto_production", 0):
                if not self._can_afford_production_cost(u):
                    continue
                u.take_order(["auto_produce"])

    def _deposit_has_resources(self, target):
        if isinstance(target, Deposit):
            return getattr(target, "qty", 0) > 0
        if hasattr(target, "resource_qty"):
            return target.resource_qty > 0
        return True

    def _gather_target_ok(self, target):
        if target is None or target.place is None:
            return False
        return self._deposit_has_resources(target)

    def _worker_can_hunt(self, worker):
        skills = getattr(worker, "basic_skills", None) or getattr(
            worker, "_basic_skills", ()
        )
        if "attack" not in skills:
            return False
        deposits = getattr(worker, "can_gather_deposit", None) or []
        if not deposits:
            return False
        return "food_carcass" in deposits or "all" in deposits

    def _worker_can_herd(self, worker):
        if not getattr(worker, "can_herd", 0):
            return False
        skills = getattr(worker, "basic_skills", None) or getattr(
            worker, "_basic_skills", ()
        )
        return "herd" in skills

    def _herded_animals(self, worker):
        result = []
        for p in self.world.players:
            if not getattr(p, "neutral", False):
                continue
            for u in p.units:
                if (
                    getattr(u, "_herd_leader", None) is worker
                    and getattr(u, "hp", 0) > 0
                ):
                    result.append(u)
        return result

    def _world_place_for_unit(self, unit):
        """Map square for pathfinding; None when the unit is inside a container."""
        if getattr(unit, "is_inside", False):
            return None
        place = getattr(unit, "place", None)
        if place is None or not hasattr(place, "shortest_path_distance_to"):
            return None
        return place

    def _world_place_for_pathfinding(self, place):
        """Map square for pathfinding; unwrap container interiors."""
        if getattr(place, "is_inside_place", False):
            place = getattr(place, "outside", None)
        if place is None or not hasattr(place, "shortest_path_distance_to"):
            return None
        return place

    def _herd_dropoff_building(self, worker):
        place = self._world_place_for_unit(worker)
        if place is None:
            return None
        wh = self.nearest_warehouse(place, "resource3", include_building_sites=False)
        if wh is not None and wh.place is not None:
            return wh
        buildings = [
            u
            for u in self.units
            if getattr(u, "is_a_building", False)
            and u.place is not None
            and "resource3" in getattr(u, "storable_resource_types", ())
        ]
        if not buildings:
            return None
        buildings.sort(
            key=lambda b: place.shortest_path_distance_to(b.place, self, avoid=True)
        )
        return buildings[0]

    def _maintain_worker_herding(self, worker):
        """已绑定羊群的工人：引回基地，到基地后宰杀采集。"""
        if getattr(worker, "is_inside", False):
            return False
        herded = self._herded_animals(worker)
        if not herded:
            return False
        dropoff = self._herd_dropoff_building(worker)
        if dropoff is None or dropoff.place is None:
            return False
        if worker.place is dropoff.place:
            for animal in herded:
                if animal.place is worker.place and self._worker_can_hunt(worker):
                    worker.take_order(["attack", animal.id], imperative=True)
                    return True
            return False
        worker.take_order(["go", dropoff.place.id])
        return True

    def _choose_herd_target(self, worker):
        if not self._worker_can_herd(worker):
            return None
        origin = self._world_place_for_unit(worker)
        if origin is None:
            return None
        if self._herded_animals(worker):
            return None
        animals = [
            o
            for o in self.perception.union(self.memory)
            if getattr(o, "herdable", 0)
            and getattr(o, "hp", 0) > 0
            and o.place is not None
            and getattr(getattr(o, "player", None), "neutral", False)
            and getattr(o, "_herd_leader", None) is None
        ]
        if not animals:
            return None
        if self._herd_dropoff_building(worker) is None:
            return None
        animals.sort(
            key=lambda a: origin.shortest_path_distance_to(
                a.place, self, avoid=True
            )
        )
        for animal in animals:
            if self.square_is_dangerous(animal.place):
                continue
            if (
                origin.shortest_path_distance_to(animal.place, self, avoid=True)
                < float("inf")
            ):
                return animal
        return None

    def _choose_hunt_target(self, worker):
        if not self._worker_can_hunt(worker):
            return None
        origin = self._world_place_for_unit(worker)
        if origin is None:
            return None
        animals = [
            o
            for o in self.perception.union(self.memory)
            if getattr(o, "is_huntable", 0)
            and getattr(o, "hp", 0) > 0
            and o.place is not None
            and getattr(getattr(o, "player", None), "neutral", False)
            and not (
                getattr(o, "herdable", 0) and self._worker_can_herd(worker)
            )
        ]
        if not animals:
            return None
        animals.sort(
            key=lambda a: origin.shortest_path_distance_to(
                a.place, self, avoid=True
            )
        )
        for animal in animals:
            if self.square_is_dangerous(animal.place):
                continue
            if (
                origin.shortest_path_distance_to(animal.place, self, avoid=True)
                < float("inf")
            ):
                return animal
        return None

    def _choose_gather_target(self, worker):
        origin = self._world_place_for_unit(worker)
        if origin is None:
            return None
        deposits = [
            o
            for o in self.perception.union(self.memory)
            if isinstance(o, Deposit)
            and self._gather_target_ok(o)
            and Worker._gather_terrain_ok_for_unit(worker, o)
        ]
        if deposits:
            deposits.sort(
                key=lambda d: origin.shortest_path_distance_to(
                    d.place, self, avoid=True
                )
            )
            for deposit in deposits:
                if origin.shortest_path_distance_to(
                    deposit.place, self, avoid=True
                ) < float("inf"):
                    return deposit
        deposit = self.choose(Deposit, starting_place=origin, random=True)
        if (
            deposit
            and self._gather_target_ok(deposit)
            and Worker._gather_terrain_ok_for_unit(worker, deposit)
        ):
            return deposit
        building_targets = [
            u
            for u in self.units
            if getattr(u, "is_a_building", False)
            and getattr(u, "resource_qty", 0) > 0
            and getattr(u, "resource_type", None)
            and u.place is not None
            and not self.square_is_dangerous(u.place)
            and Worker._gather_terrain_ok_for_unit(worker, u)
        ]
        if building_targets:
            building_targets.sort(
                key=lambda b: origin.shortest_path_distance_to(
                    b.place, self, avoid=True
                )
            )
            return building_targets[0]
        deposit = self.choose(Deposit, starting_place=origin, random=True)
        if (
            deposit
            and self._gather_target_ok(deposit)
            and Worker._gather_terrain_ok_for_unit(worker, deposit)
        ):
            return deposit
        return None

    def _choose_water_gather_target(self, worker):
        origin = self._world_place_for_unit(worker)
        if origin is None:
            return None
        plane = path_plane(worker)
        deposits = [
            o
            for o in self.perception.union(self.memory)
            if isinstance(o, Deposit)
            and self._gather_target_ok(o)
            and Worker._gather_terrain_ok_for_unit(worker, o)
        ]
        if deposits:
            deposits.sort(
                key=lambda d: origin.shortest_path_distance_to(
                    d.place, self, plane, avoid=True
                )
            )
            for deposit in deposits:
                if origin.shortest_path_distance_to(
                    deposit.place, self, plane, avoid=True
                ) < float("inf"):
                    return deposit
        deposit = self.choose(Deposit, starting_place=origin, random=True)
        if (
            deposit
            and self._gather_target_ok(deposit)
            and Worker._gather_terrain_ok_for_unit(worker, deposit)
        ):
            return deposit
        return None

    def _idle_water_workers_gather(self):
        for u in self.units:
            if not is_water_worker(u) or not Worker.has_gather_permissions(u):
                continue
            if not self._water_unit_is_idle_for_ai_orders(u):
                continue
            target = self._choose_water_gather_target(u)
            if target:
                u.take_order(["gather", target.id])
                try:
                    self._gathered_deposits[target] += 1
                except Exception:
                    self._gathered_deposits[target] = 1

    def _idle_workers_gather(self):
        for u in self._workers:
            if u.orders:
                continue
            if getattr(u, "is_inside", False):
                continue
            if self._maintain_worker_herding(u):
                continue
            target = self._choose_gather_target(u)
            if target:
                if self._try_send_worker_to_gather_amphibious(u, target):
                    continue
                u.take_order(["gather", target.id])
                try:
                    self._gathered_deposits[target] += 1
                except:
                    self._gathered_deposits[target] = 1
                continue
            herd_target = self._choose_herd_target(u)
            if herd_target:
                u.take_order(["herd", herd_target.id], imperative=True)
                continue
            hunt_target = self._choose_hunt_target(u)
            if hunt_target:
                u.take_order(["attack", hunt_target.id], imperative=True)

    def _should_play_this_turn(self):
        players = self.world.cpu_intensive_players()
        turn = players.index(self) * 10 // len(players)
        return self.world.turn % 10 == turn

    def _defensive_routine(self):
        if self._sensible_building is not None:
            if self._sensible_building not in self.units:
                self._sensible_building = None

        # Only pull wounded soldiers back to the main base. Sending every idle
        # fighter to the mining site each AI turn cancels their orders and
        # spams acknowledgments without accomplishing anything useful.
        townhall = self.equivalent("townhall")
        heal_place = None
        for u in self.units:
            if getattr(u, "type_name", None) == townhall:
                heal_place = getattr(u, "place", None)
                break
        if heal_place is not None:
            wounded = [
                u
                for u in self._idle_fighters
                if u.hp < u.hp_max and u.place is not heal_place
            ]
            if wounded:
                self._send_units(wounded, heal_place)

        # build static defenses
        gate = rules.unit_class("gate")
        if self._sensible_building is not None and gate is not None:

            def nearest_exit(u):
                result = sorted(
                    u.place.exits, key=lambda e: square_of_distance(u.x, u.y, e.x, e.y)
                )
                if result:
                    return result[0]

            e = nearest_exit(self._sensible_building)
            if (
                e is not None
                and not e.is_blocked()
                and self.gather(gate.cost, 0)
                and any(worker_can_build(w, "gate") for w in self._workers)
            ):
                self._issue_build("gate", e, self._workers)

    nb_workers_to_get = 10

    def _naval_destroyer_target(self):
        """Target destroyer count for _try_maintain_naval by difficulty."""
        if self.AI_type in ("nightmare", "expert"):
            return 4
        if self.AI_type == "advanced":
            return 3
        if self.AI_type == "intermediate":
            return 2
        return 0

    def _try_maintain_naval(self):
        """On water maps, keep a dock and a small navy for crossing / river fights."""
        if not self._map_has_water():
            return
        if self.AI_type in ("beginner", "timers"):
            return
        shipyard = self.equivalent("shipyard")
        lumbermill = self.equivalent("lumbermill")
        if self.nb(shipyard) == 0:
            if self.nb(lumbermill) == 0 and self.future_nb(lumbermill) == 0:
                self.get(1, lumbermill)
                return
            if self.future_nb(shipyard) == 0:
                self.get(1, shipyard)
            return
        boat = self.equivalent("boat")
        destroyer = self.equivalent("destroyer")
        if self.nb(boat) < 2 and self.future_nb(boat) < 2:
            self.get(2, boat)
            return
        dd_target = self._naval_destroyer_target()
        if dd_target and self.nb(destroyer) < dd_target and self.future_nb(destroyer) < dd_target:
            self.get(dd_target, destroyer)

    def _is_idle_for_ai_orders(self, unit):
        """True when a unit has no active order (impossible orders are cleared)."""
        if not unit.orders:
            return True
        if unit.orders[0].is_impossible:
            unit.cancel_all_orders()
            return True
        return False

    def _water_unit_is_idle_for_ai_orders(self, unit):
        return self._is_idle_for_ai_orders(unit)

    def _naval_patrol_targets(self):
        """Places naval units should sail toward (enemies, or hostile bases as fallback)."""
        places = []
        seen = set()
        for p in self._enemy_presence:
            p = self._world_place_for_pathfinding(p)
            if p is None or id(p) in seen:
                continue
            seen.add(id(p))
            places.append(p)
        if places:
            return places
        seen = set()
        result = []
        for player in self.world.players:
            if not self.player_is_a_hostile_enemy(player):
                continue
            for unit in player.units:
                place = self._world_place_for_pathfinding(getattr(unit, "place", None))
                if place is None or id(place) in seen:
                    continue
                seen.add(id(place))
                result.append(place)
            if result:
                return result
        water_squares = [
            sq for sq in self.world.squares if getattr(sq, "is_water", False)
        ]
        if water_squares:
            return [water_squares[len(water_squares) // 2]]
        return []

    def _sanitize_water_unit_orders(self):
        """Cancel AI orders that send water units onto land (e.g. boat gather)."""
        for u in self.units:
            if getattr(u, "airground_type", None) != "water":
                continue
            if not u.orders:
                continue
            order = u.orders[0]
            keyword = order.keyword
            if keyword == "gather":
                target = getattr(order, "target", None)
                if target and not Worker._gather_terrain_ok_for_unit(u, target):
                    u.cancel_all_orders()
                continue
            if keyword in ("herd", "auto_explore", "build", "repair"):
                u.cancel_all_orders()
                continue
            if keyword == "go":
                target = getattr(order, "target", None)
                if target is None:
                    continue
                place = (
                    target
                    if hasattr(target, "strict_neighbors")
                    else getattr(target, "place", None)
                )
                if place is None or getattr(place, "is_water", False):
                    continue
                move_target = movement_target_for_unit(u, place, self)
                u.cancel_all_orders()
                if getattr(move_target, "is_water", False):
                    u.take_order(["go", move_target.id], forget_previous=True)

    def _idle_water_workers(self):
        """Return idle water workers to the nearest reachable water square."""
        for u in self.units:
            if getattr(u, "airground_type", None) != "water":
                continue
            if u.speed <= 0 or not self._water_unit_is_idle_for_ai_orders(u):
                continue
            place = u.place
            if place is None:
                continue
            if getattr(place, "is_water", False):
                continue
            neighbors = [
                n
                for n in place.strict_neighbors
                if getattr(n, "is_water", False)
            ]
            if not neighbors:
                continue
            target = min(
                neighbors,
                key=lambda sq: place.shortest_path_distance_to(
                    sq, self, "water"
                ),
            )
            u.take_order(["go", target.id], forget_previous=True)

    def _idle_naval_patrol(self):
        """Send idle boats and warships on water toward enemies or the lake center."""
        if not self._map_has_water():
            return
        targets = self._naval_patrol_targets()
        if not targets:
            return

        for u in self.units:
            if getattr(u, "airground_type", None) != "water":
                continue
            if u.speed <= 0 or getattr(u, "is_inside", False):
                continue
            if not self._water_unit_is_idle_for_ai_orders(u):
                continue
            place = u.place
            if place is None or not getattr(place, "is_water", False):
                continue
            # Boats are transports — keep them free for amphibious landings.
            if getattr(u, "transport_capacity", 0) > 0:
                continue

            best_move = None
            best_key = None
            for target_place in targets:
                move_target = movement_target_for_unit(u, target_place, self)
                if not getattr(move_target, "is_water", False):
                    continue
                if move_target is place:
                    continue
                key = place.shortest_path_distance_to(move_target, self, "water")
                if key is None or key == float("inf"):
                    continue
                if best_key is None or key < best_key:
                    best_key = key
                    best_move = move_target
            if best_move is not None:
                u.take_order(["go", best_move.id], forget_previous=True)

    def _idle_ground_assault_units(self):
        from .worldunit import Soldier

        return [
            u
            for u in self.units
            if isinstance(u, Soldier)
            and getattr(u, "airground_type", None) == "ground"
            and u.speed > 0
            and not getattr(u, "is_inside", False)
            and self._is_idle_for_ai_orders(u)
        ]

    def _try_transport_assaults(self):
        """Ferry blocked ground troops by boat or air transport toward enemy bases."""
        targets = [
            p
            for p in self._naval_patrol_targets()
            if p is not None and not getattr(p, "is_water", False)
        ]
        if not targets:
            return
        candidates = self._idle_ground_assault_units()
        if not candidates:
            return
        for dest in targets:
            need = self._ground_units_needing_transport(candidates, dest)
            if not need:
                continue
            mode = self._choose_transport_mode(need, dest)
            if mode == "amphibious":
                if not self._available_water_transports():
                    continue
                sent = self._send_ground_units_amphibious(need, dest)
            elif mode == "airborne":
                if not self._available_air_transports():
                    continue
                sent = self._send_ground_units_airborne(need, dest)
            else:
                continue
            if sent:
                sent_ids = {id(u) for u in sent}
                candidates = [u for u in candidates if id(u) not in sent_ids]

    def _try_amphibious_landings(self):
        """Backward-compatible entry point for boat/air assault scheduling."""
        self._try_transport_assaults()

    def play(self):
        if self.AI_type == "timers":
            return
        if not self._should_play_this_turn():
            return
        # print self.number, "plays turn", self.world.turn
        self._update_effect_users_and_workers()
        self._update_time_has_come()
        self._send_workers_to_forgotten_building_sites()
        maintain_terran_recombine(self)
        self._maintain_resource_buildings()
        self._idle_resource_buildings_produce()
        self._idle_workers_gather()
        self._idle_water_workers_gather()
        self._sanitize_water_unit_orders()
        self._idle_water_workers()
        self._try_maintain_naval()
        self._try_amphibious_landings()
        self._idle_naval_patrol()
        self._send_explorer()
        if self._attacked_places:
            self._eventually_attack(self._attacked_places)
            self._attacked_places = []
        elif self.constant_attacks:
            self._eventually_attack(self._enemy_presence)
        else:
            self._defensive_routine()
        if self.research:
            self.idle_buildings_research()
        self._raise_dead()
        self._build_a_warehouse_if_useful()
        self._maintain_expansions()
        self._ensure_housing(min_headroom=0)
        self.get(self.nb_workers_to_get, self.equivalent("peasant"))
        try:
            self._follow_plan()
        except RuntimeError:
            warning(
                "recursion error with %s; current ai.txt line is: %s",
                self.AI_type,
                self._plan[self._line_nb],
            )
            if IS_DEV_VERSION:
                exception("")
            self._line_nb += 1  # go to next step

    def _deposit_priority(self, deposit):
        if deposit is None:
            return -100, 0, 0
        try:
            workers = self._gathered_deposits[deposit]
        except:
            workers = 0
            
        # 将字符串资源类型转换为索引
        if hasattr(deposit, "resource_type"):
            if deposit.resource_type == "resource1":
                resource_index = 0  # 对应第一个资源类型
            elif deposit.resource_type == "resource2":
                resource_index = 1  # 对应第二个资源类型
            else:
                try:
                    # 从resource3开始解析数字
                    resource_index = int(deposit.resource_type[8:]) - 1
                except (ValueError, AttributeError):
                    resource_index = 0  # 默认使用第一个资源类型
        else:
            resource_index = 0
            
        # The resources difference is taken into account only if the difference is significant.
        return (
            -self.resources[resource_index] // 10,
            -workers,
            deposit.id,
        )  # deterministic (avoid sync errors)

    def _update_effect_users_and_workers(self):
        self._workers = []
        self._gathered_deposits = {}
        self._building_sites = []
        self._raise_dead_users = []
        self._teleportation_users = []
        self._cataclysm_users = []
        self._detector_users = []
        self._summon_users = []

        # 按ID排序单位，确保处理顺序一致
        sorted_units = sorted(self.units, key=lambda u: u.id)
        for u in sorted_units:
            if is_ground_worker(u):
                self._workers.append(u)
                if u.orders and u.orders[0].keyword == "gather":
                    try:
                        self._gathered_deposits[u.orders[0].target] += 1
                    except:
                        self._gathered_deposits[u.orders[0].target] = 1
            elif isinstance(u, BuildingSite):
                self._building_sites.append(u)
            
            # 检查 can_use - 按字母顺序排序确保顺序一致
            sorted_can_use = sorted(u.can_use)
            for a in sorted_can_use:
                if not UseOrder.is_allowed(u, a):
                    continue
                e = rules.get(a, "effect")
                if not e:
                    continue
                elif e[0] == "raise_dead":
                    self._raise_dead_users.append((u, a))
                elif e[0] == "teleportation":
                    self._teleportation_users.append((u, a))
                elif e[0] == "summon":
                    for item in e[1:]:
                        if rules.get(item, "harm_level"):
                            self._cataclysm_users.append((u, a))
                        if rules.get(item, "is_a_detector"):
                            self._detector_users.append((u, a))
                        if rules.get(item, "damage"):
                            self._summon_users.append((u, a))
            
            # 检查 can_use_tech - 按字母顺序排序确保顺序一致
            if hasattr(u, 'can_use_tech'):
                sorted_can_use_tech = sorted(u.can_use_tech)
                for a in sorted_can_use_tech:
                    if not UseOrder.is_allowed(u, a):
                        continue
                    e = rules.get(a, "effect")
                    if not e:
                        continue
                    elif e[0] == "raise_dead":
                        self._raise_dead_users.append((u, a))
                    elif e[0] == "teleportation":
                        self._teleportation_users.append((u, a))
                    elif e[0] == "summon":
                        for item in e[1:]:
                            if rules.get(item, "harm_level"):
                                self._cataclysm_users.append((u, a))
                            if rules.get(item, "is_a_detector"):
                                self._detector_users.append((u, a))
                            if rules.get(item, "damage"):
                                self._summon_users.append((u, a))
            
            # 检查 can_use_skill - 按字母顺序排序确保顺序一致
            if hasattr(u, 'can_use_skill'):
                sorted_can_use_skill = sorted(u.can_use_skill)
                for a in sorted_can_use_skill:
                    if not UseOrder.is_allowed(u, a):
                        continue
                    e = rules.get(a, "effect")
                    if not e:
                        continue
                    elif e[0] == "raise_dead":
                        self._raise_dead_users.append((u, a))
                    elif e[0] == "teleportation":
                        self._teleportation_users.append((u, a))
                    elif e[0] == "summon":
                        for item in e[1:]:
                            if rules.get(item, "harm_level"):
                                self._cataclysm_users.append((u, a))
                            if rules.get(item, "is_a_detector"):
                                self._detector_users.append((u, a))
                            if rules.get(item, "damage"):
                                self._summon_users.append((u, a))

    def _raise_dead(self):
        for u, a in self._raise_dead_users:
            if u.place in self._places_with_corpses:
                u.take_order(
                    ["use", a, u.place.id]
                )  # optional target will be eventually ignored

    def missing_resources(self, cost):
        result = []
        for i, c in enumerate(cost):
            if c > self.resources[i]:
                result.append(i)
        return result

    def unit_class(self, name):
        return rules.unit_class(name)

    def best_explorers(self):
        return sorted(
            [
                u
                for u in self.units
                if u.speed > 0
                and getattr(u, "airground_type", "ground") != "water"
                and not (u.orders and u.orders[0].keyword == "upgrade_to")
            ],
            key=value_as_an_explorer,
            reverse=True,
        )

    def _send_explorer(self):
        candidates = self.best_explorers()
        if candidates:
            best_explorer = candidates[0]
            if not (
                best_explorer.orders
                and best_explorer.orders[0].keyword == "auto_explore"
            ):
                explorer = None
                for u in self.units:
                    if u.orders and u.orders[0].keyword == "auto_explore":
                        explorer = u
                        break
                if explorer:
                    if (
                        value_as_an_explorer(explorer)[0]
                        == value_as_an_explorer(best_explorer)[0]
                    ):
                        return
                    explorer.take_order(["go", self.units[0].place.id])
                best_explorer.take_order(["auto_explore"])

    def _remove_far_candidates(self, candidates, start, limit):
        ids = {o.id: o for o in candidates}
        c = []
        queue = [start]
        done = []
        while queue and len(c) < limit:
            room = queue.pop(0)
            for o in room.objects:
                if o.id in ids:
                    c.append(ids[o.id])
                    if len(c) >= limit:
                        break
            if room in done:
                continue
            for e in room.exits:
                next_room = e.other_side.place
                if next_room not in done:
                    queue.append(next_room)
            done.append(room)
        return c

    def is_ok_for_warehouse(self, z, resource_type):
        # Eventually, to completely avoid cheating, is_ok() would
        # return True if "no owned warehouse and no remembered enemy".
        # a warehouse (allied or not) must not be already there
        for o2 in z.objects:
            if resource_type in getattr(o2, "storable_resource_types", ()):
                return False
        # a resource must be there
        for o in z.objects:
            if isinstance(o, Deposit) and o.resource_type == resource_type:
                return True

    def choose(self, c, resource_type=None, starting_place=None, random=False):
        if not self.units:
            return

        def is_ok(o):
            return (
                o.place is not None
                and (
                    resource_type is None
                    or self.is_ok_for_warehouse(o.place, resource_type)
                )
                and not self.square_is_dangerous(o.place)
                and (
                    not isinstance(o, Deposit)
                    or getattr(o, "qty", 0) > 0
                )
            )

        k = f"{c} {resource_type} {starting_place}"
        if k in self._previous_choose and not random:
            o = self._previous_choose[k]
            if (o in self.perception or o in self.memory) and is_ok(o):
                #                warning("useful cache %s %s", c, resource_type)
                return o
            else:
                del self._previous_choose[k]
        if starting_place is None:
            starting_place = self.units[0].place
        candidates = [
            o
            for o in self.perception.union(self.memory)
            if self.check_type(o, c) and is_ok(o)
        ]
        candidates = sorted(
            candidates, key=lambda x: x.id
        )  # avoid synchronization errors
        if len(candidates) > 10:
            candidates = self._remove_far_candidates(candidates, starting_place, 10)
        else:
            candidates.sort(
                key=lambda x: starting_place.shortest_path_distance_to(
                    x.place, self, avoid=True
                )
            )
            while candidates and starting_place.shortest_path_distance_to(
                candidates[-1].place, self, avoid=True
            ) is float("inf"):
                del candidates[-1]  # no path
        if random:
            if candidates:
                p = candidates[0].place
                candidates = sorted(
                    [o for o in candidates if o.place is p],
                    key=self._deposit_priority,
                    reverse=True,
                )
        for o in candidates:
            if not random:
                self._previous_choose[k] = o
            return o

    def nb(self, types):
        if (
            types
            and isinstance(types, list)
            and isinstance(types[0], str)
            and types[0] in self.upgrades
        ):
            return 1
        n = 0
        for u in self.units:
            if self.check_type(u, types):
                n += 1
        return n

    def _nb_in_production(self, types):
        n = 0
        for u in self.units:
            if isinstance(u, BuildingSite) and self.check_type(u.type, types):
                n += 1
                continue
            for o in u.orders:
                if getattr(o, "is_deferred", False):
                    continue
                if o.keyword in (
                    "build",
                    "train",
                    "upgrade_to",
                    "research",
                ) and self.check_type(o.type, types):
                    # the result might be temporarily too high because of build orders
                    # but that's not a big problem for order()
                    n += 1
        return n

    def future_nb(self, types):
        return self.nb(types) + self._nb_in_production(types)

    def _worker_orders_priority(self, u):
        if not u.orders:
            return (0,)
        if u.orders[0].keyword == "gather":
            return (1, self._deposit_priority(u.orders[0].target))
        return (2,)

    def order(self, nb, types, order, near=None, requisition=False):
        order_id = repr((types, order))
        if order_id in self._orders:
            for unit_order in list(self._orders[order_id]):
                if unit_order.is_complete:
                    self._orders[order_id].remove(unit_order)
                elif (
                    unit_order.unit.place is None
                    or unit_order not in unit_order.unit.orders
                ):
                    self._orders[order_id].remove(unit_order)
        else:
            self._orders[order_id] = []
        if len(self._orders[order_id]) >= nb:
            return
        units = [u for u in self.units if self.check_type(u, types)]
        while units:
            if requisition:
                units.sort(key=self._worker_orders_priority)
            u = units.pop(0)
            if (
                order[0] == "upgrade_to"
                and u.orders
                and u.orders[0].keyword == "auto_explore"
            ):
                u.take_order(["stop"])
            if requisition or not u.orders:
                if u.orders and u.orders[0].keyword in ("build", "repair"):
                    continue
                if order[0] == "build" and len(order) >= 2:
                    if not worker_can_build(u, order[1]):
                        continue
                if order[0] == "repair":
                    if not worker_can_repair(u):
                        continue
                    if len(order) >= 2:
                        target = self.get_object_by_id(order[1])
                        if isinstance(target, BuildingSite) and (
                            getattr(target, "_self_construct", False)
                            or getattr(getattr(target, "type", None), "self_constructs", 0)
                        ):
                            continue
                if requisition and u.orders and u.orders[0].keyword == "gather":
                    self._gathered_deposits[u.orders[0].target] -= 1
                order_cls = ORDERS_DICT.get(order[0])
                if order_cls is not None and not order_cls.is_allowed(u, *order[1:]):
                    continue
                u.take_order(order)
                if u.orders and u.orders[0].keyword == order[0]:
                    self._orders[order_id].append(u.orders[0])
                    if len(self._orders[order_id]) >= nb:
                        return

    def potential(self, cost):
        result = 9999
        for i, res in enumerate(self.resources):
            if cost[i]:
                result = min(result, res // cost[i])
        return result

    def _map_has_water(self):
        water_squares = getattr(self.world, "water_squares", None)
        if water_squares:
            return len(water_squares) > 0
        for sq in getattr(self.world, "squares", ()):
            if getattr(sq, "is_water", False):
                return True
        return False

    def _type_needs_water(self, type_name_or_class):
        if isinstance(type_name_or_class, str):
            cls = rules.unit_class(self.equivalent(type_name_or_class))
        else:
            cls = type_name_or_class
        if cls is None:
            return False
        if getattr(cls, "airground_type", None) == "water":
            return True
        if getattr(cls, "is_buildable_near_water_only", False):
            return True
        return False

    def get(self, nb, type):
        if not self._map_has_water() and self._type_needs_water(type):
            return True
        self._safe_cnt = 0
        return self._get(nb, [type])

    def _get(self, nb, types):
        if not hasattr(self, "_safe_cnt"):
            self._safe_cnt = 0
        if isinstance(types, str):
            types = [types]
        elif not isinstance(types, (list, tuple)):
            types = [types]
        if self.nb(types) >= nb:
            return True
        if self.future_nb(types) >= nb:
            return False
        self._safe_cnt += 1
        if self._safe_cnt > 10:
            info("AI has trouble getting: %s %s", nb, types)
            return False
        for type in types:
            if isinstance(type, str):
                unit_class = rules.unit_class(type)
                if unit_class is None:
                    warning("无效的单位类型: %s", type)
                    continue
                type = unit_class
            elif type is None:
                continue
            elif not hasattr(type, "__name__"):
                warning("无效的单位类型: %s", type)
                continue

            # 获取制造者类型列表
            makers = rules.get_makers(type)
            if not makers:
                continue
                
            # 检查是否已有该类型的制造者
            if self.nb(makers) > 0:
                try:
                    # 尝试建造或培训单位
                    future_count = self.future_nb(types)
                    target_count = nb - future_count
                    if target_count > 0:
                        self.build_or_train_or_upgradeto_or_summon(
                            type, target_count
                        )
                    break
                except Exception as e:
                    warning(
                        "创建单位时出错: %s - %s: %s",
                        type.__name__ if hasattr(type, "__name__") else type,
                        type(e).__name__,
                        e,
                    )
            elif makers:
                # 递归获取制造者
                if not self._get(1, makers[0]):
                    # 如果无法获取制造者，尝试其他可能的制造者
                    for maker in makers[1:]:
                        if self._get(1, maker):
                            return True
                    return False
                return False
        return False

    def _population_headroom(self):
        return self.available_population - self.used_population

    def _is_house_type(self, building_type):
        house = self.equivalent("house")
        if isinstance(building_type, str):
            return building_type == house
        return getattr(building_type, "type_name", None) == house

    def _ensure_housing(self, min_headroom=2):
        """Build faction supply (pylon / depot equivalent) when population is tight."""
        if self._population_headroom() > min_headroom:
            return False
        if self.available_population >= self.world.population_limit:
            return False
        house = self.equivalent("house")
        house_cls = rules.unit_class(house)
        if house_cls is None:
            return False
        peasant_cls = rules.unit_class(self.equivalent("peasant"))
        if peasant_cls is None or house not in getattr(peasant_cls, "can_build", ()):
            return False
        if self.future_nb(house) > self.nb(house):
            return False
        if self.missing_resources(house_cls.cost):
            return False
        self.build_or_train_or_upgradeto_or_summon(house)
        return True

    def gather(self, cost, population):
        missing = self.missing_resources(cost)
        if missing:
            self._ensure_resource_buildings(missing)
            self._idle_resource_buildings_produce()
            return
        if population != 0 and population > self._population_headroom():
            if self._ensure_housing(min_headroom=population - 1):
                return
            if self.available_population >= self.world.population_limit:
                return
            return
        return True

    def _get_requirements(self, t):
        for r in t.requirements:
            if not self.has(r):  # requirement (eventually is_a)
                if rules.get(r, "class") == ["deposit"]:
                    return False
                if not rules.get_makers(r):
                    return False
                return self._get(1, r)  # exact type
        return True

    def _builders_place(self):
        starts = {}
        for u in self._workers:
            place = u.place
            if place is None:
                continue
            if getattr(place, "is_inside_place", False):
                place = place.outside
            if place is None or place.id is None:
                continue
            starts[place] = starts.get(place, 0) + 1
        if starts:
            return sorted(starts.items(), key=lambda x: (x[1], x[0].id))[-1][0]

    def _try_morph_from_larva(self, type_name):
        from .worldorders.production import ChangeToOrder, UpgradeToOrder

        unit_type = rules.unit_class(type_name)
        if unit_type is None:
            return False
        if not self.gather(unit_type.cost, unit_type.population_cost):
            return False
        for u in self.units:
            if not getattr(u, "morph_as_train", 0):
                continue
            if type_name in u.can_upgrade_to and UpgradeToOrder.is_allowed(u, type_name):
                u.take_order(["upgrade_to", type_name])
                return True
            if type_name in u.can_change_to and ChangeToOrder.is_allowed(u, type_name):
                u.take_order(["change_to", type_name])
                return True
        return False

    def build_or_train_or_upgradeto_or_summon(self, t, nb=1):
        if t.__class__ == str:
            t = rules.unit_class(t)
        type = t.__name__
        makers = rules.get_makers(type)
        if self._get(1, makers) and self._get_requirements(t):
            for maker in makers:
                # TODO: choose one without orders if possible
                if self.nb(maker):
                    break
            maker_cls = rules.unit_class(maker)
            if type in rules.class_rules_attr(maker_cls, "can_upgrade_to"):
                if self.nb(maker) >= nb:
                    m = rules.unit_class(maker)
                    if self.gather(
                        [t.cost[i] - m.cost[i] for i in range(len(t.cost))],
                        t.population_cost - m.population_cost,
                    ):
                        self.order(nb, maker, ["upgrade_to", type])
                else:
                    self._get(nb, maker)
            elif type in rules.class_rules_attr(maker_cls, "can_build"):
                if not self.gather(t.cost, t.population_cost):
                    return
                if ensure_field_provider_before_build(self, t):
                    return
                resource_type = (
                    t.storable_resource_types[0] if t.storable_resource_types else None
                )
                starting = self._builders_place()
                if getattr(t, "is_buildable_near_water_only", False):
                    target = choose_near_water_build_target(
                        self, t, starting_place=starting
                    )
                elif self._is_house_type(t):
                    target = choose_house_build_target(
                        self, t, starting_place=starting
                    )
                else:
                    target = choose_build_target(
                        self, t, starting_place=starting, resource_type=resource_type
                    )
                if (
                    target is None
                    and resource_type is not None
                    and self.nb(t)
                ):
                    return
                if target is None and resource_type is None:
                    if getattr(t, "is_buildable_near_water_only", False):
                        target = choose_near_water_build_target(
                            self, t, starting_place=starting
                        )
                    else:
                        target = choose_build_target(self, t, starting_place=starting)
                if (
                    target is None
                    and not is_addon_type(t)
                    and not requires_build_field_type(t)
                    and not getattr(t, "is_buildable_anywhere", 0)
                ):
                    target = self.choose(
                        Meadow,
                        resource_type=resource_type,
                        starting_place=starting,
                    )
                target = resolve_build_target(self, t, target)
                if target:
                    self.order(
                        build_worker_count(maker_cls, t),
                        maker,
                        ["build", type, target.id],
                        requisition=True,
                        near=target,
                    )
            elif type in rules.class_can_train(maker_cls):
                if (
                    self.nb(Worker)
                    and nb > self.nb(maker) * 3
                    and self.potential(t.cost) > self.nb(maker) * 100
                ):
                    # additional production sites
                    self.build_or_train_or_upgradeto_or_summon(maker)
                if not self.gather(t.cost, t.population_cost):
                    return
                trained = False
                host = find_train_host(self, maker, type)
                if host is not None:
                    host.take_order(["train", type])
                    trained = True
                elif self.nb(maker):
                    for u in self.units:
                        if (
                            self.check_type(u, maker)
                            and not u.orders
                            and building_can_operate(u)
                            and type in effective_can_train(u)
                        ):
                            u.take_order(["train", type])
                            trained = True
                            break
                if not trained:
                    self._try_morph_from_larva(type)
            elif type in rules.class_rules_attr(maker_cls, "can_research"):
                if self.gather(t.cost, t.population_cost):
                    self.order(1, maker, ["research", type])
            elif type in rules.class_rules_attr(maker_cls, "can_advance"):
                if self.gather(t.cost, t.population_cost):
                    self.order(1, maker, ["advance", type])
            elif self._try_morph_from_larva(type):
                pass
            else:
                for skill in rules.unit_class(maker).can_use:
                    effect = rules.get(skill, "effect")
                    if effect and "summon" in effect[:1] and type in effect:
                        if rules.get(skill, "effect_target") == ["ask"]:
                            self.order(1, maker, ["use", skill, self.units[0].id])
                            # TODO select best place
                        else:
                            self.order(1, maker, ["use", skill])
                        break

                # 检查 can_use_tech
                if hasattr(rules.unit_class(maker), 'can_use_tech'):
                    for skill in rules.unit_class(maker).can_use_tech:
                        effect = rules.get(skill, "effect")
                        if effect and "summon" in effect[:1] and type in effect:
                            if rules.get(skill, "effect_target") == ["ask"]:
                                self.order(1, maker, ["use", skill, self.units[0].id])
                                # TODO select best place
                            else:
                                self.order(1, maker, ["use", skill])
                            break

                # 检查 can_use_skill
                if hasattr(rules.unit_class(maker), 'can_use_skill'):
                    for skill in rules.unit_class(maker).can_use_skill:
                        effect = rules.get(skill, "effect")
                        if effect and "summon" in effect[:1] and type in effect:
                            if rules.get(skill, "effect_target") == ["ask"]:
                                self.order(1, maker, ["use", skill, self.units[0].id])
                                # TODO select best place
                            else:
                                self.order(1, maker, ["use", skill])
                            break

    def _cataclysm_is_efficient(self, a, units):
        type_names = {u.type_name for u in units}
        e = rules.get(a, "effect")
        if e[0] == "summon":
            for item in e[1:]:
                if rules.get(item, "harm_level"):
                    for t in type_names:
                        if self.world.can_harm(item, t):
                            return True

    def _enemies_at(self, place):
        return [
            u
            for l in (self.perception, self.memory)
            for u in l
            if u.place is place and self.is_an_enemy(u)
        ]

    def _counter_skill_level(self):
        if not self.smart_units:
            return 0
        return max(0, min(100, getattr(self, "counter_skill", 100)))

    def _place_counter_score(self, place, units):
        """Sum of best vs bonuses each unit has against enemies at place."""
        skill = self._counter_skill_level()
        if skill <= 0:
            return 0
        enemies = self._enemies_at(place)
        if not enemies:
            return 0
        score = 0
        for u in units:
            score += max(u._get_vs_damage_bonus(e) for e in enemies)
        return score * skill

    def _attack_place_sort_key(self, place, units):
        menace = self.enemy_menace(place)
        counter = self._place_counter_score(place, units)
        if counter:
            return (menace, -counter)
        return (menace,)

    def _counter_priority_units(self, units, place):
        """Prefer units with mdg_vs/rdg_vs bonus vs enemies at place; keep enough menace."""
        enemies = self._enemies_at(place)
        skill = self._counter_skill_level()
        if not enemies or skill <= 0:
            return units
        ratio = self._attack_ratio
        if self.used_population >= self.world.population_limit - 5:
            ratio = min(100, ratio)
        min_menace = self.enemy_menace(place) * ratio // 100 + 1
        scored = sorted(
            units,
            key=lambda u: -(
                max(u._get_vs_damage_bonus(e) for e in enemies) * skill
                + u.menace * (100 - skill)
            ),
        )
        chosen = []
        menace = 0
        for u in scored:
            chosen.append(u)
            if u.speed > 0 and isinstance(u, Soldier):
                menace += u.menace
            if menace >= min_menace:
                break
        chosen_set = set(chosen)
        for u in units:
            if u in chosen_set:
                continue
            if not isinstance(u, Soldier):
                continue
            if getattr(u, "airground_type", None) != "ground" or u.speed <= 0:
                continue
            start = self._world_place_for_unit(u)
            if start is None:
                continue
            if self._unit_can_reach(u, place):
                chosen.append(u)
                continue
            if self._choose_transport_mode([u], place):
                chosen.append(u)
        return chosen

    def _eventually_attack(self, places):
        units = self._idle_fighters
        if not units:
            return
        places = sorted(
            places, key=lambda p: self._attack_place_sort_key(p, units)
        )
        for place in places:
            to_send = self._counter_priority_units(units, place)
            if self._units_should_attack(to_send, place):
                self._send_units(to_send, place)
                return
        if places:
            place = places[0]
            temp_units = [u for u in units if u.time_limit and u.speed]
            if temp_units:
                self._send_units(temp_units, place)
            place = places[-1]
            if not self._friendly_presence(place):
                enemies = (
                    u
                    for l in (self.perception, self.memory)
                    for u in l
                    if u.place is place and self.is_an_enemy(u)
                )
                for u, a in self._cataclysm_users:
                    if u.orders or not self._cataclysm_is_efficient(a, enemies):
                        continue
                    move_target = movement_target_for_unit(u, place, self)
                    path = self._unit_path(u, move_target, places=True)
                    if path and len(path) > 2:
                        u.take_order(["go", path[-2].id], forget_previous=False)
                    u.take_order(["use", a, place.id], forget_previous=False)
                    if u.orders and not u.orders[0].is_impossible:
                        u.take_order(["go", u.place.id], forget_previous=False)

    @property
    def _idle_fighters(self):
        return [
            u
            for u in self.units
            if isinstance(u, Soldier)
            and not getattr(u, "is_inside", False)
            and (
                not u.orders
                or len(u.orders) == 1
                and u.orders[0].keyword == "go"
                and u.orders[0].target not in self._enemy_presence
            )
        ]

    def _update_time_has_come(self):
        self._waiting_menace = {}
        self._waiting_units = {}
        for u in self.units:
            for o in u.orders[:1]:
                if o.keyword == "wait":
                    try:
                        self._waiting_menace[o.target] += u.menace
                        self._waiting_units[o.target].append(u)
                    except:
                        self._waiting_menace[o.target] = u.menace
                        self._waiting_units[o.target] = [u]
        self._time_has_come = {}
        for place in self._waiting_units:
            self._time_has_come[place] = self._is_powerful_enough(
                self._waiting_units.get(place, ()), place
            )
        cancel = set()
        for place in self._waiting_menace:
            if not self._is_powerful_enough(self.units, place):
                for u in self.units:
                    for o in u.orders:
                        if o.keyword == "wait" and o.target is place:
                            cancel.add(u)
        for u in cancel:
            u.cancel_all_orders()

    def time_has_come(self, place):
        if place in self._cataclysmic_places:
            return False
        try:
            return self._time_has_come[place]
        except:
            return False

    def _friendly_presence(self, place):
        return place in self._places_with_friends

    def _unit_path(self, unit, dest, places=False, avoid=False):
        origin = self._world_place_for_unit(unit)
        dest = self._world_place_for_pathfinding(dest)
        if origin is None or dest is None:
            return [] if places else None
        return origin.shortest_path_to(
            dest, self, plane=path_plane(unit), places=places, avoid=avoid
        )

    def _unit_can_reach(self, unit, dest, avoid=False):
        dest = self._world_place_for_pathfinding(dest)
        if dest is None:
            return False
        move_target = movement_target_for_unit(unit, dest, self)
        path = self._unit_path(unit, move_target, places=True, avoid=avoid)
        return bool(path)

    def _amphibious_transport_cost(self, unit, dest_place):
        start = self._world_place_for_unit(unit)
        dest_place = self._world_place_for_pathfinding(dest_place)
        if start is None or dest_place is None:
            return float("inf")
        route = find_amphibious_crossing(start, dest_place, self)
        if route is None or not self._available_water_transports():
            return float("inf")
        load_land, load_water, unload_water, unload_land = route
        leg1 = start.shortest_path_distance_to(load_land, self, "ground")
        if leg1 is None or leg1 == float("inf"):
            return float("inf")
        leg2 = load_water.shortest_path_distance_to(unload_water, self, "water")
        if leg2 is None or leg2 == float("inf"):
            return float("inf")
        leg3 = unload_land.shortest_path_distance_to(dest_place, self, "ground")
        if leg3 is None or leg3 == float("inf"):
            leg3 = 0
        return leg1 + leg2 + leg3

    def _airborne_transport_cost(self, unit, dest_place):
        start = self._world_place_for_unit(unit)
        dest_place = self._world_place_for_pathfinding(dest_place)
        if start is None or dest_place is None or getattr(dest_place, "is_water", False):
            return float("inf")
        if not self._available_air_transports():
            return float("inf")
        unload_land = movement_target_for_unit(unit, dest_place, self)
        if getattr(unload_land, "is_water", False):
            return float("inf")
        leg = start.shortest_path_distance_to(unload_land, self, "air")
        if leg is None or leg == float("inf"):
            return float("inf")
        return leg

    def _choose_transport_mode(self, units, dest_place):
        """Pick boat landing or airlift when ground troops cannot walk to dest."""
        if not units:
            return None
        unit = units[0]
        if self._unit_can_reach(unit, dest_place):
            return None
        amp = self._amphibious_transport_cost(unit, dest_place)
        air = self._airborne_transport_cost(unit, dest_place)
        amp_ok = amp < float("inf")
        air_ok = air < float("inf")
        if not amp_ok and not air_ok:
            return None
        if amp_ok and not air_ok:
            return "amphibious"
        if air_ok and not amp_ok:
            return "airborne"
        return "airborne" if air <= amp else "amphibious"

    def _ground_units_needing_transport(self, units, dest_place):
        blocked = []
        for u in units:
            if getattr(u, "airground_type", None) != "ground" or u.speed <= 0:
                continue
            if self._unit_can_reach(u, dest_place):
                continue
            if self._choose_transport_mode([u], dest_place):
                blocked.append(u)
        return blocked

    def _available_water_transports(self):
        result = []
        for u in self.units:
            if getattr(u, "transport_capacity", 0) <= 0:
                continue
            if getattr(u, "airground_type", None) != "water":
                continue
            if u.speed <= 0 or getattr(u, "is_inside", False):
                continue
            if u.orders:
                keywords = {o.keyword for o in u.orders}
                if keywords & {"load", "load_all", "unload", "unload_all"}:
                    continue
                if u.orders[0].keyword not in ("go",):
                    continue
            result.append(u)
        return result

    def _water_path_distance(self, start_place, dest_place):
        if start_place is None or dest_place is None:
            return float("inf")
        dist = start_place.shortest_path_distance_to(dest_place, self, "water")
        if dist is None or dist == float("inf"):
            return float("inf")
        return dist

    def _available_air_transports(self):
        result = []
        for u in self.units:
            if getattr(u, "transport_capacity", 0) <= 0:
                continue
            if getattr(u, "airground_type", None) != "air":
                continue
            if u.speed <= 0 or getattr(u, "is_inside", False):
                continue
            if u.orders:
                keywords = {o.keyword for o in u.orders}
                if keywords & {"load", "load_all", "unload", "unload_all"}:
                    continue
                if u.orders[0].keyword not in ("go",):
                    continue
            result.append(u)
        return result

    def _air_path_distance(self, start_place, dest_place):
        if start_place is None or dest_place is None:
            return float("inf")
        dist = start_place.shortest_path_distance_to(dest_place, self, "air")
        if dist is None or dist == float("inf"):
            return float("inf")
        return dist

    def _order_amphibious_transport(
        self, transport, ground_units, load_land, load_water, unload_water, unload_land, final_dest
    ):
        for u in ground_units:
            u.cancel_all_orders()
            u.take_order(["go", load_land.id], forget_previous=False)
        transport.cancel_all_orders()
        transport.take_order(["go", load_water.id], forget_previous=False)
        transport.take_order(["load_all", load_land.id], forget_previous=False)
        transport.take_order(["go", unload_water.id], forget_previous=False)
        transport.take_order(["unload_all", unload_land.id], forget_previous=False)
        for u in ground_units:
            u.take_order(["go", final_dest.id], forget_previous=False)

    def _send_ground_units_amphibious(self, units, dest_place):
        if not units:
            return []
        origin = self._world_place_for_unit(units[0])
        dest_place = self._world_place_for_pathfinding(dest_place)
        if origin is None or dest_place is None:
            return []
        amphib = find_amphibious_crossing(origin, dest_place, self)
        if amphib is None:
            return []
        load_land, load_water, unload_water, unload_land = amphib
        transports = sorted(
            self._available_water_transports(),
            key=lambda t: self._water_path_distance(t.place, load_water),
        )
        if not transports:
            return []
        remaining = list(units)
        sent = []
        for transport in transports:
            if not remaining:
                break
            capacity_left = transport.transport_capacity
            inside = getattr(transport, "inside", None)
            if inside is not None:
                for o in inside.objects:
                    capacity_left -= getattr(o, "transport_volume", 1)
            batch = []
            for u in remaining:
                vol = getattr(u, "transport_volume", 1)
                if capacity_left >= vol:
                    batch.append(u)
                    capacity_left -= vol
            if not batch:
                continue
            for u in batch:
                remaining.remove(u)
            self._order_amphibious_transport(
                transport, batch, load_land, load_water, unload_water, unload_land, dest_place
            )
            sent.extend(batch)
        return sent

    def _order_airborne_transport(
        self, transport, ground_units, load_land, unload_land, final_dest
    ):
        for u in ground_units:
            u.cancel_all_orders()
            if u.place is not load_land:
                u.take_order(["go", load_land.id], forget_previous=False)
        transport.cancel_all_orders()
        transport.take_order(["go", load_land.id], forget_previous=False)
        transport.take_order(["load_all", load_land.id], forget_previous=False)
        transport.take_order(["go", unload_land.id], forget_previous=False)
        transport.take_order(["unload_all", unload_land.id], forget_previous=False)
        for u in ground_units:
            u.take_order(["go", final_dest.id], forget_previous=False)

    def _send_ground_units_airborne(self, units, dest_place):
        if not units:
            return []
        origin = self._world_place_for_unit(units[0])
        dest_place = self._world_place_for_pathfinding(dest_place)
        if origin is None or dest_place is None:
            return []
        unload_land = movement_target_for_unit(units[0], dest_place, self)
        if getattr(unload_land, "is_water", False):
            return []
        load_land = origin
        transports = sorted(
            self._available_air_transports(),
            key=lambda t: self._air_path_distance(getattr(t, "place", None), load_land),
        )
        if not transports:
            return []
        remaining = list(units)
        sent = []
        for transport in transports:
            if not remaining:
                break
            capacity_left = transport.transport_capacity
            inside = getattr(transport, "inside", None)
            if inside is not None:
                for o in inside.objects:
                    capacity_left -= getattr(o, "transport_volume", 1)
            batch = []
            for u in remaining:
                vol = getattr(u, "transport_volume", 1)
                if capacity_left >= vol:
                    batch.append(u)
                    capacity_left -= vol
            if not batch:
                continue
            for u in batch:
                remaining.remove(u)
            self._order_airborne_transport(
                transport, batch, load_land, unload_land, dest_place
            )
            sent.extend(batch)
        return sent

    def _send_ground_units_by_transport(self, units, dest_place):
        dest_place = self._world_place_for_pathfinding(dest_place)
        if dest_place is None:
            return []
        mode = self._choose_transport_mode(units, dest_place)
        if mode == "amphibious":
            return self._send_ground_units_amphibious(units, dest_place)
        if mode == "airborne":
            return self._send_ground_units_airborne(units, dest_place)
        return []

    def _send_unit_to_place(self, unit, place, used_teleportation, enemies):
        place = self._world_place_for_pathfinding(place)
        if self._world_place_for_unit(unit) is None or place is None:
            return
        move_target = movement_target_for_unit(unit, place, self)
        path = self._unit_path(unit, move_target, places=True)
        plane = path_plane(unit)
        if (
            not path
            and plane == "ground"
            and unit.speed > 0
            and getattr(unit, "airground_type", None) == "ground"
        ):
            mode = self._choose_transport_mode([unit], place)
            if mode == "amphibious" and self._send_ground_units_amphibious([unit], place):
                return
            if mode == "airborne" and self._send_ground_units_airborne([unit], place):
                return
        if not used_teleportation and len(path) > 2:
            unit.take_order(["go", path[-2].id], forget_previous=False)
            if not self._friendly_presence(place):
                for u_, a in self._cataclysm_users:
                    if u_ is unit and self._cataclysm_is_efficient(a, enemies):
                        unit.take_order(["use", a, place.id], forget_previous=False)
        for u_, a in self._summon_users:
            if u_ is unit:
                unit.take_order(["use", a, place.id], forget_previous=False)
        for u_, a in self._detector_users:
            if u_ is unit:
                unit.take_order(["use", a, place.id], forget_previous=False)
        unit.take_order(["go", move_target.id], forget_previous=False)

    def _send_units(self, units, place):
        place = self._world_place_for_pathfinding(place)
        if place is None:
            return
        units = [u for u in units if u.place != place]
        to_move = []
        for u in units:
            if (
                u.orders
                and u.orders[-1].keyword == "go"
                and getattr(u.orders[-1].target, "id", None) == place.id
            ):
                continue
            u.cancel_all_orders()
            to_move.append(u)
        if not to_move:
            return
        used_teleportation = False
        for u, a in self._teleportation_users:
            u.take_order(["use", a, place.id])
            if u.orders and not u.orders[0].is_impossible:
                used_teleportation = True
        enemies = (
            u
            for l in (self.perception, self.memory)
            for u in l
            if u.place is place and self.is_an_enemy(u)
        )
        ground_blocked = []
        for u in to_move:
            if (
                getattr(u, "airground_type", None) == "ground"
                and u.speed > 0
                and not self._unit_can_reach(u, place)
            ):
                ground_blocked.append(u)
                continue
            self._send_unit_to_place(u, place, used_teleportation, enemies)
        if ground_blocked:
            if not self._send_ground_units_by_transport(ground_blocked, place):
                for u in ground_blocked:
                    self._send_unit_to_place(u, place, used_teleportation, enemies)

    def _units_should_attack(self, units, place):
        # assert units is not None
        place = self._world_place_for_pathfinding(place)
        if place is None:
            return False
        if not self._is_powerful_enough(units, place):
            return False
        for u in units:
            if u.speed <= 0:
                continue
            if self._unit_can_reach(u, place):
                return True
            if self._unit_can_reach(u, place, avoid=True):
                return True
        ground_units = [
            u
            for u in units
            if getattr(u, "airground_type", None) == "ground" and u.speed > 0
        ]
        if ground_units and self._choose_transport_mode(ground_units, place):
            return True
        return False

    def on_unit_attacked(self, unit, attacker):
        if attacker.player in self.allied or not attacker.is_vulnerable:
            return
        if unit.orders and unit.orders[0].keyword == "auto_explore":
            # Don't react now. Constant attacks will do the job if active.
            # And the easy computer AI shouldn't be aggressive.
            return
        if unit.is_a_building:
            self._sensible_building = unit
        if attacker in self.perception:
            place = attacker.place
        else:
            # undetected attacker
            place = unit.place  # neighbors?
        if place not in self._attacked_places:
            self._attacked_places.append(place)
