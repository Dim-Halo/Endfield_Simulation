import unittest
from core.config_manager import ConfigManager, get_config

class TestConfigManager(unittest.TestCase):
    def setUp(self):
        # 重置单例以保证测试隔离
        ConfigManager._instance = None
        self.config = get_config()

    def test_singleton(self):
        c1 = get_config()
        c2 = get_config()
        self.assertIs(c1, c2)

    def test_default_values(self):
        self.assertEqual(self.config.tick_rate, 10)
        self.assertEqual(self.config.reaction_base_mv["burst"], 160)
        self.assertTrue(self.config.enable_statistics)

    def test_reaction_mv_calculation(self):
        # 测试基础倍率计算
        # burst: 160 * (1+0) = 160
        # tech: 1 + 0 = 1
        # spell: 1 + (5/980)*(80-1) = 1 + 0.403...
        mv = self.config.get_reaction_mv("burst", level=0, tech_power=0, attacker_lvl=1)
        self.assertAlmostEqual(mv, 160.0)

        # 测试带Tech的计算
        # tech=100 -> mult = 2.0
        mv_tech = self.config.get_reaction_mv("burst", level=0, tech_power=100, attacker_lvl=1)
        self.assertAlmostEqual(mv_tech, 320.0)

if __name__ == '__main__':
    unittest.main()
