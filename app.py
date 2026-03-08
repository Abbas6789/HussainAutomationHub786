"""
app.py — PUBLIC USER PORTAL
Hussain Automation Hub · Social Media Automation
Run: streamlit run app.py
"""
import sys, os, json, tempfile, time
from pathlib import Path
from datetime import datetime

# Allow shared imports
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Hussain Automation Hub",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

from shared.styles import inject_global_css, whatsapp_button, brand_header
from shared.firebase_utils import (
    get_db, get_user, upsert_user, get_settings,
    get_balance, get_system_message, get_platform_toggles,
)
from shared.ai_meta import generate_metadata_ai
from shared.uploaders import upload_youtube, upload_facebook, upload_tiktok, process_video_ffmpeg

inject_global_css()

GOOGLE_CLIENT_ID = "249087096220-dkg4b73rq7s5sqji0fq8p6n42h1lvvq4.apps.googleusercontent.com"

# ── Session defaults ──────────────────────────────────────────────────────────
for k, v in {
    "user": None,
    "upload_logs": [],
    "meta": {},
    "page": "home",
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

db = get_db()

# ════════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════════════════════════════

def handle_google_login(token_info: dict):
    """Called after Google OAuth returns user info."""
    email = token_info.get("email", "")
    if not email:
        st.error("Could not retrieve email from Google.")
        return

    db_user = get_user(db, email)
    if not db_user:
        # New user — create pending record
        upsert_user(db, email, {
            "email": email,
            "name": token_info.get("name", email.split("@")[0]),
            "picture": token_info.get("picture", ""),
            "provider": "google",
            "status": "pending",
            "approved": False,
            "balance": 0.0,
            "created_at": datetime.utcnow().isoformat(),
            "device_approved": False,
        })
        st.warning("⏳ Your account is pending admin approval. Please contact support.")
        whatsapp_button("💬 Contact Admin for Approval")
        return

    if not db_user.get("approved", False):
        st.warning("⏳ Your account is pending admin approval.")
        whatsapp_button("💬 Contact Admin for Approval")
        return

    st.session_state.user = {
        "email": email,
        "name":  db_user.get("name", email),
        "picture": db_user.get("picture", ""),
        "balance": db_user.get("balance", 0.0),
    }
    st.session_state.page = "dashboard"
    st.rerun()


# ════════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ════════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    brand_header("PUBLIC PORTAL")
    st.markdown("---")

    if st.session_state.user:
        u = st.session_state.user
        pic = u.get("picture", "")
        if pic:
            st.markdown(f'<img class="avatar" src="{pic}" style="width:52px;height:52px;margin-bottom:8px;">', unsafe_allow_html=True)
        st.markdown(f"**{u['name']}**")
        st.markdown(f"<span style='color:var(--muted);font-size:0.75rem;'>{u['email']}</span>", unsafe_allow_html=True)
        st.markdown("---")

        # Live balance from Firestore
        live_bal = get_balance(db, u["email"]) if db else u.get("balance", 0.0)
        st.metric("💰 Account Balance", f"PKR {live_bal:,.2f}")
        st.markdown("---")

        nav = st.radio("Navigation", ["🏠 Dashboard", "📤 Upload & Post", "📊 History", "👤 Profile"],
                       label_visibility="collapsed")
        st.markdown("---")
        whatsapp_button("💬 Support")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.user = None
            st.session_state.page = "home"
            st.rerun()
    else:
        nav = "home"
        st.markdown("""
        <p style='font-size:0.78rem;color:var(--muted);line-height:1.6;'>
        Welcome to Hussain Automation Hub.<br>
        Please log in to access the automation tools.
        </p>
        """, unsafe_allow_html=True)
        st.markdown("---")
        whatsapp_button("💬 Support / Contact Admin")

# ════════════════════════════════════════════════════════════════════════════════
#  HOME / LOGIN PAGE
# ════════════════════════════════════════════════════════════════════════════════
def page_home():
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        brand_header("SOCIAL MEDIA AUTOMATION PLATFORM")
        st.markdown("---")

        # System message from Firestore
        sys_msg = get_system_message(db) if db else "Welcome! Log in to automate your social media presence."
        st.info(f"📢 {sys_msg}")
        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("""
        <div class='hub-card' style='text-align:center;'>
          <div style='font-size:2.5rem;margin-bottom:0.5rem;'>⚡</div>
          <h2 style='font-family:Syne,sans-serif;font-size:1.6rem;margin:0 0 0.5rem;'>
            One Upload.<br>Every Platform.
          </h2>
          <p style='color:var(--muted);font-size:0.85rem;'>
            Post to YouTube Shorts, Facebook Reels, and TikTok simultaneously
            with AI-generated titles and hashtags.
          </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Google Login Button
        st.markdown("""
        <p style='text-align:center;color:var(--muted);font-size:0.8rem;margin-bottom:0.8rem;'>
          Sign in with your Google account to get started
        </p>
        """, unsafe_allow_html=True)

        # Google One Tap / OAuth via JS component
        google_login_html = f"""
        <script src="https://accounts.google.com/gsi/client" async defer></script>
        <div id="g_id_onload"
             data-client_id="{GOOGLE_CLIENT_ID}"
             data-context="signin"
             data-ux_mode="popup"
             data-callback="handleCredentialResponse"
             data-auto_prompt="false">
        </div>
        <div class="g_id_signin"
             data-type="standard"
             data-shape="rectangular"
             data-theme="filled_black"
             data-text="sign_in_with"
             data-size="large"
             data-logo_alignment="left"
             style="display:flex;justify-content:center;margin:1rem 0;">
        </div>
        <script>
        function handleCredentialResponse(response) {{
            const payload = JSON.parse(atob(response.credential.split('.')[1]));
            const params = new URLSearchParams(payload);
            window.parent.postMessage({{type:'google_login', payload: payload}}, '*');
        }}
        </script>
        """
        st.components.v1.html(google_login_html, height=90)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Manual email login fallback
        with st.expander("🔐 Or log in with Email / Password"):
            email_in = st.text_input("Email", placeholder="you@email.com", key="login_email")
            pass_in  = st.text_input("Password", type="password", key="login_pass")
            if st.button("Log In", use_container_width=True, key="btn_login"):
                if email_in and pass_in:
                    db_user = get_user(db, email_in) if db else None
                    if db_user:
                        stored_hash = db_user.get("password_hash", "")
                        import hashlib
                        attempt_hash = hashlib.sha256(("hussain_hub_salt_786" + pass_in).encode()).hexdigest()
                        if stored_hash and stored_hash == attempt_hash:
                            if not db_user.get("approved", False):
                                st.warning("⏳ Account pending admin approval.")
                                whatsapp_button("Contact Admin")
                            else:
                                st.session_state.user = {
                                    "email": email_in,
                                    "name": db_user.get("name", email_in),
                                    "picture": db_user.get("picture", ""),
                                    "balance": db_user.get("balance", 0.0),
                                }
                                st.session_state.page = "dashboard"
                                st.rerun()
                        else:
                            st.error("Invalid credentials.")
                    else:
                        if not db:
                            st.warning("⚠️ Firebase not connected. Set up credentials first.")
                        else:
                            st.error("No account found. Please contact admin.")
                else:
                    st.warning("Enter email and password.")

        st.markdown("---")
        st.markdown("""
        <div style='text-align:center;'>
          <p style='color:var(--muted);font-size:0.75rem;'>
            New user? After login, your account requires <b>admin approval</b> before access is granted.
          </p>
        </div>
        """, unsafe_allow_html=True)
        whatsapp_button("💬 Need help? Contact Admin")


# ════════════════════════════════════════════════════════════════════════════════
#  DASHBOARD
# ════════════════════════════════════════════════════════════════════════════════
def page_dashboard():
    u = st.session_state.user
    toggles = get_platform_toggles(db) if db else {"youtube": True, "facebook": True, "tiktok": True}

    # Header with avatar
    hcol1, hcol2, hcol3 = st.columns([3, 1, 1])
    with hcol1:
        brand_header(f"WELCOME BACK, {u['name'].upper()}")
    with hcol2:
        if u.get("picture"):
            st.markdown(f'<img class="avatar" src="{u["picture"]}" style="width:48px;height:48px;margin-top:1.5rem;">', unsafe_allow_html=True)
    with hcol3:
        st.markdown("<div style='margin-top:1.5rem;'>", unsafe_allow_html=True)
        whatsapp_button("💬 Support")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    # Live metrics
    live_bal = get_balance(db, u["email"]) if db else 0.0
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("💰 Balance",        f"PKR {live_bal:,.2f}")
    m2.metric("📤 Posts Today",    len([l for l in st.session_state.upload_logs if l.get("ok")]))
    m3.metric("📡 Active Platforms", sum(1 for v in toggles.values() if v))
    m4.metric("🏷️ AI Hashtags",    "30 auto")

    st.markdown("---")

    # Platform status badges
    pcol1, pcol2, pcol3 = st.columns(3)
    for col, name, key, icon in [
        (pcol1, "YouTube", "youtube",  "▶️"),
        (pcol2, "Facebook","facebook", "📘"),
        (pcol3, "TikTok",  "tiktok",   "🎵"),
    ]:
        badge = "badge-green" if toggles.get(key) else "badge-red"
        status = "ACTIVE" if toggles.get(key) else "DISABLED BY ADMIN"
        col.markdown(f"""
        <div class='hub-card' style='text-align:center;'>
          <div style='font-size:2rem;'>{icon}</div>
          <div style='font-weight:700;margin:4px 0;'>{name}</div>
          <span class='{badge}'>{status}</span>
        </div>
        """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════════
#  UPLOAD & POST PAGE
# ════════════════════════════════════════════════════════════════════════════════
def page_upload():
    st.markdown("<h2 style='font-family:Syne,sans-serif;'>📤 Upload & Post Everywhere</h2>", unsafe_allow_html=True)

    settings   = get_settings(db) if db else {}
    toggles    = get_platform_toggles(db) if db else {"youtube": True, "facebook": True, "tiktok": True}
    anthropic_key = settings.get("anthropic_api_key", os.getenv("ANTHROPIC_API_KEY",""))

    uploaded = st.file_uploader("Drop your video (MP4, MOV, AVI)", type=["mp4","mov","avi","mkv"])

    if not uploaded:
        st.markdown("""
        <div class='hub-card' style='text-align:center;padding:3rem;'>
          <div style='font-size:3rem;'>🎬</div>
          <p style='color:var(--muted);'>Upload a video above to get started.<br>
          AI will automatically generate your title, description, and hashtags.</p>
        </div>
        """, unsafe_allow_html=True)
        return

    left, right = st.columns([3, 2], gap="large")

    with left:
        st.video(uploaded)

        # Auto-generate metadata
        if not st.session_state.meta or st.session_state.meta.get("_file") != uploaded.name:
            with st.spinner("🤖 AI is generating your title, description & hashtags…"):
                meta = generate_metadata_ai(uploaded.name, anthropic_key)
                meta["_file"] = uploaded.name
                st.session_state.meta = meta
            st.success("✅ AI metadata generated!")

        meta = st.session_state.meta
        title  = st.text_input("Title (AI-generated, editable)", value=meta.get("title",""))
        desc   = st.text_area("Description", value=meta.get("description",""), height=90)
        tags   = meta.get("hashtags", [])
        st.text_area("Hashtags (AI-generated)", value=" ".join(tags), height=70)

        if st.button("🔄 Regenerate Metadata"):
            st.session_state.meta = {}
            st.rerun()

    with right:
        st.markdown("""
        <div class='hub-card'>
          <h4 style='font-family:Syne,sans-serif;margin-top:0;'>🎯 Platform Selection</h4>
        """, unsafe_allow_html=True)

        post_yt = st.checkbox("▶️ YouTube Shorts",  value=toggles.get("youtube",  True), disabled=not toggles.get("youtube",  True))
        post_fb = st.checkbox("📘 Facebook Reels",  value=toggles.get("facebook", True), disabled=not toggles.get("facebook", True))
        post_tt = st.checkbox("🎵 TikTok",          value=toggles.get("tiktok",   True), disabled=not toggles.get("tiktok",   True))

        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        # API keys from Firestore settings
        yt_key  = settings.get("youtube_api_key",  os.getenv("YOUTUBE_API_KEY",""))
        fb_tok  = settings.get("facebook_token",   os.getenv("FACEBOOK_ACCESS_TOKEN",""))
        tt_key  = settings.get("tiktok_api_key",   os.getenv("TIKTOK_API_KEY",""))

        active_platforms = []
        if post_yt and toggles.get("youtube"):  active_platforms.append("YouTube")
        if post_fb and toggles.get("facebook"): active_platforms.append("Facebook")
        if post_tt and toggles.get("tiktok"):   active_platforms.append("TikTok")

        if not active_platforms:
            st.warning("Select at least one platform.")
        else:
            st.markdown(f"""
            <div style='background:rgba(108,99,255,0.1);border:1px solid rgba(108,99,255,0.3);
                        border-radius:8px;padding:0.8rem 1rem;margin-bottom:1rem;font-size:0.82rem;'>
              Ready to post to: <b>{', '.join(active_platforms)}</b>
            </div>
            """, unsafe_allow_html=True)

            if st.button("🚀  POST EVERYWHERE", use_container_width=True):
                caption = f"{title}\n\n{desc}\n\n{' '.join(tags)}"
                logs = []

                with tempfile.TemporaryDirectory() as tmp:
                    tmp_p = Path(tmp)
                    src = tmp_p / uploaded.name
                    src.write_bytes(uploaded.getvalue())

                    prog = st.progress(0)
                    stat = st.empty()
                    total = len(active_platforms)

                    for i, plat in enumerate(active_platforms):
                        stat.markdown(f"**{plat}** — processing video…")
                        proc = process_video_ffmpeg(src, tmp_p, plat)
                        stat.markdown(f"**{plat}** — uploading…")

                        if plat == "YouTube":
                            res = upload_youtube(proc, title, desc, tags, yt_key)
                        elif plat == "Facebook":
                            res = upload_facebook(proc, title, desc, tags, fb_tok)
                        else:
                            res = upload_tiktok(proc, title, desc, tags, tt_key)

                        res["ts"] = datetime.now().strftime("%H:%M:%S")
                        logs.append(res)
                        prog.progress((i+1)/total)

                stat.empty(); prog.empty()
                for log in logs:
                    if log["ok"]:
                        st.success(f"✅ **{log['platform']}** posted successfully at {log['ts']}")
                    else:
                        st.error(f"❌ **{log['platform']}** — {log.get('error')}")

                st.session_state.upload_logs.extend(logs)


# ════════════════════════════════════════════════════════════════════════════════
#  HISTORY PAGE
# ════════════════════════════════════════════════════════════════════════════════
def page_history():
    st.markdown("<h2 style='font-family:Syne,sans-serif;'>📊 Upload History</h2>", unsafe_allow_html=True)
    if not st.session_state.upload_logs:
        st.info("No posts yet. Upload a video to get started.")
        return
    for log in reversed(st.session_state.upload_logs):
        icon  = "✅" if log["ok"] else "❌"
        color = "#43e97b" if log["ok"] else "#ff6584"
        st.markdown(f"""
        <div class='hub-card' style='display:flex;justify-content:space-between;align-items:center;'>
          <span>{icon} <b style='color:{color};'>{log.get("platform","?")}</b></span>
          <span style='color:var(--muted);font-size:0.8rem;'>{log.get("ts","")}</span>
          <span style='color:var(--muted);font-size:0.78rem;'>
            {log.get("error","") if not log["ok"] else log.get("video_id",log.get("publish_id","ok"))}
          </span>
        </div>
        """, unsafe_allow_html=True)
    if st.button("🗑️ Clear History"):
        st.session_state.upload_logs = []
        st.rerun()


# ════════════════════════════════════════════════════════════════════════════════
#  PROFILE PAGE
# ════════════════════════════════════════════════════════════════════════════════
def page_profile():
    u = st.session_state.user
    st.markdown("<h2 style='font-family:Syne,sans-serif;'>👤 My Profile</h2>", unsafe_allow_html=True)
    col1, col2 = st.columns([1, 3])
    with col1:
        if u.get("picture"):
            st.markdown(f'<img src="{u["picture"]}" style="width:120px;height:120px;border-radius:50%;border:3px solid var(--accent);">', unsafe_allow_html=True)
    with col2:
        st.markdown(f"### {u['name']}")
        st.markdown(f"📧 `{u['email']}`")
        live_bal = get_balance(db, u["email"]) if db else 0.0
        st.metric("💰 Live Balance", f"PKR {live_bal:,.2f}")
        db_user = get_user(db, u["email"]) if db else {}
        if db_user:
            status = db_user.get("status", "active")
            badge  = "badge-green" if status == "active" else "badge-yellow"
            st.markdown(f'Account Status: <span class="{badge}">{status.upper()}</span>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════════
#  ROUTER
# ════════════════════════════════════════════════════════════════════════════════
if not st.session_state.user:
    page_home()
else:
    if "nav" in dir() or True:
        try:
            page = nav if "nav" in locals() else "🏠 Dashboard"
        except:
            page = "🏠 Dashboard"

        if "Upload" in str(page):
            page_upload()
        elif "History" in str(page):
            page_history()
        elif "Profile" in str(page):
            page_profile()
        else:
            page_dashboard()
