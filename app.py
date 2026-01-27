# app.py 完整程式碼優化版
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Cell Wars: Immune Defense", layout="wide")

# 修改為你的資訊
GITHUB_USER = "你的GitHub帳號"
GITHUB_REPO = "你的專案名稱"
SERVER_URL = "https://你的後端名稱.onrender.com"
ASSETS_BASE = f"https://raw.githubusercontent.com/{{GITHUB_USER}}/{{GITHUB_REPO}}/main/assets/"

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
    <style>
        body {{ 
            background-color: #0d0211; color: #fff; margin: 0; 
            font-family: 'Courier New', monospace; overflow: hidden; 
            display: flex; flex-direction: column; align-items: center;
        }}
        
        /* 1. 橫向記分板 (移至最上方，不遮擋畫布) */
        #top-bar {{
            width: 100%; background: #1a0620; padding: 5px 0;
            display: flex; justify-content: center; gap: 15px;
            border-bottom: 1px solid #bd93f9; font-size: 14px;
        }}
        .score-pill {{
            background: rgba(189, 147, 249, 0.2); padding: 2px 8px; border-radius: 10px;
        }}

        /* 2. 登入介面 */
        #login-overlay {{
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: #0d0211; z-index: 100; display: flex; flex-direction: column; align-items: center; justify-content: center;
        }}

        /* 3. 遊戲與畫布 */
        canvas {{ 
            background-color: #000; border: 2px solid #444; 
            width: 95vw; max-width: 600px; image-rendering: pixelated;
        }}

        /* 4. 手機控制鈕 */
        #ui-controls {{ width: 100%; display: flex; justify-content: space-around; padding: 10px; }}
        .btn {{ width: 55px; height: 55px; background: #222; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 20px; }}
        .btn-fire {{ background: #ff5555; width: 80px; height: 80px; border-radius: 50%; font-weight: bold; }}
    </style>
</head>
<body>

    <div id="login-overlay">
        <h1 style="color: #50fa7b;">🦠 CELL WARS</h1>
        <input type="text" id="name-input" placeholder="Name (EN)" style="padding:10px; margin:10px;">
        <button id="start-btn" style="padding:10px 20px; background:#50fa7b; border:none; font-weight:bold;">START</button>
    </div>

    <div id="top-bar">
        <span>Top Cells:</span>
        <div id="lb-content" style="display:flex; gap:10px;"></div>
    </div>

    <canvas id="gameCanvas" width="600" height="500"></canvas>

    <div id="ui-controls">
        <div style="display: grid; grid-template-columns: repeat(3, 55px); gap: 5px;">
            <div class="btn" style="grid-column: 2" id="up">▲</div>
            <div class="btn" style="grid-column: 1; grid-row: 2" id="left">◀</div>
            <div class="btn" style="grid-column: 3; grid-row: 2" id="right">▶</div>
            <div class="btn" style="grid-column: 2; grid-row: 3" id="down">▼</div>
        </div>
        <div class="btn btn-fire" id="fire">FIRE</div>
    </div>

    <script>
        const socket = io("{SERVER_URL}");
        const canvas = document.getElementById('gameCanvas');
        const ctx = canvas.getContext('2d');
        const assetsBase = "{ASSETS_BASE}";
        
        const skins = {{ cells: [], viruses: [] }};
        for(let i=1; i<=3; i++) {{
            let c = new Image(); c.src = assetsBase + "cell_" + i + ".png"; skins.cells.push(c);
            let v = new Image(); v.src = assetsBase + "virus_" + i + ".png"; skins.viruses.push(v);
        }}

        let gameState = {{ players: {{}}, enemies: {{}}, bullets: [] }};

        document.getElementById('start-btn').onclick = () => {{
            const name = document.getElementById('name-input').value.trim();
            if(!name) return;
            socket.emit('join_game', {{ name: name }});
            document.getElementById('login-overlay').style.display = 'none';
        }};

        socket.on('state_update', (data) => {{
            gameState = data;
            draw();
            // 更新上方橫向記分板
            const sorted = Object.values(gameState.players).sort((a,b)=>b.score-a.score).slice(0,3);
            document.getElementById('lb-content').innerHTML = sorted.map(p=>`<span class="score-pill">${{p.name}}: ${{p.score}}</span>`).join('');
        }});

        function draw() {{
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            // 畫敵人
            for (let id in gameState.enemies) {{
                let e = gameState.enemies[id];
                let isBoss = (e.type === 3);
                let size = isBoss ? 50 : 30;
                let img = skins.viruses[(e.type || 1) - 1];
                
                if(img.complete) ctx.drawImage(img, e.x, e.y, size, size);

                // --- 修正：魔王血條邏輯 ---
                if(isBoss) {{
                    ctx.fillStyle = "#444"; ctx.fillRect(e.x, e.y - 12, size, 6);
                    ctx.fillStyle = "#ff5555"; ctx.fillRect(e.x, e.y - 12, size * (e.hp/10), 6);
                    ctx.strokeStyle = "white"; ctx.strokeRect(e.x, e.y - 12, size, 6);
                }}
            }}

            // 畫玩家
            for (let id in gameState.players) {{
                let p = gameState.players[id];
                let img = skins.cells[(p.skin || 1) - 1];
                if(img.complete) ctx.drawImage(img, p.x, p.y, 30, 30);
                
                ctx.fillStyle = "white"; ctx.font = "10px Arial"; ctx.textAlign="center";
                ctx.fillText(p.name, p.x+15, p.y-15);
                
                // 玩家血條
                ctx.fillStyle="#50fa7b"; ctx.fillRect(p.x, p.y-10, 30*(p.hp/3), 3);

                if (id === socket.id) {{
                    ctx.strokeStyle = '#f1fa8c'; ctx.strokeRect(p.x-2, p.y-2, 34, 34);
                }}
            }}

            // 畫子彈
            ctx.fillStyle = '#8be9fd';
            gameState.bullets.forEach(b => {{
                ctx.beginPath(); ctx.arc(b.x, b.y, 4, 0, Math.PI*2); ctx.fill();
            }});
        }}

        // 控制邏輯 (略，同前版本)
        const move = (dir) => {{
            let dx=0, dy=0;
            if(dir==='up') dy=-15; if(dir==='down') dy=15;
            if(dir==='left') dx=-15; if(dir==='right') dx=15;
            socket.emit('move', {{dx, dy, dir}});
        }};
        const bind = (id, dir) => {{ document.getElementById(id).ontouchstart = (e)=>{{e.preventDefault(); move(dir);}}; }};
        bind('up','up'); bind('down','down'); bind('left','left'); bind('right','right');
        document.getElementById('fire').ontouchstart = (e)=>{{e.preventDefault(); socket.emit('shoot');}};
    </script>
</body>
</html>
"""

components.html(html_code, height=850)
