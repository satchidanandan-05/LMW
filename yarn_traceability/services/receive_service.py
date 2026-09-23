"""Receive workflow: validate a cone + COBs payload and save it as one transaction."""
import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

import config
from database import queries as q
from services import audit_service
from utils.dates import now_local, to_db
from utils.logger import get_logger
from utils.validators import cob_after_cone, is_future, is_valid_id, normalize_id

logger = get_logger("receive")

DUPLICATE_MSG = ("Could not save: a record already exists or references unknown master data. "
                 "Please re-check and try again.")


@dataclass
class CobEntry:
    cob_id: str
    speedframe_id: str
    spindle_id: str
    cob_scan_datetime: datetime | None


@dataclass
class ReceivePayload:
    cy_id: str
    autoconer_id: str
    drum_id: str
    cone_scan_datetime: datetime | None
    cobs: list[CobEntry]


@dataclass(frozen=True)
class ValidationError:
    field: str
    row: int | None
    message: str


class ReceiveRejected(Exception):
    def __init__(self, errors: list[ValidationError]):
        super().__init__("; ".join(e.message for e in errors))
        self.errors = errors


def validate_receive(engine, payload: ReceivePayload, now: datetime | None = None) -> list[ValidationError]:
    """Check every rule and return all errors (empty list = valid). Never writes."""
    now = now or now_local()
    errors: list[ValidationError] = []
    cy_id = normalize_id(payload.cy_id)
    autoconer_id = normalize_id(payload.autoconer_id)
    drum_id = normalize_id(payload.drum_id)
    cone_dt = payload.cone_scan_datetime

    cy_ok = _check_id(errors, "cy_id", None, "CY", cy_id, "Yarn Cone ID")
    ac_ok = _check_id(errors, "autoconer_id", None, "AUTOCONER", autoconer_id, "Autoconer")
    drum_ok = _check_id(errors, "drum_id", None, "DRUM", drum_id, "Drum")
    _check_time(errors, "cone_scan_datetime", None, cone_dt, "Cone scan time", now)
    if not payload.cobs:
        errors.append(ValidationError("cobs", None, "At least one COB is required"))

    with engine.connect() as conn:
        if cy_ok and conn.execute(q.EXISTS_CONE, {"cy_id": cy_id}).first():
            errors.append(ValidationError("cy_id", None, f"Yarn Cone {cy_id} already exists"))
        if ac_ok and _check_machine(conn, errors, "autoconer_id", None, q.SELECT_AUTOCONER_ACTIVE,
                                    {"autoconer_id": autoconer_id}, f"Autoconer {autoconer_id}") and drum_ok:
            _check_owner(conn, errors, "drum_id", None, q.SELECT_DRUM_OWNER,
                         {"drum_id": drum_id}, f"Drum {drum_id}", autoconer_id)

        seen: set[str] = set()
        for row, cob in enumerate(payload.cobs, start=1):
            cob_id = normalize_id(cob.cob_id)
            speedframe_id = normalize_id(cob.speedframe_id)
            spindle_id = normalize_id(cob.spindle_id)
            if _check_id(errors, "cob_id", row, "COB", cob_id, "COB ID"):
                if cob_id in seen:
                    errors.append(ValidationError("cob_id", row, f"COB {cob_id} is repeated in this form"))
                elif conn.execute(q.EXISTS_COB, {"cob_id": cob_id}).first():
                    errors.append(ValidationError("cob_id", row, f"COB {cob_id} already exists"))
                seen.add(cob_id)
            sf_ok = _check_id(errors, "speedframe_id", row, "SPEEDFRAME", speedframe_id, "Speedframe")
            sp_ok = _check_id(errors, "spindle_id", row, "SPINDLE", spindle_id, "Spindle")
            if sf_ok and _check_machine(conn, errors, "speedframe_id", row, q.SELECT_SPEEDFRAME_ACTIVE,
                                        {"speedframe_id": speedframe_id}, f"Speedframe {speedframe_id}") and sp_ok:
                _check_owner(conn, errors, "spindle_id", row, q.SELECT_SPINDLE_OWNER,
                             {"spindle_id": spindle_id}, f"Spindle {spindle_id}", speedframe_id)
            if (_check_time(errors, "cob_scan_datetime", row, cob.cob_scan_datetime, "COB scan time", now)
                    and cone_dt is not None and cob_after_cone(cob.cob_scan_datetime, cone_dt)):
                errors.append(ValidationError("cob_scan_datetime", row,
                                              "COB scan time must be at or before the cone scan time"))
    return errors


def save_receive(engine, payload: ReceivePayload, user_id: int, now: datetime | None = None) -> str:
    """Validate, then insert cone + COBs + links in one transaction. Returns receive_txn_id."""
    now = now or now_local()
    cy_id = normalize_id(payload.cy_id)
    errors = validate_receive(engine, payload, now)
    if errors:
        _reject(engine, user_id, cy_id, errors)

    txn_id = str(uuid.uuid4())
    created_at = to_db(now)
    try:
        with engine.begin() as conn:
            conn.execute(q.INSERT_CONE, {
                "cy_id": cy_id, "drum_id": normalize_id(payload.drum_id),
                "cone_scan_datetime": to_db(payload.cone_scan_datetime),
                "receive_txn_id": txn_id, "created_by": user_id, "created_at": created_at,
            })
            for cob in payload.cobs:
                conn.execute(q.INSERT_COB, {
                    "cob_id": normalize_id(cob.cob_id), "spindle_id": normalize_id(cob.spindle_id),
                    "cob_scan_datetime": to_db(cob.cob_scan_datetime),
                    "receive_txn_id": txn_id, "created_by": user_id, "created_at": created_at,
                })
            for cob in payload.cobs:
                conn.execute(q.INSERT_TRACE, {
                    "cy_id": cy_id, "cob_id": normalize_id(cob.cob_id),
                    "receive_txn_id": txn_id, "created_at": created_at,
                })
    except IntegrityError:
        logger.warning("Receive integrity failure for %s", cy_id, exc_info=True)
        _reject(engine, user_id, cy_id, [ValidationError("system", None, DUPLICATE_MSG)])
    except SQLAlchemyError:
        logger.exception("Receive save failed for %s", cy_id)
        _reject(engine, user_id, cy_id, [ValidationError("system", None, config.SYSTEM_ERROR_MSG)])

    audit_service.log(engine, user_id, "RECEIVE", "SUCCESS", id_type="CY", id_value=cy_id,
                      detail=f"txn={txn_id}; cobs={len(payload.cobs)}")
    return txn_id


def _reject(engine, user_id: int, cy_id: str, errors: list[ValidationError]) -> None:
    audit_service.log(engine, user_id, "RECEIVE", "FAILED", id_type="CY", id_value=cy_id,
                      detail="; ".join(e.message for e in errors)[:1000])
    raise ReceiveRejected(errors)


def _check_id(errors, field, row, kind, value, label) -> bool:
    if not value:
        errors.append(ValidationError(field, row, f"{label} is required"))
        return False
    if not is_valid_id(kind, value):
        errors.append(ValidationError(field, row, f"{label} '{value}' has an invalid format"))
        return False
    return True


def _check_time(errors, field, row, value, label, now) -> bool:
    if value is None:
        errors.append(ValidationError(field, row, f"{label} is required"))
        return False
    if is_future(value, now):
        errors.append(ValidationError(field, row, f"{label} cannot be in the future"))
        return False
    return True


def _check_machine(conn, errors, field, row, stmt, params, label) -> bool:
    is_active = conn.execute(stmt, params).scalar()
    if is_active is None:
        errors.append(ValidationError(field, row, f"{label} does not exist"))
        return False
    if not is_active:
        errors.append(ValidationError(field, row, f"{label} is inactive"))
        return False
    return True


def _check_owner(conn, errors, field, row, stmt, params, label, expected_parent) -> None:
    owner = conn.execute(stmt, params).scalar()
    if owner is None:
        errors.append(ValidationError(field, row, f"{label} does not exist"))
    elif owner != expected_parent:
        errors.append(ValidationError(field, row, f"{label} belongs to {owner}, not {expected_parent}"))
