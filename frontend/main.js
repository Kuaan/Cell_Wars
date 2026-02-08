// frontend/main.js v5.0

// 圖片載入
const skins = { cells: [], viruses: [], boss: null };
function loadImg(path) {
    let img = new Image(); img.src = path;
    return img;
}

for(let i=1; i<=3; i++) {
    skins.cells.push(loadImg(ASSETS_BASE + "cell_" + i + ".png"));
    skins.viruses.push(loadImg(ASSETS_BASE + "virus_" + i + ".png"));
}
skins.boss = loadImg(ASSETS_BASE + "boss_1.png");

// 遊戲狀態與連線
const socket = io(SERVER_URL, { reconnection: true });
const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');

let gameState = { players: {}, enemies: {}, bullets: [], items: [], skill_objects: [], w: false };
let myId = null;
let lastShotTime = 0;

socket.on('connect', () => { myId = socket.id; });

// 接收音效指令 (調用 audio.js 裡的 playSfx)
socket.on('sfx', (data) => {
    switch(data.type) {
        case 'character_hitted': playSfx('p_hit'); break;
        case 'boss_coming': playSfx('boss_come'); break;
        case 'boss_hitted': playSfx('boss_hit'); break;
        case 'boss_shot': playSfx('boss_shot'); break;
        case 'enemy_hitted': playSfx('e_hit'); break;
        case 'enemy_nor_shot': playSfx('e_shot'); break;
        case 'skill_slime': playSfx('skill'); break;
        case 'powerup': playSfx('powerup'); break;
    }
});

// 更新畫面
socket.on('state_update', (data) => {
    gameState = data;
    requestAnimationFrame(draw); // draw() 在 drawing.js 定義
    updateUI();
});

function updateUI() {
    if (!myId || !gameState.players[myId]) return;
    const me = gameState.players[myId];
    
    // 排行榜
    const sorted = Object.values(gameState.players).sort((a,b)=>b.score-a.score).slice(0,3);
    document.getElementById('lb-content').innerHTML = sorted.map((p, i) => `<span class="score-pill">${i==0?'👑':''}${p.name}:${p.score}</span>`).join('');

    // 能量條
    for(let i=1; i<=3; i++) {
        const elSeg = document.getElementById('seg'+i);
        const elFill = document.getElementById('fill'+i);
        if (me.charge >= i) { elSeg.classList.add('full'); elFill.style.width = '100%'; }
        else if (me.charge === i - 1) { elSeg.classList.remove('full'); elFill.style.width = ((me.hit_accumulated / 20) * 100) + '%'; }
        else { elSeg.classList.remove('full'); elFill.style.width = '0%'; }
    }
    
    const sBtn = document.getElementById('skill-btn');
    if (me.charge >= 1) sBtn.classList.remove('disabled'); else sBtn.classList.add('disabled');

    const fBtn = document.getElementById('fire-btn');
    if (me.w_icon && fBtn.innerText !== me.w_icon) {
        fBtn.innerText = me.w_icon; 
    }
}

// 搖桿與操作
let currentAimAngle = -90; // 預設向上

const manager = nipplejs.create({
    zone: document.getElementById('joystick-zone'),
    mode: 'static',
    position: { left: '70px', top: '70px' },
    size: 100,
    color: 'white'
});

manager.on('move', (evt, data) => { 
    if(data.vector) {
        // NippleJS 的 vector.y 向上是正，但 Canvas 座標向下是正，所以 dy 取負
        socket.emit('move', { dx: data.vector.x, dy: -data.vector.y });
        
        // 計算角度 (Degree)
        // Math.atan2(y, x) 回傳弧度，轉換為角度
        // 注意：這裡我們用 -data.vector.y 來符合螢幕座標系 (上為負)
        const angleRad = Math.atan2(-data.vector.y, data.vector.x);
        currentAimAngle = angleRad * (180 / Math.PI);
    }
});

manager.on('end', () => { 
    socket.emit('move', { dx: 0, dy: 0 }); 
    // 不重置 currentAimAngle，這樣玩家停下來時還能朝最後方向射擊
});

function doFire() {
    const now = Date.now();
    if (now - lastShotTime < 150) return;
    lastShotTime = now;
    
    // 發送射擊指令，帶上角度
    socket.emit('shoot', { angle: currentAimAngle });
    playSfx('p_shot');
}

function doSkill() { socket.emit('use_skill'); }

document.getElementById('fire-btn').addEventListener('touchstart', (e) => { e.preventDefault(); doFire(); });
document.getElementById('fire-btn').addEventListener('mousedown', (e) => { e.preventDefault(); doFire(); });
document.getElementById('skill-btn').addEventListener('touchstart', (e) => { e.preventDefault(); doSkill(); });
document.getElementById('skill-btn').addEventListener('mousedown', (e) => { e.preventDefault(); doSkill(); });

document.addEventListener('keydown', (e) => {
    if (e.code === 'Space') doFire();
    if (e.key === 'q' || e.key === 'Q') doSkill();
});

// 開始按鈕
document.getElementById('start-btn').onclick = function() {
    if (audioCtx.state === 'suspended') {
        audioCtx.resume().then(() => { console.log("AudioContext unlocked"); });
    }
    playBGM();
    const name = document.getElementById('name-input').value || 'Cell';
    socket.emit('join_game', { name: name });
    document.getElementById('login-overlay').style.display = 'none';
};
