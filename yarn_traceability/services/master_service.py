"""Admin maintenance of machine masters and users."""
from sqlalchemy.exc import SQLAlchemyError

import config
from database import queries as q
from services import audit_service
from utils.logger import get_logger
from utils.security import hash_password
from utils.validators import is_valid_id, normalize_id

logger = get_logger("master")

ROLES = ("operator", "supervisor", "admin")
MIN_PASSWORD_LENGTH = 6


class MasterDataError(Exception):
    """Admin input was rejected. The message is safe to show to the user."""


# --- reads -----------------------------------------------------------------------
def _rows(engine, stmt, params=None) -> list[dict]:
    with engine.connect() as conn:
        return [dict(r) for r in conn.execute(stmt, params or {}).mappings()]


def _scalar(engine, stmt, params):
    with engine.connect() as conn:
        return conn.execute(stmt, params).scalar()


def list_autoconers(engine, active_only: bool = True) -> list[dict]:
    return _rows(engine, q.LIST_AUTOCONERS, {"active_only": int(active_only)})


def list_drums(engine, autoconer_id: str | None = None) -> list[dict]:
    return _rows(engine, q.LIST_DRUMS, {"autoconer_id": autoconer_id})


def list_speedframes(engine, active_only: bool = True) -> list[dict]:
    return _rows(engine, q.LIST_SPEEDFRAMES, {"active_only": int(active_only)})


def list_spindles(engine, speedframe_id: str | None = None) -> list[dict]:
    return _rows(engine, q.LIST_SPINDLES, {"speedframe_id": speedframe_id})


def list_users(engine) -> list[dict]:
    return _rows(engine, q.LIST_USERS)


# --- writes ----------------------------------------------------------------------
def _require_id(kind: str, value: str, label: str) -> str:
    value = normalize_id(value)
    if not is_valid_id(kind, value):
        raise MasterDataError(f"{label} '{value}' has an invalid format")
    return value


def _require_name(machine_name: str) -> str:
    name = (machine_name or "").strip()
    if not name:
        raise MasterDataError("Machine name is required")
    return name


def _write(engine, admin_id: int, stmt, params: dict, detail: str) -> None:
    try:
        with engine.begin() as conn:
            conn.execute(stmt, params)
    except SQLAlchemyError:
        logger.exception("Admin write failed: %s", detail)
        audit_service.log(engine, admin_id, "ADMIN", "FAILED", detail=detail)
        raise MasterDataError(config.SYSTEM_ERROR_MSG)
    audit_service.log(engine, admin_id, "ADMIN", "SUCCESS", detail=detail)


def add_autoconer(engine, admin_id: int, autoconer_id: str, machine_name: str) -> None:
    aid = _require_id("AUTOCONER", autoconer_id, "Autoconer ID")
    name = _require_name(machine_name)
    if _scalar(engine, q.SELECT_AUTOCONER_ACTIVE, {"autoconer_id": aid}) is not None:
        raise MasterDataError(f"Autoconer {aid} already exists")
    _write(engine, admin_id, q.INSERT_AUTOCONER, {"autoconer_id": aid, "machine_name": name},
           f"add autoconer {aid}")


def add_drum(engine, admin_id: int, drum_id: str, autoconer_id: str) -> None:
    did = _require_id("DRUM", drum_id, "Drum ID")
    aid = _require_id("AUTOCONER", autoconer_id, "Autoconer ID")
    if _scalar(engine, q.SELECT_DRUM_OWNER, {"drum_id": did}) is not None:
        raise MasterDataError(f"Drum {did} already exists")
    if _scalar(engine, q.SELECT_AUTOCONER_ACTIVE, {"autoconer_id": aid}) is None:
        raise MasterDataError(f"Autoconer {aid} does not exist")
    _write(engine, admin_id, q.INSERT_DRUM, {"drum_id": did, "autoconer_id": aid},
           f"add drum {did} on {aid}")


def add_speedframe(engine, admin_id: int, speedframe_id: str, machine_name: str) -> None:
    sid = _require_id("SPEEDFRAME", speedframe_id, "Speedframe ID")
    name = _require_name(machine_name)
    if _scalar(engine, q.SELECT_SPEEDFRAME_ACTIVE, {"speedframe_id": sid}) is not None:
        raise MasterDataError(f"Speedframe {sid} already exists")
    _write(engine, admin_id, q.INSERT_SPEEDFRAME, {"speedframe_id": sid, "machine_name": name},
           f"add speedframe {sid}")


def add_spindle(engine, admin_id: int, spindle_id: str, speedframe_id: str) -> None:
    pid = _require_id("SPINDLE", spindle_id, "Spindle ID")
    sid = _require_id("SPEEDFRAME", speedframe_id, "Speedframe ID")
    if _scalar(engine, q.SELECT_SPINDLE_OWNER, {"spindle_id": pid}) is not None:
        raise MasterDataError(f"Spindle {pid} already exists")
    if _scalar(engine, q.SELECT_SPEEDFRAME_ACTIVE, {"speedframe_id": sid}) is None:
        raise MasterDataError(f"Speedframe {sid} does not exist")
    _write(engine, admin_id, q.INSERT_SPINDLE, {"spindle_id": pid, "speedframe_id": sid},
           f"add spindle {pid} on {sid}")


def add_user(engine, admin_id: int, username: str, password: str, role: str,
             bcrypt_rounds: int = config.BCRYPT_ROUNDS) -> None:
    username = (username or "").strip()
    if not username:
        raise MasterDataError("Username is required")
    if len(password or "") < MIN_PASSWORD_LENGTH:
        raise MasterDataError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
    if role not in ROLES:
        raise MasterDataError(f"Role must be one of: {', '.join(ROLES)}")
    if _scalar(engine, q.SELECT_USER_BY_USERNAME, {"username": username}) is not None:
        raise MasterDataError(f"User {username} already exists")
    _write(engine, admin_id, q.INSERT_USER,
           {"username": username, "password_hash": hash_password(password, bcrypt_rounds), "role": role},
           f"add user {username} ({role})")


def disable_user(engine, admin_id: int, user_id: int) -> None:
    if user_id == admin_id:
        raise MasterDataError("You cannot disable your own account")
    _write(engine, admin_id, q.DISABLE_USER, {"user_id": user_id}, f"disable user_id {user_id}")
