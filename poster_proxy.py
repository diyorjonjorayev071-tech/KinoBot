import os
import time
import threading

import httpx
import psycopg
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response

from config import TOKEN


app = FastAPI(
    title="xD KINO Internal Poster Proxy",
    docs_url=None,
    redoc_url=None,
)

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

_cache = {}
_cache_lock = threading.Lock()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "worker-poster-proxy",
    }


def _poster_file_id(code: int) -> str:
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL yo'q.")

    last_error = None

    for _ in range(5):
        try:
            with psycopg.connect(
                DATABASE_URL,
                connect_timeout=5,
            ) as conn:

                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT poster_file_id
                        FROM movies
                        WHERE code=%s
                        LIMIT 1
                        """,
                        (code,),
                    )

                    row = cur.fetchone()

                    if not row:
                        return ""

                    return str(row[0] or "").strip()

        except Exception as exc:
            last_error = exc
            time.sleep(1.5)

    if last_error:
        raise last_error

    return ""


@app.get("/poster/{code}")
def poster(code: int):

    now = time.time()

    with _cache_lock:
        cached = _cache.get(code)

    if cached and now - cached[0] < 3600:
        return Response(
            content=cached[1],
            media_type=cached[2],
            headers={
                "Cache-Control": "public,max-age=3600",
                "X-Poster-Proxy": "cache",
            },
        )

    file_id = _poster_file_id(code)

    if not file_id:
        raise HTTPException(
            status_code=404,
            detail="Poster file_id yo'q.",
        )

    if not TOKEN:
        raise HTTPException(
            status_code=503,
            detail="Bot token yo'q.",
        )

    with httpx.Client(
        timeout=25,
        follow_redirects=True,
    ) as client:

        meta = client.post(
            f"https://api.telegram.org/bot{TOKEN}/getFile",
            json={
                "file_id": file_id,
            },
        )

        payload = meta.json()

        if not meta.is_success or not payload.get("ok"):
            raise HTTPException(
                status_code=502,
                detail=payload.get("description", "Telegram getFile xatosi"),
            )

        file_path = (
            (payload.get("result") or {})
            .get("file_path", "")
            .strip()
        )

        if not file_path:
            raise HTTPException(
                status_code=502,
                detail="Telegram file_path bermadi.",
            )

        image = client.get(
            f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
        )

        image.raise_for_status()

    content_type = (
        image.headers
        .get("content-type", "image/jpeg")
        .split(";")[0]
        .strip()
    )

    if (
        not content_type.startswith("image/")
        or "svg" in content_type.lower()
        or not image.content
    ):
        raise HTTPException(
            status_code=502,
            detail="Telegram real poster bermadi.",
        )

    with _cache_lock:
        _cache[code] = (
            now,
            image.content,
            content_type,
        )

        # Xotira haddan oshmasin
        if len(_cache) > 400:
            oldest = min(
                _cache,
                key=lambda key: _cache[key][0],
            )
            _cache.pop(oldest, None)

    return Response(
        content=image.content,
        media_type=content_type,
        headers={
            "Cache-Control": "public,max-age=3600",
            "X-Poster-Proxy": "telegram",
        },
    )
