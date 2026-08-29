from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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
        return "Standard Size"
    mb = bytes_val / (1024 * 1024)
    return f"{mb:.1f} MB"

def format_duration(seconds):
    if not seconds:
        return "N/A"
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}:{secs:02d}"

@app.get("/")
def home():
    return {"status": "active", "message": "SnapLoad API is Running"}

@app.post("/api/analyze")
def analyze_video(req: VideoRequest):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'no_color': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios', 'mweb']
            },
            'tiktok': {
                'app_version': 'latest'
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1'
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(req.url, download=False)
            
            formats = []
            if 'formats' in info:
                for f in info['formats']:
                    url = f.get('url')
                    if not url:
                        continue
                    
                    ext = f.get('ext', 'mp4')
                    vcodec = f.get('vcodec', 'none')
                    acodec = f.get('acodec', 'none')
                    format_note = f.get('format_note') or f.get('resolution') or (f"{f.get('height')}p" if f.get('height') else None)
                    filesize = f.get('filesize') or f.get('filesize_approx')

                    if vcodec != 'none' or acodec != 'none':
                        label = f"{format_note} ({ext})" if format_note else f"Media ({ext})"
                        formats.append({
                            "quality": label,
                            "size": format_size(filesize),
                            "url": url
                        })

            if not formats and info.get('url'):
                formats.append({
                    "quality": "Direct Video Link (HD)",
                    "size": "Auto",
                    "url": info.get('url')
                })

            # Duplicate URLs remove karein
            unique_formats = []
            seen_urls = set()
            for fmt in formats:
                if fmt['url'] not in seen_urls:
                    seen_urls.add(fmt['url'])
                    unique_formats.append(fmt)

            return {
                "success": True,
                "title": info.get('title', 'Extracted Video'),
                "thumbnail": info.get('thumbnail', ''),
                "uploader": info.get('uploader', 'Creator'),
                "duration": format_duration(info.get('duration', 0)),
                "formats": unique_formats[:5] if unique_formats else [
                    {"quality": "Standard MP4", "size": "Auto", "url": req.url}
                ]
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Download Error: {str(e)}")
