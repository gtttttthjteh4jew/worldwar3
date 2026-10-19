import time
import json
import threading
from copy import deepcopy
from sqlalchemy import select
from database.models import BotSetting

_STATE_MUTATION_LOCK = threading.RLock()


ECONOMY_KEY = "economy_metal_mine_v1"
INITIAL_RESOURCES_KEY = "game_initial_resources_v1"
COMPLETION_TIME_HOURS_MIGRATION_KEY = "completion_time_hours_migrated_v1"

def _migrate_completion_times_to_hours(session):
    row = session.scalar(select(BotSetting).where(BotSetting.key == COMPLETION_TIME_HOURS_MIGRATION_KEY))
    if row is not None and row.value == "1":
        return
    changed = False
    for key, normalizer in ((ECONOMY_KEY, _normalize if "_normalize" in globals() else None), (ARSENAL_KEY, _normalize_arsenal if "_normalize_arsenal" in globals() else None), (HQ_KEY, _normalize_hq if "_normalize_hq" in globals() else None)):
        if normalizer is None:
            continue
        r = session.scalar(select(BotSetting).where(BotSetting.key == key))
        if r is None:
            continue
        try:
            data = json.loads(r.value)
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        if "build_completion_time" in data:
            data["build_completion_time"] = float(data.get("build_completion_time", 0) or 0) / 3600.0
            changed = True
        levels = data.get("levels")
        if isinstance(levels, dict):
            for vals in levels.values():
                if isinstance(vals, dict) and "completion_time" in vals:
                    vals["completion_time"] = float(vals.get("completion_time", 0) or 0) / 3600.0
                    changed = True
        r.value = json.dumps(normalizer(data), ensure_ascii=False)
    if row is None:
        session.add(BotSetting(key=COMPLETION_TIME_HOURS_MIGRATION_KEY, value="1"))
    else:
        row.value = "1"
    session.commit()


DEFAULT_INITIAL_RESOURCES = {"money": 0.0, "fuel": 0.0, "metal": 0.0, "uranium": 0.0}

def get_initial_resources(session):
    row=session.scalar(select(BotSetting).where(BotSetting.key==INITIAL_RESOURCES_KEY))
    if row is None: return deepcopy(DEFAULT_INITIAL_RESOURCES)
    try:
        data=json.loads(row.value); out=deepcopy(DEFAULT_INITIAL_RESOURCES)
        for k in out:
            if k in data: out[k]=max(0.0,float(data[k]))
        return out
    except Exception: return deepcopy(DEFAULT_INITIAL_RESOURCES)

def save_initial_resources(session, data):
    out=deepcopy(DEFAULT_INITIAL_RESOURCES)
    for k in out:
        try: out[k]=max(0.0,float(data.get(k,out[k])))
        except Exception: pass
    row=session.scalar(select(BotSetting).where(BotSetting.key==INITIAL_RESOURCES_KEY))
    payload=json.dumps(out,ensure_ascii=False)
    if row is None: session.add(BotSetting(key=INITIAL_RESOURCES_KEY,value=payload))
    else: row.value=payload
    return out

DEFAULT_METAL_MINE = {
    "max_level": 100,
    "build_cost": {"money": 3000.0, "metal": 500.0, "fuel": 250.0, "uranium": 0.0},
    "build_military_power": 5.0,
    "build_strength": 10.0,
    "build_production_per_hour": 100.0,
    "build_storage_capacity": 500.0,
    "build_cost_uranium": 10.0,
    "build_required_hq_level": 1,
    "build_completion_time": 0.0,
    "instant_finish_uranium_per_hour": 0.0,
    "levels": {
        2: {"active": True, "production_per_hour": 250.0, "storage_capacity": 1500.0, "money": 5000.0, "metal": 1000.0, "fuel": 500.0, "uranium": 2.0, "military_power": 10.0, "strength": 10.0, "required_hq_level": 2},
        3: {"active": True, "production_per_hour": 500.0, "storage_capacity": 3500.0, "money": 12000.0, "metal": 2500.0, "fuel": 1250.0, "uranium": 0.0, "military_power": 25.0, "strength": 20.0, "required_hq_level": 3},
        4: {"active": True, "production_per_hour": 900.0, "storage_capacity": 7000.0, "money": 25000.0, "metal": 6000.0, "fuel": 3000.0, "uranium": 0.0, "military_power": 0.0, "strength": 0.0},
        5: {"active": True, "production_per_hour": 1500.0, "storage_capacity": 12000.0, "money": 50000.0, "metal": 15000.0, "fuel": 7500.0, "uranium": 0.0, "military_power": 0.0, "strength": 0.0},
        6: {"active": True, "production_per_hour": 2400.0, "storage_capacity": 20000.0, "money": 90000.0, "metal": 30000.0, "fuel": 15000.0, "uranium": 0.0, "military_power": 0.0, "strength": 0.0},
        7: {"active": True, "production_per_hour": 3800.0, "storage_capacity": 32000.0, "money": 160000.0, "metal": 55000.0, "fuel": 27500.0, "uranium": 0.0, "military_power": 0.0, "strength": 0.0},
        8: {"active": True, "production_per_hour": 6000.0, "storage_capacity": 50000.0, "money": 280000.0, "metal": 100000.0, "fuel": 50000.0, "uranium": 0.0, "military_power": 0.0, "strength": 0.0},
        9: {"active": True, "production_per_hour": 9000.0, "storage_capacity": 75000.0, "money": 480000.0, "metal": 180000.0, "fuel": 90000.0, "uranium": 0.0, "military_power": 0.0, "strength": 0.0},
        10: {"active": True, "production_per_hour": 13000.0, "storage_capacity": 110000.0, "money": 800000.0, "metal": 300000.0, "fuel": 150000.0, "uranium": 0.0, "military_power": 0.0, "strength": 0.0},
    },
}

# مقادیر اقتصادی قابل تنظیم توسط Owner در حالت پیش‌فرض صفر هستند.
# max_level یک محدودیت ساختاری است و مقدار پیش‌فرض معتبر آن 100 باقی می‌ماند.
for _k in ("money", "metal", "fuel", "uranium"):
    DEFAULT_METAL_MINE["build_cost"][_k] = 0.0
DEFAULT_METAL_MINE["build_military_power"] = 0.0
DEFAULT_METAL_MINE["build_strength"] = 0.0
DEFAULT_METAL_MINE["build_production_per_hour"] = 0.0
DEFAULT_METAL_MINE["build_storage_capacity"] = 0.0
DEFAULT_METAL_MINE["build_cost_uranium"] = 0.0
for _level, _vals in DEFAULT_METAL_MINE["levels"].items():
    for _field in ("production_per_hour", "storage_capacity", "money", "metal", "fuel", "uranium", "military_power", "strength", "required_hq_level", "completion_time"):
        _vals[_field] = 0.0

def _normalize(data):
    result = deepcopy(DEFAULT_METAL_MINE)
    try:
        max_level = int(data.get("max_level", result.get("max_level", 100))) if isinstance(data, dict) else 100
        result["max_level"] = max(2, min(100, max_level))
    except (TypeError, ValueError):
        result["max_level"] = 100
    if not isinstance(data, dict):
        return result
    if isinstance(data.get("build_cost"), dict):
        for k in result["build_cost"]:
            value = data["build_cost"].get(k)
            try:
                value = float(value)
            except (TypeError, ValueError):
                continue
            if value >= 0:
                result["build_cost"][k] = value

    try:
        build_military = float(data.get("build_military_power", result.get("build_military_power", 5.0)))
        if build_military >= 0:
            result["build_military_power"] = build_military
    except (TypeError, ValueError):
        pass

    try:
        build_strength = float(data.get("build_strength", result.get("build_strength", 10.0)))
        if build_strength >= 0:
            result["build_strength"] = build_strength
    except (TypeError, ValueError):
        pass

    for _field in ("build_production_per_hour", "build_storage_capacity", "build_completion_time"):
        try:
            _value = float(data.get(_field, result.get(_field, 0.0)))
            if _value >= 0:
                result[_field] = _value
        except (TypeError, ValueError):
            pass

    try:
        result["build_required_hq_level"] = max(1, min(100, int(data.get("build_required_hq_level", result.get("build_required_hq_level", 1)))))
    except (TypeError, ValueError):
        pass

    try:
        uranium_cost = float(data.get("build_cost_uranium", result.get("build_cost_uranium", 10.0)))
        if uranium_cost >= 0:
            result["build_cost_uranium"] = uranium_cost
    except (TypeError, ValueError):
        pass

    for f in ("money","metal","fuel","uranium"):
        try: result["build_cost"][f]=max(0.0,float(data.get("build_cost",{}).get(f,result["build_cost"][f])))
        except Exception: pass
    try: result["build_strength"]=max(0.0,float(data.get("build_strength",result["build_strength"])))
    except Exception: pass
    try:
        legacy_u=float(data.get("build_cost_uranium", result.get("build_cost",{}).get("uranium",0.0)))
        if legacy_u >= 0:
            result["build_cost_uranium"] = legacy_u
            if legacy_u > 0 or float(result["build_cost"].get("uranium",0.0)) == 0:
                result["build_cost"]["uranium"] = legacy_u
    except Exception: pass
    try:
        v=float(data.get("build_strength", result.get("build_strength",0.0)))
        if v>=0: result["build_strength"]=v
    except (TypeError,ValueError): pass
    if isinstance(data.get("build_cost"), dict):
        for k in result["build_cost"]:
            try:
                v=float(data["build_cost"].get(k,result["build_cost"][k]))
                if v>=0: result["build_cost"][k]=v
            except (TypeError,ValueError): pass
    try:
        v=float(data.get("build_completion_time", result.get("build_completion_time",0.0)))
        if v>=0: result["build_completion_time"]=v
    except (TypeError,ValueError): pass
    try:
        v=float(data.get("instant_finish_uranium_per_hour", result.get("instant_finish_uranium_per_hour",0.0)))
        if v>=0: result["instant_finish_uranium_per_hour"]=v
    except (TypeError,ValueError): pass
    levels = data.get("levels", {})
    if isinstance(levels, dict):
        for key, vals in levels.items():
            try:
                level = int(key)
            except (TypeError, ValueError):
                continue
            # سطح ۱ تنظیم‌پذیر نیست؛ ساخت معدن خودش سطح ۱ است.
            if level not in result["levels"] or not isinstance(vals, dict):
                continue
            for field in ("production_per_hour", "storage_capacity", "money", "metal", "fuel", "uranium", "military_power", "strength", "required_hq_level", "completion_time"):
                try:
                    value = float(vals.get(field, result["levels"][level][field]))
                except (TypeError, ValueError):
                    continue
                if value >= 0:
                    result["levels"][level][field] = value
    # همیشه سطوح ۲ تا ۱۰۰ قابل تنظیم باشند؛ برای سطوح جدید از الگوی سطح ۱۰ استفاده می‌کنیم.
    template = result["levels"].get(10, {"active": True, "production_per_hour": 13000.0, "storage_capacity": 110000.0, "money": 800000.0, "metal": 300000.0, "fuel": 150000.0, "uranium": 0.0, "military_power": 0.0, "strength": 0.0, "completion_time": 0.0})
    for level in range(2, 101):
        if level not in result["levels"]:
            factor = max(1.0, level / 10.0)
            result["levels"][level] = {
                "production_per_hour": float(template.get("production_per_hour", 0)) * factor,
                "storage_capacity": float(template.get("storage_capacity", 0)) * factor,
                "money": float(template.get("money", 0)) * factor,
                "metal": float(template.get("metal", 0)) * factor,
                "fuel": float(template.get("fuel", 0)) * factor,
                "uranium": float(template.get("uranium", 0)),
                "military_power": float(template.get("military_power", 0)),
                "strength": float(template.get("strength", 0)),
                "required_hq_level": level,
                "completion_time": float(template.get("completion_time", 0)),
            }
    result["levels"] = {k:v for k,v in result["levels"].items() if 2 <= int(k) <= 100}
    return result


def get_metal_mine_config(session):
    row = session.scalar(select(BotSetting).where(BotSetting.key == ECONOMY_KEY))
    if row is None:
        return _normalize({})
    try:
        return _normalize(json.loads(row.value))
    except Exception:
        return _normalize({})


def save_metal_mine_config(session, config):
    payload = _normalize(config)
    row = session.scalar(select(BotSetting).where(BotSetting.key == ECONOMY_KEY))
    if row is None:
        row = BotSetting(key=ECONOMY_KEY, value=json.dumps(payload, ensure_ascii=False))
        session.add(row)
    else:
        row.value = json.dumps(payload, ensure_ascii=False)
    return payload


# =========================================================
# 🏭 تنظیمات زرادخانه
# =========================================================
ARSENAL_KEY = "economy_arsenal_v1"

def _default_arsenal_level():
    return {"money":0.0,"metal":0.0,"fuel":0.0,"uranium":0.0,"storage_capacity":0.0,"strength":0.0,"military_power":0.0,"completion_time":0.0,"required_hq_level":1}

DEFAULT_ARSENAL = {
    "max_level": 100,
    "build_cost": {"money":0.0,"metal":0.0,"fuel":0.0,"uranium":0.0},
    "build_storage_capacity": 0.0,
    "build_strength": 0.0,
    "build_military_power": 0.0,
    "build_required_hq_level": 1,
    "build_completion_time": 0.0,
    "instant_finish_uranium_per_hour": 0.0,
    "levels": {2:_default_arsenal_level()},
}

def _normalize_arsenal(data):
    result = deepcopy(DEFAULT_ARSENAL)
    if not isinstance(data, dict): data={}
    try: result["max_level"]=max(2,min(100,int(data.get("max_level",100))))
    except (TypeError,ValueError): result["max_level"]=100
    if isinstance(data.get("build_cost"),dict):
        for k in result["build_cost"]:
            try:
                v=float(data["build_cost"].get(k,result["build_cost"][k]))
                if v>=0: result["build_cost"][k]=v
            except (TypeError,ValueError): pass
    try: result["build_required_hq_level"]=max(1,min(100,int(data.get("build_required_hq_level",1))))
    except Exception: pass
    # نرخ تکمیل فوری باید هنگام نرمال‌سازی حفظ شود؛ قبلاً هر بار
    # save_arsenal_config اجرا می‌شد مقدار دوباره به صفر برمی‌گشت.
    try:
        v=float(data.get("instant_finish_uranium_per_hour", result.get("instant_finish_uranium_per_hour",0.0)))
        if v >= 0:
            result["instant_finish_uranium_per_hour"] = v
    except (TypeError, ValueError):
        pass
    for f in ("build_storage_capacity","build_strength","build_military_power","build_completion_time"):
        try:
            v=float(data.get(f,result[f]))
            if v>=0: result[f]=v
        except (TypeError,ValueError): pass
    levels=data.get("levels",{})
    if isinstance(levels,dict):
        for key,vals in levels.items():
            try: level=int(key)
            except (TypeError,ValueError): continue
            if not 2<=level<=100 or not isinstance(vals,dict): continue
            base=deepcopy(result["levels"].get(level,_default_arsenal_level()))
            for f in base:
                try:
                    if f == "required_hq_level":
                        base[f]=max(1,min(100,int(vals.get(f,base[f])))); continue
                    v=float(vals.get(f,base[f]))
                    if v>=0: base[f]=v
                except (TypeError,ValueError): pass
            result["levels"][level]=base
    template=result["levels"].get(2,_default_arsenal_level())
    for level in range(2,101):
        if level not in result["levels"]: result["levels"][level]=deepcopy(template)
    return result

def get_arsenal_config(session):
    _migrate_completion_times_to_hours(session)
    row=session.scalar(select(BotSetting).where(BotSetting.key==ARSENAL_KEY))
    if row is None: return _normalize_arsenal({})
    try: return _normalize_arsenal(json.loads(row.value))
    except Exception: return _normalize_arsenal({})

def save_arsenal_config(session,config):
    payload=_normalize_arsenal(config)
    row=session.scalar(select(BotSetting).where(BotSetting.key==ARSENAL_KEY))
    if row is None: session.add(BotSetting(key=ARSENAL_KEY,value=json.dumps(payload,ensure_ascii=False)))
    else: row.value=json.dumps(payload,ensure_ascii=False)
    return payload


# =========================================================
# 🏛️ تنظیمات مرکز فرماندهی
# =========================================================
HQ_KEY = "economy_hq_v1"

def _default_hq_level():
    return {"money":0.0,"metal":0.0,"fuel":0.0,"uranium":0.0,"strength":0.0,"military_power":0.0,"completion_time":0.0}

DEFAULT_HQ = {
    "max_level": 100,
    "build_cost": {"money":0.0,"metal":0.0,"fuel":0.0,"uranium":0.0},
    "build_strength": 0.0,
    "build_military_power": 0.0,
    "build_completion_time": 0.0,
    "instant_finish_uranium_per_hour": 0.0,
    "levels": {2: {**_default_hq_level(), "military_power": 0.0}},
}

def _normalize_hq(data):
    result = deepcopy(DEFAULT_HQ)
    if not isinstance(data, dict): data = {}
    try: result["max_level"] = max(1, min(100, int(data.get("max_level",100))))
    except (TypeError, ValueError): result["max_level"] = 100
    if isinstance(data.get("build_cost"), dict):
        for k in result["build_cost"]:
            try:
                v=float(data["build_cost"].get(k,result["build_cost"][k]))
                if v>=0: result["build_cost"][k]=v
            except (TypeError,ValueError): pass
    for field in ("build_strength","build_military_power","build_completion_time","instant_finish_uranium_per_hour"):
        try:
            v=float(data.get(field,result[field]))
            if v>=0: result[field]=v
        except (TypeError,ValueError): pass
    levels = data.get("levels", {})
    if isinstance(levels, dict):
        for key, vals in levels.items():
            try: level=int(key)
            except (TypeError, ValueError): continue
            if not 2 <= level <= 100 or not isinstance(vals, dict): continue
            base=deepcopy(result["levels"].get(level,_default_hq_level()))
            for f in base:
                try:
                    v=float(vals.get(f,base[f]))
                except (TypeError,ValueError): continue
                if v>=0: base[f]=v
            result["levels"][level]=base
    template=deepcopy(result["levels"].get(2,_default_hq_level()))
    for level in range(2,101):
        if level not in result["levels"]:
            result["levels"][level]=deepcopy(template)
    return result

def get_hq_config(session):
    _migrate_completion_times_to_hours(session)
    row=session.scalar(select(BotSetting).where(BotSetting.key==HQ_KEY))
    if row is None: return _normalize_hq({})
    try: return _normalize_hq(json.loads(row.value))
    except Exception: return _normalize_hq({})

def save_hq_config(session, config):
    payload=_normalize_hq(config)
    row=session.scalar(select(BotSetting).where(BotSetting.key==HQ_KEY))
    if row is None: session.add(BotSetting(key=HQ_KEY,value=json.dumps(payload,ensure_ascii=False)))
    else: row.value=json.dumps(payload,ensure_ascii=False)
    return payload

# =========================================================
# 🚀 مدیریت موشک‌ها / فروشگاه
# =========================================================
MISSILES_KEY = "game_missiles_v1"

def _default_missiles():
    return {"items": []}

def get_missiles_config(session):
    row=session.scalar(select(BotSetting).where(BotSetting.key==MISSILES_KEY))
    if row is None: return deepcopy(_default_missiles())
    try:
        data=json.loads(row.value)
        if not isinstance(data,dict) or not isinstance(data.get("items"),list): return deepcopy(_default_missiles())
        changed=False
        for m in data.get("items",[]):
            if "max_level" not in m: m["max_level"]=100; changed=True
            if "hq_required" not in m: m["hq_required"]=1; changed=True
            if "active" not in m: m["active"]=False; changed=True
            if "arsenal_required" not in m: m["arsenal_required"]=1; changed=True
            if "operational_names" not in m or not isinstance(m.get("operational_names"), list): m["operational_names"]=[]; changed=True
            for base_key in ("base_cost", "base_power", "base_capacity", "base_target_time"):
                if base_key not in m:
                    m[base_key]=0.0; changed=True
            for legacy_key in ("power", "price", "capacity"):
                if legacy_key in m:
                    m.pop(legacy_key, None); changed=True
            levels=m.setdefault("levels",{})
            for _lvl in levels.values():
                if "loot_percent" not in _lvl:
                    _lvl["loot_percent"] = 0.0
                    changed = True
            ml=max(1,min(100,int(m.get("max_level",100) or 100)))
            # ظرفیت اشغال از این نسخه یک ویژگی کلی خود موشک است، نه ویژگی هر سطح.
            # برای داده‌های قدیمی، اگر ظرفیت پایه خالی باشد از ظرفیت سطح ۱ استفاده می‌کنیم
            # تا تنظیم قبلی از بین نرود؛ سپس ظرفیت‌های سطحی حذف می‌شوند.
            if float(m.get("base_capacity",0) or 0) <= 0:
                try:
                    legacy_cap = float((levels.get("1") or {}).get("capacity",0) or 0)
                except (TypeError, ValueError):
                    legacy_cap = 0.0
                if legacy_cap > 0:
                    m["base_capacity"] = legacy_cap
                    changed=True
            for i in range(1,ml+1):
                if str(i) not in levels:
                    levels[str(i)]={"hq_required":int(m.get("hq_required",1) or 1),"cost":0.0,"power":0.0,"target_time":0.0,"loot_percent":0.0}
                    changed=True
            for _lvl in levels.values():
                if "capacity" in _lvl:
                    _lvl.pop("capacity", None)
                    changed=True
                try:
                    new_tt = float(_lvl.get("target_time", 0) or 0)
                except (TypeError, ValueError):
                    new_tt = 0.0
                if _lvl.get("target_time") != new_tt:
                    _lvl["target_time"] = new_tt
                    changed=True
        if changed and row is not None:
            row.value=json.dumps(data,ensure_ascii=False)
            session.flush()
        return data
    except Exception:
        return deepcopy(_default_missiles())

def save_missiles_config(session, config):
    row=session.scalar(select(BotSetting).where(BotSetting.key==MISSILES_KEY))
    payload=json.dumps(config,ensure_ascii=False)
    if row is None: session.add(BotSetting(key=MISSILES_KEY,value=payload))
    else: row.value=payload
    return config


# =========================================================
# 🛡️ سپرهای دفاعی / فروشگاه
# =========================================================
SHIELD_KEY='game_shields_v1'


def _default():
    # Owner creates the actual shield products. Keep the store empty by default.
    return {'items': [], 'global_enabled': True, 'continental_enabled': True, 'auto_attack_threshold': 5, 'auto_shield_hours': 5.0, 'shield_attack_penalty_hours': 1.25}


def get_config(session):
    row=session.scalar(select(BotSetting).where(BotSetting.key==SHIELD_KEY))
    if not row:
        data=_default(); save_config(session,data); return data
    try: data=json.loads(row.value)
    except Exception: data=_default()
    if not isinstance(data,dict) or not isinstance(data.get('items'),list): data=_default()
    data.setdefault('global_enabled', True)
    data.setdefault('continental_enabled', True)
    data.setdefault('auto_attack_threshold', 5)
    data.setdefault('auto_shield_hours', 5.0)
    data.setdefault('shield_attack_penalty_hours', 1.25)
    changed=False
    for x in data['items']:
        x.setdefault('name','سپر جهانی' if x.get('type')=='global' else 'سپر قاره‌ای')
        x.setdefault('type','global'); x.setdefault('price',0.0); x.setdefault('active',False)
        if 'duration_hours' not in x:
            if 'duration_seconds' in x:
                try: x['duration_hours']=max(0.01,float(x.get('duration_seconds',86400) or 86400)/3600.0)
                except: x['duration_hours']=24.0
            else:
                x['duration_hours']=24.0
            changed=True
        if 'cooldown_hours' not in x:
            x['cooldown_hours']=0.0; changed=True
        if not x.get('id'): x['id']=f"shield_{len(data['items'])}"
        x['type']='continental' if x.get('type')=='continental' else 'global'
        try: x['price']=max(0.0,float(x.get('price',0) or 0))
        except: x['price']=0.0
        try: x['duration_hours']=max(0.01,float(x.get('duration_hours',24) or 24))
        except: x['duration_hours']=24.0
        try: x['cooldown_hours']=max(0.0,float(x.get('cooldown_hours',0) or 0))
        except: x['cooldown_hours']=0.0
    if changed: save_config(session,data)
    return data


def save_config(session,data):
    row=session.scalar(select(BotSetting).where(BotSetting.key==SHIELD_KEY))
    raw=json.dumps(data,ensure_ascii=False)
    if row is None: session.add(BotSetting(key=SHIELD_KEY,value=raw))
    else: row.value=raw
    session.flush(); return data


def get_items(session, typ=None, active_only=False):
    items=get_config(session).get('items',[])
    if typ in ('global','continental'):
        items=[x for x in items if x.get('type')==typ]
    if active_only:
        if typ in ('global','continental') and not bool(get_config(session).get(f'{typ}_enabled', True)):
            return []
        items=[x for x in items if bool(x.get('active'))]
    return items


def is_type_enabled(session, typ):
    if typ not in ('global','continental'):
        return False
    return bool(get_config(session).get(f'{typ}_enabled', True))


def get_item(session, item_id_or_type):
    # Backward compatible: a type returns the first active item of that type.
    cfg=get_config(session)
    value=str(item_id_or_type or '')
    if value in ('global','continental'):
        return next((x for x in cfg['items'] if x.get('type')==value and x.get('active')), None)
    return next((x for x in cfg['items'] if str(x.get('id'))==value), None)


def get_item_by_id(session, item_id):
    return next((x for x in get_config(session).get('items',[]) if str(x.get('id'))==str(item_id)), None)


def _shield_key(user_id,item_id,country_id=None):
    return f'active:{int(country_id)}:{item_id}' if country_id is not None else f'active:{int(user_id)}:{item_id}'


def _state(session):
    row=session.scalar(select(BotSetting).where(BotSetting.key=='shield_active_v1'))
    if not row: return {}
    try: return json.loads(row.value) or {}
    except: return {}


def _save_state(session,state):
    with _STATE_MUTATION_LOCK:
        row=session.scalar(select(BotSetting).where(BotSetting.key=='shield_active_v1'))
        raw=json.dumps(state,ensure_ascii=False)
        if row is None: session.add(BotSetting(key='shield_active_v1',value=raw))
        else: row.value=raw
        session.flush()


def cleanup(session):
    s=_state(session); now=time.time(); changed=False
    for k,v in list(s.items()):
        if float(v.get('expires_at',0) or 0)<=now:
            s.pop(k,None); changed=True
    if changed: _save_state(session,s)
    return s


def _cooldown_state(session):
    row=session.scalar(select(BotSetting).where(BotSetting.key=='shield_purchase_cooldown_v1'))
    if not row: return {}
    try: return json.loads(row.value) or {}
    except: return {}


def _save_cooldown_state(session,state):
    with _STATE_MUTATION_LOCK:
        row=session.scalar(select(BotSetting).where(BotSetting.key=='shield_purchase_cooldown_v1'))
        raw=json.dumps(state,ensure_ascii=False)
        if row is None: session.add(BotSetting(key='shield_purchase_cooldown_v1',value=raw))
        else: row.value=raw
        session.flush()

def purchase_cooldown_remaining(session,user_id,item_id,country_id=None):
    state=_cooldown_state(session); key=_shield_key(user_id,item_id,country_id); rec=state.get(key) or {}
    item=get_item_by_id(session,item_id)
    hours=float(item.get('cooldown_hours',0) or 0) if item else 0
    if hours<=0 or not rec.get('purchased_at'): return 0
    return max(0, int(float(rec['purchased_at']) + hours*3600 - time.time()))


def purchase(session,user_id,item_id,country):
    item=get_item_by_id(session,item_id)
    if not item or not bool(item.get('active')):
        return False,'این سپر در حال حاضر در فروشگاه فعال نیست.',None
    if not is_type_enabled(session, str(item.get('type') or '')):
        return False,'این نوع سپر در حال حاضر غیرفعال است.',None
    country_id=int(getattr(country,'id',0) or 0)
    scope_country_id = country_id if item.get('type') == 'continental' else None
    cooldown=purchase_cooldown_remaining(session,user_id,item_id,scope_country_id)
    if cooldown>0:
        h,rem=divmod(cooldown,3600); m,_=divmod(rem,60)
        return False,f'⏳ خرید دوباره این سپر تا {h} ساعت و {m} دقیقه دیگر امکان‌پذیر نیست.',None
    price=float(item.get('price',0) or 0)
    uranium=float(getattr(country,'uranium',0) or 0)
    infinite=bool(getattr(country,'infinite_uranium',False))
    if not infinite and uranium<price:
        return False,'❌ اورانیوم کافی نیست.',None
    if not infinite:
        country.uranium=uranium-price
    s=cleanup(session); now=time.time()
    duration=float(item.get('duration_hours',24) or 24)*3600
    # اگر کاربر از همین نوع سپر، سپر فعال دیگری داشته باشد، مدت خرید جدید
    # روی همان زمان باقی‌مانده اضافه می‌شود؛ خرید سپر جدید زمان قبلی را از بین نمی‌برد.
    same_type=[]
    cfg_items={str(x.get('id')):x for x in get_config(session).get('items',[])}
    for skey, rec in s.items():
        if int(rec.get('country_id',0) or 0) != int(scope_country_id or 0): continue
        exp=float(rec.get('expires_at',0) or 0)
        if exp<=now: continue
        rec_item=cfg_items.get(str(rec.get('item_id')))
        rec_type=rec_item.get('type') if rec_item else rec.get('type')
        if rec_type==item.get('type'):
            same_type.append((skey,rec,exp))
    if same_type:
        key,old,_=max(same_type,key=lambda x:x[2])
        expires=max(now,float(old.get('expires_at',0) or 0))+duration
        old['expires_at']=expires
        old.setdefault('purchased_at',now)
    else:
        key=_shield_key(user_id,item_id,scope_country_id)
        old=s.get(key) or {}
        old_exp=float(old.get('expires_at',0) or 0)
        expires=max(now,old_exp)+duration
        s[key]={'user_id':int(user_id),'country_id':scope_country_id,'item_id':str(item_id),'type':item.get('type'),'expires_at':expires,'purchased_at':now}
    _save_state(session,s)
    cd=_cooldown_state(session); cd[_shield_key(user_id,item_id,scope_country_id)]={'user_id':int(user_id),'country_id':scope_country_id,'item_id':str(item_id),'purchased_at':now}; _save_cooldown_state(session,cd)
    session.commit()
    return True,'',expires



def reset_purchase_limitations(session, user_id, country_id=None):
    """تمام محدودیت‌های خرید سپر یک کاربر را صفر می‌کند."""
    state=_cooldown_state(session)
    uid=int(user_id)
    removed=0
    for key, rec in list(state.items()):
        if int(rec.get('user_id',0) or 0)==uid and (country_id is None or int(rec.get('country_id',0) or 0)==int(country_id)):
            state.pop(key,None); removed += 1
    _save_cooldown_state(session,state)
    session.commit()
    return removed

def adjust_active_shield_time(session, user_id, shield_type, delta_hours, country_id=None):
    """زمان سپر را تغییر می‌دهد؛ جهانی در سطح کاربر و قاره‌ای در سطح کشور/گروه است."""
    if shield_type not in {'global','continental'}: return False, 0, None
    delta=float(delta_hours or 0)
    if delta == 0: return False, 0, None
    scope_country_id = int(country_id) if shield_type == 'continental' and country_id is not None else None
    s=cleanup(session); now=time.time(); candidates=[]
    cfg={str(x.get('id')):x for x in get_config(session).get('items',[])}
    for key,v in s.items():
        if int(v.get('user_id',0) or 0)!=int(user_id): continue
        if shield_type == 'continental' and scope_country_id is not None and int(v.get('country_id',0) or 0)!=scope_country_id: continue
        if shield_type == 'global' and v.get('country_id') is not None: continue
        expires=float(v.get('expires_at',0) or 0)
        if expires<=now: continue
        item=cfg.get(str(v.get('item_id'))); typ=(item.get('type') if item else v.get('type'))
        if typ==shield_type: candidates.append((key,v,expires,item))
    if not candidates:
        if delta < 0: return False, 0, None
        key=_shield_key(user_id,f'__admin_{shield_type}__',scope_country_id)
        expires=now+delta*3600
        s[key]={'user_id':int(user_id),'country_id':scope_country_id,'item_id':f'__admin_{shield_type}__','type':shield_type,'name':('سپر جهانی' if shield_type=='global' else 'سپر قاره‌ای'),'expires_at':expires,'purchased_at':now,'admin_granted':True}
        _save_state(session,s); session.commit(); return True, delta*3600, expires
    key,v,old,item=max(candidates,key=lambda x:x[2]); new=max(now,old+delta*3600)
    if new<=now: s.pop(key,None); actual=old-now; expires=None
    else: v['expires_at']=new; actual=new-old; expires=new
    _save_state(session,s); session.commit(); return True, actual, expires

def active_for_target(session,user_id,attacker_continent=None,target_continent=None,country_id=None):
    s=cleanup(session); now=time.time(); cfg={str(x.get('id')):x for x in get_config(session).get('items',[])}; out=[]
    for k,v in s.items():
        if int(v.get('user_id',0) or 0)!=int(user_id): continue
        if float(v.get('expires_at',0) or 0)<=now: continue
        item=cfg.get(str(v.get('item_id')))
        # Removed store items no longer provide a purchased shield; internal/admin/auto shields remain valid.
        if item is None and not str(v.get('item_id','')).startswith(('__admin_','__auto_')):
            continue
        typ=(item.get('type') if item else v.get('type'))
        if country_id is not None:
            # حمله داخل گروه فقط سپر قاره‌ای همان کشور/گروه را بررسی می‌کند.
            if typ!='continental': continue
            if int(v.get('country_id',0) or 0)!=int(country_id): continue
            if attacker_continent is not None and target_continent is not None and str(attacker_continent)!=str(target_continent): continue
        else:
            # سپر جهانی در سطح کل ربات است و در حمله گروهی دخالت نمی‌کند.
            if typ!='global' or v.get('country_id') is not None: continue
        vv=dict(v); vv['name']=(item.get('name') if item else v.get('name','سپر')); vv['type']=typ; out.append(vv)
    if not out: return None
    return max(out,key=lambda x: float(x.get('expires_at',0) or 0))

def remaining_text(expires_at):
    sec=max(0,int(float(expires_at)-time.time()))
    h,rem=divmod(sec,3600); m,_=divmod(rem,60)
    return f'{h} ساعت و {m} دقیقه'



SHIELD_AUTO_KEY='shield_auto_attack_v1'

def get_shield_auto_settings(session):
    cfg=get_config(session)
    return {
        'auto_attack_threshold': max(1,int(cfg.get('auto_attack_threshold',5) or 5)),
        'auto_shield_hours': max(0.01,float(cfg.get('auto_shield_hours',5) or 5)),
        'shield_attack_penalty_hours': max(0.0,float(cfg.get('shield_attack_penalty_hours',1.25) or 1.25)),
    }

def save_shield_auto_setting(session,key,value):
    cfg=get_config(session); cfg[key]=value; save_config(session,cfg); return cfg

def _auto_attack_state(session):
    row=session.scalar(select(BotSetting).where(BotSetting.key==SHIELD_AUTO_KEY))
    if not row: return {}
    try: return json.loads(row.value) or {}
    except Exception: return {}

def _save_auto_attack_state(session,state):
    with _STATE_MUTATION_LOCK:
        row=session.scalar(select(BotSetting).where(BotSetting.key==SHIELD_AUTO_KEY)); raw=json.dumps(state,ensure_ascii=False)
        if row is None: session.add(BotSetting(key=SHIELD_AUTO_KEY,value=raw))
        else: row.value=raw
        session.flush()

def register_group_attack_received(session,target_user_id,group_id,country_id=None):
    st=_auto_attack_state(session)
    scope=int(country_id) if country_id is not None else int(target_user_id)
    key=f'{int(group_id)}:{scope}'
    settings=get_shield_auto_settings(session)
    now=time.time()
    window=settings['auto_shield_hours']*3600.0

    raw=st.get(key)
    if isinstance(raw, dict):
        started_at=float(raw.get('started_at', now) or now)
        count=int(raw.get('count', 0) or 0)
    else:
        # سازگاری با شمارنده‌های قدیمی
        started_at=now
        count=int(raw or 0)

    # شمارش اتک‌ها فقط داخل پنجره «مدت سپر رایگان» معتبر است.
    # اگر پنجره قبلی تمام شده باشد، اتک فعلی شروع‌کننده شمارش جدید است.
    if now-started_at >= window:
        started_at=now
        count=0

    count += 1
    threshold=settings['auto_attack_threshold']
    if count < threshold:
        st[key]={'count':count,'started_at':started_at}
        _save_auto_attack_state(session,st)
        return False,None

    st.pop(key,None)
    _save_auto_attack_state(session,st)
    s=cleanup(session)
    skey=_shield_key(target_user_id,'__auto_continental__',country_id) if country_id is not None else f'active:{int(target_user_id)}:__auto_continental__'
    old=s.get(skey) or {}
    expires=max(now,float(old.get('expires_at',0) or 0))+settings['auto_shield_hours']*3600
    s[skey]={'user_id':int(target_user_id),'country_id':int(country_id) if country_id is not None else None,'item_id':'__auto_continental__','type':'continental','name':'سپر خودکار قاره‌ای','expires_at':expires,'purchased_at':now,'automatic':True}
    _save_state(session,s)
    return True,expires

def consume_shield_time_for_group_attack(session,user_id,country_id=None):
    settings=get_shield_auto_settings(session); penalty=settings['shield_attack_penalty_hours']*3600
    if penalty<=0: return 0
    s=cleanup(session); candidates=[]
    for k,v in s.items():
        if (int(v.get('country_id',0) or 0)==int(country_id) if country_id is not None else int(v.get('user_id',0) or 0)==int(user_id)) and float(v.get('expires_at',0) or 0)>time.time():
            candidates.append((k,v))
    if not candidates: return 0
    key,v=min(candidates,key=lambda kv: float(kv[1].get('expires_at',0) or 0))
    old=float(v.get('expires_at',0) or 0); new=max(time.time(),old-penalty)
    if new<=time.time(): s.pop(key,None)
    else: v['expires_at']=new
    _save_state(session,s); return max(0,int(old-new))

# ================================================================
# 🏦 بانک مرکزی — تنظیمات و عملیات پایه
# ================================================================
BANK_KEY = "central_bank_v1"

def _default_bank_config():
    levels = {}
    for level in range(1, 101):
        levels[str(level)] = {
            "build_cost": {"money": 0, "metal": 0, "fuel": 0, "uranium": 0},
            "build_time_hours": 0,
            "upgrade_cost": {"money": 0, "metal": 0, "fuel": 0, "uranium": 0},
            "upgrade_time_hours": 0,
            "required_hq_level": 1,
            "deposit_capacity": 0,
            "deposit_hourly_profit_percent": 0,
            "loan": {"min_amount": 0, "max_amount": 0, "min_interest_percent": 0, "max_interest_percent": 0, "min_installments": 1, "max_installments": 1, "max_active_loans": 1, "bank_unlock_cost": 0},
            "tax_min": 0,
            "tax_max": 0,
            "active": True,
            "investments": [],
        }
    return {"max_level": 100, "population_initial": 1_000_000, "population_growth_per_hour": 0, "levels": levels, "instant_finish_uranium_per_hour": 0}

def get_bank_config(session):
    row=session.scalar(select(BotSetting).where(BotSetting.key==BANK_KEY))
    if row is None:
        cfg=_default_bank_config(); session.add(BotSetting(key=BANK_KEY,value=json.dumps(cfg,ensure_ascii=False))); session.flush(); return cfg
    try: cfg=json.loads(row.value)
    except Exception: cfg=_default_bank_config()
    if not isinstance(cfg,dict): cfg=_default_bank_config()
    cfg.setdefault("max_level",100); cfg.setdefault("population_initial",1_000_000); cfg.setdefault("population_growth_per_hour",0); cfg.setdefault("instant_finish_uranium_per_hour",0); cfg.setdefault("levels",{})
    defaults = _default_bank_config()["levels"]
    for level in range(1,101):
        current = cfg["levels"].setdefault(str(level), defaults[str(level)])
        current.setdefault("deposit_capacity", 0)
        current.setdefault("deposit_hourly_profit_percent", 0)
        legacy_unlock=current.pop("bank_unlock_cost", None)
        current.setdefault("investments", [])
        loan_defaults = {"min_amount": 0, "max_amount": 0, "min_interest_percent": 0, "max_interest_percent": 0, "min_installments": 1, "max_installments": 1, "max_active_loans": 1, "bank_unlock_cost": 0}
        loan = current.setdefault("loan", {})
        if not isinstance(loan, dict):
            loan = {}; current["loan"] = loan
        for key, default in loan_defaults.items():
            loan.setdefault(key, default)
        if legacy_unlock is not None and float(loan.get("bank_unlock_cost",0) or 0) == 0:
            loan["bank_unlock_cost"] = max(0.0, float(legacy_unlock or 0))
        # Legacy global/basic loan settings are migrated into level 1 only when
        # the new per-level values are still empty.
        if level == 1:
            legacy = cfg.get("loan", {}) if isinstance(cfg.get("loan", {}), dict) else {}
            if legacy and not any(float(loan.get(k, 0) or 0) for k in ("min_amount", "max_amount")):
                loan["min_amount"] = float(legacy.get("min_amount", legacy.get("min", 0)) or 0)
                loan["max_amount"] = float(legacy.get("max_amount", legacy.get("max", legacy.get("max_amount", 0))) or 0)
            base_interest = float(legacy.get("interest_percent", 0) or 0)
            if base_interest and not float(loan.get("min_interest_percent", 0) or 0):
                loan["min_interest_percent"] = base_interest; loan["max_interest_percent"] = base_interest
            if legacy.get("installments") and int(loan.get("min_installments", 1) or 1) == 1:
                loan["min_installments"] = int(legacy.get("installments", 1) or 1); loan["max_installments"] = int(legacy.get("installments", 1) or 1)
    # Migrate the old global investment list into every level once. Investments
    # are now owned by each bank level (including level 1/build mode).
    legacy_investments = cfg.pop("investments", []) or []
    for level in range(1, 101):
        current = cfg["levels"][str(level)]
        if not current.get("investments") and legacy_investments:
            current["investments"] = deepcopy(legacy_investments)
        for plan in current.get("investments", []) or []:
            if not isinstance(plan, dict):
                continue
            plan.setdefault("max_per_user", 1)
            plan.setdefault("allow_multiple_active", False)
            plan.setdefault("return_type", "money")
            if str(plan.get("return_type")) in {"defense","drones","missiles"}:
                plan["return_type"]="money"
            for _k in ("profit_min_value","profit_max_value","loss_min_value","loss_max_value"):
                plan.setdefault(_k, 0)
            # New two-bound outcome ranges. Migrate old single values to fixed ranges.
            old_profit=float(plan.get("profit_percent", 0) or 0)
            old_loss=float(plan.get("loss_percent", 0) or 0)
            plan.setdefault("profit_min_percent", old_profit)
            plan.setdefault("profit_max_percent", old_profit)
            plan.setdefault("loss_min_percent", old_loss)
            plan.setdefault("loss_max_percent", old_loss)
            plan.setdefault("profit_percent", float(plan.get("profit_max_percent", old_profit) or 0))
            plan.setdefault("loss_percent", float(plan.get("loss_max_percent", old_loss) or 0))
            if "risk" not in plan:
                diff=str(plan.get("difficulty", "متوسط"))
                plan["risk"]={"آسان":"کم", "سخت":"زیاد"}.get(diff, "متوسط")
            plan.pop("difficulty", None)
    # The old global loan object is no longer a source of truth. Level settings
    # are authoritative; keep the legacy object only as a migration source above.
    cfg.pop("loan", None)
    return cfg

def save_bank_config(session,cfg):
    row=session.scalar(select(BotSetting).where(BotSetting.key==BANK_KEY))
    if row is None: row=BotSetting(key=BANK_KEY,value="{}"); session.add(row)
    row.value=json.dumps(cfg,ensure_ascii=False); session.flush()

def bank_level_config(session,level):
    cfg=get_bank_config(session); return cfg["levels"].get(str(int(level)),{})

def bank_max_level(session): return max(0,min(100,int(get_bank_config(session).get("max_level",100) or 0)))

def ensure_bank_account(session,country):
    from database.models import BankAccount
    acc=session.scalar(select(BankAccount).where(BankAccount.country_id==country.id))
    if acc is None:
        cfg=get_bank_config(session); acc=BankAccount(country_id=country.id,citizens=int(cfg.get("population_initial",1_000_000) if cfg.get("population_initial",1_000_000) is not None else 1_000_000)); session.add(acc); session.flush()
    return acc

def accrue_bank_profit(session,country):
    from datetime import datetime
    acc=ensure_bank_account(session,country); now=datetime.utcnow()
    if acc.deposit_principal<=0:
        acc.deposit_last_accrual_at=now; return acc
    level=max(1,int(country.bank_level or 1)); rate=float(bank_level_config(session,level).get("deposit_hourly_profit_percent",0) or 0)
    elapsed=max(0,(now-acc.deposit_last_accrual_at).total_seconds())/3600.0
    if elapsed>0 and rate>0: acc.accrued_profit += acc.deposit_principal*(rate/100.0)*elapsed
    acc.deposit_last_accrual_at=now
    return acc

def accrue_bank_tax(session,country):
    """Accrue tax continuously; configured tax is charged per 1,000 citizens."""
    from datetime import datetime
    acc=ensure_bank_account(session,country); now=datetime.utcnow()
    last=acc.tax_last_accrual_at or now
    elapsed=max(0.0,(now-last).total_seconds())
    daily=(max(0.0,float(acc.citizens or 0))/1000.0)*max(0.0,float(acc.tax_per_citizen or 0))
    if elapsed>0 and daily>0:
        acc.accrued_tax += daily*(elapsed/86400.0)
    acc.tax_last_accrual_at=now
    return acc

def bank_withdraw_tax(session,country):
    acc=accrue_bank_tax(session,country)
    amount=max(0.0,float(acc.accrued_tax or 0.0))
    acc.accrued_tax=0.0
    country.money=float(country.money or 0.0)+amount
    return amount

def bank_deposit_capacity(session,country):
    return float(bank_level_config(session,max(1,int(country.bank_level or 1))).get("deposit_capacity",0) or 0)

def bank_deposit(session,country,amount):
    amount=float(amount); acc=accrue_bank_profit(session,country); cap=bank_deposit_capacity(session,country)
    if amount<=0: return False,"مبلغ نامعتبر است."
    if cap<=0: return False,"ظرفیت سپرده برای این سطح تنظیم نشده است."
    if acc.deposit_principal+amount>cap:
        return False,f"ظرفیت سپرده تکمیل است. حداکثر قابل سپرده‌گذاری: {max(0,cap-acc.deposit_principal):,.0f}"
    if not country.infinite_money and float(country.money or 0)<amount: return False,"پول کافی ندارید."
    if not country.infinite_money: country.money-=amount
    acc.deposit_principal+=amount
    return True,"سپرده با موفقیت ثبت شد."

def bank_withdraw_principal(session,country):
    """Return only the deposited principal; accrued profit remains claimable."""
    acc=accrue_bank_profit(session,country)
    amount=max(0.0,float(acc.deposit_principal or 0.0))
    acc.deposit_principal=0.0
    country.money=float(country.money or 0.0)+amount
    return amount

def bank_withdraw_profit(session,country):
    acc=accrue_bank_profit(session,country); amount=max(0,float(acc.accrued_profit or 0)); acc.accrued_profit=0; country.money+=amount; return amount

def bank_withdraw_all(session,country):
    acc=accrue_bank_profit(session,country); amount=max(0,float(acc.deposit_principal or 0)+float(acc.accrued_profit or 0)); acc.deposit_principal=0; acc.accrued_profit=0; country.money+=amount; return amount


def bank_instant_finish_uranium_cost(country, session):
    from services.game import construction_remaining
    remaining, _ = construction_remaining(country, "bank")
    if remaining <= 0:
        return 0.0
    cfg = get_bank_config(session)
    rate = max(0.0, float(cfg.get("instant_finish_uranium_per_hour", 0) or 0))
    if rate <= 0:
        return 0.0
    import math
    return math.ceil((remaining / 3600.0) * rate * 100.0) / 100.0

def cancel_bank_construction(country, session):
    """Cancel active Central Bank construction/upgrade and refund 50% of paid resources."""
    from services.game import construction_remaining, add_resource
    remaining, encoded_target = construction_remaining(country, "bank")
    if remaining <= 0 or not encoded_target:
        return False, "NOT_IN_PROGRESS"
    target = abs(int(encoded_target))
    if target <= 1 and int(country.bank_level or 0) <= 0:
        cfg = bank_level_config(session, 1)
        cost = dict(cfg.get("build_cost", {}) or {})
    else:
        current = int(country.bank_level or 0)
        cfg = bank_level_config(session, target)
        cost = dict(cfg.get("upgrade_cost", {}) or {})
    refund = {}
    for resource, amount in cost.items():
        amount = float(amount or 0)
        if amount > 0:
            refunded = amount * 0.5
            add_resource(country, resource, refunded)
            refund[resource] = refunded
    from services.game import _construction_fields
    until_field, target_field = _construction_fields("bank")
    setattr(country, until_field, None)
    setattr(country, target_field, None)
    try:
        from services.construction_teams import release_team
        release_team(session, country, "bank")
    except Exception:
        pass
    return True, refund


def finish_bank_construction_now(country, session):
    from services.game import finalize_construction, resource_available
    cost = bank_instant_finish_uranium_cost(country, session)
    if cost <= 0 or not resource_available(country, "uranium", cost):
        return False, cost
    if not getattr(country, "infinite_uranium", False):
        country.uranium = max(0.0, float(country.uranium or 0) - cost)
    finalize_construction(country)
    return int(country.bank_level or 0) > 0, cost
