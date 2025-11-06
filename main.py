from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/tiktok")
def tiktok(url: str):
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

@app.get("/test")
def test():
    return {"status": "ok"}
