# v5.1 app.py (Matching Server v3.7.3)
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Cell Wars V5.1", layout="wide")

SERVER_URL = "https://cell-wars.onrender.com"
GITHUB_USER = "Kuaan"
GITHUB_REPO = "Cell_Wars"
ASSETS_BASE = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/assets/"
SOUNDS_BASE = f"{ASSETS_BASE}sounds/"

st.markdown("""
    <style>
    [data-testid="stHeader"] {display: none;}
    .stApp {background-color: #0d0211; margin: 0; padding: 0;}
    iframe {display: block;} 
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
        /* ... 此處維持你原始的 CSS 樣式 ... */
        * {{ box-sizing: border-box; }}
        body {{ 
            background-color: #0d0211; color: #fff; margin: 0; padding: 0;
            font-family: 'Courier New', monospace; overflow: hidden; 
            display: flex; flex-direction: column; align-items: center;
            height: 100vh; width: 100vw;
        }}
        #login-overlay {{
            position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
            background: #0d0211; z-index: 99999; 
            display: flex; flex-direction: column; align-items: center; 
            justify-content: flex-start; padding-top: 20%;
        }}
        #login-box {{
            background: #1a0620; padding: 30px; border-radius: 15px;
            border: 2px solid #50fa7b; text-align: center; width: 85%; max-width: 400px;
        }}
        input {{ margin: 15px 0; padding: 12px; font-size: 18px; width: 100%; text-align: center; background: #222; color: #fff; border: 1px solid #444; border-radius: 8px; }}
        button {{ padding: 15px 40px; font-size: 18px; background: #50fa7b; color: #000; border: none; border-radius: 8px; font-weight: bold; width: 100%; cursor: pointer; }}
        #top-bar {{
            width: 100%; background: #1a0620; padding: 5px 0;
            display: flex; justify-content: space-around; align-items: center;
            border-bottom: 1px solid #bd93f9; font-size: 12px;
            height: 40px; flex-shrink: 0;
        }}
        .vol-control {{ display: flex; align-items: center; gap: 5px; font-size: 10px; color: #bd93f9; }}
        canvas {{ 
            background-color: #000; border: 2px solid #444; 
            width: 95vw; max-width: 600px; height: auto; aspect-ratio: 6/5;
            image-rendering: pixelated; margin-top: 5px;
        }}
        #ui-container {{
            width: 100%; max-width: 600px; height: 180px;
            margin-top: 10px; display: flex; justify-content: space-between;
            align-items: center; padding: 0 15px;
        }}
        #joystick-zone {{ width: 140px; height: 140px; position: relative; }}
        .btn-fire {{
            width: 75px; height: 75px; background: #ff5555; border-radius: 50%;
            border: 3px solid #ff9999; display: flex; align-items: center; justify-content: center;
            font-weight: bold; box-shadow: 0 4px 0 #b30000; touch-action: none;
        }}
        .btn-skill {{
            width: 55px; height: 55px; background: #8be9fd; border-radius: 50%;
            border: 3px solid cyan; display: flex; align-items: center; justify-content: center;
            font-size: 12px; font-weight: bold; color: #000;
        }}
        .disabled {{ opacity: 0.3; }}
        #charge-container {{ display: flex; gap: 4px; margin-bottom: 5px; }}
        .charge-bar-segment {{ width: 25px; height: 10px; background: #333; transform: skewX(-15deg); position: relative; }}
        .charge-fill {{ position: absolute; left: 0; top: 0; height: 100%; background: #f1fa8c; width: 0%; }}
        .full .charge-fill {{ width: 100%; box-shadow: 0 0 5px #f1fa8c; }}
    </style>
</head>
<body>

    <div id="login-overlay">
        <div id="login-box">
            <h1 style="color: #50fa7b; margin: 0 0 10px 0;">🦠 CELL WARS</h1>
            <p style="color: #aaa; font-size: 12px;">已隔離他人槍聲 | 本地零延遲</p>
            <input type="text" id="name-input" placeholder="輸入名稱" maxlength="8">
            <button id="start-btn">進入遊戲</button>
        </div>
    </div>

    <div id="top-bar">
        <div class="vol-control">BGM <input type="range" id="vol-bgm" min="0" max="1" step="0.1" value="0.4"></div>
        <div id="lb-content">載入中...</div>
        <div class="vol-control">SFX <input type="range" id="vol-sfx" min="0" max="1" step="0.1" value="0.6"></div>
    </div>

    <canvas id="gameCanvas" width="600" height="500"></canvas>

    <div id="ui-container">
        <div id="joystick-zone"></div>
        <div id="actions-zone">
            <div id="charge-container">
                <div class="charge-bar-segment" id="seg1"><div class="charge-fill" id="fill1"></div></div>
                <div class="charge-bar-segment" id="seg2"><div class="charge-fill" id="fill2"></div></div>
                <div class="charge-bar-segment" id="seg3"><div class="charge-fill" id="fill3"></div></div>
            </div>
            <div style="display:flex; gap:15px; align-items:flex-end;">
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

        // --- 音效系統 ---
        const audioFiles = {{
            bgm: new Audio(soundsBase + "bgm/bgm-145a.wav"),
            p_hit: new Audio(soundsBase + "characters/character_hitted.wav"),
            p_shot: new Audio(soundsBase + "characters/character_nor_shot.wav"),
            boss_come: new Audio(soundsBase + "enemy/boss_coming.wav"),
            boss_hit: new Audio(soundsBase + "enemy/boss_hitted.wav"),
            boss_shot: new Audio(soundsBase + "enemy/boss_shot.wav"), 
            e_hit: new Audio(soundsBase + "enemy/enemy_hitted.wav"),
            e_shot: new Audio(soundsBase + "enemy/enemy_nor_shot.wav"),
            skill: new Audio(soundsBase + "skill/slime.wav")
        }};
        audioFiles.bgm.loop = true;
        let volBGM = 0.4;
        let volSFX = 0.6;

        // --- 核心變數 ---
        let gameState = {{ players: {{}}, enemies: {{}}, bullets: [], skill_objects: [], w: false }};
        let myId = null;
        let localBullets = []; 
        let lastShotTimeLocal = 0; // 本地射擊冷卻控制

        function playSfx(key) {{
            if (volSFX <= 0.01) return;
            const s = audioFiles[key];
            if(s) {{ 
                const clone = s.cloneNode(); // 使用 Clone 允許音效重疊播放（解決射速快時聲音斷掉問題）
                clone.volume = volSFX;
                clone.play().catch(e => {{}}); 
            }}
        }}

        // --- 資源加載 ---
        const skins = {{ cells: [], viruses: [], boss: null }};
        function loadImg(path) {{ let img = new Image(); img.src = path; return img; }}
        for(let i=1; i<=3; i++) {{
            skins.cells.push(loadImg(assetsBase + "cell_" + i + ".png"));
            skins.viruses.push(loadImg(assetsBase + "virus_" + i + ".png"));
        }}
        skins.boss = loadImg(assetsBase + "boss_1.png");

        socket.on('connect', () => {{ myId = socket.id; }});

        // 監聽 Server 發送的「專屬」音效 (擊中、受傷等)
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
            updateUI();
        }});

        function loop() {{
            updateLocalBullets();
            draw();
            requestAnimationFrame(loop);
        }}
        requestAnimationFrame(loop);

        function updateLocalBullets() {{
            for(let i = localBullets.length - 1; i >= 0; i--) {{
                localBullets[i].y -= localBullets[i].speed; 
                if(localBullets[i].y < -50) localBullets.splice(i, 1);
            }}
        }}

        // --- 核心優化：零延遲射擊處理 ---
        function doFire() {{
            if (!myId || !gameState.players[myId]) return;
            const now = Date.now();
            const p = gameState.players[myId];
            
            // 根據不同兵種設定本地冷卻 (ms) - 稍微比 Server 短一點點確保流暢
            const cooldowns = {{ 1: 220, 2: 130, 3: 380 }}; 
            const myCd = cooldowns[p.skin] || 200;

            if (now - lastShotTimeLocal >= myCd) {{
                lastShotTimeLocal = now;

                // 1. 本地立即播音
                playSfx('p_shot');

                // 2. 生成預測子彈
                let speed = (p.skin === 2) ? 10 : (p.skin === 3 ? 6 : 7);
                localBullets.push({{ x: p.x + 15, y: p.y, speed: speed }});

                // 3. 通知 Server
                socket.emit('shoot');
            }}
        }}

        function draw() {{
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            // 繪製敵人
            for (let id in gameState.enemies) {{
                let e = gameState.enemies[id];
                if (e.type === 999) {{
                    if(skins.boss.complete) ctx.drawImage(skins.boss, e.x, e.y, e.size, e.size);
                }} else {{
                    let img = skins.viruses[(e.type || 1) - 1];
                    if(img && img.complete) ctx.drawImage(img, e.x, e.y, e.size, e.size);
                }}
            }}

            // 繪製玩家
            for (let id in gameState.players) {{
                let p = gameState.players[id];
                if (p.invincible) ctx.globalAlpha = 0.5;
                let img = skins.cells[(p.skin || 1) - 1];
                if(img && img.complete) ctx.drawImage(img, p.x, p.y, 30, 30);
                ctx.globalAlpha = 1.0;
            }}

            // 繪製 Server 子彈 (過濾掉自己的，避免重影)
            gameState.bullets.forEach(b => {{
                if (b.owner === myId) return; // 自己的子彈看本地預測的就好
                ctx.beginPath();
                if (b.owner === 'boss') ctx.fillStyle = '#bd93f9';
                else if (b.owner === 'enemy') ctx.fillStyle = '#ff5555';
                else ctx.fillStyle = '#8be9fd';
                ctx.arc(b.x, b.y, 4, 0, Math.PI*2);
                ctx.fill();
            }});

            // 繪製本地預測子彈
            ctx.fillStyle = '#f1fa8c';
            localBullets.forEach(b => {{
                ctx.beginPath(); ctx.arc(b.x, b.y, 4, 0, Math.PI*2); ctx.fill();
            }});
        }}

        // ... Joystick 與 UI 更新維持原樣 ...
        const manager = nipplejs.create({{
            zone: document.getElementById('joystick-zone'),
            mode: 'static', position: {{ left: '70px', top: '70px' }},
            size: 100, color: 'white'
        }});
        manager.on('move', (evt, data) => {{ if(data.vector) socket.emit('move', {{ dx: data.vector.x, dy: -data.vector.y }}); }});
        manager.on('end', () => {{ socket.emit('move', {{ dx: 0, dy: 0 }}); }});

        const fireBtn = document.getElementById('fire-btn');
        fireBtn.addEventListener('touchstart', (e) => {{ e.preventDefault(); doFire(); }});
        fireBtn.addEventListener('mousedown', (e) => {{ e.preventDefault(); doFire(); }});

        document.getElementById('start-btn').onclick = function() {{
            const name = document.getElementById('name-input').value || 'Cell';
            socket.emit('join_game', {{ name: name }});
            document.getElementById('login-overlay').style.display = 'none';
            audioFiles.bgm.play().catch(e=>{{}});
        }};

        function updateUI() {{
            if (!myId || !gameState.players[myId]) return;
            const me = gameState.players[myId];
            const sorted = Object.values(gameState.players).sort((a,b)=>b.score-a.score).slice(0,3);
            document.getElementById('lb-content').innerHTML = sorted.map((p, i) => `<span class="score-pill">${{i==0?'👑':''}}${{p.name}}:${{p.score}}</span>`).join('');
            for(let i=1; i<=3; i++) {{
                const elSeg = document.getElementById('seg'+i);
                const elFill = document.getElementById('fill'+i);
                if (me.charge >= i) {{ elSeg.classList.add('full'); elFill.style.width = '100%'; }}
                else if (me.charge === i - 1) {{ elSeg.classList.remove('full'); elFill.style.width = ((me.hit_accumulated / 20) * 100) + '%'; }}
                else {{ elSeg.classList.remove('full'); elFill.style.width = '0%'; }}
            }}
        }}
    </script>
</body>
</html>
"""
components.html(html_code, height=800)
