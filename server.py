# server.py (V5.1 大合體版)
import socketio, uvicorn, asyncio, random, time, math, uuid
from fastapi import FastAPI

# --- 1. 設定與參數 ---
MAP_WIDTH, MAP_HEIGHT = 600, 500
MAX_ENEMIES = 5
INVINCIBLE_TIME, FIRE_COOLDOWN, PLAYER_LIVES = 1.5, 0.15, 5

CELL_CONFIG = {
    1: {"name": "Soldier", "hp": 5, "speed": 8, "bullet_speed": 7, "damage": 1, "color": "#50fa7b"},
    2: {"name": "Scout", "hp": 3, "speed": 12, "bullet_speed": 10, "damage": 1, "color": "#8be9fd"},
    3: {"name": "Tank", "hp": 8, "speed": 5, "bullet_speed": 6, "damage": 2, "color": "#ff5555"}
}

VIRUS_CONFIG = {
    1: {"hp": 3, "speed": 3, "size": 50, "score": 10, "prob": 0.7, "drop_rate": 0.1, "attack": {"mode": "single", "damage": 1, "bullet_speed": 8, "fire_rate": 0.005}},
    2: {"hp": 1, "speed": 7, "size": 25, "score": 25, "prob": 0.2, "drop_rate": 0.15, "attack": {"mode": "single", "damage": 1, "bullet_speed": 15, "fire_rate": 0.01}},
    3: {"hp": 15, "speed": 2, "size": 95, "score": 100, "prob": 0.1, "drop_rate": 0.5, "attack": {"mode": "double", "damage": 2, "bullet_speed": 6, "fire_rate": 0.02}},
    999: {"hp": 500, "speed": 5, "size": 230, "score": 1000, "drop_rate": 1.0, "kill_bonus": 200}
}

WEAPON_CONFIG = {
    "default": {"damage": 1, "speed": 10, "count": 1, "type": "linear", "angles": [-90], "size": 5, "hits": 1, "bounce": 0},
    "spread_lv1": {"count": 3, "damage": 1, "speed": 10, "size": 5, "angles": [-20, -90, -160], "type": "linear", "color": "#ffff00"},
    "spread_lv2": {"count": 5, "damage": 1, "speed": 10, "size": 5, "angles": [-20, -60, -90, -120, -160], "type": "linear", "color": "#ffcc00"},
    "ricochet_lv1": {"count": 1, "damage": 1, "bounce_damage": 0.3, "speed": 8, "angles": [-90], "type": "bounce", "bounce": 3, "size": 6, "color": "#00ffff"},
    "ricochet_lv2": {"count": 1, "damage": 1, "bounce_damage": 0.3, "speed": 8, "angles": [-90], "type": "bounce", "bounce": 5, "size": 6, "color": "#0088ff"},
    "arc_lv1": {"damage": 2, "speed": 6, "fire_rate_mult": 0.6, "type": "arc", "angles": "random_45_135", "color": "#ff00ff"},
    "arc_lv2": {"damage": 3, "speed": 6, "fire_rate_mult": 0.6, "type": "arc", "angles": "random_45_135", "color": "#aa00aa"}
}

# --- 2. 輔助函式 ---
def check_collision(obj1, obj2, r1_override=None, r2_override=None):
    x1 = obj1.x if hasattr(obj1, 'x') else obj1['x']
    y1 = obj1.y if hasattr(obj1, 'y') else obj1['y']
    size1 = obj1.size if hasattr(obj1, 'size') else obj1.get('size', 20)
    x2 = obj2.x if hasattr(obj2, 'x') else obj2['x']
    y2 = obj2.y if hasattr(obj2, 'y') else obj2['y']
    size2 = obj2.size if hasattr(obj2, 'size') else obj2.get('size', 20)
    r1, r2 = (r1_override if r1_override is not None else size1/2), (r2_override if r2_override is not None else size2/2)
    return ((x1+r1)-(x2+r2))**2 + ((y1+r1)-(y2+r2))**2 < (r1+r2)**2 * 0.8

# --- 3. 遊戲物件 ---
class GameObject:
    def __init__(self, x, y, size): self.x, self.y, self.size = x, y, size

class Item(GameObject):
    def __init__(self, x, y, item_type):
        super().__init__(x, y, 20)
        self.id, self.item_type, self.dy = str(uuid.uuid4()), item_type, 2
    def update(self): self.y += self.dy; return -50 <= self.y <= MAP_HEIGHT + 50

class Bullet(GameObject):
    def __init__(self, x, y, owner_id, owner_type, config, angle_deg=None):
        super().__init__(x, y, config.get("size", 5))
        self.owner_id, self.owner_type, self.damage, self.color = owner_id, owner_type, config.get("damage", 1), config.get("color")
        self.speed, self.b_type = config.get("speed", 10), config.get("type", "linear")
        angle_rad = math.radians(angle_deg if angle_deg is not None else -90)
        self.dx, self.dy = math.cos(angle_rad) * self.speed, math.sin(angle_rad) * self.speed
        self.bounce_left, self.dist_traveled, self.ignore_list = config.get("bounce", 0), 0, []
        if self.b_type == "arc": self.curve_dir = random.choice([-1, 1])

    def update(self):
        if self.b_type == "arc":
            self.x += self.dx + (math.cos(time.time() * 5) * 5 * self.curve_dir)
            self.y += self.dy
        else: self.x, self.y = self.x + self.dx, self.y + self.dy
        self.dist_traveled += self.speed
        if self.b_type == "bounce" and self.bounce_left > 0:
            if self.x <= 0 or self.x >= MAP_WIDTH: self.dx *= -1; self.bounce_left -= 1
            elif self.y <= 0: self.dy *= -1; self.bounce_left -= 1
        return self.dist_traveled <= 9999 and -50 <= self.x <= MAP_WIDTH + 50 and -50 <= self.y <= MAP_HEIGHT + 50

    def handle_hit(self, target):
        if self.b_type == "bounce" and self.bounce_left > 0:
            self.damage *= 0.3; self.bounce_left -= 1
            if target: self.ignore_list.append(target)
            self.dx, self.dy = -self.dx, -self.dy
            self.x, self.y = self.x + self.dx * 2, self.y + self.dy * 2
            return True
        return False

class Player(GameObject):
    def __init__(self, sid, name, skin_id):
        stats = CELL_CONFIG[skin_id]
        super().__init__(random.randint(100, 500), 400, 30)
        self.sid, self.name, self.skin, self.stats = sid, name, skin_id, stats
        self.hp = self.max_hp = stats["hp"] * PLAYER_LIVES
        self.lives_count, self.color, self.score, self.charge, self.hit_accumulated = PLAYER_LIVES, stats["color"], 0, 0, 0
        self.last_hit_time, self.last_shot_time, self.last_skill_time = 0, 0, 0
        self.weapon_level, self.weapon_type, self.weapon_icon = 0, "default", "🔥"

    def is_invincible(self): return (time.time() - self.last_hit_time) < INVINCIBLE_TIME
    def take_damage(self, amount):
        if self.is_invincible(): return False
        self.hp -= amount
        self.last_hit_time = time.time()
        if self.hp <= 0: self.respawn()
        elif math.ceil(self.hp / self.stats["hp"]) < self.lives_count: self.reset_weapon(); self.lives_count = math.ceil(self.hp / self.stats["hp"])
        return True
    def respawn(self):
        self.x, self.y, self.hp, self.lives_count, self.score, self.charge = random.randint(100, 500), 400, self.max_hp, PLAYER_LIVES, int(self.score/2), 0
        self.reset_weapon()
    def reset_weapon(self): self.weapon_type, self.weapon_level, self.weapon_icon = "default", 0, "🔥"
    def apply_item(self, itype):
        base = itype.split('_')[0]
        if self.weapon_type.startswith(base): self.weapon_level = min(2, self.weapon_level + 1)
        else: self.weapon_type, self.weapon_level = base, 1
        self.weapon_icon = {"spread": "🔱", "ricochet": "⚡", "arc": "🌙", "default": "🔥"}.get(base, "🔥")
    def get_shoot_config(self):
        key = "default" if self.weapon_type == "default" else f"{self.weapon_type}_lv{self.weapon_level}"
        return WEAPON_CONFIG.get(key, WEAPON_CONFIG["default"])

class Enemy(GameObject):
    def __init__(self, type_id):
        stats = VIRUS_CONFIG[type_id]
        super().__init__(random.randint(0, MAP_WIDTH - stats["size"]), random.randint(-100, 0), stats["size"])
        self.id, self.type, self.hp, self.max_hp, self.speed, self.score, self.prob_drop = str(uuid.uuid4()), type_id, stats["hp"], stats["hp"], stats["speed"], stats["score"], stats["drop_rate"]
        self.move_timer = 0
    def update(self):
        if self.type != 999:
            self.y += self.speed * 0.5; self.move_timer += 1
            if self.move_timer > 30: self.x += random.choice([-20, 20, 0]); self.move_timer = 0
            self.x = max(0, min(MAP_WIDTH - self.size, self.x))
            if self.y > MAP_HEIGHT: self.y = -50

# --- 4. 伺服器主邏輯 ---
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
app = FastAPI()
sio_app = socketio.ASGIApp(sio, app)

class GameState:
    def __init__(self):
        self.players, self.enemies, self.bullets, self.items, self.skill_objects, self.walls = {}, {}, [], [], [], []
        self.warning_active = False

gs = GameState()
game_vars = {"boss_phase": "initial", "phase_start_time": 0, "elite_kill_count": 0, "target_kills": 5, "boss_score_threshold": 500}

async def game_loop():
    while True:
        curr, sfx_buffer = time.time(), []
        gs.skill_objects = [s for s in gs.skill_objects if curr - s["start_time"] <= s["duration"]]
        
        # Boss 控制與普通怪物生成
        max_score = max([p.score for p in gs.players.values()] or [0])
        if game_vars["boss_phase"] == "initial" and max_score >= game_vars["boss_score_threshold"]:
            game_vars["boss_phase"] = "countdown"; game_vars["phase_start_time"] = curr
        elif game_vars["boss_phase"] == "countdown" and curr - game_vars["phase_start_time"] > 25:
            game_vars["boss_phase"] = "warning"; game_vars["phase_start_time"] = curr; gs.warning_active = True; sfx_buffer.append({'type': 'boss_coming'})
        elif game_vars["boss_phase"] == "warning" and curr - game_vars["phase_start_time"] > 5:
            boss = Enemy(999); boss.x, boss.y = 150, -300; gs.enemies["THE_BOSS"] = boss; game_vars["boss_phase"] = "boss_active"; gs.warning_active = False

        if len(gs.enemies) < MAX_ENEMIES and game_vars["boss_phase"] != "boss_active":
            rv = random.random(); vt = 3 if rv < 0.15 else (2 if rv < 0.4 else 1)
            e = Enemy(vt); gs.enemies[e.id] = e

        # 更新與碰撞
        gs.items = [i for i in gs.items if i.update()]
        for pid, p in gs.players.items():
            for it in gs.items[:]:
                if check_collision(p, it): p.apply_item(it.item_type); gs.items.remove(it); sfx_buffer.append({'type': 'powerup'})

        active_bullets = []
        for b in gs.bullets:
            if not b.update(): continue
            hit = False
            if b.owner_type == 'player':
                for eid, en in list(gs.enemies.items()):
                    if en not in b.ignore_list and check_collision(b, en):
                        en.hp -= b.damage; hit = True; sfx_buffer.append({'type': 'enemy_hitted'})
                        if not b.handle_hit(en): break
                        if en.hp <= 0:
                            if eid in gs.enemies: del gs.enemies[eid]
                            if random.random() < en.prob_drop: gs.items.append(Item(en.x, en.y, random.choice(["spread", "ricochet", "arc"])))
                            if b.owner_id in gs.players: gs.players[b.owner_id].score += en.score
            else:
                for pid, pl in gs.players.items():
                    if not pl.is_invincible() and check_collision(b, pl, r2_override=15):
                        pl.take_damage(b.damage); hit = True; sfx_buffer.append({'type': 'character_hitted'}); break
            if not hit or (hit and b.b_type == "bounce"): active_bullets.append(b)
        gs.bullets = active_bullets

        # 發送狀態
        state_data = {
            "players": {pid: {"x": int(p.x), "y": int(p.y), "skin": p.skin, "name": p.name, "hp": max(0, int(p.hp)), "max_hp": int(p.max_hp), "score": int(p.score), "charge": p.charge, "c": p.color, "invincible": p.is_invincible(), "w_icon": p.weapon_icon} for pid, p in gs.players.items()},
            "enemies": {eid: {"x": int(e.x), "y": int(e.y), "type": e.type, "size": e.size, "hp": max(0, int(e.hp)), "max_hp": int(e.max_hp)} for eid, e in gs.enemies.items()},
            "bullets": [{"x": int(b.x), "y": int(b.y), "owner": b.owner_type, "c": b.color, "s": int(b.size)} for b in gs.bullets],
            "items": [{"x": int(i.x), "y": int(i.y), "type": i.item_type} for i in gs.items],
            "skill_objects": [{"x": int(s["x"]), "y": int(s["y"]), "skin": s["skin"]} for s in gs.skill_objects],
            "walls": [{"x": int(w.x), "y": int(w.y), "w": int(w.w), "h": int(w.h), "hp": int(w.hp), "m_hp": int(w.max_hp)} for w in gs.walls],
            "w": gs.warning_active
        }
        await sio.emit('state_update', state_data)
        for sfx in list({v['type']: v for v in sfx_buffer}.values()): await sio.emit('sfx', sfx)
        await asyncio.sleep(1/30)

@app.on_event("startup")
async def startup_event(): asyncio.create_task(game_loop())

@sio.event
async def join_game(sid, data): gs.players[sid] = Player(sid, data.get("name", "Cell")[:8], random.randint(1, 3))

@sio.event
async def move(sid, data):
    if sid in gs.players:
        p = gs.players[sid]; dx, dy = data.get('dx', 0), data.get('dy', 0)
        p.x = max(0, min(MAP_WIDTH-30, p.x + dx*p.stats['speed'])); p.y = max(0, min(MAP_HEIGHT-30, p.y + dy*p.stats['speed']))

@sio.event
async def shoot(sid):
    if sid in gs.players:
        p = gs.players[sid]; curr = time.time(); w_conf = p.get_shoot_config()
        if curr - p.last_shot_time < (FIRE_COOLDOWN / w_conf.get("fire_rate_mult", 1.0)): return
        p.last_shot_time = curr
        if isinstance(w_conf["angles"], list):
            for ang in w_conf["angles"]: gs.bullets.append(Bullet(p.x+15, p.y, sid, "player", w_conf, angle_deg=ang))
        elif w_conf["angles"] == "random_45_135": gs.bullets.append(Bullet(p.x+15, p.y, sid, "player", w_conf, angle_deg=random.uniform(-135, -45)))

@sio.event
async def disconnect(sid):
    if sid in gs.players: del gs.players[sid]

if __name__ == "__main__": uvicorn.run(sio_app, host="0.0.0.0", port=8000)
