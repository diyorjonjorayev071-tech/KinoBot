from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from config import ADMIN_ID, CHANNEL_USERNAME
from database import add_movie, normalize_quality
from handlers.admin_ui import admin_edit_keyboard, admin_movie_text
from states import movie_data, user_states


async def start_movie_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return

    movie_data[user_id] = {}
    user_states[user_id] = "add_content_type"
    await update.message.reply_text(
        "📚 <b>Kontent turini tanlang:</b>\n\n"
        "1 — 🎬 Kino\n"
        "2 — 📺 Serial\n"
        "3 — 🧸 Multfilm\n\n"
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

    if state == "add_content_type":
        content_types = {
            "1": "Kino", "kino": "Kino", "🎬 kino": "Kino",
            "2": "Serial", "serial": "Serial", "📺 serial": "Serial",
            "3": "Multfilm", "multfilm": "Multfilm", "🧸 multfilm": "Multfilm",
        }
        content_type = content_types.get(text.lower())
        if not content_type:
            await update.message.reply_text("❌ 1, 2 yoki 3 ni yuboring.")
            return
        movie_data.setdefault(user_id, {})["content_type"] = content_type
        user_states[user_id] = "add_name"
        await update.message.reply_text(f"🎬 {escape(content_type)} nomini yuboring:", parse_mode="HTML")
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
        from database import normalize_genres
        movie_data[user_id]["genre"] = normalize_genres(text)
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
        user_states[user_id] = "add_recommended"
        await update.message.reply_text(
            "⭐ <b>Xususiy tavsiyaga qo‘shilsinmi?</b>\n\n"
            "1 — ✅ Ha\n"
            "2 — ❌ Yo‘q",
            parse_mode="HTML",
        )
        return

    if state == "add_recommended":
        yes = {"1", "ha", "yes", "✅ ha"}
        no = {"2", "yo'q", "yo‘q", "yoq", "no", "❌ yo‘q"}
        value = text.lower()
        if value not in yes | no:
            await update.message.reply_text("❌ 1 (Ha) yoki 2 (Yo‘q) ni yuboring.")
            return
        movie_data[user_id]["is_recommended"] = value in yes
        user_states[user_id] = "add_description"
        await update.message.reply_text(
            "📝 <b>Izoh yoki qisqacha ma’lumot yuboring:</b>\n\n"
            "Izoh kerak bo‘lmasa: <code>skip</code>",
            parse_mode="HTML",
        )
        return

    if state == "add_description":
        movie_data[user_id]["description"] = "" if text.lower() == "skip" else text
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
    required = ["content_type", "name", "year", "country", "genre", "language", "imdb", "is_recommended", "description", "quality"]
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
        content_type=data["content_type"],
        is_recommended=data["is_recommended"],
        description=data.get("description", ""),
    )

    # CHANNEL_POST_V1
    # Kino saqlangandan keyin kanal posti yuboriladi.
    # Kanal posti xatosi asosiy saqlash jarayonini to'xtatmaydi.
    if str(data.get("content_type", "")).strip().lower() == "kino":
        try:
            bot_username = "xDKinoCodeBot"

            channel_caption = (
                "\U0001F3AC <b>xD KINO</b> \U0001F3AC \U0001F37F\n\n"
                f"\U0001F39F\uFE0F Kino kodi: <code>{code}</code>\n\n"
                "\U0001F53A Filmni hoziroq yuqori sifatda o\u2018zbek tilida tomosha qiling \U0001F4CC\n\n"
                f"\U0001F916: @{bot_username}"
            )

            channel_keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "\U0001F37F TOMOSHA QILISH",
                            url=f"https://t.me/{bot_username}?start=movie_{code}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "\U0001F4F2 KINO ILOVA",
                            url=f"https://t.me/{bot_username}?startapp=movie_{code}",
                        )
                    ],
                ]
            )

            await context.bot.send_video(
                chat_id=CHANNEL_USERNAME,
                video=update.message.video.file_id,
                caption=channel_caption,
                parse_mode="HTML",
                reply_markup=channel_keyboard,
            )

        except Exception as exc:
            await update.message.reply_text(
                "\u26A0\uFE0F <b>Kino saqlandi, lekin kanalga post yuborilmadi.</b>\n\n"
                f"<code>{escape(str(exc))}</code>",
                parse_mode="HTML",
            )

    user_states.pop(user_id, None)
    movie_data.pop(user_id, None)

    await update.message.reply_text(
        f"✅ Kino saqlandi!\n\n"
        f"📚 Turi: <b>{escape(str(data['content_type']))}</b>\n"
        f"🎬 Nomi: <b>{escape(str(data['name']))}</b>\n"
        f"⭐ Xususiy tavsiya: <b>{'Ha' if data['is_recommended'] else 'Yo‘q'}</b>\n"
        f"📝 Izoh: <b>{escape(str(data.get('description') or 'Yo‘q'))}</b>\n"
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
