import logging

from telegram.request import HTTPXRequest
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from config import TOKEN
from handlers.user import start, check_sub, user_text_handler, movie_callback
from handlers.admin import admin_text_handler
from handlers.movie_add import (
    movie_add_text_handler,
    movie_add_photo_handler,
    movie_add_video_handler,
)


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

request = HTTPXRequest(
    connection_pool_size=8,
    connect_timeout=60,
    read_timeout=60,
    write_timeout=60,
    pool_timeout=60,
    httpx_kwargs={"trust_env": False},
)

app = (
    Application.builder()
    .token(TOKEN)
    .request(request)
    .build()
)

app.add_handler(CommandHandler("start", start))

app.add_handler(CallbackQueryHandler(check_sub, pattern="^check_sub$"))
app.add_handler(CallbackQueryHandler(movie_callback, pattern="^(trailer|fav|genre):"))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, movie_add_text_handler), group=0)
app.add_handler(MessageHandler(filters.PHOTO, movie_add_photo_handler), group=0)
app.add_handler(MessageHandler(filters.VIDEO, movie_add_video_handler), group=0)

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text_handler), group=1)
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, user_text_handler), group=2)


async def error_handler(update, context):
    logging.error("Bot xatosi:", exc_info=context.error)


app.add_error_handler(error_handler)

print("✅ xD KINO BOT ishga tushdi")

app.run_polling(allowed_updates=["message", "callback_query"])