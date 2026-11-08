"""Per-message inline-panel ownership."""
from contextvars import ContextVar
from collections import OrderedDict

_current_owner = ContextVar("panel_owner", default=None)
PANEL_OWNERS = OrderedDict()
MAX_PANEL_REGISTRY = 5000

def set_panel_owner(user_id):
    return _current_owner.set(int(user_id) if user_id is not None else None)

def get_panel_owner():
    return _current_owner.get()

def register_panel(chat_id, message_id, user_id):
    if chat_id is not None and message_id is not None and user_id is not None:
        key=(int(chat_id), int(message_id))
        PANEL_OWNERS.pop(key, None)
        PANEL_OWNERS[key] = int(user_id)
        while len(PANEL_OWNERS) > MAX_PANEL_REGISTRY:
            PANEL_OWNERS.popitem(last=False)

def check_panel(chat_id, message_id, user_id):
    key = (int(chat_id), int(message_id))
    owner = PANEL_OWNERS.get(key)
    if owner is None:
        # Fail closed: a panel not known to the current process is stale (for
        # example after a restart) or was not issued by this bot.
        return False, None
    PANEL_OWNERS.move_to_end(key)
    return owner == int(user_id), owner
