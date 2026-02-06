// 初始化
const socket = io(SERVER_URL, { transports: ['websocket'] });
const audioCtrl = new AudioController();

// 遊戲狀態變數
let myId = null;
let lastState = null;     // 上一次從 Server 收到的狀態
let currentState = null;  // 最新收到的狀態
let lastStateTime = 0;    
let currentStateTime = 0;
const SERVER_TICK_RATE = 50; // ms (對應後端的廣播頻率)

// UI 元素
const loginBox = document.getElementById('login-overlay');
const startBtn = document.getElementById('start-btn');
const nameInput = document.getElementById('name-input');
const volBgm = document.getElementById('vol-bgm');
const volSfx = document.getElementById('vol-sfx');

// --- 搖桿設定 (Nipple.js) ---
const joystick = nipplejs.create({
    zone: document.getElementById('joystick-zone'),
    mode: 'static',
    position: { left: '50%', top: '50%' },
    color: '#bd93f9',
    size: 100
});

// 輸入狀態
let inputState = { dx: 0, dy: 0, fire: false, angle: -90 };

// 監聽搖桿
joystick.on('move', (evt, data) => {
    if (data.vector) {
        inputState.dx = data.vector.x;
        inputState.dy = -data.vector.y; // Nipple Y軸向上是正，Canvas向下是正，需反轉邏輯確認
        // 修正: HTML Canvas Y 軸向下增加，Nipple 向上增加
        // 這裡直接傳向量給後端，後端 p.y += dy，若 dy 為負則向上
        inputState.dy = -data.vector.y; 
        inputState.angle = data.angle.degree;
    }
});
joystick.on('end', () => {
    inputState.dx = 0; inputState.dy = 0;
});

// 按鈕監聽
const btnFire = document.getElementById('fire-btn');
const btnSkill = document.getElementById('skill-btn'); // WALL / SKILL
const btnBuild = document.getElementById('build-btn'); // WALL

// 觸控/滑鼠支援
const handleFireStart = (e) => { e.preventDefault(); inputState.fire = true; };
const handleFireEnd = (e) => { e.preventDefault(); inputState.fire = false; };

btnFire.addEventListener('mousedown', handleFireStart);
btnFire.addEventListener('touchstart', handleFireStart);
btnFire.addEventListener('mouseup', handleFireEnd);
btnFire.addEventListener('touchend', handleFireEnd);

// Wall 按鈕 (對應 use_skill 事件)
btnBuild.addEventListener('click', () => {
    socket.emit('use_skill'); // 這裡可以觸發後端的技能
});

// --- Socket 事件 ---

socket.on('connect', () => {
    console.log("Connected to server");
    startBtn.innerText = "START GAME";
    startBtn.disabled = false;
});

socket.on('init_game', (data) => {
    myId = data.id;
    loginBox.style.display = 'none';
    audioCtrl.enable();
    audioCtrl.play('powerup'); // Start sound
    gameLoop(); // 開始渲染迴圈
});

socket.on('state_update', (data) => {
    // 狀態緩衝與插值準備
    lastState = currentState;
    lastStateTime = currentStateTime;
    
    currentState = data;
    currentStateTime = Date.now();

    // 處理音效事件 (從後端來的 sfx 列表)
    if (data.events && data.events.length > 0) {
        data.events.forEach(evt => {
            // 特效
            if (evt.type === 'enemy_hitted' || evt.type === 'boss_hitted') {
                // 我們沒傳座標，所以暫時隨機或不畫，這裡簡單畫在畫面中央示意
                // 為了更好的體驗，建議後端 event 帶上 x, y
            }
            // 音效
            audioCtrl.play(evt.type);
        });
    }

    // 更新 UI (分數、充能)
    if (myId && currentState.p[myId]) {
        const me = currentState.p[myId];
        document.getElementById('lb-content').innerText = `SCORE: ${me.s}`;
        
        // 更新充能條 UI
        // 假設 me.charge 是 0-3
        // 這裡需要根據 me.charge 更新 .charge-fill 的 width
        for(let i=1; i<=3; i++) {
            let fill = document.getElementById(`fill${i}`);
            if (me.charge >= i) fill.style.width = "100%";
            else fill.style.width = "0%";
        }
        
        // 武器圖示
        btnFire.innerText = me.w_icon || "🔥";
    }
});

// --- 登入流程 ---
startBtn.addEventListener('click', () => {
    const name = nameInput.value || "Soldier";
    socket.emit('join_game', { name: name, skin: 1 });
});

// 音量控制
volBgm.addEventListener('input', (e) => audioCtrl.setBgmVolume(e.target.value));
volSfx.addEventListener('input', (e) => audioCtrl.setSfxVolume(e.target.value));

// --- 遊戲迴圈 (Render Loop) ---
function gameLoop() {
    const now = Date.now();
    
    // 1. 計算插值係數 (Alpha)
    // 我們希望在收到兩個狀態之間進行平滑過渡
    let alpha = 0;
    if (currentState && lastState) {
        const timeSinceLastUpdate = now - currentStateTime;
        // 預測插值：假設更新間隔是 SERVER_TICK_RATE
        // 限制 alpha 在 0~1 之間
        alpha = Math.min(timeSinceLastUpdate / SERVER_TICK_RATE, 1.0);
    }

    // 2. 繪圖
    renderGame(currentState, lastState, alpha, myId);

    // 3. 發送輸入 (Input Loop)
    // 限制發送頻率，例如每秒 30 次，或者每一幀都發送 (視伺服器負載)
    // 為了反應靈敏，這裡每幀發送，但在後端有檢查
    if (myId) {
        socket.emit('player_input', inputState);
    }

    requestAnimationFrame(gameLoop);
}
