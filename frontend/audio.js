class AudioManager {
    constructor() {
        this.sounds = {};
        this.bgm = null;
        this.enabled = true;
    }

    loadSound(name, url) {
        this.sounds[name] = new Audio(url);
        this.sounds[name].volume = VOL_SFX;
    }

    play(name) {
        if (!this.enabled || !this.sounds[name]) return;
        const sound = this.sounds[name].cloneNode(); // 允許重疊播放
        sound.volume = VOL_SFX;
        sound.play().catch(e => console.log("Audio play failed", e));
    }

    playBGM(url) {
        if (!this.enabled) return;
        if (this.bgm) this.bgm.pause();
        this.bgm = new Audio(url);
        this.bgm.volume = VOL_BGM;
        this.bgm.loop = true;
        this.bgm.play().catch(e => console.log("BGM play failed", e));
    }
}

const audio = new AudioManager();
// 預載基本音效 (可根據你的 repo 實際檔案名稱調整)
// audio.loadSound('shoot', SOUNDS_BASE + 'shoot.mp3');
// audio.loadSound('hit', SOUNDS_BASE + 'hit.mp3');
