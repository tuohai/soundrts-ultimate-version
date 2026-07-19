import math
import random
import time
import os
import gc
from typing import Dict, List, Optional

import pygame

from soundrts.lib import tts
from .sound_cache import Sound

from .. import parameters
from .log import warning, debug

DEFAULT_VOLUME = math.sin(
    math.pi / 4.0
)  # (about .7) volume for each speaker for an "in front of you" message

# 添加音乐相关变量
current_music = None
menu_music = None
game_music = None
campaign_music = None  # 战役菜单音乐
game_creation_music = None  # 创建游戏菜单音乐
server_lobby_music = None  # 服务器大厅菜单音乐
faction_music = None  # 阵营专属音乐
battle_music = None  # 战斗音乐
faction_battle_music = None  # 阵营专属战斗音乐
victory_sound = None  # 胜利音乐
defeat_sound = None  # 失败音乐
in_battle = False  # 是否处于战斗状态
music_volume = 0.5  # 初始音乐音量
music_enabled = True  # 控制音乐开关
music_fade_time = 20  # 淡入淡出时间(毫秒)
music_paused = False  # 记录音乐是否被暂停
current_player_faction = None  # 当前玩家阵营

# 支持的音乐格式
MUSIC_FORMATS = ['.mp3', '.ogg', '.wav']  # 添加对OGG格式和WAV格式的支持

# 音乐缓存
_music_cache = {}  # 音乐ID到文件路径的映射

# 添加一个全局变量来记录当前菜单类型
current_menu_type = "main"  # 可能的值: "main", "campaign", "game_creation", "server_lobby"


def distance(x1, y1, x2, y2):
    dx = x2 - x1
    dy = y2 - y1
    return math.sqrt(dx * dx + dy * dy)


def angle(x1, y1, x2, y2, o=0):
    """angle of x2,y2 related to player x1,y1,o"""
    d = distance(x1, y1, x2, y2)
    if d == 0:
        return 0  # object too close => in front of player
    ac = math.acos((x2 - x1) / d)
    if y2 - y1 > 0:
        a = ac
    else:
        a = -ac
    return a - math.radians(o)


def stereo(x, y, xo, yo, o, volume=1, no_distance=False):
    a = angle(x, y, xo, yo, o)
    if no_distance:
        d = 1
    else:
        d = distance(x, y, xo, yo)
        if d < 1:
            d = 1
    vg = (math.sin(a) + 1) / 2.0
    vd = 1 - vg
    vg = math.sin(vg * math.pi / 2.0)
    vd = math.sin(vd * math.pi / 2.0)
    if math.cos(a) < 0:  # behind
        if no_distance:
            k = 1.3
        else:
            k = 2.0  # TODO: attenuate less? (especially in overhead view)
        vg /= k
        vd /= k
    vg = min(vg * volume / d, 1)
    vd = min(vd * volume / d, 1)
    return vg, vd


def find_idle_channel():
    # because pygame.mixer.find_channel() doesn't work
    # (it can return the reserved channel 0)
    # Also leave the last channel free for VoiceChannel parallel-ops SFX.
    n_ch = pygame.mixer.get_num_channels()
    end = n_ch - 1 if n_ch > 2 else n_ch
    for n in range(1, end):  # avoid channel 0 (and last when reserved)
        if not pygame.mixer.Channel(n).get_busy():
            return pygame.mixer.Channel(n)


class SoundSource:

    channel = None
    previous_vol = (0, 0)
    ended = False
    loop = 0

    def __init__(self, s, v, x, y, priority, limit=0, ambient=False):
        self.sound = s
        self.v = v
        self.x = x
        self.y = y
        self.priority = priority
        self.ambient = ambient
        if self.sound is None:
            self.ended = True
        elif psounds.should_be_played(self.sound, limit):
            self._start()

    def _start(self):
        if not self._volume_too_low():
            self.channel = psounds.find_a_channel(self.priority)
            if self.channel is not None:
                self.channel.stop()
                self._update_volume(force=True)
                self.channel.play(self.sound, self.loop)
                self.channel.set_endevent(pygame.locals.USEREVENT + 1)
        if self.is_playing():
            psounds.remember_start_time(self.sound)

    def is_playing(self):
        return (
            self.channel is not None
            and self.channel.get_busy()
            and self.channel.get_sound() == self.sound
        )

    def _volume_too_low(self):
        return max(psounds.get_stereo_volume(self)) < 0.02

    def _update_volume(self, force=False):
        if self._volume_too_low():
            self.channel.stop()
            self.channel = None
        else:
            if self.ambient:
                vol = self.ambient_volume()
            else:
                vol = psounds.get_stereo_volume(self)
            if force or vol != self.previous_vol:
                self.channel.set_volume(vol[0] * sfx_volume, vol[1] * sfx_volume)
                self.previous_vol = vol

    def update(self):
        if self.ended:
            return
        if self.is_playing():
            self._update_volume()
        else:
            self.stop()

    def move(self, x, y):
        if self.ended:
            return
        if (x, y) != (self.x, self.y):
            self.x = x
            self.y = y
            self.update()

    def stop(self):
        if self.is_playing():
            self.channel.stop()
            self.channel = None
        self.ended = True

    def __getstate__(self):
        state = self.__dict__.copy()
        state["channel"] = None
        return state

    def ambient_volume(self):
        return random.random(), random.random()


class LoopingSoundSource(SoundSource):

    loop = -1

    def update(self):
        if self.ended:
            return
        if self.is_playing():
            self._update_volume()
        else:
            self._start()

    def ambient_volume(self):
        return 1, 1


def stop(stop_voice_too=True):
    psounds.stop()
    if stop_voice_too:
        pygame.mixer.stop()
        tts.stop()
    else:  # stop every channel except channel 0 (voice channel)
        for _id in range(1, pygame.mixer.get_num_channels()):
            pygame.mixer.Channel(_id).stop()


class SoundManager:

    listener = None
    _sources: List[SoundSource] = []
    _start_time: Dict[Sound, float] = {}

    def remember_start_time(self, sound):
        self._start_time[sound] = time.time()

    def should_be_played(self, sound, limit):
        return self._start_time.get(sound, 0) + limit < time.time()

    def find_a_channel(self, priority):
        c = find_idle_channel()
        if c is None:
            playing = [
                s for s in self._sources if s.is_playing() and s.priority < priority
            ]
            if playing:
                playing = sorted(
                    playing, key=lambda x: (x.priority, max(x.previous_vol))
                )
                c = playing[0].channel
                c.stop()
                return c
        else:
            if c.get_endevent() == pygame.locals.USEREVENT:
                warning("find_channel() have chosen the reserved channel!")
            return c

    def get_stereo_volume(self, source):
        if self.listener.immersion:
            flattening_factor = 1.0
        else:
            flattening_factor = parameters.d.get("flattening_factor", 2.0)
            self.listener.o = 90
        return stereo(
            self.listener.x,
            self.listener.y / flattening_factor,
            source.x,
            source.y / flattening_factor,
            self.listener.o,
            source.v,
        )

    def play(self, *args, **keywords):
        s = SoundSource(*args, **keywords)
        if s.is_playing():
            self._sources.append(s)
            return s

    def play_loop(self, *args, **keywords):
        s = LoopingSoundSource(*args, **keywords)
        if not s.ended:
            self._sources.append(s)
            return s

    def play_stereo(self, s, vol=1, limit=0):
        """play a stereo sound (not a positional sound)"""
        if s is not None:
            if not self.should_be_played(s, limit):
                return
            c = self.find_a_channel(priority=10)
            if c is not None:
                c.play(s)
                if isinstance(vol, tuple):
                    c.set_volume(vol[0] * sfx_volume, vol[1] * sfx_volume)
                else:
                    c.set_volume(vol * sfx_volume)
                self.remember_start_time(s)

    def update(self):
        for s in self._sources[:]:
            s.update()
            if s.ended:
                self._sources.remove(s)
        if parameters.d.get("debug_channels", False):
            for n, s in sorted(
                [
                    (
                        n,
                        pygame.mixer.Channel(n).get_sound().name
                        if pygame.mixer.Channel(n).get_busy()
                        else "    ",
                    )
                    for n in range(pygame.mixer.get_num_channels())
                ]
            ):
                print(f"{n}:{s}", end=" ")
            print()

    def stop(self):
        for s in self._sources:
            s.stop()
        


def play_music(music_id, loop=True, fade_ms=music_fade_time):
    """播放背景音乐
    
    Args:
        music_id: 音乐ID或文件路径
        loop: 是否循环播放
        fade_ms: 淡入时间(毫秒)
    """
    global current_music, music_enabled
    
    # 如果音乐已关闭，则不执行任何操作
    if not music_enabled:
        return
    
    # 如果已经在播放相同的音乐，则不重新播放
    if current_music == music_id:
        return
    
    # 找到音乐文件
    music_file = _find_music_file(music_id)
    if not music_file:
        return
    
    # 停止当前音乐（使用传入的淡出时间）
    stop_music(fade_ms=fade_ms)
    
    try:
        # 加载并播放新音乐（使用传入的淡入时间）
        pygame.mixer.music.load(music_file)
        if loop:
            pygame.mixer.music.play(-1, 0.0, fade_ms)
        else:
            pygame.mixer.music.play(0, 0.0, fade_ms)
        pygame.mixer.music.set_volume(music_volume)
        current_music = music_id
    except Exception as e:
        from .log import exception
        exception("无法播放音乐文件: " + music_file)
        # 出错时清除当前音乐状态
        current_music = None

def _find_music_file(music_id):
    """在不同位置查找音乐文件
    
    Args:
        music_id: 音乐ID或文件路径
        
    Returns:
        str: 找到的音乐文件路径，如果未找到返回None
    """
    import os
    
    debug(f"尝试查找音乐: {music_id}")
    
    # 检查缓存中是否已存在
    if music_id in _music_cache:
        debug(f"从缓存中找到音乐: {_music_cache[music_id]}")
        # 验证缓存的文件是否仍然存在
        if os.path.exists(_music_cache[music_id]):
            return _music_cache[music_id]
        else:
            # 从缓存中移除无效条目
            debug(f"缓存中的音乐文件不存在，移除缓存: {_music_cache[music_id]}")
            del _music_cache[music_id]
    
    # 如果是绝对路径且文件存在，直接返回
    if os.path.isabs(music_id) and os.path.exists(music_id):
        debug(f"找到绝对路径音乐: {music_id}")
        _music_cache[music_id] = music_id
        return music_id
        
    # 如果是相对路径且文件直接存在，直接返回
    if os.path.exists(music_id):
        debug(f"找到相对路径音乐: {music_id}")
        abs_path = os.path.abspath(music_id)
        _music_cache[music_id] = abs_path
        return abs_path
    
    try:
        from .. import config
        from ..lib.resource import res
        active_mod = config.mods.strip() if hasattr(config, "mods") else ""
        debug(f"当前激活的mod: {active_mod}")
        
        # 获取当前活动的地图
        active_map = None
        if hasattr(res, '_map') and res._map:
            active_map = res._map
            debug(f"当前活动的地图: {active_map.name}")
        
        # 获取当前活动的战役
        active_campaign = None
        if hasattr(res, '_campaign') and res._campaign:
            active_campaign = res._campaign
            debug(f"当前活动的战役: {active_campaign.name}")
    except Exception as e:
        debug(f"获取mod或地图信息时出错: {e}")
        active_mod = ""
        active_map = None
        active_campaign = None
    
    # 确定是简单ID还是路径
    is_simple_id = os.path.basename(music_id) == music_id and not os.path.isabs(music_id)
    debug(f"音乐{'是' if is_simple_id else '不是'}简单ID")
    
    # 获取当前工作目录
    cwd = os.getcwd()
    debug(f"当前工作目录: {cwd}")
    
    # 构建搜索路径列表和实际的完整路径列表
    search_paths = []
    full_paths = []
    
    if is_simple_id:
        # 简单ID的搜索逻辑
        base_name = music_id
        
        # 检查是否是特殊的音乐文件（胜利、失败音效）
        is_victory_defeat_sound = False
        special_sound_ids = ["victory", "defeat", "gamefail", "combatvictory", "combatdefeat"]
        
        for special_id in special_sound_ids:
            if base_name == special_id or base_name.startswith(special_id):
                is_victory_defeat_sound = True
                break
        
        # 首先检查当前活动的地图中的音乐/音效文件（仅当地图与当前mod关联时）
        if active_map:
            # 检查地图是否与当前mod关联
            map_belongs_to_current_mod = False
            if hasattr(active_map, 'mod_specific') and active_map.mod_specific:
                if hasattr(active_map, 'mod_name') and active_map.mod_name == active_mod:
                    map_belongs_to_current_mod = True
                    debug(f"地图 {active_map.name} 属于当前mod: {active_mod}")
            
            # 如果地图不属于任何mod或属于当前mod，则检查地图的音乐/音效
            if not hasattr(active_map, 'mod_specific') or map_belongs_to_current_mod:
                # 检查地图的音乐/音效路径
                map_package = active_map.resources if hasattr(active_map, 'resources') else None
                
                if map_package:
                    # 对于胜利、失败音效，查找地图的ui/sounds目录
                    if is_victory_defeat_sound:
                        for ext in ['.ogg', '.mp3', '.wav']:
                            map_sounds_path = os.path.join("ui", "sounds", f"{base_name}{ext}")
                            # 使用Path对象构建完整路径
                            try:
                                map_path = os.path.join(str(map_package), map_sounds_path)
                                if os.path.exists(map_path):
                                    debug(f"在地图目录中找到胜利/失败音效: {map_path}")
                                    _music_cache[music_id] = map_path
                                    return map_path
                            except Exception as e:
                                debug(f"检查地图音效路径失败: {e}")
                    
                    # 对于游戏音乐，查找地图的ui/music目录
                    for ext in MUSIC_FORMATS:
                        map_music_path = os.path.join("ui", "music", f"{base_name}{ext}")
                        # 使用Path对象构建完整路径
                        try:
                            map_path = os.path.join(str(map_package), map_music_path)
                            if os.path.exists(map_path):
                                debug(f"在地图目录中找到音乐: {map_path}")
                                _music_cache[music_id] = map_path
                                return map_path
                        except Exception as e:
                            debug(f"检查地图音乐路径失败: {e}")
        
        # 然后检查当前活动的战役中的音乐/音效文件（仅当战役与当前mod关联时）
        if active_campaign:
            # 检查战役是否与当前mod关联
            campaign_belongs_to_current_mod = False
            if hasattr(active_campaign, 'mod_specific') and active_campaign.mod_specific:
                if hasattr(active_campaign, 'mod_name') and active_campaign.mod_name == active_mod:
                    campaign_belongs_to_current_mod = True
                    debug(f"战役 {active_campaign.name} 属于当前mod: {active_mod}")
            
            # 如果战役不属于任何mod或属于当前mod，则检查战役的音乐/音效
            if not hasattr(active_campaign, 'mod_specific') or campaign_belongs_to_current_mod:
                # 检查战役的音乐/音效路径
                campaign_package = active_campaign.resources if hasattr(active_campaign, 'resources') else None
                
                if campaign_package:
                    # 对于胜利、失败音效，查找战役的ui/sounds目录
                    if is_victory_defeat_sound:
                        for ext in ['.ogg', '.mp3', '.wav']:
                            campaign_sounds_path = os.path.join("ui", "sounds", f"{base_name}{ext}")
                            # 使用Path对象构建完整路径
                            try:
                                campaign_path = os.path.join(str(campaign_package), campaign_sounds_path)
                                if os.path.exists(campaign_path):
                                    debug(f"在战役目录中找到胜利/失败音效: {campaign_path}")
                                    _music_cache[music_id] = campaign_path
                                    return campaign_path
                            except Exception as e:
                                debug(f"检查战役音效路径失败: {e}")
                    
                    # 对于游戏音乐，查找战役的ui/music目录
                    for ext in MUSIC_FORMATS:
                        campaign_music_path = os.path.join("ui", "music", f"{base_name}{ext}")
                        # 使用Path对象构建完整路径
                        try:
                            campaign_path = os.path.join(str(campaign_package), campaign_music_path)
                            if os.path.exists(campaign_path):
                                debug(f"在战役目录中找到音乐: {campaign_path}")
                                _music_cache[music_id] = campaign_path
                                return campaign_path
                        except Exception as e:
                            debug(f"检查战役音乐路径失败: {e}")
        
        # 如果是胜利/失败音效，优先搜索sounds目录
        if is_victory_defeat_sound:
            debug(f"检测到胜利/失败音效: {base_name}")
            
            # 1. 检查激活的mod的sounds目录（仅当有激活的mod时）
            if active_mod:
                for ext in ['.ogg', '.mp3', '.wav']:
                    active_mod_sounds_path = os.path.join("mods", active_mod, "ui", "sounds", f"{base_name}{ext}")
                    # 直接检查文件是否存在
                    full_path = os.path.join(cwd, active_mod_sounds_path)
                    if os.path.exists(full_path):
                        debug(f"在当前mod目录中找到胜利/失败音效: {full_path}")
                        _music_cache[music_id] = full_path
                        return full_path
            
            # 2. 仅当没有激活的mod时，检查游戏根目录的sounds目录
            if not active_mod:
                for ext in ['.ogg', '.mp3', '.wav']:
                    game_sounds_path = os.path.join("ui", "sounds", f"{base_name}{ext}")
                    full_path = os.path.join(cwd, game_sounds_path)
                    if os.path.exists(full_path):
                        debug(f"在根目录中找到胜利/失败音效: {full_path}")
                        _music_cache[music_id] = full_path
                        return full_path
                    
                    # 添加对res/ui/sounds的支持
                    res_sounds_path = os.path.join("res", "ui", "sounds", f"{base_name}{ext}")
                    full_path = os.path.join(cwd, res_sounds_path)
                    if os.path.exists(full_path):
                        debug(f"在res目录中找到胜利/失败音效: {full_path}")
                        _music_cache[music_id] = full_path
                        return full_path
                    
                    # 添加对campaigns/default/ui/sounds的支持
                    default_campaign_sounds_path = os.path.join("campaigns", "default", "ui", "sounds", f"{base_name}{ext}")
                    full_path = os.path.join(cwd, default_campaign_sounds_path)
                    if os.path.exists(full_path):
                        debug(f"在默认战役目录中找到胜利/失败音效: {full_path}")
                        _music_cache[music_id] = full_path
                        return full_path
        
        # 接下来查找音乐目录 (ui/music/)
        # 1. 优先检查当前激活的mod的music目录
        if active_mod:
            for ext in MUSIC_FORMATS:
                mod_music_path = os.path.join("mods", active_mod, "ui", "music", f"{base_name}{ext}")
                full_path = os.path.join(cwd, mod_music_path)
                if os.path.exists(full_path):
                    debug(f"在当前mod目录中找到音乐: {full_path}")
                    _music_cache[music_id] = full_path
                    return full_path
        
        # 2. 仅当没有激活的mod时，再检查游戏根目录的music目录
        if not active_mod:
            for ext in MUSIC_FORMATS:
                # 游戏根目录的music目录
                game_music_path = os.path.join("ui", "music", f"{base_name}{ext}")
                full_path = os.path.join(cwd, game_music_path)
                if os.path.exists(full_path):
                    debug(f"在根目录中找到音乐: {full_path}")
                    _music_cache[music_id] = full_path
                    return full_path
                
                # 添加对res/ui/music的支持
                res_music_path = os.path.join("res", "ui", "music", f"{base_name}{ext}")
                full_path = os.path.join(cwd, res_music_path)
                if os.path.exists(full_path):
                    debug(f"在res目录中找到音乐: {full_path}")
                    _music_cache[music_id] = full_path
                    return full_path
                
                # 添加对campaigns/default/ui/music的支持
                default_campaign_music_path = os.path.join("campaigns", "default", "ui", "music", f"{base_name}{ext}")
                full_path = os.path.join(cwd, default_campaign_music_path)
                if os.path.exists(full_path):
                    debug(f"在默认战役目录中找到音乐: {full_path}")
                    _music_cache[music_id] = full_path
                    return full_path
        
        # 最后，查找effects目录（仅当没有找到其他文件时）
        # 1. 优先检查当前激活的mod的effects目录
        if active_mod:
            for ext in MUSIC_FORMATS:
                active_mod_effects_path = os.path.join("mods", active_mod, "ui", "effects", f"{base_name}{ext}")
                full_path = os.path.join(cwd, active_mod_effects_path)
                if os.path.exists(full_path):
                    debug(f"在当前mod的effects目录中找到音效: {full_path}")
                    _music_cache[music_id] = full_path
                    return full_path
        
        # 2. 仅当没有激活的mod时，检查游戏根目录的effects目录
        if not active_mod:
            for ext in MUSIC_FORMATS:
                # 检查res/ui/effects/目录
                res_effects_path = os.path.join("res", "ui", "effects", f"{base_name}{ext}")
                full_path = os.path.join(cwd, res_effects_path)
                if os.path.exists(full_path):
                    debug(f"在res的effects目录中找到音效: {full_path}")
                    _music_cache[music_id] = full_path
                    return full_path
                
                # 检查ui/effects/目录
                effects_path = os.path.join("ui", "effects", f"{base_name}{ext}")
                full_path = os.path.join(cwd, effects_path)
                if os.path.exists(full_path):
                    debug(f"在根目录的effects目录中找到音效: {full_path}")
                    _music_cache[music_id] = full_path
                    return full_path
                
                # 检查campaigns/default/ui/effects的支持
                default_campaign_effects_path = os.path.join("campaigns", "default", "ui", "effects", f"{base_name}{ext}")
                full_path = os.path.join(cwd, default_campaign_effects_path)
                if os.path.exists(full_path):
                    debug(f"在默认战役的effects目录中找到音效: {full_path}")
                    _music_cache[music_id] = full_path
                    return full_path
    else:
        # 如果不是简单ID，而是一个路径，解析后再搜索
        path_components = os.path.split(music_id)
        base_name = path_components[-1]
        
        # 尝试直接解析路径
        if os.path.exists(music_id):
            _music_cache[music_id] = music_id
            return music_id
        
        # 分离文件名和扩展名
        base_without_ext, ext = os.path.splitext(base_name)
        
        # 判断当前路径是否位于mod目录下
        mod_path_match = False
        if active_mod and "mods/" + active_mod in music_id:
            mod_path_match = True
        
        # 对于属于mod的路径，仅在对应mod激活时查找
        if mod_path_match:
            if active_mod and "mods/" + active_mod in music_id:
                # 尝试直接查找完整路径
                full_path = os.path.join(cwd, music_id)
                if os.path.exists(full_path):
                    debug(f"找到mod中的音乐文件: {full_path}")
                    _music_cache[music_id] = full_path
                    return full_path
                
                # 如果未找到，可能是因为扩展名不匹配，尝试其他扩展名
                if ext:
                    # 文件有扩展名，但可能不正确
                    for format_ext in MUSIC_FORMATS:
                        if ext.lower() != format_ext:
                            new_path = music_id.replace(ext, format_ext)
                            full_path = os.path.join(cwd, new_path)
                            if os.path.exists(full_path):
                                debug(f"找到扩展名不同的mod音乐文件: {full_path}")
                                _music_cache[music_id] = full_path
                                return full_path
                else:
                    # 文件没有扩展名，尝试添加所有可能的扩展名
                    for format_ext in MUSIC_FORMATS:
                        new_path = music_id + format_ext
                        full_path = os.path.join(cwd, new_path)
                        if os.path.exists(full_path):
                            debug(f"找到添加扩展名后的mod音乐文件: {full_path}")
                            _music_cache[music_id] = full_path
                            return full_path
        else:
            # 对于非mod路径，仅在没有激活mod时查找
            if not active_mod:
                # 尝试直接查找完整路径
                full_path = os.path.join(cwd, music_id)
                if os.path.exists(full_path):
                    debug(f"找到非mod音乐文件: {full_path}")
                    _music_cache[music_id] = full_path
                    return full_path
                
                # 如果未找到，可能是因为扩展名不匹配，尝试其他扩展名
                if ext:
                    # 文件有扩展名，但可能不正确
                    for format_ext in MUSIC_FORMATS:
                        if ext.lower() != format_ext:
                            new_path = music_id.replace(ext, format_ext)
                            full_path = os.path.join(cwd, new_path)
                            if os.path.exists(full_path):
                                debug(f"找到扩展名不同的非mod音乐文件: {full_path}")
                                _music_cache[music_id] = full_path
                                return full_path
                else:
                    # 文件没有扩展名，尝试添加所有可能的扩展名
                    for format_ext in MUSIC_FORMATS:
                        new_path = music_id + format_ext
                        full_path = os.path.join(cwd, new_path)
                        if os.path.exists(full_path):
                            debug(f"找到添加扩展名后的非mod音乐文件: {full_path}")
                            _music_cache[music_id] = full_path
                            return full_path
    
    # 如果找不到，并且当前使用的是mod，尝试获取mod默认的音乐作为后备
    if active_mod and is_simple_id:
        debug(f"在mod {active_mod} 中未找到音乐 {music_id}，尝试回退到默认音乐")
        
        # 对于各种特定的音乐类型，使用对应的默认值
        default_id = None
            
        if default_id and default_id != music_id:
            # 递归调用，但避免无限循环
            default_path = _find_music_file(default_id)
            if default_path:
                debug(f"找到默认音乐: {default_path}")
                _music_cache[music_id] = default_path
                return default_path
    
    # 如果找不到，返回None
    debug(f"找不到音乐文件: {music_id}")
    return None

def stop_music(fade_ms=music_fade_time):
    """停止当前播放的背景音乐
    
    Args:
        fade_ms: 淡出时间(毫秒)
    """
    global current_music
    
    if pygame.mixer.music.get_busy():
        # 如果需要立即停止，则不使用淡出效果
        if fade_ms <= 0:
            pygame.mixer.music.stop()
        else:
            pygame.mixer.music.fadeout(fade_ms)
    
    current_music = None

def set_music_volume(volume):
    """设置音乐音量
    
    Args:
        volume: 音量大小(0.0-1.0)
    """
    global music_volume
    
    music_volume = max(0.0, min(1.0, volume))
    if pygame.mixer.music.get_busy():
        pygame.mixer.music.set_volume(music_volume)

def adjust_music_volume(delta):
    """调整音乐音量
    
    Args:
        delta: 音量变化值(-1.0 ~ 1.0)
        
    Returns:
        int: 百分比形式的当前音量(0-100)
    """
    global music_volume
    
    # 向主音量处理方式看齐，使用0.1的固定增量
    music_volume = min(1, max(0, music_volume + 0.1 * delta))
    
    # 如果音乐正在播放，立即应用新音量
    if pygame.mixer.music.get_busy():
        pygame.mixer.music.set_volume(music_volume)
    
    # 返回百分比形式的音量值
    return int(music_volume * 100)

def adjust_sfx_volume(delta):
    """Adjust positional/stereo SFX volume."""
    global sfx_volume

    sfx_volume = min(1, max(0, sfx_volume + 0.1 * delta))
    for source in psounds._sources:
        if source.is_playing():
            source._update_volume(force=True)
    return int(sfx_volume * 100)

def toggle_music():
    """切换音乐开关状态"""
    global music_enabled, current_music, in_battle

    
    # 记录当前播放的音乐，以便恢复时使用
    previous_music = current_music
    
    music_enabled = not music_enabled
    
    if not music_enabled:
        # 使用全局淡出时间
        stop_music(fade_ms=music_fade_time)
    else:
        # 检查是否在菜单中，如果是则重置战斗状态
        if current_menu_type in ["main", "campaign", "game_creation", "server_lobby"]:
            # 在菜单中时，应该重置战斗状态
            in_battle = False
            
        # 根据当前状态播放相应的音乐
        if in_battle:
            # 如果处于战斗状态，播放战斗音乐
            play_battle_music()
        elif current_menu_type == "campaign":
            play_campaign_music()
        elif current_menu_type == "game_creation":
            play_game_creation_music()
        elif current_menu_type == "server_lobby":
            play_server_lobby_music()
        else:
            # 默认播放主菜单音乐
            play_menu_music()
    
    return music_enabled

def play_menu_music():
    """播放主菜单音乐"""
    global menu_music, current_menu_type
    
    # 设置当前菜单类型
    current_menu_type = "main"
    
    if menu_music:
        # 检查菜单音乐文件是否存在
        if _find_music_file(menu_music):
            play_music(menu_music)
        else:
            # 如果未找到配置的菜单音乐，不播放任何音乐
            debug(f"未找到主菜单音乐文件: {menu_music}，不播放任何音乐")
            stop_music()
    else:
        # 如果未配置菜单音乐，不播放任何音乐
        debug("未配置主菜单音乐，不播放任何音乐")
        stop_music()

def play_campaign_music():
    """播放战役菜单音乐"""
    global campaign_music, menu_music, current_menu_type
    
    # 设置当前菜单类型
    current_menu_type = "campaign"
    
    # 如果有战役音乐，则播放
    if campaign_music:
        # 检查campaign_music对应的文件是否存在
        if _find_music_file(campaign_music):
            play_music(campaign_music)
        else:
            # 如果没找到当前mod的战役菜单音乐，则使用主菜单音乐
            debug(f"未找到战役菜单音乐文件: {campaign_music}，使用主菜单音乐")
            # 如果主菜单音乐已配置且存在，则使用它
            if menu_music and _find_music_file(menu_music):
                play_music(menu_music)
            else:
                debug("未找到可用的菜单音乐，不播放任何音乐")
                stop_music()
    else:
        # 如果未配置战役音乐，则使用主菜单音乐
        debug("未配置战役菜单音乐，使用主菜单音乐")
        # 如果主菜单音乐已配置且存在，则使用它
        if menu_music and _find_music_file(menu_music):
            play_music(menu_music)
        else:
            debug("未找到可用的菜单音乐，不播放任何音乐")
            stop_music()

def play_game_creation_music():
    """播放创建游戏菜单音乐"""
    global game_creation_music, menu_music, current_menu_type
    
    # 设置当前菜单类型
    current_menu_type = "game_creation"
    
    # 如果有创建游戏音乐，则播放
    if game_creation_music:
        # 检查game_creation_music对应的文件是否存在
        if _find_music_file(game_creation_music):
            play_music(game_creation_music)
        else:
            # 如果没找到当前mod的创建游戏菜单音乐，则使用主菜单音乐
            debug(f"未找到创建游戏菜单音乐文件: {game_creation_music}，使用主菜单音乐")
            # 如果主菜单音乐已配置且存在，则使用它
            if menu_music and _find_music_file(menu_music):
                play_music(menu_music)
            else:
                debug("未找到可用的菜单音乐，不播放任何音乐")
                stop_music()
    else:
        # 如果未配置创建游戏音乐，则使用主菜单音乐
        debug("未配置创建游戏菜单音乐，使用主菜单音乐")
        # 如果主菜单音乐已配置且存在，则使用它
        if menu_music and _find_music_file(menu_music):
            play_music(menu_music)
        else:
            debug("未找到可用的菜单音乐，不播放任何音乐")
            stop_music()

def play_server_lobby_music():
    """播放服务器大厅菜单音乐"""
    global server_lobby_music, menu_music, current_menu_type
    
    # 设置当前菜单类型
    current_menu_type = "server_lobby"
    
    # 如果有服务器大厅音乐，则播放
    if server_lobby_music:
        # 检查server_lobby_music对应的文件是否存在
        if _find_music_file(server_lobby_music):
            play_music(server_lobby_music)
        else:
            # 如果没找到当前mod的服务器大厅菜单音乐，则使用主菜单音乐
            debug(f"未找到服务器大厅菜单音乐文件: {server_lobby_music}，使用主菜单音乐")
            # 如果主菜单音乐已配置且存在，则使用它
            if menu_music and _find_music_file(menu_music):
                play_music(menu_music)
            else:
                debug("未找到可用的菜单音乐，不播放任何音乐")
                stop_music()
    else:
        # 如果未配置服务器大厅音乐，则使用主菜单音乐
        debug("未配置服务器大厅菜单音乐，使用主菜单音乐")
        # 如果主菜单音乐已配置且存在，则使用它
        if menu_music and _find_music_file(menu_music):
            play_music(menu_music)
        else:
            debug("未找到可用的菜单音乐，不播放任何音乐")
            stop_music()

def play_game_music(map_music=None, faction_music=None):
    """播放游戏内背景音乐
    
    Args:
        map_music: 地图指定的背景音乐，如果提供则优先使用
        faction_music: 阵营专属背景音乐，优先级最高
    """
    global game_music, in_battle, current_player_faction
    
    # 如果当前处于战斗状态，不改变音乐
    if in_battle:
        return
    
    debug(f"尝试播放游戏背景音乐，阵营指定: {faction_music}, 地图指定: {map_music}, 全局设置: {game_music}")
    
    # 检查是否处于战役游戏中
    is_campaign_game = False
    try:
        from ..lib.resource import res
        is_campaign_game = hasattr(res, '_campaign') and res._campaign is not None
    except Exception as e:
        debug(f"检查是否处于战役游戏时出错: {e}")
    
    # 如果没有提供faction_music，但有current_player_faction，尝试从style中获取
    if not faction_music and current_player_faction and not is_campaign_game:
        try:
            from ..definitions import style
            if hasattr(style, 'faction_music_settings') and current_player_faction in style.faction_music_settings:
                faction_music = style.faction_music_settings[current_player_faction]
                debug(f"使用全局阵营变量获取阵营 {current_player_faction} 的专属音乐: {faction_music}")
        except Exception as e:
            debug(f"尝试从style获取阵营音乐时出错: {e}")
    
    # 尝试从当前地图或战役加载特定的音乐
    try:
        from ..lib.resource import res
        active_map = res._map if hasattr(res, '_map') else None
        active_campaign = res._campaign if hasattr(res, '_campaign') else None
        
        # 检查当前地图中是否有专用的游戏音乐
        if active_map and not map_music:
            try:
                map_package = active_map.resources if hasattr(active_map, 'resources') else None
                if map_package:
                    # 尝试查找地图专用的游戏音乐
                    map_music_found = False
                    for ext in MUSIC_FORMATS:
                        map_music_path = os.path.join(str(map_package), "ui", "music", f"game{ext}")
                        if os.path.exists(map_music_path):
                            debug(f"在地图目录中找到game音乐: {map_music_path}")
                            map_music = map_music_path
                            map_music_found = True
                            break
                    
                    if not map_music_found:
                        # 尝试使用与地图同名的音乐
                        for ext in MUSIC_FORMATS:
                            map_name_music_path = os.path.join(str(map_package), "ui", "music", f"{active_map.name}{ext}")
                            if os.path.exists(map_name_music_path):
                                debug(f"在地图目录中找到与地图同名的音乐: {map_name_music_path}")
                                map_music = map_name_music_path
                                break
            except Exception as e:
                debug(f"检查地图音乐时出错: {e}")
        
        # 检查当前战役中是否有专用的游戏音乐
        if active_campaign and not map_music:
            try:
                campaign_package = active_campaign.resources if hasattr(active_campaign, 'resources') else None
                if campaign_package:
                    # 尝试查找战役专用的游戏音乐
                    campaign_music_found = False
                    for ext in MUSIC_FORMATS:
                        campaign_music_path = os.path.join(str(campaign_package), "ui", "music", f"game{ext}")
                        if os.path.exists(campaign_music_path):
                            debug(f"在战役目录中找到game音乐: {campaign_music_path}")
                            map_music = campaign_music_path
                            campaign_music_found = True
                            break
                    
                    if not campaign_music_found:
                        # 尝试使用与战役同名的音乐
                        for ext in MUSIC_FORMATS:
                            campaign_name_music_path = os.path.join(str(campaign_package), "ui", "music", f"{active_campaign.name}{ext}")
                            if os.path.exists(campaign_name_music_path):
                                debug(f"在战役目录中找到与战役同名的音乐: {campaign_name_music_path}")
                                map_music = campaign_name_music_path
                                break
            except Exception as e:
                debug(f"检查战役音乐时出错: {e}")
    except Exception as e:
        debug(f"尝试获取地图或战役音乐时出错: {e}")
    
    # 在战役游戏中：始终优先使用game_music，除非在地图中有专门指定
    if is_campaign_game:
        # 如果是战役游戏且有地图专属音乐，使用地图音乐，否则使用game_music
        if map_music:
            debug(f"战役游戏中使用地图专属音乐: {map_music}")
            play_music(map_music)
        # 使用全局game_music
        elif game_music:
            debug(f"战役游戏中使用全局游戏音乐: {game_music}")
            # 检查音乐文件是否存在，不存在则不播放
            if _find_music_file(game_music):
                play_music(game_music)
            else:
                debug(f"未找到游戏音乐文件: {game_music}，不播放任何音乐")
                stop_music()
        # 如果没有设置任何音乐，则静默不播放
        else:
            debug("未配置游戏音乐，不播放任何音乐")
            stop_music()
    else:
        # 非战役游戏按正常优先级：阵营专属音乐 > 地图专属音乐 > 全局游戏音乐
        # 优先使用阵营专属音乐（最高优先级）
        if faction_music:
            faction_music_file = _find_music_file(faction_music)
            if faction_music_file:
                debug(f"播放阵营专属音乐: {faction_music}")
                play_music(faction_music)
                return
            else:
                debug(f"未找到阵营专属音乐文件: {faction_music}，尝试其他音乐")
        
        # 其次使用地图指定的背景音乐
        if map_music:
            play_music(map_music)
        # 最后使用style.txt中配置的全局游戏音乐
        elif game_music:
            # 检查音乐文件是否存在，不存在则不播放
            if _find_music_file(game_music):
                play_music(game_music)
            else:
                debug(f"未找到游戏音乐文件: {game_music}，不播放任何音乐")
                stop_music()
        # 如果没有设置任何音乐，则静默不播放
        else:
            debug("未配置游戏音乐，不播放任何音乐")
            stop_music()

def set_menu_music(music_id):
    """设置主菜单音乐
    
    Args:
        music_id: 音乐ID或文件路径
    """
    global menu_music
    
    menu_music = music_id

def set_campaign_music(music_id):
    """设置战役菜单音乐
    
    Args:
        music_id: 音乐ID或文件路径
    """
    global campaign_music
    
    campaign_music = music_id

def set_game_creation_music(music_id):
    """设置创建游戏菜单音乐
    
    Args:
        music_id: 音乐ID或文件路径
    """
    global game_creation_music
    
    game_creation_music = music_id

def set_server_lobby_music(music_id):
    """设置服务器大厅菜单音乐
    
    Args:
        music_id: 音乐ID或文件路径
    """
    global server_lobby_music
    
    server_lobby_music = music_id

def set_game_music(music_id):
    """设置游戏全局背景音乐ID"""
    global game_music
    game_music = music_id

def set_faction_music(music_id):
    """设置阵营专属背景音乐ID"""
    global faction_music
    faction_music = music_id

def get_music_status():
    """获取音乐状态
    
    Returns:
        dict: 包含当前音乐状态的字典
    """
    return {
        "enabled": music_enabled,
        "volume": music_volume,
        "sfx_volume": sfx_volume,
        "current_music": current_music,
        "menu_music": menu_music,
        "campaign_music": campaign_music,
        "game_creation_music": game_creation_music,
        "server_lobby_music": server_lobby_music,
        "faction_music": faction_music,
        "game_music": game_music,
        "battle_music": battle_music,
        "faction_battle_music": faction_battle_music,
        "victory_sound": victory_sound,
        "defeat_sound": defeat_sound,
        "in_battle": in_battle,
        "current_player_faction": current_player_faction
    }

def clear_music_cache():
    """清除音乐缓存"""
    global _music_cache
    _music_cache.clear()

psounds = SoundManager()  # positional sounds (3D)
main_volume = 0.5
sfx_volume = 0.5
voice_volume = 1.0  # for sounds played on the voice channel (not for the TTS)


def init(num_channels, mixer_buffer=2048, frequency=44100):
    """Initialize pygame mixer.

    mixer_buffer: samples per buffer (512–8192). Larger = less stutter, more latency.
    frequency: output sample rate in Hz (typically 44100).
    """
    pygame.mixer.pre_init(frequency, -16, 2, mixer_buffer)
    pygame.init()
    pygame.mixer.set_reserved(1)
    pygame.mixer.set_num_channels(num_channels)
    
    # 不再设置默认音乐值，完全依赖style.txt中的设置
    # 全局变量定义在文件开头，这里不再重新赋默认值

def set_player_faction(faction):
    """设置当前玩家的阵营，用于选择阵营专属音乐
    
    Args:
        faction: 阵营ID或对象
    """
    global current_player_faction
    
    # 如果阵营是对象且有type_name属性，获取type_name
    if faction and hasattr(faction, "type_name"):
        current_player_faction = faction.type_name
    else:
        current_player_faction = faction
    
    from .log import debug
    debug(f"设置当前玩家阵营为: {current_player_faction}")

def play_battle_music(map_battle_music=None):
    """播放战斗音乐
    
    Args:
        map_battle_music: 地图指定的战斗音乐，如果提供则优先使用
    """
    global battle_music, faction_battle_music, in_battle, current_player_faction
    
    in_battle = True
    
    debug(f"尝试播放战斗音乐，地图指定: {map_battle_music}, 全局设置: {battle_music}")
    
    # 尝试从当前地图或战役加载特定的战斗音乐
    try:
        from ..lib.resource import res
        active_map = res._map if hasattr(res, '_map') else None
        active_campaign = res._campaign if hasattr(res, '_campaign') else None
        
        # 检查当前地图中是否有专用的战斗音乐
        if active_map and not map_battle_music:
            try:
                map_package = active_map.resources if hasattr(active_map, 'resources') else None
                if map_package:
                    # 尝试查找地图专用的战斗音乐
                    map_battle_found = False
                    for ext in MUSIC_FORMATS:
                        map_battle_path = os.path.join(str(map_package), "ui", "music", f"battle{ext}")
                        if os.path.exists(map_battle_path):
                            debug(f"在地图目录中找到battle音乐: {map_battle_path}")
                            map_battle_music = map_battle_path
                            map_battle_found = True
                            break
                    
                    if not map_battle_found:
                        # 尝试使用与地图同名的战斗音乐
                        for ext in MUSIC_FORMATS:
                            map_name_battle_path = os.path.join(str(map_package), "ui", "music", f"{active_map.name}_battle{ext}")
                            if os.path.exists(map_name_battle_path):
                                debug(f"在地图目录中找到与地图同名的战斗音乐: {map_name_battle_path}")
                                map_battle_music = map_name_battle_path
                                break
            except Exception as e:
                debug(f"检查地图战斗音乐时出错: {e}")
        
        # 检查当前战役中是否有专用的战斗音乐
        if active_campaign and not map_battle_music:
            try:
                campaign_package = active_campaign.resources if hasattr(active_campaign, 'resources') else None
                if campaign_package:
                    # 尝试查找战役专用的战斗音乐
                    campaign_battle_found = False
                    for ext in MUSIC_FORMATS:
                        campaign_battle_path = os.path.join(str(campaign_package), "ui", "music", f"battle{ext}")
                        if os.path.exists(campaign_battle_path):
                            debug(f"在战役目录中找到battle音乐: {campaign_battle_path}")
                            map_battle_music = campaign_battle_path
                            campaign_battle_found = True
                            break
                    
                    if not campaign_battle_found:
                        # 尝试使用与战役同名的战斗音乐
                        for ext in MUSIC_FORMATS:
                            campaign_name_battle_path = os.path.join(str(campaign_package), "ui", "music", f"{active_campaign.name}_battle{ext}")
                            if os.path.exists(campaign_name_battle_path):
                                debug(f"在战役目录中找到与战役同名的战斗音乐: {campaign_name_battle_path}")
                                map_battle_music = campaign_name_battle_path
                                break
            except Exception as e:
                debug(f"检查战役战斗音乐时出错: {e}")
    except Exception as e:
        debug(f"尝试获取地图或战役战斗音乐时出错: {e}")
    
    # 判断是否在战役中
    is_in_campaign = False
    try:
        from ..lib.resource import res
        is_in_campaign = hasattr(res, '_campaign') and res._campaign is not None
    except:
        pass
    
    # 获取当前阵营
    player_faction = current_player_faction
    faction_battle_music = None
    
    try:
        from ..definitions import style
        # 检查是否有阵营专属战斗音乐
        if player_faction and hasattr(style, 'faction_battle_music_settings'):
            faction_battle_key = f"{player_faction}_battle_music"
            debug(f"检查阵营专属战斗音乐: {faction_battle_key}")
            if faction_battle_key in style.faction_battle_music_settings:
                faction_battle_music_path = style.faction_battle_music_settings[faction_battle_key]
                debug(f"找到阵营专属战斗音乐: {faction_battle_music_path} (阵营: {player_faction})")
                faction_battle_music = faction_battle_music_path
            else:
                debug(f"未找到阵营 {player_faction} 的专属战斗音乐")
    except Exception as e:
        debug(f"加载style定义或阵营专属战斗音乐时出错: {e}")
        
    # 优先级: 阵营专属战斗音乐 > 地图战斗音乐 > 全局战斗音乐
    if faction_battle_music:
        # 检查阵营专属战斗音乐文件是否存在
        if _find_music_file(faction_battle_music):
            debug(f"播放阵营专属战斗音乐: {faction_battle_music}")
            play_music(faction_battle_music)
        else:
            debug(f"未找到阵营专属战斗音乐文件: {faction_battle_music}，尝试其他音乐")
            # 如果阵营专属战斗音乐不存在，继续下一个优先级
            if map_battle_music:
                play_music(map_battle_music)
            elif battle_music:
                if _find_music_file(battle_music):
                    play_music(battle_music)
                else:
                    debug(f"未找到战斗音乐文件: {battle_music}，使用游戏音乐")
                    play_game_music()
            else:
                debug("未配置战斗音乐，使用游戏音乐")
                play_game_music()
    # 其次使用地图指定的战斗音乐
    elif map_battle_music:
        play_music(map_battle_music)
    # 最后使用style.txt中配置的全局战斗音乐
    elif battle_music:
        # 检查音乐文件是否存在，不存在则使用游戏音乐
        if _find_music_file(battle_music):
            play_music(battle_music)
        else:
            debug(f"未找到战斗音乐文件: {battle_music}，使用游戏音乐")
            # 继续使用游戏音乐（如果有）
            play_game_music()
    else:
        # 如果没有设置战斗音乐，继续使用游戏音乐
        debug("未配置战斗音乐，使用游戏音乐")
        play_game_music()

def stop_battle_music():
    """停止战斗音乐，恢复到游戏音乐"""
    global in_battle
    
    in_battle = False
    
    # 恢复游戏音乐
    play_game_music()

def set_battle_music(music_id):
    """设置战斗音乐
    
    Args:
        music_id: 音乐ID或文件路径
    """
    global battle_music
    
    battle_music = music_id

def set_faction_battle_music(music_id):
    """设置阵营专属战斗音乐
    
    Args:
        music_id: 音乐ID或文件路径
    """
    global faction_battle_music
    
    faction_battle_music = music_id

def play_victory_sound(map_victory_sound=None):
    """播放胜利音乐
    
    Args:
        map_victory_sound: 地图指定的胜利音乐，如果提供则优先使用
    """
    global victory_sound
    
    debug(f"尝试播放胜利音乐，地图指定: {map_victory_sound}, 全局设置: {victory_sound}")
    
    # 尝试从当前地图或战役加载特定的胜利音效
    try:
        from ..lib.resource import res
        active_map = res._map if hasattr(res, '_map') else None
        active_campaign = res._campaign if hasattr(res, '_campaign') else None
        
        # 检查当前地图中是否有专用的胜利音效
        if active_map and not map_victory_sound:
            try:
                map_package = active_map.resources if hasattr(active_map, 'resources') else None
                if map_package:
                    # 尝试查找地图专用的胜利音效
                    for ext in ['.ogg', '.mp3', '.wav']:
                        map_victory_path = os.path.join(str(map_package), "ui", "sounds", f"victory{ext}")
                        if os.path.exists(map_victory_path):
                            debug(f"在地图目录中找到victory音效: {map_victory_path}")
                            map_victory_sound = map_victory_path
                            break
            except Exception as e:
                debug(f"检查地图胜利音效时出错: {e}")
        
        # 检查当前战役中是否有专用的胜利音效
        if active_campaign and not map_victory_sound:
            try:
                campaign_package = active_campaign.resources if hasattr(active_campaign, 'resources') else None
                if campaign_package:
                    # 尝试查找战役专用的胜利音效
                    for ext in ['.ogg', '.mp3', '.wav']:
                        campaign_victory_path = os.path.join(str(campaign_package), "ui", "sounds", f"victory{ext}")
                        if os.path.exists(campaign_victory_path):
                            debug(f"在战役目录中找到victory音效: {campaign_victory_path}")
                            map_victory_sound = campaign_victory_path
                            break
            except Exception as e:
                debug(f"检查战役胜利音效时出错: {e}")
    except Exception as e:
        debug(f"尝试获取地图或战役胜利音效时出错: {e}")
    
    # 优先使用地图指定的胜利音乐
    if map_victory_sound:
        # 非循环播放胜利音乐，只播放一次
        play_music(map_victory_sound, loop=False)
    # 否则使用style.txt中配置的全局胜利音乐
    elif victory_sound:
        # 检查音乐文件是否存在，不存在则不播放
        if _find_music_file(victory_sound):
            # 非循环播放胜利音乐，只播放一次
            play_music(victory_sound, loop=False)
        else:
            debug(f"未找到胜利音效文件: {victory_sound}，不播放任何音效")
    else:
        debug("未配置胜利音效，不播放任何音效")

def play_defeat_sound(map_defeat_sound=None):
    """播放失败音乐
    
    Args:
        map_defeat_sound: 地图指定的失败音乐，如果提供则优先使用
    """
    global defeat_sound
    
    debug(f"尝试播放失败音乐，地图指定: {map_defeat_sound}, 全局设置: {defeat_sound}")
    
    # 尝试从当前地图或战役加载特定的失败音效
    try:
        from ..lib.resource import res
        active_map = res._map if hasattr(res, '_map') else None
        active_campaign = res._campaign if hasattr(res, '_campaign') else None
        
        # 检查当前地图中是否有专用的失败音效
        if active_map and not map_defeat_sound:
            try:
                map_package = active_map.resources if hasattr(active_map, 'resources') else None
                if map_package:
                    # 尝试查找地图专用的失败音效
                    for ext in ['.ogg', '.mp3', '.wav']:
                        map_defeat_path = os.path.join(str(map_package), "ui", "sounds", f"defeat{ext}")
                        if os.path.exists(map_defeat_path):
                            debug(f"在地图目录中找到defeat音效: {map_defeat_path}")
                            map_defeat_sound = map_defeat_path
                            break
                            
                    # 如果没找到，尝试找gamefail音效
                    if not map_defeat_sound:
                        for ext in ['.ogg', '.mp3', '.wav']:
                            map_defeat_path = os.path.join(str(map_package), "ui", "sounds", f"gamefail{ext}")
                            if os.path.exists(map_defeat_path):
                                debug(f"在地图目录中找到gamefail音效: {map_defeat_path}")
                                map_defeat_sound = map_defeat_path
                                break
            except Exception as e:
                debug(f"检查地图失败音效时出错: {e}")
        
        # 检查当前战役中是否有专用的失败音效
        if active_campaign and not map_defeat_sound:
            try:
                campaign_package = active_campaign.resources if hasattr(active_campaign, 'resources') else None
                if campaign_package:
                    # 尝试查找战役专用的失败音效
                    for ext in ['.ogg', '.mp3', '.wav']:
                        campaign_defeat_path = os.path.join(str(campaign_package), "ui", "sounds", f"defeat{ext}")
                        if os.path.exists(campaign_defeat_path):
                            debug(f"在战役目录中找到defeat音效: {campaign_defeat_path}")
                            map_defeat_sound = campaign_defeat_path
                            break
                            
                    # 如果没找到，尝试找gamefail音效
                    if not map_defeat_sound:
                        for ext in ['.ogg', '.mp3', '.wav']:
                            campaign_defeat_path = os.path.join(str(campaign_package), "ui", "sounds", f"gamefail{ext}")
                            if os.path.exists(campaign_defeat_path):
                                debug(f"在战役目录中找到gamefail音效: {campaign_defeat_path}")
                                map_defeat_sound = campaign_defeat_path
                                break
            except Exception as e:
                debug(f"检查战役失败音效时出错: {e}")
    except Exception as e:
        debug(f"尝试获取地图或战役失败音效时出错: {e}")
    
    # 优先使用地图指定的失败音乐
    if map_defeat_sound:
        # 非循环播放失败音乐，只播放一次
        play_music(map_defeat_sound, loop=False)
    # 否则使用style.txt中配置的全局失败音乐
    elif defeat_sound:
        # 检查音乐文件是否存在，不存在则不播放
        if _find_music_file(defeat_sound):
            # 非循环播放失败音乐，只播放一次
            play_music(defeat_sound, loop=False)
        else:
            debug(f"未找到失败音效文件: {defeat_sound}，不播放任何音效")
    else:
        debug("未配置失败音效，不播放任何音效")

def set_victory_sound(music_id):
    """设置胜利音乐
    
    Args:
        music_id: 音乐ID或文件路径
    """
    global victory_sound
    
    victory_sound = music_id

def set_defeat_sound(music_id):
    """设置失败音乐
    
    Args:
        music_id: 音乐ID或文件路径
    """
    global defeat_sound
    
    defeat_sound = music_id

def pause_music():
    """暂停当前播放的背景音乐，保留播放位置"""
    global music_paused
    
    if pygame.mixer.music.get_busy() and not music_paused:
        pygame.mixer.music.pause()
        music_paused = True
        return True
    return False
    
def unpause_music():
    """从暂停的位置恢复音乐播放"""
    global music_paused
    
    if music_paused:
        pygame.mixer.music.unpause()
        music_paused = False
        return True
    return False

