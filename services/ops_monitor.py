from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from config import BASE_DIR, DATABASE_URL, OWNER_ID
from database.db import SessionLocal
from database.models import BotSetting
from services.settings import set_bot_shutdown_mode

ERRORS_KEY = "ww3_error_center_v1"
ALERTS_KEY = "ww3_alert_center_v1"
ERROR_STREAK_KEY = "ww3_internal_error_streak"
EMERGENCY_KEY = "ww3_emergency_shutdown_reason"
PROCESS_STARTED = time.time()

_SECRET_PATTERNS = [
    (re.compile(r"(?i)(bot[_ -]?token\s*[=:]\s*)[^\s,;]+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(api[_ -]?key\s*[=:]\s*)[^\s,;]+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(password|secret|authorization)\s*[=:]\s*[^\s,;]+"), r"\1=[REDACTED]"),
    (re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{30,}\b"), "[REDACTED_TELEGRAM_TOKEN]"),
]


def _setting(session, key: str):
    return session.scalar(select(BotSetting).where(BotSetting.key == key))


def _get_json(session, key: str, default):
    row = _setting(session, key)
    try:
        data = json.loads(row.value) if row and row.value else default
        return data if isinstance(data, type(default)) else default
    except Exception:
        return default


def _set_json(session, key: str, value):
    row = _setting(session, key)
    raw = json.dumps(value, ensure_ascii=False)
    if row is None:
        session.add(BotSetting(key=key, value=raw))
    else:
        row.value = raw


def _redact(value: str) -> str:
    value = str(value or "")
    for pattern, replacement in _SECRET_PATTERNS:
        value = pattern.sub(replacement, value)
    return value[:12000]


def record_error(error, *, update=None, source="پردازش ربات", severity="important") -> str | None:
    """Persist a deduplicated, redacted error record. Safe to call from handlers."""
    try:
        tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        tb = _redact(tb)
        frames = traceback.extract_tb(error.__traceback__) if getattr(error, "__traceback__", None) else []
        frame = frames[-1] if frames else None
        filename = Path(frame.filename).name if frame else "unknown"
        function = frame.name if frame else "unknown"
        line = int(frame.lineno) if frame else 0
        message = _redact(f"{type(error).__name__}: {error}")
        fingerprint = hashlib.sha256(f"{type(error).__name__}|{filename}|{function}|{line}|{message}".encode("utf-8", "replace")).hexdigest()[:16]
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        user = getattr(update, "effective_user", None) if update else None
        chat = getattr(update, "effective_chat", None) if update else None
        with SessionLocal() as session:
            rows = _get_json(session, ERRORS_KEY, [])
            item = next((x for x in rows if x.get("id") == fingerprint), None)
            if item is None:
                item = {
                    "id": fingerprint, "type": type(error).__name__, "message": message,
                    "source": _redact(source), "file": filename, "function": function,
                    "line": line, "traceback": tb, "severity": severity,
                    "first_at": now, "last_at": now, "count": 1, "status": "new",
                    "user_id": getattr(user, "id", None), "chat_id": getattr(chat, "id", None),
                }
                rows.insert(0, item)
            else:
                item["count"] = int(item.get("count", 0)) + 1
                item["last_at"] = now
                item["traceback"] = tb
                if item.get("status") == "resolved":
                    item["status"] = "new"
            _set_json(session, ERRORS_KEY, rows[:500])
            session.commit()
        return fingerprint
    except Exception:
        return None


def record_alert(alert_key: str, title: str, detail: str, *, severity="warning") -> tuple[dict, bool]:
    """Upsert alert by key; returns (record, newly_active)."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with SessionLocal() as session:
        rows = _get_json(session, ALERTS_KEY, [])
        item = next((x for x in rows if x.get("key") == alert_key), None)
        created = item is None
        if created:
            item = {"key": alert_key, "title": title, "detail": detail, "severity": severity,
                    "first_at": now, "last_at": now, "count": 1, "active": True, "resolved_at": None}
            rows.insert(0, item)
        else:
            was_active = bool(item.get("active"))
            item.update({"title": title, "detail": detail, "severity": severity,
                         "last_at": now, "count": int(item.get("count", 0)) + 1, "active": True,
                         "resolved_at": None})
            created = not was_active
        _set_json(session, ALERTS_KEY, rows[:300])
        session.commit()
        return dict(item), created


def resolve_alert(alert_key: str):
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with SessionLocal() as session:
        rows = _get_json(session, ALERTS_KEY, [])
        for item in rows:
            if item.get("key") == alert_key and item.get("active"):
                item["active"] = False
                item["resolved_at"] = now
        _set_json(session, ALERTS_KEY, rows[:300])
        session.commit()


def set_error_status(error_id: str, status: str) -> bool:
    if status not in {"new", "seen", "in_progress", "resolved"}:
        return False
    with SessionLocal() as session:
        rows = _get_json(session, ERRORS_KEY, [])
        item = next((x for x in rows if x.get("id") == error_id), None)
        if item is None:
            return False
        item["status"] = status
        item["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        _set_json(session, ERRORS_KEY, rows[:500])
        session.commit()
    return True


def get_error_records():
    with SessionLocal() as session:
        return _get_json(session, ERRORS_KEY, [])


def get_alert_records():
    with SessionLocal() as session:
        return _get_json(session, ALERTS_KEY, [])


def _memory_percent():
    try:
        values = {}
        with open("/proc/meminfo", "r", encoding="utf-8") as fh:
            for line in fh:
                key, value = line.split(":", 1)
                values[key] = int(value.strip().split()[0])
        total = values.get("MemTotal", 0)
        available = values.get("MemAvailable", values.get("MemFree", 0))
        return round((1 - available / total) * 100, 1) if total else None
    except Exception:
        return None


def _cpu_percent():
    try:
        def read():
            with open("/proc/stat", "r", encoding="utf-8") as fh:
                parts = fh.readline().split()[1:]
            nums = [int(x) for x in parts]
            idle = nums[3] + (nums[4] if len(nums) > 4 else 0)
            return sum(nums), idle
        a, idle_a = read()
        time.sleep(0.05)
        b, idle_b = read()
        total = b - a
        return round((1 - (idle_b - idle_a) / total) * 100, 1) if total > 0 else None
    except Exception:
        return None


def _db_path():
    if not str(DATABASE_URL).startswith("sqlite:"):
        return None
    raw = str(DATABASE_URL)[len("sqlite:///"):]
    if raw.startswith("/"):
        return Path(raw)
    return (Path(BASE_DIR) / raw).resolve()


def collect_snapshot(*, quick_db_check=False) -> dict:
    snapshot = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "uptime_seconds": max(0, int(time.time() - PROCESS_STARTED)),
        "process_started_at": datetime.fromtimestamp(PROCESS_STARTED).astimezone().isoformat(timespec="seconds"),
        "cpu_percent": _cpu_percent(),
        "ram_percent": _memory_percent(),
        "disk_percent": None,
        "disk_free_bytes": None,
        "database_ok": False,
        "database_bytes": None,
        "database_check": "not checked",
    }
    try:
        usage = shutil.disk_usage(BASE_DIR)
        snapshot["disk_percent"] = round((usage.used / usage.total) * 100, 1) if usage.total else None
        snapshot["disk_free_bytes"] = usage.free
    except Exception:
        pass
    path = _db_path()
    if path and path.exists():
        snapshot["database_bytes"] = path.stat().st_size
        try:
            with sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5) as conn:
                conn.execute("SELECT 1").fetchone()
                snapshot["database_ok"] = True
                if quick_db_check:
                    check = conn.execute("PRAGMA quick_check(1)").fetchone()
                    snapshot["database_check"] = str(check[0]) if check else "unknown"
        except Exception as exc:
            snapshot["database_check"] = f"{type(exc).__name__}: {_redact(exc)}"
    return snapshot


def get_internal_error_streak() -> int:
    try:
        with SessionLocal() as session:
            row = _setting(session, ERROR_STREAK_KEY)
            return max(0, int(row.value)) if row and row.value else 0
    except Exception:
        return 0


def reset_internal_error_streak():
    try:
        with SessionLocal() as session:
            row = _setting(session, ERROR_STREAK_KEY)
            if row is not None:
                row.value = "0"
                session.commit()
    except Exception:
        pass


def register_internal_error(error, *, threshold=10) -> tuple[int, bool]:
    """Count consecutive unexpected internal errors and engage the existing shutdown mode."""
    with SessionLocal() as session:
        row = _setting(session, ERROR_STREAK_KEY)
        try:
            count = max(0, int(row.value)) if row and row.value else 0
        except Exception:
            count = 0
        count += 1
        if row is None:
            session.add(BotSetting(key=ERROR_STREAK_KEY, value=str(count)))
        else:
            row.value = str(count)
        activated = count >= max(1, int(threshold))
        if activated:
            set_bot_shutdown_mode(session, "all")
            reason = f"خاموشی اضطراری خودکار پس از {count} خطای داخلی متوالی در {datetime.now(timezone.utc).isoformat(timespec='seconds')}"
            reason_row = _setting(session, EMERGENCY_KEY)
            if reason_row is None:
                session.add(BotSetting(key=EMERGENCY_KEY, value=reason))
            else:
                reason_row.value = reason
        session.commit()
    return count, activated


def clear_emergency_shutdown_state():
    try:
        with SessionLocal() as session:
            for key in (ERROR_STREAK_KEY, EMERGENCY_KEY):
                row = _setting(session, key)
                if row is not None:
                    session.delete(row)
            session.commit()
    except Exception:
        pass


def get_emergency_shutdown_reason():
    try:
        with SessionLocal() as session:
            row = _setting(session, EMERGENCY_KEY)
            return str(row.value) if row and row.value else None
    except Exception:
        return None


def latest_backup_snapshot() -> dict:
    """Return newest local database backup metadata without touching its contents."""
    try:
        from services.backup import BACKUP_DIR
        candidates = [p for p in Path(BACKUP_DIR).glob("worldwar3_*.db") if p.is_file()]
        disk_info = None
        if candidates:
            latest = max(candidates, key=lambda p: p.stat().st_mtime)
            mtime = latest.stat().st_mtime
            disk_info = {"path": str(latest), "mtime": datetime.fromtimestamp(mtime, timezone.utc).isoformat(timespec="seconds"), "age_seconds": max(0, int(time.time() - mtime)), "bytes": latest.stat().st_size}
        with SessionLocal() as session:
            row = _setting(session, "ww3_backup_last_success_v1")
            saved = json.loads(row.value) if row and row.value else None
        if isinstance(saved, dict) and saved.get("at"):
            stamp = datetime.fromisoformat(str(saved["at"]))
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=timezone.utc)
            success_age = max(0, int(time.time() - stamp.timestamp()))
            return {"path": None, "mtime": stamp.isoformat(timespec="seconds"), "age_seconds": success_age, "bytes": saved.get("bytes"), "delivered": True}
        if disk_info:
            disk_info["delivered"] = False
            return disk_info
        return {"path": None, "mtime": None, "age_seconds": None, "bytes": None, "delivered": False}
    except Exception:
        return {"path": None, "mtime": None, "age_seconds": None, "bytes": None}


def _background_task_snapshot(app) -> list[dict]:
    result = []
    for task in list(app.bot_data.get("background_tasks", []) or []):
        try:
            name = task.get_name()
            done = task.done()
            cancelled = task.cancelled()
            error = None
            if done and not cancelled:
                try:
                    exc = task.exception()
                    error = _redact(exc) if exc else None
                except Exception as exc:
                    error = _redact(exc)
            result.append({"name": name, "running": not done, "cancelled": cancelled, "error": error})
        except Exception:
            continue
    return result


async def ops_monitor_worker(app):
    """Low-frequency resource, database, backup and background-service checks."""
    while True:
        try:
            snap = await __import__("asyncio").to_thread(collect_snapshot, quick_db_check=True)
            backup = latest_backup_snapshot()
            with SessionLocal() as session:
                from services.settings import get_backup_started, get_backup_interval
                backup_enabled = get_backup_started(session)
                backup_interval_minutes = max(1, int(get_backup_interval(session)))
            checks = [
                ("database", not snap.get("database_ok") or snap.get("database_check") not in {"ok", "not checked"}, "🚨 اختلال پایگاه‌داده", f"بررسی دیتابیس: {snap.get('database_check')}", "critical"),
                ("cpu", snap.get("cpu_percent") is not None and snap["cpu_percent"] >= 90, "⚠️ مصرف بالای CPU", f"مصرف CPU: {snap.get('cpu_percent')}٪", "warning"),
                ("ram", snap.get("ram_percent") is not None and snap["ram_percent"] >= 90, "⚠️ مصرف بالای RAM", f"مصرف RAM: {snap.get('ram_percent')}٪", "warning"),
                ("disk", snap.get("disk_percent") is not None and snap["disk_percent"] >= 90, "⚠️ فضای دیسک رو به اتمام است", f"مصرف دیسک: {snap.get('disk_percent')}٪", "important"),
            ]
            if backup_enabled:
                age_limit = max(6 * 3600, backup_interval_minutes * 60 * 2)
                backup_age = backup.get("age_seconds")
                overdue = (backup_age is None and (time.time() - PROCESS_STARTED) >= age_limit) or (backup_age is not None and backup_age >= age_limit)
                checks.append(("backup_age", overdue, "⚠️ پشتیبان‌گیری عقب افتاده است", f"آخرین پشتیبان: {backup.get('mtime') or 'وجود ندارد'}", "important"))
            for key, triggered, title, detail, severity in checks:
                if triggered:
                    _, newly_active = record_alert(key, title, detail, severity=severity)
                    if newly_active and OWNER_ID:
                        try:
                            await app.bot.send_message(chat_id=int(OWNER_ID), text=f"{title}\n\n{detail}")
                        except Exception:
                            pass
                else:
                    resolve_alert(key)

            # All long-lived services are registered in Application.bot_data. A completed task is a failure.
            for task_info in _background_task_snapshot(app):
                key = f"service:{task_info['name']}"
                if task_info["running"]:
                    resolve_alert(key)
                elif not task_info["cancelled"]:
                    detail = f"سرویس {task_info['name']} متوقف شده است. {task_info.get('error') or ''}".strip()
                    _, newly_active = record_alert(key, "🚨 توقف سرویس داخلی", detail, severity="critical")
                    if newly_active and OWNER_ID:
                        try:
                            await app.bot.send_message(chat_id=int(OWNER_ID), text=f"🚨 توقف سرویس داخلی\n\n{detail}")
                        except Exception:
                            pass
        except Exception as exc:
            record_error(exc, source="مانیتورینگ خودکار", severity="critical")
        await __import__("asyncio").sleep(60)
