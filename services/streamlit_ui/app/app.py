import streamlit as st
from db_access import (
    get_latest_statement,
    get_transactions_by_statement,
    get_available_months,
    get_monthly_summary,
)

from ui.upload import upload_section
from ui.transaction import transactions_table

from agent_client import query_agent


st.set_page_config(
    page_title="FinOps – Bank Statement Analyzer",
    layout="wide",
)

st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "",
    ["Upload", "Transactions", "Summary"],
)

# ---------------- Upload ----------------
if page == "Upload":
    upload_section()

# ---------------- Transactions ----------------
elif page == "Transactions":
    st.title("📄 Transactions")

    stmt = get_latest_statement()
    if not stmt:
        st.info("Upload a statement first")
    else:
        txns = get_transactions_by_statement(stmt["id"])
        if not txns:
            st.warning("No transactions found")
        else:
            transactions_table(txns)

# ---------------- Summary ----------------
elif page == "Summary":
    st.title("📊 Monthly Summary")

    # -------- Agent Input (NEW) --------
    st.subheader("🤖 Ask a question")
    agent_query = st.text_input(
        "Ask about expenses, weather, forex, calendar (e.g. 'Show my expenses for Oct 2025 and weather in London')"
    )

    if agent_query:
        with st.spinner("Thinking..."):
            try:
                agent_resp = query_agent(agent_query)

                # n8n returns a list with single object
                result = agent_resp[0] if isinstance(agent_resp, list) else agent_resp

                # 1️⃣ Natural language answer
                st.success(result.get("answer", ""))
                
                structured = result.get("structured", {})

                # 2️⃣ Expense summary (reuse your existing UI style)
                expenses = structured.get("expenses")
                if expenses:
                    st.subheader("📊 Expense Summary")

                    c1, c2, c3 = st.columns(3)
                    c1.metric("Total Debit", f"{expenses['total_debit']:,.2f}")
                    c2.metric("Total Credit", f"{expenses['total_credit']:,.2f}")
                    c3.metric("Net", f"{expenses['net']:,.2f}")

                # 3️⃣ Weather card
                weather = structured.get("weather")
                if weather:
                    st.subheader("🌤 Weather")
                    st.write(
                        f"**{weather['city']}** — {weather['description']}, "
                        f"{weather['temperature_c']}°C (feels like {weather['feels_like_c']}°C)"
                    )

                # 4️⃣ Forex card
                forex = structured.get("forex")
                if forex:
                    st.subheader("💱 Exchange Rate")
                    converted = abs(expenses["total_debit"]) * forex["rate"] if expenses else None
                    st.write(
                        f"1 {forex['from']} = {forex['rate']} {forex['to']}"
                    )
                    if converted:
                        st.write(
                            f"Approx value: {converted:,.2f} {forex['to']}"
                        )

            except Exception as e:
                st.error(f"Agent error: {e}")

        st.divider()
        st.info("⬇️ You can also use the manual summary below")

    # -------- Existing Dropdown Summary (UNCHANGED) --------
    months = get_available_months()
    if not months:
        st.warning("No extracted data yet")
    else:
        col1, col2 = st.columns(2)

        with col1:
            month = st.selectbox(
                "Month",
                sorted({int(m["month"]) for m in months}),
            )
        with col2:
            year = st.selectbox(
                "Year",
                sorted({int(m["year"]) for m in months}),
            )

        df = get_monthly_summary(year, month)
        if df.empty:
            st.info("No data for selected period")
        else:
            total_debit = df["debit"].fillna(0).sum()
            total_credit = df["credit"].fillna(0).sum()
            net = total_credit - total_debit

            c1, c2, c3 = st.columns(3)
            c1.metric("Total Debit", f"{total_debit:,.2f}")
            c2.metric("Total Credit", f"{total_credit:,.2f}")
            c3.metric("Net", f"{net:,.2f}")

            st.divider()
            st.dataframe(df, use_container_width=True)

# elif page == "Summary":
#     st.title("📊 Monthly Summary")

#     months = get_available_months()
#     if not months:
#         st.warning("No extracted data yet")
#     else:
#         col1, col2 = st.columns(2)

#         with col1:
#             month = st.selectbox(
#                 "Month",
#                 sorted({int(m["month"]) for m in months}),
#             )
#         with col2:
#             year = st.selectbox(
#                 "Year",
#                 sorted({int(m["year"]) for m in months}),
#             )

#         df = get_monthly_summary(year, month)
#         if df.empty:
#             st.info("No data for selected period")
#         else:
#             total_debit = df["debit"].fillna(0).sum()
#             total_credit = df["credit"].fillna(0).sum()
#             net = total_credit - total_debit

#             c1, c2, c3 = st.columns(3)
#             c1.metric("Total Debit", f"{total_debit:,.2f}")
#             c2.metric("Total Credit", f"{total_credit:,.2f}")
#             c3.metric("Net", f"{net:,.2f}")

#             st.divider()
#             st.dataframe(df, use_container_width=True)


# import sys
# import os
# sys.path.append(os.path.dirname(__file__))

# import streamlit as st
# from ui.upload import upload_section
# from ui.transaction import transactions_table
# from ui.adjustments import adjustments_page
# from ui.summary import summary_page

# st.set_page_config(layout="wide")

# page = st.sidebar.radio(
#     "Navigation",
#     ["Upload", "Transactions", "Adjustments", "Summary"]
# )

# if page == "Upload":
#     upload_section()

# elif page == "Transactions":
#     if "transactions" in st.session_state:
#         transactions_table(st.session_state.transactions)
#     else:
#         st.info("Upload a statement first")

# elif page == "Adjustments":
#     adjustments_page()

# elif page == "Summary":
#     summary_page()