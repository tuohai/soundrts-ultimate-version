"""音效和声音相关模块 - 步行音效、环境音效、音效播放等"""

import random
import time

import pygame

from .. import parameters
from ..animation import noise
from ..clientmedia import sounds
from ..definitions import style
from ..lib.sound import psounds, distance
from .base import FOOTSTEP_LIMIT


class EntityViewAudio:
    """EntityView的音效相关方法"""
    
    # 音效相关属性
    _noise = None
    _buff_noises = None
    previous_hp = None

    def _terrain_footstep(self):
        t = self.place.type_name
        if t:
            g = style.get(t, "ground")
            if g and style.has(self.type_name, "move_on_%s" % g[0]):
                return style.get(self.type_name, "move_on_%s" % g[0])

    def footstepnoise(self):
        # assert: "only immobile objects must be taken into account"
        result = style.get(self.type_name, "move")
        if self.airground_type == "ground" and self._terrain_footstep():
            return self._terrain_footstep()
        elif (
            self.airground_type == "ground" and len(self.place.objects) < 30
        ):  # save CPU
            d_min = 9999999
            for m in self.place.objects:
                if getattr(m, "speed", 0):
                    continue
                g = style.get(m.type_name, "ground")
                if g and style.has(self.type_name, "move_on_%s" % g[0]):
                    try:
                        k = float(g[1])
                    except IndexError:
                        k = 1.0
                    try:
                        o = self.interface.dobjets[m.id]
                    except KeyError:  # probably caused by the world client updates
                        continue
                    try:
                        d = distance(o.x, o.y, self.x, self.y) / k
                    except ZeroDivisionError:
                        continue
                    if d < d_min:
                        result = style.get(self.type_name, "move_on_%s" % g[0])
                        d_min = d
        return result

    def footstep(self):
        if self.is_moving and not self.is_memory:
            # 脚步声按真实时间（time.time + real_speed），不用游戏虚拟时间
            now = time.time()
            interval = self.footstep_interval / self.interface.real_speed
            if self.next_step is None:
                self.step_side = 1
                self.next_step = (
                    now + random.random() * interval
                )  # start at different moments
            elif now >= self.next_step:
                if self.interface.immersion and (self.x, self.y) == (
                    self.interface.x,
                    self.interface.y,
                ):
                    v = 1 / 2.0
                else:
                    v = 1
                try:
                    self.launch_event(
                        self.footstepnoise()[self.step_side],
                        v,
                        priority=-10,
                        limit=FOOTSTEP_LIMIT,
                    )
                except IndexError:
                    pass
                self.next_step = now + interval
                self.step_side = 1 - self.step_side
        else:
            self.next_step = None

    def get_style(self, attr):
        st = style.get(self.type_name, attr)
        if st and st[0] == "if_me":
            if self.player in self.interface.player.allied:
                return st[1]
            else:
                return st[2]
        return st

    def _get_noise_style(self):
        # 缓存常用阈值，减少属性访问与除法开销
        activity = getattr(self, 'activity', None)
        if activity:
            st = self.get_style(f"noise_when_{activity}")
            if st:
                return st
        hp = getattr(self, 'hp', None)
        if hp is not None:
            hp_max = getattr(self, 'hp_max', 0) or 0
            if hp_max:
                third = hp_max / 3
                two_thirds = (hp_max * 2) / 3
                if hp < third:
                    st = self.get_style("noise_if_very_damaged")
                    if st:
                        return st
                if hp < two_thirds:
                    st = self.get_style("noise_if_damaged")
                    if st:
                        return st
        return self.get_style("noise")

    _noise = None

    def _set_noise(self, st):
        # 检查noise函数是否可用，防止序列化后函数变成None
        from ..animation import noise as noise_func
        
        if self._noise:
            if st is self._noise.style:
                self._noise.update()
            else:
                self._noise.stop()
                try:
                    self._noise = noise_func(self, st) if noise_func else None
                except (TypeError, AttributeError):
                    self._noise = None
        else:
            try:
                self._noise = noise_func(self, st) if noise_func else None
            except (TypeError, AttributeError):
                self._noise = None

    def _active_buff_types(self):
        try:
            buffs = getattr(self.model, "_buffs", None) or ()
        except AttributeError:
            return []
        result = []
        for buff in buffs:
            buff_type = getattr(buff, "type_name", None)
            if buff_type is None and isinstance(buff, tuple) and buff:
                buff_type = buff[0]
            if buff_type and buff_type not in result:
                result.append(buff_type)
        return result

    def _update_buff_noises(self):
        from ..animation import noise as noise_func

        if self._buff_noises is None:
            self._buff_noises = {}
        active = set()
        for buff_type in self._active_buff_types():
            st = style.get(buff_type, "noise", warn_if_not_found=False)
            if not st:
                continue
            active.add(buff_type)
            current = self._buff_noises.get(buff_type)
            if current and st is current.style:
                current.update()
                continue
            if current:
                current.stop()
            try:
                current = noise_func(self, st) if noise_func else None
            except (TypeError, AttributeError):
                current = None
            if current:
                current.update()
                self._buff_noises[buff_type] = current
            else:
                self._buff_noises.pop(buff_type, None)
        for buff_type in list(self._buff_noises):
            if buff_type not in active:
                self._buff_noises[buff_type].stop()
                del self._buff_noises[buff_type]

    def update_noise(self):
        st = self._get_noise_style()
        self._set_noise(st)
        self._update_buff_noises()

    def launch_event_style(self, attr, alert=False, priority=0):
        st = self.get_style(attr)
        if not st:
            return
        s = random.choice(st)
        if alert and not self.is_local:
            self.launch_alert(s)
        else:
            self.launch_event(s, priority=priority)

    def animate(self):
        if self.is_local:
            self.footstep()
            self.update_noise()
            self.render_hp()

    previous_hp = None

    def _hp_noise(self, hp):
        return int(hp * 10 / self.hp_max)

    def render_hp_evolution(self):
        if self.previous_hp is not None:
            if self.hp < self.previous_hp or self._hp_noise(  # always noise if less HP
                self.hp
            ) != self._hp_noise(self.previous_hp):
                self.launch_event_style("proportion_%s" % self._hp_noise(self.hp))
            if self.hp > self.previous_hp and self.is_healable:
                self.launch_event_style("healed")

    def render_hp(self):
        if hasattr(self, "hp"):
            if self.hp < 0:
                return  # TODO: remove this line (isolate the UI or use a deep copy of perception)
            if self.hp != self.previous_hp:
                self.render_hp_evolution()
                self.previous_hp = self.hp

    def launch_event(self, sound, volume=1, priority=0, limit=0, ambient=False):
        if self.place is self.interface.place:
            pass
        elif self.place in getattr(self.interface.place, "neighbors", []):
            priority -= 1
        else:
            return
        if self.is_memory:
            volume *= parameters.d.get("fog_of_war_factor", 0.5)
        return psounds.play(
            sounds.get_sound(sound), volume, self.x, self.y, priority, limit, ambient
        )

    def launch_alert(self, sound):
        if self.is_inside:
            place = self.place.container.place
        else:
            place = self.place
        self.interface.launch_alert(place, sound)

    @property
    def is_local(self):
        return self.place is self.interface.place or parameters.d.get("render_nearby_objects", False) and self.interface.place and self.place in self.interface.place.neighbors

    def on_use_complete(self, skill):
        st = style.get(skill, "alert")
        if not st:
            return
        s = random.choice(st)
        self.launch_alert(s)