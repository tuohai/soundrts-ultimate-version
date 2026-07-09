"""音效和声音相关模块 - 步行音效、环境音效、音效播放等"""

import random
import time

import pygame

from .. import parameters
from ..animation import noise
from ..clientmedia import sounds
from ..definitions import style
from ..open_container import inside_unit_visible_from_place
from ..lib.sound import psounds, distance
from .base import FOOTSTEP_LIMIT


class EntityViewAudio:
    """EntityView的音效相关方法"""
    
    # 音效相关属性
    _noise = None
    _buff_noises = None
    previous_hp = None

    def _iter_building_land_sources(self, place):
        for obj in getattr(place, "objects", ()) or ():
            if getattr(obj, "type_name", None) == "buildingsite":
                land = getattr(obj, "building_land", None)
                if land is not None:
                    yield land
            if getattr(obj, "is_a_building_land", False) and not getattr(
                obj, "is_an_exit", False
            ):
                yield obj

    def _building_land_ground_keys(self, place, voice_name):
        from ..lib.square_terrain_rules import square_terrain_entries_for_type

        keys = []
        for obj in self._iter_building_land_sources(place):
            tn = getattr(obj, "type_name", None)
            if not tn:
                continue
            for ent in square_terrain_entries_for_type(tn):
                if ent.get("name") != voice_name:
                    continue
                ground = style.get(tn, "ground", warn_if_not_found=False)
                if ground and ground[0] and ground[0] not in keys:
                    keys.append(ground[0])
        return keys

    def _terrain_voice_to_sound_keys(self, voice_name, place=None):
        keys = []
        if not voice_name:
            return keys
        keys.append(voice_name)
        ground = style.get(voice_name, "ground", warn_if_not_found=False)
        if ground and ground[0] and ground[0] not in keys:
            keys.append(ground[0])
        elif place is not None:
            for gk in self._building_land_ground_keys(place, voice_name):
                if gk not in keys:
                    keys.append(gk)
        return keys

    def _overlay_terrain_voices(self, place):
        """覆盖层地形（桥面、脚手架、草皮/建筑用地、森林等）优先于底图。"""
        if place is None:
            return []
        from ..lib.square_terrain_rules import resolve_square_layers

        try:
            layers = resolve_square_layers(place, self.x, self.y)
        except AttributeError:
            return []
        return list(layers.get("overlay_voices") or ())

    def _place_terrain_voice(self):
        place = self.place
        if place is None:
            return None
        overlays = self._overlay_terrain_voices(place)
        if overlays:
            return overlays[0]
        if hasattr(place, "type_name_at"):
            name = place.type_name_at(self.x, self.y)
            if name:
                return name
        return getattr(place, "type_name", None)

    def _terrain_sound_keys(self):
        """Return terrain keys for falling_on_* / move_on_* (name, then ground type)."""
        place = self._client_audio_place()
        if place is None:
            return []
        keys = []
        for voice in self._overlay_terrain_voices(place):
            for key in self._terrain_voice_to_sound_keys(voice, place):
                if key not in keys:
                    keys.append(key)
        if keys:
            return keys
        terrain_name = None
        if hasattr(place, "type_name_at"):
            terrain_name = place.type_name_at(self.x, self.y)
        if not terrain_name:
            terrain_name = getattr(place, "type_name", None)
        return self._terrain_voice_to_sound_keys(terrain_name, place)

    def _get_terrain_style(self, prefix):
        for key in self._terrain_sound_keys():
            attr = prefix + key
            if style.has(self.type_name, attr):
                return style.get(self.type_name, attr)
        return None

    def _get_falling_sound(self):
        st = self._get_terrain_style("falling_on_")
        return st if st else self.get_style("falling")

    def _terrain_footstep(self):
        return self._get_terrain_style("move_on_")

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
                keys = [m.type_name]
                g = style.get(m.type_name, "ground", warn_if_not_found=False)
                if g and g[0] and g[0] not in keys:
                    keys.append(g[0])
                move_on = None
                for key in keys:
                    if style.has(self.type_name, "move_on_%s" % key):
                        move_on = style.get(self.type_name, "move_on_%s" % key)
                        break
                if not move_on:
                    continue
                try:
                    k = float(g[1]) if g else 1.0
                except (IndexError, TypeError):
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
                    result = move_on
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
            if activity == "building" and self.type_name == "buildingsite":
                building_type = getattr(getattr(self, "model", None), "type", None)
                bt_name = getattr(building_type, "type_name", None)
                if bt_name:
                    st = style.get(bt_name, "noise_when_building", warn_if_not_found=False)
                    if st:
                        return st
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

    def _client_audio_place(self):
        if getattr(self, "is_inside", False):
            container = getattr(self.place, "container", None)
            if container is not None:
                return container.place
        return self.place

    def launch_event(self, sound, volume=1, priority=0, limit=0, ambient=False, x=None, y=None):
        audio_place = self._client_audio_place()
        if audio_place is self.interface.place:
            pass
        elif audio_place in getattr(self.interface.place, "neighbors", []):
            priority -= 1
        elif not inside_unit_visible_from_place(self, self.interface.place):
            return
        if self.is_memory:
            volume *= parameters.d.get("fog_of_war_factor", 0.5)
        sx = self.x if x is None else x
        sy = self.y if y is None else y
        return psounds.play(
            sounds.get_sound(sound), volume, sx, sy, priority, limit, ambient
        )

    def launch_staggered_shouts(
        self,
        sound_ids,
        headcount,
        kind="shout_unit",
        base_volume=1.0,
        priority=0,
        burst_cap=None,
        spread=None,
    ):
        """按规模错开播放多条喊杀音效。"""
        from .battle_shout_audio import (
            _DEFAULT_SPREAD,
            burst_stagger_delays,
            normalize_sound_pool,
            scaled_shout_burst,
            shout_combat_priority,
            shout_combat_volume,
        )
        from .formation_sound_queue import queue_formation_sound

        pool = normalize_sound_pool(sound_ids)
        if not pool:
            return
        burst = scaled_shout_burst(headcount, kind)
        if burst_cap is not None:
            burst = min(burst, burst_cap)
        if burst <= 0:
            return
        sfx_priority = priority or shout_combat_priority(headcount, kind)
        spread = _DEFAULT_SPREAD if spread is None else spread
        now = time.time()
        entity_id = getattr(self, "id", None)
        for delay in burst_stagger_delays(burst, kind, headcount):
            sound = random.choice(pool)
            jx = self.x + random.uniform(-spread, spread)
            jy = self.y + random.uniform(-spread, spread)
            vol = shout_combat_volume(base_volume, headcount, kind)
            if entity_id is not None:
                queue_formation_sound(
                    self.interface,
                    entity_id,
                    now + delay,
                    sound,
                    vol,
                    sfx_priority,
                    0,
                    jx,
                    jy,
                )
            else:
                self.launch_event(
                    sound, vol, priority=sfx_priority, x=jx, y=jy
                )

    def launch_alert(self, sound):
        if self.is_inside:
            place = self.place.container.place
        else:
            place = self.place
        self.interface.launch_alert(place, sound)

    @property
    def is_local(self):
        audio_place = self._client_audio_place()
        interface_place = self.interface.place
        return audio_place is interface_place or (
            parameters.d.get("render_nearby_objects", False)
            and interface_place
            and audio_place in interface_place.neighbors
        )

    def on_use_complete(self, skill):
        st = style.get(skill, "alert")
        if not st:
            return
        s = random.choice(st)
        self.launch_alert(s)