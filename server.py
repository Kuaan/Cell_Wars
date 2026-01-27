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
MAX_ENEMIES = 3

# --- 遊戲狀態 ---
game_state = {
    "players": {},  # {sid: {x, y, dir, color, hp, score}}
    "enemies": {},  # {id: {x, y, dir, hp}}
    "bullets": []  # [{x, y, dx, dy, owner}] owner可能是 'enemy' 或 player_sid
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
        # 生成敵人邏輯
        if len(game_state["enemies"]) < MAX_ENEMIES:
            eid = str(uuid.uuid4())
            # 隨機前兩種病毒 (virus_1 或 virus_2)
            v_type = random.randint(1, 2) 
            # 如果想加入解鎖機制，可以根據分數決定是否出現 v_type = 3
            
            game_state["enemies"][eid] = {
                "x": random.randint(0, MAP_WIDTH - TANK_SIZE),
                "y": random.randint(0, 100),
                "type": v_type, # 紀錄病毒種類
                "hp": 1,
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
                            game_state["enemies"].pop(eid)  # 移除敵人
                            # 幫玩家加分
                            if b['owner'] in game_state["players"]:
                                game_state["players"][b['owner']]['score'] += 10
                            hit = True
                            break

                # 2.2 檢查子彈是否打中玩家 (如果是敵人射的)
                else:
                    for pid, player in list(game_state["players"].items()):
                        if check_collision(b, player, 5, TANK_SIZE):
                            player['hp'] -= 1
                            if player['hp'] <= 0:
                                # 重生邏輯
                                player['x'] = random.randint(0, MAP_WIDTH)
                                player['y'] = MAP_HEIGHT - 50
                                player['hp'] = 3
                                player['score'] = max(0, player['score'] - 5)
                            hit = True
                            break

                if not hit:
                    active_bullets.append(b)

        game_state["bullets"] = active_bullets

        # 3. 更新敵人 AI (簡單的隨機移動與射擊)
        for eid, enemy in game_state["enemies"].items():
            enemy['y'] += ENEMY_SPEED  # 慢慢往下走

            # 隨機左右移動
            enemy['move_timer'] += 1
            if enemy['move_timer'] > 20:
                enemy['x'] += random.choice([-10, 10, 0])
                enemy['move_timer'] = 0

            # 邊界限制
            enemy['x'] = max(0, min(MAP_WIDTH - TANK_SIZE, enemy['x']))
            if enemy['y'] > MAP_HEIGHT: enemy['y'] = 0  # 到底部回到頂部

            # 隨機射擊 (1% 機率)
            if random.random() < 0.05:
                game_state["bullets"].append({
                    "x": enemy['x'] + 12, "y": enemy['y'] + 30,
                    "dx": 0, "dy": BULLET_SPEED, "owner": "enemy"
                })

        # 4. 廣播狀態給所有玩家
        await sio.emit('state_update', game_state)

        # 控制 FPS (0.05秒 = 20 FPS)
        await asyncio.sleep(0.05)


# --- Socket 事件 ---

@app.on_event("startup")
async def startup_event():
    # 伺服器啟動時，同時啟動遊戲迴圈
    asyncio.create_task(game_loop())


# 玩家狀態結構新增 "name"
# game_state["players"] = {sid: {x, y, dir, color, hp, score, name}}

@sio.event
async def connect(sid, environ):
    print(f"連線中: {sid}")

@sio.event
async def join_game(sid, data):
    name = data.get("name", "Cell")[:10]
    game_state["players"][sid] = {
        "x": random.randint(100, 500),
        "y": 400,
        "name": name,
        "skin": random.randint(1, 3), # 隨機分配 1, 2, 3 號細胞
        "hp": 3,
        "score": 0
    }
    print(f"玩家 {name} ({sid}) 正式加入戰場")

@sio.event
async def disconnect(sid):
    if sid in game_state["players"]:
        print(f"玩家 {game_state['players'][sid]['name']} 離開")
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
        if p['dir'] == 'up':
            dy = -BULLET_SPEED
        elif p['dir'] == 'down':
            dy = BULLET_SPEED
        elif p['dir'] == 'left':
            dx = -BULLET_SPEED
        elif p['dir'] == 'right':
            dx = BULLET_SPEED

        game_state["bullets"].append({
            "x": p['x'] + 12,
            "y": p['y'] + 12,
            "dx": dx,
            "dy": dy,
            "owner": sid
        })


if __name__ == "__main__":
    uvicorn.run("server:sio_app", host="0.0.0.0", port=8000, reload=True)
