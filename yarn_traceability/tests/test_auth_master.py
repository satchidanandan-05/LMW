import pytest

from services import audit_service, master_service as ms
from services.auth_service import User, authenticate, has_role
from services.master_service import MasterDataError


def test_authenticate_success_is_audited(engine):
    assert authenticate(engine, "operator1", "operator123") == User(2, "operator1", "operator")
    row = audit_service.recent(engine)[0]
    assert (row["action"], row["result"], row["username"]) == ("LOGIN", "SUCCESS", "operator1")


def test_wrong_password_rejected_and_audited(engine):
    assert authenticate(engine, "operator1", "wrong") is None
    row = audit_service.recent(engine)[0]
    assert (row["action"], row["result"]) == ("LOGIN", "FAILED")


def test_unknown_user_rejected(engine):
    assert authenticate(engine, "ghost", "x") is None
    row = audit_service.recent(engine)[0]
    assert (row["action"], row["result"], row["username"]) == ("LOGIN", "FAILED", None)


def test_disabled_user_cannot_log_in(engine):
    ms.disable_user(engine, admin_id=1, user_id=2)
    assert authenticate(engine, "operator1", "operator123") is None


@pytest.mark.parametrize("role,page,allowed", [
    ("operator", "search", True), ("operator", "receive", True),
    ("operator", "report", False), ("operator", "admin", False),
    ("supervisor", "search", True), ("supervisor", "receive", False),
    ("supervisor", "report", True), ("supervisor", "admin", False),
    ("admin", "search", True), ("admin", "receive", True),
    ("admin", "report", True), ("admin", "admin", True),
])
def test_role_matrix(role, page, allowed):
    assert has_role(User(1, "x", role), page) is allowed


def test_has_role_without_user():
    assert not has_role(None, "search")


def test_add_machines_and_list(engine):
    ms.add_autoconer(engine, 1, "ac-04", "Autoconer 4")
    ms.add_drum(engine, 1, "d041", "AC-04")
    ms.add_speedframe(engine, 1, "SF-06", "Speedframe 6")
    ms.add_spindle(engine, 1, "S301", "SF-06")
    assert "AC-04" in [a["autoconer_id"] for a in ms.list_autoconers(engine)]
    assert [d["drum_id"] for d in ms.list_drums(engine, "AC-04")] == ["D041"]
    assert [s["spindle_id"] for s in ms.list_spindles(engine, "SF-06")] == ["S301"]
    assert len(ms.list_drums(engine)) == 7
    rows = audit_service.recent(engine, action="ADMIN")
    assert len(rows) == 4 and all(r["result"] == "SUCCESS" for r in rows)


def test_add_machine_rejections(engine):
    with pytest.raises(MasterDataError, match="Autoconer AC-01 already exists"):
        ms.add_autoconer(engine, 1, "AC-01", "Dup")
    with pytest.raises(MasterDataError, match="has an invalid format"):
        ms.add_drum(engine, 1, "DRUM1", "AC-01")
    with pytest.raises(MasterDataError, match="Speedframe SF-99 does not exist"):
        ms.add_spindle(engine, 1, "S999", "SF-99")
    with pytest.raises(MasterDataError, match="Machine name is required"):
        ms.add_speedframe(engine, 1, "SF-07", "  ")


def test_add_user_then_login(engine):
    ms.add_user(engine, 1, "operator2", "secret99", "operator", bcrypt_rounds=4)
    user = authenticate(engine, "operator2", "secret99")
    assert user is not None and user.role == "operator"
    assert "operator2" in [u["username"] for u in ms.list_users(engine)]


def test_add_user_rejections(engine):
    with pytest.raises(MasterDataError, match="at least 6"):
        ms.add_user(engine, 1, "newbie", "123", "operator", bcrypt_rounds=4)
    with pytest.raises(MasterDataError, match="Role must be one of"):
        ms.add_user(engine, 1, "newbie", "secret99", "manager", bcrypt_rounds=4)
    with pytest.raises(MasterDataError, match="User operator1 already exists"):
        ms.add_user(engine, 1, "operator1", "secret99", "operator", bcrypt_rounds=4)


def test_admin_cannot_disable_self(engine):
    with pytest.raises(MasterDataError, match="cannot disable your own account"):
        ms.disable_user(engine, admin_id=1, user_id=1)
