from telegram import Bot, BotCommand, BotCommandScopeChat, BotCommandScopeDefault, BotCommandScopeAllGroupChats, MenuButtonCommands
from telegram.error import BadRequest, Forbidden

from config import OWNER_ID
from database.db import SessionLocal
from services.admin import get_admins, get_users


USER_COMMANDS = [
    BotCommand("start", "شروع ربات"),
]

ADMIN_COMMANDS = [
    BotCommand("start", "شروع ربات"),
    BotCommand("admin", "پنل مدیریت"),
]

OWNER_COMMANDS = [
    BotCommand("start", "شروع ربات"),
    BotCommand("admin", "پنل مدیریت"),
    BotCommand("owner", "پنل مالک"),
]

GROUP_COMMANDS = [
    BotCommand("start", "شروع ربات"),
    BotCommand("leaderboard_continent", "برترین کشورهای قاره"),
    BotCommand("leaderboard_global", "برترین کاربران جهان"),
    BotCommand("leaderboard_continents", "برترین قاره های جهان"),
]


async def set_user_command_scope(bot: Bot, telegram_id: int, *, owner: bool = False, admin: bool = False, include_back: bool = False):
    """Set commands visible in a specific private chat."""
    if owner:
        commands = OWNER_COMMANDS
    elif admin:
        commands = ADMIN_COMMANDS
    else:
        commands = USER_COMMANDS

    try:
        chat_id = int(telegram_id)
        await bot.set_my_commands(
            commands,
            scope=BotCommandScopeChat(chat_id=chat_id),
        )
        # Keep Telegram's native four-square Commands button visible in every
        # private chat that has a command menu. This is Telegram's own menu
        # button, not a custom reply/inline button, so it survives navigation
        # between all sections that use prepared commands.
        try:
            await bot.set_chat_menu_button(
                chat_id=chat_id,
                menu_button=MenuButtonCommands(),
            )
        except (BadRequest, Forbidden):
            # A stale/unavailable chat must not prevent command synchronization.
            pass
    except (BadRequest, Forbidden) as exc:
        # A user may have blocked the bot, deleted their account, or otherwise
        # become unavailable. Telegram then rejects ChatCommandScope with
        # errors such as "Chat not found". One stale user must never prevent
        # the whole bot from starting or syncing the remaining users.
        text = str(exc).lower()
        if "chat not found" in text or "user not found" in text or "forbidden" in text or "bot was blocked" in text:
            return False
        raise
    return True


async def sync_all_command_scopes(bot: Bot):
    """Reset default commands and restore the correct per-user scopes."""
    # در چت خصوصی کاربر فقط /start دیده می‌شود؛ لیدربوردها فقط در گروه‌ها هستند.
    await bot.set_my_commands(USER_COMMANDS, scope=BotCommandScopeDefault())
    await bot.set_my_commands(GROUP_COMMANDS, scope=BotCommandScopeAllGroupChats())
    # Telegram's native Commands/menu button must remain available by default
    # as well; per-user scopes below reinforce it for every known private chat.
    try:
        await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    except (BadRequest, Forbidden):
        pass

    if OWNER_ID:
        await set_user_command_scope(bot, OWNER_ID, owner=True, admin=True)

    with SessionLocal() as session:
        admins = get_admins(session)
        admin_ids = {int(a.telegram_id) for a in admins}
        # Explicitly reset the per-chat command menu for every registered user.
        # This removes stale /admin and /owner entries left by older versions.
        for user in get_users(session):
            uid = int(user.telegram_id)
            if OWNER_ID and uid == int(OWNER_ID):
                await set_user_command_scope(bot, uid, owner=True, admin=True)
            elif uid in admin_ids:
                await set_user_command_scope(bot, uid, admin=True)
            else:
                await set_user_command_scope(bot, uid)


async def grant_admin_command_scope(bot: Bot, telegram_id: int):
    """Immediately show /admin to a newly-created admin."""
    if OWNER_ID and int(telegram_id) == int(OWNER_ID):
        await set_user_command_scope(bot, telegram_id, owner=True, admin=True)
        return
    await set_user_command_scope(bot, telegram_id, admin=True)


async def revoke_admin_command_scope(bot: Bot, telegram_id: int):
    """Immediately hide /admin after an admin is removed."""
    if OWNER_ID and int(telegram_id) == int(OWNER_ID):
        await set_user_command_scope(bot, telegram_id, owner=True, admin=True)
        return
    await set_user_command_scope(bot, telegram_id)
