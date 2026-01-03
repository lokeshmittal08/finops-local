import streamlit as st

def reconciliation_view(meta, transactions, adjustments):
    st.header("🧮 Reconciliation")

    opening = meta["opening_balance"]["amount"]
    closing = meta["closing_balance"]["amount"]

    debit = sum(t["debit"] or 0 for t in transactions)
    credit = sum(t["credit"] or 0 for t in transactions)

    adj_debit = sum(a.amount for a in adjustments if a.direction == "DEBIT")
    adj_credit = sum(a.amount for a in adjustments if a.direction == "CREDIT")

    computed = opening + credit - debit + adj_credit - adj_debit

    col1, col2, col3 = st.columns(3)
    col1.metric("Opening Balance", opening)
    col2.metric("Computed Closing", round(computed, 2))
    col3.metric("Statement Closing", closing)

    if abs(computed - closing) < 0.05:
        st.success("✅ Reconciled")
    else:
        st.error("❌ Not reconciled")