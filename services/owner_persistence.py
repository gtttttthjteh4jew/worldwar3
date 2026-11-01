"""Durable Owner runtime state for values that are safe to persist.

Business configuration is already stored in dedicated database tables/BotSetting rows.
This module adds a final safety net for Owner-only runtime values that are JSON-safe and
not explicitly transient UI/waiting state. It prevents a future Owner-facing value from
being left only inside python-telegram-bot's in-memory user_data.
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select

from database.models import BotSetting

PREFIX = "owner_runtime_state:"

# Current Owner user_data keys are all workflow/UI state, not durable business settings.
# They are explicitly excluded so an interrupted form, message id, pager or pending
# operation is never resumed after restart. Any *new* JSON-safe Owner key is persisted
# by default, which prevents future durable values from silently remaining in RAM.
TRANSIENT_KEYS = {
    "account_settings_message", "admin_leadership_bulk_pending", "admin_leadership_confirm",
    "admin_leadership_pending", "admin_list_page", "admin_message_pending", "admin_panel",
    "admin_pending", "admin_swap", "admin_swap_confirm", "arsenal_sell_custom_pending",
    "arsenal_sell_pending", "balance_back_callback", "balance_pending", "balance_selected_country",
    "balance_selected_user", "bank_investment_quote", "bank_loan_quote", "bank_nav", "bank_pending",
    "construction_buy_pending", "country_edit", "country_edit_list_back", "country_edit_name",
    "country_edit_waiting", "economy_pending", "enigma_pending", "exchange_rate_pending",
    "exchange_text_draft", "exchange_text_pending", "global_loot_percent_pending", "golden_pending",
    "leadership_back_callback", "leadership_operation", "missile_draft", "missile_operational_pending",
    "missile_pending", "owner_economy_confirm", "pending_exchange", "population_pending",
    "population_selected_user", "search_scope", "security_pending", "self_country_edit",
    "self_country_edit_name", "shield_add_pending", "shield_adjust_pending", "shield_auto_setting_pending",
    "shield_edit_pending", "shield_purchase_pending", "shield_reset_pending", "social_delete_pending",
    "social_pending", "store_nav", "swap_pending", "user_admin_back", "user_admin_origin",
    "user_country_delete_back", "user_detail_back", "user_game_country_back",
    "user_game_population_confirm", "user_game_population_pending", "user_game_settings_back",
    "user_game_specs_back", "wallet_card_draft", "wallet_crypto_dest_draft", "wallet_nav_stack",
    "wallet_owner_edit_preview", "wallet_owner_manual_preview", "wallet_owner_panel",
    "wallet_owner_rejection_preview", "wallet_owner_state", "wallet_panel_message",
}

TRANSIENT_PREFIXES = (
    "__waiting_scope__", "enigma_page_", "country_name_pending_", "country_creation_start_",
    "country_creation_prompt_", "country_name_value_", "country_creation_name_message_",
)


def _is_persistable_key(key: str) -> bool:
    k = str(key or "")
    if not k or k in TRANSIENT_KEYS:
        return False
    return not any(k.startswith(prefix) for prefix in TRANSIENT_PREFIXES)


def _json_safe(value: Any) -> bool:
    try:
        json.dumps(value, ensure_ascii=False, allow_nan=False)
        return True
    except (TypeError, ValueError):
        return False


def load_owner_state(session, owner_id: int) -> dict[str, Any]:
    key = f"{PREFIX}{int(owner_id)}"
    row = session.scalar(select(BotSetting).where(BotSetting.key == key))
    if row is None or not row.value:
        return {}
    try:
        data = json.loads(row.value)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def save_owner_state(session, owner_id: int, user_data) -> None:
    """Checkpoint all persistable Owner user_data values into SQLite."""
    payload = {}
    for key, value in list(user_data.items()):
        if not _is_persistable_key(str(key)):
            continue
        if not _json_safe(value):
            continue
        payload[str(key)] = value

    row_key = f"{PREFIX}{int(owner_id)}"
    row = session.scalar(select(BotSetting).where(BotSetting.key == row_key))
    raw = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    if row is None:
        session.add(BotSetting(key=row_key, value=raw))
    else:
        row.value = raw
    session.commit()


def load_into_user_data(session, owner_id: int, user_data) -> None:
    """Restore durable Owner values without overwriting the live in-process state."""
    persisted = load_owner_state(session, owner_id)
    for key, value in persisted.items():
        if _is_persistable_key(key) and key not in user_data:
            user_data[key] = value
