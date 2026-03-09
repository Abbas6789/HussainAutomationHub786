"""
# ============================================================
#  Filename: google_auth.py
#  Part: 1 — Public Website Files
#  Purpose: Google OAuth 2.0 helper for SocioSaas Pro
#  Developer: Ghulam Hussain
#  Usage: imported by app.py
# ============================================================
#
#  How it works:
#  1. Admin stores Google Client ID + Secret in Firebase
#     via the Admin Panel → System Auth tab.
#  2. app.py calls firebase_utils.get_google_auth_config()
#     to fetch those credentials at runtime.
#  3. This file builds the OAuth URL and handles the callback.
#
#  To activate real Google login, you must:
#  a) Create a project at https://console.cloud.google.com
#  b) Enable the Google+ / People API
#  c) Create OAuth 2.0 credentials (Web application)
#  d) Add your Streamlit Cloud URL to Authorised Redirect URIs:
#     https://YOUR-APP.streamlit.app/  (or localhost:8501 for local)
#  e) Save Client ID and Secret in Admin Panel → System Auth
# ============================================================
"""

import urllib.parse
import hashlib
import hmac
import json
import urllib.request
import urllib.error
import streamlit as st
import firebase_utils as fb


# ─── GOOGLE OAuth 2.0 ENDPOINTS ───────────────────────────────────────────────
GOOGLE_AUTH_URL  = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USER_URL  = "https://www.googleapis.com/oauth2/v3/userinfo"

# ─── REDIRECT URI ─────────────────────────────────────────────────────────────
def get_redirect_uri() -> str:
    """
    Returns the correct redirect URI.
    On Streamlit Cloud this is your app URL; locally it is localhost:8501.
    Override via st.secrets["google_oauth"]["redirect_uri"] if needed.
    """
    try:
        return st.secrets["google_oauth"]["redirect_uri"]
    except Exception:
        return "http://localhost:8501/"


# ─── BUILD AUTHORISATION URL ──────────────────────────────────────────────────
def build_google_auth_url(state: str = "google_oauth") -> str | None:
    """
    Constructs the Google OAuth consent-screen URL.
    Credentials are fetched live from Firebase (no hardcoding).
    Returns None if credentials are not yet configured.
    """
    creds = fb.get_google_auth_config()
    client_id = creds.get("client_id", "")

    if not client_id:
        return None

    params = {
        "client_id":     client_id,
        "redirect_uri":  get_redirect_uri(),
        "response_type": "code",
        "scope":         "openid email profile",
        "access_type":   "offline",
        "prompt":        "select_account",
        "state":         state,
    }
    return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"


# ─── EXCHANGE CODE FOR TOKENS ─────────────────────────────────────────────────
def exchange_code_for_token(auth_code: str) -> dict | None:
    """
    Exchanges the authorisation code returned by Google for an access token.
    Returns the token response dict, or None on failure.
    """
    creds = fb.get_google_auth_config()
    client_id     = creds.get("client_id", "")
    client_secret = creds.get("client_secret", "")

    if not client_id or not client_secret:
        st.error("Google credentials not configured. Ask the admin to set them.")
        return None

    payload = urllib.parse.urlencode({
        "code":          auth_code,
        "client_id":     client_id,
        "client_secret": client_secret,
        "redirect_uri":  get_redirect_uri(),
        "grant_type":    "authorization_code",
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            GOOGLE_TOKEN_URL,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        st.error(f"Google token exchange failed ({e.code}): {body}")
        return None
    except Exception as e:
        st.error(f"Google auth error: {e}")
        return None


# ─── FETCH USER PROFILE ───────────────────────────────────────────────────────
def get_google_user_info(access_token: str) -> dict | None:
    """
    Uses the access token to retrieve the user's Google profile.
    Returns dict with keys: sub, email, name, picture, email_verified
    """
    try:
        req = urllib.request.Request(
            GOOGLE_USER_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        st.error(f"Could not fetch Google user info: {e}")
        return None


# ─── FULL FLOW: HANDLE CALLBACK ───────────────────────────────────────────────
def handle_google_callback() -> dict | None:
    """
    Call this at the top of app.py to detect and process a Google OAuth callback.

    Usage in app.py:
        from google_auth import handle_google_callback, build_google_auth_url
        google_user = handle_google_callback()
        if google_user:
            st.session_state.google_profile = google_user

    Returns the Google user profile dict if the flow completed, else None.
    """
    params = st.query_params
    code  = params.get("code")
    state = params.get("state", "")
    error = params.get("error")

    if error:
        st.error(f"Google login cancelled or failed: {error}")
        st.query_params.clear()
        return None

    if code and "google" in state:
        token_resp = exchange_code_for_token(code)
        if token_resp:
            access_token = token_resp.get("access_token")
            if access_token:
                user_info = get_google_user_info(access_token)
                # Clear the query params so the code isn't reused
                st.query_params.clear()
                return user_info
    return None


# ─── CONVENIENCE: RENDER GOOGLE SIGN-IN BUTTON ───────────────────────────────
def render_google_login_button(label: str = "Continue with Google") -> None:
    """
    Renders a styled Google Sign-In button.
    Clicking it redirects to Google's consent screen.
    If credentials aren't configured, shows a warning instead.
    """
    auth_url = build_google_auth_url()

    if not auth_url:
        st.warning("⚠️ Google login is not yet configured. Admin must add credentials in the Admin Panel → System Auth.")
        return

    st.markdown(f"""
    <a href="{auth_url}" target="_self" style="
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        background: #ffffff;
        color: #1a1a2e;
        border: 1px solid #dadce0;
        border-radius: 10px;
        padding: 12px 20px;
        text-decoration: none;
        font-family: 'DM Sans', sans-serif;
        font-weight: 500;
        font-size: 14px;
        transition: box-shadow 0.2s;
        margin: 8px 0;
    "
    onmouseover="this.style.boxShadow='0 4px 12px rgba(0,0,0,0.15)'"
    onmouseout="this.style.boxShadow='none'"
    >
        <svg width="18" height="18" viewBox="0 0 48 48">
            <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
            <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
            <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
            <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.18 1.48-4.97 2.31-8.16 2.31-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
        </svg>
        {label}
    </a>
    """, unsafe_allow_html=True)
