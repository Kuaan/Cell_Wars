import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Cell Wars: Immune Defense", layout="wide")

# --- 設定區 ---
GITHUB_USER = "Kuaan"
GITHUB_REPO = "Cell_Wars"
SERVER_URL = "https://cell-wars.onrender.com"  # 你的 Render 網址
# 圖片路徑 (確保你的 Repo 是 Public 的，否則讀不到)
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
    <style>
        body {{ 
            background-color: #0d0211; color: #fff; margin: 0; 
            font-family: 'Courier New', monospace; overflow: hidden; 
            display: flex; flex-direction: column; align-items: center;
        }}
        #top-bar {{
            width: 100%; background: #1a0620; padding: 5px 0;
            display: flex; justify-content: center; gap: 15px;
            border-bottom: 1px solid #bd93f9; font-size: 14px;
        }}
        .score-pill {{ background: rgba(189, 147, 249, 0.2); padding: 2px 8px; border-radius: 10px; }}
        
        #login-overlay {{
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(13, 2, 17, 0.95); z-index: 100; 
            display: flex; flex-direction: column; align-items: center; justify-content: center;
        }}
        
        canvas {{ 
            background-color: #000; border: 2px solid #444; 
            width: 95vw; max-width: 600px; height: auto; aspect-ratio: 6/5;
            image-rendering: pixelated; margin-top: 10px;
        }}
        
        #ui-controls {{ width: 100%; max-width: 400px; display: flex; justify-content: space-around; padding: 10px; }}
        .btn {{ width: 55px; height: 55px; background: #333; border: 1px solid #555; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 20px; cursor: pointer; user-select: none; }}
        .btn:active {{ background: #666; }}
        .btn-fire {{ background: #ff5555; width: 70px; height: 70px; border-radius: 50%; font-weight: bold; border: 2px solid #ff9999; }}
        .btn-fire:active {{ background: #ff0000; }}
        
        #debug-info {{ font-size: 10px; color: #666; margin-top: 5px; }}
    </style>
</head>
<body>

    <div id="login-overlay">
        <h1 style="color: #50fa7b;">🦠 CELL WARS</h1>
        <input type="text" id="name-input" placeholder="Enter Name" style="padding:10px; font-size:16px; text-align:center;">
        <br>
        <button id="start-btn" style="padding:10px 30px; background:#50fa7b; border:none; border-radius:5px; font-weight:bold; cursor:pointer;">START GAME</button>
        <p style="font-size:12px; color:#aaa;">Controls: WASD / Arrows / Buttons</p>
    </div>

    <div id="top-bar">
        <span>Leaderboard:</span>
        <div id="lb-content" style="display:flex; gap:10px;">Waiting...</div>
    </div>

    <canvas id="gameCanvas" width="600" height="500"></canvas>
    <div id="debug-info">Connecting...</div>

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
        const socket = io("{SERVER_URL}", {{
            reconnectionAttempts: 5,
            timeout: 10000
        }});
        
        const canvas = document.getElementById('gameCanvas');
        const ctx = canvas.getContext('2d');
        const debugDiv = document.getElementById('debug-info');
        const assetsBase = "{ASSETS_BASE}";
        
        // 載入圖片 (含錯誤處理)
        const skins = {{ cells: [], viruses: [] }};
        function loadImg(path) {{
            let img = new Image();
            img.src = path;
            img.onerror = () => {{ console.warn("Image failed:", path); img.isBroken = true; }};
            return img;
        }}

        for(let i=1; i<=3; i++) {{
            skins.cells.push(loadImg(assetsBase + "cell_" + i + ".png"));
            skins.viruses.push(loadImg(assetsBase + "virus_" + i + ".png"));
        }}

        let gameState = {{ players: {{}}, enemies: {{}}, bullets: [] }};
        let myId = null;

        // --- Socket 連線監聽 ---
        socket.on('connect', () => {{
            debugDiv.innerHTML = "Connected! ID: " + socket.id;
            myId = socket.id;
        }});
        
        socket.on('connect_error', (err) => {{
            debugDiv.innerHTML = "Connection Error: " + err.message;
            debugDiv.style.color = "red";
        }});

        // --- 登入邏輯 ---
        document.getElementById('start-btn').onclick = () => {{
            const name = document.getElementById('name-input').value.trim() || "Cell";
            socket.emit('join_game', {{ name: name }});
            document.getElementById('login-overlay').style.display = 'none';
        }};

        socket.on('state_update', (data) => {{
            gameState = data;
            requestAnimationFrame(draw); // 使用 requestAnimationFrame 讓動畫更順暢
            
            // 更新計分板
            const sorted = Object.values(gameState.players).sort((a,b)=>b.score-a.score).slice(0,3);
            const lbHtml = sorted.map(p=>`<span class="score-pill">${{p.name}}: ${{p.score}}</span>`).join('');
            document.getElementById('lb-content').innerHTML = lbHtml || "No players";
        }});

        function draw() {{
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            // 畫敵人
            for (let id in gameState.enemies) {{
                let e = gameState.enemies[id];
                let isBoss = (e.type === 3);
                let size = isBoss ? 50 : 30;
                let img = skins.viruses[(e.type || 1) - 1];
                
                // 圖片載入成功則畫圖，失敗或未載入則畫色塊
                if(img && img.complete && !img.isBroken && img.naturalWidth !== 0) {{
                    ctx.drawImage(img, e.x, e.y, size, size);
                }} else {{
                    ctx.fillStyle = isBoss ? "purple" : "red";
                    ctx.fillRect(e.x, e.y, size, size);
                }}

                // 血條
                ctx.fillStyle = "#444"; ctx.fillRect(e.x, e.y - 8, size, 4);
                ctx.fillStyle = "#ff5555"; ctx.fillRect(e.x, e.y - 8, size * (e.hp/(isBoss?10:1)), 4);
            }}

            // 畫玩家
            for (let id in gameState.players) {{
                let p = gameState.players[id];
                let img = skins.cells[(p.skin || 1) - 1];
                
                if(img && img.complete && !img.isBroken && img.naturalWidth !== 0) {{
                    ctx.drawImage(img, p.x, p.y, 30, 30);
                }} else {{
                    ctx.fillStyle = p.color || "#50fa7b"; // 備用顏色
                    ctx.fillRect(p.x, p.y, 30, 30);
                }}
                
                // 名字
                ctx.fillStyle = "white"; ctx.font = "12px monospace"; ctx.textAlign="center";
                ctx.fillText(p.name, p.x+15, p.y-15);
                
                // 血條
                ctx.fillStyle="#50fa7b"; ctx.fillRect(p.x, p.y-10, 30*(p.hp/3), 3);

                if (id === myId) {{
                    ctx.strokeStyle = '#f1fa8c'; ctx.lineWidth = 2;
                    ctx.strokeRect(p.x-2, p.y-2, 34, 34);
                }}
            }}

            // 畫子彈
            ctx.fillStyle = '#8be9fd';
            gameState.bullets.forEach(b => {{
                ctx.beginPath(); ctx.arc(b.x, b.y, 4, 0, Math.PI*2); ctx.fill();
            }});
        }}

        // --- 完整控制邏輯 (支援 PC 與 手機) ---
        const move = (dir) => {{
            let dx=0, dy=0;
            if(dir==='up') dy=-15; if(dir==='down') dy=15;
            if(dir==='left') dx=-15; if(dir==='right') dx=15;
            socket.emit('move', {{dx, dy, dir}});
        }};

        // 綁定按鈕 (支援滑鼠點擊與觸控)
        const bind = (id, dir) => {{ 
            const el = document.getElementById(id);
            const handler = (e) => {{ e.preventDefault(); move(dir); }};
            el.addEventListener('touchstart', handler);
            el.addEventListener('mousedown', handler);
        }};
        bind('up','up'); bind('down','down'); bind('left','left'); bind('right','right');
        
        const fireBtn = document.getElementById('fire');
        const fireHandler = (e) => {{ e.preventDefault(); socket.emit('shoot'); }};
        fireBtn.addEventListener('touchstart', fireHandler);
        fireBtn.addEventListener('mousedown', fireHandler);

        // 綁定鍵盤
        document.addEventListener('keydown', (e) => {{
            if (e.key === 'ArrowUp' || e.key === 'w') move('up');
            if (e.key === 'ArrowDown' || e.key === 's') move('down');
            if (e.key === 'ArrowLeft' || e.key === 'a') move('left');
            if (e.key === 'ArrowRight' || e.key === 'd') move('right');
            if (e.code === 'Space') socket.emit('shoot');
        }});
    </script>
</body>
</html>
"""

components.html(html_code, height=850)
