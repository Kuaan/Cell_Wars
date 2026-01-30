#v3.7.3 server.py
import socketio
import uvicorn
from fastapi import FastAPI
import asyncio
import random
import uuid
import math
import time

# --- 設定與參數 (保持不變) ---
CELL_CONFIG = {
    1: {"name": "Soldier", "hp": 5, "speed": 8, "bullet_speed": 7, "damage": 1, "color": "#50fa7b"},
    2: {"name": "Scout", "hp": 3, "speed": 12, "bullet_speed": 10, "damage": 1, "color": "#8be9fd"},
    3: {"name": "Tank", "hp": 8, "speed": 5, "bullet_speed": 6, "damage": 2, "color": "#ff5555"}
}

VIRUS_CONFIG = {
    1: {"hp": 3, "speed": 3, "size": 50, "score": 10, "prob": 0.7,
        "attack": {"mode": "single", "damage": 1, "bullet_speed": 8, "fire_rate": 0.005}},
    2: {"hp": 1, "speed": 7, "size": 25, "score": 25, "prob": 0.2,
        "attack": {"mode": "single", "damage": 1, "bullet_speed": 15, "fire_rate": 0.01}},
    3: {"hp": 15, "speed": 2, "size": 95, "score": 100, "prob": 0.1,
        "attack": {"mode": "double", "damage": 2, "bullet_speed": 6, "fire_rate": 0.02}}
}

sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
app = FastAPI()
sio_app = socketio.ASGIApp(sio, app)

MAP_WIDTH, MAP_HEIGHT = 600, 500
MAX_ENEMIES = 5
INVINCIBLE_TIME = 0.5 

game_vars = {"boss_phase": "initial", "phase_start_time": 0, "elite_kill_count": 0, "target_kills": 10}
game_state = {"players": {}, "enemies": {}, "bullets": [], "skill_objects": [], "warning_active": False}

class LoopTimer:
    def __init__(self, fps):
        self.frame_duration = 1.0 / fps
        self.next_tick = time.time()
    async def tick(self):
        now = time.time()
        sleep_time = self.next_tick - now
        if sleep_time > 0: await asyncio.sleep(sleep_time)
        self.next_tick = time.time() + self.frame_duration

def compress_state(state):
    compressed = {"players": {}, "enemies": {}, "bullets": [], "skill_objects": [], "w": state["warning_active"]}
    for pid, p in state["players"].items():
        compressed["players"][pid] = {
            "x": int(p["x"]), "y": int(p["y"]), "skin": p["skin"], "name": p["name"],
            "hp": max(0, int(p["hp"])), "max_hp": int(p["max_hp"]), "score": int(p["score"]),
            "charge": p["charge"], "hit_accumulated": p["hit_accumulated"],
            "invincible": (time.time() - p.get("last_hit_time", 0) < INVINCIBLE_TIME)
        }
    for eid, e in state["enemies"].items():
        compressed["enemies"][eid] = {"x": int(e["x"]), "y": int(e["y"]), "type": e["type"], "size": e["size"], "hp": max(0, int(e["hp"])), "max_hp": int(e["max_hp"])}
    for b in state["bullets"]:
        compressed["bullets"].append({"x": int(b["x"]), "y": int(b["y"]), "owner": b["owner"]})
    for s in state["skill_objects"]:
        compressed["skill_objects"].append({"x": int(s["x"]), "y": int(s["y"]), "skin": s["skin"]})
    return compressed

def check_collision(obj1, obj2, r1_override=None, r2_override=None):
    r1 = r1_override if r1_override is not None else obj1.get('size', 20) / 2
    r2 = r2_override if r2_override is not None else obj2.get('size', 20) / 2
    cx1, cy1 = obj1['x'] + r1, obj1['y'] + r1
    cx2, cy2 = obj2['x'] + r2, obj2['y'] + r2
    return ((cx1 - cx2)**2 + (cy1 - cy2)**2) < ((r1 + r2)**2 * 0.8)

def spawn_boss():
    game_state["enemies"]["THE_BOSS"] = {"x": 150, "y": -300, "type": 999, "hp": 500, "max_hp": 500, "speed": 5, "size": 230, "score": 1000, "move_timer": 0}
    game_vars["boss_phase"] = "boss_active"
    game_state["warning_active"] = False

async def game_loop():
    timer = LoopTimer(fps=30)
    boss_shoot_toggle = 0
    while True:
        curr = time.time()
        sfx_buffer = []

        # --- Boss 流程管理 ---
        if game_vars["boss_phase"] == "countdown" and curr - game_vars["phase_start_time"] > 25:
            game_vars["boss_phase"], game_vars["phase_start_time"], game_state["warning_active"] = "warning", curr, True
            sfx_buffer.append({'type': 'boss_coming'})
        elif game_vars["boss_phase"] == "warning" and curr - game_vars["phase_start_time"] > 5:
            spawn_boss()
            sfx_buffer.append({'type': 'boss_coming'})

        # --- 敵人生成 ---
        if len(game_state["enemies"]) < MAX_ENEMIES and game_vars["boss_phase"] != "boss_active":
            eid, rv = str(uuid.uuid4()), random.random()
            v_type = 3 if rv < 0.1 else (2 if rv < 0.3 else 1)
            st = VIRUS_CONFIG[v_type]
            game_state["enemies"][eid] = {"x": random.randint(0, MAP_WIDTH-st["size"]), "y": -100, "type": v_type, "hp": st["hp"], "max_hp": st["hp"], "speed": st["speed"], "size": st["size"], "score": st["score"], "move_timer": 0}

        # --- 子彈與碰撞邏輯 ---
        new_bullets = []
        for b in game_state["bullets"]:
            b['x'] += b['dx']; b['y'] += b['dy']
            if not (-50 <= b['x'] <= MAP_WIDTH+50 and -50 <= b['y'] <= MAP_HEIGHT+50): continue
            
            hit = False
            if b['owner'] not in ['enemy', 'boss']: # 玩家子彈
                for eid, en in list(game_state["enemies"].items()):
                    if check_collision(b, en, 5):
                        en['hp'] -= b.get('damage', 1); hit = True
                        sfx_buffer.append({'type': 'boss_hitted' if en['type']==999 else 'enemy_hitted'})
                        if b['owner'] in game_state["players"]:
                            p = game_state["players"][b['owner']]
                            p["hit_accumulated"] += 1
                            if p["hit_accumulated"] >= 20: p["hit_accumulated"]=0; p["charge"]=min(3, p["charge"]+1)
                            if en['hp'] <= 0:
                                p['score'] += en['score']
                                if en['type'] == 3: # 精英怪邏輯
                                    if game_vars["boss_phase"] == "initial": game_vars["boss_phase"], game_vars["phase_start_time"] = "countdown", curr
                                    elif game_vars["boss_phase"] == "collecting":
                                        game_vars["elite_kill_count"] += 1
                                        if game_vars["elite_kill_count"] >= game_vars["target_kills"]: game_vars["boss_phase"], game_vars["phase_start_time"], game_state["warning_active"] = "warning", curr, True; sfx_buffer.append({'type': 'boss_coming'})
                                elif en['type'] == 999: game_vars["boss_phase"], game_vars["elite_kill_count"] = "collecting", 0
                                game_state["enemies"].pop(eid)
                        break
            else: # 敵方子彈
                for pid, pl in game_state["players"].items():
                    if (curr - pl.get('last_hit_time', 0)) >= INVINCIBLE_TIME and check_collision(b, pl, b.get('size',5)/2, 15):
                        pl['hp'] -= b.get('damage', 1); pl['last_hit_time'], hit = curr, True
                        sfx_buffer.append({'type': 'character_hitted'})
                        if pl['hp'] <= 0:
                            pl['x'], pl['y'], pl['hp'], pl['score'], pl['charge'] = 300, 400, pl['max_hp'], int(pl['score']/2), 0
                        break
            if not hit: new_bullets.append(b)
        game_state["bullets"] = new_bullets

        # --- 技能物件邏輯 ---
        new_skills = []
        for s in game_state["skill_objects"]:
            if curr - s["start_time"] > s["duration"] or s["durability"] <= 0: continue
            if s["owner_id"] in game_state["players"]:
                owner = game_state["players"][s["owner_id"]]
                angle = (curr * 3) + s["angle_offset"]
                s["x"], s["y"] = owner["x"] + math.cos(angle)*50, owner["y"] + math.sin(angle)*50
                for eid, en in list(game_state["enemies"].items()):
                    if check_collision(s, en):
                        en["hp"] -= s["damage"]; s["durability"] -= 1
                        sfx_buffer.append({'type': 'enemy_hitted'})
                        if en["hp"] <= 0:
                            owner["score"] += en["score"]; game_state["enemies"].pop(eid)
            new_skills.append(s)
        game_state["skill_objects"] = new_skills

        # --- 敵人 AI 與開火 ---
        for eid, en in game_state["enemies"].items():
            if en['type'] == 999: # Boss
                en['move_timer'] += 1
                if en['move_timer'] > 40: en['dx'], en['dy'], en['move_timer'] = random.randint(-2,2), random.randint(-1,1), 0
                en['x'] = max(0, min(MAP_WIDTH-en['size'], en['x']+en.get('dx',0)))
                en['y'] = max(0, min(MAP_HEIGHT-en['size'], en['y']+en.get('dy',0)))
                if random.random() < (0.05 if en['hp'] < 250 else 0.03):
                    for dx, dy in [(0,10),(0,-10),(10,0),(-10,0)]: game_state["bullets"].append({"x": en['x']+en['size']/2, "y": en['y']+en['size']/2, "dx": dx, "dy": dy, "owner": "boss", "damage": 1, "size": 10})
                    sfx_buffer.append({'type': 'boss_shot'})
            else: # 一般怪
                en['y'] += en['speed']*0.5
                if en['y'] > MAP_HEIGHT: en['y'] = -50
                atk = VIRUS_CONFIG[en['type']]['attack']
                if random.random() < atk['fire_rate']:
                    game_state["bullets"].append({"x": en['x']+en['size']/2, "y": en['y']+en['size'], "dx": 0, "dy": atk['bullet_speed'], "owner": "enemy", "damage": atk['damage'], "size": 6})
                    sfx_buffer.append({'type': 'enemy_nor_shot'})

        # --- 同步狀態 ---
        await sio.emit('state_update', compress_state(game_state))
        if sfx_buffer:
            # 去重廣播，避免同一幀內發送過多重複音效
            for s_type in set(s['type'] for s in sfx_buffer):
                await sio.emit('sfx', {'type': s_type})
        await timer.tick()

@sio.event
async def join_game(sid, data):
    sk = random.randint(1, 3)
    game_state["players"][sid] = {"x": 300, "y": 400, "name": data.get("name","Cell")[:8], "skin": sk, "stats": CELL_CONFIG[sk], "hp": CELL_CONFIG[sk]["hp"], "max_hp": CELL_CONFIG[sk]["hp"], "score": 0, "charge": 0, "hit_accumulated": 0, "last_skill_time": 0, "last_hit_time": 0}

@sio.event
async def disconnect(sid):
    if sid in game_state["players"]: del game_state["players"][sid]

@sio.event
async def move(sid, data):
    if sid in game_state["players"]:
        p = game_state["players"][sid]
        p['x'] = max(0, min(MAP_WIDTH-30, p['x'] + data.get('dx',0)*p['stats']['speed']))
        p['y'] = max(0, min(MAP_HEIGHT-30, p['y'] + data.get('dy',0)*p['stats']['speed']))

@sio.event
async def shoot(sid):
    if sid in game_state["players"]:
        p = game_state["players"][sid]
        game_state["bullets"].append({"x": p['x']+15, "y": p['y'], "dx": 0, "dy": -p['stats']['bullet_speed'], "owner": sid, "damage": p['stats']['damage'], "size": 5})
        # [優化] 此處不 emit 音效，由前端 doFire() 本地直接播放

@sio.event
async def use_skill(sid):
    if sid in game_state["players"]:
        p = game_state["players"][sid]
        if p["charge"] >= 1 and (time.time() - p["last_skill_time"] > 2):
            p["charge"] -= 1; p["last_skill_time"] = time.time()
            game_state["skill_objects"].append({"owner_id": sid, "x": p["x"], "y": p["y"], "size": 30, "damage": 1, "durability": 10, "duration": 10, "start_time": time.time(), "angle_offset": 0, "skin": p["skin"]})
            await sio.emit('sfx', {'type': 'skill_slime'})

@app.on_event("startup")
async def startup(): asyncio.create_task(game_loop())

if __name__ == "__main__":
    uvicorn.run(sio_app, host="0.0.0.0", port=8000)
