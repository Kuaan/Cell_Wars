// frontend/audio.js
const AudioContext = window.AudioContext || window.webkitAudioContext;
const audioCtx = new AudioContext();

const gainNodeBGM = audioCtx.createGain();
const gainNodeSFX = audioCtx.createGain();
gainNodeBGM.connect(audioCtx.destination);
gainNodeSFX.connect(audioCtx.destination);

const audioBuffers = {};
const bgmSourceNode = { current: null };

// 初始音量由 HTML 注入的變數決定
let volBGM = parseFloat(document.getElementById('vol-bgm').value);
let volSFX = parseFloat(document.getElementById('vol-sfx').value);
gainNodeBGM.gain.value = volBGM;
gainNodeSFX.gain.value = volSFX;

// SOUNDS_BASE 是全域變數
const soundList = {
    bgm: SOUNDS_BASE + "bgm/bgm-145a.wav",
    p_hit: SOUNDS_BASE + "characters/character_hitted.wav",
    p_shot: SOUNDS_BASE + "characters/character_nor_shot.wav",
    boss_come: SOUNDS_BASE + "enemy/boss_coming.wav",
    boss_hit: SOUNDS_BASE + "enemy/boss_hitted.wav",
    boss_shot: SOUNDS_BASE + "enemy/boss_shot.wav",
    e_hit: SOUNDS_BASE + "enemy/enemy_hitted.wav",
    e_shot: SOUNDS_BASE + "enemy/enemy_nor_shot.wav",
    skill: SOUNDS_BASE + "skill/slime.wav",
    powerup: SOUNDS_BASE + "skill/slime.wav" 
};

async function loadSound(key, url) {
    try {
        const response = await fetch(url);
        const arrayBuffer = await response.arrayBuffer();
        const decodedBuffer = await audioCtx.decodeAudioData(arrayBuffer);
        audioBuffers[key] = decodedBuffer;
    } catch(e) { console.error(`Error loading ${key}:`, e); }
}

// 載入所有音效
Promise.all(Object.keys(soundList).map(key => loadSound(key, soundList[key]))).then(() => {
    const btn = document.getElementById('start-btn');
    btn.innerText = "進入戰場";
    btn.disabled = false;
});

function playSfx(key) {
    if (volSFX <= 0.01 || !audioBuffers[key]) return;
    const source = audioCtx.createBufferSource();
    source.buffer = audioBuffers[key];
    source.connect(gainNodeSFX);
    source.start(0);
}

function playBGM() {
    if (!audioBuffers['bgm']) return;
    if (bgmSourceNode.current) { try { bgmSourceNode.current.stop(); } catch(e) {} }
    const source = audioCtx.createBufferSource();
    source.buffer = audioBuffers['bgm'];
    source.loop = true;
    source.connect(gainNodeBGM);
    source.start(0);
    bgmSourceNode.current = source;
}

document.getElementById('vol-bgm').oninput = function() {
    volBGM = parseFloat(this.value);
    gainNodeBGM.gain.setTargetAtTime(volBGM, audioCtx.currentTime, 0.1);
    if (volBGM > 0 && audioCtx.state === 'suspended') audioCtx.resume();
};
document.getElementById('vol-sfx').oninput = function() {
    volSFX = parseFloat(this.value);
    gainNodeSFX.gain.setTargetAtTime(volSFX, audioCtx.currentTime, 0.1);
};
