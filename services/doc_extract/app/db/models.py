from sqlalchemy import Column, Integer, String, Date, DateTime, JSON, ForeignKey, Float, Boolean
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
from db.database import Base


class Statement(Base):
    __tablename__ = "statements"

    id = Column(Integer, primary_key=True)
    bank_name = Column(String, nullable=True)   # ✅ ADD THIS


    account_number = Column(String, nullable=True)
    statement_hash = Column(String, unique=True, index=True, nullable=False)
    period_from = Column(Date, nullable=True)
    period_to = Column(Date, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    is_reconciled = Column(Boolean, default=False)
    reconciliation_diff = Column(Float, nullable=True)
    statement_confidence = Column(Float, nullable=True)
    transactions = relationship("Transaction", back_populates="statement")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    statement_id = Column(Integer, ForeignKey("statements.id"), index=True)
    txn_hash = Column(String, index=True, nullable=False)  # ✅ ADD THIS

    is_duplicate = Column(Boolean, default=False)
    duplicate_of = Column(Integer, ForeignKey("transactions.id"), nullable=True)

    date = Column(Date, nullable=False)
    description = Column(String, nullable=False)
    debit = Column(Integer, nullable=True)
    credit = Column(Integer, nullable=True)
    balance_after = Column(Integer, nullable=True)
    currency = Column(String, nullable=False)
    direction = Column(String, nullable=False)
    confidence = Column(Integer)
    reference_id = Column(String, nullable=True)
    raw = Column(JSON)

    statement = relationship("Statement", back_populates="transactions")


class ManualAdjustment(Base):
    __tablename__ = "manual_adjustments"

    id = Column(Integer, primary_key=True)
    statement_id = Column(Integer, ForeignKey("statements.id"), index=True)

    date = Column(Date, nullable=False)
    description = Column(String, nullable=False)
    amount = Column(Integer, nullable=False)
    direction = Column(String, nullable=False)  # DEBIT / CREDIT
    reason = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)