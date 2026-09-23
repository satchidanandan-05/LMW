"""SQLAlchemy engine creation and database initialisation."""
from functools import lru_cache
from pathlib import Path

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

import config
from utils.security import hash_password

# (user_id, username, password, role) — demo accounts, documented in README.
DEMO_USERS = [
    (1, "admin", "admin123", "admin"),
    (2, "operator1", "operator123", "operator"),
    (3, "supervisor1", "supervisor123", "supervisor"),
]


def make_engine(url: str) -> Engine:
    kwargs = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if ":memory:" in url:
            kwargs["poolclass"] = StaticPool  # one shared in-memory DB per engine
    engine = create_engine(url, **kwargs)
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_conn, _record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    return engine


def sqlite_path(url: str) -> Path | None:
    prefix = "sqlite:///"
    if url.startswith(prefix) and ":memory:" not in url:
        return Path(url[len(prefix):])
    return None


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    path = sqlite_path(config.DATABASE_URL)
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
    return make_engine(config.DATABASE_URL)


def is_initialized(engine: Engine) -> bool:
    return inspect(engine).has_table("users")


def _run_sql_file(engine: Engine, path: Path) -> None:
    raw = engine.raw_connection()
    try:
        raw.driver_connection.executescript(path.read_text(encoding="utf-8"))
        raw.commit()
    finally:
        raw.close()


def init_database(engine: Engine, sample_data: bool = True,
                  bcrypt_rounds: int = config.BCRYPT_ROUNDS) -> None:
    _run_sql_file(engine, config.SQL_DIR / "schema.sql")
    _run_sql_file(engine, config.SQL_DIR / "indexes.sql")
    if not sample_data:
        return
    with engine.begin() as conn:
        for user_id, username, password, role in DEMO_USERS:
            conn.execute(
                text("INSERT INTO users (user_id, username, password_hash, role) "
                     "VALUES (:user_id, :username, :password_hash, :role)"),
                {"user_id": user_id, "username": username, "role": role,
                 "password_hash": hash_password(password, bcrypt_rounds)},
            )
    _run_sql_file(engine, config.SQL_DIR / "sample_data.sql")
