class AudioController {
    constructor() {
        this.ctx = new (window.AudioContext || window.webkitAudioContext)();
        this.masterGain = this.ctx.createGain();
        this.masterGain.connect(this.ctx.destination);
        this.bgmGain = this.ctx.createGain();
        this.sfxGain = this.ctx.createGain();
        
        this.bgmGain.connect(this.masterGain);
        this.sfxGain.connect(this.masterGain);
        
        this.setBgmVolume(0.5);
        this.setSfxVolume(0.5);
        this.enabled = false;
    }

    enable() {
        if (this.ctx.state === 'suspended') {
            this.ctx.resume();
        }
        this.enabled = true;
    }

    setBgmVolume(val) { this.bgmGain.gain.value = val; }
    setSfxVolume(val) { this.sfxGain.gain.value = val; }

    // 播放音調 (頻率, 類型, 持續時間)
    playTone(freq, type, duration, time = 0) {
        if (!this.enabled) return;
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        
        osc.type = type;
        osc.frequency.setValueAtTime(freq, this.ctx.currentTime + time);
        
        gain.gain.setValueAtTime(this.sfxGain.gain.value, this.ctx.currentTime + time);
        gain.gain.exponentialRampToValueAtTime(0.01, this.ctx.currentTime + time + duration);
        
        osc.connect(gain);
        gain.connect(this.masterGain);
        
        osc.start(this.ctx.currentTime + time);
        osc.stop(this.ctx.currentTime + time + duration);
    }

    play(type) {
        switch (type) {
            case 'shoot':
                this.playTone(400, 'square', 0.1);
                this.playTone(200, 'sawtooth', 0.1, 0.05);
                break;
            case 'enemy_hitted':
                this.playTone(100, 'sawtooth', 0.1);
                break;
            case 'character_hitted':
                this.playTone(150, 'square', 0.3);
                this.playTone(100, 'square', 0.3, 0.1);
                break;
            case 'boss_shot':
                this.playTone(80, 'sawtooth', 0.3);
                break;
            case 'powerup':
                this.playTone(600, 'sine', 0.1);
                this.playTone(1200, 'sine', 0.2, 0.1);
                break;
            case 'boss_coming':
                this.playTone(50, 'sawtooth', 1.0);
                this.playTone(40, 'sawtooth', 1.0, 0.5);
                break;
            case 'win':
                this.playTone(400, 'square', 0.2);
                this.playTone(600, 'square', 0.2, 0.2);
                this.playTone(800, 'square', 0.4, 0.4);
                break;
        }
    }
}
