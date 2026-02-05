#config.py v4.2
import math

# --- 地圖與基礎設定 ---
MAP_WIDTH = 600
MAP_HEIGHT = 500
MAX_ENEMIES = 5
INVINCIBLE_TIME = 1.5
FIRE_COOLDOWN = 0.15
PLAYER_LIVES = 5

# --- 角色設定 (Cell) ---
CELL_CONFIG = {
    1: {"name": "Soldier", "hp": 5, "speed": 8, "bullet_speed": 7, "damage": 1, "color": "#50fa7b"},
    2: {"name": "Scout", "hp": 3, "speed": 12, "bullet_speed": 10, "damage": 1, "color": "#8be9fd"},
    3: {"name": "Tank", "hp": 8, "speed": 5, "bullet_speed": 6, "damage": 2, "color": "#ff5555"}
}

# --- 牆壁設定 (Wall) ---
# 根據需求：體長 2.5 倍, 寬度=自己(1倍), 血量 100, 存在 25s, CD 20s
WALL_CONFIG = {
    "hp": 100,
    "duration": 25,
    "cooldown": 20,
    "width_mult": 1.0,  # 寬度倍率
    "length_mult": 2.5, # 長度倍率
    "color": "#7f8c8d"  # 灰色
}

# --- 怪物設定 (Virus) ---
VIRUS_CONFIG = {
    1: {"hp": 3, "speed": 3, "size": 50, "score": 10, "prob": 0.7, "drop_rate": 0.1,
        "attack": {"mode": "single", "damage": 1, "bullet_speed": 8, "fire_rate": 0.005}},
    2: {"hp": 1, "speed": 7, "size": 25, "score": 25, "prob": 0.2, "drop_rate": 0.15,
        "attack": {"mode": "single", "damage": 1, "bullet_speed": 15, "fire_rate": 0.01}},
    3: {"hp": 15, "speed": 2, "size": 95, "score": 100, "prob": 0.1, "drop_rate": 0.5,
        "attack": {"mode": "double", "damage": 2, "bullet_speed": 6, "fire_rate": 0.02}},
    999: {"hp": 500, "speed": 5, "size": 230, "score": 1000, "drop_rate": 1.0,
          "kill_bonus": 200}
}

# --- 道具與子彈技能設定 ---
WEAPON_CONFIG = {
    "default": {
        "damage": 1, "speed": 10, "count": 1, "type": "linear",
        "angles": [0], # 這裡的角度會被搖桿覆蓋，只是預設值
        "size": 5, "hits": 1, "bounce": 0
    },
    "spread_lv1": {
        "condition": "spread_item", "level": 1,
        "count": 3, "damage": 1, "speed": 10, "size": 5,
        "angles": [-30, 0, 30], # 改為相對角度 (相對於搖桿方向)
        "type": "linear", "hits": 1, "bounce": 0, "color": "#ffff00"
    },
    "spread_lv2": {
        "condition": "spread_item", "level": 2,
        "count": 5, "damage": 1, "speed": 10, "size": 5,
        "angles": [-40, -20, 0, 20, 40], # 相對角度
        "type": "linear", "hits": 1, "bounce": 0, "color": "#ffcc00"
    },
    "ricochet_lv1": {
        "condition": "ricochet_item", "level": 1,
        "count": 1, "damage": 1, "bounce_damage": 0.3, "speed": 8,
        "angles": [0],
        "type": "bounce", "hits": 1, "bounce": 3, "size": 6, "color": "#00ffff"
    },
    "ricochet_lv2": {
        "condition": "ricochet_item", "level": 2,
        "count": 1, "damage": 1, "bounce_damage": 0.3, "speed": 8,
        "angles": [0],
        "type": "bounce", "hits": 1, "bounce": 5, "size": 6, "color": "#0088ff"
    },
    "arc_lv1": {
        "condition": "arc_item", "level": 1,
        "count": 1, "damage": 2, "speed": 6,
        "fire_rate_mult": 0.6,
        "type": "arc", "angles": "random_forward", # 修改為隨機前方
        "size_mult": 1.0, "range": MAP_HEIGHT * 0.5, "color": "#ff00ff"
    },
    "arc_lv2": {
        "condition": "arc_item", "level": 2,
        "count": 1, "damage": 3, "speed": 6,
        "fire_rate_mult": 0.6,
        "type": "arc", "angles": "random_forward",
        "size_mult": 1.5, "range": MAP_HEIGHT * 0.5, "color": "#aa00aa"
    }
}
