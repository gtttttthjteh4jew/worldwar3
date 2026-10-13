import asyncio, random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import select
from database.db import SessionLocal
from database.models import Country
from services.panel_security import register_panel
from services.error_reporting import report_exception
from services.settings import get_bot_shutdown_mode
from .database import ensure_settings
from .engine import due_countries, create_pending, state, save_state, weekly_id, STATUS_PENDING, STATUS_ACTIVE, STATUS_FAILED, STATUS_EXPIRED
from .messages import MISSED, EXPIRE


try:
    # تمام زمان‌بندی‌های انیگما بر اساس ساعت ایران محاسبه می‌شوند.
    TZ = ZoneInfo('Asia/Tehran')
except Exception:
    from datetime import timezone
    TZ = timezone(timedelta(hours=3, minutes=30))

def _as_local_datetime(value):
    dt=datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt=dt.replace(tzinfo=TZ)
    return dt

def _as_utc_naive(value):
    dt=datetime.fromisoformat(value)
    # engine.now() و زمان‌های ذخیره‌شدهٔ چرخه انیگما به‌صورت UTC بدون timezone ذخیره می‌شوند.
    # بنابراین مقدار بدون timezone را نباید ساعت ایران فرض کرد؛ در غیر این صورت
    # زمان نمایش سؤال و انقضای جعبه چند ساعت جابه‌جا می‌شود.
    if dt.tzinfo is not None:
        dt=dt.astimezone(ZoneInfo('UTC')).replace(tzinfo=None)
    return dt

def _now_local(): return datetime.now(TZ)

def _parse_hm(x):
    try: h,m=map(int,str(x).split(':')); return h,m
    except Exception: return 10,0

def _weekday_index(dt):
    # رابط کاربری: شنبه=0 ... جمعه=6
    # datetime.weekday(): دوشنبه=0 ... یکشنبه=6
    return (dt.weekday() + 2) % 7

def _week_start(now):
    return now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=_weekday_index(now))

def _make_slots(cfg, now):
    """برنامه هفتگی را دقیقاً در بازه ساعت و روزهای تعیین‌شده Owner می‌سازد."""
    count=max(1,int(cfg.get('weekly_per_country',1) or 1))
    min_h,min_m=_parse_hm(cfg.get('min_hour','10:00'))
    max_h,max_m=_parse_hm(cfg.get('max_hour','23:00'))
    min_h=max(0,min(23,min_h)); max_h=max(0,min(23,max_h))
    start_min=min_h*60+min_m
    end_min=max_h*60+max_m
    if end_min < start_min:
        # بازه شبانه که از نیمه‌شب عبور می‌کند.
        end_min += 24*60
    gap_minutes=max(0,int(round(float(cfg.get('min_gap_hours',0) or 0)*60)))

    if cfg.get('random_days'):
        # در حالت تصادفی، تعداد روزهای انتخابی متناسب با سهم هفتگی است؛
        # اگر سهم بیشتر از ۷ باشد، در همان روزها چند نوبت مجاز است.
        day_count=min(7,count)
        days=sorted(random.sample(range(7),day_count))
    else:
        days=sorted({int(x) for x in (cfg.get('send_days') or []) if str(x).isdigit() and 0 <= int(x) < 7})
        if not days:
            days=list(range(7))

    ws=_week_start(now)
    candidates=[]
    for day in days:
        base=ws+timedelta(days=day)
        for minute in range(start_min,end_min+1):
            dt=base+timedelta(minutes=minute)
            if dt > now:
                candidates.append(dt)

    if not candidates:
        # Current week's window may already have passed when the Owner changes the
        # schedule or restarts the bot. Do not freeze an empty schedule forever;
        # schedule the next valid weekly window using the exact configured days/times.
        next_now = now + timedelta(days=7)
        next_ws = _week_start(next_now)
        candidates = []
        for day in days:
            base = next_ws + timedelta(days=day)
            for minute in range(start_min, end_min + 1):
                candidates.append(base + timedelta(minutes=minute))
        if not candidates:
            return []

    # بدون فاصله: زمان‌ها کاملاً تصادفی ولی فقط داخل بازه Owner هستند.
    if gap_minutes <= 0:
        selected=sorted(random.sample(candidates,min(count,len(candidates))))
    else:
        # برای جلوگیری از تکرار زمان، از یک ترتیب تصادفی شروع می‌کنیم و
        # فقط زمان‌هایی را نگه می‌داریم که حداقل فاصله Owner را رعایت کنند.
        random.shuffle(candidates)
        selected=[]
        for dt in candidates:
            if all(abs((dt-x).total_seconds()) >= gap_minutes*60 for x in selected):
                selected.append(dt)
                if len(selected)>=count:
                    break
        if len(selected)<count:
            # اگر با محدودیت‌های Owner تعداد موردنظر از نظر ریاضی ممکن نباشد،
            # بیشترین تعداد ممکن ارسال می‌شود؛ زمان خارج از بازه هرگز ساخته نمی‌شود.
            selected=sorted(selected)

    # اگر Scheduler دقیقاً در بازه امروز بالا آمده باشد، نزدیک‌ترین دقیقه مجاز
    # همان بازه را از دست نده؛ در غیر این صورت اولین ارسال به هفته بعد نمی‌رود.
    ui_day=_weekday_index(now)
    current_min=now.hour*60+now.minute
    if ui_day in days and start_min <= current_min <= min(end_min,1439):
        immediate=now.replace(second=0,microsecond=0)
        if immediate < now:
            immediate += timedelta(minutes=1)
        if immediate <= ws+timedelta(days=ui_day,minutes=end_min):
            if not selected or all(abs((immediate-x).total_seconds()) >= gap_minutes*60 for x in selected):
                selected=[immediate]+[x for x in selected if x != immediate]
                selected=sorted(selected)[:count]

    return sorted(selected)[:count]

def _schedule_signature(cfg):
    return repr({k: cfg.get(k) for k in ('weekly_per_country','send_days','random_days','min_hour','max_hour','min_gap_hours')})

def _prepare_schedule(session,cfg):
    s=state(session); week=weekly_id(_now_local()); sig=_schedule_signature(cfg)
    if s.get('schedule_week')!=week or s.get('schedule_signature')!=sig:
        s['schedule_week']=week; s['schedule_signature']=sig; s['schedule']={}
    for c in session.scalars(select(Country)).all():
        key=str(c.id)
        if key not in s['schedule']:
            s['schedule'][key]=[x.isoformat() for x in _make_slots(cfg,_now_local())]
    save_state(session,s); return s

async def enigma_scheduler(app):
    await asyncio.sleep(3)
    while True:
        try:
            with SessionLocal() as session:
                cfg=ensure_settings(session)
                # حذف جعبه‌های بازنشده مستقل از روشن/خاموش بودن ارسال‌های جدید انجام می‌شود.
                box_expiry=max(1,float(cfg.get('box_expiry_minutes',60)))*60
                s=state(session); changed=False
                # مأموریت‌های فعال پس از زمان نمایش تعیین‌شده خودکار به پنل پاسخگویی می‌روند.
                for token,rec in list((s.get('active') or {}).items()):
                    if rec.get('status') == STATUS_ACTIVE and not rec.get('answer_panel') and rec.get('question_until'):
                        try:
                            q_until=_as_utc_naive(rec['question_until'])
                            if datetime.utcnow() >= q_until:
                                # باز شدن خودکار پنل دقیقاً همان مسیر باز شدن دستی را طی می‌کند؛
                                # بنابراین زمان حل از همین لحظه شروع می‌شود.
                                from .engine import reveal_answer_panel, render_answer_panel
                                uid=int(rec.get('user_id',0))
                                updated = reveal_answer_panel(session, token, uid)
                                if updated:
                                    # reveal_answer_panel ذخیره را انجام می‌دهد؛ این commit صریحاً تضمین می‌کند
                                    # callback کاربر که بلافاصله بعد از ویرایش پیام می‌رسد همان state را ببیند.
                                    session.commit()
                                    changed=True
                                    mid=updated.get('message_id')
                                    if mid:
                                        panel=render_answer_panel(session,token,uid)
                                        if panel:
                                            try: await app.bot.unpin_chat_message(chat_id=uid,message_id=int(mid))
                                            except Exception: pass
                                            # همان پیام سؤال را به پنل پاسخگویی تبدیل کن؛ پیام جدید نساز.
                                            try:
                                                await app.bot.edit_message_text(chat_id=uid,message_id=int(mid),text=panel['text'],parse_mode='HTML',reply_markup=panel['markup'])
                                                updated['message_id']=int(mid); updated['chat_id']=uid
                                                save_state(session,s)
                                            except Exception: pass
                        except Exception:
                            pass
                # پایان خودکار زمان حل؛ زمان حل از لحظه باز شدن پنل پاسخگویی شروع می‌شود.
                for token,rec in list((s.get('active') or {}).items()):
                    if rec.get('status') != STATUS_ACTIVE or not rec.get('expiry_at'):
                        continue
                    try:
                        if datetime.utcnow() >= _as_utc_naive(rec['expiry_at']):
                            rec['status']=STATUS_FAILED; rec['expired_at']=datetime.utcnow().isoformat(); rec['failure_reason']='timeout'
                            for h in s.get('history',[]):
                                if h.get('token')==token:
                                    h.update(rec); break
                            changed=True
                            mid=rec.get('message_id'); uid=int(rec.get('user_id',0))
                            if mid:
                                try:
                                    await app.bot.unpin_chat_message(chat_id=uid, message_id=int(mid))
                                except Exception:
                                    pass
                                try:
                                    await app.bot.delete_message(chat_id=uid, message_id=int(mid))
                                except Exception:
                                    pass
                            rec['message_id'] = None
                            rec['chat_id'] = None
                            # رکورد ACTIVE نیز از فهرست عملیات جاری حذف می‌شود؛
                            # تاریخچه برای آمار باقی می‌ماند. این باعث می‌شود عملیات منقضی‌شده
                            # دوباره به‌عنوان چالش باز دیده نشود و واقعاً از active حذف شود.
                            s.setdefault('active', {}).pop(token, None)
                            save_state(session, s)
                            session.commit()
                            # بعد از حذف خودکار پنل پاسخگویی، نتیجه عملیات را یک‌بار
                            # برای کاربر اعلام کن.
                            try:
                                await app.bot.send_message(chat_id=uid, text=EXPIRE, parse_mode='HTML')
                            except Exception:
                                pass
                    except Exception:
                        pass

                for token,rec in list((s.get('active') or {}).items()):
                    if rec.get('status') != STATUS_PENDING: continue
                    created=rec.get('created_at')
                    if not created: continue
                    try: age=(datetime.utcnow()-_as_utc_naive(created)).total_seconds()
                    except Exception: continue
                    if age < box_expiry: continue
                    rec['status']=STATUS_EXPIRED; rec['expired_at']=datetime.utcnow().isoformat(); changed=True
                    mid=rec.get('message_id'); uid=int(rec.get('user_id',0))
                    if mid:
                        try:
                            await app.bot.unpin_chat_message(chat_id=uid, message_id=int(mid))
                        except Exception:
                            pass
                        try: await app.bot.delete_message(chat_id=uid,message_id=int(mid))
                        except Exception: pass
                    try:
                        from datetime import timezone
                        created_dt=_as_utc_naive(created).replace(tzinfo=timezone.utc).astimezone(TZ)
                        lost_time=created_dt.strftime('%H:%M')
                        await app.bot.send_message(chat_id=uid,text=MISSED.format(time=lost_time),parse_mode='HTML')
                    except Exception:
                        pass
                if changed: save_state(session,s)

                # خاموشی کامل ربات ارسال مأموریت جدید را نیز متوقف می‌کند؛ داده‌های قبلی دست‌نخورده می‌مانند.
                with SessionLocal() as gate_session:
                    bot_shutdown = get_bot_shutdown_mode(gate_session)
                if cfg.get('enabled') and bot_shutdown == 'none':
                    s=_prepare_schedule(session,cfg); now=_now_local(); due=[]
                    for cid, slots in list((s.get('schedule') or {}).items()):
                        ready=[x for x in slots if _as_local_datetime(x)<=now]
                        if ready:
                            # زمان‌های سررسیدشده تا وقتی واقعاً ارسال نشوند حذف نمی‌شوند؛
                            # بنابراین وجود یک عملیات باز باعث از دست رفتن سهم هفتگی نمی‌شود.
                            due.append(int(cid))
                    save_state(session,s)
                    for cid in due:
                        c=session.get(Country,cid)
                        if not c: continue
                        candidates=[pair for pair in due_countries(session) if pair[0].id==c.id]
                        if not candidates: continue
                        user=candidates[0][1]
                        # فقط بعد از ارسال موفق، زمان سررسید را مصرف کن.
                        slots=s.get('schedule',{}).get(str(cid),[])
                        ready=[x for x in slots if _as_local_datetime(x)<=now]
                        if not ready: continue
                        token,text=create_pending(session,user,c,app.bot)
                        try:
                            msg=await app.bot.send_message(chat_id=int(user.telegram_id),text=text,parse_mode='HTML',reply_markup=__import__('enigma.keyboards',fromlist=['box_keyboard']).box_keyboard(token))
                            # چالش دریافتی تا زمان باز شدن/حذف شدن سنجاق می‌شود.
                            # در چت خصوصی ممکن است تلگرام اجازه سنجاق توسط ربات ندهد؛ در آن
                            # صورت ارسال همچنان موفق است و خطا عمداً نادیده گرفته می‌شود.
                            try:
                                await app.bot.pin_chat_message(chat_id=msg.chat_id, message_id=msg.message_id, disable_notification=True)
                            except Exception:
                                pass
                        except Exception:
                            # ارسال ناموفق نباید سهم هفتگی یا عملیات بازِ جعلی بسازد.
                            s=state(session)
                            s.get('active',{}).pop(token,None)
                            s['history']=[x for x in s.get('history',[]) if x.get('token') != token]
                            save_state(session,s)
                            raise
                        s=state(session); rec=s.get('active',{}).get(token)
                        if rec:
                            rec['message_id']=msg.message_id; rec['chat_id']=msg.chat_id
                            slots=s.get('schedule',{}).get(str(cid),[])
                            if slots:
                                # قدیمی‌ترین زمان سررسیدشده مصرف می‌شود.
                                ready_idx=min((i for i,x in enumerate(slots) if _as_local_datetime(x)<=now), default=None)
                                if ready_idx is not None: slots.pop(ready_idx)
                            s.setdefault('schedule',{})[str(cid)]=slots
                            save_state(session,s)
                        register_panel(msg.chat_id,msg.message_id,int(user.telegram_id))
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            import logging; logging.getLogger('worldwar3_bot').exception('انیگما scheduler error')
            await report_exception(app.bot, exc, source='🚨 خطای زمان‌بندی انیگما')
        await asyncio.sleep(1)
