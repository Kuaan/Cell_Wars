import random, math, uuid, time
from config import *

class GameObject:
    def __init__(self, x, y, size):
        self.x, self.y, self.size = x, y, size

class Wall(GameObject):
    def __init__(self, x, y, width, height, owner_id):
        super().__init__(x, y, 0)
        self.width, self.height = width, height
        self.owner_id = owner_id
        self.hp = 100
        self.start_time = time.time()
        self.duration = 25 # 存在25秒

class Bullet(GameObject):
    def __init__(self, x, y, owner_id, owner_type, config, angle_rad=None):
        size = config.get("size", 5)
        super().__init__(x, y, size)
        self.owner_id, self.owner_type = owner_id, owner_type
        self.damage = config.get("damage", 1)
        self.speed = config.get("speed", 10)
        
        # 使用弧度計算精確向量
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
        self.sid, self.name, self.skin, self.stats = sid, name, skin_id, stats
        self.hp = stats["hp"] * PLAYER_LIVES
        self.max_hp = self.hp
        self.color = stats["color"]
        self.score = self.charge = 0
        self.last_shot_time = self.last_hit_time = 0
        self.weapon_type, self.weapon_icon = "default", "🔥"
        self.weapon_level = 0
        # 牆壁冷卻
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

    def get_shoot_config(self):
        key = "default" if self.weapon_type == "default" else f"{self.weapon_type}_lv{self.weapon_level}"
        return WEAPON_CONFIG.get(key, WEAPON_CONFIG["default"])

class Enemy(GameObject):
    def __init__(self, type_id):
        stats = VIRUS_CONFIG[type_id]
        super().__init__(random.randint(0, MAP_WIDTH-stats["size"]), -50, stats["size"])
        self.id = str(uuid.uuid4())
        self.type = type_id
        self.hp = stats["hp"]
        self.speed = stats["speed"]
        self.score = stats["score"]
        self.prob_drop = stats["drop_rate"]

    def update(self):
        self.y += self.speed * 0.5
        return self.y < MAP_HEIGHT + 50
