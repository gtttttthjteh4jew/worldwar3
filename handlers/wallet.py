from __future__ import annotations

import asyncio
import re
from datetime import datetime, timedelta
from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, Update
from telegram.ext import ContextTypes
from sqlalchemy import func, select

from config import OWNER_ID
from database.db import SessionLocal
from database.models import User, Wallet, WalletCard, WalletCryptoDestination, WalletTransaction
from keyboards.wallet import (
    account_settings_keyboard,
    card_request_keyboard,
    card_select_keyboard,
    crypto_coin_keyboard,
    crypto_destination_keyboard,
    crypto_quote_keyboard,
    owner_deposit_action_keyboard,
    owner_edit_confirm_keyboard,
    owner_pending_transactions_keyboard,
    owner_rejection_keyboard,
    owner_rejection_confirm_keyboard,
    owner_wallet_card_detail_keyboard,
    owner_wallet_cards_keyboard,
    owner_wallet_crypto_dest_detail_keyboard,
    owner_wallet_crypto_keyboard,
    owner_wallet_gateway_keyboard,
    owner_wallet_general_keyboard,
    owner_wallet_keyboard,
    owner_wallet_payment_methods_keyboard,
    owner_card_payment_keyboard,
    owner_wallet_request_settings_keyboard,
    owner_request_list_keyboard,
    owner_request_detail_keyboard,
    owner_search_request_keyboard,
    owner_wallet_stats_keyboard,
    owner_wallet_card_delete_keyboard,
    owner_wallet_card_delete_confirm_keyboard,
    owner_wallet_stars_keyboard,
    owner_wallet_withdraw_keyboard,
    owner_wallet_manual_keyboard,
    owner_wallet_manual_mode_keyboard,
    owner_wallet_manual_users_keyboard,
    owner_wallet_manual_confirm_keyboard,
    owner_card_draft_confirm_keyboard,
    owner_card_skip_keyboard,
    owner_crypto_dest_step_keyboard,
    owner_crypto_dest_draft_confirm_keyboard,
    owner_withdraw_action_keyboard,
    receipt_confirm_keyboard,
    receipt_upload_keyboard,
    zarinpal_payment_keyboard,
    transaction_list_keyboard,
    wallet_back_inline,
    wallet_back_reply_keyboard,
    wallet_deposit_methods_keyboard,
    wallet_reply_keyboard,
    withdrawal_amount_keyboard,
    withdrawal_confirm_keyboard,
    withdrawal_methods_keyboard,
)
from services.crypto_gateway import create_crypto_invoice, crypto_gateway_configured, process_crypto_webhook
from services.wallet import (
    ACTIVE_DEPOSIT_STATUSES,
    CRYPTO_CONFIRMATIONS,
    CRYPTO_ENABLED,
    CRYPTO_MARKUP_PERCENT,
    CRYPTO_MAX,
    CRYPTO_MIN,
    DEFAULTS,
    STATUS_APPROVED,
    STATUS_CANCELLED,
    STATUS_EXPIRED,
    STATUS_REJECTED,
    STATUS_WAITING_EDIT,
    STATUS_WAITING_OWNER,
    STATUS_WAITING_PAYMENT,
    STATUS_WAITING_RECEIPT,
    STATUS_WAITING_REJECTION,
    STATUS_WAITING_WITHDRAWAL_RECEIPT,
    STARS_DESCRIPTION,
    STARS_ENABLED,
    STARS_MAX,
    STARS_MIN,
    STARS_TOMAN_RATE,
    WALLET_CARD_ENABLED,
    WALLET_CARD_RECEIPT_IMAGE,
    WALLET_CARD_RECEIPT_TEXT,
    WALLET_CARD_ROTATION,
    WALLET_PAYMENT_EXPIRY_MINUTES,
    WALLET_ENABLED,
    WITHDRAW_DAILY_COUNT_LIMIT,
    WITHDRAW_ENABLED,
    ZP_DESCRIPTION,
    ZP_ENABLED,
    ZP_MARKUP_PERCENT,
    ZP_MAX,
    ZP_MERCHANT_ID,
    ZP_MIN,
    _parse_amount,
    accept_card_receipt,
    activate_card_identifier,
    active_cards,
    allocate_identifier_amount,
    amount_limits,
    approve_deposit,
    card_text,
    cancel_transaction,
    clear_identifier,
    create_card_request,
    create_withdrawal,
    crypto_quote_amount,
    ensure_wallet,
    format_amount,
    get_bool,
    get_crypto_rates_toman,
    get_float,
    get_int,
    get_pending_owner_transactions,
    list_owner_requests,
    search_owner_request,
    wallet_admin_stats,
    get_setting,
    get_user_transaction,
    list_transactions,
    metadata,
    new_transaction,
    reject_transaction,
    save_metadata,
    selected_card,
    set_bool,
    set_float,
    set_int,
    set_setting,
    star_amount_for_credit,
    transaction_is_expired,
    validate_amount,
    verify_crypto_transaction,
    CRYPTO_CLIENT_ID,
    CRYPTO_CLIENT_SECRET,
    CRYPTO_WEBHOOK_ENABLED,
    zarinpal_request,
    zarinpal_verify,
    zarinpal_configuration_ready,
    _post_json,
)


def _waiting_scope_key(key):
    return f"__waiting_scope__{key}"


def _state(context, key="wallet_state"):
    value = context.user_data.get(key)
    return value if isinstance(value, dict) else None


def _set_state(context, chat_id, data, key="wallet_state"):
    value = dict(data or {})
    value["chat_id"] = int(chat_id)
    if key == "wallet_owner_state":
        panel = context.user_data.get("wallet_owner_panel") or {}
        value.setdefault("panel_chat_id", int(panel.get("chat_id", chat_id)))
        if panel.get("message_id"):
            value.setdefault("panel_message_id", int(panel["message_id"]))
    context.user_data[key] = value


def _clear_state(context, key="wallet_state"):
    context.user_data.pop(key, None)


def _state_matches(context, chat_id, key="wallet_state"):
    state = _state(context, key)
    return bool(state and int(state.get("chat_id", 0)) == int(chat_id))


def _html(text):
    return escape(str(text or ""))


def _wallet_nav(context):
    stack = context.user_data.get("wallet_nav_stack")
    if not isinstance(stack, list):
        stack = []
        context.user_data["wallet_nav_stack"] = stack
    return stack


def _wallet_nav_reset(context, *items):
    context.user_data["wallet_nav_stack"] = list(items)


def _wallet_nav_push(context, item):
    stack = _wallet_nav(context)
    if not stack or stack[-1] != item:
        stack.append(item)
    return stack


def _wallet_nav_set_current(context, item):
    stack = _wallet_nav(context)
    if stack:
        stack[-1] = item
    else:
        stack.append(item)
    return stack


async def _wallet_section_icon(context) -> str:
    current = (_wallet_nav(context)[-1] if _wallet_nav(context) else "wallet")
    return {
        "account_settings": "💰",
        "wallet": "💰",
        "deposit": "➕",
        "card": "💳",
        "zarinpal": "🏦",
        "crypto": "₿",
        "crypto_dest": "🌐",
        "stars": "⭐",
        "withdraw": "📤",
        "withdraw_card": "📤",
        "transactions": "📜",
        "tx": "🧾",
    }.get(current, "💰")


async def _edit_query_text_or_caption(query, text, *, parse_mode="HTML", reply_markup=None):
    """Edit a callback message regardless of whether the original is text or media+caption."""
    message = getattr(query, "message", None)
    if message is not None and any(getattr(message, attr, None) for attr in ("photo", "video", "animation", "document")):
        return await query.edit_message_caption(
            caption=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )
    return await query.edit_message_text(
        text=text,
        parse_mode=parse_mode,
        reply_markup=reply_markup,
    )


async def _set_wallet_reply_keyboard(context, chat_id, *, label="🔙 برگشت", icon=None):
    """Send the section emoji as the single carrier for the Reply Keyboard.

    Telegram Reply Keyboards are attached to outgoing messages, so wallet
    sections first render their actual panel message and then send exactly one
    visible section emoji carrying the new keyboard. No blank/invisible carrier
    message is used.
    """
    try:
        visible_icon = str(icon or await _wallet_section_icon(context))
        markup = wallet_reply_keyboard() if _command_key(label) == _command_key("💰 کیف پول") else wallet_back_reply_keyboard(label)
        await context.bot.send_message(
            chat_id=int(chat_id),
            text=visible_icon,
            reply_markup=markup,
            disable_notification=True,
        )
    except Exception:
        pass


async def _send_wallet_icon(context, chat_id, icon):
    """Send a plain Telegram Unicode emoji as a decorative section icon.

    No custom asset/sticker file is used for the wallet UI.
    """
    try:
        await context.bot.send_message(
            chat_id=int(chat_id),
            text=str(icon),
            disable_notification=True,
        )
    except Exception:
        pass


async def send_account_settings_view(context, session, target, chat_id):
    """Render the account-settings panel while keeping the existing account information intact."""
    from services.admin import is_admin, is_owner

    role = "👑 مالک ربات" if is_owner(target.telegram_id, OWNER_ID) else ("🛡️ مدیر" if is_admin(session, target.telegram_id, OWNER_ID) else "👤 بازیکن")
    bio = "ثبت نشده"
    photo_id = None
    try:
        chat_info = await context.bot.get_chat(target.telegram_id)
        bio = getattr(chat_info, "bio", None) or "ثبت نشده"
    except Exception:
        pass
    try:
        photos = await context.bot.get_user_profile_photos(target.telegram_id, limit=1)
        if photos.total_count and photos.photos:
            photo_id = photos.photos[0][-1].file_id
    except Exception:
        pass
    created = target.created_at.strftime("%Y/%m/%d — %H:%M") if target.created_at else "ثبت نشده"
    last_active = target.last_active_at.strftime("%Y/%m/%d — %H:%M") if target.last_active_at else "ثبت نشده"
    username = ("@" + target.username) if target.username else "ثبت نشده"
    text = (
        "🪪 <b>پروفایل و اطلاعات اکانت</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"✨ نام: <b>{escape(str(target.first_name or 'بدون نام'))}</b>\n"
        f"🔤 نام کاربری: <b>{escape(username)}</b>\n"
        f"🆔 آیدی تلگرام: <code>{target.telegram_id}</code>\n"
        f"📱 شماره تلفن: <b>{escape(str(target.phone_number or 'ثبت نشده'))}</b>\n"
        f"📝 بیوگرافی: <b>{escape(str(bio))}</b>\n"
        f"🎭 نقش: <b>{role}</b>\n"
        f"📅 تاریخ عضویت در ربات: <b>{created}</b>\n"
        f"🕐 آخرین فعالیت ثبت‌شده: <b>{last_active}</b>\n"
        f"🚫 وضعیت حساب: <b>{'مسدود' if target.is_banned else 'فعال'}</b>\n"
        "━━━━━━━━━━━━━━━━━━"
    )
    # برای جلوگیری از پیام تکراری «تنظیمات اکانت»، پیام قبلی این پنل را حذف و
    # همان پنل را یک‌بار با Reply Keyboard جدید ارسال می‌کنیم.
    ref = context.user_data.get("account_settings_message") or {}
    try:
        if int(ref.get("chat_id", 0)) == int(chat_id) and int(ref.get("message_id", 0)):
            await context.bot.delete_message(chat_id=int(chat_id), message_id=int(ref["message_id"]))
    except Exception:
        pass
    if photo_id:
        sent = await context.bot.send_photo(chat_id=int(chat_id), photo=photo_id, caption=text, parse_mode="HTML", reply_markup=account_settings_keyboard())
        context.user_data["account_settings_message"] = {"chat_id": int(sent.chat_id), "message_id": int(sent.message_id), "kind": "photo"}
    else:
        sent = await context.bot.send_message(chat_id=int(chat_id), text=text, parse_mode="HTML", reply_markup=account_settings_keyboard())
        context.user_data["account_settings_message"] = {"chat_id": int(sent.chat_id), "message_id": int(sent.message_id), "kind": "text"}
    _wallet_nav_reset(context, "account_settings")

def _wallet_home_text(session, user_id):
    wallet = ensure_wallet(session, user_id)
    return (
        "💰 <b>کیف پول شما</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"💵 موجودی: <b>{format_amount(wallet.balance)}</b> تومان\n"
        f"🧾 تعداد تراکنش: <b>{int(wallet.transaction_count or 0)}</b>\n"
        f"➕ مجموع افزایش موجودی: <b>{format_amount(wallet.total_deposits)}</b> تومان\n"
        f"📤 مجموع برداشت نهایی‌شده: <b>{format_amount(wallet.total_withdrawals)}</b> تومان\n"
        f"🔒 مبلغ رزروشده: <b>{format_amount(wallet.reserved_balance)}</b> تومان\n"
        "━━━━━━━━━━━━━━━━━━"
    )


def _wallet_tx_text(session, tx: WalletTransaction):
    user = session.scalar(select(User).where(User.telegram_id == tx.user_id))
    data = metadata(tx)
    status_labels = {
        STATUS_WAITING_PAYMENT: "⏳ در انتظار پرداخت",
        STATUS_WAITING_RECEIPT: "🧾 در انتظار رسید",
        STATUS_WAITING_OWNER: "🕐 در انتظار اونر",
        STATUS_WAITING_EDIT: "✏️ در انتظار ویرایش",
        STATUS_WAITING_REJECTION: "⚠️ در انتظار تعیین دلیل رد",
        STATUS_WAITING_WITHDRAWAL_RECEIPT: "📤 در انتظار رسید واریز",
        STATUS_APPROVED: "✅ تأیید شده",
        STATUS_REJECTED: "❌ رد شده",
        STATUS_CANCELLED: "🚫 لغو شده",
        STATUS_EXPIRED: "⏰ منقضی شده",
    }
    lines = [
        "🧾 <b>جزئیات تراکنش</b>",
        f"🔢 شماره: <code>{_html(tx.transaction_no)}</code>",
        f"📌 نوع: <b>{'افزایش موجودی' if tx.kind == 'deposit' else 'برداشت'}</b>",
        f"💳 روش: <b>{_html({'card': 'کارت‌به‌کارت', 'card_to_card': 'کارت‌به‌کارت', 'zarinpal': 'زرین‌پال', 'crypto': 'رمز ارز', 'stars': 'استارز'}.get(tx.method, tx.method))}</b>",
        f"📊 وضعیت: <b>{status_labels.get(tx.status, tx.status)}</b>",
        f"💰 مبلغ درخواستی: <b>{format_amount(tx.requested_amount)}</b> تومان",
    ]
    if tx.kind == "deposit":
        if tx.payment_amount:
            unit = "استار" if tx.method == "stars" else "تومان"
            lines.append(f"💵 مبلغ ثبت‌شده پرداخت: <b>{format_amount(tx.payment_amount) if unit == 'تومان' else int(tx.payment_amount)}</b> {unit}")
        if tx.verified_amount:
            unit = "استار" if tx.method == "stars" else "تومان"
            lines.append(f"✅ مبلغ تأییدشده: <b>{format_amount(tx.verified_amount) if unit == 'تومان' else int(tx.verified_amount)}</b> {unit}")
        identifier = int(tx.identifier_amount or 0) or int(data.get("identifier_amount") or 0)
        expected_transfer = int(data.get("expected_transfer_amount") or 0)
        if identifier:
            lines.append(f"🔢 مبلغ شناسه: <b>{format_amount(identifier)}</b> تومان")
        if expected_transfer:
            lines.append(f"💳 مبلغ انتقال مورد انتظار: <b>{format_amount(expected_transfer)}</b> تومان")
        if tx.external_id:
            lines.append(f"🔗 شناسه بیرونی: <code>{_html(tx.external_id)}</code>")
        if tx.external_reference:
            lines.append(f"📎 مرجع: <code>{_html(tx.external_reference)}</code>")
        if data.get("coin"):
            lines += [
                f"🪙 ارز: <b>{_html(data.get('coin'))}</b>",
                f"🌐 شبکه: <b>{_html(data.get('network'))}</b>",
                f"📈 نرخ هنگام ساخت: <b>{_html(data.get('rate_toman'))}</b> تومان",
                f"🧮 مقدار رمز ارز: <b>{_html(data.get('crypto_amount'))}</b>",
            ]
        if data.get("stars_amount"):
            lines.append(f"⭐ مقدار استارز: <b>{data['stars_amount']}</b> استار")
    else:
        lines += [
            f"💸 کارمزد: <b>{format_amount(tx.fee_amount)}</b> تومان",
            f"📤 کسر نهایی از کیف پول: <b>{format_amount(tx.payment_amount)}</b> تومان",
        ]
        if tx.destination:
            lines.append(f"📍 مقصد: <code>{_html(tx.destination)}</code>")
    if tx.balance_before or tx.balance_after:
        lines.append(f"📚 موجودی قبل/بعد: <b>{format_amount(tx.balance_before)}</b> / <b>{format_amount(tx.balance_after)}</b> تومان")
    if tx.rejection_reason:
        lines.append(f"📝 دلیل رد: {_html(tx.rejection_reason)}")
    if tx.created_at:
        lines.append(f"🕐 ایجاد: <b>{tx.created_at:%Y/%m/%d — %H:%M}</b>")
    if tx.completed_at:
        lines.append(f"✅ پایان: <b>{tx.completed_at:%Y/%m/%d — %H:%M}</b>")
    if user:
        lines.append(f"👤 کاربر: <b>{_html(user.first_name or user.username or tx.user_id)}</b> — <code>{tx.user_id}</code>")
    return "\n".join(lines)


async def _send_owner_deposit(tx: WalletTransaction, context: ContextTypes.DEFAULT_TYPE):
    with SessionLocal() as session:
        tx_db = session.get(WalletTransaction, tx.id)
        if not tx_db:
            return
        user = session.scalar(select(User).where(User.telegram_id == tx_db.user_id))
        card = session.get(WalletCard, tx_db.wallet_card_id) if tx_db.wallet_card_id else None
        text = (
            "💰 <b>درخواست افزایش موجودی جدید</b>\n\n"
            f"👤 نام: <b>{_html(user.first_name if user else '')}</b>\n"
            f"🔤 نام کاربری: <b>{_html('@' + user.username if user and user.username else 'ثبت نشده')}</b>\n"
            f"🆔 آیدی: <code>{tx_db.user_id}</code>\n"
            f"🧾 تراکنش: <code>{tx_db.transaction_no}</code>\n"
            f"💰 اعتبار درخواستی: <b>{format_amount(tx_db.requested_amount)}</b> تومان\n"
            f"💵 مبلغ قابل پرداخت: <b>{format_amount(int(tx_db.payment_amount) * 10)}</b> ریال\n"
        )
        if tx_db.identifier_amount:
            text += f"🔢 مبلغ شناسه: <b>{format_amount(tx_db.identifier_amount)}</b> تومان\n"
        if card:
            text += f"\n💳 <b>کارت انتخاب‌شده</b>\n{card_text(card)}\n"
        text += f"\n🕐 زمان: <b>{tx_db.created_at:%Y/%m/%d — %H:%M}</b>"
        markup = owner_deposit_action_keyboard(tx_db.id)
        if tx_db.receipt_file_id:
            await context.bot.send_photo(chat_id=OWNER_ID, photo=tx_db.receipt_file_id, caption=text, parse_mode="HTML", reply_markup=markup)
        else:
            receipt = f"\n\n🧾 <b>متن رسید:</b>\n<code>{_html(tx_db.receipt_text or 'ثبت نشده')}</code>"
            await context.bot.send_message(chat_id=OWNER_ID, text=text + receipt, parse_mode="HTML", reply_markup=markup)


async def _send_owner_withdrawal(tx: WalletTransaction, context: ContextTypes.DEFAULT_TYPE):
    with SessionLocal() as session:
        tx_db = session.get(WalletTransaction, tx.id)
        if not tx_db:
            return
        user = session.scalar(select(User).where(User.telegram_id == tx_db.user_id))
        text = (
            "📤 <b>درخواست برداشت جدید</b>\n\n"
            f"👤 نام: <b>{_html(user.first_name if user else '')}</b>\n"
            f"🔤 نام کاربری: <b>{_html('@' + user.username if user and user.username else 'ثبت نشده')}</b>\n"
            f"🆔 آیدی: <code>{tx_db.user_id}</code>\n"
            f"🧾 تراکنش: <code>{tx_db.transaction_no}</code>\n"
            f"📤 مبلغ قابل پرداخت به کاربر: <b>{format_amount(tx_db.requested_amount)}</b> تومان\n"
            f"💸 کارمزد: <b>{format_amount(tx_db.fee_amount)}</b> تومان\n"
            f"🔒 مبلغ رزروشده: <b>{format_amount(tx_db.payment_amount)}</b> تومان\n"
            f"💳 روش: <b>کارت‌به‌کارت</b>\n"
            f"📍 مقصد: <code>{_html(tx_db.destination)}</code>\n\n"
            f"🕐 زمان: <b>{tx_db.created_at:%Y/%m/%d — %H:%M}</b>"
        )
        await context.bot.send_message(chat_id=OWNER_ID, text=text, parse_mode="HTML", reply_markup=owner_withdraw_action_keyboard(tx_db.id))


async def open_wallet(update, context, session, user_id, *, edit_query=None):
    text = _wallet_home_text(session, user_id)
    _wallet_nav_reset(context, "account_settings", "wallet")
    _clear_state(context)
    if edit_query is not None:
        await edit_query.edit_message_text(text, parse_mode="HTML", reply_markup=None)
        context.user_data["wallet_panel_message"] = {"chat_id": int(edit_query.message.chat_id), "message_id": int(edit_query.message.message_id)}
    else:
        sent = await update.message.reply_text(text, parse_mode="HTML", reply_markup=None)
        context.user_data["wallet_panel_message"] = {"chat_id": int(sent.chat_id), "message_id": int(sent.message_id)}
    await _set_wallet_reply_keyboard(context, user_id, label="💰 کیف پول", icon="💰")


async def _handle_wallet_back(context, message, session, user):
    stack = _wallet_nav(context)
    if len(stack) < 2:
        return False
    stack.pop()
    previous = stack[-1]
    _clear_state(context)
    # Do NOT delete the user’s "🔙 برگشت" message.
    if previous == "account_settings":
        await send_account_settings_view(context, session, user, user.telegram_id)
        return True
    if previous == "wallet":
        sent = await message.reply_text(_wallet_home_text(session, user.telegram_id), parse_mode="HTML", reply_markup=None)
        context.user_data["wallet_panel_message"] = {"chat_id": int(sent.chat_id), "message_id": int(sent.message_id)}
        await _set_wallet_reply_keyboard(context, user.telegram_id, label="💰 کیف پول", icon="💰")
        return True
    if previous == "deposit":
        await message.reply_text("➕ <b>افزایش موجودی</b>\n━━━━━━━━━━━━━━━━━━\nروش پرداخت موردنظر را انتخاب کنید.", parse_mode="HTML", reply_markup=wallet_deposit_methods_keyboard(session))
        await _set_wallet_reply_keyboard(context, user.telegram_id, label="🔙 برگشت")
        return True
    if previous == "withdraw":
        await message.reply_text("📤 <b>برداشت از کیف پول</b>\n━━━━━━━━━━━━━━━━━━\nفقط روش کارت‌به‌کارت در دسترس است.", parse_mode="HTML")
        await _set_wallet_reply_keyboard(context, user.telegram_id, label="🔙 برگشت")
        return True
    if previous == "transactions":
        rows, page, pages = list_transactions(session, user.telegram_id, 1)
        if rows:
            await message.reply_text("📜 <b>تراکنش‌های کیف پول</b>\n━━━━━━━━━━━━━━━━━━\nسوابق به‌ترتیب جدیدترین تراکنش نمایش داده می‌شوند.", parse_mode="HTML", reply_markup=transaction_list_keyboard(rows, page, pages))
        else:
            await message.reply_text("📭 <b>تراکنشی وجود ندارد</b>\n\nفعلاً هیچ تراکنشی برای کیف پول شما ثبت نشده است.", parse_mode="HTML")
        await _set_wallet_reply_keyboard(context, user.telegram_id, label="🔙 برگشت")
        return True
    if previous in {"card", "zarinpal", "stars"}:
        await message.reply_text("➕ <b>افزایش موجودی</b>\n━━━━━━━━━━━━━━━━━━\nروش پرداخت موردنظر را انتخاب کنید.", parse_mode="HTML")
        await _set_wallet_reply_keyboard(context, user.telegram_id, label="🔙 برگشت")
        return True
    if previous == "crypto":
        await message.reply_text("₿ <b>رمز ارز</b>\n━━━━━━━━━━━━━━━━━━\nارز موردنظر را انتخاب کنید.", parse_mode="HTML", reply_markup=crypto_coin_keyboard())
        await _set_wallet_reply_keyboard(context, user.telegram_id, label="🔙 برگشت")
        return True
    if previous == "crypto_dest":
        state = _state(context) or {}
        coin = str(state.get("coin") or "").upper()
        if coin:
            dests = list(session.scalars(select(WalletCryptoDestination).where(WalletCryptoDestination.coin == coin, WalletCryptoDestination.enabled == True).order_by(WalletCryptoDestination.id)).all())
            await message.reply_text(f"🪙 <b>شبکه {coin} را انتخاب کنید</b>", parse_mode="HTML", reply_markup=crypto_destination_keyboard(dests))
            await _set_wallet_reply_keyboard(context, user.telegram_id, label="🔙 برگشت")
            return True
        await message.reply_text("₿ <b>رمز ارز</b>\n━━━━━━━━━━━━━━━━━━\nارز موردنظر را انتخاب کنید.", parse_mode="HTML", reply_markup=crypto_coin_keyboard())
        await _set_wallet_reply_keyboard(context, user.telegram_id, label="🔙 برگشت")
        return True
    if previous == "withdraw_card":
        await message.reply_text("📤 <b>برداشت از کیف پول</b>\n━━━━━━━━━━━━━━━━━━\nفقط روش کارت‌به‌کارت در دسترس است.", parse_mode="HTML")
        await _set_wallet_reply_keyboard(context, user.telegram_id, label="🔙 برگشت")
        return True
    return False


async def handle_wallet_message(update: Update, context: ContextTypes.DEFAULT_TYPE, message, session, user) -> bool:
    """Consume wallet-specific private messages. Returns True when consumed."""
    if not message or not getattr(message, "chat_id", None):
        return False
    chat_id = int(message.chat_id)
    text = (message.text or "").strip()
    state = _state(context)
    owner_state = _state(context, "wallet_owner_state")
    owner_user = int(user.telegram_id) == int(OWNER_ID)

    # Navigation must win over active amount/text states so that 🔙 برگشت is always functional.
    key = _command_key(text)
    if key == _command_key("🔙 برگشت"):
        if await _handle_wallet_back(context, message, session, user):
            return True
        # Let the parent account-settings handler deal with Back when the wallet is not active.
        return False

    # Owner input flows always have priority inside the Owner's own chat.
    if owner_user and owner_state and _state_matches(context, chat_id, "wallet_owner_state"):
        consumed = await _handle_owner_input(update, context, message, session, owner_state)
        if consumed:
            return True

    if state and _state_matches(context, chat_id):
        consumed = await _handle_user_input(update, context, message, session, user, state)
        if consumed:
            return True

    if key == _command_key("💰 کیف پول"):
        if not get_bool(session, WALLET_ENABLED):
            await message.reply_text("🔴 کیف پول فعلاً توسط اونر غیرفعال شده است.")
            return True
        await open_wallet(update, context, session, user.telegram_id)
        return True

    if key == _command_key("➕ افزایش موجودی"):
        if not get_bool(session, WALLET_ENABLED):
            await message.reply_text("🔴 <b>افزایش موجودی فعلاً غیرفعال است.</b>", parse_mode="HTML")
            return True
        # اگر هیچ روش پرداختی فعال نیست، نه وضعیت ناوبری و نه Reply Keyboard تغییر نکند.
        active_methods = any((
            get_bool(session, WALLET_CARD_ENABLED),
            get_bool(session, ZP_ENABLED),
            get_bool(session, CRYPTO_ENABLED),
            get_bool(session, STARS_ENABLED),
        ))
        if not active_methods:
            await message.reply_text("🔴 <b>افزایش موجودی فعلاً غیرفعال است.</b>", parse_mode="HTML")
            return True
        _wallet_nav_push(context, "deposit")
        _clear_state(context)
        await message.reply_text(
            "➕ <b>افزایش موجودی</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "روش پرداخت موردنظر را انتخاب کنید.",
            parse_mode="HTML",
            reply_markup=wallet_deposit_methods_keyboard(session),
        )
        await _set_wallet_reply_keyboard(context, user.telegram_id, label="🔙 برگشت")
        return True

    if key == _command_key("📤 برداشت"):
        if not get_bool(session, WALLET_ENABLED) or not get_bool(session, WITHDRAW_ENABLED):
            await message.reply_text("🔴 برداشت فعلاً غیرفعال است.")
            return True
        _wallet_nav_push(context, "withdraw")
        _clear_state(context)
        daily_limit = get_int(session, WITHDRAW_DAILY_COUNT_LIMIT, 0)
        from services.wallet import daily_withdraw_count
        used = daily_withdraw_count(session, user.telegram_id)
        if daily_limit:
            remaining = max(0, daily_limit - used)
            if remaining <= 0:
                await message.reply_text(f"🔴 امروز دیگر امکان ثبت برداشت ندارید. سقف شما {daily_limit:,} درخواست در روز است.")
                return True
            limit_text = f"<b>{remaining:,}</b> برداشت دیگر برای امروز"
        else:
            limit_text = "بدون محدودیت تعداد برداشت روزانه"
        wallet = ensure_wallet(session, user.telegram_id)
        _set_state(context, message.chat_id, {"type": "withdraw_amount"})
        await message.reply_text(
            "📤 <b>برداشت از کیف پول</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "روش برداشت: <b>کارت‌به‌کارت</b>\n"
            f"{limit_text}\n\n"
            "مقدار برداشت را انتخاب کنید.",
            parse_mode="HTML",
        )
        await context.bot.send_message(chat_id=user.telegram_id, text="📤", reply_markup=withdrawal_amount_keyboard(int(wallet.balance or 0)), disable_notification=True)
        return True

    if key == _command_key("📜 تراکنش‌ها"):
        _wallet_nav_push(context, "transactions")
        rows, page, pages = list_transactions(session, user.telegram_id, 1)
        _clear_state(context)
        if not rows:
            await message.reply_text(
                "📭 <b>تراکنشی وجود ندارد</b>\n\nفعلاً هیچ تراکنشی برای کیف پول شما ثبت نشده است.",
                parse_mode="HTML",
            )
        else:
            await message.reply_text(
                "📜 <b>تراکنش‌های کیف پول</b>\n━━━━━━━━━━━━━━━━━━\nسوابق به‌ترتیب جدیدترین تراکنش نمایش داده می‌شوند.",
                parse_mode="HTML", reply_markup=transaction_list_keyboard(rows, page, pages),
            )
        await _set_wallet_reply_keyboard(context, user.telegram_id, label="🔙 برگشت")
        return True

    return False


def _command_key(text):
    value = str(text or "").strip().replace("\u200c", "").replace(" ", "").replace("‌", "")
    import unicodedata
    return "".join(ch for ch in value if unicodedata.category(ch) not in {"So", "Sk"}).lower()


async def _handle_user_input(update, context, message, session, user, state):
    typ = state.get("type")
    text = (message.text or "").strip()

    if typ == "card_amount":
        try:
            amount = _parse_amount(text)
        except Exception:
            await message.reply_text("❌ مبلغ نامعتبر است. فقط عدد تومان ارسال کنید.")
            return True
        ok, err = validate_amount(session, amount, "card")
        if not ok:
            await message.reply_text(f"❌ {err}")
            return True
        tx, err = create_card_request(session, user.telegram_id, amount, state.get("card_id"))
        if err:
            await message.reply_text(f"❌ {err}")
            _clear_state(context)
            return True
        identifier, ident_err = activate_card_identifier(session, tx)
        if ident_err:
            tx.status = STATUS_CANCELLED
            session.commit()
            await message.reply_text(f"❌ {ident_err}")
            _clear_state(context)
            return True
        session.commit()
        card = session.get(WalletCard, tx.wallet_card_id)
        _set_state(context, message.chat_id, {"type": "card_request", "tx_id": tx.id, "chat_id": message.chat_id})
        payable_rial = int(tx.payment_amount) * 10
        await message.reply_text(
            "💳 <b>درخواست کارت‌به‌کارت شد</b>\n\n"
            f"💰 اعتبار موردنظر: <b>{format_amount(tx.requested_amount)}</b> تومان\n"
            f"💵 مبلغ پرداختی: <b>{format_amount(tx.payment_amount)}</b> تومان\n"
            f"⏳ مهلت درخواست: <b>{get_int(session, WALLET_PAYMENT_EXPIRY_MINUTES)} دقیقه</b>\n\n"
            f"{card_text(card) if card else ''}\n\n"
            f"💵 مبلغ قابل پرداخت: <b>{format_amount(payable_rial)}</b> ریال",
            parse_mode="HTML",
            reply_markup=card_request_keyboard(tx.id, True, payable_rial=payable_rial, card_number=(card.card_number if card else None)),
        )
        return True

    if typ == "card_receipt":
        try:
            tx_id = int(state.get("tx_id"))
        except (TypeError, ValueError):
            _clear_state(context)
            await message.reply_text("❌ درخواست رسید دیگر معتبر نیست. لطفاً دوباره از بخش کارت‌به‌کارت شروع کنید.")
            return True
        tx = session.get(WalletTransaction, tx_id)
        if not tx or tx.user_id != user.telegram_id:
            _clear_state(context); return True
        if message.photo:
            file_id = message.photo[-1].file_id
            ok, err = accept_card_receipt(session, tx, text=message.caption or None, file_id=file_id, file_kind="photo")
        elif text:
            ok, err = accept_card_receipt(session, tx, text=text)
        else:
            await message.reply_text("❌ رسید خالی است؛ متن یا تصویر رسید را ارسال کنید.")
            return True
        if not ok:
            await message.reply_text(f"❌ {err}")
            if tx.status == STATUS_EXPIRED:
                _clear_state(context)
            return True
        session.commit()
        _set_state(context, message.chat_id, {"type": "card_receipt_confirm", "tx_id": tx.id})
        await message.reply_text(
            "🧾 <b>رسید ثبت شد</b>\n\n"
            f"🆔 تراکنش: <code>{tx.transaction_no}</code>\n"
            f"💰 اعتبار درخواستی: <b>{format_amount(tx.requested_amount)}</b> تومان\n"
            f"💵 مبلغ انتقال مورد انتظار: <b>{format_amount(tx.payment_amount)}</b> تومان\n"
            "\nقبل از ارسال برای اونر، رسید را تأیید کنید.",
            parse_mode="HTML",
            reply_markup=receipt_confirm_keyboard(tx.id),
        )
        return True

    if typ == "withdraw_amount":
        percentage_map = {
            _command_key("5٪ موجودی"): 5,
            _command_key("10٪ موجودی"): 10,
            _command_key("20٪ موجودی"): 20,
            _command_key("25٪ موجودی"): 25,
            _command_key("50٪ موجودی"): 50,
            _command_key("100٪ موجودی"): 100,
        }
        if key := _command_key(text):
            pct = percentage_map.get(key)
        else:
            pct = None
        if pct is not None:
            wallet = ensure_wallet(session, user.telegram_id)
            amount = int(int(wallet.balance or 0) * pct / 100)
            if amount <= 0:
                await message.reply_text("❌ این درصد از موجودی شما مبلغ قابل برداشت ایجاد نمی‌کند.")
                return True
        else:
            if _command_key(text) == _command_key("💰 مبلغ دلخواه"):
                _set_state(context, message.chat_id, {"type": "withdraw_amount_custom"})
                await message.reply_text("✏️ مبلغ دلخواه برداشت را به تومان ارسال کنید.")
                return True
            try:
                amount = _parse_amount(text)
            except Exception:
                await message.reply_text("❌ مبلغ نامعتبر است. یکی از درصدها را انتخاب کنید یا مبلغ دلخواه را ارسال کنید.")
                return True
        try:
            amount = int(amount)
        except Exception:
            await message.reply_text("❌ مبلغ نامعتبر است. فقط عدد تومان ارسال کنید.")
            return True
        ok, err = validate_amount(session, amount, "withdraw")
        if not ok:
            await message.reply_text(f"❌ {err}")
            return True
        wallet = ensure_wallet(session, user.telegram_id)
        if int(wallet.balance) < amount:
            await message.reply_text(f"❌ موجودی کافی نیست. موجودی فعلی: {format_amount(wallet.balance)} تومان.")
            return True
        daily_limit = get_int(session, WITHDRAW_DAILY_COUNT_LIMIT, 0)
        if daily_limit:
            from services.wallet import daily_withdraw_count
            used = daily_withdraw_count(session, user.telegram_id)
            if used >= daily_limit:
                await message.reply_text(f"❌ سقف روزانه شما تکمیل شده است. حداکثر {daily_limit:,} برداشت در روز مجاز است.")
                return True
        _set_state(context, message.chat_id, {"type": "withdraw_destination", "amount": amount})
        await message.reply_text(
            "💳 <b>کارت مقصد برداشت</b>\n\n"
            f"💰 مبلغ برداشت: <b>{format_amount(amount)}</b> تومان\n"
            "شماره کارت مقصدی که اونر باید به آن واریز کند را ارسال کنید.",
            parse_mode="HTML",
        )
        await _set_wallet_reply_keyboard(context, message.chat_id, label="🔙 برگشت")
        return True

    if typ == "withdraw_amount_custom":
        try:
            amount = _parse_amount(text)
        except Exception:
            await message.reply_text("❌ مبلغ نامعتبر است. فقط عدد تومان ارسال کنید.")
            return True
        ok, err = validate_amount(session, amount, "withdraw")
        if not ok:
            await message.reply_text(f"❌ {err}")
            return True
        wallet = ensure_wallet(session, user.telegram_id)
        if int(wallet.balance or 0) < amount:
            await message.reply_text(f"❌ موجودی کافی نیست. موجودی فعلی: {format_amount(wallet.balance)} تومان.")
            return True
        daily_limit = get_int(session, WITHDRAW_DAILY_COUNT_LIMIT, 0)
        if daily_limit:
            from services.wallet import daily_withdraw_count
            if daily_withdraw_count(session, user.telegram_id) >= daily_limit:
                await message.reply_text(f"❌ سقف روزانه شما تکمیل شده است. حداکثر {daily_limit:,} برداشت در روز مجاز است.")
                return True
        _set_state(context, message.chat_id, {"type": "withdraw_destination", "amount": amount})
        await message.reply_text("💳 <b>کارت مقصد برداشت</b>\n\n" f"💰 مبلغ برداشت: <b>{format_amount(amount)}</b> تومان\n" "شماره کارت مقصد را ارسال کنید.", parse_mode="HTML")
        await _set_wallet_reply_keyboard(context, message.chat_id, label="🔙 برگشت")
        return True

    if typ == "withdraw_destination":
        destination = text.replace(" ", "").strip().translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
        if not destination:
            await message.reply_text("❌ شماره کارت مقصد را ارسال کنید.")
            return True
        try:
            amount = int(state.get("amount"))
        except (TypeError, ValueError):
            _clear_state(context)
            await message.reply_text("❌ درخواست برداشت دیگر معتبر نیست. لطفاً دوباره از بخش برداشت شروع کنید.")
            return True
        wallet = ensure_wallet(session, user.telegram_id)
        if int(wallet.balance) < amount:
            await message.reply_text("❌ موجودی شما دیگر برای این برداشت کافی نیست. دوباره مبلغ را انتخاب کنید.")
            _set_state(context, message.chat_id, {"type": "withdraw_amount"})
            return True
        if not re.fullmatch(r"\d{16,24}", destination):
            await message.reply_text("❌ شماره کارت مقصد باید فقط شامل ارقام و معمولاً ۱۶ رقم باشد.")
            return True
        daily_limit = get_int(session, WITHDRAW_DAILY_COUNT_LIMIT, 0)
        if daily_limit:
            from services.wallet import daily_withdraw_count
            if daily_withdraw_count(session, user.telegram_id) >= daily_limit:
                await message.reply_text(f"❌ سقف روزانه شما تکمیل شده است. حداکثر {daily_limit:,} برداشت در روز مجاز است.")
                _clear_state(context)
                return True
        _set_state(context, message.chat_id, {"type": "withdraw_confirm_draft", "amount": amount, "destination": destination})
        await message.reply_text(
            "📤 <b>تأیید نهایی برداشت</b>\n\n"
            f"💰 مبلغ دریافتی شما: <b>{format_amount(amount)}</b> تومان\n"
            f"📍 کارت مقصد: <code>{_html(destination)}</code>\n\n"
            "با تأیید، همین لحظه مبلغ از موجودی قابل‌مصرف شما کسر و برای اونر رزرو می‌شود.",
            parse_mode="HTML",
            reply_markup=withdrawal_confirm_keyboard(None),
        )
        await _set_wallet_reply_keyboard(context, message.chat_id, label="🔙 برگشت")
        return True

    if typ == "zarinpal_amount":
        try:
            amount = _parse_amount(text)
        except Exception:
            await message.reply_text("❌ مبلغ نامعتبر است. فقط عدد تومان ارسال کنید.")
            return True
        minimum, maximum = get_int(session, ZP_MIN), get_int(session, ZP_MAX)
        if amount < minimum or (maximum and amount > maximum):
            await message.reply_text(f"❌ مبلغ باید بین {format_amount(minimum)} و {format_amount(maximum)} تومان باشد.")
            return True
        markup = get_float(session, ZP_MARKUP_PERCENT, 0, 1000)
        payment_amount = int((amount * (100 + markup) + 99) // 100)
        expires = datetime.utcnow() + timedelta(minutes=get_int(session, WALLET_PAYMENT_EXPIRY_MINUTES, 30))
        tx = new_transaction(session, user.telegram_id, "deposit", "zarinpal", amount, expires_at=expires, metadata={"markup_percent": markup, "requested_toman": amount})
        tx.payment_amount = payment_amount
        try:
            payment_url = await zarinpal_request(session, tx)
            session.commit()
        except Exception as exc:
            tx.status = STATUS_CANCELLED
            tx.rejection_reason = f"خطای ایجاد درگاه: {type(exc).__name__}"
            session.commit()
            await message.reply_text(f"❌ ساخت لینک درگاه ناموفق بود. {_html(exc)}")
            return True
        _clear_state(context)
        await message.reply_text(
            "🏦 <b>درگاه زرین‌پال</b>\n\n"
            f"💰 اعتبار کیف پول: <b>{format_amount(amount)}</b> تومان\n"
            f"💳 مبلغ پرداخت درگاه: <b>{format_amount(payment_amount)}</b> تومان\n"
            f"➕ درصد اونر: <b>{markup:g}%</b>\n"
            f"⏳ مهلت: <b>{get_int(session, WALLET_PAYMENT_EXPIRY_MINUTES)} دقیقه</b>",
            parse_mode="HTML", reply_markup=zarinpal_payment_keyboard(tx.id, payment_url)
        )
        return True

    if typ == "stars_amount":
        try:
            amount = _parse_amount(text)
        except Exception:
            await message.reply_text("❌ مبلغ نامعتبر است. فقط عدد تومان ارسال کنید.")
            return True
        minimum, maximum = get_int(session, STARS_MIN), get_int(session, STARS_MAX)
        if amount < minimum or (maximum and amount > maximum):
            await message.reply_text(f"❌ مبلغ باید بین {format_amount(minimum)} و {format_amount(maximum)} تومان باشد.")
            return True
        stars = star_amount_for_credit(session, amount)
        expires = datetime.utcnow() + timedelta(minutes=get_int(session, WALLET_PAYMENT_EXPIRY_MINUTES, 30))
        tx = new_transaction(session, user.telegram_id, "deposit", "stars", amount, expires_at=expires, metadata={"stars_amount": stars, "stars_rate_toman": get_int(session, STARS_TOMAN_RATE), "requested_toman": amount})
        tx.payment_amount = stars
        session.commit()
        _clear_state(context)
        try:
            await context.bot.send_invoice(
                chat_id=user.telegram_id,
                title="افزایش موجودی کیف پول",
                description=get_setting(session, STARS_DESCRIPTION, "افزایش موجودی کیف پول با استارز")[:255],
                payload=f"walletstars:{tx.id}",
                currency="XTR",
                prices=[LabeledPrice(label=f"افزایش موجودی {format_amount(amount)} تومان", amount=int(stars))],
                provider_token="",
            )
        except Exception as exc:
            tx.status = STATUS_CANCELLED
            tx.rejection_reason = f"خطای ارسال فاکتور استارز: {type(exc).__name__}"
            session.commit()
            await message.reply_text(f"❌ ارسال فاکتور استارز ناموفق بود. {_html(exc)}")
        return True

    if typ == "crypto_amount":
        try:
            amount = _parse_amount(text)
        except Exception:
            await message.reply_text("❌ مبلغ نامعتبر است."); return True
        minimum, maximum = get_int(session, CRYPTO_MIN), get_int(session, CRYPTO_MAX)
        if amount < minimum or (maximum and amount > maximum):
            await message.reply_text(f"❌ مبلغ باید بین {format_amount(minimum)} و {format_amount(maximum)} تومان باشد."); return True
        if not crypto_gateway_configured(session):
            _clear_state(context)
            await message.reply_text("❌ درگاه رمز ارز هنوز توسط اونر تنظیم نشده است.")
            return True
        general_expiry = max(1, get_int(session, WALLET_PAYMENT_EXPIRY_MINUTES, 30))
        expires_at = datetime.utcnow() + timedelta(minutes=general_expiry)
        tx = new_transaction(session, user.telegram_id, "deposit", "crypto", amount, expires_at=expires_at, metadata={
            "selected_coin": str(state.get("coin") or "").upper(),
            "gateway": "coinpayments",
        })
        try:
            result = await create_crypto_invoice(session, tx, str(state.get("coin") or "").upper())
            session.commit()
        except Exception as exc:
            session.rollback()
            _clear_state(context)
            await message.reply_text(f"❌ ساخت فاکتور رمز ارزی ناموفق بود: {_html(str(exc))}")
            return True
        _clear_state(context)
        await message.reply_text(
            "₿ <b>فاکتور رمز ارزی</b>\n\n"
            f"🪙 ارز: <b>{_html(result['selected'])}</b>\n"
            f"💰 اعتبار کیف پول: <b>{format_amount(amount)}</b> تومان\n"
            f"💳 مبلغ محاسبه‌شده پرداخت: <b>{format_amount(result['charge_toman'])}</b> تومان\n"
            f"⏳ مهلت پرداخت: <b>{result['expires']:%Y/%m/%d — %H:%M:%S}</b>\n\n"
            "برای پرداخت روی دکمه زیر بزنید. وضعیت پرداخت به‌صورت خودکار بررسی می‌شود.",
            parse_mode="HTML",
            reply_markup=crypto_quote_keyboard(tx.id, result["link"]),
        )
        return True

    if typ == "crypto_txid":
        try:
            tx_id = int(state.get("tx_id"))
        except (TypeError, ValueError):
            _clear_state(context)
            await message.reply_text("❌ درخواست رمز ارز دیگر معتبر نیست. لطفاً دوباره از بخش رمز ارز شروع کنید.")
            return True
        tx = session.get(WalletTransaction, tx_id)
        if not tx or tx.user_id != user.telegram_id:
            _clear_state(context); return True
        if transaction_is_expired(tx):
            tx.status = STATUS_EXPIRED; session.commit(); _clear_state(context)
            await message.reply_text("⏰ فاکتور منقضی شده است. لطفاً فاکتور جدید بگیرید.")
            return True
        txid = text.strip()
        if not txid:
            await message.reply_text("❌ TXID نامعتبر است."); return True
        exists = session.scalar(select(WalletTransaction).where(WalletTransaction.external_id == txid, WalletTransaction.id != tx.id, WalletTransaction.status.not_in([STATUS_CANCELLED, STATUS_REJECTED, STATUS_EXPIRED])))
        if exists:
            await message.reply_text("❌ این TXID قبلاً در یک تراکنش ثبت شده است.")
            return True
        tx.external_id = txid
        dest = session.get(WalletCryptoDestination, int(metadata(tx).get("destination_id")))
        if not dest:
            await message.reply_text("❌ مقصد رمز ارز پیدا نشد."); return True
        result = await verify_crypto_transaction(tx, dest)
        tx.metadata_json = __import__("json").dumps({**metadata(tx), "verification": result}, ensure_ascii=False)
        if result.get("ok"):
            ok, err = approve_deposit(session, tx, tx.requested_amount, external_reference=txid)
            session.commit()
            _clear_state(context)
            if ok:
                await message.reply_text(f"✅ پرداخت رمز ارز تأیید شد و {format_amount(tx.requested_amount)} تومان به کیف پول شما اضافه شد.")
                await _set_wallet_reply_keyboard(context, user.telegram_id, label="🔙 برگشت")
            else:
                await message.reply_text(f"❌ {err}")
            return True
        tx.status = STATUS_WAITING_OWNER
        session.commit()
        _clear_state(context)
        await message.reply_text(
            "🕐 <b>TXID ثبت شد</b>\n\n"
            f"نتیجه بررسی آنلاین: {_html(result.get('message'))}\n"
            "در صورت نیاز اونر تراکنش را به‌صورت دستی بررسی و تأیید می‌کند.",
            parse_mode="HTML",
            reply_markup=None,
        )
        await _set_wallet_reply_keyboard(context, user.telegram_id, label="🔙 برگشت", icon="🧾")
        await _send_owner_deposit(tx, context)
        return True

    return False


async def wallet_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not update.effective_user:
        return
    data = query.data or ""
    if not (data.startswith("wallet:") or data.startswith("owner:wallet") or data.startswith("owner:wallet_")):
        return
    with SessionLocal() as session:
        from services.admin import is_owner, is_admin
        user_id = int(query.from_user.id)
        user = session.scalar(select(User).where(User.telegram_id == user_id))
        if user is None:
            await query.answer("❌ کاربر ثبت نشده است.", show_alert=True); return
        owner_user = is_owner(user_id, OWNER_ID)
        if data.startswith("owner:"):
            if not owner_user:
                await query.answer("⛔ فقط اونر به این بخش دسترسی دارد.", show_alert=True); return
            await _owner_callback(update, context, query, session, data)
        else:
            await _user_callback(update, context, query, session, user, data)


async def _user_callback(update, context, query, session, user, data):
    parts = data.split(":")
    action = parts[1] if len(parts) > 1 else ""
    if action == "noop":
        await query.answer(); return
    if not get_bool(session, WALLET_ENABLED) and action not in {"cancel"}:
        await query.answer("🔴 کیف پول فعلاً غیرفعال است.", show_alert=True); return

    if action == "home":
        stack = _wallet_nav(context)
        if not stack or stack[-1] != "wallet":
            _wallet_nav_reset(context, "account_settings", "wallet")
        _clear_state(context)
        await query.answer()
        await query.edit_message_text(_wallet_home_text(session, user.telegram_id), parse_mode="HTML", reply_markup=None)
        context.user_data["wallet_panel_message"] = {"chat_id": int(query.message.chat_id), "message_id": int(query.message.message_id)}
        await _set_wallet_reply_keyboard(context, user.telegram_id, label="💰 کیف پول", icon="💰")
        return

    if action == "deposit_methods":
        # این مسیر فقط Inline است؛ ReplyKeyboard باید در سطح منطقی قبلی باقی بماند.
        _wallet_nav_set_current(context, "deposit")
        _clear_state(context)
        await query.answer(); await query.edit_message_text("➕ <b>افزایش موجودی</b>\n━━━━━━━━━━━━━━━━━━\nروش پرداخت موردنظر را انتخاب کنید.", parse_mode="HTML", reply_markup=wallet_deposit_methods_keyboard(session))
        return

    if action == "deposit" and len(parts) >= 3:
        method = parts[2]
        if method == "card":
            if not get_bool(session, WALLET_CARD_ENABLED):
                await query.answer("💳 کارت‌به‌کارت فعلاً غیرفعال است.", show_alert=True); return
            cards = active_cards(session)
            if not cards:
                await query.answer("هیچ کارت فعالی تنظیم نشده است.", show_alert=True); return
            if get_bool(session, WALLET_CARD_ROTATION) or len(cards) == 1:
                _wallet_nav_set_current(context, "deposit")
                _set_state(context, user.telegram_id, {"type": "card_amount", "chat_id": user.telegram_id, "card_id": cards[0].id if len(cards) == 1 else None})
                await query.answer(); await query.edit_message_text(
                    "💳 <b>کارت به کارت</b>\n━━━━━━━━━━━━━━━━━━\n"
                    "مبلغی که می‌خواهید به کیف پول اضافه شود را فقط به تومان ارسال کنید.",
                    parse_mode="HTML", reply_markup=wallet_back_inline("wallet:deposit_methods")
                )
            else:
                _wallet_nav_set_current(context, "deposit")
                await query.answer(); await query.edit_message_text(
                    "💳 <b>کارت مقصد را انتخاب کنید</b>\n\nیکی از کارت‌های فعال را انتخاب کنید.",
                    parse_mode="HTML", reply_markup=card_select_keyboard(cards, "wallet:deposit_methods")
                )
            return
        if method == "zarinpal":
            if not get_bool(session, ZP_ENABLED):
                await query.answer("درگاه زرین‌پال فعلاً غیرفعال است.", show_alert=True); return
            if not zarinpal_configuration_ready(session):
                await query.answer("درگاه زرین‌پال هنوز توسط اونر کامل پیکربندی نشده است.", show_alert=True); return
            minimum, maximum = get_int(session, ZP_MIN), get_int(session, ZP_MAX)
            _wallet_nav_set_current(context, "deposit")
            _clear_state(context)
            _set_state(context, user.telegram_id, {"type": "zarinpal_amount", "chat_id": user.telegram_id})
            await query.answer(); await query.edit_message_text(
                f"🏦 <b>درگاه زرین‌پال</b>\n━━━━━━━━━━━━━━━━━━\nمبلغ اعتبار را بین <b>{format_amount(minimum)}</b> تا <b>{format_amount(maximum)}</b> تومان ارسال کنید.",
                parse_mode="HTML", reply_markup=wallet_back_inline("wallet:deposit_methods")
            )
            return
        if method == "crypto":
            _wallet_nav_set_current(context, "deposit")
            _clear_state(context)
            await query.answer(); await query.edit_message_text("₿ <b>رمز ارز</b>\n━━━━━━━━━━━━━━━━━━\nارز موردنظر را انتخاب کنید.", parse_mode="HTML", reply_markup=crypto_coin_keyboard("wallet:deposit_methods"))
            return
        if method == "stars":
            minimum, maximum = get_int(session, STARS_MIN), get_int(session, STARS_MAX)
            _wallet_nav_set_current(context, "deposit")
            _clear_state(context)
            _set_state(context, user.telegram_id, {"type": "stars_amount", "chat_id": user.telegram_id})
            await query.answer(); await query.edit_message_text(f"⭐ <b>استارز تلگرام</b>\n━━━━━━━━━━━━━━━━━━\nمبلغ اعتبار را بین <b>{format_amount(minimum)}</b> تا <b>{format_amount(maximum)}</b> تومان ارسال کنید.\n\nارزش داخلی هر استارز را اونر تنظیم می‌کند.", parse_mode="HTML", reply_markup=wallet_back_inline("wallet:deposit_methods"))
            return

    if action == "card_select" and len(parts) >= 3:
        card = selected_card(session, int(parts[2]))
        if not card:
            await query.answer("کارت دیگر فعال نیست.", show_alert=True); return
        _wallet_nav_set_current(context, "deposit")
        _set_state(context, user.telegram_id, {"type": "card_amount", "chat_id": user.telegram_id, "card_id": card.id})
        minimum, maximum = get_int(session, "wallet_card_min"), get_int(session, "wallet_card_max")
        await query.answer(); await query.edit_message_text(
            "💳 <b>کارت به کارت</b>\n━━━━━━━━━━━━━━━━━━\n"
            f"مبلغی که می‌خواهید به کیف پول اضافه شود را بین <b>{format_amount(minimum)} تومان</b> و <b>{format_amount(maximum)} تومان</b> بفرستید.",
            parse_mode="HTML", reply_markup=wallet_back_inline("wallet:deposit_methods")
        )
        return

    if action == "card_activate" and len(parts) >= 3:
        tx = get_user_transaction(session, user.telegram_id, int(parts[2]))
        if not tx:
            await query.answer("تراکنش پیدا نشد.", show_alert=True); return
        value, err = __import__('services.wallet', fromlist=['activate_card_identifier']).activate_card_identifier(session, tx)
        if err:
            session.commit(); await query.answer(err, show_alert=True); return
        session.commit()
        _set_state(context, user.telegram_id, {"type": "card_receipt", "chat_id": user.telegram_id, "tx_id": tx.id})
        await query.answer("حالا رسید را ارسال کنید.")
        await query.edit_message_text(
            "📤 <b>ارسال رسید</b>\n\n"
            "رسید را به‌صورت عکس یا متن ارسال کنید.",
            parse_mode="HTML", reply_markup=receipt_upload_keyboard(tx.id)
        )
        return

    if action == "receipt_back" and len(parts) >= 3:
        tx = get_user_transaction(session, user.telegram_id, int(parts[2]))
        if not tx or tx.status not in {STATUS_WAITING_RECEIPT, STATUS_WAITING_OWNER}:
            await query.answer("این درخواست دیگر قابل ویرایش نیست.", show_alert=True); return
        card = session.get(WalletCard, tx.wallet_card_id)
        payable_rial = int(tx.payment_amount) * 10
        _set_state(context, user.telegram_id, {"type": "card_request", "tx_id": tx.id, "chat_id": user.telegram_id})
        await query.answer()
        await query.edit_message_text(
            "💳 <b>درخواست کارت‌به‌کارت شد</b>\n\n"
            f"💰 اعتبار موردنظر: <b>{format_amount(tx.requested_amount)}</b> تومان\n"
            f"💵 مبلغ پرداختی: <b>{format_amount(tx.payment_amount)}</b> تومان\n"
            f"⏳ مهلت درخواست: <b>{get_int(session, WALLET_PAYMENT_EXPIRY_MINUTES)} دقیقه</b>\n\n"
            f"{card_text(card) if card else ''}\n\n"
            f"💵 مبلغ قابل پرداخت: <b>{format_amount(payable_rial)}</b> ریال",
            parse_mode="HTML",
            reply_markup=card_request_keyboard(tx.id, True, payable_rial=payable_rial, card_number=(card.card_number if card else None)),
        )
        return

    if action in {"receipt_confirm", "receipt_edit"} and len(parts) >= 3:
        tx = get_user_transaction(session, user.telegram_id, int(parts[2]))
        if not tx:
            await query.answer("تراکنش پیدا نشد.", show_alert=True); return
        if action == "receipt_edit":
            _set_state(context, user.telegram_id, {"type": "card_receipt", "tx_id": tx.id})
            await query.answer(); await query.edit_message_text("✏️ <b>ارسال رسید جدید</b>\n\nرسید را به‌صورت متن یا تصویر ارسال کنید.", parse_mode="HTML", reply_markup=wallet_back_inline("wallet:deposit_methods"))
            return
        if tx.status != STATUS_WAITING_OWNER:
            await query.answer("این رسید قبلاً ثبت یا پردازش شده است.", show_alert=True); return
        _clear_state(context)
        session.commit()
        _wallet_nav_reset(context, "account_settings", "wallet")
        await query.answer("✅ رسید برای اونر ارسال شد.")
        await query.edit_message_text(_wallet_home_text(session, user.telegram_id), parse_mode="HTML", reply_markup=None)
        context.user_data["wallet_panel_message"] = {"chat_id": int(query.message.chat_id), "message_id": int(query.message.message_id)}
        await _set_wallet_reply_keyboard(context, user.telegram_id, label="💰 کیف پول", icon="💰")
        await _send_owner_deposit(tx, context)
        return

    if action == "cancel" and len(parts) >= 3:
        tx = get_user_transaction(session, user.telegram_id, int(parts[2]))
        if tx and cancel_transaction(session, tx):
            session.commit()
        _clear_state(context)
        _wallet_nav_reset(context, "account_settings", "wallet")
        await query.answer("درخواست لغو شد.", show_alert=True)
        await query.edit_message_text(_wallet_home_text(session, user.telegram_id), parse_mode="HTML", reply_markup=None)
        context.user_data["wallet_panel_message"] = {"chat_id": int(query.message.chat_id), "message_id": int(query.message.message_id)}
        await _set_wallet_reply_keyboard(context, user.telegram_id, label="💰 کیف پول", icon="💰")
        return

    if action == "crypto_coin" and len(parts) >= 3:
        coin = parts[2].upper()
        if coin not in {"BTC", "USDT", "TON"}:
            await query.answer("❌ فقط بیت‌کوین، تتر و تون‌کوین پشتیبانی می‌شوند.", show_alert=True); return
        if not crypto_gateway_configured(session):
            await query.answer("❌ درگاه رمز ارز هنوز توسط اونر تنظیم نشده است.", show_alert=True); return
        _wallet_nav_set_current(context, "deposit")
        _set_state(context, user.telegram_id, {"type": "crypto_amount", "coin": coin})
        network_text = "USDT / TRC20" if coin == "USDT" else coin
        await query.answer(); await query.edit_message_text(f"🪙 <b>{_html(network_text)}</b>\n━━━━━━━━━━━━━━━━━━\nمبلغ اعتبار را به تومان ارسال کنید.", parse_mode="HTML", reply_markup=wallet_back_inline("wallet:deposit:crypto"))
        return

    if action == "crypto_dest" and len(parts) >= 3:
        dest = session.get(WalletCryptoDestination, int(parts[2]))
        if not dest or not dest.enabled:
            await query.answer("مقصد دیگر فعال نیست.", show_alert=True); return
        _wallet_nav_set_current(context, "deposit")
        _set_state(context, user.telegram_id, {"type": "crypto_amount", "coin": dest.coin, "dest_id": dest.id})
        await query.answer(); await query.edit_message_text(f"🪙 <b>{_html(dest.coin)} / {_html(dest.network)}</b>\n━━━━━━━━━━━━━━━━━━\nمبلغ اعتبار را به تومان ارسال کنید.", parse_mode="HTML", reply_markup=wallet_back_inline("wallet:deposit:crypto"))
        return

    if action == "crypto_txid" and len(parts) >= 3:
        tx = get_user_transaction(session, user.telegram_id, int(parts[2]))
        if not tx:
            await query.answer("تراکنش پیدا نشد.", show_alert=True); return
        _set_state(context, user.telegram_id, {"type": "crypto_txid", "tx_id": tx.id})
        await query.answer(); await query.edit_message_text("📝 <b>TXID تراکنش</b>\n\nTXID را ارسال کنید.", parse_mode="HTML", reply_markup=wallet_back_inline("wallet:deposit:crypto"))
        return

    if action == "crypto_check" and len(parts) >= 3:
        try:
            tx_id = int(parts[2])
        except Exception:
            await query.answer("تراکنش نامعتبر است.", show_alert=True); return
        tx = get_user_transaction(session, user.telegram_id, tx_id)
        if not tx or tx.method != "crypto":
            await query.answer("تراکنش پیدا نشد.", show_alert=True); return
        if tx.status == STATUS_APPROVED:
            await query.answer("✅ این پرداخت قبلاً تأیید شده است.", show_alert=True); return
        if not tx.external_id:
            await query.answer("⏳ فاکتور هنوز آماده نشده است.", show_alert=True); return
        from services.crypto_gateway import poll_one_crypto_transaction
        result = await poll_one_crypto_transaction(tx)
        if result and result.get("status") == STATUS_APPROVED:
            await query.answer("✅ پرداخت تأیید شد.", show_alert=True)
            await query.edit_message_text(f"✅ <b>پرداخت رمز ارزی تأیید شد.</b>\n\n🧾 تراکنش: <code>{_html(tx.transaction_no)}</code>\n💰 مبلغ اضافه‌شده: <b>{format_amount(tx.requested_amount)} تومان</b>", parse_mode="HTML")
            return
        await query.answer("⏳ هنوز پرداخت نهایی نشده است. چند لحظه بعد دوباره بررسی کنید.", show_alert=True)
        return

    if action in {"withdraw_card", "withdraw_method"}:
        if not get_bool(session, WITHDRAW_ENABLED):
            await query.answer("برداشت غیرفعال است.", show_alert=True); return
        _wallet_nav_push(context, "withdraw_card")
        _set_state(context, user.telegram_id, {"type": "withdraw_amount"})
        await query.answer()
        await query.edit_message_text(
            "💳 <b>برداشت کارت‌به‌کارت</b>\n━━━━━━━━━━━━━━━━━━\n"
            "مبلغی که می‌خواهید برداشت کنید را فقط به تومان ارسال کنید.\n\n"
            f"🔽 حداقل: <b>{format_amount(get_int(session, 'wallet_withdraw_min'))}</b> تومان\n"
            f"🔼 حداکثر: <b>{format_amount(get_int(session, 'wallet_withdraw_max'))}</b> تومان",
            parse_mode="HTML", reply_markup=None
        )
        await _set_wallet_reply_keyboard(context, user.telegram_id, label="🔙 برگشت")
        return

    if action == "withdraw_confirm":
        state = _state(context)
        if not state or state.get("type") != "withdraw_confirm_draft" or not _state_matches(context, user.telegram_id):
            await query.answer("اطلاعات برداشت منقضی یا پاک شده است.", show_alert=True); return
        amount = int(state.get("amount"))
        destination = str(state.get("destination") or "").strip()
        if not destination:
            _clear_state(context); await query.answer("مقصد برداشت خالی است.", show_alert=True); return
        tx, err = create_withdrawal(session, user.telegram_id, amount, destination)
        if err:
            await query.answer(f"❌ {err}", show_alert=True); return
        session.commit(); _clear_state(context)
        _wallet_nav_reset(context, "account_settings", "wallet")
        await query.answer("✅ برداشت ثبت شد.", show_alert=True)
        # ابتدا خود پنل کیف پول را نمایش بده، سپس پیام حامل Reply Keyboard/کیسه پول ارسال شود.
        await query.edit_message_text(_wallet_home_text(session, user.telegram_id), parse_mode="HTML", reply_markup=None)
        context.user_data["wallet_panel_message"] = {"chat_id": int(query.message.chat_id), "message_id": int(query.message.message_id)}
        await _set_wallet_reply_keyboard(context, user.telegram_id, label="💰 کیف پول", icon="💰")
        await _send_owner_withdrawal(tx, context)
        return

    if action == "withdraw_edit_draft":
        state = _state(context)
        if not state or state.get("type") != "withdraw_confirm_draft" or not _state_matches(context, user.telegram_id):
            await query.answer("پیش‌نویس برداشت پیدا نشد.", show_alert=True); return
        amount = state.get("amount")
        _set_state(context, user.telegram_id, {"type": "withdraw_amount", "previous_amount": amount})
        await query.answer()
        await query.edit_message_text("✏️ <b>ویرایش مبلغ برداشت</b>\n\nمبلغ جدید را به تومان ارسال کنید.", parse_mode="HTML", reply_markup=None)
        await _set_wallet_reply_keyboard(context, user.telegram_id, label="🔙 برگشت")
        return

    if action == "withdraw_cancel_draft":
        state = _state(context)
        if state and state.get("type") == "withdraw_confirm_draft" and _state_matches(context, user.telegram_id):
            _clear_state(context)
            _wallet_nav_reset(context, "account_settings", "wallet")
            await query.answer("درخواست برداشت لغو شد.", show_alert=True)
            await query.edit_message_text("🚫 <b>درخواست برداشت لغو شد.</b>\n\nهیچ مبلغی از کیف پول شما کسر یا رزرو نشد.", parse_mode="HTML", reply_markup=None)
            await _set_wallet_reply_keyboard(context, user.telegram_id, label="💰 کیف پول", icon="💰")
            return
        await query.answer("پیش‌نویس برداشت پیدا نشد.", show_alert=True)
        return

    if action == "transactions":
        page = int(parts[2]) if len(parts) >= 3 else 1
        _wallet_nav_set_current(context, "transactions")
        _clear_state(context)
        rows, page, pages = list_transactions(session, user.telegram_id, page)
        if not rows:
            await query.answer("📭 تراکنشی وجود ندارد.", show_alert=True)
            return
        await query.answer(); await query.edit_message_text("📜 <b>تراکنش‌های کیف پول</b>\n━━━━━━━━━━━━━━━━━━\nسوابق کیف پول شما:", parse_mode="HTML", reply_markup=transaction_list_keyboard(rows, page, pages)); return

    if action == "tx" and len(parts) >= 3:
        tx = get_user_transaction(session, user.telegram_id, int(parts[2]))
        if not tx:
            await query.answer("📭 چنین تراکنشی وجود ندارد.", show_alert=True); return
        page = int(parts[3]) if len(parts) >= 4 and parts[3].isdigit() else 1
        # جزئیات تراکنش فقط مسیر Inline است و نباید سطح جدیدی برای ReplyKeyboard بسازد.
        _wallet_nav_set_current(context, "transactions")
        await query.answer(); await query.edit_message_text(_wallet_tx_text(session, tx), parse_mode="HTML", reply_markup=wallet_back_inline(f"wallet:transactions:{page}"))
        return


def _wallet_owner_stats_text(stats):
    methods = stats.get("by_method") or {}
    labels = {
        "card": "💳 کارت‌به‌کارت",
        "card_to_card": "💳 کارت‌به‌کارت",
        "zarinpal": "🏦 زرین‌پال",
        "crypto": "₿ رمز ارز",
        "stars": "⭐ استارز",
    }
    lines = [
        "📊 <b>آمار کیف پول و پرداخت‌ها</b>",
        "━━━━━━━━━━━━━━━━━━",
        f"👛 تعداد کیف پول‌ها: <b>{stats.get('wallets', 0):,}</b>",
        f"💰 مجموع موجودی کاربران: <b>{format_amount(stats.get('balance', 0))}</b> تومان",
        f"🔒 موجودی رزروشده: <b>{format_amount(stats.get('reserved', 0))}</b> تومان",
        f"🧾 کل تراکنش‌ها: <b>{stats.get('transactions', 0):,}</b>",
        "",
        f"✅ افزایش‌های تأییدشده: <b>{stats.get('deposits_count', 0):,}</b> مورد — <b>{format_amount(stats.get('deposits_amount', 0))}</b> تومان",
        f"📤 برداشت‌های تکمیل‌شده: <b>{stats.get('withdrawals_count', 0):,}</b> مورد — <b>{format_amount(stats.get('withdrawals_amount', 0))}</b> تومان",
        f"⏳ درخواست‌های در انتظار: <b>{stats.get('pending_count', 0):,}</b> مورد — <b>{format_amount(stats.get('pending_amount', 0))}</b> تومان",
        f"❌ ردشده: <b>{stats.get('rejected_count', 0):,}</b>",
        f"🚫 لغوشده: <b>{stats.get('cancelled_count', 0):,}</b>",
        f"⏰ منقضی‌شده: <b>{stats.get('expired_count', 0):,}</b>",
    ]
    if methods:
        lines += ["", "💳 <b>تفکیک افزایش موجودی بر اساس روش</b>"]
        for code, row in sorted(methods.items()):
            label = labels.get(code, code)
            lines.append(f"{label}: <b>{row.get('count', 0):,}</b> مورد — <b>{format_amount(row.get('amount', 0))}</b> تومان")
    lines.append("━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)


def _owner_wallet_general_text(session):
    status = "🟢 فعال" if get_bool(session, WALLET_ENABLED) else "🔴 غیرفعال"
    return (
        "⚙️ <b>تنظیمات عمومی کیف پول</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"👛 وضعیت کیف پول: <b>{status}</b>\n"
        f"⏳ مهلت هر درخواست پرداخت: <b>{get_int(session, WALLET_PAYMENT_EXPIRY_MINUTES)}</b> دقیقه\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "برای تغییر هر مورد، دکمه همان مورد را بزنید."
    )


def _owner_wallet_payment_methods_text(session):
    def st(key):
        return "🟢 فعال" if get_bool(session, key) else "🔴 غیرفعال"
    return (
        "💳 <b>تنظیمات افزایش موجودی</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"💳 کارت‌به‌کارت: <b>{st(WALLET_CARD_ENABLED)}</b>\n"
        f"🏦 درگاه زرین‌پال: <b>{st(ZP_ENABLED)}</b>\n"
        f"₿ رمز ارز: <b>{st(CRYPTO_ENABLED)}</b>\n"
        f"⭐ استارز: <b>{st(STARS_ENABLED)}</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "هر روش تنظیمات مخصوص خودش را دارد."
    )


def _owner_wallet_card_payment_text(session):
    cards = active_cards(session)
    all_cards = list(session.scalars(select(WalletCard).order_by(WalletCard.sort_order, WalletCard.id)).all())
    return (
        "💳 <b>تنظیمات کارت‌به‌کارت</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🟢 وضعیت کارت‌به‌کارت: <b>{'فعال' if get_bool(session, WALLET_CARD_ENABLED) else 'غیرفعال'}</b>\n"
        f"🔄 حالت چرخشی: <b>{'فعال' if get_bool(session, WALLET_CARD_ROTATION) else 'غیرفعال'}</b>\n"
        f"💳 تعداد کل کارت‌ها: <b>{len(all_cards):,}</b>\n"
        f"🟢 کارت‌های فعال: <b>{len(cards):,}</b>\n"
        f"💰 حداقل مبلغ: <b>{format_amount(get_int(session, 'wallet_card_min'))}</b> تومان\n"
        f"💰 حداکثر مبلغ: <b>{format_amount(get_int(session, 'wallet_card_max'))}</b> تومان\n"
        f"🔢 بازه مبلغ شناسایی: <b>{format_amount(get_int(session, 'wallet_card_identifier_min'))}</b> تا <b>{format_amount(get_int(session, 'wallet_card_identifier_max'))}</b> تومان\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "این کارت‌ها همان کارت‌هایی هستند که کاربر برای افزایش موجودی کارت‌به‌کارت به آن‌ها واریز می‌کند."
    )


def _owner_wallet_gateway_text(session):
    if not get_bool(session, ZP_ENABLED):
        gateway_status = "🔴 غیرفعال"
    elif zarinpal_configuration_ready(session):
        gateway_status = "🟢 فعال"
    else:
        gateway_status = "🟠 فعال ولی ناقص؛ تنظیمات سرور/مرچنت کامل نیست"
    return (
        "🏦 <b>تنظیمات درگاه زرین‌پال</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"وضعیت درگاه: <b>{gateway_status}</b>\n"
        f"🪪 شناسه پذیرنده: <code>{_html(get_setting(session, ZP_MERCHANT_ID, 'ثبت نشده'))}</code>\n"
        f"➕ درصد افزایش مبلغ: <b>{get_float(session, ZP_MARKUP_PERCENT, 0, 1000):g}%</b>\n"
        f"🔽 حداقل: <b>{format_amount(get_int(session, ZP_MIN))}</b> تومان\n"
        f"🔼 حداکثر: <b>{format_amount(get_int(session, ZP_MAX))}</b> تومان\n"
        f"📝 توضیحات: <b>{_html(get_setting(session, ZP_DESCRIPTION, 'ثبت نشده'))}</b>\n"
        "━━━━━━━━━━━━━━━━━━"
    )


def _owner_wallet_crypto_text(session, destinations=None):
    from services.crypto_gateway import crypto_gateway_configured, CRYPTO_CLIENT_ID, CRYPTO_CLIENT_SECRET, CRYPTO_WEBHOOK_ENABLED
    ready = crypto_gateway_configured(session)
    client_id = get_setting(session, CRYPTO_CLIENT_ID, "")
    secret = get_setting(session, CRYPTO_CLIENT_SECRET, "")
    return (
        "₿ <b>تنظیمات درگاه رمز ارز</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🟢 وضعیت: <b>{'فعال' if get_bool(session, CRYPTO_ENABLED) else 'غیرفعال'}</b>\n"
        f"🔐 وضعیت تنظیمات اتصال: <b>{'آماده' if ready else 'ناقص'}</b>\n"
        f"🔑 شناسه اتصال: <code>{_html(client_id[:8] + '…' if client_id else 'ثبت نشده')}</code>\n"
        f"🔐 کلید محرمانه: <b>{'ثبت شده' if secret else 'ثبت نشده'}</b>\n"
        f"➕ درصد افزایش: <b>{get_float(session, CRYPTO_MARKUP_PERCENT, 0, 1000):g}%</b>\n"
        f"🔽 حداقل: <b>{format_amount(get_int(session, CRYPTO_MIN))}</b> تومان\n"
        f"🔼 حداکثر: <b>{format_amount(get_int(session, CRYPTO_MAX))}</b> تومان\n"
        f"🌐 وب‌هوک: <b>{'فعال' if get_bool(session, CRYPTO_WEBHOOK_ENABLED) else 'غیرفعال'}</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🪙 ارزهای فعال: BTC، TON و USDT (شبکه TRC20)\n"
        "ℹ️ در صورت نبود وب‌هوک عمومی HTTPS، ربات وضعیت فاکتورها را با Polling بررسی می‌کند."
    )


def _owner_wallet_stars_text(session):
    return (
        "⭐ <b>تنظیمات استارز</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🟢 وضعیت استارز: <b>{'فعال' if get_bool(session, STARS_ENABLED) else 'غیرفعال'}</b>\n"
        f"💰 ارزش داخلی هر استار: <b>{format_amount(get_int(session, STARS_TOMAN_RATE))}</b> تومان\n"
        f"🔽 حداقل: <b>{format_amount(get_int(session, STARS_MIN))}</b> تومان اعتبار\n"
        f"🔼 حداکثر: <b>{format_amount(get_int(session, STARS_MAX))}</b> تومان اعتبار\n"
        f"📝 توضیحات فاکتور: <b>{_html(get_setting(session, STARS_DESCRIPTION, 'ثبت نشده'))}</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "ارزش استار در این ربات نرخ داخلی Owner است، نه قیمت بازار."
    )


def _owner_wallet_withdraw_text(session):
    limit = get_int(session, WITHDRAW_DAILY_COUNT_LIMIT, 0)
    limit_text = "بدون محدودیت" if limit == 0 else f"{limit:,} برداشت در روز برای هر کاربر"
    return (
        "📤 <b>تنظیمات برداشت</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🟢 وضعیت برداشت: <b>{'فعال' if get_bool(session, WITHDRAW_ENABLED) else 'غیرفعال'}</b>\n"
        "💳 روش برداشت: <b>کارت‌به‌کارت</b>\n"
        f"🔽 حداقل: <b>{format_amount(get_int(session, 'wallet_withdraw_min'))}</b> تومان\n"
        f"🔼 حداکثر: <b>{format_amount(get_int(session, 'wallet_withdraw_max'))}</b> تومان\n"
        f"🔢 سقف تعداد برداشت روزانه هر کاربر: <b>{limit_text}</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "بعد از ثبت درخواست، مبلغ همان لحظه از موجودی قابل‌مصرف کسر و برای اونر رزرو می‌شود. با ارسال رسید پرداخت توسط اونر، برداشت تکمیل می‌شود."
    )


def _owner_panel_snapshot(context, query):
    context.user_data["wallet_owner_panel"] = {
        "chat_id": int(query.message.chat_id),
        "message_id": int(query.message.message_id),
    }


def _owner_target(session, callback):
    """Return (text, inline_markup) for the panel to restore after an Owner input is saved."""
    if callback == "owner:wallet":
        return ("💰 <b>مدیریت کیف پول و پرداخت‌ها</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "از این بخش می‌توانید وضعیت کیف پول، تنظیمات افزایش موجودی، برداشت، درخواست‌ها و آمار را مدیریت کنید.\n"
            "اطلاعات کارت‌های دریافت واریز داخل تنظیمات کارت‌به‌کارت مدیریت می‌شود.\n\n"
            "بخش موردنظر را انتخاب کنید."), owner_wallet_keyboard(session)
    if callback == "owner:wallet_general":
        return _owner_wallet_general_text(session), owner_wallet_general_keyboard(session)
    if callback == "owner:wallet_payment_methods":
        return _owner_wallet_payment_methods_text(session), owner_wallet_payment_methods_keyboard(session)
    if callback == "owner:wallet_card_payment" or callback == "owner:wallet_cards":
        return _owner_wallet_card_payment_text(session), owner_card_payment_keyboard(session)
    if callback == "owner:wallet_cards_list":
        cards = list(session.scalars(select(WalletCard).order_by(WalletCard.sort_order, WalletCard.id)).all())
        if not cards:
            return "📭 <b>لیست کارت‌ها</b>\n━━━━━━━━━━━━━━━━━━\nهنوز هیچ کارت دریافت واریزی ثبت نشده است.", wallet_back_inline("owner:wallet_card_payment")
        return "📋 <b>لیست کارت‌های دریافت واریز</b>\n━━━━━━━━━━━━━━━━━━\nهر کارت را جداگانه انتخاب کنید.", owner_wallet_cards_keyboard(cards)
    if callback == "owner:wallet_cards_delete":
        cards = list(session.scalars(select(WalletCard).order_by(WalletCard.sort_order, WalletCard.id)).all())
        if not cards:
            return "📭 <b>حذف کارت‌ها</b>\n━━━━━━━━━━━━━━━━━━\nکارت فعالی برای حذف وجود ندارد.", wallet_back_inline("owner:wallet_card_payment")
        return "🗑 <b>حذف کارت‌ها</b>\n━━━━━━━━━━━━━━━━━━\nکارت موردنظر را انتخاب کنید.", owner_wallet_card_delete_keyboard(cards)
    if callback == "owner:wallet_gateway":
        return _owner_wallet_gateway_text(session), owner_wallet_gateway_keyboard(session)
    if callback == "owner:wallet_crypto":
        dests = list(session.scalars(select(WalletCryptoDestination).order_by(WalletCryptoDestination.coin, WalletCryptoDestination.network, WalletCryptoDestination.id)).all())
        return _owner_wallet_crypto_text(session, dests), owner_wallet_crypto_keyboard(session, dests)
    if callback == "owner:wallet_stars":
        return _owner_wallet_stars_text(session), owner_wallet_stars_keyboard(session)
    if callback == "owner:wallet_manual":
        return "💸 <b>واریز / برداشت دستی کاربران</b>\n━━━━━━━━━━━━━━━━━━\nنوع عملیات را انتخاب کنید.", owner_wallet_manual_keyboard()
    if callback == "owner:wallet_withdraw":
        return _owner_wallet_withdraw_text(session), owner_wallet_withdraw_keyboard(session)
    if callback == "owner:wallet_request_settings":
        return "📋 <b>تنظیمات درخواست‌ها</b>\n━━━━━━━━━━━━━━━━━━\nوضعیت‌های درخواست و جستجوی شماره درخواست از اینجا قابل مشاهده است.", owner_wallet_request_settings_keyboard()
    m = re.fullmatch(r"owner:wallet_requests:(pending|approved|rejected):(\d+)", callback or "")
    if m:
        group, page = m.group(1), int(m.group(2))
        rows, page, pages = list_owner_requests(session, group, page, 10)
        titles = {"pending":"⏳ درخواست‌های در انتظار", "approved":"✅ درخواست‌های تأییدشده", "rejected":"❌ درخواست‌های ردشده"}
        return f"{titles[group]}\n━━━━━━━━━━━━━━━━━━\nصفحه {page} از {pages}", owner_request_list_keyboard(rows, page, pages, group) if rows else owner_wallet_request_settings_keyboard()
    m = re.fullmatch(r"owner:wallet_card:(\d+)", callback or "")
    if m:
        card = session.get(WalletCard, int(m.group(1)))
        if card:
            return f"💳 <b>کارت دریافت واریز</b>\n━━━━━━━━━━━━━━━━━━\n{card_text(card)}\n\n🟢 وضعیت: <b>{'فعال' if card.enabled else 'غیرفعال'}</b>", owner_wallet_card_detail_keyboard(card)
    m = re.fullmatch(r"owner:wallet_crypto_dest:(\d+)", callback or "")
    if m:
        dest = session.get(WalletCryptoDestination, int(m.group(1)))
        if dest:
            text = f"🪙 <b>{_html(dest.coin)} / {_html(dest.network)}</b>\n━━━━━━━━━━━━━━━━━━\n📍 <code>{_html(dest.address)}</code>\n✅ تأییدیه: <b>{dest.confirmations_required}</b>\n🟢 وضعیت: <b>{'فعال' if dest.enabled else 'غیرفعال'}</b>\n📝 {_html(dest.description)}"
            return text, owner_wallet_crypto_dest_detail_keyboard(dest)
    m = re.fullmatch(r"owner:wallet_request_tx:(\d+):(pending|approved|rejected)", callback or "")
    if m:
        tx = session.get(WalletTransaction, int(m.group(1)))
        if tx:
            return _wallet_tx_text(session, tx), owner_request_detail_keyboard(tx, back_callback=f"owner:wallet_requests:{m.group(2)}:1")
    if callback == "owner:wallet_stats":
        return _wallet_owner_stats_text(wallet_admin_stats(session)), owner_wallet_stats_keyboard()
    return None, None


async def _owner_callback(update, context, query, session, data):
    _owner_panel_snapshot(context, query)
    parts = data.split(":")
    action = parts[1] if len(parts) > 1 else ""
    if action == "noop":
        await query.answer(); return
    if action == "wallet":
        ensure_owner_defaults(session)
        await query.answer(); await query.edit_message_text(
            "💰 <b>مدیریت کیف پول و پرداخت‌ها</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "از اینجا وضعیت کیف پول، تنظیمات افزایش موجودی، برداشت، درخواست‌های پرداخت و آمار مالی را مدیریت کنید.\n"
            "اطلاعات کارت‌های دریافت واریز داخل <b>تنظیمات کارت‌به‌کارت</b> قرار دارد و از این صفحه دکمه جداگانه‌ای ندارد.\n\n"
            "بخش موردنظر را انتخاب کنید.",
            parse_mode="HTML", reply_markup=owner_wallet_keyboard(session)
        ); session.commit(); return
    if action == "wallet_toggle" and len(parts) == 2:
        key = WALLET_ENABLED
        set_bool(session, key, not get_bool(session, key)); session.commit()
        await query.answer("🟢 فعال شد." if get_bool(session, key) else "🔴 غیرفعال شد.", show_alert=True)
        await query.edit_message_text(_owner_wallet_general_text(session), parse_mode="HTML", reply_markup=owner_wallet_general_keyboard(session)); return
    if action == "wallet_manual":
        if len(parts) == 2:
            await query.answer(); await query.edit_message_text("💸 <b>واریز / برداشت دستی کاربران</b>\n━━━━━━━━━━━━━━━━━━\nنوع عملیات را انتخاب کنید.", parse_mode="HTML", reply_markup=owner_wallet_manual_keyboard()); return
        op=parts[2]
        if op not in {"deposit","withdraw"}:
            await query.answer("❌ عملیات نامعتبر است.", show_alert=True); return
        await query.answer(); await query.edit_message_text(f"{'➕ واریز دستی' if op=='deposit' else '➖ برداشت دستی'}\n\nحالت انجام عملیات را انتخاب کنید.", parse_mode="HTML", reply_markup=owner_wallet_manual_mode_keyboard(op)); return
    if action == "wallet_manual_mode" and len(parts) >= 4:
        op, mode = parts[2], parts[3]
        if op not in {"deposit","withdraw"} or mode not in {"single","multiple"}:
            await query.answer("❌ گزینه نامعتبر است.", show_alert=True); return
        state={"type":"owner_manual_wallet","action":op,"mode":mode,"users":[],"step":"user","panel_chat_id":int(query.message.chat_id),"panel_message_id":int(query.message.message_id)}
        _set_state(context, query.message.chat_id, state, "wallet_owner_state")
        context.user_data[_waiting_scope_key("wallet_owner_state")]=int(update.effective_chat.id)
        await query.answer(); await query.edit_message_text(
            f"{'➕ واریز' if op=='deposit' else '➖ برداشت'} {'یک کاربر' if mode=='single' else 'چند کاربر'}\n\n"
            "آیدی عددی، یوزرنیم، شماره تلفن یا نام کشور را ارسال کنید.",
            parse_mode="HTML", reply_markup=owner_wallet_manual_users_keyboard(op,0)
        ); return
    if action == "wallet_manual_more" and len(parts) >= 3:
        state=context.user_data.get("wallet_owner_state") or {}
        if state.get("type")!="owner_manual_wallet" or state.get("mode")!="multiple":
            await query.answer("⚠️ انتخاب کاربران فعال نیست.",show_alert=True); return
        state["step"]="user"; _set_state(context, query.message.chat_id, state, "wallet_owner_state")
        await query.answer(); await query.edit_message_text("👤 کاربر بعدی را با آیدی، یوزرنیم، شماره تلفن یا نام کشور ارسال کنید.", reply_markup=owner_wallet_manual_users_keyboard(state.get("action"),len(state.get("users") or []))); return
    if action == "wallet_manual_finish" and len(parts) >= 3:
        state=context.user_data.get("wallet_owner_state") or {}
        users=state.get("users") or []
        if state.get("type")!="owner_manual_wallet" or not users:
            await query.answer("⚠️ حداقل یک کاربر انتخاب کنید.",show_alert=True); return
        state["step"]="amount"; _set_state(context, query.message.chat_id, state, "wallet_owner_state")
        context.user_data[_waiting_scope_key("wallet_owner_state")]=int(update.effective_chat.id)
        await query.answer(); await query.edit_message_text("💰 مبلغ را به تومان ارسال کنید.", parse_mode="HTML", reply_markup=wallet_back_inline("owner:wallet_manual")); return
    if action == "wallet_manual_confirm":
        preview=context.user_data.get("wallet_owner_manual_preview") or {}
        user_ids=[int(x) for x in preview.get("users") or []]; amount=int(preview.get("amount") or 0); op=preview.get("action")
        if not user_ids or amount<=0 or op not in {"deposit","withdraw"}:
            await query.answer("❌ عملیات منقضی شده است.",show_alert=True); return
        users=[get_user_by_telegram_id(session,uid) for uid in user_ids]
        if any(u is None for u in users):
            await query.answer("❌ یکی از کاربران پیدا نشد.",show_alert=True); return
        if op=="withdraw":
            lacking=[uid for uid in user_ids if int(ensure_wallet(session,uid).balance or 0) < amount]
            if lacking:
                await query.answer("❌ موجودی یکی از کاربران برای برداشت کافی نیست.",show_alert=True); return
        for uid in user_ids:
            wallet=ensure_wallet(session,uid)
            before=int(wallet.balance or 0)
            tx=new_transaction(session,uid,"deposit" if op=="deposit" else "withdrawal","owner_manual",amount,metadata={"owner_id":int(query.from_user.id),"manual":True})
            if op=="deposit":
                wallet.balance=before+amount; wallet.total_deposits=int(wallet.total_deposits or 0)+amount
            else:
                wallet.balance=before-amount; wallet.total_withdrawals=int(wallet.total_withdrawals or 0)+amount
            after=int(wallet.balance)
            tx.status=STATUS_APPROVED; tx.requested_amount=amount; tx.payment_amount=amount; tx.credited_amount=amount if op=="deposit" else 0; tx.verified_amount=amount; tx.balance_before=before; tx.balance_after=after; tx.reserved_before=int(wallet.reserved_balance or 0); tx.reserved_after=int(wallet.reserved_balance or 0); tx.completed_at=datetime.utcnow(); tx.updated_at=datetime.utcnow()
            save_metadata(tx,{"owner_id":int(query.from_user.id),"manual":True,"action":op})
        session.commit()
        context.user_data.pop("wallet_owner_manual_preview",None); _clear_state(context,"wallet_owner_state")
        for uid in user_ids:
            try:
                current=int(ensure_wallet(session,uid).balance or 0)
                await context.bot.send_message(chat_id=uid,text=(f"✅ <b>موجودی شما توسط اونر {'افزایش' if op=='deposit' else 'کاهش'} یافت.</b>\n\n💰 مبلغ: <b>{format_amount(amount)}</b> تومان\n💳 موجودی جدید: <b>{format_amount(current)}</b> تومان"),parse_mode="HTML")
            except Exception: pass
        await query.answer("✅ عملیات با موفقیت انجام شد.",show_alert=True)
        await query.edit_message_text("✅ <b>عملیات انجام شد.</b>\n\nبخش بعدی را انتخاب کنید.",parse_mode="HTML",reply_markup=owner_wallet_manual_keyboard()); return
    if action == "wallet_manual_edit":
        preview=context.user_data.get("wallet_owner_manual_preview") or {}
        if not preview:
            await query.answer("❌ عملیات منقضی شده است.",show_alert=True); return
        users=preview.get("users") or []; op=preview.get("action","deposit")
        state={"type":"owner_manual_wallet","action":op,"mode":"multiple" if len(users)>1 else "single","users":[int(x) for x in users],"step":"amount","panel_chat_id":int(query.message.chat_id),"panel_message_id":int(query.message.message_id)}
        _set_state(context, query.message.chat_id, state, "wallet_owner_state"); context.user_data.pop("wallet_owner_manual_preview",None)
        await query.answer(); await query.edit_message_text("💰 مبلغ جدید را به تومان ارسال کنید.",reply_markup=wallet_back_inline("owner:wallet_manual")); return
    if action == "wallet_manual_cancel":
        context.user_data.pop("wallet_owner_manual_preview",None); _clear_state(context,"wallet_owner_state")
        await query.answer("لغو شد."); await query.edit_message_text("💸 <b>واریز / برداشت دستی کاربران</b>\n━━━━━━━━━━━━━━━━━━\nنوع عملیات را انتخاب کنید.",parse_mode="HTML",reply_markup=owner_wallet_manual_keyboard()); return
    if action == "wallet_general":
        await query.answer(); await query.edit_message_text(_owner_wallet_general_text(session), parse_mode="HTML", reply_markup=owner_wallet_general_keyboard(session)); return
    if action in {"wallet_identifier_range", "wallet_identifier_edit", "wallet_card_identifier_range", "wallet_card_identifier_edit"}:
        _set_state(context, query.message.chat_id, {"type": "owner_identifier_min", "back": "owner:wallet_card_payment"}, "wallet_owner_state")
        await query.answer()
        await query.edit_message_text(
            "🔢 <b>بازه مبلغ شناسایی</b>\n\n"
            f"حداقل فعلی: <b>{format_amount(get_int(session, 'wallet_card_identifier_min'))}</b> تومان\n"
            f"حداکثر فعلی: <b>{format_amount(get_int(session, 'wallet_card_identifier_max'))}</b> تومان\n\n"
            "ابتدا <b>حداقل</b> مبلغ را فقط به‌صورت عدد ارسال کنید.",
            parse_mode="HTML", reply_markup=wallet_back_inline("owner:wallet_card_payment")
        )
        return

    if action == "wallet_edit" and len(parts) >= 3:
        field = parts[2]
        mapping = {
            "deposit_min": ("حداقل افزایش موجودی", "wallet_deposit_min", "int"),
            "deposit_max": ("حداکثر افزایش موجودی", "wallet_deposit_max", "int"),
            "expiry": ("مهلت پرداخت به دقیقه", WALLET_PAYMENT_EXPIRY_MINUTES, "int"),
        }
        if field == "daily_limit":
            await query.answer("این تنظیم حذف شده است؛ سقف روزانه بر اساس تعداد برداشت هر کاربر در بخش برداشت قرار دارد.", show_alert=True); return
        if field not in mapping:
            await query.answer("گزینه نامعتبر است.", show_alert=True); return
        label, key, typ = mapping[field]
        _set_state(context, query.message.chat_id, {"type": "owner_setting", "key": key, "label": label, "cast": typ, "back": "owner:wallet_general"}, "wallet_owner_state")
        await query.answer(); await query.edit_message_text(f"⚙️ <b>{_html(label)}</b>\n\nمقدار جدید را ارسال کنید.", parse_mode="HTML", reply_markup=wallet_back_inline("owner:wallet_general")); return
    if action == "wallet_card_edit" and len(parts) >= 3:
        field = parts[2]
        mapping = {
            "min": ("حداقل مبلغ کارت‌به‌کارت", "wallet_card_min"),
            "max": ("حداکثر مبلغ کارت‌به‌کارت", "wallet_card_max"),
        }
        if field not in mapping:
            await query.answer("گزینه نامعتبر است.", show_alert=True); return
        label, key = mapping[field]
        _set_state(context, query.message.chat_id, {"type": "owner_setting", "key": key, "label": label, "cast": "int", "back": "owner:wallet_card_payment"}, "wallet_owner_state")
        await query.answer()
        await query.edit_message_text(
            f"⚙️ <b>{_html(label)}</b>\n\nمقدار جدید را به تومان ارسال کنید.",
            parse_mode="HTML", reply_markup=wallet_back_inline("owner:wallet_card_payment")
        )
        return
    if action == "wallet_card_enabled_toggle":
        set_bool(session, WALLET_CARD_ENABLED, not get_bool(session, WALLET_CARD_ENABLED)); session.commit()
        await query.answer("🟢 کارت‌به‌کارت فعال شد." if get_bool(session, WALLET_CARD_ENABLED) else "🔴 کارت‌به‌کارت غیرفعال شد.", show_alert=True)
        await query.edit_message_text(_owner_wallet_card_payment_text(session), parse_mode="HTML", reply_markup=owner_card_payment_keyboard(session))
        return
    if action == "wallet_card_rotation":
        set_bool(session, WALLET_CARD_ROTATION, not get_bool(session, WALLET_CARD_ROTATION)); session.commit()
        await query.answer("🔄 حالت چرخشی تغییر کرد.", show_alert=True)
        await query.edit_message_text(_owner_wallet_card_payment_text(session), parse_mode="HTML", reply_markup=owner_card_payment_keyboard(session))
        return
    if data.startswith("owner:wallet_toggle:") and len(parts) >= 3:
        if parts[2] in {"receipt_text", "receipt_image"}:
            await query.answer("🧾 رسید متنی و تصویری همیشه فعال هستند و نیازی به تنظیم جداگانه ندارند.", show_alert=True)
            await query.edit_message_text(_owner_wallet_card_payment_text(session), parse_mode="HTML", reply_markup=owner_card_payment_keyboard(session))
            return
    if action == "wallet_payment_methods":
        await query.answer()
        await query.edit_message_text(_owner_wallet_payment_methods_text(session), parse_mode="HTML", reply_markup=owner_wallet_payment_methods_keyboard(session))
        return
    if action == "wallet_card_payment":
        await query.answer()
        await query.edit_message_text(_owner_wallet_card_payment_text(session), parse_mode="HTML", reply_markup=owner_card_payment_keyboard(session))
        return
    if action == "wallet_cards":
        await query.answer()
        await query.edit_message_text(_owner_wallet_card_payment_text(session), parse_mode="HTML", reply_markup=owner_card_payment_keyboard(session))
        return
    if action == "wallet_cards_list":
        cards = list(session.scalars(select(WalletCard).order_by(WalletCard.sort_order, WalletCard.id)).all())
        if not cards:
            await query.answer("📭 کارتی ثبت نشده است.", show_alert=True)
            return
        await query.answer(); await query.edit_message_text("📋 <b>لیست کارت‌ها</b>\n\nهر کارت جداگانه نمایش داده شده است.", parse_mode="HTML", reply_markup=owner_wallet_cards_keyboard(cards)); return
    if action == "wallet_cards_delete":
        cards = list(session.scalars(select(WalletCard).order_by(WalletCard.sort_order, WalletCard.id)).all())
        if not cards:
            await query.answer("📭 کارتی برای حذف وجود ندارد.", show_alert=True)
            return
        await query.answer(); await query.edit_message_text("🗑 <b>حذف کارت‌ها</b>\n\nکارت موردنظر را انتخاب کنید.", parse_mode="HTML", reply_markup=owner_wallet_card_delete_keyboard(cards)); return
    if action == "wallet_card_add":
        card_add_back = "owner:wallet_cards_list" if len(parts) >= 3 and parts[2] == "list" else "owner:wallet_card_payment"
        _set_state(context, query.message.chat_id, {"type": "owner_card_add", "step": "card_number", "back": card_add_back, "data": {}}, "wallet_owner_state")
        await query.answer(); await query.edit_message_text("➕ <b>افزودن کارت</b>\n\nشماره کارت را ارسال کنید.", parse_mode="HTML", reply_markup=wallet_back_inline(card_add_back)); return
    if action.startswith("wallet_card_add_skip"):
        state = _state(context, "wallet_owner_state") or {}
        if state.get("type") != "owner_card_add":
            await query.answer("❌ مرحله افزودن کارت منقضی شده است.", show_alert=True); return
        field = parts[2] if len(parts) >= 3 else ""
        labels = {"bank": "بانک", "iban": "شبا", "account": "شماره حساب", "description": "توضیحات"}
        if field not in labels:
            await query.answer("❌ گزینه نامعتبر است.", show_alert=True); return
        data_map = dict(state.get("data") or {})
        data_map[field] = None
        next_field = {"bank": "iban", "iban": "account", "account": "description", "description": "confirm"}.get(field)
        state["data"] = data_map
        if next_field == "confirm":
            _clear_state(context, "wallet_owner_state")
            context.user_data["wallet_card_draft"] = {"mode": "add", "back": state.get("back", "owner:wallet_card_payment"), **data_map}
            await query.answer(); await query.edit_message_text(_card_draft_text(context.user_data["wallet_card_draft"]), parse_mode="HTML", reply_markup=owner_card_draft_confirm_keyboard())
            return
        state["step"] = next_field
        context.user_data["wallet_owner_state"] = state
        await query.answer(); await query.edit_message_text(_card_step_prompt(next_field), parse_mode="HTML", reply_markup=owner_card_skip_keyboard(next_field, state.get("back", "owner:wallet_card_payment")) if next_field in {"bank","iban","account","description"} else wallet_back_inline(state.get("back", "owner:wallet_card_payment"))); return

    if action == "wallet_card_add_confirm" and len(parts) >= 3:
        if parts[2] == "cancel":
            context.user_data.pop("wallet_card_draft", None)
            await query.answer("لغو شد.", show_alert=True)
            await query.edit_message_text(_owner_wallet_card_payment_text(session), parse_mode="HTML", reply_markup=owner_card_payment_keyboard(session)); return
        if parts[2] == "edit":
            draft = context.user_data.get("wallet_card_draft") or {}
            back = draft.get("back", "owner:wallet_card_payment")
            mode = "owner_card_edit" if draft.get("mode") == "edit" else "owner_card_add"
            state = {"type": mode, "step": "card_number", "back": back, "data": {}}
            if draft.get("card_id"): state["card_id"] = draft["card_id"]
            context.user_data.pop("wallet_card_draft", None)
            _set_state(context, query.message.chat_id, state, "wallet_owner_state")
            await query.answer(); await query.edit_message_text("✏️ <b>ویرایش کارت</b>\n\nشماره کارت را دوباره ارسال کنید.", parse_mode="HTML", reply_markup=wallet_back_inline(back)); return
        if parts[2] == "save":
            draft = context.user_data.get("wallet_card_draft") or {}
            if not draft.get("card_number") or not draft.get("owner_name"):
                await query.answer("❌ اطلاعات اصلی کارت ناقص است.", show_alert=True); return
            if draft.get("mode") == "edit" and draft.get("card_id"):
                card = session.get(WalletCard, int(draft["card_id"]))
                if not card:
                    await query.answer("❌ کارت پیدا نشد.", show_alert=True); return
                card.card_number = draft["card_number"]
                card.owner_name = draft["owner_name"]
                card.bank_name = draft.get("bank") or "ثبت نشده"
                card.iban = draft.get("iban")
                card.account_number = draft.get("account")
                card.description = draft.get("description")
                card.updated_at = datetime.utcnow()
                session.commit()
                context.user_data.pop("wallet_card_draft", None)
                await query.answer("✅ اطلاعات کارت ویرایش شد.", show_alert=True)
                await query.edit_message_text(f"💳 <b>کارت دریافت واریز</b>\n━━━━━━━━━━━━━━━━━━\n{card_text(card)}\n\n🟢 وضعیت: <b>{'فعال' if card.enabled else 'غیرفعال'}</b>", parse_mode="HTML", reply_markup=owner_wallet_card_detail_keyboard(card)); return
            next_order = int(session.scalar(select(WalletCard.id).order_by(WalletCard.id.desc()).limit(1)) or 0) + 1
            card = WalletCard(card_number=draft["card_number"], owner_name=draft["owner_name"], bank_name=draft.get("bank") or "ثبت نشده", iban=draft.get("iban"), account_number=draft.get("account"), description=draft.get("description"), enabled=True, sort_order=next_order)
            session.add(card); session.commit(); context.user_data.pop("wallet_card_draft", None)
            await query.answer("✅ کارت با موفقیت ثبت شد.", show_alert=True)
            await query.edit_message_text(_owner_wallet_card_payment_text(session), parse_mode="HTML", reply_markup=owner_card_payment_keyboard(session)); return

    if action == "wallet_card" and len(parts) >= 3:
        card = session.get(WalletCard, int(parts[2]))
        if not card: await query.answer("کارت پیدا نشد.", show_alert=True); return
        text = f"💳 <b>کارت دریافت واریز</b>\n━━━━━━━━━━━━━━━━━━\n{card_text(card)}\n\n📌 وضعیت کارت: <b>{'فعال' if card.enabled else 'غیرفعال'}</b>\n\nاز دکمه وضعیت پایین می‌توانید کارت را فعال یا غیرفعال کنید."
        await query.answer(); await query.edit_message_text(text, parse_mode="HTML", reply_markup=owner_wallet_card_detail_keyboard(card)); return
    if action == "wallet_card_toggle" and len(parts) >= 3:
        card = session.get(WalletCard, int(parts[2]))
        if not card: await query.answer("کارت پیدا نشد.", show_alert=True); return
        card.enabled = not bool(card.enabled); session.commit(); await query.answer("وضعیت کارت تغییر کرد.", show_alert=True)
        await query.edit_message_text(f"💳 <b>کارت</b>\n\n{card_text(card)}\n\nوضعیت: <b>{'فعال' if card.enabled else 'غیرفعال'}</b>", parse_mode="HTML", reply_markup=owner_wallet_card_detail_keyboard(card)); return
    if action == "wallet_card_delete" and len(parts) >= 3:
        card = session.get(WalletCard, int(parts[2]))
        if not card:
            await query.answer("کارت پیدا نشد.", show_alert=True); return
        await query.answer()
        await query.edit_message_text(
            "🗑 <b>تأیید حذف کارت</b>\n━━━━━━━━━━━━━━━━━━\n"
            f"{card_text(card)}\n\n"
            "آیا از حذف این کارت مطمئن هستید؟",
            parse_mode="HTML",
            reply_markup=owner_wallet_card_delete_confirm_keyboard(card),
        )
        return
    if action == "wallet_card_delete_confirm" and len(parts) >= 4:
        card_id = int(parts[2])
        decision = parts[3]
        if decision == "no":
            cards = list(session.scalars(select(WalletCard).order_by(WalletCard.sort_order, WalletCard.id)).all())
            await query.answer("لغو شد.", show_alert=True)
            if cards:
                await query.edit_message_text("🗑 <b>حذف کارت‌ها</b>\n━━━━━━━━━━━━━━━━━━\nکارت موردنظر را انتخاب کنید.", parse_mode="HTML", reply_markup=owner_wallet_card_delete_keyboard(cards))
            else:
                await query.edit_message_text(_owner_wallet_card_payment_text(session), parse_mode="HTML", reply_markup=owner_card_payment_keyboard(session))
            return
        if decision != "yes":
            await query.answer("گزینه نامعتبر است.", show_alert=True); return
        card = session.get(WalletCard, card_id)
        if not card:
            await query.answer("کارت قبلاً حذف شده است.", show_alert=True); return
        session.delete(card); session.commit()
        cards = list(session.scalars(select(WalletCard).order_by(WalletCard.sort_order, WalletCard.id)).all())
        await query.answer("✅ کارت حذف شد.", show_alert=True)
        if cards:
            await query.edit_message_text("🗑 <b>حذف کارت‌ها</b>\n━━━━━━━━━━━━━━━━━━\nکارت موردنظر را انتخاب کنید.", parse_mode="HTML", reply_markup=owner_wallet_card_delete_keyboard(cards))
        else:
            await query.edit_message_text(_owner_wallet_card_payment_text(session), parse_mode="HTML", reply_markup=owner_card_payment_keyboard(session))
        return
    if action == "wallet_card_edit" and len(parts) >= 3:
        card = session.get(WalletCard, int(parts[2]))
        if not card: await query.answer("کارت پیدا نشد.", show_alert=True); return
        _set_state(context, query.message.chat_id, {"type": "owner_card_edit", "step": "card_number", "card_id": card.id, "back": f"owner:wallet_card:{card.id}", "data": {}}, "wallet_owner_state")
        await query.answer(); await query.edit_message_text("✏️ <b>ویرایش کارت</b>\n\nشماره کارت ۱۶ رقمی را ارسال کنید.", parse_mode="HTML", reply_markup=wallet_back_inline(f"owner:wallet_card:{card.id}")); return

    if action == "wallet_gateway":
        await query.answer(); await query.edit_message_text(_owner_wallet_gateway_text(session), parse_mode="HTML", reply_markup=owner_wallet_gateway_keyboard(session)); session.commit(); return
    if action == "wallet_gateway_toggle" and len(parts) >= 3:
        if parts[2] != "enabled":
            await query.answer("درگاه زرین‌پال فقط در حالت واقعی کار می‌کند.", show_alert=True)
            return
        if not get_bool(session, ZP_ENABLED) and not zarinpal_configuration_ready(session):
            await query.answer("ابتدا شناسه پذیرنده را ثبت کنید و تنظیم فنی Callback سرور را کامل کنید.", show_alert=True)
            return
        set_bool(session, ZP_ENABLED, not get_bool(session, ZP_ENABLED))
        session.commit(); await query.answer("تنظیم تغییر کرد.", show_alert=True); await query.edit_message_text(_owner_wallet_gateway_text(session), parse_mode="HTML", reply_markup=owner_wallet_gateway_keyboard(session)); return
    if action == "wallet_gateway_edit" and len(parts) >= 3:
        field = parts[2]
        fields = {
            "merchant": ("شناسه پذیرنده", ZP_MERCHANT_ID, "text"), "markup": ("درصد افزایش مبلغ درگاه", ZP_MARKUP_PERCENT, "float"),
            "min": ("حداقل مبلغ درگاه", ZP_MIN, "int"), "max": ("حداکثر مبلغ درگاه", ZP_MAX, "int"),
            "description": ("توضیحات پرداخت", ZP_DESCRIPTION, "text"),
        }
        if field not in fields: await query.answer("گزینه نامعتبر است.", show_alert=True); return
        label, key, cast = fields[field]
        _set_state(context, query.message.chat_id, {"type": "owner_setting", "key": key, "label": label, "cast": cast, "back": "owner:wallet_gateway"}, "wallet_owner_state")
        await query.answer(); await query.edit_message_text(f"⚙️ <b>{_html(label)}</b>\n\nمقدار جدید را ارسال کنید.", parse_mode="HTML", reply_markup=wallet_back_inline("owner:wallet_gateway")); return

    if action == "wallet_crypto":
        await query.answer(); await query.edit_message_text(_owner_wallet_crypto_text(session, []), parse_mode="HTML", reply_markup=owner_wallet_crypto_keyboard(session)); return
    if action == "wallet_crypto_toggle" and len(parts) >= 3:
        if parts[2] == "webhook":
            set_bool(session, CRYPTO_WEBHOOK_ENABLED, not get_bool(session, CRYPTO_WEBHOOK_ENABLED))
        else:
            if not crypto_gateway_configured(session):
                await query.answer("ابتدا شناسه اتصال و کلید محرمانه را ثبت کنید.", show_alert=True); return
            set_bool(session, CRYPTO_ENABLED, not get_bool(session, CRYPTO_ENABLED))
        session.commit()
        await query.answer("تنظیم تغییر کرد.", show_alert=True); await query.edit_message_text(_owner_wallet_crypto_text(session, []), parse_mode="HTML", reply_markup=owner_wallet_crypto_keyboard(session)); return
    if action == "wallet_crypto_test":
        try:
            from services.crypto_gateway import _request_sync
            await asyncio.to_thread(_request_sync, session, "GET", "/v2/merchant/invoices?limit=1")
            await query.answer("✅ اتصال CoinPayments موفق است.", show_alert=True)
        except Exception as exc:
            await query.answer(f"❌ اتصال ناموفق: {str(exc)[:180]}", show_alert=True)
        return
    if action == "wallet_crypto_edit" and len(parts) >= 3:
        fields = {
            "client_id": ("شناسه اتصال CoinPayments", CRYPTO_CLIENT_ID, "text"),
            "client_secret": ("کلید محرمانه CoinPayments", CRYPTO_CLIENT_SECRET, "text"),
            "markup": ("درصد افزایش مبلغ رمز ارز", CRYPTO_MARKUP_PERCENT, "float"),
            "min": ("حداقل مبلغ رمز ارز", CRYPTO_MIN, "int"),
            "max": ("حداکثر مبلغ رمز ارز", CRYPTO_MAX, "int"),
        }
        field = parts[2]
        if field not in fields: await query.answer("گزینه نامعتبر است.", show_alert=True); return
        label, key, cast = fields[field]
        _set_state(context, query.message.chat_id, {"type": "owner_setting", "key": key, "label": label, "cast": cast, "back": "owner:wallet_crypto"}, "wallet_owner_state")
        await query.answer(); await query.edit_message_text(f"⚙️ <b>{_html(label)}</b>\n\nمقدار جدید را ارسال کنید.", parse_mode="HTML", reply_markup=wallet_back_inline("owner:wallet_crypto")); return

    if action == "wallet_stars":
        await query.answer(); await query.edit_message_text(_owner_wallet_stars_text(session), parse_mode="HTML", reply_markup=owner_wallet_stars_keyboard(session)); return
    if action == "wallet_stars_toggle":
        set_bool(session, STARS_ENABLED, not get_bool(session, STARS_ENABLED)); session.commit(); await query.answer("وضعیت استارز به‌روزرسانی شد.", show_alert=True); await query.edit_message_text(_owner_wallet_stars_text(session), parse_mode="HTML", reply_markup=owner_wallet_stars_keyboard(session)); return
    if action == "wallet_stars_edit" and len(parts) >= 3:
        fields = {"rate": ("ارزش داخلی هر استار به تومان", STARS_TOMAN_RATE, "int"), "min": ("حداقل مبلغ استارز", STARS_MIN, "int"), "max": ("حداکثر مبلغ استارز", STARS_MAX, "int"), "description": ("توضیحات فاکتور استارز", STARS_DESCRIPTION, "text")}
        field = parts[2]
        if field not in fields: await query.answer("گزینه نامعتبر است.", show_alert=True); return
        label, key, cast = fields[field]
        _set_state(context, query.message.chat_id, {"type": "owner_setting", "key": key, "label": label, "cast": cast, "back": "owner:wallet_stars"}, "wallet_owner_state")
        await query.answer(); await query.edit_message_text(f"⚙️ <b>{_html(label)}</b>\n\nمقدار جدید را ارسال کنید.", parse_mode="HTML", reply_markup=wallet_back_inline("owner:wallet_stars")); return
    if action == "wallet_stars_balance":
        try:
            balance = await context.bot.get_my_star_balance()
            value = getattr(balance, "amount", balance)
            await query.answer(f"موجودی استارز ربات: {value}", show_alert=True)
        except Exception as exc:
            await query.answer(f"خطا در دریافت موجودی استارز: {exc}", show_alert=True)
        return

    if action == "wallet_withdraw_edit" and len(parts) >= 3:
        fields = {
            "min": ("حداقل برداشت", "wallet_withdraw_min", "int"),
            "max": ("حداکثر برداشت", "wallet_withdraw_max", "int"),
            "daily_count": ("سقف تعداد برداشت روزانه هر کاربر", WITHDRAW_DAILY_COUNT_LIMIT, "int"),
        }
        field = parts[2]
        if field not in fields:
            await query.answer("گزینه نامعتبر است.", show_alert=True); return
        label, key, cast = fields[field]
        _set_state(context, query.message.chat_id, {"type": "owner_setting", "key": key, "label": label, "cast": cast, "back": "owner:wallet_withdraw"}, "wallet_owner_state")
        await query.answer()
        if field in {"min", "max"}:
            current_text = f"{format_amount(get_int(session, key))} تومان"
        else:
            current_text = f"{get_int(session, key):,} برداشت در روز برای هر کاربر" if get_int(session, key) else "بدون محدودیت"
        await query.edit_message_text(
            f"⚙️ <b>{_html(label)}</b>\n\n"
            f"مقدار فعلی: <b>{current_text}</b>\n\n"
            "مقدار جدید را ارسال کنید.",
            parse_mode="HTML", reply_markup=wallet_back_inline("owner:wallet_withdraw")
        )
        return

    if action == "wallet_withdraw_toggle" and len(parts) >= 3:
        set_bool(session, WITHDRAW_ENABLED, not get_bool(session, WITHDRAW_ENABLED)); session.commit()
        await query.answer("تنظیم وضعیت برداشت به‌روزرسانی شد.", show_alert=True)
        await query.edit_message_text(_owner_wallet_withdraw_text(session), parse_mode="HTML", reply_markup=owner_wallet_withdraw_keyboard(session)); return
    if action == "wallet_withdraw":
        await query.answer(); await query.edit_message_text(_owner_wallet_withdraw_text(session), parse_mode="HTML", reply_markup=owner_wallet_withdraw_keyboard(session)); return

    if action == "wallet_request_settings":
        await query.answer()
        await query.edit_message_text("📋 <b>تنظیمات درخواست‌ها</b>\n━━━━━━━━━━━━━━━━━━\nاز اینجا می‌توانید درخواست‌های در انتظار، تأییدشده و ردشده را ببینید یا با شماره درخواست جستجو کنید.", parse_mode="HTML", reply_markup=owner_wallet_request_settings_keyboard())
        return
    if action == "wallet_requests" and len(parts) >= 3:
        group = parts[2] if parts[2] in {"pending", "approved", "rejected"} else "pending"
        page = int(parts[3]) if len(parts) >= 4 and parts[3].isdigit() else 1
        rows, page, pages = list_owner_requests(session, group, page, 10)
        if not rows:
            labels = {"pending": "درخواستی در انتظار وجود ندارد.", "approved": "درخواست تأییدشده‌ای وجود ندارد.", "rejected": "درخواست ردشده‌ای وجود ندارد."}
            await query.answer("📭 " + labels[group], show_alert=True)
            return
        titles = {"pending": "⏳ درخواست‌های در انتظار", "approved": "✅ درخواست‌های تأییدشده", "rejected": "❌ درخواست‌های ردشده"}
        await query.answer()
        await query.edit_message_text(f"{titles[group]}\n━━━━━━━━━━━━━━━━━━\nصفحه {page} از {pages}", parse_mode="HTML", reply_markup=owner_request_list_keyboard(rows, page, pages, group))
        return
    if action == "wallet_request_tx" and len(parts) >= 3:
        tx = session.get(WalletTransaction, int(parts[2]))
        group = parts[3] if len(parts) >= 4 and parts[3] in {"pending", "approved", "rejected"} else "pending"
        if not tx:
            await query.answer("📭 درخواستی وجود ندارد یا حذف شده است.", show_alert=True)
            return
        if group == "approved" and tx.status != STATUS_APPROVED:
            await query.answer("این درخواست دیگر در فهرست تأییدشده‌ها نیست.", show_alert=True); return
        if group == "rejected" and tx.status != STATUS_REJECTED:
            await query.answer("این درخواست دیگر در فهرست ردشده‌ها نیست.", show_alert=True); return
        await query.answer()
        await query.edit_message_text(_wallet_tx_text(session, tx), parse_mode="HTML", reply_markup=owner_request_detail_keyboard(tx, back_callback=f"owner:wallet_requests:{group}:1"))
        return
    if action == "wallet_request_search":
        _set_state(context, query.message.chat_id, {"type": "owner_request_search", "back": "owner:wallet_request_settings"}, "wallet_owner_state")
        await query.answer()
        await query.edit_message_text("🔎 <b>جستجوی درخواست</b>\n\nشماره درخواست را ارسال کنید؛ مثلاً <code>WLT-20260925-0001</code>.", parse_mode="HTML", reply_markup=owner_search_request_keyboard())
        return
    if action == "wallet_stats":
        stats = wallet_admin_stats(session)
        await query.answer()
        await query.edit_message_text(_wallet_owner_stats_text(stats), parse_mode="HTML", reply_markup=owner_wallet_stats_keyboard())
        return
    if action == "wallet_pending":
        page = int(parts[2]) if len(parts) >= 3 else 1
        rows, page, pages = get_pending_owner_transactions(session, page)
        if not rows:
            await query.answer("📭 درخواستی موجود نیست.", show_alert=True)
            return
        await query.answer(); await query.edit_message_text("📋 <b>درخواست‌های در انتظار</b>", parse_mode="HTML", reply_markup=owner_pending_transactions_keyboard(rows, page, pages)); return
    if action == "wallet_pending_tx" and len(parts) >= 3:
        tx = session.get(WalletTransaction, int(parts[2]))
        if not tx: await query.answer("تراکنش پیدا نشد.", show_alert=True); return
        if tx.kind == "withdrawal":
            markup = owner_withdraw_action_keyboard(tx.id)
        else:
            markup = owner_deposit_action_keyboard(tx.id)
        await query.answer(); await _edit_query_text_or_caption(query, _wallet_tx_text(session, tx), parse_mode="HTML", reply_markup=markup); return
    if action == "wallet_approve" and len(parts) >= 3:
        tx = session.get(WalletTransaction, int(parts[2]))
        if not tx: await query.answer("تراکنش پیدا نشد.", show_alert=True); return
        if tx.status != STATUS_WAITING_OWNER:
            await query.answer("این تراکنش دیگر قابل تأیید نیست.", show_alert=True); return
        if transaction_is_expired(tx):
            tx.status = STATUS_EXPIRED; clear_identifier(tx); session.commit()
            await query.answer("⏰ مهلت تراکنش تمام شده است.", show_alert=True); return
        amount = int(tx.requested_amount)
        preview = context.user_data.get("wallet_owner_edit_preview")
        if preview and int(preview.get("tx_id", 0)) == tx.id:
            amount = int(preview.get("amount", amount))
        if tx.method == "card" and amount > int(tx.requested_amount):
            await query.answer("مبلغ نهایی نمی‌تواند بیشتر از مبلغ درخواستی باشد.", show_alert=True); return
        ok, err = approve_deposit(session, tx, amount, external_reference=tx.external_id)
        if not ok: await query.answer(f"❌ {err}", show_alert=True); return
        session.commit(); context.user_data.pop("wallet_owner_edit_preview", None); _clear_state(context, "wallet_owner_state")
        await query.answer("✅ تراکنش تأیید شد.", show_alert=True)
        await _edit_query_text_or_caption(query, _wallet_tx_text(session, tx), parse_mode="HTML", reply_markup=wallet_back_inline("owner:wallet_requests:pending:1"))
        try:
            await context.bot.send_message(chat_id=tx.user_id, text=f"✅ <b>افزایش موجودی تأیید شد.</b>\n\n🧾 تراکنش: <code>{tx.transaction_no}</code>\n💰 مبلغ اضافه‌شده: <b>{format_amount(tx.credited_amount)}</b> تومان", parse_mode="HTML")
        except Exception:
            pass
        return
    if action == "wallet_edit_tx" and len(parts) >= 3:
        tx = session.get(WalletTransaction, int(parts[2]))
        if not tx or tx.status != STATUS_WAITING_OWNER:
            await query.answer("قابل ویرایش نیست.", show_alert=True); return
        _set_state(context, query.message.chat_id, {"type": "owner_edit_tx", "tx_id": tx.id}, "wallet_owner_state")
        await query.answer(); await _edit_query_text_or_caption(query, f"✏️ <b>ویرایش مبلغ تراکنش</b>\n\nمبلغ فعلی اعتبار: <b>{format_amount(tx.requested_amount)}</b> تومان\n\nمبلغ نهایی اعتبار را ارسال کنید.", parse_mode="HTML", reply_markup=wallet_back_inline(f"owner:wallet_request_tx:{tx.id}:pending")); return
    if action == "wallet_edit_confirm" and len(parts) >= 3:
        preview = context.user_data.get("wallet_owner_edit_preview")
        tx = session.get(WalletTransaction, int(parts[2]))
        if not tx or not preview or int(preview.get("tx_id", 0)) != tx.id:
            await query.answer("ویرایش پیدا نشد.", show_alert=True); return
        amount = int(preview.get("amount", 0))
        if transaction_is_expired(tx):
            tx.status = STATUS_EXPIRED; clear_identifier(tx); session.commit()
            await query.answer("⏰ مهلت تراکنش تمام شده است.", show_alert=True); return
        if tx.method == "card" and amount > int(tx.requested_amount):
            await query.answer("مبلغ نهایی نمی‌تواند بیشتر از مبلغ درخواستی باشد.", show_alert=True); return
        ok, err = approve_deposit(session, tx, amount, external_reference=tx.external_id)
        if not ok: await query.answer(f"❌ {err}", show_alert=True); return
        context.user_data.pop("wallet_owner_edit_preview", None); _clear_state(context, "wallet_owner_state"); session.commit()
        await query.answer("✅ مبلغ و تراکنش تأیید شد.", show_alert=True); await _edit_query_text_or_caption(query, _wallet_tx_text(session, tx), parse_mode="HTML", reply_markup=wallet_back_inline("owner:wallet_requests:pending:1"))
        try: await context.bot.send_message(chat_id=tx.user_id, text=f"✅ افزایش موجودی تأیید شد.\n\nمبلغ نهایی: {format_amount(tx.credited_amount)} تومان")
        except Exception: pass
        return
    if action == "wallet_reject" and len(parts) >= 3:
        tx = session.get(WalletTransaction, int(parts[2]))
        if not tx or tx.status != STATUS_WAITING_OWNER:
            await query.answer("قابل رد نیست.", show_alert=True); return
        await query.answer(); await _edit_query_text_or_caption(query, _wallet_tx_text(session, tx) + "\n\n❌ <b>دلیل رد را انتخاب کنید.</b>", parse_mode="HTML", reply_markup=owner_rejection_keyboard(tx.id)); return
    if action == "wallet_reject_no_reason" and len(parts) >= 3:
        tx = session.get(WalletTransaction, int(parts[2]))
        if not tx or tx.status != STATUS_WAITING_OWNER:
            await query.answer("قابل رد نیست.", show_alert=True); return
        context.user_data["wallet_owner_rejection_preview"] = {"tx_id": tx.id, "reason": ""}
        await query.answer()
        await _edit_query_text_or_caption(query, "❌ <b>رد بدون دلیل</b>\n\nآیا می‌خواهید این درخواست بدون ثبت دلیل رد شود؟", parse_mode="HTML", reply_markup=owner_rejection_confirm_keyboard(tx.id))
        return
    if action == "wallet_reject_reason" and len(parts) >= 3:
        tx = session.get(WalletTransaction, int(parts[2]))
        if not tx or tx.status != STATUS_WAITING_OWNER:
            await query.answer("قابل رد نیست.", show_alert=True); return
        _set_state(context, query.message.chat_id, {"type": "owner_rejection_reason", "tx_id": tx.id}, "wallet_owner_state")
        await query.answer(); await _edit_query_text_or_caption(query, "✍️ دلیل رد را ارسال کنید.", reply_markup=wallet_back_inline(f"owner:wallet_request_tx:{tx.id}:pending")); return
    if action == "wallet_reject_confirm_reason" and len(parts) >= 3:
        preview = context.user_data.get("wallet_owner_rejection_preview") or {}
        tx = session.get(WalletTransaction, int(parts[2]))
        if not tx or tx.status != STATUS_WAITING_OWNER or int(preview.get("tx_id", 0)) != tx.id:
            await query.answer("این رد دیگر قابل اجرا نیست.", show_alert=True); return
        reason = str(preview.get("reason") or "").strip()
        ok, _ = reject_transaction(session, tx, reason or None); session.commit()
        context.user_data.pop("wallet_owner_rejection_preview", None); _clear_state(context, "wallet_owner_state")
        if ok:
            try:
                notice = "❌ <b>درخواست شما رد شد.</b>"
                if reason:
                    notice += f"\n\n📝 دلیل:\n{_html(reason)}"
                await context.bot.send_message(chat_id=tx.user_id, text=notice, parse_mode="HTML")
            except Exception: pass
        await query.answer("❌ تراکنش رد شد.", show_alert=True)
        await _edit_query_text_or_caption(query, "❌ <b>تراکنش رد شد.</b>", parse_mode="HTML", reply_markup=wallet_back_inline("owner:wallet_requests:pending:1")); return
    if action == "wallet_reject_withdraw" and len(parts) >= 3:
        tx = session.get(WalletTransaction, int(parts[2]))
        if tx:
            ok, _ = reject_transaction(session, tx, "برداشت توسط اونر رد شد."); session.commit()
            if ok:
                try: await context.bot.send_message(chat_id=tx.user_id, text="❌ درخواست برداشت شما رد شد و مبلغ رزرو‌شده به موجودی برگردانده شد.")
                except Exception: pass
        await query.answer("برداشت رد شد.", show_alert=True); await _edit_query_text_or_caption(query, "❌ برداشت رد شد.", reply_markup=wallet_back_inline("owner:wallet_requests:pending:1")); return
    if action == "wallet_withdraw_receipt" and len(parts) >= 3:
        tx = session.get(WalletTransaction, int(parts[2]))
        if not tx or tx.status != STATUS_WAITING_OWNER:
            await query.answer("این برداشت دیگر قابل پرداخت نیست.", show_alert=True); return
        _set_state(context, query.message.chat_id, {"type": "owner_withdrawal_receipt", "tx_id": tx.id}, "wallet_owner_state")
        await query.answer(); await _edit_query_text_or_caption(query, "📤 رسید واریز را به‌صورت متن یا تصویر ارسال کنید.", reply_markup=wallet_back_inline(f"owner:wallet_request_tx:{tx.id}:pending")); return


def ensure_owner_defaults(session):
    from services.wallet import ensure_wallet_defaults
    ensure_wallet_defaults(session)
    # Do not force-create a withdrawal method if Owner previously deleted all methods.
    session.commit()


def _crypto_dest_step_prompt(step, coin=None):
    prompts = {
        "network": f"🌐 <b>شبکه {escape(str(coin or ''))}</b>\n\nنام دقیق شبکه را ارسال کنید. برای USDT مثلاً <code>TRC20</code>.",
        "address": "📍 <b>آدرس مقصد</b>\n\nآدرس کیف پولی که وجه باید به آن ارسال شود را ارسال کنید.",
        "confirmations": "✅ <b>تعداد تأییدیه موردنیاز</b>\n\nمثلاً برای ۱ تأیید، عدد <code>1</code> را ارسال کنید.",
        "description": "📝 <b>توضیحات مقصد</b>\n\nتوضیح اختیاری را ارسال کنید یا گزینه «⏭ بدون توضیحات» را بزنید.",
    }
    return prompts.get(step, "⚙️ اطلاعات مقصد را وارد کنید.")

def _crypto_dest_draft_text(draft):
    return (
        "🪙 <b>بررسی مقصد رمز ارز</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🪙 ارز: <b>{escape(str(draft.get('coin') or ''))}</b>\n"
        f"🌐 شبکه: <b>{escape(str(draft.get('network') or ''))}</b>\n"
        f"📍 آدرس: <code>{escape(str(draft.get('address') or ''))}</code>\n"
        f"✅ تأییدیه: <b>{int(draft.get('confirmations') or 0)}</b>\n"
        f"📝 توضیحات: <b>{escape(str(draft.get('description') or 'ثبت نشده'))}</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "اطلاعات صحیح است؟"
    )

async def _owner_show_crypto_dest_draft(context, session, chat_id):
    draft = context.user_data.get("wallet_crypto_dest_draft") or {}
    panel = context.user_data.get("wallet_owner_panel") or {}
    text = _crypto_dest_draft_text(draft); markup = owner_crypto_dest_draft_confirm_keyboard()
    if panel.get("message_id"):
        try:
            await context.bot.edit_message_text(chat_id=int(panel.get("chat_id", chat_id)), message_id=int(panel["message_id"]), text=text, parse_mode="HTML", reply_markup=markup); return
        except Exception: pass
    await context.bot.send_message(chat_id=int(chat_id), text=text, parse_mode="HTML", reply_markup=markup)

def _card_step_prompt(step):
    prompts = {
        "card_number": "💳 <b>افزودن کارت</b>\n\nشماره کارت ۱۶ رقمی را ارسال کنید.",
        "owner_name": "👤 <b>نام صاحب کارت</b>\n\nنام صاحب کارت را ارسال کنید.",
        "bank": "🏦 <b>نام بانک</b>\n\nنام بانک را ارسال کنید یا گزینه «⏭ بدون بانک» را بزنید.",
        "iban": "🏷️ <b>شماره شبا</b>\n\nشماره شبا را ارسال کنید یا گزینه «⏭ بدون شبا» را بزنید.",
        "account": "🔢 <b>شماره حساب</b>\n\nشماره حساب را ارسال کنید یا گزینه «⏭ بدون شماره حساب» را بزنید.",
        "description": "📝 <b>توضیحات کارت</b>\n\nتوضیحات را ارسال کنید یا گزینه «⏭ بدون توضیحات» را بزنید.",
    }
    return prompts.get(step, "⚙️ مقدار موردنظر را ارسال کنید.")

def _card_draft_text(draft):
    def v(key):
        value = draft.get(key)
        return _html(value) if value else "ثبت نشده"
    return (
        "💳 <b>بررسی اطلاعات کارت</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"💳 شماره کارت: <code>{v('card_number')}</code>\n"
        f"👤 نام صاحب: <b>{v('owner_name')}</b>\n"
        f"🏦 بانک: <b>{v('bank')}</b>\n"
        f"🏷️ شبا: <b>{v('iban')}</b>\n"
        f"🔢 شماره حساب: <b>{v('account')}</b>\n"
        f"📝 توضیحات: <b>{v('description')}</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "اطلاعات صحیح است؟"
    )

async def _owner_show_card_draft(context, session, chat_id):
    draft = context.user_data.get("wallet_card_draft") or {}
    panel = context.user_data.get("wallet_owner_panel") or {}
    text = _card_draft_text(draft)
    markup = owner_card_draft_confirm_keyboard()
    if panel.get("message_id"):
        try:
            await context.bot.edit_message_text(chat_id=int(panel.get("chat_id", chat_id)), message_id=int(panel["message_id"]), text=text, parse_mode="HTML", reply_markup=markup)
            return
        except Exception:
            pass
    await context.bot.send_message(chat_id=int(chat_id), text=text, parse_mode="HTML", reply_markup=markup)

async def _delete_owner_input(message):
    try:
        await message.delete()
    except Exception:
        pass


async def _owner_return_after_input(context, session, state):
    callback = state.get("back") or "owner:wallet"
    chat_id = state.get("panel_chat_id") or state.get("chat_id")
    message_id = state.get("panel_message_id")
    if not chat_id or not message_id:
        return
    text, markup = _owner_target(session, callback)
    if not text:
        return
    try:
        await context.bot.edit_message_text(
            chat_id=int(chat_id),
            message_id=int(message_id),
            text=text,
            parse_mode="HTML",
            reply_markup=markup,
        )
    except Exception:
        pass


async def _handle_owner_input(update, context, message, session, state):
    text = (message.text or "").strip()
    typ = state.get("type")
    if typ == "owner_manual_wallet":
        if not text:
            await message.reply_text("❌ ورودی خالی است."); return True
        def resolve_user(raw):
            if raw.isdigit():
                return get_user_by_telegram_id(session,int(raw))
            uname=raw.lstrip("@").casefold()
            if raw.startswith("@") or uname:
                found=next((u for u in get_users(session) if (u.username or "").lstrip("@").casefold()==uname),None)
                if found: return found
            normalized=re.sub(r"\s+","",raw)
            found=next((u for u in get_users(session) if re.sub(r"\s+","",u.phone_number or "") == normalized),None)
            if found: return found
            return next((u for u in get_users(session) if any((c.title or "").strip().casefold()==raw.casefold() for c in get_user_countries(session,u))),None)
        if state.get("step")=="user":
            target=resolve_user(text)
            if target is None:
                await message.reply_text("❌ کاربر پیدا نشد. آیدی، یوزرنیم، شماره تلفن یا نام کشور معتبر ارسال کنید."); return True
            users=[int(x) for x in state.get("users") or []]
            if int(target.telegram_id) not in users: users.append(int(target.telegram_id))
            state["users"]=users
            if state.get("mode")=="single":
                state["step"]="amount"; context.user_data["wallet_owner_state"]=state
                await _delete_owner_input(message)
                await message.reply_text(f"👤 کاربر انتخاب شد: <code>{target.telegram_id}</code>\n\n💰 مبلغ را به تومان ارسال کنید.",parse_mode="HTML",reply_markup=wallet_back_inline("owner:wallet_manual")); return True
            state["step"]="user"; context.user_data["wallet_owner_state"]=state
            await _delete_owner_input(message)
            await message.reply_text(f"✅ کاربر <code>{target.telegram_id}</code> اضافه شد.\n\nکاربر بعدی را ارسال کنید یا «پایان انتخاب کاربران» را بزنید.",parse_mode="HTML",reply_markup=owner_wallet_manual_users_keyboard(state.get("action"),len(users))); return True
        if state.get("step")=="amount":
            try: amount=_parse_amount(text)
            except Exception:
                await message.reply_text("❌ مبلغ نامعتبر است. یک عدد مثبت به تومان ارسال کنید."); return True
            if amount<=0:
                await message.reply_text("❌ مبلغ باید بیشتر از صفر باشد."); return True
            users=[int(x) for x in state.get("users") or []]
            context.user_data["wallet_owner_manual_preview"]={"action":state.get("action"),"users":users,"amount":amount}
            _clear_state(context,"wallet_owner_state"); await _delete_owner_input(message)
            target_text="، ".join(str(x) for x in users); label="واریز" if state.get("action")=="deposit" else "برداشت"
            panel=context.user_data.get("wallet_owner_panel") or {}
            preview=(f"💸 <b>تأیید {label} دستی</b>\n\n👥 کاربران: <code>{target_text}</code>\n💰 مبلغ برای هر کاربر: <b>{format_amount(amount)}</b> تومان\n\nتأیید شود؟")
            if panel.get("message_id"):
                try:
                    await context.bot.edit_message_text(chat_id=int(panel.get("chat_id",message.chat_id)),message_id=int(panel["message_id"]),text=preview,parse_mode="HTML",reply_markup=owner_wallet_manual_confirm_keyboard()); return True
                except Exception: pass
            await message.reply_text(preview,parse_mode="HTML",reply_markup=owner_wallet_manual_confirm_keyboard()); return True
        await message.reply_text("❌ مرحله عملیات نامعتبر است."); return True
    if typ == "owner_setting":
        if not text:
            await message.reply_text("❌ مقدار خالی است."); return True
        key, cast = state.get("key"), state.get("cast")
        if not key or cast not in {"int", "float", "text"}:
            state_copy = dict(state)
            _clear_state(context, "wallet_owner_state")
            await _delete_owner_input(message)
            await _owner_return_after_input(context, session, state_copy)
            return True
        try:
            if cast == "int":
                value = _parse_amount(text)
            elif cast == "float":
                value = float(text.replace("٪", "").replace("%", "").replace(",", "."))
            else:
                value = text.strip()
            if cast in {"int", "float"} and float(value) < 0:
                raise ValueError
            # Keep related ranges logically consistent.
            if key == "wallet_deposit_min" and value > get_int(session, "wallet_deposit_max"):
                raise ValueError
            if key == "wallet_deposit_max" and value < get_int(session, "wallet_deposit_min"):
                raise ValueError
            if key == "wallet_card_min" and value > get_int(session, "wallet_card_max"):
                raise ValueError
            if key == "wallet_card_max" and value < get_int(session, "wallet_card_min"):
                raise ValueError
            if key == "wallet_withdraw_min" and value > get_int(session, "wallet_withdraw_max"):
                raise ValueError
            if key == "wallet_withdraw_max" and value < get_int(session, "wallet_withdraw_min"):
                raise ValueError
            if key == ZP_MIN and int(value) <= 0:
                raise ValueError
            if key == ZP_MAX and (int(value) <= 0 or int(value) < get_int(session, ZP_MIN)):
                raise ValueError
            if key == ZP_MARKUP_PERCENT and float(value) > 1000:
                raise ValueError
            if key in {WALLET_PAYMENT_EXPIRY_MINUTES, WITHDRAW_DAILY_COUNT_LIMIT} and int(value) <= 0:
                raise ValueError
            set_setting(session, key, value); session.commit()
        except Exception:
            await message.reply_text("❌ مقدار نامعتبر است یا با مقدار دیگر این بخش تناقض دارد. دوباره ارسال کنید."); return True
        state_copy = dict(state)
        _clear_state(context, "wallet_owner_state")
        await _delete_owner_input(message)
        await _owner_return_after_input(context, session, state_copy)
        return True

    if typ == "owner_identifier_min":
        try:
            minimum = _parse_amount(text)
            if minimum <= 0:
                raise ValueError
        except Exception:
            await message.reply_text("❌ حداقل مبلغ نامعتبر است. یک عدد مثبت ارسال کنید.")
            return True
        set_setting(session, "wallet_card_identifier_min", minimum)
        session.commit()
        state_copy = dict(state)
        state_copy["type"] = "owner_identifier_max"
        state_copy["identifier_min"] = minimum
        await _delete_owner_input(message)
        context.user_data["wallet_owner_state"] = state_copy
        panel = context.user_data.get("wallet_owner_panel") or {}
        if panel.get("message_id"):
            await context.bot.edit_message_text(
                chat_id=int(panel.get("chat_id", message.chat_id)),
                message_id=int(panel["message_id"]),
                text=(
                    "🔢 <b>بازه مبلغ شناسایی</b>\n\n"
                    f"✅ حداقل ثبت شد: <b>{format_amount(minimum)}</b> تومان\n\n"
                    "اکنون <b>حداکثر</b> مبلغ را فقط به‌صورت عدد ارسال کنید."
                ),
                parse_mode="HTML", reply_markup=wallet_back_inline("owner:wallet_card_payment")
            )
        return True

    if typ == "owner_identifier_max":
        try:
            maximum = _parse_amount(text)
            minimum = int(state.get("identifier_min") or get_int(session, "wallet_card_identifier_min"))
            if maximum < minimum:
                raise ValueError
        except Exception:
            await message.reply_text("❌ حداکثر باید عددی بزرگ‌تر یا مساوی حداقل ثبت‌شده باشد.")
            return True
        set_setting(session, "wallet_card_identifier_max", maximum)
        session.commit()
        state_copy = dict(state)
        state_copy["back"] = "owner:wallet_card_payment"
        _clear_state(context, "wallet_owner_state")
        await _delete_owner_input(message)
        await _owner_return_after_input(context, session, state_copy)
        return True

    if typ == "owner_request_search":
        value = text.strip()
        if not value:
            await message.reply_text("❌ شماره درخواست را ارسال کنید.", reply_markup=owner_search_request_keyboard())
            return True
        tx = search_owner_request(session, value)
        if not tx:
            await message.reply_text("📭 <b>درخواستی با این شماره پیدا نشد.</b>", parse_mode="HTML", reply_markup=owner_search_request_keyboard())
            return True
        group = "approved" if tx.status == STATUS_APPROVED else "rejected" if tx.status == STATUS_REJECTED else "pending"
        state_copy = dict(state)
        state_copy["back"] = f"owner:wallet_request_tx:{tx.id}:{group}"
        _clear_state(context, "wallet_owner_state")
        await _delete_owner_input(message)
        await _owner_return_after_input(context, session, state_copy)
        return True

    if typ in {"owner_card_add", "owner_card_edit"}:
        data_map = dict(state.get("data") or {})
        step = state.get("step", "card_number")
        value = text.strip()
        if not value:
            await message.reply_text("❌ این مقدار نمی‌تواند خالی باشد.")
            return True
        if step == "card_number":
            digits = value.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
            digits = re.sub(r"\D", "", digits)
            if len(digits) != 16:
                await message.reply_text("❌ شماره کارت باید ۱۶ رقم باشد.")
                return True
            data_map["card_number"] = digits
            state["step"] = "owner_name"
        elif step == "owner_name":
            data_map["owner_name"] = value
            state["step"] = "bank"
        elif step in {"bank", "iban", "account", "description"}:
            data_map[step] = value
            state["step"] = {"bank":"iban","iban":"account","account":"description","description":"confirm"}[step]
        else:
            await message.reply_text("❌ مرحله افزودن کارت معتبر نیست.")
            return True
        state["data"] = data_map
        if state["step"] == "confirm":
            _clear_state(context, "wallet_owner_state")
            context.user_data["wallet_card_draft"] = {"mode": typ.replace("owner_card_", ""), "card_id": state.get("card_id"), "back": state.get("back", "owner:wallet_card_payment"), **data_map}
            await _delete_owner_input(message)
            await _owner_show_card_draft(context, session, message.chat_id)
            return True
        context.user_data["wallet_owner_state"] = state
        await _delete_owner_input(message)
        panel = context.user_data.get("wallet_owner_panel") or {}
        if panel.get("message_id"):
            try:
                await context.bot.edit_message_text(chat_id=int(panel.get("chat_id", message.chat_id)), message_id=int(panel["message_id"]), text=_card_step_prompt(state["step"]), parse_mode="HTML", reply_markup=owner_card_skip_keyboard(state["step"], state.get("back", "owner:wallet_card_payment")) if state["step"] in {"bank","iban","account","description"} else wallet_back_inline(state.get("back", "owner:wallet_card_payment")))
                return True
            except Exception:
                pass
        await message.reply_text(_card_step_prompt(state["step"]), parse_mode="HTML", reply_markup=owner_card_skip_keyboard(state["step"], state.get("back", "owner:wallet_card_payment")) if state["step"] in {"bank","iban","account","description"} else wallet_back_inline(state.get("back", "owner:wallet_card_payment")))
        return True

    if typ in {"owner_crypto_dest_add", "owner_crypto_dest_edit"}:
        data_map = dict(state.get("data") or {})
        step = state.get("step", "coin")
        value = text.strip()
        if step == "network":
            if not value:
                await message.reply_text("❌ نام شبکه نمی‌تواند خالی باشد."); return True
            data_map["network"] = value; state["step"] = "address"
        elif step == "address":
            if not value:
                await message.reply_text("❌ آدرس مقصد نمی‌تواند خالی باشد."); return True
            data_map["address"] = value; state["step"] = "confirmations"
        elif step == "confirmations":
            try: confirmations = max(1, int(value))
            except Exception:
                await message.reply_text("❌ تعداد تأییدیه باید یک عدد مثبت باشد."); return True
            data_map["confirmations"] = confirmations; state["step"] = "description"
        elif step == "description":
            data_map["description"] = value; state["step"] = "confirm"
        else:
            await message.reply_text("❌ مرحله مقصد رمز ارز معتبر نیست."); return True
        state["data"] = data_map
        if state["step"] == "confirm":
            _clear_state(context, "wallet_owner_state")
            context.user_data["wallet_crypto_dest_draft"] = {"mode": "edit" if typ == "owner_crypto_dest_edit" else "add", "dest_id": state.get("dest_id"), "back": state.get("back", "owner:wallet_crypto"), **data_map}
            await _delete_owner_input(message); await _owner_show_crypto_dest_draft(context, session, message.chat_id); return True
        context.user_data["wallet_owner_state"] = state
        await _delete_owner_input(message)
        panel = context.user_data.get("wallet_owner_panel") or {}
        prompt = _crypto_dest_step_prompt(state["step"], data_map.get("coin"))
        markup = owner_crypto_dest_step_keyboard(state["step"]) if state["step"] == "description" else wallet_back_inline(state.get("back", "owner:wallet_crypto"))
        if panel.get("message_id"):
            try:
                await context.bot.edit_message_text(chat_id=int(panel.get("chat_id", message.chat_id)), message_id=int(panel["message_id"]), text=prompt, parse_mode="HTML", reply_markup=markup); return True
            except Exception: pass
        await message.reply_text(prompt, parse_mode="HTML", reply_markup=markup); return True

    if typ == "owner_edit_tx":
        try: amount = _parse_amount(text)
        except Exception: await message.reply_text("❌ مبلغ نامعتبر است."); return True
        tx = session.get(WalletTransaction, int(state.get("tx_id")))
        if not tx or tx.status != STATUS_WAITING_OWNER:
            _clear_state(context, "wallet_owner_state"); await message.reply_text("❌ تراکنش دیگر قابل ویرایش نیست."); return True
        if amount <= 0: await message.reply_text("❌ مبلغ باید بیشتر از صفر باشد."); return True
        if tx.kind == "deposit" and tx.method == "card" and amount > int(tx.requested_amount):
            await message.reply_text("❌ مبلغ نهایی کارت‌به‌کارت نمی‌تواند بیشتر از مبلغ اعتبار درخواستی باشد.")
            return True
        context.user_data["wallet_owner_edit_preview"] = {"tx_id": tx.id, "amount": amount}
        _clear_state(context, "wallet_owner_state")
        await message.reply_text(f"✏️ <b>تأیید مبلغ جدید</b>\n\nمبلغ نهایی اعتبار: <b>{format_amount(amount)}</b> تومان\n\nبا تأیید، تراکنش نهایی می‌شود.", parse_mode="HTML", reply_markup=owner_edit_confirm_keyboard(tx.id))
        return True

    if typ == "owner_rejection_reason":
        tx = session.get(WalletTransaction, int(state.get("tx_id")))
        if not tx or tx.status != STATUS_WAITING_OWNER:
            _clear_state(context, "wallet_owner_state"); return True
        reason = text.strip() or ""
        if not reason: await message.reply_text("❌ دلیل نمی‌تواند خالی باشد."); return True
        context.user_data["wallet_owner_rejection_preview"] = {"tx_id": tx.id, "reason": reason}
        _clear_state(context, "wallet_owner_state")
        await message.reply_text(f"❌ <b>پیش‌نمایش رد تراکنش</b>\n\n🧾 تراکنش: <code>{tx.transaction_no}</code>\n📝 دلیل: {_html(reason)}\n\nرد نهایی شود؟", parse_mode="HTML", reply_markup=owner_rejection_confirm_keyboard(tx.id))
        return True

    if typ == "owner_withdrawal_receipt":
        tx = session.get(WalletTransaction, int(state.get("tx_id")))
        if not tx or tx.status != STATUS_WAITING_OWNER:
            _clear_state(context, "wallet_owner_state"); await message.reply_text("❌ برداشت دیگر قابل پردازش نیست."); return True
        if not message.photo and not text:
            await message.reply_text("❌ رسید را به‌صورت متن یا تصویر ارسال کنید."); return True
        file_id = message.photo[-1].file_id if message.photo else None
        receipt_text = message.caption or text
        ok, err = __import__('services.wallet', fromlist=['complete_withdrawal']).complete_withdrawal(session, tx, file_id, receipt_text)
        if not ok:
            await message.reply_text(f"❌ {err}"); return True
        session.commit()
        state_copy = dict(state)
        _clear_state(context, "wallet_owner_state")
        # send receipt to user
        notice = f"✅ <b>برداشت شما پرداخت شد.</b>\n\n🧾 تراکنش: <code>{tx.transaction_no}</code>\n💰 مبلغ پرداختی: <b>{format_amount(tx.requested_amount)}</b> تومان"
        if file_id:
            await context.bot.send_photo(chat_id=tx.user_id, photo=file_id, caption=notice, parse_mode="HTML")
        else:
            await context.bot.send_message(chat_id=tx.user_id, text=notice + f"\n\n🧾 رسید:\n<code>{_html(receipt_text)}</code>", parse_mode="HTML")
        await _delete_owner_input(message)
        state_copy["back"] = f"owner:wallet_request_tx:{tx.id}:pending"
        await _owner_return_after_input(context, session, state_copy)
        return True
    return False


async def wallet_precheckout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.pre_checkout_query
    if not q:
        return
    payload = str(q.invoice_payload or "")
    if not payload.startswith("walletstars:"):
        return
    try:
        tx_id = int(payload.split(":")[1])
    except Exception:
        await q.answer(ok=False, error_message="فاکتور نامعتبر است."); return
    with SessionLocal() as session:
        tx = session.get(WalletTransaction, tx_id)
        if not tx or tx.user_id != q.from_user.id or tx.status != STATUS_WAITING_PAYMENT:
            await q.answer(ok=False, error_message="این فاکتور دیگر معتبر نیست."); return
        if transaction_is_expired(tx):
            tx.status = STATUS_EXPIRED; session.commit(); await q.answer(ok=False, error_message="مهلت این فاکتور تمام شده است."); return
        data = metadata(tx)
        expected = int(data.get("stars_amount") or 0)
        if q.currency != "XTR" or int(q.total_amount or 0) != expected:
            await q.answer(ok=False, error_message="مبلغ فاکتور با درخواست شما مطابقت ندارد."); return
        await q.answer(ok=True)


async def wallet_successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    payment = getattr(message, "successful_payment", None) if message else None
    if not payment or not update.effective_user:
        return
    with SessionLocal() as session:
        payload = str(payment.invoice_payload or "")
        if not payload.startswith("walletstars:"):
            return
        try: tx_id = int(payload.split(":")[1])
        except Exception: return
        tx = session.scalar(select(WalletTransaction).where(WalletTransaction.id == tx_id, WalletTransaction.user_id == update.effective_user.id))
        if not tx:
            return
        charge_id = str(payment.telegram_payment_charge_id or "")
        duplicate = session.scalar(select(WalletTransaction).where(WalletTransaction.external_id == charge_id, WalletTransaction.id != tx.id)) if charge_id else None
        if duplicate:
            return
        if transaction_is_expired(tx) or tx.status != STATUS_WAITING_PAYMENT:
            try:
                await context.bot.refund_star_payment(update.effective_user.id, charge_id)
            except Exception:
                pass
            tx.status = STATUS_EXPIRED
            session.commit()
            await message.reply_text("⏰ این فاکتور منقضی شده بود و اعتبار به کیف پول اضافه نشد.")
            return
        data = metadata(tx)
        expected = int(data.get("stars_amount") or 0)
        if payment.currency != "XTR" or int(payment.total_amount or 0) != expected:
            return
        tx.external_id = charge_id
        tx.external_reference = charge_id
        tx.payment_amount = expected
        ok, err = approve_deposit(session, tx, tx.requested_amount, external_reference=charge_id)
        session.commit()
        if ok:
            await message.reply_text(f"✅ <b>پرداخت استارز موفق بود.</b>\n\n💰 {format_amount(tx.requested_amount)} تومان به کیف پول شما اضافه شد.", parse_mode="HTML")
            await _set_wallet_reply_keyboard(context, update.effective_user.id, label="🔙 برگشت")
        else:
            await message.reply_text(f"❌ {err}")
