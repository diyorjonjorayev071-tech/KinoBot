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


def _movie_request_from_start_args(
    args,
) -> tuple[str, int | None, int | None] | None:
    if not args:
        return None

    payload = str(args[0]).strip()

    if payload == "premium":
        return "premium", None, None

    if not payload.startswith("movie_"):
        return None

    value = payload[len("movie_"):]

    if "_q_" in value:
        code_text, quality_text = value.split("_q_", 1)
        if not code_text.isdigit() or not quality_text.isdigit():
            return None
        return "quality_id", int(code_text), int(quality_text)

    if "_s_" in value:
        code_text, index_text = value.split("_s_", 1)
        if not code_text.isdigit() or not index_text.isdigit():
            return None
        return "quality_index", int(code_text), int(index_text)

    if not value.isdigit():
        return None

    return "movie", int(value), None


# FINAL_START_PAYLOAD_V1



# QUALITY_INDEX_DEEPLINK_V1


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.effective_message
    add_user(user.id)

    if not await check_subscription(context.bot, user.id):
        await message.reply_text(
            "❌ Botdan foydalanish uchun avval kanalga a'zo bo'ling.",
            reply_markup=subscribe_keyboard,
        )
        return

    request = _movie_request_from_start_args(context.args)

    if request is not None:
        request_type, movie_code, option_value = request

        if request_type == "premium":
            await message.reply_text(
                "💎 <b>xD KINO PLUS</b>\n\n"
                "Hozircha haqiqiy to‘lov tizimi ulanmagan. "
                "Tarif ishga tushirilganda shu bot orqali rasmiy ma’lumot beriladi.",
                parse_mode="HTML",
            )
            return

        if request_type == "quality_id":
            await send_movie_quality(
                update,
                context,
                int(movie_code),
                int(option_value),
            )
            return

        if request_type == "quality_index":
            await send_movie_quality_index(
                update,
                context,
                int(movie_code),
                int(option_value),
            )
            return

        if request_type == "movie":
            await send_movie(update, context, int(movie_code))
            return

    if user.id == ADMIN_ID:
        await message.reply_text(
            "👋 Xush kelibsiz, Admin!",
            reply_markup=admin_keyboard,
        )
        return

    await message.reply_text(
        "🎬 xD KINO BOT ga xush kelibsiz!\n\nKino kodini yuboring.",
        reply_markup=user_keyboard,
    )


# FINAL_START_HANDLER_V1



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


# QUALITY_INDEX_DIRECT_SEND_V1
async def send_movie_quality_index(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    code: int,
    quality_index: int,
):
    movie = get_movie(code)
    message = update.effective_message

    if not movie:
        await message.reply_text("❌ Bunday kodli kino topilmadi.")
        return

    quality_rows = get_movie_quality_rows(code)
    if not quality_rows and movie[8]:
        add_movie_quality(code, "Original", movie[8])
        quality_rows = get_movie_quality_rows(code)

    if not quality_rows:
        await message.reply_text("❌ Bu kino uchun video topilmadi.")
        return

    safe_index = max(0, min(int(quality_index), len(quality_rows) - 1))
    quality_id, _quality = quality_rows[safe_index]
    await send_movie_quality(update, context, code, quality_id)


# FINAL_DIRECT_QUALITY_INDEX_V1



# QUALITY_DIRECT_SEND_V1
async def send_movie_quality(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    code: int,
    quality_id: int,
):
    movie = get_movie(code)
    message = update.effective_message

    if not movie:
        await message.reply_text("❌ Bunday kodli kino topilmadi.")
        return

    quality_row = get_movie_quality_by_id(code, quality_id)

    if not quality_row:
        quality_rows = get_movie_quality_rows(code)
        if not quality_rows and movie[8]:
            add_movie_quality(code, "Original", movie[8])
            quality_rows = get_movie_quality_rows(code)

        if not quality_rows:
            await message.reply_text("❌ Bu kino uchun video topilmadi.")
            return

        fallback_id, _fallback_quality = quality_rows[0]
        quality_row = get_movie_quality_by_id(code, fallback_id)

    if not quality_row:
        await message.reply_text("❌ Video fayli topilmadi.")
        return

    quality, file_id = quality_row
    increase_views(code)
    new_views = int(movie[9]) + 1
    me = await context.bot.get_me()
    caption = _movie_caption(movie, me.username, views=new_views)
    caption = f"🎞 Sifat: <b>{escape(str(quality))}</b>\n\n" + caption

    await context.bot.send_video(
        chat_id=update.effective_chat.id,
        video=file_id,
        caption=caption,
        parse_mode="HTML",
    )


# FINAL_DIRECT_QUALITY_V1



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



# ============================================================
# ATOMIC_GENRES_MENU_V2
# ============================================================

def _genre_key(value: str) -> str:
    return (
        str(value or "")
        .replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u02bb", "'")
        .replace("\u02bc", "'")
        .replace("`", "'")
        .strip()
        .casefold()
    )


def _genre_parts(value: str) -> list[str]:
    result = []

    for raw in str(value or "").split(","):
        item = (
            raw
            .replace("\u2019", "'")
            .replace("\u2018", "'")
            .replace("\u02bb", "'")
            .replace("\u02bc", "'")
            .replace("`", "'")
            .strip()
        )

        if item:
            result.append(item)

    return result


def _canonical_genre(value: str) -> str:
    clean = str(value or "").strip()
    key = _genre_key(clean)

    aliases = {
        "animation": "Animatsion",
        "animatsiya": "Animatsion",
        "animatsion": "Animatsion",

        "anime": "Anime",

        "action": "Jangari",
        "jangari": "Jangari",

        "detective": "Detektiv",
        "detektiv": "Detektiv",

        "crime": "Kriminal",
        "kriminal": "Kriminal",

        "horror": "Qo'rqinchli",
        "dahshat": "Qo'rqinchli",
        "qo'rqinchli": "Qo'rqinchli",

        "war": "Harbiy",
        "urush": "Harbiy",
        "harbiy": "Harbiy",

        "thriller": "Triller",
        "triller": "Triller",

        "adventure": "Sarguzasht",
        "sarguzasht": "Sarguzasht",

        "melodrama": "Melodrama",

        "drama": "Drama",

        "comedy": "Komediya",
        "komediya": "Komediya",

        "sport": "Sport",

        "western": "Western",
        "vestern": "Western",

        "fantastika": "Fantastika",

        "fantasy": "Fentezi",
        "fantaziya": "Fentezi",
        "fentezi": "Fentezi",

        "sci-fi": "Ilmiy-fantastika",
        "science fiction": "Ilmiy-fantastika",
        "ilmiy fantastika": "Ilmiy-fantastika",
        "ilmiy-fantastika": "Ilmiy-fantastika",

        "history": "Tarixiy",
        "historical": "Tarixiy",
        "tarixiy": "Tarixiy",

        "biography": "Biografik",
        "biografiya": "Biografik",
        "biografik": "Biografik",

        "hayotiy": "Hayotiy",

        "disaster": "Falokat",
        "falokat": "Falokat",

        "documentary": "Hujjatli",
        "hujjatli": "Hujjatli",

        "romance": "Romantika",
        "romantika": "Romantika",

        "retro": "Retro",

        "music": "Musiqiy",
        "musical": "Musiqiy",
        "musiqiy": "Musiqiy",

        "family": "Oilaviy",
        "oilaviy": "Oilaviy",
    }

    if key in aliases:
        return aliases[key]

    if not clean:
        return ""

    return clean[:1].upper() + clean[1:]


def _genre_emoji(value: str) -> str:
    key = _genre_key(
        _canonical_genre(value)
    )

    icons = {
        "animatsion": "\U0001F3A8",
        "anime": "\U0001F338",
        "jangari": "\u26A1",
        "detektiv": "\U0001F575\uFE0F",
        "kriminal": "\U0001F303",
        "qo'rqinchli": "\U0001F56F\uFE0F",
        "harbiy": "\u2694\uFE0F",
        "triller": "\U0001F311",
        "sarguzasht": "\U0001F9ED",
        "melodrama": "\U0001F339",
        "drama": "\U0001F3AD",
        "komediya": "\U0001F604",
        "sport": "\U0001F3C6",
        "western": "\U0001F920",
        "fantastika": "\U0001F680",
        "fentezi": "\u2728",
        "ilmiy-fantastika": "\U0001FA90",
        "tarixiy": "\U0001F3DB\uFE0F",
        "biografik": "\U0001F464",
        "hayotiy": "\U0001F39E\uFE0F",
        "falokat": "\U0001F32A\uFE0F",
        "hujjatli": "\U0001F4DA",
        "romantika": "\u2764\uFE0F",
        "retro": "\U0001F4FD\uFE0F",
        "musiqiy": "\U0001F3B5",
        "oilaviy": "\U0001F46A",
    }

    return icons.get(
        key,
        "\U0001F3AC",
    )


def _atomic_genres():
    """
    Masalan:
      Animatsion, Oilaviy, Komediya (7)

    ni alohida:
      Animatsion
      Oilaviy
      Komediya

    hisobiga qo'shadi.
    """

    counts = {}
    labels = {}

    for combined_genre, count in get_genres():

        try:
            amount = int(count or 0)
        except (TypeError, ValueError):
            amount = 0

        seen = set()

        for part in _genre_parts(
            combined_genre
        ):

            label = _canonical_genre(
                part
            )

            key = _genre_key(
                label
            )

            if (
                not key
                or key in seen
            ):
                continue

            seen.add(key)

            labels[key] = label

            counts[key] = (
                counts.get(key, 0)
                + amount
            )

    result = [
        (
            labels[key],
            counts[key],
        )
        for key in counts
        if counts[key] > 0
    ]

    # Eng ko'p kinoli janrlar yuqorida
    result.sort(
        key=lambda item: (
            -item[1],
            item[0].casefold(),
        )
    )

    return result


def _movies_by_atomic_genre(
    selected_genre: str,
):
    """
    'Sarguzasht' bosilsa:
      Sarguzasht
      Sarguzasht, Jangari
      Animatsion, Oilaviy, Sarguzasht

    ichidagi barcha kinolarni yig'adi.
    """

    target = _genre_key(
        _canonical_genre(
            selected_genre
        )
    )

    stored_genres = []

    for combined_genre, _count in get_genres():

        atomic_keys = {
            _genre_key(
                _canonical_genre(part)
            )
            for part in _genre_parts(
                combined_genre
            )
        }

        if target in atomic_keys:
            stored_genres.append(
                combined_genre
            )

    if not stored_genres:
        return get_movies_by_genre(
            selected_genre
        )

    result = []
    seen_codes = set()

    for stored_genre in stored_genres:

        rows = get_movies_by_genre(
            stored_genre
        )

        for movie in rows:

            try:
                code_key = int(movie[0])
            except Exception:
                code_key = repr(movie)

            if code_key in seen_codes:
                continue

            seen_codes.add(
                code_key
            )

            result.append(
                movie
            )

    return result


async def show_genres(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    genres = _atomic_genres()

    if not genres:
        await update.message.reply_text(
            "\u274C Janrlar mavjud emas."
        )
        return

    keyboard = []
    row = []

    for genre, count in genres:

        button_text = (
            f"{_genre_emoji(genre)} "
            f"{genre} \u00B7 {count}"
        )

        row.append(
            InlineKeyboardButton(
                button_text,
                callback_data=(
                    f"genre:{genre}"
                ),
            )
        )

        if len(row) == 2:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    await update.message.reply_text(
        "\U0001F3AC <b>Janrlar</b>\n\n"
        "Kerakli janrni tanlang:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            keyboard
        ),
    )


async def show_movies_by_genre(update: Update, context: ContextTypes.DEFAULT_TYPE, genre: str):
    movies = _movies_by_atomic_genre(genre)
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
        movies = _movies_by_atomic_genre(genre)
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
