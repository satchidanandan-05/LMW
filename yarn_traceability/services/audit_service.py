"""Audit trail for Login, Search, Receive, Report, Export and Admin actions."""
from database import queries as q
from utils.dates import now_local, to_db
from utils.logger import get_logger

logger = get_logger("audit")

ACTIONS = ("LOGIN", "SEARCH", "RECEIVE", "REPORT", "EXPORT", "ADMIN")


def log(engine, user_id: int | None, action: str, result: str, id_type: str | None = None,
        id_value: str | None = None, detail: str | None = None) -> int | None:
    """Write one audit row. A failure is logged to file and never blocks the user's action."""
    if action not in ACTIONS:
        raise ValueError(f"Unknown audit action {action!r}")
    params = {
        "user_id": user_id, "action": action, "id_type": id_type, "id_value": id_value,
        "result": result, "detail": detail, "event_datetime": to_db(now_local()),
    }
    try:
        with engine.begin() as conn:
            return conn.execute(q.INSERT_AUDIT, params).lastrowid
    except Exception:
        logger.exception("Audit write failed: %s", params)
        return None


def recent(engine, limit: int = 200, action: str | None = None) -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(q.SELECT_RECENT_AUDIT, {"limit": limit, "action": action}).mappings()
        return [dict(r) for r in rows]
