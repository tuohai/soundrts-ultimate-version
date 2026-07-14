import time

from .. import msgparts as mp
from ..clientmedia import modify_sfx_volume, modify_volume, sounds, voice
from ..clientmenu import _is_valid_chat_char, input_text
from ..lib import sound
from ..lib.log import warning, exception, debug
from ..lib.msgs import literal_text_msg, nb2msg


# 基础音频和语音功能
def cmd_say(interface):
    """发送聊天消息"""
    msg = input_text(msg=mp.ENTER_MESSAGE, max_length=200, char_filter=_is_valid_chat_char)
    if not msg:
        return

    # 确保消息作为文本发送而不是声音播放命令
    voice.confirmation([interface.player.client.login] + mp.SAYS + literal_text_msg(msg))
    interface.server.write_line("say " + msg)


def cmd_say_players(interface):
    """播报当前游戏中的玩家"""
    msg = []
    for p in interface.world.players:
        if getattr(p, "_is_pure_spectator", False):
            continue
        # 地图脚本 NPC、战役触发器电脑、纯野生动物等不算对局参与者，F11 不播报。
        if not p.broadcasts_defeat_and_quit:
            continue
        msg += p.name + mp.COMMA
    voice.item(msg)


def cmd_say_time(interface):
    """播报当前游戏时间和速度"""
    m, s = divmod(int(interface.last_virtual_time), 60)
    voice.item(
        nb2msg(m)
        + mp.MINUTES
        + nb2msg(s)
        + mp.SECONDS
        + mp.COMMA
        + mp.SPEED
        + ["%.1f" % interface._get_relative_speed()]
    )


# ====== 动态联盟：客户端侧命令 ======

def _diplo_id_sort_key(p):
    """按整数 ID 排序，避免 "1", "10", "2" 这种字典序怪象（>=10 个玩家时会
    很迷惑）。极端情况下 ID 不能转 int 就退化成 (1, str(id))，仍然稳定。"""
    pid = getattr(p, 'id', None)
    try:
        return (0, int(pid))
    except (TypeError, ValueError):
        return (1, str(pid))


def _diplo_is_alive(p):
    """已被淘汰/已获胜的玩家不应再进 F12 候选——给死人发结盟请求毫无意义。"""
    if getattr(p, 'has_been_defeated', False):
        return False
    if getattr(p, 'has_victory', False):
        return False
    return True


def _diplo_players(interface):
    world = getattr(interface, 'world', None)
    me = getattr(interface, 'player', None)
    if not world or not me:
        return []
    # 战役（mission）里没有真正的"对手玩家"，只有充当触发器脚本的电脑（ai_timers）
    # 或被 (ai ...) 触发器临时升格的电脑。它们都不参与玩家间外交，F12 不应能切到
    # 任何目标。历史 bug：战役里出现 2 个电脑时，被 (ai easy) 升格的那个电脑因为
    # AI_type 不再是 "timers" 而漏进了候选，F12 能切到它并把 login "ai_timers" 读出来。
    if getattr(world, 'is_campaign', False):
        return []
    # 中立 (`computer_only ... neutral`) 玩家**不**进 F12 候选：
    # 设计上把中立 creep 当成"环境/事件物"，不参与外交。
    # 引擎层 `cmd_diplomacy 'request'` 也会对 neutral 目标短路兜底。
    #
    # ai_timers（AI_type == "timers"，login "ai_timers"，UI 名 "NPC"）同样
    # 不进 F12 候选：它是计时器脚本驱动的 NPC，不参与玩家间外交。
    players = [p for p in world.players
               if p is not me
               and _diplo_is_alive(p)
               and not getattr(p, 'neutral', False)
               and getattr(p, 'AI_type', None) != 'timers']
    players.sort(key=_diplo_id_sort_key)
    return players


def _diplo_set_selected(interface, player):
    setattr(interface, '_diplo_selected_player_id', getattr(player, 'id', None))


def _diplo_get_selected(interface):
    pid = getattr(interface, '_diplo_selected_player_id', None)
    if not pid:
        return None
    for p in _diplo_players(interface):
        if p.id == pid:
            return p
    return None


def _diplo_advance_candidate(interface, reverse=False):
    players = _diplo_players(interface)
    if not players:
        return None
    idx_attr = '_diplo_idx'
    # 先把 cur 重锚定到"上次选中的那个玩家"在新列表里的位置；玩家被淘汰、
    # F12 列表收缩后旧的整数 idx 会指向错位的人。找不到就回退到上次的 idx，
    # 越界则重置为 -1（下一次推进会落到 0）。
    cur = -1
    selected_id = getattr(interface, '_diplo_selected_player_id', None)
    if selected_id is not None:
        for i, p in enumerate(players):
            if getattr(p, 'id', None) == selected_id:
                cur = i
                break
    if cur == -1:
        last = getattr(interface, idx_attr, -1)
        if 0 <= last < len(players):
            # selected_id 没匹配上但旧 idx 还在范围内，沿用让顺序连续。
            cur = last
        else:
            cur = -1
    if reverse:
        cur = (cur - 1) % len(players)
    else:
        cur = (cur + 1) % len(players)
    setattr(interface, idx_attr, cur)
    candidate = players[cur]
    _diplo_set_selected(interface, candidate)
    return candidate


def _diplo_relation_msg(interface, p):
    try:
        me = getattr(interface, 'player', None)
        if me and p in me.allied:
            return mp.ALLY
    except Exception:
        pass
    # 未结盟的中立单独标为"中立"，避免在 F12 列表里被误报为"敌人"。
    if getattr(p, 'neutral', False):
        return mp.NEUTRAL
    return mp.ENEMY


def cmd_select_alliance_candidate(interface, inc=1):
    """F12/Shift+F12 选择（或反向选择）同盟候选玩家"""
    reverse = False
    try:
        reverse = int(inc) < 0
    except Exception:
        reverse = False
    p = _diplo_advance_candidate(interface, reverse=reverse)
    if p is None:
        voice.item(mp.DIPLOMACY + mp.NO_CANDIDATE)
        return
    # 播报候选人 + 敌对/联盟状态
    # 注：``_diplo_players`` 已过滤掉 neutral 玩家，所以这里不再有 neutral 分支。
    try:
        voice.item(p.name + mp.COMMA + _diplo_relation_msg(interface, p))
    except Exception:
        voice.item([getattr(p.client, 'login', '?')] + mp.COMMA + _diplo_relation_msg(interface, p))


def cmd_alliance_request(interface):
    """F4 发送结盟申请，目标由最近一次选择确定"""
    me = getattr(interface, 'player', None)
    target = _diplo_get_selected(interface)
    if target is None:
        # 回退：若未选择过候选，尝试使用当前界面目标的玩家
        t = getattr(interface, 'target', None)
        if t is not None and hasattr(t, 'player') and t.player and t.player is not me:
            target = t.player
    if not me or not target:
        voice.item(mp.DIPLOMACY + mp.NO_CANDIDATE)
        return
    # 不允许给自己
    if target is me:
        voice.item(mp.BEEP)
        return
    # 如果本局锁定同盟，直接提示
    if getattr(interface.world, 'alliances_locked', False):
        voice.item(mp.ALLIANCES_LOCKED)
        return
    # 发送客户端命令到世界（由本地/联机协调器转发）
    interface.server.write_line(f"diplomacy request {target.id}")
    # 本地提示
    try:
        voice.item(mp.ALLY_WITH + target.name)
    except Exception:
        voice.item(mp.ALLY_WITH + [getattr(target.client, 'login', '?')])


def cmd_alliance_accept(interface):
    """Ctrl+F4 同意最近一条对我发起的同盟请求（或当前候选）"""
    if getattr(interface.world, 'alliances_locked', False):
        voice.item(mp.ALLIANCES_LOCKED)
        return
    target = _diplo_get_selected(interface)
    if target:
        interface.server.write_line(f"diplomacy accept {target.id}")
    else:
        # 未选择候选时，交由服务器选择最近的待处理请求
        interface.server.write_line("diplomacy accept")


def cmd_alliance_decline_or_cancel(interface):
    """Shift+F4 拒绝同盟或取消现有同盟"""
    if getattr(interface.world, 'alliances_locked', False):
        voice.item(mp.ALLIANCES_LOCKED)
        return
    target = _diplo_get_selected(interface)
    if target:
        interface.server.write_line(f"diplomacy decline_or_cancel {target.id}")
    else:
        # 未选择候选时，优先拒绝最近的待处理请求
        interface.server.write_line("diplomacy decline_or_cancel")


# 音乐控制功能
def cmd_toggle_music(interface):
    """开关音乐"""
    from .. import config

    music_enabled = sound.toggle_music()
    config.save_audio_settings()

    # 语音反馈
    if music_enabled:
        voice.item(mp.MUSIC_ON if hasattr(mp, "MUSIC_ON") else ["音乐已开启"])
        # 重新开始播放当前场景的音乐
        if interface.last_virtual_time > 0:  # 如果在游戏中
            # 检查是否是战役游戏
            is_campaign_game = False
            try:
                from ..lib.resource import res
                is_campaign_game = hasattr(res, '_campaign') and res._campaign is not None
            except Exception as e:
                exception(f"检查是否是战役游戏时出错: {e}")
            
            # 优先使用地图指定的音乐
            map_music = None
            if hasattr(interface, 'world') and interface.world:
                map_music = getattr(interface.world, 'map_music', None)
            
            # 获取阵营专属音乐（仅在非战役游戏中使用）
            faction_music = None
            try:
                # 获取当前玩家的阵营
                player_faction = None
                if hasattr(interface.player, 'faction') and interface.player.faction:
                    player_faction = interface.player.faction
                    
                # 如果玩家阵营不是字符串（而是对象），尝试获取类型名称
                if player_faction and not isinstance(player_faction, str):
                    if hasattr(player_faction, 'type_name'):
                        player_faction = player_faction.type_name
                
                # 设置玩家阵营全局变量
                if player_faction:
                    sound.set_player_faction(player_faction)
                
                # 只有在非战役游戏中才使用阵营音乐
                if not is_campaign_game:
                    from ..definitions import style
                    # 检查是否有对应的阵营专属音乐
                    if player_faction and hasattr(style, 'faction_music_settings'):
                        # 检查阵营ID是否在音乐设置中
                        if player_faction in style.faction_music_settings:
                            faction_music = style.faction_music_settings[player_faction]
                            debug(f"找到玩家阵营 {player_faction} 的专属音乐: {faction_music}")
            except Exception as e:
                exception(f"获取阵营专属音乐时出错: {e}")
            
            # 播放游戏音乐，让音乐系统根据游戏类型决定播放哪种音乐
            sound.play_game_music(map_music, faction_music)
    else:
        voice.item(mp.MUSIC_OFF if hasattr(mp, "MUSIC_OFF") else ["音乐已关闭"])


def cmd_music_volume_up(interface):
    """增加音乐音量"""
    from .. import config

    # 停止当前所有语音播报，确保音量播报能立即听到
    sound.stop()
    
    # 调整音量并获取百分比值（与主音量处理方式保持一致，传递1而不是0.1）
    volume_percent = sound.adjust_music_volume(1)
    config.save_audio_settings()

    # 播报音量（与主音量处理方式保持一致）
    voice.item(nb2msg(volume_percent) + mp.PERCENT_VOLUME)


def cmd_music_volume_down(interface):
    """减小音乐音量"""
    from .. import config

    # 停止当前所有语音播报，确保音量播报能立即听到
    sound.stop()
    
    # 调整音量并获取百分比值（与主音量处理方式保持一致，传递-1而不是-0.1）
    volume_percent = sound.adjust_music_volume(-1)
    config.save_audio_settings()

    # 播报音量（与主音量处理方式保持一致）
    voice.item(nb2msg(volume_percent) + mp.PERCENT_VOLUME)


def cmd_volume(interface, inc=1):
    """调整主音量"""
    modify_volume(int(inc))


def cmd_sfx_volume(interface, inc=1):
    """调整游戏音效音量"""
    modify_sfx_volume(int(inc))


# 语音历史管理
def cmd_history_previous(interface):
    """播放上一条语音"""
    voice.previous()


def cmd_history_stop(interface):
    """停止当前语音"""
    voice.say_next()


def cmd_history_next(interface):
    """播放下一条语音"""
    voice.say_next(history_only=True)


# 音效选择和调整
def cmd_select_sound(interface, inc=1):
    """选择音效进行测试"""
    h = sounds.cache
    if getattr(interface, '_sound', None) in h:
        interface._sound = h[(h.index(interface._sound) + int(inc)) % len(h)]
    elif h:
        interface._sound = h[0]
    else:
        interface._sound = None
    if interface._sound:
        voice.silent_flush()
        voice.item(
            [
                f"{interface._sound.name}, {interface._sound.get_volume():.1f}, {interface._sound.path}"
            ]
        )
        v = interface._sound.get_volume()
        if v < 0.5:
            interface._sound.set_volume(1)
        c = interface._sound.play(loops=10)
        if c:
            c.fadeout(1000)
        else:
            warning("couldn't play %s", interface._sound.path)
        if v < 0.5:
            time.sleep(1)
            interface._sound.set_volume(v)


def cmd_sound_volume(interface, inc=1):
    """调整选中音效的音量"""
    if getattr(interface, '_sound', None):
        interface._sound.set_volume(max(interface._sound.get_volume() + int(inc) / 10, 0))
        voice.silent_flush()
        voice.item(
            [f"{interface._sound.get_volume():.1f}", f"{interface._sound.name}",], 1, 1,
        )


# 时钟和节拍器功能
def cmd_toggle_talking_clock(interface):
    """开关时钟报时"""
    interface._bell_enabled = not interface._bell_enabled
    if interface._bell_enabled:
        voice.item(mp.BELL + mp.IS_NOW_ON)
        interface._previous_nb_minutes = int(interface.last_virtual_time / 60)
    else:
        voice.item(mp.BELL + mp.IS_NOW_OFF)


def cmd_toggle_tick(interface):
    """开关节拍器"""
    interface._must_play_tick = not interface._must_play_tick


# 服务器音乐恢复
def srv_restore_music(interface, music_id):
    """恢复背景音乐
    
    参数:
        music_id: 要恢复的音乐ID
    """
    sound.play_music(music_id)


def srv_resume_music(interface, unused_args=None):
    """从暂停的位置恢复音乐播放"""
    sound.unpause_music()


# 缩放模式下的移动功能（涉及音频反馈）
def cmd_move_forward_zoom(interface):
    """缩放模式下第一人称向前移动"""
    if not interface.immersion or not interface.zoom_mode or not interface.group:
        voice.item(mp.BEEP)
        return
    
    # 获取当前选中的单位
    unit_id = interface.group[0]
    if unit_id not in interface.dobjets:
        voice.item(mp.BEEP)
        return
        
    unit = interface.dobjets[unit_id]
    current_orientation = unit.o
    
    # 在缩放模式下，计算目标子区域
    target_zoom = _get_target_zoom_by_orientation(interface, current_orientation)
    if target_zoom:
        # 检查是否需要跨越大方格和路径连通性
        if _check_zoom_movement_collision(interface, target_zoom):
            # 发送移动到缩放目标的命令
            from .game_unit_control import send_order
            send_order(interface, "go", target_zoom.id, ["imperative"])
        # 如果被阻挡，_check_zoom_movement_collision已经播放了阻挡音效
    else:
        voice.item(mp.BEEP)


def cmd_move_backward_zoom(interface):
    """缩放模式下第一人称向后移动"""
    if not interface.immersion or not interface.zoom_mode or not interface.group:
        voice.item(mp.BEEP)
        return
    
    # 获取当前选中的单位
    unit_id = interface.group[0]
    if unit_id not in interface.dobjets:
        voice.item(mp.BEEP)
        return
        
    unit = interface.dobjets[unit_id]
    current_orientation = unit.o
    
    # 计算后退方向（与前进相反）
    backward_orientation = (current_orientation + 180) % 360
    target_zoom = _get_target_zoom_by_orientation(interface, backward_orientation)
    if target_zoom:
        # 检查是否需要跨越大方格和路径连通性
        if _check_zoom_movement_collision(interface, target_zoom):
            # 发送移动到缩放目标的命令
            from .game_unit_control import send_order
            send_order(interface, "go", target_zoom.id, ["imperative"])
        # 如果被阻挡，_check_zoom_movement_collision已经播放了阻挡音效
    else:
        voice.item(mp.BEEP)


def cmd_move_left_zoom(interface):
    """缩放模式下第一人称向左移动"""
    if not interface.immersion or not interface.zoom_mode or not interface.group:
        voice.item(mp.BEEP)
        return
    
    # 获取当前选中的单位
    unit_id = interface.group[0]
    if unit_id not in interface.dobjets:
        voice.item(mp.BEEP)
        return
        
    unit = interface.dobjets[unit_id]
    current_orientation = unit.o
    
    # 计算左移方向（向左90度）
    left_orientation = (current_orientation + 90) % 360
    target_zoom = _get_target_zoom_by_orientation(interface, left_orientation)
    if target_zoom:
        # 检查是否需要跨越大方格和路径连通性
        if _check_zoom_movement_collision(interface, target_zoom):
            # 发送移动到缩放目标的命令
            from .game_unit_control import send_order
            send_order(interface, "go", target_zoom.id, ["imperative"])
        # 如果被阻挡，_check_zoom_movement_collision已经播放了阻挡音效
    else:
        voice.item(mp.BEEP)


def cmd_move_right_zoom(interface):
    """缩放模式下第一人称向右移动"""
    if not interface.immersion or not interface.zoom_mode or not interface.group:
        voice.item(mp.BEEP)
        return
    
    # 获取当前选中的单位
    unit_id = interface.group[0]
    if unit_id not in interface.dobjets:
        voice.item(mp.BEEP)
        return
        
    unit = interface.dobjets[unit_id]
    current_orientation = unit.o
    
    # 计算右移方向（向右90度）
    right_orientation = (current_orientation - 90) % 360
    target_zoom = _get_target_zoom_by_orientation(interface, right_orientation)
    if target_zoom:
        # 检查是否需要跨越大方格和路径连通性
        if _check_zoom_movement_collision(interface, target_zoom):
            # 发送移动到缩放目标的命令
            from .game_unit_control import send_order
            send_order(interface, "go", target_zoom.id, ["imperative"])
        # 如果被阻挡，_check_zoom_movement_collision已经播放了阻挡音效
    else:
        voice.item(mp.BEEP)


def _check_zoom_movement_collision(interface, target_zoom):
    """检查缩放移动时的路径连通性和边界限制
    
    参数:
        target_zoom: 目标ZoomTarget对象
        
    返回:
        bool: True表示可以移动，False表示被阻挡
    """
    # 检查目标是否在当前大方格内
    if target_zoom.place == interface.place:
        # 在同一个大方格内移动，不需要路径检查
        return True
    
    # 需要跨越大方格，检查路径连通性
    target_square = target_zoom.place
    
    # 检查基本条件
    if target_square is None:
        voice.item(mp.BEEP)
        return False
    
    # 计算移动方向
    from .game_navigation import coords_in_map
    current_col, current_row = coords_in_map(interface, interface.place)
    target_col, target_row = coords_in_map(interface, target_square)
    
    dxc = target_col - current_col
    dyc = target_row - current_row
    
    # 检查是否超出地图边界
    if (target_col < 0 or target_col > interface.xcmax or 
        target_row < 0 or target_row > interface.ycmax):
        # 超出地图边界
        voice.item(mp.BEEP)
        return False
    
    # 使用新的路径检查逻辑
    from .game_navigation import _check_exit_connection
    has_exit = _check_exit_connection(interface, interface.place, target_zoom.place)
    
    if not has_exit:
        # 没有出口连接，使用浏览地图的阻挡声音
        from .game_navigation import _get_prefix_and_collision
        prefix, _ = _get_prefix_and_collision(interface, target_square, dxc, dyc)
        voice.item(prefix)
        return False
    else:
        # 路径畅通，可以移动
        return True


def _get_target_zoom_by_orientation(interface, orientation):
    """根据朝向角度计算缩放模式下的目标子区域"""
    if not interface.zoom_mode or not interface.zoom:
        return None
        
    # 标准化角度到0-360范围
    orientation = orientation % 360
    
    # 获取当前缩放精细度和相关参数
    precision = interface._zoom_precision
    half_precision = precision // 2
    
    # 获取当前zoom对象的子区域坐标
    current_sub_x = interface.zoom.sub_x
    current_sub_y = interface.zoom.sub_y
    
    # 计算移动步长（根据精细度动态调整）
    # 对于更高精度，使用更小的步长以提供更精细的控制
    if precision <= 3:
        step_size = 1
    elif precision <= 7:
        step_size = 1  # 保持单步移动，让玩家有更好的控制
    else:
        step_size = 1  # 即使是高精度也保持单步移动
    
    # 计算目标子区域的偏移量
    delta_sub_x = 0
    delta_sub_y = 0
    
    # 根据朝向确定移动方向（使用8方向更精确的判断）
    if 337.5 <= orientation or orientation < 22.5:  # 东 (0度方向)
        delta_sub_x = step_size
    elif 22.5 <= orientation < 67.5:  # 东北
        delta_sub_x = step_size
        delta_sub_y = step_size
    elif 67.5 <= orientation < 112.5:  # 北 (90度方向)
        delta_sub_y = step_size
    elif 112.5 <= orientation < 157.5:  # 西北
        delta_sub_x = -step_size
        delta_sub_y = step_size
    elif 157.5 <= orientation < 202.5:  # 西 (180度方向)
        delta_sub_x = -step_size
    elif 202.5 <= orientation < 247.5:  # 西南
        delta_sub_x = -step_size
        delta_sub_y = -step_size
    elif 247.5 <= orientation < 292.5:  # 南 (270度方向)
        delta_sub_y = -step_size
    elif 292.5 <= orientation < 337.5:  # 东南
        delta_sub_x = step_size
        delta_sub_y = -step_size
    
    # 计算目标子区域坐标
    target_sub_x = current_sub_x + delta_sub_x
    target_sub_y = current_sub_y + delta_sub_y
    
    # 计算边界值（支持偶数和奇数精细度）
    if precision % 2 == 0:
        # 偶数精细度的边界
        max_coord = half_precision - 1
        min_coord = -half_precision
    else:
        # 奇数精细度的边界
        max_coord = half_precision
        min_coord = -half_precision
    
    # 检查目标子区域是否在当前大方格内
    if min_coord <= target_sub_x <= max_coord and min_coord <= target_sub_y <= max_coord:
        # 目标在当前大方格内，计算子区域的实际坐标
        sq = interface.place
        xstep = (sq.xmax - sq.xmin) / precision
        ystep = (sq.ymax - sq.ymin) / precision
        
        # 计算精确的子区域中心坐标
        center_offset_x = (target_sub_x + 0.5) * xstep
        center_offset_y = (target_sub_y + 0.5) * ystep
        target_x = sq.xmin + (half_precision + 0.5) * xstep + center_offset_x - xstep/2
        target_y = sq.ymin + (half_precision + 0.5) * ystep + center_offset_y - ystep/2
        
        # 创建ZoomTarget对象
        from ..worldroom import ZoomTarget, format_zoom_target_id

        zoom_id = format_zoom_target_id(sq.id, target_x, target_y, precision)
        return ZoomTarget(sq, target_x, target_y, id=zoom_id, precision=precision)
    else:
        # 目标超出当前大方格，需要移动到相邻的大方格
        from .game_navigation import _compute_move
        # 计算需要移动到哪个相邻方格
        dxc = 0
        dyc = 0
        new_target_sub_x = target_sub_x
        new_target_sub_y = target_sub_y
        
        if target_sub_x > max_coord:
            dxc = 1
            new_target_sub_x = min_coord + (target_sub_x - max_coord - 1)
        elif target_sub_x < min_coord:
            dxc = -1
            new_target_sub_x = max_coord - (min_coord - target_sub_x - 1)
            
        if target_sub_y > max_coord:
            dyc = 1
            new_target_sub_y = min_coord + (target_sub_y - max_coord - 1)
        elif target_sub_y < min_coord:
            dyc = -1
            new_target_sub_y = max_coord - (min_coord - target_sub_y - 1)
        
        # 计算目标大方格
        target_square = _compute_move(interface, dxc, dyc)
        if target_square:
            # 计算目标大方格中对应子区域的坐标
            xstep = (target_square.xmax - target_square.xmin) / precision
            ystep = (target_square.ymax - target_square.ymin) / precision
            
            # 计算精确的子区域中心坐标
            center_offset_x = (new_target_sub_x + 0.5) * xstep
            center_offset_y = (new_target_sub_y + 0.5) * ystep
            target_x = target_square.xmin + (half_precision + 0.5) * xstep + center_offset_x - xstep/2
            target_y = target_square.ymin + (half_precision + 0.5) * ystep + center_offset_y - ystep/2
            
            # 创建ZoomTarget对象
            from ..worldroom import ZoomTarget, format_zoom_target_id

            zoom_id = format_zoom_target_id(
                target_square.id, target_x, target_y, precision
            )
            return ZoomTarget(
                target_square, target_x, target_y, id=zoom_id, precision=precision
            )
        else:
            return None


# 缩放精度控制
def cmd_change_zoom_precision(interface, *args):
    """自定义RPG缩放模式的精细度
    如果没有参数，则打开输入框让用户自定义
    如果有参数，则按照原来的逻辑调整精细度
    """
    # 如果没有参数，启动非阻塞输入模式
    if not args:
        # 启动输入模式，但不暂停游戏
        from .game_input_handler import _start_zoom_input_mode
        _start_zoom_input_mode(interface)
    else:
        # 原有的级别调整逻辑
        direction = int(args[0]) if args else 1
        precision_levels = [3, 5, 7, 9, 11, 15]  # 可选的精细度级别，从原始3x3开始
        
        try:
            current_index = precision_levels.index(interface._zoom_precision)
        except ValueError:
            current_index = 0  # 默认3x3
            
        new_index = current_index + direction
        if new_index < 0:
            new_index = 0
        elif new_index >= len(precision_levels):
            new_index = len(precision_levels) - 1
            
        interface._zoom_precision = precision_levels[new_index]
        
        # 语音反馈当前精细度
        voice.item([f"{interface._zoom_precision}x{interface._zoom_precision}"])


def cmd_get_zoom_precision(interface):
    """获取当前RPG缩放模式的精细度"""
    voice.item([f"{interface._zoom_precision}x{interface._zoom_precision}"])


# 导出的函数供其他模块使用
__all__ = [
    'cmd_say', 'cmd_say_players', 'cmd_say_time', 'cmd_toggle_music',
    'cmd_music_volume_up', 'cmd_music_volume_down', 'cmd_volume', 'cmd_sfx_volume',
    'cmd_history_previous', 'cmd_history_stop', 'cmd_history_next',
    'cmd_select_sound', 'cmd_sound_volume', 'cmd_toggle_talking_clock',
    'cmd_toggle_tick', 'srv_restore_music', 'srv_resume_music',
    'cmd_move_forward_zoom', 'cmd_move_backward_zoom', 'cmd_move_left_zoom',
    'cmd_move_right_zoom', 'cmd_change_zoom_precision', 'cmd_get_zoom_precision',
    '_check_zoom_movement_collision', '_get_target_zoom_by_orientation'
]