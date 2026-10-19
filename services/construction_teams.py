"""Generic Construction Team system shared by every timed upgrade/build operation."""
from __future__ import annotations
import json
from datetime import datetime
from sqlalchemy import select
from database.models import BotSetting, Country

KEY = "construction_teams_config"
MAX_LIMIT = 10


def _default():
    return {
        "max_teams": 10,
        "prices": {str(i): (0 if i == 1 else 0) for i in range(1, MAX_LIMIT + 1)},
        "states": {},
    }


def _load(session):
    row = session.scalar(select(BotSetting).where(BotSetting.key == KEY))
    if row is None:
        cfg = _default()
        row = BotSetting(key=KEY, value=json.dumps(cfg, ensure_ascii=False))
        session.add(row)
        session.flush()
        return cfg, row
    try:
        cfg = json.loads(row.value)
    except Exception:
        cfg = _default()
    if not isinstance(cfg, dict):
        cfg = _default()
    cfg.setdefault("max_teams", 10)
    cfg["max_teams"] = max(1, min(MAX_LIMIT, int(cfg.get("max_teams", 10) or 10)))
    prices = cfg.setdefault("prices", {})
    for i in range(1, MAX_LIMIT + 1):
        prices.setdefault(str(i), 0 if i == 1 else 0)
    prices["1"] = 0
    cfg.setdefault("states", {})
    return cfg, row


def _save(row, cfg):
    row.value = json.dumps(cfg, ensure_ascii=False)


def get_construction_teams_config(session):
    cfg, row = _load(session)
    _save(row, cfg)
    return cfg


def save_construction_teams_config(session, cfg):
    cfg = dict(cfg or {})
    cfg["max_teams"] = max(1, min(MAX_LIMIT, int(cfg.get("max_teams", 10) or 10)))
    prices = cfg.setdefault("prices", {})
    for i in range(1, MAX_LIMIT + 1):
        prices[str(i)] = max(0.0, float(prices.get(str(i), 0) or 0))
    prices["1"] = 0
    cfg.setdefault("states", {})
    _, row = _load(session)
    _save(row, cfg)
    return cfg


def _state(cfg, country_id):
    states = cfg.setdefault("states", {})
    state = states.setdefault(str(int(country_id)), {"purchased": [1], "assignments": []})
    raw_purchased = state.get("purchased", [1])
    if isinstance(raw_purchased, (list, tuple, set)):
        purchased = sorted({max(1, min(MAX_LIMIT, int(x))) for x in raw_purchased})
    else:
        # سازگاری با داده‌های قدیمی که فقط تعداد تیم را نگه می‌داشتند.
        count = max(1, min(MAX_LIMIT, int(raw_purchased or 1)))
        purchased = list(range(1, count + 1))
    if 1 not in purchased:
        purchased.insert(0, 1)
    state["purchased"] = purchased
    state.setdefault("assignments", [])
    if not isinstance(state["assignments"], list):
        state["assignments"] = []
    return state


def _parse_dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def sync_country_teams(session, country, now=None):
    """Release finished assignments and bootstrap assignments from legacy timers."""
    cfg = get_construction_teams_config(session)
    state = _state(cfg, country.id)
    now = now or datetime.utcnow()
    kept=[]
    for a in state["assignments"]:
        until = _parse_dt(a.get("until"))
        if until is None or until <= now:
            continue
        kept.append(a)
    state["assignments"] = kept

    # Bootstrap an existing timed construction after upgrading to this system.
    known = {str(a.get("operation")) for a in kept}
    legacy_buildings = (
        ("command_center", "🏛️ مرکز فرماندهی"),
        ("metal_mine", "⛏️ معدن فلز"),
        ("arsenal", "🏭 زرادخانه"),
        ("bank", "🏦 بانک مرکزی"),
    )
    for building, label in legacy_buildings:
        until = getattr(country, f"{building}_construction_until", None)
        if until and until > now and building not in known:
            slot = _pick_free_slot(cfg, state)
            if slot is not None:
                state["assignments"].append({
                    "slot": slot, "operation": building, "label": label,
                    "started_at": now.isoformat(), "until": until.isoformat(),
                })
                known.add(building)

    prefix=f"missile_tech_construction:{int(country.id)}:"
    for row in session.scalars(select(BotSetting).where(BotSetting.key.like(prefix + "%"))).all():
        try:
            payload=json.loads(row.value or "{}")
            until=_parse_dt(payload.get("until"))
            if until is None or until <= now:
                continue
            missile_id=row.key.split(":",2)[-1]
            operation=f"missile:{missile_id}"
            if operation in known:
                continue
            slot=_pick_free_slot(cfg,state)
            if slot is None:
                break
            state["assignments"].append({
                "slot":slot,
                "operation":operation,
                "label":f"🚀 ارتقای فناوری موشک {missile_id}",
                "started_at":now.isoformat(),
                "until":until.isoformat(),
            })
            known.add(operation)
        except Exception:
            continue

    _save_from_cfg(session, cfg)
    return cfg, state


def _save_from_cfg(session, cfg):
    _, row = _load(session)
    _save(row, cfg)


def _active_slots(cfg, state):
    max_teams = int(cfg.get("max_teams", 10) or 10)
    purchased = {int(x) for x in (state.get("purchased", [1]) or [1])}
    busy = {int(a.get("slot", 0) or 0) for a in state.get("assignments", [])}
    return {slot for slot in purchased if slot <= max_teams} | busy


def _pick_free_slot(cfg, state):
    active = sorted(_active_slots(cfg, state))
    busy = {int(a.get("slot", 0) or 0) for a in state.get("assignments", [])}
    return next((slot for slot in active if slot not in busy), None)


def free_team_exists(session, country, now=None):
    _, state = sync_country_teams(session, country, now)
    cfg = get_construction_teams_config(session)
    return _pick_free_slot(cfg, state) is not None


def reserve_team(session, country, operation, label, until, now=None):
    """Reserve the lowest-numbered free team. Returns slot number or None."""
    now = now or datetime.utcnow()
    cfg, state = sync_country_teams(session, country, now)
    slot = _pick_free_slot(cfg, state)
    if slot is None:
        return None
    state["assignments"].append({
        "slot": int(slot), "operation": str(operation), "label": str(label),
        "started_at": now.isoformat(), "until": until.isoformat() if hasattr(until, "isoformat") else str(until),
    })
    _save_from_cfg(session, cfg)
    return slot


def release_team(session, country, operation):
    cfg, state = sync_country_teams(session, country)
    before=len(state["assignments"])
    state["assignments"]=[a for a in state["assignments"] if str(a.get("operation")) != str(operation)]
    _save_from_cfg(session, cfg)
    return before != len(state["assignments"])


def get_team_status(session, country):
    cfg, state = sync_country_teams(session, country)
    max_teams=int(cfg.get("max_teams",10) or 10)
    purchased_set={int(x) for x in (state.get("purchased", [1]) or [1])}
    purchased=len(purchased_set)
    active_capacity=len([x for x in purchased_set if x <= max_teams])
    assignments=sorted(state.get("assignments", []), key=lambda a:int(a.get("slot",0) or 0))
    busy_active=sum(1 for a in assignments if int(a.get("slot",0) or 0) <= max_teams)
    busy_overflow=[a for a in assignments if int(a.get("slot",0) or 0) > max_teams]
    visible=[]
    active_slots={slot for slot in purchased_set if slot <= max_teams} | {int(a.get("slot",0) or 0) for a in busy_overflow}
    by_slot={int(a.get("slot",0) or 0):a for a in assignments}
    for slot in sorted(active_slots):
        visible.append((slot, by_slot.get(slot)))
    return cfg, state, {
        "max": max_teams,
        "purchased": purchased,
        "active_capacity": active_capacity,
        "busy": busy_active,
        "overflow": busy_overflow,
        "visible": visible,
    }


def team_purchase_quotes(session, country):
    cfg, state, info = get_team_status(session, country)
    purchased=set(int(x) for x in (state.get("purchased", [1]) or [1]))
    max_teams=int(cfg.get("max_teams",10) or 10)
    prices=cfg.get("prices",{}) or {}
    return [
        (team, float(prices.get(str(team), 0) or 0), len(purchased), max_teams)
        for team in range(1, max_teams + 1)
        if team not in purchased
    ]


def team_purchase_quote(session, country):
    """سازگاری با کدهای قدیمی: اولین تیم خریداری‌نشده را برمی‌گرداند."""
    quotes=team_purchase_quotes(session,country)
    return quotes[0] if quotes else None


def buy_team(session, country, team_no):
    team_no=int(team_no)
    cfg,state,info=get_team_status(session,country)
    max_teams=int(cfg.get("max_teams",10) or 10)
    purchased=set(int(x) for x in (state.get("purchased", [1]) or [1]))
    if team_no < 2 or team_no > max_teams:
        return False, "INVALID", None
    if team_no in purchased:
        return False, "OWNED", None
    price=float(cfg.get("prices",{}).get(str(team_no),0) or 0)
    balance=float(country.money or 0)
    if price > 0 and not bool(getattr(country,"infinite_money",False)) and balance < price:
        return False, {"price":price,"balance":balance,"missing":price-balance}, (team_no,price,len(purchased),max_teams)
    if price > 0 and not bool(getattr(country,"infinite_money",False)):
        country.money=balance-price
    state["purchased"]=sorted(purchased | {team_no})
    _save_from_cfg(session,cfg)
    return True, team_no, (team_no,price,len(purchased),max_teams)


def buy_next_team(session, country):
    quote=team_purchase_quote(session,country)
    if quote is None:
        return False, "MAX", None
    return buy_team(session,country,quote[0])


def set_max_teams(session, value):
    value=max(1,min(MAX_LIMIT,int(value)))
    cfg=get_construction_teams_config(session)
    cfg["max_teams"]=value
    save_construction_teams_config(session,cfg)
    return cfg


def set_team_price(session, team_no, price):
    team_no=int(team_no); price=max(0.0,float(price))
    if team_no<=1 or team_no>MAX_LIMIT:
        raise ValueError("invalid team")
    cfg=get_construction_teams_config(session)
    cfg["prices"][str(team_no)]=price
    save_construction_teams_config(session,cfg)
    return cfg


def reset_country_team_state(session, country_id):
    cfg=get_construction_teams_config(session)
    cfg.setdefault("states",{})[str(int(country_id))]={"purchased":[1],"assignments":[]}
    save_construction_teams_config(session,cfg)
