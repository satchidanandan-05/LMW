"""Login page."""
import streamlit as st

import config
from database.database import get_engine
from services.auth_service import authenticate


def render() -> None:
    st.title(config.APP_NAME)
    _, middle, _ = st.columns([1, 1, 1])
    with middle:
        with st.form("login"):
            st.subheader("Sign in")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log in", type="primary")
        if submitted:
            user = authenticate(get_engine(), username, password)
            if user is None:
                st.error("Invalid username or password, or the account is disabled.")
            else:
                st.session_state.user = user
                st.rerun()
