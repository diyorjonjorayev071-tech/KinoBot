from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from config import CHANNEL_LINK, INSTAGRAM_LINK

admin_keyboard = ReplyKeyboardMarkup(
    [
        [KeyboardButton("➕ Kino qo'shish")],
        [KeyboardButton("✏️ Kino tahrirlash"), KeyboardButton("🗑 Kino o'chirish")],
        [KeyboardButton("📊 Statistika"), KeyboardButton("📢 Reklama yuborish")],
        [KeyboardButton("⚙️ Sozlamalar")],
    ],
    resize_keyboard=True,
)

user_keyboard = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🔍 Kino qidirish"), KeyboardButton("🔥 Top kinolar")],
        [KeyboardButton("❤️ Sevimlilar"), KeyboardButton("🎭 Janrlar")],
        [KeyboardButton("📢 Kanal"), KeyboardButton("ℹ️ Yordam")],
    ],
    resize_keyboard=True,
)

subscribe_keyboard = InlineKeyboardMarkup(
    [
        [InlineKeyboardButton("📢 Telegram kanal", url=CHANNEL_LINK)],
        [InlineKeyboardButton("📸 Instagram sahifasi", url=INSTAGRAM_LINK)],
        [InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub")],
    ]
)
