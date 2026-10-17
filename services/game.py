import json
import math
from datetime import datetime, timedelta
from database.models import BotSetting

from sqlalchemy import select

from database.models import Country, User, UserCountry, BankAccount
from services.economy import get_arsenal_config, get_initial_resources, get_hq_config
from services.leadership import leadership_rank_text


def get_or_create_user(session, telegram_user, referrer_user_id=None):
    user = session.scalar(
        select(User).where(User.telegram_id == telegram_user.id)
    )

    if user is None:
        user = User(
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            first_name=telegram_user.first_name,
        )
        session.add(user)
        if referrer_user_id and int(referrer_user_id) != int(telegram_user.id):
            referrer = session.scalar(select(User).where(User.telegram_id == int(referrer_user_id)))
            if referrer is not None and referrer.id != user.id:
                # Store Telegram ID as the durable referral key, matching the User model.
                user.referrer_user_id = int(referrer.telegram_id)
                user.referred_at = datetime.utcnow()
        session.flush()
    else:
        # Telegram is the source of truth for the live identity. Every interaction
        # refreshes the cached username/name so old values do not remain in panels,
        # searches or leaderboards.
        user.username = telegram_user.username
        user.first_name = telegram_user.first_name

    # Keep every country led by this account synchronized with the current Telegram name.
    live_name = getattr(telegram_user, "full_name", None) or telegram_user.first_name or user.username or "رهبر"
    for country in session.scalars(select(Country).where(Country.leader_user_id == telegram_user.id)).all():
        country.leader_name = live_name

    user.last_active_at = datetime.utcnow()
    return user


def get_countries_by_continent(session, chat_id):
    return list(session.scalars(
        select(Country).where(Country.chat_id == chat_id).order_by(Country.title)
    ).all())


def get_user_country_in_continent(session, user, chat_id):
    # There should be one country per user in a group. Limit defensively so a
    # legacy duplicate cannot crash every group interaction with MultipleResultsFound.
    return session.scalar(
        select(Country)
        .join(UserCountry, UserCountry.country_id == Country.id)
        .where(
            Country.chat_id == chat_id,
            UserCountry.user_id == user.id,
        )
        .order_by(Country.id.asc())
        .limit(1)
    )


def get_country_by_name(session, country_name):
    normalized = country_name.strip().casefold()
    countries = session.scalars(select(Country)).all()
    for country in countries:
        if country.title.strip().casefold() == normalized:
            return country
    return None


def normalize_country_name(name: str) -> str:
    return " ".join(name.strip().split())


def create_country(session, chat, country_name, leader_user):
    country_name = normalize_country_name(country_name)

    if get_country_by_name(session, country_name) is not None:
        return None

    leader_name = leader_user.full_name or leader_user.first_name or "رهبر"

    country = Country(
        chat_id=chat.id,
        title=country_name,
        continent_name=getattr(chat, "title", None) or "بدون نام",
        chat_type=chat.type,
        leader_user_id=leader_user.id,
        leader_name=leader_name,
    )
    initial = get_initial_resources(session)
    country.money = initial["money"]
    country.fuel = initial["fuel"]
    country.metal = initial["metal"]
    country.uranium = initial["uranium"]
    country.command_center_level = 0

    session.add(country)
    session.flush()
    # هر کشور از ابتدا یک میلیون شهروند دارد؛ این مقدار مستقل از سطح بانک است.
    session.add(BankAccount(country_id=country.id, citizens=1_000_000))
    session.flush()

    return country

def register_user_in_country(session, user, country):
    relation = session.scalar(
        select(UserCountry).where(
            UserCountry.user_id == user.id,
            UserCountry.country_id == country.id,
        )
    )

    if relation is None:
        relation = UserCountry(
            user_id=user.id,
            country_id=country.id,
        )
        session.add(relation)
        session.flush()

    return relation


def get_user_countries(session, user):
    stmt = (
        select(Country)
        .join(UserCountry, UserCountry.country_id == Country.id)
        .where(UserCountry.user_id == user.id)
        .order_by(Country.title)
    )
    return list(session.scalars(stmt).all())


def set_default_country(session, user, country_id):
    country = session.scalar(
        select(Country)
        .join(UserCountry, UserCountry.country_id == Country.id)
        .where(
            Country.id == country_id,
            UserCountry.user_id == user.id,
        )
    )

    if country is None:
        return False

    user.default_country_id = country.id
    return True


def get_default_country(session, user):
    if user.default_country_id is None:
        return None

    return session.scalar(
        select(Country).where(Country.id == user.default_country_id)
    )


def get_context_country(session, user, chat_id=None):
    """Resolve the user's country for the current chat, falling back to default in private chats.

    Group game buttons must always operate on the country the user owns in that
    group instead of a possibly unrelated private/default country.
    """
    try:
        if chat_id is not None and int(chat_id) < 0:
            # In a group never fall back to a private/default country from another
            # group. A missing country here must remain missing.
            return get_user_country_in_continent(session, user, int(chat_id))
    except Exception:
        return None
    return get_default_country(session, user)


def get_military_power(country, config=None, arsenal_config=None):
    total = 0.0
    try:
        # config may be a composite payload supplied by /start so all building
        # configurations used by the power calculation are the current OWNER settings.
        hcfg = (config.get("hq") if isinstance(config, dict) and isinstance(config.get("hq"), dict) else _hq_cfg(config))
        mcfg = (config.get("metal_mine") if isinstance(config, dict) and isinstance(config.get("metal_mine"), dict) else _mine_config(config))
        if getattr(country, "command_center_level", 0):
            hlevel = int(country.command_center_level)
            # قدرت نظامی مرکز فرماندهی تجمعی است: قدرت هر سطح از ۱ تا سطح فعلی
            # باید با هم جمع شود، نه اینکه فقط قدرت سطح فعلی در نظر گرفته شود.
            for level in range(1, hlevel + 1):
                hdata = hq_level_data(level, hcfg) or {}
                total += float(hdata.get("military_power", 0.0) or 0.0)
        if getattr(country, "metal_mine_level", 0):
            cfg = mcfg
            total += float(cfg.get("build_military_power", 0.0))
            for level in range(2, int(country.metal_mine_level) + 1):
                total += float((cfg.get("levels", {}).get(level) or {}).get("military_power", 0.0))
        if arsenal_config is not None and getattr(country, "arsenal_level", 0):
            total += float(arsenal_config.get("build_military_power", 0.0))
            for level in range(2, int(country.arsenal_level) + 1):
                total += float((arsenal_config.get("levels", {}).get(level) or {}).get("military_power", 0.0))
    except (TypeError, ValueError):
        pass
    return total

def is_infinite(country, resource):
    return bool(getattr(country, f"infinite_{resource}", False))

def resource_available(country, resource, amount):
    return is_infinite(country, resource) or float(getattr(country, resource)) >= float(amount)

def spend_resource(country, resource, amount):
    if is_infinite(country, resource):
        return
    setattr(country, resource, float(getattr(country, resource)) - float(amount))

def add_resource(country, resource, amount):
    if is_infinite(country, resource):
        return
    setattr(country, resource, float(getattr(country, resource)) + float(amount))

def country_status(country, config=None, arsenal_config=None, shield_status=None, include_identity=True):
    # وضعیت مرکز فرماندهی را از وضعیت ساخت/ارتقای واقعی کشور می‌خوانیم.
    hq_level = int(getattr(country, "command_center_level", 0) or 0)
    hq_remaining, hq_target = construction_remaining(country, "command_center")
    if hq_remaining > 0:
        target_level = abs(int(hq_target or 0))
        if hq_level <= 0 and target_level <= 1:
            hq_status = "🏗️ در حال ساخت"
        elif target_level > hq_level:
            hq_status = f"⬆️ در حال ارتقا به سطح {target_level}"
        else:
            hq_status = "🏗️ در حال ساخت"
    else:
        hq_status = "ساخته نشده" if hq_level <= 0 else f"سطح {hq_level}"

    identity = (
        f"🌍 قاره: <b>{getattr(country, 'continent_name', None) or 'بدون نام'}</b>\n"
        f"🏳️ کشور: <b>{country.title}</b>\n"
        f"👑 رهبر کشور: <b>{country.leader_name}</b>\n"
    ) if include_identity else ""
    return (
        identity +
        f"🪖 قدرت نظامی: <b>{get_military_power(country, config, arsenal_config):,.0f}</b>\n"
        f"👑 سطح تجربه رهبری: <b>{leadership_rank_text(getattr(country, 'leadership_experience', 0))}</b>\n"
        f"🎖️ تجربه رهبری: <b>{float(getattr(country, 'leadership_experience', 0) or 0):,.0f}</b>\n\n"
        f"🏗️ <b>ساختمان‌ها</b>\n"
        f"🏛️ مرکز فرماندهی: <b>{hq_status}</b>\n"
        f"🏭 زرادخانه: {('<b>سطح ' + str(country.arsenal_level) + '</b>') if getattr(country, 'arsenal_level', 0) else '<b>ساخته نشده</b>'}\n"
        f"⛏️ معدن فلز: {('<b>سطح ' + str(country.metal_mine_level) + '</b>') if country.metal_mine_level else '<b>ساخته نشده</b>'}\n"
        f"🏦 بانک: {('<b>سطح ' + str(country.bank_level) + '</b>') if country.bank_level else '<b>ساخته نشده</b>'}\n"
        + (f"\n🛡️ سپر قاره‌ای: <b>{shield_status.get('continental')}</b>\n🛡️ سپر جهانی: <b>{shield_status.get('global')}</b>\n" if isinstance(shield_status, dict) else '\n')
        + f"\n💸 <b>سرمایه</b>\n"
        + f"💰 پول: {'♾️' if country.infinite_money else f'<b>{country.money:,.0f}</b>'} | 🔩 فلز: {'♾️' if country.infinite_metal else f'<b>{country.metal:,.0f}</b>'}\n"
        + f"⛽ سوخت: {'♾️' if country.infinite_fuel else f'<b>{country.fuel:,.2f}</b>'} | ☢️ اورانیوم: {'♾️' if country.infinite_uranium else f'<b>{country.uranium:,.2f}</b>'}"
    )


# هزینه و تنظیمات مرکز فرماندهی از پنل Owner خوانده می‌شود.
DEFAULT_HQ_UPGRADE_COSTS = {2: {"money":0.0,"metal":0.0,"fuel":0.0,"uranium":0.0,"strength":0.0}}

def _hq_cfg(config=None):
    if isinstance(config, dict) and "levels" in config: return config
    return {"max_level":100,"build_cost":{"money":0.0,"metal":0.0,"fuel":0.0,"uranium":0.0},"build_strength":0.0,"levels":{2:dict(DEFAULT_HQ_UPGRADE_COSTS[2])}}

def hq_build_cost(config=None):
    cfg=_hq_cfg(config)
    return {k:float(cfg.get("build_cost",{}).get(k,0.0)) for k in ("money","metal","fuel","uranium")}

def hq_upgrade_cost(current_level:int, config=None):
    cfg=_hq_cfg(config); data=cfg.get("levels",{}).get(current_level+1)
    if not data: return None
    return {k:float(data.get(k,0.0)) for k in ("money","metal","fuel","uranium")}

def _hours_to_timedelta(hours):
    try:
        return timedelta(hours=max(0.0, float(hours)))
    except (TypeError, ValueError):
        return timedelta(0)

def _construction_fields(building):
    return (f"{building}_construction_until", f"{building}_construction_target_level")

def construction_remaining(country, building, now=None):
    now = now or datetime.utcnow()
    until_field, target_field = _construction_fields(building)
    until = getattr(country, until_field, None)
    if not until:
        return 0.0, None
    remaining = (until - now).total_seconds()
    if remaining <= 0:
        return 0.0, int(getattr(country, target_field, 0) or 0)
    return remaining, int(getattr(country, target_field, 0) or 0)

def finalize_construction(country, now=None, session=None):
    now = now or datetime.utcnow()
    completed = []
    for building, level_field, storage_reset in (
        ("command_center", "command_center_level", False),
        ("metal_mine", "metal_mine_level", True),
        ("arsenal", "arsenal_level", True),
        ("bank", "bank_level", False),
    ):
        until_field, target_field = _construction_fields(building)
        until = getattr(country, until_field, None)
        target = getattr(country, target_field, None)
        if until and target is not None and until <= now:
            final_target = abs(int(target))
            setattr(country, level_field, final_target)
            if storage_reset:
                setattr(country, "metal_mine_storage" if building == "metal_mine" else "arsenal_storage", 0.0)
                if building == "metal_mine":
                    country.metal_mine_last_production_at = now
            setattr(country, until_field, None)
            setattr(country, target_field, None)
            completed.append(building)
            if session is not None:
                try:
                    from services.construction_teams import release_team
                    release_team(session, country, building)
                except Exception:
                    pass
    return completed

def start_construction(country, building, target_level, hours, storage_reset=False):
    until_field, target_field = _construction_fields(building)
    now = datetime.utcnow()
    remaining, _ = construction_remaining(country, building, now)
    if remaining > 0:
        return False
    hours = max(0.0, float(hours or 0.0))
    if hours <= 0:
        setattr(country, target_field, int(target_level))
        setattr(country, until_field, now)
        finalize_construction(country, now)
        return True
    setattr(country, target_field, int(target_level))
    setattr(country, until_field, now + _hours_to_timedelta(hours))
    return True

def construction_label(country, building):
    remaining, _ = construction_remaining(country, building)
    if remaining <= 0:
        return None
    total_hours = remaining / 3600.0
    return f"⏳ زمان تکمیل: <b>{total_hours:,.0f} ساعت</b>"

def _cumulative_military_power(level: int, config=None, building: str = "hq") -> float:
    """Return total military power accumulated from level 1 through level."""
    level = max(0, int(level or 0))
    if level <= 0:
        return 0.0
    if building == "hq":
        cfg = _hq_cfg(config)
        total = float(cfg.get("build_military_power", 0.0) or 0.0)
        for lv in range(2, level + 1):
            total += float((cfg.get("levels", {}).get(lv) or {}).get("military_power", 0.0) or 0.0)
        return total
    if building == "arsenal":
        cfg = config or {}
        total = float(cfg.get("build_military_power", 0.0) or 0.0)
        for lv in range(2, level + 1):
            total += float((cfg.get("levels", {}).get(lv) or {}).get("military_power", 0.0) or 0.0)
        return total
    if building == "metal_mine":
        cfg = _mine_config(config)
        total = float(cfg.get("build_military_power", 0.0) or 0.0)
        for lv in range(2, level + 1):
            total += float((cfg.get("levels", {}).get(lv) or {}).get("military_power", 0.0) or 0.0)
        return total
    return 0.0

def hq_level_data(level:int, config=None):
    cfg=_hq_cfg(config)
    if level == 1: return {"money":0.0,"metal":0.0,"fuel":0.0,"uranium":0.0,"strength":float(cfg.get("build_strength",0.0)),"military_power":float(cfg.get("build_military_power",0.0))}
    return cfg.get("levels",{}).get(level)

def _hq_payment_cost(cost, payment="normal"):
    cost = dict(cost or {})
    if payment == "uranium":
        return {"uranium": float(cost.get("uranium", 0.0))}
    return {k: float(v) for k, v in cost.items() if k in {"money","metal","fuel"}}

def can_build_hq(country, config=None, payment="normal"):
    finalize_construction(country)
    if construction_remaining(country, "command_center")[0] > 0: return False,"IN_PROGRESS"
    if int(country.command_center_level)>0: return False,"ALREADY_BUILT"
    missing={}
    for r,a in _hq_payment_cost(hq_build_cost(config), payment).items():
        if not resource_available(country,r,a): missing[r]=max(0.0,float(a)-float(getattr(country,r,0.0)))
    return len(missing)==0,missing

def start_hq_construction(country, target_level, hours, payment="normal"):
    """Start HQ construction and remember payment mode without requiring a DB migration.
    Positive target = normal resources; negative target = uranium payment.
    """
    encoded_target = -abs(int(target_level)) if payment == "uranium" else abs(int(target_level))
    return start_construction(country, "command_center", encoded_target, hours)

def hq_instant_finish_uranium_cost(country, config=None):
    """Uranium required to finish the active HQ construction immediately.
    Rate is configured by OWNER as uranium per hour. Cost is rounded up to cents.
    """
    remaining, _ = construction_remaining(country, "command_center")
    if remaining <= 0:
        return 0.0
    cfg = _hq_cfg(config)
    rate = max(0.0, float(cfg.get("instant_finish_uranium_per_hour", 0.0) or 0.0))
    if rate <= 0:
        return 0.0
    return math.ceil((remaining / 3600.0) * rate * 100.0) / 100.0

def finish_hq_construction_now(country, config=None, session=None):
    """Instantly complete an active HQ build/upgrade by paying uranium."""
    remaining, encoded_target = construction_remaining(country, "command_center")
    if remaining <= 0 or not encoded_target:
        return False, "NOT_IN_PROGRESS"
    cost = hq_instant_finish_uranium_cost(country, config)
    if cost <= 0:
        return False, "DISABLED"
    if not resource_available(country, "uranium", cost):
        return False, cost
    spend_resource(country, "uranium", cost)
    until_field, target_field = _construction_fields("command_center")
    target = abs(int(encoded_target))
    country.command_center_level = target
    setattr(country, until_field, None)
    setattr(country, target_field, None)
    if session is not None:
        from services.construction_teams import release_team
        release_team(session, country, "command_center")
    return True, cost

def cancel_hq_construction(country, config=None, session=None):
    """Cancel active HQ build/upgrade and refund 50% of the resources originally spent."""
    remaining, encoded_target = construction_remaining(country, "command_center")
    if remaining <= 0 or not encoded_target:
        return False, "NOT_IN_PROGRESS"
    target = abs(int(encoded_target))
    payment = "uranium" if int(encoded_target) < 0 else "normal"
    if target == 1 and int(country.command_center_level) <= 0:
        cost = hq_build_cost(config)
    else:
        current = int(country.command_center_level)
        cost = hq_upgrade_cost(current, config) or {}
    refund = _hq_payment_cost(cost, payment)
    for resource, amount in refund.items():
        add_resource(country, resource, float(amount) * 0.5)
    until_field, target_field = _construction_fields("command_center")
    setattr(country, until_field, None)
    setattr(country, target_field, None)
    if session is not None:
        from services.construction_teams import release_team
        release_team(session, country, "command_center")
    return True, refund

def build_hq(country, config=None, payment="normal", session=None):
    ok,res=can_build_hq(country,config,payment)
    if not ok: return False,res
    target=1
    hours=float(_hq_cfg(config).get("build_completion_time",0) or 0)
    if session is not None and hours > 0:
        from services.construction_teams import reserve_team
        if reserve_team(session,country,"command_center",f"🏛️ ارتقای مرکز فرماندهی به سطح {target}",datetime.utcnow()+timedelta(hours=hours)) is None:
            return False,"NO_TEAM"
    for r,a in _hq_payment_cost(hq_build_cost(config), payment).items(): spend_resource(country,r,a)
    start_hq_construction(country, target, hours, payment)
    return True, "IN_PROGRESS" if construction_remaining(country,"command_center")[0] > 0 else target

def hq_info(country, config=None):
    finalize_construction(country)
    cfg=_hq_cfg(config); level=int(country.command_center_level)
    labels={"money":"💰 پول","metal":"🔩 فلز","fuel":"⛽ سوخت","uranium":"☢️ اورانیوم"}

    # اگر مرکز فرماندهی در حال ساخت/ارتقاست، وضعیت فعلی و مشخصات سطح هدف را نشان بده؛
    # هزینه ساخت/ارتقا در این حالت نمایش داده نشود.
    remaining, target_level = construction_remaining(country, "command_center")
    if remaining > 0:
        target_level = abs(int(target_level or (1 if level <= 0 else level + 1)))
        if target_level == 1 and level <= 0:
            military_power = _cumulative_military_power(1, cfg, "hq")
            strength = float(cfg.get("build_strength", 0))
            completion_hours = float(cfg.get("build_completion_time", 0))
            state = "🏗️ <b>در حال ساخت</b>"
        else:
            data = hq_level_data(target_level, cfg) or {}
            military_power = _cumulative_military_power(target_level, cfg, "hq")
            strength = float(data.get("strength", 0))
            completion_hours = float(data.get("completion_time", 0))
            state = "⬆️ <b>در حال ارتقا</b>"
        remaining_hours = remaining / 3600.0
        return (f"🏛️ <b>مرکز فرماندهی {country.title}</b>\n\n"
                f"{state}\n"
                f"📋 <b>مشخصات سطح {target_level}</b>\n"
                f"🪖 قدرت نظامی: <b>{military_power:,.0f}</b>\n"
                f"🛡️ استحکام: <b>{strength:,.0f}</b>\n"
                f"⏱️ زمان تکمیل: <b>{completion_hours:,.0f} ساعت</b>\n"
                f"⏳ زمان باقی‌مانده: <b>{remaining_hours:,.0f} ساعت</b>")

    if level<=0:
        return f"🏛️ <b>مرکز فرماندهی {country.title}</b>\n\n📊 وضعیت: <b>ساخته نشده</b>"
    data=hq_level_data(level,cfg) or {}
    text=(f"🏛️ <b>مرکز فرماندهی {country.title}</b>\n\n"
          f"📊 سطح فعلی: <b>{level}</b>\n"
          f"🪖 قدرت نظامی: <b>{_cumulative_military_power(level, cfg, 'hq'):,.0f}</b>\n"
          f"🛡️ استحکام: <b>{float(data.get('strength',0)):,.0f}</b>\n")
    if level >= int(cfg.get('max_level',100)) or hq_level_data(level+1,cfg) is None:
        return text+"\n🏆 <b>به حداکثر سطح رسیدید.</b>"
    nd=hq_level_data(level+1,cfg) or {}; cost=hq_upgrade_cost(level,cfg) or {}
    shown=[
        f"💰 پول: <b>{float(cost.get('money',0) or 0):,.2f}</b>",
        f"🔩 فلز: <b>{float(cost.get('metal',0) or 0):,.2f}</b>",
        f"⛽ سوخت: <b>{float(cost.get('fuel',0) or 0):,.2f}</b>",
        f"☢️ اورانیوم: <b>{float(cost.get('uranium',0) or 0):,.2f}</b>",
    ]
    return (text+f"\n⬆️ <b>سطح بعدی: {level+1}</b>\n"
            f"🪖 قدرت نظامی: <b>{_cumulative_military_power(level+1, cfg, 'hq'):,.0f}</b>\n"
            f"🛡️ استحکام: <b>{float(nd.get('strength',0)):,.0f}</b>\n"
            f"⏱️ زمان تکمیل: <b>{float(nd.get('completion_time',0)):,.0f} ساعت</b>\n"
            "💰 <b>هزینه‌ها:</b>\n"+"\n".join(shown))

def can_upgrade_hq(country, config=None, payment="normal"):
    finalize_construction(country)
    if construction_remaining(country, "command_center")[0] > 0: return False,"IN_PROGRESS"
    cfg=_hq_cfg(config); level=int(country.command_center_level)
    if level<=0: return False,"NOT_BUILT"
    if level>=int(cfg.get("max_level",100)) or hq_upgrade_cost(level,cfg) is None: return False,"MAX_LEVEL"
    cost=_hq_payment_cost(hq_upgrade_cost(level,cfg), payment); missing={}
    for r,a in cost.items():
        if not resource_available(country,r,a): missing[r]=max(0.0,float(a)-float(getattr(country,r,0.0)))
    return len(missing)==0,missing

def upgrade_hq(country, config=None, payment="normal", session=None):
    ok,res=can_upgrade_hq(country,config,payment)
    if not ok: return False,res
    target=country.command_center_level + 1
    nd=(_hq_cfg(config).get("levels",{}).get(target) or {})
    hours=float(nd.get("completion_time",0) or 0)
    if session is not None and hours > 0:
        from services.construction_teams import reserve_team
        if reserve_team(session,country,"command_center",f"🏛️ ارتقای مرکز فرماندهی به سطح {target}",datetime.utcnow()+timedelta(hours=hours)) is None:
            return False,"NO_TEAM"
    for resource,amount in _hq_payment_cost(hq_upgrade_cost(country.command_center_level,config), payment).items():
        spend_resource(country,resource,amount)
    start_hq_construction(country, target, hours, payment)
    return True, "IN_PROGRESS" if construction_remaining(country,"command_center")[0] > 0 else target

def _mine_config(config=None):
    if config is None:
        # Standalone military-power callers may omit Owner config. Use the
        # normalized economy defaults instead of undefined legacy constants.
        from services.economy import DEFAULT_METAL_MINE, _normalize
        return _normalize(DEFAULT_METAL_MINE)
    return config


METAL_MINE_LEVEL_1 = {
    "active": True,
    "production_per_hour": 100.0,
    "storage_capacity": 500.0,
    "money": 0.0,
    "metal": 0.0,
    "fuel": 0.0,
}

def _metal_mine_level_data(level: int, config=None):
    if level == 1:
        cfg = _mine_config(config)
        return {
            **METAL_MINE_LEVEL_1,
            "production_per_hour": float(cfg.get("build_production_per_hour", METAL_MINE_LEVEL_1["production_per_hour"])),
            "storage_capacity": float(cfg.get("build_storage_capacity", METAL_MINE_LEVEL_1["storage_capacity"])),
            "strength": float(cfg.get("build_strength", 0.0)),
            "military_power": float(cfg.get("build_military_power", 0.0)),
        }
    return _mine_config(config)["levels"].get(level)


def accrue_metal_mine(country, now=None, config=None):
    if country.metal_mine_level <= 0:
        country.metal_mine_last_production_at = now or datetime.utcnow()
        return 0.0
    data = _metal_mine_level_data(country.metal_mine_level, config)
    if data is None:
        return 0.0
    now = now or datetime.utcnow()
    last = country.metal_mine_last_production_at or now
    if now <= last:
        return 0.0
    rate_per_hour = float(data["production_per_hour"])
    capacity = float(data["storage_capacity"])
    elapsed_seconds = (now - last).total_seconds()
    produced = elapsed_seconds * rate_per_hour / 3600.0
    if produced <= 0:
        return 0.0
    current = float(country.metal_mine_storage or 0.0)
    free_space = max(0.0, capacity - current)
    added = min(produced, free_space)
    country.metal_mine_storage = min(capacity, current + added)
    country.metal_mine_last_production_at = now
    return added


def metal_mine_upgrade_cost(level: int, config=None, payment="normal"):
    data = _metal_mine_level_data(level + 1, config)
    if data is None or level <= 0:
        return None
    if payment == "uranium":
        return {"uranium": float(data.get("uranium", 0.0))}
    return {k: float(data.get(k, 0.0)) for k in ("money", "metal", "fuel")}


def can_upgrade_metal_mine(country, config=None, payment="normal"):
    finalize_construction(country)
    if construction_remaining(country, "metal_mine")[0] > 0: return False,"IN_PROGRESS"
    if country.metal_mine_level <= 0:
        return False, "NOT_BUILT"
    cfg=_mine_config(config); next_level=country.metal_mine_level+1
    req=int((cfg.get("levels",{}).get(next_level) or {}).get("required_hq_level", next_level))
    if int(country.command_center_level) < req: return False, "HQ_REQUIRED"
    next_level = country.metal_mine_level + 1
    max_level = int(_mine_config(config).get("max_level", 100))
    if next_level > max_level:
        return False, "MAX_LEVEL"
    data = _metal_mine_level_data(next_level, config)
    if data is None or not bool(data.get("active", True)):
        return False, "MAX_LEVEL"
    cost = metal_mine_upgrade_cost(country.metal_mine_level, config, payment)
    if cost is None:
        return False, "MAX_LEVEL"
    missing = {}
    for resource, amount in cost.items():
        if not resource_available(country, resource, amount):
            current = float(getattr(country, resource, 0.0))
            missing[resource] = max(0.0, float(amount) - current)
    # True means the upgrade exists and should be shown even when resources are insufficient.
    return True, missing

def upgrade_metal_mine(country, config=None, payment="normal", session=None):
    accrue_metal_mine(country, config=config)
    can_upgrade, result = can_upgrade_metal_mine(country, config, payment)
    if not can_upgrade:
        return False, result
    if isinstance(result, dict) and result:
        return False, result
    cost = metal_mine_upgrade_cost(country.metal_mine_level, config, payment)
    target=country.metal_mine_level + 1
    nd=_metal_mine_level_data(target, config) or {}
    hours=float(nd.get("completion_time",0) or 0)
    if session is not None and hours > 0:
        from services.construction_teams import reserve_team
        if reserve_team(session,country,"metal_mine",f"⛏️ ارتقای معدن فلز به سطح {target}",datetime.utcnow()+timedelta(hours=hours)) is None:
            return False,"NO_TEAM"
    for resource, amount in cost.items():
        spend_resource(country, resource, amount)
    start_construction(country, "metal_mine", (-abs(int(target)) if payment == "uranium" else abs(int(target))), hours, storage_reset=True)
    return True, "IN_PROGRESS" if construction_remaining(country,"metal_mine")[0] > 0 else target

def metal_mine_instant_finish_uranium_cost(country, config=None):
    """Uranium needed to finish an active metal-mine build/upgrade immediately."""
    remaining, _ = construction_remaining(country, "metal_mine")
    if remaining <= 0:
        return 0.0
    cfg = _mine_config(config)
    rate = max(0.0, float(cfg.get("instant_finish_uranium_per_hour", 0.0) or 0.0))
    if rate <= 0:
        return 0.0
    return math.ceil((remaining / 3600.0) * rate * 100.0) / 100.0

def finish_metal_mine_construction_now(country, config=None, session=None):
    remaining, encoded_target = construction_remaining(country, "metal_mine")
    if remaining <= 0 or not encoded_target:
        return False, "NOT_IN_PROGRESS"
    cost = metal_mine_instant_finish_uranium_cost(country, config)
    if cost <= 0:
        return False, "DISABLED"
    if not resource_available(country, "uranium", cost):
        return False, cost
    spend_resource(country, "uranium", cost)
    until_field, target_field = _construction_fields("metal_mine")
    target = abs(int(encoded_target))
    country.metal_mine_level = target
    setattr(country, until_field, None)
    setattr(country, target_field, None)
    country.metal_mine_storage = 0.0
    country.metal_mine_last_production_at = datetime.utcnow()
    if session is not None:
        from services.construction_teams import release_team
        release_team(session, country, "metal_mine")
    return True, cost

def cancel_metal_mine_construction(country, config=None, session=None):
    remaining, encoded_target = construction_remaining(country, "metal_mine")
    if remaining <= 0 or not encoded_target:
        return False, "NOT_IN_PROGRESS"
    target = abs(int(encoded_target))
    payment = "uranium" if int(encoded_target) < 0 else "normal"
    if target == 1 and int(country.metal_mine_level) <= 0:
        cfg = _mine_config(config)
        cost = dict(cfg.get("build_cost", {}) or {})
        if payment == "uranium":
            cost = {"uranium": _metal_mine_build_uranium_cost(config)}
        else:
            cost = {k: float(cost.get(k, 0.0)) for k in ("money", "metal", "fuel")}
    else:
        current = int(country.metal_mine_level)
        cost = metal_mine_upgrade_cost(current, config, payment) or {}
    for resource, amount in cost.items():
        add_resource(country, resource, float(amount) * 0.5)
    until_field, target_field = _construction_fields("metal_mine")
    setattr(country, until_field, None)
    setattr(country, target_field, None)
    if session is not None:
        from services.construction_teams import release_team
        release_team(session, country, "metal_mine")
    return True, {k: float(v) * 0.5 for k, v in cost.items()}

def collect_metal_mine(country, config=None):
    accrue_metal_mine(country, config=config)
    storage = float(country.metal_mine_storage or 0.0)
    amount = storage
    if amount <= 0:
        return 0.0
    country.metal_mine_storage = 0.0
    add_resource(country, "metal", amount)
    return amount


def metal_mine_info(country, config=None):
    finalize_construction(country)
    accrue_metal_mine(country, config=config)
    remaining, target_level = construction_remaining(country, "metal_mine")
    if remaining > 0:
        cfg = _mine_config(config)
        target_level = abs(int(target_level or (1 if country.metal_mine_level <= 0 else country.metal_mine_level + 1)))
        if target_level == 1 and country.metal_mine_level <= 0:
            data = {
                "strength": float(cfg.get("build_strength", 0.0)),
                "production_per_hour": float(cfg.get("build_production_per_hour", 0.0)),
                "storage_capacity": float(cfg.get("build_storage_capacity", 0.0)),
                "completion_time": float(cfg.get("build_completion_time", 0.0)),
            }
            state = "🏗️ <b>در حال ساخت</b>"
        else:
            data = _metal_mine_level_data(target_level, config) or {}
            state = "⬆️ <b>در حال ارتقا</b>"
        return (f"⛏️ <b>معدن فلز {country.title}</b>\n\n"
                f"{state}\n"
                f"📋 <b>مشخصات سطح {target_level}</b>\n"
                f"🪖 قدرت نظامی: <b>{_cumulative_military_power(target_level, config, 'metal_mine'):,.0f}</b>\n"
                f"🛡️ استحکام: <b>{float(data.get('strength', 0)):,.0f}</b>\n"
                f"⚙️ تولید در ساعت: <b>{float(data.get('production_per_hour', 0)):,.0f}</b> فلز\n"
                f"⏱️ زمان تکمیل: <b>{float(data.get('completion_time', 0)):,.0f} ساعت</b>\n"
                f"⏳ زمان باقی‌مانده: <b>{remaining/3600.0:,.0f} ساعت</b>\n"
                f"📦 ظرفیت مخزن: <b>{float(data.get('storage_capacity', 0)):,.0f}</b>")

    if country.metal_mine_level <= 0:
        return f"⛏️ <b>معدن فلز {country.title}</b>\n\n📊 وضعیت: <b>ساخته نشده</b>"
    if country.metal_mine_level > 0:
        data = _metal_mine_level_data(country.metal_mine_level, config)
        cost = metal_mine_upgrade_cost(country.metal_mine_level, config)
        capacity = data["storage_capacity"]
        storage = min(float(country.metal_mine_storage or 0.0), float(capacity))
        percent = int((storage / capacity) * 100) if capacity else 0
        filled = min(10, int(round(percent / 10)))
        storage_bar = "🟩" * filled + "⬜" * (10 - filled)
        text = (
            f"⛏️ <b>معدن فلز {country.title}</b>\n\n"
            f"📊 سطح فعلی: <b>{country.metal_mine_level}</b>\n"
            + ((construction_label(country, "metal_mine") + "\n") if construction_label(country, "metal_mine") else "")
            + f"🪖 قدرت نظامی: <b>{_cumulative_military_power(country.metal_mine_level, config, 'metal_mine'):,.0f}</b>\n"
            f"🛡️ استحکام: <b>{(float(_mine_config(config).get('build_strength', 0.0)) if country.metal_mine_level == 1 else float(data.get('strength', 0.0))):,.0f}</b>\n"
            f"⚙️ تولید در ساعت: <b>{data['production_per_hour']:,.0f}</b> فلز\n"
            f"⏱️ تولید در هر ثانیه: <b>{data['production_per_hour'] / 3600:.4f}</b> فلز\n"
            f"📦 <b>ذخیره معدن</b>\n{storage_bar} <b>{percent}%</b>\n"
            f"🔩 {storage:,.0f} / {capacity:,.0f}\n\n"
            "وقتی ذخیره معدن پر شود، تولید جدید متوقف می‌شود تا فلز را دریافت کنید."
        )
        max_level = int(_mine_config(config).get("max_level", 100))
        next_level = country.metal_mine_level + 1
        next_data = _metal_mine_level_data(next_level, config)
        if country.metal_mine_level >= max_level:
            text += "\n\n🏆 <b>به حداکثر سطح رسیدید.</b>"
        elif next_data is not None:
            labels = {"money":"💰 پول", "metal":"🔩 فلز", "fuel":"⛽ سوخت"}
            shown = [
                f"💰 پول: {float(cost.get('money',0) or 0):,.0f}",
                f"🔩 فلز: {float(cost.get('metal',0) or 0):,.0f}",
                f"⛽ سوخت: {float(cost.get('fuel',0) or 0):,.0f}",
                f"☢️ اورانیوم: {float(cost.get('uranium', next_data.get('uranium',0)) or 0):,.2f}",
            ]
            text += (
                f"\n\n⬆️ <b>اطلاعات سطح بعدی: {next_level}</b>\n"
                f"🛡️ استحکام: <b>{float(next_data.get('strength',0)):,.0f}</b>\n"
                f"⚙️ تولید در ساعت: <b>{float(next_data.get('production_per_hour',0)):,.0f}</b>\n"
                f"⏱️ تولید در هر ثانیه: <b>{float(next_data.get('production_per_hour',0))/3600:.4f}</b>\n"
                f"📦 ظرفیت مخزن: <b>{float(next_data.get('storage_capacity',0)):,.0f}</b>\n"
                f"🏛️ سطح مرکز فرماندهی موردنیاز: <b>{int(next_data.get('required_hq_level', next_level))}</b>\n"
                "💰 <b>هزینه‌ها:</b>\n" + "\n".join(shown)
            )
        return text
    build = _mine_config(config)["build_cost"]
    cfg=_mine_config(config)
    return (
        f"⛏️ <b>معدن فلز {country.title}</b>\n\n"
        "📊 وضعیت: <b>ساخته نشده</b>\n"
        "📋 <b>مشخصات سطح ۱</b>\n"
        f"🛡️ استحکام: <b>{float(cfg.get('build_strength',0.0)):,.0f}</b>\n"
        f"⚙️ تولید در ساعت: <b>{float(cfg.get('build_production_per_hour',0.0)):,.0f}</b>\n"
        f"⏱️ تولید در هر ثانیه: <b>{float(cfg.get('build_production_per_hour',0.0))/3600:.4f}</b>\n"
        f"⏱️ زمان تکمیل: <b>{float(cfg.get('build_completion_time',0.0)):,.0f} ساعت</b>\n"
        f"📦 ظرفیت مخزن: <b>{float(cfg.get('build_storage_capacity',0.0)):,.0f}</b>\n\n"
        f"🏛️ سطح مرکز فرماندهی موردنیاز: <b>{int(cfg.get('build_required_hq_level', 1) or 1)}</b>\n"
        "💰 <b>هزینه‌ها:</b>\n"
        f"💰 پول: <b>{float(build.get('money',0)):,.0f}</b>\n"
        f"🔩 فلز: <b>{float(build.get('metal',0)):,.0f}</b>\n"
        f"⛽ سوخت: <b>{float(build.get('fuel',0)):,.0f}</b>"
        + (f"\n☢️ اورانیوم: <b>{float(build.get('uranium',0)):,.2f}</b>" if float(build.get('uranium',0)) > 0 else "")
    )



def _metal_mine_build_uranium_cost(config):
    cfg = _mine_config(config)
    legacy = float(cfg.get("build_cost_uranium", 0.0) or 0.0)
    nested = float((cfg.get("build_cost") or {}).get("uranium", 0.0) or 0.0)
    return legacy if legacy > 0 else nested

def can_build_metal_mine(country, config=None, payment="normal"):
    finalize_construction(country)
    if construction_remaining(country, "metal_mine")[0] > 0: return False,"IN_PROGRESS"
    if country.metal_mine_level > 0:
        return False, "ALREADY_BUILT"
    required_hq = int(_mine_config(config).get("build_required_hq_level", 1) or 1)
    if int(getattr(country,"command_center_level",0)) < required_hq:
        return False, "HQ_REQUIRED"
    missing = {}
    costs = {k: float(_mine_config(config)["build_cost"].get(k, 0.0)) for k in ("money", "metal", "fuel")} if payment == "normal" else {"uranium": _metal_mine_build_uranium_cost(config)}
    for resource, amount in costs.items():
        if not resource_available(country, resource, amount):
            missing[resource] = amount - getattr(country, resource)
    return len(missing) == 0, missing


def build_metal_mine(country, config=None, payment="normal", session=None):
    can_build, result = can_build_metal_mine(country, config, payment)
    if not can_build:
        return False, result
    costs = {k: float(_mine_config(config)["build_cost"].get(k, 0.0)) for k in ("money", "metal", "fuel")} if payment == "normal" else {"uranium": _metal_mine_build_uranium_cost(config)}
    hours=float(_mine_config(config).get("build_completion_time",0) or 0)
    if session is not None and hours > 0:
        from services.construction_teams import reserve_team
        if reserve_team(session,country,"metal_mine","⛏️ ساخت معدن فلز",datetime.utcnow()+timedelta(hours=hours)) is None:
            return False,"NO_TEAM"
    for resource, amount in costs.items():
        spend_resource(country, resource, amount)
    start_construction(country, "metal_mine", (-1 if payment == "uranium" else 1), hours, storage_reset=True)
    country.metal_mine_storage = 0
    country.metal_mine_last_production_at = datetime.utcnow()
    return True, 1

def _arsenal_level_data(level, config):
    if level == 1:
        return {"storage_capacity":float(config.get("build_storage_capacity",0)),
                "strength":float(config.get("build_strength",0)),
                "military_power":float(config.get("build_military_power",0))}
    return config.get("levels",{}).get(level)

def arsenal_upgrade_cost(level, config, payment="normal"):
    data=_arsenal_level_data(level+1,config)
    if not data: return None
    if payment=="uranium": return {"uranium":float(data.get("uranium",0))}
    return {k:float(data.get(k,0)) for k in ("money","metal","fuel") if float(data.get(k,0))>0}

def can_build_arsenal(country,config,payment="normal"):
    finalize_construction(country)
    if construction_remaining(country, "arsenal")[0] > 0: return False,"IN_PROGRESS"
    if getattr(country,"arsenal_level",0)>0: return False,"ALREADY_BUILT"
    if int(getattr(country,"command_center_level",0)) < int(config.get("build_required_hq_level",1)): return False,"HQ_REQUIRED"
    if payment == "uranium":
        costs={"uranium":float(config.get("build_cost",{}).get("uranium",0))}
    else:
        costs={k:float(config.get("build_cost",{}).get(k,0)) for k in ("money","metal","fuel") if float(config.get("build_cost",{}).get(k,0))>0}
    missing={}
    for r,a in costs.items():
        if not resource_available(country,r,a): missing[r]=max(0.0,float(a)-float(getattr(country,r,0.0)))
    return len(missing)==0,missing

def build_arsenal(country,config,payment="normal",session=None):
    ok,res=can_build_arsenal(country,config,payment)
    if not ok: return False,res
    costs={"uranium":float(config.get("build_cost",{}).get("uranium",0))} if payment=="uranium" else {k:float(config.get("build_cost",{}).get(k,0)) for k in ("money","metal","fuel") if float(config.get("build_cost",{}).get(k,0))>0}
    hours=float(config.get("build_completion_time",0) or 0)
    if session is not None and hours > 0:
        from services.construction_teams import reserve_team
        if reserve_team(session,country,"arsenal", "🏭 ساخت زرادخانه", datetime.utcnow()+timedelta(hours=hours)) is None:
            return False,"NO_TEAM"
    for r,a in costs.items(): spend_resource(country,r,a)
    start_construction(country, "arsenal", (-1 if payment == "uranium" else 1), hours, storage_reset=True)
    country.arsenal_storage=0.0
    return True, "IN_PROGRESS" if construction_remaining(country,"arsenal")[0] > 0 else 1

def can_upgrade_arsenal(country,config,payment="normal"):
    finalize_construction(country)
    if construction_remaining(country, "arsenal")[0] > 0: return False,"IN_PROGRESS"
    level=int(getattr(country,"arsenal_level",0))
    if level<=0: return False,"NOT_BUILT"
    next_level=level+1
    req=int((config.get("levels",{}).get(next_level) or {}).get("required_hq_level", next_level))
    if int(getattr(country,"command_center_level",0)) < req: return False,"HQ_REQUIRED"
    if level>=int(config.get("max_level",100)): return False,"MAX_LEVEL"
    cost=arsenal_upgrade_cost(level,config,payment)
    if cost is None: return False,"MAX_LEVEL"
    missing={}
    for r,a in cost.items():
        if not resource_available(country,r,a):
            current = float(getattr(country,r,0.0))
            missing[r]=max(0.0,float(a)-current)
    return True,missing

def upgrade_arsenal(country,config,payment="normal",session=None):
    ok,res=can_upgrade_arsenal(country,config,payment)
    if not ok: return False,res
    if isinstance(res, dict) and res:
        return False,res
    target=country.arsenal_level + 1
    nxt=_arsenal_level_data(target,config) or {}
    hours=float(nxt.get("completion_time",0) or 0)
    if session is not None and hours > 0:
        from services.construction_teams import reserve_team
        if reserve_team(session,country,"arsenal",f"🏭 ارتقای زرادخانه به سطح {target}",datetime.utcnow()+timedelta(hours=hours)) is None:
            return False,"NO_TEAM"
    for r,a in arsenal_upgrade_cost(country.arsenal_level,config,payment).items(): spend_resource(country,r,a)
    start_construction(country, "arsenal", (-target if payment == "uranium" else target), hours, storage_reset=True)
    return True, "IN_PROGRESS" if construction_remaining(country,"arsenal")[0] > 0 else target

def arsenal_instant_finish_uranium_cost(country, config=None):
    remaining, _ = construction_remaining(country, "arsenal")
    if remaining <= 0:
        return 0.0
    rate = max(0.0, float((config or {}).get("instant_finish_uranium_per_hour", 0.0) or 0.0))
    if rate <= 0:
        return 0.0
    return math.ceil((remaining / 3600.0) * rate * 100.0) / 100.0

def finish_arsenal_construction_now(country, config=None, session=None):
    remaining, encoded_target = construction_remaining(country, "arsenal")
    if remaining <= 0 or not encoded_target:
        return False, "NOT_IN_PROGRESS"
    cost = arsenal_instant_finish_uranium_cost(country, config)
    if cost <= 0:
        return False, "DISABLED"
    if not resource_available(country, "uranium", cost):
        return False, cost
    spend_resource(country, "uranium", cost)
    target = abs(int(encoded_target))
    country.arsenal_level = target
    until_field, target_field = _construction_fields("arsenal")
    setattr(country, until_field, None)
    setattr(country, target_field, None)
    if session is not None:
        from services.construction_teams import release_team
        release_team(session, country, "arsenal")
    return True, cost

def cancel_arsenal_construction(country, config=None, session=None):
    remaining, encoded_target = construction_remaining(country, "arsenal")
    if remaining <= 0 or not encoded_target:
        return False, "NOT_IN_PROGRESS"
    target = abs(int(encoded_target))
    payment = "uranium" if int(encoded_target) < 0 else "normal"
    if target == 1 and int(getattr(country, "arsenal_level", 0) or 0) <= 0:
        cost = dict((config or {}).get("build_cost", {}))
    else:
        current = int(getattr(country, "arsenal_level", 0) or 0)
        cost = arsenal_upgrade_cost(current, config or {}, payment) or {}
        if payment == "uranium":
            # arsenal_upgrade_cost already returns only uranium for uranium payment.
            pass
    refund = _hq_payment_cost(cost, payment)
    for resource, amount in refund.items():
        add_resource(country, resource, float(amount) * 0.5)
    until_field, target_field = _construction_fields("arsenal")
    setattr(country, until_field, None)
    setattr(country, target_field, None)
    if session is not None:
        from services.construction_teams import release_team
        release_team(session, country, "arsenal")
    return True, refund

def arsenal_info(country,config):
    finalize_construction(country)
    level=int(getattr(country,"arsenal_level",0))
    remaining, target_level = construction_remaining(country, "arsenal")
    if remaining > 0:
        target_level = abs(int(target_level or (1 if level <= 0 else level + 1)))
        if target_level == 1 and level <= 0:
            military_power = _cumulative_military_power(1, config, "arsenal")
            strength = float(config.get("build_strength", 0))
            completion_hours = float(config.get("build_completion_time", 0))
            state = "🏗️ <b>در حال ساخت</b>"
        else:
            data = _arsenal_level_data(target_level, config) or {}
            military_power = _cumulative_military_power(target_level, config, "arsenal")
            strength = float(data.get("strength", 0))
            completion_hours = float(data.get("completion_time", 0))
            state = f"⬆️ <b>در حال ارتقا به سطح {target_level}</b>"
        return (f"🏭 <b>زرادخانه {country.title}</b>\n\n"
                f"{state}\n"
                f"📋 <b>مشخصات سطح {target_level}</b>\n"
                f"🪖 قدرت نظامی: <b>{military_power:,.0f}</b>\n"
                f"🛡️ استحکام: <b>{strength:,.0f}</b>\n"
                f"📦 ظرفیت مخزن: <b>{float((config.get('build_storage_capacity',0) if target_level == 1 else (_arsenal_level_data(target_level,config) or {}).get('storage_capacity',0))):,.0f}</b>\n"
                f"⏱️ زمان تکمیل: <b>{completion_hours:,.0f} ساعت</b>\n"
                f"⏳ زمان باقی‌مانده: <b>{remaining/3600.0:,.0f} ساعت</b>")
    if level<=0:
        return f"🏭 <b>زرادخانه {country.title}</b>\n\n📊 وضعیت: <b>ساخته نشده</b>"
    data=_arsenal_level_data(level,config) or {}
    cap=float(data.get("storage_capacity",0)); storage=min(float(getattr(country,"arsenal_storage",0)),cap) if cap else 0
    pct=int(storage/cap*100) if cap else 0
    filled=min(10,int(round(pct/10))); bar="🟩"*filled+"⬜"*(10-filled)
    text=(f"🏭 <b>زرادخانه {country.title}</b>\n\n📊 سطح فعلی: <b>{level}</b>\n"
          + f"🪖 قدرت نظامی: <b>{_cumulative_military_power(level, config, 'arsenal'):,.0f}</b>\n"
          + f"🛡️ استحکام: <b>{float(data.get('strength',0)):,.0f}</b>\n"
          + f"📦 مخزن موشک: {bar} <b>{pct}%</b>\n🚀 {storage:,.0f} / {cap:,.0f}")
    if level>=int(config.get("max_level",100)): return text+"\n\n🏆 <b>به حداکثر سطح رسیدید.</b>"
    nxt=_arsenal_level_data(level+1,config)
    if nxt:
        cost=arsenal_upgrade_cost(level,config); labels={"money":"💰 پول","metal":"🔩 فلز","fuel":"⛽ سوخت","uranium":"☢️ اورانیوم"}
        text += (
            f"\n\n⬆️ <b>اطلاعات سطح بعدی: {level+1}</b>\n"
            f"🪖 قدرت نظامی: <b>{_cumulative_military_power(level+1, config, 'arsenal'):,.0f}</b>\n"
            f"🛡️ استحکام: <b>{float(nxt.get('strength',0)):,.0f}</b>\n"
            f"📦 ظرفیت مخزن: <b>{float(nxt.get('storage_capacity',0)):,.0f}</b>\n"
            f"🏛️ سطح مرکز فرماندهی موردنیاز: <b>{int(nxt.get('required_hq_level', level+1))}</b>\n"
            f"💰 <b>هزینه‌ها:</b>\n" +
            "\n".join([
                f"💰 پول: <b>{float(cost.get('money',0) or 0):,.0f}</b>",
                f"🔩 فلز: <b>{float(cost.get('metal',0) or 0):,.0f}</b>",
                f"⛽ سوخت: <b>{float(cost.get('fuel',0) or 0):,.0f}</b>",
                f"☢️ اورانیوم: <b>{float(cost.get('uranium', nxt.get('uranium',0)) or 0):,.2f}</b>",
            ]) +
            f"\n⏱️ زمان تکمیل: <b>{float(nxt.get('completion_time',0)):,.0f} ساعت</b>"
        )
    return text

# =========================
# 💱 سیستم تبادل منابع
# =========================

# نرخ‌ها بر اساس مقدار «ورودی» تعریف شده‌اند.
# برای هر عملیات، مقدار خروجی با این نسبت محاسبه می‌شود.
EXCHANGE_RATES = {
    "money_to_metal": {
        "title": "💰 ➜ 🔩 پول به فلز",
        "from_resource": "money",
        "to_resource": "metal",
        "input_unit": 100,
        "output_unit": 10,
    },
    "metal_to_money": {
        "title": "🔩 ➜ 💰 فلز به پول",
        "from_resource": "metal",
        "to_resource": "money",
        "input_unit": 10,
        "output_unit": 90,
    },
    "money_to_fuel": {
        "title": "💰 ➜ ⛽ پول به سوخت",
        "from_resource": "money",
        "to_resource": "fuel",
        "input_unit": 200,
        "output_unit": 10,
    },
    "fuel_to_money": {
        "title": "⛽ ➜ 💰 سوخت به پول",
        "from_resource": "fuel",
        "to_resource": "money",
        "input_unit": 10,
        "output_unit": 180,
    },
    "uranium_to_fuel": {
        "title": "☢️ ➜ ⛽ اورانیوم به سوخت",
        "from_resource": "uranium",
        "to_resource": "fuel",
        "input_unit": 1,
        "output_unit": 500,
    },
    "uranium_to_money": {
        "title": "☢️ ➜ 💰 اورانیوم به پول",
        "from_resource": "uranium",
        "to_resource": "money",
        "input_unit": 1,
        "output_unit": 10_000,
    },
}


EXCHANGE_SETTINGS_KEY = "exchange_rates_v1"
EXCHANGE_TEXT_KEY = "exchange_display_text_v1"
DEFAULT_EXCHANGE_TEXT = "نرخ‌های تبادل منابع در این بخش نمایش داده می‌شوند."


def get_exchange_text(session=None):
    if session is None:
        return DEFAULT_EXCHANGE_TEXT
    row = session.scalar(select(BotSetting).where(BotSetting.key == EXCHANGE_TEXT_KEY))
    if row is None or not str(row.value or "").strip():
        return DEFAULT_EXCHANGE_TEXT
    return str(row.value)


def save_exchange_text(session, text):
    text = str(text or "").strip()
    row = session.scalar(select(BotSetting).where(BotSetting.key == EXCHANGE_TEXT_KEY))
    if row is None:
        session.add(BotSetting(key=EXCHANGE_TEXT_KEY, value=text))
    else:
        row.value = text
    return text


def get_exchange_rates(session=None):
    rates = {k: dict(v) for k, v in EXCHANGE_RATES.items()}
    if session is None:
        return rates
    row = session.scalar(select(BotSetting).where(BotSetting.key == EXCHANGE_SETTINGS_KEY))
    if row is None:
        return rates
    try:
        data = json.loads(row.value)
        for key, value in data.items():
            if key not in rates or not isinstance(value, dict):
                continue
            for fld in ("input_unit", "output_unit"):
                try:
                    v=float(value.get(fld, rates[key][fld]))
                    if v > 0: rates[key][fld]=v
                except (TypeError, ValueError):
                    pass
    except Exception:
        pass
    return rates

def save_exchange_rate(session, exchange_type, input_unit, output_unit):
    rates = get_exchange_rates(session)
    if exchange_type not in rates:
        raise ValueError("invalid exchange type")
    rates[exchange_type]["input_unit"] = max(0.000001, float(input_unit))
    rates[exchange_type]["output_unit"] = max(0.000001, float(output_unit))
    row = session.scalar(select(BotSetting).where(BotSetting.key == EXCHANGE_SETTINGS_KEY))
    payload = {k:{"input_unit":v["input_unit"],"output_unit":v["output_unit"]} for k,v in rates.items()}
    if row is None:
        session.add(BotSetting(key=EXCHANGE_SETTINGS_KEY, value=json.dumps(payload, ensure_ascii=False)))
    else:
        row.value=json.dumps(payload, ensure_ascii=False)
    return rates

def exchange_rate_text(session=None):
    rates = get_exchange_rates(session)
    names={"money":"💰 پول","metal":"🔩 فلز","fuel":"⛽ سوخت","uranium":"☢️ اورانیوم"}
    labels={
        "money_to_metal":"🛒 خرید فلز در برابر پول",
        "money_to_fuel":"🛒 خرید سوخت در برابر پول",
        "metal_to_money":"💰 فروش فلز در برابر پول",
        "fuel_to_money":"💰 فروش سوخت در برابر پول",
        "uranium_to_fuel":"☢️ فروش اورانیوم در برابر سوخت",
        "uranium_to_money":"☢️ فروش اورانیوم در برابر پول",
    }
    custom = get_exchange_text(session)
    if custom and custom != DEFAULT_EXCHANGE_TEXT:
        return custom
    lines=["💱 <b>نرخ تبادل منابع</b>", "", custom, ""]
    for key in labels:
        r=rates[key]
        lines.append(f"{labels[key]}: <b>{r['input_unit']:,.0f}</b> {names[r['from_resource']]} ➜ <b>{r['output_unit']:,.0f}</b> {names[r['to_resource']]}")
    return "\n".join(lines)


def calculate_exchange(country, exchange_type, amount, session=None):
    from decimal import Decimal

    rate = get_exchange_rates(session).get(exchange_type)
    if rate is None:
        return False, "INVALID_EXCHANGE"

    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return False, "INVALID_AMOUNT"
    if amount <= 0:
        return False, "INVALID_AMOUNT"

    available = getattr(country, rate["from_resource"])
    if not is_infinite(country, rate["from_resource"]) and available < amount:
        return False, ("INSUFFICIENT", amount - available)

    # تبدیل کاملاً اعشاری است و هیچ محدودیتی برای مضرب بودن وجود ندارد.
    output = float(
        Decimal(str(amount)) * Decimal(str(rate["output_unit"]))
        / Decimal(str(rate["input_unit"]))
    )

    if output <= 0:
        return False, "OUTPUT_TOO_SMALL"

    return True, {
        "input": amount,
        "output": output,
        "from_resource": rate["from_resource"],
        "to_resource": rate["to_resource"],
    }


def execute_exchange(country, exchange_type, amount, session=None):
    ok, result = calculate_exchange(country, exchange_type, amount, session)

    if not ok:
        return False, result

    from_resource = result["from_resource"]
    to_resource = result["to_resource"]

    spend_resource(country, from_resource, result["input"])
    add_resource(country, to_resource, result["output"])

    return True, result

# =========================================================
# موجودی اختصاصی موشک‌های هر کشور
# =========================================================
MISSILE_INVENTORY_PREFIX = "country_missile_inventory_v1:"

def _missile_inventory_key(country_id):
    return f"{MISSILE_INVENTORY_PREFIX}{int(country_id)}"

def get_missile_inventory(session, country_id):
    row = session.scalar(select(BotSetting).where(BotSetting.key == _missile_inventory_key(country_id)))
    if row is None:
        return {}
    try:
        data = json.loads(row.value)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def save_missile_inventory(session, country_id, inventory):
    key = _missile_inventory_key(country_id)
    payload = json.dumps(inventory or {}, ensure_ascii=False)
    row = session.scalar(select(BotSetting).where(BotSetting.key == key))
    if row is None:
        session.add(BotSetting(key=key, value=payload))
    else:
        row.value = payload
    return inventory

def add_missile_to_inventory(session, country_id, missile_id, level=1, amount=1):
    inv = get_missile_inventory(session, country_id)
    mid = str(missile_id)
    levels = inv.setdefault(mid, {})
    lk = str(int(level))
    current = max(0, int(levels.get(lk, 0) or 0))
    delta = int(amount)
    new_count = current + delta
    # موجودی هر سطح هرگز منفی نمی‌شود.
    if new_count <= 0:
        levels.pop(lk, None)
    else:
        levels[lk] = new_count
    if not levels:
        inv.pop(mid, None)
    save_missile_inventory(session, country_id, inv)
    return inv

MISSILE_TECH_PREFIX = "missile_tech_level:"
MISSILE_TECH_CONSTRUCTION_PREFIX = "missile_tech_construction:"

def _missile_tech_key(country_id, missile_id):
    return f"{MISSILE_TECH_CONSTRUCTION_PREFIX}{int(country_id)}:{str(missile_id)}"

def get_missile_tech_construction(session, country_id, missile_id):
    row = session.scalar(select(BotSetting).where(BotSetting.key == _missile_tech_key(country_id, missile_id)))
    if row is None or not row.value:
        return None
    try:
        import json
        return json.loads(row.value)
    except Exception:
        return None

def save_missile_tech_construction(session, country_id, missile_id, payload):
    import json
    key = _missile_tech_key(country_id, missile_id)
    row = session.scalar(select(BotSetting).where(BotSetting.key == key))
    if payload is None:
        if row is not None:
            session.delete(row)
        return
    raw = json.dumps(payload, ensure_ascii=False)
    if row is None:
        session.add(BotSetting(key=key, value=raw))
    else:
        row.value = raw

def finalize_missile_tech_upgrade(session, country_id, missile_id, now=None):
    data = get_missile_tech_construction(session, country_id, missile_id)
    if not data:
        return False, None
    now = now or datetime.utcnow()
    until = datetime.fromisoformat(data["until"])
    if until > now:
        return False, data
    level = int(data["target_level"])
    save_missile_tech_level(session, country_id, missile_id, level)
    save_missile_tech_construction(session, country_id, missile_id, None)
    try:
        from services.construction_teams import release_team
        country=session.get(Country, int(country_id))
        if country is not None:
            release_team(session, country, f"missile:{missile_id}")
    except Exception:
        pass
    return True, data

def missile_tech_upgrade_remaining(session, country_id, missile_id, now=None):
    data = get_missile_tech_construction(session, country_id, missile_id)
    if not data:
        return 0.0, None
    now = now or datetime.utcnow()
    until = datetime.fromisoformat(data["until"])
    remaining = max(0.0, (until - now).total_seconds())
    return remaining, int(data.get("target_level", 0) or 0)

def missile_tech_upgrade_cost(level_data, payment="normal"):
    if payment == "uranium":
        return {"uranium": float(level_data.get("upgrade_uranium", 0) or 0)}
    return {
        "money": float(level_data.get("upgrade_money", 0) or 0),
        "metal": float(level_data.get("upgrade_metal", 0) or 0),
        "fuel": float(level_data.get("upgrade_fuel", 0) or 0),
    }

def start_missile_tech_upgrade(session, country, missile_id, target_level, level_data, payment="normal"):
    remaining, _ = missile_tech_upgrade_remaining(session, country.id, missile_id)
    if remaining > 0:
        return False, "IN_PROGRESS"
    cost = missile_tech_upgrade_cost(level_data, payment)
    missing = {}
    for resource, amount in cost.items():
        if amount > 0 and not resource_available(country, resource, amount):
            missing[resource] = amount - float(getattr(country, resource, 0) or 0)
    if missing:
        return False, missing
    hours = max(0.0, float(level_data.get("upgrade_time", 0) or 0))
    until = datetime.utcnow() + timedelta(hours=hours)
    if hours > 0:
        from services.construction_teams import reserve_team
        if reserve_team(session, country, f"missile:{missile_id}", f"🚀 ارتقای فناوری موشک {missile_id} به سطح {target_level}", until) is None:
            return False, "NO_TEAM"
    for resource, amount in cost.items():
        if amount > 0:
            spend_resource(country, resource, amount)
    save_missile_tech_construction(session, country.id, missile_id, {
        "target_level": int(target_level), "until": until.isoformat(), "payment": payment,
        "paid": cost,
    })
    if hours <= 0:
        save_missile_tech_level(session, country.id, missile_id, int(target_level))
        save_missile_tech_construction(session, country.id, missile_id, None)
        return True, "DONE"
    return True, "IN_PROGRESS"

def cancel_missile_tech_upgrade(session, country, missile_id):
    data = get_missile_tech_construction(session, country.id, missile_id)
    if not data:
        return False, None
    paid = data.get("paid") or {}
    refund = {}
    for resource, amount in paid.items():
        value = float(amount or 0) * 0.5
        if value > 0:
            setattr(country, resource, float(getattr(country, resource, 0) or 0) + value)
            refund[resource] = value
    save_missile_tech_construction(session, country.id, missile_id, None)
    from services.construction_teams import release_team
    release_team(session, country, f"missile:{missile_id}")
    return True, refund

def missile_tech_instant_finish_uranium_cost(session, country, missile_id, missile_cfg):
    remaining, _ = missile_tech_upgrade_remaining(session, country.id, missile_id)
    if remaining <= 0:
        return 0.0
    rate = max(0.0, float(missile_cfg.get("instant_finish_uranium_per_hour", 0) or 0))
    if rate <= 0:
        return 0.0
    return math.ceil((remaining / 3600.0) * rate * 100.0) / 100.0

def finish_missile_tech_upgrade_now(session, country, missile_id, missile_cfg):
    data = get_missile_tech_construction(session, country.id, missile_id)
    if not data:
        return False, "NOT_IN_PROGRESS"
    cost = missile_tech_instant_finish_uranium_cost(session, country, missile_id, missile_cfg)
    if cost <= 0:
        return False, "DISABLED"
    if not resource_available(country, "uranium", cost):
        return False, cost
    spend_resource(country, "uranium", cost)
    save_missile_tech_level(session, country.id, missile_id, int(data["target_level"]))
    save_missile_tech_construction(session, country.id, missile_id, None)
    from services.construction_teams import release_team
    release_team(session, country, f"missile:{missile_id}")
    return True, cost


def get_missile_tech_level(session, country_id, missile_id):
    key = f"{MISSILE_TECH_PREFIX}{int(country_id)}:{str(missile_id)}"
    row = session.scalar(select(BotSetting).where(BotSetting.key == key))
    if row is None:
        return 1
    try:
        return max(1, int(float(row.value or 1)))
    except Exception:
        return 1

def save_missile_tech_level(session, country_id, missile_id, level):
    key = f"{MISSILE_TECH_PREFIX}{int(country_id)}:{str(missile_id)}"
    row = session.scalar(select(BotSetting).where(BotSetting.key == key))
    if row is None:
        session.add(BotSetting(key=key, value=str(int(level))))
    else:
        row.value = str(int(level))
    return int(level)

def get_missile_count(inventory, missile_id, level=None):
    levels = (inventory or {}).get(str(missile_id), {})
    if level is None:
        return sum(int(v or 0) for v in levels.values())
    return int(levels.get(str(int(level)), 0) or 0)
