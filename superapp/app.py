from __future__ import annotations

import hashlib
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from cachetools import TTLCache
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .auth import TelegramAuthError, TelegramUser, validate_init_data
from .db import Database, DatabaseNotConfigured
from .settings import (
    APP_NAME,
    BOT_TOKEN,
    BOT_USERNAME,
    POSTER_CACHE_SECONDS,
    STATIC_DIR,
    TELEGRAM_AUTH_MAX_AGE,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

db = Database()
poster_cache: TTLCache[int, tuple[bytes, str]] = TTLCache(
    maxsize=128,
    ttl=POSTER_CACHE_SECONDS,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.start()
    try:
        yield
    finally:
        db.close()


app = FastAPI(
    title=f"{APP_NAME} Super App API",
    version="1.0.0-staging",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url=None,
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' https://telegram.org 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob: https:; "
        "connect-src 'self'; frame-ancestors 'self' https://web.telegram.org https://*.telegram.org"
    )
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


class FavoriteBody(BaseModel):
    movie_code: int
    enabled: bool = True


class HistoryBody(BaseModel):
    movie_code: int


def verified_user(
    x_telegram_init_data: str = Header(default="", alias="X-Telegram-Init-Data"),
) -> TelegramUser:
    try:
        user = validate_init_data(
            x_telegram_init_data,
            BOT_TOKEN,
            max_age_seconds=TELEGRAM_AUTH_MAX_AGE,
        )
        db.upsert_user(user)
        return user
    except TelegramAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except DatabaseNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health():
    status = db.health()
    return {
        "status": "ok" if status["database"] == "ok" else "degraded",
        "service": "superapp-staging",
        **status,
    }


@app.get("/api/config")
def config():
    return {
        "app_name": APP_NAME,
        "bot_username": BOT_USERNAME,
        "telegram_auth_enabled": bool(BOT_TOKEN),
    }


@app.get("/api/home")
def home():
    try:
        return db.home()
    except DatabaseNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/movies")
def movies(
    q: str = Query(default="", max_length=100),
    genre: str = Query(default="", max_length=100),
    country: str = Query(default="", max_length=100),
    year: str = Query(default="", max_length=10),
    sort: str = Query(default="popular", pattern="^(popular|new|name|year)$"),
    page: int = Query(default=1, ge=1, le=1000),
    limit: int = Query(default=24, ge=1, le=60),
):
    try:
        return db.list_movies(
            q=q.strip(),
            genre=genre.strip(),
            country=country.strip(),
            year=year.strip(),
            sort=sort,
            page=page,
            limit=limit,
        )
    except DatabaseNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/movies/{code}")
def movie_detail(code: int):
    try:
        movie = db.movie(code)
    except DatabaseNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not movie:
        raise HTTPException(status_code=404, detail="Kino topilmadi.")
    return movie


@app.get("/api/genres")
def genres():
    try:
        return {"items": db.genres()}
    except DatabaseNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/me")
def me(user: TelegramUser = Depends(verified_user)):
    return db.upsert_user(user)


@app.get("/api/favorites")
def favorites(user: TelegramUser = Depends(verified_user)):
    return {"items": db.favorites(user.id)}


@app.post("/api/favorites")
def set_favorite(body: FavoriteBody, user: TelegramUser = Depends(verified_user)):
    if db.movie(body.movie_code) is None:
        raise HTTPException(status_code=404, detail="Kino topilmadi.")
    enabled = db.set_favorite(user.id, body.movie_code, body.enabled)
    return {"movie_code": body.movie_code, "enabled": enabled}


@app.post("/api/history")
def record_history(body: HistoryBody, user: TelegramUser = Depends(verified_user)):
    if db.movie(body.movie_code) is None:
        raise HTTPException(status_code=404, detail="Kino topilmadi.")
    db.record_open(user.id, body.movie_code)
    return {"ok": True}


@app.get("/api/poster/{code}")
async def poster(code: int):
    cached = poster_cache.get(code)
    if cached:
        content, content_type = cached
        etag = hashlib.sha256(content).hexdigest()[:24]
        return Response(
            content=content,
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=3600", "ETag": etag},
        )

    try:
        file_id = db.poster_file_id(code)
    except DatabaseNotConfigured:
        file_id = ""
    if not file_id or not BOT_TOKEN:
        return RedirectResponse("/static/placeholder.svg", status_code=307)

    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            meta_response = await client.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/getFile",
                json={"file_id": file_id},
            )
            meta_response.raise_for_status()
            payload = meta_response.json()
            if not payload.get("ok"):
                raise RuntimeError("Telegram getFile javobi noto'g'ri")
            file_path = payload["result"]["file_path"]
            file_response = await client.get(
                f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
            )
            file_response.raise_for_status()
            content_type = file_response.headers.get("content-type", "image/jpeg")
            content = file_response.content
            poster_cache[code] = (content, content_type)
            etag = hashlib.sha256(content).hexdigest()[:24]
            return Response(
                content=content,
                media_type=content_type,
                headers={"Cache-Control": "public, max-age=3600", "ETag": etag},
            )
    except Exception:
        logger.warning("Poster yuklanmadi: code=%s", code, exc_info=True)
        return RedirectResponse("/static/placeholder.svg", status_code=307)
