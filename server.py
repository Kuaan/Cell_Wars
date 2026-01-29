#3.2 server.py
import socketio
import uvicorn
from fastapi import FastAPI
import asyncio
import random
import uuid
import math
import time

# --- 設定與參數 ---
CELL_CONFIG = {
    1: {"name": "Soldier", "hp": 5, "speed": 8, "bullet_speed": 7, "damage": 1, "color": "#50fa7b"},
    2: {"name": "Scout", "hp": 3, "speed": 12, "bullet_speed": 10, "damage": 1, "color": "#8be9fd"},
    3: {"name": "Tank", "hp": 8, "speed": 5, "bullet_speed": 6, "damage": 2, "color": "#ff5555"}
}

VIRUS_CONFIG = {
    1: {"hp": 3, "speed": 3, "size": 50, "score": 10, "prob": 0.7},
    2: {"hp": 1, "speed": 7, "size": 25, "score": 25, "prob": 0.2},
    3: {"hp": 15, "speed": 2, "size": 90, "score": 100, "prob": 0.1}
}

sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
app = FastAPI()
sio_app = socketio.ASGIApp(sio, app)

MAP_WIDTH = 600
MAP_HEIGHT = 500
MAX_ENEMIES = 5

game_vars = {
    "boss_spawned": False,
    "first_elite_killed_time": None,
    "boss_warning_sent": False
}

game_state = {
    "players": {},
    "enemies": {},
    "bullets": [],
    "skill_objects": []
}

# --- 核心優化: 數據壓縮函式 ---
def compress_state(state):
    """
    將遊戲狀態中的浮點數轉為整數，並移除不必要的靜態數據，
    大幅減少 JSON 大小，解決多人在 Render 上的卡頓問題。
    """
    compressed = {
        "players": {},
        "enemies": {},
        "bullets": [],
        "skill_objects": []
    }
    
    for pid, p in state["players"].items():
        compressed["players"][pid] = {
            "x": int(p["x"]),
            "y": int(p["y"]),
            "skin": p["skin"],
            "name": p["name"],
            "hp": int(p["hp"]),
            "max_hp": int(p["max_hp"]),
            "score": int(p["score"]),
            "charge": p["charge"],
            "hit_accumulated": p["hit_accumulated"],
            # 這裡只傳顏色代碼，不需要傳整個 stats 字典
            "c": p["stats"]["color"] 
        }
        
    for eid, e in state["enemies"].items():
        compressed["enemies"][eid] = {
            "x": int(e["x"]),
            "y": int(e["y"]),
            "type": e["type"],
            "size": e["size"],
            "hp": int(e["hp"]),
            "max_hp": int(e["max_hp"])
        }
        
    for b in state["bullets"]:
        compressed["bullets"].append({
            "x": int(b["x"]),
            "y": int(b["y"]),
            "owner": b["owner"] # 保留 owner 用於判斷顏色
        })
        
    for s in state["skill_objects"]:
         compressed["skill_objects"].append({
            "x": int(s["x"]),
            "y": int(s["y"]),
            "skin": s["skin"]
         })
         
    return compressed

def check_collision(rect1, rect2, size1, size2):
    return (rect1['x'] < rect2['x'] + size2 and
            rect1['x'] + size1 > rect2['x'] and
            rect1['y'] < rect2['y'] + size2 and
            rect1['y'] + size1 > rect2['y'])

async def game_loop():
    boss_shoot_toggle = 0

    while True:
        current_time = time.time()

        # 1. Boss 生成
        if not game_vars["boss_spawned"] and game_vars["first_elite_killed_time"]:
            time_since_death = current_time - game_vars["first_elite_killed_time"]
            if time_since_death > 25 and not game_vars["boss_warning_sent"]:
                await sio.emit('sfx', {'type': 'boss_coming'})
                game_vars["boss_warning_sent"] = True
            if time_since_death > 30:
                game_vars["boss_spawned"] = True
                eid = "THE_BOSS"
                game_state["enemies"][eid] = {
                    "x": 150, "y": -300, "type": 999,
                    "hp": 500, "max_hp": 500, "speed": 3, "size": 230,
                    "score": 1000, "move_timer": 0
                }
                await sio.emit('sfx', {'type': 'boss_coming'})

        # 2. 敵人補充
        if len(game_state["enemies"]) < MAX_ENEMIES:
            if not any(e['type'] == 999 for e in game_state["enemies"].values()):
                eid = str(uuid.uuid4())
                rand_val = random.random()
                if rand_val < VIRUS_CONFIG[3]["prob"]: v_type = 3
                elif rand_val < VIRUS_CONFIG[3]["prob"] + VIRUS_CONFIG[2]["prob"]: v_type = 2
                else: v_type = 1
                stats = VIRUS_CONFIG[v_type]
                game_state["enemies"][eid] = {
                    "x": random.randint(0, MAP_WIDTH - stats["size"]),
                    "y": random.randint(-100, 0),
                    "type": v_type,
                    "hp": stats["hp"], "max_hp": stats["hp"],
                    "speed": stats["speed"], "size": stats["size"],
                    "score": stats["score"], "move_timer": 0
                }

        # 3. 擊殺判定函數
        def handle_enemy_death(enemy):
            if enemy['type'] == 3 and game_vars["first_elite_killed_time"] is None:
                game_vars["first_elite_killed_time"] = time.time()
                print("First Elite Killed! Boss Timer Started.")

        # 4. 技能邏輯
        active_skills = []
        for obj in game_state["skill_objects"]:
            if current_time - obj["start_time"] > obj["duration"]: continue
            angle = (current_time * 3) + obj["angle_offset"]
            if obj["owner_id"] in game_state["players"]:
                owner = game_state["players"][obj["owner_id"]]
                obj["x"] = owner["x"] + math.cos(angle) * 50
                obj["y"] = owner["y"] + math.sin(angle) * 50

                for eid, enemy in list(game_state["enemies"].items()):
                    if check_collision(obj, enemy, obj["size"], enemy["size"]):
                        enemy["hp"] -= obj["damage"]
                        obj["durability"] -= 1
                        
                        # 重要事件才廣播音效
                        if enemy["type"] == 999: await sio.emit('sfx', {'type': 'boss_hitted'})
                        else: await sio.emit('sfx', {'type': 'enemy_hitted'})

                        if enemy["hp"] <= 0:
                            handle_enemy_death(enemy)
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

        # 5. 子彈邏輯
        active_bullets = []
        for b in game_state["bullets"]:
            b['x'] += b['dx']
            b['y'] += b['dy']

            if -50 <= b['x'] <= MAP_WIDTH + 50 and -50 <= b['y'] <= MAP_HEIGHT + 50:
                hit = False
                if b['owner'] not in ['enemy', 'boss']:
                    # 玩家打敵人
                    for eid, enemy in list(game_state["enemies"].items()):
                        if check_collision(b, enemy, 5, enemy['size']):
                            enemy['hp'] -= b.get('damage', 1)
                            hit = True
                            
                            if enemy['type'] == 999: await sio.emit('sfx', {'type': 'boss_hitted'})
                            else: await sio.emit('sfx', {'type': 'enemy_hitted'})

                            if b['owner'] in game_state["players"]:
                                p = game_state["players"][b['owner']]
                                p["hit_accumulated"] += 1
                                if p["hit_accumulated"] >= 20:
                                    p["hit_accumulated"] = 0
                                    p["charge"] = min(3, p["charge"] + 1)

                                if enemy['hp'] <= 0:
                                    handle_enemy_death(enemy)
                                    p['score'] += enemy['score']
                                    if eid in game_state["enemies"]: game_state["enemies"].pop(eid)
                            break
                else:
                    # 敵人打玩家
                    for pid, player in list(game_state["players"].items()):
                        if check_collision(b, player, b.get('size', 5), 30):
                            player['hp'] -= b.get('damage', 1)
                            await sio.emit('sfx', {'type': 'character_hitted'})
                            hit = True
                            if player['hp'] <= 0:
                                player['x'], player['y'] = random.randint(100, 500), 400
                                player['hp'] = 3
                                player['score'] = int(player['score'] / 2)
                                player['charge'] = 0
                                player['hit_accumulated'] = 0
                            break
                if not hit: active_bullets.append(b)
        game_state["bullets"] = active_bullets

        # 6. AI 移動
        for eid, enemy in list(game_state["enemies"].items()):
            if enemy['type'] == 999: # Boss AI
                enemy['move_timer'] += 1
                if enemy['move_timer'] > 60:
                    enemy['dx'] = random.choice([-2, -1, 0, 1, 2])
                    enemy['dy'] = random.choice([-1, 0, 1])
                    enemy['move_timer'] = 0
                enemy['x'] = max(0, min(MAP_WIDTH - enemy['size'], enemy['x'] + enemy.get('dx', 0)))
                enemy['y'] = max(0, min(MAP_HEIGHT - enemy['size'], enemy['y'] + enemy.get('dy', 0)))

                for pid, player in game_state["players"].items():
                    if check_collision(player, enemy, 30, enemy['size']):
                        if random.random() < 0.05:
                            player['hp'] -= 1
                            await sio.emit('sfx', {'type': 'character_hitted'})

                is_enraged = (enemy['hp'] < enemy['max_hp'] * 0.5)
                fire_rate = 0.05 if is_enraged else 0.03
                if random.random() < fire_rate:
                    cx, cy = enemy['x'] + enemy['size'] / 2, enemy['y'] + enemy['size'] / 2
                    configs = [(0, 10), (0, -10), (10, 0), (-10, 0)] if is_enraged else ([(0, 10), (0, -10)] if (boss_shoot_toggle:=boss_shoot_toggle+1)%2==0 else [(10, 0), (-10, 0)])
                    for dx, dy in configs:
                        game_state["bullets"].append({
                            "x": cx, "y": cy, "dx": dx, "dy": dy,
                            "owner": "boss", "damage": 1, "size": 10
                        })
                    await sio.emit('sfx', {'type': 'boss_shot'})
            else: # 小怪 AI
                enemy['y'] += enemy['speed'] * 0.5
                enemy['move_timer'] += 1
                if enemy['move_timer'] > 30:
                    enemy['x'] += random.choice([-20, 20, 0])
                    enemy['move_timer'] = 0
                enemy['x'] = max(0, min(MAP_WIDTH - enemy['size'], enemy['x']))
                if enemy['y'] > MAP_HEIGHT: enemy['y'] = -50
                
                # 這裡移除了 enemy_nor_shot 的 sfx 廣播，優化效能
                if random.random() < 0.005:
                    game_state["bullets"].append({
                        "x": enemy['x'] + enemy['size'] / 2, "y": enemy['y'] + enemy['size'],
                        "dx": 0, "dy": 10, "owner": "enemy", "damage": 1, "size": 5
                    })

        # --- 發送壓縮後的狀態 ---
        await sio.emit('state_update', compress_state(game_state))
        await asyncio.sleep(0.05) # 維持 20 FPS

@app.on_event("startup")
async def startup_event(): asyncio.create_task(game_loop())

@sio.event
async def join_game(sid, data):
    name = data.get("name", "Cell")[:8]
    skin_type = random.randint(1, 3)
    game_state["players"][sid] = {
        "x": random.randint(100, 500), "y": 400, "name": name, "skin": skin_type,
        "stats": CELL_CONFIG[skin_type], "hp": CELL_CONFIG[skin_type]["hp"], "max_hp": CELL_CONFIG[skin_type]["hp"],
        "score": 0, "charge": 0, "hit_accumulated": 0, "last_skill_time": 0
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
        game_state["bullets"].append({
            "x": p['x'] + 15, "y": p['y'], "dx": 0, "dy": -p['stats']['bullet_speed'],
            "owner": sid, "damage": p['stats']['damage'], "size": 5
        })
        # 注意：這裡已經移除 await sio.emit('sfx'...) 改由前端自己播

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
            await sio.emit('sfx', {'type': 'skill_slime'})

if __name__ == "__main__":
    uvicorn.run(socketio.ASGIApp(sio, app), host="0.0.0.0", port=8000)
