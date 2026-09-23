"""Login and role-based page access."""
from dataclasses import dataclass

from sqlalchemy.exc import SQLAlchemyError

from database import queries as q
from services import audit_service
from utils.logger import get_logger
from utils.security import verify_password

logger = get_logger("auth")

PAGE_ROLES: dict[str, set[str]] = {
    "search": {"operator", "supervisor", "admin"},
    "receive": {"operator", "admin"},
    "report": {"supervisor", "admin"},
    "admin": {"admin"},
}


@dataclass(frozen=True)
class User:
    user_id: int
    username: str
    role: str


def authenticate(engine, username: str, password: str) -> User | None:
    username = (username or "").strip()
    try:
        with engine.connect() as conn:
            row = conn.execute(q.SELECT_USER_BY_USERNAME, {"username": username}).mappings().first()
    except SQLAlchemyError:
        logger.exception("Login lookup failed for %s", username)
        return None
    if row is None:
        reason = "unknown user"
    elif row["status"] != "active":
        reason = "user disabled"
    elif not verify_password(password or "", row["password_hash"]):
        reason = "wrong password"
    else:
        reason = None
    audit_service.log(engine, row["user_id"] if row else None, "LOGIN",
                      "FAILED" if reason else "SUCCESS",
                      detail=f"username={username}" + (f"; {reason}" if reason else ""))
    if reason:
        return None
    return User(row["user_id"], row["username"], row["role"])


def has_role(user: User | None, page: str) -> bool:
    return user is not None and user.role in PAGE_ROLES.get(page, set())
