# server.py
import socketio
import uvicorn
from fastapi import FastAPI
import asyncio
import random
import uuid

# 建立 Socket.IO 伺服器
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
app = FastAPI()
sio_app = socketio.ASGIApp(sio, app)

# --- 遊戲設定 ---
MAP_WIDTH = 600
MAP_HEIGHT = 500
TANK_SIZE = 30
BULLET_SPEED = 15
ENEMY_SPEED = 3
MAX_ENEMIES = 4  # 稍微增加敵對單位數量

# --- 遊戲狀態 ---
game_state = {
    "players": {},  # {sid: {x, y, dir, name, skin, hp, score}}
    "enemies": {},  # {id: {x, y, type, hp}}
    "bullets": []   # [{x, y, dx, dy, owner, damage}]
}

# --- 輔助函式：碰撞檢測 (AABB) ---
def check_collision(rect1, rect2, size1, size2):
    return (rect1['x'] < rect2['x'] + size2 and
            rect1['x'] + size1 > rect2['x'] and
            rect1['y'] < rect2['y'] + size2 and
            rect1['y'] + size1 > rect2['y'])

# --- 核心：遊戲主迴圈 (Game Loop) ---
async def game_loop():
    while True:
        # 0. 計算目前全服總分
        total_score = sum(p['score'] for p in game_state["players"].values())

        # 1. 生成敵人邏輯
        if len(game_state["enemies"]) < MAX_ENEMIES:
            eid = str(uuid.uuid4())
            
            # 判斷是否可以生成 virus_3 (總分 > 500 且 20% 機率)
            if total_score >= 500 and random.random() < 0.2:
                v_type = 3
                hp = 10
            else:
                v_type = random.randint(1, 2)
                hp = 1
            
            game_state["enemies"][eid] = {
                "x": random.randint(0, MAP_WIDTH - TANK_SIZE),
                "y": random.randint(0, 100),
                "type": v_type,
                "hp": hp,
                "move_timer": 0
            }

        # 2. 更新子彈位置
        active_bullets = []
        for b in game_state["bullets"]:
            b['x'] += b['dx']
            b['y'] += b['dy']

            # 檢查子彈是否出界
            if 0 <= b['x'] <= MAP_WIDTH and 0 <= b['y'] <= MAP_HEIGHT:
                hit = False
                # 2.1 檢查子彈是否打中敵人 (如果是玩家射的)
                if b['owner'] != 'enemy':
                    for eid, enemy in list(game_state["enemies"].items()):
                        if check_collision(b, enemy, 5, TANK_SIZE):
                            enemy['hp'] -= 1
                            hit = True
                            if enemy['hp'] <= 0:
                                # 根據敵人種類給分
                                reward = 100 if enemy['type'] == 3 else 10
                                if b['owner'] in game_state["players"]:
                                    game_state["players"][b['owner']]['score'] += reward
                                game_state["enemies"].pop(eid)
                            break

                # 2.2 檢查子彈是否打中玩家 (如果是敵人射的)
                else:
                    for pid, player in list(game_state["players"].items()):
                        if check_collision(b, player, 5, TANK_SIZE):
                            player['hp'] -= b.get('damage', 1) # virus_3 會造成 2 點傷害
                            hit = True
                            if player['hp'] <= 0:
                                # 重生邏輯
                                player['x'] = random.randint(0, MAP_WIDTH - TANK_SIZE)
                                player['y'] = MAP_HEIGHT - 50
                                player['hp'] = 3
                                player['score'] = max(0, player['score'] - 20) # 死亡扣分多一點
                            break

                if not hit:
                    active_bullets.append(b)
        game_state["bullets"] = active_bullets

        # 3. 更新敵人 AI
        for eid, enemy in game_state["enemies"].items():
            # virus_3 移動稍微慢一點點，增加厚重感
            current_speed = ENEMY_SPEED if enemy['type'] != 3 else ENEMY_SPEED * 0.7
            enemy['y'] += current_speed

            # 隨機左右移動
            enemy['move_timer'] += 1
            if enemy['move_timer'] > 20:
                enemy['x'] += random.choice([-15, 15, 0])
                enemy['move_timer'] = 0

            # 邊界限制與循環
            enemy['x'] = max(0, min(MAP_WIDTH - TANK_SIZE, enemy['x']))
            if enemy['y'] > MAP_HEIGHT: enemy['y'] = 0

            # 敵人射擊
            shoot_chance = 0.05 if enemy['type'] != 3 else 0.08 # virus_3 射速稍快
            if random.random() < shoot_chance:
                damage = 2 if enemy['type'] == 3 else 1
                game_state["bullets"].append({
                    "x": enemy['x'] + 15, "y": enemy['y'] + 30,
                    "dx": 0, "dy": BULLET_SPEED, 
                    "owner": "enemy", 
                    "damage": damage
                })

        # 4. 廣播狀態
        await sio.emit('state_update', game_state)
        await asyncio.sleep(0.05)

# --- Socket 事件 ---

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(game_loop())

@sio.event
async def connect(sid, environ):
    print(f"玩家連線嘗試: {sid}")

@sio.event
async def join_game(sid, data):
    name = data.get("name", "Cell")[:10]
    game_state["players"][sid] = {
        "x": random.randint(100, 500),
        "y": 400,
        "dir": "up",
        "name": name,
        "skin": random.randint(1, 3), # 隨機 3 種細胞外觀
        "hp": 3,
        "score": 0
    }
    print(f"玩家 {name} 加入戰場")

@sio.event
async def disconnect(sid):
    if sid in game_state["players"]:
        del game_state["players"][sid]

@sio.event
async def move(sid, data):
    if sid in game_state["players"]:
        p = game_state["players"][sid]
        p['x'] += data['dx']
        p['y'] += data['dy']
        p['dir'] = data['dir']
        p['x'] = max(0, min(MAP_WIDTH - TANK_SIZE, p['x']))
        p['y'] = max(0, min(MAP_HEIGHT - TANK_SIZE, p['y']))

@sio.event
async def shoot(sid):
    if sid in game_state["players"]:
        p = game_state["players"][sid]
        dx, dy = 0, 0
        if p['dir'] == 'up': dy = -BULLET_SPEED
        elif p['dir'] == 'down': dy = BULLET_SPEED
        elif p['dir'] == 'left': dx = -BULLET_SPEED
        elif p['dir'] == 'right': dx = BULLET_SPEED

        game_state["bullets"].append({
            "x": p['x'] + 15, "y": p['y'] + 15,
            "dx": dx, "dy": dy,
            "owner": sid,
            "damage": 1
        })

if __name__ == "__main__":
    uvicorn.run("server:sio_app", host="0.0.0.0", port=8000)
