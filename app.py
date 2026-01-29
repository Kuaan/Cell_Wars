import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Cell Wars V5", layout="wide")

# 修改為你的 Render 伺服器網址
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
        body {{ 
            background-color: #0d0211; color: #fff; margin: 0; padding: 0;
            font-family: 'Courier New', monospace; overflow: hidden; 
            display: flex; flex-direction: column; align-items: center;
            touch-action: none; height: 100vh; width: 100vw;
        }}

        #top-bar {{
            width: 100%; background: #1a0620; padding: 5px 0;
            display: flex; justify-content: space-around; align-items: center;
            border-bottom: 1px solid #bd93f9; font-size: 12px;
            z-index: 10; height: 40px;
        }}
        .score-pill {{ background: rgba(189, 147, 249, 0.2); padding: 2px 8px; border-radius: 10px; }}
        .vol-control {{ display: flex; align-items: center; gap: 5px; font-size: 10px; color: #bd93f9; }}
        input[type=range] {{ width: 60px; height: 5px; }}

        canvas {{ 
            background-color: #000; border: 2px solid #444; 
            width: 95vw; max-width: 600px; height: auto; aspect-ratio: 6/5;
            image-rendering: pixelated; margin-top: 5px;
        }}

        /* --- 修正: 手機登入介面絕對置中 (使用 Flexbox + Fixed Fullscreen) --- */
        #login-overlay {{
            position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            width: 100vw; height: 100vh;
            background: rgba(13, 2, 17, 0.98); 
            z-index: 10000; /* 確保最上層 */
            display: flex; flex-direction: column; align-items: center; justify-content: center;
            /* 針對手機瀏覽器網址列導致高度變化的修正 */
            min-height: -webkit-fill-available;
        }}
        
        #login-box {{
            text-align: center; padding: 20px;
        }}

        input {{ margin: 10px; padding: 10px; font-size: 16px; width: 200px; text-align: center; }}
        button {{ padding: 10px 30px; font-size: 16px; background: #50fa7b; border: none; border-radius: 5px; }}

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
            background: #333; border: 1px solid #555; transform: skewX(-15deg);
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
        <div id="login-box">
            <h1 style="color: #50fa7b; font-size: 2em; margin-bottom: 10px;">🦠 CELL WARS</h1>
            <p style="color: #aaa; font-size: 12px; margin-bottom: 20px;">
                1. Kill Elite -> Wait -> Boss<br>
                2. Kill Boss -> Kill 10 Elites -> Boss
            </p>
            <input type="text" id="name-input" placeholder="Enter Name" maxlength="8">
            <br>
            <button id="start-btn">START GAME</button>
        </div>
    </div>

    <div id="top-bar">
        <div class="vol-control">BGM <input type="range" id="vol-bgm" min="0" max="1" step="0.1" value="0.4"></div>
        <div id="lb-content">Connecting...</div>
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
        let sfxVolume = 0.6;

        document.getElementById('vol-bgm').addEventListener('input', (e) => {{ audioFiles.bgm.volume = parseFloat(e.target.value); }});
        document.getElementById('vol-sfx').addEventListener('input', (e) => {{ sfxVolume = parseFloat(e.target.value); }});

        function playSfx(key) {{
            const s = audioFiles[key];
            if(s) {{ s.volume = sfxVolume; s.currentTime = 0; s.play().catch(e => console.log(e)); }}
        }}
        function playLocalShoot() {{ playSfx('p_shot'); }}

        const skins = {{ cells: [], viruses: [], boss: null }};
        function loadImg(path) {{
            let img = new Image(); img.src = path;
            img.onerror = () => {{ img.isBroken = true; }};
            return img;
        }}
        for(let i=1; i<=3; i++) {{
            skins.cells.push(loadImg(assetsBase + "cell_" + i + ".png"));
            skins.viruses.push(loadImg(assetsBase + "virus_" + i + ".png"));
        }}
        skins.boss = loadImg(assetsBase + "boss_1.png");

        let gameState = {{ players: {{}}, enemies: {{}}, bullets: [], skill_objects: [], w: false }};
        let myId = null;

        socket.on('connect', () => {{ myId = socket.id; }});
        socket.on('sfx', (data) => {{
            switch(data.type) {{
                case 'character_hitted': playSfx('p_hit'); break;
                case 'boss_coming': playSfx('boss_come'); break;
                case 'boss_hitted': playSfx('boss_hit'); break;
                case 'boss_shot': playSfx('boss_shot'); break;
                case 'enemy_hitted': playSfx('e_hit'); break;
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
            document.getElementById('lb-content').innerHTML = sorted.map((p, i) => `<span class="score-pill">${{i==0?'👑':''}}${{p.name}}:${{p.score}}</span>`).join('');

            for(let i=1; i<=3; i++) {{
                const elSeg = document.getElementById('seg'+i);
                const elFill = document.getElementById('fill'+i);
                if (me.charge >= i) {{ elSeg.classList.add('full'); elFill.style.width = '100%'; }}
                else if (me.charge === i - 1) {{ elSeg.classList.remove('full'); elFill.style.width = ((me.hit_accumulated / 20) * 100) + '%'; }}
                else {{ elSeg.classList.remove('full'); elFill.style.width = '0%'; }}
            }}
            const btn = document.getElementById('skill-btn');
            if (me.charge >= 1) btn.classList.remove('disabled'); else btn.classList.add('disabled');
        }}

        function drawBossWarning() {{
            if (!gameState.w) return; // Server 說要顯示才顯示
            
            // 在畫面中間畫一個黃色三角形警告
            const cx = canvas.width / 2;
            const cy = canvas.height / 2;
            
            ctx.save();
            ctx.globalAlpha = 0.5; // 半透明
            ctx.fillStyle = "yellow";
            ctx.beginPath();
            ctx.moveTo(cx, cy - 50);
            ctx.lineTo(cx + 50, cy + 50);
            ctx.lineTo(cx - 50, cy + 50);
            ctx.closePath();
            ctx.fill();
            
            ctx.globalAlpha = 1.0;
            ctx.fillStyle = "black";
            ctx.font = "bold 40px Arial";
            ctx.textAlign = "center";
            ctx.fillText("!", cx, cy + 25);
            
            ctx.fillStyle = "red";
            ctx.font = "16px Courier New";
            ctx.fillText("WARNING", cx, cy + 70);
            ctx.restore();
        }}

        function draw() {{
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            // 1. 技能
            ctx.globalAlpha = 0.7;
            if (gameState.skill_objects) {{
                gameState.skill_objects.forEach(obj => {{
                    let img = skins.cells[(obj.skin || 1) - 1];
                    if(img && img.complete && !img.isBroken) ctx.drawImage(img, obj.x, obj.y, 30, 30);
                    else {{ ctx.beginPath(); ctx.arc(obj.x, obj.y, 15, 0, Math.PI*2); ctx.fillStyle="#8be9fd"; ctx.fill(); }}
                }});
            }}
            ctx.globalAlpha = 1.0;

            // 2. 敵人
            for (let id in gameState.enemies) {{
                let e = gameState.enemies[id];
                if (e.type === 999) {{
                    let img = skins.boss; 
                    if(img && img.complete && !img.isBroken) ctx.drawImage(img, e.x, e.y, e.size, e.size);
                    else {{ ctx.fillStyle = "purple"; ctx.fillRect(e.x, e.y, e.size, e.size); }}
                    ctx.fillStyle = "#555"; ctx.fillRect(e.x, e.y-10, e.size, 8);
                    ctx.fillStyle = "#bd93f9"; ctx.fillRect(e.x, e.y-10, e.size * (e.hp/e.max_hp), 8);
                }} else {{
                    let img = skins.viruses[(e.type || 1) - 1];
                    if(img && img.complete) ctx.drawImage(img, e.x, e.y, e.size, e.size);
                    else {{ ctx.fillStyle = "red"; ctx.fillRect(e.x, e.y, e.size, e.size); }}
                    ctx.fillStyle = "#555"; ctx.fillRect(e.x, e.y-6, e.size, 3);
                    ctx.fillStyle = "#ff5555"; ctx.fillRect(e.x, e.y-6, e.size * (e.hp/e.max_hp), 3);
                }}
            }}

            // 3. 玩家
            for (let id in gameState.players) {{
                let p = gameState.players[id];
                let img = skins.cells[(p.skin || 1) - 1];
                if(img && img.complete) ctx.drawImage(img, p.x, p.y, 30, 30);
                else {{ ctx.fillStyle = p.c; ctx.fillRect(p.x, p.y, 30, 30); }}
                ctx.fillStyle = (id === myId) ? "#f1fa8c" : "white";
                ctx.font = "12px Arial"; ctx.textAlign = "center";
                ctx.fillText(p.name, p.x+15, p.y-15);
                ctx.fillStyle = "#444"; ctx.fillRect(p.x, p.y-10, 30, 4);
                ctx.fillStyle = "#50fa7b"; ctx.fillRect(p.x, p.y-10, 30 * (p.hp / p.max_hp), 4);
            }}

            // 4. 子彈
            gameState.bullets.forEach(b => {{
                ctx.beginPath();
                if (b.owner === 'boss') {{ ctx.fillStyle = '#bd93f9'; ctx.arc(b.x, b.y, 8, 0, Math.PI*2); }}
                else if (b.owner === 'enemy') {{ ctx.fillStyle = '#ff5555'; ctx.moveTo(b.x, b.y+5); ctx.lineTo(b.x-4, b.y-4); ctx.lineTo(b.x+4, b.y-4); }}
                else {{ ctx.fillStyle = (b.owner === myId) ? '#f1fa8c' : '#8be9fd'; ctx.arc(b.x, b.y, 4, 0, Math.PI*2); }}
                ctx.fill();
            }});
            
            // 5. 警告圖層 (畫在最上面)
            drawBossWarning();
        }}

        const manager = nipplejs.create({{
            zone: document.getElementById('joystick-zone'),
            mode: 'static', position: {{left: '50%', top: '50%'}}, size: 100, color: 'white'
        }});
        manager.on('move', (evt, data) => {{ if(data.vector) socket.emit('move', {{ dx: data.vector.x, dy: -data.vector.y }}); }});
        manager.on('end', () => socket.emit('move', {{ dx: 0, dy: 0 }}));

        document.getElementById('start-btn').onclick = () => {{
            const name = document.getElementById('name-input').value.trim() || "Hero";
            socket.emit('join_game', {{ name: name }});
            document.getElementById('login-overlay').style.display = 'none';
            audioFiles.bgm.play().catch(e => console.log(e));
        }};

        const fireBtn = document.getElementById('fire-btn');
        let fireInterval;
        const startFire = (e) => {{ e.preventDefault(); playLocalShoot(); socket.emit('shoot'); fireInterval = setInterval(()=> {{ socket.emit('shoot'); playLocalShoot(); }}, 250); }};
        const stopFire = () => clearInterval(fireInterval);
        fireBtn.addEventListener('touchstart', startFire); fireBtn.addEventListener('touchend', stopFire);
        fireBtn.addEventListener('mousedown', startFire); fireBtn.addEventListener('mouseup', stopFire);

        const skillBtn = document.getElementById('skill-btn');
        const castSkill = (e) => {{ e.preventDefault(); socket.emit('use_skill'); }};
        skillBtn.addEventListener('touchstart', castSkill); skillBtn.addEventListener('mousedown', castSkill);

        document.addEventListener('keydown', (e) => {{
            if (e.code === 'Space') {{ socket.emit('shoot'); playLocalShoot(); }}
            if (e.key === 'q') socket.emit('use_skill');
        }});
    </script>
</body>
</html>
"""

components.html(html_code, height=850)
