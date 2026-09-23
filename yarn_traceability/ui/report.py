"""REPORT module: full traceability report for a CY or COB ID, with PDF/Excel/CSV download."""
import streamlit as st

from database.database import get_engine
from services import export_service, report_service
from ui.components import ID_TYPE_LABELS, render_trace_result, require_role
from utils.dates import to_display
from utils.validators import normalize_id

FORMATS = [
    ("PDF", "pdf", "application/pdf", export_service.to_pdf),
    ("Excel", "xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", export_service.to_excel),
    ("CSV", "csv", "text/csv", export_service.to_csv),
]


def render() -> None:
    user = require_role("report")
    engine = get_engine()
    st.header("Report")
    with st.form("report_form"):
        id_type = st.radio("Report for", list(ID_TYPE_LABELS), format_func=ID_TYPE_LABELS.get, horizontal=True)
        id_value = st.text_input("ID", placeholder="e.g. YC006 or COB004")
        generate = st.form_submit_button("Generate report", type="primary")

    if generate:
        if not normalize_id(id_value):
            st.warning("Enter an ID to report on.")
        else:
            st.session_state.report = report_service.generate_report(engine, id_type, id_value, user)

    report = st.session_state.get("report")
    if report is None:
        return
    trace = report.trace
    st.subheader(report.title)
    st.caption(f"{report.reference_no} · Generated {to_display(report.generated_at)} by {report.generated_by}")
    render_trace_result(trace, highlight_cob=trace.searched_id if trace.searched_type == "COB" else None)
    if trace.status in ("NOT_FOUND", "ERROR"):
        return
    st.markdown(f"**Traceability:** {report_service.trace_chain(trace)}")

    stem = export_service.file_stem(report)
    for column, (label, ext, mime, build) in zip(st.columns(len(FORMATS)), FORMATS):
        column.download_button(
            f"Download {label}", data=build(report), file_name=f"{stem}.{ext}", mime=mime,
            on_click=report_service.record_export, args=(engine, user.user_id, report, label),
        )
