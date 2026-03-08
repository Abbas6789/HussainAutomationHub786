"""
uploaders.py  — Platform upload functions (root-level, no subfolders)
Swap the commented-out real API code in once your keys are live.
"""
import os, time, shutil
from pathlib import Path


def process_video_ffmpeg(src: Path, out_dir: Path, platform: str) -> Path:
    """Convert video to 9:16 1080×1920. Falls back to copy if FFmpeg absent."""
    import subprocess
    out = out_dir / f"{platform.lower().replace(' ', '_')}_{src.name}"
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        filt = (
            "scale=1080:1920:force_original_aspect_ratio=decrease,"
            "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black"
        )
        subprocess.run([
            "ffmpeg", "-y", "-i", str(src),
            "-vf", filt,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart", str(out),
        ], capture_output=True, check=True)
    except Exception:
        shutil.copy(src, out)
    return out


def upload_youtube(video_path: Path, title: str, description: str,
                   hashtags: list, api_key: str) -> dict:
    if not api_key:
        return {"ok": False, "platform": "YouTube", "error": "YouTube API Key not configured"}
    try:
        # ── Uncomment for real upload ────────────────────────────────────────
        # from googleapiclient.discovery import build
        # from googleapiclient.http import MediaFileUpload
        # youtube = build('youtube', 'v3', developerKey=api_key)
        # body = {
        #     'snippet': {'title': title[:100], 'description': description,
        #                 'tags': [h.lstrip('#') for h in hashtags], 'categoryId': '22'},
        #     'status':  {'privacyStatus': 'public', 'selfDeclaredMadeForKids': False}
        # }
        # media = MediaFileUpload(str(video_path), mimetype='video/*', resumable=True)
        # r = youtube.videos().insert(part=','.join(body), body=body, media_body=media).execute()
        # return {"ok": True, "platform": "YouTube", "video_id": r['id']}
        # ────────────────────────────────────────────────────────────────────
        time.sleep(1.2)
        return {"ok": True, "platform": "YouTube",
                "video_id": f"yt_{int(time.time())}",
                "url": "https://youtube.com/shorts/demo"}
    except Exception as e:
        return {"ok": False, "platform": "YouTube", "error": str(e)}


def upload_facebook(video_path: Path, title: str, description: str,
                    hashtags: list, token: str) -> dict:
    if not token:
        return {"ok": False, "platform": "Facebook", "error": "Facebook Access Token not configured"}
    try:
        # ── Uncomment for real upload ────────────────────────────────────────
        # import requests
        # caption = f"{title}\n\n{description}\n\n{' '.join(hashtags)}"
        # r = requests.post("https://graph.facebook.com/v19.0/me/video_reels",
        #                   data={"upload_phase":"start","access_token":token})
        # vid_id = r.json().get("video_id")
        # with open(video_path,'rb') as vf:
        #     requests.post(f"https://rupload.facebook.com/video-upload/v19.0/{vid_id}",
        #                   headers={"Authorization":f"OAuth {token}","offset":"0",
        #                            "file_size":str(os.path.getsize(video_path))}, data=vf)
        # requests.post("https://graph.facebook.com/v19.0/me/video_reels",
        #               data={"video_id":vid_id,"upload_phase":"finish",
        #                     "video_state":"PUBLISHED","description":caption,"access_token":token})
        # return {"ok":True,"platform":"Facebook","video_id":vid_id}
        # ────────────────────────────────────────────────────────────────────
        time.sleep(1.2)
        return {"ok": True, "platform": "Facebook",
                "video_id": f"fb_{int(time.time())}",
                "url": "https://facebook.com/reels/demo"}
    except Exception as e:
        return {"ok": False, "platform": "Facebook", "error": str(e)}


def upload_tiktok(video_path: Path, title: str, description: str,
                  hashtags: list, api_key: str) -> dict:
    if not api_key:
        return {"ok": False, "platform": "TikTok", "error": "TikTok API Key not configured"}
    try:
        # ── Uncomment for real upload ────────────────────────────────────────
        # import requests
        # caption = f"{title} {' '.join(hashtags[:10])}"[:2200]
        # r = requests.post(
        #     "https://open.tiktokapis.com/v2/post/publish/video/init/",
        #     headers={"Authorization":f"Bearer {api_key}","Content-Type":"application/json"},
        #     json={"post_info":{"title":caption,"privacy_level":"PUBLIC_TO_EVERYONE"},
        #           "source_info":{"source":"FILE_UPLOAD",
        #                          "video_size":os.path.getsize(video_path),
        #                          "chunk_size":os.path.getsize(video_path),
        #                          "total_chunk_count":1}}
        # )
        # upload_url = r.json()["data"]["upload_url"]
        # with open(video_path,'rb') as vf:
        #     requests.put(upload_url, data=vf, headers={"Content-Type":"video/mp4"})
        # return {"ok":True,"platform":"TikTok","publish_id":r.json()["data"]["publish_id"]}
        # ────────────────────────────────────────────────────────────────────
        time.sleep(1.2)
        return {"ok": True, "platform": "TikTok",
                "publish_id": f"tt_{int(time.time())}",
                "url": "https://tiktok.com/@demo"}
    except Exception as e:
        return {"ok": False, "platform": "TikTok", "error": str(e)}
