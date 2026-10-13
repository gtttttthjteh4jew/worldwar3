import logging
import traceback
import asyncio
import time
from collections import deque
from services.anti_spam import _user_state

from telegram import Update, Bot, InlineKeyboardMarkup, MenuButtonCommands, InlineKeyboardButton
from telegram.error import (
    BadRequest, Forbidden, RetryAfter, TimedOut, NetworkError, TelegramError,
)

# Telegram Bot API button styles (blue/green/red) are supported by python-telegram-bot 22.8.
# Apply them centrally so every existing InlineKeyboardButton gets the same subtle visual language.
import telegram as _telegram
from keyboards.style import styled_button as _styled_button
_telegram.InlineKeyboardButton = _styled_button

from telegram import KeyboardButton as _KeyboardButtonOriginal
def _styled_keyboard_button(*args, **kwargs):
    text = kwargs.get("text") if "text" in kwargs else (args[0] if args else "")
    if any(x in str(text or "").strip().lower() for x in ("برگشت", "بازگشت")):
        kwargs["style"] = "danger"
    return _KeyboardButtonOriginal(*args, **kwargs)
_telegram.KeyboardButton = _styled_keyboard_button
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
    ChatMemberHandler,
)

from config import BOT_TOKEN, OWNER_ID, PAYMENT_WEB_HOST, PAYMENT_WEB_PORT
from database.db import init_db, SessionLocal
from services.command_scopes import sync_all_command_scopes
from handlers.callbacks import callbacks, resume_pending_broadcasts
from handlers.messages import group_message, private_message, command_key, is_text_command
from handlers.start import start
from handlers.admin import admin_command, owner_command
from handlers.leaderboards import group_leaderboard, global_leaderboard, continents_leaderboard
from handlers.contact import contact_message
from services.panel_security import get_panel_owner, register_panel
from enigma.scheduler import enigma_scheduler
from services.golden_scheduler import golden_scheduler
from services.backup import backup_worker
from services.missile_flights import missile_flight_worker
from services.social_rewards import social_reward_worker, auto_register_optional_membership, auto_track_mandatory_membership
from services.bank_loan_reminders import bank_loan_reminder_worker
from services.bank_maintenance import bank_maintenance_worker
from services.error_reporting import report_exception
from services.group_status import set_group_status
from services.anti_spam import allow_user_request, remaining_user_limit, allow_group_message, group_remaining_seconds, should_send_group_warning, user_warning_sent, mark_user_warning_sent
from services.social_links import get_active_social_items, public_chat_target, social_item_button_url
from services.admin import ban_expiry_worker
from handlers.wallet import wallet_callbacks, wallet_precheckout, wallet_successful_payment
from services.payment_web import start_payment_callback_server, stop_payment_callback_server
from services.owner_persistence import load_into_user_data, save_owner_state



# ---------------------------------------------------------------------------
# Telegram API safety layer
# ---------------------------------------------------------------------------
# Telegram documents approximate limits rather than a single universal quota:
# ~1 msg/s per chat, ~20 msg/min in groups, and ~30 msg/s for bulk broadcasts
# unless paid broadcasts are enabled.  We deliberately stay slightly below
# those limits and also honor server-provided RetryAfter values.
class _TelegramRateLimiter:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._global = deque()
        self._chat_next = {}
        self._group_next = {}

    async def wait(self, chat_id=None, *, paid=False):
        cid = None
        try:
            cid = int(chat_id) if chat_id is not None else None
        except (TypeError, ValueError):
            cid = None
        is_group = cid is not None and cid < 0
        global_interval = 0.0011 if paid else (1.0 / 30.0)
        chat_interval = 3.05 if is_group else 1.05
        async with self._lock:
            while True:
                now = time.monotonic()
                # Global bulk limit: keep a sliding one-second window.
                while self._global and now - self._global[0] >= 1.0:
                    self._global.popleft()
                delay = 0.0
                if self._global:
                    delay = max(delay, global_interval - (now - self._global[-1]))
                if cid is not None:
                    delay = max(delay, self._chat_next.get(cid, 0.0) - now)
                if delay <= 0:
                    now = time.monotonic()
                    self._global.append(now)
                    if cid is not None:
                        self._chat_next[cid] = now + chat_interval
                    return
                await asyncio.sleep(delay)

_api_limiter = _TelegramRateLimiter()
_MAX_API_RETRIES = 6

async def _report_api_issue(bot, error, method, chat_id=None):
    try:
        text=f"⚠️ <b>Telegram API error</b>\n\n🔧 متد: <code>{method}</code>\n💬 Chat ID: <code>{chat_id}</code>\n❌ {type(error).__name__}: {error}"
        await _ORIG_SEND_MESSAGE(bot, chat_id=int(OWNER_ID), text=text, parse_mode="HTML")
    except Exception:
        pass

async def _api_call_safe(orig, self, *args, **kwargs):
    chat_id = kwargs.get("chat_id") if "chat_id" in kwargs else (args[0] if args else None)
    paid = bool(kwargs.get("allow_paid_broadcast", False))
    for attempt in range(_MAX_API_RETRIES):
        await _api_limiter.wait(chat_id, paid=paid)
        try:
            return await orig(self, *args, **kwargs)
        except RetryAfter as exc:
            wait_for = max(0.5, float(getattr(exc, "retry_after", 1)))
            logging.getLogger("worldwar3_bot").warning(
                "Telegram rate limit hit for %s; retrying after %.2fs (attempt %d/%d)",
                getattr(orig, "__name__", "api_method"), wait_for, attempt + 1, _MAX_API_RETRIES
            )
            await _report_api_issue(self, exc, getattr(orig,"__name__","api_method"), chat_id)
            await asyncio.sleep(wait_for + 0.05)
        except (TimedOut, NetworkError) as exc:
            # Transient HTTP/network failures are retried with backoff.
            wait_for = min(8.0, 1.0 * (2 ** attempt))
            logging.getLogger("worldwar3_bot").warning(
                "Transient Telegram error in %s: %s; retrying in %.1fs",
                getattr(orig, "__name__", "api_method"), exc, wait_for
            )
            await asyncio.sleep(wait_for)
        except (Forbidden, BadRequest) as exc:
            # These are destination/permission/content errors, not process
            # crashes. A user who never opened the bot is an expected
            # copy_message failure and should only count as a failed recipient.
            method_name = getattr(orig, "__name__", "api_method")
            logging.getLogger("worldwar3_bot").warning(
                "Telegram rejected %s: %s", method_name, exc
            )
            if method_name == "copy_message" and isinstance(exc, Forbidden) and "can't initiate conversation" in str(exc):
                return None
            await _report_api_issue(self, exc, method_name, chat_id)
            return None
        except TelegramError as exc:
            logging.getLogger("worldwar3_bot").warning(
                "Telegram API error in %s: %s", getattr(orig, "__name__", "api_method"), exc
            )
            await _report_api_issue(self, exc, getattr(orig,"__name__","api_method"), chat_id)
            return None
    return None

# ثبت خودکار مالک پیام‌های دارای Inline Keyboard.
_ORIG_SEND_MESSAGE = Bot.send_message
_ORIG_SEND_DOCUMENT = Bot.send_document
_ORIG_SEND_PHOTO = Bot.send_photo
_ORIG_SEND_VIDEO = Bot.send_video
_ORIG_SEND_AUDIO = Bot.send_audio
_ORIG_SEND_VOICE = Bot.send_voice
_ORIG_SEND_ANIMATION = Bot.send_animation
_ORIG_SEND_STICKER = Bot.send_sticker
_ORIG_SEND_MEDIA_GROUP = Bot.send_media_group
_ORIG_COPY_MESSAGE = Bot.copy_message
_ORIG_FORWARD_MESSAGE = Bot.forward_message
_ORIG_EDIT_MESSAGE_TEXT = Bot.edit_message_text
_ORIG_EDIT_REPLY_MARKUP = Bot.edit_message_reply_markup

def _plain_text_for_fallback(text: str) -> str:
    # When a very long formatted message has to be split, removing formatting
    # is safer than cutting an HTML/Markdown tag in half and creating a 400.
    import re
    text = re.sub(r"<[^>]+>", "", str(text))
    text = re.sub(r"[*_`~]", "", text)
    return text

def _split_telegram_text(text: str, limit: int = 4096):
    text = str(text)
    if len(text) <= limit:
        return [text]
    chunks=[]
    while text:
        part=text[:limit]
        cut=part.rfind("\n")
        if cut < max(1, limit//2):
            cut=limit
        chunks.append(part[:cut])
        text=text[cut:].lstrip("\n")
    return chunks

def _safe_caption_kwargs(kwargs):
    caption = kwargs.get("caption")
    if caption is None or len(str(caption)) <= 1024:
        return kwargs, None
    extra = _plain_text_for_fallback(str(caption))[1024:]
    new_kwargs=dict(kwargs)
    new_kwargs["caption"]=_plain_text_for_fallback(str(caption))[:1024]
    new_kwargs.pop("parse_mode", None)
    new_kwargs.pop("caption_entities", None)
    return new_kwargs, extra

async def _send_message_owned(self, *args, **kwargs):
    chat_id = kwargs.get("chat_id") if "chat_id" in kwargs else (args[0] if args else None)
    text_value = kwargs.get("text") if "text" in kwargs else (args[1] if len(args) > 1 else None)
    if isinstance(text_value, str) and len(text_value) > 4096:
        # Telegram measures the final text after entity parsing.  For an
        # oversized payload we send safe plain-text chunks instead of letting
        # a 400 Bad Request escape into the update loop.
        chunks = _split_telegram_text(_plain_text_for_fallback(text_value), 4096)
        first = None
        for index, chunk in enumerate(chunks):
            kw=dict(kwargs)
            kw["text"]=chunk
            kw.pop("parse_mode", None)
            kw.pop("entities", None)
            # An inline keyboard belongs to the logical message, not every chunk.
            if index > 0:
                kw.pop("reply_markup", None)
            sent = await _send_message_owned(self, *args[:1], **kw) if args else await _send_message_owned(self, **kw)
            if first is None:
                first=sent
        return first
    if chat_id is not None:
        try:
            cid = int(chat_id)
            if cid < 0 and not allow_group_message(cid):
                # One system warning per blocked window; ordinary group messages stay blocked.
                if should_send_group_warning(cid):
                    remaining = group_remaining_seconds(cid)
                    warning = await _ORIG_SEND_MESSAGE(
                        self, chat_id=cid,
                        text=("⚠️ <b>محدودیت ارسال ربات در این گروه</b>\n\n"
                              "ربات در این بازه به سقف مجاز ارسال پیام رسیده است.\n"
                              "ارسال پیام‌های عادی تا شروع بازهٔ بعدی متوقف شده است.\n\n"
                              "زمان باقی‌مانده را از دکمه زیر مشاهده کنید."),
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
                            "⏱ مشاهده زمان باقی‌مانده", callback_data="group:anti_status")]])
                    )
                    # هشدار پس از پایان بازه حذف و سپس فعال‌شدن مجدد ربات اعلام می‌شود.
                    async def _release_group_warning():
                        import asyncio
                        await asyncio.sleep(max(1, group_remaining_seconds(cid)))
                        try:
                            await self.delete_message(chat_id=cid, message_id=warning.message_id)
                        except Exception:
                            pass
                        try:
                            await _ORIG_SEND_MESSAGE(self, chat_id=cid,
                                text="✅ <b>ربات مجدداً فعال شد و به کار خود ادامه می‌دهد.</b>", parse_mode="HTML")
                        except Exception:
                            pass
                    import asyncio
                    asyncio.create_task(_release_group_warning())
                    return warning
                return None
        except (TypeError, ValueError):
            pass
    result = await _api_call_safe(_ORIG_SEND_MESSAGE, self, *args, **kwargs)
    if result is None:
        return None
    owner = get_panel_owner()
    if owner and isinstance(kwargs.get("reply_markup"), InlineKeyboardMarkup):
        register_panel(result.chat_id, result.message_id, owner)
    return result

async def _edit_message_text_owned(self, *args, **kwargs):
    try:
        result = await _ORIG_EDIT_MESSAGE_TEXT(self, *args, **kwargs)
    except BadRequest as exc:
        if "Message is not modified" in str(exc):
            return None
        raise
    owner = get_panel_owner()
    if owner:
        chat_id = kwargs.get("chat_id")
        message_id = kwargs.get("message_id")
        if chat_id is not None and message_id is not None:
            register_panel(chat_id, message_id, owner)
    return result

async def _edit_reply_markup_owned(self, *args, **kwargs):
    try:
        result = await _ORIG_EDIT_REPLY_MARKUP(self, *args, **kwargs)
    except BadRequest as exc:
        if "Message is not modified" in str(exc):
            return None
        raise
    owner = get_panel_owner()
    if owner:
        chat_id = kwargs.get("chat_id")
        message_id = kwargs.get("message_id")
        if chat_id is not None and message_id is not None:
            register_panel(chat_id, message_id, owner)
    return result

Bot.send_message = _send_message_owned
async def _media_send_owned(orig, self, *args, **kwargs):
    chat_id = kwargs.get("chat_id") if "chat_id" in kwargs else (args[0] if args else None)
    try:
        cid=int(chat_id)
        if cid < 0 and not allow_group_message(cid):
            return None
    except (TypeError,ValueError):
        pass
    kwargs, extra_caption = _safe_caption_kwargs(kwargs)
    result=await _api_call_safe(orig,self,*args,**kwargs)
    if result is None:
        return None
    if extra_caption:
        try:
            await _send_message_owned(self, chat_id=chat_id, text=extra_caption)
        except Exception:
            pass
    owner=get_panel_owner()
    if owner and isinstance(kwargs.get("reply_markup"), InlineKeyboardMarkup):
        register_panel(result.chat_id,result.message_id,owner)
    return result

Bot.send_document = lambda self,*a,**kw: _media_send_owned(_ORIG_SEND_DOCUMENT,self,*a,**kw)
Bot.send_photo = lambda self,*a,**kw: _media_send_owned(_ORIG_SEND_PHOTO,self,*a,**kw)
Bot.send_video = lambda self,*a,**kw: _media_send_owned(_ORIG_SEND_VIDEO,self,*a,**kw)
Bot.send_audio = lambda self,*a,**kw: _media_send_owned(_ORIG_SEND_AUDIO,self,*a,**kw)
Bot.send_voice = lambda self,*a,**kw: _media_send_owned(_ORIG_SEND_VOICE,self,*a,**kw)
Bot.send_animation = lambda self,*a,**kw: _media_send_owned(_ORIG_SEND_ANIMATION,self,*a,**kw)
Bot.send_sticker = lambda self,*a,**kw: _media_send_owned(_ORIG_SEND_STICKER,self,*a,**kw)

async def _media_group_owned(self, *args, **kwargs):
    result = await _api_call_safe(_ORIG_SEND_MEDIA_GROUP, self, *args, **kwargs)
    return result

async def _copy_message_safe(self, *args, **kwargs):
    return await _api_call_safe(_ORIG_COPY_MESSAGE, self, *args, **kwargs)

async def _forward_message_safe(self, *args, **kwargs):
    return await _api_call_safe(_ORIG_FORWARD_MESSAGE, self, *args, **kwargs)

Bot.send_media_group = _media_group_owned
Bot.copy_message = _copy_message_safe
Bot.forward_message = _forward_message_safe
Bot.edit_message_text = _edit_message_text_owned
Bot.edit_message_reply_markup = _edit_reply_markup_owned

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.WARNING,
)

# لاگ‌های تکراری ارتباط با Telegram/HTTP را مخفی می‌کنیم.
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("httpcore").setLevel(logging.CRITICAL)
logging.getLogger("telegram").setLevel(logging.CRITICAL)
logging.getLogger("telegram.ext").setLevel(logging.CRITICAL)


async def post_init(app):
    # منوی داخلی خود تلگرام برای دستورات فعال باشد؛ کنترل باز/بسته شدن آن
    # توسط خود برنامه تلگرام انجام می‌شود و دکمه سفارشی برای آن ساخته نمی‌شود.
    await app.bot.set_chat_menu_button(menu_button=MenuButtonCommands())

    # دستورات بر اساس نقش کاربر تنظیم می‌شوند:
    # کاربر عادی: فقط /start | Admin: /start + /admin | Owner: هر سه
    await sync_all_command_scopes(app.bot)
    # Telegram native Commands menu: keep it enabled after per-chat scopes are synced.
    await app.bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    # انیگما scheduler is independent from normal game mechanics.
    # post_init runs before Application.start(); use asyncio.create_task to avoid PTB
    # warning about create_task() calls made before the application is running.
    # Tasks are registered on the Application so shutdown can cancel and await them cleanly.
    # Start the local HTTP callback endpoint used by ZarinPal. Owner configures the public callback URL.
    try:
        with SessionLocal() as session:
            from services.wallet import ensure_wallet_defaults
            from services.crypto_gateway import ensure_crypto_gateway_defaults
            ensure_wallet_defaults(session)
            ensure_crypto_gateway_defaults(session)
            session.commit()
            # Host/port are deployment settings, never Owner/business settings.
            host = PAYMENT_WEB_HOST
            port = PAYMENT_WEB_PORT
        loop = asyncio.get_running_loop()
        server, thread = start_payment_callback_server(loop, host, port, app)
        app.bot_data["wallet_payment_server"] = server
        app.bot_data["wallet_payment_server_thread"] = thread
    except Exception as exc:
        logging.getLogger("worldwar3_bot").warning("Wallet payment callback server was not started: %s", exc)

    app.bot_data["background_tasks"] = [
        app.create_task(enigma_scheduler(app), update=None, name="enigma_scheduler"),
        app.create_task(golden_scheduler(app), update=None, name="golden_scheduler"),
        app.create_task(ban_expiry_worker(app), update=None, name="ban_expiry_worker"),
        app.create_task(backup_worker(app), update=None, name="backup_worker"),
        app.create_task(social_reward_worker(app), update=None, name="social_reward_worker"),
        app.create_task(missile_flight_worker(app), update=None, name="missile_flight_worker"),
        app.create_task(resume_pending_broadcasts(app), update=None, name="resume_pending_broadcasts"),
        app.create_task(bank_loan_reminder_worker(app), update=None, name="bank_loan_reminder_worker"),
        app.create_task(bank_maintenance_worker(app), update=None, name="bank_maintenance_worker"),
        app.create_task(__import__("services.construction_maintenance", fromlist=["construction_maintenance_worker"]).construction_maintenance_worker(app), update=None, name="construction_maintenance_worker"),
        app.create_task(__import__("services.wallet", fromlist=["wallet_expiry_worker"]).wallet_expiry_worker(app), update=None, name="wallet_expiry_worker"),
        app.create_task(__import__("services.crypto_gateway", fromlist=["crypto_invoice_poll_worker"]).crypto_invoice_poll_worker(app), update=None, name="crypto_invoice_poll_worker"),
    ]


async def post_shutdown(app):
    # Never leave infinite background workers pending when the event loop closes.
    tasks = list(app.bot_data.get("background_tasks", []))
    for task in tasks:
        if not task.done():
            task.cancel()
    if tasks:
        import asyncio
        await asyncio.gather(*tasks, return_exceptions=True)
    server = app.bot_data.pop("wallet_payment_server", None)
    app.bot_data.pop("wallet_payment_server_thread", None)
    if server is not None:
        try:
            await asyncio.to_thread(stop_payment_callback_server, server)
        except Exception:
            pass
    app.bot_data.pop("background_tasks", None)


async def _anti_spam_user(update, context) -> bool:
    user = getattr(update, "effective_user", None)
    if not user or allow_user_request(int(user.id)):
        return True
    seconds = remaining_user_limit(int(user.id))
    query = getattr(update, "callback_query", None)
    if query:
        # در زمان محدودیت، کلیک‌های ربات نباید پیام/هشدار جدید ایجاد کنند.
        return False
    message = getattr(update, "effective_message", None)
    if message is not None and (getattr(message, "text", "") or "").strip().startswith("/"):
        # دستورات اسلشی نیز در زمان محدودیت بدون پاسخ رد می‌شوند.
        return False
    else:
        # برای هر دورهٔ محدودیت فقط یک پیام هشدار خصوصی ارسال می‌شود.
        # پیام‌های بعدی کاربر در زمان محدودیت هیچ پیام خصوصی جدیدی ایجاد نمی‌کنند.
        if user_warning_sent(int(user.id)):
            return False
        # قبل از await یک علامت موقت ثبت می‌کنیم تا چند update هم‌زمان نتوانند
        # دو هشدار خصوصی ایجاد کنند.
        mark_user_warning_sent(int(user.id))
        try:
            warning = await context.bot.send_message(
                chat_id=int(user.id),
                text=("⚠️ <b>محدودیت موقت</b>\n\n"
                      "به دلیل ارسال درخواست‌های زیاد، استفاده از ربات موقتاً متوقف شد.\n\n"
                      "برای مشاهده زمان باقی‌مانده، دکمه زیر را بزنید."),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
                    "⏱ مشاهده زمان باقی‌مانده", callback_data="anti:status")]])
            )
            mark_user_warning_sent(int(user.id), warning.message_id)
            async def _remove_and_restore():
                import asyncio
                await asyncio.sleep(max(1, seconds))
                try:
                    await context.bot.delete_message(chat_id=warning.chat_id, message_id=warning.message_id)
                except Exception:
                    pass
                # پایان دوره: علامت هشدار پاک می‌شود تا در محدودیت بعدی یک هشدار جدید مجاز باشد.
                try:
                    _user_state(int(user.id)).warning_message_id = None
                except Exception:
                    pass
                try:
                    await context.bot.send_message(
                        chat_id=int(user.id),
                        text="✅ <b>محدودیت شما برداشته شد.</b>\n\nاکنون می‌توانید دوباره از ربات استفاده کنید.",
                        parse_mode="HTML",
                    )
                except Exception:
                    pass
            context.application.create_task(_remove_and_restore())
        except Exception:
            # اگر ارسال هشدار شکست خورد، اجازه بده update بعدی دوباره تلاش کند.
            try:
                _user_state(int(user.id)).warning_message_id = None
            except Exception:
                pass
    return False


async def _group_anti_spam_status(update, context):
    query = getattr(update, "callback_query", None)
    if query is None or getattr(update, "effective_chat", None) is None:
        return
    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        await query.answer("این دکمه فقط در گروه قابل استفاده است.", show_alert=True)
        return
    seconds = group_remaining_seconds(int(chat.id))
    try:
        if seconds > 0:
            await query.answer(f"⏱ {seconds} ثانیه تا شروع بازهٔ بعدی باقی مانده است.", show_alert=True)
        else:
            await query.answer("✅ بازهٔ جدید شروع شده است.", show_alert=True)
    except BadRequest as exc:
        # CallbackQuery ممکن است به‌علت تأخیر شبکه/کلاینت منقضی شده باشد؛
        # این خطای تلگرام نباید به‌عنوان خطای پردازش ربات گزارش شود.
        if "Query is too old" in str(exc) or "query id is invalid" in str(exc).lower():
            return
        raise


async def _anti_spam_status(update, context):
    query = getattr(update, "callback_query", None)
    user = getattr(update, "effective_user", None)
    if query is None or user is None:
        return
    seconds = remaining_user_limit(int(user.id))
    if seconds > 0:
        try:
            await query.answer(f"⏱ {seconds} ثانیه باقی مانده است.", show_alert=True)
        except Exception:
            pass
    else:
        try:
            await query.answer("✅ محدودیت به پایان رسیده است.", show_alert=True)
        except Exception:
            pass


def _has_waiting_state(context) -> bool:
    data = getattr(context, "user_data", {}) or {}
    waiting_keys = (
        "economy_pending", "balance_pending", "country_edit_waiting", "country_edit_name",
        "self_country_edit", "self_country_edit_name", "country_edit", "pending_exchange",
        "exchange_rate_pending", "admin_pending", "swap_pending", "missile_pending",
        "missile_operational_pending", "exchange_text_pending", "exchange_text_draft",
        "missile_draft", "enigma_pending", "security_pending", "social_pending", "golden_pending", "admin_message_pending", "admin_leadership_pending", "wallet_state", "wallet_owner_state",
    )
    return any(data.get(k) for k in waiting_keys)


def _is_bot_usage_update(update, context) -> bool:
    # Callbackها همیشه تعامل مستقیم با ربات هستند.
    if getattr(update, "callback_query", None) is not None:
        return True
    message = getattr(update, "effective_message", None)
    if message is None:
        return False
    text = (getattr(message, "text", None) or "").strip()
    if not text:
        return False
    if text.startswith("/"):
        return True
    if _has_waiting_state(context):
        # هر ورودی در یک مرحلهٔ فعالِ دریافت اطلاعات، درخواست ربات محسوب می‌شود.
        return True
    chat = getattr(update, "effective_chat", None)
    chat_type = getattr(chat, "type", None)
    normalized = command_key(text)
    if chat_type == "private":
        return is_text_command(text)
    if chat_type in ("group", "supergroup"):
        # در گروه فقط پیام‌هایی که واقعاً توسط منطق ربات مصرف می‌شوند شمارش شوند.
        return (normalized in {command_key("کشور"), command_key("شروع بازی"), command_key("شروعبازی")}
                or __import__("re").match(r"^\s*(خرید|فروش)\s+.+$", text) is not None
                or __import__("re").match(r"^\s*شلیک\s+.+$", text, flags=__import__("re").IGNORECASE) is not None)
    return False


async def _mandatory_missing_for_user(bot, user_id: int):
    missing=[]
    with SessionLocal() as session:
        for item in get_active_social_items(session, "mandatory_ad"):
            if not str(item.get("url") or "").strip():
                continue
            target=item.get("chat_id") or public_chat_target(item.get("url"))
            joined=False
            if target:
                try:
                    member=await bot.get_chat_member(target, int(user_id))
                    status=getattr(member,"status","")
                    joined=status not in {"left","kicked","restricted"} or bool(getattr(member,"is_member",False))
                except Exception:
                    # بررسی ناموفق را fail-closed می‌کنیم؛ تا زمانی که Telegram
                    # عضویت را تأیید نکند، کاربر نباید بتواند گیت را دور بزند.
                    joined = False
            if not joined:
                missing.append(item)
    return missing


def _mandatory_gate_markup(missing, user_id=None):
    rows=[]
    for item in missing:
        url=social_item_button_url(item.get("url"))
        if url:
            rows.append([InlineKeyboardButton(f"🚨 {item.get('title') or item.get('name') or 'ورود به تبلیغ اجباری'}", url=url)])
    rows.append([InlineKeyboardButton("🔄 بررسی عضویت", callback_data=f"social:mandatory_check:{int(user_id)}")])
    return InlineKeyboardMarkup(rows)


def _guard(handler):
    async def wrapped(update, context):
        # Owner business/runtime values that are safe to persist are restored from SQLite
        # before every Owner interaction and checkpointed after the handler finishes.
        # Transient waiting/UI keys are explicitly excluded by owner_persistence.
        owner_user = getattr(update, "effective_user", None)
        owner_id = getattr(owner_user, "id", None) if owner_user is not None else None
        is_owner_update = owner_id is not None and int(owner_id) == int(OWNER_ID)
        if is_owner_update:
            try:
                with SessionLocal() as _owner_state_session:
                    load_into_user_data(_owner_state_session, int(owner_id), context.user_data)
            except Exception as exc:
                logging.getLogger("worldwar3_bot").warning("Owner state restore failed: %s", exc)

        # /start تنها استثناست؛ تا تکمیل عضویت در تبلیغات اجباری هیچ قابلیت دیگری اجرا نمی‌شود.
        message=getattr(update,"effective_message",None)
        text=(getattr(message,"text",None) or "").strip() if message is not None else ""
        if not text.startswith("/start") and getattr(update,"callback_query",None) is None and _is_bot_usage_update(update, context):
            user=getattr(update,"effective_user",None)
            if user is not None and not getattr(user,"is_bot",False):
                try:
                    missing=await _mandatory_missing_for_user(context.bot,user.id)
                    if missing:
                        if message is not None:
                            await message.reply_text("🚨 <b>ابتدا عضو تبلیغات اجباری شوید.</b>\n\nتا تکمیل عضویت، هیچ بخش دیگری از ربات فعال نیست.",parse_mode="HTML",reply_markup=_mandatory_gate_markup(missing, user.id))
                        return
                except Exception:
                    if message is not None:
                        await message.reply_text("🚨 <b>ابتدا عضویت در تبلیغات اجباری را تکمیل کنید.</b>",parse_mode="HTML")
                    return

        # هر دستور اسلش جدید باید انتظار عدد/مقدار قبلی امنیت را نیز لغو کند.
        # (پیام‌های عددی عادی نباید این حالت را لغو کنند.)
        message = getattr(update, "effective_message", None)
        text = (getattr(message, "text", None) or "").strip() if message is not None else ""
        if text.startswith("/"):
            context.user_data.pop("security_pending", None)
            # هر دستور جدید، حالت‌های انتظار عدد/متن قبلی را لغو می‌کند.
            waiting_keys = {
                "wallet_state", "wallet_owner_state", "wallet_card_draft",
                "pending_exchange", "economy_pending", "golden_pending", "golden_stage_scope",
                "bank_pending", "missile_pending", "arsenal_sell_pending", "arsenal_sell_custom_pending",
                "hq_tech_pending", "metal_mine_pending", "shield_pending", "social_pending",
            }
            for _key in waiting_keys:
                context.user_data.pop(_key, None)

        # پیام عادی که ربات قرار نیست به آن واکنش نشان دهد، هرگز سهمیهٔ ضداسپم را مصرف نمی‌کند.
        try:
            if _is_bot_usage_update(update, context):
                if not await _anti_spam_user(update, context):
                    return
            return await handler(update, context)
        finally:
            if is_owner_update:
                try:
                    with SessionLocal() as _owner_state_session:
                        save_owner_state(_owner_state_session, int(owner_id), context.user_data)
                except Exception as exc:
                    logging.getLogger("worldwar3_bot").warning("Owner state checkpoint failed: %s", exc)
    return wrapped


async def silent_error_handler(update, context):
    """Never let a Telegram transport/quota error crash the update loop.

    Expected Telegram-side conditions (old callback queries, rate limits,
    blocked users, missing permissions and message-edit races) are handled
    quietly. Unexpected errors are still logged and reported to the Owner.
    """
    logger = logging.getLogger("worldwar3_bot")
    error = context.error
    text = str(error or "")
    lower = text.lower()
    expected = (
        isinstance(error, (RetryAfter, TimedOut, NetworkError, Forbidden))
        or "too many requests" in lower
        or "query is too old" in lower
        or "query id is invalid" in lower
        or "message is not modified" in lower
        or "message to delete not found" in lower
        or "message can't be deleted" in lower
        or "message can't be edited" in lower
        or "user is blocked" in lower
        or "bot was blocked" in lower
        or "chat not found" in lower
        or "user not found" in lower
        or "not enough rights" in lower
        or "administrator rights" in lower
        or "slowmode" in lower
        or "user_banned_in_channel" in lower
    )
    if expected:
        logger.warning("Handled Telegram/API condition: %s", error)
        await report_exception(context.bot, error, update=update, source="⚠️ خطای Telegram/API")
        return
    logger.error("Unhandled update error", exc_info=error)
    await report_exception(context.bot, error, update=update, source="🚨 خطای پردازش ربات")


async def track_bot_group_membership(update, context):
    cm = getattr(update, "my_chat_member", None)
    if cm is None or cm.chat.type not in ("group", "supergroup"):
        return
    status = getattr(cm.new_chat_member, "status", "")
    active = status in {"member", "administrator", "creator", "restricted"}
    try:
        with SessionLocal() as session:
            set_group_status(session, cm.chat.id, active=active, chat_type=cm.chat.type, title=cm.chat.title)
            session.commit()
    except Exception as exc:
        await report_exception(context.bot, exc, update=update, source="🚨 خطای ثبت وضعیت گروه")


def create_application():
    init_db()

    app = Application.builder().token(BOT_TOKEN).post_init(post_init).post_shutdown(post_shutdown).build()

    # تنها دستور اسلشی بازی
    app.add_handler(ChatMemberHandler(track_bot_group_membership, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(ChatMemberHandler(auto_register_optional_membership, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(ChatMemberHandler(auto_track_mandatory_membership, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(CommandHandler("start", _guard(start)))
    app.add_handler(CommandHandler("admin", _guard(admin_command)))
    app.add_handler(CommandHandler("owner", _guard(owner_command)))
    app.add_handler(CommandHandler("leaderboard_continent", _guard(group_leaderboard)))
    app.add_handler(CommandHandler("leaderboard_global", _guard(global_leaderboard)))
    app.add_handler(CommandHandler("leaderboard_continents", _guard(continents_leaderboard)))
    app.add_error_handler(silent_error_handler)

    # دکمه وضعیت ضداسپم باید حتی هنگام محدودیت نیز قابل استفاده باشد.
    app.add_handler(CallbackQueryHandler(_anti_spam_status, pattern=r"^anti:status$"))
    app.add_handler(CallbackQueryHandler(_group_anti_spam_status, pattern=r"^group:anti_status$"))
    # Wallet/payment callbacks before the generic callback dispatcher.
    app.add_handler(CallbackQueryHandler(_guard(wallet_callbacks), pattern=r"^(wallet:|owner:wallet)"))
    # دکمه‌های اصلی ساختمان‌ها باید مستقیم به dispatcher برسند؛
    # ضداسپم متنی نباید باعث بی‌واکنشی CallbackQueryهای ساخت/ارتقا شود.
    app.add_handler(CallbackQueryHandler(_guard(callbacks), pattern=r"^(metal_mine_|hq_|arsenal_)"))
    # دکمه‌های Inline
    app.add_handler(CallbackQueryHandler(_guard(callbacks)))

    # Telegram Stars payment updates.
    app.add_handler(PreCheckoutQueryHandler(wallet_precheckout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, wallet_successful_payment))

    # ثبت Contact تلگرام
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.CONTACT, _guard(contact_message)))

    # پیام‌های متنی گروه
    app.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS & ~filters.COMMAND,
            _guard(group_message),
        )
    )

    # پیام‌های متنی پیوی
    app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & ~filters.COMMAND,
            _guard(private_message),
        )
    )

    return app


if __name__ == "__main__":
    app = create_application()
    print("🌍 World War 3 Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)
