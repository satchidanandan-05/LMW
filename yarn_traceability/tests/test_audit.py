import pytest
from sqlalchemy import text

from services import audit_service
from utils.logger import get_logger


def test_log_writes_row_and_returns_id(engine):
    audit_id = audit_service.log(engine, 2, "SEARCH", "FOUND", id_type="CY", id_value="YC006")
    assert isinstance(audit_id, int)
    row = audit_service.recent(engine)[0]
    assert row["audit_id"] == audit_id
    assert (row["username"], row["action"], row["id_type"], row["id_value"], row["result"]) == (
        "operator1", "SEARCH", "CY", "YC006", "FOUND")


def test_recent_filters_by_action_newest_first(engine):
    audit_service.log(engine, 2, "SEARCH", "FOUND")
    audit_service.log(engine, 3, "REPORT", "FOUND")
    audit_service.log(engine, 3, "REPORT", "PARTIAL")
    rows = audit_service.recent(engine, action="REPORT")
    assert [r["result"] for r in rows] == ["PARTIAL", "FOUND"]


def test_log_failure_does_not_raise(engine):
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE audit_log"))
    assert audit_service.log(engine, 2, "SEARCH", "FOUND") is None


def test_log_rejects_unknown_action(engine):
    with pytest.raises(ValueError):
        audit_service.log(engine, 2, "DELETE", "SUCCESS")


def test_logger_is_namespaced_and_has_file_handler():
    logger = get_logger("unit")
    assert logger.name == "traceability.unit"
    assert logger.parent.handlers
