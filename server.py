#<<<<<<<<<<<<<<<<<<<<<<<<5.2.1 server.py
import socketio
import uvicorn
from fastapi import FastAPI
import asyncio
import random
import time
import math
import uuid

from server_config import *

# --- 工具函式優化 ---

def clamp(val, min_v, max_v):
    """限制數值在範圍內"""
    return max(min_v, min(max_v, val))

def check_collision(obj1, obj2, r1_override=None, r2_override=None):
    # 支援字典或物件屬性存取 (邏輯不變，僅排版微調)
    x1 = obj1.x if hasattr(obj1, 'x') else obj1['x']
    y1 = obj1.y if hasattr(obj1, 'y') else obj1['y']
    size1 = obj1.size if hasattr(obj1, 'size') else obj1.get('size', 20)
    
    x2 = obj2.x if hasattr(obj2, 'x') else obj2['x']
    y2 = obj2.y if hasattr(obj2, 'y') else obj2['y']
    size2 = obj2.size if hasattr(obj2, 'size') else obj2.get('size', 20)

    r1 = r1_override if r1_override is not None else size1 / 2
    r2 = r2_override if r2_override is not None else size2 / 2

    dist_sq = (x1 + r1 - (x2 + r2)) ** 2 + (y1 + r1 - (y2 + r2)) ** 2
    radius_sum_sq = (r1 + r2) ** 2
    return dist_sq < (radius_sum_sq * 0.8)

def get_distance(obj1, obj2):
    x1 = obj1.x if hasattr(obj1, 'x') else obj1['x']
    y1 = obj1.y if hasattr(obj1, 'y') else obj1['y']
    x2 = obj2.x if hasattr(obj2, 'x') else obj2['x']
    y2 = obj2.y if hasattr(obj2, 'y') else obj2['y']
    return math.sqrt((x1-x2)**2 + (y1-y2)**2)

def compress_state(state):
    compressed = {
        "players": {}, "enemies": {}, "bullets": [], 
        "items": [], "skill_objects": [], "w": state["warning_active"]
    }
    
    for pid, p in state["players"].items():
        compressed["players"][pid] = {
            "x": int(p.x), "y": int(p.y), "skin": p.skin, "name": p.name,
            "hp": max(0, int(p.hp)), "max_hp": int(p.max_hp), "score": int(p.score),
            "charge": p.charge, "c": p.color,
            "invincible": p.is_invincible(),
            "w_icon": p.weapon_icon,
            "ha": p.hit_accumulated,
            "shield": (time.time() < p.shield_end_time),
            "l_st": p.laser_state,
            "l_t": int(p.laser_timer * 1000),
            "l_a": int(p.laser_angle)
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

    return compressed

class GameObject:
    def __init__(self, x, y, size):
        self.x = x
        self.y = y
        self.size = size

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
        
        angle_rad = math.radians(angle_deg if angle_deg is not None else -90)
        self.dx = math.cos(angle_rad) * self.speed
        self.dy = math.sin(angle_rad) * self.speed
        
        self.bounce_left = config.get("bounce", 0)
        self.bounce_damage_mult = config.get("bounce_damage", 0.3)
        self.range_limit = config.get("range", 9999)
        self.dist_traveled = 0
        self.ignore_list = []
        
        if self.b_type == "arc":
            self.arc_angle = 0
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
            
            # 使用新的 clamp 邏輯雖然可以限制位置，但反彈需要知道撞到哪邊
            # 這裡維持原邏輯，但位置修正部分可以簡化
            if self.x <= 0 or self.x >= MAP_WIDTH:
                self.x = clamp(self.x, 0, MAP_WIDTH)
                self.dx *= -1
                hit_wall = True
            
            if self.y <= 0 or self.y >= MAP_HEIGHT:
                self.y = clamp(self.y, 0, MAP_HEIGHT)
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
            self.ignore_list.append(target)
            
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
        self.shield_end_time = 0

        self.laser_state = 0
        self.laser_timer = 0
        self.laser_angle = 0
        
        self.weapon_level = 0
        self.weapon_type = "default"
        self.weapon_icon = "🌕" 

    def is_invincible(self):
        now = time.time()
        return (now - self.last_hit_time < INVINCIBLE_TIME) or (now < self.shield_end_time)

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
        self.weapon_icon = "🌕"

    def apply_item(self, item_type):
        base_type = item_type.split('_')[0]
        
        if self.weapon_type.startswith(base_type):
            self.weapon_level = min(2, self.weapon_level + 1)
        else:
            self.weapon_type = base_type
            self.weapon_level = 1
            
        icons = {"spread": "🔱", "ricochet": "⚡", "arc": "🫧", "default": "🌕"}
        self.weapon_icon = icons.get(base_type, "🌕")

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
        if self.type == 999: # Boss
            pass 
        else:
            self.y += self.speed * 0.5
            self.move_timer += 1
            if self.move_timer > 30:
                self.x += random.choice([-20, 20, 0])
                self.move_timer = 0
            # 使用 clamp 優化
            self.x = clamp(self.x, 0, MAP_WIDTH - self.size)
            if self.y > MAP_HEIGHT: self.y = -50

sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
app = FastAPI()
sio_app = socketio.ASGIApp(sio, app)

# --- 全域狀態 ---
game_vars = {
    "boss_phase": "initial",
    "phase_start_time": 0,
    "elite_kill_count": 0,
    "target_kills": 5,
    "boss_score_threshold": 500
}

class GameState:
    def __init__(self):
        self.players = {}
        self.enemies = {}
        self.bullets = []
        self.items = []
        self.skill_objects = []
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

# --- 新增：怪物死亡處理函式 (優化核心) ---
def handle_enemy_death(eid, enemy, killer_id):
    """處理怪物死亡的所有邏輯：移除、加分、掉寶、階段轉換"""
    # 1. 移除
    if eid in gs.enemies: 
        del gs.enemies[eid]
    
    # 2. 分數與擊殺判定
    if killer_id in gs.players:
        p = gs.players[killer_id]
        p.score += enemy.score
        if enemy.type == 999: # Boss Kill Bonus
            p.score += VIRUS_CONFIG[999].get("kill_bonus", 0)

    # 3. 掉寶
    if random.random() < enemy.prob_drop:
        spawn_item(enemy.x, enemy.y)

    # 4. 階段轉換邏輯
    if enemy.type == 3: # Elite
        if game_vars["boss_phase"] == "collecting":
            game_vars["elite_kill_count"] += 1
            if game_vars["elite_kill_count"] >= game_vars["target_kills"]:
                game_vars["boss_phase"] = "warning"
                game_vars["phase_start_time"] = time.time()
                gs.warning_active = True
    elif enemy.type == 999: # Boss Died
        game_vars["boss_phase"] = "collecting"
        game_vars["elite_kill_count"] = 0
        gs.warning_active = False

# --- 主遊戲迴圈 ---
async def game_loop():
    timer = LoopTimer(fps=30)
    boss_shoot_toggle = 0
    
    while True:
        curr = time.time()
        sfx_buffer = []
        active_skills = []
        
        # 1. 玩家雷射邏輯
        for pid, p in gs.players.items():
            if p.laser_state == 1:
                if curr - p.laser_timer >= 1.0:
                    p.laser_state = 2
                    p.laser_timer = curr
                    
                    lx, ly = p.x + 15, p.y + 15
                    rad = math.radians(p.laser_angle)
                    dir_x, dir_y = math.cos(rad), math.sin(rad)
                    
                    for eid, enemy in list(gs.enemies.items()):
                        ex, ey = enemy.x + enemy.size/2, enemy.y + enemy.size/2
                        vx, vy = ex - lx, ey - ly
                        proj = vx * dir_x + vy * dir_y
                        
                        if 0 < proj < 800:
                            orth_dist = abs(vx * (-dir_y) + vy * dir_x)
                            if orth_dist < (enemy.size/2 + 10):
                                enemy.hp -= 50
                                sfx_buffer.append({'type': 'boss_hitted' if enemy.type==999 else 'enemy_hitted'})
                                
                                # 使用封裝後的死亡處理
                                if enemy.hp <= 0:
                                    handle_enemy_death(eid, enemy, p.sid)

            elif p.laser_state == 2:
                if curr - p.laser_timer >= 0.3:
                    p.laser_state = 0
                    
        for obj in gs.skill_objects:
             if curr - obj["start_time"] > obj["duration"]: continue
             active_skills.append(obj)
        gs.skill_objects = active_skills

        # 2. 敵人生成與 Boss 狀態機
        max_score = max([p.score for p in gs.players.values()] or [0])

        if game_vars["boss_phase"] == "initial":
            if max_score >= game_vars["boss_score_threshold"]:
                game_vars["boss_phase"] = "countdown"
                game_vars["phase_start_time"] = curr

        elif game_vars["boss_phase"] == "countdown":
            if curr - game_vars["phase_start_time"] > 25:
                game_vars["boss_phase"] = "warning"
                game_vars["phase_start_time"] = curr
                gs.warning_active = True
                sfx_buffer.append({'type': 'boss_coming'})

        elif game_vars["boss_phase"] == "warning":
            if curr - game_vars["phase_start_time"] > 5:
                spawn_boss()
                sfx_buffer.append({'type': 'boss_coming'})

        if len(gs.enemies) < MAX_ENEMIES and game_vars["boss_phase"] != "boss_active":
            rand_val = random.random()
            v_type = 3 if rand_val < 0.15 else (2 if rand_val < 0.4 else 1)
            enemy = Enemy(v_type)
            gs.enemies[enemy.id] = enemy

        # 3. 道具移動
        gs.items = [i for i in gs.items if i.update()]
        for pid, player in gs.players.items():
            for item in gs.items[:]:
                if check_collision(player, item):
                    player.apply_item(item.item_type)
                    gs.items.remove(item)
                    sfx_buffer.append({'type': 'powerup'})

        # 4. 子彈移動與碰撞 
        active_bullets = []
        for b in gs.bullets:
            still_alive = b.update()
            if not still_alive: continue
            hit = False
            
            # A. 玩家子彈打怪
            if b.owner_type == 'player':
                for eid, enemy in list(gs.enemies.items()):
                    if enemy in b.ignore_list: continue

                    if check_collision(b, enemy):
                        enemy.hp -= b.damage
                        hit = True
                        sfx_buffer.append({'type': 'boss_hitted' if enemy.type == 999 else 'enemy_hitted'})
                        
                        bullet_survives = b.handle_hit(enemy)
                        
                        if b.owner_id in gs.players:
                            p = gs.players[b.owner_id]
                            if p.charge < 3:
                                p.hit_accumulated += 1
                                if p.hit_accumulated >= 20:
                                    p.hit_accumulated = 0
                                    p.charge += 1
                            else:
                                p.hit_accumulated = 0

                        # 使用封裝後的死亡處理
                        if enemy.hp <= 0:
                            handle_enemy_death(eid, enemy, b.owner_id)

                        if not bullet_survives: break 

            # B. 怪物子彈打人
            else:
                for pid, player in gs.players.items():
                    if player.is_invincible(): continue
                    
                    if check_collision(b, player, r2_override=15):
                        is_dead = player.take_damage(b.damage)
                        hit = True
                        sfx_buffer.append({'type': 'character_hitted'})
                        break

            if not hit or (hit and b.b_type == "bounce" and b.bounce_left >= 0):
                if not (hit and not b.handle_hit(None)):
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
                
                # 使用 clamp 優化 Boss 移動限制
                enemy.x = clamp(enemy.x + enemy.dx, 0, MAP_WIDTH - enemy.size)
                enemy.y = clamp(enemy.y + enemy.dy, 0, MAP_HEIGHT - enemy.size)
                
                is_enraged = (enemy.hp < enemy.max_hp * 0.5)
                fire_rate = 0.05 if is_enraged else 0.03
                if random.random() < fire_rate:
                    cx, cy = enemy.x + enemy.size/2, enemy.y + enemy.size/2
                    configs = [(0, 10), (0, -10), (10, 0), (-10, 0)] if is_enraged else (
                        [(0, 10), (0, -10)] if (boss_shoot_toggle := boss_shoot_toggle + 1) % 2 == 0 else [(10, 0), (-10, 0)])
                    
                    for dx, dy in configs:
                        b = Bullet(cx, cy, "boss", "boss", {"damage":1, "speed":0, "size":10})
                        b.dx, b.dy = dx, dy
                        gs.bullets.append(b)
                    sfx_buffer.append({'type': 'boss_shot'})
            
            else:
                enemy.update() # 普通怪物移動
                for pid, player in gs.players.items():
                    if player.is_invincible(): continue
                    if check_collision(player, enemy, r1_override=15):
                        if random.random() < 0.2:
                            player.take_damage(1)
                            sfx_buffer.append({'type': 'character_hitted'})
                
                atk = VIRUS_CONFIG[enemy.type]['attack']
                if random.random() < atk['fire_rate']:
                    cx, cy = enemy.x + enemy.size/2, enemy.y + enemy.size
                    
                    target = None
                    min_dist = 9999
                    for p in gs.players.values():
                        d = get_distance(enemy, p)
                        if d < min_dist:
                            min_dist = d
                            target = p
                    
                    angle_deg = 90
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
            "items": gs.items, "skill_objects": gs.skill_objects, "warning_active": gs.warning_active
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
        # 使用 clamp 優化玩家移動限制
        p.x = clamp(p.x + data.get('dx', 0) * p.stats['speed'], 0, MAP_WIDTH - 30)
        p.y = clamp(p.y + data.get('dy', 0) * p.stats['speed'], 0, MAP_HEIGHT - 30)

@sio.event
async def shoot(sid, data=None):
    if sid in gs.players:
        p = gs.players[sid]
        curr = time.time()
        
        w_conf = p.get_shoot_config()
        cooldown = FIRE_COOLDOWN / w_conf.get("fire_rate_mult", 1.0)
        
        if curr - p.last_shot_time < cooldown: return
        p.last_shot_time = curr

        base_angle = -90
        if data and isinstance(data, dict) and 'angle' in data:
            base_angle = data['angle']

        conf_angles = w_conf["angles"]
        
        if isinstance(conf_angles, list):
            for conf_angle in conf_angles:
                if len(conf_angles) == 1 and conf_angle == -90:
                    final_angle = base_angle
                else:
                    offset = conf_angle - (-90) 
                    final_angle = base_angle + offset
                
                rad = math.radians(final_angle)
                offset_x = math.cos(rad) * 20
                offset_y = math.sin(rad) * 20
                
                b = Bullet(p.x + 15 + offset_x, p.y + 15 + offset_y, sid, "player", w_conf, angle_deg=final_angle)
                gs.bullets.append(b)
                
        elif conf_angles == "random_45_135":
            angle = base_angle + random.uniform(-45, 45)
            b = Bullet(p.x + 15, p.y, sid, "player", w_conf, angle_deg=angle)
            gs.bullets.append(b)

@sio.event
async def use_skill(sid):
    if sid in gs.players:
        p = gs.players[sid]
        curr = time.time()
        if p.charge >= 1:
            p.charge -= 1
            p.shield_end_time = curr + 5
            await sio.emit('sfx', {'type': 'skill_slime'})
            
@sio.event
async def use_laser(sid, data):
    if sid in gs.players:
        p = gs.players[sid]
        if p.charge >= 1 and p.laser_state == 0:
            p.charge -= 1
            p.laser_state = 1
            p.laser_timer = time.time()
            p.laser_angle = data.get('angle', -90)
            await sio.emit('sfx', {'type': 'skill_slime'})

if __name__ == "__main__":
    uvicorn.run(socketio.ASGIApp(sio, app), host="0.0.0.0", port=8000)
