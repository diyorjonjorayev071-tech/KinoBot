from __future__ import annotations

import html
import os
import time
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from db import Database, DatabaseError

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
BOT_TOKEN = (os.getenv("BOT_TOKEN") or "").strip()
BOT_USERNAME = (os.getenv("BOT_USERNAME") or "xDKinoCodeBot").strip().lstrip("@")
BOT_START_PREFIX = (os.getenv("BOT_START_PREFIX") or "movie_").strip()
LEGACY_POSTER_BASE = (os.getenv("LEGACY_POSTER_BASE") or "https://superapp-production-c942.up.railway.app").rstrip("/")

app = FastAPI(title="xD KINO Clean", version="1.0.0")
db = Database()
poster_cache: dict[int, tuple[float, bytes, str]] = {}


# FRONTEND_NO_CACHE_V5
@app.middleware("http")
async def frontend_no_cache(request, call_next):
    response = await call_next(request)

    if (
        request.url.path in {"/", "/v5"}
        or request.url.path.startswith("/static/")
    ):
        response.headers["Cache-Control"] = (
            "no-store, no-cache, must-revalidate, max-age=0"
        )
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

    return response



@app.get("/health")
def health() -> dict[str, Any]:
    try:
        info = db.health()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "status": "ok",
        "service": "xd-kino-clean",
        "ui_version": "final-v29-splash-posters",
        **info,
    }


@app.get("/api/config")
def config() -> dict[str, Any]:
    return {
        "bot_username": BOT_USERNAME,
        "bot_start_prefix": BOT_START_PREFIX,
        "telegram_posters": bool(BOT_TOKEN),
    }


@app.get("/api/home")
def home() -> dict[str, Any]:
    try:
        return db.home()
    except DatabaseError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/movies")
def movies(
    q: str = Query(default="", max_length=100),
    genre: str = Query(default="", max_length=100),
    country: str = Query(default="", max_length=100),
    year: str = Query(default="", max_length=10),
    content_type: str = Query(default="", max_length=30),
    recommended: bool = False,
    sort: str = Query(default="popular", pattern="^(popular|new|name|year)$"),
    page: int = Query(default=1, ge=1, le=1000),
    limit: int = Query(default=24, ge=1, le=60),
) -> dict[str, Any]:
    return db.list_movies(
        q=q.strip(), genre=genre.strip(), country=country.strip(), year=year.strip(),
        content_type=content_type.strip(), recommended=recommended, sort=sort,
        page=page, limit=limit,
    )


@app.get("/api/movie/{code}")
def movie(code: int) -> dict[str, Any]:
    item = db.movie(code)
    if item is None:
        raise HTTPException(status_code=404, detail="Kino topilmadi.")
    return item


@app.post("/api/view/{code}")
def add_view(code: int) -> dict[str, Any]:
    if db.movie(code) is None:
        raise HTTPException(status_code=404, detail="Kino topilmadi.")
    return {"ok": True, "views": db.increase_views(code)}


@app.get("/api/filter-options")
def filter_options() -> dict[str, Any]:
    return db.filter_options()


def placeholder_svg(name: str, code: int) -> bytes:
    safe = html.escape((name or "xD KINO")[:30])
    initials = "".join(word[:1].upper() for word in safe.split()[:2]) or "XD"
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="600" height="900" viewBox="0 0 600 900">
    <defs>
      <radialGradient id="g" cx="50%" cy="38%" r="75%"><stop offset="0" stop-color="#183b20"/><stop offset=".5" stop-color="#0a120c"/><stop offset="1" stop-color="#020403"/></radialGradient>
      <filter id="glow"><feGaussianBlur stdDeviation="8" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
    </defs>
    <rect width="600" height="900" fill="url(#g)"/>
    <circle cx="300" cy="360" r="110" fill="#0d1c10" stroke="#46ef5a" stroke-width="5" opacity=".96"/>
    <text x="300" y="390" text-anchor="middle" font-family="Arial,sans-serif" font-size="86" font-weight="800" fill="#52f062" filter="url(#glow)">{initials}</text>
    <text x="300" y="585" text-anchor="middle" font-family="Arial,sans-serif" font-size="34" font-weight="700" fill="#f1f6f1">{safe}</text>
    <text x="300" y="640" text-anchor="middle" font-family="Arial,sans-serif" font-size="24" fill="#7e8a80">xD KINO • {code}</text>
    </svg>"""
    return svg.encode("utf-8")



# ============================================================
# FINAL_V25_FAVORITES_PROXY
# ============================================================

FAVORITES_BACKEND = (
    os.getenv(
        "FAVORITES_BACKEND",
        "https://superapp-production-c942.up.railway.app",
    )
    .strip()
    .rstrip("/")
)


async def _favorites_proxy(request: Request) -> Response:

    init_data = (
        request.headers
        .get("X-Telegram-Init-Data", "")
        .strip()
    )

    if not init_data:
        return Response(
            content='{"detail":"Telegram initData yoq."}',
            status_code=401,
            media_type="application/json",
        )

    headers = {
        "X-Telegram-Init-Data": init_data,
    }

    body = None

    if request.method == "POST":
        body = await request.body()

        headers["Content-Type"] = (
            request.headers.get(
                "Content-Type",
                "application/json",
            )
        )

    try:

        async with httpx.AsyncClient(
            timeout=20,
            follow_redirects=True,
        ) as client:

            upstream = await client.request(
                request.method,
                f"{FAVORITES_BACKEND}/api/favorites",
                headers=headers,
                content=body,
            )

        content_type = (
            upstream.headers
            .get(
                "content-type",
                "application/json",
            )
            .split(";")[0]
            .strip()
        )

        return Response(
            content=upstream.content,
            status_code=upstream.status_code,
            media_type=content_type,
            headers={
                "Cache-Control": "no-store",
                "X-Favorites-Source": "proxy",
            },
        )

    except Exception as exc:

        return Response(
            content=(
                '{"detail":"Favorites backend vaqtincha javob bermadi."}'
            ),
            status_code=502,
            media_type="application/json",
            headers={
                "Cache-Control": "no-store",
                "X-Favorites-Error": type(exc).__name__,
            },
        )


@app.get("/api/favorites")
async def favorites_get(request: Request) -> Response:
    return await _favorites_proxy(request)


@app.post("/api/favorites")
async def favorites_post(request: Request) -> Response:
    return await _favorites_proxy(request)



@app.get("/api/poster/{code}")
async def poster(code: int) -> Response:

    info = db.poster_info(code)

    if info is None:
        raise HTTPException(status_code=404, detail="Kino topilmadi.")

    name, file_id = info

    cached = poster_cache.get(code)

    if (
        cached
        and len(cached) >= 3
        and time.time() - cached[0] < 3600
    ):
        return Response(
            content=cached[1],
            media_type=cached[2],
            headers={
                "Cache-Control": "public,max-age=3600",
                "X-Poster-Source": "cache",
            },
        )

    if not file_id:
        data = placeholder_svg(name, code)
        return Response(
            data,
            media_type="image/svg+xml",
            headers={
                "Cache-Control": "no-store",
                "X-Poster-Source": "fallback",
                "X-Poster-Error": "no_file_id",
            },
        )

    if not BOT_TOKEN:
        data = placeholder_svg(name, code)
        return Response(
            data,
            media_type="image/svg+xml",
            headers={
                "Cache-Control": "no-store",
                "X-Poster-Source": "fallback",
                "X-Poster-Error": "no_bot_token",
            },
        )

    try:
        async with httpx.AsyncClient(
            timeout=25,
            follow_redirects=True,
        ) as client:

            meta = await client.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/getFile",
                json={"file_id": file_id},
            )

            if not meta.is_success:
                raise RuntimeError(f"getFile_http_{meta.status_code}")

            payload = meta.json()

            if not payload.get("ok"):
                raise RuntimeError("getFile_not_ok")

            file_path = str(
                (payload.get("result") or {}).get("file_path") or ""
            ).strip()

            if not file_path:
                raise RuntimeError("no_file_path")

            image = await client.get(
                f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
            )

            if not image.is_success:
                raise RuntimeError(f"download_http_{image.status_code}")

        raw = image.content

        if not raw:
            raise RuntimeError("download_empty")

        content_type = (
            image.headers.get("content-type", "")
            .split(";")[0]
            .strip()
            .lower()
        )

        # Telegram ayrim posterlarni application/octet-stream
        # ko'rinishida qaytaradi. poster_file_id esa rasmga tegishli,
        # shuning uchun file_path kengaytmasidan MIME aniqlanadi.
        if (
            not content_type.startswith("image/")
            or "svg" in content_type
        ):
            lower_path = file_path.lower()

            if lower_path.endswith((".jpg", ".jpeg")):
                content_type = "image/jpeg"
            elif lower_path.endswith(".png"):
                content_type = "image/png"
            elif lower_path.endswith(".webp"):
                content_type = "image/webp"
            elif lower_path.endswith(".gif"):
                content_type = "image/gif"
            else:
                # Telegram photo fayllari odatda JPEG.
                content_type = "image/jpeg"

        poster_cache[code] = (
            time.time(),
            image.content,
            content_type,
        )

        return Response(
            image.content,
            media_type=content_type,
            headers={
                "Cache-Control": "public,max-age=3600",
                "X-Poster-Source": "telegram",
            },
        )

    except Exception as exc:

        error_code = type(exc).__name__

        text = str(exc)

        for known in (
            "getFile_http_401",
            "getFile_http_404",
            "getFile_http_400",
            "getFile_not_ok",
            "no_file_path",
            "download_http_401",
            "download_http_404",
            "download_not_image",
        ):
            if known in text:
                error_code = known
                break

        data = placeholder_svg(name, code)

        return Response(
            data,
            media_type="image/svg+xml",
            headers={
                "Cache-Control": "no-store",
                "X-Poster-Source": "fallback",
                "X-Poster-Error": error_code,
            },
        )


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")



# FINAL_V8_NO_CACHE
@app.middleware("http")
async def final_v8_no_cache(request, call_next):
    response = await call_next(request)

    if (
        request.url.path == "/"
        or request.url.path.startswith("/static/")
    ):
        response.headers["Cache-Control"] = (
            "no-store, no-cache, must-revalidate, max-age=0"
        )
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

    return response


@app.get("/")
def index() -> FileResponse:
    return FileResponse(
        STATIC_DIR / "index.html",
        headers={
            "Cache-Control":
            "no-store, no-cache, must-revalidate, max-age=0"
        },
    )


@app.get("/v5")
def index_v5() -> FileResponse:
    return FileResponse(
        STATIC_DIR / "index.html",
        headers={
            "Cache-Control":
            "no-store, no-cache, must-revalidate, max-age=0"
        },
    )
