#v430
import random
import math
import uuid
import time
from config import *
from utils import check_collision, get_distance

# 假設 utils 有這些，若無 server.py 會處理碰撞邏輯
# from utils import check_collision, get_distance 

class GameObject:
    def __init__(self, x, y, size):
        self.x = x
        self.y = y
        self.size = size

class Wall(GameObject):
    def __init__(self, x, y, owner_id, width, height):
        # Wall 比較特殊，size 這裡我們用較大的一邊作為簡易碰撞判定半徑
        super().__init__(x, y, max(width, height))
        self.id = str(uuid.uuid4())
        self.owner_id = owner_id
        self.width = width
        self.height = height
        self.hp = WALL_CONFIG["hp"]
        self.max_hp = WALL_CONFIG["hp"]
        self.spawn_time = time.time()
        self.duration = WALL_CONFIG["duration"]
        self.color = WALL_CONFIG["color"]
    
    def is_expired(self):
        return (time.time() - self.spawn_time) > self.duration

class Item(GameObject):
    def __init__(self, x, y, item_type):
        super().__init__(x, y, 20)
        self.id = str(uuid.uuid4())
        self.item_type = item_type
        self.dy = 2
        
    def update(self):
        self.y += self.dy
        return -50 <= self.y <= MAP_HEIGHT + 50

class Bullet(GameObject):
    def __init__(self, x, y, owner_id, owner_type, config, angle_deg=None):
        size = config.get("size", 5)
        super().__init__(x, y, size)
        self.owner_id = owner_id
        self.owner_type = owner_type
        self.damage = config.get("damage", 1)
        self.color = config.get("color", None)
        self.config = config
        
        self.speed = config.get("speed", 10)
        self.b_type = config.get("type", "linear")
        
        # 這裡 angle_deg 是絕對角度
        angle_rad = math.radians(angle_deg if angle_deg is not None else -90)
        self.dx = math.cos(angle_rad) * self.speed
        self.dy = math.sin(angle_rad) * self.speed
        
        self.bounce_left = config.get("bounce", 0)
        self.bounce_damage_mult = config.get("bounce_damage", 0.3)
        self.range_limit = config.get("range", 9999)
        self.dist_traveled = 0
        self.ignore_list = []
        
        if self.b_type == "arc":
            self.curve_dir = random.choice([-1, 1])

    def update(self):
        if self.b_type == "arc":
            self.x += self.dx + (math.cos(time.time() * 5) * 5 * self.curve_dir)
            self.y += self.dy
        else:
            self.x += self.dx
            self.y += self.dy
            
        self.dist_traveled += self.speed
        
        if self.b_type == "bounce" and self.bounce_left > 0:
            hit_wall = False
            if self.x <= 0 or self.x >= MAP_WIDTH:
                self.dx *= -1
                hit_wall = True
            if self.y <= 0:
                self.dy *= -1
                hit_wall = True
            
            if hit_wall:
                self.bounce_left -= 1
                return True
                
        if self.dist_traveled > self.range_limit:
            return False

        return -50 <= self.x <= MAP_WIDTH + 50 and -50 <= self.y <= MAP_HEIGHT + 50

    def handle_hit(self, target):
        if self.b_type == "bounce" and self.bounce_left > 0:
            self.damage *= self.bounce_damage_mult
            self.bounce_left -= 1
            if target: self.ignore_list.append(target)
            self.dx *= -1 
            self.dy *= -1 
            self.x += self.dx * 2
            self.y += self.dy * 2
            return True
        return False

class Player(GameObject):
    def __init__(self, sid, name, skin_id):
        stats = CELL_CONFIG[skin_id]
        super().__init__(random.randint(100, 500), 400, 30)
        self.sid = sid
        self.name = name
        self.skin = skin_id
        self.stats = stats
        self.hp = stats["hp"] * PLAYER_LIVES
        self.max_hp = stats["hp"] * PLAYER_LIVES
        self.lives_count = PLAYER_LIVES
        self.color = stats["color"]
        self.score = 0
        self.charge = 0
        self.hit_accumulated = 0
        
        self.last_hit_time = 0
        self.last_shot_time = 0
        self.last_skill_time = 0
        
        # 造牆技能
        self.wall_cd_finish_time = 0 # 紀錄CD結束的時間點
        self.is_building_pressed = False # 是否按著按鈕
        
        self.weapon_level = 0
        self.weapon_type = "default"
        self.weapon_icon = "🔥" 

    def is_invincible(self):
        return (time.time() - self.last_hit_time) < INVINCIBLE_TIME

    def take_damage(self, amount):
        if self.is_invincible(): return False
        self.hp -= amount
        self.last_hit_time = time.time()
        
        unit_hp = self.stats["hp"]
        current_lives = math.ceil(self.hp / unit_hp)
        
        if self.hp <= 0:
            self.respawn()
        elif current_lives < self.lives_count:
             self.reset_weapon()
             self.lives_count = current_lives
        return True

    def respawn(self):
        self.x, self.y = random.randint(100, 500), 400
        self.hp = self.max_hp
        self.lives_count = PLAYER_LIVES
        self.score = int(self.score / 2)
        self.charge = 0
        self.reset_weapon()

    def reset_weapon(self):
        self.weapon_type = "default"
        self.weapon_level = 0
        self.weapon_icon = "🔥"

    def apply_item(self, item_type):
        base_type = item_type.split('_')[0]
        if self.weapon_type.startswith(base_type):
            self.weapon_level = min(2, self.weapon_level + 1)
        else:
            self.weapon_type = base_type
            self.weapon_level = 1
        icons = {"spread": "🔱", "ricochet": "⚡", "arc": "🌙", "default": "🔥"}
        self.weapon_icon = icons.get(base_type, "🔥")

    def get_shoot_config(self):
        key = "default"
        if self.weapon_type != "default":
            key = f"{self.weapon_type}_lv{self.weapon_level}"
        return WEAPON_CONFIG.get(key, WEAPON_CONFIG["default"])

class Enemy(GameObject):
    def __init__(self, type_id):
        stats = VIRUS_CONFIG[type_id]
        super().__init__(random.randint(0, MAP_WIDTH - stats["size"]), random.randint(-100, 0), stats["size"])
        self.id = str(uuid.uuid4())
        self.type = type_id
        self.hp = stats["hp"]
        self.max_hp = stats["hp"]
        self.speed = stats["speed"]
        self.score = stats["score"]
        self.prob_drop = stats["drop_rate"]
        self.move_timer = 0
        self.dx = 0
        self.dy = 0
        
    def update(self):
        if self.type == 999:
            pass
        else:
            self.y += self.speed * 0.5
            self.move_timer += 1
            if self.move_timer > 30:
                self.x += random.choice([-20, 20, 0])
                self.move_timer = 0
            self.x = max(0, min(MAP_WIDTH - self.size, self.x))
            if self.y > MAP_HEIGHT: self.y = -50
