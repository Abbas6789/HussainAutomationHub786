import streamlit as st
import sqlite3
import hashlib
import uuid
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

# ─── CONFIG ───────────────────────────────────────────────────────────────────
ADMIN_EMAIL = "hklhhklh5@gmail.com"
ADMIN_PASSWORD = "Ghse45*#"
DEVELOPER_NAME = "Ghulam Hussain"
WHATSAPP_NUMBER = "923461785207"
DB_PATH = "sociosaas.db"
APP_TITLE = "SocioSaas Pro"

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=f"{APP_TITLE} | {DEVELOPER_NAME}",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── DATABASE ─────────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        name TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        plan TEXT DEFAULT 'free',
        device_id TEXT,
        created_at TEXT,
        last_login TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS notice (
        id INTEGER PRIMARY KEY,
        message TEXT DEFAULT ''
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS social_connections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        platform TEXT,
        connected_at TEXT,
        account_name TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS videos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        hashtags TEXT,
        filename TEXT,
        uploaded_at TEXT,
        status TEXT DEFAULT 'queued'
    )''')
    # Seed notice board
    c.execute("INSERT OR IGNORE INTO notice (id, message) VALUES (1, '🎉 Welcome to SocioSaas Pro! Automate your social media growth today.')")
    conn.commit()
    conn.close()

def get_db():
    return sqlite3.connect(DB_PATH)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def generate_device_id() -> str:
    """Generate a browser-session fingerprint."""
    if "device_id" not in st.session_state:
        # Combine random UUID with session-specific info
        raw = f"{uuid.uuid4()}-{st.context.headers.get('User-Agent','unknown') if hasattr(st, 'context') else 'browser'}"
        st.session_state.device_id = hashlib.md5(raw.encode()).hexdigest()
    return st.session_state.device_id

def get_notice():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT message FROM notice WHERE id=1")
    row = c.fetchone()
    conn.close()
    return row[0] if row else ""

def update_notice(msg: str):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE notice SET message=? WHERE id=1", (msg,))
    conn.commit()
    conn.close()

def register_user(email, password, name):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (email, password, name, created_at) VALUES (?,?,?,?)",
                  (email, hash_password(password), name, datetime.now().isoformat()))
        conn.commit()
        return True, "Registration successful! Await admin approval."
    except sqlite3.IntegrityError:
        return False, "Email already registered."
    finally:
        conn.close()

def login_user(email, password, device_id):
    if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
        return "admin", None
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email=? AND password=?",
              (email, hash_password(password)))
    user = c.fetchone()
    if not user:
        conn.close()
        return None, "Invalid email or password."
    cols = [d[0] for d in c.description]
    u = dict(zip(cols, user))
    if u['status'] == 'pending':
        conn.close()
        return None, "⏳ Your account is pending admin approval."
    if u['status'] == 'blocked':
        conn.close()
        return None, "🚫 Your account has been blocked. Contact developer."
    if u['device_id'] and u['device_id'] != device_id:
        conn.close()
        return None, "🔒 Device mismatch! This account is locked to another device. Contact admin to reset."
    if not u['device_id']:
        c.execute("UPDATE users SET device_id=?, last_login=? WHERE id=?",
                  (device_id, datetime.now().isoformat(), u['id']))
        conn.commit()
    else:
        c.execute("UPDATE users SET last_login=? WHERE id=?",
                  (datetime.now().isoformat(), u['id']))
        conn.commit()
    conn.close()
    return u, None

def get_all_users():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, email, name, status, plan, device_id, created_at, last_login FROM users")
    rows = c.fetchall()
    conn.close()
    return rows

def update_user_status(user_id, status):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET status=? WHERE id=?", (status, user_id))
    conn.commit()
    conn.close()

def reset_device(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET device_id=NULL WHERE id=?", (user_id,))
    conn.commit()
    conn.close()

def update_plan(user_id, plan):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET plan=? WHERE id=?", (plan, user_id))
    conn.commit()
    conn.close()

def get_user_videos(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM videos WHERE user_id=? ORDER BY uploaded_at DESC", (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def add_video(user_id, title, hashtags, filename):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO videos (user_id, title, hashtags, filename, uploaded_at) VALUES (?,?,?,?,?)",
              (user_id, title, hashtags, filename, datetime.now().isoformat()))
    conn.commit()
    conn.close()

# ─── CSS ──────────────────────────────────────────────────────────────────────
def inject_css(is_dashboard=False, profile_pic_exists=False):
    watermark = ""
    if is_dashboard and profile_pic_exists:
        watermark = """
        .main .block-container::before {
            content: '';
            position: fixed;
            top: 50%;
            left: 55%;
            transform: translate(-50%, -50%);
            width: 420px;
            height: 420px;
            background-image: url('data:image/png;base64,WATERMARK_PLACEHOLDER');
            background-size: contain;
            background-repeat: no-repeat;
            background-position: center;
            opacity: 0.04;
            pointer-events: none;
            z-index: 0;
        }
        """

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,300&display=swap');

    :root {{
        --primary: #6C63FF;
        --primary-dark: #4A43CC;
        --accent: #FF6584;
        --success: #43D9AD;
        --warning: #FFB547;
        --bg-dark: #0D0F1A;
        --bg-card: #161929;
        --bg-card2: #1E2235;
        --text-main: #E8EAFF;
        --text-muted: #8B8FA8;
        --border: #2A2D45;
    }}

    html, body, .stApp {{
        background-color: var(--bg-dark) !important;
        font-family: 'DM Sans', sans-serif;
        color: var(--text-main);
    }}

    h1, h2, h3 {{ font-family: 'Syne', sans-serif; color: var(--text-main); }}

    /* Sidebar */
    section[data-testid="stSidebar"] {{
        background: linear-gradient(180deg, #10132A 0%, #0D0F1A 100%) !important;
        border-right: 1px solid var(--border);
    }}
    section[data-testid="stSidebar"] * {{ color: var(--text-main) !important; }}

    /* Inputs */
    .stTextInput > div > div > input,
    .stPasswordInput > div > div > input {{
        background: var(--bg-card2) !important;
        border: 1px solid var(--border) !important;
        color: var(--text-main) !important;
        border-radius: 10px !important;
        padding: 12px 16px !important;
        font-family: 'DM Sans', sans-serif;
    }}
    .stTextInput > div > div > input:focus,
    .stPasswordInput > div > div > input:focus {{
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 2px rgba(108,99,255,0.25) !important;
    }}

    /* Buttons */
    .stButton > button {{
        background: linear-gradient(135deg, var(--primary), var(--primary-dark)) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 10px 24px !important;
        font-family: 'Syne', sans-serif !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        transition: all 0.2s ease !important;
        cursor: pointer !important;
    }}
    .stButton > button:hover {{
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 20px rgba(108,99,255,0.4) !important;
    }}

    /* Metric cards */
    [data-testid="stMetric"] {{
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 14px !important;
        padding: 16px !important;
    }}
    [data-testid="stMetricValue"] {{ color: var(--primary) !important; font-family: 'Syne', sans-serif; }}

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{
        background: var(--bg-card) !important;
        border-radius: 12px !important;
        padding: 4px !important;
        border: 1px solid var(--border);
    }}
    .stTabs [data-baseweb="tab"] {{
        color: var(--text-muted) !important;
        font-family: 'Syne', sans-serif !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
    }}
    .stTabs [aria-selected="true"] {{
        background: var(--primary) !important;
        color: white !important;
    }}

    /* Alerts */
    .stAlert {{ border-radius: 12px !important; border: none !important; }}
    .stSuccess {{ background: rgba(67,217,173,0.1) !important; border-left: 3px solid var(--success) !important; }}
    .stError {{ background: rgba(255,101,132,0.1) !important; border-left: 3px solid var(--accent) !important; }}
    .stWarning {{ background: rgba(255,181,71,0.1) !important; border-left: 3px solid var(--warning) !important; }}
    .stInfo {{ background: rgba(108,99,255,0.1) !important; border-left: 3px solid var(--primary) !important; }}

    /* Dataframes */
    .stDataFrame {{ border-radius: 12px !important; overflow: hidden; }}

    /* Divider */
    hr {{ border-color: var(--border) !important; }}

    /* Custom card */
    .gh-card {{
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 24px;
        margin: 12px 0;
        position: relative;
        overflow: hidden;
    }}
    .gh-card::before {{
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, var(--primary), var(--accent));
    }}

    /* Plan cards */
    .plan-card {{
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 20px;
        padding: 32px 24px;
        text-align: center;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }}
    .plan-card.premium {{
        border-color: var(--primary);
        background: linear-gradient(160deg, #1E2235, #16183A);
    }}
    .plan-card:hover {{
        transform: translateY(-4px);
        box-shadow: 0 16px 40px rgba(108,99,255,0.2);
    }}
    .plan-price {{
        font-family: 'Syne', sans-serif;
        font-size: 42px;
        font-weight: 800;
        color: var(--primary);
    }}

    /* Login page */
    .login-hero {{
        text-align: center;
        padding: 20px 0 10px;
    }}
    .login-title {{
        font-family: 'Syne', sans-serif;
        font-size: 42px;
        font-weight: 800;
        background: linear-gradient(135deg, #6C63FF, #FF6584);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        line-height: 1.1;
    }}
    .dev-badge {{
        display: inline-block;
        background: rgba(108,99,255,0.15);
        border: 1px solid rgba(108,99,255,0.4);
        color: #A89CFF;
        padding: 6px 16px;
        border-radius: 100px;
        font-size: 13px;
        font-family: 'DM Sans', sans-serif;
        margin: 8px 0;
    }}
    .wa-button {{
        display: inline-block;
        background: linear-gradient(135deg, #25D366, #128C7E);
        color: white !important;
        padding: 10px 22px;
        border-radius: 10px;
        text-decoration: none !important;
        font-family: 'Syne', sans-serif;
        font-weight: 600;
        font-size: 14px;
        transition: all 0.2s;
    }}
    .wa-button:hover {{ box-shadow: 0 6px 20px rgba(37,211,102,0.4); transform: translateY(-2px); }}

    /* Social buttons */
    .social-btn {{
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 10px;
        padding: 12px 20px;
        border-radius: 12px;
        border: 1px solid var(--border);
        background: var(--bg-card2);
        color: var(--text-main);
        font-family: 'Syne', sans-serif;
        font-weight: 600;
        font-size: 14px;
        cursor: pointer;
        transition: all 0.2s;
        width: 100%;
        margin: 6px 0;
        text-align: center;
    }}
    .social-btn.yt {{ border-color: #FF0000; }}
    .social-btn.yt:hover {{ background: rgba(255,0,0,0.1); box-shadow: 0 4px 16px rgba(255,0,0,0.2); }}
    .social-btn.fb {{ border-color: #1877F2; }}
    .social-btn.fb:hover {{ background: rgba(24,119,242,0.1); box-shadow: 0 4px 16px rgba(24,119,242,0.2); }}
    .social-btn.tt {{ border-color: #69C9D0; }}
    .social-btn.tt:hover {{ background: rgba(105,201,208,0.1); box-shadow: 0 4px 16px rgba(105,201,208,0.2); }}

    /* Notice banner */
    .notice-banner {{
        background: linear-gradient(135deg, rgba(108,99,255,0.15), rgba(255,101,132,0.1));
        border: 1px solid rgba(108,99,255,0.3);
        border-radius: 12px;
        padding: 14px 20px;
        margin-bottom: 20px;
        font-size: 14px;
        color: #C4BEFF;
    }}

    /* Status badges */
    .badge-approved {{ color: #43D9AD; background: rgba(67,217,173,0.1); padding: 3px 10px; border-radius: 100px; font-size: 12px; font-weight: 600; }}
    .badge-pending {{ color: #FFB547; background: rgba(255,181,71,0.1); padding: 3px 10px; border-radius: 100px; font-size: 12px; font-weight: 600; }}
    .badge-blocked {{ color: #FF6584; background: rgba(255,101,132,0.1); padding: 3px 10px; border-radius: 100px; font-size: 12px; font-weight: 600; }}

    /* Hide Streamlit branding */
    #MainMenu, footer {{ visibility: hidden; }}
    header[data-testid="stHeader"] {{ background: transparent; }}

    {watermark}
    </style>
    """, unsafe_allow_html=True)

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
def render_sidebar(user=None):
    with st.sidebar:
        # Profile picture
        pic_path = Path("hussain.jpg")
        if pic_path.exists():
            st.image(str(pic_path), width=80, use_container_width=False)
        else:
            st.markdown("🧑‍💻")

        st.markdown(f"""
        <div style='margin: 8px 0 16px;'>
            <div style='font-family: Syne, sans-serif; font-size: 18px; font-weight: 700;'>{DEVELOPER_NAME}</div>
            <div style='color: #8B8FA8; font-size: 12px; margin-top: 2px;'>Social Media Automation</div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        if user and user != "admin":
            plan_color = "#43D9AD" if user.get('plan') == 'premium' else "#FFB547"
            plan_label = "⭐ Premium" if user.get('plan') == 'premium' else "🆓 Free Plan"
            st.markdown(f"""
            <div style='background: var(--bg-card2, #1E2235); border-radius: 10px; padding: 12px; margin-bottom: 16px;'>
                <div style='font-size: 13px; color: #8B8FA8;'>Logged in as</div>
                <div style='font-weight: 600; font-size: 14px; margin-top: 2px;'>{user.get('name','User')}</div>
                <div style='font-size: 12px; color: {plan_color}; margin-top: 4px;'>{plan_label}</div>
            </div>
            """, unsafe_allow_html=True)

        elif user == "admin":
            st.markdown("""
            <div style='background: rgba(255,101,132,0.1); border: 1px solid rgba(255,101,132,0.3); border-radius: 10px; padding: 12px; margin-bottom: 16px;'>
                <div style='color: #FF6584; font-weight: 700; font-size: 13px;'>🛡️ MASTER ADMIN</div>
                <div style='color: #8B8FA8; font-size: 12px; margin-top: 2px;'>Full system access</div>
            </div>
            """, unsafe_allow_html=True)

        st.divider()

        # WhatsApp contact
        st.markdown(f"""
        <div style='text-align: center; padding: 8px 0;'>
            <a href='https://wa.me/{WHATSAPP_NUMBER}' target='_blank' class='wa-button'>
                💬 Contact Developer
            </a>
        </div>
        """, unsafe_allow_html=True)

        if user:
            st.divider()
            if st.button("🚪 Logout", use_container_width=True):
                for key in list(st.session_state.keys()):
                    if key != 'device_id':
                        del st.session_state[key]
                st.rerun()

# ─── LOGIN / REGISTER PAGE ────────────────────────────────────────────────────
def render_auth_page():
    render_sidebar()
    inject_css()

    pic_path = Path("hussain.jpg")

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        # Hero
        if pic_path.exists():
            colA, colB, colC = st.columns([1, 1, 1])
            with colB:
                st.image(str(pic_path), width=90)

        st.markdown(f"""
        <div class='login-hero'>
            <div class='login-title'>SocioSaas Pro</div>
            <div style='color: #8B8FA8; font-size: 15px; margin: 6px 0 4px;'>
                Automate. Grow. Dominate Social Media.
            </div>
            <span class='dev-badge'>by {DEVELOPER_NAME}</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        tab_login, tab_register = st.tabs(["🔐 Login", "📝 Register"])

        with tab_login:
            st.markdown("<div class='gh-card'>", unsafe_allow_html=True)
            email = st.text_input("Email Address", placeholder="you@example.com", key="login_email")
            password = st.text_input("Password", type="password", placeholder="••••••••", key="login_pass")
            st.markdown("<br>", unsafe_allow_html=True)

            if st.button("🚀 Sign In", use_container_width=True, key="btn_login"):
                if email and password:
                    device_id = generate_device_id()
                    result, err = login_user(email, password, device_id)
                    if result == "admin":
                        st.session_state.user = "admin"
                        st.session_state.is_admin = True
                        st.rerun()
                    elif result:
                        st.session_state.user = result
                        st.session_state.is_admin = False
                        st.rerun()
                    else:
                        st.error(err)
                else:
                    st.warning("Please fill all fields.")
            st.markdown("</div>", unsafe_allow_html=True)

        with tab_register:
            st.markdown("<div class='gh-card'>", unsafe_allow_html=True)
            name = st.text_input("Full Name", placeholder="Your Name", key="reg_name")
            reg_email = st.text_input("Email Address", placeholder="you@example.com", key="reg_email")
            reg_pass = st.text_input("Password", type="password", placeholder="Min 6 characters", key="reg_pass")
            reg_pass2 = st.text_input("Confirm Password", type="password", placeholder="Repeat password", key="reg_pass2")
            st.markdown("<br>", unsafe_allow_html=True)

            if st.button("✨ Create Account", use_container_width=True, key="btn_register"):
                if name and reg_email and reg_pass and reg_pass2:
                    if reg_pass != reg_pass2:
                        st.error("Passwords do not match.")
                    elif len(reg_pass) < 6:
                        st.error("Password must be at least 6 characters.")
                    else:
                        ok, msg = register_user(reg_email, reg_pass, name)
                        if ok:
                            st.success(msg)
                        else:
                            st.error(msg)
                else:
                    st.warning("Please fill all fields.")
            st.markdown("</div>", unsafe_allow_html=True)

# ─── ADMIN DASHBOARD ──────────────────────────────────────────────────────────
def render_admin():
    inject_css()
    render_sidebar("admin")

    st.markdown(f"""
    <div style='margin-bottom: 24px;'>
        <h1 style='font-family: Syne, sans-serif; font-size: 32px; font-weight: 800; margin: 0;'>
            🛡️ Admin Control Panel
        </h1>
        <p style='color: #8B8FA8; margin: 4px 0 0;'>Master Dashboard — {DEVELOPER_NAME}</p>
    </div>
    """, unsafe_allow_html=True)

    users = get_all_users()
    total = len(users)
    pending = sum(1 for u in users if u[3] == 'pending')
    active = sum(1 for u in users if u[3] == 'approved')
    premium = sum(1 for u in users if u[4] == 'premium')

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("👥 Total Users", total)
    with c2: st.metric("⏳ Pending", pending)
    with c3: st.metric("✅ Active", active)
    with c4: st.metric("⭐ Premium", premium)

    st.markdown("<br>", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["👥 User Management", "📢 Notice Board", "🔒 Device Management"])

    with tab1:
        st.markdown("### Registered Users")
        if not users:
            st.info("No users registered yet.")
        else:
            for u in users:
                uid, email, name, status, plan, device_id, created_at, last_login = u
                with st.expander(f"{'🟢' if status=='approved' else '🟡' if status=='pending' else '🔴'} {name} — {email}"):
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.write(f"**Status:** {status.upper()}")
                        st.write(f"**Plan:** {plan.upper()}")
                    with col2:
                        st.write(f"**Joined:** {created_at[:10] if created_at else 'N/A'}")
                        st.write(f"**Last Login:** {last_login[:10] if last_login else 'Never'}")
                    with col3:
                        if status != 'approved':
                            if st.button(f"✅ Approve", key=f"approve_{uid}"):
                                update_user_status(uid, 'approved')
                                st.success(f"Approved {name}")
                                st.rerun()
                        if status != 'blocked':
                            if st.button(f"🚫 Block", key=f"block_{uid}"):
                                update_user_status(uid, 'blocked')
                                st.warning(f"Blocked {name}")
                                st.rerun()
                        if status == 'blocked':
                            if st.button(f"🔓 Unblock", key=f"unblock_{uid}"):
                                update_user_status(uid, 'approved')
                                st.success(f"Unblocked {name}")
                                st.rerun()
                    with col4:
                        new_plan = "free" if plan == "premium" else "premium"
                        plan_label = "⬇️ Downgrade" if plan == "premium" else "⭐ Set Premium"
                        if st.button(plan_label, key=f"plan_{uid}"):
                            update_plan(uid, new_plan)
                            st.success(f"Plan updated to {new_plan}")
                            st.rerun()

    with tab2:
        st.markdown("### 📢 Notice Board")
        st.write("This message is shown to all logged-in users.")
        current_notice = get_notice()
        new_notice = st.text_area("Notice Message", value=current_notice, height=100,
                                   placeholder="Enter announcement for all users...", key="admin_notice")
        if st.button("💾 Save Notice", key="save_notice"):
            update_notice(new_notice)
            st.success("✅ Notice updated!")

    with tab3:
        st.markdown("### 🔒 Device ID Management")
        st.write("Reset a user's device lock to allow them to log in from a new device.")
        if not users:
            st.info("No users.")
        else:
            for u in users:
                uid, email, name, status, plan, device_id, *_ = u
                if device_id:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**{name}** ({email})")
                        st.code(f"Device: {device_id[:20]}...", language=None)
                    with col2:
                        if st.button("🔄 Reset Device", key=f"reset_{uid}"):
                            reset_device(uid)
                            st.success(f"Device reset for {name}")
                            st.rerun()

# ─── USER DASHBOARD ───────────────────────────────────────────────────────────
def render_dashboard(user: dict):
    inject_css(is_dashboard=True, profile_pic_exists=Path("hussain.jpg").exists())
    render_sidebar(user)

    # Notice board
    notice = get_notice()
    if notice:
        st.markdown(f"<div class='notice-banner'>📢 {notice}</div>", unsafe_allow_html=True)

    # Header
    st.markdown(f"""
    <div style='margin-bottom: 24px;'>
        <h1 style='font-family: Syne, sans-serif; font-size: 30px; font-weight: 800; margin: 0;'>
            👋 Welcome back, {user.get('name','User')}!
        </h1>
        <p style='color: #8B8FA8; margin: 4px 0 0;'>Powered by {DEVELOPER_NAME} · SocioSaas Pro</p>
    </div>
    """, unsafe_allow_html=True)

    # Quick stats
    videos = get_user_videos(user['id'])
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("📹 Videos Uploaded", len(videos))
    with c2: st.metric("🔗 Connected Platforms", 0)
    with c3: st.metric("📅 Member Since", user.get('created_at', 'N/A')[:10] if user.get('created_at') else 'N/A')
    with c4:
        plan = user.get('plan','free')
        st.metric("💎 Plan", plan.upper())

    st.markdown("<br>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["🔗 Social Connect", "📹 Video Automation", "💎 Subscription", "⚙️ Account"])

    # ── Social Connect ──────────────────────────────────────────────────────
    with tab1:
        st.markdown("### 🔗 Connect Your Social Media")
        st.markdown("<div class='gh-card'>", unsafe_allow_html=True)
        st.write("Connect your accounts to enable automated publishing and analytics.")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("""
            <div class='gh-card' style='text-align: center;'>
                <div style='font-size: 40px;'>▶️</div>
                <div style='font-family: Syne, sans-serif; font-size: 16px; font-weight: 700; margin: 8px 0;'>YouTube</div>
                <div style='color: #8B8FA8; font-size: 13px; margin-bottom: 16px;'>Upload videos, manage playlists & analytics</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Connect YouTube", key="yt_connect", use_container_width=True):
                st.info("🔄 YouTube OAuth — Configure your Google Client ID in settings to enable.")

        with col2:
            st.markdown("""
            <div class='gh-card' style='text-align: center;'>
                <div style='font-size: 40px;'>📘</div>
                <div style='font-family: Syne, sans-serif; font-size: 16px; font-weight: 700; margin: 8px 0;'>Facebook</div>
                <div style='color: #8B8FA8; font-size: 13px; margin-bottom: 16px;'>Post to pages, groups & manage ads</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Connect Facebook", key="fb_connect", use_container_width=True):
                st.info("🔄 Facebook OAuth — Configure your Facebook App ID in settings to enable.")

        with col3:
            st.markdown("""
            <div class='gh-card' style='text-align: center;'>
                <div style='font-size: 40px;'>🎵</div>
                <div style='font-family: Syne, sans-serif; font-size: 16px; font-weight: 700; margin: 8px 0;'>TikTok</div>
                <div style='color: #8B8FA8; font-size: 13px; margin-bottom: 16px;'>Auto-post videos, get trending hashtags</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Connect TikTok", key="tt_connect", use_container_width=True):
                st.info("🔄 TikTok OAuth — Configure your TikTok Developer credentials to enable.")

        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.info("💡 **OAuth Setup**: Add your API credentials to `.streamlit/secrets.toml` to activate platform connections. See `README.md` for setup guide.")

    # ── Video Automation ────────────────────────────────────────────────────
    with tab2:
        st.markdown("### 📹 Video Upload & Automation")

        if user.get('plan') == 'free':
            st.warning("⚠️ You're on the **Free plan**. Upgrade to **Premium** to unlock unlimited video uploads and auto-scheduling.")

        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown("<div class='gh-card'>", unsafe_allow_html=True)
            st.markdown("#### 📤 Upload Video")
            uploaded_file = st.file_uploader("Choose a video file", type=["mp4", "mov", "avi", "mkv"])
            custom_title = st.text_input("Custom Title (optional)", placeholder="Leave blank for AI-generated title")
            niche = st.selectbox("Content Niche", ["Tech", "Lifestyle", "Gaming", "Education", "Business", "Health", "Entertainment"])
            target_platform = st.multiselect("Target Platforms", ["YouTube", "Facebook", "TikTok"], default=["YouTube"])

            if st.button("⚡ Generate & Queue", key="gen_video", use_container_width=True):
                if uploaded_file:
                    # AI title/hashtag generation (simulated)
                    generated_titles = {
                        "Tech": f"🔥 Top {niche} Tips That Will Blow Your Mind | {datetime.now().year}",
                        "Lifestyle": f"My Ultimate {niche} Routine That Changed Everything",
                        "Gaming": f"INSANE {niche} Moments You Won't Believe!",
                        "Education": f"Learn {niche} in 5 Minutes - Complete Guide",
                        "Business": f"How I Made $10K with {niche} Automation",
                        "Health": f"Transform Your Life with This {niche} Hack",
                        "Entertainment": f"This {niche} Trend is Breaking the Internet 🚀"
                    }
                    hashtag_map = {
                        "Tech": "#tech #technology #coding #AI #programming",
                        "Lifestyle": "#lifestyle #vlog #daily #motivation #life",
                        "Gaming": "#gaming #gamer #gameplay #viral #twitch",
                        "Education": "#education #learn #knowledge #school #study",
                        "Business": "#business #entrepreneur #money #success #hustle",
                        "Health": "#health #fitness #wellness #diet #workout",
                        "Entertainment": "#entertainment #viral #trending #fyp #foryou"
                    }
                    title = custom_title if custom_title else generated_titles.get(niche, "My Video")
                    hashtags = hashtag_map.get(niche, "#viral #trending")
                    add_video(user['id'], title, hashtags, uploaded_file.name)
                    st.success(f"✅ Video queued!\n\n**Title:** {title}\n\n**Tags:** {hashtags}")
                else:
                    st.error("Please upload a video file first.")
            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown("<div class='gh-card'>", unsafe_allow_html=True)
            st.markdown("#### 📋 Video Queue")
            user_videos = get_user_videos(user['id'])
            if not user_videos:
                st.markdown("""
                <div style='text-align: center; color: #8B8FA8; padding: 40px 0;'>
                    <div style='font-size: 40px;'>🎬</div>
                    <div style='margin-top: 12px;'>No videos uploaded yet</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                for v in user_videos[:5]:
                    vid_id, uid, title, hashtags, filename, uploaded_at, status = v
                    status_color = "#43D9AD" if status == "published" else "#FFB547"
                    st.markdown(f"""
                    <div style='border: 1px solid #2A2D45; border-radius: 10px; padding: 12px; margin: 8px 0;'>
                        <div style='font-weight: 600; font-size: 13px;'>{title[:50]}...</div>
                        <div style='color: #8B8FA8; font-size: 11px; margin-top: 4px;'>{filename}</div>
                        <div style='display: flex; justify-content: space-between; margin-top: 8px;'>
                            <span style='font-size: 11px; color: #8B8FA8;'>{uploaded_at[:10]}</span>
                            <span style='font-size: 11px; color: {status_color}; background: rgba(255,181,71,0.1); padding: 2px 8px; border-radius: 100px;'>{status.upper()}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # ── Subscription ─────────────────────────────────────────────────────────
    with tab3:
        st.markdown("### 💎 Choose Your Plan")
        st.markdown("<br>", unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("""
            <div class='plan-card'>
                <div style='font-family: Syne, sans-serif; font-size: 22px; font-weight: 800;'>🆓 Free</div>
                <div class='plan-price'>$0</div>
                <div style='color: #8B8FA8; font-size: 13px; margin-bottom: 20px;'>per month</div>
                <hr style='border-color: #2A2D45; margin: 16px 0;'>
                <div style='text-align: left; font-size: 14px; line-height: 2;'>
                    ✅ 3 Video Uploads/month<br>
                    ✅ 1 Platform Connection<br>
                    ✅ Basic Hashtag Generator<br>
                    ❌ Auto-scheduling<br>
                    ❌ Analytics Dashboard<br>
                    ❌ Priority Support
                </div>
            </div>
            """, unsafe_allow_html=True)
            if user.get('plan') == 'free':
                st.markdown("<div style='text-align:center; padding: 8px; color: #43D9AD; font-weight:600;'>✅ Current Plan</div>", unsafe_allow_html=True)

        with col2:
            st.markdown("""
            <div class='plan-card premium'>
                <div style='position: absolute; top: 16px; right: 16px; background: linear-gradient(135deg, #6C63FF, #FF6584); color: white; padding: 4px 12px; border-radius: 100px; font-size: 11px; font-weight: 700;'>POPULAR</div>
                <div style='font-family: Syne, sans-serif; font-size: 22px; font-weight: 800;'>⭐ Premium</div>
                <div class='plan-price'>$19</div>
                <div style='color: #8B8FA8; font-size: 13px; margin-bottom: 20px;'>per month</div>
                <hr style='border-color: #2A2D45; margin: 16px 0;'>
                <div style='text-align: left; font-size: 14px; line-height: 2;'>
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
                if st.button("🚀 Buy Now — $19/mo", key="buy_premium", use_container_width=True):
                    st.markdown(f"""
                    <div style='background: rgba(108,99,255,0.1); border: 1px solid rgba(108,99,255,0.3); border-radius: 12px; padding: 16px; margin-top: 8px;'>
                        💬 <strong>To upgrade, contact the developer via WhatsApp:</strong><br>
                        <a href='https://wa.me/{WHATSAPP_NUMBER}?text=Hi! I want to upgrade to Premium plan on SocioSaas Pro' target='_blank' class='wa-button' style='display: inline-block; margin-top: 10px;'>
                            📲 WhatsApp: +{WHATSAPP_NUMBER}
                        </a>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown("<div style='text-align:center; padding: 8px; color: #43D9AD; font-weight:600;'>✅ Current Plan</div>", unsafe_allow_html=True)

    # ── Account ───────────────────────────────────────────────────────────────
    with tab4:
        st.markdown("### ⚙️ Account Settings")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("<div class='gh-card'>", unsafe_allow_html=True)
            st.markdown("#### 👤 Profile Info")
            st.write(f"**Name:** {user.get('name')}")
            st.write(f"**Email:** {user.get('email')}")
            st.write(f"**Plan:** {user.get('plan','free').upper()}")
            st.write(f"**Status:** {user.get('status','').upper()}")
            st.write(f"**Member Since:** {user.get('created_at','N/A')[:10] if user.get('created_at') else 'N/A'}")
            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown("<div class='gh-card'>", unsafe_allow_html=True)
            st.markdown("#### 🔒 Device Lock Status")
            device_id = st.session_state.get('device_id', 'Unknown')
            st.write("Your account is locked to this device for security.")
            st.code(f"Device ID: {device_id[:16]}...", language=None)
            st.info("To reset your device lock (e.g., new computer), contact the developer.")
            st.markdown(f"""
            <a href='https://wa.me/{WHATSAPP_NUMBER}?text=Hi! Please reset my device ID. Email: {user.get('email')}' target='_blank' class='wa-button'>
                💬 Request Device Reset
            </a>
            """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    init_db()

    # Session defaults
    if "user" not in st.session_state:
        st.session_state.user = None
    if "is_admin" not in st.session_state:
        st.session_state.is_admin = False

    # Generate/persist device fingerprint
    generate_device_id()

    user = st.session_state.get("user")

    if user is None:
        render_auth_page()
    elif user == "admin":
        render_admin()
    else:
        render_dashboard(user)

if __name__ == "__main__":
    main()
