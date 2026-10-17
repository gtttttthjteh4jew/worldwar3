from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def admin_panel_keyboard():
    # پنل مدیریت
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 مدیریت کاربران", callback_data="admin:users")],
        [InlineKeyboardButton("📩 ارسال پیام", callback_data="admin:messages")],
        [InlineKeyboardButton("📊 آمار", callback_data="admin:stats")],
    ])


def owner_panel_keyboard():
    # پنل مالک عمداً دکمه برگشت ندارد.
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👨‍💼 مدیریت ادمین‌ها", callback_data="owner:admins")],
        [InlineKeyboardButton("🎮 تنظیمات بازی", callback_data="owner:economy")],
        [InlineKeyboardButton("🛠️ تنظیمات عمومی ربات", callback_data="owner:general_settings")],
        [InlineKeyboardButton("💰 کیف پول و پرداخت‌ها", callback_data="owner:wallet", style="success")],
        [InlineKeyboardButton("🧩 چالش‌ها", callback_data="owner:challenges")],
    ])


def owner_challenges_keyboard():
    """دسته‌بندی واحد برای مدیریت انیگما و جعبه‌ها."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔐 مدیریت انیگما", callback_data="owner:enigma")],
        [InlineKeyboardButton("🎁 مدیریت جعبه‌ها", callback_data="owner:golden")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="owner:back")],
    ])


def admin_management_keyboard():
    """
    صفحه اصلی مدیریت ادمین‌ها
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ افزودن ادمین", callback_data="owner:add_admin"),
            InlineKeyboardButton("➖ حذف ادمین", callback_data="owner:remove_admin"),
        ],
        [
            InlineKeyboardButton("🔎 جستجوی ادمین", callback_data="owner:search_admin"),
            InlineKeyboardButton("📋 لیست ادمین‌ها", callback_data="owner:list_admins:1"),
        ],
        [
            InlineKeyboardButton(
                "🛡️ دسترسی ادمین‌ها",
                callback_data="owner:admin_permissions_menu",
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 برگشت",
                callback_data="owner:back",
            )
        ],
    ])


def add_admin_mode_keyboard():
    """
    بعد از زدن افزودن ادمین:
    افزودن تکی / افزودن چندتایی / برگشت
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "1️⃣ افزودن تکی",
                callback_data="owner:add_single",
            )
        ],
        [
            InlineKeyboardButton(
                "2️⃣ افزودن چندتایی",
                callback_data="owner:add_multiple",
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 برگشت",
                callback_data="owner:back_admins",
            )
        ],
    ])


def admin_confirm_keyboard(action: str):
    """تأیید افزودن/حذف تکی ادمین؛ همه در همان پنل."""
    edit_action = "add_admin" if action == "add_admin" else "remove_admin"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأیید", callback_data=f"owner:confirm:{action}")],
        [InlineKeyboardButton("✏️ ویرایش", callback_data=f"owner:edit:{edit_action}")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="owner:back_admins")],
    ])


def admin_multiple_confirm_keyboard():
    """تأیید نهایی افزودن چند ادمین؛ برگشت به انتخاب روش افزودن."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأیید افزودن همه", callback_data="owner:confirm_multiple")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="owner:add_admin")],
    ])


def remove_admin_mode_keyboard():
    """انتخاب حذف تکی یا چندتایی."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("1️⃣ حذف تکی", callback_data="owner:remove_single")],
        [InlineKeyboardButton("2️⃣ حذف چندتایی", callback_data="owner:remove_multiple")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="owner:back_admins")],
    ])


def remove_multiple_confirm_keyboard():
    """تأیید نهایی حذف چند ادمین؛ برگشت به انتخاب روش حذف."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأیید حذف همه", callback_data="owner:confirm_remove_multiple")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="owner:remove_admin")],
    ])


def admin_search_result_keyboard(user_id: int | None = None):
    rows = []
    if user_id is not None:
        rows.append([InlineKeyboardButton("✅ تأیید اطلاعات و ورود به اطلاعات ادمین", callback_data=f"owner:admin_search_confirm:{user_id}")])
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data="owner:search_admin")])
    return InlineKeyboardMarkup(rows)


def admin_info_keyboard(user_id: int, back_callback: str = "owner:back_admins", banned: bool = False):
    rows = [
        [InlineKeyboardButton("👑 مدیریت ادمینی کاربر", callback_data=f"admin:user_admin:{user_id}")],
        [InlineKeyboardButton("🎮 تنظیمات بازی", callback_data=f"admin:user_game_settings:{user_id}:admin")],
    ]
    rows.append([InlineKeyboardButton("✅ رفع بن" if banned else "🚫 بن", callback_data=f"admin:user_unban:{user_id}" if banned else f"admin:user_ban:{user_id}")])
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data=back_callback)])
    return InlineKeyboardMarkup(rows)


def admin_clear_confirm_keyboard():
    """تأیید پاکسازی همه ادمین‌ها؛ برگشت به خود لیست ادمین‌ها."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ بله، پاکسازی همه", callback_data="owner:confirm_clear_admins")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="owner:list_admins:1")],
    ])




def admin_step_back_keyboard(callback_data: str):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data=callback_data)]])


def economy_value_confirm_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأیید", callback_data="owner:economy_value_confirm")],
        [InlineKeyboardButton("✏️ ویرایش", callback_data="owner:economy_value_edit")],
        [InlineKeyboardButton("❌ لغو", callback_data="owner:economy_value_cancel")],
    ])

def admin_back_keyboard():
    """
    صفحات داخلی ادمین
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔙 برگشت",
                callback_data="owner:back_admins",
            )
        ]
    ])


def admin_permission_keyboard(target_id, perms):
    """صفحه اصلی سطح دسترسی: فقط سه بخش اصلی نمایش داده می‌شود."""
    def status(key):
        return "🟢 دسترسی فعال" if perms.get(key, True) else "🔴 دسترسی غیرفعال"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"👥 مدیریت کاربران | {status('users')}", callback_data=f"owner:admin_perm_section:{target_id}:users")],
        [InlineKeyboardButton(f"📩 ارسال پیام | {status('messages')}", callback_data=f"owner:admin_perm_section:{target_id}:messages")],
        [InlineKeyboardButton(f"📊 آمار بازی | {status('stats')}", callback_data=f"owner:admin_perm_section:{target_id}:stats")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=f"owner:admin_detail:{target_id}")],
    ])

def admin_permission_section_keyboard(target_id, section, perms):
    rows = []
    if section == "users":
        labels = [
            ("users", "👥 مدیریت کاربران"),
            ("user_search", "🔎 جستجوی کاربران"),
            ("user_info", "👤 اطلاعات کاربری"),
            ("user_account_settings", "🪪 تنظیمات اکانت"),
            ("game_settings", "🎮 تنظیمات بازی"),
            ("game_specs", "📊 مشخصات بازی کاربر"),
            ("country_name", "🌍 ویژگی نام کشور"),
            ("delete_country", "🗑️ حذف کشور کاربر"),
            ("swap_countries", "🔄 جابه‌جایی دو کشور"),
            ("reset_swap", "♻️ ریست جابه‌جایی"),
        ]
    elif section == "messages":
        labels = [
            ("messages", "📩 ارسال پیام"),
            ("message_private", "📩 پیام خصوصی"),
            ("message_public", "📢 پیام عمومی"),
            ("message_lists_private", "📋 لیست پیام‌های خصوصی"),
            ("message_lists_public", "📋 لیست پیام‌های عمومی"),
        ]
    else:
        labels = [("stats", "📊 آمار بازی")]
    for key, label in labels:
        enabled = perms.get(key, True)
        action = "🟢 غیرفعال کردن دسترسی" if enabled else "🔴 فعال کردن دسترسی"
        rows.append([InlineKeyboardButton(f"{label} | {action}", callback_data=f"owner:admin_perm:{target_id}:{key}")])
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data=f"owner:admin_permissions:{target_id}")])
    return InlineKeyboardMarkup(rows)

def admin_list_keyboard(page: int, total_pages: int, admins=None):
    """
    کیبورد مخصوص لیست ادمین‌ها.
    فقط دکمه‌های صفحه‌بندی + برگشت.
    """

    rows = []

    if admins:
        for adm in admins:
            rows.append([InlineKeyboardButton(f"👤 {adm[0]}", callback_data=f"owner:admin_detail:{adm[1]}")])

    navigation = []

    if page > 1:
        navigation.append(
            InlineKeyboardButton(
                "⬅️ قبلی",
                callback_data=f"owner:list_admins:{page - 1}",
            )
        )

    navigation.append(
        InlineKeyboardButton(
            f"📄 {page}/{total_pages}",
            callback_data="owner:list_noop",
        )
    )

    if page < total_pages:
        navigation.append(
            InlineKeyboardButton(
                "بعدی ➡️",
                callback_data=f"owner:list_admins:{page + 1}",
            )
        )

    rows.append(navigation)

    rows.append([
        InlineKeyboardButton(
            "🗑 پاکسازی همه ادمین‌ها",
            callback_data="owner:clear_admins",
        )
    ])
    rows.append([
        InlineKeyboardButton(
            "🔙 برگشت",
            callback_data="owner:back_admins",
        )
    ])

    return InlineKeyboardMarkup(rows)

def user_management_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 لیست کاربران", callback_data="admin:user_list:1")],
        [InlineKeyboardButton("🔎 جستجوی کاربران", callback_data="admin:search_users")],
        [InlineKeyboardButton("🛡 دسترسی‌ها", callback_data="admin:user_access")],
        [InlineKeyboardButton("⚙️ ابزارهای مدیریت کاربر", callback_data="admin:user_tools")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="admin:back")],
    ])

def user_management_tools_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 تغییر موجودی", callback_data="admin:balance_change")],
        [InlineKeyboardButton("👥 تغییر جمعیت", callback_data="admin:population_change")],
        [InlineKeyboardButton("🛡️ تنظیم سپر", callback_data="admin:shield_manage")],
        [InlineKeyboardButton("👑 تنظیم تجربه رهبری", callback_data="admin:leadership_change")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="admin:users")],
    ])


def leadership_change_mode_keyboard(back_callback="admin:user_tools"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("1️⃣ یک نفر", callback_data="admin:leadership_mode:single")],
        [InlineKeyboardButton("👥 چند نفر", callback_data="admin:leadership_mode:multiple")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=back_callback)],
    ])

def leadership_operation_keyboard(back_callback="admin:user_tools"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ افزودن تجربه", callback_data="admin:leadership_apply:add")],
        [InlineKeyboardButton("➖ کم کردن تجربه", callback_data="admin:leadership_apply:sub")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=back_callback)],
    ])

def leadership_multiple_keyboard(count=0):
    rows = []
    if count > 0:
        rows.append([InlineKeyboardButton(f"➕ افزودن نفر دیگر ({count})", callback_data="admin:leadership_more")])
        rows.append([InlineKeyboardButton("✅ پایان انتخاب", callback_data="admin:leadership_finish")])
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data="admin:user_tools")])
    return InlineKeyboardMarkup(rows)

def leadership_apply_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ افزودن تجربه", callback_data="admin:leadership_apply:add")],
        [InlineKeyboardButton("➖ کم کردن تجربه", callback_data="admin:leadership_apply:sub")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="admin:user_tools")],
    ])

def user_access_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚫 بن کاربر", callback_data="admin:ban_user")],
        [InlineKeyboardButton("✅ رفع بن کاربر", callback_data="admin:unban_user")],
        [InlineKeyboardButton("🚫 لیست بن‌شده‌ها", callback_data="admin:banned_list:1")],
        [InlineKeyboardButton("🔎 جستجوی کاربران بن‌شده", callback_data="admin:search_banned")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="admin:users")],
    ])


def user_search_mode_keyboard(banned=False):
    # جستجو دیگر به چهار دکمه جدا نیاز ندارد؛ ورودی می‌تواند هرکدام از چهار مشخصه باشد.
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 برگشت", callback_data="admin:user_access" if banned else "admin:users")]
    ])


def user_search_confirm_keyboard(user_id: int, back_callback: str = "admin:users", confirm_callback: str | None = None):
    confirm_data = confirm_callback or f"admin:search_confirm:{user_id}"
    if confirm_callback and "{user_id}" in confirm_data:
        confirm_data = confirm_data.format(user_id=user_id)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأیید", callback_data=confirm_data)],
        [InlineKeyboardButton("🔙 برگشت", callback_data=back_callback)],
    ])


def user_action_keyboard(user_id: int, viewer_is_owner: bool, back_callback: str = "admin:users", banned: bool = False, include_ban: bool = True):
    """دکمه‌های کامل صفحه اطلاعات کاربر."""
    rows = []
    # کاربر بن‌شده هرگز نباید از این صفحه قابل تبدیل به ادمین باشد.
    if viewer_is_owner and not banned:
        rows.append([InlineKeyboardButton("👑 مدیریت ادمینی کاربر", callback_data=f"admin:user_admin:{user_id}")])
    rows.append([InlineKeyboardButton("🎮 تنظیمات بازی", callback_data=f"admin:user_game_settings:{user_id}:user")])
    if include_ban:
        ban_label = "✅ رفع بن" if banned else "🚫 بن"
        ban_callback = f"admin:user_unban:{user_id}" if banned else f"admin:user_ban:{user_id}"
        rows.append([InlineKeyboardButton(ban_label, callback_data=ban_callback)])
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data=back_callback)])
    return InlineKeyboardMarkup(rows)


def admin_user_game_settings_keyboard(user_id: int, back_callback: str | None = None, include_country_name: bool = True):
    rows = [
        [InlineKeyboardButton("🎮 مشخصات بازی کاربر", callback_data=f"admin:user_game_specs:{user_id}")],
    ]
    if include_country_name:
        rows.append([InlineKeyboardButton("🌍 ویرایش نام کشور", callback_data=f"admin:user_country_edit:{user_id}")])
    rows += [
        [InlineKeyboardButton("🗑️ حذف کشور کاربر", callback_data=f"admin:user_country_delete:{user_id}")],
        [InlineKeyboardButton("🔄 جابه‌جایی دو کشور", callback_data=f"admin:user_swap:{user_id}")],
        [InlineKeyboardButton("♻️ ریست محدودیت جابه‌جایی", callback_data=f"admin:user_swap_reset:{user_id}")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=back_callback or f"admin:user:{user_id}")],
    ]
    return InlineKeyboardMarkup(rows)


def user_status_keyboard(user_id: int, banned: bool):
    # برای سازگاری با callbackهای قدیمی نگه داشته شده است؛
    # صفحه جزئیات جدید دیگر این صفحه را باز نمی‌کند.
    label = "✅ رفع بن" if banned else "🚫 بن"
    callback = f"admin:user_unban:{user_id}" if banned else f"admin:user_ban:{user_id}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data=callback)],
        [InlineKeyboardButton("🔙 برگشت", callback_data=f"admin:user:{user_id}")],
    ])




def user_leadership_country_keyboard(user_id: int, countries, back_callback=None):
    rows=[[InlineKeyboardButton(f"🌍 {c.title} — {float(c.leadership_experience or 0):,.0f}", callback_data=f"admin:user_leadership_country:{user_id}:{c.id}")] for c in countries]
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data=back_callback or f"admin:user:{user_id}")])
    return InlineKeyboardMarkup(rows)

def user_leadership_mode_keyboard(user_id: int, country_id: int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ افزودن تجربه", callback_data=f"admin:user_leadership_mode:{user_id}:{country_id}:add")],
        [InlineKeyboardButton("➖ کم کردن تجربه", callback_data=f"admin:user_leadership_mode:{user_id}:{country_id}:sub")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=f"admin:user_leadership:{user_id}")],
    ])

def user_game_specs_country_list_keyboard(user_id: int, countries, default_country_id=None, back_callback: str | None = None):
    rows=[]
    for c in countries:
        suffix = " ⭐" if default_country_id is not None and int(c.id) == int(default_country_id) else ""
        rows.append([InlineKeyboardButton(f"🌍 {c.title}{suffix}", callback_data=f"admin:user_game_country:{user_id}:{c.id}")])
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data=back_callback or f"admin:user_game_settings:{user_id}")])
    return InlineKeyboardMarkup(rows)


def user_country_list_keyboard(user_id: int, countries, back_callback: str | None = None):
    rows = [[InlineKeyboardButton(f"🌍 {c.title}", callback_data=f"admin:user_country_pick:{user_id}:{c.id}")] for c in countries]
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data=back_callback or f"admin:user:{user_id}")])
    return InlineKeyboardMarkup(rows)


def user_country_delete_list_keyboard(user_id: int, countries, back_callback: str | None = None):
    rows=[[InlineKeyboardButton(f"🗑️ {c.title}", callback_data=f"admin:user_country_delete_pick:{user_id}:{c.id}")] for c in countries]
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data=back_callback or f"admin:user:{user_id}")])
    return InlineKeyboardMarkup(rows)

def user_country_delete_confirm_keyboard(user_id: int, country_id: int):
    return InlineKeyboardMarkup([[InlineKeyboardButton("✅ تأیید حذف", callback_data=f"admin:user_country_delete_confirm:{user_id}:{country_id}")],[InlineKeyboardButton("🔙 برگشت", callback_data=f"admin:user_country_delete_cancel:{user_id}:{country_id}")]])

def user_admin_keyboard(user_id: int, is_admin_user: bool, back_callback: str = None):
    label = "➖ حذف از ادمینی" if is_admin_user else "➕ افزودن به ادمینی"
    callback = f"admin:user_admin_remove:{user_id}" if is_admin_user else f"admin:user_admin_add:{user_id}"
    rows = [[InlineKeyboardButton(label, callback_data=callback)]]
    # فقط وقتی شخص واقعاً ادمین است، تعیین سطح دسترسی نمایش داده شود.
    if is_admin_user:
        rows.append([InlineKeyboardButton("🛡️ تعیین سطح دسترسی", callback_data=f"admin:admin_permissions:{user_id}")])
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data=back_callback or f"admin:user:{user_id}")])
    return InlineKeyboardMarkup(rows)



def user_action_mode_keyboard(mode: str):
    """انتخاب عملیات تکی یا چندتایی برای بن/رفع بن."""
    title_single = "🚫 بن تکی" if mode == "ban" else "✅ رفع بن تکی"
    title_multi = "🚫 بن چندتایی" if mode == "ban" else "✅ رفع بن چندتایی"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(title_single, callback_data=f"admin:{mode}_single")],
        [InlineKeyboardButton(title_multi, callback_data=f"admin:{mode}_multiple")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="admin:user_access")],
    ])






def ban_multiple_ids_keyboard(back_callback="admin:user_access"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏁 پایان دریافت آیدی‌ها", callback_data="admin:ban_multiple_finish")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=back_callback)],
    ])

def ban_duration_keyboard(user_id=None, back_callback="admin:user_access"):
    uid = f":{user_id}" if user_id else ""
    return InlineKeyboardMarkup([[InlineKeyboardButton("⏱️ بن ساعتی",callback_data=f"admin:ban_duration:hour{uid}")],[InlineKeyboardButton("📅 بن روزانه",callback_data=f"admin:ban_duration:day{uid}")],[InlineKeyboardButton("♾️ بن دائم",callback_data=f"admin:ban_duration:permanent{uid}")],[InlineKeyboardButton("🔙 برگشت",callback_data=back_callback)]])

def ban_reason_keyboard(back_callback="admin:user_access"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🚫 بدون دلیل", callback_data="admin:ban_reason_empty")],[InlineKeyboardButton("📝 ثبت دلیل", callback_data="admin:ban_reason_text")],[InlineKeyboardButton("🔙 برگشت", callback_data=back_callback)]])

def ban_reason_back_keyboard(back_callback="admin:user_access"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🚫 بدون دلیل", callback_data="admin:ban_reason_empty")], [InlineKeyboardButton("🔙 برگشت", callback_data=back_callback)]])

def user_confirm_keyboard(mode: str, back_callback: str = "admin:user_access"):
    """تأیید عملیات تکی بن/رفع بن."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأیید", callback_data=f"admin:confirm_{mode}")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=back_callback)],
    ])


def user_multiple_confirm_keyboard(mode: str):
    """تأیید نهایی فهرست چندتایی بن/رفع بن."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأیید همه", callback_data=f"admin:confirm_{mode}_multiple")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="admin:user_access")],
    ])


def user_search_result_keyboard(user_id: int, viewer_is_owner: bool = False, back_callback: str = "admin:users"):
    """نتیجه جستجوی کاربر با دکمه تأیید صریح."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأیید", callback_data=f"admin:search_confirm:{user_id}")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=back_callback)],
    ])


def user_detail_back_keyboard(back_callback: str = "admin:users"):
    """بازگشت یک مرحله به عقب."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 برگشت", callback_data=back_callback)]
    ])

def user_list_keyboard(page: int, total_pages: int, banned_only=False, users=None, viewer_is_owner=False):
    prefix = "admin:banned_list" if banned_only else "admin:user_list"
    rows = []
    for u in users or []:
        name = (u.first_name or u.username or "بدون نام")[:28]
        status = "🚫" if u.is_banned else "🟢"
        rows.append([InlineKeyboardButton(f"{status} {name} | {u.telegram_id}", callback_data=f"admin:user:{u.telegram_id}:user_list:{page}")])
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f"{prefix}:{page-1}"))
    nav.append(InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="admin:list_noop"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("بعدی ➡️", callback_data=f"{prefix}:{page+1}"))
    rows.append(nav)
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data="admin:user_access" if banned_only else "admin:users")])
    return InlineKeyboardMarkup(rows)


def banned_list_keyboard(page: int, total_pages: int, users=None, viewer_is_owner=False):
    rows = []
    for u in users or []:
        name = (u.first_name or u.username or "بدون نام")[:28]
        rows.append([InlineKeyboardButton(f"🚫 {name} | {u.telegram_id}", callback_data=f"admin:user:{u.telegram_id}:banned_list:{page}")])
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f"admin:banned_list:{page-1}"))
    nav.append(InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="admin:list_noop"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("بعدی ➡️", callback_data=f"admin:banned_list:{page+1}"))
    rows.append(nav)
    rows.append([InlineKeyboardButton("🗑 پاکسازی همه", callback_data="admin:clear_bans")])
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data="admin:user_access")])
    return InlineKeyboardMarkup(rows)


def balance_country_list_keyboard(user_id: int, countries, sign: str, back_callback="admin:user_tools"):
    rows = [[InlineKeyboardButton(f"🌍 {c.title}", callback_data=f"admin:balance_country_pick:{user_id}:{c.id}:{sign}")] for c in countries]
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data=back_callback)])
    return InlineKeyboardMarkup(rows)

def balance_change_keyboard(back_callback="admin:user_tools"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ افزایش موجودی", callback_data="admin:balance_add")],
        [InlineKeyboardButton("➖ کاهش موجودی", callback_data="admin:balance_remove")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=back_callback)],
    ])

def population_change_keyboard(back_callback="admin:user_tools"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ افزایش جمعیت", callback_data="admin:population_add")],
        [InlineKeyboardButton("➖ کاهش جمعیت", callback_data="admin:population_remove")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=back_callback)],
    ])


def population_mode_keyboard(sign: str, back_callback="admin:population_change"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 تک‌نفره", callback_data=f"admin:population_{sign}_single")],
        [InlineKeyboardButton("👥 چندنفره", callback_data=f"admin:population_{sign}_multiple")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=back_callback)],
    ])


def population_single_input_keyboard(sign: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 برگشت", callback_data=f"admin:population_mode:{sign}")],
    ])


def population_multiple_users_keyboard(sign: str, has_users: bool = False):
    rows = []
    if has_users:
        rows.append([InlineKeyboardButton("🏁 پایان انتخاب کاربران", callback_data=f"admin:population_users_done:{sign}")])
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data=f"admin:population_mode:{sign}")])
    return InlineKeyboardMarkup(rows)


def population_country_list_keyboard(user_id: int, countries, sign: str):
    rows = [
        [InlineKeyboardButton(f"🌍 {c.title}", callback_data=f"admin:population_country_pick:{user_id}:{c.id}:{sign}")]
        for c in countries
    ]
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data=f"admin:population_{sign}_single")])
    return InlineKeyboardMarkup(rows)


def population_amount_keyboard(back_callback="admin:population_change"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 برگشت", callback_data="admin:population_amount_back")],
    ])


def user_game_population_mode_keyboard(target_id, country_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ افزایش جمعیت", callback_data=f"admin:user_game_population_mode:{int(target_id)}:{int(country_id)}:add")],
        [InlineKeyboardButton("➖ کاهش جمعیت", callback_data=f"admin:user_game_population_mode:{int(target_id)}:{int(country_id)}:sub")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=f"admin:user_game_country:{int(target_id)}:{int(country_id)}")],
    ])


def user_game_population_input_keyboard(target_id, country_id):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data=f"admin:user_game_country:{int(target_id)}:{int(country_id)}")]])


def user_game_population_confirm_keyboard(target_id, country_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأیید", callback_data=f"admin:user_game_population_confirm:{int(target_id)}:{int(country_id)}")],
        [InlineKeyboardButton("✏️ ویرایش مقدار", callback_data=f"admin:user_game_population:{int(target_id)}:{int(country_id)}")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=f"admin:user_game_country:{int(target_id)}:{int(country_id)}")],
    ])


def population_final_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأیید نهایی", callback_data="admin:population_commit")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="admin:population_amount_back")],
    ])

def stats_role_keyboard(is_owner_user: bool):
    if is_owner_user:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🤖 آمار ربات", callback_data="admin:stats_game")],
            [InlineKeyboardButton("🔙 برگشت", callback_data="admin:back")],
        ])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 آمار ربات", callback_data="admin:stats_game")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="admin:back")],
    ])


def stats_back_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data="admin:stats")]])



def clear_bans_confirm_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأیید", callback_data="admin:confirm_clear_bans")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="admin:banned_list:1")],
    ])


def balance_mode_keyboard(sign: str, back_callback: str = "admin:users"):
    title = "افزایش" if sign == "add" else "کاهش"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 تک‌نفره", callback_data=f"admin:balance_{sign}_single")],
        [InlineKeyboardButton("👥 چندنفره", callback_data=f"admin:balance_{sign}_multiple")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=back_callback)],
    ])


def resource_keyboard(sign: str, back_action: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 پول", callback_data=f"admin:balance_resource:{sign}:money")],
        [InlineKeyboardButton("🔩 فلز", callback_data=f"admin:balance_resource:{sign}:metal")],
        [InlineKeyboardButton("⛽ سوخت", callback_data=f"admin:balance_resource:{sign}:fuel")],
        [InlineKeyboardButton("☢️ اورانیوم", callback_data=f"admin:balance_resource:{sign}:uranium")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=back_action)],
    ])

def balance_amount_keyboard(sign: str, resource: str, back_callback: str = "admin:users", infinite_state=None):
    rows = []
    active = bool(infinite_state)
    if sign == "add" and not active:
        rows.append([InlineKeyboardButton("♾️ فعال کردن بی‌نهایت", callback_data=f"admin:balance_infinite:add:{resource}")])
    elif sign == "remove" and active:
        rows.append([InlineKeyboardButton("♾️ برداشتن بی‌نهایت", callback_data=f"admin:balance_infinite:remove:{resource}")])
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data=back_callback)])
    return InlineKeyboardMarkup(rows)

def balance_continue_keyboard(sign: str, back_callback: str = "admin:users"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ ادامه", callback_data=f"admin:balance_continue:{sign}")],
        [InlineKeyboardButton("🏁 پایان", callback_data=f"admin:balance_finish:{sign}")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=back_callback)],
    ])


def balance_final_keyboard(sign: str, back_callback: str = "admin:users"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأیید نهایی", callback_data=f"admin:balance_commit:{sign}")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=back_callback)],
    ])


def balance_multiple_users_keyboard(sign: str, back_callback: str = "admin:users", has_users: bool = True):
    rows = []
    if has_users:
        rows.append([InlineKeyboardButton("🏁 پایان افزودن کاربران", callback_data=f"admin:balance_users_done:{sign}")])
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data=back_callback)])
    return InlineKeyboardMarkup(rows)


def phone_status_keyboard(back_callback="owner:general_settings", user_enabled=False, admin_enabled=False):
    all_enabled = bool(user_enabled and admin_enabled)
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"{'🟢' if user_enabled else '🔴'} کاربران عادی: {'فعال' if user_enabled else 'غیرفعال'}", callback_data="owner:phone_set:users:toggle"),
            InlineKeyboardButton(f"{'🟢' if admin_enabled else '🔴'} ادمین‌ها: {'فعال' if admin_enabled else 'غیرفعال'}", callback_data="owner:phone_set:admins:toggle"),
        ],
        [InlineKeyboardButton(f"{'🟢' if all_enabled else '🔴'} همه کاربران: {'فعال' if all_enabled else 'غیرفعال'}", callback_data="owner:phone_set:all:toggle")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=back_callback)],
    ])

def phone_toggle_keyboard(group: str, enabled: bool, back_callback="owner:phone_status"):
    # سازگاری با نسخه‌های قبلی؛ وضعیت‌ها دیگر پنل جدا ندارند.
    return phone_status_keyboard(back_callback=back_callback)

def stats_period_keyboard(role: str, period: str):
    # «همه» همیشه در آمار کاربران هم نمایش داده می‌شود؛ فقط گزینه انتخاب‌شده
    # از ردیف دکمه‌ها حذف می‌شود تا کاربر بتواند هر زمان به بازه همه برگردد.
    labels = [("all", "📊 همه"), ("today", "📅 امروز"), ("yesterday", "📆 دیروز"), ("week", "🗓 این هفته"), ("month", "🗓 این ماه"), ("year", "📅 امسال")]
    rows = [[InlineKeyboardButton(label, callback_data=f"admin:stats_period:{role}:{key}")] for key, label in labels if key != period]
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data="admin:stats_game")])
    return InlineKeyboardMarkup(rows)



def game_settings_user_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌍 انتخاب کشور پیش‌فرض", callback_data="choose_country")],
        [InlineKeyboardButton("✏️ ویرایش نام کشور", callback_data="settings:self_country_edit")],
        [InlineKeyboardButton("🔄 جابجایی", callback_data="settings:swap")],
        [InlineKeyboardButton("🗑️ حذف کشور", callback_data="settings:delete_group")],
    ])

def delete_group_keyboard(countries):
    rows = [[InlineKeyboardButton(f"🗑️ {c.title}", callback_data=f"delete_group_pick:{c.id}")] for c in countries]
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data="settings:game")])
    return InlineKeyboardMarkup(rows)

def delete_group_confirm_keyboard(country_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأیید حذف", callback_data=f"delete_group_confirm:{country_id}")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="delete_group_cancel")],
    ])

def metal_mine_costs_keyboard(level=None, build=False, show_uranium=True):
    if build:
        prefix = "owner:mine_build_edit"
        back = "owner:mine_build"
    else:
        prefix = f"owner:mine_edit:{level}"
        back = f"owner:mine_level:{level}"
    rows = [
        [InlineKeyboardButton("💰 پول", callback_data=f"{prefix}:money")],
        [InlineKeyboardButton("🔩 فلز", callback_data=f"{prefix}:metal")],
        [InlineKeyboardButton("⛽ سوخت", callback_data=f"{prefix}:fuel")],
    ]
    if show_uranium:
        rows.append([InlineKeyboardButton("☢️ اورانیوم", callback_data=f"{prefix}:uranium")])
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data=back)])
    return InlineKeyboardMarkup(rows)

def bot_shutdown_keyboard(mode="none", back_callback="owner:back"):
    # کاربران عادی و ادمین‌ها کنار هم؛ «همه» در ردیف بعدی قرار می‌گیرد.
    users_on = mode in {"none", "admins"}
    admins_on = mode in {"none", "users"}
    all_on = mode == "none"
    def _btn(label, enabled, callback):
        return InlineKeyboardButton(label, callback_data=callback, style="success" if enabled else "danger")
    return InlineKeyboardMarkup([
        [
            _btn(f"کاربران عادی: {'فعال' if users_on else 'غیرفعال'}", users_on, "owner:bot_shutdown:users"),
            _btn(f"ادمین‌ها: {'فعال' if admins_on else 'غیرفعال'}", admins_on, "owner:bot_shutdown:admins"),
        ],
        [_btn(f"همه: {'فعال' if all_on else 'غیرفعال'}", all_on, "owner:bot_shutdown:all")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=back_callback)],
    ])

# -------------------------
# 👑 اقتصاد Owner
# -------------------------
def exchange_text_confirm_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("✅ تأیید", callback_data="owner:exchange_text_confirm")],[InlineKeyboardButton("✏️ ویرایش", callback_data="owner:exchange_text_edit")],[InlineKeyboardButton("🔙 برگشت", callback_data="owner:exchange_text_cancel")]])

def general_settings_keyboard(mode="none", loan_interval_hours=24, reminder_time="09:00"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏻ روشن/خاموش کردن ربات", callback_data="owner:bot_shutdown")],
        [InlineKeyboardButton("📱 وضعیت ثبت شماره تلفن", callback_data="owner:phone_status")],
        [InlineKeyboardButton("🛡️ امنیت", callback_data="owner:security")],
        [InlineKeyboardButton("💬 چت، کانال و تبلیغات", callback_data="owner:social_links")],
        [InlineKeyboardButton("📡 پینگ ربات", callback_data="owner:ping")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="owner:back")],
    ])

def installment_settings_keyboard(loan_interval_hours=24, reminder_time="09:00", lock_days=1, overdue_multiplier=2):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"💳 فاصله پرداخت هر قسط: {float(loan_interval_hours):g} ساعت", callback_data="owner:bank_loan_interval_edit", style="primary")],
        [InlineKeyboardButton(f"🔒 مدت بسته بودن بانک پس از عدم پرداخت: {float(lock_days):g} ساعت", callback_data="owner:bank_loan_lock_days_edit", style="primary")],
        [InlineKeyboardButton(f"📈 ضریب افزایش قسط معوق: ×{float(overdue_multiplier):g}", callback_data="owner:bank_loan_overdue_multiplier_edit", style="primary")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="owner:initial_settings")],
    ])


def owner_security_keyboard():
    """پنل اصلی امنیت؛ ضداسپم و پشتیبان‌گیری کاملاً جدا هستند."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛡️ ضداسپم", callback_data="owner:security_anti")],
        [InlineKeyboardButton("💾 پشتیبان‌گیری", callback_data="owner:security_backup")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="owner:general_settings")],
    ])


def owner_anti_spam_panel_text(session):
    from services.settings import get_anti_spam_enabled, get_anti_spam_user_max, get_anti_spam_user_window, get_anti_spam_group_max, get_anti_spam_group_window
    status = "فعال" if get_anti_spam_enabled(session) else "غیرفعال"
    return (
        "🛡️ <b>ضداسپم</b>\n\n"
        f"🔘 وضعیت: <b>{status}</b>\n"
        f"👤 بازه کاربر: <b>{get_anti_spam_user_window(session)} ثانیه</b>\n"
        f"👤 حداکثر درخواست کاربر: <b>{get_anti_spam_user_max(session)}</b>\n"
        f"👥 بازه گروه: <b>{get_anti_spam_group_window(session)} ثانیه</b>\n"
        f"👥 حداکثر پیام گروه: <b>{get_anti_spam_group_max(session)}</b>"
    )

def owner_anti_spam_keyboard(session):
    from services.settings import get_anti_spam_enabled, get_anti_spam_user_max, get_anti_spam_user_window, get_anti_spam_group_max, get_anti_spam_group_window
    enabled = get_anti_spam_enabled(session)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔴 غیرفعال کردن ضداسپم" if enabled else "🟢 فعال کردن ضداسپم", callback_data="owner:anti_toggle")],
        [InlineKeyboardButton("👤 حداکثر درخواست کاربر", callback_data="owner:anti_edit:user_max"), InlineKeyboardButton("⏱ بازه کاربر", callback_data="owner:anti_edit:user_window")],
        [InlineKeyboardButton("👥 حداکثر پیام گروه", callback_data="owner:anti_edit:group_max"), InlineKeyboardButton("⏱ بازه گروه", callback_data="owner:anti_edit:group_window")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="owner:security")],
    ])


def owner_backup_panel_text(session):
    from services.settings import get_backup_started, get_backup_execution_time, get_backup_interval
    status = "فعال" if get_backup_started(session) else "غیرفعال"
    return (
        "💾 <b>پشتیبان‌گیری</b>\n\n"
        f"🔘 وضعیت: <b>{status}</b>\n"
        f"🕐 زمان اجرا: <b>{get_backup_execution_time(session)}</b>\n"
        f"⏱ فاصله بکاپ: <b>{get_backup_interval(session)} دقیقه</b>\n\n"
        "📌 بعد از شروع، اولین بکاپ در زمان اجرا ارسال می‌شود و سپس با فاصله تعیین‌شده ادامه پیدا می‌کند."
    )

def owner_backup_keyboard(session):
    from services.settings import get_backup_started
    started = get_backup_started(session)
    rows = [[InlineKeyboardButton("🔴 توقف پشتیبان‌گیری" if started else "🟢 شروع پشتیبان‌گیری", callback_data="owner:backup_start_toggle")]]
    rows.append([InlineKeyboardButton("🕐 زمان اجرا", callback_data="owner:backup_execution_time_edit"), InlineKeyboardButton("⏱ فاصله بکاپ", callback_data="owner:backup_interval_edit")])
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data="owner:security")])
    return InlineKeyboardMarkup(rows)


def economy_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧩 مدیریت زیرساخت‌های بازی", callback_data="owner:game_management", style="primary")],
        [InlineKeyboardButton("⚙️ تنظیمات اولیه", callback_data="owner:initial_settings")],
        [InlineKeyboardButton("💱 تبدیل", callback_data="owner:exchange_settings")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="owner:back")],
    ])

def game_management_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏗️ مدیریت ساختمان‌ها", callback_data="owner:buildings")],
        [InlineKeyboardButton("🚀 مدیریت موشک‌ها", callback_data="owner:missiles")],
        [InlineKeyboardButton("🛡️ مدیریت سپرها", callback_data="owner:shields")],
        [InlineKeyboardButton("🏗️ مدیریت تیم‌های ساخت‌وساز", callback_data="owner:construction_teams")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="owner:economy")],
    ])

def initial_settings_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 منابع اولیه", callback_data="owner:initial_resources"), InlineKeyboardButton("👥 جمعیت اولیه", callback_data="owner:initial_population")],
        [InlineKeyboardButton("👑 تنظیمات تجربه رهبری", callback_data="owner:leadership_settings")],
        [InlineKeyboardButton("⏱️ محدودیت جابه‌جایی", callback_data="owner:swap_cooldown"), InlineKeyboardButton("💳 هزینه تغییر نام", callback_data="owner:country_rename_cost")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="owner:economy")],
    ])

def admin_messages_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📩 پیام خصوصی", callback_data="admin:message_private", style="primary"), InlineKeyboardButton("📢 پیام عمومی", callback_data="admin:message_public", style="primary")],
        [InlineKeyboardButton("📋 لیست پیام‌ها", callback_data="admin:message_lists")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="admin:back")],
    ])

def message_lists_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📩 لیست پیام‌های خصوصی", callback_data="admin:message_list:private:1")],
        [InlineKeyboardButton("📢 لیست پیام‌های عمومی", callback_data="admin:message_list:public:1")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="admin:messages")],
    ])

def message_items_keyboard(kind, page, total_pages, items):
    rows=[]
    for idx, item in enumerate(items, 1):
        rows.append([InlineKeyboardButton(f"📨 پیام {idx}", callback_data=f"admin:message_detail:{kind}:{item.get('id')}:page:{page}")])
    nav=[]
    if page>1: nav.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f"admin:message_list:{kind}:{page-1}"))
    nav.append(InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="admin:list_noop"))
    if page<total_pages: nav.append(InlineKeyboardButton("بعدی ➡️", callback_data=f"admin:message_list:{kind}:{page+1}"))
    rows.append(nav); rows.append([InlineKeyboardButton("🔙 برگشت", callback_data="admin:message_lists")])
    return InlineKeyboardMarkup(rows)

def message_detail_keyboard(kind, page, message_id=None):
    rows=[]
    if message_id:
        rows.append([InlineKeyboardButton("📨 فرستادن پیام ارسال شده", callback_data=f"admin:message_sent:{kind}:{message_id}")])
        rows.append([InlineKeyboardButton("📤 فرستادن گیرنده‌ها", callback_data=f"admin:message_recipients_send:{kind}:{message_id}")])
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data=f"admin:message_list:{kind}:{page}")])
    return InlineKeyboardMarkup(rows)

def message_private_continue_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("➕ افزودن کاربر دیگر", callback_data="admin:message_private_add")],[InlineKeyboardButton("✅ پایان و دریافت متن", callback_data="admin:message_private_finish")],[InlineKeyboardButton("🔙 برگشت", callback_data="admin:messages")]])

def message_public_targets_keyboard(owner=True):
    rows=[]
    if owner:
        rows += [[InlineKeyboardButton("👥 کاربران", callback_data="admin:message_public_target:users")],[InlineKeyboardButton("🛡️ مدیرها", callback_data="admin:message_public_target:admins")],[InlineKeyboardButton("🌐 همه", callback_data="admin:message_public_target:all")]]
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data="admin:messages")])
    return InlineKeyboardMarkup(rows)

def message_confirm_keyboard(kind="private"):
    back = "admin:messages"
    return InlineKeyboardMarkup([[InlineKeyboardButton("✅ تأیید ارسال", callback_data="admin:message_send_confirm")],[InlineKeyboardButton("✏️ ویرایش پیام", callback_data="admin:message_edit")],[InlineKeyboardButton("🔙 برگشت", callback_data=back)]])



def bank_economy_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔝 حداکثر سطح", callback_data="owner:bank_max_level", style="primary")],
        [InlineKeyboardButton("🏗️ ساخت", callback_data="owner:bank_build", style="success")],
        [InlineKeyboardButton("💳 تنظیمات قسط", callback_data="owner:installment_settings", style="primary")],
        [InlineKeyboardButton("📊 تنظیم سطوح", callback_data="owner:bank_levels", style="primary")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="owner:buildings")],
    ])


def bank_build_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏛️ سطح مرکز فرماندهی مورد نیاز", callback_data="owner:bank_build_edit:required_hq_level", style="primary")],
        [InlineKeyboardButton("⏱️ زمان تکمیل", callback_data="owner:bank_build_edit:build_time_hours", style="primary")],
        [InlineKeyboardButton("💰 هزینه‌ها", callback_data="owner:bank_build_costs", style="primary")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="owner:economy_bank")],
    ])

def bank_build_costs_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 پول", callback_data="owner:bank_build_edit:build_cost:money", style="primary")],
        [InlineKeyboardButton("🔩 فلز", callback_data="owner:bank_build_edit:build_cost:metal", style="primary")],
        [InlineKeyboardButton("⛽ سوخت", callback_data="owner:bank_build_edit:build_cost:fuel", style="primary")],
        [InlineKeyboardButton("☢️ اورانیوم", callback_data="owner:bank_build_edit:build_cost:uranium", style="primary")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="owner:bank_build")],
    ])

def bank_level_edit_keyboard(level):
    level = int(level)
    if level <= 1:
        fields = [
            ("🏛️ سطح مرکز فرماندهی مورد نیاز", "required_hq_level"),
            ("⏱️ زمان تکمیل", "build_time_hours"),
            ("💰 هزینه‌ها", "owner:bank_level_costs:1"),
            ("⚙️ تنظیمات سطح بانک", "owner:bank_level_settings:1:build"),
        ]
    else:
        fields = [
            ("🏛️ سطح مرکز فرماندهی مورد نیاز", "required_hq_level"),
            ("⏱️ زمان ارتقا", "upgrade_time_hours"),
            ("💰 هزینه‌ها", f"owner:bank_level_costs:{level}"),
            ("⚙️ تنظیمات سطح بانک", f"owner:bank_level_settings:{level}:level"),
        ]
    rows = []
    for label, field in fields:
        callback = field if field.startswith("owner:") else f"owner:bank_edit:{level}:{field}"
        rows.append([InlineKeyboardButton(label, callback_data=callback, style="primary")])
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data="owner:bank_levels")])
    return InlineKeyboardMarkup(rows)

def bank_level_settings_keyboard(level, build=False):
    level = int(level)
    back_cb = f"owner:bank_level_settings:{level}:{1 if build or level <= 1 else 0}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏦 تنظیمات سپرده", callback_data=f"owner:bank_deposit_settings:{level}:{1 if build or level <= 1 else 0}", style="primary")],
        [InlineKeyboardButton("💳 تنظیمات وام", callback_data=f"owner:bank_loan_settings:{level}:{1 if build or level <= 1 else 0}", style="primary")],
        [InlineKeyboardButton("📈 تنظیمات سرمایه‌گذاری", callback_data=f"owner:bank_investments:{level}:{1 if build or level <= 1 else 0}", style="primary")],
        [InlineKeyboardButton("🧾 تنظیمات مالیات", callback_data=f"owner:bank_tax_settings:{level}:{1 if build or level <= 1 else 0}", style="primary")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=back_cb)],
    ])


def bank_deposit_settings_keyboard(level, build=False):
    level = int(level)
    if build or level <= 1:
        cap_cb = "owner:bank_build_edit:deposit_capacity"
        profit_cb = "owner:bank_build_edit:deposit_hourly_profit_percent"
        back_cb = f"owner:bank_level_settings:{level}:{1 if build or level <= 1 else 0}"
    else:
        cap_cb = f"owner:bank_edit:{level}:deposit_capacity"
        profit_cb = f"owner:bank_edit:{level}:deposit_hourly_profit_percent"
        back_cb = f"owner:bank_level_settings:{level}:{1 if build or level <= 1 else 0}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 حداکثر سپرده", callback_data=cap_cb, style="primary")],
        [InlineKeyboardButton("📈 سود سپرده در ساعت (%)", callback_data=profit_cb, style="primary")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=back_cb)],
    ])


def bank_tax_settings_keyboard(level, build=False):
    level=int(level)
    back_cb = f"owner:bank_level_settings:{level}:{1 if build or level <= 1 else 0}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬇️ حداقل مالیات به ازای هر ۱۰۰۰ شهروند", callback_data=f"owner:bank_edit:{level}:tax_min", style="primary")],
        [InlineKeyboardButton("⬆️ حداکثر مالیات به ازای هر ۱۰۰۰ شهروند", callback_data=f"owner:bank_edit:{level}:tax_max", style="primary")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=back_cb)],
    ])


def bank_level_costs_keyboard(level):
    level = int(level)
    group = "build_cost" if level <= 1 else "upgrade_cost"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 پول", callback_data=f"owner:bank_edit:{level}:{group}:money", style="primary")],
        [InlineKeyboardButton("🔩 فلز", callback_data=f"owner:bank_edit:{level}:{group}:metal", style="primary")],
        [InlineKeyboardButton("⛽ سوخت", callback_data=f"owner:bank_edit:{level}:{group}:fuel", style="primary")],
        [InlineKeyboardButton("☢️ اورانیوم", callback_data=f"owner:bank_edit:{level}:{group}:uranium", style="primary")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=f"owner:bank_level:{level}")],
    ])

def bank_loans_settings_keyboard(level=1, build=False, loan=None):
    level = int(level)
    loan = loan or {}
    prefix = "owner:bank_build_loan_edit:" if build or level <= 1 else f"owner:bank_loan_edit:{level}:"
    back_cb = f"owner:bank_level_settings:{level}:{1 if build or level <= 1 else 0}"
    min_amount=float(loan.get("min_amount",0) or 0); max_amount=float(loan.get("max_amount",0) or 0)
    min_interest=float(loan.get("min_interest_percent",0) or 0); max_interest=float(loan.get("max_interest_percent",0) or 0)
    min_inst=int(loan.get("min_installments",1) or 1); max_inst=int(loan.get("max_installments",1) or 1)
    active=int(loan.get("max_active_loans",1) or 1)
    unlock=float(loan.get("bank_unlock_cost",0) or 0)
    fields = [
        (f"💰 محدوده مبلغ: {min_amount:,.0f} تا {max_amount:,.0f}", "amount_range"),
        (f"📈 سود: {min_interest:g}% تا {max_interest:g}%", "interest_range"),
        (f"🧾 اقساط: {min_inst} تا {max_inst}", "installments_range"),
        (f"👥 حداکثر وام فعال همزمان: {active}", "max_active_loans"),
    ]
    rows=[]
    for label, field in fields:
        rows.append([InlineKeyboardButton(label, callback_data=prefix + field, style="primary")])
    rows.append([InlineKeyboardButton(f"🔓 هزینه بازگشایی بانک: {unlock:,.0f}", callback_data=prefix + "bank_unlock_cost", style="primary")])
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data=back_cb)])
    return InlineKeyboardMarkup(rows)

def bank_loan_range_keyboard(level, build, kind):
    level=int(level); build=bool(build)
    prefix = "owner:bank_build_loan_edit:" if build or level <= 1 else f"owner:bank_loan_edit:{level}:"
    if kind == "amount":
        fields=[("حداقل مبلغ", "min_amount"),("حداکثر مبلغ", "max_amount")]
    elif kind == "interest":
        fields=[("حداقل سود (%)", "min_interest_percent"),("حداکثر سود (%)", "max_interest_percent")]
    else:
        fields=[("حداقل تعداد اقساط", "min_installments"),("حداکثر تعداد اقساط", "max_installments")]
    back_cb = "owner:bank_build_loan_settings" if build else f"owner:bank_loan_settings:{level}"
    rows=[[InlineKeyboardButton(label,callback_data=prefix+field,style="primary")] for label,field in fields]
    rows.append([InlineKeyboardButton("🔙 برگشت",callback_data=back_cb)])
    return InlineKeyboardMarkup(rows)

def bank_investments_settings_keyboard(plans, level=1, build=False):
    level = int(level)
    mode = 1 if build or level <= 1 else 0
    prefix = f"owner:bank_investments:{level}:{mode}"
    rows = [
        [InlineKeyboardButton("➕ افزودن سرمایه‌گذاری", callback_data=f"owner:bank_investment_add:{level}:{mode}", style="success")],
        [InlineKeyboardButton("📋 لیست سرمایه‌گذاری‌ها", callback_data=f"owner:bank_investment_list:{level}:{mode}", style="primary")],
        [InlineKeyboardButton("🗑️ حذف سرمایه‌گذاری", callback_data=f"owner:bank_investment_delete_list:{level}:{mode}", style="danger")],
    ]
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data=f"owner:bank_level_settings:{level}:{mode}")])
    return InlineKeyboardMarkup(rows)


def bank_investment_return_type_keyboard(level, build=False):
    level=int(level); mode=1 if build or level<=1 else 0
    types=[("money","💰 پول"),("metal","🔩 فلز"),("fuel","⛽ سوخت"),("uranium","☢️ اورانیوم"),("leadership_experience","👑 تجربه رهبری"),("population","👥 جمعیت")]
    rows=[[InlineKeyboardButton(label, callback_data=f"owner:bank_investment_add_return:{level}:{mode}:{key}", style="primary")] for key,label in types]
    rows.append([InlineKeyboardButton("🔙 برگشت",callback_data=f"owner:bank_investments:{level}:{mode}")])
    return InlineKeyboardMarkup(rows)

def bank_investment_list_keyboard(plans, level=1, build=False, delete_mode=False):
    level = int(level)
    mode = 1 if build or level <= 1 else 0
    rows = []
    for i, plan in enumerate(plans):
        name = str(plan.get("name") or "سرمایه‌گذاری")[:45]
        icon = "🗑️" if delete_mode else "📈"
        action = "delete" if delete_mode else "view"
        rows.append([InlineKeyboardButton(f"{icon} {name}", callback_data=(f"owner:bank_investment_delete:{level}:{i}:{mode}" if delete_mode else f"owner:bank_investment:{level}:{i}:{mode}"))])
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data=f"owner:bank_investments:{level}:{mode}")])
    return InlineKeyboardMarkup(rows)

def bank_investment_delete_confirm_keyboard(level, index, build=False):
    level = int(level)
    mode = 1 if build or level <= 1 else 0
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأیید حذف", callback_data=f"owner:bank_investment_delete_confirm:{level}:{index}:{mode}", style="danger")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=f"owner:bank_investment_delete_list:{level}:{mode}")],
    ])

def bank_investment_financial_keyboard(index, level=1, build=False):
    level=int(level); mode=1 if build or level<=1 else 0
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 حداکثر مبلغ",callback_data=f"owner:bank_investment_edit:{level}:{index}:{mode}:max_amount",style="primary"), InlineKeyboardButton("💰 حداقل مبلغ",callback_data=f"owner:bank_investment_edit:{level}:{index}:{mode}:min_amount",style="primary")],
        [InlineKeyboardButton("📈 حداکثر سود احتمالی",callback_data=f"owner:bank_investment_edit:{level}:{index}:{mode}:profit_max",style="primary"), InlineKeyboardButton("📈 حداقل سود احتمالی",callback_data=f"owner:bank_investment_edit:{level}:{index}:{mode}:profit_min",style="primary")],
        [InlineKeyboardButton("📉 حداکثر زیان احتمالی",callback_data=f"owner:bank_investment_edit:{level}:{index}:{mode}:loss_max",style="primary"), InlineKeyboardButton("📉 حداقل زیان احتمالی",callback_data=f"owner:bank_investment_edit:{level}:{index}:{mode}:loss_min",style="primary")],
        [InlineKeyboardButton("⏱️ مدت (ساعت)",callback_data=f"owner:bank_investment_edit:{level}:{index}:{mode}:duration_hours",style="primary")],
        [InlineKeyboardButton("🔙 برگشت",callback_data=f"owner:bank_investment:{level}:{index}:{mode}")],
    ])

def bank_investment_edit_keyboard(index, level=1, build=False):
    level=int(level); mode=1 if build or level<=1 else 0
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ نام", callback_data=f"owner:bank_investment_edit:{level}:{index}:{mode}:name", style="primary")],
        [InlineKeyboardButton("⚙️ مبلغ، سود، زیان و مدت", callback_data=f"owner:bank_investment_financial:{level}:{index}:{mode}", style="primary")],
        [InlineKeyboardButton("🧩 نوع طرح", callback_data=f"owner:bank_investment_edit:{level}:{index}:{mode}:plan_type", style="primary")],
        [InlineKeyboardButton("🎚️ ریسک", callback_data=f"owner:bank_investment_edit:{level}:{index}:{mode}:risk", style="primary")],
        [InlineKeyboardButton("👤 حداکثر تعداد برای هر کاربر", callback_data=f"owner:bank_investment_edit:{level}:{index}:{mode}:max_per_user", style="primary")],
        [InlineKeyboardButton("🔁 سرمایه‌گذاری همزمان", callback_data=f"owner:bank_investment_multi:{level}:{index}:{mode}", style="primary")],
        [InlineKeyboardButton("🔄 فعال/غیرفعال", callback_data=f"owner:bank_investment_toggle:{level}:{index}:{mode}", style="primary")],
        [InlineKeyboardButton("🗑️ حذف طرح", callback_data=f"owner:bank_investment_delete:{level}:{index}:{mode}", style="danger")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=f"owner:bank_investments:{level}:{mode}")],
    ])

def construction_teams_owner_keyboard(cfg):
    max_teams=int(cfg.get("max_teams",10) or 10)
    rows=[[InlineKeyboardButton(f"⚙️ حداکثر تیم‌ها: {max_teams}", callback_data="owner:construction_team_max", style="primary")],
          [InlineKeyboardButton("💰 مدیریت قیمت‌ها", callback_data="owner:construction_team_prices", style="primary")],
          [InlineKeyboardButton("🔙 برگشت", callback_data="owner:game_management")]]
    return InlineKeyboardMarkup(rows)

def construction_team_prices_keyboard(cfg):
    prices=cfg.get("prices",{}) or {}
    max_teams=max(1,min(10,int(cfg.get("max_teams",10) or 10)))
    rows=[]
    # فقط تیم‌هایی که در Maximum فعلی قرار دارند برای تنظیم قیمت نمایش داده شوند.
    for i in range(2,max_teams+1):
        button=InlineKeyboardButton(f"🏗️ تیم {i}: {float(prices.get(str(i),0) or 0):,.0f} 💰", callback_data=f"owner:construction_team_price:{i}", style="primary")
        if not rows or len(rows[-1]) >= 2:
            rows.append([button])
        else:
            rows[-1].append(button)
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data="owner:construction_teams")])
    return InlineKeyboardMarkup(rows)


def building_management_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("☢️ اورانیوم تکمیل فوری", callback_data="owner:buildings_instant_finish_rate", style="primary")],
        [InlineKeyboardButton("🏛️ مرکز فرماندهی", callback_data="owner:economy_hq"), InlineKeyboardButton("⛏️ معدن فلز", callback_data="owner:economy_metal_mine"), InlineKeyboardButton("🏭 زرادخانه", callback_data="owner:economy_arsenal")],
        [InlineKeyboardButton("🏦 بانک مرکزی", callback_data="owner:economy_bank")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="owner:game_management")],
    ])

def metal_mine_economy_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔝 حداکثر سطح", callback_data="owner:mine_max_level")],
        [InlineKeyboardButton("🏗 ساخت", callback_data="owner:mine_build")],
        [InlineKeyboardButton("📊 تنظیم سطوح", callback_data="owner:mine_levels", style="primary")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="owner:buildings")],
    ])


def metal_mine_level_keyboard(levels):
    rows = []
    row = []
    for level in levels:
        row.append(InlineKeyboardButton(f"سطح {level}", callback_data=f"owner:mine_level:{level}", style="primary"))
        if len(row) == 5:
            rows.append(row); row = []
    if row: rows.append(row)
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data="owner:economy_metal_mine")])
    return InlineKeyboardMarkup(rows)


def metal_mine_level_edit_keyboard(level, active=True):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏛️ سطح مرکز فرماندهی مورد نیاز", callback_data=f"owner:mine_edit:{level}:required_hq_level")],
        [InlineKeyboardButton("🪖 قدرت نظامی", callback_data=f"owner:mine_edit:{level}:military_power")],
        [InlineKeyboardButton("🛡️ استحکام", callback_data=f"owner:mine_edit:{level}:strength")],
        [InlineKeyboardButton("⚙️ تولید در ساعت", callback_data=f"owner:mine_edit:{level}:production_per_hour")],
        [InlineKeyboardButton("📦 ظرفیت مخزن", callback_data=f"owner:mine_edit:{level}:storage_capacity")],
        [InlineKeyboardButton("⏱️ زمان تکمیل", callback_data=f"owner:mine_edit:{level}:completion_time")],
        [InlineKeyboardButton("💰 هزینه‌ها", callback_data=f"owner:mine_level_costs:{level}" )],
        [InlineKeyboardButton("🔙 برگشت", callback_data="owner:mine_levels")],
    ])


def metal_mine_build_cost_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏛️ سطح مرکز فرماندهی مورد نیاز", callback_data="owner:mine_build_edit:required_hq_level")],
        [InlineKeyboardButton("🪖 قدرت نظامی", callback_data="owner:mine_build_edit:military_power")],
        [InlineKeyboardButton("🛡️ استحکام", callback_data="owner:mine_build_edit:strength")],
        [InlineKeyboardButton("⚙️ تولید در ساعت", callback_data="owner:mine_build_edit:production_per_hour")],
        [InlineKeyboardButton("📦 ظرفیت مخزن", callback_data="owner:mine_build_edit:storage_capacity")],
        [InlineKeyboardButton("⏱️ زمان تکمیل", callback_data="owner:mine_build_edit:completion_time")],
        [InlineKeyboardButton("💰 هزینه‌ها", callback_data="owner:mine_build_costs")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="owner:economy_metal_mine")],
    ])



def metal_mine_build_cost_input_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 برگشت", callback_data="owner:mine_build")],
    ])



def balance_single_input_keyboard(back_callback: str = "admin:users"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 برگشت", callback_data=back_callback)]
    ])


def arsenal_economy_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔝 حداکثر سطح", callback_data="owner:arsenal_max_level")],
        [InlineKeyboardButton("🏗 ساخت", callback_data="owner:arsenal_build")],
        [InlineKeyboardButton("📊 تنظیم سطوح", callback_data="owner:arsenal_levels", style="primary")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="owner:buildings")],
    ])

def arsenal_level_keyboard(levels):
    rows=[]; row=[]
    for level in levels:
        row.append(InlineKeyboardButton(f"سطح {level}", callback_data=f"owner:arsenal_level:{level}", style="primary"))
        if len(row)==5:
            rows.append(row); row=[]
    if row: rows.append(row)
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data="owner:economy_arsenal")])
    return InlineKeyboardMarkup(rows)

def arsenal_level_edit_keyboard(level):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏛️ سطح مرکز فرماندهی مورد نیاز", callback_data=f"owner:arsenal_edit:{level}:required_hq_level")],
        [InlineKeyboardButton("🪖 قدرت نظامی", callback_data=f"owner:arsenal_edit:{level}:military_power")],
        [InlineKeyboardButton("🛡️ استحکام", callback_data=f"owner:arsenal_edit:{level}:strength")],
        [InlineKeyboardButton("📦 ظرفیت مخزن", callback_data=f"owner:arsenal_edit:{level}:storage_capacity")],
        [InlineKeyboardButton("⏱️ زمان تکمیل", callback_data=f"owner:arsenal_edit:{level}:completion_time")],
        [InlineKeyboardButton("💰 هزینه‌ها", callback_data=f"owner:arsenal_level_costs:{level}" )],
        [InlineKeyboardButton("🔙 برگشت", callback_data="owner:arsenal_levels")],
    ])

def arsenal_build_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏛️ سطح مرکز فرماندهی مورد نیاز", callback_data="owner:arsenal_build_edit:required_hq_level")],
        [InlineKeyboardButton("🪖 قدرت نظامی", callback_data="owner:arsenal_build_edit:military_power")],
        [InlineKeyboardButton("🛡️ استحکام", callback_data="owner:arsenal_build_edit:strength")],
        [InlineKeyboardButton("📦 ظرفیت مخزن", callback_data="owner:arsenal_build_edit:storage_capacity")],
        [InlineKeyboardButton("⏱️ زمان تکمیل", callback_data="owner:arsenal_build_edit:completion_time")],
        [InlineKeyboardButton("💰 هزینه‌ها", callback_data="owner:arsenal_build_costs")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="owner:economy_arsenal")],
    ])

def arsenal_costs_keyboard(level=None, build=False):
    prefix="owner:arsenal_build_edit" if build else f"owner:arsenal_edit:{level}"
    back="owner:arsenal_build" if build else f"owner:arsenal_level:{level}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 پول", callback_data=f"{prefix}:money")],
        [InlineKeyboardButton("🔩 فلز", callback_data=f"{prefix}:metal")],
        [InlineKeyboardButton("⛽ سوخت", callback_data=f"{prefix}:fuel")],
        [InlineKeyboardButton("☢️ اورانیوم", callback_data=f"{prefix}:uranium")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=back)],
    ])


def missile_management_keyboard(missiles):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ افزودن موشک", callback_data="owner:missile_add"), InlineKeyboardButton("📋 لیست موشک‌ها", callback_data="owner:missile_list")],
        [InlineKeyboardButton("☢️ اورانیوم تکمیل فوری", callback_data="owner:missiles_instant_finish_rate", style="primary")],
        [InlineKeyboardButton("💰 درصد غارت منابع کلی", callback_data="owner:global_loot_percent")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="owner:game_management")],
    ])

def missile_category_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 موشک‌های کروز", callback_data="owner:missile_list_type:کروز")],
        [InlineKeyboardButton("🚀 موشک‌های بالستیک", callback_data="owner:missile_list_type:بالستیک")],
        [InlineKeyboardButton("⚡ موشک‌های هایپرسونیک", callback_data="owner:missile_list_type:هایپرسونیک")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="owner:missiles")],
    ])

def missile_items_keyboard(items, back="owner:missile_list"):
    rows=[[InlineKeyboardButton(f"{m.get('name','موشک')}", callback_data=f"owner:missile:{m.get('id')}")] for m in items]
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data=back)])
    return InlineKeyboardMarkup(rows)

def missile_sticker_keyboard(mid, has_sticker=False):
    rows = []
    if has_sticker:
        rows.append([InlineKeyboardButton("✏️ ویرایش استیکر", callback_data=f"owner:missile_sticker:{mid}:edit")])
        rows.append([InlineKeyboardButton("🗑️ حذف استیکر", callback_data=f"owner:missile_sticker_delete:{mid}")])
    else:
        rows.append([InlineKeyboardButton("➕ افزودن استیکر", callback_data=f"owner:missile_sticker:{mid}:edit")])
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data=f"owner:missile:{mid}")])
    return InlineKeyboardMarkup(rows)


def missile_edit_keyboard(mid, back="owner:missile_list", active=False):
    # چیدمان ثابت تنظیمات هر موشک:
    # ردیف ۱: نوع موشک + نام‌های عملیاتی
    # ردیف ۲: استیکر شلیک + ظرفیت اشغال کلی
    # ردیف ۳: حداکثر سطح + تنظیمات پایه
    # ردیف ۴: تنظیم سطح
    # ردیف ۵: اورانیوم تکمیل فوری
    # ردیف ۶: فعال/غیرفعال + حذف موشک
    # ردیف ۷: برگشت
    toggle_text = "🔴 غیرفعال" if active else "🟢 فعال"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🏷️ نام‌های عملیاتی", callback_data=f"owner:missile_operational:{mid}"),
            InlineKeyboardButton("🏷 نوع موشک", callback_data=f"owner:missile_edit:{mid}:type"),
        ],
        [
            InlineKeyboardButton("🎭 استیکر شلیک", callback_data=f"owner:missile_sticker:{mid}"),
            InlineKeyboardButton("📦 ظرفیت اشغال کلی", callback_data=f"owner:missile_edit:{mid}:base_capacity"),
        ],
        [
            InlineKeyboardButton("🔝 حداکثر سطح", callback_data=f"owner:missile_edit:{mid}:max_level"),
            InlineKeyboardButton("⚙️ تنظیمات پایه", callback_data=f"owner:missile_base:{mid}"),
        ],
        [InlineKeyboardButton("📊 تنظیم سطح", callback_data=f"owner:missile_levels:{mid}")],
        [
            InlineKeyboardButton(toggle_text, callback_data=f"owner:missile_toggle:{mid}"),
            InlineKeyboardButton("🗑️ حذف موشک", callback_data=f"owner:missile_delete:{mid}"),
        ],
        [InlineKeyboardButton("🔙 برگشت", callback_data=back)],
    ])

def missile_base_settings_keyboard(mid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏛️ سطح مرکز فرماندهی لازم", callback_data=f"owner:missile_edit:{mid}:hq_required")],
        [InlineKeyboardButton("🏭 سطح زرادخانه لازم", callback_data=f"owner:missile_edit:{mid}:arsenal_required")],
        [InlineKeyboardButton("💰 هزینه پایه", callback_data=f"owner:missile_edit:{mid}:base_cost")],
        [InlineKeyboardButton("💥 قدرت پایه", callback_data=f"owner:missile_edit:{mid}:base_power")],
        [InlineKeyboardButton("⏱️ زمان برخورد با هدف پایه (ثانیه)", callback_data=f"owner:missile_edit:{mid}:base_target_time")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=f"owner:missile:{mid}")],
    ])

def missile_delete_confirm_keyboard(mid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأیید حذف", callback_data=f"owner:missile_delete_confirm:{mid}")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=f"owner:missile:{mid}")],
    ])

def missile_level_keyboard(mid, max_level=100):
    rows=[]
    # سطح ۱ بعد از باز شدن موشک به‌صورت خودکار فعال است و از این بخش تنظیم نمی‌شود.
    max_level=min(int(max_level),100)
    levels=list(range(2, max_level+1)) if max_level >= 2 else []
    for i in range(0, len(levels), 5):
        chunk=levels[i:i+5]
        rows.append([InlineKeyboardButton(f"سطح {x}", callback_data=f"owner:missile_level:{mid}:{x}") for x in chunk])
    if not levels:
        rows.append([InlineKeyboardButton("ℹ️ سطح قابل تنظیمی وجود ندارد", callback_data=f"owner:missile:{mid}")])
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data=f"owner:missile:{mid}")])
    return InlineKeyboardMarkup(rows)

def missile_operational_keyboard(mid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ افزودن نام عملیاتی", callback_data=f"owner:missile_operational_add:{mid}")],
        [InlineKeyboardButton("🗑️ حذف نام عملیاتی", callback_data=f"owner:missile_operational_delete:{mid}")],
        [InlineKeyboardButton("📋 لیست نام‌های عملیاتی", callback_data=f"owner:missile_operational_list:{mid}")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=f"owner:missile:{mid}")],
    ])

def missile_operational_delete_keyboard(mid, names):
    rows=[[InlineKeyboardButton(f"🗑️ {name}", callback_data=f"owner:missile_operational_del:{mid}:{i}")] for i,name in enumerate(names)]
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data=f"owner:missile_operational:{mid}")])
    return InlineKeyboardMarkup(rows)

def missile_operational_list_keyboard(mid, names):
    rows=[]
    for i,name in enumerate(names,1):
        rows.append([InlineKeyboardButton(f"{i}. {name}", callback_data=f"owner:missile_operational_item:{mid}:{i-1}")])
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data=f"owner:missile_operational:{mid}")])
    return InlineKeyboardMarkup(rows)

def missile_level_edit_keyboard(mid, level):
    # تنظیمات عمومی سطح؛ تنظیمات ارتقا در بخش جداگانه قرار دارد.
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏛️ سطح مرکز فرماندهی لازم", callback_data=f"owner:missile_level_edit:{mid}:{level}:hq_required")],
        [InlineKeyboardButton("🏭 سطح زرادخانه لازم", callback_data=f"owner:missile_level_edit:{mid}:{level}:arsenal_required")],
        [InlineKeyboardButton("💰 هزینه", callback_data=f"owner:missile_level_edit:{mid}:{level}:cost")],
        [InlineKeyboardButton("💥 قدرت", callback_data=f"owner:missile_level_edit:{mid}:{level}:power")],
        [InlineKeyboardButton("⏱️ زمان برخورد با هدف", callback_data=f"owner:missile_level_edit:{mid}:{level}:target_time")],
        [InlineKeyboardButton("⬆️ تنظیمات ارتقا", callback_data=f"owner:missile_upgrade_settings:{mid}:{level}")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=f"owner:missile_levels:{mid}")],
    ])

def missile_upgrade_settings_keyboard(mid, level):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏳ زمان ارتقا", callback_data=f"owner:missile_level_edit:{mid}:{level}:upgrade_time")],
        [InlineKeyboardButton("💵 هزینه ارتقا با پول", callback_data=f"owner:missile_level_edit:{mid}:{level}:upgrade_money")],
        [InlineKeyboardButton("🔩 هزینه ارتقا با فلز", callback_data=f"owner:missile_level_edit:{mid}:{level}:upgrade_metal")],
        [InlineKeyboardButton("⛽ هزینه ارتقا با سوخت", callback_data=f"owner:missile_level_edit:{mid}:{level}:upgrade_fuel")],
        [InlineKeyboardButton("☢️ هزینه ارتقا با اورانیوم", callback_data=f"owner:missile_level_edit:{mid}:{level}:upgrade_uranium")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=f"owner:missile_level:{mid}:{level}")],
    ])

def missile_value_confirm_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأیید", callback_data="owner:missile_value_confirm")],
        [InlineKeyboardButton("✏️ ویرایش", callback_data="owner:missile_value_edit")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="owner:missile_value_cancel")],
    ])

def missile_name_confirm_keyboard(back="owner:missile_add"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأیید", callback_data="owner:missile_name_confirm")],
        [InlineKeyboardButton("✏️ ویرایش نام", callback_data="owner:missile_name_edit")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=back)],
    ])


def hq_economy_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔝 حداکثر سطح", callback_data="owner:hq_max_level")],
        [InlineKeyboardButton("🏗️ ساخت", callback_data="owner:hq_build")],
        [InlineKeyboardButton("📊 تنظیم سطوح", callback_data="owner:hq_levels", style="primary")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="owner:buildings")],
    ])

def hq_level_keyboard(levels):
    rows=[]; row=[]
    for level in levels:
        row.append(InlineKeyboardButton(f"سطح {level}", callback_data=f"owner:hq_level:{level}", style="primary"))
        if len(row)==5: rows.append(row); row=[]
    if row: rows.append(row)
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data="owner:economy_hq")])
    return InlineKeyboardMarkup(rows)

def hq_level_edit_keyboard(level):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🪖 قدرت نظامی", callback_data=f"owner:hq_edit:{level}:military_power")],
        [InlineKeyboardButton("🛡️ استحکام", callback_data=f"owner:hq_edit:{level}:strength")],
        [InlineKeyboardButton("⏱️ زمان تکمیل", callback_data=f"owner:hq_edit:{level}:completion_time")],
        [InlineKeyboardButton("💰 هزینه‌ها", callback_data=f"owner:hq_level_costs:{level}")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="owner:hq_levels")],
    ])

def hq_costs_keyboard(level):
    prefix=f"owner:hq_edit:{level}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 پول", callback_data=f"{prefix}:money")],
        [InlineKeyboardButton("🔩 فلز", callback_data=f"{prefix}:metal")],
        [InlineKeyboardButton("⛽ سوخت", callback_data=f"{prefix}:fuel")],
        [InlineKeyboardButton("☢️ اورانیوم", callback_data=f"{prefix}:uranium")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=f"owner:hq_level:{level}")],
    ])

# Keyboard used while creating/editing a missile draft.
def missile_draft_keyboard(back="owner:missile_add"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔝 حداکثر سطح", callback_data="owner:missile_draft_edit:max_level")],
        [InlineKeyboardButton("🏛️ سطح مرکز فرماندهی لازم", callback_data="owner:missile_draft_edit:hq_required")],
        [InlineKeyboardButton("🏭 سطح زرادخانه لازم", callback_data="owner:missile_draft_edit:arsenal_required")],
        [InlineKeyboardButton("✅ تأیید نهایی", callback_data="owner:missile_draft_confirm")],
        [InlineKeyboardButton("✏️ ویرایش نام", callback_data="owner:missile_name_edit")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=back)],
    ])

# Backward-compatible aliases for older callback imports.
MissileDraftKeyword = missile_draft_keyboard
MisileDraftKeyword = missile_draft_keyboard

# Compatibility keyboards for missile type/loot flows.
def missile_type_keyboard(mid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 کروز", callback_data=f"owner:missile_type:{mid}:کروز")],
        [InlineKeyboardButton("🚀 بالستیک", callback_data=f"owner:missile_type:{mid}:بالستیک")],
        [InlineKeyboardButton("⚡ هایپرسونیک", callback_data=f"owner:missile_type:{mid}:هایپرسونیک")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=f"owner:missile:{mid}")],
    ])


def missile_create_type_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 کروز", callback_data="owner:missile_create_type:کروز")],
        [InlineKeyboardButton("🚀 بالستیک", callback_data="owner:missile_create_type:بالستیک")],
        [InlineKeyboardButton("⚡ هایپرسونیک", callback_data="owner:missile_create_type:هایپرسونیک")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="owner:missiles")],
    ])


def missile_loot_percent_keyboard(mid, level):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 تنظیم درصد غارت", callback_data=f"owner:missile_loot:{mid}:{level}")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=f"owner:missile_level:{mid}:{level}")],
    ])


def missile_global_loot_percent_keyboard():
    values = [5, 10, 15, 20, 25, 30, 40, 50, 100]
    rows = [[InlineKeyboardButton(f"{v}٪", callback_data=f"owner:global_loot_percent_set:{v}") for v in values[i:i+3]] for i in range(0, len(values), 3)]
    rows.append([InlineKeyboardButton("✏️ تنظیم دلخواه", callback_data="owner:global_loot_percent_custom")])
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data="owner:missiles")])
    return InlineKeyboardMarkup(rows)

# تنظیمات امنیت و پشتیبان‌گیری Owner
def owner_security_backup_keyboard(session):
    """سازگاری با نسخه‌های قبلی؛ پنل امنیت را برمی‌گرداند."""
    return owner_security_keyboard()


def owner_social_links_keyboard():
    # افزودن و حذف کنار هم؛ لیست در ردیف مستقل زیر آن‌ها.
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ افزودن", callback_data="owner:social_add"),
            InlineKeyboardButton("🗑️ حذف", callback_data="owner:social_delete"),
        ],
        [InlineKeyboardButton("📋 لیست", callback_data="owner:social_list")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="owner:general_settings")],
    ])

def owner_social_add_keyboard():
    labels = [("panel", "🧩 پنل بازی"), ("mandatory_ad", "🚨 تبلیغ اجباری"),
              ("optional_ad", "🎁 تبلیغ اختیاری"), ("chat", "💬 چت بازی"), ("channel", "📣 کانال بازی")]
    rows=[[InlineKeyboardButton(label, callback_data=f"owner:social_add_type:{typ}")] for typ,label in labels]
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data="owner:social_links")])
    return InlineKeyboardMarkup(rows)

def owner_social_list_keyboard(items):
    return owner_social_item_keyboard('detail', items)

def owner_social_item_detail_keyboard(item_id, active=True, item_type=None):
    rows = [[InlineKeyboardButton("🔴 غیرفعال کردن" if active else "🟢 فعال کردن", callback_data=f"owner:social_toggle:{item_id}")]]
    if item_type in {"optional_ad", "mandatory_ad"}:
        rows.append([InlineKeyboardButton("✏️ ویرایش", callback_data=f"owner:social_edit_item:{item_id}:menu")])
    else:
        rows.append([InlineKeyboardButton("✏️ ویرایش", callback_data=f"owner:social_edit_item:{item_id}:link")])
    rows.append([InlineKeyboardButton("🗑️ حذف", callback_data=f"owner:social_delete_item:{item_id}")])
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data="owner:social_list")])
    return InlineKeyboardMarkup(rows)


def owner_social_edit_keyboard(item_id, item_type):
    rows=[[InlineKeyboardButton("🔗 ویرایش لینک", callback_data=f"owner:social_edit_item:{item_id}:link")]]
    if item_type == "optional_ad":
        rows.append([InlineKeyboardButton("☢️ ویرایش پاداش", callback_data=f"owner:social_edit_item:{item_id}:reward")])
    if item_type in {"mandatory_ad","optional_ad"}:
        rows.append([InlineKeyboardButton("👥 ویرایش محدودیت کاربر", callback_data=f"owner:social_edit_item:{item_id}:members")])
        rows.append([InlineKeyboardButton("⏱️ ویرایش محدودیت زمان", callback_data=f"owner:social_edit_item:{item_id}:time")])
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data=f"owner:social_item:{item_id}")])
    return InlineKeyboardMarkup(rows)

def owner_mandatory_ad_edit_keyboard(item_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 ویرایش لینک", callback_data=f"owner:social_edit_item:{item_id}:link")],
        [InlineKeyboardButton("👥 ویرایش محدودیت اعضا", callback_data=f"owner:social_edit_item:{item_id}:members")],
        [InlineKeyboardButton("⏱️ ویرایش محدودیت زمانی", callback_data=f"owner:social_edit_item:{item_id}:time")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=f"owner:social_item:{item_id}")],
    ])

def owner_optional_ad_edit_keyboard(item_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("☢️ ویرایش پاداش", callback_data=f"owner:social_edit_item:{item_id}:reward")],
        [InlineKeyboardButton("🔗 ویرایش لینک", callback_data=f"owner:social_edit_item:{item_id}:link")],
        [InlineKeyboardButton("👥 ویرایش محدودیت کاربر", callback_data=f"owner:social_edit_item:{item_id}:members")],
        [InlineKeyboardButton("⏱️ ویرایش محدودیت زمان", callback_data=f"owner:social_edit_item:{item_id}:time")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=f"owner:social_item:{item_id}")],
    ])

def owner_optional_ad_members_keyboard(item_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("♾️ بدون محدودیت کاربر", callback_data=f"owner:social_edit_set:{item_id}:members:none")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=f"owner:social_edit_item:{item_id}:menu")],
    ])

def owner_optional_ad_time_keyboard(item_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("♾️ بدون محدودیت زمان", callback_data=f"owner:social_edit_set:{item_id}:time:none")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=f"owner:social_edit_item:{item_id}:menu")],
    ])

def owner_social_delete_keyboard(items):
    return owner_social_item_keyboard('delete', items)

def owner_social_type_keyboard(action):
    # سازگاری با نسخه‌های قدیمی
    if action == 'add':
        return owner_social_add_keyboard()
    labels = [("panel", "🧩 پنل بازی"), ("mandatory_ad", "🚨 تبلیغ اجباری"),
              ("optional_ad", "🎁 تبلیغ اختیاری"), ("chat", "💬 چت بازی"), ("channel", "📣 کانال بازی")]
    rows=[[InlineKeyboardButton(label, callback_data=f"owner:social_{action}_type:{typ}")] for typ,label in labels]
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data="owner:social_links")])
    return InlineKeyboardMarkup(rows)

def social_members_constraint_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("♾️ بدون محدودیت اعضا", callback_data="owner:social_constraint_members:none")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="owner:social_constraint_members:back")],
    ])

def social_time_constraint_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("♾️ بدون محدودیت زمانی", callback_data="owner:social_constraint_time:none")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="owner:social_constraint_time:back")],
    ])

def social_constraint_keyboard():
    # سازگاری با نسخه‌های قبلی؛ مسیر جدید مرحله‌ای است.
    return social_members_constraint_keyboard()

def social_add_edit_keyboard(pending):
    typ=pending.get("field")
    rows=[[InlineKeyboardButton("🔗 ویرایش لینک", callback_data="owner:social_constraint:edit_link")]]
    if typ == "optional_ad":
        rows.append([InlineKeyboardButton("☢️ ویرایش پاداش", callback_data="owner:social_constraint:edit_reward")])
    if typ in {"mandatory_ad","optional_ad"}:
        rows.append([InlineKeyboardButton("👥 ویرایش محدودیت کاربر", callback_data="owner:social_constraint:edit_members")])
        rows.append([InlineKeyboardButton("⏱️ ویرایش محدودیت زمان", callback_data="owner:social_constraint:edit_time")])
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data="owner:social_constraint:back")])
    return InlineKeyboardMarkup(rows)

def social_add_confirm_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأیید و ثبت", callback_data="owner:social_add_confirm")],
        [InlineKeyboardButton("✏️ ویرایش", callback_data="owner:social_constraint:edit")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="owner:social_constraint:back")],
    ])

def owner_social_item_keyboard(action, items):
    rows=[]
    for i,item in enumerate(items,1):
        label = {"panel":"🧩", "mandatory_ad":"🚨", "optional_ad":"🎁", "chat":"💬", "channel":"📣"}.get(item.get("type"),"🔗")
        short=str(item.get("url") or "")
        if len(short)>32: short=short[:29]+"…"
        
        if action == 'delete':
            cb=f"owner:social_delete_item:{item.get('id')}"
        elif action == 'detail':
            cb=f"owner:social_item:{item.get('id')}"
        else:
            cb=f"owner:social_edit_item:{item.get('id')}"
        rows.append([InlineKeyboardButton(f"{label} {i} — {short}", callback_data=cb)])
        if action == 'edit' and item.get('type') == 'optional_ad':
            rows.append([InlineKeyboardButton(f"☢️ پاداش تبلیغ {i}", callback_data=f"owner:social_reward_item:{item.get('id')}")])
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data="owner:social_links")])
    return InlineKeyboardMarkup(rows)

def social_links_keyboard(settings):
    rows=[]; has_optional=False
    for item in settings.get("items", []):
        if not bool(item.get("active", True)): continue
        url=str(item.get("url") or "").strip()
        if not url: continue
        typ=item.get("type")
        if typ == "panel": continue
        label={"mandatory_ad":"🚨 تبلیغ اجباری","optional_ad":"🎁 تبلیغ اختیاری","chat":"💬 چت بازی","channel":"📣 کانال بازی"}.get(typ,"🔗")
        rows.append([InlineKeyboardButton(label,url=url)])
        if typ=="optional_ad": has_optional=True
    return InlineKeyboardMarkup(rows) if rows else None


def shield_management_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚙️ تنظیمات خودکار سپر", callback_data="owner:shield_auto_settings")],
        [InlineKeyboardButton("🌍 سپرهای قاره‌ای", callback_data="owner:shield_type:continental")],
        [InlineKeyboardButton("🌐 سپرهای جهانی", callback_data="owner:shield_type:global")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="owner:game_management")],
    ])

def shield_type_management_keyboard(typ, type_enabled=True):
    # وضعیت کلی نوع سپر فقط در بالاترین ردیف قرار دارد؛
    # وضعیت تک‌تک سپرها داخل صفحه جزئیات همان سپر مدیریت می‌شود.
    label = "🔴 غیرفعال کردن نوع سپر" if type_enabled else "🟢 فعال کردن نوع سپر"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data=f"owner:shield_type_toggle:{typ}")],
        [InlineKeyboardButton("➕ افزودن", callback_data=f"owner:shield_add:{typ}")],
        [InlineKeyboardButton("📋 لیست", callback_data=f"owner:shield_list:{typ}:1")],
        [InlineKeyboardButton("➖ حذف", callback_data=f"owner:shield_delete:{typ}:1")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="owner:shields")],
    ])

def shield_item_list_keyboard(items, typ, page=1, mode="list"):
    per_page=10; page=max(1,int(page)); total=max(1,(len(items)+per_page-1)//per_page)
    page_items=items[(page-1)*per_page:page*per_page]; rows=[]
    for item in page_items:
        status="🟢" if item.get('active') else "🔴"
        if mode=="delete": cb=f"owner:shield_delete_item:{typ}:{item.get('id')}"
        elif mode=="toggle": cb=f"owner:shield_toggle_item:{typ}:{item.get('id')}"
        else: cb=f"owner:shield_item:{typ}:{item.get('id')}"
        rows.append([InlineKeyboardButton(f"{status} {item.get('name','سپر')} | ☢️ {float(item.get('price',0) or 0):,.0f}",callback_data=cb)])
    nav=[]
    if page>1: nav.append(InlineKeyboardButton("⬅️ قبلی",callback_data=f"owner:shield_{mode}:{typ}:{page-1}"))
    nav.append(InlineKeyboardButton(f"📄 {page}/{total}",callback_data="owner:list_noop"))
    if page<total: nav.append(InlineKeyboardButton("بعدی ➡️",callback_data=f"owner:shield_{mode}:{typ}:{page+1}"))
    rows.append(nav); rows.append([InlineKeyboardButton("🔙 برگشت",callback_data=f"owner:shield_type:{typ}")])
    return InlineKeyboardMarkup(rows)

def shield_item_detail_keyboard(typ, item_id, active):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑️ حذف", callback_data=f"owner:shield_delete_item:{typ}:{item_id}"), InlineKeyboardButton("✏️ ویرایش", callback_data=f"owner:shield_edit:{typ}:{item_id}")],
        [InlineKeyboardButton("🔴 غیرفعال کردن" if active else "🟢 فعال کردن", callback_data=f"owner:shield_toggle_item:{typ}:{item_id}")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=f"owner:shield_list:{typ}:1")],
    ])

def shield_delete_confirm_keyboard(typ, item_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ بله، حذف شود", callback_data=f"owner:shield_delete_confirm:{typ}:{item_id}")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=f"owner:shield_item:{typ}:{item_id}")],
    ])

def shield_edit_keyboard(typ, item_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏷️ نام", callback_data=f"owner:shield_edit_field:{typ}:{item_id}:name")],
        [InlineKeyboardButton("☢️ قیمت", callback_data=f"owner:shield_edit_field:{typ}:{item_id}:price")],
        [InlineKeyboardButton("⏱️ مدت فعال بودن", callback_data=f"owner:shield_edit_field:{typ}:{item_id}:duration")],
        [InlineKeyboardButton("🔁 مدت زمان بین خرید", callback_data=f"owner:shield_edit_field:{typ}:{item_id}:cooldown")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=f"owner:shield_item:{typ}:{item_id}")],
    ])

def shield_add_keyboard(typ):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data=f"owner:shield_type:{typ}")]])




def shield_auto_settings_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 تعداد اتک دریافتی", callback_data="owner:shield_auto_setting:auto_attack_threshold")],
        [InlineKeyboardButton("🛡️ مدت سپر رایگان", callback_data="owner:shield_auto_setting:auto_shield_hours")],
        [InlineKeyboardButton("⏳ کسر از سپر هنگام اتک", callback_data="owner:shield_auto_setting:shield_attack_penalty_hours")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="owner:shields")],
    ])



def shield_user_country_pick_keyboard(user_id: int, countries, mode="adjust", back_callback="admin:user_tools"):
    action = "shield_pick_country" if mode == "adjust" else "shield_reset_pick_country"
    rows=[[InlineKeyboardButton(f"🌍 {c.title}", callback_data=f"admin:{action}:{int(user_id)}:{int(c.id)}")] for c in countries]
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data=back_callback)])
    return InlineKeyboardMarkup(rows)

def shield_user_country_keyboard(user_id: int, countries, mode="manage", back_callback=None):
    rows=[]
    for c in countries:
        rows.append([InlineKeyboardButton(f"🌍 {c.title}", callback_data=f"admin:shield_country:{user_id}:{c.id}:{mode}")])
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data=back_callback or f"admin:user_game_settings:{user_id}")])
    return InlineKeyboardMarkup(rows)

def shield_user_sign_keyboard(back_callback="admin:user_tools", reset_callback="admin:shield_reset_select"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ افزایش سپر", callback_data="admin:shield_sign:add")],
        [InlineKeyboardButton("➖ کاهش سپر", callback_data="admin:shield_sign:remove")],
        [InlineKeyboardButton("♻️ ریست محدودیت خرید", callback_data=reset_callback)],
        [InlineKeyboardButton("🔙 برگشت", callback_data=back_callback)],
    ])

def shield_user_mode_keyboard(sign, back_callback="admin:user_tools"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 تک‌نفره", callback_data=f"admin:shield_mode:{sign}:single")],
        [InlineKeyboardButton("👥 چندنفره", callback_data=f"admin:shield_mode:{sign}:multiple")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=back_callback)],
    ])

def shield_user_multiple_keyboard(sign, has_users=False, back_callback="admin:user_tools"):
    rows=[]
    if has_users:
        rows.append([InlineKeyboardButton("➕ افزودن کاربر دیگر", callback_data=f"admin:shield_mode:{sign}:multiple")])
        rows.append([InlineKeyboardButton("✅ پایان انتخاب کاربران", callback_data="admin:shield_users_done")])
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data=back_callback)])
    return InlineKeyboardMarkup(rows)

def shield_user_type_keyboard(sign, back_callback="admin:user_tools"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌍 سپر قاره‌ای", callback_data=f"admin:shield_type:{sign}:continental")],
        [InlineKeyboardButton("🌐 سپر جهانی", callback_data=f"admin:shield_type:{sign}:global")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=back_callback)],
    ])

def shield_user_amount_keyboard(sign, shield_type, back_callback="admin:user_tools"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data="admin:shield_adjust_back")]])

def shield_user_confirm_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأیید تغییر", callback_data="admin:shield_adjust_confirm")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="admin:shield_adjust_cancel")],
    ])

def shield_reset_mode_keyboard(back_callback="admin:user_tools"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 تک‌نفره", callback_data="admin:shield_reset_mode:single")],
        [InlineKeyboardButton("👥 چندنفره", callback_data="admin:shield_reset_mode:multiple")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=back_callback)],
    ])

def shield_reset_multiple_keyboard(has_users=False, back_callback="admin:user_tools"):
    rows=[]
    if has_users:
        rows.append([InlineKeyboardButton("➕ افزودن کاربر دیگر", callback_data="admin:shield_reset_add")])
        rows.append([InlineKeyboardButton("✅ پایان انتخاب کاربران", callback_data="admin:shield_reset_done")])
    rows.append([InlineKeyboardButton("🔙 برگشت", callback_data=back_callback)])
    return InlineKeyboardMarkup(rows)

def shield_reset_confirm_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ بله، ریست شود", callback_data="admin:shield_reset_confirm")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="admin:shield_reset_cancel")],
    ])


def golden_owner_keyboard(cfg):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('⚙️ تنظیمات عمومی جعبه‌ها',callback_data='owner:golden_general')],
        [InlineKeyboardButton('📦 تنظیمات جعبه‌ها',callback_data='owner:golden_box_settings')],
        [InlineKeyboardButton('🧩 تنظیمات چالش',callback_data='owner:golden_challenge')],
        [InlineKeyboardButton('📊 آمار',callback_data='owner:golden_stats')],
        [InlineKeyboardButton('🔙 برگشت',callback_data='owner:challenges')],
    ])

def golden_general_keyboard(cfg):
    on=bool(cfg.get('enabled'))
    opened=max(0,int(cfg.get("opened_delete_seconds",0) or 0))//60
    unanswered=max(1,int(cfg.get("unanswered_delete_seconds",60) or 60))//60
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('🔴 خاموش کردن' if on else '🟢 روشن کردن',callback_data='owner:golden_toggle')],
        [InlineKeyboardButton(f'📦 تعداد روزانه: {int(cfg.get("daily_count",0) or 0)}',callback_data='owner:golden_edit:daily_count'),
         InlineKeyboardButton('📅 روزهای ارسال',callback_data='owner:golden_days')],
        [InlineKeyboardButton(f'🕐 شروع: {cfg.get("start","10:00")}',callback_data='owner:golden_edit:start'),
         InlineKeyboardButton(f'🕐 پایان: {cfg.get("end","23:00")}',callback_data='owner:golden_edit:end')],
        [InlineKeyboardButton(f'🗑️ حذف پس از باز شدن: {opened} دقیقه',callback_data='owner:golden_edit:opened_delete_minutes'),
         InlineKeyboardButton(f'⌛ حذف بدون برنده: {unanswered} دقیقه',callback_data='owner:golden_edit:unanswered_delete_minutes')],
        [InlineKeyboardButton('🔙 برگشت',callback_data='owner:golden')],
    ])

def golden_days_keyboard(cfg):
    days=set(int(x) for x in (cfg.get('active_days',list(range(7))) or []))
    names=['شنبه','یکشنبه','دوشنبه','سه‌شنبه','چهارشنبه','پنجشنبه','جمعه']
    rows=[]
    for i in range(0,7,2):
        row=[]
        for j in (i,i+1):
            if j<7:
                row.append(InlineKeyboardButton(('🟢 ' if j in days else '⚪ ')+names[j],callback_data=f'owner:golden_day:{j}'))
        rows.append(row)
    rows.append([InlineKeyboardButton('🔙 برگشت',callback_data='owner:golden_general')])
    return InlineKeyboardMarkup(rows)

def golden_box_settings_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('💰 جعبه پول',callback_data='owner:golden_box:money')],
        [InlineKeyboardButton('⛽ جعبه سوخت',callback_data='owner:golden_box:fuel')],
        [InlineKeyboardButton('🔩 جعبه فلز',callback_data='owner:golden_box:metal')],
        [InlineKeyboardButton('☢️ جعبه اورانیوم',callback_data='owner:golden_box:uranium')],
        [InlineKeyboardButton('🔙 برگشت',callback_data='owner:golden')],
    ])

def golden_box_detail_keyboard(k):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('🎲 احتمال',callback_data=f'owner:golden_box_edit:{k}:weight')],
        [InlineKeyboardButton('⭐ حداکثر سطح',callback_data=f'owner:golden_box_edit:{k}:max')],
        [InlineKeyboardButton('⚡ اورانیوم تکمیل فوری',callback_data=f'owner:golden_box_edit:{k}:instant_uranium')],
        [InlineKeyboardButton('📊 تنظیمات سطوح',callback_data=f'owner:golden_box_levels:{k}')],
        [InlineKeyboardButton('🔙 برگشت',callback_data='owner:golden_box_settings')],
    ])

def golden_box_levels_keyboard(k, max_level):
    rows=[]
    max_level=max(1,min(100,int(max_level or 1)))
    for start in range(1,max_level+1,5):
        rows.append([InlineKeyboardButton(f'سطح {lv}',callback_data=f'owner:golden_box_level:{k}:{lv}') for lv in range(start,min(start+5,max_level+1))])
    rows.append([InlineKeyboardButton('🔙 برگشت',callback_data=f'owner:golden_box:{k}')])
    return InlineKeyboardMarkup(rows)

def golden_box_level_edit_keyboard(k, level):
    level = int(level or 1)
    rows = [
        [InlineKeyboardButton('🎁 حداقل جایزه',callback_data=f'owner:golden_box_level_edit:{k}:{level}:reward_min'),
         InlineKeyboardButton('🎁 حداکثر جایزه',callback_data=f'owner:golden_box_level_edit:{k}:{level}:reward_max')],
    ]
    if level >= 2:
        rows.append([
            InlineKeyboardButton('💰 هزینه ارتقا',callback_data=f'owner:golden_box_level_edit:{k}:{level}:cost'),
            InlineKeyboardButton('⏱ زمان ارتقا',callback_data=f'owner:golden_box_level_edit:{k}:{level}:time'),
        ])
        rows.append([
            InlineKeyboardButton('🏛️ مرکز فرماندهی موردنیاز',callback_data=f'owner:golden_box_level_edit:{k}:{level}:hq'),
        ])
    rows.append([InlineKeyboardButton('🔙 برگشت',callback_data=f'owner:golden_box_levels:{k}')])
    return InlineKeyboardMarkup(rows)

def golden_weights_keyboard(cfg):
    return golden_box_settings_keyboard()

def golden_schedule_keyboard(cfg):
    days=cfg.get('active_days',list(range(7)))
    daynames=['شنبه','یکشنبه','دوشنبه','سه‌شنبه','چهارشنبه','پنجشنبه','جمعه']
    rows=[[InlineKeyboardButton(f'📦 تعداد روزانه: {int(cfg.get("daily_count",0))}',callback_data='owner:golden_edit:daily_count'),InlineKeyboardButton(f'🕐 شروع: {cfg.get("start")}',callback_data='owner:golden_edit:start')],
          [InlineKeyboardButton(f'🕐 پایان: {cfg.get("end")}',callback_data='owner:golden_edit:end')]]
    for i in range(0,7,2):
        row=[]
        for j in (i,i+1):
            if j<7: row.append(InlineKeyboardButton(('🟢 ' if j in days else '🔴 ')+daynames[j],callback_data=f'owner:golden_day:{j}'))
        rows.append(row)
    rows.append([InlineKeyboardButton('🔙 برگشت',callback_data='owner:golden_general')])
    return InlineKeyboardMarkup(rows)

def golden_expiry_keyboard(cfg):
    opened=max(0,int(cfg.get('opened_delete_seconds',30) or 0))//60
    unanswered=max(1,int(cfg.get('unanswered_delete_seconds',60) or 60))//60
    if unanswered < 1: unanswered=1
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f'🗑️ حذف بعد از باز شدن: {opened} دقیقه',callback_data='owner:golden_edit:opened_delete_minutes')],
        [InlineKeyboardButton(f'⌛ حذف بدون برنده: {unanswered} دقیقه',callback_data='owner:golden_edit:unanswered_delete_minutes')],
        [InlineKeyboardButton('🔙 برگشت',callback_data='owner:golden_general')],
    ])

def golden_challenge_keyboard(cfg):
    return InlineKeyboardMarkup([[InlineKeyboardButton(f'🔢 تعداد رقم رمز: {cfg.get("challenge_digits",5)}',callback_data='owner:golden_edit:challenge_digits')],[InlineKeyboardButton(f'🔘 تعداد گزینه‌ها: {cfg.get("options_count",4)}',callback_data='owner:golden_edit:options_count')],[InlineKeyboardButton('🔙 برگشت',callback_data='owner:golden')]])
