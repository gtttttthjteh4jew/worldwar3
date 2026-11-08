from math import ceil
from html import escape

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from sqlalchemy import select, func

from database.db import SessionLocal
from database.models import User, Country, GroupStatus
from services.group_status import refresh_known_groups, group_is_active
from services.game import get_or_create_user



def rtl_name(value):
    if value is None:
        return ""
    return "\u202b" + str(value) + "\u202c"
PAGE_SIZE = 10
GROUP_MAX_RANKS = 100
GLOBAL_MAX_RANKS = 1000
CONTINENT_MAX_RANKS = 100


def _page_keyboard(kind: str, page: int, total: int, max_ranks: int) -> InlineKeyboardMarkup:
    total = min(total, max_ranks)
    pages = max(1, ceil(total / PAGE_SIZE))
    page = max(1, min(page, pages))
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("🟦 ◀️ قبلی", callback_data=f"leaderboard:{kind}:{page-1}"))
    nav.append(InlineKeyboardButton(f"📖 {page} / {pages}", callback_data="leaderboard:noop"))
    if page < pages:
        nav.append(InlineKeyboardButton("بعدی ▶️ 🟦", callback_data=f"leaderboard:{kind}:{page+1}"))
    rows = [nav]
    # برگشت فقط وقتی معنی دارد؛ در لیدربورد گروه، همان پیام صفحه اصلی خودش پنل است.
    return InlineKeyboardMarkup(rows)


def _pretty_name(name: str | None, username: str | None, user_id: int | None = None) -> str:
    """Render the name/identity connector as one stable RTL block.

    The connector is isolated from the bidi algorithm so Latin usernames do not
    flip the box-drawing characters. The corner remains on the right side of
    the connector, directly under the name.
    """
    name_text = escape((name or "بدون نام").strip() or "بدون نام")
    if username:
        username = username.lstrip("@").strip()
    identity = f"@{escape(username)}" if username else (str(int(user_id)) if user_id is not None else "—")
    # RLI/PDI keeps the connector's visual order stable inside the RTL message.
    connector = f"\u2067🪪 <code>{identity}</code>\u2066"
    return (f"\u200f\u202b{name_text}\u202c\u200f\n"
            f"\u200f\u202b┘───────│\u202c\u200f {connector}")


def _render_users(title: str, rows, page: int, max_ranks: int, kind: str) -> tuple[str, InlineKeyboardMarkup]:
    total = min(len(rows), max_ranks)
    pages = max(1, ceil(total / PAGE_SIZE))
    page = max(1, min(page, pages))
    start = (page - 1) * PAGE_SIZE
    current = rows[start:start + PAGE_SIZE]

    medals = ["🥇", "🥈", "🥉"]
    lines = [
        "╭━━━━━━━━━━━━━━━━━━━━╮",
        f"🏆 <b>{title}</b>",
        "│",
        f"│  📖 <b>صفحه {page} از {pages}</b>",
        "╰━━━━━━━━━━━━━━━━━━━━╯",
        "",
    ]
    if not current:
        lines.append("📭 <b>هنوز کاربری برای نمایش وجود ندارد.</b>")
    else:
        for offset, item in enumerate(current):
            rank = start + offset + 1
            icon = medals[rank - 1] if rank <= 3 else "🔹"
            name = _pretty_name(item[0], item[1], item[3] if len(item) > 3 else None)
            xp = float(item[2] or 0)
            # Entire row is explicitly RTL so rank, name, username and value stay on the right.
            lines.append(
                f"\u2067{icon} <b>رتبه {rank}</b>\u2066\n"
                f"\u200f\u202b{name}\u202c\u200f\n"
                f"\u200f\u202b   🎖 <b>تجربه رهبری: {xp:,.0f}</b>\u202c\u200f"
            )
            if offset != len(current) - 1:
                lines.append("──────────────")
    return "\u202b" + "\n".join(lines) + "\u202c", _page_keyboard(kind, page, total, max_ranks)


def _group_rows(session, chat_id: int):
    rows = session.execute(
        select(Country.leader_user_id, Country.leader_name, Country.leadership_experience, User.username, User.first_name)
        .outerjoin(User, User.telegram_id == Country.leader_user_id)
        .join(GroupStatus, GroupStatus.chat_id == Country.chat_id)
        .where(Country.chat_id == chat_id, GroupStatus.active.is_(True))
    ).all()
    totals = {}
    meta = {}
    for uid, leader_name, xp, username, first_name in rows:
        uid = int(uid)
        totals[uid] = totals.get(uid, 0.0) + float(xp or 0)
        # Prefer the live User record over the cached country leader_name.
        meta[uid] = (first_name or leader_name or "بدون نام", username)
    return sorted(
        ((meta[uid][0], meta[uid][1], xp, uid) for uid, xp in totals.items()),
        key=lambda x: (-x[2], x[0].casefold()),
    )[:GROUP_MAX_RANKS]


def _global_rows(session):
    rows = session.execute(
        select(Country.leader_user_id, Country.leader_name, Country.leadership_experience, User.username, User.first_name)
        .outerjoin(User, User.telegram_id == Country.leader_user_id)
        .join(GroupStatus, GroupStatus.chat_id == Country.chat_id)
        .where(GroupStatus.active.is_(True))
    ).all()
    totals = {}
    meta = {}
    for uid, leader_name, xp, username, first_name in rows:
        uid = int(uid)
        totals[uid] = totals.get(uid, 0.0) + float(xp or 0)
        meta[uid] = (first_name or leader_name or "بدون نام", username)
    return sorted(
        ((meta[uid][0], meta[uid][1], xp, uid) for uid, xp in totals.items()),
        key=lambda x: (-x[2], x[0].casefold()),
    )[:GLOBAL_MAX_RANKS]


def _continent_rows(session):
    return session.execute(
        select(Country.continent_name, func.sum(Country.leadership_experience))
        .join(GroupStatus, GroupStatus.chat_id == Country.chat_id)
        .where(GroupStatus.active.is_(True))
        .group_by(Country.continent_name)
        .order_by(func.sum(Country.leadership_experience).desc(), Country.continent_name.asc())
        .limit(CONTINENT_MAX_RANKS)
    ).all()


def _render_continents(rows, page: int):
    total = min(len(rows), CONTINENT_MAX_RANKS)
    pages = max(1, ceil(total / PAGE_SIZE))
    page = max(1, min(page, pages))
    start = (page - 1) * PAGE_SIZE
    current = rows[start:start + PAGE_SIZE]
    lines = [
        "╭━━━━━━━━━━━━━━━━━━━━╮",
        "🌍 <b>برترین قاره‌های جهان</b>",
        "│",
        f"│  📖 <b>صفحه {page} از {pages}</b>",
        "╰━━━━━━━━━━━━━━━━━━━━╯",
        "",
    ]
    medals = ["🥇", "🥈", "🥉"]
    if not current:
        lines.append("📭 <b>هنوز داده‌ای برای نمایش وجود ندارد.</b>")
    else:
        for offset, (name, xp) in enumerate(current):
            rank = start + offset + 1
            icon = medals[rank - 1] if rank <= 3 else "🔹"
            cname = escape(str(name or "بدون نام"))
            lines.append(
                f"\u2067{icon} <b>رتبه {rank}</b>\n"
                f"\u200f\u202b   🌍 <b>{cname}</b>\u202c\u200f\n"
                f"\u200f\u202b   🎖 <b>تجربه رهبری: {float(xp or 0):,.0f}</b>\u202c\u200f"
            )
            if offset != len(current) - 1:
                lines.append("──────────────")
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("🟦 ◀️ قبلی", callback_data=f"leaderboard:continents:{page-1}"))
    nav.append(InlineKeyboardButton(f"📖 {page} / {pages}", callback_data="leaderboard:noop"))
    if page < pages:
        nav.append(InlineKeyboardButton("بعدی ▶️ 🟦", callback_data=f"leaderboard:continents:{page+1}"))
    return "\u202b" + "\n".join(lines) + "\u202c", InlineKeyboardMarkup([nav])


async def _delete_leaderboard_messages(bot, chat_id: int, message_ids: list[int], delay: int = 300):
    """Delete the leaderboard command and bot response after ten minutes."""
    import asyncio
    await asyncio.sleep(delay)
    for message_id in message_ids:
        if not message_id:
            continue
        try:
            await bot.delete_message(chat_id=int(chat_id), message_id=int(message_id))
        except Exception:
            # Missing delete permission, already-deleted message, etc. must not
            # turn a leaderboard cleanup into an update error.
            pass


def _schedule_leaderboard_cleanup(context: ContextTypes.DEFAULT_TYPE, chat_id: int, *message_ids: int):
    ids = [int(x) for x in message_ids if x]
    if ids:
        context.application.create_task(
            _delete_leaderboard_messages(context.bot, int(chat_id), ids),
            update=None,
            name="leaderboard_cleanup",
        )


async def _send_group_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, markup=None):
    if update.effective_chat and update.effective_chat.type in ("group", "supergroup"):
        sent = await update.effective_message.reply_text(text, parse_mode="HTML", reply_markup=markup)
        # پیام دستوری کاربر نباید توسط ربات حذف شود؛ فقط پاسخ‌های خود ربات
        # در صورت فعال بودن پاکسازی بعدی حذف می‌شوند.
        _schedule_leaderboard_cleanup(
            context, int(update.effective_chat.id),
            getattr(sent, "message_id", 0),
        )
        return sent
    return await update.effective_message.reply_text("این دستور فقط داخل گروه قابل استفاده است.")


async def _leaderboard_loading_message(update: Update):
    return await update.effective_message.reply_text(
        "⏳ <b>در حال جمع‌آوری اطلاعات از پایگاه داده...</b>\n\nلطفاً کمی صبر کنید.",
        parse_mode="HTML",
    )


async def _edit_leaderboard_result(update: Update, context: ContextTypes.DEFAULT_TYPE, message, text: str, markup=None):
    await message.edit_text(text, parse_mode="HTML", reply_markup=markup)
    # پیام اصلی کاربر دست‌نخورده باقی می‌ماند؛ فقط پاسخ ربات پاک می‌شود.
    _schedule_leaderboard_cleanup(
        context, int(update.effective_chat.id),
        getattr(message, "message_id", 0),
    )


async def group_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or update.effective_chat.type not in ("group", "supergroup"):
        await _send_group_leaderboard(update, context, "")
        return
    loading = await _leaderboard_loading_message(update)
    with SessionLocal() as s:
        await refresh_known_groups(context.bot, s)
        if not group_is_active(s, int(update.effective_chat.id)):
            await _edit_leaderboard_result(update, context, loading, "📭 این گروه دیگر فعال نیست.")
            return
        if update.effective_user:
            get_or_create_user(s, update.effective_user)
            for c in s.scalars(select(Country).where(Country.leader_user_id == update.effective_user.id)).all():
                c.leader_name = update.effective_user.full_name or update.effective_user.first_name or c.leader_name
        s.commit()
        rows = _group_rows(s, int(update.effective_chat.id))
    text, markup = _render_users("برترین کشورهای قاره", rows, 1, GROUP_MAX_RANKS, "users_group")
    await _edit_leaderboard_result(update, context, loading, text, markup)


async def global_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or update.effective_chat.type not in ("group", "supergroup"):
        await _send_group_leaderboard(update, context, "")
        return
    loading = await _leaderboard_loading_message(update)
    with SessionLocal() as s:
        await refresh_known_groups(context.bot, s)
        if update.effective_user:
            get_or_create_user(s, update.effective_user)
            for c in s.scalars(select(Country).where(Country.leader_user_id == update.effective_user.id)).all():
                c.leader_name = update.effective_user.full_name or update.effective_user.first_name or c.leader_name
        s.commit()
        rows = _global_rows(s)
    text, markup = _render_users("برترین کاربران جهان", rows, 1, GLOBAL_MAX_RANKS, "users_global")
    await _edit_leaderboard_result(update, context, loading, text, markup)


async def continents_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or update.effective_chat.type not in ("group", "supergroup"):
        await _send_group_leaderboard(update, context, "")
        return
    loading = await _leaderboard_loading_message(update)
    with SessionLocal() as s:
        await refresh_known_groups(context.bot, s)
        rows = _continent_rows(s)
    text, markup = _render_continents(rows, 1)
    await _edit_leaderboard_result(update, context, loading, text, markup)


async def leaderboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not update.effective_chat or update.effective_chat.type not in ("group", "supergroup"):
        if query:
            await query.answer("این بخش فقط داخل گروه قابل استفاده است.", show_alert=True)
        return
    parts = (query.data or "").split(":")
    kind = parts[1] if len(parts) > 1 else ""
    if kind == "noop":
        await query.answer()
        return
    try:
        page = int(parts[2]) if len(parts) > 2 else 1
    except ValueError:
        page = 1
    with SessionLocal() as s:
        await refresh_known_groups(context.bot, s)
        if kind == "users_group":
            if query.from_user:
                get_or_create_user(s, query.from_user)
                for c in s.scalars(select(Country).where(Country.leader_user_id == query.from_user.id)).all():
                    c.leader_name = query.from_user.full_name or query.from_user.first_name or c.leader_name
            s.commit()
            rows = _group_rows(s, int(update.effective_chat.id))
            text, markup = _render_users("برترین کشورهای قاره", rows, page, GROUP_MAX_RANKS, kind)
        elif kind == "users_global":
            if query.from_user:
                get_or_create_user(s, query.from_user)
                for c in s.scalars(select(Country).where(Country.leader_user_id == query.from_user.id)).all():
                    c.leader_name = query.from_user.full_name or query.from_user.first_name or c.leader_name
            s.commit()
            rows = _global_rows(s)
            text, markup = _render_users("برترین کاربران جهان", rows, page, GLOBAL_MAX_RANKS, kind)
        elif kind == "continents":
            rows = _continent_rows(s)
            text, markup = _render_continents(rows, page)
        else:
            await query.answer("صفحه‌بندی نامعتبر است.", show_alert=True)
            return
    await query.answer()
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=markup)
