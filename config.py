# config.py 5.2
import math

# --- 地圖與基礎設定 ---
MAP_WIDTH = 600
MAP_HEIGHT = 500
MAX_ENEMIES = 5
INVINCIBLE_TIME = 1.5  # 復活/受傷無敵時間
FIRE_COOLDOWN = 0.15   # 基礎射速限制
PLAYER_LIVES = 5       # 玩家命數

# --- 角色設定 (Cell) ---
CELL_CONFIG = {
    1: {"name": "Soldier", "hp": 5, "speed": 8, "bullet_speed": 7, "damage": 1, "color": "#50fa7b"},
    2: {"name": "Scout", "hp": 3, "speed": 12, "bullet_speed": 10, "damage": 1, "color": "#8be9fd"},
    3: {"name": "Tank", "hp": 8, "speed": 5, "bullet_speed": 6, "damage": 2, "color": "#ff5555"}
}

# --- 生物牆設定 (Cell Wall) ---
WALL_CONFIG = {
    "hp": 100,
    "duration": 25,     # 存在時間 (s)
    "cooldown": 20,     # 冷卻時間 (s)
    "length_mult": 2.5, # 長度倍率 (相對於玩家 size)
    "thickness": 10,    # 牆體厚度
    "color": "#ff79c6"  # 牆體顏色 (Pink)
}

# --- 怪物設定 (Virus) ---
# drop_rate: 掉落道具機率 (0~1)
VIRUS_CONFIG = {
    1: {"hp": 3, "speed": 3, "size": 50, "score": 10, "prob": 0.7, "drop_rate": 0.1,
        "attack": {"mode": "single", "damage": 1, "bullet_speed": 8, "fire_rate": 0.005}},
    2: {"hp": 1, "speed": 7, "size": 25, "score": 25, "prob": 0.2, "drop_rate": 0.15,
        "attack": {"mode": "single", "damage": 1, "bullet_speed": 15, "fire_rate": 0.01}},
    3: {"hp": 15, "speed": 2, "size": 95, "score": 100, "prob": 0.1, "drop_rate": 0.5, # 菁英怪高掉落
        "attack": {"mode": "double", "damage": 2, "bullet_speed": 6, "fire_rate": 0.02}},
    999: {"hp": 500, "speed": 5, "size": 230, "score": 1000, "drop_rate": 1.0, # Boss
          "kill_bonus": 200}
}

# --- 道具與子彈技能設定 ---
# 這裡定義你要求的詳細參數
WEAPON_CONFIG = {
    "default": {
        "damage": 1, "speed": 10, "count": 1, "type": "linear",
        "angles": [-90], # 向上
        "size": 5, "hits": 1, "bounce": 0
    },
    # 散射 (Spread)
    "spread_lv1": {
        "condition": "spread_item", "level": 1,
        "count": 3, "damage": 1, "speed": 10, "size": 5,
        "angles": [-20, -90, -160], # 玩家前方為90度(對應Y軸負方向)
        "type": "linear", "hits": 1, "bounce": 0, "color": "#ffff00"
    },
    "spread_lv2": {
        "condition": "spread_item", "level": 2,
        "count": 5, "damage": 1, "speed": 10, "size": 5,
        "angles": [-20, -60, -90, -120, -160],
        "type": "linear", "hits": 1, "bounce": 0, "color": "#ffcc00"
    },
    # 彈射 (Ricochet)
    "ricochet_lv1": {
        "condition": "ricochet_item", "level": 1,
        "count": 1, "damage": 1, "bounce_damage": 0.3, "speed": 8,
        "angles": [-90],
        "type": "bounce", "hits": 1, "bounce": 3, "size": 6, "color": "#00ffff"
    },
    "ricochet_lv2": {
        "condition": "ricochet_item", "level": 2,
        "count": 1, "damage": 1, "bounce_damage": 0.3, "speed": 8,
        "angles": [-90],
        "type": "bounce", "hits": 1, "bounce": 5, "size": 6, "color": "#0088ff"
    },
    # 弧射 (Arc)
    "arc_lv1": {
        "condition": "arc_item", "level": 1,
        "count": 1, "damage": 2, "speed": 6, # 基礎速度x0.6
        "fire_rate_mult": 0.6,
        "type": "arc", "angles": "random_45_135", # 特殊邏輯
        "size_mult": 1.0, "range": MAP_HEIGHT * 0.5, "color": "#ff00ff"
    },
    "arc_lv2": {
        "condition": "arc_item", "level": 2,
        "count": 1, "damage": 3, "speed": 6,
        "fire_rate_mult": 0.6,
        "type": "arc", "angles": "random_45_135",
        "size_mult": 1.5, "range": MAP_HEIGHT * 0.5, "color": "#aa00aa"
    }
}
