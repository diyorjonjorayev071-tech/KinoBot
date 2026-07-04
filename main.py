from telegram.request import HTTPXRequest
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from config import TOKEN
from handlers import (
    start,
    check_sub,
    text_handler,
    video_handler,
)

request = HTTPXRequest(
    connection_pool_size=8,
    connect_timeout=60,
    read_timeout=60,
    write_timeout=60,
    pool_timeout=60,
    httpx_kwargs={
        "trust_env": False,
    },
)

app = (
    Application.builder()
    .token(TOKEN)
    .request(request)
    .build()
)

# /start
app.add_handler(CommandHandler("start", start))

# Kanalga a'zolikni tekshirish
app.add_handler(CallbackQueryHandler(check_sub, pattern="^check_sub$"))

# Matnlar
app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        text_handler,
    )
)

# Videolar
app.add_handler(
    MessageHandler(
        filters.VIDEO,
        video_handler,
    )
)

print("✅ xD KINO BOT ishga tushdi!")

app.run_polling(
    allowed_updates=["message", "callback_query"]
)