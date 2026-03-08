"""
styles.py  — CSS, background image, brand header, WhatsApp button (root-level)
"""
import base64, os
import streamlit as st
from pathlib import Path

WHATSAPP_NUMBER = "923001234567"   # ← Replace with your real number (no + sign)


def _bg_b64() -> str:
    for p in ["background.jpg", "background.png"]:
        if Path(p).exists():
            return base64.b64encode(Path(p).read_bytes()).decode()
    return ""


def inject_global_css(accent: str = "#6c63ff", opacity: float = 0.18):
    b64 = _bg_b64()
    bg_css = f"""
        body::before {{
            content: '';
            position: fixed;
            inset: 0;
            background: url('data:image/jpeg;base64,{b64}') center/cover no-repeat;
            opacity: {opacity};
            z-index: -1;
            pointer-events: none;
        }}""" if b64 else ""

    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@300;400;500&display=swap');

:root {{
    --bg:      #080810;
    --surface: #0f0f1a;
    --card:    #141422;
    --border:  #252538;
    --accent:  {accent};
    --accent2: #ff6584;
    --green:   #43e97b;
    --text:    #eaeaf5;
    --muted:   #65658a;
}}
html, body, [data-testid="stAppViewContainer"] {{
    background: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'DM Mono', monospace !important;
}}
{bg_css}
[data-testid="stSidebar"] {{
    background: rgba(15,15,26,0.95) !important;
    border-right: 1px solid var(--border) !important;
    backdrop-filter: blur(12px);
}}
[data-testid="stSidebar"] * {{ color: var(--text) !important; }}
h1,h2,h3,h4 {{ font-family: 'Syne', sans-serif !important; }}
.hub-card {{
    background: rgba(20,20,34,0.82);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1rem;
    backdrop-filter: blur(8px);
}}
.grad-text {{
    background: linear-gradient(90deg, {accent}, #ff6584);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}}
.stButton > button {{
    background: var(--accent) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    letter-spacing: 0.05em !important;
    transition: all .2s !important;
}}
.stButton > button:hover {{
    filter: brightness(1.15) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 24px rgba(108,99,255,.4) !important;
}}
[data-testid="stTextInput"] input, textarea {{
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text) !important;
    font-family: 'DM Mono', monospace !important;
}}
[data-testid="stTextInput"] input:focus {{
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px rgba(108,99,255,.2) !important;
}}
[data-testid="stMetric"] {{
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    padding: 1rem !important;
}}
[data-testid="stAlert"] {{ border-radius: 8px !important; }}
[data-testid="stExpander"] {{
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
}}
[data-testid="stFileUploader"] {{
    background: var(--card) !important;
    border: 2px dashed var(--border) !important;
    border-radius: 12px !important;
}}
hr {{ border-color: var(--border) !important; }}
::-webkit-scrollbar {{ width: 5px; }}
::-webkit-scrollbar-track {{ background: var(--bg); }}
::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 4px; }}
.wa-btn {{
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: #25d366;
    color: #fff !important;
    text-decoration: none !important;
    padding: 0.5rem 1.1rem;
    border-radius: 8px;
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    font-size: 0.85rem;
    letter-spacing: 0.04em;
    transition: all .2s;
}}
.wa-btn:hover {{ filter: brightness(1.1); transform: translateY(-1px); }}
.avatar {{
    width: 38px; height: 38px;
    border-radius: 50%;
    border: 2px solid var(--accent);
    object-fit: cover;
}}
.badge-green {{ background:#43e97b22; color:#43e97b; border:1px solid #43e97b55; padding:2px 10px; border-radius:20px; font-size:0.75rem; }}
.badge-red   {{ background:#ff658422; color:#ff6584; border:1px solid #ff658455; padding:2px 10px; border-radius:20px; font-size:0.75rem; }}
.badge-yellow{{ background:#ffd70022; color:#ffd700; border:1px solid #ffd70055; padding:2px 10px; border-radius:20px; font-size:0.75rem; }}
</style>
""", unsafe_allow_html=True)


def whatsapp_button(label: str = "💬 Support / Contact Admin",
                    pre_msg: str = "Hello, I need help with Hussain Automation Hub."):
    url = f"https://wa.me/{WHATSAPP_NUMBER}?text={pre_msg.replace(' ', '%20')}"
    st.markdown(f'<a class="wa-btn" href="{url}" target="_blank">🟢 {label}</a>',
                unsafe_allow_html=True)


def brand_header(subtitle: str = ""):
    st.markdown(f"""
    <div style='padding:1.6rem 0 0.6rem;'>
      <div style='font-family:Syne,sans-serif;font-size:2rem;font-weight:800;line-height:1.1;'>
        <span class='grad-text'>Hussain</span>
        <span style='color:#eaeaf5;'> Automation Hub</span>
        <span style='font-size:1rem;margin-left:6px;'>⚡</span>
      </div>
      <div style='color:var(--muted);font-size:0.75rem;letter-spacing:0.12em;margin-top:4px;'>
        {subtitle}
      </div>
    </div>
    """, unsafe_allow_html=True)
