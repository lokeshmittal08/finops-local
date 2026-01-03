from fastapi import APIRouter, UploadFile, File, Query
from schemas.extract import ExtractResponse
from services.extraction_service import handle_extract
from fastapi import Depends
from sqlalchemy.orm import Session
from db.database import SessionLocal
from schemas.expense_summary import ExpenseSummaryRequest, ExpenseSummaryResponse
from db.crud import get_monthly_expense_summary



router = APIRouter()

@router.get("/health")
def health():
    return {"status": "ok"}

@router.post("/extract", response_model=ExtractResponse)
def extract(
    file: UploadFile = File(...),
    currency_hint: str | None = Query(None),
    bank_hint: str | None = Query(None),
    account_holder_hint: str | None = Query(None),
):
    return handle_extract(
        file=file,
        currency_hint=currency_hint,
        bank_hint=bank_hint,
        account_holder_hint=account_holder_hint,
    )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/expenses/summary", response_model=ExpenseSummaryResponse)
def expenses_summary(payload: ExpenseSummaryRequest, db: Session = Depends(get_db)):
    data = get_monthly_expense_summary(
        db=db,
        year=payload.year,
        month=payload.month,
        account_number=payload.account_number,
    )

    # currency is stored in transactions per row; simplest: pick first row if exists
    currency = None
    # (optional) you can query first currency quickly
    # but for demo, leave null or hardcode AED if that's your default

    return ExpenseSummaryResponse(
        year=payload.year,
        month=payload.month,
        currency=currency,
        total_debit=data["total_debit"],
        total_credit=data["total_credit"],
        net=data["net"],
        txn_count=data["txn_count"],
        daily=data["daily"],
    )