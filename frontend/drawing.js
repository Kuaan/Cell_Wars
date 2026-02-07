// frontend/drawing.js
function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const time = Date.now();
    
    // 1. 繪製道具 (Items)
    if (gameState.items) {
        gameState.items.forEach(item => {
            let color = '#ffffff';
            if (item.type.includes('spread')) color = '#ffff00';
            else if (item.type.includes('ricochet')) color = '#00ffff';
            else if (item.type.includes('arc')) color = '#ff00ff';
            else if (item.type.includes('heal')) color = '#50fa7b';

            ctx.save();
            ctx.shadowColor = color;
            ctx.shadowBlur = 15;
            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.arc(item.x + 10, item.y + 10, 12, 0, Math.PI * 2);
            ctx.fill();
            ctx.fillStyle = '#ffffff';
            ctx.beginPath();
            ctx.arc(item.x + 10, item.y + 10, 5, 0, Math.PI * 2);
            ctx.fill();
            ctx.restore();
        });
    }

    // 2. 繪製技能物件
    ctx.globalAlpha = 0.6;
    (gameState.skill_objects || []).forEach(obj => {
        let img = skins.cells[(obj.skin || 1) - 1];
        if(img && img.complete) ctx.drawImage(img, obj.x, obj.y, 30, 30);
    });
    ctx.globalAlpha = 1.0;

    // 3. 繪製敵人 (增加旋轉邏輯：面向最近的玩家)
    for (let id in gameState.enemies) {
        let e = gameState.enemies[id];
        let centerX = e.x + e.size / 2;
        let centerY = e.y + e.size / 2;

        // 尋找最近的玩家來決定面向
        let targetAngle = 0; // 預設
        let minDist = 9999;
        let closestPlayer = null;
        
        for (let pid in gameState.players) {
            let p = gameState.players[pid];
            let dist = Math.hypot(p.x - e.x, p.y - e.y);
            if (dist < minDist) {
                minDist = dist;
                closestPlayer = p;
            }
        }

        if (closestPlayer) {
            targetAngle = Math.atan2(closestPlayer.y - e.y, closestPlayer.x - e.x);
        } else {
            targetAngle = Math.PI / 2; // 若無玩家，面向下
        }
        // 修正圖片預設方向 (假設圖片原本朝上 -PI/2，需要轉正)
        // 根據你的素材，通常 0 是右，PI/2 是下。這裡假設素材頭部朝上。
        let rotation = targetAngle + Math.PI / 2; 

        if (e.type === 999) {
            // Boss
            ctx.save();
            ctx.translate(centerX, centerY);
            // Boss 不一定需要旋轉，看設計，這裡先不轉 Boss 避免看起來奇怪
            // ctx.rotate(rotation); 
            ctx.translate(-centerX, -centerY);
            if(skins.boss.complete) ctx.drawImage(skins.boss, e.x, e.y, e.size, e.size);
            ctx.restore();

            const hpRatio = Math.max(0, e.hp / e.max_hp);
            ctx.fillStyle = "#bd93f9"; ctx.fillRect(e.x, e.y-10, e.size * hpRatio, 8);
        } else {
            // 一般病毒
            let img = skins.viruses[(e.type || 1) - 1];
            
            ctx.save();
            ctx.translate(centerX, centerY);
            ctx.rotate(rotation); 
            // 繪製圖片 (以中心點為準)
            if(img && img.complete) ctx.drawImage(img, -e.size/2, -e.size/2, e.size, e.size);
            ctx.restore();

            // 血條不跟著旋轉
            const hpRatio = Math.max(0, e.hp / e.max_hp);
            ctx.fillStyle = "#ff5555"; ctx.fillRect(e.x, e.y-6, e.size * hpRatio, 3);
        }
    }

    // 4. 繪製玩家 (增加旋轉邏輯)
    for (let id in gameState.players) {
        let p = gameState.players[id];
        let size = 30;
        let centerX = p.x + size / 2;
        let centerY = p.y + size / 2;

        if (p.invincible) ctx.globalAlpha = 0.5;
        
        let img = skins.cells[(p.skin || 1) - 1];
        
        // 計算旋轉：如果有 p.angle (來自後端) 則用，否則如果是自己，用 currentAngle
        let rotation = 0;
        if (id === myId) {
            rotation = currentAngle + Math.PI / 2; // 修正素材預設朝上的偏移
        } else if (p.angle !== undefined) {
            rotation = p.angle + Math.PI / 2;
        }

        ctx.save();
        ctx.translate(centerX, centerY);
        ctx.rotate(rotation);
        if(img && img.complete) ctx.drawImage(img, -size/2, -size/2, size, size);
        ctx.restore();
        
        ctx.globalAlpha = 1.0;
        
        // UI 文字與血條 (不旋轉)
        ctx.fillStyle = (id === myId) ? "#f1fa8c" : "white";
        ctx.font = "12px Courier New";
        let estimatedLives = Math.ceil(p.hp / (p.max_hp / 5)); 
        ctx.fillText(p.name + " ❤️x" + estimatedLives, p.x, p.y-15);

        let currentLifeHp = p.hp % (p.max_hp / 5);
        if (currentLifeHp === 0 && p.hp > 0) currentLifeHp = (p.max_hp / 5);
        let maxLifeHp = (p.max_hp / 5);
        
        const hpRatio = Math.max(0, currentLifeHp / maxLifeHp);
        ctx.fillStyle = "#50fa7b"; 
        ctx.fillRect(p.x, p.y-10, 30 * hpRatio, 4);
        ctx.strokeStyle = "#fff";
        ctx.lineWidth = 1;
        ctx.strokeRect(p.x, p.y-10, 30, 4);
    }

    // 5. 繪製子彈
    gameState.bullets.forEach(b => {
        // 檢查是否為 Arc 子彈 (紫色 #ff00ff)
        if (b.c === '#ff00ff' || b.c==='#aa00aa' || b.c === 'rgb(255, 0, 255)') {
            ctx.save();
            ctx.translate(b.x, b.y);
            ctx.rotate(time * 0.008); 
            
            ctx.font = "30px sans-serif";
            ctx.fillStyle = "#ff00ff";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText("🎵", 0, 0); 
            
            ctx.restore();
        } else {
            // 一般子彈
            ctx.beginPath();
            if (b.c) {
                ctx.fillStyle = b.c;
            } else {
                if (b.owner === 'boss') ctx.fillStyle = '#bd93f9';
                else if (b.owner === 'enemy') ctx.fillStyle = '#ff5555';
                else ctx.fillStyle = (b.owner === myId) ? '#f1fa8c' : '#8be9fd';
            }
            let size = b.s || 4;
            ctx.arc(b.x, b.y, size, 0, Math.PI*2);
            ctx.fill();
        }
    });

    // 6. 警告閃爍
    if (gameState.w) {
        ctx.save();
        const alpha = 0.2 + 0.15 * Math.sin(time * 0.01);
        ctx.fillStyle = `rgba(255, 0, 0, ${alpha})`;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        const scanY = (time * 0.2) % canvas.height;
        ctx.strokeStyle = "rgba(255, 50, 50, 0.5)";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(0, scanY); ctx.lineTo(canvas.width, scanY);
        ctx.moveTo(0, canvas.height - scanY); ctx.lineTo(canvas.width, canvas.height - scanY);
        ctx.stroke();
        if (Math.floor(time / 250) % 2 === 0) {
            ctx.translate(canvas.width/2, canvas.height/2);
            ctx.font = "bold 40px Courier New";
            ctx.fillStyle = "#ff5555";
            ctx.textAlign = "center";
            ctx.shadowColor = "red"; ctx.shadowBlur = 20;
            ctx.fillText("⚠ WARNING ⚠", 0, -20);
            ctx.font = "bold 20px Courier New";
            ctx.fillStyle = "#fff";
            ctx.fillText("BOSS APPROACHING", 0, 20);
        }
        ctx.restore();
    }
}
