"""
shared/firebase_utils.py
Firebase Firestore utilities shared by both apps.
"""
import os
import json
import streamlit as st
from datetime import datetime

# ── Try to import Firebase ────────────────────────────────────────────────────
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False


def init_firebase():
    """Initialize Firebase app (call once per session)."""
    if not FIREBASE_AVAILABLE:
        return None
    if firebase_admin._apps:
        return firestore.client()

    # Try env var first (Streamlit Cloud secrets), then local file
    cred_json = os.getenv("FIREBASE_CREDENTIALS")
    if cred_json:
        try:
            cred_dict = json.loads(cred_json)
            cred = credentials.Certificate(cred_dict)
        except Exception:
            return None
    else:
        cred_path = os.path.join(os.path.dirname(__file__), "..", "firebase_credentials.json")
        if not os.path.exists(cred_path):
            return None
        cred = credentials.Certificate(cred_path)

    firebase_admin.initialize_app(cred)
    return firestore.client()


def get_db():
    """Return Firestore client or None."""
    return init_firebase()


# ── User helpers ──────────────────────────────────────────────────────────────

def get_user(db, email: str) -> dict | None:
    if not db:
        return None
    doc = db.collection("users").document(email.replace(".", "_")).get()
    return doc.to_dict() if doc.exists else None


def upsert_user(db, email: str, data: dict):
    if not db:
        return
    ref = db.collection("users").document(email.replace(".", "_"))
    data["updated_at"] = datetime.utcnow().isoformat()
    ref.set(data, merge=True)


def get_all_users(db) -> list[dict]:
    if not db:
        return []
    docs = db.collection("users").stream()
    return [d.to_dict() for d in docs]


def approve_user(db, email: str, approved: bool = True):
    upsert_user(db, email, {"approved": approved, "status": "active" if approved else "pending"})


# ── Settings helpers ──────────────────────────────────────────────────────────

def get_settings(db) -> dict:
    if not db:
        return {}
    doc = db.collection("settings").document("global").get()
    return doc.to_dict() if doc.exists else {}


def save_settings(db, data: dict):
    if not db:
        return
    data["updated_at"] = datetime.utcnow().isoformat()
    db.collection("settings").document("global").set(data, merge=True)


# ── Balance helpers ───────────────────────────────────────────────────────────

def get_balance(db, email: str) -> float:
    user = get_user(db, email)
    if user:
        return float(user.get("balance", 0.0))
    return 0.0


def set_balance(db, email: str, amount: float):
    upsert_user(db, email, {"balance": amount})


# ── System message helpers ────────────────────────────────────────────────────

def get_system_message(db) -> str:
    s = get_settings(db)
    return s.get("system_message", "Welcome to Hussain Automation Hub!")


def set_system_message(db, msg: str):
    save_settings(db, {"system_message": msg})


# ── Platform toggle helpers ───────────────────────────────────────────────────

def get_platform_toggles(db) -> dict:
    s = get_settings(db)
    return {
        "youtube":  s.get("platform_youtube",  True),
        "facebook": s.get("platform_facebook", True),
        "tiktok":   s.get("platform_tiktok",   True),
    }


def set_platform_toggles(db, toggles: dict):
    save_settings(db, {
        "platform_youtube":  toggles.get("youtube",  True),
        "platform_facebook": toggles.get("facebook", True),
        "platform_tiktok":   toggles.get("tiktok",   True),
    })
