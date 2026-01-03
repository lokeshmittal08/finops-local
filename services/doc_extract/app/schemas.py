from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class TxnCandidate(BaseModel):
    txn_date: str  # ISO yyyy-mm-dd
    description: str
    amount: float
    currency: Literal["AED","INR"]
    direction: Literal["DEBIT","CREDIT"]
    reference_id: Optional[str] = None
    merchant: Optional[str] = None
    confidence: float = 0.5
    raw: dict = Field(default_factory=dict)

class ExtractResponse(BaseModel):
    bank_hint: Optional[str] = None
    account_hint: Optional[str] = None
    transactions: List[TxnCandidate]
    text_preview: Optional[str] = None