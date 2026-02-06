import math
import time

<<<<<<< HEAD
def check_collision(obj1, obj2, r1_override=None, r2_override=None):
    # 支援字典或物件屬性存取
    x1 = obj1.x if hasattr(obj1, 'x') else obj1['x']
    y1 = obj1.y if hasattr(obj1, 'y') else obj1['y']
    size1 = obj1.size if hasattr(obj1, 'size') else obj1.get('size', 20)
    
    x2 = obj2.x if hasattr(obj2, 'x') else obj2['x']
    y2 = obj2.y if hasattr(obj2, 'y') else obj2['y']
    size2 = obj2.size if hasattr(obj2, 'size') else obj2.get('size', 20)

    r1 = r1_override if r1_override is not None else size1 / 2
    r2 = r2_override if r2_override is not None else size2 / 2

    cx1, cy1 = x1 + r1, y1 + r1
    cx2, cy2 = x2 + r2, y2 + r2

    dist_sq = (cx1 - cx2) ** 2 + (cy1 - cy2) ** 2
    radius_sum_sq = (r1 + r2) ** 2
    return dist_sq < (radius_sum_sq * 0.8)

def get_distance(obj1, obj2):
    x1 = obj1.x if hasattr(obj1, 'x') else obj1['x']
    y1 = obj1.y if hasattr(obj1, 'y') else obj1['y']
    x2 = obj2.x if hasattr(obj2, 'x') else obj2['x']
    y2 = obj2.y if hasattr(obj2, 'y') else obj2['y']
    return math.sqrt((x1-x2)**2 + (y1-y2)**2)

def compress_state(state):
    # 將複雜的物件轉為前端需要的精簡 JSON
    compressed = {
        "players": {}, "enemies": {}, "bullets": [], 
        "items": [], "skill_objects": [], "w": state["warning_active"]
    }
    
    for pid, p in state["players"].items():
        compressed["players"][pid] = {
            "x": int(p.x), "y": int(p.y), "skin": p.skin, "name": p.name,
            "hp": max(0, int(p.hp)), "max_hp": int(p.max_hp), "score": int(p.score),
            "charge": p.charge, "c": p.color,
            "invincible": p.is_invincible(),
            "w_icon": p.weapon_icon # 用於前端顯示 FIRE 鍵圖騰
        }
    
    for eid, e in state["enemies"].items():
        compressed["enemies"][eid] = {
            "x": int(e.x), "y": int(e.y), "type": e.type,
            "size": e.size, "hp": max(0, int(e.hp)), "max_hp": int(e.max_hp)
        }
        
    for b in state["bullets"]:
        compressed["bullets"].append({
            "x": int(b.x), "y": int(b.y), "owner": b.owner_type, 
            "c": getattr(b, 'color', None), "s": int(b.size)
        })
        
    for i in state["items"]:
        compressed["items"].append({
            "x": int(i.x), "y": int(i.y), "type": i.item_type
=======
# --- Helper Functions (內部使用) ---
def get_obj_info(obj):
    """
    統一從 物件(Object) 或 字典(Dict) 中提取 x, y, size。
    回傳: (x, y, size, center_x, center_y)
    """
    # 判斷是 Object 還是 Dict 來取得屬性
    if isinstance(obj, dict):
        x = obj.get('x', 0)
        y = obj.get('y', 0)
        size = obj.get('size', 20)
        width = obj.get('width', size)   # 預留給非正方形物件
        height = obj.get('height', size) # 預留給非正方形物件
    else:
        x = getattr(obj, 'x', 0)
        y = getattr(obj, 'y', 0)
        size = getattr(obj, 'size', 20)
        width = getattr(obj, 'width', size)
        height = getattr(obj, 'height', size)

    # 計算中心點 (假設 x, y 是左上角)
    cx = x + width / 2
    cy = y + height / 2
    
    return x, y, size, cx, cy

# --- Core Functions ---

def check_collision(obj1, obj2, hit_ratio=0.8):
    """
    圓形碰撞檢測
    :param hit_ratio: 碰撞箱係數 (0.8 表示判定範圍是圖片大小的 80%)
    """
    _, _, size1, cx1, cy1 = get_obj_info(obj1)
    _, _, size2, cx2, cy2 = get_obj_info(obj2)

    # 半徑計算 (基於 size * hit_ratio)
    r1 = (size1 / 2) * hit_ratio
    r2 = (size2 / 2) * hit_ratio

    dist_sq = (cx1 - cx2) ** 2 + (cy1 - cy2) ** 2
    radius_sum_sq = (r1 + r2) ** 2
    
    return dist_sq < radius_sum_sq

def get_distance(obj1, obj2):
    """
    計算兩個物件「中心點」之間的距離
    """
    _, _, _, cx1, cy1 = get_obj_info(obj1)
    _, _, _, cx2, cy2 = get_obj_info(obj2)
    
    return math.sqrt((cx1 - cx2)**2 + (cy1 - cy2)**2)

def compress_state(state):
    """
    將遊戲狀態壓縮為 JSON 格式傳給前端
    優化：加入 angle (角度) 支援，並統一處理整數化
    """
    compressed = {
        "players": {}, 
        "enemies": {}, 
        "bullets": [], 
        "items": [], 
        "skill_objects": [], 
        "w": state.get("warning_active", False)
    }
    
    # --- Players ---
    for pid, p in state["players"].items():
        compressed["players"][pid] = {
            "x": int(p.x),
            "y": int(p.y),
            "skin": p.skin,
            "name": p.name,
            "hp": max(0, int(p.hp)),
            "max_hp": int(p.max_hp),
            "score": int(p.score),
            "charge": round(p.charge, 1), # 保留一位小數用於 UI 顯示
            "c": p.color,
            "invincible": p.is_invincible(),
            "w_icon": getattr(p, 'weapon_icon', 'default'),
            "face": getattr(p, 'facing_right', True) # 如果有人物朝向，可加這個
        }
    
    # --- Enemies ---
    for eid, e in state["enemies"].items():
        compressed["enemies"][eid] = {
            "x": int(e.x),
            "y": int(e.y),
            "type": e.type,
            "size": int(e.size),
            "hp": max(0, int(e.hp)),
            "max_hp": int(e.max_hp),
            # 如果敵人有旋轉 (如 Boss)，這裡可以加 angle
        }
        
    # --- Bullets ---
    for b in state["bullets"]:
        bullet_data = {
            "x": int(b.x),
            "y": int(b.y),
            "owner": getattr(b, 'owner_type', 'enemy'),
            "c": getattr(b, 'color', '#FFF'),
            "s": int(b.size)
        }
        # 如果子彈有角度 (例如長條形雷射或指向性子彈)，前端需要知道角度來旋轉圖片
        if hasattr(b, 'angle'):
             bullet_data["a"] = int(b.angle) # "a" for angle, save bytes
             
        compressed["bullets"].append(bullet_data)
        
    # --- Items ---
    for i in state["items"]:
        compressed["items"].append({
            "x": int(i.x),
            "y": int(i.y),
            "type": i.item_type
        })

    # --- Skill Objects ---
    for s in state["skill_objects"]:
        # 兼容字典或物件
        sx = s['x'] if isinstance(s, dict) else s.x
        sy = s['y'] if isinstance(s, dict) else s.y
        skin = s['skin'] if isinstance(s, dict) else getattr(s, 'skin', 'default')
        compressed["skill_objects"].append({
            "x": int(sx), 
            "y": int(sy), 
            "skin": skin
>>>>>>> cf61c11d6df7b5141882f1c3ab7a2e9f88b1a6d6
        })

    # Skill Objects (保留原本邏輯)
    for s in state["skill_objects"]:
         compressed["skill_objects"].append({"x": int(s["x"]), "y": int(s["y"]), "skin": s["skin"]})

    return compressed
