# --- 獨立物件設定檔 (Configuration) ---

# 玩家細胞的三種型態
CELL_CONFIG = {
    1: { # 綠色細胞 (均衡型)
        "name": "Soldier",
        "hp": 5,
        "speed": 10,       # 移動速度
        "bullet_speed": 15,
        "damage": 1,       # 子彈傷害
        "color": "#50fa7b" # 綠色
    },
    2: { # 藍色細胞 (速度型 - 攻擊低但跑得快)
        "name": "Scout",
        "hp": 3,
        "speed": 16,       # 跑超快
        "bullet_speed": 20,
        "damage": 1,
        "color": "#8be9fd" # 藍色
    },
    3: { # 紅色細胞 (重裝型 - 跑得慢但皮厚痛)
        "name": "Tank",
        "hp": 8,           # 血超厚
        "speed": 6,        # 跑得慢
        "bullet_speed": 12,
        "damage": 2,       # 一槍兩滴血
        "color": "#ff5555" # 紅色
    }
}

# 病毒的三種型態
VIRUS_CONFIG = {
    1: { # 紫色病毒 (雜魚)
        "hp": 3,
        "speed": 3,
        "size": 30,
        "score": 10,
        "prob": 0.7  # 出現機率 70%
    },
    2: { # 綠色病毒 (快速衝撞者)
        "hp": 1,
        "speed": 7,  # 衝很快
        "size": 25,  # 體積小
        "score": 25,
        "prob": 0.2  # 出現機率 20%
    },
    3: { # 魔王病毒 (Boss)
        "hp": 15,
        "speed": 2,  # 慢慢壓境
        "size": 60,  # 超大隻
        "score": 100,
        "prob": 0.1  # 出現機率 10%
    }
}


import socketio
import uvicorn
from fastapi import FastAPI
import asyncio
import random
import uuid

# --- 伺服器初始化 ---
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
app = FastAPI()
sio_app = socketio.ASGIApp(sio, app)

# --- 遊戲設定 ---
MAP_WIDTH = 600
MAP_HEIGHT = 500
CELL_SIZE = 30    # 玩家與普通病毒大小
BOSS_SIZE = 50    # 魔王(virus_3)大小
BULLET_SPEED = 15
ENEMY_SPEED = 3
MAX_ENEMIES = 4
MAX_PLAYERS = 20  # 伺服器人數上限

# --- 遊戲狀態 ---
game_state = {
    "players": {},  # {sid: {x, y, dir, name, skin, hp, score}}
    "enemies": {},  # {id: {x, y, type, hp, move_timer}}
    "bullets": []   # [{x, y, dx, dy, owner, damage}]
}

# --- 輔助函式：碰撞檢測 (AABB) ---
def check_collision(rect1, rect2, size1, size2):
    return (rect1['x'] < rect2['x'] + size2 and
            rect1['x'] + size1 > rect2['x'] and
            rect1['y'] < rect2['y'] + size2 and
            rect1['y'] + size1 > rect2['y'])

# --- 核心遊戲迴圈 ---
async def game_loop():
    while True:
        # 0. 計算全伺服器總分
        total_score = sum(p['score'] for p in game_state["players"].values())

        # 1. 敵人生成邏輯
        # ... 在 game_loop 裡面 ...
        if len(game_state["enemies"]) < MAX_ENEMIES:
            eid = str(uuid.uuid4())
            
            # 根據機率決定生成哪種病毒
            rand_val = random.random()
            if total_score >= 500 and random.random() < 0.2: v_type = 3     # 20% 機率 Boss
            elif rand_val < 0.3: v_type = 2   # 20% 機率 衝撞怪
            else: v_type = 1                  # 剩下是雜魚
            
            stats = VIRUS_CONFIG[v_type]
            
            game_state["enemies"][eid] = {
                "x": random.randint(0, MAP_WIDTH - stats["size"]),
                "y": random.randint(-100, 0),
                "type": v_type,
                "hp": stats["hp"],
                "max_hp": stats["hp"],
                "speed": stats["speed"], # 寫入個別速度
                "size": stats["size"],   # 寫入個別大小
                "score": stats["score"],
                "move_timer": 0
            }


        # 2. 子彈邏輯
        active_bullets = []
        for b in game_state["bullets"]:
            b['x'] += b['dx']
            b['y'] += b['dy']

            if 0 <= b['x'] <= MAP_WIDTH and 0 <= b['y'] <= MAP_HEIGHT:
                hit = False
                # 2.1 玩家子彈擊中敵人
                if b['owner'] != 'enemy':
                    for eid, enemy in list(game_state["enemies"].items()):
                        # 動態判定敵人碰撞箱大小
                        e_size = BOSS_SIZE if enemy['type'] == 3 else CELL_SIZE
                        if check_collision(b, enemy, 5, e_size):
                            enemy['hp'] -= 1
                            hit = True
                            if enemy['hp'] <= 0:
                                reward = 100 if enemy['type'] == 3 else 10
                                if b['owner'] in game_state["players"]:
                                    game_state["players"][b['owner']]['score'] += reward
                                game_state["enemies"].pop(eid)
                            break
                # 2.2 敵人子彈擊中玩家
                else:
                    for pid, player in list(game_state["players"].items()):
                        if check_collision(b, player, 5, CELL_SIZE):
                            player['hp'] -= b.get('damage', 1)
                            hit = True
                            if player['hp'] <= 0:
                                # 死亡重生
                                player['x'] = random.randint(100, 500)
                                player['y'] = 400
                                player['hp'] = 3
                                player['score'] = max(0, player['score']/2)
                            break
                if not hit:
                    active_bullets.append(b)
        game_state["bullets"] = active_bullets

        # 3. 敵人 AI 移動與攻擊
        for eid, enemy in game_state["enemies"].items():
            # 魔王移動稍慢，更有壓迫感
            speed = ENEMY_SPEED * 0.6 if enemy['type'] == 3 else ENEMY_SPEED
            enemy['y'] += speed

            enemy['move_timer'] += 1
            if enemy['move_timer'] > 30:
                enemy['x'] += random.choice([-20, 20, 0])
                enemy['move_timer'] = 0

            # 邊界限制
            e_size = BOSS_SIZE if enemy['type'] == 3 else CELL_SIZE
            enemy['x'] = max(0, min(MAP_WIDTH - e_size, enemy['x']))
            if enemy['y'] > MAP_HEIGHT: enemy['y'] = -50

            # 敵人射擊頻率
            shoot_rate = 0.02 if enemy['type'] == 3 else 0.01 #0.08/0.04
            
            if random.random() < shoot_rate:
                damage = 2 if enemy['type'] == 3 else 1
                game_state["bullets"].append({
                    "x": enemy['x'] + e_size/2, 
                    "y": enemy['y'] + e_size,
                    "dx": 0, "dy": BULLET_SPEED,
                    "owner": "enemy", "damage": damage
                })

        # 4. 廣播狀態
        await sio.emit('state_update', game_state)
        await asyncio.sleep(0.05) # 20 FPS

# --- Socket 事件 ---

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(game_loop())

@sio.event
async def connect(sid, environ):
    if len(game_state["players"]) >= MAX_PLAYERS:
        return False # 拒絕連線
    print(f"Connected: {sid}")

@sio.event
async def join_game(sid, data):
    name = data.get("name", "Cell")[:10]
    
    # 隨機分配一種細胞類型 (1~3)
    skin_type = random.randint(1, 3)
    stats = CELL_CONFIG[skin_type] # 讀取上面的設定檔
    
    game_state["players"][sid] = {
        "x": random.randint(100, 500),
        "y": 400,
        "dir": "up",
        "name": name,
        "skin": skin_type,  # 記住是什麼皮
        "type_stats": stats, # 把整個能力值存進去，方便後面用
        "hp": stats["hp"],
        "max_hp": stats["hp"], # 用來算血條比例
        "score": 0
    }

@sio.event
async def disconnect(sid):
    if sid in game_state["players"]:
        del game_state["players"][sid]

@sio.event
async def move(sid, data):
    if sid in game_state["players"]:
        p = game_state["players"][sid]
        direction = data.get('dir', 'up')
        p['dir'] = direction
        
        # 從設定檔讀取該玩家的速度
        speed = p['type_stats']['speed']
        
        # 伺服器自己計算位移 (防作弊也更準確)
        if direction == 'up': p['y'] -= speed
        if direction == 'down': p['y'] += speed
        if direction == 'left': p['x'] -= speed
        if direction == 'right': p['x'] += speed

        # 邊界限制
        p['x'] = max(0, min(MAP_WIDTH - 30, p['x']))
        p['y'] = max(0, min(MAP_HEIGHT - 30, p['y']))

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
            "owner": sid
        })

@app.get("/")
async def index():
    return {
        "status": "Cell Wars Server is Running", 
        "players": len(game_state["players"]),
        "enemies": len(game_state["enemies"])
    }

# --- 關鍵：Procfile 必須指向這個變數 ---
# 確保這行在檔案最下方，這樣 app 裡的路由才會被包進去
sio_app = socketio.ASGIApp(sio, app)
