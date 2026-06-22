import os

from soundrts import parameters


def _mkdir(path):
    if not os.path.exists(path):
        try:
            os.mkdir(path)
        except:
            # no log file at this stage
            print("cannot make dir: %s" % path)


if os.path.exists("user"):
    CONFIG_DIR_PATH = "user"
elif "APPDATA" in os.environ:  # Windows
    CONFIG_DIR_PATH = os.path.join(os.environ["APPDATA"], "SoundRTS")
elif "HOME" in os.environ:
    CONFIG_DIR_PATH = os.path.join(os.environ["HOME"], ".SoundRTS")
else:
    CONFIG_DIR_PATH = "user"
_mkdir(CONFIG_DIR_PATH)

TMP_PATH = os.path.join(CONFIG_DIR_PATH, "tmp")
_mkdir(TMP_PATH)

REPLAYS_PATH = os.path.join(CONFIG_DIR_PATH, "replays")
_mkdir(REPLAYS_PATH)

DOWNLOADED_PATH = os.path.join(CONFIG_DIR_PATH, "downloaded")
_mkdir(DOWNLOADED_PATH)

CLIENT_LOG_PATH = os.path.join(TMP_PATH, "client.log")
SERVER_LOG_PATH = os.path.join(TMP_PATH, "server.log")

CONFIG_FILE_PATH = os.path.join(CONFIG_DIR_PATH, "SoundRTS.ini")
CAMPAIGNS_CONFIG_PATH = os.path.join(CONFIG_DIR_PATH, "campaigns.ini")
STATS_PATH = os.path.join(CONFIG_DIR_PATH, "stats.tmp")
# 旧版的单存档路径，仅为兼容性保留
SAVE_PATH = os.path.join(CONFIG_DIR_PATH, "savegame")
# 多存档槽目录（每个 mod 一个子目录，每个 mod 最多 10 个存档）
SAVES_DIR_PATH = os.path.join(CONFIG_DIR_PATH, "saves")
_mkdir(SAVES_DIR_PATH)
# 当玩家未加载任何 mod 时使用的 mod key（也是 SAVES_DIR_PATH 下的子目录名）
BASE_MOD_KEY = "_base"
# 旧版（mod 隔离之前）的"继续未完成的游戏"存档路径，仅为兼容性保留
RESUME_SAVE_PATH = os.path.join(CONFIG_DIR_PATH, "resume_savegame")
# 每个 mod 的存档子目录中，续玩存档的文件名
RESUME_SAVE_FILENAME = "resume_savegame"
# 单 mod 下手动存档槽的最大数量
MAX_SAVE_SLOTS = 10
CUSTOM_BINDINGS_PATH = os.path.join(CONFIG_DIR_PATH, "bindings.txt")
HOTKEY_OVERRIDES_DIR = os.path.join(CONFIG_DIR_PATH, "hotkey_overrides")
_mkdir(HOTKEY_OVERRIDES_DIR)
# 旧版单文件路径（迁移到 hotkey_overrides/_base.json）
LEGACY_HOTKEY_OVERRIDES_PATH = os.path.join(CONFIG_DIR_PATH, "hotkey_overrides.json")


def current_hotkey_overrides_path():
    """当前 mod 专属热键映射文件（与存档/回放隔离规则相同）。"""
    return os.path.join(HOTKEY_OVERRIDES_DIR, current_mod_key() + ".json")


def _sanitize_mod_part(name):
    """把 mod 名转成对文件系统安全的标识。"""
    # 只保留字母、数字、下划线、连字符
    out = []
    for ch in name:
        if ch.isalnum() or ch in ("_", "-"):
            out.append(ch)
        else:
            out.append("_")
    s = "".join(out).strip("_")
    return s or "_"


def current_mod_key():
    """返回当前激活的 mod 用于存档隔离的标识符。

    - 未加载任何 mod 时返回 BASE_MOD_KEY ("_base")
    - 单个 mod 时返回该 mod 的安全名称
    - 多个 mod 同时启用时，按顺序用 "+" 连接所有名称
    """
    # 这里使用延迟导入，以避免 paths.py <-> config.py 循环依赖。
    # 运行期资源管理器 res.mods 是当前实际加载 mod 的权威来源（启动时由
    # config/options 初始化，并在切换 mod 时更新）。只要 res 可用就以它为准——
    # 包括空字符串（表示"未加载任何 mod"），此时存档应隔离到 _base。仅当 res
    # 不可用时才回退到配置值 config.mods。
    mods_str = None
    try:
        from .lib.resource import res  # noqa: WPS433
        mods_str = getattr(res, "mods", None)
    except Exception:
        mods_str = None
    if mods_str is None:
        try:
            from . import config  # noqa: WPS433
            mods_str = getattr(config, "mods", "") or ""
        except Exception:
            mods_str = ""
    if not mods_str:
        return BASE_MOD_KEY
    parts = [_sanitize_mod_part(p.strip()) for p in mods_str.split(",") if p.strip()]
    parts = [p for p in parts if p]
    if not parts:
        return BASE_MOD_KEY
    return "+".join(parts)


def current_saves_dir():
    """返回当前 mod 专属的存档目录（如不存在则创建）。"""
    d = os.path.join(SAVES_DIR_PATH, current_mod_key())
    _mkdir(d)
    return d


def current_resume_save_path():
    """返回当前 mod 专属的"继续未完成的游戏"存档文件路径。"""
    return os.path.join(current_saves_dir(), RESUME_SAVE_FILENAME)


def current_replays_dir():
    """返回当前 mod 专属的回放目录（如不存在则创建）。"""
    d = os.path.join(REPLAYS_PATH, current_mod_key())
    _mkdir(d)
    return d


# --- 旧版（mod 隔离之前）存档的一次性迁移：把所有放在 SAVES_DIR_PATH 根目录下的
# 旧 save_* 文件以及 RESUME_SAVE_PATH 移动到 BASE_MOD_KEY 子目录，让没有加载 mod
# 的玩家保持原本的可见存档列表。
try:
    _base_dir = os.path.join(SAVES_DIR_PATH, BASE_MOD_KEY)
    _mkdir(_base_dir)
    # 1) 旧的单存档（更老的版本）
    if os.path.exists(SAVE_PATH) and os.path.isfile(SAVE_PATH):
        try:
            _ts = int(os.path.getmtime(SAVE_PATH))
            _target = os.path.join(_base_dir, "save_%d" % _ts)
            if not os.path.exists(_target):
                os.rename(SAVE_PATH, _target)
        except Exception:
            pass
    # 2) 散落在 SAVES_DIR_PATH 根目录下的 save_* 文件
    try:
        for _name in os.listdir(SAVES_DIR_PATH):
            _src = os.path.join(SAVES_DIR_PATH, _name)
            if os.path.isfile(_src) and _name.startswith("save_"):
                _dst = os.path.join(_base_dir, _name)
                if not os.path.exists(_dst):
                    try:
                        os.rename(_src, _dst)
                    except Exception:
                        pass
    except OSError:
        pass
    # 3) 旧的"继续未完成的游戏"存档
    if os.path.exists(RESUME_SAVE_PATH) and os.path.isfile(RESUME_SAVE_PATH):
        _dst = os.path.join(_base_dir, RESUME_SAVE_FILENAME)
        if not os.path.exists(_dst):
            try:
                os.rename(RESUME_SAVE_PATH, _dst)
            except Exception:
                pass
except Exception:
    pass

# --- 旧版（mod 隔离之前）回放文件的一次性迁移：把所有放在 REPLAYS_PATH 根目录下的
# 旧 *.txt 文件移动到 BASE_MOD_KEY 子目录，让没有加载 mod 的玩家保持原本可见的回放列表。
try:
    _base_replays_dir = os.path.join(REPLAYS_PATH, BASE_MOD_KEY)
    _mkdir(_base_replays_dir)
    try:
        for _name in os.listdir(REPLAYS_PATH):
            _src = os.path.join(REPLAYS_PATH, _name)
            if os.path.isfile(_src) and _name.endswith(".txt"):
                _dst = os.path.join(_base_replays_dir, _name)
                if not os.path.exists(_dst):
                    try:
                        os.rename(_src, _dst)
                    except Exception:
                        pass
    except OSError:
        pass
except Exception:
    pass

_mkdir(os.path.join(CONFIG_DIR_PATH, "single"))
_mkdir(os.path.join(CONFIG_DIR_PATH, "multi"))
_mkdir(os.path.join(CONFIG_DIR_PATH, "mods"))
_mkdir(os.path.join(CONFIG_DIR_PATH, "packages"))

_mkdir(os.path.join(DOWNLOADED_PATH, "multi"))
_mkdir(os.path.join(DOWNLOADED_PATH, "packages"))

DOWNLOADED_PACKAGES_PATH = os.path.join(DOWNLOADED_PATH, "packages")

BASE_PACKAGE_PATH = parameters.d["packages"]["base"]
BASE_PATHS = parameters.d["packages"]["additional"]


def packages_paths():
    packages = []
    packages.extend(BASE_PATHS)
    for rp in BASE_PATHS:
        pp = os.path.join(rp, "packages")
        if os.path.isdir(pp):
            for name in os.listdir(pp):
                p = os.path.join(pp, name)
                if os.path.normpath(p) != os.path.normpath(BASE_PACKAGE_PATH):
                    packages.append(p)
    return packages
