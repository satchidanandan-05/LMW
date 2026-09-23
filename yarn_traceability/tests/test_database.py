import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from database.database import init_database, is_initialized, make_engine
from utils.security import hash_password, verify_password

EXPECTED_TABLES = {
    "autoconer", "drum", "speedframe", "spindle", "users",
    "yarn_cone", "cob", "cob_traceability", "audit_log",
}


def test_schema_creates_all_tables(engine):
    with engine.connect() as conn:
        names = {r[0] for r in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))}
    assert EXPECTED_TABLES <= names


def test_foreign_keys_are_enforced(engine):
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO drum (drum_id, autoconer_id) VALUES ('D999', 'AC-99')"))


def test_cob_can_link_to_only_one_cone(engine):
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(text(
                "INSERT INTO cob_traceability (cy_id, cob_id, receive_txn_id, created_at) "
                "VALUES ('YC001', 'COB004', 't', '2026-09-23 10:00:00')"
            ))


def test_sample_data_contains_image_scenario(engine):
    with engine.connect() as conn:
        cobs = conn.execute(text(
            "SELECT cob_id FROM cob_traceability WHERE cy_id = 'YC006' ORDER BY cob_id"
        )).scalars().all()
    assert cobs == ["COB004", "COB005", "COB015"]


def test_demo_users_seeded_with_hashes(engine):
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT username, password_hash, role FROM users ORDER BY user_id")).all()
    assert [(r.username, r.role) for r in rows] == [
        ("admin", "admin"), ("operator1", "operator"), ("supervisor1", "supervisor"),
    ]
    assert rows[1].password_hash != "operator123"
    assert verify_password("operator123", rows[1].password_hash)


def test_is_initialized():
    eng = make_engine("sqlite:///:memory:")
    assert not is_initialized(eng)
    init_database(eng, sample_data=False, bcrypt_rounds=4)
    assert is_initialized(eng)


def test_verify_password_rejects_wrong_and_garbage():
    hashed = hash_password("secret", rounds=4)
    assert verify_password("secret", hashed)
    assert not verify_password("nope", hashed)
    assert not verify_password("secret", "not-a-hash")
