import sqlite3
import random
from datetime import datetime

conn = sqlite3.connect("movies.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
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
    created_at TEXT DEFAULT ''
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    created_at TEXT DEFAULT ''
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS favorites(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    movie_code INTEGER,
    created_at TEXT DEFAULT '',
    UNIQUE(user_id, movie_code)
)
""")

conn.commit()


def ensure_columns():
    cursor.execute("PRAGMA table_info(movies)")
    columns = [col[1] for col in cursor.fetchall()]

    movie_columns = {
        "year": "TEXT DEFAULT ''",
        "country": "TEXT DEFAULT ''",
        "genre": "TEXT DEFAULT ''",
        "language": "TEXT DEFAULT ''",
        "imdb": "TEXT DEFAULT ''",
        "trailer_file_id": "TEXT DEFAULT ''",
        "poster_file_id": "TEXT DEFAULT ''",
        "views": "INTEGER DEFAULT 0",
        "created_at": "TEXT DEFAULT ''",
    }

    for column, column_type in movie_columns.items():
        if column not in columns:
            cursor.execute(f"ALTER TABLE movies ADD COLUMN {column} {column_type}")

    cursor.execute("PRAGMA table_info(users)")
    user_columns = [col[1] for col in cursor.fetchall()]

    if "created_at" not in user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN created_at TEXT DEFAULT ''")

    conn.commit()


ensure_columns()


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def add_user(user_id: int):
    cursor.execute(
        "INSERT OR IGNORE INTO users(user_id, created_at) VALUES(?, ?)",
        (user_id, now())
    )
    conn.commit()


def get_users():
    cursor.execute("SELECT user_id FROM users")
    return cursor.fetchall()


def users_count():
    cursor.execute("SELECT COUNT(*) FROM users")
    return cursor.fetchone()[0]


def movies_count():
    cursor.execute("SELECT COUNT(*) FROM movies")
    return cursor.fetchone()[0]


def generate_code():
    while True:
        code = random.randint(1000, 9999)
        cursor.execute("SELECT id FROM movies WHERE code=?", (code,))
        if cursor.fetchone() is None:
            return code


def add_movie(name, year, country, genre, language, imdb, trailer_file_id, poster_file_id, file_id):
    code = generate_code()

    cursor.execute(
        """
        INSERT INTO movies(
            code, name, year, country, genre, language, imdb,
            trailer_file_id, poster_file_id, file_id, views, created_at
        )
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            code, name, year, country, genre, language, imdb,
            trailer_file_id, poster_file_id, file_id, 0, now()
        )
    )

    conn.commit()
    return code


def get_movie(code):
    cursor.execute(
        """
        SELECT name, year, country, genre, language, imdb,
               trailer_file_id, poster_file_id, file_id, views
        FROM movies
        WHERE code=?
        """,
        (code,)
    )
    return cursor.fetchone()


def increase_views(code):
    cursor.execute(
        "UPDATE movies SET views = views + 1 WHERE code=?",
        (code,)
    )
    conn.commit()


def delete_movie(code):
    cursor.execute("DELETE FROM movies WHERE code=?", (code,))
    cursor.execute("DELETE FROM favorites WHERE movie_code=?", (code,))
    conn.commit()


def movie_exists(code):
    cursor.execute("SELECT id FROM movies WHERE code=?", (code,))
    return cursor.fetchone() is not None


def search_movies(query):
    cursor.execute(
        """
        SELECT code, name, year, genre
        FROM movies
        WHERE name LIKE ?
        ORDER BY id DESC
        LIMIT 10
        """,
        (f"%{query}%",)
    )
    return cursor.fetchall()


def add_favorite(user_id, movie_code):
    cursor.execute(
        "INSERT OR IGNORE INTO favorites(user_id, movie_code, created_at) VALUES(?, ?, ?)",
        (user_id, movie_code, now())
    )
    conn.commit()


def remove_favorite(user_id, movie_code):
    cursor.execute(
        "DELETE FROM favorites WHERE user_id=? AND movie_code=?",
        (user_id, movie_code)
    )
    conn.commit()


def is_favorite(user_id, movie_code):
    cursor.execute(
        "SELECT id FROM favorites WHERE user_id=? AND movie_code=?",
        (user_id, movie_code)
    )
    return cursor.fetchone() is not None


def get_favorites(user_id):
    cursor.execute(
        """
        SELECT movies.code, movies.name, movies.year, movies.genre
        FROM favorites
        JOIN movies ON favorites.movie_code = movies.code
        WHERE favorites.user_id=?
        ORDER BY favorites.id DESC
        LIMIT 20
        """,
        (user_id,)
    )
    return cursor.fetchall()


def get_top_movies(limit=10):
    cursor.execute(
        """
        SELECT code, name, year, genre, views
        FROM movies
        ORDER BY views DESC
        LIMIT ?
        """,
        (limit,)
    )
    return cursor.fetchall()


def get_genres():
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
    cursor.execute(
        """
        SELECT code, name, year, genre
        FROM movies
        WHERE genre=?
        ORDER BY id DESC
        LIMIT 20
        """,
        (genre,)
    )
    return cursor.fetchall()