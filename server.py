# v3.7.3 server.py (FastAPI Optimized + Rate Limit + Unicast SFX)
import socketio
import uvicorn
from fastapi import FastAPI
import asyncio
import random
import uuid
import math
import time

# --- 設定與參數 ---
# [修改] 加入 'cooldown' (秒)，對應前端的射速限制
CELL_CONFIG = {
    1: {"name": "Soldier", "hp": 5, "speed": 8, "bullet_speed": 7, "damage": 1, "color": "#50fa7b", "cooldown": 0.25},
    2: {"name": "Scout", "hp": 3, "speed": 12, "bullet_speed": 10, "damage": 1, "color": "#8be9fd", "cooldown": 0.15},
    3: {"name": "Tank", "hp": 8, "speed": 5, "bullet_speed": 6, "damage": 2, "color": "#ff5555", "cooldown": 0.4}
}

VIRUS_CONFIG = {
    1: {"hp": 3, "speed": 3, "size": 50, "score": 10, "prob": 0.7,
        "attack": {"mode": "single", "damage": 1, "bullet_speed": 8, "fire_rate": 0.005}},
    2: {"hp": 1, "speed": 7, "size": 25, "score": 25, "prob": 0.2,
        "attack": {"mode": "single", "damage": 1, "bullet_speed": 15, "fire_rate": 0.01}},
    3: {"hp": 15, "speed": 2, "size": 95, "score": 100, "prob": 0.1,
        "attack": {"mode": "double", "damage": 2, "bullet_speed": 6, "fire_rate": 0.02}}
}

# --- 初始化 Server ---
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
app = FastAPI()
sio_app = socketio.ASGIApp(sio, app)

MAP_WIDTH = 600
MAP_HEIGHT = 500
MAX_ENEMIES = 5
INVINCIBLE_TIME = 0.5

# --- 全域狀態 ---
game_vars = {
    "boss_phase": "initial",
    "phase_start_time": 0,
    "elite_kill_count": 0,
    "target_kills": 10
}

game_state = {
    "players": {},
    "enemies": {},
    "bullets": [],
    "skill_objects": [],
    "warning_active": False
}

# --- Helper: 穩定 FPS 的計時器 ---
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

# --- 數據壓縮 ---
def compress_state(state):
    compressed = {
        "players": {}, "enemies": {}, "bullets": [], "skill_objects": [], "w": state["warning_active"]
    }
    for pid, p in state["players"].items():
        compressed["players"][pid] = {
            "x": int(p["x"]), "y": int(p["y"]), "skin": p["skin"], "name": p["name"],
            "hp": max(0, int(p["hp"])), "max_hp": int(p["max_hp"]), "score": int(p["score"]),
            "charge": p["charge"], "hit_accumulated": p["hit_accumulated"], "c": p["stats"]["color"],
            "invincible": (time.time() - p.get("last_hit_time", 0) < INVINCIBLE_TIME)
        }
    for eid, e in state["enemies"].items():
        compressed["enemies"][eid] = {
            "x": int(e["x"]), "y": int(e["y"]), "type": e["type"],
            "size": e["size"], "hp": max(0, int(e["hp"])), "max_hp": int(e["max_hp"])
        }
    for b in state["bullets"]:
        # 這裡只回傳必要的子彈資訊
        compressed["bullets"].append({"x": int(b["x"]), "y": int(b["y"]), "owner": b["owner"]})
    for s in state["skill_objects"]:
        compressed["skill_objects"].append({"x": int(s["x"]), "y": int(s["y"]), "skin": s["skin"]})
    return compressed

# --- 碰撞檢測 ---
def check_collision(obj1, obj2, r1_override=None, r2_override=None):
    r1 = r1_override if r1_override is not None else obj1.get('size', 20) / 2
    r2 = r2_override if r2_override is not None else obj2.get('size', 20) / 2
    cx1, cy1 = obj1['x'] + r1, obj1['y'] + r1
    cx2, cy2 = obj2['x'] + r2, obj2['y'] + r2
    dist_sq = (cx1 - cx2) ** 2 + (cy1 - cy2) ** 2
    radius_sum_sq = (r1 + r2) ** 2
    return dist_sq < (radius_sum_sq * 0.8)

def spawn_boss():
    eid = "THE_BOSS"
    game_state["enemies"][eid] = {
        "x": 150, "y": -300, "type": 999,
        "hp": 500, "max_hp": 500, "speed": 5, "size": 230,
        "score": 1000, "move_timer": 0
    }
    game_vars["boss_phase"] = "boss_active"
    game_state["warning_active"] = False

# --- 主遊戲迴圈 ---
async def game_loop():
    boss_shoot_toggle = 0
    timer = LoopTimer(fps=30) # 30 TPS 對於這類遊戲已足夠，能大幅降低頻寬

    while True:
        curr = time.time()
        
        # [修改] 將 sfx_buffer 分為「廣播」和「單播」
        global_sfx_buffer = []  # 給所有人聽 (Boss出場、警告)
        unicast_sfx_tasks = []  # 只給特定人聽 (擊中回饋)

        def handle_enemy_death_logic(enemy):
            if enemy['type'] == 3:
                if game_vars["boss_phase"] == "initial":
                    game_vars["boss_phase"] = "countdown"
                    game_vars["phase_start_time"] = time.time()
                elif game_vars["boss_phase"] == "collecting":
                    game_vars["elite_kill_count"] += 1
                    if game_vars["elite_kill_count"] >= game_vars["target_kills"]:
                        game_vars["boss_phase"] = "warning"
                        game_vars["phase_start_time"] = time.time()
                        game_state["warning_active"] = True
                        global_sfx_buffer.append({'type': 'boss_coming'})

            if enemy['type'] == 999:
                game_vars["boss_phase"] = "collecting"
                game_vars["elite_kill_count"] = 0
                game_state["warning_active"] = False

        # --- 魔王狀態機 ---
        if game_vars["boss_phase"] == "countdown":
            if curr - game_vars["phase_start_time"] > 25:
                game_vars["boss_phase"] = "warning"
                game_vars["phase_start_time"] = curr
                game_state["warning_active"] = True
                global_sfx_buffer.append({'type': 'boss_coming'})

        elif game_vars["boss_phase"] == "warning":
            if curr - game_vars["phase_start_time"] > 5:
                spawn_boss()
                global_sfx_buffer.append({'type': 'boss_coming'})

        # --- 敵人生成 ---
        if len(game_state["enemies"]) < MAX_ENEMIES and game_vars["boss_phase"] != "boss_active":
            eid = str(uuid.uuid4())
            rand_val = random.random()
            if rand_val < VIRUS_CONFIG[3]["prob"]: v_type = 3
            elif rand_val < VIRUS_CONFIG[3]["prob"] + VIRUS_CONFIG[2]["prob"]: v_type = 2
            else: v_type = 1
            stats = VIRUS_CONFIG[v_type]
            game_state["enemies"][eid] = {
                "x": random.randint(0, MAP_WIDTH - stats["size"]),
                "y": random.randint(-100, 0), "type": v_type,
                "hp": stats["hp"], "max_hp": stats["hp"],
                "speed": stats["speed"], "size": stats["size"],
                "score": stats["score"], "move_timer": 0
            }

        # --- 技能邏輯 ---
        active_skills = []
        for obj in game_state["skill_objects"]:
            if curr - obj["start_time"] > obj["duration"]: continue
            angle = (curr * 3) + obj["angle_offset"]
            if obj["owner_id"] in game_state["players"]:
                owner = game_state["players"][obj["owner_id"]]
                obj["x"] = owner["x"] + math.cos(angle) * 50
                obj["y"] = owner["y"] + math.sin(angle) * 50

                for eid, enemy in list(game_state["enemies"].items()):
                    if check_collision(obj, enemy):
                        enemy["hp"] -= obj["damage"]
                        obj["durability"] -= 1
                        
                        # 技能擊中音效可以考慮廣播，因為很帥且不頻繁
                        global_sfx_buffer.append({'type': 'boss_hitted' if enemy["type"] == 999 else 'enemy_hitted'})

                        if enemy["hp"] <= 0:
                            handle_enemy_death_logic(enemy)
                            if obj["owner_id"] in game_state["players"]:
                                p = game_state["players"][obj["owner_id"]]
                                p["score"] += enemy["score"]
                                p["hit_accumulated"] += 1
                                if p["hit_accumulated"] >= 20:
                                    p["hit_accumulated"] = 0
                                    p["charge"] = min(3, p["charge"] + 1)
                            if eid in game_state["enemies"]: game_state["enemies"].pop(eid)
                        break
            if obj["durability"] > 0: active_skills.append(obj)
        game_state["skill_objects"] = active_skills

        # --- 子彈邏輯 ---
        active_bullets = []
        for b in game_state["bullets"]:
            b['x'] += b['dx']
            b['y'] += b['dy']

            if not (-50 <= b['x'] <= MAP_WIDTH + 50 and -50 <= b['y'] <= MAP_HEIGHT + 50):
                continue

            hit = False
            # 玩家打怪
            if b['owner'] not in ['enemy', 'boss']:
                for eid, enemy in list(game_state["enemies"].items()):
                    if check_collision(b, enemy, r1_override=5):
                        enemy['hp'] -= b.get('damage', 1)
                        hit = True

                        # [重點優化] 擊中音效改為 Unicast (只傳給擁有者)
                        # 這樣不會讓所有人都收到 "Hit" 封包，大幅降低延遲
                        if b['owner'] in game_state["players"]:
                            sfx_type = 'boss_hitted' if enemy['type'] == 999 else 'enemy_hitted'
                            # 建立一個非同步發送任務
                            unicast_sfx_tasks.append(sio.emit('sfx', {'type': sfx_type}, to=b['owner']))

                            p = game_state["players"][b['owner']]
                            p["hit_accumulated"] += 1
                            if p["hit_accumulated"] >= 20:
                                p["hit_accumulated"] = 0
                                p["charge"] = min(3, p["charge"] + 1)

                        if enemy['hp'] <= 0:
                            handle_enemy_death_logic(enemy)
                            if b['owner'] in game_state["players"]:
                                game_state["players"][b['owner']]['score'] += enemy['score']
                            if eid in game_state["enemies"]: game_state["enemies"].pop(eid)
                        break

            # 怪物打玩家
            else:
                for pid, player in list(game_state["players"].items()):
                    if (curr - player.get('last_hit_time', 0)) < INVINCIBLE_TIME:
                        continue 

                    if check_collision(b, player, r1_override=b.get('size', 5) / 2, r2_override=15):
                        player['hp'] -= b.get('damage', 1)
                        player['last_hit_time'] = curr
                        # 受傷音效還是需要讓該玩家知道
                        unicast_sfx_tasks.append(sio.emit('sfx', {'type': 'character_hitted'}, to=pid))
                        hit = True
                        if player['hp'] <= 0:
                            player['x'], player['y'] = random.randint(100, 500), 400
                            player['hp'] = player['max_hp']
                            player['score'] = int(player['score'] / 2)
                            player['charge'] = 0
                            player['hit_accumulated'] = 0
                        break

            if not hit: active_bullets.append(b)
        game_state["bullets"] = active_bullets

        # --- AI 移動與攻擊 ---
        for eid, enemy in list(game_state["enemies"].items()):
            # Boss
            if enemy['type'] == 999:
                enemy['move_timer'] += 1
                if enemy['move_timer'] > 60:
                    enemy['dx'] = random.choice([-2, -1, 0, 1, 2])
                    enemy['dy'] = random.choice([-1, 0, 1])
                    enemy['move_timer'] = 0
                enemy['x'] = max(0, min(MAP_WIDTH - enemy['size'], enemy['x'] + enemy.get('dx', 0)))
                enemy['y'] = max(0, min(MAP_HEIGHT - enemy['size'], enemy['y'] + enemy.get('dy', 0)))

                for pid, player in game_state["players"].items():
                    if (curr - player.get('last_hit_time', 0)) < INVINCIBLE_TIME: continue
                    if check_collision(player, enemy, r1_override=15):
                        if random.random() < 0.2:
                            player['hp'] -= 1
                            player['last_hit_time'] = curr
                            unicast_sfx_tasks.append(sio.emit('sfx', {'type': 'character_hitted'}, to=pid))
                            if player['hp'] <= 0:
                                player['x'], player['y'] = random.randint(100, 500), 400
                                player['hp'] = player['max_hp']
                                player['score'] = int(player['score'] / 2)
                                player['charge'] = 0
                                player['hit_accumulated'] = 0

                is_enraged = (enemy['hp'] < enemy['max_hp'] * 0.5)
                fire_rate = 0.05 if is_enraged else 0.03
                if random.random() < fire_rate:
                    cx, cy = enemy['x'] + enemy['size'] / 2, enemy['y'] + enemy['size'] / 2
                    configs = [(0, 10), (0, -10), (10, 0), (-10, 0)] if is_enraged else (
                        [(0, 10), (0, -10)] if (boss_shoot_toggle := boss_shoot_toggle + 1) % 2 == 0 else [(10, 0), (-10, 0)])
                    for dx, dy in configs:
                        game_state["bullets"].append({
                            "x": cx, "y": cy, "dx": dx, "dy": dy,
                            "owner": "boss", "damage": 1, "size": 10
                        })
                    global_sfx_buffer.append({'type': 'boss_shot'})

            # Normal Enemy
            else:
                enemy['y'] += enemy['speed'] * 0.5
                enemy['move_timer'] += 1
                if enemy['move_timer'] > 30:
                    enemy['x'] += random.choice([-20, 20, 0])
                    enemy['move_timer'] = 0
                enemy['x'] = max(0, min(MAP_WIDTH - enemy['size'], enemy['x']))
                if enemy['y'] > MAP_HEIGHT: enemy['y'] = -50

                for pid, player in game_state["players"].items():
                    if (curr - player.get('last_hit_time', 0)) < INVINCIBLE_TIME: continue
                    if check_collision(player, enemy, r1_override=15):
                        if random.random() < 0.2:
                            player['hp'] -= 1
                            player['last_hit_time'] = curr
                            unicast_sfx_tasks.append(sio.emit('sfx', {'type': 'character_hitted'}, to=pid))
                            if player['hp'] <= 0:
                                player['x'], player['y'] = random.randint(100, 500), 400
                                player['hp'] = player['max_hp']
                                player['score'] = int(player['score'] / 2)
                                player['charge'] = 0
                                player['hit_accumulated'] = 0

                atk_stats = VIRUS_CONFIG[enemy['type']]['attack']
                if random.random() < atk_stats['fire_rate']:
                    center_x = enemy['x'] + enemy['size'] / 2
                    bottom_y = enemy['y'] + enemy['size']
                    bullets_to_spawn = []
                    if atk_stats['mode'] == 'double':
                        bullets_to_spawn.append({"x": center_x - 15, "y": bottom_y})
                        bullets_to_spawn.append({"x": center_x + 15, "y": bottom_y})
                    else:
                        bullets_to_spawn.append({"x": center_x, "y": bottom_y})

                    for b_pos in bullets_to_spawn:
                        game_state["bullets"].append({
                            "x": b_pos['x'], "y": b_pos['y'], "dx": 0, "dy": atk_stats['bullet_speed'],
                            "owner": "enemy", "damage": atk_stats['damage'],
                            "size": 6 if atk_stats['damage'] > 1 else 5
                        })
                    # 敵人射擊頻率很高，如果會卡頓，可以註解掉下面這行
                    # global_sfx_buffer.append({'type': 'enemy_nor_shot'}) 

        # --- 廣播與發送 ---
        emit_tasks = [sio.emit('state_update', compress_state(game_state))]
        
        # 處理廣播 SFX
        if global_sfx_buffer:
            unique_sfx = list({v['type']: v for v in global_sfx_buffer}.values())
            for sfx in unique_sfx:
                emit_tasks.append(sio.emit('sfx', sfx))
        
        # 合併 Unicast SFX 任務
        emit_tasks.extend(unicast_sfx_tasks)

        await asyncio.gather(*emit_tasks)
        await timer.tick()

# --- 事件處理 ---
@app.on_event("startup")
async def startup_event(): asyncio.create_task(game_loop())

@sio.event
async def join_game(sid, data):
    name = data.get("name", "Cell")[:8]
    skin_type = random.randint(1, 3)
    game_state["players"][sid] = {
        "x": random.randint(100, 500), "y": 400, "name": name, "skin": skin_type,
        "stats": CELL_CONFIG[skin_type], 
        "hp": CELL_CONFIG[skin_type]["hp"], 
        "max_hp": CELL_CONFIG[skin_type]["hp"],
        "score": 0, "charge": 0, "hit_accumulated": 0, "last_skill_time": 0,
        "last_hit_time": 0,
        "last_shot_time": 0 # [新增] 初始化射擊時間
    }

@sio.event
async def disconnect(sid):
    if sid in game_state["players"]: del game_state["players"][sid]

@sio.event
async def move(sid, data):
    if sid in game_state["players"]:
        p = game_state["players"][sid]
        p['x'] = max(0, min(MAP_WIDTH - 30, p['x'] + data.get('dx', 0) * p['stats']['speed']))
        p['y'] = max(0, min(MAP_HEIGHT - 30, p['y'] + data.get('dy', 0) * p['stats']['speed']))

@sio.event
async def shoot(sid):
    if sid in game_state["players"]:
        p = game_state["players"][sid]
        curr = time.time()
        
        # [重點優化] Server 端射速限制
        # 如果請求間隔小於 cooldown (設定檔內的秒數)，直接無視請求
        if curr - p.get("last_shot_time", 0) < p["stats"]["cooldown"]:
            return

        p["last_shot_time"] = curr
        
        # 生成子彈
        game_state["bullets"].append({
            "x": p['x'] + 15, "y": p['y'], "dx": 0, "dy": -p['stats']['bullet_speed'],
            "owner": sid, "damage": p['stats']['damage'], "size": 5
        })
        # 注意：我們已經移除 emit 'character_nor_shot'，解決回音問題

@sio.event
async def use_skill(sid):
    if sid in game_state["players"]:
        p = game_state["players"][sid]
        curr = time.time()
        if p["charge"] >= 1 and (curr - p["last_skill_time"] > 2):
            p["charge"] -= 1
            p["last_skill_time"] = curr
            game_state["skill_objects"].append({
                "owner_id": sid, "x": p["x"], "y": p["y"], "size": 30, "damage": 1,
                "durability": 10, "duration": 10, "start_time": curr, "angle_offset": 0, "skin": p["skin"]
            })
            # 技能音效比較少見，可以廣播
            await sio.emit('sfx', {'type': 'skill_slime'})

if __name__ == "__main__":
    uvicorn.run(socketio.ASGIApp(sio, app), host="0.0.0.0", port=8000)
