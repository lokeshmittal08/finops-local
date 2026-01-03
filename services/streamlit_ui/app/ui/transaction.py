import streamlit as st
import pandas as pd

def transactions_table(transactions):
    if not transactions:
        st.info("No transactions")
        return

    df = pd.DataFrame(transactions)

    preferred_cols = [
        "date",
        "description",
        "debit",
        "credit",
        "balance_after",
        "currency",
        "direction",
        "reference_id",
        "confidence",
    ]

    show_cols = [c for c in preferred_cols if c in df.columns]

    st.dataframe(df[show_cols])