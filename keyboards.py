from telegram import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

# ==========================
# ADMIN MENU
# ==========================

admin_keyboard = ReplyKeyboardMarkup(
    [
        [KeyboardButton("➕ Kino qo'shish")],
        [KeyboardButton("✏️ Kino tahrirlash"), KeyboardButton("🗑 Kino o'chirish")],
        [KeyboardButton("📊 Statistika"), KeyboardButton("📢 Reklama yuborish")],
        [KeyboardButton("⚙️ Sozlamalar")],
    ],
    resize_keyboard=True,
)

# ==========================
# USER MENU
# ==========================

user_keyboard = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🔍 Kino qidirish"), KeyboardButton("🔥 Top kinolar")],
        [KeyboardButton("❤️ Sevimlilar"), KeyboardButton("🎭 Janrlar")],
        [KeyboardButton("📢 Kanal"), KeyboardButton("ℹ️ Yordam")],
    ],
    resize_keyboard=True,
)

# ==========================
# SUBSCRIBE
# ==========================

subscribe_keyboard = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(
                "📢 Telegram kanal",
                url="https://t.me/xDKinoCode",
            )
        ],
        [
            InlineKeyboardButton(
                "📷 Instagram",
                url="https://instagram.com/USERNAME"
            )
        ],
        [
            InlineKeyboardButton(
                "✅ Tekshirish",
                callback_data="check_sub",
            )
        ],
    ]
)