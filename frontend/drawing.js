// frontend/drawing.js v5.3
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

    // 3. 繪製敵人
    for (let id in gameState.enemies) {
        let e = gameState.enemies[id];
        if (e.type === 999) {
            if(skins.boss.complete) ctx.drawImage(skins.boss, e.x, e.y, e.size, e.size);
            const hpRatio = Math.max(0, e.hp / e.max_hp);
            ctx.fillStyle = "#bd93f9"; ctx.fillRect(e.x, e.y-10, e.size * hpRatio, 8);
        } else {
            let img = skins.viruses[(e.type || 1) - 1];
            if(img && img.complete) ctx.drawImage(img, e.x, e.y, e.size, e.size);
            const hpRatio = Math.max(0, e.hp / e.max_hp);
            ctx.fillStyle = "#ff5555"; ctx.fillRect(e.x, e.y-6, e.size * hpRatio, 3);
        }
    }

    // 4. 繪製玩家
    for (let id in gameState.players) {
        let p = gameState.players[id];
        // --- 雷射特效邏輯 ---
        
        if (p.l_st === 1) { // 蓄力中 (1秒)
            let progress = (time - p.l_t) / 1000; // 0.0 ~ 1.0
            if (progress < 1.0) {
                ctx.save();
                ctx.translate(p.x + 15, p.y + 15);
                // 匯聚線條
                for(let i=0; i<6; i++) {
                    ctx.beginPath();
                    let angle = (time * 0.01) + (i * 60 * Math.PI/180);
                    let dist = 40 * (1 - progress);
                    ctx.arc(Math.cos(angle)*dist, Math.sin(angle)*dist, 3, 0, Math.PI*2);
                    ctx.fillStyle = `rgba(255, 184, 108, ${0.5 + progress*0.5})`;
                    ctx.fill();
                }
                // 核心光球變大
                ctx.beginPath();
                ctx.arc(0, 0, 5 + 10 * progress, 0, Math.PI*2);
                ctx.fillStyle = "#ffb86c";
                ctx.fill();
                ctx.restore();
            }
        } else if (p.l_st === 2) { // 發射中 (雷射光束)
             ctx.save();
             ctx.translate(p.x + 15, p.y + 15);
             ctx.rotate(p.l_a * Math.PI / 180); 
             
             // 光束外發光
             ctx.beginPath();
             ctx.moveTo(0, 0);
             ctx.lineTo(800, 0); 
             ctx.lineWidth = 15;
             ctx.strokeStyle = "rgba(255, 100, 100, 0.4)";
             ctx.stroke();
             
             // 光束核心
             ctx.beginPath();
             ctx.moveTo(0, 0);
             ctx.lineTo(800, 0);
             ctx.lineWidth = 5;
             ctx.strokeStyle = "#ffffff";
             ctx.shadowColor = "#ff5555";
             ctx.shadowBlur = 20;
             ctx.stroke();
             
             ctx.restore();
        }
        
        // 繪製護盾
        if (p.shield) {
            ctx.save();
            ctx.beginPath();
            ctx.arc(p.x + 15, p.y + 15, 35, 0, Math.PI * 2); 
            ctx.strokeStyle = `rgba(100, 200, 255, ${0.5 + 0.3 * Math.sin(time * 0.01)})`; 
            ctx.lineWidth = 3;
            ctx.stroke();
            ctx.fillStyle = `rgba(100, 200, 255, 0.1)`;
            ctx.fill();
            
            // 護盾旋轉光環
            ctx.translate(p.x + 15, p.y + 15);
            ctx.rotate(time * 0.005);
            ctx.beginPath();
            ctx.arc(0, 0, 38, 0, Math.PI * 1.5); 
            ctx.strokeStyle = "rgba(200, 255, 255, 0.6)";
            ctx.lineWidth = 2;
            ctx.stroke();
            ctx.restore();
        }

        // 受傷閃爍
        if (p.invincible && !p.shield) ctx.globalAlpha = 0.5;
        
        let img = skins.cells[(p.skin || 1) - 1];
        if(img && img.complete) ctx.drawImage(img, p.x, p.y, 30, 30);
        
        ctx.globalAlpha = 1.0;
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
        if (b.c === '#ff00ff' || b.c==='#aa00aa' || b.c === 'rgb(255, 0, 255)') {
            ctx.save();
            ctx.translate(b.x, b.y);
            ctx.rotate(time * 0.005); 
            
            let scale = 1 + Math.sin(time * 0.01) * 0.1; 
            ctx.scale(scale, scale);
            
            ctx.font = "30px sans-serif";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText("🫧", 0, 0);
            
            ctx.restore();
        } else {
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
