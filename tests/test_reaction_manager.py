import unittest
from unittest.mock import MagicMock
from core.enums import Element, ReactionType
from mechanics.reaction_manager import ReactionManager

class TestReactionManager(unittest.TestCase):
    def setUp(self):
        self.mock_owner = MagicMock()
        self.mock_owner.name = "TestDummy"
        self.mock_owner.buffs = MagicMock() # Mock buff manager
        self.mock_engine = MagicMock()
        
        self.manager = ReactionManager(self.mock_owner, self.mock_engine)

    def test_initial_state(self):
        self.assertIsNone(self.manager.attachment_element)
        self.assertEqual(self.manager.attachment_stacks, 0)

    def test_attach_element(self):
        # 测试施加元素附着
        result = self.manager.apply_hit(Element.HEAT, attachments=[Element.HEAT])

        self.assertIn(ReactionType.ATTACH, result.reaction_types)
        self.assertEqual(self.manager.attachment_element, Element.HEAT)
        self.assertEqual(self.manager.attachment_stacks, 1)

    def test_reaction_trigger(self):
        # 先附着火
        self.manager.apply_hit(Element.HEAT, attachments=[Element.HEAT])

        # 再打雷，触发导电
        result = self.manager.apply_hit(Element.ELECTRIC, attachments=[Element.ELECTRIC])

        self.assertIn(ReactionType.CONDUCTIVE, result.reaction_types)
        self.assertIsNone(self.manager.attachment_element) # 反应后消耗附着

        # 验证Buff是否施加 (ReactionManager调用的是owner.add_buff)
        self.mock_owner.add_buff.assert_called()

if __name__ == '__main__':
    unittest.main()
