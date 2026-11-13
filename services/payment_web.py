from __future__ import annotations

import asyncio
import html
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.parse import parse_qs, urlparse
import json

from config import OWNER_ID
from database.db import SessionLocal
from database.models import WalletTransaction
from services.wallet import STATUS_EXPIRED, STATUS_WAITING_PAYMENT, approve_deposit, transaction_is_expired, zarinpal_verify
from services.crypto_gateway import CRYPTO_CLIENT_SECRET, process_crypto_webhook, verify_webhook_signature


class _CallbackHandler(BaseHTTPRequestHandler):
    server_version = "WalletPaymentCallback/1.0"

    def log_message(self, format, *args):
        return

    def do_GET(self):
        loop = getattr(self.server, "wallet_loop", None)
        if loop is None:
            self._respond("500 Internal Server Error", "پردازشگر درگاه آماده نیست.")
            return
        try:
            query = parse_qs(urlparse(self.path).query)
            if urlparse(self.path).path != "/payments/zarinpal/callback":
                self._respond("404 Not Found", "مسیر پیدا نشد.")
                return
            future = asyncio.run_coroutine_threadsafe(_process_zarinpal_callback(query), loop)
            result = future.result(timeout=35)
            self._respond("200 OK", result)
        except Exception as exc:
            self._respond("500 Internal Server Error", f"خطا در پردازش پرداخت: {html.escape(str(exc))}")

    def do_POST(self):
        loop = getattr(self.server, "wallet_loop", None)
        if loop is None:
            self._respond("500 Internal Server Error", "پردازشگر درگاه آماده نیست.")
            return
        path = urlparse(self.path).path
        if path != "/payments/coinpayments/webhook":
            self._respond("404 Not Found", "مسیر پیدا نشد.")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(max(0, length))
            app = getattr(_CallbackHandler, "wallet_app", None)
            secret = ""
            expected_client = ""
            if app is not None:
                with SessionLocal() as session:
                    getter = __import__("services.wallet", fromlist=["get_setting"]).get_setting
                    secret = getter(session, CRYPTO_CLIENT_SECRET, "").strip()
                    expected_client = getter(session, "wallet_crypto_client_id", "").strip()
            if not secret:
                self._respond("503 Service Unavailable", "درگاه رمز ارز تنظیم نشده است.")
                return
            url = getattr(self.server, "public_crypto_webhook_url", "") or f"http://{self.headers.get('Host', '')}{path}"
            headers = {k: v for k, v in self.headers.items()}
            received_client = headers.get("X-CoinPayments-Client") or headers.get("x-coinpayments-client")
            if not expected_client or received_client != expected_client:
                self._respond("401 Unauthorized", "شناسه اتصال معتبر نیست.")
                return
            if not verify_webhook_signature(headers, raw, url, secret):
                self._respond("401 Unauthorized", "امضای درخواست معتبر نیست.")
                return
            payload = json.loads(raw.decode("utf-8"))
            future = asyncio.run_coroutine_threadsafe(process_crypto_webhook(payload), loop)
            ok, result = future.result(timeout=25)
            self._respond("200 OK" if ok else "202 Accepted", "ok" if ok else "accepted")
        except Exception:
            self._respond("500 Internal Server Error", "خطا در پردازش وب‌هوک.")

    def _respond(self, status, text):
        body = f"<html><meta charset='utf-8'><body style='font-family:sans-serif;direction:rtl;text-align:center;padding:40px'><h2>{text}</h2><p>می‌توانید این صفحه را ببندید و به ربات برگردید.</p></body></html>".encode("utf-8")
        code = int(status.split()[0])
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


async def _process_zarinpal_callback(query):
    status = str((query.get("Status") or [""])[0])
    authority = str((query.get("Authority") or [""])[0])
    if not authority:
        return "❌ اطلاعات Callback ناقص است."
    with SessionLocal() as session:
        tx = session.query(WalletTransaction).filter(WalletTransaction.external_id == authority).first()
        if tx is None:
            return "❌ تراکنش مرتبط پیدا نشد."
        if tx.status == "APPROVED":
            return "✅ این پرداخت قبلاً ثبت شده است."
        if status.upper() != "OK":
            if tx.status not in {"APPROVED", "REJECTED", "CANCELLED", "EXPIRED"}:
                tx.status = "CANCELLED"
                tx.updated_at = datetime.utcnow()
                session.commit()
                await session_bind_bot_send_message(tx.user_id, f"❌ پرداخت زرین‌پال انجام نشد.\n\n🧾 تراکنش: {tx.transaction_no}")
            return "❌ پرداخت توسط کاربر لغو شد یا موفق نبود."

        result = await zarinpal_verify(session, tx)
        if not result.get("ok"):
            session.rollback()
            await session_bind_bot_send_message(tx.user_id, f"⚠️ تأیید پرداخت زرین‌پال ناموفق بود.\n\n🧾 تراکنش: {tx.transaction_no}\nاگر مبلغ از حساب شما کسر شده است، نتیجه را از پشتیبانی پیگیری کنید.")
            return "❌ پرداخت قابل تأیید نبود. در صورت کسر وجه، نتیجه را از پشتیبانی/Owner پیگیری کنید."

        if transaction_is_expired(tx) or tx.status != STATUS_WAITING_PAYMENT:
            tx.status = STATUS_EXPIRED
            session.commit()
            try:
                await session_bind_bot_send_message(tx.user_id, "⚠️ پرداخت زرین‌پال شما تأیید شد، اما درخواست کیف پول منقضی شده بود و به‌صورت خودکار به موجودی اضافه نشد. Owner باید این مورد را بررسی کند.")
                await session_bind_bot_send_message(OWNER_ID, f"⚠️ پرداخت دیرهنگام زرین‌پال\nتراکنش: {tx.transaction_no}\nAuthority: {authority}\nمبلغ: {tx.payment_amount:,} تومان\nنیاز به بررسی دستی دارد.")
            except Exception:
                pass
            return "⚠️ پرداخت تأیید شد اما درخواست منقضی شده بود؛ Owner باید آن را بررسی کند."

        ok, error = approve_deposit(session, tx, tx.requested_amount, external_reference=result.get("ref_id") or authority)
        session.commit()
        if not ok:
            return f"❌ {error}"
        try:
            await session_bind_bot_send_message(
                tx.user_id,
                f"✅ افزایش موجودی با زرین‌پال موفق بود.\n\n🧾 تراکنش: {tx.transaction_no}\n💰 مبلغ اضافه‌شده: {tx.credited_amount:,} تومان",
            )
        except Exception:
            pass
        return "✅ پرداخت با موفقیت تأیید شد. می‌توانید این صفحه را ببندید و به ربات برگردید."


async def session_bind_bot_send_message(chat_id, text):
    # The active PTB application is injected when the server starts.
    app = getattr(_CallbackHandler, "wallet_app", None)
    if app is not None:
        try:
            await app.bot.send_message(chat_id=int(chat_id), text=text)
        except Exception:
            pass


def start_payment_callback_server(loop, host: str, port: int, app):
    server = ThreadingHTTPServer((str(host), int(port)), _CallbackHandler)
    server.wallet_loop = loop
    server.wallet_app = app
    _CallbackHandler.wallet_app = app
    try:
        from config import PAYMENT_WEB_BASE_URL
        server.public_crypto_webhook_url = f"{PAYMENT_WEB_BASE_URL.rstrip('/')}/payments/coinpayments/webhook" if PAYMENT_WEB_BASE_URL else ""
    except Exception:
        server.public_crypto_webhook_url = ""
    _CallbackHandler.server_class = server
    thread = Thread(target=server.serve_forever, name="wallet_payment_callback", daemon=True)
    thread.start()
    return server, thread


def stop_payment_callback_server(server):
    if server is not None:
        try:
            server.shutdown()
            server.server_close()
        except Exception:
            pass
