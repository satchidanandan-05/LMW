"""Shared Streamlit pieces: page role guard and the traceability result view."""
import pandas as pd
import streamlit as st

from services.auth_service import User, has_role
from services.traceability_service import TraceResult
from ui.graph import build_dot
from utils.dates import to_display

ID_TYPE_LABELS = {"CY": "Yarn Cone ID", "COB": "COB ID"}
STATUS_BADGES = {
    "FOUND": ("Found", "green"),
    "PARTIAL": ("Partial", "orange"),
    "INCONSISTENT": ("Data Inconsistency", "red"),
    "NOT_FOUND": ("Not Found", "gray"),
    "ERROR": ("Error", "red"),
}
COB_TABLE_COLUMNS = ["Sl. No.", "COB ID", "Speedframe", "Spindle", "COB Scan Date & Time"]


def require_role(page: str) -> User:
    user = st.session_state.get("user")
    if not has_role(user, page):
        st.error("You do not have access to this page.")
        st.stop()
    return user


def _cob_table(trace: TraceResult) -> pd.DataFrame:
    rows = [[i, c.cob_id, c.speedframe_id, c.spindle_id, to_display(c.cob_scan_datetime)]
            for i, c in enumerate(trace.cobs, start=1)]
    return pd.DataFrame(rows, columns=COB_TABLE_COLUMNS)


def _highlighter(cob_id: str | None):
    def style(row):
        colour = "background-color: rgba(255, 193, 7, 0.35)" if row["COB ID"] == cob_id else ""
        return [colour] * len(row)
    return style


def render_trace_result(trace: TraceResult, highlight_cob: str | None = None) -> None:
    label, colour = STATUS_BADGES[trace.status]
    st.markdown(f"Status: :{colour}-background[**{label}**]")
    if trace.status == "NOT_FOUND":
        st.info(f"No record found for {ID_TYPE_LABELS[trace.searched_type]} {trace.searched_id}.")
        return
    if trace.status == "ERROR":
        st.error(trace.exceptions[0])
        return

    left, right = st.columns([3, 2], gap="large")
    with left:
        if trace.cone:
            cone = trace.cone
            st.subheader(f"Traceability result for Yarn Cone: {cone.cy_id}")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Yarn Cone ID", cone.cy_id)
            c2.metric("Produced in Autoconer", cone.autoconer_id)
            c3.metric("Drum ID", cone.drum_id)
            c4.metric("Cone Scan Date & Time", to_display(cone.cone_scan_datetime))
            st.markdown("**COBs used for this Yarn Cone**")
        else:
            st.subheader("No linked Yarn Cone")
            st.markdown("**COB**")
        table = _cob_table(trace)
        if table.empty:
            st.caption("No COBs linked.")
        else:
            st.dataframe(table.style.apply(_highlighter(highlight_cob), axis=1), hide_index=True)
    with right:
        st.markdown("**Traceability flow**")
        st.graphviz_chart(build_dot(trace, highlight_cob))

    if trace.exceptions:
        st.warning("**Exceptions**\n\n" + "\n".join(f"- {e}" for e in trace.exceptions))
