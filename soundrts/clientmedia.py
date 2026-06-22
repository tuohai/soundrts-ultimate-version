import os
import platform

import pygame

from . import config
from . import msgparts as mp
from .lib import sound
from .lib.msgs import nb2msg
from .lib.resource import res
from .lib.screen import set_screen
from .lib.sound_cache import sounds
from .lib.voice import voice
from .version import VERSION

if platform.system() == "Windows":
    # problem with F10 and DirectX, so use windib
    os.environ["SDL_VIDEODRIVER"] = "windib"

fullscreen = False


def app_title():
    return f"SoundRTS {VERSION} {res.mods} {res.soundpacks}"


def update_display_caption():
    """set the window title"""
    pygame.display.set_caption(app_title())


def minimal_init():
    """initialize sound, voice, screen, window title, keyboard"""
    sound.init(config.num_channels)
    config.apply_audio_settings()
    voice.init(config)
    set_screen(fullscreen)
    res.register(update_display_caption)
    pygame.key.set_repeat(500, 100)


def init_media():
    """initialize sound, voice, screen, window title, keyboard,
    and sound cache"""
    minimal_init()
    sounds.load_default(res)


def modify_volume(incr):
    """increase or decrease the main volume only, and say it"""
    # 只调整主音量
    sound.main_volume = min(1, max(0, sound.main_volume + 0.1 * incr))
    config.save_audio_settings()

    sound.stop()
    voice.item(nb2msg(round(sound.main_volume * 100)) + mp.PERCENT_VOLUME)


def toggle_fullscreen():
    """toggle full screen mode, and say it"""
    global fullscreen
    fullscreen = not fullscreen
    set_screen(fullscreen)
    if fullscreen:
        voice.item(mp.DISPLAY_ON)
    else:
        voice.item(mp.DISPLAY_OFF)


def get_fullscreen():
    """return True if in full screen mode"""
    return fullscreen


def close_media():
    """try to clean up before closing the client"""
    sound.stop()
    pygame.quit()


def play_sequence(names):
    """播放一系列声音或文本，每个都可以被中断
    
    参数:
        names: 要播放的声音或文本的ID列表，可以是数字、字母或中文字符
              对于自定义音效，可以选择是否包含.ogg后缀，例如'launch_mdg 1000'或'launch_mdg 1000.ogg'均可
    """
    # 检查音乐是否已经被暂停（比如上层调用者已经暂停了）
    music_already_paused = sound.music_paused
    
    # 保存当前音乐状态
    current_music_id = sound.current_music
    music_was_playing = pygame.mixer.music.get_busy()
    
    # 只有当音乐没有被暂停时才执行音乐控制
    # 这避免了与上层调用者的音乐控制发生冲突
    music_controlled_by_us = False
    if not music_already_paused and music_was_playing:
        sound.pause_music()
        music_controlled_by_us = True
    
    # 停止其他声音效果
    sound.stop(stop_voice_too=False)  # 不停止语音通道
    
    # 播放序列
    for name in names:
        # 检查是否是数字ID，但不要立即判断它是聊天文本
        # 先检查它是否是一个有效的声音ID
        if isinstance(name, str) and name.isdigit():
            voice.important([name])  # 让voice系统处理数字ID
        else:
            voice.important([name])  # each element is interruptible
            
    # 只有当我们暂停了音乐时才恢复
    if music_controlled_by_us:
        # 尝试恢复暂停的音乐
        if not sound.unpause_music():
            # 如果无法恢复暂停的音乐（可能因为某些原因音乐被停止），则重新播放
            if current_music_id:
                sound.play_music(current_music_id)
