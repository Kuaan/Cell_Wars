#v3.7.3
import eventlet
import socketio
import random
import math
import time

# --- 1. 伺服器初始化 ---
sio = socketio.Server(cors_allowed_origins='*')
app = socketio.WSGIApp(sio)

# --- 2. 遊戲參數設定 (Constants) ---
MAP_WIDTH = 600
MAP_HEIGHT = 500
FPS = 60
TICK_RATE = 1 / FPS

# 角色數值設定
SKINS_STATS = {
    1: {'name': 'Soldier', 'hp': 100, 'speed': 5, 'bullet_speed': 7, 'damage': 10},
    2: {'name': 'Scout',   'hp': 70,  'speed': 7, 'bullet_speed': 10, 'damage': 6},
    3: {'name': 'Tank',    'hp': 150, 'speed': 3, 'bullet_speed': 6, 'damage': 20},
}

# --- 3. 遊戲狀態 (Global State) ---
players = {}       # { sid: { x, y, hp, score... } }
enemies = {}       # { id: { x, y, hp, type... } }
bullets = []       # [ { x, y, dx, dy, owner... } ]
skill_objects = [] # [ { x, y, type, owner, duration } ]

game_state = {
    'boss_active': False,
    'boss_id': None,
    'warning_trigger': False,
    'enemy_counter': 0  # 用於生成唯一 ID
}

# --- 4. 輔助函式 ---
def reset_game():
    """重置遊戲狀態"""
    global players, enemies, bullets, skill_objects, game_state
    players = {}
    enemies = {}
    bullets = []
    skill_objects = []
    game_state = {'boss_active': False, 'boss_id': None, 'warning_trigger': False, 'enemy_counter': 0}
    print("Game Reset")

def get_dist(o1, o2):
    return math.sqrt((o1['x'] - o2['x'])**2 + (o1['y'] - o2['y'])**2)

def spawn_enemy():
    """生成普通敵人"""
    if len(enemies) >= 8 or game_state['boss_active']: return
    
    eid = f"e_{game_state['enemy_counter']}"
    game_state['enemy_counter'] += 1
    
    # 隨機決定類型 (1:普通, 2:快速, 3:菁英)
    etype = random.choices([1, 2, 3], weights=[0.6, 0.3, 0.1])[0]
    
    hp_map = {1: 30, 2: 20, 3: 80}
    size_map = {1: 30, 2: 25, 3: 45}
    
    enemies[eid] = {
        'x': random.randint(20, MAP_WIDTH - 20),
        'y': -50, # 從上方進入
        'type': etype,
        'hp': hp_map[etype],
        'max_hp': hp_map[etype],
        'size': size_map[etype],
        'speed': random.uniform(1, 3) if etype != 2 else 5
    }

def spawn_boss():
    """生成 Boss"""
    if game_state['boss_active']: return
    
    game_state['warning_trigger'] = True
    sio.emit('state_update', {'w': True}) # 發送警告信號
    
    # 3秒後 Boss 出現
    def _boss_enter():
        time.sleep(3)
        game_state['warning_trigger'] = False
        game_state['boss_active'] = True
        bid = "BOSS"
        enemies[bid] = {
            'x': MAP_WIDTH / 2 - 40,
            'y': -100,
            'type': 999, # Boss 類型 ID
            'hp': 1000,
            'max_hp': 1000,
            'size': 80,
            'speed': 1,
            'phase': 1
        }
        game_state['boss_id'] = bid
        sio.emit('sfx', {'type': 'boss_coming'})
        print("BOSS SPAWNED")
        
    eventlet.spawn(_boss_enter)

# --- 5. 遊戲主迴圈 (核心邏輯) ---
def game_loop():
    while True:
        start_time = time.time()
        
        # A. 處理玩家
        # ------------------------
        for sid, p in players.items():
            if p['hp'] <= 0: continue
            
            # 移動
            p['x'] += p['dx'] * p['speed']
            p['y'] += p['dy'] * p['speed']
            
            # 邊界限制
            p['x'] = max(0, min(MAP_WIDTH - 30, p['x']))
            p['y'] = max(0, min(MAP_HEIGHT - 30, p['y']))
            
            # 無敵時間減少
            if p['invincible'] > 0:
                p['invincible'] -= 1

        # B. 處理敵人
        # ------------------------
        if not game_state['boss_active']:
            if random.random() < 0.03: spawn_enemy()
            
        dead_enemies = []
        for eid, e in enemies.items():
            # Boss 行為
            if e['type'] == 999:
                if e['y'] < 50: e['y'] += 1 # 進場
                else:
                    # 左右移動
                    e['x'] += math.sin(time.time()) * 2
                    # 隨機射擊
                    if random.random() < 0.05:
                        bullets.append({
                            'x': e['x'] + 40, 'y': e['y'] + 80,
                            'dx': random.uniform(-0.5, 0.5), 'dy': 1,
                            'speed': 5, 'owner': 'boss'
                        })
                        sio.emit('sfx', {'type': 'boss_shot'})
            else:
                # 普通敵人直走 + 簡單追蹤
                e['y'] += e['speed']
                if e['y'] > MAP_HEIGHT: dead_enemies.append(eid)
                
                # 簡單 AI 射擊
                if random.random() < 0.005:
                     bullets.append({
                        'x': e['x'] + e['size']/2, 'y': e['y'] + e['size'],
                        'dx': 0, 'dy': 1, 'speed': 4, 'owner': 'enemy'
                    })
                     sio.emit('sfx', {'type': 'enemy_nor_shot'})

        for eid in dead_enemies:
            if eid in enemies: del enemies[eid]

        # C. 處理子彈
        # ------------------------
        keep_bullets = []
        for b in bullets:
            b['x'] += b['dx'] * b['speed']
            b['y'] += b['dy'] * b['speed']
            
            # 移除出界的子彈
            if -50 < b['x'] < MAP_WIDTH + 50 and -50 < b['y'] < MAP_HEIGHT + 50:
                keep_bullets.append(b)
        bullets = keep_bullets

        # D. 碰撞檢測 (Collision)
        # ------------------------
        # 1. 子彈擊中判定
        bullets_to_remove = []
        
        for i, b in enumerate(bullets):
            hit = False
            
            # 玩家子彈擊中敵人
            if b['owner'] in players: 
                for eid, e in enemies.items():
                    if get_dist(b, e) < e['size']:
                        p_owner = players.get(b['owner'])
                        dmg = p_owner['damage'] if p_owner else 10
                        
                        e['hp'] -= dmg
                        hit = True
                        sio.emit('sfx', {'type': 'boss_hitted' if e['type']==999 else 'enemy_hitted'})
                        
                        # 敵人死亡
                        if e['hp'] <= 0:
                            if eid not in dead_enemies: # 防止重複刪除
                                if p_owner:
                                    p_owner['score'] += 100 if e['type'] == 999 else (e['type'] * 10)
                                    # 集氣機制
                                    p_owner['hit_accumulated'] += 1
                                    if p_owner['hit_accumulated'] >= 20 and p_owner['charge'] < 3:
                                        p_owner['charge'] += 1
                                        p_owner['hit_accumulated'] = 0
                                
                                if e['type'] == 999: # Boss 死掉
                                    game_state['boss_active'] = False
                                    game_state['boss_id'] = None
                                    del enemies[eid]
                                    break 
                                elif e['type'] == 3: # 菁英怪死掉觸發 Boss
                                    spawn_boss()
                                    del enemies[eid]
                                    break
                                else:
                                    del enemies[eid]
                                    break
                        break # 子彈只能打中一隻

            # 敵人子彈擊中玩家
            elif (b['owner'] == 'enemy' or b['owner'] == 'boss'):
                for pid, p in players.items():
                    if p['invincible'] <= 0 and get_dist(b, p) < 20: # 玩家半徑約 15-20
                        p['hp'] -= 10
                        p['invincible'] = 60 # 無敵 1 秒
                        hit = True
                        sio.emit('sfx', {'type': 'character_hitted'})
                        if p['hp'] <= 0:
                            sio.emit('game_over', {'score': p['score']}, room=pid)
                            del players[pid]
                            break
                        break

            if hit:
                bullets_to_remove.append(i)

        # 移除已碰撞的子彈 (倒序移除)
        for i in sorted(bullets_to_remove, reverse=True):
            if i < len(bullets):
                bullets.pop(i)

        # 2. 技能物件處理 (Slime 炸彈)
        current_time = time.time()
        active_skills = []
        for obj in skill_objects:
            if current_time < obj['end_time']:
                active_skills.append(obj)
                # 技能持續傷害判定
                for eid, e in list(enemies.items()):
                    if get_dist(obj, e) < 100: # 爆炸範圍
                        e['hp'] -= 2
                        if e['hp'] <= 0:
                            if eid in enemies: del enemies[eid]
            else:
                # 技能結束
                pass
        skill_objects = active_skills

        # E. 廣播狀態
        # ------------------------
        sio.emit('state_update', {
            'players': players,
            'enemies': enemies,
            'bullets': bullets,
            'skill_objects': skill_objects,
            'w': game_state['warning_trigger']
        })

        # 控制 FPS
        process_time = time.time() - start_time
        sleep_time = max(0, TICK_RATE - process_time)
        eventlet.sleep(sleep_time)

# 啟動遊戲迴圈
eventlet.spawn(game_loop)

# --- 6. SocketIO 事件處理 ---

@sio.event
def connect(sid, environ):
    print(f"Player connected: {sid}")

@sio.event
def join_game(sid, data):
    name = data.get('name', 'Unknown')
    # 預設 Skin 1
    stats = SKINS_STATS[1]
    
    players[sid] = {
        'name': name,
        'skin': 1,
        'x': MAP_WIDTH / 2,
        'y': MAP_HEIGHT - 50,
        'hp': stats['hp'],
        'max_hp': stats['hp'],
        'speed': stats['speed'],
        'damage': stats['damage'],
        'bullet_speed': stats['bullet_speed'],
        'score': 0,
        'dx': 0, 'dy': 0,
        'charge': 0,        # 技能集氣格數 (0-3)
        'hit_accumulated': 0, # 當前格數累積進度
        'invincible': 0
    }
    print(f"{name} joined the game.")

@sio.event
def move(sid, data):
    if sid in players:
        players[sid]['dx'] = data.get('dx', 0)
        players[sid]['dy'] = data.get('dy', 0)

@sio.event
def shoot(sid):
    if sid in players:
        p = players[sid]
        # 雖然前端已經預測播放聲音，後端還是發送事件給 "其他人" 聽
        # 但前端 v3.6.4 已過濾掉 'character_nor_shot'，所以這行主要是為了兼容性或觀戰者
        sio.emit('sfx', {'type': 'character_nor_shot'}) 
        
        bullets.append({
            'x': p['x'] + 15, 
            'y': p['y'],
            'dx': 0, 
            'dy': -1,
            'speed': p['bullet_speed'], # 使用角色特定彈速
            'owner': sid
        })

@sio.event
def use_skill(sid):
    if sid in players:
        p = players[sid]
        if p['charge'] >= 1:
            p['charge'] -= 1
            # 放置一個持續 3 秒的技能物件
            skill_objects.append({
                'x': p['x'],
                'y': p['y'] - 50,
                'skin': p['skin'],
                'owner': sid,
                'end_time': time.time() + 3.0
            })
            sio.emit('sfx', {'type': 'skill_slime'})

@sio.event
def disconnect(sid):
    if sid in players:
        del players[sid]
        print(f"Player disconnected: {sid}")

# --- 7. 啟動伺服器 ---
if __name__ == '__main__':
    print("Server running on port 10000...")
    eventlet.wsgi.server(eventlet.listen(('0.0.0.0', 10000)), app)
