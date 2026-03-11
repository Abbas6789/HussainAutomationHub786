"""
app.py — SocioSaas Pro | Public Portal
Developer: Ghulam Hussain

WHAT CHANGED vs previous version
──────────────────────────────────
• Video data (titles, URLs, comments) is now fetched from Google Sheets
  instead of Firebase / SQLite.
• User comments are written back to Google Sheets.
• All other UI elements, login, device-locking, sidebar, subscriptions,
  social-connect tab, and WhatsApp contact are UNCHANGED.
• Uses st.connection("gsheets") — zero JSON files needed on GitHub.

Run:  streamlit run app.py
"""

import streamlit as st
import sqlite3
import hashlib
import uuid
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
import firebase_utils as fb

# ─── CONSTANTS ────────────────────────────────────────────────────────────────
ADMIN_EMAIL    = "hklhhklh5@gmail.com"
ADMIN_PASSWORD = "Ghse45*#"
DEVELOPER_NAME = "Ghulam Hussain"
DB_PATH        = "sociosaas.db"
APP_TITLE      = "SocioSaas Pro"

# Google Sheets spreadsheet ID (from the URL you provided)
SHEET_ID       = "1cWzMMmuJsmYCy9L-GOyAbwSzAmAe7zD9v4a3yUdPJOA"

# Column names in your Google Sheet — change these if your headers differ
COL_TITLE    = "Video_Title"
COL_URL      = "Video_URL"
COL_COMMENTS = "User_Comments"

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=f"{APP_TITLE} | {DEVELOPER_NAME}",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ══════════════════════════════════════════════════════════════════════════════
#  GOOGLE SHEETS  — fetch & save  (ONLY section that changed)
# ══════════════════════════════════════════════════════════════════════════════

def _get_gsheets_conn():
    """
    Returns the Google Sheets connection using st.connection("gsheets").
    Credentials come entirely from Streamlit Secrets — no JSON file uploaded.
    """
    return st.connection("gsheets", type="GSheetsConnection")


@st.cache_data(ttl=60)
def fetch_videos_from_sheet() -> list[dict]:
    """
    Reads all rows from the Google Sheet and returns a list of dicts:
        [{"Video_Title": "...", "Video_URL": "...", "User_Comments": "..."}, ...]

    Results are cached for 60 seconds so repeated renders don't call the API.
    Call st.cache_data.clear() after a comment write to refresh instantly.
    """
    try:
        conn = _get_gsheets_conn()
        df: pd.DataFrame = conn.read(
            spreadsheet=SHEET_ID,
            usecols=[COL_TITLE, COL_URL, COL_COMMENTS],
            ttl=60,
        )
        # Drop rows where Video_Title is empty
        df = df.dropna(subset=[COL_TITLE])
        df = df.fillna("")          # replace NaN with empty string
        return df.to_dict("records")
    except Exception as e:
        st.warning(f"⚠️ Could not load videos from Google Sheets: {e}")
        return []


def save_comment_to_sheet(video_title: str, comment: str) -> bool:
    """
    Appends a new row to the Google Sheet with the user's comment.
    Leaves Video_URL blank on comment rows (they are comment-only records).

    Returns True on success, False on failure.
    """
    try:
        conn = _get_gsheets_conn()

        # Read existing data first (required by gsheets connector for updates)
        df: pd.DataFrame = conn.read(
            spreadsheet=SHEET_ID,
            ttl=0,          # bypass cache so we get the freshest data
        )

        # Build the new row
        new_row = pd.DataFrame([{
            COL_TITLE:    video_title,
            COL_URL:      "",
            COL_COMMENTS: comment,
        }])

        updated_df = pd.concat([df, new_row], ignore_index=True)

        conn.update(
            spreadsheet=SHEET_ID,
            data=updated_df,
        )

        # Clear the read cache so the next fetch picks up the new comment
        fetch_videos_from_sheet.clear()
        return True

    except Exception as e:
        st.error(f"❌ Could not save comment: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════════
#  SQLITE  — users, auth, device-locking  (UNCHANGED)
# ══════════════════════════════════════════════════════════════════════════════

def get_db():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_db(); c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL, password TEXT NOT NULL,
        name TEXT NOT NULL, status TEXT DEFAULT 'pending',
        plan TEXT DEFAULT 'free', device_id TEXT,
        created_at TEXT, last_login TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS notice (
        id INTEGER PRIMARY KEY, message TEXT DEFAULT ''
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS social_connections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, platform TEXT, connected_at TEXT, account_name TEXT
    )''')
    c.execute("INSERT OR IGNORE INTO notice (id,message) VALUES (1,'🎉 Welcome to SocioSaas Pro!')")
    conn.commit(); conn.close()

def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

def generate_device_id():
    if "device_id" not in st.session_state:
        st.session_state.device_id = hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()
    return st.session_state.device_id

def register_user(email, password, name):
    conn = get_db(); c = conn.cursor()
    try:
        c.execute("INSERT INTO users (email,password,name,created_at) VALUES (?,?,?,?)",
                  (email, hash_password(password), name, datetime.now().isoformat()))
        conn.commit()
        return True, "Registration successful! Await admin approval."
    except sqlite3.IntegrityError:
        return False, "Email already registered."
    finally:
        conn.close()

def login_user(email, password, device_id):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email=? AND password=?",
              (email, hash_password(password)))
    user = c.fetchone()
    if not user:
        conn.close()
        return None, "Invalid email or password."
    cols = [d[0] for d in c.description]
    u = dict(zip(cols, user))
    if u['status'] == 'pending':
        conn.close(); return None, "⏳ Your account is pending admin approval."
    if u['status'] == 'blocked':
        conn.close(); return None, "🚫 Your account has been blocked. Contact developer."
    if u['device_id'] and u['device_id'] != device_id:
        conn.close(); return None, "🔒 Device mismatch! Contact admin to reset."
    if not u['device_id']:
        c.execute("UPDATE users SET device_id=?,last_login=? WHERE id=?",
                  (device_id, datetime.now().isoformat(), u['id']))
    else:
        c.execute("UPDATE users SET last_login=? WHERE id=?",
                  (datetime.now().isoformat(), u['id']))
    conn.commit(); conn.close()
    return u, None


# ══════════════════════════════════════════════════════════════════════════════
#  FIREBASE REMOTE CONFIG helpers  (UNCHANGED)
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=60)
def get_cached_remote():
    return fb.get_remote_config()

@st.cache_data(ttl=30)
def get_cached_notice():
    result = fb.get_notice_board()
    if result:
        return result
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT message FROM notice WHERE id=1")
    row = c.fetchone(); conn.close()
    return row[0] if row else ""

def get_whatsapp_number():
    return get_cached_remote().get("support_whatsapp", "923461785207")

def get_premium_price():
    return get_cached_remote().get("premium_price", "$19")

def get_free_limit():
    return int(get_cached_remote().get("free_upload_limit", 3))


# ══════════════════════════════════════════════════════════════════════════════
#  CSS  (UNCHANGED)
# ══════════════════════════════════════════════════════════════════════════════

def inject_css(is_dashboard=False):
    watermark = ""
    if is_dashboard and Path("hussain.jpg").exists():
        watermark = """
        .main .block-container::before {
            content:''; position:fixed; top:50%; left:55%;
            transform:translate(-50%,-50%); width:420px; height:420px;
            background-image:url('/app/static/hussain.jpg');
            background-size:contain; background-repeat:no-repeat;
            background-position:center; opacity:0.04;
            pointer-events:none; z-index:0;
        }
        """
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');
    :root {{
        --primary:#6C63FF; --primary-dark:#4A43CC; --accent:#FF6584;
        --success:#43D9AD; --warning:#FFB547; --bg-dark:#0D0F1A;
        --bg-card:#161929; --bg-card2:#1E2235;
        --text-main:#E8EAFF; --text-muted:#8B8FA8; --border:#2A2D45;
    }}
    html,body,.stApp {{ background:var(--bg-dark)!important; font-family:'DM Sans',sans-serif; color:var(--text-main); }}
    h1,h2,h3 {{ font-family:'Syne',sans-serif; color:var(--text-main); }}
    section[data-testid="stSidebar"] {{ background:linear-gradient(180deg,#10132A 0%,#0D0F1A 100%)!important; border-right:1px solid var(--border); }}
    section[data-testid="stSidebar"] * {{ color:var(--text-main)!important; }}
    .stTextInput>div>div>input,.stPasswordInput>div>div>input {{
        background:var(--bg-card2)!important; border:1px solid var(--border)!important;
        color:var(--text-main)!important; border-radius:10px!important;
    }}
    .stTextInput>div>div>input:focus {{ border-color:var(--primary)!important; box-shadow:0 0 0 2px rgba(108,99,255,0.25)!important; }}
    .stButton>button {{
        background:linear-gradient(135deg,var(--primary),var(--primary-dark))!important;
        color:white!important; border:none!important; border-radius:10px!important;
        padding:10px 24px!important; font-family:'Syne',sans-serif!important; font-weight:600!important; transition:all 0.2s!important;
    }}
    .stButton>button:hover {{ transform:translateY(-2px)!important; box-shadow:0 8px 20px rgba(108,99,255,0.4)!important; }}
    [data-testid="stMetric"] {{ background:var(--bg-card)!important; border:1px solid var(--border)!important; border-radius:14px!important; padding:16px!important; }}
    [data-testid="stMetricValue"] {{ color:var(--primary)!important; font-family:'Syne',sans-serif; }}
    .stTabs [data-baseweb="tab-list"] {{ background:var(--bg-card)!important; border-radius:12px!important; padding:4px!important; border:1px solid var(--border); }}
    .stTabs [data-baseweb="tab"] {{ color:var(--text-muted)!important; font-family:'Syne',sans-serif!important; font-weight:600!important; border-radius:8px!important; }}
    .stTabs [aria-selected="true"] {{ background:var(--primary)!important; color:white!important; }}
    .stAlert {{ border-radius:12px!important; border:none!important; }}
    .stSuccess {{ background:rgba(67,217,173,0.1)!important; border-left:3px solid var(--success)!important; }}
    .stError {{ background:rgba(255,101,132,0.1)!important; border-left:3px solid var(--accent)!important; }}
    .stWarning {{ background:rgba(255,181,71,0.1)!important; border-left:3px solid var(--warning)!important; }}
    .stInfo {{ background:rgba(108,99,255,0.1)!important; border-left:3px solid var(--primary)!important; }}
    hr {{ border-color:var(--border)!important; }}
    .gh-card {{ background:var(--bg-card); border:1px solid var(--border); border-radius:16px; padding:24px; margin:12px 0; position:relative; overflow:hidden; }}
    .gh-card::before {{ content:''; position:absolute; top:0; left:0; right:0; height:2px; background:linear-gradient(90deg,var(--primary),var(--accent)); }}
    .plan-card {{ background:var(--bg-card); border:1px solid var(--border); border-radius:20px; padding:32px 24px; text-align:center; transition:all 0.3s; position:relative; overflow:hidden; }}
    .plan-card.premium {{ border-color:var(--primary); background:linear-gradient(160deg,#1E2235,#16183A); }}
    .plan-card:hover {{ transform:translateY(-4px); box-shadow:0 16px 40px rgba(108,99,255,0.2); }}
    .plan-price {{ font-family:'Syne',sans-serif; font-size:42px; font-weight:800; color:var(--primary); }}
    .login-title {{ font-family:'Syne',sans-serif; font-size:42px; font-weight:800; background:linear-gradient(135deg,#6C63FF,#FF6584); -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; line-height:1.1; }}
    .dev-badge {{ display:inline-block; background:rgba(108,99,255,0.15); border:1px solid rgba(108,99,255,0.4); color:#A89CFF; padding:6px 16px; border-radius:100px; font-size:13px; margin:8px 0; }}
    .wa-button {{ display:inline-block; background:linear-gradient(135deg,#25D366,#128C7E); color:white!important; padding:10px 22px; border-radius:10px; text-decoration:none!important; font-family:'Syne',sans-serif; font-weight:600; font-size:14px; transition:all 0.2s; }}
    .wa-button:hover {{ box-shadow:0 6px 20px rgba(37,211,102,0.4); transform:translateY(-2px); }}
    .notice-banner {{ background:linear-gradient(135deg,rgba(108,99,255,0.15),rgba(255,101,132,0.1)); border:1px solid rgba(108,99,255,0.3); border-radius:12px; padding:14px 20px; margin-bottom:20px; font-size:14px; color:#C4BEFF; }}
    .maint-screen {{ text-align:center; padding:80px 20px; }}

    /* TikTok-style video card */
    .video-card {{
        background:var(--bg-card);
        border:1px solid var(--border);
        border-radius:18px;
        overflow:hidden;
        transition:transform 0.25s, box-shadow 0.25s;
        position:relative;
    }}
    .video-card:hover {{
        transform:translateY(-5px);
        box-shadow:0 20px 50px rgba(108,99,255,0.25);
    }}
    .video-card::before {{
        content:'';
        position:absolute; top:0; left:0; right:0;
        height:3px;
        background:linear-gradient(90deg,var(--primary),var(--accent));
    }}
    .video-thumb {{
        width:100%; aspect-ratio:9/16;
        background:linear-gradient(160deg,#1a1c2e,#0d0f1a);
        display:flex; align-items:center; justify-content:center;
        font-size:52px; cursor:pointer; position:relative;
        overflow:hidden;
    }}
    .video-thumb iframe {{
        width:100%; height:100%; border:none; position:absolute; inset:0;
    }}
    .video-meta {{ padding:14px 16px 10px; }}
    .video-title {{
        font-family:'Syne',sans-serif; font-weight:700;
        font-size:14px; color:var(--text-main);
        display:-webkit-box; -webkit-line-clamp:2;
        -webkit-box-orient:vertical; overflow:hidden;
        line-height:1.4; margin-bottom:8px;
    }}
    .video-comments {{
        border-top:1px solid var(--border);
        padding:10px 16px 14px;
    }}
    .comment-bubble {{
        background:var(--bg-card2);
        border-radius:10px;
        padding:8px 12px;
        margin:6px 0;
        font-size:12px;
        color:var(--text-muted);
        border-left:2px solid var(--primary);
    }}

    #MainMenu, footer {{ visibility:hidden; }}
    header[data-testid="stHeader"] {{ background:transparent; }}
    {watermark}
    </style>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  MAINTENANCE GATE  (UNCHANGED)
# ══════════════════════════════════════════════════════════════════════════════

def check_maintenance():
    try:
        maint = fb.get_maintenance_status()
        return maint.get("enabled", False), maint.get("message","🔧 Under Maintenance")
    except Exception:
        return False, ""


# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR  (UNCHANGED)
# ══════════════════════════════════════════════════════════════════════════════

def render_sidebar(user=None):
    wa = get_whatsapp_number()
    with st.sidebar:
        pic = Path("hussain.jpg")
        if pic.exists():
            st.image(str(pic), width=80)
        st.markdown(f"""
        <div style='margin:8px 0 16px;'>
            <div style='font-family:Syne,sans-serif;font-size:18px;font-weight:700;'>{DEVELOPER_NAME}</div>
            <div style='color:#8B8FA8;font-size:12px;margin-top:2px;'>Social Media Automation</div>
        </div>
        """, unsafe_allow_html=True)
        st.divider()
        if user and user != "admin":
            plan_color = "#43D9AD" if user.get('plan')=='premium' else "#FFB547"
            plan_label = "⭐ Premium" if user.get('plan')=='premium' else "🆓 Free Plan"
            st.markdown(f"""
            <div style='background:#1E2235;border-radius:10px;padding:12px;margin-bottom:16px;'>
                <div style='font-size:13px;color:#8B8FA8;'>Logged in as</div>
                <div style='font-weight:600;font-size:14px;margin-top:2px;'>{user.get('name','User')}</div>
                <div style='font-size:12px;color:{plan_color};margin-top:4px;'>{plan_label}</div>
            </div>
            """, unsafe_allow_html=True)
        st.divider()
        st.markdown(f"""
        <div style='text-align:center;padding:8px 0;'>
            <a href='https://wa.me/{wa}' target='_blank' class='wa-button'>💬 Contact Developer</a>
        </div>
        """, unsafe_allow_html=True)
        if user:
            st.divider()
            if st.button("🚪 Logout", use_container_width=True):
                for k in [k for k in st.session_state if k != 'device_id']:
                    del st.session_state[k]
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  LOGIN / REGISTER  (UNCHANGED)
# ══════════════════════════════════════════════════════════════════════════════

def render_auth_page():
    inject_css()
    render_sidebar()
    pic = Path("hussain.jpg")
    col1, col2, col3 = st.columns([1,1.2,1])
    with col2:
        if pic.exists():
            ca, cb, cc = st.columns([1,1,1])
            with cb: st.image(str(pic), width=90)
        st.markdown(f"""
        <div style='text-align:center;padding:20px 0 10px;'>
            <div class='login-title'>SocioSaas Pro</div>
            <div style='color:#8B8FA8;font-size:15px;margin:6px 0 4px;'>Automate. Grow. Dominate Social Media.</div>
            <span class='dev-badge'>by {DEVELOPER_NAME}</span>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        tab_l, tab_r = st.tabs(["🔐 Login", "📝 Register"])
        with tab_l:
            st.markdown("<div class='gh-card'>", unsafe_allow_html=True)
            email    = st.text_input("Email Address", placeholder="you@example.com", key="li_email")
            password = st.text_input("Password", type="password", placeholder="••••••••", key="li_pass")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🚀 Sign In", use_container_width=True, key="btn_li"):
                if email and password:
                    result, err = login_user(email, password, generate_device_id())
                    if result:
                        st.session_state.user = result
                        st.rerun()
                    else:
                        st.error(err)
                else:
                    st.warning("Please fill all fields.")
            st.markdown("</div>", unsafe_allow_html=True)
        with tab_r:
            st.markdown("<div class='gh-card'>", unsafe_allow_html=True)
            name      = st.text_input("Full Name",        placeholder="Your Name",      key="reg_name")
            reg_email = st.text_input("Email Address",    placeholder="you@example.com",key="reg_email")
            reg_pass  = st.text_input("Password",         type="password", placeholder="Min 6 characters", key="reg_pass")
            reg_pass2 = st.text_input("Confirm Password", type="password", placeholder="Repeat password",  key="reg_pass2")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("✨ Create Account", use_container_width=True, key="btn_reg"):
                if name and reg_email and reg_pass and reg_pass2:
                    if reg_pass != reg_pass2:
                        st.error("Passwords do not match.")
                    elif len(reg_pass) < 6:
                        st.error("Password must be at least 6 characters.")
                    else:
                        ok, msg = register_user(reg_email, reg_pass, name)
                        st.success(msg) if ok else st.error(msg)
                else:
                    st.warning("Please fill all fields.")
            st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  TikTok-style VIDEO FEED  (NEW — replaces old video queue display)
# ══════════════════════════════════════════════════════════════════════════════

def _make_embed_url(raw_url: str) -> str | None:
    """
    Converts a standard YouTube / TikTok share URL to an embeddable URL.
    Returns None if the URL cannot be converted.
    """
    if not raw_url:
        return None
    raw_url = raw_url.strip()

    # YouTube long form: https://www.youtube.com/watch?v=VIDEO_ID
    if "youtube.com/watch" in raw_url:
        try:
            vid = raw_url.split("v=")[1].split("&")[0]
            return f"https://www.youtube.com/embed/{vid}?autoplay=0&rel=0"
        except IndexError:
            pass

    # YouTube short form: https://youtu.be/VIDEO_ID
    if "youtu.be/" in raw_url:
        try:
            vid = raw_url.split("youtu.be/")[1].split("?")[0]
            return f"https://www.youtube.com/embed/{vid}?autoplay=0&rel=0"
        except IndexError:
            pass

    # TikTok video URL — direct link (embedding is restricted by TikTok)
    if "tiktok.com" in raw_url:
        return raw_url   # will open in new tab instead

    # Generic direct video file (.mp4 etc.)
    if raw_url.endswith((".mp4", ".webm", ".ogg")):
        return raw_url

    return None


def render_video_feed(videos: list[dict], user: dict):
    """
    Renders the TikTok-style vertical video feed.
    Each card shows: embedded player / thumbnail, title, and comments.
    """
    if not videos:
        st.markdown("""
        <div style='text-align:center;padding:60px 0;color:#8B8FA8;'>
            <div style='font-size:52px;'>🎬</div>
            <div style='font-family:Syne,sans-serif;font-size:20px;font-weight:700;margin:12px 0 6px;'>
                No Videos Yet
            </div>
            <div style='font-size:14px;'>
                Add rows to your Google Sheet and they will appear here.
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    # Render 2-column grid of video cards
    for i in range(0, len(videos), 2):
        cols = st.columns(2, gap="medium")
        for col_idx, video in enumerate(videos[i : i + 2]):
            with cols[col_idx]:
                title    = str(video.get(COL_TITLE, "Untitled"))
                raw_url  = str(video.get(COL_URL,   ""))
                comments = str(video.get(COL_COMMENTS, ""))
                embed    = _make_embed_url(raw_url)

                # ── Video card ───────────────────────────────────────────────
                st.markdown("<div class='video-card'>", unsafe_allow_html=True)

                # Thumbnail / player
                if embed and ("youtube.com/embed" in embed):
                    st.markdown(f"""
                    <div class='video-thumb' style='aspect-ratio:16/9;'>
                        <iframe src='{embed}' allowfullscreen
                            allow='accelerometer; autoplay; clipboard-write;
                                   encrypted-media; gyroscope; picture-in-picture'>
                        </iframe>
                    </div>
                    """, unsafe_allow_html=True)
                elif embed and embed.endswith((".mp4", ".webm", ".ogg")):
                    st.video(raw_url)
                elif raw_url:
                    # TikTok or unknown — show clickable thumbnail button
                    st.markdown(f"""
                    <div class='video-thumb'>
                        <a href='{raw_url}' target='_blank'
                           style='display:flex;flex-direction:column;align-items:center;
                                  justify-content:center;gap:10px;text-decoration:none;
                                  color:#E8EAFF;width:100%;height:100%;padding:20px;'>
                            <div style='font-size:48px;'>▶️</div>
                            <div style='font-size:12px;color:#8B8FA8;'>Tap to open</div>
                        </a>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div class='video-thumb'>
                        <span style='color:#8B8FA8;font-size:13px;'>No video URL</span>
                    </div>
                    """, unsafe_allow_html=True)

                # Title
                st.markdown(f"""
                <div class='video-meta'>
                    <div class='video-title'>{title}</div>
                </div>
                """, unsafe_allow_html=True)

                # Existing comments
                st.markdown("<div class='video-comments'>", unsafe_allow_html=True)
                if comments:
                    for line in comments.split("|"):
                        line = line.strip()
                        if line:
                            st.markdown(f"""
                            <div class='comment-bubble'>💬 {line}</div>
                            """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div style='font-size:12px;color:#8B8FA8;padding:4px 0;'>
                        No comments yet — be the first!
                    </div>
                    """, unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)  # close video-card

                # Comment input (outside the HTML block so Streamlit renders it)
                comment_key = f"comment_{i}_{col_idx}"
                new_comment = st.text_input(
                    "💬 Add a comment",
                    placeholder="Write something...",
                    key=comment_key,
                    label_visibility="collapsed"
                )
                if st.button("Post", key=f"post_{i}_{col_idx}", use_container_width=True):
                    if new_comment.strip():
                        ok = save_comment_to_sheet(title, new_comment.strip())
                        if ok:
                            st.success("✅ Comment posted!")
                            st.rerun()
                    else:
                        st.warning("Type something first.")

                st.markdown("<br>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  USER DASHBOARD  (Video tab replaced; all other tabs UNCHANGED)
# ══════════════════════════════════════════════════════════════════════════════

def render_dashboard(user: dict):
    inject_css(is_dashboard=True)
    render_sidebar(user)

    wa        = get_whatsapp_number()
    price     = get_premium_price()
    free_limit = get_free_limit()

    # Remote popup announcement
    remote = get_cached_remote()
    popup  = remote.get("popup_announcement", "")
    if popup:
        st.info(f"🎉 {popup}")

    # Notice board
    notice = get_cached_notice()
    if notice:
        st.markdown(f"<div class='notice-banner'>📢 {notice}</div>", unsafe_allow_html=True)

    st.markdown(f"""
    <div style='margin-bottom:24px;'>
        <h1 style='font-family:Syne,sans-serif;font-size:30px;font-weight:800;margin:0;'>
            👋 Welcome back, {user.get('name','User')}!
        </h1>
        <p style='color:#8B8FA8;margin:4px 0 0;'>Powered by {DEVELOPER_NAME} · SocioSaas Pro</p>
    </div>
    """, unsafe_allow_html=True)

    # Load videos once for the metrics row
    videos = fetch_videos_from_sheet()

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("🎬 Videos in Feed",  len(videos))
    with c2: st.metric("🔗 Platforms",       "3 Available")
    with c3: st.metric("📅 Member Since",    user.get('created_at','')[:10] if user.get('created_at') else 'N/A')
    with c4: st.metric("💎 Plan",            user.get('plan','free').upper())

    st.markdown("<br>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🎬 Video Feed", "🔗 Social Connect",
        "💎 Subscription", "💬 Contact Admin", "⚙️ Account"
    ])

    # ── Tab 1: TikTok-style Video Feed (NEW — powered by Google Sheets) ──────
    with tab1:
        st.markdown("### 🎬 Video Feed")
        col_refresh, col_info = st.columns([1, 4])
        with col_refresh:
            if st.button("🔄 Refresh", key="refresh_feed"):
                fetch_videos_from_sheet.clear()
                st.rerun()
        with col_info:
            st.caption(f"📊 {len(videos)} video(s) loaded from Google Sheets · auto-refreshes every 60s")

        render_video_feed(videos, user)

    # ── Tab 2: Social Connect (UNCHANGED) ────────────────────────────────────
    with tab2:
        st.markdown("### 🔗 Connect Your Social Media")
        social_creds = fb.get_social_credentials()

        has_yt = bool(social_creds.get("youtube", {}).get("api_key"))
        has_fb = bool(social_creds.get("facebook",{}).get("app_id"))
        has_tt = bool(social_creds.get("tiktok",  {}).get("client_key"))

        col1, col2, col3 = st.columns(3)
        for col, platform, icon, has_key, description in [
            (col1, "YouTube", "▶️", has_yt, "Upload videos, manage playlists & analytics"),
            (col2, "Facebook","📘", has_fb, "Post to pages, groups & manage ads"),
            (col3, "TikTok",  "🎵", has_tt, "Auto-post videos, trending hashtags"),
        ]:
            with col:
                status_color = "#43D9AD" if has_key else "#8B8FA8"
                status_label = "API Configured ✅" if has_key else "Not Configured"
                st.markdown(f"""
                <div class='gh-card' style='text-align:center;'>
                    <div style='font-size:40px;'>{icon}</div>
                    <div style='font-family:Syne,sans-serif;font-size:16px;font-weight:700;margin:8px 0;'>{platform}</div>
                    <div style='color:#8B8FA8;font-size:13px;margin-bottom:8px;'>{description}</div>
                    <div style='color:{status_color};font-size:12px;font-weight:600;'>{status_label}</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"Connect {platform}", key=f"connect_{platform}", use_container_width=True):
                    if has_key:
                        st.success(f"✅ {platform} credentials loaded! Full OAuth flow ready.")
                    else:
                        st.warning(f"⚠️ Admin hasn't configured {platform} API keys yet.")
        if not (has_yt or has_fb or has_tt):
            st.info("💡 Platform connections are managed by the admin. Once API keys are configured, connect buttons will be activated.")

    # ── Tab 3: Subscription (UNCHANGED) ──────────────────────────────────────
    with tab3:
        st.markdown("### 💎 Choose Your Plan")
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class='plan-card'>
                <div style='font-family:Syne,sans-serif;font-size:22px;font-weight:800;'>🆓 Free</div>
                <div class='plan-price'>$0</div>
                <div style='color:#8B8FA8;font-size:13px;margin-bottom:20px;'>per month</div>
                <hr style='border-color:#2A2D45;margin:16px 0;'>
                <div style='text-align:left;font-size:14px;line-height:2;'>
                    ✅ {free_limit} Video Uploads/month<br>
                    ✅ 1 Platform Connection<br>
                    ✅ Basic Hashtag Generator<br>
                    ❌ Auto-scheduling<br>
                    ❌ Analytics Dashboard<br>
                    ❌ Priority Support
                </div>
            </div>
            """, unsafe_allow_html=True)
            if user.get('plan') == 'free':
                st.markdown("<div style='text-align:center;padding:8px;color:#43D9AD;font-weight:600;'>✅ Current Plan</div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class='plan-card premium'>
                <div style='position:absolute;top:16px;right:16px;background:linear-gradient(135deg,#6C63FF,#FF6584);color:white;padding:4px 12px;border-radius:100px;font-size:11px;font-weight:700;'>POPULAR</div>
                <div style='font-family:Syne,sans-serif;font-size:22px;font-weight:800;'>⭐ Premium</div>
                <div class='plan-price'>{price}</div>
                <div style='color:#8B8FA8;font-size:13px;margin-bottom:20px;'>per month</div>
                <hr style='border-color:#2A2D45;margin:16px 0;'>
                <div style='text-align:left;font-size:14px;line-height:2;'>
                    ✅ Unlimited Video Uploads<br>
                    ✅ All 3 Platforms<br>
                    ✅ AI Title & Hashtag Generator<br>
                    ✅ Auto-scheduling<br>
                    ✅ Analytics Dashboard<br>
                    ✅ Priority WhatsApp Support
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            if user.get('plan') != 'premium':
                if st.button(f"🚀 Buy Now — {price}/mo", key="buy_premium", use_container_width=True):
                    st.markdown(f"""
                    <div style='background:rgba(108,99,255,0.1);border:1px solid rgba(108,99,255,0.3);border-radius:12px;padding:16px;margin-top:8px;'>
                        💬 <strong>Contact developer to upgrade:</strong><br>
                        <a href='https://wa.me/{wa}?text=Hi! I want to upgrade to Premium on SocioSaas Pro. Email: {user.get("email")}' target='_blank' class='wa-button' style='display:inline-block;margin-top:10px;'>📲 WhatsApp Us</a>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown("<div style='text-align:center;padding:8px;color:#43D9AD;font-weight:600;'>✅ Current Plan</div>", unsafe_allow_html=True)

    # ── Tab 4: Contact Admin (UNCHANGED) ─────────────────────────────────────
    with tab4:
        st.markdown("### 💬 Contact Admin / Support")
        col1, col2 = st.columns([1.2, 1])
        with col1:
            st.markdown("<div class='gh-card'>", unsafe_allow_html=True)
            st.markdown("#### Send a Message to Admin")
            st.write("Your message will appear in the Admin Panel for a direct response.")
            msg_text = st.text_area("Your Message", height=120, placeholder="Describe your issue...", key="contact_msg")
            if st.button("📤 Send Message", key="send_msg", use_container_width=True):
                if msg_text.strip():
                    ok = fb.push_whatsapp_message(user.get("email",""), user.get("name","User"), msg_text.strip())
                    st.success("✅ Message sent! Admin will reply shortly.") if ok else \
                    st.warning("⚠️ Could not reach Firebase. Try WhatsApp directly below.")
                else:
                    st.warning("Please type a message.")
            st.markdown("</div>", unsafe_allow_html=True)
        with col2:
            st.markdown("<div class='gh-card'>", unsafe_allow_html=True)
            st.markdown("#### 📲 Direct WhatsApp")
            st.write("For urgent support, reach the developer directly on WhatsApp.")
            st.markdown(f"""
            <div style='text-align:center;padding:16px 0;'>
                <div style='font-size:48px;'>💬</div>
                <a href='https://wa.me/{wa}?text=Hi! I need help. Account: {user.get("email","")}' target='_blank'
                   class='wa-button' style='display:inline-block;margin-top:12px;padding:14px 28px;'>
                    Open WhatsApp Chat
                </a>
                <div style='color:#8B8FA8;font-size:12px;margin-top:12px;'>+{wa}</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # ── Tab 5: Account (UNCHANGED) ────────────────────────────────────────────
    with tab5:
        st.markdown("### ⚙️ Account Settings")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("<div class='gh-card'>", unsafe_allow_html=True)
            st.markdown("#### 👤 Profile Info")
            st.write(f"**Name:** {user.get('name')}")
            st.write(f"**Email:** {user.get('email')}")
            st.write(f"**Plan:** {user.get('plan','free').upper()}")
            st.write(f"**Status:** {user.get('status','').upper()}")
            st.write(f"**Member Since:** {user.get('created_at','')[:10] if user.get('created_at') else 'N/A'}")
            st.markdown("</div>", unsafe_allow_html=True)
        with col2:
            st.markdown("<div class='gh-card'>", unsafe_allow_html=True)
            st.markdown("#### 🔒 Device Lock")
            device_id = st.session_state.get('device_id','Unknown')
            st.write("Your account is locked to this device for security.")
            st.code(f"Device: {device_id[:16]}...", language=None)
            st.info("Changed devices? Contact admin for a reset.")
            st.markdown(f"""
            <a href='https://wa.me/{wa}?text=Please reset my device ID. Email: {user.get("email","")}' target='_blank' class='wa-button'>
                💬 Request Device Reset
            </a>
            """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def main():
    init_db()
    if "user" not in st.session_state:
        st.session_state.user = None
    generate_device_id()

    is_maint, maint_msg = check_maintenance()
    if is_maint:
        inject_css()
        render_sidebar()
        st.markdown(f"""
        <div class='maint-screen'>
            <div style='font-size:72px;'>🔧</div>
            <h1 style='font-family:Syne,sans-serif;font-size:36px;font-weight:800;margin:16px 0 8px;'>Under Maintenance</h1>
            <p style='color:#8B8FA8;font-size:16px;max-width:500px;margin:0 auto 24px;'>{maint_msg}</p>
            <div style='color:#8B8FA8;font-size:14px;'>Managed by <strong>{DEVELOPER_NAME}</strong></div>
        </div>
        """, unsafe_allow_html=True)
        return

    user = st.session_state.get("user")
    if user is None:
        render_auth_page()
    else:
        render_dashboard(user)

if __name__ == "__main__":
    main()
