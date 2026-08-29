import re

from soundrts.lib.nofloat import square_of_distance, to_int
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
    is_land_shore,
    is_passable_land,
    movement_target_for_unit,
    path_plane,
    water_neighbors_of_land,
)
from .version import IS_DEV_VERSION
from .worldupgrade.base import is_an_upgrade
from .worldplayerbase import Player
from .worldresource import Deposit
from .worldunit import BuildingSite
from .worldunit import Soldier
from .worldunit import Worker

_PROD_ORDER_KEYWORDS = frozenset(
    ("build", "train", "upgrade_to", "research", "advance")
)
_PLAY_PROD_MEMO_PREFIXES = frozenset(
    (
        "nbprod",
        "futurenb",
        "pending_makers",
        "plan_wood",
        "plan_expensive_wood",
        "plan_next",
        "first_startable",
        "has_startable",
        "wood_below",
        "defer_token",
        "unmet_phases_type",
        "trainer_food",
        "low_thr",
        "age_missing",
        "keep_farms",
        "saving_food",
        "plan_prod_types",
        "upgrade_set",
    )
)


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
    # One-shot ai.txt multipliers (100 = normal). See parse_ai_start_settings.
    ai_train_time_percent = 100
    ai_research_time_percent = 100
    ai_build_time_percent = 100
    ai_gather_time_percent = 100
    ai_unit_hp_percent = 100
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
        # Apply ai.txt multipliers before map starting units spawn (unit_hp).
        self._apply_ai_multipliers()
        super().init_position(parsed_start)
        self._apply_ai_start_settings()

    def _apply_ai_multipliers(self):
        """Load train/research/build/gather_time / unit_hp from ai.txt onto this player."""
        if self.AI_type == "timers" or self.neutral:
            return
        script_name = self.faction_ai_type(self.AI_type)
        *_, train_time, research_time, build_time, gather_time, unit_hp = (
            parse_ai_start_settings(script_name)
        )
        self.ai_train_time_percent = train_time
        self.ai_research_time_percent = research_time
        self.ai_build_time_percent = build_time
        self.ai_gather_time_percent = gather_time
        self.ai_unit_hp_percent = unit_hp

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
        (
            resource_bonus,
            unit_tokens,
            population_bonus,
            train_time,
            research_time,
            build_time,
            gather_time,
            unit_hp,
        ) = parse_ai_start_settings(script_name)
        self.ai_train_time_percent = train_time
        self.ai_research_time_percent = research_time
        self.ai_build_time_percent = build_time
        self.ai_gather_time_percent = gather_time
        self.ai_unit_hp_percent = unit_hp
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
                        self.add_unit(unit_cls, place)
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
            self.ai_train_time_percent = type(self).ai_train_time_percent
            self.ai_research_time_percent = type(self).ai_research_time_percent
            self.ai_build_time_percent = type(self).ai_build_time_percent
            self.ai_gather_time_percent = type(self).ai_gather_time_percent
            self.ai_unit_hp_percent = type(self).ai_unit_hp_percent
            self._wait_deadline = None
            self._update_effect_users_and_workers()  # required by some tests

    _previous_linechange = 0
    __line_nb = 0
    ##    _prev_line_nb = None

    def get_line_nb(self):
        return self.__line_nb

    def set_line_nb(self, value):
        if value != self.__line_nb:
            self._previous_linechange = self.world.time
        self.__line_nb = value

    _line_nb = property(get_line_nb, set_line_nb)

    def _follow_plan(self):
        if not self._plan:
            return
        if self._watchdog_should_wait():
            # Pause the stuck-line timer while the current get is still
            # completable (dark-age eco, age click, unpaid workshop, ram wood).
            self._previous_linechange = self.world.time
        elif (
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
                saving_for_feudal = self._saving_food_for_age()
                for w in cmd[1:]:
                    if re.match("^[0-9]+$", w):
                        n = int(w)
                    else:
                        # After mod ``clear``, ai.txt must name types that exist
                        # in the mod (militia / aoe_archer / …). Unknown names
                        # warn — do not silently map base aliases via race table.
                        if rules.unit_class(w) is not None:
                            name = self.equivalent(w)
                            if self._defer_plan_get_token(
                                name, saving_for_feudal=saving_for_feudal
                            ):
                                if not saving_for_feudal:
                                    self._ensure_plan_production_building(name)
                                done = False
                                n = 1
                                continue
                            if not self.get(n, w):
                                done = False
                            n = 1
                        else:
                            warning("get: unknown unit: '%s' (in ai.txt)", w)
                            n = 1
                if done:
                    self._line_nb += 1
            else:
                warning("unknown command: '%s' (in ai.txt)", cmd[0])
                self._line_nb += 1

    # ------------------------------------------------------------------
    # Attribute-driven type discovery (no faction type-name literals).
    # ai.txt still uses semantic names via equivalent(); economy/naval/
    # housing code must work for arbitrary mods from rules attributes.
    # ------------------------------------------------------------------

    def _discovery_cache_get(self, key, factory):
        turn = getattr(getattr(self, "world", None), "turn", -1)
        cache = getattr(self, "_type_discovery_cache", None)
        if cache is None or cache.get("_turn") != turn:
            cache = {"_turn": turn}
            self._type_discovery_cache = cache
        if key not in cache:
            cache[key] = factory()
        return cache[key]

    def _play_memo_get(self, key, factory):
        """Cache a value for the rest of this Computer.play() turn only."""
        memo = getattr(self, "_play_memo", None)
        if memo is None:
            return factory()
        if key not in memo:
            memo[key] = factory()
        return memo[key]

    def _iter_ground_worker_classes(self):
        for name in rules.classnames():
            uc = rules.unit_class(name)
            if uc is None:
                continue
            try:
                if not issubclass(uc, Worker):
                    continue
            except TypeError:
                continue
            if getattr(uc, "airground_type", "ground") != "ground":
                continue
            yield name, uc

    def _worker_buildable_type_names(self):
        def _compute():
            names = set()
            seen_types = set()
            for w in getattr(self, "_workers", ()) or ():
                tn = getattr(w, "type_name", None)
                if tn in seen_types:
                    continue
                if tn is not None:
                    seen_types.add(tn)
                built = getattr(w, "can_build", ()) or ()
                if built:
                    names.update(built)
            if names:
                return frozenset(names)
            for _name, uc in self._iter_ground_worker_classes():
                built = rules.class_rules_attr(uc, "can_build", ()) or ()
                if built:
                    names.update(built)
            return frozenset(names)

        return self._play_memo_get(
            "worker_buildables_play",
            lambda: self._discovery_cache_get("worker_buildables", _compute),
        )

    def _primary_worker_type_name(self):
        def _compute():
            counts = {}
            for u in getattr(self, "_workers", ()) or ():
                tn = getattr(u, "type_name", None)
                if tn:
                    counts[tn] = counts.get(tn, 0) + 1
            if counts:
                return max(counts, key=counts.get)
            best = None
            best_score = -1
            for name, uc in self._iter_ground_worker_classes():
                score = 0
                if rules.class_rules_attr(uc, "can_build", ()):
                    score += 2
                if rules.class_rules_attr(uc, "can_gather_deposit", ()) or rules.class_rules_attr(
                    uc, "can_gather_building", ()
                ):
                    score += 1
                if score > best_score:
                    best_score = score
                    best = name
            return best

        return self._discovery_cache_get("primary_worker", _compute)

    def _main_base_type_names(self):
        """Buildings that train the primary worker (townhall / nexus / cc…)."""

        def _compute():
            worker = self._primary_worker_type_name()
            if not worker:
                return ()
            makers = rules.get_makers(worker) or ()
            return tuple(m for m in makers if rules.unit_class(m) is not None)

        return self._discovery_cache_get("main_base_types", _compute)

    def _housing_type_names(self):
        """Supply buildings: provide population and are not the main base.

        Prefer real houses (high population_provided, meadow build) over castles
        or exit-only walls/gates that also happen to grant a little pop.
        """

        def _compute():
            main = set(self._main_base_type_names())
            ranked = []
            for name in self._worker_buildable_type_names():
                if name in main:
                    continue
                uc = rules.unit_class(name)
                if uc is None:
                    continue
                pop = int(getattr(uc, "population_provided", 0) or 0)
                if pop <= 0:
                    continue
                # Walls/gates are not housing — building them for supply spams
                # cannot_build_here on exits.
                if getattr(uc, "is_buildable_on_exits_only", 0):
                    continue
                if getattr(uc, "is_a_gate", 0):
                    continue
                cost = sum(getattr(uc, "cost", ()) or ())
                ranked.append((name, pop, cost))
            # More pop first, then cheaper, then stable name order.
            ranked.sort(key=lambda item: (-item[1], item[2], item[0]))
            return tuple(item[0] for item in ranked)

        return self._discovery_cache_get("housing_types", _compute)

    def _storage_building_type_names(self, resource_index):
        resource_type = f"resource{resource_index + 1}"

        def _compute():
            result = []
            for name in self._worker_buildable_type_names():
                uc = rules.unit_class(name)
                if uc is None:
                    continue
                stores = getattr(uc, "storable_resource_types", ()) or ()
                if resource_type in stores:
                    result.append(name)
            return tuple(result)

        return self._discovery_cache_get(
            f"storage_{resource_index}", _compute
        )

    def _gate_type_names(self):
        def _compute():
            result = []
            for name in self._worker_buildable_type_names():
                uc = rules.unit_class(name)
                if uc is not None and getattr(uc, "is_a_gate", 0):
                    result.append(name)
            return tuple(result)

        return self._discovery_cache_get("gate_types", _compute)

    def _naval_yard_type_names(self):
        def _compute():
            result = []
            for name in self._worker_buildable_type_names():
                uc = rules.unit_class(name)
                if uc is None:
                    continue
                if getattr(uc, "is_buildable_near_water_only", False):
                    result.append(name)
                    continue
                for t in rules.class_can_train(uc) or ():
                    tc = rules.unit_class(t)
                    if tc is not None and getattr(tc, "airground_type", None) == "water":
                        result.append(name)
                        break
            return tuple(result)

        return self._discovery_cache_get("naval_yards", _compute)

    def _trainable_from_types(self, maker_names):
        result = []
        seen = set()
        for maker in maker_names or ():
            uc = rules.unit_class(maker)
            if uc is None:
                continue
            for t in rules.class_can_train(uc) or ():
                if t not in seen:
                    seen.add(t)
                    result.append(t)
        return result

    def _water_transport_type_names(self):
        def _compute():
            candidates = self._trainable_from_types(self._naval_yard_type_names())
            if not candidates:
                candidates = [
                    n
                    for n in rules.classnames()
                    if (uc := rules.unit_class(n)) is not None
                    and getattr(uc, "airground_type", None) == "water"
                    and getattr(uc, "transport_capacity", 0) > 0
                ]
            result = []
            for name in candidates:
                uc = rules.unit_class(name)
                if uc is None:
                    continue
                if getattr(uc, "airground_type", None) != "water":
                    continue
                if getattr(uc, "transport_capacity", 0) <= 0:
                    continue
                result.append(name)
            return tuple(result)

        return self._discovery_cache_get("water_transports", _compute)

    def _water_warship_type_names(self):
        def _compute():
            candidates = self._trainable_from_types(self._naval_yard_type_names())
            if not candidates:
                candidates = list(rules.classnames())
            result = []
            for name in candidates:
                uc = rules.unit_class(name)
                if uc is None:
                    continue
                if getattr(uc, "airground_type", None) != "water":
                    continue
                if getattr(uc, "transport_capacity", 0) > 0:
                    continue
                if not (getattr(uc, "mdg", 0) or getattr(uc, "rdg", 0)):
                    continue
                result.append(name)
            # Prefer cheaper warships first (destroyer before battleship).
            result.sort(
                key=lambda n: sum(getattr(rules.unit_class(n), "cost", ()) or ())
            )
            return tuple(result)

        return self._discovery_cache_get("water_warships", _compute)

    def _water_worker_type_names(self):
        """Trainable water workers (fishing ships): gather deposit/building, no warship."""

        def _compute():
            candidates = self._trainable_from_types(self._naval_yard_type_names())
            if not candidates:
                candidates = list(rules.classnames())
            result = []
            for name in candidates:
                uc = rules.unit_class(name)
                if uc is None:
                    continue
                if getattr(uc, "airground_type", None) != "water":
                    continue
                if getattr(uc, "transport_capacity", 0) > 0:
                    continue
                if getattr(uc, "mdg", 0) or getattr(uc, "rdg", 0):
                    continue
                if not (
                    getattr(uc, "can_gather_deposit", None)
                    or getattr(uc, "can_gather_building", None)
                ):
                    continue
                result.append(name)
            result.sort(
                key=lambda n: sum(getattr(rules.unit_class(n), "cost", ()) or ())
            )
            return tuple(result)

        return self._discovery_cache_get("water_workers", _compute)

    def _preferred_warehouse_class(self, resource_type=None):
        """Pick a buildable warehouse class; prefer dedicated storage when possible."""
        candidates = []
        for name in self._worker_buildable_type_names():
            uc = rules.unit_class(name)
            if uc is None:
                continue
            stores = tuple(getattr(uc, "storable_resource_types", ()) or ())
            if not stores:
                continue
            if resource_type is not None and resource_type not in stores:
                continue
            dedicated = 1 if len(stores) == 1 else 0
            coverage = len(stores)
            cost = sum(getattr(uc, "cost", ()) or ())
            # Dedicated dropoff near wood > multi-purpose hall when resource given;
            # otherwise prefer widest coverage (main hall).
            if resource_type is not None:
                score = (dedicated, -cost, coverage)
            else:
                score = (coverage, dedicated, -cost)
            candidates.append((score, name, uc))
        if not candidates:
            return None
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][2]

    def _best_warehouse(self, place=None, resource_type=None):
        if resource_type is None and isinstance(place, Deposit):
            resource_type = getattr(place, "resource_type", None)
        return self._preferred_warehouse_class(resource_type=resource_type)

    def _warehouse_economy_enabled(self):
        wh = self._preferred_warehouse_class()
        return wh is not None and bool(getattr(wh, "storable_resource_types", None))

    def _has_dedicated_dropoff_types(self):
        """True if workers can build a single-resource drop-off that is not the main base."""

        def _compute():
            main = set(self._main_base_type_names())
            for name in self._worker_buildable_type_names():
                if name in main:
                    continue
                uc = rules.unit_class(name)
                if uc is None:
                    continue
                stores = tuple(getattr(uc, "storable_resource_types", ()) or ())
                if len(stores) == 1:
                    return True
            return False

        return self._discovery_cache_get("dedicated_dropoff", _compute)

    def _auto_warehouse_expansion_enabled(self):
        """Build extra drop-offs when a dedicated mill/lumber/mining type exists.

        The generic warehouse lookup prefers the main hall (widest coverage).
        That must not disable lumber mills just because the town center already
        stores wood.
        """
        if self._has_dedicated_dropoff_types():
            return True
        wh_type = self._preferred_warehouse_class()
        if wh_type is None:
            return False
        main = self._main_base_type_names()
        if wh_type.type_name in main and self.nb(list(main)) >= 1:
            return False
        return True

    def _warehouse_spend_blocked_by_wood_reserve(self, warehouse_cost, stores=None):
        """True if this drop-off would steal wood needed for a get-line building."""
        cost = warehouse_cost or ()
        wood_cost = cost[1] if len(cost) > 1 else 0
        if wood_cost <= 0:
            return False
        stores = tuple(stores or ())
        later = self._later_age_startable_production_wood()
        res = getattr(self, "resources", None) or ()
        wood = res[1] if len(res) > 1 else 0
        # Blacksmith (etc.) for any_buildings must beat mills/camps; the lumber
        # "income investment" exception below must not spend that unlock stash.
        unlock_w = self._next_plan_phase_building_wood_need()
        if unlock_w and wood - wood_cost < unlock_w:
            return True
        # After castle, a gold/stone camp must not spend the workshop stash
        # even if the get-line wood reserve is briefly unseen on a watchdog line.
        if (
            stores
            and "resource2" not in stores
            and (
                self._wood_below_pending_building()
                or (later and wood < later)
                or (later and wood - wood_cost < later)
            )
        ):
            return True
        reserve = self._plan_expensive_wood_reserve(ignore_age_defer=True)
        if not reserve:
            return False
        if wood >= reserve:
            return True
        if wood - wood_cost >= reserve:
            return False
        if not self._owns_get_line_production_building():
            return True
        # After barracks: a lumber drop-off is an income investment unless we
        # are already close enough to place the next production building.
        # Callers that only pass a cost are treated as lumber (legacy tests).
        if not stores or "resource2" in stores:
            return wood * 5 >= reserve * 4
        # Gold/stone camps are not wood income; wait for the stash.
        return True

    def _dedicated_dropoff_at_cap(self, wh_type):
        """True if we already have enough copies of this single-resource drop-off."""
        if wh_type is None:
            return True
        stores = tuple(getattr(wh_type, "storable_resource_types", ()) or ())
        if len(stores) != 1:
            return False
        name = getattr(wh_type, "type_name", None)
        if not name:
            return False
        reserve = self._plan_expensive_wood_reserve(ignore_age_defer=True)
        cap = 1 if reserve else 2
        return self.future_nb(name) >= cap

    def _issue_build(self, type_name, target, workers=None):
        cls = rules.unit_class(type_name)
        worker_name = self._primary_worker_type_name()
        maker_cls = rules.unit_class(worker_name) if worker_name else None
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
                self._invalidate_play_derived_counts()
                issued += 1
        return issued > 0

    def _square_has_finished_dropoff(self, place, resource_type):
        """True if this square already has a completed building that stores the resource."""
        if place is None or resource_type is None:
            return False
        for o in getattr(place, "objects", ()) or ():
            if isinstance(o, BuildingSite):
                continue
            stores = getattr(o, "storable_resource_types", None)
            if stores and resource_type in stores:
                return True
        return False

    def _dropoff_building_site_on_square(self, place, resource_type):
        """BuildingSite on this square whose type would store the resource."""
        if place is None or resource_type is None:
            return None
        for o in getattr(place, "objects", ()) or ():
            if not isinstance(o, BuildingSite):
                continue
            stores = getattr(getattr(o, "type", None), "storable_resource_types", None)
            if stores and resource_type in stores:
                return o
        return None

    def _adjacent_usable_dropoff(self, place, resource_type):
        """Finished drop-off or warehouse site on an orthogonally adjacent square.

        Expansion only cares whether path distance exceeds one square_width.
        Neighbor squares are the only ones that can be that close, so this
        replaces nearest_warehouse + A*.
        """
        if place is None or resource_type is None:
            return None
        for e in getattr(place, "exits", ()) or ():
            other = getattr(e, "other_side", None)
            dest = getattr(other, "place", None) if other is not None else None
            if dest is None:
                continue
            try:
                if e.is_blocked(self, ignore_enemy_walls=True):
                    continue
            except Exception:
                continue
            try:
                if other.is_blocked(self, ignore_enemy_walls=True):
                    continue
            except Exception:
                continue
            try:
                if self.square_is_dangerous(dest):
                    continue
            except Exception:
                pass
            if self._square_has_finished_dropoff(dest, resource_type):
                return ("finished", None)
            site = self._dropoff_building_site_on_square(dest, resource_type)
            if site is not None:
                return ("site", site)
        return None

    def _warehouse_is_too_far(self, place, wh):
        """True if the drop-off is farther than one square (or has no safe path).

        Path length is at least Euclidean distance, so a warehouse more than
        one square_width away cannot satisfy the old ``d > square_width``
        test — skip A*. Orthogonal neighbors still need the avoid=True path.
        """
        if wh is None:
            return True
        wh_place = getattr(wh, "place", None)
        if wh_place is None:
            return True
        if wh_place is place:
            return False
        try:
            dx = place.x - wh_place.x
            dy = place.y - wh_place.y
            sw = self.world.square_width
            if dx * dx + dy * dy > sw * sw:
                return True
            d = place.shortest_path_distance_to(wh_place, self, avoid=True)
            return d > sw
        except Exception:
            return True

    def _build_a_warehouse_for(self, deposit):
        place = getattr(deposit, "place", None)
        if place is None:
            return
        resource_type = getattr(deposit, "resource_type", None)

        nearby_workers = [
            v
            for v in self._workers
            if (
                v.place is place
                or v.orders
                and v.orders[0].keyword == "gather"
                and (
                    v.orders[0].target is None
                    or v.orders[0].target.place is place
                )
            )
        ]
        if not nearby_workers:
            return

        # Home gold/wood sits on the townhall square: no A* needed.
        if self._square_has_finished_dropoff(place, resource_type):
            return

        site = self._dropoff_building_site_on_square(place, resource_type)
        if site is not None:
            if getattr(site, "_self_construct", False):
                return
            for v in nearby_workers:
                if worker_can_repair(v):
                    v.take_order(["repair", site.id])
                    return
            return

        adj = self._adjacent_usable_dropoff(place, resource_type)
        if adj is not None:
            kind, adj_site = adj
            if kind == "finished":
                return
            if adj_site is not None:
                if getattr(adj_site, "_self_construct", False):
                    return
                for v in nearby_workers:
                    if worker_can_repair(v):
                        v.take_order(["repair", adj_site.id])
                        return
                return

        # No drop-off within one square: equivalent to path d > square_width.
        wh_type = self._best_warehouse(resource_type=getattr(deposit, "resource_type", None))
        if wh_type is None:
            return
        # Never place a second town center / command center as a "drop-off".
        if getattr(wh_type, "type_name", None) in set(self._main_base_type_names()):
            return
        if self._dedicated_dropoff_at_cap(wh_type):
            return
        meadow = choose_build_target(
            self, wh_type, starting_place=deposit.place
        ) or self.choose(
            getattr(self.world, "building_land", "meadow"),
            starting_place=deposit.place,
        )
        if meadow:
            from .worldrequirements import requirements_satisfied

            if not requirements_satisfied(
                self, getattr(wh_type, "requirements", ()) or ()
            ):
                return
            cost = getattr(wh_type, "cost", None) or ()
            if self.missing_resources(cost):
                return
            stores = tuple(
                getattr(wh_type, "storable_resource_types", ()) or ()
            )
            if self._warehouse_spend_blocked_by_wood_reserve(
                cost, stores=stores
            ):
                return
            self._issue_build(wh_type.type_name, meadow, nearby_workers)

    def _maintain_expansions(self):
        """Build extra main bases up to the ``expand`` target.

        The starting base counts toward the total, so ``expand 2`` makes
        the AI build a single additional base. Disabled by default (``0``).
        """
        if self._target_townhalls <= 0:
            return
        bases = self._main_base_type_names()
        if not bases:
            return
        townhall = bases[0]
        cls = rules.unit_class(townhall)
        if cls is None:
            return
        if self.future_nb(list(bases)) >= self._target_townhalls:
            return
        if self.missing_resources(cls.cost):
            return
        self.build_or_train_or_upgradeto_or_summon(townhall)

    def _build_a_warehouse_if_useful(self):
        if not self._warehouse_economy_enabled() or not self._auto_warehouse_expansion_enabled():
            return
        seen = set()
        for u in self._workers:
            for o in u.orders:
                if o.keyword != "gather":
                    continue
                target = o.target
                if target is None or target.place is None:
                    continue
                tid = getattr(target, "id", None)
                if tid is None:
                    tid = id(target)
                if tid in seen:
                    continue
                seen.add(tid)
                self._build_a_warehouse_for(target)

    def _iter_types_on_get_line(self, line):
        """Yield unit type names named on one ai.txt ``get`` line."""
        yield from self._types_on_get_line(line)

    def _types_on_get_line(self, line):
        if not isinstance(line, str) or not line.startswith("get "):
            return ()
        return self._play_memo_get(
            ("get_line_types", line),
            lambda: self._types_on_get_line_compute(line),
        )

    def _types_on_get_line_compute(self, line):
        names = []
        for token in line.split()[1:]:
            if re.match("^[0-9]+$", token):
                continue
            name = self.equivalent(token)
            if rules.unit_class(name) is not None:
                names.append(name)
        return tuple(names)

    def _iter_current_get_line_types(self):
        """Yield unit type names named on the current ai.txt ``get`` line."""
        yield from self._current_get_line_types()

    def _current_get_line_types(self):
        return self._play_memo_get(
            ("cur_get_types", getattr(self, "_line_nb", 0)),
            self._current_get_line_types_compute,
        )

    def _current_get_line_types_compute(self):
        plan = getattr(self, "_plan", None) or []
        try:
            line = plan[self._line_nb]
        except Exception:
            return ()
        return self._types_on_get_line(line)

    def _iter_lookahead_get_line_types(self, extra_gets=2):
        """Yield types on the current get line and the next few get lines.

        Intermediate waves put castle/siege units on later ``get`` lines.
        Looking ahead lets the AI click castle and save food while still
        finishing the feudal barracks/archery wave.
        """
        yield from self._lookahead_get_line_types(extra_gets)

    def _lookahead_get_line_types(self, extra_gets=2):
        return self._play_memo_get(
            ("look_get_types", int(extra_gets), getattr(self, "_line_nb", 0)),
            lambda: self._lookahead_get_line_types_compute(extra_gets),
        )

    def _lookahead_get_line_types_compute(self, extra_gets=2):
        plan = getattr(self, "_plan", None) or []
        try:
            start = int(self._line_nb or 0)
        except Exception:
            start = 0
        names = []
        yielded_gets = 0
        i = start
        n = len(plan)
        while i < n and yielded_gets <= extra_gets:
            line = plan[i]
            if isinstance(line, str) and line.startswith("get "):
                names.extend(self._types_on_get_line(line))
                yielded_gets += 1
            i += 1
        return tuple(names)

    def _phase_requirement_names(self, type_name):
        """``class phase`` names listed in this type's ``has`` requirements."""
        cache = getattr(self, "_phase_req_cache", None)
        if cache is None:
            cache = {}
            self._phase_req_cache = cache
        if type_name not in cache:
            from .worldrequirements import parse_requirement_clauses

            found = []
            t = rules.unit_class(type_name)
            if t is not None:
                for clause in parse_requirement_clauses(
                    getattr(t, "requirements", ()) or ()
                ):
                    if clause[0] != "has":
                        continue
                    r = clause[1]
                    if rules.get(r, "class") == ["phase"] and r not in found:
                        found.append(r)
            cache[type_name] = tuple(found)
        return cache[type_name]

    def _upgrade_name_set(self):
        return self._play_memo_get(
            ("upgrade_set",),
            lambda: frozenset(getattr(self, "upgrades", None) or ()),
        )

    def _unmet_phase_names_for_type(self, type_name, include_makers=True):
        """Unmet ``class phase`` requirements of a unit (and optionally its makers)."""
        return self._play_memo_get(
            ("unmet_phases_type", type_name, bool(include_makers)),
            lambda: self._unmet_phase_names_for_type_compute(
                type_name, include_makers
            ),
        )

    def _unmet_phase_names_for_type_compute(self, type_name, include_makers=True):
        """Unmet ``class phase`` requirements of a unit (and optionally its makers)."""
        upg = self._upgrade_name_set()
        found = []

        def _add_from(tn):
            for r in self._phase_requirement_names(tn):
                if r not in upg and r not in found:
                    found.append(r)

        _add_from(type_name)
        if not include_makers:
            return found
        for maker in rules.get_makers(type_name) or ():
            mc = rules.unit_class(maker)
            if mc is None:
                continue
            try:
                if issubclass(mc, Worker):
                    continue
            except TypeError:
                continue
            _add_from(maker)
        return found

    def _plan_unmet_phase_names(self, lookahead=False):
        """Phases still needed by the current get line (and later waves if asked)."""
        return self._play_memo_get(
            ("unmet_phases", bool(lookahead), getattr(self, "_line_nb", 0)),
            lambda: self._plan_unmet_phase_names_compute(lookahead),
        )

    def _plan_unmet_phase_names_compute(self, lookahead=False):
        order = ("dark_age", "feudal_age", "castle_age", "imperial_age")
        found = []
        names = (
            self._iter_lookahead_get_line_types()
            if lookahead
            else self._iter_current_get_line_types()
        )
        for name in names:
            for phase in self._unmet_phase_names_for_type(name):
                if phase not in found:
                    found.append(phase)
        found.sort(key=lambda p: order.index(p) if p in order else 99)
        return found

    def _plan_has_deferred_unit_phase(self):
        """True if a current-line unit itself still needs an age (not just its building)."""
        for name in self._iter_current_get_line_types():
            if self._is_worker_type_name(name):
                continue
            if self._unmet_phase_names_for_type(name, include_makers=False):
                return True
        return False

    def _should_click_plan_phase(self):
        """Click the earliest unmet age for the current/next get waves."""
        return self._play_memo_get(
            ("click_phase", getattr(self, "_line_nb", 0)),
            self._should_click_plan_phase_compute,
        )

    def _should_click_plan_phase_compute(self):
        # Click an age the current get line itself still needs.
        if self._plan_unmet_phase_names(lookahead=False):
            return True
        # Dark villager wave: feudal is only on later lines — still click it.
        if self._before_first_expensive_food_age():
            return bool(self._plan_unmet_phase_names(lookahead=True))
        # Do not skip a feudal army to rush castle from a later get line.
        return False

    def _click_plan_phase_if_ready(self):
        """Bank age cost and get() the next plan phase (buildings + advance)."""
        phases = self._plan_unmet_phase_names(lookahead=True)
        if not phases or not self._should_click_plan_phase():
            return
        pc = rules.unit_class(phases[0])
        if pc is not None:
            cost = getattr(pc, "cost", None) or ()
            pop = getattr(pc, "population_cost", 0) or 0
            if cost:
                # Even if any_buildings still blocks advance, pull villagers onto
                # food/gold so orchards are used while blacksmith is placed.
                self.gather(cost, pop)
        self.get(1, phases[0])

    def _age_up_missing_resource_types(self):
        """Resource type names still needed to click the next plan age-up."""
        return self._play_memo_get(
            ("age_missing", getattr(self, "_line_nb", 0)),
            self._age_up_missing_resource_types_compute,
        )

    def _age_up_missing_resource_types_compute(self):
        """Resource type names still needed to click the next plan age-up."""
        if not self._should_click_plan_phase():
            return frozenset()
        phases = self._plan_unmet_phase_names(lookahead=True)
        if not phases:
            return frozenset()
        pc = rules.unit_class(phases[0])
        cost = getattr(pc, "cost", None) or ()
        if not cost or getattr(self, "resources", None) is None:
            return frozenset()
        missing = self.missing_resources(cost) or ()
        return frozenset(f"resource{i + 1}" for i in missing)

    def _age_up_needs_food(self):
        # Feudal already has a mill/farm path; do not steal barracks wood.
        return self._play_memo_get("age_up_needs_food", self._age_up_needs_food_compute)

    def _age_up_needs_food_compute(self):
        if self._saving_food_for_age():
            return False
        return "resource3" in self._age_up_missing_resource_types()

    def _spend_would_block_age_up(self, cost):
        """True if this spend would leave too little for the next plan age-up.

        Dark-age loom must still fire while saving for the first expensive age.
        After that, do not dump castle food/gold into line upgrades, even on a
        watchdog get line that is not itself clicking the age this turn.
        """
        cost = cost or ()
        if self._saving_food_for_age():
            return False
        if not self._should_click_plan_phase():
            return False
        phases = self._plan_unmet_phase_names(lookahead=True)
        if not phases or not self._phase_saves_food(phases[0]):
            return False
        pc = rules.unit_class(phases[0])
        pcost = getattr(pc, "cost", None) or ()
        if not pcost:
            return False
        res = getattr(self, "resources", None) or ()
        for i, amount in enumerate(cost):
            if not amount:
                continue
            need = pcost[i] if i < len(pcost) else 0
            if not need:
                continue
            have = res[i] if i < len(res) else 0
            if have - amount < need:
                return True
        return False

    def _is_worker_type_name(self, name):
        if not isinstance(name, str):
            uc = name
            try:
                return uc is not None and issubclass(uc, Worker)
            except TypeError:
                return False
        cache = self._discovery_cache_get("is_worker_name", dict)
        if name not in cache:
            uc = rules.unit_class(name)
            try:
                cache[name] = uc is not None and issubclass(uc, Worker)
            except TypeError:
                cache[name] = False
        return cache[name]

    def _phase_food_cost(self, phase_name):
        pc = rules.unit_class(phase_name) if phase_name else None
        cost = getattr(pc, "cost", None) or ()
        return cost[2] if len(cost) > 2 else 0

    def _phase_saves_food(self, phase_name):
        """True when this age-up spends a large food stockpile (AoE2 feudal)."""
        return self._phase_food_cost(phase_name) >= to_int("100")

    def _feudal_age_saves_food(self):
        """True if rules define feudal_age as an expensive-food click."""
        return self._phase_saves_food("feudal_age")

    def _saving_food_for_age(self):
        """True when the get line is blocked on the first expensive-food age-up.

        Later expensive ages (AoE2 castle is 800 food) must not freeze barracks
        or militia after an earlier expensive age is already complete.
        """
        return self._play_memo_get(
            ("saving_food", getattr(self, "_line_nb", 0)),
            self._saving_food_for_age_compute,
        )

    def _saving_food_for_age_compute(self):
        phases = self._plan_unmet_phase_names()
        if not phases or not self._phase_saves_food(phases[0]):
            return False
        current = phases[0]
        upgrades = getattr(self, "upgrades", None) or ()
        for name in rules.classnames():
            if name == current:
                continue
            if rules.get(name, "class") != ["phase"]:
                continue
            if not self._phase_saves_food(name):
                continue
            if name in upgrades:
                return False
        return True

    def _first_expensive_food_phase_name(self):
        """Earliest high-food age in the ruleset (AoE2 feudal), or None."""
        for name in ("dark_age", "feudal_age", "castle_age", "imperial_age"):
            if rules.get(name, "class") == ["phase"] and self._phase_saves_food(name):
                return name
        return None

    def _plan_unit_type_names(self):
        """Unit type names named on any ``get`` line of the current AI plan."""
        found = []
        seen = set()
        for line in getattr(self, "_plan", None) or ():
            for name in self._iter_types_on_get_line(line):
                if name not in seen:
                    seen.add(name)
                    found.append(name)
        return found

    def _later_age_startable_production_wood(self):
        """Wood cost of an unbuilt production building unlocked after the first expensive age.

        Watchdog lines can hide workshop from the current get-line lookahead.
        Scanning every get line for a startable trainer of a planned unit keeps
        the 200-wood stash after castle even when the feudal get is active.
        """
        return self._play_memo_get(
            (
                "later_prod_wood",
                getattr(self, "_line_nb", 0),
                tuple(getattr(self, "upgrades", None) or ()),
            ),
            self._later_age_startable_production_wood_compute,
        )

    def _later_age_startable_production_wood_compute(self):
        from .worldrequirements import parse_requirement_clauses, requirements_satisfied

        first = self._first_expensive_food_phase_name()
        upgrades = getattr(self, "upgrades", None) or ()
        wanted = set(self._plan_unit_type_names())
        if not wanted:
            return 0
        best = 0
        for name in self._worker_buildable_type_names():
            uc = rules.unit_class(name)
            if uc is None:
                continue
            if self.nb(name) > 0 or self.future_nb(name) > 0:
                continue
            cost = getattr(uc, "cost", None) or ()
            wood = cost[1] if len(cost) > 1 else 0
            if wood < to_int("100"):
                continue
            reqs = getattr(uc, "requirements", ()) or ()
            if not requirements_satisfied(self, reqs):
                continue
            unlocked = False
            for clause in parse_requirement_clauses(reqs):
                if clause[0] != "has":
                    continue
                phase = clause[1]
                if (
                    rules.get(phase, "class") == ["phase"]
                    and self._phase_saves_food(phase)
                    and phase != first
                    and phase in upgrades
                ):
                    unlocked = True
                    break
            if not unlocked:
                continue
            trains = set(rules.class_rules_attr(uc, "can_train", ()) or ())
            if not (trains & wanted):
                continue
            if wood > best:
                best = wood
        return best

    def _before_first_expensive_food_age(self):
        """True until the first high-food age-up is in upgrades (AoE2 dark age)."""
        if self._saving_food_for_age():
            return True
        if not self._ruleset_has_expensive_food_age():
            return False
        return not any(
            self._phase_saves_food(name)
            for name in (getattr(self, "upgrades", None) or ())
        )

    def _watchdog_should_wait(self):
        """True if the stuck-line timer must not skip the current plan row."""
        if self._before_first_expensive_food_age():
            return True
        try:
            line = self._plan[self._line_nb]
        except Exception:
            return False
        if not isinstance(line, str) or not line.startswith("get "):
            return False

        def _ok(fn):
            try:
                return bool(fn())
            except Exception:
                return False

        if _ok(self._age_click_in_progress):
            return True
        if _ok(self._should_click_plan_phase) and _ok(
            self._age_up_missing_resource_types
        ):
            return True
        # Feudal army get intentionally does not click castle. Later-wave wood
        # (workshop) and trainer food must not freeze the stuck-line timer —
        # soldiers dying at an AFK TC would never reach the castle/ram wave.
        if (
            not self._plan_unmet_phase_names(lookahead=False)
            and self._plan_unmet_phase_names(lookahead=True)
        ):
            if self._pending_production_makers(ignore_age_defer=False):
                return True
            if _ok(self._plan_get_maker_in_progress):
                return True
            return False
        if _ok(self._wood_below_pending_building):
            return True
        if _ok(self._has_startable_plan_production_building):
            return True
        if _ok(self._plan_get_maker_in_progress):
            return True
        if _ok(self._owned_trainer_wood_need) or _ok(self._owned_trainer_food_need):
            return True
        return False

    def _ruleset_has_expensive_food_age(self):
        """True if any ``class phase`` in the loaded rules costs much food."""

        def _compute():
            for name in rules.classnames():
                if rules.get(name, "class") == ["phase"] and self._phase_saves_food(
                    name
                ):
                    return True
            return False

        return self._discovery_cache_get("expensive_food_age", _compute)

    def _first_startable_unpaid_maker_cost(self):
        """Gold, wood of the first unpaid get-line production building current ages allow.

        Does not call ``_defer_plan_get_token`` (that method must stay recursion-free).
        """
        return self._play_memo_get(
            ("first_startable", getattr(self, "_line_nb", 0)),
            self._first_startable_unpaid_maker_cost_compute,
        )

    def _first_startable_unpaid_maker_cost_compute(self):
        from .worldrequirements import requirements_satisfied

        nb = getattr(self, "nb", None)
        future_nb = getattr(self, "future_nb", None)
        if not callable(nb):
            return 0, 0
        if not callable(future_nb):
            future_nb = lambda _n: 0
        land_only = not self._map_has_water()
        for name in self._iter_plan_production_type_names():
            if self._is_worker_type_name(name):
                continue
            # Land maps never place shipyards; do not bank gold/wood for them
            # (or unit→unit “makers” like darkarcher←archer) while barracks
            # already owns the current wave.
            if land_only and self._type_needs_water(name):
                continue
            owned_maker = False
            pending = None
            for maker in rules.get_makers(name) or ():
                mc = rules.unit_class(maker)
                if mc is None:
                    continue
                try:
                    if issubclass(mc, Worker):
                        continue
                except TypeError:
                    continue
                if not getattr(mc, "is_a_building", False):
                    continue
                if land_only and self._type_needs_water(maker):
                    continue
                if nb(maker) > 0 or future_nb(maker) > 0:
                    owned_maker = True
                    break
                cost = getattr(mc, "cost", None) or ()
                gold = cost[0] if cost else 0
                wood = cost[1] if len(cost) > 1 else 0
                # Stone-only unique buildings (AoE2 castle) must not hide a later
                # wood/gold workshop on the next get line.
                if not gold and not wood:
                    continue
                if not requirements_satisfied(
                    self, getattr(mc, "requirements", ()) or ()
                ):
                    continue
                pending = mc
                break
            if owned_maker or pending is None:
                continue
            cost = getattr(pending, "cost", None) or ()
            gold = cost[0] if cost else 0
            wood = cost[1] if len(cost) > 1 else 0
            return gold, wood
        return 0, 0

    def _defer_plan_get_token(self, type_name, saving_for_feudal=False):
        """Skip a get-line token this turn (unmet age on the unit, or save food)."""
        return self._play_memo_get(
            (
                "defer_token",
                type_name,
                bool(saving_for_feudal),
                getattr(self, "_line_nb", 0),
            ),
            lambda: self._defer_plan_get_token_compute(
                type_name, saving_for_feudal
            ),
        )

    def _defer_plan_get_token_compute(self, type_name, saving_for_feudal=False):
        """Skip a get-line token this turn (unmet age on the unit, or save food)."""
        # Only the unit's own phase — maker buildings (barracks needs feudal in
        # default res) must still go through get() so the AI clicks the age.
        if self._unmet_phase_names_for_type(type_name, include_makers=False):
            return True
        if saving_for_feudal and not self._is_worker_type_name(type_name):
            return True
        if self._is_worker_type_name(type_name):
            n = len(getattr(self, "_workers", ()) or ())
            if n >= 6 and self._saving_food_for_age():
                phases = self._plan_unmet_phase_names()
                if phases and getattr(self, "resources", None) is not None:
                    pc = rules.unit_class(phases[0])
                    cost = getattr(pc, "cost", None) if pc is not None else None
                    if cost and self.missing_resources(cost):
                        return True
            if n >= 8:
                later = self._plan_unmet_phase_names(lookahead=False)
                if (
                    later
                    and self._phase_saves_food(later[0])
                    and getattr(self, "resources", None) is not None
                ):
                    pc = rules.unit_class(later[0])
                    cost = getattr(pc, "cost", None) if pc is not None else None
                    if cost and self.missing_resources(cost):
                        wt = rules.unit_class(type_name)
                        wcost = getattr(wt, "cost", None) or ()
                        food = wcost[2] if len(wcost) > 2 else 0
                        need = cost[2] if len(cost) > 2 else 0
                        have = 0
                        res = self.resources or ()
                        if len(res) > 2:
                            have = res[2]
                        if food and need and have - food < need:
                            return True
                trainer_food = self._owned_trainer_food_need()
                if trainer_food and getattr(self, "resources", None) is not None:
                    wt = rules.unit_class(type_name)
                    wcost = getattr(wt, "cost", None) or ()
                    food = wcost[2] if len(wcost) > 2 else 0
                    have = 0
                    res = self.resources or ()
                    if len(res) > 2:
                        have = res[2]
                    if food and have - food < trainer_food:
                        return True
            return False
        # After the age-up, do not dump wood/gold into soldiers whose own
        # production building is already up while a later startable get-line
        # building (workshop after castle) is still unpaid. Must not call
        # _iter_pending / _plan_next_production_building_cost (recursion).
        nb = getattr(self, "nb", None)
        future_nb = getattr(self, "future_nb", None)
        if callable(nb):
            uc = rules.unit_class(type_name)
            cost = getattr(uc, "cost", None) or ()
            sw = cost[1] if len(cost) > 1 else 0
            sg = cost[0] if cost else 0
            if sw or sg:
                own_owned = False
                for maker in rules.get_makers(type_name) or ():
                    fut = future_nb(maker) if callable(future_nb) else 0
                    if nb(maker) > 0 or fut > 0:
                        own_owned = True
                        break
                if own_owned:
                    pg, pw = self._first_startable_unpaid_maker_cost()
                    if pw and sw:
                        return True
                    if pg and sg:
                        return True
        return False

    def _phase_advance_in_progress(self, phase_name):
        """True if a town center (or similar) is already researching this age."""
        if not phase_name:
            return False
        fut = getattr(self, "future_nb", None)
        nb = getattr(self, "nb", None)
        if not callable(fut):
            return False
        try:
            in_prod = fut(phase_name)
            have = nb(phase_name) if callable(nb) else 0
        except Exception:
            return False
        return in_prod > have

    def _age_click_in_progress(self):
        """True if the next plan age-up is already paying its research time."""
        later = self._plan_unmet_phase_names(lookahead=True)
        return bool(later) and self._phase_advance_in_progress(later[0])

    def _iter_plan_production_type_names(self):
        """Get-line unit names whose makers can still be the next wood/gold spend.

        While an expensive later age still needs food, stay on the current line
        so a later stables/workshop does not freeze farms. Once that age is
        clicking (or paid), look ahead so the 160s castle research still banks
        workshop wood.
        """
        yield from self._play_memo_get(
            ("plan_prod_types", getattr(self, "_line_nb", 0)),
            self._plan_production_type_names_compute,
        )

    def _plan_production_type_names_compute(self):
        later = self._plan_unmet_phase_names(lookahead=True)
        if (
            later
            and self._phase_saves_food(later[0])
            and not self._phase_advance_in_progress(later[0])
        ):
            # Keep farms running for that age, but still see a later-line
            # building that can already be placed (workshop after castle,
            # while imperial food is still unpaid).
            names = list(self._iter_current_get_line_types())
            names.extend(self._iter_startable_later_get_line_types())
            return tuple(names)
        return tuple(self._iter_lookahead_get_line_types(extra_gets=2))

    def _iter_startable_later_get_line_types(self):
        """Later get-line units unlocked by a completed post-feudal expensive age.

        Stables are placeable after feudal and must not freeze castle farms.
        Workshop requires castle, so after castle it must still bank wood even
        on a watchdog line while imperial food is unpaid.
        """
        from .worldrequirements import parse_requirement_clauses, requirements_satisfied

        first_expensive = self._first_expensive_food_phase_name()
        upgrades = getattr(self, "upgrades", None) or ()
        seen = set()
        for name in self._iter_current_get_line_types():
            seen.add(name)
        land_only = not self._map_has_water()
        for name in self._iter_lookahead_get_line_types(extra_gets=2):
            if name in seen:
                continue
            seen.add(name)
            if self._is_worker_type_name(name):
                continue
            if land_only and self._type_needs_water(name):
                continue
            for maker in rules.get_makers(name) or ():
                mc = rules.unit_class(maker)
                if mc is None:
                    continue
                try:
                    if issubclass(mc, Worker):
                        continue
                except TypeError:
                    continue
                if not getattr(mc, "is_a_building", False):
                    continue
                if land_only and self._type_needs_water(maker):
                    continue
                if self.nb(maker) > 0 or self.future_nb(maker) > 0:
                    break
                cost = getattr(mc, "cost", None) or ()
                gold = cost[0] if cost else 0
                wood = cost[1] if len(cost) > 1 else 0
                if not gold and not wood:
                    continue
                if not requirements_satisfied(
                    self, getattr(mc, "requirements", ()) or ()
                ):
                    continue
                unlocked_by_later_age = False
                for clause in parse_requirement_clauses(
                    getattr(mc, "requirements", ()) or ()
                ):
                    if clause[0] != "has":
                        continue
                    phase = clause[1]
                    if rules.get(phase, "class") != ["phase"]:
                        continue
                    if (
                        self._phase_saves_food(phase)
                        and phase != first_expensive
                        and phase in upgrades
                    ):
                        unlocked_by_later_age = True
                        break
                if unlocked_by_later_age:
                    yield name
                    break

    def _iter_pending_production_makers(self, ignore_age_defer=False):
        """Maker classes of get-line units whose production building is not started."""
        from .worldrequirements import requirements_satisfied

        saving_for_feudal = (not ignore_age_defer) and self._saving_food_for_age()
        buildable = self._worker_buildable_type_names()
        land_only = not self._map_has_water()
        for name in self._iter_plan_production_type_names():
            if self._is_worker_type_name(name):
                continue
            if land_only and self._type_needs_water(name):
                continue
            # Full ``_defer_plan_get_token`` (soldier-hold / workshop tail) is for
            # get(); pending buildings only need own-phase + feudal-save skip.
            if saving_for_feudal:
                continue
            deferred = bool(
                self._unmet_phase_names_for_type(name, include_makers=False)
            )
            if not deferred and self.nb(name) > 0:
                continue
            owned_maker = False
            pending = []
            for maker in rules.get_makers(name) or ():
                mc = rules.unit_class(maker)
                if mc is None:
                    continue
                try:
                    if issubclass(mc, Worker):
                        continue
                except TypeError:
                    continue
                if not getattr(mc, "is_a_building", False):
                    continue
                if land_only and self._type_needs_water(maker):
                    continue
                if self.nb(maker) > 0 or self.future_nb(maker) > 0:
                    # briton_barracks counts as barracks; do not also treat
                    # frank_barracks / chinese_barracks as still-missing.
                    owned_maker = True
                    break
                # captured_barracks (cost 0) lists as a footman maker but peasants
                # cannot build it; using it as the "next" building zeroed the
                # gold/wood reserve and let farms spend the barracks stash.
                cost = getattr(mc, "cost", None) or ()
                gold = cost[0] if cost else 0
                wood = cost[1] if len(cost) > 1 else 0
                # captured_barracks (all zeros) and stone-only unique buildings
                # (AoE2 castle) must not zero the gold/wood reserve.
                if not gold and not wood:
                    continue
                if (
                    deferred
                    and not requirements_satisfied(
                        self, getattr(mc, "requirements", ()) or ()
                    )
                ):
                    if not ignore_age_defer:
                        continue
                    # ignore_age_defer banks workshop wood during the castle
                    # click. Before that click (e.g. still missing blacksmith
                    # for any_buildings 2), do not reserve 200 wood or the
                    # unlock building never gets paid.
                    if not self._age_click_in_progress():
                        continue
                pending.append(mc)
            if owned_maker:
                continue
            if not pending:
                continue
            pending.sort(
                key=lambda mc: 0
                if (
                    getattr(mc, "type_name", None) in buildable
                    or getattr(mc, "__name__", None) in buildable
                )
                else 1
            )
            for mc in pending:
                yield mc
            # First unbuilt production building only (barracks before range).
            return

    def _pending_production_makers(self, ignore_age_defer=False):
        """Tuple of pending maker classes; shared by wood/next/startable checks."""
        return self._play_memo_get(
            (
                "pending_makers",
                bool(ignore_age_defer),
                getattr(self, "_line_nb", 0),
            ),
            lambda: tuple(
                self._iter_pending_production_makers(
                    ignore_age_defer=ignore_age_defer
                )
            ),
        )

    def _plan_wood_building_cost(self, ignore_age_defer=False):
        """Wood cost of the next unbuilt production building on the get line."""
        return self._play_memo_get(
            (
                "plan_wood",
                bool(ignore_age_defer),
                getattr(self, "_line_nb", 0),
            ),
            lambda: self._plan_wood_building_cost_compute(ignore_age_defer),
        )

    def _plan_wood_building_cost_compute(self, ignore_age_defer=False):
        """Wood cost of the next unbuilt production building on the get line."""
        best = 0
        for mc in self._pending_production_makers(
            ignore_age_defer=ignore_age_defer
        ):
            cost = getattr(mc, "cost", None) or ()
            if len(cost) > 1 and cost[1] > best:
                best = cost[1]
        return best

    def _plan_next_production_building_cost(self, ignore_age_defer=False):
        """Gold, wood of the first unbuilt get-line production building."""
        return self._play_memo_get(
            (
                "plan_next",
                bool(ignore_age_defer),
                getattr(self, "_line_nb", 0),
            ),
            lambda: self._plan_next_production_building_cost_compute(
                ignore_age_defer
            ),
        )

    def _plan_next_production_building_cost_compute(self, ignore_age_defer=False):
        for mc in self._pending_production_makers(
            ignore_age_defer=ignore_age_defer
        ):
            cost = getattr(mc, "cost", None) or ()
            gold = cost[0] if cost else 0
            wood = cost[1] if len(cost) > 1 else 0
            return gold, wood
        return 0, 0

    def _would_spend_past_plan_building(self, spend_cost, ignore_age_defer=False):
        """True if this spend would leave too little gold/wood for the get-line building."""
        pg, pw = self._plan_next_production_building_cost(
            ignore_age_defer=ignore_age_defer
        )
        trainer_w = self._owned_trainer_wood_need()
        if trainer_w > pw:
            pw = trainer_w
        spend_cost = spend_cost or ()
        sg = spend_cost[0] if len(spend_cost) > 0 else 0
        sw = spend_cost[1] if len(spend_cost) > 1 else 0
        unlock_w = self._next_plan_phase_building_wood_need()
        # Exact unlock cost (blacksmith 150) must beat a larger pending maker
        # (barracks 175): castle any_buildings cannot wait on barracks wood.
        if unlock_w and sw == unlock_w:
            return False
        if unlock_w and sw < unlock_w and unlock_w > pw:
            pw = unlock_w
        if not pg and not pw:
            return False
        if (
            ignore_age_defer
            and self._age_up_needs_food()
            and not self._has_startable_plan_production_building()
            and not self._age_click_in_progress()
            and not unlock_w
        ):
            return False
        res = getattr(self, "resources", None) or ()
        gold = res[0] if len(res) > 0 else 0
        wood = res[1] if len(res) > 1 else 0
        return gold - sg < pg or wood - sw < pw

    def _plan_expensive_wood_reserve(self, ignore_age_defer=False):
        """Wood to keep for a costly production building (AoE2 175), else 0."""
        return self._play_memo_get(
            (
                "plan_expensive_wood",
                bool(ignore_age_defer),
                getattr(self, "_line_nb", 0),
            ),
            lambda: self._plan_expensive_wood_reserve_compute(ignore_age_defer),
        )

    def _plan_expensive_wood_reserve_compute(self, ignore_age_defer=False):
        cost = self._plan_wood_building_cost(ignore_age_defer=ignore_age_defer)
        later = self._later_age_startable_production_wood()
        if later > cost:
            cost = later
        trainer_w = self._owned_trainer_wood_need()
        if trainer_w > cost:
            cost = trainer_w
        unlock_w = self._next_plan_phase_building_wood_need()
        if unlock_w > cost:
            cost = unlock_w
        if cost >= to_int("100"):
            return cost
        return 0

    def _wood_below_pending_building(self):
        """True if wood is still short of the next get-line production building."""
        return self._play_memo_get(
            (
                "wood_below",
                getattr(self, "_line_nb", 0),
                tuple(getattr(self, "resources", None) or ()),
            ),
            self._wood_below_pending_building_compute,
        )

    def _wood_below_pending_building_compute(self):
        # Dark age must bank food for feudal; barracks wood is not the pinch yet.
        if self._before_first_expensive_food_age():
            return False
        trainer_w = self._owned_trainer_wood_need()
        _pg, pw = self._plan_next_production_building_cost(ignore_age_defer=True)
        later = self._later_age_startable_production_wood()
        if later > pw:
            pw = later
        if trainer_w > pw:
            pw = trainer_w
        if not pw:
            return False
        res = getattr(self, "resources", None) or ()
        wood = res[1] if len(res) > 1 else 0
        if wood >= pw:
            return False
        # Owned siege workshop still needs ram wood after the building is paid.
        if trainer_w and wood < trainer_w:
            return True
        # Workshop cannot be placed until castle finishes, but the 160s click
        # has already paid the food — chop then, instead of planting more farms.
        if (
            later
            or self._has_startable_plan_production_building()
            or self._age_click_in_progress()
        ):
            return True
        return False

    def _age_up_farm_wood_reserve(self):
        """Wood to keep so auto-cultivate food buildings can restart for an age-up.

        Bank one recultivate even while farms are still producing: they empty
        together, and a house or tech would otherwise spend the last 40 wood.
        """
        if self._before_first_expensive_food_age():
            return 0
        if self._wood_below_pending_building():
            return 0
        if not self._age_up_needs_food():
            return 0
        need = self._cultivate_missing_wood()
        if need:
            return need
        for u in getattr(self, "units", ()) or ():
            if not getattr(u, "auto_cultivate", 0):
                continue
            prod = getattr(u, "production_cost", None)
            if prod is None:
                prod = getattr(getattr(u, "type", None), "production_cost", None)
            prod = prod or ()
            wood = prod[1] if len(prod) > 1 else 0
            if wood:
                return wood
        return 0

    def _need_wood_for_age_up_farms(self):
        """True if a later expensive age needs food but recultivate wood is short."""
        need = self._age_up_farm_wood_reserve()
        if not need:
            return False
        res = getattr(self, "resources", None) or ()
        wood = res[1] if len(res) > 1 else 0
        return wood < need

    def _keep_lumberjacks(self):
        """True when lumberjacks must not be pulled onto farms or gold."""
        return self._wood_below_pending_building() or self._need_wood_for_age_up_farms()

    def _should_keep_farms_producing(self):
        """True if idle mills should recultivate.

        Pending production-building wood wins over a later expensive age-up:
        a 60-wood farm must not freeze archery after barracks is already up.
        Before the first expensive-food age is researched, keep farms even
        on watchdog/timer lines that are not themselves a ``get``.
        """
        return self._play_memo_get(
            (
                "keep_farms",
                getattr(self, "_line_nb", 0),
                tuple(getattr(self, "resources", None) or ()),
            ),
            self._should_keep_farms_producing_compute,
        )

    def _should_keep_farms_producing_compute(self):
        """True if idle mills should recultivate."""
        if self._before_first_expensive_food_age():
            return True
        res = getattr(self, "resources", None) or ()
        trainer_w = self._owned_trainer_wood_need()
        wood = res[1] if len(res) > 1 else 0
        if trainer_w and wood < trainer_w:
            return False
        _pg, pw = self._plan_next_production_building_cost(ignore_age_defer=True)
        if pw and len(res) > 1 and res[1] < pw:
            # Unpaid archery still wins; an unplaceable next-age workshop must not
            # freeze farms — unless that age is already researching.
            if not (
                self._age_up_needs_food()
                and not self._has_startable_plan_production_building()
                and not self._age_click_in_progress()
            ):
                food_need = self._owned_trainer_food_need()
                food = res[2] if len(res) > 2 else 0
                if food_need and food < food_need:
                    return True
                return False
        if self._age_up_needs_food():
            # Castle food must not recultivate farms while any_buildings still
            # needs a wood-cost unlock (blacksmith): farms eat the 150 wood.
            need_w = self._next_plan_phase_building_wood_need()
            wood = res[1] if len(res) > 1 else 0
            if need_w and wood < need_w:
                return False
            return True
        food_need = self._owned_trainer_food_need()
        food = res[2] if len(res) > 2 else 0
        return bool(food_need) and food < food_need

    def _next_plan_phase_building_wood_need(self):
        """Wood to place the next any_buildings unlock for the planned age-up."""
        from .worldrequirements import (
            ANY_BUILDINGS,
            count_owned_buildings_of_group,
            iter_unmet_building_candidates,
            parse_requirement_clauses,
        )

        if not self._should_click_plan_phase():
            return 0
        phases = self._plan_unmet_phase_names(lookahead=True)
        if not phases:
            return 0
        pc = rules.unit_class(phases[0])
        if pc is None:
            return 0
        buildable = self._worker_buildable_type_names()
        land_only = not self._map_has_water()
        # Use full requirement counts (not missing_requirement_clauses): that
        # helper already subtracts owned buildings, so owned>=missing_count would
        # wrongly treat "need 1 more of 2" as satisfied.
        for clause in parse_requirement_clauses(
            getattr(pc, "requirements", ()) or ()
        ):
            if clause[0] != ANY_BUILDINGS:
                continue
            _, count, group = clause
            if count_owned_buildings_of_group(self, group) >= count:
                continue
            for r in iter_unmet_building_candidates(self, group):
                if land_only and self._type_needs_water(r):
                    continue
                eq = self.equivalent(r) if isinstance(r, str) else r
                if r not in buildable and eq not in buildable:
                    continue
                if self.nb(r) > 0 or self.future_nb(r) > 0:
                    continue
                if self.nb(eq) > 0 or self.future_nb(eq) > 0:
                    continue
                uc = rules.unit_class(r)
                cost = getattr(uc, "cost", None) or () if uc is not None else ()
                wood = cost[1] if len(cost) > 1 else 0
                if wood:
                    return wood
        return 0

    def _plan_wants_unbuilt_wood_building(self, ignore_age_defer=False):
        """True if the current get line still needs a wood-cost production building."""
        return self._plan_wood_building_cost(ignore_age_defer=ignore_age_defer) > 0

    def _owns_get_line_production_building(self):
        """True if any get-line military production building is already up."""
        for name in self._iter_current_get_line_types():
            if self._is_worker_type_name(name):
                continue
            for maker in rules.get_makers(name) or ():
                if self.nb(maker) > 0:
                    return True
        return False

    def _has_startable_plan_production_building(self):
        """True if a get-line production building can be placed with current ages."""
        return self._play_memo_get(
            ("has_startable", getattr(self, "_line_nb", 0)),
            self._has_startable_plan_production_building_compute,
        )

    def _has_startable_plan_production_building_compute(self):
        if self._saving_food_for_age():
            return False
        # Pending makers already skip unmet ages; do not re-check full
        # requirements (town_center etc.) — stub AIs and the click-phase
        # test only model owned ages via ``upgrades``.
        return bool(self._pending_production_makers(ignore_age_defer=False))

    def _plan_get_maker_in_progress(self):
        """True if a get-line production building is already under construction."""
        nb = getattr(self, "nb", None)
        future_nb = getattr(self, "future_nb", None)
        if not callable(nb) or not callable(future_nb):
            return False
        for name in self._iter_current_get_line_types():
            if self._is_worker_type_name(name):
                continue
            for maker in rules.get_makers(name) or ():
                try:
                    if future_nb(maker) > nb(maker):
                        return True
                except Exception:
                    continue
        return False

    def _need_later_age_production_wood(self):
        """True when a castle-unlocked production building (workshop) still needs wood.

        Watchdog lines hide workshop from ``_has_startable_plan_production_building``
        after feudal barracks/range/stable are already up.
        """
        return bool(
            self._wood_below_pending_building()
            and self._later_age_startable_production_wood()
        )

    def _trainer_blocked_by_later_age_wood(self, type_name):
        """True if this trainer would spend wood still needed for workshop.

        Monastery costs 175 wood and is startable in the same age as workshop
        (200 wood). ``get(monk)`` must not place it first and dump the stash.
        """
        later = self._later_age_startable_production_wood()
        if not later:
            return False
        uc = (
            rules.unit_class(type_name)
            if isinstance(type_name, str)
            else type_name
        )
        if uc is None:
            return False
        trains = rules.class_rules_attr(uc, "can_train", ()) or ()
        if not trains:
            return False
        cost = getattr(uc, "cost", None) or ()
        wood_cost = cost[1] if len(cost) > 1 else 0
        if wood_cost <= 0:
            return False
        if wood_cost >= later:
            return False
        return True

    def _should_hold_extra_workers(self, n_workers, worker_type):
        """Stop extra villagers only when they spend the stockpile we are saving."""
        if n_workers < 6:
            return False
        phases = self._plan_unmet_phase_names()
        if self._saving_food_for_age() and phases:
            pc = rules.unit_class(phases[0])
            cost = getattr(pc, "cost", None) if pc is not None else None
            if cost and self.missing_resources(cost):
                return True
        later = self._plan_unmet_phase_names(lookahead=True)
        if n_workers >= 8 and later and self._phase_saves_food(later[0]):
            pc = rules.unit_class(later[0])
            cost = getattr(pc, "cost", None) if pc is not None else None
            if cost and self.missing_resources(cost):
                wt = rules.unit_class(worker_type) if worker_type else None
                wcost = getattr(wt, "cost", None) or ()
                food = wcost[2] if len(wcost) > 2 else 0
                need = cost[2] if len(cost) > 2 else 0
                have = 0
                res = getattr(self, "resources", None) or ()
                if len(res) > 2:
                    have = res[2]
                if food and need and have - food < need:
                    return True
        if n_workers >= 8:
            trainer_food = self._owned_trainer_food_need()
            if trainer_food and worker_type:
                wt = rules.unit_class(worker_type)
                wcost = getattr(wt, "cost", None) or ()
                food = wcost[2] if len(wcost) > 2 else 0
                have = 0
                res = getattr(self, "resources", None) or ()
                if len(res) > 2:
                    have = res[2]
                if food and have - food < trainer_food:
                    return True
        if not worker_type or not self._plan_expensive_wood_reserve():
            return False
        wt = rules.unit_class(worker_type)
        wcost = getattr(wt, "cost", None) or ()
        spends_gold = bool(wcost) and wcost[0]
        spends_wood = len(wcost) > 1 and wcost[1]
        if not spends_gold and not spends_wood:
            return False
        return self._would_spend_past_plan_building(wcost)

    def _wood_gather_worker_cap(self, n_workers):
        """How many workers to put on wood. Cap of 2 is only while saving food."""
        n_w = max(1, int(n_workers or 0))
        if self._before_first_expensive_food_age():
            return 2
        if self._plan_expensive_wood_reserve(ignore_age_defer=True):
            return max(4, (n_w * 2) // 3)
        if self._need_wood_for_age_up_farms():
            return max(5, (n_w * 2) // 3)
        return max(3, n_w // 2)

    def _owned_trainer_food_need(self):
        """Food to train one still-wanted get-line soldier from an owned building."""
        return self._play_memo_get(
            ("trainer_food", getattr(self, "_line_nb", 0)),
            self._owned_trainer_food_need_compute,
        )

    def _owned_trainer_wood_need(self):
        """Wood to train one still-wanted get-line soldier from an owned building."""
        return self._play_memo_get(
            ("trainer_wood", getattr(self, "_line_nb", 0)),
            self._owned_trainer_wood_need_compute,
        )

    def _owned_trainer_food_need_compute(self):
        return self._owned_trainer_resource_need_compute(2)

    def _owned_trainer_wood_need_compute(self):
        return self._owned_trainer_resource_need_compute(1)

    def _owned_trainer_resource_need_compute(self, res_index):
        """Cost of one still-wanted get-line soldier from an owned building."""
        best = 0
        nb = getattr(self, "nb", None)
        if not callable(nb):
            return 0
        try:
            line = self._plan[self._line_nb]
        except Exception:
            return 0
        if not isinstance(line, str) or not line.startswith("get "):
            return 0
        wanted_amounts = []
        n = 1
        for token in str(line).split()[1:]:
            if re.match("^[0-9]+$", token):
                n = int(token)
                continue
            wanted = self.equivalent(token)
            if self._is_worker_type_name(wanted):
                n = 1
                continue
            uc = rules.unit_class(wanted)
            cost = getattr(uc, "cost", None) or ()
            amount = cost[res_index] if len(cost) > res_index else 0
            if amount > 0 and nb(wanted) < n:
                wanted_amounts.append((wanted, amount))
            n = 1
        if not wanted_amounts:
            return 0
        for u in getattr(self, "units", ()) or ():
            if not getattr(u, "is_a_building", False):
                continue
            trainables = set(effective_can_train(u) or ())
            if not trainables:
                continue
            for wanted, amount in wanted_amounts:
                if amount <= best:
                    continue
                match = wanted in trainables
                if not match:
                    for tn in trainables:
                        tc = rules.unit_class(tn)
                        if tc is None:
                            continue
                        if wanted == tn or wanted in getattr(
                            tc, "expanded_is_a", ()
                        ):
                            match = True
                            break
                if match:
                    best = amount
        return best

    def _plan_wants_food_from_owned_trainers(self):
        """True if an owned get-line building still needs a food-cost unit."""
        return self._owned_trainer_food_need() > 0

    def _ensure_plan_production_building(self, type_name):
        """Start a get-line maker that can be placed now (stables before castle)."""
        from .worldrequirements import requirements_satisfied

        buildable = self._worker_buildable_type_names()
        candidates = []
        for maker in rules.get_makers(type_name) or ():
            mc = rules.unit_class(maker)
            if mc is None:
                continue
            try:
                if issubclass(mc, Worker):
                    continue
            except TypeError:
                continue
            if self.nb(maker) > 0 or self.future_nb(maker) > 0:
                return True
            cost = getattr(mc, "cost", None) or ()
            if not any(c > 0 for c in cost):
                continue
            if not requirements_satisfied(self, getattr(mc, "requirements", ()) or ()):
                continue
            candidates.append(maker)
        if not candidates:
            return False
        for maker in candidates:
            if maker in buildable:
                return bool(self.get(1, maker))
        return bool(self.get(1, candidates[0]))

    def _plan_still_wants_trains_from(self, building):
        """True if the current ai.txt get line still needs units this building trains."""
        if not getattr(self, "_plan", None):
            return False
        try:
            line = self._plan[self._line_nb]
        except Exception:
            return False
        if not isinstance(line, str) or not line.startswith("get "):
            return False
        trainables = set(effective_can_train(building) or ())
        if not trainables:
            return False
        n = 1
        for token in line.split()[1:]:
            if re.match("^[0-9]+$", token):
                n = int(token)
                continue
            wanted = self.equivalent(token)
            if wanted in trainables and self.nb(wanted) < n:
                return True
            # Line-upgraded forms still count toward the semantic quota.
            wanted_cls = rules.unit_class(wanted)
            for tn in trainables:
                tc = rules.unit_class(tn)
                if tc is None or wanted_cls is None:
                    continue
                if tn == wanted or wanted in getattr(tc, "expanded_is_a", ()):
                    if self.nb(wanted) < n:
                        return True
            n = 1
        return False

    def idle_buildings_research(self):
        from .worldorders.production import AdvanceOrder, ResearchOrder

        plan_blocked_on_phase = self._saving_food_for_age()
        for u in self.units:
            if u.orders:
                continue
            # Finish get-line training before spending the building on tech,
            # unless the get line is waiting on an age we do not have yet.
            if self._plan_still_wants_trains_from(u) and not plan_blocked_on_phase:
                continue

            def _try_start(keyword, type_names, order_cls):
                names = list(type_names or ())
                if keyword == "research":
                    # Prefer unit-line unlocks; keep rules order otherwise.
                    names.sort(
                        key=lambda n: 0
                        if int(
                            getattr(self.unit_class(n), "line_upgrade", 0) or 0
                        )
                        else 1
                    )
                # Research: keep a 4x stockpile so cheap techs do not drain the
                # last resources. Age-up must fire at 1x cost (feudal is 500 food).
                stockpile = 3 if keyword == "research" else 0
                for t in names:
                    unit_type = self.unit_class(t)
                    if unit_type is None:
                        continue
                    if not order_cls.is_allowed(u, t):
                        continue
                    if (
                        not self.future_nb([t])
                        and not self.missing_resources(unit_type.cost)
                        and self.potential(unit_type.cost) > stockpile
                    ):
                        cost = getattr(unit_type, "cost", None) or ()
                        if keyword == "research" and self._spend_would_block_age_up(
                            cost
                        ):
                            continue
                        reserve = self._plan_expensive_wood_reserve(
                            ignore_age_defer=True
                        )
                        farm_w = self._age_up_farm_wood_reserve()
                        if (
                            keyword == "research"
                            and len(cost) > 1
                            and cost[1] > 0
                            and (
                                (
                                    reserve
                                    and self.resources[1] < to_int("200")
                                )
                                or (
                                    farm_w
                                    and self.resources[1] - cost[1] < farm_w
                                )
                            )
                        ):
                            continue
                        u.take_order([keyword, t])
                        return True
                return False

            if plan_blocked_on_phase:
                if _try_start(
                    "advance", getattr(u, "can_advance", ()) or (), AdvanceOrder
                ):
                    continue
                if _try_start("research", u.can_research, ResearchOrder):
                    continue
            else:
                if _try_start("research", u.can_research, ResearchOrder):
                    continue
                _try_start(
                    "advance", getattr(u, "can_advance", ()) or (), AdvanceOrder
                )

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
        return self._target_resource_index(deposit)

    def _target_resource_index(self, target):
        resource_type = getattr(target, "resource_type", None)
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

    def _resource_need_ratio(self, resource_index):
        """Lower ratio = more urgently needed relative to the low threshold."""
        return self._play_memo_get(
            ("need_ratio", resource_index),
            lambda: self._resource_need_ratio_compute(resource_index),
        )

    def _resource_need_ratio_compute(self, resource_index):
        if resource_index is None or resource_index >= len(self.resources):
            return 999.0
        have = self.resources[resource_index]
        pg, pw = self._plan_next_production_building_cost(ignore_age_defer=True)
        # Pending production wood beats nearby farms so archery is not starved
        # while a later expensive age-up is also missing food.
        if resource_index == 1 and self._keep_lumberjacks():
            if not (
                self._age_up_needs_food()
                and self._has_harvestable_food_buildings()
                and not self._need_wood_for_age_up_farms()
            ):
                return -3.0
        if resource_index == 0 and pg and have < pg:
            return -2.5
        age_missing = self._age_up_missing_resource_types()
        if resource_index == 0 and "resource1" in age_missing:
            return -2.0
        if resource_index == 2 and "resource3" in age_missing:
            return -1.0
        need = self._owned_trainer_food_need()
        if resource_index == 2 and need and have < need:
            return -1.0
        threshold = max(1, self._resource_low_threshold(resource_index))
        return have / threshold

    def _worker_can_gather_deposit(self, worker, deposit):
        allowed = getattr(worker, "can_gather_deposit", None) or []
        if "all" in allowed:
            return True
        type_name = getattr(deposit, "type_name", None)
        return type_name in allowed

    def _pick_nearest_reachable(
        self, origin, candidates, plane="ground", avoid=True, top_k=12, scan_rest=True,
        place_of=None,
    ):
        """欧氏距离预排序后，按序 A* 直到找到第一个可达目标。

        对齐 nearest_warehouse 的预筛思路：避免 AI 对全部矿点/猎物
        做 O(n) 次 shortest_path_distance_to。默认最多探测 top_k 个；
        ``scan_rest=True`` 时若都不可达再扫描剩余。采集路径应关扫描，
        因为调用方已有欧氏回退，全表 A* 在 cw1 上约 50 次/次挑选。
        ``place_of``：可选，返回寻路方格（岸边鱼用相邻陆地）。
        """
        if origin is None or not candidates:
            return None

        def _place(o):
            if place_of is not None:
                p = place_of(o)
                if p is not None:
                    return p
            return getattr(o, "place", None)

        scored = []
        ox = origin.x
        oy = origin.y
        for o in candidates:
            place = _place(o)
            if place is None:
                continue
            try:
                euclid = square_of_distance(ox, oy, place.x, place.y)
            except Exception:
                euclid = 0
            # id(o) 作最终 tie-break：两矿同距且 o.id 同为 None 时，
            # 不能让 sort 落到比较 goldmine 实例本身。
            oid = o.id
            if oid is None:
                oid = 0
            scored.append((euclid, oid, id(o), o, place))
        if not scored:
            return None
        scored.sort()
        # Same square is always reachable; _shortest_path_to(self, self) is 0
        # but skipping the call avoids cache/decorator overhead in the gather loop.
        for _, _, _, o, place in scored:
            if place is origin:
                return o
        sw = getattr(getattr(self, "world", None), "square_width", 0) or 0
        adj_limit = sw * sw if sw else 0
        adjacent = getattr(self, "_warehouse_places_adjacent", None)
        if adj_limit and callable(adjacent):
            for euclid, _, _, o, place in scored:
                if euclid > adj_limit:
                    break
                try:
                    if adjacent(origin, place):
                        return o
                except Exception:
                    continue
        limit = top_k if top_k > 0 else len(scored)
        for _, _, _, o, place in scored[:limit]:
            dist = origin.shortest_path_distance_to(
                place, self, plane, avoid=avoid
            )
            if dist is not None and dist < float("inf"):
                return o
        if scan_rest:
            for _, _, _, o, place in scored[limit:]:
                dist = origin.shortest_path_distance_to(
                    place, self, plane, avoid=avoid
                )
                if dist is not None and dist < float("inf"):
                    return o
        return None

    def _worker_origin_for_gather(self):
        origin = self._builders_place()
        if origin is None:
            for u in self._workers:
                origin = self._world_place_for_unit(u)
                if origin is not None:
                    break
        return origin

    def _reachable_deposits(
        self, from_place, resource_index=None, worker=None, first_only=False
    ):
        if from_place is None:
            return []
        candidates = []
        for o in self.perception.union(self.memory):
            if not isinstance(o, Deposit) or not self._gather_target_ok(o):
                continue
            idx = self._deposit_resource_index(o)
            if resource_index is not None and idx != resource_index:
                continue
            if worker is not None and not self._worker_can_gather_deposit(worker, o):
                continue
            place = Worker.gather_path_place_for_plane(o, "ground")
            if worker is not None:
                place = Worker.gather_stand_place(worker, o) or place
            if place is None:
                continue
            try:
                euclid = square_of_distance(
                    from_place.x, from_place.y, place.x, place.y
                )
            except Exception:
                euclid = 0
            oid = o.id
            if oid is None:
                oid = 0
            candidates.append((euclid, oid, id(o), o, place))
        candidates.sort()
        found = []
        for _, _, _, o, place in candidates:
            if place is from_place:
                dist = 0
            else:
                dist = from_place.shortest_path_distance_to(place, self, avoid=True)
            if dist is not None and dist < float("inf"):
                found.append((dist, o, "ground"))
            elif find_amphibious_crossing(from_place, place, self):
                found.append((float("inf"), o, "amphibious"))
            else:
                continue
            if first_only:
                break
        found.sort(key=lambda x: (0 if x[2] == "ground" else 1, x[0]))
        return [(o, mode) for _, o, mode in found]

    def _has_reachable_deposit(self, resource_index):
        # Existence only: stop at the first reachable deposit (AoE2 cw1 has
        # dozens of trees; a full A* pass was ~70ms per call).
        memo = getattr(self, "_play_memo", None)
        key = ("has_reach_dep", resource_index)
        if memo is not None and key in memo:
            return memo[key]
        result = bool(
            self._reachable_deposits(
                self._worker_origin_for_gather(),
                resource_index,
                first_only=True,
            )
        )
        if memo is not None:
            memo[key] = result
        return result

    def _resource_low_threshold(self, resource_index):
        # Food threshold 150 only if this ruleset has an expensive-food age-up.
        # Cheap gold/wood ages (default res) keep the generic 40 so farms do
        # not spend the barracks stash.
        return self._play_memo_get(
            ("low_thr", resource_index),
            lambda: self._resource_low_threshold_compute(resource_index),
        )

    def _resource_low_threshold_compute(self, resource_index):
        if resource_index == 2:
            if self._age_up_needs_food():
                phases = self._plan_unmet_phase_names(lookahead=True)
                if phases:
                    need = self._phase_food_cost(phases[0])
                    if need:
                        return need
            if self._ruleset_has_expensive_food_age():
                return to_int("150")
        return to_int("40")

    def _storage_type_for_resource(self, resource_index):
        names = self._storage_building_type_names(resource_index)
        if not names:
            return None
        # Prefer a dedicated store (single resource) when one exists.
        dedicated = []
        multi = []
        for name in names:
            uc = rules.unit_class(name)
            stores = getattr(uc, "storable_resource_types", ()) or ()
            if len(stores) == 1:
                dedicated.append(name)
            else:
                multi.append(name)
        return (dedicated or multi)[0]

    def _has_storage_for_resource(self, resource_index):
        """True if any building (incl. sites) can store this resource type."""
        resource_type = f"resource{resource_index + 1}"
        for u in self.units:
            if resource_type in getattr(u, "storable_resource_types", ()):
                return True
            site_type = getattr(u, "type", None)
            if site_type is not None and resource_type in getattr(
                site_type, "storable_resource_types", ()
            ):
                return True
        return False

    def _ensure_deposit_supply(self, resource_index):
        storage = self._storage_type_for_resource(resource_index)
        # Townhall already stores wood: demanding lumbermill while wood is missing
        # recurses (lumbermill costs wood → gather → ensure lumbermill → …).
        if (
            storage
            and self.nb(storage) == 0
            and self.future_nb(storage) == 0
            and not self._has_storage_for_resource(resource_index)
        ):
            sc = rules.unit_class(storage)
            cost = getattr(sc, "cost", None) or () if sc is not None else ()
            stores = (
                tuple(getattr(sc, "storable_resource_types", ()) or ())
                if sc is not None
                else ()
            )
            if not self._warehouse_spend_blocked_by_wood_reserve(cost, stores=stores):
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
        if (
            storage
            and self.nb(storage) == 0
            and self.future_nb(storage) == 0
            and not self._has_storage_for_resource(resource_index)
        ):
            sc = rules.unit_class(storage)
            cost = getattr(sc, "cost", None) or () if sc is not None else ()
            stores = (
                tuple(getattr(sc, "storable_resource_types", ()) or ())
                if sc is not None
                else ()
            )
            if not self._warehouse_spend_blocked_by_wood_reserve(cost, stores=stores):
                self.get(1, storage)
        return True

    def _resource_building_types(self, resource_type):
        """Return buildable building type names that produce the given resource."""
        result = []
        worker_name = self._primary_worker_type_name()
        peasant_class = rules.unit_class(worker_name) if worker_name else None
        buildables = (
            rules.class_rules_attr(peasant_class, "can_build", ())
            if peasant_class is not None
            else self._worker_buildable_type_names()
        )
        for name in buildables:
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
            n = max(2, workers // 4)
            # Castle is 800 food: one 175-food cycle on 4 farms is ~700 and
            # still dies if recultivate wood is spent elsewhere.
            if self._age_up_needs_food() and not self._wood_below_pending_building():
                n = max(n, max(6, workers // 2))
            return n
        if resource_index == 0:
            return max(1, workers // 8)
        return 1

    def _maintain_resource_buildings(self):
        low = []
        for i, amount in enumerate(self.resources):
            threshold = self._resource_low_threshold(i)
            if amount >= threshold:
                continue
            producers = self._resource_building_types(f"resource{i + 1}")
            if producers:
                can_run = any(
                    self._can_afford_production_cost(rules.unit_class(name))
                    or (
                        # food/cultivate often needs wood (resource2)
                        i == 2 and self._has_reachable_deposit(1)
                    )
                    for name in producers
                    if rules.unit_class(name) is not None
                )
                if not can_run:
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
                if self._would_spend_past_plan_building(
                    t.cost, ignore_age_defer=True
                ):
                    continue
                if i == 2 and self._should_defer_food_building_expansion(t.cost):
                    continue
                self.build_or_train_or_upgradeto_or_summon(t)
                return

    def _idle_resource_buildings_produce(self):
        keep_farms = self._should_keep_farms_producing()
        for u in self.units:
            if not getattr(u, "is_a_building", False):
                continue
            if getattr(u, "auto_cultivate", 0):
                prod = getattr(u, "production_cost", None)
                if prod is None:
                    prod = getattr(getattr(u, "type", None), "production_cost", None)
                steal_wood = self._would_spend_past_plan_building(
                    prod, ignore_age_defer=True
                )
                if not keep_farms or steal_wood:
                    # The engine restarts depleted farms between AI turns while
                    # current_production_mode is still "auto"; that 60 wood
                    # never lets archery reach 175.
                    if getattr(u, "current_production_mode", None) == "auto":
                        u.current_production_mode = None
                    continue
                if getattr(u, "is_producing", False) or u.orders:
                    continue
                if getattr(u, "resource_qty", 0) > 0:
                    continue
                if not self._can_afford_production_cost(u):
                    continue
                u.take_order(["start_automatic_cultivate"])
            elif getattr(u, "auto_production", 0):
                if getattr(u, "is_producing", False) or u.orders:
                    continue
                if not self._can_afford_production_cost(u):
                    continue
                u.take_order(["auto_produce"])

    def _cultivate_missing_wood(self):
        """Wood still needed to restart idle auto-cultivate buildings (farms)."""
        need = 0
        for u in getattr(self, "units", ()) or ():
            if not getattr(u, "auto_cultivate", 0):
                continue
            if getattr(u, "is_producing", False) or u.orders:
                continue
            if getattr(u, "resource_qty", 0) > 0:
                continue
            prod = getattr(u, "production_cost", None)
            if prod is None:
                prod = getattr(getattr(u, "type", None), "production_cost", None)
            prod = prod or ()
            wood = prod[1] if len(prod) > 1 else 0
            if wood > need:
                need = wood
        return need

    def _should_defer_food_building_expansion(self, spend_cost=None):
        """True if a new mill/farm would steal recultivate wood from an age-up.

        Empty farms sitting idle while the AI plants more of them never reach
        the 800-food castle click: each new farm costs the same 60 wood as
        restarting one that is already built.
        """
        spend_cost = spend_cost or ()
        sw = spend_cost[1] if len(spend_cost) > 1 else 0
        res = getattr(self, "resources", None) or ()
        wood = res[1] if len(res) > 1 else 0
        unlock_w = self._next_plan_phase_building_wood_need()
        if unlock_w and wood - sw < unlock_w:
            return True
        if not self._age_up_needs_food():
            return False
        if self._cultivate_missing_wood():
            return True
        farm_w = self._age_up_farm_wood_reserve()
        if not farm_w:
            return False
        return wood - sw < farm_w

    def _has_harvestable_food_buildings(self):
        """True if an owned farm still has food that workers can gather."""
        return self._play_memo_get(
            "harvestable_food", self._has_harvestable_food_buildings_compute
        )

    def _has_harvestable_food_buildings_compute(self):
        for u in getattr(self, "units", ()) or ():
            if not getattr(u, "auto_cultivate", 0):
                continue
            if getattr(u, "resource_qty", 0) > 0:
                return True
        return False

    def _deposit_has_resources(self, target):
        if isinstance(target, Deposit):
            return getattr(target, "qty", 0) > 0
        if hasattr(target, "resource_qty"):
            return target.resource_qty > 0
        return True

    def _wood_memory_square_worth_walking(self, deposit):
        """True if an empty remembered forest is still a useful walk target.

        After castle, chopped piles sit at qty 0. Random auto_explore then
        never returns to those squares (or to still-stocked neighbors).
        """
        if self._deposit_resource_index(deposit) != 1:
            return False
        if not (
            self._wood_below_pending_building()
            and self._later_age_startable_production_wood()
        ):
            return False
        if getattr(deposit, "qty", 0) > 0:
            return True
        return bool(
            getattr(deposit, "resource_regen", 0)
            or getattr(deposit, "qty_max", 0)
        )

    def _gather_target_ok(self, target):
        if target is None or target.place is None:
            return False
        return self._deposit_has_resources(target)

    def _known_ok_deposits(self):
        """Deposits currently worth gathering; shared across workers this play()."""
        return self._play_memo_get("ok_deposits", self._known_ok_deposits_compute)

    def _known_ok_deposits_compute(self):
        result = []
        for o in self.perception.union(self.memory):
            if isinstance(o, Deposit) and self._gather_target_ok(o):
                result.append(o)
        return result

    def _huntable_food_deposit_types(self):
        """Deposit type names produced by ``is_huntable`` animals (from rules)."""
        cached = getattr(self, "_cached_huntable_food_deposits", None)
        if cached is not None:
            return cached
        types = set()
        try:
            from soundrts.definitions import rules

            for name in rules.classnames():
                raw = rules.get(name, "is_huntable")
                if raw in (1, "1", True) or (
                    isinstance(raw, list) and raw and str(raw[0]) in ("1", "true", "True")
                ):
                    fd = rules.get(name, "food_deposit")
                    if not fd:
                        continue
                    types.add(fd[0] if isinstance(fd, list) else fd)
        except Exception:
            types = set()
        self._cached_huntable_food_deposits = frozenset(types)
        return self._cached_huntable_food_deposits

    def _worker_can_hunt(self, worker):
        skills = getattr(worker, "basic_skills", None) or getattr(
            worker, "_basic_skills", ()
        )
        if "attack" not in skills:
            return False
        deposits = getattr(worker, "can_gather_deposit", None) or []
        if not deposits:
            return False
        if "all" in deposits:
            return True
        return bool(set(deposits) & self._huntable_food_deposit_types())

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
        return self._pick_nearest_reachable(place, buildings) or buildings[0]

    def _is_livestock_unit(self, unit):
        """Owned/claimable herd animals (sheep), not wild deer/boar."""
        return bool(
            getattr(unit, "is_huntable", 0)
            and (getattr(unit, "herdable", 0) or getattr(unit, "claimable", 0))
        )

    def _livestock_food_dropoff(self):
        """Town center / mill / pasture that stores food for livestock slaughter."""
        for u in self.units:
            if not getattr(u, "is_a_building", False) or u.place is None:
                continue
            if "resource3" in getattr(u, "storable_resource_types", ()):
                return u
        return None

    def _maintain_owned_livestock(self):
        """Send owned sheep to the food drop-off; workers slaughter them there.

        AoE2 villagers often have ``can_herd 0``: claimed livestock are still
        controllable units, so the AI orders the animals themselves to ``go``.
        """
        dropoff = self._livestock_food_dropoff()
        if dropoff is None or dropoff.place is None:
            return
        dest = dropoff.place
        for animal in self.units:
            if not self._is_livestock_unit(animal):
                continue
            if getattr(animal, "hp", 0) <= 0 or animal.place is None:
                continue
            if getattr(animal, "is_inside", False):
                continue
            if animal.place is dest:
                continue
            orders = getattr(animal, "orders", None) or ()
            if orders:
                o0 = orders[0]
                kw = getattr(o0, "keyword", None)
                if kw == "go" and getattr(o0, "target", None) is dest:
                    continue
                # auto_explore is imperative and would keep sheep wandering forever.
                if kw == "auto_explore":
                    animal.take_order(["stop"])
            animal.take_order(["go", dest.id], forget_previous=True)

    def _choose_livestock_slaughter_target(self, worker):
        """Owned livestock already at the food drop-off (ready to kill)."""
        if not self._worker_can_hunt(worker):
            return None
        dropoff = self._herd_dropoff_building(worker)
        if dropoff is None or dropoff.place is None:
            dropoff = self._livestock_food_dropoff()
        if dropoff is None or dropoff.place is None:
            return None
        dest = dropoff.place
        origin = self._world_place_for_unit(worker)
        if origin is None:
            return None
        ready = [
            u
            for u in self.units
            if self._is_livestock_unit(u)
            and getattr(u, "hp", 0) > 0
            and u.place is dest
        ]
        if not ready:
            return None
        if worker.place is dest:
            return ready[0]
        return self._pick_nearest_reachable(origin, ready) or ready[0]

    def _choose_claim_livestock_target(self, worker):
        """Neutral claimable sheep: approach with ``go`` to take ownership."""
        origin = self._world_place_for_unit(worker)
        if origin is None:
            return None
        animals = [
            o
            for o in self.perception.union(self.memory)
            if getattr(o, "claimable", 0)
            and getattr(o, "hp", 0) > 0
            and o.place is not None
            and getattr(getattr(o, "player", None), "neutral", False)
        ]
        if not animals:
            return None
        safe = [a for a in animals if not self.square_is_dangerous(a.place)]
        return self._pick_nearest_reachable(origin, safe or animals)

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
            and getattr(o, "_herd_leader", None) is None
            and (
                getattr(getattr(o, "player", None), "neutral", False)
                or o.player is self
            )
        ]
        if not animals:
            return None
        if self._herd_dropoff_building(worker) is None:
            return None
        safe = [a for a in animals if not self.square_is_dangerous(a.place)]
        return self._pick_nearest_reachable(origin, safe)

    def _known_huntable_animals(self):
        """Huntable animals in perception/memory; shared across workers this play()."""

        def _compute():
            result = []
            for o in self.perception.union(self.memory):
                if not getattr(o, "is_huntable", 0):
                    continue
                if getattr(o, "hp", 0) <= 0 or o.place is None:
                    continue
                owner = getattr(o, "player", None)
                if getattr(owner, "neutral", False) or (
                    owner is self
                    and (getattr(o, "herdable", 0) or getattr(o, "claimable", 0))
                ):
                    result.append(o)
            return result

        return self._play_memo_get("huntable_animals", _compute)

    def _choose_hunt_target(self, worker):
        if not self._worker_can_hunt(worker):
            return None
        origin = self._world_place_for_unit(worker)
        if origin is None:
            return None
        can_herd = self._worker_can_herd(worker)
        dropoff = self._herd_dropoff_building(worker) or self._livestock_food_dropoff()
        drop_place = getattr(dropoff, "place", None) if dropoff is not None else None
        animals = []
        for o in self._known_huntable_animals():
            owner = getattr(o, "player", None)
            # Livestock: never kill in the field. Owned sheep walk to the TC
            # via ``_maintain_owned_livestock``; slaughter only at drop-off.
            # Neutral claimable sheep are approached with ``go`` to claim.
            if self._is_livestock_unit(o):
                if owner is self and drop_place is not None and o.place is drop_place:
                    animals.append(o)
                continue
            if (
                getattr(o, "herdable", 0)
                and can_herd
                and getattr(owner, "neutral", False)
            ):
                continue
            # Wild boar (pursue_attacker): lure to the TC instead of field-killing.
            if self._is_lureable_huntable(o):
                if drop_place is None or o.place is drop_place:
                    animals.append(o)
                continue
            animals.append(o)
        if not animals:
            return None
        # 危险格在挑选时过滤，避免先 A* 全排序再丢弃
        safe = [a for a in animals if not self.square_is_dangerous(a.place)]
        return self._pick_nearest_reachable(origin, safe or animals)

    @staticmethod
    def _rules_flag_on(value):
        if value in (1, True, "1"):
            return True
        if isinstance(value, str) and value.lower() in ("1", "true"):
            return True
        if isinstance(value, (list, tuple)) and value:
            return str(value[0]).lower() in ("1", "true")
        return False

    def _is_lureable_huntable(self, unit):
        """Wild hunt that chase the hitter (AoE2 boar), not sheep/deer."""
        if not getattr(unit, "is_huntable", 0):
            return False
        if getattr(unit, "herdable", 0) or getattr(unit, "claimable", 0):
            return False
        pursue = getattr(unit, "pursue_attacker", None)
        if pursue is None:
            pursue = getattr(type(unit), "pursue_attacker", 0)
        return self._rules_flag_on(pursue)

    def _hunt_lure_dropoff_place(self, worker):
        dropoff = self._herd_dropoff_building(worker)
        if dropoff is None:
            alt = getattr(self, "_livestock_food_dropoff", None)
            if callable(alt):
                dropoff = alt()
        return getattr(dropoff, "place", None) if dropoff is not None else None

    def _worker_order_matches(self, worker, keyword, target=None, target_id=None):
        orders = getattr(worker, "orders", None) or ()
        if not orders:
            return False
        o0 = orders[0]
        if getattr(o0, "keyword", None) != keyword:
            return False
        if target is None and target_id is None:
            return True
        tgt = getattr(o0, "target", None)
        if target is not None and tgt is target:
            return True
        tid = target_id
        if tid is None and target is not None:
            tid = getattr(target, "id", None)
        if tid is not None and (tgt == tid or getattr(tgt, "id", None) == tid):
            return True
        return False

    def _clear_boar_lure(self, worker):
        setattr(worker, "_lure_animal", None)
        setattr(worker, "_lure_run_home", False)

    def _other_lure_workers(self, worker):
        others = []
        pool = list(getattr(self, "_workers", ()) or ())
        if worker is not None and worker not in pool:
            pool.append(worker)
        for u in pool:
            if u is worker:
                continue
            animal = getattr(u, "_lure_animal", None)
            if animal is not None and getattr(animal, "hp", 0) > 0:
                others.append(u)
        return others

    def _choose_boar_lure_target(self, worker):
        if not self._worker_can_hunt(worker):
            return None
        origin = self._world_place_for_unit(worker)
        drop_place = self._hunt_lure_dropoff_place(worker)
        if origin is None or drop_place is None:
            return None
        taken_ids = {
            id(getattr(u, "_lure_animal", None))
            for u in (getattr(self, "_workers", ()) or ())
            if getattr(u, "_lure_animal", None) is not None
        }
        animals = []
        for o in self._known_huntable_animals():
            if not self._is_lureable_huntable(o):
                continue
            if o.place is drop_place:
                continue
            if id(o) in taken_ids:
                continue
            animals.append(o)
        if not animals:
            return None
        safe = [a for a in animals if not self.square_is_dangerous(a.place)]
        return self._pick_nearest_reachable(origin, safe or animals)

    def _choose_lure_kill_target(self, worker):
        """Boar already at the town center / mill: all hunters may finish it."""
        if not self._worker_can_hunt(worker):
            return None
        drop_place = self._hunt_lure_dropoff_place(worker)
        origin = self._world_place_for_unit(worker)
        if drop_place is None or origin is None:
            return None
        ready = [
            o
            for o in self._known_huntable_animals()
            if self._is_lureable_huntable(o) and o.place is drop_place
        ]
        if not ready:
            return None
        if getattr(worker, "place", None) is drop_place:
            return ready[0]
        return self._pick_nearest_reachable(origin, ready) or ready[0]

    def _try_start_boar_lure(self, worker):
        if getattr(worker, "_lure_animal", None) is not None:
            return False
        if getattr(worker, "is_inside", False):
            return False
        if self._other_lure_workers(worker):
            return False
        animal = self._choose_boar_lure_target(worker)
        if animal is None:
            return False
        worker._lure_animal = animal
        worker._lure_run_home = False
        worker.take_order(["attack", animal.id], imperative=True)
        return True

    def _maintain_boar_lure(self, worker):
        """Hit the boar once, run to the TC, then kill it when it arrives."""
        animal = getattr(worker, "_lure_animal", None)
        if animal is None:
            return False
        if getattr(animal, "hp", 0) <= 0 or getattr(animal, "place", None) is None:
            self._clear_boar_lure(worker)
            return False
        drop_place = self._hunt_lure_dropoff_place(worker)
        if drop_place is None:
            worker._lure_run_home = False
            if not self._worker_order_matches(worker, "attack", target=animal):
                worker.take_order(["attack", animal.id], imperative=True)
            return True
        if animal.place is drop_place:
            worker._lure_run_home = False
            if not self._worker_order_matches(worker, "attack", target=animal):
                worker.take_order(["attack", animal.id], imperative=True)
            return True
        hit = getattr(animal, "last_attacker", None) is worker
        if hit:
            worker._lure_run_home = True
            if getattr(worker, "place", None) is drop_place:
                if self._worker_order_matches(worker, "attack"):
                    worker.take_order(["stop"])
                return True
            if self._worker_order_matches(
                worker, "go", target=drop_place, target_id=getattr(drop_place, "id", None)
            ):
                return True
            # Imperative attack cannot be replaced by a normal go (would queue
            # behind it). stop is allowed to cancel, then walk home.
            worker.take_order(["stop"])
            worker.take_order(["go", drop_place.id], forget_previous=True)
            return True
        worker._lure_run_home = False
        if not self._worker_order_matches(worker, "attack", target=animal):
            worker.take_order(["attack", animal.id], imperative=True)
        return True

    def _ensure_boar_lure(self):
        """Keep one hunter luring a boar, even if others are already gathering."""
        workers = list(getattr(self, "_workers", ()) or ())
        if not workers:
            return
        if self._other_lure_workers(None):
            return
        idle = []
        steal = []
        for u in workers:
            if getattr(u, "is_inside", False) or not self._worker_can_hunt(u):
                continue
            if not getattr(u, "orders", None):
                idle.append(u)
                continue
            kw = getattr(u.orders[0], "keyword", None)
            if kw in ("gather", "pickup", "auto_explore"):
                steal.append(u)
        for worker in idle + steal:
            if self._try_start_boar_lure(worker):
                return

    def _gatherable_building_targets(self, worker):
        from .world_extractor import (
            extractor_can_still_yield,
            gather_target_wants_more_workers,
        )

        result = []
        for u in self.units:
            if not getattr(u, "is_a_building", False):
                continue
            if not getattr(u, "resource_type", None):
                continue
            if getattr(u, "is_an_extractor", 0):
                if not extractor_can_still_yield(u):
                    continue
                # SC gas: do not assign a 4th worker while 3 are already on it
                if not gather_target_wants_more_workers(u, worker):
                    continue
            elif getattr(u, "resource_qty", 0) <= 0:
                continue
            if u.place is None or self.square_is_dangerous(u.place):
                continue
            if not Worker._can_gather_target(worker, u):
                continue
            result.append(u)
        return result

    def _item_resource_indices(self, item):
        rewards = getattr(item, "resource_rewards", None) or ()
        indices = []
        for i, amount in enumerate(rewards):
            try:
                if int(amount) > 0:
                    indices.append(i)
            except (TypeError, ValueError):
                continue
        return indices

    def _is_resource_pickup_item(self, obj):
        """Ground loot that grants resources on pickup (e.g. gold_coin from gold_mint)."""
        if obj is None or obj.place is None:
            return False
        # Creature.resource_rewards defaults to [0, 0] (truthy) — only real loot
        # uses default_order "pickup" (Item). Without this, world scans hit every unit.
        if getattr(obj, "default_order", None) != "pickup":
            return False
        rewards = getattr(obj, "resource_rewards", None)
        if not rewards:
            return False
        for amount in rewards:
            try:
                if amount:
                    return True
            except (TypeError, ValueError):
                continue
        return False

    def _collect_resource_pickup_items(self):
        """Scan producers every turn; throttle full perception loot scan."""
        result = []
        seen = set()
        producers = []
        for u in self.units:
            if getattr(u, "production_item", None):
                producers.append(u)
        for u in producers:
            place = u.place
            if place is None:
                continue
            for o in place.objects:
                oid = id(o)
                if oid in seen:
                    continue
                if self._is_resource_pickup_item(o):
                    seen.add(oid)
                    result.append(o)
        world = getattr(self, "world", None)
        if world is None:
            return result
        # No resource producers and no prior world-loot cache → skip perception.
        if not producers and not getattr(self, "_pickup_world_scan_cache", None):
            bucket = world.time // 2000
            if getattr(self, "_pickup_world_scan_bucket", -1) == bucket:
                return result
        # World loot in perception — at most every 2s game time
        bucket = world.time // 2000
        if getattr(self, "_pickup_world_scan_bucket", -1) != bucket:
            self._pickup_world_scan_bucket = bucket
            cached = []
            for o in self.perception:
                # Cheap prefilter (Creature defaults fooled bare rewards check)
                if getattr(o, "default_order", None) != "pickup":
                    continue
                oid = id(o)
                if oid in seen:
                    continue
                if self._is_resource_pickup_item(o):
                    seen.add(oid)
                    result.append(o)
                    cached.append(o)
            self._pickup_world_scan_cache = cached
        else:
            for o in getattr(self, "_pickup_world_scan_cache", ()):
                if o.place is None:
                    continue
                oid = id(o)
                if oid in seen:
                    continue
                if self._is_resource_pickup_item(o):
                    seen.add(oid)
                    result.append(o)
        return result

    def _resource_pickup_items_cached(self):
        """Per world-time cache: pickup scans were ~9M calls / 10min bench."""
        t = getattr(getattr(self, "world", None), "time", -1)
        if getattr(self, "_pickup_cache_time", None) == t:
            return self._pickup_cache_list
        items = self._collect_resource_pickup_items()
        self._pickup_cache_time = t
        self._pickup_cache_list = items
        return items

    def _iter_resource_pickup_items(self):
        return iter(self._resource_pickup_items_cached())

    def _item_need_ratio(self, item):
        idxs = self._item_resource_indices(item)
        if not idxs:
            return 999.0
        return min(self._resource_need_ratio(i) for i in idxs)

    def _worker_can_pickup(self, worker):
        if getattr(worker, "is_inside", False):
            return False
        if not getattr(worker, "have_inventory_space", False):
            return False
        skills = getattr(worker, "basic_skills", None) or getattr(
            worker, "_basic_skills", ()
        )
        return "pickup" in skills

    def _choose_pickup_target(self, worker, resource_indices=None):
        if not self._worker_can_pickup(worker):
            return None
        origin = self._world_place_for_unit(worker)
        if origin is None:
            return None
        items = self._resource_pickup_items_cached()
        if not items:
            return None
        candidates = []
        for item in items:
            if self.square_is_dangerous(item.place):
                continue
            idxs = self._item_resource_indices(item)
            if resource_indices is not None and not any(
                i in resource_indices for i in idxs
            ):
                continue
            candidates.append(item)
        if not candidates:
            return None
        candidates.sort(
            key=lambda t: (
                self._item_need_ratio(t),
                square_of_distance(origin.x, origin.y, t.place.x, t.place.y),
            )
        )
        best = self._item_need_ratio(candidates[0])
        preferred = [
            t for t in candidates if self._item_need_ratio(t) <= best + 1e-9
        ]
        return self._pick_nearest_reachable(
            origin, preferred
        ) or self._pick_nearest_reachable(origin, candidates)

    def _maintain_resource_pickups(self, max_workers=2):
        """Send workers to pick up free resource loot (gold_mint coins, chests, …)."""
        items = self._resource_pickup_items_cached()
        if not items:
            return
        already = sum(
            1
            for u in self._workers
            if u.orders and u.orders[0].keyword == "pickup"
        )
        need = max_workers - already
        if need <= 0:
            return
        for u in self._workers:
            if need <= 0:
                break
            if u.orders and u.orders[0].keyword in ("build", "repair", "pickup"):
                continue
            target = self._choose_pickup_target(u)
            if target is None:
                continue
            if u.orders and u.orders[0].keyword in (
                "auto_explore",
                "auto_attack",
                "gather",
            ):
                u.take_order(["stop"])
            u.take_order(["pickup", target.id])
            need -= 1

    def _choose_gather_target(self, worker, resource_indices=None):
        """Pick a gather target, preferring the most needed resource type.

        When food (or another resource) is low, owned gatherable buildings such as
        farms are considered alongside deposits so peasants actually harvest them.
        """
        origin = self._world_place_for_unit(worker)
        if origin is None:
            return None
        allowed = getattr(worker, "can_gather_deposit", None) or ()
        try:
            allowed_key = tuple(allowed)
        except TypeError:
            allowed_key = ("all",)
        idx_key = tuple(resource_indices) if resource_indices is not None else None
        return self._play_memo_get(
            (
                "gather_tgt",
                getattr(origin, "id", None),
                idx_key,
                allowed_key,
                getattr(worker, "airground_type", "ground"),
            ),
            lambda: self._choose_gather_target_compute(
                worker, origin, resource_indices
            ),
        )

    def _choose_gather_target_compute(self, worker, origin, resource_indices=None):
        candidates = []
        for o in self._known_ok_deposits():
            if not self._worker_can_gather_deposit(worker, o):
                continue
            if not Worker._gather_terrain_ok_for_unit(worker, o):
                continue
            idx = self._target_resource_index(o)
            if resource_indices is not None and idx not in resource_indices:
                continue
            candidates.append(o)

        for u in self._gatherable_building_targets(worker):
            idx = self._target_resource_index(u)
            if resource_indices is not None and idx not in resource_indices:
                continue
            candidates.append(u)

        if candidates:
            candidates.sort(
                key=lambda t: (
                    self._resource_need_ratio(self._target_resource_index(t)),
                    square_of_distance(origin.x, origin.y, t.place.x, t.place.y),
                )
            )
            best_ratio = self._resource_need_ratio(
                self._target_resource_index(candidates[0])
            )
            preferred = [
                t
                for t in candidates
                if self._resource_need_ratio(self._target_resource_index(t))
                <= best_ratio + 1e-9
            ]
            avoid = True

            def _gather_place(t):
                return Worker.gather_stand_place(worker, t) or getattr(t, "place", None)

            picked = self._pick_nearest_reachable(
                origin, preferred, avoid=avoid, scan_rest=False, top_k=4,
                place_of=_gather_place,
            )
            if picked is not None:
                return picked
            if len(preferred) < len(candidates):
                picked = self._pick_nearest_reachable(
                    origin, candidates, avoid=avoid, scan_rest=False, top_k=4,
                    place_of=_gather_place,
                )
                if picked is not None:
                    return picked
            # Workshop wood after castle: do not skip the last trees because a
            # neighboring square was once flagged dangerous. Watchdog lines hide
            # workshop from ``_has_startable_plan_production_building``.
            if self._need_later_age_production_wood():
                wood_only = [
                    t
                    for t in candidates
                    if self._target_resource_index(t) == 1
                ]
                if wood_only:
                    picked = self._pick_nearest_reachable(
                        origin, wood_only, avoid=False, scan_rest=False, top_k=4,
                        place_of=_gather_place,
                    )
                    if picked is not None:
                        return picked
            # Path blocked: keep the Euclidean-nearest known deposit instead of
            # rescanning perception via choose(Deposit) (that listcomp was ~21s
            # of Computer.play on cw1 15-beginner).
            return preferred[0] if preferred else candidates[0]

        return None

    def _send_worker_toward_known_wood(self, worker):
        """Walk toward a remembered wood pile when gather targeting cannot path yet."""
        origin = self._world_place_for_unit(worker)
        dest = None
        best = None
        same_square = None
        for o in self.perception.union(getattr(self, "memory", ()) or ()):
            if not isinstance(o, Deposit):
                continue
            if self._deposit_resource_index(o) != 1:
                continue
            gatherable = self._gather_target_ok(o)
            if not gatherable and not self._wood_memory_square_worth_walking(o):
                continue
            place = getattr(o, "place", None)
            if place is None or getattr(place, "id", None) is None:
                continue
            if origin is not None and (
                place is origin
                or getattr(place, "id", None) == getattr(origin, "id", None)
            ):
                if same_square is None and (
                    gatherable or self._wood_memory_square_worth_walking(o)
                ):
                    same_square = o
                continue
            try:
                if (
                    not self._need_later_age_production_wood()
                    and self.square_is_dangerous(place)
                ):
                    continue
            except Exception:
                pass
            if origin is not None:
                try:
                    dist = square_of_distance(origin.x, origin.y, place.x, place.y)
                except Exception:
                    dist = 0
            else:
                dist = 0
            if best is None or dist < best:
                best = dist
                dest = place
        # Chop the square we already stand on (including qty-0 regen after
        # castle) before walking to another remembered forest.
        if same_square is not None and (
            dest is None or self._gather_target_ok(same_square)
        ):
            orders = getattr(worker, "orders", None) or ()
            kw = getattr(orders[0], "keyword", None) if orders else None
            tgt = getattr(orders[0], "target", None) if orders else None
            if kw == "gather" and (
                tgt is same_square
                or getattr(tgt, "id", None) == getattr(same_square, "id", None)
            ):
                return True
            if kw in ("auto_explore", "auto_attack", "go", "gather"):
                worker.take_order(["stop"])
            worker.take_order(["gather", same_square.id])
            return True
        if dest is None:
            # Local piles are gone; scout instead of bouncing on one neighbor.
            return self._send_worker_to_scout_for_wood(worker)
        orders = getattr(worker, "orders", None) or ()
        if orders and getattr(orders[0], "keyword", None) == "go":
            tgt = getattr(orders[0], "target", None)
            if tgt is dest or getattr(tgt, "id", None) == dest.id:
                return True
        if orders and getattr(orders[0], "keyword", None) in (
            "auto_explore",
            "auto_attack",
            "gather",
        ):
            worker.take_order(["stop"])
        worker.take_order(["go", dest.id])
        return True

    def _count_wood_scouts(self):
        n = 0
        for u in getattr(self, "_workers", ()) or ():
            orders = getattr(u, "orders", None) or ()
            if orders and getattr(orders[0], "keyword", None) == "auto_explore":
                n += 1
        return n

    def _wood_scout_worker_cap(self):
        """How many villagers may explore for wood.

        Cap of 2 while a later expensive age is still unpaid or researching:
        sending the town walking empties farms and walks into fights. After
        that age, workshop wood (including watchdog lines that hide the
        building from the current get) may take the lumberjack cap.
        """
        if not self._need_later_age_production_wood():
            return 2
        n_w = max(1, len(getattr(self, "_workers", ()) or ()))
        return self._wood_gather_worker_cap(n_w)

    def _send_worker_to_scout_for_wood(self, worker):
        """Explore when remembered wood piles are empty so recultivate can restart."""
        orders = getattr(worker, "orders", None) or ()
        kw = getattr(orders[0], "keyword", None) if orders else None
        if kw == "auto_explore":
            return True
        if kw in ("build", "repair"):
            return False
        # Keep lumberjacks and walks toward known piles. Farm/gold gatherers
        # may scout only after a later age unlocks a production building
        # (workshop). Doing this in feudal empties farms and walks into fights.
        if kw == "gather":
            tgt = getattr(orders[0], "target", None)
            if self._target_resource_index(tgt) == 1:
                return False
            if not self._later_age_startable_production_wood():
                return False
        elif kw in ("go", "pickup"):
            return False
        if self._count_wood_scouts() >= self._wood_scout_worker_cap():
            return False
        if kw in ("auto_attack", "gather"):
            worker.take_order(["stop"])
        worker.take_order(["auto_explore"])
        return True

    def _send_worker_to_adjacent_square(self, worker):
        """Walk a peasant into a neighboring square so off-spawn woods enter LOS."""
        origin = self._world_place_for_unit(worker)
        if origin is None:
            return False
        neighbors = [
            n
            for n in (getattr(origin, "neighbors", ()) or ())
            if n is not None and getattr(n, "id", None) is not None
        ]
        if not neighbors:
            return False
        orders = getattr(worker, "orders", None) or ()
        kw = getattr(orders[0], "keyword", None) if orders else None
        if kw == "go":
            return True
        if kw == "auto_explore" and not self._need_later_age_production_wood():
            return True
        dest = neighbors[0]
        if orders and getattr(orders[0], "keyword", None) in (
            "auto_explore",
            "auto_attack",
            "gather",
        ):
            worker.take_order(["stop"])
        worker.take_order(["go", dest.id])
        return True

    def _send_workers_toward_resources(self, resource_indices, max_workers=None):
        """Reassign a few workers to gather specifically needed resources (e.g. farm food)."""
        if not resource_indices:
            return
        n_w = max(1, len(getattr(self, "_workers", ()) or ()))
        for resource_index in resource_indices:
            cap = max_workers
            if cap is None:
                if resource_index == 1:
                    cap = self._wood_gather_worker_cap(n_w)
                elif (
                    resource_index == 2
                    and self._age_up_needs_food()
                    and not self._keep_lumberjacks()
                ):
                    cap = max(2, n_w // 2)
                elif (
                    resource_index == 0
                    and "resource1" in self._age_up_missing_resource_types()
                    and not self._keep_lumberjacks()
                ):
                    cap = max(2, n_w // 3)
                else:
                    cap = 2
            sent = 0
            for u in self._workers:
                if sent >= cap:
                    break
                if getattr(u, "is_inside", False):
                    continue
                if u.orders and u.orders[0].keyword in ("build", "repair"):
                    continue
                if u.orders and u.orders[0].keyword == "pickup":
                    current = u.orders[0].target
                    if resource_index in self._item_resource_indices(current):
                        sent += 1
                        continue
                if u.orders and u.orders[0].keyword == "gather":
                    current = u.orders[0].target
                    if self._target_resource_index(current) == resource_index:
                        sent += 1
                        continue
                    # Keep lumberjacks on wood while a production building is unpaid.
                    if (
                        resource_index != 1
                        and self._target_resource_index(current) == 1
                        and self._keep_lumberjacks()
                    ):
                        continue
                    # Keep miners on gold while a later expensive age still needs it.
                    if (
                        resource_index == 2
                        and self._target_resource_index(current) == 0
                        and "resource1" in self._age_up_missing_resource_types()
                    ):
                        continue
                # gold_mint coins etc. before mines when that resource is missing
                pickup = self._choose_pickup_target(
                    u, resource_indices=[resource_index]
                )
                if pickup is not None:
                    if u.orders and u.orders[0].keyword in (
                        "auto_explore",
                        "auto_attack",
                        "gather",
                    ):
                        u.take_order(["stop"])
                    u.take_order(["pickup", pickup.id])
                    sent += 1
                    continue
                target = self._choose_gather_target(
                    u, resource_indices=[resource_index]
                )
                if target is None:
                    if resource_index == 1 and self._send_worker_toward_known_wood(u):
                        kw = (
                            getattr(u.orders[0], "keyword", None) if u.orders else None
                        )
                        # auto_explore is not gathering; counting it filled the
                        # lumberjack cap and left miners on gold/stone.
                        if kw in ("gather", "go"):
                            sent += 1
                    continue
                if u.orders and u.orders[0].keyword in (
                    "auto_explore",
                    "auto_attack",
                    "gather",
                ):
                    u.take_order(["stop"])
                if self._try_send_worker_to_gather_amphibious(u, target):
                    sent += 1
                    continue
                u.take_order(["gather", target.id])
                try:
                    self._gathered_deposits[target] += 1
                except Exception:
                    self._gathered_deposits[target] = 1
                sent += 1

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
        buildings = self._gatherable_building_targets(worker)
        candidates = deposits + buildings
        if candidates:
            deposit = self._pick_nearest_reachable(
                origin, candidates, plane=plane, avoid=True, scan_rest=False, top_k=4
            )
            if deposit is not None:
                return deposit
            return min(
                candidates,
                key=lambda o: square_of_distance(
                    origin.x, origin.y, o.place.x, o.place.y
                ),
            )
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

    def _count_gatherers_for_resource(self, resource_index):
        n = 0
        for u in getattr(self, "_workers", ()) or ():
            orders = getattr(u, "orders", None) or ()
            if not orders:
                continue
            kw = getattr(orders[0], "keyword", None)
            tgt = getattr(orders[0], "target", None)
            if kw == "gather":
                if self._target_resource_index(tgt) == resource_index:
                    n += 1
            elif kw == "pickup":
                indices = self._item_resource_indices(tgt) or ()
                if resource_index in indices:
                    n += 1
        return n

    def _idle_workers_gather(self):
        n_w = max(1, len(getattr(self, "_workers", ()) or ()))
        wood_cap = self._wood_gather_worker_cap(n_w)
        self._ensure_boar_lure()
        for u in self._workers:
            if getattr(u, "_lure_animal", None) is not None:
                self._maintain_boar_lure(u)
                continue
            if u.orders:
                if (
                    self._keep_lumberjacks()
                    and getattr(u.orders[0], "keyword", None) == "auto_explore"
                ):
                    wood_t = self._choose_gather_target(u, resource_indices=[1])
                    if wood_t is not None:
                        u.take_order(["stop"])
                        u.take_order(["gather", wood_t.id])
                        try:
                            self._gathered_deposits[wood_t] += 1
                        except Exception:
                            self._gathered_deposits[wood_t] = 1
                    elif self._send_worker_toward_known_wood(u):
                        pass
                continue
            if getattr(u, "is_inside", False):
                continue
            if self._maintain_worker_herding(u):
                continue
            # Owned sheep already at the TC/mill: slaughter before farms.
            livestock = self._choose_livestock_slaughter_target(u)
            if livestock is not None:
                u.take_order(["attack", livestock.id], imperative=True)
                continue
            lure_kill = self._choose_lure_kill_target(u)
            if lure_kill is not None:
                u.take_order(["attack", lure_kill.id], imperative=True)
                continue
            if self._try_start_boar_lure(u):
                continue
            # Prefer free loot (gold_mint coins) over mining when available
            pickup = self._choose_pickup_target(u)
            if pickup:
                u.take_order(["pickup", pickup.id])
                continue
            target = self._choose_gather_target(u)
            if target:
                idx = self._target_resource_index(target)
                on_wood = self._count_gatherers_for_resource(1)
                if idx == 1 and on_wood >= wood_cap:
                    others = [
                        i
                        for i in range(len(getattr(self, "resources", ()) or ()))
                        if i != 1
                    ]
                    alt = self._choose_gather_target(u, resource_indices=others)
                    if alt is not None:
                        target = alt
                elif (
                    idx != 1
                    and on_wood < wood_cap
                    and self._keep_lumberjacks()
                    and not (
                        idx == 2
                        and self._age_up_needs_food()
                        and self._has_harvestable_food_buildings()
                        and not self._need_wood_for_age_up_farms()
                    )
                ):
                    wood_t = self._choose_gather_target(u, resource_indices=[1])
                    if wood_t is not None:
                        target = wood_t
                    elif self._send_worker_toward_known_wood(u):
                        continue
                if self._try_send_worker_to_gather_amphibious(u, target):
                    continue
                u.take_order(["gather", target.id])
                try:
                    self._gathered_deposits[target] += 1
                except:
                    self._gathered_deposits[target] = 1
                continue
            if self._keep_lumberjacks() and self._send_worker_toward_known_wood(u):
                continue
            claim_target = self._choose_claim_livestock_target(u)
            if claim_target is not None:
                u.take_order(["go", claim_target.id])
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
        heal_place = None
        for base_name in self._main_base_type_names():
            for u in self.units:
                if getattr(u, "type_name", None) == base_name:
                    heal_place = getattr(u, "place", None)
                    break
            if heal_place is not None:
                break
        if heal_place is None:
            for u in self.units:
                if getattr(u, "heal_level", 0):
                    heal_place = getattr(u, "place", None)
                    if heal_place is not None:
                        break
        if heal_place is not None:
            wounded = [
                u
                for u in self._idle_fighters
                if u.hp < u.hp_max and u.place is not heal_place
            ]
            if wounded:
                self._send_units(wounded, heal_place)

        # build static defenses (any is_a_gate building workers can build)
        # Beginner/timers: never auto-wall — repeated failed gate builds spam
        # ``cannot_build_here`` (orders queued behind auto_explore, or many
        # workers targeting the same exit).
        if self.AI_type in ("beginner", "timers", "easy"):
            return
        gate_names = self._gate_type_names()
        if self._sensible_building is not None and gate_names:
            gate_name = self._prefer_gate_type_name(gate_names)
            gate = rules.unit_class(gate_name)

            def nearest_exit(u):
                place = getattr(u, "place", None)
                if place is None:
                    return None
                result = sorted(
                    place.exits,
                    key=lambda e: square_of_distance(u.x, u.y, e.x, e.y),
                )
                if result:
                    return result[0]

            e = nearest_exit(self._sensible_building)
            if (
                e is not None
                and not e.is_blocked()
                and gate is not None
                and self.get_object_by_id(e.id) is e
                and not self._gate_build_already_pending(gate_name, e)
                and self.future_nb(gate_name) <= self.nb(gate_name)
                and self.gather(gate.cost, 0)
                and any(worker_can_build(w, gate_name) for w in self._workers)
            ):
                # requisition=True stops auto_explore so the build reaches queue head
                worker_name = self._primary_worker_type_name()
                if worker_name:
                    self.order(
                        1,
                        worker_name,
                        ["build", gate_name, e.id],
                        near=e,
                        requisition=True,
                    )

    def _prefer_gate_type_name(self, gate_names):
        """Prefer cheap dark-age palisade gates over stone gates when both exist."""
        names = list(gate_names or ())
        for preferred in ("palisade_gate", "gate"):
            if preferred in names:
                return preferred
        return names[0]

    def _gate_build_already_pending(self, gate_name, exit_obj):
        """True if a worker already has a gate build (any queue slot) for this exit."""
        exit_id = getattr(exit_obj, "id", None)
        for u in self._workers:
            for o in getattr(u, "orders", ()) or ():
                if getattr(o, "keyword", None) != "build":
                    continue
                t = getattr(o, "type", None)
                tn = getattr(t, "__name__", None) or getattr(t, "type_name", None)
                if tn != gate_name:
                    continue
                target = getattr(o, "target", None)
                if target is exit_obj:
                    return True
                args = getattr(o, "args", None) or ()
                if exit_id is not None and exit_id in args:
                    return True
        return False

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

    def _try_maintain_fishing(self):
        """If a dock exists, keep a few water gatherers (rules-driven, not type-hardcoded)."""
        yards = self._naval_yard_type_names()
        if not yards:
            return
        if self.nb(yards[0]) == 0:
            return
        names = self._water_worker_type_names()
        if not names:
            return
        name = names[0]
        want = 3 if self.AI_type in ("nightmare", "expert") else 2
        if self.nb(name) < want and self.future_nb(name) < want:
            self.get(want, name)

    def _try_maintain_naval(self):
        """On water maps, keep a dock and a small navy for crossing / river fights."""
        if not self._map_has_water():
            return
        yards = self._naval_yard_type_names()
        if not yards:
            return
        shipyard = yards[0]
        if self.nb(shipyard) == 0:
            # Requirements (e.g. lumbermill) are pulled by get()/_get_requirements.
            if self.future_nb(shipyard) == 0:
                self.get(1, shipyard)
            return
        # Dock first (including beginner/timers) so Dark Age fishing can start.
        self._try_maintain_fishing()
        if self.AI_type in ("beginner", "timers"):
            return
        boats = self._water_transport_type_names()
        if boats:
            boat = boats[0]
            if self.nb(boat) < 2 and self.future_nb(boat) < 2:
                self.get(2, boat)
                return
        warships = self._water_warship_type_names()
        dd_target = self._naval_destroyer_target()
        if warships and dd_target:
            destroyer = warships[0]
            if self.nb(destroyer) < dd_target and self.future_nb(destroyer) < dd_target:
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

    def _enemy_land_assault_targets(self):
        return [
            p
            for p in self._naval_patrol_targets()
            if p is not None and not getattr(p, "is_water", False)
        ]

    def _choose_unload_land_for_transport(self, transport, dest_places):
        """Pick a passable land square to unload onto near the transport / enemy."""
        place = getattr(transport, "place", None)
        if place is None:
            return None
        ag = getattr(transport, "airground_type", None)
        adjacent = []
        if ag == "water":
            for n in place.strict_neighbors:
                if is_passable_land(n):
                    adjacent.append(n)
        elif ag == "air":
            if is_passable_land(place):
                adjacent.append(place)
            for n in place.strict_neighbors:
                if is_passable_land(n):
                    adjacent.append(n)
        if not adjacent:
            return None

        def _score(land):
            best = None
            for dest in dest_places or ():
                dest = self._world_place_for_pathfinding(dest)
                if dest is None:
                    continue
                dist = land.shortest_path_distance_to(dest, self, "ground")
                if dist is None or dist == float("inf"):
                    continue
                if best is None or dist < best:
                    best = dist
            if best is None:
                return (1, 0 if is_land_shore(land) else 1)
            return (0, best)

        return min(adjacent, key=_score)

    def _try_unload_idle_loaded_transports(self):
        """Unload boats/air transports that already carry troops but sit idle.

        `_try_transport_assaults` only sees idle ground soldiers outside a
        transport. After load+sail (or a failed unload), a packed boat can
        park next to an enemy shore forever unless we re-issue unload_all.
        """
        targets = self._enemy_land_assault_targets()
        for transport in self.units:
            if getattr(transport, "transport_capacity", 0) <= 0:
                continue
            if transport.speed <= 0 or getattr(transport, "is_inside", False):
                continue
            inside = getattr(transport, "inside", None)
            if inside is None or not inside.objects:
                continue
            if not any(
                getattr(o, "airground_type", None) == "ground" for o in inside.objects
            ):
                continue
            if transport.orders:
                keywords = {o.keyword for o in transport.orders}
                if keywords & {"load", "load_all", "unload", "unload_all"}:
                    continue
                if not self._is_idle_for_ai_orders(transport):
                    continue
            unload_land = self._choose_unload_land_for_transport(transport, targets)
            ag = getattr(transport, "airground_type", None)
            if unload_land is not None:
                transport.cancel_all_orders()
                if ag == "water":
                    transport.take_order(
                        ["unload_all", unload_land.id], forget_previous=True
                    )
                else:
                    transport.take_order(
                        ["go", unload_land.id], forget_previous=False
                    )
                    transport.take_order(
                        ["unload_all", unload_land.id], forget_previous=False
                    )
                continue
            if ag != "water" or not targets:
                continue
            # Not adjacent to land yet: sail to a shore next to the enemy, then unload.
            dest = self._world_place_for_pathfinding(targets[0])
            if dest is None:
                continue
            origin = self._world_place_for_unit(transport)
            route = find_amphibious_crossing(origin, dest, self) if origin else None
            if route is None:
                # Fall back: nearest water neighbor of any shore near dest.
                shores = []
                if is_land_shore(dest):
                    shores.append(dest)
                for n in dest.neighbors:
                    if is_land_shore(n) and n not in shores:
                        shores.append(n)
                best_water = None
                best_land = None
                best_dist = None
                for shore in shores:
                    for water in water_neighbors_of_land(shore):
                        dist = self._water_path_distance(transport.place, water)
                        if best_dist is None or dist < best_dist:
                            best_dist = dist
                            best_water = water
                            best_land = shore
                if best_water is None or best_land is None:
                    continue
                unload_water, unload_land = best_water, best_land
            else:
                _load_land, _load_water, unload_water, unload_land = route
            transport.cancel_all_orders()
            transport.take_order(["go", unload_water.id], forget_previous=False)
            transport.take_order(
                ["unload_all", unload_land.id], forget_previous=False
            )

    def _try_transport_assaults(self):
        """Ferry blocked ground troops by boat or air transport toward enemy bases."""
        # Cheap gate: pathfinding below is expensive; skip when no transport exists.
        if not self._available_water_transports() and not self._available_air_transports():
            return
        targets = self._enemy_land_assault_targets()
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
        self._try_unload_idle_loaded_transports()
        self._try_transport_assaults()

    def play(self):
        if self.AI_type == "timers":
            return
        if not self._should_play_this_turn():
            return
        self._play_memo = {}
        try:
            self._play_body()
        finally:
            self._play_memo = None

    def _play_body(self):
        # print self.number, "plays turn", self.world.turn
        self._update_effect_users_and_workers()
        self._update_time_has_come()
        self._send_workers_to_forgotten_building_sites()
        maintain_terran_recombine(self)
        self._maintain_resource_buildings()
        self._idle_resource_buildings_produce()
        self._maintain_owned_livestock()
        self._idle_workers_gather()
        self._maintain_resource_pickups()
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
        # Click the plan age-up before line-upgrade research spends its food/gold.
        # Bank age cost even while any_buildings (blacksmith, …) is still unpaid —
        # otherwise gather() never runs and villagers stay on wood/gold.
        self._click_plan_phase_if_ready()
        if self.research:
            self.idle_buildings_research()
        self._raise_dead()
        stash = self._plan_expensive_wood_reserve(ignore_age_defer=True)
        wood_now = self.resources[1] if len(self.resources) > 1 else 0
        hold_stash = bool(stash) and wood_now >= stash
        # If wood already covers the next barracks/range/stable, place it this
        # turn before a mill or house spends the stash.
        if not hold_stash:
            self._build_a_warehouse_if_useful()
        self._maintain_expansions()
        if not hold_stash:
            self._ensure_housing(min_headroom=0)
        # Age-up before training more workers so 500 food is not spent on villagers.
        # With a working eco, follow the get-line (barracks/range/stable) before
        # flooding extra villagers onto the town center.
        self._click_plan_phase_if_ready()
        worker_type = self._primary_worker_type_name()
        n_workers = len(getattr(self, "_workers", ()) or ())
        hold_workers = self._should_hold_extra_workers(n_workers, worker_type)

        def _maybe_workers():
            if worker_type and not hold_workers:
                self.get(self.nb_workers_to_get, worker_type)

        if n_workers < 6:
            _maybe_workers()
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
                self._line_nb += 1
        else:
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
                self._line_nb += 1
            _maybe_workers()
        if hold_stash:
            self._build_a_warehouse_if_useful()
            self._ensure_housing(min_headroom=0)
        reserve = self._plan_expensive_wood_reserve(ignore_age_defer=True)
        farm_w = self._age_up_farm_wood_reserve()
        if reserve and self.resources[1] < to_int("200"):
            self._send_workers_toward_resources([1])
        elif farm_w and self.resources[1] < farm_w:
            self._send_workers_toward_resources([1])

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
                and not self._is_livestock_unit(u)
            ],
            key=value_as_an_explorer,
            reverse=True,
        )

    def _send_explorer(self):
        candidates = self.best_explorers()
        if not candidates:
            return
        best_explorer = candidates[0]
        keep_wood_scouts = bool(
            self._wood_below_pending_building()
            and self._later_age_startable_production_wood()
        )
        workers = getattr(self, "_workers", ()) or ()
        explorers = [
            u
            for u in self.units
            if u.orders
            and u.orders[0].keyword == "auto_explore"
            and not (keep_wood_scouts and u in workers)
        ]

        def _recall(u):
            # auto_explore is imperative: plain take_order(["go", ...]) only queues
            # behind it (1.4 take_order change). Must stop first, else explorers pile
            # up and constant_attacks never gets idle fighters (jl1 vs 1.3.8.1).
            if u.orders and u.orders[0].keyword == "auto_explore":
                u.take_order(["stop"])
            if self.units:
                u.take_order(["go", self.units[0].place.id])

        if (
            best_explorer.orders
            and best_explorer.orders[0].keyword == "auto_explore"
        ):
            for u in explorers:
                if u is not best_explorer:
                    _recall(u)
            return

        current = explorers[0] if explorers else None
        if current is not None:
            if (
                value_as_an_explorer(current)[0]
                == value_as_an_explorer(best_explorer)[0]
            ):
                for u in explorers[1:]:
                    _recall(u)
                return
            for u in explorers:
                _recall(u)
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

    def _invalidate_play_derived_counts(self):
        """Drop production/plan memo after a train/build/research order this turn."""
        memo = getattr(self, "_play_memo", None)
        if not memo:
            return
        memo.pop("_nb_prod_name_counts", None)
        memo.pop("_nb_prod_class_counts", None)
        for key in list(memo):
            if isinstance(key, tuple) and key and key[0] in _PLAY_PROD_MEMO_PREFIXES:
                del memo[key]

    def _add_type_name_counts(self, counts, obj):
        names = set()
        tn = getattr(obj, "type_name", None)
        if tn:
            names.add(tn)
        expanded = getattr(obj, "expanded_is_a", None)
        if expanded:
            names.update(expanded)
        for name in names:
            counts[name] = counts.get(name, 0) + 1

    def _ensure_nb_name_counts(self):
        memo = getattr(self, "_play_memo", None)
        if memo is None:
            return None
        counts = memo.get("_nb_name_counts")
        if counts is not None:
            return counts
        counts = {}
        for u in self.units:
            self._add_type_name_counts(counts, u)
        memo["_nb_name_counts"] = counts
        return counts

    def _ensure_nb_prod_name_counts(self):
        memo = getattr(self, "_play_memo", None)
        if memo is None:
            return None
        counts = memo.get("_nb_prod_name_counts")
        if counts is not None:
            return counts
        counts = {}
        for u in self.units:
            if isinstance(u, BuildingSite):
                self._add_type_name_counts(counts, u.type)
                continue
            if not u.orders:
                continue
            o = u.orders[0]
            if getattr(o, "is_deferred", False):
                continue
            if o.keyword in _PROD_ORDER_KEYWORDS:
                self._add_type_name_counts(counts, o.type)
        memo["_nb_prod_name_counts"] = counts
        return counts

    def _nb_class_count(self, cls, production=False):
        memo = getattr(self, "_play_memo", None)
        cache_key = "_nb_prod_class_counts" if production else "_nb_class_counts"
        cache = None if memo is None else memo.get(cache_key)
        if cache is not None and cls in cache:
            return cache[cls]
        n = 0
        if production:
            for u in self.units:
                if isinstance(u, BuildingSite) and isinstance(u.type, cls):
                    n += 1
                    continue
                if not u.orders:
                    continue
                o = u.orders[0]
                if getattr(o, "is_deferred", False):
                    continue
                if o.keyword in _PROD_ORDER_KEYWORDS and isinstance(o.type, cls):
                    n += 1
        else:
            for u in self.units:
                if isinstance(u, cls):
                    n += 1
        if memo is not None:
            if cache is None:
                cache = {}
                memo[cache_key] = cache
            cache[cls] = n
        return n

    def _nb_scan(self, types, production=False):
        n = 0
        if production:
            for u in self.units:
                if isinstance(u, BuildingSite) and self.check_type(u.type, types):
                    n += 1
                    continue
                if not u.orders:
                    continue
                o = u.orders[0]
                if getattr(o, "is_deferred", False):
                    continue
                if o.keyword in _PROD_ORDER_KEYWORDS and self.check_type(
                    o.type, types
                ):
                    n += 1
        else:
            for u in self.units:
                if self.check_type(u, types):
                    n += 1
        return n

    def _nb_lookup(self, types, production=False):
        if (
            types
            and isinstance(types, list)
            and isinstance(types[0], str)
            and types[0] in (getattr(self, "upgrades", None) or ())
        ):
            return 0 if production else 1
        if isinstance(types, list) and len(types) == 1:
            return self._nb_lookup(types[0], production=production)
        if isinstance(types, str):
            counts = (
                self._ensure_nb_prod_name_counts()
                if production
                else self._ensure_nb_name_counts()
            )
            if counts is not None:
                return counts.get(types, 0)
        elif isinstance(types, type):
            return self._nb_class_count(cls=types, production=production)
        else:
            tn = getattr(types, "type_name", None)
            if isinstance(tn, str) and not isinstance(types, type):
                counts = (
                    self._ensure_nb_prod_name_counts()
                    if production
                    else self._ensure_nb_name_counts()
                )
                if counts is not None:
                    return counts.get(tn, 0)
        memo = getattr(self, "_play_memo", None)
        if memo is not None:
            try:
                key_types = tuple(types) if isinstance(types, list) else types
                key = ("nbprod" if production else "nbscan", key_types)
                if key in memo:
                    return memo[key]
            except TypeError:
                key = None
            n = self._nb_scan(types, production=production)
            if key is not None:
                memo[key] = n
            return n
        return self._nb_scan(types, production=production)

    def nb(self, types):
        return self._nb_lookup(types, production=False)

    def _nb_in_production(self, types):
        # 只统计正在执行（队首）的生产命令。auto_explore / auto_attack 是
        # imperative，普通 build 会被 take_order 排到后面且永远到不了队首；
        # 若把这些卡住的 build 算进 future_nb，AI 会以为兵营已在造而不再下单。
        return self._nb_lookup(types, production=True)

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
            # auto_explore / auto_attack 是 imperative：普通 take_order 只能排队
            # 到它们后面，建造永远不会开始。征用工人或升级时先停掉探索。
            if (
                u.orders
                and u.orders[0].keyword in ("auto_explore", "auto_attack")
                and (
                    requisition
                    or order[0] in ("upgrade_to", "build", "repair", "gather")
                )
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
                        # fishing_ship is a Worker with can_repair, but land
                        # scaffolds must not pull boats off deep_fish / shore_fish.
                        if getattr(u, "airground_type", "ground") == "water":
                            tgt_place = getattr(target, "place", None)
                            if getattr(target, "airground_type", None) != "water" and not getattr(
                                tgt_place, "is_water", False
                            ):
                                continue
                order_cls = ORDERS_DICT.get(order[0])
                if order_cls is not None and not order_cls.is_allowed(u, *order[1:]):
                    continue
                # Water gatherers are not counted in _gathered_deposits (only
                # ground peasants are). Decrement only when the worker actually
                # takes the new order, and only if the deposit was tracked.
                if requisition and u.orders and u.orders[0].keyword == "gather":
                    try:
                        self._gathered_deposits[u.orders[0].target] -= 1
                    except Exception:
                        pass
                u.take_order(order)
                if order and order[0] in _PROD_ORDER_KEYWORDS:
                    self._invalidate_play_derived_counts()
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
        cached = getattr(self, "_map_has_water_cached", None)
        if cached is not None:
            return cached
        # Prefer water_squares even when empty (land-only maps); avoid rescanning squares.
        water_squares = getattr(self.world, "water_squares", None)
        if water_squares is not None:
            result = len(water_squares) > 0
        else:
            result = any(
                getattr(sq, "is_water", False)
                for sq in getattr(self.world, "squares", ())
            )
        self._map_has_water_cached = result
        return result

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
        if getattr(cls, "is_buildable_on_water_only", False):
            return True
        return False

    def get(self, nb, type):
        if not self._map_has_water() and self._type_needs_water(type):
            return True
        type_name = type if isinstance(type, str) else getattr(type, "__name__", None)
        if type_name is None:
            return False
        getting = getattr(self, "_getting", None)
        if getting is None:
            getting = set()
            self._getting = getting
        # Re-entrancy guard: gather→ensure storage→get(same) must not recurse.
        if type_name in getting:
            return False
        getting.add(type_name)
        try:
            self._safe_cnt = 0
            return self._get(nb, [type])
        finally:
            getting.discard(type_name)

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
        for wanted in types:
            if isinstance(wanted, str):
                unit_class = rules.unit_class(wanted)
                if unit_class is None:
                    warning("无效的单位类型: %s", wanted)
                    continue
                wanted = unit_class
            elif wanted is None:
                continue
            elif not hasattr(wanted, "__name__"):
                warning("无效的单位类型: %s", wanted)
                continue

            # 获取制造者类型列表
            makers = rules.get_makers(wanted)
            if not makers:
                # Civ equivalents (e.g. frank_barracks, chinese_villager) may have
                # no direct makers; fall back to an is_a ancestor that does.
                for parent in getattr(wanted, "expanded_is_a", ()) or ():
                    if parent == getattr(wanted, "__name__", None):
                        continue
                    if rules.get_makers(parent):
                        return self._get(nb, parent)
                continue

            # Prefer makers we already own, then makers that are themselves
            # obtainable. Collapse civ building shells (portuguese_barracks,
            # vietnamese_archery, …) to a semantic name workers can produce so
            # get(militia) does not recurse through every civ shell and burn
            # safe_cnt with "trouble getting".
            ordered = []
            seen = set()

            def _push(name):
                if name and name not in seen:
                    seen.add(name)
                    ordered.append(name)

            def _obtainable_maker(name):
                if not name:
                    return name
                if self.nb(name) > 0:
                    return name
                get_direct = getattr(rules, "get_direct_makers", None)
                if callable(get_direct) and get_direct(name):
                    return name
                race_sources = getattr(rules, "_race_equivalent_sources", None)
                if callable(race_sources):
                    for semantic in race_sources(name):
                        if self.nb(semantic) > 0:
                            return semantic
                        if callable(get_direct) and get_direct(semantic):
                            return semantic
                        if rules.get_makers(semantic):
                            return semantic
                mc = rules.unit_class(name)
                for parent in getattr(mc, "expanded_is_a", ()) or ():
                    if parent == name:
                        continue
                    if self.nb(parent) > 0 or rules.get_makers(parent):
                        return parent
                return name

            for m in makers:
                if self.nb(m) > 0:
                    _push(_obtainable_maker(m))
            for m in makers:
                if self.nb(m) > 0:
                    continue
                m2 = _obtainable_maker(m)
                if self.nb(m2) > 0:
                    _push(m2)
                    continue
                if rules.get_makers(m2):
                    _push(m2)
                    continue
                mc = rules.unit_class(m2)
                for parent in getattr(mc, "expanded_is_a", ()) or ():
                    if parent == m2:
                        continue
                    if rules.get_makers(parent):
                        _push(parent)
                        break
            owned = [m for m in ordered if self.nb(m) > 0]
            rest = [m for m in ordered if self.nb(m) == 0]
            buildable = self._worker_buildable_type_names()
            rest = [m for m in rest if m in buildable] + [
                m for m in rest if m not in buildable
            ]
            makers = owned + rest
            if not makers:
                for parent in getattr(wanted, "expanded_is_a", ()) or ():
                    if parent == getattr(wanted, "__name__", None):
                        continue
                    if rules.get_makers(parent):
                        return self._get(nb, parent)
                continue

            # 检查是否已有该类型的制造者
            if self.nb(makers) > 0:
                try:
                    # 尝试建造或培训单位
                    future_count = self.future_nb(types)
                    target_count = nb - future_count
                    if target_count > 0:
                        self.build_or_train_or_upgradeto_or_summon(
                            wanted, target_count
                        )
                    break
                except Exception as e:
                    # Avoid formatting e when RecursionError: str(e) can recurse again.
                    wanted_name = (
                        wanted.__name__ if hasattr(wanted, "__name__") else wanted
                    )
                    try:
                        detail = str(e)
                    except Exception:
                        detail = "<unprintable>"
                    warning(
                        "创建单位时出错: %s - %s: %s",
                        wanted_name,
                        e.__class__.__name__,
                        detail,
                    )
            elif makers:
                # 递归获取制造者
                if self._trainer_blocked_by_later_age_wood(makers[0]):
                    return False
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
        houses = self._housing_type_names()
        if isinstance(building_type, str):
            return building_type in houses
        return getattr(building_type, "type_name", None) in houses

    def _ensure_housing(self, min_headroom=2):
        """Build faction supply when population is tight (any pop-providing non-base)."""
        from .worldrequirements import requirements_satisfied

        if self._population_headroom() > min_headroom:
            return False
        if self.available_population >= self.world.population_limit:
            return False
        houses = self._housing_type_names()
        if not houses:
            return False
        buildable = self._worker_buildable_type_names()
        for house in houses:
            house_cls = rules.unit_class(house)
            if house_cls is None:
                continue
            if house not in buildable:
                continue
            # Do not chase castle_age (via walls) just to unlock castle housing.
            if not requirements_satisfied(self, getattr(house_cls, "requirements", ())):
                continue
            if self.future_nb(house) > self.nb(house):
                continue
            if self.missing_resources(house_cls.cost):
                continue
            cost = getattr(house_cls, "cost", None) or ()
            reserve = self._plan_expensive_wood_reserve(ignore_age_defer=True)
            farm_w = self._age_up_farm_wood_reserve()
            if (
                len(cost) > 1
                and cost[1] > 0
                and (
                    (reserve and self.resources[1] - cost[1] < reserve)
                    or (farm_w and self.resources[1] - cost[1] < farm_w)
                )
            ):
                continue
            self.build_or_train_or_upgradeto_or_summon(house)
            return True
        return False

    def gather(self, cost, population):
        missing = self.missing_resources(cost)
        if missing:
            self._ensure_resource_buildings(missing)
            self._idle_resource_buildings_produce()
            # e.g. knight needs food: send peasants to harvest farms, not only gold/wood
            self._send_workers_toward_resources(missing)
            if 2 in missing:
                need_w = self._cultivate_missing_wood()
                if need_w and self.resources[1] < need_w:
                    self._send_workers_toward_resources([1])
            return
        if population != 0 and population > self._population_headroom():
            if self._ensure_housing(min_headroom=population - 1):
                return
            if self.available_population >= self.world.population_limit:
                return
            return
        return True

    def _get_requirements(self, t):
        from .worldrequirements import (
            ANY_BUILDINGS,
            count_owned_buildings_of_group,
            iter_unmet_building_candidates,
            parse_requirement_clauses,
        )

        for clause in parse_requirement_clauses(t.requirements):
            if clause[0] == "has":
                r = clause[1]
                if not self.has(r):  # requirement (eventually is_a)
                    if rules.get(r, "class") == ["deposit"]:
                        return False
                    if not rules.get_makers(r):
                        return False
                    return self._get(1, r)  # exact type
            elif clause[0] == ANY_BUILDINGS:
                _, count, group = clause
                if count_owned_buildings_of_group(self, group) >= count:
                    continue
                pending = set()
                for mc in self._pending_production_makers(ignore_age_defer=True):
                    tn = getattr(mc, "type_name", None) or getattr(mc, "__name__", None)
                    if tn:
                        pending.add(tn)
                cands = list(iter_unmet_building_candidates(self, group))
                if pending:
                    cands.sort(key=lambda n: 0 if n in pending else 1)
                buildable = self._worker_buildable_type_names()
                land_only = not self._map_has_water()
                for r in cands:
                    if rules.get(r, "class") == ["deposit"]:
                        continue
                    # Cheapest feudal member is often fish_trap (fishing_ship only).
                    # On land maps get(water) returns True without building, so the
                    # old "return first _get" never reached blacksmith/stables.
                    if land_only and self._type_needs_water(r):
                        continue
                    eq = self.equivalent(r) if isinstance(r, str) else r
                    if r not in buildable and eq not in buildable:
                        continue
                    if not rules.get_makers(r) and not rules.get_makers(eq):
                        continue
                    return self._get(1, r)
                return False
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
                self._invalidate_play_derived_counts()
                return True
            if type_name in u.can_change_to and ChangeToOrder.is_allowed(u, type_name):
                u.take_order(["change_to", type_name])
                return True
        return False

    def _class_produces_type(self, maker_cls, type_name, attr):
        """True if maker class lists type_name, or a semantic race source of it."""
        if attr == "can_train":
            raw = rules.class_can_train(maker_cls)
            names = raw.keys() if isinstance(raw, dict) else (raw or ())
        else:
            names = rules.class_rules_attr(maker_cls, attr, ()) or ()
        if type_name in names:
            return True
        race_sources = getattr(rules, "_race_equivalent_sources", None)
        if not callable(race_sources):
            return False
        for semantic in race_sources(type_name):
            if semantic in names:
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
            elif self._class_produces_type(maker_cls, type, "can_build"):
                if not self.gather(t.cost, t.population_cost):
                    return
                stores = tuple(getattr(t, "storable_resource_types", ()) or ())
                if stores and self._warehouse_spend_blocked_by_wood_reserve(
                    getattr(t, "cost", None) or (), stores=stores
                ):
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
                if target is None and resource_type is not None:
                    # Town center already stores food/wood/gold, so mill/lumber/
                    # mining fail the "warehouse next to a deposit" check on the
                    # home square. Still place the building on any meadow — mill
                    # is required for farms even when the TC is the drop-off.
                    if self.nb(t):
                        return
                    target = choose_build_target(
                        self, t, starting_place=starting, resource_type=None
                    )
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
                        getattr(self.world, "building_land", "meadow"),
                        resource_type=resource_type,
                        starting_place=starting,
                    )
                    if target is None and resource_type is not None:
                        target = self.choose(
                            getattr(self.world, "building_land", "meadow"),
                            resource_type=None,
                            starting_place=starting,
                        )
                target = resolve_build_target(self, t, target)
                # Workers list semantic names; race shells resolve in BuildOrder.
                build_name = type
                builds = rules.class_rules_attr(maker_cls, "can_build", ()) or ()
                if build_name not in builds:
                    race_sources = getattr(rules, "_race_equivalent_sources", None)
                    if callable(race_sources):
                        for semantic in race_sources(type):
                            if semantic in builds:
                                build_name = semantic
                                break
                if target:
                    self.order(
                        build_worker_count(maker_cls, t),
                        maker,
                        ["build", build_name, target.id],
                        requisition=True,
                        near=target,
                    )
            elif self._class_produces_type(maker_cls, type, "can_train"):
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
                    self._invalidate_play_derived_counts()
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
                            self._invalidate_play_derived_counts()
                            trained = True
                            break
                if not trained:
                    self._try_morph_from_larva(type)
            elif type in rules.class_rules_attr(maker_cls, "can_research"):
                if self.gather(t.cost, t.population_cost):
                    self.order(1, maker, ["research", type])
            elif type in rules.class_rules_attr(maker_cls, "can_advance"):
                if self.gather(t.cost, t.population_cost):
                    issued = False
                    for u in self.units:
                        if not self.check_type(u, maker):
                            continue
                        if not building_can_operate(u):
                            continue
                        if u.orders:
                            kw = getattr(u.orders[0], "keyword", None)
                            if kw in ("advance", "research"):
                                issued = True
                                break
                            u.take_order(["stop"])
                        u.take_order(["advance", type])
                        self._invalidate_play_derived_counts()
                        issued = True
                        break
                    if not issued:
                        self.order(1, maker, ["advance", type], requisition=True)
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
            and not self._is_livestock_unit(u)
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
        """Units that cannot walk to dest. Does not re-run transport pathfinding per unit."""
        blocked = []
        for u in units:
            if getattr(u, "airground_type", None) != "ground" or u.speed <= 0:
                continue
            if self._unit_can_reach(u, dest_place):
                continue
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
