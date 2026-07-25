# KinoBot PostgreSQL Bridge v1

Bu paket production botni hozircha o'zgartirmaydi. U ikkita backend beradi:

- `DATABASE_URL` bor: PostgreSQL
- `DATABASE_URL` yo'q: avvalgi SQLite

Fayllar:

- `database.py` — backend tanlagich
- `database_sqlite.py` — mavjud SQLite kodining o'zgarmagan nusxasi
- `database_postgres.py` — Super App PostgreSQL sxemasi bilan mos backend
- `requirements.txt` — psycopg drayveri qo'shilgan

Muhim: avval `postgres-sync` branchda sintaksis va lokal SQLite regressiya testi bajariladi. Production deploy keyingi alohida bosqichda qilinadi.
