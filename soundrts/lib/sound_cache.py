"""Sounds and text stored in memory (cache).
Loaded from resources (depending on the active language,
packages, mods, campaign, map)."""
import re
import zipfile
from pathlib import Path
from typing import Dict, Optional, Union

import pygame

from soundrts import parameters
from soundrts.lib.log import debug, warning
from soundrts.lib.msgs import NB_ENCODE_SHIFT

TXT_FILE = "ui/tts"

SHORT_SILENCE = "9998"  # 0.01 s
SILENCE = "9999"  # 0.2 s


class TextTable(dict):
    def __init__(self, res, path):
        super().__init__()
        self.phrase_translations = {}  # 添加新的词组翻译字典
        for txt in res.texts(TXT_FILE, localize=True, root=path):
            self._update_from_text(txt)

    def _update_from_text(self, txt):
        lines = txt.split("\n")
        for line in lines:
            line = line.strip()
            # 跳过空行和注释行
            if not line or line.startswith(";") or line.startswith("//"):
                continue
                
            try:
                # 处理等号分隔的格式: 例如 "objective be to eliminate the enemy = 目标为消灭敌人"
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # 检查是否为词组翻译（包含空格的key）
                    if " " in key:
                        self.phrase_translations[key] = value
                        continue
                    else:
                        # 处理常规带等号的键值对
                        if value:
                            self[key] = value
                        else:
                            warning("in '%s', empty value ignored: %s", TXT_FILE, line)
                # 处理原有的空格分隔格式: 例如 "123 翻译文本"
                else:
                    key, value = line.split(None, 1)
                    if value:
                        self[key] = value
                    else:
                        warning("in '%s', empty value ignored: %s", TXT_FILE, line)
            except ValueError:
                warning("in '%s', syntax error: %s", TXT_FILE, line)
                        
    def translate_phrase(self, phrase):
        """尝试翻译完整的词组"""
        if phrase in self.phrase_translations:
            return self.phrase_translations[phrase]
        return None


class Layer:
    sounds: Dict[str, Union[str, tuple, pygame.mixer.Sound]]

    def __init__(self, res, path=None):
        self.txt = TextTable(res, path)
        self._load_sounds(res, path)
        if path is None:
            # the silent sounds are needed (used as random noises in style.txt)
            self.txt[SHORT_SILENCE] = ","
            self.txt[SILENCE] = "."
        self.path = path

    def _load_sound(self, key, file_ref):
        # if a text exists with the same name, the sound won't be loaded
        if key in self.txt:
            debug("didn't load %s.ogg (text exists)", key)
        elif key not in self.sounds:
            self.sounds[key] = file_ref

    def _load_sounds(self, res, root: Optional[Union[str, zipfile.ZipFile]]):
        self.sounds = {}
        for package, path in reversed(list(res.paths("ui", root, localize=True))):
            for name in package.relative_paths_of_files_in_subtree(path):
                n = Path(name)
                if n.suffix == ".ogg":
                    key = n.stem
                    file_ref = package, name
                    self._load_sound(key, file_ref)


def _volume(name, mod_name):
    d1 = parameters.d.get("volume", {})
    if d1.get(name) is not None:
        return d1.get(name)
    else:
        d2 = parameters.d.get("default_volume", {})
        if d2.get(mod_name) is not None:
            return d2.get(mod_name)
    return 1


class Sound(pygame.mixer.Sound):
    def __init__(self, file, mod_name, name):
        super().__init__(file=file)
        self.name = name
        self.mod_name = mod_name
        self.update_volume()

    def update_volume(self):
        self.set_volume(_volume(self.name, self.mod_name))

    # pygame.mixer.Sound 对象无法被 pickle，导致存档失败。
    # 我们把 Sound 序列化为它在缓存中的名字，加载时通过 sounds.get_sound()
    # 重新取回。如果加载时缓存里没有该声音（例如换了 mod），就返回 None；
    # 这与缓存未命中时 get_sound 的既有行为一致，不会破坏调用方。
    def __reduce__(self):
        return (_restore_sound_by_name, (self.name,))


def _restore_sound_by_name(name):
    """读档时根据名字从全局 SoundCache 中恢复 Sound 对象。

    使用顶层函数（而非 lambda/方法）以保证 pickle 在不同进程/版本中可寻址。
    """
    try:
        return sounds.get_sound(name, warn=False)
    except Exception:
        return None


class SoundCache:
    """Numbered sounds and texts.
    Usually a number will give only one type of value, but strange things
    can happen (until I fix this), with SHORT_SILENCE and SILENCE for example.
    """

    def __init__(self):
        self.layers = []
        # 全局回退缓存：数字键 -> 文本
        self._global_text_cache = {}

    @property
    def cache(self):
        return [
            s
            for layer in self.layers
            for s in layer.sounds.values()
            if hasattr(s, "update_volume")
        ]

    def get_sound(self, name, warn=True, restrict_to_mod=None):
        """return the sound corresponding to the given name
        
        Args:
            name: 声音名称
            warn: 是否在未找到声音时发出警告
            restrict_to_mod: 如果设置，只在指定的mod中查找声音
        """
        original_key = "%s" % name
        
        # 无论用户是否提供了.ogg后缀，都尝试查找
        key = original_key
        raw_key = original_key
        
        # 如果提供了.ogg后缀，移除后缀以匹配内部存储的键格式
        if key.lower().endswith('.ogg'):
            raw_key = key[:-4]  # 去掉.ogg后缀
        
        # 尝试使用处理后的键查找
        for layer in reversed(self.layers):
            # 如果指定了mod限制，则只在该mod中查找
            if restrict_to_mod is not None and hasattr(layer, 'path') and layer.path:
                mod_name = getattr(layer.path, 'name', None) 
                if mod_name != restrict_to_mod:
                    continue
                    
            if raw_key in layer.sounds:
                s = layer.sounds[raw_key]
                if isinstance(s, Sound):
                    return s
                else:
                    package, sound_name = s
                    mod_name = package.name
                    try:
                        layer.sounds[raw_key] = Sound(package.open_binary(sound_name), mod_name, raw_key)
                        return layer.sounds[raw_key]
                    except IOError:
                        warning("couldn't load %s from %s", s, mod_name)
                        del layer.sounds[raw_key]
                        continue  # try next layer
        
        if warn:
            warning("this sound may be missing: %s", name)
        return None

    def has_sound(self, name):
        """return True if the cache have a sound with that name"""
        try:
            key = "%s" % name
            raw_key = key
            
            # 如果名称以.ogg结尾，移除后缀
            if key.lower().endswith('.ogg'):
                raw_key = key[:-4]
            
            # 检查是否存在该音效
            for layer in reversed(self.layers):
                if raw_key in layer.sounds:
                    return True
            return False
        except pygame.error:
            return False

    def text(self, key):
        """return the text corresponding to the given name"""
        assert isinstance(key, str)
        for layer in reversed(self.layers):
            if key in layer.txt:
                return layer.txt[key]

    def load_default(self, res):
        """load the default layer into memory from res"""
        self.layers = [Layer(res)]
        # 切换战役/mod/地图时清空跨战役 tts 的全局回退缓存，
        # 避免上一个战役命中过的 ID 被下一个战役继续复用
        self._global_text_cache = {}

    def translate_sound_number(self, sound_number):
        """Return the text or sound corresponding to the sound number.

        If the number is greater than NB_ENCODE_SHIFT, then it's really a number.
        """
        # 已解析的 Sound 对象直接返回，避免二次 str() 变成 repr 文本。
        if isinstance(sound_number, Sound):
            return sound_number

        # 检查是否为强制文本标记
        if isinstance(sound_number, str) and sound_number.startswith("文本: "):
            return sound_number  # 直接返回，在message.py中会处理前缀
            
        key = "%s" % sound_number
        # 首先检查是否有对应的文本（当前资源层：基础包 + 当前战役/mod/地图）
        t = self.text(key)
        if t is not None:
            return t

        # 处理带或不带.ogg后缀的情况
        raw_key = key
        if key.lower().endswith('.ogg'):
            raw_key = key[:-4]

        # 优先使用当前资源层加载好的声音文件，避免被其他战役 tts 的全局回退覆盖
        # 例如：nathan tech campaign 1 自己的 ui/7501.ogg 必须优先于战役 tts.txt 中的 7501 文本
        if self.has_sound(raw_key):
            return self.get_sound(raw_key)

        # 全局回退：仅当前层既无文本也无声音时，才扫描所有包/模组的战役 tts 查找（命中即缓存）
        try:
            fb = self._global_lookup_text(key)
            if fb is not None:
                return fb
        except Exception:
            pass

        # 检查是否是一个大于NB_ENCODE_SHIFT的数字(表示真实的数字，如分数)
        if re.match("^[0-9]+$", key) is not None and int(key) >= NB_ENCODE_SHIFT:
            return "%s" % (int(key) - NB_ENCODE_SHIFT)
        
        # 对于纯数字ID，如果找不到对应的声音或文本，就返回原始ID
        # 不再添加警告信息以避免干扰
        if re.match("^[0-9]+$", key) is not None:
            return str(key)
            
        # 对于其他类型的ID，返回字符串形式
        try:
            return str(key)
        except ValueError:
            warning("Unicode error in %s", repr(key))
            return str(key, errors="ignore")

    def _global_lookup_text(self, key: str):
        """在所有可访问包/模组/战役下的 ui/tts 中查找键对应的文本，并缓存。

        仅在当前层未找到时调用，避免性能影响。支持数字 ID 与文本键（如 loc_ch02_outpost）。
        """
        if not key:
            return None
        if key in self._global_text_cache:
            return self._global_text_cache[key]

        try:
            # 延迟导入，避免服务端无声环境的问题
            from .resource import res
        except Exception:
            return None

        def _parse_texts_for_key(texts):
            # 解析多份文本；后加载的本地化文件优先（与 Layer 内 dict 覆盖一致）
            for txt in reversed(texts or []):
                for line in txt.split("\n"):
                    s = line.strip()
                    if not s or s.startswith(";") or s.startswith("//"):
                        continue
                    # 等号格式：123 = text
                    if "=" in s:
                        k, v = s.split("=", 1)
                        if k.strip() == key:
                            v = v.strip()
                            if v:
                                return v
                    else:
                        # 空格格式：123 text
                        parts = s.split(None, 1)
                        if len(parts) == 2 and parts[0] == key:
                            v = parts[1].strip()
                            if v:
                                return v
            return None

        # 1) 扫描基础包下的所有战役 single/*
        try:
            for package in res.packages:
                single = package.subpackage("single")
                if single:
                    for camp_name in single.dirnames():
                        camp_pkg = single.subpackage(camp_name)
                        texts = res.texts(TXT_FILE, localize=True, root=camp_pkg)
                        v = _parse_texts_for_key(texts)
                        if v is not None:
                            self._global_text_cache[key] = v
                            return v
        except Exception:
            pass

        # 2) 扫描所有mod下的战役 mods/*/single/*
        try:
            for package in res.packages:
                mods_pkg = package.subpackage("mods")
                if not mods_pkg:
                    continue
                for mod_name in mods_pkg.dirnames():
                    mod_pkg = mods_pkg.subpackage(mod_name)
                    if not mod_pkg:
                        continue
                    mod_single = mod_pkg.subpackage("single")
                    if not mod_single:
                        continue
                    for camp_name in mod_single.dirnames():
                        camp_pkg = mod_single.subpackage(camp_name)
                        texts = res.texts(TXT_FILE, localize=True, root=camp_pkg)
                        v = _parse_texts_for_key(texts)
                        if v is not None:
                            self._global_text_cache[key] = v
                            return v
        except Exception:
            pass

        # 3) 扫描 mods/*/ui/tts（mod 菜单 title 等）
        try:
            for package in res.packages:
                mods_pkg = package.subpackage("mods")
                if not mods_pkg:
                    continue
                for mod_name in mods_pkg.dirnames():
                    mod_pkg = mods_pkg.subpackage(mod_name)
                    if not mod_pkg:
                        continue
                    texts = res.texts(TXT_FILE, localize=True, root=mod_pkg)
                    v = _parse_texts_for_key(texts)
                    if v is not None:
                        self._global_text_cache[key] = v
                        return v
        except Exception:
            pass

        # 未命中
        return None

    def translate_phrase(self, phrase):
        """尝试翻译完整的词组
        
        Args:
            phrase (str): 要翻译的词组
            
        Returns:
            str 或 None: 翻译结果，如果没有找到匹配的翻译则返回None
        """
        if not phrase or not isinstance(phrase, str):
            return None
            
        # 优先尝试完整匹配
        for layer in reversed(self.layers):
            if hasattr(layer.txt, 'translate_phrase'):
                result = layer.txt.translate_phrase(phrase)
                if result is not None:
                    return result
        
        # 尝试按词语子集匹配（支持部分词组翻译，例如 "be to eliminate the enemy" 可匹配 "objective be to eliminate the enemy"）
        words = phrase.split()
        if len(words) > 1:
            for layer in reversed(self.layers):
                if not hasattr(layer.txt, 'phrase_translations'):
                    continue
                    
                # 尝试查找包含该词组的更长词组
                for key, value in layer.txt.phrase_translations.items():
                    key_words = key.split()
                    # 检查是否为子序列
                    if len(key_words) >= len(words):
                        for i in range(len(key_words) - len(words) + 1):
                            if key_words[i:i+len(words)] == words:
                                return value
        
        return None

    def update_volumes(self):
        for s in self.cache:
            s.update_volume()


sounds = SoundCache()
