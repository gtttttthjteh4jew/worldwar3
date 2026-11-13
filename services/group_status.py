from __future__ import annotations
from datetime import datetime
from telegram.error import BadRequest, Forbidden
from sqlalchemy import select
from database.models import GroupStatus, Country

_ACTIVE_STATUSES = {"member", "administrator", "creator", "restricted"}


def set_group_status(session, chat_id: int, *, active: bool, chat_type: str | None = None, title: str | None = None):
    row = session.scalar(select(GroupStatus).where(GroupStatus.chat_id == int(chat_id)))
    if row is None:
        row = GroupStatus(chat_id=int(chat_id), active=bool(active), chat_type=chat_type or "group", title=title, updated_at=datetime.utcnow())
        session.add(row)
    else:
        row.active = bool(active)
        if chat_type:
            row.chat_type = chat_type
        if title is not None:
            row.title = title
        row.updated_at = datetime.utcnow()
    return row


async def refresh_known_groups(bot, session):
    """Synchronize group existence/membership without deleting any game data."""
    ids = [int(x) for x in session.scalars(select(Country.chat_id).distinct()).all()]
    if not ids:
        return
    me = await bot.get_me()
    for chat_id in ids:
        try:
            member = await bot.get_chat_member(chat_id=chat_id, user_id=me.id)
            status = getattr(member, "status", "")
            active = status in _ACTIVE_STATUSES
            chat = await bot.get_chat(chat_id)
            set_group_status(session, chat_id, active=active, chat_type=getattr(chat, "type", None), title=getattr(chat, "title", None))
        except (BadRequest, Forbidden):
            # Bot removed/kicked or the group no longer exists: mark inactive only.
            set_group_status(session, chat_id, active=False)
        except Exception:
            # Temporary Telegram/network failure must not hide a group permanently.
            continue
    session.commit()


def group_is_active(session, chat_id: int) -> bool:
    row = session.scalar(select(GroupStatus).where(GroupStatus.chat_id == int(chat_id)))
    # Legacy groups without a status row remain visible until their first sync.
    return True if row is None else bool(row.active)
