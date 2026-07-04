from telegram import Update
from telegram.ext import ContextTypes

from config import ADMIN_ID
from database import (
    movies_count,
    users_count,
    delete_movie,
    movie_exists,
    get_users,
)
from states import user_states
from handlers.movie_add import start_movie_add


async def admin_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if user.id != ADMIN_ID:
        return

    text = update.message.text.strip()

    if text == "➕ Kino qo'shish":
        await start_movie_add(update, context)
        return

    if text == "📊 Statistika":
        await update.message.reply_text(
            f"📊 BOT STATISTIKASI\n\n"
            f"👤 Foydalanuvchilar: {users_count()}\n"
            f"🎬 Kinolar: {movies_count()}"
        )
        return

    if text == "🗑 Kino o'chirish":
        user_states[user.id] = "delete_movie"
        await update.message.reply_text("🗑 O'chirmoqchi bo'lgan kino kodini yuboring:")
        return

    if user_states.get(user.id) == "delete_movie":
        if not text.isdigit():
            await update.message.reply_text("❌ Faqat kino kodi yuboring.")
            return

        code = int(text)

        if not movie_exists(code):
            await update.message.reply_text("❌ Bunday kino mavjud emas.")
            return

        delete_movie(code)
        user_states.pop(user.id, None)

        await update.message.reply_text("✅ Kino muvaffaqiyatli o'chirildi.")
        return

    if text == "📢 Reklama yuborish":
        user_states[user.id] = "broadcast"
        await update.message.reply_text(
            "📢 Reklama xabarini yuboring.\n\n"
            "Matn, rasm, video yoki post yuborishingiz mumkin."
        )
        return

    if user_states.get(user.id) == "broadcast":
        users = get_users()
        success = 0
        failed = 0

        await update.message.reply_text("⏳ Reklama yuborish boshlandi...")

        for item in users:
            chat_id = item[0]

            try:
                await context.bot.copy_message(
                    chat_id=chat_id,
                    from_chat_id=update.message.chat_id,
                    message_id=update.message.message_id,
                )
                success += 1
            except Exception:
                failed += 1

        user_states.pop(user.id, None)

        await update.message.reply_text(
            f"✅ Reklama yuborildi!\n\n"
            f"📨 Yetkazildi: {success}\n"
            f"❌ Yetmadi: {failed}"
        )


async def admin_video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return