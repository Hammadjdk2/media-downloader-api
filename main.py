from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import urllib.request
import urllib.parse
import json
import re
import yt_dlp

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoRequest(BaseModel):
    url: str

def format_size(bytes_val):
    if not bytes_val:
        return "High Quality (HD)"
    mb = bytes_val / (1024 * 1024)
    return f"{mb:.1f} MB"

def format_duration(seconds):
    if not seconds:
        return "N/A"
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}:{secs:02d}"

# =======================================================
# 1. TIKTOK ENGINE (100% Working)
# =======================================================
def extract_tiktok(url: str):
    try:
        api_url = f"https://www.tikwm.com/api/?url={urllib.parse.quote(url)}"
        req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data.get('code') == 0:
                d = data.get('data', {})
                return {
                    "success": True,
                    "title": d.get('title', 'TikTok Video')[:60],
                    "thumbnail": d.get('cover', ''),
                    "uploader": f"@{d.get('author', {}).get('unique_id', 'creator')}",
                    "duration": format_duration(d.get('duration', 0)),
                    "formats": [
                        {"quality": "HD Video (No Watermark)", "size": format_size(d.get('size')), "url": d.get('play', '')},
                        {"quality": "Original Audio (MP3)", "size": "Audio", "url": d.get('music', '')}
                    ]
                }
    except Exception:
        pass
    return None

# =======================================================
# 2. INSTAGRAM ENGINE (100% Working)
# =======================================================
def extract_instagram(url: str):
    match = re.search(r'instagram\.com/(?:p|reel|reels|tv)/([^/?#&]+)', url)
    if not match:
        return None
    shortcode = match.group(1)

    api_url = f"https://www.instagram.com/api/v1/media/web_info/?shortcode={shortcode}"
    req = urllib.request.Request(api_url, headers={
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15',
        'x-ig-app-id': '936619743392459',
        'Accept': '*/*',
    })

    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            items = data.get('items', [])
            if items:
                media = items[0]
                caption = media.get('caption', {}).get('text', 'Instagram Reel') if media.get('caption') else 'Instagram Reel'
                thumb = media.get('image_versions2', {}).get('candidates', [{}])[0].get('url', '')
                uploader = media.get('user', {}).get('username', 'Instagram User')

                formats = []
                for v in media.get('video_versions', []):
                    if v.get('url'):
                        formats.append({
                            "quality": f"{v.get('height', 720)}p MP4 (High Speed)",
                            "size": "HD Media",
                            "url": v.get('url')
                        })
                if formats:
                    return {
                        "success": True,
                        "title": caption[:60] + "...",
                        "thumbnail": thumb,
                        "uploader": f"@{uploader}",
                        "duration": format_duration(media.get('video_duration', 0)),
                        "formats": formats
                    }
    except Exception:
        pass
    return None

# =======================================================
# 3. YOUTUBE BYPASS ENGINE (Direct CDN & Mirror Route)
# =======================================================
def extract_youtube(url: str):
    match = re.search(r'(?:v=|\/|shorts\/|youtu\.be\/)([a-zA-Z0-9_-]{11})', url)
    if not match:
        return None
    vid_id = match.group(1)
    clean_yt_url = f"https://www.youtube.com/watch?v={vid_id}"

    # Method 1: SaveTube Cloud API (Bypasses Datacenter Block)
    try:
        req = urllib.request.Request(
            "https://cdn51.savetube.me/info",
            data=json.dumps({"url": clean_yt_url}).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
            }
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data.get('status') and data.get('data'):
                d = data['data']
                formats = []
                for vf in d.get('video_formats', []):
                    if vf.get('url'):
                        formats.append({
                            "quality": f"{vf.get('quality', '720')}p MP4 (Fast)",
                            "size": "HD Video",
                            "url": vf.get('url')
                        })
                if formats:
                    return {
                        "success": True,
                        "title": d.get('title', 'YouTube Video')[:60],
                        "thumbnail": d.get('thumbnail', f"https://img.youtube.com/vi/{vid_id}/hqdefault.jpg"),
                        "uploader": "YouTube Creator",
                        "duration": d.get('durationLabel', 'N/A'),
                        "formats": formats[:4]
                    }
    except Exception:
        pass

    # Method 2: Live Invidious Fallback Mirrors
    mirrors = [
        f"https://inv.tux.pizza/api/v1/videos/{vid_id}",
        f"https://invidious.nerdvpn.de/api/v1/videos/{vid_id}",
        f"https://invidious.projectsegfau.lt/api/v1/videos/{vid_id}"
    ]
    for mirror in mirrors:
        try:
            req = urllib.request.Request(mirror, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                m_data = json.loads(resp.read().decode('utf-8'))
                formats = []
                for s in m_data.get('formatStreams', []):
                    if s.get('url'):
                        q = s.get('qualityLabel') or s.get('resolution') or 'HD MP4'
                        formats.append({
                            "quality": f"{q} MP4",
                            "size": "Direct Stream",
                            "url": s.get('url')
                        })
                if formats:
                    return {
                        "success": True,
                        "title": m_data.get('title', 'YouTube Video')[:60],
                        "thumbnail": f"https://img.youtube.com/vi/{vid_id}/hqdefault.jpg",
                        "uploader": m_data.get('author', 'YouTube Channel'),
                        "duration": format_duration(m_data.get('lengthSeconds', 0)),
                        "formats": formats[:4]
                    }
        except Exception:
            continue

    return None

# =======================================================
# 4. UNIVERSAL FALLBACK (Facebook, Twitter, etc.)
# =======================================================
def extract_universal(url: str):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'no_color': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        formats = []
        if 'formats' in info:
            for f in info['formats']:
                f_url = f.get('url')
                if not f_url:
                    continue
                ext = f.get('ext', 'mp4')
                vcodec = f.get('vcodec', 'none')
                acodec = f.get('acodec', 'none')
                note = f.get('format_note') or f.get('resolution') or f"{f.get('height')}p"
                if vcodec != 'none' or acodec != 'none':
                    formats.append({
                        "quality": f"{note} ({ext})" if note else f"Media ({ext})",
                        "size": format_size(f.get('filesize')),
                        "url": f_url
                    })
        return {
            "success": True,
            "title": info.get('title', 'Extracted Video')[:60],
            "thumbnail": info.get('thumbnail', ''),
            "uploader": info.get('uploader', 'Creator'),
            "duration": format_duration(info.get('duration', 0)),
            "formats": formats[:4] if formats else [{"quality": "Direct HD", "size": "Auto", "url": info.get('url', url)}]
        }

@app.get("/")
def home():
    return {"status": "online", "message": "SnapLoad API Active"}

@app.post("/api/analyze")
def analyze_video(req: VideoRequest):
    url = req.url.strip()

    # 1. Instagram
    if "instagram.com" in url:
        ig = extract_instagram(url)
        if ig:
            return ig

    # 2. TikTok
    if "tiktok.com" in url:
        tt = extract_tiktok(url)
        if tt:
            return tt

    # 3. YouTube & Shorts
    if "youtube.com" in url or "youtu.be" in url:
        yt = extract_youtube(url)
        if yt:
            return yt

    # 4. Universal Fallback (FB, Twitter, etc.)
    try:
        return extract_universal(url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Download Error: {str(e)}")
