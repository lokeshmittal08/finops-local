import os
import pandas as pd
from sqlalchemy import create_engine, text

POSTGRES_DSN = os.getenv("POSTGRES_DSN")
engine = create_engine(POSTGRES_DSN)

# -------------------------
# Statements
# -------------------------

def get_latest_statement():
    query = """
        SELECT *
        FROM statements
        ORDER BY uploaded_at DESC
        LIMIT 1
    """
    df = pd.read_sql(query, engine)
    return df.iloc[0].to_dict() if not df.empty else None


# -------------------------
# Transactions
# -------------------------

def get_transactions_by_statement(statement_id: int):
    query = """
        SELECT *
        FROM transactions
        WHERE statement_id = :sid
        ORDER BY date
    """
    return pd.read_sql(
        text(query),
        engine,
        params={"sid": statement_id},
    ).to_dict(orient="records")


# -------------------------
# Monthly helpers
# -------------------------

def get_available_months():
    query = """
        SELECT DISTINCT
            EXTRACT(YEAR FROM date) AS year,
            EXTRACT(MONTH FROM date) AS month
        FROM transactions
        ORDER BY year DESC, month DESC
    """
    return pd.read_sql(query, engine).to_dict(orient="records")


def get_monthly_summary(year: int, month: int):
    query = """
        SELECT
            date,
            description,
            debit,
            credit,
            balance_after
        FROM transactions
        WHERE
            EXTRACT(YEAR FROM date) = :year
            AND EXTRACT(MONTH FROM date) = :month
        ORDER BY date
    """
    return pd.read_sql(
        text(query),
        engine,
        params={"year": year, "month": month},
    )