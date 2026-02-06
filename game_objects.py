# game_objects.py
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
        self.size = size # 視為直徑
        self.radius = size / 2

class Item(GameObject):
    def __init__(self, x, y, item_type):
        super().__init__(x, y, 20) 
        self.id = str(uuid.uuid4())
        self.item_type = item_type # 'spread', 'ricochet', 'arc', 'heal'
        self.dy = 1.5 # 稍微慢一點，比較好接
        
    def update(self):
        self.y += self.dy
        return -50 <= self.y <= MAP_HEIGHT + 50

class Bullet(GameObject):
    def __init__(self, x, y, owner_id, owner_type, config, angle_deg, size=5):
        super().__init__(x, y, size)
        self.owner_id = owner_id
        self.owner_type = owner_type
        
        # 戰鬥屬性
        self.damage = config.get("damage", 1)
        self.color = config.get("color", None)
        self.b_type = config.get("type", "linear")
        self.speed = config.get("speed", 10)
        
        # 運動向量
        angle_rad = math.radians(angle_deg)
        self.dx = math.cos(angle_rad) * self.speed
        self.dy = math.sin(angle_rad) * self.speed
        
        # 彈射/特殊邏輯
        self.bounce_left = config.get("bounce", 0)
        self.bounce_damage_mult = config.get("bounce_damage", 0.3)
        self.range_limit = config.get("range", 2000)
        self.dist_traveled = 0
        self.ignore_list = [] # 避免連續命中同一敵人

        # 弧射邏輯
        if self.b_type == "arc":
            self.curve_factor = random.choice([-0.2, 0.2]) # 左右隨機偏轉
            self.curve_timer = 0

    def update(self):
        # 弧射：非線性移動
        if self.b_type == "arc":
            self.x += self.dx + (math.sin(self.curve_timer) * 5)
            self.y += self.dy
            self.curve_timer += self.curve_factor
        else:
            self.x += self.dx
            self.y += self.dy
            
        self.dist_traveled += self.speed
        
        # 射程檢查
        if self.dist_traveled > self.range_limit:
            return False

        # 邊界檢查 (彈射子彈遇到牆壁反彈)
        if self.b_type == "bounce" and self.bounce_left > 0:
            hit_wall = False
            if self.x <= 0 or self.x >= MAP_WIDTH:
                self.dx *= -1
                hit_wall = True
            elif self.y <= 0:
                self.dy *= -1
                hit_wall = True
            
            if hit_wall:
                self.bounce_left -= 1
                return True

        # 一般子彈出界檢查
        return -50 <= self.x <= MAP_WIDTH + 50 and -50 <= self.y <= MAP_HEIGHT + 50

    def ricochet(self, current_target_id, all_enemies):
        """
        彈射邏輯：擊中後尋找最近的另一個敵人轉向
        """
        if self.b_type != "bounce" or self.bounce_left <= 0:
            return False # 消失

        self.damage *= self.bounce_damage_mult
        self.bounce_left -= 1
        self.ignore_list.append(current_target_id)

        # 尋找最近且未打過的敵人
        closest_enemy = None
        min_dist = 500 # 搜索半徑
        
        for eid, enemy in all_enemies.items():
            if eid in self.ignore_list: continue
            dist = get_distance(self.x, self.y, enemy.x, enemy.y)
            if dist < min_dist:
                min_dist = dist
                closest_enemy = enemy
        
        if closest_enemy:
            # 計算指向新敵人的向量
            dx = closest_enemy.x - self.x
            dy = closest_enemy.y - self.y
            length = math.sqrt(dx**2 + dy**2)
            if length > 0:
                self.dx = (dx / length) * self.speed
                self.dy = (dy / length) * self.speed
            return True # 繼續飛行
        else:
            # 沒敵人了，隨機反彈飛走
            self.dx = -self.dx + random.uniform(-2, 2)
            self.dy = -self.dy
            return True

class Player(GameObject):
    def __init__(self, sid, name, skin_id):
        stats = CELL_CONFIG[skin_id]
        super().__init__(random.randint(100, MAP_WIDTH-100), MAP_HEIGHT - 100, stats["radius"]*2)
        self.sid = sid
        self.name = name
        self.skin = skin_id
        self.stats = stats
        
        # 生命系統
        self.lives_count = PLAYER_LIVES
        self.hp = stats["hp"] 
        self.max_hp = stats["hp"]
        
        self.score = 0
        self.charge = 0 # 技能充能
        
        # 狀態
        self.last_hit_time = 0
        self.last_shot_time = 0
        
        # 武器系統
        self.reset_weapon()

    def is_invincible(self):
        return (time.time() - self.last_hit_time) < INVINCIBLE_TIME

    def take_damage(self, amount):
        if self.is_invincible(): return False
        self.hp -= amount
        self.last_hit_time = time.time()
        
        if self.hp <= 0:
            self.lives_count -= 1
            if self.lives_count > 0:
                self.respawn(soft=True)
            else:
                self.respawn(soft=False) # Game Over logic handled by server usually, but here reset
        return True

    def respawn(self, soft=False):
        self.x, self.y = random.randint(100, MAP_WIDTH-100), MAP_HEIGHT - 100
        self.hp = self.max_hp
        self.last_hit_time = time.time() + 1 # 額外無敵時間
        if not soft:
            # 徹底死亡重置
            self.score = int(self.score / 2)
            self.lives_count = PLAYER_LIVES
            self.reset_weapon()
        else:
            # 掉一條命，武器降級或重置
            self.weapon_level = max(0, self.weapon_level - 1)

    def reset_weapon(self):
        self.weapon_type = "default"
        self.weapon_level = 0
        self.weapon_icon = "🔥"

    def apply_item(self, item_type):
        if item_type == "heal":
            self.hp = min(self.max_hp, self.hp + 2)
            return

        base_type = item_type.split('_')[0]
        if self.weapon_type == base_type:
            self.weapon_level = min(2, self.weapon_level + 1)
        else:
            self.weapon_type = base_type
            self.weapon_level = 1
            
        icons = {"spread": "🔱", "ricochet": "⚡", "arc": "🌙", "default": "🔥"}
        self.weapon_icon = icons.get(base_type, "🔥")

    def shoot(self):
        """產生子彈物件列表"""
        current_time = time.time()
        config = self._get_weapon_config()
        
        # 射速限制
        fire_rate = FIRE_COOLDOWN * config.get("fire_rate_mult", 1.0)
        if current_time - self.last_shot_time < fire_rate:
            return []
            
        self.last_shot_time = current_time
        bullets = []
        
        # 根據 Config 的 angles 生成子彈
        angles = config.get("angles", [-90])
        
        # 處理 "random" 角度 (Arc 武器)
        if angles == "random":
             angles = [random.uniform(-110, -70)]

        for angle in angles:
            # Arc 武器可以有隨機擴散
            if isinstance(angle, str): continue 
            
            b = Bullet(
                self.x, self.y - 10, 
                self.sid, "player", 
                config, angle, 
                size=config.get("size", 5)
            )
            bullets.append(b)
            
        return bullets

    def _get_weapon_config(self):
        key = "default"
        if self.weapon_type != "default":
            key = f"{self.weapon_type}_lv{self.weapon_level}"
        # 確保 key 存在，不存在回退 default
        return WEAPON_CONFIG.get(key, WEAPON_CONFIG["default"])

class Enemy(GameObject):
    def __init__(self, type_id):
        stats = VIRUS_CONFIG[type_id]
        # Boss (999) 生成在上方中間，一般怪隨機
        start_x = MAP_WIDTH / 2 if type_id == 999 else random.randint(50, MAP_WIDTH - 50)
        start_y = -100
        
        super().__init__(start_x, start_y, stats["size"])
        self.id = str(uuid.uuid4())
        self.type = type_id
        self.hp = stats["hp"]
        self.max_hp = stats["hp"]
        self.speed = stats["speed"]
        self.score = stats["score"]
        self.prob_drop = stats["drop_rate"]
        
        # 移動 AI 參數
        self.move_timer = 0
        self.patrol_dir = 1 # 1: Right, -1: Left

    def update(self):
        # Boss 行為
        if self.type == 999:
            # 進場
            if self.y < 80:
                self.y += 1
            else:
                # 左右巡邏
                self.x += self.speed * self.patrol_dir
                if self.x > MAP_WIDTH - 150 or self.x < 150:
                    self.patrol_dir *= -1
            return True # Boss 不會自行走出邊界消失

        # 一般怪行為
        self.y += self.speed
        
        # 稍微左右搖擺，增加動感
        self.x += math.sin(self.y * 0.02) * 2

        # 邊界檢查
        if self.y > MAP_HEIGHT + 50:
            return False # 移除
        return True
