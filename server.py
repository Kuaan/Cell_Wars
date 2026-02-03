import eventlet
eventlet.monkey_patch()

from flask import Flask, request
from flask_socketio import SocketIO, emit
import time
import math
import random

app = Flask(__name__)
# async_mode='eventlet' 是效能關鍵，確保非阻塞處理
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet', logger=False, engineio_logger=False)

# --- 遊戲常數 ---
WIDTH, HEIGHT = 600, 500
# 定義各兵種冷卻時間 (毫秒)
COOLDOWNS = {
    1: 250,  # Soldier: 標準
    2: 150,  # Scout: 快
    3: 400   # Tank: 慢
}
# 定義各兵種子彈速度
BULLET_SPEEDS = {
    1: 7,
    2: 10,
    3: 6
}

# --- 遊戲狀態 ---
# players 結構增加: 'last_shot': timestamp
gameState = {
    "players": {},
    "enemies": {},
    "bullets": [],
    "skill_objects": [],
    "w": False
}

def get_current_ms():
    return time.time() * 1000

# --- 輔助函式 ---
def spawn_enemy():
    if len(gameState["enemies"]) >= 5: return
    eid = str(time.time())
    etype = random.randint(1, 3)
    # Boss 邏輯省略簡化，維持隨機生成小怪
    gameState["enemies"][eid] = {
        "x": random.randint(20, WIDTH-20),
        "y": -50,
        "type": etype,
        "hp": 20 * etype,
        "max_hp": 20 * etype,
        "size": 30 + (etype * 5),
        "speed": 2
    }

def check_collision(rect1, rect2):
    return (rect1["x"] < rect2["x"] + rect2["w"] and
            rect1["x"] + rect1["w"] > rect2["x"] and
            rect1["y"] < rect2["y"] + rect2["h"] and
            rect1["y"] + rect1["h"] > rect2["y"])

# --- Socket 事件 ---

@socketio.on('connect')
def on_connect():
    print(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def on_disconnect():
    if request.sid in gameState["players"]:
        del gameState["players"][request.sid]
    print(f"Client disconnected: {request.sid}")

@socketio.on('join_game')
def on_join(data):
    # 預設 Skin 1
    skin = 1
    gameState["players"][request.sid] = {
        "name": data.get("name", "Unknown")[:8],
        "x": WIDTH / 2,
        "y": HEIGHT - 50,
        "hp": 100,
        "max_hp": 100,
        "skin": skin,
        "score": 0,
        "charge": 0,
        "hit_accumulated": 0,
        "invincible": False,
        "last_shot": 0  # [新增] 射擊冷卻計時
    }
    emit('state_update', gameState)

@socketio.on('move')
def on_move(data):
    if request.sid not in gameState["players"]: return
    p = gameState["players"][request.sid]
    
    # 簡單移動邏輯
    dx = data.get('dx', 0)
    dy = data.get('dy', 0)
    speed = 5
    
    p['x'] += dx * speed
    p['y'] += dy * speed
    
    # 邊界限制
    p['x'] = max(0, min(WIDTH - 30, p['x']))
    p['y'] = max(0, min(HEIGHT - 30, p['y']))

@socketio.on('shoot')
def on_shoot():
    sid = request.sid
    if sid not in gameState["players"]: return
    p = gameState["players"][sid]
    
    now = get_current_ms()
    cd = COOLDOWNS.get(p['skin'], 250)
    
    # [關鍵優化] Server 端射速限制
    # 如果距離上次射擊時間小於冷卻時間，直接無視請求
    if now - p['last_shot'] < cd:
        return 

    # 更新最後射擊時間
    p['last_shot'] = now
    
    # 生成子彈
    b_speed = BULLET_SPEEDS.get(p['skin'], 7)
    gameState["bullets"].append({
        "x": p['x'] + 15,
        "y": p['y'],
        "owner": sid,
        "speed": b_speed,
        "vy": -b_speed
    })
    
    # [關鍵優化] 這裡 "不" 廣播射擊音效
    # 因為 Client 端已經自己播放了。Server 廣播只會造成網路阻塞和回音。
    # 如果一定要讓別人聽到，必須使用 socketio.emit(..., skip_sid=sid)
    # 但為了效能，建議省略普通射擊的廣播。

@socketio.on('use_skill')
def on_skill():
    sid = request.sid
    if sid not in gameState["players"]: return
    p = gameState["players"][sid]
    
    if p['charge'] >= 1:
        p['charge'] -= 1
        # 技能邏輯 (簡單生成一個向上飛的物體)
        gameState["skill_objects"].append({
            "x": p['x'],
            "y": p['y'],
            "owner": sid,
            "skin": p['skin']
        })
        # 技能音效比較稀有，可以廣播
        socketio.emit('sfx', {'type': 'skill_slime'})

# --- 遊戲主迴圈 (Background Thread) ---
def game_loop():
    print("Game loop started")
    while True:
        start_time = time.time()
        
        # 1. 更新子彈
        # 過濾掉出界的子彈，避免陣列無限膨脹
        active_bullets = []
        for b in gameState["bullets"]:
            b['y'] += b.get('vy', -7) # 預設向上
            
            hit = False
            # 檢查是否打中敵人 (簡單 AABB)
            b_rect = {"x": b['x']-4, "y": b['y']-4, "w": 8, "h": 8}
            
            # 只有玩家子彈會打敵人
            if b['owner'] in gameState["players"]: 
                player_id = b['owner']
                enemies_to_remove = []
                
                for eid, e in gameState["enemies"].items():
                    e_rect = {"x": e['x'], "y": e['y'], "w": e['size'], "h": e['size']}
                    if check_collision(b_rect, e_rect):
                        e['hp'] -= 5 # 傷害
                        hit = True
                        
                        # [關鍵優化] 命中音效只傳給攻擊者 (Unicast)
                        # 這大幅減少了網路流量
                        socketio.emit('sfx', {'type': 'enemy_hitted'}, to=player_id)
                        
                        # 加分與充能邏輯
                        if player_id in gameState["players"]:
                            p = gameState["players"][player_id]
                            p['hit_accumulated'] += 1
                            if p['hit_accumulated'] >= 20:
                                p['hit_accumulated'] = 0
                                p['charge'] = min(3, p['charge'] + 1)
                        
                        if e['hp'] <= 0:
                            enemies_to_remove.append(eid)
                            if player_id in gameState["players"]:
                                gameState["players"][player_id]['score'] += 100
                        break # 一顆子彈只打一隻
                
                # 移除死掉的敵人
                for eid in enemies_to_remove:
                    del gameState["enemies"][eid]
            
            if not hit and -50 < b['y'] < HEIGHT + 50:
                active_bullets.append(b)
                
        gameState["bullets"] = active_bullets

        # 2. 生成敵人
        if random.random() < 0.02:
            spawn_enemy()
            
        # 3. 敵人移動
        for eid, e in gameState["enemies"].items():
            e['y'] += e['speed']
            if e['y'] > HEIGHT:
                e['y'] = -50 # 簡單循環
                e['x'] = random.randint(20, WIDTH-20)

        # 4. 廣播狀態 (State Sync)
        # 降低廣播頻率到 30FPS (0.033s) 或 20FPS (0.05s) 可以進一步減輕負擔
        socketio.emit('state_update', gameState)
        
        # 控制迴圈速度 (約 60 FPS)
        elapsed = time.time() - start_time
        sleep_time = max(0, 0.016 - elapsed)
        eventlet.sleep(sleep_time)

if __name__ == '__main__':
    # 啟動背景執行緒
    eventlet.spawn(game_loop)
    # 啟動 Server
    socketio.run(app, host='0.0.0.0', port=10000)
