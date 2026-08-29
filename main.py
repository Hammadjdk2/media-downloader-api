from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import urllib.request
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

# ==========================================
# 1. TIKTOK DEDICATED HIGH-SPEED ENGINE
# ==========================================
def extract_tiktok(url: str):
    try:
        api_url = f"https://www.tikwm.com/api/?url={url}"
        req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
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
                        {
                            "quality": "HD Video (No Watermark)",
                            "size": format_size(d.get('size')),
                            "url": d.get('play', '')
                        },
                        {
                            "quality": "Original Audio (MP3)",
                            "size": "Audio",
                            "url": d.get('music', '')
                        }
                    ]
                }
    except Exception:
        pass
    return None

# ==========================================
# 2. INSTAGRAM DEDICATED SCRAPER
# ==========================================
def extract_instagram(url: str):
    try:
        match = re.search(r'instagram\.com/(?:p|reel|reels|tv)/([^/?#&]+)', url)
        if not match:
            return None
        shortcode = match.group(1)
        
        api_url = f"https://www.instagram.com/api/v1/media/web_info/?shortcode={shortcode}"
        req = urllib.request.Request(api_url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'x-ig-app-id': '936619743392459',
            'Accept': '*/*',
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            items = data.get('items', [])
            if items:
                media = items[0]
                caption = media.get('caption', {}).get('text', 'Instagram Reel') if media.get('caption') else 'Instagram Reel'
                thumb = media.get('image_versions2', {}).get('candidates', [{}])[0].get('url', '')
                uploader = media.get('user', {}).get('username', 'Instagram Creator')
                
                formats = []
                for v in media.get('video_versions', []):
                    formats.append({
                        "quality": f"{v.get('height', 720)}p MP4 (Fast Download)",
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

# ==========================================
# 3. UNIVERSAL ENGINE (YOUTUBE, FB, TWITTER)
# ==========================================
def extract_universal(url: str):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'no_color': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'android', 'mweb', 'web_embedded']
            },
            'facebook': {
                'app_version': 'latest'
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
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
                format_note = f.get('format_note') or f.get('resolution') or (f"{f.get('height')}p" if f.get('height') else None)
                filesize = f.get('filesize') or f.get('filesize_approx')

                if vcodec != 'none' or acodec != 'none':
                    label = f"{format_note} ({ext})" if format_note else f"Direct ({ext})"
                    formats.append({
                        "quality": label,
                        "size": format_size(filesize),
                        "url": f_url
                    })

        if not formats and info.get('url'):
            formats.append({
                "quality": "Direct HD Stream",
                "size": "Auto",
                "url": info.get('url')
            })

        # Remove duplicate stream links
        unique_formats = []
        seen = set()
        for fmt in formats:
            if fmt['url'] not in seen:
                seen.add(fmt['url'])
                unique_formats.append(fmt)

        return {
            "success": True,
            "title": info.get('title', 'Extracted Video')[:60],
            "thumbnail": info.get('thumbnail', ''),
            "uploader": info.get('uploader', 'Content Creator'),
            "duration": format_duration(info.get('duration', 0)),
            "formats": unique_formats[:5] if unique_formats else [
                {"quality": "Standard MP4", "size": "Auto", "url": url}
            ]
        }

@app.get("/")
def home():
    return {"status": "online", "message": "SnapLoad Universal Multi-Engine API Ready"}

@app.post("/api/analyze")
def analyze_video(req: VideoRequest):
    url = req.url.strip()
    
    # 1. TikTok Route
    if "tiktok.com" in url:
        res = extract_tiktok(url)
        if res:
            return res

    # 2. Instagram Route
    if "instagram.com" in url:
        res = extract_instagram(url)
        if res:
            return res

    # 3. Universal Multi-Platform Route
    try:
        return extract_universal(url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Download Error: {str(e)}")
