from __future__ import annotations

import html
import os
import time
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
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
        "ui_version": "final-v7",
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


@app.get("/api/poster/{code}")
async def poster(code: int) -> Response:
    info = db.poster_info(code)

    if info is None:
        raise HTTPException(
            status_code=404,
            detail="Kino topilmadi.",
        )

    name, file_id = info

    cached = poster_cache.get(code)

    if cached and time.time() - cached[0] < 3600:
        return Response(
            cached[1],
            media_type=cached[2],
            headers={
                "Cache-Control": "public,max-age=3600",
                "X-Poster-Source": "cache",
            },
        )

    # 1. Telegram'dan to'g'ridan-to'g'ri
    if BOT_TOKEN and file_id:
        try:
            timeout = httpx.Timeout(
                20.0,
                connect=10.0,
            )

            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=True,
            ) as client:

                meta = await client.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/getFile",
                    json={"file_id": file_id},
                )

                payload = meta.json()

                if not meta.is_success or not payload.get("ok"):
                    raise RuntimeError(
                        payload.get("description")
                        or f"Telegram HTTP {meta.status_code}"
                    )

                file_path = (
                    (payload.get("result") or {})
                    .get("file_path", "")
                    .strip()
                )

                if not file_path:
                    raise RuntimeError(
                        "Telegram file_path bermadi."
                    )

                image = await client.get(
                    f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
                )

                image.raise_for_status()

                content_type = (
                    image.headers
                    .get("content-type", "image/jpeg")
                    .split(";")[0]
                    .strip()
                )

                if (
                    content_type.startswith("image/")
                    and "svg" not in content_type
                    and image.content
                ):
                    poster_cache[code] = (
                        time.time(),
                        image.content,
                        content_type,
                    )

                    return Response(
                        image.content,
                        media_type=content_type,
                        headers={
                            "Cache-Control":
                                "public,max-age=3600",
                            "X-Poster-Source":
                                "telegram",
                        },
                    )

        except Exception:
            pass


    # 2. Eski SuperApp poster servisi fallback
    try:
        async with httpx.AsyncClient(
            timeout=20,
            follow_redirects=True,
        ) as client:

            legacy = await client.get(
                f"{LEGACY_POSTER_BASE}/api/poster/{code}",
                params={"v": "final-v7"},
            )

            content_type = (
                legacy.headers
                .get("content-type", "")
                .split(";")[0]
                .strip()
            )

            if (
                legacy.is_success
                and content_type.startswith("image/")
                and "svg" not in content_type
                and legacy.content
            ):
                poster_cache[code] = (
                    time.time(),
                    legacy.content,
                    content_type,
                )

                return Response(
                    legacy.content,
                    media_type=content_type,
                    headers={
                        "Cache-Control":
                            "public,max-age=3600",
                        "X-Poster-Source":
                            "legacy",
                    },
                )

    except Exception:
        pass


    # FAQAT IKKALA USUL HAM ISHLAMASA FALLBACK
    data = placeholder_svg(name, code)

    return Response(
        data,
        media_type="image/svg+xml",
        headers={
            "Cache-Control":
                "no-store,no-cache,max-age=0",
            "X-Poster-Source":
                "fallback",
        },
    )


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


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
