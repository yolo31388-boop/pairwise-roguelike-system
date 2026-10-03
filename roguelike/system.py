"""RoguelikeSystem - 随机地下城、怪物、道具、角色成长与层数系统。

Features:
- 地图生成: 随机种子可复现, 多种房间类型, 保证连通性
- 怪物系统: 层数缩放, 怪物组合, 精英/Boss
- 道具系统: 稀有度, 分层道具池, 三合一合成升级
- 角色系统: 经验成长, 技能树, 死亡后保留的永久升级
- 层数系统: 每10层Boss层, 商店层, 事件层
"""

import random

ROOM_TYPES = ("combat", "treasure", "shop", "rest", "event")

RARITY_TIERS = ("common", "uncommon", "rare", "epic", "legendary")

MONSTER_TYPES = {
    "goblin": {"hp": 20, "attack": 5, "defense": 1, "xp": 10},
    "slime": {"hp": 15, "attack": 3, "defense": 0, "xp": 8},
    "skeleton": {"hp": 25, "attack": 6, "defense": 2, "xp": 14},
    "orc": {"hp": 35, "attack": 8, "defense": 3, "xp": 20},
    "bat": {"hp": 10, "attack": 4, "defense": 0, "xp": 6},
    "dark_mage": {"hp": 18, "attack": 10, "defense": 1, "xp": 24},
}

BOSS_TYPES = {
    "dungeon_lord": {"hp": 200, "attack": 20, "defense": 8, "xp": 200},
    "ancient_dragon": {"hp": 300, "attack": 25, "defense": 10, "xp": 300},
}

ITEM_POOLS = {
    1: ["rusty_sword", "wooden_shield", "leather_armor", "small_potion"],
    4: ["iron_sword", "iron_shield", "chainmail", "potion", "bomb"],
    7: ["steel_blade", "tower_shield", "plate_armor", "elixir", "scroll"],
    10: ["dragon_slayer", "aegis", "dragon_scale", "phoenix_down", "holy_grail"],
}

RARITY_WEIGHTS = {
    "common": 50,
    "uncommon": 30,
    "rare": 12,
    "epic": 6,
    "legendary": 2,
}

SKILL_TREE = {
    "power_strike": {"requires_level": 2, "prereq": None},
    "iron_skin": {"requires_level": 3, "prereq": None},
    "double_slash": {"requires_level": 5, "prereq": "power_strike"},
    "battle_rage": {"requires_level": 7, "prereq": "iron_skin"},
    "whirlwind": {"requires_level": 10, "prereq": "double_slash"},
}

PERMANENT_UPGRADES = {
    "toughness": {"stat": "max_hp", "per_rank": 10},
    "sharpening": {"stat": "attack", "per_rank": 2},
    "plating": {"stat": "defense", "per_rank": 1},
}

BOSS_FLOOR_INTERVAL = 10
SHOP_FLOOR_INTERVAL = 5
EVENT_FLOOR_INTERVAL = 3


class RoguelikeSystem:
    def __init__(self, seed=None):
        self.state = {}
        self.seed = seed
        self._rng = random.Random(seed)
        self.floor = 1
        self.meta_currency = 0
        self.permanent_upgrades = {}
        self.character = self._new_character()

    # ------------------------------------------------------------------
    # 地图生成: 随机种子 + 房间类型 + 连通性
    # ------------------------------------------------------------------
    def generate_dungeon(self, seed=None, floor=None, num_rooms=12):
        """生成地下城。相同 seed 生成相同地图; 房间类型多样; 全部房间连通。"""
        if seed is None:
            seed = self._rng.randrange(2**31)
        rng = random.Random(seed)
        floor = self.floor if floor is None else floor

        cells = [(0, 0)]
        occupied = {(0, 0)}
        edges = set()
        while len(cells) < num_rooms:
            x, y = cells[rng.randrange(len(cells))]
            dx, dy = rng.choice(((1, 0), (-1, 0), (0, 1), (0, -1)))
            nx, ny = x + dx, y + dy
            if (nx, ny) not in occupied:
                occupied.add((nx, ny))
                cells.append((nx, ny))
                edges.add(tuple(sorted(((x, y), (nx, ny)))))
        for cell in list(occupied):
            x, y = cell
            for dx, dy in ((1, 0), (0, 1)):
                neighbor = (x + dx, y + dy)
                if neighbor in occupied:
                    edges.add(tuple(sorted((cell, neighbor))))

        index_of = {cell: i for i, cell in enumerate(cells)}
        adjacency = {i: set() for i in range(len(cells))}
        for a, b in edges:
            ia, ib = index_of[a], index_of[b]
            adjacency[ia].add(ib)
            adjacency[ib].add(ia)

        boss_room = max(
            range(len(cells)),
            key=lambda i: abs(cells[i][0]) + abs(cells[i][1]),
        )
        rooms = []
        for i, (x, y) in enumerate(cells):
            if i == 0:
                room_type = "entrance"
            elif i == boss_room:
                room_type = "boss"
            else:
                room_type = rng.choice(ROOM_TYPES)
            rooms.append(
                {
                    "id": i,
                    "x": x,
                    "y": y,
                    "type": room_type,
                    "connections": sorted(adjacency[i]),
                }
            )

        dungeon = {
            "seed": seed,
            "floor": floor,
            "rooms": rooms,
            "edges": sorted(tuple(sorted(e)) for e in edges),
            "entrance": 0,
            "boss_room": boss_room,
            "room_count": len(rooms),
            "connected": self._is_connected(rooms),
        }
        self.state["dungeon"] = dungeon
        return dungeon

    @staticmethod
    def _is_connected(rooms):
        """BFS 验证从入口出发所有房间可达。"""
        if not rooms:
            return False
        adjacency = {room["id"]: room["connections"] for room in rooms}
        visited = {rooms[0]["id"]}
        stack = [rooms[0]["id"]]
        while stack:
            for nxt in adjacency.get(stack.pop(), ()):
                if nxt not in visited:
                    visited.add(nxt)
                    stack.append(nxt)
        return len(visited) == len(rooms)

    # ------------------------------------------------------------------
    # 怪物系统: 层数缩放 + 怪物组合 + 精英/Boss
    # ------------------------------------------------------------------
    def spawn_monsters(self, floor=None, count=None, seed=None):
        """按层数生成怪物组合, 属性随层数缩放, 含精英与Boss。"""
        floor = self.floor if floor is None else floor
        rng = random.Random(seed) if seed is not None else self._rng
        scale = 1.0 + 0.2 * (floor - 1)
        if count is None:
            count = min(3 + floor // 3, 8)

        monsters = []
        names = list(MONSTER_TYPES)
        for _ in range(count):
            name = rng.choice(names)
            base = MONSTER_TYPES[name]
            is_elite = rng.random() < min(0.05 + 0.02 * floor, 0.5)
            mult = 1.5 if is_elite else 1.0
            monsters.append(
                {
                    "name": ("Elite " if is_elite else "") + name,
                    "type": name,
                    "level": floor,
                    "hp": int(base["hp"] * scale * mult),
                    "attack": int(base["attack"] * scale * mult),
                    "defense": int(base["defense"] * scale * mult),
                    "xp_reward": int(base["xp"] * scale * mult),
                    "is_elite": is_elite,
                    "is_boss": False,
                    "rank": "elite" if is_elite else "normal",
                }
            )

        if floor % BOSS_FLOOR_INTERVAL == 0:
            boss_name = rng.choice(list(BOSS_TYPES))
            base = BOSS_TYPES[boss_name]
            monsters.append(
                {
                    "name": boss_name,
                    "type": boss_name,
                    "level": floor,
                    "hp": int(base["hp"] * scale),
                    "attack": int(base["attack"] * scale),
                    "defense": int(base["defense"] * scale),
                    "xp_reward": int(base["xp"] * scale),
                    "is_elite": False,
                    "is_boss": True,
                    "rank": "boss",
                }
            )
        self.state["monsters"] = monsters
        return monsters

    # ------------------------------------------------------------------
    # 道具系统: 稀有度 + 道具池 + 合成升级
    # ------------------------------------------------------------------
    def generate_items(self, floor=None, count=5, seed=None):
        """按层数道具池生成道具, 稀有度按权重随机(层数越高稀有度越好)。"""
        floor = self.floor if floor is None else floor
        rng = random.Random(seed) if seed is not None else self._rng
        pool = self._item_pool_for_floor(floor)
        weights = self._rarity_weights(floor)

        items = []
        for _ in range(count):
            rarity = rng.choices(
                list(weights), weights=list(weights.values()), k=1
            )[0]
            items.append(
                {
                    "name": rng.choice(pool),
                    "rarity": rarity,
                    "floor": floor,
                    "power": (RARITY_TIERS.index(rarity) + 1) * (1 + floor // 5),
                    "combinable": True,
                }
            )
        self.state["items"] = items
        return items

    @staticmethod
    def _item_pool_for_floor(floor):
        pool = []
        for threshold in sorted(ITEM_POOLS):
            if floor >= threshold:
                pool = ITEM_POOLS[threshold]
        return pool

    @staticmethod
    def _rarity_weights(floor):
        bonus = min(floor, 20)
        return {
            "common": max(RARITY_WEIGHTS["common"] - bonus, 10),
            "uncommon": RARITY_WEIGHTS["uncommon"],
            "rare": RARITY_WEIGHTS["rare"] + bonus // 2,
            "epic": RARITY_WEIGHTS["epic"] + bonus // 3,
            "legendary": RARITY_WEIGHTS["legendary"] + bonus // 5,
        }

    def combine_items(self, items):
        """三合一: 3个同名同稀有度道具合成1个更高稀有度道具。"""
        groups = {}
        for item in items:
            groups.setdefault((item["name"], item["rarity"]), []).append(item)

        results = []
        for (name, rarity), group in groups.items():
            source_floor = group[0]["floor"]
            while len(group) >= 3:
                group = group[3:]
                idx = RARITY_TIERS.index(rarity)
                new_rarity = RARITY_TIERS[min(idx + 1, len(RARITY_TIERS) - 1)]
                results.append(
                    {
                        "name": name,
                        "rarity": new_rarity,
                        "floor": source_floor,
                        "power": (RARITY_TIERS.index(new_rarity) + 1) * 3,
                        "combinable": True,
                        "upgraded": True,
                    }
                )
            results.extend(group)
        return results

    # ------------------------------------------------------------------
    # 角色系统: 成长 + 技能树 + 永久升级
    # ------------------------------------------------------------------
    def _new_character(self):
        character = {
            "level": 1,
            "xp": 0,
            "xp_to_next": 100,
            "max_hp": 100,
            "attack": 10,
            "defense": 5,
            "skill_points": 0,
            "skills": [],
            "alive": True,
        }
        return self._apply_permanent_upgrades(character)

    def _apply_permanent_upgrades(self, character):
        for name, rank in self.permanent_upgrades.items():
            upgrade = PERMANENT_UPGRADES[name]
            character[upgrade["stat"]] += upgrade["per_rank"] * rank
        return character

    def update_character(self, kills=0, xp=0, learn=None):
        """杀怪获得经验并升级; 可学习技能树中的技能。返回更新后的角色。"""
        character = self.character
        if not character.get("alive", True):
            return character

        gained = int(xp) + int(kills) * 10
        character["xp"] += gained
        leveled = False
        while character["xp"] >= character["xp_to_next"]:
            character["xp"] -= character["xp_to_next"]
            character["level"] += 1
            character["xp_to_next"] = 100 * character["level"]
            character["max_hp"] += 10
            character["attack"] += 2
            character["defense"] += 1
            character["skill_points"] += 1
            leveled = True
        character["leveled_up"] = leveled

        if learn:
            self.learn_skill(learn)
        self.state["character"] = character
        return character

    def learn_skill(self, name):
        """按技能树要求学习技能(等级 + 前置 + 技能点)。"""
        character = self.character
        if name not in SKILL_TREE:
            return False
        if name in character["skills"]:
            return False
        node = SKILL_TREE[name]
        if character["level"] < node["requires_level"]:
            return False
        if node["prereq"] and node["prereq"] not in character["skills"]:
            return False
        if character["skill_points"] < 1:
            return False
        character["skill_points"] -= 1
        character["skills"].append(name)
        return True

    def buy_permanent_upgrade(self, name, cost=100):
        """用meta货币购买永久升级, 死亡后依然保留。"""
        if name not in PERMANENT_UPGRADES or self.meta_currency < cost:
            return False
        self.meta_currency -= cost
        self.permanent_upgrades[name] = self.permanent_upgrades.get(name, 0) + 1
        self._apply_permanent_upgrades(self.character)
        return True

    def reset_character(self):
        """角色死亡: 等级/经验/技能清零, 永久升级与meta货币保留。"""
        self.meta_currency += self.character["level"] * 10
        self.character = self._new_character()
        return self.character

    # ------------------------------------------------------------------
    # 层数系统: Boss层 + 商店层 + 事件层
    # ------------------------------------------------------------------
    def advance_floor(self, floors=1):
        """推进层数并返回该层类型: 每10层Boss, 每5层商店, 每3层事件。"""
        self.floor += floors
        floor = self.floor
        is_boss = floor % BOSS_FLOOR_INTERVAL == 0
        is_shop = not is_boss and floor % SHOP_FLOOR_INTERVAL == 0
        is_event = not is_boss and not is_shop and floor % EVENT_FLOOR_INTERVAL == 0
        if is_boss:
            floor_type = "boss"
        elif is_shop:
            floor_type = "shop"
        elif is_event:
            floor_type = "event"
        else:
            floor_type = "normal"
        info = {
            "floor": floor,
            "floor_type": floor_type,
            "is_boss_floor": is_boss,
            "is_shop_floor": is_shop,
            "is_event_floor": is_event,
        }
        self.state["floor_info"] = info
        return info
