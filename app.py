import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Cell Wars 3.1 - Boss Coming !!", layout="wide")

# 修改為你的 Render 伺服器網址
SERVER_URL = "https://cell-wars.onrender.com" 
GITHUB_USER = "Kuaan"
GITHUB_REPO = "Cell_Wars"
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
            height: 100vh;
        }}
        
        /* --- 登入頁面置中優化 --- */
        #login-overlay {{
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(13, 2, 17, 0.98); z-index: 100; 
            display: flex; flex-direction: column; 
            align-items: center; justify-content: center;
            text-align: center; /* 確保所有文字置中 */
        }}

        #login-overlay h1 {{
            margin-bottom: 5px;
            text-shadow: 0 0 10px #50fa7b;
        }}

        #login-overlay p {{
            margin-bottom: 25px;
            letter-spacing: 1px;
        }}

        #name-input {{
            padding: 12px;
            width: 200px;
            border: 2px solid #50fa7b;
            background: #1a0620;
            color: #fff;
            border-radius: 5px;
            outline: none;
            margin-bottom: 15px;
        }}

        #start-btn {{
            padding: 12px 40px;
            background: #50fa7b;
            border: none;
            border-radius: 5px;
            font-weight: bold;
            cursor: pointer;
            transition: 0.2s;
            box-shadow: 0 0 15px rgba(80, 250, 123, 0.3);
        }}

        #start-btn:hover {{
            transform: scale(1.05);
            background: #62ff8a;
            box-shadow: 0 0 25px rgba(80, 250, 123, 0.5);
        }}

        /* --- 遊戲介面樣式 --- */
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
            font-weight: bold; user-select: none; box-shadow: 0 4px 0 #b30000;
        }}
        .btn-fire:active {{ transform: translateY(4px); box-shadow: none; }}

        .btn-skill {{
            width: 50px; height: 50px; background: #8be9fd; 
            border-radius: 50%; border: 3px solid #cyan;
            display: flex; align-items: center; justify-content: center;
            font-size: 12px; font-weight: bold; color: #000;
            user-select: none; transition: 0.3s;
        }}
        .btn-skill.disabled {{ filter: grayscale(100%); opacity: 0.5; }}
        .btn-skill:active {{ transform: scale(0.95); }}

        #charge-container {{ 
            display: flex; gap: 4px; margin-bottom: 8px; align-items: center; 
            background: #222; padding: 4px; border-radius: 4px; border: 1px solid #444;
        }}
        .charge-bar-segment {{
            position: relative; width: 30px; height: 12px;
            background: #333; border: 1px solid #555;
            transform: skewX(-15deg);
        }}
        .charge-fill {{
            position: absolute; bottom: 0; left: 0; width: 0%; height: 100%;
            background: #f1fa8c; transition: width 0.2s;
        }}
        .charge-bar-segment.full .charge-fill {{ width: 100% !important; box-shadow: 0 0 5px #f1fa8c; }}
    </style>
</head>
<body>

    <div id="login-overlay">
        <h1 style="color: #50fa7b;">🦠 CELL WARS: BOSS MODE</h1>
        <p style="color: #aaa; font-size: 12px;">Defeat Elite -> Wait 30s -> Boss</p>
        <input type="text" id="name-input" placeholder="Enter Name" maxlength="8">
        <button id="start-btn">START MISSION</button>
    </div>

    <div id="top-bar">
        <div id="lb-content">Connecting...</div>
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
            
            <div style="display:flex; gap:20px; align-items:flex-end;">
                <div class="btn-skill disabled" id="skill-btn">SKILL</div>
                <div class="btn-fire" id="fire-btn">FIRE</div>
            </div>
        </div>
    </div>

    <script>
        // ... (以下 JavaScript 與音效載入部分保持不變) ...
        const socket = io("{SERVER_URL}", {{ reconnection: true }});
        const canvas = document.getElementById('gameCanvas');
        const ctx = canvas.getContext('2d');
        const assetsBase = "{ASSETS_BASE}";
        const soundsBase = "{SOUNDS_BASE}";
        
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
        audioFiles.bgm.volume = 0.4;

        function playSfx(key) {{
            const s = audioFiles[key];
            if(s) {{ s.currentTime = 0; s.play().catch(e => {{}}); }}
        }}

        const skins = {{ cells: [], viruses: [], boss: null }};
        function loadImg(path) {{
            let img = new Image(); img.src = path;
            return img;
        }}
        for(let i=1; i<=3; i++) {{
            skins.cells.push(loadImg(assetsBase + "cell_" + i + ".png"));
            skins.viruses.push(loadImg(assetsBase + "virus_" + i + ".png"));
        }}
        skins.boss = loadImg(assetsBase + "boss_1.png");

        let gameState = {{ players: {{}}, enemies: {{}}, bullets: [], skill_objects: [] }};
        let myId = null;

        socket.on('connect', () => {{ myId = socket.id; }});
        
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

        function updateUI() {{
            if (!myId || !gameState.players[myId]) return;
            const me = gameState.players[myId];

            const sorted = Object.values(gameState.players).sort((a,b)=>b.score-a.score).slice(0,3);
            const lbHtml = sorted.map((p, i) => `<span class="score-pill">${{i==0?'👑':''}}${{p.name}}:${{p.score}}</span>`).join('');
            document.getElementById('lb-content').innerHTML = lbHtml;

            for(let i=1; i<=3; i++) {{
                const elSeg = document.getElementById('seg'+i);
                const elFill = document.getElementById('fill'+i);
                if (me.charge >= i) {{
                    elSeg.classList.add('full');
                    elFill.style.width = '100%';
                }} else if (me.charge === i - 1) {{
                    elSeg.classList.remove('full');
                    let pct = (me.hit_accumulated / 20) * 100;
                    elFill.style.width = pct + '%';
                }} else {{
                    elSeg.classList.remove('full');
                    elFill.style.width = '0%';
                }}
            }}
            const btn = document.getElementById('skill-btn');
            if (me.charge >= 1) btn.classList.remove('disabled');
            else btn.classList.add('disabled');
        }}

        function draw() {{
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            if (gameState.skill_objects) {{
                ctx.globalAlpha = 0.7;
                gameState.skill_objects.forEach(obj => {{
                    let img = skins.cells[(obj.skin || 1) - 1];
                    if(img && img.complete) ctx.drawImage(img, obj.x, obj.y, 30, 30);
                    ctx.strokeStyle = "#fff"; ctx.lineWidth = 1; 
                    ctx.beginPath(); ctx.arc(obj.x+15, obj.y+15, 18, 0, Math.PI*2); ctx.stroke();
                }});
                ctx.globalAlpha = 1.0;
            }

            for (let id in gameState.enemies) {{
                let e = gameState.enemies[id];
                if (e.type === 999) {{
                    if(skins.boss.complete) ctx.drawImage(skins.boss, e.x, e.y, e.size, e.size);
                    ctx.fillStyle = "#555"; ctx.fillRect(e.x, e.y-10, e.size, 8);
                    ctx.fillStyle = "#bd93f9"; ctx.fillRect(e.x, e.y-10, e.size * (e.hp/e.max_hp), 8);
                }} else {{
                    let img = skins.viruses[(e.type || 1) - 1];
                    if(img && img.complete) ctx.drawImage(img, e.x, e.y, e.size, e.size);
                    ctx.fillStyle = "#555"; ctx.fillRect(e.x, e.y-6, e.size, 3);
                    ctx.fillStyle = "#ff5555"; ctx.fillRect(e.x, e.y-6, e.size * (e.hp/e.max_hp), 3);
                }}
            }}

            for (let id in gameState.players) {{
                let p = gameState.players[id];
                let img = skins.cells[(p.skin || 1) - 1];
                if(img && img.complete) ctx.drawImage(img, p.x, p.y, 30, 30);
                ctx.fillStyle = (id === myId) ? "#f1fa8c" : "white";
                ctx.font = "12px Arial"; ctx.textAlign = "center";
                ctx.fillText(p.name, p.x+15, p.y-15);
                ctx.fillStyle = "#444"; ctx.fillRect(p.x, p.y-10, 30, 4);
                ctx.fillStyle = "#50fa7b"; ctx.fillRect(p.x, p.y-10, 30 * (p.hp / p.max_hp), 4);
            }}

            gameState.bullets.forEach(b => {{
                ctx.beginPath();
                if (b.owner === 'boss') {{ ctx.fillStyle = '#bd93f9'; ctx.arc(b.x, b.y, 8, 0, Math.PI*2); }}
                else if (b.owner === 'enemy') {{ ctx.fillStyle = '#ff5555'; ctx.arc(b.x, b.y, 4, 0, Math.PI*2); }}
                else {{ ctx.fillStyle = '#8be9fd'; ctx.arc(b.x, b.y, 4, 0, Math.PI*2); }}
                ctx.fill();
            }});
        }}

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
            audioFiles.bgm.play().catch(e => {{}});
        }};

        const fireBtn = document.getElementById('fire-btn');
        let fireInterval;
        const startFire = (e) => {{ 
            e.preventDefault(); playSfx('p_shot'); socket.emit('shoot');
            fireInterval = setInterval(()=> {{ socket.emit('shoot'); playSfx('p_shot'); }}, 250); 
        }};
        const stopFire = () => clearInterval(fireInterval);

        fireBtn.addEventListener('touchstart', startFire); fireBtn.addEventListener('touchend', stopFire);
        fireBtn.addEventListener('mousedown', startFire); fireBtn.addEventListener('mouseup', stopFire);

        document.getElementById('skill-btn').addEventListener('touchstart', (e) => {{ e.preventDefault(); socket.emit('use_skill'); }});
        document.getElementById('skill-btn').addEventListener('mousedown', (e) => {{ e.preventDefault(); socket.emit('use_skill'); }});
        
        document.addEventListener('keydown', (e) => {{
            if (e.code === 'Space') {{ socket.emit('shoot'); playSfx('p_shot'); }}
            if (e.key === 'q') socket.emit('use_skill');
        }});
    </script>
</body>
</html>
"""

components.html(html_code, height=850)
