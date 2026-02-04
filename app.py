#v4.0 app.py
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Cell Wars V5", layout="wide")

# 設定伺服器與資源路徑
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
        * {{ box-sizing: border-box; }}
        body {{ 
            background-color: #0d0211; color: #fff; margin: 0; padding: 0;
            font-family: 'Courier New', monospace; overflow: hidden; 
            display: flex; flex-direction: column; align-items: center;
            height: 100vh; width: 100vw;
        }}

        /* 登入介面 */
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
        button {{ padding: 15px 40px; font-size: 18px; background: #50fa7b; color: #000; border: none; border-radius: 8px; font-weight: bold; width: 100%; cursor: pointer; transition: 0.3s; }}
        button:disabled {{ background: #555; color: #888; cursor: not-allowed; }}

        #top-bar {{
            width: 100%; background: #1a0620; padding: 5px 0;
            display: flex; justify-content: space-around; align-items: center;
            border-bottom: 1px solid #bd93f9; font-size: 12px;
            height: 40px; flex-shrink: 0;
        }}
        .vol-control {{ display: flex; align-items: center; gap: 5px; font-size: 10px; color: #bd93f9; }}
        input[type=range] {{ width: 50px; cursor: pointer; }}

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
        #actions-zone {{ display: flex; flex-direction: column; align-items: flex-end; gap: 10px; }}

        .btn-fire {{
            width: 75px; height: 75px; background: #ff5555; border-radius: 50%;
            border: 3px solid #ff9999; display: flex; align-items: center; justify-content: center;
            font-weight: bold; font-size: 30px; /* 加大字體以顯示 Emoji */
            box-shadow: 0 4px 0 #b30000; touch-action: none; user-select: none;
            overflow: hidden;
            transition: transform 0.1s;
        }}
        .btn-fire:active {{ box-shadow: 0 0 0; transform: translateY(4px); }}
        
        .btn-skill {{
            width: 55px; height: 55px; background: #8be9fd; border-radius: 50%;
            border: 3px solid #cyan; display: flex; align-items: center; justify-content: center;
            font-size: 12px; font-weight: bold; color: #000; touch-action: none; user-select: none;
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
            <h1 style="color: #50fa7b; margin: 0 0 10px 0;">🦠 CELL WARS V5</h1>
            <p style="color: #aaa; font-size: 12px;">Weapon System Online</p>
            <input type="text" id="name-input" placeholder="輸入名稱" maxlength="8">
            <button id="start-btn" disabled>資源載入中...</button>
        </div>
    </div>

    <div id="top-bar">
        <div class="vol-control">BGM <input type="range" id="vol-bgm" min="0" max="1" step="0.1" value="0.4"></div>
        <div id="lb-content">...</div>
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
                <div class="btn-fire" id="fire-btn">🔥</div>
            </div>
        </div>
    </div>

    <script>
        const socket = io("{SERVER_URL}", {{ reconnection: true }});
        const canvas = document.getElementById('gameCanvas');
        const ctx = canvas.getContext('2d');
        const assetsBase = "{ASSETS_BASE}";
        const soundsBase = "{SOUNDS_BASE}";

        // --- Web Audio API ---
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        const audioCtx = new AudioContext();
        
        const gainNodeBGM = audioCtx.createGain();
        const gainNodeSFX = audioCtx.createGain();
        gainNodeBGM.connect(audioCtx.destination);
        gainNodeSFX.connect(audioCtx.destination);

        const audioBuffers = {{}};
        const bgmSourceNode = {{ current: null }};

        let volBGM = 0.4;
        let volSFX = 0.6;
        gainNodeBGM.gain.value = volBGM;
        gainNodeSFX.gain.value = volSFX;

        const soundList = {{
            bgm: soundsBase + "bgm/bgm-145a.wav",
            p_hit: soundsBase + "characters/character_hitted.wav",
            p_shot: soundsBase + "characters/character_nor_shot.wav",
            boss_come: soundsBase + "enemy/boss_coming.wav",
            boss_hit: soundsBase + "enemy/boss_hitted.wav",
            boss_shot: soundsBase + "enemy/boss_shot.wav",
            e_hit: soundsBase + "enemy/enemy_hitted.wav",
            e_shot: soundsBase + "enemy/enemy_nor_shot.wav",
            skill: soundsBase + "skill/slime.wav",
            powerup: soundsBase + "skill/slime.wav" // 暫時共用音效
        }};

        async function loadSound(key, url) {{
            try {{
                const response = await fetch(url);
                const arrayBuffer = await response.arrayBuffer();
                const decodedBuffer = await audioCtx.decodeAudioData(arrayBuffer);
                audioBuffers[key] = decodedBuffer;
            }} catch(e) {{ console.error(`Error loading ${{key}}:`, e); }}
        }}

        Promise.all(Object.keys(soundList).map(key => loadSound(key, soundList[key]))).then(() => {{
            const btn = document.getElementById('start-btn');
            btn.innerText = "進入戰場";
            btn.disabled = false;
        }});

        function playSfx(key) {{
            if (volSFX <= 0.01 || !audioBuffers[key]) return;
            const source = audioCtx.createBufferSource();
            source.buffer = audioBuffers[key];
            source.connect(gainNodeSFX);
            source.start(0);
        }}

        function playBGM() {{
            if (!audioBuffers['bgm']) return;
            if (bgmSourceNode.current) {{ try {{ bgmSourceNode.current.stop(); }} catch(e) {{}} }}
            const source = audioCtx.createBufferSource();
            source.buffer = audioBuffers['bgm'];
            source.loop = true;
            source.connect(gainNodeBGM);
            source.start(0);
            bgmSourceNode.current = source;
        }}

        document.getElementById('vol-bgm').oninput = function() {{
            volBGM = parseFloat(this.value);
            gainNodeBGM.gain.setTargetAtTime(volBGM, audioCtx.currentTime, 0.1);
            if (volBGM > 0 && audioCtx.state === 'suspended') audioCtx.resume();
        }};
        document.getElementById('vol-sfx').oninput = function() {{
            volSFX = parseFloat(this.value);
            gainNodeSFX.gain.setTargetAtTime(volSFX, audioCtx.currentTime, 0.1);
        }};

        // --- 圖片載入 ---
        const skins = {{ cells: [], viruses: [], boss: null }};
        function loadImg(path) {{
            let img = new Image(); img.src = path;
            return img;
        }}
        
        // 載入角色與敵人
        for(let i=1; i<=3; i++) {{
            skins.cells.push(loadImg(assetsBase + "cell_" + i + ".png"));
            skins.viruses.push(loadImg(assetsBase + "virus_" + i + ".png"));
        }}
        skins.boss = loadImg(assetsBase + "boss_1.png");

        let gameState = {{ players: {{}}, enemies: {{}}, bullets: [], items: [], skill_objects: [], w: false }};
        let myId = null;
        let lastShotTime = 0;

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
                case 'powerup': playSfx('powerup'); break; // 新增道具音效
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
            document.getElementById('lb-content').innerHTML = sorted.map((p, i) => `<span class="score-pill">${{i==0?'👑':''}}${{p.name}}:${{p.score}}</span>`).join('');

            // 能量條
            for(let i=1; i<=3; i++) {{
                const elSeg = document.getElementById('seg'+i);
                const elFill = document.getElementById('fill'+i);
                if (me.charge >= i) {{ elSeg.classList.add('full'); elFill.style.width = '100%'; }}
                else if (me.charge === i - 1) {{ elSeg.classList.remove('full'); elFill.style.width = ((me.hit_accumulated / 20) * 100) + '%'; }}
                else {{ elSeg.classList.remove('full'); elFill.style.width = '0%'; }}
            }}
            
            // 技能按鈕
            const sBtn = document.getElementById('skill-btn');
            if (me.charge >= 1) sBtn.classList.remove('disabled'); else sBtn.classList.add('disabled');

            // --- 武器按鈕 (直接顯示後端傳來的 Emoji) ---
            const fBtn = document.getElementById('fire-btn');
            if (me.w_icon && fBtn.innerText !== me.w_icon) {{
                fBtn.innerText = me.w_icon; 
            }}
        }}

        function draw() {{
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            // 1. 繪製道具 (Items) - 使用色塊代替圖片
            if (gameState.items) {{
                gameState.items.forEach(item => {{
                    // 根據 type 決定顏色
                    let color = '#ffffff';
                    if (item.type.includes('spread')) color = '#ffff00';     // 黃色
                    else if (item.type.includes('ricochet')) color = '#00ffff'; // 青色
                    else if (item.type.includes('arc')) color = '#ff00ff';      // 紫色
                    else if (item.type.includes('heal')) color = '#50fa7b';     // 綠色

                    ctx.save();
                    ctx.shadowColor = color;
                    ctx.shadowBlur = 15;
                    ctx.fillStyle = color;
                    
                    // 繪製膠囊形狀 (這裡簡化為圓形，因為像素畫風圓形也很清楚)
                    ctx.beginPath();
                    ctx.arc(item.x + 10, item.y + 10, 12, 0, Math.PI * 2);
                    ctx.fill();
                    
                    // 加上白色核心讓它看起來像發光體
                    ctx.fillStyle = '#ffffff';
                    ctx.beginPath();
                    ctx.arc(item.x + 10, item.y + 10, 5, 0, Math.PI * 2);
                    ctx.fill();
                    
                    ctx.restore();
                }});
            }}

            // 2. 繪製技能物件
            ctx.globalAlpha = 0.6;
            (gameState.skill_objects || []).forEach(obj => {{
                let img = skins.cells[(obj.skin || 1) - 1];
                if(img && img.complete) ctx.drawImage(img, obj.x, obj.y, 30, 30);
            }});
            ctx.globalAlpha = 1.0;

            // 3. 繪製敵人
            for (let id in gameState.enemies) {{
                let e = gameState.enemies[id];
                if (e.type === 999) {{
                    if(skins.boss.complete) ctx.drawImage(skins.boss, e.x, e.y, e.size, e.size);
                    const hpRatio = Math.max(0, e.hp / e.max_hp);
                    ctx.fillStyle = "#bd93f9"; ctx.fillRect(e.x, e.y-10, e.size * hpRatio, 8);
                }} else {{
                    let img = skins.viruses[(e.type || 1) - 1];
                    if(img && img.complete) ctx.drawImage(img, e.x, e.y, e.size, e.size);
                    const hpRatio = Math.max(0, e.hp / e.max_hp);
                    ctx.fillStyle = "#ff5555"; ctx.fillRect(e.x, e.y-6, e.size * hpRatio, 3);
                }}
            }}

            // 4. 繪製玩家 (含命數顯示)
            for (let id in gameState.players) {{
                let p = gameState.players[id];
                if (p.invincible) ctx.globalAlpha = 0.5;
                
                let img = skins.cells[(p.skin || 1) - 1];
                if(img && img.complete) ctx.drawImage(img, p.x, p.y, 30, 30);
                
                ctx.globalAlpha = 1.0;
                
                // 名字與血條
                ctx.fillStyle = (id === myId) ? "#f1fa8c" : "white";
                ctx.font = "12px Courier New";
                
                // 計算命數 (假設一條命為 5 HP，需與後端 Config 同步，這裡做視覺估算)
                // 顯示邏輯：總血量 / 單條命最大血量 (後端沒傳單條命最大值，這裡暫時寫死 5 或根據比例)
                // 更好的方式：後端傳 lives_count，但目前只有 hp/max_hp。
                // 變通：顯示 "❤️ x N"
                let estimatedLives = Math.ceil(p.hp / (p.max_hp / 5)); // 假設5條命
                ctx.fillText(p.name + " ❤️x" + estimatedLives, p.x, p.y-15);

                // 血條顯示 (顯示當前這條命的殘血)
                let currentLifeHp = p.hp % (p.max_hp / 5);
                if (currentLifeHp === 0 && p.hp > 0) currentLifeHp = (p.max_hp / 5);
                let maxLifeHp = (p.max_hp / 5);
                
                const hpRatio = Math.max(0, currentLifeHp / maxLifeHp);
                ctx.fillStyle = "#50fa7b"; 
                ctx.fillRect(p.x, p.y-10, 30 * hpRatio, 4);
                
                // 血條外框
                ctx.strokeStyle = "#fff";
                ctx.lineWidth = 1;
                ctx.strokeRect(p.x, p.y-10, 30, 4);
            }}

            // 5. 繪製子彈 (支援後端傳來的顏色與大小)
            gameState.bullets.forEach(b => {{
                ctx.beginPath();
                // 優先使用後端傳來的顏色 (b.c)，沒有則用預設邏輯
                if (b.c) {{
                    ctx.fillStyle = b.c;
                }} else {{
                    if (b.owner === 'boss') ctx.fillStyle = '#bd93f9';
                    else if (b.owner === 'enemy') ctx.fillStyle = '#ff5555';
                    else ctx.fillStyle = (b.owner === myId) ? '#f1fa8c' : '#8be9fd';
                }}
                
                // 使用後端傳來的尺寸 (b.s)，預設為 4
                let size = b.s || 4;
                ctx.arc(b.x, b.y, size, 0, Math.PI*2);
                ctx.fill();
            }});

            // 6. 警告閃爍
            if (gameState.w) {{
                const time = Date.now();
                ctx.save();
                const alpha = 0.2 + 0.15 * Math.sin(time * 0.01);
                ctx.fillStyle = `rgba(255, 0, 0, ${{alpha}})`;
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                ctx.restore();
            }}
        }}

        const manager = nipplejs.create({{
            zone: document.getElementById('joystick-zone'),
            mode: 'static',
            position: {{ left: '70px', top: '70px' }},
            size: 100,
            color: 'white'
        }});
        manager.on('move', (evt, data) => {{ if(data.vector) socket.emit('move', {{ dx: data.vector.x, dy: -data.vector.y }}); }});
        manager.on('end', () => {{ socket.emit('move', {{ dx: 0, dy: 0 }}); }});

        function doFire() {{
            const now = Date.now();
            if (now - lastShotTime < 150) return; // 前端簡單防抖，實際射速由後端控制
            lastShotTime = now;
            socket.emit('shoot');
            playSfx('p_shot');
        }}

        function doSkill() {{ socket.emit('use_skill'); }}

        document.getElementById('fire-btn').addEventListener('touchstart', (e) => {{ e.preventDefault(); doFire(); }});
        document.getElementById('fire-btn').addEventListener('mousedown', (e) => {{ e.preventDefault(); doFire(); }});
        document.getElementById('skill-btn').addEventListener('touchstart', (e) => {{ e.preventDefault(); doSkill(); }});
        document.getElementById('skill-btn').addEventListener('mousedown', (e) => {{ e.preventDefault(); doSkill(); }});

        document.addEventListener('keydown', (e) => {{
            if (e.code === 'Space') doFire();
            if (e.key === 'q' || e.key === 'Q') doSkill();
        }});

        document.getElementById('start-btn').onclick = function() {{
            if (audioCtx.state === 'suspended') {{
                audioCtx.resume().then(() => {{ console.log("AudioContext unlocked"); }});
            }}
            playBGM();
            const name = document.getElementById('name-input').value || 'Cell';
            socket.emit('join_game', {{ name: name }});
            document.getElementById('login-overlay').style.display = 'none';
        }};
    </script>
</body>
</html>
"""
components.html(html_code, height=800)
