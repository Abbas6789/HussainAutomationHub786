"""
firebase_utils.py  — Firestore helpers (root-level, no subfolders)
"""
import os, json
from datetime import datetime

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False


def init_firebase():
    if not FIREBASE_AVAILABLE:
        return None
    if firebase_admin._apps:
        return firestore.client()
    cred_json = os.getenv("FIREBASE_CREDENTIALS")
    if cred_json:
        try:
            cred = credentials.Certificate(json.loads(cred_json))
        except Exception:
            return None
    else:
        if not os.path.exists("firebase_credentials.json"):
            return None
        cred = credentials.Certificate("firebase_credentials.json")
    firebase_admin.initialize_app(cred)
    return firestore.client()


def get_db():
    return init_firebase()


# ── User helpers ──────────────────────────────────────────────────────────────

def _key(email): return email.replace(".", "_").replace("@", "_at_")

def get_user(db, email):
    if not db: return None
    doc = db.collection("users").document(_key(email)).get()
    return doc.to_dict() if doc.exists else None

def upsert_user(db, email, data):
    if not db: return
    data["updated_at"] = datetime.utcnow().isoformat()
    db.collection("users").document(_key(email)).set(data, merge=True)

def get_all_users(db):
    if not db: return []
    return [d.to_dict() for d in db.collection("users").stream()]

def approve_user(db, email, approved=True):
    upsert_user(db, email, {"approved": approved, "status": "active" if approved else "pending"})

def get_balance(db, email):
    u = get_user(db, email)
    return float(u.get("balance", 0.0)) if u else 0.0

def set_balance(db, email, amount):
    upsert_user(db, email, {"balance": float(amount)})


# ── Settings helpers ──────────────────────────────────────────────────────────

def get_settings(db):
    if not db: return {}
    doc = db.collection("settings").document("global").get()
    return doc.to_dict() if doc.exists else {}

def save_settings(db, data):
    if not db: return
    data["updated_at"] = datetime.utcnow().isoformat()
    db.collection("settings").document("global").set(data, merge=True)

def get_system_message(db):
    return get_settings(db).get("system_message", "Welcome to Hussain Automation Hub!")

def set_system_message(db, msg):
    save_settings(db, {"system_message": msg})

def get_platform_toggles(db):
    s = get_settings(db)
    return {
        "youtube":  s.get("platform_youtube",  True),
        "facebook": s.get("platform_facebook", True),
        "tiktok":   s.get("platform_tiktok",   True),
    }

def set_platform_toggles(db, toggles):
    save_settings(db, {
        "platform_youtube":  toggles.get("youtube",  True),
        "platform_facebook": toggles.get("facebook", True),
        "platform_tiktok":   toggles.get("tiktok",   True),
    })
