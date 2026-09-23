from datetime import datetime

import pytest
from sqlalchemy import text

from services import audit_service
from services import receive_service as rs
from services.receive_service import CobEntry, ReceivePayload, ReceiveRejected, ValidationError
from services.traceability_service import search_cy

NOW = datetime(2026, 9, 23, 16, 0, 0)


def make_payload(**overrides) -> ReceivePayload:
    base = dict(
        cy_id="YC900", autoconer_id="AC-01", drum_id="D011",
        cone_scan_datetime=datetime(2026, 9, 23, 12, 0, 0),
        cobs=[
            CobEntry("COB900", "SF-01", "S101", datetime(2026, 9, 23, 10, 0, 0)),
            CobEntry("COB901", "SF-02", "S128", datetime(2026, 9, 23, 10, 30, 0)),
        ],
    )
    base.update(overrides)
    return ReceivePayload(**base)


def errors_for(engine, **overrides):
    return rs.validate_receive(engine, make_payload(**overrides), NOW)


def test_valid_payload_has_no_errors(engine):
    assert rs.validate_receive(engine, make_payload(), NOW) == []


def test_ids_are_normalized_before_checks(engine):
    assert errors_for(engine, cy_id=" yc900 ", autoconer_id="ac-01", drum_id="d011") == []


def test_blank_and_malformed_ids(engine):
    errs = errors_for(engine, cy_id="", drum_id="X1",
                      cobs=[CobEntry("COP1", "SF-01", "S101", datetime(2026, 9, 23, 10))])
    assert ValidationError("cy_id", None, "Yarn Cone ID is required") in errs
    assert ValidationError("drum_id", None, "Drum 'X1' has an invalid format") in errs
    assert ValidationError("cob_id", 1, "COB ID 'COP1' has an invalid format") in errs


def test_existing_cone_rejected(engine):
    assert ValidationError("cy_id", None, "Yarn Cone YC006 already exists") in errors_for(engine, cy_id="YC006")


def test_requires_at_least_one_cob(engine):
    assert ValidationError("cobs", None, "At least one COB is required") in errors_for(engine, cobs=[])


def test_cob_repeated_in_form(engine):
    t = datetime(2026, 9, 23, 10)
    errs = errors_for(engine, cobs=[CobEntry("COB900", "SF-01", "S101", t), CobEntry("cob900", "SF-01", "S102", t)])
    assert ValidationError("cob_id", 2, "COB COB900 is repeated in this form") in errs


def test_existing_cob_rejected(engine):
    errs = errors_for(engine, cobs=[CobEntry("COB004", "SF-01", "S101", datetime(2026, 9, 23, 10))])
    assert ValidationError("cob_id", 1, "COB COB004 already exists") in errs


def test_drum_must_belong_to_autoconer(engine):
    assert ValidationError("drum_id", None, "Drum D025 belongs to AC-02, not AC-01") in errors_for(engine, drum_id="D025")


def test_spindle_must_belong_to_speedframe(engine):
    errs = errors_for(engine, cobs=[CobEntry("COB900", "SF-01", "S210", datetime(2026, 9, 23, 10))])
    assert ValidationError("spindle_id", 1, "Spindle S210 belongs to SF-05, not SF-01") in errs


def test_unknown_masters(engine):
    assert ValidationError("autoconer_id", None, "Autoconer AC-09 does not exist") in errors_for(engine, autoconer_id="AC-09")
    errs = errors_for(engine, cobs=[CobEntry("COB900", "SF-09", "S101", datetime(2026, 9, 23, 10))])
    assert ValidationError("speedframe_id", 1, "Speedframe SF-09 does not exist") in errs


def test_future_cone_time_rejected(engine):
    errs = errors_for(engine, cone_scan_datetime=datetime(2026, 9, 23, 17, 0, 0))
    assert ValidationError("cone_scan_datetime", None, "Cone scan time cannot be in the future") in errs


def test_cob_after_cone_rejected(engine):
    errs = errors_for(engine, cobs=[CobEntry("COB900", "SF-01", "S101", datetime(2026, 9, 23, 12, 30))])
    assert ValidationError("cob_scan_datetime", 1, "COB scan time must be at or before the cone scan time") in errs


def test_missing_times(engine):
    assert ValidationError("cone_scan_datetime", None, "Cone scan time is required") in errors_for(engine, cone_scan_datetime=None)
    errs = errors_for(engine, cobs=[CobEntry("COB900", "SF-01", "S101", None)])
    assert ValidationError("cob_scan_datetime", 1, "COB scan time is required") in errs


def test_collects_all_errors_at_once(engine):
    errs = errors_for(engine, cy_id="", drum_id="D025", cobs=[])
    assert {e.field for e in errs} >= {"cy_id", "drum_id", "cobs"}


def test_save_writes_all_rows_with_one_txn_id(engine):
    txn = rs.save_receive(engine, make_payload(cy_id="yc900"), user_id=2, now=NOW)
    result = search_cy(engine, "YC900")
    assert result.status == "FOUND"
    assert [c.cob_id for c in result.cobs] == ["COB900", "COB901"]
    with engine.connect() as conn:
        txns = set(conn.execute(text(
            "SELECT receive_txn_id FROM yarn_cone WHERE cy_id = 'YC900' "
            "UNION SELECT receive_txn_id FROM cob WHERE cob_id IN ('COB900', 'COB901') "
            "UNION SELECT receive_txn_id FROM cob_traceability WHERE cy_id = 'YC900'"
        )).scalars())
    assert txns == {txn}
    row = audit_service.recent(engine)[0]
    assert (row["action"], row["result"], row["id_value"]) == ("RECEIVE", "SUCCESS", "YC900")


def test_save_rejects_invalid_and_audits_failure(engine):
    with pytest.raises(ReceiveRejected) as exc:
        rs.save_receive(engine, make_payload(cy_id="YC006"), user_id=2, now=NOW)
    assert "Yarn Cone YC006 already exists" in [e.message for e in exc.value.errors]
    row = audit_service.recent(engine)[0]
    assert (row["action"], row["result"]) == ("RECEIVE", "FAILED")


def test_failure_midway_rolls_back_everything(engine, monkeypatch):
    monkeypatch.setattr(rs, "validate_receive", lambda *args, **kwargs: [])
    bad = make_payload(cobs=[
        CobEntry("COB900", "SF-01", "S101", datetime(2026, 9, 23, 10)),
        CobEntry("COB901", "SF-01", "S999", datetime(2026, 9, 23, 10)),  # unknown spindle -> FK error
    ])
    with pytest.raises(ReceiveRejected):
        rs.save_receive(engine, bad, user_id=2, now=NOW)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM yarn_cone WHERE cy_id = 'YC900'")).scalar() == 0
        assert conn.execute(text("SELECT COUNT(*) FROM cob WHERE cob_id = 'COB900'")).scalar() == 0
