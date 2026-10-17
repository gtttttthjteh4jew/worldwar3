import json
from datetime import datetime
from sqlalchemy import select, func
from database.models import BotSetting

PREFIX='enigma:'

def get_setting(session,key,default=None):
    row=session.scalar(select(BotSetting).where(BotSetting.key==PREFIX+key))
    if not row: return default
    try: return json.loads(row.value)
    except Exception: return row.value

def set_setting(session,key,value):
    row=session.scalar(select(BotSetting).where(BotSetting.key==PREFIX+key))
    raw=json.dumps(value,ensure_ascii=False)
    if row: row.value=raw
    else: session.add(BotSetting(key=PREFIX+key,value=raw))
    session.commit()

def default_settings():
    return {
      'enabled': False, 'weekly_per_country': 3, 'send_days':[0,1,3], 'random_days':True,
      'min_hour':'10:00','max_hour':'23:00','min_gap_hours':6,
      # مدت باقی‌ماندن جعبه قبل از باز شدن؛ بعد از این مدت خود جعبه حذف می‌شود.
      'box_expiry_minutes':60,
      'max_attempts':3,'unlimited_attempts':False,
      # این سه رفتار بخشی از منطق ثابت انیگما هستند و از پنل Owner قابل خاموش/روشن کردن نیستند.
      'no_repeat':True,'active_country_only':True,'speed_bonus_enabled':True,
      'levels':{
        'easy':{'enabled':True,'weight':50,'min_reward':100,'max_reward':300,'speed_factor':0.20,'time_minutes':5,'operation_seconds':300,'question_display_seconds':30},
        'medium':{'enabled':True,'weight':35,'min_reward':300,'max_reward':700,'speed_factor':0.30,'time_minutes':8,'operation_seconds':480,'question_display_seconds':30},
        'hard':{'enabled':True,'weight':15,'min_reward':700,'max_reward':1500,'speed_factor':0.50,'time_minutes':12,'operation_seconds':720,'question_display_seconds':30},
      },
      'types':{
        'letter_shift':{'enabled':True,'weight':25},'morse':{'enabled':True,'weight':25},
        'memory_multi':{'enabled':True,'weight':25},'memory_text':{'enabled':True,'weight':25}
      },
    }

def ensure_settings(session):
    current=get_setting(session,'config')
    defaults=default_settings()
    if not isinstance(current,dict):
        current=defaults
    else:
        # تنظیمات جدید را بدون از بین بردن مقادیر قبلی اضافه/ترمیم می‌کنیم.
        for key,value in defaults.items():
            if key not in current:
                current[key]=value
        for section in ('levels','types'):
            current.setdefault(section,{})
            for key,value in defaults[section].items():
                current[section].setdefault(key, value.copy())
                if isinstance(value,dict):
                    for f,fv in value.items(): current[section][key].setdefault(f,fv)
        # هر نوع چالش تنظیمات مستقل سطح‌های خودش را دارد.
        for typ in defaults['types']:
            current['types'].setdefault(typ, defaults['types'][typ].copy())
            current['types'][typ].setdefault('levels', {})
            for lev, base in defaults['levels'].items():
                current['types'][typ]['levels'].setdefault(lev, base.copy())
                for f, fv in base.items():
                    current['types'][typ]['levels'][lev].setdefault(f, fv)
        # زمان عملیات پاسخگویی از این نسخه بر حسب ثانیه است. برای تنظیمات قدیمی،
        # مقدار دقیقه‌ای قبلی یک‌بار به ثانیه تبدیل می‌شود.
        for lev, lv in current.get('levels', {}).items():
            if 'operation_seconds' not in lv:
                try: lv['operation_seconds']=max(1,int(float(lv.get('time_minutes',1) or 1)*60))
                except Exception: lv['operation_seconds']=60
        for typ_cfg in current.get('types', {}).values():
            for lev, lv in typ_cfg.get('levels', {}).items():
                if 'operation_seconds' not in lv:
                    try: lv['operation_seconds']=max(1,int(float(lv.get('time_minutes',1) or 1)*60))
                    except Exception: lv['operation_seconds']=60

        # زمان نمایش پرسش از این نسخه در سطح «نوع + سطح» نگهداری می‌شود، نه داخل مأموریت.
        missions = get_setting(session, 'missions', []) or []
        for typ, typ_cfg in current.get('types', {}).items():
            for lev, lv in typ_cfg.get('levels', {}).items():
                if 'question_display_seconds' not in lv:
                    candidates = [m.get('display_seconds') for m in missions
                                  if isinstance(m, dict) and m.get('type') == typ
                                  and m.get('level', 'easy') == lev
                                  and m.get('display_seconds') is not None]
                    try:
                        lv['question_display_seconds'] = max(0, int(float(candidates[0]))) if candidates else 30
                    except Exception:
                        lv['question_display_seconds'] = 30
        # پیام‌های قابل ویرایش Owner در نسخه‌های قبلی دیگر استفاده نمی‌شوند.
        current.pop('messages',None)
        current.pop('expiry_minutes',None)
    # رفتارهای ثابت انیگما: عدم تکرار مأموریت، فقط کشور فعال و پاداش سرعت همیشه فعال.
    current['no_repeat'] = True
    current['active_country_only'] = True
    current['speed_bonus_enabled'] = True
    set_setting(session,'config',current)
    return current
