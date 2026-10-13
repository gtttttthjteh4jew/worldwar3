import random, uuid
from html import escape
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func
from database.models import User, UserCountry, Country
from .database import get_setting,set_setting,ensure_settings
from .challenges import LEVEL_NAMES,pick_weighted,pick_mission,ensure_missions
from .keyboards import box_keyboard,answer_keyboard
from .messages import BOX, START, SUCCESS, FAIL, EXPIRE, WRONG

STATUS_PENDING='PENDING'; STATUS_ACTIVE='ACTIVE'; STATUS_COMPLETED='COMPLETED'; STATUS_FAILED='FAILED'; STATUS_EXPIRED='EXPIRED'

def now(): return datetime.utcnow()

def _dt(value):
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    if value is None:
        raise ValueError('datetime value is missing')
    return datetime.fromisoformat(str(value)).replace(tzinfo=None)

def state(session): return get_setting(session,'state',{}) or {}
def save_state(session,s):
    # تاریخچه باید همیشه آخرین وضعیت عملیات را داشته باشد؛ چون آمار فقط از history خوانده می‌شود.
    history=s.setdefault('history',[])
    by_token={str(x.get('token')): x for x in history if x.get('token')}
    for token, rec in (s.get('active') or {}).items():
        h=by_token.get(str(token))
        if h is None:
            history.append(dict(rec))
        elif h is not rec:
            h.update(rec)
    set_setting(session,'state',s)

def _week_start_utc(dt=None):
    dt = dt or now()
    # Saturday is the first day of the game's weekly cycle.
    saturday_offset = (dt.weekday() + 2) % 7
    return dt.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=saturday_offset)

def weekly_id(dt=None):
    return _week_start_utc(dt).strftime('%Y-%m-%d')

def _country_users(session,country,active_only=True):
    q=select(User).join(UserCountry,UserCountry.user_id==User.id).where(UserCountry.country_id==country.id,User.is_banned==False)
    if active_only: q=q.where(User.default_country_id==country.id)
    rows=session.execute(q).scalars().all()
    return rows

def _week_count(s,cid): return sum(1 for x in s.get('history',[]) if x.get('country_id')==cid and x.get('week_id')==weekly_id())

def create_pending(session,user,country,bot):
    cfg=ensure_settings(session); s=state(session)
    token=uuid.uuid4().hex[:16]
    cycle=int(s.get('mission_cycle',0) or 0)
    rec={'token':token,'user_id':user.telegram_id,'country_id':country.id,'status':STATUS_PENDING,'created_at':now().isoformat(),'week_id':weekly_id(),'cycle':cycle,'used_missions':[]}
    s.setdefault('active',{})[token]=rec; s.setdefault('history',[]).append(rec); save_state(session,s)
    return token,BOX

def start(session,token,user_id):
    cfg=ensure_settings(session); s=state(session); rec=s.get('active',{}).get(token)
    if not rec or int(rec['user_id'])!=int(user_id): return None,'این عملیات برای شما نیست.'
    if rec['status']!=STATUS_PENDING: return None,'این عملیات قبلاً شروع شده یا بسته شده است.'
    country=session.get(Country,int(rec.get('country_id',0)))
    user=session.scalar(select(User).where(User.telegram_id==int(user_id)))
    if not country or not user: return None,'اطلاعات کشور یا کاربر پیدا نشد.'
    if int(user.default_country_id or 0)!=int(country.id):
        return None,'این کشور دیگر کشور فعال شما نیست.'
    # A country/user may not have two simultaneous انیگما operations.
    for other in s.get('active',{}).values():
        if other is rec: continue
        if int(other.get('user_id',0))==int(user_id) and other.get('status') in {STATUS_PENDING,STATUS_ACTIVE}:
            return None,'شما یک عملیات انیگما باز دارید.'
    cycle=int(s.get('mission_cycle',0) or 0)
    used=[x.get('mission_id') for x in s.get('history',[]) if int(x.get('user_id',0))==int(user_id) and x.get('mission_id') is not None and int(x.get('cycle',0) or 0) == cycle]
    # فقط ترکیب‌هایی را وارد قرعه می‌کنیم که واقعاً مأموریت فعال دارند؛
    # در نتیجه داشتن یک مأموریت ثبت‌شده دیگر به‌خاطر انتخاب تصادفی سطح/نوع بی‌استفاده نمی‌شود.
    available=[]
    for key,value in cfg['types'].items():
        if not value.get('enabled',True): continue
        levels=value.get('levels') or cfg['levels']
        for lev_key,lev_value in levels.items():
            if not lev_value.get('enabled',True): continue
            mission=pick_mission(session,cfg,used,lev_key,key)
            if mission:
                available.append(({'key':key,**value},{'key':lev_key,**lev_value},mission))
    if not available:
        return None,'هیچ مأموریت فعال و قابل انتخابی برای تنظیمات فعلی وجود ندارد.'
    choices=[]
    for typ_candidate,lev_candidate,mission in available:
        weight=max(0.0,float(typ_candidate.get('weight',1) or 0))*max(0.0,float(lev_candidate.get('weight',1) or 0))
        choices.append((typ_candidate,lev_candidate,mission,weight))
    positive=[x for x in choices if x[3]>0]
    chosen=random.choices(positive if positive else choices,weights=[x[3] for x in (positive if positive else choices)],k=1)[0]
    typ,lev,mission=chosen[:3]
    now_dt=now()
    level_seconds=max(1,float(lev.get('operation_seconds', float(lev.get('time_minutes',1) or 1)*60) or 1))
    total_seconds=max(1,float(lev.get('operation_seconds', level_seconds) or level_seconds))
    display_seconds=max(0,int(float(lev.get('question_display_seconds',30) or 0)))
    rec.update({'status':STATUS_ACTIVE,'level':lev['key'],'mission_id':mission['id'],'type':mission['type'],'answer':mission['answer'],'hint':mission.get('hint',''),'question_display_seconds':display_seconds,'question_until':(now_dt+timedelta(seconds=display_seconds)).isoformat() if display_seconds else now_dt.isoformat(),'answer_panel':False,'start_time':now_dt.isoformat(),'expiry_at':None,'attempts':0,'input':''})
    save_state(session,s)
    type_name={'letter_shift':'جابه‌جایی حروف','morse':'مورس','memory_multi':'حفظ چند اطلاعات','memory_text':'حفظ اطلاعات در متن'}.get(mission.get('type'),mission.get('type',''))
    text=(START+f"\n\n╭━━━━━━━━━━━━━━━━━━━━╮\n"
          f"🧩 <b>دسته چالش:</b> {type_name}\n"
          f"🎚 <b>سطح:</b> {LEVEL_NAMES[lev['key']]}\n"
          f"👁 <b>زمان دیدن پرسش:</b> {display_seconds} ثانیه\n"
          f"╰━━━━━━━━━━━━━━━━━━━━╯\n\n"
          f"❓ <b>سؤال مأموریت</b>\n{mission['prompt']}")
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    question_markup=InlineKeyboardMarkup([[InlineKeyboardButton('➡️ رفتن به پنل پاسخگویی',callback_data=f'enigma:answerpanel:{token}')]])
    return {'text':text,'markup':question_markup},None

def reveal_answer_panel(session, token, user_id):
    s=state(session); rec=s.get('active',{}).get(token)
    if not rec or rec.get('status') != STATUS_ACTIVE or int(rec.get('user_id',0)) != int(user_id):
        return None
    if not rec.get('answer_panel'):
        panel_now=now()
        rec['answer_panel']=True
        rec['answer_panel_at']=panel_now.isoformat()
        lev_cfg=(ensure_settings(session).get('types',{}).get(rec.get('type'),{}).get('levels') or ensure_settings(session).get('levels',{})).get(rec.get('level'), {})
        total_seconds=max(1,float(lev_cfg.get('operation_seconds', float(lev_cfg.get('time_minutes',1) or 1)*60) or 1))
        rec['start_time']=panel_now.isoformat()
        rec['expiry_at']=(panel_now+timedelta(seconds=total_seconds)).isoformat()
        rec['question_until']=panel_now.isoformat()
    save_state(session,s)
    return rec

def render_answer_panel(session, token, user_id):
    s=state(session); rec=s.get('active',{}).get(token)
    if not rec or rec.get('status') != STATUS_ACTIVE or int(rec.get('user_id',0)) != int(user_id): return None
    type_name={'letter_shift':'جابه‌جایی حروف','morse':'مورس','memory_multi':'حفظ چند اطلاعات','memory_text':'حفظ اطلاعات در متن'}.get(rec.get('type'),rec.get('type',''))
    level_name=LEVEL_NAMES.get(rec.get('level'),rec.get('level',''))
    hint=rec.get('hint') or 'راهنمایی برای این مأموریت ثبت نشده است.'
    lev_cfg=(ensure_settings(session).get('types',{}).get(rec.get('type'),{}).get('levels') or ensure_settings(session).get('levels',{})).get(rec.get('level'), {})
    operation_seconds=max(1,int(float(lev_cfg.get('operation_seconds', float(lev_cfg.get('time_minutes',1) or 1)*60) or 1)))
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    entered=escape(str(rec.get('input','') or '')) or '—'
    return {'text':(f"📡 <b>پنل پاسخگویی انیگما</b>\n\n"
          f"╭━━━━━━━━━━━━━━━━━━━━╮\n"
          f"🧩 <b>دسته چالش:</b> {type_name}\n"
          f"🎚 <b>سطح:</b> {level_name}\n"
          f"⏱ <b>زمان عملیات:</b> {operation_seconds} ثانیه\n"
          f"💡 <b>راهنمایی:</b> {hint}\n"
          f"╰━━━━━━━━━━━━━━━━━━━━╯\n\n"
          f"⌨️ <b>پاسخ فعلی شما</b>\n"
          f"┌──────────────────┐\n"
          f"│ <code>{entered}</code>\n"
          f"└──────────────────┘"), 'markup':answer_keyboard(token)}

def key(session,token,user_id,k):
    s=state(session); rec=s.get('active',{}).get(token)
    if not rec or rec['status']!=STATUS_ACTIVE or int(rec['user_id'])!=int(user_id): return None
    if not rec.get('answer_panel'):
        return None
    val=rec.get('input','')
    if k=='BACK': val=val[:-1]
    elif k=='CLEAR': val=''
    elif k=='SPACE': val+=' '
    elif len(k)==1 and (k.isalpha() or k.isdigit()): val+=k.upper()
    rec['input']=val; save_state(session,s); return val

def submit(session,token,user_id):
    cfg=ensure_settings(session); s=state(session); rec=s.get('active',{}).get(token)
    if not rec or int(rec['user_id'])!=int(user_id): return None,'این عملیات برای شما نیست.'
    if rec['status']!=STATUS_ACTIVE: return None,'این عملیات دیگر فعال نیست.'
    # تأیید بدون پاسخ همیشه باید پیام «پاسخ را وارد کنید» بدهد؛
    # این بررسی عمداً قبل از کنترل expiry_at انجام می‌شود تا stateهای ناقص/قدیمی
    # کاربر را با پیام «پنل پاسخگویی هنوز فعال نشده است» اشتباه نکنند.
    if not str(rec.get('input','') or '').strip():
        return {'empty':True},None
    expiry_at=rec.get('expiry_at')
    if not expiry_at:
        return None,'پنل پاسخگویی هنوز فعال نشده است.'
    try:
        expiry_dt=_dt(expiry_at)
    except (TypeError,ValueError):
        rec['status']=STATUS_EXPIRED; save_state(session,s); return {'expired':True},None
    if now()>expiry_dt: rec['status']=STATUS_EXPIRED; save_state(session,s); return {'expired':True},None
    if rec.get('input','').strip().upper()!=str(rec['answer']).strip().upper():
        rec['attempts']=int(rec.get('attempts',0))+1
        limit=999999 if cfg['unlimited_attempts'] else int(cfg['max_attempts'])
        if rec['attempts']>=limit:
            rec['status']=STATUS_FAILED; save_state(session,s); return {'failed':True},None
        save_state(session,s); return {'wrong':True,'remaining':limit-rec['attempts']},None
    rec['status']=STATUS_COMPLETED; rec['completed_at']=now().isoformat()
    lev=(cfg.get('types',{}).get(rec.get('type'),{}).get('levels') or cfg.get('levels',{})).get(rec['level'], cfg['levels'][rec['level']]); mn=float(lev['min_reward']); mx=float(lev['max_reward']); total=max(1,float(lev.get('operation_seconds', float(lev.get('time_minutes',1) or 1)*60) or 1)); remaining=max(0,(_dt(rec['expiry_at'])-now()).total_seconds())
    base=random.uniform(mn,mx)
    base=min(mx,max(mn,base + base*(remaining/total)*float(lev.get('speed_factor',0))))
    reward=round(base,2)
    rec.update({'reward':reward,'solve_seconds':max(0,(_dt(rec['completed_at'])-_dt(rec['start_time'])).total_seconds())})
    save_state(session,s)
    all_done = not _available_missions_for_user(session, cfg, s, user_id)
    return {'success':True,'reward':reward,'all_done':all_done},None

def grant_reward(session,user_id,country_id,kind,amount):
    c=session.get(Country,int(country_id));
    if not c: return
    if kind != 'uranium':
        kind = 'uranium'
    setattr(c,'uranium',float(getattr(c,'uranium',0) or 0)+float(amount)); session.commit()

def _available_missions_for_user(session, cfg, s, user_id, cycle=None):
    """Return missions this user has not completed/attempted in the current cycle.

    The check deliberately follows the same type/level enablement rules used by
    ``start()``.  It is used both before sending a new challenge and immediately
    after a successful solve, so a user who has exhausted the whole current bank
    is never sent another challenge.  No permanent lock is stored: adding/enabling
    a new mission makes the user eligible again, while changing ``mission_cycle``
    through the Owner reset automatically starts a fresh cycle.
    """
    cycle = int(s.get('mission_cycle', 0) or 0) if cycle is None else int(cycle)
    used={x.get('mission_id') for x in s.get('history', [])
          if int(x.get('user_id', 0) or 0) == int(user_id)
          and x.get('mission_id') is not None
          and int(x.get('cycle', 0) or 0) == cycle}
    out=[]
    for typ, typ_cfg in (cfg.get('types') or {}).items():
        if not typ_cfg.get('enabled', True):
            continue
        levels=typ_cfg.get('levels') or cfg.get('levels') or {}
        for lev_key, lev_cfg in levels.items():
            if not lev_cfg.get('enabled', True):
                continue
            for mission in ensure_missions(session):
                if (mission.get('type') == typ and mission.get('enabled', True)
                        and mission.get('level', 'easy') == lev_key
                        and int(mission.get('id', 0) or 0) not in used):
                    out.append(mission)
    return out

def user_has_available_mission(session, user_id):
    cfg=ensure_settings(session)
    if not cfg.get('enabled'):
        return False
    return bool(_available_missions_for_user(session, cfg, state(session), user_id))

def due_countries(session):
    cfg=ensure_settings(session)
    if not cfg.get('enabled'): return []
    s=state(session); week=weekly_id(); out=[]
    for c in session.scalars(select(Country)).all():
        if _week_count(s,c.id)>=int(cfg['weekly_per_country']): continue
        users=_country_users(session,c,True)
        if not users: continue
        # اگر یک کاربر تمام مأموریت‌های قابل‌اجرای چرخه فعلی را تمام کرده باشد،
        # دیگر نباید هیچ جعبه‌ای برای او ساخته شود؛ فقط با افزودن/فعال‌کردن مأموریت
        # جدید یا ریست چرخه دوباره واجد شرایط می‌شود.
        eligible=[u for u in users if user_has_available_mission(session, int(u.telegram_id))]
        if not eligible: continue
        active=[x for x in s.get('active',{}).values() if int(x.get('country_id',0))==c.id and x.get('status') in {STATUS_PENDING, STATUS_ACTIVE}]
        if active: continue
        out.append((c,random.choice(eligible)))
    return out


