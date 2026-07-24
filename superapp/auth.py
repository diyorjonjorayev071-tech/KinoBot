from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl


class TelegramAuthError(ValueError):
    pass


@dataclass(frozen=True)
class TelegramUser:
    id: int
    first_name: str = ""
    last_name: str = ""
    username: str = ""
    language_code: str = ""
    photo_url: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "TelegramUser":
        user_id = data.get("id")
        if not isinstance(user_id, int):
            raise TelegramAuthError("Telegram user id noto'g'ri.")
        return cls(
            id=user_id,
            first_name=str(data.get("first_name") or ""),
            last_name=str(data.get("last_name") or ""),
            username=str(data.get("username") or ""),
            language_code=str(data.get("language_code") or ""),
            photo_url=str(data.get("photo_url") or ""),
        )


def validate_init_data(
    init_data: str,
    bot_token: str,
    *,
    max_age_seconds: int = 86400,
    now: int | None = None,
) -> TelegramUser:
    if not init_data:
        raise TelegramAuthError("Telegram initData yuborilmagan.")
    if not bot_token:
        raise TelegramAuthError("BOT_TOKEN serverda sozlanmagan.")

    pairs = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=False))
    received_hash = pairs.pop("hash", "")
    pairs.pop("signature", None)
    if not received_hash:
        raise TelegramAuthError("Telegram hash topilmadi.")

    data_check_string = "\n".join(f"{key}={pairs[key]}" for key in sorted(pairs))
    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise TelegramAuthError("Telegram initData imzosi noto'g'ri.")

    try:
        auth_date = int(pairs.get("auth_date", "0"))
    except ValueError as exc:
        raise TelegramAuthError("Telegram auth_date noto'g'ri.") from exc

    current_time = int(time.time() if now is None else now)
    if auth_date <= 0 or current_time - auth_date > max_age_seconds:
        raise TelegramAuthError("Telegram sessiyasi eskirgan.")
    if auth_date > current_time + 60:
        raise TelegramAuthError("Telegram auth_date kelajak vaqtini ko'rsatmoqda.")

    try:
        user_data = json.loads(pairs.get("user", "{}"))
    except json.JSONDecodeError as exc:
        raise TelegramAuthError("Telegram user ma'lumoti buzilgan.") from exc

    if not isinstance(user_data, dict):
        raise TelegramAuthError("Telegram user ma'lumoti noto'g'ri.")
    return TelegramUser.from_dict(user_data)
