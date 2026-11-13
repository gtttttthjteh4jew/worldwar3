from __future__ import annotations

from datetime import datetime, timedelta
import json

from sqlalchemy import select

from database.models import BotSetting


LEADERSHIP_GROUP_BASE_KEY = "leadership_group_base"
LEADERSHIP_GLOBAL_BASE_KEY = "leadership_global_base"
LEADERSHIP_REPEAT_RESET_HOURS_KEY = "leadership_repeat_reset_hours"

LEADERSHIP_RANKS = [
    (0, "🏳️", "فرماندار"),
    (50, "🎖️", "فرمانده منطقه"),
    (150, "⚔️", "فرمانده میدانی"),
    (300, "🛡️", "فرمانده عالی"),
    (500, "⭐", "ژنرال"),
    (750, "⭐", "ژنرال ارشد"),
    (1050, "⚔️", "فرمانده کل"),
    (1400, "🦅", "مارشال"),
    (1800, "🏛️", "فرمانده عالی‌رتبه"),
    (2250, "👑", "فرمانروا"),
    (2750, "⚜️", "حاکم نظامی"),
    (3300, "🦁", "رهبر عالی"),
    (3900, "⚔️", "فاتح منطقه"),
    (4550, "🌐", "قدرت منطقه‌ای"),
    (5250, "🌍", "قدرت جهانی"),
    (6000, "🦅", "ابرقدرت جهانی"),
    (6800, "🔱", "سلطان جنگ"),
    (7650, "👑", "امیر اعظم"),
    (8550, "🌎", "هژمون"),
    (9500, "👑🌍", "فاتح جهان"),
]

POWER_MULTIPLIERS = (
    (0.50, 0.5),
    (0.75, 0.7),
    (1.00, 0.9),
    (1.25, 1.1),
    (1.50, 1.3),
    (2.00, 1.6),
    (float("inf"), 2.0),
)

WIN_RESULT_MULTIPLIERS = (
    (50, 0.8), (60, 0.9), (70, 1.0), (80, 1.1), (90, 1.2), (100.0001, 1.3)
)
LOSS_MULTIPLIERS = (
    (40, 0.75), (30, 1.0), (20, 1.25), (10, 1.5), (0, 1.75)
)
REPEAT_MULTIPLIERS = (1.0, 0.75, 0.50, 0.25, 0.10)


def leadership_rank(value: float):
    value = max(0.0, float(value or 0))
    current = LEADERSHIP_RANKS[0]
    for rank in LEADERSHIP_RANKS:
        if value >= rank[0]:
            current = rank
        else:
            break
    return current


def leadership_rank_index(value: float) -> int:
    value = max(0.0, float(value or 0))
    idx = 0
    for i, rank in enumerate(LEADERSHIP_RANKS):
        if value >= rank[0]: idx = i
        else: break
    return idx


def leadership_rank_text(value: float) -> str:
    _, emoji, name = leadership_rank(value)
    return f"{emoji} {name}"


def _get_numeric_setting(session, key: str, default: float) -> float:
    row = session.scalar(select(BotSetting).where(BotSetting.key == key))
    if row is None:
        return float(default)
    try:
        return max(0.0, float(row.value))
    except (TypeError, ValueError):
        return float(default)


def _set_numeric_setting(session, key: str, value: float) -> None:
    value = max(0.0, float(value))
    row = session.scalar(select(BotSetting).where(BotSetting.key == key))
    if row is None:
        session.add(BotSetting(key=key, value=str(value)))
    else:
        row.value = str(value)


def get_group_base(session) -> float:
    return _get_numeric_setting(session, LEADERSHIP_GROUP_BASE_KEY, 20.0)


def set_group_base(session, value: float) -> None:
    _set_numeric_setting(session, LEADERSHIP_GROUP_BASE_KEY, value)


def get_global_base(session) -> float:
    return _get_numeric_setting(session, LEADERSHIP_GLOBAL_BASE_KEY, 20.0)


def set_global_base(session, value: float) -> None:
    _set_numeric_setting(session, LEADERSHIP_GLOBAL_BASE_KEY, value)


def get_repeat_reset_hours(session) -> float:
    return _get_numeric_setting(session, LEADERSHIP_REPEAT_RESET_HOURS_KEY, 12.0)


def set_repeat_reset_hours(session, value: float) -> None:
    _set_numeric_setting(session, LEADERSHIP_REPEAT_RESET_HOURS_KEY, value)


def power_multiplier(defender_power: float, attacker_power: float) -> float:
    attacker_power = float(attacker_power or 0)
    defender_power = max(0.0, float(defender_power or 0))
    if attacker_power <= 0:
        ratio = float("inf") if defender_power > 0 else 0.0
    else:
        ratio = defender_power / attacker_power
    if ratio < 0.50: return 0.5
    if ratio < 0.75: return 0.7
    if ratio < 1.00: return 0.9
    if ratio < 1.25: return 1.1
    if ratio < 1.50: return 1.3
    if ratio < 2.00: return 1.6
    return 2.0


def win_result_multiplier(attack_percent: float) -> float:
    p = max(50.0, min(100.0, float(attack_percent or 0)))
    if p < 60: return 0.8
    if p < 70: return 0.9
    if p < 80: return 1.0
    if p < 90: return 1.1
    if p < 100: return 1.2
    return 1.3


def loss_multiplier(attack_percent: float) -> float:
    p = max(0.0, min(49.999999, float(attack_percent or 0)))
    if p >= 40: return 0.75
    if p >= 30: return 1.0
    if p >= 20: return 1.25
    if p >= 10: return 1.5
    return 1.75


def _repeat_key(attacker_country_id: int, defender_country_id: int) -> str:
    a, b = sorted((int(attacker_country_id), int(defender_country_id)))
    return f"leadership_repeat:{a}:{b}"


def get_repeat_count(session, attacker_country_id: int, defender_country_id: int) -> int:
    key = _repeat_key(attacker_country_id, defender_country_id)
    row = session.scalar(select(BotSetting).where(BotSetting.key == key))
    if not row:
        return 0
    try:
        data = json.loads(row.value)
        last = datetime.fromisoformat(str(data.get("last_at")))
        hours = get_repeat_reset_hours(session)
        if hours > 0 and datetime.utcnow() - last >= timedelta(hours=hours):
            row.value = json.dumps({"count": 0, "last_at": datetime.utcnow().isoformat()})
            return 0
        return max(0, int(data.get("count", 0)))
    except Exception:
        return 0


def increment_repeat_count(session, attacker_country_id: int, defender_country_id: int) -> int:
    key = _repeat_key(attacker_country_id, defender_country_id)
    count = get_repeat_count(session, attacker_country_id, defender_country_id) + 1
    value = json.dumps({"count": count, "last_at": datetime.utcnow().isoformat()})
    row = session.scalar(select(BotSetting).where(BotSetting.key == key))
    if row is None:
        session.add(BotSetting(key=key, value=value))
    else:
        row.value = value
    return count


def repeat_multiplier(repeat_number: int) -> float:
    n = max(1, int(repeat_number or 1))
    return REPEAT_MULTIPLIERS[min(n - 1, 4)]


def calculate_battle_leadership(session, attacker_power: float, defender_power: float, attack_percent: float):
    """Return the experience loss/gain before applying the repeat multiplier."""
    base = get_group_base(session)
    pm = power_multiplier(defender_power, attacker_power)
    battle = base * pm
    if float(attack_percent or 0) >= 50:
        result_mult = win_result_multiplier(attack_percent)
    else:
        result_mult = loss_multiplier(attack_percent)
    loss = round(battle * result_mult)
    gain = round(loss * 0.8)
    return {
        "base": base, "power_multiplier": pm, "result_multiplier": result_mult,
        "loss": max(0, loss), "gain": max(0, gain)
    }


def apply_leadership_result(session, attacker_country, defender_country, attack_percent: float):
    """Apply group leadership experience and return a rich result."""
    from services.game import get_military_power
    attacker_power = get_military_power(attacker_country)
    defender_power = get_military_power(defender_country)
    calc = calculate_battle_leadership(session, attacker_power, defender_power, attack_percent)
    repeat_number = increment_repeat_count(session, attacker_country.id, defender_country.id)
    rm = repeat_multiplier(repeat_number)
    loss = int(round(calc["loss"] * rm))
    gain = int(round(loss * 0.8))
    attacker_before = float(getattr(attacker_country, "leadership_experience", 0) or 0)
    defender_before = float(getattr(defender_country, "leadership_experience", 0) or 0)
    attacker_won = float(attack_percent or 0) >= 50
    if attacker_won:
        attacker_after = attacker_before + gain
        defender_after = max(0.0, defender_before - loss)
    else:
        attacker_after = max(0.0, attacker_before - loss)
        defender_after = defender_before + gain
    attacker_country.leadership_experience = attacker_after
    defender_country.leadership_experience = defender_after
    return {
        **calc, "repeat_number": repeat_number, "repeat_multiplier": rm,
        "loss": loss, "gain": gain, "attacker_won": attacker_won,
        "attacker_before": attacker_before, "attacker_after": attacker_after,
        "defender_before": defender_before, "defender_after": defender_after,
        "attacker_rank_before": leadership_rank(attacker_before),
        "attacker_rank_after": leadership_rank(attacker_after),
        "defender_rank_before": leadership_rank(defender_before),
        "defender_rank_after": leadership_rank(defender_after),
    }
