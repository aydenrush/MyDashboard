import streamlit as st


def require_login():
    email = st.user.email
    if not email:
        st.warning("Please log in to access this app.")
        st.stop()
    allowed = st.secrets.get("ALLOWED_EMAILS", [])
    if allowed and email not in allowed:
        st.error("Access denied.")
        st.stop()
