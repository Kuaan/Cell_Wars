# v4.2.0 app.py (Refactored)
import streamlit as st
import streamlit.components.v1 as components
import os
import client_config as cfg  # 匯入設定檔

st.set_page_config(page_title="Cell Wars V5.1", layout="wide")

# 隱藏 Streamlit 預設介面
st.markdown("""
    <style>
    [data-testid="stHeader"] {display: none;}
    .stApp {background-color: #0d0211; margin: 0; padding: 0;}
    iframe {display: block;} 
    </style>
""", unsafe_allow_html=True)

def load_file(filename):
    """讀取 frontend 資料夾下的檔案內容"""
    file_path = os.path.join("frontend", filename)
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

# 1. 讀取各個部分的程式碼
html_template = load_file("index.html")
css_code = load_file("style.css")
audio_logic = load_file("audio.js")
drawing_logic = load_file("drawing.js")
main_logic = load_file("main.js")

# 2. 進行變數替換 (Injection)
# 我們把 Python 的變數塞進 HTML/JS 字串中
rendered_html = html_template.format(
    style=css_code,
    audio_js=audio_logic,
    drawing_js=drawing_logic,
    main_js=main_logic,
    server_url=cfg.SERVER_URL,
    assets_base=cfg.ASSETS_BASE,
    sounds_base=cfg.SOUNDS_BASE,
    vol_bgm=cfg.DEFAULT_VOL_BGM,
    vol_sfx=cfg.DEFAULT_VOL_SFX
)

# 3. 渲染
components.html(rendered_html, height=800)
