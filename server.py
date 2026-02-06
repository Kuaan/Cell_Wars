# server.py
import socketio
import uvicorn
from fastapi import FastAPI
import asyncio
import random
import time
import math

# 引入模組 (確保與前面的檔案一致)
from config import *
from utils import compress_state, check_collision
from game_objects import Player, Enemy, Bullet, Item

# --- 初始化 ---
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
app = FastAPI()
sio_app = socketio.ASGIApp(sio, app)

# --- 全域狀態 ---
game_vars = {
    "boss_phase": "initial", 
    "phase_start_time": 0,
    "elite_kill_count": 0,
    "target_kills": 5,        
    "boss_score_threshold": 500 
}

class GameState:
    def __init__(self):
        self.players = {}
        self.enemies = {}
        self.bullets = []
        self.items = []
        self.skill_objects = [] # 暫時保留，若未來要擴充技能系統可用
        self.warning_active = False

gs = GameState()

# --- Helper: 穩定 FPS ---
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
            # 如果落後太多，直接重置時間軸，避免快進
            self.next_tick = now + self.frame_duration

def spawn_boss():
    # 確保只有一隻 Boss
    if any(e.type == 999 for e in gs.enemies.values()): return

    boss = Enemy(999) # 999 is Boss ID
    gs.enemies[boss.id] = boss
    game_vars["boss_phase"] = "boss_active"
    gs.warning_active = False
    print("BOSS SPAWNED!")

def spawn_item(x, y, forced_type=None):
    types = ["spread", "ricochet", "arc", "heal", "spread", "ricochet"] # 加權隨機
    itype = forced_type if forced_type else random.choice(types)
    gs.items.append(Item(x, y, itype))

# --- 主遊戲迴圈 ---
async def game_loop():
    timer = LoopTimer(fps=FPS) # 使用 config.py 的 FPS (60)
    print(f"Game Loop Started. FPS: {FPS}")

    while True:
        curr = time.time()
        sfx_buffer = [] # 音效緩衝區，避免一幀發送太多重複音效

        # 1. 玩家連線與無效玩家清理
        # (SocketIO 會自動處理斷線，這裡主要處理邏輯層面)
        
        # 2. 敵人生成與 Boss 狀態機
        max_score = max([p.score for p in gs.players.values()] or [0])

        if game_vars["boss_phase"] == "initial":
            if max_score >= game_vars["boss_score_threshold"]:
                game_vars["boss_phase"] = "countdown"
                game_vars["phase_start_time"] = curr

        elif game_vars["boss_phase"] == "countdown":
            if curr - game_vars["phase_start_time"] > 20: # 20秒後警告
                game_vars["boss_phase"] = "warning"
                game_vars["phase_start_time"] = curr
                gs.warning_active = True
                sfx_buffer.append({'type': 'boss_coming'})

        elif game_vars["boss_phase"] == "warning":
            if curr - game_vars["phase_start_time"] > 5: # 5秒後生成
                spawn_boss()
                sfx_buffer.append({'type': 'boss_coming'})

        # 一般怪物生成
        if len(gs.enemies) < MAX_ENEMIES and game_vars["boss_phase"] != "boss_active":
            if random.random() < 0.05: # 每幀 5% 機率生成，直到上限
                rand_val = random.random()
                v_type = 3 if rand_val < 0.1 else (2 if rand_val < 0.3 else 1)
                enemy = Enemy(v_type)
                gs.enemies[enemy.id] = enemy

        # 3. 道具更新
        gs.items = [i for i in gs.items if i.update()]
        # 玩家吃道具
        for pid, player in gs.players.items():
            for item in gs.items[:]:
                if check_collision(player, item):
                    player.apply_item(item.item_type)
                    gs.items.remove(item)
                    sfx_buffer.append({'type': 'powerup'})

        # 4. 子彈移動與碰撞 (核心重構)
        active_bullets = []
        for b in gs.bullets:
            still_alive = b.update()
            if not still_alive: continue
            
            hit = False
            
            # A. 玩家子彈 -> 打怪
            if b.owner_type == 'player':
                for eid, enemy in list(gs.enemies.items()):
                    if eid in b.ignore_list: continue # 彈射忽略列表

                    if check_collision(b, enemy):
                        enemy.hp -= b.damage
                        hit = True
                        sfx_buffer.append({'type': 'enemy_hitted'})
                        
                        # 處理彈射邏輯 (如果成功彈射，handle_hit 回傳 True)
                        bullet_survives = b.ricochet(eid, gs.enemies)
                        
                        # 充能邏輯
                        if b.owner_id in gs.players:
                            p = gs.players[b.owner_id]
                            p.hit_accumulated += 1
                            if p.hit_accumulated >= 20:
                                p.hit_accumulated = 0
                                p.charge = min(3, p.charge + 1)

                        # 死亡邏輯
                        if enemy.hp <= 0:
                            if eid in gs.enemies: del gs.enemies[eid]
                            if random.random() < enemy.prob_drop:
                                spawn_item(enemy.x, enemy.y)
                            
                            # 加分
                            if b.owner_id in gs.players:
                                bonus = VIRUS_CONFIG[999]["kill_bonus"] if enemy.type == 999 else 0
                                gs.players[b.owner_id].score += enemy.score + bonus
                                
                            # Boss/Elite 死亡狀態更新
                            if enemy.type == 999:
                                game_vars["boss_phase"] = "initial" # Reset loop
                                game_vars["boss_score_threshold"] += 1000 # 下次更難
                                sfx_buffer.append({'type': 'win'}) # 或是 boss_die

                        if not bullet_survives: break # 子彈撞到就消失 (除非彈射成功)

            # B. 怪物子彈 -> 打人
            else:
                for pid, player in gs.players.items():
                    if player.is_invincible(): continue
                    # 玩家判定稍微寬鬆一點 (Hitbox 縮小)
                    if check_collision(b, player, r2_override=10):
                        player.take_damage(b.damage)
                        hit = True
                        sfx_buffer.append({'type': 'character_hitted'})
                        break # 一顆子彈只能打一個人

            # 如果沒擊中，或者擊中後依然存活(彈射)，則保留
            # 注意：b.ricochet() 已經在上面處理了存活邏輯
            if not hit:
                active_bullets.append(b)
            elif hit and b.b_type == "bounce" and b.bounce_left >= 0:
                 active_bullets.append(b) # 彈射成功的子彈繼續保留

        gs.bullets = active_bullets

        # 5. 怪物行為 (移動與射擊)
        for eid, enemy in list(gs.enemies.items()):
            alive = enemy.update() # Boss 或一般怪的移動邏輯
            if not alive:
                del gs.enemies[eid]
                continue
            
            # Boss 射擊邏輯 (簡單版)
            if enemy.type == 999:
                 if random.random() < 0.05: # Boss 射速
                    # 8方位射擊
                    for angle in range(0, 360, 45):
                        b = Bullet(
                            enemy.x + enemy.size/2, enemy.y + enemy.size/2, 
                            "boss", "enemy", 
                            {"damage":1, "speed":5, "size":10, "color": "#ff0000"}, 
                            angle_deg=angle
                        )
                        gs.bullets.append(b)

            # 碰撞傷害 (撞人)
            for pid, player in gs.players.items():
                if player.is_invincible(): continue
                # 簡單判定：距離過近
                if check_collision(player, enemy, r1_override=15):
                    player.take_damage(1)
                    sfx_buffer.append({'type': 'character_hitted'})

        # 6. 廣播狀態
        # 為了節省頻寬，不需要每幀廣播，可累積幾幀發送一次 (若 FPS=60, 廣播率=20)
        # 這裡簡單起見每幀發送，若卡頓可改為計數器跳幀發送
        state_data = compress_state({
            "players": gs.players, 
            "enemies": gs.enemies, 
            "bullets": gs.bullets, 
            "items": gs.items, 
            "events": sfx_buffer # 把音效事件包進去
        })
        
        # 廣播
        await sio.emit('state_update', state_data)
        
        await timer.tick()

# --- SocketIO 事件 ---

@app.on_event("startup")
async def startup_event():
    # 啟動背景遊戲迴圈
    asyncio.create_task(game_loop())

@sio.event
async def join_game(sid, data):
    print(f"Player joining: {sid}")
    name = data.get("name", "Soldier")[:8]
    skin_type = data.get("skin", 1) # 前端選擇的皮膚
    if skin_type not in [1, 2, 3]: skin_type = 1
    
    gs.players[sid] = Player(sid, name, skin_type)
    # 回傳初始設定給玩家 (自己的 ID)
    await sio.emit('init_game', {'id': sid}, room=sid)

@sio.event
async def disconnect(sid):
    if sid in gs.players:
        del gs.players[sid]
        print(f"Player left: {sid}")

@sio.event
async def player_input(sid, data):
    # 接收前端的整合輸入包 {"dx": 0, "dy": 0, "fire": true, "angle": 90}
    # 這樣比分開的 move/shoot 事件更有效率
    if sid not in gs.players: return
    
    p = gs.players[sid]
    
    # 1. 移動
    dx = data.get('dx', 0)
    dy = data.get('dy', 0)
    # 簡單防作弊：限制速度向量長度 (或在 server 計算位置，client 只傳方向)
    # 這裡採用信任 Client 方向 * Server 速度
    if dx != 0 or dy != 0:
        # 正規化向量
        length = math.sqrt(dx*dx + dy*dy)
        if length > 0:
            dx, dy = dx/length, dy/length
            
        p.x += dx * p.stats['speed']
        p.y += dy * p.stats['speed']
        # 邊界限制
        p.x = max(0, min(MAP_WIDTH - p.size, p.x))
        p.y = max(0, min(MAP_HEIGHT - p.size, p.y))

    # 2. 射擊
    if data.get('fire', False):
        new_bullets = p.shoot() # 使用 Player 內部的冷卻與武器邏輯
        if new_bullets:
            gs.bullets.extend(new_bullets)

@sio.event
async def use_skill(sid):
    # 暫時保留
    pass

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
