# 🚀 SocioSaas Pro — Master Admin System
**Developer: Ghulam Hussain** | 📲 WhatsApp: 03461785207

## 🏗️ Architecture
Firebase RTDB is the brain — app.py reads credentials dynamically, admin.py writes them.

## 📁 Files (Flat Structure)
- app.py — Public portal for users
- admin.py — Private master admin panel  
- firebase_utils.py — Secure Firebase bridge
- requirements.txt — Dependencies
- hussain.jpg — Your profile photo
- .streamlit/secrets.toml — Firebase credentials (NEVER commit this)
- .streamlit/config.toml — Dark theme config

## ⚡ Quick Start
1. pip install -r requirements.txt
2. Create .streamlit/secrets.toml with your Firebase URL and secret
3. streamlit run app.py  (public portal)
4. streamlit run admin.py  (your private panel)

## 🛡️ Admin: hklhhklh5@gmail.com / Ghse45*#

## 🔐 Secrets File Format
[firebase]
database_url = "https://YOUR-PROJECT-default-rtdb.firebaseio.com"
db_secret = "YOUR_FIREBASE_DATABASE_SECRET"

Get your secret from: Firebase Console > Project Settings > Service Accounts > Database Secrets
