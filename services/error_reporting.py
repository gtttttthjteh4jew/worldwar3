from __future__ import annotations
import traceback
from config import OWNER_ID

async def report_exception(bot, error, *, update=None, source="خطای پس‌زمینه"):
    if not OWNER_ID:
        return
    try:
        user = getattr(update, "effective_user", None) if update else None
        chat = getattr(update, "effective_chat", None) if update else None
        message = getattr(update, "effective_message", None) if update else None
        callback = getattr(update, "callback_query", None) if update else None
        tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        if len(tb) > 3000:
            tb = tb[-3000:]
        text = getattr(message, "text", None) or getattr(message, "caption", None) or "-"
        callback_data = getattr(callback, "data", None) or "-"
        report = (
            f"🚨 {source}\n\n"
            f"👤 کاربر: {getattr(user, 'full_name', None) or getattr(user, 'username', None) or 'نامشخص'}\n"
            f"🆔 شناسه کاربر: {getattr(user, 'id', 'نامشخص')}\n"
            f"💬 شناسه گفت‌وگو: {getattr(chat, 'id', 'نامشخص')}\n"
            f"📝 متن: {str(text)[:500]}\n"
            f"🔘 داده دکمه: {callback_data}\n\n"
            f"❌ {type(error).__name__}: {error}\n\n"
            f"📋 گزارش خطا:\n{tb}"
        )
        await bot.send_message(chat_id=int(OWNER_ID), text=report[:4096])
    except Exception:
        pass
