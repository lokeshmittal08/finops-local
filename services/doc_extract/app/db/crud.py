# app/db/crud.py

import hashlib
from sqlalchemy.orm import Session
from .models import Statement, Transaction ,ManualAdjustment

from sqlalchemy import func
from datetime import date

def hash_statement(account_number: str, period_from: str, period_to: str) -> str:
    raw = f"{account_number}|{period_from}|{period_to}"
    return hashlib.sha256(raw.encode()).hexdigest()


def hash_transaction(tx: dict) -> str:
    raw = (
        f"{tx['date']}|"
        f"{tx.get('debit')}|"
        f"{tx.get('credit')}|"
        f"{tx.get('balance_after')}|"
        f"{tx.get('reference_id')}"
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def create_statement(db: Session, meta: dict) -> Statement:
    stmt_hash = hash_statement(
        meta["account_number"],
        meta["statement_period"]["from"],
        meta["statement_period"]["to"],
    )

    stmt = db.query(Statement).filter_by(statement_hash=stmt_hash).first()
    if stmt:
        return stmt

    stmt = Statement(
        bank_name=meta.get("bank_name"),
        account_number=meta["account_number"],
        statement_hash=stmt_hash,
        period_from=meta["statement_period"]["from"],
        period_to=meta["statement_period"]["to"],
    )

    db.add(stmt)
    db.commit()
    db.refresh(stmt)
    return stmt


def create_transactions(db: Session, statement_id: int, txns: list):
    for t in txns:
        txn_hash = hash_transaction(t)

        exists = (
            db.query(Transaction)
            .filter_by(txn_hash=txn_hash)
            .first()
        )
        if exists:
            continue

        row = Transaction(
            statement_id=statement_id,
            txn_hash=txn_hash,
            date=t["date"],
            description=t["description"],
            debit=t.get("debit"),
            credit=t.get("credit"),
            balance_after=t.get("balance_after"),
            currency=t["currency"],
            direction=t["direction"],
            confidence=int(t.get("confidence", 0) * 100),
            reference_id=t.get("reference_id"),
            raw=t.get("raw"),
            is_duplicate=t.get("is_duplicate", False),
            duplicate_of=None,  
        )
        db.add(row)

    db.commit()


def create_manual_adjustment(
    db: Session,
    statement_id: int,
    date,
    description: str,
    amount: int,
    direction: str,
    reason: str = None,
):
    adj = ManualAdjustment(
        statement_id=statement_id,
        date=date,
        description=description,
        amount=amount,
        direction=direction,
        reason=reason,
    )
    db.add(adj)
    db.commit()
    return adj


def get_manual_adjustments(db: Session, statement_id: int):
    return (
        db.query(ManualAdjustment)
        .filter(ManualAdjustment.statement_id == statement_id)
        .all()
    )



def get_monthly_expense_summary(db: Session, year: int, month: int, account_number: str | None = None):
    """
    Returns monthly totals and daily breakdown from transactions table.
    - Filters by year/month on Transaction.date
    - Optionally filters by Statement.account_number (join)
    """
    from .models import Transaction, Statement  # local import to avoid circulars

    q = (
        db.query(
            Transaction.date.label("date"),
            func.count(Transaction.id).label("cnt"),
            func.coalesce(func.sum(Transaction.debit), 0).label("sum_debit"),
            func.coalesce(func.sum(Transaction.credit), 0).label("sum_credit"),
        )
        .join(Statement, Statement.id == Transaction.statement_id)
        .filter(func.extract("year", Transaction.date) == year)
        .filter(func.extract("month", Transaction.date) == month)
    )

    if account_number:
        q = q.filter(Statement.account_number == account_number)

    daily_rows = q.group_by(Transaction.date).order_by(Transaction.date.asc()).all()

    total_debit = float(sum(r.sum_debit for r in daily_rows))
    total_credit = float(sum(r.sum_credit for r in daily_rows))
    txn_count = int(sum(r.cnt for r in daily_rows))

    daily = []
    for r in daily_rows:
        d = r.date.isoformat() if hasattr(r.date, "isoformat") else str(r.date)
        debit = float(r.sum_debit or 0)
        credit = float(r.sum_credit or 0)
        daily.append({
            "date": d,
            "debit": debit,
            "credit": credit,
            "net": credit - debit,
            "count": int(r.cnt or 0),
        })

    return {
        "total_debit": total_debit,
        "total_credit": total_credit,
        "net": total_credit - total_debit,
        "txn_count": txn_count,
        "daily": daily,
    }