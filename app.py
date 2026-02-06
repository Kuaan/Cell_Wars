# v4.2.0 app.py (Modular Refactor)
import streamlit as st
import streamlit.components.v1 as components
import os
import client_config as cfg  # 匯入我們剛寫的設定檔

st.set_page_config(page_title="Cell Wars V5.1", layout="wide")

# 隱藏 Streamlit 原生介面 (保留在 Python 端處理)
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

# 1. 讀取各檔案內容
html_template = load_file("index.html")
css_code = load_file("style.css")
audio_logic = load_file("audio.js")
drawing_logic = load_file("drawing.js")
main_logic = load_file("main.js")

# 2. 變數替換 (Injection)
# 使用 replace 而不是 format，避免與 JS 內的 { } 衝突
rendered_html = html_template
rendered_html = rendered_html.replace("{style}", css_code)
rendered_html = rendered_html.replace("{audio_js}", audio_logic)
rendered_html = rendered_html.replace("{drawing_js}", drawing_logic)
rendered_html = rendered_html.replace("{main_js}", main_logic)
rendered_html = rendered_html.replace("{server_url}", cfg.SERVER_URL)
rendered_html = rendered_html.replace("{assets_base}", cfg.ASSETS_BASE)
rendered_html = rendered_html.replace("{sounds_base}", cfg.SOUNDS_BASE)
rendered_html = rendered_html.replace("{vol_bgm}", str(cfg.DEFAULT_VOL_BGM))
rendered_html = rendered_html.replace("{vol_sfx}", str(cfg.DEFAULT_VOL_SFX))

# 3. 渲染
components.html(rendered_html, height=800)
