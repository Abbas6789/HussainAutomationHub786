"""
shared/ai_meta.py
Auto-generate video titles, descriptions, and hashtags via Claude API.
Falls back to rule-based generation if API key is absent.
"""
import os, re, json, time, random
import streamlit as st

HASHTAG_POOL = [
    "#Viral","#Trending","#FYP","#ForYou","#Agriculture","#FarmLife","#AgTech",
    "#SmartFarming","#ContentCreator","#VideoCreator","#Reels","#Shorts",
    "#TikTokViral","#ViralVideo","#SocialMedia","#DigitalMarketing",
    "#OrganicFarming","#ModernFarming","#CreatorEconomy","#VideoMarketing",
    "#Pakistan","#PakistanFarming","#HussainHub","#AutomationHub",
    "#VideoContent","#ViralContent","#GrowOnSocial","#Trending2025",
    "#MustWatch","#ShareThis","#ExploreMore","#NewVideo","#AgricultureTech",
    "#CropScience","#FarmToTable","#SoilHealth","#PrecisionAgriculture",
]

TITLE_TEMPLATES = [
    "You Won't Believe This {topic} Hack 🔥",
    "The Secret {topic} Method Nobody Talks About",
    "This {topic} Technique Changed Everything 🚀",
    "Watch This Before You Try {topic}",
    "I Tried {topic} For 30 Days — Here's What Happened",
    "{topic}: The Complete Guide You Need",
    "Why Everyone Is Talking About {topic}",
    "Transform Your {topic} Results With This One Trick",
]

def generate_metadata_ai(filename: str, claude_api_key: str = "") -> dict:
    """
    Generate title, description, and hashtags using Claude API.
    Falls back to template-based if key unavailable.
    """
    # Infer topic from filename
    stem = re.sub(r'[_\-\.]', ' ', filename.rsplit('.', 1)[0]).strip()
    topic = stem.title() if stem else "My Video"

    if not claude_api_key:
        claude_api_key = os.getenv("ANTHROPIC_API_KEY", "")

    if claude_api_key:
        try:
            import urllib.request
            payload = json.dumps({
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 500,
                "messages": [{
                    "role": "user",
                    "content": (
                        f"Generate social media metadata for a video file named '{filename}'. "
                        "Return ONLY a JSON object with keys: "
                        "'title' (catchy, <80 chars), "
                        "'description' (2-3 sentences, engaging), "
                        "'hashtags' (list of 20 relevant hashtags as strings). "
                        "Focus on agriculture/farming and content creator niches. "
                        "No extra text, just the JSON."
                    )
                }]
            }).encode()
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": claude_api_key,
                    "anthropic-version": "2023-06-01",
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
                text = data["content"][0]["text"]
                # Strip markdown fences if present
                text = re.sub(r"```json|```", "", text).strip()
                meta = json.loads(text)
                return {
                    "title": meta.get("title", _fallback_title(topic)),
                    "description": meta.get("description", _fallback_desc(topic)),
                    "hashtags": meta.get("hashtags", _random_tags()),
                }
        except Exception:
            pass  # fall through to template

    return _fallback_meta(topic)


def _fallback_title(topic: str) -> str:
    return random.choice(TITLE_TEMPLATES).format(topic=topic)

def _fallback_desc(topic: str) -> str:
    return (
        f"Discover the latest in {topic} with this exclusive video from Hussain Automation Hub. "
        f"Watch till the end for game-changing insights that will transform your approach. "
        f"Like, share, and follow for more viral content!"
    )

def _random_tags(n: int = 25) -> list[str]:
    pool = HASHTAG_POOL.copy()
    random.shuffle(pool)
    return pool[:n]

def _fallback_meta(topic: str) -> dict:
    return {
        "title": _fallback_title(topic),
        "description": _fallback_desc(topic),
        "hashtags": _random_tags(),
    }
