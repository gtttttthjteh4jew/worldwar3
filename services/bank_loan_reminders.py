"""Central Bank loan due-date reminder worker. No automatic repayment."""
from __future__ import annotations
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select
from database.db import SessionLocal
from database.models import BankLoan, Country
from services.economy import ensure_bank_account, bank_level_config
from services.bank_loan_repayment import due_installment_count, current_installment_amount, scheduled_due_at
from services.settings import get_bank_loan_lock_hours, get_bank_loan_overdue_multiplier

async def bank_loan_reminder_worker(app):
    """Send reminders only. Never deduct money automatically."""
    while True:
        try:
            with SessionLocal() as session:
                now=datetime.utcnow()
                loans=session.scalars(select(BankLoan).where(BankLoan.status=="active")).all()
                for loan in loans:
                    if not loan.created_at: continue
                    country=session.get(Country,int(loan.country_id))
                    if country is None: continue
                    acc=ensure_bank_account(session,country)
                    due_count=due_installment_count(loan,now)
                    paid=int(loan.installments_paid or 0)
                    total=int(loan.installments or 0)
                    if due_count <= paid: continue
                    # Current due slot is the latest scheduled installment reached. Send one reminder per slot.
                    current_due_at=scheduled_due_at(loan,due_count)
                    if loan.last_reminder_for != current_due_at:
                        leader_id=int(getattr(country,"leader_user_id",0) or 0)
                        if leader_id:
                            # Oldest unpaid installment is multiplied once it has become overdue; other reached installments stay at base.
                            base=float(loan.installment_amount or 0)
                            multiplier=get_bank_loan_overdue_multiplier(session)
                            amounts=[]
                            for n in range(paid+1,due_count+1):
                                amounts.append(base*(multiplier if n < due_count else 1.0))
                            total_due=sum(amounts)
                            try:
                                await app.bot.send_message(chat_id=leader_id,text=(
                                    f"💳 <b>یادآوری سررسید قسط وام</b>\n\n"
                                    f"وام #{loan.id}\n"
                                    f"🧾 اقساط قابل پرداخت: <b>{len(amounts)}</b>\n"
                                    f"💵 مبلغ قابل پرداخت اکنون: <b>{total_due:,.0f}</b> پول\n"
                                    "لطفاً از بخش «وام‌های من» اقساط را به‌صورت دستی پرداخت کنید."),parse_mode="HTML")
                            except Exception:
                                pass
                        loan.last_reminder_for=current_due_at
                    # One full interval after the final installment's due time, lock the bank if the final installment is still unpaid.
                    final_due=scheduled_due_at(loan,total) if total else None
                    if total and paid < total and final_due and now >= final_due + timedelta(days=max(0.1/24.0,float(loan.installment_interval_days or 1.0))):
                        lock_hours=get_bank_loan_lock_hours(session)
                        if lock_hours>0 and (not acc.bank_locked_until or acc.bank_locked_until<=now):
                            acc.bank_locked_until=now+timedelta(hours=lock_hours)
                            leader_id=int(getattr(country,"leader_user_id",0) or 0)
                            if leader_id:
                                try:
                                    await app.bot.send_message(chat_id=leader_id,text=(
                                        f"🔒 <b>هشدار نهایی بانک مرکزی</b>\n\n"
                                        f"قسط آخر وام #{loan.id} هنوز پرداخت نشده است.\n"
                                        f"بانک مرکزی به مدت <b>{lock_hours:g} ساعت</b> بسته شد."),parse_mode="HTML")
                                except Exception:
                                    pass
                session.commit()
        except asyncio.CancelledError:
            raise
        except Exception:
            pass
        await asyncio.sleep(30)
