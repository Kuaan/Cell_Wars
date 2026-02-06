# config.py
import math

# --- 系統與網路設定 (新增) ---
FPS = 60                # 伺服器邏輯運算幀率
BROADCAST_RATE = 0.05   # 廣播頻率 (秒)，約每秒 20 次更新 (比 60 次省流且夠順暢)
MAP_WIDTH = 800         # 稍微加寬以適應現代螢幕
MAP_HEIGHT = 600

# --- 遊戲平衡設定 ---
MAX_ENEMIES = 10        # 稍微增加上限，讓共鬥感更強
INVINCIBLE_TIME = 1.5   
PLAYER_LIVES = 5       

# --- 角色設定 (Cell) ---
CELL_CONFIG = {
    1: {"name": "Soldier", "hp": 5, "speed": 5, "bullet_speed": 7, "damage": 1, "color": "#50fa7b", "radius": 20},
    2: {"name": "Scout",   "hp": 3, "speed": 7, "bullet_speed": 9, "damage": 1, "color": "#8be9fd", "radius": 15},
    3: {"name": "Tank",    "hp": 8, "speed": 3, "bullet_speed": 6, "damage": 2, "color": "#ff5555", "radius": 25}
}

# --- 怪物設定 (Virus) ---
VIRUS_CONFIG = {
    1: {"hp": 3,  "speed": 2,   "size": 40, "score": 10,  "prob": 0.7, "drop_rate": 0.1,  "color": "#bd93f9"},
    2: {"hp": 1,  "speed": 5,   "size": 20, "score": 25,  "prob": 0.2, "drop_rate": 0.15, "color": "#ff79c6"},
    3: {"hp": 15, "speed": 1.5, "size": 80, "score": 100, "prob": 0.1, "drop_rate": 0.5,  "color": "#f1fa8c"},
    999: {"hp": 500, "speed": 1, "size": 200, "score": 1000, "drop_rate": 1.0, "color": "#ff5555"} # Boss
}

# --- 武器與技能詳細參數 (保留你的設計) ---
WEAPON_CONFIG = {
    "default": {
        "damage": 1, "speed": 10, "count": 1, "type": "linear",
        "angles": [-90], 
        "size": 5, "hits": 1, "bounce": 0
    },
    # 散射 (Spread)
    "spread_lv1": {
        "condition": "spread_item", "level": 1,
        "count": 3, "damage": 1, "speed": 10, "size": 5,
        "angles": [-70, -90, -110], # 修正角度，讓散射更集中在前方
        "type": "linear", "hits": 1, "bounce": 0, "color": "#ffff00"
    },
    "spread_lv2": {
        "condition": "spread_item", "level": 2,
        "count": 5, "damage": 1, "speed": 10, "size": 5,
        "angles": [-50, -70, -90, -110, -130],
        "type": "linear", "hits": 1, "bounce": 0, "color": "#ffcc00"
    },
    # 彈射 (Ricochet)
    "ricochet_lv1": {
        "condition": "ricochet_item", "level": 1,
        "count": 1, "damage": 1, "bounce_damage": 0.5, "speed": 8,
        "angles": [-90],
        "type": "bounce", "hits": 1, "bounce": 2, "size": 6, "color": "#00ffff"
    },
    "ricochet_lv2": {
        "condition": "ricochet_item", "level": 2,
        "count": 1, "damage": 1, "bounce_damage": 0.5, "speed": 8,
        "angles": [-90],
        "type": "bounce", "hits": 1, "bounce": 4, "size": 6, "color": "#0088ff"
    },
    # 弧射 (Arc) - 類似迫擊砲
    "arc_lv1": {
        "condition": "arc_item", "level": 1,
        "count": 1, "damage": 2, "speed": 5, 
        "fire_rate_mult": 0.7,
        "type": "arc", "angles": "random", 
        "size_mult": 1.0, "range": 250, "color": "#ff00ff"
    },
    "arc_lv2": {
        "condition": "arc_item", "level": 2,
        "count": 1, "damage": 3, "speed": 5,
        "fire_rate_mult": 0.7,
        "type": "arc", "angles": "random",
        "size_mult": 1.5, "range": 300, "color": "#aa00aa"
    }
}
