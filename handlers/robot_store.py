from __future__ import annotations

import json
import math
import re
import uuid
from datetime import datetime
from html import escape

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from config import OWNER_ID
from database.db import SessionLocal
from database.models import BotSetting, ProductInventory, User, Wallet
from services.wallet import ensure_wallet, get_bool, WALLET_ENABLED, format_amount
from services.economy import get_missiles_config
from services.construction_teams import get_construction_teams_config

CATALOG_KEY = "robot_store_catalog_v1"

RESOURCE_LABELS = {
    "money": "💰 پول",
    "metal": "🔩 فلز",
    "fuel": "⛽ سوخت",
    "uranium": "☢️ اورانیوم",
}
RESOURCE_ORDER = ("money", "metal", "fuel", "uranium")
CATEGORY_LABELS = {
    "resources": "💰 منابع",
    "population": "👥 شهروند",
    "leadership": "👑 تجربه رهبری",
    "shields": "🛡️ سپر",
    "missiles": "🚀 موشک‌ها",
    "teams": "🏗️ تیم ساخت‌وساز",
    "bundles": "📦 محصولات ترکیبی",
    "events": "🎉 محصولات مناسبتی",
}
SHIELD_LABELS = {"global": "🌐 سپر جهانی", "continental": "🛡️ سپر قاره‌ای"}


def _btn(text, data, style="primary"):
    return InlineKeyboardButton(text, callback_data=data, style=style)


def _markup(rows):
    return InlineKeyboardMarkup(rows)


def _uid_cb(uid, *parts):
    return "rs:u:{}:{}".format(int(uid), ":".join(str(x) for x in parts))


def _owner_cb(*parts):
    return "rs:o:" + ":".join(str(x) for x in parts)


def _default_quantity_config(minimum=1):
    return {
        "enabled": False,
        "unit_amount": 100,
        "unit_price": 0,
        "min": minimum,
        "max": 0,
        "plans": [],
    }


def _default_catalog():
    return {
        "enabled": True,
        "resources": {key: _default_quantity_config(1) for key in RESOURCE_ORDER},
        "population": _default_quantity_config(1),
        "leadership": _default_quantity_config(1),
        "shields": {
            "global": _default_quantity_config(1),
            "continental": _default_quantity_config(1),
        },
        "missiles": {},
        "teams": {},
        "custom_products": [],
    }


def _catalog(session):
    row = session.scalar(select(BotSetting).where(BotSetting.key == CATALOG_KEY))
    if row is None:
        data = _default_catalog()
        row = BotSetting(key=CATALOG_KEY, value=json.dumps(data, ensure_ascii=False))
        session.add(row)
        session.flush()
    else:
        try:
            data = json.loads(row.value or "{}")
        except Exception:
            data = _default_catalog()
        if not isinstance(data, dict):
            data = _default_catalog()

    defaults = _default_catalog()
    data.setdefault("enabled", True)
    for section in ("resources", "shields"):
        data.setdefault(section, {})
        for key, value in defaults[section].items():
            current = data[section].setdefault(key, value)
            if not isinstance(current, dict):
                data[section][key] = dict(value)
            else:
                for field, default in value.items():
                    current.setdefault(field, default)
                if not isinstance(current.get("plans"), list):
                    current["plans"] = []
    for section in ("population", "leadership"):
        value = data.setdefault(section, dict(defaults[section]))
        if not isinstance(value, dict):
            data[section] = dict(defaults[section])
        else:
            for field, default in defaults[section].items():
                value.setdefault(field, default)
            if not isinstance(value.get("plans"), list):
                value["plans"] = []

    missiles = data.setdefault("missiles", {})
    if not isinstance(missiles, dict):
        missiles = data["missiles"] = {}
    missile_cfg = get_missiles_config(session)
    for missile in missile_cfg.get("items", []):
        mid = str(missile.get("id", "")).strip()
        if not mid:
            continue
        conf = missiles.setdefault(mid, {"enabled": False, "unit_price": 0, "min": 1, "max": 0, "plans": []})
        if not isinstance(conf, dict):
            conf = missiles[mid] = {"enabled": False, "unit_price": 0, "min": 1, "max": 0, "plans": []}
        conf.setdefault("enabled", False)
        # نگهداری فیلدهای قدیمی برای سازگاری با نسخه‌های قبلی؛ تنظیمات فروش
        # از این نسخه به بعد برای هر سطح موشک جداگانه ذخیره می‌شوند.
        conf.setdefault("unit_price", 0)
        conf.setdefault("min", 1)
        conf.setdefault("max", 0)
        conf.setdefault("plans", [])
        if not isinstance(conf.get("plans"), list):
            conf["plans"] = []
        had_level_config = isinstance(conf.get("levels"), dict)
        levels = conf.setdefault("levels", {})
        if not isinstance(levels, dict):
            levels = conf["levels"] = {}
            had_level_config = False
        max_level = max(1, min(100, int(missile.get("max_level", 1) or 1)))
        legacy_level = {
            "enabled": bool(conf.get("enabled", False)),
            "unit_price": int(conf.get("unit_price", 0) or 0),
            "min": int(conf.get("min", 1) or 1),
            "max": int(conf.get("max", 0) or 0),
            "plans": list(conf.get("plans", []) or []),
        }
        for level in range(1, max_level + 1):
            level_conf = levels.setdefault(str(level), dict(legacy_level) if not had_level_config else {
                "enabled": False, "unit_price": 0, "min": 1, "max": 0, "plans": []
            })
            if not isinstance(level_conf, dict):
                level_conf = levels[str(level)] = {"enabled": False, "unit_price": 0, "min": 1, "max": 0, "plans": []}
            level_conf.setdefault("enabled", False)
            level_conf.setdefault("unit_price", 0)
            level_conf.setdefault("min", 1)
            level_conf.setdefault("max", 0)
            level_conf.setdefault("plans", [])
            if not isinstance(level_conf.get("plans"), list):
                level_conf["plans"] = []

    data.setdefault("teams", {})
    if not isinstance(data["teams"], dict):
        data["teams"] = {}
    team_cfg = get_construction_teams_config(session)
    max_teams = max(1, min(10, int(team_cfg.get("max_teams", 10) or 10)))
    for number in range(2, max_teams + 1):
        conf = data["teams"].setdefault(str(number), {"enabled": False, "price": 0})
        if not isinstance(conf, dict):
            data["teams"][str(number)] = {"enabled": False, "price": 0}
        else:
            conf.setdefault("enabled", False)
            conf.setdefault("price", 0)

    products = data.setdefault("custom_products", [])
    if not isinstance(products, list):
        data["custom_products"] = []
    row.value = json.dumps(data, ensure_ascii=False)
    session.flush()
    return data


def _save_catalog(session, data):
    row = session.scalar(select(BotSetting).where(BotSetting.key == CATALOG_KEY))
    raw = json.dumps(data, ensure_ascii=False)
    if row is None:
        session.add(BotSetting(key=CATALOG_KEY, value=raw))
    else:
        row.value = raw
    session.flush()


def _user_keyboard(uid):
    rows = [
        [_btn("💰 منابع", _uid_cb(uid, "cat", "resources")), _btn("👥 شهروند", _uid_cb(uid, "cat", "population"))],
        [_btn("👑 تجربه رهبری", _uid_cb(uid, "cat", "leadership")), _btn("🛡️ سپر", _uid_cb(uid, "cat", "shields"))],
        [_btn("🚀 موشک‌ها", _uid_cb(uid, "cat", "missiles")), _btn("🏗️ تیم ساخت‌وساز", _uid_cb(uid, "cat", "teams"))],
        [_btn("📦 محصولات ترکیبی", _uid_cb(uid, "cat", "bundles")), _btn("🎉 محصولات مناسبتی", _uid_cb(uid, "cat", "events"))],
    ]
    return _markup(rows)


def _owner_keyboard():
    return _markup([
        # کلید فعال/غیرفعال همیشه در ابتدای پنل مدیریت فروشگاه نمایش داده می‌شود.
        [_btn("🔴 غیرفعال کردن فروشگاه" if _catalog_enabled_cache else "🟢 فعال کردن فروشگاه", _owner_cb("toggle_store"), "danger" if _catalog_enabled_cache else "success")],
        [_btn("💰 مدیریت منابع", _owner_cb("category", "resources")), _btn("👥 مدیریت شهروند", _owner_cb("category", "population"))],
        [_btn("👑 تجربه رهبری", _owner_cb("category", "leadership")), _btn("🛡️ مدیریت سپر", _owner_cb("category", "shields"))],
        [_btn("🚀 مدیریت موشک‌ها", _owner_cb("category", "missiles")), _btn("🏗️ تیم ساخت‌وساز", _owner_cb("category", "teams"))],
        [_btn("📦 محصولات ترکیبی", _owner_cb("category", "bundles")), _btn("🎉 محصولات مناسبتی", _owner_cb("category", "events"))],
        [_btn("📜 تاریخچه فروش", _owner_cb("history", 1))],
        [_btn("🔙 برگشت", "owner:back_owner_panel", "danger")],
    ])

# Set only while rendering owner home; this avoids a second catalog read in the keyboard helper.
_catalog_enabled_cache = True


def _owner_missile_type_keyboard(missile_type, data, session):
    missile_cfg = get_missiles_config(session)
    catalog_missiles = data.get("missiles", {})
    items = [
        m for m in missile_cfg.get("items", [])
        if str(m.get("type", "")).strip() == str(missile_type)
    ]
    buttons = []
    for missile in items:
        mid = str(missile.get("id", ""))
        if not mid:
            continue
        conf = catalog_missiles.get(mid, {})
        status = "🟢" if conf.get("enabled") else "🔴"
        buttons.append(_btn(f"{status} {str(missile.get('name') or 'موشک')[:35]}", _owner_cb("missile_levels", mid)))
    rows = [buttons[i:i + 3] for i in range(0, len(buttons), 3)]
    rows.append([_btn("🔙 برگشت", _owner_cb("category", "missiles"), "danger")])
    return _markup(rows)


def _owner_missile_levels_keyboard(missile, data):
    mid = str(missile.get("id"))
    conf = data.get("missiles", {}).get(mid, {})
    enabled = bool(conf.get("enabled", False))
    rows = [[_btn(
        "🔴 غیرفعال کردن فروش این موشک" if enabled else "🟢 فعال کردن فروش این موشک",
        _owner_cb("missile_toggle", mid),
        "danger" if enabled else "success",
    )]]
    level_configs = conf.get("levels", {}) if isinstance(conf.get("levels"), dict) else {}
    max_level = max(1, min(100, int(missile.get("max_level", 1) or 1)))
    level_buttons = []
    for level in range(1, max_level + 1):
        level_conf = level_configs.get(str(level), {})
        status = "🟢" if level_conf.get("enabled") else "🔴"
        level_buttons.append(_btn(f"{status} سطح {level}", _owner_cb("missile_level", mid, level)))
    rows.extend(level_buttons[i:i + 5] for i in range(0, len(level_buttons), 5))
    rows.append([_btn("🔙 برگشت به دسته موشک‌ها", _owner_cb("missile_type", str(missile.get("type", ""))), "danger")])
    return _markup(rows)


def _category_owner_keyboard(category, data, session):
    rows = []
    if category == "resources":
        # چیدمان دو در دو: پول/فلز در ردیف اول و سوخت/اورانیوم در ردیف دوم.
        rows.extend([
            [_btn(RESOURCE_LABELS["money"], _owner_cb("cfg", "resources", "money")),
             _btn(RESOURCE_LABELS["metal"], _owner_cb("cfg", "resources", "metal"))],
            [_btn(RESOURCE_LABELS["fuel"], _owner_cb("cfg", "resources", "fuel")),
             _btn(RESOURCE_LABELS["uranium"], _owner_cb("cfg", "resources", "uranium"))],
        ])
    elif category in {"population", "leadership"}:
        # این دسته‌ها مستقیماً پنل تنظیمات اصلی خود را باز می‌کنند.
        conf = data[category]
        rows.append([_btn("⚙️ تنظیمات فروش", _owner_cb("cfg", category, "main"))])
    elif category == "shields":
        rows.append([
            _btn(SHIELD_LABELS["global"], _owner_cb("cfg", "shields", "global")),
            _btn(SHIELD_LABELS["continental"], _owner_cb("cfg", "shields", "continental")),
        ])
    elif category == "missiles":
        rows.extend([
            [_btn("🚀 موشک‌های کروز", _owner_cb("missile_type", "کروز")),
             _btn("🚀 موشک‌های بالستیک", _owner_cb("missile_type", "بالستیک"))],
            [_btn("⚡ موشک‌های هایپرسونیک", _owner_cb("missile_type", "هایپرسونیک"))],
        ])
    elif category == "teams":
        team_cfg = get_construction_teams_config(session)
        max_teams = max(1, min(10, int(team_cfg.get("max_teams", 10) or 10)))
        team_buttons = [
            _btn(f"🏗️ تیم ساخت‌وساز {number}", _owner_cb("cfg", "teams", number))
            for number in range(2, max_teams + 1)
        ]
        rows.extend([team_buttons[i:i + 2] for i in range(0, len(team_buttons), 2)])
        if max_teams <= 1:
            rows.append([_btn("ℹ️ تیم قابل خریدی فعال نیست", _owner_cb("noop"))])
    elif category in {"bundles", "events"}:
        kind = "bundle" if category == "bundles" else "event"
        for product in data.get("custom_products", []):
            if product.get("kind") != kind:
                continue
            status = "🟢" if product.get("enabled", True) else "🔴"
            rows.append([_btn(f"{status} {str(product.get('name') or 'محصول')[:45]}", _owner_cb("custom", product.get("id")))])
        label = "بسته ترکیبی" if kind == "bundle" else "محصول مناسبتی"
        rows.append([_btn(f"➕ ساخت {label} جدید", _owner_cb("create", kind), "success")])
    rows.append([_btn("🔙 برگشت", _owner_cb("home"), "danger")])
    return _markup(rows)


def _config_text(category, key, conf, title):
    enabled = "فعال" if conf.get("enabled") else "غیرفعال"
    lines = [f"⚙️ <b>{escape(title)}</b>", "", f"وضعیت فروش: <b>{enabled}</b>"]
    if category == "teams":
        lines.append(f"💰 قیمت خرید: <b>{int(conf.get('price', 0) or 0):,} تومان</b>")
    else:
        if category in {"missiles", "missile_level"}:
            lines.append(f"💰 قیمت هر موشک: <b>{int(conf.get('unit_price', 0) or 0):,} تومان</b>")
        else:
            amount_label = "ساعت" if category == "shields" else ("واحد" if category == "resources" else ("شهروند" if category == "population" else "واحد تجربه"))
            lines.append(f"💰 قیمت هر <b>{int(conf.get('unit_amount', 1) or 1):,} {amount_label}</b>: <b>{int(conf.get('unit_price', 0) or 0):,} تومان</b>")
        lines.append(f"📉 حداقل خرید دلخواه: <b>{conf.get('min', 1)}</b>")
        maximum = int(conf.get("max", 0) or 0)
        lines.append(f"📈 حداکثر خرید دلخواه: <b>{format_amount(maximum) if maximum else 'بدون سقف'}</b>")
        lines.append(f"📦 تعداد پلن‌های فعال: <b>{sum(1 for p in conf.get('plans', []) if p.get('enabled', True))}</b>")
    lines.append("\nاز گزینه‌های زیر برای مدیریت استفاده کنید:")
    return "\n".join(lines)


def _config_keyboard(category, key, conf):
    rows = []
    enabled = bool(conf.get("enabled"))
    rows.append([_btn("🔴 غیرفعال کردن" if enabled else "🟢 فعال کردن", _owner_cb("toggle", category, key), "danger" if enabled else "success")])
    if category == "teams":
        rows.append([_btn("💰 تنظیم قیمت تیم", _owner_cb("set", category, key, "price"))])
    else:
        if category in {"missiles", "missile_level"}:
            rows.append([_btn("💰 تنظیم قیمت هر موشک", _owner_cb("set", category, key, "unit_price"))])
        else:
            rows.append([_btn("🔢 تعیین مقدار واحد", _owner_cb("set", category, key, "unit_amount")), _btn("💵 تنظیم قیمت", _owner_cb("set", category, key, "unit_price"))])
        rows.append([_btn("📉 حداقل خرید", _owner_cb("set", category, key, "min")), _btn("📈 حداکثر خرید", _owner_cb("set", category, key, "max"))])
        rows.append([_btn("📋 مدیریت پلن‌ها", _owner_cb("plans", category, key, 1))])
    if category in {"population", "leadership"}:
        back_callback = _owner_cb("home")
    elif category == "missile_level":
        missile_id = str(key).split("@", 1)[0]
        back_callback = _owner_cb("missile_levels", missile_id)
    else:
        back_category = {"resources": "resources", "shields": "shields", "missiles": "missiles", "teams": "teams"}.get(category, category)
        back_callback = _owner_cb("category", back_category)
    rows.append([_btn("🔙 برگشت", back_callback, "danger")])
    return _markup(rows)


def _plan_list_keyboard(category, key, conf, page=1, delete_mode=False):
    """Buttons for the separate plan browser or plan-deletion selector."""
    plans = list(conf.get("plans", []))
    per_page = 5
    total_pages = max(1, (len(plans) + per_page - 1) // per_page)
    page = max(1, min(int(page or 1), total_pages))
    rows = []
    start = (page - 1) * per_page
    for plan in plans[start:start + per_page]:
        label = str(plan.get("name") or "پلن")[:36]
        if delete_mode:
            rows.append([_btn(f"🗑 {label}", _owner_cb("plan_delete_select", category, key, plan.get("id"), page), "danger")])
        else:
            state = "🟢" if plan.get("enabled", True) else "🔴"
            rows.append([_btn(f"{state} {label} — {int(plan.get('price', 0) or 0):,} تومان", _owner_cb("plan", category, key, plan.get("id"), page))])
    nav = []
    if page > 1:
        action = "plan_delete_mode" if delete_mode else "plan_list"
        nav.append(_btn("◀️ قبلی", _owner_cb(action, category, key, page - 1), "primary"))
    nav.append(_btn(f"صفحه {page}/{total_pages}", _owner_cb("noop")))
    if page < total_pages:
        action = "plan_delete_mode" if delete_mode else "plan_list"
        nav.append(_btn("بعدی ▶️", _owner_cb(action, category, key, page + 1), "primary"))
    if nav:
        rows.append(nav)
    back_action = "plans"
    rows.append([_btn("🔙 برگشت", _owner_cb(back_action, category, key, page), "danger")])
    return _markup(rows)


def _plan_management_text(category, key, conf, title):
    plans = list(conf.get("plans", []))
    enabled_count = sum(1 for plan in plans if plan.get("enabled", True))
    return (
        f"📋 <b>مدیریت پلن‌های {escape(title)}</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"تعداد کل پلن‌ها: <b>{len(plans)}</b>\n"
        f"پلن‌های فعال: <b>{enabled_count}</b>\n\n"
        "از گزینه‌های زیر برای افزودن، حذف یا مشاهده پلن‌ها استفاده کنید."
    )


def _plan_management_keyboard(category, key, conf):
    return _markup([
        [
            _btn("➕ افزودن پلن", _owner_cb("plan_add", category, key, 1), "success"),
            _btn("🗑 حذف پلن", _owner_cb("plan_delete_mode", category, key, 1), "danger"),
        ],
        [_btn("📋 لیست پلن‌ها", _owner_cb("plan_list", category, key, 1))],
        [_btn("🔙 برگشت", _owner_cb("cfg", category, key), "danger")],
    ])


def _plan_text(conf, plan, title):
    amount = plan.get("amount", 0)
    unit = "ساعت" if title in {SHIELD_LABELS["global"], SHIELD_LABELS["continental"]} else ("شهروند" if title == "👥 شهروند" else ("واحد تجربه" if title == "👑 تجربه رهبری" else ("موشک" if "موشک" in title else "واحد")))
    return (f"📋 <b>{escape(str(plan.get('name') or 'پلن'))}</b>\n\n"
            f"📦 مقدار: <b>{amount:,} {unit}</b>\n"
            f"💰 قیمت: <b>{int(plan.get('price', 0) or 0):,} تومان</b>\n"
            f"وضعیت: <b>{'فعال' if plan.get('enabled', True) else 'غیرفعال'}</b>")


def _plan_detail_keyboard(category, key, plan, page=1):
    pid = str(plan.get("id"))
    enabled = bool(plan.get("enabled", True))
    return _markup([
        [_btn("✏️ ویرایش نام", _owner_cb("plan_set", category, key, pid, "name", page))],
        [_btn("🔢 ویرایش مقدار", _owner_cb("plan_set", category, key, pid, "amount", page)), _btn("💰 ویرایش قیمت", _owner_cb("plan_set", category, key, pid, "price", page))],
        [
            _btn("🗑 حذف پلن", _owner_cb("plan_delete", category, key, pid, page), "danger"),
            _btn("🔴 غیرفعال کردن" if enabled else "🟢 فعال کردن", _owner_cb("plan_toggle", category, key, pid, page), "danger" if enabled else "success"),
        ],
        [_btn("🔙 برگشت به لیست پلن‌ها", _owner_cb("plan_list", category, key, page), "danger")],
    ])


def _custom_components_text(product):
    components = product.get("components", [])
    description = str(product.get("description") or "").strip()
    original_price = int(product.get("original_price", 0) or 0)
    package_price = int(product.get("price", 0) or 0)
    lines = [
        f"📦 <b>{escape(str(product.get('name') or 'محصول'))}</b>",
        f"📝 توضیحات: <b>{escape(description) if description else 'بدون توضیحات'}</b>",
        f"💎 قیمت واقعی محصولات: <b>{original_price:,} تومان</b>",
        f"🎁 قیمت بسته: <b>{package_price:,} تومان</b>",
    ]
    if product.get("kind") == "event":
        lines.append(f"🔔 اعلان به کاربران: <b>{'فعال' if product.get('announce', False) else 'غیرفعال'}</b>")
    lines.extend(["", "<b>محتویات:</b>"])
    if not components:
        lines.append("هنوز محصولی به این بسته اضافه نشده است.")
    else:
        for index, comp in enumerate(components, 1):
            lines.append(f"{index}. {escape(_component_label(comp))}")
    lines.append("\nبرای افزودن یا مدیریت محتویات و تعیین قیمت‌ها از دکمه‌های زیر استفاده کنید.")
    return "\n".join(lines)


def _component_label(comp):
    kind = comp.get("kind")
    if kind == "resource":
        return f"{RESOURCE_LABELS.get(comp.get('resource'), 'منبع')}: {int(comp.get('amount', 0) or 0):,}"
    if kind == "population":
        return f"👥 شهروند: {int(comp.get('amount', 0) or 0):,}"
    if kind == "leadership":
        return f"👑 تجربه رهبری: {int(comp.get('amount', 0) or 0):,}"
    if kind == "shield":
        return f"{SHIELD_LABELS.get(comp.get('shield_type'), 'سپر')}: {comp.get('hours', 0)} ساعت"
    if kind == "missile":
        return f"🚀 {comp.get('missile_name', 'موشک')}: {int(comp.get('quantity', 0) or 0):,} عدد"
    if kind == "team":
        return f"🏗️ تیم ساخت‌وساز {int(comp.get('team_number', 0) or 0)}"
    return "محصول"


def _custom_builder_keyboard(product, *, is_new):
    rows = [[
        _btn("➕ افزودن محصول", _owner_cb("add_comp"), "success"),
        _btn("📋 لیست محصولات", _owner_cb("components_list")),
    ]]
    rows.append([_btn("💰 تنظیم قیمت‌ها", _owner_cb("custom_set_price"), "primary")])
    if product.get("kind") == "event":
        announce = bool(product.get("announce", False))
        rows.append([_btn(
            "🔔 اعلان رویداد: فعال" if announce else "🔕 اعلان رویداد: غیرفعال",
            _owner_cb("custom_announce_toggle"),
            "success" if announce else "danger",
        )])
    if is_new:
        rows.append([_btn("✅ ذخیره نهایی محصول", _owner_cb("save_custom"), "success")])
        rows.append([_btn("🔙 برگشت به توضیحات", _owner_cb("custom_back_description"), "danger")])
    else:
        rows.append([_btn("✅ ذخیره تغییرات", _owner_cb("save_custom"), "success")])
        rows.append([_btn("🔙 برگشت به جزئیات محصول", _owner_cb("custom", product.get("id")), "danger")])
    return _markup(rows)


def _custom_detail_keyboard(product):
    enabled = bool(product.get("enabled", True))
    return _markup([
        [_btn("🧩 مشاهده و ویرایش محتویات", _owner_cb("edit_components", product.get("id")))],
        [_btn("✏️ تغییر نام", _owner_cb("custom_set", product.get("id"), "name"))],
        [_btn("💰 قیمت واقعی / قیمت بسته", _owner_cb("custom_set_price", product.get("id")))],
        [_btn("📝 تغییر توضیحات", _owner_cb("custom_set", product.get("id"), "description"))],
        [_btn("🔴 غیرفعال کردن" if enabled else "🟢 فعال کردن", _owner_cb("custom_toggle", product.get("id")), "danger" if enabled else "success")],
        [_btn("🗑 حذف محصول", _owner_cb("custom_delete", product.get("id")), "danger")],
        [_btn("🔙 برگشت", _owner_cb("category", "bundles" if product.get("kind") == "bundle" else "events"), "danger")],
    ])


def _format_payload(payload):
    kind = payload.get("kind")
    if kind == "resource":
        return f"{RESOURCE_LABELS.get(payload.get('resource'), 'منبع')}: {int(payload.get('amount', 0) or 0):,} واحد"
    if kind == "population":
        return f"👥 شهروند: {int(payload.get('amount', 0) or 0):,}"
    if kind == "leadership":
        return f"👑 تجربه رهبری: {int(payload.get('amount', 0) or 0):,}"
    if kind == "shield":
        return f"{SHIELD_LABELS.get(payload.get('shield_type'), 'سپر')}: {payload.get('duration_hours', 0)} ساعت"
    if kind == "missile":
        return f"🚀 {payload.get('missile_name', 'موشک')}: {int(payload.get('quantity', 0) or 0):,} عدد"
    if kind == "team":
        return f"🏗️ تیم ساخت‌وساز شماره {int(payload.get('team_number', 0) or 0)}"
    if kind in {"bundle", "event"}:
        components = payload.get("components", [])
        prefix = "🎉 محصول مناسبتی" if kind == "event" else "📦 محصول ترکیبی"
        detail = "\n".join(f"• {escape(_component_label(c))}" for c in components) or "محتویات ثبت نشده"
        description = str(payload.get("description") or "").strip()
        description_line = f"\n📝 {escape(description)}\n" if description else "\n"
        return f"{prefix}{description_line}{detail}"
    return "محصول خریداری‌شده"


def _parse_number(raw, *, integer=True):
    value = str(raw or "").strip().translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
    value = value.replace(",", "").replace("٬", "").replace("٫", ".").replace(" ", "").replace("_", "")
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise ValueError("invalid")
    if integer:
        if not number.is_integer():
            raise ValueError("integer")
        return int(number)
    return number


async def _edit(query, text, markup=None):
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=markup, disable_web_page_preview=True)


def _register(query):
    try:
        from services.panel_security import register_panel
        register_panel(query.message.chat_id, query.message.message_id, query.from_user.id)
    except Exception:
        pass


async def open_user_store(message, context, session, user):
    catalog = _catalog(session)
    if not catalog.get("enabled", True):
        # فروشگاه غیرفعال نباید هیچ پنل یا دکمه‌ای برای کاربر باز کند.
        await message.reply_text("🔴 فروشگاه محصولات فعلاً غیرفعال است.")
        return
    wallet = ensure_wallet(session, user.telegram_id)
    text = (
        "🛍️ <b>فروشگاه محصولات</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"👛 موجودی کیف پول: <b>{format_amount(wallet.balance)} تومان</b>\n\n"
        "محصول موردنظر را انتخاب کنید. تمام خریدها ابتدا وارد کیف محصولات می‌شوند و فعلاً مستقیماً روی کشور اعمال نمی‌شوند."
    )
    sent = await message.reply_text(text, parse_mode="HTML", reply_markup=_user_keyboard(user.telegram_id))
    from services.panel_security import register_panel
    register_panel(sent.chat_id, sent.message_id, user.telegram_id)


async def open_product_bag(message, context, session, user, page=1):
    await _send_bag_page(message, context, session, user.telegram_id, int(page), reply=True)


async def _send_bag_page(message_or_query, context, session, user_id, page, reply=False):
    page = max(1, int(page or 1))
    per_page = 8
    total = int(session.scalar(select(__import__('sqlalchemy').func.count(ProductInventory.id)).where(ProductInventory.user_id == int(user_id))) or 0)
    pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, pages)
    rows = list(session.scalars(select(ProductInventory).where(ProductInventory.user_id == int(user_id)).order_by(ProductInventory.created_at.desc(), ProductInventory.id.desc()).offset((page - 1) * per_page).limit(per_page)).all())
    if total == 0:
        empty_text = "❌ هیچ محصولی در کیف محصولات موجود نیست."
        if hasattr(message_or_query, "answer"):
            await message_or_query.answer(empty_text, show_alert=True)
        else:
            await message_or_query.reply_text(empty_text)
        return
    lines = ["🎒 <b>کیف محصولات</b>", "━━━━━━━━━━━━━━━━━━", f"📦 تعداد خریدهای نگهداری‌شده: <b>{total}</b>", ""]
    buttons = []
    if not rows:
        lines.append("هنوز محصولی خریداری نکرده‌اید.")
    else:
        for item in rows:
            lines.append(f"• <b>{escape(item.product_name)}</b> — {int(item.paid_amount):,} تومان")
            buttons.append([_btn(f"📦 {item.product_name[:34]}", _uid_cb(user_id, "bagitem", item.id, page))])
    nav = []
    if page > 1:
        nav.append(_btn("◀️ قبلی", _uid_cb(user_id, "bag", page - 1)))
    nav.append(_btn(f"{page}/{pages}", _uid_cb(user_id, "noop")))
    if page < pages:
        nav.append(_btn("بعدی ▶️", _uid_cb(user_id, "bag", page + 1)))
    if nav:
        buttons.append(nav)
    text = "\n".join(lines)
    markup = _markup(buttons)
    if reply:
        sent = await message_or_query.reply_text(text, parse_mode="HTML", reply_markup=markup)
        from services.panel_security import register_panel
        register_panel(sent.chat_id, sent.message_id, user_id)
    else:
        await message_or_query.answer()
        await _edit(message_or_query, text, markup)
        _register(message_or_query)


async def _user_home(query, uid, session):
    catalog = _catalog(session)
    if not catalog.get("enabled", True):
        await query.answer("🔴 فروشگاه محصولات فعلاً غیرفعال است.", show_alert=True)
        return
    wallet = ensure_wallet(session, uid)
    text = ("🛍️ <b>فروشگاه محصولات</b>\n━━━━━━━━━━━━━━━━━━\n"
            f"👛 موجودی کیف پول: <b>{format_amount(wallet.balance)} تومان</b>\n\n"
            "محصول موردنظر را انتخاب کنید. خریدها ابتدا به کیف محصولات اضافه می‌شوند.")
    await _edit(query, text, _user_keyboard(uid)); _register(query)


def _user_category_keyboard(uid, category, data, session):
    rows = []
    if category == "resources":
        resource_buttons = [
            _btn(RESOURCE_LABELS[key], _uid_cb(uid, "item", "resources", key))
            for key in RESOURCE_ORDER
        ]
        rows.extend([resource_buttons[i:i + 2] for i in range(0, len(resource_buttons), 2)])
    elif category in {"population", "leadership"}:
        conf = data[category]
        has_plans = any(p.get("enabled", True) and int(p.get("price", 0) or 0) > 0 for p in conf.get("plans", []))
        if conf.get("enabled") and (int(conf.get("unit_price", 0) or 0) > 0 or has_plans):
            rows.append([_btn(CATEGORY_LABELS[category], _uid_cb(uid, "item", category, "main"))])
    elif category == "shields":
        for key, label in SHIELD_LABELS.items():
            conf = data["shields"].get(key, {})
            has_plans = any(p.get("enabled", True) and int(p.get("price", 0) or 0) > 0 for p in conf.get("plans", []))
            if conf.get("enabled") and (int(conf.get("unit_price", 0) or 0) > 0 or has_plans):
                rows.append([_btn(label, _uid_cb(uid, "item", "shields", key))])
    elif category == "missiles":
        mcfg = get_missiles_config(session)
        for missile in mcfg.get("items", []):
            if not missile.get("active"):
                continue
            mid = str(missile.get("id"))
            conf = data.get("missiles", {}).get(mid, {})
            level_configs = conf.get("levels", {}) if isinstance(conf.get("levels"), dict) else {}
            has_sale_level = any(
                level_conf.get("enabled") and (
                    int(level_conf.get("unit_price", 0) or 0) > 0
                    or any(p.get("enabled", True) and int(p.get("price", 0) or 0) > 0 for p in level_conf.get("plans", []))
                )
                for level_conf in level_configs.values() if isinstance(level_conf, dict)
            )
            if conf.get("enabled") and has_sale_level:
                rows.append([_btn(str(missile.get("name") or "موشک")[:48], _uid_cb(uid, "item", "missiles", mid))])
    elif category == "teams":
        team_cfg = get_construction_teams_config(session)
        for number in range(2, max(1, min(10, int(team_cfg.get("max_teams", 10) or 10))) + 1):
            conf = data.get("teams", {}).get(str(number), {})
            if conf.get("enabled") and int(conf.get("price", 0) or 0) > 0:
                rows.append([_btn(f"🏗️ تیم ساخت‌وساز {number} — {int(conf.get('price', 0)):,.0f} تومان", _uid_cb(uid, "team", number))])
    elif category in {"bundles", "events"}:
        kind = "bundle" if category == "bundles" else "event"
        for product in data.get("custom_products", []):
            if product.get("kind") == kind and product.get("enabled", True) and int(product.get("price", 0) or 0) > 0:
                rows.append([_btn(f"{product.get('name', 'محصول')[:40]} — {int(product.get('price', 0) or 0):,} تومان", _uid_cb(uid, "custom_product", product.get("id")))])
    rows.append([_btn("🔙 برگشت به فروشگاه", _uid_cb(uid, "home"), "danger")])
    return _markup(rows)


def _user_category_disabled(data, category, session):
    if category == "resources":
        return not any(bool(data.get("resources", {}).get(key, {}).get("enabled")) for key in RESOURCE_ORDER)
    if category in {"population", "leadership"}:
        return not bool(data.get(category, {}).get("enabled"))
    if category == "shields":
        return not any(bool(data.get("shields", {}).get(key, {}).get("enabled")) for key in SHIELD_LABELS)
    if category == "missiles":
        active_ids = {
            str(m.get("id")) for m in get_missiles_config(session).get("items", [])
            if m.get("active") and m.get("id") is not None
        }
        missile_sales = data.get("missiles", {}) or {}
        return not any(
            bool(missile_sales.get(mid, {}).get("enabled")) and any(
                bool(lc.get("enabled")) and (
                    int(lc.get("unit_price", 0) or 0) > 0
                    or any(p.get("enabled", True) and int(p.get("price", 0) or 0) > 0 for p in lc.get("plans", []))
                )
                for lc in (missile_sales.get(mid, {}).get("levels", {}) or {}).values() if isinstance(lc, dict)
            )
            for mid in active_ids
        )
    if category == "teams":
        team_cfg = get_construction_teams_config(session)
        max_teams = max(1, min(10, int(team_cfg.get("max_teams", 10) or 10)))
        team_sales = data.get("teams", {}) or {}
        return not any(bool(team_sales.get(str(number), {}).get("enabled")) for number in range(2, max_teams + 1))
    if category in {"bundles", "events"}:
        kind = "bundle" if category == "bundles" else "event"
        return not any(
            p.get("kind") == kind and bool(p.get("enabled", True))
            and int(p.get("price", 0) or 0) > 0
            for p in data.get("custom_products", [])
        )
    return False


async def _show_user_category(query, uid, category, session, *, answer=True):
    data = _catalog(session)
    if _user_category_disabled(data, category, session):
        await query.answer("این بخش غیرفعال است.", show_alert=True)
        return
    title = CATEGORY_LABELS.get(category, "فروشگاه")
    keyboard = _user_category_keyboard(uid, category, data, session)
    if answer:
        await query.answer()
    await _edit(query, f"🛍️ <b>{escape(title)}</b>\n\nمحصول موردنظر را انتخاب کنید.", keyboard)
    _register(query)


def _get_config(data, category, key):
    if category == "resources":
        return data["resources"].get(str(key))
    if category in {"population", "leadership"}:
        return data.get(category)
    if category == "shields":
        return data["shields"].get(str(key))
    if category == "missiles":
        return data.get("missiles", {}).get(str(key))
    if category == "missile_level":
        try:
            missile_id, level = str(key).rsplit("@", 1)
            missile = data.get("missiles", {}).get(missile_id, {})
            return (missile.get("levels") or {}).get(str(int(level)))
        except (ValueError, TypeError):
            return None
    if category == "teams":
        return data.get("teams", {}).get(str(key))
    return None


def _missile_level_parent_enabled(data, key, session):
    """A level is sellable only while both its missile and the missile itself are enabled."""
    try:
        missile_id, _level = str(key).rsplit("@", 1)
    except ValueError:
        return False
    parent = (data.get("missiles", {}) or {}).get(str(missile_id), {})
    if not isinstance(parent, dict) or not parent.get("enabled"):
        return False
    missile = next(
        (m for m in get_missiles_config(session).get("items", [])
         if str(m.get("id")) == str(missile_id)),
        None,
    )
    return bool(missile and missile.get("active"))


def _get_config_title(category, key, session):
    if category == "resources":
        return RESOURCE_LABELS.get(str(key), "منبع")
    if category == "population":
        return "👥 شهروند"
    if category == "leadership":
        return "👑 تجربه رهبری"
    if category == "shields":
        return SHIELD_LABELS.get(str(key), "سپر")
    if category in {"missiles", "missile_level"}:
        raw_key = str(key)
        missile_id, level = (raw_key.rsplit("@", 1) if category == "missile_level" and "@" in raw_key else (raw_key, None))
        missile = next((m for m in get_missiles_config(session).get("items", []) if str(m.get("id")) == missile_id), None)
        if not missile:
            return "🚀 موشک حذف‌شده"
        suffix = f" — سطح {int(level)}" if level is not None else ""
        return f"🚀 {missile.get('name', 'موشک')}{suffix}"
    if category == "teams":
        return f"🏗️ تیم ساخت‌وساز {key}"
    return "محصول"


def _set_value(data, category, key, field, value):
    conf = _get_config(data, category, key)
    if conf is None:
        raise ValueError("config not found")
    if field in {"unit_amount", "min", "max"}:
        conf[field] = value
    elif field in {"unit_price", "price"}:
        conf[field] = value
    else:
        raise ValueError("field not allowed")


def _find_plan(conf, plan_id):
    return next((p for p in conf.get("plans", []) if str(p.get("id")) == str(plan_id)), None)


def _find_custom(data, product_id):
    return next((p for p in data.get("custom_products", []) if str(p.get("id")) == str(product_id)), None)


def _owner_config_view(query, data, category, key, session):
    conf = _get_config(data, category, key)
    if conf is None:
        return None
    title = _get_config_title(category, key, session)
    return _config_text(category, key, conf, title), _config_keyboard(category, key, conf)


def _component_selector_keyboard(session):
    rows = [
        [_btn("💰 منابع", _owner_cb("comp_category", "resource")), _btn("👥 شهروند", _owner_cb("comp_category", "population"))],
        [_btn("👑 تجربه رهبری", _owner_cb("comp_category", "leadership")), _btn("🛡️ سپر", _owner_cb("comp_category", "shield"))],
        [_btn("🚀 موشک", _owner_cb("comp_category", "missile")), _btn("🏗️ تیم ساخت‌وساز", _owner_cb("comp_category", "team"))],
        [_btn("🔙 برگشت به بسته", _owner_cb("builder"), "danger")],
    ]
    return _markup(rows)


def _component_target_keyboard(kind, session, edit_index=None):
    rows = []
    if kind == "resource":
        rows.extend([
            [_btn(RESOURCE_LABELS["money"], _owner_cb("comp_select", "resource", "money")),
             _btn(RESOURCE_LABELS["metal"], _owner_cb("comp_select", "resource", "metal"))],
            [_btn(RESOURCE_LABELS["fuel"], _owner_cb("comp_select", "resource", "fuel")),
             _btn(RESOURCE_LABELS["uranium"], _owner_cb("comp_select", "resource", "uranium"))],
        ])
    elif kind == "shield":
        rows.append([
            _btn(SHIELD_LABELS["global"], _owner_cb("comp_select", "shield", "global")),
            _btn(SHIELD_LABELS["continental"], _owner_cb("comp_select", "shield", "continental")),
        ])
    elif kind == "missile":
        for missile in get_missiles_config(session).get("items", []):
            if missile.get("active"):
                rows.append([_btn(str(missile.get("name", "موشک"))[:45], _owner_cb("comp_select", "missile", missile.get("id")))])
    elif kind == "team":
        team_cfg = get_construction_teams_config(session)
        max_teams = max(1, min(10, int(team_cfg.get("max_teams", 10) or 10)))
        team_buttons = []
        for number in range(2, max_teams + 1):
            callback = (_owner_cb("comp_edit_team", edit_index, number)
                        if edit_index is not None else _owner_cb("comp_select", "team", number))
            team_buttons.append(_btn(f"🏗️ تیم {number}", callback))
        rows.extend([team_buttons[i:i + 2] for i in range(0, len(team_buttons), 2)])
    elif kind in {"population", "leadership"}:
        rows.append([_btn("➡️ ادامه", _owner_cb("comp_select", kind, "main"), "success")])
    back_callback = _owner_cb("components_list") if edit_index is not None else _owner_cb("add_comp")
    rows.append([_btn("🔙 برگشت", back_callback, "danger")])
    return _markup(rows)


def _owner_home_text(data):
    return ("🛍️ <b>مدیریت محصولات فروشگاه</b>\n━━━━━━━━━━━━━━━━━━\n"
            f"وضعیت فروشگاه: <b>{'فعال' if data.get('enabled', True) else 'غیرفعال'}</b>\n\n"
            "از این بخش می‌توانید قیمت‌گذاری منابع، شهروند، تجربه رهبری، سپر، موشک‌ها و تیم‌های ساخت‌وساز را مدیریت کنید و بسته‌های ترکیبی یا مناسبتی بسازید.\n\n"
            "محصولات مناسبتی مانند بسته ترکیبی ساخته می‌شوند و تاریخ شروع یا پایان ندارند.")


async def _owner_home(query, session):
    global _catalog_enabled_cache
    data = _catalog(session)
    _catalog_enabled_cache = bool(data.get("enabled", True))
    await _edit(query, _owner_home_text(data), _owner_keyboard())
    _register(query)


async def _owner_category(query, session, category):
    data = _catalog(session)
    if category in {"population", "leadership"}:
        # ورود مستقیم به پنل اصلی؛ این دو محصول در حالت اولیه غیرفعال هستند.
        await _owner_config(query, session, category, "main")
        return
    title = CATEGORY_LABELS.get(category, "مدیریت محصولات")
    intro = f"🛍️ <b>{escape(title)}</b>\n\nمحصول یا موردی را که می‌خواهید قیمت‌گذاری یا مدیریت کنید، انتخاب کنید."
    if category in {"bundles", "events"}:
        intro += "\n\n" + ("بسته‌های ترکیبی بدون محدودیت زمانی ساخته می‌شوند." if category == "bundles" else "محصولات مناسبتی دقیقاً مانند بسته‌های ترکیبی هستند و زمان‌بندی ندارند.")
    await _edit(query, intro, _category_owner_keyboard(category, data, session))
    _register(query)


async def _owner_config(query, session, category, key):
    data = _catalog(session)
    view = _owner_config_view(query, data, category, key, session)
    if view is None:
        await query.answer("❌ مورد موردنظر پیدا نشد.", show_alert=True)
        return
    await _edit(query, *view)
    _register(query)


async def _owner_plans(query, session, category, key, page=1, delete_mode=False):
    data = _catalog(session)
    conf = _get_config(data, category, key)
    if conf is None:
        await query.answer("❌ تنظیمات محصول پیدا نشد.", show_alert=True)
        return
    plans = list(conf.get("plans", []))
    title = _get_config_title(category, key, session)
    per_page = 5
    total_pages = max(1, (len(plans) + per_page - 1) // per_page)
    page = max(1, min(int(page or 1), total_pages))
    if delete_mode:
        if not plans:
            # پس از حذف آخرین پلن، کاربر باید به مدیریت پلن‌ها برگردد.
            await _edit(query, _plan_management_text(category, key, conf, title), _plan_management_keyboard(category, key, conf))
        else:
            start = (page - 1) * per_page
            lines = [
                f"🗑 <b>حذف پلن‌های {escape(title)}</b>",
                "━━━━━━━━━━━━━━━━━━",
                f"تعداد پلن‌ها: <b>{len(plans)}</b>",
                f"صفحه: <b>{page}/{total_pages}</b>",
                "",
                "برای حذف، پلن موردنظر را انتخاب کنید:",
            ]
            for index, plan in enumerate(plans[start:start + per_page], start + 1):
                lines.append(f"{index}. {escape(str(plan.get('name') or 'پلن'))}")
            await _edit(query, "\n".join(lines), _plan_list_keyboard(category, key, conf, page, True))
    else:
        await _edit(query, _plan_management_text(category, key, conf, title), _plan_management_keyboard(category, key, conf))
    _register(query)


async def _owner_plan_browse(query, session, category, key, page=1):
    data = _catalog(session)
    conf = _get_config(data, category, key)
    if conf is None:
        await query.answer("❌ تنظیمات محصول پیدا نشد.", show_alert=True)
        return
    plans = list(conf.get("plans", []))
    if not plans:
        return
    per_page = 5
    total_pages = max(1, (len(plans) + per_page - 1) // per_page)
    page = max(1, min(int(page or 1), total_pages))
    title = _get_config_title(category, key, session)
    start = (page - 1) * per_page
    lines = [
        f"📋 <b>لیست پلن‌های {escape(title)}</b>",
        "━━━━━━━━━━━━━━━━━━",
        f"تعداد کل پلن‌ها: <b>{len(plans)}</b>",
        f"صفحه: <b>{page}/{total_pages}</b>",
        "",
        "برای مشاهده جزئیات، یک پلن را انتخاب کنید:",
    ]
    for index, plan in enumerate(plans[start:start + per_page], start + 1):
        lines.append(f"{index}. {escape(str(plan.get('name') or 'پلن'))} — {int(plan.get('amount', 0) or 0):,} — {int(plan.get('price', 0) or 0):,} تومان")
    await _edit(query, "\n".join(lines), _plan_list_keyboard(category, key, conf, page, False))
    _register(query)


async def _owner_plan_detail(query, session, category, key, plan_id, page=1):
    data = _catalog(session)
    conf = _get_config(data, category, key)
    plan = _find_plan(conf or {}, plan_id)
    if not plan:
        return
    title = _get_config_title(category, key, session)
    await _edit(query, _plan_text(conf, plan, title), _plan_detail_keyboard(category, key, plan, page))
    _register(query)


async def _owner_plan_delete_confirm(query, session, category, key, plan_id, page=1):
    data = _catalog(session)
    conf = _get_config(data, category, key)
    plan = _find_plan(conf or {}, plan_id)
    if not plan:
        return
    text = ("🗑 <b>تأیید حذف پلن</b>\n\n"
            f"پلن: <b>{escape(str(plan.get('name') or 'پلن'))}</b>\n"
            f"مقدار: <b>{int(plan.get('amount', 0) or 0):,}</b>\n"
            f"قیمت: <b>{int(plan.get('price', 0) or 0):,} تومان</b>\n\n"
            "آیا از حذف این پلن مطمئن هستید؟")
    markup = _markup([
        [_btn("✅ بله، حذف شود", _owner_cb("plan_delete_yes", category, key, plan_id, page), "danger")],
        [_btn("❌ انصراف", _owner_cb("plan_delete_mode", category, key, page), "primary")],
    ])
    await _edit(query, text, markup)
    _register(query)


async def _owner_custom_detail(query, session, product_id):
    data = _catalog(session)
    product = _find_custom(data, product_id)
    if not product:
        await query.answer("❌ محصول پیدا نشد.", show_alert=True)
        return
    kind_label = "محصول ترکیبی" if product.get("kind") == "bundle" else "محصول مناسبتی"
    lines = [f"🛍️ <b>{escape(kind_label)}</b>", f"📦 نام: <b>{escape(str(product.get('name', '')))}</b>",
             f"💎 قیمت واقعی محصولات: <b>{int(product.get('original_price', 0) or 0):,} تومان</b>",
             f"🎁 قیمت بسته: <b>{int(product.get('price', 0) or 0):,} تومان</b>",
             f"وضعیت: <b>{'فعال' if product.get('enabled', True) else 'غیرفعال'}</b>", "",
             f"📝 توضیحات: {escape(str(product.get('description') or 'ثبت نشده'))}", "",
             "<b>محتویات:</b>"]
    if product.get("components"):
        lines.extend(f"• {escape(_component_label(c))}" for c in product["components"])
    else:
        lines.append("محتویاتی ثبت نشده است.")
    await _edit(query, "\n".join(lines), _custom_detail_keyboard(product))
    _register(query)


def _start_input(context, state, query, prompt, back_callback=None):
    state["chat_id"] = int(query.message.chat_id)
    state["panel_message_id"] = int(query.message.message_id)
    context.user_data["robot_store_state"] = state
    rows = []
    if back_callback:
        rows.append([_btn("🔙 برگشت", back_callback, "danger")])
    return prompt, _markup(rows) if rows else None


async def _show_custom_builder(query, product, *, is_new):
    await _edit(query, _custom_components_text(product), _custom_builder_keyboard(product, is_new=is_new))
    _register(query)


def _component_list_keyboard(product):
    rows = []
    components = list(product.get("components", []))
    for index, component in enumerate(components):
        rows.append([_btn(f"{index + 1}. {_component_label(component)[:48]}", _owner_cb("comp_manage", index))])
    rows.append([_btn("🔙 برگشت به بسته", _owner_cb("builder"), "danger")])
    return _markup(rows)


async def _show_component_list(query, product):
    components = list(product.get("components", []))
    if not components:
        await query.answer("📭 هنوز محصولی به این بسته اضافه نشده است.", show_alert=True)
        return
    text = "📋 <b>لیست محصولات داخل بسته</b>\n━━━━━━━━━━━━━━━━━━\nبرای ویرایش یا حذف، مورد را انتخاب کنید:"
    await query.answer()
    await _edit(query, text, _component_list_keyboard(product))
    _register(query)


async def _show_component_manage(query, product, index):
    components = list(product.get("components", []))
    if index < 0 or index >= len(components):
        await query.answer("❌ این مورد پیدا نشد.", show_alert=True)
        return
    component = components[index]
    text = ("🧩 <b>مدیریت محصول داخل بسته</b>\n━━━━━━━━━━━━━━━━━━\n"
            f"{escape(_component_label(component))}\n\nیکی از عملیات زیر را انتخاب کنید:")
    markup = _markup([
        [_btn("✏️ ویرایش مقدار / نوع", _owner_cb("comp_edit", index), "primary")],
        [_btn("🗑 حذف از بسته", _owner_cb("comp_delete", index), "danger")],
        [_btn("🔙 برگشت به لیست", _owner_cb("components_list"), "danger")],
    ])
    await query.answer()
    await _edit(query, text, markup)
    _register(query)


def _new_product_id():
    return uuid.uuid4().hex[:12]


async def _owner_history_page(query, session, page=1):
    from sqlalchemy import func
    page = max(1, int(page or 1))
    per_page = 10
    total = int(session.scalar(select(func.count(ProductInventory.id))) or 0)
    if total == 0:
        await query.answer("📭 تاریخچه فروش خالی است.", show_alert=True)
        return
    pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, pages)
    rows = list(session.scalars(select(ProductInventory).order_by(ProductInventory.created_at.desc(), ProductInventory.id.desc()).offset((page - 1) * per_page).limit(per_page)).all())
    await query.answer()
    lines = ["📜 <b>تاریخچه فروش فروشگاه محصولات</b>", "━━━━━━━━━━━━━━━━━━", f"تعداد کل خریدها: <b>{total}</b>", ""]
    buttons = []
    if not rows:
        lines.append("هنوز خریدی از فروشگاه ثبت نشده است.")
    else:
        for item in rows:
            buyer = session.scalar(select(User).where(User.telegram_id == int(item.user_id)))
            buyer_name = (buyer.first_name or buyer.username or str(item.user_id)) if buyer else str(item.user_id)
            lines.append(f"• {escape(item.product_name)} — {int(item.paid_amount):,} تومان | {escape(str(buyer_name))}")
            buttons.append([_btn(f"📦 {item.product_name[:24]} — {int(item.paid_amount):,}", _owner_cb("sale", item.id, page))])
    nav = []
    if page > 1:
        nav.append(_btn("◀️ قبلی", _owner_cb("history", page - 1)))
    nav.append(_btn(f"{page}/{pages}", _owner_cb("noop")))
    if page < pages:
        nav.append(_btn("بعدی ▶️", _owner_cb("history", page + 1)))
    if nav:
        buttons.append(nav)
    buttons.append([_btn("🔙 برگشت", _owner_cb("home"), "danger")])
    await _edit(query, "\n".join(lines), _markup(buttons))
    _register(query)


async def _owner_sale_detail(query, session, sale_id, back_page=1):
    item = session.get(ProductInventory, int(sale_id))
    if item is None:
        await query.answer("❌ خرید پیدا نشد.", show_alert=True); return
    buyer = session.scalar(select(User).where(User.telegram_id == int(item.user_id)))
    buyer_name = buyer.first_name if buyer and buyer.first_name else (buyer.username if buyer and buyer.username else "بدون نام")
    try:
        payload = json.loads(item.payload_json or "{}")
    except Exception:
        payload = {}
    created = item.created_at.strftime("%Y/%m/%d — %H:%M") if item.created_at else "ثبت نشده"
    text = ("📜 <b>جزئیات فروش</b>\n━━━━━━━━━━━━━━━━━━\n"
            f"📦 محصول: <b>{escape(item.product_name)}</b>\n"
            f"👤 خریدار: <b>{escape(str(buyer_name))}</b>\n"
            f"🆔 آیدی تلگرام: <code>{int(item.user_id)}</code>\n"
            f"💰 مبلغ پرداختی: <b>{int(item.paid_amount):,} تومان</b>\n"
            f"📅 تاریخ: <b>{created}</b>\n"
            f"📌 وضعیت: <b>{escape(item.status)}</b>\n\n"
            f"<b>محتویات محصول:</b>\n{_format_payload(payload)}")
    await _edit(query, text, _markup([[_btn("🔙 برگشت به تاریخچه", _owner_cb("history", back_page), "danger")]]))
    _register(query)


async def _owner_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, query, data: str, session):
    parts = data.split(":")
    action = parts[2] if len(parts) > 2 else ""
    if int(query.from_user.id) != int(OWNER_ID):
        await query.answer("⛔ فقط مالک ربات به مدیریت فروشگاه دسترسی دارد.", show_alert=True)
        return
    if action not in {"custom_no_description", "custom_back_name", "custom_back_description", "plan_add_back"}:
        context.user_data.pop("robot_store_state", None)
    catalog = _catalog(session)

    if action == "noop":
        await query.answer("ℹ️ موردی برای نمایش وجود ندارد.", show_alert=True)
        return
    if action == "history" and len(parts) >= 4:
        await _owner_history_page(query, session, parts[3]); return
    if action == "sale" and len(parts) >= 4:
        back_page = parts[4] if len(parts) >= 5 else 1
        await query.answer(); await _owner_sale_detail(query, session, parts[3], back_page); return
    if action == "home":
        context.user_data.pop("robot_store_state", None)
        context.user_data.pop("robot_store_draft", None)
        await query.answer()
        await _owner_home(query, session)
        return
    if action == "toggle_store":
        catalog["enabled"] = not bool(catalog.get("enabled", True))
        _save_catalog(session, catalog)
        await query.answer("وضعیت فروشگاه تغییر کرد.", show_alert=True)
        await _owner_home(query, session)
        return
    if action == "category" and len(parts) >= 4:
        context.user_data.pop("robot_store_state", None)
        context.user_data.pop("robot_store_draft", None)
        await query.answer()
        await _owner_category(query, session, parts[3])
        return
    if action == "missile_type" and len(parts) >= 4:
        missile_type = parts[3]
        if missile_type not in {"کروز", "بالستیک", "هایپرسونیک"}:
            await query.answer("❌ دسته‌بندی موشک معتبر نیست.", show_alert=True)
            return
        items = [m for m in get_missiles_config(session).get("items", [])
                 if str(m.get("type", "")).strip() == missile_type and str(m.get("id", "")).strip()]
        if not items:
            await query.answer("❌ هیچ موشکی در این دسته وجود ندارد.", show_alert=True)
            return
        await query.answer()
        await _edit(query, f"🚀 <b>مدیریت موشک‌های {escape(missile_type)}</b>\n\nموشک موردنظر را برای تنظیم انتخاب کنید:", _owner_missile_type_keyboard(missile_type, catalog, session))
        _register(query)
        return
    if action == "missile_levels" and len(parts) >= 4:
        missile_id = str(parts[3])
        missile = next((m for m in get_missiles_config(session).get("items", []) if str(m.get("id")) == missile_id), None)
        if not missile:
            await query.answer("❌ موشک پیدا نشد.", show_alert=True)
            return
        await query.answer()
        await _edit(query, f"🚀 <b>تنظیم سطوح {escape(str(missile.get('name') or 'موشک'))}</b>\n\nابتدا وضعیت فروش موشک را مشخص کنید؛ سپس سطح موردنظر را انتخاب کنید.", _owner_missile_levels_keyboard(missile, catalog))
        _register(query)
        return
    if action == "missile_toggle" and len(parts) >= 4:
        missile_id = str(parts[3])
        missile = next((m for m in get_missiles_config(session).get("items", []) if str(m.get("id")) == missile_id), None)
        conf = catalog.get("missiles", {}).get(missile_id)
        if not missile or not isinstance(conf, dict):
            await query.answer("❌ موشک پیدا نشد.", show_alert=True)
            return
        conf["enabled"] = not bool(conf.get("enabled", False))
        _save_catalog(session, catalog)
        await query.answer("وضعیت فروش موشک تغییر کرد.", show_alert=True)
        await _edit(query, f"🚀 <b>تنظیم سطوح {escape(str(missile.get('name') or 'موشک'))}</b>\n\nسطح موردنظر را انتخاب کنید.", _owner_missile_levels_keyboard(missile, catalog))
        _register(query)
        return
    if action == "missile_level" and len(parts) >= 5:
        missile_id = str(parts[3])
        try:
            level = int(parts[4])
        except (TypeError, ValueError):
            await query.answer("❌ سطح موشک معتبر نیست.", show_alert=True)
            return
        missile = next((m for m in get_missiles_config(session).get("items", []) if str(m.get("id")) == missile_id), None)
        if not missile or level < 1 or level > int(missile.get("max_level", 1) or 1):
            await query.answer("❌ سطح موشک پیدا نشد.", show_alert=True)
            return
        await query.answer()
        await _owner_config(query, session, "missile_level", f"{missile_id}@{level}")
        return
    if action == "cfg" and len(parts) >= 5:
        await query.answer()
        await _owner_config(query, session, parts[3], parts[4])
        return
    if action == "toggle" and len(parts) >= 5:
        category, key = parts[3], parts[4]
        conf = _get_config(catalog, category, key)
        if conf is None:
            await query.answer("❌ مورد پیدا نشد.", show_alert=True); return
        conf["enabled"] = not bool(conf.get("enabled"))
        _save_catalog(session, catalog)
        await query.answer("وضعیت فروش تغییر کرد.", show_alert=True)
        await _owner_config(query, session, category, key)
        return
    if action == "set" and len(parts) >= 6:
        category, key, field = parts[3], parts[4], parts[5]
        conf = _get_config(catalog, category, key)
        if conf is None:
            await query.answer("❌ مورد پیدا نشد.", show_alert=True); return
        labels = {"unit_amount": "مقدار واحد قیمت‌گذاری", "unit_price": "قیمت به تومان", "min": "حداقل خرید", "max": "حداکثر خرید (۰ یعنی بدون سقف)", "price": "قیمت تیم به تومان"}
        current = conf.get(field, 0)
        prompt = (f"✏️ <b>{escape(labels.get(field, field))}</b>\n\nمقدار فعلی: <b>{current}</b>\n\nمقدار جدید را به‌صورت عدد مثبت ارسال کنید. برای حداکثر خرید، عدد ۰ یعنی بدون سقف.")
        state = {"mode": "config_value", "category": category, "key": key, "field": field}
        prompt, markup = _start_input(context, state, query, prompt, _owner_cb("cfg", category, key))
        await query.answer(); await _edit(query, prompt, markup); _register(query)
        return
    if action == "plans" and len(parts) >= 5:
        page = int(parts[5]) if len(parts) >= 6 else 1
        await query.answer(); await _owner_plans(query, session, parts[3], parts[4], page, False); return
    if action == "plan_list" and len(parts) >= 5:
        page = int(parts[5]) if len(parts) >= 6 else 1
        conf = _get_config(catalog, parts[3], parts[4])
        if not conf or not conf.get("plans"):
            await query.answer("📭 هیچ پلنی موجود نیست.", show_alert=True)
            return
        await query.answer(); await _owner_plan_browse(query, session, parts[3], parts[4], page); return
    if action == "plan_delete_mode" and len(parts) >= 6:
        conf = _get_config(catalog, parts[3], parts[4])
        if not conf or not conf.get("plans"):
            await query.answer("📭 هیچ پلنی برای حذف وجود ندارد.", show_alert=True); return
        await query.answer(); await _owner_plans(query, session, parts[3], parts[4], int(parts[5]), True); return
    if action == "plan_add" and len(parts) >= 5:
        category, key = parts[3], parts[4]
        page = int(parts[5]) if len(parts) >= 6 else 1
        state = {"mode": "plan_add", "step": "name", "category": category, "key": key, "page": page}
        prompt, markup = _start_input(context, state, query,
            "➕ <b>افزودن پلن جدید</b>\n\nنام پلن را ارسال کنید.", _owner_cb("plans", category, key, page))
        await query.answer(); await _edit(query, prompt, markup); _register(query); return
    if action == "plan_add_back" and len(parts) >= 6:
        category, key, target_step = parts[3], parts[4], parts[5]
        page = int(parts[6]) if len(parts) >= 7 else 1
        current = context.user_data.get("robot_store_state") or {}
        if current.get("mode") != "plan_add" or current.get("category") != category or str(current.get("key")) != str(key):
            current = {"mode": "plan_add", "category": category, "key": key, "page": page}
        state = dict(current)
        state.update({"mode": "plan_add", "category": category, "key": key, "page": page, "step": target_step})
        if target_step == "name":
            prompt = "➕ <b>افزودن پلن جدید</b>\n\nنام پلن را ارسال کنید."
            back = _owner_cb("plans", category, key, page)
        elif target_step == "amount":
            unit = "ساعت" if category == "shields" else "واحد/تعداد"
            prompt = f"🔢 <b>مقدار پلن</b>\n\nتعداد {unit} این پلن را ارسال کنید."
            back = _owner_cb("plan_add_back", category, key, "name", page)
        else:
            await query.answer("❌ مرحله نامعتبر است.", show_alert=True)
            return
        prompt, markup = _start_input(context, state, query, prompt, back)
        await query.answer(); await _edit(query, prompt, markup); _register(query); return
    if action == "plan" and len(parts) >= 6:
        page = int(parts[6]) if len(parts) >= 7 else 1
        conf = _get_config(catalog, parts[3], parts[4])
        if not _find_plan(conf or {}, parts[5]):
            await query.answer("❌ پلن پیدا نشد.", show_alert=True); return
        await query.answer(); await _owner_plan_detail(query, session, parts[3], parts[4], parts[5], page); return
    if action == "plan_set" and len(parts) >= 7:
        category, key, pid, field = parts[3], parts[4], parts[5], parts[6]
        page = int(parts[7]) if len(parts) >= 8 else 1
        conf = _get_config(catalog, category, key); plan = _find_plan(conf or {}, pid)
        if not plan:
            await query.answer("❌ پلن پیدا نشد.", show_alert=True); return
        labels = {"name": "نام جدید پلن", "amount": "مقدار جدید پلن", "price": "قیمت جدید پلن"}
        prompt = f"✏️ <b>{labels.get(field, 'ویرایش پلن')}</b>\n\nمقدار فعلی: <b>{escape(str(plan.get(field, '')))}</b>\n\nمقدار جدید را ارسال کنید."
        state = {"mode": "plan_edit", "category": category, "key": key, "plan_id": pid, "field": field, "page": page}
        prompt, markup = _start_input(context, state, query, prompt, _owner_cb("plan", category, key, pid, page))
        await query.answer(); await _edit(query, prompt, markup); _register(query); return
    if action == "plan_toggle" and len(parts) >= 6:
        category, key, pid = parts[3], parts[4], parts[5]
        page = int(parts[6]) if len(parts) >= 7 else 1
        conf = _get_config(catalog, category, key); plan = _find_plan(conf or {}, pid)
        if not plan:
            await query.answer("❌ پلن پیدا نشد.", show_alert=True); return
        plan["enabled"] = not bool(plan.get("enabled", True)); _save_catalog(session, catalog)
        await query.answer("وضعیت پلن تغییر کرد.", show_alert=True); await _owner_plan_detail(query, session, category, key, pid, page); return
    if action == "plan_delete_select" and len(parts) >= 7:
        conf = _get_config(catalog, parts[3], parts[4])
        if not _find_plan(conf or {}, parts[5]):
            await query.answer("❌ پلن پیدا نشد.", show_alert=True); return
        await query.answer()
        await _owner_plan_delete_confirm(query, session, parts[3], parts[4], parts[5], int(parts[6])); return
    if action == "plan_delete" and len(parts) >= 6:
        page = int(parts[6]) if len(parts) >= 7 else 1
        conf = _get_config(catalog, parts[3], parts[4])
        if not _find_plan(conf or {}, parts[5]):
            await query.answer("❌ پلن پیدا نشد.", show_alert=True); return
        await query.answer()
        await _owner_plan_delete_confirm(query, session, parts[3], parts[4], parts[5], page); return
    if action == "plan_delete_yes" and len(parts) >= 7:
        category, key, pid, page = parts[3], parts[4], parts[5], int(parts[6])
        conf = _get_config(catalog, category, key)
        if conf is None or not _find_plan(conf, pid):
            await query.answer("❌ پلن پیدا نشد.", show_alert=True); return
        conf["plans"] = [p for p in conf.get("plans", []) if str(p.get("id")) != str(pid)]
        _save_catalog(session, catalog)
        await query.answer()
        remaining = list(conf.get("plans", []))
        if remaining:
            await _owner_plans(query, session, category, key, page, True)
        else:
            await _owner_plans(query, session, category, key, 1, False)
        return

    # ساخت محصول ترکیبی یا مناسبتی؛ هیچ فیلد زمانی برای این دو نوع وجود ندارد.
    if action == "create" and len(parts) >= 4 and parts[3] in {"bundle", "event"}:
        kind = parts[3]
        context.user_data.pop("robot_store_draft", None)
        state = {"mode": "custom_create", "step": "name", "kind": kind}
        prompt = "📦 <b>ساخت محصول ترکیبی</b>\n\nنام بسته را ارسال کنید." if kind == "bundle" else "🎉 <b>ساخت محصول مناسبتی</b>\n\nنام محصول مناسبتی را ارسال کنید.\n\nاین محصول مانند بسته ترکیبی ساخته می‌شود و زمان‌بندی ندارد."
        prompt, markup = _start_input(context, state, query, prompt, _owner_cb("category", "bundles" if kind == "bundle" else "events"))
        await query.answer(); await _edit(query, prompt, markup); _register(query); return
    if action == "custom_no_description":
        state = context.user_data.get("robot_store_state") or {}
        if state.get("mode") != "custom_create" or state.get("step") != "description":
            await query.answer("این مرحله دیگر فعال نیست.", show_alert=True); return
        draft = context.user_data.get("robot_store_draft")
        if not isinstance(draft, dict):
            draft = {"id": None, "kind": state.get("kind"), "name": state.get("name", "محصول"), "description": "", "price": 0, "original_price": 0, "components": [], "enabled": True, "announce": False}
        draft["description"] = ""
        context.user_data["robot_store_draft"] = draft
        state.update({"mode": "custom_compose", "is_new": True})
        context.user_data["robot_store_state"] = state
        await query.answer()
        await _show_custom_builder(query, draft, is_new=True)
        return
    if action == "custom_back_name":
        state = context.user_data.get("robot_store_state") or {}
        draft = context.user_data.get("robot_store_draft") or {}
        kind = state.get("kind") or draft.get("kind", "bundle")
        state.update({"mode": "custom_create", "step": "name", "kind": kind, "name": draft.get("name", state.get("name", ""))})
        context.user_data["robot_store_state"] = state
        prompt = "✏️ <b>نام محصول</b>\n\nنام فعلی را ویرایش کنید یا همان نام را دوباره ارسال کنید."
        prompt, markup = _start_input(context, state, query, prompt, _owner_cb("category", "bundles" if kind == "bundle" else "events"))
        await query.answer(); await _edit(query, prompt, markup); _register(query); return
    if action == "custom_back_description":
        draft = context.user_data.get("robot_store_draft")
        if not isinstance(draft, dict):
            await query.answer("پیش‌نویس پیدا نشد.", show_alert=True); return
        state = context.user_data.get("robot_store_state") or {}
        state.update({"mode": "custom_create", "step": "description", "kind": draft.get("kind"), "name": draft.get("name")})
        context.user_data["robot_store_state"] = state
        text = "📝 <b>توضیحات محصول</b>\n\nتوضیحات فعلی را ارسال کنید؛ برای خالی کردن توضیحات از دکمه «بدون توضیحات» استفاده کنید."
        markup = _markup([
            [_btn("🚫 بدون توضیحات", _owner_cb("custom_no_description"), "danger")],
            [_btn("🔙 برگشت به نام محصول", _owner_cb("custom_back_name"), "danger")],
        ])
        await query.answer(); await _edit(query, text, markup); _register(query); return
    if action == "custom_set_price":
        product_id = parts[3] if len(parts) >= 4 else None
        draft = context.user_data.get("robot_store_draft")
        return_to_detail = False
        if product_id:
            product = _find_custom(catalog, product_id)
            if not product:
                await query.answer("❌ محصول پیدا نشد.", show_alert=True); return
            draft = dict(product)
            context.user_data["robot_store_draft"] = draft
            return_to_detail = True
        if not isinstance(draft, dict):
            await query.answer("پیش‌نویس محصول پیدا نشد.", show_alert=True); return
        context.user_data["robot_store_state"] = {
            "mode": "custom_compose", "is_new": not bool(draft.get("id")),
            "product_id": draft.get("id"), "return_to_detail": return_to_detail,
            "chat_id": int(query.message.chat_id), "panel_message_id": int(query.message.message_id),
        }
        markup = _markup([
            [_btn("💎 قیمت واقعی محصولات", _owner_cb("custom_price_field", "original_price"), "primary")],
            [_btn("🎁 قیمت نهایی بسته", _owner_cb("custom_price_field", "price"), "success")],
            [_btn("🔙 برگشت", _owner_cb("custom", draft.get("id")) if return_to_detail else _owner_cb("builder"), "danger")],
        ])
        text = (f"💰 <b>تنظیم قیمت‌های {escape(str(draft.get('name') or 'محصول'))}</b>\n\n"
                f"💎 قیمت واقعی محصولات: <b>{int(draft.get('original_price', 0) or 0):,} تومان</b>\n"
                f"🎁 قیمت بسته: <b>{int(draft.get('price', 0) or 0):,} تومان</b>\n\n"
                "ابتدا یکی از قیمت‌ها را انتخاب کنید و مبلغ را به تومان بفرستید.")
        await query.answer(); await _edit(query, text, markup); _register(query); return
    if action == "custom_price_field" and len(parts) >= 4:
        field = parts[3]
        if field not in {"original_price", "price"}:
            await query.answer("❌ نوع قیمت معتبر نیست.", show_alert=True); return
        draft = context.user_data.get("robot_store_draft")
        if not isinstance(draft, dict):
            await query.answer("❌ پیش‌نویس محصول پیدا نشد.", show_alert=True); return
        current = int(draft.get(field, 0) or 0)
        label = "قیمت واقعی مجموع محصولات" if field == "original_price" else "قیمت نهایی بسته"
        state = {
            "mode": "custom_price", "field": field,
            "product_id": draft.get("id"),
            "is_new": not bool(draft.get("id")),
            "return_to_detail": bool(draft.get("id")),
        }
        back_callback = _owner_cb("custom_set_price", draft.get("id")) if draft.get("id") else _owner_cb("custom_set_price")
        prompt, markup = _start_input(context, state, query,
            f"💰 <b>{label}</b>\n\nمبلغ فعلی: <b>{current:,} تومان</b>\nمبلغ جدید را به تومان ارسال کنید.",
            back_callback)
        await query.answer(); await _edit(query, prompt, markup); _register(query); return
    if action == "custom_announce_toggle":
        draft = context.user_data.get("robot_store_draft")
        if not isinstance(draft, dict) or draft.get("kind") != "event":
            await query.answer("این گزینه فقط برای محصولات مناسبتی است.", show_alert=True); return
        draft["announce"] = not bool(draft.get("announce", False))
        context.user_data["robot_store_draft"] = draft
        await query.answer("وضعیت اعلان تغییر کرد.", show_alert=True)
        await _show_custom_builder(query, draft, is_new=not bool(draft.get("id")))
        return
    if action == "custom" and len(parts) >= 4:
        context.user_data.pop("robot_store_state", None); context.user_data.pop("robot_store_draft", None)
        await query.answer(); await _owner_custom_detail(query, session, parts[3]); return
    if action == "custom_toggle" and len(parts) >= 4:
        product = _find_custom(catalog, parts[3])
        if not product:
            await query.answer("❌ محصول پیدا نشد.", show_alert=True); return
        product["enabled"] = not bool(product.get("enabled", True)); _save_catalog(session, catalog)
        await query.answer("وضعیت محصول تغییر کرد.", show_alert=True); await _owner_custom_detail(query, session, parts[3]); return
    if action == "custom_delete" and len(parts) >= 4:
        product = _find_custom(catalog, parts[3])
        if not product:
            await query.answer("❌ محصول پیدا نشد.", show_alert=True); return
        catalog["custom_products"] = [p for p in catalog["custom_products"] if str(p.get("id")) != parts[3]]
        _save_catalog(session, catalog)
        category = "bundles" if product.get("kind") == "bundle" else "events"
        await query.answer("محصول حذف شد.", show_alert=True); await _owner_category(query, session, category); return
    if action == "custom_set" and len(parts) >= 5:
        product_id, field = parts[3], parts[4]
        product = _find_custom(catalog, product_id)
        if not product:
            await query.answer("❌ محصول پیدا نشد.", show_alert=True); return
        label = {"name": "نام جدید", "price": "قیمت جدید به تومان", "description": "توضیحات جدید"}.get(field, "مقدار جدید")
        prompt = f"✏️ <b>{label}</b>\n\nمقدار فعلی: <b>{escape(str(product.get(field, '')))}</b>\n\nمقدار جدید را ارسال کنید."
        state = {"mode": "custom_edit", "product_id": product_id, "field": field}
        prompt, markup = _start_input(context, state, query, prompt, _owner_cb("custom", product_id))
        await query.answer(); await _edit(query, prompt, markup); _register(query); return
    if action == "edit_components" and len(parts) >= 4:
        product = _find_custom(catalog, parts[3])
        if not product:
            await query.answer("❌ محصول پیدا نشد.", show_alert=True); return
        context.user_data["robot_store_draft"] = dict(product)
        context.user_data["robot_store_state"] = {"mode": "custom_compose", "product_id": product["id"], "is_new": False}
        await query.answer(); await _show_custom_builder(query, product, is_new=False); return
    if action == "builder":
        product = context.user_data.get("robot_store_draft")
        if not isinstance(product, dict):
            await query.answer("❌ پیش‌نویس پیدا نشد.", show_alert=True); return
        state = context.user_data.get("robot_store_state") or {}
        state.update({"mode": "custom_compose", "is_new": not bool(product.get("id"))})
        context.user_data["robot_store_state"] = state
        await query.answer(); await _show_custom_builder(query, product, is_new=not bool(product.get("id"))); return
    if action == "add_comp":
        if not isinstance(context.user_data.get("robot_store_draft"), dict):
            await query.answer("❌ ابتدا یک بسته ایجاد کنید.", show_alert=True); return
        await query.answer(); await _edit(query, "➕ <b>افزودن محصول به بسته</b>\n\nنوع محصول را انتخاب کنید:", _component_selector_keyboard(session)); _register(query); return
    if action == "components_list":
        draft = context.user_data.get("robot_store_draft")
        if not isinstance(draft, dict):
            await query.answer("❌ پیش‌نویس بسته پیدا نشد.", show_alert=True); return
        await _show_component_list(query, draft); return
    if action == "comp_manage" and len(parts) >= 4:
        draft = context.user_data.get("robot_store_draft")
        if not isinstance(draft, dict):
            await query.answer("❌ پیش‌نویس بسته پیدا نشد.", show_alert=True); return
        try:
            index = int(parts[3])
        except (TypeError, ValueError):
            await query.answer("❌ شماره محصول معتبر نیست.", show_alert=True); return
        await _show_component_manage(query, draft, index); return
    if action == "comp_delete" and len(parts) >= 4:
        draft = context.user_data.get("robot_store_draft")
        try:
            index = int(parts[3])
            if not isinstance(draft, dict) or index < 0 or index >= len(draft.get("components", [])):
                raise ValueError
            draft["components"].pop(index)
            context.user_data["robot_store_draft"] = draft
            await query.answer("✅ محصول از بسته حذف شد.", show_alert=True)
            if draft.get("components"):
                text = "📋 <b>لیست محصولات داخل بسته</b>\n━━━━━━━━━━━━━━━━━━\nبرای ویرایش یا حذف، مورد را انتخاب کنید:"
                await _edit(query, text, _component_list_keyboard(draft))
                _register(query)
            else:
                await _edit(query, _custom_components_text(draft), _custom_builder_keyboard(draft, is_new=not bool(draft.get("id"))))
                _register(query)
        except (TypeError, ValueError):
            await query.answer("❌ محصول معتبر نیست.", show_alert=True)
        return
    if action == "comp_edit" and len(parts) >= 4:
        draft = context.user_data.get("robot_store_draft")
        try:
            index = int(parts[3])
            comp = draft.get("components", [])[index]
            if not isinstance(draft, dict):
                raise ValueError
        except (TypeError, ValueError, IndexError, AttributeError):
            await query.answer("❌ محصول معتبر نیست.", show_alert=True); return
        kind = comp.get("kind")
        if kind == "team":
            await query.answer()
            await _edit(query, "🏗️ <b>تغییر تیم ساخت‌وساز</b>\n\nتیم جدید را انتخاب کنید:", _component_target_keyboard("team", session, edit_index=index))
            _register(query)
            return
        selection = {key: value for key, value in comp.items() if key != "amount" and key != "hours" and key != "quantity"}
        label = {"resource": "مقدار منبع", "population": "مقدار شهروند", "leadership": "مقدار تجربه رهبری", "shield": "مدت سپر به ساعت", "missile": "تعداد موشک"}.get(kind)
        if not label:
            await query.answer("❌ ویرایش این نوع محصول پشتیبانی نمی‌شود.", show_alert=True); return
        state = {"mode": "component_edit_amount", "selection": selection, "component_index": index}
        await query.answer()
        prompt, markup = _start_input(context, state, query, f"✏️ <b>ویرایش {label}</b>\n\nمقدار جدید را ارسال کنید.", _owner_cb("comp_manage", index))
        await _edit(query, prompt, markup); _register(query); return
    if action == "comp_edit_team" and len(parts) >= 5:
        draft = context.user_data.get("robot_store_draft")
        try:
            if not isinstance(draft, dict):
                raise ValueError
            index, number = int(parts[3]), int(parts[4])
            comp = draft.get("components", [])[index]
            if comp.get("kind") != "team":
                raise ValueError
            comp["team_number"] = number
            context.user_data["robot_store_draft"] = draft
            await query.answer("✅ تیم تغییر کرد.", show_alert=True)
            if draft.get("components"):
                await _edit(query, "📋 <b>لیست محصولات داخل بسته</b>\n━━━━━━━━━━━━━━━━━━\nبرای ویرایش یا حذف، مورد را انتخاب کنید:", _component_list_keyboard(draft))
            else:
                await _edit(query, _custom_components_text(draft), _custom_builder_keyboard(draft, is_new=not bool(draft.get("id"))))
            _register(query)
        except (TypeError, ValueError, IndexError, AttributeError):
            await query.answer("❌ انتخاب تیم معتبر نیست.", show_alert=True)
        return
    if action == "comp_category" and len(parts) >= 4:
        kind = parts[3]
        if kind not in {"resource", "population", "leadership", "shield", "missile", "team"}:
            await query.answer("❌ نوع محصول نامعتبر است.", show_alert=True); return
        await query.answer(); await _edit(query, "نوع دقیق محصول را انتخاب کنید:", _component_target_keyboard(kind, session)); _register(query); return
    if action == "comp_select" and len(parts) >= 5:
        kind, key = parts[3], parts[4]
        selection = {"kind": kind}
        prompt_label = "مقدار" 
        if kind == "resource":
            selection["resource"] = key; prompt_label = f"مقدار {RESOURCE_LABELS.get(key, key)}"
        elif kind == "shield":
            selection["shield_type"] = key; prompt_label = "مدت سپر به ساعت"
        elif kind == "missile":
            missile = next((m for m in get_missiles_config(session).get("items", []) if str(m.get("id")) == str(key)), None)
            if not missile:
                await query.answer("❌ موشک پیدا نشد.", show_alert=True); return
            selection.update({"missile_id": key, "missile_name": missile.get("name", "موشک")}); prompt_label = "تعداد موشک"
        elif kind == "team":
            selection["team_number"] = int(key)
            draft = context.user_data.get("robot_store_draft") or {}
            draft.setdefault("components", []).append({"kind": "team", "team_number": int(key)})
            context.user_data["robot_store_draft"] = draft
            await query.answer("تیم به بسته اضافه شد.", show_alert=True); await _show_custom_builder(query, draft, is_new=not bool(draft.get("id"))); return
        elif kind in {"population", "leadership"}:
            prompt_label = "مقدار شهروند" if kind == "population" else "مقدار تجربه رهبری"
        # بازگشت از ورود مقدار همیشه باید به انتخاب نوع/مدل همان محصول برگردد؛
        # برای جمعیت و تجربه رهبری نیز پنل مرحلهٔ قبلی همان comp_category است.
        back_callback = _owner_cb("comp_category", kind)
        state = {"mode": "component_amount", "selection": selection, "back_callback": back_callback}
        prompt, markup = _start_input(context, state, query, f"🔢 <b>{escape(prompt_label)}</b>\n\nمقدار موردنظر را به‌صورت عدد مثبت ارسال کنید.", back_callback)
        await query.answer(); await _edit(query, prompt, markup); _register(query); return
    if action == "remove_comp" and len(parts) >= 4:
        draft = context.user_data.get("robot_store_draft")
        try:
            index = int(parts[3])
            if not isinstance(draft, dict) or index < 0 or index >= len(draft.get("components", [])):
                raise ValueError
            draft["components"].pop(index)
            context.user_data["robot_store_draft"] = draft
            await query.answer("مورد از بسته حذف شد.", show_alert=True); await _show_custom_builder(query, draft, is_new=not bool(draft.get("id"))); return
        except Exception:
            await query.answer("❌ مورد معتبر نیست.", show_alert=True); return
    if action == "save_custom":
        draft = context.user_data.get("robot_store_draft")
        if not isinstance(draft, dict) or not draft.get("components"):
            await query.answer("❌ محصول باید حداقل یک مورد داشته باشد.", show_alert=True); return
        if not draft.get("id"):
            draft["id"] = _new_product_id()
            draft["created_at"] = datetime.utcnow().isoformat()
            draft.setdefault("original_price", 0)
            draft["enabled"] = True
            catalog["custom_products"].append(draft)
        else:
            existing = _find_custom(catalog, draft["id"])
            if not existing:
                await query.answer("❌ محصول اصلی پیدا نشد.", show_alert=True); return
            existing.update(draft)
        _save_catalog(session, catalog)
        context.user_data.pop("robot_store_draft", None); context.user_data.pop("robot_store_state", None)
        await query.answer("✅ محصول ذخیره شد.", show_alert=True)
        await _owner_custom_detail(query, session, draft["id"])
        return
    if action == "cancel_custom":
        draft = context.user_data.pop("robot_store_draft", None); context.user_data.pop("robot_store_state", None)
        category = "bundles" if (draft or {}).get("kind") == "bundle" else "events"
        await query.answer("ساخت محصول لغو شد.", show_alert=True); await _owner_category(query, session, category); return

    await query.answer("❌ این گزینه شناخته نشد.", show_alert=True)


def _make_payload(category, key, amount, session):
    if category == "resources":
        return {"kind": "resource", "resource": key, "amount": int(amount)}
    if category == "population":
        return {"kind": "population", "amount": int(amount)}
    if category == "leadership":
        return {"kind": "leadership", "amount": int(amount)}
    if category == "shields":
        return {"kind": "shield", "shield_type": key, "duration_hours": int(amount)}
    if category in {"missiles", "missile_level"}:
        if category == "missile_level":
            missile_id, level = str(key).rsplit("@", 1)
        else:
            missile_id, level = str(key), None
        missile = next((m for m in get_missiles_config(session).get("items", []) if str(m.get("id")) == missile_id), {})
        payload = {"kind": "missile", "missile_id": missile_id, "missile_name": str(missile.get("name") or "موشک"), "quantity": int(amount)}
        if level is not None:
            payload["level"] = int(level)
        return payload
    raise ValueError("invalid product category")


def _purchase_name(payload, fallback="محصول فروشگاه"):
    kind = payload.get("kind")
    if kind == "resource":
        return RESOURCE_LABELS.get(payload.get("resource"), "منبع")
    if kind == "population":
        return "👥 شهروند"
    if kind == "leadership":
        return "👑 تجربه رهبری"
    if kind == "shield":
        return SHIELD_LABELS.get(payload.get("shield_type"), "سپر")
    if kind == "missile":
        name = str(payload.get("missile_name") or "موشک")
        level = payload.get("level")
        return f"{name} — سطح {int(level)}" if level is not None else name
    if kind == "team":
        return f"🏗️ تیم ساخت‌وساز {int(payload.get('team_number', 0) or 0)}"
    return fallback


async def _set_pending_purchase(query, context, uid, name, category, payload, price, product_id=None, session=None, back_callback=None, original_price=0):
    price = int(price)
    if price <= 0:
        await query.answer("❌ قیمت این محصول هنوز توسط اونر تنظیم نشده است.", show_alert=True)
        return
    if price > 9_000_000_000_000_000_000:
        await query.answer("❌ مبلغ محصول خارج از محدوده مجاز است.", show_alert=True)
        return
    context.user_data["robot_store_pending_purchase"] = {
        "user_id": int(uid), "name": str(name), "category": str(category),
        "payload": payload, "price": price, "product_id": product_id,
        "back_callback": back_callback,
        "original_price": max(0, int(original_price or 0)),
        "purchase_token": uuid.uuid4().hex[:16],
    }
    if session is not None:
        wallet = ensure_wallet(session, uid)
        balance = int(wallet.balance or 0)
    else:
        with SessionLocal() as temp:
            wallet = ensure_wallet(temp, uid)
            balance = int(wallet.balance or 0)
    detail = _format_payload(payload)
    original_price = int(context.user_data["robot_store_pending_purchase"].get("original_price", 0) or 0)
    price_lines = (f"💎 قیمت واقعی محصولات: <s>{format_amount(original_price)} تومان</s>\n"
                   f"🎁 قیمت بسته: <b>{format_amount(price)} تومان</b>\n") if original_price > 0 else f"💰 مبلغ پرداختی: <b>{format_amount(price)} تومان</b>\n"
    text = ("🧾 <b>تأیید خرید</b>\n━━━━━━━━━━━━━━━━━━\n"
            f"📦 محصول: <b>{escape(str(name))}</b>\n"
            f"{detail}\n\n"
            f"{price_lines}"
            f"👛 موجودی فعلی کیف پول: <b>{format_amount(balance)} تومان</b>\n"
            f"👛 موجودی پس از خرید: <b>{format_amount(max(0, balance-price))} تومان</b>\n\n"
            "با تأیید خرید، محصول به کیف محصولات شما اضافه می‌شود و فعلاً روی هیچ کشوری اعمال نخواهد شد.")
    await _edit(query, text, _markup([
        [_btn("✅ تأیید و پرداخت", _uid_cb(uid, "confirm_purchase", context.user_data["robot_store_pending_purchase"]["purchase_token"]), "success")],
        [_btn("❌ لغو خرید", _uid_cb(uid, "cancel_purchase", context.user_data["robot_store_pending_purchase"]["purchase_token"]), "danger")],
    ]))
    _register(query)


async def _user_item_view(query, uid, category, key, session, *, answer=True):
    data = _catalog(session)
    if category == "resources":
        conf = data["resources"].get(key, {})
    elif category == "missiles":
        missile = next((m for m in get_missiles_config(session).get("items", []) if str(m.get("id")) == str(key)), None)
        missile_conf = data.get("missiles", {}).get(str(key), {})
        if not missile or not missile_conf.get("enabled"):
            await query.answer("این موشک فعلاً برای فروش فعال نیست.", show_alert=True); return
        level_configs = missile_conf.get("levels", {}) if isinstance(missile_conf.get("levels"), dict) else {}
        level_buttons = []
        for level in range(1, max(1, min(100, int(missile.get("max_level", 1) or 1))) + 1):
            level_conf = level_configs.get(str(level), {})
            if not level_conf.get("enabled"):
                continue
            has_price = int(level_conf.get("unit_price", 0) or 0) > 0 or any(
                p.get("enabled", True) and int(p.get("price", 0) or 0) > 0
                for p in level_conf.get("plans", [])
            )
            if has_price:
                level_buttons.append(_btn(f"🚀 سطح {level}", _uid_cb(uid, "missile_level", str(key), level)))
        if not level_buttons:
            await query.answer("❌ در حال حاضر هیچ سطح قابل خریدی برای این موشک وجود ندارد.", show_alert=True); return
        rows = [level_buttons[i:i + 5] for i in range(0, len(level_buttons), 5)]
        rows.append([_btn("🔙 برگشت", _uid_cb(uid, "cat", "missiles"), "danger")])
        if answer:
            await query.answer()
        await _edit(query, f"🚀 <b>{escape(str(missile.get('name') or 'موشک'))}</b>\n\nسطح موردنظر را انتخاب کنید:", _markup(rows))
        _register(query)
        return
    elif category == "population":
        conf = data["population"]
    elif category == "leadership":
        conf = data["leadership"]
    elif category == "shields":
        conf = data["shields"].get(key, {})
    elif category == "missile_level":
        if not _missile_level_parent_enabled(data, key, session):
            await query.answer("این موشک فعلاً برای فروش فعال نیست.", show_alert=True)
            return
        conf = _get_config(data, "missile_level", key) or {}
    else:
        await query.answer("❌ محصول پیدا نشد.", show_alert=True); return
    if not conf.get("enabled"):
        await query.answer("این محصول فعلاً برای فروش فعال نیست.", show_alert=True); return
    title = _get_config_title(category, key, session)
    lines = [f"🛍️ <b>{escape(title)}</b>", ""]
    rows = []
    unit_price = int(conf.get("unit_price", 0) or 0)
    if unit_price > 0:
        if category in {"missiles", "missile_level"}:
            lines.append(f"💰 قیمت هر موشک: <b>{unit_price:,} تومان</b>")
        else:
            unit_label = {"shields": "ساعت", "population": "شهروند", "leadership": "واحد تجربه", "missile_level": "موشک"}.get(category, "واحد")
            lines.append(f"💰 هر <b>{int(conf.get('unit_amount', 1) or 1):,} {unit_label}</b>: <b>{unit_price:,} تومان</b>")
        minimum = int(conf.get("min", 1) or 1)
        maximum = int(conf.get("max", 0) or 0)
        lines.append(f"📉 حداقل خرید: <b>{minimum:,}</b>")
        lines.append(f"📈 حداکثر خرید: <b>{format_amount(maximum) if maximum else 'بدون سقف'}</b>")
        rows.append([_btn("✍️ خرید مقدار دلخواه", _uid_cb(uid, "custom", category, key), "success")])
    plans = [p for p in conf.get("plans", []) if p.get("enabled", True) and int(p.get("price", 0) or 0) > 0]
    if plans:
        lines.append("\n<b>📦 پلن‌های آماده:</b>")
        for plan in plans:
            unit_label = {"shields": "ساعت", "missiles": "موشک", "missile_level": "موشک", "population": "شهروند", "leadership": "واحد تجربه"}.get(category, "واحد")
            rows.append([_btn(f"{str(plan.get('name') or 'پلن')[:24]} — {int(plan.get('amount', 0) or 0):,} {unit_label} | {int(plan.get('price', 0) or 0):,} تومان", _uid_cb(uid, "plan", category, key, plan.get("id")))])
    lines.append("\nتمام خریدها به کیف محصولات اضافه می‌شوند.")
    rows.append([_btn("🔙 برگشت", _uid_cb(uid, "cat", category), "danger")])
    if answer:
        await query.answer()
    await _edit(query, "\n".join(lines), _markup(rows))
    _register(query)


async def _user_plan_purchase(query, context, uid, category, key, plan_id, session):
    data = _catalog(session)
    conf = _get_config(data, category, key)
    plan = _find_plan(conf or {}, plan_id)
    if category == "missile_level" and not _missile_level_parent_enabled(data, key, session):
        await query.answer("این موشک فعلاً برای فروش فعال نیست.", show_alert=True); return
    if not conf or not conf.get("enabled") or not plan or not plan.get("enabled", True):
        await query.answer("❌ این پلن در دسترس نیست.", show_alert=True); return
    amount = int(plan.get("amount", 0) or 0)
    price = int(plan.get("price", 0) or 0)
    if amount <= 0 or price <= 0:
        await query.answer("❌ اطلاعات قیمت‌گذاری پلن کامل نیست.", show_alert=True); return
    payload = _make_payload(category, key, amount, session)
    name = f"{_get_config_title(category, key, session)} — {plan.get('name', 'پلن')}"
    await query.answer()
    await _set_pending_purchase(query, context, uid, name, category, payload, price,
                                f"plan:{category}:{key}:{plan_id}", session=session,
                                back_callback=_uid_cb(uid, "item", category, key))


async def _user_custom_product(query, context, uid, product_id, session):
    data = _catalog(session)
    product = _find_custom(data, product_id)
    if not product or not product.get("enabled", True) or int(product.get("price", 0) or 0) <= 0:
        await query.answer("❌ این محصول در دسترس نیست یا قیمت بسته تعیین نشده است.", show_alert=True); return
    payload = {"kind": product.get("kind"), "components": list(product.get("components", [])), "description": product.get("description", "")}
    name = str(product.get("name") or "محصول")
    price = int(product.get("price", 0) or 0)
    await query.answer()
    back_category = "events" if product.get("kind") == "event" else "bundles"
    await _set_pending_purchase(query, context, uid, name,
                                "event" if product.get("kind") == "event" else "bundle",
                                payload, price, f"custom:{product_id}", session=session,
                                back_callback=_uid_cb(uid, "cat", back_category),
                                original_price=int(product.get("original_price", 0) or 0))


async def _user_team_purchase(query, context, uid, team_number, session):
    data = _catalog(session)
    conf = data.get("teams", {}).get(str(team_number), {})
    if not conf.get("enabled") or int(conf.get("price", 0) or 0) <= 0:
        await query.answer("❌ این تیم فعلاً برای فروش فعال نیست.", show_alert=True); return
    team_cfg = get_construction_teams_config(session)
    if int(team_number) < 2 or int(team_number) > int(team_cfg.get("max_teams", 10) or 10):
        await query.answer("❌ این تیم در تنظیمات بازی فعال نیست.", show_alert=True); return
    payload = {"kind": "team", "team_number": int(team_number)}
    await query.answer()
    await _set_pending_purchase(query, context, uid, _purchase_name(payload), "team", payload,
                                int(conf["price"]), f"team:{team_number}", session=session,
                                back_callback=_uid_cb(uid, "cat", "teams"))


async def _user_custom_amount_prompt(query, context, uid, category, key, session):
    data = _catalog(session)
    conf = _get_config(data, category, key)
    if category == "missile_level" and not _missile_level_parent_enabled(data, key, session):
        await query.answer("این موشک فعلاً برای فروش فعال نیست.", show_alert=True); return
    if not conf or not conf.get("enabled") or int(conf.get("unit_price", 0) or 0) <= 0:
        await query.answer("❌ خرید دلخواه این محصول فعال نیست.", show_alert=True); return
    title = _get_config_title(category, key, session)
    unit = {"shields": "ساعت", "missiles": "موشک", "missile_level": "موشک", "population": "شهروند", "leadership": "واحد تجربه"}.get(category, "واحد")
    state = {"mode": "user_custom_amount", "category": category, "key": key, "user_id": uid,
             "chat_id": int(query.message.chat_id), "panel_message_id": int(query.message.message_id), "owner_id": int(uid)}
    context.user_data["robot_store_state"] = state
    minimum = int(conf.get("min", 1) or 1)
    maximum = int(conf.get("max", 0) or 0)
    text = (f"✍️ <b>خرید مقدار دلخواه — {escape(title)}</b>\n\n"
            f"قیمت هر {int(conf.get('unit_amount', 1) or 1) if category != 'missiles' else 1} {unit}: <b>{int(conf.get('unit_price', 0) or 0):,} تومان</b>\n"
            f"حداقل: <b>{minimum:,}</b>\nحداکثر: <b>{format_amount(maximum) if maximum else 'بدون سقف'}</b>\n\n"
            f"مقدار {unit} موردنظر را ارسال کنید:")
    await query.answer(); await _edit(query, text, _markup([[_btn("🔙 برگشت", _uid_cb(uid, "item", category, key), "danger")]])); _register(query)


async def _restore_user_store_back(query, uid, callback, session):
    """Restore the exact store panel from which the purchase was started."""
    if not callback:
        await _user_home(query, uid, session)
        return
    parts = str(callback).split(":")
    if len(parts) < 4 or parts[0:2] != ["rs", "u"] or not parts[2].isdigit() or int(parts[2]) != int(uid):
        await _user_home(query, uid, session)
        return
    action = parts[3]
    if action == "cat" and len(parts) >= 5:
        await _show_user_category(query, uid, parts[4], session, answer=False)
        return
    if action == "item" and len(parts) >= 6:
        await _user_item_view(query, uid, parts[4], parts[5], session, answer=False)
        return
    if action == "missile_level" and len(parts) >= 6:
        await _user_item_view(query, uid, "missile_level", f"{parts[4]}@{parts[5]}", session, answer=False)
        return
    await _user_home(query, uid, session)


async def _confirm_purchase(query, context, uid, session, expected_token=None):
    pending = context.user_data.get("robot_store_pending_purchase")
    if (not isinstance(pending, dict)
            or int(pending.get("user_id", 0) or 0) != int(uid)
            or (expected_token and str(pending.get("purchase_token") or "") != str(expected_token))):
        await query.answer("این درخواست خرید منقضی شده است. دوباره محصول را انتخاب کنید.", show_alert=True)
        return
    price = int(pending.get("price", 0) or 0)
    ensure_wallet(session, uid)
    now = datetime.utcnow()
    result = session.execute(
        update(Wallet)
        .where(Wallet.user_id == int(uid), Wallet.balance >= price)
        .values(balance=Wallet.balance - price, transaction_count=Wallet.transaction_count + 1, updated_at=now)
    )
    if int(result.rowcount or 0) != 1:
        back_callback = pending.get("back_callback")
        context.user_data.pop("robot_store_pending_purchase", None)
        await query.answer("❌ موجودی کافی نیست.", show_alert=True)
        await _restore_user_store_back(query, uid, back_callback, session)
        return
    purchase_token = str(pending.get("purchase_token") or uuid.uuid4().hex[:16])
    pending["purchase_token"] = purchase_token
    inventory = ProductInventory(
        user_id=int(uid),
        product_id=str(pending.get("product_id") or "") or None,
        purchase_token=purchase_token,
        product_name=str(pending.get("name") or "محصول فروشگاه")[:255],
        product_category=str(pending.get("category") or "other")[:48],
        payload_json=json.dumps(pending.get("payload") or {}, ensure_ascii=False),
        paid_amount=price,
        status="available",
        created_at=now,
    )
    session.add(inventory)
    try:
        session.flush()
    except IntegrityError:
        # A unique purchase token makes a rapid/double callback idempotent.
        session.rollback()
        context.user_data.pop("robot_store_pending_purchase", None)
        await query.answer("✅ این خرید قبلاً ثبت شده است.", show_alert=True)
        return
    wallet = session.scalar(select(Wallet).where(Wallet.user_id == int(uid)))
    balance_after = int(wallet.balance or 0) if wallet else 0
    session.commit()
    context.user_data.pop("robot_store_pending_purchase", None)
    text = ("✅ <b>خرید با موفقیت انجام شد.</b>\n\n"
            f"📦 محصول: <b>{escape(inventory.product_name)}</b>\n"
            f"💰 مبلغ پرداخت‌شده: <b>{format_amount(price)} تومان</b>\n"
            f"👛 موجودی جدید کیف پول: <b>{format_amount(balance_after)} تومان</b>\n\n"
            "محصول در کیف محصولات شما ذخیره شد. فعلاً امکان اعمال آن روی کشور وجود ندارد.")
    await query.answer("✅ خرید ثبت شد.", show_alert=True)
    await _edit(query, text, _markup([
        [_btn("🛍️ بازگشت به فروشگاه", _uid_cb(uid, "home"), "primary")],
    ]))
    _register(query)


async def _user_callback(update, context, query, data, session):
    parts = data.split(":")
    if len(parts) < 4 or not parts[2].isdigit():
        await query.answer("❌ درخواست نامعتبر است.", show_alert=True); return
    uid = int(parts[2])
    if uid != int(query.from_user.id):
        await query.answer("⛔ این فروشگاه متعلق به کاربر دیگری است.", show_alert=True); return
    action = parts[3]
    if action in {"home", "cat", "item", "missile_level", "custom", "plan", "team", "custom_product", "confirm_purchase", "bag", "bagitem"}:
        current_catalog = _catalog(session)
        if not current_catalog.get("enabled", True):
            await query.answer("🔴 فروشگاه محصولات فعلاً غیرفعال است.", show_alert=True); return
        if action == "confirm_purchase" and not get_bool(session, WALLET_ENABLED):
            await query.answer("🔴 کیف پول فعلاً غیرفعال است.", show_alert=True); return
    if action == "noop":
        await query.answer(); return
    if action == "home":
        context.user_data.pop("robot_store_state", None)
        context.user_data.pop("robot_store_pending_purchase", None)
        await query.answer(); await _user_home(query, uid, session); return
    if action == "cat" and len(parts) >= 5:
        context.user_data.pop("robot_store_state", None)
        category = parts[4]
        catalog = _catalog(session)
        if not catalog.get("enabled", True):
            await query.answer("🔴 فروشگاه فعلاً غیرفعال است.", show_alert=True); return
        await _show_user_category(query, uid, category, session); return
    if action == "item" and len(parts) >= 6:
        context.user_data.pop("robot_store_state", None)
        category, key = parts[4], parts[5]
        await _user_item_view(query, uid, category, key, session); return
    if action == "missile_level" and len(parts) >= 6:
        context.user_data.pop("robot_store_state", None)
        await _user_item_view(query, uid, "missile_level", f"{parts[4]}@{parts[5]}", session); return
    if action == "custom" and len(parts) >= 6:
        category, key = parts[4], parts[5]
        await _user_custom_amount_prompt(query, context, uid, category, key, session); return
    if action == "plan" and len(parts) >= 7:
        await _user_plan_purchase(query, context, uid, parts[4], parts[5], parts[6], session); return
    if action == "team" and len(parts) >= 5:
        await _user_team_purchase(query, context, uid, int(parts[4]), session); return
    if action == "custom_product" and len(parts) >= 5:
        await _user_custom_product(query, context, uid, parts[4], session); return
    if action == "confirm_purchase":
        expected_token = parts[4] if len(parts) >= 5 else None
        await _confirm_purchase(query, context, uid, session, expected_token=expected_token); return
    if action == "cancel_purchase":
        pending = context.user_data.get("robot_store_pending_purchase")
        expected_token = parts[4] if len(parts) >= 5 else None
        if expected_token and (not isinstance(pending, dict) or str(pending.get("purchase_token") or "") != expected_token):
            await query.answer("این درخواست خرید منقضی شده است.", show_alert=True); return
        back_callback = pending.get("back_callback") if isinstance(pending, dict) else None
        context.user_data.pop("robot_store_pending_purchase", None)
        await query.answer("خرید لغو شد.", show_alert=True)
        await _restore_user_store_back(query, uid, back_callback, session); return
    if action == "bag" and len(parts) >= 5:
        context.user_data.pop("robot_store_state", None)
        await _send_bag_page(query, context, session, uid, int(parts[4]), reply=False); return
    if action == "bagitem" and len(parts) >= 5:
        item_id = int(parts[4])
        bag_page = int(parts[5]) if len(parts) >= 6 else 1
        item = session.scalar(select(ProductInventory).where(ProductInventory.id == item_id, ProductInventory.user_id == uid))
        if item is None:
            await query.answer("❌ این محصول در کیف شما پیدا نشد.", show_alert=True); return
        try:
            payload = json.loads(item.payload_json or "{}")
        except Exception:
            payload = {}
        created = item.created_at.strftime("%Y/%m/%d — %H:%M") if item.created_at else "ثبت نشده"
        text = (f"🎒 <b>{escape(item.product_name)}</b>\n━━━━━━━━━━━━━━━━━━\n"
                f"📦 محتویات:\n{_format_payload(payload)}\n\n"
                f"💰 مبلغ پرداخت‌شده: <b>{int(item.paid_amount):,} تومان</b>\n"
                f"📅 تاریخ خرید: <b>{created}</b>\n"
                f"📌 وضعیت: <b>{'آماده در کیف محصولات' if item.status == 'available' else escape(item.status)}</b>\n\n"
                "فعلاً این محصول فقط در کیف نگهداری می‌شود و امکان اعمال روی کشور هنوز فعال نشده است.")
        await query.answer(); await _edit(query, text, _markup([[_btn("🔙 برگشت به کیف محصولات", _uid_cb(uid, "bag", bag_page), "danger")], [_btn("🛍️ فروشگاه", _uid_cb(uid, "home"))]])); _register(query); return
    await query.answer("❌ این گزینه شناخته نشد.", show_alert=True)


async def notify_store_events_on_interaction(bot, user_id: int, chat_id: int):
    """Send each enabled event announcement once on the user's next bot interaction."""
    user_id = int(user_id)
    if user_id == int(OWNER_ID):
        return
    try:
        with SessionLocal() as session:
            catalog = _catalog(session)
            if not catalog.get("enabled", True):
                return
            events = [
                dict(product) for product in catalog.get("custom_products", [])
                if product.get("kind") == "event" and product.get("enabled", True)
                and product.get("announce", False) and str(product.get("id") or "")
            ]
            unseen = []
            for product in events:
                seen_key = f"robot_store_event_seen:{user_id}:{product['id']}"
                if session.scalar(select(BotSetting).where(BotSetting.key == seen_key)) is None:
                    unseen.append(product)
            session.commit()

        for product in unseen:
            components = product.get("components", []) or []
            detail = "\n".join(f"• {escape(_component_label(comp))}" for comp in components) or "محتویات ثبت نشده"
            description = str(product.get("description") or "").strip()
            text = (
                f"🎉 <b>محصول مناسبتی جدید در فروشگاه محصولات</b>\n\n"
                f"📦 <b>{escape(str(product.get('name') or 'محصول مناسبتی'))}</b>\n"
                + (f"📝 {escape(description)}\n" if description else "")
                + f"💰 قیمت: <b>{int(product.get('price', 0) or 0):,} تومان</b>\n\n"
                f"<b>محتویات بسته:</b>\n{detail}\n\n"
                "برای خرید این محصول به فروشگاه محصولات مراجعه کنید."
            )
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=text,
                    parse_mode="HTML",
                    reply_markup=_markup([[_btn("🛍️ ورود به فروشگاه", _uid_cb(user_id, "home"), "success")]]),
                    disable_web_page_preview=True,
                )
            except Exception:
                # اگر ارسال ممکن نباشد (مثلاً کاربر ربات را بلاک کرده)، برای تلاش بعدی علامت نزن.
                continue
            seen_key = f"robot_store_event_seen:{user_id}:{product['id']}"
            with SessionLocal() as mark_session:
                if mark_session.scalar(select(BotSetting).where(BotSetting.key == seen_key)) is None:
                    mark_session.add(BotSetting(key=seen_key, value="1"))
                    try:
                        mark_session.commit()
                    except IntegrityError:
                        mark_session.rollback()
    except Exception:
        # اطلاع‌رسانی نباید مانع اجرای تعامل اصلی ربات شود.
        return


async def robot_store_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query is None or query.from_user is None:
        return
    data = str(query.data or "")
    if not data.startswith("rs:"):
        return
    if query.from_user.is_bot:
        await query.answer("حساب رباتی اجازه استفاده ندارد.", show_alert=True); return
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.telegram_id == int(query.from_user.id)))
        if user is None:
            await query.answer("❌ ابتدا ربات را با /start فعال کنید.", show_alert=True); return
        parts = data.split(":")
        if len(parts) < 3:
            await query.answer("❌ درخواست نامعتبر است.", show_alert=True); return
        if parts[1] == "o":
            if int(query.from_user.id) != int(OWNER_ID):
                await query.answer("⛔ فقط اونر به این بخش دسترسی دارد.", show_alert=True); return
            await _owner_callback(update, context, query, data, session)
            if session.in_transaction():
                session.commit()
            return
        if parts[1] == "u":
            await _user_callback(update, context, query, data, session)
            if session.in_transaction():
                session.commit()
            return
        await query.answer("❌ درخواست نامعتبر است.", show_alert=True)


async def _edit_saved_panel(context, state, text, markup=None, fallback_message=None):
    chat_id = state.get("chat_id")
    message_id = state.get("panel_message_id")
    if chat_id and message_id:
        try:
            await context.bot.edit_message_text(
                chat_id=int(chat_id), message_id=int(message_id), text=text,
                parse_mode="HTML", reply_markup=markup, disable_web_page_preview=True,
            )
            try:
                from services.panel_security import register_panel
                register_panel(chat_id, message_id, int(state.get("owner_id") or fallback_message.from_user.id))
            except Exception:
                pass
            return
        except Exception:
            pass
    if fallback_message is not None:
        sent = await fallback_message.reply_text(text, parse_mode="HTML", reply_markup=markup)
        state["chat_id"] = int(sent.chat_id)
        state["panel_message_id"] = int(sent.message_id)


async def _message_purchase_confirmation(context, message, uid, pending, panel_state=None, session=None):
    price = int(pending.get("price", 0) or 0)
    if session is not None:
        wallet = ensure_wallet(session, uid)
        balance = int(wallet.balance or 0)
    else:
        with SessionLocal() as temp:
            wallet = ensure_wallet(temp, uid)
            balance = int(wallet.balance or 0)
            temp.commit()
    detail = _format_payload(pending.get("payload") or {})
    original_price = int(pending.get("original_price", 0) or 0)
    price_lines = (f"💎 قیمت واقعی محصولات: <s>{format_amount(original_price)} تومان</s>\n"
                   f"🎁 قیمت بسته: <b>{format_amount(price)} تومان</b>\n") if original_price > 0 else f"💰 مبلغ پرداختی: <b>{format_amount(price)} تومان</b>\n"
    text = ("🧾 <b>تأیید خرید</b>\n━━━━━━━━━━━━━━━━━━\n"
            f"📦 محصول: <b>{escape(str(pending.get('name') or 'محصول'))}</b>\n{detail}\n\n"
            f"{price_lines}"
            f"👛 موجودی فعلی: <b>{format_amount(balance)} تومان</b>\n"
            f"👛 موجودی پس از خرید: <b>{format_amount(max(0, balance-price))} تومان</b>\n\n"
            "با تأیید، محصول به کیف محصولات اضافه می‌شود و فعلاً روی کشور اعمال نخواهد شد.")
    purchase_token = str(pending.get("purchase_token") or uuid.uuid4().hex[:16])
    pending["purchase_token"] = purchase_token
    context.user_data["robot_store_pending_purchase"] = pending
    markup = _markup([
        [_btn("✅ تأیید و پرداخت", _uid_cb(uid, "confirm_purchase", purchase_token), "success")],
        [_btn("❌ لغو خرید", _uid_cb(uid, "cancel_purchase", purchase_token), "danger")],
    ])
    if panel_state and panel_state.get("panel_message_id"):
        await _edit_saved_panel(context, panel_state, text, markup, message)
    else:
        sent = await message.reply_text(text, parse_mode="HTML", reply_markup=markup)
        from services.panel_security import register_panel
        register_panel(sent.chat_id, sent.message_id, uid)


async def handle_store_message(update: Update, context: ContextTypes.DEFAULT_TYPE, message, session, user) -> bool:
    """Consume only messages belonging to an active robot-store input flow."""
    state = context.user_data.get("robot_store_state")
    if not isinstance(state, dict):
        return False
    if int(state.get("chat_id", message.chat_id) or message.chat_id) != int(message.chat_id):
        return False

    raw = (message.text or "").strip()
    if not raw:
        await message.reply_text("❌ لطفاً مقدار را به‌صورت متن ارسال کنید.")
        return True

    # هر دکمه/دستور شناخته‌شدهٔ دیگر، حالت انتظار فروشگاه را لغو می‌کند.
    try:
        from handlers.messages import BAN_COMMAND_NAMES, command_key, is_text_command
        if raw.startswith("/") or is_text_command(raw) or command_key(raw) in BAN_COMMAND_NAMES:
            context.user_data.pop("robot_store_state", None)
            context.user_data.pop("robot_store_draft", None)
            return False
    except Exception:
        if raw.startswith("/"):
            context.user_data.pop("robot_store_state", None)
            context.user_data.pop("robot_store_draft", None)
            return False

    mode = state.get("mode")
    uid = int(user.telegram_id)

    # پیام متنیِ دریافتی در تمام مراحل فروشگاه، قبل از ویرایش پنل حذف می‌شود.
    try:
        await message.delete()
    except Exception:
        pass

    if mode == "user_custom_amount":
        category, key = state.get("category"), str(state.get("key"))
        catalog = _catalog(session)
        conf = _get_config(catalog, category, key)
        if (not conf or not conf.get("enabled")
                or (category == "missile_level" and not _missile_level_parent_enabled(catalog, key, session))):
            context.user_data.pop("robot_store_state", None)
            await message.reply_text("❌ این محصول دیگر فعال نیست.")
            return True
        try:
            amount = _parse_number(raw, integer=True)
            minimum = int(conf.get("min", 1) or 1)
            maximum = int(conf.get("max", 0) or 0)
            if amount < minimum:
                raise ValueError(f"حداقل خرید {minimum:,} است.")
            if maximum > 0 and amount > maximum:
                raise ValueError(f"حداکثر خرید {maximum:,} است.")
            unit_amount = 1 if category in {"missiles", "missile_level"} else max(1, int(conf.get("unit_amount", 1) or 1))
            unit_price = int(conf.get("unit_price", 0) or 0)
            price = (amount * unit_price + unit_amount - 1) // unit_amount
            if price <= 0:
                raise ValueError("قیمت این محصول هنوز تنظیم نشده است.")
            if price > 9_000_000_000_000_000_000:
                raise ValueError("مبلغ محاسبه‌شده از محدوده مجاز بیشتر است.")
            payload = _make_payload(category, key, amount, session)
            name = _purchase_name(payload)
        except ValueError as exc:
            await message.reply_text(f"❌ مقدار واردشده معتبر نیست. {escape(str(exc) if str(exc) != 'invalid' else '')}\nدوباره مقدار را ارسال کنید.", parse_mode="HTML")
            return True
        panel_state = dict(state)
        context.user_data.pop("robot_store_state", None)
        pending = {"user_id": uid, "name": name, "category": category, "payload": payload,
                   "price": price, "product_id": f"custom-amount:{category}:{key}",
                   "back_callback": _uid_cb(uid, "item", category, key),
                   "purchase_token": uuid.uuid4().hex[:16]}
        context.user_data["robot_store_pending_purchase"] = pending
        await _message_purchase_confirmation(context, message, uid, pending, panel_state, session=session)
        return True

    if mode == "config_value":
        category, key, field = state.get("category"), str(state.get("key")), state.get("field")
        catalog = _catalog(session)
        conf = _get_config(catalog, category, key)
        if conf is None:
            context.user_data.pop("robot_store_state", None)
            await message.reply_text("❌ تنظیمات این محصول پیدا نشد.")
            return True
        try:
            if field in {"unit_price", "price"}:
                value = _parse_number(raw, integer=True) if raw not in {"0", "۰"} else 0
            else:
                value = _parse_number(raw, integer=True) if raw not in {"0", "۰"} else 0
            if field == "unit_amount" and value < 1:
                raise ValueError("مقدار پایه باید حداقل ۱ باشد.")
            if field == "min" and value < 1:
                raise ValueError("حداقل خرید باید حداقل ۱ باشد.")
            if field == "max" and value > 0 and value < int(conf.get("min", 1) or 1):
                raise ValueError("حداکثر خرید نمی‌تواند کمتر از حداقل خرید باشد.")
            if field not in {"unit_amount", "unit_price", "min", "max", "price"}:
                raise ValueError("فیلد نامعتبر است.")
            conf[field] = value
            _save_catalog(session, catalog)
        except Exception as exc:
            await message.reply_text(f"❌ مقدار نامعتبر است: {escape(str(exc))}\nدوباره ارسال کنید.", parse_mode="HTML")
            return True
        context.user_data.pop("robot_store_state", None)
        title = _get_config_title(category, key, session)
        text = _config_text(category, key, conf, title)
        markup = _config_keyboard(category, key, conf)
        await _edit_saved_panel(context, state, text, markup, message)
        return True

    if mode == "plan_add":
        step = state.get("step")
        if step == "name":
            name = raw.strip()
            if not name or len(name) > 60:
                await message.reply_text("❌ نام پلن باید بین ۱ تا ۶۰ نویسه باشد.")
                return True
            state["name"] = name
            state["step"] = "amount"
            context.user_data["robot_store_state"] = state
            unit = "ساعت" if state.get("category") == "shields" else "واحد/تعداد"
            await _edit_saved_panel(context, state, f"🔢 <b>مقدار پلن</b>\n\nتعداد {unit} این پلن را ارسال کنید.", _markup([[_btn("🔙 برگشت", _owner_cb("plan_add_back", state.get("category"), state.get("key"), "name", state.get("page", 1)), "danger")]]), message)
            return True
        if step == "amount":
            try:
                amount = _parse_number(raw, integer=True)
            except Exception:
                await message.reply_text("❌ مقدار باید یک عدد صحیح مثبت باشد. دوباره ارسال کنید.")
                return True
            state["amount"] = amount
            state["step"] = "price"
            context.user_data["robot_store_state"] = state
            await _edit_saved_panel(context, state, "💰 <b>قیمت پلن</b>\n\nقیمت نهایی این پلن را به تومان ارسال کنید.", _markup([[_btn("🔙 برگشت", _owner_cb("plan_add_back", state.get("category"), state.get("key"), "amount", state.get("page", 1)), "danger")]]), message)
            return True
        if step == "price":
            try:
                price = _parse_number(raw, integer=True)
            except Exception:
                await message.reply_text("❌ قیمت باید یک عدد مثبت باشد. دوباره ارسال کنید.")
                return True
            catalog = _catalog(session)
            conf = _get_config(catalog, state.get("category"), state.get("key"))
            if conf is None:
                context.user_data.pop("robot_store_state", None)
                await message.reply_text("❌ تنظیمات این محصول پیدا نشد.")
                return True
            conf.setdefault("plans", []).append({"id": uuid.uuid4().hex[:8], "name": state["name"], "amount": int(state["amount"]), "price": int(price), "enabled": True})
            _save_catalog(session, catalog)
            category, key = state.get("category"), state.get("key")
            context.user_data.pop("robot_store_state", None)
            title = _get_config_title(category, key, session)
            await _edit_saved_panel(
                context, state,
                _plan_management_text(category, key, conf, title),
                _plan_management_keyboard(category, key, conf),
                message,
            )
            return True

    if mode == "plan_edit":
        category, key, pid, field = state.get("category"), state.get("key"), state.get("plan_id"), state.get("field")
        catalog = _catalog(session); conf = _get_config(catalog, category, key); plan = _find_plan(conf or {}, pid)
        if not plan:
            context.user_data.pop("robot_store_state", None)
            await message.reply_text("❌ پلن پیدا نشد.")
            return True
        try:
            if field == "name":
                value = raw.strip()
                if not value or len(value) > 60:
                    raise ValueError("نام پلن باید بین ۱ تا ۶۰ نویسه باشد.")
            elif field == "amount":
                value = _parse_number(raw, integer=True)
            elif field == "price":
                value = _parse_number(raw, integer=True) if raw not in {"0", "۰"} else 0
            else:
                raise ValueError("فیلد نامعتبر است.")
            plan[field] = value
            _save_catalog(session, catalog)
        except Exception as exc:
            await message.reply_text(f"❌ مقدار نامعتبر است: {escape(str(exc))}\nدوباره ارسال کنید.", parse_mode="HTML")
            return True
        context.user_data.pop("robot_store_state", None)
        text = _plan_text(conf, plan, _get_config_title(category, key, session))
        await _edit_saved_panel(context, state, text, _plan_detail_keyboard(category, key, plan, int(state.get("page", 1) or 1)), message)
        return True

    if mode == "custom_create":
        step = state.get("step")
        if step == "name":
            if not raw or len(raw) > 70:
                await message.reply_text("❌ نام باید بین ۱ تا ۷۰ نویسه باشد.")
                return True
            state["name"] = raw
            state["step"] = "description"
            context.user_data["robot_store_state"] = state
            prompt = "📝 <b>توضیحات محصول</b>\n\nتوضیحات بسته را ارسال کنید یا برای ادامه بدون توضیحات، دکمه زیر را بزنید."
            markup = _markup([
                [_btn("🚫 بدون توضیحات", _owner_cb("custom_no_description"), "danger")],
                [_btn("🔙 برگشت به نام محصول", _owner_cb("custom_back_name"), "danger")],
            ])
            await _edit_saved_panel(context, state, prompt, markup, message)
            return True
        if step == "description":
            description = "" if raw == "-" else raw
            if len(description) > 800:
                await message.reply_text("❌ توضیحات حداکثر ۸۰۰ نویسه باشد.")
                return True
            draft = context.user_data.get("robot_store_draft")
            if not isinstance(draft, dict):
                draft = {"id": None, "kind": state.get("kind"), "name": state.get("name", "محصول"), "description": "", "price": 0, "original_price": 0, "components": [], "enabled": True, "announce": False}
            draft["description"] = description
            draft["name"] = state.get("name") or draft.get("name")
            context.user_data["robot_store_draft"] = draft
            builder_state = dict(state)
            builder_state.update({"mode": "custom_compose", "is_new": True})
            context.user_data["robot_store_state"] = builder_state
            await _edit_saved_panel(context, state, _custom_components_text(draft), _custom_builder_keyboard(draft, is_new=True), message)
            return True

    if mode == "custom_price":
        try:
            price = 0 if raw.strip().translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")) in {"0", ""} else _parse_number(raw, integer=True)
        except Exception:
            await message.reply_text("❌ قیمت باید عدد صحیح صفر یا بیشتر به تومان باشد.")
            return True
        draft = context.user_data.get("robot_store_draft")
        if not isinstance(draft, dict):
            context.user_data.pop("robot_store_state", None)
            await message.reply_text("❌ پیش‌نویس محصول پیدا نشد.")
            return True
        field = state.get("field", "price")
        if field not in {"price", "original_price"}:
            field = "price"
        draft[field] = int(price)
        context.user_data["robot_store_draft"] = draft
        product_id = draft.get("id")
        if product_id:
            catalog = _catalog(session)
            product = _find_custom(catalog, product_id)
            if not product:
                context.user_data.pop("robot_store_state", None)
                await message.reply_text("❌ محصول ذخیره‌شده پیدا نشد.")
                return True
            product.update(draft)
            product[field] = int(price)
            _save_catalog(session, catalog)
            context.user_data.pop("robot_store_state", None)
            detail_lines = [f"🛍️ <b>{'محصول ترکیبی' if product.get('kind') == 'bundle' else 'محصول مناسبتی'}</b>",
                            f"📦 نام: <b>{escape(str(product.get('name', '')))}</b>",
                            f"💎 قیمت واقعی محصولات: <b>{int(product.get('original_price', 0) or 0):,} تومان</b>",
                            f"🎁 قیمت بسته: <b>{int(product.get('price', 0) or 0):,} تومان</b>",
                            f"وضعیت: <b>{'فعال' if product.get('enabled', True) else 'غیرفعال'}</b>",
                            f"📝 توضیحات: {escape(str(product.get('description') or 'ثبت نشده'))}"]
            await _edit_saved_panel(context, state, "\n".join(detail_lines), _custom_detail_keyboard(product), message)
            context.user_data.pop("robot_store_draft", None)
            return True
        builder_state = dict(state)
        builder_state.update({"mode": "custom_compose", "is_new": True})
        context.user_data["robot_store_state"] = builder_state
        await _edit_saved_panel(context, state, _custom_components_text(draft), _custom_builder_keyboard(draft, is_new=True), message)
        return True

    if mode == "custom_edit":
        product_id, field = state.get("product_id"), state.get("field")
        catalog = _catalog(session); product = _find_custom(catalog, product_id)
        if not product:
            context.user_data.pop("robot_store_state", None)
            await message.reply_text("❌ محصول پیدا نشد.")
            return True
        try:
            if field == "name":
                value = raw.strip()
                if not value or len(value) > 70:
                    raise ValueError("نام باید بین ۱ تا ۷۰ نویسه باشد.")
            elif field == "description":
                value = "" if raw == "-" else raw
                if len(value) > 800:
                    raise ValueError("توضیحات حداکثر ۸۰۰ نویسه باشد.")
            elif field == "price":
                value = _parse_number(raw, integer=True)
            else:
                raise ValueError("فیلد نامعتبر است.")
            product[field] = value
            _save_catalog(session, catalog)
        except Exception as exc:
            await message.reply_text(f"❌ مقدار نامعتبر است: {escape(str(exc))}\nدوباره ارسال کنید.", parse_mode="HTML")
            return True
        context.user_data.pop("robot_store_state", None)
        lines = [f"📦 <b>{escape(str(product.get('name')))}</b>",
                 f"💎 قیمت واقعی محصولات: <b>{int(product.get('original_price', 0) or 0):,} تومان</b>",
                 f"🎁 قیمت بسته: <b>{int(product.get('price', 0) or 0):,} تومان</b>",
                 f"📝 {escape(str(product.get('description') or 'بدون توضیحات'))}"]
        await _edit_saved_panel(context, state, "\n".join(lines), _custom_detail_keyboard(product), message)
        return True

    if mode in {"component_amount", "component_edit_amount"}:
        selection = state.get("selection") or {}
        kind = selection.get("kind")
        try:
            amount = _parse_number(raw, integer=(kind != "shield"))
            if kind == "shield" and (amount <= 0 or amount > 8760):
                raise ValueError("مدت سپر باید بیشتر از صفر و حداکثر ۸۷۶۰ ساعت باشد.")
        except Exception as exc:
            await message.reply_text(f"❌ مقدار معتبر نیست: {escape(str(exc))}\nدوباره ارسال کنید.", parse_mode="HTML")
            return True
        comp = dict(selection)
        if kind == "resource":
            comp["amount"] = int(amount)
        elif kind == "population":
            comp["amount"] = int(amount)
        elif kind == "leadership":
            comp["amount"] = int(amount)
        elif kind == "shield":
            comp["hours"] = float(amount)
        elif kind == "missile":
            comp["quantity"] = int(amount)
        else:
            await message.reply_text("❌ نوع محصول معتبر نیست.")
            return True
        draft = context.user_data.get("robot_store_draft")
        if not isinstance(draft, dict):
            context.user_data.pop("robot_store_state", None)
            await message.reply_text("❌ پیش‌نویس بسته پیدا نشد. دوباره شروع کنید.")
            return True
        if mode == "component_edit_amount":
            index = int(state.get("component_index", -1))
            if index < 0 or index >= len(draft.get("components", [])):
                await message.reply_text("❌ موردی که می‌خواهید ویرایش کنید پیدا نشد.")
                return True
            draft["components"][index] = comp
        else:
            draft.setdefault("components", []).append(comp)
        context.user_data["robot_store_draft"] = draft
        builder_state = dict(state)
        builder_state.update({"mode": "custom_compose", "is_new": not bool(draft.get("id"))})
        context.user_data["robot_store_state"] = builder_state
        if mode == "component_edit_amount":
            list_text = "📋 <b>لیست محصولات داخل بسته</b>\n━━━━━━━━━━━━━━━━━━\nبرای ویرایش یا حذف، مورد را انتخاب کنید:"
            await _edit_saved_panel(context, state, list_text, _component_list_keyboard(draft), message)
        else:
            await _edit_saved_panel(context, state, _custom_components_text(draft), _custom_builder_keyboard(draft, is_new=not bool(draft.get("id"))), message)
        return True

    return False
