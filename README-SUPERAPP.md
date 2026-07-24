# xD KINO Super App — staging v1

Bu paket production botni o'zgartirmasdan `superapp-staging` Railway servisida ishlaydi.

## Hozirgi imkoniyatlar

- Telegram Mini App uchun mobil katalog
- PostgreSQL schema va xavfsiz bir martalik SQLite import
- qidiruv, janr filtri, ommabop va yangi kinolar
- kino tafsilotlari va mavjud sifatlar
- Telegram initData HMAC tekshiruvi
- sevimlilar va tomosha tarixi
- Telegram posterlarini server orqali xavfsiz proxy qilish
- healthcheck, xavfsizlik headerlari va restart siyosati

## Railway variables

`superapp-staging` servisida:

- `DATABASE_URL=${{Postgres.DATABASE_URL}}`
- `BOT_USERNAME=xDKinoCodeBot`
- `BOT_TOKEN` ixtiyoriy: loyiha `config.py` ichidagi token bilan orqaga mos ishlaydi. Keyinchalik Variables'ga ko'chirish tavsiya qilinadi.

## Tekshiruv

- `/health` — database va kino soni
- `/api/docs` — API hujjati
