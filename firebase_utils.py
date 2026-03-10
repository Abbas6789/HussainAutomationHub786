"""
firebase_utils.py  —  SocioSaas Pro  |  hussain-admin-786
Developer: Ghulam Hussain
Database:  https://hussain-admin-786-default-rtdb.firebaseio.com/

ROOT CAUSE OF "Invalid control character" ERROR — AND THE FIX
==============================================================
When Streamlit reads a triple-quoted TOML value, the \\n sequences
inside the private_key JSON field become REAL newline characters
(ASCII 0x0A).  Real newlines are illegal inside a JSON string value,
which is why json.loads() throws:

    Invalid control character at: line 5 column 46 (char 177)

This file fixes that by running _sanitise_json_string() on the raw
secret before json.loads() ever sees it.  The function finds the
private_key value using a regex and re-escapes any real newlines back
to the two-character \\n sequence that JSON requires.

HOW TO ADD YOUR SECRET IN STREAMLIT
=====================================
Go to App Settings → Secrets and paste EXACTLY this format:

    FIREBASE_SERVICE_ACCOUNT = \"\"\"
    {
      "type": "service_account",
      "project_id": "hussain-admin-786",
      "private_key_id": "your_key_id",
      "private_key": "-----BEGIN PRIVATE KEY-----\\nMII...\\n-----END PRIVATE KEY-----\\n",
      "client_email": "firebase-adminsdk-fbsvc@hussain-admin-786.iam.gserviceaccount.com",
      "client_id": "108892461800259841786",
      "auth_uri": "https://accounts.google.com/o/oauth2/auth",
      "token_uri": "https://oauth2.googleapis.com/token",
      "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
      "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/...",
      "universe_domain": "googleapis.com"
    }
    \"\"\"

Just paste the raw downloaded JSON — no manual formatting needed.
To rotate the key: download new JSON, replace the value, save.
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

def _sanitise_json_string(raw: str) -> str:
    """
    THE ROOT-CAUSE FIX
    ══════════════════
    When Streamlit reads a triple-quoted TOML value the private_key field
    inside the JSON ends up with REAL newline characters (ASCII 0x0A) instead
    of the two-character escape sequence \\n.  Real newlines inside a JSON
    string value are illegal — that is exactly what causes:

        "Invalid control character at line 5 column 46 (char 177)"

    This function surgically fixes the raw string before json.loads() sees it:

    Strategy
    --------
    1. Find the private_key value in the raw text using a regex.
    2. Inside that value only, replace every real newline (0x0A) that sits
       between the PEM header/footer lines with the two-char escape \\n.
    3. Also collapse any run of whitespace-then-newline inside the key block
       (Streamlit sometimes adds indentation to triple-quoted values).
    4. Leave every other part of the JSON completely untouched.

    This is safer than touching the whole string because the JSON keys,
    braces, and other string values must NOT have their newlines altered.
    """
    import re

    # Pattern: capture everything between the opening quote after "private_key":
    # and the closing quote, including real newlines.
    # We use a non-greedy match and allow the value to span multiple lines.
    def _fix_pem_value(m: re.Match) -> str:
        inner = m.group(1)
        # Replace real newlines (possibly with surrounding whitespace/indent)
        # with the JSON-legal two-character escape sequence.
        inner = re.sub(r'\s*\n\s*', r'\\n', inner)
        # Also replace any literal \\n that became \\\\n due to double-escaping
        inner = inner.replace('\\\\n', '\\n')
        return f'"private_key": "{inner}"'

    fixed = re.sub(
        r'"private_key"\s*:\s*"(.*?)"',
        _fix_pem_value,
        raw,
        flags=re.DOTALL,
    )
    return fixed


def _load_sa() -> dict:
    """
    Reads the Service Account from Streamlit Secrets and returns a clean dict.

    Accepted secret format (paste raw JSON between triple-quotes — no
    manual formatting needed):

        FIREBASE_SERVICE_ACCOUNT = \"\"\"
        {
          "type": "service_account",
          "project_id": "hussain-admin-786",
          ...entire downloaded JSON file...
        }
        \"\"\"

    The function handles every broken newline variant that Streamlit/TOML
    can produce and repairs the JSON before parsing it.
    """
    # ── Step 1: read the raw secret ──────────────────────────────────────────
    try:
        raw: str = str(st.secrets["FIREBASE_SERVICE_ACCOUNT"]).strip()
    except KeyError:
        st.error(
            "❌ Secret **FIREBASE_SERVICE_ACCOUNT** not found.\n\n"
            "In Streamlit Cloud → App Settings → Secrets, add:\n\n"
            "```\nFIREBASE_SERVICE_ACCOUNT = \"\"\"\n"
            "{ ...paste entire service account JSON here... }\n\"\"\"\n```"
        )
        return {}
    except Exception as e:
        st.error(f"❌ Cannot read FIREBASE_SERVICE_ACCOUNT: {e}")
        return {}

    # ── Step 2: repair the private_key newlines BEFORE json.loads ────────────
    # This is the fix for "Invalid control character" — real \n inside the
    # private_key value are re-escaped to the two-char sequence \n so that
    # the JSON parser accepts them.
    raw_fixed = _sanitise_json_string(raw)

    # ── Step 3: parse JSON ────────────────────────────────────────────────────
    try:
        sa: dict = json.loads(raw_fixed)
    except json.JSONDecodeError:
        # Last-resort fallback: try with strict=False which ignores control chars
        try:
            sa = json.loads(raw_fixed, strict=False)
        except json.JSONDecodeError as e2:
            st.error(
                f"❌ Could not parse FIREBASE_SERVICE_ACCOUNT as JSON: {e2}\n\n"
                "**How to fix:** In Streamlit Secrets, make sure the value is "
                "the complete, unmodified JSON file pasted between triple-quotes:\n\n"
                "```\nFIREBASE_SERVICE_ACCOUNT = \"\"\"\n{ ...json... }\n\"\"\"\n```"
            )
            return {}

    # ── Step 4: validate required fields ─────────────────────────────────────
    for field in ("private_key", "client_email", "token_uri"):
        if not sa.get(field):
            st.error(
                f"❌ Field **{field}** is missing from the service account JSON. "
                "Download a fresh key from Google Cloud Console."
            )
            return {}

    # ── Step 5: ensure private_key has real newlines for the RSA library ─────
    # After json.loads() the key may still have literal \\n two-char sequences
    # if the JSON itself contained \\\\n.  Normalise to real newlines.
    pk = sa["private_key"]
    if "\\n" in pk:
        pk = pk.replace("\\n", "\n")
    sa["private_key"] = pk.strip()

    if "BEGIN PRIVATE KEY" not in sa["private_key"]:
        st.error(
            "❌ private_key does not contain a valid PEM block after normalisation. "
            "Re-download the service account JSON and paste it fresh."
        )
        return {}

    # ── Step 6: inject database_url (not in standard Google JSON) ────────────
    sa.setdefault("database_url", _FALLBACK_DB_URL)
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
#  STREAMLIT SECRETS — EXACT FORMAT TO PASTE
#
#  Streamlit Cloud → Your App → ⋮ menu → Settings → Secrets tab
#  Paste the block below, replacing the placeholder values with your real JSON.
#  Then click Save.  Both admin.py and app.py share the same secret.
#
#  ⚠️  LOCAL DEV: save as  .streamlit/secrets.toml  and add to .gitignore
#  ⚠️  NEVER commit secrets.toml to GitHub
#
# ──────────────────────────────────────────────────────────────────────────────
#
# FIREBASE_SERVICE_ACCOUNT = """
# {
#   "type": "service_account",
#   "project_id": "hussain-admin-786",
#   "private_key_id": "YOUR_KEY_ID",
#   "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBAD...rest of key...\n-----END PRIVATE KEY-----\n",
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
# IMPORTANT: The \n characters inside "private_key" above are TWO characters
# (backslash + n) — NOT real newlines.  Paste the JSON exactly as downloaded.
# The _sanitise_json_string() function in this file handles all variations
# automatically so you never need to manually edit the key.
# ══════════════════════════════════════════════════════════════════════════════
