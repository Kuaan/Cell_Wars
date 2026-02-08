# <<<<<<<<<<<<<<<<<<<<<<<< 5.1 server.py
import socketio
import uvicorn
from fastapi import FastAPI
import asyncio
import random
import time
import math
import uuid

# 假設 server_config 存在，若無請自行定義或註解
# from server_config import *
# 為了讓程式能跑，這裡補上預設 config (若你有 server_config.py 可刪除這段)
MAP_WIDTH = 2000
MAP_HEIGHT = 2000
PLAYER_LIVES = 3
INVINCIBLE_TIME = 3
MAX_ENEMIES = 50
FIRE_COOLDOWN = 0.5
WALL_CONFIG = {"width": 100, "height": 20, "hp": 50, "cooldown": 10, "duration": 20}
CELL_CONFIG = {
    1: {"hp": 10, "color": "red", "speed": 5},
    2: {"hp": 10, "color": "green", "speed": 6},
    3: {"hp": 10, "color": "blue", "speed": 4}
}
WEAPON_CONFIG = {
    "default": {"damage": 1, "speed": 10, "size": 5, "angles": [-90], "type": "linear"},
    "spread_lv1": {"damage": 1, "speed": 10, "size": 5, "angles": [-100, -80], "type": "linear"},
    "spread_lv2": {"damage": 1, "speed": 10, "size": 5, "angles": [-110, -90, -70], "type": "linear"},
}
VIRUS_CONFIG = {
    1: {"size": 30, "hp": 2, "speed": 2, "score": 10, "drop_rate": 0.1, "attack": {"fire_rate": 0.01, "damage": 1, "bullet_speed": 5, "mode": "single"}},
    2: {"size": 40, "hp": 5, "speed": 1.5, "score": 20, "drop_rate": 0.2, "attack": {"fire_rate": 0.02, "damage": 2, "bullet_speed": 6, "mode": "double"}},
    3: {"size": 50, "hp": 10, "speed": 1, "score": 50, "drop_rate": 0.3, "attack": {"fire_rate": 0.03, "damage": 3, "bullet_speed": 7, "mode": "single"}},
    999: {"size": 100, "hp": 500, "speed": 1, "score": 1000, "drop_rate": 1.0, "kill_bonus": 5000, "attack": {"fire_rate": 0.1, "damage": 5, "bullet_speed": 8, "mode": "double"}}
}

def check_collision(obj1, obj2, r1_override=None, r2_override=None):
    # 支援字典或物件屬性存取
    x1 = obj1.x if hasattr(obj1, 'x') else obj1['x']
    y1 = obj1.y if hasattr(obj1, 'y') else obj1['y']
    size1 = obj1.size if hasattr(obj1, 'size') else obj1.get('size', 20)
    
    x2 = obj2.x if hasattr(obj2, 'x') else obj2['x']
    y2 = obj2.y if hasattr(obj2, 'y') else obj2['y']
    size2 = obj2.size if hasattr(obj2, 'size') else obj2.get('size', 20)

    r1 = r1_override if r1_override is not None else size1 / 2
    r2 = r2_override if r2_override is not None else size2 / 2

    cx1, cy1 = x1 + r1, y1 + r1
    cx2, cy2 = x2 + r2, y2 + r2

    dist_sq = (cx1 - cx2) ** 2 + (cy1 - cy2) ** 2
    radius_sum_sq = (r1 + r2) ** 2
    return dist_sq < (radius_sum_sq * 0.8)

def check_rect_circle_collision(rect_obj, circle_obj, circle_r_override=None):
    """矩形(Wall) 與 圓形(Player/Enemy/Bullet) 的碰撞檢測"""
    rx = rect_obj.x
    ry = rect_obj.y
    rw = rect_obj.width
    rh = rect_obj.height
    
    cx = circle_obj.x if hasattr(circle_obj, 'x') else circle_obj['x']
    cy = circle_obj.y if hasattr(circle_obj, 'y') else circle_obj['y']
    size = circle_obj.size if hasattr(circle_obj, 'size') else circle_obj.get('size', 20)
    radius = circle_r_override if circle_r_override is not None else size / 2

    # 尋找矩形上距離圓心最近的點
    closest_x = max(rx, min(cx, rx + rw))
    closest_y = max(ry, min(cy, ry + rh))

    # 計算距離
    distance_x = cx - closest_x
    distance_y = cy - closest_y
    distance_sq = (distance_x ** 2) + (distance_y ** 2)

    return distance_sq < (radius ** 2)

class GameObject:
    def __init__(self, x, y, size):
        self.x = x
        self.y = y
        self.size = size

class Wall(GameObject):
    def __init__(self, x, y, owner_id):
        super().__init__(x, y, 0) # Size 對矩形沒用，設 0
        self.width = WALL_CONFIG["width"]
        self.height = WALL_CONFIG["height"]
        self.hp = WALL_CONFIG["hp"]
        self.max_hp = WALL_CONFIG["hp"]
        self.owner_id = owner_id
        self.created_at = time.time()
        self.id = str(uuid.uuid4())

def get_distance(obj1, obj2):
    x1 = obj1.x if hasattr(obj1, 'x') else obj1['x']
    y1 = obj1.y if hasattr(obj1, 'y') else obj1['y']
    x2 = obj2.x if hasattr(obj2, 'x') else obj2['x']
    y2 = obj2.y if hasattr(obj2, 'y') else obj2['y']
    return math.sqrt((x1-x2)**2 + (y1-y2)**2)

def compress_state(state):
    compressed = {
        "players": {}, "enemies": {}, "bullets": [], 
        "items": [], "skill_objects": [], "walls": [], "w": state["warning_active"]
    }
    
    for pid, p in state["players"].items():
        # 計算牆壁 CD 剩餘時間 (用於前端顯示)
        wall_cd = 0
        if p.active_wall_id is None:
            time_passed = time.time() - p.wall_destroyed_time
            wall_cd = max(0, WALL_CONFIG["cooldown"] - time_passed)
            
        compressed["players"][pid] = {
            "x": int(p.x), "y": int(p.y), "skin": p.skin, "name": p.name,
            "hp": max(0, int(p.hp)), "max_hp": int(p.max_hp), "score": int(p.score),
            "charge": p.charge, "c": p.color,
            "invincible": p.is_invincible(),
            "w_icon": p.weapon_icon,
            "w_cd": int(wall_cd) # 傳送 CD 秒數
        }
    
    for eid, e in state["enemies"].items():
        compressed["enemies"][eid] = {
            "x": int(e.x), "y": int(e.y), "type": e.type,
            "size": e.size, "hp": max(0, int(e.hp)), "max_hp": int(e.max_hp)
        }
        
    for b in state["bullets"]:
        compressed["bullets"].append({
            "x": int(b.x), "y": int(b.y), "owner": b.owner_type, 
            "c": getattr(b, 'color', None), "s": int(b.size)
        })
        
    for i in state["items"]:
        compressed["items"].append({
            "x": int(i.x), "y": int(i.y), "type": i.item_type
        })

    for s in state["skill_objects"]:
        compressed["skill_objects"].append({"x": int(s["x"]), "y": int(s["y"]), "skin": s["skin"]})

    # 新增牆壁數據
    for w in state["walls"]:
        compressed["walls"].append({
            "x": int(w.x), "y": int(w.y), "w": w.width, "h": w.height, 
            "hp": w.hp, "max_hp": w.max_hp
        })

    return compressed

class Item(GameObject):
    def __init__(self, x, y, item_type):
        super().__init__(x, y, 20) # 膠囊大小
        self.id = str(uuid.uuid4())
        self.item_type = item_type # 'spread', 'ricochet', 'arc', 'heal'
        self.dy = 2 # 道具緩慢下落
        
    def update(self):
        self.y += self.dy
        return -50 <= self.y <= MAP_HEIGHT + 50

class Bullet(GameObject):
    def __init__(self, x, y, owner_id, owner_type, config, angle_deg=None):
        size = config.get("size", 5)
        super().__init__(x, y, size)
        self.owner_id = owner_id
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
        self.bounce_left = config.get("bounce", 0)
        self.bounce_damage_mult = config.get("bounce_damage", 0.3)
        self.range_limit = config.get("range", 9999)
        self.dist_traveled = 0
        self.ignore_list = [] # 彈射時避免重複打同一隻
        
        # 弧射參數
        if self.b_type == "arc":
            self.arc_angle = 0
            self.curve_dir = random.choice([-1, 1])

    def update(self):
        if self.b_type == "arc":
            # 弧形運動：在原向量基礎上疊加切線運動
            self.x += self.dx + (math.cos(time.time() * 5) * 5 * self.curve_dir)
            self.y += self.dy
        else:
            self.x += self.dx
            self.y += self.dy
            
        self.dist_traveled += self.speed
        
        # 邊界反彈 (彈射屬性)
        if self.b_type == "bounce" and self.bounce_left > 0:
            hit_wall = False
            
            # X 軸邊界檢查
            if self.x <= 0:
                self.x = 0             # 強制推回邊界內 (防黏牆)
                self.dx *= -1          # 反轉 X 速度
                hit_wall = True
            elif self.x >= MAP_WIDTH:
                self.x = MAP_WIDTH     # 強制推回邊界內
                self.dx *= -1
                hit_wall = True
            
            # Y 軸邊界檢查 (修正：補上 MAP_HEIGHT 判定)
            if self.y <= 0:
                self.y = 0             # 強制推回
                self.dy *= -1          # 反轉 Y 速度
                hit_wall = True
            elif self.y >= MAP_HEIGHT: # 新增：底部邊界判定
                self.y = MAP_HEIGHT    # 強制推回
                self.dy *= -1
                hit_wall = True
            
            if hit_wall:
                self.bounce_left -= 1
                return True # 成功反彈，保持存活
                
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
            if target:
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
        
        # 狀態
        self.last_hit_time = 0
        self.last_shot_time = 0
        self.last_skill_time = 0
        
        # 牆壁機制
        self.wall_destroyed_time = 0 # 記錄牆壁消失的時間，用於計算 CD
        self.active_wall_id = None   # 當前存在的牆壁 ID
        
        # 武器狀態
        self.weapon_level = 0
        self.weapon_type = "default"
        self.weapon_icon = "🔥"

    def is_invincible(self):
        return (time.time() - self.last_hit_time) < INVINCIBLE_TIME

    def take_damage(self, amount):
        if self.is_invincible(): return False
        self.hp -= amount
        self.last_hit_time = time.time()
        
        # 死亡判定 (扣命模擬)
        unit_hp = self.stats["hp"]
        current_lives = math.ceil(self.hp / unit_hp)
        
        if self.hp <= 0:
            self.respawn()
        elif current_lives < self.lives_count:
             # 掉了一條命但還沒死透，重置武器
             self.reset_weapon()
             self.lives_count = current_lives
        return True

    def respawn(self):
        self.x, self.y = random.randint(100, 500), 400
        self.hp = self.max_hp
        self.lives_count = PLAYER_LIVES
        self.score = int(self.score / 2)
        self.charge = 0
        self.reset_weapon() # 重生時不重置牆壁 CD，保持戰略性

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

sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
app = FastAPI()
sio_app = socketio.ASGIApp(sio, app)

# --- 全域狀態 ---
game_vars = {
    "boss_phase": "initial", # 初始狀態
    "phase_start_time": 0,
    "elite_kill_count": 0,
    "target_kills": 5,        # 測試用設 5，正式可改回 10
    "boss_score_threshold": 500 # 分數達到 500 啟動第一次魔王
}

# 使用物件管理 State
class GameState:
    def __init__(self):
        self.players = {}
        self.enemies = {}
        self.bullets = []
        self.items = []
        self.skill_objects = []
        self.walls = []  # 新增
        self.warning_active = False

gs = GameState()

class LoopTimer:
    def __init__(self, fps):
        self.frame_duration = 1.0 / fps
        self.next_tick = time.time()
    async def tick(self):
        now = time.time()
        sleep_time = self.next_tick - now
        if sleep_time > 0:
            await asyncio.sleep(sleep_time)
            self.next_tick += self.frame_duration
        else:
            self.next_tick = now + self.frame_duration

def spawn_boss():
    eid = "THE_BOSS"
    boss = Enemy(999)
    boss.x, boss.y = 150, -300
    gs.enemies[eid] = boss
    game_vars["boss_phase"] = "boss_active"
    gs.warning_active = False

def spawn_item(x, y, forced_type=None):
    types = ["spread", "ricochet", "arc"]
    itype = forced_type if forced_type else random.choice(types)
    gs.items.append(Item(x, y, itype))

# --- 主遊戲迴圈 ---
async def game_loop():
    timer = LoopTimer(fps=30)
    boss_shoot_toggle = 0
    
    while True:
        curr = time.time()
        sfx_buffer = []
        active_skills = []
        for obj in gs.skill_objects:
             if curr - obj["start_time"] > obj["duration"]: continue
             active_skills.append(obj)
        gs.skill_objects = active_skills

        # --- 新增：牆壁更新邏輯 (放在 敵人生成 之前) ---
        active_walls = []
        for w in gs.walls:
            # 檢查時間是否過期
            if curr - w.created_at > WALL_CONFIG["duration"]:
                # 時間到消失，設定 owner 的 CD 開始時間
                if w.owner_id in gs.players:
                    gs.players[w.owner_id].active_wall_id = None
                    gs.players[w.owner_id].wall_destroyed_time = curr
                continue # 移除
                
            # 檢查血量
            if w.hp <= 0:
                if w.owner_id in gs.players:
                    gs.players[w.owner_id].active_wall_id = None
                    gs.players[w.owner_id].wall_destroyed_time = curr
                continue # 移除
                
            active_walls.append(w)
        gs.walls = active_walls

        # 2. 敵人生成與 Boss 狀態機
        # 取得當前最高分
        max_score = max([p.score for p in gs.players.values()] or [0])

        # --- 狀態轉換邏輯 ---條件 A: 分數達標 OR 條件 B: 已經殺了一些小怪 (這裡用分數判定)
        if game_vars["boss_phase"] == "initial":
            if max_score >= game_vars["boss_score_threshold"]:
                game_vars["boss_phase"] = "countdown"
                game_vars["phase_start_time"] = curr

        elif game_vars["boss_phase"] == "countdown":
            if curr - game_vars["phase_start_time"] > 25:  # 倒數 25 秒準備進入警告
                game_vars["boss_phase"] = "warning"
                game_vars["phase_start_time"] = curr
                gs.warning_active = True
                sfx_buffer.append({'type': 'boss_coming'})

        elif game_vars["boss_phase"] == "warning":
            if curr - game_vars["phase_start_time"] > 5: # 警告 5 秒後正式出生
                spawn_boss()
                sfx_buffer.append({'type': 'boss_coming'})

        # --- 敵人生成控制 ---只有在非 Boss 戰期間才生成普通小怪
        if len(gs.enemies) < MAX_ENEMIES and game_vars["boss_phase"] != "boss_active":
            rand_val = random.random()
            # 根據狀態調整精英怪出現機率
            v_type = 3 if rand_val < 0.15 else (2 if rand_val < 0.4 else 1)
            enemy = Enemy(v_type)
            gs.enemies[enemy.id] = enemy

        # 3. 道具移動
        gs.items = [i for i in gs.items if i.update()]
        # 玩家吃道具
        for pid, player in gs.players.items():
            for item in gs.items[:]:
                if check_collision(player, item):
                    player.apply_item(item.item_type)
                    gs.items.remove(item)
                    sfx_buffer.append({'type': 'powerup'}) # 假設前端有這音效

        # 4. 子彈移動與碰撞 
        active_bullets = []
        for b in gs.bullets:
            still_alive = b.update()
            if not still_alive: continue
            bullet_removed = False
            # --- 新增：子彈打牆壁 ---
            for w in gs.walls:
                if check_rect_circle_collision(w, b):
                    bullet_removed = True
                    # 只有 "非玩家" (即敵人/Boss) 的子彈會傷害牆壁
                    if b.owner_type != 'player':
                        w.hp -= b.damage
                        sfx_buffer.append({'type': 'wall_hit'}) # 需在前端加音效或忽略
                    # 玩家子彈撞牆直接消失 (不穿透、不傷害)
                    break 
            
            if bullet_removed:
                continue # 子彈撞牆消失，跳過後續判定

            hit = False
            
            # A. 玩家子彈打怪
            if b.owner_type == 'player':
                for eid, enemy in list(gs.enemies.items()):
                    if enemy in b.ignore_list: continue # 彈射忽略

                    if check_collision(b, enemy):
                        enemy.hp -= b.damage
                        hit = True
                        sfx_buffer.append({'type': 'boss_hitted' if enemy.type == 999 else 'enemy_hitted'})
                        
                        # 處理彈射
                        bullet_survives = b.handle_hit(enemy)
                        
                        # 處理玩家充能
                        if b.owner_id in gs.players:
                            p = gs.players[b.owner_id]
                            p.hit_accumulated += 1
                            if p.hit_accumulated >= 20:
                                p.hit_accumulated = 0
                                p.charge = min(3, p.charge + 1)

                        # 怪物死亡
                        if enemy.hp <= 0:
                            if eid in gs.enemies: del gs.enemies[eid]
                            # 掉寶邏輯
                            if random.random() < enemy.prob_drop:
                                spawn_item(enemy.x, enemy.y)
                                
                            # 分數邏輯
                            if b.owner_id in gs.players:
                                gs.players[b.owner_id].score += enemy.score
                                if enemy.type == 999: # Boss Kill
                                    gs.players[b.owner_id].score += VIRUS_CONFIG[999]["kill_bonus"]

                            # Boss 階段邏輯
                            if enemy.type == 3: # Elite
                                if game_vars["boss_phase"] == "collecting":
                                    game_vars["elite_kill_count"] += 1
                                    if game_vars["elite_kill_count"] >= game_vars["target_kills"]:
                                        game_vars["boss_phase"] = "warning"
                                        game_vars["phase_start_time"] = time.time()
                                        gs.warning_active = True
                            elif enemy.type == 999:
                                game_vars["boss_phase"] = "collecting"
                                game_vars["elite_kill_count"] = 0
                                gs.warning_active = False

                        if not bullet_survives: break # 子彈消失

            # B. 怪物子彈打人
            else:
                for pid, player in gs.players.items():
                    if player.is_invincible(): continue
                    
                    if check_collision(b, player, r2_override=15):
                        is_dead = player.take_damage(b.damage)
                        hit = True
                        sfx_buffer.append({'type': 'character_hitted'})
                        if is_dead:
                             # 重生已在 take_damage 處理
                             pass 
                        break

            if not hit or (hit and b.b_type == "bounce" and b.bounce_left >= 0):
                if not (hit and not b.handle_hit(None)): # 如果命中了且不是反彈子彈，就不要加入 active
                    active_bullets.append(b)

        gs.bullets = active_bullets

        # 5. 怪物 AI 與 射擊
        for eid, enemy in list(gs.enemies.items()):
            if enemy.type == 999: # Boss Movement
                enemy.move_timer += 1
                if enemy.move_timer > 60:
                    enemy.dx = random.choice([-2, -1, 0, 1, 2])
                    enemy.dy = random.choice([-1, 0, 1])
                    enemy.move_timer = 0
                    
                # Boss 預判位置
                next_x = max(0, min(MAP_WIDTH - enemy.size, enemy.x + enemy.dx))
                next_y = max(0, min(MAP_HEIGHT - enemy.size, enemy.y + enemy.dy))
                
                # Boss 牆壁碰撞 (簡單處理：撞牆就不動)
                collides_wall = False
                temp_enemy = type('obj', (object,), {'x': next_x, 'y': next_y, 'size': enemy.size})
                for w in gs.walls:
                    if check_rect_circle_collision(w, temp_enemy):
                        collides_wall = True; break
                
                if not collides_wall:
                    enemy.x, enemy.y = next_x, next_y
                
                # Boss Fire
                is_enraged = (enemy.hp < enemy.max_hp * 0.5)
                fire_rate = 0.05 if is_enraged else 0.03
                if random.random() < fire_rate:
                    cx, cy = enemy.x + enemy.size/2, enemy.y + enemy.size/2
                    configs = [(0, 10), (0, -10), (10, 0), (-10, 0)] if is_enraged else (
                        [(0, 10), (0, -10)] if (boss_shoot_toggle := boss_shoot_toggle + 1) % 2 == 0 else [(10, 0), (-10, 0)])
                    
                    for dx, dy in configs:
                        # 這裡 Boss 子彈也可以用 Bullet Class，但為了簡化先手動塞
                        b = Bullet(cx, cy, "boss", "boss", {"damage":1, "speed":0, "size":10})
                        b.dx, b.dy = dx, dy # 覆蓋向量
                        gs.bullets.append(b)
                    sfx_buffer.append({'type': 'boss_shot'})
            
            else:
                # 普通怪物移動 原本: enemy.update() -> 拆解出來加入碰撞
                prev_y = enemy.y
                enemy.y += enemy.speed * 0.5
                enemy.move_timer += 1
                if enemy.move_timer > 30:
                    enemy.x += random.choice([-20, 20, 0])
                    enemy.move_timer = 0
                enemy.x = max(0, min(MAP_WIDTH - enemy.size, enemy.x))
                if enemy.y > MAP_HEIGHT: enemy.y = -50

                # 怪物牆壁碰撞檢查
                for w in gs.walls:
                    if check_rect_circle_collision(w, enemy):
                        # 撞牆回退簡單邏輯
                        enemy.y = prev_y 
                        # 嘗試繞開(簡單AI)：往中間靠
                        if enemy.x < w.x: enemy.x -= 2
                        else: enemy.x += 2
                        break
                
                # ... (怪物撞人與射擊邏輯保持不變) ...
                for pid, player in gs.players.items():
                    if player.is_invincible(): continue
                    if check_collision(player, enemy, r1_override=15):
                        if random.random() < 0.2:
                            player.take_damage(1)
                            sfx_buffer.append({'type': 'character_hitted'})
                
                # 普通怪物射擊 (優化版：瞄準最近玩家)
                atk = VIRUS_CONFIG[enemy.type]['attack']
                if random.random() < atk['fire_rate']:
                    cx, cy = enemy.x + enemy.size/2, enemy.y + enemy.size
                    
                    # 尋找最近的玩家
                    target = None
                    min_dist = 9999
                    for p in gs.players.values():
                        d = get_distance(enemy, p)
                        if d < min_dist:
                            min_dist = d
                            target = p
                    
                    # 計算射擊角度
                    angle_deg = 90 # 預設向下
                    if target:
                        dx = (target.x + 15) - cx
                        dy = (target.y + 15) - cy
                        angle_deg = math.degrees(math.atan2(dy, dx))
                    bullets_pos = [{"x": cx-15, "y": cy}, {"x": cx+15, "y": cy}] if atk['mode'] == 'double' else [{"x": cx, "y": cy}]
                    for pos in bullets_pos:
                        b = Bullet(pos['x'], pos['y'], eid, "enemy", {"damage": atk['damage'], "speed": atk['bullet_speed']}, angle_deg=angle_deg)
                        gs.bullets.append(b)
                        sfx_buffer.append({'type': 'enemy_nor_shot'})

        # 6. 發送狀態
        state_data = compress_state({
            "players": gs.players, "enemies": gs.enemies, "bullets": gs.bullets, 
            "items": gs.items, "skill_objects": gs.skill_objects, "walls": gs.walls, # 傳入 walls
            "warning_active": gs.warning_active
        })
        emit_tasks = [sio.emit('state_update', state_data)]
        
        if sfx_buffer:
            unique_sfx = list({v['type']: v for v in sfx_buffer}.values())
            for sfx in unique_sfx:
                emit_tasks.append(sio.emit('sfx', sfx))

        await asyncio.gather(*emit_tasks)
        await timer.tick()

# --- 事件處理 ---
@app.on_event("startup")
async def startup_event(): asyncio.create_task(game_loop())

@sio.event
async def join_game(sid, data):
    name = data.get("name", "Cell")[:8]
    skin_type = random.randint(1, 3)
    gs.players[sid] = Player(sid, name, skin_type)

@sio.event
async def disconnect(sid):
    if sid in gs.players: del gs.players[sid]

@sio.event
async def move(sid, data):
    if sid in gs.players:
        p = gs.players[sid]
        # 計算預期位置
        next_x = max(0, min(MAP_WIDTH - 30, p.x + data.get('dx', 0) * p.stats['speed']))
        next_y = max(0, min(MAP_HEIGHT - 30, p.y + data.get('dy', 0) * p.stats['speed']))
        
        # 牆壁碰撞檢查
        collides = False
        # 建立一個臨時物件來模擬移動後的位置
        temp_player = type('obj', (object,), {'x': next_x, 'y': next_y, 'size': 30})
        
        for w in gs.walls:
            if check_rect_circle_collision(w, temp_player):
                collides = True
                break
        
        if not collides:
            p.x = next_x
            p.y = next_y
            
@sio.event
async def build_wall(sid):
    if sid in gs.players:
        p = gs.players[sid]
        curr = time.time()
        # 檢查是否已有牆壁
        if p.active_wall_id is not None:
            return # 已經有一道牆了  
        # 檢查冷卻
        time_since_destroyed = curr - p.wall_destroyed_time
        if time_since_destroyed < WALL_CONFIG["cooldown"]:
            return # CD 中
            
        # 生成牆壁 (在玩家當前位置)
        wall = Wall(p.x - 20, p.y - 10, sid) # 稍微偏移讓玩家在牆的一側或中心
        # 確保不出界
        wall.x = max(0, min(MAP_WIDTH - wall.width, wall.x))
        wall.y = max(0, min(MAP_HEIGHT - wall.height, wall.y))
        
        gs.walls.append(wall)
        p.active_wall_id = wall.id
        await sio.emit('sfx', {'type': 'skill_slime'}) # 借用一下技能音效

@sio.event
async def shoot(sid, data=None): # 修改：接收 data 參數
    if sid in gs.players:
        p = gs.players[sid]
        curr = time.time()
        
        # 根據武器類型調整射速
        w_conf = p.get_shoot_config()
        cooldown = FIRE_COOLDOWN / w_conf.get("fire_rate_mult", 1.0)
        
        if curr - p.last_shot_time < cooldown: return
        p.last_shot_time = curr

        # 決定基礎瞄準角度 (若前端有傳來 angle 則使用，否則預設 -90 向上)
        base_angle = -90
        if data and isinstance(data, dict) and 'angle' in data:
            base_angle = data['angle']

        # 產生子彈 (支援散射/特殊發射)
        # 邏輯：將武器設定的固定角度視為「相對角度」，加上玩家目前的瞄準角度
        conf_angles = w_conf["angles"]
        
        if isinstance(conf_angles, list): # 固定角度 (一般/散射)
            # 判斷是否為預設武器(單發)，如果是，直接用瞄準角度
            # 如果是散射(多發)，我們假設 [-20, -90, -160] 這種設定是相對於 "前方(-90)" 的偏移
            # 計算偏移量： config_angle - (-90)
            
            for conf_angle in conf_angles:
                # 簡單化處理：如果只有一發且是 -90，直接用 base_angle
                if len(conf_angles) == 1 and conf_angle == -90:
                    final_angle = base_angle
                else:
                    # 散射邏輯：計算相對偏移。假設 -90 是正前方
                    offset = conf_angle - (-90) 
                    final_angle = base_angle + offset
                
                # 計算發射位置 (稍微往子彈方向偏移一點，避免重疊在身體裡)
                rad = math.radians(final_angle)
                offset_x = math.cos(rad) * 20
                offset_y = math.sin(rad) * 20
                
                b = Bullet(p.x + 15 + offset_x, p.y + 15 + offset_y, sid, "player", w_conf, angle_deg=final_angle)
                gs.bullets.append(b)
                
        elif conf_angles == "random_45_135": # 弧射 (特殊技能)
            # 在瞄準方向左右 45 度內隨機
            angle = base_angle + random.uniform(-45, 45)
            b = Bullet(p.x + 15, p.y, sid, "player", w_conf, angle_deg=angle)
            gs.bullets.append(b)

@sio.event
async def use_skill(sid):
    # 技能邏輯暫時保持原樣，因為需求主要在一般子彈
    if sid in gs.players:
        p = gs.players[sid]
        curr = time.time()
        if p.charge >= 1 and (curr - p.last_skill_time > 2):
            p.charge -= 1
            p.last_skill_time = curr
            gs.skill_objects.append({
                "owner_id": sid, "x": p.x, "y": p.y, "size": 30, "damage": 1,
                "durability": 10, "duration": 10, "start_time": curr, "angle_offset": 0, "skin": p.skin
            })
            await sio.emit('sfx', {'type': 'skill_slime'})

if __name__ == "__main__":
    uvicorn.run(socketio.ASGIApp(sio, app), host="0.0.0.0", port=8000)
