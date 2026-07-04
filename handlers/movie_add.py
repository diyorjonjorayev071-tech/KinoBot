from telegram import Update
from telegram.ext import ContextTypes

from database import add_movie
from states import user_states, movie_data


async def start_movie_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    movie_data[user_id] = {}
    user_states[user_id] = "add_name"

    await update.message.reply_text("🎬 Kino nomini yuboring:")


async def movie_add_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    state = user_states.get(user_id)

    if state == "add_name":
        movie_data[user_id]["name"] = text
        user_states[user_id] = "add_year"
        await update.message.reply_text("📅 Kino yilini yuboring:")
        return True

    if state == "add_year":
        movie_data[user_id]["year"] = text
        user_states[user_id] = "add_country"
        await update.message.reply_text("🌍 Davlatini yuboring:")
        return True

    if state == "add_country":
        movie_data[user_id]["country"] = text
        user_states[user_id] = "add_genre"
        await update.message.reply_text("🎭 Janrini yuboring:")
        return True

    if state == "add_genre":
        movie_data[user_id]["genre"] = text
        user_states[user_id] = "add_language"
        await update.message.reply_text("🗣 Tilini yuboring:")
        return True

    if state == "add_language":
        movie_data[user_id]["language"] = text
        user_states[user_id] = "add_imdb"
        await update.message.reply_text("⭐ IMDB reytingini yuboring:")
        return True

    if state == "add_imdb":
        movie_data[user_id]["imdb"] = text
        user_states[user_id] = "add_poster"
        await update.message.reply_text(
            "🖼 Poster rasmini yuboring.\n\n"
            "Agar poster kerak bo‘lmasa: skip"
        )
        return True

    if state == "add_poster" and text.lower() == "skip":
        movie_data[user_id]["poster_file_id"] = ""
        user_states[user_id] = "add_trailer"
        await update.message.reply_text(
            "🎞 Treyler videosini yuboring.\n\n"
            "Agar treyler kerak bo‘lmasa: skip"
        )
        return True

    if state == "add_trailer" and text.lower() == "skip":
        movie_data[user_id]["trailer_file_id"] = ""
        user_states[user_id] = "add_video"
        await update.message.reply_text("📹 Endi asosiy kino videosini yuboring:")
        return True

    return False


async def movie_add_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_states.get(user_id) != "add_poster":
        return False

    photo = update.message.photo[-1]
    movie_data[user_id]["poster_file_id"] = photo.file_id

    user_states[user_id] = "add_trailer"

    await update.message.reply_text(
        "✅ Poster qabul qilindi.\n\n"
        "🎞 Endi treyler videosini yuboring.\n"
        "Agar treyler kerak bo‘lmasa: skip"
    )

    return True


async def movie_add_video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = user_states.get(user_id)

    if state == "add_trailer":
        movie_data[user_id]["trailer_file_id"] = update.message.video.file_id
        user_states[user_id] = "add_video"

        await update.message.reply_text(
            "✅ Treyler qabul qilindi.\n\n"
            "📹 Endi asosiy kino videosini yuboring:"
        )
        return True

    if state == "add_video":
        data = movie_data.get(user_id, {})

        name = data.get("name", "")
        year = data.get("year", "")
        country = data.get("country", "")
        genre = data.get("genre", "")
        language = data.get("language", "")
        imdb = data.get("imdb", "")
        trailer_file_id = data.get("trailer_file_id", "")
        poster_file_id = data.get("poster_file_id", "")
        file_id = update.message.video.file_id

        code = add_movie(
            name=name,
            year=year,
            country=country,
            genre=genre,
            language=language,
            imdb=imdb,
            trailer_file_id=trailer_file_id,
            poster_file_id=poster_file_id,
            file_id=file_id,
        )

        user_states.pop(user_id, None)
        movie_data.pop(user_id, None)

        await update.message.reply_text(
            f"✅ Kino saqlandi!\n\n"
            f"🎬 Nomi: {name}\n"
            f"📅 Yili: {year}\n"
            f"🌍 Davlati: {country}\n"
            f"🎭 Janri: {genre}\n"
            f"🗣 Tili: {language}\n"
            f"⭐ IMDB: {imdb}\n\n"
            f"🔑 Kodi: <code>{code}</code>",
            parse_mode="HTML"
        )

        return True

    return False