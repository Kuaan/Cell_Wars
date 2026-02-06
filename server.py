<<<<<<< HEAD
# 4.1 server.py 
=======
#v430
>>>>>>> cf61c11d6df7b5141882f1c3ab7a2e9f88b1a6d6
import socketio
import uvicorn
from fastapi import FastAPI
import asyncio
import random
import time
import math

# 引入模組
from config import *
from utils import compress_state, check_collision # 假設 utils 沒變，但我們會用到它
from game_objects import Player, Enemy, Bullet, Item, Wall

# --- 初始化 ---
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
app = FastAPI()
sio_app = socketio.ASGIApp(sio, app)

# --- 全域狀態 ---
game_vars = {
<<<<<<< HEAD
    "boss_phase": "initial", # 初始狀態
    "phase_start_time": 0,
    "elite_kill_count": 0,
    "target_kills": 5,        # 測試用設 5，正式可改回 10
    "boss_score_threshold": 500 # 分數達到 500 啟動第一次魔王
=======
    "boss_phase": "initial",
    "phase_start_time": 0,
    "elite_kill_count": 0,
    "target_kills": 5,
    "boss_score_threshold": 500
>>>>>>> cf61c11d6df7b5141882f1c3ab7a2e9f88b1a6d6
}

# 使用物件管理 State
class GameState:
    def __init__(self):
        self.players = {}
        self.enemies = {}
        self.bullets = []
        self.items = []
<<<<<<< HEAD
=======
        self.walls = [] # 新增牆壁清單
>>>>>>> cf61c11d6df7b5141882f1c3ab7a2e9f88b1a6d6
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

# 簡易矩形碰撞檢查 (用於牆壁)
def check_rect_collision(obj, wall):
    # obj 視為圓形，wall 為矩形
    # 這裡做一個簡單的 AABB 檢查
    closest_x = max(wall.x, min(obj.x, wall.x + wall.width))
    closest_y = max(wall.y, min(obj.y, wall.y + wall.height))
    dx = obj.x - closest_x
    dy = obj.y - closest_y
    return (dx*dx + dy*dy) < (obj.size * obj.size)

# 解決碰撞 (把角色推開)
def resolve_wall_collision(obj, wall):
    # 簡單計算推開方向
    cx = wall.x + wall.width / 2
    cy = wall.y + wall.height / 2
    dx = obj.x - cx
    dy = obj.y - cy
    
    # 正規化
    dist = math.sqrt(dx*dx + dy*dy)
    if dist == 0: dist = 1
    
    # 推開一點點
    push_strength = 5
    obj.x += (dx / dist) * push_strength
    obj.y += (dy / dist) * push_strength

# --- 主遊戲迴圈 ---
async def game_loop():
    timer = LoopTimer(fps=30)
    boss_shoot_toggle = 0
    
    while True:
        curr = time.time()
        sfx_buffer = []
<<<<<<< HEAD

        # 1. 玩家/技能 邏輯 (簡化: 這裡省略 Skill Object 的詳細類別化，保留原結構但用新邏輯)
        # (此處為保持代碼長度適中，重點放在道具與射擊重構)
        active_skills = []
        for obj in gs.skill_objects:
             # ... 保留原本技能邏輯，或者也可以移到 game_objects ...
             if curr - obj["start_time"] > obj["duration"]: continue
             # (技能移動與判定邏輯略，建議也封裝)
             active_skills.append(obj)
        gs.skill_objects = active_skills

        # 2. 敵人生成與 Boss 狀態機
        
        # 取得當前最高分
=======

        # 1. 玩家/技能/牆壁 邏輯
        active_skills = []
        for obj in gs.skill_objects:
             if curr - obj["start_time"] > obj["duration"]: continue
             active_skills.append(obj)
        gs.skill_objects = active_skills
        
        # 牆壁邏輯
        active_walls = []
        for w in gs.walls:
            if w.hp <= 0 or w.is_expired():
                # 牆壁消失，設定擁有者的 CD
                if w.owner_id in gs.players:
                    gs.players[w.owner_id].wall_cd_finish_time = curr + WALL_CONFIG["cooldown"]
                continue
            active_walls.append(w)
        gs.walls = active_walls

        # 造牆判定
        for pid, p in gs.players.items():
            if p.is_building_pressed:
                # 檢查 CD
                if curr >= p.wall_cd_finish_time:
                    # 必須正在移動才能「劃出」
                    # 這裡簡化為：按下就生成一個靜態阻擋體
                    # 若要實現「劃出」，通常需要檢查位移量，這裡先做「原地生成」版本
                    # 為了符合"劃出"的感覺，我們讓牆壁長度隨移動方向延伸，或者固定生成
                    
                    # 檢查場上是否已經有該玩家的牆 (假設一次只能蓋一個，或者CD限制)
                    # 這裡依據描述：破壞或消失後開始CD，所以同時只能存在一個
                    my_walls = [w for w in gs.walls if w.owner_id == pid]
                    if not my_walls:
                        # 生成牆壁
                        # 牆壁尺寸：長 2.5倍, 寬 1倍
                        # 預設橫向，若要進階可根據 joystick 角度旋轉，這裡先做正方形或橫條
                        w_w = p.size * WALL_CONFIG["length_mult"]
                        w_h = p.size * WALL_CONFIG["width_mult"]
                        
                        wall = Wall(p.x, p.y, pid, w_w, w_h)
                        gs.walls.append(wall)
                        sfx_buffer.append({'type': 'skill_slime'}) # 借用音效

        # 2. 敵人生成 (略: 與原程式相同)
>>>>>>> cf61c11d6df7b5141882f1c3ab7a2e9f88b1a6d6
        max_score = max([p.score for p in gs.players.values()] or [0])
        if game_vars["boss_phase"] == "initial" and max_score >= game_vars["boss_score_threshold"]:
             game_vars["boss_phase"] = "countdown"; game_vars["phase_start_time"] = curr
        elif game_vars["boss_phase"] == "countdown" and curr - game_vars["phase_start_time"] > 25:
             game_vars["boss_phase"] = "warning"; game_vars["phase_start_time"] = curr; gs.warning_active = True; sfx_buffer.append({'type': 'boss_coming'})
        elif game_vars["boss_phase"] == "warning" and curr - game_vars["phase_start_time"] > 5:
             spawn_boss()
             sfx_buffer.append({'type': 'boss_coming'})

<<<<<<< HEAD
        # --- 狀態轉換邏輯 ---
        if game_vars["boss_phase"] == "initial":
            # 條件 A: 分數達標 OR 條件 B: 已經殺了一些小怪 (這裡用分數判定)
            if max_score >= game_vars["boss_score_threshold"]:
                game_vars["boss_phase"] = "countdown"
                game_vars["phase_start_time"] = curr

        elif game_vars["boss_phase"] == "countdown":
            # 倒數 25 秒準備進入警告
            if curr - game_vars["phase_start_time"] > 25:
                game_vars["boss_phase"] = "warning"
                game_vars["phase_start_time"] = curr
                gs.warning_active = True
                sfx_buffer.append({'type': 'boss_coming'})

        elif game_vars["boss_phase"] == "warning":
            # 警告 5 秒後正式出生
            if curr - game_vars["phase_start_time"] > 5:
                spawn_boss()
                sfx_buffer.append({'type': 'boss_coming'})

        # --- 敵人生成控制 ---
        # 只有在非 Boss 戰期間才生成普通小怪
        if len(gs.enemies) < MAX_ENEMIES and game_vars["boss_phase"] != "boss_active":
            rand_val = random.random()
            # 根據狀態調整精英怪出現機率
=======
        if len(gs.enemies) < MAX_ENEMIES and game_vars["boss_phase"] != "boss_active":
            rand_val = random.random()
>>>>>>> cf61c11d6df7b5141882f1c3ab7a2e9f88b1a6d6
            v_type = 3 if rand_val < 0.15 else (2 if rand_val < 0.4 else 1)
            enemy = Enemy(v_type)
            gs.enemies[enemy.id] = enemy

<<<<<<< HEAD
        # 3. 道具移動
=======
        # 3. 道具移動 (略)
>>>>>>> cf61c11d6df7b5141882f1c3ab7a2e9f88b1a6d6
        gs.items = [i for i in gs.items if i.update()]
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
            
<<<<<<< HEAD
=======
            bullet_destroyed = False
            
            # 檢查子彈撞牆
            for w in gs.walls:
                if check_rect_collision(b, w):
                    if b.owner_type == 'player':
                        # 我方子彈不傷牆，也不穿越 -> 消失 (根據描述 "子彈也不會穿越")
                        bullet_destroyed = True
                    else:
                        # 敵方子彈傷牆
                        w.hp -= b.damage
                        bullet_destroyed = True
                    break # 撞到一個牆就停
            
            if bullet_destroyed: continue

>>>>>>> cf61c11d6df7b5141882f1c3ab7a2e9f88b1a6d6
            hit = False
            # A. 玩家子彈打怪
            if b.owner_type == 'player':
                for eid, enemy in list(gs.enemies.items()):
<<<<<<< HEAD
                    if enemy in b.ignore_list: continue # 彈射忽略

=======
                    if enemy in b.ignore_list: continue
>>>>>>> cf61c11d6df7b5141882f1c3ab7a2e9f88b1a6d6
                    if check_collision(b, enemy):
                        enemy.hp -= b.damage
                        hit = True
                        sfx_buffer.append({'type': 'boss_hitted' if enemy.type == 999 else 'enemy_hitted'})
<<<<<<< HEAD
                        
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

=======
                        if b.handle_hit(enemy): bullet_destroyed = False
                        else: bullet_destroyed = True
                        
                        if b.owner_id in gs.players:
                            p = gs.players[b.owner_id]
                            p.hit_accumulated += 1
                            if p.hit_accumulated >= 20: p.hit_accumulated = 0; p.charge = min(3, p.charge + 1)
                        
                        if enemy.hp <= 0:
                            if eid in gs.enemies: del gs.enemies[eid]
                            if random.random() < enemy.prob_drop: spawn_item(enemy.x, enemy.y)
                            if b.owner_id in gs.players:
                                gs.players[b.owner_id].score += enemy.score
                                if enemy.type == 999: gs.players[b.owner_id].score += VIRUS_CONFIG[999]["kill_bonus"]
                            
                            # Boss logic check (略)
                            if enemy.type == 999:
                                game_vars["boss_phase"] = "collecting"; game_vars["elite_kill_count"] = 0; gs.warning_active = False
                        break
                if bullet_destroyed: continue

>>>>>>> cf61c11d6df7b5141882f1c3ab7a2e9f88b1a6d6
            # B. 怪物子彈打人
            else:
                for pid, player in gs.players.items():
                    if player.is_invincible(): continue
<<<<<<< HEAD
                    
=======
>>>>>>> cf61c11d6df7b5141882f1c3ab7a2e9f88b1a6d6
                    if check_collision(b, player, r2_override=15):
                        is_dead = player.take_damage(b.damage)
                        hit = True
                        sfx_buffer.append({'type': 'character_hitted'})
<<<<<<< HEAD
                        if is_dead:
                             # 重生已在 take_damage 處理
                             pass 
                        break

            if not hit or (hit and b.b_type == "bounce" and b.bounce_left >= 0):
                if not (hit and not b.handle_hit(None)): # 如果命中了且不是反彈子彈，就不要加入 active
                    active_bullets.append(b)
=======
                        bullet_destroyed = True
                        break
                if bullet_destroyed: continue
>>>>>>> cf61c11d6df7b5141882f1c3ab7a2e9f88b1a6d6

            active_bullets.append(b)
        gs.bullets = active_bullets

        # 5. 怪物 AI 與 射擊
        for eid, enemy in list(gs.enemies.items()):
<<<<<<< HEAD
            if enemy.type == 999: # Boss Movement
=======
            # 檢查怪物撞牆
            for w in gs.walls:
                if check_rect_collision(enemy, w):
                    resolve_wall_collision(enemy, w)

            if enemy.type == 999: # Boss
>>>>>>> cf61c11d6df7b5141882f1c3ab7a2e9f88b1a6d6
                enemy.move_timer += 1
                if enemy.move_timer > 60:
                    enemy.dx = random.choice([-2, -1, 0, 1, 2])
                    enemy.dy = random.choice([-1, 0, 1])
                    enemy.move_timer = 0
                enemy.x = max(0, min(MAP_WIDTH - enemy.size, enemy.x + enemy.dx))
                enemy.y = max(0, min(MAP_HEIGHT - enemy.size, enemy.y + enemy.dy))
                
                # Boss Fire
                is_enraged = (enemy.hp < enemy.max_hp * 0.5)
                fire_rate = 0.05 if is_enraged else 0.03
                if random.random() < fire_rate:
                    cx, cy = enemy.x + enemy.size/2, enemy.y + enemy.size/2
<<<<<<< HEAD
                    configs = [(0, 10), (0, -10), (10, 0), (-10, 0)] if is_enraged else (
                        [(0, 10), (0, -10)] if (boss_shoot_toggle := boss_shoot_toggle + 1) % 2 == 0 else [(10, 0), (-10, 0)])
                    
                    for dx, dy in configs:
                        # 這裡 Boss 子彈也可以用 Bullet Class，但為了簡化先手動塞
                        b = Bullet(cx, cy, "boss", "boss", {"damage":1, "speed":0, "size":10})
                        b.dx, b.dy = dx, dy # 覆蓋向量
                        gs.bullets.append(b)
                    sfx_buffer.append({'type': 'boss_shot'})
            
            else:
                enemy.update() # 普通怪物移動
                # 普通怪物撞人
=======
                    # Boss 朝下方亂射
                    angles = [random.uniform(45, 135) for _ in range(4)] if is_enraged else [random.uniform(60, 120)]
                    for ang in angles:
                         b = Bullet(cx, cy, "boss", "boss", {"damage":1, "speed":8, "size":10}, angle_deg=ang)
                         gs.bullets.append(b)
                    sfx_buffer.append({'type': 'boss_shot'})
            
            else:
                enemy.update()
                # 怪物撞人
>>>>>>> cf61c11d6df7b5141882f1c3ab7a2e9f88b1a6d6
                for pid, player in gs.players.items():
                    if player.is_invincible(): continue
                    if check_collision(player, enemy, r1_override=15):
                        if random.random() < 0.2:
                            player.take_damage(1)
                            sfx_buffer.append({'type': 'character_hitted'})
                
<<<<<<< HEAD
                # 普通怪物射擊
=======
                # 怪物射擊：朝下方 180 度隨機 (0度是右, 90下, 180左)
>>>>>>> cf61c11d6df7b5141882f1c3ab7a2e9f88b1a6d6
                atk = VIRUS_CONFIG[enemy.type]['attack']
                if random.random() < atk['fire_rate']:
                    cx, cy = enemy.x + enemy.size/2, enemy.y + enemy.size
                    bullets_pos = [{"x": cx-15, "y": cy}, {"x": cx+15, "y": cy}] if atk['mode'] == 'double' else [{"x": cx, "y": cy}]
<<<<<<< HEAD
                    for pos in bullets_pos:
                        b = Bullet(pos['x'], pos['y'], eid, "enemy", {"damage": atk['damage'], "speed": atk['bullet_speed']})
                        # 敵人子彈向下
                        b.dx, b.dy = 0, atk['bullet_speed']
                        gs.bullets.append(b)

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
=======
                    
                    for pos in bullets_pos:
                        # 隨機角度 0 ~ 180
                        rand_angle = random.uniform(0, 180)
                        b = Bullet(pos['x'], pos['y'], eid, "enemy", {"damage": atk['damage'], "speed": atk['bullet_speed']}, angle_deg=rand_angle)
                        gs.bullets.append(b)

        # 玩家撞牆判定
        for pid, player in gs.players.items():
            for w in gs.walls:
                if check_rect_collision(player, w):
                    resolve_wall_collision(player, w)

        # 6. 發送狀態 (加上 walls)
        state_data = compress_state({
            "players": gs.players, "enemies": gs.enemies, "bullets": gs.bullets, 
            "items": gs.items, "walls": gs.walls, "skill_objects": gs.skill_objects, 
            "warning_active": gs.warning_active
        })
        emit_tasks = [sio.emit('state_update', state_data)]
        if sfx_buffer:
            unique_sfx = list({v['type']: v for v in sfx_buffer}.values())
            for sfx in unique_sfx: emit_tasks.append(sio.emit('sfx', sfx))
>>>>>>> cf61c11d6df7b5141882f1c3ab7a2e9f88b1a6d6

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
<<<<<<< HEAD
=======
        # 簡單移動檢查
>>>>>>> cf61c11d6df7b5141882f1c3ab7a2e9f88b1a6d6
        p.x = max(0, min(MAP_WIDTH - 30, p.x + data.get('dx', 0) * p.stats['speed']))
        p.y = max(0, min(MAP_HEIGHT - 30, p.y + data.get('dy', 0) * p.stats['speed']))

@sio.event
<<<<<<< HEAD
async def shoot(sid):
    if sid in gs.players:
        p = gs.players[sid]
        curr = time.time()
        
        # 根據武器類型調整射速
=======
async def start_build(sid):
    if sid in gs.players: gs.players[sid].is_building_pressed = True

@sio.event
async def stop_build(sid):
    if sid in gs.players: gs.players[sid].is_building_pressed = False

@sio.event
async def shoot(sid, data):
    # data 預期包含 {'angle': degrees}
    if sid in gs.players:
        p = gs.players[sid]
        curr = time.time()
>>>>>>> cf61c11d6df7b5141882f1c3ab7a2e9f88b1a6d6
        w_conf = p.get_shoot_config()
        cooldown = FIRE_COOLDOWN / w_conf.get("fire_rate_mult", 1.0)
        
        if curr - p.last_shot_time < cooldown: return
        p.last_shot_time = curr

<<<<<<< HEAD
        # 產生子彈 (支援散射/特殊發射)
        angles = w_conf["angles"]
        if isinstance(angles, list): # 固定角度 (一般/散射)
            for angle in angles:
                b = Bullet(p.x + 15, p.y, sid, "player", w_conf, angle_deg=angle)
                gs.bullets.append(b)
        elif angles == "random_45_135": # 弧射 (隨機前方)
            angle = random.uniform(-135, -45) # 上方隨機
            b = Bullet(p.x + 15, p.y, sid, "player", w_conf, angle_deg=angle)
            gs.bullets.append(b)

@sio.event
async def use_skill(sid):
    # 技能邏輯暫時保持原樣，因為需求主要在一般子彈
=======
        # 取得前端傳來的搖桿角度 (若沒有則預設 -90 向上)
        base_angle = data.get('angle', -90)
        
        config_angles = w_conf["angles"]
        if isinstance(config_angles, list):
            for rel_angle in config_angles:
                # 這裡將設定檔的「相對角度」加上搖桿的「絕對角度」
                final_angle = base_angle + rel_angle 
                b = Bullet(p.x + 15, p.y, sid, "player", w_conf, angle_deg=final_angle)
                gs.bullets.append(b)
        elif config_angles == "random_forward":
             # 在前方扇形區域隨機
             final_angle = base_angle + random.uniform(-45, 45)
             b = Bullet(p.x + 15, p.y, sid, "player", w_conf, angle_deg=final_angle)
             gs.bullets.append(b)

@sio.event
async def use_skill(sid):
>>>>>>> cf61c11d6df7b5141882f1c3ab7a2e9f88b1a6d6
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
