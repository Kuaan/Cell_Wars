const socket = io(SERVER_URL, {
    transports: ['websocket', 'polling'],
    reconnection: true
});

let myId = null;
let gameState = { players: {}, enemies: {}, bullets: [], items: [] };
let joystickAngle = -Math.PI / 2; // 預設朝上 (-90度)
let lastMoveTime = 0;

// --- Nipple.js 搖桿設定 ---
const joystickManager = nipplejs.create({
    zone: document.getElementById('joystick-zone'),
    mode: 'static',
    position: { left: '50%', top: '50%' },
    color: 'white',
    size: 100
});

// 監聽搖桿移動
joystickManager.on('move', (evt, data) => {
    if (data && data.vector) {
        // 1. 計算移動向量
        const dx = data.vector.x;
        const dy = data.vector.y; // Nipple.js 的 y 向上是負的嗎? 需確認，通常向下是正
        // 在 Nipple 中，上是 y<0 (如果用 vector)，但在 HTML canvas 座標系 y 向下是正
        // data.vector.y 向上是正，向下是負。
        // 我們後端地圖: y 向下增加。所以 dy 需要反轉或是直接使用 vector?
        // 修正：Nipple 的 vector {x, y} 是正規化的單位向量。上是 y=1, 下是 y=-1。
        // 後端需求：dy > 0 往下。所以傳送時 dy 要 = -data.vector.y
        
        const sendDx = data.vector.x;
        const sendDy = -data.vector.y; 

        // 2. 捕捉角度 (用於繪圖旋轉)
        // data.angle.radian: 0是右, PI/2是上, PI是左...
        // 我們需要轉換成 Canvas rotate 的角度 (0是右, 順時針增加)
        // Nipple radian: 逆時針。
        joystickAngle = -data.angle.radian; 

        // 3. 限制傳送頻率 (每 30ms 傳一次，避免塞爆)
        const now = Date.now();
        if (now - lastMoveTime > 30) {
            socket.emit('move', { dx: sendDx, dy: sendDy });
            lastMoveTime = now;
        }
    }
});

joystickManager.on('end', () => {
    socket.emit('move', { dx: 0, dy: 0 });
});

// --- 按鈕事件 ---
const btnFire = document.getElementById('btn-fire');
const btnSkill = document.getElementById('btn-skill');

// 支援連點與長按
let isFiring = false;
let fireInterval = null;

function startFire() {
    if (!isFiring) {
        isFiring = true;
        socket.emit('shoot'); // 立即射一發
        fireInterval = setInterval(() => socket.emit('shoot'), 150); // 連射
        btnFire.style.transform = "scale(0.9)";
    }
}
function stopFire() {
    isFiring = false;
    clearInterval(fireInterval);
    btnFire.style.transform = "scale(1)";
}

// 電腦版按鍵支援
document.addEventListener('keydown', (e) => {
    if (e.code === 'Space') startFire();
});
document.addEventListener('keyup', (e) => {
    if (e.code === 'Space') stopFire();
});

// 手機觸控支援
btnFire.addEventListener('touchstart', (e) => { e.preventDefault(); startFire(); });
btnFire.addEventListener('touchend', (e) => { e.preventDefault(); stopFire(); });
btnFire.addEventListener('mousedown', startFire);
btnFire.addEventListener('mouseup', stopFire);

btnSkill.addEventListener('click', () => {
    socket.emit('use_skill');
});

// --- Socket 事件 ---
socket.on('connect', () => {
    document.getElementById('connection-status').innerText = "Connected: " + socket.id;
    myId = socket.id;
});

socket.on('state_update', (state) => {
    // 簡單的狀態更新，若要更滑順可做 Linear Interpolation (Lerp)
    gameState = state;
});

socket.on('sfx', (data) => {
    audio.play(data.type);
});

// --- 遊戲循環 (Render Loop) ---
function gameLoop() {
    clearCanvas();

    // 1. 繪製道具
    gameState.items.forEach(drawItem);

    // 2. 繪製子彈
    gameState.bullets.forEach(drawBullet);

    // 3. 繪製敵人
    Object.values(gameState.enemies).forEach(drawEnemy);

    // 4. 繪製玩家
    Object.keys(gameState.players).forEach(pid => {
        const p = gameState.players[pid];
        
        // 如果是自己，使用搖桿角度；如果是別人，暫時預設朝上(或根據移動方向)
        let rotation = -Math.PI / 2; 
        if (pid === myId) {
            rotation = joystickAngle; 
            
            // 更新 UI
            document.getElementById('score-val').innerText = p.score;
            const hpPct = (p.hp / p.max_hp) * 100;
            document.getElementById('hp-bar').style.width = hpPct + "%";
        }
        
        drawPlayer(p, rotation);
    });
    
    // 5. 警告特效
    if (gameState.w) { // warning_active
        ctx.fillStyle = `rgba(255, 0, 0, ${Math.abs(Math.sin(Date.now()/200)) * 0.3})`;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = "red";
        ctx.font = "40px Arial";
        ctx.textAlign = "center";
        ctx.fillText("WARNING", canvas.width/2, canvas.height/2);
    }

    requestAnimationFrame(gameLoop);
}

// --- 啟動畫面 ---
document.getElementById('btn-start').addEventListener('click', () => {
    const name = document.getElementById('username').value || "Soldier";
    socket.emit('join_game', { name: name });
    document.getElementById('start-screen').style.display = 'none';
    audio.playBGM(SOUNDS_BASE + 'bgm_battle.mp3'); // 需自行準備路徑
    gameLoop();
});
