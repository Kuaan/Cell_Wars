const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');

// 設定畫布尺寸
function resizeCanvas() {
    // 保持 4:3 或 寬螢幕比例，但最大不超過視窗
    const aspect = 600 / 500;
    let w = window.innerWidth;
    let h = window.innerHeight;
    
    if (w / h > aspect) {
        w = h * aspect;
    } else {
        h = w / aspect;
    }
    
    canvas.width = 600;  // 邏輯解析度寬
    canvas.height = 500; // 邏輯解析度高
    canvas.style.width = `${w}px`;
    canvas.style.height = `${h}px`;
}
window.addEventListener('resize', resizeCanvas);
resizeCanvas();

// --- 繪圖工具 ---

function clearCanvas() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
}

/**
 * 繪製可旋轉的物件
 * @param {number} x 中心 X
 * @param {number} y 中心 Y
 * @param {number} angle 旋轉角度 (弧度)
 * @param {function} drawFn 實際繪製內容的函式 (以 0,0 為中心)
 */
function drawRotated(x, y, angle, drawFn) {
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(angle);
    drawFn();
    ctx.restore();
}

// 繪製玩家 (支援跟隨搖桿旋轉)
function drawPlayer(p, angle) {
    drawRotated(p.x + 15, p.y + 15, angle, () => {
        // 這裡繪製一個簡單的像素風格戰機/細胞
        ctx.fillStyle = p.c || '#50fa7b';
        
        // 本體
        ctx.beginPath();
        ctx.moveTo(0, -15); // 尖端 (朝上，因為 -90 度是上)
        ctx.lineTo(12, 12);
        ctx.lineTo(0, 8);
        ctx.lineTo(-12, 12);
        ctx.closePath();
        ctx.fill();

        // 武器圖示或裝飾
        if (p.w_icon) {
            ctx.fillStyle = "#fff";
            ctx.font = "10px Arial";
            ctx.fillText(p.w_icon, -5, 5);
        }
        
        // 受傷/無敵閃爍
        if (p.invincible) {
            ctx.strokeStyle = "white";
            ctx.lineWidth = 2;
            ctx.stroke();
        }
    });

    // ID
    ctx.fillStyle = "white";
    ctx.font = "12px Courier";
    ctx.textAlign = "center";
    ctx.fillText(p.name, p.x + 15, p.y - 10);
}

// 繪製敵人
function drawEnemy(e) {
    const cx = e.x + e.size/2;
    const cy = e.y + e.size/2;
    
    // 簡單的呼吸動畫
    const pulse = Math.sin(Date.now() / 200) * 2;
    
    ctx.fillStyle = e.type === 999 ? "#ff0000" : (e.type === 3 ? "#ff5555" : "#bd93f9");
    
    // Boss 畫大一點，且有特效
    if (e.type === 999) {
        ctx.beginPath();
        ctx.arc(cx, cy, (e.size/2) + pulse, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = "yellow";
        ctx.lineWidth = 3;
        ctx.stroke();
    } else {
        // 普通怪 (病毒形狀)
        ctx.beginPath();
        const spikes = 8;
        const outerRadius = e.size / 2;
        const innerRadius = e.size / 4;
        
        for (let i = 0; i < spikes * 2; i++) {
            const r = (i % 2 === 0) ? outerRadius : innerRadius;
            const a = (Math.PI * i) / spikes + (Date.now()/1000); // 自轉
            ctx.lineTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r);
        }
        ctx.closePath();
        ctx.fill();
    }
    
    // 血條
    const hpPct = e.hp / e.max_hp;
    ctx.fillStyle = "red";
    ctx.fillRect(e.x, e.y - 8, e.size, 4);
    ctx.fillStyle = "#50fa7b";
    ctx.fillRect(e.x, e.y - 8, e.size * hpPct, 4);
}

// 繪製子彈 (根據顏色或類型優化)
function drawBullet(b) {
    ctx.fillStyle = b.c || "#fff";
    
    // 如果沒有速度向量，預設圓形。如果有(這裡預設畫圓，因為後端尚未傳送 dx/dy)
    // 為了視覺優化，我們加光暈
    ctx.shadowBlur = 5;
    ctx.shadowColor = b.c || "#fff";
    
    ctx.beginPath();
    ctx.arc(b.x, b.y, b.s || 5, 0, Math.PI * 2);
    ctx.fill();
    
    ctx.shadowBlur = 0; // 重置
}

function drawItem(item) {
    ctx.fillStyle = "#f1fa8c";
    ctx.beginPath();
    ctx.arc(item.x + 10, item.y + 10, 8, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#000";
    ctx.font = "10px Arial";
    ctx.fillText("?", item.x + 7, item.y + 14);
}
