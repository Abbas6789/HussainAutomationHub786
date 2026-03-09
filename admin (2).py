"""
admin.py — SocioSaas Pro | Master Admin Panel
Developer: Ghulam Hussain
Run: streamlit run admin.py
"""

import streamlit as st
import sqlite3
import hashlib
import json
from datetime import datetime
from pathlib import Path
import firebase_utils as fb

# ─── CONSTANTS ────────────────────────────────────────────────────────────────
ADMIN_EMAIL    = "hklhhklh5@gmail.com"
ADMIN_PASSWORD = "Ghse45*#"
DEVELOPER_NAME = "Ghulam Hussain"
WHATSAPP_NUMBER = "923461785207"
DB_PATH        = "sociosaas.db"
APP_TITLE      = "SocioSaas Admin"

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=f"Admin Panel | {DEVELOPER_NAME}",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── DATABASE (shared with app.py) ────────────────────────────────────────────
def get_db():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_db()
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
    c.execute("INSERT OR IGNORE INTO notice (id, message) VALUES (1, '🎉 Welcome to SocioSaas Pro!')")
    conn.commit()
    conn.close()

def hash_password(p): return hashlib.sha256(p.encode()).hexdigest()

def get_all_users():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id,email,name,status,plan,device_id,created_at,last_login FROM users")
    rows = c.fetchall()
    conn.close()
    return rows

def update_user_status(uid, status):
    conn = get_db(); c = conn.cursor()
    c.execute("UPDATE users SET status=? WHERE id=?", (status, uid))
    conn.commit(); conn.close()

def reset_device(uid):
    conn = get_db(); c = conn.cursor()
    c.execute("UPDATE users SET device_id=NULL WHERE id=?", (uid,))
    conn.commit(); conn.close()

def update_plan(uid, plan):
    conn = get_db(); c = conn.cursor()
    c.execute("UPDATE users SET plan=? WHERE id=?", (plan, uid))
    conn.commit(); conn.close()

def get_all_videos():
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT v.id, u.name, u.email, v.title, v.filename, v.uploaded_at, v.status
                 FROM videos v JOIN users u ON v.user_id = u.id
                 ORDER BY v.uploaded_at DESC""")
    rows = c.fetchall(); conn.close(); return rows

def update_video_status(vid_id, status):
    conn = get_db(); c = conn.cursor()
    c.execute("UPDATE videos SET status=? WHERE id=?", (status, vid_id))
    conn.commit(); conn.close()

# ─── CSS ──────────────────────────────────────────────────────────────────────
def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');
    :root {
        --primary:#6C63FF; --primary-dark:#4A43CC; --accent:#FF6584;
        --success:#43D9AD; --warning:#FFB547; --danger:#FF6584;
        --bg-dark:#0D0F1A; --bg-card:#161929; --bg-card2:#1E2235;
        --text-main:#E8EAFF; --text-muted:#8B8FA8; --border:#2A2D45;
    }
    html,body,.stApp { background:var(--bg-dark)!important; font-family:'DM Sans',sans-serif; color:var(--text-main); }
    h1,h2,h3 { font-family:'Syne',sans-serif; color:var(--text-main); }

    section[data-testid="stSidebar"] {
        background:linear-gradient(180deg,#10132A 0%,#0D0F1A 100%)!important;
        border-right:1px solid var(--border);
    }
    section[data-testid="stSidebar"] * { color:var(--text-main)!important; }

    .stTextInput>div>div>input, .stPasswordInput>div>div>input, .stTextArea>div>div>textarea {
        background:var(--bg-card2)!important; border:1px solid var(--border)!important;
        color:var(--text-main)!important; border-radius:10px!important;
    }
    .stTextInput>div>div>input:focus, .stPasswordInput>div>div>input:focus {
        border-color:var(--primary)!important;
        box-shadow:0 0 0 2px rgba(108,99,255,0.25)!important;
    }
    .stButton>button {
        background:linear-gradient(135deg,var(--primary),var(--primary-dark))!important;
        color:white!important; border:none!important; border-radius:10px!important;
        padding:10px 24px!important; font-family:'Syne',sans-serif!important;
        font-weight:600!important; transition:all 0.2s!important;
    }
    .stButton>button:hover { transform:translateY(-2px)!important; box-shadow:0 8px 20px rgba(108,99,255,0.4)!important; }

    [data-testid="stMetric"] { background:var(--bg-card)!important; border:1px solid var(--border)!important; border-radius:14px!important; padding:16px!important; }
    [data-testid="stMetricValue"] { color:var(--primary)!important; font-family:'Syne',sans-serif; }

    .stTabs [data-baseweb="tab-list"] { background:var(--bg-card)!important; border-radius:12px!important; padding:4px!important; border:1px solid var(--border); }
    .stTabs [data-baseweb="tab"] { color:var(--text-muted)!important; font-family:'Syne',sans-serif!important; font-weight:600!important; border-radius:8px!important; }
    .stTabs [aria-selected="true"] { background:var(--primary)!important; color:white!important; }

    .stAlert { border-radius:12px!important; border:none!important; }
    .stSuccess { background:rgba(67,217,173,0.1)!important; border-left:3px solid var(--success)!important; }
    .stError { background:rgba(255,101,132,0.1)!important; border-left:3px solid var(--accent)!important; }
    .stWarning { background:rgba(255,181,71,0.1)!important; border-left:3px solid var(--warning)!important; }
    .stInfo { background:rgba(108,99,255,0.1)!important; border-left:3px solid var(--primary)!important; }

    hr { border-color:var(--border)!important; }

    .gh-card { background:var(--bg-card); border:1px solid var(--border); border-radius:16px; padding:24px; margin:12px 0; position:relative; overflow:hidden; }
    .gh-card::before { content:''; position:absolute; top:0; left:0; right:0; height:2px; background:linear-gradient(90deg,var(--primary),var(--accent)); }

    .admin-header { background:linear-gradient(135deg,rgba(255,101,132,0.12),rgba(108,99,255,0.08)); border:1px solid rgba(255,101,132,0.25); border-radius:16px; padding:20px 28px; margin-bottom:24px; }

    .section-badge { display:inline-block; background:rgba(108,99,255,0.15); border:1px solid rgba(108,99,255,0.3); color:#A89CFF; padding:4px 14px; border-radius:100px; font-size:12px; font-weight:600; margin-bottom:12px; }

    .msg-card { background:var(--bg-card2); border:1px solid var(--border); border-radius:12px; padding:16px; margin:8px 0; }
    .msg-card.replied { border-color:rgba(67,217,173,0.3); }
    .msg-card.unread { border-color:rgba(255,181,71,0.4); border-left:3px solid var(--warning); }

    .toggle-on { background:rgba(67,217,173,0.15)!important; border:1px solid rgba(67,217,173,0.4)!important; border-radius:12px; padding:16px; }
    .toggle-off { background:rgba(255,101,132,0.1)!important; border:1px solid rgba(255,101,132,0.3)!important; border-radius:12px; padding:16px; }

    .wa-button { display:inline-block; background:linear-gradient(135deg,#25D366,#128C7E); color:white!important; padding:10px 22px; border-radius:10px; text-decoration:none!important; font-family:'Syne',sans-serif; font-weight:600; font-size:14px; transition:all 0.2s; }
    .wa-button:hover { box-shadow:0 6px 20px rgba(37,211,102,0.4); transform:translateY(-2px); }

    #MainMenu, footer { visibility:hidden; }
    header[data-testid="stHeader"] { background:transparent; }

    select, .stSelectbox>div>div { background:var(--bg-card2)!important; color:var(--text-main)!important; border-color:var(--border)!important; }
    </style>
    """, unsafe_allow_html=True)

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        pic = Path("hussain.jpg")
        if pic.exists():
            st.image(str(pic), width=75)
        st.markdown(f"""
        <div style='margin:8px 0 16px;'>
            <div style='font-family:Syne,sans-serif;font-size:17px;font-weight:700;'>{DEVELOPER_NAME}</div>
            <div style='color:#FF6584;font-size:11px;font-weight:600;letter-spacing:1px;'>MASTER ADMIN</div>
        </div>
        """, unsafe_allow_html=True)
        st.divider()

        # Firebase status indicator
        maint = fb.get_maintenance_status()
        status_color = "#FF6584" if maint.get("enabled") else "#43D9AD"
        status_label = "🔴 MAINTENANCE ON" if maint.get("enabled") else "🟢 APP ONLINE"
        st.markdown(f"""
        <div style='background:var(--bg-card2,#1E2235);border-radius:10px;padding:12px;margin-bottom:12px;'>
            <div style='font-size:12px;color:{status_color};font-weight:700;'>{status_label}</div>
            <div style='font-size:11px;color:#8B8FA8;margin-top:2px;'>Firebase Connected</div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()
        st.markdown(f"""
        <div style='text-align:center;padding:8px 0;'>
            <a href='https://wa.me/{WHATSAPP_NUMBER}' target='_blank' class='wa-button'>💬 WhatsApp</a>
        </div>
        """, unsafe_allow_html=True)
        st.divider()
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()

# ─── LOGIN ────────────────────────────────────────────────────────────────────
def render_login():
    inject_css()

    # ── Brute-force lockout state ────────────────────────────────────────────
    if "admin_fail_count" not in st.session_state:
        st.session_state.admin_fail_count = 0
    if "admin_locked_until" not in st.session_state:
        st.session_state.admin_locked_until = 0

    import time
    now = time.time()
    is_locked = now < st.session_state.admin_locked_until
    lock_secs  = max(0, int(st.session_state.admin_locked_until - now))

    # Extra CSS just for login page
    st.markdown("""
    <style>
    .login-wrap {
        background: linear-gradient(160deg, #12142A 0%, #0D0F1A 100%);
        border: 1px solid #2A2D45;
        border-radius: 20px;
        padding: 36px 32px 28px;
        position: relative;
        overflow: hidden;
    }
    .login-wrap::before {
        content: '';
        position: absolute; top: 0; left: 0; right: 0; height: 3px;
        background: linear-gradient(90deg, #FF6584, #6C63FF, #43D9AD);
    }
    .login-lock-badge {
        display: inline-flex; align-items: center; gap: 6px;
        background: rgba(255,101,132,0.12); border: 1px solid rgba(255,101,132,0.35);
        color: #FF8FA3; padding: 6px 16px; border-radius: 100px;
        font-size: 12px; font-weight: 600; margin-bottom: 6px;
    }
    .credential-hint {
        background: rgba(108,99,255,0.08);
        border: 1px solid rgba(108,99,255,0.2);
        border-radius: 10px; padding: 12px 16px; margin: 12px 0;
        font-size: 13px; color: #8B8FA8;
    }
    .credential-hint code {
        color: #A89CFF; background: rgba(108,99,255,0.15);
        padding: 2px 7px; border-radius: 5px; font-size: 12px;
    }
    .attempt-counter {
        display: inline-block;
        color: #FFB547; font-size: 12px; font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)

    _, col2, _ = st.columns([1, 1.1, 1])
    with col2:
        pic = Path("hussain.jpg")
        if pic.exists():
            ca, cb, cc = st.columns([1, 1, 1])
            with cb:
                st.image(str(pic), width=88)

        st.markdown(f"""
        <div style='text-align:center; padding:10px 0 18px;'>
            <div style='font-family:Syne,sans-serif; font-size:32px; font-weight:800;
                        background:linear-gradient(135deg,#FF6584,#6C63FF);
                        -webkit-background-clip:text; -webkit-text-fill-color:transparent;'>
                🛡️ Admin Panel
            </div>
            <div style='color:#8B8FA8; font-size:13px; margin:5px 0 3px;'>
                SocioSaas Pro &mdash; Master Control Centre
            </div>
            <span class='login-lock-badge'>by {DEVELOPER_NAME}</span>
        </div>
        """, unsafe_allow_html=True)

        # ── Locked-out banner ────────────────────────────────────────────────
        if is_locked:
            st.markdown(f"""
            <div style='background:rgba(255,101,132,0.12); border:1px solid rgba(255,101,132,0.4);
                        border-radius:12px; padding:16px; text-align:center; margin-bottom:12px;'>
                <div style='font-size:28px;'>🔒</div>
                <div style='color:#FF6584; font-family:Syne,sans-serif; font-weight:700; font-size:15px; margin:6px 0 4px;'>
                    Access Temporarily Locked
                </div>
                <div style='color:#8B8FA8; font-size:13px;'>
                    Too many failed attempts. Try again in <strong style='color:#FFB547;'>{lock_secs}s</strong>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.stop()

        # ── Login card ───────────────────────────────────────────────────────
        st.markdown("<div class='login-wrap'>", unsafe_allow_html=True)

        # Credential hint card (helpful for first-time setup)
        st.markdown(f"""
        <div class='credential-hint'>
            🔑 <strong>First-time setup?</strong> Use your master credentials:<br>
            Email &nbsp;→ <code>{ADMIN_EMAIL}</code><br>
            Password → <code>Ghse45*#</code>
        </div>
        """, unsafe_allow_html=True)

        email    = st.text_input("📧 Admin Email",
                                  value=ADMIN_EMAIL,          # pre-filled for convenience
                                  placeholder=ADMIN_EMAIL,
                                  key="adm_email")
        password = st.text_input("🔑 Admin Password",
                                  type="password",
                                  placeholder="Enter your master password",
                                  key="adm_pass")

        # Attempt counter display
        if st.session_state.admin_fail_count > 0:
            remaining = 5 - st.session_state.admin_fail_count
            st.markdown(f"""
            <div style='margin:6px 0 2px;'>
                <span class='attempt-counter'>
                    ⚠️ {st.session_state.admin_fail_count} failed attempt(s) —
                    {remaining} remaining before 60s lockout
                </span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("🔐 Access Master Admin Panel", use_container_width=True, key="adm_login_btn"):
            stripped_email    = email.strip().lower()
            stripped_expected = ADMIN_EMAIL.strip().lower()

            if stripped_email == stripped_expected and password == ADMIN_PASSWORD:
                # ✅ Success — clear counters, set session
                st.session_state.admin_logged_in   = True
                st.session_state.admin_fail_count  = 0
                st.session_state.admin_locked_until = 0
                st.rerun()
            else:
                # ❌ Failure — increment counter
                st.session_state.admin_fail_count += 1
                fails = st.session_state.admin_fail_count

                if fails >= 5:
                    # Lock out for 60 seconds
                    st.session_state.admin_locked_until = time.time() + 60
                    st.session_state.admin_fail_count   = 0
                    st.error("🔒 5 failed attempts — locked for 60 seconds.")
                else:
                    # Specific, helpful error messages
                    if stripped_email != stripped_expected:
                        st.error(f"❌ Unrecognised email. Expected: `{ADMIN_EMAIL}`")
                    else:
                        st.error("❌ Incorrect password. Check for typos or extra spaces.")

        st.markdown("</div>", unsafe_allow_html=True)

        # Footer help
        st.markdown(f"""
        <div style='text-align:center; margin-top:16px; color:#8B8FA8; font-size:12px;'>
            Locked out? Contact &nbsp;
            <a href='https://wa.me/{WHATSAPP_NUMBER}' target='_blank'
               style='color:#A89CFF; text-decoration:none;'>
                💬 {DEVELOPER_NAME} on WhatsApp
            </a>
        </div>
        """, unsafe_allow_html=True)

# ─── MAIN ADMIN DASHBOARD ─────────────────────────────────────────────────────
def render_admin_dashboard():
    inject_css()
    render_sidebar()

    st.markdown(f"""
    <div class='admin-header'>
        <h1 style='font-family:Syne,sans-serif;font-size:28px;font-weight:800;margin:0;'>
            🛡️ Master Admin Dashboard
        </h1>
        <p style='color:#8B8FA8;margin:4px 0 0;font-size:14px;'>
            SocioSaas Pro · Full System Control · {DEVELOPER_NAME}
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Top-level stats ──────────────────────────────────────────────────────
    users = get_all_users()
    videos = get_all_videos()
    wa_msgs = fb.get_whatsapp_messages()
    unread_wa = sum(1 for m in wa_msgs if not m.get("replied"))

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: st.metric("👥 Total Users", len(users))
    with c2: st.metric("⏳ Pending", sum(1 for u in users if u[3]=='pending'))
    with c3: st.metric("✅ Active", sum(1 for u in users if u[3]=='approved'))
    with c4: st.metric("📹 Videos", len(videos))
    with c5: st.metric("💬 WA Unread", unread_wa)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 5 Tabs ───────────────────────────────────────────────────────────────
    t1, t2, t3, t4, t5 = st.tabs([
        "🔐 System Auth",
        "📡 Social Media Hub",
        "💬 WhatsApp Manager",
        "🔧 Maintenance",
        "🚀 Remote Update"
    ])

    # ════════════════════════════════════════════════════════════════════════
    # TAB 1 — System Auth
    # ════════════════════════════════════════════════════════════════════════
    with t1:
        st.markdown("<span class='section-badge'>🔐 SYSTEM AUTH</span>", unsafe_allow_html=True)
        st.markdown("### Google / OAuth 2.0 Configuration")
        st.info("These credentials are stored encrypted in Firebase and fetched dynamically by the public app. No API keys are ever hardcoded.")

        existing = fb.get_google_auth_config()
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("<div class='gh-card'>", unsafe_allow_html=True)
            st.markdown("#### Google OAuth Credentials")
            g_client_id = st.text_input(
                "Google Client ID",
                value=existing.get("client_id",""),
                placeholder="xxxx.apps.googleusercontent.com",
                key="g_cid"
            )
            g_client_secret = st.text_input(
                "Google Client Secret",
                value=existing.get("client_secret",""),
                placeholder="GOCSPX-xxxxxxxxxxxx",
                type="password",
                key="g_csec"
            )
            if existing.get("updated_at"):
                st.caption(f"Last updated: {existing['updated_at'][:16]}")
            if st.button("💾 Save Google Auth", key="save_google", use_container_width=True):
                if g_client_id and g_client_secret:
                    if fb.set_google_credentials(g_client_id, g_client_secret):
                        st.success("✅ Google credentials saved to Firebase!")
                    else:
                        st.error("❌ Firebase write failed. Check your DB secret.")
                else:
                    st.warning("Both fields are required.")
            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown("<div class='gh-card'>", unsafe_allow_html=True)
            st.markdown("#### 🔒 Security Info")
            st.markdown("""
            **How it works:**

            1. You enter credentials here → saved to Firebase with auth token
            2. Public app fetches them at runtime via encrypted REST call
            3. No keys ever appear in source code or GitHub
            4. Firebase rules ensure only authenticated requests can read/write

            **Streamlit Secrets required:**
            ```toml
            [firebase]
            database_url = "https://YOUR-PROJECT.firebaseio.com"
            db_secret = "YOUR_DATABASE_SECRET"
            ```
            """)
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 👥 User Management")
        if not users:
            st.info("No users registered yet.")
        else:
            # Summary table
            import pandas as pd
            df_data = [{
                "Name": u[2], "Email": u[1],
                "Status": u[3].upper(), "Plan": u[4].upper(),
                "Device Locked": "Yes" if u[5] else "No",
                "Joined": u[6][:10] if u[6] else "N/A",
                "Last Login": u[7][:10] if u[7] else "Never"
            } for u in users]
            st.dataframe(df_data, use_container_width=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("#### Actions")
            for u in users:
                uid, email, name, status, plan, device_id, created_at, last_login = u
                with st.expander(f"{'🟢' if status=='approved' else '🟡' if status=='pending' else '🔴'} {name} — {email} [{status.upper()}]"):
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        if status != 'approved':
                            if st.button("✅ Approve", key=f"ap_{uid}"):
                                update_user_status(uid, 'approved')
                                st.rerun()
                        if status != 'blocked':
                            if st.button("🚫 Block", key=f"bl_{uid}"):
                                update_user_status(uid, 'blocked')
                                st.rerun()
                        if status == 'blocked':
                            if st.button("🔓 Unblock", key=f"ub_{uid}"):
                                update_user_status(uid, 'approved')
                                st.rerun()
                    with col2:
                        new_plan = "free" if plan=="premium" else "premium"
                        if st.button("⭐ Toggle Plan", key=f"pl_{uid}"):
                            update_plan(uid, new_plan)
                            st.rerun()
                        st.caption(f"Current: {plan.upper()}")
                    with col3:
                        if device_id:
                            if st.button("🔄 Reset Device", key=f"rd_{uid}"):
                                reset_device(uid)
                                st.success("Device reset!")
                                st.rerun()
                        else:
                            st.caption("No device locked")
                    with col4:
                        st.caption(f"Joined: {created_at[:10] if created_at else 'N/A'}")
                        st.caption(f"Last: {last_login[:10] if last_login else 'Never'}")

    # ════════════════════════════════════════════════════════════════════════
    # TAB 2 — Social Media Hub
    # ════════════════════════════════════════════════════════════════════════
    with t2:
        st.markdown("<span class='section-badge'>📡 SOCIAL MEDIA HUB</span>", unsafe_allow_html=True)
        st.markdown("### API Credentials Manager")
        st.info("All keys stored securely in Firebase. The public app fetches them dynamically — never hardcoded.")

        existing_social = fb.get_social_credentials()

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("<div class='gh-card'>", unsafe_allow_html=True)
            st.markdown("#### ▶️ YouTube / Google API")
            yt = existing_social.get("youtube", {})
            yt_api_key = st.text_input("API Key", value=yt.get("api_key",""), type="password", key="yt_api")
            yt_client_id = st.text_input("OAuth Client ID", value=yt.get("client_id",""), key="yt_cid")
            yt_client_secret = st.text_input("OAuth Client Secret", value=yt.get("client_secret",""), type="password", key="yt_csec")
            yt_channel_id = st.text_input("Default Channel ID", value=yt.get("channel_id",""), key="yt_chan")
            if yt.get("updated_at"):
                st.caption(f"Updated: {yt['updated_at'][:16]}")
            if st.button("💾 Save YouTube", key="save_yt", use_container_width=True):
                if fb.set_social_credentials("youtube", {
                    "api_key": yt_api_key, "client_id": yt_client_id,
                    "client_secret": yt_client_secret, "channel_id": yt_channel_id
                }):
                    st.success("✅ YouTube credentials saved!")
                else:
                    st.error("Firebase write failed.")
            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown("<div class='gh-card'>", unsafe_allow_html=True)
            st.markdown("#### 📘 Facebook / Meta API")
            fb_creds = existing_social.get("facebook", {})
            fb_app_id = st.text_input("App ID", value=fb_creds.get("app_id",""), key="fb_aid")
            fb_app_secret = st.text_input("App Secret", value=fb_creds.get("app_secret",""), type="password", key="fb_asec")
            fb_access_token = st.text_input("Page Access Token", value=fb_creds.get("access_token",""), type="password", key="fb_tok")
            fb_page_id = st.text_input("Page ID", value=fb_creds.get("page_id",""), key="fb_pid")
            if fb_creds.get("updated_at"):
                st.caption(f"Updated: {fb_creds['updated_at'][:16]}")
            if st.button("💾 Save Facebook", key="save_fb", use_container_width=True):
                if fb.set_social_credentials("facebook", {
                    "app_id": fb_app_id, "app_secret": fb_app_secret,
                    "access_token": fb_access_token, "page_id": fb_page_id
                }):
                    st.success("✅ Facebook credentials saved!")
                else:
                    st.error("Firebase write failed.")
            st.markdown("</div>", unsafe_allow_html=True)

        with col3:
            st.markdown("<div class='gh-card'>", unsafe_allow_html=True)
            st.markdown("#### 🎵 TikTok API")
            tt = existing_social.get("tiktok", {})
            tt_client_key = st.text_input("Client Key", value=tt.get("client_key",""), key="tt_key")
            tt_client_secret = st.text_input("Client Secret", value=tt.get("client_secret",""), type="password", key="tt_sec")
            tt_access_token = st.text_input("Access Token", value=tt.get("access_token",""), type="password", key="tt_tok")
            tt_open_id = st.text_input("Open ID", value=tt.get("open_id",""), key="tt_oid")
            if tt.get("updated_at"):
                st.caption(f"Updated: {tt['updated_at'][:16]}")
            if st.button("💾 Save TikTok", key="save_tt", use_container_width=True):
                if fb.set_social_credentials("tiktok", {
                    "client_key": tt_client_key, "client_secret": tt_client_secret,
                    "access_token": tt_access_token, "open_id": tt_open_id
                }):
                    st.success("✅ TikTok credentials saved!")
                else:
                    st.error("Firebase write failed.")
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 📹 Video Queue (All Users)")
        if not videos:
            st.info("No videos uploaded yet.")
        else:
            for v in videos[:20]:
                vid_id, uname, uemail, title, filename, uploaded_at, vstatus = v
                sc = "#43D9AD" if vstatus=="published" else "#FFB547" if vstatus=="queued" else "#8B8FA8"
                col1, col2, col3 = st.columns([3,1,1])
                with col1:
                    st.markdown(f"**{title[:60]}**  \n<span style='color:#8B8FA8;font-size:12px;'>{uname} · {filename}</span>", unsafe_allow_html=True)
                with col2:
                    st.markdown(f"<span style='color:{sc};font-size:12px;font-weight:600;'>{vstatus.upper()}</span>", unsafe_allow_html=True)
                with col3:
                    new_vs = "published" if vstatus != "published" else "queued"
                    if st.button(f"{'📤 Publish' if new_vs=='published' else '↩ Requeue'}", key=f"vs_{vid_id}"):
                        update_video_status(vid_id, new_vs)
                        st.rerun()

    # ════════════════════════════════════════════════════════════════════════
    # TAB 3 — WhatsApp Manager
    # ════════════════════════════════════════════════════════════════════════
    with t3:
        st.markdown("<span class='section-badge'>💬 WHATSAPP MANAGER</span>", unsafe_allow_html=True)
        st.markdown("### Incoming User Messages")

        col1, col2 = st.columns([2, 1])
        with col2:
            st.markdown(f"""
            <div style='text-align:center;padding:12px;'>
                <div style='font-size:13px;color:#8B8FA8;margin-bottom:8px;'>Open WhatsApp directly</div>
                <a href='https://wa.me/{WHATSAPP_NUMBER}' target='_blank' class='wa-button'>
                    📲 Open WhatsApp
                </a>
            </div>
            """, unsafe_allow_html=True)

        with col1:
            if st.button("🔄 Refresh Messages", key="refresh_wa"):
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        wa_msgs = fb.get_whatsapp_messages()
        if not wa_msgs:
            st.markdown("""
            <div style='text-align:center;color:#8B8FA8;padding:40px;'>
                <div style='font-size:40px;'>💬</div>
                <div style='margin-top:12px;'>No messages yet</div>
                <div style='font-size:13px;margin-top:4px;'>Messages sent via the public app will appear here</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            for msg in wa_msgs:
                fkey     = msg.get("_firebase_key","")
                is_read  = msg.get("replied", False)
                card_cls = "msg-card replied" if is_read else "msg-card unread"
                badge_c  = "#43D9AD" if is_read else "#FFB547"
                badge_l  = "✅ Replied" if is_read else "🔔 Unread"

                with st.expander(f"{'✅' if is_read else '🔔'} {msg.get('sender_name','?')} — {msg.get('timestamp','')[:16]}"):
                    st.markdown(f"""
                    <div class='{card_cls}'>
                        <div style='display:flex;justify-content:space-between;margin-bottom:8px;'>
                            <div>
                                <strong>{msg.get('sender_name','Unknown')}</strong>
                                <span style='color:#8B8FA8;font-size:12px;margin-left:8px;'>{msg.get('sender_email','')}</span>
                            </div>
                            <span style='color:{badge_c};font-size:12px;font-weight:600;'>{badge_l}</span>
                        </div>
                        <div style='background:rgba(255,255,255,0.04);border-radius:8px;padding:12px;margin:8px 0;font-size:14px;'>
                            {msg.get('message','')}
                        </div>
                        {'<div style="color:#43D9AD;font-size:13px;margin-top:8px;"><strong>Your reply:</strong> ' + msg.get("reply_text","") + '</div>' if is_read and msg.get("reply_text") else ""}
                    </div>
                    """, unsafe_allow_html=True)

                    if not is_read:
                        reply_text = st.text_area("Reply to this message", key=f"reply_{fkey}", placeholder="Type your reply...")
                        col1r, col2r = st.columns(2)
                        with col1r:
                            if st.button("📤 Send Reply", key=f"send_{fkey}", use_container_width=True):
                                if reply_text:
                                    if fb.reply_to_whatsapp(fkey, reply_text):
                                        st.success("Reply saved!")
                                        st.rerun()
                                    else:
                                        st.error("Firebase write failed.")
                                else:
                                    st.warning("Type a reply first.")
                        with col2r:
                            wa_link = f"https://wa.me/{WHATSAPP_NUMBER}?text=Reply+to+{urllib.parse.quote(msg.get('sender_name','user'))}"
                            st.markdown(f"<a href='https://wa.me/{WHATSAPP_NUMBER}' target='_blank' class='wa-button' style='display:block;text-align:center;padding:10px;'>📲 Reply on WhatsApp</a>", unsafe_allow_html=True)
                    if st.button("🗑️ Delete Message", key=f"del_{fkey}"):
                        fb.delete_whatsapp_message(fkey)
                        st.rerun()

    # ════════════════════════════════════════════════════════════════════════
    # TAB 4 — Maintenance Mode
    # ════════════════════════════════════════════════════════════════════════
    with t4:
        st.markdown("<span class='section-badge'>🔧 MAINTENANCE</span>", unsafe_allow_html=True)
        st.markdown("### App Maintenance Switch")

        maint = fb.get_maintenance_status()
        is_on = maint.get("enabled", False)
        current_msg = maint.get("message","🔧 We're performing scheduled maintenance. Please check back soon!")

        status_html = f"""
        <div class='{'toggle-off' if is_on else 'toggle-on'}' style='margin-bottom:16px;'>
            <div style='font-family:Syne,sans-serif;font-size:18px;font-weight:700;'>
                {'🔴 MAINTENANCE MODE IS ON' if is_on else '🟢 APP IS LIVE AND RUNNING'}
            </div>
            <div style='color:#8B8FA8;font-size:13px;margin-top:4px;'>
                {'Public portal is showing maintenance page to users.' if is_on else 'All users can access the public portal normally.'}
            </div>
        </div>
        """
        st.markdown(status_html, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("<div class='gh-card'>", unsafe_allow_html=True)
            new_msg = st.text_area(
                "Maintenance Message (shown to users)",
                value=current_msg,
                height=100,
                key="maint_msg"
            )
            col_on, col_off = st.columns(2)
            with col_on:
                if st.button("🔴 Enable Maintenance", key="maint_on", use_container_width=True):
                    if fb.set_maintenance(True, new_msg):
                        st.success("🔴 Maintenance mode ON")
                        st.rerun()
                    else:
                        st.error("Firebase write failed.")
            with col_off:
                if st.button("🟢 Go Live", key="maint_off", use_container_width=True):
                    if fb.set_maintenance(False, new_msg):
                        st.success("🟢 App is now live!")
                        st.rerun()
                    else:
                        st.error("Firebase write failed.")
            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown("<div class='gh-card'>", unsafe_allow_html=True)
            st.markdown("#### 📢 Notice Board")
            st.write("This message appears as a banner to all logged-in users.")
            current_notice = fb.get_notice_board()
            new_notice = st.text_area(
                "Notice Message",
                value=current_notice,
                height=100,
                key="notice_msg",
                placeholder="Announce updates, features, or news..."
            )
            if st.button("💾 Update Notice Board", key="save_notice", use_container_width=True):
                if fb.set_notice_board(new_notice):
                    st.success("✅ Notice updated!")
                else:
                    # Fallback to SQLite
                    conn = get_db(); c = conn.cursor()
                    c.execute("UPDATE notice SET message=? WHERE id=1", (new_notice,))
                    conn.commit(); conn.close()
                    st.success("✅ Notice updated (SQLite fallback).")
            st.markdown("</div>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # TAB 5 — Remote Update
    # ════════════════════════════════════════════════════════════════════════
    with t5:
        st.markdown("<span class='section-badge'>🚀 REMOTE UPDATE</span>", unsafe_allow_html=True)
        st.markdown("### Remote Config & Live Updates")
        st.info("Push configuration changes to the live app instantly without redeploying. The public app reads these values at startup.")

        remote = fb.get_remote_config()

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("<div class='gh-card'>", unsafe_allow_html=True)
            st.markdown("#### ⚙️ Core Config")

            app_version = st.text_input("App Version", value=remote.get("app_version","1.0.0"), key="rc_ver")
            update_url = st.text_input("Update / Redirect URL", value=remote.get("update_url",""), placeholder="https://...", key="rc_url")
            support_wa = st.text_input("Support WhatsApp Number", value=remote.get("support_whatsapp", WHATSAPP_NUMBER), key="rc_wa")
            premium_price = st.text_input("Premium Plan Price", value=remote.get("premium_price","$19"), key="rc_price")
            free_upload_limit = st.text_input("Free Upload Limit/mo", value=remote.get("free_upload_limit","3"), key="rc_limit")

            if st.button("💾 Save Core Config", key="save_rc_core", use_container_width=True):
                fields = {
                    "app_version": app_version,
                    "update_url": update_url,
                    "support_whatsapp": support_wa,
                    "premium_price": premium_price,
                    "free_upload_limit": free_upload_limit,
                }
                all_ok = all(fb.set_remote_config(k, v) for k, v in fields.items())
                if all_ok:
                    st.success("✅ Core config pushed to Firebase!")
                else:
                    st.error("Some fields failed. Check Firebase connection.")
            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown("<div class='gh-card'>", unsafe_allow_html=True)
            st.markdown("#### 🧩 Custom Logic / Feature Flags")

            feature_flags = st.text_area(
                "Feature Flags (JSON)",
                value=remote.get("feature_flags", '{\n  "video_upload": true,\n  "tiktok_connect": true,\n  "ai_hashtags": true\n}'),
                height=140,
                key="rc_flags"
            )
            custom_announcement = st.text_area(
                "Popup Announcement (leave blank to hide)",
                value=remote.get("popup_announcement",""),
                height=80,
                key="rc_popup",
                placeholder="🎉 New feature launched! Check the Video tab."
            )

            if st.button("💾 Save Feature Config", key="save_rc_feat", use_container_width=True):
                ok1 = fb.set_remote_config("feature_flags", feature_flags)
                ok2 = fb.set_remote_config("popup_announcement", custom_announcement)
                if ok1 and ok2:
                    st.success("✅ Feature flags pushed!")
                else:
                    st.error("Firebase write failed.")
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='gh-card'>", unsafe_allow_html=True)
        st.markdown("#### 📡 Firebase Live Preview")
        if st.button("🔄 Fetch Live Remote Config", key="fetch_rc"):
            live = fb.get_remote_config()
            if live:
                st.json(live)
            else:
                st.warning("Could not reach Firebase. Check secrets.")
        st.markdown("</div>", unsafe_allow_html=True)


# ─── URL PARSE FIX ────────────────────────────────────────────────────────────
try:
    import urllib.parse
except ImportError:
    pass

# ─── ENTRY POINT ──────────────────────────────────────────────────────────────
def main():
    init_db()
    if "admin_logged_in" not in st.session_state:
        st.session_state.admin_logged_in = False

    if not st.session_state.admin_logged_in:
        render_login()
    else:
        render_admin_dashboard()

if __name__ == "__main__":
    main()
