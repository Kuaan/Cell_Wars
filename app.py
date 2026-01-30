#v3.6.2 app.py
import streamlit as st
import streamlit.components.v1 as components
import json
import time

# --- 1. 初始化 Session State (確保設定不會因為刷新而重置) ---
if 'bgm_on' not in st.session_state:
    st.session_state.bgm_on = True
if 'sfx_on' not in st.session_state:
    st.session_state.sfx_on = True
if 'volume' not in st.session_state:
    st.session_state.volume = 0.5
if 'sfx_queue' not in st.session_state:
    st.session_state.sfx_queue = [] # 用來存儲需要播放的音效列表

# --- 2. 側邊欄控制項 (UI) ---
with st.sidebar:
    st.header("🔊 音效設定")
    
    # 使用 checkbox 直接綁定 session_state
    st.session_state.bgm_on = st.checkbox("開啟背景音樂 (BGM)", value=st.session_state.bgm_on)
    st.session_state.sfx_on = st.checkbox("開啟音效 (SFX)", value=st.session_state.sfx_on)
    
    # 音量滑桿
    st.session_state.volume = st.slider("音量大小", 0.0, 1.0, st.session_state.volume, 0.1)

# --- 3. 遊戲邏輯模擬 (Python 端) ---
# 假設這是你的遊戲主迴圈或事件觸發點
def trigger_explosion():
    # 只有當 SFX 開啟時，才將音效加入隊列
    if st.session_state.sfx_on:
        # 為了避免重複播放導致的問題，我們可以加入一個時間戳記或唯一ID
        st.session_state.sfx_queue.append({"name": "explosion", "id": time.time()})

st.title("Cell Wars Audio Test")
if st.button("💥 觸發爆炸 (測試 SFX)"):
    trigger_explosion()

# --- 4. 核心：JavaScript 音訊管理器 (嵌入 HTML) ---
# 我們將 Python 的狀態轉成 JSON 傳給 JS
js_data = json.dumps({
    "bgm_on": st.session_state.bgm_on,
    "sfx_on": st.session_state.sfx_on,
    "volume": st.session_state.volume,
    "sfx_queue": st.session_state.sfx_queue
})

# 清空 Python 端的佇列，避免下次刷新時重複播放 (這步很重要！)
# 注意：在 Streamlit 中清空狀態要在 component 渲染之後或透過 callback，
# 這裡為了簡化，我們依賴 JS 判斷 ID 是否已播放，或者由 Python 下次運行時覆蓋。
# 更嚴謹的做法是 Python 端只保留最近 1 秒內的音效。

html_code = f"""
<!DOCTYPE html>
<html>
<body>
    <audio id="bgm_player" loop>
        <source src="https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3" type="audio/mpeg">
    </audio>
    
    <audio id="sfx_explosion" src="https://www.myinstants.com/media/sounds/vine-boom.mp3"></audio>

    <script>
        // 接收 Python 傳來的資料
        var data = {js_data};
        
        var bgm = document.getElementById("bgm_player");
        var explosion = document.getElementById("sfx_explosion");
        
        // --- 設定音量 ---
        bgm.volume = data.volume;
        explosion.volume = data.volume;
        
        // --- BGM 邏輯 ---
        if (data.bgm_on) {{
            // 瀏覽器政策通常要求使用者與頁面互動後才能自動播放
            // Streamlit 每次刷新都是新的互動，所以通常由 play() 的 Promise 處理
            var playPromise = bgm.play();
            if (playPromise !== undefined) {{
                playPromise.then(_ => {{
                    // Automatic playback started!
                }}).catch(error => {{
                    // Auto-play was prevented
                    console.log("Audio autoplay prevented");
                }});
            }}
        }} else {{
            bgm.pause();
            bgm.currentTime = 0; // 可選：重置進度
        }}
        
        // --- SFX 邏輯 ---
        // 檢查佇列中有沒有需要播放的音效
        if (data.sfx_on && data.sfx_queue.length > 0) {{
            data.sfx_queue.forEach(sound => {{
                if (sound.name === "explosion") {{
                    // 複製節點可以允許多個爆炸聲重疊播放 (Overlapping)
                    var soundClone = explosion.cloneNode();
                    soundClone.volume = data.volume; 
                    soundClone.play();
                }}
            }});
        }}
    </script>
</body>
</html>
"""

# 將這個 HTML 區塊渲染出來，height=0 讓它隱藏起來
components.html(html_code, height=0)

# 渲染完後清空 Python 佇列，以免下次 Rerun 又播一次
# (在 Streamlit 這種 stateless 環境，比較簡單的做法是直接清空)
if st.session_state.sfx_queue:
    st.session_state.sfx_queue = []
