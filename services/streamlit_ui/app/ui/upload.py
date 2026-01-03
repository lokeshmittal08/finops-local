import streamlit as st
from api import extract_statement


def upload_section():
    st.header("📄 Upload Bank Statement")

    uploaded = st.file_uploader(
        "Upload PDF statement",
        type=["pdf"],
    )

    if uploaded and st.button("Extract"):
        with st.spinner("Extracting..."):
            result = extract_statement(uploaded)
            st.session_state["statement"] = result
            st.success("Extraction complete")