import math
import time

def check_collision(obj1, obj2, r1_override=None, r2_override=None):
    """基本圓形碰撞 (Player/Enemy/Item)"""
    x1, y1 = (obj1.x, obj1.y) if hasattr(obj1, 'x') else (obj1['x'], obj1['y'])
    x2, y2 = (obj2.x, obj2.y) if hasattr(obj2, 'x') else (obj2['x'], obj2['y'])
    r1 = r1_override if r1_override is not None else (obj1.size / 2 if hasattr(obj1, 'size') else 10)
    r2 = r2_override if r2_override is not None else (obj2.size / 2 if hasattr(obj2, 'size') else 10)
    
    dist_sq = (x1 + r1 - (x2 + r2))**2 + (y1 + r1 - (y2 + r2))**2
    return dist_sq < (r1 + r2)**2

def check_circle_rect_collision(circle, rect):
    """圓形與矩形碰撞 (用於牆壁阻擋)"""
    # 找到矩形上最接近圓心的點
    closest_x = max(rect.x, min(circle.x + circle.size/2, rect.x + rect.width))
    closest_y = max(rect.y, min(circle.y + circle.size/2, rect.y + rect.height))
    
    # 計算該點與圓心的距離
    dist_x = (circle.x + circle.size/2) - closest_x
    dist_y = (circle.y + circle.size/2) - closest_y
    
    return (dist_x**2 + dist_y**2) < (circle.size/2)**2

def compress_state(state):
    """將遊戲狀態轉換為精簡 JSON"""
    compressed = {
        "players": {}, "enemies": {}, "bullets": [], 
        "items": [], "walls": [], "w": state["warning_active"]
    }
    
    for pid, p in state["players"].items():
        compressed["players"][pid] = {
            "x": int(p.x), "y": int(p.y), "skin": p.skin, "name": p.name,
            "hp": max(0, int(p.hp)), "max_hp": int(p.max_hp), "score": int(p.score),
            "charge": p.charge, "c": p.color, "invincible": p.is_invincible(),
            "w_icon": p.weapon_icon,
            "wall_cd": max(0, int(p.get_wall_cd())) # 傳送牆壁冷卻秒數
        }
    
    for eid, e in state["enemies"].items():
        compressed["enemies"][eid] = {
            "x": int(e.x), "y": int(e.y), "type": e.type, "size": e.size, 
            "hp": max(0, int(e.hp)), "max_hp": int(e.max_hp)
        }
        
    for b in state["bullets"]:
        compressed["bullets"].append({"x": int(b.x), "y": int(b.y), "owner": b.owner_type, "s": int(b.size)})
        
    for i in state["items"]:
        compressed["items"].append({"x": int(i.x), "y": int(i.y), "type": i.item_type})

    for w in state["walls"]:
        compressed["walls"].append({
            "x": int(w.x), "y": int(w.y), "w": w.width, "l": w.height,
            "hp": int(w.hp), "max_hp": 100
        })
        
    return compressed
