
# app.py (Cell Wars Theme)
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Cell Wars", layout="wide")

# 隱藏 Streamlit 預設選單，讓畫面更沉浸
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stApp {overflow: hidden; background-color: #200f21;} /* 深紫色背景 */
    </style>
""", unsafe_allow_html=True)

st.title("🦠 Cell Wars")
st.caption("Eliminate all viruses!")

# --- 重要：請填入你的 Render 伺服器網址 ---
SERVER_URL = "https://cell-wars.onrender.com" 
# ---------------------------------------

html_code = f"""
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <script src="https://cdn.socket.io/4.6.0/socket.io.min.js"></script>
    <style>
        body {{ 
            background-color: #200f21; color: #e0e0e0; margin: 0; 
            display: flex; flex-direction: column; align-items: center; 
            font-family: 'Courier New', monospace; /* 像素風字體感 */
            overflow: hidden; touch-action: none;
        }}
        canvas {{ 
            background-color: #0d0412; /* 更深的背景 */
            border: 3px solid #4a2a52; 
            border-radius: 10px;
            box-shadow: 0 0 15px #4a2a52;
            width: 95vw; height: auto; max-height: 55vh;
            image-rendering: pixelated; /* 關鍵：讓圖片放大時保持像素顆粒感 */
        }}
        #status {{ 
            width: 90%; text-align: center; padding: 5px; 
            font-weight: bold; color: #50fa7b;
        }}
        #ui-container {{
            width: 100%; display: flex; justify-content: space-around; align-items: center;
            padding: 15px 0; background: #200f21; height: 35vh;
        }}
        .d-pad {{
            display: grid; grid-template-columns: 60px 60px 60px; grid-template-rows: 60px 60px 60px; gap: 5px;
        }}
        .btn {{
            background: #3c1e45; border: 2px solid #6b3e7a; color: #bd93f9;
            display: flex; justify-content: center; align-items: center;
            user-select: none; border-radius: 8px; font-size: 24px;
        }}
        .btn:active {{ background: #6b3e7a; color: white; }}
        .btn-up {{ grid-column: 2; grid-row: 1; }}
        .btn-down {{ grid-column: 2; grid-row: 3; }}
        .btn-left {{ grid-column: 1; grid-row: 2; }}
        .btn-right {{ grid-column: 3; grid-row: 2; }}
        
        .fire-container {{ width: 90px; height: 90px; }}
        .btn-fire {{
            width: 100%; height: 100%; background: #ff5555; border: 3px solid #ff7777;
            border-radius: 50%; color: white;
            display: flex; justify-content: center; align-items: center; font-weight: bold;
        }}
        .btn-fire:active {{ background: #ff7777; transform: scale(0.95); }}
    </style>
</head>
<body>
    <div id="status">正在連結免疫系統...</div>
    <canvas id="gameCanvas" width="600" height="500"></canvas>

    <div id="ui-container">
        <div class="d-pad">
            <div class="btn btn-up" id="up">▲</div>
            <div class="btn btn-left" id="left">◀</div>
            <div class="btn btn-right" id="right">▶</div>
            <div class="btn btn-down" id="down">▼</div>
        </div>
        <div class="fire-container">
            <div class="btn btn-fire" id="fire">FIRE</div>
        </div>
    </div>

    <script>
        const socket = io("{SERVER_URL}");
        const canvas = document.getElementById('gameCanvas');
        const ctx = canvas.getContext('2d');
        const statusDiv = document.getElementById('status');
        
        let gameState = {{ players: {{}}, enemies: {{}}, bullets: [] }};
        const TANK_SIZE = 30; # 這裡的大小要跟圖片匹配

        // --- 1. 圖片預加載區域 ---
        const cellImg = new Image();
        # 這裡使用 Base64 範例圖片 (一個綠色像素細胞)
        # 你可以替換成你自己的圖片網址，例如: cellImg.src = "https://你的圖床/cell.png";
        cellImg.src = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAB4AAAAeCAYAAAA7MK6iAAAAAXNSR0IArs4c6QAAAMZJREFUSEvtlssNgzAMRKnTSh2WQapMwSAdpB2kY5QO0mFaRkGqjJLaD3WCIj+2UaRIkSIF+XwsX5yF8a8P7w/r0b559k6B3IB7cO/BvQf/z4G7e7e6h9c2v04tF/Cqqr5P+9U5R76eI+ec47332FpblmVJv2tG7sDjnH9i995jGAbW/e4IuQHP84yqqrDGYBiG+3jXjNyA11qRZZn2rEbbthgE4f5O5+H6t2x+g94R+q/grbUoigLDMJAX3916F27A27bFkiTwPA95nr+qP2rWwV9eFwAAAABJRU5ErkJggg==";

        const virusImg = new Image();
        # 這裡使用 Base64 範例圖片 (一個紫色像素病毒)
        virusImg.src = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAB4AAAAeCAYAAAA7MK6iAAAAAXNSR0IArs4c6QAAAL5JREFUSEvlldENwyAMRCkdJcOUYRKGyRhlmIxShskwZZQ6/aHaqhIgX5UqqUIi8fEZf7gU/rR6D4vO8e3ZPgXqBtyDe4/m+zlwL+9e9/DahutUvYBXjTEdU9+dc+Tri/i+b8g5h3MOaZoQx7F8d8zYgddaf2Kvqqqq0PZ7ImYDnmUZdV2jjUEf8a4ZuwFvtyLLMvR5NUqSBGEY/n/D6bj+PZrfod+F7q1F0zSw1iLPo7v1duEGfLsVjDEIggB5nre6P2rbB/9+S6q0AAAAAElFTkSuQmCC";

        let imagesLoaded = false;
        // 確保兩張圖都載入完成後才開始繪圖
        cellImg.onload = () => {{ if(virusImg.complete) imagesLoaded = true; }};
        virusImg.onload = () => {{ if(cellImg.complete) imagesLoaded = true; }};
        // -----------------------


        socket.on('state_update', (data) => {{
            gameState = data;
            // 只有當圖片載入完成後，才執行繪圖
            if (imagesLoaded) {{
                 requestAnimationFrame(draw);
            }}
            if (gameState.players[socket.id]) {{
                const p = gameState.players[socket.id];
                statusDiv.innerHTML = `Health: ${{p.hp}} | Score: ${{p.score}}`;
            }}
        }});

        // --- 2. 繪圖函數修改 ---
        function draw() {{
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            // 畫玩家 (細胞)
            for (let id in gameState.players) {{
                let p = gameState.players[id];
                
                // 畫血條 (稍微改細一點，比較不擋圖片)
                ctx.fillStyle = '#ff5555'; ctx.fillRect(p.x, p.y - 8, 30, 4);
                ctx.fillStyle = '#50fa7b'; ctx.fillRect(p.x, p.y - 8, 30 * (p.hp / 3), 4);

                // --> 關鍵修改：使用 drawImage 畫出細胞圖片 <--
                // 參數：圖片物件, X座標, Y座標, 寬度, 高度
                ctx.drawImage(cellImg, p.x, p.y, TANK_SIZE, TANK_SIZE);
                
                // 標記自己 (用一個發光的圓圈代替方框)
                if (id === socket.id) {{
                    ctx.strokeStyle = '#f1fa8c'; // 黃色光圈
                    ctx.lineWidth = 3;
                    ctx.beginPath();
                    // 在細胞中心畫一個圓
                    ctx.arc(p.x + TANK_SIZE/2, p.y + TANK_SIZE/2, TANK_SIZE/1.5, 0, 2 * Math.PI);
                    ctx.stroke();
                }}
            }}
            
            // 畫敵人 (病毒)
            for (let id in gameState.enemies) {{
                let e = gameState.enemies[id];
                // --> 關鍵修改：使用 drawImage 畫出病毒圖片 <--
                ctx.drawImage(virusImg, e.x, e.y, TANK_SIZE, TANK_SIZE);
            }}
            
            // 畫子彈 (改成亮藍色能量球)
            ctx.fillStyle = '#8be9fd';
            ctx.shadowBlur = 10; ctx.shadowColor = '#8be9fd'; // 加一點發光效果
            gameState.bullets.forEach(b => {{
                ctx.beginPath(); ctx.arc(b.x, b.y, 5, 0, Math.PI*2); ctx.fill();
            }});
            ctx.shadowBlur = 0; // 畫完子彈後關閉發光，避免影響其他物件
        }}

        // --- 控制邏輯 (不變) ---
        function sendMove(dir) {{
            let dx=0, dy=0;
            const speed = 10;
            if (dir==='up') dy=-speed;
            if (dir==='down') dy=speed;
            if (dir==='left') dx=-speed;
            if (dir==='right') dx=speed;
            socket.emit('move', {{dx, dy, dir}});
        }}

        const setupBtn = (id, dir) => {{
            const el = document.getElementById(id);
            const handleAction = (e) => {{ e.preventDefault(); sendMove(dir); }};
            el.addEventListener('touchstart', handleAction);
            el.addEventListener('mousedown', handleAction);
        }};
        setupBtn('up', 'up'); setupBtn('down', 'down');
        setupBtn('left', 'left'); setupBtn('right', 'right');

        const fireBtn = document.getElementById('fire');
        const handleFire = (e) => {{ e.preventDefault(); socket.emit('shoot'); }};
        fireBtn.addEventListener('touchstart', handleFire);
        fireBtn.addEventListener('mousedown', handleFire);

        document.addEventListener('keydown', (e) => {{
            if (e.key === 'ArrowUp') sendMove('up');
            if (e.key === 'ArrowDown') sendMove('down');
            if (e.key === 'ArrowLeft') sendMove('left');
            if (e.key === 'ArrowRight') sendMove('right');
            if (e.code === 'Space') socket.emit('shoot');
        }});
    </script>
</body>
</html>
"""

components.html(html_code, height=850)
