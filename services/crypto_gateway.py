from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_CEILING

from sqlalchemy import select

from config import PAYMENT_WEB_BASE_URL
from database.db import SessionLocal
from database.models import WalletTransaction
from services.wallet import (
    CRYPTO_ENABLED,
    CRYPTO_MARKUP_PERCENT,
    CRYPTO_MIN,
    CRYPTO_MAX,
    WALLET_PAYMENT_EXPIRY_MINUTES,
    STATUS_APPROVED,
    STATUS_CANCELLED,
    STATUS_EXPIRED,
    STATUS_WAITING_PAYMENT,
    approve_deposit,
    format_amount,
    get_bool,
    get_float,
    get_int,
    get_setting,
    metadata,
    save_metadata,
    transaction_is_expired,
)

LOGGER = logging.getLogger("worldwar3.crypto_gateway")

CRYPTO_CLIENT_ID = "wallet_crypto_client_id"
CRYPTO_CLIENT_SECRET = "wallet_crypto_client_secret"
CRYPTO_API_BASE = "wallet_crypto_api_base"
CRYPTO_FIAT_CURRENCY = "wallet_crypto_fiat_currency"
CRYPTO_WEBHOOK_ENABLED = "wallet_crypto_webhook_enabled"
CRYPTO_POLL_SECONDS = "wallet_crypto_poll_seconds"

DEFAULT_CRYPTO_GATEWAY = {
    CRYPTO_CLIENT_ID: "",
    CRYPTO_CLIENT_SECRET: "",
    CRYPTO_API_BASE: "https://a-api.coinpayments.net/api",
    CRYPTO_FIAT_CURRENCY: "USD",
    CRYPTO_WEBHOOK_ENABLED: "1",
    CRYPTO_POLL_SECONDS: "60",
}

# CoinPayments V2 payment symbols. USDT is intentionally fixed to TRC20 for
# the first production version to avoid ambiguous USDT network selection.
PAYMENT_CURRENCIES = {
    "BTC": "BTC",
    "TON": "TON",
    "USDT": "USDT.TRC20",
}


class CryptoGatewayError(RuntimeError):
    pass


def ensure_crypto_gateway_defaults(session):
    from database.models import BotSetting
    changed = False
    for key, value in DEFAULT_CRYPTO_GATEWAY.items():
        row = session.scalar(select(BotSetting).where(BotSetting.key == key))
        if row is None:
            session.add(BotSetting(key=key, value=str(value)))
            changed = True
    if changed:
        session.flush()


def crypto_gateway_configured(session) -> bool:
    ensure_crypto_gateway_defaults(session)
    return bool(
        get_setting(session, CRYPTO_CLIENT_ID, "").strip()
        and get_setting(session, CRYPTO_CLIENT_SECRET, "").strip()
    )


def _json_bytes(payload: dict | None) -> bytes:
    if payload is None:
        return b""
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _timestamp() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")


def _signature(method: str, url: str, client_id: str, timestamp: str, body: bytes, secret: str) -> str:
    canonical = "\ufeff" + method.upper() + url + client_id + timestamp + body.decode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(digest).decode("ascii")


def _request_sync(session, method: str, path: str, payload: dict | None = None):
    ensure_crypto_gateway_defaults(session)
    client_id = get_setting(session, CRYPTO_CLIENT_ID, "").strip()
    secret = get_setting(session, CRYPTO_CLIENT_SECRET, "").strip()
    base = get_setting(session, CRYPTO_API_BASE, DEFAULT_CRYPTO_GATEWAY[CRYPTO_API_BASE]).strip().rstrip("/")
    if not client_id or not secret:
        raise CryptoGatewayError("کلیدهای CoinPayments هنوز در پنل اونر ثبت نشده‌اند.")
    url = f"{base}/{path.lstrip('/')}"
    body = _json_bytes(payload)
    timestamp = _timestamp()
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-CoinPayments-Client": client_id,
        "X-CoinPayments-Timestamp": timestamp,
        "X-CoinPayments-Signature": _signature(method, url, client_id, timestamp, body, secret),
        "User-Agent": "WorldWar3Bot-CryptoGateway/1.0",
    }
    req = urllib.request.Request(url, data=body if method.upper() != "GET" else None, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise CryptoGatewayError(f"خطای CoinPayments ({exc.code})") from None
    except (urllib.error.URLError, TimeoutError) as exc:
        raise CryptoGatewayError(f"ارتباط با CoinPayments برقرار نشد: {type(exc).__name__}") from None
    except json.JSONDecodeError:
        raise CryptoGatewayError("پاسخ نامعتبر از CoinPayments دریافت شد.") from None


def _public_usd_per_toman_sync() -> Decimal:
    # Open Exchange Rates API used only as a public FX source. It returns USD
    # base rates; IRR is Rial, so divide by 10 for Toman.
    url = "https://open.er-api.com/v6/latest/USD"
    req = urllib.request.Request(url, headers={"User-Agent": "WorldWar3Bot-CryptoGateway/1.0"})
    with urllib.request.urlopen(req, timeout=15) as response:
        data = json.loads(response.read().decode("utf-8", errors="replace"))
    irr = Decimal(str((data.get("rates") or {}).get("IRR") or "0"))
    if irr <= 0:
        raise CryptoGatewayError("نرخ USD/IRR در دسترس نیست.")
    return irr / Decimal(10)


async def create_crypto_invoice(session, tx: WalletTransaction, selected: str):
    selected = str(selected or "").upper()
    payment_currency = PAYMENT_CURRENCIES.get(selected)
    if not payment_currency:
        raise CryptoGatewayError("ارز رمز ارز پشتیبانی نمی‌شود.")
    if not crypto_gateway_configured(session):
        raise CryptoGatewayError("درگاه رمز ارز هنوز توسط اونر تنظیم نشده است.")

    requested = Decimal(int(tx.requested_amount))
    markup = Decimal(str(get_float(session, CRYPTO_MARKUP_PERCENT, 0, 1000)))
    charge_toman = (requested * (Decimal(1) + markup / Decimal(100))).quantize(Decimal("1"), rounding=ROUND_CEILING)
    usd_per_toman = await asyncio.to_thread(_public_usd_per_toman_sync)
    usd_amount = (charge_toman * usd_per_toman).quantize(Decimal("0.01"), rounding=ROUND_CEILING)
    if usd_amount <= 0:
        raise CryptoGatewayError("مبلغ معادل دلاری نامعتبر است.")

    expires_minutes = max(1, get_int(session, WALLET_PAYMENT_EXPIRY_MINUTES, 30))
    expires = datetime.utcnow() + timedelta(minutes=expires_minutes)
    invoice_no = tx.transaction_no
    webhook_url = None
    if get_bool(session, CRYPTO_WEBHOOK_ENABLED) and PAYMENT_WEB_BASE_URL:
        webhook_url = f"{PAYMENT_WEB_BASE_URL.rstrip('/')}/payments/coinpayments/webhook"

    payload = {
        "currency": get_setting(session, CRYPTO_FIAT_CURRENCY, "USD").strip() or "USD",
        "items": [{
            "name": "افزایش موجودی کیف پول",
            "description": f"تراکنش {invoice_no}",
            "quantity": {"value": 1, "type": "quantity"},
            "amount": str(usd_amount),
        }],
        "amount": {
            "breakdown": {"subtotal": str(usd_amount)},
            "total": str(usd_amount),
        },
        "invoiceId": invoice_no,
        "customData": {
            "transaction_id": str(tx.id),
            "transaction_no": invoice_no,
            "user_id": str(tx.user_id),
        },
        "notes": "Wallet crypto payment",
        "notesToRecipient": "پرداخت افزایش موجودی کیف پول",
        "payment": {
            "paymentCurrency": payment_currency,
            "isSimpleQR": False,
        },
    }
    if webhook_url:
        payload["webhooks"] = [{
            "notificationsUrl": webhook_url,
            "notifications": ["invoicePaid", "invoiceCompleted", "invoiceCancelled", "invoiceTimedOut"],
        }]

    response = await asyncio.to_thread(_request_sync, session, "POST", "/v2/merchant/invoices", payload)
    invoices = response.get("invoices") or []
    invoice = invoices[0] if invoices else response.get("invoice") or {}
    invoice_id = str(invoice.get("id") or "")
    link = str(invoice.get("checkoutLink") or invoice.get("link") or "")
    payment = invoice.get("payment") or {}
    payment_id = str(payment.get("paymentId") or "")
    # CoinPayments may expose its own provider-side timeout, but the bot's
    # transaction expiry remains the single Owner-configured general payment deadline.
    # Store provider metadata separately; do not replace tx.expires_at with it.
    gateway_expires = payment.get("expires")
    if not invoice_id or not link:
        raise CryptoGatewayError("CoinPayments فاکتور معتبر برنگرداند.")

    save_metadata(tx, {
        **metadata(tx),
        "provider": "coinpayments",
        "provider_invoice_id": invoice_id,
        "provider_payment_id": payment_id,
        "payment_currency": payment_currency,
        "selected_coin": selected,
        "charge_toman": str(charge_toman),
        "usd_amount": str(usd_amount),
        "usd_per_toman": str(usd_per_toman),
        "gateway_expires_at": str(gateway_expires or ""),
        "gateway_link": link,
    })
    tx.external_id = invoice_id
    tx.payment_amount = int(charge_toman)
    tx.status = STATUS_WAITING_PAYMENT
    tx.destination = link
    tx.expires_at = expires
    session.flush()
    return {
        "invoice_id": invoice_id,
        "payment_id": payment_id,
        "link": link,
        "selected": selected,
        "payment_currency": payment_currency,
        "charge_toman": int(charge_toman),
        "usd_amount": str(usd_amount),
        "expires": expires,
    }


def _extract_status(payload: dict) -> str:
    return str(payload.get("status") or "").strip()


def _invoice_payment_amount_ok(invoice: dict, expected_usd: Decimal) -> bool:
    amount = invoice.get("amount") or {}
    total = amount.get("total")
    if total is None:
        try:
            total = invoice.get("total")
        except Exception:
            total = None
    try:
        return Decimal(str(total)) >= expected_usd
    except Exception:
        return False


def _invoice_event_matches_tx(invoice: dict, tx: WalletTransaction) -> bool:
    data = metadata(tx)
    custom = invoice.get("customData") or {}
    if custom.get("transaction_id") and str(custom.get("transaction_id")) != str(tx.id):
        return False
    if custom.get("transaction_no") and str(custom.get("transaction_no")) != tx.transaction_no:
        return False
    if invoice.get("invoiceId") and str(invoice.get("invoiceId")) != tx.transaction_no:
        return False
    if data.get("provider_invoice_id") and str(invoice.get("id")) != str(data.get("provider_invoice_id")):
        return False
    return True


def finalize_crypto_invoice(session, tx: WalletTransaction, invoice: dict):
    if tx.status == STATUS_APPROVED:
        return True, "قبلاً تأیید شده است."
    if tx.status in {STATUS_CANCELLED, STATUS_EXPIRED}:
        return False, "این تراکنش دیگر قابل تأیید نیست."
    if not _invoice_event_matches_tx(invoice, tx):
        return False, "شناسه فاکتور با تراکنش ربات تطابق ندارد."
    status = _extract_status(invoice)
    if status not in {"paid", "completed"}:
        return False, "پرداخت هنوز نهایی نشده است."
    data = metadata(tx)
    expected_usd = Decimal(str(data.get("usd_amount") or "0"))
    if expected_usd <= 0 or not _invoice_payment_amount_ok(invoice, expected_usd):
        return False, "مبلغ فاکتور با مبلغ ثبت‌شده مطابقت ندارد."
    tx.external_reference = str(invoice.get("id") or tx.external_id or "")
    paid_hash = ""
    for item in invoice.get("payoutDetails", {}).get("paidTransactions", []) or []:
        paid_hash = str(item.get("hash") or item.get("completedTxId") or "")
        if paid_hash:
            break
    if paid_hash:
        data["tx_hash"] = paid_hash
    data["gateway_status"] = status
    save_metadata(tx, data)
    ok, error = approve_deposit(session, tx, int(tx.requested_amount), external_reference=paid_hash or tx.external_id)
    return ok, error


async def poll_one_crypto_transaction(tx: WalletTransaction):
    with SessionLocal() as session:
        fresh = session.get(WalletTransaction, tx.id)
        if not fresh or fresh.method != "crypto" or fresh.status in {STATUS_APPROVED, STATUS_CANCELLED, STATUS_EXPIRED}:
            return None
        data = metadata(fresh)
        invoice_id = str(data.get("provider_invoice_id") or fresh.external_id or "")
        if not invoice_id:
            return None
        try:
            invoice = await asyncio.to_thread(_request_sync, session, "GET", f"/v2/merchant/invoices/{urllib.parse.quote(invoice_id, safe='')}")
            status = _extract_status(invoice)
            if status in {"cancelled", "timedOut", "deleted"}:
                fresh.status = STATUS_CANCELLED if status == "cancelled" else STATUS_EXPIRED
                fresh.updated_at = datetime.utcnow()
                session.commit()
                return {"tx": fresh, "status": fresh.status, "changed": True}
            if status in {"paid", "completed"}:
                ok, error = finalize_crypto_invoice(session, fresh, invoice)
                session.commit()
                return {"tx": fresh, "status": fresh.status, "changed": ok, "error": error, "invoice": invoice}
            session.commit()
            return {"tx": fresh, "status": status, "changed": False}
        except Exception as exc:
            session.rollback()
            LOGGER.warning("Crypto invoice poll failed for %s: %s", invoice_id, type(exc).__name__)
            return None


async def crypto_invoice_poll_worker(app):
    await asyncio.sleep(3)
    interval = 60
    while True:
        try:
            with SessionLocal() as session:
                if not crypto_gateway_configured(session):
                    interval = 60
                    tx_ids = []
                else:
                    interval = max(20, min(300, get_int(session, CRYPTO_POLL_SECONDS, 60)))
                    tx_ids = [
                        int(x.id) for x in session.scalars(
                            select(WalletTransaction).where(
                                WalletTransaction.method == "crypto",
                                WalletTransaction.status == STATUS_WAITING_PAYMENT,
                                WalletTransaction.external_id.is_not(None),
                            ).order_by(WalletTransaction.id).limit(25)
                        ).all()
                    ]
            for tx_id in tx_ids:
                result = await poll_one_crypto_transaction(type("Tx", (), {"id": tx_id})())
                if not result or not result.get("changed"):
                    continue
                tx = result["tx"]
                if result.get("status") == STATUS_APPROVED:
                    try:
                        await app.bot.send_message(
                            chat_id=tx.user_id,
                            text=f"✅ <b>پرداخت رمز ارزی تأیید شد.</b>\n\n🧾 تراکنش: <code>{tx.transaction_no}</code>\n💰 مبلغ اضافه‌شده: <b>{format_amount(tx.credited_amount)} تومان</b>",
                            parse_mode="HTML",
                        )
                    except Exception:
                        pass
                elif result.get("status") in {STATUS_CANCELLED, STATUS_EXPIRED}:
                    try:
                        await app.bot.send_message(chat_id=tx.user_id, text="⏰ فاکتور رمز ارزی منقضی یا لغو شد. برای پرداخت دوباره، درخواست جدید ایجاد کنید.")
                    except Exception:
                        pass
        except asyncio.CancelledError:
            raise
        except Exception:
            LOGGER.exception("Crypto gateway worker failed")
        await asyncio.sleep(interval)


async def process_crypto_webhook(payload: dict):
    custom = payload.get("customData") or {}
    tx_id = custom.get("transaction_id")
    tx_no = custom.get("transaction_no")
    invoice_id = str(payload.get("id") or "")
    with SessionLocal() as session:
        tx = None
        if tx_id:
            try:
                tx = session.get(WalletTransaction, int(tx_id))
            except Exception:
                tx = None
        if tx is None and tx_no:
            tx = session.scalar(select(WalletTransaction).where(WalletTransaction.transaction_no == str(tx_no)))
        if tx is None and invoice_id:
            tx = session.scalar(select(WalletTransaction).where(WalletTransaction.external_id == invoice_id, WalletTransaction.method == "crypto"))
        if tx is None:
            return False, "تراکنش پیدا نشد."
        if tx.status == STATUS_APPROVED:
            return True, "قبلاً تأیید شده است."
        if tx.method != "crypto":
            return False, "نوع تراکنش نامعتبر است."
        if transaction_is_expired(tx) and _extract_status(payload) not in {"paid", "completed"}:
            tx.status = STATUS_EXPIRED
            session.commit()
            return False, "تراکنش منقضی شده است."
        if invoice_id:
            data = metadata(tx)
            if data.get("provider_invoice_id") and str(data.get("provider_invoice_id")) != invoice_id:
                return False, "شناسه فاکتور نامعتبر است."
            try:
                full = await asyncio.to_thread(_request_sync, session, "GET", f"/v2/merchant/invoices/{urllib.parse.quote(invoice_id, safe='')}")
                if isinstance(full, dict) and full.get("id"):
                    payload = full
            except Exception:
                pass
        ok, error = finalize_crypto_invoice(session, tx, payload)
        session.commit()
        return ok, error or "تأیید شد."


def verify_webhook_signature(headers: dict, raw_body: bytes, url: str, client_secret: str) -> bool:
    client = headers.get("X-CoinPayments-Client") or headers.get("x-coinpayments-client")
    timestamp = headers.get("X-CoinPayments-Timestamp") or headers.get("x-coinpayments-timestamp")
    signature = headers.get("X-CoinPayments-Signature") or headers.get("x-coinpayments-signature")
    if not client or not timestamp or not signature:
        return False
    try:
        stamp = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return False
    if abs((datetime.utcnow() - stamp).total_seconds()) > 300:
        return False
    expected = _signature("POST", url, client, timestamp, raw_body, client_secret)
    return hmac.compare_digest(expected, signature)
