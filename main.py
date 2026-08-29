from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp

app = FastAPI(title="Super Media Downloader API")

# Enable CORS for Frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoRequest(BaseModel):
    url: str

@app.post("/api/analyze")
def analyze_video(req: VideoRequest):
    if not req.url:
        raise HTTPException(status_code=400, detail="URL is required")
        
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(req.url, download=False)
            
            formats_list = []
            
            # Formats filter
            for f in info.get('formats', []):
                # Video + Audio combined or progressive mp4
                if f.get('ext') == 'mp4' and f.get('url'):
                    res = f.get('resolution') or f"{f.get('height', 'HD')}p"
                    filesize = f.get('filesize') or f.get('filesize_approx')
                    size_mb = f"{round(filesize / (1024 * 1024), 1)} MB" if filesize else "Direct Stream"
                    
                    formats_list.append({
                        "quality": res,
                        "size": size_mb,
                        "url": f.get('url'),
                        "type": "video"
                    })
                
                # Audio (MP3/M4A)
                elif (f.get('ext') in ['m4a', 'mp3'] or f.get('acodec') != 'none' and f.get('vcodec') == 'none') and f.get('url'):
                    filesize = f.get('filesize') or f.get('filesize_approx')
                    size_mb = f"{round(filesize / (1024 * 1024), 1)} MB" if filesize else "Audio"
                    formats_list.append({
                        "quality": "MP3 Audio (Highest Quality)",
                        "size": size_mb,
                        "url": f.get('url'),
                        "type": "audio"
                    })

            # Clean and unique list
            unique_formats = []
            seen_qualities = set()
            for item in formats_list:
                if item['quality'] not in seen_qualities:
                    seen_qualities.add(item['quality'])
                    unique_formats.append(item)

            return {
                "success": True,
                "title": info.get('title', 'Video Download'),
                "thumbnail": info.get('thumbnail', ''),
                "uploader": info.get('uploader', 'Content Creator'),
                "duration": f"{info.get('duration', 0) // 60}:{info.get('duration', 0) % 60:02d}" if info.get('duration') else "Live/Short",
                "formats": unique_formats[:5] # Best 5 formats
            }
            
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid link or private video: " + str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)