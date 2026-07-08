from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from config import ADMIN_ID, CHANNEL_USERNAME, CHANNEL_LINK
from keyboards import admin_keyboard, user_keyboard, subscribe_keyboard
from database import (
    add_user,
    get_movie,
    search_movies,
    increase_views,
    add_favorite,
    remove_favorite,
    is_favorite,
    get_favorites,
    get_top_movies,
    get_genres,
    get_movies_by_genre,
)
from states import user_states


async def check_subscription(bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id)

    if not await check_subscription(context.bot, user.id):
        await update.message.reply_text(
            "❌ Botdan foydalanish uchun avval kanalga a'zo bo'ling.",
            reply_markup=subscribe_keyboard,
        )
        return

    if user.id == ADMIN_ID:
        await update.message.reply_text(
            "👋 Xush kelibsiz, Admin!",
            reply_markup=admin_keyboard,
        )
        return

    await update.message.reply_text(
        "🎬 xD KINO BOT ga xush kelibsiz!",
        reply_markup=user_keyboard,
    )


async def check_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    add_user(user.id)

    if not await check_subscription(context.bot, user.id):
        await query.answer("❌ Siz hali kanalga a'zo emassiz!", show_alert=True)
        return

    try:
        await query.message.delete()
    except Exception:
        pass

    if user.id == ADMIN_ID:
        await context.bot.send_message(
            chat_id=user.id,
            text="✅ A'zolik tasdiqlandi.\n\n👮 Admin panel ochildi.",
            reply_markup=admin_keyboard,
        )
        return

    await context.bot.send_message(
        chat_id=user.id,
        text="✅ A'zolik tasdiqlandi!",
        reply_markup=user_keyboard,
    )


def movie_buttons(code: int, trailer_file_id: str, user_id: int):
    fav_text = "💔 Sevimlidan olish" if is_favorite(user_id, code) else "⭐ Sevimli"

    buttons = [
        [InlineKeyboardButton(fav_text, callback_data=f"fav:{code}")]
    ]

    row = []

    if trailer_file_id:
        row.append(InlineKeyboardButton("🎞 Treyler", callback_data=f"trailer:{code}"))

    row.append(InlineKeyboardButton("📢 Kanal", url=CHANNEL_LINK))
    buttons.append(row)

    return InlineKeyboardMarkup(buttons)


async def send_movie(update: Update, context: ContextTypes.DEFAULT_TYPE, code: int):
    movie = get_movie(code)

    if not movie:
        await update.message.reply_text("❌ Bunday kodli kino topilmadi.")
        return

    (
        name,
        year,
        country,
        genre,
        language,
        imdb,
        trailer_file_id,
        poster_file_id,
        file_id,
        views,
    ) = movie

    increase_views(code)
    views += 1

    me = await context.bot.get_me()

    caption = (
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🎬 <b>{name}</b>\n\n"
        f"⭐ IMDB: {imdb}\n"
        f"📅 Yili: {year}\n"
        f"🌍 Davlati: {country}\n"
        f"🎭 Janri: {genre}\n"
        f"🗣 Tili: {language}\n"
        f"👁 Ko‘rishlar: {views}\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"🍿 Yoqimli tomosha!\n\n"
        f"📢 Kanal: <a href='{CHANNEL_LINK}'>{CHANNEL_USERNAME}</a>\n"
        f"🤖 Bot: @{me.username}\n"
        f"━━━━━━━━━━━━━━━━━━"
    )

    keyboard = movie_buttons(code, trailer_file_id, update.effective_user.id)

    if poster_file_id:
        await update.message.reply_photo(
            photo=poster_file_id,
            caption=caption,
            parse_mode="HTML",
            reply_markup=keyboard,
        )

        await update.message.reply_video(
            video=file_id,
            caption=f"🎬 <b>{name}</b>",
            parse_mode="HTML",
        )
    else:
        await update.message.reply_video(
            video=file_id,
            caption=caption,
            parse_mode="HTML",
            reply_markup=keyboard,
        )


async def show_favorites(update: Update, context: ContextTypes.DEFAULT_TYPE):
    favorites = get_favorites(update.effective_user.id)

    if not favorites:
        await update.message.reply_text("❤️ Sevimlilar ro‘yxatingiz bo‘sh.")
        return

    text = "❤️ <b>Sevimli kinolaringiz:</b>\n\n"

    for code, name, year, genre in favorites:
        text += (
            f"🎬 <b>{name}</b>\n"
            f"📅 {year} | 🎭 {genre}\n"
            f"🔑 Kod: <code>{code}</code>\n\n"
        )

    await update.message.reply_text(text, parse_mode="HTML")


async def show_top_movies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    movies = get_top_movies()

    if not movies:
        await update.message.reply_text("❌ Hozircha top kinolar mavjud emas.")
        return

    msg = "🔥 <b>TOP 10 Kinolar</b>\n\n"

    for i, (code, name, year, genre, views) in enumerate(movies, start=1):
        msg += (
            f"{i}. 🎬 <b>{name}</b>\n"
            f"👁 {views} | 📅 {year}\n"
            f"🔑 Kod: <code>{code}</code>\n\n"
        )

    await update.message.reply_text(msg, parse_mode="HTML")


async def show_genres(update: Update, context: ContextTypes.DEFAULT_TYPE):
    genres = get_genres()

    if not genres:
        await update.message.reply_text("❌ Janrlar mavjud emas.")
        return

    keyboard = []

    for genre, count in genres:
        keyboard.append([
            InlineKeyboardButton(
                f"🎭 {genre} ({count})",
                callback_data=f"genre:{genre}",
            )
        ])

    await update.message.reply_text(
        "🎭 Janrni tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def show_movies_by_genre(update: Update, context: ContextTypes.DEFAULT_TYPE, genre: str):
    movies = get_movies_by_genre(genre)

    if not movies:
        await update.message.reply_text("❌ Bu janrda kino topilmadi.")
        return

    msg = f"🎭 <b>{genre}</b>\n\n"

    for code, name, year, genre_name in movies:
        msg += (
            f"🎬 <b>{name}</b>\n"
            f"📅 {year}\n"
            f"🔑 Kod: <code>{code}</code>\n\n"
        )

    await update.message.reply_text(msg, parse_mode="HTML")


async def search_by_name(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str):
    results = search_movies(query)

    if not results:
        await update.message.reply_text("❌ Bu nom bo‘yicha kino topilmadi.")
        return

    message = "🔍 <b>Qidiruv natijalari:</b>\n\n"

    for code, name, year, genre in results:
        message += (
            f"🎬 <b>{name}</b>\n"
            f"📅 {year} | 🎭 {genre}\n"
            f"🔑 Kod: <code>{code}</code>\n\n"
        )

    message += "Kerakli kino kodini yuboring."

    await update.message.reply_text(message, parse_mode="HTML")


async def user_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()

    add_user(user.id)

    if user.id == ADMIN_ID and user_states.get(user.id):
        return

    if not await check_subscription(context.bot, user.id):
        await update.message.reply_text(
            "🎬 xD KINO BOT\n\n"
"Botdan foydalanishni davom ettirish uchun quyidagi rasmiy sahifalarimizga obuna bo'ling.\n\n"
"📢 Telegram kanal\n"
"📸 Instagram sahifasi\n\n"
"Obuna bo'lgach, «✅ Tekshirish» tugmasini bosing.",
            reply_markup=subscribe_keyboard,
        )
        return

    if text == "🔍 Kino qidirish":
        user_states[user.id] = "search_movie"
        await update.message.reply_text("🔍 Kino nomi yoki kodini kiriting:")
        return

    if text == "🔥 Top kinolar":
        await show_top_movies(update, context)
        return

    if text == "❤️ Sevimlilar":
        await show_favorites(update, context)
        return

    if text == "🎭 Janrlar":
        await show_genres(update, context)
        return

    if text == "📢 Kanal":
        await update.message.reply_text(f"📢 Kanalimiz: {CHANNEL_LINK}")
        return

    if text == "ℹ️ Yordam":
        await update.message.reply_text(
            "ℹ️ <b>Yordam</b>\n\n"
            "🔍 Kino qidirish — kino nomi yoki kod orqali qidirish.\n"
            "🔥 Top kinolar — eng ko‘p ko‘rilgan kinolar.\n"
            "❤️ Sevimlilar — saqlangan kinolaringiz.\n"
            "🎭 Janrlar — janrlar bo‘yicha kinolar.\n\n"
            "Kino olish uchun kod yuboring. Masalan: <code>1234</code>",
            parse_mode="HTML",
        )
        return

    if user_states.get(user.id) == "search_movie":
        user_states.pop(user.id, None)

        if text.isdigit():
            await send_movie(update, context, int(text))
            return

        await search_by_name(update, context, text)
        return

    genres = get_genres()
    for genre, _ in genres:
        if text.lower() == genre.lower():
            await show_movies_by_genre(update, context, genre)
            return

    if text.isdigit():
        await send_movie(update, context, int(text))
        return

    await search_by_name(update, context, text)


async def movie_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = query.from_user.id

    if data.startswith("trailer:"):
        code = int(data.split(":")[1])
        movie = get_movie(code)

        if not movie:
            await query.answer("❌ Kino topilmadi.", show_alert=True)
            return

        name = movie[0]
        trailer_file_id = movie[6]

        if not trailer_file_id:
            await query.answer("❌ Treyler mavjud emas.", show_alert=True)
            return

        await context.bot.send_video(
            chat_id=query.message.chat_id,
            video=trailer_file_id,
            caption=f"🎞 <b>{name}</b> treyleri",
            parse_mode="HTML",
        )
        return

    if data.startswith("fav:"):
        code = int(data.split(":")[1])

        if is_favorite(user_id, code):
            remove_favorite(user_id, code)
            await query.answer("💔 Sevimlilardan olib tashlandi.", show_alert=True)
        else:
            add_favorite(user_id, code)
            await query.answer("⭐ Sevimlilarga qo‘shildi.", show_alert=True)
        return

    if data.startswith("genre:"):
        genre = data.split(":", 1)[1]
        movies = get_movies_by_genre(genre)

        if not movies:
            await query.answer("❌ Kino topilmadi.", show_alert=True)
            return

        text = f"🎭 <b>{genre}</b>\n\n"

        for code, name, year, genre_name in movies:
            text += (
                f"🎬 <b>{name}</b>\n"
                f"📅 {year}\n"
                f"🔑 <code>{code}</code>\n\n"
            )

        await query.message.reply_text(text, parse_mode="HTML")
        return