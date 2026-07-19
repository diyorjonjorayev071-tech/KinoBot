import logging

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from telegram.request import HTTPXRequest

from config import TOKEN
from handlers.admin import (
    admin_callback,
    admin_photo_handler,
    admin_text_handler,
    admin_video_handler,
)
from handlers.movie_add import (
    movie_add_photo_handler,
    movie_add_text_handler,
    movie_add_video_handler,
)
from handlers.user import check_sub, movie_callback, start, user_text_handler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
# HTTPX INFO loglari Telegram tokenini URL ichida ko'rsatmasin.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


def build_application() -> Application:
    request = HTTPXRequest(
        connection_pool_size=8,
        connect_timeout=60,
        read_timeout=60,
        write_timeout=60,
        pool_timeout=60,
        httpx_kwargs={"trust_env": False},
    )

    app = Application.builder().token(TOKEN).request(request).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_sub, pattern=r"^check_sub$"))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern=r"^admin_"))
    app.add_handler(
        CallbackQueryHandler(
            movie_callback,
            pattern=r"^(quality|fav|genre|trailer):",
        )
    )

    # Kino qo'shish jarayoni.
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, movie_add_text_handler),
        group=0,
    )
    app.add_handler(MessageHandler(filters.PHOTO, movie_add_photo_handler), group=0)
    app.add_handler(MessageHandler(filters.VIDEO, movie_add_video_handler), group=0)

    # Admin tahrirlash va boshqaruv jarayoni.
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text_handler),
        group=1,
    )
    app.add_handler(MessageHandler(filters.PHOTO, admin_photo_handler), group=1)
    app.add_handler(MessageHandler(filters.VIDEO, admin_video_handler), group=1)

    # Oddiy foydalanuvchi matnlari.
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, user_text_handler),
        group=2,
    )

    async def error_handler(update, context):
        logging.error("Bot xatosi", exc_info=context.error)

    app.add_error_handler(error_handler)
    return app


def main() -> None:
    app = build_application()
    print("✅ xD KINO BOT ishga tushdi")
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
