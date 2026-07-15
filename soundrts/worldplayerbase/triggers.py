"""玩家触发器系统和游戏事件模块"""

import copy
import re

from .. import msgparts as mp
from ..definitions import rules
from ..lib.log import exception, warning
from ..lib.nofloat import to_int
from ..lib.msgs import nb2msg
from ..worldentity import NotEnoughSpaceError
from ..worldupgrade import is_an_upgrade
from ..worldskill import Skill
from ..worlditem import Item
from ..objective_announce import objective_prefix_msg, should_announce_objective_number
from .base import alliance_ids_equal, normalize_alliance_id
from .allied_control import mark_allied_control_changed


class TriggersManager:
    """触发器管理器"""
    
    def __init__(self, player):
        self.player = player

    def run_triggers(self):
        if not self.player.is_playing:
            return
        for t in self.player.triggers[:]:
            condition, action = t
            if self.player.my_eval(condition):
                self.player.my_eval(action)
                if not self.player.is_playing:  # after victory or defeat
                    break
                else:
                    self.player.triggers.remove(t)
                    self.player._eventually_reschedule(t)


class TriggersMixin:
    """触发器和游戏事件相关的方法混入类"""

    def _default_square_key(self):
        """返回一个安全的默认方格键，用于当未显式提供坐标时的回退。

        优先使用世界中的第一个方格名称（如"0,0"），否则回退到(0,0)元组键。
        """
        try:
            if getattr(self.world, "squares", None):
                return self.world.squares[0].name
        except Exception:
            pass
        return (0, 0)

    def _normalize_square_token(self, token):
        """将触发器中的坐标/别名标准化为 self.world.grid 可用的键。

        支持：
        - 直接是现有键（字符串如"x,y"或元组( x, y )）
        - 字符串形式的"x,y"或"(x,y)"（视为1基，需要转为0基）
        - 旧式字母+数字（如 a1, c12 等）
        - 地名/别名（在 world.name_to_square 中），其值为1基的"x,y"
        失败时返回 None。
        """
        if not isinstance(token, str):
            if token in getattr(self.world, "grid", {}):
                return token
            return token
        # 别名到坐标（1基）
        try:
            if isinstance(token, str) and token in getattr(self.world, "name_to_square", {}):
                token = self.world.name_to_square[token]
        except Exception:
            pass
        # 解析字符串
        if isinstance(token, str):
            t = token.strip()
            if t.startswith("(") and t.endswith(")"):
                t = t[1:-1].strip()
            # x,y 视为 1 基坐标并转为 0 基；必须在直接查 grid 之前做，
            # 否则像 lanes 9×3 地图上 "8,2" 会与 0 基键 "8,2" 冲突，导致
            # has_entered 8,2 指向错误方格（遗迹在 7,1 却永远触发不了）。
            if "," in t:
                parts = t.split(",")
                if len(parts) == 2:
                    try:
                        col1 = int(parts[0].strip())
                        row1 = int(parts[1].strip())
                        key = f"{col1-1},{row1-1}"
                        if key in self.world.grid:
                            return key
                        tup = (col1 - 1, row1 - 1)
                        if tup in self.world.grid:
                            return tup
                    except ValueError:
                        return None
            # 旧式 a1
            import re as _re
            if _re.match(r"^[a-z]+[0-9]+$", t):
                letters = ''.join([c for c in t if c.isalpha()])
                digits = ''.join([c for c in t if c.isdigit()])
                col = 0
                for ch in letters:
                    col = col * 26 + (ord(ch) - ord('a') + 1)
                col -= 1
                try:
                    row = int(digits) - 1
                except ValueError:
                    return None
                key = f"{col},{row}"
                if key in self.world.grid:
                    return key
                tup = (col, row)
                if tup in self.world.grid:
                    return tup
                return key
            if t in getattr(self.world, "grid", {}):
                return t
        return None

    def _map_square_key(self, place_or_token):
        """地图单位选择符使用的方格键（与触发器坐标写法一致）。"""
        grid = getattr(self.world, "grid", {})
        if hasattr(place_or_token, "name"):
            candidates = [place_or_token.name]
        else:
            candidates = [place_or_token]
        for cand in candidates:
            if cand is None:
                continue
            if cand in grid:
                return cand
        normalized = self._normalize_square_token(candidates[0])
        if normalized in grid:
            return normalized
        if isinstance(normalized, str) and "," in normalized:
            parts = normalized.split(",")
            try:
                tup = (int(parts[0]), int(parts[1]))
                if tup in grid:
                    return tup
            except ValueError:
                pass
        if isinstance(normalized, tuple) and normalized in grid:
            return normalized
        if normalized is not None:
            return normalized
        return candidates[0]

    def run_triggers(self):
        if not self.is_playing:
            return
        for t in self.triggers[:]:
            condition, action = t
            if self.my_eval(condition):
                self.my_eval(action)
                if not self.is_playing:  # after victory or defeat
                    break
                else:
                    self.triggers.remove(t)
                    self._eventually_reschedule(t)

    def _eventually_reschedule(self, t):
        condition, action = t
        if len(condition) == 3 and condition[0] == "timer":
            condition[1] = float(condition[1]) + float(condition[2])
            self.triggers.append((condition, action))

    def my_eval(self, l):
        if hasattr(self, "lang_" + l[0]):
            return getattr(self, "lang_" + l[0])(l[1:])
        return False

    def lang_timer(self, args):
        # float(args[0]) is probably not a problem for synchro since the result
        # of the multiplication is not reused after the comparison.
        # And for example: 6 == .1 * 60 (tested in Python 2.4)
        return self.world.time // 1000 >= float(args[0]) * self.world.timer_coefficient

    def lang_if(self, args):
        if self.my_eval(args[0]):
            self.my_eval(args[1])
        elif len(args) > 2:
            self.my_eval(args[2])

    def lang_do(self, args):
        """触发器动作：按顺序执行多个子动作（与 if 的 if/else 二选一不同）。

        用法::

            (do (cut_scene 7560) (remove_item mana_potion c3) (objective_complete 1))
        """
        for action in args:
            self.my_eval(action)

    def lang_not(self, args):
        return not self.my_eval(args[0])

    def lang_and(self, args):
        """触发器条件：所有子条件均成立时返回真。

        用法：``(and <条件1> <条件2> ...)``
        """
        for x in args:
            if not self.my_eval(x):
                return False
        return True

    def lang_find(self, args):
        default_square = self._default_square_key()
        for x in args:
            # 如果给出坐标/别名，更新默认方格
            sq_key = self._normalize_square_token(x)
            if sq_key is not None and sq_key in self.world.grid:
                default_square = sq_key
                continue
            # 否则视为类型，在默认方格中查找
            for o in self.world.grid[default_square].objects:
                if self.check_type(o, x):
                    break
            else:
                return False
        return True

    def lang_protect(self, args):
        time, select = args
        for o in self._units(select):
            o.is_protected = True
            o.protection_limit = self.world.time + to_int(time)

    def lang_team_defeat(self, args):
        for p in self.allied:
            p.defeat()

    def lang_play(self, args):
        self.push("play", args)

    def lang_alliance(self, args):
        """设置同盟编号。

        ``(alliance <编号>)`` — 仅触发器所属玩家。
        ``(alliance <编号> player1 computer1 ...)`` — 同时设置所列玩家。
        """
        if not args:
            return
        aid = normalize_alliance_id(args[0])
        targets = []
        for ref in args[1:]:
            player = self._resolve_map_player_ref(ref)
            if player is None:
                warning("alliance: unknown player %s", ref)
            else:
                targets.append(player)
        if not targets:
            targets = [self]
        for player in targets:
            player.client.alliance = aid
        self.world.update_alliances()
        self._ceasefire_among_players(self._players_sharing_alliance(aid))

    def _players_sharing_alliance(self, aid):
        if aid in (None, "None", "ai"):
            return []
        result = []
        for player in self.world.players:
            pa = getattr(player.client, "alliance", None)
            if pa is None or pa in (None, "None", "ai"):
                continue
            if alliance_ids_equal(pa, aid):
                result.append(player)
        return result

    def _unit_combat_target(self, unit):
        """解析单位当前攻击/追击目标（action、命令队列）。"""
        target = getattr(unit, "action_target", None)
        if target is not None:
            return target
        action = getattr(unit, "action", None)
        if action is not None:
            target = getattr(action, "target", None)
            if target is not None:
                return target
        orders = getattr(unit, "orders", None)
        if orders:
            order = orders[0]
            if getattr(order, "keyword", None) in ("attack", "go"):
                target = getattr(order, "target", None)
                if target is not None and getattr(target, "player", None) is not None:
                    return target
        return None

    def _halt_unit_combat(self, unit):
        """停止单位当前攻击/追击并清空战斗命令。"""
        unit.action_target = None
        if hasattr(unit, "orders") and getattr(unit, "orders", None) and hasattr(
            unit, "cancel_all_orders"
        ):
            unit.cancel_all_orders(unpay=False)
        elif hasattr(unit, "stop"):
            unit.stop()
        if hasattr(unit, "last_attacker"):
            unit.last_attacker = None

    def _ceasefire_among_players(self, players):
        """所列玩家之间一切正在进行的攻击/追击立刻停止。"""
        if not players:
            return
        allied = set(players)
        for player in self.world.players:
            to_scan = list(getattr(player, "units", []))
            if hasattr(player, "allied_control_units"):
                to_scan.extend(player.allied_control_units)
            seen = set()
            for unit in to_scan:
                if unit in seen or not getattr(unit, "presence", True):
                    continue
                seen.add(unit)
                uplayer = getattr(unit, "player", None)
                target = self._unit_combat_target(unit)
                if target is not None:
                    tplayer = getattr(target, "player", None)
                    if uplayer in allied and tplayer in allied:
                        self._halt_unit_combat(unit)
                elif uplayer in allied and getattr(unit, "last_attacker", None) is not None:
                    la = unit.last_attacker
                    lap = getattr(la, "player", None)
                    if lap in allied:
                        unit.last_attacker = None

    def _resolve_map_player_ref(self, ref):
        """将地图触发器里的 player1 / computer1 解析为运行时 Player 对象。"""
        if not ref:
            return None
        ref = str(ref).strip()
        m = re.match(r"^player(\d+)$", ref)
        if m:
            idx = int(m.group(1)) - 1
            humans = [p for p in self.world.players if getattr(p, "is_human", False)]
            if 0 <= idx < len(humans):
                return humans[idx]
            return None
        m = re.match(r"^computer(\d+)$", ref)
        if m:
            idx = int(m.group(1)) - 1
            computers = [
                p for p in self.world.players if not getattr(p, "is_human", False)
            ]
            if 0 <= idx < len(computers):
                return computers[idx]
            return None
        return None

    def lang_alliance_request(self, args):
        """触发器动作：让某玩家向另一玩家发起结盟申请（战役可用 Ctrl+F4 同意）。

        用法：
            (alliance_request <发起方>) — 发起方向触发器所属玩家申请
            (alliance_request <发起方> <接收方>)

        示例：首领收到密信后向玩家申请结盟::

            trigger player1 (npc_has_item knight_leader secret_letter)
                (do (cut_scene 7580) (alliance_request computer1))
        """
        if not args:
            return
        sender = self._resolve_map_player_ref(args[0])
        if sender is None:
            warning("alliance_request: unknown sender %s", args[0])
            return
        if len(args) >= 2:
            target = self._resolve_map_player_ref(args[1])
        else:
            target = self
        if target is None:
            warning("alliance_request: unknown target")
            return
        if getattr(target, "neutral", False):
            return
        try:
            if sender in getattr(target, "allied", []):
                return
        except Exception:
            pass
        target._ally_requests_from.add(sender.id)
        try:
            target.send_voice_important(mp.ALLIANCE_REQUEST_FROM + sender.name)
        except Exception:
            target.send_voice_important(mp.ALLIANCE_REQUEST_FROM)

    def lang_alliance_with(self, args):
        """触发器条件：触发器所属玩家是否与指定玩家已结盟。

        用法：``(alliance_with <player1|computer1|...>)``
        """
        if not args:
            return False
        other = self._resolve_map_player_ref(args[0])
        if other is None:
            return False
        return other in getattr(self, "allied", [])

    def lang_alliance_request_pending(self, args):
        """触发器条件：是否收到来自指定玩家的待处理结盟申请。

        用法：``(alliance_request_pending <player1|computer1|...>)``
        """
        if not args:
            return False
        sender = self._resolve_map_player_ref(args[0])
        if sender is None:
            return False
        return sender.id in getattr(self, "_ally_requests_from", set())

    def lang_alliance_declined_with(self, args):
        """触发器条件：是否已拒绝来自指定玩家的结盟申请。

        用法：``(alliance_declined_with <player1|computer1|...>)``
        """
        if not args:
            return False
        other = self._resolve_map_player_ref(args[0])
        if other is None:
            return False
        return other.id in getattr(self, "_alliance_declined_from", set())

    def _assign_map_select_slot(self, unit, place):
        """为地图/触发器刷出的单位分配稳定的 (方格, 类型, 序号) 标识。

        与 ``transfer_units`` / ``order`` 等单位选择符一致：``c2 3 footman``
        表示该方格上按 ``objects`` 遍历顺序计数的第 3 个 footman。
        """
        try:
            sq_key = self._map_square_key(place)
            if sq_key is None:
                return
            type_name = getattr(unit, "type_name", None)
            if not type_name:
                return
            if not hasattr(self, "_map_select_counters"):
                self._map_select_counters = {}
            counter_key = (sq_key, type_name)
            index = self._map_select_counters.get(counter_key, 0) + 1
            self._map_select_counters[counter_key] = index
            unit.map_select_square = sq_key
            unit.map_select_type = type_name
            unit.map_select_index = index
            self._assign_map_global_select_slot(unit)
        except Exception:
            pass

    def _assign_map_global_select_slot(self, unit):
        """为玩家名下单位分配跨方格的全局刷出序号（同类型从 1 递增）。"""
        try:
            type_name = getattr(unit, "type_name", None)
            if not type_name:
                return
            if not hasattr(self, "_map_global_select_counters"):
                self._map_global_select_counters = {}
            index = self._map_global_select_counters.get(type_name, 0) + 1
            self._map_global_select_counters[type_name] = index
            unit.map_select_global_index = index
        except Exception:
            pass

    def _parse_map_unit_selector(self, args):
        """解析 ``<方格> <序号> <类型>`` 选择符，失败返回 None。"""
        if len(args) < 3 or not re.match("^[0-9]+$", args[1]):
            return None
        sq_key = self._map_square_key(args[0])
        if sq_key is None:
            return None
        try:
            index = int(args[1])
        except (TypeError, ValueError):
            return None
        if index <= 0:
            return None
        return sq_key, index, args[2]

    def _parse_global_map_unit_selector(self, args):
        """解析 ``<序号> <类型>`` 全局刷出序号选择符，失败返回 None。"""
        if len(args) != 2 or not re.match("^[0-9]+$", args[0]):
            return None
        try:
            index = int(args[0])
        except (TypeError, ValueError):
            return None
        if index <= 0:
            return None
        return index, args[1]

    def _parse_global_map_unit_selector_with_owner(self, args):
        """解析 ``<序号> <类型> [enemy|ally]``，失败返回 None。"""
        if len(args) < 2 or len(args) > 3 or not re.match("^[0-9]+$", args[0]):
            return None
        try:
            index = int(args[0])
        except (TypeError, ValueError):
            return None
        if index <= 0:
            return None
        target_owner = "enemy"
        if len(args) == 3:
            if args[2] not in ("enemy", "ally"):
                return None
            target_owner = args[2]
        return index, args[1], target_owner

    def _unit_matches_map_select_type(self, unit, type_name):
        return (
            getattr(unit, "type_name", None) == type_name
            or type_name in getattr(unit, "expanded_is_a", [])
        )

    def _find_unit_by_map_select(self, square, index, type_name, owner_player=None):
        """按地图序号查找单位（单位移动后仍按刷出序号识别）。"""
        parsed = self._parse_map_unit_selector([square, str(index), type_name])
        if parsed is None:
            return None
        sq_key, idx, type_name = parsed
        for unit in self._iter_world_units():
            unit_sq = getattr(unit, "map_select_square", None)
            if unit_sq is not None:
                unit_sq = self._map_square_key(unit_sq)
            if unit_sq != sq_key:
                continue
            if getattr(unit, "map_select_type", None) != type_name:
                continue
            if getattr(unit, "map_select_index", None) != idx:
                continue
            if owner_player is not None and unit.player != owner_player:
                continue
            if not getattr(unit, "presence", True):
                continue
            return unit
        return None

    def _find_unit_by_global_map_select(self, index, type_name, owner_player=None):
        """按玩家全局刷出序号查找单位（与所在方格无关）。"""
        for unit in self._iter_world_units():
            if getattr(unit, "map_select_global_index", None) != index:
                continue
            if not self._unit_matches_map_select_type(unit, type_name):
                continue
            if owner_player is not None and unit.player != owner_player:
                continue
            if not getattr(unit, "presence", True):
                continue
            return unit
        return None

    def _was_map_select_unit_killed(self, square, index, type_name, target_owner="enemy"):
        """检查团队是否击杀了指定方格序号的单位。"""
        parsed = self._parse_map_unit_selector([square, str(index), type_name])
        if parsed is None:
            return False
        sq_key, idx, type_name = parsed
        slot_key = (sq_key, type_name, idx, target_owner)
        for p in self._has_killed_contributors():
            if slot_key in getattr(p, "_killed_map_slots", set()):
                return True
        return False

    def _was_global_map_select_unit_killed(self, index, type_name, target_owner="enemy"):
        """检查团队是否击杀了指定全局刷出序号的单位。"""
        slot_key = (type_name, index, target_owner)
        for p in self._has_killed_contributors():
            if slot_key in getattr(p, "_killed_global_map_slots", set()):
                return True
        return False

    def _map_select_unit_alive(self, square, index, type_name, *, survival_only=False):
        """指定刷出序号的单位是否仍存活（仅检查 self 名下单位）。"""
        unit = self._find_unit_by_map_select(square, index, type_name, owner_player=self)
        if unit is None:
            return False
        if survival_only and not getattr(unit, "provides_survival", False):
            return False
        return True

    def _map_select_global_unit_alive(self, index, type_name, *, survival_only=False):
        """指定全局刷出序号的单位是否仍存活（仅检查 self 名下单位）。"""
        unit = self._find_unit_by_global_map_select(index, type_name, owner_player=self)
        if unit is None:
            return False
        if survival_only and not getattr(unit, "provides_survival", False):
            return False
        return True

    def _unit_kill_record_matches_map_select(self, unit_record, sq_key, index, type_name):
        """死亡记录是否匹配指定 (方格, 序号, 类型)。"""
        if unit_record.get("map_select_type") != type_name:
            return False
        if unit_record.get("map_select_index") != index:
            return False
        rec_sq = unit_record.get("map_select_square")
        if rec_sq is not None:
            rec_sq = self._map_square_key(rec_sq)
        return rec_sq == sq_key

    def _unit_kill_record_matches_global_map_select(self, unit_record, index, type_name):
        """死亡记录是否匹配指定全局 (序号, 类型)。"""
        if unit_record.get("map_select_global_index") != index:
            return False
        rec_type = unit_record.get("type")
        if rec_type == type_name or type_name in unit_record.get("expanded_types", []):
            return True
        return unit_record.get("map_select_type") == type_name

    def _pick_player_units(self, player, square_key, count, type_name):
        """按方格+类型选取玩家单位（优先刷出序号，单位移动后仍有效）。"""
        norm_sq = self._map_square_key(square_key) if square_key is not None else None
        if norm_sq is not None:
            by_map_select = []
            for unit in getattr(player, "units", []):
                if not getattr(unit, "presence", True):
                    continue
                if unit.player != player:
                    continue
                if not self.check_type(unit, type_name):
                    continue
                unit_sq = getattr(unit, "map_select_square", None)
                if unit_sq is None:
                    continue
                if self._map_square_key(unit_sq) != norm_sq:
                    continue
                by_map_select.append(unit)
            if by_map_select:
                by_map_select.sort(key=lambda u: getattr(u, "map_select_index", 0))
                return by_map_select[:count]

            if norm_sq in self.world.grid:
                legacy = []
                for o in self.world.grid[norm_sq].objects:
                    if self.check_type(o, type_name) and o.player == player:
                        if not getattr(o, "presence", True):
                            continue
                        legacy.append(o)
                        if len(legacy) >= count:
                            break
                return legacy[:count]
            return []

        by_global = []
        for unit in getattr(player, "units", []):
            if not getattr(unit, "presence", True):
                continue
            if unit.player != player:
                continue
            if not self.check_type(unit, type_name):
                continue
            if getattr(unit, "map_select_global_index", None) is None:
                continue
            by_global.append(unit)
        if by_global:
            by_global.sort(key=lambda u: getattr(u, "map_select_global_index", 0))
            return by_global[:count]
        return []

    def _units_of_player(self, player, select):
        result = []
        default_square = self._default_square_key()
        n = 1
        for x in select:
            sq_key = self._normalize_square_token(x)
            if sq_key is not None and sq_key in self.world.grid:
                default_square = sq_key
                n = 1
            elif re.match("^[0-9]+$", x):
                n = int(x)
            else:
                result.extend(self._pick_player_units(player, default_square, n, x))
                n = 1
        return result

    def lang_transfer_units(self, args):
        """触发器动作：把某玩家的单位转移给另一玩家（改归属，非刷兵）。

        用法：
            (transfer_units <原属方> <新属方> [<方格> <数量> <类型> ...])
            (convert_units ...) / (change_owner ...) 为同义别名

        未写单位选择符时，转移原属方的全部存活单位。用于**改归属**（归顺、
        策反、俘虏等），不是结盟；结盟后协同指挥请用 ``allied_control``::

            trigger player1 (enemy_surrendered computer2)
                (do (transfer_units computer2 player1))
        """
        if len(args) < 2:
            return
        from_player = self._resolve_map_player_ref(args[0])
        to_player = self._resolve_map_player_ref(args[1])
        if from_player is None or to_player is None:
            warning("transfer_units: unknown player ref in %s", " ".join(args[:2]))
            return
        rest = args[2:]
        if rest:
            units = self._units_of_player(from_player, rest)
        else:
            units = [
                u
                for u in from_player.units
                if getattr(u, "presence", True)
            ]
        for u in units:
            if hasattr(u, "set_player"):
                u.set_player(to_player)
        self.world.update_alliances()

    def lang_convert_units(self, args):
        self.lang_transfer_units(args)

    def lang_change_owner(self, args):
        self.lang_transfer_units(args)

    def _align_alliance_for_allied_control(self, controller, ally):
        """使被移交指挥权的盟友与指挥者处于同一同盟（全盟友移交时）。"""
        try:
            aid = getattr(controller.client, "alliance", None)
            if aid in (None, "None"):
                return
            if getattr(ally.client, "alliance", None) != aid:
                ally.client.alliance = aid
                self.world.update_alliances()
        except Exception:
            pass

    def _ceasefire_for_allied_control_units(self, controller, units):
        """移交指挥权后：友方停攻被移交单位，被移交单位停攻指挥者同盟。"""
        protected = set(units)
        friendly_players = set(getattr(controller, "allied", (controller,)))
        for player in self.world.players:
            to_scan = list(getattr(player, "units", []))
            if hasattr(player, "allied_control_units"):
                to_scan.extend(player.allied_control_units)
            seen = set()
            for unit in to_scan:
                if unit in seen or not getattr(unit, "presence", True):
                    continue
                seen.add(unit)
                target = self._unit_combat_target(unit)
                if target in protected:
                    self._halt_unit_combat(unit)
                elif unit in protected and target is not None:
                    tplayer = getattr(target, "player", None)
                    if tplayer in friendly_players:
                        self._halt_unit_combat(unit)

    def _begin_allied_assist(self, ally):
        """让盟友可战斗单位从站岗切为追击，自主寻敌（不授予玩家指挥权）。"""
        self._begin_allied_assist_units(ally.units)

    def _begin_allied_assist_excluding(self, ally, excluded):
        """让盟友可战斗单位切为追击，但跳过已移交玩家指挥的单位。"""
        excluded = set(excluded)
        self._begin_allied_assist_units(
            u for u in ally.units if u not in excluded
        )

    def _begin_allied_assist_units(self, units):
        """让指定可战斗单位切为追击（站岗/进攻/防御 → 追击）。"""
        for u in units:
            if not getattr(u, "presence", True):
                continue
            if not (getattr(u, "mdg", 0) or getattr(u, "rdg", 0)):
                continue
            if getattr(u, "ai_mode", None) in ("guard", "offensive", "defensive"):
                u.ai_mode = "chase"

    def lang_allied_assist(self, args):
        """触发器动作：结盟后让盟友部队主动参战（**不能**被玩家选中指挥）。

        用法：
            (allied_assist <盟友玩家>)
            (allied_assist <盟友玩家> <方格> <数量> <类型> ...)

        结盟后盟友仍属对方玩家。未写单位选择符时，该盟友全部可战斗单位（站岗/进攻/防御）
        切为追击；写了选择符时仅匹配单位切为追击，其余不变。若需让玩家直接下令盟友，用
        ``allied_control``。"""

        if not args:
            return
        ally = self._resolve_map_player_ref(args[0])
        if ally is None:
            warning("allied_assist: unknown ally %s", args[0])
            return
        rest = args[1:]
        if rest:
            units = self._units_of_player(ally, rest)
            self._begin_allied_assist_units(units)
        else:
            self._begin_allied_assist(ally)

    def lang_allied_control(self, args):
        """触发器动作：让玩家获得对盟友部队的直接指挥权（选中、移动、攻击）。

        用法：
            (allied_control <盟友玩家>)
            (allied_control <盟友玩家> <指挥者玩家>)
            (allied_control <盟友玩家> [<指挥者>] <方格> <数量> <类型> ...)

        省略指挥者时，默认为触发器所属玩家。带单位选择符时仅移交匹配单位
        的指挥权；**未移交**的可战斗单位会从站岗切为追击，已移交单位保持原
        AI 模式由玩家下令。未写选择符时移交该盟友全部单位并全部切为追击。"""
        if not args:
            return
        ally = self._resolve_map_player_ref(args[0])
        if ally is None:
            warning("allied_control: unknown ally %s", args[0])
            return
        controller = self
        rest = args[1:]
        if rest:
            maybe_controller = self._resolve_map_player_ref(rest[0])
            if maybe_controller is not None:
                controller = maybe_controller
                rest = rest[1:]
        if controller is None:
            warning("allied_control: unknown controller")
            return
        if rest:
            units = self._units_of_player(ally, rest)
            controlled = set(getattr(controller, "allied_control_units_set", set()))
            for u in units:
                controlled.add(u)
            controller.allied_control_units_set = controlled
            mark_allied_control_changed(self.world)
            self._begin_allied_assist_excluding(ally, units)
            if units:
                self._ceasefire_for_allied_control_units(controller, units)
                self._ceasefire_among_players(
                    self._players_sharing_alliance(
                        getattr(controller.client, "alliance", None)
                    )
                )
        else:
            ac = tuple(getattr(controller, "allied_control", (controller,)))
            if ally not in ac:
                controller.allied_control = ac + (ally,)
                mark_allied_control_changed(self.world)
            self._begin_allied_assist(ally)
            self._align_alliance_for_allied_control(controller, ally)
            self._ceasefire_for_allied_control_units(controller, ally.units)

    def _units(self, select):
        return self._units_of_player(self, select)

    def _stop_units_of_player(self, player):
        """停止指定玩家的全部单位（含 allied_control 单位）。"""
        to_stop = list(getattr(player, "units", []))
        if hasattr(player, "allied_control_units"):
            to_stop.extend(player.allied_control_units)
        seen = set()
        for unit in to_stop:
            if unit in seen or not getattr(unit, "presence", True):
                continue
            seen.add(unit)
            self._halt_unit_combat(unit)

    def lang_stop_all_units(self, args):
        """停止单位战斗。

        无参数：停止触发器所属玩家。
        ``all``：停止全场所有玩家。
        否则将参数解析为 player1 / computer1 等并逐一停止。
        """
        if not args:
            self._stop_units_of_player(self)
            return
        if len(args) == 1 and str(args[0]).strip().lower() == "all":
            for player in self.world.players:
                self._stop_units_of_player(player)
            return
        for ref in args:
            player = self._resolve_map_player_ref(ref)
            if player is None:
                warning("stop_all_units: unknown player %s", ref)
                continue
            self._stop_units_of_player(player)

    def _release_yielded_units_of_player(self, player):
        for unit in list(getattr(player, "units", [])):
            if not getattr(unit, "presence", True):
                continue
            if hasattr(unit, "release_yield_invulnerability"):
                unit.release_yield_invulnerability()

    def _add_items_to_unit_inventory(self, unit, item_type, nb=1):
        """把若干件物品放入单位背包（战役剧情发奖等）。"""
        cls = rules.unit_class(item_type)
        if not self._is_item_type(item_type, cls):
            warning("add_inventory_item: unknown item %s", item_type)
            return
        inv = getattr(unit, "inventory", None)
        if not isinstance(inv, list):
            warning("add_inventory_item: unit has no inventory")
            return
        place = getattr(unit, "place", None)
        x = getattr(unit, "x", 0)
        y = getattr(unit, "y", 0)
        for _ in range(nb):
            cap = getattr(unit, "inventory_capacity", 0)
            if isinstance(cap, (list, tuple)):
                cap = cap[0] if cap else 0
            try:
                cap = int(cap)
            except (TypeError, ValueError):
                cap = 0
            if cap > 0 and len(inv) >= cap:
                break
            try:
                item = cls(place, x, y)
            except Exception:
                exception("add_inventory_item: couldn't create %s", item_type)
                break
            item.move_to(None, 0, 0)
            inv.append(item)
            if hasattr(item, "equip"):
                item.equip(unit)

    def lang_add_inventory_item(self, args):
        """把物品放入单位背包。

        用法：``(add_inventory_item <物品type_name> [<数量>] [<单位type_name>])``

        省略单位时，放入触发器所属玩家首个有背包的空位单位；数量默认 1。
        指定单位类型时支持 ``is_a`` 继承（如 ``raynor`` 可匹配 ``raynor6``/``raynor7``）。
        """
        if not args:
            return
        item_type = args[0]
        rest = list(args[1:])
        nb = 1
        if rest and re.match("^[0-9]+$", str(rest[0])):
            nb = int(rest.pop(0))
        unit = None
        if rest:
            type_name = rest[0]
            for u in self.units:
                if getattr(u, "presence", True) and self._unit_matches_map_select_type(
                    u, type_name
                ):
                    unit = u
                    break
        else:
            for u in self.units:
                cap = getattr(u, "inventory_capacity", 0)
                if isinstance(cap, (list, tuple)):
                    cap = cap[0] if cap else 0
                try:
                    cap = int(cap)
                except (TypeError, ValueError):
                    cap = 0
                if getattr(u, "presence", True) and cap > 0:
                    unit = u
                    break
        if unit is None:
            warning("add_inventory_item: no target unit for %s", item_type)
            return
        self._add_items_to_unit_inventory(unit, item_type, nb)

    def lang_set_ai_mode(self, args):
        """设置触发器所属玩家单位的 AI 模式。

        用法：``(set_ai_mode <offensive|defensive|guard|chase> [<方格> <数量> <类型> ...])``

        带单位选择符时仅作用于匹配单位；省略时作用于该玩家全部存活单位。
        """
        if not args:
            return
        mode = str(args[0])
        if mode not in ("offensive", "defensive", "guard", "chase"):
            warning("set_ai_mode: unknown mode %s", mode)
            return
        if len(args) == 1:
            targets = [
                u for u in self.units if getattr(u, "presence", True)
            ]
        else:
            targets = self._units(args[1:])
        for u in targets:
            u.ai_mode = mode

    def lang_set_yield_on_defeat(self, args):
        """设置触发器所属玩家单位的战败投降开关。

        用法：``(set_yield_on_defeat <0|1> [<方格> <数量> <类型> ...])``

        带单位选择符时仅作用于匹配单位；省略时作用于该玩家全部存活单位。
        """
        if not args:
            return
        try:
            value = int(args[0])
        except (TypeError, ValueError):
            warning("set_yield_on_defeat: invalid value %s", args[0])
            return
        if len(args) == 1:
            targets = [
                u for u in self.units if getattr(u, "presence", True)
            ]
        else:
            targets = self._units(args[1:])
        for u in targets:
            u.yield_on_defeat = value

    def lang_release_yielded_units(self, args):
        """结束指定玩家名下单位的认输无敌（Ctrl+F4/Shift+F4 后恢复可战）。

        无参数：触发器所属玩家。``all``：全场。否则解析 player1 / computer1 等。
        """
        if not args:
            self._release_yielded_units_of_player(self)
            return
        if len(args) == 1 and str(args[0]).strip().lower() == "all":
            for player in self.world.players:
                self._release_yielded_units_of_player(player)
            return
        for ref in args:
            player = self._resolve_map_player_ref(ref)
            if player is None:
                warning("release_yielded_units: unknown player %s", ref)
                continue
            self._release_yielded_units_of_player(player)

    def lang_order(self, args):
        default_square = self._default_square_key()
        n = 1
        select, orders = args
        for x in select:
            sq_key = self._normalize_square_token(x)
            if sq_key is not None and sq_key in self.world.grid:
                default_square = sq_key
                n = 1
            elif re.match("^[0-9]+$", x):
                n = int(x)
            else:
                for o in self.world.grid[default_square].objects:
                    if self.check_type(o, x) and (o.player == self):
                        for order in orders:
                            # 处理imperative修饰符，就像1.3.5.2版本一样
                            if order[0] == "imperative":
                                order = order[1:]
                                imperative = True
                            else:
                                imperative = False
                            o.take_order(order, forget_previous=False, imperative=imperative)
                        n -= 1
                        if n == 0:
                            break
                n = 1

    def lang_has_resources(self, args):
        """触发器条件：玩家某资源存量达到阈值。

        用法：``(has_resources resource2 8)`` 或 ``(has_resources 8 resource2)``
        数量为玩家可见的资源单位（与 starting_resources 一致，非内部千分位）。
        """
        if len(args) < 2:
            return False
        if re.match(r"^[0-9]+$", args[0]):
            amount = int(args[0])
            resource_type = args[1]
        else:
            resource_type = args[0]
            amount = int(args[1])
        from ..lib.nofloat import to_int

        index = rules.parse_resource_type(resource_type)
        if index is None or index >= len(self.resources):
            return False
        return self.resources[index] >= to_int(str(amount))

    def lang_has_gathered(self, args):
        """触发器条件：玩家累计采集某资源达到阈值（不含开局自带资源）。

        用法：``(has_gathered resource1 2500)`` 或 ``(has_gathered 2500 resource1)``
        数量为玩家可见的资源单位（与 starting_resources 一致，非内部千分位）。
        """
        if len(args) < 2:
            return False
        if re.match(r"^[0-9]+$", args[0]):
            amount = int(args[0])
            resource_type = args[1]
        else:
            resource_type = args[0]
            amount = int(args[1])
        from ..lib.nofloat import to_int

        index = rules.parse_resource_type(resource_type)
        if index is None or index >= len(self.resources):
            return False
        if not hasattr(self, "stats"):
            return False
        threshold = to_int(str(amount))
        starting = self.stats._starting_resources()
        gathered = max(0, self.stats.get("gathered", index) - starting[index])
        return gathered >= threshold

    def lang_grant_resources(self, args):
        """Grant resources to the trigger owner (exploration rewards, quests).

        Usage: ``(grant_resources 500 resource1 200 resource2)``
        or ``(grant_resources resource1 500)``.
        """
        if len(args) < 2:
            return
        from ..lib.nofloat import to_int

        pairs = list(args)
        i = 0
        while i < len(pairs):
            if re.match(r"^[0-9]+$", str(pairs[i])):
                amount = int(pairs[i])
                if i + 1 >= len(pairs):
                    break
                resource_type = pairs[i + 1]
                i += 2
            else:
                resource_type = pairs[i]
                if i + 1 >= len(pairs):
                    break
                amount = int(pairs[i + 1])
                i += 2
            index = rules.parse_resource_type(resource_type)
            if index is None or index >= len(self.resources):
                warning("grant_resources: unknown resource %s", resource_type)
                continue
            self.resources[index] += to_int(str(amount))

    def lang_has(self, args):
        nb = 1
        for x in args:
            if re.match("[0-9]+$", x):
                nb = int(x)
            else:
                remaining = nb
                for u in self.units:
                    if self.check_type(u, x):
                        remaining -= 1
                        if not remaining:
                            break
                if remaining:
                    uc = rules.unit_class(x)
                    if (
                        uc is not None
                        and is_an_upgrade(uc)
                        and x in getattr(self, "upgrades", ())
                    ):
                        remaining -= 1
                if remaining:
                    return False
                nb = 1
        return True

    def _iter_world_units(self):
        """遍历世界中所有玩家（含已出局玩家）的单位。"""
        players = list(getattr(self.world, "players", []))
        players += list(getattr(self.world, "ex_players", []))
        for p in players:
            for u in list(getattr(p, "units", [])):
                yield u

    def _npc_matches_selector(self, unit, selector):
        """判断 unit 是否匹配触发器里的 NPC 选择符（id 或 type_name）。"""
        if str(getattr(unit, "id", "")) == str(selector):
            return True
        if getattr(unit, "type_name", None) == selector:
            return True
        return False

    def _unit_holds_item(self, unit, item_type):
        # 已交付记录
        if item_type in getattr(unit, "received_items", ()):
            return True
        # 当前库存中持有该物品
        for it in getattr(unit, "inventory", []):
            if getattr(it, "type_name", None) == item_type:
                return True
        return False

    def lang_npc_has_item(self, args):
        """触发器条件：某个单位（通常是NPC/中立单位）是否已获得指定物品。

        用法：
            (npc_has_item <NPC选择符> <物品type_name> [所在方格])
            (npc_has_item <序号> <单位类型> <物品type_name>)
            (npc_has_item <方格> <序号> <单位类型> <物品type_name>)

        - <NPC选择符>：单位的 type_name（如 oldman）或单位 id。
        - <物品type_name>：物品类型（如 health_potion）。
        - [所在方格]：可选，限定NPC所在方格（用于区分同名NPC，如 a1 / "5,7"）。
        - 全局序号：``3 quest_npc short_sword`` 表示玩家名下第 3 个刷出的 quest_npc
          （与所在方格无关）。
        - 方格序号：与 ``transfer_units`` 相同，``b2 3 quest_npc short_sword`` 表示
          b2 上第 3 个（按该格刷出顺序编号，移动后仍有效）。

        典型用法：玩家把物品交给NPC后，本条件成立，再配合
        (objective_complete N) 或 (victory) 完成关卡目标。
        """
        if len(args) < 2:
            return False
        parsed = self._parse_map_unit_selector(args)
        if parsed is not None and len(args) >= 4:
            sq_key, index, type_name = parsed
            item_type = args[3]
            unit = self._find_unit_by_map_select(sq_key, index, type_name)
            return unit is not None and self._unit_holds_item(unit, item_type)
        if len(args) == 3 and re.match("^[0-9]+$", args[0]):
            try:
                index = int(args[0])
            except (TypeError, ValueError):
                return False
            if index <= 0:
                return False
            type_name = args[1]
            item_type = args[2]
            unit = self._find_unit_by_global_map_select(index, type_name)
            return unit is not None and self._unit_holds_item(unit, item_type)
        npc_selector = args[0]
        item_type = args[1]
        square_key = None
        if len(args) >= 3 and args[2]:
            square_key = self._normalize_square_token(args[2])
        for unit in self._iter_world_units():
            if not self._npc_matches_selector(unit, npc_selector):
                continue
            if square_key is not None:
                place = getattr(unit, "place", None)
                place_name = getattr(place, "name", place)
                if place_name != square_key and place != square_key:
                    continue
            if self._unit_holds_item(unit, item_type):
                return True
        return False

    def lang_has_item(self, args):
        """触发器条件：玩家是否已"找到"（拾取到）指定物品。

        用法：
            (has_item <物品type_name> [数量])

        - <物品type_name>：物品类型（如 lost_amulet）。
        - [数量]：可选，需要持有的数量，默认 1。

        判定方式：统计该玩家当前所有存活单位库存(inventory)中该类型
        物品的数量，达到所需数量即成立。典型用法：地图上放置一件
        物品，玩家移动单位过去右键拾取后，本条件成立，再配合
        (objective_complete N) 或 (victory) 完成关卡目标。

        注意：物品不能设置 consume_on_pickup（拾取即消耗），否则
        拾取后会被删除而不会进入库存，本条件将无法成立。
        """
        if not args:
            return False
        item_type = args[0]
        need = int(args[1]) if len(args) > 1 and args[1].isdigit() else 1
        count = 0
        for u in self.units:
            for it in getattr(u, "inventory", []):
                if getattr(it, "type_name", None) == item_type:
                    count += 1
                    if count >= need:
                        return True
        return False

    def lang_has_entered(self, args):
        """触发器条件：触发方单位进入指定方格。

        用法：``(has_entered <方格> [<单位类型> ...])``

        可写多个方格；可选单位类型（支持 ``is_a`` 继承）限定必须由匹配单位进入。
        """
        square_keys = []
        type_filters = []
        for x in args:
            sq_key = self._normalize_square_token(x)
            if sq_key is not None and sq_key in self.world.grid:
                square_keys.append(sq_key)
            else:
                type_filters.append(x)
        if not square_keys:
            return False
        for sq_key in square_keys:
            for o in self.world.grid[sq_key].objects:
                if o not in self.units or not getattr(o, "presence", True):
                    continue
                if type_filters:
                    if any(self._unit_matches_map_select_type(o, t) for t in type_filters):
                        return True
                else:
                    return True
        return False

    def lang_has_brought_item(self, args):
        """触发器条件：玩家是否将指定物品带到指定方格（携带在库存中即可）。

        用法：
            (has_brought_item <方格> <物品type_name> [数量])

        - <方格>：目标方格（如 c3、"3,3"）。
        - <物品type_name>：物品类型（如 mana_potion）。
        - [数量]：可选，需要在场单位身上合计持有的数量，默认 1。

        判定方式：在目标方格上查找该玩家的存活单位，统计这些单位
        库存中的指定物品数量；达到所需数量即成立。无需将物品丢弃到地面。

        与相关条件的区别：
        - ``find``：物品必须在地面方格上（通常需丢弃）
        - ``has_item``：玩家任意单位持有即可，不要求在某方格
        - ``has_entered``：玩家单位进入方格即可，不要求携带物品
        """
        if len(args) < 2:
            return False
        square_key = self._normalize_square_token(args[0])
        if square_key is None or square_key not in self.world.grid:
            return False
        item_type = args[1]
        need = int(args[2]) if len(args) > 2 and args[2].isdigit() else 1
        count = 0
        for o in self.world.grid[square_key].objects:
            if o not in self.units:
                continue
            if not getattr(o, "presence", True):
                continue
            for it in getattr(o, "inventory", []):
                if getattr(it, "type_name", None) == item_type:
                    count += 1
                    if count >= need:
                        return True
        return False

    def _unit_on_square(self, unit, square_key):
        place = getattr(unit, "place", None)
        if place is None:
            return False
        place_name = getattr(place, "name", place)
        return place_name == square_key or place == square_key

    def _destroy_inventory_item(self, unit, item):
        """从单位库存移除物品并销毁（用于触发器剧情交付等）。"""
        try:
            if getattr(unit, "is_inventory_weapon_item", None) and unit.is_inventory_weapon_item(item):
                unit.unequip_weapon_item(item)
            if getattr(unit, "is_inventory_armor_item", None) and unit.is_inventory_armor_item(item):
                unit.unequip_armor_item(item)
        except Exception:
            pass
        if hasattr(item, "unequip"):
            try:
                item.unequip(unit)
            except Exception:
                pass
        inv = getattr(unit, "inventory", None)
        if inv is not None and item in inv:
            inv.remove(item)
        item.move_to(None, 0, 0)
        self.world.schedule_after(100, lambda it=item: it.delete())

    def lang_remove_item(self, args):
        """触发器动作：从玩家单位库存中移除并销毁指定物品。

        用法：
            (remove_item <物品type_name> [方格] [数量])

        - <物品type_name>：物品类型（如 mana_potion）。
        - [方格]：可选，只从该方格上的玩家单位库存中移除（如 c3）。
        - [数量]：可选，默认 1。

        典型用法：玩家携带物品到达某地后，播放过场并“剧情上交”物品::

            trigger player1 (has_brought_item c3 mana_potion)
                (if (timer 0) (cut_scene 7560) (remove_item mana_potion c3) (objective_complete 1))
        """
        if not args:
            return
        item_type = args[0]
        square_key = None
        need = 1
        for token in args[1:]:
            if re.match("^[0-9]+$", token):
                need = int(token)
            else:
                sq = self._normalize_square_token(token)
                if sq is not None and sq in self.world.grid:
                    square_key = sq
        removed = 0
        for u in self.units:
            if square_key is not None and not self._unit_on_square(u, square_key):
                continue
            for item in list(getattr(u, "inventory", [])):
                if getattr(item, "type_name", None) != item_type:
                    continue
                self._destroy_inventory_item(u, item)
                removed += 1
                if removed >= need:
                    return

    def lang_remove_ground_item(self, args):
        """触发器动作：删除某方格地面上的指定类型物品。

        用法：``(remove_ground_item <方格> <物品type_name> [数量])``
        """
        if len(args) < 2:
            return
        square_key = self._normalize_square_token(args[0])
        if square_key is None or square_key not in self.world.grid:
            return
        item_type = args[1]
        need = int(args[2]) if len(args) > 2 and args[2].isdigit() else 1
        removed = 0
        for o in list(self.world.grid[square_key].objects):
            if not self.check_type(o, item_type):
                continue
            try:
                o.delete()
            except Exception:
                pass
            removed += 1
            if removed >= need:
                return

    def _nb_scouts(self, square):
        n = 0
        for u in self.units:
            if u.place == square:
                n += 1
        return n

    def _is_item_type(self, type_name, cls):
        if cls is None:
            return False
        try:
            if issubclass(cls, Item):
                return True
        except TypeError:
            pass
        try:
            return rules.get(type_name, "class") == ["item"]
        except Exception:
            return False

    def _add_items_on_square(self, cls, square, nb):
        """在方格地面上生成物品（与地图放置物品逻辑一致）。"""
        if not getattr(square, "can_receive", lambda t: True)("ground"):
            warning("cannot add item on square %s", getattr(square, "name", square))
            return
        for idx in range(nb):
            offset_x = (idx % 3 - 1) * 100
            offset_y = (idx // 3 - 1) * 100
            cls(square, square.x + offset_x, square.y + offset_y)

    def _add_unit(self, cls, square, target, decay, from_corpse, corpses, notify):
        land = None
        if from_corpse:
            if corpses:
                corpse = corpses.pop(0)
                x, y = corpse.x, corpse.y
                square = corpse.place
                corpse.delete()
            else:
                return
        elif target:
            x, y = target.x, target.y
            square = target if target in self.world.squares else target.place
        else:
            x, y, land = square.find_and_remove_meadow(cls)
        u = cls(self, square, x, y)
        u.building_land = land
        self._assign_map_select_slot(u, square)
        if decay:
            u.time_limit = self.world.time + decay
        if notify:
            u.notify("added")

    def lang_add_units(
        self, items, target=None, decay=0, from_corpse=False, corpses=None, notify=True
    ):
        # 防止观战者通过触发器获得单位
        if hasattr(self, '_is_pure_spectator') and self._is_pure_spectator:
            warning("Attempted to add units to spectator player via trigger, ignoring")
            return
            
        square_key = self._default_square_key()
        square = self.world.grid[square_key]
        nb = 1
        for i in items:
            sq_key = self._normalize_square_token(i)
            if sq_key is not None and sq_key in self.world.grid:
                square = self.world.grid[sq_key]
                nb = 1
            elif re.match("^[0-9]+$", i):
                nb = int(i)
            else:
                cls = rules.unit_class(i)
                if is_an_upgrade(cls):
                    self.upgrades.append(i)
                    self.send_voice_important(mp.OK)
                elif getattr(cls, "cls", None) == Skill:
                    self.send_voice_important(mp.BEEP)
                    warning("cannot add an skill")
                elif self._is_item_type(i, cls):
                    try:
                        self._add_items_on_square(cls, square, nb)
                    except Exception:
                        exception("couldn't add item: %s", cls)
                elif cls:
                    for _ in range(nb):
                        if not self.check_count_limit(i):
                            break
                        try:
                            self._add_unit(
                                cls, square, target, decay, from_corpse, corpses, notify
                            )
                        except NotEnoughSpaceError:
                            warning("not enough space")
                            self.units[-1].delete()
                        except:
                            exception("couldn't add unit: %s", cls)
                else:
                    self.send_voice_important(mp.BEEP)
                nb = 1

    def lang_no_enemy_left(self, unused_args):
        return not [
            p for p in self.world.players if self.player_is_an_enemy(p) and p.is_playing
        ]

    def lang_no_enemy_player_left(self, unused_args):
        # 只统计对局参与者（真人、邀请的电脑对手）。地图 ``computer_only``
        # 脚本 NPC（AI_type=="timers"）、战役触发器电脑、纯野生动物等
        # broadcasts_defeat_and_quit=False，虽可敌对/可战斗，但不计入多人默认
        # 胜利条件。否则 sg4 等图上邀请的初级电脑被 creep 消灭后，残留的
        # 非中立 computer_only 会挡住 (no_enemy_player_left)(victory)。
        # 需要清空全部敌对势力（含 NPC）时用 no_enemy_left。
        return not [
            p
            for p in self.world.match_participating_players
            if self.player_is_an_enemy(p)
        ]

    def lang_no_unit_left(self, unused_args):
        return not self.units

    def lang_no_building_left(self, unused_args):
        for u in self.units:
            if u.provides_survival:
                return False
        return True

    def lang_killed_target(self, args):
        """检查玩家是否杀死了目标单位
        
        参数:
            args[0]: 目标单位的ID或类型名
            args[1]: (可选)单位所属玩家，可以是"enemy"(敌方)或"ally"(己方)
            方格序号: (killed_target <方格> <序号> <类型> [enemy|ally])
            全局序号: (killed_target <序号> <类型> [enemy|ally])
            
        如果args[0]是一个单位ID，则检查该特定单位是否已被杀死
        如果args[0]是一个单位类型名，则检查是否已杀死指定类型的单位
        序号格式仅当击杀该方格上指定序号的单位时成立（击杀同类型其他序号无效）
        """
        # 检查参数
        if not args:
            return False

        parsed = self._parse_map_unit_selector(args)
        if parsed is not None:
            target_owner = "enemy"
            if len(args) > 3 and args[3] in ("enemy", "ally"):
                target_owner = args[3]
            sq_key, index, type_name = parsed
            return self._was_map_select_unit_killed(
                sq_key, index, type_name, target_owner
            )

        global_parsed = self._parse_global_map_unit_selector_with_owner(args)
        if global_parsed is not None:
            index, type_name, target_owner = global_parsed
            return self._was_global_map_select_unit_killed(
                index, type_name, target_owner
            )
            
        target_info = args[0]
        target_owner = "enemy"  # 默认检查杀死敌方单位
        
        # 如果指定了单位所属方
        if len(args) > 1:
            target_owner = args[1]
        
        # 根据单位ID或类型名和所属方检查是否杀死了目标
        if target_info.isdigit() or (target_info and target_info[0].isdigit()):
            # 检查ID的单位是否存在于世界对象中(已被杀死)并且是否记录了击杀
            killed_unit = target_info not in self.world.objects and self.has_killed_unit_with_id(target_info)
            
            # 如果没有设置单位所属方的筛选或者所属方匹配
            if killed_unit and hasattr(self, '_killed_unit_owners'):
                # 检查被杀死单位的所属方是否符合条件
                killed_unit_owner = self._killed_unit_owners.get(target_info)
                if target_owner == "enemy" and killed_unit_owner != "ally":
                    return True
                elif target_owner == "ally" and killed_unit_owner == "ally":
                    return True
                else:
                    return killed_unit  # 如果没有记录所属方，仍返回基本击杀判定
            return killed_unit
        else:
            # 如果是单位类型名，检查是否杀死过该类型的单位
            if target_owner == "enemy" and hasattr(self, '_killed_enemy_unit_types'):
                return target_info in self._killed_enemy_unit_types
            elif target_owner == "ally" and hasattr(self, '_killed_ally_unit_types'):
                return target_info in self._killed_ally_unit_types
            else:
                return self.has_killed_unit_of_type(target_info)  # 不区分所属方的旧行为
    
    def has_killed_unit_with_id(self, unit_id):
        """检查是否杀死了特定ID的单位"""
        # 这个方法可以通过存储被杀死单位的ID来实现
        # 为实现这一点，我们需要在Player类中添加一个新的属性来跟踪
        if not hasattr(self, '_killed_unit_ids'):
            self._killed_unit_ids = set()
        return unit_id in self._killed_unit_ids
    
    def has_killed_unit_of_type(self, unit_type):
        """检查是否杀死了指定类型的单位"""
        # 这个方法可以通过存储被杀死单位的类型来实现
        if not hasattr(self, '_killed_unit_types'):
            self._killed_unit_types = set()
        return unit_type in self._killed_unit_types
    
    def get_kill_count(self, unit_type):
        """获取指定类型单位的击杀数量"""
        if not hasattr(self, '_killed_unit_counts'):
            self._killed_unit_counts = {}
        return self._killed_unit_counts.get(unit_type, 0)

    def _has_killed_contributors(self):
        """合并本人、盟友与 allied_control 玩家的击杀（团队目标）。

        合作战役里多名人类同属一方时，任一盟友的击杀都计入本玩家的
        ``has_killed``；第 24/25 章里 computer1 补刀内奸同理。
        """
        contributors = set(getattr(self, "allied", ()) or ())
        contributors.update(getattr(self, "allied_control", ()) or ())
        return contributors

    def _has_killed_count(self, unit_type, target_owner="enemy"):
        """统计 contributors 对指定类型的击杀合计。"""
        total = 0
        for p in self._has_killed_contributors():
            if target_owner == "enemy":
                if hasattr(p, "_killed_enemy_unit_counts"):
                    total += p._killed_enemy_unit_counts.get(unit_type, 0)
                else:
                    total += p.get_kill_count(unit_type)
            elif target_owner == "ally":
                if hasattr(p, "_killed_ally_unit_counts"):
                    total += p._killed_ally_unit_counts.get(unit_type, 0)
            else:
                total += p.get_kill_count(unit_type)
        return total
    
    def lang_has_killed(self, args):
        """检查玩家及其团队是否杀死了指定数量的特定类型单位

        击杀数合计自 ``_has_killed_contributors()``（本人 + ``allied`` +
        ``allied_control``）。合作战役与战役里 NPC 盟友补刀均适用。
        
        支持两种格式:
        1. 基本格式 - 检查单一类型单位:
            args[0]: 需要的击杀数量
            args[1]: 单位类型名
            args[2]: (可选) 单位所属方，可以是"enemy"(敌方)或"ally"(己方)
            
        2. 高级格式 - 检查多种类型单位:
            args格式为: [数量1, 类型1, 数量2, 类型2, ..., 所属方(可选)]
            例如: (has_killed 1 footman 3 knight 7 catapult enemy)
        
        例如:
            (has_killed 5 dragon) - 检查是否击杀了5条龙(默认检查敌方单位)
            (has_killed 5 dragon enemy) - 明确检查是否击杀了5条敌方龙
            (has_killed 1 knight ally) - 检查是否击杀了1个友方骑士
            (has_killed 1 footman 3 knight 7 catapult enemy) - 检查是否击杀了多种类型的敌方单位
        """
        if len(args) < 2:
            return False
            
        # 确定是否使用高级格式（多种单位类型）
        # 高级格式的参数数量至少为4，且为偶数或偶数+1（最后可能有enemy/ally）
        is_advanced_format = len(args) >= 4 and (len(args) % 2 == 0 or (len(args) % 2 == 1 and args[-1] in ["enemy", "ally"]))
        
        # 确定单位所属方
        target_owner = "enemy"  # 默认检查敌方单位击杀
        
        if is_advanced_format:
            # 如果最后一个参数是enemy或ally，取出来作为所属方
            if args[-1] in ["enemy", "ally"]:
                target_owner = args[-1]
                # 移除所属方参数，使剩下的参数形成完整的数量-类型对
                args = args[:-1]
            
            # 检查每一对数量-类型组合
            for i in range(0, len(args), 2):
                if i + 1 >= len(args):
                    break  # 防止越界
                
                try:
                    required_count = int(args[i])
                    unit_type = args[i + 1]
                    current_count = self._has_killed_count(unit_type, target_owner)
                    
                    # 如果任一组合不满足要求，返回False
                    if current_count < required_count:
                        return False
                except (ValueError, IndexError):
                    return False
            
            # 如果所有要求都满足，返回True
            return True
        else:
            # 原来的基本格式处理
            try:
                required_count = int(args[0])
                unit_type = args[1]
                
                # 检查是否指定了单位所属方
                if len(args) > 2:
                    target_owner = args[2]
                
                return self._has_killed_count(unit_type, target_owner) >= required_count
            except (ValueError, IndexError):
                return False

    def _yield_contributors(self):
        return self._has_killed_contributors()

    def _yield_type_matches(self, actual_type, expanded_types, required_type):
        if actual_type is None:
            return False
        if actual_type == required_type:
            return True
        return required_type in (expanded_types or ())

    def record_unit_yielded(self, unit, attacker=None):
        """记录战败投降的单位（未死亡）。"""
        if not hasattr(self, "_yielded_unit_ids"):
            self._yielded_unit_ids = set()
        if not hasattr(self, "_yielded_unit_counts"):
            self._yielded_unit_counts = {}
        if not hasattr(self, "_yielded_enemy_unit_counts"):
            self._yielded_enemy_unit_counts = {}
        if not hasattr(self, "_yielded_ally_unit_counts"):
            self._yielded_ally_unit_counts = {}
        if not hasattr(self, "_unit_yield_records"):
            self._unit_yield_records = []

        if unit.id in self._yielded_unit_ids:
            return
        self._yielded_unit_ids.add(unit.id)

        unit_type = unit.type_name
        victim_expanded = set(getattr(unit, "expanded_is_a", []) or [])
        attacker_type = getattr(attacker, "type_name", None) if attacker is not None else None
        attacker_expanded = set(getattr(attacker, "expanded_is_a", []) or []) if attacker is not None else set()
        is_ally = unit.player in self.allied if unit.player else False
        self._unit_yield_records.append(
            {
                "victim_type": unit_type,
                "victim_expanded": victim_expanded,
                "attacker_type": attacker_type,
                "attacker_expanded": attacker_expanded,
                "is_enemy": not is_ally,
            }
        )
        self._yielded_unit_counts[unit_type] = self._yielded_unit_counts.get(unit_type, 0) + 1
        if is_ally:
            self._yielded_ally_unit_counts[unit_type] = (
                self._yielded_ally_unit_counts.get(unit_type, 0) + 1
            )
        else:
            self._yielded_enemy_unit_counts[unit_type] = (
                self._yielded_enemy_unit_counts.get(unit_type, 0) + 1
            )
        if hasattr(unit, "expanded_is_a"):
            for type_name in unit.expanded_is_a:
                self._yielded_unit_counts[type_name] = (
                    self._yielded_unit_counts.get(type_name, 0) + 1
                )
                if is_ally:
                    self._yielded_ally_unit_counts[type_name] = (
                        self._yielded_ally_unit_counts.get(type_name, 0) + 1
                    )
                else:
                    self._yielded_enemy_unit_counts[type_name] = (
                        self._yielded_enemy_unit_counts.get(type_name, 0) + 1
                    )

    def lang_units_yielded(self, args):
        """检查是否已击败（战败投降）指定数量的敌方/友方单位。

        格式与 ``has_killed`` 相同，例如::
            (units_yielded 1 npc_roland 2 npc_roland_guard enemy)
        """
        if len(args) < 2:
            return False

        is_advanced_format = len(args) >= 4 and (
            len(args) % 2 == 0 or (len(args) % 2 == 1 and args[-1] in ["enemy", "ally"])
        )
        target_owner = "enemy"
        if is_advanced_format:
            if args[-1] in ["enemy", "ally"]:
                target_owner = args[-1]
                args = args[:-1]
            for i in range(0, len(args), 2):
                if i + 1 >= len(args):
                    break
                try:
                    required_count = int(args[i])
                    unit_type = args[i + 1]
                    current_count = 0
                    for p in self._yield_contributors():
                        counts = getattr(p, "_yielded_enemy_unit_counts", {})
                        if target_owner == "ally":
                            counts = getattr(p, "_yielded_ally_unit_counts", {})
                        current_count += counts.get(unit_type, 0)
                    if current_count < required_count:
                        return False
                except (ValueError, IndexError):
                    return False
            return True
        try:
            required_count = int(args[0])
            unit_type = args[1]
            if len(args) > 2:
                target_owner = args[2]
            current_count = 0
            for p in self._yield_contributors():
                counts = getattr(p, "_yielded_enemy_unit_counts", {})
                if target_owner == "ally":
                    counts = getattr(p, "_yielded_ally_unit_counts", {})
                current_count += counts.get(unit_type, 0)
            return current_count >= required_count
        except (ValueError, IndexError):
            return False

    def _count_yields_by_attacker(self, attacker_type, victim_type, target_owner="enemy"):
        count = 0
        for player in self._yield_contributors():
            for record in getattr(player, "_unit_yield_records", []):
                if target_owner == "enemy" and not record.get("is_enemy", True):
                    continue
                if target_owner == "ally" and record.get("is_enemy", True):
                    continue
                if not self._yield_type_matches(
                    record.get("victim_type"),
                    record.get("victim_expanded"),
                    victim_type,
                ):
                    continue
                if self._yield_type_matches(
                    record.get("attacker_type"),
                    record.get("attacker_expanded"),
                    attacker_type,
                ):
                    count += 1
        return count

    def lang_units_yielded_by(self, args):
        """检查指定攻击者是否令足够数量的单位战败投降。

        格式::
            (units_yielded_by <攻击者类型> <数量> <受害者类型> [enemy|ally])

        攻击者与受害者类型均支持 ``is_a`` 继承（``expanded_is_a``）。
        """
        if len(args) < 3:
            return False
        try:
            attacker_type = args[0]
            required_count = int(args[1])
            victim_type = args[2]
            target_owner = args[3] if len(args) > 3 else "enemy"
            return self._count_yields_by_attacker(attacker_type, victim_type, target_owner) >= required_count
        except (ValueError, IndexError):
            return False

    def _get_campaign(self):
        world = getattr(self, "world", None)
        if world is not None:
            return getattr(world, "campaign", None)
        return None

    def lang_campaign_flag(self, args):
        """检查战役进度标记是否已设置。"""
        if not args:
            return False
        campaign = self._get_campaign()
        if campaign is None:
            return False
        return campaign.has_flag(args[0])

    def lang_set_campaign_flag(self, args):
        """设置战役进度标记（跨章节保留奖励）。"""
        if not args:
            return
        campaign = self._get_campaign()
        if campaign is None:
            warning("set_campaign_flag: no active campaign")
            return
        campaign.set_flag(args[0])

    def lang_unset_campaign_flag(self, args):
        """清除战役进度标记（用于重玩单章时复位误持久化的局内标记）。"""
        if not args:
            return
        campaign = self._get_campaign()
        if campaign is None:
            return
        if hasattr(campaign, "clear_flag"):
            campaign.clear_flag(args[0])

    def lang_map_flag(self, args):
        """检查当前地图局内标记（不跨章持久化）。"""
        if not args:
            return False
        return args[0] in getattr(self.world, "_map_flags", set())

    def lang_set_map_flag(self, args):
        """设置当前地图局内标记（不跨章持久化）。"""
        if not args:
            return
        if not hasattr(self.world, "_map_flags"):
            self.world._map_flags = set()
        self.world._map_flags.add(args[0])

    @staticmethod
    def _rmg_ruin_disc_flag(ruin_flag, player_id) -> str:
        return f"{ruin_flag}_disc_{player_id}"

    def lang_rmg_mark_ruin_discovered(self, args):
        """Mark an RMG ruin discovered for this player (victory / progress)."""
        if not args:
            return
        ruin_flag = args[0]
        self.lang_set_map_flag([self._rmg_ruin_disc_flag(ruin_flag, self.id)])

    def lang_rmg_ruin_discovered_by_self(self, args):
        """True when this player has personally discovered the listed ruin."""
        if not args:
            return False
        flags = getattr(self.world, "_map_flags", set())
        return self._rmg_ruin_disc_flag(args[0], self.id) in flags

    @staticmethod
    def _rmg_ruin_depth_flag(ruin_flag, player_id) -> str:
        return f"{ruin_flag}_depth_{player_id}"

    def lang_rmg_ruin_depth_claimed_by_self(self, args):
        if not args:
            return False
        flags = getattr(self.world, "_map_flags", set())
        return self._rmg_ruin_depth_flag(args[0], self.id) in flags

    def lang_rmg_claim_ruin_depth(self, args):
        if not args:
            return
        self.lang_set_map_flag([self._rmg_ruin_depth_flag(args[0], self.id)])

    def lang_rmg_all_ruins_discovered_by_allies(self, args):
        """True when every listed ruin was discovered by a member of allied_victory."""
        if not args:
            return False
        flags = getattr(self.world, "_map_flags", set())
        for ruin_flag in args:
            if not any(
                self._rmg_ruin_disc_flag(ruin_flag, ally.id) in flags
                for ally in self.allied_victory
            ):
                return False
        return True

    def lang_rmg_announce_ruins_remaining(self, args):
        """Voice progress after a ruin discovery (exploration mode RMG)."""
        if not args:
            return
        world_flags = getattr(self.world, "_map_flags", set())
        remaining = 0
        for ruin_flag in args:
            if not any(
                self._rmg_ruin_disc_flag(ruin_flag, ally.id) in world_flags
                for ally in self.allied_victory
            ):
                remaining += 1
        if remaining <= 0:
            return
        from ..lib.msgs import nb2msg

        if remaining == 1:
            payload = [5493]
        else:
            payload = [5492] + nb2msg(remaining) + [5431]

        def _emit(player):
            player.push("sequence", payload)

        _emit(self)
        try:
            for ally in getattr(self, "allied", []) or []:
                if ally is not self:
                    _emit(ally)
        except Exception:
            pass
    
    def record_skill_used(self, skill_name, caster=None, target=None):
        """记录玩家成功施放技能（供触发器条件 used_skill 使用）。"""
        if not skill_name:
            return
        if not hasattr(self, "_used_skill_counts"):
            self._used_skill_counts = {}
        if not hasattr(self, "_used_skill_events"):
            self._used_skill_events = []
        self._used_skill_counts[skill_name] = self._used_skill_counts.get(skill_name, 0) + 1
        self._used_skill_events.append(
            (skill_name, getattr(caster, "type_name", None), self._skill_event_target_type(target))
        )

    @staticmethod
    def _skill_event_target_type(target):
        if target is None:
            return None
        if hasattr(target, "type_name"):
            return target.type_name
        return None

    def _used_skill_count(self, skill_name, caster_type=None, target_type=None):
        if not hasattr(self, "_used_skill_events"):
            return 0
        count = 0
        for skill, caster, target in self._used_skill_events:
            if skill != skill_name:
                continue
            if caster_type and not self._unit_type_matches_filter(caster, caster_type):
                continue
            if target_type and not self._unit_type_matches_filter(target, target_type):
                continue
            count += 1
        return count

    def _unit_type_matches_filter(self, type_name, filter_name):
        if not type_name or not filter_name:
            return False
        if type_name == filter_name:
            return True
        try:
            cls = rules.unit_class(type_name)
        except (AttributeError, KeyError):
            cls = None
        expanded = getattr(cls, "expanded_is_a", ()) if cls else ()
        return filter_name in expanded

    def lang_used_skill(self, args):
        """触发器条件：玩家是否成功施放过指定技能。

        用法：
            (used_skill <技能type_name>)
            (used_skill <次数> <技能type_name>)
            (used_skill <技能type_name> <施法单位type_name> [<目标type_name>])

        示例：
            (used_skill sc_stim_pack)
            (used_skill sc_heal medivac)
            (used_skill sc_spawn_larva queen hatchery)
        """
        if not args:
            return False
        required = 1
        skill_name = None
        caster_type = None
        target_type = None
        idx = 0
        if args[0].isdigit():
            required = int(args[0])
            idx = 1
        if idx >= len(args):
            return False
        skill_name = args[idx]
        idx += 1
        if idx < len(args):
            caster_type = args[idx]
            idx += 1
        if idx < len(args):
            target_type = args[idx]
        return self._used_skill_count(skill_name, caster_type, target_type) >= required

    def record_unit_killed(self, unit):
        """记录被杀死的单位"""
        # 在单位死亡时调用此方法以记录ID和类型
        if not hasattr(self, '_killed_unit_ids'):
            self._killed_unit_ids = set()
        if not hasattr(self, '_killed_unit_types'):
            self._killed_unit_types = set()
        if not hasattr(self, '_killed_unit_counts'):
            self._killed_unit_counts = {}
        # 添加单位所属方的记录
        if not hasattr(self, '_killed_unit_owners'):
            self._killed_unit_owners = {}
        if not hasattr(self, '_killed_enemy_unit_types'):
            self._killed_enemy_unit_types = set()
        if not hasattr(self, '_killed_ally_unit_types'):
            self._killed_ally_unit_types = set()
        # 添加敌友单位击杀计数
        if not hasattr(self, '_killed_enemy_unit_counts'):
            self._killed_enemy_unit_counts = {}
        if not hasattr(self, '_killed_ally_unit_counts'):
            self._killed_ally_unit_counts = {}
        if not hasattr(self, '_killed_map_slots'):
            self._killed_map_slots = set()
        if not hasattr(self, '_killed_global_map_slots'):
            self._killed_global_map_slots = set()
            
        # 记录单位ID
        self._killed_unit_ids.add(unit.id)

        map_index = getattr(unit, "map_select_index", None)
        map_square = getattr(unit, "map_select_square", None)
        map_type = getattr(unit, "map_select_type", None)
        global_index = getattr(unit, "map_select_global_index", None)
        is_ally = unit.player in self.allied
        side = "ally" if is_ally else "enemy"
        if map_index and map_square and map_type:
            sq = self._map_square_key(map_square)
            self._killed_map_slots.add((sq, map_type, map_index, side))
        if global_index:
            slot_type = map_type or unit.type_name
            self._killed_global_map_slots.add((slot_type, global_index, side))
        
        # 记录单位类型
        self._killed_unit_types.add(unit.type_name)
        
        # 增加单位类型击杀计数
        self._killed_unit_counts[unit.type_name] = self._killed_unit_counts.get(unit.type_name, 0) + 1
        
        # 记录单位所属方
        is_ally = unit.player in self.allied
        self._killed_unit_owners[unit.id] = "ally" if is_ally else "enemy"
        
        # 根据单位所属方分别记录
        if is_ally:
            self._killed_ally_unit_types.add(unit.type_name)
            # 增加友方单位击杀计数
            self._killed_ally_unit_counts[unit.type_name] = self._killed_ally_unit_counts.get(unit.type_name, 0) + 1
        else:
            self._killed_enemy_unit_types.add(unit.type_name)
            # 增加敌方单位击杀计数
            self._killed_enemy_unit_counts[unit.type_name] = self._killed_enemy_unit_counts.get(unit.type_name, 0) + 1
        
        # 如果单位有扩展类型，也记录这些类型
        if hasattr(unit, 'expanded_is_a'):
            self._killed_unit_types.update(unit.expanded_is_a)
            # 同时为扩展类型增加计数
            for type_name in unit.expanded_is_a:
                self._killed_unit_counts[type_name] = self._killed_unit_counts.get(type_name, 0) + 1
                
                # 根据单位所属方分别记录扩展类型
                if is_ally:
                    self._killed_ally_unit_types.add(type_name)
                    # 增加友方扩展类型击杀计数
                    self._killed_ally_unit_counts[type_name] = self._killed_ally_unit_counts.get(type_name, 0) + 1
                else:
                    self._killed_enemy_unit_types.add(type_name)
                    # 增加敌方扩展类型击杀计数
                    self._killed_enemy_unit_counts[type_name] = self._killed_enemy_unit_counts.get(type_name, 0) + 1
                    
        # 添加被杀记录 - 记录单位被谁杀死
        if unit.player and hasattr(unit, 'killer_id'):
            killer_id = getattr(unit, 'killer_id', None)
            if killer_id is not None:
                killer = None
                for p in self.world.players:
                    if p.id == killer_id:
                        killer = p
                        break
                
                if killer:
                    if not hasattr(unit.player, '_units_killed_by'):
                        unit.player._units_killed_by = {}
                    
                    if killer.id not in unit.player._units_killed_by:
                        unit.player._units_killed_by[killer.id] = []
                    
                    death_record = {
                        'id': unit.id,
                        'type': unit.type_name,
                        'expanded_types': getattr(unit, 'expanded_is_a', []),
                        'time': self.world.time
                    }
                    if map_index and map_square and map_type:
                        death_record['map_select_square'] = self._map_square_key(map_square)
                        death_record['map_select_index'] = map_index
                        death_record['map_select_type'] = map_type
                    global_index = getattr(unit, "map_select_global_index", None)
                    if global_index:
                        death_record['map_select_global_index'] = global_index
                    unit.player._units_killed_by[killer.id].append(death_record)
    
    def lang_key_unit_killed(self, args):
        """检查关键单位是否被杀死，如果是则触发失败
        
        支持四种格式:
        1. 方格序号格式: (key_unit_killed <方格> <序号> <类型>)
        2. 全局序号格式: (key_unit_killed <序号> <类型>)
        3. 基本格式 - 检查单一类型单位:
            args[0]: 单位类型名(如knight, archer等)
        4. 高级格式 - 检查多种类型单位:
            args格式为: [类型1, 类型2, ...]
            如(key_unit_killed knight archer)
        
        单位被杀死则返回True，可用于触发游戏失败条件
        """
        if not args:
            return False

        parsed = self._parse_map_unit_selector(args)
        if parsed is not None:
            sq_key, index, type_name = parsed
            if not hasattr(self, '_units_killed_by'):
                self._units_killed_by = {}
            for killed_units in self._units_killed_by.values():
                for unit_record in killed_units:
                    if self._unit_kill_record_matches_map_select(
                        unit_record, sq_key, index, type_name
                    ):
                        return True
            return False

        global_parsed = self._parse_global_map_unit_selector(args)
        if global_parsed is not None:
            index, type_name = global_parsed
            if not hasattr(self, '_units_killed_by'):
                self._units_killed_by = {}
            for killed_units in self._units_killed_by.values():
                for unit_record in killed_units:
                    if self._unit_kill_record_matches_global_map_select(
                        unit_record, index, type_name
                    ):
                        return True
            return False
            
        # 确保初始化杀死记录结构
        if not hasattr(self, '_units_killed_by'):
            self._units_killed_by = {}
            
        # 检查每种类型的单位
        for unit_type in args:
            # 获取所有玩家杀死的该类型单位
            for player_id, killed_units in self._units_killed_by.items():
                for unit_record in killed_units:
                    if unit_record['type'] == unit_type or unit_type in unit_record.get('expanded_types', []):
                        return True
                        
        return False
        
    def lang_key_units_killed(self, args):
        """检查是否有指定数量的关键单位被杀死，如果达到则触发失败
        
        支持两种格式:
        1. 基本格式 - 检查单一类型单位数量:
            args[0]: 需要检查的单位数量(如5)
            args[1]: 单位类型名(如knight, archer等)
            
        2. 高级格式 - 检查多种类型单位数量:
            args格式为: [数量1, 类型1, 数量2, 类型2, ...]
            如(key_units_killed 3 knight 5 archer)
        
        当指定数量的单位被杀死时返回True，可用于触发游戏失败条件
        """
        if len(args) < 2:
            return False
            
        # 确保初始化杀死记录结构
        if not hasattr(self, '_units_killed_by'):
            self._units_killed_by = {}
            
        # 确定是否使用高级格式（多种单位类型）
        is_advanced_format = len(args) >= 4 and len(args) % 2 == 0
        
        if is_advanced_format:
            # 用于跟踪每种单位类型的死亡计数
            kill_counts = {}
            
            # 统计所有玩家杀死的单位
            for player_id, killed_units in self._units_killed_by.items():
                for unit_record in killed_units:
                    unit_type = unit_record['type']
                    kill_counts[unit_type] = kill_counts.get(unit_type, 0) + 1
                    # 同时计算扩展类型
                    for exp_type in unit_record.get('expanded_types', []):
                        kill_counts[exp_type] = kill_counts.get(exp_type, 0) + 1
            
            # 检查每一对数量-类型组合
            for i in range(0, len(args), 2):
                if i + 1 >= len(args):
                    break
                
                try:
                    required_count = int(args[i])
                    unit_type = args[i + 1]
                    
                    # 获取该类型单位的死亡数量
                    killed_count = kill_counts.get(unit_type, 0)
                    
                    # 如果数量未达到要求，返回False
                    if killed_count < required_count:
                        return False
                except (ValueError, IndexError):
                    return False
            
            # 如果所有组合都满足条件，返回True
            return True
        else:
            # 基本格式处理
            try:
                required_count = int(args[0])
                unit_type = args[1]
                
                # 计算该类型单位的死亡数量
                killed_count = 0
                
                # 统计所有玩家杀死的该类型单位
                for player_id, killed_units in self._units_killed_by.items():
                    for unit_record in killed_units:
                        if unit_record['type'] == unit_type or unit_type in unit_record.get('expanded_types', []):
                            killed_count += 1
                
                # 返回是否达到要求数量
                return killed_count >= required_count
            except (ValueError, IndexError):
                return False

    def victory(self):
        # 必须遍历 players 的快照：``p.defeat()`` 对非观察者（含战役里的电脑）会走到
        # ``quit_game()`` -> ``self.world.players.remove(self)``，在原列表上边遍历边删
        # 会跳过紧随其后的玩家。历史 bug：战役里有 2 个电脑时，victory() 打败第 1 个
        # 后跳过第 2 个，导致完成任务目标也不结束游戏，必须再手动消灭第 2 个电脑才胜利。
        for p in self.world.players[:]:
            if p.is_playing:
                if p in self.allied_victory:
                    p.has_victory = True
                    p.stats.freeze()
                else:
                    p.defeat()

    def defeat(self, force_quit=False):
        self.has_been_defeated = True
        self.stats.freeze()
        # 地图脚本 NPC、战役电脑等不算对局参与者，被击败时不播报。
        if self in self.world.true_players() and self.broadcasts_defeat_and_quit:
            self.broadcast_to_others_only(self.name + mp.HAS_BEEN_DEFEATED)
        for u in self.units[:]:
            u.delete()
        
        # 立即检查剩余玩家的胜利条件
        # 当玩家被击败时需要立即检查胜利条件
        self._check_victory_conditions_after_player_change()
        
        if force_quit:
            self.quit_game()
        elif self.observer_if_defeated and self._has_other_playing_humans():
            # 多人局：真人被淘汰后旁观剩余真人；单机对 AI 时不应旁观。
            if self.world.at_least_two_camps:
                self.send_voice_important(
                    mp.YOU_HAVE_BEEN_DEFEATED + mp.YOU_ARE_NOW_IN_OBSERVER_MODE
                )
            else:
                self.send_voice_important(mp.YOU_HAVE_BEEN_DEFEATED)
        else:
            if (
                self.observer_if_defeated
                and self.is_human
                and self in self.world.true_players()
            ):
                self.send_voice_important(mp.YOU_HAVE_BEEN_DEFEATED)
            self.quit_game()

    def lang_victory(self, unused_args):
        self.victory()

    def lang_personal_victory(self, unused_args):
        """Win without eliminating other survivors (RMG survival multiplayer)."""
        if self.has_been_defeated or self.has_victory:
            return
        self.has_victory = True
        self.stats.freeze()
        # 单机/最后一名仍在场的真人：与 defeat() 对称，应结束对局并结算。
        if not self._has_other_playing_humans():
            self.quit_game()

    def lang_defeat(self, unused_args):
        self.defeat()

    def lang_cut_scene(self, args):
        """处理切场景指令
        
        支持两种格式:
        1. cut_scene = ID - 使用等号格式，等号会被自动忽略
        2. cut_scene ID - 使用空格格式
        
        ID可以是数字、字母或中文字符
        如果ID被双引号括起来，则作为一个整体处理并去掉引号
        """
        # 过滤掉等号（如果存在）
        filtered_args = [arg for arg in args if arg != "="]
        if not filtered_args:
            return
        
        # 导入sound模块
        from ..lib import sound
        
        # 暂停背景音乐（保留播放位置）
        sound.pause_music()
        
        # 检查是否被双引号括起来或包含中文字符
        if (len(filtered_args) >= 1 and 
            (filtered_args[0].startswith('"') and filtered_args[-1].endswith('"') or
             any('\u4e00' <= c <= '\u9fff' for c in " ".join(filtered_args)))):
            # 将内容作为一个整体处理
            content = " ".join(filtered_args)
            # 去掉首尾的引号（如果有）
            if content.startswith('"') and content.endswith('"'):
                content = content.strip('"')
            payload = [content]
        else:
            # 按原来的方式处理
            payload = filtered_args

        # 过场剧情对触发器所属玩家及其全部盟友广播：
        # 合作战役里所有人类玩家同盟为一队，于是人人都能听到剧情对白
        # （与目标 add/complete 的盟友广播逻辑一致）。单人时 allied 仅含自己，
        # 行为不变。display-only，确定性安全。
        def _emit(p):
            p.push("sequence", payload)
            # 消息播放完后恢复背景音乐（从暂停位置继续）
            p.push("resume_music", None)

        _emit(self)
        try:
            for ally in getattr(self, "allied", []) or []:
                if ally is self:
                    continue
                _emit(ally)
        except Exception:
            pass

    def _parse_objective_content(self, args):
        """解析 add_objective / add_secondary_objective 的目标描述参数。"""
        if len(args) >= 2 and args[1] == "=":
            content_args = args[2:]
        else:
            content_args = args[1:]

        if content_args and (
            (content_args[0].startswith('"') and content_args[-1].endswith('"')) or
            any('\u4e00' <= c <= '\u9fff' for c in " ".join(content_args))
        ):
            content = " ".join(content_args)
            if content.startswith('"') and content.endswith('"'):
                content = content.strip('"')
            return [content]

        all_digits = True
        for token in content_args:
            if not (isinstance(token, str) and token.isdigit()):
                all_digits = False
                break
        if all_digits:
            return content_args

        converted = []
        for token in content_args:
            if isinstance(token, str) and token.isdigit():
                converted.extend(nb2msg(int(token)))
            else:
                converted.append(token)
        return converted

    def _add_objective_impl(self, args, optional=False):
        from .base import Objective

        n = args[0]
        objective_content = self._parse_objective_content(args)
        o = Objective(n, objective_content, optional=optional)
        key = Objective.storage_key(n, optional=optional)

        if key not in self.objectives:
            self.objectives[key] = o
            if not optional:
                self._required_objective_numbers.add(str(n))

            from ..lib import sound

            sound.pause_music()
            prefix = mp.SECONDARY_OBJECTIVE if optional else mp.PRIMARY_OBJECTIVE
            show_number = should_announce_objective_number(self, optional=optional)
            announcement = objective_prefix_msg(prefix, n, show_number) + o.description
            self.send_voice_important(announcement)
            self.push("resume_music", None)

            try:
                for ally in getattr(self, 'allied', []) or []:
                    if ally is self:
                        continue
                    if not hasattr(ally, 'objectives'):
                        continue
                    if key not in ally.objectives:
                        ally_obj = Objective(n, o.description, optional=optional)
                        ally.objectives[key] = ally_obj
                        if not optional:
                            ally._required_objective_numbers.add(str(n))
                        try:
                            ally_show_number = should_announce_objective_number(
                                ally, optional=optional
                            )
                            ally_announcement = objective_prefix_msg(
                                prefix, n, ally_show_number
                            ) + ally_obj.description
                            ally.send_voice_important(ally_announcement)
                        except Exception:
                            pass
            except Exception:
                pass

    def lang_register_objective(self, args):
        """登记主要目标编号（通关所需），不显示、不播报。

        用于 timer 0 预先登记全部目标，避免分步 add_objective 导致提前胜利；
        配合完成上一目标后再 add_objective 下一目标，实现 F9 逐步显示。
        """
        if not args:
            return
        for n in args:
            self._required_objective_numbers.add(str(n))
        try:
            for ally in getattr(self, "allied", []) or []:
                if ally is self:
                    continue
                ally_required = getattr(ally, "_required_objective_numbers", None)
                if ally_required is None:
                    continue
                for n in args:
                    ally_required.add(str(n))
        except Exception:
            pass

    def lang_add_objective(self, args):
        """添加主要目标（必须完成才能通关）。

        支持两种格式:
        1. add_objective n = "内容"
        2. add_objective n 内容
        """
        self._add_objective_impl(args, optional=False)

    def lang_add_secondary_objective(self, args):
        """添加次要/可选目标（可不完成即通关）。"""
        self._add_objective_impl(args, optional=True)

    def _complete_objective_impl(self, args, optional=False):
        from .base import Objective
        from .. import msgparts as mp

        if not args:
            return
        n = args[0]
        key = Objective.storage_key(n, optional=optional)
        if optional:
            if key not in self.objectives:
                return
        elif key not in self.objectives and str(n) not in self._required_objective_numbers:
            return

        from ..lib import sound

        description = None
        if key in self.objectives:
            description = self.objectives[key].description
            del self.objectives[key]

        if not optional:
            self._completed_objective_numbers.add(str(n))

        if description is not None:
            sound.pause_music()
            self.send_voice_important(mp.OBJECTIVE_COMPLETE + description)

        try:
            for ally in getattr(self, 'allied', []) or []:
                if ally is self:
                    continue
                ally_description = None
                if hasattr(ally, 'objectives') and key in ally.objectives:
                    ally_description = ally.objectives[key].description
                    del ally.objectives[key]
                if not optional:
                    ally_completed = getattr(ally, "_completed_objective_numbers", None)
                    if ally_completed is not None:
                        ally_completed.add(str(n))
                if ally_description is not None:
                    try:
                        ally.send_voice_important(
                            mp.OBJECTIVE_COMPLETE + ally_description
                        )
                    except Exception:
                        pass
        except Exception:
            pass

        self._try_mission_victory()
        if not self.has_victory:
            self.push("resume_music", None)

    def lang_objective_complete(self, args):
        """完成主要目标 N（与可选目标编号独立）。"""
        self._complete_objective_impl(args, optional=False)

    def lang_secondary_objective_complete(self, args):
        """完成可选目标 N（与主要目标编号独立）。"""
        self._complete_objective_impl(args, optional=True)

    def lang_objective_abandon(self, args):
        """放弃可选目标（如拒绝结盟）；不播报完成，仅移除目标。"""
        from .base import Objective

        if not args:
            return
        n = args[0]
        key = Objective.storage_key(n, optional=True)
        if key not in self.objectives:
            return
        o = self.objectives[key]
        if not getattr(o, "optional", False):
            warning("objective_abandon only applies to secondary objectives: %s", n)
            return

        from ..lib import sound

        sound.pause_music()
        self.send_voice_important(mp.OPTIONAL_OBJECTIVE_ABANDONED + o.description)
        del self.objectives[key]

        try:
            for ally in getattr(self, 'allied', []) or []:
                if ally is self:
                    continue
                if hasattr(ally, 'objectives') and key in ally.objectives:
                    try:
                        ally.send_voice_important(
                            mp.OPTIONAL_OBJECTIVE_ABANDONED + ally.objectives[key].description
                        )
                    except Exception:
                        pass
                    del ally.objectives[key]
        except Exception:
            pass

        if not self.has_victory:
            self.push("resume_music", None)

    def lang_ai(self, args):
        self.set_ai(args[0])

    def lang_faction(self, args):
        if args and args[0] in rules.factions:
            self.faction = args[0]
        else:
            warning("unknown faction: %s", " ".join(args))

    def lang_unit_lost(self, args):
        """检查特定单位是否已经死亡或丢失
        
        参数:
            方格序号: (unit_lost <方格> <序号> <类型>)
            全局序号: (unit_lost <序号> <类型>)
            args[0]: 单位类型名(如knight, archer等)或单位ID
            
        用法示例:
            (unit_lost 1 townhall) - 玩家名下第 1 个 townhall 已丢失（不限方格）
            (unit_lost a1 3 footman) - a1 上第 3 个 footman 已丢失
            (unit_lost knight) - 所有 knight 都已死亡或丢失
            (unit_lost 42) - ID 为 42 的单位已死亡或丢失
        """
        if not args:
            return False

        parsed = self._parse_map_unit_selector(args)
        if parsed is not None:
            sq_key, index, type_name = parsed
            return not self._map_select_unit_alive(sq_key, index, type_name)

        global_parsed = self._parse_global_map_unit_selector(args)
        if global_parsed is not None:
            index, type_name = global_parsed
            return not self._map_select_global_unit_alive(index, type_name)
            
        unit_identifier = args[0]
        
        # 检查是否是单位ID
        if unit_identifier.isdigit() or (unit_identifier and unit_identifier[0].isdigit()):
            # 检查该ID的单位是否存在于世界中
            return not any(u.id == unit_identifier for u in self.units)
        else:
            # 检查该类型的单位是否在玩家单位中存在
            return not any(u.type_name == unit_identifier or 
                          unit_identifier in getattr(u, 'expanded_is_a', []) 
                          for u in self.units)
    
    def lang_units_lost(self, args):
        """检查是否失去了指定数量和类型的单位
        
        支持两种格式:
        1. 基本格式 - 检查单一类型单位:
            args[0]: 需要检查的单位数量(如5)
            args[1]: 单位类型名(如knight, archer等)
            
        2. 高级格式 - 检查多种类型单位:
            args格式为: [数量1, 类型1, 数量2, 类型2, ...]
            如(units_lost 3 knight 5 archer)表示失去了3个骑士和5个弓箭手
            
        返回True表示玩家失去了至少指定数量的单位
        """
        if len(args) < 2:
            return False
            
        # 确定是否使用高级格式（多种单位类型）
        is_advanced_format = len(args) >= 4 and len(args) % 2 == 0
        
        if is_advanced_format:
            # 检查每一对数量-类型组合
            for i in range(0, len(args), 2):
                if i + 1 >= len(args):
                    break
                
                try:
                    required_count = int(args[i])
                    unit_type = args[i + 1]
                    
                    # 计算该类型单位的当前数量
                    current_count = sum(1 for u in self.units if 
                                      u.type_name == unit_type or 
                                      unit_type in getattr(u, 'expanded_is_a', []))
                    
                    # 如果数量满足要求，继续检查下一组
                    # 注意: units_lost检查的是单位数量不足,所以当前数量应小于要求数量
                    if current_count >= required_count:
                        return False
                except (ValueError, IndexError):
                    continue
            
            # 如果所有组合都满足条件(当前数量都小于要求数量)，返回True
            return True
        else:
            # 基本格式处理
            try:
                required_count = int(args[0])
                unit_type = args[1]
                
                # 计算该类型单位的当前数量
                current_count = sum(1 for u in self.units if 
                                  u.type_name == unit_type or 
                                  unit_type in getattr(u, 'expanded_is_a', []))
                
                # 返回是否数量不足
                return current_count < required_count
            except (ValueError, IndexError):
                return False
    
    def lang_building_lost(self, args):
        """检查特定建筑是否已经被摧毁
        
        参数:
            方格序号: (building_lost <方格> <序号> <类型>)
            全局序号: (building_lost <序号> <类型>)
            args[0]: 建筑类型名(如townhall, barracks等)或建筑ID
            
        用法示例:
            (building_lost 1 townhall) - 玩家名下第 1 个 townhall 已被摧毁（不限方格）
            (building_lost a1 1 townhall) - a1 上第 1 个 townhall 已被摧毁
            (building_lost townhall) - 所有 townhall 都已被摧毁
            (building_lost 42) - ID 为 42 的建筑已被摧毁
        """
        if not args:
            return False

        parsed = self._parse_map_unit_selector(args)
        if parsed is not None:
            sq_key, index, type_name = parsed
            return not self._map_select_unit_alive(
                sq_key, index, type_name, survival_only=True
            )

        global_parsed = self._parse_global_map_unit_selector(args)
        if global_parsed is not None:
            index, type_name = global_parsed
            return not self._map_select_global_unit_alive(
                index, type_name, survival_only=True
            )
            
        building_identifier = args[0]
        
        # 检查是否是建筑ID
        if building_identifier.isdigit() or (building_identifier and building_identifier[0].isdigit()):
            # 检查该ID的建筑是否存在于世界中
            return not any(u.id == building_identifier and getattr(u, 'provides_survival', False) 
                          for u in self.units)
        else:
            # 检查该类型的建筑是否在玩家建筑中存在
            return not any((u.type_name == building_identifier or 
                           building_identifier in getattr(u, 'expanded_is_a', [])) and
                           getattr(u, 'provides_survival', False)
                           for u in self.units)
    
    def lang_buildings_lost(self, args):
        """检查是否失去了指定数量和类型的建筑
        
        支持两种格式:
        1. 基本格式 - 检查单一类型建筑:
            args[0]: 需要检查的建筑数量(如2)
            args[1]: 建筑类型名(如townhall, barracks等)
            
        2. 高级格式 - 检查多种类型建筑:
            args格式为: [数量1, 类型1, 数量2, 类型2, ...]
            如(buildings_lost 1 townhall 2 barracks)表示失去了1个主城和2个兵营
            
        返回True表示玩家失去了至少指定数量的建筑
        """
        if len(args) < 2:
            return False
            
        # 确定是否使用高级格式（多种建筑类型）
        is_advanced_format = len(args) >= 4 and len(args) % 2 == 0
        
        if is_advanced_format:
            # 检查每一对数量-类型组合
            for i in range(0, len(args), 2):
                if i + 1 >= len(args):
                    break
                
                try:
                    required_count = int(args[i])
                    building_type = args[i + 1]
                    
                    # 计算该类型建筑的当前数量
                    current_count = sum(1 for u in self.units if 
                                      (u.type_name == building_type or 
                                      building_type in getattr(u, 'expanded_is_a', [])) and
                                      getattr(u, 'provides_survival', False))
                    
                    # 如果数量满足要求，继续检查下一组
                    if current_count >= required_count:
                        return False
                except (ValueError, IndexError):
                    continue
            
            # 如果所有组合都满足条件(当前数量都小于要求数量)，返回True
            return True
        else:
            # 基本格式处理
            try:
                required_count = int(args[0])
                building_type = args[1]
                
                # 计算该类型建筑的当前数量
                current_count = sum(1 for u in self.units if 
                                  (u.type_name == building_type or 
                                   building_type in getattr(u, 'expanded_is_a', [])) and
                                   getattr(u, 'provides_survival', False))
                
                # 返回是否数量不足
                return current_count < required_count
            except (ValueError, IndexError):
                return False

    def _player_units_killed(self, killer_player):
        """获取被指定玩家杀死的单位记录
        
        参数:
            killer_player: 杀手玩家对象
            
        返回: 该玩家杀死的所有单位记录
        """
        if not hasattr(self, '_player_kill_records'):
            return []
        return self._player_kill_records.get(killer_player.id, [])