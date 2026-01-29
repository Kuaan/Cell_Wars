import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Cell Wars 3.0 - Boss Coming !!", layout="wide")

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

# 注意：這裡的 {{ }} 是為了避開 Python f-string 的語法衝突
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
            touch-action: none; height: 100vh;
        }}
        
        #login-overlay {{
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(13, 2, 17, 0.98); z-index: 100; 
            display: flex; flex-direction: column; 
            align-items: center; justify-content: center;
            text-align: center;
        }}

        #name-input {{
            padding: 12px; width: 200px; border: 2px solid #50fa7b;
            background: #1a0620; color: #fff; border-radius: 5px;
            outline: none; margin-bottom: 15px;
        }}

        #start-btn {{
            padding: 12px 40px; background: #50fa7b; border: none;
            border-radius: 5px; font-weight: bold; cursor: pointer;
        }}

        #top-bar {{
            width: 100%; background: #1a0620; padding: 5px 0;
            display: flex; justify-content: center; gap: 10px;
            border-bottom: 1px solid #bd93f9; font-size: 12px;
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
        #joystick-zone {{ width: 150px; height: 150px; }}

        .btn-fire {{
            width: 70px; height: 70px; background: #ff5555; border-radius: 50%;
            border: 3px solid #ff9999; display: flex; align-items: center; 
            justify-content: center; font-weight: bold;
        }}

        .btn-skill {{
            width: 50px; height: 50px; background: #8be9fd; border-radius: 50%;
            border: 3px solid cyan; display: flex; align-items: center; 
            justify-content: center; font-size: 12px; font-weight: bold; color: #000;
        }}
        .btn-skill.disabled {{ filter: grayscale(100%); opacity: 0.5; }}

        #charge-container {{ 
            display: flex; gap: 4px; margin-bottom: 8px; background: #222; 
            padding: 4px; border-radius: 4px; border: 1px solid #444;
        }}
        .charge-bar-segment {{ position: relative; width: 30px; height: 12px; background: #333; transform: skewX(-15deg); }}
        .charge-fill {{ position: absolute; bottom: 0; left: 0; width: 0%; height: 100%; background: #f1fa8c; }}
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

    <div id="top-bar"><div id="lb-content">Connecting...</div></div>
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
            document.getElementById('lb-content').innerHTML = sorted.map((p, i) => `<span class="score-pill">${{i==0?'👑':''}}${{p.name}}:${{p.score}}</span>`).join('');

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
            document.getElementById('skill-btn').classList.toggle('disabled', me.charge < 1);
        }}

        function draw() {{
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            if (gameState.skill_objects) {{
                ctx.globalAlpha = 0.7;
                gameState.skill_objects.forEach(obj => {{
                    let img = skins.cells[(obj.skin || 1) - 1];
                    if(img && img.complete) ctx.drawImage(img, obj.x, obj.y, 30, 30);
                }});
                ctx.globalAlpha = 1.0;
            }}
            for (let id in gameState.enemies) {{
                let e = gameState.enemies[id];
                if (e.type === 999) {{
                    if(skins.boss.complete) ctx.drawImage(skins.boss, e.x, e.y, e.size, e.size);
                }} else {{
                    let img = skins.viruses[(e.type || 1) - 1];
                    if(img && img.complete) ctx.drawImage(img, e.x, e.y, e.size, e.size);
                }}
            }}
            for (let id in gameState.players) {{
                let p = gameState.players[id];
                let img = skins.cells[(p.skin || 1) - 1];
                if(img && img.complete) ctx.drawImage(img, p.x, p.y, 30, 30);
            }}
            gameState.bullets.forEach(b => {{
                ctx.beginPath();
                ctx.fillStyle = (b.owner === 'boss') ? '#bd93f9' : (b.owner === 'enemy' ? '#ff5555' : '#8be9fd');
                ctx.arc(b.x, b.y, b.size || 4, 0, Math.PI*2);
                ctx.fill();
            }});
        }}

        nipplejs.create({{ zone: document.getElementById('joystick-zone'), mode: 'static', position: {{left:'50%', top:'50%'}}, size: 100 }}).on('move', (evt, data) => {{
            if(data.vector) socket.emit('move', {{ dx: data.vector.x, dy: -data.vector.y }});
        }}).on('end', () => socket.emit('move', {{ dx: 0, dy: 0 }}));

        document.getElementById('start-btn').onclick = () => {{
            socket.emit('join_game', {{ name: document.getElementById('name-input').value || "Hero" }});
            document.getElementById('login-overlay').style.display = 'none';
            audioFiles.bgm.play().catch(e => {{}});
        }};

        const fireBtn = document.getElementById('fire-btn');
        let fireInterval;
        fireBtn.onmousedown = fireBtn.ontouchstart = (e) => {{
            e.preventDefault(); playSfx('p_shot'); socket.emit('shoot');
            fireInterval = setInterval(()=> {{ socket.emit('shoot'); playSfx('p_shot'); }}, 250);
        }};
        fireBtn.onmouseup = fireBtn.ontouchend = () => clearInterval(fireInterval);

        document.getElementById('skill-btn').onclick = () => socket.emit('use_skill');
    </script>
</body>
</html>
"""

components.html(html_code, height=850)
