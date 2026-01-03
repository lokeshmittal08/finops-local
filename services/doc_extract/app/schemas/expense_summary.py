from pydantic import BaseModel, Field
from typing import Optional, List, Dict


class ExpenseSummaryRequest(BaseModel):
    year: int = Field(..., ge=2000, le=2100)
    month: int = Field(..., ge=1, le=12)
    account_number: Optional[str] = None  # optional, but recommended


class ExpenseSummaryResponse(BaseModel):
    year: int
    month: int
    currency: Optional[str] = None

    total_debit: float = 0.0
    total_credit: float = 0.0
    net: float = 0.0  # credit - debit
    txn_count: int = 0

    daily: List[Dict] = []  # [{"date":"YYYY-MM-DD","debit":..,"credit":..,"net":..,"count":..}]