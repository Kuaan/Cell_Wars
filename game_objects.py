import random
import math
import uuid
import time
from config import *
from utils import check_collision, get_distance

class GameObject:
    def __init__(self, x, y, size):
        self.x = x
        self.y = y
        self.size = size

class Item(GameObject):
    def __init__(self, x, y, item_type):
        super().__init__(x, y, 20) # 道具大小
        self.id = str(uuid.uuid4())
        self.item_type = item_type # 'spread', 'ricochet', 'arc', 'heal'
        self.dy = 2 # 道具緩慢下落
        
    def update(self):
        self.y += self.dy
        # 邊界判定：如果超出底部則消失
        return -50 <= self.y <= MAP_HEIGHT + 50

class Wall(GameObject):
    def __init__(self, x, y, width, height, owner_id):
        super().__init__(x, y, 0)
        self.width = width
        self.height = height
        self.owner_id = owner_id
        self.hp = 100
        self.max_hp = 100
        self.start_time = time.time()
        self.duration = 25 # 存在25秒

    def is_expired(self):
        return (time.time() - self.start_time) > self.duration

class Bullet(GameObject):
    def __init__(self, x, y, owner_id, owner_type, config, angle_rad=None):
        size = config.get("size", 5)
        super().__init__(x, y, size)
        self.owner_id = owner_id
        self.owner_type = owner_type
        self.damage = config.get("damage", 1)
        self.speed = config.get("speed", 10)
        
        # 使用弧度計算向量
        rad = angle_rad if angle_rad is not None else math.radians(-90)
        self.dx = math.cos(rad) * self.speed
        self.dy = math.sin(rad) * self.speed
        self.ignore_list = []

    def update(self):
        self.x += self.dx
        self.y += self.dy
        return -50 <= self.x <= MAP_WIDTH + 50 and -50 <= self.y <= MAP_HEIGHT + 50

class Player(GameObject):
    def __init__(self, sid, name, skin_id):
        stats = CELL_CONFIG[skin_id]
        super().__init__(random.randint(100, 500), 400, 30)
        self.sid = sid
        self.name = name
        self.skin = skin_id
        self.stats = stats
        self.hp = stats["hp"] * PLAYER_LIVES
        self.max_hp = self.hp
        self.color = stats["color"]
        self.score = 0
        self.charge = 0
        self.last_shot_time = 0
        self.last_hit_time = 0
        self.weapon_type = "default"
        self.weapon_level = 0
        self.weapon_icon = "🔥"
        self.wall_available_at = 0 

    def get_wall_cd(self):
        return max(0, self.wall_available_at - time.time())

    def is_invincible(self):
        return (time.time() - self.last_hit_time) < INVINCIBLE_TIME

    def take_damage(self, amount):
        if self.is_invincible(): return False
        self.hp -= amount
        self.last_hit_time = time.time()
        if self.hp <= 0: self.respawn()
        return True

    def respawn(self):
        self.x, self.y = 300, 400
        self.hp = self.max_hp
        self.score = int(self.score / 2)
        self.weapon_type = "default"
        self.weapon_level = 0

    def apply_item(self, item_type):
        # 處理吃道具邏輯
        base_type = item_type.split('_')[0]
        if self.weapon_type == base_type:
            self.weapon_level = min(2, self.weapon_level + 1)
        else:
            self.weapon_type = base_type
            self.weapon_level = 1
        icons = {"spread": "🔱", "ricochet": "⚡", "arc": "🌙", "default": "🔥"}
        self.weapon_icon = icons.get(base_type, "🔥")

    def get_shoot_config(self):
        key = "default" if self.weapon_type == "default" else f"{self.weapon_type}_lv{self.weapon_level}"
        return WEAPON_CONFIG.get(key, WEAPON_CONFIG["default"])

class Enemy(GameObject):
    def __init__(self, type_id):
        stats = VIRUS_CONFIG[type_id]
        super().__init__(random.randint(0, MAP_WIDTH - stats["size"]), -50, stats["size"])
        self.id = str(uuid.uuid4())
        self.type = type_id
        self.hp = stats["hp"]
        self.max_hp = stats["hp"]
        self.speed = stats["speed"]
        self.score = stats["score"]
        self.prob_drop = stats["drop_rate"]

    def update(self):
        self.y += self.speed * 0.5
        return self.y < MAP_HEIGHT + 50
