import time

import pygame

from .. import parameters
from ..animation import noise
from ..clientgameentity import SquareView
from ..clientmedia import toggle_fullscreen, voice
from ..definitions import style
from .. import msgparts as mp
from ..lib.msgs import localize_voice_msg
from ..lib import chronometer as chrono
from ..lib.log import exception, debug
from ..lib.screen import (
    get_screen,
    screen_render,
    screen_render_subtitle,
)
from ..clientmedia import get_fullscreen
from ..version import IS_DEV_VERSION


def display(interface):
    """主显示函数"""
    if get_screen() is None:
        return  # this might allow some machines to work without any display
    chrono.start("display")
    get_screen().fill((0, 0, 0))
    if interface.display_is_active:
        interface.grid_view.display()
        if (
            interface.mouse_select_origin
            and interface.mouse_select_origin != pygame.mouse.get_pos()
        ):
            x, y = interface.mouse_select_origin
            x2, y2 = pygame.mouse.get_pos()
            pygame.draw.rect(
                get_screen(),
                (255, 255, 255),
                (min(x, x2), min(y, y2), abs(x - x2), abs(y - y2)),
                1,
            )
    elif not IS_DEV_VERSION:
        screen_render(
            "[Ctrl + F2] display",
            pygame.display.get_surface().get_rect().center,
            center=True,
        )
    if getattr(interface, '_must_play_tick', False) or IS_DEV_VERSION:
        display_metrics(interface)
    if getattr(interface, '_must_display_target_info', False) and get_fullscreen():
        _display_target_info(interface)
    screen_render_subtitle()
    try:
        from ..lib import pygame_ui

        if pygame_ui.narrative_is_active():
            pygame_ui.draw_narrative_onto(get_screen())
    except Exception:
        pass
    pygame.display.flip()
    chrono.stop("display")


def display_metrics(interface):
    """显示性能指标"""
    warn = (255, 0, 0)
    normal = (0, 200, 0)
    if not get_fullscreen():
        screen_render(f"x{interface._get_relative_speed():.1f}", (0, 0))
        screen_render(chrono.text("update", label="w"), (-1, 0), right=True)
        screen_render(chrono.text("display", label="d"), (-1, 15), right=True)
        return
    screen_render(
        "total delay: %sms" % chrono.ms(time.time() - interface.next_update),
        (0, 30),
        color=warn if time.time() > interface.next_update else normal,
    )
    if hasattr(interface.server, "turn"):
        screen_render(
            "com turn(sim subturn): {}({}/{})".format(
                interface.server.turn, interface.server.sub_turn + 1, interface.server.fpct
            ),
            (0, 45),
        )
        screen_render(
            "com delay: %sms" % chrono.ms(interface.server.delay),
            (0, 60),
            color=warn if interface.server.delay > 0 else normal,
        )
    screen_render(chrono.text("ping"), (-1, 0), right=True)
    screen_render(chrono.text("update", label="world update"), (-1, 30), right=True)
    screen_render(chrono.text("animate"), (-1, 45), right=True)
    screen_render(chrono.text("display"), (-1, 60), right=True)
    screen_render(f"turn: {interface.world.turn}", (0, 0))
    s = "speed: {:.0f} sim turns per second (normal x{:.1f})".format(
        interface._get_tps(), interface._get_relative_speed()
    )
    screen_render(
        s,
        (0, 15),
        color=warn if interface._get_relative_speed() < interface.speed * 0.9 else normal,
    )


def _display_target_info(interface):
    """显示目标信息（调试用）"""
    dy = 0
    if interface.target is not None:
        screen_render("TARGET INFO", (-1, 100 + dy), right=True)
        dy += 15
        try:
            screen_render(
                repr(interface.target.model),
                (-1, 100 + dy),
                color=(255, 255, 255),
                right=True,
            )
            dy += 15
            d = interface.target.model.__dict__
            for k in sorted(d):
                screen_render(k + ": " + repr(d[k]), (-1, 100 + dy), right=True)
                dy += 15
        except:
            exception("error inspecting target: %s", interface.target)
    if interface.place is not None:
        dy += 15
        screen_render("PLACE INFO", (-1, 100 + dy), right=True)
        dy += 15
        try:
            screen_render(
                repr(interface.place), (-1, 100 + dy), color=(255, 255, 255), right=True
            )
            dy += 15
            d = interface.place.__dict__
            for k in sorted(d):
                screen_render(k + ": " + repr(d[k]), (-1, 100 + dy), right=True)
                dy += 15
        except:
            exception("error inspecting place: %s", interface.place)
    dy = 0
    screen_render("PLAYER INFO", (-1, 100 + dy))
    dy += 15
    d = interface.player.__dict__
    for k in sorted(d):
        try:
            screen_render(k + ": " + repr(d[k]), (-1, 100 + dy))
            dy += 15
        except:
            exception("error inspecting player: %s", interface.player)


def _animation_nearby_places(interface):
    """Places whose EntityViews may pass ``is_local`` (current + optional neighbors)."""
    place = getattr(interface, "place", None)
    if place is None:
        return None
    nearby = {place}
    if parameters.d.get("render_nearby_objects", False):
        for n in getattr(place, "neighbors", ()) or ():
            nearby.add(n)
    return nearby


def _entity_view_audio_place(o):
    """Match EntityView._client_audio_place without going through animate()."""
    try:
        if getattr(o, "is_inside", False):
            container = getattr(getattr(o, "place", None), "container", None)
            if container is not None:
                return getattr(container, "place", None)
        return getattr(o, "place", None)
    except Exception:
        return None


def _iter_animation_candidates(interface):
    """Prefer in-range objects so distant memory views do not pay animate() setup."""
    nearby = _animation_nearby_places(interface)
    objs = list(interface.dobjets.values())
    if nearby is None:
        return objs
    local = []
    for o in objs:
        if _entity_view_audio_place(o) in nearby:
            local.append(o)
    # Fallback: if filter emptied oddly, keep full list.
    return local if local else objs


def _finish_animation_wave(interface):
    interface.previous_animation = time.time()
    interface._animate_resume = None
    chrono.stop("animate")


def _animation_post_steps():
    """Deferred end-of-wave work (each step may run on its own frame)."""

    def _terrain(iface):
        _animate_terrain(iface)

    def _build_field(iface):
        from .build_field_voice import animate_build_field_noises

        animate_build_field_noises(iface)

    def _battle(iface):
        _check_battle_status(iface)

    def _rpg(iface):
        _check_rpg_unit_place_change(iface)

    return (
        ("terrain", _terrain),
        ("build_field", _build_field),
        ("battle", _battle),
        ("rpg", _rpg),
    )


def _animate_objects(interface):
    """动画对象。

    Heavy early-game waves (many local units + footsteps/noise) used to block the
    client loop for 0.5–1s+, delaying the next world ask and dropping F-key speed.
    Work is now budgeted across frames (~8ms) so voila/ask can keep pace; sound
    content is unchanged, only when each unit is refreshed within the wave.
    """
    resume = getattr(interface, "_animate_resume", None)
    delay = parameters.d.get("animation_delay", 0.1)
    # Default 8ms keeps main-loop ask cadence near the 300ms tick.
    budget_s = float(parameters.d.get("animation_budget_ms", 8)) / 1000.0
    if budget_s < 0.002:
        budget_s = 0.002

    if resume is None:
        if time.time() < getattr(interface, "previous_animation", 0) + delay:
            return
        chrono.start("animate")
        # setup_obs → setup_cand → objs → post (one frame each at least)
        resume = {"phase": "setup_obs"}
        interface._animate_resume = resume

    deadline = time.perf_counter() + budget_s

    if resume.get("phase") == "setup_obs":
        try:
            from .game_navigation import set_obs_pos

            # Stereo refresh is handled on a throttle / mixer events; skip the
            # full psounds.update() here so animation waves stay cheap.
            set_obs_pos(interface, update_sounds=False)
        except Exception:
            exception("couldn't set user interface position")
        resume = {"phase": "setup_cand"}
        interface._animate_resume = resume
        return

    if resume.get("phase") == "setup_cand":
        try:
            from ..clientgameentity.formation_sound_queue import (
                flush_formation_sound_queue,
            )

            flush_formation_sound_queue(interface)
        except Exception:
            exception("couldn't flush formation sound queue")
        objs = _iter_animation_candidates(interface)
        resume = {"phase": "objs", "objs": objs, "i": 0}
        interface._animate_resume = resume
        return

    if resume.get("phase") == "objs":
        objs = resume["objs"]
        i = resume["i"]
        n = len(objs)
        while i < n:
            if time.perf_counter() >= deadline:
                resume["i"] = i
                interface._animate_resume = resume
                return
            o = objs[i]
            i += 1
            try:
                o.animate()
            except Exception:
                exception("couldn't animate object")
        # Never fall through into post on the same frame.
        resume = {"phase": "post", "step": 0}
        interface._animate_resume = resume
        return

    if resume.get("phase") == "post":
        steps = _animation_post_steps()
        step = int(resume.get("step", 0))
        while step < len(steps):
            name, fn = steps[step]
            try:
                fn(interface)
            except Exception:
                exception("couldn't animate post-step %s" % name)
            step += 1
            # Terrain/battle can spike; always yield after one post-step.
            if step < len(steps):
                resume["step"] = step
                interface._animate_resume = resume
                return
        _finish_animation_wave(interface)

def _animate_terrain(interface):
    """动画地形"""
    if interface.place:
        squares = [interface.place]
        if parameters.d.get("render_nearby_land", False):
            squares += interface.place.neighbors
        squares = [
            sq
            for sq in squares
            if sq in interface.scouted_squares or sq in interface.scouted_before_squares
        ]
        # 获取地形噪音列表
        terrain_noises = getattr(interface, '_terrain_noises', [])
        for n in terrain_noises[:]:
            if n.obj.model not in squares:
                n.stop()
                terrain_noises.remove(n)
            else:
                n.update()
        for sq in squares:
            if sq not in [n.obj.model for n in terrain_noises]:
                t = sq.type_name
                if t:
                    st = style.get(t, "noise")
                    n = noise(SquareView(interface, sq), st)
                    if n:
                        terrain_noises.append(n)
        # 设置回接口
        interface._terrain_noises = terrain_noises


def _check_battle_status(interface, force_check=False):
    """检查所有区域是否还有战斗，如果没有则停止战斗音乐"""
    # 当前时间
    current_time = time.time()
    
    # 如果距离上次检查时间不足间隔时间，且不是强制检查，则跳过
    if not force_check and current_time - interface._last_battle_status_check < interface._battle_status_check_interval:
        return
        
    # 更新最后检查时间
    interface._last_battle_status_check = current_time
    
    # 获取音乐状态
    from ..lib import sound
    
    status = sound.get_music_status()
    
    # 如果当前不在战斗音乐状态，不需要检查
    if not status["in_battle"]:
        return
        
    # 检查所有地区是否有敌人
    # 中立 creep（neutral）不算"还在战斗"——他们是被动的，常驻在地图上
    # 也不会自己来打你，所以在判定"是否该停止战斗音乐"时应忽略。
    has_enemies = False

    # 遍历所有可见区域
    for place in interface.scouted_squares:
        # 检查该区域中的所有对象
        for obj in place.objects:
            # 检查是否是敌方单位（且非中立 creep）
            if (hasattr(obj, 'player') and obj.player and
                interface.player.player_is_an_enemy(obj.player) and
                not getattr(obj.player, 'neutral', False)):
                has_enemies = True
                break
        
        if has_enemies:
            break
    
    # 如果视野中没有敌人，停止战斗音乐
    if not has_enemies:
        try:
            # 确保玩家阵营信息正确设置
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
                debug(f"战斗结束时设置玩家阵营: {player_faction}")
                
            # 停止战斗音乐
            sound.stop_battle_music()
            debug("战斗结束，停止战斗音乐")
        except Exception as e:
            exception(f"停止战斗音乐时出错: {e}")


def _check_rpg_unit_place_change(interface):
    """检查RPG模式下单位是否进入新方格，如果是则播报主方格名称加子区域信息"""
    # 只在RPG缩放模式下进行检查
    if not (interface.immersion and interface.zoom_mode and interface.group):
        interface._rpg_unit_previous_place = None
        return
        
    # 获取当前选中的单位
    unit_id = interface.group[0]
    if unit_id not in interface.dobjets:
        interface._rpg_unit_previous_place = None
        return
        
    unit = interface.dobjets[unit_id]
    current_place = unit.place
    
    # 检查是否发生了方格变化
    if (interface._rpg_unit_previous_place is not None and 
        current_place != interface._rpg_unit_previous_place):
        # 单位进入了新方格，需要更新缩放焦点并播报区域信息
        prev_place = interface._rpg_unit_previous_place
        province_prefix = []
        try:
            world = interface.world
            key_new = f"{current_place.col},{current_place.row}"
            key_prev = f"{prev_place.col},{prev_place.row}" if prev_place else None
            province_name = getattr(world, 'square_provinces', {}).get(key_new)
            prev_province = getattr(world, 'square_provinces', {}).get(key_prev) if key_prev else None
            if province_name and province_name != prev_province:
                province_prefix = [province_name] + mp.COMMA
        except Exception:
            pass

        # 更新zoom对象的主方格记录
        if interface.zoom:
            interface.zoom.current_main_square = current_place
            interface.zoom.move_to(unit)  # 让zoom对象自动定位到单位所在的子区域
            
            # 播报（跨主区域边界则加主区域名前缀）+ 主方格名称 + 子区域信息
            interface.zoom.say(prefix=province_prefix + current_place.title + [" "])
        else:
            # 如果zoom对象不存在：播报（跨主区域边界则加主区域名前缀）+ 主方格名称
            voice.item(localize_voice_msg(province_prefix + current_place.title))
        
    # 更新记录的位置
    interface._rpg_unit_previous_place = current_place


def cmd_fullscreen(interface):
    """切换全屏模式"""
    toggle_fullscreen()


# 导出的函数供其他模块使用
__all__ = [
    'display', 'display_metrics', '_display_target_info', '_animate_objects',
    '_animate_terrain', '_check_battle_status', '_check_rpg_unit_place_change',
    'cmd_fullscreen'
]