"""
firebase_utils.py  —  SocioSaas Pro  |  hussain-admin-786
Developer: Ghulam Hussain
Database:  https://hussain-admin-786-default-rtdb.firebaseio.com/

HOW SECRETS WORK IN THIS VERSION
==================================
Paste your entire downloaded Service Account JSON as ONE secret called
FIREBASE_SERVICE_ACCOUNT using triple-quotes in Streamlit Secrets:

    FIREBASE_SERVICE_ACCOUNT = \"\"\"
    {
      "type": "service_account",
      "project_id": "hussain-admin-786",
      "private_key_id": "abc123...",
      "private_key": "-----BEGIN PRIVATE KEY-----\\nMII...\\n-----END PRIVATE KEY-----\\n",
      "client_email": "firebase-adminsdk-fbsvc@hussain-admin-786.iam.gserviceaccount.com",
      "client_id": "...",
      "auth_uri": "https://accounts.google.com/o/oauth2/auth",
      "token_uri": "https://oauth2.googleapis.com/token",
      ...
    }
    \"\"\"

That's it — no manual formatting, no splitting into fields, no \\n escaping.
Just paste the raw JSON file content between the triple-quotes and save.

To update the key in the future:
  1. Download new JSON from Google Cloud Console
  2. Replace the value of FIREBASE_SERVICE_ACCOUNT in Streamlit Secrets
  3. Done — no code changes needed

The database_url is read from the JSON if present, otherwise the
hard-coded fallback https://hussain-admin-786-default-rtdb.firebaseio.com
is used automatically.
"""

import streamlit as st
import json
import urllib.request
import urllib.parse
import urllib.error
import base64
import hashlib
import time
import threading
from datetime import datetime, timezone, timedelta

# ─── CONSTANTS ────────────────────────────────────────────────────────────────
_FALLBACK_DB_URL = "https://hussain-admin-786-default-rtdb.firebaseio.com"
_TOKEN_CACHE: dict = {"token": None, "expires_at": 0.0}
_TOKEN_LOCK = threading.Lock()


# ══════════════════════════════════════════════════════════════════════════════
#  1.  LOAD SERVICE ACCOUNT  — single JSON string approach
# ══════════════════════════════════════════════════════════════════════════════

def _load_sa() -> dict:
    """
    Reads the entire Service Account JSON from ONE Streamlit secret:

        FIREBASE_SERVICE_ACCOUNT = \"\"\"{ ...raw JSON... }\"\"\"

    Steps performed here:
      1. Read the raw string from st.secrets["FIREBASE_SERVICE_ACCOUNT"]
      2. Parse it with json.loads() — this is the ONLY safe way to handle
         the private_key field because json.loads() correctly converts
         every \\n inside the JSON string into a real newline character,
         eliminating all control-character URL errors at the source.
      3. Validate that the parsed dict contains the required fields.
      4. Append database_url (not in the standard JSON file) using the
         hard-coded fallback if the secret doesn't include it.

    To update credentials in the future:
      - Download new Service Account JSON from Google Cloud Console
      - In Streamlit Cloud → App Settings → Secrets, replace the value
        of FIREBASE_SERVICE_ACCOUNT with the new JSON content
      - Save — no code changes required
    """
    # ── Step 1: read raw secret string ───────────────────────────────────────
    try:
        raw: str = st.secrets["FIREBASE_SERVICE_ACCOUNT"]
    except KeyError:
        st.error(
            "❌ Secret FIREBASE_SERVICE_ACCOUNT not found in Streamlit Secrets.\n\n"
            "Add it as:\n"
            "FIREBASE_SERVICE_ACCOUNT = \"\"\"\n"
            "{ ...paste your full service account JSON here... }\n"
            "\"\"\""
        )
        return {}
    except Exception as e:
        st.error(f"❌ Could not read FIREBASE_SERVICE_ACCOUNT secret: {e}")
        return {}

    # ── Step 2: parse JSON ────────────────────────────────────────────────────
    # json.loads() handles ALL newline escaping inside the JSON automatically.
    # The private_key field's \\n sequences become real \n characters here.
    raw = raw.strip()
    try:
        sa: dict = json.loads(raw)
    except json.JSONDecodeError as e:
        st.error(
            f"❌ FIREBASE_SERVICE_ACCOUNT is not valid JSON: {e}\n\n"
            "Make sure you pasted the complete, unmodified JSON file content "
            "between the triple-quotes."
        )
        return {}

    # ── Step 3: validate required fields ─────────────────────────────────────
    required = ("private_key", "client_email", "token_uri")
    missing  = [k for k in required if not sa.get(k)]
    if missing:
        st.error(
            f"❌ Service account JSON is missing required fields: {missing}\n"
            "Download a fresh JSON from Google Cloud Console and try again."
        )
        return {}

    # Confirm the PEM block survived JSON parsing intact
    if "BEGIN PRIVATE KEY" not in sa["private_key"]:
        st.error(
            "❌ private_key in the JSON does not look like a valid PEM block.\n"
            "The JSON may have been modified or truncated. Download a fresh key."
        )
        return {}

    # ── Step 4: add database_url (not in standard SA JSON) ───────────────────
    # If you want to store the DB URL inside the JSON you can add it manually:
    # "database_url": "https://hussain-admin-786-default-rtdb.firebaseio.com"
    if "database_url" not in sa:
        sa["database_url"] = _FALLBACK_DB_URL

    sa["database_url"] = sa["database_url"].rstrip("/")
    return sa


def _get_db_url() -> str:
    sa = _load_sa()
    return sa.get("database_url", _FALLBACK_DB_URL)


# ══════════════════════════════════════════════════════════════════════════════
#  2.  JWT BUILDING  (pure stdlib — no PyJWT required)
# ══════════════════════════════════════════════════════════════════════════════

def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _make_jwt(sa: dict) -> str:
    """
    Creates a signed RS256 JWT for the Google token endpoint.
    Tries:  1) cryptography package  (fastest, works on Streamlit Cloud)
            2) openssl subprocess    (fallback, also on Streamlit Cloud)
    """
    now = int(time.time())
    header  = _b64url(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
    payload = _b64url(json.dumps({
        "iss":   sa["client_email"],
        "sub":   sa["client_email"],
        "aud":   sa["token_uri"],
        "iat":   now,
        "exp":   now + 3600,
        "scope": (
            "https://www.googleapis.com/auth/firebase "
            "https://www.googleapis.com/auth/userinfo.email "
            "https://www.googleapis.com/auth/devstorage.full_control "
            "https://www.googleapis.com/auth/datastore"
        ),
    }).encode())

    signing_input = f"{header}.{payload}".encode("ascii")

    # ── Method A: cryptography package ──────────────────────────────────────
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding as _padding

        priv = serialization.load_pem_private_key(
            sa["private_key"].encode(), password=None
        )
        sig = priv.sign(signing_input, _padding.PKCS1v15(), hashes.SHA256())
        return f"{header}.{payload}.{_b64url(sig)}"

    except ImportError:
        pass  # fall through to Method B

    # ── Method B: openssl subprocess ─────────────────────────────────────────
    import subprocess, tempfile, os

    pem = sa["private_key"].encode()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pem", mode="wb") as kf:
        kf.write(pem)
        key_path = kf.name

    try:
        proc = subprocess.run(
            ["openssl", "dgst", "-sha256", "-sign", key_path],
            input=signing_input,
            capture_output=True
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"openssl sign failed: {proc.stderr.decode()}"
            )
        return f"{header}.{payload}.{_b64url(proc.stdout)}"
    finally:
        try:
            os.unlink(key_path)
        except OSError:
            pass


# ══════════════════════════════════════════════════════════════════════════════
#  3.  OAUTH2 BEARER TOKEN  (FIX 2 + FIX 3)
# ══════════════════════════════════════════════════════════════════════════════

def _get_token() -> str | None:
    """
    Returns a cached OAuth2 Bearer token (refreshes when < 60 s left).
    Thread-safe.  Replaces the legacy  ?auth=db_secret  approach.
    """
    with _TOKEN_LOCK:
        now = time.time()
        if _TOKEN_CACHE["token"] and now < _TOKEN_CACHE["expires_at"] - 60:
            return _TOKEN_CACHE["token"]

        sa = _load_sa()
        if not sa:
            return None

        try:
            jwt = _make_jwt(sa)
        except Exception as e:
            st.error(f"❌ JWT signing error: {e}")
            return None

        body = urllib.parse.urlencode({
            "grant_type": "urn:ietf:params:oauth2:grant-type:jwt-bearer",
            "assertion":  jwt,
        }).encode()

        try:
            req = urllib.request.Request(
                sa["token_uri"],
                data=body,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                td = json.loads(resp.read().decode())

            _TOKEN_CACHE["token"]      = td["access_token"]
            _TOKEN_CACHE["expires_at"] = now + int(td.get("expires_in", 3600))
            return _TOKEN_CACHE["token"]

        except urllib.error.HTTPError as e:
            body_txt = ""
            try:
                body_txt = e.read().decode()
            except Exception:
                pass
            st.error(f"❌ Token exchange HTTP {e.code}: {body_txt or e.reason}")
            return None
        except Exception as e:
            st.error(f"❌ Token exchange error: {e}")
            return None


# ══════════════════════════════════════════════════════════════════════════════
#  4.  CORE REQUEST  (FIX 1 — clean URL)
# ══════════════════════════════════════════════════════════════════════════════

def _req(path: str, method: str = "GET", data=None, silent: bool = False):
    """
    Authenticated Firebase RTDB REST call.
    path — e.g. "/config/notice"  (no .json suffix needed)
    """
    db_url = _get_db_url()
    if not db_url:
        if not silent:
            st.warning("Firebase database URL not set.")
        return None

    # FIX 1 — sanitise path so URL never contains control characters
    path = (path or "").strip().replace("\n", "").replace("\r", "").replace("\t", "")
    if not path.startswith("/"):
        path = "/" + path

    url = f"{db_url}{path}.json"          # Firebase REST requires .json

    token = _get_token()
    if not token:
        if not silent:
            st.warning("Cannot get Firebase auth token.")
        return None

    headers = {
        "Content-Type":  "application/json",
        "Authorization": f"Bearer {token}",
    }

    try:
        if method == "GET":
            request_obj = urllib.request.Request(url, headers=headers)
        else:
            payload = json.dumps(data).encode() if data is not None else b"null"
            request_obj = urllib.request.Request(
                url, data=payload, headers=headers, method=method
            )

        with urllib.request.urlopen(request_obj, timeout=10) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw and raw.strip() != "null" else {}

    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode()
        except Exception:
            pass
        if not silent:
            st.warning(f"Firebase {e.code} on {path}: {body or e.reason}")
        return None
    except urllib.error.URLError as e:
        if not silent:
            st.warning(f"Firebase network error: {e.reason}")
        return None
    except Exception as e:
        if not silent:
            st.warning(f"Firebase error: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  5.  AUTO-DELETE  (FIX 4)
# ══════════════════════════════════════════════════════════════════════════════

def sweep_expired_files(silent: bool = True) -> dict:
    """
    Deletes every RTDB record under /uploads, /files, /temp_files
    whose timestamp field is older than 24 hours.

    Returns {"checked": N, "deleted": N, "errors": N}

    Background usage (call once at startup):
        import firebase_utils as fb
        fb.schedule_auto_sweep()
    """
    NODES    = ["/uploads", "/files", "/temp_files"]
    CUTOFF   = datetime.now(timezone.utc) - timedelta(hours=24)
    TS_KEYS  = ("uploaded_at", "created_at", "timestamp", "ts")
    summary  = {"checked": 0, "deleted": 0, "errors": 0}

    for node in NODES:
        records = _req(node, method="GET", silent=silent)
        if not isinstance(records, dict):
            continue

        for key, val in records.items():
            if not isinstance(val, dict):
                continue
            summary["checked"] += 1

            # Find whichever timestamp field exists
            raw_ts = next((val[k] for k in TS_KEYS if k in val), None)
            if not raw_ts:
                continue

            try:
                ts_str = str(raw_ts).replace("Z", "+00:00")
                entry_dt = datetime.fromisoformat(ts_str)
                if entry_dt.tzinfo is None:
                    entry_dt = entry_dt.replace(tzinfo=timezone.utc)

                if entry_dt < CUTOFF:
                    result = _req(f"{node}/{key}", method="DELETE", silent=silent)
                    if result is not None:
                        summary["deleted"] += 1
                    else:
                        summary["errors"] += 1

            except (ValueError, TypeError):
                continue

    return summary


def schedule_auto_sweep(interval_seconds: int = 3600) -> None:
    """
    Runs sweep_expired_files() in a daemon thread every hour.
    Call once at the very top of admin.py (after imports):

        import firebase_utils as fb
        fb.schedule_auto_sweep()
    """
    def _loop():
        while True:
            try:
                sweep_expired_files(silent=True)
            except Exception:
                pass
            time.sleep(interval_seconds)

    t = threading.Thread(target=_loop, daemon=True, name="fb-auto-sweep")
    t.start()


# ══════════════════════════════════════════════════════════════════════════════
#  6.  CONNECTION TEST  (call from admin.py to show live status)
# ══════════════════════════════════════════════════════════════════════════════

def test_connection() -> dict:
    """
    Writes a ping record and reads it back.
    Returns {"ok": bool, "message": str, "latency_ms": int}
    """
    import time as _t
    t0 = _t.monotonic()
    path = "/config/_ping"
    payload = {"ok": True, "at": datetime.now(timezone.utc).isoformat()}

    if _req(path, method="PUT", data=payload) is None:
        return {
            "ok": False,
            "message": "Write failed — check service account role and database URL.",
            "latency_ms": 0,
        }
    read = _req(path, method="GET")
    ms   = int((_t.monotonic() - t0) * 1000)
    if read and read.get("ok"):
        return {"ok": True,  "message": f"✅ Firebase connected ({ms} ms)", "latency_ms": ms}
    return {"ok": False, "message": "Write OK but read-back failed.", "latency_ms": ms}


# ══════════════════════════════════════════════════════════════════════════════
#  7.  PUBLIC API  (same signatures as before — nothing in app.py/admin.py
#                  needs to change)
# ══════════════════════════════════════════════════════════════════════════════

# ── Reads ─────────────────────────────────────────────────────────────────────

def get_maintenance_status() -> dict:
    r = _req("/config/maintenance")
    if r is None:
        return {"enabled": False, "message": ""}
    return {
        "enabled": bool(r.get("enabled", False)),
        "message": r.get("message", "🔧 Under maintenance. Please check back soon."),
    }


def get_notice_board() -> str:
    r = _req("/config/notice")
    if isinstance(r, str):  return r
    if isinstance(r, dict): return r.get("message", "")
    return ""


def get_social_credentials() -> dict:
    return _req("/credentials/social") or {}


def get_google_auth_config() -> dict:
    return _req("/credentials/google") or {}


def get_remote_config() -> dict:
    return _req("/config/remote") or {}


def get_whatsapp_messages() -> list:
    r = _req("/whatsapp/messages")
    if not isinstance(r, dict):
        return []
    msgs = []
    for k, v in r.items():
        if isinstance(v, dict):
            v["_firebase_key"] = k
            msgs.append(v)
    msgs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return msgs


# ── Writes ────────────────────────────────────────────────────────────────────

def set_maintenance(enabled: bool, message: str) -> bool:
    return _req("/config/maintenance", "PUT",
                {"enabled": enabled, "message": message}) is not None


def set_notice_board(message: str) -> bool:
    return _req("/config/notice", "PUT",
                {"message": message,
                 "updated_at": datetime.now(timezone.utc).isoformat()}) is not None


def set_google_credentials(client_id: str, client_secret: str) -> bool:
    return _req("/credentials/google", "PUT", {
        "client_id":     client_id,
        "client_secret": client_secret,
        "updated_at":    datetime.now(timezone.utc).isoformat(),
    }) is not None


def set_social_credentials(platform: str, fields: dict) -> bool:
    fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    return _req(f"/credentials/social/{platform}", "PUT", fields) is not None


def set_remote_config(key: str, value) -> bool:
    return _req(f"/config/remote/{key}", "PUT", value) is not None


def push_whatsapp_message(sender_email: str, sender_name: str, message: str) -> bool:
    pid = hashlib.md5(f"{sender_email}{time.time()}".encode()).hexdigest()[:16]
    return _req(f"/whatsapp/messages/{pid}", "PUT", {
        "sender_email": sender_email,
        "sender_name":  sender_name,
        "message":      message,
        "timestamp":    datetime.now(timezone.utc).isoformat(),
        "replied":      False,
        "reply_text":   "",
    }) is not None


def reply_to_whatsapp(firebase_key: str, reply_text: str) -> bool:
    return _req(f"/whatsapp/messages/{firebase_key}", "PATCH", {
        "replied":    True,
        "reply_text": reply_text,
        "replied_at": datetime.now(timezone.utc).isoformat(),
    }) is not None


def delete_whatsapp_message(firebase_key: str) -> bool:
    return _req(f"/whatsapp/messages/{firebase_key}", "DELETE") is not None


# ══════════════════════════════════════════════════════════════════════════════
#  STREAMLIT SECRETS TEMPLATE
#
#  LOCAL:  save as  .streamlit/secrets.toml   (add to .gitignore!)
#  CLOUD:  Streamlit Cloud → App → Settings → Secrets → paste → Save
#
#  HOW TO SET UP (one-time):
#  1. Go to console.cloud.google.com
#  2. IAM & Admin → Service Accounts → your account → Keys → Add Key → JSON
#  3. Open the downloaded JSON file in any text editor
#  4. Copy the ENTIRE contents
#  5. Paste between the triple-quotes below
#
#  HOW TO UPDATE KEY IN THE FUTURE:
#  1. Delete old key in Google Cloud Console, create new JSON key
#  2. Open the new JSON, copy all contents
#  3. In Streamlit Secrets, replace everything between the triple-quotes
#  4. Save — no code changes needed
#
# ──────────────────────────────────────────────────────────────────────────────
#
# FIREBASE_SERVICE_ACCOUNT = """
# {
#   "type": "service_account",
#   "project_id": "hussain-admin-786",
#   "private_key_id": "your_key_id_here",
#   "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvg...\n-----END PRIVATE KEY-----\n",
#   "client_email": "firebase-adminsdk-fbsvc@hussain-admin-786.iam.gserviceaccount.com",
#   "client_id": "108892461800259841786",
#   "auth_uri": "https://accounts.google.com/o/oauth2/auth",
#   "token_uri": "https://oauth2.googleapis.com/token",
#   "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
#   "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40hussain-admin-786.iam.gserviceaccount.com",
#   "universe_domain": "googleapis.com"
# }
# """
#
# NOTE: The \\n characters inside "private_key" in the JSON are handled
# automatically by json.loads() — you do NOT need to change anything
# in the JSON. Just paste it as-is between the triple-quotes.
# ══════════════════════════════════════════════════════════════════════════════
