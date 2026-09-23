"""SEARCH module: look up a Yarn Cone or COB and show its full traceability."""
import streamlit as st

from database.database import get_engine
from services import traceability_service
from ui.components import ID_TYPE_LABELS, render_trace_result, require_role
from utils.validators import normalize_id


def _clear() -> None:
    st.session_state.pop("search_result", None)
    st.session_state["search_id"] = ""


def render() -> None:
    user = require_role("search")
    st.header("Search")
    with st.form("search_form"):
        id_type = st.radio("Search by", list(ID_TYPE_LABELS), format_func=ID_TYPE_LABELS.get,
                           horizontal=True, key="search_type")
        id_value = st.text_input("ID", placeholder="e.g. YC006 or COB004", key="search_id")
        c1, c2, _ = st.columns([1, 1, 6])
        submitted = c1.form_submit_button("Search", type="primary")
        c2.form_submit_button("Clear", on_click=_clear)

    if submitted:
        if not normalize_id(id_value):
            st.warning("Enter an ID to search.")
        else:
            st.session_state.search_result = traceability_service.search(
                get_engine(), user.user_id, id_type, id_value)

    result = st.session_state.get("search_result")
    if result is not None:
        render_trace_result(result, highlight_cob=result.searched_id if result.searched_type == "COB" else None)
