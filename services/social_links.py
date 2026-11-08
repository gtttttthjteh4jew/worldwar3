from __future__ import annotations
from datetime import datetime, timezone, timedelta
import json
import re
from sqlalchemy import select
from database.models import BotSetting

KEYS = {
    "panel": "social_panel_url",
    "mandatory_ad": "social_mandatory_ad_url",
    "optional_ad": "social_optional_ad_url",
    "chat": "social_chat_url",
    "channel": "social_channel_url",
    "optional_ad_reward": "social_optional_ad_reward_uranium",
    "items": "social_items_json",
}

SOCIAL_TYPES = ("panel", "mandatory_ad", "optional_ad", "chat", "channel")


def _legacy_settings(session):
    out = {}
    for name, key in KEYS.items():
        if name == "items":
            continue
        row = session.scalar(select(BotSetting).where(BotSetting.key == key))
        out[name] = row.value if row and row.value is not None else ("0" if name == "optional_ad_reward" else "")
    return out


def _load_items(session):
    row = session.scalar(select(BotSetting).where(BotSetting.key == KEYS["items"]))
    if row and row.value:
        try:
            data = json.loads(row.value)
            if isinstance(data, list):
                return data
        except Exception:
            pass
    # Migrate the old one-item-per-type configuration into the new unlimited list.
    old = _legacy_settings(session)
    items = []
    for typ in SOCIAL_TYPES:
        value = str(old.get(typ) or "").strip()
        if value:
            items.append({"id": f"legacy_{typ}", "type": typ, "url": value,
                          "reward": float(old.get("optional_ad_reward") or 0) if typ == "optional_ad" else 0})
    return items


def _save_items(session, items):
    row = session.scalar(select(BotSetting).where(BotSetting.key == KEYS["items"]))
    value = json.dumps(items, ensure_ascii=False)
    if row is None:
        session.add(BotSetting(key=KEYS["items"], value=value))
    else:
        row.value = value


def _item_active(item, now=None):
    if not bool(item.get("active", True)):
        return False
    if now is None:
        now = datetime.now(timezone.utc)
    exp = item.get("expires_at")
    if exp:
        try:
            dt = datetime.fromisoformat(str(exp))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt <= now:
                return False
        except Exception:
            pass
    return True

def get_social_items(session, typ=None):
    items = _load_items(session)
    if typ is None:
        return items
    return [x for x in items if x.get("type") == typ]

def get_active_social_items(session, typ=None):
    items = [x for x in _load_items(session) if _item_active(x)]
    if typ is None:
        return items
    return [x for x in items if x.get("type") == typ]


def add_social_item(session, typ, url, reward=0, chat_id=None, chat_type=None):
    if typ not in SOCIAL_TYPES:
        raise ValueError("invalid social type")
    items = _load_items(session)
    import secrets
    item = {"id": secrets.token_hex(6), "type": typ, "url": str(url).strip(),
            "reward": max(0.0, float(reward or 0)) if typ == "optional_ad" else 0,
            "reward_delay_minutes": 60 if typ == "optional_ad" else 0,
            "active": True}
    if chat_id is not None:
        item["chat_id"] = int(chat_id)
    if chat_type:
        item["chat_type"] = str(chat_type)
    items.append(item)
    _save_items(session, items)
    return item


def update_social_item(session, item_id, url=None, reward=None, chat_id=None, chat_type=None):
    items = _load_items(session)
    for item in items:
        if str(item.get("id")) == str(item_id):
            if url is not None:
                item["url"] = str(url).strip()
            if reward is not None and item.get("type") == "optional_ad":
                item["reward"] = max(0.0, float(reward))
            if chat_id is not None:
                item["chat_id"] = int(chat_id)
            if chat_type:
                item["chat_type"] = str(chat_type)
            _save_items(session, items)
            return item
    return None


def delete_social_item(session, item_id):
    items = _load_items(session)
    new = [x for x in items if str(x.get("id")) != str(item_id)]
    changed = len(new) != len(items)
    if changed:
        _save_items(session, new)
    return changed


def get_social_settings(session):
    """Backward-compatible summary plus unlimited configured items."""
    items = _load_items(session)
    out = {k: "" for k in SOCIAL_TYPES}
    out["optional_ad_reward"] = "0"
    for typ in SOCIAL_TYPES:
        first = next((x for x in items if x.get("type") == typ), None)
        if first:
            out[typ] = str(first.get("url") or "")
            if typ == "optional_ad":
                out["optional_ad_reward"] = str(first.get("reward", 0))
    out["items"] = items
    return out


def set_social_value(session, name, value):
    # Legacy single-value API remains available for compatibility, but writes the
    # first matching item in the new list (or creates one).
    if name in SOCIAL_TYPES:
        items = _load_items(session)
        for item in items:
            if item.get("type") == name:
                item["url"] = str(value).strip()
                _save_items(session, items)
                return
        if str(value).strip():
            add_social_item(session, name, value)
        return
    key = KEYS[name]
    row = session.scalar(select(BotSetting).where(BotSetting.key == key))
    value = str(value).strip()
    if row is None:
        session.add(BotSetting(key=key, value=value))
    else:
        row.value = value

def get_optional_join_pending(session, telegram_id: int):
    key = f"social_optional_join:{int(telegram_id)}"
    row = session.scalar(select(BotSetting).where(BotSetting.key == key))
    if not row or not row.value:
        return None
    try:
        return datetime.fromisoformat(row.value)
    except Exception:
        return None


def save_optional_join_pending(session, telegram_id: int, when: datetime):
    key = f"social_optional_join:{int(telegram_id)}"
    row = session.scalar(select(BotSetting).where(BotSetting.key == key))
    value = when.astimezone(timezone.utc).isoformat()
    if row is None:
        session.add(BotSetting(key=key, value=value))
    else:
        row.value = value


def clear_optional_join_pending(session, telegram_id: int):
    key = f"social_optional_join:{int(telegram_id)}"
    row = session.scalar(select(BotSetting).where(BotSetting.key == key))
    if row is not None:
        session.delete(row)


def chat_target(value: str) -> str:
    value = str(value or '').strip()
    if value.startswith('https://t.me/'):
        tail = value.split('https://t.me/', 1)[1].split('?',1)[0].strip('/')
        if tail and not tail.startswith('+'):
            return '@' + tail.lstrip('@')
    return value


def private_invite_link(value: str) -> bool:
    """Return True for Telegram private invite links that Bot API cannot resolve to a chat by URL."""
    value = str(value or "").strip().lower()
    return (value.startswith("https://t.me/+") or value.startswith("http://t.me/+")
            or value.startswith("t.me/+") or value.startswith("https://t.me/joinchat/")
            or value.startswith("http://t.me/joinchat/") or value.startswith("t.me/joinchat/"))


def private_message_link_chat_id(value: str):
    """Extract a Telegram private chat/channel id from a copied message link.

    Telegram private message links use /c/<internal_id>/<message_id>. The internal
    id is converted to the Bot API -100... chat id. The function intentionally
    accepts a larger surrounding string so an owner can paste a sentence containing
    the message URL.
    """
    value = str(value or "").strip()
    m = re.search(r"(?:https?://)?(?:www\.)?(?:t\.me|telegram\.me)/c/(\d+)(?:/\d+)?(?:\?[^\s]+)?", value, re.I)
    if not m:
        return None
    return int("-100" + m.group(1))


def public_chat_target(value: str):
    """Return a Telegram-resolvable public @username from a public chat/channel URL.

    Public post links may be either ``https://t.me/ChannelName/123`` or a bare
    ``t.me/ChannelName/123``.  The trailing message id is intentionally ignored
    for ``get_chat``; the ChannelName is the chat identity.
    """
    value = str(value or '').strip()
    if value.startswith('@'):
        return value.split()[0]
    m = re.match(r'^(?:https?://)?(?:www\.)?(?:t\.me|telegram\.me)/([A-Za-z0-9_]{4,})/(?:\d+)(?:\?.*)?/?$', value, re.I)
    if m:
        return '@' + m.group(1)
    m = re.match(r'^(?:https?://)?(?:www\.)?(?:t\.me|telegram\.me)/([A-Za-z0-9_]{4,})(?:\?.*)?/?$', value, re.I)
    if m:
        username = m.group(1)
        if not username.startswith(('+', 'joinchat')):
            return '@' + username
    return None


def social_item_button_url(value: str) -> str:
    """Normalize a link for Telegram inline URL buttons without breaking invite links."""
    value = str(value or '').strip()
    if value.startswith('@'):
        return 'https://t.me/' + value[1:]
    if value.startswith('t.me/'):
        return 'https://' + value
    return value


def mandatory_items(session):
    return [x for x in get_social_items(session, 'mandatory_ad') if str(x.get('url') or '').strip()]
