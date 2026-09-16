from fastapi import FastAPI, HTTPException, Query
from app.config import settings
from app.queue import submit
from app.redis_client import redis_client

app = FastAPI(
    title="Telegram Music Resolver API",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

@app.get("/")
async def root():
    return {
        "ok": True,
        "service": "telegram-music-resolver",
        "version": "2.0.0",
    }

@app.get("/health")
async def health():
    try:
        await redis_client.ping()
        return {"ok": True, "redis": "up"}
    except Exception:
        return {"ok": False, "redis": "down"}

@app.get("/search")
async def search(q: str = Query(..., min_length=1, max_length=200)):
    try:
        return await submit("search", q.strip())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/info")
async def info(url: str = Query(..., min_length=5)):
    try:
        return await submit("info", url.strip())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/stream")
async def stream(url: str = Query(..., min_length=5)):
    try:
        return await submit("stream", url.strip())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
