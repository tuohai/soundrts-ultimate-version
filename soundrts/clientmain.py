from . import config

config.load()

# hide the pygame support prompt from players
if not config.debug_mode:
    import os

    os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

from .lib import log
from .lib.log import exception, warning
from .paths import CLIENT_LOG_PATH
from .version import VERSION_FOR_BUG_REPORTS

log.set_version(VERSION_FOR_BUG_REPORTS)
log.clear_handlers()
log.add_secure_file_handler(CLIENT_LOG_PATH, "w")
if VERSION_FOR_BUG_REPORTS.startswith("v"):  # executable
    log.add_http_handler("http://jlpo.free.fr/soundrts/metaserver")
log.add_console_handler()

import os
from pathlib import Path
import sys
import time
import webbrowser

import cloudpickle

from . import discovery
from . import msgparts as mp
from . import stats
from .clientmedia import close_media, init_media, voice, app_title
from .clientmenu import (
    CLOSE_MENU,
    Menu,
    confirm_yes_no,
    input_string,
    input_text,
)
from .clientserver import (
    connect_and_play,
    server_delay,
    start_server_and_connect,
)
from .clientversion import revision_checker
from .definitions import ai_invite_label, get_menu_ai_difficulties, rules, style
from .achievements_menu import achievements_menu
from .game import ReplayGame, TrainingGame, pickle_recursion_limit_for_file_size
from .lib.msgs import literal_text_msg, nb2msg
from .lib.package import mod_menu_label
from .lib.resource import best_language_match, preferred_language, res
from .lib import sound
from .metaserver import servers_list
from .paths import (
    CONFIG_DIR_PATH,
    RESUME_SAVE_FILENAME,
    current_replays_dir,
    current_resume_save_path,
    current_saves_dir,
)
from .version import server_is_compatible


def choose_server_ip_in_a_list():
    servers = servers_list(voice)
    try:
        local = discovery.local_server()
        if local:
            version, port, login = local[1].split(" ", 2)
            servers.insert(
                0, " ".join(("0", local[0], version, local[0] + "_" + login, port))
            )
    except:
        warning("error while searching for a local server")
    total = 0
    compatible = 0
    menu = Menu()
    for s in servers:
        if s == "":
            continue
        try:
            _, ip, version, login, port = s.split()
        except ValueError:
            warning("line not recognized from the metaserver: %s", s)
        else:
            total += 1
            if server_is_compatible(version):
                compatible += 1
                delay = server_delay(ip, port)
                if delay is not None:
                    menu.append(
                        [login],
                        (connect_and_play, ip, port),
                        [f"{int(delay * 1000)}ms", ","] + mp.SERVER_HOSTED_BY + [login],
                    )
    menu.choices.sort(key=lambda x: int(x[2][0][:-2]))
    menu.title = nb2msg(compatible) + mp.SERVERS_ON + nb2msg(total)
    menu.append(mp.CANCEL2, None, mp.GO_BACK_TO_PREVIOUS_MENU)
    menu.run()


def enter_server_ip():
    host = input_string([], r"^[A-Za-z0-9\.]$")
    if host == "":
        host = "localhost"
    if host:
        connect_and_play(host)


def multiplayer_menu():
    if config.login == "player":
        voice.alert(mp.ENTER_NEW_LOGIN)
        modify_login()
    menu = Menu(
        mp.MAKE_A_SELECTION,
        [
            (mp.CHOOSE_SERVER_IN_LIST, choose_server_ip_in_a_list),
            (mp.ENTER_SERVER_IP, enter_server_ip),
            (mp.CANCEL, None),
        ],
        menu_type="submenu"  # 指定这是子菜单
    )
    menu.run()


def replay(n):
    # 回放文件在当前 mod 的回放目录中
    ReplayGame(os.path.join(current_replays_dir(), n)).run()


def replay_filenames(minimal_size=1):
    """列出当前 mod 下的回放文件名（按修改时间从新到旧排序）。

    支持玩家直接在文件系统中重命名回放文件——只要文件位于当前 mod 的回放目录中、
    是普通文件且大小足够，就会被列出。
    """
    replays_dir = current_replays_dir()
    try:
        names = os.listdir(replays_dir)
    except OSError:
        return
    items = []
    for n in names:
        p = Path(replays_dir, n)
        try:
            if p.is_file() and p.stat().st_size >= minimal_size:
                items.append((p.stat().st_mtime, n))
        except OSError:
            continue
    # 按 mtime 从新到旧
    items.sort(reverse=True)
    for _mtime, n in items:
        yield n


def _is_auto_replay_filename(filename):
    """判断回放文件名是否仍是自动生成的 "replay<N>_<timestamp>.txt" 形式（玩家未改名）。"""
    stem = filename[:-4] if filename.endswith(".txt") else filename
    import re as _re
    return bool(_re.match(r"^replay\d+_\d+$", stem))


def _replay_display_name(filename):
    """从回放文件名推导出菜单中要朗读 / 显示的名字。

    - 自动命名的回放是 "replay<N>_<timestamp>.txt"：返回列表，第一项为 mp.REPLAY 消息常量
      （可由 tts.txt 翻译为多语言），后接空格 + 序号 + 空格 + 时间。
    - 玩家重命名后的回放：使用文件名本身（如果以 .txt 结尾则去掉后缀）作为名字。
    """
    stem = filename[:-4] if filename.endswith(".txt") else filename
    import re as _re
    m = _re.match(r"^replay(\d+)_(\d+)$", stem)
    if m:
        num = m.group(1)
        ts = int(m.group(2))
        try:
            ts_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
            return [mp.REPLAY[0], " " + num + ", " + ts_str]
        except (OSError, OverflowError):
            return [stem]
    try:
        return [time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(stem)))]
    except (ValueError, OSError, OverflowError):
        return [stem]


def _sanitize_filename(name):
    """把用户输入的名字转换为对文件系统安全的形式。

    - 去掉首尾空白和"."；
    - 把禁用字符替换为下划线（理论上 input_text 已过滤，这里再兜底）；
    - 如果结果为空返回 None。
    """
    if not name:
        return None
    bad = set('\\/:*?"<>|\0')
    cleaned = "".join("_" if c in bad else c for c in name)
    cleaned = cleaned.strip().strip(".")
    # 控制字符兜底
    cleaned = "".join(c for c in cleaned if c.isprintable())
    cleaned = cleaned.strip()
    if not cleaned:
        return None
    return cleaned


def _refresh_replay_menu(menu):
    """根据当前回放目录的内容重建给定的回放菜单。"""
    menu.clear_choices()
    menu.title = list(mp.OBSERVE_RECORDED_GAME)
    replays_dir = current_replays_dir()
    for n in replay_filenames():
        name_list = _replay_display_name(n)
        # 自动命名的回放（"<timestamp>.txt"）的 name 已经是时间，
        # 无需在 explanation 里重复说明；玩家重命名后的回放则把文件修改时间作为
        # explanation 单独朗读，得到类似 "录像1, 2026-05-24 23:30:35" 的效果。
        if _is_auto_replay_filename(n):
            explanation = []
        else:
            try:
                ts = os.path.getmtime(os.path.join(replays_dir, n))
                explanation = [
                    time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
                ]
            except OSError:
                explanation = []
        menu.append(
            name_list,
            (replay, n),
            explanation,
            on_rename=(lambda n=n, m=menu: _rename_replay(n, m)),
            on_delete=(lambda immediate, n=n, m=menu: _delete_replay(n, m, immediate)),
        )
    menu.append(mp.QUIT2, None)


def _rename_replay(old_filename, menu):
    """重命名一个回放文件，并刷新菜单。"""
    replays_dir = current_replays_dir()
    old_path = os.path.join(replays_dir, old_filename)
    if not os.path.isfile(old_path):
        voice.alert(mp.BEEP)
        _refresh_replay_menu(menu)
        return
    # 编辑框从空开始，避免玩家需要先按多次 backspace 才能清空旧名字。
    # 玩家在菜单中浏览选中该项时已经听过当前名称，无需再次显示。
    new_name = input_text(mp.ENTER_NEW_NAME)
    # 玩家按 Esc 取消, 或没输入直接回车 (后者等价于取消, 比报错友好):
    if new_name is None or not new_name.strip():
        voice.alert(mp.CANCELED)
        return
    safe = _sanitize_filename(new_name)
    if not safe:
        voice.alert(mp.INVALID_NAME)
        return
    # 保留 .txt 扩展名以便后续仍可识别为回放文件。
    if not safe.lower().endswith(".txt"):
        safe = safe + ".txt"
    new_path = os.path.join(replays_dir, safe)
    if os.path.normcase(os.path.abspath(new_path)) == os.path.normcase(
        os.path.abspath(old_path)
    ):
        # 名称未变，无需操作。
        voice.alert(mp.CANCELED)
        return
    if os.path.exists(new_path):
        voice.alert(mp.INVALID_NAME)
        return
    try:
        os.rename(old_path, new_path)
    except OSError:
        voice.alert(mp.BEEP)
        return
    voice.alert(mp.RENAMED)
    _refresh_replay_menu(menu)


def _delete_replay(filename, menu, immediate):
    """删除一个回放文件；immediate=False 时先询问。"""
    replays_dir = current_replays_dir()
    path = os.path.join(replays_dir, filename)
    if not os.path.isfile(path):
        voice.alert(mp.BEEP)
        _refresh_replay_menu(menu)
        return
    if not immediate:
        if not confirm_yes_no(list(mp.CONFIRM_DELETE) + _replay_display_name(filename)):
            voice.alert(mp.CANCELED)
            return
    try:
        os.remove(path)
    except OSError:
        voice.alert(mp.BEEP)
        return
    voice.alert(mp.DELETED)
    _refresh_replay_menu(menu)


def replay_menu():
    menu = Menu(mp.OBSERVE_RECORDED_GAME, menu_type="submenu")  # 指定这是子菜单
    _refresh_replay_menu(menu)
    menu.run()


def modify_login():
    from .config import login_char_is_valid

    login = input_text(
        msg=mp.ENTER_NEW_LOGIN,
        default="" if config.login == config.DEFAULT_LOGIN else config.login,
        max_length=20,
        char_filter=login_char_is_valid,
    )
    if login is None:
        voice.alert(mp.CURRENT_LOGIN_KEPT)
    elif not config.login_is_valid(login):
        voice.alert(mp.BAD_LOGIN + mp.CURRENT_LOGIN_KEPT)
    else:
        voice.alert(mp.NEW_LOGIN + literal_text_msg(login))
        config.login = login
        config.save()


def _quarantine_broken_save(path):
    """把损坏的存档 rename 成 ``<path>.broken``, 失败时直接删除.

    用于隔离截断/孤儿存档, 避免 "继续未完成游戏" / "读档列表" 反复撞上.
    """
    try:
        broken_path = path + ".broken"
        # 若已有同名 .broken 文件, 加个时间戳
        if os.path.exists(broken_path):
            import time as _time
            broken_path = "%s.%d.broken" % (path, int(_time.time()))
        os.replace(path, broken_path)
        warning("quarantined broken savegame: %s -> %s", path, broken_path)
    except OSError:
        try:
            os.remove(path)
            warning("deleted broken savegame (rename failed): %s", path)
        except OSError:
            pass


def _load_savegame_file(path, delete_on_success=False):
    """从指定路径加载并运行存档；返回是否成功。

    Robustness: 历史上写存档若中途崩溃 (e.g. RecursionError 见
    game._write_save_to docstring) 会留下只有 header / 截断 pickle 的孤儿
    文件, 加载时报 ``EOFError: Ran out of input``. 这里把那种坏档当作
    损坏存档处理 — 提示用户, 并把坏档移走 (rename 成 ``.broken``) 以免
    "继续未完成游戏" 每次都撞上同一个坏档.
    """
    if not os.path.exists(path):
        voice.alert(mp.BEEP)
        return False
    # 0 字节或只有 header 一行的极端坏档: 直接当作损坏文件处理
    try:
        if os.path.getsize(path) < 16:
            warning("savegame file too small (likely corrupted): %s", path)
            _quarantine_broken_save(path)
            voice.alert(mp.BEEP)
            return False
    except OSError:
        pass
    # 立即打断任何残留的语音朗读（例如菜单确认朗读），让加载马上开始，
    # 避免玩家在 restore 时还要再按一次键才能进入游戏。
    try:
        voice.silent_flush()
    except Exception:
        pass
    f = open(path, "rb")
    try:
        try:
            i = int(stats.Stats(None, None)._get_weak_user_id())
            j = int(f.readline())
        except Exception:
            i = 0
            j = "error"
        if i != j:
            warning("savegame file is not from this machine: %s", path)
            voice.alert(mp.BEEP)
            return False
        try:
            # 与 game._write_save_to 对称: 按存档体积拉高 recursion limit;
            # cw1-mm 等大地图读档也需要 ~50000.
            _saved_limit = sys.getrecursionlimit()
            _load_limit = pickle_recursion_limit_for_file_size(os.path.getsize(path))
            sys.setrecursionlimit(max(_saved_limit, _load_limit))
            try:
                game_session = cloudpickle.load(f)
            finally:
                sys.setrecursionlimit(_saved_limit)
        except EOFError:
            # 截断的孤儿文件 (写档中途崩溃留下): 隔离掉避免反复撞.
            warning("savegame file truncated (likely from a failed save): %s", path)
            f.close()
            _quarantine_broken_save(path)
            voice.alert(mp.BEEP)
            return False
        except Exception:
            exception("cannot load savegame file: %s" % path)
            voice.alert(mp.BEEP)
            return False
    finally:
        try:
            f.close()
        except Exception:
            pass

    if delete_on_success:
        # 先尝试删除，再进入游戏；即使删除失败也继续
        try:
            os.remove(path)
        except OSError:
            pass

    try:
        game_session.run_on()
    except Exception:
        exception("error while running restored game")
        voice.alert(mp.BEEP)
        return False
    return True


def _list_save_slots():
    """列出当前 mod 下的存档槽（最新的在前）：返回 [(label_msg, explanation_msg, path), ...]。

    - 自动命名的存档（文件名形如 save_<digits>）：label 朗读为简短的"存档 N"，
      explanation 中带上修改时间；
    - 玩家重命名后的存档：label 直接朗读文件名，explanation 同样带上修改时间。
    - 不同 mod 的存档保存在不同的子目录中，因此此函数只会返回与当前 mod 相关的存档。
    - 续玩存档（RESUME_SAVE_FILENAME）不会出现在该列表中。
    """
    saves_dir = current_saves_dir()
    auto_paths = []
    custom_paths = []
    try:
        names = os.listdir(saves_dir)
    except OSError:
        names = []
    for n in names:
        p = os.path.join(saves_dir, n)
        if not os.path.isfile(p):
            continue
        if n == RESUME_SAVE_FILENAME:
            continue
        if n.startswith("save_"):
            auto_paths.append(p)
        else:
            custom_paths.append(p)

    auto_paths.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    custom_paths.sort(key=lambda p: os.path.getmtime(p), reverse=True)

    slots = []
    # 自动存档保持原本的 "存档 1, 存档 2 ..." 显示，方便老玩家熟悉。
    for idx, p in enumerate(auto_paths, start=1):
        try:
            ts = os.path.getmtime(p)
            time_label = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
        except OSError:
            time_label = ""
        label = list(mp.SAVE_SLOT_PREFIX) + nb2msg(idx)
        explanation = [time_label] if time_label else []
        slots.append((label, explanation, p))
    # 玩家自定义命名的存档直接朗读文件名。
    for p in custom_paths:
        name = os.path.basename(p)
        try:
            ts = os.path.getmtime(p)
            time_label = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
        except OSError:
            time_label = ""
        label = [name]
        explanation = [time_label] if time_label else []
        slots.append((label, explanation, p))
    return slots


def _save_display_name(path):
    """读盘提示中使用的存档显示名（用于重命名 / 删除提示）。"""
    name = os.path.basename(path)
    if name.startswith("save_"):
        # 对自动命名的存档，使用时间字符串作为提示中的可读名字。
        try:
            ts = os.path.getmtime(path)
            return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
        except OSError:
            return name
    return name


def _refresh_save_menu(menu):
    """根据当前存档目录的内容重建给定的存档菜单。"""
    menu.clear_choices()
    menu.title = list(mp.SELECT_SAVE_SLOT)
    slots = _list_save_slots()
    for label, explanation, path in slots:
        menu.append(
            label,
            (_load_savegame_file, path, False),
            explanation,
            on_rename=(lambda p=path, m=menu: _rename_save(p, m)),
            on_delete=(lambda immediate, p=path, m=menu: _delete_save(p, m, immediate)),
        )
    menu.append(mp.BACK, CLOSE_MENU)


def _rename_save(old_path, menu):
    """重命名一个存档文件，并刷新菜单。"""
    saves_dir = current_saves_dir()
    if not os.path.isfile(old_path):
        voice.alert(mp.BEEP)
        _refresh_save_menu(menu)
        return
    # 编辑框从空开始，避免玩家需要先按多次 backspace 才能清空旧名字。
    # 玩家在菜单中浏览选中该项时已经听过当前名称，无需再次显示。
    new_name = input_text(mp.ENTER_NEW_NAME)
    # 玩家按 Esc 取消, 或没输入直接回车 (后者等价于取消, 比报错友好):
    if new_name is None or not new_name.strip():
        voice.alert(mp.CANCELED)
        return
    safe = _sanitize_filename(new_name)
    if not safe:
        voice.alert(mp.INVALID_NAME)
        return
    # 避免和系统保留的续玩存档冲突。
    if safe == RESUME_SAVE_FILENAME:
        voice.alert(mp.INVALID_NAME)
        return
    new_path = os.path.join(saves_dir, safe)
    if os.path.normcase(os.path.abspath(new_path)) == os.path.normcase(
        os.path.abspath(old_path)
    ):
        voice.alert(mp.CANCELED)
        return
    if os.path.exists(new_path):
        voice.alert(mp.INVALID_NAME)
        return
    try:
        os.rename(old_path, new_path)
    except OSError:
        voice.alert(mp.BEEP)
        return
    voice.alert(mp.RENAMED)
    _refresh_save_menu(menu)


def _delete_save(path, menu, immediate):
    """删除一个存档文件；immediate=False 时先询问。"""
    if not os.path.isfile(path):
        voice.alert(mp.BEEP)
        _refresh_save_menu(menu)
        return
    if not immediate:
        if not confirm_yes_no(list(mp.CONFIRM_DELETE) + [_save_display_name(path)]):
            voice.alert(mp.CANCELED)
            return
    try:
        os.remove(path)
    except OSError:
        voice.alert(mp.BEEP)
        return
    voice.alert(mp.DELETED)
    _refresh_save_menu(menu)


def restore_game():
    """打开存档槽菜单，让玩家用方向键选择不同的存档进行加载。"""
    slots = _list_save_slots()
    if not slots:
        voice.alert(mp.NO_SAVE_FOUND)
        return
    menu = Menu(mp.SELECT_SAVE_SLOT, menu_type="submenu")
    _refresh_save_menu(menu)
    menu.run()


def has_resume_save():
    """是否存在当前 mod 专属的"继续未完成的游戏"存档。"""
    return os.path.exists(current_resume_save_path())


def resume_unfinished_game():
    """加载当前 mod 下玩家上次退出时自动保留的存档，并删除该存档（一次性）。"""
    path = current_resume_save_path()
    if not os.path.exists(path):
        voice.alert(mp.BEEP)
        return
    _load_savegame_file(path, delete_on_success=True)


def open_user_folder():
    webbrowser.open(CONFIG_DIR_PATH)


class TrainingMenu:
    def _add_ai(self, ai_type):
        self._players.append(ai_type)
        self._factions.append("random_faction")
        self._players_menu.update_menu(self._build_players_menu())

    def _run_game(self):
        from .achievements_menu import resolve_training_faction
        from .card_loadout import loadout_available
        from .card_loadout_menu import select_card_loadout

        alliances = ["1"] + ["2"] * (len(self._players) - 1)
        human_faction = resolve_training_faction(self._factions[0])
        if human_faction and human_faction != "random_faction":
            self._factions[0] = human_faction
        game = TrainingGame(self._map, self._players, self._factions, alliances)
        if loadout_available(human_faction):
            game.card_loadout = select_card_loadout(human_faction)
        else:
            game.card_loadout = []
        game.card_loadout_faction = human_faction
        try:
            game.treaty_minutes = getattr(self, "_treaty_minutes", 0) or 0
        except Exception:
            pass
        seed = getattr(self, "_random_seed", None)
        if seed is not None:
            game.seed = int(seed)
        game.run()
        return CLOSE_MENU

    def _set_faction(self, pn, r):
        self._factions[pn] = r
        self._players_menu.update_menu(self._build_players_menu())

    def _add_faction_menus(self, menu):
        for pn, (p, pr) in enumerate(zip(self._players, self._factions)):
            for r in ["random_faction"] + rules.factions:
                if r != pr:
                    menu.append(
                        [p,] + style.get(r, "title"), (self._set_faction, pn, r)
                    )

    def _treaty_label(self):
        minutes = getattr(self, "_treaty_minutes", 0) or 0
        if minutes <= 0:
            return mp.TREATY + [":"] + mp.NO_TREATY
        else:
            return mp.TREATY + nb2msg(minutes) + mp.MINUTES

    def _set_treaty(self, minutes):
        try:
            self._treaty_minutes = int(minutes)
        except Exception:
            self._treaty_minutes = 0
        # 条约选择后，进入邀请电脑界面
        self._open_players_menu()

    def _open_treaty_menu(self):
        menu = Menu(mp.MAKE_A_SELECTION, menu_type="submenu")
        menu.append(mp.TREATY + [":"] + mp.NO_TREATY, (self._set_treaty, 0))
        for m in (5, 10, 15, 20):
            menu.append(mp.TREATY + nb2msg(m) + mp.MINUTES, (self._set_treaty, m))
        menu.append(mp.CANCEL, CLOSE_MENU)
        menu.run()

    def _open_mode_menu(self, m):
        # 地图已选，直接选择条约
        self._players = [config.login]
        self._factions = ["random_faction"]
        self._map = m
        self._treaty_minutes = 0
        res.set_map(m)
        try:
            self._open_treaty_menu()
        finally:
            res.set_map()

    def _open_random_map_menu(self):
        from .randommap_menu import RandomMapMenu

        def on_ready(m, seed, treaty_minutes):
            self._players = [config.login]
            self._factions = ["random_faction"]
            self._map = m
            self._treaty_minutes = treaty_minutes
            self._random_seed = seed
            res.set_map(m)
            try:
                self._open_players_menu()
            finally:
                res.set_map()

        RandomMapMenu(on_ready).run()

    def _build_players_menu(self):
        menu = Menu(menu_type="submenu")  # 指定这是子菜单
        if len(self._players) < self._map.nb_players_max:
            self._add_ai_invite_menu(menu)
        if len(self._players) >= self._map.nb_players_min:
            menu.append(mp.START, self._run_game)
        if len(rules.factions) > 1:
            self._add_faction_menus(menu)
        menu.append(mp.CANCEL, CLOSE_MENU, mp.CANCEL_THIS_GAME)
        return menu

    def _add_ai_invite_menu(self, menu):
        for ai_type in get_menu_ai_difficulties():
            menu.append(ai_invite_label(ai_type), (self._add_ai, ai_type))

    def _open_players_menu(self):
        res.set_map(self._map)
        try:
            self._players_menu = self._build_players_menu()
            self._players_menu.loop()
        finally:
            res.set_map()

    def run(self):
        # 播放创建游戏菜单音乐
        sound.play_game_creation_music()
        menu = Menu(mp.START_A_GAME_ON, remember="mapmenu", menu_type="submenu")
        menu.append(mp.RMG_RANDOM_MAP, self._open_random_map_menu)
        for m in res.multiplayer_maps():
            menu.append(m.title, (self._open_mode_menu, m))
        menu.append(mp.QUIT2, None)
        menu.run()
        # 恢复主菜单音乐
        sound.play_menu_music()


def campaign_menu():
    Menu(
        mp.CAMPAIGN,
        [(c.title, c) for c in res.campaigns()]
        + [(mp.BACK, CLOSE_MENU)],
        menu_type="submenu",
    ).loop()


def _build_single_player_menu_choices():
    """构建单人游戏子菜单选项（含动态的"继续未完成的游戏"）。"""
    choices = []
    if has_resume_save():
        choices.append(
            [
                mp.CONTINUE_UNFINISHED_GAME,
                resume_unfinished_game,
                mp.CONTINUE_UNFINISHED_GAME_EXPLANATION,
            ]
        )
    choices.extend(
        [
            (mp.CAMPAIGN, campaign_menu),
            (mp.START_A_GAME_ON, TrainingMenu().run),
            (mp.RESTORE, restore_game),
            (mp.BACK, CLOSE_MENU),
        ]
    )
    return choices


def single_player_menu():
    from .lib.resource import res

    res.load_rules_and_ai()
    from .achievements import build_current_rank_msgs

    rank_msgs = build_current_rank_msgs()
    if rank_msgs:
        voice.menu(rank_msgs[0])

    # 每轮重新构建菜单，使得"继续未完成的游戏"能在取消/续玩后及时出现或消失，
    # 并始终指向磁盘上最新的续玩存档（与 main_menu 行为一致）。
    while True:
        menu = Menu(
            mp.MAKE_A_SELECTION,
            _build_single_player_menu_choices(),
            menu_type="submenu",
        )
        menu.run()
        if menu.end_loop:
            break


def server_menu():
    Menu(
        mp.WHAT_KIND_OF_SERVER,
        [
            (
                mp.SIMPLE_SERVER,
                (start_server_and_connect, "admin_only"),
                mp.SIMPLE_SERVER_EXPLANATION,
            ),
            (
                mp.PUBLIC_SERVER,
                (start_server_and_connect, ""),
                mp.PUBLIC_SERVER_EXPLANATION,
            ),
            (
                mp.PRIVATE_SERVER,
                (start_server_and_connect, "admin_only no_metaserver"),
                mp.PRIVATE_SERVER_EXPLANATION,
            ),
            (mp.CANCEL, None),
        ],
        menu_type="submenu"  # 指定这是子菜单
    ).run()


def set_and_launch_mod(mods):
    config.mods = mods
    config.save()
    res.set_mods(config.mods)
    
    # 在更新菜单前播放新mod的菜单音乐
    sound.clear_music_cache()  # 清除音乐缓存，确保重新加载
    sound.play_menu_music()    # 播放新mod的菜单音乐
    
    main_menu()  # update the menu title
    raise SystemExit


def mods_menu():
    res.update_packages()
    mods_menu = Menu(mp.MODS, menu_type="submenu")  # 指定这是子菜单
    mods_menu.append([0], (set_and_launch_mod, ""))
    for mod in res.available_mods():
        mods_menu.append(mod_menu_label(res.packages, mod), (set_and_launch_mod, mod))
    mods_menu.append(mp.BACK, CLOSE_MENU)
    mods_menu.run()
    return CLOSE_MENU


def set_and_launch_soundpack(soundpacks):
    config.soundpacks = soundpacks
    config.save()
    res.set_soundpacks(config.soundpacks)
    
    # 在更新菜单前播放新音效包的菜单音乐
    sound.clear_music_cache()  # 清除音乐缓存，确保重新加载
    sound.play_menu_music()    # 播放新的菜单音乐
    
    main_menu()  # update the menu title
    raise SystemExit


def soundpacks_menu():
    res.update_packages()
    soundpacks_menu = Menu(mp.SOUNDPACKS, menu_type="submenu")  # 指定这是子菜单
    soundpacks_menu.append(mp.NOTHING, (set_and_launch_soundpack, ""))
    for soundpack in res.available_soundpacks():
        soundpacks_menu.append(
            mod_menu_label(res.packages, soundpack),
            (set_and_launch_soundpack, soundpack),
        )
    soundpacks_menu.append(mp.BACK, CLOSE_MENU)
    soundpacks_menu.run()
    return CLOSE_MENU


def _layered_hotkeys_active():
    from .hotkey_editor import get_layered_hotkeys_scheme

    return get_layered_hotkeys_scheme() != 0


def _hotkey_scheme_status_msgs(is_active):
    return mp.HOTKEY_SCHEME_ACTIVE if is_active else mp.HOTKEY_SCHEME_INACTIVE


def _build_hotkeys_menu_choices(set_scheme):
    layered_active = _layered_hotkeys_active()
    return [
        (
            mp.LAYERED_HOTKEYS + mp.COMMA + _hotkey_scheme_status_msgs(layered_active),
            (set_scheme, 1),
        ),
        (
            mp.CLASSIC_HOTKEYS + mp.COMMA + _hotkey_scheme_status_msgs(not layered_active),
            (set_scheme, 0),
        ),
        (mp.BACK, CLOSE_MENU),
    ]


def _refresh_hotkeys_menu(menu, set_scheme):
    layered_active = _layered_hotkeys_active()
    new_menu = Menu(
        mp.HOTKEYS_MENU,
        _build_hotkeys_menu_choices(set_scheme),
        default_choice_index=0 if layered_active else 1,
        menu_type="submenu",
    )
    menu.update_menu(new_menu)
    menu.choice_index = 0 if layered_active else 1
    menu._say_choice()


def hotkeys_menu():
    from .hotkey_editor import (
        get_layered_hotkeys_scheme,
        set_layered_hotkeys_scheme,
    )
    from .hotkey_remapping_menu import announce_hotkey_overrides_mod

    layered_active = _layered_hotkeys_active()
    menu_ref = [None]

    announce_hotkey_overrides_mod()

    def set_scheme(value):
        value = int(value)
        if get_layered_hotkeys_scheme() == value:
            menu_ref[0]._say_choice()
            return
        set_layered_hotkeys_scheme(value)
        voice.item(mp.HOTKEYS_SCHEME_APPLIED)
        _refresh_hotkeys_menu(menu_ref[0], set_scheme)

    menu = Menu(
        mp.HOTKEYS_MENU,
        _build_hotkeys_menu_choices(set_scheme),
        default_choice_index=0 if layered_active else 1,
        menu_type="submenu",
    )
    menu_ref[0] = menu
    menu.loop()


def open_voices_folder():
    """Open the user voices folder (Nuance / SAPI pack install location)."""
    from .paths import VOICES_PATH

    try:
        readme = os.path.join(VOICES_PATH, "README.txt")
        with open(readme, "w", encoding="utf-8") as f:
            f.write(
                "SoundRTS2 游戏语音安装说明\n"
                "=========================\n\n"
                "主语音库：玩家操作与菜单。副语音库：对局内被动事件。\n"
                "选项 → 语音库设置 可分别调整；菜单内按 F3 可启用或禁用副语音。\n\n"
                "SAPI 音库：先安装到 Windows。部分音库（如 VW Julie）只有 32 位，\n"
                "游戏会通过 tools/sapi32 调用。也可在本目录建子文件夹 + voice.ini\n"
                "（title=中文名，sapi=系统语音名）。\n\n"
                "可选：将 Nuance 数据包放到 voices/nuance/ 后可在列表中选用。\n"
            )
    except Exception:
        pass
    webbrowser.open(VOICES_PATH)


def import_nuance_apple_voices():
    """Copy Mist World Apple pack into user/voices/nuance (one-time)."""
    from .lib import nuance_tts

    def _progress(msg):
        try:
            voice.info([msg])
        except Exception:
            pass

    try:
        voice.info(["开始导入苹果音库，约需一两分钟…"])
    except Exception:
        pass
    ok, detail = nuance_tts.import_from_mist_world(progress=_progress)
    if ok:
        voice.info(["导入完成，可在语音库设置中选择 Nuance"])
        try:
            from .lib import game_tts, voice_libs

            voice_libs.load_from_config()
            voice_libs.profile(voice_libs.PRIMARY)["voice"] = "nuance:Ting-Ting"
            voice_libs.save_to_config()
            voice_libs.apply_all()
            game_tts.speak("SoundRTS 语音测试", interrupt=True, channel=game_tts.PRIMARY)
        except Exception:
            pass
    else:
        voice.info(["导入失败", str(detail)])
    return ok


def voice_lib_editor(which: str):
    """Edit one voice library: Up/Down select param, Left/Right adjust, Enter/Esc back."""
    import pygame
    from pygame.locals import (
        KEYDOWN,
        K_DOWN,
        K_ESCAPE,
        K_KP_ENTER,
        K_LEFT,
        K_RETURN,
        K_RIGHT,
        K_UP,
        QUIT,
        USEREVENT,
    )

    from .lib import voice_libs
    from .lib.msgs import literal_text_msg

    voice_libs.load_from_config()
    rows = [
        voice_libs.PARAM_VOLUME,
        voice_libs.PARAM_PITCH,
        voice_libs.PARAM_RATE,
        voice_libs.PARAM_VOICE,
        "device",
    ]
    idx = 0
    title = (
        mp.VOICE_LIB_PRIMARY[0]
        if which == voice_libs.PRIMARY
        else mp.VOICE_LIB_SECONDARY[0]
    )

    def _announce_row():
        row = rows[idx]
        if row == "device":
            voice_libs.announce_device(which)
        else:
            voice_libs.profile(which)["param"] = int(row)
            voice_libs.announce_param_value(which)

    def _nudge(delta: int):
        row = rows[idx]
        if row == "device":
            voice_libs.cycle_device(which, step=1 if delta > 0 else -1)
            voice_libs.announce_device(which)
        else:
            voice_libs.profile(which)["param"] = int(row)
            voice_libs.nudge_param(which, delta)
            voice_libs.announce_param_value(which)

    hint = mp.VOICE_LIB_EDITOR_HINT[0] if mp.VOICE_LIB_EDITOR_HINT else ""
    voice.item(literal_text_msg(f"{title}。{hint}" if hint else title))
    _announce_row()
    pygame.event.clear([KEYDOWN])

    while True:
        e = pygame.event.poll()
        if e.type == QUIT:
            sys.exit()
        if e.type == USEREVENT:
            voice.update()
        elif e.type == KEYDOWN:
            pygame.event.clear([KEYDOWN])
            if e.key in (K_ESCAPE, K_RETURN, K_KP_ENTER):
                break
            if e.key == K_UP:
                idx = (idx - 1) % len(rows)
                _announce_row()
            elif e.key == K_DOWN:
                idx = (idx + 1) % len(rows)
                _announce_row()
            elif e.key == K_LEFT:
                _nudge(-5)
            elif e.key == K_RIGHT:
                _nudge(5)
            elif e.key in (pygame.K_F9, pygame.K_F10, pygame.K_F11, pygame.K_F12):
                try:
                    voice_libs.handle_hotkey(e.key, e.mod)
                except Exception:
                    voice.item(mp.BEEP)
        voice.update()
        time.sleep(0.01)


def voice_libs_menu():
    """选项 → 语音库设置：主/副库编辑器（经典 UI，无 wx）。"""
    from .lib import voice_libs

    voice_libs.load_from_config()
    menu = Menu(mp.VOICE_LIBS_MENU, menu_type="submenu")

    def _secondary_status():
        if int(getattr(config, "secondary_voice_enabled", 1)):
            return mp.VOICE_LIB_SECONDARY_ON
        return mp.VOICE_LIB_SECONDARY_OFF

    def _refresh_choices():
        menu.choices = [
            (mp.VOICE_LIB_HELP, None),
            (
                mp.VOICE_LIB_SECONDARY_TOGGLE,
                _toggle_secondary_voice,
                _secondary_status(),
            ),
            (
                mp.VOICE_LIB_PRIMARY,
                (lambda: voice_lib_editor(voice_libs.PRIMARY)),
            ),
            (
                mp.VOICE_LIB_SECONDARY,
                (lambda: voice_lib_editor(voice_libs.SECONDARY)),
            ),
            (mp.OPEN_VOICES_FOLDER, open_voices_folder),
            (mp.BACK, CLOSE_MENU),
        ]

    def _toggle_secondary_voice():
        voice_libs.toggle_secondary_voice_enabled(announce=True)
        _refresh_choices()

    _refresh_choices()
    menu.loop()


def options_menu():
    from .hotkey_remapping_menu import hotkey_mapping_menu

    Menu(
        mp.OPTIONS_MENU,
        [
            (mp.MODIFY_LOGIN, modify_login),
            (mp.HOTKEYS_MENU, hotkeys_menu),
            (mp.HOTKEY_MAPPING, hotkey_mapping_menu),
            (mp.MODS, mods_menu),
            (mp.SOUNDPACKS, soundpacks_menu),
            (mp.VOICE_LIBS_MENU, voice_libs_menu),
            (mp.OPEN_USER_FOLDER, open_user_folder),
            (mp.BACK, CLOSE_MENU),
        ],
        menu_type="submenu"  # 指定这是子菜单
    ).loop()


def quit_game():
    """退出游戏程序"""
    try:
        config.save_audio_settings()
        # 清理资源
        close_media()
    finally:
        # 确保无论如何都退出程序
        sys.exit()


def _build_main_menu_choices():
    from .achievements import achievements_enabled
    from .lib.resource import res

    res.load_rules_and_ai()
    choices = [
        [mp.SINGLE_PLAYER, single_player_menu, mp.SINGLE_PLAYER_EXPLANATION],
        [mp.MULTIPLAYER2, multiplayer_menu, mp.MULTIPLAYER2_EXPLANATION],
        [mp.SERVER, server_menu, mp.SERVER_EXPLANATION],
        [mp.OBSERVE_RECORDED_GAME, replay_menu],
    ]
    if achievements_enabled():
        choices.append([mp.ACHIEVEMENTS, achievements_menu, mp.ACHIEVEMENTS_EXPLANATION])
    choices.extend(
        [
            [mp.OPTIONS, options_menu, mp.OPTIONS_EXPLANATION],
            [mp.DOCUMENTATION, launch_manual],
            [mp.QUIT2, quit_game, mp.QUIT2_EXPLANATION],
        ]
    )
    return choices


def main_menu():
    # 每轮重新构建菜单，使得单人游戏子菜单中的动态选项能在游戏退出后实时出现/消失
    while True:
        Menu(
            [app_title() + ","] + mp.MAKE_A_SELECTION,
            _build_main_menu_choices(),
            menu_type="main"  # 明确指定这是主菜单
        ).run()


def launch_manual():
    p = "doc"
    try:
        lang = best_language_match(preferred_language, os.listdir(p))
    except OSError:
        voice.alert(mp.BEEP)
    else:
        webbrowser.open(os.path.join(p, lang, "help-index.htm"))


def main():
    try:
        init_media()
        revision_checker.start_if_needed()
        
        # 设置并启动菜单音乐
        sound.play_menu_music()
        
        if "connect_localhost" in sys.argv:
            connect_and_play()
        else:
            main_menu()
    except SystemExit:
        # 直接重新抛出SystemExit异常，不要在finally块中再次关闭媒体
        raise
    except:
        exception("error")
        # 在这里关闭媒体，而不是在finally块中
        close_media()
    # 不再需要finally块，因为其他异常已经在except块中处理
