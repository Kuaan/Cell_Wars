import random
import math
import uuid
import time
from config import * # 匯入所有設定 (MAP_WIDTH, WEAPON_CONFIG 等)
from utils import check_collision, get_distance

class GameObject:
    def __init__(self, x, y, size):
        self.x = x
        self.y = y
        self.size = size

class Wall(GameObject):
    def __init__(self, x, y, owner_id, width, height):
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

class Bullet(GameObject):
    def __init__(self, x, y, owner_id, owner_type, config, angle_deg=None):
        size = config.get("size", 5)
        super().__init__(x, y, size)
        self.owner_id = owner_id
        self.owner_type = owner_type
        self.damage = config.get("damage", 1)
        self.color = config.get("color", None)
        
        # 核心屬性
        self.angle = angle_deg if angle_deg is not None else -90
        self.speed = config.get("speed", 10)
        self.b_type = config.get("type", "linear")
        
        angle_rad = math.radians(self.angle)
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
            if self.x <= 0 or self.x >= MAP_WIDTH:
                self.dx *= -1
                self.bounce_left -= 1
            if self.y <= 0:
                self.dy *= -1
                self.bounce_left -= 1
            self.angle = math.degrees(math.atan2(self.dy, self.dx))
                
        return -50 <= self.x <= MAP_WIDTH + 50 and -50 <= self.y <= MAP_HEIGHT + 50

class Player(GameObject):
    def __init__(self, sid, name, skin_id):
        # 防呆轉型
        try:
            s_id = int(skin_id)
            stats = CELL_CONFIG.get(s_id, CELL_CONFIG[1])
        except:
            stats = CELL_CONFIG[1]
            s_id = 1

        super().__init__(random.randint(100, 500), 400, 30)
        self.sid = sid
        self.name = name
        self.skin = s_id
        self.stats = stats
        self.hp = stats["hp"] * PLAYER_LIVES
        self.max_hp = stats["hp"] * PLAYER_LIVES
        self.lives_count = PLAYER_LIVES
        self.color = stats["color"]
        self.score = 0
        self.charge = 0 # 能量條 (0.0 ~ 3.0)
        
        self.last_hit_time = 0
        self.last_shot_time = 0
        
        self.weapon_type = "default"
        self.weapon_level = 0
        self.weapon_icon = "🔥" 

    def is_invincible(self):
        return (time.time() - self.last_hit_time) < INVINCIBLE_TIME

    def get_shoot_config(self):
        key = "default"
        if self.weapon_type != "default":
            key = f"{self.weapon_type}_lv{self.weapon_level}"
        return WEAPON_CONFIG.get(key, WEAPON_CONFIG["default"])

    def shoot(self, target_angle=None):
        current_time = time.time()
        w_cfg = self.get_shoot_config()
        
        base_cd = w_cfg.get("cooldown", FIRE_COOLDOWN)
        fr_mult = w_cfg.get("fire_rate_mult", 1.0)
        real_cd = base_cd / fr_mult

        if current_time - self.last_shot_time < real_cd:
            return []

        self.last_shot_time = current_time
        new_bullets = []
        base_angle = target_angle if target_angle is not None else -90
        
        angles = w_cfg.get("angles", [0])
        if angles == "random_forward":
            for _ in range(w_cfg.get("count", 1)):
                b = Bullet(self.x, self.y, self.sid, "player", w_cfg, base_angle + random.uniform(-30, 30))
                new_bullets.append(b)
        else:
            for offset in angles:
                b = Bullet(self.x, self.y, self.sid, "player", w_cfg, base_angle + offset)
                new_bullets.append(b)
        return new_bullets

    def take_damage(self, amount):
        if self.is_invincible(): return False
        self.hp -= amount
        self.last_hit_time = time.time()
        if self.hp <= 0: self.respawn()
        return True

    def respawn(self):
        self.x, self.y = random.randint(100, 500), 400
        self.hp = self.max_hp
        self.score = int(self.score * 0.5)
        self.weapon_type = "default"
        self.weapon_level = 0
