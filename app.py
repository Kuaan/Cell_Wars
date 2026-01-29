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
        /* 基礎設定 */
        * {{ box-sizing: border-box; }}
        body {{ 
            background-color: #0d0211; color: #fff; margin: 0; padding: 0;
            font-family: 'Courier New', monospace; overflow: hidden; 
            display: flex; flex-direction: column; align-items: center;
            height: 100vh; width: 100vw;
        }}

        /* --- 強制置頂登入介面 --- */
        #login-overlay {{
            position: fixed; 
            top: 0; left: 0; 
            width: 100%; 
            height: 100%; 
            background: #0d0211; /* 完全不透明，擋住後方內容 */
            z-index: 99999;     /* 極高層級 */
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: flex-start; /* 改為從頂部開始排，避免被鍵盤推擠 */
            padding-top: 20%;            /* 距離頂部 20% */
        }}

        #login-box {{
            background: #1a0620;
            padding: 30px;
            border-radius: 15px;
            border: 2px solid #50fa7b;
            text-align: center;
            width: 85%;
            max-width: 400px;
        }}

        input {{ 
            margin: 15px 0; 
            padding: 12px; 
            font-size: 18px; 
            width: 100%; 
            text-align: center; 
            background: #222;
            color: #fff;
            border: 1px solid #444;
            border-radius: 8px;
        }}

        button {{ 
            padding: 15px 40px; 
            font-size: 18px; 
            background: #50fa7b; 
            color: #000;
            border: none; 
            border-radius: 8px; 
            font-weight: bold;
            width: 100%;
            cursor: pointer;
        }}

        /* 遊戲介面元件 */
        #top-bar {{
            width: 100%; background: #1a0620; padding: 5px 0;
            display: flex; justify-content: space-around; align-items: center;
            border-bottom: 1px solid #bd93f9; font-size: 12px;
            height: 40px; flex-shrink: 0;
        }}
        .vol-control {{ display: flex; align-items: center; gap: 5px; font-size: 10px; color: #bd93f9; }}
        input[type=range] {{ width: 50px; }}

        canvas {{ 
            background-color: #000; border: 2px solid #444; 
            width: 95vw; max-width: 600px; height: auto; aspect-ratio: 6/5;
            image-rendering: pixelated; margin-top: 5px;
        }}

        #ui-container {{
            width: 95vw; max-width: 600px; height: 160px;
            margin-top: 10px; display: flex; justify-content: space-between; align-items: center;
        }}
        #joystick-zone {{ width: 120px; height: 120px; }}
        #actions-zone {{ display: flex; flex-direction: column; align-items: flex-end; gap: 10px; }}

        .btn-fire {{
            width: 70px; height: 70px; background: #ff5555; border-radius: 50%;
            border: 3px solid #ff9999; display: flex; align-items: center; justify-content: center;
            font-weight: bold; box-shadow: 0 4px 0 #b30000;
        }}
        .btn-skill {{
            width: 50px; height: 50px; background: #8be9fd; border-radius: 50%;
            border: 3px solid #cyan; display: flex; align-items: center; justify-content: center;
            font-size: 12px; font-weight: bold; color: #000;
        }}
        .btn-skill.disabled {{ opacity: 0.3; }}

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
            <p style="color: #aaa; font-size: 12px; line-height: 1.5;">
                擊敗菁英怪以觸發魔王出現<br>
                魔王死後需再擊殺 10 隻菁英怪重生
            </p>
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
        // 伺服器連接設定
        const socket = io("{SERVER_URL}", {{ reconnection: true }});
        const canvas = document.getElementById('gameCanvas');
        const ctx = canvas.getContext('2d');
        const assetsBase = "{ASSETS_BASE}";
        const soundsBase = "{SOUNDS_BASE}";

        // 音頻資源
        const audioFiles = {{
            bgm: new Audio(soundsBase + "bgm/bgm-145a.wav"),
            p_hit: new Audio(soundsBase + "characters/character_hitted.wav"),
            p_shot: new Audio(soundsBase + "characters/character_nor_shot.wav"),
            boss_come: new Audio(soundsBase + "enemy/boss_coming.wav"),
            boss_hit: new Audio(soundsBase + "enemy/boss_hitted.wav"),
            boss_shot: new Audio(soundsBase + "enemy/boss_shot.wav"), 
            e_hit: new Audio(soundsBase + "enemy/enemy_hitted.wav"),
            skill: new Audio(soundsBase + "skill/slime.wav")
        }};
        audioFiles.bgm.loop = true;
        let sfxVolume = 0.6;

        // 音量控制監聽
        document.getElementById('vol-bgm').addEventListener('input', (e) => {{ audioFiles.bgm.volume = parseFloat(e.target.value); }});
        document.getElementById('vol-sfx').addEventListener('input', (e) => {{ sfxVolume = parseFloat(e.target.value); }});

        function playSfx(key) {{
            const s = audioFiles[key];
            if(s) {{ s.volume = sfxVolume; s.currentTime = 0; s.play().catch(e => {{}}); }}
        }}

        // 圖片資源載入
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
            
            // 排行榜
            const sorted = Object.values(gameState.players).sort((a,b)=>b.score-a.score).slice(0,3);
            document.getElementById('lb-content').innerHTML = sorted.map((p, i) => 
                `<span class="score-pill">${{i==0?'👑':''}}${{p.name}}:${{p.score}}</span>`
            ).join('');

            // 能量條
            for(let i=1; i<=3; i++) {{
                const elSeg = document.getElementById('seg'+i);
                const elFill = document.getElementById('fill'+i);
                if (me.charge >= i) {{ 
                    elSeg.classList.add('full'); elFill.style.width = '100%'; 
                }} else if (me.charge === i - 1) {{ 
                    elSeg.classList.remove('full'); elFill.style.width = ((me.hit_accumulated / 20) * 100) + '%'; 
                }} else {{ 
                    elSeg.classList.remove('full'); elFill.style.width = '0%'; 
                }}
            }}
            const btn = document.getElementById('skill-btn');
            if (me.charge >= 1) btn.classList.remove('disabled'); else btn.classList.add('disabled');
        }}

        function draw() {{
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            // 1. 技能
            ctx.globalAlpha = 0.6;
            (gameState.skill_objects || []).forEach(obj => {{
                let img = skins.cells[(obj.skin || 1) - 1];
                if(img && img.complete) ctx.drawImage(img, obj.x, obj.y, 30, 30);
            }});
            ctx.globalAlpha = 1.0;

            // 2. 敵人
            for (let id in gameState.enemies) {{
                let e = gameState.enemies[id];
                if (e.type === 999) {{
                    if(skins.boss.complete) ctx.drawImage(skins.boss, e.x, e.y, e.size, e.size);
                    ctx.fillStyle = "#555"; ctx.fillRect(e.x, e.y-10, e.size, 8);
                    ctx.fillStyle = "#bd93f9"; ctx.fillRect(e.x, e.y-10, e.size * (e.hp/e.max_hp), 8);
                } else {{
                    let img = skins.viruses[(e.type || 1) - 1];
                    if(img && img.complete) ctx.drawImage(img, e.x, e.y, e.size, e.size);
                    ctx.fillStyle = "#555"; ctx.fillRect(e.x, e.y-6, e.size, 3);
                    ctx.fillStyle = "#ff5555"; ctx.fillRect(e.x, e.y-6, e.size * (e.hp/e.max_hp), 3);
                }}
            }}

            // 3. 玩家
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

            // 4. 子彈
            gameState.bullets.forEach(b => {{
                ctx.beginPath();
                if (b.owner === 'boss') {{ ctx.fillStyle = '#bd93f9'; ctx.arc(b.x, b.y, 8, 0, Math.PI*2); }}
                else if (b.owner === 'enemy') {{ ctx.fillStyle = '#ff5555'; ctx.arc(b.x, b.y, 3, 0, Math.PI*2); }}
                else {{ ctx.fillStyle = (b.owner === myId) ? '#f1fa8c' : '#8be9fd'; ctx.arc(b.x, b.y, 4, 0, Math.PI*2); }}
                ctx.fill();
            }});

            // 5. Boss 警告
            if (gameState.w) {{
                ctx.save();
                ctx.globalAlpha = 0.6;
                ctx.fillStyle = "yellow";
                const cx = canvas.width / 2;
                const cy = canvas.height / 2;
                ctx.beginPath();
                ctx.moveTo(cx, cy - 40); ctx.lineTo(cx + 40, cy + 40); ctx.lineTo(cx - 40, cy + 40);
                ctx.closePath(); ctx.fill();
                ctx.fillStyle = "black"; ctx.font = "bold 30px Arial"; ctx.fillText("!", cx, cy + 25);
                ctx.restore();
            }}
        }}

        // 搖桿
        const manager = nipplejs.create({{
            zone: document.getElementById('joystick-zone'),
            mode: 'static', position: {{left: '50%', top: '50%'}}, size: 100, color: 'white'
        }});
        manager.on('move', (evt, data) => {{ if(data.vector) socket.emit('move', {{ dx: data.vector.x, dy: -data.vector.y }}); }});
        manager.on('end', () => socket.emit('move', {{ dx: 0, dy: 0 }}));

        // 登入事件
        document.getElementById('start-btn').onclick = () => {{
            const name = document.getElementById('name-input').value.trim() || "Cell";
            socket.emit('join_game', {{ name: name }});
            document.getElementById('login-overlay').style.display = 'none';
            audioFiles.bgm.play().catch(e => {{}});
        }};

        // 射擊
        const fireBtn = document.getElementById('fire-btn');
        let fireInterval;
        const shoot = (e) => {{ 
            e.preventDefault(); 
            socket.emit('shoot'); 
            playSfx('p_shot'); 
            if(!fireInterval) fireInterval = setInterval(()=> {{ socket.emit('shoot'); playSfx('p_shot'); }}, 250); 
        }};
        fireBtn.addEventListener('touchstart', shoot);
        fireBtn.addEventListener('touchend', () => {{ clearInterval(fireInterval); fireInterval = null; }});
        fireBtn.addEventListener('mousedown', shoot);
        fireBtn.addEventListener('mouseup', () => {{ clearInterval(fireInterval); fireInterval = null; }});

        // 技能
        document.getElementById('skill-btn').addEventListener('touchstart', (e) => {{ e.preventDefault(); socket.emit('use_skill'); }});
        document.getElementById('skill-btn').addEventListener('mousedown', (e) => {{ e.preventDefault(); socket.emit('use_skill'); }});

        // 鍵盤支援
        document.addEventListener('keydown', (e) => {{
            if (e.code === 'Space') {{ socket.emit('shoot'); playSfx('p_shot'); }}
            if (e.key === 'q') socket.emit('use_skill');
        }});
    </script>
</body>
</html>
"""

components.html(html_code, height=800)
