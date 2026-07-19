from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from database import get_movie_full, get_movie_quality_rows


def admin_movie_text(code: int) -> str:
    movie = get_movie_full(code)
    if not movie:
        return "❌ Kino topilmadi."

    (
        _code,
        name,
        year,
        country,
        genre,
        language,
        imdb,
        poster_file_id,
        _file_id,
        views,
        _created_at,
    ) = movie
    qualities = get_movie_quality_rows(code)
    quality_text = ", ".join(escape(str(row[1])) for row in qualities) or "yo‘q"

    return (
        "✏️ <b>Kino tahrirlash</b>\n\n"
        f"🔑 Kod: <code>{code}</code>\n"
        f"🎬 Nomi: {escape(str(name))}\n"
        f"📅 Yili: {escape(str(year or '-'))}\n"
        f"🌍 Davlati: {escape(str(country or '-'))}\n"
        f"🎭 Janri: {escape(str(genre or '-'))}\n"
        f"🗣 Tili: {escape(str(language or '-'))}\n"
        f"⭐ IMDB: {escape(str(imdb or '-'))}\n"
        f"🖼 Poster: {'bor' if poster_file_id else 'yo‘q'}\n"
        f"🎞 Sifatlar: {quality_text}\n"
        f"👁 Ko‘rishlar: {views}\n\n"
        "O‘zgartiriladigan bo‘limni tanlang:"
    )


def admin_edit_keyboard(code: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🎬 Nomi", callback_data=f"admin_field:{code}:name"),
                InlineKeyboardButton("📅 Yili", callback_data=f"admin_field:{code}:year"),
            ],
            [
                InlineKeyboardButton("🌍 Davlati", callback_data=f"admin_field:{code}:country"),
                InlineKeyboardButton("🎭 Janri", callback_data=f"admin_field:{code}:genre"),
            ],
            [
                InlineKeyboardButton("🗣 Tili", callback_data=f"admin_field:{code}:language"),
                InlineKeyboardButton("⭐ IMDB", callback_data=f"admin_field:{code}:imdb"),
            ],
            [
                InlineKeyboardButton("🖼 Poster", callback_data=f"admin_poster:{code}"),
                InlineKeyboardButton("🔑 Kod", callback_data=f"admin_code:{code}"),
            ],
            [
                InlineKeyboardButton("➕ Sifat qo‘shish", callback_data=f"admin_qadd:{code}"),
                InlineKeyboardButton("➖ Sifat o‘chirish", callback_data=f"admin_qdel_menu:{code}"),
            ],
            [InlineKeyboardButton("✅ Tugatish", callback_data=f"admin_done:{code}")],
        ]
    )


def admin_quality_delete_keyboard(code: int) -> InlineKeyboardMarkup:
    rows = get_movie_quality_rows(code)
    buttons = [
        [
            InlineKeyboardButton(
                f"🗑 {quality}",
                callback_data=f"admin_qdel:{code}:{quality_id}",
            )
        ]
        for quality_id, quality in rows
    ]
    buttons.append(
        [InlineKeyboardButton("⬅️ Orqaga", callback_data=f"admin_menu:{code}")]
    )
    return InlineKeyboardMarkup(buttons)
