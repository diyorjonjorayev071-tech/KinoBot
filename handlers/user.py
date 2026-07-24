from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from config import ADMIN_ID, CHANNEL_LINK, CHANNEL_USERNAME
from database import (
    add_favorite,
    add_movie_quality,
    add_user,
    get_favorites,
    get_genres,
    get_movie,
    get_movie_qualities,
    get_movie_quality_by_id,
    get_movie_quality_rows,
    get_movies_by_genre,
    get_top_movies,
    increase_views,
    is_favorite,
    remove_favorite,
    search_movies,
)
from keyboards import admin_keyboard, subscribe_keyboard, user_keyboard
from states import user_states


async def check_subscription(bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False


def _movie_code_from_start_args(args) -> int | None:
    if not args:
        return None

    payload = str(args[0]).strip()
    prefix = "movie_"
    if not payload.startswith(prefix):
        return None

    code_text = payload[len(prefix):]
    if not code_text.isdigit():
        return None
    return int(code_text)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id)

    if not await check_subscription(context.bot, user.id):
        await update.message.reply_text(
            "❌ Botdan foydalanish uchun avval kanalga a'zo bo'ling.",
            reply_markup=subscribe_keyboard,
        )
        return

    # Super App ichidagi “Botda tomosha” tugmasi:
    # https://t.me/xDKinoCodeBot?start=movie_1234
    movie_code = _movie_code_from_start_args(context.args)
    if movie_code is not None:
        await send_movie(update, context, movie_code)
        return

    if user.id == ADMIN_ID:
        await update.message.reply_text(
            "👋 Xush kelibsiz, Admin!",
            reply_markup=admin_keyboard,
        )
        return

    await update.message.reply_text(
        "🎬 xD KINO BOT ga xush kelibsiz!\n\nKino kodini yuboring.",
        reply_markup=user_keyboard,
    )


async def check_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    add_user(user.id)

    if not await check_subscription(context.bot, user.id):
        await query.answer("❌ Siz hali kanalga a'zo emassiz!", show_alert=True)
        return

    await query.answer("✅ A'zolik tasdiqlandi!")
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
        text="✅ A'zolik tasdiqlandi!\n\n🎬 Kino kodini yuboring.",
        reply_markup=user_keyboard,
    )


def _movie_caption(movie, bot_username: str, *, views: int | None = None) -> str:
    (
        name,
        year,
        country,
        genre,
        language,
        imdb,
        _trailer_file_id,
        _poster_file_id,
        _file_id,
        current_views,
    ) = movie

    shown_views = current_views if views is None else views
    return (
        "━━━━━━━━━━━━━━━━━━\n"
        f"🎬 <b>{escape(str(name))}</b>\n\n"
        f"⭐ IMDB: {escape(str(imdb or '-'))}\n"
        f"📅 Yili: {escape(str(year or '-'))}\n"
        f"🌍 Davlati: {escape(str(country or '-'))}\n"
        f"🎭 Janri: {escape(str(genre or '-'))}\n"
        f"🗣 Tili: {escape(str(language or '-'))}\n"
        f"👁 Ko‘rishlar: {shown_views}\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "🍿 Yoqimli tomosha!\n\n"
        f"📢 Kanal: <a href='{CHANNEL_LINK}'>{escape(CHANNEL_USERNAME)}</a>\n"
        f"🤖 Bot: @{escape(bot_username)}\n"
        "━━━━━━━━━━━━━━━━━━"
    )


def movie_choice_keyboard(code: int, user_id: int) -> InlineKeyboardMarkup:
    quality_rows = get_movie_quality_rows(code)
    buttons = []

    for quality_id, quality in quality_rows:
        buttons.append(
            [
                InlineKeyboardButton(
                    f"🎞 {quality}",
                    callback_data=f"quality:{code}:{quality_id}",
                )
            ]
        )

    fav_text = "💔 Sevimlidan olish" if is_favorite(user_id, code) else "⭐ Sevimli"
    buttons.append([InlineKeyboardButton(fav_text, callback_data=f"fav:{code}")])
    buttons.append([InlineKeyboardButton("📢 Kanal", url=CHANNEL_LINK)])
    return InlineKeyboardMarkup(buttons)


async def send_movie(update: Update, context: ContextTypes.DEFAULT_TYPE, code: int):
    movie = get_movie(code)
    if not movie:
        await update.message.reply_text("❌ Bunday kodli kino topilmadi.")
        return

    quality_rows = get_movie_quality_rows(code)
    if not quality_rows and movie[8]:
        # Juda eski yozuv bo'lsa ham foydalanuvchi videosiz qolmaydi.
        add_movie_quality(code, "Original", movie[8])
        quality_rows = get_movie_quality_rows(code)

    if not quality_rows:
        await update.message.reply_text("❌ Bu kino uchun video sifati topilmadi.")
        return

    me = await context.bot.get_me()
    caption = _movie_caption(movie, me.username)
    caption += "\n\n<b>Kerakli sifatni tanlang:</b>"
    keyboard = movie_choice_keyboard(code, update.effective_user.id)
    poster_file_id = movie[7]

    if poster_file_id:
        await update.message.reply_photo(
            photo=poster_file_id,
            caption=caption,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    else:
        await update.message.reply_text(
            caption,
            parse_mode="HTML",
            reply_markup=keyboard,
            disable_web_page_preview=True,
        )


async def show_favorites(update: Update, context: ContextTypes.DEFAULT_TYPE):
    favorites = get_favorites(update.effective_user.id)
    if not favorites:
        await update.message.reply_text("❤️ Sevimlilar ro‘yxatingiz bo‘sh.")
        return

    text = "❤️ <b>Sevimli kinolaringiz:</b>\n\n"
    for code, name, year, genre in favorites:
        text += (
            f"🎬 <b>{escape(str(name))}</b>\n"
            f"📅 {escape(str(year or '-'))} | 🎭 {escape(str(genre or '-'))}\n"
            f"🔑 Kod: <code>{code}</code>\n\n"
        )
    await update.message.reply_text(text, parse_mode="HTML")


async def show_top_movies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    movies = get_top_movies()
    if not movies:
        await update.message.reply_text("❌ Hozircha top kinolar mavjud emas.")
        return

    msg = "🔥 <b>TOP 10 Kinolar</b>\n\n"
    for index, (code, name, year, _genre, views) in enumerate(movies, start=1):
        msg += (
            f"{index}. 🎬 <b>{escape(str(name))}</b>\n"
            f"👁 {views} | 📅 {escape(str(year or '-'))}\n"
            f"🔑 Kod: <code>{code}</code>\n\n"
        )
    await update.message.reply_text(msg, parse_mode="HTML")


async def show_genres(update: Update, context: ContextTypes.DEFAULT_TYPE):
    genres = get_genres()
    if not genres:
        await update.message.reply_text("❌ Janrlar mavjud emas.")
        return

    keyboard = [
        [
            InlineKeyboardButton(
                f"🎭 {genre} ({count})",
                callback_data=f"genre:{genre}",
            )
        ]
        for genre, count in genres
    ]
    await update.message.reply_text(
        "🎭 Janrni tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def show_movies_by_genre(update: Update, context: ContextTypes.DEFAULT_TYPE, genre: str):
    movies = get_movies_by_genre(genre)
    if not movies:
        await update.message.reply_text("❌ Bu janrda kino topilmadi.")
        return

    msg = f"🎭 <b>{escape(genre)}</b>\n\n"
    for code, name, year, _genre_name in movies:
        msg += (
            f"🎬 <b>{escape(str(name))}</b>\n"
            f"📅 {escape(str(year or '-'))}\n"
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
            f"🎬 <b>{escape(str(name))}</b>\n"
            f"📅 {escape(str(year or '-'))} | 🎭 {escape(str(genre or '-'))}\n"
            f"🔑 Kod: <code>{code}</code>\n\n"
        )
    message += "Kerakli kino kodini yuboring."
    await update.message.reply_text(message, parse_mode="HTML")


async def user_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()
    add_user(user.id)

    # Admin xabarlari admin handlerlarida ishlanadi; bir xabar ikki marta bajarilmaydi.
    if user.id == ADMIN_ID:
        return

    if not await check_subscription(context.bot, user.id):
        await update.message.reply_text(
            "🎬 xD KINO BOT\n\n"
            "Botdan foydalanishni davom ettirish uchun rasmiy sahifalarimizga "
            "obuna bo‘ling. So‘ng «✅ Tekshirish» tugmasini bosing.",
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
            "Kino kodini yuboring, so‘ng kerakli video sifatini tanlang.\n"
            "🔍 Kino qidirish — nom yoki kod orqali qidirish.\n"
            "🔥 Top kinolar — eng ko‘p ko‘rilgan kinolar.\n"
            "❤️ Sevimlilar — saqlangan kinolaringiz.\n"
            "🎭 Janrlar — janrlar bo‘yicha kinolar.",
            parse_mode="HTML",
        )
        return

    if user_states.get(user.id) == "search_movie":
        user_states.pop(user.id, None)
        if text.isdigit():
            await send_movie(update, context, int(text))
        else:
            await search_by_name(update, context, text)
        return

    if text.isdigit():
        await send_movie(update, context, int(text))
        return

    await search_by_name(update, context, text)


async def movie_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data or ""
    user_id = query.from_user.id

    if data.startswith("quality:"):
        try:
            _, code_text, quality_id_text = data.split(":", 2)
            code = int(code_text)
            quality_id = int(quality_id_text)
        except ValueError:
            await query.answer("❌ Noto‘g‘ri tugma.", show_alert=True)
            return

        if not await check_subscription(context.bot, user_id):
            await query.answer("❌ Avval kanalga a’zo bo‘ling.", show_alert=True)
            return

        movie = get_movie(code)
        quality_row = get_movie_quality_by_id(code, quality_id)
        if not movie or not quality_row:
            await query.answer("❌ Kino yoki sifat topilmadi.", show_alert=True)
            return

        quality, file_id = quality_row
        await query.answer(f"🎞 {quality} yuborilmoqda...")
        increase_views(code)
        new_views = int(movie[9]) + 1
        me = await context.bot.get_me()
        caption = _movie_caption(movie, me.username, views=new_views)
        caption = f"🎞 Sifat: <b>{escape(str(quality))}</b>\n\n" + caption

        await context.bot.send_video(
            chat_id=query.message.chat_id,
            video=file_id,
            caption=caption,
            parse_mode="HTML",
        )
        return

    if data.startswith("fav:"):
        try:
            code = int(data.split(":", 1)[1])
        except ValueError:
            await query.answer("❌ Noto‘g‘ri tugma.", show_alert=True)
            return

        if not get_movie(code):
            await query.answer("❌ Kino topilmadi.", show_alert=True)
            return

        if is_favorite(user_id, code):
            remove_favorite(user_id, code)
            text = "💔 Sevimlilardan olib tashlandi."
        else:
            add_favorite(user_id, code)
            text = "⭐ Sevimlilarga qo‘shildi."

        await query.answer(text, show_alert=True)
        try:
            await query.edit_message_reply_markup(
                reply_markup=movie_choice_keyboard(code, user_id)
            )
        except Exception:
            pass
        return

    if data.startswith("genre:"):
        genre = data.split(":", 1)[1]
        movies = get_movies_by_genre(genre)
        if not movies:
            await query.answer("❌ Kino topilmadi.", show_alert=True)
            return

        await query.answer()
        text = f"🎭 <b>{escape(genre)}</b>\n\n"
        for code, name, year, _genre_name in movies:
            text += (
                f"🎬 <b>{escape(str(name))}</b>\n"
                f"📅 {escape(str(year or '-'))}\n"
                f"🔑 <code>{code}</code>\n\n"
            )
        await query.message.reply_text(text, parse_mode="HTML")
        return

    if data.startswith("trailer:"):
        # Eski xabarlardagi tugmalar uchun: yangi botda treyler butunlay o'chirilgan.
        await query.answer("🎞 Treyler funksiyasi olib tashlangan.", show_alert=True)
        return

    await query.answer()
