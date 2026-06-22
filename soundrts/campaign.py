import configparser
import os
import re
from pathlib import Path
import hashlib
import pygame

from . import msgparts as mp
from .clientmedia import play_sequence, voice
from .clientmenu import Menu
from .game import MissionGame
from .lib.package import resource_layer
from .lib.msgs import nb2msg
from .lib.resource import res
from .mapfile import Map
from .paths import CAMPAIGNS_CONFIG_PATH
from .lib import sound


def parse_chapter_spec(text: str) -> frozenset[int]:
    """Parse ``1 2 3``, ``1-29``, or ``1,2,3`` chapter lists from campaign.txt."""
    numbers: set[int] = set()
    for token in re.split(r"[\s,]+", text.strip()):
        if not token:
            continue
        if "-" in token:
            start_s, end_s = token.split("-", 1)
            start, end = int(start_s), int(end_s)
            if start > end:
                start, end = end, start
            numbers.update(range(start, end + 1))
        else:
            numbers.add(int(token))
    return frozenset(numbers)


class Chapter:
    campaign: "Campaign"
    number: int

    def _next(self):
        return self.campaign.next(self)


class MissionChapter(Chapter):
    def __init__(self, campaign, number, map_):
        self.campaign = campaign
        self.number = number
        self.map = map_

    @property
    def title(self):
        return self.map.title[1:]

    def _run_victory_menu(self):
        # 帝国时代决定版风格：通关后明确播报"下一关已解锁"。
        voice.important(mp.NEXT_MISSION_UNLOCKED)
        menu = Menu(menu_type="submenu")
        menu.append(mp.CONTINUE, self._next())
        menu.append(mp.QUIT, None)
        menu.run()

    def _run_defeat_menu(self):
        # 决定版风格：失败菜单提供"重新挑战本关"。
        menu = Menu(menu_type="submenu")
        menu.append(mp.RETRY_THIS_MISSION, self)
        menu.append(mp.QUIT, None)
        menu.run()

    def run(self):
        voice.important(self.title)
        game = MissionGame(self)
        # 共用 N.txt 的合作战役地图在磁盘上含合作向强化；单人加载时还原为基线布局。
        from .campaign_map_mode import map_for_solo_campaign

        game.map = map_for_solo_campaign(self.map)
        # 帝国时代决定版风格难度：把本战役选定的敌人强度百分比传给单人战役会话，
        # 由 game.run 写入世界，确定性地缩放敌方单位 hp/伤害（回放也会记录）。
        try:
            hp, dmg = self.campaign.difficulty_factors()
            game.enemy_hp_factor = hp
            game.enemy_damage_factor = dmg
            game.coop_difficulty = self.campaign.get_difficulty()
        except Exception:
            pass
        game.run()
        self.run_next_step(game)

    def run_next_step(self, game):
        if game.has_victory():
            self.campaign.unlock_next(self)
            if self._next():
                self._run_victory_menu()
        else:
            self._run_defeat_menu()


class RandomMapMissionChapter(MissionChapter):
    """Campaign mission whose terrain is generated on each play."""

    def __init__(self, campaign, number, config, title, overlay):
        self.campaign = campaign
        self.number = number
        self._config = config
        self._title = title
        self._overlay = overlay
        self.map = None
        self.last_seed: int | None = None

    @property
    def title(self):
        return self._title

    def build_map(self):
        from .randommap import make_campaign_map

        self.map, self.last_seed = make_campaign_map(
            self._config,
            self._overlay,
            self.campaign.name,
            self.number,
        )
        return self.map

    def run(self):
        self.build_map()
        super().run()


def ensure_chapter_map(chapter: Chapter):
    """Return a ready ``Map`` for *chapter*, generating random-map chapters first."""
    if isinstance(chapter, RandomMapMissionChapter):
        return chapter.build_map()
    return chapter.map


def load_coop_chapter_map(campaign: "Campaign", chapter: Chapter):
    """Load the mission map for co-op (same ``N.txt`` as single-player)."""
    del campaign  # same chapter object; kept for call-site compatibility
    return ensure_chapter_map(chapter)


class CutSceneChapter(Chapter):
    def __init__(self, campaign, number, path):
        self.campaign = campaign
        self.number = number
        self.path = path
        self._load()

    def _load(self):
        with self.campaign.resources.open_text(self.path) as chapter_file:
            s = chapter_file.read()
        
        # 从文本中提取title部分
        m = re.search("title[ \t]+(.*?)$", s, re.MULTILINE)
        if m:
            title = m.group(1).strip()
            try:
                self.title = [int(title)] # 尝试作为数字处理
            except ValueError:
                self.title = [title]      # 作为文本处理
        else:
            self.title = []
            
        # 从文本中提取sequence部分
        m = re.search("sequence[ \t=]+(.*?)$", s, re.MULTILINE)
        
        if m:
            content = m.group(1).strip()
            
            # 只有当内容被双引号括起来时，才作为整体处理
            if (content.startswith('"') and content.endswith('"')):
                # 去掉引号，作为一个整体
                sequence = [content[1:-1]]
            else:
                # split() 而非 split(" ")：CRLF 会在末 token 上留下 \r，TTS 查不到 ID
                sequence = content.split()
                sequence = [int(x) if x.isdigit() else x for x in sequence]
                # 过滤掉可能的空字符串
                sequence = [item for item in sequence if item]
        else:
            sequence = []
        self.sequence = sequence

    def run(self):
        # 保存当前音乐状态
        current_music_id = sound.current_music
        music_was_playing = pygame.mixer.music.get_busy()
        
        # 完全停止背景音乐，确保过场剧情期间没有音乐播放
        if music_was_playing:
            sound.stop_music()
        
        voice.important(self.title)
        play_sequence(self.sequence)
        self.campaign.unlock_next(self)
        
        # 恢复背景音乐
        if music_was_playing and current_music_id:
            sound.play_music(current_music_id)
            
        if self._next():
            self._next().run()

    def run_for_coop(self):
        """Play this cutscene and advance co-op bookmark only (no auto-start next mission)."""
        current_music_id = sound.current_music
        music_was_playing = pygame.mixer.music.get_busy()

        if music_was_playing:
            sound.stop_music()

        voice.important(self.title)
        play_sequence(self.sequence)
        self.campaign.unlock_next_coop(self)

        if music_was_playing and current_music_id:
            sound.play_music(current_music_id)


class Campaign:
    def _id(self):
        # 生成一个唯一的ID，但保留可读性
        # 对于中文名称，使用name的哈希值作为ID的一部分
        if re.search(r'[^\x00-\x7F]', self.name):  # 检查是否包含非ASCII字符
            hash_part = hashlib.md5(self.name.encode('utf-8')).hexdigest()[:8]
            return f"campaign_{hash_part}"
        else:
            return re.sub("[^a-zA-Z0-9]", "_", self.name)

    def __init__(self, package, path):
        self.name = Path(path).stem
        self.resources = resource_layer(package, self.name)
        self._set_title_and_mods()
        self._set_mods_from_mods_txt()
        self._set_chapters()

    def _set_title_and_mods(self):
        if self.resources.isfile("campaign.txt"):
            with self.resources.open_text("campaign.txt") as campaign_file:
                s = campaign_file.read()
        else:
            s = ""
        m = re.search("(?m)^title[ \t]+(.+)$", s)
        if m:
            self.title = m.group(1).split()
        else:
            self.title = [self.name]
        m = re.search("(?m)^mods[ \t]+(.+)$", s)
        if m:
            self.mods = m.group(1)
        elif re.search("(?m)^mods$", s):
            self.mods = ""
        else:
            self.mods = None
        # 可选战役简介（帝国时代决定版风格的 campaign synopsis）。
        # campaign.txt 里写 `synopsis <tts_id...>`，菜单据此朗读简介；未写则不显示。
        m = re.search("(?m)^synopsis[ \t]+(.+)$", s)
        if m:
            self.synopsis = [
                int(x) if x.isdigit() else x for x in m.group(1).split() if x
            ]
        else:
            self.synopsis = []
        m = re.search("(?m)^coop_campaign[ \t]+(.+)$", s)
        if m:
            self.coop_campaign = bool(int(m.group(1).strip()))
        else:
            self.coop_campaign = False
        m = re.search("(?m)^coop_intro[ \t]+(.+)$", s)
        if m:
            self.coop_intro = parse_chapter_spec(m.group(1))
        else:
            self.coop_intro = frozenset()
        m = re.search("(?m)^coop_missions[ \t]+(.+)$", s)
        if m:
            self.coop_missions = parse_chapter_spec(m.group(1))
        else:
            self.coop_missions = frozenset()
        self.hero_min_level = {}
        m = re.search("(?m)^hero_min_level[ \t]+(.+)$", s)
        if m:
            for token in m.group(1).split():
                if ":" not in token:
                    continue
                ch_s, lv_s = token.split(":", 1)
                try:
                    self.hero_min_level[int(ch_s)] = int(lv_s)
                except ValueError:
                    pass

    def _set_mods_from_mods_txt(self):
        if self.resources.isfile("mods.txt"):
            with self.resources.open_text("mods.txt") as mods_file:
                self.mods = mods_file.read()

    def _set_chapters(self):
        self.chapters = []
        number = 0
        while True:
            filename = f"{number}.txt"
            if not self.resources.isfile(filename):
                filename = f"{number}.zip"
                if not self.resources.isfile(filename):
                    break
            if self._is_a_cutscene(filename):
                c = CutSceneChapter(self, number, filename)
            elif self._is_a_random_map_chapter(filename):
                from .randommap import parse_campaign_random_chapter

                with self.resources.open_text(filename) as chapter_file:
                    text = chapter_file.read()
                config, title, overlay = parse_campaign_random_chapter(text)
                c = RandomMapMissionChapter(self, number, config, title, overlay)
            else:
                with self.resources.open_binary(filename) as chapter_file:
                    map_ = Map.load(chapter_file, filename)
                map_.name = self.name + "/" + str(number)
                c = MissionChapter(self, number, map_)
            self.chapters.append(c)
            number += 1

    def _is_a_cutscene(self, path):
        if not path.endswith(".txt"):
            return False
        with self.resources.open_text(path) as chapter_file:
            return chapter_file.readline().strip() == "cut_scene_chapter"

    def _is_a_random_map_chapter(self, path):
        if not path.endswith(".txt"):
            return False
        with self.resources.open_text(path) as chapter_file:
            return chapter_file.readline().strip() == "random_map_chapter"

    def chapter(self, number):
        if number < len(self.chapters):
            return self.chapters[number]
        else:
            return None

    def next(self, chapter):
        return self.chapter(chapter.number + 1)

    def _get_bookmark(self):
        c = configparser.SafeConfigParser()
        if os.path.isfile(CAMPAIGNS_CONFIG_PATH):
            c.read_file(open(CAMPAIGNS_CONFIG_PATH))
        return c.getint(self._id(), "chapter", fallback=0)

    def _available_chapters(self):
        return self.chapters[: self._get_bookmark() + 1]

    def _get_coop_bookmark(self):
        """合作战役进度书签（与单人 ``chapter`` 独立持久化）。"""
        c = self._read_config()
        return c.getint(self._id(), "coop_chapter", fallback=0)

    def _set_coop_bookmark(self, number):
        c = self._read_config()
        c.set(self._id(), "coop_chapter", repr(number))
        self._write_config(c)

    def _available_coop_chapters(self):
        return self.chapters[: self._get_coop_bookmark() + 1]

    def coop_mission_chapters(self):
        """Mission chapters playable in co-op (listed in ``coop_missions``)."""
        if not self.coop_missions:
            return []
        chapters = []
        for ch in self.chapters:
            if isinstance(ch, CutSceneChapter):
                continue
            if ch.number in self.coop_missions:
                chapters.append(ch)
        return chapters

    def coop_menu_chapters(self):
        """Chapters listed in the co-op campaign browser (intro cutscenes + co-op missions)."""
        if not self.supports_coop():
            return []
        mission_numbers = {ch.number for ch in self.coop_mission_chapters()}
        chapters = []
        for ch in self.chapters:
            if isinstance(ch, CutSceneChapter) and ch.number in self.coop_intro:
                chapters.append(ch)
            elif ch.number in mission_numbers:
                chapters.append(ch)
        return chapters

    def supports_coop(self) -> bool:
        return bool(self.coop_campaign)

    def _set_bookmark(self, number):
        c = configparser.SafeConfigParser()
        if os.path.isfile(CAMPAIGNS_CONFIG_PATH):
            c.read_file(open(CAMPAIGNS_CONFIG_PATH))
        if self._id() not in c.sections():
            c.add_section(self._id())
        c.set(self._id(), "chapter", repr(number))
        c.write(open(CAMPAIGNS_CONFIG_PATH, "w"))

    def _read_config(self):
        c = configparser.SafeConfigParser()
        if os.path.isfile(CAMPAIGNS_CONFIG_PATH):
            c.read_file(open(CAMPAIGNS_CONFIG_PATH))
        if self._id() not in c.sections():
            c.add_section(self._id())
        return c

    def _write_config(self, c):
        c.write(open(CAMPAIGNS_CONFIG_PATH, "w"))

    def get_flags(self):
        c = self._read_config()
        raw = c.get(self._id(), "flags", fallback="")
        if not raw:
            return set()
        return {part.strip() for part in raw.split(",") if part.strip()}

    def has_flag(self, flag):
        return flag in self.get_flags()

    def set_flag(self, flag):
        flags = self.get_flags()
        if flag in flags:
            return
        flags.add(flag)
        c = self._read_config()
        c.set(self._id(), "flags", ",".join(sorted(flags)))
        self._write_config(c)

    def clear_flag(self, flag):
        flags = self.get_flags()
        if flag not in flags:
            return
        flags.discard(flag)
        c = self._read_config()
        if flags:
            c.set(self._id(), "flags", ",".join(sorted(flags)))
        else:
            c.set(self._id(), "flags", "")
        self._write_config(c)

    def get_difficulty(self):
        """返回本战役当前难度等级（持久化于战役配置；缺省为标准）。"""
        from .coop_difficulty import normalize_level

        c = self._read_config()
        return normalize_level(c.get(self._id(), "difficulty", fallback=""))

    def set_difficulty(self, level):
        from .coop_difficulty import normalize_level

        c = self._read_config()
        c.set(self._id(), "difficulty", normalize_level(level))
        self._write_config(c)

    def difficulty_factors(self):
        """单人战役按当前难度返回 (enemy_hp%, enemy_damage%)（单人 → 不做人数缩放）。"""
        from .coop_difficulty import factors

        return factors(self.get_difficulty(), 1)

    def unlock_next(self, chapter):
        if self._get_bookmark() == chapter.number:
            next_chapter = self.next(chapter)
            if next_chapter:
                self._set_bookmark(next_chapter.number)

    def get_coop_difficulty(self):
        """返回合作战役当前难度（与单人 ``difficulty`` 独立；缺省为中等）。"""
        from .coop_difficulty import MODERATE, normalize_level

        c = self._read_config()
        if c.has_option(self._id(), "coop_difficulty"):
            return normalize_level(c.get(self._id(), "coop_difficulty"))
        return MODERATE

    def set_coop_difficulty(self, level):
        from .coop_difficulty import normalize_level

        c = self._read_config()
        c.set(self._id(), "coop_difficulty", normalize_level(level))
        self._write_config(c)

    def unlock_next_coop(self, chapter):
        if self._get_coop_bookmark() == chapter.number:
            next_chapter = self.next(chapter)
            if next_chapter:
                self._set_coop_bookmark(next_chapter.number)

    def run(self):
        if self.mods is not None:
            res.set_mods(self.mods)
        try:
            res.set_campaign(self)

            # 重置战斗状态，并播放战役菜单音乐
            sound.in_battle = False
            sound.play_campaign_music()

            self.menu().run()
        finally:
            res.set_campaign()
            # 在返回主菜单时重置战斗状态并恢复播放主菜单音乐
            sound.in_battle = False
            sound.play_menu_music()

    def menu(self):
        # 帝国时代决定版风格的战役/任务浏览器：
        #  - 顶部可选"战役简介"（若 campaign.txt 提供 synopsis）；
        #  - "难度"项显示当前难度并可修改（持久化）；
        #  - 章节列表标注 已完成 / 未解锁，未解锁章节不可选（避免剧透标题）。
        from .coop_difficulty import label as _difficulty_label

        menu = Menu(self.title, menu_type="submenu")
        if self.synopsis:
            menu.append(mp.CAMPAIGN_SYNOPSIS, (self._play_synopsis, None))
        menu.append(
            mp.DIFFICULTY + _difficulty_label(self.get_difficulty()),
            (self._difficulty_menu, None),
        )
        available = self._available_chapters()
        if len(available) > 1:
            chapter = available[-1]
            menu.append(mp.CONTINUE + chapter.title, chapter)
        bookmark = self._get_bookmark()
        for chapter in self.chapters:
            prefix = nb2msg(chapter.number) if chapter.number > 0 else []
            if chapter.number < bookmark:
                # 已通关：标注"已完成"，仍可重玩
                menu.append(prefix + chapter.title + mp.MISSION_COMPLETED, chapter)
            elif chapter.number == bookmark:
                # 当前可玩章节
                menu.append(prefix + chapter.title, chapter)
            else:
                # 未解锁：仅显示编号 + "未解锁"，不可选，避免剧透标题
                menu.append(prefix + mp.MISSION_LOCKED, None)
        menu.append(mp.BACK, None)
        return menu

    def _reopen_menu(self, _ignored=None):
        """重新展示战役菜单（用于在子操作后回到列表）。"""
        self.menu().run()

    def _play_synopsis(self, _ignored=None):
        if self.synopsis:
            voice.important(self.synopsis)
        self._reopen_menu()

    def _difficulty_menu(self, _ignored=None):
        from .coop_difficulty import LEVELS, label as _difficulty_label

        current = self.get_difficulty()
        entries = []
        default_idx = 1
        for i, lvl in enumerate(LEVELS):
            if lvl == current:
                default_idx = i
            entries.append((_difficulty_label(lvl), (self._choose_difficulty, lvl)))
        entries.append((mp.BACK, (self._reopen_menu, None)))
        Menu(
            mp.DIFFICULTY,
            entries,
            default_choice_index=default_idx,
            menu_type="submenu",
        ).run()

    def _choose_difficulty(self, level):
        self.set_difficulty(level)
        self._reopen_menu()
