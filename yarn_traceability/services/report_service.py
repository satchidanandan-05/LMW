"""Report dataset preparation. Uses the same traceability service as Search."""
from dataclasses import dataclass
from datetime import datetime

from services import audit_service
from services.auth_service import User
from services.traceability_service import TraceResult, get_traceability
from utils.dates import now_local

ENTITY_LABELS = {"CY": "Yarn Cone", "COB": "COB"}


@dataclass
class ReportData:
    title: str
    generated_at: datetime
    generated_by: str
    reference_no: str
    trace: TraceResult


def generate_report(engine, id_type: str, id_value: str, user: User,
                    now: datetime | None = None) -> ReportData:
    trace = get_traceability(engine, id_type, id_value)
    audit_id = audit_service.log(engine, user.user_id, "REPORT", trace.status,
                                 id_type=trace.searched_type, id_value=trace.searched_id)
    return ReportData(
        title=f"Traceability Report - {ENTITY_LABELS[trace.searched_type]} {trace.searched_id}",
        generated_at=now or now_local(),
        generated_by=user.username,
        reference_no=f"RPT-{audit_id}" if audit_id is not None else "RPT-UNLOGGED",
        trace=trace,
    )


def trace_chain(trace: TraceResult, arrow: str = "→") -> str:
    cobs = ", ".join(f"{c.cob_id} ({c.speedframe_id}/{c.spindle_id})" for c in trace.cobs)
    if trace.cone:
        cone = trace.cone
        return f"{cone.cy_id} {arrow} {cone.autoconer_id} / {cone.drum_id} {arrow} {cobs or 'no COBs'}"
    if trace.cobs:
        return f"{cobs} {arrow} no Yarn Cone link"
    return "No traceability data"


def record_export(engine, user_id: int, report: ReportData, fmt: str) -> None:
    audit_service.log(engine, user_id, "EXPORT", "SUCCESS",
                      id_type=report.trace.searched_type, id_value=report.trace.searched_id,
                      detail=f"format={fmt}; ref={report.reference_no}")
