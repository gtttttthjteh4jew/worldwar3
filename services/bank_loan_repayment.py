"""Central Bank manual loan repayment rules. Automatic repayment is disabled."""
from __future__ import annotations
from datetime import datetime, timedelta
from services.settings import get_bank_loan_overdue_multiplier

def _interval(loan):
    return timedelta(days=max(0.1/24.0, float(loan.installment_interval_days or 1.0)))

def scheduled_due_at(loan, installment_no):
    return loan.created_at + _interval(loan) * int(installment_no)

def due_installment_count(loan, now=None):
    now = now or datetime.utcnow()
    if loan.status != "active" or not loan.created_at:
        return 0
    interval=_interval(loan)
    elapsed=(now-loan.created_at).total_seconds()
    if elapsed < interval.total_seconds():
        return 0
    return min(int(loan.installments or 0), max(0, int(elapsed // interval.total_seconds())))

def current_installment_amount(loan, session=None, now=None):
    """Amount of the oldest unpaid installment. Late oldest installments are multiplied."""
    now=now or datetime.utcnow()
    paid=int(loan.installments_paid or 0)
    total=int(loan.installments or 0)
    if paid >= total:
        return 0.0
    base=max(0.0,float(loan.installment_amount or 0.0))
    if base<=0:
        return 0.0
    due_count=due_installment_count(loan,now)
    installment_no=paid+1
    if due_count >= installment_no and due_count > installment_no:
        mult=get_bank_loan_overdue_multiplier(session) if session is not None else 2.0
        return base*mult
    return base

def due_amount(loan, cycles=1, session=None, now=None):
    return current_installment_amount(loan,session,now)

def process_due_loan(session, loan, country, now=None):
    """Manually pay exactly the oldest unpaid installment; it may be paid before its due date."""
    now=now or datetime.utcnow()
    if loan.status != "active":
        return {"status":"not_due","cycles":0,"amount":0.0}
    total_installments=int(loan.installments or 0)
    paid_installments=int(loan.installments_paid or 0)
    if paid_installments >= total_installments:
        loan.status="paid"; loan.next_payment_at=None
        return {"status":"not_due","cycles":0,"amount":0.0}
    amount=current_installment_amount(loan,session,now)
    infinite=bool(getattr(country,"infinite_money",False))
    if not infinite and float(country.money or 0)+1e-9 < amount:
        return {"status":"insufficient","cycles":1,"amount":amount}
    if not infinite:
        country.money=float(country.money or 0)-amount
    loan.paid=float(loan.paid or 0)+amount
    loan.installments_paid=paid_installments+1
    if loan.installments_paid>=total_installments:
        loan.status="paid"; loan.next_payment_at=None; loan.last_reminder_for=None
    else:
        loan.next_payment_at=scheduled_due_at(loan, loan.installments_paid+1)
    remaining=max(0,total_installments-int(loan.installments_paid or 0))
    # Keep the displayed contractual total based on the base installment; overdue multipliers are penalties paid when installments are late.
    loan.total_due=float(loan.principal or 0)+float(loan.interest or 0)
    return {"status":"paid","cycles":1,"amount":amount}
