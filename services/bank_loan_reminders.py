"""Central Bank daily installment reminders and final overdue lock worker."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select

from database.db import SessionLocal
from database.models import BankLoan, Country
from services.economy import ensure_bank_account
from services.bank_loan_repayment import due_installment_count, current_installment_amount, scheduled_due_at
from services.settings import get_bank_loan_lock_hours


async def bank_loan_reminder_worker(app):
    """Remind users at the configured daily due time; never auto-deduct money."""
    while True:
        try:
            with SessionLocal() as session:
                now = datetime.utcnow()
                loans = session.scalars(select(BankLoan).where(BankLoan.status == "active")).all()
                for loan in loans:
                    if not loan.created_at:
                        continue
                    country = session.get(Country, int(loan.country_id))
                    if country is None:
                        continue
                    acc = ensure_bank_account(session, country)
                    due_count = due_installment_count(loan, now)
                    paid = int(loan.installments_paid or 0)
                    total = int(loan.installments or 0)

                    if due_count > paid:
                        current_due_at = scheduled_due_at(loan, due_count)
                        if loan.last_reminder_for != current_due_at:
                            leader_id = int(getattr(country, "leader_user_id", 0) or 0)
                            if leader_id:
                                amount = current_installment_amount(loan, session, now)
                                cycles = due_count - paid
                                try:
                                    await app.bot.send_message(
                                        chat_id=leader_id,
                                        text=(
                                            f"💳 <b>یادآوری سررسید اقساط وام</b>\n\n"
                                            f"وام #{loan.id}\n"
                                            f"🧾 اقساط سررسیدشده: <b>{cycles}</b>\n"
                                            f"💵 مجموع بدهی قابل پرداخت: <b>{amount:,.0f}</b> پول\n"
                                            "لطفاً از بخش «وام‌های من» بدهی سررسیدشده را پرداخت کنید."
                                        ),
                                        parse_mode="HTML",
                                    )
                                except Exception:
                                    pass
                            loan.last_reminder_for = current_due_at

                    # The final lock happens exactly one calendar day after the
                    # last installment due time, at the same configured hour.
                    final_due = scheduled_due_at(loan, total) if total else None
                    lock_at = final_due + timedelta(days=1) if final_due else None
                    if (
                        total
                        and paid < total
                        and lock_at is not None
                        and now >= lock_at
                        and getattr(loan, "final_lock_applied_at", None) is None
                    ):
                        lock_hours = get_bank_loan_lock_hours(session)
                        if lock_hours > 0:
                            acc.bank_locked_until = now + timedelta(hours=lock_hours)
                            loan.final_lock_applied_at = lock_at
                            leader_id = int(getattr(country, "leader_user_id", 0) or 0)
                            if leader_id:
                                try:
                                    await app.bot.send_message(
                                        chat_id=leader_id,
                                        text=(
                                            f"🔒 <b>هشدار نهایی بانک مرکزی</b>\n\n"
                                            f"قسط آخر وام #{loan.id} تا مهلت نهایی پرداخت نشده است.\n"
                                            f"بانک مرکزی به مدت <b>{lock_hours:g} ساعت</b> بسته شد."
                                        ),
                                        parse_mode="HTML",
                                    )
                                except Exception:
                                    pass
                session.commit()
        except asyncio.CancelledError:
            raise
        except Exception:
            # A single corrupt loan must not stop reminders for all other loans.
            pass
        await asyncio.sleep(30)
