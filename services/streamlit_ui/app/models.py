from sqlalchemy import Column, Integer, String, Date, JSON, Boolean
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    date = Column(Date)
    description = Column(String)
    debit = Column(Integer)
    credit = Column(Integer)
    balance_after = Column(Integer)
    reference_id = Column(String)
    is_duplicate = Column(Boolean)
    raw = Column(JSON)


class ManualAdjustment(Base):
    __tablename__ = "manual_adjustments"

    id = Column(Integer, primary_key=True)
    statement_id = Column(Integer)
    date = Column(Date)
    description = Column(String)
    amount = Column(Integer)
    direction = Column(String)
    reason = Column(String)