"""Which resource will be loaded will depend on the preferred language,
the active packages, the loading order of the mods.
Some resources will be combined differently: some are replaced (sounds),
some are merged (some text files).
"""
import locale
import os
import re
import platform
import warnings
from pathlib import Path
from typing import List

from soundrts.definitions import rules, load_ai, style
from soundrts.achievements import achievements_enabled, load_achievements
from soundrts.cards import load_cards
from soundrts.titles import load_titles
from soundrts.lib.log import warning, exception, debug
from soundrts.lib.package import PackageStack, Package
try:
    from soundrts.lib.sound_cache import sounds
except ModuleNotFoundError:
    # the server doesn't need the sound cache
    class Sounds:
        def load_default(self, *args):
            pass
    sounds = Sounds()
from .. import config, options
from ..mapfile import Map
from ..pack import unpack_file
from ..paths import BASE_PACKAGE_PATH, packages_paths, DOWNLOADED_PATH


def localized_path(path, lang):
    """Return the path modified for this language.
    For example, "ui" becomes "ui-fr".
    """
    return re.sub(r"(?<!\w)ui(?!\w)", "ui-" + lang, path)


def localized_paths(path, language):
    """Return the paths according to the preferred language.
    The default language is always returned as a fallback.
    """
    result = [path]
    if language:
        result.append(localized_path(path, language))
    return result


def best_language_match(lang, available_languages):
    """Return the available language matching best the preferred language."""
    if lang is None:
        lang = ""
    # full match
    lang = lang.replace("_", "-")
    for available_language in available_languages:
        if lang.lower() == available_language.lower():
            return available_language
    # ignore the second part
    if "-" in lang:
        lang = lang.split("-")[0]
    # match a short code
    for available_language in available_languages:
        if lang.lower() == available_language.lower():
            return available_language
    # match a long code
    for available_language in available_languages:
        if "-" in available_language:
            shortened_code = available_language.split("-")[0]
            if lang.lower() == shortened_code.lower():
                return available_language
    # default value
    return "en"


def _preferred_language():
    # 首先尝试从配置文件读取用户指定的语言
    try:
        with open("cfg/language.txt") as t:
            cfg = t.read().strip()
            if cfg:
                return cfg
    except IOError:
        warning("couldn't read cfg/language.txt")
    
    # 如果配置文件不存在或为空，则尝试获取系统语言
    try:
        system_lang = locale.getdefaultlocale()[0]  # 使用getdefaultlocale代替getlocale
        if system_lang:
            # 从类似 'zh_CN' 这样的格式中提取主要语言代码
            main_lang = system_lang.split('_')[0].lower()
            return main_lang
    except (ValueError, AttributeError, IndexError):
        # 如果获取系统语言失败，记录警告
        warning("Couldn't get the system language.")
    
    # 默认使用英语
    return "en"


preferred_language = _preferred_language()


class ResourceStack:
    mods = ""
    soundpacks = ""
    _campaign = None
    _map = None
    language = "en"

    def __init__(self, base_and_additional_packages_paths):
        self.packages = PackageStack(base_and_additional_packages_paths)
        # 在初始化时就确定当前系统语言
        self._determine_language()
        self._reload()

    def _determine_language(self):
        """在初始化时确定当前语言"""
        # 首先尝试获取系统语言
        try:
            system_lang = locale.getdefaultlocale()[0]  # 使用getdefaultlocale代替getlocale
            if system_lang:
                # 从类似 'zh_CN' 这样的格式中提取主要语言代码
                main_lang = system_lang.split('_')[0].lower()
                # 暂存语言，等待_best_available_language验证
                self._system_language = main_lang
                return
        except (ValueError, AttributeError, IndexError):
            warning("Couldn't get the system language.")
            
        self._system_language = None

    def update_packages(self):
        self.__init__([BASE_PACKAGE_PATH] + packages_paths())

    def available_mods(self):
        return [mod.name for mod in self.packages.mods() if not mod.is_a_soundpack()]

    def available_soundpacks(self):
        return [mod.name for mod in self.packages.mods() if mod.is_a_soundpack()]

    def _available_languages(self):
        """Guessed from the existing "ui-language" folders."""
        result = {"en"}
        prefix = "ui-"
        for package in self._layers:
            for name in package.dirnames():
                if name.startswith(prefix):
                    result.add(name[len(prefix):])
        return result

    def _best_available_language(self):
        """确定最佳可用语言"""
        available_languages = self._available_languages()
        
        # 首先尝试从language.txt读取用户指定的语言
        try:
            with open("cfg/language.txt") as t:
                cfg = t.read().strip()
                if cfg:
                    return best_language_match(cfg, available_languages)
        except IOError:
            pass
        
        # 如果language.txt不存在或为空，尝试使用在初始化时检测到的系统语言
        if hasattr(self, '_system_language') and self._system_language:
            system_match = best_language_match(self._system_language, available_languages)
            if system_match:
                return system_match
        
        # 使用默认语言
        return "en"

    def _add_layers(self, packages, mods):
        actual_mods = []
        self._actual_mods_and_required_mods = set()
        for mod_name in [name.strip() for name in mods.split(",")]:
            if mod_name:
                mod = packages.mod(mod_name)
                if mod:
                    self._add_layer(mod, packages)
                    actual_mods.append(mod_name)
        return ",".join(actual_mods)

    def _add_layer(self, mod, packages):
        self._actual_mods_and_required_mods.add(mod.name)
        for required_mod_name in getattr(mod, "mods", []):
            if required_mod_name not in self._actual_mods_and_required_mods:
                required_mod = packages.mod(required_mod_name)
                if required_mod:
                    self._add_layer(required_mod, packages)
        self._layers.append(mod)

    def _add(self, package):
        if package:
            self._layers.append(package)

    _notify = None

    def register(self, f):
        self._notify = f
        self._notify()

    _previous_layers = None

    def _reload(self):
        self._layers = self.packages[:1]
        self.mods = self._add_layers(self.packages, self.mods)
        self.soundpacks = self._add_layers(self.packages, self.soundpacks)
        if self._campaign:
            self._add(self._campaign.resources)
        if self._map:
            self._add(self._map.resources)
        if self._layers != self._previous_layers:
            # 确定最佳可用语言
            self.language = self._best_available_language()
            self.load_rules_and_ai()
            self.load_style()
            sounds.load_default(self)
            if self._notify:
                self._notify()
            self._previous_layers = self._layers[:]
            # 保存语言设置到文件
            self.save_language_to_file()

    def set_mods(self, new_mods):
        if new_mods != self.mods:
            # 清除音乐缓存
            try:
                from .sound import clear_music_cache
                clear_music_cache()
            except Exception as e:
                warning(f"清除音乐缓存失败: {e}")
                
            self.mods = new_mods
            self._reload()

    def set_soundpacks(self, new_soundpacks):
        if new_soundpacks != self.soundpacks:
            self.soundpacks = new_soundpacks
            self._reload()

    def set_map(self, m=None):
        # 当地图变化时，清除音乐缓存
        if m != self._map:
            try:
                from .sound import clear_music_cache
                clear_music_cache()
            except Exception as e:
                warning(f"清除音乐缓存失败: {e}")
                
        self._map = m
        self._reload()

    def set_campaign(self, c=None):
        # 当战役变化时，清除音乐缓存
        if c != self._campaign:
            try:
                from .sound import clear_music_cache
                clear_music_cache()
            except Exception as e:
                warning(f"清除音乐缓存失败: {e}")
                
        self._campaign = c
        self._reload()

    def load_rules_and_ai(self):
        rules.load(self.text("rules", append=True))
        load_ai(*self.texts("ai"))
        if achievements_enabled():
            load_achievements(*self.texts("achievements"))
            load_cards(*self.texts("cards"))
            load_titles(*self.texts("titles"))
        else:
            load_achievements()
            load_cards()
            load_titles()

    def load_style(self):
        style.load(self.text("ui/style", append=True, localize=True))

    def texts(self, name: str, localize=False, root=None) -> List[str]:
        result = []
        for package, path in self.paths(name + ".txt", root, localize):
            try:
                with package.open_text(path) as file:
                    text = file.read()
            except (FileNotFoundError, KeyError):
                pass
            else:
                result.append(text)
        return result

    def text(self, name, localize=False, append=False, root=None):
        """Return the content of the text file with the highest priority
        or the concatenation of the text files contents.
        """
        texts = self.texts(name, localize, root)
        if append:
            return "\n".join(texts)
        else:
            return texts[-1]

    def paths(self, path, root=None, localize=False):
        if root is None:
            roots = self._layers
        else:
            roots = [root]
        if localize:
            lang = self.language
        else:
            lang = None
        for root in roots:
            for p in localized_paths(path, lang):
                yield root, p

    _multi_maps = None
    _mods_at_the_previous_multi_maps_update = None

    def multiplayer_maps(self):
        if self._multi_maps is None or self._mods_at_the_previous_multi_maps_update != self.mods:
            self._reload()  # required by test_desync (used by _move_recommended_maps)
            self._multi_maps = _get_multi_maps()
            self._mods_at_the_previous_multi_maps_update = self.mods
        return self._multi_maps

    def find_multiplayer_map(self, digest):
        for m in self.multiplayer_maps():
            if m.digest() == digest:
                return m

    def unpack_map(self, b: bytes, save=False):
        buffer, name = unpack_file(b)
        m = Map.loads(buffer, name)
        if save and not self.find_multiplayer_map(m.digest()):
            filename = name
            _save_downloaded_map(buffer, filename)
            self._multi_maps = None  # update soon
        return m

    _campaigns = None
    _mods_at_the_previous_campaigns_update = None

    def campaigns(self):
        if self._campaigns is None or self._mods_at_the_previous_campaigns_update != self.mods:
            self._campaigns = _campaigns()
            self._mods_at_the_previous_campaigns_update = self.mods
        return self._campaigns

    def find_campaign(self, name):
        for c in self.campaigns():
            if c.name == name:
                return c

    def coop_campaigns(self):
        """Campaigns with ``coop_campaign 1`` in campaign.txt."""
        return [c for c in self.campaigns() if c.supports_coop()]

    def apply_campaign_resources(self, campaign_name):
        """加载战役资源层（rules / ui/tts 等），供合作战役多人客户端播报地名。"""
        if not campaign_name:
            return None
        campaign = self.find_campaign(campaign_name)
        if campaign is None:
            return None
        if getattr(campaign, "mods", None):
            self.set_mods(campaign.mods)
        self.set_campaign(campaign)
        return campaign

    def apply_campaign_from_map_name(self, map_name):
        """地图名为 ``战役/章节`` 时自动加载战役资源（合作战役）。"""
        if isinstance(map_name, str) and "/" in map_name:
            return self.apply_campaign_resources(map_name.rsplit("/", 1)[0])
        return None

    def save_language_to_file(self):
        """保存当前语言设置到language.txt文件"""
        # 检查是否是从language.txt文件读取的语言设置
        try:
            with open("cfg/language.txt", "r") as f:
                existing_content = f.read().strip()
            
            # 只有当文件存在且有内容时才更新
            if existing_content:
                try:
                    os.makedirs("cfg", exist_ok=True)
                    with open("cfg/language.txt", "w") as f:
                        f.write(self.language)
                except IOError:
                    warning("couldn't write to cfg/language.txt")
        except (IOError, FileNotFoundError):
            # 文件不存在或无法读取，不需要更新
            pass


def _campaigns():
    from soundrts.campaign import Campaign
    campaigns = []
    
    # 检查当前是否有激活的mod
    active_mod = res.mods.strip() if res.mods else ""
    
    # 标记是否找到了mod专用战役
    found_mod_campaigns = False
    
    if active_mod:
        # 如果有激活的mod，先尝试加载该mod目录下的战役
        for package in res.packages:
            mod_package = package.subpackage("mods/" + active_mod)
            if mod_package:
                mod_single = mod_package.subpackage("single")
                if mod_single:
                    mod_campaign_dirs = mod_single.dirnames()
                    if mod_campaign_dirs:  # 如果找到了专用战役
                        found_mod_campaigns = True
                        for n in mod_campaign_dirs:
                            c = Campaign(mod_single.subpackage(n), n)
                            # 添加标记表示这是mod专用战役
                            c.mod_specific = True
                            c.mod_name = active_mod
                            campaigns.append(c)
    
    # 如果没有激活的mod或者没有找到mod专用战役，加载所有战役
    if not active_mod or not found_mod_campaigns:
        for package in res.packages:
            single = package.subpackage("single")
            if single:
                for n in single.dirnames():
                    c = Campaign(single.subpackage(n), n)
                    campaigns.append(c)
    
    return campaigns


def _map_size(m):
    return m.size()


def official_multiplayer_maps():
    maps = []
    official = res.packages[0].subpackage("multi")
    # 加载文件类型地图
    for n in official.filenames():
        m = Map.load(official.open_binary(n), n)
        m.official = True
        maps.append(m)
    
    # 加载文件夹类型地图
    for n in official.dirnames():
        try:
            # 获取文件夹的完整路径
            dir_path = os.path.join(str(res.packages[0]), "multi", n)
            if os.path.isdir(dir_path):
                m = Map.load(dir_path, n)
                m.official = True
                maps.append(m)
        except Exception as e:
            exception("couldn't load map folder %s: %s", n, e)
    
    return maps


def _add_custom_multi(maps):
    active_mod = res.mods.strip() if res.mods else ""
    
    # 用于标记是否找到了mod专用地图
    found_mod_maps = False
    
    
    # 如果有active mod，先尝试加载该mod目录下的multi地图
    if active_mod:
        # 在active mod的根目录下查找multi文件夹
        for package in res.packages[1:]:
            mod_package = package.subpackage("mods/" + active_mod)
            if mod_package:
                mod_multi = mod_package.subpackage("multi")
                if mod_multi:
                    mod_map_files = list(mod_multi.filenames())
                    mod_map_dirs = list(mod_multi.dirnames())
                    
                    if mod_map_files or mod_map_dirs:  # 如果找到了mod专用地图
                        found_mod_maps = True
                        # 处理文件类型地图
                        for n in mod_map_files:
                            try:
                                m = Map.load(mod_multi.open_binary(n), n)
                                m.title.insert(0, 1097)  # heal sound to alert player
                                m.mod_specific = True
                                m.mod_name = active_mod
                                maps.append(m)
                            except Exception as e:
                                exception("couldn't load map file %s: %s", n, e)
                        
                        # 处理文件夹类型地图
                        for n in mod_map_dirs:
                            try:
                                # 获取文件夹的完整路径
                                dir_path = os.path.join(os.path.dirname(str(package)), "mods", active_mod, "multi", n)
                                if os.path.isdir(dir_path):
                                    m = Map.load(dir_path, n)
                                    m.title.insert(0, 1097)  # heal sound to alert player
                                    m.mod_specific = True
                                    m.mod_name = active_mod
                                    maps.append(m)
                                else:
                                    warning("地图文件夹路径不存在: %s", dir_path)
                                    # 尝试使用包路径加载
                                    m = Map.load(mod_multi.subpackage(n), n)
                                    m.title.insert(0, 1097)
                                    m.mod_specific = True
                                    m.mod_name = active_mod
                                    maps.append(m)
                            except Exception as e:
                                exception("couldn't load map folder %s: %s", n, e)
    
    # 如果没有active mod或者没有找到mod专用地图，加载所有自定义地图
    if not active_mod or not found_mod_maps:
        for package in res.packages[1:] + [Package.from_path(DOWNLOADED_PATH)]:
            multi = package.subpackage("multi")
            if multi:
                map_files = list(multi.filenames())
                map_dirs = list(multi.dirnames())
                
                # 处理文件类型地图
                for n in map_files:
                    try:
                        m = Map.load(multi.open_binary(n), n)
                        m.title.insert(0, 1097)  # heal sound to alert player
                        maps.append(m)
                    except Exception as e:
                        exception("couldn't load map file %s: %s", n, e)
                
                # 处理文件夹类型地图
                for n in map_dirs:
                    try:
                        # 获取文件夹的完整路径
                        dir_path = os.path.join(str(package), "multi", n)
                        if os.path.isdir(dir_path):
                            m = Map.load(dir_path, n)
                            m.title.insert(0, 1097)  # heal sound to alert player
                            maps.append(m)
                        else:
                            warning("地图文件夹路径不存在: %s", dir_path)
                            # 尝试使用包路径加载
                            m = Map.load(multi.subpackage(n), n)
                            m.title.insert(0, 1097)
                            maps.append(m)
                    except Exception as e:
                        exception("couldn't load map folder %s: %s", n, e)


def _copy_recommended_maps(maps):
    for n in reversed(style.get("parameters", "recommended_maps")):
        for m in reversed(maps[:]):  # reversed so the custom map is after the official map
            if m.name == n:
                maps.insert(0, m)


def _get_multi_maps():
    maps = []
    
    # 检查当前是否有激活的mod
    active_mod = res.mods.strip() if res.mods else ""
    
    # 用于标记是否找到了mod专用地图
    found_mod_maps = False
    
    # 如果有激活的mod，先尝试检查该mod是否有专用地图
    if active_mod:
        for package in res.packages[1:]:
            mod_package = package.subpackage("mods/" + active_mod)
            if mod_package:
                mod_multi = mod_package.subpackage("multi")
                if mod_multi:
                    mod_map_files = list(mod_multi.filenames()) + list(mod_multi.dirnames())
                    if mod_map_files:  # 如果找到了mod专用地图
                        found_mod_maps = True
                        break
    
    # 只有当没有激活mod或没有找到mod专用地图时，才加载官方地图
    if not active_mod or not found_mod_maps:
        maps.extend(official_multiplayer_maps())
    
    # 加载自定义地图（如果有激活的mod且有专用地图，则只加载该mod的专用地图；否则加载所有地图）
    _add_custom_multi(maps)

    def text_only_title(map_):
        # custom maps will appear after official maps
        return [part.lower() if isinstance(part, str) else chr(ord("z") + 1) for part in map_.title]

    maps.sort(key=text_only_title)
    
    # 只有当没有激活mod或没有找到mod专用地图时，才应用推荐地图排序
    if not active_mod or not found_mod_maps:
        _copy_recommended_maps(maps)
        
    return maps


def _save_downloaded_map(b, name):
    # 合作/战役地图打包名形如 ``The Legend of Raynor/1.txt``，不能当作
    # 多人下载目录下的单文件名写入（Windows 上含 ``/`` 会失败）。
    if "/" in name or "\\" in name:
        return
    try:
        with open(os.path.join(DOWNLOADED_PATH, "multi", name), "wb") as f:
            f.write(b)
    except IOError:
        warning("couldn't write %s", name)


def _resource_stack():
    if options.mods is not None:
        mods = options.mods
    else:
        mods = config.mods
    if options.soundpacks is not None:
        soundpacks = options.soundpacks
    else:
        soundpacks = config.soundpacks

    result = ResourceStack([BASE_PACKAGE_PATH] + packages_paths())
    result.set_mods(mods)
    result.set_soundpacks(soundpacks)

    return result


res = _resource_stack()
