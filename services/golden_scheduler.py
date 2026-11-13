from __future__ import annotations

import asyncio
import json
import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from html import escape

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
    parse_hhmm,
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
    if row:
        try:
            payload = json.loads(row.value)
            if (
                isinstance(payload, dict)
                and int(payload.get('generation', -1)) == generation
                and int(payload.get('continent_chat_id', 0)) == chat_id
                and isinstance(payload.get('events'), list)
                and int(payload.get('schedule_version', 0) or 0) == 2
            ):
                # Persist a daily schedule once. Recomputing ``desired`` on every
                # scheduler loop makes schedule_times() shrink as time advances,
                # which would regenerate the plan every five seconds and keep
                # moving the next box into the future forever.
                return payload['events']
        except Exception:
            pass

    times = schedule_times(cfg, day, now=now)
    types = daily_box_types(cfg, len(times), day, random_seed=f'{chat_id}:{int(cfg.get("schedule_generation", 0) or 0)}')
    events = [{'index': i, 'at': t.isoformat(), 'box': types[i]} for i, t in enumerate(times)]
    raw = json.dumps(
        {
            'generation': generation,
            'schedule_version': 2,
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
    """Publish one box to the group, with a text fallback if photo sending fails.

    Country.chat_id is already the canonical group identifier stored when the
    continent was registered. A separate get_chat preflight was unnecessary and
    could prevent an otherwise-valid send when Telegram's metadata lookup
    temporarily failed. Try the actual send first; if photo upload/rendering is
    rejected, preserve the challenge using a regular text message.
    """
    chat_id = int(country.chat_id)
    try:
        state = load_group_state(session, chat_id)
        answer, opts = make_challenge(int(cfg.get('challenge_digits', 5)), int(cfg.get('options_count', 4)))
        token = f'{chat_id}-{int(datetime.utcnow().timestamp() * 1000)}-{len(state.get("history", []))}-{len(state.get("actives", {}))}'
        icon, name = BOXES[box]
        option_width = max(1, min(4, (len(opts) + 1) // 2))
        rows = []
        for i in range(0, len(opts), option_width):
            rows.append([
                InlineKeyboardButton(
                    value,
                    callback_data=f'golden:answer:{country.id}:{token}:{value}',
                    style='primary',
                ) for value in opts[i:i + option_width]
            ])
        kb = InlineKeyboardMarkup(rows)
        caption = (
            f'{icon} <b>جعبه {name}</b>\n\n'
            '⚡ اولین نفری که رمز درست را پیدا کند، جایزه را می‌برد.\n\n'
            'یکی از گزینه‌های زیر پاسخ صحیح است.'
        )
        msg = None
        try:
            img = challenge_image(answer)
            img.name = 'golden_box.png'
            msg = await app.bot.send_photo(
                chat_id=chat_id,
                photo=img,
                caption=caption,
                parse_mode='HTML',
                reply_markup=kb,
                _bypass_group_limits=True,
                _raise_api_errors=True,
            )
        except Exception:
            LOGGER.exception("Golden box photo send failed; trying text fallback for chat_id=%s box=%s", chat_id, box)

        if msg is None:
            msg = await app.bot.send_message(
                chat_id=chat_id,
                text=caption + f'\n\n🔐 <b>رمز چالش: <tg-spoiler>{escape(str(answer))}</tg-spoiler></b>',
                parse_mode='HTML',
                reply_markup=kb,
                _bypass_group_limits=True,
                _raise_api_errors=True,
            )

        if msg is None:
            raise RuntimeError("Telegram did not return a message while publishing a golden box")
        state['actives'][token] = {
            'token': token,
            'box': box,
            'answer': answer,
            'options': opts,
            'wrong': [],
            'created_at': datetime.utcnow().isoformat(),
            'status': 'open',
            'message_id': int(msg.message_id),
            'chat_id': chat_id,
        }
        save_group_state(session, chat_id, state)
        return True
    except Exception:
        LOGGER.exception("Failed to publish golden box to chat_id=%s box=%s", chat_id, box)
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

            # Publish from today's plan and, during an overnight window, also
            # finish yesterday's plan until its configured end time.
            if cfg.get('enabled') and weights_valid(cfg):
                start_m = parse_hhmm(cfg.get('start', '10:00'))
                end_m = parse_hhmm(cfg.get('end', '23:00'))
                overnight = end_m <= start_m
                schedule_dates = [today]
                if overnight and now_iran.hour * 60 + now_iran.minute <= end_m:
                    schedule_dates.append(today - timedelta(days=1))
                generation = int(cfg.get('schedule_generation', 0) or 0)
                for schedule_day in schedule_dates:
                    if iran_weekday(schedule_day) not in cfg.get('active_days', []):
                        continue
                    day_key = schedule_day.isoformat()
                    for country in countries:
                        chat_id = int(country.chat_id)
                        # Do not create yesterday's plan after a restart if no
                        # plan was ever persisted; that would dump a full day's
                        # boxes in one catch-up burst after midnight.
                        if schedule_day < today:
                            existing_key = f'{DAY_KEY}{day_key}:{chat_id}'
                            existing_row = session.scalar(select(BotSetting).where(BotSetting.key == existing_key))
                            if existing_row is None:
                                continue
                            try:
                                existing_plan = json.loads(existing_row.value or "{}")
                                if int(existing_plan.get("generation", -1)) != generation or not isinstance(existing_plan.get("events"), list):
                                    continue
                            except Exception:
                                continue
                        events = _scheduled(session, schedule_day, cfg, chat_id, now=now_iran)
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
                            # A schedule from yesterday is valid only until its
                            # configured end (the next-day portion of the window).
                            if schedule_day < today and not overnight:
                                continue
                            ok = await _publish(app, session, country, cfg, str(event.get('box') or 'money'))
                            if not ok:
                                continue

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
