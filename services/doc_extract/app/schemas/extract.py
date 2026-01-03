from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

from db.database import SessionLocal
from db.crud import create_statement, create_transactions



class Balance(BaseModel):
    amount: Optional[float] = None
    currency: str = Field(..., pattern="^(AED|INR)$")


class StatementPeriod(BaseModel):
    from_: Optional[str] = Field(default=None, alias="from")
    to: Optional[str] = None


class StatementMetadata(BaseModel):
    bank_name: Optional[str] = None
    account_holder_name: Optional[str] = None
    account_number: Optional[str] = None
    statement_period: StatementPeriod
    opening_balance: Balance
    closing_balance: Balance


class Transaction(BaseModel):
    date: str
    description: str
    debit: Optional[float] = None
    credit: Optional[float] = None
    balance_after: Optional[float] = None
    currency: str = Field(..., pattern="^(AED|INR)$")
    direction: str = Field(..., pattern="^(DEBIT|CREDIT)$")
    confidence: float = Field(..., ge=0.0, le=1.0)
    reference_id: Optional[str] = None
    raw: Dict[str, Any] = {}


class ExtractResponse(BaseModel):
    statement_metadata: StatementMetadata
    transactions: List[Transaction]

