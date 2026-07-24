from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any

from .settings import DATABASE_URL, SEED_DB_PATH

logger = logging.getLogger(__name__)


class DatabaseNotConfigured(RuntimeError):
    pass


class Database:
    def __init__(self, database_url: str = DATABASE_URL) -> None:
        self.database_url = database_url
        self.pool = None

    @property
    def configured(self) -> bool:
        return bool(self.database_url)

    def start(self) -> None:
        if not self.configured:
            logger.warning("DATABASE_URL sozlanmagan; katalog API vaqtincha o'chirilgan.")
            return

        try:
            from psycopg.rows import dict_row
            from psycopg_pool import ConnectionPool
        except ImportError as exc:
            raise RuntimeError("psycopg va psycopg_pool o'rnatilmagan.") from exc

        self.pool = ConnectionPool(
            conninfo=self.database_url,
            min_size=1,
            max_size=8,
            timeout=30,
            kwargs={"row_factory": dict_row, "autocommit": False},
            open=True,
        )
        self._init_schema()
        self._seed_from_sqlite(SEED_DB_PATH)

    def close(self) -> None:
        if self.pool is not None:
            self.pool.close()
            self.pool = None

    def _require_pool(self):
        if self.pool is None:
            raise DatabaseNotConfigured("DATABASE_URL sozlanmagan.")
        return self.pool

    def _init_schema(self) -> None:
        pool = self._require_pool()
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
                poster_file_id TEXT NOT NULL DEFAULT '',
                views INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
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
            conn.commit()

    def _seed_from_sqlite(self, path: Path) -> None:
        pool = self._require_pool()
        if not path.exists():
            logger.warning("Seed SQLite topilmadi: %s", path)
            return

        sqlite_conn = sqlite3.connect(str(path))
        sqlite_conn.row_factory = sqlite3.Row
        try:
            movie_rows = sqlite_conn.execute("SELECT * FROM movies ORDER BY id").fetchall()
            quality_rows: list[sqlite3.Row] = []
            table_exists = sqlite_conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='movie_qualities'"
            ).fetchone()
            if table_exists:
                quality_rows = sqlite_conn.execute("SELECT * FROM movie_qualities").fetchall()

            with pool.connection() as conn, conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS count FROM movies")
                current_count = int(cur.fetchone()["count"])

            if current_count >= len(movie_rows):
                logger.info(
                    "SQLite sinxronlash o'tkazib yuborildi: manba=%s, PostgreSQL=%s",
                    len(movie_rows),
                    current_count,
                )
                return

            with pool.connection() as conn:
                with conn.cursor() as cur:
                    for row in movie_rows:
                        keys = set(row.keys())
                        cur.execute(
                            """
                            INSERT INTO movies(
                                code, name, year, country, genre, language,
                                imdb, poster_file_id, views, created_at
                            ) VALUES(
                                %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                COALESCE(NULLIF(%s, '')::timestamptz, NOW())
                            )
                            ON CONFLICT(code) DO UPDATE SET
                                name=EXCLUDED.name,
                                year=EXCLUDED.year,
                                country=EXCLUDED.country,
                                genre=EXCLUDED.genre,
                                language=EXCLUDED.language,
                                imdb=EXCLUDED.imdb,
                                poster_file_id=EXCLUDED.poster_file_id,
                                views=GREATEST(movies.views, EXCLUDED.views)
                            """,
                            (
                                int(row["code"]),
                                str(row["name"] or ""),
                                str(row["year"] or "") if "year" in keys else "",
                                str(row["country"] or "") if "country" in keys else "",
                                str(row["genre"] or "") if "genre" in keys else "",
                                str(row["language"] or "") if "language" in keys else "",
                                str(row["imdb"] or "") if "imdb" in keys else "",
                                str(row["poster_file_id"] or "") if "poster_file_id" in keys else "",
                                int(row["views"] or 0) if "views" in keys else 0,
                                str(row["created_at"] or "") if "created_at" in keys else "",
                            ),
                        )

                        file_id = str(row["file_id"] or "") if "file_id" in keys else ""
                        if file_id:
                            cur.execute(
                                """
                                INSERT INTO movie_qualities(movie_code, quality, file_id)
                                VALUES(%s, 'Original', %s)
                                ON CONFLICT(movie_code, quality)
                                DO UPDATE SET file_id=EXCLUDED.file_id
                                """,
                                (int(row["code"]), file_id),
                            )

                    for row in quality_rows:
                        cur.execute(
                            """
                            INSERT INTO movie_qualities(movie_code, quality, file_id)
                            VALUES(%s, %s, %s)
                            ON CONFLICT(movie_code, quality)
                            DO UPDATE SET file_id=EXCLUDED.file_id
                            """,
                            (int(row["movie_code"]), str(row["quality"]), str(row["file_id"])),
                        )
                conn.commit()
            with pool.connection() as conn, conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS count FROM movies")
                postgres_count = int(cur.fetchone()["count"])
            logger.info(
                "SQLite sinxronlandi: manba=%s ta, PostgreSQL=%s ta kino",
                len(movie_rows),
                postgres_count,
            )
        finally:
            sqlite_conn.close()

    def health(self) -> dict[str, Any]:
        if not self.configured:
            return {"database": "not_configured", "movies": 0}
        pool = self._require_pool()
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS count FROM movies")
            return {"database": "ok", "movies": int(cur.fetchone()["count"])}

    def home(self, limit: int = 12) -> dict[str, Any]:
        return {
            "featured": self.list_movies(limit=1, sort="popular")["items"],
            "popular": self.list_movies(limit=limit, sort="popular")["items"],
            "new": self.list_movies(limit=limit, sort="new")["items"],
        }

    def list_movies(
        self,
        *,
        q: str = "",
        genre: str = "",
        country: str = "",
        year: str = "",
        sort: str = "popular",
        page: int = 1,
        limit: int = 24,
    ) -> dict[str, Any]:
        pool = self._require_pool()
        where = []
        params: list[Any] = []
        if q:
            where.append("(name ILIKE %s OR CAST(code AS TEXT) ILIKE %s)")
            params.extend([f"%{q}%", f"%{q}%"])
        if genre:
            where.append("genre ILIKE %s")
            params.append(f"%{genre}%")
        if country:
            where.append("country ILIKE %s")
            params.append(f"%{country}%")
        if year:
            where.append("year = %s")
            params.append(year)

        where_sql = " WHERE " + " AND ".join(where) if where else ""
        order_sql = {
            "new": "created_at DESC, id DESC",
            "name": "name ASC",
            "year": "year DESC, id DESC",
            "popular": "views DESC, id DESC",
        }.get(sort, "views DESC, id DESC")
        offset = (page - 1) * limit

        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) AS count FROM movies{where_sql}", params)
            total = int(cur.fetchone()["count"])
            cur.execute(
                f"""
                SELECT code, name, year, country, genre, language, imdb,
                       views, (poster_file_id <> '') AS has_poster
                FROM movies
                {where_sql}
                ORDER BY {order_sql}
                LIMIT %s OFFSET %s
                """,
                [*params, limit, offset],
            )
            items = [dict(row) for row in cur.fetchall()]
        return {"items": items, "page": page, "limit": limit, "total": total}

    def movie(self, code: int) -> dict[str, Any] | None:
        pool = self._require_pool()
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT code, name, year, country, genre, language, imdb,
                       views, (poster_file_id <> '') AS has_poster
                FROM movies WHERE code=%s
                """,
                (code,),
            )
            row = cur.fetchone()
            if not row:
                return None
            movie = dict(row)
            cur.execute(
                "SELECT quality FROM movie_qualities WHERE movie_code=%s ORDER BY id",
                (code,),
            )
            movie["qualities"] = [item["quality"] for item in cur.fetchall()]
            return movie

    def poster_file_id(self, code: int) -> str:
        pool = self._require_pool()
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT poster_file_id FROM movies WHERE code=%s", (code,))
            row = cur.fetchone()
            return str(row["poster_file_id"] or "") if row else ""

    def genres(self) -> list[dict[str, Any]]:
        pool = self._require_pool()
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT genre, COUNT(*) AS count
                FROM movies
                WHERE TRIM(genre) <> ''
                GROUP BY genre
                ORDER BY count DESC, genre ASC
                """
            )
            return [dict(row) for row in cur.fetchall()]

    def upsert_user(self, user) -> dict[str, Any]:
        pool = self._require_pool()
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO app_users(
                    user_id, first_name, last_name, username,
                    language_code, photo_url
                ) VALUES(%s, %s, %s, %s, %s, %s)
                ON CONFLICT(user_id) DO UPDATE SET
                    first_name=EXCLUDED.first_name,
                    last_name=EXCLUDED.last_name,
                    username=EXCLUDED.username,
                    language_code=EXCLUDED.language_code,
                    photo_url=EXCLUDED.photo_url,
                    last_seen_at=NOW()
                RETURNING user_id, first_name, last_name, username,
                          language_code, photo_url
                """,
                (
                    user.id,
                    user.first_name,
                    user.last_name,
                    user.username,
                    user.language_code,
                    user.photo_url,
                ),
            )
            result = dict(cur.fetchone())
            conn.commit()
            return result

    def favorites(self, user_id: int) -> list[dict[str, Any]]:
        pool = self._require_pool()
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT m.code, m.name, m.year, m.country, m.genre, m.language,
                       m.imdb, m.views, (m.poster_file_id <> '') AS has_poster
                FROM favorites f
                JOIN movies m ON m.code=f.movie_code
                WHERE f.user_id=%s
                ORDER BY f.created_at DESC
                """,
                (user_id,),
            )
            return [dict(row) for row in cur.fetchall()]

    def set_favorite(self, user_id: int, movie_code: int, enabled: bool) -> bool:
        pool = self._require_pool()
        with pool.connection() as conn, conn.cursor() as cur:
            if enabled:
                cur.execute(
                    """
                    INSERT INTO favorites(user_id, movie_code)
                    VALUES(%s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (user_id, movie_code),
                )
            else:
                cur.execute(
                    "DELETE FROM favorites WHERE user_id=%s AND movie_code=%s",
                    (user_id, movie_code),
                )
            conn.commit()
        return enabled

    def is_favorite(self, user_id: int, movie_code: int) -> bool:
        pool = self._require_pool()
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM favorites WHERE user_id=%s AND movie_code=%s",
                (user_id, movie_code),
            )
            return cur.fetchone() is not None

    def record_open(self, user_id: int, movie_code: int) -> None:
        pool = self._require_pool()
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO watch_history(user_id, movie_code) VALUES(%s, %s)",
                (user_id, movie_code),
            )
            cur.execute("UPDATE movies SET views=views+1 WHERE code=%s", (movie_code,))
            conn.commit()
