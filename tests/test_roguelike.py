import pytest
from roguelike.system import RoguelikeSystem


class TestRoguelikeSystem:

    def test_generate_dungeon(self):
        """地图生成不做随机种子，每次都一样"""
        obj = RoguelikeSystem()
        result = obj.generate_dungeon()
        self.assertIsNotNone(result)

    def test_spawn_monsters(self):
        """怪物不做层数缩放，1层和10层怪物一样强"""
        obj = RoguelikeSystem()
        result = obj.spawn_monsters()
        self.assertIsNotNone(result)

    def test_generate_items(self):
        """道具不做稀有度，传说和普通一起掉"""
        obj = RoguelikeSystem()
        result = obj.generate_items()
        self.assertIsNotNone(result)

    def test_update_character(self):
        """角色不做成长，杀怪不加经验"""
        obj = RoguelikeSystem()
        result = obj.update_character()
        self.assertIsNotNone(result)

    def test_advance_floor(self):
        """层数不做Boss层，每10层没有Boss"""
        obj = RoguelikeSystem()
        result = obj.advance_floor()
        self.assertIsNotNone(result)

