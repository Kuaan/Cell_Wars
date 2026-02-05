// frontend/main.js

// 圖片載入 (略，保持原樣)
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

// 增加 walls 到狀態
let gameState = { players: {}, enemies: {}, bullets: [], items: [], skill_objects: [], walls: [], w: false };
let myId = null;
let lastShotTime = 0;
let currentAngle = -90; // 預設向上 (-90度)

socket.on('connect', () => { myId = socket.id; });

// 接收音效指令
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
    requestAnimationFrame(draw); 
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
    
    // Wall CD 顯示 (選擇性)
    const wBtn = document.getElementById('build-btn');
    // 如果後端有傳送 CD 時間最好，這裡暫時不即時顯示 CD 進度條，只做基本按鈕
}

// 搖桿與操作
const manager = nipplejs.create({
    zone: document.getElementById('joystick-zone'),
    mode: 'static',
    position: { left: '70px', top: '70px' },
    size: 100,
    color: 'white'
});

manager.on('move', (evt, data) => { 
    if(data.vector) {
        // 發送移動向量
        socket.emit('move', { dx: data.vector.x, dy: -data.vector.y });
        // 紀錄角度 (nipplejs 的 angle.degree 是 0=右, 90=上, 180=左, 270=下)
        // 但 Canvas 座標系是 Y向下。
        // data.angle.radian: 0是右, PI/2是上(螢幕上方), PI是左。
        // 我們需要轉換成 math.atan2(dy, dx) 的格式：
        // 螢幕座標: dy 負數是向上。
        // Nipple 輸出的 vector.y 是 "上為正"。
        // 所以計算角度:
        const angleRad = Math.atan2(-data.vector.y, data.vector.x);
        currentAngle = angleRad * (180 / Math.PI); // 轉成度數
    }
});
manager.on('end', () => { socket.emit('move', { dx: 0, dy: 0 }); });

function doFire() {
    const now = Date.now();
    if (now - lastShotTime < 150) return;
    lastShotTime = now;
    // 傳送當前角度
    socket.emit('shoot', { angle: currentAngle });
    playSfx('p_shot');
}

function doSkill() { socket.emit('use_skill'); }

// 造牆邏輯
const buildBtn = document.getElementById('build-btn');
const startBuild = (e) => { e.preventDefault(); socket.emit('start_build'); buildBtn.style.opacity = 0.5; };
const stopBuild = (e) => { e.preventDefault(); socket.emit('stop_build'); buildBtn.style.opacity = 1.0; };

buildBtn.addEventListener('touchstart', startBuild);
buildBtn.addEventListener('touchend', stopBuild);
buildBtn.addEventListener('mousedown', startBuild);
buildBtn.addEventListener('mouseup', stopBuild);

document.getElementById('fire-btn').addEventListener('touchstart', (e) => { e.preventDefault(); doFire(); });
document.getElementById('fire-btn').addEventListener('mousedown', (e) => { e.preventDefault(); doFire(); });
document.getElementById('skill-btn').addEventListener('touchstart', (e) => { e.preventDefault(); doSkill(); });
document.getElementById('skill-btn').addEventListener('mousedown', (e) => { e.preventDefault(); doSkill(); });

document.addEventListener('keydown', (e) => {
    if (e.code === 'Space') doFire();
    if (e.key === 'q' || e.key === 'Q') doSkill();
    if (e.key === 'w' || e.key === 'W') socket.emit('start_build'); 
});
document.addEventListener('keyup', (e) => {
    if (e.key === 'w' || e.key === 'W') socket.emit('stop_build');
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
