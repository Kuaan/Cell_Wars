// frontend/main.js v5.3 - UI Logic Update
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

// --- UI 更新邏輯 (核心修改) ---
function updateUI() {
    if (!myId || !gameState.players[myId]) return;
    const me = gameState.players[myId];
    
    // 1. 排行榜
    const sorted = Object.values(gameState.players).sort((a,b)=>b.score-a.score).slice(0,3);
    document.getElementById('lb-content').innerHTML = sorted.map((p, i) => `<span class="score-pill">${i==0?'👑':''}${p.name}:${p.score}</span>`).join('');

    // 2. 能量條顯示
    for(let i=1; i<=3; i++) {
        const elSeg = document.getElementById('seg'+i);
        const elFill = document.getElementById('fill'+i);
        
        if (me.charge >= i) { 
            // 滿格狀態
            elSeg.classList.add('active'); // 配合 CSS v5.3 修改 class 名稱
            elFill.style.width = '100%'; 
        }
        else if (me.charge === i - 1) { 
            // 正在充能的這一格
            elSeg.classList.remove('active'); 
            let percent = ((me.ha || 0) / 20) * 100; 
            elFill.style.width = percent + '%'; 
        }
        else { 
            elSeg.classList.remove('active'); 
            elFill.style.width = '0%'; 
        }
    }

    // 3. 按鈕狀態控制 (新功能)
    // 只要有 1 格能量，護盾與雷射按鈕都亮起
    const hasEnergy = me.charge >= 1;
    const skillBtn = document.getElementById('skill-btn');
    const laserBtn = document.getElementById('laser-btn');

    if (hasEnergy) {
        skillBtn.classList.remove('disabled');
        laserBtn.classList.remove('disabled');
    } else {
        skillBtn.classList.add('disabled');
        laserBtn.classList.add('disabled');
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
        socket.emit('move', { dx: data.vector.x, dy: -data.vector.y });
        const angleRad = Math.atan2(-data.vector.y, data.vector.x);
        currentAimAngle = angleRad * (180 / Math.PI);
    }
});

manager.on('end', () => { 
    socket.emit('move', { dx: 0, dy: 0 }); 
});

function doFire() {
    const now = Date.now();
    if (now - lastShotTime < 150) return;
    lastShotTime = now;
    socket.emit('shoot', { angle: currentAimAngle });
    playSfx('p_shot');
}

function doSkill() { 
    // 前端簡單檢查：有能量才發送
    if (gameState.players[myId] && gameState.players[myId].charge >= 1) {
        socket.emit('use_skill'); 
    }
}

function doLaser() {
    // 前端簡單檢查：有能量才發送
    if (gameState.players[myId] && gameState.players[myId].charge >= 1) {
        socket.emit('use_laser', { angle: currentAimAngle });
    }
}

// 綁定觸控與滑鼠事件
const fireBtn = document.getElementById('fire-btn');
fireBtn.addEventListener('touchstart', (e) => { e.preventDefault(); doFire(); });
fireBtn.addEventListener('mousedown', (e) => { e.preventDefault(); doFire(); });

const skillBtn = document.getElementById('skill-btn');
skillBtn.addEventListener('touchstart', (e) => { e.preventDefault(); doSkill(); });
skillBtn.addEventListener('mousedown', (e) => { e.preventDefault(); doSkill(); });

const laserBtn = document.getElementById('laser-btn');
laserBtn.addEventListener('touchstart', (e) => { e.preventDefault(); doLaser(); });
laserBtn.addEventListener('mousedown', (e) => { e.preventDefault(); doLaser(); });

// 鍵盤綁定
document.addEventListener('keydown', (e) => {
    if (e.repeat) return; // 避免長按重複觸發
    if (e.code === 'Space') doFire();
    if (e.key === 'q' || e.key === 'Q') doSkill();
    if (e.key === 'e' || e.key === 'E') doLaser();
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
