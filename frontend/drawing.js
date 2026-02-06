const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');

// 粒子系統
let particles = [];
class Particle {
    constructor(x, y, color) {
        this.x = x; this.y = y; this.color = color;
        this.vx = (Math.random() - 0.5) * 4;
        this.vy = (Math.random() - 0.5) * 4;
        this.life = 1.0;
    }
    update() {
        this.x += this.vx; this.y += this.vy;
        this.life -= 0.05;
    }
    draw(ctx) {
        ctx.globalAlpha = this.life;
        ctx.fillStyle = this.color;
        ctx.fillRect(this.x, this.y, 4, 4);
        ctx.globalAlpha = 1.0;
    }
}

// 產生爆炸特效
function spawnExplosion(x, y, color, count=5) {
    for(let i=0; i<count; i++) particles.push(new Particle(x, y, color));
}

// 線性插值：讓移動平滑
function lerp(start, end, t) {
    return start * (1 - t) + end * t;
}

// 核心繪圖函式
function renderGame(state, prevState, alpha, myId) {
    // 1. 清空畫布
    ctx.fillStyle = '#0d0211';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // 2. 繪製網格背景 (增加速度感)
    ctx.strokeStyle = '#1a0620';
    ctx.lineWidth = 1;
    const offset = (Date.now() / 50) % 40;
    for (let i = 0; i < canvas.width; i += 40) {
        ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, canvas.height); ctx.stroke();
    }
    for (let i = 0; i < canvas.height; i += 40) {
        ctx.beginPath(); ctx.moveTo(0, i + offset); ctx.lineTo(canvas.width, i + offset); ctx.stroke();
    }

    if (!state) return;

    // 3. 繪製道具
    state.i.forEach(item => {
        ctx.fillStyle = item.t === 'heal' ? '#ff5555' : '#f1fa8c';
        ctx.beginPath();
        ctx.arc(item.x, item.y, 8, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = '#fff';
        ctx.font = '10px Arial';
        ctx.fillText("?", item.x-3, item.y+3);
    });

    // 4. 繪製敵人
    state.e.forEach(enemy => {
        // 嘗試從舊狀態找對應 ID 做插值
        let x = enemy.x, y = enemy.y;
        if (prevState) {
            const prev = prevState.e.find(e => e.id === enemy.id);
            if (prev) {
                x = lerp(prev.x, enemy.x, alpha);
                y = lerp(prev.y, enemy.y, alpha);
            }
        }

        ctx.save();
        ctx.translate(x, y);
        
        // 根據類型畫不同圖形
        if (enemy.t === 999) { // Boss
            ctx.fillStyle = '#ff5555';
            ctx.fillRect(0, 0, enemy.s, enemy.s);
            // Boss 血條
            ctx.fillStyle = 'red';
            ctx.fillRect(0, -10, enemy.s, 5);
            ctx.fillStyle = '#0f0';
            ctx.fillRect(0, -10, enemy.s * (enemy.hp / 500), 5); // 假設 Boss 500血
        } else {
            ctx.fillStyle = enemy.t === 3 ? '#f1fa8c' : (enemy.t === 2 ? '#ff79c6' : '#bd93f9');
            // 簡單的病毒形狀 (帶刺的圓)
            ctx.beginPath();
            ctx.arc(enemy.s/2, enemy.s/2, enemy.s/2, 0, Math.PI*2);
            ctx.fill();
        }
        ctx.restore();
    });

    // 5. 繪製玩家
    Object.keys(state.p).forEach(pid => {
        const p = state.p[pid];
        let x = p.x, y = p.y;
        
        // 插值
        if (prevState && prevState.p[pid]) {
            x = lerp(prevState.p[pid].x, p.x, alpha);
            y = lerp(prevState.p[pid].y, p.y, alpha);
        }

        ctx.save();
        ctx.translate(x, y);

        // 無敵閃爍
        if (p.iv && Math.floor(Date.now() / 100) % 2 === 0) ctx.globalAlpha = 0.5;

        // 玩家本體
        ctx.fillStyle = pid === myId ? '#50fa7b' : '#6272a4';
        ctx.beginPath();
        ctx.arc(15, 15, 15, 0, Math.PI*2); // 半徑15
        ctx.fill();

        // 名字
        ctx.fillStyle = '#fff';
        ctx.font = '10px Courier';
        ctx.fillText(pid === myId ? "YOU" : "P" + pid.substr(0,2), 5, -5);

        // 血條
        ctx.fillStyle = '#444';
        ctx.fillRect(0, 35, 30, 4);
        ctx.fillStyle = '#ff5555';
        ctx.fillRect(0, 35, 30 * (p.hp / (p.hp+2)), 4); // 粗略估算比例

        ctx.restore();
    });

    // 6. 繪製子彈
    state.b.forEach(b => {
        // 子彈速度快，通常不做插值，直接畫最新位置以免視覺延遲感
        ctx.fillStyle = b.c || (b.t === 1 ? '#ffff00' : '#ff5555');
        ctx.beginPath();
        ctx.arc(b.x, b.y, b.s, 0, Math.PI*2);
        ctx.fill();
    });

    // 7. 更新與繪製粒子
    particles = particles.filter(p => p.life > 0);
    particles.forEach(p => { p.update(); p.draw(ctx); });

    // 8. 警告層
    if (state.w) { // warning_active
        if (Math.floor(Date.now() / 500) % 2 === 0) {
            ctx.fillStyle = 'rgba(255, 0, 0, 0.2)';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = 'red';
            ctx.font = '30px Courier';
            ctx.fillText("WARNING", canvas.width/2 - 60, canvas.height/2);
        }
    }
}
