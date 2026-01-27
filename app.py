import streamlit as st
import streamlit.components.v1 as components

# 頁面基本設定
st.set_page_config(page_title="Cell Wars: Immune Defense", layout="wide")

# --- 1. 使用者自定義區塊 (請務必修改這裡) ---
# 修改為你的 GitHub 帳號名稱與專案名稱
GITHUB_USER = "Kuaan"
GITHUB_REPO = "Cell_wars"
# 修改為你的 Render 後端網址
SERVER_URL = "https://cell-wars.onrender.com"
# ---------------------------------------

# 隱藏 Streamlit 多餘元件並設定背景顏色
st.markdown("""
    <style>
    [data-testid="stHeader"] {display: none;}
    .stApp {background-color: #1a0620;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# 組合 GitHub 圖片路徑
ASSETS_BASE = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/assets/"

# HTML/JavaScript 核心邏輯
html_code = f"""
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <script src="https://cdn.socket.io/4.6.0/socket.io.min.js"></script>
    <style>
        body {{ 
            background-color: #1a0620; color: #fff; margin: 0; 
            font-family: 'Courier New', monospace; overflow: hidden; 
            display: flex; flex-direction: column; align-items: center;
        }}
        
        /* 登入介面 */
        #login-overlay {{
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: radial-gradient(circle, #2b0b3d 0%, #0d0211 100%);
            z-index: 100; display: flex; flex-direction: column; align-items: center; justify-content: center;
        }}
        .login-box {{
            background: rgba(255, 255, 255, 0.05); padding: 30px; border-radius: 15px;
            border: 2px solid #bd93f9; text-align: center; backdrop-filter: blur(5px);
        }}
        input {{
            padding: 12px; font-size: 18px; border-radius: 5px; border: none;
            background: #282a36; color: white; width: 200px; margin: 15px 0;
        }}
        button {{
            padding: 10px 25px; font-size: 18px; background: #50fa7b; border: none;
            border-radius: 5px; cursor: pointer; font-weight: bold; color: #1a0620;
        }}

        /* 遊戲區域 */
        #game-wrapper {{ display: none; position: relative; padding: 10px; }}
        canvas {{ 
            background-color: #0c0111; border: 3px solid #44475a; 
            border-radius: 10px; width: 95vw; max-width: 600px;
            image-rendering: pixelated; box-shadow: 0 0 20px rgba(189, 147, 249, 0.3);
        }}

        /* 記分板 */
        #leaderboard {{
            position: absolute; top: 20px; right: 20px; 
            background: rgba(0, 0, 0, 0.7); padding: 10px; border-radius: 5px;
            border: 1px solid #6272a4; font-size: 14px; min-width: 120px; pointer-events: none;
        }}
        .lb-item {{ display: flex; justify-content: space-between; margin: 3px 0; }}
        .lb-title {{ color: #f1fa8c; font-weight: bold; border-bottom: 1px solid #444; margin-bottom: 5px; }}

        /* 控制按鈕 */
        #ui-controls {{ width: 100%; display: flex; justify-content: space-around; padding: 15px; }}
        .btn {{ width: 60px; height: 60px; background: #3c1e45; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 24px; user-select: none; border: 1px solid #6272a4; }}
        .btn:active {{ background: #bd93f9; color: white; }}
        .btn-fire {{ background: #ff5555; width: 85px; height: 85px; border-radius: 50%; font-weight: bold; color: white; }}
    </style>
</head>
<body>

    <div id="login-overlay">
        <div class="login-box">
            <h1 style="color: #50fa7b; margin: 0;">🦠 CELL WARS</h1>
            <p style="color: #8be9fd;">Immune System Protocol</p>
            <input type="text" id="name-input" placeholder="Enter Name (EN)" maxlength="10">
            <br>
            <button id="start-btn">ENGAGE</button>
        </div>
    </div>

    <div id="game-wrapper">
        <div id="leaderboard">
            <div class="lb-title">Leaderboard</div>
            <div id="lb-content"></div>
        </div>
        <canvas id="gameCanvas" width="600" height="500"></canvas>
        <div id="ui-controls">
            <div style="display: grid; grid-template-columns: repeat(3, 65px); gap: 8px;">
                <div class="btn" style="grid-column: 2" id="up">▲</div>
                <div class="btn" style="grid-column: 1; grid-row: 2" id="left">◀</div>
                <div class="btn" style="grid-column: 3; grid-row: 2" id="right">▶</div>
                <div class="btn" style="grid-column: 2; grid-row: 3" id="down">▼</div>
            </div>
            <div class="btn btn-fire" id="fire">FIRE</div>
        </div>
    </div>

    <script>
        const socket = io("{SERVER_URL}");
        const canvas = document.getElementById('gameCanvas');
        const ctx = canvas.getContext('2d');
        const assetsBase = "{ASSETS_BASE}";
        
        // --- 1. 圖片預加載池 ---
        const skinImages = {{
            cells: [],
            viruses: []
        }};

        for(let i=1; i<=3; i++) {{
            let c = new Image(); c.src = assetsBase + "cell_" + i + ".png";
            skinImages.cells.push(c);
            let v = new Image(); v.src = assetsBase + "virus_" + i + ".png";
            skinImages.viruses.push(v);
        }}

        let gameState = {{ players: {{}}, enemies: {{}}, bullets: [] }};

        // --- 2. 登入邏輯 ---
        document.getElementById('start-btn').onclick = () => {{
            const name = document.getElementById('name-input').value.trim();
            if(!name) {{ alert("Please enter a name!"); return; }}
            socket.emit('join_game', {{ name: name }});
            document.getElementById('login-overlay').style.display = 'none';
            document.getElementById('game-wrapper').style.display = 'block';
        }};

        // --- 3. 遊戲核心與繪圖 ---
        socket.on('state_update', (data) => {{
            gameState = data;
            requestAnimationFrame(draw);
            updateLeaderboard();
        }});

        function updateLeaderboard() {{
            const players = Object.values(gameState.players).sort((a,b) => b.score - a.score).slice(0, 5);
            let html = "";
            players.forEach(p => {{
                html += `<div class="lb-item"><span>${{p.name}}</span><span>${{p.score}}</span></div>`;
            }});
            document.getElementById('lb-content').innerHTML = html;
        }}

        function draw() {{
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            // 畫敵人 (病毒)
            for (let id in gameState.enemies) {{
                let e = gameState.enemies[id];
                // 使用後端傳來的 type (1, 2, 3)，陣列索引要 -1
                let img = skinImages.viruses[(e.type || 1) - 1];
                if(img.complete) ctx.drawImage(img, e.x, e.y, 30, 30);
            }}

            // 畫子彈 (藍色發光球)
            ctx.fillStyle = '#8be9fd';
            ctx.shadowBlur = 8; ctx.shadowColor = '#8be9fd';
            gameState.bullets.forEach(b => {{
                ctx.beginPath(); ctx.arc(b.x, b.y, 4, 0, Math.PI*2); ctx.fill();
            }});
            ctx.shadowBlur = 0;

            // 畫玩家 (細胞)
            for (let id in gameState.players) {{
                let p = gameState.players[id];
                
                // 畫名字與血條
                ctx.fillStyle = "white";
                ctx.font = "bold 10px Arial";
                ctx.textAlign = "center";
                ctx.fillText(p.name, p.x + 15, p.y - 15);
                
                ctx.fillStyle = "#444"; ctx.fillRect(p.x, p.y - 10, 30, 4);
                ctx.fillStyle = "#50fa7b"; ctx.fillRect(p.x, p.y - 10, 30 * (p.hp/3), 4);

                // 畫隨機分配的細胞 Skin
                let img = skinImages.cells[(p.skin || 1) - 1];
                if(img.complete) ctx.drawImage(img, p.x, p.y, 30, 30);

                if (id === socket.id) {{
                    ctx.strokeStyle = '#f1fa8c'; ctx.lineWidth = 2;
                    ctx.strokeRect(p.x-2, p.y-2, 34, 34);
                }}
            }}
        }}

        // --- 4. 控制輸入 ---
        const move = (dir) => {{
            let dx=0, dy=0;
            if (dir==='up') dy=-15; if (dir==='down') dy=15;
            if (dir==='left') dx=-15; if (dir==='right') dx=15;
            socket.emit('move', {{dx, dy, dir}});
        }};

        const bind = (id, dir) => {{
            const el = document.getElementById(id);
            el.onmousedown = el.ontouchstart = (e) => {{ e.preventDefault(); move(dir); }};
        }};
        bind('up','up'); bind('down','down'); bind('left','left'); bind('right','right');
        
        const fire = (e) => {{ e.preventDefault(); socket.emit('shoot'); }};
        document.getElementById('fire').onmousedown = document.getElementById('fire').ontouchstart = fire;

        document.onkeydown = (e) => {{
            if (e.key === 'ArrowUp') move('up');
            if (e.key === 'ArrowDown') move('down');
            if (e.key === 'ArrowLeft') move('left');
            if (e.key === 'ArrowRight') move('right');
            if (e.code === 'Space') socket.emit('shoot');
        }};
    </script>
</body>
</html>
"""

# 渲染組件
components.html(html_code, height=850)
