import pandas as pd
import pytest
from sqlalchemy import text

from database.database import init_database, make_engine
from services import audit_service
from services.auth_service import authenticate
from services.import_service import import_dataset
from services.traceability_service import search_cob, search_cy


def make_sheets(**overrides) -> dict[str, pd.DataFrame]:
    sheets = {
        "Autoconer": pd.DataFrame({
            "Autoconer_ID": ["AC-01", "AC-02"], "Autoconer_Name": ["Autoconer-01", "Autoconer-02"],
            "Machine_Status": ["Running", "Maintenance"]}),
        "Drum": pd.DataFrame({"Drum_ID": ["D0101"], "Autoconer_ID": ["AC-01"], "Drum_Status": ["Active"]}),
        "Speedframe": pd.DataFrame({
            "Speedframe_ID": ["SF-01"], "Speedframe_Name": ["Speedframe-01"], "Machine_Status": ["Running"]}),
        "Spindle": pd.DataFrame({
            "Spindle_ID": ["S101", "S102"], "Speedframe_ID": ["SF-01", "SF-01"], "Spindle_Status": ["Active"] * 2}),
        "Yarn_Cone": pd.DataFrame({
            "CY_ID": ["YC001", "YC006"], "Autoconer_ID": ["AC-01", "AC-02"], "Drum_ID": ["D0101", "D025"],
            "Cone_Scan_DateTime": ["2026-09-01 08:33:00", "2026-09-20 11:12:09"],
            "Created_By": ["SampleAdmin", "System"]}),
        "COB": pd.DataFrame({
            "COB_ID": ["COB001", "COB002", "COB003"], "Speedframe_ID": ["SF-01"] * 3,
            "Spindle_ID": ["S101", "S102", "S101"], "COB_Status": ["Consumed"] * 3}),
        "COB_Traceability": pd.DataFrame({
            "Trace_ID": ["1", "2", "3"], "CY_ID": ["YC006", "YC001", "YC001"],
            "COB_ID": ["COB001", "COB001", "COB002"],
            "COB_Scan_DateTime": ["2026-09-20 08:05:12", "2026-09-01 06:33:00", "2026-09-01 06:26:00"],
            "Created_By": ["System", "SampleAdmin", "SampleAdmin"]}),
        "Users": pd.DataFrame({
            "User_ID": ["U001", "U002", "U003", "U004"],
            "Username": ["admin", "production01", "quality01", "supervisor01"],
            "Role": ["Administrator", "Production User", "Quality User", "Supervisor"],
            "Status": ["Active"] * 4}),
        "Audit_Log": pd.DataFrame({
            "Audit_ID": ["AUD001", "AUD002"], "User_ID": ["U002", "U003"],
            "Action": ["SEARCH_CY", "REPORT_COB"], "Search_ID": ["YC006", "COB001"],
            "Action_DateTime": ["2026-09-20 11:15:00", "2026-09-20 11:20:00"], "Result": ["SUCCESS"] * 2}),
    }
    sheets.update(overrides)
    return sheets


@pytest.fixture
def empty_engine():
    eng = make_engine("sqlite:///:memory:")
    init_database(eng, sample_data=False)
    yield eng
    eng.dispose()


def test_imports_cones_and_links(empty_engine):
    report = import_dataset(empty_engine, make_sheets(), bcrypt_rounds=4)
    yc001 = search_cy(empty_engine, "YC001")
    assert yc001.status == "FOUND"
    assert yc001.cone.autoconer_id == "AC-01" and yc001.cone.drum_id == "D0101"
    assert [c.cob_id for c in yc001.cobs] == ["COB002"]
    assert yc001.cobs[0].spindle_id == "S102"
    assert report.counts["yarn_cone"] == 2 and report.counts["cob_traceability"] == 2


def test_second_link_for_same_cob_is_rejected_and_reported(empty_engine):
    report = import_dataset(empty_engine, make_sheets(), bcrypt_rounds=4)
    assert search_cob(empty_engine, "COB001").cone.cy_id == "YC006"
    assert any("Trace_ID 2" in r and "COB001" in r and "YC006" in r for r in report.rejected)


def test_missing_drum_is_created_on_cone_autoconer_and_reported(empty_engine):
    report = import_dataset(empty_engine, make_sheets(), bcrypt_rounds=4)
    yc006 = search_cy(empty_engine, "YC006")
    assert (yc006.cone.autoconer_id, yc006.cone.drum_id) == ("AC-02", "D025")
    assert any("D025" in n and "AC-02" in n for n in report.notes)


def test_unlinked_cob_is_skipped_and_reported(empty_engine):
    report = import_dataset(empty_engine, make_sheets(), bcrypt_rounds=4)
    assert search_cob(empty_engine, "COB003").status == "NOT_FOUND"
    assert any("COB003" in r for r in report.skipped)


def test_spindle_on_wrong_speedframe_is_rejected(empty_engine):
    sheets = make_sheets(Speedframe=pd.DataFrame({
        "Speedframe_ID": ["SF-01", "SF-02"], "Speedframe_Name": ["a", "b"], "Machine_Status": ["Running"] * 2}))
    sheets["COB"].loc[1, "Speedframe_ID"] = "SF-02"  # COB002 claims SF-02 but S102 belongs to SF-01
    report = import_dataset(empty_engine, sheets, bcrypt_rounds=4)
    assert search_cob(empty_engine, "COB002").status == "NOT_FOUND"
    assert any("COB002" in r and "S102" in r for r in report.rejected)


def test_machine_status_maps_to_active_flag(empty_engine):
    import_dataset(empty_engine, make_sheets(), bcrypt_rounds=4)
    with empty_engine.connect() as conn:
        flags = dict(conn.execute(text("SELECT autoconer_id, is_active FROM autoconer")).all())
    assert flags == {"AC-01": 1, "AC-02": 0}


def test_users_are_mapped_and_demo_accounts_kept(empty_engine):
    import_dataset(empty_engine, make_sheets(), bcrypt_rounds=4)
    assert authenticate(empty_engine, "production01", "production01123").role == "operator"
    assert authenticate(empty_engine, "quality01", "quality01123").role == "supervisor"
    assert authenticate(empty_engine, "supervisor01", "supervisor01123").role == "supervisor"
    assert authenticate(empty_engine, "admin", "admin123").role == "admin"
    assert authenticate(empty_engine, "operator1", "operator123").role == "operator"
    assert authenticate(empty_engine, "supervisor1", "supervisor123").role == "supervisor"


def test_audit_log_rows_are_imported(empty_engine):
    import_dataset(empty_engine, make_sheets(), bcrypt_rounds=4)
    rows = [r for r in audit_service.recent(empty_engine) if r["action"] in ("SEARCH", "REPORT")]
    assert {(r["username"], r["action"], r["id_type"], r["id_value"]) for r in rows} == {
        ("production01", "SEARCH", "CY", "YC006"), ("quality01", "REPORT", "COB", "COB001")}
