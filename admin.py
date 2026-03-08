"""
admin.py — PRIVATE ADMIN PANEL
Hussain Automation Hub · Admin Controls
Run: streamlit run admin.py
"""
import sys, os, hashlib, json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

st.set_page_config(
    page_title="HAH · Admin Panel",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded",
)

from shared.styles import inject_global_css, whatsapp_button, brand_header
from shared.firebase_utils import (
    get_db, get_user, upsert_user, get_all_users, approve_user,
    get_settings, save_settings, get_balance, set_balance,
    get_system_message, set_system_message,
    get_platform_toggles, set_platform_toggles,
)

inject_global_css(accent="#ff6584")  # Red accent for admin

# ── Admin credentials (hashed) ────────────────────────────────────────────────
ADMIN_EMAIL    = "ashkeel"
ADMIN_PW_HASH  = "76d56d9fa01cefa10eb5b1c1e76ecf7b0643929b6d5f358dfd95f7572295ed09"
SALT           = "hussain_hub_salt_786"

# ── Session ───────────────────────────────────────────────────────────────────
if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

db = get_db()


# ════════════════════════════════════════════════════════════════════════════════
#  LOGIN PAGE
# ════════════════════════════════════════════════════════════════════════════════
def admin_login():
    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        st.markdown("""
        <div style='padding:2rem 0 1rem;text-align:center;'>
          <div style='font-size:3rem;'>🔐</div>
          <h2 style='font-family:Syne,sans-serif;font-weight:800;'>Admin Panel</h2>
          <p style='color:var(--muted);font-size:0.8rem;'>Hussain Automation Hub · Private Access</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("admin_login_form"):
            username = st.text_input("Username", placeholder="ashkeel")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("🔐 Sign In", use_container_width=True)

        if submitted:
            pw_hash = hashlib.sha256((SALT + password).encode()).hexdigest()
            if username == ADMIN_EMAIL and pw_hash == ADMIN_PW_HASH:
                st.session_state.admin_logged_in = True
                st.rerun()
            else:
                st.error("Invalid credentials.")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <p style='text-align:center;color:var(--muted);font-size:0.72rem;'>
          🔒 This panel is for authorized administrators only.
        </p>
        """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ════════════════════════════════════════════════════════════════════════════════
def admin_sidebar():
    with st.sidebar:
        brand_header("ADMIN PANEL")
        st.markdown("""
        <span class='badge-red' style='font-size:0.7rem;'>PRIVATE ACCESS</span>
        """, unsafe_allow_html=True)
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

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"""
        <p style='font-size:0.7rem;color:var(--muted);'>
          Logged in as <b>{ADMIN_EMAIL}</b><br>
          {datetime.now().strftime('%d %b %Y, %H:%M')}
        </p>
        """, unsafe_allow_html=True)

    return nav


# ════════════════════════════════════════════════════════════════════════════════
#  DASHBOARD
# ════════════════════════════════════════════════════════════════════════════════
def tab_dashboard():
    brand_header("ADMIN DASHBOARD")

    users  = get_all_users(db) if db else []
    approved = [u for u in users if u.get("approved")]
    pending  = [u for u in users if not u.get("approved")]
    settings = get_settings(db) if db else {}

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("👥 Total Users",    len(users))
    m2.metric("✅ Approved",       len(approved))
    m3.metric("⏳ Pending",        len(pending))
    m4.metric("🔑 APIs Configured", sum(1 for k in ["youtube_api_key","facebook_token","tiktok_api_key"] if settings.get(k)))

    st.markdown("---")

    if not db:
        st.warning("""
        ⚠️ **Firebase not connected.** All data is simulated.
        To enable real-time sync, add your `firebase_credentials.json`
        to the project root, or set the `FIREBASE_CREDENTIALS` environment variable
        in Streamlit Cloud Secrets.
        """)
    else:
        st.success("✅ Firebase Firestore connected — real-time sync active.")

    if pending:
        st.markdown("### ⏳ Pending Approvals")
        for u in pending:
            c1, c2, c3 = st.columns([3, 2, 1])
            c1.write(u.get("email","?"))
            c2.write(u.get("name","?"))
            if c3.button("✅ Approve", key=f"approve_{u.get('email')}"):
                approve_user(db, u["email"], True)
                st.success(f"Approved {u['email']}")
                st.rerun()


# ════════════════════════════════════════════════════════════════════════════════
#  USER MANAGEMENT
# ════════════════════════════════════════════════════════════════════════════════
def tab_users():
    st.markdown("<h2 style='font-family:Syne,sans-serif;'>👥 User Management</h2>", unsafe_allow_html=True)
    users = get_all_users(db) if db else []

    if not users:
        st.info("No users found in database.")
        return

    # Add new manual user
    with st.expander("➕ Add Manual User"):
        with st.form("add_user"):
            nu_email = st.text_input("Email")
            nu_name  = st.text_input("Name")
            nu_pass  = st.text_input("Password", type="password")
            nu_bal   = st.number_input("Initial Balance (PKR)", value=0.0)
            nu_approved = st.checkbox("Approve immediately", value=True)
            if st.form_submit_button("Add User"):
                if nu_email and nu_name and nu_pass:
                    pw_hash = hashlib.sha256((SALT + nu_pass).encode()).hexdigest()
                    upsert_user(db, nu_email, {
                        "email": nu_email, "name": nu_name,
                        "password_hash": pw_hash, "balance": nu_bal,
                        "approved": nu_approved, "status": "active" if nu_approved else "pending",
                        "provider": "manual", "created_at": datetime.utcnow().isoformat(),
                        "device_approved": nu_approved,
                    })
                    st.success(f"User {nu_email} added.")
                    st.rerun()

    st.markdown("---")
    st.markdown(f"**{len(users)} users registered**")

    for u in users:
        with st.expander(f"{'✅' if u.get('approved') else '⏳'} {u.get('email','?')} — {u.get('name','?')}"):
            col1, col2, col3 = st.columns(3)

            with col1:
                if u.get("picture"):
                    st.markdown(f'<img src="{u["picture"]}" style="width:48px;border-radius:50%;">', unsafe_allow_html=True)
                st.write(f"**Provider:** {u.get('provider','?')}")
                st.write(f"**Joined:** {u.get('created_at','?')[:10]}")

            with col2:
                approved = st.checkbox("Approved", value=u.get("approved", False), key=f"appr_{u.get('email')}")
                device   = st.checkbox("Device Approved", value=u.get("device_approved", False), key=f"dev_{u.get('email')}")

            with col3:
                bal = st.number_input("Balance (PKR)", value=float(u.get("balance", 0)), key=f"bal_{u.get('email')}")
                if st.button("💾 Save Changes", key=f"save_{u.get('email')}"):
                    upsert_user(db, u["email"], {
                        "approved": approved, "device_approved": device,
                        "balance": bal, "status": "active" if approved else "pending",
                    })
                    st.success("Saved!")
                    st.rerun()

            if st.button("🗑️ Delete User", key=f"del_{u.get('email')}"):
                if db:
                    db.collection("users").document(u["email"].replace(".","_")).delete()
                st.rerun()


# ════════════════════════════════════════════════════════════════════════════════
#  BALANCE / FUNDS
# ════════════════════════════════════════════════════════════════════════════════
def tab_balance():
    st.markdown("<h2 style='font-family:Syne,sans-serif;'>💰 Balance & Funds Manager</h2>", unsafe_allow_html=True)
    users = get_all_users(db) if db else []

    if not users:
        st.info("No users found.")
        return

    st.markdown("### Live Balances")
    for u in users:
        c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
        c1.write(u.get("email","?"))
        c2.write(u.get("name","?"))
        new_bal = c3.number_input("PKR", value=float(u.get("balance",0)), key=f"b_{u.get('email')}", label_visibility="collapsed")
        if c4.button("Set", key=f"setbal_{u.get('email')}"):
            set_balance(db, u["email"], new_bal)
            st.success(f"Balance updated for {u['email']}")
            st.rerun()

    st.markdown("---")
    st.markdown("### Bulk Add Funds")
    with st.form("bulk_funds"):
        add_amount = st.number_input("Add PKR to ALL users", value=0.0, min_value=0.0)
        if st.form_submit_button("💰 Add to All"):
            for u in users:
                set_balance(db, u["email"], float(u.get("balance",0)) + add_amount)
            st.success(f"Added PKR {add_amount} to all users.")
            st.rerun()


# ════════════════════════════════════════════════════════════════════════════════
#  API KEYS
# ════════════════════════════════════════════════════════════════════════════════
def tab_api_keys():
    st.markdown("<h2 style='font-family:Syne,sans-serif;'>⚙️ API Key Management</h2>", unsafe_allow_html=True)
    st.info("These keys are stored in Firestore and used by the public app automatically.")

    settings = get_settings(db) if db else {}

    with st.form("api_keys_form"):
        st.markdown("#### 📱 Social Media APIs")
        fb_tok  = st.text_input("Facebook Access Token",  value=settings.get("facebook_token",""),  type="password", placeholder="EAAxxxxxxxx…")
        yt_key  = st.text_input("YouTube API Key",        value=settings.get("youtube_api_key",""), type="password", placeholder="AIzaSyxxxxxxxx…")
        tt_key  = st.text_input("TikTok API Key",         value=settings.get("tiktok_api_key",""),  type="password", placeholder="tiktok_xxxxxxxx…")

        st.markdown("#### 🤖 AI Integration")
        ant_key = st.text_input("Anthropic API Key (for AI metadata)", value=settings.get("anthropic_api_key",""), type="password", placeholder="sk-ant-…")

        st.markdown("#### 🔥 Firebase")
        st.markdown("""
        <p style='font-size:0.78rem;color:var(--muted);'>
        Firebase credentials are loaded from <code>firebase_credentials.json</code> or the
        <code>FIREBASE_CREDENTIALS</code> environment variable. Do not paste them here.
        </p>
        """, unsafe_allow_html=True)

        if st.form_submit_button("💾 Save All API Keys", use_container_width=True):
            save_settings(db, {
                "facebook_token":   fb_tok,
                "youtube_api_key":  yt_key,
                "tiktok_api_key":   tt_key,
                "anthropic_api_key": ant_key,
            })
            st.success("✅ All API keys saved to Firestore.")


# ════════════════════════════════════════════════════════════════════════════════
#  PLATFORM TOGGLES
# ════════════════════════════════════════════════════════════════════════════════
def tab_toggles():
    st.markdown("<h2 style='font-family:Syne,sans-serif;'>🔧 Platform Feature Toggles</h2>", unsafe_allow_html=True)
    st.info("Disabling a platform hides it from all users on the public app instantly.")

    toggles = get_platform_toggles(db) if db else {"youtube": True, "facebook": True, "tiktok": True}

    yt_on = st.toggle("▶️ YouTube Shorts",  value=toggles.get("youtube",  True))
    fb_on = st.toggle("📘 Facebook Reels",  value=toggles.get("facebook", True))
    tt_on = st.toggle("🎵 TikTok",          value=toggles.get("tiktok",   True))

    if st.button("💾 Save Toggles", use_container_width=True):
        set_platform_toggles(db, {"youtube": yt_on, "facebook": fb_on, "tiktok": tt_on})
        st.success("✅ Platform toggles updated — changes live instantly.")


# ════════════════════════════════════════════════════════════════════════════════
#  SYSTEM MESSAGES
# ════════════════════════════════════════════════════════════════════════════════
def tab_messages():
    st.markdown("<h2 style='font-family:Syne,sans-serif;'>📝 System Messages & Announcements</h2>", unsafe_allow_html=True)
    st.info("This message appears on the public app's home/login page.")

    current = get_system_message(db) if db else "Welcome to Hussain Automation Hub!"

    new_msg = st.text_area("System / Announcement Message", value=current, height=120)

    if st.button("📢 Publish Message", use_container_width=True):
        set_system_message(db, new_msg)
        st.success("✅ Message updated — visible on public site immediately.")

    st.markdown("---")
    st.markdown("### Maintenance Mode")
    settings = get_settings(db) if db else {}
    maint = st.toggle("🚧 Enable Maintenance Mode", value=settings.get("maintenance_mode", False))
    if st.button("Save Maintenance Status"):
        save_settings(db, {"maintenance_mode": maint})
        st.success("Saved.")


# ════════════════════════════════════════════════════════════════════════════════
#  FORCE REFRESH
# ════════════════════════════════════════════════════════════════════════════════
def tab_refresh():
    st.markdown("<h2 style='font-family:Syne,sans-serif;'>🔄 Force Refresh / System Reset</h2>", unsafe_allow_html=True)
    st.warning("These actions affect the public site. Use with caution.")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div class='hub-card' style='text-align:center;'>
          <div style='font-size:2rem;'>🔄</div>
          <h4 style='font-family:Syne,sans-serif;'>Force Refresh</h4>
          <p style='font-size:0.78rem;color:var(--muted);'>Push a timestamp to Firestore that triggers public app refresh.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🔄 Force Refresh Public App", use_container_width=True):
            save_settings(db, {"force_refresh_ts": datetime.utcnow().isoformat()})
            st.success("✅ Refresh signal sent.")

    with col2:
        st.markdown("""
        <div class='hub-card' style='text-align:center;'>
          <div style='font-size:2rem;'>🗑️</div>
          <h4 style='font-family:Syne,sans-serif;'>Clear Cache</h4>
          <p style='font-size:0.78rem;color:var(--muted);'>Clear all cached settings and reload from Firestore.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🗑️ Clear Settings Cache", use_container_width=True):
            st.cache_data.clear()
            save_settings(db, {"cache_cleared_ts": datetime.utcnow().isoformat()})
            st.success("✅ Cache cleared.")

    with col3:
        st.markdown("""
        <div class='hub-card' style='text-align:center;'>
          <div style='font-size:2rem;'>⚠️</div>
          <h4 style='font-family:Syne,sans-serif;'>Emergency Lock</h4>
          <p style='font-size:0.78rem;color:var(--muted);'>Lock ALL users out of the public app instantly.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🔒 Lock Public App", use_container_width=True):
            save_settings(db, {"maintenance_mode": True, "lock_reason": "Admin initiated emergency lock."})
            st.success("🔒 Public app locked.")


# ════════════════════════════════════════════════════════════════════════════════
#  AUDIT LOG (simulated)
# ════════════════════════════════════════════════════════════════════════════════
def tab_audit():
    st.markdown("<h2 style='font-family:Syne,sans-serif;'>📜 Audit Log</h2>", unsafe_allow_html=True)
    settings = get_settings(db) if db else {}
    st.markdown(f"""
    <div class='hub-card'>
      <table style='width:100%;font-size:0.82rem;border-collapse:collapse;'>
        <tr style='border-bottom:1px solid var(--border);'>
          <th style='text-align:left;padding:6px 12px;color:var(--muted);'>Event</th>
          <th style='text-align:left;padding:6px 12px;color:var(--muted);'>Value</th>
        </tr>
        <tr><td style='padding:6px 12px;'>Last Settings Update</td>
            <td style='padding:6px 12px;color:var(--muted);'>{settings.get('updated_at','—')}</td></tr>
        <tr><td style='padding:6px 12px;'>Last Force Refresh</td>
            <td style='padding:6px 12px;color:var(--muted);'>{settings.get('force_refresh_ts','—')}</td></tr>
        <tr><td style='padding:6px 12px;'>Last Cache Clear</td>
            <td style='padding:6px 12px;color:var(--muted);'>{settings.get('cache_cleared_ts','—')}</td></tr>
        <tr><td style='padding:6px 12px;'>Maintenance Mode</td>
            <td style='padding:6px 12px;color:var(--muted);'>{settings.get('maintenance_mode', False)}</td></tr>
      </table>
    </div>
    """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════════
#  ROUTER
# ════════════════════════════════════════════════════════════════════════════════
if not st.session_state.admin_logged_in:
    admin_login()
else:
    nav = admin_sidebar()

    if "Dashboard"   in nav: tab_dashboard()
    elif "User"      in nav: tab_users()
    elif "Balance"   in nav: tab_balance()
    elif "API Keys"  in nav: tab_api_keys()
    elif "Platform"  in nav: tab_toggles()
    elif "Messages"  in nav: tab_messages()
    elif "Refresh"   in nav: tab_refresh()
    elif "Audit"     in nav: tab_audit()
