# app.py 
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Cell Wars", layout="wide")


st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stApp {overflow: hidden;}
    </style>
""", unsafe_allow_html=True)


SERVER_URL = "http://localhost:8000"

html_code = f"""
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <script src="https://cdn.socket.io/4.6.0/socket.io.min.js"></script>
    <style>
        body {{ 
            background-color: #111; color: white; margin: 0; 
            display: flex; flex-direction: column; align-items: center; 
            font-family: sans-serif; overflow: hidden; touch-action: none;
        }}
        canvas {{ 
            background-color: #000; border-bottom: 2px solid #444; 
            width: 100vw; height: auto; max-height: 60vh;
        }}
        #ui-container {{
            width: 100%; display: flex; justify-content: space-around; align-items: center;
            padding: 20px 0; background: #222; height: 35vh;
        }}
        .d-pad {{
            display: grid; grid-template-columns: 60px 60px 60px; grid-template-rows: 60px 60px 60px;
        }}
        .btn {{
            background: #444; border: 1px solid #666; color: white;
            display: flex; justify-content: center; align-items: center;
            user-select: none; border-radius: 10px; font-weight: bold;
        }}
        .btn:active {{ background: #888; transform: scale(0.95); }}
        .btn-up {{ grid-column: 2; grid-row: 1; }}
        .btn-down {{ grid-column: 2; grid-row: 3; }}
        .btn-left {{ grid-column: 1; grid-row: 2; }}
        .btn-right {{ grid-column: 3; grid-row: 2; }}

        .fire-container {{ width: 100px; height: 100px; }}
        .btn-fire {{
            width: 80px; height: 80px; background: #ff4444; border-radius: 50%;
            display: flex; justify-content: center; align-items: center; font-size: 20px;
        }}
        #status {{ position: absolute; top: 10px; left: 10px; font-size: 12px; pointer-events: none; }}
    </style>
</head>
<body>
    <div id="status">連線中...</div>
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

        socket.on('state_update', (data) => {{
            gameState = data;
            requestAnimationFrame(draw);
            if (gameState.players[socket.id]) {{
                const p = gameState.players[socket.id];
                statusDiv.innerHTML = `HP: ${{p.hp}} | Score: ${{p.score}}`;
            }}
        }});

        function draw() {{
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            // 
            for (let id in gameState.players) {{
                let p = gameState.players[id];
                
                //HP
                ctx.fillStyle = 'red';
                ctx.fillRect(p.x, p.y - 10, 30, 5); // red
                ctx.fillStyle = '#0f0';
                ctx.fillRect(p.x, p.y - 10, 30 * (p.hp / 3), 5); // green
                //
                
                ctx.fillStyle = p.color;
                ctx.fillRect(p.x, p.y, 30, 30);
                if (id === socket.id) {{
                    ctx.strokeStyle = 'yellow'; ctx.strokeRect(p.x, p.y, 30, 30);
                }}
            }}
            // 
            for (let id in gameState.enemies) {{
                let e = gameState.enemies[id];
                ctx.fillStyle = 'red';
                ctx.fillRect(e.x, e.y, 30, 30);
            }}
            // 
            ctx.fillStyle = 'yellow';
            gameState.bullets.forEach(b => {{
                ctx.beginPath(); ctx.arc(b.x, b.y, 4, 0, Math.PI*2); ctx.fill();
            }});
        }}

        // ctrl
        function sendMove(dir) {{
            let dx=0, dy=0;
            const speed = 10;
            if (dir==='up') dy=-speed;
            if (dir==='down') dy=speed;
            if (dir==='left') dx=-speed;
            if (dir==='right') dx=speed;
            socket.emit('move', {{dx, dy, dir}});
        }}

        // touch event
        const setupBtn = (id, dir) => {{
            const el = document.getElementById(id);
            // support wouch and mouse
            const handleAction = (e) => {{ e.preventDefault(); sendMove(dir); }};
            el.addEventListener('touchstart', handleAction);
            el.addEventListener('mousedown', handleAction);
        }};

        setupBtn('up', 'up');
        setupBtn('down', 'down');
        setupBtn('left', 'left');
        setupBtn('right', 'right');

        const fireBtn = document.getElementById('fire');
        const handleFire = (e) => {{ e.preventDefault(); socket.emit('shoot'); }};
        fireBtn.addEventListener('touchstart', handleFire);
        fireBtn.addEventListener('mousedown', handleFire);

        // keep KB support 
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

# 使用更寬的高度來容納控制按鈕
components.html(html_code, height=800)
