from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from keyboards.style import resolve_callback_data
from telegram.ext import ContextTypes
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import json
import time
from collections import Counter
import asyncio as _asyncio
from html import escape
from sqlalchemy import select, delete, func

from database.db import SessionLocal
from database.models import User, Admin, Country, UserCountry, BotSetting, BankAccount, BankLoan, BankInvestment
CountryModel = Country

from config import OWNER_ID
from services.admin import (
    is_admin, is_owner, add_admin, remove_admin, get_admin_user, get_admins,
    clear_all_admins,
    get_users, get_admin_permissions, set_admin_permission, admin_has_permission, get_user_by_telegram_id, ban_user, unban_user, clear_bans, ban_status_text,
)
from keyboards.admin import (
    admin_panel_keyboard,
    owner_panel_keyboard, owner_challenges_keyboard,
    admin_management_keyboard,
    add_admin_mode_keyboard,
    admin_confirm_keyboard,
    admin_multiple_confirm_keyboard,
    remove_admin_mode_keyboard,
    remove_multiple_confirm_keyboard,
    admin_search_result_keyboard,
    admin_clear_confirm_keyboard,
    admin_permission_keyboard, admin_permission_section_keyboard,
    admin_back_keyboard, admin_step_back_keyboard,
    admin_info_keyboard,
    admin_list_keyboard,
    balance_amount_keyboard,
    balance_country_list_keyboard,
    user_management_keyboard, user_management_tools_keyboard, user_access_keyboard, user_list_keyboard, user_action_mode_keyboard,
    user_action_keyboard, admin_user_game_settings_keyboard, user_status_keyboard, user_admin_keyboard, user_search_result_keyboard, user_detail_back_keyboard, user_search_mode_keyboard, user_search_confirm_keyboard, user_leadership_country_keyboard, user_leadership_mode_keyboard, user_game_population_mode_keyboard, user_game_population_input_keyboard, user_game_population_confirm_keyboard,
    user_confirm_keyboard, user_multiple_confirm_keyboard, user_game_specs_country_list_keyboard, stats_role_keyboard, stats_back_keyboard, leadership_change_mode_keyboard, leadership_multiple_keyboard, leadership_apply_keyboard, leadership_operation_keyboard,
    banned_list_keyboard, clear_bans_confirm_keyboard, balance_change_keyboard, balance_mode_keyboard, resource_keyboard, ban_reason_keyboard, ban_reason_back_keyboard, ban_duration_keyboard,
    balance_continue_keyboard, balance_final_keyboard, balance_multiple_users_keyboard, balance_single_input_keyboard, population_change_keyboard, population_mode_keyboard, population_single_input_keyboard, population_multiple_users_keyboard, population_country_list_keyboard, population_amount_keyboard, population_final_keyboard, ban_multiple_ids_keyboard, user_country_list_keyboard, user_country_delete_list_keyboard, user_country_delete_confirm_keyboard,
    phone_status_keyboard, phone_toggle_keyboard, stats_period_keyboard, initial_settings_keyboard, admin_messages_keyboard, message_lists_keyboard, message_items_keyboard, message_detail_keyboard, message_private_continue_keyboard, message_public_targets_keyboard, message_confirm_keyboard,
    economy_keyboard, building_management_keyboard, bank_economy_keyboard, bank_build_keyboard, bank_build_costs_keyboard, bank_level_edit_keyboard, bank_level_costs_keyboard, bank_deposit_settings_keyboard, bank_tax_settings_keyboard, bank_level_settings_keyboard, bank_loans_settings_keyboard, bank_loan_range_keyboard, installment_settings_keyboard, bank_investments_settings_keyboard, bank_investment_edit_keyboard, bank_investment_list_keyboard, bank_investment_delete_confirm_keyboard, bank_investment_return_type_keyboard, bot_shutdown_keyboard, general_settings_keyboard, owner_security_keyboard, owner_anti_spam_keyboard, owner_backup_keyboard, owner_backup_panel_text, owner_security_backup_keyboard, owner_anti_spam_panel_text, owner_social_links_keyboard, owner_social_add_keyboard, owner_social_list_keyboard, owner_social_delete_keyboard, owner_social_item_detail_keyboard, owner_social_edit_keyboard, owner_mandatory_ad_edit_keyboard, owner_optional_ad_edit_keyboard, social_add_edit_keyboard, owner_optional_ad_members_keyboard, owner_optional_ad_time_keyboard, social_links_keyboard, social_constraint_keyboard, social_members_constraint_keyboard, social_time_constraint_keyboard, social_add_confirm_keyboard, metal_mine_economy_keyboard, metal_mine_level_keyboard, metal_mine_level_edit_keyboard, metal_mine_build_cost_keyboard, metal_mine_build_cost_input_keyboard, metal_mine_costs_keyboard, game_settings_user_keyboard, delete_group_keyboard, delete_group_confirm_keyboard, economy_value_confirm_keyboard,
    arsenal_economy_keyboard, arsenal_level_keyboard, arsenal_level_edit_keyboard, arsenal_build_keyboard, arsenal_costs_keyboard, hq_economy_keyboard, hq_level_keyboard, hq_level_edit_keyboard, hq_costs_keyboard, missile_management_keyboard, missile_edit_keyboard, missile_base_settings_keyboard, missile_type_keyboard, missile_category_keyboard, missile_items_keyboard, missile_create_type_keyboard, missile_draft_keyboard, missile_delete_confirm_keyboard, missile_sticker_keyboard, missile_level_keyboard, missile_level_edit_keyboard, missile_value_confirm_keyboard, missile_operational_keyboard, missile_operational_delete_keyboard, missile_operational_list_keyboard, missile_loot_percent_keyboard, missile_global_loot_percent_keyboard, shield_management_keyboard, shield_type_management_keyboard, shield_item_list_keyboard, shield_item_detail_keyboard, shield_delete_confirm_keyboard, shield_edit_keyboard, shield_add_keyboard, shield_user_sign_keyboard, shield_user_mode_keyboard, shield_user_multiple_keyboard, shield_user_type_keyboard, shield_user_amount_keyboard, shield_user_confirm_keyboard, shield_reset_mode_keyboard, shield_reset_multiple_keyboard, shield_reset_confirm_keyboard, shield_user_country_keyboard, shield_user_country_pick_keyboard,
)
from services.command_scopes import grant_admin_command_scope, revoke_admin_command_scope
from services.settings import get_setting, set_setting, PHONE_USER_KEY, PHONE_ADMIN_KEY, all_phone_enabled, phone_required_for, get_bot_shutdown_mode, set_bot_shutdown_mode, get_anti_spam_enabled, set_anti_spam_enabled, get_anti_spam_user_max, set_anti_spam_user_max, get_anti_spam_user_window, set_anti_spam_user_window, get_anti_spam_group_max, set_anti_spam_group_max, get_anti_spam_group_window, set_anti_spam_group_window, get_backup_interval, set_backup_interval, get_backup_started, set_backup_started, get_backup_execution_time, set_backup_execution_time, get_swap_cooldown_hours, set_swap_cooldown_hours, get_swap_last_at, set_swap_last_at, get_country_establishment_uranium_cost, set_country_establishment_uranium_cost, get_country_rename_money_cost, set_country_rename_money_cost, get_country_rename_method, set_country_rename_method, get_country_rename_money_enabled, set_country_rename_money_enabled, get_country_rename_uranium_enabled, set_country_rename_uranium_enabled, get_global_loot_percent, set_global_loot_percent, get_bank_loan_interval_hours, set_bank_loan_interval_hours, get_bank_loan_lock_days, set_bank_loan_lock_days, get_bank_loan_lock_hours, set_bank_loan_lock_hours, get_bank_loan_overdue_multiplier, set_bank_loan_overdue_multiplier
from services.social_rewards import _mark_verified
from services.social_links import _save_items, get_social_settings, get_social_items, get_active_social_items, add_social_item, delete_social_item, update_social_item, set_social_value, save_optional_join_pending, public_chat_target, social_item_button_url, mandatory_items, private_message_link_chat_id
from services.economy import get_config as get_shield_config, save_config as save_shield_config, get_items as get_shield_items, get_item_by_id as get_shield_item_by_id, purchase as purchase_shield, is_type_enabled as is_shield_type_enabled, remaining_text as shield_remaining_text, purchase_cooldown_remaining as shield_purchase_cooldown_remaining, reset_purchase_limitations as reset_shield_purchase_limitations, adjust_active_shield_time, get_shield_auto_settings, save_shield_auto_setting, register_group_attack_received, consume_shield_time_for_group_attack, active_for_target as active_shield_for_target
from services.economy import get_metal_mine_config, save_metal_mine_config, get_arsenal_config, save_arsenal_config, get_hq_config, save_hq_config, get_missiles_config, save_missiles_config, get_initial_resources, save_initial_resources, get_bank_config, save_bank_config, bank_level_config, bank_max_level, ensure_bank_account, accrue_bank_profit, accrue_bank_tax, bank_deposit, bank_deposit_capacity, bank_withdraw_principal, bank_withdraw_profit, bank_withdraw_tax, bank_withdraw_all, bank_instant_finish_uranium_cost, finish_bank_construction_now, cancel_bank_construction
from services.bank_loan_smart import policy_from_level_config, quote_loan
from services.panel_security import check_panel, set_panel_owner, register_panel
from services.bank_loan_repayment import process_due_loan, current_installment_amount
from services.construction_teams import (
    get_construction_teams_config, get_team_status, team_purchase_quote, team_purchase_quotes, buy_team, buy_next_team,
    set_max_teams, set_team_price, reserve_team, release_team, free_team_exists, sync_country_teams,
)
from enigma.database import ensure_settings, get_setting as enigma_get, set_setting as enigma_set
from services.golden_boxes import load_config as golden_config, save_config as golden_save_config, load_state as golden_state, save_state as golden_save_state, load_group_state as golden_group_state, save_group_state as golden_save_group_state, reward_for as golden_reward_for, cost_for as golden_cost_for, hq_required_for as golden_hq_required_for, apply_reward as golden_apply_reward, BOXES as GOLDEN_BOXES, weights_valid as golden_weights_valid
from enigma.challenges import ensure_missions, TYPE_NAMES, mission_bank_counts
from enigma.engine import start as enigma_start, key as enigma_key, submit as enigma_submit, grant_reward, state as enigma_state, reveal_answer_panel as enigma_reveal_answer_panel, render_answer_panel as enigma_render_answer_panel, STATUS_PENDING, STATUS_ACTIVE, STATUS_COMPLETED, STATUS_FAILED, STATUS_EXPIRED
from enigma.keyboards import box_keyboard, answer_keyboard, owner_main_keyboard, owner_settings_keyboard, owner_levels_keyboard, owner_level_edit_keyboard, owner_types_keyboard, owner_type_edit_keyboard, owner_type_level_edit_keyboard, owner_bank_keyboard, owner_bank_type_keyboard, owner_days_keyboard, owner_mission_manage_keyboard, owner_attempts_keyboard, owner_mission_type_keyboard, owner_mission_level_keyboard, owner_mission_list_keyboard, owner_mission_edit_keyboard, owner_mission_type_edit_keyboard, owner_mission_level_edit_keyboard, owner_mission_reward_edit_keyboard, owner_mission_delete_confirm_keyboard, owner_mission_search_type_keyboard, owner_mission_search_results_keyboard

from handlers.leaderboards import leaderboard_callback


def _user_game_country_panel(session, target_id, country_id, back_callback=None):
    """Render the canonical country details panel used by all user-game edit confirmations."""
    target = get_user_by_telegram_id(session, int(target_id))
    country = session.get(Country, int(country_id))
    if target is None or country is None:
        return None, None
    owned_ids = {int(c.id) for c in get_user_countries(session, target)}
    if int(country.id) not in owned_ids:
        return None, None
    default_country = get_default_country(session, target)
    population = int(ensure_bank_account(session, country).citizens or 0)
    text = (
        f"🌍 <b>مشخصات بازی کشور</b>\n\n"
        f"🏳️ کشور: <b>{escape(country.title)}</b>\n"
        f"⭐ کشور پیش‌فرض: <b>{'بله' if default_country and int(default_country.id)==int(country.id) else 'خیر'}</b>\n"
        f"👥 جمعیت: <b>{population:,}</b> نفر\n\n"
        + country_status(country, get_metal_mine_config(session), get_arsenal_config(session), _country_shield_status(session, country), include_identity=False)
    )
    back = back_callback or f"admin:user_game_specs:{int(target_id)}"
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 تغییر موجودی", callback_data=f"admin:user_balance:{int(target_id)}:{int(country_id)}")],
        [InlineKeyboardButton("👑 تنظیم تجربه رهبری", callback_data=f"admin:user_leadership_country:{int(target_id)}:{int(country_id)}")],
        [InlineKeyboardButton("🛡️ تنظیم سپر", callback_data=f"admin:shield_country:{int(target_id)}:{int(country_id)}:manage")],
        [InlineKeyboardButton("👥 تغییر جمعیت", callback_data=f"admin:user_game_population:{int(target_id)}:{int(country_id)}")],
        [InlineKeyboardButton("🔙 برگشت", callback_data=back)],
    ])
    return text[:4096], markup


def _golden_box_text(cfg, k):
    icon, name = GOLDEN_BOXES[k]
    lv = cfg['levels'][k]
    return (
        f"{icon} <b>تنظیمات جعبه {name}</b>\n\n"
        f"🎲 احتمال: <b>{float(cfg['weights'].get(k, 0) or 0):g}%</b>\n"
        f"⭐ حداکثر سطح: <b>{int(lv.get('max_level', 100))}</b>\n"
        f"⚡ اورانیوم تکمیل فوری: <b>{float(lv.get('instant_finish_uranium', 0) or 0):g}</b>\n"
        f"📊 تنظیمات سطح‌ها: <b>برای هر سطح جداگانه</b>"
    )

from services.leadership import (get_group_base, set_group_base, get_global_base, set_global_base, get_repeat_reset_hours, set_repeat_reset_hours, leadership_rank_text, apply_leadership_result)

from services.game import (
    can_upgrade_hq, hq_level_data, hq_build_cost, hq_upgrade_cost, hq_instant_finish_uranium_cost, finish_hq_construction_now,
    build_hq,
    get_default_country, get_context_country,
    get_or_create_user,
    get_user_countries,
    hq_info,
    set_default_country,
    upgrade_hq,
    build_metal_mine,
    can_build_metal_mine,
    metal_mine_info,
    can_upgrade_metal_mine,
    build_arsenal, can_build_arsenal, arsenal_info, can_upgrade_arsenal, upgrade_arsenal, arsenal_instant_finish_uranium_cost, finish_arsenal_construction_now, cancel_arsenal_construction,
    upgrade_metal_mine,
    collect_metal_mine, metal_mine_instant_finish_uranium_cost, finish_metal_mine_construction_now, cancel_metal_mine_construction,
    country_status, create_country, get_country_by_name, register_user_in_country, get_user_country_in_continent,
    exchange_rate_text,
    get_exchange_rates, save_exchange_rate, get_exchange_text, save_exchange_text,
    EXCHANGE_RATES,
    calculate_exchange,
    execute_exchange,
    resource_available, construction_remaining, finalize_construction, construction_label, cancel_hq_construction, start_construction,
    get_missile_inventory, save_missile_inventory, get_missile_count, add_missile_to_inventory, get_missile_tech_level, save_missile_tech_level, get_missile_tech_construction, finalize_missile_tech_upgrade, missile_tech_upgrade_remaining, start_missile_tech_upgrade, cancel_missile_tech_upgrade, missile_tech_instant_finish_uranium_cost, finish_missile_tech_upgrade_now,
)
from keyboards.main import (
    country_list_keyboard,
    self_country_edit_list_keyboard,
    hq_keyboard, hq_cancel_confirm_keyboard,
    arsenal_cancel_confirm_keyboard,
    metal_mine_keyboard, metal_mine_cancel_confirm_keyboard,
    private_main_keyboard,
    exchange_keyboard,
    exchange_confirm_keyboard,
    exchange_input_keyboard,
    country_edit_confirm_keyboard,
    country_edit_waiting_keyboard,
    swap_country_keyboard,
    swap_target_keyboard,
    swap_confirm_keyboard,
    country_name_confirm_keyboard, arsenal_keyboard, arsenal_missile_list_keyboard, arsenal_sell_quantity_keyboard, arsenal_sell_confirm_keyboard, country_rename_payment_keyboard, central_bank_keyboard, central_bank_locked_keyboard, construction_teams_user_keyboard, central_bank_deposit_keyboard, central_bank_loans_keyboard, central_bank_deposit_input_keyboard, central_bank_withdraw_confirm_keyboard, central_bank_loan_input_keyboard, central_bank_investment_input_keyboard, central_bank_loan_detail_keyboard, central_bank_investments_keyboard, central_bank_investment_plan_keyboard, central_bank_my_loans_keyboard, central_bank_my_investments_keyboard, central_bank_my_investment_detail_keyboard, central_bank_population_keyboard, shield_purchase_list_keyboard, missile_technology_keyboard, missile_technology_types_keyboard, missile_technology_list_keyboard, missile_upgrade_levels_keyboard, missile_upgrade_settings_keyboard
)


def _investment_plan_text(plan, index=None, admin=False):
    ptype=str(plan.get("plan_type",plan.get("type","medium")))
    type_name={"short":"کوتاه‌مدت","medium":"میان‌مدت","long":"بلندمدت"}.get(ptype,"میان‌مدت")
    return_names={"money":"پول","population":"جمعیت","fuel":"سوخت","metal":"فلز","uranium":"اورانیوم","leadership_experience":"تجربه رهبری"}
    return_type=str(plan.get("return_type","money")); return_name=return_names.get(return_type,"پول")
    mn=float(plan.get("min_amount",0) or 0); mx=float(plan.get("max_amount",0) or 0); max_text=f"{mx:,.0f}" if mx>0 else "بدون سقف"
    if return_type=="money":
        pmin=float(plan.get("profit_min_percent",plan.get("profit_percent",0)) or 0); pmax=float(plan.get("profit_max_percent",plan.get("profit_percent",0)) or 0)
        lmin=float(plan.get("loss_min_percent",plan.get("loss_percent",0)) or 0); lmax=float(plan.get("loss_max_percent",plan.get("loss_percent",0)) or 0)
        outcome=f"📈 سود احتمالی: <b>{(pmin+pmax)/2:g}%</b>\n📉 زیان احتمالی: <b>{(lmin+lmax)/2:g}%</b>"
    else:
        pmin=float(plan.get("profit_min_value",0) or 0); pmax=float(plan.get("profit_max_value",0) or 0); lmin=float(plan.get("loss_min_value",0) or 0); lmax=float(plan.get("loss_max_value",0) or 0)
        outcome=f"📈 سود احتمالی: <b>{(pmin+pmax)/2:,.0f}</b>\n📉 زیان احتمالی: <b>{(lmin+lmax)/2:,.0f}</b>"
    base=(f"📈 <b>{escape(str(plan.get('name','سرمایه‌گذاری')))}</b>\n\n"+f"🧩 نوع طرح: <b>{type_name}</b>\n"+f"🎚️ ریسک: <b>{escape(str(plan.get('risk','متوسط')))}</b>\n"+f"🎁 نوع بازده: <b>{return_name}</b>\n"+f"💰 مبلغ: <b>{mn:,.0f}</b> تا <b>{max_text}</b>\n"+outcome+"\n"+f"⏱️ مدت: <b>{float(plan.get('duration_hours',0) or 0):g} ساعت</b>")
    if admin:
        base += f"\n👤 حداکثر برای هر کاربر: <b>{int(plan.get('max_per_user',1) or 1)}</b> مورد\n🔁 سرمایه‌گذاری همزمان: <b>{'مجاز' if bool(plan.get('allow_multiple_active',False)) else 'غیرمجاز'}</b>\n📌 وضعیت: <b>{'فعال' if bool(plan.get('active',True)) else 'غیرفعال'}</b>"
    return base



def _golden_general_text(cfg):
    days=cfg.get('active_days',list(range(7))) or []
    daynames=['شنبه','یکشنبه','دوشنبه','سه‌شنبه','چهارشنبه','پنجشنبه','جمعه']
    selected='، '.join(daynames[int(i)] for i in days if 0 <= int(i) < 7) or 'هیچ روزی'
    return ("⚙️ <b>تنظیمات عمومی جعبه‌ها</b>\n\n"
            f"🔘 وضعیت: <b>{'فعال' if cfg.get('enabled') else 'غیرفعال'}</b>\n"
            f"📦 تعداد روزانه: <b>{int(cfg.get('daily_count',0) or 0)}</b>\n"
            f"🕐 ساعت شروع: <b>{cfg.get('start','10:00')}</b>\n"
            f"🕐 ساعت پایان: <b>{cfg.get('end','23:00')}</b>\n"
            f"📅 روزهای ارسال: <b>{selected}</b>\n"
            f"🗑️ حذف پس از باز شدن: <b>{max(0,int(cfg.get('opened_delete_seconds',0) or 0))//60} دقیقه</b>\n"
            f"⌛ حذف بدون برنده: <b>{max(1,int(cfg.get('unanswered_delete_seconds',60) or 60))//60} دقیقه</b>\n\n"
            "در این بخش فقط تنظیمات عمومی زمان ارسال و حذف جعبه‌ها مدیریت می‌شود.")

def _golden_schedule_text(cfg):
    days=cfg.get('active_days',list(range(7))) or []
    daynames=['شنبه','یکشنبه','دوشنبه','سه‌شنبه','چهارشنبه','پنجشنبه','جمعه']
    selected='، '.join(daynames[int(i)] for i in days if 0 <= int(i) < 7) or 'هیچ روزی'
    return ("⏰ <b>زمان‌بندی جعبه‌ها</b>\n\n"
            f"📦 تعداد روزانه: <b>{int(cfg.get('daily_count',0) or 0)}</b>\n"
            f"🕐 ساعت شروع: <b>{cfg.get('start','10:00')}</b>\n"
            f"🕐 ساعت پایان: <b>{cfg.get('end','23:00')}</b>\n"
            f"📅 روزهای فعال: <b>{selected}</b>")

def _golden_expiry_text(cfg):
    opened=max(0,int(cfg.get('opened_delete_seconds',0) or 0))//60
    unanswered=max(1,int(cfg.get('unanswered_delete_seconds',60) or 60))//60
    return ("⏳ <b>زمان‌های حذف جعبه</b>\n\n"
            f"🗑️ حذف پس از باز شدن: <b>{opened} دقیقه</b>\n"
            f"⌛ حذف بدون برنده: <b>{unanswered} دقیقه</b>\n\n"
            "هر دو مقدار بر حسب دقیقه تنظیم می‌شوند.")

def _golden_challenge_text(cfg):
    return ("🧩 <b>تنظیمات چالش</b>\n\n"
            f"🔢 تعداد رقم رمز: <b>{int(cfg.get('challenge_digits',5) or 5)}</b>\n"
            f"🔘 تعداد گزینه‌ها: <b>{int(cfg.get('options_count',4) or 4)}</b>\n\n"
            "این بخش تنظیمات رمز و گزینه‌های پاسخ چالش جعبه‌ها را کنترل می‌کند.")


def _bank_user_level_text(session, country):
    raw_level=int(country.bank_level or 0)
    if raw_level <= 0:
        return f"🏦 <b>بانک مرکزی</b>\n\n📊 وضعیت: <b>ساخته نشده</b>"
    level=raw_level
    acc=accrue_bank_profit(session,country)
    lines=[f"🏦 <b>بانک مرکزی — سطح {level}</b>", ""]

    # در پنل اصلی فقط اطلاعاتی که واقعاً موجود است نمایش داده شود؛
    # سود سپرده قابل برداشت عمداً در این پنل نمایش داده نمی‌شود.
    deposit=float(acc.deposit_principal or 0)
    active_loans=int(session.scalar(select(func.count(BankLoan.id)).where(
        BankLoan.country_id==country.id, BankLoan.status=="active"
    )) or 0)
    active_investments=int(session.scalar(select(func.count(BankInvestment.id)).where(
        BankInvestment.country_id==country.id, BankInvestment.status=="active"
    )) or 0)

    if deposit>0:
        lines.append(f"💰 موجودی سپرده: <b>{deposit:,.0f}</b> پول")
    if active_loans>0:
        lines.append(f"💳 تعداد وام‌ها: <b>{active_loans}</b>")
    if active_investments>0:
        lines.append(f"📈 تعداد سرمایه‌گذاری‌ها: <b>{active_investments}</b>")

    lines.append(f"👥 جمعیت: <b>{int(acc.citizens or 0):,}</b>")
    return "\n".join(lines)


def _bank_build_upgrade_text(session, country, target, operation):
    d=bank_level_config(session,target) or {}
    cost=(d.get("build_cost",{}) if target<=1 else d.get("upgrade_cost",{})) or {}
    time_key="build_time_hours" if target<=1 else "upgrade_time_hours"
    loan=d.get("loan",{}) or {}
    investments=[x for x in (d.get("investments",[]) or []) if isinstance(x,dict)]
    min_amount=float(loan.get("min_amount",0) or 0); max_amount=float(loan.get("max_amount",0) or 0)
    min_interest=float(loan.get("min_interest_percent",0) or 0); max_interest=float(loan.get("max_interest_percent",0) or 0)
    min_inst=int(loan.get("min_installments",1) or 1); max_inst=int(loan.get("max_installments",1) or 1)
    max_active=int(loan.get("max_active_loans",1) or 1)
    tax_min=float(d.get("tax_min",0) or 0); tax_max=float(d.get("tax_max",0) or 0)
    inv_lines=[]
    for inv in investments:
        inv_lines.append(f"• {escape(str(inv.get('name','سرمایه‌گذاری')))} | وضعیت: {'فعال' if bool(inv.get('active',True)) else 'غیرفعال'} | ریسک: {escape(str(inv.get('risk','متوسط')))} | سود: {float(inv.get('profit_percent',0) or 0):g}% | زیان: {float(inv.get('loss_percent',0) or 0):g}% | مدت: {float(inv.get('duration_hours',0) or 0):g} ساعت")
    inv_text="\n".join(inv_lines) if inv_lines else "• طرح فعالی برای این سطح ثبت نشده است."
    return (f"{'🏗️' if target<=1 else '⬆️'} <b>{operation} بانک مرکزی — سطح {target}</b>\n\n"
        f"📋 <b>تمام مشخصات سطح {target}</b>\n"
        f"🏛️ سطح مرکز فرماندهی مورد نیاز: <b>{int(d.get('required_hq_level',1) or 1)}</b>\n"
        f"⏱️ زمان {('ساخت' if target<=1 else 'ارتقا')}: <b>{float(d.get(time_key,0) or 0):g} ساعت</b>\n\n"
        f"💰 <b>هزینه {('ساخت' if target<=1 else 'ارتقا')}</b>\n"
        f"💰 پول: <b>{float(cost.get('money',0) or 0):,.0f}</b>\n"
        f"🔩 فلز: <b>{float(cost.get('metal',0) or 0):,.0f}</b>\n"
        f"⛽ سوخت: <b>{float(cost.get('fuel',0) or 0):,.0f}</b>\n"
        f"☢️ اورانیوم: <b>{float(cost.get('uranium',0) or 0):,.2f}</b>\n\n"
        f"🏦 <b>سپرده</b>\n📦 ظرفیت: <b>{float(d.get('deposit_capacity',0) or 0):,.0f}</b> پول\n📈 سود ساعتی: <b>{float(d.get('deposit_hourly_profit_percent',0) or 0):g}%</b>\n\n"
        f"💳 <b>وام</b>\n💰 مبلغ: <b>{min_amount:,.0f}</b> تا <b>{max_amount:,.0f}</b>\n📈 سود: <b>{min_interest:g}%</b> تا <b>{max_interest:g}%</b>\n🧾 تعداد اقساط: <b>{min_inst}</b> تا <b>{max_inst}</b>\n💳 فاصله هر قسط: <b>{get_bank_loan_interval_hours(session):g} ساعت</b>\n👥 حداکثر وام فعال: <b>{max_active}</b>\n\n"
        f"📈 <b>سرمایه‌گذاری</b>\n{inv_text}\n\n"
        f"👥 <b>مالیات</b>\n🧾 مالیات به ازای هر ۱۰۰۰ شهروند: <b>{tax_min:g}</b> تا <b>{tax_max:g}</b>")


def _display_tehran(value):
    if value is None:
        return "—"
    if value.tzinfo is None:
        value=value.replace(tzinfo=timezone.utc)
    return value.astimezone(ZoneInfo("Asia/Tehran")).strftime("%Y-%m-%d %H:%M")


def _waiting_scope_key(key):
    return f"__waiting_scope__{key}"


def _swap_country_state(session, a, b):
    """Swap all mutable gameplay state between two Country rows.
    Primary key and chat_id stay attached to the physical country row; every
    other country field is swapped, including active construction timers/targets.
    """
    excluded = {"id", "chat_id"}
    # موجودی موشک‌ها در BotSetting و خارج از جدول Country نگهداری می‌شود؛ آن را هم منتقل می‌کنیم.
    inv_a = get_missile_inventory(session, a.id)
    inv_b = get_missile_inventory(session, b.id)
    save_missile_inventory(session, a.id, inv_b)
    save_missile_inventory(session, b.id, inv_a)

    # حساب بانک یک رکورد یکتا برای هر کشور دارد؛ ابتدا شناسه‌های موقت می‌گذاریم
    # تا UniqueConstraint هنگام جابه‌جایی برخورد نکند.
    bank_a=session.scalar(select(BankAccount).where(BankAccount.country_id==a.id))
    bank_b=session.scalar(select(BankAccount).where(BankAccount.country_id==b.id))
    if bank_a: bank_a.country_id=-int(a.id)
    if bank_b: bank_b.country_id=-int(b.id)
    session.flush()
    if bank_a: bank_a.country_id=int(b.id)
    if bank_b: bank_b.country_id=int(a.id)
    for loan in session.scalars(select(BankLoan).where(BankLoan.country_id.in_([a.id,b.id]))).all():
        loan.country_id = int(b.id) if int(loan.country_id)==int(a.id) else int(a.id)
    for inv in session.scalars(select(BankInvestment).where(BankInvestment.country_id.in_([a.id,b.id]))).all():
        inv.country_id = int(b.id) if int(inv.country_id)==int(a.id) else int(a.id)

    # وضعیت سپرهای کشورمحور و محدودیت خرید نیز باید همراه کشور جابه‌جا شوند.
    for setting_key in ("shield_active_v1", "shield_purchase_cooldown_v1"):
        row=session.scalar(select(BotSetting).where(BotSetting.key==setting_key))
        if row and row.value:
            try:
                state=json.loads(row.value)
                if isinstance(state,dict):
                    for rec in state.values():
                        if isinstance(rec,dict) and rec.get("country_id") is not None:
                            cid=int(rec.get("country_id"))
                            if cid==int(a.id): rec["country_id"]=-int(a.id)
                            elif cid==int(b.id): rec["country_id"]=-int(b.id)
                    for rec in state.values():
                        if isinstance(rec,dict) and rec.get("country_id") is not None:
                            cid=int(rec.get("country_id"))
                            if cid==-int(a.id): rec["country_id"]=int(b.id)
                            elif cid==-int(b.id): rec["country_id"]=int(a.id)
                    # کلیدهای کشورمحور را هم بازسازی می‌کنیم.
                    rebuilt={}
                    for key,rec in state.items():
                        nk=key
                        if isinstance(rec,dict) and rec.get("country_id") is not None and ":" in str(key):
                            parts=str(key).split(":")
                            if len(parts)>=3:
                                try:
                                    oldcid=int(parts[1]); newcid=int(rec.get("country_id"))
                                    parts[1]=str(newcid); nk=":".join(parts)
                                except Exception: pass
                        rebuilt[nk]=rec
                    row.value=json.dumps(rebuilt,ensure_ascii=False)
            except Exception:
                pass

    # سطح فناوری موشک و تایمر آن با country_id در کلید ذخیره می‌شوند.
    for row in session.scalars(select(BotSetting)).all():
        key=str(row.key)
        for prefix in ("missile_tech_level:", "missile_tech_construction:"):
            if key.startswith(prefix):
                tail=key[len(prefix):]
                try:
                    oldcid=int(tail.split(":",1)[0])
                    if oldcid in {int(a.id),int(b.id)}:
                        newcid=int(b.id) if oldcid==int(a.id) else int(a.id)
                        suffix=tail.split(":",1)[1] if ":" in tail else ""
                        newkey=prefix+str(newcid)+(":"+suffix if suffix else "")
                        existing=session.scalar(select(BotSetting).where(BotSetting.key==newkey))
                        if existing is None:
                            row.key=newkey
                        else:
                            existing.value=row.value; session.delete(row)
                except Exception:
                    pass
                break

    for column in Country.__table__.columns:
        name = column.name
        if name in excluded:
            continue
        va = getattr(a, name)
        vb = getattr(b, name)
        setattr(a, name, vb)
        setattr(b, name, va)


def _delete_country_dependencies(session, country_id: int):
    """Remove every persistent state owned by a deleted country."""
    cid=int(country_id)
    session.execute(delete(BankAccount).where(BankAccount.country_id==cid))
    session.execute(delete(BankLoan).where(BankLoan.country_id==cid))
    session.execute(delete(BankInvestment).where(BankInvestment.country_id==cid))
    # Country-scoped JSON states.
    for setting_key in ("shield_active_v1", "shield_purchase_cooldown_v1"):
        row=session.scalar(select(BotSetting).where(BotSetting.key==setting_key))
        if not row: continue
        try:
            state=json.loads(row.value) if row.value else {}
            if isinstance(state,dict):
                state={k:v for k,v in state.items() if not (isinstance(v,dict) and int(v.get("country_id",0) or 0)==cid)}
                row.value=json.dumps(state,ensure_ascii=False)
        except Exception: pass
    # Missile inventory/tech/construction settings are keyed by country id.
    for row in session.scalars(select(BotSetting)).all():
        key=str(row.key)
        if key.startswith(("country_missile_inventory_v1:", "missile_tech_level:", "missile_tech_construction:")):
            try:
                if int(key.split(":",2)[1])==cid:
                    session.delete(row)
            except Exception: pass


async def _delete_message_after(bot, chat_id: int, message_id: int, delay: float = 30.0):
    import asyncio
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass


async def _notify_user(bot, telegram_id: int, text: str):
    """ارسال اعلان مدیریتی به کاربر؛ خطای ارسال نباید عملیات مدیریتی را خراب کند."""
    try:
        await bot.send_message(chat_id=int(telegram_id), text=text, parse_mode="HTML")
    except Exception:
        pass




async def _resolve_missile_flight(bot, flight, user_data=None, flight_token=None):
    """پس از رسیدن موشک، نتیجه را در گروه ارسال و گزارش دائمی را در PV مهاجم می‌فرستد."""
    import asyncio, time
    delay=max(0.0, float(flight.get("target_time", 0) or 0))
    await asyncio.sleep(delay)
    # Persisted flight cleanup is handled by the worker after this resolver returns.
    chat_id=int(flight.get("chat_id")); flight_message_id=int(flight.get("message_id"))
    result = "🚀 <b>نتیجه حمله</b>\n\n⚠️ در محاسبه نتیجه حمله خطایی رخ داد."
    private_result = None
    attacker = target = None
    leadership = None
    try:
        with SessionLocal() as session:
            if flight_token:
                from services.atomic_claims import claim_once
                if not claim_once(session, f"missile:claim:{flight_token}", "1"):
                    return
            attacker=session.get(Country, int(flight.get("attacker_country_id",0)))
            target=session.get(Country, int(flight.get("target_country_id",0)))
            if attacker is None or target is None:
                result="💥 <b>نتیجه حمله</b>\n\n❌ کشور مهاجم یا هدف دیگر وجود ندارد."
            else:
                from services.economy import get_hq_config, get_metal_mine_config, get_arsenal_config, get_missiles_config
                from handlers.messages import _launch_target_buildings
                hq_cfg=get_hq_config(session); mine_cfg=get_metal_mine_config(session); arsenal_cfg=get_arsenal_config(session)
                buildings=_launch_target_buildings(target,hq_cfg,mine_cfg,arsenal_cfg)
                power=float(flight.get("power",0) or 0)
                loot_percent=max(0.0,min(100.0,float(flight.get("loot_percent",0) or 0)))
                missile_name=str(flight.get("missile_name","موشک"))
                level=int(flight.get("level",1))
                attacker_country=escape(str(attacker.title or "کشور شما"))
                target_country=escape(str(target.title or "کشور هدف"))
                attacker_continent=escape(str(getattr(attacker,"continent_name",None) or "بدون نام"))
                target_continent=escape(str(getattr(target,"continent_name",None) or "بدون نام"))
                weapon_label=f"{escape(missile_name)} ({level})"

                if not buildings:
                    result=("🚀 <b>نتیجه حمله</b>\n\n"
                            f"🚀 موشک: <b>{weapon_label}</b>\n"
                            "❌ شخص هدف هیچ ساختمانی ندارد.")
                    private_result=("🚀 <b>گزارش حمله (حمله قاره‌ای)</b>\n\n"
                                    f"🌍 کشور شما: <b>{attacker_country}</b>\n"
                                    f"🗺️ قاره شما: <b>{attacker_continent}</b>\n"
                                    f"🎯 کشور هدف: <b>{target_country}</b>\n"
                                    f"🗺️ قاره هدف: <b>{target_continent}</b>\n\n"
                                    f"🚀 تسلیحات شلیک‌شده: <b>{weapon_label}</b>\n"
                                    "❌ شخص هدف هیچ ساختمانی ندارد.")
                else:
                    # ساختمان‌ها برای گزارش از قوی‌ترین به ضعیف‌ترین مرتب می‌شوند.
                    buildings = sorted(buildings, key=lambda b: float(b.get("strength", 0) or 0), reverse=True)
                    total=sum(max(0.0,float(b.get("strength",0) or 0)) for b in buildings)
                    remaining_power=max(0.0,power)
                    total_damage=min(power,total)
                    damage_ratio=(total_damage/total) if total>0 else 0.0
                    effective_loot_percent=loot_percent

                    # میزان خسارت هر ساختمان به ترتیب قدرت محاسبه می‌شود.
                    damage_lines=[]
                    building_status_lines=[]
                    for b in buildings:
                        strength=max(0.0,float(b.get("strength",0) or 0))
                        dmg=min(strength,remaining_power)
                        remaining_power-=dmg
                        if strength <= 0:
                            status="سالم ماند"
                        elif dmg >= strength:
                            status="تخریب شد"
                        elif dmg > 0:
                            status="آسیب دید"
                        else:
                            status="سالم ماند"
                        level_text = f" سطح {int(b.get('level', 0))}" if b.get('level') else ""
                        damage_lines.append(
                            f"🏢 <b>{escape(str(b['name']))}{level_text}</b> — <b>{status}</b>\n"
                            f"خسارت <b>{dmg:,.0f}</b> از <b>{strength:,.0f}</b>"
                        )
                        building_status_lines.append(f"🏢 <b>{escape(str(b['name']))}{level_text}</b>: <b>{status}</b>")

                    leadership = apply_leadership_result(session, attacker, target, damage_ratio * 100.0)
                    attacker_xp_delta = leadership["gain"] if leadership["attacker_won"] else -leadership["loss"]
                    defender_xp_delta = -leadership["loss"] if leadership["attacker_won"] else leadership["gain"]

                    resource_labels={"money":"💰 پول","metal":"🔩 فلز","fuel":"⛽ سوخت"}
                    stolen={}
                    for key,label in resource_labels.items():
                        # کشور دارای منبع بی‌نهایت هرگز قابل غارت نیست؛
                        # حتی اگر به‌دلیل سابقه داده‌ای مقدار عددی هم در ستون منبع مانده باشد.
                        if bool(getattr(target, f"infinite_{key}", False)):
                            continue
                        current=float(getattr(target,key,0) or 0)
                        if current <= 0: continue
                        amount=current * effective_loot_percent / 100.0
                        amount=min(current,max(0.0,amount))
                        if amount > 0:
                            setattr(target,key,current-amount)
                            stolen[key]=amount
                            if key == "money": attacker.money=float(attacker.money or 0)+amount
                            elif key == "metal": attacker.metal=float(attacker.metal or 0)+amount
                            elif key == "fuel": attacker.fuel=float(attacker.fuel or 0)+amount

                    # گزارش نهایی گروه: هر بخش در نقل‌قول مستقل نمایش داده می‌شود.
                    quote = lambda text: "<blockquote>" + text + "</blockquote>"
                    attacker_name = escape(str(attacker.leader_name or attacker.title or "نامشخص"))
                    defender_name = escape(str(target.leader_name or target.title or "نامشخص"))

                    result_parts = ["⚔️ <b>نتیجه حمله</b>", ""]
                    result_parts.append(quote(f"مهاجم:\n{attacker_name}"))
                    result_parts.append(quote(f"مدافع:\n{defender_name}"))
                    result_parts.append("🚀 <b>تسلیحات شلیک شده:</b>")
                    result_parts.append(quote(
                        f"موشک: {escape(missile_name)} ({level})\n"
                        f"قدرت موشک: {power:,.0f}"
                    ))
                    result_parts.append(quote(f"مجموع قدرت شلیک: {power:,.0f}"))
                    result_parts.append("🏢 <b>ساختمان‌های هدف:</b>")
                    for b, dmg_line in zip(buildings, damage_lines):
                        # damage_lines از قبل دقیقاً بر اساس قدرت شلیک ساخته شده است؛ همان خط را داخل نقل‌قول قرار می‌دهیم.
                        clean = dmg_line.replace("🏢 ", "", 1)
                        result_parts.append(quote(clean))

                    attacker_resource_lines = [f"تجربه XP: {'+' if attacker_xp_delta >= 0 else ''}{attacker_xp_delta:,.0f}"]
                    defender_resource_lines = [f"تجربه XP: {'+' if defender_xp_delta >= 0 else ''}{defender_xp_delta:,.0f}"]
                    if stolen:
                        for key,label in resource_labels.items():
                            if key in stolen:
                                attacker_resource_lines.append(f"{label}: +{stolen[key]:,.0f}")
                                defender_resource_lines.append(f"{label}: -{stolen[key]:,.0f}")
                    result_parts.append("📊 <b>نتایج مهاجم:</b>")
                    result_parts.append(quote("\n".join(attacker_resource_lines)))
                    result_parts.append("📊 <b>نتایج مدافع:</b>")
                    result_parts.append(quote("\n".join(defender_resource_lines)))
                    result = "\n\n".join(result_parts)

                    # گزارش دائمی PV مهاجم؛ اطلاعات کامل حمله بدون درصدهای داخلی محاسبه.
                    private_lines=[
                        "🚀 <b>گزارش حمله (حمله قاره‌ای)</b>","",
                        f"🌍 کشور شما: <b>{attacker_country}</b>",
                        f"🗺️ قاره شما: <b>{attacker_continent}</b>",
                        f"🎯 کشور هدف: <b>{target_country}</b>",
                        f"🗺️ قاره هدف: <b>{target_continent}</b>","",
                        f"🚀 <b>تسلیحات شلیک‌شده:</b> {weapon_label}",
                        "\n🏢 <b>میزان تخریب:</b>",
                    ]
                    private_lines.extend(damage_lines)
                    private_lines.append(f"\n💥 <b>مجموع آسیب: {total_damage:,.0f} از {total:,.0f}</b>")
                    if stolen:
                        for key,label in resource_labels.items():
                            if key in stolen: private_lines.append(f"• {label}: <b>{stolen[key]:,.0f}</b>")
                    else:
                        private_lines.append("• هیچ منبعی کسب نشد.")
                    if leadership:
                        xp_gain = leadership['gain'] if leadership["attacker_won"] else 0
                        private_lines.append(f"\n👑 <b>تجربه (XP) کسب‌شده: +{xp_gain}</b>")
                    private_result="\n".join(private_lines)
                session.commit()

                if leadership is not None:
                    for country, side in ((attacker, "attacker"), (target, "defender")):
                        before=leadership[f"{side}_rank_before"]; after=leadership[f"{side}_rank_after"]
                        if before[0] != after[0]:
                            direction="⬆️" if after[0] > before[0] else "⬇️"
                            verb="رسیدید" if after[0] > before[0] else "سقوط کردید"
                            text=(f"{direction} <b>{'تبریک! شما به درجه' if after[0] > before[0] else 'شما به درجه'} "
                                  f"{escape(after[1] + ' ' + after[2])}</b> {verb}.\n\n"
                                  f"👑 تجربه رهبری: <b>{float(getattr(country,'leadership_experience',0) or 0):,.0f}</b>")
                            await _notify_user(bot,int(country.leader_user_id),text)

        # پیام شلیک و پیام وضعیت پرواز در گروه هنگام برخورد حذف می‌شوند.
        for message_id in (int(flight.get("launch_message_id",0) or 0), int(flight.get("command_message_id",0) or 0), flight_message_id):
            if message_id:
                try: await bot.delete_message(chat_id=chat_id,message_id=message_id)
                except Exception: pass
        if user_data is not None and flight_token:
            flights=user_data.get("missile_flights") or {}
            flights.pop(flight_token,None)
            if not flights: user_data.pop("missile_flights",None)

        # نتیجه گروه فقط ۳۰ ثانیه بماند.
        group_result_message=await bot.send_message(chat_id=chat_id,text=result,parse_mode="HTML")
        asyncio.create_task(_delete_message_after(bot,chat_id,group_result_message.message_id,30.0))

        # گزارش PV مهاجم دائمی است و هرگز حذف نمی‌شود.
        if private_result and attacker is not None:
            try:
                await bot.send_message(chat_id=int(attacker.leader_user_id),text=private_result,parse_mode="HTML")
            except Exception:
                pass
    except Exception:
        try: await bot.delete_message(chat_id=chat_id,message_id=flight_message_id)
        except Exception: pass
        await bot.send_message(chat_id=chat_id,text="🚀 <b>موشک به مقصد رسید</b>\n\n⚠️ در محاسبه نتیجه حمله خطایی رخ داد.",parse_mode="HTML")


async def _notify_owner_logic_bug(bot, query, detail: str):
    try:
        if not OWNER_ID:
            return
        user = query.from_user
        chat = query.message.chat if query.message else None
        text = query.message.text if query.message else "-"
        report = (
            "🚨 BUG REPORT — رفتار نامعتبر\n\n"
            f"👤 کاربر: {getattr(user,'full_name','نامشخص')}\n"
            f"🆔 User ID: {getattr(user,'id','نامشخص')}\n"
            f"💬 Chat ID: {getattr(chat,'id','نامشخص')}\n"
            f"📍 Chat: {getattr(chat,'type','نامشخص')}\n"
            f"📝 Text: {text[:500] if text else '-'}\n"
            f"🔘 Callback: {getattr(query,'data','-')}\n"
            f"❌ {detail}"
        )
        await bot.send_message(chat_id=int(OWNER_ID), text=report[:4096])
    except Exception:
        pass

def _period_range(period: str):
    local_now=datetime.now(ZoneInfo("Asia/Tehran"))
    now=local_now.astimezone(timezone.utc).replace(tzinfo=None)
    if period == "all": return None, now
    if period == "today":
        start_local=local_now.replace(hour=0,minute=0,second=0,microsecond=0)
        return start_local.astimezone(timezone.utc).replace(tzinfo=None), now
    if period == "yesterday":
        end_local=local_now.replace(hour=0,minute=0,second=0,microsecond=0); start_local=end_local-timedelta(days=1)
        return start_local.astimezone(timezone.utc).replace(tzinfo=None), end_local.astimezone(timezone.utc).replace(tzinfo=None)
    if period == "week":
        start_local=(local_now-timedelta(days=local_now.weekday())).replace(hour=0,minute=0,second=0,microsecond=0)
        return start_local.astimezone(timezone.utc).replace(tzinfo=None), now
    if period == "month":
        start_local=local_now.replace(day=1,hour=0,minute=0,second=0,microsecond=0)
        return start_local.astimezone(timezone.utc).replace(tzinfo=None), now
    if period == "year":
        start_local=local_now.replace(month=1,day=1,hour=0,minute=0,second=0,microsecond=0)
        return start_local.astimezone(timezone.utc).replace(tzinfo=None), now
    return None, now

def _stats_text(session, role: str, period: str) -> str:
    start, end = _period_range(period); now = datetime.utcnow(); users_all = get_users(session)
    admin_ids = {int(a.telegram_id) for a in get_admins(session)}
    if OWNER_ID: admin_ids.add(int(OWNER_ID))
    def in_period(dt): return start is None or bool(dt and start <= dt < end)
    users = [u for u in users_all if in_period(u.created_at)]
    admins = [u for u in users_all if int(u.telegram_id) in admin_ids and in_period(u.created_at)]
    if start is None:
        active = [u for u in users if u.last_active_at and u.last_active_at >= now - timedelta(hours=24)]
        admin_active = [u for u in admins if u.last_active_at and u.last_active_at >= now - timedelta(hours=24)]
    else:
        active = [u for u in users if u.last_active_at and start <= u.last_active_at < end]
        admin_active = [u for u in admins if u.last_active_at and start <= u.last_active_at < end]
    banned = [u for u in users if bool(u.is_banned)]; phone = sum(bool(u.phone_number) for u in users); username = sum(bool(u.username) for u in users)
    def has_country(u):
        return session.scalar(select(UserCountry.id).where(UserCountry.user_id == u.id).limit(1)) is not None
    country = sum(has_country(u) for u in users)
    def invite_total(user_set):
        total = 0
        for u in user_set:
            stmt = select(func.count(User.id)).where(User.referrer_user_id == int(u.telegram_id))
            if start is not None:
                stmt = stmt.where(User.referred_at >= start, User.referred_at < end)
            total += int(session.scalar(stmt) or 0)
        return total
    invites_users = invite_total(users); invites_admins = invite_total(admins)
    if role == "users":
        return (f"👥 <b>آمار کاربران</b> — {_period_label(period)}\n\n" f"👥 تعداد کل کاربران: <b>{len(users):,}</b>\n" f"🟢 کاربران فعال: <b>{len(active):,}</b>\n" f"🚫 کاربران بن‌شده: <b>{len(banned):,}</b>\n" f"📱 کاربران دارای شماره تلفن: <b>{phone:,}</b>\n" f"🔤 کاربران دارای یوزرنیم: <b>{username:,}</b>\n" f"🌍 کاربران دارای کشور: <b>{country:,}</b>\n" f"👥 تعداد دعوت‌ها: <b>{invites_users:,}</b>")
    if role == "admins":
        admin_phone = sum(bool(u.phone_number) for u in admins); admin_username = sum(bool(u.username) for u in admins); admin_country = sum(has_country(u) for u in admins)
        return (f"👨‍💼 <b>آمار ادمین‌ها</b> — {_period_label(period)}\n\n" f"👨‍💼 تعداد کل ادمین‌ها: <b>{len(admins):,}</b>\n" f"🟢 ادمین‌های فعال: <b>{len(admin_active):,}</b>\n" f"📱 ادمین‌های دارای شماره تلفن: <b>{admin_phone:,}</b>\n" f"🔤 ادمین‌های دارای یوزرنیم: <b>{admin_username:,}</b>\n" f"🌍 ادمین‌های دارای کشور: <b>{admin_country:,}</b>\n" f"👥 تعداد دعوت‌ها: <b>{invites_admins:,}</b>")
    return (f"📊 <b>آمار همه</b> — {_period_label(period)}\n\n" f"👥 تعداد کل افراد: <b>{len(users):,}</b>\n" f"🟢 مجموع افراد فعال: <b>{len(active):,}</b>\n" f"📱 مجموع افراد دارای شماره تلفن: <b>{phone:,}</b>\n" f"🔤 مجموع افراد دارای یوزرنیم: <b>{username:,}</b>\n" f"🌍 مجموع افراد دارای کشور: <b>{country:,}</b>\n" f"👥 مجموع دعوت‌ها: <b>{invites_users:,}</b>")

def _period_label(period: str) -> str:
    return {"all":"همه", "today":"امروز", "yesterday":"دیروز", "week":"این هفته", "month":"این ماه", "year":"امسال"}.get(period, "همه")


from services.social_rewards import is_optional_claimed, is_optional_pending, get_optional_pending_entry, optional_timer_markup, optional_timer_text, optional_reward_delay_minutes, optional_claimed_count, scan_existing_optional_memberships, reset_social_item_state, _verified_count

def _social_links_panel_text(session):
    settings = get_social_settings(session)
    items = settings.get("items", [])
    counts = {t: sum(1 for x in items if x.get("type") == t) for t in ("panel", "mandatory_ad", "optional_ad", "chat", "channel")}
    return ("💬 <b>چت، کانال و تبلیغات</b>\n\n"
            "این بخش برای مدیریت لینک‌های بازی است. می‌توانید برای هر بخش هر تعداد مورد که لازم دارید ثبت کنید.\n\n"
            f"🧩 پنل بازی: <b>{counts['panel']}</b> مورد\n"
            f"🚨 تبلیغ اجباری: <b>{counts['mandatory_ad']}</b> مورد\n"
            f"🎁 تبلیغ اختیاری: <b>{counts['optional_ad']}</b> مورد\n"
            f"💬 چت بازی: <b>{counts['chat']}</b> مورد\n"
            f"📣 کانال بازی: <b>{counts['channel']}</b> مورد\n\n"
            "🎁 برای هر تبلیغ اختیاری، پاداش اورانیوم به‌صورت جداگانه تعیین می‌شود.")


def _clear_social_waiting(context):
    for key in ("social_pending", "social_delete_pending"):
        context.user_data.pop(key, None)




async def _send_logged_message(bot, chat_id, item):
    """Re-send a logged broadcast, using the original message first and a durable file_id/text fallback."""
    source_chat_id = item.get("source_chat_id")
    source_message_id = item.get("source_message_id")
    if source_chat_id and source_message_id:
        try:
            result = await bot.copy_message(chat_id=int(chat_id), from_chat_id=int(source_chat_id), message_id=int(source_message_id))
            if result is not None:
                return result
        except Exception:
            pass
    ctype = str(item.get("content_type") or "text")
    file_id = item.get("file_id")
    caption = item.get("text") or item.get("caption") or ""
    if ctype == "text":
        return await bot.send_message(chat_id=int(chat_id), text=caption or "پیام خالی")
    if not file_id:
        return None
    kwargs = {"chat_id": int(chat_id), "caption": caption} if caption else {"chat_id": int(chat_id)}
    if ctype == "photo": return await bot.send_photo(photo=file_id, **kwargs)
    if ctype == "video": return await bot.send_video(video=file_id, **kwargs)
    if ctype == "document": return await bot.send_document(document=file_id, **kwargs)
    if ctype == "audio": return await bot.send_audio(audio=file_id, **kwargs)
    if ctype == "voice": return await bot.send_voice(voice=file_id, **kwargs)
    if ctype == "sticker": return await bot.send_sticker(chat_id=int(chat_id), sticker=file_id)
    if ctype == "animation": return await bot.send_animation(animation=file_id, **kwargs)
    return None


def _message_recipients_text(session, item):
    ids = [int(x) for x in (item.get("recipients") or [])]
    users = {int(u.telegram_id): u for u in get_users(session)}
    lines=[]
    for n, uid in enumerate(ids, 1):
        u=users.get(uid)
        name=(u.first_name if u else None) or (u.username if u else None) or "بدون نام"
        username=("@"+u.username.lstrip("@")) if u and u.username else "ثبت نشده"
        phone=(u.phone_number or "ثبت نشده") if u else "ثبت نشده"
        lines.append((n, uid, name, username, phone))
    return lines

def _render_managed_user_info(session, target):
    """Canonical full user/admin information panel text."""
    countries = get_user_countries(session, target)
    default_country = get_default_country(session, target)
    role = "👑 مالک" if is_owner(target.telegram_id, OWNER_ID) else ("🛡 ادمین" if is_admin(session, target.telegram_id, OWNER_ID) else "👤 کاربر عادی")
    country_lines = "\n".join(
        f"  🌍 {escape(c.title)} — 🎖 تجربه رهبری: <b>{float(c.leadership_experience or 0):,.0f}</b>"
        for c in countries
    ) or "ندارد"
    return (
        "👤 <b>اطلاعات کاربر</b>\n\n"
        f"👤 نام: <b>{escape(target.first_name or target.username or 'بدون نام')}</b>\n"
        f"🆔 آیدی تلگرام: <code>{target.telegram_id}</code>\n"
        f"🔤 نام کاربری: {escape('@'+target.username if target.username else 'ثبت نشده')}\n"
        f"📱 شماره تلفن: {escape(target.phone_number or 'ثبت نشده')}\n"
        f"📝 بیوگرافی: {escape(getattr(target, 'bio', None) or 'ثبت نشده')}\n"
        f"🎭 نقش: <b>{role}</b>\n"
        f"📅 تاریخ عضویت: {target.created_at.strftime('%Y/%m/%d — %H:%M') if target.created_at else 'ثبت نشده'}\n"
        f"🕒 آخرین فعالیت ثبت‌شده: {target.last_active_at.strftime('%Y/%m/%d — %H:%M') if target.last_active_at else 'ثبت نشده'}\n"
        f"🚫 وضعیت حساب: {'مسدود' if target.is_banned else 'فعال'}\n"
        f"📝 دلیل بن: {escape(target.ban_reason or 'ندارد')}\n"
        f"⏳ پایان بن: {target.ban_until.strftime('%Y/%m/%d — %H:%M') if target.ban_until else 'دائمی/ندارد'}\n"
        f"🌍 کشور پیش‌فرض: {escape(default_country.title) if default_country else 'ثبت نشده'}\n\n"
        f"🎮 <b>مشخصات بازی</b>\n🌎 تعداد کشورها: <b>{len(countries)}</b>\n{country_lines}"
    )

BROADCAST_STATE_KEY = "admin_broadcast_resume_v1"
BROADCAST_RUNNING_KEY = "broadcast_running"

async def _broadcast_send_one(bot, uid, state):
    try:
        if state.get("source_message_id"):
            result = await bot.copy_message(
                chat_id=int(uid),
                from_chat_id=int(state["source_chat_id"]),
                message_id=int(state["source_message_id"]),
            )
        else:
            result = await bot.send_message(chat_id=int(uid), text=state.get("text", ""))
        return True if result is not None else False
    except Exception:
        return False


async def _persist_broadcast_state(state):
    try:
        with SessionLocal() as session:
            row = session.scalar(select(BotSetting).where(BotSetting.key == BROADCAST_STATE_KEY))
            if row is None:
                session.add(BotSetting(key=BROADCAST_STATE_KEY, value=json.dumps(state, ensure_ascii=False)))
            else:
                row.value = json.dumps(state, ensure_ascii=False)
            session.commit()
    except Exception:
        pass


async def _update_broadcast_status(bot, state, total, *, final=False):
    ok = int(state.get("success", 0))
    fail = int(state.get("failed", 0))
    done = ok + fail
    waiting = max(0, total - done)
    pct = round(done * 100 / total) if total else 100
    filled = round(pct / 10)
    bar = "🟩" * filled + "⬜" * (10 - filled)
    if final:
        title = "✅ <b>ارسال پیام به پایان رسید</b>"
    else:
        title = "📨 <b>در حال ارسال پیام</b>"
    text = (
        f"{title}\n\n"
        f"🟢 فرستاده شده: <b>{ok}</b> ({round(ok * 100 / total) if total else 0}%)\n"
        f"🔴 فرستاده نشده: <b>{fail}</b> ({round(fail * 100 / total) if total else 0}%)\n"
        f"🟡 در انتظار: <b>{waiting}</b>\n"
        f"📊 همه: <b>{total}</b>\n\n"
        f"{bar} <b>{pct}%</b>"
    )
    chat_id = state.get("status_chat_id")
    message_id = state.get("status_message_id")
    if not chat_id or not message_id:
        return
    try:
        await bot.edit_message_text(chat_id=int(chat_id), message_id=int(message_id), text=text, parse_mode="HTML")
    except Exception:
        pass


async def _run_broadcast_task(app, state):
    """ارسال همگانی با concurrency کنترل‌شده؛ پیام وضعیت هرگز حذف نمی‌شود."""
    total = len(state.get("recipients") or [])
    recipients = [int(x) for x in state.get("recipients", [])]
    start = max(0, int(state.get("next_index", 0)))
    batch_size = 32
    last_status = 0.0
    try:
        for batch_start in range(start, len(recipients), batch_size):
            batch = recipients[batch_start:batch_start + batch_size]
            results = await _asyncio.gather(*[_broadcast_send_one(app.bot, uid, state) for uid in batch])
            for result in results:
                if result:
                    state["success"] = int(state.get("success", 0)) + 1
                else:
                    state["failed"] = int(state.get("failed", 0)) + 1
            state["next_index"] = batch_start + len(batch)
            await _persist_broadcast_state(state)
            now = time.monotonic()
            if now - last_status >= 0.8 or state["next_index"] >= len(recipients):
                await _update_broadcast_status(app.bot, state, total, final=False)
                last_status = now

        state["next_index"] = len(recipients)
        await _persist_broadcast_state(state)
        await _update_broadcast_status(app.bot, state, total, final=True)

        with SessionLocal() as session:
            row = session.scalar(select(BotSetting).where(BotSetting.key == "admin_message_logs_v1"))
            try:
                logs = json.loads(row.value) if row else []
            except Exception:
                logs = []
            pending_text = state.get("text", "") or ""
            logs.append({
                "id": __import__("uuid").uuid4().hex[:10],
                "kind": state.get("kind", "private"),
                "target": state.get("target"),
                "text": pending_text,
                "content_type": state.get("content_type", "text"),
                "file_id": state.get("file_id"),
                "source_message_id": state.get("source_message_id"),
                "sent_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                "sender_id": int(state.get("owner_id", 0)),
                "recipients": recipients,
                "recipients_text": f"{len(set(recipients))} گیرنده",
                "recipient_count": len(set(recipients)),
                "success": int(state.get("success", 0)),
                "failed": int(state.get("failed", 0)),
                "preview": pending_text.replace("\n", " "),
            })
            value = json.dumps(logs, ensure_ascii=False)
            if row is None:
                session.add(BotSetting(key="admin_message_logs_v1", value=value))
            else:
                row.value = value
            session.commit()
        with SessionLocal() as session:
            row = session.scalar(select(BotSetting).where(BotSetting.key == BROADCAST_STATE_KEY))
            if row is not None:
                session.delete(row)
                session.commit()
    finally:
        app.bot_data[BROADCAST_RUNNING_KEY] = False


async def resume_pending_broadcasts(app):
    """پس از Restart، ارسال همگانی نیمه‌تمام را از آخرین checkpoint ادامه می‌دهد."""
    while True:
        state = None
        try:
            with SessionLocal() as session:
                row = session.scalar(select(BotSetting).where(BotSetting.key == BROADCAST_STATE_KEY))
                if row and row.value:
                    state = json.loads(row.value)
        except Exception:
            state = None
        if state and state.get("recipients") and not bool(app.bot_data.get(BROADCAST_RUNNING_KEY)):
            app.bot_data[BROADCAST_RUNNING_KEY] = True
            try:
                await _update_broadcast_status(app.bot, state, len(state.get("recipients", [])), final=False)
                await _run_broadcast_task(app, state)
                try:
                    await app.bot.send_message(
                        chat_id=int(state.get("owner_id", 0)),
                        text=(
                            "♻️ <b>ارسال همگانی پس از راه‌اندازی مجدد ادامه یافت و کامل شد.</b>\n\n"
                            f"🟢 موفق: <b>{int(state.get('success', 0))}</b>\n"
                            f"❌ ناموفق: <b>{int(state.get('failed', 0))}</b>"
                        ),
                        parse_mode="HTML",
                    )
                except Exception:
                    pass
            except Exception:
                app.bot_data[BROADCAST_RUNNING_KEY] = False
        await _asyncio.sleep(5)

async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query is None or query.from_user is None:
        return
    data = resolve_callback_data(query.data or "")
    # دکمه «بررسی عضویت» متعلق به همان کاربری است که گیت برای او ساخته شده است.
    # شناسه کاربر داخل callback ذخیره می‌شود تا در گروه، کاربر دیگری نتواند
    # عضویت شخص دیگر را بررسی/تأیید کند.
    mandatory_check_user_id = None
    if data.startswith("social:mandatory_check"):
        parts = data.split(":")
        if len(parts) == 3 and parts[2].isdigit():
            mandatory_check_user_id = int(parts[2])
        if mandatory_check_user_id is None:
            await query.answer("⛔ این دکمه برای کاربر مشخصی صادر نشده است. دوباره از /start یا دستور ربات استفاده کنید.", show_alert=True)
            return
        if mandatory_check_user_id != int(query.from_user.id):
            await query.answer("⛔ این دکمه فقط برای همان کاربری است که درخواست عضویت را بررسی کرده است.", show_alert=True)
            return
    if query.from_user.is_bot:
        await query.answer("⛔ حساب‌های رباتی اجازه استفاده از این ربات را ندارند.", show_alert=True)
        return

    # جعبه‌های گروهی متعلق به خود گروه هستند و هر عضو باید بتواند پاسخ دهد؛
    # مسیر پاسخ جعبه از قفل مالکیت پنل مستثنی است.
    _public_group_box_callback = str(data).startswith("golden:answer:")
    # سایر پنل‌ها متعلق به همان کاربری هستند که آن‌ها را باز کرده است.
    if query.message is not None and not _public_group_box_callback:
        allowed, owner_id = check_panel(query.message.chat_id, query.message.message_id, query.from_user.id)
        if owner_id is None and (str(data).startswith("owner:") or str(data).startswith("admin:")):
            await query.answer("⛔ این پنل منقضی شده است. پنل را دوباره باز کنید.", show_alert=True)
            return
        if not allowed:
            await query.answer("⛔ این پنل فقط برای شخصی است که آن را باز کرده است.", show_alert=True)
            return
        register_panel(query.message.chat_id, query.message.message_id, query.from_user.id)
    set_panel_owner(query.from_user.id)

    # هر Callback جدید به‌عنوان یک اقدام جدید در نظر گرفته می‌شود.
    # اگر Owner در حال وارد کردن مقدار امنیت/ضداسپم/پشتیبان‌گیری بوده،
    # با زدن هر دکمه یا برگشت، حالت انتظار قبلی فوراً لغو می‌شود.
    # خود دکمه‌های «ویرایش مقدار» پایین‌تر دوباره security_pending را ایجاد می‌کنند.
    context.user_data.pop("security_pending", None)
    # social_pending باید برای دکمه‌های تأیید/تنظیم محدودیت حفظ شود.
    country = None

    with SessionLocal() as session:
        # ---- Global phone/banned security gate ----
        # Owner هرگز به ثبت شماره تلفن نیاز ندارد. برای Admin و کاربران عادی،
        # وضعیت ثبت شماره در لحظه بررسی می‌شود تا حتی Callbackهای قدیمی هم
        # نتوانند بدون ثبت شماره به بخش‌های بازی دسترسی پیدا کنند.
        current_user = get_or_create_user(session, query.from_user)
        # بخش‌های بازی از متغیر user استفاده می‌کنند؛ آن را به کاربر جاری متصل می‌کنیم.
        user = current_user
        if current_user.is_banned:
            session.commit()
            await query.answer("🚫 شما بن شده‌اید؛ جزئیات را در پیام بعدی می‌بینید.", show_alert=True)
            try:
                await query.get_bot().send_message(chat_id=query.from_user.id, text=ban_status_text(current_user), parse_mode="HTML")
            except Exception:
                pass
            return

        owner_user = is_owner(query.from_user.id, OWNER_ID)
        admin_user = is_admin(session, query.from_user.id, OWNER_ID)
        shutdown_mode = get_bot_shutdown_mode(session)
        if not owner_user:
            blocked = (shutdown_mode == "all" or (shutdown_mode == "admins" and admin_user) or (shutdown_mode == "users" and not admin_user))
            if blocked:
                session.commit()
                await query.answer("⏸️ ربات موقتاً خاموش است.", show_alert=True)
                return
        phone_required = phone_required_for(
            session,
            is_admin_user=admin_user,
            is_owner_user=owner_user,
        )
        if phone_required and not current_user.phone_number:
            session.commit()
            await query.answer("📱 ابتدا شماره تلفن خودتان را ثبت کنید.", show_alert=True)
            try:
                await query.get_bot().send_message(
                    chat_id=query.from_user.id,
                    text=(
                        "📱 <b>ثبت شماره تلفن الزامی است</b>\n\n"
                        "برای ادامه استفاده از ربات، مخاطب خودتان را از طریق دکمه زیر ارسال کنید."
                    ),
                    parse_mode="HTML",
                    reply_markup=ReplyKeyboardMarkup(
                        [[KeyboardButton("📱 ثبت شماره تلفن", request_contact=True, style="success")]],
                        resize_keyboard=True,
                        is_persistent=False,
                        one_time_keyboard=False,
                    ),
                )
            except Exception:
                pass
            return

        # ---- بررسی تبلیغات اجباری ----
        # این گیت روی همه Callbackها اعمال می‌شود تا با دکمه‌های قدیمی هم نتوان از الزام عبور کرد.
        if not data.startswith("social:mandatory_check:"):
            mandatory = [x for x in get_active_social_items(session, "mandatory_ad") if str(x.get("url") or "").strip()]
            missing=[]
            for item in mandatory:
                target = item.get("chat_id") or public_chat_target(item.get("url")) or private_message_link_chat_id(item.get("url"))
                ok=False
                if target:
                    try:
                        member=await query.get_bot().get_chat_member(target, query.from_user.id)
                        status=getattr(member,"status","")
                        ok = status in {"member","administrator","creator"} or (status == "restricted" and bool(getattr(member,"is_member",False)))
                    except Exception:
                        # خطای شبکه نباید عضویت قطعی قبلی را به «عضو نیست» تبدیل کند.
                        # در این حالت این مورد را موقتاً نادیده می‌گیریم تا اتصال پایدار شود.
                        continue
                if not ok: missing.append(item)
            if missing:
                rows=[]
                for item in missing:
                    url=social_item_button_url(item.get("url"))
                    if url:
                        rows.append([InlineKeyboardButton(f"🚨 {item.get('title') or item.get('name') or 'ورود به تبلیغ اجباری'}", url=url)])
                rows.append([InlineKeyboardButton("🔄 بررسی عضویت", callback_data=f"social:mandatory_check:{int(query.from_user.id)}")])
                await query.answer("🚨 ابتدا در تبلیغات اجباری عضو شوید.", show_alert=True)
                try:
                    await query.message.reply_text("🚨 <b>عضویت در تبلیغات اجباری</b>\n\nتا زمان عضویت در همه تبلیغات اجباری، استفاده از ربات امکان‌پذیر نیست.", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(rows))
                except Exception:
                    pass
                return

        if data.startswith("social:mandatory_check:"):
            mandatory = [x for x in get_active_social_items(session, "mandatory_ad") if str(x.get("url") or "").strip()]
            missing=[]
            unknown=False
            for item in mandatory:
                target = item.get("chat_id") or public_chat_target(item.get("url")) or private_message_link_chat_id(item.get("url"))
                if not target:
                    missing.append(item)
                    continue
                try:
                    member=await query.get_bot().get_chat_member(target, query.from_user.id)
                    status=getattr(member,"status","")
                    ok = status in {"member","administrator","creator"} or (status == "restricted" and bool(getattr(member,"is_member",False)))
                    if not ok:
                        missing.append(item)
                except Exception:
                    # خطای موقت شبکه را «عضو نیست» حساب نکن؛ این مورد در پنل باقی می‌ماند
                    # تا بررسی بعدی انجام شود، اما مواردی که واقعاً عضو شده‌اند حذف می‌شوند.
                    unknown=True
                    missing.append(item)

            if missing:
                rows=[]
                for item in missing:
                    url=social_item_button_url(item.get("url"))
                    if url:
                        rows.append([InlineKeyboardButton(f"🚨 {item.get('title') or item.get('name') or 'ورود به تبلیغ اجباری'}", url=url)])
                rows.append([InlineKeyboardButton("🔄 بررسی عضویت", callback_data=f"social:mandatory_check:{int(query.from_user.id)}")])
                try:
                    await query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(rows))
                except Exception:
                    pass
                await query.answer(
                    "⚠️ بررسی کامل نشد؛ اتصال را بررسی کنید و دوباره بزنید." if unknown else "❌ هنوز عضویت شما کامل نشده است.",
                    show_alert=True,
                )
                return

            # همه موارد با موفقیت بررسی شدند؛ فقط بعد از تأیید واقعی عضویت ثبت می‌شوند.
            for item in mandatory:
                _mark_verified(session, query.from_user.id, item.get("id"))
                max_members=item.get("max_members")
                if max_members and _verified_count(session,item.get("id")) >= int(max_members):
                    item["active"]=False
                    item["disabled_at"]=datetime.now(timezone.utc).isoformat()
                    item["disabled_reason"]="members"
            all_items=get_social_items(session)
            _save_items(session, all_items)
            session.commit()
            await query.answer("✅ عضویت شما تأیید شد.", show_alert=True)
            try:
                await query.message.delete()
            except Exception: pass
            try:
                await query.get_bot().send_message(chat_id=query.from_user.id, text="✅ <b>عضویت شما تأیید شد.</b>\n\n🔓 دسترسی برای شما فعال شد.", parse_mode="HTML")
            except Exception: pass
            return

        # ---- Missile flight ETA (available to normal users too) ----
        if data == "missile_eta" or data.startswith("missile_eta:"):
            token = data.split(":", 1)[1] if ":" in data else ""
            flight = context.user_data.get("missile_flights", {}).get(token) if token else None
            if not flight and token:
                from services.missile_flights import get as get_persisted_flight
                flight = get_persisted_flight(session, token)
                if flight:
                    context.user_data.setdefault("missile_flights", {})[token] = flight
            if not flight:
                await query.answer("❌ اطلاعات پرواز در دسترس نیست.", show_alert=True); return
            remaining=max(0.0,float(flight.get("arrival_at",0))-time.time())
            if remaining <= 0:
                await query.answer("🚀 موشک به هدف رسیده است.", show_alert=True)
            else:
                await query.answer(f"⏱️ زمان باقی‌مانده: {remaining:,.0f} ثانیه", show_alert=True)
            return

        # ---- Missile launch callbacks (available to normal users too) ----
        if data.startswith("missile_launch_cancel:") or data.startswith("missile_launch_confirm:"):
            action, token = data.split(":", 1)
            pending_all = context.user_data.get("missile_launch_pending") or {}
            pending = pending_all.get(token)
            if not pending:
                await query.answer("❌ این درخواست شلیک دیگر معتبر نیست.", show_alert=True)
                return
            if action == "missile_launch_cancel":
                pending_all.pop(token, None)
                if not pending_all:
                    context.user_data.pop("missile_launch_pending", None)
                await query.answer("❌ شلیک لغو شد.", show_alert=True)
                # پیام تأیید ربات و پیام اصلی شلیک هر دو همان لحظه حذف می‌شوند.
                for message_id in (pending.get("confirmation_message_id"), pending.get("launch_message_id")):
                    if message_id:
                        try:
                            await query.get_bot().delete_message(chat_id=int(pending.get("chat_id", query.message.chat_id)), message_id=int(message_id))
                        except Exception:
                            pass
                return
            try:
                attacker = session.get(Country, int(pending.get("attacker_country_id", 0)))
                target = session.get(Country, int(pending.get("target_country_id", 0)))
                if attacker is None or target is None or int(attacker.leader_user_id) != int(query.from_user.id):
                    pending_all.pop(token, None)
                    if not pending_all: context.user_data.pop("missile_launch_pending", None)
                    await query.answer("❌ اطلاعات شلیک معتبر نیست.", show_alert=True)
                    return
                mid = str(pending.get("missile_id")); level = int(pending.get("level", 1))
                from services.economy import active_for_target as active_shield_for_target, remaining_text as shield_remaining_text
                shield=active_shield_for_target(session, int(target.leader_user_id), getattr(attacker,"continent_name",None), getattr(target,"continent_name",None), int(target.id))
                if shield:
                    text=f"🛡️ <b>شخص سپر فعال دارد.</b>\n\n⏳ زمان باقی‌مانده: <b>{shield_remaining_text(shield.get('expires_at'))}</b>\n❌ این شلیک امکان‌پذیر نیست."
                    pending_all.pop(token, None)
                    if not pending_all: context.user_data.pop("missile_launch_pending", None)
                    await query.answer("🛡️ شخص سپر دارد.", show_alert=True)
                    try:
                        await query.edit_message_text(text,parse_mode="HTML")
                        async def _del_blocked():
                            await _asyncio.sleep(30)
                            for _mid in (int(query.message.message_id), int(pending.get("launch_message_id", 0) or 0)):
                                if not _mid: continue
                                try: await query.get_bot().delete_message(chat_id=int(query.message.chat_id),message_id=_mid)
                                except Exception: pass
                        query.get_bot().create_task(_del_blocked())
                    except Exception: pass
                    return
                inv = get_missile_inventory(session, attacker.id)
                if get_missile_count(inv, mid, level) <= 0:
                    await query.answer("❌ این موشک دیگر در زرادخانه شما موجود نیست.", show_alert=True)
                    try:
                        await query.edit_message_text("❌ <b>این موشک دیگر در زرادخانه شما موجود نیست.</b>", parse_mode="HTML", reply_markup=None)
                        async def _del_missing_missile():
                            await _asyncio.sleep(30)
                            for _mid in (int(query.message.message_id), int(pending.get("launch_message_id",0) or 0)):
                                try: await query.get_bot().delete_message(chat_id=int(query.message.chat_id),message_id=_mid)
                                except Exception: pass
                        query.get_bot().create_task(_del_missing_missile())
                    except Exception: pass
                    pending_all.pop(token, None)
                    if not pending_all: context.user_data.pop("missile_launch_pending", None)
                    return
                # موشک دقیقاً در لحظه تأیید شلیک از زرادخانه مصرف می‌شود؛
                # رسیدن موشک به هدف نباید باعث کسر موجودی شود.
                missile_cfg = get_missiles_config(session)
                missile_obj = next((m for m in missile_cfg.get("items", []) if str(m.get("id")) == mid), {})
                missile_capacity = float(missile_obj.get("base_capacity", 0) or 0)
                add_missile_to_inventory(session, attacker.id, mid, level, -1)
                attacker.missiles=max(0,int(getattr(attacker,"missiles",0) or 0)-1)
                attacker.arsenal_storage=max(0.0,float(getattr(attacker,"arsenal_storage",0) or 0)-missile_capacity)
                session.flush()
                missile_name = str(missile_obj.get("name", "موشک"))
                delay = max(0.0, float(pending.get("target_time", 0) or 0))
                pending_all.pop(token, None)
                if not pending_all: context.user_data.pop("missile_launch_pending", None)
                arrival_at=time.time()+delay
                # اگر مهاجم در گروه سپر فعال داشته باشد، مقدار قابل تنظیمی از آن کم می‌شود.
                if int(pending.get("chat_id",0) or 0) == int(getattr(query.message,"chat_id",0) or 0):
                    consume_shield_time_for_group_attack(session, int(attacker.leader_user_id), int(attacker.id))
                # هر شلیک تأییدشده در گروه برای شمارنده دریافت حمله هدف ثبت می‌شود.
                auto_granted, auto_expires = register_group_attack_received(session, int(target.leader_user_id), int(pending.get("chat_id",0) or 0), int(target.id))
                session.commit()
                loot_percent=get_global_loot_percent(session)
                flight={"attacker_country_id":int(attacker.id),"target_country_id":int(target.id),"missile_id":mid,"level":level,"power":float(pending.get("power",0) or 0),"target_time":delay,"loot_percent":loot_percent,"attacker_name":str(attacker.leader_name or attacker.title),"target_name":str(target.leader_name or target.title),"missile_name":missile_name,"chat_id":int(query.message.chat_id if query.message else pending.get("chat_id")),"message_id":int(query.message.message_id if query.message else 0),"command_message_id":int(pending.get("launch_message_id",0) or 0),"launch_message_id":0,"arrival_at":arrival_at}
                flight_token = token
                flights=context.user_data.setdefault("missile_flights", {})
                flights[flight_token]=flight
                from services.missile_flights import put as persist_missile_flight
                persist_missile_flight(session, flight_token, flight)
                session.commit()
                await query.answer()
                # پیام تأیید شلیک و خود دستور شلیک کاربر باید بعد از تأیید حذف شوند؛
                # سپس استیکر موشک و پیام وضعیت شلیک ارسال می‌شوند.
                chat_id = int(pending.get("chat_id") or query.message.chat_id)
                for _message_id in (int(query.message.message_id), int(pending.get("launch_message_id", 0) or 0)):
                    if not _message_id:
                        continue
                    try:
                        await query.get_bot().delete_message(chat_id=chat_id, message_id=_message_id)
                    except Exception:
                        pass
                launch_sticker = str(missile_obj.get("launch_sticker") or "").strip()
                if launch_sticker:
                    try:
                        await query.get_bot().send_sticker(chat_id=chat_id, sticker=launch_sticker)
                    except Exception:
                        pass
                try:
                    launch_status_message = await query.get_bot().send_message(
                        chat_id=chat_id,
                        text=f"🚀 <b>حمله آغاز شد</b>\n\n⚔️ <b>تسلیحات</b>\n🚀 موشک: <b>{escape(missile_name)}</b>\n💥 قدرت: <b>{float(pending.get('power',0) or 0):,.0f}</b>\n🎯 هدف: <b>{escape(str(target.title))}</b>",
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏱️ زمان برخورد با هدف", callback_data=f"missile_eta:{flight_token}")]])
                    )
                    flight["launch_message_id"] = int(launch_status_message.message_id)
                    try:
                        with SessionLocal() as _persist_session:
                            from services.missile_flights import put as _persist_put
                            _persist_put(_persist_session, flight_token, flight)
                            _persist_session.commit()
                    except Exception:
                        pass
                except Exception:
                    pass
                context.application.create_task(_resolve_missile_flight(query.get_bot(),flight, context.user_data, flight_token))
            except Exception:
                session.rollback()
                await query.answer("❌ انجام شلیک با خطا مواجه شد.", show_alert=True)
            return

        # ---- صفحه‌بندی لیدربورد ----
        if data.startswith("leaderboard:"):
            await leaderboard_callback(update, context)
            return

        # ---- انیگما ----
        if data.startswith("enigma:"):
            parts=data.split(":")
            action=parts[1] if len(parts)>1 else ""; token=parts[2] if len(parts)>2 else ""
            if action == "start":
                result,err=enigma_start(session,token,query.from_user.id)
                if err: await query.answer(err,show_alert=True); return
                await query.answer("🔓 عملیات استخراج کد آغاز شد.")
                # با شروع مأموریت، سنجاق جعبه اولیه برداشته می‌شود؛ از اینجا به بعد
                # همان پیام به‌عنوان پنل مأموریت استفاده می‌شود.
                try:
                    await context.bot.unpin_chat_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
                except Exception:
                    pass
                msg=await query.edit_message_text(result['text'],parse_mode='HTML',reply_markup=result['markup'])
                rec=enigma_state(session).get('active',{}).get(token)
                if rec and msg:
                    rec['message_id']=msg.message_id; rec['chat_id']=msg.chat_id
                    enigma_set(session,'state',enigma_state(session))
                return
            if action == 'answerpanel':
                rec=enigma_reveal_answer_panel(session,token,query.from_user.id)
                if not rec: await query.answer('این عملیات دیگر فعال نیست.',show_alert=True); return
                panel=enigma_render_answer_panel(session,token,query.from_user.id)
                await query.answer('پنل پاسخگویی باز شد.')
                old_chat_id=query.message.chat_id
                old_message_id=query.message.message_id
                try: await context.bot.unpin_chat_message(chat_id=old_chat_id, message_id=old_message_id)
                except Exception: pass
                # همان پیام سؤال را ویرایش کن تا Scheduler و Callback پیام دوم نسازند.
                await query.edit_message_text(panel['text'],parse_mode='HTML',reply_markup=panel['markup'])
                rec['message_id']=old_message_id; rec['chat_id']=old_chat_id
                enigma_set(session,'state',enigma_state(session)); session.commit()
                return
            if action == "key":
                k=parts[3] if len(parts)>3 else ""
                rec0=enigma_state(session).get('active',{}).get(token,{})
                if not rec0.get('answer_panel'):
                    # اگر زمان نمایش سؤال تمام شده ولی Worker هنوز همان لحظه را پردازش نکرده،
                    # همین کلیک باید پنل را باز کند تا کاربر هرگز با «هنوز باز نشده» مواجه نشود.
                    q_until=rec0.get('question_until')
                    try:
                        q_due = q_until and datetime.fromisoformat(str(q_until)) <= datetime.utcnow()
                    except Exception:
                        q_due = False
                    if q_due:
                        opened=enigma_reveal_answer_panel(session,token,query.from_user.id)
                        if opened:
                            rec0=opened
                    if not rec0.get('answer_panel'):
                        # اگر Worker دقیقاً هم‌زمان با کلیک کاربر در حال انتقال بود،
                        # خود callback انتقال را تکمیل می‌کند تا هیچ کلیک معتبری با خطای
                        # «پنل پاسخگویی هنوز باز نشده است» مواجه نشود.
                        opened=enigma_reveal_answer_panel(session,token,query.from_user.id)
                        if opened:
                            rec0=opened
                        else:
                            await query.answer("⏳ پنل پاسخگویی هنوز باز نشده است.",show_alert=True); return
                value=enigma_key(session,token,query.from_user.id,k)
                if value is None: await query.answer("❌ این عملیات فعال نیست.",show_alert=True); return
                rec=enigma_state(session).get('active',{}).get(token,{})
                page=int(context.user_data.get(f'enigma_page_{token}',0))
                # دکمه‌های کیبورد فقط در پنل پاسخگویی عمل می‌کنند؛
                # هرگز پیام را به نمای سؤال برنمی‌گردانند.
                panel=enigma_render_answer_panel(session,token,query.from_user.id)
                if not panel:
                    await query.answer("❌ پنل پاسخگویی دیگر فعال نیست.",show_alert=True); return
                await query.answer()
                await query.edit_message_text(panel['text'],parse_mode='HTML',reply_markup=answer_keyboard(token,page=page))

            if action == "page":
                page=int(parts[3]); context.user_data[f'enigma_page_{token}']=page; await query.answer(); await query.edit_message_reply_markup(reply_markup=answer_keyboard(token,space=True,page=page)); return
            if action == "submit":
                result,err=enigma_submit(session,token,query.from_user.id)
                if err: await query.answer(err,show_alert=True); return
                if result.get('expired'):
                    from enigma.messages import EXPIRE
                    try:
                        await context.bot.unpin_chat_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
                    except Exception:
                        pass
                    await query.answer("⏱ زمان عملیات تمام شد.",show_alert=True); await query.edit_message_text(EXPIRE,parse_mode='HTML',reply_markup=None); return
                if result.get('empty'):
                    await query.answer('لطفاً پاسخ را وارد کنید و بعد تأیید کنید.',show_alert=True); return
                if result.get('wrong'):
                    await query.answer(f"❌ پاسخ اشتباه است. تلاش باقی‌مانده: {result['remaining']}",show_alert=True); return
                if result.get('failed'):
                    from enigma.messages import FAIL
                    try:
                        await context.bot.unpin_chat_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
                    except Exception:
                        pass
                    await query.answer("❌ عملیات شکست خورد.",show_alert=True); await query.edit_message_text(FAIL,parse_mode='HTML',reply_markup=None); return
                if result.get('success'):
                    rec_done=enigma_state(session).get('active',{}).get(token,{})
                    if not rec_done.get('sample'):
                        grant_reward(session,query.from_user.id,int(rec_done.get('country_id',0)),'uranium',result['reward'])
                    from enigma.messages import SUCCESS
                    try:
                        await context.bot.unpin_chat_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
                    except Exception:
                        pass
                    completion_note = "\n\n🏁 <b>شما تمام چالش‌های انیگمای ربات را تمام کردید.</b>\nاز این پس چالش دیگری برای شما ارسال نمی‌شود، مگر اینکه Owner چالش جدیدی اضافه/فعال کند یا چرخه مأموریت‌ها را ریست کند." if result.get('all_done') else ''
                    await query.answer("🎖 رمزگشایی موفق بود.",show_alert=True); await query.edit_message_text(SUCCESS+f"\n\n☢️ اورانیوم: <b>{result['reward']:,.2f}</b>"+completion_note,parse_mode='HTML',reply_markup=None); return
            if action == "cancel":
                s=enigma_state(session); rec=s.get('active',{}).get(token)
                if rec: rec['status']=STATUS_FAILED; enigma_set(session,'state',s)
                await query.answer("عملیات بسته شد.",show_alert=True); await query.delete_message(); return
            return

        # ---- Admin / Owner security boundary ----
        if data.startswith(("admin:", "owner:")):
            if not is_admin(session, query.from_user.id, OWNER_ID):
                await query.answer("⛔ دسترسی غیرمجاز است.", show_alert=True)
                return

            parts = data.split(":")
            namespace = parts[0]
            action = parts[1] if len(parts) > 1 else ""

            # admin: مسیرهای پنل ادمین و owner: مسیرهای پنل Owner هستند.
            # Owner علاوه بر owner: می‌تواند همه admin:ها را هم اجرا کند؛ Admin به owner: دسترسی ندارد.
            if namespace == "owner" and not owner_user:
                await query.answer("⛔ این بخش فقط برای مالک است.", show_alert=True)
                return
            if namespace == "admin" and not admin_user:
                await query.answer("⛔ دسترسی غیرمجاز است.", show_alert=True)
                return

            # مالک همیشه دسترسی کامل دارد؛ مدیران بر اساس مجوزهای اختصاصی کنترل می‌شوند.
            permission_map = {"users":"users", "user_access":"users", "balance_change":"users", "population_change":"users", "population_mode":"users", "search_users":"user_search", "search_banned":"user_search", "admin_account_settings":"user_account_settings", "admin_account_info":"user_info", "stats":"stats", "stats_all":"stats", "messages":"messages", "message_private":"message_private", "message_public":"message_public", "message_lists":"messages", "message_list":"message_lists_private", "message_list_private":"message_lists_private", "message_list_public":"message_lists_public", "stats_period":"stats"}
            required_perm = permission_map.get(action)
            granular_perm = {
                "user_balance":"balance_change", "balance_change":"balance_change", "balance_search_confirm":"balance_change", "balance_add":"balance_change", "balance_remove":"balance_change", "balance_users_done":"balance_change", "balance_country_pick":"balance_change", "balance_resource":"balance_change", "balance_infinite":"balance_change", "balance_continue":"balance_change", "balance_finish":"balance_change", "balance_commit":"balance_change",
                "population_change":"users", "population_mode":"users", "population_add":"users", "population_remove":"users", "population_add_single":"users", "population_remove_single":"users", "population_add_multiple":"users", "population_remove_multiple":"users", "population_search_confirm":"users", "population_user_search_back":"users", "population_single_search_back":"users", "population_country_pick":"users", "population_users_done":"users", "population_amount_back":"users", "population_commit":"users",
                "user_country_edit":"country_name", "user_country_delete":"delete_country", "user_country_delete_pick":"delete_country", "user_country_delete_confirm":"delete_country", "user_country_delete_cancel":"delete_country",
                "user_swap":"swap_countries", "swap_from":"swap_countries", "swap_to":"swap_countries", "swap_confirm":"swap_countries", "swap_confirm_cancel":"swap_countries",
                "user_swap_reset":"reset_swap", "user_swap_reset_confirm":"reset_swap",
                "user_game_settings":"game_settings", "user_game_specs":"game_specs", "user_game_country":"game_specs", "user_game_population":"game_specs", "user_game_population_mode":"game_specs", "user_game_population_confirm":"game_specs",
                "user_leadership_country":"game_specs", "user_leadership_mode":"game_specs",
            }.get(action)
            required_perm = granular_perm or required_perm
            if required_perm and not owner_user and not admin_has_permission(session, query.from_user.id, OWNER_ID, required_perm):
                await query.answer("🔒 دسترسی محدود شد.", show_alert=True); return

            if not data.startswith("exchange"):
                context.user_data.pop("pending_exchange", None)
            _navigation_actions = {"back","cancel","initial_settings","economy","game_management","buildings","economy_hq","economy_metal_mine","economy_arsenal","economy_bank","missiles","shields","leadership_settings","country_rename_cost","installment_settings","security","general_settings","user_tools","messages","admin_panel","owner_panel","owner"}
            if any(token in data.lower() for token in (":back",":cancel","_cancel")) or action in _navigation_actions or action.endswith("_back"):
                for _key in ("economy_pending","owner_economy_confirm","exchange_rate_pending","exchange_text_pending","exchange_text_draft","pending_exchange","missile_pending","missile_draft","missile_operational_pending","social_pending","social_delete_pending","admin_pending","admin_leadership_pending","admin_leadership_bulk_pending","shield_adjust_pending","shield_reset_pending","shield_add_pending","shield_edit_pending","shield_auto_setting_pending","security_pending","bank_pending","golden_pending","enigma_pending","swap_pending","country_edit_waiting","country_edit_name","country_edit","self_country_edit","self_country_edit_name","arsenal_sell_pending","arsenal_sell_custom_pending","balance_pending","population_pending","population_selected_user","user_game_population_pending","user_game_population_confirm","admin_message_pending"):
                    context.user_data.pop(_key,None); context.user_data.pop(_waiting_scope_key(_key),None)

            # ---------------- تنظیم سپر کاربران ----------------
            if action in {"shield_manage", "user_shield_manage"} or action.startswith("shield_"):
                if not owner_user and not admin_has_permission(session, query.from_user.id, OWNER_ID, "game_settings"):
                    await query.answer("🔒 دسترسی محدود شد.", show_alert=True); return

                if action == "shield_manage":
                    context.user_data.pop("shield_adjust_pending", None); context.user_data.pop("shield_reset_pending", None)
                    await query.answer(); await query.edit_message_text("🛡️ <b>تنظیم سپر کاربران</b>\n\nنوع عملیات را انتخاب کنید:", parse_mode="HTML", reply_markup=shield_user_sign_keyboard("admin:user_tools")); return

                if action == "user_shield_manage" and len(parts)>=3:
                    target_id=int(parts[2]); target=get_user_by_telegram_id(session,target_id)
                    if not target: await query.answer("❌ کاربر پیدا نشد.",show_alert=True); return
                    countries=get_user_countries(session,target)
                    if not countries: await query.answer("⚠️ این کاربر کشوری ندارد.",show_alert=True); return
                    await query.answer(); await query.edit_message_text("🛡️ <b>انتخاب کشور برای تنظیم سپر</b>",parse_mode="HTML",reply_markup=shield_user_country_keyboard(target_id,countries,"manage",f"admin:user:{target_id}")); return

                if action == "shield_pick_country" and len(parts)>=4:
                    target_id,country_id=int(parts[2]),int(parts[3]); pending=context.user_data.get("shield_adjust_pending") or {}
                    target=get_user_by_telegram_id(session,target_id); country=session.get(CountryModel,country_id)
                    if not target or not country or country.id not in {c.id for c in get_user_countries(session,target)}:
                        await query.answer("❌ کشور نامعتبر است.",show_alert=True); return
                    if any(isinstance(x,dict) and int(x.get("user_id"))==target_id and int(x.get("country_id"))==country_id for x in pending.get("users",[])):
                        await query.answer("⚠️ این کشور قبلاً انتخاب شده است.",show_alert=True); return
                    pending.setdefault("users",[]).append({"user_id":target_id,"country_id":country_id}); pending.pop("pending_country_user_id",None); context.user_data["shield_adjust_pending"]=pending
                    await query.answer("✅ کشور انتخاب شد.")
                    if pending.get("mode") == "single":
                        await query.edit_message_text("🛡️ <b>نوع سپر</b>\n\nنوع سپر موردنظر را انتخاب کنید:",parse_mode="HTML",reply_markup=shield_user_type_keyboard(pending.get("sign"),pending.get("back_callback","admin:user_tools")))
                    else:
                        await query.edit_message_text(f"✅ <b>{escape(target.first_name or target.username or str(target_id))}</b> — 🌍 <b>{escape(country.title)}</b> انتخاب شد.\n\nکاربر بعدی را ارسال کنید یا پایان انتخاب را بزنید.",parse_mode="HTML",reply_markup=shield_user_multiple_keyboard(pending.get("sign"),True,pending.get("back_callback","admin:user_tools")))
                    return

                if action == "shield_reset_pick_country" and len(parts)>=4:
                    target_id,country_id=int(parts[2]),int(parts[3]); pending=context.user_data.get("shield_reset_pending") or {}
                    target=get_user_by_telegram_id(session,target_id); country=session.get(CountryModel,country_id)
                    if not target or not country or country.id not in {c.id for c in get_user_countries(session,target)}:
                        await query.answer("❌ کشور نامعتبر است.",show_alert=True); return
                    pending.setdefault("users",[]).append({"user_id":target_id,"country_id":country_id}); pending.pop("pending_country_user_id",None); context.user_data["shield_reset_pending"]=pending
                    await query.answer("✅ کشور انتخاب شد.")
                    if pending.get("mode")=="single":
                        await query.edit_message_text("♻️ <b>تأیید ریست محدودیت خرید</b>\n\nمحدودیت خرید همین کشور صفر می‌شود. ادامه می‌دهید؟",parse_mode="HTML",reply_markup=shield_reset_confirm_keyboard())
                    else:
                        await query.edit_message_text(f"✅ <b>{escape(country.title)}</b> انتخاب شد.\n\nکاربر بعدی را ارسال کنید یا پایان انتخاب را بزنید.",parse_mode="HTML",reply_markup=shield_reset_multiple_keyboard(True))
                    return

                if action == "shield_country" and len(parts)>=5:
                    target_id,country_id,mode=int(parts[2]),int(parts[3]),parts[4]
                    target=get_user_by_telegram_id(session,target_id); country=session.get(CountryModel,country_id)
                    if not target or not country or country.id not in {c.id for c in get_user_countries(session,target)}:
                        await query.answer("❌ کشور نامعتبر است.",show_alert=True); return
                    context.user_data["shield_adjust_pending"]={"users":[{"user_id":target_id,"country_id":country_id}],"mode":"single","back_callback":f"admin:user_game_country:{target_id}:{country_id}","prompt_chat_id":int(query.message.chat_id),"prompt_message_id":int(query.message.message_id)}
                    context.user_data[_waiting_scope_key("shield_adjust_pending")]=int(update.effective_chat.id)
                    await query.answer(); await query.edit_message_text(f"🛡️ <b>تنظیم سپر کشور {escape(country.title)}</b>\n\nافزایش یا کاهش مقدار سپر را انتخاب کنید:",parse_mode="HTML",reply_markup=shield_user_sign_keyboard(f"admin:user_game_country:{target_id}:{country_id}", f"admin:shield_country_reset:{target_id}:{country_id}")); return

                if action == "shield_country_reset" and len(parts)>=4:
                    target_id,country_id=int(parts[2]),int(parts[3]); target=get_user_by_telegram_id(session,target_id); country=session.get(CountryModel,country_id)
                    if not target or not country or country.id not in {c.id for c in get_user_countries(session,target)}:
                        await query.answer("❌ کشور نامعتبر است.",show_alert=True); return
                    # این مسیر مخصوص یک کاربر/یک کشور است؛ نباید وارد انتخاب تک‌نفره/چندنفره شود.
                    # ابتدا تأیید می‌گیریم و فقط پس از تأیید محدودیت همان کاربر در همان کشور را ریست می‌کنیم.
                    context.user_data["shield_reset_pending"]={
                        "mode":"single",
                        "users":[{"user_id":target_id,"country_id":country_id}],
                        "back_callback":f"admin:user_game_country:{target_id}:{country_id}",
                    }
                    context.user_data[_waiting_scope_key("shield_reset_pending")]=int(update.effective_chat.id)
                    await query.answer()
                    await query.edit_message_text(
                        f"♻️ <b>تأیید ریست محدودیت خرید</b>\n\n"
                        f"کاربر: <code>{target_id}</code>\n"
                        f"کشور: <b>{escape(country.title)}</b>\n\n"
                        "آیا می‌خواهید محدودیت خرید این کاربر را در این کشور ریست کنید؟",
                        parse_mode="HTML", reply_markup=shield_reset_confirm_keyboard()
                    )
                    return

                if action == "shield_reset_user" and len(parts)>=3:
                    target_id=int(parts[2]); target=get_user_by_telegram_id(session,target_id)
                    if not target: await query.answer("❌ کاربر پیدا نشد.",show_alert=True); return
                    countries=get_user_countries(session,target)
                    if not countries: await query.answer("⚠️ این کاربر کشوری ندارد.",show_alert=True); return
                    await query.answer(); await query.edit_message_text("🛡️ <b>کشور موردنظر را برای تنظیم سپر انتخاب کنید</b>",parse_mode="HTML",reply_markup=shield_user_country_keyboard(target_id,countries,"manage",f"admin:user:{target_id}")); return

                if action == "shield_sign" and len(parts)>=3:
                    sign=parts[2]
                    if sign not in {"add","remove"}: await query.answer("❌ عملیات نامعتبر است.",show_alert=True); return
                    pending=context.user_data.get("shield_adjust_pending") or {}
                    pending["sign"]=sign; pending.setdefault("users",[]); pending.setdefault("back_callback","admin:user_tools")
                    context.user_data["shield_adjust_pending"]=pending; context.user_data[_waiting_scope_key("shield_adjust_pending")]=int(update.effective_chat.id)
                    if pending.get("mode")=="single" and pending.get("users"):
                        await query.answer(); await query.edit_message_text("🛡️ <b>نوع سپر</b>\n\nنوع سپر موردنظر را انتخاب کنید:",parse_mode="HTML",reply_markup=shield_user_type_keyboard(sign,pending["back_callback"])); return
                    await query.answer(); await query.edit_message_text(f"{'➕ افزایش' if sign=='add' else '➖ کاهش'} سپر\n\nحالت عملیات را انتخاب کنید:",parse_mode="HTML",reply_markup=shield_user_mode_keyboard(sign,pending.get("back_callback","admin:user_tools"))); return

                if action == "shield_mode" and len(parts)>=3:
                    sign=parts[2]; mode=parts[3] if len(parts)>=4 else ""
                    pending=context.user_data.get("shield_adjust_pending") or {}
                    if mode=="back":
                        context.user_data.pop("shield_adjust_pending",None); context.user_data.pop(_waiting_scope_key("shield_adjust_pending"),None)
                        await query.answer(); await query.edit_message_text("🛡️ <b>تنظیم سپر کاربران</b>\n\nنوع عملیات را انتخاب کنید:",parse_mode="HTML",reply_markup=shield_user_sign_keyboard("admin:user_tools")); return
                    pending.update({"sign":sign,"mode":mode}); pending.setdefault("users",[])
                    context.user_data["shield_adjust_pending"]=pending; context.user_data[_waiting_scope_key("shield_adjust_pending")]=int(update.effective_chat.id)
                    if mode=="single" and not pending.get("users"):
                        await query.answer(); await query.edit_message_text("👤 <b>کاربر را وارد کنید</b>\n\nنام کشور، شماره تلفن، نام کاربری با @ یا آیدی عددی را ارسال کنید:",parse_mode="HTML",reply_markup=shield_user_multiple_keyboard(sign,False)); return
                    if mode=="multiple":
                        await query.answer(); await query.edit_message_text("👥 <b>انتخاب کاربران</b>\n\nکاربر را با نام کشور، شماره تلفن، نام کاربری با @ یا آیدی عددی ارسال کنید:",parse_mode="HTML",reply_markup=shield_user_multiple_keyboard(sign,bool(pending.get("users")))); return
                    await query.answer(); await query.edit_message_text("🛡️ <b>نوع سپر</b>\n\nنوع سپر موردنظر را انتخاب کنید:",parse_mode="HTML",reply_markup=shield_user_type_keyboard(sign,pending.get("back_callback","admin:user_tools"))); return

                if action == "shield_users_done":
                    pending=context.user_data.get("shield_adjust_pending") or {}
                    if pending.get("mode")!="multiple" or not pending.get("users"):
                        await query.answer("⚠️ حداقل یک کاربر انتخاب کنید.",show_alert=True); return
                    await query.answer(); await query.edit_message_text("🛡️ <b>نوع سپر</b>\n\nنوع سپر موردنظر را انتخاب کنید:",parse_mode="HTML",reply_markup=shield_user_type_keyboard(pending.get("sign"),pending.get("back_callback","admin:user_tools"))); return

                if action == "shield_type" and len(parts)>=4:
                    sign,typ=parts[2],parts[3]; pending=context.user_data.get("shield_adjust_pending") or {}
                    if sign not in {"add","remove"} or typ not in {"global","continental"}: await query.answer("❌ گزینه نامعتبر است.",show_alert=True); return
                    pending.update({"sign":sign,"shield_type":typ,"prompt_chat_id":int(query.message.chat_id),"prompt_message_id":int(query.message.message_id)}); context.user_data["shield_adjust_pending"]=pending; context.user_data[_waiting_scope_key("shield_adjust_pending")]=int(update.effective_chat.id)
                    await query.answer(); await query.edit_message_text(f"{'➕ افزایش' if sign=='add' else '➖ کاهش'} {'سپر جهانی' if typ=='global' else 'سپر قاره‌ای'}\n\nمقدار تغییر را به <b>ساعت</b> ارسال کنید:",parse_mode="HTML",reply_markup=shield_user_amount_keyboard(sign,typ,pending.get("back_callback","admin:user_tools"))); return

                if action == "shield_adjust_back":
                    pending=context.user_data.get("shield_adjust_pending") or {}; back=pending.get("back_callback","admin:user_tools")
                    context.user_data.pop("shield_adjust_pending",None); context.user_data.pop(_waiting_scope_key("shield_adjust_pending"),None)
                    await query.answer("🔙 برگشت")
                    if str(back).startswith("admin:user_game_settings:"):
                        tid=int(str(back).split(":")[2])
                        await query.edit_message_text("⚙️ <b>تنظیمات بازی کاربر</b>",parse_mode="HTML",reply_markup=admin_user_game_settings_keyboard(tid,context.user_data.get("user_game_settings_back",f"admin:user:{tid}")))
                    else:
                        await query.edit_message_text("🛡️ <b>تنظیم سپر کاربران</b>\n\nنوع عملیات را انتخاب کنید:",parse_mode="HTML",reply_markup=shield_user_sign_keyboard(back))
                    return

                if action == "shield_adjust_cancel":
                    pending=context.user_data.get("shield_adjust_pending") or {}; back=pending.get("back_callback","admin:user_tools")
                    context.user_data.pop("shield_adjust_pending",None); context.user_data.pop(_waiting_scope_key("shield_adjust_pending"),None)
                    await query.answer("لغو شد."); await query.edit_message_text("🛡️ <b>تنظیم سپر کاربران</b>\n\nنوع عملیات را انتخاب کنید:",parse_mode="HTML",reply_markup=shield_user_sign_keyboard(back)); return

                if action == "shield_adjust_confirm":
                    pending=context.user_data.get("shield_adjust_pending") or {}; amount=float(pending.get("amount",0) or 0)
                    if not pending.get("users") or amount<=0 or pending.get("shield_type") not in {"global","continental"}: await query.answer("❌ اطلاعات عملیات کامل نیست.",show_alert=True); return
                    delta=amount if pending.get("sign")=="add" else -amount
                    for entry in pending["users"]:
                        if isinstance(entry,dict): adjust_active_shield_time(session,int(entry.get("user_id")),pending["shield_type"],delta,int(entry.get("country_id")))
                        else: adjust_active_shield_time(session,int(entry),pending["shield_type"],delta,None)
                    users_text="\n".join(f"🆔 <code>{(entry.get('user_id') if isinstance(entry,dict) else entry)}</code>" for entry in pending["users"])
                    typ="سپر جهانی" if pending["shield_type"]=="global" else "سپر قاره‌ای"; sign_text="افزایش" if delta>0 else "کاهش"
                    back=pending.get("back_callback","admin:user_tools")
                    context.user_data.pop("shield_adjust_pending",None); context.user_data.pop(_waiting_scope_key("shield_adjust_pending"),None)
                    await query.answer("✅ تغییر سپر انجام شد.",show_alert=True)
                    if str(back).startswith("admin:user_game_country:"):
                        pieces=str(back).split(":")
                        if len(pieces) >= 4:
                            panel_text, panel_markup = _user_game_country_panel(session, int(pieces[2]), int(pieces[3]), str(back))
                            if panel_text:
                                await query.edit_message_text(panel_text, parse_mode="HTML", reply_markup=panel_markup)
                                return
                    await query.edit_message_text(f"🛡️ <b>تغییر سپر انجام شد</b>\n\n{users_text}\n\n{typ}: <b>{sign_text} {amount:g} ساعت</b>",parse_mode="HTML",reply_markup=shield_user_sign_keyboard(back)); return

                if action == "shield_reset_select":
                    await query.answer(); await query.edit_message_text("♻️ <b>ریست محدودیت خرید سپر</b>\n\nحالت انتخاب کاربر را مشخص کنید:",parse_mode="HTML",reply_markup=shield_reset_mode_keyboard()); return

                if action == "shield_reset_mode" and len(parts)>=3:
                    mode=parts[2]; pending={"mode":mode,"users":[]}; context.user_data["shield_reset_pending"]=pending; context.user_data[_waiting_scope_key("shield_reset_pending")]=int(update.effective_chat.id)
                    if mode=="single":
                        await query.answer(); await query.edit_message_text("👤 <b>کاربر را وارد کنید</b>\n\nنام کشور، شماره تلفن، نام کاربری با @ یا آیدی عددی را ارسال کنید:",parse_mode="HTML",reply_markup=shield_reset_multiple_keyboard(False)); return
                    await query.answer(); await query.edit_message_text("👥 <b>انتخاب کاربران</b>\n\nکاربر را ارسال کنید:",parse_mode="HTML",reply_markup=shield_reset_multiple_keyboard(False)); return

                if action == "shield_reset_add":
                    pending=context.user_data.get("shield_reset_pending") or {}; pending["mode"]="multiple"; context.user_data["shield_reset_pending"]=pending; context.user_data[_waiting_scope_key("shield_reset_pending")]=int(update.effective_chat.id)
                    await query.answer(); return

                if action == "shield_reset_done":
                    pending=context.user_data.get("shield_reset_pending") or {}
                    if not pending.get("users"): await query.answer("⚠️ حداقل یک کاربر انتخاب کنید.",show_alert=True); return
                    await query.answer(); await query.edit_message_text(f"♻️ <b>تأیید ریست محدودیت خرید</b>\n\nتعداد کاربران: <b>{len(pending['users'])}</b>\n\nتمام محدودیت‌های خرید سپر این کاربران صفر می‌شود. ادامه می‌دهید؟",parse_mode="HTML",reply_markup=shield_reset_confirm_keyboard()); return

                if action == "shield_reset_confirm":
                    pending=context.user_data.get("shield_reset_pending") or {}; users=pending.get("users") or []
                    if not users: await query.answer("⚠️ کاربری انتخاب نشده است.",show_alert=True); return
                    for entry in users:
                        if isinstance(entry,dict): reset_shield_purchase_limitations(session,int(entry.get("user_id")),int(entry.get("country_id")))
                        else: reset_shield_purchase_limitations(session,int(entry),None)
                    back=pending.get("back_callback","admin:user_tools")
                    context.user_data.pop("shield_reset_pending",None); context.user_data.pop(_waiting_scope_key("shield_reset_pending"),None)
                    await query.answer("♻️ محدودیت خرید ریست شد.",show_alert=True)
                    if str(back).startswith("admin:user_game_country:"):
                        parts_back=str(back).split(":")
                        tid=int(parts_back[2]); cid=int(parts_back[3])
                        country=session.get(CountryModel,cid)
                        title=escape(country.title) if country else str(cid)
                        await query.edit_message_text(
                            f"🛡️ <b>تنظیم سپر — {title}</b>\n\n"
                            "محدودیت خرید این کاربر در این کشور با موفقیت ریست شد.",
                            parse_mode="HTML",
                            reply_markup=shield_user_sign_keyboard(back, f"admin:shield_country_reset:{tid}:{cid}")
                        )
                    else:
                        await query.edit_message_text("🛡️ <b>تنظیم سپر کاربران</b>\n\nنوع عملیات را انتخاب کنید.",parse_mode="HTML",reply_markup=shield_user_sign_keyboard(back))
                    return

                if action == "shield_reset_cancel":
                    pending=context.user_data.get("shield_reset_pending") or {}
                    back=pending.get("back_callback","admin:user_tools")
                    context.user_data.pop("shield_reset_pending",None); context.user_data.pop(_waiting_scope_key("shield_reset_pending"),None)
                    await query.answer("لغو شد.")
                    if str(back).startswith("admin:user_game_country:"):
                        parts_back=str(back).split(":")
                        tid=int(parts_back[2]); cid=int(parts_back[3])
                        await query.edit_message_text("🛡️ <b>تنظیم سپر کشور</b>\n\nعملیات لغو شد.",parse_mode="HTML",reply_markup=shield_user_sign_keyboard(back, f"admin:shield_country_reset:{tid}:{cid}"))
                    else:
                        await query.edit_message_text("🛡️ <b>تنظیم سپر کاربران</b>\n\nنوع عملیات را انتخاب کنید:",parse_mode="HTML",reply_markup=shield_user_sign_keyboard(back))
                    return

            # پنل اصلی ادمین
            if namespace == "admin" and action == "back":
                context.user_data.pop("admin_pending", None)
                await query.answer()
                await query.edit_message_text(
                    "⚙️ <b>پنل ادمین</b>",
                    parse_mode="HTML",
                    reply_markup=admin_panel_keyboard(),
                )
                return

            # مدیریت کاربران
            if action == "messages":
                context.user_data.pop("admin_message_pending", None)
                await query.answer(); await query.edit_message_text("📩 <b>ارسال پیام</b>\n\nنوع عملیات را انتخاب کنید:", parse_mode="HTML", reply_markup=admin_messages_keyboard()); return
            if action == "message_lists":
                await query.answer(); await query.edit_message_text("📋 <b>لیست پیام‌ها</b>\n\nنوع پیام را انتخاب کنید:", parse_mode="HTML", reply_markup=message_lists_keyboard()); return
            if action == "message_send_confirm":
                if bool(context.application.bot_data.get(BROADCAST_RUNNING_KEY)):
                    await query.answer("⏳ یک ارسال همگانی دیگر در حال اجراست. لطفاً بعداً دوباره تلاش کنید.", show_alert=True)
                    return
                try:
                    await query.answer()
                except BadRequest as exc:
                    low = str(exc).lower()
                    if not any(x in low for x in ("query is too old", "query id is invalid", "response timeout expired")):
                        raise
                pending = context.user_data.get("admin_message_pending") or {}
                if not pending.get("source_message_id") and not pending.get("text"):
                    await query.edit_message_text("📩 <b>ارسال پیام</b>\n\nنوع عملیات را انتخاب کنید:", parse_mode="HTML", reply_markup=admin_messages_keyboard())
                    return

                sender_id = int(query.from_user.id)
                recipients = list(pending.get("recipients") or [])
                if pending.get("kind") == "public":
                    target = pending.get("target")
                    all_users = get_users(session)
                    admin_ids = {int(a.telegram_id) for a in get_admins(session)} | {int(OWNER_ID)}
                    if target == "users":
                        recipients = [u.telegram_id for u in all_users if int(u.telegram_id) not in admin_ids and int(u.telegram_id) != sender_id]
                    elif target == "admins":
                        recipients = sorted(uid for uid in admin_ids if uid != sender_id)
                    elif target == "all":
                        recipients = [u.telegram_id for u in all_users if int(u.telegram_id) != sender_id]
                        if int(OWNER_ID) != sender_id and int(OWNER_ID) not in {int(x) for x in recipients}:
                            recipients.append(int(OWNER_ID))
                        for admin_id in admin_ids:
                            if admin_id != sender_id and admin_id not in {int(x) for x in recipients}:
                                recipients.append(admin_id)

                unique_recipients = list(dict.fromkeys(int(x) for x in recipients if int(x) != sender_id))
                if not unique_recipients:
                    await query.edit_message_text("📩 <b>ارسال پیام</b>\n\nنوع عملیات را انتخاب کنید:", parse_mode="HTML", reply_markup=admin_messages_keyboard())
                    return

                total = len(unique_recipients)
                context.application.bot_data[BROADCAST_RUNNING_KEY] = True

                # بلافاصله همان پیام تأیید به پنل اصلی ارسال پیام برمی‌گردد.
                await query.edit_message_text(
                    "📩 <b>ارسال پیام</b>\n\nنوع عملیات را انتخاب کنید:",
                    parse_mode="HTML",
                    reply_markup=admin_messages_keyboard(),
                )
                status_msg = await context.bot.send_message(
                    chat_id=int(query.message.chat_id),
                    text=(
                        f"📨 <b>در حال ارسال پیام</b>\n\n"
                        f"🟢 فرستاده شده: <b>0</b>\n"
                        f"🔴 فرستاده نشده: <b>0</b>\n"
                        f"🟡 در انتظار: <b>{total}</b>\n"
                        f"📊 همه: <b>{total}</b>\n\n"
                        "▱▱▱▱▱▱▱▱▱▱ 0%"
                    ),
                    parse_mode="HTML",
                )

                resume_state = {
                    "owner_id": sender_id,
                    "kind": pending.get("kind", "private"),
                    "target": pending.get("target"),
                    "text": pending.get("text", ""),
                    "source_chat_id": pending.get("source_chat_id"),
                    "source_message_id": pending.get("source_message_id"),
                    "content_type": pending.get("content_type", "text"),
                    "recipients": unique_recipients,
                    "next_index": 0,
                    "success": 0,
                    "failed": 0,
                    "status_chat_id": int(status_msg.chat_id),
                    "status_message_id": int(status_msg.message_id),
                    "started_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                }
                try:
                    row = session.scalar(select(BotSetting).where(BotSetting.key == BROADCAST_STATE_KEY))
                    value = json.dumps(resume_state, ensure_ascii=False)
                    if row is None:
                        session.add(BotSetting(key=BROADCAST_STATE_KEY, value=value))
                    else:
                        row.value = value
                    session.commit()
                except Exception:
                    pass

                context.user_data.pop("admin_message_pending", None)
                context.application.create_task(
                    _run_broadcast_task(context.application, resume_state),
                    update=update,
                    name=f"broadcast-{sender_id}-{status_msg.message_id}",
                )
                return
            if action == "message_edit":
                pending=context.user_data.get("admin_message_pending") or {}; pending.pop("text",None); pending.pop("source_chat_id",None); pending.pop("source_message_id",None); pending.pop("content_type",None); pending["step"]="text"; context.user_data["admin_message_pending"]=pending
                context.user_data[_waiting_scope_key("admin_message_pending")] = int(update.effective_chat.id)
                back_cb = "admin:messages"
                await query.answer(); await query.edit_message_text("📝 متن جدید پیام را ارسال کنید:",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data=back_cb)]])); return
            if action == "message_public_target" and len(parts)>=3:
                # handled below in the generic public target branch
                pass
            if action == "message_private":
                context.user_data["admin_message_pending"]={"kind":"private","recipients":[]}
                context.user_data[_waiting_scope_key("admin_message_pending")] = int(update.effective_chat.id)
                await query.answer(); await query.edit_message_text("📩 <b>پیام خصوصی</b>\n\nآیدی عددی کاربر، یوزرنیم، شماره تلفن یا نام کشور را ارسال کنید:", parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="admin:messages")]])); return
            if action == "message_private_add":
                pending=context.user_data.get("admin_message_pending") or {}
                await query.answer(); await query.edit_message_text("➕ کاربر بعدی را با آیدی، یوزرنیم، شماره تلفن یا نام کشور ارسال کنید:", parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="admin:messages")]])); return
            if action == "message_private_finish":
                pending=context.user_data.get("admin_message_pending") or {}
                if not pending.get("recipients"):
                    await query.answer("❌ حداقل یک گیرنده اضافه کنید.",show_alert=True); return
                pending["step"]="text"; context.user_data["admin_message_pending"]=pending
                context.user_data[_waiting_scope_key("admin_message_pending")] = int(update.effective_chat.id)
                await query.answer(); await query.edit_message_text("📝 پیام مورد نظر را ارسال کنید:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="admin:messages")]])); return
            if action == "message_public":
                if owner_user:
                    try:
                        await query.answer()
                    except Exception as exc:
                        # Telegram can reject a stale callback query; the panel edit itself is still valid.
                        if "Query is too old" not in str(exc) and "response timeout expired" not in str(exc):
                            raise
                    await query.edit_message_text("📢 <b>پیام عمومی</b>\n\nگروه گیرندگان را انتخاب کنید:",parse_mode="HTML",reply_markup=message_public_targets_keyboard(True)); return
                context.user_data["admin_message_pending"]={"kind":"public","target":"all","step":"text"}
                context.user_data[_waiting_scope_key("admin_message_pending")] = int(update.effective_chat.id)
                try:
                    await query.answer()
                except Exception as exc:
                    if "Query is too old" not in str(exc) and "response timeout expired" not in str(exc):
                        raise
                await query.edit_message_text("📢 <b>پیام عمومی</b>\n\nپیام مورد نظر را ارسال کنید:",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="admin:messages")]])); return
            if action == "message_public_target" and len(parts)>=3:
                context.user_data["admin_message_pending"]={"kind":"public","target":parts[2],"step":"text"}
                context.user_data[_waiting_scope_key("admin_message_pending")] = int(update.effective_chat.id)
                await query.answer(); await query.edit_message_text("📝 پیام مورد نظر را ارسال کنید:",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="admin:messages")]])); return
            if action == "message_list" and len(parts)>=4:
                kind=parts[2]; page=max(1,int(parts[3]));
                if not owner_user:
                    needed = "message_lists_public" if kind == "public" else "message_lists_private"
                    if not admin_has_permission(session, query.from_user.id, OWNER_ID, needed):
                        await query.answer("🔒 دسترسی محدود شد.", show_alert=True); return
                logs=session.scalar(select(BotSetting).where(BotSetting.key=="admin_message_logs_v1"))
                data=[]
                try: data=json.loads(logs.value) if logs else []
                except Exception: data=[]
                data=[x for x in data if x.get("kind")==kind]
                if not owner_user: data=[x for x in data if int(x.get("sender_id",0))==int(query.from_user.id)]
                data.sort(key=lambda x:x.get("sent_at", ""), reverse=True)
                per=5; total_pages=max(1,(len(data)+per-1)//per); page=min(page,total_pages); items=data[(page-1)*per:page*per]
                if not items:
                    title = "خصوصی" if kind == "private" else "عمومی"
                    await query.answer()
                    await query.edit_message_text(
                        f"📭 <b>پیامی در فهرست پیام‌های {title} وجود ندارد.</b>",
                        parse_mode="HTML",
                        reply_markup=message_lists_keyboard(),
                    )
                    return
                title = "خصوصی" if kind == "private" else "عمومی"
                lines = [f"📋 <b>پیام‌های {title}</b>", "", f"📄 <b>صفحه {page} از {total_pages}</b>", ""]
                for idx, item in enumerate(items, 1):
                    lines.append(f"📨 <b>پیام {idx}</b>")
                    lines.append(f"🕐 تاریخ و ساعت ارسال: <b>{escape(str(item.get('sent_at','ثبت نشده')))}</b>")
                    lines.append(f"👥 گیرندگان: <b>{escape(str(item.get('recipients_text','ثبت نشده')))}</b>")
                    if owner_user:
                        sender = get_user_by_telegram_id(session, int(item.get('sender_id', 0)))
                        sender_name = (sender.first_name if sender else None) or (sender.username if sender else None) or str(item.get('sender_id', 0))
                        lines.append(f"👤 ارسال‌کننده: <b>{escape(str(sender_name))}</b>")
                    lines.append("")
                await query.answer(); await query.edit_message_text("\n".join(lines),parse_mode="HTML",reply_markup=message_items_keyboard(kind,page,total_pages,items)); return
            if action == "message_sent" and len(parts)>=4:
                kind=parts[2]; mid=str(parts[3])
                logs=session.scalar(select(BotSetting).where(BotSetting.key=="admin_message_logs_v1")); data=[]
                try: data=json.loads(logs.value) if logs else []
                except Exception: data=[]
                item=next((x for x in data if str(x.get("id"))==mid and x.get("kind")==kind),None)
                if not item or (not owner_user and int(item.get("sender_id",0))!=int(query.from_user.id)):
                    await query.answer("❌ پیام پیدا نشد.",show_alert=True); return
                # «فرستادن پیام ارسال‌شده» فقط خودِ پیام ثبت‌شده را برای ادمین/اونری
                # که روی این دکمه زده است می‌فرستد؛ هرگز دوباره برای همه گیرندگان ارسال نمی‌شود.
                result=await _send_logged_message(query.get_bot(), query.from_user.id, item)
                if result is None:
                    await query.answer("❌ نسخه قابل ارسال پیام در دسترس نیست.",show_alert=True); return
                await query.answer("✅ پیام ارسال‌شده برای شما فرستاده شد.",show_alert=True)
                return

            if action == "message_recipients" and len(parts)>=5:
                kind=parts[2]; mid=str(parts[3])
                try: page=max(1,int(parts[4]))
                except Exception: page=1
                try: detail_page=max(1,int(parts[5])) if len(parts)>=6 else 1
                except Exception: detail_page=1
                logs=session.scalar(select(BotSetting).where(BotSetting.key=="admin_message_logs_v1")); data=[]
                try: data=json.loads(logs.value) if logs else []
                except Exception: data=[]
                item=next((x for x in data if str(x.get("id"))==mid and x.get("kind")==kind),None)
                if not item or (not owner_user and int(item.get("sender_id",0))!=int(query.from_user.id)):
                    await query.answer("❌ پیام پیدا نشد.",show_alert=True); return
                recipients=_message_recipients_text(session,item)
                per=10; total_pages=max(1,(len(recipients)+per-1)//per); page=min(page,total_pages)
                chunk=recipients[(page-1)*per:page*per]
                lines=["👥 <b>لیست گیرنده‌های پیام</b>","",f"📄 صفحه <b>{page}</b> از <b>{total_pages}</b>",""]
                for n,uid,name,username,phone in chunk:
                    lines += [f"{n}. <b>{escape(str(name))}</b>",f"   🆔 آیدی: <code>{uid}</code>",f"   🔤 یوزرنیم: {escape(username)}",f"   📱 تلفن: {escape(phone)}",""]
                rows=[]
                nav=[]
                if page>1: nav.append(InlineKeyboardButton("⬅️ قبلی",callback_data=f"admin:message_recipients:{kind}:{mid}:{page-1}"))
                nav.append(InlineKeyboardButton(f"📄 {page}/{total_pages}",callback_data="admin:list_noop"))
                if page<total_pages: nav.append(InlineKeyboardButton("بعدی ➡️",callback_data=f"admin:message_recipients:{kind}:{mid}:{page+1}"))
                if nav: rows.append(nav)
                rows.append([InlineKeyboardButton("📤 فرستادن لیست گیرنده‌ها",callback_data=f"admin:message_recipients_send:{kind}:{mid}")])
                rows.append([InlineKeyboardButton("🔙 برگشت",callback_data=f"admin:message_detail:{kind}:{mid}:page:{detail_page}")])
                await query.answer(); await query.edit_message_text("\n".join(lines)[:4096],parse_mode="HTML",reply_markup=InlineKeyboardMarkup(rows)); return

            if action == "message_recipients_send" and len(parts)>=4:
                kind=parts[2]; mid=str(parts[3])
                logs=session.scalar(select(BotSetting).where(BotSetting.key=="admin_message_logs_v1")); data=[]
                try: data=json.loads(logs.value) if logs else []
                except Exception: data=[]
                item=next((x for x in data if str(x.get("id"))==mid and x.get("kind")==kind),None)
                if not item or (not owner_user and int(item.get("sender_id",0))!=int(query.from_user.id)):
                    await query.answer("❌ پیام پیدا نشد.",show_alert=True); return
                recipients=_message_recipients_text(session,item)
                if not recipients:
                    await query.answer("📭 گیرنده‌ای ثبت نشده است.",show_alert=True); return
                lines=["👥 <b>گیرنده‌های پیام</b>",""]
                for n,uid,name,username,phone in recipients:
                    lines += [f"{n}. <b>{escape(str(name))}</b> | 🆔 <code>{uid}</code> | 🔤 {escape(username)} | 📱 {escape(phone)}"]
                text="\n".join(lines)
                for i in range(0,len(text),3900):
                    await query.get_bot().send_message(chat_id=query.message.chat_id,text=text[i:i+3900],parse_mode="HTML")
                await query.answer("✅ لیست گیرنده‌ها ارسال شد.",show_alert=True); return

            if action == "message_detail" and len(parts)>=6:
                kind=parts[2]; mid=str(parts[3]); page=int(parts[5])
                logs=session.scalar(select(BotSetting).where(BotSetting.key=="admin_message_logs_v1")); data=[]
                try: data=json.loads(logs.value) if logs else []
                except Exception: data=[]
                item=next((x for x in data if str(x.get("id"))==mid and x.get("kind")==kind),None)
                if not item or (not owner_user and int(item.get("sender_id",0))!=int(query.from_user.id)):
                    await query.answer("❌ پیام پیدا نشد.",show_alert=True); return
                content_type=item.get('content_type','text')
                text=(f"📩 <b>جزئیات پیام</b>\n\n📅 زمان ارسال: <b>{escape(str(item.get('sent_at','')))}</b>\n👥 گیرندگان: <b>{escape(str(item.get('recipients_text','')))}</b>\n📊 تعداد گیرندگان: <b>{int(item.get('recipient_count',0))}</b>\n📌 نوع: <b>{'خصوصی' if kind=='private' else 'عمومی'}</b>\n📎 نوع محتوا: <b>{escape(str(content_type))}</b>\n\nبرای مشاهده همان پیامی که ارسال شده، دکمه زیر را بزنید.")
                if owner_user:
                    sender = get_user_by_telegram_id(session, int(item.get("sender_id", 0)))
                    sender_name = (sender.first_name if sender else None) or (sender.username if sender else None) or str(item.get("sender_id", 0))
                    text += f"\n👤 ارسال‌کننده: <b>{escape(str(sender_name))}</b>"
                await query.answer(); await query.edit_message_text(text,parse_mode="HTML",reply_markup=message_detail_keyboard(kind,page,mid)); return
            if action == "users":
                context.user_data.pop("admin_pending", None)
                await query.answer()
                await query.edit_message_text(
                    "👥 <b>مدیریت کاربران</b>",
                    parse_mode="HTML",
                    reply_markup=user_management_keyboard(),
                )
                return

            if action == "user_tools":
                context.user_data.pop("admin_pending", None)
                await query.answer()
                await query.edit_message_text("⚙️ <b>ابزارهای مدیریت کاربر</b>\n\nعملیات موردنظر را انتخاب کنید:", parse_mode="HTML", reply_markup=user_management_tools_keyboard())
                return

            # دسترسی‌های مدیریت کاربران
            if action == "user_access":
                context.user_data.pop("admin_pending", None)
                await query.answer()
                await query.edit_message_text(
                    "🛡 <b>دسترسی‌ها</b>", parse_mode="HTML", reply_markup=user_access_keyboard()
                )
                return

            # مدیریت تجربه رهبری از داخل پنل مدیریت کاربران
            if action == "leadership_change":
                if not (is_owner(query.from_user.id, OWNER_ID) or is_admin(session, query.from_user.id, OWNER_ID)):
                    await query.answer("⛔ دسترسی ندارید.", show_alert=True); return
                context.user_data.pop("admin_pending", None)
                context.user_data.pop("admin_leadership_pending", None)
                context.user_data["leadership_back_callback"] = "admin:user_tools"
                context.user_data[_waiting_scope_key("leadership_back_callback")] = int(update.effective_chat.id)
                await query.answer()
                await query.edit_message_text("👑 <b>تنظیم تجربه رهبری کاربران</b>\n\nابتدا مشخص کنید تجربه رهبری اضافه شود یا کم شود:", parse_mode="HTML", reply_markup=leadership_operation_keyboard("admin:user_tools"))
                return

            if action == "leadership_mode" and len(parts) >= 3:
                mode = parts[2]
                if mode not in {"single", "multiple"}:
                    await query.answer("❌ گزینه نامعتبر است.", show_alert=True); return
                operation = context.user_data.get("leadership_operation")
                if operation not in {"add", "sub"}:
                    await query.answer("⚠️ ابتدا نوع تغییر (افزودن یا کم کردن) را انتخاب کنید.", show_alert=True); return
                context.user_data["admin_pending"] = {"action":"leadership_select_users", "mode":mode, "users":[], "operation":operation}
                context.user_data[_waiting_scope_key("admin_pending")] = int(update.effective_chat.id)
                await query.answer()
                text = "👤 <b>انتخاب کاربر</b>\n\nآیدی عددی، یوزرنیم با @، شماره تلفن یا نام کشور را ارسال کنید."
                if mode == "multiple": text += "\n\nمی‌توانید چند کاربر اضافه کنید و در پایان «پایان انتخاب» را بزنید."
                await query.edit_message_text(text, parse_mode="HTML", reply_markup=leadership_multiple_keyboard(0) if mode=="multiple" else InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data="admin:user_tools")]]))
                return

            if action == "leadership_more":
                pending=context.user_data.get("admin_pending") or {}
                if pending.get("action")!="leadership_select_users":
                    await query.answer("⚠️ این عملیات منقضی شده است.", show_alert=True); return
                await query.answer()
                await query.edit_message_text("👥 <b>افزودن کاربر</b>\n\nآیدی، یوزرنیم با @، شماره تلفن یا نام کشور را ارسال کنید:", parse_mode="HTML", reply_markup=leadership_multiple_keyboard(len(pending.get("users",[]))))
                return

            if action == "leadership_apply" and len(parts)>=3:
                mode=parts[2]
                if mode not in {"add","sub"}:
                    await query.answer("⚠️ نوع تغییر نامعتبر است.", show_alert=True); return
                context.user_data["leadership_operation"] = mode
                context.user_data[_waiting_scope_key("leadership_operation")] = int(update.effective_chat.id)
                await query.answer()
                await query.edit_message_text("👥 <b>تعداد افراد</b>\n\nحالا انتخاب کنید تغییر روی یک نفر انجام شود یا چند نفر:", parse_mode="HTML", reply_markup=leadership_change_mode_keyboard())
                return

            if action == "leadership_confirm":
                pending = context.user_data.get("admin_leadership_confirm") or {}
                if not pending:
                    await query.answer("⚠️ این درخواست منقضی شده است.", show_alert=True); return
                target_id = int(pending.get("user_id", 0)); country_id = int(pending.get("country_id", 0))
                target = get_user_by_telegram_id(session, target_id)
                country = session.get(Country, country_id)
                if target is None or country is None or int(country.leader_user_id or 0) != target_id:
                    context.user_data.pop("admin_leadership_confirm", None)
                    await query.answer("❌ اطلاعات کاربر یا کشور معتبر نیست.", show_alert=True); return
                old = float(pending.get("old", 0) or 0)
                delta = float(pending.get("delta", 0) or 0)
                country.leadership_experience = max(0.0, old + delta)
                new_value = float(country.leadership_experience or 0)
                session.commit()
                context.user_data.pop("admin_leadership_confirm", None)
                await query.answer("✅ تغییر تجربه رهبری تأیید و ثبت شد.", show_alert=True)
                if pending.get("source") == "game_specs":
                    back = pending.get("back_callback") or f"admin:user_game_country:{target_id}:{country_id}"
                    panel_text, panel_markup = _user_game_country_panel(session, target_id, country_id, back)
                    if panel_text:
                        await query.edit_message_text(panel_text, parse_mode="HTML", reply_markup=panel_markup)
                        return
                role = "👑 مالک" if is_owner(target.telegram_id, OWNER_ID) else ("🛡 ادمین" if is_admin(session, target.telegram_id, OWNER_ID) else "👤 کاربر عادی")
                text = (
                    "👤 <b>اطلاعات کاربر</b>\n\n"
                    f"نام: <b>{escape(target.first_name or target.username or str(target.telegram_id))}</b>\n"
                    f"🆔 آیدی: <code>{target.telegram_id}</code>\n"
                    f"🔤 نام کاربری: {escape('@'+target.username if target.username else 'ثبت نشده')}\n"
                    f"📱 شماره: {escape(target.phone_number or 'ثبت نشده')}\n"
                    f"🎭 نقش: {role}\n\n"
                    f"🌍 کشور: <b>{escape(country.title)}</b>\n"
                    f"👑 تجربه رهبری قبلی: <b>{old:,.0f}</b>\n"
                    f"📌 تغییر اعمال‌شده: <b>{delta:+,.0f}</b>\n"
                    f"👑 تجربه رهبری جدید: <b>{new_value:,.0f}</b>\n\n"
                    "✅ تغییر با موفقیت ثبت شد."
                )
                await query.edit_message_text(text[:4096], parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت به پنل ادمین", callback_data="admin:back")]]))
                return

            if action == "leadership_finish":
                pending=context.user_data.get("admin_pending") or {}
                users=pending.get("users",[])
                if pending.get("action")!="leadership_select_users" or not users:
                    await query.answer("⚠️ حداقل یک کاربر انتخاب کنید.", show_alert=True); return
                mode = pending.get("operation") or context.user_data.get("leadership_operation")
                if mode not in {"add", "sub"}:
                    await query.answer("⚠️ نوع تغییر مشخص نشده است.", show_alert=True); return
                context.user_data["admin_leadership_bulk_pending"]={"user_ids":pending.get("users",[]),"mode":mode}
                context.user_data[_waiting_scope_key("admin_leadership_bulk_pending")] = int(update.effective_chat.id)
                context.user_data.pop("leadership_operation", None)
                context.user_data.pop("admin_pending",None)
                await query.answer(); await query.edit_message_text("👑 <b>مقدار تجربه رهبری</b>\n\nمقدار عددی را ارسال کنید. برای کم‌کردن، ربات تا صفر پایین می‌آورد.", parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data="admin:user_tools")]])); return

            # تغییر جمعیت کاربران
            if action == "population_change":
                context.user_data.pop("population_pending", None)
                context.user_data.pop("population_selected_user", None)
                context.user_data.pop("population_back_callback", None)
                await query.answer()
                await query.edit_message_text(
                    "👥 <b>تغییر جمعیت</b>\n\nنوع تغییر را انتخاب کنید:",
                    parse_mode="HTML",
                    reply_markup=population_change_keyboard("admin:user_tools"),
                )
                return

            if action == "population_mode" and len(parts) >= 3:
                sign = parts[2]
                if sign not in {"add", "remove"}:
                    await query.answer("❌ نوع عملیات نامعتبر است.", show_alert=True); return
                context.user_data.pop("population_pending", None)
                await query.answer()
                title = "افزایش" if sign == "add" else "کاهش"
                await query.edit_message_text(
                    f"👥 <b>{title} جمعیت</b>\n\nتعداد افراد را انتخاب کنید:",
                    parse_mode="HTML",
                    reply_markup=population_mode_keyboard(sign, "admin:population_change"),
                )
                return

            if action in {"population_add", "population_remove"}:
                sign = "add" if action == "population_add" else "remove"
                context.user_data.pop("population_pending", None)
                await query.answer()
                title = "افزایش" if sign == "add" else "کاهش"
                await query.edit_message_text(
                    f"👥 <b>{title} جمعیت</b>\n\nتعداد افراد را انتخاب کنید:",
                    parse_mode="HTML",
                    reply_markup=population_mode_keyboard(sign, "admin:population_change"),
                )
                return

            if action in {"population_add_single", "population_remove_single", "population_add_multiple", "population_remove_multiple"}:
                sign = "add" if "_add_" in action else "remove"
                mode = "single" if action.endswith("_single") else "multiple"
                context.user_data["population_pending"] = {
                    "sign": sign,
                    "mode": mode,
                    "users": [],
                    "country_id": None,
                    "amount": None,
                    "awaiting_amount": False,
                    "back_action": "admin:user_tools",
                }
                context.user_data[_waiting_scope_key("population_pending")] = int(update.effective_chat.id)
                await query.answer()
                title = "افزایش" if sign == "add" else "کاهش"
                text = (
                    f"👥 <b>{title} جمعیت — {'تک‌نفره' if mode == 'single' else 'چندنفره'}</b>\n\n"
                    "آیدی عددی، نام کاربری با @، شماره تلفن یا نام کشور را ارسال کنید."
                )
                if mode == "multiple":
                    text += "\n\nبعد از تأیید هر کاربر می‌توانید کاربر بعدی را اضافه کنید و در پایان «🏁 پایان انتخاب کاربران» را بزنید."
                await query.edit_message_text(
                    text,
                    parse_mode="HTML",
                    reply_markup=(population_multiple_users_keyboard(sign, False) if mode == "multiple" else population_single_input_keyboard(sign)),
                )
                return

            if action == "population_user_search_back":
                pending = context.user_data.get("population_pending") or {}
                if pending.get("mode") != "multiple":
                    await query.answer("⚠️ عملیات منقضی شده است.", show_alert=True); return
                pending.pop("pending_user_id", None)
                pending["awaiting_amount"] = False
                context.user_data["population_pending"] = pending
                context.user_data[_waiting_scope_key("population_pending")] = int(update.effective_chat.id)
                await query.answer()
                await query.edit_message_text(
                    "👥 <b>انتخاب کاربر بعدی</b>\n\nآیدی عددی، نام کاربری با @، شماره تلفن یا نام کشور را ارسال کنید.",
                    parse_mode="HTML",
                    reply_markup=population_multiple_users_keyboard(pending.get("sign", "add"), bool(pending.get("users"))),
                )
                return

            if action == "population_single_search_back":
                pending = context.user_data.get("population_pending") or {}
                if pending.get("mode") != "single":
                    await query.answer("⚠️ عملیات منقضی شده است.", show_alert=True); return
                sign = pending.get("sign")
                context.user_data["population_pending"] = {
                    "sign": sign, "mode": "single", "users": [], "country_id": None,
                    "amount": None, "awaiting_amount": False, "back_action": "admin:user_tools"
                }
                context.user_data.pop("population_selected_user", None)
                context.user_data[_waiting_scope_key("population_pending")] = int(update.effective_chat.id)
                await query.answer()
                await query.edit_message_text(
                    "👤 <b>انتخاب کاربر</b>\n\nآیدی عددی، نام کاربری با @، شماره تلفن یا نام کشور را ارسال کنید.",
                    parse_mode="HTML",
                    reply_markup=population_single_input_keyboard(sign),
                )
                return

            if action == "population_search_confirm" and len(parts) >= 3:
                target_id = int(parts[2])
                pending = context.user_data.get("population_pending") or {}
                target = get_user_by_telegram_id(session, target_id)
                if target is None:
                    await query.answer("❌ کاربر پیدا نشد.", show_alert=True); return
                if pending.get("sign") not in {"add", "remove"} or pending.get("mode") not in {"single", "multiple"}:
                    await query.answer("⚠️ این عملیات منقضی شده است.", show_alert=True); return
                expected_pending_id = pending.get("pending_user_id")
                if expected_pending_id is not None and int(expected_pending_id) != target_id:
                    await query.answer("⚠️ این درخواست قدیمی شده است. دوباره کاربر را جستجو کنید.", show_alert=True); return
                if pending.get("mode") == "multiple":
                    users = [int(x) for x in (pending.get("users") or [])]
                    if target_id in users:
                        await query.answer("⚠️ این کاربر قبلاً انتخاب شده است.", show_alert=True); return
                    users.append(target_id)
                    pending["users"] = users
                    pending["pending_user_id"] = None
                    context.user_data["population_pending"] = pending
                    context.user_data[_waiting_scope_key("population_pending")] = int(update.effective_chat.id)
                    await query.answer("✅ کاربر تأیید شد.", show_alert=True)
                    await query.edit_message_text(
                        f"✅ <b>کاربر اضافه شد.</b>\n\n👤 {escape(target.first_name or target.username or 'بدون نام')}\n🆔 <code>{target.telegram_id}</code>\n\nکاربر بعدی را با آیدی، نام کاربری با @، شماره تلفن یا نام کشور ارسال کنید؛ یا پایان انتخاب را بزنید.",
                        parse_mode="HTML",
                        reply_markup=population_multiple_users_keyboard(pending["sign"], True),
                    )
                    return

                countries = get_user_countries(session, target)
                if not countries:
                    await query.answer("⚠️ این کاربر هیچ کشوری ندارد.", show_alert=True); return
                pending["users"] = [target_id]
                pending["pending_user_id"] = None
                context.user_data["population_pending"] = pending
                context.user_data["population_selected_user"] = target_id
                context.user_data[_waiting_scope_key("population_selected_user")] = int(update.effective_chat.id)
                context.user_data[_waiting_scope_key("population_pending")] = int(update.effective_chat.id)
                await query.answer("✅ کاربر تأیید شد.", show_alert=True)
                await query.edit_message_text(
                    "🌍 <b>کشور موردنظر برای تغییر جمعیت را انتخاب کنید:</b>",
                    parse_mode="HTML",
                    reply_markup=population_country_list_keyboard(target_id, countries, pending["sign"]),
                )
                return

            if action == "population_users_done":
                pending = context.user_data.get("population_pending") or {}
                sign = pending.get("sign")
                users = pending.get("users") or []
                if pending.get("mode") != "multiple" or sign not in {"add", "remove"} or not users:
                    await query.answer("⚠️ حداقل یک کاربر را انتخاب کنید.", show_alert=True); return
                pending["awaiting_amount"] = True
                pending["amount"] = None
                context.user_data["population_pending"] = pending
                context.user_data[_waiting_scope_key("population_pending")] = int(update.effective_chat.id)
                await query.answer()
                title = "اضافه" if sign == "add" else "کم"
                await query.edit_message_text(
                    f"👥 <b>مقدار {title} جمعیت</b>\n\nعدد صحیح مثبت را ارسال کنید.",
                    parse_mode="HTML",
                    reply_markup=population_amount_keyboard(),
                )
                return

            if action == "population_country_pick" and len(parts) >= 5:
                target_id, country_id, sign = int(parts[2]), int(parts[3]), parts[4]
                pending = context.user_data.get("population_pending") or {}
                target = get_user_by_telegram_id(session, target_id)
                if target is None or pending.get("sign") != sign or pending.get("mode") != "single":
                    await query.answer("⚠️ این عملیات منقضی شده است.", show_alert=True); return
                country = next((c for c in get_user_countries(session, target) if int(c.id) == country_id), None)
                if country is None:
                    await query.answer("❌ این کشور متعلق به کاربر نیست.", show_alert=True); return
                pending["users"] = [target_id]
                pending["country_id"] = country_id
                pending["awaiting_amount"] = True
                pending["amount"] = None
                context.user_data["population_pending"] = pending
                context.user_data[_waiting_scope_key("population_pending")] = int(update.effective_chat.id)
                await query.answer()
                title = "اضافه" if sign == "add" else "کم"
                await query.edit_message_text(
                    f"🌍 <b>{escape(country.title)}</b>\n\n👥 جمعیت فعلی: <b>{int((ensure_bank_account(session, country)).citizens or 0):,}</b> نفر\n\nمقدار {title} جمعیت را به‌صورت عدد صحیح مثبت ارسال کنید.",
                    parse_mode="HTML",
                    reply_markup=population_amount_keyboard(),
                )
                return

            if action == "population_amount_back":
                pending = context.user_data.get("population_pending") or {}
                if not pending:
                    await query.answer("⚠️ عملیات منقضی شده است.", show_alert=True); return
                pending["amount"] = None
                pending["awaiting_amount"] = True
                context.user_data["population_pending"] = pending
                context.user_data[_waiting_scope_key("population_pending")] = int(update.effective_chat.id)
                await query.answer()
                title = "اضافه" if pending.get("sign") == "add" else "کم"
                await query.edit_message_text(
                    f"👥 <b>مقدار {title} جمعیت</b>\n\nعدد صحیح مثبت را ارسال کنید.",
                    parse_mode="HTML",
                    reply_markup=population_amount_keyboard(),
                )
                return

            if action == "population_commit":
                pending = context.user_data.get("population_pending") or {}
                sign = pending.get("sign")
                amount = pending.get("amount")
                user_ids = [int(x) for x in (pending.get("users") or [])]
                if sign not in {"add", "remove"} or not user_ids or not amount or int(amount) <= 0:
                    await query.answer("⚠️ عملیات منقضی شده است.", show_alert=True); return
                amount = int(amount)

                targets = []
                for uid in user_ids:
                    target = get_user_by_telegram_id(session, uid)
                    if target is None:
                        session.rollback()
                        await query.answer(f"❌ کاربر {uid} دیگر ثبت نیست.", show_alert=True); return
                    if not get_user_countries(session, target):
                        session.rollback()
                        await query.answer(f"❌ کاربر {uid} هیچ کشوری ندارد.", show_alert=True); return
                    targets.append(target)

                changes = []
                limit = 2_147_483_647
                for target in targets:
                    if pending.get("mode") == "single":
                        country = next((c for c in get_user_countries(session, target) if int(c.id) == int(pending.get("country_id", 0))), None)
                    else:
                        country = get_default_country(session, target)
                    if country is None:
                        session.rollback()
                        await query.answer(f"❌ کشور مقصد برای کاربر {target.telegram_id} پیدا نشد.", show_alert=True); return
                    acc = ensure_bank_account(session, country)
                    old_value = int(acc.citizens or 0)
                    if sign == "add":
                        new_value = min(limit, old_value + amount)
                    else:
                        new_value = max(0, old_value - amount)
                    acc.citizens = int(new_value)
                    actual_delta = int(new_value - old_value)
                    changes.append({
                        "user_id": int(target.telegram_id),
                        "country": country.title,
                        "old": old_value,
                        "new": int(new_value),
                        "delta": actual_delta,
                    })

                session.commit()
                context.user_data.pop("population_pending", None)
                context.user_data.pop("population_selected_user", None)
                context.user_data.pop("population_back_callback", None)
                context.user_data.pop(_waiting_scope_key("population_pending"), None)
                context.user_data.pop(_waiting_scope_key("population_selected_user"), None)

                direction = "افزایش" if sign == "add" else "کاهش"
                for change in changes:
                    delta_abs = abs(int(change["delta"]))
                    delta_text = f"+{delta_abs:,}" if change["delta"] > 0 else f"-{delta_abs:,}" if change["delta"] < 0 else "0"
                    await _notify_user(
                        query.get_bot(),
                        change["user_id"],
                        f"✅ <b>تغییر جمعیت انجام شد.</b>\n\n"
                        f"🌍 کشور: <b>{escape(str(change['country']))}</b>\n"
                        f"👥 نوع تغییر: <b>{direction}</b>\n"
                        f"📊 مقدار تغییر: <b>{delta_text}</b> نفر\n"
                        f"👥 جمعیت جدید: <b>{change['new']:,}</b> نفر",
                    )

                if len(changes) == 1:
                    c = changes[0]
                    delta_abs = abs(int(c["delta"]))
                    delta_text = f"+{delta_abs:,}" if c["delta"] > 0 else f"-{delta_abs:,}" if c["delta"] < 0 else "0"
                    admin_text = (
                        "✅ <b>تغییر جمعیت انجام شد.</b>\n\n"
                        f"👤 کاربر: <code>{c['user_id']}</code>\n"
                        f"🌍 کشور: <b>{escape(str(c['country']))}</b>\n"
                        f"📊 مقدار تغییر: <b>{delta_text}</b> نفر\n"
                        f"👥 جمعیت قبلی: <b>{c['old']:,}</b>\n"
                        f"👥 جمعیت جدید: <b>{c['new']:,}</b>"
                    )
                else:
                    lines = [
                        "✅ <b>تغییر جمعیت انجام شد.</b>",
                        "",
                        f"👥 تعداد کاربران: <b>{len(changes):,}</b>",
                    ]
                    for c in changes:
                        delta_abs = abs(int(c["delta"]))
                        delta_text = f"+{delta_abs:,}" if c["delta"] > 0 else f"-{delta_abs:,}" if c["delta"] < 0 else "0"
                        lines.append(f"• <code>{c['user_id']}</code> | 🌍 {escape(str(c['country']))} | {delta_text} | {c['new']:,}")
                    admin_text = "\n".join(lines)
                    if len(admin_text) > 3900:
                        admin_text = admin_text[:3900] + "\n\n… فهرست کامل کاربران به‌دلیل محدودیت طول پیام نمایش داده نشد."
                await _notify_user(query.get_bot(), query.from_user.id, admin_text)
                await query.answer("✅ تغییر جمعیت با موفقیت انجام شد.", show_alert=True)
                await query.edit_message_text(
                    "⚙️ <b>ابزارهای مدیریت کاربر</b>\n\nعملیات موردنظر را انتخاب کنید:",
                    parse_mode="HTML",
                    reply_markup=user_management_tools_keyboard(),
                )
                return

            # تغییر موجودی
            if action == "balance_change":
                context.user_data.pop("balance_pending", None)
                await query.answer()
                await query.edit_message_text(
                    "💰 <b>تغییر موجودی</b>\n\nنوع تغییر را انتخاب کنید:",
                    parse_mode="HTML", reply_markup=balance_change_keyboard()
                )
                return

            # جستجوی کاربران / بن‌شده‌ها
            if action in {"search_users", "search_banned"}:
                banned = action == "search_banned"
                if banned and not get_users(session, banned=True):
                    await query.answer("⚠️ هیچ کاربر بن‌شده‌ای وجود ندارد.", show_alert=True); return
                context.user_data["admin_pending"] = {"action": "search_banned_users" if banned else "search_users"}
                context.user_data[_waiting_scope_key("admin_pending")] = int(update.effective_chat.id)
                await query.answer()
                await query.edit_message_text(("🔎 <b>جستجوی کاربران بن‌شده</b>\n\nآیدی عددی، نام کاربری، شماره تلفن یا نام کشور را ارسال کنید:" if banned else "🔎 <b>جستجوی کاربران</b>\n\nآیدی عددی، نام کاربری، شماره تلفن یا نام کشور را ارسال کنید:"), parse_mode="HTML", reply_markup=user_search_mode_keyboard(banned)); return

            if action == "search_mode":
                banned = len(parts) >= 3 and parts[2] == "banned"
                context.user_data["admin_pending"] = {"action": "search_banned_users" if banned else "search_users"}
                context.user_data[_waiting_scope_key("admin_pending")] = int(update.effective_chat.id)
                await query.answer(); await query.edit_message_text("🔎 <b>جستجو</b>\n\nآیدی عددی، نام کاربری، شماره تلفن یا نام کشور را ارسال کنید:", parse_mode="HTML", reply_markup=user_search_mode_keyboard(banned)); return

            if action == "balance_search_confirm" and len(parts) >= 3:
                target_id = int(parts[2])
                pending = context.user_data.get("balance_pending") or {}
                target = get_user_by_telegram_id(session, target_id)
                if target is None:
                    await query.answer("❌ کاربر پیدا نشد.", show_alert=True); return
                if not pending:
                    await query.answer("⚠️ عملیات منقضی شده است.", show_alert=True); return
                pending["pending_user_id"] = target_id
                pending.setdefault("users", [])
                pending["users"] = [x for x in pending["users"] if int(x) != target_id]
                # حالت تک‌نفره باید کاربر تأییدشده را هم در users نگه دارد؛
                # در غیر این صورت کلیک روی منبع، pending را بدون کاربر می‌بیند و «عملیات منقضی شده» نمایش می‌دهد.
                if pending.get("mode") != "multiple":
                    pending["users"] = [target_id]
                    context.user_data["balance_selected_user"] = target_id
                    context.user_data[_waiting_scope_key("balance_selected_user")] = int(update.effective_chat.id)
                if pending.get("mode") == "multiple":
                    pending["users"].append(target_id)
                    pending.pop("pending_user_id", None)
                    context.user_data["balance_pending"] = pending
                    context.user_data[_waiting_scope_key("balance_pending")] = int(update.effective_chat.id)
                    await query.answer("✅ کاربر تأیید شد.", show_alert=True)
                    await query.edit_message_text(
                        f"✅ <b>کاربر تأیید شد</b>\n\n👤 {escape(target.first_name or target.username or 'بدون نام')}\n🆔 <code>{target.telegram_id}</code>\n\nکاربر بعدی را با آیدی، نام کاربری با @، شماره تلفن یا نام کشور ارسال کنید؛ یا «پایان» را بزنید.",
                        parse_mode="HTML",
                        reply_markup=balance_multiple_users_keyboard(pending["sign"], pending.get("back_action", "admin:users"), has_users=True)
                    ); return
                context.user_data["balance_pending"] = pending
                context.user_data[_waiting_scope_key("balance_pending")] = int(update.effective_chat.id)
                countries = get_user_countries(session, target)
                if not countries:
                    await query.answer("⚠️ این کاربر هیچ کشوری ندارد.", show_alert=True); return
                await query.answer("✅ کاربر تأیید شد.", show_alert=True)
                await query.edit_message_text(
                    "🌍 <b>کشور موردنظر برای تغییر موجودی را انتخاب کنید:</b>",
                    parse_mode="HTML",
                    reply_markup=balance_country_list_keyboard(target_id, countries, pending["sign"], pending.get("back_action", context.user_data.get("balance_back_callback", "admin:user_tools")))
                ); return

            if action == "search_confirm" and len(parts) >= 3:
                target_id=int(parts[2]); target=get_user_by_telegram_id(session,target_id)
                if target is None:
                    await query.answer("❌ کاربر پیدا نشد.",show_alert=True); return
                scope=context.user_data.pop("search_scope","users")
                back="admin:user_access" if scope=="banned" else "admin:users"
                context.user_data["user_detail_back"] = back
                context.user_data[_waiting_scope_key("user_detail_back")] = int(update.effective_chat.id)
                await query.answer("✅ تأیید شد.")
                context.user_data["user_admin_origin"] = f"admin:user:{target_id}"
                context.user_data[_waiting_scope_key("user_admin_origin")] = int(update.effective_chat.id)
                await query.edit_message_text(_render_managed_user_info(session,target)[:4096], parse_mode="HTML", reply_markup=user_action_keyboard(target_id,is_owner(query.from_user.id,OWNER_ID),back_callback=back,banned=bool(target.is_banned)))
                return

            # لیست کاربران / بن‌شده‌ها
            if action in {"user_list", "banned_list"}:
                context.user_data.pop("admin_pending", None)
                banned_only = action == "banned_list"
                all_list_users = get_users(session, banned=True if banned_only else None)
                viewer_owner = is_owner(query.from_user.id, OWNER_ID)
                viewer_admin = is_admin(session, query.from_user.id, OWNER_ID)
                if viewer_owner:
                    users = all_list_users
                else:
                    users = [u for u in all_list_users if not is_owner(u.telegram_id, OWNER_ID) and (not is_admin(session, u.telegram_id, OWNER_ID) or u.telegram_id == query.from_user.id)]
                if not users:
                    await query.answer("⚠️ هیچ کاربری در این فهرست وجود ندارد.", show_alert=True)
                    return
                try:
                    page = int(parts[2])
                except (IndexError, ValueError):
                    page = 1
                per_page = 10
                total_pages = max(1, (len(users) + per_page - 1) // per_page)
                page = max(1, min(page, total_pages))
                page_users = users[(page-1)*per_page: page*per_page]
                lines = ["🚫 <b>لیست بن‌شده‌ها</b>" if banned_only else "📋 <b>لیست کاربران</b>", ""]
                for i, u in enumerate(page_users, start=(page-1)*per_page+1):
                    name = u.first_name or u.username or "بدون نام"
                    status = "🚫 بن" if u.is_banned else "🟢 فعال"
                    phone_line = f"\n📱 {u.phone_number}" if u.phone_number else ""
                    lines.append(f"{i}. 👤 <b>{name}</b>\n🆔 <code>{u.telegram_id}</code> | {status}{phone_line}")
                await query.answer()
                await query.edit_message_text(
                    "\n\n".join(lines), parse_mode="HTML",
                    reply_markup=(banned_list_keyboard(page, total_pages, page_users, is_owner(query.from_user.id, OWNER_ID))
                                  if banned_only else user_list_keyboard(page, total_pages, False, page_users, is_owner(query.from_user.id, OWNER_ID)))
                )
                return

            # نمایش جزئیات یک کاربر از لیست/جستجو
            if action == "user" and len(parts) >= 3:
                try:
                    target_id = int(parts[2])
                except ValueError:
                    await query.answer("❌ آیدی نامعتبر است.", show_alert=True)
                    return
                target = get_user_by_telegram_id(session, target_id)
                if target is None:
                    await query.answer("❌ این کاربر در ربات ثبت نشده است.", show_alert=True)
                    return
                if not is_owner(query.from_user.id, OWNER_ID) and (is_owner(target_id, OWNER_ID) or (is_admin(session, target_id, OWNER_ID) and target_id != query.from_user.id)):
                    await query.answer("⛔ این کاربر برای شما قابل مشاهده نیست.", show_alert=True)
                    return

                # مبدأ صفحه کاربر را از callback مشخص می‌کنیم تا «برگشت» دقیقاً
                # یک مرحله به عقب برگردد (لیست کاربران/لیست بن‌شده‌ها/جستجو).
                back_callback = "admin:users"
                if len(parts) >= 5:
                    origin = parts[3]
                    try:
                        origin_page = int(parts[4])
                    except ValueError:
                        origin_page = 1
                    if origin == "user_list":
                        back_callback = f"admin:user_list:{origin_page}"
                    elif origin == "banned_list":
                        back_callback = f"admin:banned_list:{origin_page}"
                    elif origin == "users":
                        back_callback = "admin:users"

                role = "👑 مالک" if is_owner(target_id, OWNER_ID) else ("🛡 ادمین" if is_admin(session, target_id, OWNER_ID) else "👤 کاربر عادی")
                context.user_data["user_detail_back"] = back_callback
                context.user_data[_waiting_scope_key("user_detail_back")] = int(update.effective_chat.id)
                await query.answer()
                await query.edit_message_text(
                    _render_managed_user_info(session, target)[:4096],
                    parse_mode="HTML",
                    reply_markup=user_action_keyboard(
                        target_id,
                        is_owner(query.from_user.id, OWNER_ID),
                        back_callback=back_callback,
                        banned=target.is_banned,
                    )
                )
                return

            if action == "user_country_edit" and len(parts) >= 3:
                if not is_owner(query.from_user.id, OWNER_ID):
                    await query.answer("⛔ این بخش فقط برای مالک است.", show_alert=True)
                    return
                target_id = int(parts[2])
                target = get_user_by_telegram_id(session, target_id)
                if target is None:
                    await query.answer("❌ کاربر پیدا نشد.", show_alert=True); return
                countries = get_user_countries(session, target)
                if not countries:
                    await query.answer("⚠️ هیچ کشوری ثبت نشده است.", show_alert=True); return
                context.user_data["country_edit_list_back"] = context.user_data.get("user_game_settings_back", f"admin:user_game_settings:{target_id}")
                await query.answer()
                await query.edit_message_text("🌍 <b>کشوری را که می‌خواهید نامش را ویرایش کنید انتخاب کنید:</b>", parse_mode="HTML", reply_markup=user_country_list_keyboard(target_id, countries, context.user_data.get("user_game_settings_back", f"admin:user_game_settings:{target_id}")))
                return

            if action == "user_country_pick" and len(parts) >= 4:
                if not (is_owner(query.from_user.id, OWNER_ID) or is_admin(session, query.from_user.id, OWNER_ID)):
                    await query.answer("⛔ این بخش فقط برای ادمین و Owner است.", show_alert=True); return
                target_id, country_id = int(parts[2]), int(parts[3])
                target = get_user_by_telegram_id(session, target_id)
                if target is None:
                    await query.answer("❌ کاربر پیدا نشد.", show_alert=True); return
                countries = session.scalars(select(CountryModel)).all()
                edit_country = next((c for c in countries if c.id == country_id), None)
                if edit_country is None:
                    await query.answer("❌ کشور پیدا نشد.", show_alert=True); return
                context.user_data["country_edit"] = {"target_user": target_id, "country_id": country_id, "back": context.user_data.get("country_edit_list_back", f"admin:user_country_edit:{target_id}"), "country_list_back": f"admin:user_country_edit:{target_id}"}
                context.user_data[_waiting_scope_key("country_edit")] = int(update.effective_chat.id)
                context.user_data["country_edit_waiting"] = True
                context.user_data[_waiting_scope_key("country_edit_waiting")] = int(update.effective_chat.id)
                await query.answer()
                await query.edit_message_text(f"✏️ نام جدید کشور «{edit_country.title}» را ارسال کنید.", reply_markup=country_edit_waiting_keyboard())
                return

            if action == "user_country_delete" and len(parts) >= 3:
                if not is_owner(query.from_user.id, OWNER_ID) and not is_admin(session, query.from_user.id, OWNER_ID):
                    await query.answer("⛔ دسترسی ندارید.", show_alert=True); return
                target_id = int(parts[2]); target = get_user_by_telegram_id(session, target_id)
                if target is None:
                    await query.answer("❌ کاربر پیدا نشد.", show_alert=True); return
                countries = get_user_countries(session, target)
                if not countries:
                    await query.answer("⚠️ این کاربر کشوری ندارد.", show_alert=True); return
                context.user_data["user_country_delete_back"] = context.user_data.get("user_game_settings_back", f"admin:user_game_settings:{target_id}")
                await query.answer(); await query.edit_message_text("🗑️ <b>کشور موردنظر برای حذف را انتخاب کنید:</b>", parse_mode="HTML", reply_markup=user_country_delete_list_keyboard(target_id, countries, context.user_data.get("user_game_settings_back", f"admin:user_game_settings:{target_id}"))); return

            if action == "user_country_delete_pick" and len(parts) >= 4:
                if not is_owner(query.from_user.id, OWNER_ID) and not is_admin(session, query.from_user.id, OWNER_ID):
                    await query.answer("⛔ دسترسی ندارید.", show_alert=True); return
                target_id, country_id = int(parts[2]), int(parts[3])
                country = session.get(CountryModel, country_id)
                if country is None or country.id not in {c.id for c in get_user_countries(session, get_user_by_telegram_id(session, target_id))}:
                    await query.answer("❌ کشور پیدا نشد.", show_alert=True); return
                await query.answer()
                # قبل از حذف، مشخصات کامل همان کشور را نمایش می‌دهیم تا ادمین
                # دقیقاً بداند کدام کشور را در حال حذف است.
                country_details = country_status(
                    country,
                    get_metal_mine_config(session),
                    get_arsenal_config(session),
                    _country_shield_status(session, country),
                )
                text = (
                    "🗑️ <b>حذف کشور</b>\n\n"
                    f"{country_details}\n\n"
                    "⚠️ <b>آیا از حذف این کشور مطمئن هستید؟</b>\n"
                    "تمام اطلاعات این کشور برای همیشه حذف می‌شود."
                )
                await query.edit_message_text(
                    text,
                    parse_mode="HTML",
                    reply_markup=user_country_delete_confirm_keyboard(target_id, country_id),
                )
                return

            if action == "user_country_delete_confirm" and len(parts) >= 4:
                if not is_owner(query.from_user.id, OWNER_ID) and not is_admin(session, query.from_user.id, OWNER_ID):
                    await query.answer("⛔ دسترسی ندارید.", show_alert=True); return
                target_id, country_id = int(parts[2]), int(parts[3]); country = session.get(CountryModel, country_id)
                if country is None:
                    await query.answer("❌ کشور قبلاً حذف شده است.", show_alert=True); return
                target = get_user_by_telegram_id(session, target_id)
                if target is None or country.id not in {c.id for c in get_user_countries(session, target)}:
                    await query.answer("❌ کشور پیدا نشد.", show_alert=True); return
                if target.default_country_id == country.id: target.default_country_id = None
                _delete_country_dependencies(session, country.id)
                session.execute(delete(UserCountry).where(UserCountry.country_id == country.id)); session.delete(country); session.commit()
                remaining=get_user_countries(session,target)
                await query.answer("🗑️ کشور حذف شد.", show_alert=True)
                if remaining:
                    back_callback=context.user_data.get("user_game_settings_back", f"admin:user_game_settings:{target_id}")
                    await query.edit_message_text("🗑️ <b>حذف کشور</b>\n\nکشوری را که می‌خواهید تمام اطلاعاتش حذف شود انتخاب کنید:",parse_mode="HTML",reply_markup=user_country_delete_list_keyboard(target_id,remaining,back_callback))
                else:
                    await query.edit_message_text("⚙️ <b>تنظیمات بازی کاربر</b>", parse_mode="HTML", reply_markup=admin_user_game_settings_keyboard(target_id, context.user_data.get("user_game_settings_back", f"admin:user:{target_id}")))
                return

            if action == "user_country_delete_cancel":
                target_id=int(parts[2]) if len(parts)>2 else int(context.user_data.get("balance_selected_user", query.from_user.id))
                country_id=int(parts[3]) if len(parts)>3 else 0
                target=get_user_by_telegram_id(session,target_id)
                countries=get_user_countries(session,target) if target else []
                await query.answer("🔙 برگشت")
                if country_id and target:
                    country=next((c for c in countries if int(c.id)==country_id),None)
                    if country:
                        country_details=country_status(country,get_metal_mine_config(session),get_arsenal_config(session),_country_shield_status(session,country))
                        await query.edit_message_text("🗑️ <b>حذف کشور</b>\n\n"+country_details+"\n\n⚠️ <b>آیا از حذف این کشور مطمئن هستید؟</b>\nتمام اطلاعات این کشور برای همیشه حذف می‌شود.",parse_mode="HTML",reply_markup=user_country_delete_confirm_keyboard(target_id,country_id)); return
                back_callback=context.user_data.get("user_game_settings_back", f"admin:user_game_settings:{target_id}")
                await query.edit_message_text("🗑️ <b>حذف کشور</b>\n\nکشوری را که می‌خواهید تمام اطلاعاتش حذف شود انتخاب کنید:",parse_mode="HTML",reply_markup=user_country_delete_list_keyboard(target_id,countries,back_callback))
                return

            if action == "user_settings" and len(parts) >= 3:
                target_id = int(parts[2]); target = get_user_by_telegram_id(session, target_id)
                if target is None:
                    await query.answer("❌ کاربر پیدا نشد.", show_alert=True); return
                back = context.user_data.get("user_detail_back", "admin:users")
                session.expire_all()
                target = get_user_by_telegram_id(session, target_id)
                await query.answer()
                await query.edit_message_text(_render_managed_user_info(session,target)[:4096], parse_mode="HTML", reply_markup=user_action_keyboard(target_id,is_owner(query.from_user.id,OWNER_ID),back_callback=back,banned=bool(target.is_banned)))
                return

            if action in {"user_info", "admin_account_settings", "admin_account_info"} and len(parts) >= 3:
                target_id = int(parts[2]); target = get_user_by_telegram_id(session, target_id)
                if target is None:
                    await query.answer("❌ کاربر پیدا نشد.", show_alert=True); return
                back = context.user_data.get("user_detail_back", "admin:users")
                session.expire_all()
                target = get_user_by_telegram_id(session, target_id)
                if action == "admin_account_settings" or action == "admin_account_info":
                    back = f"owner:admin_detail:{target_id}" if is_admin(session,target_id,OWNER_ID) or is_owner(target_id,OWNER_ID) else back
                await query.answer()
                context.user_data["user_admin_origin"] = f"owner:admin_detail:{target_id}" if (is_admin(session,target_id,OWNER_ID) or is_owner(target_id,OWNER_ID)) else f"admin:user:{target_id}"
                context.user_data[_waiting_scope_key("user_admin_origin")] = int(update.effective_chat.id)
                await query.edit_message_text(_render_managed_user_info(session,target)[:4096], parse_mode="HTML", reply_markup=(admin_info_keyboard(target_id,back_callback=back,banned=bool(target.is_banned)) if is_admin(session,target_id,OWNER_ID) or is_owner(target_id,OWNER_ID) else user_action_keyboard(target_id,is_owner(query.from_user.id,OWNER_ID),back_callback=back,banned=bool(target.is_banned))))
                return

            if action == "user_leadership" and len(parts) >= 3:
                if not (is_owner(query.from_user.id, OWNER_ID) or is_admin(session, query.from_user.id, OWNER_ID)):
                    await query.answer("⛔ دسترسی ندارید.", show_alert=True); return
                target_id=int(parts[2]); target=get_user_by_telegram_id(session,target_id)
                if target is None:
                    await query.answer("❌ کاربر پیدا نشد.", show_alert=True); return
                countries=get_user_countries(session,target)
                if not countries:
                    await query.answer("⚠️ این کاربر کشوری ندارد.",show_alert=True); return
                role = "👑 مالک" if is_owner(target_id, OWNER_ID) else ("🛡 ادمین" if is_admin(session, target_id, OWNER_ID) else "👤 کاربر عادی")
                default_country = get_default_country(session, target)
                country_lines = "\n".join(
                    f"  🌍 {escape(c.title)} — 🎖 {float(c.leadership_experience or 0):,.0f} تجربه — 💰 {'♾️' if c.infinite_money else f'{c.money:,.0f}'}"
                    for c in countries
                ) or "ندارد"
                text = (
                    "👑 <b>تنظیم تجربه رهبری</b>\n\n"
                    f"👤 نام: <b>{escape(target.first_name or target.username or 'بدون نام')}</b>\n"
                    f"🆔 آیدی: <code>{target.telegram_id}</code>\n"
                    f"🔤 نام کاربری: {escape('@'+target.username if target.username else 'ثبت نشده')}\n"
                    f"📱 شماره: {escape(target.phone_number or 'ثبت نشده')}\n"
                    f"📝 بیوگرافی: {escape(getattr(target, 'bio', None) or 'ثبت نشده')}\n"
                    f"🎭 نقش: {role}\n"
                    f"📅 تاریخ عضویت: {target.created_at.strftime('%Y/%m/%d — %H:%M') if target.created_at else 'ثبت نشده'}\n"
                    f"🕒 آخرین فعالیت: {target.last_active_at.strftime('%Y/%m/%d — %H:%M') if target.last_active_at else 'ثبت نشده'}\n"
                    f"🌍 کشور پیش‌فرض: {escape(default_country.title) if default_country else 'ثبت نشده'}\n"
                    f"🌎 تعداد کشورها: <b>{len(countries)}</b>\n\n"
                    "کشور موردنظر برای تغییر تجربه را از دکمه‌های زیر انتخاب کنید:\n\n"
                    f"🎮 <b>کشورها</b>\n{country_lines}"
                )
                await query.answer(); await query.edit_message_text(text[:4096],parse_mode="HTML",reply_markup=user_leadership_country_keyboard(target_id,countries,context.user_data.get("user_game_specs_back",f"admin:user_game_specs:{target_id}"))); return

            if action == "user_leadership_all" and len(parts) >= 3:
                target_id = int(parts[2]); target = get_user_by_telegram_id(session, target_id)
                if target is None:
                    await query.answer("❌ کاربر پیدا نشد.", show_alert=True); return
                countries = get_user_countries(session, target)
                if not countries:
                    await query.answer("⚠️ این کاربر کشوری ندارد.", show_alert=True); return
                lines = [f"👑 <b>تمام کشورهای {escape(target.first_name or target.username or str(target.telegram_id))}</b>", ""]
                for c in countries:
                    lines.append(
                        f"🌍 <b>{escape(c.title)}</b>\n"
                        f"🎖 تجربه رهبری: <b>{float(c.leadership_experience or 0):,.0f}</b>\n"
                        f"💰 پول: {'♾️' if c.infinite_money else f'{c.money:,.0f}'} | "
                        f"🔩 فلز: {'♾️' if c.infinite_metal else f'{c.metal:,.0f}'}\n"
                        f"⛽ سوخت: {'♾️' if c.infinite_fuel else f'{c.fuel:,.2f}'} | "
                        f"☢️ اورانیوم: {'♾️' if c.infinite_uranium else f'{c.uranium:,.2f}'}\n"
                        f"🏛️ مرکز فرماندهی: سطح {int(c.command_center_level or 0)} | 🏭 زرادخانه: سطح {int(c.arsenal_level or 0)}\n"
                        f"⛏️ معدن فلز: سطح {int(c.metal_mine_level or 0)} | 🛡️ پدافند: {int(c.defense or 0)}\n"
                        f"🚁 پهپاد: {int(c.drones or 0)} | 🚀 موشک: {int(c.missiles or 0)}"
                    )
                    lines.append("")
                back = context.user_data.get("user_game_specs_back", f"admin:user_game_specs:{target_id}")
                await query.answer()
                await query.edit_message_text("\n".join(lines)[:4096], parse_mode="HTML", reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 برگشت به تجربه رهبری", callback_data=f"admin:user_game_country:{target_id}:{country_id}")],
                    [InlineKeyboardButton("🔙 برگشت به اطلاعات کاربر", callback_data=back)],
                ]))
                return

            if action == "user_leadership_country" and len(parts) >= 4:
                target_id=int(parts[2]); country_id=int(parts[3]); target=get_user_by_telegram_id(session,target_id); country=session.get(Country,country_id)
                if target is None or country is None or int(country.leader_user_id or 0)!=target_id:
                    await query.answer("❌ اطلاعات کشور معتبر نیست.",show_alert=True); return
                pending_lead = context.user_data.get("admin_pending") or {}
                operation = pending_lead.get("operation") if pending_lead.get("action") == "leadership_select_users" else None
                if operation in {"add", "sub"}:
                    context.user_data.pop("admin_pending", None)
                    context.user_data["admin_leadership_pending"]={"user_id":target_id,"country_id":country_id,"mode":operation,"source":"game_specs","back_callback":f"admin:user_game_country:{target_id}:{country_id}"}
                    context.user_data[_waiting_scope_key("admin_leadership_pending")] = int(update.effective_chat.id)
                    label="افزودن" if operation == "add" else "کم کردن"
                    await query.answer(); await query.edit_message_text(f"👑 <b>{escape(country.title)}</b>\n\n🎖 تجربه فعلی: <b>{float(country.leadership_experience or 0):,.0f}</b>\n\nمقدار {label} تجربه رهبری را ارسال کنید.",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data=f"admin:user_game_country:{target_id}:{country_id}")]])); return
                await query.answer(); await query.edit_message_text(f"👑 <b>{escape(country.title)}</b>\n\n🎖 تجربه فعلی: <b>{float(country.leadership_experience or 0):,.0f}</b>\n\nنوع تغییر را انتخاب کنید:",parse_mode="HTML",reply_markup=user_leadership_mode_keyboard(target_id,country_id)); return

            if action == "user_leadership_mode" and len(parts) >= 5:
                target_id=int(parts[2]); country_id=int(parts[3]); mode=parts[4]
                if mode not in {"add","sub"}: await query.answer("❌ گزینه نامعتبر است.",show_alert=True); return
                target=get_user_by_telegram_id(session,target_id); country=session.get(Country,country_id)
                if target is None or country is None or int(country.leader_user_id or 0)!=target_id:
                    await query.answer("❌ اطلاعات کشور معتبر نیست.",show_alert=True); return
                context.user_data["admin_leadership_pending"]={"user_id":target_id,"country_id":country_id,"mode":mode,"source":"game_specs","back_callback":f"admin:user_game_country:{target_id}:{country_id}"}
                context.user_data[_waiting_scope_key("admin_leadership_pending")] = int(update.effective_chat.id)
                label="افزودن" if mode=="add" else "کم کردن"
                await query.answer(); await query.edit_message_text(f"👑 <b>{label} تجربه رهبری</b>\n\nتجربه فعلی: <b>{float(country.leadership_experience or 0):,.0f}</b>\n\nمقدار {label} را به‌صورت عدد ارسال کنید.",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data=f"admin:user_game_country:{target_id}:{country_id}")]])); return

            if action == "user_game_population" and len(parts) >= 4:
                target_id, country_id = int(parts[2]), int(parts[3])
                target = get_user_by_telegram_id(session, target_id); country = session.get(Country, country_id)
                if target is None or country is None or country.id not in {c.id for c in get_user_countries(session, target)} or int(country.leader_user_id or 0) != target_id:
                    await query.answer("❌ اطلاعات کشور معتبر نیست.", show_alert=True); return
                acc = ensure_bank_account(session, country)
                context.user_data["user_game_population_pending"] = {"user_id": target_id, "country_id": country_id, "mode": None}
                context.user_data[_waiting_scope_key("user_game_population_pending")] = int(query.message.chat_id)
                from keyboards.admin import user_game_population_mode_keyboard
                await query.answer(); await query.edit_message_text(f"👥 <b>تغییر جمعیت — {escape(country.title)}</b>\n\nجمعیت فعلی: <b>{int(acc.citizens or 0):,}</b> نفر\n\nنوع تغییر را انتخاب کنید:", parse_mode="HTML", reply_markup=user_game_population_mode_keyboard(target_id, country_id)); return

            if action == "user_game_population_mode" and len(parts) >= 5:
                target_id, country_id, mode = int(parts[2]), int(parts[3]), parts[4]
                if mode not in {"add", "sub"}: await query.answer("❌ گزینه نامعتبر است.", show_alert=True); return
                target = get_user_by_telegram_id(session, target_id); country = session.get(Country, country_id)
                if target is None or country is None or int(country.leader_user_id or 0) != target_id:
                    await query.answer("❌ اطلاعات کشور معتبر نیست.", show_alert=True); return
                acc = ensure_bank_account(session, country)
                context.user_data["user_game_population_pending"] = {"user_id": target_id, "country_id": country_id, "mode": mode}
                context.user_data[_waiting_scope_key("user_game_population_pending")] = int(query.message.chat_id)
                label = "افزایش" if mode == "add" else "کاهش"
                from keyboards.admin import user_game_population_input_keyboard
                await query.answer(); await query.edit_message_text(f"👥 <b>{label} جمعیت</b> — {escape(country.title)}\n\nجمعیت فعلی: <b>{int(acc.citizens or 0):,}</b> نفر\n\nمقدار {label} را به‌صورت عدد ارسال کنید.", parse_mode="HTML", reply_markup=user_game_population_input_keyboard(target_id, country_id)); return

            if action == "user_game_population_confirm" and len(parts) >= 4:
                target_id, country_id = int(parts[2]), int(parts[3])
                pending = context.user_data.get("user_game_population_confirm") or {}
                if int(pending.get("user_id", -1)) != target_id or int(pending.get("country_id", -1)) != country_id:
                    await query.answer("⚠️ عملیات منقضی شده است.", show_alert=True); return
                target = get_user_by_telegram_id(session, target_id); country = session.get(Country, country_id)
                if target is None or country is None or int(country.leader_user_id or 0) != target_id:
                    await query.answer("❌ اطلاعات کشور معتبر نیست.", show_alert=True); return
                acc = ensure_bank_account(session, country); old_value = int(acc.citizens or 0); amount = int(pending.get("amount", 0) or 0); mode = pending.get("mode")
                if amount <= 0 or mode not in {"add", "sub"}: await query.answer("⚠️ مقدار عملیات معتبر نیست.", show_alert=True); return
                new_value = min(2_147_483_647, old_value + amount) if mode == "add" else max(0, old_value - amount)
                acc.citizens = int(new_value); session.commit()
                for key in ("user_game_population_pending", "user_game_population_confirm"):
                    context.user_data.pop(key, None); context.user_data.pop(_waiting_scope_key(key), None)
                default_country = get_default_country(session, target)
                text=(f"✅ <b>تغییر جمعیت انجام شد.</b>\n\n👥 مقدار قبلی: <b>{old_value:,}</b>\n📌 تغییر: <b>{'+' if mode=='add' else '-'}{amount:,}</b> نفر\n👥 جمعیت جدید: <b>{new_value:,}</b> نفر\n\n🌍 <b>مشخصات بازی کشور</b>\n\n🏳️ کشور: <b>{escape(country.title)}</b>\n⭐ کشور پیش‌فرض: <b>{'بله' if default_country and int(default_country.id)==int(country.id) else 'خیر'}</b>\n👥 جمعیت: <b>{new_value:,}</b> نفر\n\n" + country_status(country, get_metal_mine_config(session), get_arsenal_config(session), _country_shield_status(session, country), include_identity=False))
                from keyboards.admin import user_game_population_mode_keyboard
                await query.answer("✅ جمعیت تغییر کرد.", show_alert=True)
                await query.edit_message_text(text[:4096], parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💰 تغییر موجودی", callback_data=f"admin:user_balance:{target_id}:{country_id}")],[InlineKeyboardButton("👑 تنظیم تجربه رهبری", callback_data=f"admin:user_leadership_country:{target_id}:{country_id}")],[InlineKeyboardButton("🛡️ تنظیم سپر", callback_data=f"admin:shield_country:{target_id}:{country_id}:manage")],[InlineKeyboardButton("👥 تغییر جمعیت", callback_data=f"admin:user_game_population:{target_id}:{country_id}")],[InlineKeyboardButton("🔙 برگشت", callback_data=f"admin:user_game_country:{target_id}:{country_id}")]])); return

            if action == "user_game_settings" and len(parts) >= 3:
                target_id=int(parts[2]); target=get_user_by_telegram_id(session,target_id)
                if target is None: await query.answer("❌ کاربر پیدا نشد.",show_alert=True); return
                # مبدأ را از خود دکمه ثبت می‌کنیم؛ نقش فعلی کاربر تعیین‌کننده مبدأ نیست.
                source = parts[3] if len(parts) >= 4 else ("admin" if is_admin(session,target_id,OWNER_ID) or is_owner(target_id,OWNER_ID) else "user")
                if source == "admin":
                    back_callback = f"owner:admin_detail:{target_id}"
                else:
                    list_back = context.user_data.get("user_detail_back") or "admin:users"
                    if str(list_back).startswith("admin:user_list:"):
                        back_callback = f"admin:user:{target_id}:user_list:{str(list_back).split(':')[-1]}"
                    else:
                        back_callback = f"admin:user:{target_id}"
                context.user_data["user_game_settings_back"] = back_callback
                await query.answer(); await query.edit_message_text("⚙️ <b>تنظیمات بازی کاربر</b>",parse_mode="HTML",reply_markup=admin_user_game_settings_keyboard(target_id,back_callback,include_country_name=owner_user)); return

            if action == "user_game_country" and len(parts) >= 4:
                target_id, country_id = int(parts[2]), int(parts[3])
                session.expire_all()
                country_back = context.user_data.get("user_game_country_back", f"admin:user_game_specs:{target_id}")
                text, markup = _user_game_country_panel(session, target_id, country_id, country_back)
                if text is None:
                    await query.answer("❌ کشور پیدا نشد.", show_alert=True); return
                await query.answer(); await query.edit_message_text(text, parse_mode="HTML", reply_markup=markup); return

            if action == "user_game_specs" and len(parts) >= 3:
                target_id = int(parts[2])
                target = get_user_by_telegram_id(session, target_id)
                if target is None:
                    await query.answer("❌ کاربر پیدا نشد.", show_alert=True)
                    return
                countries = get_user_countries(session, target)
                country = get_default_country(session, target)
                back_callback = context.user_data.get("user_game_settings_back", f"admin:user_game_settings:{target_id}")
                context.user_data["user_game_specs_back"] = back_callback
                context.user_data["user_game_country_back"] = f"admin:user_game_specs:{target_id}"
                if country is None:
                    await query.answer("⚠️ این کاربر کشور پیش‌فرضی ندارد.", show_alert=True)
                    await query.edit_message_text(
                        f"🎮 <b>مشخصات بازی کاربر</b>\n\n🌍 تعداد کشورها: <b>{len(countries):,}</b>\n\n❌ این کاربر هنوز کشور پیش‌فرضی ندارد.",
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data=back_callback)]])
                    )
                    return
                text = (f"🎮 <b>مشخصات بازی کاربر</b>\n\n"
                        f"🌍 تعداد کشورها: <b>{len(countries):,}</b>\n"
                        f"⭐ کشور پیش‌فرض: <b>{escape(country.title)}</b>\n\n"
                        "کشور موردنظر را از دکمه‌های زیر انتخاب کنید:")
                await query.answer()
                await query.edit_message_text(text, parse_mode="HTML", reply_markup=user_game_specs_country_list_keyboard(target_id, countries, country.id, back_callback=back_callback))
                return

            if action == "user_swap_reset" and len(parts) >= 3:
                if not (is_owner(query.from_user.id, OWNER_ID) or is_admin(session, query.from_user.id, OWNER_ID)):
                    await query.answer("⛔ دسترسی ندارید.", show_alert=True); return
                target_id = int(parts[2])
                target = get_user_by_telegram_id(session, target_id)
                if target is None:
                    await query.answer("❌ کاربر پیدا نشد.", show_alert=True); return
                # پاک کردن زمان آخرین جابه‌جایی، محدودیت بعدی را از صفر شروع می‌کند.
                row = session.scalar(select(BotSetting).where(BotSetting.key == f"swap_last:{target_id}"))
                if row is not None:
                    session.delete(row)
                session.commit()
                await query.answer("♻️ محدودیت جابه‌جایی کاربر ریست شد.", show_alert=True)
                await query.edit_message_text("⚙️ <b>تنظیمات بازی کاربر</b>", parse_mode="HTML", reply_markup=admin_user_game_settings_keyboard(target_id, context.user_data.get("user_game_settings_back", f"admin:user:{target_id}")))
                return

            if action == "user_swap" and len(parts)>=3:
                target_id=int(parts[2]); target=get_user_by_telegram_id(session,target_id); countries=get_user_countries(session,target) if target else []
                if target is None or len(countries)<2: await query.answer("⚠️ کاربر حداقل دو کشور لازم دارد.",show_alert=True); return
                context.user_data["admin_swap"]={"user_id":target_id,"country_ids":[c.id for c in countries]}
                await query.answer(); await query.edit_message_text("🔄 <b>کشور مبدأ را انتخاب کنید:</b>",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(c.title,callback_data=f"admin:swap_from:{target_id}:{c.id}")] for c in countries]+[[InlineKeyboardButton("🔙 برگشت",callback_data=context.user_data.get("user_game_settings_back", f"admin:user_game_settings:{target_id}"))]])); return
            if action == "swap_from" and len(parts)>=4:
                target_id,source_id=int(parts[2]),int(parts[3]); target=get_user_by_telegram_id(session,target_id); countries=get_user_countries(session,target) if target else []
                if source_id not in {c.id for c in countries}: await query.answer("❌ کشور نامعتبر است.",show_alert=True); return
                await query.answer(); await query.edit_message_text("🔄 <b>کشور مقصد را انتخاب کنید:</b>",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(c.title,callback_data=f"admin:swap_to:{target_id}:{source_id}:{c.id}")] for c in countries if c.id!=source_id]+[[InlineKeyboardButton("🔙 برگشت",callback_data=f"admin:user_swap:{target_id}")]])); return
            if action == "swap_to" and len(parts)>=5:
                target_id,source_id,target_country_id=map(int,parts[2:5]); target=get_user_by_telegram_id(session,target_id); countries=get_user_countries(session,target) if target else []
                ids={c.id for c in countries}
                if source_id not in ids or target_country_id not in ids: await query.answer("❌ کشور نامعتبر است.",show_alert=True); return
                a=session.get(CountryModel,source_id); b=session.get(CountryModel,target_country_id)
                if not a or not b:
                    await query.answer("❌ کشور پیدا نشد.",show_alert=True); return
                context.user_data["admin_swap_confirm"]={"user_id":target_id,"source_id":source_id,"target_id":target_country_id}
                await query.answer()
                await query.edit_message_text(
                    f"🔄 <b>تأیید جابه‌جایی کشورها</b>\n\n🌍 مبدأ: <b>{a.title}</b>\n🌍 مقصد: <b>{b.title}</b>\n\nتمام اطلاعات بازی این دو کشور جابه‌جا خواهد شد.\n\nآیا مطمئن هستید؟",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ تأیید جابه‌جایی",callback_data=f"admin:swap_confirm:{target_id}:{source_id}:{target_country_id}")],[InlineKeyboardButton("🔙 برگشت",callback_data=f"admin:swap_from:{target_id}:{source_id}")]])
                ); return
            if action == "swap_confirm" and len(parts)>=5:
                target_id,source_id,target_country_id=map(int,parts[2:5]); target=get_user_by_telegram_id(session,target_id); countries=get_user_countries(session,target) if target else []
                if not target or source_id not in {c.id for c in countries} or target_country_id not in {c.id for c in countries}:
                    await query.answer("❌ کشور نامعتبر است.",show_alert=True); return
                a=session.get(CountryModel,source_id); b=session.get(CountryModel,target_country_id)
                if not a or not b:
                    await query.answer("❌ کشور پیدا نشد.",show_alert=True); return
                _swap_country_state(session, a, b)
                session.commit(); context.user_data.pop("admin_swap_confirm",None)
                await query.answer("✅ جابه‌جایی انجام شد.",show_alert=True)
                await query.edit_message_text("⚙️ <b>تنظیمات بازی کاربر</b>",parse_mode="HTML",reply_markup=admin_user_game_settings_keyboard(target_id, context.user_data.get("user_game_settings_back", f"admin:user:{target_id}"))); return
            if action == "swap_confirm_cancel" and len(parts)>=3:
                target_id=int(parts[2]); context.user_data.pop("admin_swap_confirm",None)
                await query.answer(); await query.edit_message_text("⚙️ <b>تنظیمات بازی کاربر</b>",parse_mode="HTML",reply_markup=admin_user_game_settings_keyboard(target_id, context.user_data.get("user_game_settings_back", f"admin:user:{target_id}"))); return

            if action == "user_balance" and len(parts) >= 3:
                target_id = int(parts[2])
                country_id = int(parts[3]) if len(parts) >= 4 else None
                target = get_user_by_telegram_id(session, target_id)
                if target is None:
                    await query.answer("❌ کاربر پیدا نشد.", show_alert=True); return
                if country_id is not None and country_id not in {int(c.id) for c in get_user_countries(session, target)}:
                    await query.answer("❌ کشور نامعتبر است.", show_alert=True); return
                context.user_data["balance_selected_user"] = target_id
                context.user_data[_waiting_scope_key("balance_selected_user")] = int(update.effective_chat.id)
                if country_id is not None:
                    context.user_data["balance_selected_country"] = country_id
                    context.user_data[_waiting_scope_key("balance_selected_country")] = int(update.effective_chat.id)
                else:
                    context.user_data.pop("balance_selected_country", None)
                context.user_data["balance_back_callback"] = (f"admin:user_game_country:{target_id}:{country_id}" if country_id is not None else "admin:user_tools")
                context.user_data.pop("balance_pending", None)
                if country_id is not None:
                    context.user_data["balance_pending"] = {"mode":"single", "users":[target_id], "country_id":country_id}
                    context.user_data[_waiting_scope_key("balance_pending")] = int(update.effective_chat.id)
                await query.answer()
                await query.edit_message_text("💰 <b>تغییر موجودی کاربر</b>\n\nنوع تغییر را انتخاب کنید:", parse_mode="HTML", reply_markup=balance_change_keyboard())
                return

            if action == "ban_duration" and len(parts) >= 3:
                duration=parts[2]; target_id=int(parts[3]) if len(parts)>=4 else None
                pending=context.user_data.get("admin_pending") or {}
                if target_id: pending["telegram_id"]=target_id
                if duration not in {"hour","day","permanent"}: await query.answer("❌ مدت نامعتبر است.",show_alert=True); return
                if not pending.get("telegram_id") and not pending.get("telegram_ids"):
                    await query.answer("⚠️ عملیات منقضی شده است.",show_alert=True); return
                pending["duration"]=duration; pending.pop("duration_amount",None); pending["awaiting_reason_button"]=False
                if duration in {"hour","day"}:
                    pending["action"]="ban_duration_value"
                    context.user_data["admin_pending"]=pending; context.user_data[_waiting_scope_key("admin_pending")]=int(update.effective_chat.id)
                    unit="ساعت" if duration=="hour" else "روز"
                    await query.answer(); await query.edit_message_text(f"⏳ <b>مدت بن</b>\n\nتعداد {unit} را ارسال کنید. این مقدار دقیقاً مدت بن کاربر خواهد بود.",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data=pending.get("back_callback","admin:user_access"))]])); return
                pending["action"]="ban_single_reason" if pending.get("telegram_id") else "ban_multiple_reason"
                context.user_data["admin_pending"]=pending; context.user_data[_waiting_scope_key("admin_pending")]=int(update.effective_chat.id)
                await query.answer(); await query.edit_message_text("🚫 <b>دلیل بن</b>\n\nبدون دلیل یا «ثبت دلیل» را انتخاب کنید.",parse_mode="HTML",reply_markup=ban_reason_keyboard(pending.get("back_callback", "admin:user_access"))); return

            if action in {"user_ban", "user_unban"} and len(parts) >= 3:
                target_id = int(parts[2])
                mode = "ban" if action == "user_ban" else "unban"
                target = get_user_by_telegram_id(session, target_id)
                if target is None:
                    await query.answer("❌ کاربر پیدا نشد.", show_alert=True); return
                if mode == "ban" and (is_owner(target_id, OWNER_ID) or is_admin(session, target_id, OWNER_ID)):
                    await query.answer("⛔ مالک یا مدیر قابل بن شدن نیست.", show_alert=True); return
                back_callback = context.user_data.get("user_detail_back", f"admin:user:{target_id}")
                if mode == "ban":
                    context.user_data["admin_pending"] = {"action": "ban_duration_select", "telegram_id": target_id, "back_callback": back_callback}
                    context.user_data[_waiting_scope_key("admin_pending")] = int(update.effective_chat.id)
                    await query.answer(); await query.edit_message_text(f"🚫 <b>نوع بن کاربر</b>\n\n🆔 آیدی: <code>{target_id}</code>\nمدت بن را انتخاب کنید:",parse_mode="HTML",reply_markup=ban_duration_keyboard(target_id, back_callback=back_callback)); return
                context.user_data["admin_pending"] = {"action": "unban_single", "telegram_id": target_id, "back_callback": back_callback}
                context.user_data[_waiting_scope_key("admin_pending")] = int(update.effective_chat.id)
                await query.answer(); await query.edit_message_text(
                    f"⚠️ آیا از رفع بن کاربر <code>{target_id}</code> مطمئن هستید؟",
                    parse_mode="HTML", reply_markup=user_confirm_keyboard("unban", back_callback=back_callback)
                ); return

            if action == "user_admin" and len(parts) >= 3:
                if not is_owner(query.from_user.id, OWNER_ID):
                    await query.answer("⛔ این بخش فقط برای مالک است.", show_alert=True); return
                target_id = int(parts[2]); target = get_user_by_telegram_id(session, target_id)
                if target is None:
                    await query.answer("❌ کاربر پیدا نشد.", show_alert=True); return
                back_callback = context.user_data.get("user_admin_origin", f"admin:user:{target_id}")
                context.user_data["user_admin_back"] = back_callback
                await query.answer(); await query.edit_message_text("👑 <b>مدیریت ادمینی کاربر</b>", parse_mode="HTML", reply_markup=user_admin_keyboard(target_id, is_admin(session, target_id, OWNER_ID), back_callback=back_callback)); return

            if action in {"user_admin_add", "user_admin_remove"} and len(parts) >= 3:
                if not is_owner(query.from_user.id, OWNER_ID):
                    await query.answer("⛔ این بخش فقط برای مالک است.", show_alert=True); return
                target_id = int(parts[2])
                if action == "user_admin_add":
                    if is_owner(target_id, OWNER_ID):
                        await query.answer("⚠️ مالک از قبل دسترسی کامل دارد.", show_alert=True); return
                    target_for_admin = get_user_by_telegram_id(session, target_id)
                    if target_for_admin is None:
                        await query.answer("❌ کاربر در ربات ثبت نشده است.", show_alert=True); return
                    if target_for_admin.is_banned:
                        await query.answer("⛔ کاربر بن‌شده را نمی‌توان ادمین کرد. ابتدا بن را رفع کنید.", show_alert=True); return
                    if is_admin(session, target_id, OWNER_ID):
                        await query.answer("⚠️ این کاربر از قبل ادمین است.", show_alert=True); return
                    if add_admin(session, target_id):
                        session.commit(); await _notify_user(query.get_bot(), target_id, "👑 <b>شما ادمین شدید.</b>")
                        await query.answer("✅ ادمین اضافه شد.", show_alert=True)
                    else:
                        await query.answer("❌ افزودن ادمین انجام نشد.", show_alert=True)
                else:
                    result = remove_admin(session, target_id, OWNER_ID)
                    if result == "REMOVED":
                        session.commit(); await _notify_user(query.get_bot(), target_id, "👤 <b>دسترسی ادمینی شما حذف شد.</b>")
                        await query.answer("✅ ادمین حذف شد.", show_alert=True)
                    else:
                        await query.answer("❌ این کاربر ادمین نیست یا قابل حذف نیست.", show_alert=True)
                back_callback = context.user_data.get("user_admin_back", context.user_data.get("user_detail_back", "admin:users"))
                target = get_user_by_telegram_id(session, target_id)
                if target is not None:
                    if is_admin(session,target_id,OWNER_ID) or is_owner(target_id,OWNER_ID):
                        # اگر این عملیات از صفحه اطلاعات ادمین در لیست ادمین‌ها آمده،
                        # برگشت دوم باید دقیقاً به همان لیست ادمین‌ها برگردد.
                        if str(back_callback).startswith("owner:admin_detail:"):
                            info_back = f"owner:list_admins:{max(1, int(context.user_data.get('admin_list_page', 1)))}"
                        else:
                            info_back = back_callback
                        context.user_data["user_detail_back"] = info_back
                        context.user_data[_waiting_scope_key("user_detail_back")] = int(update.effective_chat.id)
                        context.user_data["user_admin_origin"] = f"owner:admin_detail:{target_id}"
                        context.user_data[_waiting_scope_key("user_admin_origin")] = int(update.effective_chat.id)
                        markup = admin_info_keyboard(target_id, back_callback=info_back, banned=bool(target.is_banned))
                    else:
                        context.user_data["user_admin_origin"] = f"admin:user:{target_id}"
                        context.user_data[_waiting_scope_key("user_admin_origin")] = int(update.effective_chat.id)
                        markup = user_action_keyboard(target_id,True,back_callback=back_callback,banned=bool(target.is_banned))
                    await query.edit_message_text(_render_managed_user_info(session,target)[:4096], parse_mode="HTML", reply_markup=markup)
                return

            if action == "list_noop":
                await query.answer()
                return

            # انتخاب تکی/چندتایی بن و رفع بن
            if action in {"ban_user", "unban_user"}:
                mode = "ban" if action == "ban_user" else "unban"
                users = get_users(session, banned=True if mode == "unban" else None)
                if mode == "unban" and not users:
                    await query.answer("⚠️ هیچ کاربر بن‌شده‌ای وجود ندارد.", show_alert=True)
                    return
                if mode == "ban" and not users:
                    await query.answer("⚠️ هیچ کاربری وجود ندارد.", show_alert=True)
                    return
                context.user_data.pop("admin_pending", None)
                await query.answer()
                await query.edit_message_text(
                    f"{'🚫 بن کاربر' if mode == 'ban' else '✅ رفع بن کاربر'}\n\nروش عملیات را انتخاب کنید:",
                    reply_markup=user_action_mode_keyboard(mode),
                )
                return

            if action in {"ban_single", "unban_single", "ban_multiple", "unban_multiple"}:
                mode = "ban" if action.startswith("ban") else "unban"
                multiple = action.endswith("multiple")
                context.user_data["admin_pending"] = {
                    "action": f"{mode}_{'multiple' if multiple else 'single'}",
                    "telegram_ids": [],
                    "back_callback": f"admin:{mode}_user",
                }
                context.user_data[_waiting_scope_key("admin_pending")] = int(update.effective_chat.id)
                await query.answer()
                await query.edit_message_text(
                    f"{'🚫 بن چندتایی' if mode == 'ban' and multiple else '🚫 بن تکی' if mode == 'ban' else '✅ رفع بن چندتایی' if multiple else '✅ رفع بن تکی'}\n\nکاربر را با یوزرنیم، آیدی عددی، شماره تلفن یا نام کشور جستجو کنید.",
                    reply_markup=admin_step_back_keyboard(f"admin:{mode}_user"),
                )
                return

            # پایان دریافت آیدی‌های چندتایی و ورود دلیل
            if action == "ban_multiple_finish":
                pending = context.user_data.get("admin_pending") or {}
                if pending.get("action") != "ban_multiple" or not pending.get("telegram_ids"):
                    await query.answer("⚠️ ابتدا حداقل یک آیدی معتبر وارد کنید.", show_alert=True); return
                pending["action"] = "ban_duration_select"
                context.user_data["admin_pending"] = pending
                context.user_data[_waiting_scope_key("admin_pending")] = int(update.effective_chat.id)
                await query.answer()
                await query.edit_message_text("🚫 <b>نوع بن کاربران</b>\n\nمدت بن را انتخاب کنید:", parse_mode="HTML", reply_markup=ban_duration_keyboard(back_callback=pending.get("back_callback", "admin:user_access")))
                return

            if action == "ban_reason_text":
                pending = context.user_data.get("admin_pending") or {}
                if pending.get("action") == "ban_single_reason" and pending.get("telegram_id"):
                    pending["action"]="ban_single_wait_reason"; context.user_data["admin_pending"]=pending
                    context.user_data[_waiting_scope_key("admin_pending")] = int(update.effective_chat.id)
                    await query.answer()
                    await query.edit_message_text(
                        "📝 <b>دلیل بن را ارسال کنید.</b>\n\nاگر نمی‌خواهید دلیل ثبت شود، دکمه «بدون دلیل» را بزنید.",
                        parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data=pending.get("back_callback", "admin:ban_user"))]])
                    )
                    return
                if pending.get("action") == "ban_multiple" and pending.get("telegram_ids"):
                    pending["action"] = "ban_multiple_reason"
                    context.user_data["admin_pending"] = pending
                    context.user_data[_waiting_scope_key("admin_pending")] = int(update.effective_chat.id)
                    await query.answer()
                    await query.edit_message_text(
                        "📝 <b>دلیل بن را ارسال کنید.</b>\n\nاگر نمی‌خواهید دلیل ثبت شود، دکمه «بدون دلیل» را بزنید.",
                        parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data=pending.get("back_callback", "admin:ban_user"))]])
                    )
                    return
                await query.answer("⚠️ عملیات منقضی شده است.", show_alert=True)
                return

            # دریافت/تأیید دلیل بن
            if action == "ban_reason_empty":
                pending = context.user_data.get("admin_pending") or {}
                if pending.get("action") == "ban_single_reason":
                    pending["reason"] = None
                    pending["action"] = "ban_single"
                    context.user_data["admin_pending"] = pending
                    context.user_data[_waiting_scope_key("admin_pending")] = int(update.effective_chat.id)
                    await query.answer()
                    await query.edit_message_text("⚠️ آیا از بن این کاربر بدون دلیل مطمئن هستید؟", reply_markup=user_confirm_keyboard("ban", back_callback=pending.get("back_callback", "admin:user_access")))
                    return
                if pending.get("action") in {"ban_multiple", "ban_multiple_reason"}:
                    pending["reason"] = None
                    pending["action"] = "ban_multiple"
                    context.user_data["admin_pending"] = pending
                    context.user_data[_waiting_scope_key("admin_pending")] = int(update.effective_chat.id)
                    await query.answer()
                    await query.edit_message_text("⚠️ آیا از بن کاربران بدون دلیل مطمئن هستید؟", reply_markup=user_multiple_confirm_keyboard("ban"))
                    return
                await query.answer("⚠️ عملیات منقضی شده است.", show_alert=True); return

            # تأیید بن/رفع بن تکی
            if action in {"confirm_ban", "confirm_unban"}:
                mode = "ban" if action == "confirm_ban" else "unban"
                pending = context.user_data.get("admin_pending") or {}
                target_id = pending.get("telegram_id")
                if not target_id or pending.get("action") != f"{mode}_single":
                    await query.answer("⚠️ عملیات منقضی شده است.", show_alert=True)
                    context.user_data.pop("admin_pending", None)
                    return
                result = ban_user(session, target_id, OWNER_ID, (pending.get("reason") or "").strip() or None) if mode == "ban" else unban_user(session, target_id)
                if result == "BANNED" and mode == "ban":
                    target_user = get_user_by_telegram_id(session, target_id)
                    duration = pending.get("duration", "permanent")
                    if duration == "hour": target_user.ban_until = datetime.utcnow() + timedelta(hours=int(pending.get("duration_amount",1) or 1))
                    elif duration == "day": target_user.ban_until = datetime.utcnow() + timedelta(days=int(pending.get("duration_amount",1) or 1))
                    else: target_user.ban_until = None
                context.user_data.pop("admin_pending", None)
                if result == "NOT_FOUND":
                    await query.answer("❌ این کاربر در ربات ثبت نشده است.", show_alert=True)
                    return
                if result == "OWNER_PROTECTED":
                    await query.answer("⛔ مالک قابل بن شدن نیست.", show_alert=True)
                    return
                if result == "ADMIN_PROTECTED":
                    await query.answer("⛔ ادمین قابل بن شدن نیست.", show_alert=True)
                    return
                if result in {"ALREADY_BANNED", "NOT_BANNED"}:
                    await query.answer("⚠️ وضعیت کاربر تغییری نکرد.", show_alert=True)
                    return
                session.commit()
                if mode == "ban":
                    reason = (pending.get("reason") or "").strip()
                    reason_line = f"\n\n📝 دلیل: {escape(reason)}" if reason else ""
                    ban_text = ban_status_text(target_user) if target_user is not None else "🚫 <b>شما بن شدید.</b>"
                    await _notify_user(query.get_bot(), target_id, ban_text + reason_line)
                else:
                    await _notify_user(query.get_bot(), target_id, "✅ <b>بن شما رفع شد.</b>\n\nدسترسی شما به ربات دوباره فعال شد.")
                await query.answer("✅ عملیات با موفقیت انجام شد.", show_alert=True)
                target_user = get_user_by_telegram_id(session, target_id)
                if target_user is not None:
                    back_callback = pending.get("back_callback") or context.user_data.get("user_detail_back", "admin:users")
                    await query.edit_message_text(_render_managed_user_info(session,target_user)[:4096], parse_mode="HTML", reply_markup=user_action_keyboard(target_id,is_owner(query.from_user.id,OWNER_ID),back_callback=back_callback,banned=bool(target_user.is_banned)))
                else:
                    await query.edit_message_text("👥 <b>مدیریت کاربران</b>", parse_mode="HTML", reply_markup=user_management_keyboard())
                return

            # تأیید چندتایی
            if action in {"confirm_ban_multiple", "confirm_unban_multiple"}:
                mode = "ban" if action == "confirm_ban_multiple" else "unban"
                pending = context.user_data.get("admin_pending") or {}
                ids = pending.get("telegram_ids", [])
                if pending.get("action") not in {f"{mode}_multiple", f"{mode}_multiple_reason"} or not ids:
                    await query.answer("⚠️ هنوز هیچ آیدی آماده نشده است.", show_alert=True)
                    return
                results = []
                for target_id in ids:
                    result = ban_user(session, target_id, OWNER_ID, (pending.get("reason") or "").strip() or None) if mode == "ban" else unban_user(session, target_id)
                    if result not in ({"BANNED", "UNBANNED"}):
                        session.rollback()
                        await query.answer(f"❌ عملیات روی آیدی {target_id} انجام نشد.", show_alert=True)
                        return
                    if mode == "ban" and result == "BANNED":
                        target_user = get_user_by_telegram_id(session, target_id)
                        duration = pending.get("duration", "permanent")
                        amount = int(pending.get("duration_amount", 1) or 1)
                        if target_user is not None:
                            if duration == "hour": target_user.ban_until = datetime.utcnow() + timedelta(hours=amount)
                            elif duration == "day": target_user.ban_until = datetime.utcnow() + timedelta(days=amount)
                            else: target_user.ban_until = None
                    results.append(result)
                session.commit()
                context.user_data.pop("admin_pending", None)
                for target_id in ids:
                    if mode == "ban":
                        target_user = get_user_by_telegram_id(session, target_id)
                        reason = (pending.get("reason") or "").strip()
                        reason_line = f"\n\n📝 دلیل: {escape(reason)}" if reason else ""
                        ban_text = ban_status_text(target_user) if target_user is not None else "🚫 <b>شما بن شدید.</b>"
                        await _notify_user(query.get_bot(), target_id, ban_text + reason_line)
                    else:
                        await _notify_user(query.get_bot(), target_id, "✅ <b>بن شما رفع شد.</b>\n\nدسترسی شما به ربات دوباره فعال شد.")
                await query.answer(f"✅ عملیات روی {len(results)} کاربر انجام شد.", show_alert=True)
                await query.edit_message_text("👥 <b>مدیریت کاربران</b>", parse_mode="HTML", reply_markup=user_management_keyboard())
                return

            # پاکسازی همه بن‌ها
            if action == "clear_bans":
                banned = get_users(session, banned=True)
                if not banned:
                    await query.answer("⚠️ هیچ کاربر بن‌شده‌ای وجود ندارد.", show_alert=True)
                    return
                context.user_data.pop("admin_pending", None)
                await query.answer()
                await query.edit_message_text(
                    "⚠️ <b>پاکسازی همه بن‌ها</b>\n\nآیا از رفع بن تمام کاربران مطمئن هستید؟",
                    parse_mode="HTML", reply_markup=clear_bans_confirm_keyboard()
                )
                return

            if action == "confirm_clear_bans":
                banned_ids = [u.telegram_id for u in get_users(session, banned=True)]
                count = clear_bans(session)
                session.commit()
                context.user_data.pop("admin_pending", None)
                for target_id in banned_ids:
                    await _notify_user(query.get_bot(), target_id, "✅ <b>رفع بن شدید</b>\n\nدسترسی شما به ربات دوباره فعال شد.")
                await query.answer(f"✅ {count} کاربر رفع بن شدند.", show_alert=True)
                await query.edit_message_text("👥 <b>مدیریت کاربران</b>", parse_mode="HTML", reply_markup=user_management_keyboard())
                return

            # افزایش/کاهش موجودی
            if action in {"balance_add", "balance_remove"}:
                sign = "add" if action == "balance_add" else "remove"
                selected = context.user_data.pop("balance_selected_user", None)
                selected_country_id = context.user_data.pop("balance_selected_country", None)
                context.user_data.pop("balance_pending", None)
                if selected:
                    pending_balance = {"sign": sign, "mode": "single", "users": [int(selected)], "items": [], "back_action": context.user_data.get("balance_back_callback", f"admin:user:{int(selected)}")}
                    if selected_country_id is not None:
                        pending_balance["country_id"] = int(selected_country_id)
                    context.user_data["balance_pending"] = pending_balance
                    context.user_data[_waiting_scope_key("balance_pending")] = int(update.effective_chat.id)
                    await query.answer()
                    await query.edit_message_text(("💰 کدام منبع را می‌خواهید اضافه کنید؟" if sign == "add" else "💰 کدام منبع را می‌خواهید کم کنید؟"), reply_markup=resource_keyboard(sign, context.user_data.get("balance_back_callback", f"admin:user:{selected}")))
                    return
                await query.answer()
                await query.edit_message_text(
                    f"{'➕ افزایش' if sign == 'add' else '➖ کاهش'} <b>موجودی</b>\n\nروش عملیات را انتخاب کنید:",
                    parse_mode="HTML", reply_markup=balance_mode_keyboard(sign, context.user_data.get("balance_back_callback", "admin:users"))
                )
                return

            if action in {"balance_add_single", "balance_remove_single", "balance_add_multiple", "balance_remove_multiple"}:
                sign = "add" if "_add_" in action else "remove"
                mode = "single" if action.endswith("_single") else "multiple"
                context.user_data["balance_pending"] = {"sign": sign, "mode": mode, "users": [], "items": []}
                context.user_data[_waiting_scope_key("balance_pending")] = int(update.effective_chat.id)
                await query.answer()
                await query.edit_message_text(
                    f"{'➕ افزایش' if sign == 'add' else '➖ کاهش'} موجودی — {'تک‌نفره' if mode == 'single' else 'چندنفره'}\n\nآیدی عددی، نام کاربری با @، شماره تلفن یا نام کشور {'کاربر' if mode == 'single' else 'اولین کاربر'} را ارسال کنید.",
                    parse_mode="HTML", reply_markup=balance_multiple_users_keyboard(sign, context.user_data.get("balance_back_callback", "admin:users"), has_users=False) if mode == "multiple" else balance_single_input_keyboard(context.user_data.get("balance_back_callback", "admin:users"))
                )
                # برای حالت تکی باید ID در پیام متنی گرفته شود؛ resource بعد از ID نمایش داده می‌شود.
                return

            if action == "balance_users_done":
                pending = context.user_data.get("balance_pending") or {}
                sign = pending.get("sign")
                if pending.get("mode") != "multiple" or not pending.get("users"):
                    await query.answer("⚠️ حداقل یک کاربر را اضافه کنید.", show_alert=True)
                    return
                await query.answer()
                await query.edit_message_text(("💰 کدام منبع را می‌خواهید اضافه کنید؟" if pending.get("sign") == "add" else "💰 کدام منبع را می‌خواهید کم کنید؟"), reply_markup=resource_keyboard(sign, pending.get("back_action", "admin:users")))
                return

            if action == "balance_country_pick" and len(parts) >= 5:
                target_id, country_id, sign = int(parts[2]), int(parts[3]), parts[4]
                pending = context.user_data.get("balance_pending") or {}
                target = get_user_by_telegram_id(session, target_id)
                if target is None or sign not in {"add", "remove"}:
                    await query.answer("⚠️ عملیات منقضی شده است.", show_alert=True); return
                countries = get_user_countries(session, target)
                country = next((c for c in countries if int(c.id) == country_id), None)
                if country is None:
                    await query.answer("❌ این کشور متعلق به کاربر نیست.", show_alert=True); return
                pending["users"] = [target_id]
                pending["country_id"] = country_id
                pending["sign"] = sign
                pending.pop("resource", None)
                context.user_data["balance_selected_user"] = target_id
                context.user_data[_waiting_scope_key("balance_selected_user")] = int(update.effective_chat.id)
                context.user_data["balance_pending"] = pending
                context.user_data[_waiting_scope_key("balance_pending")] = int(update.effective_chat.id)
                await query.answer()
                await query.edit_message_text(
                    f"🌍 <b>{escape(country.title)}</b>\n\nکدام منبع را می‌خواهید {'اضافه' if sign == 'add' else 'کم'} کنید؟",
                    parse_mode="HTML", reply_markup=resource_keyboard(sign, pending.get("back_action", f"admin:user:{target_id}"))
                ); return

            if action == "balance_resource":
                # ساختار callback: admin:balance_resource:<sign>:<resource>
                if len(parts) < 4:
                    await query.answer("❌ عملیات نامعتبر است.", show_alert=True)
                    return
                sign, resource = parts[2], parts[3]
                pending = context.user_data.get("balance_pending") or {}
                selected_user = context.user_data.get("balance_selected_user")
                if not pending.get("users") and selected_user:
                    pending["users"] = [int(selected_user)]
                if not pending.get("sign"):
                    pending["sign"] = sign
                pending.setdefault("mode", "single" if len(pending.get("users", [])) == 1 else "multiple")
                pending.setdefault("items", [])
                if pending.get("mode") == "single" and pending.get("country_id") is None and pending.get("users"):
                    target = get_user_by_telegram_id(session, int(pending["users"][0]))
                    countries = get_user_countries(session, target) if target else []
                    if len(countries) == 1:
                        pending["country_id"] = int(countries[0].id)
                    else:
                        await query.answer("⚠️ ابتدا کشور موردنظر را انتخاب کنید.", show_alert=True)
                        return
                context.user_data["balance_pending"] = pending
                context.user_data[_waiting_scope_key("balance_pending")] = int(update.effective_chat.id)
                if pending.get("sign") != sign or not pending.get("users"):
                    await query.answer("⚠️ عملیات منقضی شده است.", show_alert=True)
                    return
                pending["resource"] = resource
                context.user_data["balance_pending"] = pending
                context.user_data[_waiting_scope_key("balance_pending")] = int(update.effective_chat.id)
                names = {"money":"💰 پول", "fuel":"⛽ سوخت", "metal":"🔩 فلز", "uranium":"☢️ اورانیوم"}
                targets = [get_user_by_telegram_id(session, uid) for uid in pending.get("users", [])]
                await query.answer()
                target_countries = [get_default_country(session, t) for t in targets if t is not None]
                active_infinite = bool(target_countries) and all(bool(getattr(c, f"infinite_{resource}", False)) for c in target_countries if c is not None)
                await query.edit_message_text(f"{names[resource]}\n\nمقدار را به‌صورت عددی مثبت ارسال کنید.", parse_mode="HTML", reply_markup=balance_amount_keyboard(sign, resource, pending.get("back_action", context.user_data.get("balance_back_callback", "admin:users")), infinite_state=active_infinite))
                return

            if action == "balance_infinite" and len(parts) >= 4:
                sign, resource = parts[2], parts[3]
                pending = context.user_data.get("balance_pending") or {}
                if sign not in {"add", "remove"} or not pending.get("users"):
                    await query.answer("⚠️ عملیات منقضی شده است.", show_alert=True); return
                targets = [get_user_by_telegram_id(session, uid) for uid in pending.get("users", [])]
                if any(t is None for t in targets):
                    await query.answer("❌ یکی از کاربران در ربات ثبت نیست.", show_alert=True); return
                attr = f"infinite_{resource}"
                if not hasattr(targets[0], attr):
                    pass
                # در حالت تک/چند نفره، فعال/حذف بی‌نهایت به‌صورت یک آیتم نهایی ذخیره می‌شود.
                pending.pop("resource", None)
                pending.setdefault("items", []).append({"resource": resource, "infinite": True})
                context.user_data["balance_pending"] = pending
                context.user_data[_waiting_scope_key("balance_pending")] = int(update.effective_chat.id)
                session.commit()
                await query.answer("♾️ تنظیم بی‌نهایت ثبت شد.")
                await query.edit_message_text("📦 مورد دریافت شد.\n\nآیا کافی است یا ادامه می‌دهید؟", reply_markup=balance_continue_keyboard(sign, pending.get("back_action", "admin:users")))
                return

            if action == "balance_continue":
                pending = context.user_data.get("balance_pending") or {}
                sign = pending.get("sign")
                if not sign or not pending.get("users") or pending.get("resource"):
                    await query.answer("⚠️ ابتدا مقدار منبع را وارد کنید.", show_alert=True)
                    return
                await query.answer()
                await query.edit_message_text("➕ منبع بعدی را انتخاب کنید:", reply_markup=resource_keyboard(sign, pending.get("back_action", "admin:users")))
                return

            if action == "balance_finish":
                pending = context.user_data.get("balance_pending") or {}
                if not pending.get("users") or not pending.get("items"):
                    await query.answer("⚠️ هنوز عملیاتی برای تأیید وجود ندارد.", show_alert=True)
                    return
                names = {"money":"💰 پول", "fuel":"⛽ سوخت", "metal":"🔩 فلز", "uranium":"☢️ اورانیوم"}
                users_text = "\n".join(f"🆔 <code>{uid}</code>" for uid in pending["users"])
                def _item_text(item):
                    resource_name = names[item["resource"]]
                    if item.get("infinite"):
                        return f"{resource_name}: ♾️ {'بی‌نهایت فعال' if pending['sign'] == 'add' else 'بی‌نهایت برداشته می‌شود'}"
                    sign_text = "+" if pending["sign"] == "add" else "-"
                    return f"{resource_name}: {sign_text}{item['amount']:,.0f}"
                items_text = "\n".join(_item_text(i) for i in pending["items"])
                await query.answer()
                await query.edit_message_text(f"📦 <b>خلاصه عملیات</b>\n\n{users_text}\n\n{items_text}\n\nآیا عملیات انجام شود؟", parse_mode="HTML", reply_markup=balance_final_keyboard(pending["sign"], pending.get("back_action", context.user_data.get("balance_back_callback", "admin:users"))))
                return

            if action == "balance_commit":
                pending = context.user_data.get("balance_pending") or {}
                sign = pending.get("sign")
                user_ids = pending.get("users") or []
                items = pending.get("items") or []
                if not sign or not user_ids or not items:
                    await query.answer("⚠️ عملیات منقضی شده است.", show_alert=True)
                    return
                targets = [get_user_by_telegram_id(session, uid) for uid in user_ids]
                if any(u is None for u in targets):
                    session.rollback()
                    await query.answer("❌ یکی از کاربران دیگر در ربات ثبت نیست.", show_alert=True)
                    context.user_data.pop("balance_pending", None)
                    return
                selected_country_id = pending.get("country_id")
                for u in targets:
                    if selected_country_id is not None and pending.get("mode") == "single":
                        country = next((c for c in get_user_countries(session, u) if int(c.id) == int(selected_country_id)), None)
                    else:
                        country = get_default_country(session, u)
                    if country is None:
                        session.rollback()
                        await query.answer(f"❌ کشور موردنظر برای کاربر {u.telegram_id} پیدا نشد.", show_alert=True)
                        return
                    for item in items:
                        resource = item["resource"]
                        if item.get("infinite"):
                            setattr(country, f"infinite_{resource}", sign == "add")
                            if sign == "remove":
                                # برداشتن بی‌نهایت فقط فلگ را خاموش می‌کند و مقدار عددی دست‌نخورده می‌ماند.
                                setattr(country, f"infinite_{resource}", False)
                            continue

                selected_country_id = pending.get("country_id")
                for u in targets:
                    if selected_country_id is not None and pending.get("mode") == "single":
                        country = next((c for c in get_user_countries(session, u) if int(c.id) == int(selected_country_id)), None)
                    else:
                        country = get_default_country(session, u)
                    if country is None:
                        continue
                    for item in items:
                        if item.get("infinite"):
                            continue
                        resource = item["resource"]
                        if sign == "remove" and getattr(country, f"infinite_{resource}", False):
                            continue
                        current = getattr(country, resource)
                        delta = item["amount"] if sign == "add" else -item["amount"]
                        new_value = current + delta
                        if sign == "add":
                            new_value = min(999999999999999.0, new_value)
                        else:
                            new_value = max(0.0, new_value)
                        setattr(country, resource, new_value)
                session.commit()
                context.user_data.pop("balance_pending", None)
                names = {"money":"💰 پول", "fuel":"⛽ سوخت", "metal":"🔩 فلز", "uranium":"☢️ اورانیوم"}
                sign_text = "+" if sign == "add" else "-"
                changes_text = "\n".join((f"{names[i['resource']]}: {'♾️ بی‌نهایت فعال شد' if sign == 'add' else '♾️ بی‌نهایت برداشته شد'}" if i.get('infinite') else f"{names[i['resource']]}: {sign_text}{i['amount']:,}") for i in items)
                for u in targets:
                    await _notify_user(query.get_bot(), u.telegram_id, f"💰 <b>موجودی شما تغییر کرد.</b>\n\n{changes_text}")
                admin_changes = changes_text if len(targets) == 1 else f"{changes_text}\n\n👥 تعداد کاربران: {len(targets):,}"
                await _notify_user(query.get_bot(), query.from_user.id, f"✅ <b>تغییر موجودی انجام شد.</b>\n\n{admin_changes}")
                await query.answer("✅ عملیات موجودی با موفقیت انجام شد.", show_alert=True)
                back_action = pending.get("back_action")
                if back_action and str(back_action).startswith("admin:user_game_country:"):
                    pieces=str(back_action).split(":")
                    if len(pieces) >= 4:
                        panel_text, panel_markup = _user_game_country_panel(session, int(pieces[2]), int(pieces[3]), str(back_action))
                        if panel_text:
                            await query.edit_message_text(panel_text, parse_mode="HTML", reply_markup=panel_markup)
                            return
                if back_action and back_action.startswith("admin:user:"):
                    target_id = int(back_action.split(":")[2])
                    target = get_user_by_telegram_id(session, target_id)
                    if target:
                        role = "👑 مالک" if is_owner(target_id, OWNER_ID) else ("🛡 ادمین" if is_admin(session, target_id, OWNER_ID) else "👤 کاربر عادی")
                        back_callback = context.user_data.get("user_detail_back", back_action)
                        await query.edit_message_text(
                            "👤 <b>اطلاعات کاربر</b>\n\n"
                            f"نام: <b>{target.first_name or target.username or 'بدون نام'}</b>\n"
                            f"🆔 <code>{target.telegram_id}</code>\n"
                            f"🎭 نقش: {role}\n"
                            f"📱 شماره: {'ثبت شده' if target.phone_number else 'ثبت نشده'}",
                            parse_mode="HTML", reply_markup=user_action_keyboard(target_id, is_owner(query.from_user.id, OWNER_ID), back_callback=back_callback, banned=target.is_banned)
                        )
                        return
                await query.edit_message_text("👥 <b>مدیریت کاربران</b>", parse_mode="HTML", reply_markup=user_management_keyboard())
                return

            if action == "stats_period":
                role = parts[2] if len(parts) > 2 else "users"
                period = parts[3] if len(parts) > 3 else "all"
                if role != "users" and not is_owner(query.from_user.id, OWNER_ID):
                    await query.answer("⛔ این آمار فقط برای مالک است.", show_alert=True)
                    return
                await query.answer()
                await query.edit_message_text(_stats_text(session, role, period), parse_mode="HTML", reply_markup=stats_period_keyboard(role, period))
                return

            # آمار
            if action == "stats":
                await query.answer()
                await query.edit_message_text(
                    "📊 <b>آمار</b>\n\nنوع آمار را انتخاب کنید:",
                    parse_mode="HTML",
                    reply_markup=stats_role_keyboard(is_owner(query.from_user.id, OWNER_ID)),
                )
                return

            if action == "stats_game":
                await query.answer()
                if is_owner(query.from_user.id, OWNER_ID):
                    await query.edit_message_text(
                        "🤖 <b>آمار ربات</b>\n\nنوع آمار را انتخاب کنید:",
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("👥 آمار کاربران", callback_data="admin:stats_users")],
                            [InlineKeyboardButton("👨‍💼 آمار ادمین‌ها", callback_data="admin:stats_admins")],
                            [InlineKeyboardButton("📊 آمار همه", callback_data="admin:stats_all")],
                            [InlineKeyboardButton("🔙 برگشت", callback_data="admin:stats")],
                        ]),
                    )
                else:
                    await query.edit_message_text(
                        _stats_text(session, "users", "all"),
                        parse_mode="HTML",
                        reply_markup=stats_period_keyboard("users", "all"),
                    )
                return

            if action == "stats_bot":
                countries_count = int(session.scalar(select(func.count(Country.id))) or 0)
                groups_count = int(session.scalar(select(func.count(func.distinct(Country.chat_id)))) or 0)
                active_loans = int(session.scalar(select(func.count(BankLoan.id)).where(BankLoan.status == "active")) or 0)
                active_investments = int(session.scalar(select(func.count(BankInvestment.id)).where(BankInvestment.status == "active")) or 0)
                missiles_tech = int(session.scalar(select(func.count(BotSetting.id)).where(BotSetting.key.like("missile_tech_level:%"))) or 0)
                gold_states = session.scalars(select(BotSetting).where(BotSetting.key.like("golden:state:%"))).all()
                gold_open = gold_won = gold_expired = 0
                for row in gold_states:
                    try:
                        state=json.loads(row.value or "{}")
                    except Exception:
                        continue
                    gold_open += len(state.get("actives", {}) or {})
                    for item in (state.get("history", []) or []):
                        status=str(item.get("status", ""))
                        gold_won += int(status == "won")
                        gold_expired += int(status == "expired")
                text=(
                    "🎮 <b>آمار بازی</b>\n\n"
                    f"🌍 تعداد کشورها: <b>{countries_count:,}</b>\n"
                    f"💬 گروه‌های فعال بازی: <b>{groups_count:,}</b>\n"
                    f"💳 وام‌های فعال: <b>{active_loans:,}</b>\n"
                    f"📈 سرمایه‌گذاری‌های فعال: <b>{active_investments:,}</b>\n"
                    f"🚀 پروفایل‌های فناوری موشک ثبت‌شده: <b>{missiles_tech:,}</b>\n"
                    f"🎁 جعبه‌های باز فعلی: <b>{gold_open:,}</b>\n"
                    f"🏆 جعبه‌های برنده‌شده: <b>{gold_won:,}</b>\n"
                    f"⌛ جعبه‌های منقضی‌شده: <b>{gold_expired:,}</b>"
                )
                await query.answer()
                await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data="admin:stats")]]))
                return

            if action in {"stats_users", "stats_admins", "stats_all"}:
                if action != "stats_users" and not is_owner(query.from_user.id, OWNER_ID):
                    await query.answer("⛔ این آمار فقط برای مالک است.", show_alert=True)
                    return
                role_map = {"stats_users":"users", "stats_admins":"admins", "stats_all":"all"}
                role = role_map[action]
                await query.answer()
                await query.edit_message_text(_stats_text(session, role, "all"), parse_mode="HTML", reply_markup=stats_period_keyboard(role, "all"))
                return

            # فقط Callbackهای admin: که در شاخهٔ ادمین ناشناخته مانده‌اند باید به پنل ادمین برگردند.
            # owner: نباید هیچ‌وقت از این fallback عبور کند؛ باید ادامهٔ شاخهٔ Owner را اجرا کند.
            if namespace == "admin":
                await query.answer()
                await query.edit_message_text("⚙️ <b>پنل ادمین</b>", parse_mode="HTML", reply_markup=admin_panel_keyboard())
                return

        if data == "country_edit_waiting_back":
            state = context.user_data.get("country_edit")
            if not state:
                await query.answer("⚠️ عملیات منقضی شده است.", show_alert=True); return
            context.user_data["country_edit_waiting"] = False
            context.user_data[_waiting_scope_key("country_edit_waiting")] = int(update.effective_chat.id)
            await query.answer("🔙 برگشت")
            back = state.get("back", "settings:self_country_edit")
            if str(back).startswith("admin:user_game_settings:"):
                target_id = int(str(back).split(":")[2])
                await query.edit_message_text("⚙️ <b>تنظیمات بازی کاربر</b>", parse_mode="HTML", reply_markup=admin_user_game_settings_keyboard(target_id, context.user_data.get("user_game_settings_back", f"admin:user:{target_id}")))
                return
            await query.edit_message_text(
                "💳 <b>روش پرداخت تغییر نام کشور را انتخاب کنید:</b>",
                parse_mode="HTML",
                reply_markup=country_rename_payment_keyboard(
                    get_country_rename_money_cost(session),
                    get_country_establishment_uranium_cost(session),
                    back_callback=back
                )
            )
            return

        if data.startswith("country_rename_payment:"):
            state = context.user_data.get("country_edit")
            if not state:
                await query.answer("⚠️ عملیات منقضی شده است.", show_alert=True); return
            method = data.split(":",1)[1]
            if method not in {"money","uranium"}:
                await query.answer("❌ روش نامعتبر است.", show_alert=True); return
            enabled = get_country_rename_money_enabled(session) if method == "money" else get_country_rename_uranium_enabled(session)
            if not enabled:
                await query.answer("❌ این روش پرداخت در حال حاضر فعال نیست.", show_alert=True); return
            state["payment_method"] = method
            context.user_data["country_edit"] = state
            context.user_data[_waiting_scope_key("country_edit")] = int(update.effective_chat.id)
            context.user_data["country_edit_waiting"] = True
            context.user_data[_waiting_scope_key("country_edit_waiting")] = int(update.effective_chat.id)
            await query.answer()
            label = "پول" if method == "money" else "اورانیوم"
            await query.edit_message_text(f"✏️ نام جدید کشور را ارسال کنید.\n💳 روش پرداخت: <b>{label}</b>", parse_mode="HTML", reply_markup=country_edit_waiting_keyboard())
            return

        if data in {"country_edit_confirm", "country_edit_change", "country_edit_cancel"}:
            state = context.user_data.get("country_edit")
            if state:
                target_id = int(state.get("target_user", query.from_user.id))
                if target_id != query.from_user.id and not (is_owner(query.from_user.id, OWNER_ID) or is_admin(session, query.from_user.id, OWNER_ID)):
                    await query.answer("⛔ دسترسی غیرمجاز است.", show_alert=True); return
                if data == "country_edit_cancel":
                    back = state.get("back", "main_menu")
                    target_id = int(state.get("target_user", query.from_user.id))
                    context.user_data.pop("country_edit", None)
                    context.user_data.pop("country_edit_name", None)
                    context.user_data.pop("self_country_edit_name", None)
                    context.user_data.pop("country_edit_waiting", None)
                    await query.answer("🔙 برگشت")
                    if back == "settings_game":
                        await query.edit_message_text("🎮 <b>تنظیمات بازی</b>\n\nبخش موردنظر را انتخاب کنید.", parse_mode="HTML", reply_markup=game_settings_user_keyboard())
                    elif back.startswith("admin:user_country_edit:"):
                        target = get_user_by_telegram_id(session, target_id)
                        countries = get_user_countries(session, target) if target else []
                        await query.edit_message_text("🌍 <b>کشور موردنظر را انتخاب کنید:</b>", parse_mode="HTML", reply_markup=user_country_list_keyboard(target_id, countries, back_callback=context.user_data.get("user_game_settings_back", back)))
                    elif back.startswith("admin:user_game_settings:"):
                        await query.edit_message_text("⚙️ <b>تنظیمات بازی کاربر</b>", parse_mode="HTML", reply_markup=admin_user_game_settings_keyboard(target_id, back))
                    else:
                        await query.edit_message_text("🔙 <b>بازگشت</b>", parse_mode="HTML")
                    return
                if data == "country_edit_change":
                    context.user_data["country_edit_waiting"] = True
                    context.user_data[_waiting_scope_key("country_edit_waiting")] = int(update.effective_chat.id)
                    await query.answer()
                    await query.edit_message_text(
                        "✏️ نام جدید کشور را ارسال کنید.",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data="country_edit_cancel")]])
                    )
                    return
                name = context.user_data.get("country_edit_name") or context.user_data.get("self_country_edit_name")
                if not name:
                    await query.answer("❌ نام جدید دریافت نشده است.", show_alert=True); return
                # Resolve the country explicitly before any branch that can use it.
                # This avoids the local-variable shadowing/unbound-country error that
                # could occur in the country rename flow.
                edit_country = session.get(CountryModel, int(state.get("country_id", 0)))
                if edit_country is None:
                    await query.answer("❌ کشور پیدا نشد.", show_alert=True)
                    return
                existing_country = get_country_by_name(session, name)
                if existing_country is not None and existing_country.id != edit_country.id:
                    await query.answer("❌ این نام کشور قبلاً استفاده شده است.", show_alert=True)
                    return
                # تأسیس کشور رایگان است؛ فقط تغییر واقعی نام کشور هزینه دارد.
                # اگر کاربر همان نام قبلی را دوباره تأیید کند، هیچ مبلغی کم نمی‌شود.
                old_name = str(getattr(edit_country, "title", "") or "").strip()
                if name.strip() == old_name:
                    context.user_data.pop("country_edit", None)
                    context.user_data.pop("country_edit_name", None)
                    context.user_data.pop("self_country_edit", None)
                    context.user_data.pop("self_country_edit_name", None)
                    context.user_data.pop("country_edit_waiting", None)
                    await query.answer("ℹ️ نام کشور تغییر نکرد.", show_alert=True)
                    if target_id == query.from_user.id:
                        await query.edit_message_text("🎮 <b>تنظیمات بازی</b>\n\nبخش موردنظر را انتخاب کنید.", parse_mode="HTML", reply_markup=game_settings_user_keyboard())
                    else:
                        back_game = state.get("back", context.user_data.get("user_game_settings_back", f"admin:user_game_settings:{target_id}"))
                        await query.edit_message_text("⚙️ <b>تنظیمات بازی کاربر</b>\n\nℹ️ نام کشور تغییر نکرد.", parse_mode="HTML", reply_markup=admin_user_game_settings_keyboard(target_id, back_game))
                    return
                if target_id == query.from_user.id:
                    method = state.get("payment_method") or get_country_rename_method(session)
                    if method == "money":
                        rename_cost = get_country_rename_money_cost(session)
                        current = float(getattr(edit_country, "money", 0.0) or 0.0)
                        if rename_cost > 0 and not getattr(edit_country, "infinite_money", False):
                            if current < rename_cost:
                                await query.answer(f"❌ پول کافی نیست.\n💰 موردنیاز: {rename_cost:,.0f}\n📉 کمبود: {rename_cost-current:,.0f}", show_alert=True); return
                            edit_country.money = current - rename_cost
                    else:
                        rename_cost = get_country_establishment_uranium_cost(session)
                        current = float(getattr(edit_country, "uranium", 0.0) or 0.0)
                        if rename_cost > 0 and not getattr(edit_country, "infinite_uranium", False):
                            if current < rename_cost:
                                await query.answer(f"❌ اورانیوم کافی نیست.\n☢️ موردنیاز: {rename_cost:,.2f}\n📉 کمبود: {rename_cost-current:,.2f}", show_alert=True); return
                            edit_country.uranium = current - rename_cost
                edit_country.title = name
                session.commit()
                context.user_data.pop("country_edit", None)
                context.user_data.pop("country_edit_name", None)
                context.user_data.pop("self_country_edit", None)
                context.user_data.pop("self_country_edit_name", None)
                await query.answer("✅ نام کشور تغییر کرد.", show_alert=True)
                if target_id == query.from_user.id:
                    # پنل موفقیت جای پنل اصلی را نمی‌گیرد؛ پس از اعلان، همان صفحه تنظیمات بازی نمایش داده می‌شود.
                    await query.edit_message_text("🎮 <b>تنظیمات بازی</b>\n\nبخش موردنظر را انتخاب کنید.", parse_mode="HTML", reply_markup=game_settings_user_keyboard())
                else:
                    back_game = state.get("back", context.user_data.get("user_game_settings_back", f"admin:user_game_settings:{target_id}"))
                    await query.edit_message_text("⚙️ <b>تنظیمات بازی کاربر</b>", parse_mode="HTML", reply_markup=admin_user_game_settings_keyboard(target_id, back_game))
                return

        if data == "swap_back":
            context.user_data.pop("swap_pending", None)
            await query.answer()
            await query.edit_message_text("🎮 <b>تنظیمات بازی</b>\n\nبخش موردنظر را انتخاب کنید.", parse_mode="HTML", reply_markup=game_settings_user_keyboard())
            return

        if data == "swap_target_back":
            countries = get_user_countries(session, current_user)
            await query.answer()
            await query.edit_message_text("🔄 <b>کشور مبدأ را انتخاب کنید:</b>", parse_mode="HTML", reply_markup=swap_country_keyboard(countries))
            return

        if data.startswith("swap_from:"):
            source_id = int(data.split(":")[1])
            countries = get_user_countries(session, current_user)
            if not any(cn.id == source_id for cn in countries):
                await query.answer("⛔ کشور نامعتبر است.", show_alert=True); return
            targets = [cn for cn in countries if cn.id != source_id]
            context.user_data["swap_pending"] = {"source_id": source_id, "country_ids": [c.id for c in countries]}
            context.user_data[_waiting_scope_key("swap_pending")] = int(update.effective_chat.id)
            await query.answer()
            await query.edit_message_text("🔄 کشور مقصد را انتخاب کنید:", reply_markup=swap_target_keyboard(targets, source_id))
            return

        if data.startswith("swap_to:"):
            _, source_s, target_s = data.split(":")
            source_id, target_id = int(source_s), int(target_s)
            countries = get_user_countries(session, current_user)
            if {source_id, target_id} - {cn.id for cn in countries}:
                await query.answer("⛔ کشور نامعتبر است.", show_alert=True); return
            a = session.get(CountryModel, source_id)
            b = session.get(CountryModel, target_id)
            if not a or not b:
                await query.answer("❌ کشور پیدا نشد.", show_alert=True); return
            context.user_data["swap_pending"] = {"source_id": source_id, "target_id": target_id}
            context.user_data[_waiting_scope_key("swap_pending")] = int(update.effective_chat.id)
            await query.answer()
            await query.edit_message_text(
                f"🔄 <b>تأیید جابه‌جایی</b>\n\n🌍 مبدأ: <b>{a.title}</b>\n🌍 مقصد: <b>{b.title}</b>\n\nتمام اطلاعات بازی این دو کشور جابه‌جا خواهد شد.\n\nآیا مطمئن هستید؟",
                parse_mode="HTML", reply_markup=swap_confirm_keyboard(source_id, target_id)
            )
            return

        if data.startswith("swap_confirm:"):
            _, source_s, target_s = data.split(":")
            pending = context.user_data.get("swap_pending") or {}
            if int(pending.get("source_id", -1)) != int(source_s) or int(pending.get("target_id", -1)) != int(target_s):
                await query.answer("⚠️ عملیات منقضی شده است.", show_alert=True); return
            a = session.get(CountryModel, int(source_s))
            b = session.get(CountryModel, int(target_s))
            if not a or not b:
                await query.answer("❌ کشور پیدا نشد.", show_alert=True); return
            cooldown = get_swap_cooldown_hours(session)
            last_swap = get_swap_last_at(session, query.from_user.id)
            if cooldown > 0 and last_swap is not None:
                remaining = cooldown * 3600 - (datetime.utcnow() - last_swap).total_seconds()
                if remaining > 0:
                    hours = int(remaining // 3600)
                    minutes = int((remaining % 3600) // 60)
                    await query.answer(f"⏳ هنوز {hours} ساعت و {minutes} دقیقه تا جابه‌جایی بعدی باقی مانده است.", show_alert=True)
                    return
            _swap_country_state(session, a, b)
            set_swap_last_at(session, query.from_user.id, datetime.utcnow())
            session.commit(); context.user_data.pop("swap_pending", None)
            await query.answer("✅ جابه‌جایی با موفقیت انجام شد.", show_alert=True)
            await query.edit_message_text("🎮 <b>تنظیمات بازی</b>\n\nبخش موردنظر را انتخاب کنید.", parse_mode="HTML", reply_markup=game_settings_user_keyboard())
            return

        if data in {"country_name_confirm", "country_name_change", "country_name_cancel", "country_name_edit_back"}:
            # تأیید/تعویض نام کشور فقط برای فرآیند تأسیس اولیه در گروه.
            pending_name = context.user_data.get(f"country_name_value_{query.from_user.id}")
            if data == "country_name_edit_back":
                # از صفحه «ویرایش نام» همیشه دقیقاً به همان صفحه تأیید/ویرایش/لغو برگرد.
                pending_name = context.user_data.get(f"country_name_value_{query.from_user.id}")
                if not pending_name:
                    await query.answer("❌ نام موقت کشور پیدا نشد.", show_alert=True)
                    return
                context.user_data[f"country_name_pending_{query.from_user.id}"] = False
                await query.answer("برگشتید")
                await query.edit_message_text(
                    f"🌍 نام کشور انتخابی: <b>{pending_name}</b>\n\nآیا تأیید می‌کنید؟",
                    parse_mode="HTML",
                    reply_markup=country_name_confirm_keyboard(),
                )
                return
            if not pending_name:
                await query.answer("❌ نام کشوری برای تأیید وجود ندارد.", show_alert=True)
                return
            if data == "country_name_cancel":
                context.user_data.pop(f"country_name_value_{query.from_user.id}", None)
                context.user_data.pop(f"country_name_pending_{query.from_user.id}", None)
                await query.answer("لغو شد.")
                await query.edit_message_text("❌ تأسیس کشور لغو شد.")
                return
            if data == "country_name_change":
                context.user_data[f"country_name_pending_{query.from_user.id}"] = True
                await query.answer()
                await query.edit_message_text("✏️ نام جدید کشور را ارسال کنید.\n\nبرای برگشت، دکمه زیر را بزنید.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data="country_name_edit_back")]]))
                return

            chat = query.message.chat if query.message else None
            if chat is None or chat.type not in ("group", "supergroup"):
                await query.answer("❌ این عملیات فقط داخل گروه انجام می‌شود.", show_alert=True)
                return
            user = current_user
            existing_in_group = get_user_country_in_continent(session, user, chat.id)
            if existing_in_group is not None:
                await query.answer(
                    f"❌ شما در این گروه قبلاً کشور «{escape(str(existing_in_group.title))}» را دارید.",
                    show_alert=True,
                )
                return
            if get_country_by_name(session, pending_name) is not None:
                await query.answer("❌ این نام کشور قبلاً انتخاب شده است.", show_alert=True)
                return
            country = create_country(session, chat, pending_name, query.from_user)
            if country is None:
                session.rollback()
                await query.answer("❌ این نام کشور قبلاً انتخاب شده است.", show_alert=True)
                return
            register_user_in_country(session, user, country)
            user.default_country_id = country.id
            context.user_data.pop(f"country_name_value_{query.from_user.id}", None)
            context.user_data.pop(f"country_name_pending_{query.from_user.id}", None)
            session.commit()
            success_text = (
                "🎉 <b>کشور با موفقیت تأسیس شد!</b>\n\n"
                + country_status(country, get_metal_mine_config(session), get_arsenal_config(session), _country_shield_status(session, country))
            )
            await query.answer("کشور با موفقیت تأسیس شد.")
            prompt_id = context.user_data.pop(f"country_creation_prompt_{query.from_user.id}", None)
            start_id = context.user_data.pop(f"country_creation_start_{query.from_user.id}", None)
            name_message_id = context.user_data.pop(f"country_creation_name_message_{query.from_user.id}", None)
            if prompt_id:
                try:
                    await query.get_bot().edit_message_text(
                        chat_id=chat.id,
                        message_id=int(prompt_id),
                        text=success_text,
                        parse_mode="HTML",
                    )
                except Exception:
                    pass
            # هم پیام شروع بازی و هم پیام انتخاب نام، ۳۰ ساعت بعد پاک شوند.
            for mid in (prompt_id, start_id, name_message_id):
                if mid:
                    try:
                        context.application.create_task(_delete_message_after(query.get_bot(), chat.id, int(mid), 30.0))
                    except Exception:
                        pass
            if not prompt_id:
                try:
                    await query.edit_message_text(success_text, parse_mode="HTML")
                except Exception:
                    pass
            return

        if data == "settings:game":
            await query.answer()
            await query.edit_message_text("🎮 <b>تنظیمات بازی</b>\n\nبخش موردنظر را انتخاب کنید:", parse_mode="HTML", reply_markup=game_settings_user_keyboard())
            return

        if data.startswith("delete_group_pick:"):
            try:
                country_id = int(data.split(":",1)[1])
            except (ValueError, IndexError):
                await query.answer("❌ کشور نامعتبر است.", show_alert=True); return
            country = session.scalar(select(CountryModel).where(CountryModel.id == country_id))
            if country is None:
                await query.answer("❌ کشور پیدا نشد.", show_alert=True); return
            owned = get_user_countries(session, current_user)
            if country.id not in {c.id for c in owned}:
                await query.answer("⛔ دسترسی ندارید.", show_alert=True); return
            await query.answer()
            await query.edit_message_text(
                f"⚠️ <b>آیا مطمئن هستید؟</b>\n\nهمه اطلاعات کشور <b>{country.title}</b> در این گروه برای همیشه حذف می‌شود.",
                parse_mode="HTML", reply_markup=delete_group_confirm_keyboard(country.id)
            )
            return

        if data.startswith("delete_group_confirm:"):
            try:
                country_id = int(data.split(":",1)[1])
            except (ValueError, IndexError):
                await query.answer("❌ کشور نامعتبر است.", show_alert=True); return
            country = session.scalar(select(CountryModel).where(CountryModel.id == country_id))
            if country is None:
                await query.answer("❌ این گروه قبلاً حذف شده است.", show_alert=True); return
            owned = get_user_countries(session, current_user)
            if country.id not in {c.id for c in owned}:
                await query.answer("⛔ دسترسی ندارید.", show_alert=True); return
            for u in session.scalars(select(User).where(User.default_country_id == country.id)).all():
                u.default_country_id = None
            _delete_country_dependencies(session, country.id)
            session.execute(delete(UserCountry).where(UserCountry.country_id == country.id))
            session.delete(country)
            session.commit()
            remaining = get_user_countries(session, current_user)
            await query.answer("🗑️ کشور و تمام اطلاعات آن حذف شد.", show_alert=True)
            if remaining:
                await query.edit_message_text("🗑️ <b>حذف کشور</b>\n\nکشوری را که می‌خواهید تمام اطلاعاتش حذف شود انتخاب کنید:", parse_mode="HTML", reply_markup=delete_group_keyboard(remaining))
            else:
                await query.edit_message_text("🎮 <b>تنظیمات بازی</b>\n\nبخش موردنظر را انتخاب کنید:", parse_mode="HTML", reply_markup=game_settings_user_keyboard())
            return

        if data.startswith("delete_group_cancel"):
            remaining = get_user_countries(session, current_user)
            await query.answer("لغو شد.")
            if remaining:
                await query.edit_message_text("🗑️ <b>حذف کشور</b>\n\nکشوری را که می‌خواهید تمام اطلاعاتش حذف شود انتخاب کنید:", parse_mode="HTML", reply_markup=delete_group_keyboard(remaining))
            else:
                await query.edit_message_text("🎮 <b>تنظیمات بازی</b>\n\nبخش موردنظر را انتخاب کنید:", parse_mode="HTML", reply_markup=game_settings_user_keyboard())
            return

        if data.startswith("settings:"):
            if data == "settings:user_info":
                target=current_user
                role = "👑 مالک" if is_owner(target.telegram_id, OWNER_ID) else ("🛡 ادمین" if is_admin(session, target.telegram_id, OWNER_ID) else "👤 کاربر عادی")
                await query.answer()
                await query.edit_message_text(
                    "👤 <b>اطلاعات کاربر</b>\n\n"
                    f"نام: <b>{escape(str(target.first_name or target.username or 'بدون نام'))}</b>\n"
                    f"🆔 آیدی: <code>{target.telegram_id}</code>\n"
                    f"🔤 نام کاربری: {(('@' + target.username) if target.username else 'ثبت نشده')}\n"
                    f"🎭 نقش: {role}\n"
                    f"📱 شماره: {escape(str(target.phone_number or 'ثبت نشده'))}",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data="settings:game")]])
                )
                return
            if data == "settings:self_country_edit":
                countries = get_user_countries(session, current_user)
                if not countries:
                    await query.answer("❌ هنوز کشوری ثبت نشده است.", show_alert=True); return
                await query.answer()
                await query.edit_message_text("🌍 <b>کشوری را که می‌خواهید نامش را ویرایش کنید انتخاب کنید:</b>", parse_mode="HTML", reply_markup=self_country_edit_list_keyboard(countries))
                return
            if data.startswith("settings:country_edit_pick:"):
                country_id = int(data.split(":")[-1])
                edit_country = session.get(CountryModel, country_id)
                if owner_user:
                    allowed_country = edit_country is not None
                else:
                    allowed_country = edit_country is not None and any(c.id == country_id for c in get_user_countries(session, current_user))
                if not allowed_country:
                    await query.answer("⛔ این کشور متعلق به شما نیست.", show_alert=True); return
                context.user_data["self_country_edit"] = True
                context.user_data[_waiting_scope_key("self_country_edit")] = int(update.effective_chat.id)
                context.user_data["self_country_edit_name"] = None
                context.user_data[_waiting_scope_key("self_country_edit_name")] = int(update.effective_chat.id)
                context.user_data["country_edit"] = {"target_user": query.from_user.id, "country_id": edit_country.id, "back": "settings:self_country_edit", "country_list_back": "settings:self_country_edit"}
                context.user_data[_waiting_scope_key("country_edit")] = int(update.effective_chat.id)
                context.user_data["country_edit_waiting"] = False
                context.user_data[_waiting_scope_key("country_edit_waiting")] = int(update.effective_chat.id)
                await query.answer()
                await query.edit_message_text("💳 <b>روش پرداخت تغییر نام کشور را انتخاب کنید:</b>", parse_mode="HTML", reply_markup=country_rename_payment_keyboard(get_country_rename_money_cost(session), get_country_establishment_uranium_cost(session)))
                return
            if data == "settings:delete_group":
                countries = get_user_countries(session, current_user)
                if not countries:
                    await query.answer("❌ هنوز هیچ کشوری برای حذف ندارید.", show_alert=True); return
                await query.answer()
                await query.edit_message_text(
                    "🗑️ <b>حذف کشور</b>\n\nکشوری را که می‌خواهید تمام اطلاعاتش حذف شود انتخاب کنید:",
                    parse_mode="HTML", reply_markup=delete_group_keyboard(countries)
                )
                return

            if data == "settings:swap":
                cooldown = get_swap_cooldown_hours(session)
                last_swap = get_swap_last_at(session, query.from_user.id)
                if cooldown > 0 and last_swap is not None:
                    remaining = cooldown * 3600 - (datetime.utcnow() - last_swap).total_seconds()
                    if remaining > 0:
                        hours = int(remaining // 3600)
                        minutes = int((remaining % 3600) // 60)
                        await query.answer(f"⏳ هنوز {hours} ساعت و {minutes} دقیقه تا جابه‌جایی بعدی باقی مانده است.", show_alert=True)
                        return
                countries = get_user_countries(session, current_user)
                if len(countries) < 2:
                    await query.answer("⚠️ برای جابجایی حداقل دو کشور لازم است.", show_alert=True); return
                context.user_data["swap_pending"] = {"country_ids": [c.id for c in countries]}
                context.user_data[_waiting_scope_key("swap_pending")] = int(update.effective_chat.id)
                await query.answer(); await query.edit_message_text("🔄 <b>کشور مبدأ را انتخاب کنید:</b>", parse_mode="HTML", reply_markup=swap_country_keyboard(countries)); return
            return

        # ---- Optional advertisement timer ----
        if data.startswith("social:optional_timer:"):
            ad_id = data.split(":", 2)[2]
            from services.social_rewards import _claimed
            entry = get_optional_pending_entry(session, query.from_user.id, ad_id)
            if _claimed(session, query.from_user.id, ad_id):
                await query.answer("🎁 پاداش این تبلیغ قبلاً واریز شده است.", show_alert=True)
                return
            if not entry or not entry.get("at"):
                await query.answer("❌ برای این تبلیغ زمان فعالی وجود ندارد.", show_alert=True)
                return
            ad = next((x for x in get_social_items(session, "optional_ad") if str(x.get("id")) == str(ad_id)), None)
            if not ad or not bool(ad.get("active", True)):
                await query.answer("❌ این تبلیغ دیگر فعال نیست.", show_alert=True)
                return
            target = ad.get("chat_id") or public_chat_target(ad.get("url"))
            joined = False
            if target:
                try:
                    member = await query.get_bot().get_chat_member(target, query.from_user.id)
                    status = getattr(member, "status", "")
                    joined = status not in {"left", "kicked", "restricted"} or bool(getattr(member, "is_member", False))
                except Exception:
                    joined = False
            if not joined:
                await query.answer("⚠️ شما از این مورد خارج شده‌اید. ابتدا دوباره عضو شوید.", show_alert=True)
                return
            try:
                joined_at = datetime.fromisoformat(str(entry.get("at")))
                if joined_at.tzinfo is None:
                    joined_at = joined_at.replace(tzinfo=timezone.utc)
            except Exception:
                await query.answer("❌ زمان عضویت قابل محاسبه نیست.", show_alert=True)
                return
            remaining = max(0, int((joined_at + timedelta(minutes=optional_reward_delay_minutes(ad)) - datetime.now(timezone.utc)).total_seconds()))
            if remaining <= 0:
                await query.answer("⏳ زمان تعیین‌شده تمام شده؛ پرداخت پاداش در حال بررسی است.", show_alert=True)
                return
            h, rem = divmod(remaining, 3600); m, sec = divmod(rem, 60)
            if h:
                txt = f"{h} ساعت و {m} دقیقه"
            elif m:
                txt = f"{m} دقیقه و {sec} ثانیه"
            else:
                txt = f"{sec} ثانیه"
            await query.answer(f"⏱️ زمان باقی‌مانده: {txt}", show_alert=True)
            return

        # ---- Optional advertisement membership check (normal users too) ----
        if data == "social:optional_check" or data.startswith("social:optional_check:"):
            # تأیید عضویت فقط تایمر یک‌ساعته را شروع می‌کند؛ پاداش در این مرحله پرداخت نمی‌شود.
            active = get_active_social_items(session, "optional_ad")
            started = []
            missing = []
            now = datetime.now(timezone.utc)
            for ad in active:
                ad_id = ad.get("id")
                if is_optional_claimed(session, query.from_user.id, ad_id) or is_optional_pending(session, query.from_user.id, ad_id):
                    continue
                target = ad.get("chat_id") or public_chat_target(ad.get("url"))
                if not target:
                    continue
                try:
                    member = await query.get_bot().get_chat_member(target, query.from_user.id)
                    status = getattr(member, "status", "")
                    joined = status not in {"left", "kicked", "restricted"} or bool(getattr(member, "is_member", False))
                except Exception:
                    joined = False
                if not joined:
                    missing.append(ad)
                    continue
                key = f"social_optional_join:{query.from_user.id}"
                row = session.scalar(select(BotSetting).where(BotSetting.key == key))
                meta = {}
                if row and row.value:
                    try: meta = json.loads(row.value)
                    except Exception: meta = {}
                # یک کاربر می‌تواند هم‌زمان برای چند تبلیغ تایمر جداگانه داشته باشد.
                entries = meta.get("ads") if isinstance(meta.get("ads"), dict) else {}
                if str(ad_id) not in entries:
                    entries[str(ad_id)] = {"at": now.isoformat(), "left_notified": False}
                    started.append(ad)
                if row is None:
                    session.add(BotSetting(key=key, value=json.dumps({"ads": entries}, ensure_ascii=False)))
                else:
                    row.value = json.dumps({"ads": entries}, ensure_ascii=False)
            session.commit()
            if started:
                # تبلیغ ثبت‌شده دیگر در پنل تبلیغات نمایش داده نمی‌شود؛ به‌جای آن پیام تایمر ارسال می‌شود.
                for ad in started:
                    ad_id = ad.get("id")
                    target = ad.get("chat_id") or public_chat_target(ad.get("url"))
                    try:
                        chat = await query.get_bot().get_chat(target) if target else None
                        title = getattr(chat, "title", None) or getattr(chat, "username", None) or "تبلیغ اختیاری"
                    except Exception:
                        title = "تبلیغ اختیاری"
                    await query.get_bot().send_message(
                        query.from_user.id,
                        optional_timer_text(title, ad.get("reward", 0), now, now, optional_reward_delay_minutes(ad)),
                        parse_mode="HTML",
                        reply_markup=optional_timer_markup(ad_id),
                    )
                # پنل قبلی را فقط برای تبلیغ‌هایی که هنوز ثبت نشده‌اند نگه می‌داریم.
                if missing:
                    rows = []
                    for ad in missing:
                        url = social_item_button_url(ad.get("url"))
                        if url:
                            reward = float(ad.get("reward", 0) or 0)
                            rows.append([InlineKeyboardButton(f"🎁 تبلیغ اختیاری — ☢️ {reward:,.0f}", url=url)])
                    if rows:
                        try:
                            await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(rows))
                        except Exception:
                            pass
                else:
                    try:
                        await query.message.delete()
                    except Exception:
                        pass
                await query.answer("✅ عضویت شما ثبت شد؛ یک ساعت دیگر در صورت لفت ندادن پاداش واریز می‌شود.", show_alert=True)
            elif missing:
                await query.answer("❌ ابتدا عضو تبلیغ شوید و سپس «ثبت عضویت» را بزنید.", show_alert=True)
            else:
                await query.answer("✅ عضویت قبلاً ثبت شده یا تبلیغ جدیدی برای ثبت وجود ندارد.", show_alert=True)
            return

        # فروشگاه سپر کاربر
        # -------------------------------------------------
        # قالب callbackهای فروشگاه سپر: shield:<action>:...
        if data.startswith("shield:"):
            shield_parts = data.split(":")
            shield_action = shield_parts[1] if len(shield_parts) > 1 else ""

            if shield_action == "types":
                from keyboards.main import shield_purchase_type_keyboard
                await query.answer()
                await query.edit_message_text(
                    "🛡️ <b>خرید سپر</b>\n\nلطفاً نوع سپر را انتخاب کنید:",
                    parse_mode="HTML",
                    reply_markup=shield_purchase_type_keyboard(),
                )
                return

            if shield_action == "list" and len(shield_parts) >= 4:
                typ = shield_parts[2]
                page = max(1, int(shield_parts[3] or 1))
                items = get_shield_items(session, typ, active_only=True)
                if not items:
                    await query.answer("❌ فعلاً سپری موجود نیست.", show_alert=True)
                    return
                await query.answer()
                await query.edit_message_text(
                    f"🛡️ <b>{'سپرهای جهانی' if typ == 'global' else 'سپرهای قاره‌ای'}</b>\n\nسپر موردنظر را انتخاب کنید:",
                    parse_mode="HTML",
                    reply_markup=shield_purchase_list_keyboard(items, typ, page),
                )
                return

            if shield_action == "buy" and len(shield_parts) >= 3:
                item_id = shield_parts[2]
                item = get_shield_item_by_id(session, item_id)
                target = get_user_by_telegram_id(session, query.from_user.id)
                country = get_default_country(session, target) if target else None
                if not item or not item.get("active"):
                    await query.answer("🔒 این سپر دیگر فعال نیست.", show_alert=True); return
                if not country:
                    await query.answer("❌ ابتدا کشور پیش‌فرض خود را انتخاب کنید.", show_alert=True); return
                cooldown = shield_purchase_cooldown_remaining(session, query.from_user.id, item_id, int(country.id))
                if cooldown > 0:
                    h, rem = divmod(cooldown, 3600); m, _ = divmod(rem, 60)
                    await query.answer(f"⏳ محدودیت خرید مجدد دارید؛ تا {h} ساعت و {m} دقیقه دیگر امکان خرید این سپر نیست.", show_alert=True); return
                price=float(item.get("price",0) or 0); uranium=float(getattr(country,"uranium",0) or 0)
                if not bool(getattr(country,"infinite_uranium",False)) and uranium < price:
                    await query.answer("❌ اورانیوم کافی نیست.", show_alert=True); return
                pending = {"item_id": str(item_id), "chat_id": int(query.message.chat_id if query.message else 0)}
                context.user_data["shield_purchase_pending"] = pending
                await query.answer()
                from keyboards.main import shield_purchase_confirm_keyboard
                await query.edit_message_text(
                    f"🛡️ <b>تأیید خرید سپر</b>\n\n"
                    f"🛡️ نام: <b>{escape(str(item.get('name','سپر')))}</b>\n"
                    f"☢️ قیمت: <b>{price:,.0f}</b> اورانیوم\n"
                    f"⏱ مدت فعال بودن: <b>{float(item.get('duration_hours',0) or 0):g} ساعت</b>\n"
                    f"🔁 فاصله خرید مجدد: <b>{float(item.get('cooldown_hours',0) or 0):g} ساعت</b>\n\n"
                    "آیا خرید این سپر را تأیید می‌کنید؟",
                    parse_mode="HTML", reply_markup=shield_purchase_confirm_keyboard(item_id)
                ); return

            if shield_action == "confirm" and len(shield_parts) >= 3:
                item_id = shield_parts[2]
                pending = context.user_data.get("shield_purchase_pending") or {}
                if str(pending.get("item_id")) != str(item_id) or int(pending.get("chat_id",0) or 0) != int(query.message.chat_id if query.message else 0):
                    await query.answer("❌ این درخواست خرید دیگر معتبر نیست.", show_alert=True); return
                item = get_shield_item_by_id(session, item_id); target=get_user_by_telegram_id(session, query.from_user.id); country=get_default_country(session,target) if target else None
                if not item or not item.get("active"):
                    context.user_data.pop("shield_purchase_pending",None); await query.answer("🔒 این سپر دیگر فعال نیست.",show_alert=True); return
                if not country:
                    context.user_data.pop("shield_purchase_pending",None); await query.answer("❌ ابتدا کشور پیش‌فرض خود را انتخاب کنید.",show_alert=True); return
                ok,msg,expires=purchase_shield(session,query.from_user.id,item_id,country)
                if not ok: await query.answer(msg,show_alert=True); return
                context.user_data.pop("shield_purchase_pending",None); session.commit()
                items=get_shield_items(session,item.get("type"),active_only=True)
                await query.answer("✅ سپر با موفقیت خریداری و فعال شد.",show_alert=True)
                await query.edit_message_text(f"🛡️ <b>{'سپرهای جهانی' if item.get('type')=='global' else 'سپرهای قاره‌ای'}</b>\n\nسپر موردنظر را برای خرید انتخاب کنید:",parse_mode="HTML",reply_markup=shield_purchase_list_keyboard(items,item.get('type')))
                return

            if shield_action == "cancel" and len(shield_parts) >= 3:
                context.user_data.pop("shield_purchase_pending",None)
                await query.answer("خرید لغو شد.")
                item=get_shield_item_by_id(session,shield_parts[2]); typ=item.get('type') if item else 'global'; items=get_shield_items(session,typ,active_only=True)
                await query.edit_message_text(f"🛡️ <b>{'سپرهای جهانی' if typ=='global' else 'سپرهای قاره‌ای'}</b>\n\nسپر موردنظر را برای خرید انتخاب کنید:",parse_mode="HTML",reply_markup=shield_purchase_list_keyboard(items,typ)); return

            if shield_action == "noop":
                await query.answer()
                return


        if data.startswith("construction:"):
            construction_parts=data.split(":")
            action=construction_parts[1] if len(construction_parts) > 1 else "open"
            country=get_context_country(session,user, query.message.chat_id if query.message else None)
            if not country:
                await query.answer("❌ کشور پیش‌فرضی انتخاب نشده است.",show_alert=True); return
            if action in {"open","back"}:
                if action=="back":
                    await query.answer(); await query.edit_message_text("🏪 <b>فروشگاه تسلیحات</b>\n\nبرای خرید، گزینه زیر را انتخاب کنید.",parse_mode="HTML"); return
                # same renderer used after a purchase
            if action == "buy":
                team=int(construction_parts[2]) if len(construction_parts) >= 3 else 0
                quotes=team_purchase_quotes(session,country)
                quote=next((q for q in quotes if int(q[0]) == team), None)
                if not quote:
                    await query.answer("❌ این تیم قابل خرید نیست.",show_alert=True); return
                team,price,purchased,max_teams=quote
                balance=float(country.money or 0)
                if float(price or 0)>balance and not bool(getattr(country,"infinite_money",False)):
                    await query.answer(f"❌ موجودی کافی نیست.\nقیمت: {price:,.0f}\nموجودی: {balance:,.0f}\nکمبود: {price-balance:,.0f}",show_alert=True); return
                text=(f"🏗️ <b>خرید تیم ساخت‌وساز {team}</b>\n\n💰 قیمت: <b>{price:,.0f}</b> پول\n💳 موجودی شما: <b>{balance:,.0f}</b> پول\n\nآیا از خرید این تیم مطمئن هستید؟")
                context.user_data["construction_buy_pending"]={"team":team,"country_id":int(country.id)}
                await query.answer(); await query.edit_message_text(text,parse_mode="HTML",reply_markup=__import__("telegram",fromlist=["InlineKeyboardButton","InlineKeyboardMarkup"]).InlineKeyboardMarkup([[__import__("telegram",fromlist=["InlineKeyboardButton"]).InlineKeyboardButton("✅ خرید",callback_data="construction:buy_confirm")],[__import__("telegram",fromlist=["InlineKeyboardButton"]).InlineKeyboardButton("🔙 برگشت",callback_data="construction:open")]])); return
            if action == "buy_confirm":
                pending=context.user_data.get("construction_buy_pending") or {}
                if int(pending.get("country_id",0))!=int(country.id):
                    await query.answer("❌ درخواست خرید منقضی شده است.",show_alert=True); return
                ok,res,quote=buy_team(session,country,int(pending.get("team",0) or 0))
                context.user_data.pop("construction_buy_pending",None)
                if not ok:
                    if isinstance(res,dict):
                        await query.answer(f"❌ موجودی کافی نیست.\nقیمت: {res['price']:,.0f}\nموجودی: {res['balance']:,.0f}\nکمبود: {res['missing']:,.0f}",show_alert=True)
                    else:
                        await query.answer("❌ تیم بعدی قابل خرید نیست.",show_alert=True)
                    return
                session.commit()
                cfg,state,info=get_team_status(session,country)
                lines=["🏗️ <b>تیم‌های ساخت‌وساز</b>","",f"ظرفیت فعال: <b>{info['active_capacity']}/{info['max']}</b>",f"خریداری‌شده: <b>{info['purchased']}</b>"]
                for slot,assignment in info["visible"]:
                    if assignment:
                        try: rem=max(0,int((datetime.fromisoformat(assignment.get('until'))-datetime.utcnow()).total_seconds()))
                        except Exception: rem=0
                        h,rr=divmod(rem,3600); m,sec=divmod(rr,60)
                        lines.append(f"🏗️ تیم {slot} — 🔴 مشغول\n└ {assignment.get('label','ارتقا')}\n└ زمان باقی‌مانده: {h:02d}:{m:02d}:{sec:02d}")
                    else:
                        lines.append(f"🏗️ تیم {slot} — 🟢 آزاد")
                await query.answer("✅ تیم ساخت‌وساز با موفقیت خریداری شد.",show_alert=True)
                await query.edit_message_text("\n".join(lines),parse_mode="HTML",reply_markup=construction_teams_user_keyboard(team_purchase_quotes(session,country))); return
            # construction:open renderer
            cfg,state,info=get_team_status(session,country)
            lines=["🏗️ <b>تیم‌های ساخت‌وساز</b>","",f"ظرفیت فعال: <b>{info['active_capacity']}/{info['max']}</b>",f"خریداری‌شده: <b>{info['purchased']}</b>"]
            for slot,assignment in info["visible"]:
                if assignment:
                    try: rem=max(0,int((datetime.fromisoformat(assignment.get('until'))-datetime.utcnow()).total_seconds()))
                    except Exception: rem=0
                    h,rr=divmod(rem,3600); m,sec=divmod(rr,60)
                    lines.append(f"🏗️ تیم {slot} — 🔴 مشغول\n└ {assignment.get('label','ارتقا')}\n└ زمان باقی‌مانده: {h:02d}:{m:02d}:{sec:02d}")
                else:
                    lines.append(f"🏗️ تیم {slot} — 🟢 آزاد")
            if info["overflow"]:
                lines.append(f"\n⏳ تیم‌های مازاد در حال اتمام کار: <b>{len(info['overflow'])}</b>")
            await query.answer(); await query.edit_message_text("\n".join(lines),parse_mode="HTML",reply_markup=construction_teams_user_keyboard(team_purchase_quotes(session,country))); return

        if data.startswith("golden:"):
            parts=data.split(":"); sub=parts[1] if len(parts)>1 else ""
            if sub=="back_hq":
                country=get_context_country(session,user, query.message.chat_id if query.message else None)
                if country is None:
                    await query.answer("❌ کشور پیش‌فرضی انتخاب نشده است.",show_alert=True); return
                cfg=get_hq_config(session)
                status=construction_label(country,"command_center")
                await query.answer()
                await query.edit_message_text(
                    hq_info(country,cfg), parse_mode="HTML",
                    reply_markup=hq_keyboard(
                        can_upgrade_hq(country,cfg)[0],
                        built=int(country.command_center_level)>0,
                        construction_text=status,
                        in_progress=bool(status),
                        finish_uranium_cost=hq_instant_finish_uranium_cost(country,cfg),
                        build_uranium=float(hq_build_cost(cfg).get("uranium",0))>0,
                        upgrade_uranium=float((hq_upgrade_cost(country.command_center_level,cfg) or {}).get("uranium",0))>0,
                    )
                )
                return
            if sub=="upgrade":
                country=get_context_country(session,user, query.message.chat_id if query.message else None)
                if not country: await query.answer("❌ ابتدا کشور پیش‌فرض خود را انتخاب کنید.",show_alert=True); return
                cfg=golden_config(session); st=golden_state(session,country.id)
                lines=["🎁 <b>ارتقای جعبه‌ها</b>","","سطح فعلی هر جعبه:"]
                rows=[]
                for k,(icon,name) in GOLDEN_BOXES.items():
                    lv=int(st['levels'].get(k,1)); mx=int(cfg['levels'][k]['max_level']); pending=st.get('upgrades',{}).get(k)
                    if pending:
                        target=int(pending.get('target', lv))
                        lines.append(f"{icon} <b>{name}</b> — در حال ارتقا به سطح <b>{target}</b>")
                    else:
                        lines.append(f"{icon} <b>{name}</b> — سطح <b>{lv}</b>")
                    if pending:
                        instant=float(cfg['levels'][k].get('instant_finish_uranium',0) or 0)
                        rows.append([InlineKeyboardButton("❌ لغو",callback_data=f"golden:cancel_confirm:{k}",style="danger"), InlineKeyboardButton(f"⚡ تکمیل فوری ({instant:g} ☢️)",callback_data=f"golden:instant_confirm:{k}",style="primary")])
                    elif lv < mx:
                        rows.append([InlineKeyboardButton(f"⬆️ ارتقاء {name}",callback_data=f"golden:box:{k}",style="primary")])
                    else:
                        lines.append("└ ⭐ حداکثر سطح")
                rows.append([InlineKeyboardButton("🔙 برگشت",callback_data="golden:back_hq")])
                await query.answer(); await query.edit_message_text("\n".join(lines),parse_mode="HTML",reply_markup=InlineKeyboardMarkup(rows)); return
            if sub=="box" and len(parts)>=3:
                country=get_context_country(session,user, query.message.chat_id if query.message else None)
                if not country: await query.answer("❌ کشور پیش‌فرضی ندارید.",show_alert=True); return
                k=parts[2]; cfg=golden_config(session); st=golden_state(session,country.id)
                if k not in GOLDEN_BOXES: await query.answer("❌ جعبه نامعتبر است.",show_alert=True); return
                lv=int(st['levels'].get(k,1)); mx=int(cfg['levels'][k]['max_level'])
                if lv>=mx: await query.answer("⭐ این جعبه به حداکثر سطح رسیده است.",show_alert=True); return
                nxt=lv+1; cost=golden_cost_for(cfg,k,nxt); hq_req=golden_hq_required_for(cfg,k,nxt); icon,name=GOLDEN_BOXES[k]
                if int(getattr(country, 'command_center_level', 0) or 0) < hq_req:
                    await query.answer(f"❌ برای ارتقای جعبه {name} به سطح {nxt}، مرکز فرماندهی باید حداقل سطح {hq_req} باشد.", show_alert=True); return
                lines=["🎁 <b>تأیید ارتقای جعبه</b>","",f"{icon} <b>{name}</b>",f"📌 سطح فعلی: <b>{lv}</b>",f"⬆️ سطح بعدی: <b>{nxt}</b>",f"💰 هزینه ارتقا: <b>{cost:,.0f}</b> پول",f"⏱ زمان ارتقا: <b>{int(cfg['levels'][k].get('upgrade_times',{}).get(str(nxt),0) or 0)} ثانیه</b>",f"🏛️ مرکز فرماندهی لازم: <b>سطح {hq_req}</b>","","آیا ارتقا را تأیید می‌کنید؟"]
                rows=[[InlineKeyboardButton(f"✅ تأیید ارتقاء {name}",callback_data=f"golden:upgrade_confirm:{k}",style='success')],[InlineKeyboardButton("🔙 برگشت",callback_data="golden:upgrade")]]
                await query.answer(); await query.edit_message_text("\n".join(lines),parse_mode="HTML",reply_markup=InlineKeyboardMarkup(rows)); return
            if sub=="cancel_confirm" and len(parts)>=3:
                country=get_context_country(session,user, query.message.chat_id if query.message else None); k=parts[2]
                if not country or k not in GOLDEN_BOXES:
                    await query.answer("❌ درخواست نامعتبر است.",show_alert=True); return
                st=golden_state(session,country.id); pending=st.get('upgrades',{}).get(k)
                if not pending:
                    await query.answer("ℹ️ این جعبه در حال ارتقا نیست.",show_alert=True); return
                cost=float(pending.get('cost',golden_cost_for(golden_config(session),k,int(pending.get('target',1)))) or 0)
                refund=cost*0.5
                await query.answer(); await query.edit_message_text(
                    f"❌ <b>لغو ارتقای جعبه {GOLDEN_BOXES[k][1]}</b>\n\n"
                    f"💰 هزینه ارتقا: <b>{cost:,.0f}</b> پول\n"
                    f"↩️ مبلغ بازگشتی (۵۰٪): <b>{refund:,.0f}</b> پول\n\n"
                    "آیا از لغو ارتقا مطمئن هستید؟",parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ تأیید لغو",callback_data=f"golden:cancel:{k}",style="danger")],[InlineKeyboardButton("🔙 برگشت",callback_data="golden:upgrade")]])
                ); return
            if sub=="cancel" and len(parts)>=3:
                country=get_context_country(session,user, query.message.chat_id if query.message else None); k=parts[2]
                if not country or k not in GOLDEN_BOXES:
                    await query.answer("❌ درخواست نامعتبر است.",show_alert=True); return
                cfg=golden_config(session); st=golden_state(session,country.id); pending=st.get('upgrades',{}).get(k)
                if not pending:
                    await query.answer("ℹ️ این جعبه دیگر در حال ارتقا نیست.",show_alert=True); return
                cost=float(pending.get('cost',golden_cost_for(cfg,k,int(pending.get('target',1)))) or 0); refund=cost*0.5
                if not bool(getattr(country,'infinite_money',False)):
                    country.money=float(country.money or 0)+refund
                st.setdefault('upgrades',{}).pop(k,None); golden_save_state(session,country.id,st); session.commit()
                await query.answer("✅ ارتقا لغو شد و ۵۰٪ هزینه برگشت.",show_alert=True)
                # fall through to the common upgrade renderer by recreating it inline
                lines=["🎁 <b>ارتقای جعبه‌ها</b>","","سطح فعلی هر جعبه:"]; rows=[]
                for kk,(ic,nm) in GOLDEN_BOXES.items():
                    cur=int(st['levels'].get(kk,1)); mm=int(cfg['levels'][kk]['max_level']); pend=st.get('upgrades',{}).get(kk)
                    if pend:
                        target=int(pend.get('target', cur))
                        lines.append(f"{ic} <b>{nm}</b> — در حال ارتقا به سطح <b>{target}</b>")
                    else:
                        lines.append(f"{ic} <b>{nm}</b> — سطح <b>{cur}</b>")
                    if pend:
                        instant=float(cfg['levels'][kk].get('instant_finish_uranium',0) or 0); rows.append([InlineKeyboardButton("❌ لغو",callback_data=f"golden:cancel_confirm:{kk}",style="danger"),InlineKeyboardButton(f"⚡ تکمیل فوری ({instant:g} ☢️)",callback_data=f"golden:instant_confirm:{kk}",style="primary")])
                    elif cur<mm: rows.append([InlineKeyboardButton(f"⬆️ ارتقاء {nm}",callback_data=f"golden:box:{kk}",style="primary")])
                    else: lines.append("└ ⭐ حداکثر سطح")
                rows.append([InlineKeyboardButton("🔙 برگشت",callback_data="golden:back_hq")]); await query.edit_message_text("\n".join(lines),parse_mode="HTML",reply_markup=InlineKeyboardMarkup(rows)); return
            if sub=="instant_confirm" and len(parts)>=3:
                country=get_context_country(session,user, query.message.chat_id if query.message else None); k=parts[2]
                if not country or k not in GOLDEN_BOXES:
                    await query.answer("❌ درخواست نامعتبر است.",show_alert=True); return
                cfg=golden_config(session); st=golden_state(session,country.id); pending=st.get('upgrades',{}).get(k)
                if not pending:
                    await query.answer("ℹ️ این جعبه در حال ارتقا نیست.",show_alert=True); return
                uranium=float(cfg['levels'][k].get('instant_finish_uranium',0) or 0)
                if uranium<=0:
                    await query.answer("❌ هزینه اورانیوم تکمیل فوری برای این جعبه تنظیم نشده است.",show_alert=True); return
                if not bool(getattr(country,'infinite_uranium',False)) and float(country.uranium or 0)<uranium:
                    await query.answer(f"❌ اورانیوم کافی نیست. هزینه: {uranium:g} | موجودی: {float(country.uranium or 0):g}",show_alert=True); return
                if not bool(getattr(country,'infinite_uranium',False)): country.uranium=float(country.uranium or 0)-uranium
                target=int(pending.get('target',st['levels'].get(k,1))); st['levels'][k]=max(int(st['levels'].get(k,1)),target); st.setdefault('upgrades',{}).pop(k,None); golden_save_state(session,country.id,st); session.commit()
                await query.answer("⚡ ارتقا فوراً تکمیل شد.",show_alert=True)
                lines=["🎁 <b>ارتقای جعبه‌ها</b>","","سطح فعلی هر جعبه:"]; rows=[]
                for kk,(ic,nm) in GOLDEN_BOXES.items():
                    cur=int(st['levels'].get(kk,1)); mm=int(cfg['levels'][kk]['max_level']); pend=st.get('upgrades',{}).get(kk)
                    if pend:
                        target=int(pend.get('target', cur))
                        lines.append(f"{ic} <b>{nm}</b> — در حال ارتقا به سطح <b>{target}</b>")
                    else:
                        lines.append(f"{ic} <b>{nm}</b> — سطح <b>{cur}</b>")
                    if pend:
                        instant2=float(cfg['levels'][kk].get('instant_finish_uranium',0) or 0); rows.append([InlineKeyboardButton("❌ لغو",callback_data=f"golden:cancel_confirm:{kk}",style="danger"),InlineKeyboardButton(f"⚡ تکمیل فوری ({instant2:g} ☢️)",callback_data=f"golden:instant_confirm:{kk}",style="primary")])
                    elif cur<mm: rows.append([InlineKeyboardButton(f"⬆️ ارتقاء {nm}",callback_data=f"golden:box:{kk}",style="primary")])
                    else: lines.append("└ ⭐ حداکثر سطح")
                rows.append([InlineKeyboardButton("🔙 برگشت",callback_data="golden:back_hq")]); await query.edit_message_text("\n".join(lines),parse_mode="HTML",reply_markup=InlineKeyboardMarkup(rows)); return
            if sub=="upgrade_confirm" and len(parts)>=3:
                country=get_context_country(session,user, query.message.chat_id if query.message else None); k=parts[2]
                if not country or k not in GOLDEN_BOXES: await query.answer("❌ درخواست نامعتبر است.",show_alert=True); return
                cfg=golden_config(session); st=golden_state(session,country.id); lv=int(st['levels'].get(k,1)); mx=int(cfg['levels'][k]['max_level'])
                if lv>=mx: await query.answer("⭐ به حداکثر سطح رسیده است.",show_alert=True); return
                hq_req=golden_hq_required_for(cfg,k,lv+1)
                if int(getattr(country, 'command_center_level', 0) or 0) < hq_req:
                    await query.answer(f"❌ برای ارتقای این جعبه به سطح {lv+1}، مرکز فرماندهی باید حداقل سطح {hq_req} باشد.", show_alert=True); return
                if st.get('upgrades',{}).get(k):
                    await query.answer("⏳ ارتقای این جعبه در حال انجام است.",show_alert=True); return
                cost=golden_cost_for(cfg,k,lv+1)
                if not bool(getattr(country,'infinite_money',False)) and float(country.money or 0)<cost: await query.answer(f"❌ پول کافی نیست.\nهزینه: {cost:,.0f}\nموجودی: {float(country.money or 0):,.0f}\nکمبود: {cost-float(country.money or 0):,.0f}",show_alert=True); return
                if not bool(getattr(country,'infinite_money',False)): country.money=float(country.money or 0)-cost
                duration=max(0,int(cfg['levels'][k].get('upgrade_times',{}).get(str(lv+1),0) or 0))
                if duration>0:
                    st.setdefault('upgrades',{})[k]={'target':lv+1,'cost':cost,'finish_at':(datetime.utcnow()+timedelta(seconds=duration)).isoformat()}
                    golden_save_state(session,country.id,st)
                    await query.answer("⏳ ارتقا شروع شد.",show_alert=True)
                else:
                    st['levels'][k]=lv+1; golden_save_state(session,country.id,st)
                    await query.answer("✅ ارتقای جعبه با موفقیت انجام شد.",show_alert=True)
                # بعد از تأیید، همان پنل اصلی ارتقا با متن واحد دوباره رندر می‌شود.
                lines=["🎁 <b>ارتقای جعبه‌ها</b>","","سطح فعلی هر جعبه:"]
                rows=[]
                for kk,(ic,nm) in GOLDEN_BOXES.items():
                    cur=int(st['levels'].get(kk,1)); mm=int(cfg['levels'][kk]['max_level']); pending=st.get('upgrades',{}).get(kk)
                    if pending:
                        target=int(pending.get('target', cur))
                        lines.append(f"{ic} <b>{nm}</b> — در حال ارتقا به سطح <b>{target}</b>")
                    else:
                        lines.append(f"{ic} <b>{nm}</b> — سطح <b>{cur}</b>")
                    if pending:
                        instant=float(cfg['levels'][kk].get('instant_finish_uranium',0) or 0)
                        rows.append([InlineKeyboardButton("❌ لغو",callback_data=f"golden:cancel_confirm:{kk}",style="danger"), InlineKeyboardButton(f"⚡ تکمیل فوری ({instant:g} ☢️)",callback_data=f"golden:instant_confirm:{kk}",style="primary")])
                    elif cur < mm:
                        rows.append([InlineKeyboardButton(f"⬆️ ارتقاء {nm}",callback_data=f"golden:box:{kk}",style="primary")])
                    else:
                        lines.append("└ ⭐ حداکثر سطح")
                rows.append([InlineKeyboardButton("🔙 برگشت",callback_data="golden:back_hq")])
                await query.edit_message_text("\n".join(lines),parse_mode="HTML",reply_markup=InlineKeyboardMarkup(rows)); return
            if sub=="answer" and len(parts)>=5:
                try:
                    cid=int(parts[2])
                except Exception:
                    await query.answer("❌ درخواست نامعتبر است.", show_alert=True)
                    return
                token=parts[3]
                choice=parts[4]
                # callback_data may contain the Country row that existed when the box
                # was published. That row can be deleted later, while the group and its
                # active box are still valid. Validate against the real Telegram chat and
                # the group-level box state instead of requiring the old Country row.
                country=session.scalar(select(Country).where(Country.id == cid))
                actual_chat_id=int(query.message.chat_id if query.message else 0)
                if country is not None and int(country.chat_id) != actual_chat_id:
                    await query.answer("❌ این جعبه مربوط به همین گروه نیست.", show_alert=True)
                    return
                token_chat_prefix = str(token).split('-', 1)[0]
                if token_chat_prefix.lstrip('-').isdigit() and int(token_chat_prefix) != actual_chat_id:
                    await query.answer("❌ این جعبه مربوط به همین گروه نیست.", show_alert=True)
                    return
                # A box belongs to the group, not to one particular player/country.
                # Resolve the participant's country by the actual Telegram chat so a
                # user who belongs to another country in the same group is accepted too.
                participant_country = get_user_country_in_continent(session, user, actual_chat_id)
                if participant_country is None and country is not None and int(getattr(country, 'leader_user_id', 0) or 0) == int(query.from_user.id):
                    participant_country = country
                if participant_country is None:
                    await query.answer("❌ شما عضو هیچ کشوری در این گروه نیستید.", show_alert=True)
                    return
                # Active boxes, history and daily-send bookkeeping are group-level.
                # The participant's country remains separate and is used only for its
                # level/reward progression. This prevents a deleted/replaced country
                # row from orphaning a still-active Telegram group box.
                st=golden_group_state(session, actual_chat_id)
                actives=st.get('actives') or {}
                active=actives.get(token) or {}
                if active.get('token')!=token or active.get('status')!='open':
                    await query.answer("⏰ این جعبه دیگر فعال نیست.", show_alert=True)
                    return
                uid=int(query.from_user.id)
                if uid in [int(x) for x in active.get('wrong',[])]:
                    await query.answer("❌ شما قبلاً پاسخ اشتباه داده‌اید.", show_alert=True)
                    return
                if choice != active.get('answer'):
                    active.setdefault('wrong',[]).append(uid)
                    actives[token]=active
                    st['actives']=actives
                    golden_save_group_state(session, actual_chat_id, st)
                    await query.answer("❌ پاسخ غلط است.", show_alert=True)
                    return
                # Claim the winner atomically so two simultaneous correct callbacks
                # can never both receive the same box reward.
                from services.atomic_claims import claim_once
                if not claim_once(session, f"golden:claim:{token}", str(uid)):
                    await query.answer("⚠️ این جعبه همین الان توسط کاربر دیگری باز شد.", show_alert=True)
                    return
                cfg=golden_config(session)
                box=active.get('box')
                if box not in GOLDEN_BOXES:
                    await query.answer("❌ نوع جعبه نامعتبر است.", show_alert=True)
                    return
                participant_state = golden_state(session, int(participant_country.id))
                lv = int(participant_state.get('levels', {}).get(box, 1) or 1)
                amount = golden_reward_for(cfg, box, lv)
                golden_apply_reward(participant_country, box, amount)
                active['status']='won'
                active['winner_id']=uid
                active['reward']=amount
                active['won_at']=datetime.utcnow().isoformat()
                st['history'].append(active)
                actives.pop(token,None)
                st['actives']=actives
                golden_save_group_state(session, actual_chat_id, st)
                try:
                    await query.edit_message_caption(
                        caption=(
                            f"🏆 <b>جعبه {GOLDEN_BOXES[box][1]} باز شد!</b>\n\n"
                            f"👤 برنده: <b>{escape(query.from_user.first_name or 'کاربر')}</b>\n"
                            f"🎁 جایزه: <b>{amount:,.0f}</b> {GOLDEN_BOXES[box][1]}\n"
                            "✅ پاسخ صحیح بود و جایزه پرداخت شد."
                        ),
                        parse_mode="HTML",
                        reply_markup=None,
                    )
                except Exception:
                    pass
                delay=int(cfg.get('opened_delete_seconds',30) or 0)
                if delay>0:
                    async def _del():
                        await _asyncio.sleep(delay)
                        try:
                            await context.bot.delete_message(chat_id=actual_chat_id,message_id=query.message.message_id)
                        except Exception:
                            pass
                    context.application.create_task(_del())
                await query.answer(f"🏆 پاسخ صحیح بود؛ {amount:,.0f} {GOLDEN_BOXES[box][1]} دریافت کردید.",show_alert=True)
                return

        if data.startswith("bank:"):
            parts = data.split(":"); sub = parts[1] if len(parts) > 1 else "open"
            cfg = get_bank_config(session)
            country = get_context_country(session, user, query.message.chat_id if query.message else None)
            if not country:
                countries=get_user_countries(session,user)
                msg="🌍 شما هنوز هیچ کشوری ندارید. ابتدا از «شروع بازی» یک کشور ایجاد کنید." if not countries else "🌍 شما کشور دارید، اما هیچ کشور پیش‌فرضی ندارید. ابتدا از تنظیمات بازی یک کشور پیش‌فرض انتخاب کنید."
                await query.answer(msg, show_alert=True); return
            acc=ensure_bank_account(session,country)
            now=datetime.utcnow()
            def locked_bank_panel():
                level=max(1,int(country.bank_level or 1)); level_cfg=bank_level_config(session,level) or {}
                unlock_cost=float((level_cfg.get("loan",{}) or {}).get("bank_unlock_cost",0) or 0)
                remain=max(0.0,(acc.bank_locked_until-datetime.utcnow()).total_seconds())/3600.0 if acc.bank_locked_until else 0.0
                text=(f"🏦 <b>بانک مرکزی</b>\n\n🔒 <b>بانک مرکزی شما موقتاً بسته است.</b>\n⏳ زمان باقی‌مانده: <b>{remain:.2f} ساعت</b>\n💰 غرامت بازگشایی: <b>{unlock_cost:,.0f}</b> پول")
                return text, central_bank_locked_keyboard(unlock_cost>0)

            if acc.bank_locked_until and acc.bank_locked_until > now and sub not in {"open", "unlock", "unlock_confirm"}:
                text, keyboard = locked_bank_panel()
                await query.answer("🔒 ابتدا بانک مرکزی را باز کنید.", show_alert=True)
                await query.edit_message_text(text,parse_mode="HTML",reply_markup=keyboard); return
            if sub == "open":
                if acc.bank_locked_until and acc.bank_locked_until > datetime.utcnow():
                    text, keyboard = locked_bank_panel()
                    await query.answer(); await query.edit_message_text(text,parse_mode="HTML",reply_markup=keyboard); return
                # برگشت از هر زیرپنل بانک باید واقعاً به پنل اصلی بانک مرکزی برگردد.
                # قبلاً فقط حالت قفل در این callback مدیریت می‌شد و حالت عادی به
                # fallback می‌رسید و پیام «این بخش در مرحله بعدی تکمیل می‌شود» نشان می‌داد.
                finalize_construction(country)
                level=max(1,int(country.bank_level or 1))
                can_upgrade=level < bank_max_level(session)
                text=_bank_user_level_text(session,country)
                await query.answer()
                await query.edit_message_text(
                    text,
                    parse_mode="HTML",
                    reply_markup=central_bank_keyboard(True,can_upgrade,False,0),
                )
                return
            if sub == "unlock":
                if not acc.bank_locked_until or acc.bank_locked_until <= datetime.utcnow():
                    await query.answer("ℹ️ بانک مرکزی در حال حاضر باز است.",show_alert=True); return
                level=max(1,int(country.bank_level or 1)); level_cfg=bank_level_config(session,level) or {}; cost=float((level_cfg.get("loan",{}) or {}).get("bank_unlock_cost",0) or 0)
                if cost<=0:
                    await query.answer("❌ هزینه بازگشایی بانک برای این سطح توسط Owner تنظیم نشده است.",show_alert=True); return
                await query.answer()
                remain=max(0.0,(acc.bank_locked_until-datetime.utcnow()).total_seconds())/3600.0
                text=(f"🔓 <b>بازگشایی بانک مرکزی</b>\n\n⏳ زمان باقی‌مانده: <b>{remain:.2f} ساعت</b>\n💰 غرامت بازگشایی: <b>{cost:,.0f}</b> پول\n\nآیا غرامت را پرداخت می‌کنید و بانک را همین حالا باز می‌کنید؟")
                keyboard=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ تأیید پرداخت و بازگشایی",callback_data="bank:unlock_confirm",style="success")],
                ])
                await query.edit_message_text(text,parse_mode="HTML",reply_markup=keyboard); return
            if sub == "unlock_confirm":
                if not acc.bank_locked_until or acc.bank_locked_until <= datetime.utcnow():
                    await query.answer("ℹ️ بانک مرکزی در حال حاضر باز است.",show_alert=True); return
                level=max(1,int(country.bank_level or 1)); level_cfg=bank_level_config(session,level) or {}; cost=float((level_cfg.get("loan",{}) or {}).get("bank_unlock_cost",0) or 0)
                if cost<=0:
                    await query.answer("❌ هزینه بازگشایی بانک برای این سطح توسط Owner تنظیم نشده است.",show_alert=True); return
                if not bool(getattr(country,"infinite_money",False)) and float(country.money or 0)+1e-9 < cost:
                    await query.answer(f"❌ پول کافی نیست. هزینه بازگشایی: {cost:,.0f} پول",show_alert=True); return
                if not bool(getattr(country,"infinite_money",False)):
                    country.money=float(country.money or 0)-cost
                acc.bank_locked_until=None; session.commit()
                await query.answer("✅ بانک مرکزی باز شد.",show_alert=True)
                # Re-render the normal bank panel.
                finalize_construction(country); session.flush()
                remaining,target_build=construction_remaining(country,"bank")
                level=max(1,int(country.bank_level or 1)); can_upgrade=level < bank_max_level(session)
                await query.edit_message_text(_bank_user_level_text(session,country),parse_mode="HTML",reply_markup=central_bank_keyboard(True,can_upgrade,False,0))
                return
            if sub == "build_panel":
                if int(country.bank_level or 0)>0:
                    await query.answer("🏦 بانک مرکزی قبلاً ساخته شده است.",show_alert=True); return
                await query.answer("لغو شد.")
                await query.edit_message_text("🏦 <b>بانک مرکزی</b>\n\nهنوز بانک مرکزی ساخته نشده است.",parse_mode="HTML",reply_markup=central_bank_keyboard(built=False))
                return

            if sub == "build":
                finalize_construction(country)
                current=int(country.bank_level or 0)
                if construction_remaining(country, "bank")[0] > 0:
                    await query.answer("⏳ ساخت یا ارتقای بانک مرکزی از قبل در حال انجام است.", show_alert=True); return
                if current>0: await query.answer("🏦 بانک مرکزی قبلاً ساخته شده است.",show_alert=True); return
                text=_bank_build_upgrade_text(session,country,1,"ساخت")
                await query.answer(); await query.edit_message_text(text,parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏗️ تأیید ساخت بانک مرکزی",callback_data="bank:build_confirm",style="success")],[InlineKeyboardButton("🔙 برگشت",callback_data="bank:open")]])); return

            if sub == "build_confirm":
                finalize_construction(country)
                current=int(country.bank_level or 0)
                if construction_remaining(country, "bank")[0] > 0:
                    await query.answer("⏳ ساخت یا ارتقای بانک مرکزی از قبل در حال انجام است.", show_alert=True); return
                if current>0: await query.answer("🏦 بانک مرکزی قبلاً ساخته شده است.",show_alert=True); return
                d=bank_level_config(session,1); b=d.get("build_cost",{}); hq=int(d.get("required_hq_level",1) or 1)
                if int(country.command_center_level or 0)<hq: await query.answer(f"❌ سطح مرکز فرماندهی کافی نیست. موردنیاز: {hq}",show_alert=True); return
                for r in ("money","metal","fuel","uranium"):
                    amount=float(b.get(r,0) or 0)
                    if amount>0 and not resource_available(country,r,amount): await query.answer("❌ منابع کافی نیست.",show_alert=True); return
                hours=float(d.get("build_time_hours",0) or 0)
                if hours > 0 and reserve_team(session,country,"bank","🏦 ساخت بانک مرکزی",datetime.utcnow()+timedelta(hours=hours)) is None:
                    await query.answer("⛔ تمام تیم‌های ساخت‌وساز شما مشغول هستند. برای انجام Upgrade هم‌زمان بیشتر، یک تیم ساخت‌وساز دیگر تهیه کنید.",show_alert=True); return
                for r in ("money","metal","fuel","uranium"):
                    amount=float(b.get(r,0) or 0)
                    if amount>0 and not getattr(country,f"infinite_{r}",False): setattr(country,r,float(getattr(country,r,0) or 0)-amount)
                if not start_construction(country,"bank",1,hours):
                    release_team(session,country,"bank")
                    session.rollback(); await query.answer("⏳ ساخت بانک مرکزی از قبل در حال انجام است.", show_alert=True); return
                session.commit()
                remaining,_=construction_remaining(country,"bank")
                if remaining>0:
                    cost=bank_instant_finish_uranium_cost(country,session)
                    await query.answer("🏗️ ساخت بانک مرکزی شروع شد.",show_alert=True); await query.edit_message_text(f"🏦 <b>ساخت بانک مرکزی</b>\n\n⏳ زمان باقی‌مانده: <b>{remaining/3600:,.2f} ساعت</b>\n☢️ تکمیل فوری: <b>{cost:,.2f}</b> اورانیوم",parse_mode="HTML",reply_markup=central_bank_keyboard(in_progress=True, finish_uranium_cost=bank_instant_finish_uranium_cost(country,session)))
                else:
                    await query.answer("🎉 بانک مرکزی ساخته شد.",show_alert=True); await query.edit_message_text(_bank_user_level_text(session,country),parse_mode="HTML",reply_markup=central_bank_keyboard(built=True,can_upgrade=(bank_max_level(session)>1)))
                return

            if sub == "upgrade":
                current=int(country.bank_level or 0); target=current+1
                if current<=0 or current>=bank_max_level(session): await query.answer("❌ سطح بعدی بانک مرکزی در دسترس نیست.",show_alert=True); return
                text=_bank_build_upgrade_text(session,country,target,"ارتقا")
                await query.answer(); await query.edit_message_text(text,parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"⬆️ تأیید ارتقا به سطح {target}",callback_data="bank:upgrade_confirm")],[InlineKeyboardButton("🔙 برگشت",callback_data="bank:open")]])); return

            if sub == "upgrade_confirm":
                finalize_construction(country)
                current=int(country.bank_level or 0); target=current+1
                if construction_remaining(country, "bank")[0] > 0:
                    await query.answer("⏳ ساخت یا ارتقای بانک مرکزی از قبل در حال انجام است.", show_alert=True); return
                if current<=0 or current>=bank_max_level(session): await query.answer("❌ سطح بعدی بانک مرکزی در دسترس نیست.",show_alert=True); return
                d=bank_level_config(session,target); c=d.get("upgrade_cost",{})
                if int(country.command_center_level or 0)<int(d.get("required_hq_level",1) or 1): await query.answer("❌ سطح مرکز فرماندهی کافی نیست.",show_alert=True); return
                for r in ("money","metal","fuel","uranium"):
                    amount=float(c.get(r,0) or 0)
                    if amount>0 and not resource_available(country,r,amount): await query.answer("❌ منابع کافی نیست.",show_alert=True); return
                hours=float(d.get("upgrade_time_hours",0) or 0)
                if hours > 0 and reserve_team(session,country,"bank",f"🏦 ارتقای بانک مرکزی به سطح {target}",datetime.utcnow()+timedelta(hours=hours)) is None:
                    await query.answer("⛔ تمام تیم‌های ساخت‌وساز شما مشغول هستند. برای انجام Upgrade هم‌زمان بیشتر، یک تیم ساخت‌وساز دیگر تهیه کنید.",show_alert=True); return
                for r in ("money","metal","fuel","uranium"):
                    amount=float(c.get(r,0) or 0)
                    if amount>0 and not getattr(country,f"infinite_{r}",False): setattr(country,r,float(getattr(country,r,0) or 0)-amount)
                if not start_construction(country,"bank",target,hours):
                    release_team(session,country,"bank")
                    session.rollback(); await query.answer("⏳ ساخت یا ارتقای بانک مرکزی از قبل در حال انجام است.", show_alert=True); return
                session.commit(); remaining,_=construction_remaining(country,"bank")
                await query.answer("⬆️ ارتقای بانک مرکزی شروع شد.",show_alert=True); await query.edit_message_text(f"🏦 <b>ارتقای بانک مرکزی به سطح {target}</b>\n\n⏳ زمان باقی‌مانده: <b>{remaining/3600:,.2f} ساعت</b>",parse_mode="HTML",reply_markup=central_bank_keyboard(in_progress=True, finish_uranium_cost=bank_instant_finish_uranium_cost(country,session))); return

            if sub == "cancel":
                await query.answer()
                await query.edit_message_text(
                    "⚠️ <b>لغو ساخت/ارتقای بانک مرکزی</b>\n\nآیا مطمئن هستید که می‌خواهید عملیات را لغو کنید؟",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 بله، برگشت", callback_data="bank:cancel_confirm", style="danger")],
                        [InlineKeyboardButton("🔙 ادامه عملیات", callback_data="bank:open")]
                    ])
                )
                return

            if sub == "cancel_confirm":
                old_level=int(country.bank_level or 0)
                ok, res = cancel_bank_construction(country, session)
                if not ok:
                    await query.answer("❌ ساخت/ارتقای بانک مرکزی در حال انجام نیست.", show_alert=True); return
                session.commit()
                await query.answer("❌ ساخت/ارتقا لغو شد و ۵۰٪ منابع برگشت داده شد.", show_alert=True)
                if old_level > 0:
                    text=_bank_user_level_text(session,country)
                    await query.edit_message_text(text,parse_mode="HTML",reply_markup=central_bank_keyboard(built=True,can_upgrade=(old_level<bank_max_level(session))))
                else:
                    d=bank_level_config(session,1); b=d.get("build_cost",{}) or {}
                    cap=float(d.get("deposit_capacity",0) or 0); profit=float(d.get("deposit_hourly_profit_percent",0) or 0)
                    text=(f"🏗️ <b>ساخت بانک مرکزی — سطح ۱</b>\n\n"
                          f"🏛️ سطح مرکز فرماندهی مورد نیاز: <b>{int(d.get('required_hq_level',1) or 1)}</b>\n"
                          f"⏱️ زمان تکمیل: <b>{float(d.get('build_time_hours',0) or 0):g} ساعت</b>\n\n"
                          f"💰 پول: <b>{float(b.get('money',0) or 0):,.0f}</b>\n"
                          f"🔩 فلز: <b>{float(b.get('metal',0) or 0):,.0f}</b>\n"
                          f"⛽ سوخت: <b>{float(b.get('fuel',0) or 0):,.0f}</b>\n"
                          f"☢️ اورانیوم: <b>{float(b.get('uranium',0) or 0):,.2f}</b>\n\n"
                          f"📦 ظرفیت سپرده: <b>{cap:,.0f}</b>\n"
                          f"📈 سود سپرده: <b>{profit:g}%</b> در ساعت")
                    await query.edit_message_text(text,parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏗️ ساخت بانک مرکزی",callback_data="bank:build",style="success")]]))
                return

            if sub == "finish_now":
                cost=bank_instant_finish_uranium_cost(country,session)
                if cost<=0: await query.answer("❌ ساخت/ارتقای بانک مرکزی در حال انجام نیست.",show_alert=True); return
                if not resource_available(country,"uranium",cost): await query.answer(f"❌ اورانیوم کافی نیست. موردنیاز: {cost:,.2f}",show_alert=True); return
                ok,res=finish_bank_construction_now(country,session)
                if not ok: await query.answer("❌ تکمیل فوری انجام نشد.",show_alert=True); return
                session.commit(); await query.answer(f"✅ بانک مرکزی فوراً تکمیل شد. مصرف: {float(res):,.2f} اورانیوم",show_alert=True); return
            if sub == "deposit":
                acc=accrue_bank_profit(session,country); session.flush()
                await query.answer(); await query.edit_message_text(
                    f"💰 <b>سپرده بانک مرکزی</b>\n\n💰 اصل سپرده: <b>{acc.deposit_principal:,.0f}</b>\n📈 سود قابل برداشت: <b>{acc.accrued_profit:,.0f}</b>\n📦 ظرفیت کل: <b>{bank_deposit_capacity(session,country):,.0f}</b>\n\nگزینه موردنظر را انتخاب کنید.",
                    parse_mode="HTML", reply_markup=central_bank_deposit_keyboard(acc.deposit_principal, acc.accrued_profit)); return
            if sub == "withdraw_principal":
                from services.atomic_claims import claim_once
                if not claim_once(session, f"bank:withdraw_principal:{int(country.id)}:{int(float((ensure_bank_account(session,country)).deposit_principal or 0))}", str(query.from_user.id)):
                    await query.answer("⚠️ برداشت اصل سپرده هم‌اکنون در حال انجام است.",show_alert=True); return
                amount=bank_withdraw_principal(session,country)
                if amount<=0:
                    await query.answer("ℹ️ سپرده‌ای برای دریافت وجود ندارد.",show_alert=True); return
                session.commit(); await query.answer(f"✅ {amount:,.0f} پول از اصل سپرده دریافت شد.",show_alert=True)
                acc=accrue_bank_profit(session,country); session.flush()
                await query.edit_message_text(f"💰 <b>سپرده بانک مرکزی</b>\n\n💰 اصل سپرده: <b>{acc.deposit_principal:,.0f}</b>\n📈 سود قابل دریافت: <b>{acc.accrued_profit:,.0f}</b>\n📦 ظرفیت کل: <b>{bank_deposit_capacity(session,country):,.0f}</b>\n\nگزینه موردنظر را انتخاب کنید.",parse_mode="HTML",reply_markup=central_bank_deposit_keyboard(acc.deposit_principal, acc.accrued_profit)); return
            if sub == "withdraw_profit":
                from services.atomic_claims import claim_once
                if not claim_once(session, f"bank:withdraw_profit:{int(country.id)}:{int(float((ensure_bank_account(session,country)).accrued_profit or 0))}", str(query.from_user.id)):
                    await query.answer("⚠️ برداشت سود سپرده هم‌اکنون در حال انجام است.",show_alert=True); return
                amount=bank_withdraw_profit(session,country)
                if amount<=0:
                    await query.answer("ℹ️ سودی برای دریافت وجود ندارد.",show_alert=True); return
                session.commit(); await query.answer(f"✅ {amount:,.0f} پول از سود سپرده دریافت شد.",show_alert=True)
                acc=accrue_bank_profit(session,country); session.flush()
                await query.edit_message_text(f"💰 <b>سپرده بانک مرکزی</b>\n\n💰 اصل سپرده: <b>{acc.deposit_principal:,.0f}</b>\n📈 سود قابل دریافت: <b>{acc.accrued_profit:,.0f}</b>\n📦 ظرفیت کل: <b>{bank_deposit_capacity(session,country):,.0f}</b>\n\nگزینه موردنظر را انتخاب کنید.",parse_mode="HTML",reply_markup=central_bank_deposit_keyboard(acc.deposit_principal, acc.accrued_profit)); return
            if sub == "deposit_input":
                acc=accrue_bank_profit(session,country); session.flush(); capacity=bank_deposit_capacity(session,country); remaining=max(0,capacity-acc.deposit_principal)
                if remaining <= 0:
                    await query.answer("📦 ظرفیت سپرده پر است.", show_alert=True); return
                context.user_data["bank_pending"]={"action":"deposit","country_id":country.id,"prompt_chat_id":int(query.message.chat_id),"prompt_message_id":int(query.message.message_id)}; context.user_data[_waiting_scope_key("bank_pending")]=int(query.message.chat_id)
                await query.answer(); await query.edit_message_text(f"💰 <b>سپرده‌گذاری بانک مرکزی</b>\n\n💰 سپرده فعلی: <b>{acc.deposit_principal:,.0f}</b>\n📦 ظرفیت باقی‌مانده: <b>{remaining:,.0f}</b>\n\nمبلغی که می‌خواهید سپرده‌گذاری کنید را ارسال کنید.",parse_mode="HTML",reply_markup=central_bank_deposit_input_keyboard()); return
            if sub == "loans":
                await query.answer(); await query.edit_message_text("💳 <b>وام بانک مرکزی</b>\n\nاز این بخش می‌توانید وام‌های فعال و سوابق وام خود را ببینید.",parse_mode="HTML",reply_markup=central_bank_loans_keyboard()); return
            if sub == "loan_request":
                level=max(1,int(country.bank_level or 0)); d=bank_level_config(session,level); loan_cfg=d.get("loan",{}) or {}
                try: policy=policy_from_level_config(d)
                except Exception: await query.answer("❌ تنظیمات وام این سطح کامل نیست.",show_alert=True); return
                active_count=len(session.scalars(select(BankLoan).where(BankLoan.country_id==country.id, BankLoan.status=="active")).all())
                if active_count >= policy.max_active_loans: await query.answer("❌ به حداکثر تعداد وام فعال رسیده‌اید.",show_alert=True); return
                context.user_data["bank_pending"]={"action":"loan_amount","country_id":country.id,"prompt_chat_id":int(query.message.chat_id),"prompt_message_id":int(query.message.message_id)}
                context.user_data[_waiting_scope_key("bank_pending")]=int(query.message.chat_id)
                await query.answer(); await query.edit_message_text(f"💳 <b>درخواست وام بانک مرکزی — سطح {level}</b>\n\nمبلغ: <b>{policy.min_amount:,.0f} تا {policy.max_amount:,.0f}</b>\n\nمبلغ وام موردنظر را ارسال کنید.",parse_mode="HTML",reply_markup=central_bank_loan_input_keyboard()); return

            if sub == "loan_confirm":
                pending=context.user_data.get("bank_loan_quote")
                if not pending: await query.answer("❌ درخواست وام منقضی شده است.",show_alert=True); return
                if int(pending.get("country_id",0)) != int(country.id):
                    context.user_data.pop("bank_loan_quote",None); await query.answer("❌ کشور این درخواست دیگر فعال نیست.",show_alert=True); return
                active_count=len(session.scalars(select(BankLoan).where(BankLoan.country_id==country.id, BankLoan.status=="active")).all())
                level=int(pending.get("level") or max(1,int(country.bank_level or 0)))
                d=bank_level_config(session,level); policy=policy_from_level_config(d)
                if active_count >= policy.max_active_loans: await query.answer("❌ ظرفیت وام فعال تکمیل شده است.",show_alert=True); return
                q=quote_loan(float(pending["amount"]),policy,get_bank_loan_interval_hours(session))
                # Quote is authoritative for this confirmation; do not silently replace it with a new policy.
                quote_fields={"principal":"amount","interest_percent":"interest_percent","interest_amount":"interest_amount","total_due":"total_due","installments":"installments","installment_amount":"installment_amount","term_days":"term_days","installment_interval_days":"installment_interval_days"}
                if any(abs(float(getattr(q,k))-float(pending.get(pk,0))) > 0.01 for k,pk in quote_fields.items()):
                    context.user_data.pop("bank_loan_quote",None); await query.answer("❌ شرایط وام از زمان پیشنهاد تغییر کرده است؛ دوباره درخواست دهید.",show_alert=True); return
                from services.atomic_claims import claim_once
                quote_id=str(pending.get("quote_id") or f"legacy:{country.id}:{pending.get('amount')}:{query.message.message_id}")
                if not claim_once(session, f"bank:loan:create:{quote_id}", str(query.from_user.id)):
                    await query.answer("⚠️ این درخواست وام قبلاً در حال ثبت یا ثبت نهایی شده است.",show_alert=True); return
                now=datetime.utcnow()
                loan=BankLoan(country_id=country.id,principal=float(pending["amount"]),interest=float(pending["interest_amount"]),interest_percent=float(pending["interest_percent"]),total_due=float(pending["total_due"]),paid=0,installments=int(pending["installments"]),installments_paid=0,installment_amount=float(pending["installment_amount"]),installment_interval_days=float(pending["installment_interval_days"]),term_days=float(pending["term_days"]),created_at=now,next_payment_at=now+timedelta(hours=float(pending["installment_interval_days"])*24),status="active")
                country.money=float(country.money or 0)+q.principal; session.add(loan); session.commit(); context.user_data.pop("bank_loan_quote",None); context.user_data.pop("bank_pending",None); context.user_data.pop(_waiting_scope_key("bank_pending"),None)
                await query.answer("✅ وام دریافت شد.",show_alert=True); await query.edit_message_text(f"💳 <b>وام ثبت شد</b>\n\n💰 مبلغ دریافتی: <b>{q.principal:,.0f}</b>\n📈 سود: <b>{q.interest_percent:.2f}%</b> = <b>{q.interest_amount:,.0f}</b>\n💵 کل بازپرداخت: <b>{q.total_due:,.0f}</b>\n🧾 تعداد اقساط: <b>{q.installments}</b>\n💵 مبلغ هر قسط: <b>{q.installment_amount:,.0f}</b>\n⏱️ مدت بازپرداخت: <b>{q.term_days:.1f} روز</b>\n📅 اولین سررسید: <b>{_display_tehran(loan.next_payment_at)}</b>",parse_mode="HTML",reply_markup=central_bank_loan_detail_keyboard(loan.id)); return

            if sub == "loan_pay" and len(parts)>=3:
                loan_id=int(parts[2]); loan=session.get(BankLoan,loan_id)
                if not loan or int(loan.country_id)!=int(country.id) or loan.status!="active":
                    await query.answer("❌ وام فعال پیدا نشد.",show_alert=True); return
                acc=ensure_bank_account(session,country); setattr(country,"_bank_account_for_repayment",acc)
                amount=current_installment_amount(loan,session,datetime.utcnow())
                from services.atomic_claims import claim_once
                installment_key=f"bank:loan:pay:{int(loan.id)}:{int(loan.installments_paid or 0)}"
                if not claim_once(session, installment_key, str(query.from_user.id)):
                    await query.answer("⚠️ این قسط هم‌اکنون توسط درخواست دیگری در حال پرداخت است.",show_alert=True); return
                result=process_due_loan(session,loan,country)
                if result.get("status")=="insufficient":
                    await query.answer(f"❌ پول کافی نیست. مبلغ قسط فعلی: {amount:,.0f} پول",show_alert=True); return
                if result.get("status")!="paid":
                    await query.answer("❌ پرداخت قسط انجام نشد.",show_alert=True); return
                session.commit(); await query.answer(f"✅ مبلغ {float(result.get('amount',0)):,.0f} پول بابت قسط پرداخت شد.",show_alert=True)
                remain=max(0,float(loan.total_due or 0)-float(loan.paid or 0))
                status_names={"active":"فعال","paid":"تسویه‌شده","defaulted":"معوق","locked":"مسدود"}
                status=status_names.get(str(loan.status),str(loan.status))
                detail=(f"💳 <b>وام #{loan.id}</b>\n\n"
                        f"💰 اصل پول: <b>{loan.principal:,.0f}</b>\n"
                        f"📈 سود: <b>{loan.interest_percent:.2f}%</b> = <b>{loan.interest:,.0f}</b>\n"
                        f"💵 کل بازپرداخت: <b>{loan.total_due:,.0f}</b>\n"
                        f"💵 باقی‌مانده: <b>{remain:,.0f}</b>\n"
                        f"🧾 اقساط: <b>{int(loan.installments_paid or 0)}/{int(loan.installments or 0)}</b>\n"
                        f"💵 مبلغ هر قسط: <b>{loan.installment_amount:,.0f}</b>\n"
                        f"📅 سررسید بعدی: <b>{_display_tehran(loan.next_payment_at) if loan.next_payment_at else 'تسویه‌شده'}</b>\n"
                        f"🔘 وضعیت: <b>{status}</b>")
                await query.edit_message_text(detail,parse_mode="HTML",reply_markup=central_bank_loan_detail_keyboard(loan.id) if loan.status=="active" else central_bank_my_loans_keyboard(0,0)); return

            if sub == "withdraw_tax":
                from services.atomic_claims import claim_once
                acc_for_claim=ensure_bank_account(session,country)
                claim_key=f"bank:withdraw_tax:{int(country.id)}:{int(float(acc_for_claim.accrued_tax or 0))}"
                if not claim_once(session, claim_key, str(query.from_user.id)):
                    await query.answer("⚠️ برداشت مالیات هم‌اکنون در حال انجام است.",show_alert=True); return
                amount=bank_withdraw_tax(session,country); session.commit()
                await query.answer(f"💰 {amount:,.0f} پول مالیات دریافت شد.",show_alert=True)
                acc=accrue_bank_tax(session,country)
                total_tax=(float(acc.citizens or 0)/1000.0)*float(acc.tax_per_citizen or 0)
                text=(f"👥 <b>جمعیت و مالیات</b>\n\n"
                      f"👥 تعداد شهروندان: <b>{int(acc.citizens or 0):,}</b>\n"
                      f"🧾 مالیات به ازای هر ۱۰۰۰ شهروند: <b>{float(acc.tax_per_citizen or 0):,.0f}</b>\n"
                      f"💰 مالیات ذخیره‌شده: <b>{float(acc.accrued_tax or 0):,.0f}</b>\n"
                      f"📅 مالیات یک روز کامل: <b>{total_tax:,.0f}</b>")
                await query.edit_message_text(text,parse_mode="HTML",reply_markup=central_bank_population_keyboard()); return

            if sub == "my_loans" or sub == "my_loans_page":
                page=max(0,int(parts[2])) if sub == "my_loans_page" and len(parts)>=3 else 0
                per_page=5
                loans=session.scalars(select(BankLoan).where(BankLoan.country_id==country.id).order_by(BankLoan.created_at.desc(), BankLoan.id.desc())).all()
                if not loans:
                    await query.answer("ℹ️ هنوز هیچ وامی برای شما ثبت نشده است.", show_alert=True)
                    return
                total_pages=max(1,(len(loans)+per_page-1)//per_page); page=min(page,total_pages-1)
                chunk=loans[page*per_page:(page+1)*per_page]
                rows=[]
                for i,loan in enumerate(chunk,page*per_page+1):
                    due=_display_tehran(loan.next_payment_at) if loan.next_payment_at else "تسویه‌شده"
                    rows.append([InlineKeyboardButton(f"💳 وام {int(loan.id)}",callback_data=f"bank:my_loan:{int(loan.id)}")])
                nav=[]
                if page>0: nav.append(InlineKeyboardButton("◀️ قبلی",callback_data=f"bank:my_loans_page:{page-1}"))
                if page<total_pages-1: nav.append(InlineKeyboardButton("بعدی ▶️",callback_data=f"bank:my_loans_page:{page+1}"))
                if nav: rows.append(nav)
                rows.append([InlineKeyboardButton("🔙 برگشت",callback_data="bank:loans")])
                text="💳 <b>وام‌های من</b>\n\n"+"\n".join([f"💳 <b>وام {int(loan.id)}</b>\n📅 سررسید: <b>{_display_tehran(loan.next_payment_at) if loan.next_payment_at else 'تسویه‌شده'}</b>\n💰 اصل پول: <b>{float(loan.principal or 0):,.0f}</b>" for loan in chunk])
                text += f"\n\nصفحه {page+1} از {total_pages}"
                await query.answer(); await query.edit_message_text(text,parse_mode="HTML",reply_markup=InlineKeyboardMarkup(rows)); return
            if sub == "my_loan" and len(parts)>=3:
                loan=session.get(BankLoan,int(parts[2]))
                if not loan or int(loan.country_id)!=int(country.id):
                    await query.answer("❌ وام پیدا نشد.",show_alert=True); return
                remain=max(0,float(loan.total_due or 0)-float(loan.paid or 0))
                status_names={"active":"فعال","paid":"تسویه‌شده","defaulted":"معوق","locked":"مسدود"}
                status=status_names.get(str(loan.status),str(loan.status))
                detail=(f"💳 <b>وام #{loan.id}</b>\n\n"
                        f"💰 اصل پول: <b>{loan.principal:,.0f}</b>\n"
                        f"📈 سود: <b>{loan.interest_percent:.2f}%</b> = <b>{loan.interest:,.0f}</b>\n"
                        f"💵 کل بازپرداخت: <b>{loan.total_due:,.0f}</b>\n"
                        f"💵 باقی‌مانده: <b>{remain:,.0f}</b>\n"
                        f"🧾 اقساط: <b>{int(loan.installments_paid or 0)}/{int(loan.installments or 0)}</b>\n"
                        f"💵 مبلغ هر قسط: <b>{loan.installment_amount:,.0f}</b>\n"
                        f"📅 سررسید بعدی: <b>{_display_tehran(loan.next_payment_at) if loan.next_payment_at else 'تسویه‌شده'}</b>\n"
                        f"🔘 وضعیت: <b>{status}</b>")
                await query.answer(); await query.edit_message_text(detail,parse_mode="HTML",reply_markup=central_bank_loan_detail_keyboard(loan.id) if loan.status=="active" else central_bank_my_loans_keyboard(0,0)); return
            if sub == "investments":
                await query.answer(); await query.edit_message_text("📈 <b>سرمایه‌گذاری بانک مرکزی</b>\n\nطرح فعال را انتخاب کنید یا سوابق سرمایه‌گذاری خود را ببینید.",parse_mode="HTML",reply_markup=central_bank_investments_keyboard()); return
            if sub == "investment_plans":
                level=max(1,int(country.bank_level or 1)); level_cfg=cfg.get("levels",{}).get(str(level),{}) or {}; plans=[p for p in (level_cfg.get("investments",[]) or []) if bool(p.get("active",True))]
                if not plans:
                    await query.answer("⚠️ در حال حاضر طرح فعالی وجود ندارد.",show_alert=True); return
                rows=[]
                for i,p in enumerate(level_cfg.get("investments",[]) or []):
                    if bool(p.get("active",True)):
                        rows.append([InlineKeyboardButton(str(p.get("name","سرمایه‌گذاری")),callback_data=f"bank:investment_plan:{i}")])
                rows.append([InlineKeyboardButton("🔙 برگشت",callback_data="bank:investments")])
                await query.answer(); await query.edit_message_text("📋 <b>طرح‌های سرمایه‌گذاری فعال</b>\n\nطرح موردنظر را انتخاب کنید:",parse_mode="HTML",reply_markup=InlineKeyboardMarkup(rows)); return
            if sub == "investment_plan" and len(parts)>=3:
                try: idx=int(parts[2]); level_cfg=cfg.get("levels",{}).get(str(max(1,int(country.bank_level or 1))),{}) or {}; plan=(level_cfg.get("investments",[]) or [])[idx]
                except (ValueError,IndexError): await query.answer("❌ طرح پیدا نشد.",show_alert=True); return
                if not bool(plan.get("active",True)): await query.answer("❌ این طرح فعال نیست.",show_alert=True); return
                await query.answer(); await query.edit_message_text(_investment_plan_text(plan),parse_mode="HTML",reply_markup=central_bank_investment_plan_keyboard(idx)); return
            if sub == "investment_amount" and len(parts)>=3:
                try: idx=int(parts[2]); level_cfg=cfg.get("levels",{}).get(str(max(1,int(country.bank_level or 1))),{}) or {}; plan=(level_cfg.get("investments",[]) or [])[idx]
                except (ValueError,IndexError): await query.answer("❌ طرح پیدا نشد.",show_alert=True); return
                if not bool(plan.get("active",True)): await query.answer("❌ این طرح فعال نیست.",show_alert=True); return
                context.user_data["bank_pending"]={"action":"investment_amount","country_id":country.id,"plan_index":idx,"level":max(1,int(country.bank_level or 1)),"prompt_chat_id":int(query.message.chat_id),"prompt_message_id":int(query.message.message_id)}
                context.user_data[_waiting_scope_key("bank_pending")]=int(query.message.chat_id)
                mn=float(plan.get("min_amount",0) or 0); mx=float(plan.get("max_amount",0) or 0)
                limit=f"{mn:,.0f} تا {mx:,.0f}" if mx>0 else f"حداقل {mn:,.0f}"
                await query.answer(); await query.edit_message_text(_investment_plan_text(plan)+f"\n\n💰 مبلغ سرمایه‌گذاری را ارسال کنید.\nمحدوده: <b>{limit}</b>",parse_mode="HTML",reply_markup=central_bank_investment_input_keyboard(idx)); return
            if sub == "investment_confirm" and len(parts)>=3:
                try: idx=int(parts[2]); level_cfg=cfg.get("levels",{}).get(str(max(1,int(country.bank_level or 1))),{}) or {}; plan=(level_cfg.get("investments",[]) or [])[idx]
                except (ValueError,IndexError): await query.answer("❌ طرح پیدا نشد.",show_alert=True); return
                pending=context.user_data.get("bank_investment_quote") or {}
                if int(pending.get("country_id",0))!=int(country.id) or int(pending.get("plan_index",-1))!=idx:
                    await query.answer("❌ پیشنهاد سرمایه‌گذاری منقضی شده است.",show_alert=True); return
                amount=float(pending.get("amount",0) or 0)
                snapshot_ok=(str(plan.get("name","سرمایه‌گذاری"))==str(pending.get("name")) and str(plan.get("return_type","money"))==str(pending.get("return_type","money")) and abs(float(plan.get("duration_hours",0) or 0)-float(pending.get("duration_hours",0) or 0))<0.0001)
                for _k in ("profit_min_percent","profit_max_percent","loss_min_percent","loss_max_percent","profit_min_value","profit_max_value","loss_min_value","loss_max_value"):
                    if abs(float(plan.get(_k,0) or 0)-float(pending.get(_k,0) or 0))>0.0001: snapshot_ok=False
                if not snapshot_ok or amount<=0 or (float(plan.get("max_amount",0) or 0)>0 and amount>float(plan.get("max_amount",0) or 0)) or amount<float(plan.get("min_amount",0) or 0):
                    context.user_data.pop("bank_investment_quote",None); await query.answer("❌ مبلغ سرمایه‌گذاری دیگر معتبر نیست؛ دوباره درخواست دهید.",show_alert=True); return
                max_per_user=max(1,int(plan.get("max_per_user",1) or 1))
                existing_count=session.scalar(select(func.count(BankInvestment.id)).where(BankInvestment.country_id==country.id, BankInvestment.plan_name==str(plan.get("name","سرمایه‌گذاری")), BankInvestment.status=="active")) or 0
                if int(existing_count)>=max_per_user:
                    await query.answer(f"❌ سقف این طرح برای شما {max_per_user} مورد است.",show_alert=True); return
                if not bool(plan.get("allow_multiple_active",False)):
                    active_count=session.scalar(select(func.count(BankInvestment.id)).where(BankInvestment.country_id==country.id, BankInvestment.plan_name==str(plan.get("name","سرمایه‌گذاری")), BankInvestment.status=="active")) or 0
                    if int(active_count)>0:
                        await query.answer("❌ این طرح اجازه سرمایه‌گذاری همزمان را نمی‌دهد.",show_alert=True); return
                if not getattr(country,"infinite_money",False) and float(country.money or 0)<amount:
                    await query.answer("❌ پول کافی نیست.",show_alert=True); return
                from services.atomic_claims import claim_once
                quote_id=str(pending.get("quote_id") or f"legacy:{country.id}:{idx}:{amount:g}:{query.message.message_id}")
                if not claim_once(session, f"bank:investment:create:{quote_id}", str(query.from_user.id)):
                    await query.answer("⚠️ این درخواست سرمایه‌گذاری قبلاً در حال ثبت یا ثبت نهایی شده است.",show_alert=True); return
                if not getattr(country,"infinite_money",False): country.money-=amount
                duration=max(0.0,float(plan.get("duration_hours",0) or 0)); now=datetime.utcnow()
                return_type=str(plan.get("return_type","money"))
                if return_type == "money":
                    pmin=float(plan.get("profit_min_percent",plan.get("profit_percent",0)) or 0); pmax=float(plan.get("profit_max_percent",plan.get("profit_percent",0)) or 0)
                    lmin=float(plan.get("loss_min_percent",plan.get("loss_percent",0)) or 0); lmax=float(plan.get("loss_max_percent",plan.get("loss_percent",0)) or 0)
                else:
                    pmin=float(plan.get("profit_min_value",0) or 0); pmax=float(plan.get("profit_max_value",0) or 0)
                    lmin=float(plan.get("loss_min_value",0) or 0); lmax=float(plan.get("loss_max_value",0) or 0)
                inv=BankInvestment(country_id=country.id,plan_name=str(plan.get("name","سرمایه‌گذاری")),plan_type=str(plan.get("plan_type",plan.get("type","medium"))),principal=amount,risk=float(pending.get("risk",0) or 0),profit_percent=pmax,loss_percent=lmax,profit_min_percent=pmin,profit_max_percent=pmax,loss_min_percent=lmin,loss_max_percent=lmax,return_type=return_type,started_at=now,ends_at=now+timedelta(hours=duration),status="active",result=None)
                session.add(inv); session.commit(); context.user_data.pop("bank_investment_quote",None); context.user_data.pop("bank_pending",None); context.user_data.pop(_waiting_scope_key("bank_pending"),None)
                await query.answer("📈 سرمایه‌گذاری ثبت شد.",show_alert=True); await query.edit_message_text(f"📈 <b>سرمایه‌گذاری ثبت شد</b>\n\nطرح: <b>{escape(inv.plan_name)}</b>\n💰 مبلغ: <b>{amount:,.0f}</b>\n⏱️ پایان: <b>{_display_tehran(inv.ends_at)}</b>\n🎚️ ریسک: <b>{float(inv.risk or 0):g}%</b>",parse_mode="HTML",reply_markup=central_bank_investment_plan_keyboard(idx)); return
            if sub == "my_investments":
                investments=session.scalars(select(BankInvestment).where(BankInvestment.country_id==country.id).order_by(BankInvestment.id.desc())).all()
                if not investments:
                    await query.answer("ℹ️ هنوز هیچ سرمایه‌گذاری ثبت نشده است.",show_alert=True)
                    return
                status_names={"active":"فعال","won":"سودده","lost":"زیان‌ده","settled":"تسویه‌شده"}
                lines=["💼 <b>سرمایه‌گذاری‌های من</b>","","برای مشاهده جزئیات، یکی از سرمایه‌گذاری‌ها را انتخاب کنید."]
                await query.answer(); await query.edit_message_text("\n".join(lines),parse_mode="HTML",reply_markup=central_bank_my_investments_keyboard(investments)); return

            if sub == "my_investment" and len(parts)>=3:
                try: inv_id=int(parts[2])
                except ValueError:
                    await query.answer("❌ سرمایه‌گذاری نامعتبر است.",show_alert=True); return
                inv=session.get(BankInvestment,inv_id)
                if inv is None or int(inv.country_id)!=int(country.id):
                    await query.answer("❌ سرمایه‌گذاری پیدا نشد.",show_alert=True); return
                status_names={"active":"فعال","won":"سودده","lost":"زیان‌ده","settled":"تسویه‌شده"}
                status=status_names.get(str(inv.status),"نامشخص")
                result=float(inv.result or 0)
                text=(f"💼 <b>{escape(str(inv.plan_name))}</b>\n\n"
                      f"💰 سرمایه اولیه: <b>{float(inv.principal or 0):,.0f}</b>\n"
                      f"📊 وضعیت: <b>{status}</b>\n"
                      f"📈 سود/زیان: <b>{result:+,.0f}</b>\n"
                      f"🕐 شروع: <b>{_display_tehran(inv.started_at)}</b>\n"
                      f"⏱️ پایان: <b>{_display_tehran(inv.ends_at)}</b>")
                await query.answer(); await query.edit_message_text(text,parse_mode="HTML",reply_markup=central_bank_my_investment_detail_keyboard()); return
            if sub == "back":
                await query.answer()
                try: await query.edit_message_reply_markup(reply_markup=None)
                except Exception: pass
                return

            if sub == "set_tax":
                acc=ensure_bank_account(session,country); lv=bank_level_config(session,max(1,int(country.bank_level or 1))); mn=float(lv.get("tax_min",0) or 0); mx=float(lv.get("tax_max",0) or 0)
                context.user_data["bank_pending"]={"action":"tax","country_id":country.id,"min":mn,"max":mx}
                context.user_data[_waiting_scope_key("bank_pending")]=int(query.message.chat_id)
                await query.answer(); await query.edit_message_text(f"🧾 <b>تنظیم مالیات</b>\n\nمقدار مالیات به ازای هر ۱۰۰۰ شهروند را بین <b>{mn:g}</b> و <b>{mx:g}</b> وارد کنید.\nمقدار فعلی: <b>{float(acc.tax_per_citizen or 0):g}</b>",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="bank:population")]])); return

            if sub == "population":
                acc=ensure_bank_account(session,country)
                total_tax=(float(acc.citizens or 0)/1000.0)*float(acc.tax_per_citizen or 0)
                text=(f"👥 <b>جمعیت و مالیات</b>\n\n"
                      f"👥 جمعیت کشور: <b>{int(acc.citizens or 0):,}</b> نفر\n"
                      f"🧾 مالیات به ازای هر ۱۰۰۰ شهروند: <b>{float(acc.tax_per_citizen or 0):,.0f}</b> پول\n"
                      f"💰 مالیات ذخیره‌شده: <b>{float(acc.accrued_tax or 0):,.0f}</b> پول\n"
                      f"📅 مالیات یک روز کامل: <b>{total_tax:,.0f}</b> پول")
                await query.answer()
                await query.edit_message_text(text, parse_mode="HTML", reply_markup=central_bank_population_keyboard())
                return

        # مسیرهای بدون namespace (مثل metal_mine_collect و hq_tech_missiles)
        # نباید وابسته به action تعریف‌شده در شاخه‌های دیگر باشند.
        parts = data.split(":")
        action = parts[1] if len(parts) > 1 else ""

        if action == 'noop':
            await query.answer()
            return

        if action == 'challenges':
            await query.answer()
            await query.edit_message_text(
                "🧩 <b>چالش‌ها</b>\n\nیکی از بخش‌های چالش را انتخاب کنید:",
                parse_mode="HTML",
                reply_markup=owner_challenges_keyboard(),
            )
            return

        # هر ناوبری/برگشت در تنظیمات جعبه‌ها باید waiting قبلی را ببندد.
        # در غیر این صورت بعد از زدن «برگشت»، عدد بعدی هنوز توسط golden_pending مصرف می‌شود.
        if action in {'golden','golden_general','golden_box_settings','golden_box','golden_days','golden_schedule','golden_day','golden_expiry','golden_challenge','golden_stats','golden_levels','golden_weights','golden_costs'}:
            context.user_data.pop('golden_pending', None)
            context.user_data.pop(_waiting_scope_key('golden_stage_scope'), None)
            context.user_data.pop('golden_stage_scope', None)

        if action == 'golden':
            from keyboards.admin import golden_owner_keyboard
            cfg=golden_config(session); await query.answer(); await query.edit_message_text("🎁 <b>مدیریت جعبه‌ها</b>\n\nتنظیمات هر جعبه و تنظیمات عمومی را جداگانه مدیریت کنید.",parse_mode="HTML",reply_markup=golden_owner_keyboard(cfg)); return
        if action == 'golden_general':
            from keyboards.admin import golden_general_keyboard
            cfg=golden_config(session); await query.answer(); await query.edit_message_text(_golden_general_text(cfg),parse_mode="HTML",reply_markup=golden_general_keyboard(cfg)); return
        if action == 'golden_box_settings':
            from keyboards.admin import golden_box_settings_keyboard
            await query.answer(); await query.edit_message_text("📦 <b>تنظیمات جعبه‌ها</b>\n\nجعبه موردنظر را انتخاب کنید:",parse_mode="HTML",reply_markup=golden_box_settings_keyboard()); return
        if action == 'golden_box' and len(parts)>=3:
            from keyboards.admin import golden_box_detail_keyboard
            k=parts[2]; cfg=golden_config(session)
            if k not in GOLDEN_BOXES: await query.answer("❌ جعبه نامعتبر است.",show_alert=True); return
            icon,name=GOLDEN_BOXES[k]; lv=cfg['levels'][k]
            await query.answer(); await query.edit_message_text(_golden_box_text(cfg, k), parse_mode='HTML', reply_markup=golden_box_detail_keyboard(k)); return
        if action == 'golden_box_levels' and len(parts)>=3:
            from keyboards.admin import golden_box_levels_keyboard
            k=parts[2]; cfg=golden_config(session)
            if k not in GOLDEN_BOXES: await query.answer("❌ جعبه نامعتبر است.",show_alert=True); return
            mx=int(cfg['levels'][k].get('max_level',100) or 1)
            await query.answer(); await query.edit_message_text(
                f"📊 <b>سطوح جعبه {GOLDEN_BOXES[k][1]}</b>\n\nسطح موردنظر را انتخاب کنید:",
                parse_mode='HTML', reply_markup=golden_box_levels_keyboard(k,mx)
            ); return
        if action == 'golden_box_level' and len(parts)>=4:
            from keyboards.admin import golden_box_level_edit_keyboard
            k=parts[2]
            try: lv=int(parts[3])
            except Exception: await query.answer("❌ سطح نامعتبر است.",show_alert=True); return
            cfg=golden_config(session)
            if k not in GOLDEN_BOXES or lv<1 or lv>int(cfg['levels'][k].get('max_level',100)):
                await query.answer("❌ سطح نامعتبر است.",show_alert=True); return
            data=cfg['levels'][k]
            reward_min=float(data.get('reward_min',{}).get(str(lv),0) or 0)
            reward_max=float(data.get('reward_max',{}).get(str(lv),reward_min) or reward_min)
            cost=float(data.get('costs',{}).get(str(lv),0) or 0)
            tm=int(data.get('upgrade_times',{}).get(str(lv),0) or 0)
            hq_req=golden_hq_required_for(cfg,k,lv)
            text=(f"📊 <b>تنظیمات سطح {lv} جعبه {GOLDEN_BOXES[k][1]}</b>\n\n"
                  f"🎁 بازه جایزه: <b>{reward_min:,.0f}</b> تا <b>{reward_max:,.0f}</b>\n")
            if lv >= 2:
                text += f"💰 هزینه ارتقا: <b>{cost:,.0f}</b>\n⏱ زمان ارتقا: <b>{tm}</b> ثانیه\n🏛️ مرکز فرماندهی موردنیاز: <b>سطح {hq_req}</b>"
            await query.answer(); await query.edit_message_text(text,parse_mode='HTML',reply_markup=golden_box_level_edit_keyboard(k,lv)); return
        if action == 'golden_box_level_edit' and len(parts)>=5:
            k=parts[2]
            try: lv=int(parts[3])
            except Exception: await query.answer("❌ سطح نامعتبر است.",show_alert=True); return
            field=parts[4]
            allowed_fields = {'reward_min','reward_max'} if lv == 1 else {'reward_min','reward_max','cost','time','hq'}
            if k not in GOLDEN_BOXES or field not in allowed_fields:
                await query.answer("❌ درخواست نامعتبر است.",show_alert=True); return
            cfg=golden_config(session); mx=int(cfg['levels'][k].get('max_level',100))
            if lv<1 or lv>mx: await query.answer("❌ سطح نامعتبر است.",show_alert=True); return
            labels={'reward_min':'حداقل جایزه','reward_max':'حداکثر جایزه','cost':'هزینه ارتقا','time':'زمان ارتقا (ثانیه)','hq':'سطح مرکز فرماندهی موردنیاز'}
            types={'reward_min':'level_reward_min','reward_max':'level_reward_max','cost':'level_cost','time':'level_time','hq':'level_hq'}
            context.user_data['golden_pending']={'type':types[field],'box':k,'level':lv,'back':f'owner:golden_box_level:{k}:{lv}','prompt_chat_id':int(query.message.chat_id),'prompt_message_id':int(query.message.message_id)}
            context.user_data[_waiting_scope_key('golden_stage_scope')]=int(query.message.chat_id)
            await query.answer(); await query.edit_message_text(
                f"✏️ <b>{labels[field]}</b>\n\nمقدار جدید برای سطح {lv} جعبه {GOLDEN_BOXES[k][1]} را ارسال کنید.",
                parse_mode='HTML',reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 برگشت',callback_data=f'owner:golden_box_level:{k}:{lv}')]])
            ); return
        if action == 'golden_toggle':
            cfg=golden_config(session); cfg['enabled']=not bool(cfg.get('enabled')); golden_save_config(session,cfg)
            from keyboards.admin import golden_general_keyboard
            await query.answer("🟢 روشن شد." if cfg['enabled'] else "🔴 خاموش شد.",show_alert=True); await query.edit_message_text(_golden_general_text(cfg),parse_mode="HTML",reply_markup=golden_general_keyboard(cfg)); return
        if action == 'golden_weights':
            from keyboards.admin import golden_box_settings_keyboard
            await query.answer(); await query.edit_message_text("📦 برای تنظیم احتمال، ابتدا جعبه موردنظر را انتخاب کنید.",reply_markup=golden_box_settings_keyboard()); return
        if action == 'golden_weight' and len(parts)>=3:
            k=parts[2]; context.user_data['golden_pending']={'type':'weight','box':k,'back':f'owner:golden_box:{k}','prompt_chat_id':int(query.message.chat_id),'prompt_message_id':int(query.message.message_id)}; context.user_data[_waiting_scope_key('golden_stage_scope')]=int(query.message.chat_id)
            await query.answer(); await query.edit_message_text(f"🎲 احتمال {GOLDEN_BOXES[k][1]} را بین ۰ تا ۱۰۰ ارسال کنید.",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 برگشت',callback_data=f'owner:golden_box:{k}')]])); return
        if action == 'golden_days':
            cfg=golden_config(session); from keyboards.admin import golden_days_keyboard
            days=cfg.get('active_days',list(range(7))) or []
            names=['شنبه','یکشنبه','دوشنبه','سه‌شنبه','چهارشنبه','پنجشنبه','جمعه']
            selected='، '.join(names[int(i)] for i in days if 0 <= int(i) < 7) or 'هیچ روزی'
            await query.answer(); await query.edit_message_text(
                f"📅 <b>روزهای ارسال</b>\n\nروزهای انتخاب‌شده: <b>{selected}</b>\n\nروزهایی را که جعبه‌ها اجازه ارسال دارند انتخاب کنید.",
                parse_mode='HTML', reply_markup=golden_days_keyboard(cfg)
            ); return
        if action == 'golden_schedule':
            cfg=golden_config(session); from keyboards.admin import golden_days_keyboard
            days=cfg.get('active_days',list(range(7))) or []
            names=['شنبه','یکشنبه','دوشنبه','سه‌شنبه','چهارشنبه','پنجشنبه','جمعه']
            selected='، '.join(names[int(i)] for i in days if 0 <= int(i) < 7) or 'هیچ روزی'
            await query.answer(); await query.edit_message_text(
                f"📅 <b>روزهای ارسال</b>\n\nروزهای انتخاب‌شده: <b>{selected}</b>\n\nروزهایی را که جعبه‌ها اجازه ارسال دارند انتخاب کنید.",
                parse_mode='HTML', reply_markup=golden_days_keyboard(cfg)
            ); return
        if action == 'golden_day' and len(parts)>=3:
            cfg=golden_config(session); d=int(parts[2])
            if d not in range(7):
                await query.answer("❌ روز نامعتبر است.", show_alert=True); return
            days=set(cfg.get('active_days',[])); days.remove(d) if d in days else days.add(d); cfg['active_days']=sorted(days); golden_save_config(session,cfg)
            from keyboards.admin import golden_days_keyboard
            await query.answer("✅ روزهای ارسال به‌روزرسانی شد.", show_alert=True)
            await query.edit_message_text("📅 <b>روزهای ارسال</b>\n\nروزهایی را که جعبه‌ها اجازه ارسال دارند انتخاب کنید.",parse_mode='HTML',reply_markup=golden_days_keyboard(cfg)); return
        if action == 'golden_edit' and len(parts)>=3:
            field=parts[2]
            back='owner:golden_general' if field in {'daily_count','start','end','opened_delete_minutes','unanswered_delete_minutes'} else 'owner:golden_challenge'
            labels={'daily_count':'تعداد روزانه','start':'ساعت شروع','end':'ساعت پایان','opened_delete_minutes':'زمان حذف پس از باز شدن (دقیقه)','unanswered_delete_minutes':'زمان حذف بدون برنده (دقیقه)','challenge_digits':'تعداد رقم رمز','options_count':'تعداد گزینه‌ها'}
            label=labels.get(field,'مقدار')
            context.user_data['golden_pending']={'type':field,'back':back,'prompt_chat_id':int(query.message.chat_id),'prompt_message_id':int(query.message.message_id)}; context.user_data[_waiting_scope_key('golden_stage_scope')]=int(query.message.chat_id)
            hint = ('مثلاً 12، 18 یا 12:30 وارد کنید؛ صفر اول و دو نقطه اجباری نیست.' if field in {'start','end'} else 'مقدار جدید را به صورت عددی ارسال کنید.')
            await query.answer(); await query.edit_message_text(f"✏️ <b>{label}</b>\n\n{hint}",parse_mode='HTML',reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 برگشت',callback_data=back)]])); return
        if action == 'golden_box_edit' and len(parts)>=4:
            k,field=parts[2],parts[3]
            if k not in GOLDEN_BOXES: await query.answer("❌ جعبه نامعتبر است.",show_alert=True); return
            labels={'weight':'احتمال','max':'حداکثر سطح','upgrade_time':'زمان ارتقا (ثانیه)','instant_uranium':'اورانیوم تکمیل فوری'}
            typ={'weight':'weight','max':'max','upgrade_time':'upgrade_time','instant_uranium':'instant_uranium'}[field]
            context.user_data['golden_pending']={'type':typ,'box':k,'back':f'owner:golden_box:{k}','prompt_chat_id':int(query.message.chat_id),'prompt_message_id':int(query.message.message_id)}; context.user_data[_waiting_scope_key('golden_stage_scope')]=int(query.message.chat_id)
            await query.answer(); await query.edit_message_text(f"✏️ <b>{labels[field]}</b>\n\nمقدار جدید برای جعبه {GOLDEN_BOXES[k][1]} را ارسال کنید.",parse_mode='HTML',reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 برگشت',callback_data=f'owner:golden_box:{k}')]])); return
        if action == 'golden_box_reward' and len(parts)>=3:
            k=parts[2]
            if k not in GOLDEN_BOXES: await query.answer("❌ جعبه نامعتبر است.",show_alert=True); return
            context.user_data['golden_pending']={'type':'reward_level','box':k,'back':f'owner:golden_box:{k}','prompt_chat_id':int(query.message.chat_id),'prompt_message_id':int(query.message.message_id)}; context.user_data[_waiting_scope_key('golden_stage_scope')]=int(query.message.chat_id)
            await query.answer(); await query.edit_message_text(f"🎁 سطح جعبه {GOLDEN_BOXES[k][1]} را بین ۱ تا ۱۰۰ ارسال کنید.",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 برگشت',callback_data=f'owner:golden_box:{k}')]])); return
        if action == 'golden_box_cost' and len(parts)>=3:
            k=parts[2]
            if k not in GOLDEN_BOXES: await query.answer("❌ جعبه نامعتبر است.",show_alert=True); return
            context.user_data['golden_pending']={'type':'cost_level','box':k,'back':f'owner:golden_box:{k}','prompt_chat_id':int(query.message.chat_id),'prompt_message_id':int(query.message.message_id)}; context.user_data[_waiting_scope_key('golden_stage_scope')]=int(query.message.chat_id)
            await query.answer(); await query.edit_message_text(f"💰 سطح موردنظر برای هزینه ارتقای جعبه {GOLDEN_BOXES[k][1]} را ارسال کنید.",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 برگشت',callback_data=f'owner:golden_box:{k}')]])); return
        if action == 'golden_levels':
            from keyboards.admin import golden_box_settings_keyboard
            await query.answer(); await query.edit_message_text('📦 برای تنظیم سطح، ابتدا جعبه موردنظر را انتخاب کنید.',reply_markup=golden_box_settings_keyboard()); return
        if action == 'golden_max' and len(parts)>=3:
            k=parts[2]; context.user_data['golden_pending']={'type':'max','box':k,'back':f'owner:golden_box:{k}','prompt_chat_id':int(query.message.chat_id),'prompt_message_id':int(query.message.message_id)}; context.user_data[_waiting_scope_key('golden_stage_scope')]=int(query.message.chat_id); await query.answer(); await query.edit_message_text(f"⭐ حداکثر سطح جعبه {GOLDEN_BOXES[k][1]} را بین ۱ تا ۱۰۰ ارسال کنید.",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 برگشت',callback_data=f'owner:golden_box:{k}')]])); return
        if action == 'golden_reward':
            await query.answer("📦 ابتدا جعبه را انتخاب کنید.",show_alert=True); return
        if action == 'golden_cost' and len(parts)>=3:
            k=parts[2]; context.user_data['golden_pending']={'type':'cost_level','box':k,'back':f'owner:golden_box:{k}','prompt_chat_id':int(query.message.chat_id),'prompt_message_id':int(query.message.message_id)}; context.user_data[_waiting_scope_key('golden_stage_scope')]=int(query.message.chat_id); await query.answer(); await query.edit_message_text(f'💰 سطح موردنظر برای هزینه ارتقای جعبه {GOLDEN_BOXES[k][1]} را ارسال کنید.',reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 برگشت',callback_data=f'owner:golden_box:{k}')]])); return
        if action == 'golden_costs':
            from keyboards.admin import golden_box_settings_keyboard
            await query.answer(); await query.edit_message_text('📦 برای تنظیم هزینه ارتقا، ابتدا جعبه موردنظر را انتخاب کنید.',reply_markup=golden_box_settings_keyboard()); return
        if action == 'golden_expiry':
            cfg=golden_config(session); from keyboards.admin import golden_expiry_keyboard
            await query.answer(); await query.edit_message_text(_golden_expiry_text(cfg),parse_mode='HTML',reply_markup=golden_expiry_keyboard(cfg)); return
        if action == 'golden_challenge':
            cfg=golden_config(session); from keyboards.admin import golden_challenge_keyboard
            await query.answer(); await query.edit_message_text(_golden_challenge_text(cfg),parse_mode='HTML',reply_markup=golden_challenge_keyboard(cfg)); return
        if action == 'golden_stats':
            from services.golden_boxes import load_state as _gs, GROUP_STATE_PREFIX as _GSP
            countries=session.scalars(select(Country)).all()
            reset_row=session.scalar(select(BotSetting).where(BotSetting.key=='golden_stats_reset_at'))
            reset_at=str(reset_row.value or '').strip() if reset_row else ''
            try:
                reset_dt=datetime.fromisoformat(reset_at) if reset_at else None
            except Exception:
                reset_dt=None
            total=won=expired=open_count=wrong_attempts=0
            reward_total=0.0
            by={k:{'total':0,'won':0,'expired':0,'open':0,'wrong':0,'reward':0.0} for k in GOLDEN_BOXES}
            group_rows=session.scalars(select(BotSetting).where(BotSetting.key.like(_GSP + '%'))).all()
            grouped_chats=set()
            def _in_scope(rec):
                if not reset_dt:
                    return True
                stamp=str(rec.get('created_at') or '') if isinstance(rec,dict) else ''
                try:
                    return datetime.fromisoformat(stamp) >= reset_dt
                except Exception:
                    return False
            def _consume(state):
                nonlocal total, won, expired, open_count, wrong_attempts, reward_total
                for h in state.get('history',[]) or []:
                    if not isinstance(h,dict) or not _in_scope(h):
                        continue
                    box=h.get('box')
                    if box not in by: continue
                    status=str(h.get('status') or '')
                    by[box]['total'] += 1; total += 1
                    wrong=len(h.get('wrong') or [])
                    by[box]['wrong'] += wrong; wrong_attempts += wrong
                    reward=float(h.get('reward',0) or 0)
                    if status == 'won':
                        won += 1; by[box]['won'] += 1; by[box]['reward'] += reward; reward_total += reward
                    elif status == 'expired':
                        expired += 1; by[box]['expired'] += 1
                for h in (state.get('actives') or {}).values():
                    if not isinstance(h,dict) or not _in_scope(h):
                        continue
                    box=h.get('box')
                    if box not in by or h.get('status') != 'open': continue
                    by[box]['total'] += 1; by[box]['open'] += 1; total += 1; open_count += 1
                    wrong=len(h.get('wrong') or [])
                    by[box]['wrong'] += wrong; wrong_attempts += wrong
            for row in group_rows:
                try: chat_id=int(str(row.key).rsplit(':',1)[1]); grouped_chats.add(chat_id)
                except Exception: continue
                try: state=json.loads(row.value or '{}')
                except Exception: state={}
                _consume(state)
            seen_legacy=set()
            for cc in countries:
                chat_id=int(cc.chat_id)
                if chat_id in grouped_chats or chat_id in seen_legacy: continue
                seen_legacy.add(chat_id)
                _consume(_gs(session,cc.id))
            lines=[
                '📊 <b>آمار واقعی جعبه‌ها</b>',
                '',
                f'🎁 کل جعبه‌ها: <b>{total:,}</b>',
                f'🏆 برنده‌شده: <b>{won:,}</b>',
                f'⌛ منقضی‌شده: <b>{expired:,}</b>',
                f'⏳ فعال: <b>{open_count:,}</b>',
                f'❌ پاسخ‌های اشتباه: <b>{wrong_attempts:,}</b>',
                f'💰 مجموع پاداش پرداخت‌شده: <b>{reward_total:,.0f}</b>',
                '',
                '📦 <b>تفکیک نوع جعبه</b>',
            ]
            labels={'money':'💰 پول','fuel':'⛽ سوخت','metal':'🔩 فلز','uranium':'☢️ اورانیوم'}
            for key in GOLDEN_BOXES:
                st=by[key]
                lines.append(f"{labels[key]}: <b>{st['total']:,}</b> | 🏆 {st['won']:,} | ⌛ {st['expired']:,} | ⏳ {st['open']:,} | ❌ {st['wrong']:,}")
            if reset_dt:
                lines.extend(['', f'♻️ آمار از: <b>{escape(reset_at)}</b>'])
            await query.answer()
            await query.edit_message_text('\n'.join(lines),parse_mode='HTML',reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('♻️ ریست آمار',callback_data='owner:golden_stats_reset')],
                [InlineKeyboardButton('🔙 برگشت',callback_data='owner:golden')]
            ]))
            return
        if action == 'golden_stats_reset':
            await query.answer()
            await query.edit_message_text(
                '⚠️ <b>ریست آمار جعبه‌ها</b>\n\nبا تأیید، آمار از همین لحظه صفر می‌شود. سابقهٔ داخلی جعبه‌ها حذف نمی‌شود و فقط نقطهٔ شروع آمار تغییر می‌کند.\n\nآیا مطمئن هستید؟',
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton('✅ تأیید ریست',callback_data='owner:golden_stats_reset_confirm')],
                    [InlineKeyboardButton('🔙 برگشت',callback_data='owner:golden_stats')],
                ])
            )
            return
        if action == 'golden_stats_reset_confirm':
            now=datetime.utcnow().isoformat()
            row=session.scalar(select(BotSetting).where(BotSetting.key=='golden_stats_reset_at'))
            if row is None:
                session.add(BotSetting(key='golden_stats_reset_at',value=now))
            else:
                row.value=now
            session.commit()
            await query.answer('✅ آمار جعبه‌ها ریست شد.',show_alert=True)
            # Re-render the now-empty stats panel immediately.
            lines=['📊 <b>آمار واقعی جعبه‌ها</b>','','🎁 کل جعبه‌ها: <b>0</b>','🏆 برنده‌شده: <b>0</b>','⌛ منقضی‌شده: <b>0</b>','⏳ فعال: <b>0</b>','❌ پاسخ‌های اشتباه: <b>0</b>','💰 مجموع پاداش پرداخت‌شده: <b>0</b>','','📦 <b>تفکیک نوع جعبه</b>']
            labels={'money':'💰 پول','fuel':'⛽ سوخت','metal':'🔩 فلز','uranium':'☢️ اورانیوم'}
            for key in GOLDEN_BOXES:
                lines.append(f"{labels[key]}: <b>0</b> | 🏆 0 | ⌛ 0 | ⏳ 0 | ❌ 0")
            lines.extend(['',f'♻️ آمار از: <b>{escape(now)}</b>'])
            await query.edit_message_text('\n'.join(lines),parse_mode='HTML',reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('♻️ ریست آمار',callback_data='owner:golden_stats_reset')],
                [InlineKeyboardButton('🔙 برگشت',callback_data='owner:golden')]
            ]))
            return
        if action == "enigma":
            if not owner_user: await query.answer("⛔ فقط Owner.",show_alert=True); return
            cfg=ensure_settings(session); await query.answer(); await query.edit_message_text("🔐 <b>مدیریت انیگما</b>",parse_mode='HTML',reply_markup=InlineKeyboardMarkup([*owner_main_keyboard().inline_keyboard, [InlineKeyboardButton("🔙 برگشت", callback_data="owner:challenges")]])); return
        if action == "enigma_settings":
            cfg=ensure_settings(session)
            unlimited=bool(cfg.get('unlimited_attempts'))
            days=cfg.get('send_days') or []
            day_names=['شنبه','یکشنبه','دوشنبه','سه‌شنبه','چهارشنبه','پنجشنبه','جمعه']
            selected='، '.join(day_names[i] for i in days if 0 <= int(i) < 7) if not cfg.get('random_days') else 'تصادفی'
            text=(
                "⚙️ <b>تنظیمات عمومی انیگما</b>\n\n"
                f"📦 تعداد ارسال هفتگی هر کشور: <b>{cfg.get('weekly_per_country',3)}</b>\n"
                f"⏳ حداقل فاصله بین دو چالش: <b>{cfg.get('min_gap_hours',6)} ساعت</b>\n"
                f"📦 حذف جعبه بازنشده: <b>{cfg.get('box_expiry_minutes',60)} دقیقه</b>\n"
                f"🕐 ساعت ارسال: <b>{cfg.get('min_hour','10:00')} تا {cfg.get('max_hour','23:00')}</b>\n"
                f"📅 روزهای ارسال: <b>{selected}</b>\n"
                f"🎯 تعداد تلاش: <b>{'نامحدود' if unlimited else cfg.get('max_attempts',3)}</b>\n\n"
                "برای تغییر هر مورد، دکمه مربوط به آن را انتخاب کنید."
            )
            await query.answer(); await query.edit_message_text(text,parse_mode='HTML',reply_markup=owner_settings_keyboard(cfg)); return
        if action == "enigma_toggle":
            key=parts[2]
            if key in {"no_repeat", "active_country_only", "speed_bonus_enabled"}:
                await query.answer("این گزینه در سیستم انیگما ثابت است.", show_alert=True); return
            cfg=ensure_settings(session); cfg[key]=not bool(cfg.get(key)); enigma_set(session,'config',cfg)
            await query.answer(('فعال شد.' if cfg[key] else 'غیرفعال شد.'), show_alert=True)
            if key == 'random_days':
                await query.edit_message_text('📅 <b>روزهای ارسال انیگما</b>',parse_mode='HTML',reply_markup=owner_days_keyboard(cfg))
            elif key == 'enabled':
                text=("⚙️ <b>تنظیمات عمومی انیگما</b>\n\n"
                      f"📦 تعداد ارسال هفتگی هر کشور: <b>{cfg.get('weekly_per_country',3)}</b>\n"
                      f"⏳ حداقل فاصله بین دو چالش: <b>{cfg.get('min_gap_hours',6)} ساعت</b>\n"
                      f"📦 حذف جعبه بازنشده: <b>{cfg.get('box_expiry_minutes',60)} دقیقه</b>\n"
                      f"🕐 ساعت ارسال: <b>{cfg.get('min_hour','10:00')} تا {cfg.get('max_hour','23:00')}</b>\n"
                      f"📅 روزهای ارسال: <b>{'تصادفی' if cfg.get('random_days') else '، '.join(['شنبه','یکشنبه','دوشنبه','سه‌شنبه','چهارشنبه','پنجشنبه','جمعه'][i] for i in (cfg.get('send_days') or []) if 0<=int(i)<7)}</b>\n"
                      f"🎯 تعداد تلاش: <b>{'نامحدود' if cfg.get('unlimited_attempts') else cfg.get('max_attempts',3)}</b>")
                await query.edit_message_text(text,parse_mode='HTML',reply_markup=owner_settings_keyboard(cfg))
            return
        if action == "enigma_edit":
            key=parts[2]; cfg=ensure_settings(session); context.user_data['enigma_pending']={'kind':'config','key':key,'current':cfg.get(key),'back_callback':('owner:enigma_attempts' if key == 'max_attempts' else 'owner:enigma_settings')}
            context.user_data[_waiting_scope_key('enigma_pending')] = int(update.effective_chat.id)
            context.user_data[_waiting_scope_key("enigma_pending")] = int(update.effective_chat.id)
            back_cb = 'owner:enigma_attempts' if key == 'max_attempts' else 'owner:enigma_settings'
            await query.answer(); await query.edit_message_text(f"⚙️ <b>تنظیم انیگما</b>\n\nمقدار فعلی: <b>{cfg.get(key)}</b>\n\nمقدار جدید را ارسال کنید.",parse_mode='HTML',reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 برگشت',callback_data=back_cb)]])); return
        if action == "enigma_hours":
            cfg=ensure_settings(session)
            context.user_data['enigma_pending']={'kind':'hours','stage':'min','current':f"{cfg['min_hour']} تا {cfg['max_hour']}",'back_callback':'owner:enigma_settings'}
            context.user_data[_waiting_scope_key("enigma_pending")] = int(update.effective_chat.id)
            context.user_data['enigma_pending']['prompt_message_id'] = int(query.message.message_id)
            context.user_data['enigma_pending']['prompt_chat_id'] = int(query.message.chat_id)
            await query.answer()
            await query.edit_message_text(
                f"🕐 <b>ساعت ارسال</b>\n\nمقدار فعلی: <b>{cfg['min_hour']} تا {cfg['max_hour']}</b>\n\n<b>مرحله ۱ از ۲</b>\nساعت حداقل را ارسال کنید.\nمثلاً <code>10</code> یا <code>10:30</code>",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 برگشت',callback_data='owner:enigma_settings')]])
            ); return
        if action == "enigma_attempts":
            cfg=ensure_settings(session); context.user_data['enigma_pending']={'kind':'attempts','back_callback':'owner:enigma_attempts','prompt_message_id':int(query.message.message_id),'prompt_chat_id':int(query.message.chat_id)}; context.user_data[_waiting_scope_key('enigma_pending')]=int(update.effective_chat.id); await query.answer(); await query.edit_message_text(f"🎯 <b>تعداد تلاش</b>\n\nتعداد فعلی: <b>{cfg.get('max_attempts',3)}</b>\nنامحدود: <b>{'فعال' if cfg.get('unlimited_attempts') else 'غیرفعال'}</b>\n\nبرای تغییر تعداد، دکمه عدد را بزنید. برای نامحدود، دکمه فعال/غیرفعال را بزنید.",parse_mode='HTML',reply_markup=owner_attempts_keyboard(cfg)); return
        if action == "enigma_unlimited_toggle":
            cfg=ensure_settings(session); cfg['unlimited_attempts']=not bool(cfg.get('unlimited_attempts')); enigma_set(session,'config',cfg); await query.answer(('نامحدود فعال شد.' if cfg['unlimited_attempts'] else 'نامحدود غیرفعال شد.'), show_alert=True); await query.edit_message_text(f"🎯 <b>تعداد تلاش</b>\n\nتعداد فعلی: <b>{cfg.get('max_attempts',3)}</b>\nنامحدود: <b>{'فعال' if cfg.get('unlimited_attempts') else 'غیرفعال'}</b>",parse_mode='HTML',reply_markup=owner_attempts_keyboard(cfg)); return
        if action == "enigma_days":
            cfg=ensure_settings(session); await query.answer(); await query.edit_message_text('📅 <b>روزهای ارسال انیگما</b>',parse_mode='HTML',reply_markup=owner_days_keyboard(cfg)); return
        if action == "enigma_day_toggle":
            d=int(parts[2]); cfg=ensure_settings(session); days=set(cfg.get('send_days') or []); days.remove(d) if d in days else days.add(d); cfg['send_days']=sorted(days); enigma_set(session,'config',cfg); await query.answer(); await query.edit_message_text('📅 <b>روزهای ارسال انیگما</b>',parse_mode='HTML',reply_markup=owner_days_keyboard(cfg)); return
        if action == "enigma_levels":
            cfg=ensure_settings(session); await query.answer(); await query.edit_message_text("🎚 <b>تنظیم سطح‌های انیگما</b>",parse_mode='HTML',reply_markup=owner_levels_keyboard(cfg)); return
        if action == "enigma_level":
            lev=parts[2]; cfg=ensure_settings(session); await query.answer(); await query.edit_message_text(f"🎚 <b>تنظیم {lev}</b>",parse_mode='HTML',reply_markup=owner_level_edit_keyboard(lev,cfg)); return
        if action == "enigma_level_toggle":
            lev=parts[2]; cfg=ensure_settings(session); cfg['levels'][lev]['enabled']=not cfg['levels'][lev]['enabled']; enigma_set(session,'config',cfg); await query.answer(('سطح فعال شد.' if cfg['levels'][lev]['enabled'] else 'سطح غیرفعال شد.'), show_alert=True); await query.edit_message_text(f"🎚 <b>تنظیم سطح {lev}</b>",parse_mode='HTML',reply_markup=owner_level_edit_keyboard(lev,cfg)); return
        if action == "enigma_level_edit":
            lev,field=parts[2],parts[3]; cfg=ensure_settings(session); context.user_data['enigma_pending']={'kind':'level','level':lev,'field':field,'current':cfg['levels'][lev][field],'back_callback':f'owner:enigma_level:{lev}'}; context.user_data[_waiting_scope_key("enigma_pending")]=int(update.effective_chat.id); context.user_data['enigma_pending']['prompt_message_id']=int(query.message.message_id); context.user_data['enigma_pending']['prompt_chat_id']=int(query.message.chat_id); await query.answer(); await query.edit_message_text(f"🎚 <b>تنظیم سطح</b>\n\nمقدار فعلی: <b>{cfg['levels'][lev][field]}</b>\n\nمقدار جدید را ارسال کنید.",parse_mode='HTML',reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 برگشت',callback_data=f'owner:enigma_level:{lev}')]])); return
        if action == "enigma_types":
            cfg=ensure_settings(session); await query.answer(); await query.edit_message_text('🧩 <b>تنظیم انواع چالش</b>',parse_mode='HTML',reply_markup=owner_types_keyboard(cfg)); return
        if action == "enigma_type":
            typ=parts[2]; cfg=ensure_settings(session); await query.answer(); await query.edit_message_text('🧩 <b>تنظیم نوع چالش</b>\n\nابتدا وضعیت و وزن نوع را تنظیم کنید؛ سپس سطح موردنظر را انتخاب کنید تا تنظیمات همان سطح برای همین نوع چالش جداگانه مدیریت شود.',parse_mode='HTML',reply_markup=owner_type_edit_keyboard(typ,cfg)); return
        if action == "enigma_type_level":
            typ,lev=parts[2],parts[3]; cfg=ensure_settings(session); lv=cfg['types'][typ].setdefault('levels',{}).setdefault(lev,cfg['levels'][lev].copy()); enigma_set(session,'config',cfg); await query.answer(); await query.edit_message_text(f'🧩 <b>تنظیم سطح { {"easy":"آسان","medium":"متوسط","hard":"سخت"}.get(lev,lev) }</b>\n\nاین تنظیمات فقط برای همین نوع چالش اعمال می‌شود.',parse_mode='HTML',reply_markup=owner_type_level_edit_keyboard(typ,lev,cfg)); return
        if action == "enigma_type_level_toggle":
            type_map={'ls':'letter_shift','mo':'morse','mm':'memory_multi','mt':'memory_text'}
            typ,lev=type_map.get(parts[2],parts[2]),parts[3]; cfg=ensure_settings(session); lv=cfg['types'][typ]['levels'][lev]; lv['enabled']=not bool(lv.get('enabled',True)); enigma_set(session,'config',cfg); await query.answer(('سطح برای این نوع فعال شد.' if lv['enabled'] else 'سطح برای این نوع غیرفعال شد.'),show_alert=True); await query.edit_message_text('🧩 <b>تنظیم سطح نوع چالش</b>',parse_mode='HTML',reply_markup=owner_type_level_edit_keyboard(typ,lev,cfg)); return
        if action == "enigma_type_level_edit":
            type_map={'ls':'letter_shift','mo':'morse','mm':'memory_multi','mt':'memory_text'}
            field_map={'w':'weight','tm':'operation_seconds','qd':'question_display_seconds','min':'min_reward','max':'max_reward','sf':'speed_factor'}
            typ,lev,field=type_map.get(parts[2],parts[2]),parts[3],field_map.get(parts[4],parts[4]); cfg=ensure_settings(session); lv=cfg['types'][typ]['levels'][lev]; context.user_data['enigma_pending']={'kind':'type_level','type':typ,'level':lev,'field':field,'current':lv[field],'back_callback':f'owner:enigma_type_level:{typ}:{lev}'}; context.user_data[_waiting_scope_key("enigma_pending")]=int(update.effective_chat.id); await query.answer(); await query.edit_message_text(f'🧩 <b>تنظیم سطح نوع چالش</b>\n\nمقدار فعلی: <b>{lv[field]}</b>\n\nمقدار جدید را جداگانه ارسال کنید.',parse_mode='HTML',reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 برگشت',callback_data=f'owner:enigma_type_level:{typ}:{lev}')]])); return
        if action == "enigma_type_toggle":
            typ=parts[2]; cfg=ensure_settings(session); cfg['types'][typ]['enabled']=not cfg['types'][typ]['enabled']; enigma_set(session,'config',cfg); await query.answer(('نوع فعال شد.' if cfg['types'][typ]['enabled'] else 'نوع غیرفعال شد.'), show_alert=True); await query.edit_message_text('🧩 <b>تنظیم نوع چالش</b>',parse_mode='HTML',reply_markup=owner_type_edit_keyboard(typ,cfg)); return
        if action == "enigma_type_edit":
            typ,field=parts[2],parts[3]; cfg=ensure_settings(session); context.user_data['enigma_pending']={'kind':'type','type':typ,'field':field,'current':cfg['types'][typ][field],'back_callback':f'owner:enigma_type:{typ}'}; context.user_data[_waiting_scope_key("enigma_pending")]=int(update.effective_chat.id); context.user_data['enigma_pending']['prompt_message_id']=int(query.message.message_id); context.user_data['enigma_pending']['prompt_chat_id']=int(query.message.chat_id); await query.answer(); await query.edit_message_text(f"🧩 <b>تنظیم نوع چالش</b>\n\nمقدار فعلی: <b>{cfg['types'][typ][field]}</b>\n\nمقدار جدید را ارسال کنید.",parse_mode='HTML',reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 برگشت',callback_data=f'owner:enigma_type:{typ}')]])); return
        if action == "enigma_value_edit":
            pending = context.user_data.get("enigma_pending") or {}
            if pending.get("kind") not in {"level", "type", "type_level"} or "proposed_value" not in pending:
                await query.answer("⚠️ این عملیات منقضی شده است.", show_alert=True); return
            kind=pending.get("kind")
            if kind == "level": back=f"owner:enigma_level:{pending['level']}"; label="تنظیم سطح"
            elif kind == "type": back=f"owner:enigma_type:{pending['type']}"; label="تنظیم نوع چالش"
            else: back=f"owner:enigma_type_level:{pending['type']}:{pending['level']}"; label="تنظیم سطح نوع چالش"
            pending.pop("proposed_value", None); context.user_data["enigma_pending"]=pending; context.user_data[_waiting_scope_key("enigma_pending")]=int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text(f"📝 <b>{label}</b>\n\nمقدار جدید را ارسال کنید.",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data=back)]])); return

        if action == "enigma_value_cancel":
            pending=context.user_data.get("enigma_pending") or {}; kind=pending.get("kind")
            if kind == "level": back=f"owner:enigma_level:{pending.get('level')}"
            elif kind == "type": back=f"owner:enigma_type:{pending.get('type')}"
            elif kind == "type_level": back=f"owner:enigma_type_level:{pending.get('type')}:{pending.get('level')}"
            else: back="owner:enigma"
            context.user_data.pop("enigma_pending",None); context.user_data.pop(_waiting_scope_key("enigma_pending"),None)
            await query.answer("لغو شد."); await query.edit_message_text("🔙 عملیات لغو شد.",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data=back)]])); return

        if action == "enigma_value_confirm":
            pending=context.user_data.get("enigma_pending") or {}
            if pending.get("kind") not in {"level","type","type_level"} or "proposed_value" not in pending:
                await query.answer("⚠️ این عملیات منقضی شده است.",show_alert=True); return
            cfg=ensure_settings(session); kind=pending["kind"]; field=pending["field"]; value=pending["proposed_value"]
            if kind == "level": cfg["levels"][pending["level"]][field]=value; markup=owner_level_edit_keyboard(pending["level"],cfg); text="🎚 <b>تنظیم سطح</b>"
            elif kind == "type": cfg["types"][pending["type"]][field]=value; markup=owner_type_edit_keyboard(pending["type"],cfg); text="🧩 <b>تنظیم نوع چالش</b>"
            else: cfg["types"][pending["type"]]["levels"][pending["level"]][field]=value; markup=owner_type_level_edit_keyboard(pending["type"],pending["level"],cfg); text="🧩 <b>تنظیم سطح نوع چالش</b>"
            enigma_set(session,"config",cfg); context.user_data.pop("enigma_pending",None); context.user_data.pop(_waiting_scope_key("enigma_pending"),None)
            await query.answer("✅ مقدار ثبت شد.",show_alert=True); await query.edit_message_text(text,parse_mode="HTML",reply_markup=markup); return

        if action == "enigma_reset":
            if not owner_user:
                await query.answer("⛔ فقط Owner.", show_alert=True); return
            await query.answer()
            await query.edit_message_text(
                "♻️ <b>ریست چرخه مأموریت‌های انیگما</b>\n\n"
                "با این کار تاریخچه انجام مأموریت‌ها برای انتخاب دوباره نادیده گرفته می‌شود و مأموریت‌ها از اول قابل انتخاب خواهند شد.\n\n"
                "☢️ پاداش‌هایی که قبلاً پرداخت شده‌اند <b>پس گرفته یا ریست نمی‌شوند</b>.\n"
                "📊 آمار و سابقه پرداخت‌ها نیز حفظ می‌شود.\n\n"
                "آیا مطمئن هستید؟",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton('♻️ تأیید ریست',callback_data='owner:enigma_reset_confirm')],
                    [InlineKeyboardButton('🔙 انصراف',callback_data='owner:enigma')],
                ])
            ); return
        if action == "enigma_reset_confirm":
            if not owner_user:
                await query.answer("⛔ فقط Owner.", show_alert=True); return
            s=enigma_state(session)
            s['mission_cycle']=int(s.get('mission_cycle',0) or 0)+1
            # عملیات‌های باز قبلی منقضی می‌شوند تا بعد از ریست، چرخه جدید تمیز شروع شود؛
            # سوابق COMPLETE و پاداش‌ها دست‌نخورده می‌مانند.
            # تمام جعبه‌ها و مأموریت‌های در حال اجرا حذف می‌شوند؛ اما تاریخچه و پاداش‌ها حفظ می‌شوند.
            for rec in (s.get('active') or {}).values():
                if rec.get('status') in {STATUS_PENDING, STATUS_ACTIVE}:
                    rec['status']=STATUS_EXPIRED
                    rec['expired_by_reset']=True
                    mid=rec.get('message_id'); chat_id=rec.get('chat_id') or rec.get('user_id')
                    if mid and chat_id:
                        try:
                            await context.bot.unpin_chat_message(chat_id=int(chat_id), message_id=int(mid))
                        except Exception:
                            pass
                        try:
                            await context.bot.delete_message(chat_id=int(chat_id), message_id=int(mid))
                        except Exception:
                            pass
            enigma_set(session,'state',s)
            await query.answer('♻️ چرخه انیگما ریست شد.',show_alert=True)
            # بعد از تأیید ریست، مستقیماً پنل «مدیریت انیگما» نمایش داده شود.
            cfg = ensure_settings(session)
            await query.edit_message_text("🔐 <b>مدیریت انیگما</b>", parse_mode='HTML', reply_markup=InlineKeyboardMarkup([*owner_main_keyboard().inline_keyboard, [InlineKeyboardButton("🔙 برگشت", callback_data="owner:challenges")]])); return
        if action == "enigma_stats":
            hist=enigma_state(session).get('history',[]); stats_reset=enigma_state(session).get('stats_reset_at'); hist=[x for x in hist if not stats_reset or str(x.get('created_at',''))>=str(stats_reset)]; cnt=Counter(x.get('status') for x in hist); total_reward=sum(float(x.get('reward',0) or 0) for x in hist if x.get('status')=='COMPLETED'); solved=[x.get('solve_seconds') for x in hist if x.get('status')=='COMPLETED' and x.get('solve_seconds') is not None]; avg=(sum(solved)/len(solved)) if solved else 0
            lv=Counter(x.get('level') for x in hist); tp=Counter(x.get('type') for x in hist)
            reward_total=sum(float(x.get('reward',0) or 0) for x in hist if x.get('status')=='COMPLETED')
            reward_text=f'☢️ اورانیوم: <b>{reward_total:,.2f}</b>' if reward_total else '—'
            text=(f"📊 <b>آمار انیگما</b>\n\n📨 کل ارسال‌ها: <b>{len(hist):,}</b>\n✅ موفق: <b>{cnt['COMPLETED']:,}</b>\n❌ ناموفق: <b>{cnt['FAILED']:,}</b>\n⏱ منقضی: <b>{cnt['EXPIRED']:,}</b>\n🎁 پاداش پرداخت‌شده: {reward_text}\n⏱ میانگین زمان حل: <b>{avg:,.0f} ثانیه</b>\n\n🎚 <b>تفکیک سطح‌ها</b>\n🟢 آسان: {lv['easy']:,}\n🟡 متوسط: {lv['medium']:,}\n🔴 سخت: {lv['hard']:,}\n\n🧩 <b>تفکیک انواع</b>\n🔤 جابه‌جایی حروف: {tp['letter_shift']:,}\n📡 مورس: {tp['morse']:,}\n🧠 حفظ چند اطلاعات: {tp['memory_multi']:,}\n📜 حفظ اطلاعات در متن: {tp['memory_text']:,}")
            await query.answer(); await query.edit_message_text(text,parse_mode='HTML',reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('♻️ ریست آمار',callback_data='owner:enigma_stats_reset')],[InlineKeyboardButton('🔙 برگشت',callback_data='owner:enigma')]])); return
        if action == 'enigma_stats_reset':
            await query.answer()
            await query.edit_message_text('♻️ <b>ریست آمار انیگما</b>\n\nآمار نمایش‌داده‌شده از این لحظه از نو محاسبه می‌شود؛ سابقه مأموریت‌ها و پاداش‌ها حذف نمی‌شوند.\n\nآیا مطمئن هستید؟',parse_mode='HTML',reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('♻️ تأیید ریست آمار',callback_data='owner:enigma_stats_reset_confirm')],[InlineKeyboardButton('🔙 برگشت',callback_data='owner:enigma_stats')]])); return
        if action == 'enigma_stats_reset_confirm':
            s=enigma_state(session); s['stats_reset_at']=datetime.utcnow().isoformat(); enigma_set(session,'state',s)
            hist=enigma_state(session).get('history',[]); stats_reset=enigma_state(session).get('stats_reset_at'); hist=[x for x in hist if not stats_reset or str(x.get('created_at',''))>=str(stats_reset)]
            cnt=Counter(x.get('status') for x in hist); solved=[x.get('solve_seconds') for x in hist if x.get('status')=='COMPLETED' and x.get('solve_seconds') is not None]; avg=(sum(solved)/len(solved)) if solved else 0
            lv=Counter(x.get('level') for x in hist); tp=Counter(x.get('type') for x in hist); reward_total=sum(float(x.get('reward',0) or 0) for x in hist if x.get('status')=='COMPLETED')
            reward_text=f'☢️ اورانیوم: <b>{reward_total:,.2f}</b>' if reward_total else '—'
            text=(f"📊 <b>آمار انیگما</b>\n\n📨 کل ارسال‌ها: <b>{len(hist):,}</b>\n✅ موفق: <b>{cnt['COMPLETED']:,}</b>\n❌ ناموفق: <b>{cnt['FAILED']:,}</b>\n⏱ منقضی: <b>{cnt['EXPIRED']:,}</b>\n🎁 پاداش پرداخت‌شده: {reward_text}\n⏱ میانگین زمان حل: <b>{avg:,.0f} ثانیه</b>\n\n🎚 <b>تفکیک سطح‌ها</b>\n🟢 آسان: {lv['easy']:,}\n🟡 متوسط: {lv['medium']:,}\n🔴 سخت: {lv['hard']:,}\n\n🧩 <b>تفکیک انواع</b>\n🔤 جابه‌جایی حروف: {tp['letter_shift']:,}\n📡 مورس: {tp['morse']:,}\n🧠 حفظ چند اطلاعات: {tp['memory_multi']:,}\n📜 حفظ اطلاعات در متن: {tp['memory_text']:,}")
            await query.answer('آمار ریست شد.',show_alert=True); await query.edit_message_text(text,parse_mode='HTML',reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('♻️ ریست آمار',callback_data='owner:enigma_stats_reset')],[InlineKeyboardButton('🔙 برگشت',callback_data='owner:enigma')]])); return
        if action == "enigma_bank":
            from enigma.challenges import mission_bank_counts
            counts=mission_bank_counts(session); total=sum(counts.values()); await query.answer(); await query.edit_message_text(f'📚 <b>بانک انیگما</b>\n\nمجموع مأموریت‌های فعال: <b>{total}</b>',parse_mode='HTML',reply_markup=owner_bank_keyboard(counts)); return
        if action == "enigma_bank_list":
            data=ensure_missions(session)
            if not data:
                await query.answer('هیچ چالشی موجود نیست.',show_alert=True); return
            await query.answer(); await query.edit_message_text('📋 <b>لیست انیگماها</b>\n\nنوع چالش را انتخاب کنید:',parse_mode='HTML',reply_markup=owner_mission_list_keyboard({k:sum(1 for m in data if m.get('type')==k and m.get('enabled',True)) for k in ('letter_shift','morse','memory_multi','memory_text')})); return
        if action == "enigma_bank_type":
            typ=parts[2]; page=int(parts[3]) if len(parts)>3 else 1; data=ensure_missions(session); items=[m for m in data if m.get('type')==typ]
            if not items:
                await query.answer('هیچ چالشی از این نوع موجود نیست.',show_alert=True); return
            from enigma.challenges import TYPE_NAMES; await query.answer(); await query.edit_message_text(f'📚 <b>مأموریت‌های {TYPE_NAMES.get(typ,typ)}</b>',parse_mode='HTML',reply_markup=owner_bank_type_keyboard(typ,page,data)); return
        if action == "enigma_bank_add":
            context.user_data['enigma_pending']={'kind':'mission_add','stage':'type','data':{}}
            context.user_data[_waiting_scope_key("enigma_pending")] = int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text('➕ <b>افزودن مأموریت</b>\n\n<b>مرحله ۱ از ۵</b>\nنوع مأموریت را با یکی از دکمه‌های زیر انتخاب کنید.',parse_mode='HTML',reply_markup=owner_mission_type_keyboard()); return
        if action == "enigma_add_type":
            typ=parts[2]; valid_types={'letter_shift','morse','memory_multi','memory_text'}
            if typ not in valid_types:
                await query.answer('نوع نامعتبر است.',show_alert=True); return
            context.user_data['enigma_pending']={'kind':'mission_add','stage':'level','data':{'type':typ}}
            context.user_data[_waiting_scope_key("enigma_pending")] = int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text('➕ <b>افزودن مأموریت</b>\n\n<b>مرحله ۲ از ۵</b>\nسطح مأموریت را انتخاب کنید:',parse_mode='HTML',reply_markup=owner_mission_level_keyboard()); return
        if action == 'enigma_add_level':
            lev=parts[2]
            if lev not in {'easy','medium','hard'}:
                await query.answer('سطح نامعتبر است.',show_alert=True); return
            context.user_data['enigma_pending']['data']['level']=lev; context.user_data['enigma_pending']['stage']='prompt'
            await query.answer(); await query.edit_message_text('➕ <b>افزودن مأموریت</b>\n\n<b>مرحله ۳ از ۵</b>\nمتن چالش را جداگانه ارسال کنید.',parse_mode='HTML',reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 برگشت',callback_data='owner:enigma_bank')]])); return
        if action == 'enigma_bank_search':
            context.user_data.pop('enigma_pending', None)
            await query.answer(); await query.edit_message_text('🔎 <b>جستجوی مأموریت</b>\n\nنوع مأموریت را انتخاب کنید:',parse_mode='HTML',reply_markup=owner_mission_search_type_keyboard()); return
        if action == 'enigma_search_type':
            typ=parts[2]
            context.user_data['enigma_pending']={'kind':'enigma_bank_search','type':typ}
            context.user_data[_waiting_scope_key("enigma_pending")] = int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text('🔎 <b>جستجوی مأموریت</b>\n\nشناسه مأموریت را ارسال کنید.',parse_mode='HTML',reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 برگشت',callback_data='owner:enigma_bank')]])); return
        if action == "enigma_delete_confirm":
            typ,mid=parts[2],int(parts[3]); data=ensure_missions(session); before=len(data); data[:]=[m for m in data if not (m['type']==typ and int(m['id'])==mid)]; enigma_set(session,'missions',data); await query.answer("🗑 مأموریت حذف شد.",show_alert=True); await query.edit_message_text("📚 <b>بانک انیگما</b>",parse_mode='HTML',reply_markup=owner_bank_keyboard(__import__('enigma.challenges',fromlist=['mission_bank_counts']).mission_bank_counts(session))); return
        if action == "enigma_mission_delete":
            typ,mid=parts[2],int(parts[3])
            await query.answer(); await query.edit_message_text(f'⚠️ <b>حذف مأموریت {mid}</b>\n\nآیا از حذف این مأموریت مطمئن هستید؟',parse_mode='HTML',reply_markup=owner_mission_delete_confirm_keyboard(typ,mid)); return
        if action == "enigma_mission_edit":
            typ,mid=parts[2],int(parts[3])
            await query.answer(); await query.edit_message_text(f'✏️ <b>ویرایش مأموریت {mid}</b>\n\nبخش موردنظر را انتخاب کنید.',parse_mode='HTML',reply_markup=owner_mission_edit_keyboard(typ,mid)); return
        if action == 'enigma_edit_mission_type':
            typ,mid=parts[2],int(parts[3]); await query.answer(); await query.edit_message_text('🧩 <b>ویرایش نوع مأموریت</b>\n\nنوع جدید را انتخاب کنید:',parse_mode='HTML',reply_markup=owner_mission_type_edit_keyboard(typ,mid)); return
        if action == 'enigma_set_mission_type':
            old_typ,mid,new_typ=parts[2],int(parts[3]),parts[4]
            data=ensure_missions(session); m=next((x for x in data if x.get('type')==old_typ and int(x.get('id',0))==mid),None)
            if not m: await query.answer('مأموریت پیدا نشد.',show_alert=True); return
            m['type']=new_typ; enigma_set(session,'missions',data); await query.answer('نوع مأموریت تغییر کرد.',show_alert=True); await query.edit_message_text(f'📚 <b>مأموریت {mid}</b>',parse_mode='HTML',reply_markup=owner_mission_manage_keyboard(new_typ,mid,m.get('enabled',True))); return
        if action == 'enigma_edit_mission_level':
            typ,mid=parts[2],int(parts[3]); await query.answer(); await query.edit_message_text('🎚 <b>ویرایش سطح مأموریت</b>\n\nسطح جدید را انتخاب کنید:',parse_mode='HTML',reply_markup=owner_mission_level_edit_keyboard(typ,mid)); return
        if action == 'enigma_set_mission_level':
            typ,mid,lev=parts[2],int(parts[3]),parts[4]
            data=ensure_missions(session); m=next((x for x in data if x.get('type')==typ and int(x.get('id',0))==mid),None)
            if not m: await query.answer('مأموریت پیدا نشد.',show_alert=True); return
            m['level']=lev; enigma_set(session,'missions',data); await query.answer('سطح مأموریت تغییر کرد.',show_alert=True); await query.edit_message_text(f'📚 <b>مأموریت {mid}</b>',parse_mode='HTML',reply_markup=owner_mission_manage_keyboard(typ,mid,m.get('enabled',True))); return
        if action == 'enigma_edit_mission_reward':
            typ,mid=parts[2],int(parts[3]); await query.answer(); await query.edit_message_text('☢️ <b>ویرایش جایزه</b>\n\nجایزه بر اساس سطح محاسبه می‌شود. بخش موردنظر را انتخاب کنید:',parse_mode='HTML',reply_markup=owner_mission_reward_edit_keyboard(typ,mid)); return
        if action == 'enigma_mission_reward':
            typ,mid,field=parts[2],int(parts[3]),parts[4]
            data=ensure_missions(session); m=next((x for x in data if x.get('type')==typ and int(x.get('id',0))==mid),None)
            if not m: await query.answer('مأموریت پیدا نشد.',show_alert=True); return
            lev=m.get('level','easy'); cfg=ensure_settings(session); context.user_data['enigma_pending']={'kind':'mission_reward','type':typ,'id':mid,'level':lev,'field':field,'current':cfg['levels'][lev][field]}
            context.user_data[_waiting_scope_key("enigma_pending")] = int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text(f'☢️ <b>ویرایش جایزه سطح</b>\n\nمقدار فعلی: <b>{cfg["levels"][lev][field]}</b>\n\nمقدار جدید را جداگانه ارسال کنید.',parse_mode='HTML',reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 برگشت',callback_data=f'owner:enigma_mission_edit:{typ}:{mid}')]])); return
        if action == "enigma_edit_mission":
            typ,mid,field=parts[2],int(parts[3]),parts[4]
            m=next((x for x in ensure_missions(session) if x.get('type')==typ and int(x.get('id',0))==mid),None)
            if not m: await query.answer('مأموریت پیدا نشد.',show_alert=True); return
            context.user_data['enigma_pending']={'kind':'mission_edit','type':typ,'id':mid,'field':field,'current':m.get(field)}
            context.user_data[_waiting_scope_key("enigma_pending")] = int(update.effective_chat.id)
            labels={'prompt':'متن پرسش','answer':'پاسخ','hint':'راهنمایی'}
            await query.answer(); await query.edit_message_text(f'✏️ <b>ویرایش {labels.get(field,field)}</b>\n\nمقدار فعلی: <b>{m.get(field)}</b>\n\nمقدار جدید را ارسال کنید.',parse_mode='HTML',reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 برگشت',callback_data=f'owner:enigma_mission:{typ}:{mid}')]])); return
        if action == "enigma_mission_toggle":
            typ,mid=parts[2],int(parts[3]); data=ensure_missions(session); m=next((x for x in data if x['type']==typ and int(x['id'])==mid),None)
            if not m: await query.answer('یافت نشد.',show_alert=True); return
            m['enabled']=not bool(m.get('enabled',True)); enigma_set(session,'missions',data); await query.answer(('مأموریت فعال شد.' if m['enabled'] else 'مأموریت غیرفعال شد.'), show_alert=True); await query.edit_message_text(f"📚 <b>مأموریت {mid}</b>",parse_mode='HTML',reply_markup=owner_mission_manage_keyboard(typ,mid,m['enabled'])); return
        if action == "enigma_mission":
            typ,mid=parts[2],int(parts[3])
            m=next((x for x in ensure_missions(session) if x.get('type')==typ and int(x.get('id',0))==mid),None)
            if not m: await query.answer('یافت نشد.',show_alert=True); return
            lev=m.get('level','easy'); cfg=ensure_settings(session)
            type_cfg=cfg.get('types',{}).get(typ,{})
            lv=(type_cfg.get('levels') or cfg.get('levels',{})).get(lev,{})
            text=(f"📚 <b>اطلاعات کامل مأموریت {mid}</b>\n\n"
                  f"🆔 <b>شناسه:</b> {mid}\n"
                  f"🧩 <b>نوع:</b> {escape(TYPE_NAMES.get(typ,typ))}\n"
                  f"🎚 <b>سطح:</b> {escape({'easy':'آسان','medium':'متوسط','hard':'سخت'}.get(lev,lev))}\n"
                  f"🟢 <b>وضعیت:</b> {'فعال' if m.get('enabled',True) else 'غیرفعال'}\n"
                  f"⏱ <b>زمان حل:</b> {lv.get('operation_seconds',0)} ثانیه\n"
                  f"👁 <b>زمان نمایش پرسش:</b> {lv.get('question_display_seconds',30)} ثانیه\n"
                  f"⚡ <b>ضریب سرعت:</b> {lv.get('speed_factor',0)}\n"
                  f"☢️ <b>حداقل پاداش:</b> {lv.get('min_reward',0)}\n"
                  f"☢️ <b>حداکثر پاداش:</b> {lv.get('max_reward',0)}\n\n"
                  f"📝 <b>پرسش:</b>\n{escape(str(m.get('prompt','')))}\n\n"
                  f"🔐 <b>پاسخ صحیح:</b> <code>{escape(str(m.get('answer','')))}</code>\n"
                  f"💡 <b>راهنمایی:</b> {escape(str(m.get('hint') or 'ثبت نشده'))}")
            await query.answer(); await query.edit_message_text(text,parse_mode='HTML',reply_markup=owner_mission_manage_keyboard(typ,mid,m.get('enabled',True))); return

        # مالک همیشه دسترسی کامل دارد؛ مدیران بر اساس مجوزهای اختصاصی کنترل می‌شوند.
        permission_map = {"users":"users", "user_access":"users", "balance_change":"users", "search_users":"user_search", "search_banned":"user_search", "admin_account_settings":"user_account_settings", "admin_account_info":"user_info", "stats":"stats", "stats_all":"stats", "messages":"messages", "message_private":"message_private", "message_public":"message_public", "message_lists":"messages", "message_list":"message_lists_private", "message_list_private":"message_lists_private", "message_list_public":"message_lists_public", "stats_period":"stats"}
        required_perm = permission_map.get(action)
        granular_perm = {
            "user_balance":"balance_change", "balance_change":"balance_change", "balance_search_confirm":"balance_change", "balance_add":"balance_change", "balance_remove":"balance_change", "balance_users_done":"balance_change", "balance_country_pick":"balance_change", "balance_resource":"balance_change", "balance_infinite":"balance_change", "balance_continue":"balance_change", "balance_finish":"balance_change", "balance_commit":"balance_change",
            "user_country_edit":"country_name", "user_country_delete":"delete_country", "user_country_delete_pick":"delete_country", "user_country_delete_confirm":"delete_country", "user_country_delete_cancel":"delete_country",
            "user_swap":"swap_countries", "swap_from":"swap_countries", "swap_to":"swap_countries", "swap_confirm":"swap_countries", "swap_confirm_cancel":"swap_countries",
            "user_swap_reset":"reset_swap", "user_swap_reset_confirm":"reset_swap",
            "user_game_settings":"game_settings", "user_game_specs":"game_specs", "user_game_country":"game_specs",
            "user_leadership_country":"game_specs", "user_leadership_mode":"game_specs",
        }.get(action)
        required_perm = granular_perm or required_perm
        if required_perm and not owner_user and not admin_has_permission(session, query.from_user.id, OWNER_ID, required_perm):
            await query.answer("🔒 دسترسی محدود شد.", show_alert=True); return

        if not data.startswith("exchange"):
            context.user_data.pop("pending_exchange", None)

        # -------------------------------------------------
        # تأیید/ویرایش/لغو مقدار تنظیمات اقتصاد
        # -------------------------------------------------
        if action in {"economy_value_confirm", "economy_value_edit", "economy_value_cancel"}:
            pending = context.user_data.get("economy_pending") or context.user_data.get("owner_economy_confirm") or {}
            valid_types = {"max_level", "build_military", "build_strength", "build_production", "build_storage", "build_cost", "build_cost_uranium", "level", "build_storage_capacity", "build_military_power", "build_strength", "build_completion_time", "completion_time", "resource", "build_required_hq_level", "swap_cooldown", "country_rename_uranium", "country_rename_money", "country_rename_method", "hq_instant_finish_rate", "mine_instant_finish_rate", "arsenal_instant_finish_rate", "group", "global", "reset"}
            if (pending.get("value") is None or pending.get("type") not in valid_types):
                backup = context.user_data.get("owner_economy_confirm") or {}
                if backup.get("value") is not None and backup.get("type") in valid_types:
                    pending = dict(backup)
                    context.user_data["economy_pending"] = pending
                    context.user_data[_waiting_scope_key("economy_pending")] = int(update.effective_chat.id)
                else:
                    await query.answer("⚠️ عملیات منقضی شده است.", show_alert=True); return
            if action == "economy_value_edit":
                await query.answer()
                back = pending.get("back_callback", "owner:economy_metal_mine")
                current = pending.get("current_value")
                current_text = f"{float(current):,.2f}" if current is not None else "ثبت نشده"
                await query.edit_message_text(
                    f"✏️ <b>ویرایش مقدار</b>\n\nمقدار فعلی: <b>{current_text}</b>\n\nمقدار جدید را ارسال کنید.",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data=back)]]))
                pending.pop("value", None)
                context.user_data["economy_pending"] = pending
                context.user_data[_waiting_scope_key("economy_pending")] = int(update.effective_chat.id)
                return
            if action == "economy_value_cancel":
                back = pending.get("back_callback", "owner:economy_metal_mine")
                context.user_data.pop("economy_pending", None)
                context.user_data.pop("owner_economy_confirm", None)
                await query.answer("لغو شد.")
                await query.edit_message_text("🔙 عملیات لغو شد.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data=back)]]))
                return
            value = float(pending["value"])
            if pending.get("type") == "swap_cooldown":
                set_swap_cooldown_hours(session, value); session.commit(); back=pending.get("back_callback", "owner:economy"); context.user_data.pop("economy_pending",None)
                await query.answer("✅ محدودیت جابه‌جایی ذخیره شد.", show_alert=True)
                await query.edit_message_text("⏱️ محدودیت جابه‌جایی ذخیره شد.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data=back)]])); return
            if pending.get("type") == "country_rename_uranium":
                set_country_establishment_uranium_cost(session, value); set_country_rename_uranium_enabled(session, value > 0); session.commit(); back=pending.get("back_callback", "owner:economy"); context.user_data.pop("economy_pending",None)
                await query.answer("✅ هزینه تغییر نام کشور ذخیره شد.", show_alert=True)
                await query.edit_message_text("☢️ هزینه تغییر نام کشور ذخیره شد.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data=back)]])); return
            if pending.get("type") == "country_rename_money":
                set_country_rename_money_cost(session, value); set_country_rename_money_enabled(session, value > 0); session.commit(); back=pending.get("back_callback", "owner:general_settings"); context.user_data.pop("economy_pending",None)
                await query.answer("✅ هزینه تغییر نام با پول ذخیره شد.", show_alert=True)
                await query.edit_message_text("💰 هزینه تغییر نام با پول ذخیره شد.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data=back)]])); return

            if pending.get("building") == "leadership":
                ptype=pending.get("type")
                if ptype == "group": set_group_base(session, value)
                elif ptype == "global": set_global_base(session, value)
                elif ptype == "reset": set_repeat_reset_hours(session, value)
                else:
                    await query.answer("❌ گزینه نامعتبر است.",show_alert=True); return
                session.commit(); back=pending.get("back_callback","owner:leadership_settings"); context.user_data.pop("economy_pending",None); context.user_data.pop("owner_economy_confirm",None)
                await query.answer("✅ تنظیم تجربه رهبری ذخیره شد.",show_alert=True)
                await query.edit_message_text("✅ <b>تنظیم تجربه رهبری با موفقیت ذخیره شد.</b>",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data=back)]])); return

            if pending.get("building") == "initial":
                cfg=get_initial_resources(session); cfg[pending["field"]]=value; save_initial_resources(session,cfg); session.commit(); back=pending.get("back_callback","owner:initial_settings"); context.user_data.pop("economy_pending",None)
                await query.answer("✅ مقدار ذخیره شد.",show_alert=True); await query.edit_message_text("✅ مقدار منابع اولیه ذخیره شد.",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data=back)]])); return

            if pending.get("building") == "hq" and pending.get("type") == "hq_instant_finish_rate":
                cfg = get_hq_config(session)
                cfg["instant_finish_uranium_per_hour"] = max(0.0, float(value))
                save_hq_config(session, cfg)
                session.commit()
                back = pending.get("back_callback", "owner:economy_hq")
                context.user_data.pop("economy_pending", None)
                await query.answer("✅ نرخ اورانیوم تکمیل فوری ذخیره شد.", show_alert=True)
                await query.edit_message_text(
                    f"☢️ <b>نرخ تکمیل فوری ذخیره شد.</b>\n\n"
                    f"مقدار: <b>{float(value):,.2f}</b> اورانیوم در ساعت",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data=back)]])
                )
                return

            if pending.get("building") == "mine" and pending.get("type") == "mine_instant_finish_rate":
                cfg = get_metal_mine_config(session)
                cfg["instant_finish_uranium_per_hour"] = max(0.0, float(value))
                save_metal_mine_config(session, cfg)
                session.commit()
                back = pending.get("back_callback", "owner:mine_build")
                context.user_data.pop("economy_pending", None)
                context.user_data.pop("owner_economy_confirm", None)
                await query.answer("✅ نرخ اورانیوم تکمیل فوری معدن ذخیره شد.", show_alert=True)
                await query.edit_message_text(
                    f"☢️ <b>نرخ تکمیل فوری معدن ذخیره شد.</b>\n\nمقدار: <b>{float(value):,.2f}</b> اورانیوم در ساعت",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data=back)]])
                )
                return

            if pending.get("building") == "hq":
                cfg=get_hq_config(session)
                if pending.get("type")=="max_level": cfg["max_level"]=int(value)
                elif pending.get("type")=="build_strength": cfg["build_strength"]=value
                elif pending.get("type")=="build_military_power": cfg["build_military_power"]=value
                elif pending.get("type")=="build_completion_time": cfg["build_completion_time"]=value
                elif pending.get("type")=="build_cost": cfg["build_cost"][pending["field"]]=value
                else: cfg["levels"][int(pending["level"])][pending["field"]]=value
                save_hq_config(session,cfg); session.commit(); back=pending.get("back_callback","owner:economy_hq"); context.user_data.pop("economy_pending",None)
                await query.answer("✅ مقدار ذخیره شد.",show_alert=True); await query.edit_message_text("✅ مقدار با موفقیت ذخیره شد.",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data=back)]])); return

            if pending.get("building") == "arsenal" and pending.get("type") == "arsenal_instant_finish_rate":
                cfg = get_arsenal_config(session)
                cfg["instant_finish_uranium_per_hour"] = max(0.0, float(value))
                save_arsenal_config(session, cfg)
                session.commit()
                back = pending.get("back_callback", "owner:arsenal_build")
                context.user_data.pop("economy_pending", None)
                context.user_data.pop("owner_economy_confirm", None)
                await query.answer("✅ نرخ اورانیوم تکمیل فوری زرادخانه ذخیره شد.", show_alert=True)
                await query.edit_message_text(
                    f"☢️ <b>نرخ تکمیل فوری زرادخانه ذخیره شد.</b>\n\nمقدار: <b>{float(value):,.2f}</b> اورانیوم در ساعت",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data=back)]])
                )
                return

            if pending.get("building") == "arsenal":
                cfg = get_arsenal_config(session)
                ptype=pending.get("type")
                if ptype=="max_level": cfg["max_level"]=int(value)
                elif ptype=="build_storage_capacity": cfg["build_storage_capacity"]=value
                elif ptype=="build_military_power": cfg["build_military_power"]=value
                elif ptype=="build_strength": cfg["build_strength"]=value
                elif ptype=="build_completion_time": cfg["build_completion_time"]=value
                elif ptype=="build_required_hq_level": cfg["build_required_hq_level"]=int(value)
                elif ptype=="build_cost": cfg["build_cost"][pending["field"]]=value
                elif ptype=="level": cfg["levels"][int(pending["level"])][pending["field"]]=value
                save_arsenal_config(session,cfg); session.commit()
                back=pending.get("back_callback","owner:economy_arsenal")
                context.user_data.pop("economy_pending",None)
                await query.answer("✅ مقدار ذخیره شد.",show_alert=True)
                await query.edit_message_text("✅ مقدار با موفقیت ذخیره شد.",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data=back)]]))
                return

            cfg = get_metal_mine_config(session)
            if pending.get("type") == "max_level": cfg["max_level"] = int(value)
            elif pending.get("type") == "build_required_hq_level": cfg["build_required_hq_level"] = int(value)
            elif pending.get("type") == "build_military": cfg["build_military_power"] = value
            elif pending.get("type") == "build_strength": cfg["build_strength"] = value
            elif pending.get("type") == "build_completion_time": cfg["build_completion_time"] = value
            elif pending.get("type") == "build_production": cfg["build_production_per_hour"] = value
            elif pending.get("type") == "build_storage": cfg["build_storage_capacity"] = value
            elif pending.get("type") == "build_cost_uranium":
                cfg["build_cost_uranium"] = value
                cfg["build_cost"]["uranium"] = value
            elif pending.get("type") == "build_cost": cfg["build_cost"][pending["field"]] = value
            else: cfg["levels"][int(pending["level"])][pending["field"]] = value
            save_metal_mine_config(session, cfg); session.commit()
            back = pending.get("back_callback", "owner:economy_metal_mine")
            context.user_data.pop("economy_pending", None)
            await query.answer("✅ مقدار ذخیره شد.", show_alert=True)
            await query.edit_message_text("✅ مقدار با موفقیت ذخیره شد.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data=back)]]))
            return

        # -------------------------------------------------
        # خاموش/روشن کردن ربات
        # -------------------------------------------------
        if action == "security":
            await query.answer()
            await query.edit_message_text("🛡️ <b>امنیت</b>\n\nبخش موردنظر را انتخاب کنید.", parse_mode="HTML", reply_markup=owner_security_keyboard()); return
        if action == "optional_check":
            items=get_social_items(session,"optional_ad")
            item_id=parts[2] if len(parts)>=3 else None
            item=next((x for x in items if str(x.get("id"))==str(item_id)), None) if item_id else (items[0] if items else None)
            if not item:
                await query.answer("تبلیغ اختیاری هنوز تنظیم نشده است.", show_alert=True); return
            target = item.get("chat_id") or public_chat_target(item.get("url")) or private_message_link_chat_id(item.get("url"))
            try:
                member=await query.get_bot().get_chat_member(target, query.from_user.id)
                if getattr(member,"status","") in {"left","kicked","restricted"} and not getattr(member,"is_member",False):
                    await query.answer("❌ ابتدا عضو همین تبلیغ اختیاری شوید.", show_alert=True); return
            except Exception:
                await query.answer("⚠️ امکان بررسی عضویت این مورد وجود ندارد. برای گروه/کانال عمومی، لینک عمومی یا @نام‌کاربری را ثبت کنید.", show_alert=True); return
            # Store the selected ad id with the pending timestamp so each ad has its own reward.
            save_optional_join_pending(session, query.from_user.id, datetime.now(timezone.utc))
            row=session.scalar(select(BotSetting).where(BotSetting.key==f"social_optional_join:{query.from_user.id}"))
            if row is not None:
                row.value=json.dumps({"at":datetime.now(timezone.utc).isoformat(),"ad_id":item.get("id")},ensure_ascii=False)
            session.commit()
            await query.answer("✅ عضویت این تبلیغ ثبت شد؛ ۳۰ دقیقه عضو بمانید تا پاداش همین تبلیغ بررسی شود.", show_alert=True); return

        if action == "security_backup":
            await query.answer()
            await query.edit_message_text(owner_backup_panel_text(session), parse_mode="HTML", reply_markup=owner_backup_keyboard(session)); return
        if action == "security_anti":
            await query.answer()
            await query.edit_message_text(owner_anti_spam_panel_text(session), parse_mode="HTML", reply_markup=owner_anti_spam_keyboard(session)); return

        if action == "anti_toggle":
            value = not get_anti_spam_enabled(session); set_anti_spam_enabled(session, value); session.commit()
            await query.answer("🟢 ضداسپم فعال شد." if value else "🔴 ضداسپم غیرفعال شد.", show_alert=True)
            await query.edit_message_text(owner_anti_spam_panel_text(session), parse_mode="HTML", reply_markup=owner_anti_spam_keyboard(session)); return

        if action == "anti_edit" and len(parts) >= 3:
            field=parts[2]; labels={"user_max":"حداکثر درخواست کاربر","user_window":"بازه زمانی کاربر","group_max":"حداکثر پیام گروه","group_window":"بازه زمانی گروه"}
            vals={"user_max":get_anti_spam_user_max(session),"user_window":get_anti_spam_user_window(session),"group_max":get_anti_spam_group_max(session),"group_window":get_anti_spam_group_window(session)}
            if field not in labels: await query.answer("گزینه نامعتبر است.", show_alert=True); return
            context.user_data["security_pending"]={"field":field, "chat_id": query.message.chat_id if query.message else None, "message_id": query.message.message_id if query.message else None}
            context.user_data[_waiting_scope_key("security_pending")] = int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text(f"🛡️ <b>{labels[field]}</b>\n\nمقدار فعلی: <b>{vals[field]}</b>\n\nعدد جدید را ارسال کنید.", parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data="owner:security_anti")]])); return

        if action == "backup_start_toggle":
            value = not get_backup_started(session); set_backup_started(session, value); session.commit()
            await query.answer("🟢 پشتیبان‌گیری شروع شد." if value else "🔴 پشتیبان‌گیری متوقف شد.", show_alert=True)
            await query.edit_message_text(owner_backup_panel_text(session), parse_mode="HTML", reply_markup=owner_backup_keyboard(session)); return
        if action == "backup_interval_edit":
            context.user_data["security_pending"]={"field":"backup_interval", "chat_id": query.message.chat_id if query.message else None, "message_id": query.message.message_id if query.message else None}
            context.user_data[_waiting_scope_key("security_pending")] = int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text(f"⏱ <b>فاصله بکاپ</b>\n\nمقدار فعلی: <b>{get_backup_interval(session)}</b> دقیقه\n\nفاصله جدید را به دقیقه ارسال کنید.", parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data="owner:security_backup")]])); return
        if action == "backup_execution_time_edit":
            context.user_data["security_pending"]={"field":"backup_execution_time", "chat_id": query.message.chat_id if query.message else None, "message_id": query.message.message_id if query.message else None}
            context.user_data[_waiting_scope_key("security_pending")] = int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text(f"🕐 <b>زمان اجرا</b>\n\nزمان فعلی: <b>{get_backup_execution_time(session)}</b>\n\nزمان جدید را به شکل ساعت:دقیقه ارسال کنید؛ مثلاً ۰۴:۳۰ یا 16:45.", parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data="owner:security_backup")]])); return

        if action == "social_links":
            text = _social_links_panel_text(session)
            await query.answer(); await query.edit_message_text(text, parse_mode="HTML", reply_markup=owner_social_links_keyboard()); return

        if action == "social_add":
            _clear_social_waiting(context)
            await query.answer()
            await query.edit_message_text("➕ <b>افزودن</b>\n\nنوع موردی که می‌خواهید اضافه کنید را انتخاب کنید:", parse_mode="HTML", reply_markup=owner_social_add_keyboard())
            return

        if action == "social_item" and len(parts) >= 3:
            _clear_social_waiting(context)
            item_id=parts[2]
            item=next((x for x in get_social_items(session) if str(x.get("id"))==str(item_id)),None)
            if not item:
                await query.answer("مورد پیدا نشد.", show_alert=True); return
            labels={"panel":"🧩 پنل بازی","mandatory_ad":"🚨 تبلیغ اجباری","optional_ad":"🎁 تبلیغ اختیاری","chat":"💬 چت بازی","channel":"📣 کانال بازی"}
            active=bool(item.get('active',True))
            text=(f"🔗 <b>{labels.get(item.get('type'),'مورد')}</b>\n\n"
                  f"📌 وضعیت: <b>{'فعال' if active else 'غیرفعال'}</b>\n"
                  f"🔗 لینک: <code>{escape(str(item.get('url') or 'ثبت نشده'))}</code>\n"
                  f"🆔 شناسه چت: <code>{escape(str(item.get('chat_id') or 'ثبت نشده'))}</code>\n"
                  f"📂 نوع چت: <b>{escape(str(item.get('chat_type') or 'ثبت نشده'))}</b>\n")
            if item.get('type')=='optional_ad':
                text += f"☢️ پاداش: <b>{float(item.get('reward',0) or 0):,.0f}</b> اورانیوم\n"
                text += f"⏳ زمان دریافت پاداش: <b>{optional_reward_delay_minutes(item)} دقیقه</b>\n"
                text += f"👥 محدودیت کاربر: <b>{int(item.get('max_members')):,}</b>\n" if item.get('max_members') else "👥 محدودیت کاربر: <b>بدون محدودیت</b>\n"
                exp=item.get('expires_at')
                if exp:
                    try:
                        dt=datetime.fromisoformat(str(exp)); dt=dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
                        mins=max(0,int((dt-datetime.now(timezone.utc)).total_seconds()/60))
                        text += f"⏱️ محدودیت زمان: <b>{mins} دقیقه</b>\n"
                    except Exception: text += "⏱️ محدودیت زمان: <b>تنظیم شده</b>\n"
                else: text += "⏱️ محدودیت زمان: <b>بدون محدودیت</b>\n"
                text += f"🎁 تعداد دریافت‌کنندگان پاداش: <b>{optional_claimed_count(session, item.get('id')):,}</b>\n"
            elif item.get('type')=='mandatory_ad':
                text += f"👥 تعداد اعضای تأییدشده: <b>{_verified_count(session, item.get('id')):,}</b>\n"
                text += f"👥 محدودیت کاربر: <b>{int(item.get('max_members')):,}</b>\n" if item.get('max_members') else "👥 محدودیت کاربر: <b>بدون محدودیت</b>\n"
                exp=item.get('expires_at')
                if exp:
                    try:
                        dt=datetime.fromisoformat(str(exp)); dt=dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
                        mins=max(0,int((dt-datetime.now(timezone.utc)).total_seconds()/60))
                        text += f"⏱️ محدودیت زمان: <b>{mins} دقیقه</b>\n"
                    except Exception: text += "⏱️ محدودیت زمان: <b>تنظیم شده</b>\n"
                else: text += "⏱️ محدودیت زمان: <b>بدون محدودیت</b>\n"
            # اطلاعات زمان/دلیل غیرفعال‌سازی عمداً در صفحه جزئیات نمایش داده نمی‌شود.
            await query.answer()
            await query.edit_message_text(text,parse_mode="HTML",reply_markup=owner_social_item_detail_keyboard(item_id,bool(item.get('active',True)),item.get('type')))
            return

        if action == "social_toggle" and len(parts) >= 3:
            item_id=parts[2]
            items=get_social_items(session)
            item=next((x for x in items if str(x.get('id'))==str(item_id)),None)
            if not item:
                await query.answer("مورد پیدا نشد.", show_alert=True); return
            item["active"] = not bool(item.get("active",True))
            if item["active"]:
                reset_social_item_state(session, item.get("id"), item.get("type"))
                item.pop("disabled_at",None)
                item.pop("disabled_reason",None)
                item.pop("expires_at",None)
            _save_items(session,items); session.commit()
            await query.answer("🟢 فعال شد." if item["active"] else "🔴 غیرفعال شد.", show_alert=True)
            labels={"panel":"🧩 پنل بازی","mandatory_ad":"🚨 تبلیغ اجباری","optional_ad":"🎁 تبلیغ اختیاری","chat":"💬 چت بازی","channel":"📣 کانال بازی"}
            active=bool(item['active'])
            text=(f"🔗 <b>{labels.get(item.get('type'),'مورد')}</b>\n\n"
                  f"📌 وضعیت: <b>{'فعال' if active else 'غیرفعال'}</b>\n"
                  f"🔗 لینک: <code>{escape(str(item.get('url') or 'ثبت نشده'))}</code>\n"
                  f"🆔 شناسه چت: <code>{escape(str(item.get('chat_id') or 'ثبت نشده'))}</code>\n"
                  f"📂 نوع چت: <b>{escape(str(item.get('chat_type') or 'ثبت نشده'))}</b>\n")
            if item.get('type')=='optional_ad':
                text += f"☢️ پاداش: <b>{float(item.get('reward',0) or 0):,.0f}</b> اورانیوم\n"
                text += f"⏳ زمان دریافت پاداش: <b>{optional_reward_delay_minutes(item)} دقیقه</b>\n"
                text += f"👥 محدودیت کاربر: <b>{int(item.get('max_members')):,}</b>\n" if item.get('max_members') else "👥 محدودیت کاربر: <b>بدون محدودیت</b>\n"
                exp=item.get('expires_at')
                if exp:
                    try:
                        dt=datetime.fromisoformat(str(exp)); dt=dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
                        mins=max(0,int((dt-datetime.now(timezone.utc)).total_seconds()/60))
                        text += f"⏱️ محدودیت زمان: <b>{mins} دقیقه</b>\n"
                    except Exception: text += "⏱️ محدودیت زمان: <b>تنظیم شده</b>\n"
                else: text += "⏱️ محدودیت زمان: <b>بدون محدودیت</b>\n"
                text += f"🎁 تعداد دریافت‌کنندگان پاداش: <b>{optional_claimed_count(session, item.get('id')):,}</b>\n"
            elif item.get('type')=='mandatory_ad':
                text += f"👥 تعداد اعضای تأییدشده: <b>{_verified_count(session, item.get('id')):,}</b>\n"
                text += f"👥 محدودیت کاربر: <b>{int(item.get('max_members')):,}</b>\n" if item.get('max_members') else "👥 محدودیت کاربر: <b>بدون محدودیت</b>\n"
                exp=item.get('expires_at')
                if exp:
                    try:
                        dt=datetime.fromisoformat(str(exp)); dt=dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
                        mins=max(0,int((dt-datetime.now(timezone.utc)).total_seconds()/60))
                        text += f"⏱️ محدودیت زمان: <b>{mins} دقیقه</b>\n"
                    except Exception: text += "⏱️ محدودیت زمان: <b>تنظیم شده</b>\n"
                else: text += "⏱️ محدودیت زمان: <b>بدون محدودیت</b>\n"
            # اطلاعات زمان/دلیل غیرفعال‌سازی عمداً در صفحه جزئیات نمایش داده نمی‌شود.
            await query.edit_message_text(text,parse_mode="HTML",reply_markup=owner_social_item_detail_keyboard(item_id,active,item.get('type')))
            return

        if action == "social_list":
            items=get_social_items(session)
            if not items:
                await query.answer("❌ هیچ چت، کانال یا تبلیغی موجود نیست.", show_alert=True)
                return
            labels={"panel":"🧩 پنل بازی","mandatory_ad":"🚨 تبلیغ اجباری","optional_ad":"🎁 تبلیغ اختیاری","chat":"💬 چت بازی","channel":"📣 کانال بازی"}
            lines=["📋 <b>فهرست چت، کانال و تبلیغات</b>", ""]
            for i,item in enumerate(items,1):
                reward=f" — ☢️ پاداش: {float(item.get('reward',0) or 0):,.0f}" if item.get('type')=='optional_ad' else ''
                status="🟢 فعال" if bool(item.get("active",True)) else "🔴 غیرفعال"
                if item.get('type') == 'optional_ad':
                    limit=f" — 🎁 دریافت‌کننده: {optional_claimed_count(session, item.get('id')):,}"
                elif item.get('type') == 'mandatory_ad':
                        limit=f" — 👥 عضو تأییدشده: {_verified_count(session, item.get('id')):,}"
                else:
                    limit=""
                lines.append(f"<b>{i}. {labels.get(item.get('type'),'🔗')}</b> — {status}{reward}{limit}\n<code>{escape(str(item.get('url') or ''))}</code>\n")
            await query.answer(); await query.edit_message_text("\n".join(lines), parse_mode="HTML", reply_markup=owner_social_list_keyboard(items)); return

        if action == "social_delete":
            _clear_social_waiting(context)
            items=get_social_items(session)
            if not items:
                await query.answer("❌ هیچ چت، کانال یا تبلیغی برای حذف موجود نیست.", show_alert=True)
                return
            await query.answer()
            await query.edit_message_text("🗑️ <b>حذف</b>\n\nموردی را که می‌خواهید حذف کنید انتخاب کنید:", parse_mode="HTML", reply_markup=owner_social_delete_keyboard(items))
            return

        if action == "social_add_type" and len(parts) >= 3:
            field=parts[2]
            if field not in {"panel","mandatory_ad","optional_ad","chat","channel"}:
                await query.answer("گزینه نامعتبر است.", show_alert=True); return
            _clear_social_waiting(context)
            context.user_data["social_pending"]={"mode":"add","field":field}
            context.user_data[_waiting_scope_key("social_pending")] = int(update.effective_chat.id)
            label={"panel":"پنل بازی","mandatory_ad":"تبلیغ اجباری","optional_ad":"تبلیغ اختیاری","chat":"چت بازی","channel":"کانال بازی"}[field]
            hint="لینک عمومی یا خصوصی گروه/کانال را ارسال کنید. لینک دعوت خصوصی مثل https://t.me/+... هم پشتیبانی می‌شود؛ برای تأیید، بعد از لینک، فقط لینک یکی از پیام‌های همان چت/کانال را کپی کنید و برای ربات بفرستید؛ نیازی به Forward نیست." if field in {"mandatory_ad","optional_ad","chat","channel"} else "لینک پنل بازی را با https:// ارسال کنید."
            if field=="mandatory_ad": hint += "\n⚠️ برای حد اجباری واقعی، حتماً لینک عمومی یا @نام‌کاربری کانال/گروه را ثبت کنید؛ لینک دعوت خصوصی +... قابل بررسی عضویت توسط Bot API نیست."
            if field=="optional_ad": hint += "\nبعد از ثبت لینک، پاداش همین تبلیغ را جداگانه تعیین می‌کنید."
            await query.answer(); await query.edit_message_text(f"➕ <b>افزودن {label}</b>\n\n{hint}", parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="owner:social_add")]])); return

        if action == "social_optional_reward_start" and len(parts) >= 2:
            pending=context.user_data.get("social_pending") or {}
            if pending.get("mode") != "optional_reward_wait":
                await query.answer("⚠️ عملیات افزودن منقضی شده است.",show_alert=True); return
            pending["mode"]="reward_item"
            context.user_data["social_pending"]=pending
            context.user_data[_waiting_scope_key("social_pending")] = int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text("☢️ <b>پاداش تبلیغ اختیاری</b>\n\nمقدار اورانیوم را ارسال کنید:",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="owner:social_add")]])); return

        if action == "social_reward_back":
            pending=context.user_data.get("social_pending") or {}
            if pending.get("mode") != "reward_delay_wait":
                await query.answer("⚠️ عملیات منقضی شده است.",show_alert=True); return
            pending["mode"]="reward_item"; context.user_data["social_pending"]=pending
            context.user_data[_waiting_scope_key("social_pending")] = int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text("☢️ <b>پاداش تبلیغ اختیاری</b>\n\nمقدار اورانیوم را ارسال کنید:",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="owner:social_add")]])); return

        if action == "social_constraint" and len(parts) >= 3:
            mode=parts[2]
            pending=context.user_data.get("social_pending") or {}
            if mode == "back":
                # برگشت عمومی از مرحلهٔ محدودیت به مرحلهٔ قبلیِ واقعی برمی‌گردد.
                stage=pending.get("constraint_stage")
                if stage == "done":
                    pending["constraint_waiting"]="time"
                    pending["constraint_stage"]="time"
                    context.user_data["social_pending"]=pending
                    context.user_data[_waiting_scope_key("social_pending")] = int(update.effective_chat.id)
                    await query.answer(); await query.edit_message_text("⏱️ <b>محدودیت زمانی را ارسال کنید</b>\n\nمدت فعال بودن تبلیغ را به دقیقه بفرستید:",parse_mode="HTML",reply_markup=social_time_constraint_keyboard()); return
                if stage == "time":
                    pending["constraint_waiting"]="members"
                    pending["constraint_stage"]="members"
                    context.user_data["social_pending"]=pending
                    context.user_data[_waiting_scope_key("social_pending")] = int(update.effective_chat.id)
                    await query.answer(); await query.edit_message_text("👥 <b>محدودیت اعضا را ارسال کنید</b>\n\nحداکثر تعداد اعضا را به‌صورت عدد صحیح بفرستید:",parse_mode="HTML",reply_markup=social_members_constraint_keyboard()); return
                if pending.get("field") == "optional_ad" and stage == "members":
                    pending["mode"]="reward_delay_wait"
                    pending.pop("constraint_waiting",None)
                    context.user_data["social_pending"]=pending
                    context.user_data[_waiting_scope_key("social_pending")] = int(update.effective_chat.id)
                    await query.answer(); await query.edit_message_text("⏳ <b>زمان دریافت پاداش</b>\n\nمدت عضویت لازم تا دریافت پاداش را به دقیقه ارسال کنید.\nمثلاً 60 برای یک ساعت.",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="owner:social_add")]])); return
                context.user_data.pop("social_pending",None)
                await query.answer(); await query.edit_message_text("➕ <b>افزودن</b>",parse_mode="HTML",reply_markup=owner_social_add_keyboard()); return
            if mode == "edit":
                await query.answer(); await query.edit_message_text("✏️ <b>ویرایش مشخصات</b>\n\nموردی را که می‌خواهید تغییر دهید انتخاب کنید:",parse_mode="HTML",reply_markup=social_add_edit_keyboard(pending)); return
            if mode in {"edit_link","edit_reward","edit_members","edit_time"}:
                if mode == "edit_link":
                    pending["mode"]="edit_item"; context.user_data["social_pending"]=pending
                    context.user_data[_waiting_scope_key("social_pending")] = int(update.effective_chat.id)
                    await query.answer(); await query.edit_message_text("🔗 <b>ویرایش لینک</b>\n\nلینک جدید را ارسال کنید.",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="owner:social_constraint:edit")]])); return
                if mode == "edit_reward":
                    pending["mode"]="reward_item"; context.user_data["social_pending"]=pending
                    context.user_data[_waiting_scope_key("social_pending")] = int(update.effective_chat.id)
                    await query.answer(); await query.edit_message_text("☢️ <b>ویرایش پاداش</b>\n\nمقدار جدید اورانیوم را ارسال کنید.",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="owner:social_constraint:edit")]])); return
                if mode == "edit_members":
                    pending["mode"]="add_edit_members"; pending["constraint_waiting"]="members"; context.user_data["social_pending"]=pending
                    context.user_data[_waiting_scope_key("social_pending")] = int(update.effective_chat.id)
                    await query.answer(); await query.edit_message_text("👥 <b>ویرایش محدودیت کاربر</b>\n\nمقدار جدید را ارسال کنید.",parse_mode="HTML",reply_markup=social_members_constraint_keyboard()); return
                pending["mode"]="add_edit_time"; pending["constraint_waiting"]="time"; context.user_data["social_pending"]=pending
                context.user_data[_waiting_scope_key("social_pending")] = int(update.effective_chat.id)
                await query.answer(); await query.edit_message_text("⏱️ <b>ویرایش محدودیت زمان</b>\n\nمدت جدید را به دقیقه ارسال کنید.",parse_mode="HTML",reply_markup=social_time_constraint_keyboard()); return
            if mode == "members_back":
                pending["constraint_waiting"]="members"; pending["constraint_stage"]="members"
                context.user_data["social_pending"]=pending
                context.user_data[_waiting_scope_key("social_pending")] = int(update.effective_chat.id)
                await query.answer(); await query.edit_message_text("👥 <b>محدودیت اعضا را ارسال کنید</b>\n\nحداکثر تعداد اعضا را به‌صورت عدد صحیح بفرستید:",parse_mode="HTML",reply_markup=social_members_constraint_keyboard()); return
            if mode == "members" and len(parts) >= 3:
                pending["constraint_waiting"]="members"; context.user_data["social_pending"]=pending
                context.user_data[_waiting_scope_key("social_pending")] = int(update.effective_chat.id)
                await query.answer(); await query.edit_message_text("👥 <b>محدودیت اعضا را ارسال کنید</b>\n\nحداکثر تعداد اعضا را به‌صورت عدد صحیح بفرستید:",parse_mode="HTML",reply_markup=social_members_constraint_keyboard()); return
            if mode == "time" and len(parts) >= 3:
                pending["constraint_waiting"]="time"; context.user_data["social_pending"]=pending
                context.user_data[_waiting_scope_key("social_pending")] = int(update.effective_chat.id)
                await query.answer(); await query.edit_message_text("⏱️ <b>محدودیت زمانی را ارسال کنید</b>\n\nمدت فعال بودن را به دقیقه بفرستید:",parse_mode="HTML",reply_markup=social_time_constraint_keyboard()); return
            await query.answer("گزینه نامعتبر است.",show_alert=True); return

        if data == "owner:social_constraint_members:back":
            pending=context.user_data.get("social_pending") or {}
            if pending.get("mode") == "add_edit_members":
                pending["mode"]="add"; pending.pop("constraint_waiting",None); context.user_data["social_pending"]=pending
                context.user_data[_waiting_scope_key("social_pending")] = int(update.effective_chat.id)
                await query.answer(); await query.edit_message_text("✏️ <b>ویرایش مشخصات</b>",parse_mode="HTML",reply_markup=social_add_edit_keyboard(pending)); return
            field=pending.get("field")
            if field=="optional_ad":
                pending["mode"]="reward_delay_wait"; pending["constraint_waiting"]="reward_delay"; context.user_data["social_pending"]=pending
                context.user_data[_waiting_scope_key("social_pending")] = int(update.effective_chat.id)
                await query.answer(); await query.edit_message_text("⏳ <b>زمان دریافت پاداش</b>\n\nمدت عضویت لازم را به دقیقه ارسال کنید.",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="owner:social_add")]])); return
            pending["mode"]="add"; pending.pop("constraint_waiting",None); context.user_data["social_pending"]=pending
            context.user_data[_waiting_scope_key("social_pending")] = int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text("➕ <b>لینک را ارسال کنید</b>",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="owner:social_add")]])); return

        if data == "owner:social_constraint_time:back":
            pending=context.user_data.get("social_pending") or {}
            if pending.get("mode") == "add_edit_time":
                pending["mode"]="add"; pending.pop("constraint_waiting",None); context.user_data["social_pending"]=pending
                context.user_data[_waiting_scope_key("social_pending")] = int(update.effective_chat.id)
                await query.answer(); await query.edit_message_text("✏️ <b>ویرایش مشخصات</b>",parse_mode="HTML",reply_markup=social_add_edit_keyboard(pending)); return
            pending["constraint_waiting"]="members"; pending["constraint_stage"]="members"; context.user_data["social_pending"]=pending
            context.user_data[_waiting_scope_key("social_pending")] = int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text("👥 <b>محدودیت اعضا را ارسال کنید</b>",parse_mode="HTML",reply_markup=social_members_constraint_keyboard()); return

        if data == "owner:social_constraint_members:none":
            pending=context.user_data.get("social_pending") or {}
            if pending.get("mode") == "add_edit_members":
                pending.pop("max_members",None); pending["limit_type"]="none"; pending["mode"]="add"; pending.pop("constraint_waiting",None); context.user_data["social_pending"]=pending
                context.user_data[_waiting_scope_key("social_pending")] = int(update.effective_chat.id)
                await query.answer("✅ محدودیت کاربر حذف شد.",show_alert=True); await query.edit_message_text("✏️ <b>ویرایش مشخصات</b>",parse_mode="HTML",reply_markup=social_add_edit_keyboard(pending)); return
            if pending.get("mode") != "add": await query.answer("⚠️ عملیات منقضی شده است.",show_alert=True); return
            pending.pop("max_members",None); pending["limit_type"]="none"; pending["constraint_waiting"]="time"; pending["constraint_stage"]="time"
            context.user_data["social_pending"]=pending
            context.user_data[_waiting_scope_key("social_pending")] = int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text("⏱️ <b>محدودیت زمانی را ارسال کنید</b>\n\nمدت فعال بودن تبلیغ را به دقیقه بفرستید:",parse_mode="HTML",reply_markup=social_time_constraint_keyboard()); return

        if data == "owner:social_constraint_time:none":
            pending=context.user_data.get("social_pending") or {}
            if pending.get("mode") == "add_edit_time":
                pending.pop("duration_minutes",None); pending["limit_type"]="none"; pending["mode"]="add"; pending.pop("constraint_waiting",None); context.user_data["social_pending"]=pending
                context.user_data[_waiting_scope_key("social_pending")] = int(update.effective_chat.id)
                await query.answer("✅ محدودیت زمان حذف شد.",show_alert=True); await query.edit_message_text("✏️ <b>ویرایش مشخصات</b>",parse_mode="HTML",reply_markup=social_add_edit_keyboard(pending)); return
            if pending.get("mode") != "add": await query.answer("⚠️ عملیات منقضی شده است.",show_alert=True); return
            pending.pop("duration_minutes",None); pending.pop("constraint_waiting",None); pending["constraint_stage"]="done"
            context.user_data["social_pending"]=pending
            context.user_data[_waiting_scope_key("social_pending")] = int(update.effective_chat.id)
            draft=pending.get("draft") or {}
            typ={"mandatory_ad":"🚨 تبلیغ اجباری","optional_ad":"🎁 تبلیغ اختیاری","chat":"💬 چت بازی","channel":"📣 کانال بازی","panel":"🧩 پنل بازی"}.get(pending.get("field"),"🔗 مورد")
            text=f"📋 <b>مشخصات نهایی ثبت</b>\n\n📌 نوع: <b>{typ}</b>\n🔗 لینک: <code>{escape(str(draft.get('link','')))}</code>\n"
            if pending.get("field")=="optional_ad": text += f"☢️ پاداش: <b>{float(draft.get('reward',0) or 0):,.0f}</b> اورانیوم\n⏳ زمان دریافت پاداش: <b>{int(pending.get('reward_delay_minutes',60) or 60)} دقیقه</b>\n"
            if pending.get("max_members"):
                text += f"👥 محدودیت اعضا: <b>{int(pending.get('max_members')):,}</b>\n"
            else:
                text += "👥 محدودیت اعضا: <b>بدون محدودیت</b>\n"
            if pending.get("duration_minutes"):
                text += f"⏱️ محدودیت زمانی: <b>{int(pending.get('duration_minutes'))} دقیقه</b>\n"
            else:
                text += "⏱️ محدودیت زمانی: <b>بدون محدودیت</b>\n"
            text += "\nهمه مشخصات را بررسی کنید."
            await query.answer(); await query.edit_message_text(text,parse_mode="HTML",reply_markup=social_add_confirm_keyboard()); return

        if action == "social_add_cancel":
            context.user_data.pop("social_pending",None); await query.answer("لغو شد.",show_alert=True); await query.edit_message_text("➕ <b>افزودن</b>",parse_mode="HTML",reply_markup=owner_social_add_keyboard()); return

        if action == "social_add_confirm":
            pending=context.user_data.get("social_pending") or {}
            draft=pending.get("draft")
            if pending.get("mode")!="add" or not draft:
                await query.answer("⚠️ اطلاعات افزودن موجود نیست.",show_alert=True); return
            item=add_social_item(session,pending.get("field"),draft.get("link"),float(draft.get("reward",0) or 0),chat_id=draft.get("chat_id"),chat_type=draft.get("chat_type"))
            if pending.get("field") == "optional_ad":
                item["reward_delay_minutes"] = max(1, int(pending.get("reward_delay_minutes", 60) or 60))
            if pending.get("limit_type")=="members": item["max_members"]=int(pending.get("max_members")); item["limit_type"]="members"
            elif pending.get("limit_type")=="time":
                item["expires_at"]=(datetime.now(timezone.utc)+timedelta(minutes=int(pending.get("duration_minutes",0) or 0))).isoformat()
                item["limit_type"]="time"
            else: item["limit_type"]="none"
            # add_social_item already saved; write the finalized item back.
            items=get_social_items(session)
            for x in items:
                if str(x.get("id"))==str(item.get("id")): x.update(item)
            _save_items(session,items); session.commit()
            context.user_data.pop("social_pending",None)
            if pending.get("field") == "optional_ad":
                try:
                    context.application.create_task(scan_existing_optional_memberships(query.get_bot()))
                except Exception:
                    pass
            await query.answer("✅ مورد با موفقیت ثبت شد.",show_alert=True)
            await query.edit_message_text(_social_links_panel_text(session),parse_mode="HTML",reply_markup=owner_social_links_keyboard()); return

        if action == "social_delete_item" and len(parts) >= 3:
            item_id=parts[2]
            item=next((x for x in get_social_items(session) if str(x.get("id"))==str(item_id)),None)
            if not item:
                await query.answer("این مورد دیگر وجود ندارد.",show_alert=True); return
            context.user_data["social_delete_pending"]=item_id
            context.user_data[_waiting_scope_key("social_delete_pending")] = int(update.effective_chat.id)
            label={"panel":"پنل بازی","mandatory_ad":"تبلیغ اجباری","optional_ad":"تبلیغ اختیاری","chat":"چت بازی","channel":"کانال بازی"}.get(item.get("type"),"مورد")
            await query.answer()
            await query.edit_message_text(f"🗑️ <b>تأیید حذف</b>\n\n{label}\n<code>{escape(str(item.get('url') or ''))}</code>\n\nآیا مطمئن هستید؟",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ تأیید حذف",callback_data=f"owner:social_delete_confirm:{item_id}")],[InlineKeyboardButton("🔙 برگشت",callback_data=f"owner:social_item:{item_id}")]])); return

        if action == "social_delete_confirm" and len(parts) >= 3:
            item_id=parts[2]
            if not delete_social_item(session,item_id):
                await query.answer("این مورد دیگر وجود ندارد.",show_alert=True); return
            session.commit(); context.user_data.pop("social_delete_pending",None)
            await query.answer("🗑️ مورد حذف شد.",show_alert=True)
            items=get_social_items(session)
            if not items:
                await query.edit_message_text("💬 <b>چت، کانال و تبلیغات</b>",parse_mode="HTML",reply_markup=owner_social_links_keyboard()); return
            labels={"panel":"🧩 پنل بازی","mandatory_ad":"🚨 تبلیغ اجباری","optional_ad":"🎁 تبلیغ اختیاری","chat":"💬 چت بازی","channel":"📣 کانال بازی"}
            lines=["📋 <b>فهرست چت، کانال و تبلیغات</b>", ""]
            for i,item in enumerate(items,1):
                reward=f" — ☢️ پاداش: {float(item.get('reward',0) or 0):,.0f}" if item.get('type')=='optional_ad' else ''
                status="🟢 فعال" if bool(item.get('active',True)) else "🔴 غیرفعال"
                limit=""
                if item.get('type')=='optional_ad':
                    limit=f" — 🎁 دریافت‌کننده: {optional_claimed_count(session, item.get('id')):,}"
                elif item.get('type')=='mandatory_ad':
                        limit=f" — 👥 عضو تأییدشده: {_verified_count(session, item.get('id')):,}"
                lines.append(f"<b>{i}. {labels.get(item.get('type'),'🔗')}</b> — {status}{reward}{limit}\n<code>{escape(str(item.get('url') or ''))}</code>\n")
            await query.edit_message_text("\n".join(lines),parse_mode="HTML",reply_markup=owner_social_list_keyboard(items)); return

        if action == "social_edit" and len(parts) >= 3:
            field=parts[2]
            labels={"panel":"لینک پنل","mandatory_ad":"لینک تبلیغ اجباری","optional_ad":"لینک تبلیغ اختیاری","chat":"لینک چت ربات","channel":"لینک کانال ربات","optional_ad_reward":"پاداش اورانیوم تبلیغ اختیاری"}
            if field not in labels: await query.answer("گزینه نامعتبر است.",show_alert=True); return
            context.user_data["social_pending"]={"mode":"legacy_edit","field":field}
            context.user_data[_waiting_scope_key("social_pending")] = int(update.effective_chat.id)
            current=get_social_settings(session).get(field,"")
            hint="عدد صحیح اورانیوم را ارسال کنید." if field=="optional_ad_reward" else "لینک را با https:// یا @ ارسال کنید."
            await query.answer(); await query.edit_message_text(f"✏️ <b>{labels[field]}</b>\n\nمقدار فعلی: <code>{escape(str(current or 'تنظیم نشده'))}</code>\n\n{hint}",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="owner:social_links")]])); return

        if action == "social_edit_item" and len(parts) >= 3:
            item_id=parts[2]; item=next((x for x in get_social_items(session) if str(x.get('id'))==str(item_id)),None)
            if not item: await query.answer("مورد پیدا نشد.",show_alert=True); return
            sub=parts[3] if len(parts)>=4 else "link"
            if sub == "menu":
                await query.answer()
                label={"mandatory_ad":"تبلیغ اجباری","optional_ad":"تبلیغ اختیاری","chat":"چت بازی","channel":"کانال بازی","panel":"پنل بازی"}.get(item.get("type"),"مورد")
                await query.edit_message_text(f"✏️ <b>ویرایش {label}</b>\n\nموردی را که می‌خواهید تغییر دهید انتخاب کنید:",parse_mode="HTML",reply_markup=owner_social_edit_keyboard(item_id,item.get("type"))); return
            if item.get("type") == "mandatory_ad" and sub == "menu":
                await query.answer()
                await query.edit_message_text("✏️ <b>ویرایش تبلیغ اجباری</b>\n\nموردی را که می‌خواهید تغییر دهید انتخاب کنید:",parse_mode="HTML",reply_markup=owner_mandatory_ad_edit_keyboard(item_id)); return
            if item.get("type") in {"optional_ad", "mandatory_ad"} and sub == "members":
                _clear_social_waiting(context)
                context.user_data["social_pending"]={"mode":"edit_members","item_id":item_id}
                context.user_data[_waiting_scope_key("social_pending")] = int(update.effective_chat.id)
                current_members = f"{int(item.get('max_members')):,}" if item.get('max_members') else "بدون محدودیت"
                await query.answer(); await query.edit_message_text(f"👥 <b>ویرایش محدودیت کاربر</b>\n\nمحدودیت فعلی: <b>{current_members}</b>\n\nسقف جدید را به‌صورت عدد ارسال کنید.",parse_mode="HTML",reply_markup=owner_optional_ad_members_keyboard(item_id)); return
            if item.get("type") in {"optional_ad", "mandatory_ad"} and sub == "time":
                _clear_social_waiting(context)
                context.user_data["social_pending"]={"mode":"edit_time","item_id":item_id}
                context.user_data[_waiting_scope_key("social_pending")] = int(update.effective_chat.id)
                current="بدون محدودیت"
                exp=item.get("expires_at")
                if exp:
                    try:
                        dt=datetime.fromisoformat(str(exp))
                        if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
                        mins=max(1,int((dt-datetime.now(timezone.utc)).total_seconds()/60))
                        current=f"حدود {mins} دقیقه باقی‌مانده"
                    except Exception: pass
                await query.answer(); await query.edit_message_text(f"⏱️ <b>ویرایش محدودیت زمان</b>\n\nوضعیت فعلی: <b>{current}</b>\n\nمدت جدید را به دقیقه ارسال کنید.",parse_mode="HTML",reply_markup=owner_optional_ad_time_keyboard(item_id)); return
            if item.get("type") == "optional_ad" and sub == "delay":
                _clear_social_waiting(context)
                context.user_data["social_pending"]={"mode":"edit_delay","item_id":item_id}
                context.user_data[_waiting_scope_key("social_pending")] = int(update.effective_chat.id)
                await query.answer(); await query.edit_message_text(f"⏳ <b>تنظیم زمان دریافت پاداش</b>\n\nزمان فعلی: <b>{optional_reward_delay_minutes(item)} دقیقه</b>\n\nمدت جدید را به دقیقه ارسال کنید.",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data=f"owner:social_item:{item_id}")]])); return
            if item.get("type") == "optional_ad" and sub == "reward":
                _clear_social_waiting(context)
                context.user_data["social_pending"]={"mode":"edit_reward","field":"optional_ad_reward","item_id":item_id}
                context.user_data[_waiting_scope_key("social_pending")] = int(update.effective_chat.id)
                await query.answer(); await query.edit_message_text(f"☢️ <b>ویرایش پاداش تبلیغ اختیاری</b>\n\nپاداش فعلی: <b>{float(item.get('reward',0) or 0):,.0f}</b> اورانیوم\n\nمقدار جدید را ارسال کنید.",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data=f"owner:social_item:{item_id}")]])); return
            context.user_data["social_pending"]={"mode":"edit_item","field":item.get('type'),"item_id":item_id}
            context.user_data[_waiting_scope_key("social_pending")] = int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text(f"✏️ <b>ویرایش لینک</b>\n\nلینک فعلی: <code>{escape(str(item.get('url') or ''))}</code>\n\nلینک جدید را ارسال کنید. بعد از ارسال، پیش‌نمایش و دکمه تأیید نمایش داده می‌شود و تا آن زمان چیزی ذخیره نمی‌شود.",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data=f"owner:social_item:{item_id}")]])); return

        if action == "social_reward_item" and len(parts) >= 3:
            item_id=parts[2]; item=next((x for x in get_social_items(session,"optional_ad") if str(x.get('id'))==str(item_id)),None)
            if not item: await query.answer("تبلیغ پیدا نشد.",show_alert=True); return
            context.user_data["social_pending"]={"mode":"edit_reward","field":"optional_ad_reward","item_id":item_id}
            context.user_data[_waiting_scope_key("social_pending")] = int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text(f"☢️ <b>ویرایش پاداش این تبلیغ اختیاری</b>\n\nپاداش فعلی: <b>{float(item.get('reward',0) or 0):,.0f}</b> اورانیوم\n\nمقدار جدید را ارسال کنید.",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data=f"owner:social_item:{item_id}")]])); return

        if action == "social_edit_set" and len(parts) >= 4:
            item_id, kind, value = parts[2], parts[3], parts[4] if len(parts) >= 5 else ""
            item=next((x for x in get_social_items(session) if str(x.get("id"))==str(item_id) and x.get("type") in {"optional_ad","mandatory_ad"}),None)
            if not item: await query.answer("تبلیغ پیدا نشد.",show_alert=True); return
            if value != "none": await query.answer("مقدار نامعتبر است.",show_alert=True); return
            if kind == "members":
                item.pop("max_members",None)
                if item.get("limit_type") == "members":
                    item["limit_type"] = "time" if item.get("expires_at") else "none"
            elif kind == "time":
                item.pop("expires_at",None)
                if item.get("limit_type") == "time":
                    item["limit_type"] = "members" if item.get("max_members") else "none"
            else: await query.answer("گزینه نامعتبر است.",show_alert=True); return
            _save_items(session,get_social_items(session)); session.commit()
            context.user_data.pop("social_pending",None)
            await query.answer("✅ محدودیت حذف شد.",show_alert=True)
            # نمایش جزئیات تبلیغ پس از ذخیره
            item=next((x for x in get_social_items(session,"optional_ad") if str(x.get("id"))==str(item_id)),item)
            await query.edit_message_text(text,parse_mode="HTML",reply_markup=owner_social_item_detail_keyboard(item_id,bool(item.get("active",True)),"optional_ad")); return

        if action == "social_edit_confirm" and len(parts) >= 3:
            item_id=parts[2]; pending=context.user_data.get("social_pending") or {}
            if pending.get("item_id") != item_id or pending.get("mode") not in {"edit_item","edit_reward","edit_delay","edit_members","edit_time"}:
                await query.answer("⚠️ ویرایش منقضی شده است.",show_alert=True); return
            item=next((x for x in get_social_items(session) if str(x.get("id"))==str(item_id)),None)
            if not item: await query.answer("مورد پیدا نشد.",show_alert=True); return
            if pending.get("mode")=="edit_reward":
                item["reward"]=max(0.0,float(pending.get("new_reward",0) or 0))
            elif pending.get("mode")=="edit_delay":
                item["reward_delay_minutes"]=max(1, int(pending.get("new_delay_minutes",60) or 60))
            elif pending.get("mode")=="edit_members":
                item["max_members"]=max(1,int(pending.get("new_max_members",1) or 1))
                item["limit_type"]="members"
            elif pending.get("mode")=="edit_time":
                item["expires_at"]=(datetime.now(timezone.utc)+timedelta(minutes=int(pending.get("new_duration_minutes",1) or 1))).isoformat()
                item["limit_type"]="time"
            else:
                item["url"]=str(pending.get("new_url") or "").strip()
                if pending.get("new_chat_id") is not None: item["chat_id"]=int(pending["new_chat_id"])
                if pending.get("new_chat_type"): item["chat_type"]=str(pending["new_chat_type"])
            _save_items(session,get_social_items(session)); session.commit(); context.user_data.pop("social_pending",None)
            await query.answer("✅ تغییرات تأیید و ذخیره شد.",show_alert=True)
            await query.edit_message_text("✅ <b>تغییرات با موفقیت ذخیره شد.</b>",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data=f"owner:social_item:{item_id}")]])); return

        if action == "bank_loan_interval_edit":
            current=get_bank_loan_interval_hours(session)
            context.user_data["economy_pending"]={"building":"bank","type":"bank_loan_interval","back_callback":"owner:installment_settings","current_value":current,"prompt_message_id":int(query.message.message_id),"prompt_chat_id":int(query.message.chat_id)}
            context.user_data[_waiting_scope_key("economy_pending")]=int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text(f"💳 <b>فاصله پرداخت هر قسط</b>\n\nمقدار فعلی: <b>{current:g} ساعت</b>\n\nمدت فاصله بین سررسید هر دو قسط را به ساعت ارسال کنید؛ مثلاً 12 یا 24.",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="owner:installment_settings")]])); return

        if action == "bank_loan_overdue_multiplier_edit":
            current=get_bank_loan_overdue_multiplier(session)
            context.user_data["economy_pending"]={"building":"bank","type":"bank_loan_overdue_multiplier","back_callback":"owner:installment_settings","current_value":current,"prompt_message_id":int(query.message.message_id),"prompt_chat_id":int(query.message.chat_id)}
            context.user_data[_waiting_scope_key("economy_pending")]=int(query.message.chat_id)
            await query.answer(); await query.edit_message_text(f"📈 <b>ضریب افزایش قسط معوق</b>\n\nمقدار فعلی: <b>×{current:g}</b>\n\nمثلاً ×2 یعنی اگر دو سررسید متوالی پرداخت نشوند، هنگام رسیدن سررسید دوم مبلغ آن‌ها 2 برابر قسط اول + قسط دوم خواهد بود.",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="owner:installment_settings")]])); return

        if action == "bank_loan_lock_days_edit":
            current=get_bank_loan_lock_days(session)
            context.user_data["economy_pending"]={"building":"bank","type":"bank_loan_lock_days","back_callback":"owner:installment_settings","current_value":current,"prompt_message_id":int(query.message.message_id),"prompt_chat_id":int(query.message.chat_id)}
            context.user_data[_waiting_scope_key("economy_pending")]=int(query.message.chat_id)
            await query.answer(); await query.edit_message_text(f"🔒 <b>مدت بسته بودن بانک پس از عدم پرداخت</b>\n\nمقدار فعلی: <b>{current:g} روز</b>\n\nتعداد ساعت بسته بودن بانک پس از عدم پرداخت قسط را وارد کنید.",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="owner:installment_settings")]])); return

        if action == "general_settings":
            await query.answer()
            await query.edit_message_text("⚙️ <b>تنظیمات عمومی ربات</b>\n\nیکی از موارد زیر را انتخاب کنید:", parse_mode="HTML", reply_markup=general_settings_keyboard())
            return

        if action == "bot_shutdown":
            mode = get_bot_shutdown_mode(session)
            if len(parts) >= 3:
                requested = parts[2]
                # سه حالت مستقل‌نما: users/admins، و all برای خاموشی هر دو؛ کلیک روی وضعیت فعال آن را روشن می‌کند.
                if requested == "users":
                    mode = {"none":"users", "users":"none", "admins":"all", "all":"admins"}[mode]
                elif requested == "admins":
                    mode = {"none":"admins", "admins":"none", "users":"all", "all":"users"}[mode]
                elif requested == "all":
                    mode = "none" if mode == "all" else "all"
                set_bot_shutdown_mode(session, mode); session.commit()
                msg={"none":"🟢 ربات برای همه روشن است.","users":"👤 ربات برای کاربران عادی خاموش شد.","admins":"🛡️ ربات برای ادمین‌ها خاموش شد.","all":"🔴 ربات برای همه به‌جز Owner خاموش شد."}[mode]
                await query.answer(msg, show_alert=True)
            labels={"none":"👤 کاربران عادی: فعال | 🛡️ ادمین‌ها: فعال | 👥 همه: فعال","users":"👤 کاربران عادی: غیرفعال | 🛡️ ادمین‌ها: فعال | 👥 همه: غیرفعال","admins":"👤 کاربران عادی: فعال | 🛡️ ادمین‌ها: غیرفعال | 👥 همه: غیرفعال","all":"👤 کاربران عادی: غیرفعال | 🛡️ ادمین‌ها: غیرفعال | 👥 همه: غیرفعال"}
            await query.edit_message_text(f"⏻ <b>کنترل دسترسی ربات</b>\n\n{labels[mode]}",parse_mode="HTML",reply_markup=bot_shutdown_keyboard(mode, back_callback="owner:general_settings")); return

        # -------------------------------------------------
        # -------------------------------------------------
        if action == "shields":
            if not owner_user:
                await query.answer("⛔ این بخش فقط برای مالک است.",show_alert=True); return
            await query.answer(); await query.edit_message_text("🛡️ <b>مدیریت سپرها</b>\n\nنوع سپر را انتخاب کنید:",parse_mode="HTML",reply_markup=shield_management_keyboard()); return

        if action == "shield_auto_settings":
            if not owner_user: await query.answer("⛔ این بخش فقط برای مالک است.",show_alert=True); return
            st=get_shield_auto_settings(session); from keyboards.admin import shield_auto_settings_keyboard
            # ورود به این پنل (از جمله دکمه «برگشت») هر waiting قبلی این بخش را لغو می‌کند.
            context.user_data.pop("shield_auto_setting_pending",None); context.user_data.pop(_waiting_scope_key("shield_auto_setting_pending"),None)
            await query.answer(); await query.edit_message_text(f"⚙️ <b>تنظیمات خودکار سپر</b>\n\n🎯 تعداد اتک دریافتی برای سپر خودکار: <b>{st['auto_attack_threshold']}</b>\n🛡️ مدت سپر رایگان: <b>{st['auto_shield_hours']:g} ساعت</b>\n⏳ کسر از سپر هنگام اتک در گروه: <b>{st['shield_attack_penalty_hours']:g} ساعت</b>\n\nهر مقدار را جداگانه انتخاب و تنظیم کنید.",parse_mode="HTML",reply_markup=shield_auto_settings_keyboard()); return

        if action == "shield_auto_setting" and len(parts)>=3:
            if not owner_user: await query.answer("⛔ این بخش فقط برای مالک است.",show_alert=True); return
            field=parts[2]
            if field not in {"auto_attack_threshold","auto_shield_hours","shield_attack_penalty_hours"}: await query.answer("❌ گزینه نامعتبر است.",show_alert=True); return
            labels={"auto_attack_threshold":"تعداد اتک دریافتی","auto_shield_hours":"مدت سپر رایگان (ساعت)","shield_attack_penalty_hours":"کسر از سپر هنگام اتک (ساعت)"}
            context.user_data["shield_auto_setting_pending"]={"field":field}; context.user_data[_waiting_scope_key("shield_auto_setting_pending")]=int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text(f"⚙️ <b>{labels[field]}</b>\n\nمقدار جدید را ارسال کنید:",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="owner:shield_auto_settings")]])); return

        if action == "shield_type" and len(parts)>=3:
            if not owner_user: await query.answer("⛔ این بخش فقط برای مالک است.",show_alert=True); return
            typ=parts[2]
            await query.answer(); await query.edit_message_text(f"🛡️ <b>{'سپرهای جهانی' if typ=='global' else 'سپرهای قاره‌ای'}</b>\n\nعملیات موردنظر را انتخاب کنید:",parse_mode="HTML",reply_markup=shield_type_management_keyboard(typ, is_shield_type_enabled(session, typ))); return

        if action == "shield_type_toggle" and len(parts)>=3:
            if not owner_user: await query.answer("⛔ این بخش فقط برای مالک است.",show_alert=True); return
            typ=parts[2]
            cfg=get_shield_config(session); key=f"{typ}_enabled"; cfg[key]=not bool(cfg.get(key, True)); save_shield_config(session,cfg); session.commit()
            await query.answer("🟢 نوع سپر فعال شد." if cfg[key] else "🔴 نوع سپر غیرفعال شد.", show_alert=True)
            await query.edit_message_text(f"🛡️ <b>{'سپرهای جهانی' if typ=='global' else 'سپرهای قاره‌ای'}</b>\n\nعملیات موردنظر را انتخاب کنید:",parse_mode="HTML",reply_markup=shield_type_management_keyboard(typ, bool(cfg[key]))); return

        if action == "shield_confirm_add":
            if not owner_user:
                await query.answer("⛔ این بخش فقط برای مالک است.", show_alert=True); return
            draft = context.user_data.get("shield_add_pending")
            if not draft or draft.get("stage") != "confirm":
                await query.answer("❌ اطلاعات موقت سپر پیدا نشد یا منقضی شده است.", show_alert=True); return
            typ = draft.get("type"); name = str(draft.get("name") or "").strip()
            price = float(draft.get("price", 0) or 0); duration = float(draft.get("duration_hours", 0) or 0); cooldown = float(draft.get("cooldown_hours", 0) or 0)
            if not name or duration <= 0 or cooldown <= 0 or price < 0:
                await query.answer("❌ اطلاعات سپر کامل نیست.", show_alert=True); return
            cfg = get_shield_config(session); items = cfg.setdefault("items", []); ids = {str(x.get("id")) for x in items}; n = 1
            while f"shield_{typ}_{n}" in ids: n += 1
            items.append({"id":f"shield_{typ}_{n}","name":name,"type":typ,"price":price,"duration_hours":duration,"cooldown_hours":cooldown,"active":True})
            save_shield_config(session, cfg); session.commit(); context.user_data.pop("shield_add_pending", None)
            await query.answer("✅ سپر با موفقیت ذخیره شد.", show_alert=True)
            await query.edit_message_text(f"🛡️ <b>{'سپرهای جهانی' if typ=='global' else 'سپرهای قاره‌ای'}</b>\n\nعملیات موردنظر را انتخاب کنید:", parse_mode="HTML", reply_markup=shield_type_management_keyboard(typ))
            return

        if action == "shield_add" and len(parts)>=3:
            if not owner_user: await query.answer("⛔ این بخش فقط برای مالک است.",show_alert=True); return
            typ=parts[2]; context.user_data['shield_add_pending']={'type':typ,'stage':'name'}
            context.user_data[_waiting_scope_key("shield_add_pending")] = int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text(f"➕ <b>افزودن {'سپر جهانی' if typ=='global' else 'سپر قاره‌ای'}</b>\n\nنام سپر را ارسال کنید:",parse_mode="HTML",reply_markup=shield_add_keyboard(typ)); return

        if action in {"shield_list","shield_delete","shield_toggle_list"} and len(parts)>=3:
            if not owner_user: await query.answer("⛔ این بخش فقط برای مالک است.",show_alert=True); return
            typ=parts[2]; page=int(parts[3] or 1) if len(parts)>=4 else 1; mode={'shield_list':'list','shield_delete':'delete','shield_toggle_list':'toggle'}[action]
            items=get_shield_items(session,typ)
            if not items:
                await query.answer("❌ هیچ سپری وجود ندارد.", show_alert=True)
                return
            title={'list':'📋 لیست','delete':'➖ حذف','toggle':'🟢/🔴 فعال یا غیرفعال کردن'}[mode]
            await query.answer(); await query.edit_message_text(f"🛡️ <b>{title} — {'سپرهای جهانی' if typ=='global' else 'سپرهای قاره‌ای'}</b>\n\nیک سپر را انتخاب کنید:",parse_mode="HTML",reply_markup=shield_item_list_keyboard(items,typ,page,mode)); return

        if action == "shield_item" and len(parts)>=4:
            if not owner_user: await query.answer("⛔ این بخش فقط برای مالک است.",show_alert=True); return
            typ,item_id=parts[2],parts[3]; item=get_shield_item_by_id(session,item_id)
            if not item: await query.answer("❌ سپر پیدا نشد.",show_alert=True); return
            text=(f"🛡️ <b>{escape(str(item.get('name','سپر')))}</b>\n\n📌 نوع: <b>{'جهانی' if typ=='global' else 'قاره‌ای'}</b>\n📌 وضعیت: <b>{'فعال' if item.get('active') else 'غیرفعال'}</b>\n☢️ قیمت: <b>{float(item.get('price',0) or 0):,.0f} اورانیوم</b>\n⏱ مدت اعتبار: <b>{float(item.get('duration_hours',0) or 0):g} ساعت</b>\n🔁 فاصله خرید مجدد: <b>{float(item.get('cooldown_hours',0) or 0):g} ساعت</b>")
            await query.answer(); await query.edit_message_text(text,parse_mode="HTML",reply_markup=shield_item_detail_keyboard(typ,item_id,bool(item.get('active')))); return

        if action == "shield_toggle_item" and len(parts)>=4:
            if not owner_user: await query.answer("⛔ این بخش فقط برای مالک است.",show_alert=True); return
            typ,item_id=parts[2],parts[3]; cfg=get_shield_config(session); item=next((x for x in cfg.get('items',[]) if str(x.get('id'))==str(item_id)),None)
            if not item: await query.answer("❌ سپر پیدا نشد.",show_alert=True); return
            item['active']=not bool(item.get('active')); save_shield_config(session,cfg); session.commit()
            await query.answer("🟢 سپر فعال شد." if item['active'] else "🔴 سپر غیرفعال شد.",show_alert=True)
            await query.edit_message_text(f"🛡️ <b>{escape(str(item.get('name','سپر')))}</b>\n\n📌 وضعیت: <b>{'فعال' if item.get('active') else 'غیرفعال'}</b>\n☢️ قیمت: <b>{float(item.get('price',0) or 0):,.0f} اورانیوم</b>\n⏱ مدت اعتبار: <b>{float(item.get('duration_hours',0) or 0):g} ساعت</b>\n🔁 فاصله خرید مجدد: <b>{float(item.get('cooldown_hours',0) or 0):g} ساعت</b>",parse_mode="HTML",reply_markup=shield_item_detail_keyboard(typ,item_id,bool(item.get('active')))); return

        if action == "shield_delete_item" and len(parts)>=4:
            if not owner_user: await query.answer("⛔ این بخش فقط برای مالک است.",show_alert=True); return
            typ,item_id=parts[2],parts[3]; item=get_shield_item_by_id(session,item_id)
            if not item:
                await query.answer("❌ سپر پیدا نشد.",show_alert=True); return
            await query.answer()
            await query.edit_message_text(
                f"⚠️ <b>تأیید حذف سپر</b>\n\nآیا از حذف سپر «{escape(str(item.get('name','سپر')))}» مطمئن هستید؟\n\n☢️ قیمت: <b>{float(item.get('price',0) or 0):,.0f} اورانیوم</b>\n⏱ مدت فعال بودن: <b>{float(item.get('duration_hours',0) or 0):g} ساعت</b>\n🔁 فاصله خرید: <b>{float(item.get('cooldown_hours',0) or 0):g} ساعت</b>",
                parse_mode="HTML", reply_markup=shield_delete_confirm_keyboard(typ,item_id))
            return

        if action == "shield_delete_confirm" and len(parts)>=4:
            if not owner_user: await query.answer("⛔ این بخش فقط برای مالک است.",show_alert=True); return
            typ,item_id=parts[2],parts[3]; cfg=get_shield_config(session); before=len(cfg.get('items',[])); item=next((x for x in cfg.get('items',[]) if str(x.get('id'))==str(item_id)),None)
            if not item:
                await query.answer("❌ سپر پیدا نشد.",show_alert=True); return
            cfg['items']=[x for x in cfg.get('items',[]) if str(x.get('id'))!=str(item_id)]
            save_shield_config(session,cfg); session.commit()
            await query.answer("🗑️ سپر با موفقیت حذف شد.",show_alert=True)
            await query.edit_message_text(f"🛡️ <b>{'سپرهای جهانی' if typ=='global' else 'سپرهای قاره‌ای'}</b>\n\nعملیات موردنظر را انتخاب کنید:",parse_mode="HTML",reply_markup=shield_type_management_keyboard(typ)); return

        if action == "shield_edit" and len(parts)>=4:
            if not owner_user: await query.answer("⛔ این بخش فقط برای مالک است.",show_alert=True); return
            typ,item_id=parts[2],parts[3]; item=get_shield_item_by_id(session,item_id)
            if not item:
                await query.answer("❌ سپر پیدا نشد.",show_alert=True); return
            await query.answer(); await query.edit_message_text(
                f"✏️ <b>ویرایش سپر</b>\n\n🏷 نام: <b>{escape(str(item.get('name','سپر')))}</b>\n☢️ قیمت: <b>{float(item.get('price',0) or 0):,.0f} اورانیوم</b>\n⏱ مدت فعال بودن: <b>{float(item.get('duration_hours',0) or 0):g} ساعت</b>\n🔁 فاصله خرید: <b>{float(item.get('cooldown_hours',0) or 0):g} ساعت</b>\n\nموردی را که می‌خواهید تغییر دهید انتخاب کنید:", parse_mode="HTML", reply_markup=shield_edit_keyboard(typ,item_id)); return

        if action == "shield_edit_field" and len(parts)>=5:
            if not owner_user: await query.answer("⛔ این بخش فقط برای مالک است.",show_alert=True); return
            typ,item_id,field=parts[2],parts[3],parts[4]; item=get_shield_item_by_id(session,item_id)
            if not item or field not in {"name","price","duration","cooldown"}:
                await query.answer("❌ اطلاعات ویرایش نامعتبر است.",show_alert=True); return
            labels={"name":"نام سپر","price":"قیمت سپر (اورانیوم)","duration":"مدت فعال بودن (ساعت)","cooldown":"مدت زمان بین خرید (ساعت)"}
            context.user_data['shield_edit_pending']={'type':typ,'item_id':item_id,'field':field,'stage':'value'}
            context.user_data[_waiting_scope_key('shield_edit_pending')] = int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text(f"✏️ <b>{labels[field]}</b>\n\nمقدار جدید را ارسال کنید:",parse_mode="HTML",reply_markup=shield_add_keyboard(typ)); return

        if action == "shield_edit_cancel" and len(parts)>=4:
            context.user_data.pop('shield_edit_pending',None); context.user_data.pop(_waiting_scope_key('shield_edit_pending'),None)
            typ,item_id=parts[2],parts[3]; item=get_shield_item_by_id(session,item_id)
            if not item: await query.answer("❌ سپر پیدا نشد.",show_alert=True); return
            await query.answer(); await query.edit_message_text(f"🛡️ <b>{escape(str(item.get('name','سپر')))}</b>",parse_mode="HTML",reply_markup=shield_item_detail_keyboard(typ,item_id,bool(item.get('active')))); return

        # -------------------------------------------------
        # اقتصاد Owner
        # -------------------------------------------------
        if action == "game_management":
            await query.answer()
            from keyboards.admin import game_management_keyboard
            await query.edit_message_text("🧩 <b>مدیریت بازی</b>\n\nبخش موردنظر را انتخاب کنید:", parse_mode="HTML", reply_markup=game_management_keyboard())
            return

        if action == "buildings":
            await query.answer()
            await query.edit_message_text(
                "🏗️ <b>مدیریت ساختمان‌ها</b>\n\nساختمان موردنظر را انتخاب کنید:",
                parse_mode="HTML",
                reply_markup=building_management_keyboard(),
            )
            return

        if action == "economy":
            if not is_owner(query.from_user.id, OWNER_ID):
                await query.answer("⛔ این بخش فقط برای مالک است.", show_alert=True); return
            await query.answer()
            await query.edit_message_text("🎮 <b>تنظیمات بازی</b>\n\nبخش موردنظر را انتخاب کنید:", parse_mode="HTML", reply_markup=economy_keyboard())
            return

        if action == "leadership_settings":
            if not is_owner(query.from_user.id, OWNER_ID):
                await query.answer("⛔ این بخش فقط برای مالک است.", show_alert=True); return
            gb=get_group_base(session); gl=get_global_base(session); rh=get_repeat_reset_hours(session)
            rows=[
                [InlineKeyboardButton(f"⚔️ تجربه رهبری قاره‌ای: {gb:g}", callback_data="owner:leadership_edit:group"),
                 InlineKeyboardButton(f"🌐 تجربه رهبری جهانی: {gl:g}", callback_data="owner:leadership_edit:global")],
                [InlineKeyboardButton(f"⏱️ ریست حمله‌های تکراری: {rh:g} ساعت", callback_data="owner:leadership_edit:reset")],
                [InlineKeyboardButton("🔙 برگشت", callback_data="owner:initial_settings")],
            ]
            await query.answer(); await query.edit_message_text("👑 <b>تنظیم تجربه رهبری</b>\n\nمقادیر سیستم تجربه رهبری را تنظیم کنید:",parse_mode="HTML",reply_markup=InlineKeyboardMarkup(rows)); return

        if action == "leadership_edit" and len(parts)>=3:
            field=parts[2]
            if field not in {"group","global","reset"}:
                await query.answer("❌ گزینه نامعتبر است.",show_alert=True); return
            labels={"group":"⚔️ تجربه رهبری پایه قاره‌ای","global":"🌐 تجربه رهبری پایه جهانی","reset":"⏱️ زمان ریست حمله‌های تکراری (ساعت)"}
            vals={"group":get_group_base(session),"global":get_global_base(session),"reset":get_repeat_reset_hours(session)}
            context.user_data["economy_pending"]={"building":"leadership","type":field,"back_callback":"owner:leadership_settings","current_value":vals[field],"prompt_message_id":int(query.message.message_id),"prompt_chat_id":int(query.message.chat_id)}
            context.user_data[_waiting_scope_key("economy_pending")] = int(update.effective_chat.id)
            context.user_data["owner_economy_confirm"] = dict(context.user_data["economy_pending"])
            context.user_data[_waiting_scope_key("owner_economy_confirm")] = int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text(f"{labels[field]}\n\nمقدار فعلی: <b>{vals[field]:g}</b>\n\nمقدار جدید را ارسال کنید.",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="owner:leadership_settings")]])); return

        if action == "swap_cooldown":
            value = get_swap_cooldown_hours(session)
            context.user_data["economy_pending"]={"building":"settings","type":"swap_cooldown","back_callback":"owner:initial_settings","current_value":value,"prompt_message_id":int(query.message.message_id),"prompt_chat_id":int(query.message.chat_id)}
            context.user_data[_waiting_scope_key("economy_pending")] = int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text(f"⏱️ <b>محدودیت جابه‌جایی</b>\n\nمقدار فعلی: <b>{value:g} ساعت</b>\n\nعدد جدید را بر حسب ساعت ارسال کنید.", parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data="owner:initial_settings")]])); return

        if action == "country_rename_cost":
            money=get_country_rename_money_cost(session); uranium=get_country_establishment_uranium_cost(session)
            me=get_country_rename_money_enabled(session); ue=get_country_rename_uranium_enabled(session)
            rows=[
                [InlineKeyboardButton(f"{'🟢' if me else '🔴'} پول: {money:,.0f}",callback_data="owner:country_rename_toggle:money"),
                 InlineKeyboardButton(f"{'🟢' if ue else '🔴'} اورانیوم: {uranium:,.2f}",callback_data="owner:country_rename_toggle:uranium")],
                [InlineKeyboardButton("💰 تنظیم هزینه پول",callback_data="owner:country_rename_cost_edit:money"),
                 InlineKeyboardButton("☢️ تنظیم هزینه اورانیوم",callback_data="owner:country_rename_cost_edit:uranium")],
                [InlineKeyboardButton("🔙 برگشت",callback_data="owner:initial_settings")]]
            await query.answer(); await query.edit_message_text(f"💳 <b>هزینه تغییر نام</b>\n\n💰 پول: <b>{money:,.2f}</b> — وضعیت: <b>{'فعال' if me else 'غیرفعال'}</b>\n☢️ اورانیوم: <b>{uranium:,.2f}</b> — وضعیت: <b>{'فعال' if ue else 'غیرفعال'}</b>\n\nروش پرداخت موردنظر را انتخاب کنید.",parse_mode="HTML",reply_markup=InlineKeyboardMarkup(rows)); return
        if action == "country_rename_toggle" and len(parts)>=3:
            field=parts[2]
            if field=="money": set_country_rename_money_enabled(session, not get_country_rename_money_enabled(session))
            elif field=="uranium": set_country_rename_uranium_enabled(session, not get_country_rename_uranium_enabled(session))
            else: await query.answer("❌ گزینه نامعتبر است.",show_alert=True); return
            session.commit()
            status = "فعال" if ((get_country_rename_money_enabled(session) if field == "money" else get_country_rename_uranium_enabled(session))) else "غیرفعال"
            await query.answer(f"{'💰 پول' if field == 'money' else '☢️ اورانیوم'} {status} شد.", show_alert=True)
            money=get_country_rename_money_cost(session); uranium=get_country_establishment_uranium_cost(session)
            me=get_country_rename_money_enabled(session); ue=get_country_rename_uranium_enabled(session)
            rows=[[InlineKeyboardButton(f"{'🟢' if me else '🔴'} پول: {money:,.2f}",callback_data="owner:country_rename_toggle:money")],[InlineKeyboardButton(f"{'🟢' if ue else '🔴'} اورانیوم: {uranium:,.2f}",callback_data="owner:country_rename_toggle:uranium")],[InlineKeyboardButton("💰 تنظیم هزینه پول",callback_data="owner:country_rename_cost_edit:money")],[InlineKeyboardButton("☢️ تنظیم هزینه اورانیوم",callback_data="owner:country_rename_cost_edit:uranium")],[InlineKeyboardButton("🔙 برگشت",callback_data="owner:initial_settings")]]
            await query.edit_message_text(f"💳 <b>هزینه تغییر نام</b>\n\n💰 پول: <b>{money:,.2f}</b> — وضعیت: <b>{'فعال' if me else 'غیرفعال'}</b>\n☢️ اورانیوم: <b>{uranium:,.2f}</b> — وضعیت: <b>{'فعال' if ue else 'غیرفعال'}</b>\n\nروش پرداخت موردنظر را انتخاب کنید.",parse_mode="HTML",reply_markup=InlineKeyboardMarkup(rows)); return
        if action == "country_rename_cost_edit" and len(parts)>=3:
            field=parts[2]
            if field not in {"money","uranium"}: await query.answer("❌ گزینه نامعتبر است.",show_alert=True); return
            if field=="uranium":
                value=get_country_establishment_uranium_cost(session); ptype="country_rename_uranium"
            else:
                value=get_country_rename_money_cost(session); ptype="country_rename_money"
            context.user_data["economy_pending"]={"building":"settings","type":ptype,"back_callback":"owner:country_rename_cost","current_value":value}
            context.user_data[_waiting_scope_key("economy_pending")] = int(update.effective_chat.id)
            label="☢️ اورانیوم" if field=="uranium" else "💰 پول"
            await query.answer(); await query.edit_message_text(f"💳 <b>هزینه تغییر نام با {label}</b>\n\nمقدار فعلی: <b>{value:,.0f}</b>\n\nمقدار جدید را ارسال کنید.",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="owner:country_rename_cost")]])); return

        if action == "construction_teams":
            cfg=get_construction_teams_config(session)
            text=(f"🏗️ <b>مدیریت تیم‌های ساخت‌وساز</b>\n\nحداکثر فعلی: <b>{int(cfg.get('max_teams',10))}</b> از ۱۰\nتیم ۱ همیشه رایگان است. قیمت تیم‌های ۲ تا ۱۰ جداگانه تنظیم می‌شود.")
            from keyboards.admin import construction_teams_owner_keyboard
            await query.answer(); await query.edit_message_text(text,parse_mode="HTML",reply_markup=construction_teams_owner_keyboard(cfg)); return
        if action == "construction_team_max":
            cfg=get_construction_teams_config(session); cur=int(cfg.get("max_teams",10) or 10)
            context.user_data["economy_pending"]={"building":"construction_teams","type":"max","back_callback":"owner:construction_teams","current_value":cur,"prompt_message_id":int(query.message.message_id),"prompt_chat_id":int(query.message.chat_id)}
            context.user_data[_waiting_scope_key("economy_pending")]=int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text(f"⚙️ <b>حداکثر تیم‌های ساخت‌وساز</b>\n\nمقدار فعلی: <b>{cur}</b>\n\nعدد بین ۱ تا ۱۰ ارسال کنید.",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="owner:construction_teams")]])); return
        if action == "construction_team_prices":
            cfg=get_construction_teams_config(session)
            from keyboards.admin import construction_team_prices_keyboard
            await query.answer(); await query.edit_message_text("💰 <b>مدیریت قیمت تیم‌های ساخت‌وساز</b>\n\nتیم ۱ رایگان و غیرقابل تغییر است.",parse_mode="HTML",reply_markup=construction_team_prices_keyboard(cfg)); return
        if action == "construction_team_price" and len(parts)>=3:
            team=int(parts[2])
            if team<2 or team>10: await query.answer("❌ شماره تیم نامعتبر است.",show_alert=True); return
            cfg=get_construction_teams_config(session); cur=float(cfg.get("prices",{}).get(str(team),0) or 0)
            context.user_data["economy_pending"]={"building":"construction_teams","type":"price","team":team,"back_callback":"owner:construction_team_prices","current_value":cur,"prompt_message_id":int(query.message.message_id),"prompt_chat_id":int(query.message.chat_id)}
            context.user_data[_waiting_scope_key("economy_pending")]=int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text(f"💰 <b>قیمت تیم {team}</b>\n\nقیمت فعلی: <b>{cur:,.0f}</b>\n\nقیمت جدید را ارسال کنید.",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="owner:construction_team_prices")]])); return
        if action == "initial_settings":
            await query.answer(); await query.edit_message_text("⚙️ <b>تنظیمات اولیه</b>\n\nمنابع اولیه، تجربه رهبری و تنظیمات اولیه کشور را از این بخش مدیریت کنید:",parse_mode="HTML",reply_markup=initial_settings_keyboard()); return

        if action == "installment_settings":
            await query.answer()
            await query.edit_message_text(
                f"💳 <b>تنظیمات قسط</b>\n\n💳 فاصله پرداخت هر قسط: <b>{get_bank_loan_interval_hours(session):g} ساعت</b>\n🔒 مدت بسته بودن بانک پس از عدم پرداخت: <b>{get_bank_loan_lock_days(session):g} ساعت</b>\n📈 ضریب افزایش قسط معوق: <b>×{get_bank_loan_overdue_multiplier(session):g}</b>\nتنظیم موردنظر را انتخاب کنید:",
                parse_mode="HTML", reply_markup=installment_settings_keyboard(get_bank_loan_interval_hours(session), "09:00", get_bank_loan_lock_days(session), get_bank_loan_overdue_multiplier(session))
            ); return

        if action == "initial_population":
            cfg=get_bank_config(session); current=int(cfg.get("population_initial",0) or 0)
            context.user_data["economy_pending"]={"building":"bank","type":"population_initial","back_callback":"owner:initial_settings","current_value":current,"prompt_message_id":int(query.message.message_id),"prompt_chat_id":int(query.message.chat_id)}
            context.user_data[_waiting_scope_key("economy_pending")]=int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text(f"👥 <b>جمعیت اولیه</b>\n\nمقدار فعلی: <b>{current:,}</b> شهروند\n\nتعداد جمعیت اولیه هر کشور جدید را ارسال کنید.",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="owner:initial_settings")]])); return

        if action == "initial_resources":
            cfg=get_initial_resources(session)
            await query.answer(); await query.edit_message_text(
                "🎁 <b>منابع اولیه</b>\n\n" +
                f"💰 پول: <b>{cfg['money']:,.2f}</b>\n🔩 فلز: <b>{cfg['metal']:,.2f}</b>\n⛽ سوخت: <b>{cfg['fuel']:,.2f}</b>\n☢️ اورانیوم: <b>{cfg['uranium']:,.2f}</b>\n\nمنبع موردنظر را انتخاب کنید:",
                parse_mode="HTML", reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💰 پول",callback_data="owner:initial_edit:money"), InlineKeyboardButton("🔩 فلز",callback_data="owner:initial_edit:metal")],
                    [InlineKeyboardButton("⛽ سوخت",callback_data="owner:initial_edit:fuel"), InlineKeyboardButton("☢️ اورانیوم",callback_data="owner:initial_edit:uranium")],
                    [InlineKeyboardButton("🔙 برگشت",callback_data="owner:initial_settings")]])); return

        if action == "initial_edit" and len(parts)>=3:
            field=parts[2]
            if field not in {"money","metal","fuel","uranium"}: await query.answer("❌ گزینه نامعتبر است.",show_alert=True); return
            cfg = get_initial_resources(session)
            current = float(cfg.get(field, 0) or 0)
            context.user_data["economy_pending"]={"building":"initial","type":"resource","field":field,"back_callback":"owner:initial_settings","current_value":current}
            context.user_data[_waiting_scope_key("economy_pending")] = int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text(
                f"✏️ <b>تغییر مقدار {field}</b>\n\nمقدار فعلی: <b>{current:,.2f}</b>\n\nمقدار جدید را ارسال کنید.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="owner:initial_settings")]])); return

        if action == "missiles":
            if not is_owner(query.from_user.id, OWNER_ID):
                await query.answer("⛔ این بخش فقط برای مالک است.", show_alert=True); return
            cfg=get_missiles_config(session); items=cfg.get("items",[])
            await query.answer(); await query.edit_message_text("🚀 <b>مدیریت موشک‌ها</b>\n\nبخش موردنظر را انتخاب کنید:",parse_mode="HTML",reply_markup=missile_management_keyboard(items)); return

        if action == "missile_list":
            cfg=get_missiles_config(session); items=cfg.get("items",[])
            if not items:
                await query.answer("🚫 موشکی موجود نیست.",show_alert=True); return
            await query.answer(); await query.edit_message_text("📋 <b>لیست موشک‌ها</b>\n\nنوع موشک را انتخاب کنید:",parse_mode="HTML",reply_markup=missile_category_keyboard()); return

        if action == "missile_list_type" and len(parts)>=3:
            typ=parts[2]; items=[m for m in get_missiles_config(session).get("items",[]) if m.get("type")==typ]
            if not items:
                await query.answer(f"🚫 موشک {typ} موجود نیست.",show_alert=True); return
            await query.answer(); await query.edit_message_text(f"🚀 <b>موشک‌های {typ}</b>\n\nموشک موردنظر را انتخاب کنید:",parse_mode="HTML",reply_markup=missile_items_keyboard(items,"owner:missile_list")); return

        if action == "missile_add":
            context.user_data.pop("missile_draft",None)
            await query.answer(); await query.edit_message_text("➕ <b>افزودن موشک</b>\n\nچه نوع موشکی می‌خواهید اضافه کنید؟",parse_mode="HTML",reply_markup=missile_create_type_keyboard()); return

        if action in {"missile_add_type", "missile_create_type"} and len(parts)>=3:
            typ=parts[2]
            context.user_data["missile_pending"]={"step":"name","type":typ}
            context.user_data[_waiting_scope_key("missile_pending")] = int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text(f"➕ <b>افزودن موشک {typ}</b>\n\nنام موشک را ارسال کنید.",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="owner:missile_add")]])); return

        if action == "missile_name_confirm":
            pending=context.user_data.get("missile_pending") or {}
            name=str(pending.get("name","")).strip(); typ=pending.get("type","کروز")
            if not name:
                await query.answer("❌ نام موشک وارد نشده است.",show_alert=True); return
            cfg=get_missiles_config(session); new_id=max([int(x.get("id",0)) for x in cfg.get("items",[]) if str(x.get("id","")).isdigit()] or [0])+1
            m={"id":new_id,"name":name,"type":typ,"active":False,"max_level":100,"hq_required":1,"arsenal_required":1,"base_cost":0.0,"base_power":0.0,"base_capacity":0.0,"base_target_time":0.0,"operational_names":[],"levels":{str(i):{"hq_required":1,"arsenal_required":1,"cost":0.0,"power":0.0,"target_time":0.0} for i in range(1,101)}}
            cfg.setdefault("items",[]).append(m); save_missiles_config(session,cfg); session.commit(); context.user_data.pop("missile_pending",None)
            await query.answer("✅ موشک ثبت شد و به‌صورت پیش‌فرض غیرفعال است.",show_alert=True)
            await query.edit_message_text("📋 <b>موشک‌های ثبت‌شده</b>\n\nموشک موردنظر را انتخاب کنید:",parse_mode="HTML",reply_markup=missile_items_keyboard([x for x in cfg.get("items",[]) if x.get("type")==typ],"owner:missile_list")); return
        if action == "missile_name_edit":
            pending=context.user_data.get("missile_pending") or {}
            pending["step"]="name"; context.user_data["missile_pending"]=pending
            context.user_data[_waiting_scope_key("missile_pending")] = int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text("✏️ نام جدید موشک را ارسال کنید.",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="owner:missile_add")]])); return

        if action == "missile" and len(parts)>=3:
            mid=str(parts[2]); cfg=get_missiles_config(session); m=next((x for x in cfg.get("items",[]) if str(x.get("id"))==mid),None)
            if not m: await query.answer("❌ موشک پیدا نشد.",show_alert=True); return
            ops=m.get("operational_names",[]) or []
            ops_text="، ".join(str(x) for x in ops) if ops else "ثبت نشده"
            text=(f"<b>{m.get('name','موشک')}</b>\n\n🏷 نوع: <b>{m.get('type','نامشخص')}</b>\n🏷️ نام‌های عملیاتی: <b>{escape(ops_text)}</b>\n📦 ظرفیت اشغال کلی: <b>{float(m.get('base_capacity',0) or 0):,.0f}</b>\n🔝 حداکثر سطح: <b>{int(m.get('max_level',100))}</b>\n📌 وضعیت: <b>{'فعال' if m.get('active',False) else 'غیرفعال'}</b>")
            await query.answer(); await query.edit_message_text(text,parse_mode="HTML",reply_markup=missile_edit_keyboard(mid, f"owner:missile_list_type:{m.get('type','کروز')}", bool(m.get('active',False))) ); return

        if action == "missile_operational" and len(parts)>=3:
            mid=str(parts[2]); cfg=get_missiles_config(session); m=next((x for x in cfg.get("items",[]) if str(x.get("id"))==mid),None)
            if not m: await query.answer("❌ موشک پیدا نشد.",show_alert=True); return
            names=m.setdefault("operational_names",[]) or []
            await query.answer(); await query.edit_message_text(
                f"🏷️ <b>نام‌های عملیاتی موشک {escape(str(m.get('name','موشک')))}</b>\n\nتعداد نام‌های ثبت‌شده: <b>{len(names)}</b>",
                parse_mode="HTML", reply_markup=missile_operational_keyboard(mid)); return

        if action == "missile_operational_add" and len(parts)>=3:
            mid=str(parts[2]); cfg=get_missiles_config(session); m=next((x for x in cfg.get("items",[]) if str(x.get("id"))==mid),None)
            if not m: await query.answer("❌ موشک پیدا نشد.",show_alert=True); return
            context.user_data["missile_operational_pending"]={"id":mid,"prompt_chat_id":int(query.message.chat_id),"prompt_message_id":int(query.message.message_id)}
            context.user_data[_waiting_scope_key("missile_operational_pending")] = int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text(
                "➕ <b>افزودن نام عملیاتی</b>\n\nنام عملیاتی موردنظر را ارسال کنید.",
                parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data=f"owner:missile_operational:{mid}")]])); return

        if action == "missile_operational_delete" and len(parts)>=3:
            mid=str(parts[2]); cfg=get_missiles_config(session); m=next((x for x in cfg.get("items",[]) if str(x.get("id"))==mid),None)
            if not m: await query.answer("❌ موشک پیدا نشد.",show_alert=True); return
            names=m.get("operational_names",[]) or []
            if not names: await query.answer("ℹ️ نام عملیاتی ثبت نشده است.",show_alert=True); return
            await query.answer(); await query.edit_message_text("🗑️ <b>حذف نام عملیاتی</b>\n\nنام موردنظر را انتخاب کنید:",parse_mode="HTML",reply_markup=missile_operational_delete_keyboard(mid,names)); return

        if action == "missile_operational_list" and len(parts)>=3:
            mid=str(parts[2]); cfg=get_missiles_config(session); m=next((x for x in cfg.get("items",[]) if str(x.get("id"))==mid),None)
            if not m: await query.answer("❌ موشک پیدا نشد.",show_alert=True); return
            names=m.get("operational_names",[]) or []
            if not names: await query.answer("ℹ️ نام عملیاتی ثبت نشده است.",show_alert=True); return
            text="📋 <b>لیست نام‌های عملیاتی</b>\n\n" + "\n".join(f"{i}. {escape(str(n))}" for i,n in enumerate(names,1))
            await query.answer(); await query.edit_message_text(text,parse_mode="HTML",reply_markup=missile_operational_list_keyboard(mid,names)); return

        if action == "missile_operational_item" and len(parts)>=4:
            mid=str(parts[2]); idx=int(parts[3]); cfg=get_missiles_config(session); m=next((x for x in cfg.get("items",[]) if str(x.get("id"))==mid),None)
            if not m: await query.answer("❌ موشک پیدا نشد.",show_alert=True); return
            names=m.get("operational_names",[]) or []
            if idx < 0 or idx >= len(names): await query.answer("❌ نام عملیاتی پیدا نشد.",show_alert=True); return
            name=str(names[idx])
            await query.answer(); await query.edit_message_text(
                f"🏷️ <b>نام عملیاتی</b>\n\n🚀 موشک: <b>{escape(str(m.get('name','موشک')))}</b>\n📝 نام: <b>{escape(name)}</b>",
                parse_mode="HTML", reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✏️ ویرایش",callback_data=f"owner:missile_operational_edit:{mid}:{idx}") , InlineKeyboardButton("🗑️ حذف",callback_data=f"owner:missile_operational_del:{mid}:{idx}")],
                    [InlineKeyboardButton("🔙 برگشت",callback_data=f"owner:missile_operational_list:{mid}")],
                ])
            ); return

        if action == "missile_operational_del" and len(parts)>=4:
            mid=str(parts[2]); idx=int(parts[3]); cfg=get_missiles_config(session); m=next((x for x in cfg.get("items",[]) if str(x.get("id"))==mid),None)
            if not m: await query.answer("❌ موشک پیدا نشد.",show_alert=True); return
            names=m.get("operational_names",[]) or []
            if idx < 0 or idx >= len(names): await query.answer("❌ نام عملیاتی پیدا نشد.",show_alert=True); return
            await query.answer(); await query.edit_message_text(
                f"⚠️ <b>تأیید حذف نام عملیاتی</b>\n\nنام: <b>{escape(str(names[idx]))}</b>\n\nآیا حذف شود؟",
                parse_mode="HTML", reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ تأیید حذف",callback_data=f"owner:missile_operational_delete_confirm:{mid}:{idx}")],
                    [InlineKeyboardButton("🔙 برگشت",callback_data=f"owner:missile_operational_item:{mid}:{idx}")],
                ])
            ); return

        if action == "missile_operational_delete_confirm" and len(parts)>=4:
            mid=str(parts[2]); idx=int(parts[3]); cfg=get_missiles_config(session); m=next((x for x in cfg.get("items",[]) if str(x.get("id"))==mid),None)
            if not m: await query.answer("❌ موشک پیدا نشد.",show_alert=True); return
            names=m.get("operational_names",[]) or []
            if idx < 0 or idx >= len(names): await query.answer("❌ نام عملیاتی پیدا نشد.",show_alert=True); return
            removed=names.pop(idx); m["operational_names"]=names; save_missiles_config(session,cfg); session.commit()
            await query.answer("✅ نام عملیاتی حذف شد.",show_alert=True)
            if names:
                text="📋 <b>لیست نام‌های عملیاتی</b>\n\n" + "\n".join(f"{i}. {escape(str(n))}" for i,n in enumerate(names,1))
                await query.edit_message_text(text,parse_mode="HTML",reply_markup=missile_operational_list_keyboard(mid,names))
            else:
                await query.edit_message_text("🏷️ <b>نام‌های عملیاتی</b>\n\nنام عملیاتی دیگری ثبت نشده است.",parse_mode="HTML",reply_markup=missile_operational_keyboard(mid))
            return

        if action == "missile_operational_edit" and len(parts)>=4:
            mid=str(parts[2]); idx=int(parts[3]); cfg=get_missiles_config(session); m=next((x for x in cfg.get("items",[]) if str(x.get("id"))==mid),None)
            if not m: await query.answer("❌ موشک پیدا نشد.",show_alert=True); return
            names=m.get("operational_names",[]) or []
            if idx < 0 or idx >= len(names): await query.answer("❌ نام عملیاتی پیدا نشد.",show_alert=True); return
            context.user_data["missile_operational_pending"]={"id":mid,"index":idx,"edit":True,"prompt_chat_id":int(query.message.chat_id),"prompt_message_id":int(query.message.message_id)}
            context.user_data[_waiting_scope_key("missile_operational_pending")]=int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text(
                f"✏️ <b>ویرایش نام عملیاتی</b>\n\nنام فعلی: <b>{escape(str(names[idx]))}</b>\n\nنام جدید را ارسال کنید.",
                parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data=f"owner:missile_operational_item:{mid}:{idx}")]])
            ); return

        if action == "missile_operational_noop":
            await query.answer(); return

        if action == "missile_delete" and len(parts)>=3:
            mid=str(parts[2]); cfg=get_missiles_config(session); m=next((x for x in cfg.get("items",[]) if str(x.get("id"))==mid),None)
            if not m:
                await query.answer("❌ موشک پیدا نشد.",show_alert=True); return
            await query.answer(); await query.edit_message_text(f"⚠️ <b>حذف موشک</b>\n\nآیا از حذف «{m.get('name','موشک')}» مطمئن هستید؟",parse_mode="HTML",reply_markup=missile_delete_confirm_keyboard(mid)); return

        if action == "missile_delete_confirm" and len(parts)>=3:
            mid=str(parts[2]); cfg=get_missiles_config(session); old=len(cfg.get("items",[])); cfg["items"]=[x for x in cfg.get("items",[]) if str(x.get("id"))!=mid]
            if len(cfg["items"])==old:
                await query.answer("❌ موشک پیدا نشد.",show_alert=True); return
            save_missiles_config(session,cfg); session.commit(); await query.answer("✅ موشک حذف شد.",show_alert=True)
            await query.edit_message_text("🚀 <b>مدیریت موشک‌ها</b>\n\nبخش موردنظر را انتخاب کنید:",parse_mode="HTML",reply_markup=missile_management_keyboard(cfg.get("items",[]))); return

        if action == "global_loot_percent":
            value = get_global_loot_percent(session)
            await query.answer()
            await query.edit_message_text(f"💰 <b>درصد غارت منابع کلی</b>\n\nمقدار فعلی: <b>{value:g}%</b>\n\nاین درصد برای <b>تمام موشک‌ها و تمام سطوح</b> اعمال می‌شود.", parse_mode="HTML", reply_markup=missile_global_loot_percent_keyboard())
            return

        if action == "global_loot_percent_custom":
            context.user_data["global_loot_percent_pending"] = True
            context.user_data[_waiting_scope_key("global_loot_percent_pending")] = int(update.effective_chat.id)
            await query.answer()
            await query.edit_message_text("💰 <b>تنظیم دلخواه درصد غارت منابع کلی</b>\n\nدرصد موردنظر را ارسال کنید:", parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data="owner:global_loot_percent")]]))
            return

        if action == "global_loot_percent_set" and len(parts) >= 3:
            try:
                value = max(0.0, min(100.0, float(parts[2])))
            except ValueError:
                await query.answer("❌ مقدار نامعتبر است.", show_alert=True); return
            set_global_loot_percent(session, value); session.commit()
            await query.answer(f"✅ درصد غارت کلی روی {value:g}% تنظیم شد.", show_alert=True)
            await query.edit_message_text(f"💰 <b>درصد غارت منابع کلی</b>\n\nمقدار فعلی: <b>{value:g}%</b>\n\nاین درصد برای <b>تمام موشک‌ها و تمام سطوح</b> اعمال می‌شود.", parse_mode="HTML", reply_markup=missile_global_loot_percent_keyboard())
            return

        if action == "missile_levels" and len(parts)>=3:
            mid=str(parts[2]); cfg=get_missiles_config(session); m=next((x for x in cfg.get("items",[]) if str(x.get("id"))==mid),None)
            if not m: await query.answer("❌ موشک پیدا نشد.",show_alert=True); return
            max_level=int(m.get("max_level",100) or 100); m.setdefault("levels",{})
            await query.answer(); await query.edit_message_text(f"📊 <b>سطوح موشک {m.get('name','موشک')}</b>\n\nحداکثر سطح: <b>{max_level}</b>\n🟢 سطح ۱ پس از باز شدن موشک به‌صورت خودکار است.\n\nسطح موردنظر برای تنظیم را انتخاب کنید:",parse_mode="HTML",reply_markup=missile_level_keyboard(mid,max_level)); return

        if action == "missile_level" and len(parts)>=4:
            mid=str(parts[2]); level=int(parts[3]); cfg=get_missiles_config(session); m=next((x for x in cfg.get("items",[]) if str(x.get("id"))==mid),None)
            if not m: await query.answer("❌ موشک پیدا نشد.",show_alert=True); return
            data=m.setdefault("levels",{}).setdefault(str(level),{"hq_required":1,"arsenal_required":1,"cost":0.0,"power":0.0,"target_time":0.0,"loot_percent":0.0,"upgrade_time":0.0,"upgrade_money":0.0,"upgrade_metal":0.0,"upgrade_fuel":0.0,"upgrade_uranium":0.0})
            text=(f"🚀 <b>{escape(str(m.get('name','موشک')))} — سطح {level}</b>\n\n"
                  f"🏛️ سطح مرکز فرماندهی لازم: <b>{int(data.get('hq_required',1) or 1)}</b>\n"
                  f"🏭 سطح زرادخانه لازم: <b>{int(data.get('arsenal_required',1) or 1)}</b>\n"
                  f"💰 هزینه: <b>{float(data.get('cost',0) or 0):,.0f}</b>\n"
                  f"💥 قدرت: <b>{float(data.get('power',0) or 0):,.0f}</b>\n"
                  f"⏱️ زمان برخورد با هدف: <b>{float(data.get('target_time',0) or 0):,.0f}</b> ثانیه")
            await query.answer(); await query.edit_message_text(text,parse_mode="HTML",reply_markup=missile_level_edit_keyboard(mid,level)); return

        if action == "missile_loot_set" and len(parts)>=5:
            mid=str(parts[2]); level=int(parts[3]); value=max(0.0,min(100.0,float(parts[4])))
            cfg=get_missiles_config(session); m=next((x for x in cfg.get("items",[]) if str(x.get("id"))==mid),None)
            if not m:
                await query.answer("❌ موشک پیدا نشد.",show_alert=True); return
            data=m.setdefault("levels",{}).setdefault(str(level),{"hq_required":1,"arsenal_required":1,"cost":0.0,"power":0.0,"target_time":0.0,"loot_percent":0.0,"upgrade_time":0.0,"upgrade_money":0.0,"upgrade_metal":0.0,"upgrade_fuel":0.0,"upgrade_uranium":0.0,"altitude_time":0.0,"altitude_money":0.0,"altitude_metal":0.0,"altitude_fuel":0.0,"altitude_uranium":0.0,"altitude_instant_finish_uranium_per_hour":0.0})
            data["loot_percent"]=value
            save_missiles_config(session,cfg); session.commit()
            await query.answer(f"✅ درصد غارت روی {value:g}% تنظیم شد.",show_alert=True)
            await query.edit_message_text(f"<b>{escape(str(m.get('name','موشک')))} — سطح {level}</b>\n\n💰 درصد غارت منابع: <b>{value:g}%</b>",parse_mode="HTML",reply_markup=missile_loot_percent_keyboard(mid,level))
            return

        if action == "missile_upgrade_settings" and len(parts) >= 4:
            mid = str(parts[2]); level = int(parts[3])
            cfg = get_missiles_config(session); m = next((x for x in cfg.get("items",[]) if str(x.get("id")) == mid), None)
            if not m:
                await query.answer("❌ موشک پیدا نشد.", show_alert=True); return
            data = m.get("levels", {}).get(str(level), {})
            text = (f"⬆️ <b>تنظیمات ارتقا</b>\n\n🚀 <b>{escape(str(m.get('name','موشک')))} — سطح {level}</b>\n\n"
                    f"⏳ زمان ارتقا: <b>{float(data.get('upgrade_time',0) or 0):,.0f}</b> ساعت\n"
                    "💰 <b>هزینه‌ها:</b>\n"
                    f"💰 پول: <b>{float(data.get('upgrade_money',0) or 0):,.0f}</b>\n"
                    f"🔩 فلز: <b>{float(data.get('upgrade_metal',0) or 0):,.0f}</b>\n"
                    f"⛽ سوخت: <b>{float(data.get('upgrade_fuel',0) or 0):,.0f}</b>\n"
                    f"☢️ اورانیوم: <b>{float(data.get('upgrade_uranium',0) or 0):,.2f}</b>")
            await query.answer(); await query.edit_message_text(text, parse_mode="HTML", reply_markup=missile_upgrade_settings_keyboard(mid, level)); return

        if action in {"mine_upgrade_settings", "arsenal_upgrade_settings", "hq_upgrade_settings"} and len(parts) >= 3:
            level = int(parts[2])
            if action == "mine_upgrade_settings":
                cfg = get_metal_mine_config(session); data = cfg.get("levels", {}).get(level, {})
                title = f"⛏️ معدن فلز — سطح {level}"
                back = f"owner:mine_level:{level}"
            elif action == "arsenal_upgrade_settings":
                cfg = get_arsenal_config(session); data = cfg.get("levels", {}).get(level, {})
                title = f"🏭 زرادخانه — سطح {level}"
                back = f"owner:arsenal_level:{level}"
            else:
                cfg = get_hq_config(session); data = cfg.get("levels", {}).get(level, {})
                title = f"🏛️ مرکز فرماندهی — سطح {level}"
                back = f"owner:hq_level:{level}"
            text = (f"⬆️ <b>تنظیمات ارتقا</b>\n\n{title}\n\n"
                    f"⏳ زمان ارتقا: <b>{float(data.get('upgrade_time',0) or 0):,.0f}</b> ساعت\n"
                    "💰 <b>هزینه‌ها:</b>\n"
                    f"💰 پول: <b>{float(data.get('upgrade_money',data.get('money',0)) or 0):,.0f}</b>\n"
                    f"🔩 فلز: <b>{float(data.get('upgrade_metal',data.get('metal',0)) or 0):,.0f}</b>\n"
                    f"⛽ سوخت: <b>{float(data.get('upgrade_fuel',data.get('fuel',0)) or 0):,.0f}</b>\n"
                    f"☢️ اورانیوم: <b>{float(data.get('upgrade_uranium',data.get('uranium',0)) or 0):,.2f}</b>")
            await query.answer(); await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data=back)]])); return

        if action == "missile_level_edit" and len(parts)>=5:
            mid=str(parts[2]); level=int(parts[3]); field=parts[4]
            if field not in {"hq_required","arsenal_required","cost","power","target_time","upgrade_time","upgrade_money","upgrade_metal","upgrade_fuel","upgrade_uranium"}: await query.answer("❌ گزینه نامعتبر است.",show_alert=True); return
            upgrade_fields={"upgrade_time","upgrade_money","upgrade_metal","upgrade_fuel","upgrade_uranium"}
            cfg=get_missiles_config(session)
            m=next((x for x in cfg.get("items",[]) if str(x.get("id"))==mid),None)
            level_data=(m or {}).get("levels",{}).get(str(level),(m or {}).get("levels",{}).get(level,{}))
            level_data=level_data or {}
            current=float(level_data.get(field,0) or 0)
            context.user_data["missile_pending"]={"step":field,"id":mid,"level":level,"back_callback":(f"owner:missile_upgrade_settings:{mid}:{level}" if field in {"upgrade_time","upgrade_money","upgrade_metal","upgrade_fuel","upgrade_uranium"} else f"owner:missile_level:{mid}:{level}"),"current_value":current}
            context.user_data[_waiting_scope_key("missile_pending")] = int(update.effective_chat.id)
            labels={"hq_required":"سطح مرکز فرماندهی لازم","arsenal_required":"سطح زرادخانه لازم","cost":"هزینه","power":"قدرت","capacity":"ظرفیت اشغال","target_time":"زمان برخورد با هدف (ثانیه)","loot_percent":"درصد غارت منابع","upgrade_time":"زمان ارتقا (ساعت)","upgrade_money":"هزینه ارتقا با پول","upgrade_metal":"هزینه ارتقا با فلز","upgrade_fuel":"هزینه ارتقا با سوخت","upgrade_uranium":"هزینه ارتقا با اورانیوم"}
            await query.answer(); await query.edit_message_text(f"✏️ <b>{labels[field]}</b>\n\nمقدار فعلی: <b>{current:,.2f}</b>\n\nمقدار جدید را ارسال کنید.",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data=f"owner:missile_level:{mid}:{level}")]])); return

        if action == "missile_base" and len(parts)>=3:
            mid=str(parts[2]); cfg=get_missiles_config(session); m=next((x for x in cfg.get("items",[]) if str(x.get("id"))==mid),None)
            if not m:
                await query.answer("❌ موشک پیدا نشد.",show_alert=True); return
            text=(f"⚙️ <b>تنظیمات پایه موشک {escape(str(m.get('name','موشک')))}</b>\n\n"
                  f"🏛️ سطح مرکز فرماندهی لازم: <b>{int(m.get('hq_required',1) or 1)}</b>\n"
                  f"🏭 سطح زرادخانه لازم: <b>{int(m.get('arsenal_required',1) or 1)}</b>\n"
                  f"💰 هزینه پایه: <b>{float(m.get('base_cost',0) or 0):,.0f}</b>\n"
                  f"💥 قدرت پایه: <b>{float(m.get('base_power',0) or 0):,.0f}</b>\n"
                  f"⏱️ زمان برخورد با هدف پایه: <b>{float(m.get('base_target_time',0) or 0):,.0f}</b> ثانیه")
            await query.answer(); await query.edit_message_text(text,parse_mode="HTML",reply_markup=missile_base_settings_keyboard(mid)); return

        if action == "missile_sticker" and len(parts)>=3:
            mid=str(parts[2]); cfg=get_missiles_config(session); m=next((x for x in cfg.get("items",[]) if str(x.get("id"))==mid),None)
            if not m:
                await query.answer("❌ موشک پیدا نشد.",show_alert=True); return
            current = bool(m.get("launch_sticker"))
            context.user_data["missile_pending"]={"step":"sticker","id":mid,"prompt_message_id":int(query.message.message_id),"prompt_chat_id":int(query.message.chat_id)}
            context.user_data[_waiting_scope_key("missile_pending")] = int(update.effective_chat.id)
            status = "✅ استیکر فعلی تنظیم شده است." if current else "❌ استیکری تنظیم نشده است."
            await query.answer()
            prompt_text=f"🎭 <b>استیکر شلیک موشک</b>\n\n{status}\n\nاستیکر جدید را ارسال کنید تا ذخیره شود. با ارسال استیکر جدید، استیکر قبلی ویرایش/جایگزین می‌شود."
            try:
                await query.edit_message_text(prompt_text,parse_mode="HTML",reply_markup=missile_sticker_keyboard(mid,current))
            except Exception:
                # اگر پنل قبلی به هر دلیل کپشن/مدیای تلگرام بود، همان پنل را حفظ می‌کنیم
                # و دست‌کم پاسخ callback را قطعی می‌کنیم.
                try:
                    await query.edit_message_caption(caption=prompt_text,parse_mode="HTML",reply_markup=missile_sticker_keyboard(mid,current))
                except Exception:
                    await query.answer("⚠️ پنل استیکر قابل ویرایش نیست. دوباره از تنظیمات موشک وارد شوید.",show_alert=True)
            return

        if action == "missile_sticker_delete" and len(parts)>=3:
            mid=str(parts[2]); cfg=get_missiles_config(session); m=next((x for x in cfg.get("items",[]) if str(x.get("id"))==mid),None)
            if not m:
                await query.answer("❌ موشک پیدا نشد.",show_alert=True); return
            if not m.get("launch_sticker"):
                await query.answer("ℹ️ برای این موشک استیکری ثبت نشده است.",show_alert=True); return
            m.pop("launch_sticker", None); save_missiles_config(session,cfg); session.commit()
            context.user_data.pop("missile_pending",None)
            await query.answer("🗑️ استیکر شلیک حذف شد.",show_alert=True)
            await query.edit_message_text("🎭 <b>استیکر شلیک موشک</b>\n\n❌ استیکر شلیک حذف شده است.\n\nمی‌توانید یک استیکر جدید ارسال کنید.",parse_mode="HTML",reply_markup=missile_sticker_keyboard(mid,False))
            return

        if action == "missile_edit" and len(parts)>=4:
            mid=str(parts[2]); field=parts[3]
            cfg=get_missiles_config(session)
            m=next((x for x in cfg.get("items",[]) if str(x.get("id"))==mid),None)
            if not m:
                await query.answer("❌ موشک پیدا نشد.",show_alert=True); return
            if field=="type":
                await query.answer(); await query.edit_message_text("🏷 <b>نوع موشک</b>",parse_mode="HTML",reply_markup=missile_type_keyboard(mid)); return
            if field not in {"max_level","hq_required","arsenal_required","base_cost","base_power","base_capacity","base_target_time","instant_finish_uranium_per_hour"}: await query.answer("❌ گزینه نامعتبر است.",show_alert=True); return
            base_fields={"hq_required","arsenal_required","base_cost","base_power","base_capacity","base_target_time"}
            current=float(m.get(field,0) or 0)
            context.user_data["missile_pending"]={"step":field,"id":mid,"back_callback":(f"owner:missile_base:{mid}" if field in base_fields else f"owner:missile:{mid}"),"current_value":current}
            context.user_data[_waiting_scope_key("missile_pending")] = int(update.effective_chat.id)
            label={"max_level":"حداکثر سطح","hq_required":"سطح مرکز فرماندهی لازم","arsenal_required":"سطح زرادخانه لازم","base_cost":"هزینه پایه","base_power":"قدرت پایه","base_capacity":"ظرفیت اشغال کلی","base_target_time":"زمان برخورد با هدف پایه (ثانیه)","instant_finish_uranium_per_hour":"اورانیوم تکمیل فوری ارتقا به ازای هر ساعت"}[field]
            await query.answer(); await query.edit_message_text(f"✏️ <b>{label}</b>\n\nمقدار فعلی: <b>{current:,.2f}</b>\n\nمقدار جدید را ارسال کنید.",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data=f"owner:missile:{mid}")]])); return

        if action == "missile_toggle" and len(parts)>=3:
            mid=str(parts[2]); cfg=get_missiles_config(session); m=next((x for x in cfg.get("items",[]) if str(x.get("id"))==mid),None)
            if not m:
                await query.answer("❌ موشک پیدا نشد.",show_alert=True); return
            m["active"] = not bool(m.get("active",False)); save_missiles_config(session,cfg); session.commit()
            await query.answer("🟢 موشک فعال شد." if m["active"] else "🔴 موشک غیرفعال شد.", show_alert=True)
            text=(f"<b>{m.get('name','موشک')}</b>\n\n🏷 نوع: <b>{m.get('type','نامشخص')}</b>\n🏷️ نام‌های عملیاتی: <b>{escape('، '.join(str(x) for x in (m.get('operational_names',[]) or [])) or 'ثبت نشده')}</b>\n📦 ظرفیت اشغال کلی: <b>{float(m.get('base_capacity',0) or 0):,.0f}</b>\n🔝 حداکثر سطح: <b>{int(m.get('max_level',100))}</b>\n📌 وضعیت: <b>{'فعال' if m.get('active',False) else 'غیرفعال'}</b>")
            await query.edit_message_text(text,parse_mode="HTML",reply_markup=missile_edit_keyboard(mid, f"owner:missile_list_type:{m.get('type','کروز')}", bool(m.get("active",False)))); return

        if action == "missile_type" and len(parts)>=4:
            mid=str(parts[2]); typ=parts[3]; cfg=get_missiles_config(session); m=next((x for x in cfg.get("items",[]) if str(x.get("id"))==mid),None)
            if not m: await query.answer("❌ موشک پیدا نشد.",show_alert=True); return
            m["type"]=typ; save_missiles_config(session,cfg); session.commit()
            await query.answer("✅ نوع موشک تغییر کرد.",show_alert=True)
            text=(f"<b>{m.get('name','موشک')}</b>\n\n🏷 نوع: <b>{m.get('type')}</b>\n📌 وضعیت: <b>{'فعال' if m.get('active',False) else 'غیرفعال'}</b>\n🔝 حداکثر سطح: <b>{int(m.get('max_level',100))}</b>\n🏛️ سطح مرکز فرماندهی لازم برای باز شدن: <b>{int(m.get('hq_required',1))}</b>\n🏭 سطح زرادخانه لازم برای باز شدن: <b>{int(m.get('arsenal_required',1))}</b>")
            await query.edit_message_text(text,parse_mode="HTML",reply_markup=missile_edit_keyboard(mid, f"owner:missile_list_type:{m.get('type','کروز')}", bool(m.get("active",False)))); return

        if action == "missile_draft_edit" and len(parts)>=3:
            field=parts[2]
            if field=="type":
                await query.answer("ℹ️ نوع موشک هنگام افزودن انتخاب شده است.",show_alert=True); return
            if field not in {"max_level","hq_required","arsenal_required"}: return
            d=context.user_data.get("missile_draft")
            if not d: await query.answer("❌ عملیات منقضی شده است.",show_alert=True); return
            current=float(d.get(field,0) or 0)
            context.user_data["missile_pending"]={"step":field,"draft":True,"current_value":current}
            context.user_data[_waiting_scope_key("missile_pending")] = int(update.effective_chat.id)
            label={"max_level":"حداکثر سطح","hq_required":"سطح مرکز فرماندهی لازم","arsenal_required":"سطح زرادخانه لازم"}[field]
            await query.answer(); await query.edit_message_text(f"✏️ <b>{label}</b>\n\nمقدار فعلی: <b>{current:,.2f}</b>\n\nمقدار جدید را ارسال کنید.",parse_mode="HTML",reply_markup=missile_draft_keyboard("owner:missile_add")); return

        if action in {"missile_value_confirm", "missile_value_edit", "missile_value_cancel"}:
            pending = context.user_data.get("missile_pending") or {}
            if pending.get("value") is None:
                await query.answer("⚠️ عملیات منقضی شده است.", show_alert=True); return
            if action == "missile_value_edit":
                pending.pop("value", None); context.user_data["missile_pending"] = pending
                context.user_data[_waiting_scope_key("missile_pending")] = int(update.effective_chat.id)
                back = pending.get("back_callback", "owner:missile_add" if pending.get("draft") else f"owner:missile:{pending.get('id')}")
                current = float(pending.get("current_value", 0) or 0)
                await query.answer(); await query.edit_message_text(
                    f"✏️ <b>ویرایش مقدار</b>\n\nمقدار فعلی: <b>{current:,.2f}</b>\n\nمقدار جدید را ارسال کنید.",
                    parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data=back)]])); return
            if action == "missile_value_cancel":
                back = pending.get("back_callback")
                context.user_data.pop("missile_pending", None)
                if pending.get("draft"):
                    back = back or "owner:missile_add"
                    await query.answer("لغو شد."); await query.edit_message_text("🚀 تنظیمات موشک", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data=back)]]))
                else:
                    mid=str(pending.get("id")); back = back or f"owner:missile:{mid}"; await query.answer("لغو شد."); await query.edit_message_text("🚀 تنظیمات موشک", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data=back)]]))
                return
            value=float(pending["value"]); step=pending.get("step")
            if pending.get("draft"):
                draft=context.user_data.get("missile_draft")
                if not draft:
                    context.user_data.pop("missile_pending",None); await query.answer("⚠️ عملیات منقضی شده است.",show_alert=True); return
                draft[step]=int(value) if step in {"max_level","hq_required","arsenal_required"} else value
                if step=="max_level":
                    ml=max(1,min(100,int(value))); draft["max_level"]=ml; draft.setdefault("levels",{})
                    for i in range(1,ml+1): draft["levels"].setdefault(str(i),{"hq_required":1,"arsenal_required":1,"cost":0.0,"power":0.0,"target_time":0.0})
                context.user_data["missile_draft"]=draft; context.user_data.pop("missile_pending",None)
                context.user_data[_waiting_scope_key("missile_draft")] = int(update.effective_chat.id)
                await query.answer("✅ مقدار ثبت شد.",show_alert=True); await query.edit_message_text("🚀 <b>تنظیمات موشک</b>\n\nمقدار جدید ثبت شد. برای ثبت نهایی موشک، تأیید نهایی را بزنید.",parse_mode="HTML",reply_markup=missile_draft_keyboard()); return
            cfg=get_missiles_config(session); mid=str(pending.get("id")); m=next((x for x in cfg.get("items",[]) if str(x.get("id"))==mid),None)
            if not m:
                context.user_data.pop("missile_pending",None); await query.answer("❌ موشک پیدا نشد.",show_alert=True); return
            if pending.get("level"):
                lvl=str(pending.get("level")); m.setdefault("levels",{}).setdefault(lvl,{"hq_required":1,"cost":0.0,"power":0.0,"target_time":0.0,"loot_percent":0.0})[step]=int(value) if step=="hq_required" else value
            else:
                m[step]=int(value) if step in {"max_level","hq_required","arsenal_required"} else value
                if step=="max_level":
                    ml=max(1,min(100,int(value))); m["max_level"]=ml; m.setdefault("levels",{})
                    for i in range(1,ml+1): m["levels"].setdefault(str(i),{"hq_required":1,"arsenal_required":1,"cost":0.0,"power":0.0,"target_time":0.0})
            back = pending.get("back_callback") or f"owner:missile:{mid}"
            save_missiles_config(session,cfg); session.commit(); context.user_data.pop("missile_pending",None)
            if step in {"upgrade_time","upgrade_money","upgrade_metal","upgrade_fuel","upgrade_uranium"}:
                level = int(pending.get("level", 1) or 1)
                data = m.get("levels", {}).get(str(level), {}) or {}
                text = (f"⬆️ <b>تنظیمات ارتقا</b>\n\n🚀 <b>{escape(str(m.get('name','موشک')))} — سطح {level}</b>\n\n"
                        f"⏳ زمان ارتقا: <b>{float(data.get('upgrade_time',0) or 0):,.0f}</b> ساعت\n"
                        "💰 <b>هزینه‌ها:</b>\n"
                        f"💰 پول: <b>{float(data.get('upgrade_money',0) or 0):,.0f}</b>\n"
                        f"🔩 فلز: <b>{float(data.get('upgrade_metal',0) or 0):,.0f}</b>\n"
                        f"⛽ سوخت: <b>{float(data.get('upgrade_fuel',0) or 0):,.0f}</b>\n"
                        f"☢️ اورانیوم: <b>{float(data.get('upgrade_uranium',0) or 0):,.2f}</b>")
                await query.answer()
                await query.edit_message_text(text, parse_mode="HTML", reply_markup=missile_upgrade_settings_keyboard(mid, level))
                return
            ops_text="، ".join(str(x) for x in (m.get("operational_names",[]) or [])) or "ثبت نشده"
            missile_text=(f"<b>{escape(str(m.get('name','موشک')))}</b>\n\n"
                          f"🏷 نوع: <b>{escape(str(m.get('type','نامشخص')))}</b>\n"
                          f"🏷️ نام‌های عملیاتی: <b>{escape(ops_text)}</b>\n"
                          f"📦 ظرفیت اشغال کلی: <b>{float(m.get('base_capacity',0) or 0):,.0f}</b>\n"
                          f"🔝 حداکثر سطح: <b>{int(m.get('max_level',100) or 100)}</b>\n"
                          f"☢️ اورانیوم تکمیل فوری ارتقا: <b>{float(m.get('instant_finish_uranium_per_hour',0) or 0):,.2f}</b> در ساعت\n"
                          f"📌 وضعیت: <b>{'فعال' if m.get('active',False) else 'غیرفعال'}</b>")
            await query.answer(); await query.edit_message_text(missile_text,parse_mode="HTML",reply_markup=missile_edit_keyboard(mid, f"owner:missile_list_type:{m.get('type','کروز')}", bool(m.get('active',False)))); return

        if action == "missile_draft_confirm":
            d=context.user_data.get("missile_draft")
            if not d: await query.answer("❌ عملیات منقضی شده است.",show_alert=True); return
            cfg=get_missiles_config(session); new_id=max([int(x.get("id",0)) for x in cfg.get("items",[]) if str(x.get("id","")).isdigit()] or [0])+1
            d["id"]=new_id; cfg.setdefault("items",[]).append(d); save_missiles_config(session,cfg); session.commit(); context.user_data.pop("missile_draft",None)
            await query.answer("✅ موشک ثبت شد.",show_alert=True); await query.edit_message_text("🚀 <b>مدیریت موشک‌ها</b>\n\nبخش موردنظر را انتخاب کنید:",parse_mode="HTML",reply_markup=missile_management_keyboard(cfg.get("items",[]))); return

        if action == "economy_bank":
            cfg=get_bank_config(session)
            await query.answer()
            text=(f"🏦 <b>تنظیمات بانک مرکزی</b>\n\n"
                  f"🔝 حداکثر سطح: <b>{bank_max_level(session)}</b>\n"
                  f"☢️ اورانیوم تکمیل فوری: <b>{float(cfg.get('instant_finish_uranium_per_hour',0) or 0):,.2f}</b> در ساعت\n")
            await query.edit_message_text(text,parse_mode="HTML",reply_markup=bank_economy_keyboard()); return

        if action == "bank_build":
            cfg=get_bank_config(session); d=bank_level_config(session,1)
            text=("🏗️ <b>ساخت بانک مرکزی</b>\n\n"
                  f"🏛️ سطح مرکز فرماندهی مورد نیاز: <b>{int(d.get('required_hq_level',1) or 1)}</b>\n"
                  f"⏱️ زمان تکمیل: <b>{float(d.get('build_time_hours',0) or 0):g} ساعت</b>")
            await query.answer(); await query.edit_message_text(text,parse_mode="HTML",reply_markup=bank_build_keyboard()); return

        if action == "bank_build_costs":
            cfg=get_bank_config(session); d=bank_level_config(session,1); b=d.get("build_cost",{}) or {}
            text=("💰 <b>هزینه‌ها</b>\n\n"
                  f"💰 پول: <b>{float(b.get('money',0) or 0):,.0f}</b>\n"
                  f"🔩 فلز: <b>{float(b.get('metal',0) or 0):,.0f}</b>\n"
                  f"⛽ سوخت: <b>{float(b.get('fuel',0) or 0):,.0f}</b>\n"
                  f"☢️ اورانیوم: <b>{float(b.get('uranium',0) or 0):,.2f}</b>")
            await query.answer(); await query.edit_message_text(text + "\n\nگزینه موردنظر را برای ویرایش انتخاب کنید:",parse_mode="HTML",reply_markup=bank_build_costs_keyboard()); return

        if action == "bank_build_deposit_settings":
            d=bank_level_config(session,1)
            text=("🏦 <b>تنظیمات سپرده — ساخت بانک مرکزی</b>\n\n"
                  f"📦 حداکثر سپرده: <b>{float(d.get('deposit_capacity',0) or 0):,.0f}</b>\n"
                  f"📈 سود سپرده در ساعت: <b>{float(d.get('deposit_hourly_profit_percent',0) or 0):g}%</b>\n\n"
                  "حداکثر سپرده، ظرفیت کل مخزن سپرده است. ")
            await query.answer(); await query.edit_message_text(text,parse_mode="HTML",reply_markup=bank_deposit_settings_keyboard(1,build=True)); return

        if action == "bank_build_edit" and len(parts)>=3:
            field=":".join(parts[2:]); cfg=get_bank_config(session); d=cfg["levels"]["1"]
            if field.startswith("build_cost:"):
                _,key=field.split(":",1); current=float((d.get("build_cost",{}) or {}).get(key,0) or 0)
            else:
                key=field; raw_current=d.get(key,0)
                if isinstance(raw_current, dict):
                    await query.answer("❌ گزینه تنظیم نامعتبر است.", show_alert=True); return
                current=float(raw_current or 0)
            build_back = "owner:bank_build_costs" if field.startswith("build_cost:") else ("owner:bank_deposit_settings:1:1" if field in {"deposit_capacity","deposit_hourly_profit_percent"} else ("owner:bank_tax_settings:1:1" if field in {"tax_min","tax_max"} else "owner:bank_build"))
            context.user_data["economy_pending"]={"building":"bank","type":"bank_build","field":field,"back_callback":build_back,"current_value":current,"prompt_message_id":int(query.message.message_id),"prompt_chat_id":int(query.message.chat_id)}
            context.user_data[_waiting_scope_key("economy_pending")]=int(update.effective_chat.id)
            labels={"required_hq_level":"سطح مرکز فرماندهی مورد نیاز","build_time_hours":"زمان تکمیل","build_cost:money":"پول","build_cost:metal":"فلز","build_cost:fuel":"سوخت","build_cost:uranium":"اورانیوم","deposit_capacity":"حداکثر سپرده","deposit_hourly_profit_percent":"سود سپرده در ساعت (%)","tax_min":"حداقل مالیات به ازای هر ۱۰۰۰ شهروند","tax_max":"حداکثر مالیات به ازای هر ۱۰۰۰ شهروند"}
            await query.answer(); await query.edit_message_text(f"✏️ <b>{labels.get(field,field)}</b>\n\nمقدار فعلی: <b>{current:,.2f}</b>\n\nمقدار جدید را ارسال کنید.",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="owner:bank_build")]])); return

        if action == "bank_instant_finish_rate":
            cfg=get_bank_config(session); current=float(cfg.get("instant_finish_uranium_per_hour",0) or 0)
            context.user_data["economy_pending"]={"building":"bank","type":"bank_instant_finish_rate","back_callback":"owner:economy_bank","current_value":current,"prompt_message_id":int(query.message.message_id),"prompt_chat_id":int(query.message.chat_id)}
            context.user_data[_waiting_scope_key("economy_pending")]=int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text(f"☢️ <b>اورانیوم تکمیل فوری بانک مرکزی</b>\n\nمقدار فعلی: <b>{current:,.2f}</b> اورانیوم در ساعت\n\nمقدار جدید را ارسال کنید.",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="owner:economy_bank")]])); return

        if action == "bank_loans":
            await query.answer(); await query.edit_message_text("⚙️ <b>تنظیمات بانک مرکزی — سطح ۱</b>\n\nبخش موردنظر را انتخاب کنید:",parse_mode="HTML",reply_markup=__import__("keyboards.admin",fromlist=["bank_level_settings_keyboard"]).bank_level_settings_keyboard(1,build=True)); return
        if action == "bank_investments" and len(parts)>=3:
            pending_nav=context.user_data.get("economy_pending") or {}
            if pending_nav.get("building")=="bank" and str(pending_nav.get("type","")).startswith("bank_investment"):
                context.user_data.pop("economy_pending",None); context.user_data.pop(_waiting_scope_key("economy_pending"),None)
            level=int(parts[2]); build_mode=(len(parts)>=4 and parts[3]=="1")
            cfg=get_bank_config(session); d=cfg.get("levels",{}).get(str(level),{}) or {}; plans=d.setdefault("investments",[])
            await query.answer(); await query.edit_message_text(
                f"📈 <b>تنظیمات سرمایه‌گذاری — سطح {level}</b>\n\n"
                "سرمایه‌گذاری موردنظر را انتخاب کنید یا مورد جدید اضافه کنید.",
                parse_mode="HTML",reply_markup=bank_investments_settings_keyboard(plans,level=level,build=build_mode)); return

        if action == "bank_investment_add" and len(parts)>=4:
            level=int(parts[2]); build_mode=(parts[3]=="1")
            mode=1 if build_mode else 0
            # در شروع افزودن، فقط انتخاب بازده نمایش داده می‌شود.
            # تا وقتی بازده انتخاب نشده، هیچ ورودی متنی از Owner گرفته نمی‌شود.
            await query.answer()
            await query.edit_message_text(
                f"📈 <b>افزودن سرمایه‌گذاری — سطح {level}</b>\n\n"
                "ابتدا نوع بازده سرمایه‌گذاری را انتخاب کنید:",
                parse_mode="HTML",
                reply_markup=bank_investment_return_type_keyboard(level, build=build_mode)
            ); return

        if action == "bank_investment_list" and len(parts)>=4:
            level=int(parts[2]); build_mode=(parts[3]=="1")
            cfg=get_bank_config(session); plans=(cfg.get("levels",{}).get(str(level),{}) or {}).get("investments",[]) or []
            if not plans:
                await query.answer("📋 هنوز سرمایه‌گذاری‌ای ثبت نشده است.",show_alert=True)
                return
            await query.answer()
            await query.edit_message_text(f"📋 <b>لیست سرمایه‌گذاری‌ها — سطح {level}</b>\n\nبرای ویرایش مشخصات، طرح موردنظر را انتخاب کنید.",parse_mode="HTML",reply_markup=bank_investment_list_keyboard(plans,level=level,build=build_mode))
            return

        if action == "bank_investment_delete_list" and len(parts)>=4:
            level=int(parts[2]); build_mode=(parts[3]=="1")
            cfg=get_bank_config(session); plans=(cfg.get("levels",{}).get(str(level),{}) or {}).get("investments",[]) or []
            if not plans:
                await query.answer("🗑️ طرحی برای حذف وجود ندارد.",show_alert=True)
                return
            await query.answer()
            await query.edit_message_text(f"🗑️ <b>حذف سرمایه‌گذاری — سطح {level}</b>\n\nطرح موردنظر برای حذف را انتخاب کنید.",parse_mode="HTML",reply_markup=bank_investment_list_keyboard(plans,level=level,build=build_mode,delete_mode=True))
            return

        if action == "bank_investment_delete" and len(parts)>=5:
            level=int(parts[2]); idx=int(parts[3]); build_mode=(parts[4]=="1")
            cfg=get_bank_config(session); plans=(cfg.get("levels",{}).get(str(level),{}) or {}).get("investments",[]) or []
            if idx<0 or idx>=len(plans):
                await query.answer("❌ سرمایه‌گذاری پیدا نشد.",show_alert=True); return
            plan=plans[idx]
            await query.answer()
            await query.edit_message_text(
                f"⚠️ <b>تأیید حذف سرمایه‌گذاری</b>\n\nطرح <b>{escape(str(plan.get('name','سرمایه‌گذاری')))}</b> حذف خواهد شد.\n\nآیا مطمئن هستید؟",
                parse_mode="HTML",
                reply_markup=bank_investment_delete_confirm_keyboard(level,idx,build=build_mode)
            )
            return

        if action == "bank_investment_delete_confirm" and len(parts)>=5:
            level=int(parts[2]); idx=int(parts[3]); build_mode=(parts[4]=="1")
            cfg=get_bank_config(session); plans=(cfg.get("levels",{}).get(str(level),{}) or {}).setdefault("investments",[])
            if idx<0 or idx>=len(plans):
                await query.answer("❌ سرمایه‌گذاری پیدا نشد.",show_alert=True); return
            removed=str(plans[idx].get("name","سرمایه‌گذاری"))
            plans.pop(idx); save_bank_config(session,cfg); session.commit()
            await query.answer("🗑️ سرمایه‌گذاری حذف شد.",show_alert=True)
            await query.edit_message_text(f"📈 <b>تنظیمات سرمایه‌گذاری — سطح {level}</b>\n\nطرح <b>{escape(removed)}</b> حذف شد.",parse_mode="HTML",reply_markup=bank_investments_settings_keyboard(plans,level=level,build=build_mode))
            return

        if action == "bank_investment" and len(parts)>=4:
            pending_nav=context.user_data.get("economy_pending") or {}
            if pending_nav.get("building")=="bank" and str(pending_nav.get("type","")).startswith("bank_investment"):
                context.user_data.pop("economy_pending",None); context.user_data.pop(_waiting_scope_key("economy_pending"),None)
            level=int(parts[2]); idx=int(parts[3]); build_mode=(len(parts)>=5 and parts[4]=="1"); cfg=get_bank_config(session); plans=(cfg.get("levels",{}).get(str(level),{}) or {}).get("investments",[]) or []
            if idx<0 or idx>=len(plans): await query.answer("❌ سرمایه‌گذاری پیدا نشد.",show_alert=True); return
            p=plans[idx]; await query.answer(); await query.edit_message_text(_investment_plan_text(p, admin=True),parse_mode="HTML",reply_markup=bank_investment_edit_keyboard(idx,level=level,build=build_mode)); return

        if action == "bank_investment_toggle" and len(parts)>=5:
            level=int(parts[2]); idx=int(parts[3]); build_mode=(parts[4]=="1"); cfg=get_bank_config(session); plans=(cfg.get("levels",{}).get(str(level),{}) or {}).setdefault("investments",[])
            if idx<0 or idx>=len(plans): await query.answer("❌ سرمایه‌گذاری پیدا نشد.",show_alert=True); return
            plans[idx]["active"]=not bool(plans[idx].get("active",True)); save_bank_config(session,cfg); session.commit()
            await query.answer("🟢 طرح فعال شد." if plans[idx]["active"] else "🔴 طرح غیرفعال شد.",show_alert=True); await query.edit_message_text(_investment_plan_text(plans[idx], admin=True),parse_mode="HTML",reply_markup=bank_investment_edit_keyboard(idx,level=level,build=build_mode)); return

        if action == "bank_investment_multi" and len(parts)>=5:
            level=int(parts[2]); idx=int(parts[3]); build_mode=(parts[4]=="1")
            cfg=get_bank_config(session); plans=(cfg.get("levels",{}).get(str(level),{}) or {}).setdefault("investments",[])
            if idx<0 or idx>=len(plans):
                await query.answer("❌ سرمایه‌گذاری پیدا نشد.",show_alert=True); return
            plans[idx]["allow_multiple_active"]=not bool(plans[idx].get("allow_multiple_active",False))
            save_bank_config(session,cfg); session.commit()
            state="مجاز" if plans[idx]["allow_multiple_active"] else "غیرمجاز"
            await query.answer(f"🔁 سرمایه‌گذاری همزمان: {state}",show_alert=True)
            await query.edit_message_text(_investment_plan_text(plans[idx], admin=True),parse_mode="HTML",reply_markup=bank_investment_edit_keyboard(idx,level=level,build=build_mode)); return

        if action == "bank_investment_add_return" and len(parts)>=5:
            level=int(parts[2]); mode=parts[3]; return_type=str(parts[4])
            if return_type not in {"money","population","fuel","metal","uranium","leadership_experience"}:
                await query.answer("❌ نوع بازده نامعتبر است.",show_alert=True); return
            context.user_data["economy_pending"]={"building":"bank","type":"bank_investment_add_name","level":level,"mode":1 if mode=="1" else 0,"return_type":return_type,"back_callback":f"owner:bank_investments:{level}:{mode}","prompt_message_id":int(query.message.message_id),"prompt_chat_id":int(query.message.chat_id)}
            context.user_data[_waiting_scope_key("economy_pending")]=int(update.effective_chat.id)
            names={"money":"پول","population":"جمعیت","fuel":"سوخت","metal":"فلز","uranium":"اورانیوم","leadership_experience":"تجربه رهبری"}
            await query.answer(); await query.edit_message_text(f"✏️ <b>نام سرمایه‌گذاری</b>\n\nنوع بازده انتخاب‌شده: <b>{names[return_type]}</b>\n\nنام طرح را ارسال کنید.",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data=f"owner:bank_investments:{level}:{mode}")]])); return

        if action == "bank_investment_return_type" and len(parts)>=5:
            await query.answer("ℹ️ نوع بازده پس از ساخت طرح قابل تغییر نیست.",show_alert=True); return

        if action == "bank_investment_financial" and len(parts)>=5:
            pending_nav=context.user_data.get("economy_pending") or {}
            if pending_nav.get("building")=="bank" and str(pending_nav.get("type","")).startswith("bank_investment"):
                context.user_data.pop("economy_pending",None); context.user_data.pop(_waiting_scope_key("economy_pending"),None)
            level=int(parts[2]); idx=int(parts[3]); build_mode=(parts[4]=="1")
            cfg=get_bank_config(session); plans=(cfg.get("levels",{}).get(str(level),{}) or {}).setdefault("investments",[])
            if idx<0 or idx>=len(plans): await query.answer("❌ سرمایه‌گذاری پیدا نشد.",show_alert=True); return
            p=plans[idx]
            await query.answer(); await query.edit_message_text(_investment_plan_text(p,admin=True)+"\n\n⚙️ <b>تنظیم مبلغ، سود، زیان و مدت</b>",parse_mode="HTML",reply_markup=__import__("keyboards.admin",fromlist=["bank_investment_financial_keyboard"]).bank_investment_financial_keyboard(idx,level=level,build=build_mode)); return

        if action == "bank_investment_edit" and len(parts)>=6:
            level=int(parts[2]); idx=int(parts[3]); build_mode=(parts[4]=="1"); field=parts[5]; cfg=get_bank_config(session); plans=(cfg.get("levels",{}).get(str(level),{}) or {}).setdefault("investments",[])
            if idx<0 or idx>=len(plans): await query.answer("❌ سرمایه‌گذاری پیدا نشد.",show_alert=True); return
            p=plans[idx]; current=p.get(field,"")
            if field in {"profit_min","profit_max","loss_min","loss_max"}:
                kind = "profit" if field.startswith("profit") else "loss"
                bound = "min" if field.endswith("_min") else "max"
                is_money = str(p.get("return_type","money")) == "money"
                key = f"{kind}_{bound}_percent" if is_money else f"{kind}_{bound}_value"
                current = p.get(key, 0) or 0
                unit = "٪" if is_money else "واحد"
                label = {"profit_min":"حداقل سود احتمالی","profit_max":"حداکثر سود احتمالی","loss_min":"حداقل زیان احتمالی","loss_max":"حداکثر زیان احتمالی"}[field]
                context.user_data["economy_pending"]={"building":"bank","type":"bank_investment_single_range","level":level,"index":idx,"field":field,"mode":1 if build_mode else 0,"value_mode":"percent" if is_money else "amount","back_callback":f"owner:bank_investment_financial:{level}:{idx}:{1 if build_mode else 0}","current_value":current,"prompt_message_id":int(query.message.message_id),"prompt_chat_id":int(query.message.chat_id)}
                context.user_data[_waiting_scope_key("economy_pending")]=int(update.effective_chat.id)
                await query.answer(); await query.edit_message_text(f"📊 <b>{label}</b>\n\nمقدار فعلی: <b>{float(current):g}{unit}</b>\n\nمقدار جدید را ارسال کنید.",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data=f"owner:bank_investment_financial:{level}:{idx}:{1 if build_mode else 0}")]])); return
            if field in {"profit_range","loss_range"}:
                kind="profit" if field=="profit_range" else "loss"
                is_money=str(p.get("return_type","money"))=="money"
                min_key=f"{kind}_min_percent" if is_money else f"{kind}_min_value"
                max_key=f"{kind}_max_percent" if is_money else f"{kind}_max_value"
                context.user_data["economy_pending"]={"building":"bank","type":"bank_investment_range","level":level,"index":idx,"field":kind,"mode":1 if build_mode else 0,"value_mode":"percent" if is_money else "amount","back_callback":f"owner:bank_investment_financial:{level}:{idx}:{1 if build_mode else 0}","current_value":f"{p.get(min_key,0)} تا {p.get(max_key,0)}","prompt_message_id":int(query.message.message_id),"prompt_chat_id":int(query.message.chat_id)}
                context.user_data[_waiting_scope_key("economy_pending")]=int(update.effective_chat.id)
                label="سود" if kind=="profit" else "زیان"; unit="٪" if is_money else "واحد"
                await query.answer(); await query.edit_message_text(f"📊 <b>تنظیم {label} احتمالی</b>\n\nحداقل فعلی: <b>{float(p.get(min_key,0) or 0):g}{unit}</b>\nحداکثر فعلی: <b>{float(p.get(max_key,0) or 0):g}{unit}</b>\n\nدو عدد را به شکل <b>حداقل،حداکثر</b> ارسال کنید.",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data=f"owner:bank_investment_financial:{level}:{idx}:{1 if build_mode else 0}")]])); return
            if field=="risk":
                cycle={"کم":"متوسط","متوسط":"زیاد","زیاد":"کم"}; p["risk"]=cycle.get(str(p.get("risk","متوسط")),"متوسط"); save_bank_config(session,cfg); session.commit(); await query.answer("🎚️ ریسک تغییر کرد.",show_alert=True); await query.edit_message_text(_investment_plan_text(p, admin=True),parse_mode="HTML",reply_markup=bank_investment_edit_keyboard(idx,level=level,build=build_mode)); return
            if field=="plan_type":
                order=["short","medium","long"]; cur=str(p.get("plan_type","medium")); p["plan_type"]=order[(order.index(cur)+1)%len(order)] if cur in order else "medium"; save_bank_config(session,cfg); session.commit(); await query.answer("🧩 نوع طرح تغییر کرد.",show_alert=True); await query.edit_message_text(_investment_plan_text(p, admin=True),parse_mode="HTML",reply_markup=bank_investment_edit_keyboard(idx,level=level,build=build_mode)); return
            field_labels={"name":"نام طرح","min_amount":"حداقل مبلغ","max_amount":"حداکثر مبلغ","duration_hours":"مدت (ساعت)","max_per_user":"حداکثر تعداد برای هر کاربر"}
            field_label=field_labels.get(field,"تنظیمات طرح")
            field_back = f"owner:bank_investment_financial:{level}:{idx}:{1 if build_mode else 0}" if field in {"min_amount","max_amount","duration_hours"} else f"owner:bank_investment:{level}:{idx}:{1 if build_mode else 0}"
            context.user_data["economy_pending"]={"building":"bank","type":"bank_investment","level":level,"index":idx,"field":field,"mode":1 if build_mode else 0,"back_callback":field_back,"current_value":current,"prompt_message_id":int(query.message.message_id),"prompt_chat_id":int(query.message.chat_id)}
            context.user_data[_waiting_scope_key("economy_pending")]=int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text(f"✏️ <b>ویرایش {field_label}</b>\n\nمقدار فعلی: <b>{escape(str(current))}</b>\n\nمقدار جدید را ارسال کنید.",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data=field_back)]])); return

        if action == "bank_max_level":
            cfg=get_bank_config(session); context.user_data["economy_pending"]={"building":"bank","type":"max_level","back_callback":"owner:economy_bank","current_value":bank_max_level(session),"prompt_message_id":int(query.message.message_id),"prompt_chat_id":int(query.message.chat_id)}; context.user_data[_waiting_scope_key("economy_pending")]=int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text(f"🔝 <b>حداکثر سطح بانک مرکزی</b>\n\nمقدار فعلی: <b>{bank_max_level(session)}</b>\nیک عدد بین 1 تا 100 ارسال کنید.",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="owner:economy_bank")]])); return

        if action == "bank_levels":
            mx=bank_max_level(session); rows=[]; row=[]
            for n in range(2,mx+1):
                row.append(InlineKeyboardButton(f"سطح {n}",callback_data=f"owner:bank_level:{n}",style="primary"))
                if len(row)==5:
                    rows.append(row); row=[]
            if row:
                rows.append(row)
            rows.append([InlineKeyboardButton("🔙 برگشت",callback_data="owner:economy_bank")])
            await query.answer(); await query.edit_message_text("📊 <b>تنظیم سطوح بانک مرکزی</b>\n\nگزینه موردنظر را انتخاب کنید.",parse_mode="HTML",reply_markup=InlineKeyboardMarkup(rows)); return

        if action == "bank_level_settings" and len(parts)>=4:
            level=int(parts[2]); build_mode=(parts[3]=="build"); d=bank_level_config(session,level)
            from keyboards.admin import bank_level_settings_keyboard
            title=f"⚙️ <b>تنظیمات بانک مرکزی — سطح {level}</b>" + (" (ساخت)" if build_mode else "")
            await query.answer(); await query.edit_message_text(title+"\n\nبخش موردنظر را انتخاب کنید:",parse_mode="HTML",reply_markup=bank_level_settings_keyboard(level,build=build_mode)); return

        if action == "bank_build_loan_settings":
            level=1; d=bank_level_config(session,level); loan=d.setdefault("loan",{})
            text=(f"💳 <b>تنظیمات وام — سطح ۱ (ساخت)</b>\n\n"
                  f"💰 مبلغ: <b>{float(loan.get('min_amount',0) or 0):,.0f} تا {float(loan.get('max_amount',0) or 0):,.0f}</b>\n"
                  f"📈 سود: <b>{float(loan.get('min_interest_percent',0) or 0):g}% تا {float(loan.get('max_interest_percent',0) or 0):g}%</b>\n"
                  f"🧾 اقساط: <b>{int(loan.get('min_installments',1) or 1)} تا {int(loan.get('max_installments',1) or 1)}</b>\n"
                  
                  f"👥 حداکثر وام فعال همزمان: <b>{int(loan.get('max_active_loans',1) or 1)}</b>")
            await query.answer(); await query.edit_message_text(text,parse_mode="HTML",reply_markup=bank_loans_settings_keyboard(1,build=True,loan=loan)); return

        if action == "bank_loan_settings" and len(parts)>=3:
            level=int(parts[2]); build_mode=(len(parts)>=4 and parts[3]=="1"); d=bank_level_config(session,level); loan=d.setdefault("loan",{})
            text=(f"💳 <b>تنظیمات وام — سطح {level}</b>\n\n"
                  f"💰 مبلغ: <b>{float(loan.get('min_amount',0) or 0):,.0f} تا {float(loan.get('max_amount',0) or 0):,.0f}</b>\n"
                  f"📈 سود: <b>{float(loan.get('min_interest_percent',0) or 0):g}% تا {float(loan.get('max_interest_percent',0) or 0):g}%</b>\n"
                  f"🧾 اقساط: <b>{int(loan.get('min_installments',1) or 1)} تا {int(loan.get('max_installments',1) or 1)}</b>\n"
                  
                  f"👥 حداکثر وام فعال همزمان: <b>{int(loan.get('max_active_loans',1) or 1)}</b>")
            await query.answer(); await query.edit_message_text(text,parse_mode="HTML",reply_markup=bank_loans_settings_keyboard(level, build=build_mode, loan=loan)); return

        if action == "bank_build_loan_edit" and len(parts)>=3 and parts[2] in {"amount_range","interest_range","installments_range"}:
            kind=parts[2].replace("_range","")
            d=bank_level_config(session,1); loan=d.setdefault("loan",{})
            if kind=="amount": summary=f"حداقل مبلغ: <b>{float(loan.get('min_amount',0) or 0):,.0f}</b>\nحداکثر مبلغ: <b>{float(loan.get('max_amount',0) or 0):,.0f}</b>"
            elif kind=="interest": summary=f"حداقل سود: <b>{float(loan.get('min_interest_percent',0) or 0):g}%</b>\nحداکثر سود: <b>{float(loan.get('max_interest_percent',0) or 0):g}%</b>"
            else: summary=f"حداقل اقساط: <b>{int(loan.get('min_installments',1) or 1)}</b>\nحداکثر اقساط: <b>{int(loan.get('max_installments',1) or 1)}</b>"
            await query.answer(); await query.edit_message_text(f"💳 <b>تنظیم محدوده وام — سطح ۱</b>\n\n{summary}\n\nمقدار موردنظر را برای ویرایش انتخاب کنید.",parse_mode="HTML",reply_markup=bank_loan_range_keyboard(1,True,kind)); return

        if action == "bank_build_loan_edit" and len(parts)>=3:
            field=parts[2]; level=1; d=bank_level_config(session,level); loan=d.setdefault("loan",{}); current=loan.get(field,0)
            context.user_data["economy_pending"]={"building":"bank","type":"bank_level_loan","level":level,"field":field,"current_value":current,"back_callback":"owner:bank_build_loan_settings","prompt_message_id":int(query.message.message_id),"prompt_chat_id":int(query.message.chat_id)}
            context.user_data[_waiting_scope_key("economy_pending")]=int(update.effective_chat.id)
            labels={"min_amount":"حداقل مبلغ وام","max_amount":"حداکثر مبلغ وام","min_interest_percent":"حداقل سود وام (%)","max_interest_percent":"حداکثر سود وام (%)","min_installments":"حداقل تعداد اقساط","max_installments":"حداکثر تعداد اقساط","max_active_loans":"حداکثر وام فعال همزمان","bank_unlock_cost":"هزینه بازگشایی بانک"}
            await query.answer(); await query.edit_message_text(f"💳 <b>{labels.get(field,field)}</b>\n\nمقدار فعلی: <b>{float(current or 0):,.2f}</b>\n\nمقدار جدید را ارسال کنید.",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="owner:bank_build_loan_settings")]])); return

        if action == "bank_loan_edit" and len(parts)>=4 and parts[3] in {"amount_range","interest_range","installments_range"}:
            level=int(parts[2]); kind=parts[3].replace("_range","")
            loan=d.setdefault("loan",{})
            if kind=="amount": summary=f"حداقل: <b>{float(loan.get('min_amount',0) or 0):,.0f}</b>\nحداکثر: <b>{float(loan.get('max_amount',0) or 0):,.0f}</b>"
            elif kind=="interest": summary=f"حداقل سود: <b>{float(loan.get('min_interest_percent',0) or 0):g}%</b>\nحداکثر سود: <b>{float(loan.get('max_interest_percent',0) or 0):g}%</b>"
            else: summary=f"حداقل اقساط: <b>{int(loan.get('min_installments',1) or 1)}</b>\nحداکثر اقساط: <b>{int(loan.get('max_installments',1) or 1)}</b>"
            await query.answer(); await query.edit_message_text(f"💳 <b>تنظیم محدوده وام — سطح {level}</b>\n\n{summary}\n\nمقدار موردنظر را برای ویرایش انتخاب کنید.",parse_mode="HTML",reply_markup=bank_loan_range_keyboard(level,False,kind)); return

        if action == "bank_loan_edit" and len(parts)>=4:
            level=int(parts[2]); field=parts[3]; d=bank_level_config(session,level); loan=d.setdefault("loan",{}); current=loan.get(field,0)
            context.user_data["economy_pending"]={"building":"bank","type":"bank_level_loan","level":level,"field":field,"current_value":current,"back_callback":f"owner:bank_loan_settings:{level}","prompt_message_id":int(query.message.message_id),"prompt_chat_id":int(query.message.chat_id)}
            context.user_data[_waiting_scope_key("economy_pending")]=int(update.effective_chat.id)
            labels={"min_amount":"حداقل مبلغ وام","max_amount":"حداکثر مبلغ وام","min_interest_percent":"حداقل سود وام (%)","max_interest_percent":"حداکثر سود وام (%)","min_installments":"حداقل تعداد اقساط","max_installments":"حداکثر تعداد اقساط","max_active_loans":"حداکثر وام فعال همزمان","bank_unlock_cost":"هزینه بازگشایی بانک"}
            await query.answer(); await query.edit_message_text(f"💳 <b>{labels.get(field,field)} — سطح {level}</b>\n\nمقدار فعلی: <b>{float(current or 0):,.2f}</b>\n\nمقدار جدید را ارسال کنید.",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data=f"owner:bank_loan_settings:{level}")]])); return

        if action == "bank_tax_settings" and len(parts)>=3:
            level=int(parts[2]); build_mode=(len(parts)>=4 and parts[3]=="1"); d=bank_level_config(session,level)
            text=(f"🧾 <b>تنظیمات مالیات — سطح {level}</b>\n\n"
                  f"⬇️ حداقل مالیات به ازای هر ۱۰۰۰ شهروند: <b>{float(d.get('tax_min',0) or 0):,.0f}</b>\n"
                  f"⬆️ حداکثر مالیات به ازای هر ۱۰۰۰ شهروند: <b>{float(d.get('tax_max',0) or 0):,.0f}</b>\n\n"
                  "مقدار مالیات انتخابی کاربر باید داخل این محدوده باشد.")
            await query.answer(); await query.edit_message_text(text,parse_mode="HTML",reply_markup=bank_tax_settings_keyboard(level,build=build_mode)); return

        if action == "bank_deposit_settings" and len(parts)>=3:
            level=int(parts[2]); build_mode=(len(parts)>=4 and parts[3]=="1"); d=bank_level_config(session,level)
            text=(f"🏦 <b>تنظیمات سپرده — سطح {level}</b>\n\n"
                  f"📦 حداکثر سپرده: <b>{float(d.get('deposit_capacity',0) or 0):,.0f}</b>\n"
                  f"📈 سود سپرده در ساعت: <b>{float(d.get('deposit_hourly_profit_percent',0) or 0):g}%</b>\n\n"
                  "حداکثر سپرده، ظرفیت کل مخزن سپرده است. ")
            await query.answer(); await query.edit_message_text(text,parse_mode="HTML",reply_markup=bank_deposit_settings_keyboard(level,build=build_mode)); return

        if action == "bank_level_edit" and len(parts)>=3:
            level=int(parts[2]); d=bank_level_config(session,level)
            if level <= 1:
                await query.answer("❌ سطح ۱ از بخش تنظیم سطوح قابل ویرایش نیست؛ تنظیمات آن داخل بخش ساخت بانک مرکزی است.",show_alert=True); return
            text=(f"⬆️ <b>بانک مرکزی — سطح {level}</b>\n\n"
                  f"📋 <b>مشخصات پایه سطح {level}</b>\n"
                  f"🏛️ سطح مرکز فرماندهی مورد نیاز: <b>{int(d.get('required_hq_level',1) or 1)}</b>\n"
                  f"⏱️ زمان ارتقا: <b>{float(d.get('upgrade_time_hours',0) or 0):g} ساعت</b>\n\n"
                  "برای تغییر هزینه یا هر تنظیم، وارد بخش مربوط به خودش شوید.")
            await query.answer(); await query.edit_message_text(text,parse_mode="HTML",reply_markup=bank_level_edit_keyboard(level)); return
        if action == "bank_level_costs" and len(parts)>=3:
            level=int(parts[2]); d=bank_level_config(session,level); costs=d.get("build_cost" if level<=1 else "upgrade_cost",{}) or {}
            await query.answer(); await query.edit_message_text(
                f"💰 <b>هزینه‌ها — سطح {level}</b>\n\n"
                f"💰 پول فعلی: <b>{float(costs.get('money',0) or 0):,.0f}</b>\n"
                f"🔩 فلز فعلی: <b>{float(costs.get('metal',0) or 0):,.0f}</b>\n"
                f"⛽ سوخت فعلی: <b>{float(costs.get('fuel',0) or 0):,.0f}</b>\n"
                f"☢️ اورانیوم فعلی: <b>{float(costs.get('uranium',0) or 0):,.2f}</b>\n\nگزینه موردنظر را برای ویرایش انتخاب کنید:",parse_mode="HTML",reply_markup=bank_level_costs_keyboard(level)); return

        if action == "bank_edit" and len(parts)>=4:
            level=int(parts[2]); field=":".join(parts[3:]); edit_mode=parts[5] if len(parts)>=6 and parts[4]=="investment" else "0"; cfg=get_bank_config(session); d=cfg["levels"].get(str(level));
            if not d: await query.answer("❌ سطح نامعتبر است.",show_alert=True); return
            # callbackهای هزینه به شکل owner:bank_edit:<level>:upgrade_cost:money
            # یا owner:bank_edit:<level>:build_cost:metal هستند؛ بنابراین field
            # باید از تمام قطعات بعد از level ساخته شود، نه فقط parts[3].
            if field.startswith(("upgrade_cost:", "build_cost:")):
                group,key=field.split(":",1)
                bucket=d.get(group) or {}
                if not isinstance(bucket, dict):
                    bucket={}
                    d[group]=bucket
                current=float(bucket.get(key,0) or 0)
            else:
                key=field
                raw_current=d.get(key,0)
                if isinstance(raw_current, dict):
                    await query.answer("❌ گزینه تنظیم نامعتبر است.",show_alert=True); return
                current=float(raw_current or 0)
            level_back = f"owner:bank_level_costs:{level}" if field.startswith(("build_cost:","upgrade_cost:")) else (f"owner:bank_deposit_settings:{level}:0" if field in {"deposit_capacity","deposit_hourly_profit_percent"} else (f"owner:bank_tax_settings:{level}:0" if field in {"tax_min","tax_max"} else f"owner:bank_level_settings:{level}:0"))
            context.user_data["economy_pending"]={"building":"bank","type":"level","level":level,"field":field,"current_value":current,"back_callback":level_back,"prompt_message_id":int(query.message.message_id),"prompt_chat_id":int(query.message.chat_id)}; context.user_data[_waiting_scope_key("economy_pending")]=int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text(f"✏️ <b>ویرایش سطح {level}</b>\n\nمقدار فعلی: <b>{current:,.2f}</b>\n\nمقدار جدید را ارسال کنید.",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data=level_back)]])); return

        if action == "bank_level" and len(parts)>=3:
            level=int(parts[2]); d=bank_level_config(session,level)
            loan=d.get("loan",{}) or {}
            costs=d.get("build_cost" if level<=1 else "upgrade_cost",{}) or {}
            time_key="build_time_hours" if level<=1 else "upgrade_time_hours"
            op="ساخت" if level<=1 else "ارتقا"
            text=(f"{'🏗️' if level<=1 else '⬆️'} <b>بانک مرکزی — سطح {level}</b>\n\n"
                  f"📋 <b>مشخصات دقیق این سطح</b>\n"
                  f"🏛️ سطح مرکز فرماندهی مورد نیاز: <b>{int(d.get('required_hq_level',1) or 1)}</b>\n"
                  f"⏱️ زمان {op}: <b>{float(d.get(time_key,0) or 0):g} ساعت</b>\n"
                  f"\nهر بخش تنظیمات، مشخصات مربوط به خودش را در پنل اختصاصی همان بخش نمایش می‌دهد.")
            await query.answer(); await query.edit_message_text(text,parse_mode="HTML",reply_markup=bank_level_edit_keyboard(level)); return

        if action == "missiles_instant_finish_rate":
            cfg=get_missiles_config(session) or {}; items=cfg.get("items",[]) or []; current=float(items[0].get("instant_finish_uranium_per_hour",0) or 0) if items else 0.0
            context.user_data["economy_pending"]={"building":"all_missiles","type":"instant_finish_rate","back_callback":"owner:missiles","current_value":current,"prompt_message_id":int(query.message.message_id),"prompt_chat_id":int(query.message.chat_id)}
            context.user_data[_waiting_scope_key("economy_pending")]=int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text(f"☢️ <b>اورانیوم تکمیل فوری همه موشک‌ها</b>\n\nمقدار فعلی: <b>{current:,.2f}</b> اورانیوم در ساعت\n\nمقدار جدید را ارسال کنید.",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="owner:missiles")]])); return

        if action == "economy_arsenal":
            cfg = get_arsenal_config(session)
            text = (
                "🏭 <b>تنظیمات زرادخانه</b>\n\n"
                f"🔝 حداکثر سطح: <b>{cfg.get('max_level',100)}</b>\n"
                f"☢️ اورانیوم تکمیل فوری: <b>{float(cfg.get('instant_finish_uranium_per_hour',0) or 0):,.2f}</b> در ساعت\n"
            )
            await query.answer(); await query.edit_message_text(text, parse_mode="HTML", reply_markup=arsenal_economy_keyboard()); return

        if action == "arsenal_max_level":
            cfg=get_arsenal_config(session)
            context.user_data["economy_pending"]={"building":"arsenal","type":"max_level","back_callback":"owner:economy_arsenal","current_value":int(cfg.get("max_level",100)),"prompt_message_id":int(query.message.message_id),"prompt_chat_id":int(query.message.chat_id)}
            context.user_data[_waiting_scope_key("economy_pending")] = int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text(
                f"🔝 <b>حداکثر سطح زرادخانه</b>\n\nمقدار فعلی: <b>{cfg.get('max_level',100)}</b>\n\nیک عدد بین 2 تا 100 ارسال کنید.",
                parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="owner:economy_arsenal")]])); return

        if action == "arsenal_build":
            cfg=get_arsenal_config(session); b=cfg["build_cost"]
            text=("🏗 <b>ساخت زرادخانه</b>\n\n"
                  f"🏛️ سطح مرکز فرماندهی مورد نیاز: <b>{int(cfg.get('build_required_hq_level',1))}</b>\n"
                  f"🪖 قدرت نظامی: <b>{cfg.get('build_military_power',0):,.0f}</b>\n"
                  f"🛡️ استحکام: <b>{cfg.get('build_strength',0):,.0f}</b>\n"
                  f"📦 ظرفیت مخزن: <b>{cfg.get('build_storage_capacity',0):,.0f}</b>\n"
                  f"⏱️ زمان تکمیل: <b>{cfg.get('build_completion_time',0):,.0f} ساعت</b>\n\n💰 <b>هزینه‌ها:</b>\n"+
                  "\n".join(f"{ {'money':'💰 پول','metal':'🔩 فلز','fuel':'⛽ سوخت','uranium':'☢️ اورانیوم'}[k] }: <b>{v:,.2f}</b>" for k,v in b.items()))
            await query.answer(); await query.edit_message_text(text,parse_mode="HTML",reply_markup=arsenal_build_keyboard()); return

        if action == "arsenal_instant_finish_rate":
            cfg = get_arsenal_config(session)
            context.user_data["economy_pending"] = {"building":"arsenal","type":"arsenal_instant_finish_rate","back_callback":"owner:economy_arsenal","current_value":float(cfg.get("instant_finish_uranium_per_hour",0) or 0)}
            context.user_data[_waiting_scope_key("economy_pending")] = int(update.effective_chat.id)
            await query.answer()
            await query.edit_message_text(
                f"☢️ <b>اورانیوم تکمیل فوری زرادخانه</b>\n\nمقدار فعلی: <b>{float(cfg.get('instant_finish_uranium_per_hour',0)):,.2f}</b> اورانیوم در ساعت\n\nمقدار جدید را ارسال کنید.",
                parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="owner:arsenal_build")]])
            )
            return

        if action == "arsenal_build_costs":
            cfg=get_arsenal_config(session); b=cfg.get("build_cost",{})
            await query.answer(); await query.edit_message_text(
                "💰 <b>هزینه‌ها:</b>\n\n"
                f"💰 پول: <b>{float(b.get('money',0) or 0):,.0f}</b>\n🔩 فلز: <b>{float(b.get('metal',0) or 0):,.0f}</b>\n"
                f"⛽ سوخت: <b>{float(b.get('fuel',0) or 0):,.0f}</b>\n☢️ اورانیوم: <b>{float(b.get('uranium',0) or 0):,.2f}</b>\n\nمنبع موردنظر را انتخاب کنید:",parse_mode="HTML",reply_markup=arsenal_costs_keyboard(build=True)); return

        if action == "arsenal_build_edit":
            field=parts[2] if len(parts)>2 else ""
            if field not in {"money","metal","fuel","uranium","storage_capacity","military_power","strength","required_hq_level","completion_time", "completion_time"}:
                await query.answer("❌ گزینه نامعتبر است.",show_alert=True); return
            cfg=get_arsenal_config(session)
            current = float(cfg.get("build_cost",{}).get(field,0) or 0) if field in {"money","metal","fuel","uranium"} else float(cfg.get("build_"+field,0) or 0)
            context.user_data["economy_pending"]={"building":"arsenal","type":"build_cost" if field in {"money","metal","fuel","uranium"} else f"build_{field}","field":field,"back_callback":"owner:arsenal_build_costs" if field in {"money","metal","fuel","uranium"} else "owner:arsenal_build","current_value":current,"prompt_message_id":int(query.message.message_id),"prompt_chat_id":int(query.message.chat_id)}
            context.user_data[_waiting_scope_key("economy_pending")] = int(update.effective_chat.id)
            label={"money":"💰 پول","metal":"🔩 فلز","fuel":"⛽ سوخت","uranium":"☢️ اورانیوم","storage_capacity":"📦 ظرفیت مخزن","military_power":"🪖 قدرت نظامی","strength":"🛡️ استحکام","required_hq_level":"🏛️ سطح مرکز فرماندهی مورد نیاز","completion_time":"⏱️ زمان تکمیل"}[field]
            await query.answer(); await query.edit_message_text(
                f"✏️ <b>{label}</b>\n\nمقدار فعلی: <b>{current:,.2f}</b>\n\nمقدار جدید را به‌صورت عددی ارسال کنید.",
                parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data=context.user_data["economy_pending"]["back_callback"])] ])); return

        if action == "arsenal_levels":
            cfg=get_arsenal_config(session)
            await query.answer(); await query.edit_message_text("📊 <b>سطوح زرادخانه</b>\n\nسطح موردنظر را انتخاب کنید:",parse_mode="HTML",reply_markup=arsenal_level_keyboard(range(2,int(cfg.get("max_level",100))+1))); return

        if action == "arsenal_level":
            level=int(parts[2]); cfg=get_arsenal_config(session); data=cfg["levels"].get(level)
            if not data: await query.answer("❌ سطح نامعتبر است.",show_alert=True); return
            text=(f"🏭 <b>تنظیمات زرادخانه — سطح {level}</b>\n\n"
                  f"🏛️ سطح مرکز فرماندهی مورد نیاز: <b>{data.get('required_hq_level',level)}</b>\n"
                  f"🪖 قدرت نظامی: <b>{data['military_power']:,.0f}</b>\n"
                  f"🛡️ استحکام: <b>{data['strength']:,.0f}</b>\n"
                  f"📦 ظرفیت مخزن: <b>{data['storage_capacity']:,.0f}</b>\n"
                  f"⏱️ زمان تکمیل: <b>{data.get('completion_time',0):,.0f} ساعت</b>\n\n"
                  "💰 <b>هزینه‌ها:</b>\n"
                  f"💰 پول: <b>{data['money']:,.0f}</b>\n🔩 فلز: <b>{data['metal']:,.0f}</b>\n"
                  f"⛽ سوخت: <b>{data['fuel']:,.0f}</b>\n☢️ اورانیوم: <b>{data['uranium']:,.2f}</b>")
            await query.answer(); await query.edit_message_text(text,parse_mode="HTML",reply_markup=arsenal_level_edit_keyboard(level)); return

        if action == "arsenal_level_costs":
            level=int(parts[2]); cfg=get_arsenal_config(session); data=cfg.get("levels",{}).get(level,{})
            await query.answer(); await query.edit_message_text(f"💰 <b>هزینه‌ها — سطح {level}</b>\n\n🏛️ سطح مرکز فرماندهی مورد نیاز: <b>{int(data.get('required_hq_level',level))}</b>\n💰 پول: <b>{float(data.get('money',0) or 0):,.0f}</b>\n🔩 فلز: <b>{float(data.get('metal',0) or 0):,.0f}</b>\n⛽ سوخت: <b>{float(data.get('fuel',0) or 0):,.0f}</b>\n☢️ اورانیوم: <b>{float(data.get('uranium',0) or 0):,.2f}</b>\n\nمنبع موردنظر را انتخاب کنید:",parse_mode="HTML",reply_markup=arsenal_costs_keyboard(level=level)); return

        if action == "arsenal_edit":
            level=int(parts[2]); field=parts[3]
            if field not in {"money","metal","fuel","uranium","storage_capacity","military_power","strength","required_hq_level","completion_time", "completion_time"}:
                await query.answer("❌ گزینه نامعتبر است.",show_alert=True); return
            cfg=get_arsenal_config(session); current=float(cfg.get("levels",{}).get(level,{}).get(field,0) or 0)
            context.user_data["economy_pending"]={"building":"arsenal","type":"level","level":level,"field":field,"back_callback":f"owner:arsenal_level:{level}","current_value":current,"prompt_message_id":int(query.message.message_id),"prompt_chat_id":int(query.message.chat_id)}
            context.user_data[_waiting_scope_key("economy_pending")] = int(update.effective_chat.id)
            label={"money":"💰 پول","metal":"🔩 فلز","fuel":"⛽ سوخت","uranium":"☢️ اورانیوم","storage_capacity":"📦 ظرفیت مخزن","military_power":"🪖 قدرت نظامی","strength":"🛡️ استحکام","required_hq_level":"🏛️ سطح مرکز فرماندهی مورد نیاز","completion_time":"⏱️ زمان تکمیل"}[field]
            await query.answer(); await query.edit_message_text(
                f"✏️ <b>{label}</b>\n\nمقدار فعلی: <b>{current:,.2f}</b>\n\nمقدار جدید را به‌صورت عددی ارسال کنید.",
                parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data=f"owner:arsenal_level:{level}")]])); return

        if action == "economy_hq":
            if not is_owner(query.from_user.id, OWNER_ID):
                await query.answer("⛔ این بخش فقط برای مالک است.", show_alert=True); return
            cfg=get_hq_config(session)
            await query.answer(); await query.edit_message_text(
                f"🏛️ <b>تنظیمات مرکز فرماندهی</b>\n\n🔝 حداکثر سطح: <b>{cfg.get('max_level',100)}</b>\n☢️ اورانیوم تکمیل فوری: <b>{float(cfg.get('instant_finish_uranium_per_hour',0) or 0):,.2f}</b> در ساعت",
                parse_mode="HTML", reply_markup=hq_economy_keyboard()); return

        if action == "hq_build":
            cfg=get_hq_config(session); b=cfg.get("build_cost",{})
            lines=[f"💰 پول: <b>{float(b.get('money',0)):,.0f}</b>", f"🔩 فلز: <b>{float(b.get('metal',0)):,.0f}</b>", f"⛽ سوخت: <b>{float(b.get('fuel',0)):,.0f}</b>"]
            uranium=float(b.get('uranium',0))
            lines.append(f"☢️ اورانیوم: <b>{uranium:,.2f}</b>")
            rows=[[InlineKeyboardButton("🪖 قدرت نظامی",callback_data="owner:hq_build_military_power")],
[InlineKeyboardButton("🛡️ استحکام",callback_data="owner:hq_build_strength")],
[InlineKeyboardButton("⏱️ زمان تکمیل",callback_data="owner:hq_build_completion_time")],
[InlineKeyboardButton("💰 هزینه‌ها",callback_data="owner:hq_build_costs")],
[InlineKeyboardButton("🔙 برگشت",callback_data="owner:economy_hq")]]
            await query.answer(); await query.edit_message_text("🏗️ <b>ساخت مرکز فرماندهی</b>\n\n📋 <b>مشخصات سطح ۱</b>\n"+f"🪖 قدرت نظامی: <b>{float(cfg.get('build_military_power',0)):,.0f}</b>\n"+f"🛡️ استحکام: <b>{float(cfg.get('build_strength',0)):,.0f}</b>\n"+f"⏱️ زمان تکمیل: <b>{float(cfg.get('build_completion_time',0)):,.0f} ساعت</b>\n\n💰 <b>هزینه‌ها:</b>\n"+"\n".join(lines),parse_mode="HTML",reply_markup=InlineKeyboardMarkup(rows)); return
        if action == "hq_build_costs":
            cfg=get_hq_config(session); uranium=float(cfg.get('build_cost',{}).get('uranium',0))
            rows=[[InlineKeyboardButton("💰 پول",callback_data="owner:hq_build_edit:money")],[InlineKeyboardButton("🔩 فلز",callback_data="owner:hq_build_edit:metal")],[InlineKeyboardButton("⛽ سوخت",callback_data="owner:hq_build_edit:fuel")]]
            rows.append([InlineKeyboardButton("☢️ اورانیوم",callback_data="owner:hq_build_edit:uranium")])
            rows.append([InlineKeyboardButton("🔙 برگشت",callback_data="owner:hq_build")])
            await query.answer(); await query.edit_message_text("💰 <b>هزینه‌ها:</b>\n\n" + "\n".join([f"💰 پول: <b>{float(cfg.get('build_cost',{}).get('money',0) or 0):,.0f}</b>", f"🔩 فلز: <b>{float(cfg.get('build_cost',{}).get('metal',0) or 0):,.0f}</b>", f"⛽ سوخت: <b>{float(cfg.get('build_cost',{}).get('fuel',0) or 0):,.0f}</b>", f"☢️ اورانیوم: <b>{float(cfg.get('build_cost',{}).get('uranium',0) or 0):,.2f}</b>"]) + "\n\nمنبع موردنظر را انتخاب کنید:",parse_mode="HTML",reply_markup=InlineKeyboardMarkup(rows)); return
        if action == "hq_build_completion_time":
            cfg=get_hq_config(session)
            context.user_data["economy_pending"]={"building":"hq","type":"build_completion_time","back_callback":"owner:hq_build","current_value":float(cfg.get("build_completion_time",0) or 0),"prompt_message_id":int(query.message.message_id),"prompt_chat_id":int(query.message.chat_id)}
            context.user_data[_waiting_scope_key("economy_pending")] = int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text(f"✏️ زمان تکمیل ساخت را به‌صورت عددی ارسال کنید.\n\nمقدار فعلی: <b>{float(cfg.get('build_completion_time',0)):,.0f}</b> ساعت",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="owner:hq_build")]])); return

        if action == "hq_build_military_power":
            cfg=get_hq_config(session); current=float(cfg.get("build_military_power",0) or 0)
            context.user_data["economy_pending"]={"building":"hq","type":"build_military_power","back_callback":"owner:hq_build","current_value":current,"prompt_message_id":int(query.message.message_id),"prompt_chat_id":int(query.message.chat_id)}
            context.user_data[_waiting_scope_key("economy_pending")] = int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text("✏️ <b>قدرت نظامی ساخت</b>\n\nمقدار فعلی: <b>{:,.0f}</b>\n\nمقدار جدید را ارسال کنید.".format(current),parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="owner:hq_build")]])); return
        if action == "hq_build_strength":
            cfg=get_hq_config(session); current=float(cfg.get("build_strength",0) or 0)
            context.user_data["economy_pending"]={"building":"hq","type":"build_strength","back_callback":"owner:hq_build","current_value":current,"prompt_message_id":int(query.message.message_id),"prompt_chat_id":int(query.message.chat_id)}
            context.user_data[_waiting_scope_key("economy_pending")] = int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text("✏️ <b>استحکام ساخت</b>\n\nمقدار فعلی: <b>{:,.0f}</b>\n\nمقدار جدید را ارسال کنید.".format(current),parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="owner:hq_build")]])); return
        if action == "hq_build_edit" and len(parts)>=3:
            field=parts[2]
            cfg=get_hq_config(session); current=float(cfg.get("build_cost",{}).get(field,0) or 0)
            context.user_data["economy_pending"]={"building":"hq","type":"build_cost","field":field,"back_callback":"owner:hq_build_costs","current_value":current,"prompt_message_id":int(query.message.message_id),"prompt_chat_id":int(query.message.chat_id)}
            context.user_data[_waiting_scope_key("economy_pending")] = int(update.effective_chat.id)
            label={"money":"💰 پول","metal":"🔩 فلز","fuel":"⛽ سوخت","uranium":"☢️ اورانیوم"}[field]
            await query.answer(); await query.edit_message_text(
                f"✏️ <b>{label}</b>\n\nمقدار فعلی: <b>{current:,.2f}</b>\n\nمقدار جدید را ارسال کنید.",
                parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="owner:hq_build_costs")]])); return

        if action == "hq_instant_finish_rate":
            cfg=get_hq_config(session)
            context.user_data["economy_pending"]={"building":"hq","type":"hq_instant_finish_rate","back_callback":"owner:economy_hq","current_value":float(cfg.get("instant_finish_uranium_per_hour",0) or 0),"prompt_message_id":int(query.message.message_id),"prompt_chat_id":int(query.message.chat_id)}
            context.user_data[_waiting_scope_key("economy_pending")] = int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text(
                f"☢️ <b>اورانیوم تکمیل فوری مرکز فرماندهی</b>\n\nمقدار فعلی: <b>{float(cfg.get('instant_finish_uranium_per_hour',0)):,.2f}</b> اورانیوم در ساعت\n\nمقدار جدید را ارسال کنید.",
                parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="owner:economy_hq")]])); return

        if action == "hq_max_level":
            cfg=get_hq_config(session); context.user_data["economy_pending"]={"building":"hq","type":"max_level","back_callback":"owner:economy_hq","current_value":int(cfg.get("max_level",100)),"prompt_message_id":int(query.message.message_id),"prompt_chat_id":int(query.message.chat_id)}
            context.user_data[_waiting_scope_key("economy_pending")] = int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text(f"🔝 <b>حداکثر سطح مرکز فرماندهی</b>\n\nمقدار فعلی: <b>{cfg.get('max_level',100)}</b>\n\nیک عدد بین 1 تا 100 ارسال کنید.",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="owner:economy_hq")]])); return

        if action == "hq_levels":
            cfg=get_hq_config(session); await query.answer(); await query.edit_message_text("📊 <b>سطوح مرکز فرماندهی</b>\n\nسطح موردنظر را انتخاب کنید:",parse_mode="HTML",reply_markup=hq_level_keyboard(range(2,int(cfg.get('max_level',100))+1))); return

        if action == "hq_level":
            level=int(parts[2]); cfg=get_hq_config(session); data=cfg.get("levels",{}).get(level)
            if not data: await query.answer("❌ سطح نامعتبر است.",show_alert=True); return
            text=(f"🏛️ <b>مرکز فرماندهی — سطح {level}</b>\n\n"
                  f"🪖 قدرت نظامی: <b>{data.get('military_power',0):,.0f}</b>\n🛡️ استحکام: <b>{data.get('strength',0):,.0f}</b>\n"
                  f"⏱️ زمان تکمیل: <b>{data.get('completion_time',0):,.0f} ساعت</b>\n\n"
                  "💰 <b>هزینه‌ها:</b>\n"
                  f"💰 پول: <b>{data.get('money',0):,.0f}</b>\n🔩 فلز: <b>{data.get('metal',0):,.0f}</b>\n"
                  f"⛽ سوخت: <b>{data.get('fuel',0):,.0f}</b>\n☢️ اورانیوم: <b>{data.get('uranium',0):,.2f}</b>")
            await query.answer(); await query.edit_message_text(text,parse_mode="HTML",reply_markup=hq_level_edit_keyboard(level)); return

        if action == "hq_level_costs":
            level=int(parts[2]); await query.answer(); await query.edit_message_text(f"💰 <b>هزینه‌های مرکز فرماندهی — سطح {level}</b>\n\nمنبع موردنظر را انتخاب کنید:",parse_mode="HTML",reply_markup=hq_costs_keyboard(level)); return

        if action == "hq_edit":
            level=int(parts[2]); field=parts[3]
            if field not in {"money","metal","fuel","uranium","strength","military_power","completion_time"}: await query.answer("❌ گزینه نامعتبر است.",show_alert=True); return
            cfg=get_hq_config(session); current=float(cfg.get("levels",{}).get(level,{}).get(field,0) or 0)
            context.user_data["economy_pending"]={"building":"hq","type":"level","level":level,"field":field,"back_callback":f"owner:hq_level:{level}","current_value":current,"prompt_message_id":int(query.message.message_id),"prompt_chat_id":int(query.message.chat_id)}
            context.user_data[_waiting_scope_key("economy_pending")] = int(update.effective_chat.id)
            label={"money":"💰 پول","metal":"🔩 فلز","fuel":"⛽ سوخت","uranium":"☢️ اورانیوم","strength":"🛡️ استحکام","military_power":"🪖 قدرت نظامی","completion_time":"⏱️ زمان تکمیل"}[field]
            await query.answer(); await query.edit_message_text(
                f"✏️ <b>{label}</b>\n\nمقدار فعلی: <b>{current:,.2f}</b>\n\nمقدار جدید را به‌صورت عددی ارسال کنید.",
                parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data=f"owner:hq_level:{level}")]])); return

        if action == "exchange_settings":
            context.user_data.pop("exchange_rate_pending", None)
            rates=get_exchange_rates(session)
            names={"money_to_metal":"🛒 خرید فلز در برابر پول","money_to_fuel":"🛒 خرید سوخت در برابر پول","metal_to_money":"💰 فروش فلز در برابر پول","fuel_to_money":"💰 فروش سوخت در برابر پول","uranium_to_fuel":"☢️ فروش اورانیوم در برابر سوخت","uranium_to_money":"☢️ فروش اورانیوم در برابر پول"}
            keys=list(names)
            rows=[]
            for i in range(0,len(keys),2):
                rows.append([InlineKeyboardButton(names[k],callback_data=f"owner:exchange_rate:{k}") for k in keys[i:i+2]])
            rows.append([InlineKeyboardButton("✏️ تنظیم متن تبادل",callback_data="owner:exchange_text")])
            rows.append([InlineKeyboardButton("🔙 برگشت",callback_data="owner:economy")])
            await query.answer(); await query.edit_message_text("💱 <b>تنظیم نرخ تمام تبادل‌ها</b>\n\nنرخ موردنظر را انتخاب کنید:",parse_mode="HTML",reply_markup=InlineKeyboardMarkup(rows)); return
        if action == "exchange_text":
            context.user_data["exchange_text_pending"] = True
            context.user_data[_waiting_scope_key("exchange_text_pending")] = int(update.effective_chat.id)
            context.user_data["exchange_text_prompt"] = {"chat_id": int(query.message.chat_id), "message_id": int(query.message.message_id)}
            await query.answer(); await query.edit_message_text(
                f"✏️ <b>تنظیم متن تبادل</b>\n\nمتن فعلی:\n{get_exchange_text(session)}\n\nمتن جدید را کامل ارسال کنید.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="owner:exchange_settings")]])
            ); return
        if action == "exchange_text_confirm":
            pending = context.user_data.get("exchange_text_draft")
            if not pending:
                await query.answer("⚠️ متنی برای تأیید وجود ندارد.", show_alert=True); return
            save_exchange_text(session, pending)
            session.commit(); context.user_data.pop("exchange_text_draft", None); context.user_data.pop("exchange_text_pending", None); context.user_data.pop("exchange_text_prompt", None)
            await query.answer("✅ متن تبادل ذخیره شد.", show_alert=True)
            rates=get_exchange_rates(session); names={"money_to_metal":"🛒 خرید فلز در برابر پول","money_to_fuel":"🛒 خرید سوخت در برابر پول","metal_to_money":"💰 فروش فلز در برابر پول","fuel_to_money":"💰 فروش سوخت در برابر پول","uranium_to_fuel":"☢️ فروش اورانیوم در برابر سوخت","uranium_to_money":"☢️ فروش اورانیوم در برابر پول"}; keys=list(names); rows=[[InlineKeyboardButton(names[k],callback_data=f"owner:exchange_rate:{k}") for k in keys[i:i+2]] for i in range(0,len(keys),2)]; rows += [[InlineKeyboardButton("✏️ تنظیم متن تبادل",callback_data="owner:exchange_text")],[InlineKeyboardButton("🔙 برگشت",callback_data="owner:economy")]]
            await query.edit_message_text("💱 <b>تنظیم نرخ تمام تبادل‌ها</b>\n\nنرخ موردنظر را انتخاب کنید:", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(rows)); return
        if action == "exchange_text_edit":
            context.user_data["exchange_text_pending"] = True; context.user_data.pop("exchange_text_draft", None)
            context.user_data[_waiting_scope_key("exchange_text_pending")] = int(update.effective_chat.id)
            context.user_data["exchange_text_prompt"] = {"chat_id": int(query.message.chat_id), "message_id": int(query.message.message_id)}
            await query.answer(); await query.edit_message_text("✏️ متن کامل جدید را ارسال کنید.", parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="owner:exchange_settings")]])); return
        if action == "exchange_text_cancel":
            context.user_data.pop("exchange_text_draft", None); context.user_data.pop("exchange_text_pending", None); context.user_data.pop("exchange_text_prompt", None)
            await query.answer("❌ تغییر متن لغو شد.")
            await query.edit_message_text("💱 <b>تنظیم نرخ تمام تبادل‌ها</b>\n\nنرخ موردنظر را انتخاب کنید:", parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="owner:economy")]])); return
        if action == "exchange_rate" and len(parts)>=3:
            key=parts[2]; rates=get_exchange_rates(session)
            if key not in rates: await query.answer("❌ نوع تبادل نامعتبر است.",show_alert=True); return
            r=rates[key]
            context.user_data["exchange_rate_pending"]={"key":key,"step":1,"prompt_chat_id":int(query.message.chat_id),"prompt_message_id":int(query.message.message_id)}
            context.user_data[_waiting_scope_key("exchange_rate_pending")] = int(update.effective_chat.id)
            resource_names={"money":"💰 پول","metal":"🔩 فلز","fuel":"⛽ سوخت","uranium":"☢️ اورانیوم"}
            await query.answer(); await query.edit_message_text(
                f"💱 <b>{r['title']}</b>\n\n"
                f"مقدار {resource_names[r['from_resource']]} را ارسال کنید.\n\n"
                f"مقدار فعلی: <b>{r['input_unit']:,.0f}</b>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="owner:exchange_settings")]])
            ); return

        if action == "buildings_instant_finish_rate":
            cfg=get_hq_config(session); current=float(cfg.get("instant_finish_uranium_per_hour",0) or 0)
            context.user_data["economy_pending"]={"building":"all_buildings","type":"instant_finish_rate","back_callback":"owner:buildings","current_value":current,"prompt_message_id":int(query.message.message_id),"prompt_chat_id":int(query.message.chat_id)}
            context.user_data[_waiting_scope_key("economy_pending")]=int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text(f"☢️ <b>اورانیوم تکمیل فوری همه ساختمان‌ها</b>\n\nمقدار فعلی: <b>{current:,.2f}</b> اورانیوم در ساعت\n\nمقدار جدید را ارسال کنید.",parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت",callback_data="owner:buildings")]])); return

        if action == "economy_metal_mine":
            cfg = get_metal_mine_config(session)
            build = cfg["build_cost"]
            levels = cfg["levels"]
            text = (
                "⛏️ <b>تنظیمات معدن فلز</b>\n\n"
                f"🔝 حداکثر سطح: <b>{cfg.get('max_level',100)}</b>\n"
                f"☢️ اورانیوم تکمیل فوری: <b>{float(cfg.get('instant_finish_uranium_per_hour',0) or 0):,.2f}</b> در ساعت\n"
            )
            await query.answer()
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=metal_mine_economy_keyboard())
            return

        if action == "mine_max_level":
            cfg = get_metal_mine_config(session)
            context.user_data["economy_pending"] = {"building":"mine","type": "max_level","current_value":int(cfg.get("max_level",100)),"prompt_message_id":int(query.message.message_id),"prompt_chat_id":int(query.message.chat_id)}
            context.user_data[_waiting_scope_key("economy_pending")] = int(update.effective_chat.id)
            await query.answer(); await query.edit_message_text(
                f"🔝 <b>حداکثر سطح معدن</b>\n\nمقدار فعلی: <b>{cfg.get('max_level',100)}</b>\n\nیک عدد بین 2 تا 100 ارسال کنید.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data="owner:economy_metal_mine")]])
            ); return

        if action == "mine_build_cost":
            cfg = get_metal_mine_config(session)
            b = cfg["build_cost"]
            uranium_build = float(cfg.get("build_cost_uranium", b.get("uranium", 0.0)))
            text = (
                f"🏗 <b>ساخت معدن فلز</b>\n\n"
                f"🏛️ سطح مرکز فرماندهی مورد نیاز: <b>{int(cfg.get('build_required_hq_level',1))}</b>\n"
                f"🪖 قدرت نظامی: <b>{cfg.get('build_military_power',0):,.0f}</b>\n"
                f"🛡️ استحکام: <b>{cfg.get('build_strength',0):,.0f}</b>\n"
                f"⚙️ تولید در ساعت ساخت: <b>{cfg.get('build_production_per_hour',0):,.0f}</b>\n"
                f"📦 ظرفیت مخزن: <b>{cfg.get('build_storage_capacity',0):,.0f}</b>\n"
                f"⏱️ زمان تکمیل: <b>{cfg.get('build_completion_time',0):,.0f} ساعت</b>\n\n"
                "💰 <b>هزینه‌ها:</b>\n"
                + "\n".join([
                    f"💰 پول: <b>{float(b.get('money',0)):,.0f}</b>",
                    f"🔩 فلز: <b>{float(b.get('metal',0)):,.0f}</b>",
                    f"⛽ سوخت: <b>{float(b.get('fuel',0)):,.0f}</b>",
                    f"☢️ اورانیوم: <b>{uranium_build:,.2f}</b>",
                ])
            )
            await query.answer()
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=metal_mine_build_cost_keyboard())
            return

        if action == "mine_build_costs":
            cfg = get_metal_mine_config(session)
            uranium_build = float(cfg.get("build_cost", {}).get("uranium", cfg.get("build_cost_uranium", 0)))
            await query.answer(); await query.edit_message_text("💰 <b>هزینه‌های ساخت</b>\n\nمنبع موردنظر را انتخاب کنید:", parse_mode="HTML", reply_markup=metal_mine_costs_keyboard(build=True, show_uranium=True)); return

        if action == "mine_level_costs":
            try: level = int(parts[2])
            except (IndexError, ValueError):
                await query.answer("❌ سطح نامعتبر است.", show_alert=True); return
            cfg = get_metal_mine_config(session); data=cfg.get("levels",{}).get(level,{})
            await query.answer(); await query.edit_message_text(f"💰 <b>هزینه‌ها — سطح {level}</b>\n\n🏛️ سطح مرکز فرماندهی مورد نیاز: <b>{int(data.get('required_hq_level',level))}</b>\n💰 پول: <b>{float(data.get('money',0) or 0):,.0f}</b>\n🔩 فلز: <b>{float(data.get('metal',0) or 0):,.0f}</b>\n⛽ سوخت: <b>{float(data.get('fuel',0) or 0):,.0f}</b>\n☢️ اورانیوم: <b>{float(data.get('uranium',0) or 0):,.2f}</b>\n\nمنبع موردنظر را انتخاب کنید:", parse_mode="HTML", reply_markup=metal_mine_costs_keyboard(level=level, show_uranium=True)); return

        if action == "mine_build":
            cfg = get_metal_mine_config(session)
            b = cfg["build_cost"]
            uranium_build = float(b.get('uranium', cfg.get('build_cost_uranium', 0.0)))
            text = (f"🏗 <b>ساخت معدن فلز</b>\n\n🏛️ سطح مرکز فرماندهی مورد نیاز: <b>{int(cfg.get('build_required_hq_level',1))}</b>\n🪖 قدرت نظامی: <b>{cfg.get('build_military_power',0):,.0f}</b>\n🛡️ استحکام: <b>{cfg.get('build_strength',0):,.0f}</b>\n⚙️ تولید در ساعت ساخت: <b>{cfg.get('build_production_per_hour',0):,.0f}</b>\n📦 ظرفیت مخزن: <b>{cfg.get('build_storage_capacity',0):,.0f}</b>\n⏱️ زمان تکمیل: <b>{cfg.get('build_completion_time',0):,.0f} ساعت</b>\n\n💰 <b>هزینه‌ها:</b>\n" + "\n".join([
                f"💰 پول: <b>{b.get('money',0):,.0f}</b>",
                f"🔩 فلز: <b>{b.get('metal',0):,.0f}</b>",
                f"⛽ سوخت: <b>{b.get('fuel',0):,.0f}</b>",
                f"☢️ اورانیوم: <b>{uranium_build:,.2f}</b>",
            ]))
            await query.answer(); await query.edit_message_text(text, parse_mode="HTML", reply_markup=metal_mine_build_cost_keyboard()); return

        if action == "mine_instant_finish_rate":
            cfg = get_metal_mine_config(session)
            context.user_data["economy_pending"] = {"building": "mine", "type": "mine_instant_finish_rate", "back_callback": "owner:economy_metal_mine","current_value":float(cfg.get("instant_finish_uranium_per_hour",0) or 0),"prompt_message_id":int(query.message.message_id),"prompt_chat_id":int(query.message.chat_id)}
            context.user_data[_waiting_scope_key("economy_pending")] = int(update.effective_chat.id)
            await query.answer()
            await query.edit_message_text(
                f"☢️ <b>اورانیوم تکمیل فوری معدن فلز</b>\n\nمقدار فعلی: <b>{float(cfg.get('instant_finish_uranium_per_hour', 0)):,.2f}</b> اورانیوم در ساعت\n\nمقدار جدید را ارسال کنید.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data="owner:economy_metal_mine")]])
            )
            return

        if action == "mine_build_edit":
            field = parts[2] if len(parts) > 2 else "money"
            if field not in {"money", "metal", "fuel", "uranium", "military_power", "strength", "production_per_hour", "storage_capacity", "completion_time", "required_hq_level"}:
                await query.answer("❌ گزینه نامعتبر است.", show_alert=True); return
            cfg = get_metal_mine_config(session)
            pending_type = ("build_required_hq_level" if field == "required_hq_level" else ("build_military" if field == "military_power" else ("build_strength" if field == "strength" else ("build_production" if field == "production_per_hour" else ("build_storage" if field == "storage_capacity" else ("build_completion_time" if field == "completion_time" else ("build_cost_uranium" if field == "uranium" else "build_cost")))))))
            current_value = (cfg.get('build_military_power',0) if field == 'military_power' else cfg.get('build_strength',0) if field == 'strength' else cfg.get('build_production_per_hour',0) if field == 'production_per_hour' else cfg.get('build_storage_capacity',0) if field == 'storage_capacity' else cfg.get('build_completion_time',0) if field == 'completion_time' else cfg.get('build_required_hq_level',1) if field == 'required_hq_level' else cfg.get('build_cost_uranium',0) if field == 'uranium' else cfg['build_cost'].get(field,0))
            context.user_data["economy_pending"] = {"type": pending_type, "field":field, "current_value":float(current_value or 0)}
            context.user_data[_waiting_scope_key("economy_pending")] = int(update.effective_chat.id)
            names = {"money":"💰 پول", "metal":"🔩 فلز", "fuel":"⛽ سوخت", "uranium":"☢️ اورانیوم", "military_power":"🪖 قدرت نظامی", "strength":"🛡️ استحکام", "production_per_hour":"⚙️ تولید در ساعت", "storage_capacity":"📦 ظرفیت مخزن", "completion_time":"⏱️ زمان تکمیل", "required_hq_level":"🏛️ سطح مرکز فرماندهی مورد نیاز", "completion_time":"⏱️ زمان تکمیل"}
            await query.answer()
            await query.edit_message_text(f"✏️ مقدار جدید {names[field]} را به‌صورت عددی ارسال کنید.\n\nمقدار فعلی: <b>{(cfg.get('build_military_power',0) if field == 'military_power' else cfg.get('build_strength',0) if field == 'strength' else cfg.get('build_production_per_hour',0) if field == 'production_per_hour' else cfg.get('build_storage_capacity',0) if field == 'storage_capacity' else cfg.get('build_completion_time',0) if field == 'completion_time' else cfg.get('build_required_hq_level',1) if field == 'required_hq_level' else cfg.get('build_cost_uranium',0) if field == 'uranium' else cfg['build_cost'].get(field,0)):,}</b>", parse_mode="HTML", reply_markup=metal_mine_build_cost_input_keyboard())
            return

        if action == "mine_levels":
            cfg = get_metal_mine_config(session)
            await query.answer()
            await query.edit_message_text("📊 <b>سطوح معدن فلز</b>\n\nسطح موردنظر را انتخاب کنید:", parse_mode="HTML", reply_markup=metal_mine_level_keyboard(sorted([lv for lv in cfg['levels'] if int(lv) <= int(cfg.get("max_level",100))])))
            return

        if action == "mine_level":
            try: level = int(parts[2])
            except (IndexError, ValueError):
                await query.answer("❌ سطح نامعتبر است.", show_alert=True); return
            cfg = get_metal_mine_config(session); data = cfg["levels"].get(level)
            if not data:
                await query.answer("❌ این سطح وجود ندارد.", show_alert=True); return
            text = (f"⛏️ <b>تنظیمات معدن — سطح {level}</b>\n\n"
                    f"🏛️ سطح مرکز فرماندهی مورد نیاز: <b>{int(data.get('required_hq_level', level))}</b>\n"
                    f"🪖 قدرت نظامی: <b>{data.get('military_power',0):,.0f}</b>\n🛡️ استحکام: <b>{data.get('strength',0):,.0f}</b>\n"
                    f"⚙️ تولید در ساعت: <b>{data['production_per_hour']:,.0f}</b>\n"
                    f"📦 ظرفیت مخزن: <b>{data['storage_capacity']:,.0f}</b>\n"
                    f"⏱️ زمان تکمیل: <b>{data.get('completion_time',0):,.0f} ساعت</b>\n\n"
                    "💰 <b>هزینه‌ها:</b>\n"
                    f"💰 پول: <b>{data['money']:,.0f}</b>\n"
                    f"🔩 فلز: <b>{data['metal']:,.0f}</b>\n"
                    f"⛽ سوخت: <b>{data['fuel']:,.0f}</b>\n"
                    f"☢️ اورانیوم: <b>{data.get('uranium',0):,.2f}</b>")
            await query.answer(); await query.edit_message_text(text, parse_mode="HTML", reply_markup=metal_mine_level_edit_keyboard(level, bool(data.get('active', True)))); return

        if action == "mine_level_noop":
            await query.answer()
            return

        if action == "mine_edit":
            try: level = int(parts[2]); field = parts[3]
            except (IndexError, ValueError):
                await query.answer("❌ گزینه نامعتبر است.", show_alert=True); return
            cfg = get_metal_mine_config(session)
            if level not in cfg["levels"] or field not in {"production_per_hour","storage_capacity","money","metal","fuel","uranium","military_power","strength","required_hq_level", "completion_time"}:
                await query.answer("❌ گزینه نامعتبر است.", show_alert=True); return
            context.user_data["economy_pending"] = {"building":"mine","type":"level", "level":level, "field":field, "current_value":float(cfg["levels"][level].get(field,0) or 0),"prompt_message_id":int(query.message.message_id),"prompt_chat_id":int(query.message.chat_id)}
            context.user_data[_waiting_scope_key("economy_pending")] = int(update.effective_chat.id)
            names={"production_per_hour":"⚙️ تولید در ساعت","storage_capacity":"📦 ظرفیت مخزن","money":"💰 هزینه پول","metal":"🔩 هزینه فلز","fuel":"⛽ هزینه سوخت","uranium":"☢️ هزینه اورانیوم","military_power":"🪖 قدرت نظامی", "strength":"🛡️ استحکام", "required_hq_level":"🏛️ سطح مرکز فرماندهی مورد نیاز", "completion_time":"⏱️ زمان تکمیل"}
            await query.answer(); await query.edit_message_text(
                f"✏️ مقدار جدید {names[field]} برای سطح {level} را ارسال کنید.\n\nمقدار فعلی: <b>{float(cfg['levels'][level].get(field, 0) or 0):,.0f}</b>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data=f"owner:mine_level:{level}")]])
            ); return

        # -------------------------------------------------
        # وضعیت ثبت شماره تلفن
        # -------------------------------------------------
        if action == "phone_status":
            ue = bool(get_setting(session, PHONE_USER_KEY, False))
            ae = bool(get_setting(session, PHONE_ADMIN_KEY, False))
            text = ("📱 <b>وضعیت ثبت شماره تلفن</b>\n\n"
                    f"👤 کاربران عادی: <b>{'فعال' if ue else 'غیرفعال'}</b>\n"
                    f"🛡 ادمین‌ها: <b>{'فعال' if ae else 'غیرفعال'}</b>\n"
                    f"👥 همه کاربران: <b>{'فعال' if ue and ae else 'غیرفعال'}</b>")
            await query.answer()
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=phone_status_keyboard(back_callback="owner:general_settings", user_enabled=ue, admin_enabled=ae))
            return

        if action == "phone_group":
            # callback قدیمی؛ مستقیماً به همان پنل واحد وضعیت تلفن برگرد.
            ue = bool(get_setting(session, PHONE_USER_KEY, False)); ae = bool(get_setting(session, PHONE_ADMIN_KEY, False))
            await query.answer()
            await query.edit_message_text("📱 <b>وضعیت ثبت شماره تلفن</b>\n\n"
                f"👤 کاربران عادی: <b>{'فعال' if ue else 'غیرفعال'}</b>\n"
                f"🛡 ادمین‌ها: <b>{'فعال' if ae else 'غیرفعال'}</b>\n"
                f"👥 همه کاربران: <b>{'فعال' if ue and ae else 'غیرفعال'}</b>", parse_mode="HTML",
                reply_markup=phone_status_keyboard(back_callback="owner:general_settings", user_enabled=ue, admin_enabled=ae))
            return

        if action == "phone_set":
            group = parts[2] if len(parts) > 2 else "all"
            token = parts[3] if len(parts) > 3 else "toggle"
            if token == "toggle":
                if group == "all":
                    enabled = not all_phone_enabled(session)
                    set_setting(session, PHONE_USER_KEY, enabled); set_setting(session, PHONE_ADMIN_KEY, enabled)
                elif group == "users":
                    enabled = not bool(get_setting(session, PHONE_USER_KEY, False)); set_setting(session, PHONE_USER_KEY, enabled)
                elif group == "admins":
                    enabled = not bool(get_setting(session, PHONE_ADMIN_KEY, False)); set_setting(session, PHONE_ADMIN_KEY, enabled)
            else:
                enabled = token == "1"
                if group == "all":
                    set_setting(session, PHONE_USER_KEY, enabled); set_setting(session, PHONE_ADMIN_KEY, enabled)
                elif group == "users": set_setting(session, PHONE_USER_KEY, enabled)
                elif group == "admins": set_setting(session, PHONE_ADMIN_KEY, enabled)
            session.commit()
            ue = bool(get_setting(session, PHONE_USER_KEY, False)); ae = bool(get_setting(session, PHONE_ADMIN_KEY, False))
            await query.answer("📱 وضعیت ثبت شماره تلفن به‌روزرسانی شد.", show_alert=True)
            await query.edit_message_text("📱 <b>وضعیت ثبت شماره تلفن</b>\n\n"
                f"👤 کاربران عادی: <b>{'فعال' if ue else 'غیرفعال'}</b>\n"
                f"🛡 ادمین‌ها: <b>{'فعال' if ae else 'غیرفعال'}</b>\n"
                f"👥 همه کاربران: <b>{'فعال' if ue and ae else 'غیرفعال'}</b>", parse_mode="HTML",
                reply_markup=phone_status_keyboard(back_callback="owner:general_settings", user_enabled=ue, admin_enabled=ae))
            return

        if action == "phone_noop":
            await query.answer()
            return

        # -------------------------------------------------
        # پینگ ربات: ۱۰ اندازه‌گیری با فاصله یک‌ثانیه
        # -------------------------------------------------
        if action == "ping":
            if not owner_user:
                await query.answer("⛔ فقط Owner.", show_alert=True); return
            import time as _time
            await query.answer("📡 اندازه‌گیری پینگ شروع شد...")
            samples=[]
            for i in range(1, 11):
                started=_time.perf_counter()
                try:
                    await context.bot.get_me()
                    ms=(_time.perf_counter()-started)*1000
                except Exception:
                    ms=None
                samples.append(ms)
                lines=["📡 <b>پینگ ربات</b>", "", "در حال اندازه‌گیری...", ""]
                for n,v in enumerate(samples,1): lines.append(f"{n} ثانیه: <b>{v:.0f} ms</b>" if v is not None else f"{n} ثانیه: <b>خطا</b>")
                valid=[v for v in samples if v is not None]
                if valid:
                    lines += ["", f"📊 میانگین فعلی: <b>{sum(valid)/len(valid):.0f} ms</b>"]
                try: await query.edit_message_text("\n".join(lines),parse_mode="HTML")
                except Exception: pass
                if i < 10: await _asyncio.sleep(1)
            valid=[v for v in samples if v is not None]
            avg=(sum(valid)/len(valid)) if valid else 0
            lines=["📡 <b>پینگ ربات — نتیجه نهایی</b>", ""]
            for n,v in enumerate(samples,1): lines.append(f"{n} ثانیه: <b>{v:.0f} ms</b>" if v is not None else f"{n} ثانیه: <b>خطا</b>")
            lines += ["", f"📊 تعداد موفق: <b>{len(valid)}/10</b>", f"📈 میانگین پینگ: <b>{avg:.0f} ms</b>", ""]
            await query.edit_message_text("\n".join(lines),parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data="owner:general_settings")]]))
            return

        # -------------------------------------------------
        # خروج از پنل مالک
        # -------------------------------------------------
        if action == "back_owner_panel":
            await query.answer()
            await query.edit_message_text("👑 <b>پنل مالک</b>\n\nیکی از گزینه‌های زیر را انتخاب کنید:", parse_mode="HTML", reply_markup=owner_panel_keyboard())
            return

        if action == "back_main":
            context.user_data.pop("admin_panel", None)
            context.user_data.pop("admin_pending", None)

            await query.answer()

            session.commit()

            await query.edit_message_text(
                "🔙 از پنل مالک خارج شدید.",
                reply_markup=private_main_keyboard(),
            )
            return

        # -------------------------------------------------
        # ورود به مدیریت ادمین‌ها
        # -------------------------------------------------
        if action == "admin_permissions_menu":
            if not owner_user:
                await query.answer("⛔ این بخش فقط برای مالک است.", show_alert=True); return
            await query.answer("ℹ️ بخش دسترسی ادمین‌ها آماده تنظیم است.", show_alert=True)
            return

        if action == "admins":
            context.user_data.pop("admin_pending", None)
            context.user_data["admin_panel"] = "owner_admins"
            context.user_data[_waiting_scope_key("admin_panel")] = int(update.effective_chat.id)

            await query.answer()

            session.commit()

            await query.edit_message_text(
                "👨‍💼 <b>مدیریت ادمین‌ها</b>",
                parse_mode="HTML",
                reply_markup=admin_management_keyboard(),
            )
            return

        # -------------------------------------------------
        # برگشت به مدیریت ادمین‌ها
        # -------------------------------------------------
        if action == "back_admins":
            context.user_data.pop("admin_pending", None)
            context.user_data["admin_panel"] = "owner_admins"
            context.user_data[_waiting_scope_key("admin_panel")] = int(update.effective_chat.id)

            await query.answer()

            session.commit()

            await query.edit_message_text(
                "👨‍💼 <b>مدیریت ادمین‌ها</b>",
                parse_mode="HTML",
                reply_markup=admin_management_keyboard(),
            )
            return

        # -------------------------------------------------
        # برگشت از مدیریت ادمین‌ها به Owner
        # -------------------------------------------------
        if action == "back":
            context.user_data.pop("admin_pending", None)
            context.user_data["admin_panel"] = "owner"
            context.user_data[_waiting_scope_key("admin_panel")] = int(update.effective_chat.id)

            await query.answer()

            session.commit()

            await query.edit_message_text(
                "👑 <b>پنل مالک</b>",
                parse_mode="HTML",
                reply_markup=owner_panel_keyboard(),
            )
            return

        # -------------------------------------------------
        # افزودن ادمین
        # -------------------------------------------------
        if action == "add_admin":
            context.user_data.pop("admin_pending", None)
            context.user_data["admin_panel"] = "owner_admins"
            context.user_data[_waiting_scope_key("admin_panel")] = int(update.effective_chat.id)

            await query.answer()

            session.commit()

            await query.edit_message_text(
                "➕ <b>افزودن ادمین</b>\n\n"
                "روش افزودن را انتخاب کنید:",
                parse_mode="HTML",
                reply_markup=add_admin_mode_keyboard(),
            )
            return

        # -------------------------------------------------
        # افزودن تکی
        # -------------------------------------------------
        if action == "add_single":
            context.user_data["admin_pending"] = {
                "action": "add_single",
                "prompt_chat_id": int(query.message.chat_id),
                "prompt_message_id": int(query.message.message_id),
            }
            context.user_data[_waiting_scope_key("admin_pending")] = int(update.effective_chat.id)

            await query.answer()

            session.commit()

            await query.edit_message_text(
                "1️⃣ <b>افزودن تکی ادمین</b>\n\n"
                "🆔 آیدی عددی Telegram کاربر را ارسال کنید.",
                parse_mode="HTML",
                reply_markup=admin_step_back_keyboard("owner:add_admin"),
            )
            return

        # -------------------------------------------------
        # افزودن چندتایی
        # -------------------------------------------------
        if action == "add_multiple":
            context.user_data["admin_pending"] = {
                "action": "add_multiple",
                "telegram_ids": [],
                "prompt_chat_id": int(query.message.chat_id),
                "prompt_message_id": int(query.message.message_id),
            }
            context.user_data[_waiting_scope_key("admin_pending")] = int(update.effective_chat.id)

            await query.answer()

            session.commit()

            await query.edit_message_text(
                "2️⃣ <b>افزودن چندتایی ادمین</b>\n\n"
                "🆔 آیدی عددی اولین کاربر را ارسال کنید.\n\n"
                "بعد از دریافت هر آیدی، می‌توانید آیدی نفر بعدی را ارسال کنید.\n"
                "در پایان، دکمه «✅ تأیید افزودن همه» را بزنید.",
                parse_mode="HTML",
                reply_markup=admin_back_keyboard(),
            )
            return

        # -------------------------------------------------
        # حذف ادمین: انتخاب تکی / چندتایی
        # -------------------------------------------------
        if action == "remove_admin":
            if not get_admins(session):
                await query.answer("⚠️ هیچ ادمینی وجود ندارد.", show_alert=True)
                session.commit()
                return

            context.user_data.pop("admin_pending", None)
            await query.answer()
            session.commit()
            await query.edit_message_text(
                "➖ <b>حذف ادمین</b>\n\nروش حذف را انتخاب کنید:",
                parse_mode="HTML",
                reply_markup=remove_admin_mode_keyboard(),
            )
            return

        if action == "remove_single":
            context.user_data["admin_pending"] = {
                "action": "remove_single",
                "prompt_chat_id": int(query.message.chat_id),
                "prompt_message_id": int(query.message.message_id),
            }
            context.user_data[_waiting_scope_key("admin_pending")] = int(update.effective_chat.id)
            await query.answer()
            session.commit()
            await query.edit_message_text(
                "1️⃣ <b>حذف تکی ادمین</b>\n\n🆔 آیدی عددی ادمین را ارسال کنید.",
                parse_mode="HTML",
                reply_markup=admin_step_back_keyboard("owner:remove_admin"),
            )
            return

        if action == "remove_multiple":
            context.user_data["admin_pending"] = {
                "action": "remove_multiple",
                "telegram_ids": [],
                "prompt_chat_id": int(query.message.chat_id),
                "prompt_message_id": int(query.message.message_id),
            }
            context.user_data[_waiting_scope_key("admin_pending")] = int(update.effective_chat.id)
            await query.answer()
            session.commit()
            await query.edit_message_text(
                "2️⃣ <b>حذف چندتایی ادمین</b>\n\n"
                "🆔 آیدی عددی اولین ادمین را ارسال کنید.\n\n"
                "بعد از هر آیدی می‌توانید آیدی نفر بعدی را ارسال کنید.",
                parse_mode="HTML",
                reply_markup=admin_step_back_keyboard("owner:remove_admin"),
            )
            return

        # -------------------------------------------------
        # جستجوی ادمین
        # -------------------------------------------------
        if action == "search_admin":
            admins = get_admins(session)

            if not admins:
                await query.answer(
                    "⚠️ هیچ ادمینی وجود ندارد.",
                    show_alert=True,
                )
                session.commit()
                return

            context.user_data["admin_pending"] = {
                "action": "search_admin",
                "prompt_chat_id": int(query.message.chat_id),
                "prompt_message_id": int(query.message.message_id),
            }
            context.user_data[_waiting_scope_key("admin_pending")] = int(update.effective_chat.id)

            await query.answer()

            session.commit()

            await query.edit_message_text(
                "🔎 <b>جستجوی ادمین</b>\n\n"
                "آیدی عددی، نام کاربری، شماره تلفن یا نام کشور ادمین را ارسال کنید.",
                parse_mode="HTML",
                reply_markup=admin_back_keyboard(),
            )
            return

        # تعیین سطح دسترسی ادمین توسط مالک
        if action == "admin_permissions" and len(parts) >= 3:
            if not owner_user:
                await query.answer("⛔ این بخش فقط برای مالک است.", show_alert=True); return
            target_id = int(parts[2]); target = get_admin_user(session, target_id)
            if target is None:
                await query.answer("❌ ادمین پیدا نشد.", show_alert=True); return
            perms = get_admin_permissions(session, target_id)
            await query.answer(); await query.edit_message_text("🛡️ <b>تعیین سطح دسترسی ادمین</b>\n\nبخش موردنظر را انتخاب کنید:", parse_mode="HTML", reply_markup=admin_permission_keyboard(target_id, perms)); return
        if action == "admin_perm_section" and len(parts) >= 4:
            if not owner_user:
                await query.answer("⛔ این بخش فقط برای مالک است.", show_alert=True); return
            target_id = int(parts[2]); section = parts[3]; perms = get_admin_permissions(session, target_id)
            await query.answer()
            await query.edit_message_text("🛡️ <b>تعیین سطح دسترسی</b>\n\nبخش موردنظر را انتخاب کنید:", parse_mode="HTML", reply_markup=admin_permission_section_keyboard(target_id, section, perms))
            return
        if action == "admin_perm" and len(parts) >= 4:
            if not owner_user:
                await query.answer("⛔ این بخش فقط برای مالک است.", show_alert=True); return
            target_id = int(parts[2]); perm = parts[3]; perms = get_admin_permissions(session, target_id)
            new_state = not perms.get(perm, True); set_admin_permission(session, target_id, perm, new_state); session.commit()
            await query.answer(("دسترسی فعال شد." if new_state else "دسترسی محدود شد."), show_alert=True)
            # پس از تغییر، کاربر را در همان بخش نگه می‌داریم.
            section = "messages" if perm.startswith("message_") or perm == "messages" else ("users" if perm in {"users","user_search","user_info","game_settings","game_specs","country_name","delete_country","swap_countries","reset_swap","user_account_settings"} else "stats")
            await query.edit_message_text("🛡️ <b>تعیین سطح دسترسی</b>\n\nبخش موردنظر را انتخاب کنید:", parse_mode="HTML", reply_markup=admin_permission_section_keyboard(target_id, section, get_admin_permissions(session, target_id))); return

        # -------------------------------------------------
        # تأیید نتیجه جستجوی ادمین
        # -------------------------------------------------
        if action == "admin_search_confirm" and len(parts) >= 3:
            target_id = int(parts[2])
            target = get_admin_user(session, target_id)
            if target is None:
                await query.answer("❌ ادمین پیدا نشد یا دیگر ادمین نیست.", show_alert=True); return
            text = _render_managed_user_info(session, target)
            await query.answer("✅ تأیید شد.")
            await query.edit_message_text(text[:4096], parse_mode="HTML", reply_markup=admin_info_keyboard(target_id, back_callback="owner:back_admins", banned=bool(target.is_banned)))
            return

        # -------------------------------------------------
        # جزئیات ادمین
        # -------------------------------------------------
        if action == "admin_detail" and len(parts) >= 3:
            target_id = int(parts[2])
            target = get_admin_user(session, target_id)
            if target is None:
                await query.answer("❌ ادمین پیدا نشد.", show_alert=True); return
            text = _render_managed_user_info(session, target)
            await query.answer()
            back_page=max(1, int(context.user_data.get('admin_list_page', 1)))
            context.user_data["user_admin_origin"] = f"owner:admin_detail:{target_id}"
            context.user_data[_waiting_scope_key("user_admin_origin")] = int(update.effective_chat.id)
            context.user_data["user_detail_back"] = f"owner:list_admins:{back_page}"
            context.user_data[_waiting_scope_key("user_detail_back")] = int(update.effective_chat.id)
            await query.edit_message_text(text[:4096], parse_mode="HTML", reply_markup=admin_info_keyboard(target_id, back_callback=f"owner:list_admins:{back_page}", banned=bool(target.is_banned)))
            return

        # -------------------------------------------------
        # لیست ادمین‌ها
        # -------------------------------------------------
        if action == "list_admins":
            context.user_data.pop("admin_pending", None)

            admins = get_admins(session)

            if not admins:
                await query.answer(
                    "⚠️ هیچ ادمینی وجود ندارد.",
                    show_alert=True,
                )
                session.commit()
                return

            try:
                page = int(parts[2])
            except (IndexError, ValueError):
                page = 1

            per_page = 10
            total_pages = max(
                1,
                (len(admins) + per_page - 1) // per_page,
            )

            page = max(1, min(page, total_pages))
            context.user_data["admin_list_page"] = page

            start = (page - 1) * per_page
            end = start + per_page

            page_admins = admins[start:end]

            lines = [
                "📋 <b>لیست ادمین‌ها</b>",
                "",
            ]

            for index, adm in enumerate(
                page_admins,
                start=start + 1,
            ):
                u = get_admin_user(
                    session,
                    adm.telegram_id,
                )

                name = (
                    u.first_name
                    if u and u.first_name
                    else (
                        u.username
                        if u and u.username
                        else "ثبت‌نشده"
                    )
                )

                phone_line = f"\n📱 {u.phone_number}" if u and u.phone_number else ""
                lines.append(
                    f"{index}. 👤 <b>{name}</b>\n"
                    f"🆔 <code>{adm.telegram_id}</code>{phone_line}"
                )

            await query.answer()

            session.commit()

            await query.edit_message_text(
                "\n\n".join(lines),
                parse_mode="HTML",
                reply_markup=admin_list_keyboard(
                    page,
                    total_pages,
                    admins=[((get_admin_user(session, a.telegram_id).first_name if get_admin_user(session, a.telegram_id) and get_admin_user(session, a.telegram_id).first_name else str(a.telegram_id)), a.telegram_id) for a in page_admins],
                ),
            )
            return

        # -------------------------------------------------
        # دکمه شماره صفحه؛ هیچ کاری انجام نده
        # -------------------------------------------------
        if action == "list_noop":
            await query.answer()
            return

        # -------------------------------------------------
        # ویرایش آیدی در تأیید افزودن تکی
        # -------------------------------------------------
        if action == "edit" and len(parts) > 2 and parts[2] in {"add_admin", "remove_admin"}:
            edit_action = parts[2]
            pending_action = "add_single" if edit_action == "add_admin" else "remove_single"
            context.user_data["admin_pending"] = {
                "action": pending_action,
                "prompt_chat_id": int(query.message.chat_id),
                "prompt_message_id": int(query.message.message_id),
            }
            context.user_data[_waiting_scope_key("admin_pending")] = int(update.effective_chat.id)
            await query.answer()
            title = "افزودن تکی ادمین" if edit_action == "add_admin" else "حذف تکی ادمین"
            await query.edit_message_text(
                f"1️⃣ <b>{title}</b>\n\n"
                "🆔 آیدی عددی، یوزرنیم، شماره تلفن یا نام کشور کاربر را ارسال کنید.",
                parse_mode="HTML",
                reply_markup=admin_step_back_keyboard("owner:add_admin" if edit_action == "add_admin" else "owner:remove_admin"),
            )
            return

        # -------------------------------------------------
        # تأیید افزودن تکی / حذف
        # -------------------------------------------------
        if action == "confirm":
            confirm_action = parts[2] if len(parts) > 2 else ""

            pending = (
                context.user_data.get("admin_pending")
                or {}
            )

            target_id = pending.get("telegram_id")

            if (
                not target_id
                or pending.get("action") != confirm_action
            ):
                await query.answer(
                    "⚠️ عملیات منقضی شده است.",
                    show_alert=True,
                )

                context.user_data.pop(
                    "admin_pending",
                    None,
                )

                session.commit()

                await query.edit_message_text(
                    "⚠️ عملیات منقضی شده است.",
                    reply_markup=admin_management_keyboard(),
                )
                return

            # ---------------------------------------------
            # تأیید افزودن تکی
            # ---------------------------------------------
            if confirm_action == "add_admin":
                if is_owner(
                    int(target_id),
                    OWNER_ID,
                ):
                    context.user_data.pop(
                        "admin_pending",
                        None,
                    )

                    await query.answer(
                        "⚠️ مالک قابل افزودن نیست.",
                        show_alert=True,
                    )

                    session.commit()

                    await query.edit_message_text(
                        "⚠️ مالک از قبل دسترسی کامل دارد.",
                        reply_markup=admin_management_keyboard(),
                    )
                    return

                target_user = get_admin_user(
                    session,
                    int(target_id),
                )

                if target_user is None:
                    context.user_data.pop(
                        "admin_pending",
                        None,
                    )

                    await query.answer(
                        "❌ این کاربر در ربات ثبت نشده است.",
                        show_alert=True,
                    )

                    session.rollback()

                    await query.edit_message_text(
                        "❌ این کاربر در ربات ثبت نشده است.\n\n"
                        "ابتدا باید کاربر ربات را /start کند.",
                        reply_markup=admin_management_keyboard(),
                    )
                    return

                if is_admin(
                    session,
                    int(target_id),
                    OWNER_ID,
                ):
                    context.user_data.pop(
                        "admin_pending",
                        None,
                    )

                    await query.answer(
                        "⚠️ این کاربر قبلاً ادمین است.",
                        show_alert=True,
                    )

                    session.commit()

                    await query.edit_message_text(
                        "⚠️ این کاربر قبلاً ادمین است.",
                        reply_markup=admin_management_keyboard(),
                    )
                    return

                if not add_admin(
                    session,
                    int(target_id),
                ):
                    context.user_data.pop(
                        "admin_pending",
                        None,
                    )

                    await query.answer(
                        "❌ افزودن ادمین انجام نشد.",
                        show_alert=True,
                    )

                    session.rollback()

                    await query.edit_message_text(
                        "❌ افزودن ادمین انجام نشد.",
                        reply_markup=admin_management_keyboard(),
                    )
                    return

                context.user_data.pop(
                    "admin_pending",
                    None,
                )

                session.commit()

                await grant_admin_command_scope(
                    query.get_bot(),
                    int(target_id),
                )
                await _notify_user(query.get_bot(), int(target_id), "👑 <b>شما به‌عنوان ادمین ربات منصوب شدید.</b>\n\nدسترسی‌های ادمینی برای شما فعال شد.")

                await query.answer(
                    "✅ ادمین با موفقیت اضافه شد.",
                    show_alert=True,
                )

                await query.edit_message_text(
                    "👨‍💼 <b>مدیریت ادمین‌ها</b>",
                    parse_mode="HTML",
                    reply_markup=admin_management_keyboard(),
                )
                return

            # ---------------------------------------------
            # تأیید حذف ادمین
            # ---------------------------------------------
            if confirm_action == "remove_admin":
                result = remove_admin(
                    session,
                    int(target_id),
                    OWNER_ID,
                )

                context.user_data.pop(
                    "admin_pending",
                    None,
                )

                if result == "OWNER_PROTECTED":
                    session.rollback()

                    await query.answer(
                        "⛔ مالک قابل حذف نیست.",
                        show_alert=True,
                    )

                    await query.edit_message_text(
                        "⛔ مالک قابل حذف نیست.",
                        reply_markup=admin_management_keyboard(),
                    )
                    return

                if result == "NOT_ADMIN":
                    session.rollback()

                    await query.answer(
                        "⚠️ این آیدی ادمین نیست.",
                        show_alert=True,
                    )

                    await query.edit_message_text(
                        "⚠️ این آیدی ادمین نیست.",
                        reply_markup=admin_management_keyboard(),
                    )
                    return

                session.commit()

                await revoke_admin_command_scope(
                    query.get_bot(),
                    int(target_id),
                )
                await _notify_user(query.get_bot(), int(target_id), "👤 <b>دسترسی ادمینی شما حذف شد.</b>")

                await query.answer(
                    "✅ ادمین حذف شد.",
                    show_alert=True,
                )

                await query.edit_message_text(
                    "👨‍💼 <b>مدیریت ادمین‌ها</b>",
                    parse_mode="HTML",
                    reply_markup=admin_management_keyboard(),
                )
                return

        # -------------------------------------------------
        # تأیید نهایی افزودن چندتایی
        # -------------------------------------------------
        if action == "confirm_multiple":
            pending = (
                context.user_data.get("admin_pending")
                or {}
            )

            if pending.get("action") != "add_multiple":
                await query.answer(
                    "⚠️ عملیات منقضی شده است.",
                    show_alert=True,
                )
                return

            telegram_ids = pending.get(
                "telegram_ids",
                [],
            )

            if not telegram_ids:
                await query.answer(
                    "⚠️ هنوز هیچ آیدی اضافه نشده است.",
                    show_alert=True,
                )
                return

            # بررسی نهایی همه IDها قبل از commit
            valid_ids = []

            for target_id in telegram_ids:
                if is_owner(
                    int(target_id),
                    OWNER_ID,
                ):
                    await query.answer(
                        "⛔ مالک قابل افزودن نیست.",
                        show_alert=True,
                    )
                    return

                user = get_admin_user(
                    session,
                    int(target_id),
                )

                if user is None:
                    await query.answer(
                        f"❌ آیدی {target_id} "
                        "در ربات ثبت نشده است.",
                        show_alert=True,
                    )
                    return

                if is_admin(
                    session,
                    int(target_id),
                    OWNER_ID,
                ):
                    await query.answer(
                        f"⚠️ آیدی {target_id} "
                        "قبلاً ادمین است.",
                        show_alert=True,
                    )
                    return

                valid_ids.append(
                    int(target_id)
                )

            # همه یا هیچ؛ اگر مشکلی باشد هیچ‌کدام ثبت نمی‌شوند.
            for target_id in valid_ids:
                if not add_admin(
                    session,
                    target_id,
                ):
                    session.rollback()

                    await query.answer(
                        "❌ عملیات افزودن گروهی انجام نشد.",
                        show_alert=True,
                    )
                    return

            session.commit()

            for target_id in valid_ids:
                await grant_admin_command_scope(
                    query.get_bot(),
                    target_id,
                )
                await _notify_user(query.get_bot(), target_id, "👑 <b>شما به‌عنوان ادمین ربات منصوب شدید.</b>\n\nدسترسی‌های ادمینی برای شما فعال شد.")

            count = len(valid_ids)

            context.user_data.pop(
                "admin_pending",
                None,
            )

            await query.answer(
                f"✅ {count} ادمین با موفقیت اضافه شدند.",
                show_alert=True,
            )

            await query.edit_message_text(
                "👨‍💼 <b>مدیریت ادمین‌ها</b>",
                parse_mode="HTML",
                reply_markup=admin_management_keyboard(),
            )
            return

        # -------------------------------------------------
        # تأیید حذف چندتایی
        # -------------------------------------------------
        if action == "confirm_remove_multiple":
            pending = context.user_data.get("admin_pending") or {}
            if pending.get("action") != "remove_multiple":
                await query.answer("⚠️ عملیات منقضی شده است.", show_alert=True)
                return

            telegram_ids = list(dict.fromkeys(pending.get("telegram_ids", [])))
            if not telegram_ids:
                await query.answer("⚠️ هنوز هیچ آیدی برای حذف انتخاب نشده است.", show_alert=True)
                return

            # همه IDها دوباره قبل از حذف بررسی می‌شوند.
            for target_id in telegram_ids:
                if is_owner(int(target_id), OWNER_ID):
                    await query.answer("⛔ مالک قابل حذف نیست.", show_alert=True)
                    return
                if not is_admin(session, int(target_id), OWNER_ID):
                    await query.answer(f"⚠️ آیدی {target_id} دیگر ادمین نیست.", show_alert=True)
                    return

            removed_ids = []
            for target_id in telegram_ids:
                result = remove_admin(session, int(target_id), OWNER_ID)
                if result != "REMOVED":
                    session.rollback()
                    await query.answer("❌ عملیات حذف گروهی انجام نشد.", show_alert=True)
                    return
                removed_ids.append(int(target_id))

            session.commit()
            context.user_data.pop("admin_pending", None)

            for target_id in removed_ids:
                await revoke_admin_command_scope(query.get_bot(), target_id)
                await _notify_user(query.get_bot(), target_id, "👤 <b>دسترسی ادمینی شما حذف شد.</b>")

            await query.answer(
                f"✅ {len(removed_ids)} ادمین حذف شدند.",
                show_alert=True,
            )
            await query.edit_message_text(
                "👨‍💼 <b>مدیریت ادمین‌ها</b>",
                parse_mode="HTML",
                reply_markup=admin_management_keyboard(),
            )
            return

        # -------------------------------------------------
        # پاکسازی همه ادمین‌ها
        # -------------------------------------------------
        if action == "clear_admins":
            if not get_admins(session):
                await query.answer("⚠️ هیچ ادمینی وجود ندارد.", show_alert=True)
                session.commit()
                return

            context.user_data.pop("admin_pending", None)
            await query.answer()
            session.commit()
            await query.edit_message_text(
                "⚠️ <b>پاکسازی همه ادمین‌ها</b>\n\n"
                "از حذف تمام ادمین‌ها مطمئن هستید؟",
                parse_mode="HTML",
                reply_markup=admin_clear_confirm_keyboard(),
            )
            return

        if action == "confirm_clear_admins":
            admin_ids = clear_all_admins(session)
            session.commit()

            for target_id in admin_ids:
                await revoke_admin_command_scope(query.get_bot(), target_id)

            await query.answer(
                f"✅ {len(admin_ids)} ادمین حذف شدند.",
                show_alert=True,
            )
            await query.edit_message_text(
                "👨‍💼 <b>مدیریت ادمین‌ها</b>",
                parse_mode="HTML",
                reply_markup=admin_management_keyboard(),
            )
            return

        # اگر Callback مربوط به بخش ادمین نبود، اجرای مسیرهای کاربر/بازی ادامه پیدا می‌کند.
        user = get_or_create_user(session, query.from_user)

        if data == "cancel_country_creation":
            context.user_data.pop(f"country_name_pending_{query.from_user.id}", None)
            session.commit()
            await query.edit_message_text("❌ ساخت کشور لغو شد.")
            return

        if data == "active_country":
            country = get_context_country(session, user, query.message.chat_id if query.message else None)

            if country is None:
                text = "❌ هنوز کشور پیش‌فرضی انتخاب نکرده‌اید."
            else:
                text = f"🌍 کشور فعال شما: <b>{country.title}</b>"

            session.commit()
            await query.edit_message_text(
                text,
                parse_mode="HTML",
                reply_markup=private_main_keyboard(),
            )
            return

        if data == "choose_country":
            countries = get_user_countries(session, user)

            if not countries:
                session.commit()
                await query.answer("🌍 شما هیچ کشوری ندارید. ابتدا در یک گروه کشور خود را بسازید.", show_alert=True)
                return

            session.commit()
            await query.edit_message_text(
                "🌍 <b>کشور پیش‌فرض را انتخاب کنید:</b>",
                parse_mode="HTML",
                reply_markup=country_list_keyboard(countries, selected_id=user.default_country_id, back_callback="settings:game"),
            )
            return

        if data.startswith("set_country:"):
            context.user_data.pop("pending_exchange", None)
            country_id = int(data.split(":", 1)[1])

            old_default_id = user.default_country_id
            if set_default_country(session, user, country_id):
                country = get_context_country(session, user, query.message.chat_id if query.message else None)
                session.commit()
                if old_default_id == country_id:
                    await query.answer(f"ℹ️ {country.title} از قبل کشور پیش‌فرض شماست.", show_alert=True)
                    return
                await query.answer(f"✅ {country.title} انتخاب شد.")
                await query.edit_message_reply_markup(reply_markup=country_list_keyboard(get_user_countries(session, user), selected_id=user.default_country_id, back_callback="settings:game"))
            else:
                session.rollback()
                await query.edit_message_text(
                    "❌ این کشور برای شما قابل انتخاب نیست.",
                    reply_markup=private_main_keyboard(),
                )
            return

        if data == "exchange:rates":
            session.commit()
            await query.edit_message_text(
                exchange_rate_text(session),
                parse_mode="HTML",
                reply_markup=exchange_keyboard(),
            )
            return

        if data.startswith("exchange:"):
            exchange_type = data.split(":", 1)[1]

            if exchange_type not in EXCHANGE_RATES:
                session.commit()
                await query.edit_message_text(
                    "❌ نوع تبادل نامعتبر است.",
                    reply_markup=exchange_keyboard(),
                )
                return

            country = get_context_country(session, user, query.message.chat_id if query.message else None)

            if country is None:
                session.commit()
                await query.edit_message_text(
                    "❌ کشور پیش‌فرضی انتخاب نشده است.",
                    reply_markup=private_main_keyboard(),
                )
                return

            context.user_data["pending_exchange"] = {
                "type": exchange_type,
            }
            context.user_data[_waiting_scope_key("pending_exchange")] = int(update.effective_chat.id)

            rate = get_exchange_rates(session)[exchange_type]
            from_names = {
                "money": "💰 پول",
                "metal": "🔩 فلز",
                "fuel": "⛽ سوخت",
                "uranium": "☢️ اورانیوم",
            }

            session.commit()
            await query.edit_message_text(
                f"💱 <b>{rate['title']}</b>\n\n"
                f"مقدار {from_names[rate['from_resource']]} را ارسال کنید.\n\n"
                f"📌 حداقل واحد قابل تبدیل: <b>{rate['input_unit']:,}</b>\n"
                f"📈 نرخ: <b>{rate['input_unit']:,}</b> "
                f"{from_names[rate['from_resource']]} ➜ "
                f"<b>{rate['output_unit']:,}</b> "
                f"{from_names[rate['to_resource']]}\n\n"
                "مثال: <code>"
                f"{rate['input_unit']:,}"
                "</code>",
                parse_mode="HTML",
                reply_markup=exchange_input_keyboard(),
            )
            return

        if data == "exchange_back":
            context.user_data.pop("pending_exchange", None)
            session.commit()
            await query.answer()
            await query.edit_message_text(
                exchange_rate_text(session),
                parse_mode="HTML",
                reply_markup=exchange_keyboard(),
            )
            return

        if data == "exchange_cancel":
            context.user_data.pop("pending_exchange", None)
            session.commit()
            await query.answer("❌ تبادل لغو شد.", show_alert=True)
            await query.edit_message_text(exchange_rate_text(session), parse_mode="HTML", reply_markup=None)
            return

        if data == "exchange_confirm":
            pending = context.user_data.get("pending_exchange")

            if not pending or "amount" not in pending:
                session.commit()
                await query.edit_message_text(
                    "⚠️ معامله‌ای برای تأیید وجود ندارد.",
                    reply_markup=exchange_keyboard(),
                )
                return

            country = get_context_country(session, user, query.message.chat_id if query.message else None)

            if country is None:
                context.user_data.pop("pending_exchange", None)
                session.commit()
                await query.edit_message_text(
                    "❌ کشور پیش‌فرضی انتخاب نشده است.",
                    reply_markup=private_main_keyboard(),
                )
                return

            success, result = execute_exchange(
                country,
                pending["type"],
                pending["amount"],
                session,
            )

            if not success:
                context.user_data.pop("pending_exchange", None)
                session.rollback()
                await query.edit_message_text(
                    "❌ موجودی شما برای انجام این معامله دیگر کافی نیست.",
                    reply_markup=exchange_keyboard(),
                )
                return

            context.user_data.pop("pending_exchange", None)
            session.commit()

            from_names = {
                "money": "💰 پول",
                "metal": "🔩 فلز",
                "fuel": "⛽ سوخت",
                "uranium": "☢️ اورانیوم",
            }

            await query.answer(f"تبدیل انجام شد\n📤 {result['input']:,} {from_names[result['from_resource']]} ➜ 📥 {result['output']:,} {from_names[result['to_resource']]}", show_alert=True)
            await query.edit_message_text(exchange_rate_text(session), parse_mode="HTML", reply_markup=None)
            return

        if data == "arsenal_missiles":
            try:
                country = get_context_country(session, user, query.message.chat_id if query.message else None)
                if country is None:
                    await query.answer("❌ کشور پیش‌فرضی انتخاب نشده است.", show_alert=True); return
                cfg = get_missiles_config(session) or {}
                inv = get_missile_inventory(session, country.id) or {}
                if int(getattr(country, "arsenal_level", 0) or 0) <= 0:
                    if inv:
                        save_missile_inventory(session, country.id, {})
                    country.missiles = 0
                    country.arsenal_storage = 0.0
                    session.commit()
                    await query.answer("🚀 برای مشاهده موجودی، ابتدا زرادخانه را بسازید.", show_alert=True)
                    return
                known_ids = {str(x.get("id")) for x in (cfg.get("items", []) or []) if x.get("id") is not None}
                cleaned = {}
                for mid, levels in inv.items():
                    if str(mid) not in known_ids or not isinstance(levels, dict):
                        continue
                    valid_levels = {}
                    for raw_level, raw_count in levels.items():
                        try:
                            level = int(raw_level)
                            count = int(raw_count or 0)
                        except (TypeError, ValueError):
                            continue
                        if level > 0 and count > 0:
                            valid_levels[str(level)] = count
                    if valid_levels:
                        cleaned[str(mid)] = valid_levels
                if cleaned != inv:
                    save_missile_inventory(session, country.id, cleaned)
                    session.commit()
                items = []
                for mid, levels in cleaned.items():
                    m = next((x for x in cfg.get("items", []) if str(x.get("id")) == str(mid)), None)
                    if not m:
                        continue
                    for raw_level, count in sorted(levels.items(), key=lambda x: int(x[0])):
                        items.append({"mid": str(mid), "level": int(raw_level), "label": f"{m.get('name', 'موشک')} — سطح {int(raw_level)} ({int(count)} فروند)"})
                if not items:
                    await query.answer("🚀 در حال حاضر موشکی در زرادخانه ندارید.", show_alert=True)
                    return
                await query.answer()
                await query.edit_message_text(
                    "🚀 <b>لیست موشک‌های زرادخانه</b>\n\nموشک موردنظر را برای فروش انتخاب کنید:",
                    parse_mode="HTML", reply_markup=arsenal_missile_list_keyboard(items)
                )
            except Exception:
                session.rollback()
                await query.answer("❌ نمایش لیست موشک‌ها با خطا روبه‌رو شد. دوباره تلاش کنید.", show_alert=True)
            return

        if data == "arsenal_missiles_back":
            country=get_context_country(session,user, query.message.chat_id if query.message else None)
            if country is None: await query.answer("❌ کشور پیش‌فرضی انتخاب نشده است.",show_alert=True); return
            cfg=get_arsenal_config(session); level=int(getattr(country,"arsenal_level",0)); nxt=cfg.get("levels",{}).get(level+1,{})
            status=construction_label(country,"arsenal")
            await query.answer()
            await query.edit_message_text(arsenal_info(country,cfg),parse_mode="HTML",reply_markup=arsenal_keyboard(level==0,can_upgrade_arsenal(country,cfg)[0],float(cfg.get("build_cost",{}).get("uranium",0))>0,float(nxt.get("uranium",0))>0,construction_text=status,finish_uranium_cost=arsenal_instant_finish_uranium_cost(country,cfg)))
            return

        if data.startswith("arsenal_sell_select:"):
            parts=data.split(":")
            if len(parts)!=3: return
            mid, level=parts[1], int(parts[2])
            country=get_context_country(session,user, query.message.chat_id if query.message else None); cfg=get_missiles_config(session)
            m=next((x for x in cfg.get("items",[]) if str(x.get("id"))==str(mid)),None)
            if country is None or not m: await query.answer("❌ موشک پیدا نشد.",show_alert=True); return
            count=get_missile_count(get_missile_inventory(session,country.id),mid,level)
            if count<=0: await query.answer("❌ این موشک در زرادخانه موجود نیست.",show_alert=True); return
            context.user_data.pop("arsenal_sell_pending",None)
            await query.answer()
            await query.edit_message_text(
                f"💰 <b>فروش موشک</b>\n\n🚀 {escape(str(m.get('name','موشک')))} — سطح {level}\n📦 موجودی این سطح: <b>{count}</b> فروند\n\nتعداد موشک‌هایی که می‌خواهید بفروشید را انتخاب کنید:",
                parse_mode="HTML", reply_markup=arsenal_sell_quantity_keyboard(mid, level, count)
            )
            return

        if data.startswith("arsenal_sell_qty:"):
            parts=data.split(":")
            if len(parts)!=4: return
            mid, level, requested = parts[1], int(parts[2]), int(parts[3])
            country=get_context_country(session,user, query.message.chat_id if query.message else None); cfg=get_missiles_config(session)
            m=next((x for x in cfg.get("items",[]) if str(x.get("id"))==str(mid)),None)
            if country is None or not m: await query.answer("❌ موشک پیدا نشد.",show_alert=True); return
            available=get_missile_count(get_missile_inventory(session,country.id),mid,level)
            if available <= 0: await query.answer("❌ این موشک دیگر در زرادخانه موجود نیست.",show_alert=True); return
            qty=min(requested, available)
            lvl=(m.get("levels") or {}).get(str(level),{}) or {}
            price=float(lvl.get("cost",0) or 0) or float(m.get("base_cost",0) or 0)
            refund=price/2
            context.user_data["arsenal_sell_pending"]={"mid":mid,"level":level,"quantity":qty,"refund":refund,"name":str(m.get("name","موشک"))}
            context.user_data[_waiting_scope_key("arsenal_sell_pending")] = int(update.effective_chat.id)
            total=refund*qty
            await query.answer()
            await query.edit_message_text(
                f"💰 <b>تأیید فروش</b>\n\n🚀 {escape(str(m.get('name','موشک')))} — سطح {level}\n📦 تعداد فروش: <b>{qty}</b> فروند\n💵 دریافتی هر فروند: <b>{refund:,.0f}</b>\n💰 مجموع دریافتی: <b>{total:,.0f}</b>\n\nفروش این تعداد تأیید شود؟",
                parse_mode="HTML", reply_markup=arsenal_sell_confirm_keyboard()
            )
            return

        if data.startswith("arsenal_sell_custom:"):
            parts=data.split(":")
            if len(parts)!=3: return
            mid, level=parts[1], int(parts[2])
            country=get_context_country(session,user, query.message.chat_id if query.message else None)
            if country is None: await query.answer("❌ کشور پیش‌فرضی ندارید.",show_alert=True); return
            available=get_missile_count(get_missile_inventory(session,country.id),mid,level)
            if available<=0: await query.answer("❌ این موشک دیگر در زرادخانه موجود نیست.",show_alert=True); return
            context.user_data["arsenal_sell_custom_pending"]={"mid":mid,"level":level,"available":available,"chat_id":query.message.chat_id if query.message else None,"message_id":query.message.message_id if query.message else None}
            context.user_data[_waiting_scope_key("arsenal_sell_custom_pending")] = int(update.effective_chat.id)
            await query.answer()
            await query.edit_message_text(
                f"✏️ <b>تعداد دلخواه برای فروش</b>\n\nحداکثر موجودی: <b>{available}</b> فروند\nعدد موردنظر را ارسال کنید:",
                parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data="arsenal_sell_quantity_back")]])
            )
            return

        if data == "arsenal_sell_quantity_back":
            custom=context.user_data.pop("arsenal_sell_custom_pending",None)
            country=get_context_country(session,user, query.message.chat_id if query.message else None)
            if country is None: await query.answer("❌ کشور پیش‌فرضی ندارید.",show_alert=True); return
            inv=get_missile_inventory(session,country.id); cfg=get_missiles_config(session)
            items=[]
            for rmid,levels in inv.items():
                rm=next((x for x in cfg.get("items",[]) if str(x.get("id"))==str(rmid)),None)
                if not rm: continue
                for rlevel,rcount in sorted((levels or {}).items(),key=lambda x:int(x[0])):
                    if int(rcount or 0)>0: items.append({"mid":str(rmid),"level":int(rlevel),"label":f"{rm.get('name','موشک')} — سطح {int(rlevel)} ({int(rcount)} فروند)"})
            await query.answer(); await query.edit_message_text("🚀 <b>لیست موشک‌های زرادخانه</b>\n\nموشک موردنظر را برای فروش انتخاب کنید:",parse_mode="HTML",reply_markup=arsenal_missile_list_keyboard(items)); return

        if data == "arsenal_sell_change_qty":
            pending=context.user_data.get("arsenal_sell_pending")
            if not pending: await query.answer("❌ عملیات فروش منقضی شده است.",show_alert=True); return
            country=get_context_country(session,user, query.message.chat_id if query.message else None)
            available=get_missile_count(get_missile_inventory(session,country.id),pending["mid"],pending["level"]) if country else 0
            if available<=0: await query.answer("❌ این موشک دیگر در زرادخانه موجود نیست.",show_alert=True); return
            context.user_data.pop("arsenal_sell_pending",None)
            await query.answer(); await query.edit_message_text("💰 <b>تعداد فروش</b>\n\nتعداد موشک‌های موردنظر را انتخاب کنید:",parse_mode="HTML",reply_markup=arsenal_sell_quantity_keyboard(pending["mid"],pending["level"],available)); return

        if data == "arsenal_sell_back":
            context.user_data.pop("arsenal_sell_pending",None)
            country=get_context_country(session,user, query.message.chat_id if query.message else None); cfg=get_missiles_config(session)
            inv=get_missile_inventory(session,country.id) if country else {}
            items=[]
            for mid,levels in inv.items():
                m=next((x for x in cfg.get("items",[]) if str(x.get("id"))==str(mid)),None)
                if not m: continue
                for level,count in sorted((levels or {}).items(),key=lambda x:int(x[0])):
                    if int(count or 0)>0: items.append({"mid":str(mid),"level":int(level),"label":f"{m.get('name','موشک')} — سطح {int(level)} ({int(count)} فروند)"})
            await query.answer(); await query.edit_message_text("🚀 <b>لیست موشک‌های زرادخانه</b>\n\nموشک موردنظر را برای فروش انتخاب کنید:",parse_mode="HTML",reply_markup=arsenal_missile_list_keyboard(items)); return

        if data == "arsenal_sell_confirm":
            pending=context.user_data.pop("arsenal_sell_pending",None)
            country=get_context_country(session,user, query.message.chat_id if query.message else None)
            if not pending or country is None: await query.answer("❌ عملیات فروش منقضی شده است.",show_alert=True); return
            mid,level=pending["mid"],int(pending["level"])
            requested=max(1,int(pending.get("quantity",1) or 1))
            inv=get_missile_inventory(session,country.id)
            count=get_missile_count(inv,mid,level)
            if count<=0: await query.answer("❌ این موشک دیگر در زرادخانه نیست.",show_alert=True); return
            sell_n=min(requested,count)
            m=next((x for x in get_missiles_config(session).get("items",[]) if str(x.get("id"))==str(mid)),None)
            cap=float((m or {}).get("base_capacity",0) or 0)
            country.arsenal_storage=max(0.0,float(getattr(country,"arsenal_storage",0) or 0)-cap*sell_n)
            country.missiles=max(0,int(getattr(country,"missiles",0) or 0)-sell_n)
            add_missile_to_inventory(session,country.id,mid,level=level,amount=-sell_n)
            country.money=float(getattr(country,"money",0) or 0)+float(pending["refund"])*sell_n
            session.commit()
            remaining_items=[]
            cfg_now=get_missiles_config(session)
            inv_now=get_missile_inventory(session,country.id)
            for rmid,levels in inv_now.items():
                rm=next((x for x in cfg_now.get("items",[]) if str(x.get("id"))==str(rmid)),None)
                if not rm: continue
                for rlevel,rcount in sorted((levels or {}).items(),key=lambda x:int(x[0])):
                    if int(rcount or 0)>0:
                        remaining_items.append({"mid":str(rmid),"level":int(rlevel),"label":f"{rm.get('name','موشک')} — سطح {int(rlevel)} ({int(rcount)} فروند)"})
            await query.answer(f"✅ {escape(pending['name'])} × {sell_n} فروخته شد. مبلغ دریافتی: {float(pending['refund'])*sell_n:,.0f}",show_alert=True)
            # نتیجه فروش در Alert نمایش داده می‌شود، اما پنل اصلی نیز بلافاصله به زرادخانه برمی‌گردد.
            acfg=get_arsenal_config(session)
            alevel=int(getattr(country,"arsenal_level",0) or 0)
            anext=acfg.get("levels",{}).get(alevel+1,{})
            astatus=construction_label(country,"arsenal")
            await query.edit_message_text(arsenal_info(country,acfg),parse_mode="HTML",reply_markup=arsenal_keyboard(alevel==0,can_upgrade_arsenal(country,acfg)[0],float(acfg.get("build_cost",{}).get("uranium",0))>0,float(anext.get("uranium",0))>0,construction_text=astatus,finish_uranium_cost=arsenal_instant_finish_uranium_cost(country,acfg)))
            return

        if data.startswith("arsenal_build_preview:"):
            country=get_context_country(session,user,query.message.chat_id if query.message else None); cfg=get_arsenal_config(session)
            payment=data.split(":",1)[1]
            if country is None: await query.answer("❌ کشور پیش‌فرضی انتخاب نشده است.",show_alert=True); return
            cost=cfg.get("build_cost",{}) or {}; labels={"money":"💰 پول","metal":"🔩 فلز","fuel":"⛽ سوخت","uranium":"☢️ اورانیوم"}
            cost_lines="\n".join(f"{labels[k]}: <b>{float(v):,.0f}</b>" for k,v in cost.items() if (payment=="uranium" and k=="uranium") or (payment=="normal" and k!="uranium"))
            text=(f"🏗️ <b>تأیید ساخت زرادخانه — سطح ۱</b>\n\n🪖 قدرت نظامی: <b>{float(cfg.get('build_military_power',0) or 0):,.0f}</b>\n🛡️ استحکام: <b>{float(cfg.get('build_strength',0) or 0):,.0f}</b>\n📦 ظرفیت مخزن: <b>{float(cfg.get('build_storage_capacity',0) or 0):,.0f}</b>\n⏱️ زمان تکمیل: <b>{float(cfg.get('build_completion_time',0) or 0):,.0f} ساعت</b>\n\n💰 <b>هزینه ساخت:</b>\n{cost_lines}\n\nآیا ساخت را تأیید می‌کنید؟")
            rows=[[InlineKeyboardButton("✅ تأیید ساخت",callback_data=f"arsenal_build:{payment}")],[InlineKeyboardButton("✏️ ویرایش",callback_data=f"arsenal_build_preview:{payment}")],[InlineKeyboardButton("🔙 برگشت",callback_data="arsenal_refresh")]]
            await query.answer(); await query.edit_message_text(text,parse_mode="HTML",reply_markup=InlineKeyboardMarkup(rows)); return

        if data.startswith("arsenal_upgrade_preview:"):
            country=get_context_country(session,user,query.message.chat_id if query.message else None); cfg=get_arsenal_config(session); payment=data.split(":",1)[1]
            if country is None: await query.answer("❌ کشور پیش‌فرضی انتخاب نشده است.",show_alert=True); return
            target=int(country.arsenal_level)+1; nd=cfg.get("levels",{}).get(target,{}) or {}; labels={"money":"💰 پول","metal":"🔩 فلز","fuel":"⛽ سوخت","uranium":"☢️ اورانیوم"}
            costs="\n".join(f"{labels[k]}: <b>{float(nd.get(k,0) or 0):,.0f}</b>" for k in labels if (payment=="uranium" and k=="uranium") or (payment=="normal" and k!="uranium"))
            text=(f"⬆️ <b>تأیید ارتقای زرادخانه به سطح {target}</b>\n\n🪖 قدرت نظامی: <b>{float(nd.get('military_power',0) or 0):,.0f}</b>\n🛡️ استحکام: <b>{float(nd.get('strength',0) or 0):,.0f}</b>\n📦 ظرفیت مخزن: <b>{float(nd.get('storage_capacity',0) or 0):,.0f}</b>\n⏱️ زمان تکمیل: <b>{float(nd.get('completion_time',0) or 0):,.0f} ساعت</b>\n\n💰 <b>هزینه ارتقا:</b>\n{costs}\n\nآیا ارتقا را تأیید می‌کنید؟")
            rows=[[InlineKeyboardButton(f"✅ تأیید ارتقا به سطح {target}",callback_data=f"arsenal_upgrade:{payment}")],[InlineKeyboardButton("✏️ ویرایش",callback_data=f"arsenal_upgrade_preview:{payment}")],[InlineKeyboardButton("🔙 برگشت",callback_data="arsenal_refresh")]]
            await query.answer(); await query.edit_message_text(text,parse_mode="HTML",reply_markup=InlineKeyboardMarkup(rows)); return

        if data.startswith("arsenal_build"):
            country=get_context_country(session,user, query.message.chat_id if query.message else None)
            if country is None:
                await query.answer("❌ کشور پیش‌فرضی انتخاب نشده است.",show_alert=True); return
            payment=data.split(":",1)[1] if ":" in data else "normal"
            cfg=get_arsenal_config(session)
            required_hq = int(cfg.get("build_required_hq_level", 1) or 1)
            current_hq = int(getattr(country, "command_center_level", 0) or 0)
            if current_hq < required_hq:
                await query.answer(f"❌ سطح مرکز فرماندهی کافی نیست.\n🏛️ سطح موردنیاز: {required_hq}", show_alert=True); return
            if payment=="uranium":
                # future-proof; build_cost_uranium isn't a separate setting for arsenal yet.
                costs={"uranium":float(cfg.get("build_cost",{}).get("uranium",0))}
                missing={r:max(0.0, float(a)-float(getattr(country,r,0.0))) for r,a in costs.items() if not resource_available(country,r,a)}
                if missing:
                    await query.answer(f"❌ اورانیوم کافی نیست.\\n☢️ موردنیاز: {missing.get('uranium',0):,.2f}",show_alert=True); return
            ok,res=build_arsenal(country,cfg,payment,session)
            if ok:
                session.commit();
                status = construction_label(country, "arsenal")
                if status:
                    await query.answer("🏗️ ساخت زرادخانه شروع شد.", show_alert=True)
                else:
                    await query.answer("🎉 زرادخانه ساخته شد.", show_alert=True)
                next_data = cfg.get("levels", {}).get(int(country.arsenal_level) + 1, {})
                await query.edit_message_text("🎉 <b>زرادخانه ساخته شد!</b>\n\n"+arsenal_info(country,cfg),parse_mode="HTML",reply_markup=arsenal_keyboard(False,can_upgrade_arsenal(country,cfg)[0],False,float(next_data.get("uranium",0))>0,construction_text=status,finish_uranium_cost=arsenal_instant_finish_uranium_cost(country,cfg))); return
            if res=="NO_TEAM": await query.answer("⛔ تمام تیم‌های ساخت‌وساز شما مشغول هستند. برای انجام Upgrade هم‌زمان بیشتر، یک تیم ساخت‌وساز دیگر تهیه کنید.",show_alert=True)
            elif res=="ALREADY_BUILT": await query.answer("⚠️ زرادخانه قبلاً ساخته شده است.",show_alert=True)
            elif res=="IN_PROGRESS": await query.answer("⏳ ساخت زرادخانه هنوز در حال تکمیل است.",show_alert=True)
            else:
                labels={"money":"💰 پول","metal":"🔩 فلز","fuel":"⛽ سوخت","uranium":"☢️ اورانیوم"}
                await query.answer("❌ منابع کافی نیست.\\n\\n"+"\n".join(f"{labels[k]} موردنیاز: {v:,.0f}" for k,v in (res.items() if isinstance(res, dict) else {})),show_alert=True)
            return

        if data.startswith("arsenal_upgrade"):
            country=get_context_country(session,user, query.message.chat_id if query.message else None)
            if country is None: await query.answer("❌ کشور پیش‌فرضی انتخاب نشده است.",show_alert=True); return
            payment=data.split(":",1)[1] if ":" in data else "normal"
            cfg=get_arsenal_config(session); ok,res=upgrade_arsenal(country,cfg,payment,session)
            if ok:
                session.commit();
                status = construction_label(country, "arsenal")
                if status:
                    await query.answer("🏗️ ارتقای زرادخانه شروع شد.", show_alert=True)
                else:
                    await query.answer("🎉 زرادخانه ارتقا یافت.", show_alert=True)
                next_data = cfg.get("levels", {}).get(int(country.arsenal_level) + 1, {})
                await query.edit_message_text(f"🎉 <b>زرادخانه به سطح {country.arsenal_level} ارتقا یافت!</b>\n\n"+arsenal_info(country,cfg),parse_mode="HTML",reply_markup=arsenal_keyboard(False,can_upgrade_arsenal(country,cfg)[0],False,float(next_data.get("uranium",0))>0,construction_text=status,finish_uranium_cost=arsenal_instant_finish_uranium_cost(country,cfg))); return
            if res=="NO_TEAM": await query.answer("⛔ تمام تیم‌های ساخت‌وساز شما مشغول هستند. برای انجام Upgrade هم‌زمان بیشتر، یک تیم ساخت‌وساز دیگر تهیه کنید.",show_alert=True)
            elif res=="MAX_LEVEL": await query.answer("🏆 به حداکثر سطح رسیدید.",show_alert=True)
            elif res=="IN_PROGRESS": await query.answer("⏳ ارتقای زرادخانه هنوز در حال تکمیل است.",show_alert=True)
            elif res=="HQ_REQUIRED": await query.answer("🏛️ سطح مرکز فرماندهی کافی نیست.",show_alert=True)
            else:
                labels={"money":"💰 پول","metal":"🔩 فلز","fuel":"⛽ سوخت","uranium":"☢️ اورانیوم"}
                await query.answer("❌ منابع کافی نیست.\\n\\n"+"\n".join(f"{labels[k]} موردنیاز: {v:,.0f}" for k,v in (res.items() if isinstance(res, dict) else {})),show_alert=True)
            return

        if data == "arsenal_finish_now":
            country=get_context_country(session,user, query.message.chat_id if query.message else None)
            if country is None:
                await query.answer("❌ کشور پیش‌فرضی انتخاب نشده است.",show_alert=True); return
            cfg=get_arsenal_config(session)
            cost=arsenal_instant_finish_uranium_cost(country,cfg)
            if cost<=0:
                await query.answer("❌ تکمیل فوری فعال نشده است یا زمان باقی‌مانده‌ای وجود ندارد.",show_alert=True); return
            if not resource_available(country,"uranium",cost):
                await query.answer(f"❌ اورانیوم کافی نیست.\n☢️ موردنیاز: {cost:,.2f}",show_alert=True); return
            ok,res=finish_arsenal_construction_now(country,cfg,session)
            if not ok:
                await query.answer("❌ تکمیل فوری انجام نشد.",show_alert=True); return
            session.commit()
            await query.answer(f"✅ زرادخانه فوراً تکمیل شد.\n☢️ مصرف: {float(res):,.0f}",show_alert=True)
            return

        if data == "arsenal_cancel":
            country=get_context_country(session,user, query.message.chat_id if query.message else None)
            if country is None:
                await query.answer("❌ کشور پیش‌فرضی انتخاب نشده است.",show_alert=True); return
            remaining,target=construction_remaining(country,"arsenal")
            if remaining<=0 or not target:
                await query.answer("⚠️ زرادخانه در حال ساخت یا ارتقا نیست.",show_alert=True); return
            await query.answer()
            await query.edit_message_text(
                "⚠️ <b>لغو ساخت/ارتقای زرادخانه</b>\n\nآیا مطمئن هستید که می‌خواهید عملیات لغو شود؟\n\n💡 در صورت تأیید، <b>۵۰٪ منابع پرداخت‌شده</b> به شما برگردانده می‌شود.",
                parse_mode="HTML", reply_markup=arsenal_cancel_confirm_keyboard()
            )
            return

        if data == "arsenal_cancel_back":
            country=get_context_country(session,user, query.message.chat_id if query.message else None)
            if country is None:
                await query.answer("❌ کشور پیش‌فرضی انتخاب نشده است.",show_alert=True); return
            cfg=get_arsenal_config(session); status=construction_label(country,"arsenal")
            await query.answer()
            await query.edit_message_text(arsenal_info(country,cfg),parse_mode="HTML",reply_markup=arsenal_keyboard(int(getattr(country,"arsenal_level",0))==0,can_upgrade_arsenal(country,cfg)[0],float(cfg.get("build_cost",{}).get("uranium",0))>0,float(cfg.get("levels",{}).get(int(getattr(country,"arsenal_level",0))+1,{}).get("uranium",0))>0,construction_text=status,finish_uranium_cost=arsenal_instant_finish_uranium_cost(country,cfg)))
            return

        if data == "arsenal_cancel_confirm":
            country=get_context_country(session,user, query.message.chat_id if query.message else None)
            if country is None:
                await query.answer("❌ کشور پیش‌فرضی انتخاب نشده است.",show_alert=True); return
            ok,refund=cancel_arsenal_construction(country,get_arsenal_config(session),session)
            if not ok:
                await query.answer("⚠️ زرادخانه در حال ساخت یا ارتقا نیست.",show_alert=True); return
            session.commit()
            await query.answer("❌ عملیات لغو شد و نصف منابع پرداختی برگشت داده شد.",show_alert=True)
            cfg=get_arsenal_config(session)
            level=int(getattr(country,"arsenal_level",0)); nxt=cfg.get("levels",{}).get(level+1,{})
            await query.edit_message_text(arsenal_info(country,cfg),parse_mode="HTML",reply_markup=arsenal_keyboard(level==0,can_upgrade_arsenal(country,cfg)[0],float(cfg.get("build_cost",{}).get("uranium",0))>0,float(nxt.get("uranium",0))>0))
            return

        if data.startswith("metal_mine_build_preview:"):
            country=get_context_country(session,user,query.message.chat_id if query.message else None); cfg=get_metal_mine_config(session); payment=data.split(":",1)[1]
            if country is None: await query.answer("❌ کشور پیش‌فرضی انتخاب نشده است.",show_alert=True); return
            cost=cfg.get("build_cost",{}) or {}; labels={"money":"💰 پول","metal":"🔩 فلز","fuel":"⛽ سوخت","uranium":"☢️ اورانیوم"}
            costs="\n".join(f"{labels[k]}: <b>{float(v):,.0f}</b>" for k,v in cost.items() if (payment=="uranium" and k=="uranium") or (payment=="normal" and k!="uranium"))
            text=(f"🏗️ <b>تأیید ساخت معدن فلز — سطح ۱</b>\n\n🪖 قدرت نظامی: <b>{float(cfg.get('build_military_power',0) or 0):,.0f}</b>\n🛡️ استحکام: <b>{float(cfg.get('build_strength',0) or 0):,.0f}</b>\n⚙️ تولید در ساعت: <b>{float(cfg.get('build_production_per_hour',0) or 0):,.0f} فلز</b>\n📦 ظرفیت مخزن: <b>{float(cfg.get('build_storage_capacity',0) or 0):,.0f}</b>\n⏱️ زمان تکمیل: <b>{float(cfg.get('build_completion_time',0) or 0):,.0f} ساعت</b>\n\n💰 <b>هزینه ساخت:</b>\n{costs}\n\nآیا ساخت را تأیید می‌کنید؟")
            rows=[[InlineKeyboardButton("✅ تأیید ساخت",callback_data=f"metal_mine_build:{payment}")],[InlineKeyboardButton("✏️ ویرایش",callback_data=f"metal_mine_build_preview:{payment}")],[InlineKeyboardButton("🔙 برگشت",callback_data="metal_mine_refresh")]]
            await query.answer(); await query.edit_message_text(text,parse_mode="HTML",reply_markup=InlineKeyboardMarkup(rows)); return

        if data.startswith("metal_mine_upgrade_preview:"):
            country=get_context_country(session,user,query.message.chat_id if query.message else None); cfg=get_metal_mine_config(session); payment=data.split(":",1)[1]
            if country is None: await query.answer("❌ کشور پیش‌فرضی انتخاب نشده است.",show_alert=True); return
            target=int(country.metal_mine_level)+1; nd=cfg.get("levels",{}).get(target,{}) or {}; labels={"money":"💰 پول","metal":"🔩 فلز","fuel":"⛽ سوخت","uranium":"☢️ اورانیوم"}
            costs="\n".join(f"{labels[k]}: <b>{float(nd.get(k,0) or 0):,.0f}</b>" for k in labels if (payment=="uranium" and k=="uranium") or (payment=="normal" and k!="uranium"))
            text=(f"⬆️ <b>تأیید ارتقای معدن فلز به سطح {target}</b>\n\n⚙️ تولید در ساعت: <b>{float(nd.get('production_per_hour',0) or 0):,.0f} فلز</b>\n📦 ظرفیت مخزن: <b>{float(nd.get('storage_capacity',0) or 0):,.0f}</b>\n🪖 قدرت نظامی: <b>{float(nd.get('military_power',0) or 0):,.0f}</b>\n🛡️ استحکام: <b>{float(nd.get('strength',0) or 0):,.0f}</b>\n⏱️ زمان تکمیل: <b>{float(nd.get('completion_time',0) or 0):,.0f} ساعت</b>\n\n💰 <b>هزینه ارتقا:</b>\n{costs}\n\nآیا ارتقا را تأیید می‌کنید؟")
            rows=[[InlineKeyboardButton(f"✅ تأیید ارتقا به سطح {target}",callback_data=f"metal_mine_upgrade:{payment}")],[InlineKeyboardButton("✏️ ویرایش",callback_data=f"metal_mine_upgrade_preview:{payment}")],[InlineKeyboardButton("🔙 برگشت",callback_data="metal_mine_refresh")]]
            await query.answer(); await query.edit_message_text(text,parse_mode="HTML",reply_markup=InlineKeyboardMarkup(rows)); return

        if data.startswith("metal_mine_build"):
            country = get_context_country(session, user, query.message.chat_id if query.message else None)
            if country is None:
                session.commit()
                await query.edit_message_text("❌ کشور پیش‌فرضی انتخاب نشده است.", reply_markup=private_main_keyboard())
                return

            payment = data.split(":", 1)[1] if ":" in data else "normal"
            cfg = get_metal_mine_config(session)
            required_hq = int(cfg.get("build_required_hq_level", 1) or 1)
            current_hq = int(getattr(country, "command_center_level", 0) or 0)
            if current_hq < required_hq:
                await query.answer(f"❌ سطح مرکز فرماندهی کافی نیست.\n🏛️ سطح موردنیاز: {required_hq}", show_alert=True); return
            success, result = build_metal_mine(country, cfg, payment=payment, session=session)
            if success:
                session.commit()
                status = construction_label(country, "metal_mine")
                await query.answer("🏗️ ساخت معدن فلز شروع شد.", show_alert=True) if status else await query.answer("🎉 معدن فلز ساخته شد.", show_alert=True)
                await query.edit_message_text(
                    f"🎉 <b>معدن فلز ساخته شد!</b>\n\n{metal_mine_info(country, get_metal_mine_config(session))}",
                    parse_mode="HTML",
                    reply_markup=metal_mine_keyboard(
                        can_build=False, can_collect=True,
                        can_upgrade=can_upgrade_metal_mine(country, get_metal_mine_config(session))[0],
                        can_upgrade_uranium=float(get_metal_mine_config(session).get("levels", {}).get(country.metal_mine_level + 1, {}).get("uranium", 0)) > 0,
                        construction_text=status,
                        finish_uranium_cost=metal_mine_instant_finish_uranium_cost(country, get_metal_mine_config(session)),
                    ),
                )
                return

            session.rollback()
            names = {"money": "💰 پول", "metal": "🔩 فلز", "fuel": "⛽ سوخت", "uranium": "☢️ اورانیوم"}
            if result == "NO_TEAM":
                text = "⛔ تمام تیم‌های ساخت‌وساز شما مشغول هستند. برای انجام Upgrade هم‌زمان بیشتر، یک تیم ساخت‌وساز دیگر تهیه کنید."
            elif result == "ALREADY_BUILT":
                text = "⚠️ <b>معدن فلز قبلاً ساخته شده است.</b>"
            else:
                if result == "HQ_REQUIRED":
                    detail = "🏛️ ابتدا مرکز فرماندهی را به سطح موردنیاز برسانید."
                elif isinstance(result, dict):
                    detail = "\n".join(f"{names.get(k,k)}: {float(v):,.0f}" for k, v in result.items())
                else:
                    detail = str(result)
                text = "❌ <b>ساخت انجام نشد.</b>\n\n" + detail
            country = get_context_country(session, user, query.message.chat_id if query.message else None)
            session.commit()
            if result == "ALREADY_BUILT":
                await query.answer("⚠️ معدن فلز قبلاً ساخته شده است.", show_alert=True)
            elif result == "IN_PROGRESS":
                await query.answer("⏳ ساخت معدن فلز هنوز در حال تکمیل است.", show_alert=True)
            else:
                # در ساخت با اورانیوم، هشدار باید مستقیماً روی همان Callback
                # نمایش داده شود و پیام اصلی معدن به هیچ وجه ادیت نشود.
                if result == "HQ_REQUIRED":
                    await query.answer("🏛️ ابتدا مرکز فرماندهی را به سطح موردنیاز برسانید.", show_alert=True)
                elif payment == "uranium" and isinstance(result, dict) and "uranium" in result:
                    required = float(result["uranium"])
                    await query.answer(
                        f"❌ اورانیوم کافی نیست.\n\n☢️ اورانیوم موردنیاز: {required:,.2f}",
                        show_alert=True,
                    )
                else:
                    if isinstance(result, dict):
                        missing_text = "\n".join(f"{names.get(k,k)} موردنیاز: <b>{float(v):,.0f}</b>" for k, v in result.items())
                    else:
                        missing_text = str(result)
                    await query.answer(f"❌ منابع کافی نیست.\n\n{missing_text}", show_alert=True)
            return

        if data == "metal_mine_finish_now":
            country = get_context_country(session, user, query.message.chat_id if query.message else None)
            if country is None:
                await query.answer("❌ کشور پیش‌فرضی انتخاب نشده است.", show_alert=True); return
            cfg = get_metal_mine_config(session)
            cost = metal_mine_instant_finish_uranium_cost(country, cfg)
            if cost <= 0:
                await query.answer("❌ تکمیل فوری فعال نشده است یا زمان باقی‌مانده‌ای وجود ندارد.", show_alert=True); return
            if not resource_available(country, "uranium", cost):
                await query.answer(f"❌ اورانیوم کافی نیست.\n☢️ موردنیاز: {cost:,.2f}", show_alert=True); return
            ok, res = finish_metal_mine_construction_now(country, cfg, session)
            if not ok:
                await query.answer("❌ تکمیل فوری معدن انجام نشد.", show_alert=True); return
            session.commit()
            await query.answer(f"✅ معدن فلز فوراً تکمیل شد.\n☢️ مصرف: {float(res):,.0f}", show_alert=True)
            cfg = get_metal_mine_config(session)
            next_data = cfg.get("levels", {}).get(country.metal_mine_level + 1, {})
            await query.edit_message_text(
                metal_mine_info(country, cfg), parse_mode="HTML",
                reply_markup=metal_mine_keyboard(False, True, can_upgrade_metal_mine(country, cfg)[0], False, float(next_data.get("uranium", 0)) > 0)
            )
            return

        if data == "metal_mine_cancel":
            country = get_context_country(session, user, query.message.chat_id if query.message else None)
            if country is None:
                await query.answer("❌ کشور پیش‌فرضی انتخاب نشده است.", show_alert=True); return
            remaining, target = construction_remaining(country, "metal_mine")
            if remaining <= 0 or not target:
                await query.answer("⚠️ معدن فلز در حال ساخت یا ارتقا نیست.", show_alert=True); return
            await query.answer()
            await query.edit_message_text(
                "⚠️ <b>لغو ساخت/ارتقای معدن فلز</b>\n\nآیا مطمئن هستید که می‌خواهید عملیات لغو شود؟\n\n💡 در صورت تأیید، <b>۵۰٪ منابع پرداخت‌شده</b> به شما برگردانده می‌شود.",
                parse_mode="HTML", reply_markup=metal_mine_cancel_confirm_keyboard()
            )
            return

        if data == "metal_mine_cancel_back":
            country = get_context_country(session, user, query.message.chat_id if query.message else None)
            if country is None:
                await query.answer("❌ کشور پیش‌فرضی انتخاب نشده است.", show_alert=True); return
            cfg = get_metal_mine_config(session)
            status = construction_label(country, "metal_mine")
            next_data = cfg.get("levels", {}).get(country.metal_mine_level + 1, {})
            await query.answer()
            await query.edit_message_text(
                metal_mine_info(country, cfg), parse_mode="HTML",
                reply_markup=metal_mine_keyboard(False, True, can_upgrade_metal_mine(country, cfg)[0], False, float(next_data.get("uranium", 0)) > 0, status, metal_mine_instant_finish_uranium_cost(country, cfg))
            )
            return

        if data == "metal_mine_cancel_confirm":
            country = get_context_country(session, user, query.message.chat_id if query.message else None)
            if country is None:
                await query.answer("❌ کشور پیش‌فرضی انتخاب نشده است.", show_alert=True); return
            ok, refund = cancel_metal_mine_construction(country, get_metal_mine_config(session), session)
            if not ok:
                await query.answer("⚠️ معدن فلز در حال ساخت یا ارتقا نیست.", show_alert=True); return
            session.commit()
            await query.answer("❌ عملیات لغو شد و نصف منابع پرداختی برگشت داده شد.", show_alert=True)
            cfg = get_metal_mine_config(session)
            next_data = cfg.get("levels", {}).get(country.metal_mine_level + 1, {})
            await query.edit_message_text(
                metal_mine_info(country, cfg), parse_mode="HTML",
                reply_markup=metal_mine_keyboard(country.metal_mine_level == 0, True, can_upgrade_metal_mine(country, cfg)[0], float(cfg.get("build_cost", {}).get("uranium", 0)) > 0, float(next_data.get("uranium", 0)) > 0)
            )
            return

        if data == "metal_mine_refresh":
            try:
                country = get_context_country(session, user, query.message.chat_id if query.message else None)
                if country is None:
                    await query.answer("❌ کشور پیش‌فرضی انتخاب نشده است.", show_alert=True); return
                cfg = get_metal_mine_config(session) or {}
                before_level = int(getattr(country, "metal_mine_level", 0) or 0)
                finalize_construction(country)
                session.commit()
                current_level = int(getattr(country, "metal_mine_level", 0) or 0)
                nxt = cfg.get("levels", {}).get(current_level + 1, {}) or {}
                can_upgrade = bool(can_upgrade_metal_mine(country, cfg)[0])
                can_upgrade_uranium = float(nxt.get("uranium", 0) or 0) > 0
                status = construction_label(country, "metal_mine")
                markup = metal_mine_keyboard(False, True, can_upgrade, False, can_upgrade_uranium, status, metal_mine_instant_finish_uranium_cost(country, cfg))
                if current_level > before_level:
                    await query.answer(f"🎉 ارتقای معدن فلز به سطح {current_level} تکمیل شد.", show_alert=True)
                    await query.edit_message_text(metal_mine_info(country, cfg), parse_mode="HTML", reply_markup=markup)
                else:
                    await query.answer("🔄 اطلاعات معدن به‌روزرسانی شد.")
                    await query.edit_message_text(metal_mine_info(country, cfg), parse_mode="HTML", reply_markup=markup)
            except Exception:
                session.rollback()
                await query.answer("❌ به‌روزرسانی معدن فلز با خطا روبه‌رو شد. دوباره تلاش کنید.", show_alert=True)
            return

        if data == "metal_mine_collect":
            try:
                country = get_context_country(session, user, query.message.chat_id if query.message else None)
                if country is None:
                    await query.answer("❌ کشور پیش‌فرضی انتخاب نشده است.", show_alert=True)
                    return
                cfg = get_metal_mine_config(session) or {}
                amount = collect_metal_mine(country, cfg)
                next_data = cfg.get("levels", {}).get(int(getattr(country, "metal_mine_level", 0)) + 1, {}) or {}
                max_level = int(cfg.get("max_level", 100) or 100)
                can_upgrade = int(getattr(country, "metal_mine_level", 0)) < max_level and bool(next_data) and bool(next_data.get("active", True))
                can_upgrade_uranium = float(next_data.get("uranium", 0) or 0) > 0
                session.commit()
                amount_text = f"{float(amount or 0):,.0f}"
                await query.answer((f"📥 {amount_text} فلز دریافت کردید." if float(amount or 0) > 0 else "📦 فعلاً فلز آماده دریافت نیست."), show_alert=True)
                await query.edit_message_text(
                    metal_mine_info(country, cfg),
                    parse_mode="HTML",
                    reply_markup=metal_mine_keyboard(False, True, can_upgrade, False, can_upgrade_uranium),
                )
            except Exception:
                session.rollback()
                await query.answer("❌ دریافت فلز استخراج‌شده با خطا روبه‌رو شد. دوباره تلاش کنید.", show_alert=True)
            return

        if data.startswith("metal_mine_upgrade"):
            country = get_context_country(session, user, query.message.chat_id if query.message else None)
            if country is None:
                session.commit()
                await query.edit_message_text("❌ کشور پیش‌فرضی انتخاب نشده است.", reply_markup=private_main_keyboard())
                return

            payment = data.split(":", 1)[1] if ":" in data else "normal"
            success, result = upgrade_metal_mine(country, get_metal_mine_config(session), payment=payment, session=session)
            if success:
                session.commit()
                status = construction_label(country, "metal_mine")
                await query.answer("🏗️ ارتقای معدن فلز شروع شد.", show_alert=True) if status else await query.answer("🎉 معدن فلز ارتقا یافت.", show_alert=True)
                await query.edit_message_text(
                    metal_mine_info(country, get_metal_mine_config(session)),
                    parse_mode="HTML",
                    reply_markup=metal_mine_keyboard(
                    False, True, can_upgrade_metal_mine(country, get_metal_mine_config(session))[0],
                    can_upgrade_uranium=float(get_metal_mine_config(session).get("levels", {}).get(country.metal_mine_level + 1, {}).get("uranium", 0)) > 0,
                    construction_text=status,
                    finish_uranium_cost=metal_mine_instant_finish_uranium_cost(country, get_metal_mine_config(session)),
                ),
                )
                return

            session.rollback()
            if result == "NO_TEAM":
                text = "⛔ تمام تیم‌های ساخت‌وساز شما مشغول هستند. برای انجام Upgrade هم‌زمان بیشتر، یک تیم ساخت‌وساز دیگر تهیه کنید."
            elif result == "IN_PROGRESS":
                text = "⏳ ساخت یا ارتقای معدن فلز هنوز در حال تکمیل است."
            elif result == "NOT_BUILT":
                text = "❌ ابتدا معدن فلز را بسازید."
            elif result == "MAX_LEVEL":
                text = "🏆 معدن فلز به حداکثر سطح رسیده است."
            else:
                names = {"money": "💰 پول", "metal": "🔩 فلز", "fuel": "⛽ سوخت", "uranium": "☢️ اورانیوم"}
                detail = "\n".join(f"{names.get(k,k)}: {float(v):,.0f}" for k, v in result.items()) if isinstance(result, dict) else str(result)
                text = "❌ <b>منابع کافی برای ارتقا ندارید.</b>\n\n" + detail
            country = get_context_country(session, user, query.message.chat_id if query.message else None)
            session.commit()
            if isinstance(result, str) and result not in {"NOT_BUILT", "MAX_LEVEL"} and country:
                names = {"money": "💰 پول", "metal": "🔩 فلز", "fuel": "⛽ سوخت", "uranium": "☢️ اورانیوم"}
                missing_text = "\n".join(f"{names.get(k,k)} موردنیاز: <b>{float(v):,.0f}</b>" for k, v in result.items()) if isinstance(result, dict) else str(result)
                await query.answer(f"❌ منابع کافی نیست.\n\n{missing_text}", show_alert=True)
            else:
                await query.answer(text.replace("<b>", "").replace("</b>", ""), show_alert=True)
            return

        if data == "hq_technology":
            try:
                country = get_context_country(session, user, query.message.chat_id if query.message else None)
                if country is None:
                    await query.answer("❌ کشور پیش‌فرضی انتخاب نشده است.", show_alert=True); return
                markup = missile_technology_keyboard()
                await query.answer()
                await query.edit_message_text(
                    "🧬 <b>فناوری نظامی</b>\n\nبخش موردنظر را انتخاب کنید:",
                    parse_mode="HTML", reply_markup=markup
                )
            except Exception:
                await query.answer("❌ باز کردن فناوری نظامی با خطا روبه‌رو شد. دوباره تلاش کنید.", show_alert=True)
            return

        if data == "hq_tech_missiles":
            country = get_context_country(session, user, query.message.chat_id if query.message else None)
            if country is None:
                await query.answer("❌ کشور پیش‌فرضی انتخاب نشده است.", show_alert=True); return
            await query.answer()
            await query.edit_message_text(
                "🚀 <b>موشک‌ها</b>\n\nنوع موشک را انتخاب کنید:",
                parse_mode="HTML",
                reply_markup=missile_technology_types_keyboard(),
            )
            return

        if data.startswith("hq_tech_type:"):
            country = get_context_country(session, user, query.message.chat_id if query.message else None)
            if country is None:
                await query.answer("❌ کشور پیش‌فرضی انتخاب نشده است.", show_alert=True); return
            missile_type = data.split(":", 1)[1]
            cfg = get_missiles_config(session)
            missiles = [m for m in cfg.get("items", []) if str(m.get("type", "")) == missile_type and bool(m.get("active", False))]
            await query.answer()
            if not missiles:
                await query.edit_message_text(
                    f"🚀 <b>موشک‌های {escape(missile_type)}</b>\n\nℹ️ هنوز موشکی از این نوع ثبت نشده است.",
                    parse_mode="HTML",
                    reply_markup=missile_technology_list_keyboard([], missile_type),
                )
                return
            
            for _m in missiles:
                finalize_missile_tech_upgrade(session, country.id, str(_m.get("id")))
            session.commit()
            tech_levels = {str(m.get("id")): get_missile_tech_level(session, country.id, str(m.get("id"))) for m in missiles}
            await query.edit_message_text(
                f"🚀 <b>موشک‌های {escape(missile_type)}</b>\n\nموشک موردنظر برای ارتقا را انتخاب کنید:",
                parse_mode="HTML",
                reply_markup=missile_technology_list_keyboard(missiles, missile_type, tech_levels),
            )
            return

        if data == "hq_technology_back":
            country = get_context_country(session, user, query.message.chat_id if query.message else None)
            if country is None:
                await query.answer("❌ کشور پیش‌فرضی انتخاب نشده است.", show_alert=True); return
            cfg = get_hq_config(session)
            status = construction_label(country, "command_center")
            await query.answer()
            await query.edit_message_text(hq_info(country, cfg), parse_mode="HTML", reply_markup=hq_keyboard(can_upgrade_hq(country, cfg)[0], built=int(country.command_center_level)>0, construction_text=status, in_progress=bool(status), finish_uranium_cost=hq_instant_finish_uranium_cost(country,cfg), build_uranium=float(hq_build_cost(cfg).get("uranium",0))>0, upgrade_uranium=float((hq_upgrade_cost(country.command_center_level,cfg) or {}).get("uranium",0))>0))
            return

        if data.startswith("hq_tech_missile_back:"):
            mid = data.split(":", 1)[1]
            country = get_context_country(session, user, query.message.chat_id if query.message else None)
            cfg = get_missiles_config(session)
            m = next((x for x in cfg.get("items", []) if str(x.get("id")) == str(mid)), None)
            if country is None or not m:
                await query.answer("❌ اطلاعات موشک پیدا نشد.", show_alert=True); return
            missile_type = str(m.get("type", ""))
            missiles = [x for x in cfg.get("items", []) if str(x.get("type", "")) == missile_type and bool(x.get("active", False))]
            for _m in missiles:
                finalize_missile_tech_upgrade(session, country.id, str(_m.get("id")))
            session.commit()
            tech_levels = {str(x.get("id")): get_missile_tech_level(session, country.id, str(x.get("id"))) for x in missiles}
            await query.answer()
            await query.edit_message_text(
                f"🚀 <b>موشک‌های {escape(missile_type)}</b>\n\nموشک موردنظر برای ارتقا را انتخاب کنید:",
                parse_mode="HTML",
                reply_markup=missile_technology_list_keyboard(missiles, missile_type, tech_levels),
            )
            return

        if data.startswith("hq_tech_missile:"):
            parts = data.split(":")
            if len(parts) < 2: return
            mid = parts[1]
            country = get_context_country(session, user, query.message.chat_id if query.message else None)
            cfg = get_missiles_config(session)
            m = next((x for x in cfg.get("items",[]) if str(x.get("id")) == str(mid)), None)
            if country is None or not m:
                await query.answer("❌ اطلاعات موشک پیدا نشد.", show_alert=True); return
            finalize_missile_tech_upgrade(session, country.id, mid)
            session.commit()
            current_level = get_missile_tech_level(session, country.id, mid)
            max_level = int(m.get("max_level",100) or 100)
            levels = m.get("levels") or {}
            data = levels.get(str(current_level), {}) or {}
            remaining, target = missile_tech_upgrade_remaining(session, country.id, mid)
            if remaining > 0:
                text = (f"🧬 <b>فناوری نظامی — {escape(str(m.get('name','موشک')))}</b>\n\n"
                        f"⏳ <b>در حال ارتقا به سطح {target}</b>\n"
                        f"💳 روش ارتقا: <b>{'با اورانیوم' if (get_missile_tech_construction(session,country.id,mid) or {}).get('payment') == 'uranium' else 'با پول، فلز و سوخت'}</b>\n"
                        f"⏱️ زمان باقی‌مانده: <b>{remaining/60:,.0f} دقیقه</b>")
                await query.answer(); await query.edit_message_text(text,parse_mode="HTML",reply_markup=missile_upgrade_levels_keyboard(mid,current_level,None,True)); return
            next_level = current_level + 1 if current_level < max_level else None
            current_power = float(data.get("power",0) or 0) or float(m.get("base_power",0) or 0)
            current_time = float(data.get("target_time",0) or 0) or float(m.get("base_target_time",0) or 0)
            current_cost = float(data.get("cost",0) or 0) or float(m.get("base_cost",0) or 0)
            text = (f"🧬 <b>فناوری نظامی — {escape(str(m.get('name','موشک')))}</b>\n\n"
                    f"🔰 <b>سطح فعلی: {current_level}</b>\n"
                    f"🪖 قدرت: <b>{current_power:,.0f}</b>\n"
                    f"⏱️ زمان برخورد با هدف: <b>{current_time:,.0f} ثانیه</b>\n"
                    f"💰 هزینه: <b>{current_cost:,.0f}</b>")
            if next_level:
                nd=levels.get(str(next_level),{}) or {}
                hq_req=int(nd.get("hq_required",m.get("hq_required",1)) or 1)
                arsenal_req=int(nd.get("arsenal_required",m.get("arsenal_required",1)) or 1)
                lock=[]
                if int(getattr(country,"command_center_level",0) or 0)<hq_req: lock.append(f"🏛️ سطح مرکز فرماندهی لازم: <b>{hq_req}</b>")
                if int(getattr(country,"arsenal_level",0) or 0)<arsenal_req: lock.append(f"🏭 سطح زرادخانه لازم: <b>{arsenal_req}</b>")
                _has_uranium = float(nd.get("upgrade_uranium",0) or 0) > 0
                _has_normal = any(float(nd.get(k,0) or 0) > 0 for k in ("upgrade_money","upgrade_metal","upgrade_fuel"))
                _method = "با اورانیوم" if _has_uranium and not _has_normal else "با پول، فلز و سوخت"
                text += (f"\n\n⬆️ <b>سطح بعدی: {next_level}</b>\n💳 روش ارتقا: <b>{_method}</b>")
                if lock: text += "\n\n🔒 <b>شرایط ارتقا فراهم نیست:</b>\n" + "\n".join(lock)
                await query.answer(); await query.edit_message_text(text,parse_mode="HTML",reply_markup=missile_upgrade_levels_keyboard(mid,current_level,None if lock else next_level)); return
            await query.answer(); await query.edit_message_text(text+"\n\n🏆 <b>موشک به حداکثر سطح رسیده است.</b>",parse_mode="HTML",reply_markup=missile_upgrade_levels_keyboard(mid,current_level,None)); return

        if data.startswith("hq_tech_upgrade:"):
            parts=data.split(":")
            if len(parts)<3: return
            mid,target_level=parts[1],int(parts[2]); payment=parts[3] if len(parts)>3 else "normal"
            country=get_context_country(session,user, query.message.chat_id if query.message else None); cfg=get_missiles_config(session)
            m=next((x for x in cfg.get("items",[]) if str(x.get("id"))==str(mid)),None)
            if country is None or not m: await query.answer("❌ اطلاعات موشک پیدا نشد.",show_alert=True); return
            finalize_missile_tech_upgrade(session,country.id,mid); current_level=get_missile_tech_level(session,country.id,mid)
            if target_level != current_level+1: await query.answer("❌ این سطح ارتقا معتبر نیست.",show_alert=True); return
            data=(m.get("levels") or {}).get(str(target_level),{}) or {}
            hq_req=int(data.get("hq_required",m.get("hq_required",1)) or 1); arsenal_req=int(data.get("arsenal_required",m.get("arsenal_required",1)) or 1)
            if int(getattr(country,"command_center_level",0) or 0)<hq_req: await query.answer(f"❌ سطح مرکز فرماندهی کافی نیست. موردنیاز: {hq_req}",show_alert=True); return
            if int(getattr(country,"arsenal_level",0) or 0)<arsenal_req: await query.answer(f"❌ سطح زرادخانه کافی نیست. موردنیاز: {arsenal_req}",show_alert=True); return
            ok,res=start_missile_tech_upgrade(session,country,mid,target_level,data,payment)
            if not ok:
                if res == "NO_TEAM":
                    await query.answer("⛔ تمام تیم‌های ساخت‌وساز شما مشغول هستند. برای انجام Upgrade هم‌زمان بیشتر، یک تیم ساخت‌وساز دیگر تهیه کنید.",show_alert=True); return
                names={"money":"💰 پول","metal":"🔩 فلز","fuel":"⛽ سوخت","uranium":"☢️ اورانیوم"}
                detail="\n".join(f"{names.get(k,k)}: {float(v):,.0f}" for k,v in res.items()) if isinstance(res,dict) else ("❌ ارتقا در حال انجام است." if res=="IN_PROGRESS" else str(res))
                await query.answer("❌ ارتقا انجام نشد.",show_alert=True); return
            session.commit()
            if res=="DONE":
                await query.answer("✅ ارتقا کامل شد.",show_alert=True)
                lvl=int(target_level)
                nd=(m.get("levels") or {}).get(str(lvl),{}) or {}
                next_level=lvl+1 if lvl<int(m.get("max_level",100) or 100) else None
                text=(f"🧬 <b>فناوری نظامی — {escape(str(m.get('name','موشک')))}</b>\n\n"
                      f"🔰 <b>سطح فعلی: {lvl}</b>\n"
                      f"🪖 قدرت: <b>{float(nd.get('power',0) or 0):,.0f}</b>\n"
                      f"⏱️ زمان برخورد: <b>{float(nd.get('target_time',0) or 0):,.0f} ثانیه</b>")
                await query.edit_message_text(text,parse_mode="HTML",reply_markup=missile_upgrade_levels_keyboard(mid,lvl,next_level))
            else:
                await query.answer("⏳ ارتقا شروع شد.",show_alert=True)
                await query.edit_message_text(f"🧬 <b>فناوری نظامی — {escape(str(m.get('name','موشک')))}</b>\n\n⏳ <b>در حال ارتقا به سطح {target_level}</b>\n💳 روش پرداخت: <b>{'اورانیوم' if payment=='uranium' else 'پول، فلز و سوخت'}</b>\n⏱️ زمان ارتقا: <b>{float(data.get('upgrade_time',0) or 0):,.2f} ساعت</b>",parse_mode="HTML",reply_markup=missile_upgrade_levels_keyboard(mid,current_level,None,True))
            return

        if data.startswith("hq_tech_cancel_confirm:"):
            mid=data.split(":",1)[1]; country=get_context_country(session,user, query.message.chat_id if query.message else None)
            if country is None: await query.answer("❌ کشور پیش‌فرضی ندارید.",show_alert=True); return
            ok,refund=cancel_missile_tech_upgrade(session,country,mid)
            if not ok: await query.answer("⚠️ ارتقای موشک در حال انجام نیست.",show_alert=True); return
            session.commit(); await query.answer("✅ ارتقا لغو شد و بازپرداخت انجام شد.",show_alert=True)
            lvl=get_missile_tech_level(session,country.id,mid)
            await query.edit_message_text("🧬 <b>ارتقای موشک لغو شد.</b>\n\n💰 <b>مبلغ بازگشتی:</b>\n" + "\n".join(f"{ {'money':'💰 پول','metal':'🔩 فلز','fuel':'⛽ سوخت','uranium':'☢️ اورانیوم'}.get(k,k) }: <b>{float(v):,.2f}</b>" for k,v in refund.items()),parse_mode="HTML",reply_markup=missile_upgrade_levels_keyboard(mid,lvl,lvl+1)); return

        if data.startswith("hq_tech_cancel:"):
            mid=data.split(":",1)[1]; country=get_context_country(session,user, query.message.chat_id if query.message else None)
            if country is None: await query.answer("❌ کشور پیش‌فرضی ندارید.",show_alert=True); return
            data=get_missile_tech_construction(session,country.id,mid)
            if not data:
                await query.answer("⚠️ ارتقای موشک در حال انجام نیست.",show_alert=True); return
            paid=data.get("paid") or {}
            labels={"money":"💰 پول","metal":"🔩 فلز","fuel":"⛽ سوخت","uranium":"☢️ اورانیوم"}
            refund_lines=[f"{labels.get(k,k)}: <b>{float(v or 0)*0.5:,.2f}</b>" for k,v in paid.items() if float(v or 0)>0]
            refund_text="\n".join(refund_lines) or "موردی برای بازپرداخت وجود ندارد."
            await query.answer()
            await query.edit_message_text(
                "⚠️ <b>تأیید لغو ارتقا</b>\n\n"
                "آیا مطمئن هستید که ارتقای این موشک لغو شود؟\n\n"
                "💰 <b>مبلغ بازگشتی (۵۰٪ هزینه پرداخت‌شده):</b>\n" + refund_text,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ تأیید برگشت",callback_data=f"hq_tech_cancel_confirm:{mid}")],
                    [InlineKeyboardButton("🔙 بازگشت",callback_data=f"hq_tech_missile:{mid}")],
                ])
            ); return

        if data.startswith("hq_tech_finish_now:"):
            mid=data.split(":",1)[1]; country=get_context_country(session,user, query.message.chat_id if query.message else None); cfg=get_missiles_config(session); m=next((x for x in cfg.get("items",[]) if str(x.get("id"))==str(mid)),None)
            if country is None or not m: await query.answer("❌ اطلاعات موشک پیدا نشد.",show_alert=True); return
            cost=missile_tech_instant_finish_uranium_cost(session,country,mid,m)
            if cost<=0: await query.answer("❌ تکمیل فوری فعال نیست.",show_alert=True); return
            if not resource_available(country,"uranium",cost): await query.answer(f"❌ اورانیوم کافی نیست. موردنیاز: {cost:,.2f}",show_alert=True); return
            ok,res=finish_missile_tech_upgrade_now(session,country,mid,m)
            if not ok: await query.answer("❌ تکمیل فوری انجام نشد.",show_alert=True); return
            session.commit(); lvl=get_missile_tech_level(session,country.id,mid); await query.answer(f"✅ فناوری موشک به سطح {lvl} رسید.\n☢️ مصرف اورانیوم: {res:,.2f}",show_alert=True)
            # پیام تأیید فقط به‌صورت پنجره نمایش داده می‌شود؛ پیام اصلی به صفحه همان موشک برمی‌گردد.
            levels=m.get("levels") or {}; max_level=int(m.get("max_level",100) or 100)
            current_data=levels.get(str(lvl),{}) or {}
            current_level=lvl
            next_level=lvl+1 if lvl<max_level else None
            text=(f"🧬 <b>فناوری نظامی — {escape(str(m.get('name','موشک')))}</b>\n\n"
                  f"🔰 <b>سطح فعلی: {lvl}</b>\n"
                  f"🪖 قدرت: <b>{float(current_data.get('power',0) or m.get('base_power',0) or 0):,.0f}</b>\n"
                  f"⏱️ زمان برخورد با هدف: <b>{float(current_data.get('target_time',0) or m.get('base_target_time',0) or 0):,.0f} ثانیه</b>")
            if next_level:
                nd=levels.get(str(next_level),{}) or {}
                lock=[]
                if int(getattr(country,"command_center_level",0) or 0) < int(nd.get("hq_required",m.get("hq_required",1)) or 1):
                    lock.append(f"🏛️ سطح مرکز فرماندهی لازم: <b>{int(nd.get('hq_required',m.get('hq_required',1)) or 1)}</b>")
                if int(getattr(country,"arsenal_level",0) or 0) < int(nd.get("arsenal_required",m.get("arsenal_required",1)) or 1):
                    lock.append(f"🏭 سطح زرادخانه لازم: <b>{int(nd.get('arsenal_required',m.get('arsenal_required',1)) or 1)}</b>")
                _has_uranium = float(nd.get("upgrade_uranium",0) or 0) > 0
                _has_normal = any(float(nd.get(k,0) or 0) > 0 for k in ("upgrade_money","upgrade_metal","upgrade_fuel"))
                _method = "با اورانیوم" if _has_uranium and not _has_normal else "با پول، فلز و سوخت"
                text += (f"\n\n⬆️ <b>سطح بعدی: {next_level}</b>\n💳 روش ارتقا: <b>{_method}</b>")
                if lock: text += "\n\n🔒 <b>شرایط ارتقا فراهم نیست:</b>\n" + "\n".join(lock)
                await query.answer(); await query.edit_message_text(text,parse_mode="HTML",reply_markup=missile_upgrade_levels_keyboard(mid,current_level,None if lock else next_level)); return
            await query.answer(); await query.edit_message_text(text+"\n\n🏆 <b>موشک به حداکثر سطح رسیده است.</b>",parse_mode="HTML",reply_markup=missile_upgrade_levels_keyboard(mid,current_level,None)); return

        if data.startswith("hq_tech_refresh:"):
            mid=data.split(":",1)[1]
            country=get_context_country(session,user, query.message.chat_id if query.message else None)
            if country is None: await query.answer("❌ کشور پیش‌فرضی ندارید.",show_alert=True); return
            done,_=finalize_missile_tech_upgrade(session,country.id,mid); session.commit()
            cfg=get_missiles_config(session); m=next((x for x in cfg.get("items",[]) if str(x.get("id"))==str(mid)),None)
            if not m: await query.answer("❌ اطلاعات موشک پیدا نشد.",show_alert=True); return
            lvl=get_missile_tech_level(session,country.id,mid); rem,tgt=missile_tech_upgrade_remaining(session,country.id,mid)
            if rem>0:
                await query.answer("⏳ هنوز زمان ارتقا تمام نشده است.",show_alert=True)
                await query.edit_message_text(f"🧬 <b>فناوری نظامی — {escape(str(m.get('name','موشک')))}</b>\n\n⏳ در حال ارتقا به سطح <b>{tgt}</b>\n⏱️ زمان باقی‌مانده: <b>{rem/60:,.0f} دقیقه</b>",parse_mode="HTML",reply_markup=missile_upgrade_levels_keyboard(mid,lvl,None,True))
            else:
                await query.answer("✅ ارتقا تکمیل شد." if done else "🔄 صفحه به‌روزرسانی شد.",show_alert=True)
                cd=(m.get("levels") or {}).get(str(lvl),{}) or {}
                next_level=lvl+1 if lvl<int(m.get("max_level",100) or 100) else None
                text=(f"🧬 <b>فناوری نظامی — {escape(str(m.get('name','موشک')))}</b>\n\n🔰 <b>سطح فعلی: {lvl}</b>\n🪖 قدرت: <b>{float(cd.get('power',0) or m.get('base_power',0) or 0):,.0f}</b>\n⏱️ زمان برخورد: <b>{float(cd.get('target_time',0) or m.get('base_target_time',0) or 0):,.0f} ثانیه</b>")
                await query.edit_message_text(text,parse_mode="HTML",reply_markup=missile_upgrade_levels_keyboard(mid,lvl,next_level))
            return

        if data == "hq_finish_now":
            country=get_context_country(session,user, query.message.chat_id if query.message else None)
            if country is None:
                await query.answer("❌ کشور پیش‌فرضی انتخاب نشده است.",show_alert=True); return
            cfg=get_hq_config(session)
            cost=hq_instant_finish_uranium_cost(country,cfg)
            if cost<=0:
                await query.answer("❌ تکمیل فوری فعال نشده است یا زمان باقی‌مانده‌ای وجود ندارد.",show_alert=True); return
            if not resource_available(country,"uranium",cost):
                await query.answer(f"❌ اورانیوم کافی نیست.\n☢️ موردنیاز: {cost:,.2f}",show_alert=True); return
            ok,res=finish_hq_construction_now(country,cfg,session)
            if not ok:
                await query.answer("❌ تکمیل فوری انجام نشد.",show_alert=True); return
            session.commit()
            await query.answer(f"✅ مرکز فرماندهی فوراً تکمیل شد.\n☢️ مصرف: {float(res):,.0f}",show_alert=True)
            await query.edit_message_text(hq_info(country,cfg),parse_mode="HTML",reply_markup=hq_keyboard(can_upgrade_hq(country,cfg)[0],built=int(country.command_center_level)>0,build_uranium=float(hq_build_cost(cfg).get("uranium",0))>0,upgrade_uranium=float((hq_upgrade_cost(country.command_center_level,cfg) or {}).get("uranium",0))>0))
            return

        if data == "hq_cancel":
            country = get_context_country(session, user, query.message.chat_id if query.message else None)
            if country is None:
                await query.answer("❌ کشور پیش‌فرضی انتخاب نشده است.", show_alert=True); return
            remaining, target_level = construction_remaining(country, "command_center")
            if remaining <= 0 or not target_level:
                await query.answer("⚠️ مرکز فرماندهی در حال ساخت یا ارتقا نیست.", show_alert=True); return
            await query.answer()
            await query.edit_message_text(
                "⚠️ <b>لغو ساخت/ارتقای مرکز فرماندهی</b>\n\n"
                "آیا مطمئن هستید که می‌خواهید عملیات لغو شود؟\n\n"
                "💡 در صورت تأیید، <b>۵۰٪ منابع پرداخت‌شده</b> به شما برگردانده می‌شود.",
                parse_mode="HTML", reply_markup=hq_cancel_confirm_keyboard()
            )
            return

        if data == "hq_cancel_back":
            country = get_context_country(session, user, query.message.chat_id if query.message else None)
            if country is None:
                await query.answer("❌ کشور پیش‌فرضی انتخاب نشده است.", show_alert=True); return
            cfg = get_hq_config(session)
            status = construction_label(country, "command_center")
            await query.answer()
            await query.edit_message_text(
                hq_info(country, cfg), parse_mode="HTML",
                reply_markup=hq_keyboard(can_upgrade_hq(country, cfg)[0], built=int(country.command_center_level)>0, construction_text=status, in_progress=bool(status), finish_uranium_cost=hq_instant_finish_uranium_cost(country,cfg), build_uranium=float(hq_build_cost(cfg).get("uranium",0))>0, upgrade_uranium=float((hq_upgrade_cost(country.command_center_level,cfg) or {}).get("uranium",0))>0)
            )
            return

        if data == "hq_cancel_confirm":
            country = get_context_country(session, user, query.message.chat_id if query.message else None)
            if country is None:
                await query.answer("❌ کشور پیش‌فرضی انتخاب نشده است.", show_alert=True); return
            ok, refund = cancel_hq_construction(country, get_hq_config(session), session)
            if not ok:
                await query.answer("⚠️ مرکز فرماندهی در حال ساخت یا ارتقا نیست.", show_alert=True); return
            session.commit()
            await query.answer("❌ عملیات لغو شد و نصف منابع پرداختی برگشت داده شد.", show_alert=True)
            cfg = get_hq_config(session)
            await query.edit_message_text(hq_info(country, cfg), parse_mode="HTML", reply_markup=hq_keyboard(can_upgrade_hq(country, cfg)[0], built=int(country.command_center_level)>0, construction_text=None, build_uranium=float(hq_build_cost(cfg).get("uranium",0))>0, upgrade_uranium=float((hq_upgrade_cost(country.command_center_level,cfg) or {}).get("uranium",0))>0))
            return

        if data == "hq_refresh":
            country = get_context_country(session, user, query.message.chat_id if query.message else None)
            if country is None:
                await query.answer("❌ کشور پیش‌فرضی انتخاب نشده است.", show_alert=True); return
            _before_level=int(getattr(country,"command_center_level",0))
            cfg=get_hq_config(session)
            finalize_construction(country)
            session.commit()
            if int(getattr(country,"command_center_level",0)) > _before_level:
                await query.answer(f"🎉 ارتقای مرکز فرماندهی به سطح {int(country.command_center_level)} تکمیل شد.", show_alert=True)
                await query.edit_message_text(hq_info(country,cfg), chat_id=int(query.message.chat_id), parse_mode="HTML", reply_markup=hq_keyboard(can_upgrade_hq(country,cfg)[0],built=int(country.command_center_level)>0,construction_text=construction_label(country,"command_center"),in_progress=bool(construction_label(country,"command_center")),finish_uranium_cost=hq_instant_finish_uranium_cost(country,cfg),build_uranium=float(hq_build_cost(cfg).get("uranium",0))>0,upgrade_uranium=float((hq_upgrade_cost(country.command_center_level,cfg) or {}).get("uranium",0))>0))
                return
            cfg = get_hq_config(session)
            status = construction_label(country, "command_center")
            await query.answer("🔄 به‌روزرسانی شد.")
            await query.edit_message_text(
                hq_info(country, cfg), parse_mode="HTML",
                reply_markup=hq_keyboard(can_upgrade_hq(country, cfg)[0], built=int(country.command_center_level)>0, construction_text=status, in_progress=bool(status), finish_uranium_cost=hq_instant_finish_uranium_cost(country,cfg), build_uranium=float(hq_build_cost(cfg).get("uranium",0))>0, upgrade_uranium=float((hq_upgrade_cost(country.command_center_level,cfg) or {}).get("uranium",0))>0),
            )
            return

        if data.startswith("hq_build_preview:"):
            country=get_context_country(session,user,query.message.chat_id if query.message else None); cfg=get_hq_config(session); payment=data.split(":",1)[1]
            if country is None: await query.answer("❌ کشور پیش‌فرضی انتخاب نشده است.",show_alert=True); return
            cost=hq_build_cost(cfg); labels={"money":"💰 پول","metal":"🔩 فلز","fuel":"⛽ سوخت","uranium":"☢️ اورانیوم"}
            costs="\n".join(f"{labels[k]}: <b>{float(v):,.0f}</b>" for k,v in cost.items() if (payment=="uranium" and k=="uranium") or (payment=="normal" and k!="uranium"))
            text=(f"🏗️ <b>تأیید ساخت مرکز فرماندهی — سطح ۱</b>\n\n🪖 قدرت نظامی: <b>{float(cfg.get('build_military_power',0) or 0):,.0f}</b>\n🛡️ استحکام: <b>{float(cfg.get('build_strength',0) or 0):,.0f}</b>\n⏱️ زمان تکمیل: <b>{float(cfg.get('build_completion_time',0) or 0):,.0f} ساعت</b>\n\n💰 <b>هزینه ساخت:</b>\n{costs}\n\nآیا ساخت را تأیید می‌کنید؟")
            rows=[[InlineKeyboardButton("✅ تأیید ساخت",callback_data=f"hq_build:{payment}")],[InlineKeyboardButton("✏️ ویرایش",callback_data=f"hq_build_preview:{payment}")],[InlineKeyboardButton("🔙 برگشت",callback_data="hq_cancel")]]
            await query.answer(); await query.edit_message_text(text,parse_mode="HTML",reply_markup=InlineKeyboardMarkup(rows)); return

        if data.startswith("hq_upgrade_preview:"):
            country=get_context_country(session,user,query.message.chat_id if query.message else None); cfg=get_hq_config(session); payment=data.split(":",1)[1]
            if country is None: await query.answer("❌ کشور پیش‌فرضی انتخاب نشده است.",show_alert=True); return
            target=int(country.command_center_level)+1; nd=hq_level_data(target,cfg) or {}; labels={"money":"💰 پول","metal":"🔩 فلز","fuel":"⛽ سوخت","uranium":"☢️ اورانیوم"}; cost=hq_upgrade_cost(target-1,cfg) or {}
            costs="\n".join(f"{labels[k]}: <b>{float(v):,.0f}</b>" for k,v in cost.items() if (payment=="uranium" and k=="uranium") or (payment=="normal" and k!="uranium"))
            text=(f"⬆️ <b>تأیید ارتقای مرکز فرماندهی به سطح {target}</b>\n\n🪖 قدرت نظامی: <b>{float(nd.get('military_power',0) or 0):,.0f}</b>\n🛡️ استحکام: <b>{float(nd.get('strength',0) or 0):,.0f}</b>\n⏱️ زمان تکمیل: <b>{float(nd.get('completion_time',0) or 0):,.0f} ساعت</b>\n\n💰 <b>هزینه ارتقا:</b>\n{costs}\n\nآیا ارتقا را تأیید می‌کنید؟")
            rows=[[InlineKeyboardButton(f"✅ تأیید ارتقا به سطح {target}",callback_data=f"hq_upgrade:{payment}")],[InlineKeyboardButton("✏️ ویرایش",callback_data=f"hq_upgrade_preview:{payment}")],[InlineKeyboardButton("🔙 برگشت",callback_data="hq_cancel")]]
            await query.answer(); await query.edit_message_text(text,parse_mode="HTML",reply_markup=InlineKeyboardMarkup(rows)); return

        if data in {"hq_build", "hq_build:normal", "hq_build:uranium"}:
            country = get_context_country(session, user, query.message.chat_id if query.message else None)
            if country is None:
                await query.answer("❌ کشور پیش‌فرضی انتخاب نشده است.", show_alert=True); return
            cfg = get_hq_config(session)
            finalize_construction(country)
            payment = data.split(":",1)[1] if ":" in data else "normal"
            success, result = build_hq(country, cfg, payment=payment, session=session)
            if success:
                session.commit()
                status = construction_label(country, "command_center")
                if status:
                    await query.answer("🏗️ ساخت مرکز فرماندهی شروع شد.", show_alert=True)
                else:
                    await query.answer("🎉 مرکز فرماندهی ساخته شد.", show_alert=True)
                await query.edit_message_text(
                    hq_info(country, cfg), parse_mode="HTML",
                    reply_markup=hq_keyboard(can_upgrade_hq(country, cfg)[0], built=int(country.command_center_level)>0, construction_text=status, in_progress=bool(status), finish_uranium_cost=hq_instant_finish_uranium_cost(country,cfg), build_uranium=float(hq_build_cost(cfg).get("uranium",0))>0, upgrade_uranium=float((hq_upgrade_cost(country.command_center_level,cfg) or {}).get("uranium",0))>0),
                )
                return
            session.rollback()
            if result == "NO_TEAM":
                await query.answer("⛔ تمام تیم‌های ساخت‌وساز شما مشغول هستند. برای انجام Upgrade هم‌زمان بیشتر، یک تیم ساخت‌وساز دیگر تهیه کنید.", show_alert=True); return
            if result == "IN_PROGRESS":
                await query.answer("⏳ ساخت مرکز فرماندهی هنوز در حال تکمیل است.", show_alert=True); return
            if result == "ALREADY_BUILT":
                await query.answer("⚠️ مرکز فرماندهی قبلاً ساخته شده است.", show_alert=True); return
            if result == "HQ_REQUIRED":
                await query.answer("🏛️ ابتدا شرایط لازم را فراهم کنید.", show_alert=True); return
            labels={"money":"💰 پول","metal":"🔩 فلز","fuel":"⛽ سوخت","uranium":"☢️ اورانیوم"}
            detail="\n".join(f"{labels.get(k,k)} موردنیاز: {float(v):,.0f}" for k,v in result.items()) if isinstance(result,dict) else str(result)
            await query.answer("❌ منابع کافی نیست.\n\n"+detail, show_alert=True)
            return

        if data in {"hq_upgrade", "hq_upgrade:normal", "hq_upgrade:uranium"}:
            country = get_context_country(session, user, query.message.chat_id if query.message else None)

            if country is None:
                session.commit()
                await query.edit_message_text(
                    "❌ کشور پیش‌فرضی انتخاب نشده است.",
                    reply_markup=private_main_keyboard(),
                )
                return

            cfg = get_hq_config(session)
            payment = data.split(":",1)[1] if ":" in data else "normal"
            success, result = upgrade_hq(country, cfg, payment=payment, session=session)

            if success:
                session.commit()
                status = construction_label(country, "command_center")
                await query.answer("🏗️ ارتقای مرکز فرماندهی شروع شد.", show_alert=True) if status else await query.answer("🎉 مرکز فرماندهی ارتقا یافت.", show_alert=True)
                progress_text = hq_info(country, cfg)
                result_text = (
                    progress_text if status else
                    f"🎉 <b>مرکز فرماندهی ارتقا یافت!</b>\n\n"
                    f"🌍 کشور: <b>{country.title}</b>\n"
                    f"🏛️ سطح جدید: <b>{country.command_center_level}</b>\n\n"
                    f"{progress_text}"
                )
                await query.edit_message_text(
                    result_text,
                    parse_mode="HTML",
                    reply_markup=hq_keyboard(
                        can_upgrade_hq(country, cfg)[0], built=int(country.command_center_level)>0, construction_text=status, in_progress=bool(status), finish_uranium_cost=hq_instant_finish_uranium_cost(country,cfg),
                        build_uranium=float(hq_build_cost(cfg).get("uranium",0))>0,
                        upgrade_uranium=float((hq_upgrade_cost(country.command_center_level,cfg) or {}).get("uranium",0))>0
                    ),
                )
            else:
                session.rollback()

                if result == "MAX_LEVEL":
                    text = "🏆 مرکز فرماندهی به حداکثر سطح فعلی رسیده است."
                elif result == "IN_PROGRESS":
                    text = "⏳ ارتقای مرکز فرماندهی هنوز در حال تکمیل است."
                elif result == "HQ_REQUIRED":
                    text = "🏛️ سطح مرکز فرماندهی کافی نیست."
                else:
                    names = {
                        "money": "💰 پول",
                        "metal": "🔩 فلز",
                        "fuel": "⛽ سوخت",
                    }
                    missing_lines = ([f"{names.get(key,key)}: {float(value):,.0f}" for key, value in result.items()] if isinstance(result, dict) else [str(result)])
                    text = (
                        "❌ منابع کافی برای ارتقا ندارید.\n\n"
                        "کمبود فعلی:\n"
                        + "\n".join(missing_lines)
                    )

                country = get_context_country(session, user, query.message.chat_id if query.message else None)
                session.commit()

                await query.answer(text.replace("<b>", "").replace("</b>", ""), show_alert=True)
            return

        if data == "main_menu":
            country = get_context_country(session, user, query.message.chat_id if query.message else None)
            session.commit()

            if country is None:
                await query.edit_message_text(
                    "❌ هنوز کشور پیش‌فرضی انتخاب نشده است.",
                    reply_markup=private_main_keyboard(),
                )
            else:
                await query.edit_message_text(
                    f"🌍 <b>{country.title}</b>\n\n"
                    "کشور پیش‌فرض شما انتخاب شده است.",
                    parse_mode="HTML",
                    reply_markup=private_main_keyboard(),
                )
            return
        
        await _notify_owner_logic_bug(query.get_bot(), query, "Callback برای این دکمه در Handler پیدا نشد.")
        await query.answer("⚠️ این گزینه در حال حاضر قابل اجرا نیست.", show_alert=True)
        return


# هر Callback ثبت‌نشده باید پاسخ قابل مشاهده و گزارش Owner داشته باشد.

def _shield_find_user_any(session, raw):
    raw=str(raw or '').strip().lstrip('\ufeff')
    raw=raw.translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹','0123456789'))
    if not raw: return None
    users=get_users(session)
    if raw.isdigit():
        return get_user_by_telegram_id(session,int(raw))
    if raw.startswith('@'):
        q=raw[1:].casefold()
        return next((u for u in users if (u.username or '').lstrip('@').casefold()==q),None)
    digits=''.join(ch for ch in raw if ch.isdigit())
    if digits and len(digits)>=7:
        return next((u for u in users if ''.join(ch for ch in str(u.phone_number or '') if ch.isdigit())==digits),None)
    q=raw.casefold()
    for u in users:
        if any(str(c.title or '').casefold()==q for c in get_user_countries(session,u)):
            return u
    return None


def _country_shield_status(session, country):
    """Live, scope-correct shield state for an exact user country."""
    try:
        import time
        session.expire_all()
        cfg = get_shield_config(session)
        state = __import__('services.economy', fromlist=['_state'])._state(session)
        out = {'continental': 'غیرفعال', 'global': 'غیرفعال'}
        uid = int(getattr(country, 'leader_user_id', 0) or 0)
        cid = int(getattr(country, 'id', 0) or 0)
        now = time.time()
        for rec in state.values():
            if int(rec.get('user_id', 0) or 0) != uid or float(rec.get('expires_at', 0) or 0) <= now:
                continue
            typ = str(rec.get('type') or '').strip().lower()
            if typ not in {'continental', 'global'}:
                item = next((x for x in cfg.get('items', []) if str(x.get('id')) == str(rec.get('item_id'))), None)
                typ = str(item.get('type') or '').strip().lower() if item else ''
            if typ == 'continental':
                if int(rec.get('country_id', 0) or 0) != cid:
                    continue
            elif typ == 'global':
                if rec.get('country_id') is not None:
                    continue
            else:
                continue
            out[typ] = shield_remaining_text(rec.get('expires_at'))
        return out
    except Exception:
        return {'continental': 'غیرفعال', 'global': 'غیرفعال'}
