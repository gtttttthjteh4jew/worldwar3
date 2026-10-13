from telegram import CopyTextButton, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


PRIMARY = "primary"
SUCCESS = "success"
DANGER = "danger"


def _ib(text, callback_data=None, *, style=None, url=None, copy_text=None):
    kwargs = {}
    if callback_data is not None:
        kwargs["callback_data"] = callback_data
    if url is not None:
        kwargs["url"] = url
    if copy_text is not None:
        kwargs["copy_text"] = CopyTextButton(text=str(copy_text))
    if style:
        kwargs["style"] = style
    return InlineKeyboardButton(text, **kwargs)


def _kb(text, *, style=None):
    kwargs = {"text": text}
    if style:
        kwargs["style"] = style
    return KeyboardButton(**kwargs)


def wallet_back_reply_keyboard(label="🔙 برگشت"):
    return ReplyKeyboardMarkup(
        [[_kb(label, style=DANGER)]],
        resize_keyboard=True,
        is_persistent=False,
        one_time_keyboard=False,
        input_field_placeholder="برای برگشت، دکمه زیر را بزنید",
    )


def wallet_reply_keyboard():
    # Telegram renders rows according to the client locale/direction. The vector order here is
    # kept as withdrawal first / deposit second so in the RTL UI the deposit action sits on the right.
    return ReplyKeyboardMarkup(
        [
            [_kb("📤 برداشت", style=PRIMARY), _kb("➕ افزایش موجودی", style=SUCCESS)],
            [_kb("📜 تراکنش‌ها", style=PRIMARY)],
            [_kb("🔙 برگشت", style=DANGER)],
        ],
        resize_keyboard=True,
        is_persistent=False,
        one_time_keyboard=False,
        input_field_placeholder="کیف پول",
    )


def withdrawal_amount_keyboard(balance: int):
    rows = [
        [_kb("5٪ موجودی", style=PRIMARY), _kb("10٪ موجودی", style=PRIMARY)],
        [_kb("20٪ موجودی", style=PRIMARY), _kb("25٪ موجودی", style=PRIMARY)],
        [_kb("50٪ موجودی", style=PRIMARY), _kb("100٪ موجودی", style=PRIMARY)],
        [_kb("💰 مبلغ دلخواه", style=SUCCESS)],
        [_kb("🔙 برگشت", style=DANGER)],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, is_persistent=False, one_time_keyboard=False, input_field_placeholder="مقدار برداشت را انتخاب کنید")

def account_settings_keyboard():
    return ReplyKeyboardMarkup(
        [[_kb("💰 کیف پول", style=SUCCESS)], [_kb("🔙 برگشت", style=DANGER)]],
        resize_keyboard=True,
        is_persistent=False,
        one_time_keyboard=False,
        input_field_placeholder="تنظیمات اکانت",
    )


def wallet_back_inline(callback="wallet:home"):
    return InlineKeyboardMarkup([[_ib("🔙 برگشت", callback, style=DANGER)]])


def wallet_deposit_methods_keyboard(session):
    from services.wallet import get_bool
    from services.wallet import WALLET_CARD_ENABLED, ZP_ENABLED, CRYPTO_ENABLED, STARS_ENABLED
    rows = []
    if get_bool(session, WALLET_CARD_ENABLED):
        rows.append([_ib("💳 کارت به کارت", "wallet:deposit:card", style=SUCCESS)])
    if get_bool(session, ZP_ENABLED):
        rows.append([_ib("🏦 درگاه زرین‌پال", "wallet:deposit:zarinpal", style=PRIMARY)])
    if get_bool(session, CRYPTO_ENABLED):
        rows.append([_ib("₿ رمز ارز", "wallet:deposit:crypto", style=PRIMARY)])
    if get_bool(session, STARS_ENABLED):
        rows.append([_ib("⭐ استارز", "wallet:deposit:stars", style=SUCCESS)])
    return InlineKeyboardMarkup(rows)


def card_select_keyboard(cards, back_callback="wallet:deposit_methods"):
    rows = [
        [_ib(f"💳 {card.bank_name or 'ثبت نشده'} — {card.owner_name}", f"wallet:card_select:{card.id}", style=PRIMARY)]
        for card in cards
    ]
    rows.append([_ib("🔙 برگشت", back_callback, style=DANGER)])
    return InlineKeyboardMarkup(rows)


def card_request_keyboard(transaction_id, can_submit=True, *, payable_rial=None, card_number=None, back_callback="wallet:deposit_methods"):
    rows = []
    if can_submit and payable_rial is not None and card_number:
        rows.append([
            _ib("📋 کپی مبلغ", copy_text=str(int(payable_rial)), style=PRIMARY),
            _ib("💳 کپی شماره کارت", copy_text=str(card_number), style=PRIMARY),
        ])
    elif payable_rial is not None:
        rows.append([_ib("📋 کپی مبلغ", copy_text=str(int(payable_rial)), style=PRIMARY)])
    if can_submit:
        rows.append([_ib("📤 ارسال رسید", f"wallet:card_activate:{transaction_id}", style=SUCCESS)])
    rows.append([_ib("❌ لغو", f"wallet:cancel:{transaction_id}", style=DANGER)])
    if not can_submit:
        rows.append([_ib("🔙 برگشت", back_callback, style=DANGER)])
    return InlineKeyboardMarkup(rows)


def receipt_upload_keyboard(transaction_id):
    return InlineKeyboardMarkup([
        [_ib("🔙 برگشت", f"wallet:receipt_back:{transaction_id}", style=DANGER)],
    ])


def receipt_confirm_keyboard(transaction_id):
    return InlineKeyboardMarkup([
        [_ib("✅ تأیید و ارسال رسید", f"wallet:receipt_confirm:{transaction_id}", style=SUCCESS)],
        [_ib("✏️ ویرایش", f"wallet:receipt_edit:{transaction_id}", style=PRIMARY)],
        [_ib("❌ لغو", f"wallet:cancel:{transaction_id}", style=DANGER)],
        [_ib("🔙 برگشت", f"wallet:receipt_back:{transaction_id}", style=DANGER)],
    ])


def crypto_coin_keyboard(back_callback="wallet:deposit_methods"):
    return InlineKeyboardMarkup([
        [_ib("₿ بیت‌کوین (BTC)", "wallet:crypto_coin:BTC", style=PRIMARY)],
        [_ib("₮ تتر (USDT)", "wallet:crypto_coin:USDT", style=PRIMARY)],
        [_ib("💎 تون‌کوین (TON)", "wallet:crypto_coin:TON", style=SUCCESS)],
        [_ib("🔙 برگشت", back_callback, style=DANGER)],
    ])


def crypto_destination_keyboard(destinations, back_callback="wallet:deposit:crypto"):
    rows = [
        [_ib(f"{d.coin} — {d.network}", f"wallet:crypto_dest:{d.id}", style=PRIMARY)]
        for d in destinations
    ]
    rows.append([_ib("🔙 برگشت", back_callback, style=DANGER)])
    return InlineKeyboardMarkup(rows)


def crypto_quote_keyboard(transaction_id, payment_url=None):
    rows = []
    if payment_url:
        rows.append([_ib("₿ پرداخت رمز ارزی", url=payment_url, style=SUCCESS)])
    rows += [
        [_ib("🔄 بررسی وضعیت پرداخت", f"wallet:crypto_check:{transaction_id}", style=PRIMARY)],
        [_ib("❌ لغو", f"wallet:cancel:{transaction_id}", style=DANGER)],
        [_ib("🔙 برگشت", "wallet:deposit:crypto", style=DANGER)],
    ]
    return InlineKeyboardMarkup(rows)


def zarinpal_payment_keyboard(transaction_id, payment_url):
    return InlineKeyboardMarkup([
        [_ib("🏦 پرداخت درگاه", url=payment_url, style=SUCCESS)],
        [_ib("❌ لغو درخواست", f"wallet:cancel:{transaction_id}", style=DANGER)],
        [_ib("🔙 برگشت", "wallet:deposit_methods", style=DANGER)],
    ])


def withdrawal_methods_keyboard():
    return InlineKeyboardMarkup([[
        _ib("💳 برداشت کارت‌به‌کارت", "wallet:withdraw_card", style=SUCCESS)
    ]])

def withdrawal_confirm_keyboard(transaction_id=None):
    if transaction_id is None:
        return InlineKeyboardMarkup([
            [_ib("✅ تأیید برداشت", "wallet:withdraw_confirm", style=SUCCESS)],
            [_ib("✏️ ویرایش", "wallet:withdraw_edit_draft", style=PRIMARY)],
            [_ib("❌ لغو", "wallet:withdraw_cancel_draft", style=DANGER)],
        ])
    return InlineKeyboardMarkup([
        [_ib("✅ تأیید برداشت", f"wallet:withdraw_confirm:{transaction_id}", style=SUCCESS)],
        [_ib("✏️ ویرایش", f"wallet:withdraw_edit:{transaction_id}", style=PRIMARY)],
        [_ib("❌ لغو", f"wallet:cancel:{transaction_id}", style=DANGER)],
    ])


def transaction_list_keyboard(rows, page, pages):
    buttons = [[_ib(
        f"{'➕' if r.kind == 'deposit' else '📤'} {r.transaction_no} — {r.credited_amount if r.kind == 'deposit' else r.requested_amount:,}",
        f"wallet:tx:{r.id}:{page}",
        style=SUCCESS if r.kind == "deposit" else PRIMARY,
    )] for r in rows]
    if pages > 1:
        nav = []
        if page > 1:
            nav.append(_ib("⬅️ قبلی", f"wallet:transactions:{page-1}", style=PRIMARY))
        nav.append(_ib(f"📄 {page}/{pages}", "wallet:noop"))
        if page < pages:
            nav.append(_ib("بعدی ➡️", f"wallet:transactions:{page+1}", style=PRIMARY))
        buttons.append(nav)
    return InlineKeyboardMarkup(buttons)


# ---------------------------------------------------------------------------
# Owner keyboards
# ---------------------------------------------------------------------------
def owner_wallet_manual_keyboard():
    return InlineKeyboardMarkup([
        [_ib("➕ واریز دستی", "owner:wallet_manual:deposit", style=SUCCESS)],
        [_ib("➖ برداشت دستی", "owner:wallet_manual:withdraw", style=DANGER)],
        [_ib("🔙 برگشت", "owner:wallet", style=DANGER)],
    ])


def owner_wallet_manual_mode_keyboard(action):
    return InlineKeyboardMarkup([
        [_ib("1️⃣ تک‌کاربره", f"owner:wallet_manual_mode:{action}:single", style=PRIMARY)],
        [_ib("👥 چندکاربره", f"owner:wallet_manual_mode:{action}:multiple", style=PRIMARY)],
        [_ib("🔙 برگشت", "owner:wallet_manual", style=DANGER)],
    ])


def owner_wallet_manual_users_keyboard(action, count=0):
    rows=[]
    if count:
        rows.append([_ib(f"➕ افزودن کاربر دیگر ({count})", f"owner:wallet_manual_more:{action}", style=PRIMARY)])
        rows.append([_ib("✅ پایان انتخاب کاربران", f"owner:wallet_manual_finish:{action}", style=SUCCESS)])
    rows.append([_ib("🔙 برگشت", "owner:wallet_manual", style=DANGER)])
    return InlineKeyboardMarkup(rows)


def owner_wallet_manual_confirm_keyboard():
    return InlineKeyboardMarkup([
        [_ib("✅ تأیید عملیات", "owner:wallet_manual_confirm", style=SUCCESS)],
        [_ib("✏️ ویرایش", "owner:wallet_manual_edit", style=PRIMARY)],
        [_ib("🔙 لغو", "owner:wallet_manual_cancel", style=DANGER)],
    ])


def owner_wallet_keyboard(session):
    return InlineKeyboardMarkup([
        [_ib("💸 واریز / برداشت موجودی کاربران", "owner:wallet_manual", style=SUCCESS)],
        [_ib("⚙️ تنظیمات عمومی", "owner:wallet_general", style=PRIMARY)],
        [_ib("📤 تنظیمات برداشت", "owner:wallet_withdraw", style=PRIMARY), _ib("💳 تنظیمات افزایش موجودی", "owner:wallet_payment_methods", style=SUCCESS)],
        [_ib("📋 تنظیمات درخواست‌ها", "owner:wallet_request_settings", style=PRIMARY)],
        [_ib("📊 آمار", "owner:wallet_stats", style=PRIMARY)],
        [_ib("🔙 برگشت", "owner:back", style=DANGER)],
    ])


def owner_wallet_general_keyboard(session):
    from services.wallet import get_bool, WALLET_ENABLED
    enabled = get_bool(session, WALLET_ENABLED)
    status_label = "🔴 غیرفعال کردن کیف پول" if enabled else "🟢 فعال کردن کیف پول"
    status_style = DANGER if enabled else SUCCESS
    return InlineKeyboardMarkup([
        [_ib(status_label, "owner:wallet_toggle", style=status_style)],
        [_ib("⏳ مهلت پرداخت", "owner:wallet_edit:expiry", style=PRIMARY)],
        [_ib("🔙 برگشت", "owner:wallet", style=DANGER)],
    ])

def session_wallet_int(session, key):
    from services.wallet import get_int
    return get_int(session, key, 0)


def owner_wallet_identifier_keyboard(session):
    return InlineKeyboardMarkup([
        [_ib("🔢 ثبت بازه مبلغ شناسایی", "owner:wallet_identifier_edit", style=PRIMARY)],
        [_ib("🔙 برگشت", "owner:wallet_card_payment", style=DANGER)],
    ])

def owner_wallet_payment_methods_keyboard(session):
    return InlineKeyboardMarkup([
        [_ib("💳 کارت‌به‌کارت", "owner:wallet_card_payment", style=SUCCESS), _ib("🏦 درگاه زرین‌پال", "owner:wallet_gateway", style=PRIMARY)],
        [_ib("₿ رمز ارز", "owner:wallet_crypto", style=PRIMARY), _ib("⭐ استارز", "owner:wallet_stars", style=SUCCESS)],
        [_ib("🔙 برگشت", "owner:wallet", style=DANGER)],
    ])

def owner_card_payment_keyboard(session):
    from services.wallet import get_bool, WALLET_CARD_ENABLED, WALLET_CARD_ROTATION
    enabled = get_bool(session, WALLET_CARD_ENABLED)
    rotation = get_bool(session, WALLET_CARD_ROTATION)
    status_label = "🔴 غیرفعال کردن کارت‌به‌کارت" if enabled else "🟢 فعال کردن کارت‌به‌کارت"
    rotation_label = "🔴 غیرفعال کردن حالت چرخشی" if rotation else "🟢 فعال کردن حالت چرخشی"
    return InlineKeyboardMarkup([
        [_ib(status_label, "owner:wallet_card_enabled_toggle", style=DANGER if enabled else SUCCESS)],
        [_ib(rotation_label, "owner:wallet_card_rotation", style=DANGER if rotation else SUCCESS)],
        [_ib("🔽 حداقل مبلغ", "owner:wallet_card_edit:min", style=PRIMARY), _ib("🔼 حداکثر مبلغ", "owner:wallet_card_edit:max", style=PRIMARY)],
        [_ib("🔢 بازه مبلغ شناسایی", "owner:wallet_identifier_range", style=PRIMARY)],
        [_ib("🗑 حذف کارت‌ها", "owner:wallet_cards_delete", style=DANGER), _ib("➕ افزودن کارت", "owner:wallet_card_add", style=SUCCESS)],
        [_ib("📋 لیست کارت‌ها", "owner:wallet_cards_list", style=PRIMARY)],
        [_ib("🔙 برگشت", "owner:wallet_payment_methods", style=DANGER)],
    ])

def owner_wallet_cards_keyboard(cards):
    rows = []
    for c in cards:
        status = "🟢" if bool(c.enabled) else "🔴"
        bank = c.bank_name or "ثبت نشده"
        rows.append([_ib(f"{status} 💳 {bank} — {c.owner_name}", f"owner:wallet_card:{c.id}", style=PRIMARY)])
    rows.append([_ib("🔙 برگشت", "owner:wallet_cards", style=DANGER)])
    return InlineKeyboardMarkup(rows)


def owner_wallet_card_delete_confirm_keyboard(card):
    bank = card.bank_name or "ثبت نشده"
    return InlineKeyboardMarkup([
        [_ib("✅ تأیید حذف", f"owner:wallet_card_delete_confirm:{card.id}:yes", style=DANGER)],
        [_ib("❌ لغو", f"owner:wallet_card_delete_confirm:{card.id}:no", style=PRIMARY)],
    ])


def owner_wallet_card_delete_keyboard(cards):
    rows = [[_ib(f"🗑 {c.bank_name} — {c.owner_name}", f"owner:wallet_card_delete:{c.id}", style=DANGER)] for c in cards]
    rows.append([_ib("🔙 برگشت", "owner:wallet_cards", style=DANGER)])
    return InlineKeyboardMarkup(rows)


def owner_card_skip_keyboard(field, back="owner:wallet_card_payment"):
    labels = {
        "bank": "⏭ بدون بانک",
        "iban": "⏭ بدون شبا",
        "account": "⏭ بدون شماره حساب",
        "description": "⏭ بدون توضیحات",
    }
    return InlineKeyboardMarkup([
        [_ib(labels.get(field, "⏭ رد کردن"), f"owner:wallet_card_add_skip:{field}", style=PRIMARY)],
        [_ib("🔙 برگشت", back, style=DANGER)],
    ])

def owner_card_draft_confirm_keyboard():
    return InlineKeyboardMarkup([
        [_ib("✅ تأیید", "owner:wallet_card_add_confirm:save", style=SUCCESS)],
        [_ib("✏️ ویرایش", "owner:wallet_card_add_confirm:edit", style=PRIMARY)],
        [_ib("❌ لغو", "owner:wallet_card_add_confirm:cancel", style=DANGER)],
    ])

def owner_wallet_card_detail_keyboard(card):
    toggle_label = "🔴 غیرفعال کردن کارت" if bool(card.enabled) else "🟢 فعال کردن کارت"
    toggle_style = DANGER if bool(card.enabled) else SUCCESS
    return InlineKeyboardMarkup([
        [_ib("✏️ ویرایش اطلاعات", f"owner:wallet_card_edit:{card.id}", style=PRIMARY)],
        [_ib(toggle_label, f"owner:wallet_card_toggle:{card.id}", style=toggle_style)],
        [_ib("🗑 حذف کارت", f"owner:wallet_card_delete:{card.id}", style=DANGER)],
        [_ib("🔙 برگشت", "owner:wallet_cards_list", style=DANGER)],
    ])


def owner_wallet_gateway_keyboard(session):
    from services.wallet import get_bool, ZP_ENABLED
    enabled = get_bool(session, ZP_ENABLED)
    return InlineKeyboardMarkup([
        [_ib(("🔴 غیرفعال کردن درگاه" if enabled else "🟢 فعال کردن درگاه"), "owner:wallet_gateway_toggle:enabled", style=DANGER if enabled else SUCCESS)],
        [_ib("🪪 شناسه پذیرنده", "owner:wallet_gateway_edit:merchant", style=PRIMARY), _ib("➕ درصد افزایش مبلغ", "owner:wallet_gateway_edit:markup", style=PRIMARY)],
        [_ib("🔽 حداقل مبلغ", "owner:wallet_gateway_edit:min", style=PRIMARY), _ib("🔼 حداکثر مبلغ", "owner:wallet_gateway_edit:max", style=PRIMARY)],
        [_ib("📝 توضیحات پرداخت", "owner:wallet_gateway_edit:description", style=PRIMARY)],
        [_ib("🔙 برگشت", "owner:wallet_payment_methods", style=DANGER)],
    ])

def owner_wallet_crypto_keyboard(session, destinations=None):
    from services.wallet import get_bool, CRYPTO_ENABLED, CRYPTO_CLIENT_ID, CRYPTO_CLIENT_SECRET, CRYPTO_WEBHOOK_ENABLED
    enabled = get_bool(session, CRYPTO_ENABLED)
    client_id = bool(__import__("services.wallet", fromlist=["get_setting"]).get_setting(session, CRYPTO_CLIENT_ID, "").strip())
    secret = bool(__import__("services.wallet", fromlist=["get_setting"]).get_setting(session, CRYPTO_CLIENT_SECRET, "").strip())
    ready = client_id and secret
    rows = [
        [_ib(("🔴 غیرفعال کردن رمز ارز" if enabled else "🟢 فعال کردن رمز ارز"), "owner:wallet_crypto_toggle:enabled", style=DANGER if enabled else SUCCESS)],
        [_ib("🔑 شناسه اتصال", "owner:wallet_crypto_edit:client_id", style=PRIMARY), _ib("🔐 کلید محرمانه", "owner:wallet_crypto_edit:client_secret", style=PRIMARY)],
        [_ib("➕ درصد افزایش", "owner:wallet_crypto_edit:markup", style=PRIMARY)],
        [_ib("🔽 حداقل مبلغ", "owner:wallet_crypto_edit:min", style=PRIMARY), _ib("🔼 حداکثر مبلغ", "owner:wallet_crypto_edit:max", style=PRIMARY)],
        [_ib(("🟢 وب‌هوک فعال" if get_bool(session, CRYPTO_WEBHOOK_ENABLED) else "🔴 وب‌هوک غیرفعال"), "owner:wallet_crypto_toggle:webhook", style=SUCCESS if get_bool(session, CRYPTO_WEBHOOK_ENABLED) else DANGER)],
        [_ib("🔄 بررسی اتصال", "owner:wallet_crypto_test", style=PRIMARY)],
        [_ib("🔙 برگشت", "owner:wallet_payment_methods", style=DANGER)],
    ]
    return InlineKeyboardMarkup(rows)


def owner_crypto_dest_step_keyboard(step):
    if step == "coin":
        return InlineKeyboardMarkup([
            [_ib("₿ بیت‌کوین", "owner:wallet_crypto_dest_coin:BTC", style=PRIMARY), _ib("₮ تتر", "owner:wallet_crypto_dest_coin:USDT", style=PRIMARY)],
            [_ib("💎 تون‌کوین", "owner:wallet_crypto_dest_coin:TON", style=SUCCESS)],
            [_ib("🔙 برگشت", "owner:wallet_crypto", style=DANGER)],
        ])
    if step == "description":
        return InlineKeyboardMarkup([
            [_ib("⏭ بدون توضیحات", "owner:wallet_crypto_dest_skip:description", style=PRIMARY)],
            [_ib("🔙 برگشت", "owner:wallet_crypto", style=DANGER)],
        ])
    return wallet_back_inline("owner:wallet_crypto")

def owner_crypto_dest_draft_confirm_keyboard():
    return InlineKeyboardMarkup([
        [_ib("✅ تأیید", "owner:wallet_crypto_dest_confirm:save", style=SUCCESS)],
        [_ib("✏️ ویرایش", "owner:wallet_crypto_dest_confirm:edit", style=PRIMARY)],
        [_ib("❌ لغو", "owner:wallet_crypto_dest_confirm:cancel", style=DANGER)],
    ])

def owner_wallet_crypto_dest_detail_keyboard(dest):
    return InlineKeyboardMarkup([
        [_ib("✏️ ویرایش", f"owner:wallet_crypto_dest_edit:{dest.id}", style=PRIMARY)],
        [_ib("🔄 تغییر وضعیت مقصد", f"owner:wallet_crypto_dest_toggle:{dest.id}", style=PRIMARY)],
        [_ib("🗑 حذف", f"owner:wallet_crypto_dest_delete:{dest.id}", style=DANGER)],
        [_ib("🔙 برگشت", "owner:wallet_crypto", style=DANGER)],
    ])


def owner_wallet_stars_keyboard(session):
    from services.wallet import get_bool, STARS_ENABLED
    enabled = get_bool(session, STARS_ENABLED)
    return InlineKeyboardMarkup([
        [_ib(("🔴 غیرفعال کردن استارز" if enabled else "🟢 فعال کردن استارز"), "owner:wallet_stars_toggle", style=DANGER if enabled else SUCCESS)],
        [_ib("💰 تنظیم ارزش هر استار", "owner:wallet_stars_edit:rate", style=PRIMARY)],
        [_ib("🔽 حداقل مبلغ", "owner:wallet_stars_edit:min", style=PRIMARY), _ib("🔼 حداکثر مبلغ", "owner:wallet_stars_edit:max", style=PRIMARY)],
        [_ib("⭐ موجودی استارز ربات", "owner:wallet_stars_balance", style=SUCCESS)],
        [_ib("📝 توضیحات فاکتور", "owner:wallet_stars_edit:description", style=PRIMARY)],
        [_ib("🔙 برگشت", "owner:wallet_payment_methods", style=DANGER)],
    ])

def owner_wallet_withdraw_keyboard(session):
    from services.wallet import get_bool, WITHDRAW_ENABLED
    enabled = get_bool(session, WITHDRAW_ENABLED)
    status_label = "🔴 غیرفعال کردن برداشت" if enabled else "🟢 فعال کردن برداشت"
    status_style = DANGER if enabled else SUCCESS
    return InlineKeyboardMarkup([
        [_ib(status_label, "owner:wallet_withdraw_toggle:enabled", style=status_style)],
        [_ib("📤 حداقل برداشت", "owner:wallet_withdraw_edit:min", style=PRIMARY), _ib("📤 حداکثر برداشت", "owner:wallet_withdraw_edit:max", style=PRIMARY)],
        [_ib("🔢 سقف تعداد برداشت روزانه هر کاربر", "owner:wallet_withdraw_edit:daily_count", style=PRIMARY)],
        [_ib("🔙 برگشت", "owner:wallet", style=DANGER)],
    ])

def owner_wallet_request_settings_keyboard():
    return InlineKeyboardMarkup([
        [_ib("⏳ در انتظار", "owner:wallet_requests:pending:1", style=PRIMARY), _ib("✅ تأیید شده", "owner:wallet_requests:approved:1", style=SUCCESS)],
        [_ib("❌ رد شده", "owner:wallet_requests:rejected:1", style=DANGER)],
        [_ib("🔎 جستجوی درخواست", "owner:wallet_request_search", style=PRIMARY)],
        [_ib("🔙 برگشت", "owner:wallet", style=DANGER)],
    ])


def owner_request_list_keyboard(rows, page, pages, group):
    buttons = []
    for tx in rows:
        icon = "➕" if tx.kind == "deposit" else "📤"
        style = SUCCESS if tx.status == "APPROVED" else DANGER if tx.status == "REJECTED" else PRIMARY
        buttons.append([_ib(f"{icon} {tx.transaction_no} — {tx.requested_amount:,} تومان", f"owner:wallet_request_tx:{tx.id}:{group}", style=style)])
    nav = []
    if pages > 1:
        if page > 1:
            nav.append(_ib("⬅️ قبلی", f"owner:wallet_requests:{group}:{page-1}", style=PRIMARY))
        nav.append(_ib(f"📄 {page}/{pages}", "owner:wallet_noop"))
        if page < pages:
            nav.append(_ib("بعدی ➡️", f"owner:wallet_requests:{group}:{page+1}", style=PRIMARY))
        buttons.append(nav)
    buttons.append([_ib("🔙 برگشت", "owner:wallet_request_settings", style=DANGER)])
    return InlineKeyboardMarkup(buttons)


def owner_request_detail_keyboard(tx, *, back_callback="owner:wallet_request_settings"):
    rows = []
    if tx.status == "WAITING_OWNER" and tx.kind == "deposit":
        rows.append([_ib("✅ تأیید", f"owner:wallet_approve:{tx.id}", style=SUCCESS), _ib("✏️ ویرایش", f"owner:wallet_edit_tx:{tx.id}", style=PRIMARY)])
        rows.append([_ib("❌ رد", f"owner:wallet_reject:{tx.id}", style=DANGER)])
    elif tx.status == "WAITING_OWNER" and tx.kind == "withdrawal":
        rows.append([_ib("📤 ارسال رسید واریز", f"owner:wallet_withdraw_receipt:{tx.id}", style=SUCCESS), _ib("❌ رد برداشت", f"owner:wallet_reject_withdraw:{tx.id}", style=DANGER)])
    rows.append([_ib("🔙 برگشت", back_callback, style=DANGER)])
    return InlineKeyboardMarkup(rows)


def owner_search_request_keyboard():
    return InlineKeyboardMarkup([[_ib("🔙 برگشت", "owner:wallet_request_settings", style=DANGER)]])


def owner_wallet_stats_keyboard():
    return InlineKeyboardMarkup([[_ib("🔙 برگشت", "owner:wallet", style=DANGER)]])


def owner_pending_transactions_keyboard(rows, page, pages):
    return owner_request_list_keyboard(rows, page, pages, "pending")


def owner_deposit_action_keyboard(tx_id):
    return InlineKeyboardMarkup([
        [_ib("✅ تأیید", f"owner:wallet_approve:{tx_id}", style=SUCCESS)],
        [_ib("✏️ ویرایش", f"owner:wallet_edit_tx:{tx_id}", style=PRIMARY)],
        [_ib("❌ رد", f"owner:wallet_reject:{tx_id}", style=DANGER)],
    ])


def owner_withdraw_action_keyboard(tx_id):
    return InlineKeyboardMarkup([
        [_ib("📤 ارسال رسید واریز", f"owner:wallet_withdraw_receipt:{tx_id}", style=SUCCESS)],
        [_ib("❌ رد برداشت", f"owner:wallet_reject_withdraw:{tx_id}", style=DANGER)],
    ])


def owner_rejection_keyboard(tx_id):
    return InlineKeyboardMarkup([
        [_ib("🚫 بدون دلیل", f"owner:wallet_reject_no_reason:{tx_id}", style=DANGER)],
        [_ib("✍️ وارد کردن دلیل", f"owner:wallet_reject_reason:{tx_id}", style=PRIMARY)],
        [_ib("🔙 برگشت", f"owner:wallet_request_tx:{tx_id}:pending", style=DANGER)],
    ])


def owner_rejection_confirm_keyboard(tx_id):
    return InlineKeyboardMarkup([
        [_ib("✅ تأیید رد", f"owner:wallet_reject_confirm_reason:{tx_id}", style=DANGER)],
        [_ib("✏️ ویرایش دلیل", f"owner:wallet_reject_reason:{tx_id}", style=PRIMARY)],
        [_ib("🔙 برگشت", f"owner:wallet_request_tx:{tx_id}:pending", style=DANGER)],
    ])


def owner_edit_confirm_keyboard(tx_id):
    return InlineKeyboardMarkup([
        [_ib("✅ تأیید مبلغ جدید", f"owner:wallet_edit_confirm:{tx_id}", style=SUCCESS)],
        [_ib("🔙 برگشت", f"owner:wallet_request_tx:{tx_id}:pending", style=DANGER)],
    ])
