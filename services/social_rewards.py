from __future__ import annotations
import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from database.db import SessionLocal
from database.models import BotSetting, User
from services.social_links import _save_items, get_social_items, get_active_social_items, get_optional_join_pending, clear_optional_join_pending, social_item_button_url, public_chat_target, private_message_link_chat_id
from services.game import get_default_country
from services.atomic_claims import claim_once
from config import OWNER_ID

LOGGER = logging.getLogger("worldwar3_bot.social_rewards")
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from html import escape

CLAIM_PREFIX = "social_optional_claimed:"
VERIFIED_PREFIX = "social_verified:"

def _claim_key(uid: int, ad_id) -> str:
    return CLAIM_PREFIX + f"{int(uid)}:{str(ad_id or 'default')}"

def _claimed(session, uid: int, ad_id=None) -> bool:
    return session.scalar(select(BotSetting).where(BotSetting.key == _claim_key(uid, ad_id))) is not None

def is_optional_claimed(session, uid: int, ad_id=None) -> bool:
    return _claimed(session, uid, ad_id)

def _claimed_count(session, ad_id=None) -> int:
    prefix = CLAIM_PREFIX + f"%:{str(ad_id or 'default')}"
    return len(session.scalars(select(BotSetting).where(BotSetting.key.like(prefix))).all())

def optional_claimed_count(session, ad_id=None) -> int:
    return _claimed_count(session, ad_id)

def is_optional_pending(session, uid: int, ad_id=None) -> bool:
    """Return True when the user has a running/pending one-hour optional-ad timer."""
    key = f"social_optional_join:{int(uid)}"
    row = session.scalar(select(BotSetting).where(BotSetting.key == key))
    if not row or not row.value:
        return False
    try:
        meta = json.loads(row.value)
        ads = meta.get("ads") if isinstance(meta.get("ads"), dict) else {}
        entry = ads.get(str(ad_id))
        return isinstance(entry, dict) and entry.get("at") is not None
    except Exception:
        return False


def get_optional_pending_entry(session, uid: int, ad_id=None):
    key = f"social_optional_join:{int(uid)}"
    row = session.scalar(select(BotSetting).where(BotSetting.key == key))
    if not row or not row.value:
        return None
    try:
        meta = json.loads(row.value)
        ads = meta.get("ads") if isinstance(meta.get("ads"), dict) else {}
        entry = ads.get(str(ad_id))
        return dict(entry) if isinstance(entry, dict) else None
    except Exception:
        return None


def optional_timer_markup(ad_id):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⏳ زمان باقی‌مانده", callback_data=f"social:optional_timer:{ad_id}")
    ]])


def optional_reward_delay_minutes(ad) -> int:
    try:
        value = int(ad.get("reward_delay_minutes", 60) or 60)
    except Exception:
        value = 60
    return max(1, value)

def optional_timer_text(title, reward, joined_at, now=None, delay_minutes=60):
    now = now or datetime.now(timezone.utc)
    delay_minutes = max(1, int(delay_minutes or 60))
    remaining = max(0, int((joined_at + timedelta(minutes=delay_minutes) - now).total_seconds()))
    h, rem = divmod(remaining, 3600); m, sec = divmod(rem, 60)
    if h: time_text=f"{h} ساعت و {m} دقیقه"
    elif m: time_text=f"{m} دقیقه و {sec} ثانیه"
    else: time_text=f"{sec} ثانیه"
    return (f"✅ <b>عضویت شما ثبت شد.</b>\n\n"
            f"📣 مورد: <b>{escape(str(title))}</b>\n"
            f"☢️ پاداش: <b>{float(reward):,.0f}</b> اورانیوم\n\n"
            "⏳ با ماندن در عضویت، پس از پایان زمان تعیین‌شده پاداش به شما اضافه می‌شود.")

def _mark_claimed(session, uid: int, ad_id=None):
    session.add(BotSetting(key=_claim_key(uid, ad_id), value=datetime.now(timezone.utc).isoformat()))

def _verified_key(uid: int, ad_id) -> str:
    return VERIFIED_PREFIX + f"{int(uid)}:{str(ad_id or 'default')}"

def _verified_count(session, ad_id) -> int:
    prefix = VERIFIED_PREFIX + f"%:{str(ad_id or 'default')}"
    return len(session.scalars(select(BotSetting).where(BotSetting.key.like(prefix))).all())

def _mark_verified(session, uid: int, ad_id=None):
    key=_verified_key(uid, ad_id)
    if session.scalar(select(BotSetting).where(BotSetting.key == key)) is None:
        session.add(BotSetting(key=key, value=datetime.now(timezone.utc).isoformat()))



def reset_social_item_state(session, ad_id, item_type):
    """Reset all per-user progress for an ad when it is re-enabled.

    Re-enabling an optional/mandatory ad starts a completely new cycle: verified
    members, claimed rewards, and running optional timers are cleared.
    """
    aid = str(ad_id or "default")
    if item_type == "mandatory_ad":
        prefixes = (VERIFIED_PREFIX + "%:" + aid,)
    elif item_type == "optional_ad":
        prefixes = (CLAIM_PREFIX + "%:" + aid, VERIFIED_PREFIX + "%:" + aid)
    else:
        return
    for prefix in prefixes:
        rows = session.scalars(select(BotSetting).where(BotSetting.key.like(prefix))).all()
        for row in rows:
            session.delete(row)

    if item_type == "optional_ad":
        # Timers for optional ads are stored as one JSON object per user.
        timer_rows = session.scalars(select(BotSetting).where(BotSetting.key.like("social_optional_join:%"))).all()
        for row in timer_rows:
            try:
                meta = json.loads(row.value or "{}")
                ads = meta.get("ads") if isinstance(meta.get("ads"), dict) else {}
                if aid in ads:
                    ads.pop(aid, None)
                    meta["ads"] = ads
                    if ads:
                        row.value = json.dumps(meta, ensure_ascii=False)
                    else:
                        session.delete(row)
            except Exception:
                continue

def _title(chat, fallback="تبلیغ"):
    return getattr(chat, "title", None) or getattr(chat, "username", None) or fallback

async def claim_optional_ads_now(bot, uid: int, session):
    """Check all active optional ads once; reward joined unclaimed ads immediately."""
    earned=[]; missing=[]; already=0
    ads=get_active_social_items(session, "optional_ad")
    user=session.scalar(select(User).where(User.telegram_id == int(uid)))
    if user is None:
        return {"earned":[],"missing":[],"already":0}
    country=get_default_country(session,user)
    for ad in ads:
        ad_id=ad.get("id")
        if _claimed(session, uid, ad_id):
            already += 1
            continue
        target=ad.get("chat_id") or public_chat_target(ad.get("url")) or private_message_link_chat_id(ad.get("url"))
        if not target:
            missing.append({"title":"تبلیغ اختیاری"}); continue
        try:
            member=await bot.get_chat_member(target, uid)
            status=getattr(member,"status","")
            joined=status in {"member","administrator","creator"} or (status == "restricted" and bool(getattr(member,"is_member",False)))
        except Exception:
            joined=False
        if not joined:
            try: chat=await bot.get_chat(target); title=_title(chat)
            except Exception: title="تبلیغ اختیاری"
            missing.append({"title":title})
            continue
        reward=max(0.0,float(ad.get("reward",0) or 0))
        if country is None:
            missing.append({"title":"ابتدا کشور پیش‌فرض خود را انتخاب کنید"})
            continue
        if not claim_once(session, _claim_key(uid, ad_id), datetime.now(timezone.utc).isoformat()):
            already += 1
            continue
        if reward > 0 and not getattr(country,"infinite_uranium",False):
            country.uranium=float(getattr(country,"uranium",0) or 0)+reward
        _mark_verified(session,uid,ad_id)
        # سقف اعضا بر اساس تأییدهای ثبت‌شده در ربات است، نه تعداد واقعی اعضای تلگرام.
        max_members=ad.get("max_members")
        if max_members and _verified_count(session,ad_id) >= int(max_members):
            ad["active"]=False
            ad["disabled_at"]=datetime.now(timezone.utc).isoformat()
            ad["disabled_reason"]="members"
            _save_items(session,get_social_items(session))
        try: chat=await bot.get_chat(target); title=_title(chat)
        except Exception: title="تبلیغ اختیاری"
        earned.append({"title":title,"reward":reward})
    session.commit()
    return {"earned":earned,"missing":missing,"already":already}

async def auto_register_optional_membership(bot, update):
    """Automatically start an optional-ad reward timer when Telegram reports a user joining.

    The bot must be an administrator in the target channel/group for Telegram to send
    chat_member updates. The public confirmation button is no longer required.
    """
    cm = getattr(update, "chat_member", None)
    if cm is None:
        return
    user = getattr(cm, "new_chat_member", None)
    chat = getattr(cm, "chat", None)
    if user is None or chat is None:
        return
    uid = int(getattr(user, "user", user).id)
    new_status = getattr(user, "status", "")
    old = getattr(cm, "old_chat_member", None)
    old_status = getattr(old, "status", "") if old else ""
    joined = new_status in {"member", "administrator", "creator", "restricted"}
    was_joined = old_status in {"member", "administrator", "creator", "restricted"}
    if not joined or was_joined:
        return

    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        active = get_active_social_items(session, "optional_ad")
        matching = [x for x in active if str(x.get("chat_id")) == str(chat.id) or str(public_chat_target(x.get("url"))) == str(chat.id)]
        if not matching:
            return
        key = f"social_optional_join:{uid}"
        row = session.scalar(select(BotSetting).where(BotSetting.key == key))
        meta = {}
        if row and row.value:
            try:
                meta = json.loads(row.value)
            except Exception:
                meta = {}
        ads = meta.get("ads") if isinstance(meta.get("ads"), dict) else {}
        started = []
        for ad in matching:
            ad_id = ad.get("id")
            if _claimed(session, uid, ad_id):
                continue
            key_id = str(ad_id)
            entry = ads.get(key_id)
            # If a timer already exists, do not restart it from a duplicate update.
            if isinstance(entry, dict) and entry.get("at"):
                continue
            ads[key_id] = {"at": now.isoformat(), "left_notified": False, "membership_misses": 0}
            started.append(ad)
        if not started:
            return
        payload = json.dumps({"ads": ads}, ensure_ascii=False)
        if row is None:
            session.add(BotSetting(key=key, value=payload))
        else:
            row.value = payload
        session.commit()

    for ad in started:
        try:
            target = ad.get("chat_id") or public_chat_target(ad.get("url")) or private_message_link_chat_id(ad.get("url"))
            title = getattr(chat, "title", None) or getattr(chat, "username", None) or "تبلیغ اختیاری"
            await bot.send_message(
                uid,
                optional_timer_text(title, ad.get("reward", 0), now, now, optional_reward_delay_minutes(ad)),
                parse_mode="HTML",
                reply_markup=optional_timer_markup(ad.get("id")),
            )
        except Exception:
            pass


async def scan_existing_optional_memberships(bot):
    """Discover users who are already members of newly-added optional ads.

    This covers the case where a user joined before the Owner added the ad.
    The timer starts when the membership is first discovered for that ad.
    """
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        ads = get_active_social_items(session, "optional_ad")
        users = session.scalars(select(User)).all()
        if not ads or not users:
            return
        changed = []
        for ad in ads:
            ad_id = ad.get("id")
            target = ad.get("chat_id") or public_chat_target(ad.get("url")) or private_message_link_chat_id(ad.get("url"))
            if not target:
                continue
            for user in users:
                uid = int(user.telegram_id)
                if _claimed(session, uid, ad_id):
                    continue
                key = f"social_optional_join:{uid}"
                row = session.scalar(select(BotSetting).where(BotSetting.key == key))
                meta = {}
                if row and row.value:
                    try: meta = json.loads(row.value)
                    except Exception: meta = {}
                ads_meta = meta.get("ads") if isinstance(meta.get("ads"), dict) else {}
                entry = ads_meta.get(str(ad_id))
                if isinstance(entry, dict) and entry.get("at"):
                    continue
                try:
                    member = await bot.get_chat_member(target, uid)
                    status = getattr(member, "status", "")
                    joined = status not in {"left", "kicked", "restricted"} or bool(getattr(member, "is_member", False))
                except Exception:
                    continue
                if not joined:
                    continue
                ads_meta[str(ad_id)] = {"at": now.isoformat(), "left_notified": False, "membership_misses": 0}
                payload = json.dumps({"ads": ads_meta}, ensure_ascii=False)
                if row is None:
                    session.add(BotSetting(key=key, value=payload))
                else:
                    row.value = payload
                changed.append((uid, ad))
        session.commit()

    for uid, ad in changed:
        try:
            target = ad.get("chat_id") or public_chat_target(ad.get("url")) or private_message_link_chat_id(ad.get("url"))
            chat = await bot.get_chat(target) if target else None
            title = _title(chat) if chat else "تبلیغ اختیاری"
            await bot.send_message(uid, optional_timer_text(title, ad.get("reward", 0), now, now, optional_reward_delay_minutes(ad)), parse_mode="HTML", reply_markup=optional_timer_markup(ad.get("id")))
        except Exception:
            pass

async def social_reward_worker(app):
    # Optional-ad rewards use each ad's owner-defined delay. Membership is
    # checked continuously by the worker; leaving pauses the timer and rejoining
    # starts a fresh timer.
    await asyncio.sleep(5)
    while True:
        try:
            now = datetime.now(timezone.utc)
            with SessionLocal() as session:
                items = get_social_items(session)
                changed = False
                for item in items:
                    if not bool(item.get("active", True)):
                        continue
                    reason = None
                    exp = item.get("expires_at")
                    if exp:
                        try:
                            dt = datetime.fromisoformat(str(exp))
                            if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
                            if dt <= now: reason = "time"
                        except Exception: pass
                    if reason is None and item.get("type") in {"mandatory_ad", "optional_ad"} and item.get("max_members"):
                        if _verified_count(session, item.get("id")) >= int(item.get("max_members")):
                            reason = "members"
                    if reason:
                        item["active"] = False
                        item["disabled_at"] = now.isoformat()
                        item["disabled_reason"] = reason
                        changed = True
                        label = {"mandatory_ad":"تبلیغ اجباری","optional_ad":"تبلیغ اختیاری","chat":"چت بازی","channel":"کانال بازی","panel":"پنل بازی"}.get(item.get("type"),"مورد")
                        try:
                            await app.bot.send_message(OWNER_ID, f"⚠️ <b>{label} غیرفعال شد.</b>\n\n🔗 <code>{item.get('url','')}</code>\n📌 دلیل: {'رسیدن به حد اعضا' if reason=='members' else 'پایان زمان'}", parse_mode="HTML")
                        except Exception: pass
                if changed:
                            _save_items(session, items)
                session.commit()
                pending = session.scalars(select(BotSetting).where(BotSetting.key.like("social_optional_join:%"))).all()

            for row in pending:
                uid = int(row.key.split(":")[-1])
                try:
                    meta = json.loads(row.value)
                    ads_meta = meta.get("ads") if isinstance(meta.get("ads"), dict) else {}
                except Exception:
                    continue
                for ad_id, ad_meta in list(ads_meta.items()):
                    try:
                        joined_at = datetime.fromisoformat(str(ad_meta.get("at"))) if ad_meta.get("at") else None
                        left_notified = bool(ad_meta.get("left_notified", False))
                    except Exception:
                        continue
                    with SessionLocal() as session:
                        ad = next((x for x in get_social_items(session, "optional_ad") if str(x.get("id")) == str(ad_id)), None)
                        user = session.scalar(select(User).where(User.telegram_id == uid))
                    if not ad or not user:
                        ads_meta.pop(str(ad_id), None); continue
                    target = ad.get("chat_id") or public_chat_target(ad.get("url")) or private_message_link_chat_id(ad.get("url"))
                    if not target:
                        continue
                    try:
                        member = await app.bot.get_chat_member(target, uid)
                        status = getattr(member, "status", "")
                        joined = status not in {"left", "kicked", "restricted"} or bool(getattr(member, "is_member", False))
                    except Exception:
                        joined = False

                    if not joined:
                        # get_chat_member گاهی در لحظهٔ تغییر عضویت یک وضعیت قدیمی/موقت
                        # برمی‌گرداند. تا سه بررسی پیاپی ناموفق، «خارج شدید» اعلام نکن.
                        miss_count = int(ad_meta.get("membership_misses", 0) or 0) + 1
                        ads_meta[str(ad_id)]["membership_misses"] = miss_count
                        if miss_count < 3:
                            continue
                        if not left_notified:
                            try:
                                chat = await app.bot.get_chat(target); title = _title(chat)
                            except Exception:
                                title = "کانال/گروه"
                            try:
                                from telegram import InlineKeyboardMarkup, InlineKeyboardButton
                                await app.bot.send_message(uid, f"⚠️ <b>از {title} خارج شدید.</b>\n\nبرای دریافت پاداش، دوباره به این کانال/گروه برگردید. تا وقتی برنگشته‌اید، زمان پاداش محاسبه نمی‌شود.", parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"🔗 ورود به {title}", url=social_item_button_url(ad.get("url")))]]))
                            except Exception: pass
                            ads_meta[str(ad_id)]["left_notified"] = True
                            ads_meta[str(ad_id)]["at"] = None
                        continue

                    # عضویت تأیید شد؛ هر خطای موقت قبلی پاک می‌شود.
                    ads_meta[str(ad_id)]["membership_misses"] = 0
                    # کاربر دوباره عضو شده؛ تایمر از زمان بازگشت شروع می‌شود.
                    if joined_at is None or left_notified:
                        ads_meta[str(ad_id)]["at"] = now.isoformat()
                        ads_meta[str(ad_id)]["left_notified"] = False
                        ads_meta[str(ad_id)]["membership_misses"] = 0
                        try:
                            chat = await app.bot.get_chat(target)
                            title = _title(chat)
                        except Exception:
                            title = "کانال/گروه"
                        try:
                            await app.bot.send_message(
                                uid,
                                optional_timer_text(title, ad.get("reward", 0), now, now, optional_reward_delay_minutes(ad)),
                                parse_mode="HTML",
                                reply_markup=optional_timer_markup(ad_id),
                            )
                        except Exception:
                            pass
                        continue

                    if now - joined_at < timedelta(minutes=optional_reward_delay_minutes(ad)):
                        continue

                    with SessionLocal() as session:
                        if not claim_once(session, _claim_key(uid, ad_id), datetime.now(timezone.utc).isoformat()):
                            ads_meta.pop(str(ad_id), None); continue
                        user = session.scalar(select(User).where(User.telegram_id == uid))
                        country = get_default_country(session, user) if user else None
                        if country is None:
                            continue
                        reward = max(0.0, float(ad.get("reward", 0) or 0))
                        if reward > 0 and not getattr(country, "infinite_uranium", False):
                            country.uranium = float(getattr(country, "uranium", 0) or 0) + reward
                        _mark_verified(session, uid, ad_id)
                        if ad.get("max_members") and _verified_count(session, ad_id) >= int(ad["max_members"]):
                            ad["active"] = False
                            _save_items(session, get_social_items(session))
                        session.commit()
                    ads_meta.pop(str(ad_id), None)
                    try:
                        await app.bot.send_message(uid, f"🎁 <b>پاداش تبلیغ اختیاری واریز شد.</b>\n\n☢️ مقدار پاداش: <b>{reward:,.0f}</b> اورانیوم", parse_mode="HTML")
                    except Exception: pass

                with SessionLocal() as session:
                    row2 = session.scalar(select(BotSetting).where(BotSetting.key == row.key))
                    if row2:
                        row2.value = json.dumps({"ads": ads_meta}, ensure_ascii=False)
                        if not ads_meta:
                            session.delete(row2)
                        session.commit()
        except asyncio.CancelledError:
            raise
        except Exception:
            pass
        try:
            await scan_existing_optional_memberships(app.bot)
        except Exception:
            pass
        await asyncio.sleep(10)


def _member_is_joined(member) -> bool:
    status = getattr(member, "status", "")
    return status in {"member", "administrator", "creator", "restricted"} and (status != "restricted" or bool(getattr(member, "is_member", False)))


async def auto_track_mandatory_membership(update, context):
    """Notify users when mandatory membership changes and gate access on all required items."""
    cm = getattr(update, "chat_member", None)
    if cm is None or getattr(cm, "chat", None) is None:
        return
    member = getattr(cm, "new_chat_member", None)
    user = getattr(member, "user", None)
    if user is None or getattr(user, "is_bot", False):
        return
    chat_id = int(cm.chat.id)
    old_joined = _member_is_joined(getattr(cm, "old_chat_member", None))
    new_joined = _member_is_joined(member)
    if old_joined == new_joined:
        return

    with SessionLocal() as session:
        items = [x for x in get_active_social_items(session, "mandatory_ad")
                 if int(x.get("chat_id") or 0) == chat_id]
        all_items = get_active_social_items(session, "mandatory_ad")
    if not items:
        return

    title = getattr(cm.chat, "title", None) or getattr(cm.chat, "username", None) or "کانال/گروه اجباری"

    if new_joined:
        # یک عضویت به‌تنهایی دسترسی را باز نمی‌کند؛ همه تبلیغات اجباری باید عضو باشند.
        all_joined = True
        for item in all_items:
            target = item.get("chat_id") or public_chat_target(item.get("url")) or private_message_link_chat_id(item.get("url"))
            if not target:
                all_joined = False
                break
            try:
                m = await context.bot.get_chat_member(target, user.id)
                if not _member_is_joined(m):
                    all_joined = False
                    break
            except Exception:
                all_joined = False
                break
        if all_joined:
            text = (f"✅ <b>شما عضو {escape(str(title))} شدید.</b>\n\n"
                    "🔓 دسترسی شما به ربات باز شد.")
            try:
                await context.bot.send_message(user.id, text, parse_mode="HTML")
            except Exception:
                pass
    else:
        url = social_item_button_url(items[0].get("url"))
        markup = InlineKeyboardMarkup([[InlineKeyboardButton(f"🔗 ورود به {title}", url=url)]]) if url else None
        text = (f"⚠️ <b>شما از {escape(str(title))} خارج شدید.</b>\n\n"
                "🔒 دسترسی شما به ربات محدود شد. برای استفاده دوباره، ابتدا عضو شوید.")
        try:
            await context.bot.send_message(user.id, text, parse_mode="HTML", reply_markup=markup)
        except Exception:
            pass

