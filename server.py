import socketio
import uvicorn
from fastapi import FastAPI
import asyncio
import random
import uuid
import math
import time

# --- 獨立物件設定檔 (Configuration) ---

CELL_CONFIG = {
    1: { "name": "Soldier", "hp": 5, "speed": 8,  "bullet_speed": 15, "damage": 1, "color": "#50fa7b" },
    2: { "name": "Scout",   "hp": 3, "speed": 12, "bullet_speed": 20, "damage": 1, "color": "#8be9fd" },
    3: { "name": "Tank",    "hp": 8, "speed": 5,  "bullet_speed": 12, "damage": 2, "color": "#ff5555" }
}

VIRUS_CONFIG = {
    1: { "hp": 3,  "speed": 3, "size": 30, "score": 10,  "prob": 0.7 },
    2: { "hp": 1,  "speed": 7, "size": 25, "score": 25,  "prob": 0.2 },
    3: { "hp": 15, "speed": 2, "size": 50, "score": 100, "prob": 0.1 } # Boss
}

# --- 伺服器初始化 ---
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
app = FastAPI()
sio_app = socketio.ASGIApp(sio, app)

# --- 遊戲常數 ---
MAP_WIDTH = 600
MAP_HEIGHT = 500
MAX_ENEMIES = 5
MAX_PLAYERS = 20

# --- 遊戲狀態 ---
game_state = {
    "players": {},       # 存放玩家數據
    "enemies": {},       # 存放敵人
    "bullets": [],       # 存放子彈
    "skill_objects": []  # 存放技能產生的物件 (如分身)
}

# --- 碰撞檢測 (AABB) ---
def check_collision(rect1, rect2, size1, size2):
    return (rect1['x'] < rect2['x'] + size2 and
            rect1['x'] + size1 > rect2['x'] and
            rect1['y'] < rect2['y'] + size2 and
            rect1['y'] + size1 > rect2['y'])

# --- 核心遊戲迴圈 ---
async def game_loop():
    while True:
        total_score = sum(p['score'] for p in game_state["players"].values())
        current_time = time.time()

        # 1. 敵人生成
        if len(game_state["enemies"]) < MAX_ENEMIES:
            eid = str(uuid.uuid4())
            rand_val = random.random()
            if total_score >= 500 and random.random() < 0.2: v_type = 3
            elif rand_val < 0.3: v_type = 2
            else: v_type = 1
            
            stats = VIRUS_CONFIG[v_type]
            game_state["enemies"][eid] = {
                "x": random.randint(0, MAP_WIDTH - stats["size"]),
                "y": random.randint(-100, 0),
                "type": v_type,
                "hp": stats["hp"],
                "max_hp": stats["hp"],
                "speed": stats["speed"],
                "size": stats["size"],
                "score": stats["score"],
                "move_timer": 0
            }

        # 2. 玩家技能物件邏輯 (分身)
        active_skills = []
        for obj in game_state["skill_objects"]:
            owner = game_state["players"].get(obj["owner_id"])
            if not owner: continue # 主人斷線，技能消失

            # 檢查持續時間
            if current_time - obj["start_time"] > obj["duration"]:
                continue
            
            # 檢查耐久度
            if obj["durability"] <= 0:
                continue

            # 移動邏輯：環繞主人 (Orbit)
            # 簡單計算：維持在主人周圍
            angle = (current_time * 2) + obj["angle_offset"] # 旋轉
            radius = 45 # 距離中心 45px
            obj["x"] = owner["x"] + math.cos(angle) * radius
            obj["y"] = owner["y"] + math.sin(angle) * radius

            # 技能碰撞敵人
            hit = False
            for eid, enemy in list(game_state["enemies"].items()):
                if check_collision(obj, enemy, obj["size"], enemy["size"]):
                    enemy["hp"] -= obj["damage"]
                    obj["durability"] -= 1
                    hit = True
                    if enemy["hp"] <= 0:
                        owner["score"] += enemy["score"]
                        game_state["enemies"].pop(eid)
                        # 技能擊殺也算充能
                        owner["hit_accumulated"] += 1
                        if owner["hit_accumulated"] >= 20:
                            owner["hit_accumulated"] = 0
                            owner["charge"] = min(3, owner["charge"] + 1)
                    break 
            
            if obj["durability"] > 0:
                active_skills.append(obj)
        game_state["skill_objects"] = active_skills

        # 3. 子彈邏輯
        active_bullets = []
        for b in game_state["bullets"]:
            b['x'] += b['dx']
            b['y'] += b['dy']

            if 0 <= b['x'] <= MAP_WIDTH and 0 <= b['y'] <= MAP_HEIGHT:
                hit = False
                # 3.1 玩家打敵人
                if b['owner'] != 'enemy':
                    for eid, enemy in list(game_state["enemies"].items()):
                        e_size = enemy['size']
                        if check_collision(b, enemy, 5, e_size):
                            # --- 修正 1: 使用子彈攜帶的傷害值 ---
                            damage = b.get('damage', 1) 
                            enemy['hp'] -= damage
                            hit = True
                            
                            # --- 修正 3: 充能邏輯 ---
                            if b['owner'] in game_state["players"]:
                                p = game_state["players"][b['owner']]
                                p["hit_accumulated"] += 1
                                if p["hit_accumulated"] >= 20:
                                    p["hit_accumulated"] = 0
                                    p["charge"] = min(3, p["charge"] + 1) # 最大充能 3

                                if enemy['hp'] <= 0:
                                    p['score'] += enemy['score']
                                    game_state["enemies"].pop(eid)
                            break
                # 3.2 敵人打玩家
                else:
                    for pid, player in list(game_state["players"].items()):
                        if check_collision(b, player, 5, 30):
                            player['hp'] -= b.get('damage', 1)
                            hit = True
                            if player['hp'] <= 0:
                                # 重生重置
                                player['x'], player['y'] = random.randint(100, 500), 400
                                player['hp'] = 3
                                player['score'] = int(player['score'] / 2)
                                player['charge'] = 0 # 死亡掉充能
                            break
                if not hit:
                    active_bullets.append(b)
        game_state["bullets"] = active_bullets

        # 4. 敵人 AI
        for eid, enemy in game_state["enemies"].items():
            speed = enemy['speed'] * 0.6 if enemy['type'] == 3 else enemy['speed']
            enemy['y'] += speed * 0.5 # 整體變慢
            
            enemy['move_timer'] += 1
            if enemy['move_timer'] > 30:
                enemy['x'] += random.choice([-20, 20, 0])
                enemy['move_timer'] = 0
            
            enemy['x'] = max(0, min(MAP_WIDTH - enemy['size'], enemy['x']))
            if enemy['y'] > MAP_HEIGHT: enemy['y'] = -50

            # --- 修正 1: 敵人攻速變慢 (0.005) ---
            shoot_rate = 0.005 # 非常慢
            if enemy['type'] == 3: shoot_rate = 0.015 # Boss稍快一點點
            
            if random.random() < shoot_rate:
                damage = 2 if enemy['type'] == 3 else 1
                game_state["bullets"].append({
                    "x": enemy['x'] + enemy['size']/2, 
                    "y": enemy['y'] + enemy['size'],
                    "dx": 0, "dy": 15, # 敵人子彈向下
                    "owner": "enemy", "damage": damage
                })

        await sio.emit('state_update', game_state)
        await asyncio.sleep(0.05) 

# --- Socket 事件 ---
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(game_loop())

@sio.event
async def join_game(sid, data):
    name = data.get("name", "Cell")[:8]
    skin_type = random.randint(1, 3)
    stats = CELL_CONFIG[skin_type]
    
    game_state["players"][sid] = {
        "x": random.randint(100, 500), "y": 400,
        "name": name, "skin": skin_type, "stats": stats,
        "hp": stats["hp"], "max_hp": stats["hp"],
        "score": 0,
        "charge": 0,            # 當前能量點數 (0-3)
        "hit_accumulated": 0,   # 累積擊中次數 (每20次 +1 charge)
        "last_skill_time": 0    # 冷卻計時用
    }

@sio.event
async def disconnect(sid):
    if sid in game_state["players"]: del game_state["players"][sid]

@sio.event
async def move(sid, data):
    # 接收來自搖桿的向量 dx, dy (範圍 -1 到 1)
    if sid in game_state["players"]:
        p = game_state["players"][sid]
        speed = p['stats']['speed']
        
        # 簡單的物理移動
        vx = data.get('dx', 0)
        vy = data.get('dy', 0)
        
        p['x'] += vx * speed
        p['y'] += vy * speed

        p['x'] = max(0, min(MAP_WIDTH - 30, p['x']))
        p['y'] = max(0, min(MAP_HEIGHT - 30, p['y']))

@sio.event
async def shoot(sid):
    if sid in game_state["players"]:
        p = game_state["players"][sid]
        # --- 修正 5: 只能往上攻擊 ---
        game_state["bullets"].append({
            "x": p['x'] + 15, "y": p['y'],
            "dx": 0, "dy": -p['stats']['bullet_speed'], # 負值往上
            "owner": sid,
            "damage": p['stats']['damage'] # 帶入角色傷害
        })

@sio.event
async def use_skill(sid):
    # --- 修正 4: 技能邏輯 ---
    if sid in game_state["players"]:
        p = game_state["players"][sid]
        current_time = time.time()
        
        # 檢查冷卻 (10秒) 和 能量 (至少1點)
        if p["charge"] >= 1 and (current_time - p["last_skill_time"] > 10):
            p["charge"] -= 1
            p["last_skill_time"] = current_time
            
            # 產生分身 (Orbiting Clone)
            # 一次產生 2 個對角的分身
            game_state["skill_objects"].append({
                "owner_id": sid,
                "x": p["x"], "y": p["y"],
                "size": 30,
                "damage": 1,
                "durability": 10, # 碰撞10次消失
                "duration": 10,   # 持續10秒
                "start_time": current_time,
                "angle_offset": 0 # 0度
            })

@app.get("/")
async def index():
    return {"status": "Cell Wars 2.0 Running"}

# 啟動設定
if __name__ == "__main__":
    uvicorn.run(socketio.ASGIApp(sio, app), host="0.0.0.0", port=8000)
