import socketio, uvicorn, asyncio, random, time, math
from fastapi import FastAPI
from config import *
from utils import compress_state, check_collision, check_circle_rect_collision, get_distance
from game_objects import Player, Enemy, Bullet, Item, Wall

sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
app = FastAPI()
sio_app = socketio.ASGIApp(sio, app)

class GameState:
    def __init__(self):
        self.players, self.enemies, self.bullets, self.items, self.walls = {}, {}, [], [], []
        self.warning_active = False

gs = GameState()

async def game_loop():
    while True:
        curr = time.time()
        
        # 1. 牆壁邏輯：處理消失與 CD 開始
        active_walls = []
        for w in gs.walls:
            if w.hp > 0 and (curr - w.start_time) < w.duration:
                active_walls.append(w)
            else:
                if w.owner_id in gs.players:
                    # 牆壁消失後，開始 20 秒冷卻
                    gs.players[w.owner_id].wall_available_at = curr + 20
        gs.walls = active_walls

        # 2. 敵人邏輯：生成、移動與射擊
        if len(gs.enemies) < MAX_ENEMIES:
            e = Enemy(random.choice([1, 1, 1, 2, 3]))
            gs.enemies[e.id] = e

        for eid, enemy in list(gs.enemies.items()):
            if not enemy.update(): 
                del gs.enemies[eid]
            elif enemy.hp <= 0:
                # --- 敵人死亡邏輯 ---
                # 1. 掉落道具判定
                if random.random() < enemy.prob_drop:
                    item_type = random.choice(['spread', 'ricochet', 'arc', 'heal'])
                    gs.items.append(Item(enemy.x, enemy.y, item_type))
                # 2. 移除敵人
                del gs.enemies[eid]
            else:
                # 敵人射擊 (向下 180 度隨機)
                atk = VIRUS_CONFIG[enemy.type]['attack']
                if random.random() < atk['fire_rate']:
                    angle = math.radians(random.uniform(20, 160))
                    gs.bullets.append(Bullet(enemy.x+enemy.size/2, enemy.y+enemy.size, eid, "enemy", 
                                      {"damage": atk['damage'], "speed": atk['bullet_speed']}, angle_rad=angle))

        # 3. 道具邏輯：下落與拾取
        active_items = []
        for item in gs.items:
            hit_player = False
            for pid, p in gs.players.items():
                if check_collision(item, p):
                    if item.item_type == 'heal':
                        p.hp = min(p.max_hp, p.hp + 20)
                    else:
                        p.apply_item(item.item_type)
                    hit_player = True; break
            
            if not hit_player and item.update():
                active_items.append(item)
        gs.items = active_items

        # 4. 子彈邏輯：移動與碰撞
        active_bullets = []
        for b in gs.bullets:
            hit_anything = False
            for w in gs.walls:
                if check_circle_rect_collision(b, w):
                    if b.owner_type != 'player': w.hp -= b.damage
                    hit_anything = True; break
            
            if hit_anything: continue 

            if b.owner_type == 'player':
                for eid, enemy in gs.enemies.items():
                    if check_collision(b, enemy):
                        enemy.hp -= b.damage
                        if enemy.hp <= 0 and b.owner_id in gs.players:
                            gs.players[b.owner_id].score += enemy.score # 給予擊殺者分數
                        hit_anything = True; break
            else:
                for pid, p in gs.players.items():
                    if not p.is_invincible() and check_collision(b, p):
                        p.take_damage(b.damage); hit_anything = True; break
            
            if not hit_anything and b.update(): active_bullets.append(b)
        gs.bullets = active_bullets

        # 5. 發送狀態
        state = compress_state({"players": gs.players, "enemies": gs.enemies, "bullets": gs.bullets, 
                               "items": gs.items, "walls": gs.walls, "warning_active": gs.warning_active})
        await sio.emit('state_update', state)
        await asyncio.sleep(1/30)

# --- 事件處理維持不變 ---
@sio.event
async def move(sid, data):
    if sid not in gs.players: return
    p = gs.players[sid]
    dx, dy = data.get('dx', 0) * p.stats['speed'], data.get('dy', 0) * p.stats['speed']
    future_p = type('Temp', (object,), {'x': p.x + dx, 'y': p.y + dy, 'size': p.size})
    if not any(check_circle_rect_collision(future_p, w) for w in gs.walls):
        p.x = max(0, min(MAP_WIDTH - p.size, p.x + dx))
        p.y = max(0, min(MAP_HEIGHT - p.size, p.y + dy))

@sio.event
async def shoot(sid, data):
    if sid in gs.players:
        p = gs.players[sid]
        angle = data.get('angle', -math.pi/2)
        w_conf = p.get_shoot_config()
        if time.time() - p.last_shot_time > FIRE_COOLDOWN:
            gs.bullets.append(Bullet(p.x+15, p.y, sid, "player", w_conf, angle_rad=angle))
            p.last_shot_time = time.time()

@sio.event
async def build_wall(sid, data):
    if sid in gs.players:
        p = gs.players[sid]
        if p.get_wall_cd() <= 0:
            angle = data.get('angle', 0)
            is_vertical = abs(math.cos(angle)) > abs(math.sin(angle))
            w_len, w_thick = p.size * 2.5, p.size
            new_wall = Wall(p.x - (w_thick/2 if is_vertical else w_len/2) + 15,
                            p.y - (w_len/2 if is_vertical else w_thick/2) + 15,
                            w_thick if is_vertical else w_len,
                            w_len if is_vertical else w_thick, sid)
            gs.walls.append(new_wall)
            p.wall_available_at = 9999999999 # 蓋住期間凍結 CD

@sio.event
async def join_game(sid, data):
    gs.players[sid] = Player(sid, data.get("name", "Cell")[:8], random.randint(1, 3))

@app.on_event("startup")
async def startup(): asyncio.create_task(game_loop())

if __name__ == "__main__":
    uvicorn.run(sio_app, host="0.0.0.0", port=8000)
