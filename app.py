import streamlit as st
import sqlite3
import hashlib
import uuid
import json
import pandas as pd
from datetime import datetime
from pathlib import Path

# ─── CONSTANTS ────────────────────────────────────────────────────────────────
ADMIN_EMAIL    = "hklhhklh5@gmail.com"
ADMIN_PASSWORD = "Ghse45*#"
DEVELOPER_NAME = "Ghulam Hussain"
DB_PATH        = "sociosaas.db"
APP_TITLE      = "SocioSaas Pro"

# Google Sheets spreadsheet ID
SHEET_ID       = "1cWzMMmuJsmYCy9L-GOyAbwSzAmAe7zD9v4a3yUdPJOA"

# Column names
COL_TITLE    = "Video_Title"
COL_URL      = "Video_URL"
COL_COMMENTS = "User_Comments"

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=f"{APP_TITLE} | {DEVELOPER_NAME}",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ══════════════════════════════════════════════════════════════════════════════
#  GOOGLE SHEETS CONNECTION
# ══════════════════════════════════════════════════════════════════════════════

def _get_gsheets_conn():
    return st.connection("gsheets", type="GSheetsConnection")

@st.cache_data(ttl=60)
def fetch_videos_from_sheet() -> list[dict]:
    try:
        conn = _get_gsheets_conn()
        df = conn.read(
            spreadsheet=SHEET_ID,
            usecols=[COL_TITLE, COL_URL, COL_COMMENTS],
            ttl=60,
        )
        df = df.dropna(subset=[COL_TITLE])
        df = df.fillna("")
        return df.to_dict("records")
    except Exception as e:
        st.warning(f"⚠️ Could not load videos from Google Sheets: {e}")
        return []

# ══════════════════════════════════════════════════════════════════════════════
#  REPLACING FIREBASE FUNCTIONS (Fixed)
# ══════════════════════════════════════════════════════════════════════════════

def get_whatsapp_number():
    return "923461785207"

def get_premium_price():
    return "$19"

def get_free_limit():
    return 3

def get_cached_notice():
    return "🎉 Welcome to SocioSaas Pro! Manage your videos easily via Google Sheets."

def check_maintenance():
    # Maintenance is disabled by default now
    return False, ""

# (باقی تمام لاگ ان اور رجسٹریشن کا کوڈ آپ کی پرانی فائل والا ہی چلے گا)
st.write("App is Ready!")

