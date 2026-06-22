import random
import time
from typing import TYPE_CHECKING, List, Union

from . import config
from .definitions import VIRTUAL_TIME_INTERVAL
from .lib.log import info, warning
from .mapfile import Map

if TYPE_CHECKING:
    from .serverclient import ConnectionToClient

from .version import IS_DEV_VERSION


def same(strings):
    return len(set(strings)) == 1


def time_string(check_string):
    if check_string is not None:
        return check_string.split("-", 1)[0]


def pack(p):
    return ",".join((p.login, str(p.alliance), p.faction))


class _State:
    allowed_commands: tuple

    def send_menu(self, client):
        pass


class Anonymous(_State):

    allowed_commands = ("login",)


class InTheLobby(_State):

    allowed_commands = ("create", "create_random", "create_campaign", "register", "quit", "say", "list_games", "spectate")

    def send_menu(self, client):
        client.send_maps()
        client.send_invitations()
        client.notify("update_menu")


class OrganizingAGame(_State):

    allowed_commands = (
        "invite",
        "invite_ai",
        "invite_beginner",
        "invite_intermediate",
        "invite_advanced",
        "invite_expert",
        "invite_nightmare",
        "invite_easy",
        "invite_aggressive",
        "invite_ai2",
        "move_to_alliance",
        "set_coop_slot",
        "start",
        "cancel_game",
        "say",
        "faction",
        "create_campaign",
    )

    def send_menu(self, client):
        client.notify(
            "available_players",
            *[
                p.login
                for p in client.server.available_players(client)
                if p not in client.game.guests
            ],
        )
        client.notify("registered_players", *[pack(p) for p in client.game.players])
        client.notify("update_menu")


class WaitingForTheGameToStart(_State):

    allowed_commands = ("unregister", "say", "faction")

    def send_menu(self, client):
        client.notify("registered_players", *[pack(p) for p in client.game.players])
        client.notify("update_menu")


class Playing(_State):

    allowed_commands = ("orders", "quit_game", "timeout", "debug_info", "say")


class Spectating(_State):

    allowed_commands = ("quit_spectating", "say")


class _Computer:
    def __init__(self, level, coop_partner=False):
        self.level = level
        self.coop_partner = coop_partner
        self.alliance = 0
        self.faction = "random_faction"

    @property
    def login(self):
        if self.coop_partner:
            return "ai_coop"
        return "ai_" + self.level


class Orders:
    def __init__(self, game):
        self.all_orders = {}
        for client in game.human_players:
            self.all_orders[client] = []

    def __repr__(self):
        return "<Orders '%s'>" % repr(self.all_orders)

    def add(self, client, args):
        self.all_orders[client].append(args)

    def pop_and_pack(self):
        _all_orders = []
        for player, queue in list(self.all_orders.items()):
            orders = queue.pop(0)[0]
            _all_orders.append(f"{player.login}/{orders}")
        return " ".join(_all_orders)

    def are_ready(self):
        return [] not in list(self.all_orders.values())

    def remove(self, client):
        del self.all_orders[client]

    def players_without_orders(self):
        return [player for player, queue in list(self.all_orders.items()) if not queue]

    def get_next_check_strings(self):
        return [queue[0][1] for queue in list(self.all_orders.values())]


class Game:

    started = False
    speed = 1

    def __init__(self, scenario: Map, speed, server, admin, is_public=False, treaty_minutes: int = 0) -> None:
        self.id = server.get_next_id()
        self.scenario = scenario
        self.speed = speed
        self.real_speed = speed
        self.server = server
        self.admin = admin
        self.is_public = is_public
        self.treaty_minutes = int(treaty_minutes) if treaty_minutes else 0
        self.players: List[Union["ConnectionToClient", _Computer]] = []
        self.guests: List[Union["ConnectionToClient", _Computer]] = []
        self.spectators: List["ConnectionToClient"] = []  # 旁观者列表
        # 旁观同步所需：开局随机种子 + 已下发的全部 all_orders 历史。
        # 服务器本身不模拟世界，旁观者要靠"相同 seed + 重放历史 orders"
        # 才能确定性地重建当前对局状态，因此必须把这两样记录下来。
        self.seed = 0
        self._order_history: List[tuple] = []  # [(fpct, all_orders_string), ...]
        self._initial_players_pack = ""  # 开局原始玩家名册，旁观重建用
        self.register(admin)
        if self.is_public:
            self._process_public_game()

    def _process_public_game(self):
        for player in self.server.available_players():
            if player.is_compatible(self.admin):
                self.invite(player)

    def notify_connection_of(self, client):
        if self.is_public and self.can_register() and client.is_compatible(self.admin):
            self.invite(client)

    @property
    def human_players(self) -> List["ConnectionToClient"]:
        return [p for p in self.players if not isinstance(p, _Computer)]

    def _start(self):
        info(
            "start game %s on map %s with players %s",
            self.id,
            self.scenario.name,
            " ".join(p.login for p in self.players),
        )
        self.guests = []
        self.started = True
        self.time = 0
        random.seed()
        seed = getattr(self, "rmg_seed", None)
        if seed is None:
            seed = random.randint(0, 10000)
        # 记录种子，供旁观者用相同种子确定性重建世界。
        self.seed = seed
        self._order_history = []
        self._orders = Orders(self)
        ##        # guess first ping from the connection delays
        ##        self.ping = max([p.delay for p in self.human_players])
        # 帝国时代式合作战役：人类玩家与 AI 队友同属 1 队。
        # 敌人来自地图的 computer_only（在 populate_map 里以 "ai" 同盟自成一队），
        # 不在 game.players 里，因此这里把 game.players 全部归为 1 队即可；
        # 并先用同盟 AI 队友补满地图声明但无人占用的玩家位（空位由 AI 接管，
        # 这样单人也能开合作关，符合帝国时代"线上单人"的做法）。
        try:
            is_coop = bool(getattr(self, "is_coop_campaign", False))
        except Exception:
            is_coop = False
        if is_coop:
            self._fill_coop_ai_partners()
            for p in self.players:
                p.alliance = 1

        # 固化开局玩家名册（含此刻的 alliance/faction）。旁观者必须用这份原始名册
        # 重建世界，而不是 self.players（玩家中途退出会从中移除），否则重放的历史
        # orders 会引用世界里不存在的玩家而分叉。退出动作本身已在 orders 历史里。
        self._initial_players_pack = ";".join(pack(p) for p in self.players)

        # 合作战役难度：在开局时一次性算定敌人强度百分比（含玩家人数缩放），
        # 作为唯一数据源下发给所有客户端，并缓存供旁观者使用。确定性要求各端一致，
        # 故必须由服务器算定后分发，而不是各端自行根据等级名重算。
        self._coop_enemy_hp = 100
        self._coop_enemy_damage = 100
        coop_difficulty = getattr(self, "coop_difficulty", None)
        if is_coop and coop_difficulty:
            try:
                from .coop_difficulty import factors

                self._coop_enemy_hp, self._coop_enemy_damage = factors(
                    coop_difficulty, len(self.human_players)
                )
            except Exception:
                self._coop_enemy_hp = 100
                self._coop_enemy_damage = 100

        for client in self.human_players:
            # 难度行必须在 start_game 之前发送：客户端 menu 顺序处理事件，
            # srv_coop_difficulty 先把百分比存好，srv_start_game 再读取并配置世界。
            if is_coop and coop_difficulty:
                client.notify(
                    "coop_difficulty",
                    self._coop_enemy_hp,
                    self._coop_enemy_damage,
                    coop_difficulty,
                )
            client.notify(
                "start_game",
                self._initial_players_pack,
                client.login,
                seed,
                self.speed,
                self.treaty_minutes,
                # 附加合作战役元信息：标记、战役名、章节号
                int(is_coop),
                getattr(self, "coop_campaign_name", ""),
                getattr(self, "coop_chapter", ""),
            )
            client.state = Playing()
        self.server.log_status()
        self._start_time = time.time()

    def start(self):
        if (
            self.scenario.nb_players_min
            <= len(self.players)
            <= self.scenario.nb_players_max
        ):
            self._start()
        else:
            warning("couldn't start game: bad number of players")

    def remove(self, client):
        info("%s has quit game %s after %s turns", client.login, self.id, self.time)
        self.players.remove(client)
        if self.human_players:
            self._orders.remove(client)
            self._dispatch_orders_if_needed()
        else:
            self.close()

    @property
    def nb_minutes(self):
        return int((time.time() - self._start_time) / 60)

    def close(self):
        info(
            "closed game %s after %s turns (played for %s minutes)",
            self.id,
            self.time,
            self.nb_minutes,
        )
        self.cancel()
        self.server.log_status()

    _nb_allowed_alerts = 1

    def _check_synchronization(self, check_strings):
        if not same(check_strings) and self._nb_allowed_alerts > 0:
            if not same(time_string(cs) for cs in check_strings):
                if IS_DEV_VERSION and None not in check_strings:
                    info(
                        "time mismatch in game %s at turn %s: %s",
                        self.id,
                        self.time,
                        check_strings,
                    )
                return
            warning(
                "mismatch in game %s at turn %s: %s", self.id, self.time, check_strings
            )
            self._nb_allowed_alerts -= 1
            self.notify("synchronization_error")

    ping = 0
    delay = 0

    def orders(
        self, client, orders, check=None, ping=0, update=0, delay=0, real_speed=0
    ):
        self.ping = max(self.ping, float(ping))
        self.delay = max(self.delay, float(delay))
        self.real_speed = min(self.real_speed, float(real_speed))
        self._orders.add(client, [orders, check])
        self._dispatch_orders_if_needed()

    max_ping = 0.5  # seconds

    def fpct(self):
        """number of simulation frames per communication turn"""
        # 1 is probably the best number in most cases because the game is often CPU-bound.
        # the following number could be chosen instead someday
        tps = self.real_speed * 1000 / VIRTUAL_TIME_INTERVAL
        # Avoid unrealistic ping values.
        ping = min(self.max_ping, self.ping)
        result = int(tps * ping * config.fpct_coef) + 1
        return min(config.fpct_max, result)

    def _dispatch_orders_if_needed(self):
        while self._orders.are_ready():
            self._check_synchronization(self._orders.get_next_check_strings())
            all_orders = self._orders.pop_and_pack()
            fpct = self.fpct()
            # 记录这一通信回合下发的 orders，供后来加入的旁观者重放追帧。
            self._order_history.append((fpct, all_orders))
            self.notify("all_orders", fpct, all_orders)
            self.time += 1
            self._timeout_reference = None
            self.ping = 0
            self.delay = 0
            self.real_speed = self.speed

    def invite(self, client):
        self.guests.append(client)
        from .randommap import map_voice_title

        voice_title = map_voice_title(self.scenario)
        if voice_title:
            client.notify("invitation", self.admin.login, *voice_title)
        else:
            client.notify("invitation", self.admin.login, self.scenario.name)

    # 合作战役 AI 队友默认等级（积极型 AI：会主动用该位的起始部队作战）
    coop_partner_level = "aggressive"

    def _player_at_alliance(self, alliance):
        for p in self.players:
            if p.alliance == alliance:
                return p
        return None

    def _add_coop_ai_at_alliance(self, alliance):
        partner = _Computer(self.coop_partner_level, coop_partner=True)
        partner.alliance = alliance
        self.players.append(partner)

    def _notify_registered_players(self):
        self.notify("registered_players", *[pack(p) for p in self.players])

    def set_coop_slot_ai(self, alliance):
        """将指定合作槽位设为 AI 队友（帝国时代决定版式，非遭遇战难度 AI）。"""
        occupant = self._player_at_alliance(alliance)
        if occupant is not None and not isinstance(occupant, _Computer):
            return False
        self.players = [
            p
            for p in self.players
            if not (isinstance(p, _Computer) and p.alliance == alliance)
        ]
        self._add_coop_ai_at_alliance(alliance)
        self._notify_registered_players()
        return True

    def clear_coop_slot(self, alliance):
        """将指定合作槽位设为空缺（移除该位的合作 AI 队友）。"""
        before = len(self.players)
        self.players = [
            p
            for p in self.players
            if not (
                isinstance(p, _Computer)
                and getattr(p, "coop_partner", False)
                and p.alliance == alliance
            )
        ]
        if len(self.players) != before:
            self._notify_registered_players()
        return True

    def _fill_coop_ai_partners(self):
        """合作战役：用同盟 AI 队友补满地图声明但无人占用的玩家位。

        帝国时代决定版的合作战役允许空的玩家位由 AI 队友接管（"线上单人"也能
        开战役）。仅当地图的 ``nb_players_max`` 大于当前已注册玩家数时才补；
        补出的 AI 与人类同队（其 alliance 由调用方在合作分支里统一设为 1）。

        敌人来自地图的 ``computer_only``（不在 ``self.players`` 内），不受影响。
        每个补出的 AI 会在 ``populate_map`` 里分到一个独立的玩家出生点，
        从而像帝国时代那样各自拥有一份起始部队/基地。
        """
        try:
            max_slots = int(self.scenario.nb_players_max)
        except Exception:
            return
        used = {p.alliance for p in self.players}
        for alliance in range(1, max_slots + 1):
            if alliance not in used:
                self._add_coop_ai_at_alliance(alliance)

    def invite_computer(self, level):
        if getattr(self, "is_coop_campaign", False):
            self.admin.notify("invite_computer_error")
            return
        if (
            not config.require_humans
            or "admin_only" in self.server.parameters
            or len(self.players) > 1
        ):
            self.register(_Computer(level))
        else:
            self.admin.notify("invite_computer_error")

    def uninvite(self, client):
        self.guests.remove(client)

    def add_spectator(self, client):
        """添加旁观者"""
        if client not in self.spectators:
            self.spectators.append(client)
            client.game = self
            client.state = Spectating()
            # 通知所有玩家和旁观者有新的旁观者加入
            for player in self.human_players:
                player.notify("spectator_joined", client.login)
            for spectator in self.spectators:
                if spectator != client:
                    spectator.notify("spectator_joined", client.login)
            info(f"旁观者 {client.login} 加入游戏 {self.id}")

    def remove_spectator(self, client):
        """移除旁观者"""
        if client in self.spectators:
            self.spectators.remove(client)
            client.game = None
            client.state = InTheLobby()
            # 通知所有玩家和旁观者有旁观者离开
            for player in self.human_players:
                player.notify("spectator_left", client.login)
            for spectator in self.spectators:
                spectator.notify("spectator_left", client.login)
            info(f"旁观者 {client.login} 离开游戏 {self.id}")

    def start_spectating(self, client):
        """开始旁观游戏

        关键点：服务器是纯转发器、不模拟世界。要让旁观者看到与对局完全一致的
        画面，必须做到确定性重放：
          1) 下发开局 seed 与 treaty 分钟数（影响世界生成与战斗/移动判定）；
          2) 把开局至今的全部 all_orders 历史按顺序回放给旁观者，让其把世界
             快进到当前回合；
          3) 先把 client 加入 spectators（本函数是单线程、原子执行，期间不会有
             新回合派发），随后的实时回合再通过 notify 正常推送，既无空档也无重复。
        """
        if self.started:
            self.add_spectator(client)
            # 发送游戏状态给旁观者（含确定性重放所需的 seed 与 treaty）。
            # 使用开局原始名册，确保与历史 orders 引用的玩家集合一致。
            initial_players = getattr(self, "_initial_players_pack", None)
            if not initial_players:
                initial_players = ";".join(pack(p) for p in self.players)
            client.notify(
                "start_spectating",
                initial_players,
                self.scenario.name,
                self.speed,
                self.seed,
                self.treaty_minutes,
                # 合作战役难度：旁观者必须用与对局相同的敌人强度百分比重建世界，
                # 否则敌方 hp/伤害缩放不一致会导致重放历史 orders 时分叉。
                getattr(self, "_coop_enemy_hp", 100),
                getattr(self, "_coop_enemy_damage", 100),
            )
            # 重放历史 orders，让旁观者世界追上当前进度
            for fpct, all_orders in self._order_history:
                client.notify("all_orders", fpct, all_orders)
            return True
        return False

    def move_to_alliance(self, player_index, alliance):
        player = self.players[int(player_index)]
        player.alliance = int(alliance)
        self.notify("alliance", player.login, player.alliance)

    def set_faction(self, player_index, faction):
        player = self.players[int(player_index)]
        player.faction = faction
        self.notify("faction", player.login, faction)

    def notify(self, *args):
        for client in self.human_players:
            client.notify(*args)
        # 旁观者也接收游戏消息
        for spectator in self.spectators:
            spectator.notify(*args)

    def can_register(self):
        if self.started:
            return False
        if getattr(self, "is_coop_campaign", False):
            return self._coop_has_joinable_slot()
        return len(self.players) < self.scenario.nb_players_max

    def _coop_partner_slots(self):
        try:
            max_slots = int(self.scenario.nb_players_max)
        except Exception:
            return []
        return list(range(2, max_slots + 1))

    def _coop_has_joinable_slot(self):
        for alliance in self._coop_partner_slots():
            occupant = self._player_at_alliance(alliance)
            if occupant is None:
                return True
            if isinstance(occupant, _Computer) and getattr(occupant, "coop_partner", False):
                return True
        return False

    def prepare_coop_slot_for_human(self, alliance=None):
        """Remove coop AI from partner slot(s) before a human is invited or joins."""
        slots = [alliance] if alliance is not None else self._coop_partner_slots()
        changed = False
        for slot in slots:
            occupant = self._player_at_alliance(slot)
            if isinstance(occupant, _Computer) and getattr(occupant, "coop_partner", False):
                if self.clear_coop_slot(slot):
                    changed = True
        return changed

    def register(self, client):
        if getattr(self, "is_coop_campaign", False):
            return self._register_coop(client)
        if not self.can_register():
            return False
        for n in range(len(self.players) + 1):
            n += 1
            if n not in [p.alliance for p in self.players]:
                break
        self._add_registered_client(client, n)
        return True

    def _register_coop(self, client):
        if not self._coop_has_joinable_slot():
            return False
        for alliance in self._coop_partner_slots():
            occupant = self._player_at_alliance(alliance)
            if occupant is None:
                self._add_registered_client(client, alliance)
                return True
            if isinstance(occupant, _Computer) and getattr(occupant, "coop_partner", False):
                self.clear_coop_slot(alliance)
                self._add_registered_client(client, alliance)
                return True
        return False

    def _add_registered_client(self, client, alliance):
        self.players.append(client)
        client.game = self
        client.alliance = alliance
        client.faction = "random_faction"
        self.notify(
            "registered", client.login, ",".join([c.login for c in self.players])
        )
        self._notify_registered_players()

    @property
    def short_status(self):
        from .randommap import map_voice_title

        voice_title = map_voice_title(self.scenario)
        if voice_title is None:
            voice_title = [self.scenario.name]
        return (
            *voice_title,
            ",".join([c.login for c in self.players]),
            self.nb_minutes,
        )

    def unregister(self, client):
        self.players.remove(client)
        client.notify("quit")
        client.state = InTheLobby()

    def cancel(self):
        for c in self.human_players:
            self.unregister(c)
        for c in self.guests[:]:
            self.uninvite(c)
        # 清理旁观者
        for c in self.spectators[:]:
            self.remove_spectator(c)
        self.server.games.remove(self)

    _timeout_reference = None

    def check_timeout(self):
        if self._timeout_reference is None:
            self._timeout_reference = time.time()
        elif time.time() > self._timeout_reference + config.timeout:
            for player in self._orders.players_without_orders():
                warning("timeout %s", player.login)
                player.handle_close()  # disconnect player
                break  # don't continue! (might disconnect more players)
