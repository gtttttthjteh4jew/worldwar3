"""تهیه، نگهداری، فهرست و ارسال نسخه‌های پشتیبان SQLite برای Owner."""
from __future__ import annotations

import asyncio
import logging
import os
import re
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import func, select

from config import BASE_DIR, DATABASE_URL, OWNER_ID
from database.db import SessionLocal
from database.models import BackupRecord, BotSetting
from services.settings import get_backup_interval, get_backup_started, get_backup_execution_time
from services.error_reporting import report_exception

log = logging.getLogger("worldwar3_bot.backup")
TZ = ZoneInfo("Asia/Tehran")
BACKUP_DIR = BASE_DIR / "backups"
BACKUP_SEND_COUNT_KEY = "worldwar3_backup_send_count"
_BACKUP_NUMBER_LOCK = threading.RLock()
BACKUP_HISTORY_LIMIT = 100


def database_path() -> Path:
    if not DATABASE_URL.startswith("sqlite:"):
        raise RuntimeError("پشتیبان‌گیری فقط برای پایگاه‌داده SQLite فعال است.")
    raw = DATABASE_URL[len("sqlite:///"):]
    if raw.startswith("/"):
        return Path(raw)
    return (BASE_DIR / raw).resolve()


def _zip_database() -> Path:
    """یک Snapshot سازگار از آخرین وضعیت commitشده دیتابیس تهیه می‌کند.

    از SQLite Online Backup API استفاده می‌شود تا دیتابیس اصلی، حتی در حالت WAL،
    به‌صورت یک فایل مستقل و قابل‌بازشدن ذخیره شود. قفل کوتاه BEGIN IMMEDIATE نیز
    از شروع write جدید تا پایان snapshot جلوگیری می‌کند.
    """
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    source = database_path()
    if not source.exists():
        raise FileNotFoundError(f"Database not found: {source}")

    stamp = datetime.now(TZ).strftime("%Y%m%d_%H%M%S_%f")
    snapshot = BACKUP_DIR / f".snapshot_{stamp}.tmp"
    last_error = None

    for attempt in range(6):
        lock_conn = src = dst = None
        locked = False
        try:
            lock_conn = sqlite3.connect(str(source), timeout=60, isolation_level=None)
            lock_conn.execute("PRAGMA busy_timeout=60000")
            lock_conn.execute("BEGIN IMMEDIATE")
            locked = True

            src = sqlite3.connect(str(source), timeout=60)
            src.execute("PRAGMA busy_timeout=60000")
            snapshot.unlink(missing_ok=True)
            dst = sqlite3.connect(str(snapshot), timeout=60)
            dst.execute("PRAGMA synchronous=FULL")
            src.backup(dst)
            check = dst.execute("PRAGMA integrity_check").fetchone()
            if not check or str(check[0]).lower() != "ok":
                raise sqlite3.DatabaseError(f"Backup integrity check failed: {check}")

            dst.close(); dst = None
            src.close(); src = None
            lock_conn.execute("ROLLBACK")
            locked = False
            lock_conn.close(); lock_conn = None
            return snapshot
        except sqlite3.OperationalError as exc:
            last_error = exc
            if attempt >= 5 or "locked" not in str(exc).lower():
                snapshot.unlink(missing_ok=True)
                raise
            time.sleep(1.0 + attempt * 0.5)
        except Exception:
            snapshot.unlink(missing_ok=True)
            raise
        finally:
            for conn in (dst, src):
                if conn is not None:
                    try:
                        conn.close()
                    except Exception:
                        pass
            if lock_conn is not None:
                try:
                    if locked:
                        lock_conn.execute("ROLLBACK")
                except Exception:
                    pass
                try:
                    lock_conn.close()
                except Exception:
                    pass

    raise last_error or RuntimeError("SQLite backup failed")


def _relative_record_path(record: BackupRecord | dict) -> Path:
    raw = record.file_path if isinstance(record, BackupRecord) else record.get("file_path")
    path = Path(str(raw or ""))
    return path if path.is_absolute() else (BASE_DIR / path).resolve()


def _legacy_counter(session) -> int:
    row = session.scalar(select(BotSetting).where(BotSetting.key == BACKUP_SEND_COUNT_KEY))
    try:
        return max(0, int(row.value)) if row and row.value is not None else 0
    except (TypeError, ValueError):
        return 0


def _register_snapshot(snapshot: Path, kind: str) -> dict:
    """برای Snapshot شماره متوالی رزرو می‌کند و آن را در تاریخچه ثبت می‌کند."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    with _BACKUP_NUMBER_LOCK:
        with SessionLocal() as session:
            last_sequence = session.scalar(select(func.max(BackupRecord.sequence))) or 0
            sequence = max(int(last_sequence), _legacy_counter(session)) + 1
            filename = f"worldwar3_{sequence}.db"
            permanent_path = BACKUP_DIR / filename
            if permanent_path.exists():
                permanent_path.unlink()
            os.replace(snapshot, permanent_path)

            stat = permanent_path.stat()
            record = BackupRecord(
                sequence=sequence,
                filename=filename,
                file_path=str(permanent_path.relative_to(BASE_DIR)),
                kind=str(kind or "automatic"),
                created_at=datetime.utcnow(),
                sent_at=None,
                size_bytes=int(stat.st_size),
            )
            session.add(record)
            counter = session.scalar(select(BotSetting).where(BotSetting.key == BACKUP_SEND_COUNT_KEY))
            if counter is None:
                session.add(BotSetting(key=BACKUP_SEND_COUNT_KEY, value=str(sequence)))
            else:
                counter.value = str(sequence)
            session.commit()
            record_id = int(record.id)

    _prune_history()
    result = get_backup_record(record_id)
    if result is None:
        raise RuntimeError("ثبت اطلاعات نسخه پشتیبان ناموفق بود.")
    return result


def _prune_history() -> None:
    """صد نسخه ارسال‌شده اخیر را نگه می‌دارد؛ موارد ارسال‌نشده برای retry حفظ می‌شوند."""
    with SessionLocal() as session:
        old_records = session.scalars(
            select(BackupRecord)
            .where(BackupRecord.sent_at.is_not(None))
            .order_by(BackupRecord.sequence.desc())
            .offset(BACKUP_HISTORY_LIMIT)
        ).all()
        for record in old_records:
            try:
                _relative_record_path(record).unlink(missing_ok=True)
            except Exception:
                log.exception("Could not remove old backup file %s", record.filename)
            session.delete(record)
        if old_records:
            session.commit()


def _record_to_dict(record: BackupRecord) -> dict:
    return {
        "id": int(record.id),
        "sequence": int(record.sequence),
        "filename": str(record.filename),
        "file_path": str(record.file_path),
        "kind": str(record.kind or "automatic"),
        "created_at": record.created_at,
        "sent_at": record.sent_at,
        "size_bytes": int(record.size_bytes or 0),
        "last_error": record.last_error,
    }


def get_backup_record(record_id: int) -> dict | None:
    with SessionLocal() as session:
        record = session.get(BackupRecord, int(record_id))
        return _record_to_dict(record) if record else None


def get_backup_records_page(page: int = 1) -> tuple[list[dict], int, int]:
    """حداکثر ۱۰۰ نسخه اخیر را با ۱۰ مورد در هر صفحه برمی‌گرداند."""
    page = max(1, int(page or 1))
    with SessionLocal() as session:
        records = session.scalars(
            select(BackupRecord)
            .order_by(BackupRecord.sequence.desc())
            .limit(BACKUP_HISTORY_LIMIT)
        ).all()
        items = [_record_to_dict(record) for record in records]
    total_pages = max(1, (len(items) + 9) // 10)
    page = min(page, total_pages)
    start = (page - 1) * 10
    return items[start:start + 10], page, total_pages


def _format_backup_datetime(value) -> str:
    if value is None:
        return "ثبت نشده"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(TZ).strftime("%Y-%m-%d | %H:%M:%S")


def backup_record_detail_text(record: dict) -> str:
    kind = "فوری" if record.get("kind") == "manual" else "خودکار"
    status = "✅ ارسال‌شده" if record.get("sent_at") else "⏳ در انتظار ارسال"
    size_mb = float(record.get("size_bytes") or 0) / (1024 * 1024)
    return (
        f"💾 <b>جزئیات نسخه پشتیبان شماره {int(record['sequence'])}</b>\n\n"
        f"📄 نام فایل: <code>{record['filename']}</code>\n"
        f"🗂 نوع: <b>{kind}</b>\n"
        f"🕐 زمان تهیه: <b>{_format_backup_datetime(record.get('created_at'))}</b>\n"
        f"📦 حجم فایل: <b>{size_mb:.2f} مگابایت</b>\n"
        f"📤 وضعیت ارسال: <b>{status}</b>"
    )


async def _deliver_record(bot, record_id: int) -> bool:
    if not OWNER_ID:
        log.error("OWNER_ID is not configured; backup remains queued (record=%s)", record_id)
        return False
    record = get_backup_record(record_id)
    if not record:
        raise FileNotFoundError("اطلاعات نسخه پشتیبان پیدا نشد.")
    path = _relative_record_path(record)
    if not path.is_file():
        raise FileNotFoundError(f"فایل نسخه پشتیبان موجود نیست: {record['filename']}")

    kind_label = "فوری" if record["kind"] == "manual" else "خودکار"
    caption = (
        f"💾 <b>نسخه پشتیبان پایگاه‌داده شماره {record['sequence']}</b>\n\n"
        f"🗂 نوع: <b>{kind_label}</b>\n"
        f"🕐 زمان تهیه: <b>{_format_backup_datetime(record['created_at'])}</b>\n"
        "🔒 فایل دیتابیس کامل ربات است؛ آن را در محل امن نگهداری کنید."
    )
    try:
        with path.open("rb") as file_handle:
            await bot.send_document(
                chat_id=int(OWNER_ID),
                document=file_handle,
                filename=record["filename"],
                caption=caption,
                parse_mode="HTML",
            )
        with SessionLocal() as session:
            current = session.get(BackupRecord, int(record_id))
            if current is not None:
                current.sent_at = datetime.utcnow()
                current.last_error = None
                session.commit()
        _prune_history()
        return True
    except Exception as exc:
        with SessionLocal() as session:
            current = session.get(BackupRecord, int(record_id))
            if current is not None:
                current.last_error = str(exc)[:2000]
                session.commit()
        raise


async def backup_now(bot) -> bool:
    """در همان لحظه درخواست، Snapshot کامل DB می‌گیرد و برای Owner می‌فرستد."""
    snapshot = await asyncio.to_thread(_zip_database)
    record = await asyncio.to_thread(_register_snapshot, snapshot, "manual")
    return await _deliver_record(bot, int(record["id"]))


async def resend_backup(bot, record_id: int) -> bool:
    """ارسال مجدد همان فایل ذخیره‌شده؛ شماره‌گذاری جدید ایجاد نمی‌کند."""
    if not OWNER_ID:
        return False
    record = get_backup_record(int(record_id))
    if not record:
        raise FileNotFoundError("نسخه پشتیبان موردنظر پیدا نشد.")
    path = _relative_record_path(record)
    if not path.is_file():
        raise FileNotFoundError("فایل این نسخه پشتیبان روی سرور موجود نیست.")
    with path.open("rb") as file_handle:
        await bot.send_document(
            chat_id=int(OWNER_ID),
            document=file_handle,
            filename=record["filename"],
            caption=(
                f"📤 <b>ارسال مجدد نسخه پشتیبان شماره {record['sequence']}</b>\n"
                f"🕐 زمان تهیه: <b>{_format_backup_datetime(record['created_at'])}</b>"
            ),
            parse_mode="HTML",
        )
    return True


async def _import_legacy_pending_files() -> None:
    """فایل‌های معلق باقی‌مانده از نسخه قدیمی را هم وارد تاریخچه جدید می‌کند."""
    legacy_pattern = re.compile(r"^worldwar3_\d{8}_\d{6}_\d+\.db$")
    for archive in sorted(BACKUP_DIR.glob("worldwar3_*.db")):
        if not archive.is_file() or not legacy_pattern.match(archive.name):
            continue
        try:
            snapshot = archive
            await asyncio.to_thread(_register_snapshot, snapshot, "automatic")
        except Exception:
            log.exception("Could not import legacy pending backup %s", archive)


async def _retry_pending(app) -> None:
    await _import_legacy_pending_files()
    with SessionLocal() as session:
        pending_ids = list(session.scalars(
            select(BackupRecord.id)
            .where(BackupRecord.sent_at.is_(None))
            .order_by(BackupRecord.sequence.asc())
        ).all())
    for record_id in pending_ids:
        try:
            await _deliver_record(app.bot, int(record_id))
        except Exception as exc:
            log.exception("Backup retry failed (record=%s)", record_id)
            try:
                await report_exception(app.bot, exc, source="🚨 خطای تلاش مجدد پشتیبان")
            except Exception:
                pass
            break


def _next_execution(now: datetime, execution_time: str, interval_minutes: int = 60) -> datetime:
    """نوبت آینده را از زمان اجرای روزانه و با فاصله ثابت محاسبه می‌کند.

    مثال: زمان اجرا 21:00 و فاصله 180 دقیقه => 21:00، 00:00، 03:00 و ... .
    محاسبه از لنگر انجام می‌شود و به ساعت ارسال دستی وابسته نیست.
    """
    try:
        hour, minute = map(int, str(execution_time).split(":", 1))
        hour = max(0, min(23, hour))
        minute = max(0, min(59, minute))
    except Exception:
        hour, minute = 0, 0
    interval = max(1, int(interval_minutes or 60))
    today_anchor = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    # اگر از ساعت اجرا عبور کرده‌ایم، لنگر امروز است؛ در غیر این صورت
    # زنجیره فاصله‌ها از اجرای روز قبل ادامه پیدا می‌کند (مثلاً 21، 00، 03).
    anchor = today_anchor if now >= today_anchor else today_anchor - timedelta(days=1)
    elapsed = max(0.0, (now - anchor).total_seconds())
    interval_seconds = interval * 60
    # ceil باعث می‌شود اگر برنامه دقیقاً روی مرز اجرا راه‌اندازی شد، همان نوبت
    # برگردانده شود؛ و اگر اندکی از آن گذشته بود، نوبت بعدی انتخاب شود.
    import math
    steps = int(math.ceil(elapsed / interval_seconds))
    return anchor + timedelta(minutes=steps * interval)


async def backup_worker(app):
    """اجرای خودکار بر اساس لنگر زمانی؛ بکاپ فوری برنامه خودکار را جابه‌جا نمی‌کند."""
    next_run = None
    schedule_key = None
    last_retry = 0.0

    while True:
        try:
            with SessionLocal() as session:
                started = get_backup_started(session)
                interval = max(1, int(get_backup_interval(session)))
                execution_time = get_backup_execution_time(session)

            now = datetime.now(TZ)
            current_key = (bool(started), int(interval), str(execution_time))
            if not started:
                next_run = None
                schedule_key = None
                await asyncio.sleep(5)
                continue

            if schedule_key != current_key or next_run is None:
                schedule_key = current_key
                next_run = _next_execution(now, execution_time, interval)

            now = datetime.now(TZ)
            retry_due = time.monotonic() - last_retry >= 60
            if now < next_run:
                # تا نزدیک نوبت بعدی، تنظیمات را با فاصله یک‌ثانیه‌ای بررسی می‌کنیم
                # تا زمان اجرا و تغییرات Owner با کمترین تأخیر اعمال شوند.
                if retry_due:
                    await _retry_pending(app)
                    last_retry = time.monotonic()
                    continue
                await asyncio.sleep(min(1, max(0.1, (next_run - now).total_seconds())))
                continue

            # اگر نوبت خودکار رسیده باشد، اول Snapshot همان لحظه گرفته می‌شود؛
            # ارسال مجدد فایل‌های قدیمی نباید اجرای زمان‌بندی‌شده را عقب بیندازد.
            scheduled_run = next_run
            snapshot = await asyncio.to_thread(_zip_database)
            record = await asyncio.to_thread(_register_snapshot, snapshot, "automatic")
            try:
                await _deliver_record(app.bot, int(record["id"]))
            except Exception as exc:
                log.exception("Fresh backup delivery failed (record=%s)", record.get("id"))
                try:
                    await report_exception(app.bot, exc, source="🚨 خطای ارسال پشتیبان")
                except Exception:
                    pass

            # نوبت بعدی دقیقاً از نوبت برنامه‌ریزی‌شده قبلی مشتق می‌شود؛
            # ارسال دستی یا چند ثانیه تأخیر، زنجیره خودکار را جابه‌جا نمی‌کند.
            next_run = scheduled_run + timedelta(minutes=interval)
            current_time = datetime.now(TZ)
            while next_run <= current_time:
                next_run += timedelta(minutes=interval)
            if retry_due:
                await _retry_pending(app)
                last_retry = time.monotonic()

        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.exception("Backup worker error")
            try:
                await report_exception(app.bot, exc, source="🚨 خطای پشتیبان‌گیری خودکار")
            except Exception:
                pass
            await asyncio.sleep(30)
