"""Streamlit entry point: login gate and role-based navigation.  Run: streamlit run app.py"""
import streamlit as st

import config
from database.database import get_engine, is_initialized
from services.auth_service import has_role
from ui import admin, login, receive, report, search

st.set_page_config(page_title="Yarn Traceability", page_icon="🧵", layout="wide")

# (page key, title, icon, render function). Order = sidebar order; the first allowed page is the landing page.
PAGES = [
    ("search", "Search", ":material/search:", search.render),
    ("receive", "Receive", ":material/add_box:", receive.render),
    ("report", "Report", ":material/description:", report.render),
    ("admin", "Admin", ":material/settings:", admin.render),
]


def _logout() -> None:
    st.session_state.clear()


def main() -> None:
    if not is_initialized(get_engine()):
        st.error("Database is not initialized. Run `python scripts/init_db.py`, then reload this page.")
        st.stop()

    user = st.session_state.get("user")
    if user is None:
        st.navigation([st.Page(login.render, title="Login", url_path="login")], position="hidden").run()
        return

    allowed = [p for p in PAGES if has_role(user, p[0])]
    pages = [st.Page(fn, title=title, icon=icon, url_path=key, default=(i == 0))
             for i, (key, title, icon, fn) in enumerate(allowed)]
    with st.sidebar:
        st.markdown(f"**{config.APP_NAME}**")
        st.caption(f"Signed in as **{user.username}** ({user.role})")
        st.button("Log out", on_click=_logout)
    st.navigation(pages).run()


main()
