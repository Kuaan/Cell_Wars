import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Cell Wars 2.0 - Boss Update", layout="wide")

# --- GitHub 資源路徑設定 ---
GITHUB_USER = "Kuaan"
GITHUB_REPO = "Cell_Wars"
# 修改為你的 Render 伺服器網址
SERVER_URL = "https://cell-wars.onrender.com" 
ASSETS_BASE = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/assets/"
SOUNDS_BASE = f"{ASSETS_BASE}sounds/"

st.markdown("""
    <style>
    [data-testid="stHeader"] {display: none;}
    .stApp {background-color: #0d0211;}
    </style>
""", unsafe_allow_html=True)

html_code = f"""
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <script src="https://cdn.socket.io/4.6.0/socket.io.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/nipplejs/0.10.1/nipplejs.min.js"></script>
    <style>
        body {{ 
            background-color: #0d0211; color: #fff; margin: 0; 
            font-family: 'Courier New', monospace; overflow: hidden; 
            display: flex; flex-direction: column; align-items: center;
            touch-action: none;
        }}
        
        #top-bar {{
            width: 100%; background: #1a0620; padding: 5px 0;
            display: flex; justify-content: center; gap: 10px;
            border-bottom: 1px solid #bd93f9; font-size: 12px;
            z-index: 10;
        }}
        .score-pill {{ background: rgba(189, 147, 249, 0.2); padding: 2px 8px; border-radius: 10px; }}
        
        canvas {{ 
            background-color: #000; border: 2px solid #444; 
            width: 95vw; max-width: 600px; height: auto; aspect-ratio: 6/5;
            image-rendering: pixelated; margin-top: 5px;
        }}

        #login-overlay {{
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(13, 2, 17, 0.95); z-index: 100; 
            display: flex; flex-direction: column; align-items: center; justify-content: center;
        }}

        #ui-container {{
            position: relative; width: 95vw; max-width: 600px; height: 180px;
            margin-top: 10px; display: flex; justify-content: space-between; align-items: center;
        }}
        #joystick-zone {{ width: 150px; height: 150px; position: relative; }}
        #actions-zone {{ display: flex; flex-direction: column; align-items: center; gap: 15px; padding-right: 20px; }}

        .btn-fire {{
            width: 70px; height: 70px; background: #ff5555; 
            border-radius: 50%; border: 3px solid #ff9999;
            display: flex; align-items: center; justify-content: center;
            font-weight: bold; user-select: none;
        }}
        .btn-fire:active {{ background: #ff0000; transform: scale(0.95); }}

        .btn-skill {{
            width: 50px; height: 50px; background: #8be9fd; 
            border-radius: 50%; border: 3px solid #cyan;
            display: flex; align-items: center; justify-content: center;
            font-size: 12px; font-weight: bold; color: #000;
            user-select: none; transition: 0.3s;
        }}
        .btn-skill.disabled {{ filter: grayscale(100%); opacity: 0.5; }}
        .btn-skill:active {{ transform: scale(0.95); }}

        /* --- 優化2: 技能條樣式 --- */
        #charge-container {{ display: flex; gap: 8px; margin-bottom: 5px; align-items: center; }}
        .charge-wrapper {{
            position: relative; width: 16px; height: 16px;
            border-radius: 50%; border: 2px solid #555; background: #222;
            overflow: hidden;
        }}
        .charge-fill {{
            position: absolute; bottom: 0; left: 0; width: 100%; height: 0%;
            background: #f1fa8c; transition: height 0.2s;
        }}
        .charge-wrapper.full {{ border-color: #fff; box-shadow: 0 0 5px #f1fa8c; }}
        .charge-wrapper.full .charge-fill {{ height: 100% !important; }}

    </style>
</head>
<body>

    <div id="login-overlay">
        <h1 style="color: #50fa7b;">🦠 CELL WARS: BOSS MODE</h1>
        <p style="color: #aaa; font-size: 12px;">Boss appears in 45s</p>
        <input type="text" id="name-input" placeholder="Enter Name" maxlength="8" style="padding:10px; text-align:center;">
        <br><button id="start-btn" style="padding:10px 30px; background:#50fa7b; border:none; border-radius:5px; font-weight:bold;">START</button>
    </div>

    <div id="top-bar">
        <div id="lb-content">Connecting...</div>
    </div>

    <canvas id="gameCanvas" width="600" height="500"></canvas>
    
    <div id="ui-container">
        <div id="joystick-zone"></div>

        <div id="actions-zone">
            <div id="charge-container">
                <div class="charge-wrapper" id="cw1"><div class="charge-fill" id="cf1"></div></div>
                <div class="charge-wrapper" id="cw2"><div class="charge-fill" id="cf2"></div></div>
                <div class="charge-wrapper" id="cw3"><div class="charge-fill" id="cf3"></div></div>
            </div>
            
            <div style="display:flex; gap:20px; align-items:flex-end;">
                <div class="btn-skill disabled" id="skill-btn">SKILL</div>
                <div class="btn-fire" id="fire-btn">FIRE</div>
            </div>
        </div>
    </div>

    <script>
        const socket = io("{SERVER_URL}", {{ reconnection: true }});
        const canvas = document.getElementById('gameCanvas');
        const ctx = canvas.getContext('2d');
        const assetsBase = "{ASSETS_BASE}";
        const soundsBase = "{SOUNDS_BASE}";
        
        // --- 1. 聲音實作 ---
        const audioFiles = {{
            bgm: new Audio(soundsBase + "bgm/bgm-145a.wav"),
            p_hit: new Audio(soundsBase + "characters/charcter_hitted.wav"),
            p_shot: new Audio(soundsBase + "characters/charcter_nor_shot.wav"),
            boss_come: new Audio(soundsBase + "enemy/boss_coming.wav"),
            boss_hit: new Audio(soundsBase + "enemy/boss_hitted.wav"),
            boss_shot: new Audio(soundsBase + "enemy/boss_shot.wav"), 
            e_hit: new Audio(soundsBase + "enemy/enemy_hitted.wav"),
            e_shot: new Audio(soundsBase + "enemy/enemy_nor_shot.wav"),
            skill: new Audio(soundsBase + "skill/slime.wav")
        }};
        
        // 設定 BGM 循環
        audioFiles.bgm.loop = true;
        audioFiles.bgm.volume = 0.5;

        // 播放輔助函式 (防止報錯)
        function playSfx(key) {{
            const s = audioFiles[key];
            if(s) {{
                s.currentTime = 0;
                s.play().catch(e => console.log("Audio play failed", e));
            }}
        }}

        // --- 圖片載入 ---
        const skins = {{ cells: [], viruses: [] }};
        function loadImg(path) {{
            let img = new Image(); img.src = path;
            img.onerror = () => {{ img.isBroken = true; }};
            return img;
        }}
        for(let i=1; i<=3; i++) {{
            skins.cells.push(loadImg(assetsBase + "cell_" + i + ".png"));
            skins.viruses.push(loadImg(assetsBase + "virus_" + i + ".png"));
        }}

        let gameState = {{ players: {{}}, enemies: {{}}, bullets: [], skill_objects: [] }};
        let myId = null;

        // --- Socket 監聽 ---
        socket.on('connect', () => {{ myId = socket.id; }});
        
        // 接收音效事件
        socket.on('sfx', (data) => {{
            switch(data.type) {{
                case 'character_hitted': playSfx('p_hit'); break;
                case 'boss_coming': playSfx('boss_come'); break;
                case 'boss_hitted': playSfx('boss_hit'); break;
                case 'boss_shot': playSfx('boss_shot'); break;
                case 'enemy_hitted': playSfx('e_hit'); break;
                case 'enemy_nor_shot': playSfx('e_shot'); break;
                case 'skill_slime': playSfx('skill'); break;
            }}
        }});

        socket.on('state_update', (data) => {{
            gameState = data;
            requestAnimationFrame(draw);
            updateUI();
        }});

        // --- UI 更新邏輯 ---
        function updateUI() {{
            if (!myId || !gameState.players[myId]) return;
            const me = gameState.players[myId];

            // 排行榜
            const sorted = Object.values(gameState.players).sort((a,b)=>b.score-a.score).slice(0,3);
            const lbHtml = sorted.map((p, i) => `<span class="score-pill">${{i==0?'👑':''}}${{p.name}}:${{p.score}}</span>`).join('');
            document.getElementById('lb-content').innerHTML = lbHtml;

            // 優化2: 技能槽百分比顯示
            // logic: me.charge 是整數(0-3), me.hit_accumulated 是當前集氣進度(0-20)
            for(let i=1; i<=3; i++) {{
                const elWrap = document.getElementById('cw'+i);
                const elFill = document.getElementById('cf'+i);
                
                if (me.charge >= i) {{
                    // 已經集滿的氣
                    elWrap.classList.add('full');
                    elFill.style.height = '100%';
                }} else if (me.charge === i - 1) {{
                    // 正在集的氣
                    elWrap.classList.remove('full');
                    let pct = (me.hit_accumulated / 20) * 100;
                    elFill.style.height = pct + '%';
                }} else {{
                    // 還沒開始集的氣
                    elWrap.classList.remove('full');
                    elFill.style.height = '0%';
                }}
            }}

            const btn = document.getElementById('skill-btn');
            if (me.charge >= 1) btn.classList.remove('disabled');
            else btn.classList.add('disabled');
        }}

        // --- 繪圖邏輯 ---
        function draw() {{
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            // 1. 畫技能分身 (優化3: 用跟自己一樣的圖示)
            ctx.globalAlpha = 0.7;
            if (gameState.skill_objects) {{
                gameState.skill_objects.forEach(obj => {{
                    // 取得對應的 skin 圖片
                    let img = skins.cells[(obj.skin || 1) - 1];
                    if(img && img.complete && !img.isBroken) {{
                        ctx.drawImage(img, obj.x, obj.y, 30, 30);
                    }} else {{
                        // Fallback
                        ctx.beginPath(); ctx.arc(obj.x, obj.y, 15, 0, Math.PI*2);
                        ctx.fillStyle = "#8be9fd"; ctx.fill();
                    }}
                    // 畫個圈表示是分身
                    ctx.strokeStyle = "#fff"; ctx.lineWidth = 1; 
                    ctx.beginPath(); ctx.arc(obj.x+15, obj.y+15, 18, 0, Math.PI*2); ctx.stroke();
                }});
            }}
            ctx.globalAlpha = 1.0;

            // 2. 畫敵人 (包含 Boss)
            for (let id in gameState.enemies) {{
                let e = gameState.enemies[id];
                let isBoss = (e.type === 999);
                
                if (isBoss) {{
                    // 優化4: Boss 300x300
                    // 這裡暫時放大 virus_3 的圖
                    let img = skins.viruses[2]; 
                    if(img && img.complete) ctx.drawImage(img, e.x, e.y, e.size, e.size);
                    else {{ ctx.fillStyle = "purple"; ctx.fillRect(e.x, e.y, e.size, e.size); }}
                    
                    // Boss 血條
                    ctx.fillStyle = "#555"; ctx.fillRect(e.x, e.y-10, e.size, 8);
                    ctx.fillStyle = "#bd93f9"; ctx.fillRect(e.x, e.y-10, e.size * (e.hp/e.max_hp), 8);
                    
                }} else {{
                    let img = skins.viruses[(e.type || 1) - 1];
                    if(img && img.complete) ctx.drawImage(img, e.x, e.y, e.size, e.size);
                    else {{ ctx.fillStyle = "red"; ctx.fillRect(e.x, e.y, e.size, e.size); }}
                    
                    // 小怪血條
                    ctx.fillStyle = "#555"; ctx.fillRect(e.x, e.y-6, e.size, 3);
                    ctx.fillStyle = "#ff5555"; ctx.fillRect(e.x, e.y-6, e.size * (e.hp/e.max_hp), 3);
                }}
            }}

            // 3. 畫玩家
            for (let id in gameState.players) {{
                let p = gameState.players[id];
                let img = skins.cells[(p.skin || 1) - 1];
                if(img && img.complete) ctx.drawImage(img, p.x, p.y, 30, 30);
                else {{ ctx.fillStyle = p.stats.color; ctx.fillRect(p.x, p.y, 30, 30); }}
                
                ctx.fillStyle = (id === myId) ? "#f1fa8c" : "white";
                ctx.font = "12px Arial"; ctx.textAlign = "center";
                ctx.fillText(p.name, p.x+15, p.y-15);

                ctx.fillStyle = "#444"; ctx.fillRect(p.x, p.y-10, 30, 4);
                ctx.fillStyle = "#50fa7b"; ctx.fillRect(p.x, p.y-10, 30 * (p.hp / p.max_hp), 4);
            }}

            // 4. 畫子彈 (優化5: 不同圖示)
            gameState.bullets.forEach(b => {{
                ctx.beginPath();
                if (b.owner === 'boss') {{
                    // 魔王子彈：大紫色
                    ctx.fillStyle = '#bd93f9';
                    ctx.arc(b.x, b.y, 8, 0, Math.PI*2);
                }} else if (b.owner === 'enemy') {{
                    // 敵方子彈：紅色三角
                    ctx.fillStyle = '#ff5555';
                    ctx.moveTo(b.x, b.y+5); ctx.lineTo(b.x-4, b.y-4); ctx.lineTo(b.x+4, b.y-4);
                }} else {{
                    // 玩家子彈：藍色圓點
                    ctx.fillStyle = '#8be9fd';
                    ctx.arc(b.x, b.y, 4, 0, Math.PI*2);
                }}
                ctx.fill();
            }});
        }}

        // --- 控制 ---
        const manager = nipplejs.create({{
            zone: document.getElementById('joystick-zone'),
            mode: 'static', position: {{left: '50%', top: '50%'}}, size: 100, color: 'white'
        }});
        manager.on('move', (evt, data) => {{
            if(data.vector) socket.emit('move', {{ dx: data.vector.x, dy: -data.vector.y }});
        }});
        manager.on('end', () => socket.emit('move', {{ dx: 0, dy: 0 }}));

        document.getElementById('start-btn').onclick = () => {{
            const name = document.getElementById('name-input').value.trim() || "Hero";
            socket.emit('join_game', {{ name: name }});
            document.getElementById('login-overlay').style.display = 'none';
            // 嘗試播放 BGM (需使用者互動)
            audioFiles.bgm.play().catch(()=>console.log("Auto-play blocked"));
        }};

        const fireBtn = document.getElementById('fire-btn');
        let fireInterval;
        const startFire = (e) => {{ 
            e.preventDefault(); 
            playSfx('p_shot'); // 玩家自己開槍的聲音直接在前端播
            socket.emit('shoot');
            fireInterval = setInterval(()=> {{
                socket.emit('shoot');
                playSfx('p_shot');
            }}, 250); 
        }};
        const stopFire = () => clearInterval(fireInterval);

        fireBtn.addEventListener('touchstart', startFire);
        fireBtn.addEventListener('touchend', stopFire);
        fireBtn.addEventListener('mousedown', startFire);
        fireBtn.addEventListener('mouseup', stopFire);

        const skillBtn = document.getElementById('skill-btn');
        const castSkill = (e) => {{ e.preventDefault(); socket.emit('use_skill'); }};
        skillBtn.addEventListener('touchstart', castSkill);
        skillBtn.addEventListener('mousedown', castSkill);
        
        document.addEventListener('keydown', (e) => {{
            if (e.code === 'Space') {{ socket.emit('shoot'); playSfx('p_shot'); }}
            if (e.key === 'q') socket.emit('use_skill');
        }});
    </script>
</body>
</html>
"""

components.html(html_code, height=850)
