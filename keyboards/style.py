"""Subtle Telegram button styling for the bot UI.

Keeps most buttons neutral and applies only a few semantic colors:
- success: confirm/build/enable/receive
- danger: delete/ban/remove/disable
- primary: main navigation/settings/selection
"""

from telegram import InlineKeyboardButton as _InlineKeyboardButton
import hashlib
import base64
import zlib

# Telegram limits callback_data to 1-64 UTF-8 bytes.  Long dynamic callback
# payloads are replaced with a compact in-process token; callbacks.py resolves
# the token before dispatch.
_LONG_CALLBACKS: dict[str, str] = {}

def resolve_callback_data(data):
    raw = str(data)
    cached = _LONG_CALLBACKS.get(raw)
    if cached is not None:
        return cached
    if raw.startswith("z:"):
        try:
            packed = base64.urlsafe_b64decode(raw[2:] + "=" * (-len(raw[2:]) % 4))
            return zlib.decompress(packed).decode("utf-8")
        except Exception:
            return data
    return data

def _safe_callback_data(value):
    if value is None:
        return None
    raw = str(value)
    if len(raw.encode("utf-8")) <= 64:
        return value
    # Prefer a restart-safe compressed payload. This avoids the old in-memory-only
    # token for almost all long callbacks and keeps old callbacks compatible.
    try:
        packed = base64.urlsafe_b64encode(zlib.compress(raw.encode("utf-8"), 9)).decode("ascii").rstrip("=")
        token = "z:" + packed
        if len(token.encode("utf-8")) <= 64:
            return token
    except Exception:
        pass
    token = "cb:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
    _LONG_CALLBACKS[token] = raw
    return token


def _pick_style(text: str, callback_data=None):
    t = (text or "").strip().lower()
    c = str(callback_data or "").lower()

    # Back buttons are always red across the entire bot.
    if any(x in t for x in ("برگشت", "بازگشت")):
        return "danger"
    # Cancel/refresh stay neutral unless an explicit style is supplied.
    if any(x in t for x in ("لغو", "رفرش")):
        return None

    # Destructive actions: red, but not every button containing a related word.
    if any(x in t for x in ("حذف", "بن ", "بن‌", "رفع بن", "غیرفعال", "پاکسازی", "کاهش موجودی", "برداشتن")):
        return "danger"
    if any(x in c for x in (":delete", ":ban", "remove", "clear", "disable")):
        return "danger"

    # Positive actions: green.
    if any(x in t for x in ("تأیید", "تایید", "ساخت", "ارتقا", "فعال", "دریافت", "افزایش", "اضافه", "ثبت", "انتخاب")):
        return "success"
    if any(x in c for x in ("confirm", "build", "upgrade", "enable", "receive", "add")):
        return "success"

    # Main navigation / neutral selection: blue, sparingly.
    if any(x in t for x in ("مدیریت", "تنظیمات", "آمار", "اطلاعات", "لیست", "جستجو", "تبادل", "اقتصاد", "معدن", "مرکز فرماندهی", "کشور")):
        return "primary"
    if any(x in c for x in ("settings", "stats", "admin", "owner", "list", "search", "exchange", "country", "mine", "command")):
        return "primary"

    return None


def styled_button(*args, **kwargs):
    """Drop-in replacement for InlineKeyboardButton with subtle auto styling."""
    if "callback_data" in kwargs:
        kwargs["callback_data"] = _safe_callback_data(kwargs.get("callback_data"))
    elif len(args) > 0:
        # InlineKeyboardButton accepts callback_data as a keyword in all current
        # PTB versions used by this project; positional handling is intentionally
        # left untouched.
        pass
    text = kwargs.get("text") if "text" in kwargs else (args[0] if args else "")
    callback_data = kwargs.get("callback_data")
    # Explicit styles must not override the global red-back rule.
    if any(x in str(text or "").strip().lower() for x in ("برگشت", "بازگشت")):
        kwargs["style"] = "danger"
    elif "style" not in kwargs:
        style = _pick_style(text, callback_data)
        if style:
            kwargs["style"] = style
    return _InlineKeyboardButton(*args, **kwargs)
