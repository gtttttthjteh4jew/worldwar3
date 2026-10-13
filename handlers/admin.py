from telegram import Update
from telegram.ext import ContextTypes

from config import OWNER_ID
from database.db import SessionLocal
from services.admin import is_admin, is_owner
from services.settings import phone_required_for, get_bot_shutdown_mode
from keyboards.admin import admin_panel_keyboard, owner_panel_keyboard, admin_management_keyboard, admin_back_keyboard
from services.panel_security import set_panel_owner


def clear_admin_pending(context):
    # هر دستور جدید، تمام حالت‌های انتظار قبلی را لغو می‌کند.
    for key in (
        "admin_pending", "admin_panel", "balance_pending", "population_pending", "population_selected_user", "balance_selected_user",
        "balance_back_callback", "population_back_callback", "pending_exchange", "economy_pending",
        "country_edit_waiting", "country_edit_name", "self_country_edit",
        "self_country_edit_name", "country_edit", "swap_pending",
    ):
        context.user_data.pop(key, None)


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message:
        return
    if update.effective_user.is_bot:
        return
    set_panel_owner(update.effective_user.id)
    if update.effective_chat and update.effective_chat.type not in ("private",):
        return
    clear_admin_pending(context)
    with SessionLocal() as session:
        from services.game import get_or_create_user
        user = get_or_create_user(session, update.effective_user)
        mode = get_bot_shutdown_mode(session)
        owner_user = is_owner(update.effective_user.id, OWNER_ID)
        admin_user = is_admin(session, update.effective_user.id, OWNER_ID)
        if not owner_user and (mode == "all" or (mode == "admins" and admin_user) or (mode == "users" and not admin_user)):
            session.commit(); await update.message.reply_text("⏸️ ربات موقتاً خاموش است."); return
        if user.is_banned and not is_owner(update.effective_user.id, OWNER_ID):
            session.commit()
            await update.message.reply_text("🚫 شما بن شده‌اید.")
            return
        if not is_admin(session, update.effective_user.id, OWNER_ID):
            await update.message.reply_text("⛔ شما دسترسی به پنل مدیر ندارید.")
            return
        if phone_required_for(
            session,
            is_admin_user=True,
            is_owner_user=is_owner(update.effective_user.id, OWNER_ID),
        ) and not user.phone_number:
            session.commit()
            await update.message.reply_text("📱 ابتدا شماره تلفن خودتان را ثبت کنید.")
            return
        session.commit()
    context.user_data["admin_panel"] = "root"
    await update.message.reply_text("⚙️ <b>پنل ادمین</b>", parse_mode="HTML", reply_markup=admin_panel_keyboard())


async def owner_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message:
        return
    if update.effective_user.is_bot:
        return
    set_panel_owner(update.effective_user.id)
    if update.effective_chat and update.effective_chat.type not in ("private",):
        return
    clear_admin_pending(context)
    if not is_owner(update.effective_user.id, OWNER_ID):
        await update.message.reply_text("⛔ این دستور فقط برای مالک است.")
        return
    context.user_data["admin_panel"] = "owner"
    await update.message.reply_text("👑 <b>پنل مالک</b>", parse_mode="HTML", reply_markup=owner_panel_keyboard())
