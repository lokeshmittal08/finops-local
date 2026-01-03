import streamlit as st
from datetime import date

def adjustments_page():
    st.header("➕ Add Extra Expense / Income (UI Only)")

    if "manual_txns" not in st.session_state:
        st.session_state.manual_txns = []

    with st.form("manual_txn_form"):
        txn_date = st.date_input("Date", date.today())
        description = st.text_input("Description")
        amount = st.number_input("Amount", min_value=0.0)
        txn_type = st.selectbox("Type", ["Debit", "Credit"])
        currency = st.selectbox("Currency", ["AED", "INR"])

        submitted = st.form_submit_button("Add")

    if submitted:
        st.session_state.manual_txns.append({
            "date": txn_date.isoformat(),
            "description": description,
            "debit": amount if txn_type == "Debit" else None,
            "credit": amount if txn_type == "Credit" else None,
            "balance_after": None,
            "currency": currency,
            "direction": txn_type.upper(),
            "confidence": 1.0,
            "reference_id": "MANUAL",
            "raw": {"source": "ui"},
        })
        st.success("Added (UI only)")

    if st.session_state.manual_txns:
        st.subheader("Manual Entries (Session)")
        st.dataframe(st.session_state.manual_txns)