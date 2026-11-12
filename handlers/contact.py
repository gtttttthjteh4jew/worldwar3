from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from database.db import SessionLocal
from services.game import get_or_create_user
from services.admin import is_admin, is_owner
from services.settings import phone_required_for
from config import OWNER_ID


async def contact_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.effective_message or not update.effective_message.contact:
        return
    if update.effective_user.is_bot:
        return
    contact = update.effective_message.contact
    uid = update.effective_user.id
    if contact.user_id != uid:
        await update.effective_message.reply_text("❌ فقط مخاطب خودتان قابل ثبت است.")
        return
    with SessionLocal() as session:
        user = get_or_create_user(session, update.effective_user)
        user.phone_number = contact.phone_number
        session.commit()
        required = phone_required_for(session, is_admin_user=is_admin(session, uid, OWNER_ID), is_owner_user=is_owner(uid, OWNER_ID))
    await update.effective_message.reply_text("✅ شماره تلفن شما با موفقیت ثبت شد.", reply_markup=ReplyKeyboardRemove())
    if required:
        await update.effective_message.reply_text("🎮 دسترسی شما فعال شد. اکنون می‌توانید بازی را ادامه دهید.")
