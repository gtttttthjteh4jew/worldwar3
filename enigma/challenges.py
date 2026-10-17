import random, string
TYPE_NAMES={'letter_shift':'جابه‌جایی حروف','morse':'مورس','memory_multi':'حفظ چند اطلاعات','memory_text':'حفظ اطلاعات در متن'}
LEVEL_NAMES={'easy':'🟢 آسان','medium':'🟡 متوسط','hard':'🔴 سخت'}
MORSE={**dict(zip('ABCDEFGHIJKLMNOPQRSTUVWXYZ',['.-','-...','-.-.','-..','.','..-.','--.','....','..','.---','-.-','.-..','--','-.','---','.--.','--.-','.-.','...','-','..-','...-','.--','-..-','-.--','--..'])), '0':'-----','1':'.----','2':'..---','3':'...--','4':'....-','5':'.....','6':'-....','7':'--...','8':'---..','9':'----.'}
REV={v:k for k,v in MORSE.items()}

def _code(n=5): return ''.join(random.choice(string.ascii_uppercase+string.digits) for _ in range(n))
def _shift_char(c,n):
    if c.isalpha(): return chr((ord(c.upper())-65+n)%26+65)
    return c

def generated_missions():
    out=[]
    for typ in ('letter_shift','morse','memory_multi','memory_text'):
        for i in range(1,501):
            if typ=='letter_shift':
                answer=_code(random.randint(4,6)); shift=random.randint(1,9)
                encoded=''.join(_shift_char(c,shift) for c in answer)
                prompt=f'رمز جابه‌جایی حروف را حل کنید. هر حرف را {shift} خانه به عقب برگردانید و کد نهایی را به حروف بزرگ ارسال کنید:\n<code>{encoded}</code>'
            elif typ=='morse':
                answer=_code(random.randint(4,6)); morse=' / '.join(MORSE[c] for c in answer)
                prompt=f'کد زیر با مورس نوشته شده است. آن را به حروف و اعداد تبدیل کنید و پاسخ نهایی را ارسال کنید:\n<code>{morse}</code>'
            elif typ=='memory_multi':
                pairs=[]
                answer=_code(5)
                for c in answer: pairs.append(f'{c}{random.randint(10,99)}')
                random.shuffle(pairs)
                target=random.choice(pairs); prompt=f'این اطلاعات را برای چند لحظه حفظ کنید:\n<code>{" | ".join(pairs)}</code>\n\nعدد کنار حرف <b>{target[0]}</b> را پیدا کنید و همراه همان حرف ارسال کنید.'
                answer=target
            else:
                answer=_code(5); distractors=[_code(5) for _ in range(3)]
                all_codes=distractors+[answer]; random.shuffle(all_codes)
                lines=[f'گزارش شماره {j+1}: شناسه عملیات <code>{x}</code> ثبت شد.' for j,x in enumerate(all_codes)]
                pos=all_codes.index(answer)+1
                prompt='متن زیر را با دقت بخوانید و شناسه عملیات گزارش شماره '+str(pos)+' را ارسال کنید:\n\n'+'\n'.join(lines)
            out.append({'id':i,'type':typ,'prompt':prompt,'answer':answer,'enabled':True})
    return out

def ensure_missions(session):
    """بانک مأموریت‌ها فقط توسط Owner ساخته می‌شود؛ هیچ مأموریت پیش‌فرضی تولید نمی‌شود."""
    from .database import get_setting, set_setting
    data = get_setting(session, 'missions')
    if data is None or not isinstance(data, list):
        data = []
        set_setting(session, 'missions', data)
        return data

    # نسخه‌های قبلی ۲۰۰۰ مأموریت آزمایشی را خودکار می‌ساختند.
    # اگر همان بانک تولیدشده هنوز در تنظیمات باقی مانده باشد، آن را یک‌بار پاک می‌کنیم
    # تا از این نسخه به بعد بانک کاملاً خالی باشد و Owner همه مأموریت‌ها را اضافه کند.
    valid_types = {'letter_shift', 'morse', 'memory_multi', 'memory_text'}
    generated_shape = (
        len(data) == 2000 and
        {str(m.get('type')) for m in data if isinstance(m, dict)} == valid_types and
        all(isinstance(m, dict) and int(m.get('id', 0) or 0) in range(1, 501)
            and float(m.get('min_reward', 0) or 0) == 0
            and float(m.get('max_reward', 0) or 0) == 0
            for m in data)
        and all(sum(1 for m in data if isinstance(m, dict) and m.get('type') == typ) == 500 for typ in valid_types)
    )
    if generated_shape:
        data = []
        set_setting(session, 'missions', data)
        return data

    changed = False
    for m in data:
        if not isinstance(m, dict):
            continue
        if 'reward_type' in m:
            m.pop('reward_type', None); changed = True
        m.pop('min_reward', None); m.pop('max_reward', None)
        if 'hint' not in m:
            m['hint'] = ''
            changed = True
        # زمان نمایش پرسش اکنون در تنظیمات نوع+سطح نگهداری می‌شود.
        if 'display_seconds' in m:
            m.pop('display_seconds', None)
            changed = True
        if 'level' not in m:
            m['level'] = 'easy'; changed = True
        if 'enabled' not in m:
            m['enabled'] = True; changed = True
    if changed:
        set_setting(session, 'missions', data)
    return data

def mission_bank_counts(session):
    data=ensure_missions(session); return {t:sum(1 for m in data if m['type']==t and m.get('enabled',True)) for t in TYPE_NAMES}

def pick_weighted(items, weight_key='weight'):
    vals=[x for x in items if x.get('enabled',True) and float(x.get(weight_key,0))>0]
    if not vals: return None
    return random.choices(vals,weights=[float(x.get(weight_key,1)) for x in vals],k=1)[0]

def pick_mission(session,cfg,used_ids=None,level=None,typ=None):
    used_ids=set(used_ids or [])
    if typ is None:
        chosen=pick_weighted([{'key':k,**v} for k,v in cfg['types'].items()])
        if not chosen: return None
        typ=chosen['key']
    missions=[m for m in ensure_missions(session) if m['type']==typ and m.get('enabled',True) and int(m.get('id',0)) not in used_ids and (level is None or m.get('level','easy')==level)]
    return random.choice(missions) if missions else None
