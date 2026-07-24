from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = Path(__file__).resolve().parent / "static"
SEED_DB_PATH = Path(os.getenv("SEED_DB_PATH", BASE_DIR / "movies-backup.db"))

APP_NAME = os.getenv("APP_NAME", "xD KINO")
BOT_USERNAME = os.getenv("BOT_USERNAME", "xDKinoCodeBot").lstrip("@")
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
TELEGRAM_AUTH_MAX_AGE = int(os.getenv("TELEGRAM_AUTH_MAX_AGE", "86400"))
POSTER_CACHE_SECONDS = int(os.getenv("POSTER_CACHE_SECONDS", "3600"))


def _load_bot_token() -> str:
    token = os.getenv("BOT_TOKEN", "").strip()
    if token:
        return token

    # Hozirgi bot loyihasi bilan orqaga moslik. Keyinchalik Railway Variables afzal.
    try:
        from config import TOKEN  # type: ignore

        return str(TOKEN).strip()
    except Exception:
        return ""


BOT_TOKEN = _load_bot_token()
