from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import requests
from typing import Optional

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/tiktok")
def tiktok(url: str = Query(..., description="TikTok video URL")):
    try:
        api_url = "https://www.tikwm.com/api/"
        resp = requests.get(api_url, params={"url": url}, timeout=20)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail="Upstream error")
        data = resp.json()
        if data.get("code") != 0:
            raise HTTPException(status_code=400, detail=data.get("msg", "Invalid response"))
        d = data.get("data", {})
        return {
            "title": d.get("title") or "TikTok Video",
            "thumbnail_url": d.get("cover") or d.get("origin_cover"),
            "download_url": d.get("play") or d.get("wmplay")
        }
    except requests.Timeout:
        raise HTTPException(status_code=504, detail="Timed out fetching video info")
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Upstream request failed: {e}")


def _proxy_stream(upstream_url: str):
    try:
        upstream = requests.get(upstream_url, stream=True, timeout=30)
    except requests.Timeout:
        raise HTTPException(status_code=504, detail="Timed out fetching video stream")
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Upstream request failed: {e}")

    if upstream.status_code != 200:
        raise HTTPException(status_code=upstream.status_code, detail="Upstream error while streaming")

    content_type = upstream.headers.get("Content-Type", "application/octet-stream")

    def iter_chunks():
        for chunk in upstream.iter_content(chunk_size=1024 * 64):
            if chunk:
                yield chunk

    return iter_chunks, content_type


@app.get("/api/stream")
def stream_video(url: str = Query(..., description="Direct video URL")):
    iterator, content_type = _proxy_stream(url)
    return StreamingResponse(iterator(), media_type=content_type)


@app.get("/api/download")
def download_video(url: str = Query(..., description="Direct video URL"), filename: Optional[str] = None):
    iterator, content_type = _proxy_stream(url)
    safe_name = (filename or "video").strip().replace("/", "-")
    if not safe_name.lower().endswith(".mp4"):
        safe_name += ".mp4"
    headers = {"Content-Disposition": f"attachment; filename=\"{safe_name}\""}
    return StreamingResponse(iterator(), media_type=content_type, headers=headers)


@app.get("/test")
def test():
    return {"status": "ok"}
