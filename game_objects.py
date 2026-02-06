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

<<<<<<< HEAD
class Item(GameObject):
    def __init__(self, x, y, item_type):
        super().__init__(x, y, 20) # 膠囊大小
        self.id = str(uuid.uuid4())
        self.item_type = item_type # 'spread', 'ricochet', 'arc', 'heal'
        self.dy = 2 # 道具緩慢下落
        
    def update(self):
        self.y += self.dy
        return -50 <= self.y <= MAP_HEIGHT + 50
=======
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
>>>>>>> cf61c11d6df7b5141882f1c3ab7a2e9f88b1a6d6

class Bullet(GameObject):
    def __init__(self, x, y, owner_id, owner_type, config, angle_deg=None):
        size = config.get("size", 5)
        super().__init__(x, y, size)
        self.owner_id = owner_id
<<<<<<< HEAD
        self.owner_type = owner_type # 'player', 'enemy', 'boss'
        self.damage = config.get("damage", 1)
        self.color = config.get("color", None)
        self.config = config
        
        # 運動邏輯
        self.speed = config.get("speed", 10)
        self.b_type = config.get("type", "linear")
        
        # 計算向量
        angle_rad = math.radians(angle_deg if angle_deg is not None else -90)
        self.dx = math.cos(angle_rad) * self.speed
        self.dy = math.sin(angle_rad) * self.speed
        
        # 特殊屬性
=======
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
        
>>>>>>> cf61c11d6df7b5141882f1c3ab7a2e9f88b1a6d6
        self.bounce_left = config.get("bounce", 0)
        self.bounce_damage_mult = config.get("bounce_damage", 0.3)
        self.range_limit = config.get("range", 9999)
        self.dist_traveled = 0
<<<<<<< HEAD
        self.ignore_list = [] # 彈射時避免重複打同一隻
        
        # 弧射參數
        if self.b_type == "arc":
            self.arc_angle = 0
            self.curve_dir = random.choice([-1, 1])

    def update(self):
        # 移動
        if self.b_type == "arc":
            # 弧形運動：在原向量基礎上疊加切線運動
=======
        self.ignore_list = []
        
        if self.b_type == "arc":
            self.curve_dir = random.choice([-1, 1])

    def update(self):
        if self.b_type == "arc":
>>>>>>> cf61c11d6df7b5141882f1c3ab7a2e9f88b1a6d6
            self.x += self.dx + (math.cos(time.time() * 5) * 5 * self.curve_dir)
            self.y += self.dy
        else:
            self.x += self.dx
            self.y += self.dy
            
        self.dist_traveled += self.speed
        
<<<<<<< HEAD
        # 邊界反彈 (彈射屬性)
=======
>>>>>>> cf61c11d6df7b5141882f1c3ab7a2e9f88b1a6d6
        if self.b_type == "bounce" and self.bounce_left > 0:
            if self.x <= 0 or self.x >= MAP_WIDTH:
                self.dx *= -1
<<<<<<< HEAD
                hit_wall = True
            if self.y <= 0: # 頂部
                self.dy *= -1
                hit_wall = True
            
            if hit_wall:
                self.bounce_left -= 1
                return True # 活著
                
        # 射程限制
        if self.dist_traveled > self.range_limit:
            return False

        # 一般邊界檢查
        return -50 <= self.x <= MAP_WIDTH + 50 and -50 <= self.y <= MAP_HEIGHT + 50

    def handle_hit(self, target):
        """處理命中後的邏輯 (回傳 False 代表子彈消失, True 代表子彈繼續)"""
        if self.b_type == "bounce" and self.bounce_left > 0:
            self.damage *= self.bounce_damage_mult
            self.bounce_left -= 1
            self.ignore_list.append(target) # 短時間不打同一隻
            
            # 尋找最近的其他目標 (簡單的反彈邏輯：直接反轉或是隨機偏轉)
            # 這裡做簡單物理反彈：假設撞到圓形切線
            self.dx *= -1 
            self.dy *= -1 
            # 為了避免黏在敵人身上，稍微推開
            self.x += self.dx * 2
            self.y += self.dy * 2
            return True
        return False

class Player(GameObject):
    def __init__(self, sid, name, skin_id):
        stats = CELL_CONFIG[skin_id]
=======
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

>>>>>>> cf61c11d6df7b5141882f1c3ab7a2e9f88b1a6d6
        super().__init__(random.randint(100, 500), 400, 30)
        self.sid = sid
        self.name = name
        self.skin = s_id
        self.stats = stats
<<<<<<< HEAD
        self.hp = stats["hp"] * PLAYER_LIVES # 5條命總血量
=======
        self.hp = stats["hp"] * PLAYER_LIVES
>>>>>>> cf61c11d6df7b5141882f1c3ab7a2e9f88b1a6d6
        self.max_hp = stats["hp"] * PLAYER_LIVES
        self.lives_count = PLAYER_LIVES
        self.color = stats["color"]
        self.score = 0
<<<<<<< HEAD
        self.charge = 0
        self.hit_accumulated = 0
=======
        self.charge = 0 # 能量條 (0.0 ~ 3.0)
>>>>>>> cf61c11d6df7b5141882f1c3ab7a2e9f88b1a6d6
        
        self.last_hit_time = 0
        self.last_shot_time = 0
        self.last_skill_time = 0
        
<<<<<<< HEAD
        # 武器狀態
        self.weapon_level = 0
        self.weapon_type = "default" # default, spread, ricochet, arc
=======
        self.weapon_type = "default"
        self.weapon_level = 0
>>>>>>> cf61c11d6df7b5141882f1c3ab7a2e9f88b1a6d6
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
<<<<<<< HEAD
        
        # 死亡判定 (扣命模擬)
        unit_hp = self.stats["hp"]
        current_lives = math.ceil(self.hp / unit_hp)
        
        if self.hp <= 0:
            self.respawn()
        elif current_lives < self.lives_count:
             # 掉了一條命但還沒死透，重置武器
             self.reset_weapon()
             self.lives_count = current_lives
=======
        if self.hp <= 0: self.respawn()
>>>>>>> cf61c11d6df7b5141882f1c3ab7a2e9f88b1a6d6
        return True

    def respawn(self):
        self.x, self.y = random.randint(100, 500), 400
        self.hp = self.max_hp
<<<<<<< HEAD
        self.lives_count = PLAYER_LIVES
        self.score = int(self.score / 2)
        self.charge = 0
        self.reset_weapon()

    def reset_weapon(self):
        self.weapon_type = "default"
        self.weapon_level = 0
        self.weapon_icon = "🔥"

    def apply_item(self, item_type):
        # 簡單狀態機
        base_type = item_type.split('_')[0] # spread, ricochet...
        
        if self.weapon_type.startswith(base_type):
            # 同類別，升級
            self.weapon_level = min(2, self.weapon_level + 1)
        else:
            # 不同類別，覆蓋且 Lv1
            self.weapon_type = base_type
            self.weapon_level = 1
            
        # 更新 Icon
        icons = {"spread": "🔱", "ricochet": "⚡", "arc": "🌙", "default": "🔥"}
        self.weapon_icon = icons.get(base_type, "🔥")

    def get_shoot_config(self):
        # 根據當前狀態回傳子彈設定
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
        # 簡單 AI 移動邏輯 (Boss 會有 Server 端額外控制，這裡處理基本移動)
        if self.type == 999: # Boss
            pass # 由 Server 主控
        else:
            self.y += self.speed * 0.5
            self.move_timer += 1
            if self.move_timer > 30:
                self.x += random.choice([-20, 20, 0])
                self.move_timer = 0
            self.x = max(0, min(MAP_WIDTH - self.size, self.x))
            if self.y > MAP_HEIGHT: self.y = -50
=======
        self.score = int(self.score * 0.5)
        self.weapon_type = "default"
        self.weapon_level = 0
>>>>>>> cf61c11d6df7b5141882f1c3ab7a2e9f88b1a6d6
