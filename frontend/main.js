// frontend/main.js

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
let currentAngle = -Math.PI / 2; // 預設朝上

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
        // NippleJS vector y 是向上的為正，但在 Canvas 座標系 y 向下為正，所以這裡 dy 要取負
        let dx = data.vector.x;
        let dy = -data.vector.y; 
        
        // 計算角度 (radians)
        currentAngle = Math.atan2(dy, dx);

        socket.emit('move', { 
            dx: dx, 
            dy: dy,
            angle: currentAngle // 傳送角度給後端 (若後端支援)
        }); 
    }
});

manager.on('end', () => { 
    // 停止移動，但不重置 currentAngle，這樣角色會停留在最後面向的角度
    socket.emit('move', { dx: 0, dy: 0, angle: currentAngle }); 
});

function doFire() {
    const now = Date.now();
    if (now - lastShotTime < 150) return;
    lastShotTime = now;
    
    // 發送射擊指令，帶上當前的角度
    socket.emit('shoot', { angle: currentAngle });
    playSfx('p_shot');
}

function doSkill() { 
    // 技能也帶上方向
    socket.emit('use_skill', { angle: currentAngle }); 
}

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
