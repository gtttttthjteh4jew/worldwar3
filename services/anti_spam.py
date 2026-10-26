"""Fixed, in-code anti-spam limits for users and group bot output."""
from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from database.db import SessionLocal
from services.settings import (get_anti_spam_enabled, get_anti_spam_user_max, get_anti_spam_user_window, get_anti_spam_group_max, get_anti_spam_group_window)

USER_LIMIT_DURATION = 60.0

@dataclass
class UserState:
    requests: deque
    limited_until: float = 0.0
    warning_message_id: int | None = None

_users: dict[int, UserState] = {}
_group_messages: dict[int, deque] = defaultdict(deque)
_group_blocked_until: dict[int, float] = {}
_group_warning_until: dict[int, float] = {}
_lock = asyncio.Lock()


_STATE_PREFIX = "anti_spam_state_v2:"
_STATE_LOCK = __import__("threading").RLock()
_LOADED_USERS = set()
_LOADED_GROUPS = set()


def _state_key(kind: str, ident: int) -> str:
    return f"{_STATE_PREFIX}{kind}:{int(ident)}"


def _load_persisted(kind: str, ident: int):
    from database.models import BotSetting
    import json
    from sqlalchemy import select
    with SessionLocal() as session:
        row = session.scalar(select(BotSetting).where(BotSetting.key == _state_key(kind, ident)))
        if not row or not row.value:
            return {}
        try:
            value = json.loads(row.value)
            return value if isinstance(value, dict) else {}
        except Exception:
            return {}


def _save_persisted(kind: str, ident: int, value: dict) -> None:
    from database.models import BotSetting
    import json
    from sqlalchemy import select
    with SessionLocal() as session:
        row = session.scalar(select(BotSetting).where(BotSetting.key == _state_key(kind, ident)))
        raw = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        if row is None:
            session.add(BotSetting(key=_state_key(kind, ident), value=raw))
        else:
            row.value = raw
        session.commit()


def _hydrate_user(user_id: int) -> UserState:
    uid = int(user_id)
    state = _users.get(uid)
    if state is not None:
        return state
    state = UserState(deque())
    data = _load_persisted("user", uid)
    try:
        state.requests.extend(float(x) for x in data.get("requests", []) if float(x) > 0)
    except Exception:
        state.requests.clear()
    state.limited_until = float(data.get("limited_until", 0) or 0)
    warn = data.get("warning_message_id")
    state.warning_message_id = int(warn) if warn is not None else None
    _users[uid] = state
    _LOADED_USERS.add(uid)
    return state


def _persist_user(user_id: int, state: UserState) -> None:
    now = time.time()
    requests = [float(x) for x in state.requests if now - float(x) <= max(60.0, USER_LIMIT_DURATION)]
    state.requests.clear(); state.requests.extend(requests)
    if state.limited_until <= now:
        state.limited_until = 0.0
        state.warning_message_id = None
    _save_persisted("user", int(user_id), {
        "requests": requests[-100:],
        "limited_until": float(state.limited_until),
        "warning_message_id": state.warning_message_id,
    })


def _hydrate_group(chat_id: int) -> None:
    cid = int(chat_id)
    if cid in _LOADED_GROUPS:
        return
    data = _load_persisted("group", cid)
    q = _group_messages[cid]
    q.clear()
    try:
        q.extend(float(x) for x in data.get("messages", []) if float(x) > 0)
    except Exception:
        q.clear()
    _group_blocked_until[cid] = float(data.get("blocked_until", 0) or 0)
    _group_warning_until[cid] = float(data.get("warning_until", 0) or 0)
    _LOADED_GROUPS.add(cid)


def _persist_group(chat_id: int) -> None:
    cid = int(chat_id)
    q = _group_messages[cid]
    now = time.time()
    messages = [float(x) for x in q if now - float(x) <= max(60.0, USER_LIMIT_DURATION)]
    while q and now - q[0] > max(60.0, USER_LIMIT_DURATION):
        q.popleft()
    if _group_blocked_until.get(cid, 0) <= now:
        _group_blocked_until.pop(cid, None)
        _group_warning_until.pop(cid, None)
    _save_persisted("group", cid, {
        "messages": messages[-100:],
        "blocked_until": float(_group_blocked_until.get(cid, 0) or 0),
        "warning_until": float(_group_warning_until.get(cid, 0) or 0),
    })


def _user_state(user_id: int) -> UserState:
    with _STATE_LOCK:
        return _hydrate_user(user_id)


def remaining_user_limit(user_id: int) -> int:
    with _STATE_LOCK:
        state = _hydrate_user(user_id)
        return max(0, int(state.limited_until - time.time() + 0.999))


def user_warning_sent(user_id: int) -> bool:
    with _STATE_LOCK:
        return _hydrate_user(user_id).warning_message_id is not None


def mark_user_warning_sent(user_id: int, message_id: int = -1) -> None:
    with _STATE_LOCK:
        state = _hydrate_user(user_id)
        state.warning_message_id = int(message_id)
        _persist_user(user_id, state)


def user_is_limited(user_id: int) -> bool:
    with _STATE_LOCK:
        state = _hydrate_user(user_id)
        now = time.time()
        if state.limited_until and now >= state.limited_until:
            state.limited_until = 0.0
            state.warning_message_id = None
            state.requests.clear()
            _persist_user(user_id, state)
            return False
        return state.limited_until > now


def allow_user_request(user_id: int) -> bool:
    """ثبت درخواست واقعی ربات؛ وضعیت سهمیه پس از هر تغییر در SQLite نگهداری می‌شود."""
    with _STATE_LOCK:
        now = time.time()
        state = _hydrate_user(user_id)
        if state.limited_until > now:
            return False
        with SessionLocal() as session:
            if not get_anti_spam_enabled(session):
                return True
            max_requests = max(1, int(get_anti_spam_user_max(session)))
            time_window = max(1.0, float(get_anti_spam_user_window(session)))
        state.limited_until = 0.0
        while state.requests and now - state.requests[0] >= time_window:
            state.requests.popleft()
        state.requests.append(now)
        if len(state.requests) >= max_requests:
            state.limited_until = now + USER_LIMIT_DURATION
            _persist_user(user_id, state)
            return False
        _persist_user(user_id, state)
        return True


def allow_group_message(chat_id: int) -> bool:
    """سقف گروهی با state پایدار؛ Restart دیگر بازه فعال را پاک نمی‌کند."""
    with _STATE_LOCK:
        now = time.time()
        _hydrate_group(chat_id)
        with SessionLocal() as session:
            if not get_anti_spam_enabled(session):
                return True
            max_messages = max(1, int(get_anti_spam_group_max(session)))
            time_window = max(1.0, float(get_anti_spam_group_window(session)))
        cid = int(chat_id)
        blocked_until = _group_blocked_until.get(cid, 0.0)
        if blocked_until > now:
            return False
        if blocked_until:
            _group_blocked_until.pop(cid, None)
            _group_messages.pop(cid, None)
        q = _group_messages[cid]
        if q and now - q[0] >= time_window:
            q.clear()
        if not q:
            q.append(now)
            _persist_group(cid)
            return True
        window_start = q[0]
        if len(q) >= max_messages:
            _group_blocked_until[cid] = window_start + time_window
            _persist_group(cid)
            return False
        q.append(now)
        if len(q) >= max_messages:
            _group_blocked_until[cid] = window_start + time_window
        _persist_group(cid)
        return True


def group_remaining_seconds(chat_id: int) -> int:
    with _STATE_LOCK:
        _hydrate_group(chat_id)
        now = time.time()
        blocked_until = _group_blocked_until.get(int(chat_id), 0.0)
        return max(0, int(blocked_until - now + 0.999)) if blocked_until > now else 0


def should_send_group_warning(chat_id: int) -> bool:
    with _STATE_LOCK:
        _hydrate_group(chat_id)
        now = time.time()
        cid = int(chat_id)
        if _group_blocked_until.get(cid, 0.0) <= now:
            _group_warning_until.pop(cid, None)
            _persist_group(cid)
            return True
        until = _group_warning_until.get(cid, 0.0)
        if now >= until:
            _group_warning_until[cid] = _group_blocked_until[cid]
            _persist_group(cid)
            return True
        return False


def reset_group_state(chat_id: int) -> None:
    """Forget the quota for a group, including its persisted state."""
    with _STATE_LOCK:
        cid = int(chat_id)
        _group_messages.pop(cid, None)
        _group_blocked_until.pop(cid, None)
        _group_warning_until.pop(cid, None)
        _LOADED_GROUPS.discard(cid)
        _save_persisted("group", cid, {})
