import os
import random
import shutil
import sqlite3
import re

try:
    import psycopg
except ImportError:
    psycopg = None
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent
VOLUME_DIR = os.getenv("RAILWAY_VOLUME_MOUNT_PATH", "").strip()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

if VOLUME_DIR:
    DB_PATH = Path(VOLUME_DIR) / "movies.db"
else:
    DB_PATH = BASE_DIR / "movies.db"

DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Birinchi Railway ishga tushishida lokal backupni bo'sh volume ichiga ko'chiradi.
if not DB_PATH.exists():
    for seed_name in ("movies-backup.db", "movies.db"):
        seed_path = BASE_DIR / seed_name
        if (
            seed_path.exists()
            and seed_path.resolve() != DB_PATH.resolve()
            and seed_path.stat().st_size > 0
        ):
            shutil.copy2(seed_path, DB_PATH)
            break

conn = sqlite3.connect(
    str(DB_PATH),
    check_same_thread=False,
    timeout=30,
)
conn.execute("PRAGMA foreign_keys = ON")
conn.execute("PRAGMA busy_timeout = 30000")
conn.execute("PRAGMA journal_mode = WAL")
cursor = conn.cursor()
db_lock = threading.RLock()


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _commit() -> None:
    conn.commit()


def _table_columns(table: str) -> set[str]:
    cursor.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cursor.fetchall()}



def _postgres_required_for_shared_write() -> bool:
    return bool(
        os.getenv("RAILWAY_PROJECT_ID", "").strip()
        or os.getenv("RAILWAY_ENVIRONMENT_ID", "").strip()
    )


def _require_shared_database() -> None:
    if _postgres_required_for_shared_write() and not DATABASE_URL:
        raise RuntimeError(
            "Railway worker uchun DATABASE_URL sozlanmagan. "
            "Kino faqat bot bazasida qolib ketmasligi uchun yozish to'xtatildi."
        )


def _upsert_movie_postgres(
    *,
    code: int,
    name: str,
    year: str,
    country: str,
    genre: str,
    language: str,
    imdb: str,
    poster_file_id: str,
    file_id: str,
    views: int,
    created_at: str,
    quality: str,
    content_type: str,
    is_recommended: bool,
    description: str,
) -> None:
    if not DATABASE_URL:
        return
    if psycopg is None:
        raise RuntimeError("psycopg paketi o'rnatilmagan.")

    with psycopg.connect(DATABASE_URL) as pg_conn:
        with pg_conn.cursor() as pg_cursor:
            pg_cursor.execute(
                """
                INSERT INTO movies(
                    code, name, year, country, genre, language, imdb,
                    trailer_file_id, poster_file_id, file_id, views, created_at,
                    content_type, is_recommended, description
                )
                VALUES(%s, %s, %s, %s, %s, %s, %s, '', %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(code) DO UPDATE SET
                    name=EXCLUDED.name,
                    year=EXCLUDED.year,
                    country=EXCLUDED.country,
                    genre=EXCLUDED.genre,
                    language=EXCLUDED.language,
                    imdb=EXCLUDED.imdb,
                    trailer_file_id='',
                    poster_file_id=EXCLUDED.poster_file_id,
                    file_id=EXCLUDED.file_id,
                    views=GREATEST(movies.views, EXCLUDED.views),
                    content_type=EXCLUDED.content_type,
                    is_recommended=EXCLUDED.is_recommended,
                    description=EXCLUDED.description
                """,
                (
                    code, name, year, country, genre, language, imdb,
                    poster_file_id, file_id, views, created_at,
                    content_type, bool(is_recommended), description,
                ),
            )
            pg_cursor.execute(
                """
                INSERT INTO movie_qualities(movie_code, quality, file_id, created_at)
                VALUES(%s, %s, %s, %s)
                ON CONFLICT(movie_code, quality)
                DO UPDATE SET
                    file_id=EXCLUDED.file_id,
                    created_at=EXCLUDED.created_at
                """,
                (code, quality, file_id, created_at),
            )


def _upsert_quality_postgres(
    movie_code: int,
    quality: str,
    file_id: str,
    created_at: str,
) -> None:
    if not DATABASE_URL:
        return
    if psycopg is None:
        raise RuntimeError("psycopg paketi o'rnatilmagan.")

    with psycopg.connect(DATABASE_URL) as pg_conn:
        with pg_conn.cursor() as pg_cursor:
            pg_cursor.execute(
                """
                INSERT INTO movie_qualities(movie_code, quality, file_id, created_at)
                VALUES(%s, %s, %s, %s)
                ON CONFLICT(movie_code, quality)
                DO UPDATE SET
                    file_id=EXCLUDED.file_id,
                    created_at=EXCLUDED.created_at
                """,
                (movie_code, quality, file_id, created_at),
            )
            pg_cursor.execute(
                """
                UPDATE movies
                SET file_id=%s
                WHERE code=%s
                  AND (file_id IS NULL OR TRIM(file_id)='')
                """,
                (file_id, movie_code),
            )


def _sync_movie_postgres_from_sqlite(movie_code: int) -> bool:
    """Bitta kino va uning barcha sifatlarini SQLite'dan PostgreSQL'ga tenglaydi."""
    if not DATABASE_URL:
        return False
    if psycopg is None:
        raise RuntimeError("psycopg paketi o'rnatilmagan.")

    with db_lock:
        cursor.execute(
            """
            SELECT code, name, year, country, genre, language, imdb,
                   poster_file_id, file_id, views, created_at,
                   content_type, is_recommended, description
            FROM movies
            WHERE code=?
            """,
            (movie_code,),
        )
        movie_row = cursor.fetchone()
        if not movie_row:
            return False

        cursor.execute(
            """
            SELECT quality, file_id, created_at
            FROM movie_qualities
            WHERE movie_code=?
            ORDER BY
                CASE quality
                    WHEN '360p' THEN 1
                    WHEN '480p' THEN 2
                    WHEN '720p' THEN 3
                    WHEN '1080p' THEN 4
                    WHEN 'Original' THEN 5
                    ELSE 6
                END,
                quality
            """,
            (movie_code,),
        )
        quality_rows = cursor.fetchall()

    (
        code, name, year, country, genre, language, imdb,
        poster_file_id, file_id, views, created_at,
        content_type, is_recommended, description,
    ) = movie_row

    with psycopg.connect(DATABASE_URL) as pg_conn:
        with pg_conn.cursor() as pg_cursor:
            pg_cursor.execute(
                """
                INSERT INTO movies(
                    code, name, year, country, genre, language, imdb,
                    trailer_file_id, poster_file_id, file_id, views, created_at,
                    content_type, is_recommended, description
                )
                VALUES(%s, %s, %s, %s, %s, %s, %s, '', %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(code) DO UPDATE SET
                    name=EXCLUDED.name,
                    year=EXCLUDED.year,
                    country=EXCLUDED.country,
                    genre=EXCLUDED.genre,
                    language=EXCLUDED.language,
                    imdb=EXCLUDED.imdb,
                    trailer_file_id='',
                    poster_file_id=EXCLUDED.poster_file_id,
                    file_id=EXCLUDED.file_id,
                    views=GREATEST(movies.views, EXCLUDED.views),
                    content_type=EXCLUDED.content_type,
                    is_recommended=EXCLUDED.is_recommended,
                    description=EXCLUDED.description
                """,
                (
                    code, name, year, country, genre, language, imdb,
                    poster_file_id or '', file_id or '', int(views or 0), created_at,
                    content_type or 'Kino', bool(is_recommended), description or '',
                ),
            )
            pg_cursor.execute(
                "DELETE FROM movie_qualities WHERE movie_code=%s",
                (code,),
            )
            for quality, quality_file_id, quality_created_at in quality_rows:
                pg_cursor.execute(
                    """
                    INSERT INTO movie_qualities(movie_code, quality, file_id, created_at)
                    VALUES(%s, %s, %s, %s)
                    ON CONFLICT(movie_code, quality)
                    DO UPDATE SET
                        file_id=EXCLUDED.file_id,
                        created_at=EXCLUDED.created_at
                    """,
                    (code, quality, quality_file_id, quality_created_at),
                )
    return True


# EDIT_AND_QUALITY_POSTGRES_SYNC_V2

def sync_sqlite_movies_to_postgres() -> int:
    if not DATABASE_URL:
        return 0
    if psycopg is None:
        raise RuntimeError("psycopg paketi o'rnatilmagan.")

    with db_lock:
        movie_rows = cursor.execute(
            """
            SELECT code, name, year, country, genre, language, imdb,
                   poster_file_id, file_id, views, created_at,
                   content_type, is_recommended, description
            FROM movies
            ORDER BY id
            """
        ).fetchall()
        quality_rows = cursor.execute(
            """
            SELECT movie_code, quality, file_id, created_at
            FROM movie_qualities
            ORDER BY id
            """
        ).fetchall()

    with psycopg.connect(DATABASE_URL) as pg_conn:
        with pg_conn.cursor() as pg_cursor:
            for row in movie_rows:
                pg_cursor.execute(
                    """
                    INSERT INTO movies(
                        code, name, year, country, genre, language, imdb,
                        trailer_file_id, poster_file_id, file_id, views, created_at,
                        content_type, is_recommended, description
                    )
                    VALUES(%s, %s, %s, %s, %s, %s, %s, '', %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT(code) DO UPDATE SET
                        name=EXCLUDED.name,
                        year=EXCLUDED.year,
                        country=EXCLUDED.country,
                        genre=EXCLUDED.genre,
                        language=EXCLUDED.language,
                        imdb=EXCLUDED.imdb,
                        trailer_file_id='',
                        poster_file_id=EXCLUDED.poster_file_id,
                        file_id=EXCLUDED.file_id,
                        views=GREATEST(movies.views, EXCLUDED.views),
                        content_type=EXCLUDED.content_type,
                        is_recommended=EXCLUDED.is_recommended,
                        description=EXCLUDED.description
                    """,
                    row,
                )

            for row in quality_rows:
                pg_cursor.execute(
                    """
                    INSERT INTO movie_qualities(
                        movie_code, quality, file_id, created_at
                    )
                    VALUES(%s, %s, %s, %s)
                    ON CONFLICT(movie_code, quality)
                    DO UPDATE SET
                        file_id=EXCLUDED.file_id,
                        created_at=EXCLUDED.created_at
                    """,
                    row,
                )

    return len(movie_rows)


# SHARED_MOVIE_DATABASE_V1

def normalize_genres(value: str) -> str:
    raw = " ".join(str(value or "").strip().split())
    if not raw:
        return ""

    aliases = {
        "sarguzash": "Sarguzasht",
        "sarguzasht": "Sarguzasht",
        "adventure": "Sarguzasht",
        "drama melodrama": "Drama",
        "drama-melodrama": "Drama",
        "melodrama": "Drama",
        "drama": "Drama",
        "qo'rqinchli": "Qo‘rqinchli",
        "qo‘rqinchli": "Qo‘rqinchli",
        "qo`rqinchli": "Qo‘rqinchli",
        "qo'rqinch": "Qo‘rqinchli",
        "qo‘rqinch": "Qo‘rqinchli",
        "ujas": "Qo‘rqinchli",
        "dahshat": "Qo‘rqinchli",
        "horror": "Qo‘rqinchli",
        "jangari": "Jangari",
        "komediya": "Komediya",
        "detektiv": "Detektiv",
        "fantastik": "Fantastika", "fantastika": "Fantastika",
        "triller": "Triller",
        "tarixiy": "Tarixiy",
        "oilaviy": "Oilaviy",
        "romantik": "Romantik",
    }

    if raw.casefold() in aliases:
        return aliases[raw.casefold()]

    parts = re.split(r"\s*[,/;|]+\s*", raw)
    result = []
    seen = set()
    for part in parts:
        cleaned = " ".join(part.strip().split())
        if not cleaned:
            continue
        canonical = aliases.get(cleaned.casefold(), cleaned[:1].upper() + cleaned[1:])
        key = canonical.casefold()
        if key not in seen:
            seen.add(key)
            result.append(canonical)
    return ", ".join(result)


def normalize_quality(quality: str) -> str:
    value = " ".join(str(quality).strip().split())
    if not value:
        raise ValueError("Sifat nomi bo'sh bo'lmasligi kerak.")
    if len(value) > 24:
        raise ValueError("Sifat nomi 24 belgidan oshmasligi kerak.")

    common = {
        "360": "360p",
        "360p": "360p",
        "480": "480p",
        "480p": "480p",
        "720": "720p",
        "720p": "720p",
        "1080": "1080p",
        "1080p": "1080p",
        "original": "Original",
        "asl": "Original",
    }
    return common.get(value.lower(), value)


def init_database() -> None:
    with db_lock:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS movies(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code INTEGER UNIQUE,
                name TEXT NOT NULL,
                year TEXT DEFAULT '',
                country TEXT DEFAULT '',
                genre TEXT DEFAULT '',
                language TEXT DEFAULT '',
                imdb TEXT DEFAULT '',
                trailer_file_id TEXT DEFAULT '',
                poster_file_id TEXT DEFAULT '',
                file_id TEXT NOT NULL,
                views INTEGER DEFAULT 0,
                created_at TEXT DEFAULT '',
                content_type TEXT DEFAULT 'Kino',
                is_recommended INTEGER DEFAULT 0,
                description TEXT DEFAULT ''
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users(
                user_id INTEGER PRIMARY KEY,
                created_at TEXT DEFAULT ''
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS favorites(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                movie_code INTEGER,
                created_at TEXT DEFAULT '',
                UNIQUE(user_id, movie_code)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS movie_qualities(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                movie_code INTEGER NOT NULL,
                quality TEXT NOT NULL,
                file_id TEXT NOT NULL,
                created_at TEXT DEFAULT '',
                UNIQUE(movie_code, quality)
            )
            """
        )

        movie_columns = {
            "year": "TEXT DEFAULT ''",
            "country": "TEXT DEFAULT ''",
            "genre": "TEXT DEFAULT ''",
            "language": "TEXT DEFAULT ''",
            "imdb": "TEXT DEFAULT ''",
            "trailer_file_id": "TEXT DEFAULT ''",
            "poster_file_id": "TEXT DEFAULT ''",
            "file_id": "TEXT DEFAULT ''",
            "views": "INTEGER DEFAULT 0",
            "created_at": "TEXT DEFAULT ''",
            "content_type": "TEXT DEFAULT 'Kino'",
            "is_recommended": "INTEGER DEFAULT 0",
            "description": "TEXT DEFAULT ''",
        }
        existing_movie_columns = _table_columns("movies")
        for column, column_type in movie_columns.items():
            if column not in existing_movie_columns:
                cursor.execute(f"ALTER TABLE movies ADD COLUMN {column} {column_type}")

        if "created_at" not in _table_columns("users"):
            cursor.execute("ALTER TABLE users ADD COLUMN created_at TEXT DEFAULT ''")

        _commit()

        rows = cursor.execute("SELECT code, genre FROM movies").fetchall()
        for code, old_genre in rows:
            clean_genre = normalize_genres(old_genre)
            if clean_genre != str(old_genre or ""):
                cursor.execute("UPDATE movies SET genre=? WHERE code=?", (clean_genre, code))
        _commit()

        # Oldingi 57 ta kino o'chmaydi: ularning file_id qiymati "Original" sifatiga o'tadi.
        cursor.execute(
            """
            INSERT OR IGNORE INTO movie_qualities(
                movie_code, quality, file_id, created_at
            )
            SELECT code, 'Original', file_id,
                   CASE WHEN created_at = '' THEN ? ELSE created_at END
            FROM movies
            WHERE file_id IS NOT NULL AND TRIM(file_id) != ''
            """,
            (now(),),
        )
        _commit()


init_database()


def add_user(user_id: int) -> None:
    with db_lock:
        cursor.execute(
            "INSERT OR IGNORE INTO users(user_id, created_at) VALUES(?, ?)",
            (user_id, now()),
        )
        _commit()


def get_users():
    with db_lock:
        cursor.execute("SELECT user_id FROM users")
        return cursor.fetchall()


def users_count() -> int:
    with db_lock:
        cursor.execute("SELECT COUNT(*) FROM users")
        return int(cursor.fetchone()[0])


def movies_count() -> int:
    with db_lock:
        cursor.execute("SELECT COUNT(*) FROM movies")
        return int(cursor.fetchone()[0])


def generate_code() -> int:
    with db_lock:
        while True:
            code = random.randint(1000, 9999)
            cursor.execute("SELECT id FROM movies WHERE code=?", (code,))
            if cursor.fetchone() is None:
                return code


def add_movie(
    name,
    year,
    country,
    genre,
    language,
    imdb,
    trailer_file_id,
    poster_file_id,
    file_id,
    quality: str = "Original",
    content_type: str = "Kino",
    is_recommended: bool = False,
    description: str = "",
):
    _require_shared_database()
    code = generate_code()
    quality = normalize_quality(quality)
    genre = normalize_genres(genre)
    description = str(description or "").strip()
    created_at = now()
    clean_poster = poster_file_id or ""
    content_type = str(content_type or "Kino").strip().title()
    if content_type not in {"Kino", "Serial", "Multfilm"}:
        raise ValueError("Kontent turi Kino, Serial yoki Multfilm bo'lishi kerak.")
    is_recommended = bool(is_recommended)

    with db_lock:
        try:
            cursor.execute(
                """
                INSERT INTO movies(
                    code, name, year, country, genre, language, imdb,
                    trailer_file_id, poster_file_id, file_id, views, created_at,
                    content_type, is_recommended, description
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    code,
                    name,
                    year,
                    country,
                    genre,
                    language,
                    imdb,
                    "",
                    clean_poster,
                    file_id,
                    0,
                    created_at,
                    content_type,
                    1 if is_recommended else 0,
                    description,
                ),
            )
            cursor.execute(
                """
                INSERT INTO movie_qualities(movie_code, quality, file_id, created_at)
                VALUES(?, ?, ?, ?)
                """,
                (code, quality, file_id, created_at),
            )

            _upsert_movie_postgres(
                code=code,
                name=name,
                year=year,
                country=country,
                genre=genre,
                language=language,
                imdb=imdb,
                poster_file_id=clean_poster,
                file_id=file_id,
                views=0,
                created_at=created_at,
                quality=quality,
                content_type=content_type,
                is_recommended=is_recommended,
                description=description,
            )
            _commit()
        except Exception:
            conn.rollback()
            raise

    return code



def get_movie(code):
    """Eski handlerlar bilan mos tuple qaytaradi."""
    with db_lock:
        cursor.execute(
            """
            SELECT name, year, country, genre, language, imdb,
                   trailer_file_id, poster_file_id, file_id, views
            FROM movies
            WHERE code=?
            """,
            (code,),
        )
        return cursor.fetchone()


def get_movie_full(code):
    with db_lock:
        cursor.execute(
            """
            SELECT code, name, year, country, genre, language, imdb,
                   poster_file_id, file_id, views, created_at,
                   content_type, is_recommended
            FROM movies
            WHERE code=?
            """,
            (code,),
        )
        return cursor.fetchone()


def update_movie(
    code: int,
    *,
    name: Optional[str] = None,
    year: Optional[str] = None,
    country: Optional[str] = None,
    genre: Optional[str] = None,
    language: Optional[str] = None,
    imdb: Optional[str] = None,
    poster_file_id: Optional[str] = None,
) -> bool:
    _require_shared_database()
    if genre is not None:
        genre = normalize_genres(genre)

    values = {
        "name": name,
        "year": year,
        "country": country,
        "genre": genre,
        "language": language,
        "imdb": imdb,
        "poster_file_id": poster_file_id,
    }
    updates = []
    params = []

    for column, value in values.items():
        if value is not None:
            updates.append(f"{column}=?")
            params.append(value)

    if not updates:
        return False

    params.append(code)
    with db_lock:
        try:
            cursor.execute(
                f"UPDATE movies SET {', '.join(updates)} WHERE code=?",
                params,
            )
            changed = cursor.rowcount > 0
            if changed:
                _sync_movie_postgres_from_sqlite(code)
            _commit()
            return changed
        except Exception:
            conn.rollback()
            raise


# EDIT_MOVIE_SHARED_SYNC_V2



def update_movie_code(old_code: int, new_code: int) -> bool:
    if old_code == new_code:
        return movie_exists(old_code)

    with db_lock:
        cursor.execute("SELECT 1 FROM movies WHERE code=?", (new_code,))
        if cursor.fetchone() is not None:
            return False

        cursor.execute("UPDATE movies SET code=? WHERE code=?", (new_code, old_code))
        if cursor.rowcount == 0:
            return False

        cursor.execute(
            "UPDATE favorites SET movie_code=? WHERE movie_code=?",
            (new_code, old_code),
        )
        cursor.execute(
            "UPDATE movie_qualities SET movie_code=? WHERE movie_code=?",
            (new_code, old_code),
        )
        _commit()
        return True


def increase_views(code):
    with db_lock:
        cursor.execute("UPDATE movies SET views = views + 1 WHERE code=?", (code,))
        _commit()


def _delete_movie_postgres(code: int) -> None:
    """Super App PostgreSQL bazasidan aynan bitta kino kodini o'chiradi."""
    _require_shared_database()

    if not DATABASE_URL:
        return

    if psycopg is None:
        raise RuntimeError("psycopg paketi o'rnatilmagan.")

    with psycopg.connect(DATABASE_URL) as pg_conn:
        with pg_conn.cursor() as pg_cursor:
            pg_cursor.execute(
                "DELETE FROM movies WHERE code=%s",
                (int(code),),
            )


def delete_movie(code):
    # Avval Super App bazasi.
    # PostgreSQL ishlamasa SQLite'dagi kino o'chirilmaydi.
    _delete_movie_postgres(code)

    with db_lock:
        cursor.execute("DELETE FROM movie_qualities WHERE movie_code=?", (code,))
        cursor.execute("DELETE FROM favorites WHERE movie_code=?", (code,))
        cursor.execute("DELETE FROM movies WHERE code=?", (code,))
        _commit()


def movie_exists(code):
    with db_lock:
        cursor.execute("SELECT id FROM movies WHERE code=?", (code,))
        return cursor.fetchone() is not None


def search_movies(query):
    with db_lock:
        cursor.execute(
            """
            SELECT code, name, year, genre
            FROM movies
            WHERE name LIKE ?
            ORDER BY id DESC
            LIMIT 10
            """,
            (f"%{query}%",),
        )
        return cursor.fetchall()


def get_all_movies(limit: int = 100):
    with db_lock:
        cursor.execute(
            """
            SELECT code, name, year, genre
            FROM movies
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        return cursor.fetchall()


def add_movie_quality(movie_code: int, quality: str, file_id: str) -> int:
    _require_shared_database()
    quality = normalize_quality(quality)
    if not file_id:
        raise ValueError("Video file_id bo'sh bo'lmasligi kerak.")

    created_at = now()

    with db_lock:
        try:
            cursor.execute(
                """
                INSERT INTO movie_qualities(movie_code, quality, file_id, created_at)
                VALUES(?, ?, ?, ?)
                ON CONFLICT(movie_code, quality)
                DO UPDATE SET file_id=excluded.file_id, created_at=excluded.created_at
                """,
                (movie_code, quality, file_id, created_at),
            )
            cursor.execute(
                """
                UPDATE movies
                SET file_id=?
                WHERE code=?
                  AND (file_id IS NULL OR TRIM(file_id)='')
                """,
                (file_id, movie_code),
            )
            _sync_movie_postgres_from_sqlite(movie_code)
            _commit()
        except Exception:
            conn.rollback()
            raise

        cursor.execute(
            "SELECT id FROM movie_qualities WHERE movie_code=? AND quality=?",
            (movie_code, quality),
        )
        return int(cursor.fetchone()[0])


# ADD_QUALITY_SHARED_SYNC_V2




def get_movie_qualities(movie_code: int):
    with db_lock:
        cursor.execute(
            """
            SELECT quality, file_id
            FROM movie_qualities
            WHERE movie_code=?
            ORDER BY
                CASE quality
                    WHEN '360p' THEN 1
                    WHEN '480p' THEN 2
                    WHEN '720p' THEN 3
                    WHEN '1080p' THEN 4
                    WHEN 'Original' THEN 5
                    ELSE 6
                END,
                quality
            """,
            (movie_code,),
        )
        return cursor.fetchall()


def get_movie_quality_rows(movie_code: int):
    with db_lock:
        cursor.execute(
            """
            SELECT id, quality
            FROM movie_qualities
            WHERE movie_code=?
            ORDER BY
                CASE quality
                    WHEN '360p' THEN 1
                    WHEN '480p' THEN 2
                    WHEN '720p' THEN 3
                    WHEN '1080p' THEN 4
                    WHEN 'Original' THEN 5
                    ELSE 6
                END,
                quality
            """,
            (movie_code,),
        )
        return cursor.fetchall()


def get_movie_quality(movie_code: int, quality: str):
    with db_lock:
        cursor.execute(
            """
            SELECT file_id
            FROM movie_qualities
            WHERE movie_code=? AND quality=?
            """,
            (movie_code, quality),
        )
        row = cursor.fetchone()
        return row[0] if row else None


def get_movie_quality_by_id(movie_code: int, quality_id: int):
    with db_lock:
        cursor.execute(
            """
            SELECT quality, file_id
            FROM movie_qualities
            WHERE movie_code=? AND id=?
            """,
            (movie_code, quality_id),
        )
        return cursor.fetchone()


def delete_movie_quality(movie_code: int, quality: str) -> bool:
    with db_lock:
        cursor.execute(
            "SELECT id FROM movie_qualities WHERE movie_code=? AND quality=?",
            (movie_code, quality),
        )
        row = cursor.fetchone()
        if not row:
            return False
        return delete_movie_quality_by_id(movie_code, int(row[0])) == "deleted"


def delete_movie_quality_by_id(movie_code: int, quality_id: int) -> str:
    """Natija: deleted, not_found yoki last_quality."""
    _require_shared_database()
    with db_lock:
        try:
            cursor.execute(
                "SELECT file_id FROM movie_qualities WHERE movie_code=? AND id=?",
                (movie_code, quality_id),
            )
            target = cursor.fetchone()
            if not target:
                return "not_found"

            cursor.execute(
                "SELECT COUNT(*) FROM movie_qualities WHERE movie_code=?",
                (movie_code,),
            )
            if int(cursor.fetchone()[0]) <= 1:
                return "last_quality"

            deleted_file_id = target[0]
            cursor.execute(
                "DELETE FROM movie_qualities WHERE movie_code=? AND id=?",
                (movie_code, quality_id),
            )

            cursor.execute("SELECT file_id FROM movies WHERE code=?", (movie_code,))
            movie_row = cursor.fetchone()
            if movie_row and movie_row[0] == deleted_file_id:
                cursor.execute(
                    """
                    SELECT file_id
                    FROM movie_qualities
                    WHERE movie_code=?
                    ORDER BY
                        CASE quality
                            WHEN '360p' THEN 1
                            WHEN '480p' THEN 2
                            WHEN '720p' THEN 3
                            WHEN '1080p' THEN 4
                            WHEN 'Original' THEN 5
                            ELSE 6
                        END,
                        quality
                    LIMIT 1
                    """,
                    (movie_code,),
                )
                replacement = cursor.fetchone()
                if replacement:
                    cursor.execute(
                        "UPDATE movies SET file_id=? WHERE code=?",
                        (replacement[0], movie_code),
                    )

            _sync_movie_postgres_from_sqlite(movie_code)
            _commit()
            return "deleted"
        except Exception:
            conn.rollback()
            raise


# DELETE_QUALITY_SHARED_SYNC_V2



def add_favorite(user_id, movie_code):
    with db_lock:
        cursor.execute(
            """
            INSERT OR IGNORE INTO favorites(user_id, movie_code, created_at)
            VALUES(?, ?, ?)
            """,
            (user_id, movie_code, now()),
        )
        _commit()


def remove_favorite(user_id, movie_code):
    with db_lock:
        cursor.execute(
            "DELETE FROM favorites WHERE user_id=? AND movie_code=?",
            (user_id, movie_code),
        )
        _commit()


def is_favorite(user_id, movie_code):
    with db_lock:
        cursor.execute(
            "SELECT id FROM favorites WHERE user_id=? AND movie_code=?",
            (user_id, movie_code),
        )
        return cursor.fetchone() is not None


def get_favorites(user_id):
    with db_lock:
        cursor.execute(
            """
            SELECT movies.code, movies.name, movies.year, movies.genre
            FROM favorites
            JOIN movies ON favorites.movie_code = movies.code
            WHERE favorites.user_id=?
            ORDER BY favorites.id DESC
            LIMIT 20
            """,
            (user_id,),
        )
        return cursor.fetchall()


def get_top_movies(limit=10):
    with db_lock:
        cursor.execute(
            """
            SELECT code, name, year, genre, views
            FROM movies
            ORDER BY views DESC
            LIMIT ?
            """,
            (limit,),
        )
        return cursor.fetchall()


def get_genres():
    with db_lock:
        cursor.execute(
            """
            SELECT genre, COUNT(*)
            FROM movies
            WHERE genre != ''
            GROUP BY genre
            ORDER BY genre ASC
            """
        )
        return cursor.fetchall()


def get_movies_by_genre(genre):
    with db_lock:
        cursor.execute(
            """
            SELECT code, name, year, genre
            FROM movies
            WHERE genre=?
            ORDER BY id DESC
            LIMIT 20
            """,
            (genre,),
        )
        return cursor.fetchall()


def database_status() -> dict:
    with db_lock:
        cursor.execute("PRAGMA integrity_check")
        integrity = cursor.fetchone()[0]
        return {
            "path": str(DB_PATH),
            "integrity": integrity,
            "movies": movies_count(),
        }

if DATABASE_URL:
    try:
        synced_count = sync_sqlite_movies_to_postgres()
        print(f"✅ SQLite → PostgreSQL kino sinxronlandi: {synced_count} ta")
    except Exception as sync_error:
        print(f"⚠️ SQLite → PostgreSQL boshlang'ich sinxronlash xatosi: {sync_error}")

# SHARED_MOVIE_DATABASE_STARTUP_SYNC_V1


