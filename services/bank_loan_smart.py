"""Smart Central Bank loan calculation engine."""
from __future__ import annotations
from dataclasses import dataclass
from math import floor

@dataclass(frozen=True)
class SmartLoanPolicy:
    min_amount: float = 0.0
    max_amount: float = 0.0
    min_interest_percent: float = 0.0
    max_interest_percent: float = 0.0
    min_installments: int = 1
    max_installments: int = 1
    max_active_loans: int = 1

@dataclass(frozen=True)
class SmartLoanQuote:
    principal: float
    risk_ratio: float
    interest_percent: float
    interest_amount: float
    total_due: float
    installments: int
    installment_amount: float
    term_days: float
    installment_interval_days: float

def _clamp(value, low, high):
    return max(low, min(high, value))

def _ratio(amount, minimum, maximum):
    if maximum <= minimum:
        return 0.0
    return _clamp((amount - minimum) / (maximum - minimum), 0.0, 1.0)

def _interpolate(low, high, ratio):
    return low + (high - low) * ratio

def validate_policy(policy):
    if policy.min_amount < 0 or policy.max_amount < policy.min_amount:
        raise ValueError("Loan amount range is invalid.")
    if policy.max_amount <= 0:
        raise ValueError("Maximum loan amount is not configured.")
    if policy.min_interest_percent < 0 or policy.max_interest_percent < policy.min_interest_percent:
        raise ValueError("Interest range is invalid.")
    if policy.min_installments < 1 or policy.max_installments < policy.min_installments:
        raise ValueError("Installment range is invalid.")
    if policy.max_active_loans < 1:
        raise ValueError("Maximum active loans is not configured.")

def quote_loan(amount, policy, interval_hours=24.0):
    validate_policy(policy)
    amount = float(amount)
    if amount < policy.min_amount or amount > policy.max_amount:
        raise ValueError(f"Requested amount must be between {policy.min_amount:g} and {policy.max_amount:g}.")
    ratio = _ratio(amount, policy.min_amount, policy.max_amount)
    interest_percent = _interpolate(policy.min_interest_percent, policy.max_interest_percent, ratio)
    interest_amount = amount * interest_percent / 100.0
    total_due = amount + interest_amount
    installments = int(floor(_interpolate(policy.min_installments, policy.max_installments, ratio) + 0.5))
    installments = max(policy.min_installments, min(policy.max_installments, installments))
    # Repayment spacing is a single global Owner setting. The first installment
    # is due exactly interval_hours after the loan is received; no per-loan
    # repayment-duration range is configured.
    interval_hours = max(0.1, float(interval_hours or 24.0))
    interval = interval_hours / 24.0
    term_days = float(installments) * interval
    return SmartLoanQuote(amount, ratio, interest_percent, interest_amount, total_due, installments, total_due/installments, term_days, interval)

def policy_from_level_config(level_config):
    loan = level_config.get("loan", {}) if isinstance(level_config, dict) else {}
    if not isinstance(loan, dict): loan = {}
    base = float(loan.get("interest_percent", 0) or 0)
    return SmartLoanPolicy(
        min_amount=float(loan.get("min_amount", loan.get("min", 0)) or 0),
        max_amount=float(loan.get("max_amount", loan.get("max", 0)) or 0),
        min_interest_percent=float(loan.get("min_interest_percent", base) or 0),
        max_interest_percent=float(loan.get("max_interest_percent", base) or 0),
        min_installments=max(1, int(loan.get("min_installments", loan.get("installments", 1)) or 1)),
        max_installments=max(1, int(loan.get("max_installments", loan.get("installments", 1)) or 1)),
        max_active_loans=max(1, int(loan.get("max_active_loans", loan.get("max_active", 1)) or 1)),
    )
