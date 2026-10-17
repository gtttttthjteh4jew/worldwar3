from telegram import InlineKeyboardButton,InlineKeyboardMarkup

def box_keyboard(token):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('🚨 شروع مأموریت', callback_data=f'enigma:start:{token}')]
    ])

def answer_keyboard(token, value='', page=0, space=False):
    """کیبورد پاسخ انیگما؛ حروف پنج‌تایی و اعداد سه‌تایی، با ظاهر رنگی و بدون فاصله."""
    rows=[]
    if page == 0:
        chars='ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        # از نمادهای رنگی برای ظاهر جذاب‌تر استفاده می‌کنیم؛ تلگرام برای دکمه‌های شیشه‌ای
        # امکان تعیین رنگ واقعی پس‌زمینه را نمی‌دهد.
        markers=['🔴','🟠','🟡','🟢','🔵']
        for i in range(0, len(chars), 5):
            chunk=chars[i:i+5]
            rows.append([
                InlineKeyboardButton(f'{markers[j%5]} {c}', callback_data=f'enigma:key:{token}:{c}')
                for j,c in enumerate(chunk)
            ])
        rows.append([
            InlineKeyboardButton('🔴⌫', callback_data=f'enigma:key:{token}:BACK'),
            InlineKeyboardButton('🧹 پاک کردن', callback_data=f'enigma:key:{token}:CLEAR'),
            InlineKeyboardButton('🔢 اعداد', callback_data=f'enigma:page:{token}:1'),
            InlineKeyboardButton('✅ تأیید', callback_data=f'enigma:submit:{token}'),
        ])
    else:
        chars='1234567890'
        markers=['🔴','🟠','🟡']
        for i in range(0, len(chars), 3):
            chunk=chars[i:i+3]
            rows.append([
                InlineKeyboardButton(f'{markers[j%3]} {c}', callback_data=f'enigma:key:{token}:{c}')
                for j,c in enumerate(chunk)
            ])
        rows.append([
            InlineKeyboardButton('🔴⌫', callback_data=f'enigma:key:{token}:BACK'),
            InlineKeyboardButton('🧹 پاک کردن', callback_data=f'enigma:key:{token}:CLEAR'),
            InlineKeyboardButton('🔤 حروف', callback_data=f'enigma:page:{token}:0'),
            InlineKeyboardButton('✅ تأیید', callback_data=f'enigma:submit:{token}'),
        ])
    return InlineKeyboardMarkup(rows)

def owner_main_keyboard():
    return InlineKeyboardMarkup([
      [InlineKeyboardButton('⚙️ تنظیمات عمومی',callback_data='owner:enigma_settings')],
      [InlineKeyboardButton('🧩 تنظیم انواع چالش',callback_data='owner:enigma_types')],
      [InlineKeyboardButton('📚 بانک انیگما',callback_data='owner:enigma_bank')],
      [InlineKeyboardButton('📊 آمار انیگما',callback_data='owner:enigma_stats')],
      [InlineKeyboardButton('♻️ ریست چرخه مأموریت‌ها',callback_data='owner:enigma_reset')],
    ])

def owner_attempts_keyboard(cfg):
    unlimited = bool(cfg.get('unlimited_attempts'))
    rows=[[InlineKeyboardButton('🔴 غیرفعال کردن نامحدود' if unlimited else '🟢 فعال کردن نامحدود',callback_data='owner:enigma_unlimited_toggle')]]
    if not unlimited:
        rows.append([InlineKeyboardButton('🔢 تغییر حداکثر تعداد تلاش',callback_data='owner:enigma_edit:max_attempts')])
    rows.append([InlineKeyboardButton('🔙 برگشت',callback_data='owner:enigma_settings')])
    return InlineKeyboardMarkup(rows)

def owner_settings_keyboard(cfg):
    enabled=bool(cfg.get('enabled'))
    rows=[
        [InlineKeyboardButton('🔴 غیرفعال کردن' if enabled else '🟢 فعال کردن', callback_data='owner:enigma_toggle:enabled')],
        [InlineKeyboardButton('📦 ارسال هفتگی هر کشور',callback_data='owner:enigma_edit:weekly_per_country'), InlineKeyboardButton('⏳ حداقل فاصله',callback_data='owner:enigma_edit:min_gap_hours')],
        [InlineKeyboardButton('📦 حذف جعبه بازنشده',callback_data='owner:enigma_edit:box_expiry_minutes'), InlineKeyboardButton('🕐 ساعت ارسال',callback_data='owner:enigma_hours')],
        [InlineKeyboardButton('📅 روزهای ارسال',callback_data='owner:enigma_days'), InlineKeyboardButton('🎯 تعداد تلاش',callback_data='owner:enigma_attempts')],
        [InlineKeyboardButton('🔙 برگشت',callback_data='owner:enigma')],
    ]
    return InlineKeyboardMarkup(rows)

def owner_levels_keyboard(cfg):
    rows=[]
    for k,title in [('easy','🟢 آسان'),('medium','🟡 متوسط'),('hard','🔴 سخت')]:
        v=cfg['levels'][k]; rows.append([InlineKeyboardButton(f"{title} | وزن {v['weight']} | {v['min_reward']} تا {v['max_reward']}",callback_data=f'owner:enigma_level:{k}')])
    rows.append([InlineKeyboardButton('🔙 برگشت',callback_data='owner:enigma')]); return InlineKeyboardMarkup(rows)

def owner_level_edit_keyboard(level,cfg):
    v=cfg['levels'][level]
    return InlineKeyboardMarkup([
      [InlineKeyboardButton(('🔴 غیرفعال کردن' if v['enabled'] else '🟢 فعال کردن'),callback_data=f'owner:enigma_level_toggle:{level}')],
      [InlineKeyboardButton(f"⚖️ احتمال انتخاب: {v['weight']}",callback_data=f'owner:enigma_level_edit:{level}:weight')],
      [InlineKeyboardButton(f"⏱ زمان عملیات: {v['operation_seconds']} ثانیه",callback_data=f'owner:enigma_level_edit:{level}:operation_seconds')],
      [InlineKeyboardButton(f"☢️ حداقل پاداش اورانیوم: {v['min_reward']}",callback_data=f'owner:enigma_level_edit:{level}:min_reward')],
      [InlineKeyboardButton(f"☢️ حداکثر پاداش اورانیوم: {v['max_reward']}",callback_data=f'owner:enigma_level_edit:{level}:max_reward')],
      [InlineKeyboardButton(f"⚡ ضریب سرعت: {v['speed_factor']}",callback_data=f'owner:enigma_level_edit:{level}:speed_factor')],
      [InlineKeyboardButton('🔙 برگشت',callback_data='owner:enigma_levels')]
    ])

def owner_types_keyboard(cfg):
    names={'letter_shift':'جابه‌جایی حروف','morse':'مورس','memory_multi':'حفظ چند اطلاعات','memory_text':'حفظ اطلاعات در متن'}
    rows=[]
    for k,n in names.items():
        v=cfg['types'][k]; rows.append([InlineKeyboardButton(f"{'🟢' if v['enabled'] else '🔴'} {n} | وزن {v['weight']}",callback_data=f'owner:enigma_type:{k}')])
    rows.append([InlineKeyboardButton('🔙 برگشت',callback_data='owner:enigma')]); return InlineKeyboardMarkup(rows)

def owner_type_edit_keyboard(k,cfg):
    v=cfg['types'][k]; names={'letter_shift':'🔤 جابه‌جایی حروف','morse':'📡 مورس','memory_multi':'🧠 حفظ چند اطلاعات','memory_text':'📜 حفظ اطلاعات در متن'}
    rows=[
      [InlineKeyboardButton(('🔴 غیرفعال کردن' if v['enabled'] else '🟢 فعال کردن'),callback_data=f'owner:enigma_type_toggle:{k}')],
      [InlineKeyboardButton(f"⚖️ وزن انتخاب: {v['weight']}",callback_data=f'owner:enigma_type_edit:{k}:weight')],
    ]
    for lev,title in [('easy','🟢 آسان'),('medium','🟡 متوسط'),('hard','🔴 سخت')]:
        lv=v.setdefault('levels',{}).setdefault(lev, cfg['levels'][lev].copy())
        rows.append([InlineKeyboardButton(f"{title} | {'فعال' if lv.get('enabled') else 'غیرفعال'} | وزن {lv.get('weight')} | {lv.get('min_reward')} تا {lv.get('max_reward')}",callback_data=f'owner:enigma_type_level:{k}:{lev}')])
    rows.append([InlineKeyboardButton('🔙 برگشت',callback_data='owner:enigma_types')])
    return InlineKeyboardMarkup(rows)

def owner_type_level_edit_keyboard(typ,level,cfg):
    # Telegram callback_data is limited to 64 UTF-8 bytes. Keep this family
    # compact because some type/field combinations otherwise exceed that limit.
    v=cfg['types'][typ]['levels'][level]
    type_code={'letter_shift':'ls','morse':'mo','memory_multi':'mm','memory_text':'mt'}[typ]
    field_code={
        'weight':'w','operation_seconds':'tm','question_display_seconds':'qd',
        'min_reward':'min','max_reward':'max','speed_factor':'sf',
    }
    title={'easy':'🟢 آسان','medium':'🟡 متوسط','hard':'🔴 سخت'}[level]
    return InlineKeyboardMarkup([
      [InlineKeyboardButton(('🔴 غیرفعال کردن' if v.get('enabled') else '🟢 فعال کردن'),callback_data=f'owner:enigma_type_level_toggle:{type_code}:{level}')],
      [InlineKeyboardButton(f"⚖️ وزن انتخاب: {v.get('weight')}",callback_data=f'owner:enigma_type_level_edit:{type_code}:{level}:w')],
      [InlineKeyboardButton(f"⏱ زمان عملیات: {v.get('operation_seconds')} ثانیه",callback_data=f'owner:enigma_type_level_edit:{type_code}:{level}:tm')],
      [InlineKeyboardButton(f"👁 زمان نمایش پرسش: {v.get('question_display_seconds',30)} ثانیه",callback_data=f'owner:enigma_type_level_edit:{type_code}:{level}:qd')],
      [InlineKeyboardButton(f"☢️ حداقل پاداش اورانیوم: {v.get('min_reward')}",callback_data=f'owner:enigma_type_level_edit:{type_code}:{level}:min')],
      [InlineKeyboardButton(f"☢️ حداکثر پاداش اورانیوم: {v.get('max_reward')}",callback_data=f'owner:enigma_type_level_edit:{type_code}:{level}:max')],
      [InlineKeyboardButton(f"⚡ ضریب سرعت: {v.get('speed_factor')}",callback_data=f'owner:enigma_type_level_edit:{type_code}:{level}:sf')],
      [InlineKeyboardButton('🔙 برگشت',callback_data=f'owner:enigma_type:{typ}')]
    ])

def owner_bank_keyboard(counts):
    total=sum(counts.values())
    return InlineKeyboardMarkup([
      [InlineKeyboardButton(f'📋 لیست انیگماها ({total})',callback_data='owner:enigma_bank_list')],
      [InlineKeyboardButton('➕ افزودن مأموریت',callback_data='owner:enigma_bank_add'), InlineKeyboardButton('🔎 جستجوی مأموریت',callback_data='owner:enigma_bank_search')],
      [InlineKeyboardButton('🔙 برگشت',callback_data='owner:enigma')]
    ])

def owner_mission_list_keyboard(counts):
    names={'letter_shift':'🔤 جابه‌جایی حروف','morse':'📡 مورس','memory_multi':'🧠 حفظ چند اطلاعات','memory_text':'📜 حفظ اطلاعات در متن'}
    rows=[[InlineKeyboardButton(f'{n}: {counts.get(k,0)}',callback_data=f'owner:enigma_bank_type:{k}:1')] for k,n in names.items()]
    rows.append([InlineKeyboardButton('🔙 برگشت',callback_data='owner:enigma_bank')])
    return InlineKeyboardMarkup(rows)

def owner_mission_type_keyboard():
    return InlineKeyboardMarkup([
      [InlineKeyboardButton('🔤 جابه‌جایی حروف',callback_data='owner:enigma_add_type:letter_shift')],
      [InlineKeyboardButton('📡 مورس',callback_data='owner:enigma_add_type:morse')],
      [InlineKeyboardButton('🧠 حفظ چند اطلاعات',callback_data='owner:enigma_add_type:memory_multi')],
      [InlineKeyboardButton('📜 حفظ اطلاعات در متن',callback_data='owner:enigma_add_type:memory_text')],
      [InlineKeyboardButton('🔙 برگشت',callback_data='owner:enigma_bank')]
    ])


def owner_mission_level_keyboard():
    return InlineKeyboardMarkup([
      [InlineKeyboardButton('🟢 آسان',callback_data='owner:enigma_add_level:easy')],
      [InlineKeyboardButton('🟡 متوسط',callback_data='owner:enigma_add_level:medium')],
      [InlineKeyboardButton('🔴 سخت',callback_data='owner:enigma_add_level:hard')],
      [InlineKeyboardButton('🔙 برگشت',callback_data='owner:enigma_bank')]
    ])

def owner_bank_type_keyboard(k,page=1,missions=None):
    rows=[]
    items=[m for m in (missions or []) if m.get('type')==k]
    items.sort(key=lambda m:int(m.get('id',0)))
    page=max(1,int(page)); per_page=20; start=(page-1)*per_page; chunk=items[start:start+per_page]
    for m in chunk:
        mid=int(m.get('id',0)); status='🟢' if m.get('enabled',True) else '🔴'
        rows.append([InlineKeyboardButton(f'{status} مأموریت {mid}',callback_data=f'owner:enigma_mission:{k}:{mid}')])
    total_pages=max(1,(len(items)+per_page-1)//per_page)
    nav=[]
    if page>1: nav.append(InlineKeyboardButton('◀️',callback_data=f'owner:enigma_bank_type:{k}:{page-1}'))
    if page<total_pages: nav.append(InlineKeyboardButton('▶️',callback_data=f'owner:enigma_bank_type:{k}:{page+1}'))
    if nav: rows.append(nav)
    rows.append([InlineKeyboardButton(f'صفحه {page} از {total_pages}',callback_data='owner:noop')])
    rows.append([InlineKeyboardButton('🔙 برگشت',callback_data='owner:enigma_bank')]); return InlineKeyboardMarkup(rows)

def owner_days_keyboard(cfg):
    names=['شنبه','یکشنبه','دوشنبه','سه‌شنبه','چهارشنبه','پنجشنبه','جمعه']
    selected=set(cfg.get('send_days') or [])
    rows=[]
    if not cfg.get('random_days'):
        buttons=[InlineKeyboardButton(('✅ ' if i in selected else '☐ ')+n,callback_data=f'owner:enigma_day_toggle:{i}') for i,n in enumerate(names)]
        for i in range(0,len(buttons),2):
            rows.append(buttons[i:i+2])
    rows.append([InlineKeyboardButton('🎲 انتخاب تصادفی روزها: '+('فعال' if cfg.get('random_days') else 'غیرفعال'),callback_data='owner:enigma_toggle:random_days')])
    rows.append([InlineKeyboardButton('🔙 برگشت',callback_data='owner:enigma_settings')])
    return InlineKeyboardMarkup(rows)

def owner_mission_delete_confirm_keyboard(typ,mid):
    return InlineKeyboardMarkup([[InlineKeyboardButton('🗑 تأیید حذف',callback_data=f'owner:enigma_delete_confirm:{typ}:{mid}')],[InlineKeyboardButton('🔙 برگشت',callback_data=f'owner:enigma_bank_type:{typ}:1')]])

def owner_mission_manage_keyboard(typ,mid,enabled=True):
    return InlineKeyboardMarkup([
      [InlineKeyboardButton(('🟢 غیرفعال کردن' if enabled else '🔴 فعال کردن'),callback_data=f'owner:enigma_mission_toggle:{typ}:{mid}')],
      [InlineKeyboardButton('✏️ ویرایش مأموریت',callback_data=f'owner:enigma_mission_edit:{typ}:{mid}'), InlineKeyboardButton('🗑 حذف مأموریت',callback_data=f'owner:enigma_mission_delete:{typ}:{mid}')],
      [InlineKeyboardButton('🔙 برگشت',callback_data=f'owner:enigma_bank_type:{typ}:1')]
    ])

def owner_mission_edit_keyboard(typ,mid):
    return InlineKeyboardMarkup([
      [InlineKeyboardButton('🧩 ویرایش نوع',callback_data=f'owner:enigma_edit_mission_type:{typ}:{mid}') , InlineKeyboardButton('🎚 ویرایش سطح',callback_data=f'owner:enigma_edit_mission_level:{typ}:{mid}')],
      [InlineKeyboardButton('📝 ویرایش متن پرسش',callback_data=f'owner:enigma_edit_mission:{typ}:{mid}:prompt'), InlineKeyboardButton('🔐 ویرایش پاسخ',callback_data=f'owner:enigma_edit_mission:{typ}:{mid}:answer')],
      [InlineKeyboardButton('💡 ویرایش راهنمایی',callback_data=f'owner:enigma_edit_mission:{typ}:{mid}:hint')],
      [InlineKeyboardButton('☢️ ویرایش جایزه',callback_data=f'owner:enigma_edit_mission_reward:{typ}:{mid}')],
      [InlineKeyboardButton('🔙 برگشت',callback_data=f'owner:enigma_mission:{typ}:{mid}')]
    ])

def owner_mission_type_edit_keyboard(typ,mid):
    return InlineKeyboardMarkup([
      [InlineKeyboardButton('🔤 جابه‌جایی حروف',callback_data=f'owner:enigma_set_mission_type:{typ}:{mid}:letter_shift')],
      [InlineKeyboardButton('📡 مورس',callback_data=f'owner:enigma_set_mission_type:{typ}:{mid}:morse')],
      [InlineKeyboardButton('🧠 حفظ چند اطلاعات',callback_data=f'owner:enigma_set_mission_type:{typ}:{mid}:memory_multi')],
      [InlineKeyboardButton('📜 حفظ اطلاعات در متن',callback_data=f'owner:enigma_set_mission_type:{typ}:{mid}:memory_text')],
      [InlineKeyboardButton('🔙 برگشت',callback_data=f'owner:enigma_mission_edit:{typ}:{mid}')]
    ])

def owner_mission_level_edit_keyboard(typ,mid):
    return InlineKeyboardMarkup([
      [InlineKeyboardButton('🟢 آسان',callback_data=f'owner:enigma_set_mission_level:{typ}:{mid}:easy')],
      [InlineKeyboardButton('🟡 متوسط',callback_data=f'owner:enigma_set_mission_level:{typ}:{mid}:medium')],
      [InlineKeyboardButton('🔴 سخت',callback_data=f'owner:enigma_set_mission_level:{typ}:{mid}:hard')],
      [InlineKeyboardButton('🔙 برگشت',callback_data=f'owner:enigma_mission_edit:{typ}:{mid}')]
    ])

def owner_mission_reward_edit_keyboard(typ,mid):
    return InlineKeyboardMarkup([
      [InlineKeyboardButton('☢️ حداقل جایزه سطح',callback_data=f'owner:enigma_mission_reward:{typ}:{mid}:min_reward')],
      [InlineKeyboardButton('☢️ حداکثر جایزه سطح',callback_data=f'owner:enigma_mission_reward:{typ}:{mid}:max_reward')],
      [InlineKeyboardButton('🔙 برگشت',callback_data=f'owner:enigma_mission_edit:{typ}:{mid}')]
    ])

def owner_mission_search_type_keyboard():
    return InlineKeyboardMarkup([
      [InlineKeyboardButton('🔤 جابه‌جایی حروف',callback_data='owner:enigma_search_type:letter_shift'), InlineKeyboardButton('📡 مورس',callback_data='owner:enigma_search_type:morse')],
      [InlineKeyboardButton('🧠 حفظ چند اطلاعات',callback_data='owner:enigma_search_type:memory_multi'), InlineKeyboardButton('📜 حفظ اطلاعات در متن',callback_data='owner:enigma_search_type:memory_text')],
      [InlineKeyboardButton('🔙 برگشت',callback_data='owner:enigma_bank')]
    ])

def owner_mission_search_results_keyboard(matches):
    rows=[]
    for m in matches[:20]:
        typ=m.get('type'); mid=int(m.get('id',0)); status='فعال' if m.get('enabled',True) else 'غیرفعال'
        rows.append([InlineKeyboardButton(f"مأموریت {mid} — {status}",callback_data=f'owner:enigma_mission:{typ}:{mid}')])
    rows.append([InlineKeyboardButton('🔙 برگشت',callback_data='owner:enigma_bank')])
    return InlineKeyboardMarkup(rows)

