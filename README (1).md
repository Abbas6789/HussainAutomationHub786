# 🚀 SocioSaas Pro — Social Media Automation SaaS
**Developed by Ghulam Hussain**  
📲 WhatsApp: [03461785207](https://wa.me/923461785207)

---

## ✨ Features

| Feature | Details |
|---|---|
| Multi-user Auth | Register → Pending → Admin Approval |
| Device Locking | Each account locked to one browser/device |
| Master Admin | Hidden admin panel with full control |
| Social Media OAuth | YouTube, Facebook, TikTok connect buttons |
| Video Automation | Upload + AI-generated titles & hashtags |
| Subscription Plans | Free vs Premium with WhatsApp buy flow |
| Notice Board | Admin broadcasts messages to all users |
| Custom Branding | Profile pic watermark + sidebar branding |

---

## 🔑 Admin Access
- **Email:** `hklhhklh5@gmail.com`  
- **Password:** `Ghse45*#`

---

## 🚀 Deployment

### Local Run
```bash
pip install -r requirements.txt
streamlit run main.py
```

### Streamlit Cloud
1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo → set `main.py` as entry point
4. Deploy!

### 📁 File Structure
```
├── main.py              # Main app (all-in-one)
├── requirements.txt     # Dependencies
├── hussain.jpg          # Developer profile picture (add your photo)
├── .streamlit/
│   └── config.toml      # Optional theme config
└── README.md
```

---

## 🔗 OAuth Setup (Optional)

To activate real social media connections, add to `.streamlit/secrets.toml`:

```toml
[youtube]
client_id = "YOUR_GOOGLE_CLIENT_ID"
client_secret = "YOUR_GOOGLE_CLIENT_SECRET"

[facebook]
app_id = "YOUR_FACEBOOK_APP_ID"
app_secret = "YOUR_FACEBOOK_APP_SECRET"

[tiktok]
client_key = "YOUR_TIKTOK_CLIENT_KEY"
client_secret = "YOUR_TIKTOK_CLIENT_SECRET"
```

---

## 👤 User Flow
1. User registers → status = `pending`
2. Admin logs in → approves user
3. User logs in → device ID locked
4. If device changes → admin resets device ID
5. Admin can upgrade plans, block, or send notices

---

*© 2025 Ghulam Hussain — SocioSaas Pro*
