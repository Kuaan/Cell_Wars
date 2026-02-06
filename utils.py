# utils.py
import math

def check_collision(obj1, obj2, r1_override=None, r2_override=None):
    """
    通用圓形碰撞檢測
    """
    # 為了效能，優先讀取屬性，若無則讀取字典
    x1 = getattr(obj1, 'x', obj1.get('x', 0))
    y1 = getattr(obj1, 'y', obj1.get('y', 0))
    # 如果物件有 radius 屬性優先使用，否則用 size / 2
    r1 = r1_override if r1_override is not None else getattr(obj1, 'radius', obj1.get('size', 20) / 2)

    x2 = getattr(obj2, 'x', obj2.get('x', 0))
    y2 = getattr(obj2, 'y', obj2.get('y', 0))
    r2 = r2_override if r2_override is not None else getattr(obj2, 'radius', obj2.get('size', 20) / 2)

    # 距離平方計算 (比開根號快)
    dist_sq = (x1 - x2) ** 2 + (y1 - y2) ** 2
    
    # 碰撞判定：距離 < 半徑之和
    # * 0.8 是為了讓判定稍微寬鬆一點(Hitbox比貼圖小)，手感較好
    radius_sum = (r1 + r2) * 0.8 
    return dist_sq < (radius_sum ** 2)

def get_distance(x1, y1, x2, y2):
    return math.sqrt((x1 - x2)**2 + (y1 - y2)**2)

def compress_state(state):
    """
    將後端物件狀態壓縮為極簡 JSON 格式傳給前端
    優化原則：
    1. 只傳變動數據 (x, y, hp)
    2. 使用短 Key (p=players, b=bullets, e=enemies)
    3. 座標取整數 (像素風不需要小數點精度)
    """
    compressed = {
        "p": {},  # Players
        "e": [],  # Enemies (改為列表，減少ID傳輸，前端只負責渲染)
        "b": [],  # Bullets
        "i": [],  # Items
        "ev": state.get("events", []) # 用於播放音效或特殊特效的事件列表
    }
    
    # 壓縮玩家數據
    for pid, p in state["players"].items():
        compressed["p"][pid] = {
            "x": int(p.x),
            "y": int(p.y),
            "hp": int(p.hp),
            "s": int(p.score), # Score
            "sk": p.skin,      # Skin ID (前端根據 ID 決定顏色和貼圖)
            "iv": 1 if p.is_invincible() else 0, # Invincible status
            # 不傳送 max_hp, name, color，這些由前端在 "JOIN" 時紀錄一次即可
        }
    
    # 壓縮敵人數據
    for eid, e in state["enemies"].items():
        compressed["e"].append({
            "id": eid,       # 仍需要ID來處理擊中邏輯(如果是前端預測)
            "x": int(e.x),
            "y": int(e.y),
            "t": e.type,     # Type
            "hp": int(e.hp),
            "s": int(e.size) # Size (動態變化的話需要傳，否則可省略)
        })
        
    # 壓縮子彈數據 (流量大戶，盡量精簡)
    for b in state["bullets"]:
        bullet_data = {
            "x": int(b.x),
            "y": int(b.y),
            "t": 1 if b.owner_type == "player" else 0, # 1=玩家子彈, 0=怪物子彈
            "s": int(b.size)
        }
        # 只有特殊子彈才傳顏色，預設子彈前端自己畫
        if hasattr(b, 'color') and b.color:
            bullet_data["c"] = b.color
        
        compressed["b"].append(bullet_data)
        
    # 壓縮道具數據
    for i in state["items"]:
        compressed["i"].append({
            "x": int(i.x),
            "y": int(i.y),
            "t": i.item_type # 例如 "spread", "heal"
        })

    return compressed
