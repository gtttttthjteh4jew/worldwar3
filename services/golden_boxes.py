from __future__ import annotations

import hashlib
import json
import threading
import math
import random
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from io import BytesIO

from sqlalchemy import select
from database.models import BotSetting

_BOX_STATE_LOCK = threading.RLock()

PREFIX = 'golden:'
IRAN_TZ = ZoneInfo('Asia/Tehran')
BOXES = {
    'money': ('💰', 'پول'),
    'fuel': ('⛽', 'سوخت'),
    'metal': ('🔩', 'فلز'),
    'uranium': ('☢️', 'اورانیوم'),
}
MAX_LEVEL = 100
MAX_DAILY_COUNT = 10_000


def _default():
    cfg = {
        'enabled': False,
        'daily_count': 5,
        'start': '10:00',
        'end': '23:00',
        'active_days': [0, 1, 2, 3, 4, 5, 6],
        'weights': {k: 25.0 for k in BOXES},
        'opened_delete_seconds': 30,
        'unanswered_delete_seconds': 60,
        'challenge_digits': 5,
        'options_count': 4,
        'levels': {},
        'distribution_version': 2,
    }
    bases = {'money': 50000, 'fuel': 100, 'metal': 100, 'uranium': 10}
    costs = {'money': 100000, 'fuel': 100000, 'metal': 100000, 'uranium': 100000}
    for k in BOXES:
        rewards_min = {str(i): float(bases[k] * i) for i in range(1, MAX_LEVEL + 1)}
        rewards_max = dict(rewards_min)
        cfg['levels'][k] = {
            'max_level': MAX_LEVEL,
            'upgrade_times': {str(i): 0 for i in range(1, MAX_LEVEL + 1)},
            'reward_min': rewards_min,
            'reward_max': rewards_max,
            # Legacy field is retained only for compatibility with older DB data.
            'rewards': dict(rewards_min),
            'costs': {str(i): float(costs[k] * i) for i in range(1, MAX_LEVEL + 1)},
            'hq_required': {str(i): 1 for i in range(2, MAX_LEVEL + 1)},
            'instant_finish_uranium': 0.0,
        }
    return cfg


def _row(session):
    return session.scalar(select(BotSetting).where(BotSetting.key == PREFIX + 'config'))


def _migrate_reward_range(level_cfg: dict, level: int, default_value: float):
    """Normalize old scalar rewards and new min/max reward ranges."""
    mins = level_cfg.setdefault('reward_min', {})
    maxs = level_cfg.setdefault('reward_max', {})
    legacy = level_cfg.get('rewards', {})
    key = str(level)
    if key not in mins:
        value = legacy.get(key, default_value) if isinstance(legacy, dict) else default_value
        if isinstance(value, dict):
            mins[key] = float(value.get('min', value.get('minimum', default_value)) or 0)
            maxs.setdefault(key, float(value.get('max', value.get('maximum', mins[key])) or 0))
        else:
            mins[key] = float(value or 0)
    if key not in maxs:
        value = legacy.get(key, mins[key]) if isinstance(legacy, dict) else mins[key]
        if isinstance(value, dict):
            maxs[key] = float(value.get('max', value.get('maximum', mins[key])) or mins[key])
        else:
            maxs[key] = float(value or mins[key])
    mins[key] = max(0.0, float(mins[key] or 0))
    maxs[key] = max(mins[key], float(maxs[key] or 0))


def load_config(session):
    row = _row(session)
    try:
        cfg = json.loads(row.value) if row else None
    except Exception:
        cfg = None
    defaults = _default()
    if not isinstance(cfg, dict):
        cfg = defaults

    def merge(dst, src):
        for k, v in src.items():
            if isinstance(v, dict):
                if not isinstance(dst.get(k), dict):
                    dst[k] = {}
                merge(dst[k], v)
            elif k not in dst:
                dst[k] = v

    merge(cfg, defaults)
    cfg['daily_count'] = max(0, min(MAX_DAILY_COUNT, int(cfg.get('daily_count', 5) or 0)))
    cfg['opened_delete_seconds'] = max(0, int(cfg.get('opened_delete_seconds', 30) or 0))
    cfg['unanswered_delete_seconds'] = max(1, int(cfg.get('unanswered_delete_seconds', 60) or 60))
    cfg['active_days'] = [int(x) for x in cfg.get('active_days', list(range(7))) if int(x) in range(7)]
    cfg['weights'] = {k: max(0.0, float(cfg.get('weights', {}).get(k, 0) or 0)) for k in BOXES}
    cfg['distribution_version'] = max(2, int(cfg.get('distribution_version', 2) or 2))

    for k in BOXES:
        lv = cfg['levels'].setdefault(k, defaults['levels'][k].copy())
        lv.setdefault('upgrade_times', {})
        lv.setdefault('costs', {})
        lv.setdefault('reward_min', {})
        lv.setdefault('reward_max', {})
        lv.setdefault('hq_required', {})
        legacy_time = max(0, int(lv.get('upgrade_seconds', 0) or 0))
        for i in range(1, MAX_LEVEL + 1):
            key = str(i)
            lv['upgrade_times'].setdefault(key, legacy_time)
            lv['upgrade_times'][key] = max(0, int(lv['upgrade_times'].get(key, 0) or 0))
            lv['costs'].setdefault(key, defaults['levels'][k]['costs'][key])
            lv['costs'][key] = max(0.0, float(lv['costs'].get(key, 0) or 0))
            _migrate_reward_range(lv, i, defaults['levels'][k]['reward_min'][key])
        lv['hq_required'].pop('1', None)
        for i in range(2, MAX_LEVEL + 1):
            key = str(i)
            lv['hq_required'].setdefault(key, 1)
            lv['hq_required'][key] = max(1, int(lv['hq_required'].get(key, 1) or 1))
        lv['max_level'] = max(1, min(MAX_LEVEL, int(lv.get('max_level', MAX_LEVEL) or MAX_LEVEL)))
        lv['instant_finish_uranium'] = max(0.0, float(lv.get('instant_finish_uranium', 0) or 0))

    save_config(session, cfg)
    return cfg


def _schedule_fingerprint(cfg):
    return {
        'enabled': bool(cfg.get('enabled', False)),
        'daily_count': int(cfg.get('daily_count', 0) or 0),
        'start': str(cfg.get('start', '10:00')),
        'end': str(cfg.get('end', '23:00')),
        'active_days': sorted(int(x) for x in (cfg.get('active_days') or [])),
        'weights': {k: float((cfg.get('weights') or {}).get(k, 0) or 0) for k in BOXES},
        'distribution_version': int(cfg.get('distribution_version', 2) or 2),
    }


def save_config(session, cfg):
    with _BOX_STATE_LOCK:
        row = _row(session)
        if row:
            try:
                old_cfg = json.loads(row.value) if row.value else {}
            except Exception:
                old_cfg = {}
            old_fp = _schedule_fingerprint(old_cfg) if isinstance(old_cfg, dict) else None
            new_fp = _schedule_fingerprint(cfg)
            generation = int((old_cfg or {}).get('schedule_generation', 0) or 0)
            if old_fp != new_fp:
                generation += 1
            cfg['schedule_generation'] = max(0, generation)
            row.value = json.dumps(cfg, ensure_ascii=False)
        else:
            cfg['schedule_generation'] = max(1, int(cfg.get('schedule_generation', 0) or 0))
            session.add(BotSetting(key=PREFIX + 'config', value=json.dumps(cfg, ensure_ascii=False)))
        session.commit()


def _state_row(session, country_id):
    return session.scalar(select(BotSetting).where(BotSetting.key == f'{PREFIX}state:{int(country_id)}'))


def load_state(session, country_id):
    row = _state_row(session, country_id)
    try:
        state = json.loads(row.value) if row else None
    except Exception:
        state = None
    if not isinstance(state, dict):
        state = {}

    state.setdefault('levels', {k: 1 for k in BOXES})
    state.setdefault('history', [])
    state.setdefault('upgrades', {})
    state.setdefault('actives', {})
    state.setdefault('daily_sent', {})

    # Migrate the old single-active schema to multiple independently tracked boxes.
    legacy_active = state.pop('active', None)
    if legacy_active and isinstance(legacy_active, dict) and legacy_active.get('token'):
        state['actives'].setdefault(str(legacy_active['token']), legacy_active)

    if not isinstance(state['actives'], dict):
        state['actives'] = {}
    if not isinstance(state['daily_sent'], dict):
        state['daily_sent'] = {}

    for k in BOXES:
        state['levels'][k] = max(1, min(MAX_LEVEL, int(state['levels'].get(k, 1) or 1)))

    # Keep only a few recent days/generations of sent-index bookkeeping.
    # New schedule generations use keys like YYYY-MM-DD:generation so a rebuilt
    # plan never inherits sent indexes from the previous plan.
    today_key = datetime.utcnow().date().isoformat()
    keep_keys = []
    for raw_key in state['daily_sent'].keys():
        day_key = str(raw_key).split(':', 1)[0]
        try:
            day_value = date.fromisoformat(day_key)
        except Exception:
            continue
        if day_value.isoformat() <= today_key:
            keep_keys.append((day_value.isoformat(), str(raw_key)))
    keep_keys = [raw_key for _, raw_key in sorted(keep_keys)[-12:]]
    state['daily_sent'] = {k: state['daily_sent'][k] for k in keep_keys}
    return state


def save_state(session, country_id, state):
    with _BOX_STATE_LOCK:
        row = _state_row(session, country_id)
        raw = json.dumps(state, ensure_ascii=False)
        if row:
            row.value = raw
        else:
            session.add(BotSetting(key=f'{PREFIX}state:{int(country_id)}', value=raw))
        session.commit()


GROUP_STATE_PREFIX = PREFIX + 'group_state:'

def _normalize_group_state(state):
    if not isinstance(state, dict):
        state = {}
    state.setdefault('history', [])
    state.setdefault('actives', {})
    state.setdefault('daily_sent', {})
    if not isinstance(state['history'], list):
        state['history'] = []
    if not isinstance(state['actives'], dict):
        state['actives'] = {}
    if not isinstance(state['daily_sent'], dict):
        state['daily_sent'] = {}
    # Keep only recent sent-index bookkeeping. This uses UTC consistently with the
    # legacy country state because these indexes are schedule bookkeeping, not display time.
    today_key = datetime.utcnow().date().isoformat()
    keep = []
    for raw_key in state['daily_sent'].keys():
        day_key = str(raw_key).split(':', 1)[0]
        try:
            day_value = date.fromisoformat(day_key)
        except Exception:
            continue
        if day_value.isoformat() <= today_key:
            keep.append((day_value.isoformat(), str(raw_key)))
    keep = [raw_key for _, raw_key in sorted(keep)[-12:]]
    state['daily_sent'] = {k: state['daily_sent'][k] for k in keep}
    return state

def load_group_state(session, chat_id):
    key = f'{GROUP_STATE_PREFIX}{int(chat_id)}'
    row = session.scalar(select(BotSetting).where(BotSetting.key == key))
    if row is not None:
        try:
            state = json.loads(row.value or '{}')
        except Exception:
            state = {}
        return _normalize_group_state(state)

    # One-time migration from the previous schema, where group activity was stored
    # on whichever Country row happened to represent the group. Merge every legacy
    # country state for this Telegram chat so changing/deleting the representative
    # country cannot orphan active boxes or their history.
    merged = {'history': [], 'actives': {}, 'daily_sent': {}}
    try:
        from database.models import Country
        country_ids = list(session.scalars(select(Country.id).where(Country.chat_id == int(chat_id))).all())
    except Exception:
        country_ids = []
    for cid in country_ids:
        legacy = load_state(session, int(cid))
        for token, active in (legacy.get('actives') or {}).items():
            if token not in merged['actives']:
                merged['actives'][token] = active
        for item in legacy.get('history', []) or []:
            token = str(item.get('token') or '') if isinstance(item, dict) else ''
            if token and any(str(x.get('token') or '') == token for x in merged['history'] if isinstance(x, dict)):
                continue
            merged['history'].append(item)
        for day_key, indexes in (legacy.get('daily_sent') or {}).items():
            target = merged['daily_sent'].setdefault(str(day_key), [])
            for idx in indexes or []:
                if idx not in target:
                    target.append(idx)
            target.sort()
    merged = _normalize_group_state(merged)
    session.add(BotSetting(key=key, value=json.dumps(merged, ensure_ascii=False)))
    session.flush()
    return merged

def save_group_state(session, chat_id, state):
    with _BOX_STATE_LOCK:
        key = f'{GROUP_STATE_PREFIX}{int(chat_id)}'
        raw = json.dumps(_normalize_group_state(state), ensure_ascii=False)
        row = session.scalar(select(BotSetting).where(BotSetting.key == key))
        if row is not None:
            row.value = raw
        else:
            session.add(BotSetting(key=key, value=raw))
        session.commit()


def weights_valid(cfg):
    weights = [max(0.0, float(cfg.get('weights', {}).get(k, 0) or 0)) for k in BOXES]
    return bool(weights) and abs(sum(weights) - 100.0) < 1e-6


def daily_box_types(cfg, count: int, for_date: date, random_seed=None):
    """Build a weighted random sequence independently for each group/day.

    Every scheduled event is sampled from the Owner-configured box weights, so
    a 10% Uranium setting really means a 10% selection probability rather than
    a forced daily quota. ``random_seed`` separates the deterministic schedule
    for each Telegram group while keeping the same configured probabilities.
    """
    count = max(0, int(count or 0))
    if count <= 0:
        return []
    weights = {k: max(0.0, float(cfg.get('weights', {}).get(k, 0) or 0)) for k in BOXES}
    total = sum(weights.values())
    if total <= 0:
        return ['money'] * count

    keys = list(BOXES.keys())
    weight_values = [weights[k] for k in keys]
    seed_material = (
        f"{for_date.isoformat()}|{count}|group:{random_seed!s}|"
        + '|'.join(f'{k}:{weights[k]:.8f}' for k in keys)
    )
    seed = int.from_bytes(hashlib.sha256(seed_material.encode('utf-8')).digest()[:8], 'big')
    rng = random.Random(seed)
    return rng.choices(keys, weights=weight_values, k=count)


def choose_type(cfg):
    # Kept for compatibility with callers outside the scheduler.
    sequence = daily_box_types(cfg, 1, datetime.utcnow().date(), random_seed='compat')
    return sequence[0] if sequence else 'money'


def hq_required_for(cfg, box, level):
    """Minimum Command Center level required to reach a box level. Level 1 has no requirement."""
    level = int(level or 1)
    if level <= 1:
        return 0
    data = (cfg.get('levels') or {}).get(box) or {}
    return max(1, int((data.get('hq_required') or {}).get(str(level), 1) or 1))


def reward_range_for(cfg, box, level):
    data = cfg['levels'][box]
    key = str(level)
    lo = float(data.get('reward_min', {}).get(key, data.get('rewards', {}).get(key, 0)) or 0)
    hi = float(data.get('reward_max', {}).get(key, lo) or lo)
    lo = max(0.0, lo)
    hi = max(lo, hi)
    return lo, hi


def reward_for(cfg, box, level):
    lo, hi = reward_range_for(cfg, box, level)
    if math.isclose(lo, hi):
        return lo
    return random.SystemRandom().uniform(lo, hi)


def cost_for(cfg, box, next_level):
    return float(cfg['levels'][box]['costs'].get(str(next_level), 0) or 0)


def apply_reward(country, box, amount):
    if box == 'money':
        country.money = float(country.money or 0) + amount
    elif box == 'fuel':
        country.fuel = float(country.fuel or 0) + amount
    elif box == 'metal':
        country.metal = float(country.metal or 0) + amount
    else:
        country.uranium = float(country.uranium or 0) + amount


def make_challenge(digits=5, n=4):
    digits = max(1, int(digits))
    n = max(2, int(n))
    low = 10 ** (digits - 1) if digits > 1 else 0
    high = (10 ** digits) - 1
    answer = f'{random.randint(low, high):0{digits}d}'
    vals = {answer}
    max_unique = 10 ** digits
    target = min(n, max_unique)
    attempts = 0
    while len(vals) < target and attempts < target * 30:
        vals.add(f'{random.randint(low, high):0{digits}d}')
        attempts += 1
    if len(vals) < target:
        for value in range(max(0, low), high + 1):
            vals.add(f'{value:0{digits}d}')
            if len(vals) >= target:
                break
    opts = list(vals)
    random.shuffle(opts)
    return answer, opts


def challenge_image(answer):
    from PIL import Image, ImageDraw, ImageFont
    import os

    # Keep a consistent photo size, but make the challenge code itself occupy
    # almost the entire usable canvas. Different digit counts naturally have
    # different glyph aspect ratios, so the rendered code is fitted to both
    # dimensions rather than being limited by a fixed font-size ceiling.
    width, height = 8000, 3334
    im = Image.new('RGB', (width, height), 'white')

    font_candidates = [
        os.path.join(os.path.dirname(__file__), 'DejaVuSans-Bold.ttf'),
        r'C:\Windows\Fonts\arialbd.ttf',
        r'C:\Windows\Fonts\segoeuib.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
    ]
    font_path = next((x for x in font_candidates if os.path.exists(x)), None)

    if font_path:
        # Render at a large size first, crop to the exact glyph bounds, then
        # fit that glyph image into a 97% x 90% target box. This guarantees
        # that the visible number—not the font's invisible line metrics—is
        # what fills the photo.
        probe = Image.new('L', (18000, 10000), 0)
        probe_draw = ImageDraw.Draw(probe)
        font = ImageFont.truetype(font_path, 6000)
        bbox = probe_draw.textbbox((0, 0), str(answer), font=font, stroke_width=0)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if tw > 0 and th > 0:
            glyph = Image.new('RGBA', (tw + 20, th + 20), (255, 255, 255, 0))
            glyph_draw = ImageDraw.Draw(glyph)
            glyph_draw.text((10 - bbox[0], 10 - bbox[1]), str(answer), font=font, fill=(0, 0, 0, 255))
            visible = glyph.getchannel('A').getbbox()
            if visible:
                glyph = glyph.crop(visible)

            target_w = int(width * 0.97)
            target_h = int(height * 0.90)
            glyph = glyph.resize((target_w, target_h), Image.Resampling.LANCZOS)

            x = (width - target_w) // 2
            y = (height - target_h) // 2
            im.paste(glyph, (x, y), glyph)

    else:
        # Absolute last fallback for an installation without any supported TTF.
        draw = ImageDraw.Draw(im)
        font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), str(answer), font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (width - tw) / 2 - bbox[0]
        y = (height - th) / 2 - bbox[1]
        draw.text((x, y), str(answer), font=font, fill='black')

    out = BytesIO()
    im.save(out, 'PNG', optimize=True)
    out.seek(0)
    return out

def parse_hhmm(v):
    """Parse owner-entered time in flexible forms.

    Accepted examples: 12, 7, 12:30, 7:05, 1230, 705.
    A bare hour always means minute 00.
    """
    raw = str(v).strip().translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '0123456789' * 2))
    if not raw:
        raise ValueError('time')
    if ':' in raw:
        parts = raw.split(':', 1)
        if not all(part.isdigit() for part in parts):
            raise ValueError('time')
        h, m = int(parts[0]), int(parts[1])
    elif raw.isdigit():
        if len(raw) <= 2:
            h, m = int(raw), 0
        elif len(raw) in (3, 4):
            h, m = int(raw[:-2]), int(raw[-2:])
        else:
            raise ValueError('time')
    else:
        raise ValueError('time')
    if h == 24 and m == 0:
        return 24 * 60
    if not 0 <= h <= 23 or not 0 <= m <= 59:
        raise ValueError('time')
    return h * 60 + m

def iran_weekday(d: date) -> int:
    """Map Python Monday=0 to Persian UI Saturday=0 ... Friday=6."""
    return (d.weekday() + 2) % 7


def schedule_times(cfg, date_value, now=None):
    """Create exactly daily_count evenly spaced send times inside the window.

    On a freshly created/recreated plan for today, times are only generated from
    the current moment forward, so changing settings or re-enabling the feature
    mid-day never dumps old missed events immediately.
    """
    count = max(0, min(MAX_DAILY_COUNT, int(cfg.get('daily_count', 0) or 0)))
    if count <= 0 or iran_weekday(date_value) not in cfg.get('active_days', []):
        return []
    start_minutes = parse_hhmm(cfg.get('start', '10:00'))
    end_minutes = parse_hhmm(cfg.get('end', '23:00'))
    if end_minutes <= start_minutes:
        return []

    start_seconds = float(start_minutes * 60)
    end_seconds = float(end_minutes * 60)
    if now is not None and date_value == now.date():
        current_seconds = (now.hour * 3600) + (now.minute * 60) + now.second + (now.microsecond / 1_000_000)
        if current_seconds > start_seconds:
            start_seconds = current_seconds + 1.0
    if start_seconds >= end_seconds:
        return []

    span = end_seconds - start_seconds
    base = datetime(date_value.year, date_value.month, date_value.day, tzinfo=IRAN_TZ)
    return [
        base + timedelta(seconds=start_seconds + span * ((i + 0.5) / count))
        for i in range(count)
    ]
