from sqlalchemy import select
from database.models import BotSetting

PHONE_USER_KEY = "phone_required_users"
PHONE_ADMIN_KEY = "phone_required_admins"


def get_setting(session, key: str, default: bool = False) -> bool:
    row = session.scalar(select(BotSetting).where(BotSetting.key == key))
    if row is None:
        return default
    return row.value == "1"


def set_setting(session, key: str, enabled: bool) -> None:
    row = session.scalar(select(BotSetting).where(BotSetting.key == key))
    if row is None:
        row = BotSetting(key=key, value="1" if enabled else "0")
        session.add(row)
    else:
        row.value = "1" if enabled else "0"


def phone_required_for(session, *, is_admin_user: bool, is_owner_user: bool = False) -> bool:
    if is_owner_user:
        return False
    if is_admin_user:
        return get_setting(session, PHONE_ADMIN_KEY, False)
    return get_setting(session, PHONE_USER_KEY, False)


def all_phone_enabled(session) -> bool:
    return (
        get_setting(session, PHONE_USER_KEY, False)
        and get_setting(session, PHONE_ADMIN_KEY, False)
    )


BOT_SHUTDOWN_KEY = "bot_shutdown_mode"
SWAP_COOLDOWN_KEY = "swap_cooldown_hours"
COUNTRY_ESTABLISHMENT_URANIUM_KEY = "country_establishment_uranium_cost"
COUNTRY_RENAME_MONEY_KEY = "country_rename_money_cost"
COUNTRY_RENAME_METHOD_KEY = "country_rename_payment_method"
COUNTRY_RENAME_MONEY_ENABLED_KEY = "country_rename_money_enabled"
COUNTRY_RENAME_URANIUM_ENABLED_KEY = "country_rename_uranium_enabled"

def get_swap_cooldown_hours(session) -> float:
    row = session.scalar(select(BotSetting).where(BotSetting.key == SWAP_COOLDOWN_KEY))
    try:
        return max(0.0, float(row.value)) if row else 0.0
    except (TypeError, ValueError):
        return 0.0

def set_swap_cooldown_hours(session, hours: float) -> None:
    value = max(0.0, float(hours))
    row = session.scalar(select(BotSetting).where(BotSetting.key == SWAP_COOLDOWN_KEY))
    if row is None:
        session.add(BotSetting(key=SWAP_COOLDOWN_KEY, value=str(value)))
    else:
        row.value = str(value)

def get_country_establishment_uranium_cost(session) -> float:
    row = session.scalar(select(BotSetting).where(BotSetting.key == COUNTRY_ESTABLISHMENT_URANIUM_KEY))
    try:
        return max(0.0, float(row.value)) if row else 0.0
    except (TypeError, ValueError):
        return 0.0

def set_country_establishment_uranium_cost(session, amount: float) -> None:
    value = max(0.0, float(amount))
    row = session.scalar(select(BotSetting).where(BotSetting.key == COUNTRY_ESTABLISHMENT_URANIUM_KEY))
    if row is None:
        session.add(BotSetting(key=COUNTRY_ESTABLISHMENT_URANIUM_KEY, value=str(value)))
    else:
        row.value = str(value)

def get_swap_last_at(session, telegram_id: int):
    row = session.scalar(select(BotSetting).where(BotSetting.key == f"swap_last:{int(telegram_id)}"))
    if not row or not row.value:
        return None
    from datetime import datetime
    try:
        return datetime.fromisoformat(row.value)
    except ValueError:
        return None

def set_swap_last_at(session, telegram_id: int, when) -> None:
    row = session.scalar(select(BotSetting).where(BotSetting.key == f"swap_last:{int(telegram_id)}"))
    value = when.isoformat()
    if row is None:
        session.add(BotSetting(key=f"swap_last:{int(telegram_id)}", value=value))
    else:
        row.value = value


# none = روشن، admins = برای ادمین‌ها خاموش، users = برای کاربران عادی خاموش، all = برای همه به‌جز Owner خاموش
def get_bot_shutdown_mode(session) -> str:
    row = session.scalar(select(BotSetting).where(BotSetting.key == BOT_SHUTDOWN_KEY))
    return row.value if row and row.value in {"none", "admins", "users", "all"} else "none"

def set_bot_shutdown_mode(session, mode: str) -> None:
    if mode not in {"none", "admins", "users", "all"}:
        mode = "none"
    row = session.scalar(select(BotSetting).where(BotSetting.key == BOT_SHUTDOWN_KEY))
    if row is None:
        session.add(BotSetting(key=BOT_SHUTDOWN_KEY, value=mode))
    else:
        row.value = mode



def get_country_rename_money_cost(session) -> float:
    row = session.scalar(select(BotSetting).where(BotSetting.key == COUNTRY_RENAME_MONEY_KEY))
    try:
        return max(0.0, float(row.value)) if row else 0.0
    except (TypeError, ValueError):
        return 0.0

def set_country_rename_money_cost(session, amount: float) -> None:
    value = max(0.0, float(amount))
    row = session.scalar(select(BotSetting).where(BotSetting.key == COUNTRY_RENAME_MONEY_KEY))
    if row is None:
        session.add(BotSetting(key=COUNTRY_RENAME_MONEY_KEY, value=str(value)))
    else:
        row.value = str(value)

def get_country_rename_method(session) -> str:
    row = session.scalar(select(BotSetting).where(BotSetting.key == COUNTRY_RENAME_METHOD_KEY))
    return row.value if row and row.value in {"money", "uranium"} else "uranium"

def set_country_rename_method(session, method: str) -> None:
    method = method if method in {"money", "uranium"} else "uranium"
    row = session.scalar(select(BotSetting).where(BotSetting.key == COUNTRY_RENAME_METHOD_KEY))
    if row is None:
        session.add(BotSetting(key=COUNTRY_RENAME_METHOD_KEY, value=method))
    else:
        row.value = method


def get_country_rename_money_enabled(session) -> bool:
    return get_setting(session, COUNTRY_RENAME_MONEY_ENABLED_KEY, get_country_rename_money_cost(session) > 0)

def set_country_rename_money_enabled(session, enabled: bool) -> None:
    set_setting(session, COUNTRY_RENAME_MONEY_ENABLED_KEY, enabled)

def get_country_rename_uranium_enabled(session) -> bool:
    return get_setting(session, COUNTRY_RENAME_URANIUM_ENABLED_KEY, get_country_establishment_uranium_cost(session) > 0)

def set_country_rename_uranium_enabled(session, enabled: bool) -> None:
    set_setting(session, COUNTRY_RENAME_URANIUM_ENABLED_KEY, enabled)


GLOBAL_LOOT_PERCENT_KEY = "global_loot_percent"

def get_global_loot_percent(session) -> float:
    row = session.scalar(select(BotSetting).where(BotSetting.key == GLOBAL_LOOT_PERCENT_KEY))
    try:
        return max(0.0, min(100.0, float(row.value))) if row else 0.0
    except (TypeError, ValueError):
        return 0.0

def set_global_loot_percent(session, value: float) -> None:
    value = max(0.0, min(100.0, float(value)))
    row = session.scalar(select(BotSetting).where(BotSetting.key == GLOBAL_LOOT_PERCENT_KEY))
    if row is None:
        session.add(BotSetting(key=GLOBAL_LOOT_PERCENT_KEY, value=str(value)))
    else:
        row.value = str(value)

# ---------------- تنظیمات ضداسپم و پشتیبان‌گیری ----------------
ANTI_SPAM_ENABLED_KEY = "anti_spam_enabled"
ANTI_SPAM_USER_MAX_KEY = "anti_spam_user_max_requests"
ANTI_SPAM_USER_WINDOW_KEY = "anti_spam_user_window_seconds"
ANTI_SPAM_GROUP_MAX_KEY = "anti_spam_group_max_messages"
ANTI_SPAM_GROUP_WINDOW_KEY = "anti_spam_group_window_seconds"
BACKUP_INTERVAL_KEY = "backup_interval_minutes"
BACKUP_STARTED_KEY = "backup_started"
BACKUP_EXECUTION_TIME_KEY = "backup_execution_time"
BANK_LOAN_REMINDER_TIME_KEY = "bank_loan_reminder_time"
BANK_LOAN_INTERVAL_HOURS_KEY = "bank_loan_interval_hours"
BANK_LOAN_LOCK_DAYS_KEY = "bank_loan_lock_days"
BANK_LOAN_OVERDUE_MULTIPLIER_KEY = "bank_loan_overdue_multiplier"

def _get_num(session, key, default, cast=float, minimum=0):
    row = session.scalar(select(BotSetting).where(BotSetting.key == key))
    try:
        return max(minimum, cast(row.value)) if row else default
    except (TypeError, ValueError):
        return default

def _set_num(session, key, value):
    row = session.scalar(select(BotSetting).where(BotSetting.key == key))
    raw = str(value)
    if row is None:
        session.add(BotSetting(key=key, value=raw))
    else:
        row.value = raw

def get_anti_spam_enabled(session): return get_setting(session, ANTI_SPAM_ENABLED_KEY, True)
def set_anti_spam_enabled(session, value): set_setting(session, ANTI_SPAM_ENABLED_KEY, bool(value))
def get_anti_spam_user_max(session): return _get_num(session, ANTI_SPAM_USER_MAX_KEY, 5, int, 1)
def set_anti_spam_user_max(session, value): _set_num(session, ANTI_SPAM_USER_MAX_KEY, max(1, int(value)))
def get_anti_spam_user_window(session): return _get_num(session, ANTI_SPAM_USER_WINDOW_KEY, 10, int, 1)
def set_anti_spam_user_window(session, value): _set_num(session, ANTI_SPAM_USER_WINDOW_KEY, max(1, int(value)))
def get_anti_spam_group_max(session): return _get_num(session, ANTI_SPAM_GROUP_MAX_KEY, 20, int, 1)
def set_anti_spam_group_max(session, value): _set_num(session, ANTI_SPAM_GROUP_MAX_KEY, max(1, int(value)))
def get_anti_spam_group_window(session): return _get_num(session, ANTI_SPAM_GROUP_WINDOW_KEY, 60, int, 1)
def set_anti_spam_group_window(session, value): _set_num(session, ANTI_SPAM_GROUP_WINDOW_KEY, max(1, int(value)))
def get_backup_interval(session): return _get_num(session, BACKUP_INTERVAL_KEY, 60, int, 1)
def set_backup_interval(session, value): _set_num(session, BACKUP_INTERVAL_KEY, max(1, int(value)))
def get_backup_started(session): return bool(get_setting(session, BACKUP_STARTED_KEY, False))
def set_backup_started(session, value): set_setting(session, BACKUP_STARTED_KEY, bool(value))
def get_backup_execution_time(session):
    # این مقدار متن HH:MM است و نباید از get_setting بولی خوانده شود.
    row = session.scalar(select(BotSetting).where(BotSetting.key == BACKUP_EXECUTION_TIME_KEY))
    value = str(row.value if row is not None else "00:00")
    try:
        h,m = map(int, value.split(":",1))
        if not (0 <= h <= 23 and 0 <= m <= 59): raise ValueError
        return f"{h:02d}:{m:02d}"
    except Exception:
        return "00:00"
def set_backup_execution_time(session, value):
    h,m = map(int, str(value).strip().split(":",1))
    if not (0 <= h <= 23 and 0 <= m <= 59): raise ValueError
    raw = f"{h:02d}:{m:02d}"
    row = session.scalar(select(BotSetting).where(BotSetting.key == BACKUP_EXECUTION_TIME_KEY))
    if row is None:
        session.add(BotSetting(key=BACKUP_EXECUTION_TIME_KEY, value=raw))
    else:
        row.value = raw



def get_bank_loan_interval_hours(session):
    return max(0.1, float(_get_num(session, BANK_LOAN_INTERVAL_HOURS_KEY, 24, float, 0.1)))

def set_bank_loan_interval_hours(session, value):
    value = max(0.1, float(value))
    _set_num(session, BANK_LOAN_INTERVAL_HOURS_KEY, value)



def get_bank_loan_lock_days(session):
    return max(0.0, float(_get_num(session, BANK_LOAN_LOCK_DAYS_KEY, 1, float, 0.0)))

def set_bank_loan_lock_days(session, value):
    _set_num(session, BANK_LOAN_LOCK_DAYS_KEY, max(0.0, float(value)))



def get_bank_loan_lock_hours(session):
    return max(0.0, float(_get_num(session, BANK_LOAN_LOCK_DAYS_KEY, 1, float, 0.0)))

def set_bank_loan_lock_hours(session, value):
    _set_num(session, BANK_LOAN_LOCK_DAYS_KEY, max(0.0, float(value)))

def get_bank_loan_overdue_multiplier(session):
    return max(1.0, float(_get_num(session, BANK_LOAN_OVERDUE_MULTIPLIER_KEY, 2, float, 1.0)))

def set_bank_loan_overdue_multiplier(session, value):
    _set_num(session, BANK_LOAN_OVERDUE_MULTIPLIER_KEY, max(1.0, float(value)))

def get_bank_loan_reminder_time(session):
    row = session.scalar(select(BotSetting).where(BotSetting.key == BANK_LOAN_REMINDER_TIME_KEY))
    value = str(row.value if row is not None else "09:00")
    try:
        h, m = map(int, value.split(":", 1))
        if not (0 <= h <= 23 and 0 <= m <= 59): raise ValueError
        return f"{h:02d}:{m:02d}"
    except Exception:
        return "09:00"

def set_bank_loan_reminder_time(session, value):
    h, m = map(int, str(value).strip().split(":", 1))
    if not (0 <= h <= 23 and 0 <= m <= 59): raise ValueError
    raw = f"{h:02d}:{m:02d}"
    row = session.scalar(select(BotSetting).where(BotSetting.key == BANK_LOAN_REMINDER_TIME_KEY))
    if row is None:
        session.add(BotSetting(key=BANK_LOAN_REMINDER_TIME_KEY, value=raw))
    else:
        row.value = raw
