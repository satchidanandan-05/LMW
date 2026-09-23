"""Central CY/COB traceability retrieval, shared by Search and Report."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from sqlalchemy.exc import SQLAlchemyError

import config
from database import queries as q
from services import audit_service
from utils.dates import from_db, to_display
from utils.logger import get_logger
from utils.validators import normalize_id

logger = get_logger("traceability")

IdType = Literal["CY", "COB"]
Status = Literal["FOUND", "NOT_FOUND", "PARTIAL", "INCONSISTENT", "ERROR"]
ID_TYPES = ("CY", "COB")


@dataclass(frozen=True)
class ConeInfo:
    cy_id: str
    autoconer_id: str
    drum_id: str
    cone_scan_datetime: datetime


@dataclass(frozen=True)
class CobInfo:
    cob_id: str
    speedframe_id: str
    spindle_id: str
    cob_scan_datetime: datetime


@dataclass
class TraceResult:
    status: Status
    searched_type: IdType
    searched_id: str
    cone: ConeInfo | None = None
    cobs: list[CobInfo] = field(default_factory=list)
    exceptions: list[str] = field(default_factory=list)


def get_traceability(engine, id_type: str, id_value: str) -> TraceResult:
    id_type = (id_type or "").upper()
    if id_type not in ID_TYPES:
        raise ValueError(f"id_type must be one of {ID_TYPES}, got {id_type!r}")
    id_value = normalize_id(id_value)
    try:
        with engine.connect() as conn:
            if id_type == "CY":
                return _search_cy(conn, id_value)
            return _search_cob(conn, id_value)
    except SQLAlchemyError:
        logger.exception("Traceability lookup failed for %s %s", id_type, id_value)
        return TraceResult("ERROR", id_type, id_value, exceptions=[config.SYSTEM_ERROR_MSG])


def search_cy(engine, cy_id: str) -> TraceResult:
    return get_traceability(engine, "CY", cy_id)


def search_cob(engine, cob_id: str) -> TraceResult:
    return get_traceability(engine, "COB", cob_id)


def search(engine, user_id: int, id_type: str, id_value: str) -> TraceResult:
    """Search-page entry point: trace, then record a SEARCH audit row."""
    result = get_traceability(engine, id_type, id_value)
    audit_service.log(engine, user_id, "SEARCH", result.status,
                      id_type=result.searched_type, id_value=result.searched_id)
    return result


def _search_cy(conn, cy_id: str) -> TraceResult:
    cone = _load_cone(conn, cy_id)
    if cone is None:
        return TraceResult("NOT_FOUND", "CY", cy_id)
    return _classify("CY", cy_id, cone, _load_cobs(conn, cy_id))


def _search_cob(conn, cob_id: str) -> TraceResult:
    row = conn.execute(q.SELECT_COB, {"cob_id": cob_id}).mappings().first()
    if row is None:
        return TraceResult("NOT_FOUND", "COB", cob_id)
    cy_id = conn.execute(q.SELECT_CONE_ID_FOR_COB, {"cob_id": cob_id}).scalar()
    if cy_id is None:
        return TraceResult("PARTIAL", "COB", cob_id, cone=None, cobs=[_cob_from_row(row)],
                           exceptions=[f"COB {cob_id} is not linked to any Yarn Cone"])
    return _classify("COB", cob_id, _load_cone(conn, cy_id), _load_cobs(conn, cy_id))


def _load_cone(conn, cy_id: str) -> ConeInfo | None:
    row = conn.execute(q.SELECT_CONE, {"cy_id": cy_id}).mappings().first()
    if row is None:
        return None
    return ConeInfo(row["cy_id"], row["autoconer_id"], row["drum_id"], from_db(row["cone_scan_datetime"]))


def _load_cobs(conn, cy_id: str) -> list[CobInfo]:
    return [_cob_from_row(r) for r in conn.execute(q.SELECT_COBS_FOR_CONE, {"cy_id": cy_id}).mappings()]


def _cob_from_row(row) -> CobInfo:
    return CobInfo(row["cob_id"], row["speedframe_id"], row["spindle_id"], from_db(row["cob_scan_datetime"]))


def _classify(id_type: IdType, id_value: str, cone: ConeInfo, cobs: list[CobInfo]) -> TraceResult:
    late = [
        f"COB {c.cob_id} scanned at {to_display(c.cob_scan_datetime)} after Yarn Cone "
        f"{cone.cy_id} scanned at {to_display(cone.cone_scan_datetime)}"
        for c in cobs if c.cob_scan_datetime > cone.cone_scan_datetime
    ]
    if late:
        return TraceResult("INCONSISTENT", id_type, id_value, cone, cobs, late)
    if not cobs:
        return TraceResult("PARTIAL", id_type, id_value, cone, cobs,
                           [f"Yarn Cone {cone.cy_id} has no linked COBs"])
    return TraceResult("FOUND", id_type, id_value, cone, cobs)
