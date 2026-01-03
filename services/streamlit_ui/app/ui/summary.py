import streamlit as st
import pandas as pd

def summary_page():
    st.header("📊 Monthly Summary")

    if "transactions" not in st.session_state:
        st.warning("No extracted data yet")
        return

    txns = st.session_state.transactions.copy()

    # Add manual entries if any
    if "manual_txns" in st.session_state:
        txns += st.session_state.manual_txns

    if not txns:
        st.info("No transactions available")
        return

    df = pd.DataFrame(txns)
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.to_period("M").astype(str)

    months = sorted(df["month"].unique())

    col1, col2 = st.columns(2)
    with col1:
        from_month = st.selectbox("From Month", months, index=0)
    with col2:
        to_month = st.selectbox("To Month", months, index=len(months) - 1)

    df = df[(df["month"] >= from_month) & (df["month"] <= to_month)]

    df["debit"] = df["debit"].fillna(0)
    df["credit"] = df["credit"].fillna(0)

    total_debit = df["debit"].sum()
    total_credit = df["credit"].sum()
    net = total_credit - total_debit

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Debit", f"{total_debit:.2f}")
    c2.metric("Total Credit", f"{total_credit:.2f}")
    c3.metric("Net (Credit - Debit)", f"{net:.2f}")

    st.subheader("Monthly Breakdown")
    monthly = (
        df.groupby("month")[["debit", "credit"]]
        .sum()
        .reset_index()
    )
    st.dataframe(monthly)

    st.subheader("Transactions Used")
    st.dataframe(
        df[[
            "date",
            "description",
            "debit",
            "credit",
            "currency",
            "reference_id",
        ]]
    )