from __future__ import annotations

import asyncio
import json
import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from database.db import SessionLocal
from database.models import Country, BotSetting
from services.golden_boxes import (
    BOXES,
    challenge_image,
    daily_box_types,
    iran_weekday,
    load_config,
    load_state,
    make_challenge,
    save_state,
    load_group_state,
    save_group_state,
    schedule_times,
    weights_valid,
)

DAY_KEY = 'golden:schedule:'
IRAN_TZ = ZoneInfo('Asia/Tehran')
LOGGER = logging.getLogger("worldwar3_bot.golden_scheduler")


def _scheduled(session, day: date, cfg, continent_chat_id, now=None):
    """Persist exactly daily_count events for one Telegram continent/group.

    In this game a continent is represented by a Telegram group/supergroup
    (Country.chat_id). The owner's daily count therefore belongs to each
    continent independently: daily_count=30 means 30 boxes in every active
    continent during the configured time window, never 30 per country row and
    never an accidental global total shared by all continents.
    """
    chat_id = int(continent_chat_id)
    key = f"{DAY_KEY}{day.strftime('%Y-%m-%d')}:{chat_id}"
    row = session.scalar(select(BotSetting).where(BotSetting.key == key))
    generation = int(cfg.get('schedule_generation', 0) or 0)
    desired = len(schedule_times(cfg, day, now=now))
    if row:
        try:
            payload = json.loads(row.value)
            if (
                isinstance(payload, dict)
                and int(payload.get('generation', -1)) == generation
                and int(payload.get('continent_chat_id', 0)) == chat_id
                and isinstance(payload.get('events'), list)
            ):
                existing = payload['events']
                if len(existing) == desired:
                    return existing
        except Exception:
            pass

    times = schedule_times(cfg, day, now=now)
    types = daily_box_types(cfg, len(times), day, random_seed=f'{chat_id}:{int(cfg.get("schedule_generation", 0) or 0)}')
    events = [{'index': i, 'at': t.isoformat(), 'box': types[i]} for i, t in enumerate(times)]
    raw = json.dumps(
        {
            'generation': generation,
            'continent_chat_id': chat_id,
            'daily_count': len(events),
            'randomized_per_group': True,
            'events': events,
        },
        ensure_ascii=False,
    )
    if row:
        row.value = raw
    else:
        session.add(BotSetting(key=key, value=raw))
    session.commit()
    return events


async def _publish(app, session, country, cfg, box):
    """Publish one real box message to the country's actual Telegram group."""
    try:
        chat = await app.bot.get_chat(int(country.chat_id))
        if getattr(chat, 'type', None) not in {'group', 'supergroup'}:
            return False
        if getattr(country, 'chat_type', None) != getattr(chat, 'type', None):
            country.chat_type = chat.type
            session.flush()

        state = load_group_state(session, country.chat_id)
        answer, opts = make_challenge(int(cfg.get('challenge_digits', 5)), int(cfg.get('options_count', 4)))
        token = f'{int(country.chat_id)}-{int(datetime.utcnow().timestamp() * 1000)}-{len(state.get("history", []))}-{len(state.get("actives", {}))}'
        icon, name = BOXES[box]
        option_width = max(1, min(4, (len(opts) + 1) // 2))
        rows = []
        for i in range(0, len(opts), option_width):
            rows.append([
                InlineKeyboardButton(
                    x,
                    callback_data=f'golden:answer:{country.id}:{token}:{x}',
                    style='primary',
                ) for x in opts[i:i + option_width]
            ])
        kb = InlineKeyboardMarkup(rows)
        img = challenge_image(answer)
        msg = await app.bot.send_photo(
            chat_id=int(country.chat_id),
            photo=img,
            caption=(
                f'{icon} <b>جعبه {name}</b>\n\n'
                '⚡ اولین نفری که رمز درست را پیدا کند، جایزه را می‌برد.\n\n'
                'یکی از گزینه‌های زیر پاسخ صحیح است.'
            ),
            parse_mode='HTML',
            reply_markup=kb,
        )
        state['actives'][token] = {
            'token': token,
            'box': box,
            'answer': answer,
            'options': opts,
            'wrong': [],
            'created_at': datetime.utcnow().isoformat(),
            'status': 'open',
            'message_id': int(msg.message_id),
            'chat_id': int(country.chat_id),
        }
        save_group_state(session, country.chat_id, state)
        return True
    except Exception:
        return False


def _mark_sent(state, day_key, index):
    sent = state.setdefault('daily_sent', {}).setdefault(day_key, [])
    if index not in sent:
        sent.append(index)
        sent.sort()


async def golden_scheduler(app):
    while True:
        now_utc = datetime.utcnow()
        now_iran = datetime.now(IRAN_TZ)
        session = SessionLocal()
        try:
            cfg = load_config(session)
            today = now_iran.date()

            # Country records are individual countries, while box messages are
            # group-level. Use one representative country per real Telegram
            # group for scheduling/expiry, but process upgrades for every country.
            all_countries = session.scalars(select(Country)).all()
            countries = []
            seen_chats = set()
            for c in all_countries:
                try:
                    chat_id = int(c.chat_id)
                except Exception:
                    continue
                if chat_id in seen_chats:
                    continue
                seen_chats.add(chat_id)
                countries.append(c)

            # Complete country-specific box upgrades for every country.
            for country in all_countries:
                state = load_state(session, country.id)
                upgrades = state.get('upgrades', {}) or {}
                changed = False
                for box, pending in list(upgrades.items()):
                    try:
                        finish = datetime.fromisoformat(str(pending.get('finish_at')))
                    except Exception:
                        continue
                    if now_utc >= finish and box in BOXES:
                        target = int(pending.get('target', state['levels'].get(box, 1)))
                        state['levels'][box] = max(int(state['levels'].get(box, 1)), target)
                        upgrades.pop(box, None)
                        changed = True
                state['upgrades'] = upgrades
                if changed:
                    save_state(session, country.id, state)

            # Publish new boxes only from the current Owner configuration.
            if cfg.get('enabled') and weights_valid(cfg) and iran_weekday(today) in cfg.get('active_days', []):
                day_key = today.isoformat()
                generation = int(cfg.get('schedule_generation', 0) or 0)
                for country in countries:
                    chat_id = int(country.chat_id)
                    events = _scheduled(session, today, cfg, chat_id, now=now_iran)
                    sent_key = f'{day_key}:{generation}:{chat_id}'
                    state = load_group_state(session, chat_id)
                    sent = set(state.setdefault('daily_sent', {}).get(sent_key, []))

                    for event in events:
                        idx = int(event.get('index', 0))
                        if idx in sent:
                            continue
                        try:
                            at = datetime.fromisoformat(str(event.get('at')))
                        except Exception:
                            continue
                        if now_iran < at:
                            continue

                        ok = await _publish(app, session, country, cfg, str(event.get('box') or 'money'))
                        if not ok:
                            continue

                        # _publish() writes the active box to the DB. Reload the
                        # state before marking the schedule event as sent so a
                        # stale snapshot can never erase the newly-open box.
                        fresh_state = load_group_state(session, chat_id)
                        _mark_sent(fresh_state, sent_key, idx)
                        save_group_state(session, chat_id, fresh_state)
                        state = fresh_state
                        sent = set(state.setdefault('daily_sent', {}).get(sent_key, []))

            # Expire unanswered boxes independently of whether new sending is
            # enabled today. The owner-controlled unanswered-delete time is used
            # for every group.
            expire_after = timedelta(seconds=int(cfg.get('unanswered_delete_seconds', 60)))
            for country in countries:
                chat_id = int(country.chat_id)
                state = load_group_state(session, chat_id)
                actives = state.get('actives', {}) or {}
                active_changed = False
                for token, active in list(actives.items()):
                    if active.get('status') != 'open':
                        actives.pop(token, None)
                        active_changed = True
                        continue
                    try:
                        created = datetime.fromisoformat(str(active.get('created_at')))
                    except Exception:
                        continue
                    if now_utc - created >= expire_after:
                        message_id = active.get('message_id')
                        if message_id:
                            try:
                                await app.bot.delete_message(chat_id=int(country.chat_id), message_id=int(message_id))
                            except Exception:
                                pass
                        active['status'] = 'expired'
                        active['expired_at'] = now_utc.isoformat()
                        state.setdefault('history', []).append(active)
                        actives.pop(token, None)
                        active_changed = True
                state['actives'] = actives
                if active_changed:
                    save_group_state(session, chat_id, state)
        except Exception:
            # One broken country/API call must never stop the scheduler loop.
            LOGGER.exception("Golden-box scheduler cycle failed")
        finally:
            session.close()
        await asyncio.sleep(5)
