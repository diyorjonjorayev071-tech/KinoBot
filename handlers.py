from telegram import Update
from telegram.ext import ContextTypes

from config import ADMIN_ID, CHANNEL_USERNAME
from keyboards import admin_keyboard, subscribe_keyboard
from database import add_user, get_movie, add_movie
from states import user_states, movie_names


# =========================
# KANALGA A'ZOLIKNI TEKSHIRISH
# =========================

async def check_subscription(bot, user_id: int):
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False


# =========================
# /START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    add_user(user.id)

    if not await check_subscription(context.bot, user.id):
        await update.message.reply_text(
            "❌ Botdan foydalanish uchun avval kanalga a'zo bo'ling.",
            reply_markup=subscribe_keyboard
        )
        return

    if user.id == ADMIN_ID:
        await update.message.reply_text(
            "👋 Xush kelibsiz, Admin!",
            reply_markup=admin_keyboard
        )
    else:
        await update.message.reply_text(
            "🎬 Kino kodini yuboring."
        )


# =========================
# KANALNI TEKSHIRISH TUGMASI
# =========================

async def check_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user

    if not await check_subscription(context.bot, user.id):
        await query.answer(
            "❌ Siz hali kanalga a'zo bo'lmagansiz!",
            show_alert=True
        )
        return

    await query.message.delete()

    if user.id == ADMIN_ID:
        await context.bot.send_message(
            chat_id=user.id,
            text="👋 Xush kelibsiz Admin!",
            reply_markup=admin_keyboard
        )
    else:
        await context.bot.send_message(
            chat_id=user.id,
            text="✅ A'zolik tasdiqlandi.\n\n🎬 Endi kino kodini yuboring."
        )


# =========================
# TEXT HANDLER
# =========================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # ADMIN - KINO QO'SHISH
    if user_id == ADMIN_ID and text == "➕ Kino qo'shish":
        user_states[user_id] = "waiting_name"
        await update.message.reply_text("🎬 Kino nomini yuboring:")
        return

    # ADMIN - NOM QABUL QILISH
    if user_states.get(user_id) == "waiting_name":
        movie_names[user_id] = text
        user_states[user_id] = "waiting_video"

        await update.message.reply_text("📹 Endi kino videosini yuboring:")
        return

    # FOYDALANUVCHI FAQAT KOD YUBORADI
    if not text.isdigit():
        await update.message.reply_text("❌ Faqat kino kodini yuboring.")
        return

    movie = get_movie(int(text))

    if not movie:
        await update.message.reply_text("❌ Bunday kodli kino topilmadi.")
        return

    name, file_id = movie

    me = await context.bot.get_me()

    caption = (
        f"🎬 <b>{name}</b>\n\n"
        f"📢 Kanal: {CHANNEL_USERNAME}\n"
        f"🤖 Bot: @{me.username}\n\n"
        f"🍿 Yoqimli tomosha!"
    )

    await update.message.reply_video(
        video=file_id,
        caption=caption,
        parse_mode="HTML"
    )


# =========================
# VIDEO HANDLER
# =========================

async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_states.get(user_id) != "waiting_video":
        return

    file_id = update.message.video.file_id
    name = movie_names.get(user_id)

    if not name:
        await update.message.reply_text("❌ Kino nomi topilmadi.")
        return

    code = add_movie(name, file_id)

    user_states.pop(user_id, None)
    movie_names.pop(user_id, None)

    await update.message.reply_text(
        f"✅ Kino muvaffaqiyatli saqlandi!\n\n"
        f"🎬 Nomi: {name}\n"
        f"🔑 Kodi: {code}"
    )