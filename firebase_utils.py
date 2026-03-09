"""
firebase_utils.py — Secure Firebase Realtime Database bridge
All credentials fetched from Streamlit secrets (never hardcoded).
Used by both app.py (read-only public) and admin.py (read/write).
"""

import streamlit as st
import json
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime

# ─── FIREBASE REST API HELPERS ────────────────────────────────────────────────

def _get_firebase_url() -> str:
    """Return the Firebase project base URL from secrets."""
    try:
        return st.secrets["firebase"]["database_url"].rstrip("/")
    except Exception:
        return ""

def _get_firebase_token() -> str:
    """Return the Firebase secret token for authenticated requests."""
    try:
        return st.secrets["firebase"]["db_secret"]
    except Exception:
        return ""

def _firebase_request(path: str, method: str = "GET", data: dict = None) -> dict | None:
    """
    Low-level authenticated Firebase REST call.
    path  — e.g. "/config/maintenance"
    method — GET | PUT | PATCH | DELETE
    data  — Python dict, serialised to JSON for write ops
    Returns parsed JSON or None on failure.
    """
    base_url = _get_firebase_url()
    token    = _get_firebase_token()
    if not base_url or not token:
        return None

    url = f"{base_url}{path}.json?auth={token}"
    headers = {"Content-Type": "application/json"}

    try:
        if method == "GET":
            req = urllib.request.Request(url, headers=headers)
        else:
            payload = json.dumps(data).encode("utf-8") if data is not None else b"null"
            req = urllib.request.Request(url, data=payload, headers=headers, method=method)

        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw and raw != "null" else {}
    except urllib.error.HTTPError as e:
        st.warning(f"Firebase HTTP {e.code}: {e.reason}")
        return None
    except Exception as e:
        st.warning(f"Firebase connection error: {e}")
        return None


# ─── PUBLIC CONFIG (read by app.py) ───────────────────────────────────────────

def get_maintenance_status() -> dict:
    """
    Returns {"enabled": bool, "message": str}
    Defaults to off if Firebase unreachable.
    """
    result = _firebase_request("/config/maintenance")
    if result is None:
        return {"enabled": False, "message": ""}
    return {
        "enabled": result.get("enabled", False),
        "message": result.get("message", "🔧 Under Maintenance. Please check back soon.")
    }

def get_notice_board() -> str:
    """Global notice message shown to all logged-in users."""
    result = _firebase_request("/config/notice")
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        return result.get("message", "")
    return ""

def get_social_credentials() -> dict:
    """
    Returns all social API keys for the public portal.
    Shape: { "youtube": {...}, "facebook": {...}, "tiktok": {...} }
    """
    result = _firebase_request("/credentials/social")
    return result or {}

def get_google_auth_config() -> dict:
    """Returns Google OAuth client_id / client_secret."""
    result = _firebase_request("/credentials/google")
    return result or {}

def get_remote_config() -> dict:
    """
    Returns remote-update fields set by admin:
    { "app_version": str, "update_url": str, "custom_logic": str, ... }
    """
    result = _firebase_request("/config/remote")
    return result or {}

def get_whatsapp_messages() -> list:
    """
    Reads /whatsapp/messages node — list of user message objects.
    Each: { id, sender_email, sender_name, message, timestamp, replied }
    """
    result = _firebase_request("/whatsapp/messages")
    if not result:
        return []
    # Firebase returns dict keyed by push-id; convert to list
    messages = []
    for key, val in result.items():
        if isinstance(val, dict):
            val["_firebase_key"] = key
            messages.append(val)
    # Sort newest first
    messages.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return messages


# ─── ADMIN WRITE OPERATIONS (used only by admin.py) ───────────────────────────

def set_maintenance(enabled: bool, message: str) -> bool:
    result = _firebase_request(
        "/config/maintenance",
        method="PUT",
        data={"enabled": enabled, "message": message}
    )
    return result is not None

def set_notice_board(message: str) -> bool:
    result = _firebase_request(
        "/config/notice",
        method="PUT",
        data={"message": message, "updated_at": datetime.now().isoformat()}
    )
    return result is not None

def set_google_credentials(client_id: str, client_secret: str) -> bool:
    result = _firebase_request(
        "/credentials/google",
        method="PUT",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "updated_at": datetime.now().isoformat()
        }
    )
    return result is not None

def set_social_credentials(platform: str, fields: dict) -> bool:
    """platform = 'youtube' | 'facebook' | 'tiktok'"""
    fields["updated_at"] = datetime.now().isoformat()
    result = _firebase_request(
        f"/credentials/social/{platform}",
        method="PUT",
        data=fields
    )
    return result is not None

def set_remote_config(key: str, value: str) -> bool:
    result = _firebase_request(
        f"/config/remote/{key}",
        method="PUT",
        data=value
    )
    return result is not None

def push_whatsapp_message(sender_email: str, sender_name: str, message: str) -> bool:
    """Called from app.py when a user sends a message to the admin."""
    import hashlib, time
    push_id = hashlib.md5(f"{sender_email}{time.time()}".encode()).hexdigest()[:16]
    result = _firebase_request(
        f"/whatsapp/messages/{push_id}",
        method="PUT",
        data={
            "sender_email": sender_email,
            "sender_name": sender_name,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "replied": False,
            "reply_text": ""
        }
    )
    return result is not None

def reply_to_whatsapp(firebase_key: str, reply_text: str) -> bool:
    """Admin replies to a user message."""
    result = _firebase_request(
        f"/whatsapp/messages/{firebase_key}",
        method="PATCH",
        data={
            "replied": True,
            "reply_text": reply_text,
            "replied_at": datetime.now().isoformat()
        }
    )
    return result is not None

def delete_whatsapp_message(firebase_key: str) -> bool:
    result = _firebase_request(
        f"/whatsapp/messages/{firebase_key}",
        method="DELETE"
    )
    return result is not None
