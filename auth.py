import streamlit as st


def require_login():
    if not st.experimental_user.is_logged_in:
        st.warning("Please log in to access this app.")
        st.stop()
    allowed = st.secrets.get("ALLOWED_EMAILS", [])
    if allowed and st.experimental_user.email not in allowed:
        st.error("Access denied.")
        st.stop()
