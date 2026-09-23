"""Admin: machine masters, users and the audit log."""
import pandas as pd
import streamlit as st

from database.database import get_engine
from services import audit_service, master_service
from services.master_service import ROLES, MasterDataError
from ui.components import require_role


def _attempt(action, success_message: str) -> None:
    try:
        action()
    except MasterDataError as error:
        st.error(str(error))
    else:
        st.success(success_message)


def render() -> None:
    user = require_role("admin")
    engine = get_engine()
    st.header("Admin")
    machines_tab, users_tab, audit_tab = st.tabs(["Machines", "Users", "Audit Log"])
    with machines_tab:
        _machines(engine, user.user_id)
    with users_tab:
        _users(engine, user.user_id)
    with audit_tab:
        _audit(engine)


def _machines(engine, admin_id: int) -> None:
    left, right = st.columns(2)
    with left:
        with st.form("add_autoconer", clear_on_submit=True):
            st.markdown("**Add Autoconer**")
            autoconer_id = st.text_input("Autoconer ID", placeholder="AC-04")
            name = st.text_input("Machine name", key="ac_name")
            if st.form_submit_button("Add Autoconer"):
                _attempt(lambda: master_service.add_autoconer(engine, admin_id, autoconer_id, name),
                         f"Autoconer {autoconer_id.strip().upper()} added")
        with st.form("add_drum", clear_on_submit=True):
            st.markdown("**Add Drum**")
            drum_id = st.text_input("Drum ID", placeholder="D041")
            parent = st.selectbox("Autoconer", [a["autoconer_id"] for a in
                                                master_service.list_autoconers(engine, active_only=False)])
            if st.form_submit_button("Add Drum"):
                _attempt(lambda: master_service.add_drum(engine, admin_id, drum_id, parent),
                         f"Drum {drum_id.strip().upper()} added")
    with right:
        with st.form("add_speedframe", clear_on_submit=True):
            st.markdown("**Add Speedframe**")
            speedframe_id = st.text_input("Speedframe ID", placeholder="SF-06")
            sf_name = st.text_input("Machine name", key="sf_name")
            if st.form_submit_button("Add Speedframe"):
                _attempt(lambda: master_service.add_speedframe(engine, admin_id, speedframe_id, sf_name),
                         f"Speedframe {speedframe_id.strip().upper()} added")
        with st.form("add_spindle", clear_on_submit=True):
            st.markdown("**Add Spindle**")
            spindle_id = st.text_input("Spindle ID", placeholder="S301")
            sf_parent = st.selectbox("Speedframe", [s["speedframe_id"] for s in
                                                    master_service.list_speedframes(engine, active_only=False)])
            if st.form_submit_button("Add Spindle"):
                _attempt(lambda: master_service.add_spindle(engine, admin_id, spindle_id, sf_parent),
                         f"Spindle {spindle_id.strip().upper()} added")

    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    for column, title, rows in [
        (c1, "Autoconers", master_service.list_autoconers(engine, active_only=False)),
        (c2, "Drums", master_service.list_drums(engine)),
        (c3, "Speedframes", master_service.list_speedframes(engine, active_only=False)),
        (c4, "Spindles", master_service.list_spindles(engine)),
    ]:
        column.markdown(f"**{title}**")
        column.dataframe(pd.DataFrame(rows), hide_index=True)


def _users(engine, admin_id: int) -> None:
    left, right = st.columns(2)
    with left:
        with st.form("add_user", clear_on_submit=True):
            st.markdown("**Add User**")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            role = st.selectbox("Role", ROLES)
            if st.form_submit_button("Add User"):
                _attempt(lambda: master_service.add_user(engine, admin_id, username, password, role),
                         f"User {username.strip()} added")
    with right:
        candidates = [u for u in master_service.list_users(engine)
                      if u["status"] == "active" and u["user_id"] != admin_id]
        with st.form("disable_user"):
            st.markdown("**Disable User**")
            target = st.selectbox("User", candidates, format_func=lambda u: f"{u['username']} ({u['role']})")
            if st.form_submit_button("Disable", disabled=not candidates) and target:
                _attempt(lambda: master_service.disable_user(engine, admin_id, target["user_id"]),
                         f"User {target['username']} disabled")
    st.dataframe(pd.DataFrame(master_service.list_users(engine)), hide_index=True)


def _audit(engine) -> None:
    action = st.selectbox("Action", ["All", *audit_service.ACTIONS])
    rows = audit_service.recent(engine, limit=200, action=None if action == "All" else action)
    st.dataframe(pd.DataFrame(rows), hide_index=True)
