from html import escape

from telegram import Update
from telegram.ext import ContextTypes

from config import ADMIN_ID
from database import add_movie, normalize_quality
from handlers.admin_ui import admin_edit_keyboard, admin_movie_text
from states import movie_data, user_states


async def start_movie_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return

    movie_data[user_id] = {}
    user_states[user_id] = "add_name"
    await update.message.reply_text(
        "🎬 Kino nomini yuboring:\n\n"
        "Jarayonni to‘xtatish uchun: <code>bekor</code>",
        parse_mode="HTML",
    )


async def movie_add_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return

    text = update.message.text.strip()
    state = user_states.get(user_id, "")

    # "bekor" admin.py ichida qayta ishlanadi.
    if text.lower() in {"bekor", "cancel", "/cancel", "❌ bekor qilish"}:
        return

    if state == "add_name":
        movie_data.setdefault(user_id, {})["name"] = text
        user_states[user_id] = "add_year"
        await update.message.reply_text("📅 Kino yilini yuboring:")
        return

    if state == "add_year":
        movie_data[user_id]["year"] = text
        user_states[user_id] = "add_country"
        await update.message.reply_text("🌍 Davlatini yuboring:")
        return

    if state == "add_country":
        movie_data[user_id]["country"] = text
        user_states[user_id] = "add_genre"
        await update.message.reply_text("🎭 Janrini yuboring:")
        return

    if state == "add_genre":
        movie_data[user_id]["genre"] = text
        user_states[user_id] = "add_language"
        await update.message.reply_text("🗣 Tilini yuboring:")
        return

    if state == "add_language":
        movie_data[user_id]["language"] = text
        user_states[user_id] = "add_imdb"
        await update.message.reply_text("⭐ IMDB reytingini yuboring:")
        return

    if state == "add_imdb":
        movie_data[user_id]["imdb"] = text
        user_states[user_id] = "add_poster"
        await update.message.reply_text(
            "🖼 Poster rasmini yuboring.\n\n"
            "Poster kerak bo‘lmasa: <code>skip</code>",
            parse_mode="HTML",
        )
        return

    if state == "add_poster" and text.lower() == "skip":
        movie_data[user_id]["poster_file_id"] = ""
        user_states[user_id] = "add_quality_name"
        await update.message.reply_text(
            "🎞 Birinchi video sifatini yuboring.\n"
            "Masalan: <code>360p</code>, <code>480p</code>, "
            "<code>720p</code>, <code>1080p</code> yoki <code>Original</code>",
            parse_mode="HTML",
        )
        return

    if state == "add_quality_name":
        try:
            quality = normalize_quality(text)
        except ValueError as error:
            await update.message.reply_text(f"❌ {escape(str(error))}", parse_mode="HTML")
            return

        movie_data[user_id]["quality"] = quality
        user_states[user_id] = "add_video"
        await update.message.reply_text(
            f"🎞 Sifat: <b>{escape(quality)}</b>\n\n"
            "Endi shu sifatdagi asosiy kino videosini yuboring:",
            parse_mode="HTML",
        )
        return


async def movie_add_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID or user_states.get(user_id) != "add_poster":
        return

    photo = update.message.photo[-1]
    movie_data.setdefault(user_id, {})["poster_file_id"] = photo.file_id
    user_states[user_id] = "add_quality_name"
    await update.message.reply_text(
        "✅ Poster qabul qilindi.\n\n"
        "🎞 Birinchi video sifatini yuboring.\n"
        "Masalan: <code>360p</code>, <code>480p</code>, "
        "<code>720p</code>, <code>1080p</code> yoki <code>Original</code>",
        parse_mode="HTML",
    )


async def movie_add_video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID or user_states.get(user_id) != "add_video":
        return

    data = movie_data.get(user_id, {})
    required = ["name", "year", "country", "genre", "language", "imdb", "quality"]
    if any(key not in data for key in required):
        user_states.pop(user_id, None)
        movie_data.pop(user_id, None)
        await update.message.reply_text(
            "❌ Kino ma’lumotlari to‘liq emas. Jarayonni qaytadan boshlang."
        )
        return

    code = add_movie(
        name=data["name"],
        year=data["year"],
        country=data["country"],
        genre=data["genre"],
        language=data["language"],
        imdb=data["imdb"],
        trailer_file_id="",
        poster_file_id=data.get("poster_file_id", ""),
        file_id=update.message.video.file_id,
        quality=data["quality"],
    )

    user_states.pop(user_id, None)
    movie_data.pop(user_id, None)

    await update.message.reply_text(
        f"✅ Kino saqlandi!\n\n"
        f"🎬 Nomi: <b>{escape(str(data['name']))}</b>\n"
        f"🎞 Birinchi sifat: <b>{escape(str(data['quality']))}</b>\n"
        f"🔑 Kodi: <code>{code}</code>\n\n"
        "Boshqa sifatlarni quyidagi menyudan qo‘shishingiz mumkin.",
        parse_mode="HTML",
    )
    await update.message.reply_text(
        admin_movie_text(code),
        parse_mode="HTML",
        reply_markup=admin_edit_keyboard(code),
    )
