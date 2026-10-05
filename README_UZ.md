# xD KINO CLEAN

Bu loyiha xD KINO Mini App uchun boshidan yozilgan toza, alohida versiya.

## Nimalar bor

- Qora + neon-yashil zamonaviy kino interfeysi.
- Faqat kod bilan chizilgan cinematic splash: kino g'altagi, film lenta, clapperboard, popcorn va xD KINO logo.
- Bosh sahifa: hero, janrlar, yangi kinolar, kinolar, seriallar, multfilmlar, ko'p ko'rilganlar.
- **Siz uchun tavsiyalar**: Kino + Serial + Multfilm ichidan IMDb **7.5 yoki yuqori**, so'ng ko'rishlar bo'yicha saralanadi.
- Qidiruv va tur/janr/yil/davlat filtrlari.
- Kino batafsil oynasi, sifatlar, sevimlilar va ko'rish tarixi.
- Telegram WebApp bilan ishlaydi.
- PostgreSQL bo'lsa mavjud katalogdan o'qiydi; `DATABASE_URL` bo'lmasa lokal SQLite demo bazasi bilan ishga tushadi.
- `BOT_TOKEN` berilsa Telegramdagi `poster_file_id` orqali posterlarni backend xavfsiz olib beradi. Token brauzerga chiqarilmaydi.
- Dockerfile bor: alohida service/repo sifatida deploy qilish oson.

## Kompyuterda ishga tushirish

PowerShell:

```powershell
cd xD_KINO_CLEAN
Copy-Item .env.example .env
.\START.ps1
```

Keyin brauzerda:

`http://127.0.0.1:8000`

## Production bazaga ulash

`.env` ichida `DATABASE_URL` ni hostingdagi PostgreSQL qiymatiga sozlang. Maxfiy qiymatlarni GitHub'ga commit qilmang.

Posterlar uchun `BOT_TOKEN` server environment variable sifatida beriladi. Token hech qachon `static/app.js` yoki `index.html` ichiga yozilmasligi kerak.

## Telegramdagi "Botda ko'rish" tugmasi

`.env`:

```env
BOT_USERNAME=xDKinoCodeBot
BOT_START_PREFIX=movie_
```

Shunda kino kodi 123 bo'lsa tugma `https://t.me/xDKinoCodeBot?start=movie_123` formatida ochadi. Agar botingiz boshqa start format ishlatsa, faqat `BOT_START_PREFIX` ni o'zgartiring.

## Railway uchun

Loyiha Dockerfile bilan keladi. Uni **alohida SuperApp service** sifatida deploy qilish tavsiya etiladi. `PORT` Railway tomonidan avtomatik beriladi; Dockerfile shu portni ishlatadi.

Healthcheck:

`/health`

## Muhim

Bu paket eski ishchi fayllarni ustiga yozish uchun emas. Avval alohida papkada tekshirib ko'rish uchun tayyorlangan. Ishlayotgan bot/worker/Postgres servislariga tegmasdan sinash mumkin.
