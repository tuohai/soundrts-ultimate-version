import queue
import time
import threading

from .. import config
from .. import msgparts as mp
from .. import parameters
from ..attributes_face import AttributesInterface
from ..clientgameentity import EntityView
from ..clientgamefocus import Zoom
from ..clientgamegridview import GridView
from ..clientmedia import voice
from ..lib.sound import psounds
from ..definitions import VIRTUAL_TIME_INTERVAL
from ..lib import chronometer as chrono
from ..lib.bindings import Bindings
from ..lib.log import exception, warning
from ..lib.nofloat import PRECISION
from ..lib.sound import distance
from ..version import IS_DEV_VERSION


class GameInterface(AttributesInterface):
    """游戏界面基础类，负责与服务器通信和基本状态管理"""

    last_virtual_time = 0
    x = y = o = 0
    place = None
    mouse_select_origin = None
    collision_debug = None
    shortcut_mode = False
    zoom_mode = False
    zoom = None

    def __init__(self, server, speed=config.speed):
        self.server = server
        self.speed = speed
        self.alert_squares = {}
        self.dobjets = {}
        self.group = []
        self.lost_units = []
        self.neutralized_units = []
        self.new_enemy_units = []
        self.previous_menus = {}
        self.scout_info = set()
        self.previous_unit_attacked_alert = None
        self._known_resource_places = set()
        self._known_item_ids = set()
        server.interface = self
        self.grid_view = GridView(self)
        psounds.listener = self
        voice.silent_flush()
        self._srv_queue = queue.Queue()
        self.scouted_squares = ()
        self.scouted_before_squares = ()
        self._bindings = Bindings()
        
        # 初始化属性界面
        AttributesInterface.__init__(self, self)
        
        # 倒地音效回调字典
        self._falling_callbacks = {}
        
        # 添加方向过滤和类型过滤变量
        self._side_filter = "all"  # 可选值: "ally"（己方）, "enemy"（敌方）, "all"（全部）
        self._type_filter = "all"   # 可选值: "building"（建筑）, "unit"（单位）, "element"（元素）, "all"（全部）
        
        # 战斗音乐状态检查
        self._last_battle_status_check = 0
        self._battle_status_check_interval = 5.0  # 每5秒检查一次战斗状态
        
        # RPG缩放模式精细度设置（可选：3, 5, 7, 9, 11）
        self._zoom_precision = 3  # 3x3网格，9个子区域
        
        # RPG模式单位位置跟踪，用于检测何时进入新方格
        self._rpg_unit_previous_place = None
        
        # 缩放比例输入模式状态
        self._zoom_input_mode = False
        self._zoom_input_string = ""

    def _stop_unpicklable_audio(self):
        """Stop ambient noises that hold pygame.mixer.Channel via SoundSource."""
        from .build_field_voice import stop_build_field_noises

        stop_build_field_noises(self)
        for n in getattr(self, "_terrain_noises", [])[:]:
            try:
                n.stop()
            except Exception:
                pass
        self._terrain_noises = []
        self._build_field_noises = []

    def __getstate__(self):
        self._stop_unpicklable_audio()
        odict = self.__dict__.copy()
        del odict["_srv_queue"]
        odict["_terrain_noises"] = []
        odict["_build_field_noises"] = []
        return odict

    def __setstate__(self, dictionary):
        self.__dict__.update(dictionary)
        self._srv_queue = queue.Queue()
        self._terrain_noises = []
        self._build_field_noises = []
        psounds.listener = self
        self.waiting_for_world_update = False

    @property
    def display_is_active(self):
        from ..clientmedia import get_fullscreen
        return get_fullscreen() or IS_DEV_VERSION

    @property
    def player(self):
        try:
            return self.server.player
        except:
            return None

    @property
    def world(self):
        return self.server.player.world

    _square_width = None

    @property
    def square_width(self):
        if self._square_width is None:
            self._square_width = self.world.square_width / 1000.0
        return self._square_width

    def distance(self, o):
        return distance(self.x, self.y, o.x, o.y)

    def _process_srv_event(self, *e):
        try:
            cmd = getattr(self, "srv_" + e[0])
        except AttributeError:
            warning("Not recognized: %s" % e[0])
        else:
            cmd(*e[1:])

    def srv_event(self, o, e):
        try:
            if (
                hasattr(self, "next_update")
                and time.time() > self.next_update + 3  # EVENT_LIMIT
            ):
                return
            EntityView(self, o).notify(e)
        except:
            exception("problem during srv_event")

    def queue_srv_event(self, *e):
        self._srv_queue.put(e)

    def _process_srv_events(self):
        # 恢复逐帧仅处理一个事件的行为，避免改变音效触发节奏
        if not self._srv_queue.empty():
            e = self._srv_queue.get()
            self._process_srv_event(*e)

    def srv_quit(self):
        voice.silent_flush()
        from ..lib import sound
        sound.stop()
        self.end_loop = True

    def srv_msg(self, s):
        from ..lib.msgs import eval_msg_and_volume
        voice.info(*eval_msg_and_volume(s))

    def srv_voice_important(self, s):
        from ..lib.msgs import eval_msg_and_volume
        voice.confirmation(*eval_msg_and_volume(s))

    def srv_speed(self, s):
        self.speed = float(s)

    def srv_sequence(self, parts):
        from ..clientmedia import play_sequence
        play_sequence(parts)

    def srv_play(self, s):
        from ..clientmedia import sounds
        psounds.play_stereo(sounds.get_sound(s[0]))

    def srv_voila(
        self,
        t,
        memory,
        perception,
        scouted_squares,
        scouted_before_squares,
        collision_debug,
    ):
        self.last_virtual_time = float(t) / 1000.0
        self.waiting_for_world_update = False

        self.memory = memory
        self.perception = perception
        self.scouted_squares = scouted_squares
        self.scouted_before_squares = scouted_before_squares
        self.collision_debug = collision_debug

        # 这些方法会在其他模块中定义
        from .game_resources import send_resource_alerts_if_needed
        from .game_unit_control import send_menu_alerts_if_needed, units_alert_if_needed, update_group
        from .game_navigation import squares_alert_if_needed, scout_info_if_needed, update_fog_of_war, _follow_if_needed
        from .game_display import display

        send_resource_alerts_if_needed(self)
        if self.previous_menus == {}:
            send_menu_alerts_if_needed(self)  # init
        units_alert_if_needed(self)
        squares_alert_if_needed(self)
        scout_info_if_needed(self)

        update_fog_of_war(self)
        update_group(self)
        display(self)

        if getattr(self, '_bell_enabled', False):
            self._eventually_play_bell()
        if getattr(self, '_must_play_tick', False):
            self._play_tick()
        self._record_update_time()

    waiting_for_world_update = False

    def _ask_for_update(self):
        self._update_catch_up_audio()
        for player, order in self.server.get_orders():
            self.world.queue_command(player, order)
        self.world.queue_command(None, self.world.update)
        self.waiting_for_world_update = True
        interval = VIRTUAL_TIME_INTERVAL / 1000.0 / self.speed
        self.next_update = time.time() + interval

    def _time_to_ask_for_next_update(self):
        if self.waiting_for_world_update:
            return False
        # 旁观者追帧：当积压了大量待重放的历史回合时，跳过实时节流，尽快把世界
        # 追到当前进度（追帧期间音频被静音，避免几十分钟战斗音一次性炸开）。
        has_backlog = getattr(self.server, "has_catch_up_backlog", None)
        if has_backlog is not None and has_backlog():
            return True
        return time.time() >= self.next_update

    _catch_up_muted = False

    def _update_catch_up_audio(self):
        """旁观追帧期间静音，追上后恢复音频。"""
        has_backlog = getattr(self.server, "has_catch_up_backlog", None)
        if has_backlog is None:
            return
        catching_up = has_backlog()
        if catching_up and not self._catch_up_muted:
            from ..lib import sound
            self._saved_main_volume = sound.main_volume
            sound.main_volume = 0
            voice.muted = True
            self._catch_up_muted = True
        elif not catching_up and self._catch_up_muted:
            from ..lib import sound
            sound.main_volume = getattr(self, "_saved_main_volume", sound.main_volume)
            voice.muted = False
            voice.silent_flush()
            self._catch_up_muted = False
            voice.info(mp.YOU_ARE_SPECTATING)

    # 时钟相关功能
    _bell_enabled = False
    _previous_nb_minutes = 0

    def _eventually_play_bell(self):
        from ..clientmedia import sounds
        nb_minutes = int(self.last_virtual_time / 60)
        if self._previous_nb_minutes != nb_minutes:
            psounds.play_stereo(sounds.get_sound(mp.POSITIONAL_BEEP[0]))
            self._previous_nb_minutes = nb_minutes

    _must_play_tick = False
    _average_turn_duration = 0
    _previous_update_time = None

    def _play_tick(self):
        from ..clientmedia import sounds
        psounds.play_stereo(sounds.get_sound(mp.POSITIONAL_BEEP[0]), vol=0.1)

    def _record_update_time(self):
        interval = VIRTUAL_TIME_INTERVAL / 1000.0 / min(10.0, self.speed)
        nb_samples = max(1.0, 1.0 / interval)
        if self._previous_update_time is None:
            turn_duration = interval
        else:
            turn_duration = time.time() - self._previous_update_time
        self._previous_update_time = time.time()
        if self._average_turn_duration == 0:
            self._average_turn_duration = turn_duration
        else:
            self._average_turn_duration = (
                self._average_turn_duration * (nb_samples - 1) + turn_duration
            ) / nb_samples

    def _get_tps(self):
        try:
            return 1 / self._average_turn_duration
        except ZeroDivisionError:
            return 100

    @property
    def real_speed(self):
        return self._get_relative_speed()

    def _get_relative_speed(self):
        normal_speed_tps = 1 / (VIRTUAL_TIME_INTERVAL / 1000.0)
        return self._get_tps() / normal_speed_tps

    def is_admin(self):
        try:
            return self.player.world.players[0] is self.player
        except:
            warning("couldn't be sure if this client is the admin of the game")
            return True

    def can_save(self):
        return hasattr(self.server, "save_game")

    def load_bindings(self, s):
        self._bindings.load(s, self)

    def get_bindings(self):
        if getattr(self, "_layered_bindings_active", False):
            from .interface_modes import get_bindings_text
            return get_bindings_text(getattr(self, "_ui_mode", "unit"))
        from .interface_modes import get_legacy_bindings_text
        return get_legacy_bindings_text()

    def run_game(self, game, new=True):
        from ..lib import game_tts as _game_tts

        # in_match stays False through opening intro/objective so any-key skip
        # uses the simple VoiceChannel path (like 1.3.8.1). World start enables it.
        try:
            self._run_game_body(game, new=new)
        finally:
            _game_tts.set_in_match(False)

    def _run_game_body(self, game, new=True):
        from ..lib import game_tts as _game_tts
        from ..clientgameorder import update_orders_list
        update_orders_list()  # when style has changed

        # Opening intro/objective must run BEFORE world.loop starts. On heavy
        # maps (e.g. sg4) the simulation thread otherwise starves the GIL and
        # key-polling in voice.confirmation becomes sluggish.
        if new:
            game.pre_run()
            # 播放游戏背景音乐，优先使用阵营专属音乐，其次是地图指定的音乐
            from ..lib import sound
            from ..definitions import style
            from ..lib.log import debug, exception
            
            # 默认为None，后续会根据优先级尝试设置
            faction_music = None
            
            # 检查是否是战役游戏
            is_campaign_game = False
            try:
                from ..lib.resource import res
                is_campaign_game = hasattr(res, '_campaign') and res._campaign is not None
                if is_campaign_game:
                    debug("检测到战役游戏，将使用全局音乐")
            except Exception as e:
                exception(f"检查是否是战役游戏时出错: {e}")
            
            # 获取玩家的阵营ID（非战役游戏才使用阵营音乐）
            player_faction = None
            try:
                # 获取当前玩家的阵营
                if hasattr(self.player, 'faction') and self.player.faction:
                    player_faction = self.player.faction
                    
                # 如果玩家阵营不是字符串（而是对象），尝试获取类型名称
                if player_faction and not isinstance(player_faction, str):
                    if hasattr(player_faction, 'type_name'):
                        player_faction = player_faction.type_name
                
                # 设置玩家阵营全局变量
                if player_faction:
                    sound.set_player_faction(player_faction)
                
                # 只有在非战役游戏中才使用阵营音乐
                if not is_campaign_game:
                    # 检查是否有对应的阵营专属音乐
                    if player_faction and hasattr(style, 'faction_music_settings'):
                        # 检查阵营ID是否在音乐设置中
                        if player_faction in style.faction_music_settings:
                            faction_music = style.faction_music_settings[player_faction]
                            debug(f"找到玩家阵营 {player_faction} 的专属音乐: {faction_music}")
                        else:
                            debug(f"玩家阵营 {player_faction} 没有专属音乐设置")
            except Exception as e:
                exception(f"获取阵营专属音乐时出错: {e}")
            
            # 将地图音乐信息传递给play_game_music函数
            map_music = getattr(game.world, 'map_music', None)
            sound.play_game_music(map_music, faction_music)
            
            if game.world.objective:
                # 暂停背景音乐（保留播放位置）
                sound.pause_music()
                
                # 播放任务目标
                voice.confirmation(mp.OBJECTIVE + game.world.objective)
                
                # 恢复背景音乐（从暂停位置继续）
                sound.unpause_music()
        else:
            # 对于加载的存档游戏，也需要重新播放游戏音乐
            from ..lib import sound
            from ..definitions import style
            from ..lib.log import debug, exception
            
            # 重置战斗状态
            sound.in_battle = False
            
            # 默认为None，后续会根据优先级尝试设置
            faction_music = None
            
            # 检查是否是战役游戏
            is_campaign_game = False
            try:
                from ..lib.resource import res
                is_campaign_game = hasattr(res, '_campaign') and res._campaign is not None
                if is_campaign_game:
                    debug("检测到加载的战役游戏，将使用全局音乐")
            except Exception as e:
                exception(f"检查是否是战役游戏时出错: {e}")
            
            # 获取玩家的阵营ID（非战役游戏才使用阵营音乐）
            player_faction = None
            try:
                # 获取当前玩家的阵营
                if hasattr(self.player, 'faction') and self.player.faction:
                    player_faction = self.player.faction
                    
                # 如果玩家阵营不是字符串（而是对象），尝试获取类型名称
                if player_faction and not isinstance(player_faction, str):
                    if hasattr(player_faction, 'type_name'):
                        player_faction = player_faction.type_name
                
                # 设置玩家阵营全局变量
                if player_faction:
                    sound.set_player_faction(player_faction)
                
                # 只有在非战役游戏中才使用阵营音乐
                if not is_campaign_game:
                    # 检查是否有对应的阵营专属音乐
                    if player_faction and hasattr(style, 'faction_music_settings'):
                        # 检查阵营ID是否在音乐设置中
                        if player_faction in style.faction_music_settings:
                            faction_music = style.faction_music_settings[player_faction]
                            debug(f"加载游戏：找到玩家阵营 {player_faction} 的专属音乐: {faction_music}")
                        else:
                            debug(f"加载游戏：玩家阵营 {player_faction} 没有专属音乐设置")
            except Exception as e:
                exception(f"获取阵营专属音乐时出错: {e}")
            
            # 将地图音乐信息传递给play_game_music函数
            map_music = getattr(game.world, 'map_music', None)
            debug(f"加载存档：播放游戏音乐 map_music={map_music}, faction_music={faction_music}")
            sound.play_game_music(map_music, faction_music)

        t = threading.Thread(target=game.world.loop)
        t.daemon = True
        _game_tts.set_in_match(True)
        t.start()

        from .interface_modes import init_interface_modes
        init_interface_modes(self)
        # 主循环：支持性能分析输出（与 1.3.8.1 行为对齐，且生成 .txt 报告）
        from .game_input_handler import _loop

        # 支持两种开关来源：
        # 1) 包级开关 soundrts.clientgame.__init__.PROFILE
        # 2) 兼容层文件 soundrts/clientgame.py 的 PROFILE 或 profile
        try:
            from . import PROFILE as _pkg_profile
        except Exception:
            _pkg_profile = False

        _legacy_profile = False
        try:
            import os
            import importlib.util
            _base_dir = os.path.dirname(__file__)
            _legacy_path = os.path.abspath(os.path.join(_base_dir, os.pardir, "clientgame.py"))
            if os.path.exists(_legacy_path):
                _spec = importlib.util.spec_from_file_location("soundrts._clientgame_legacy", _legacy_path)
                if _spec and _spec.loader:
                    _mod = importlib.util.module_from_spec(_spec)
                    _spec.loader.exec_module(_mod)
                    _legacy_profile = bool(getattr(_mod, "PROFILE", False) or getattr(_mod, "profile", False))
        except Exception:
            _legacy_profile = False

        _profile_enabled = bool(_pkg_profile or _legacy_profile)
        if _profile_enabled:
            import cProfile
            cProfile.runctx("_loop(self)", globals(), locals(), "interface_profile.tmp")
            # 生成可读的文本报告
            try:
                import pstats
                with open("interface_profile.txt", "w", encoding="utf-8") as _txt:
                    _p = pstats.Stats("interface_profile.tmp", stream=_txt)
                    _p.strip_dirs()
                    _p.sort_stats("time", "cumulative").print_stats(30)
                    _p.print_callers(30)
                    _p.print_callees(20)
                    _p.sort_stats("cumulative").print_stats(50)
                    _p.print_callers(100)
                    _p.print_callees(100)
            except Exception:
                pass
        else:
            _loop(self)

        # 兜底：若退出循环时仍处于旁观追帧静音状态，务必恢复全局音量与语音，
        # 否则 main_volume 会一直停留在 0、影响后续菜单与对局。
        if self._catch_up_muted:
            from ..lib import sound
            sound.main_volume = getattr(self, "_saved_main_volume", sound.main_volume)
            voice.muted = False
            self._catch_up_muted = False
        
        game._record_stats(game.world)
        game.post_run()
        game.world.stop()
        
        # 游戏结束时，恢复菜单音乐
        from ..lib import sound
        # 重置战斗状态，并播放主菜单音乐
        sound.in_battle = False
        sound.play_menu_music()

    # auto相关
    auto = []