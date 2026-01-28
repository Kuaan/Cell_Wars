import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Cell Wars 2.0", layout="wide")

# --- 設定區 ---
GITHUB_USER = "Kuaan"
GITHUB_REPO = "Cell_Wars"
SERVER_URL = "https://cell-wars.onrender.com"
ASSETS_BASE = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/assets/"

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
            touch-action: none; /* 禁止瀏覽器預設滑動 */
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

        /* 登入畫面 */
        #login-overlay {{
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(13, 2, 17, 0.95); z-index: 100; 
            display: flex; flex-direction: column; align-items: center; justify-content: center;
        }}

        /* UI 控制區 - 改為絕對定位覆蓋在畫布下方 */
        #ui-container {{
            position: relative;
            width: 95vw; max-width: 600px;
            height: 180px;
            margin-top: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        /* 左側搖桿區 */
        #joystick-zone {{
            width: 150px; height: 150px;
            position: relative;
        }}

        /* 右側按鈕區 */
        #actions-zone {{
            display: flex; flex-direction: column; align-items: center; gap: 15px;
            padding-right: 20px;
        }}

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

        /* 充能燈條 */
        #charge-bar {{ display: flex; gap: 5px; margin-bottom: 5px; }}
        .charge-dot {{ width: 10px; height: 10px; border-radius: 50%; background: #333; border: 1px solid #555; }}
        .charge-dot.active {{ background: #f1fa8c; box-shadow: 0 0 5px #f1fa8c; border-color: #fff; }}

    </style>
</head>
<body>

    <div id="login-overlay">
        <h1 style="color: #50fa7b;">🦠 CELL WARS 2.0</h1>
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
            <div id="charge-bar">
                <div class="charge-dot" id="c1"></div>
                <div class="charge-dot" id="c2"></div>
                <div class="charge-dot" id="c3"></div>
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
        
        // 圖片載入
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

        // --- 搖桿設定 (Nipple.js) ---
        const manager = nipplejs.create({{
            zone: document.getElementById('joystick-zone'),
            mode: 'static',
            position: {{left: '50%', top: '50%'}},
            color: 'white',
            size: 100
        }});

        // 搖桿移動事件
        manager.on('move', (evt, data) => {{
            if(data.vector) {{
                // 發送向量 (x, y) 範圍 -1 ~ 1
                socket.emit('move', {{ dx: data.vector.x, dy: -data.vector.y }});
            }}
        }});
        manager.on('end', () => {{
            socket.emit('move', {{ dx: 0, dy: 0 }}); // 停止移動
        }});

        // --- 登入與 Socket ---
        socket.on('connect', () => {{ myId = socket.id; }});
        
        document.getElementById('start-btn').onclick = () => {{
            const name = document.getElementById('name-input').value.trim() || "Hero";
            socket.emit('join_game', {{ name: name }});
            document.getElementById('login-overlay').style.display = 'none';
        }};

        socket.on('state_update', (data) => {{
            gameState = data;
            requestAnimationFrame(draw);
            updateUI();
        }});

        function updateUI() {{
            // 更新排行榜
            const sorted = Object.values(gameState.players).sort((a,b)=>b.score-a.score).slice(0,3);
            const lbHtml = sorted.map((p, i) => `<span class="score-pill">${{i==0?'👑':''}}${{p.name}}:${{p.score}}</span>`).join('');
            document.getElementById('lb-content').innerHTML = lbHtml;

            // 更新技能按鈕狀態
            if (myId && gameState.players[myId]) {{
                const me = gameState.players[myId];
                // 更新燈號
                for(let i=1; i<=3; i++) {{
                    document.getElementById('c'+i).classList.toggle('active', me.charge >= i);
                }}
                // 更新按鈕外觀 (有能量且不在冷卻中)
                // 這裡簡單判定: 有能量就亮起 (冷卻由後端擋)
                const btn = document.getElementById('skill-btn');
                if (me.charge >= 1) btn.classList.remove('disabled');
                else btn.classList.add('disabled');
            }}
        }}

        function draw() {{
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            // 1. 畫技能分身 (半透明)
            ctx.globalAlpha = 0.6;
            if (gameState.skill_objects) {{
                gameState.skill_objects.forEach(obj => {{
                    // 畫一個發光的球
                    ctx.beginPath();
                    ctx.arc(obj.x, obj.y, 15, 0, Math.PI*2);
                    ctx.fillStyle = "#8be9fd";
                    ctx.fill();
                    ctx.strokeStyle = "white";
                    ctx.stroke();
                }});
            }}
            ctx.globalAlpha = 1.0;

            // 2. 畫敵人
            for (let id in gameState.enemies) {{
                let e = gameState.enemies[id];
                let isBoss = (e.type === 3);
                let img = skins.viruses[(e.type || 1) - 1];
                
                if(img && img.complete && !img.isBroken && img.naturalWidth!==0) {{
                    ctx.drawImage(img, e.x, e.y, e.size, e.size);
                }} else {{
                    ctx.fillStyle = isBoss?"purple":"red"; ctx.fillRect(e.x, e.y, e.size, e.size);
                }}
                
                // 敵人血條 (頭頂)
                ctx.fillStyle = "#555"; ctx.fillRect(e.x, e.y-8, e.size, 4);
                ctx.fillStyle = "#ff5555"; ctx.fillRect(e.x, e.y-8, e.size * (e.hp/e.max_hp), 4);
            }}

            // 3. 畫玩家
            for (let id in gameState.players) {{
                let p = gameState.players[id];
                let img = skins.cells[(p.skin || 1) - 1];
                
                if(img && img.complete && !img.isBroken && img.naturalWidth!==0) {{
                    ctx.drawImage(img, p.x, p.y, 30, 30);
                }} else {{
                    ctx.fillStyle = p.stats.color; ctx.fillRect(p.x, p.y, 30, 30);
                }}
                
                // 名字
                ctx.fillStyle = (id === myId) ? "#f1fa8c" : "white";
                ctx.font = "12px Arial"; ctx.textAlign = "center";
                ctx.fillText(p.name, p.x+15, p.y-15);

                // --- 修正 6: 玩家血條與身寬一樣 (30px) ---
                ctx.fillStyle = "#444"; ctx.fillRect(p.x, p.y-10, 30, 4);
                ctx.fillStyle = "#50fa7b"; ctx.fillRect(p.x, p.y-10, 30 * (p.hp / p.max_hp), 4);
            }}

            // 4. 畫子彈
            ctx.fillStyle = '#8be9fd';
            gameState.bullets.forEach(b => {{
                ctx.beginPath(); ctx.arc(b.x, b.y, 4, 0, Math.PI*2); ctx.fill();
            }});
        }}

        // --- 綁定按鈕 ---
        const fireBtn = document.getElementById('fire-btn');
        const skillBtn = document.getElementById('skill-btn');
        
        // 為了支援連發，使用 interval
        let fireInterval;
        const startFire = (e) => {{ 
            e.preventDefault(); 
            socket.emit('shoot');
            fireInterval = setInterval(()=>socket.emit('shoot'), 250); 
        }};
        const stopFire = () => clearInterval(fireInterval);

        fireBtn.addEventListener('touchstart', startFire);
        fireBtn.addEventListener('touchend', stopFire);
        fireBtn.addEventListener('mousedown', startFire);
        fireBtn.addEventListener('mouseup', stopFire);

        // 技能按鈕
        const castSkill = (e) => {{ e.preventDefault(); socket.emit('use_skill'); }};
        skillBtn.addEventListener('touchstart', castSkill);
        skillBtn.addEventListener('mousedown', castSkill);

        // 鍵盤支援 (測試用)
        document.addEventListener('keydown', (e) => {{
            if (e.code === 'Space') socket.emit('shoot');
            if (e.key === 'q') socket.emit('use_skill');
        }});
    </script>
</body>
</html>
"""

components.html(html_code, height=850)
