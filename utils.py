# utils.py
import math
import time

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
        })

    # Skill Objects (保留原本邏輯)
    for s in state["skill_objects"]:
         compressed["skill_objects"].append({"x": int(s["x"]), "y": int(s["y"]), "skin": s["skin"]})

    return compressed
