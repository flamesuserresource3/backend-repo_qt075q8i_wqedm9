import os
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
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


@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    
    try:
        # Try to import database module
        from database import db
        
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            
            # Try to list collections to verify connectivity
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]  # Show first 10 collections
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
            
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    # Check environment variables
    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    
    return response


@app.get("/api/tiktok")
def tiktok_download(url: Optional[str] = Query(None, description="TikTok video URL")):
    """
    Proxy endpoint that fetches TikTok video metadata and a no-watermark download URL
    using tikwm.com public API and returns a simplified response.
    """
    if not url:
        raise HTTPException(status_code=400, detail="Missing 'url' query parameter")

    # TikWM public API
    api_endpoint = "https://www.tikwm.com/api/"
    try:
        r = requests.get(api_endpoint, params={"url": url}, timeout=15)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Failed to reach upstream service: {str(e)}")

    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Upstream responded with status {r.status_code}")

    try:
        payload = r.json()
    except ValueError:
        raise HTTPException(status_code=502, detail="Invalid response from upstream service")

    if payload.get("code") != 0 or not payload.get("data"):
        msg = payload.get("msg") or "Failed to fetch video info"
        raise HTTPException(status_code=400, detail=msg)

    data = payload["data"]
    # Prefer HD play, fallback to play (both are no-watermark according to API docs)
    download_url = data.get("hdplay") or data.get("play")
    if not download_url:
        # As a last resort, fall back to wmplay but inform client
        download_url = data.get("wmplay")

    result = {
        "title": data.get("title") or "TikTok Video",
        "thumbnail_url": data.get("cover") or data.get("origin_cover") or data.get("dynamic_cover"),
        "download_url": download_url,
        "author": data.get("author") or {},
        "duration": data.get("duration")
    }

    if not result["download_url"]:
        raise HTTPException(status_code=400, detail="Could not find a downloadable URL for this video")

    return result


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
