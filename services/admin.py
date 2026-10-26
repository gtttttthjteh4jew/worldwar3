from sqlalchemy import select, delete
from datetime import datetime
import asyncio

from database.models import Admin, User, BotSetting
from database.db import SessionLocal
import json


def is_owner(telegram_id: int, owner_id: int) -> bool:
    return bool(owner_id) and int(telegram_id) == int(owner_id)


def is_admin(session, telegram_id: int, owner_id: int) -> bool:
    if is_owner(telegram_id, owner_id):
        return True
    return session.scalar(
        select(Admin).where(Admin.telegram_id == int(telegram_id))
    ) is not None


def add_admin(session, telegram_id: int) -> bool:
    telegram_id = int(telegram_id)
    # فقط کاربری که واقعاً در دیتابیس ربات ثبت شده باشد می‌تواند ادمین شود.
    if session.scalar(select(User).where(User.telegram_id == telegram_id)) is None:
        return False
    if session.scalar(select(Admin).where(Admin.telegram_id == telegram_id)):
        return False
    session.add(Admin(telegram_id=telegram_id))
    return True


def remove_admin(session, telegram_id: int, owner_id: int) -> str:
    telegram_id = int(telegram_id)
    if is_owner(telegram_id, owner_id):
        return "OWNER_PROTECTED"
    admin = session.scalar(select(Admin).where(Admin.telegram_id == telegram_id))
    if admin is None:
        return "NOT_ADMIN"
    session.delete(admin)
    return "REMOVED"


def get_admins(session):
    return session.scalars(select(Admin).order_by(Admin.created_at.asc())).all()


def get_admin_user(session, telegram_id: int):
    return session.scalar(select(User).where(User.telegram_id == int(telegram_id)))


def clear_all_admins(session) -> list[int]:
    """تمام رکوردهای Admin را حذف می‌کند و IDهای حذف‌شده را برمی‌گرداند."""
    ids = list(session.scalars(select(Admin.telegram_id)).all())
    session.execute(delete(Admin))
    return [int(x) for x in ids]

# ---------------- User management / statistics ----------------
def get_users(session, *, banned=None):
    q = select(User).order_by(User.created_at.asc())
    if banned is not None:
        q = q.where(User.is_banned == bool(banned))
    return list(session.scalars(q).all())


def get_user_by_telegram_id(session, telegram_id: int):
    user = session.scalar(select(User).where(User.telegram_id == int(telegram_id)))
    if user and user.is_banned and user.ban_until and user.ban_until <= datetime.utcnow():
        user.is_banned = False; user.ban_until = None; user.ban_reason = None
        session.commit()
    return user




def ban_status_text(user, now=None) -> str:
    """متن دقیق وضعیت بن برای نمایش به خود کاربر و ادمین."""
    if not getattr(user, "is_banned", False):
        return "🟢 حساب شما فعال است."
    if getattr(user, "ban_until", None) is None:
        return "🚫 <b>شما بن دائم شده‌اید.</b>"
    now = now or datetime.utcnow()
    remaining = user.ban_until - now
    total = max(0, int(remaining.total_seconds()))
    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    parts=[]
    if days: parts.append(f"{days} روز")
    if hours: parts.append(f"{hours} ساعت")
    if minutes and not days: parts.append(f"{minutes} دقیقه")
    if not parts: parts.append("کمتر از ۱ دقیقه")
    return ("🚫 <b>شما بن شده‌اید.</b>\n\n⏳ تا رفع بن: <b>" + " و ".join(parts) + "</b>\n🕐 زمان رفع بن: <code>" + user.ban_until.strftime("%Y/%m/%d — %H:%M") + "</code>")

def ban_user(session, telegram_id: int, owner_id: int, reason: str | None = None) -> str:
    user = get_user_by_telegram_id(session, telegram_id)
    if user is None:
        return "NOT_FOUND"
    if is_owner(telegram_id, owner_id):
        return "OWNER_PROTECTED"
    if session.scalar(select(Admin).where(Admin.telegram_id == int(telegram_id))) is not None:
        return "ADMIN_PROTECTED"
    if user.is_banned:
        return "ALREADY_BANNED"
    user.is_banned = True
    user.ban_until = None
    user.ban_reason = (reason or "").strip() or None
    return "BANNED"


def unban_user(session, telegram_id: int) -> str:
    user = get_user_by_telegram_id(session, telegram_id)
    if user is None:
        return "NOT_FOUND"
    if not user.is_banned:
        return "NOT_BANNED"
    user.is_banned = False
    user.ban_until = None
    user.ban_reason = None
    return "UNBANNED"


def clear_bans(session) -> int:
    users = list(session.scalars(select(User).where(User.is_banned == True)).all())
    for user in users:
        user.is_banned = False
        user.ban_until = None
        user.ban_reason = None
    return len(users)



async def ban_expiry_worker(app):
    """رفع خودکار بن‌های ساعتی/روزانه در لحظه انقضا.

    زمان انقضا در ``User.ban_until`` با UTC ذخیره می‌شود؛ Worker مستقل است تا
    حتی اگر کاربر هیچ پیام/دستوری نفرستد، وضعیت او به‌صورت خودکار آزاد شود.
    """
    await asyncio.sleep(1)
    while True:
        try:
            expired=[]
            now=datetime.utcnow()
            with SessionLocal() as session:
                users=list(session.scalars(select(User).where(User.is_banned == True, User.ban_until.is_not(None), User.ban_until <= now)).all())
                for user in users:
                    uid=int(user.telegram_id)
                    user.is_banned=False
                    user.ban_until=None
                    user.ban_reason=None
                    expired.append(uid)
                if expired:
                    session.commit()
            for uid in expired:
                try:
                    await app.bot.send_message(chat_id=uid, text="✅ <b>مدت بن شما به پایان رسید.</b>\n\nبن شما به‌صورت خودکار رفع شد و دسترسی‌تان دوباره فعال است.", parse_mode="HTML")
                except Exception:
                    pass
        except asyncio.CancelledError:
            raise
        except Exception:
            # Worker باید زنده بماند حتی اگر یک دور DB/Telegram با خطا مواجه شود.
            pass
        await asyncio.sleep(1)


def get_admin_permissions(session, telegram_id: int) -> dict:
    defaults = {"users": True, "messages": True, "stats": True, "message_private": True, "message_public": True, "message_lists_private": True, "message_lists_public": True, "user_search": True, "user_info": True, "game_settings": True, "game_specs": True, "country_name": True, "delete_country": True, "swap_countries": True, "reset_swap": True}
    row = session.scalar(select(BotSetting).where(BotSetting.key == f"admin_permissions:{int(telegram_id)}"))
    if not row: return defaults
    try:
        data = json.loads(row.value); defaults.update({k: bool(v) for k,v in data.items()})
    except Exception: pass
    return defaults

def set_admin_permission(session, telegram_id: int, permission: str, enabled: bool) -> None:
    perms = get_admin_permissions(session, telegram_id); perms[str(permission)] = bool(enabled)
    key = f"admin_permissions:{int(telegram_id)}"
    row = session.scalar(select(BotSetting).where(BotSetting.key == key))
    val = json.dumps(perms, ensure_ascii=False)
    if row is None: session.add(BotSetting(key=key, value=val))
    else: row.value = val

def admin_has_permission(session, telegram_id: int, owner_id: int, permission: str) -> bool:
    if is_owner(telegram_id, owner_id):
        return True
    if not is_admin(session, telegram_id, owner_id):
        return False
    perms = get_admin_permissions(session, telegram_id)
    # غیرفعال بودن بخش اصلی، تمام زیرمجموعه‌های آن را نیز مسدود می‌کند.
    parents = {
        "user_search": "users", "user_info": "users", "game_settings": "users",
        "game_specs": "users", "country_name": "users", "delete_country": "users",
        "swap_countries": "users", "reset_swap": "users",
        "message_private": "messages", "message_public": "messages",
        "message_lists_private": "messages", "message_lists_public": "messages",
    }
    parent = parents.get(permission)
    if parent and not perms.get(parent, False):
        return False
    return bool(perms.get(permission, False))
