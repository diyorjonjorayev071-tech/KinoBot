"""KinoBot ma'lumotlar bazasi tanlagichi.

Railway'da DATABASE_URL mavjud bo'lsa PostgreSQL ishlatiladi.
Mahalliy kompyuterda yoki DATABASE_URL bo'lmasa avvalgi SQLite backend ishlaydi.
"""

import os

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

if DATABASE_URL:
    from database_postgres import *  # noqa: F401,F403
else:
    from database_sqlite import *  # noqa: F401,F403
