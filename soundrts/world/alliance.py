"""
轻量版联盟视野管理器

目标：
- 管理同一联盟玩家的成员列表
- 提供共享“探测”信息的通道（例如探测到的隐形单位）
- 不接管、不替换现有玩家视野/感知逻辑
"""

from typing import List


class AllianceVisionManager:
    def __init__(self, alliance_id: str):
        self.alliance_id = alliance_id
        self.players: List = []
        # 共享探测集合（隐形/隐身单位被探测到时可加入此集合）
        self.detected_units = set()

    def add_player(self, player):
        if player not in self.players:
            self.players.append(player)
            player.alliance_vision_manager = self

    def remove_player(self, player):
        if player in self.players:
            self.players.remove(player)
            if getattr(player, 'alliance_vision_manager', None) is self:
                player.alliance_vision_manager = None

    def share_detection(self, unit):
        """在联盟内共享被探测到的单位（不影响现有视野机制）。"""
        self.detected_units.add(unit)
        for p in self.players:
            p.detected_units.add(unit)


