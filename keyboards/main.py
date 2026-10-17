from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

def private_main_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🌍 کشور فعال", callback_data="active_country"),
            ],
        ]
    )


def country_list_keyboard(countries, selected_id=None, back_callback="main_menu"):
    rows = []

    for country in countries:
        rows.append(
            [
                InlineKeyboardButton(
                    ("✅ " if selected_id == country.id else "") + country.title,
                    callback_data=f"set_country:{country.id}",
                )
            ]
        )

    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data=back_callback)])
    return InlineKeyboardMarkup(rows)


def self_country_edit_list_keyboard(countries):
    rows = [[InlineKeyboardButton(f"🌍 {c.title}", callback_data=f"settings:country_edit_pick:{c.id}")] for c in countries]
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data="settings:game")])
    return InlineKeyboardMarkup(rows)


def metal_mine_cancel_confirm_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأیید برگشت", callback_data="metal_mine_cancel_confirm")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="metal_mine_cancel_back")],
    ])


def hq_cancel_confirm_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأیید برگشت", callback_data="hq_cancel_confirm")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="hq_cancel_back")],
    ])


def hq_keyboard(can_upgrade: bool = True, built: bool = True, construction_text: str | None = None, build_uranium: bool = False, upgrade_uranium: bool = False, in_progress: bool = False, finish_uranium_cost: float = 0.0):
    if in_progress or construction_text:
        rows = [[InlineKeyboardButton("🔙 برگشت", callback_data="hq_cancel")]]
        if float(finish_uranium_cost or 0) > 0:
            rows.append([InlineKeyboardButton(f"☢️ تکمیل فوری با {float(finish_uranium_cost):,.2f} اورانیوم", callback_data="hq_finish_now")])
        return InlineKeyboardMarkup(rows)
    if not built:
        rows=[[InlineKeyboardButton("🏗️ ساخت با پول/فلز/سوخت", callback_data="hq_build_preview:normal")]]
        if build_uranium:
            rows.append([InlineKeyboardButton("☢️ ساخت با اورانیوم", callback_data="hq_build_preview:uranium")])
        return InlineKeyboardMarkup(rows)
    rows = []
    if can_upgrade:
        rows.append([InlineKeyboardButton("⬆️ ارتقا با پول/فلز/سوخت", callback_data="hq_upgrade_preview:normal")])
        if upgrade_uranium:
            rows.append([InlineKeyboardButton("☢️ ارتقا با اورانیوم", callback_data="hq_upgrade_preview:uranium")])
    rows.append([InlineKeyboardButton("🎁 ارتقای جعبه‌ها", callback_data="golden:upgrade")])
    rows.append([InlineKeyboardButton("🧬 فناوری نظامی", callback_data="hq_technology")])
    return InlineKeyboardMarkup(rows)


def country_creation_keyboard():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("❌ انصراف", callback_data="cancel_country_creation")]]
    )


def country_name_confirm_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأیید", callback_data="country_name_confirm")],
        [InlineKeyboardButton("✏️ تعویض اسم", callback_data="country_name_change")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="country_name_cancel")],
    ])


def swap_country_keyboard(countries):
    rows = [[InlineKeyboardButton(c.title, callback_data=f"swap_from:{c.id}")] for c in countries]
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data="settings:game")])
    return InlineKeyboardMarkup(rows)


def swap_target_keyboard(countries, source_id):
    rows = [[InlineKeyboardButton(c.title, callback_data=f"swap_to:{source_id}:{c.id}")] for c in countries if c.id != source_id]
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data="swap_target_back")])
    return InlineKeyboardMarkup(rows)


def swap_confirm_keyboard(source_id, target_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأیید نهایی جابه‌جایی", callback_data=f"swap_confirm:{source_id}:{target_id}")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="swap_target_back")],
    ])



def country_rename_payment_keyboard(money_cost=0, uranium_cost=0, back_callback="settings:self_country_edit"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"💰 تغییر با پول — {float(money_cost):,.0f}", callback_data="country_rename_payment:money")],
        [InlineKeyboardButton(f"☢️ تغییر با اورانیوم — {float(uranium_cost):,.2f}", callback_data="country_rename_payment:uranium")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=back_callback)],
    ])

def country_edit_waiting_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data="country_edit_waiting_back")]])


def country_edit_confirm_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأیید", callback_data="country_edit_confirm")],
        [InlineKeyboardButton("✏️ تغییر نام", callback_data="country_edit_change")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="country_edit_cancel")],
    ])


def _reply_button(text, style=None, **kwargs):
    """ساخت دکمه Reply Keyboard با استایل رسمی Telegram.

    KeyboardButton یک شیء immutable است؛ بنابراین style باید هنگام ساخت
    دکمه تعیین شود و نباید بعداً با button.style = ... تغییر کند.
    """
    label = str(text)
    if style is None:
        if label == "🔙 برگشت":
            style = "danger"
        elif any(word in label for word in ("خرید", "ثبت", "دریافت", "تأیید", "فعال", "ساخت")):
            style = "success"
        elif any(word in label for word in ("مرکز فرماندهی", "زرادخانه", "بانک مرکزی", "معدن", "تبادل", "فروشگاه", "تنظیمات", "چت و کانال", "تیم‌های ساخت", "موشک", "سپر")):
            style = "primary"
        else:
            style = "primary"
    return KeyboardButton(label, style=style, **kwargs)


def _reply_page_keyboard(rows):
    # رنگ دکمه‌های Reply Keyboard را همان لحظه ساخت تعیین می‌کنیم؛
    # تغییر دادن attribute بعد از ساخت در python-telegram-bot مجاز نیست.
    return ReplyKeyboardMarkup(
        [list(row) for row in rows],
        resize_keyboard=True,
        is_persistent=False,
        one_time_keyboard=False,
        input_field_placeholder="پیام",
    )


def command_keyboard(no_country: bool = False):
    return _reply_page_keyboard(
        [
            [_reply_button("🏛️ مرکز فرماندهی")],
            [_reply_button("🏭 زرادخانه"), _reply_button("🏦 بانک مرکزی"), _reply_button("⛏️ معدن فلز")],
            [
                _reply_button("💱 تبادل"),
                _reply_button("🏪 فروشگاه"),
            ],
            [_reply_button("💬 چت و کانال"), _reply_button("🪪 تنظیمات اکانت"), _reply_button("🎮 تنظیمات بازی")],
        ]
    )


def page_back_keyboard():
    return _reply_page_keyboard([[_reply_button("🔙 برگشت")]])


def central_bank_locked_keyboard(has_cost=True):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 پرداخت غرامت و باز شدن بانک", callback_data="bank:unlock", style="success")],
    ])


def central_bank_keyboard(built=True, can_upgrade=False, in_progress=False, finish_uranium_cost=0.0):
    if not built and not in_progress:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🏗️ ساخت بانک مرکزی", callback_data="bank:build", style="success")],
        ])
    rows=[]
    if in_progress:
        if float(finish_uranium_cost or 0) > 0:
            rows.append([InlineKeyboardButton(f"☢️ تکمیل فوری با {float(finish_uranium_cost):,.2f} اورانیوم", callback_data="bank:finish_now")])
        rows.append([InlineKeyboardButton("🔙 برگشت", callback_data="bank:cancel")])
    else:
        if can_upgrade:
            rows.append([InlineKeyboardButton("⬆️ ارتقای بانک مرکزی", callback_data="bank:upgrade")])
        rows += [
            [InlineKeyboardButton("💰 سپرده", callback_data="bank:deposit")],
            [InlineKeyboardButton("💳 وام", callback_data="bank:loans")],
            [InlineKeyboardButton("📈 سرمایه‌گذاری", callback_data="bank:investments")],
            [InlineKeyboardButton("👥 جمعیت و مالیات", callback_data="bank:population")],
        ]
    return InlineKeyboardMarkup(rows)

def central_bank_deposit_keyboard(deposit_principal=0, accrued_profit=0):
    rows=[[InlineKeyboardButton("💰 سپرده‌گذاری", callback_data="bank:deposit_input", style="success")]]
    if float(deposit_principal or 0) > 0:
        rows.append([InlineKeyboardButton("📥 دریافت سپرده", callback_data="bank:withdraw_principal", style="primary")])
    if float(accrued_profit or 0) > 0:
        rows.append([InlineKeyboardButton("💹 دریافت سود سپرده", callback_data="bank:withdraw_profit", style="primary")])
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data="bank:open")])
    return InlineKeyboardMarkup(rows)

def central_bank_deposit_input_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data="bank:deposit")]])

def central_bank_withdraw_confirm_keyboard(kind):
    action = "bank:withdraw_profit_confirm" if kind == "profit" else "bank:withdraw_all_confirm"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ بله، برداشت شود", callback_data=action, style="success")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="bank:deposit")],
    ])

def central_bank_loans_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 درخواست وام", callback_data="bank:loan_request", style="success")],
        [InlineKeyboardButton("📋 وام‌های من", callback_data="bank:my_loans")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="bank:open")],
    ])

def central_bank_loan_input_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data="bank:loans")]])

def central_bank_loan_quote_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأیید و دریافت وام", callback_data="bank:loan_confirm", style="success")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="bank:loans")],
    ])

def central_bank_loan_detail_keyboard(loan_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💵 پرداخت قسط فعلی", callback_data=f"bank:loan_pay:{int(loan_id)}", style="success")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="bank:my_loans")],
    ])

def central_bank_investments_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 طرح‌های سرمایه‌گذاری", callback_data="bank:investment_plans")],
        [InlineKeyboardButton("💼 سرمایه‌گذاری‌های من", callback_data="bank:my_investments")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="bank:open")],
    ])

def central_bank_investment_plan_keyboard(index):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 سرمایه‌گذاری", callback_data=f"bank:investment_amount:{int(index)}", style="success")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="bank:investment_plans")],
    ])

def central_bank_investment_input_keyboard(index):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data=f"bank:investment_plan:{int(index)}")]])

def central_bank_investment_confirm_keyboard(index):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأیید سرمایه‌گذاری", callback_data=f"bank:investment_confirm:{int(index)}", style="success")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=f"bank:investment_plan:{int(index)}", style="danger")],
    ])

def central_bank_my_investments_keyboard(investments):
    rows=[]
    for inv in investments:
        rows.append([InlineKeyboardButton(f"📈 {str(inv.plan_name)[:45]}", callback_data=f"bank:my_investment:{int(inv.id)}")])
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data="bank:investments")])
    return InlineKeyboardMarkup(rows)

def central_bank_my_investment_detail_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data="bank:my_investments")]])

def central_bank_population_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧾 تنظیم مالیات", callback_data="bank:set_tax", style="primary")],
        [InlineKeyboardButton("💰 دریافت مالیات", callback_data="bank:withdraw_tax", style="success")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="bank:open")],
    ])

def central_bank_my_loans_keyboard(page=0, total_pages=1):
    rows=[]
    nav=[]
    if page>0: nav.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"bank:my_loans_page:{int(page)-1}"))
    if page<total_pages-1: nav.append(InlineKeyboardButton("بعدی ▶️", callback_data=f"bank:my_loans_page:{int(page)+1}"))
    if nav: rows.append(nav)
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data="bank:loans")])
    return InlineKeyboardMarkup(rows)

def hq_command_keyboard():
    return _reply_page_keyboard([[_reply_button("🔙 برگشت")]])


def mine_command_keyboard():
    return _reply_page_keyboard([[_reply_button("🔙 برگشت")]])


def country_command_keyboard(servants=0, free_servants=0):
    return _reply_page_keyboard([
        [_reply_button(f"خادمان: {int(servants)} تا  |  {int(free_servants)} آزاد")],
        [_reply_button("🔙 برگشت")],
    ])


def metal_mine_keyboard(
    can_build: bool = True,
    can_collect: bool = True,
    can_upgrade: bool = False,
    can_build_uranium: bool = True,
    can_upgrade_uranium: bool = True,
    construction_text: str | None = None,
    finish_uranium_cost: float = 0.0,
):
    rows = []
    if construction_text:
        rows.append([InlineKeyboardButton("🔙 برگشت", callback_data="metal_mine_cancel")])
        if float(finish_uranium_cost or 0.0) > 0:
            rows.append([InlineKeyboardButton(f"☢️ تکمیل فوری با {float(finish_uranium_cost):,.2f} اورانیوم", callback_data="metal_mine_finish_now")])
        rows.append([InlineKeyboardButton("🔄 به‌روزرسانی", callback_data="metal_mine_refresh")])
        return InlineKeyboardMarkup(rows)
    if can_build:
        rows.append([InlineKeyboardButton("🔨 ساخت با پول/فلز/سوخت", callback_data="metal_mine_build_preview:normal")])
        if can_build_uranium:
            rows.append([InlineKeyboardButton("☢️ ساخت با اورانیوم", callback_data="metal_mine_build_preview:uranium")])
    else:
        if can_collect:
            rows.append([InlineKeyboardButton("📥 دریافت فلز استخراج‌شده", callback_data="metal_mine_collect")])
        # تا وقتی سطح بعدی وجود دارد، دکمه ارتقا نمایش داده می‌شود؛
        # کمبود منابع با پنجره هشدار اعلام می‌شود. در حداکثر سطح، دکمه‌ها حذف می‌شوند.
        if can_upgrade:
            upgrade_row = [InlineKeyboardButton("⬆️ ارتقا با پول/فلز/سوخت", callback_data="metal_mine_upgrade_preview:normal")]
            if can_upgrade_uranium:
                upgrade_row.append(InlineKeyboardButton("☢️ ارتقا با اورانیوم", callback_data="metal_mine_upgrade_preview:uranium"))
            rows.append(upgrade_row)
    if not can_build:
        rows.append([InlineKeyboardButton("🔄 رفرش", callback_data="metal_mine_refresh")])
    return InlineKeyboardMarkup(rows)


def arsenal_cancel_confirm_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأیید برگشت", callback_data="arsenal_cancel_confirm")],
    ])

def arsenal_keyboard(can_build: bool = True, can_upgrade: bool = False, can_build_uranium: bool = True, can_upgrade_uranium: bool = True, construction_text: str | None = None, finish_uranium_cost: float = 0.0):
    rows = []
    if construction_text:
        rows.append([InlineKeyboardButton("🔙 برگشت", callback_data="arsenal_cancel")])
        if float(finish_uranium_cost or 0) > 0:
            rows.append([InlineKeyboardButton(f"☢️ تکمیل فوری با {float(finish_uranium_cost):,.2f} اورانیوم", callback_data="arsenal_finish_now")])
        return InlineKeyboardMarkup(rows)
    if can_build:
        rows.append([InlineKeyboardButton("🔨 ساخت با پول/فلز/سوخت", callback_data="arsenal_build_preview:normal")])
        if can_build_uranium:
            rows.append([InlineKeyboardButton("☢️ ساخت با اورانیوم", callback_data="arsenal_build_preview:uranium")])
    else:
        if can_upgrade:
            rows.append([InlineKeyboardButton("⬆️ ارتقا با پول/فلز/سوخت", callback_data="arsenal_upgrade_preview:normal")])
            if can_upgrade_uranium:
                rows.append([InlineKeyboardButton("☢️ ارتقا با اورانیوم", callback_data="arsenal_upgrade_preview:uranium")])
        # فقط وقتی زرادخانه واقعاً ساخته شده است، لیست موشک‌ها قابل نمایش است.
        rows.append([InlineKeyboardButton("🚀 لیست موشک‌ها", callback_data="arsenal_missiles")])
    return InlineKeyboardMarkup(rows)

# سازگاری با importهای قدیمی
ArsenalKeyboard = arsenal_keyboard


def construction_teams_user_keyboard(quotes=None):
    rows=[]
    for team, price, _, _ in (quotes or []):
        if float(price or 0) <= 0:
            label=f"🏗️ دریافت تیم {team} — 🆓 رایگان"
        else:
            label=f"🏗️ خرید تیم {team} — {float(price):,.0f} 💰"
        rows.append([InlineKeyboardButton(label, callback_data=f"construction:buy:{int(team)}", style="success")])
    # طبق طراحی جدید، پنل تیم‌های ساخت‌وساز دکمه برگشت شیشه‌ای ندارد.
    return InlineKeyboardMarkup(rows)


def store_command_keyboard(missiles=None):
    return _reply_page_keyboard([
        [_reply_button("🚀 خرید موشک")],
        [_reply_button("🛡️ خرید سپر")],
        [_reply_button("🏗️ تیم‌های ساخت‌وساز")],
        [_reply_button("🔙 برگشت")],
    ])

def shield_purchase_type_keyboard():
    return _reply_page_keyboard([
        [_reply_button("🛡️ خرید سپر جهانی"), _reply_button("🛡️ خرید سپر قاره‌ای")],
        [_reply_button("🔙 برگشت")],
    ])

def shield_purchase_list_keyboard(items, typ, page=1, per_page=10):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    rows=[]
    for item in items:
        rows.append([InlineKeyboardButton(
            f"🛡️ {item.get('name','سپر')} | ☢️ {float(item.get('price',0) or 0):,.0f} | ⏱ {float(item.get('duration_hours',0) or 0):g} ساعت",
            callback_data=f"shield:buy:{item.get('id')}"
        )])
    # برگشت این مرحله از طریق دکمه متنی «🔙 برگشت» انجام می‌شود و باید به فروشگاه برگردد.
    return InlineKeyboardMarkup(rows)

def shield_purchase_confirm_keyboard(item_id):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأیید خرید", callback_data=f"shield:confirm:{item_id}")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=f"shield:cancel:{item_id}")],
    ])

def missile_purchase_type_keyboard():
    return _reply_page_keyboard([
        [_reply_button("🚀 خرید موشک بالستیک"), _reply_button("🚀 خرید موشک کروز")],
        [_reply_button("⚡ خرید موشک هایپرسونیک")],
        [_reply_button("🔙 برگشت")],
    ])

def missile_purchase_list_keyboard(items):
    # فقط موشک‌های بازشده به‌عنوان دستور متنی قابل انتخاب نمایش داده می‌شوند.
    # موشک قفل‌شده در متن لیست با 🔒 دیده می‌شود، اما دستور خرید آن برای کاربر نمی‌آید.
    rows=[]
    for m in items:
        if bool(m.get("locked", False)):
            continue
        name=str(m.get("name","موشک")).strip()
        level=int(m.get("display_level",1) or 1)
        label=f"{name} — سطح {level}"
        rows.append([_reply_button(label)])
    rows.append([_reply_button("🔙 برگشت")])
    return _reply_page_keyboard(rows)

def exchange_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📊 نرخ تبادل",
                    callback_data="exchange:rates",
                )
            ],
        ]
    )


def arsenal_missile_list_keyboard(items):
    rows=[]
    for item in items:
        rows.append([InlineKeyboardButton(item["label"], callback_data=f"arsenal_sell_select:{item['mid']}:{item['level']}")])
    # دکمه برگشت فقط در «لیست موشک‌ها» وجود دارد؛ خود پنل اصلی زرادخانه دکمه برگشت شیشه‌ای ندارد.
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data="arsenal_missiles_back")])
    return InlineKeyboardMarkup(rows)

def arsenal_sell_quantity_keyboard(mid, level, available):
    """دکمه‌های فروش بر اساس موجودی واقعی همان موشک/سطح."""
    presets = (1, 2, 3, 5, 10, 15, 20, 30, 50, 100)
    rows=[]
    current=[]
    for qty in presets:
        if qty <= int(available):
            current.append(InlineKeyboardButton(str(qty), callback_data=f"arsenal_sell_qty:{mid}:{int(level)}:{qty}"))
            if len(current) == 5:
                rows.append(current); current=[]
    if current:
        rows.append(current)
    rows.append([InlineKeyboardButton("✏️ تعداد دلخواه", callback_data=f"arsenal_sell_custom:{mid}:{int(level)}")])
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data="arsenal_sell_quantity_back")])
    return InlineKeyboardMarkup(rows)

def arsenal_sell_confirm_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأیید فروش", callback_data="arsenal_sell_confirm")],
        [InlineKeyboardButton("🔙 تغییر تعداد", callback_data="arsenal_sell_change_qty")],
    ])

def arsenal_command_keyboard():
    # هنگام ورود به زرادخانه، کیبورد دستورات آماده باید فقط «برگشت» باشد.
    return _reply_page_keyboard([[_reply_button("🔙 برگشت")]])


def exchange_command_keyboard():
    return ReplyKeyboardMarkup(
        [
            [
                _reply_button("💰 پول به فلز"),
                _reply_button("🔩 فلز به پول"),
            ],
            [
                _reply_button("💰 پول به سوخت"),
                _reply_button("⛽ سوخت به پول"),
            ],
            [
                _reply_button("☢️ اورانیوم به سوخت"),
                _reply_button("☢️ اورانیوم به پول"),
            ],
            [
                _reply_button("🔙 برگشت"),
            ],
        ],
        resize_keyboard=True,
        is_persistent=False,
        one_time_keyboard=False,
    )


def exchange_confirm_keyboard():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ تأیید", callback_data="exchange_confirm")],
            [InlineKeyboardButton("❌ لغو", callback_data="exchange_cancel")],
        ]
    )


def exchange_input_keyboard():
    # در مرحله ورود مقدار تبادل، دکمه شیشه‌ای «برگشت» نمایش داده نمی‌شود؛
    # دستور متنی «🔙 برگشت» همچنان فعال است و در handlers/messages.py پردازش می‌شود.
    return None




def missile_technology_keyboard(missiles=None):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 موشک‌ها", callback_data="hq_tech_missiles", style="primary")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="hq_technology_back")],
    ])

def missile_technology_types_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 موشک‌های بالستیک", callback_data="hq_tech_type:بالستیک"),
         InlineKeyboardButton("🚀 موشک‌های کروز", callback_data="hq_tech_type:کروز")],
        [InlineKeyboardButton("⚡ موشک‌های هایپرسونیک", callback_data="hq_tech_type:هایپرسونیک")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="hq_technology")],
    ])

def missile_technology_list_keyboard(missiles, missile_type, tech_levels=None):
    rows = []
    tech_levels = tech_levels or {}
    supers = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
    current_row = []
    for m in missiles:
        name = str(m.get("name", "موشک")).strip()
        level = int(tech_levels.get(str(m.get("id")), 1) or 1)
        current_row.append(InlineKeyboardButton(f"{name} {str(level).translate(supers)}", callback_data=f"hq_tech_missile:{m.get('id')}"))
        if len(current_row) == 3:
            rows.append(current_row)
            current_row = []
    if current_row:
        rows.append(current_row)
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data="hq_technology")])
    return InlineKeyboardMarkup(rows)

def missile_upgrade_levels_keyboard(mid, current_level, next_level=None, in_progress=False):
    rows = []
    if in_progress:
        rows.append([InlineKeyboardButton("🔙 برگشت", callback_data=f"hq_tech_cancel:{mid}")])
        rows.append([InlineKeyboardButton("☢️ تکمیل فوری با اورانیوم", callback_data=f"hq_tech_finish_now:{mid}")])
        rows.append([InlineKeyboardButton("🔄 به‌روزرسانی", callback_data=f"hq_tech_refresh:{mid}")])
    elif next_level is not None:
        rows.append([InlineKeyboardButton(f"⬆️ ارتقا با پول/فلز/سوخت — سطح {int(next_level)}", callback_data=f"hq_tech_upgrade:{mid}:{int(next_level)}:normal")])
        rows.append([InlineKeyboardButton(f"☢️ ارتقا با اورانیوم — سطح {int(next_level)}", callback_data=f"hq_tech_upgrade:{mid}:{int(next_level)}:uranium")])
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data=f"hq_tech_missile_back:{mid}")])
    return InlineKeyboardMarkup(rows)

# سازگاری با نام‌های قدیمی/اشتباه برای تنظیمات ارتقای موشک.
# این تابع در گذشته در keyboards.admin قرار داشت، اما handlers.callbacks
# از keyboards.main نیز آن را import می‌کند.
def missile_upgrade_settings_keyboard(mid, level):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏳ زمان ارتقا", callback_data=f"owner:missile_level_edit:{mid}:{level}:upgrade_time")],
        [InlineKeyboardButton("💵 هزینه ارتقا با پول", callback_data=f"owner:missile_level_edit:{mid}:{level}:upgrade_money")],
        [InlineKeyboardButton("🔩 هزینه ارتقا با فلز", callback_data=f"owner:missile_level_edit:{mid}:{level}:upgrade_metal")],
        [InlineKeyboardButton("⛽ هزینه ارتقا با سوخت", callback_data=f"owner:missile_level_edit:{mid}:{level}:upgrade_fuel")],
        [InlineKeyboardButton("☢️ هزینه ارتقا با اورانیوم", callback_data=f"owner:missile_level_edit:{mid}:{level}:upgrade_uranium")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=f"owner:missile_level:{mid}:{level}")],
    ])

# نام‌های سازگار برای نسخه‌هایی که نام تابع را با حروف متفاوت import کرده‌اند.
MissileUpgradeSettingsKeyboard = missile_upgrade_settings_keyboard
MisealUpgradeSettingsKeyboard = missile_upgrade_settings_keyboard
MisealUpgradeSettings_Keyboard = missile_upgrade_settings_keyboard
