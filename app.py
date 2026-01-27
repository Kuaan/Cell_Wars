# app.py (優化版)
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Cell Wars: Immune Defense", layout="wide")

# 背景與介面樣式優化
st.markdown("""
    <style>
    .stApp { background-color: #1a0620; }
    [data-testid="stHeader"] { display: none; }
    </style>
""", unsafe_allow_html=True)

# --- 重要：請填入你的 Render 伺服器網址 ---
SERVER_URL = "https://cell-wars.onrender.com" 
# ---------------------------------------

html_code = f"""
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <script src="https://cdn.socket.io/4.6.0/socket.io.min.js"></script>
    <style>
        body {{ 
            background-color: #1a0620; color: #fff; margin: 0; 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            overflow: hidden; display: flex; flex-direction: column; align-items: center;
        }}
        
        /* 登入畫面 */
        #login-overlay {{
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(26, 6, 32, 0.95); z-index: 100;
            display: flex; flex-direction: column; align-items: center; justify-content: center;
        }}
        #name-input {{
            padding: 12px; font-size: 18px; border-radius: 5px; border: 2px solid #bd93f9;
            background: #282a36; color: white; text-align: center; margin-bottom: 10px;
        }}
        #start-btn {{
            padding: 10px 30px; font-size: 20px; background: #50fa7b; border: none;
            border-radius: 5px; cursor: pointer; font-weight: bold;
        }}

        /* 遊戲畫面 */
        #game-container {{ display: none; position: relative; width: 95vw; max-width: 600px; }}
        canvas {{ 
            background-color: #0f0213; border: 3px solid #44475a; 
            border-radius: 8px; width: 100%; image-rendering: pixelated;
        }}

        /* 記分板 */
        #leaderboard {{
            position: absolute; top: 10px; right: 10px; background: rgba(0,0,0,0.6);
            padding: 10px; border-radius: 5px; font-size: 12px; min-width: 100px;
            pointer-events: none; border: 1px solid #6272a4;
        }}
        .lb-title {{ color: #f1fa8c; font-weight: bold; margin-bottom: 5px; border-bottom: 1px solid #444; }}

        /* 控制器與狀態 */
        #ui-controls {{ width: 100%; display: flex; justify-content: space-around; padding: 10px; }}
        .btn {{ width: 60px; height: 60px; background: #44475a; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 24px; user-select: none; }}
        .btn:active {{ background: #6272a4; }}
        .btn-fire {{ background: #ff5555; width: 80px; height: 80px; border-radius: 50%; font-weight: bold; }}
    </style>
</head>
<body>

    <div id="login-overlay">
        <h1 style="color: #50fa7b;">🦠 CELL WARS</h1>
        <p>Protect the body. Destroy the viruses.</p>
        <input type="text" id="name-input" placeholder="Enter English Name" maxlength="10">
        <button id="start-btn">JOIN GAME</button>
    </div>

    <div id="game-container">
        <div id="leaderboard"><div class="lb-title">Top Cells</div><div id="lb-content"></div></div>
        <canvas id="gameCanvas" width="600" height="500"></canvas>
        <div id="ui-controls">
            <div style="display: grid; grid-template-columns: repeat(3, 60px); gap: 5px;">
                <div class="btn" style="grid-column: 2" id="up">▲</div>
                <div class="btn" style="grid-column: 1" id="left">◀</div>
                <div class="btn" style="grid-column: 3" id="right">▶</div>
                <div class="btn" style="grid-column: 2" id="down">▼</div>
            </div>
            <div class="btn btn-fire" id="fire">FIRE</div>
        </div>
    </div>

    <script>
        const socket = io("{SERVER_URL}");
        const canvas = document.getElementById('gameCanvas');
        const ctx = canvas.getContext('2d');
        const loginOverlay = document.getElementById('login-overlay');
        const gameContainer = document.getElementById('game-container');
        const lbContent = document.getElementById('lb-content');
        
        let gameState = {{ players: {{}}, enemies: {{}}, bullets: [] }};

        // --- 像素角色圖片 ---
        const cellImg = new Image();
        cellImg.src = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAB4AAAAeCAYAAAA7MK6iAAAAAXNSR0IArs4c6QAAAMZJREFUSEvtlssNgzAMRKnTSh2WQapMwSAdpB2kY5QO0mFaRkGqjJLaD3WCIj+2UaRIkSIF+XwsX5yF8a8P7w/r0b559k6B3IB7cO/BvQf/z4G7e7e6h9c2v04tF/Cqqr5P+9U5R76eI+ec47332FpblmVJv2tG7sDjnH9i995jGAbW/e4IuQHP84yqqrDGYBiG+3jXjNyA11qRZZn2rEbbthgE4f5O5+H6t2x+g94R+q/grbUoigLDMJAX3916F27A27bFkiTwPA95nr+qP2rWwV9eFwAAAABJRU5ErkJggg==";

        const virusImg = new Image();
        virusImg.src = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAB4AAAAeCAYAAAA7MK6iAAAAAXNSR0IArs4c6QAAAL5JREFUSEvlldENwyAMRCkdJcOUYRKGyRhlmIxShskwZZQ6/aHaqhIgX5UqqUIi8fEZf7gU/rR6D4vO8e3ZPgXqBtyDe4/m+zlwL+9e9/DahutUvYBXjTEdU9+dc+Tri/i+b8g5h3MOaZoQx7F8d8zYgddaf2Kvqqqq0PZ7ImYDnmUZdV2jjUEf8a4ZuwFvtyLLMvR5NUqSBGEY/n/D6bj+PZrfod+F7q1F0zSw1iLPo7v1duEGfLsVjDEIggB5nre6P2rbB/9+S6q0AAAAAElFTkSuQmCC";

        // --- 加入遊戲邏輯 ---
        document.getElementById('start-btn').onclick = () => {{
            const name = document.getElementById('name-input').value.replace(/[^a-zA-Z0-9]/g, "");
            if (name.length < 2) {{ alert("Please enter at least 2 English characters."); return; }}
            socket.emit('join_game', {{ name: name }});
            loginOverlay.style.display = 'none';
            gameContainer.style.display = 'block';
        }};

        socket.on('state_update', (data) => {{
            gameState = data;
            requestAnimationFrame(draw);
            updateLeaderboard();
        }});

        function updateLeaderboard() {{
            let list = Object.values(gameState.players)
                .sort((a, b) => b.score - a.score)
                .slice(0, 5)
                .map(p => `<div>${{p.name}}: ${{p.score}}</div>`)
                .join('');
            lbContent.innerHTML = list;
        }}

        function draw() {{
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            // 1. 畫敵人 (病毒)
            for (let id in gameState.enemies) {{
                let e = gameState.enemies[id];
                ctx.drawImage(virusImg, e.x, e.y, 30, 30);
            }}

            // 2. 畫子彈
            ctx.fillStyle = '#8be9fd';
            gameState.bullets.forEach(b => {{
                ctx.beginPath(); ctx.arc(b.x, b.y, 4, 0, Math.PI*2); ctx.fill();
            }});

            // 3. 畫玩家 (細胞)
            for (let id in gameState.players) {{
                let p = gameState.players[id];
                
                // 畫名字
                ctx.fillStyle = "white";
                ctx.font = "bold 12px Arial";
                ctx.textAlign = "center";
                ctx.fillText(p.name, p.x + 15, p.y - 12);

                // 畫血條
                ctx.fillStyle = '#ff5555'; ctx.fillRect(p.x, p.y - 8, 30, 4);
                ctx.fillStyle = '#50fa7b'; ctx.fillRect(p.x, p.y - 8, 30 * (p.hp / 3), 4);

                // 畫細胞圖
                ctx.drawImage(cellImg, p.x, p.y, 30, 30);

                if (id === socket.id) {{
                    ctx.strokeStyle = '#f1fa8c'; ctx.lineWidth = 2;
                    ctx.strokeRect(p.x-2, p.y-2, 34, 34);
                }}
            }}
        }}

        // 控制邏輯 (發送移動與射擊)
        function sendMove(dir) {{
            let dx=0, dy=0;
            if (dir==='up') dy=-12; if (dir==='down') dy=12;
            if (dir==='left') dx=-12; if (dir==='right') dx=12;
            socket.emit('move', {{dx, dy, dir}});
        }}

        const setupBtn = (id, dir) => {{
            const el = document.getElementById(id);
            el.onmousedown = el.ontouchstart = (e) => {{ e.preventDefault(); sendMove(dir); }};
        }};
        setupBtn('up','up'); setupBtn('down','down'); setupBtn('left','left'); setupBtn('right','right');
        document.getElementById('fire').onmousedown = (e) => socket.emit('shoot');
        
        // 鍵盤支援
        document.onkeydown = (e) => {{
            if (e.key === 'ArrowUp') sendMove('up');
            if (e.key === 'ArrowDown') sendMove('down');
            if (e.key === 'ArrowLeft') sendMove('left');
            if (e.key === 'ArrowRight') sendMove('right');
            if (e.code === 'Space') socket.emit('shoot');
        }};
    </script>
</body>
</html>
"""

components.html(html_code, height=800)
