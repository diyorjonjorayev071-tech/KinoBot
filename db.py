from __future__ import annotations

import os
import re
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:  # local SQLite rejimida psycopg shart emas
    psycopg = None
    dict_row = None


class DatabaseError(RuntimeError):
    pass


class Database:
    def __init__(self) -> None:
        self.database_url = (os.getenv("DATABASE_URL") or "").strip()
        self.sqlite_path = Path(os.getenv("SQLITE_PATH") or "xd_kino.db")
        self.is_postgres = self.database_url.startswith(("postgres://", "postgresql://"))
        self.ensure_schema()

    @property
    def placeholder(self) -> str:
        return "%s" if self.is_postgres else "?"

    @contextmanager
    def connect(self) -> Iterator[Any]:
        if self.is_postgres:
            if psycopg is None:
                raise DatabaseError("PostgreSQL uchun psycopg o'rnatilmagan.")
            last_error: Exception | None = None
            for attempt in range(1, 7):
                try:
                    conn = psycopg.connect(
                        self.database_url,
                        connect_timeout=6,
                        row_factory=dict_row,
                    )
                    try:
                        yield conn
                    finally:
                        conn.close()
                    return
                except Exception as exc:
                    last_error = exc
                    if attempt >= 6:
                        break
                    time.sleep(2.0)
            raise DatabaseError(f"PostgreSQL ulanish xatosi: {last_error}") from last_error

        conn = sqlite3.connect(self.sqlite_path, timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def ensure_schema(self) -> None:
        if self.is_postgres:
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
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    content_type TEXT NOT NULL DEFAULT 'Kino',
                    is_recommended BOOLEAN NOT NULL DEFAULT FALSE,
                    description TEXT NOT NULL DEFAULT ''
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS movie_qualities(
                    id BIGSERIAL PRIMARY KEY,
                    movie_code INTEGER NOT NULL REFERENCES movies(code) ON DELETE CASCADE,
                    quality TEXT NOT NULL,
                    file_id TEXT NOT NULL DEFAULT '',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE(movie_code, quality)
                )
                """,
                "CREATE INDEX IF NOT EXISTS idx_xd_movies_views ON movies(views DESC)",
                "CREATE INDEX IF NOT EXISTS idx_xd_movies_type ON movies(content_type)",
            ]
            with self.connect() as conn:
                with conn.cursor() as cur:
                    for statement in statements:
                        cur.execute(statement)
                conn.commit()
            return

        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        statements = [
            """
            CREATE TABLE IF NOT EXISTS movies(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                content_type TEXT NOT NULL DEFAULT 'Kino',
                is_recommended INTEGER NOT NULL DEFAULT 0,
                description TEXT NOT NULL DEFAULT ''
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS movie_qualities(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                movie_code INTEGER NOT NULL,
                quality TEXT NOT NULL,
                file_id TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(movie_code, quality),
                FOREIGN KEY(movie_code) REFERENCES movies(code) ON DELETE CASCADE
            )
            """,
        ]
        with self.connect() as conn:
            cur = conn.cursor()
            for statement in statements:
                cur.execute(statement)
            conn.commit()
        self._seed_local_if_empty()

    def _seed_local_if_empty(self) -> None:
        with self.connect() as conn:
            count = int(conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0])
            if count:
                return
            demo = [
                (101, "Yulduzlar sari", "2026", "O'zbekiston", "Fantastika, Sarguzasht", "O'zbek", "8.4", 1640, "Kino", 1, "Kosmosga qarab yo'l olgan yosh jamoa haqidagi namuna film."),
                (102, "So'nggi signal", "2025", "AQSh", "Triller, Fantastika", "O'zbek", "8.1", 1510, "Kino", 1, "Sirli signal butun shahar hayotini o'zgartirib yuboradi."),
                (103, "Qorong'u orbit", "2026", "Buyuk Britaniya", "Fantastika", "O'zbek", "7.9", 1420, "Serial", 1, "Orbital stansiyada yuz beradigan voqealar haqidagi namuna serial."),
                (104, "Sehrli o'rmon", "2024", "Fransiya", "Multfilm, Sarguzasht", "O'zbek", "8.0", 1260, "Multfilm", 1, "Do'stlik va jasorat haqidagi rang-barang namuna multfilm."),
                (105, "Tungi shahar", "2025", "Janubiy Koreya", "Drama, Triller", "O'zbek", "7.8", 1120, "Serial", 0, "Tunda yashirin sirlar ochiladigan drama."),
                (106, "Oq bulut", "2023", "Yaponiya", "Drama", "O'zbek", "7.7", 980, "Kino", 0, "Orzular ortidan ketish haqidagi sokin hikoya."),
                (107, "Robotcha D", "2026", "Kanada", "Multfilm, Komediya", "O'zbek", "7.6", 930, "Multfilm", 0, "Kichik robotning katta sarguzashti."),
                (108, "Qaytish nuqtasi", "2024", "Germaniya", "Detektiv", "O'zbek", "7.5", 890, "Kino", 0, "Bir qaror hamma narsani o'zgartiradigan detektiv."),
                (109, "Yashil sayyora", "2025", "Ispaniya", "Hujjatli", "O'zbek", "8.5", 820, "Kino", 1, "Tabiat va kelajak haqidagi namuna hujjatli loyiha."),
                (110, "Kichik qahramonlar", "2024", "AQSh", "Multfilm, Oila", "O'zbek", "7.4", 760, "Multfilm", 0, "Kichik qahramonlarning quvnoq hikoyalari."),
                (111, "Sirli xona", "2023", "Turkiya", "Sirli, Drama", "O'zbek", "7.3", 700, "Serial", 0, "Eski uy ichidagi sirlarni ochishga urinayotgan qahramonlar."),
                (112, "Cheksiz yo'l", "2022", "O'zbekiston", "Drama, Sarguzasht", "O'zbek", "7.2", 640, "Kino", 0, "Yo'l va tanlovlar haqidagi namuna film."),
            ]
            conn.executemany(
                """
                INSERT INTO movies(code,name,year,country,genre,language,imdb,views,content_type,is_recommended,description)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)
                """,
                demo,
            )
            for code, *_ in demo:
                conn.execute(
                    "INSERT OR IGNORE INTO movie_qualities(movie_code,quality,file_id) VALUES(?,?,?)",
                    (code, "720p", ""),
                )
            conn.commit()

    @staticmethod
    def imdb_number(value: Any) -> float:
        match = re.search(r"(?:10(?:\.0+)?|[0-9](?:\.\d+)?)", str(value or ""))
        if not match:
            return 0.0
        try:
            return float(match.group(0))
        except ValueError:
            return 0.0

    @staticmethod
    def _row_dict(row: Any) -> dict[str, Any]:
        return dict(row) if row is not None else {}

    @staticmethod
    def _item(row: Any) -> dict[str, Any]:
        item = dict(row)
        item["code"] = int(item.get("code") or 0)
        item["views"] = int(item.get("views") or 0)
        item["is_recommended"] = bool(item.get("is_recommended"))
        item["poster_url"] = f"/api/poster/{item['code']}"
        return item

    def health(self) -> dict[str, Any]:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) AS count FROM movies")
            row = cur.fetchone()
            count = int(row["count"] if isinstance(row, (sqlite3.Row, dict)) else row[0])
        return {"database": "ok", "movies": count, "engine": "postgresql" if self.is_postgres else "sqlite"}

    def _fetch_movies(self, where: list[str], params: list[Any], order_sql: str, limit: int, offset: int = 0) -> list[dict[str, Any]]:
        where_sql = " WHERE " + " AND ".join(where) if where else ""
        ph = self.placeholder
        sql = f"""
            SELECT code,name,year,country,genre,language,imdb,views,
                   content_type,is_recommended,description,
                   CASE WHEN COALESCE(poster_file_id,'') <> '' THEN 1 ELSE 0 END AS has_poster
            FROM movies
            {where_sql}
            ORDER BY {order_sql}
            LIMIT {ph} OFFSET {ph}
        """
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(sql, [*params, limit, offset])
            return [self._item(row) for row in cur.fetchall()]

    def list_movies(
        self,
        *,
        q: str = "",
        genre: str = "",
        country: str = "",
        year: str = "",
        content_type: str = "",
        recommended: bool = False,
        sort: str = "popular",
        page: int = 1,
        limit: int = 24,
    ) -> dict[str, Any]:
        where: list[str] = []
        params: list[Any] = []
        ph = self.placeholder

        if q:
            where.append(f"LOWER(name) LIKE {ph}")
            params.append(f"%{q.lower()}%")
        if genre:
            where.append(f"LOWER(genre) LIKE {ph}")
            params.append(f"%{genre.lower()}%")
        if country:
            where.append(f"country = {ph}")
            params.append(country)
        if year:
            where.append(f"year = {ph}")
            params.append(year)
        if content_type:
            where.append(f"content_type = {ph}")
            params.append(content_type)
        if recommended:
            where.append("is_recommended = TRUE" if self.is_postgres else "is_recommended = 1")

        order_sql = {
            "popular": "views DESC, code DESC",
            "new": "created_at DESC, code DESC",
            "name": "name ASC",
            "year": "year DESC, code DESC",
        }.get(sort, "views DESC, code DESC")

        where_sql = " WHERE " + " AND ".join(where) if where else ""
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT COUNT(*) AS count FROM movies{where_sql}", params)
            row = cur.fetchone()
            total = int(row["count"] if isinstance(row, (sqlite3.Row, dict)) else row[0])

        page = max(1, page)
        limit = min(max(1, limit), 60)
        offset = (page - 1) * limit
        items = self._fetch_movies(where, params, order_sql, limit, offset)
        return {"items": items, "total": total, "page": page, "limit": limit}

    def recommendations(self, limit: int = 10) -> list[dict[str, Any]]:
        # Talab: Kino + Serial + Multfilm, IMDb >= 7.5, eng ko'p ko'rilganlar yuqorida.
        candidates = self._fetch_movies([], [], "views DESC, code DESC", 200, 0)
        allowed = {"kino", "serial", "multfilm"}
        selected = [
            item for item in candidates
            if str(item.get("content_type") or "").strip().lower() in allowed
            and self.imdb_number(item.get("imdb")) >= 7.5
        ]
        selected.sort(key=lambda x: (int(x.get("views") or 0), self.imdb_number(x.get("imdb"))), reverse=True)
        return selected[:limit]

    def home(self, limit: int = 12) -> dict[str, Any]:
        featured = self.list_movies(recommended=True, sort="new", limit=6)["items"]
        if not featured:
            featured = self.list_movies(sort="popular", limit=6)["items"]

        popular = self.list_movies(sort="popular", limit=limit)["items"]
        new_items = self.list_movies(sort="new", limit=limit)["items"]
        sections = [
            {"key": "new", "title": "Yangi qo'shilganlar", "items": new_items},
            {"key": "movies", "title": "Kinolar", "items": self.list_movies(content_type="Kino", sort="new", limit=limit)["items"]},
            {"key": "series", "title": "Seriallar", "items": self.list_movies(content_type="Serial", sort="new", limit=limit)["items"]},
            {"key": "cartoons", "title": "Multfilmlar", "items": self.list_movies(content_type="Multfilm", sort="new", limit=limit)["items"]},
            {"key": "popular", "title": "Ko'p ko'rilganlar", "items": popular},
        ]
        return {
            "featured": featured,
            "stories": self.recommendations(10),
            "genres": self.genres()[:16],
            "sections": sections,
            "popular": popular,
            "new": new_items,
        }

    def movie(self, code: int) -> dict[str, Any] | None:
        ph = self.placeholder
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(
                f"""
                SELECT code,name,year,country,genre,language,imdb,views,
                       content_type,is_recommended,description,
                       CASE WHEN COALESCE(poster_file_id,'') <> '' THEN 1 ELSE 0 END AS has_poster
                FROM movies WHERE code={ph}
                """,
                (code,),
            )
            row = cur.fetchone()
            if not row:
                return None
            item = self._item(row)
            cur.execute(
                f"""
                SELECT quality
                FROM movie_qualities
                WHERE movie_code={ph}
                ORDER BY CASE quality
                    WHEN '360p' THEN 1 WHEN '480p' THEN 2 WHEN '720p' THEN 3
                    WHEN '1080p' THEN 4 WHEN 'Original' THEN 5 ELSE 6 END,
                    quality
                """,
                (code,),
            )
            item["qualities"] = [str(r["quality"] if isinstance(r, (sqlite3.Row, dict)) else r[0]) for r in cur.fetchall()]
            return item

    def poster_info(self, code: int) -> tuple[str, str] | None:
        ph = self.placeholder
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT name, poster_file_id FROM movies WHERE code={ph}", (code,))
            row = cur.fetchone()
            if not row:
                return None
            if isinstance(row, (sqlite3.Row, dict)):
                return str(row["name"] or "xD KINO"), str(row["poster_file_id"] or "")
            return str(row[0] or "xD KINO"), str(row[1] or "")

    def increase_views(self, code: int) -> int:
        ph = self.placeholder
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(f"UPDATE movies SET views=views+1 WHERE code={ph}", (code,))
            conn.commit()
            cur.execute(f"SELECT views FROM movies WHERE code={ph}", (code,))
            row = cur.fetchone()
            if not row:
                return 0
            return int(row["views"] if isinstance(row, (sqlite3.Row, dict)) else row[0])

    def genres(self) -> list[str]:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT genre FROM movies WHERE COALESCE(genre,'') <> ''")
            raw = [str((r["genre"] if isinstance(r, (sqlite3.Row, dict)) else r[0]) or "") for r in cur.fetchall()]
        out: set[str] = set()
        for value in raw:
            for part in re.split(r"[,;/|]+", value):
                part = part.strip()
                if part:
                    out.add(part)
        return sorted(out, key=str.lower)

    def filter_options(self) -> dict[str, list[str]]:
        with self.connect() as conn:
            cur = conn.cursor()
            def distinct(column: str) -> list[str]:
                cur.execute(f"SELECT DISTINCT {column} AS v FROM movies WHERE COALESCE({column},'') <> '' ORDER BY {column}")
                return [str(r["v"] if isinstance(r, (sqlite3.Row, dict)) else r[0]) for r in cur.fetchall()]
            countries = distinct("country")
            years = distinct("year")
            types = distinct("content_type")
        years.sort(reverse=True)
        return {"genres": self.genres(), "countries": countries, "years": years, "types": types}
