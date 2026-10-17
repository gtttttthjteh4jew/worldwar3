from __future__ import annotations

import asyncio
import json
import random
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_CEILING, InvalidOperation

from sqlalchemy import func, select

from config import OWNER_ID, ZARINPAL_CALLBACK_BASE_URL
from database.db import SessionLocal
from services.atomic_claims import claim_once

from database.models import (
    BotSetting,
    User,
    Wallet,
    WalletCard,
    WalletCryptoDestination,
    WalletTransaction,
    WalletWithdrawalMethod,
)


# ---------------------------------------------------------------------------
# Wallet/payment settings
# ---------------------------------------------------------------------------
WALLET_ENABLED = "wallet_enabled"
WALLET_DEPOSIT_MIN = "wallet_deposit_min"
WALLET_DEPOSIT_MAX = "wallet_deposit_max"
WALLET_WITHDRAW_MIN = "wallet_withdraw_min"
WALLET_WITHDRAW_MAX = "wallet_withdraw_max"
WALLET_PAYMENT_EXPIRY_MINUTES = "wallet_payment_expiry_minutes"
WALLET_CARD_ID_MIN = "wallet_card_identifier_min"
WALLET_CARD_ID_MAX = "wallet_card_identifier_max"
WALLET_CARD_MIN = "wallet_card_min"
WALLET_CARD_MAX = "wallet_card_max"
WALLET_CARD_ENABLED = "wallet_card_enabled"
WALLET_CARD_ROTATION = "wallet_card_rotation"
WALLET_CARD_RECEIPT_TEXT = "wallet_card_receipt_text"
WALLET_CARD_RECEIPT_IMAGE = "wallet_card_receipt_image"

ZP_ENABLED = "wallet_zarinpal_enabled"
ZP_MERCHANT_ID = "wallet_zarinpal_merchant_id"
ZP_MARKUP_PERCENT = "wallet_zarinpal_markup_percent"
ZP_DESCRIPTION = "wallet_zarinpal_description"
ZP_MIN = "wallet_zarinpal_min"
ZP_MAX = "wallet_zarinpal_max"

CRYPTO_ENABLED = "wallet_crypto_enabled"
CRYPTO_MARKUP_PERCENT = "wallet_crypto_markup_percent"
CRYPTO_PRICE_SOURCE = "wallet_crypto_price_source"
CRYPTO_USD_TO_IRR_FALLBACK = "wallet_crypto_usd_to_irr_fallback"
CRYPTO_CONFIRMATIONS = "wallet_crypto_confirmations"
CRYPTO_MIN = "wallet_crypto_min"
CRYPTO_MAX = "wallet_crypto_max"

# CoinPayments gateway settings (credentials are entered from the Owner panel).
CRYPTO_CLIENT_ID = "wallet_crypto_client_id"
CRYPTO_CLIENT_SECRET = "wallet_crypto_client_secret"
CRYPTO_API_BASE = "wallet_crypto_api_base"
CRYPTO_FIAT_CURRENCY = "wallet_crypto_fiat_currency"
CRYPTO_WEBHOOK_ENABLED = "wallet_crypto_webhook_enabled"
CRYPTO_POLL_SECONDS = "wallet_crypto_poll_seconds"

STARS_ENABLED = "wallet_stars_enabled"
STARS_TOMAN_RATE = "wallet_stars_toman_rate"
STARS_MIN = "wallet_stars_min"
STARS_MAX = "wallet_stars_max"
STARS_DESCRIPTION = "wallet_stars_description"

WITHDRAW_ENABLED = "wallet_withdraw_enabled"
WITHDRAW_DAILY_COUNT_LIMIT = "wallet_withdraw_daily_count_limit"

DEFAULTS = {
    WALLET_ENABLED: "1",
    WALLET_DEPOSIT_MIN: "10000",
    WALLET_DEPOSIT_MAX: "100000000",
    WALLET_WITHDRAW_MIN: "10000",
    WALLET_WITHDRAW_MAX: "50000000",
    WALLET_PAYMENT_EXPIRY_MINUTES: "30",
    WALLET_CARD_ID_MIN: "100",
    WALLET_CARD_ID_MAX: "999",
    WALLET_CARD_MIN: "10000",
    WALLET_CARD_MAX: "100000000",
    WALLET_CARD_ENABLED: "1",
    WALLET_CARD_ROTATION: "1",
    WALLET_CARD_RECEIPT_TEXT: "1",
    WALLET_CARD_RECEIPT_IMAGE: "1",
    ZP_ENABLED: "0",
    ZP_MERCHANT_ID: "",
    ZP_MARKUP_PERCENT: "0",
    ZP_DESCRIPTION: "افزایش موجودی کیف پول",
    ZP_MIN: "10000",
    ZP_MAX: "100000000",
    CRYPTO_ENABLED: "0",
    CRYPTO_MARKUP_PERCENT: "0",
    CRYPTO_PRICE_SOURCE: "coingecko",
    CRYPTO_USD_TO_IRR_FALLBACK: "0",
    CRYPTO_CONFIRMATIONS: "1",
    CRYPTO_MIN: "10000",
    CRYPTO_MAX: "100000000",
    CRYPTO_CLIENT_ID: "",
    CRYPTO_CLIENT_SECRET: "",
    CRYPTO_API_BASE: "https://a-api.coinpayments.net/api",
    CRYPTO_FIAT_CURRENCY: "USD",
    CRYPTO_WEBHOOK_ENABLED: "1",
    CRYPTO_POLL_SECONDS: "60",
    STARS_ENABLED: "0",
    STARS_TOMAN_RATE: "1000",
    STARS_MIN: "10000",
    STARS_MAX: "10000000",
    STARS_DESCRIPTION: "افزایش موجودی کیف پول با استارز",
    WITHDRAW_ENABLED: "1",
    WITHDRAW_DAILY_COUNT_LIMIT: "1",
}


STATUS_WAITING_PAYMENT = "WAITING_PAYMENT"
STATUS_WAITING_RECEIPT = "WAITING_RECEIPT"
STATUS_WAITING_OWNER = "WAITING_OWNER"
STATUS_WAITING_EDIT = "WAITING_EDIT"
STATUS_WAITING_REJECTION = "WAITING_REJECTION"
STATUS_WAITING_WITHDRAWAL_RECEIPT = "WAITING_WITHDRAWAL_RECEIPT"
STATUS_APPROVED = "APPROVED"
STATUS_REJECTED = "REJECTED"
STATUS_CANCELLED = "CANCELLED"
STATUS_EXPIRED = "EXPIRED"

ACTIVE_DEPOSIT_STATUSES = {
    STATUS_WAITING_PAYMENT,
    STATUS_WAITING_RECEIPT,
    STATUS_WAITING_OWNER,
    STATUS_WAITING_EDIT,
    STATUS_WAITING_REJECTION,
}

SUPPORTED_COINS = {
    "BTC": "bitcoin",
    "USDT": "tether",
    "TON": "the-open-network",
}


def ensure_wallet_defaults(session):
    changed = False
    for key, default in DEFAULTS.items():
        row = session.scalar(select(BotSetting).where(BotSetting.key == key))
        if row is None:
            session.add(BotSetting(key=key, value=str(default)))
            changed = True
    if changed:
        session.flush()


def get_setting(session, key: str, default=None) -> str:
    ensure_wallet_defaults(session)
    row = session.scalar(select(BotSetting).where(BotSetting.key == key))
    return str(row.value) if row is not None else str(default if default is not None else "")


def set_setting(session, key: str, value) -> None:
    row = session.scalar(select(BotSetting).where(BotSetting.key == key))
    if row is None:
        session.add(BotSetting(key=key, value=str(value)))
    else:
        row.value = str(value)


def get_bool(session, key: str) -> bool:
    return get_setting(session, key) in {"1", "true", "True", "yes", "on"}


def set_bool(session, key: str, value: bool) -> None:
    set_setting(session, key, "1" if value else "0")


def get_int(session, key: str, minimum=0) -> int:
    try:
        return max(minimum, int(float(get_setting(session, key))))
    except (TypeError, ValueError):
        return minimum


def set_int(session, key: str, value: int, minimum=0) -> None:
    set_setting(session, key, max(minimum, int(value)))


def get_float(session, key: str, minimum=0.0, maximum=None) -> float:
    try:
        value = max(minimum, float(get_setting(session, key)))
        if maximum is not None:
            value = min(maximum, value)
        return value
    except (TypeError, ValueError):
        return minimum


def set_float(session, key: str, value: float, minimum=0.0, maximum=None) -> None:
    value = max(minimum, float(value))
    if maximum is not None:
        value = min(maximum, value)
    set_setting(session, key, value)


def wallet_enabled(session) -> bool:
    return get_bool(session, WALLET_ENABLED)


def ensure_wallet(session, user_id: int) -> Wallet:
    wallet = session.scalar(select(Wallet).where(Wallet.user_id == int(user_id)))
    if wallet is None:
        wallet = Wallet(user_id=int(user_id))
        session.add(wallet)
        session.flush()
    return wallet


def format_amount(amount: int | float) -> str:
    return f"{int(round(float(amount or 0))):,}"


def _parse_amount(text: str) -> int:
    raw = str(text or "").strip()
    raw = raw.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
    raw = raw.replace(",", "").replace("٬", "").replace(" ", "").replace("_", "")
    if not raw or not re.fullmatch(r"\d+(?:\.0+)?", raw):
        raise ValueError("invalid amount")
    return int(float(raw))


def amount_limits(session, kind="deposit"):
    if kind == "withdraw":
        return get_int(session, WALLET_WITHDRAW_MIN), get_int(session, WALLET_WITHDRAW_MAX)
    if kind in {"card", "card_to_card"}:
        return get_int(session, WALLET_CARD_MIN), get_int(session, WALLET_CARD_MAX)
    return get_int(session, WALLET_DEPOSIT_MIN), get_int(session, WALLET_DEPOSIT_MAX)


def validate_amount(session, amount: int, kind="deposit"):
    minimum, maximum = amount_limits(session, kind)
    if amount < minimum or (maximum > 0 and amount > maximum):
        return False, f"مبلغ باید بین {format_amount(minimum)} و {format_amount(maximum)} تومان باشد."
    return True, None


def new_transaction(session, user_id: int, kind: str, method: str, amount: int, *, expires_at=None, metadata=None):
    wallet = ensure_wallet(session, user_id)
    tx = WalletTransaction(
        transaction_no="TEMP",
        user_id=int(user_id),
        wallet_id=wallet.id,
        kind=kind,
        method=method,
        status=STATUS_WAITING_PAYMENT if kind == "deposit" else STATUS_WAITING_OWNER,
        requested_amount=int(amount),
        payment_amount=int(amount),
        balance_before=int(wallet.balance),
        balance_after=int(wallet.balance),
        reserved_before=int(wallet.reserved_balance),
        reserved_after=int(wallet.reserved_balance),
        expires_at=expires_at,
        metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
    )
    session.add(tx)
    session.flush()
    tx.transaction_no = f"WLT-{datetime.utcnow():%Y%m%d}-{tx.id:08d}"
    wallet.transaction_count = int(wallet.transaction_count or 0) + 1
    wallet.updated_at = datetime.utcnow()
    session.flush()
    return tx


def metadata(tx: WalletTransaction) -> dict:
    try:
        value = json.loads(tx.metadata_json or "{}")
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def save_metadata(tx: WalletTransaction, data: dict):
    tx.metadata_json = json.dumps(data or {}, ensure_ascii=False)


def transaction_is_expired(tx: WalletTransaction) -> bool:
    return bool(tx.expires_at and tx.expires_at <= datetime.utcnow())


def get_user_transaction(session, user_id: int, transaction_id: int) -> WalletTransaction | None:
    return session.scalar(select(WalletTransaction).where(WalletTransaction.id == int(transaction_id), WalletTransaction.user_id == int(user_id)))


def _active_identifier_exists(session, amount: int, exclude_tx_id: int | None = None) -> bool:
    q = select(func.count(WalletTransaction.id)).where(
        WalletTransaction.identifier_amount == int(amount),
        WalletTransaction.status.in_(list(ACTIVE_DEPOSIT_STATUSES)),
    )
    if exclude_tx_id:
        q = q.where(WalletTransaction.id != int(exclude_tx_id))
    return bool(session.scalar(q) or 0)


def allocate_identifier_amount(session, tx: WalletTransaction) -> int | None:
    minimum = get_int(session, WALLET_CARD_ID_MIN, 1)
    maximum = get_int(session, WALLET_CARD_ID_MAX)
    if minimum > maximum:
        minimum, maximum = maximum, minimum
    space = maximum - minimum + 1
    rng = random.SystemRandom()
    # برای بازه‌های بزرگ، کل بازه را در حافظه نساز؛ چند تلاش تصادفی انجام بده و در نهایت
    # در صورت اشباع، به‌صورت ترتیبی فضای آزاد را پیدا کن.
    attempts = min(max(space * 2, 32), 5000)
    for _ in range(attempts):
        value = rng.randint(minimum, maximum)
        if not _active_identifier_exists(session, value, tx.id):
            tx.identifier_amount = int(value)
            tx.payment_amount = int(tx.requested_amount) + int(value)
            save_metadata(tx, {**metadata(tx), "identifier_amount": int(value), "expected_transfer_amount": int(tx.payment_amount), "identifier_activated_at": datetime.utcnow().isoformat()})
            session.flush()
            return int(value)
    if space <= 200000:
        start = rng.randint(minimum, maximum)
        for offset in range(space):
            value = minimum + ((start - minimum + offset) % space)
            if not _active_identifier_exists(session, value, tx.id):
                tx.identifier_amount = int(value)
                tx.payment_amount = int(tx.requested_amount) + int(value)
                save_metadata(tx, {**metadata(tx), "identifier_amount": int(value), "expected_transfer_amount": int(tx.payment_amount), "identifier_activated_at": datetime.utcnow().isoformat()})
                session.flush()
                return int(value)
    return None


def clear_identifier(tx: WalletTransaction):
    tx.identifier_amount = 0
    if tx.kind == "deposit":
        tx.payment_amount = int(tx.requested_amount)


def active_cards(session):
    return list(session.scalars(select(WalletCard).where(WalletCard.enabled == True).order_by(WalletCard.sort_order, WalletCard.id)).all())


def choose_card(session, user_id: int) -> WalletCard | None:
    cards = active_cards(session)
    if not cards:
        return None
    if get_bool(session, WALLET_CARD_ROTATION):
        cursor_key = "wallet_card_rotation_cursor"
        current = get_int(session, cursor_key, 0)
        card = cards[current % len(cards)]
        set_int(session, cursor_key, (current + 1) % len(cards), 0)
        return card
    return cards[0]


def selected_card(session, card_id: int) -> WalletCard | None:
    return session.scalar(select(WalletCard).where(WalletCard.id == int(card_id), WalletCard.enabled == True))


def create_card_request(session, user_id: int, amount: int, card_id: int | None = None):
    expires = datetime.utcnow() + timedelta(minutes=get_int(session, WALLET_PAYMENT_EXPIRY_MINUTES, 30))
    card = selected_card(session, card_id) if card_id else choose_card(session, user_id)
    if card is None:
        return None, "هیچ کارت فعالی برای کارت‌به‌کارت تنظیم نشده است."
    tx = new_transaction(session, user_id, "deposit", "card", amount, expires_at=expires, metadata={"selected_card_id": card.id})
    tx.wallet_card_id = card.id
    session.flush()
    return tx, None


def activate_card_identifier(session, tx: WalletTransaction):
    if transaction_is_expired(tx):
        tx.status = STATUS_EXPIRED
        clear_identifier(tx)
        tx.completed_at = datetime.utcnow()
        tx.updated_at = datetime.utcnow()
        return None, "⏰ مهلت این درخواست تمام شده است و دیگر نمی‌توان رسید ارسال کرد."
    if tx.status not in {STATUS_WAITING_PAYMENT, STATUS_WAITING_RECEIPT}:
        return None, "این درخواست دیگر قابل فعال‌سازی نیست."
    if tx.identifier_amount:
        tx.status = STATUS_WAITING_RECEIPT
        return int(tx.identifier_amount), None
    value = allocate_identifier_amount(session, tx)
    if value is None:
        return None, "در بازه فعلی مبلغ شناسه یکتای کافی وجود ندارد؛ Owner باید بازه را افزایش دهد."
    tx.status = STATUS_WAITING_RECEIPT
    tx.updated_at = datetime.utcnow()
    session.flush()
    return value, None


def accept_card_receipt(session, tx: WalletTransaction, *, text=None, file_id=None, file_kind=None):
    if transaction_is_expired(tx):
        tx.status = STATUS_EXPIRED
        clear_identifier(tx)
        return False, "مهلت این درخواست تمام شده و ارسال رسید ممکن نیست."
    if tx.status not in {STATUS_WAITING_RECEIPT, STATUS_WAITING_PAYMENT, STATUS_WAITING_OWNER}:
        return False, "این درخواست دیگر قابل ثبت رسید نیست."
    if text is not None:
        tx.receipt_text = str(text)[:4000]
        tx.receipt_kind = "text" if not file_id else "mixed"
    if file_id is not None:
        tx.receipt_file_id = str(file_id)
        tx.receipt_kind = "photo" if not text else "mixed"
    if not tx.receipt_text and not tx.receipt_file_id:
        return False, "رسید خالی است."
    tx.status = STATUS_WAITING_OWNER
    tx.updated_at = datetime.utcnow()
    session.flush()
    return True, None


def approve_deposit(session, tx: WalletTransaction, credited_amount: int, *, verified_amount: int | None = None, external_reference=None):
    if tx.kind != "deposit":
        return False, "نوع تراکنش معتبر نیست."
    if tx.status == STATUS_APPROVED:
        return False, "این تراکنش قبلاً تأیید شده است."
    if tx.status in {STATUS_REJECTED, STATUS_CANCELLED, STATUS_EXPIRED}:
        return False, "این تراکنش دیگر قابل تأیید نیست."
    if transaction_is_expired(tx):
        tx.status = STATUS_EXPIRED
        clear_identifier(tx)
        tx.completed_at = datetime.utcnow()
        tx.updated_at = datetime.utcnow()
        session.flush()
        return False, "مهلت این تراکنش تمام شده است."
    credited_amount = int(credited_amount)
    if credited_amount <= 0:
        return False, "مبلغ اعتبار باید بیشتر از صفر باشد."
    if verified_amount is not None and credited_amount > max(0, int(verified_amount) - int(tx.identifier_amount or 0)) and tx.method == "card":
        return False, "اعتبار کیف پول نمی‌تواند بیشتر از مبلغ واریزی تأییدشده پس از کسر مبلغ شناسه باشد."
    wallet = session.get(Wallet, tx.wallet_id)
    if wallet is None:
        return False, "کیف پول پیدا نشد."
    if not claim_once(session, f"wallet:finalize:{int(tx.id)}", str(tx.id)):
        return False, "این تراکنش هم‌اکنون توسط درخواست دیگری در حال تأیید است."
    before = int(wallet.balance)
    wallet.balance = before + credited_amount
    wallet.total_deposits = int(wallet.total_deposits or 0) + credited_amount
    wallet.updated_at = datetime.utcnow()
    tx.balance_before = before
    tx.balance_after = int(wallet.balance)
    tx.verified_amount = int(verified_amount or tx.payment_amount or credited_amount)
    tx.credited_amount = credited_amount
    tx.status = STATUS_APPROVED
    tx.external_reference = str(external_reference) if external_reference is not None else tx.external_reference
    tx.completed_at = datetime.utcnow()
    tx.updated_at = datetime.utcnow()
    clear_identifier(tx)
    session.flush()
    return True, None


def reject_transaction(session, tx: WalletTransaction, reason=None):
    if tx.status in {STATUS_APPROVED, STATUS_REJECTED, STATUS_CANCELLED}:
        return False, "این تراکنش قبلاً نهایی شده است."
    if not claim_once(session, f"wallet:finalize:{int(tx.id)}", str(tx.id)):
        return False, "این تراکنش هم‌اکنون توسط درخواست دیگری در حال نهایی‌شدن است."
    if tx.kind == "withdrawal" and tx.status not in {STATUS_REJECTED, STATUS_CANCELLED}:
        wallet = session.get(Wallet, tx.wallet_id)
        if wallet is not None:
            refund = int(tx.reserved_after or tx.payment_amount or tx.requested_amount or 0)
            wallet.balance = int(wallet.balance) + refund
            wallet.reserved_balance = max(0, int(wallet.reserved_balance) - refund)
            wallet.updated_at = datetime.utcnow()
            tx.balance_before = int(tx.balance_before or wallet.balance - refund)
            tx.balance_after = int(wallet.balance)
            tx.reserved_after = int(wallet.reserved_balance)
    tx.status = STATUS_REJECTED
    tx.rejection_reason = (str(reason).strip() if reason else None)
    tx.completed_at = datetime.utcnow()
    tx.updated_at = datetime.utcnow()
    clear_identifier(tx)
    session.flush()
    return True, None


def cancel_transaction(session, tx: WalletTransaction):
    if tx.status in {STATUS_APPROVED, STATUS_REJECTED, STATUS_CANCELLED, STATUS_EXPIRED}:
        return False
    if not claim_once(session, f"wallet:finalize:{int(tx.id)}", str(tx.id)):
        return False
    if tx.kind == "withdrawal":
        wallet = session.get(Wallet, tx.wallet_id)
        if wallet is not None:
            refund = int(tx.reserved_after or tx.payment_amount or tx.requested_amount or 0)
            wallet.balance = int(wallet.balance) + refund
            wallet.reserved_balance = max(0, int(wallet.reserved_balance) - refund)
            wallet.updated_at = datetime.utcnow()
            tx.balance_after = int(wallet.balance)
            tx.reserved_after = int(wallet.reserved_balance)
    tx.status = STATUS_CANCELLED
    tx.completed_at = datetime.utcnow()
    tx.updated_at = datetime.utcnow()
    clear_identifier(tx)
    session.flush()
    return True


def expire_due_transactions(session):
    now = datetime.utcnow()
    rows = list(session.scalars(select(WalletTransaction).where(
        WalletTransaction.kind == "deposit",
        WalletTransaction.status.in_(list(ACTIVE_DEPOSIT_STATUSES)),
        WalletTransaction.expires_at.is_not(None),
        WalletTransaction.expires_at <= now,
    )).all())
    for tx in rows:
        if not claim_once(session, f"wallet:finalize:{int(tx.id)}", str(tx.id)):
            continue
        tx.status = STATUS_EXPIRED
        tx.updated_at = now
        tx.completed_at = now
        clear_identifier(tx)
    if rows:
        session.flush()
    return rows


def totals_for_user(session, user_id: int):
    wallet = ensure_wallet(session, user_id)
    return wallet


def list_transactions(session, user_id: int, page: int = 1, per_page: int = 10):
    page = max(1, int(page))
    total = int(session.scalar(select(func.count(WalletTransaction.id)).where(WalletTransaction.user_id == int(user_id))) or 0)
    pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, pages)
    rows = list(session.scalars(
        select(WalletTransaction)
        .where(WalletTransaction.user_id == int(user_id))
        .order_by(WalletTransaction.created_at.desc(), WalletTransaction.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).all())
    return rows, page, pages


def get_pending_owner_transactions(session, page=1, per_page=10):
    page = max(1, int(page))
    statuses = [STATUS_WAITING_OWNER, STATUS_WAITING_EDIT, STATUS_WAITING_REJECTION, STATUS_WAITING_WITHDRAWAL_RECEIPT]
    q = select(WalletTransaction).where(WalletTransaction.status.in_(statuses)).order_by(WalletTransaction.created_at.asc(), WalletTransaction.id.asc())
    total = int(session.scalar(select(func.count(WalletTransaction.id)).where(WalletTransaction.status.in_(statuses))) or 0)
    pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, pages)
    rows = list(session.scalars(q.offset((page - 1) * per_page).limit(per_page)).all())
    return rows, page, pages


def list_owner_requests(session, group: str, page: int = 1, per_page: int = 10):
    """List wallet requests for the Owner request center."""
    page = max(1, int(page))
    group = str(group or "pending").lower()
    if group == "approved":
        statuses = [STATUS_APPROVED]
    elif group == "rejected":
        statuses = [STATUS_REJECTED]
    else:
        statuses = [
            STATUS_WAITING_PAYMENT,
            STATUS_WAITING_RECEIPT,
            STATUS_WAITING_OWNER,
            STATUS_WAITING_EDIT,
            STATUS_WAITING_REJECTION,
            STATUS_WAITING_WITHDRAWAL_RECEIPT,
        ]
    where = WalletTransaction.status.in_(statuses)
    total = int(session.scalar(select(func.count(WalletTransaction.id)).where(where)) or 0)
    pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, pages)
    rows = list(session.scalars(
        select(WalletTransaction)
        .where(where)
        .order_by(WalletTransaction.created_at.desc(), WalletTransaction.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).all())
    return rows, page, pages


def search_owner_request(session, transaction_no: str):
    value = str(transaction_no or "").strip()
    if not value:
        return None
    return session.scalar(
        select(WalletTransaction)
        .where(WalletTransaction.transaction_no.ilike(f"%{value}%"))
        .order_by(WalletTransaction.created_at.desc(), WalletTransaction.id.desc())
    )


def wallet_admin_stats(session):
    """Return a compact, database-backed wallet/payment dashboard for Owner."""
    pending_statuses = [
        STATUS_WAITING_PAYMENT, STATUS_WAITING_RECEIPT, STATUS_WAITING_OWNER,
        STATUS_WAITING_EDIT, STATUS_WAITING_REJECTION, STATUS_WAITING_WITHDRAWAL_RECEIPT,
    ]
    total_wallets = int(session.scalar(select(func.count(Wallet.id))) or 0)
    total_balance = int(session.scalar(select(func.coalesce(func.sum(Wallet.balance), 0))) or 0)
    total_reserved = int(session.scalar(select(func.coalesce(func.sum(Wallet.reserved_balance), 0))) or 0)
    deposits = int(session.scalar(select(func.count(WalletTransaction.id)).where(WalletTransaction.kind == "deposit", WalletTransaction.status == STATUS_APPROVED)) or 0)
    deposit_amount = int(session.scalar(select(func.coalesce(func.sum(WalletTransaction.credited_amount), 0)).where(WalletTransaction.kind == "deposit", WalletTransaction.status == STATUS_APPROVED)) or 0)
    withdrawals = int(session.scalar(select(func.count(WalletTransaction.id)).where(WalletTransaction.kind == "withdrawal", WalletTransaction.status == STATUS_APPROVED)) or 0)
    withdrawal_amount = int(session.scalar(select(func.coalesce(func.sum(WalletTransaction.requested_amount), 0)).where(WalletTransaction.kind == "withdrawal", WalletTransaction.status == STATUS_APPROVED)) or 0)
    pending = int(session.scalar(select(func.count(WalletTransaction.id)).where(WalletTransaction.status.in_(pending_statuses))) or 0)
    pending_amount = int(session.scalar(select(func.coalesce(func.sum(WalletTransaction.requested_amount), 0)).where(WalletTransaction.status.in_(pending_statuses))) or 0)
    rejected = int(session.scalar(select(func.count(WalletTransaction.id)).where(WalletTransaction.status == STATUS_REJECTED)) or 0)
    cancelled = int(session.scalar(select(func.count(WalletTransaction.id)).where(WalletTransaction.status == STATUS_CANCELLED)) or 0)
    expired = int(session.scalar(select(func.count(WalletTransaction.id)).where(WalletTransaction.status == STATUS_EXPIRED)) or 0)
    tx_total = int(session.scalar(select(func.count(WalletTransaction.id))) or 0)
    by_method = {}
    method_rows = session.execute(
        select(
            WalletTransaction.method,
            func.count(WalletTransaction.id),
            func.coalesce(func.sum(WalletTransaction.credited_amount), 0),
        )
        .where(WalletTransaction.kind == "deposit", WalletTransaction.status == STATUS_APPROVED)
        .group_by(WalletTransaction.method)
    ).all()
    for method, count, amount in method_rows:
        by_method[str(method)] = {"count": int(count or 0), "amount": int(amount or 0)}
    return {
        "wallets": total_wallets,
        "balance": total_balance,
        "reserved": total_reserved,
        "transactions": tx_total,
        "deposits_count": deposits,
        "deposits_amount": deposit_amount,
        "withdrawals_count": withdrawals,
        "withdrawals_amount": withdrawal_amount,
        "pending_count": pending,
        "pending_amount": pending_amount,
        "rejected_count": rejected,
        "cancelled_count": cancelled,
        "expired_count": expired,
        "by_method": by_method,
    }


def daily_withdraw_total(session, user_id: int):
    start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return int(session.scalar(select(func.coalesce(func.sum(WalletTransaction.requested_amount), 0)).where(
        WalletTransaction.user_id == int(user_id),
        WalletTransaction.kind == "withdrawal",
        WalletTransaction.status.in_([STATUS_WAITING_OWNER, STATUS_WAITING_WITHDRAWAL_RECEIPT, STATUS_APPROVED]),
        WalletTransaction.created_at >= start,
    )) or 0)


def daily_withdraw_count(session, user_id: int):
    # «سقف تعداد برداشت روزانه» بر اساس تعداد درخواست‌های ثبت‌شده است،
    # نه فقط درخواست‌های موفق؛ بنابراین لغو/رد شدن هم سهم همان روز را مصرف می‌کند.
    start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return int(session.scalar(select(func.count(WalletTransaction.id)).where(
        WalletTransaction.user_id == int(user_id),
        WalletTransaction.kind == "withdrawal",
        WalletTransaction.created_at >= start,
    )) or 0)


def active_withdrawal_methods(session):
    # Kept only for compatibility with older databases/code paths. New UI uses
    # the single built-in card-to-card withdrawal flow and never exposes methods.
    return list(session.scalars(select(WalletWithdrawalMethod).where(WalletWithdrawalMethod.enabled == True).order_by(WalletWithdrawalMethod.id)).all())


def create_withdrawal(session, user_id: int, amount: int, destination: str):
    ok, error = validate_amount(session, amount, "withdraw")
    if not ok:
        return None, error
    daily_limit = get_int(session, WITHDRAW_DAILY_COUNT_LIMIT, 0)
    if daily_limit and daily_withdraw_count(session, user_id) >= daily_limit:
        return None, f"شما امروز به سقف {daily_limit:,} درخواست برداشت رسیده‌اید."
    wallet = ensure_wallet(session, user_id)
    total_debit = int(amount)
    if int(wallet.balance) < total_debit:
        return None, "موجودی کیف پول برای این برداشت کافی نیست."
    tx = new_transaction(
        session,
        user_id,
        "withdrawal",
        "card_to_card",
        amount,
        expires_at=None,
        metadata={"withdrawal_method": "کارت‌به‌کارت"},
    )
    before = int(wallet.balance)
    wallet.balance = before - total_debit
    wallet.reserved_balance = int(wallet.reserved_balance or 0) + total_debit
    tx.fee_amount = 0
    tx.payment_amount = total_debit
    tx.destination = str(destination)[:1000]
    tx.balance_before = before
    tx.balance_after = int(wallet.balance)
    tx.reserved_before = int(wallet.reserved_balance - total_debit)
    tx.reserved_after = int(wallet.reserved_balance)
    tx.updated_at = datetime.utcnow()
    wallet.updated_at = datetime.utcnow()
    session.flush()
    return tx, None


def complete_withdrawal(session, tx: WalletTransaction, receipt_file_id=None, receipt_text=None):
    if tx.kind != "withdrawal":
        return False, "نوع تراکنش معتبر نیست."
    if tx.status in {STATUS_APPROVED, STATUS_REJECTED, STATUS_CANCELLED}:
        return False, "این برداشت قبلاً نهایی شده است."
    wallet = session.get(Wallet, tx.wallet_id)
    if wallet is None:
        return False, "کیف پول پیدا نشد."
    if not claim_once(session, f"wallet:finalize:{int(tx.id)}", str(tx.id)):
        return False, "این برداشت هم‌اکنون توسط درخواست دیگری در حال نهایی‌شدن است."
    reserved = int(tx.payment_amount or tx.reserved_after or 0)
    wallet.reserved_balance = max(0, int(wallet.reserved_balance) - reserved)
    wallet.total_withdrawals = int(wallet.total_withdrawals or 0) + int(tx.requested_amount)
    wallet.updated_at = datetime.utcnow()
    tx.reserved_before = int(tx.reserved_after or reserved)
    tx.reserved_after = int(wallet.reserved_balance)
    tx.status = STATUS_APPROVED
    tx.completed_at = datetime.utcnow()
    tx.updated_at = datetime.utcnow()
    if receipt_file_id:
        tx.receipt_file_id = str(receipt_file_id)
        tx.receipt_kind = "photo"
    if receipt_text:
        tx.receipt_text = str(receipt_text)[:4000]
        tx.receipt_kind = "mixed" if receipt_file_id else "text"
    session.flush()
    return True, None


def star_amount_for_credit(session, toman: int) -> int:
    rate = max(1, get_int(session, STARS_TOMAN_RATE, 1))
    value = (Decimal(toman) / Decimal(rate)).to_integral_value(rounding=ROUND_CEILING)
    return max(1, int(value))


def crypto_quote_amount(session, toman: int, rate_toman_per_coin: Decimal):
    markup = Decimal(str(get_float(session, CRYPTO_MARKUP_PERCENT, 0, 1000)))
    base = Decimal(toman) * (Decimal(1) + markup / Decimal(100))
    if rate_toman_per_coin <= 0:
        raise ValueError("invalid crypto rate")
    amount = (base / rate_toman_per_coin).quantize(Decimal("0.00000001"), rounding=ROUND_CEILING)
    return amount, base


def _http_json(url: str, timeout: int = 15, headers=None):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "WorldWar3Bot-Wallet/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read().decode("utf-8", errors="replace")
    return json.loads(raw)


async def get_crypto_rates_toman(session):
    source = get_setting(session, CRYPTO_PRICE_SOURCE, "coingecko").strip().lower()
    if source != "coingecko":
        source = "coingecko"
    ids = ",".join(SUPPORTED_COINS.values())
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={urllib.parse.quote(ids)}&vs_currencies=irr,usd"
    data = await asyncio.to_thread(_http_json, url)
    rates = {}
    # CoinGecko's IRR price is rial.  Convert it to toman for the bot's display.
    for symbol, coin_id in SUPPORTED_COINS.items():
        item = data.get(coin_id) or {}
        if item.get("irr"):
            rates[symbol] = Decimal(str(item["irr"])) / Decimal(10)
            continue
        usd = item.get("usd")
        fallback = Decimal(str(get_float(session, CRYPTO_USD_TO_IRR_FALLBACK, 0)))
        if usd and fallback > 0:
            rates[symbol] = Decimal(str(usd)) * fallback / Decimal(10)
            continue
        raise RuntimeError(f"نرخ {symbol} از منبع آنلاین دریافت نشد.")
    return rates


async def verify_crypto_transaction(tx: WalletTransaction, destination: WalletCryptoDestination):
    data = metadata(tx)
    txid = str(tx.external_id or "").strip()
    if not txid:
        return {"ok": False, "message": "TXID ثبت نشده است."}
    expected = Decimal(str(data.get("crypto_amount") or "0"))
    coin = str(data.get("coin") or "").upper()
    address = destination.address
    confirmations_required = int(destination.confirmations_required or get_int_from_metadata(data, "confirmations", 1))

    try:
        if coin == "BTC":
            info = await asyncio.to_thread(_http_json, f"https://mempool.space/api/tx/{urllib.parse.quote(txid)}")
            if info.get("status") is None:
                return {"ok": False, "message": "تراکنش بیت‌کوین پیدا نشد."}
            received = Decimal("0")
            confirmations = 0
            for out in info.get("vout") or []:
                script_addr = (out.get("scriptpubkey_address") or "").strip()
                if script_addr == address:
                    received += Decimal(int(out.get("value") or 0)) / Decimal(100_000_000)
            status = info.get("status") or {}
            if status.get("confirmed"):
                confirmed_height = int(status.get("block_height") or 0)
                tip = int((await asyncio.to_thread(_http_json, "https://mempool.space/api/blocks/tip/height")) or 0)
                confirmations = max(0, tip - confirmed_height + 1)
            ok = received >= expected and confirmations >= confirmations_required
            return {"ok": ok, "received": str(received), "confirmations": confirmations, "message": "تراکنش تأیید شد." if ok else "مبلغ یا تعداد تأییدیه کافی نیست."}

        if coin == "USDT":
            network = str(data.get("network") or "TRC20").upper()
            if network != "TRC20":
                return {"ok": False, "message": "در این نسخه شبکه USDT فقط TRC20 فعال است."}
            url = "https://apilist.tronscanapi.com/api/token_trc20/transfers?limit=50&start=0&toAddress=" + urllib.parse.quote(address)
            response = await asyncio.to_thread(_http_json, url)
            transfers = response.get("data") or []
            for item in transfers:
                if str(item.get("transactionHash") or item.get("transaction_id") or "") != txid:
                    continue
                token_info = item.get("tokenInfo") or {}
                decimals = int(token_info.get("tokenDecimal") or 6)
                amount = Decimal(str(item.get("quant") or 0)) / (Decimal(10) ** decimals)
                confirmations = int(item.get("confirmations") or 0)
                ok = amount >= expected and confirmations >= confirmations_required and str(item.get("toAddress") or item.get("to_address") or "") == address
                return {"ok": ok, "received": str(amount), "confirmations": confirmations, "message": "تراکنش تأیید شد." if ok else "مبلغ، مقصد یا تأییدیه کافی نیست."}
            return {"ok": False, "message": "تراکنش USDT/ TRC20 پیدا نشد."}

        if coin == "TON":
            url = f"https://tonapi.io/v2/blockchain/transactions/{urllib.parse.quote(txid)}"
            info = await asyncio.to_thread(_http_json, url)
            received = Decimal("0")
            confirmations = int(info.get("mc_block_seqno") or 0) > 0
            for action in info.get("actions") or []:
                simple = action.get("TonTransfer") or action.get("tonTransfer") or {}
                recipient = ((simple.get("recipient") or {}).get("address") or "")
                if recipient == address:
                    amount = int((simple.get("amount") or {}).get("value") or simple.get("amount") or 0)
                    received += Decimal(amount) / Decimal(1_000_000_000)
            ok = received >= expected and bool(confirmations)
            return {"ok": ok, "received": str(received), "confirmations": 1 if confirmations else 0, "message": "تراکنش تأیید شد." if ok else "مبلغ یا وضعیت تأیید کافی نیست."}

        return {"ok": False, "message": "ارز پشتیبانی نمی‌شود."}
    except Exception as exc:
        return {"ok": False, "unavailable": True, "message": f"بررسی آنلاین تراکنش در حال حاضر در دسترس نیست: {type(exc).__name__}"}


def get_int_from_metadata(data, key, default=0):
    try:
        return int(data.get(key, default))
    except Exception:
        return default


def _zarinpal_callback_base() -> str:
    # The public callback address belongs to the server deployment, not the Owner
    # business settings. Keep it outside the database/panel.
    return str(ZARINPAL_CALLBACK_BASE_URL or "").strip().rstrip("/")


def zarinpal_configuration_ready(session) -> bool:
    merchant_id = get_setting(session, ZP_MERCHANT_ID, "").strip()
    callback_base = _zarinpal_callback_base()
    return bool(merchant_id and callback_base.startswith("https://"))


def _zarinpal_api_host(sandbox: bool) -> str:
    return "sandbox.zarinpal.com" if sandbox else "api.zarinpal.com"


def _zarinpal_start_host(sandbox: bool) -> str:
    return "sandbox.zarinpal.com" if sandbox else "www.zarinpal.com"


def _zarinpal_error_text(response: dict) -> str:
    errors = response.get("errors") or response.get("error") or {}
    if isinstance(errors, dict):
        code = errors.get("code")
        message = errors.get("message")
        if code is not None and message:
            return f"کد {code}: {message}"
        if message:
            return str(message)
        if code is not None:
            return f"کد خطا {code}"
    return "پاسخ نامعتبر از زرین‌پال دریافت شد."


async def zarinpal_request(session, tx: WalletTransaction):
    merchant_id = get_setting(session, ZP_MERCHANT_ID, "").strip()
    callback_base = _zarinpal_callback_base()
    if not merchant_id:
        raise RuntimeError("شناسه پذیرنده زرین‌پال در پنل اونر ثبت نشده است.")
    if not callback_base or not callback_base.startswith("https://"):
        raise RuntimeError("آدرس عمومی امن درگاه روی سرور تنظیم نشده است. این مورد تنظیم فنی سرور است و از پنل اونر تنظیم نمی‌شود.")

    # Wallet amounts are stored/displayed in تومان. ZarinPal v4 expects ریال.
    amount_toman = int(tx.payment_amount or tx.requested_amount)
    amount_rial = amount_toman * 10
    if amount_rial <= 0:
        raise RuntimeError("مبلغ پرداخت معتبر نیست.")

    description = get_setting(session, ZP_DESCRIPTION, "افزایش موجودی کیف پول").strip() or "افزایش موجودی کیف پول"
    callback = f"{callback_base}/payments/zarinpal/callback"
    payload = {
        "merchant_id": merchant_id,
        "amount": amount_rial,
        "description": description[:255],
        "callback_url": callback,
        "metadata": {"mobile": None, "email": None},
    }
    sandbox = False
    url = f"https://{_zarinpal_api_host(sandbox)}/pg/v4/payment/request.json"
    try:
        response = await asyncio.to_thread(_post_json, url, payload)
    except Exception as exc:
        raise RuntimeError(f"ارتباط با زرین‌پال برقرار نشد: {exc}") from exc

    data = response.get("data") or {}
    code = int(data.get("code") or 0)
    authority = str(data.get("authority") or "").strip()
    if code != 100 or not authority:
        raise RuntimeError(_zarinpal_error_text(response))

    tx.external_id = authority
    tx.status = STATUS_WAITING_PAYMENT
    tx.updated_at = datetime.utcnow()
    save_metadata(tx, {
        **metadata(tx),
        "zarinpal_authority": authority,
        "zarinpal_amount_toman": amount_toman,
        "zarinpal_amount_rial": amount_rial,
        "zarinpal_environment": "sandbox" if sandbox else "live",
    })
    session.flush()
    return f"https://{_zarinpal_start_host(sandbox)}/pg/StartPay/{authority}"


async def zarinpal_verify(session, tx: WalletTransaction):
    merchant_id = get_setting(session, ZP_MERCHANT_ID, "").strip()
    if not merchant_id or not tx.external_id:
        return {"ok": False, "message": "اطلاعات زرین‌پال ناقص است."}

    data = metadata(tx)
    amount_rial = int(data.get("zarinpal_amount_rial") or (int(tx.payment_amount or tx.requested_amount) * 10))
    if amount_rial <= 0:
        return {"ok": False, "message": "مبلغ تراکنش نامعتبر است."}

    sandbox = False
    url = f"https://{_zarinpal_api_host(sandbox)}/pg/v4/payment/verify.json"
    payload = {"merchant_id": merchant_id, "amount": amount_rial, "authority": tx.external_id}
    try:
        response = await asyncio.to_thread(_post_json, url, payload)
        data = response.get("data") or {}
        code = int(data.get("code") or 0)
        ref_id = data.get("ref_id")
        # 100 = verified; 101 = already verified/submitted. Both are safe to
        # treat as paid because the authority is tied to this exact transaction.
        return {
            "ok": code in {100, 101},
            "code": code,
            "ref_id": ref_id,
            "raw": response,
            "message": "پرداخت تأیید شد." if code in {100, 101} else _zarinpal_error_text(response),
        }
    except Exception as exc:
        return {"ok": False, "message": f"بررسی زرین‌پال ناموفق بود: {exc}"}


def _post_json(url: str, payload: dict, timeout: int = 20):
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=raw, headers={"Content-Type": "application/json", "User-Agent": "WorldWar3Bot-Wallet/1.0"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as response:
        body = response.read().decode("utf-8", errors="replace")
    return json.loads(body)


def card_text(card: WalletCard) -> str:
    lines = [
        f"💳 <b>شماره کارت:</b> <code>{card.card_number}</code>",
        f"👤 <b>به نام:</b> {card.owner_name}",
        f"🏦 <b>بانک:</b> {card.bank_name}",
    ]
    if card.iban:
        lines.append(f"🏧 <b>شبا:</b> <code>{card.iban}</code>")
    if card.account_number:
        lines.append(f"🔢 <b>شماره حساب:</b> <code>{card.account_number}</code>")
    if card.description:
        lines.append(f"📝 {card.description}")
    return "\n".join(lines)


async def wallet_expiry_worker(app):
    await asyncio.sleep(1)
    while True:
        try:
            with SessionLocal() as session:
                expired = expire_due_transactions(session)
                session.commit()
            for tx in expired:
                try:
                    await app.bot.send_message(
                        chat_id=tx.user_id,
                        text=(
                            "⏰ <b>مهلت درخواست پرداخت شما تمام شد.</b>\n\n"
                            f"🧾 تراکنش: <code>{tx.transaction_no}</code>\n"
                            "این درخواست دیگر قابل ارسال یا ثبت رسید نیست. برای پرداخت، درخواست جدید ایجاد کنید."
                        ),
                        parse_mode="HTML",
                    )
                except Exception:
                    pass
        except asyncio.CancelledError:
            raise
        except Exception:
            pass
        await asyncio.sleep(5)
