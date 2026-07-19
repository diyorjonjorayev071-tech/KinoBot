from html import escape

from telegram import Update
from telegram.ext import ContextTypes

from config import ADMIN_ID
from database import (
    add_movie_quality,
    delete_movie,
    delete_movie_quality_by_id,
    get_users,
    movie_exists,
    movies_count,
    normalize_quality,
    update_movie,
    update_movie_code,
    users_count,
)
from handlers.admin_ui import (
    admin_edit_keyboard,
    admin_movie_text,
    admin_quality_delete_keyboard,
)
from handlers.movie_add import start_movie_add
from keyboards import admin_keyboard
from states import movie_data, user_states

FIELD_LABELS = {
    "name": "kino nomini",
    "year": "kino yilini",
    "country": "davlatini",
    "genre": "janrini",
    "language": "tilini",
    "imdb": "IMDB reytingini",
}


def _clear_flow(user_id: int) -> None:
    user_states.pop(user_id, None)
    movie_data.pop(user_id, None)


async def send_admin_edit_menu(message, code: int) -> None:
    await message.reply_text(
        admin_movie_text(code),
        parse_mode="HTML",
        reply_markup=admin_edit_keyboard(code),
    )


async def admin_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        return

    user_id = user.id
    text = update.message.text.strip()
    state = user_states.get(user_id, "")

    if text.lower() in {"bekor", "cancel", "/cancel", "❌ bekor qilish"}:
        _clear_flow(user_id)
        await update.message.reply_text(
            "✅ Amal bekor qilindi.",
            reply_markup=admin_keyboard,
        )
        return

    # Admin panel tugmalari avvalgi jarayonni xavfsiz bekor qilib, yangi jarayonni ochadi.
    if text == "➕ Kino qo'shish":
        _clear_flow(user_id)
        await start_movie_add(update, context)
        return

    if text == "✏️ Kino tahrirlash":
        _clear_flow(user_id)
        user_states[user_id] = "edit_movie_code"
        await update.message.reply_text(
            "✏️ Tahrirlanadigan kino kodini yuboring:\n\n"
            "Jarayonni to‘xtatish uchun: <code>bekor</code>",
            parse_mode="HTML",
        )
        return

    if text == "🗑 Kino o'chirish":
        _clear_flow(user_id)
        user_states[user_id] = "delete_movie"
        await update.message.reply_text(
            "🗑 O‘chiriladigan kino kodini yuboring:\n\n"
            "Jarayonni to‘xtatish uchun: <code>bekor</code>",
            parse_mode="HTML",
        )
        return

    if text == "📊 Statistika":
        _clear_flow(user_id)
        await update.message.reply_text(
            "📊 <b>BOT STATISTIKASI</b>\n\n"
            f"👤 Foydalanuvchilar: {users_count()}\n"
            f"🎬 Kinolar: {movies_count()}",
            parse_mode="HTML",
            reply_markup=admin_keyboard,
        )
        return

    if text == "📢 Reklama yuborish":
        _clear_flow(user_id)
        user_states[user_id] = "broadcast"
        await update.message.reply_text(
            "📢 Reklama matnini yuboring.\n\n"
            "Jarayonni to‘xtatish uchun: <code>bekor</code>",
            parse_mode="HTML",
        )
        return

    if text == "⚙️ Sozlamalar":
        _clear_flow(user_id)
        await update.message.reply_text(
            "⚙️ Sozlamalar\n\n"
            "• Kino tahrirlash orqali ma’lumot va sifatlarni boshqaring.\n"
            "• Treyler funksiyasi olib tashlangan.",
            reply_markup=admin_keyboard,
        )
        return

    if state == "edit_movie_code":
        if not text.isdigit():
            await update.message.reply_text("❌ Faqat kino kodi yuboring.")
            return

        code = int(text)
        if not movie_exists(code):
            await update.message.reply_text(
                "❌ Bunday kodli kino topilmadi. Boshqa kod yuboring."
            )
            return

        _clear_flow(user_id)
        await send_admin_edit_menu(update.message, code)
        return

    if state.startswith("edit_field:"):
        try:
            _, code_text, field = state.split(":", 2)
            code = int(code_text)
        except ValueError:
            _clear_flow(user_id)
            await update.message.reply_text("❌ Tahrirlash holati buzilgan.")
            return

        if field not in FIELD_LABELS or not movie_exists(code):
            _clear_flow(user_id)
            await update.message.reply_text("❌ Kino yoki maydon topilmadi.")
            return

        value = "" if text == "-" else text
        changed = update_movie(code, **{field: value})
        _clear_flow(user_id)
        if changed:
            await update.message.reply_text("✅ Ma’lumot yangilandi.")
            await send_admin_edit_menu(update.message, code)
        else:
            await update.message.reply_text("❌ Ma’lumotni yangilab bo‘lmadi.")
        return

    if state.startswith("edit_code:"):
        try:
            old_code = int(state.split(":", 1)[1])
        except ValueError:
            _clear_flow(user_id)
            await update.message.reply_text("❌ Tahrirlash holati buzilgan.")
            return

        if not text.isdigit() or int(text) <= 0:
            await update.message.reply_text("❌ Yangi kod musbat son bo‘lishi kerak.")
            return

        new_code = int(text)
        changed = update_movie_code(old_code, new_code)
        _clear_flow(user_id)
        if not changed:
            await update.message.reply_text(
                "❌ Kodni almashtirib bo‘lmadi. Yangi kod boshqa kinoda band bo‘lishi mumkin."
            )
            await send_admin_edit_menu(update.message, old_code)
            return

        await update.message.reply_text(
            f"✅ Kino kodi <code>{new_code}</code> ga almashtirildi.",
            parse_mode="HTML",
        )
        await send_admin_edit_menu(update.message, new_code)
        return

    if state.startswith("edit_poster:"):
        try:
            code = int(state.split(":", 1)[1])
        except ValueError:
            _clear_flow(user_id)
            await update.message.reply_text("❌ Tahrirlash holati buzilgan.")
            return

        if text.lower() not in {"skip", "o'chir", "ochir", "remove", "-"}:
            await update.message.reply_text(
                "🖼 Yangi poster rasmini yuboring. Posterni o‘chirish uchun: <code>skip</code>",
                parse_mode="HTML",
            )
            return

        update_movie(code, poster_file_id="")
        _clear_flow(user_id)
        await update.message.reply_text("✅ Poster olib tashlandi.")
        await send_admin_edit_menu(update.message, code)
        return

    if state.startswith("edit_quality_name:"):
        try:
            code = int(state.split(":", 1)[1])
            quality = normalize_quality(text)
        except (ValueError, TypeError) as error:
            await update.message.reply_text(f"❌ {escape(str(error))}", parse_mode="HTML")
            return

        if not movie_exists(code):
            _clear_flow(user_id)
            await update.message.reply_text("❌ Kino topilmadi.")
            return

        movie_data[user_id] = {"code": code, "quality": quality}
        user_states[user_id] = f"edit_quality_video:{code}"
        await update.message.reply_text(
            f"🎞 Sifat: <b>{escape(quality)}</b>\n\n"
            "Endi shu sifatdagi kino videosini yuboring:",
            parse_mode="HTML",
        )
        return

    if state == "delete_movie":
        if not text.isdigit():
            await update.message.reply_text("❌ Faqat kino kodi yuboring.")
            return

        code = int(text)
        if not movie_exists(code):
            await update.message.reply_text("❌ Bunday kino mavjud emas.")
            return

        delete_movie(code)
        _clear_flow(user_id)
        await update.message.reply_text(
            f"✅ <code>{code}</code> kodli kino o‘chirildi.",
            parse_mode="HTML",
            reply_markup=admin_keyboard,
        )
        return

    if state == "broadcast":
        users = get_users()
        success = 0
        failed = 0
        await update.message.reply_text("⏳ Reklama yuborish boshlandi...")

        for item in users:
            try:
                await context.bot.copy_message(
                    chat_id=item[0],
                    from_chat_id=update.message.chat_id,
                    message_id=update.message.message_id,
                )
                success += 1
            except Exception:
                failed += 1

        _clear_flow(user_id)
        await update.message.reply_text(
            "✅ Reklama yuborildi!\n\n"
            f"📨 Yetkazildi: {success}\n"
            f"❌ Yetmadi: {failed}",
            reply_markup=admin_keyboard,
        )
        return


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data or ""

    if user_id != ADMIN_ID:
        await query.answer("❌ Bu tugma faqat admin uchun.", show_alert=True)
        return

    if data.startswith("admin_menu:"):
        code = int(data.split(":", 1)[1])
        _clear_flow(user_id)
        await query.answer()
        await query.message.edit_text(
            admin_movie_text(code),
            parse_mode="HTML",
            reply_markup=admin_edit_keyboard(code),
        )
        return

    if data.startswith("admin_field:"):
        try:
            _, code_text, field = data.split(":", 2)
            code = int(code_text)
        except ValueError:
            await query.answer("❌ Noto‘g‘ri tugma.", show_alert=True)
            return

        if field not in FIELD_LABELS or not movie_exists(code):
            await query.answer("❌ Kino yoki bo‘lim topilmadi.", show_alert=True)
            return

        _clear_flow(user_id)
        user_states[user_id] = f"edit_field:{code}:{field}"
        await query.answer()
        await query.message.reply_text(
            f"✏️ Yangi {FIELD_LABELS[field]} yuboring.\n"
            "Maydonni bo‘shatish uchun: <code>-</code>\n"
            "Bekor qilish uchun: <code>bekor</code>",
            parse_mode="HTML",
        )
        return

    if data.startswith("admin_poster:"):
        code = int(data.split(":", 1)[1])
        if not movie_exists(code):
            await query.answer("❌ Kino topilmadi.", show_alert=True)
            return

        _clear_flow(user_id)
        user_states[user_id] = f"edit_poster:{code}"
        await query.answer()
        await query.message.reply_text(
            "🖼 Yangi poster rasmini yuboring.\n"
            "Posterni o‘chirish uchun: <code>skip</code>\n"
            "Bekor qilish uchun: <code>bekor</code>",
            parse_mode="HTML",
        )
        return

    if data.startswith("admin_code:"):
        code = int(data.split(":", 1)[1])
        if not movie_exists(code):
            await query.answer("❌ Kino topilmadi.", show_alert=True)
            return

        _clear_flow(user_id)
        user_states[user_id] = f"edit_code:{code}"
        await query.answer()
        await query.message.reply_text(
            f"🔑 Hozirgi kod: <code>{code}</code>\n\nYangi kodni yuboring:",
            parse_mode="HTML",
        )
        return

    if data.startswith("admin_qadd:"):
        code = int(data.split(":", 1)[1])
        if not movie_exists(code):
            await query.answer("❌ Kino topilmadi.", show_alert=True)
            return

        _clear_flow(user_id)
        user_states[user_id] = f"edit_quality_name:{code}"
        await query.answer()
        await query.message.reply_text(
            "🎞 Qo‘shiladigan sifat nomini yuboring.\n"
            "Masalan: <code>360p</code>, <code>480p</code>, "
            "<code>720p</code> yoki <code>1080p</code>",
            parse_mode="HTML",
        )
        return

    if data.startswith("admin_qdel_menu:"):
        code = int(data.split(":", 1)[1])
        if not movie_exists(code):
            await query.answer("❌ Kino topilmadi.", show_alert=True)
            return

        await query.answer()
        await query.message.edit_text(
            "➖ <b>O‘chiriladigan sifatni tanlang:</b>\n\n"
            "Kino kamida bitta sifat bilan qolishi shart.",
            parse_mode="HTML",
            reply_markup=admin_quality_delete_keyboard(code),
        )
        return

    if data.startswith("admin_qdel:"):
        try:
            _, code_text, quality_id_text = data.split(":", 2)
            code = int(code_text)
            quality_id = int(quality_id_text)
        except ValueError:
            await query.answer("❌ Noto‘g‘ri tugma.", show_alert=True)
            return

        result = delete_movie_quality_by_id(code, quality_id)
        if result == "last_quality":
            await query.answer(
                "❌ Oxirgi sifatni o‘chirib bo‘lmaydi.",
                show_alert=True,
            )
            return
        if result == "not_found":
            await query.answer("❌ Sifat topilmadi.", show_alert=True)
            return

        await query.answer("✅ Sifat o‘chirildi.", show_alert=True)
        await query.message.edit_text(
            admin_movie_text(code),
            parse_mode="HTML",
            reply_markup=admin_edit_keyboard(code),
        )
        return

    if data.startswith("admin_done:"):
        _clear_flow(user_id)
        await query.answer("✅ Tahrirlash tugatildi.")
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        await query.message.reply_text(
            "✅ Admin panelga qaytildi.",
            reply_markup=admin_keyboard,
        )
        return

    await query.answer()


async def admin_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return

    state = user_states.get(user_id, "")
    if not state.startswith("edit_poster:"):
        return

    try:
        code = int(state.split(":", 1)[1])
    except ValueError:
        _clear_flow(user_id)
        await update.message.reply_text("❌ Tahrirlash holati buzilgan.")
        return

    photo = update.message.photo[-1]
    update_movie(code, poster_file_id=photo.file_id)
    _clear_flow(user_id)
    await update.message.reply_text("✅ Poster yangilandi.")
    await send_admin_edit_menu(update.message, code)


async def admin_video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return

    state = user_states.get(user_id, "")
    if not state.startswith("edit_quality_video:"):
        return

    try:
        code = int(state.split(":", 1)[1])
    except ValueError:
        _clear_flow(user_id)
        await update.message.reply_text("❌ Tahrirlash holati buzilgan.")
        return

    data = movie_data.get(user_id, {})
    quality = data.get("quality")
    if not quality or not movie_exists(code):
        _clear_flow(user_id)
        await update.message.reply_text("❌ Kino yoki sifat nomi topilmadi.")
        return

    add_movie_quality(code, quality, update.message.video.file_id)
    _clear_flow(user_id)
    await update.message.reply_text(
        f"✅ <b>{escape(str(quality))}</b> sifati saqlandi.",
        parse_mode="HTML",
    )
    await send_admin_edit_menu(update.message, code)
