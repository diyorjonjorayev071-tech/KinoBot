from __future__ import annotations

import os
import random
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from psycopg.rows import tuple_row
    from psycopg_pool import ConnectionPool
except ImportError as exc:  # Railway build paytida tushunarli xato beradi.
    raise RuntimeError(
        "PostgreSQL uchun psycopg paketi o'rnatilmagan. "
        "requirements.txt ichiga psycopg[binary,pool] qo'shing."
    ) from exc

BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
VOLUME_DIR = os.getenv("RAILWAY_VOLUME_MOUNT_PATH", "").strip()

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL bo'sh. PostgreSQL backend ishga tushmadi.")

pool = ConnectionPool(
    conninfo=DATABASE_URL,
    min_size=1,
    max_size=8,
    timeout=30,
    kwargs={"row_factory": tuple_row, "autocommit": False},
    open=True,
)

db_lock = threading.RLock()
BACKEND = "postgresql"


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


QUALITY_ORDER_SQL = """
CASE quality
    WHEN '360p' THEN 1
    WHEN '480p' THEN 2
    WHEN '720p' THEN 3
    WHEN '1080p' THEN 4
    WHEN 'Original' THEN 5
    ELSE 6
END
"""


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


def _sqlite_seed_path() -> Path | None:
    candidates: list[Path] = []
    if VOLUME_DIR:
        candidates.append(Path(VOLUME_DIR) / "movies.db")
    candidates.extend(
        [
            BASE_DIR / "movies-backup.db",
            BASE_DIR / "movies.db",
        ]
    )
    for path in candidates:
        if path.exists() and path.is_file() and path.stat().st_size > 0:
            return path
    return None


def _init_schema() -> None:
    statements = [
        """
        CREATE TABLE IF NOT EXISTS movies(
            id BIGSERIAL PRIMARY KEY,
            code INTEGER UNIQUE NOT NULL,
            name TEXT NOT NULL,
            year TEXT NOT NULL DEFAULT '',
            country TEXT NOT NULL DEFAULT '',
            genre TEXT NOT NULL DEFAULT '',
            language TEXT NOT NULL DEFAULT '',
            imdb TEXT NOT NULL DEFAULT '',
            trailer_file_id TEXT NOT NULL DEFAULT '',
            poster_file_id TEXT NOT NULL DEFAULT '',
            file_id TEXT NOT NULL DEFAULT '',
            views INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        "ALTER TABLE movies ADD COLUMN IF NOT EXISTS trailer_file_id TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE movies ADD COLUMN IF NOT EXISTS file_id TEXT NOT NULL DEFAULT ''",
        """
        CREATE TABLE IF NOT EXISTS users(
            user_id BIGINT PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS app_users(
            user_id BIGINT PRIMARY KEY,
            first_name TEXT NOT NULL DEFAULT '',
            last_name TEXT NOT NULL DEFAULT '',
            username TEXT NOT NULL DEFAULT '',
            language_code TEXT NOT NULL DEFAULT '',
            photo_url TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS movie_qualities(
            id BIGSERIAL PRIMARY KEY,
            movie_code INTEGER NOT NULL REFERENCES movies(code) ON DELETE CASCADE,
            quality TEXT NOT NULL,
            file_id TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(movie_code, quality)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS favorites(
            user_id BIGINT NOT NULL REFERENCES app_users(user_id) ON DELETE CASCADE,
            movie_code INTEGER NOT NULL REFERENCES movies(code) ON DELETE CASCADE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY(user_id, movie_code)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS watch_history(
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES app_users(user_id) ON DELETE CASCADE,
            movie_code INTEGER NOT NULL REFERENCES movies(code) ON DELETE CASCADE,
            opened_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_movies_name_lower ON movies(LOWER(name))",
        "CREATE INDEX IF NOT EXISTS idx_movies_genre_lower ON movies(LOWER(genre))",
        "CREATE INDEX IF NOT EXISTS idx_movies_views ON movies(views DESC)",
        "CREATE INDEX IF NOT EXISTS idx_history_user_time ON watch_history(user_id, opened_at DESC)",
    ]

    with pool.connection() as conn:
        with conn.cursor() as cur:
            for statement in statements:
                cur.execute(statement)

            # Super App avval yaratgan 91 ta kinoda movies.file_id ustuni bo'lmagan.
            # Birinchi mavjud sifat file_id qiymatini eski handlerlar uchun qayta to'ldiramiz.
            cur.execute(
                f"""
                UPDATE movies
                SET file_id = COALESCE(
                    (
                        SELECT mq.file_id
                        FROM movie_qualities mq
                        WHERE mq.movie_code = movies.code
                        ORDER BY {QUALITY_ORDER_SQL}, mq.id
                        LIMIT 1
                    ),
                    ''
                )
                WHERE COALESCE(file_id, '') = ''
                """
            )
        conn.commit()


def _seed_from_sqlite_if_empty() -> None:
    seed_path = _sqlite_seed_path()
    if seed_path is None:
        return

    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM movies")
        if int(cur.fetchone()[0]) > 0:
            return

    sqlite_conn = sqlite3.connect(str(seed_path))
    sqlite_conn.row_factory = sqlite3.Row
    try:
        movie_rows = sqlite_conn.execute("SELECT * FROM movies ORDER BY id").fetchall()
        if not movie_rows:
            return

        table_names = {
            row[0]
            for row in sqlite_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        quality_rows = (
            sqlite_conn.execute("SELECT * FROM movie_qualities ORDER BY id").fetchall()
            if "movie_qualities" in table_names
            else []
        )
        user_rows = (
            sqlite_conn.execute("SELECT * FROM users").fetchall()
            if "users" in table_names
            else []
        )
        favorite_rows = (
            sqlite_conn.execute("SELECT * FROM favorites").fetchall()
            if "favorites" in table_names
            else []
        )

        with pool.connection() as conn:
            with conn.cursor() as cur:
                for row in movie_rows:
                    keys = set(row.keys())
                    created_at = str(row["created_at"] or "") if "created_at" in keys else ""
                    cur.execute(
                        """
                        INSERT INTO movies(
                            code, name, year, country, genre, language, imdb,
                            trailer_file_id, poster_file_id, file_id, views, created_at
                        ) VALUES(
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            COALESCE(NULLIF(%s, '')::timestamptz, NOW())
                        )
                        ON CONFLICT(code) DO NOTHING
                        """,
                        (
                            int(row["code"]),
                            str(row["name"] or ""),
                            str(row["year"] or "") if "year" in keys else "",
                            str(row["country"] or "") if "country" in keys else "",
                            str(row["genre"] or "") if "genre" in keys else "",
                            str(row["language"] or "") if "language" in keys else "",
                            str(row["imdb"] or "") if "imdb" in keys else "",
                            str(row["trailer_file_id"] or "") if "trailer_file_id" in keys else "",
                            str(row["poster_file_id"] or "") if "poster_file_id" in keys else "",
                            str(row["file_id"] or "") if "file_id" in keys else "",
                            int(row["views"] or 0) if "views" in keys else 0,
                            created_at,
                        ),
                    )

                for row in user_rows:
                    keys = set(row.keys())
                    created_at = str(row["created_at"] or "") if "created_at" in keys else ""
                    user_id = int(row["user_id"])
                    cur.execute(
                        """
                        INSERT INTO users(user_id, created_at)
                        VALUES(%s, COALESCE(NULLIF(%s, '')::timestamptz, NOW()))
                        ON CONFLICT(user_id) DO NOTHING
                        """,
                        (user_id, created_at),
                    )
                    cur.execute(
                        "INSERT INTO app_users(user_id) VALUES(%s) ON CONFLICT(user_id) DO NOTHING",
                        (user_id,),
                    )

                for row in quality_rows:
                    keys = set(row.keys())
                    created_at = str(row["created_at"] or "") if "created_at" in keys else ""
                    cur.execute(
                        """
                        INSERT INTO movie_qualities(movie_code, quality, file_id, created_at)
                        VALUES(%s, %s, %s, COALESCE(NULLIF(%s, '')::timestamptz, NOW()))
                        ON CONFLICT(movie_code, quality)
                        DO UPDATE SET file_id=EXCLUDED.file_id
                        """,
                        (
                            int(row["movie_code"]),
                            str(row["quality"]),
                            str(row["file_id"]),
                            created_at,
                        ),
                    )

                # Eski bazada movie_qualities bo'lmagan kino bo'lsa Original sifatini yaratadi.
                cur.execute(
                    """
                    INSERT INTO movie_qualities(movie_code, quality, file_id)
                    SELECT code, 'Original', file_id
                    FROM movies
                    WHERE COALESCE(file_id, '') <> ''
                    ON CONFLICT(movie_code, quality) DO NOTHING
                    """
                )

                for row in favorite_rows:
                    keys = set(row.keys())
                    user_id = int(row["user_id"])
                    movie_code = int(row["movie_code"])
                    created_at = str(row["created_at"] or "") if "created_at" in keys else ""
                    cur.execute(
                        "INSERT INTO app_users(user_id) VALUES(%s) ON CONFLICT(user_id) DO NOTHING",
                        (user_id,),
                    )
                    cur.execute(
                        """
                        INSERT INTO favorites(user_id, movie_code, created_at)
                        VALUES(%s, %s, COALESCE(NULLIF(%s, '')::timestamptz, NOW()))
                        ON CONFLICT(user_id, movie_code) DO NOTHING
                        """,
                        (user_id, movie_code, created_at),
                    )
            conn.commit()
    finally:
        sqlite_conn.close()


def init_database() -> None:
    with db_lock:
        _init_schema()
        _seed_from_sqlite_if_empty()


init_database()


def add_user(user_id: int) -> None:
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users(user_id) VALUES(%s) ON CONFLICT(user_id) DO NOTHING",
                (user_id,),
            )
            # favorites jadvalidagi FK uchun minimal app_users yozuvi ham kerak.
            cur.execute(
                "INSERT INTO app_users(user_id) VALUES(%s) ON CONFLICT(user_id) DO NOTHING",
                (user_id,),
            )
        conn.commit()


def get_users():
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT user_id FROM users ORDER BY user_id")
        return cur.fetchall()


def users_count() -> int:
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM users")
        return int(cur.fetchone()[0])


def movies_count() -> int:
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM movies")
        return int(cur.fetchone()[0])


def generate_code() -> int:
    with db_lock:
        while True:
            code = random.randint(1000, 9999)
            with pool.connection() as conn, conn.cursor() as cur:
                cur.execute("SELECT 1 FROM movies WHERE code=%s", (code,))
                if cur.fetchone() is None:
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
):
    quality = normalize_quality(quality)

    # Juda kam uchraydigan kod to'qnashuviga qarshi qayta urinadi.
    for _ in range(30):
        code = generate_code()
        try:
            with pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO movies(
                            code, name, year, country, genre, language, imdb,
                            trailer_file_id, poster_file_id, file_id, views
                        ) VALUES(%s, %s, %s, %s, %s, %s, %s, '', %s, %s, 0)
                        """,
                        (
                            code,
                            name,
                            year,
                            country,
                            genre,
                            language,
                            imdb,
                            poster_file_id or "",
                            file_id,
                        ),
                    )
                    cur.execute(
                        """
                        INSERT INTO movie_qualities(movie_code, quality, file_id)
                        VALUES(%s, %s, %s)
                        """,
                        (code, quality, file_id),
                    )
                conn.commit()
            return code
        except Exception as exc:
            # SQLSTATE 23505 — unique_violation. Boshqa xatoni yashirmaymiz.
            if getattr(exc, "sqlstate", None) != "23505":
                raise
    raise RuntimeError("Bo'sh kino kodi topilmadi. Qayta urinib ko'ring.")


def get_movie(code):
    """Eski handlerlar bilan mos tuple qaytaradi."""
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT name, year, country, genre, language, imdb,
                   trailer_file_id, poster_file_id, file_id, views
            FROM movies
            WHERE code=%s
            """,
            (code,),
        )
        return cur.fetchone()


def get_movie_full(code):
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT code, name, year, country, genre, language, imdb,
                   poster_file_id, file_id, views, created_at
            FROM movies
            WHERE code=%s
            """,
            (code,),
        )
        return cur.fetchone()


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
    values = {
        "name": name,
        "year": year,
        "country": country,
        "genre": genre,
        "language": language,
        "imdb": imdb,
        "poster_file_id": poster_file_id,
    }
    updates: list[str] = []
    params: list[object] = []
    for column, value in values.items():
        if value is not None:
            updates.append(f"{column}=%s")
            params.append(value)
    if not updates:
        return False

    params.append(code)
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE movies SET {', '.join(updates)} WHERE code=%s",
                params,
            )
            changed = cur.rowcount > 0
        conn.commit()
        return changed


def update_movie_code(old_code: int, new_code: int) -> bool:
    if old_code == new_code:
        return movie_exists(old_code)

    with db_lock, pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM movies WHERE code=%s", (new_code,))
            if cur.fetchone() is not None:
                return False

            cur.execute("SELECT 1 FROM movies WHERE code=%s", (old_code,))
            if cur.fetchone() is None:
                return False

            # FK lar ON UPDATE CASCADE emas. Shu sabab yangi kino qatori yaratiladi,
            # barcha bog'langan qatorlar ko'chiriladi, keyin eski qator o'chiriladi.
            cur.execute(
                """
                INSERT INTO movies(
                    code, name, year, country, genre, language, imdb,
                    trailer_file_id, poster_file_id, file_id, views, created_at
                )
                SELECT %s, name, year, country, genre, language, imdb,
                       trailer_file_id, poster_file_id, file_id, views, created_at
                FROM movies WHERE code=%s
                """,
                (new_code, old_code),
            )
            cur.execute(
                "UPDATE movie_qualities SET movie_code=%s WHERE movie_code=%s",
                (new_code, old_code),
            )
            cur.execute(
                "UPDATE favorites SET movie_code=%s WHERE movie_code=%s",
                (new_code, old_code),
            )
            cur.execute(
                "UPDATE watch_history SET movie_code=%s WHERE movie_code=%s",
                (new_code, old_code),
            )
            cur.execute("DELETE FROM movies WHERE code=%s", (old_code,))
        conn.commit()
        return True


def increase_views(code):
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE movies SET views=views+1 WHERE code=%s", (code,))
        conn.commit()


def delete_movie(code):
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM movies WHERE code=%s", (code,))
        conn.commit()


def movie_exists(code):
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT 1 FROM movies WHERE code=%s", (code,))
        return cur.fetchone() is not None


def search_movies(query):
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT code, name, year, genre
            FROM movies
            WHERE name ILIKE %s
            ORDER BY id DESC
            LIMIT 10
            """,
            (f"%{query}%",),
        )
        return cur.fetchall()


def get_all_movies(limit: int = 100):
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT code, name, year, genre
            FROM movies
            ORDER BY id DESC
            LIMIT %s
            """,
            (limit,),
        )
        return cur.fetchall()


def add_movie_quality(movie_code: int, quality: str, file_id: str) -> int:
    quality = normalize_quality(quality)
    if not file_id:
        raise ValueError("Video file_id bo'sh bo'lmasligi kerak.")

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO movie_qualities(movie_code, quality, file_id)
                VALUES(%s, %s, %s)
                ON CONFLICT(movie_code, quality)
                DO UPDATE SET file_id=EXCLUDED.file_id, created_at=NOW()
                RETURNING id
                """,
                (movie_code, quality, file_id),
            )
            quality_id = int(cur.fetchone()[0])
            cur.execute(
                """
                UPDATE movies
                SET file_id=%s
                WHERE code=%s AND COALESCE(file_id, '')=''
                """,
                (file_id, movie_code),
            )
        conn.commit()
        return quality_id


def get_movie_qualities(movie_code: int):
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT quality, file_id
            FROM movie_qualities
            WHERE movie_code=%s
            ORDER BY {QUALITY_ORDER_SQL}, quality
            """,
            (movie_code,),
        )
        return cur.fetchall()


def get_movie_quality_rows(movie_code: int):
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT id, quality
            FROM movie_qualities
            WHERE movie_code=%s
            ORDER BY {QUALITY_ORDER_SQL}, quality
            """,
            (movie_code,),
        )
        return cur.fetchall()


def get_movie_quality(movie_code: int, quality: str):
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT file_id FROM movie_qualities WHERE movie_code=%s AND quality=%s",
            (movie_code, quality),
        )
        row = cur.fetchone()
        return row[0] if row else None


def get_movie_quality_by_id(movie_code: int, quality_id: int):
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT quality, file_id
            FROM movie_qualities
            WHERE movie_code=%s AND id=%s
            """,
            (movie_code, quality_id),
        )
        return cur.fetchone()


def delete_movie_quality(movie_code: int, quality: str) -> bool:
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM movie_qualities WHERE movie_code=%s AND quality=%s",
            (movie_code, quality),
        )
        row = cur.fetchone()
    if not row:
        return False
    return delete_movie_quality_by_id(movie_code, int(row[0])) == "deleted"


def delete_movie_quality_by_id(movie_code: int, quality_id: int) -> str:
    with db_lock, pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT file_id FROM movie_qualities WHERE movie_code=%s AND id=%s",
                (movie_code, quality_id),
            )
            target = cur.fetchone()
            if not target:
                return "not_found"

            cur.execute(
                "SELECT COUNT(*) FROM movie_qualities WHERE movie_code=%s",
                (movie_code,),
            )
            if int(cur.fetchone()[0]) <= 1:
                return "last_quality"

            deleted_file_id = target[0]
            cur.execute(
                "DELETE FROM movie_qualities WHERE movie_code=%s AND id=%s",
                (movie_code, quality_id),
            )
            cur.execute("SELECT file_id FROM movies WHERE code=%s", (movie_code,))
            movie_row = cur.fetchone()
            if movie_row and movie_row[0] == deleted_file_id:
                cur.execute(
                    f"""
                    SELECT file_id
                    FROM movie_qualities
                    WHERE movie_code=%s
                    ORDER BY {QUALITY_ORDER_SQL}, id
                    LIMIT 1
                    """,
                    (movie_code,),
                )
                replacement = cur.fetchone()
                if replacement:
                    cur.execute(
                        "UPDATE movies SET file_id=%s WHERE code=%s",
                        (replacement[0], movie_code),
                    )
        conn.commit()
        return "deleted"


def add_favorite(user_id, movie_code):
    add_user(int(user_id))
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO favorites(user_id, movie_code)
                VALUES(%s, %s)
                ON CONFLICT(user_id, movie_code) DO NOTHING
                """,
                (user_id, movie_code),
            )
        conn.commit()


def remove_favorite(user_id, movie_code):
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM favorites WHERE user_id=%s AND movie_code=%s",
                (user_id, movie_code),
            )
        conn.commit()


def is_favorite(user_id, movie_code):
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM favorites WHERE user_id=%s AND movie_code=%s",
            (user_id, movie_code),
        )
        return cur.fetchone() is not None


def get_favorites(user_id):
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT movies.code, movies.name, movies.year, movies.genre
            FROM favorites
            JOIN movies ON favorites.movie_code=movies.code
            WHERE favorites.user_id=%s
            ORDER BY favorites.created_at DESC
            LIMIT 20
            """,
            (user_id,),
        )
        return cur.fetchall()


def get_top_movies(limit=10):
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT code, name, year, genre, views
            FROM movies
            ORDER BY views DESC
            LIMIT %s
            """,
            (limit,),
        )
        return cur.fetchall()


def get_genres():
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT genre, COUNT(*)
            FROM movies
            WHERE genre <> ''
            GROUP BY genre
            ORDER BY genre ASC
            """
        )
        return cur.fetchall()


def get_movies_by_genre(genre):
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT code, name, year, genre
            FROM movies
            WHERE genre=%s
            ORDER BY id DESC
            LIMIT 20
            """,
            (genre,),
        )
        return cur.fetchall()


def database_status() -> dict:
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.execute("SELECT COUNT(*) FROM movies")
        movie_total = int(cur.fetchone()[0])
        return {
            "path": "PostgreSQL",
            "integrity": "ok",
            "movies": movie_total,
            "backend": BACKEND,
        }
