import unittest
import os
import tempfile
from soundrts.world import World
from soundrts.worldclient import DummyClient
from soundrts.mapfile import Map

class TestIsAllied(unittest.TestCase):
    def setUp(self):
        # 创建临时测试地图文件
        self.temp_dir = tempfile.TemporaryDirectory()
        self.map_path = os.path.join(self.temp_dir.name, "test_map.txt")
        
    def tearDown(self):
        # 清理临时文件
        self.temp_dir.cleanup()
        
    def test_is_allied_default(self):
        """测试默认情况下玩家是敌对关系"""
        # 创建没有is_allied参数的地图
        with open(self.map_path, "w") as f:
            f.write("title test_map\n")
            f.write("nb_players_min 2\n")
            f.write("nb_players_max 2\n")
            f.write("starting_squares a1 a2\n")
        
        # 加载地图
        test_map = Map(self.map_path)
        world = World()
        world.load_and_build_map(test_map)
        
        # 创建两个玩家
        client1 = DummyClient()
        client2 = DummyClient()
        world.populate_map([client1, client2])
        
        player1 = world.players[0]
        player2 = world.players[1]
        
        # 默认情况下玩家应该是敌对关系
        self.assertTrue(player1.player_is_an_enemy(player2))
        self.assertTrue(player2.player_is_an_enemy(player1))
        
    def test_is_allied_enabled(self):
        """测试开启is_allied=1时玩家是联盟关系"""
        # 创建有is_allied=1参数的地图
        with open(self.map_path, "w") as f:
            f.write("title test_map\n")
            f.write("nb_players_min 2\n")
            f.write("nb_players_max 2\n")
            f.write("is_allied 1\n")
            f.write("starting_squares a1 a2\n")
        
        # 加载地图
        test_map = Map(self.map_path)
        world = World()
        world.load_and_build_map(test_map)
        
        # 创建两个玩家
        client1 = DummyClient()
        client2 = DummyClient()
        world.populate_map([client1, client2])
        
        player1 = world.players[0]
        player2 = world.players[1]
        
        # 启用is_allied=1时，玩家应该是联盟关系
        self.assertFalse(player1.player_is_an_enemy(player2))
        self.assertFalse(player2.player_is_an_enemy(player1))
        
        # 检查allied列表
        self.assertIn(player2, player1.allied)
        self.assertIn(player1, player2.allied)
        
    def test_is_allied_disabled(self):
        """测试is_allied=0时玩家是敌对关系"""
        # 创建有is_allied=0参数的地图
        with open(self.map_path, "w") as f:
            f.write("title test_map\n")
            f.write("nb_players_min 2\n")
            f.write("nb_players_max 2\n")
            f.write("is_allied 0\n")
            f.write("starting_squares a1 a2\n")
        
        # 加载地图
        test_map = Map(self.map_path)
        world = World()
        world.load_and_build_map(test_map)
        
        # 创建两个玩家
        client1 = DummyClient()
        client2 = DummyClient()
        world.populate_map([client1, client2])
        
        player1 = world.players[0]
        player2 = world.players[1]
        
        # is_allied=0时，玩家应该是敌对关系
        self.assertTrue(player1.player_is_an_enemy(player2))
        self.assertTrue(player2.player_is_an_enemy(player1))

if __name__ == "__main__":
    unittest.main() 