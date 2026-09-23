from datetime import datetime

import pytest
from sqlalchemy.exc import OperationalError

import config
from services import audit_service
from services import traceability_service as ts


def _ids(result):
    return [(c.cob_id, c.speedframe_id, c.spindle_id) for c in result.cobs]


def test_cy_search_returns_image_scenario(engine):
    r = ts.search_cy(engine, " yc006 ")
    assert (r.status, r.searched_type, r.searched_id) == ("FOUND", "CY", "YC006")
    assert r.cone == ts.ConeInfo("YC006", "AC-02", "D025", datetime(2026, 9, 20, 11, 12, 9))
    assert _ids(r) == [("COB004", "SF-02", "S128"), ("COB005", "SF-02", "S129"), ("COB015", "SF-05", "S210")]
    assert r.cobs[2].cob_scan_datetime == datetime(2026, 9, 20, 9, 14, 33)
    assert r.exceptions == []


def test_cob_search_returns_cone_and_all_sibling_cobs(engine):
    r = ts.search_cob(engine, "COB005")
    assert (r.status, r.searched_type, r.searched_id) == ("FOUND", "COB", "COB005")
    assert r.cone.cy_id == "YC006"
    assert [c.cob_id for c in r.cobs] == ["COB004", "COB005", "COB015"]


def test_unknown_id_is_not_found(engine):
    r = ts.get_traceability(engine, "CY", "YC999")
    assert (r.status, r.cone, r.cobs) == ("NOT_FOUND", None, [])
    assert ts.get_traceability(engine, "COB", "COB999").status == "NOT_FOUND"


def test_cone_without_cobs_is_partial(engine):
    r = ts.search_cy(engine, "YC007")
    assert r.status == "PARTIAL"
    assert r.exceptions == ["Yarn Cone YC007 has no linked COBs"]


def test_orphan_cob_is_partial(engine):
    r = ts.search_cob(engine, "COB099")
    assert (r.status, r.cone) == ("PARTIAL", None)
    assert _ids(r) == [("COB099", "SF-02", "S130")]
    assert r.exceptions == ["COB COB099 is not linked to any Yarn Cone"]


def test_cob_scanned_after_cone_is_inconsistent(engine):
    r = ts.search_cy(engine, "YC008")
    assert r.status == "INCONSISTENT"
    assert r.exceptions == [
        "COB COB021 scanned at 21-09-2026 10:45:00 after Yarn Cone YC008 scanned at 21-09-2026 10:00:00"
    ]


def test_database_error_returns_error_status(engine, monkeypatch):
    def boom(conn, cy_id):
        raise OperationalError("SELECT", {}, Exception("db down"))

    monkeypatch.setattr(ts, "_search_cy", boom)
    r = ts.get_traceability(engine, "CY", "YC006")
    assert (r.status, r.cone, r.cobs) == ("ERROR", None, [])
    assert r.exceptions == [config.SYSTEM_ERROR_MSG]


def test_invalid_id_type_raises(engine):
    with pytest.raises(ValueError):
        ts.get_traceability(engine, "DRUM", "D025")


def test_search_writes_audit_row(engine):
    r = ts.search(engine, 2, "cob", "cob004")
    assert r.status == "FOUND"
    row = audit_service.recent(engine)[0]
    assert (row["action"], row["id_type"], row["id_value"], row["result"]) == ("SEARCH", "COB", "COB004", "FOUND")
