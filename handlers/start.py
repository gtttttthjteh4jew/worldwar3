from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from keyboards.main import command_keyboard
from database.db import SessionLocal
from services.game import get_or_create_user, get_default_country, country_status, get_military_power
from services.leadership import leadership_rank_text
from services.economy import get_arsenal_config, get_metal_mine_config, get_hq_config
from services.admin import is_admin, is_owner, ban_status_text
from services.settings import phone_required_for, get_bot_shutdown_mode
from services.command_scopes import set_user_command_scope
from config import OWNER_ID
from services.panel_security import set_panel_owner
from services.social_links import get_social_items, get_active_social_items, public_chat_target, social_item_button_url, private_message_link_chat_id
from services.social_rewards import is_optional_claimed, is_optional_pending


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user is None or update.message is None:
        return
    if update.effective_user.is_bot:
        return
    set_panel_owner(update.effective_user.id)

    # /start هر انتظار قبلی (تبادل/ورودی مقدار/...) را لغو می‌کند.
    for key in (
        "pending_exchange", "admin_pending", "admin_panel", "balance_pending", "population_pending",
        "population_selected_user", "population_back_callback", "balance_selected_user", "balance_back_callback", "economy_pending",
        "country_edit_waiting", "country_edit_name", "self_country_edit",
        "self_country_edit_name", "country_edit", "swap_pending",
        f"country_name_pending_{update.effective_user.id}",
        f"country_name_value_{update.effective_user.id}",
    ):
        context.user_data.pop(key, None)

    # اگر ربات برای این نقش خاموش باشد، حتی /start@Bot در گروه هم پاسخ بازی نمی‌دهد.
    if update.effective_chat and update.effective_user:
        with SessionLocal() as gate_session:
            gate_user = get_or_create_user(gate_session, update.effective_user)
            gate_mode = get_bot_shutdown_mode(gate_session)
            gate_admin = is_admin(gate_session, update.effective_user.id, OWNER_ID)
            gate_owner = is_owner(update.effective_user.id, OWNER_ID)
            if not gate_owner and (gate_mode == "all" or (gate_mode == "admins" and gate_admin) or (gate_mode == "users" and not gate_admin)):
                gate_session.commit(); await update.message.reply_text("⏸️ ربات موقتاً خاموش است."); return
    # /start@Bot در گروه فقط دعوت به Private Chat است و پنل بازی را باز نمی‌کند.
    if update.effective_chat and update.effective_chat.type in ("group", "supergroup"):
        try:
            username = (await context.bot.get_me()).username
        except Exception:
            username = None
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("🤖 ورود به ربات", url=f"https://t.me/{username}")]]) if username else None
        await update.message.reply_text("🎮 برای بازی کردن وارد ربات شوید.", reply_markup=markup)
        return

    with SessionLocal() as session:
        referrer_id = None
        try:
            if context.args and context.args[0].lower().startswith("ref_"):
                referrer_id = int(context.args[0][4:])
        except (ValueError, TypeError):
            referrer_id = None
        user = get_or_create_user(session, update.effective_user, referrer_user_id=referrer_id)
        mode = get_bot_shutdown_mode(session)
        owner_user = is_owner(update.effective_user.id, OWNER_ID)
        admin_user = is_admin(session, update.effective_user.id, OWNER_ID)
        if not owner_user and (mode == "all" or (mode == "admins" and admin_user) or (mode == "users" and not admin_user)):
            session.commit(); await update.message.reply_text("⏸️ ربات موقتاً خاموش است."); return
        # همیشه منوی Slash همین کاربر را بر اساس نقش فعلی همگام کن؛
        # این کار /admin و /owner قدیمی را برای کاربران عادی حذف می‌کند.
        await set_user_command_scope(
            context.bot,
            user.telegram_id,
            owner=is_owner(user.telegram_id, OWNER_ID),
            admin=is_admin(session, user.telegram_id, OWNER_ID),
        )
        if user.is_banned:
            session.commit()
            await update.message.reply_text(ban_status_text(user), parse_mode="HTML")
            return
        # وضعیت عضویت در تبلیغات اجباری را برای نمایش زیر پیام اصلی محاسبه می‌کنیم.
        # خود /start همیشه باید اجرا شود؛ اما تمام قابلیت‌های دیگر تا تکمیل عضویت مسدود می‌مانند.
        mandatory = [x for x in get_active_social_items(session, "mandatory_ad") if str(x.get("url") or "").strip()]
        missing=[]
        for item in mandatory:
            target=item.get("chat_id") or public_chat_target(item.get("url")) or private_message_link_chat_id(item.get("url"))
            if not target:
                missing.append(item)
                continue
            try:
                member=await context.bot.get_chat_member(target, user.telegram_id)
                status=getattr(member, "status", "")
                if not (status in {"member", "administrator", "creator"} or (status == "restricted" and bool(getattr(member, "is_member", False)))):
                    missing.append(item)
            except Exception:
                # عضویت را نمی‌توان با اطمینان تأیید کرد؛ برای جلوگیری از دور زدن
                # گیت اجباری، این مورد باید تا بررسی موفق بعدی مسدود بماند.
                missing.append(item)

        required = phone_required_for(session, is_admin_user=is_admin(session, user.telegram_id, OWNER_ID), is_owner_user=is_owner(user.telegram_id, OWNER_ID))
        phone_missing = bool(required and not user.phone_number)
        default_country = get_default_country(session, user)
        session.commit()

        if default_country:
            text = (
                "🌍 <b>World War 3</b>\n\n"
                f"کشور پیش‌فرض شما: <b>{default_country.title}</b>\n\n"
                "برای بازی در گروه، دستورات را همان‌جا ارسال کنید.\n"
                "در پیوی، عملیات روی کشور پیش‌فرض انجام می‌شود."
            )
        else:
            text = (
                "🌍 <b>World War 3</b>\n\n"
                "هنوز کشور پیش‌فرضی برای شما انتخاب نشده است.\n"
                "ابتدا وارد یک گروهی شوید که ربات در آن عضو است و در آن گروه بازی را شروع کنید؛ "
                "سپس می‌توانید آن کشور را به‌عنوان کشور پیش‌فرض انتخاب کنید."
            )

    country_label = default_country.title if default_country else "انتخاب نشده"

    # پیام اصلی /start همیشه اول ارسال می‌شود.
    start_markup=command_keyboard(no_country=not bool(default_country))
    arsenal_cfg = get_arsenal_config(session) if default_country else None
    mine_cfg = get_metal_mine_config(session) if default_country else None
    hq_cfg = get_hq_config(session) if default_country else None
    power_cfg = {"metal_mine": mine_cfg, "hq": hq_cfg} if default_country else None
    await update.message.reply_text(
        (
            "╔════════════════════╗\n"
            "🌍 <b>WORLD WAR 3</b>\n"
            "╚════════════════════╝\n\n"
            f"🏳️ کشور پیش‌فرض شما: <b>{country_label}</b>\n"
            + (f"🪖 قدرت نظامی: <b>{get_military_power(default_country, config=power_cfg, arsenal_config=arsenal_cfg):,.0f}</b>\n" if default_country else "")
            + (f"👑 سطح تجربه رهبری: <b>{leadership_rank_text(getattr(default_country, 'leadership_experience', 0))}</b>\n🎖️ تجربه رهبری: <b>{float(getattr(default_country, 'leadership_experience', 0) or 0):,.0f}</b>\n" if default_country else "")
            + "\n🎮 <b>برای اجرای دستورات، از پنل پایین استفاده کنید.</b>\n"
            "🚀 آماده‌اید؟ بازی را شروع کنید!"
        ),
        parse_mode="HTML",
        reply_markup=start_markup,
    )

    # پیام عضویت در تبلیغات اجباری/اختیاری دقیقاً زیر پیام اصلی /start قرار می‌گیرد.
    # در /start دکمه‌های «چت بازی» و «کانال بازی» نمایش داده نمی‌شوند؛ این دو فقط در «چت و کانال» هستند.
    social_rows=[]
    for item in missing:
        url=social_item_button_url(item.get("url"))
        if url:
            social_rows.append([InlineKeyboardButton(f"🚨 {item.get('title') or item.get('name') or 'تبلیغ اجباری'}", url=url)])
    if missing:
        social_rows.append([InlineKeyboardButton("🔄 بررسی عضویت", callback_data=f"social:mandatory_check:{int(update.effective_user.id)}")])

    active_optional=[
        x for x in get_active_social_items(session, "optional_ad")
        if not is_optional_claimed(session, update.effective_user.id, x.get("id")) and not is_optional_pending(session, update.effective_user.id, x.get("id"))
    ]
    for item in active_optional:
        url=social_item_button_url(item.get("url"))
        if url:
            reward=float(item.get("reward",0) or 0)
            social_rows.append([InlineKeyboardButton(f"🎁 تبلیغ اختیاری — ☢️ {reward:,.0f}", url=url)])

    if social_rows:
        title = "🚨 <b>عضویت در تبلیغات اجباری</b>\n\nابتدا در تبلیغات اجباری عضو شوید و سپس بررسی عضویت را بزنید." if missing else "🎁 <b>تبلیغات اختیاری</b>\n\nبا عضویت در تبلیغ، عضویت شما به‌صورت خودکار بررسی و ثبت می‌شود."
        await update.message.reply_text(title, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(social_rows))

    # تا وقتی عضویت در تبلیغات اجباری کامل نشده، /start تمام است؛ قابلیت دیگری اجرا نمی‌شود.
    if missing:
        return

    if phone_missing:
        keyboard = ReplyKeyboardMarkup([[KeyboardButton("📱 ثبت شماره تلفن", request_contact=True, style="success")]], resize_keyboard=True, one_time_keyboard=False, is_persistent=False)
        await update.message.reply_text("📱 <b>ثبت شماره تلفن الزامی است</b>\n\nبرای ادامه، مخاطب خودتان را از طریق دکمه زیر ارسال کنید.", parse_mode="HTML", reply_markup=keyboard)
        return
