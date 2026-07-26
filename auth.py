import streamlit as st

ALLOWED_EMAILS = {"bjgsm00th@gmail.com", "aydenrush@gmail.com"}


def require_login():
    _user = getattr(st, "user", None) or getattr(st, "experimental_user", None)
    if _user is not None:
        email = _user.get("email") if isinstance(_user, dict) else getattr(_user, "email", None)
    else:
        email = None
    if email and email not in ALLOWED_EMAILS:
        st.error("You don't have access to this app.")
        st.stop()
