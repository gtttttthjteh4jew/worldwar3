"""Central Bank installment schedule and overdue debt calculations."""
from __future__ import annotations

from datetime import datetime, timedelta
from services.settings import get_bank_loan_overdue_multiplier


def scheduled_due_at(loan, installment_no):
    """Return the UTC-naive due timestamp for an installment.

    New loans store ``first_due_at`` (tomorrow at the configured Tehran time)
    and then follow a daily calendar schedule. Legacy loans retain their former
    created_at + interval schedule.
    """
    n = max(1, int(installment_no))
    first = getattr(loan, "first_due_at", None)
    if first is not None:
        return first + timedelta(days=n - 1)
    interval = timedelta(days=max(0.1 / 24.0, float(loan.installment_interval_days or 1.0)))
    return loan.created_at + interval * n


def due_installment_count(loan, now=None):
    now = now or datetime.utcnow()
    if loan.status != "active" or not loan.created_at:
        return 0
    first = getattr(loan, "first_due_at", None)
    if first is not None:
        if now < first:
            return 0
        elapsed_days = (now - first).total_seconds() / 86400.0
        count = int(elapsed_days) + 1
        return min(int(loan.installments or 0), max(0, count))
    interval = timedelta(days=max(0.1 / 24.0, float(loan.installment_interval_days or 1.0)))
    elapsed = (now - loan.created_at).total_seconds()
    if elapsed < interval.total_seconds():
        return 0
    return min(int(loan.installments or 0), max(0, int(elapsed // interval.total_seconds())))


def current_installment_amount(loan, session=None, now=None):
    """Calculate the full matured balance, including compounded overdue debt.

    For base installment B and overdue multiplier M the amounts are B,
    B*M+B, (B*M+B)*M+B, and so on. Paying at a due date clears every matured
    installment at once; already-paid installments are not compounded again.
    """
    now = now or datetime.utcnow()
    paid = int(loan.installments_paid or 0)
    due_count = due_installment_count(loan, now)
    if due_count <= paid:
        return 0.0
    base = max(0.0, float(loan.installment_amount or 0.0))
    if base <= 0:
        return 0.0
    multiplier = get_bank_loan_overdue_multiplier(session) if session is not None else 2.0
    balance = 0.0
    for _n in range(paid + 1, due_count + 1):
        if balance > 0:
            balance *= multiplier
        balance += base
    return balance


def due_amount(loan, cycles=1, session=None, now=None):
    return current_installment_amount(loan, session, now)


def process_due_loan(session, loan, country, now=None):
    """Manually pay all installments matured as of ``now`` in one transaction."""
    now = now or datetime.utcnow()
    if loan.status != "active":
        return {"status": "not_due", "cycles": 0, "amount": 0.0}
    total_installments = int(loan.installments or 0)
    paid_installments = int(loan.installments_paid or 0)
    due_count = due_installment_count(loan, now)
    if due_count <= paid_installments:
        return {"status": "not_due", "cycles": 0, "amount": 0.0}
    amount = current_installment_amount(loan, session, now)
    infinite = bool(getattr(country, "infinite_money", False))
    if not infinite and float(country.money or 0) + 1e-9 < amount:
        return {"status": "insufficient", "cycles": due_count - paid_installments, "amount": amount}
    if not infinite:
        country.money = float(country.money or 0) - amount
    loan.paid = float(loan.paid or 0) + amount
    loan.installments_paid = due_count
    if loan.installments_paid >= total_installments:
        loan.status = "paid"
        loan.next_payment_at = None
        loan.last_reminder_for = None
    else:
        loan.next_payment_at = scheduled_due_at(loan, due_count + 1)
        loan.last_reminder_for = None
    # Contractual display remains the original principal + interest. Late
    # compounding is a collection penalty and is accounted at each settlement.
    loan.total_due = float(loan.principal or 0) + float(loan.interest or 0)
    return {"status": "paid", "cycles": due_count - paid_installments, "amount": amount}
