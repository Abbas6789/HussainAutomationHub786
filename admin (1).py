"""
admin.py  — PRIVATE ADMIN PANEL
Hussain Automation Hub · Run: streamlit run admin.py
All files are in the same root directory — no subfolders needed.
"""
import os, hashlib, json
from datetime import datetime

import streamlit as st

st.set_page_config(
    page_title="HAH · Admin Panel",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Root-level imports (no shared/ prefix) ────────────────────────────────────
from styles         import inject_global_css, whatsapp_button, brand_header
from firebase_utils import (
    get_db, get_user, upsert_user, get_all_users, approve_user,
    get_settings, save_settings, get_balance, set_balance,
    get_system_message, set_system_message,
    get_platform_toggles, set_platform_toggles,
)

inject_global_css(accent="#ff6584")

ADMIN_EMAIL   = "ashkeel"
ADMIN_PW_HASH = "76d56d9fa01cefa10eb5b1c1e76ecf7b0643929b6d5f358dfd95f7572295ed09"
SALT          = "hussain_hub_salt_786"

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

db = get_db()


# ════════════════════════════════════════════════════════════════════════════════
#  LOGIN
# ════════════════════════════════════════════════════════════════════════════════
def admin_login():
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("""
        <div style='padding:2rem 0 1rem;text-align:center;'>
          <div style='font-size:3rem;'>🔐</div>
          <h2 style='font-family:Syne,sans-serif;font-weight:800;'>Admin Panel</h2>
          <p style='color:var(--muted);font-size:0.8rem;'>
            Hussain Automation Hub · Private Access
          </p>
        </div>""", unsafe_allow_html=True)

        with st.form("login"):
            username = st.text_input("Username", placeholder="ashkeel")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("🔐 Sign In", use_container_width=True):
                ph = hashlib.sha256((SALT + password).encode()).hexdigest()
                if username == ADMIN_EMAIL and ph == ADMIN_PW_HASH:
                    st.session_state.admin_logged_in = True
                    st.rerun()
                else:
                    st.error("Invalid credentials.")

        st.markdown("""
        <p style='text-align:center;color:var(--muted);font-size:0.72rem;margin-top:1rem;'>
          🔒 Authorized administrators only.
        </p>""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ════════════════════════════════════════════════════════════════════════════════
def admin_sidebar():
    with st.sidebar:
        brand_header("ADMIN PANEL")
        st.markdown('<span class="badge-red" style="font-size:0.7rem;">PRIVATE ACCESS</span>',
                    unsafe_allow_html=True)
        st.markdown("---")
        nav = st.radio("", [
            "📊 Dashboard",
            "👥 User Management",
            "💰 Balance / Funds",
            "⚙️ API Keys",
            "🔧 Platform Toggles",
            "📝 System Messages",
            "🔄 Force Refresh",
            "📜 Audit Log",
        ], label_visibility="collapsed")
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.admin_logged_in = False
            st.rerun()
        st.markdown(f"""
        <p style='font-size:0.7rem;color:var(--muted);margin-top:1rem;'>
          Logged in as <b>{ADMIN_EMAIL}</b><br>
          {datetime.now().strftime('%d %b %Y, %H:%M')}
        </p>""", unsafe_allow_html=True)
    return nav


# ════════════════════════════════════════════════════════════════════════════════
#  DASHBOARD
# ════════════════════════════════════════════════════════════════════════════════
def tab_dashboard():
    brand_header("ADMIN DASHBOARD")
    users    = get_all_users(db) if db else []
    settings = get_settings(db) if db else {}

    m1,m2,m3,m4 = st.columns(4)
    m1.metric("👥 Total Users",      len(users))
    m2.metric("✅ Approved",          len([u for u in users if u.get("approved")]))
    m3.metric("⏳ Pending",           len([u for u in users if not u.get("approved")]))
    m4.metric("🔑 APIs Configured",  sum(1 for k in ["youtube_api_key","facebook_token","tiktok_api_key"]
                                         if settings.get(k)))
    st.markdown("---")

    if not db:
        st.warning("⚠️ **Firebase not connected.** Add `firebase_credentials.json` to the root folder, "
                   "or set `FIREBASE_CREDENTIALS` in Streamlit Cloud Secrets.")
    else:
        st.success("✅ Firebase Firestore connected — real-time sync active.")

    pending = [u for u in users if not u.get("approved")]
    if pending:
        st.markdown("### ⏳ Pending Approvals")
        for u in pending:
            c1,c2,c3 = st.columns([3,2,1])
            c1.write(u.get("email","?"))
            c2.write(u.get("name","?"))
            if c3.button("✅ Approve", key=f"appr_{u.get('email')}"):
                approve_user(db, u["email"], True)
                st.rerun()


# ════════════════════════════════════════════════════════════════════════════════
#  USER MANAGEMENT
# ════════════════════════════════════════════════════════════════════════════════
def tab_users():
    st.markdown("<h2 style='font-family:Syne,sans-serif;'>👥 User Management</h2>",
                unsafe_allow_html=True)
    users = get_all_users(db) if db else []

    with st.expander("➕ Add Manual User"):
        with st.form("add_user"):
            nu_email    = st.text_input("Email")
            nu_name     = st.text_input("Name")
            nu_pass     = st.text_input("Password", type="password")
            nu_bal      = st.number_input("Initial Balance (PKR)", value=0.0)
            nu_approved = st.checkbox("Approve immediately", value=True)
            if st.form_submit_button("Add User"):
                if nu_email and nu_name and nu_pass:
                    pw_hash = hashlib.sha256((SALT + nu_pass).encode()).hexdigest()
                    upsert_user(db, nu_email, {
                        "email": nu_email, "name": nu_name,
                        "password_hash": pw_hash, "balance": nu_bal,
                        "approved": nu_approved,
                        "status": "active" if nu_approved else "pending",
                        "provider": "manual",
                        "created_at": datetime.utcnow().isoformat(),
                        "device_approved": nu_approved,
                    })
                    st.success(f"User {nu_email} added.")
                    st.rerun()

    st.markdown("---")
    if not users:
        st.info("No users found.")
        return

    for u in users:
        with st.expander(f"{'✅' if u.get('approved') else '⏳'} {u.get('email','?')} — {u.get('name','?')}"):
            c1,c2,c3 = st.columns(3)
            with c1:
                if u.get("picture"):
                    st.markdown(f'<img src="{u["picture"]}" style="width:48px;border-radius:50%;">',
                                unsafe_allow_html=True)
                st.write(f"**Provider:** {u.get('provider','?')}")
                st.write(f"**Joined:** {u.get('created_at','?')[:10]}")
            with c2:
                approved = st.checkbox("Approved",        value=u.get("approved",False),        key=f"ap_{u.get('email')}")
                device   = st.checkbox("Device Approved", value=u.get("device_approved",False), key=f"dv_{u.get('email')}")
            with c3:
                bal = st.number_input("Balance (PKR)", value=float(u.get("balance",0)), key=f"bl_{u.get('email')}")
                if st.button("💾 Save", key=f"sv_{u.get('email')}"):
                    upsert_user(db, u["email"], {
                        "approved": approved, "device_approved": device,
                        "balance": bal, "status": "active" if approved else "pending",
                    })
                    st.success("Saved!")
                    st.rerun()
            if st.button("🗑️ Delete", key=f"dl_{u.get('email')}"):
                if db:
                    from firebase_utils import _key
                    db.collection("users").document(_key(u["email"])).delete()
                st.rerun()


# ════════════════════════════════════════════════════════════════════════════════
#  BALANCE
# ════════════════════════════════════════════════════════════════════════════════
def tab_balance():
    st.markdown("<h2 style='font-family:Syne,sans-serif;'>💰 Balance & Funds Manager</h2>",
                unsafe_allow_html=True)
    users = get_all_users(db) if db else []
    if not users:
        st.info("No users found.")
        return

    st.markdown("### Live Balances")
    for u in users:
        c1,c2,c3,c4 = st.columns([3,2,2,1])
        c1.write(u.get("email","?"))
        c2.write(u.get("name","?"))
        new_bal = c3.number_input("PKR", value=float(u.get("balance",0)),
                                  key=f"nb_{u.get('email')}", label_visibility="collapsed")
        if c4.button("Set", key=f"sb_{u.get('email')}"):
            set_balance(db, u["email"], new_bal)
            st.success("Updated!")
            st.rerun()

    st.markdown("---")
    with st.form("bulk"):
        add_amt = st.number_input("Add PKR to ALL users", value=0.0, min_value=0.0)
        if st.form_submit_button("💰 Add to All"):
            for u in users:
                set_balance(db, u["email"], float(u.get("balance",0)) + add_amt)
            st.success(f"Added PKR {add_amt} to all users.")
            st.rerun()


# ════════════════════════════════════════════════════════════════════════════════
#  API KEYS
# ════════════════════════════════════════════════════════════════════════════════
def tab_api_keys():
    st.markdown("<h2 style='font-family:Syne,sans-serif;'>⚙️ API Key Management</h2>",
                unsafe_allow_html=True)
    settings = get_settings(db) if db else {}

    with st.form("api"):
        st.markdown("#### 📱 Social Media")
        fb  = st.text_input("Facebook Access Token",  value=settings.get("facebook_token",""),  type="password")
        yt  = st.text_input("YouTube API Key",        value=settings.get("youtube_api_key",""), type="password")
        tt  = st.text_input("TikTok API Key",         value=settings.get("tiktok_api_key",""),  type="password")
        st.markdown("#### 🤖 AI")
        ant = st.text_input("Anthropic API Key",      value=settings.get("anthropic_api_key",""), type="password")
        if st.form_submit_button("💾 Save All Keys", use_container_width=True):
            save_settings(db, {
                "facebook_token":    fb,
                "youtube_api_key":   yt,
                "tiktok_api_key":    tt,
                "anthropic_api_key": ant,
            })
            st.success("✅ Keys saved to Firestore — public app will use them instantly.")


# ════════════════════════════════════════════════════════════════════════════════
#  PLATFORM TOGGLES
# ════════════════════════════════════════════════════════════════════════════════
def tab_toggles():
    st.markdown("<h2 style='font-family:Syne,sans-serif;'>🔧 Platform Feature Toggles</h2>",
                unsafe_allow_html=True)
    st.info("Changes apply to the public app instantly via Firestore.")
    toggles = get_platform_toggles(db) if db else {"youtube":True,"facebook":True,"tiktok":True}

    yt_on = st.toggle("▶️ YouTube Shorts",  value=toggles.get("youtube",True))
    fb_on = st.toggle("📘 Facebook Reels",  value=toggles.get("facebook",True))
    tt_on = st.toggle("🎵 TikTok",          value=toggles.get("tiktok",True))

    if st.button("💾 Save Toggles", use_container_width=True):
        set_platform_toggles(db, {"youtube":yt_on,"facebook":fb_on,"tiktok":tt_on})
        st.success("✅ Toggles saved — live immediately.")


# ════════════════════════════════════════════════════════════════════════════════
#  SYSTEM MESSAGES
# ════════════════════════════════════════════════════════════════════════════════
def tab_messages():
    st.markdown("<h2 style='font-family:Syne,sans-serif;'>📝 System Messages</h2>",
                unsafe_allow_html=True)
    current = get_system_message(db) if db else "Welcome to Hussain Automation Hub!"
    new_msg = st.text_area("Announcement / System Message", value=current, height=130)
    if st.button("📢 Publish Message", use_container_width=True):
        set_system_message(db, new_msg)
        st.success("✅ Live on public site immediately.")

    st.markdown("---")
    st.markdown("### 🚧 Maintenance Mode")
    settings = get_settings(db) if db else {}
    maint = st.toggle("Enable Maintenance Mode", value=settings.get("maintenance_mode",False))
    if st.button("Save Maintenance Status"):
        save_settings(db, {"maintenance_mode": maint})
        st.success("Saved.")


# ════════════════════════════════════════════════════════════════════════════════
#  FORCE REFRESH
# ════════════════════════════════════════════════════════════════════════════════
def tab_refresh():
    st.markdown("<h2 style='font-family:Syne,sans-serif;'>🔄 Force Refresh / System Reset</h2>",
                unsafe_allow_html=True)
    st.warning("These actions affect the public site. Use with care.")

    c1,c2,c3 = st.columns(3)
    with c1:
        st.markdown("<div class='hub-card' style='text-align:center;'><div style='font-size:2rem;'>🔄</div>"
                    "<h4 style='font-family:Syne,sans-serif;'>Force Refresh</h4>"
                    "<p style='font-size:0.78rem;color:var(--muted);'>Push refresh signal to public app.</p>"
                    "</div>", unsafe_allow_html=True)
        if st.button("🔄 Force Refresh", use_container_width=True):
            save_settings(db, {"force_refresh_ts": datetime.utcnow().isoformat()})
            st.success("✅ Signal sent.")
    with c2:
        st.markdown("<div class='hub-card' style='text-align:center;'><div style='font-size:2rem;'>🗑️</div>"
                    "<h4 style='font-family:Syne,sans-serif;'>Clear Cache</h4>"
                    "<p style='font-size:0.78rem;color:var(--muted);'>Reload all settings from Firestore.</p>"
                    "</div>", unsafe_allow_html=True)
        if st.button("🗑️ Clear Cache", use_container_width=True):
            st.cache_data.clear()
            save_settings(db, {"cache_cleared_ts": datetime.utcnow().isoformat()})
            st.success("✅ Cache cleared.")
    with c3:
        st.markdown("<div class='hub-card' style='text-align:center;'><div style='font-size:2rem;'>🔒</div>"
                    "<h4 style='font-family:Syne,sans-serif;'>Emergency Lock</h4>"
                    "<p style='font-size:0.78rem;color:var(--muted);'>Lock ALL users out instantly.</p>"
                    "</div>", unsafe_allow_html=True)
        if st.button("🔒 Lock Public App", use_container_width=True):
            save_settings(db, {"maintenance_mode":True,"lock_reason":"Admin emergency lock."})
            st.success("🔒 Public app locked.")


# ════════════════════════════════════════════════════════════════════════════════
#  AUDIT LOG
# ════════════════════════════════════════════════════════════════════════════════
def tab_audit():
    st.markdown("<h2 style='font-family:Syne,sans-serif;'>📜 Audit Log</h2>",
                unsafe_allow_html=True)
    s = get_settings(db) if db else {}
    rows = [
        ("Last Settings Update",  s.get("updated_at","—")),
        ("Last Force Refresh",    s.get("force_refresh_ts","—")),
        ("Last Cache Clear",      s.get("cache_cleared_ts","—")),
        ("Maintenance Mode",      str(s.get("maintenance_mode",False))),
        ("Lock Reason",           s.get("lock_reason","—")),
    ]
    for label, val in rows:
        c1,c2 = st.columns([2,3])
        c1.markdown(f"**{label}**")
        c2.markdown(f"`{val}`")


# ════════════════════════════════════════════════════════════════════════════════
#  ROUTER
# ════════════════════════════════════════════════════════════════════════════════
if not st.session_state.admin_logged_in:
    admin_login()
else:
    nav = admin_sidebar()
    if   "Dashboard"  in nav: tab_dashboard()
    elif "User"       in nav: tab_users()
    elif "Balance"    in nav: tab_balance()
    elif "API Keys"   in nav: tab_api_keys()
    elif "Platform"   in nav: tab_toggles()
    elif "Messages"   in nav: tab_messages()
    elif "Refresh"    in nav: tab_refresh()
    elif "Audit"      in nav: tab_audit()
