"""
pairwise-roguelike-system - RoguelikeSystem

This module contains a deliberately broken implementation.
Fix all bugs so that tests pass.
"""


class RoguelikeSystem:
    def __init__(self):
        self.state = {}

    def generate_dungeon(self, *args, **kwargs):
        """BUG: 地图生成不做随机种子，每次都一样"""
        return None

    def spawn_monsters(self, *args, **kwargs):
        """BUG: 怪物不做层数缩放，1层和10层怪物一样强"""
        return None

    def generate_items(self, *args, **kwargs):
        """BUG: 道具不做稀有度，传说和普通一起掉"""
        return None

    def update_character(self, *args, **kwargs):
        """BUG: 角色不做成长，杀怪不加经验"""
        return None

    def advance_floor(self, *args, **kwargs):
        """BUG: 层数不做Boss层，每10层没有Boss"""
        return None

