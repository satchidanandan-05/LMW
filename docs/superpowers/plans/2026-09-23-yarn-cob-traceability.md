# Yarn Cone / COB Traceability Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Streamlit + SQLite application that receives Yarn Cone/COB traceability data, searches it by CY ID or COB ID, and produces PDF, Excel and CSV reports.

**Architecture:** The design is SQL-first. `sql/schema.sql` is the only schema definition, and all queries are named, parameterized SQLAlchemy `text()` statements in `database/queries.py`. Services in `services/` hold every business rule, take an `engine` argument, and never import Streamlit. The Streamlit pages in `ui/` only call services. Search and Report share one function, `traceability_service.get_traceability`.

**Tech Stack:** Python 3.11, Streamlit ≥ 1.40, SQLAlchemy 2.x, SQLite, pandas, ReportLab, OpenPyXL, bcrypt, python-dotenv, tzdata, pytest.

**Spec:** `docs/superpowers/specs/2026-09-23-yarn-cob-traceability-design.md`. Read it before starting any task.

## Global Constraints

- All application code lives in `yarn_traceability/` at the repo root. **Every command in this plan runs from `yarn_traceability/`**, and all paths are relative to it.
- Use the virtualenv interpreter everywhere: `.venv/Scripts/python` (Windows; this works from Git Bash and from PowerShell).
- Use the term **COB** only. The word "COP" must never appear in UI text, code identifiers, the database or reports. The one exception is an invalid-input value inside a test.
- Every service function takes `engine` (a SQLAlchemy `Engine`) as its **first** argument. This is the one deliberate change from the spec's signatures; it is there so services can be tested.
- Services and `utils/` must not import `streamlit`.
- All SQL that includes user input is parameterized. Never build SQL with f-strings.
- Datetimes are naive plant-local time (`Asia/Kolkata`). They are stored as `YYYY-MM-DD HH:MM:SS` text and displayed as `dd-mm-yyyy HH:MM:SS`.
- ID regexes are uppercase: YC `^YC\d+$`, COB `^COB\d+$`, Autoconer `^AC-\d+$`, Drum `^D\d+$`, Speedframe `^SF-\d+$`, Spindle `^S\d+$`. Trim and uppercase input before matching.
- Every connection must run `PRAGMA foreign_keys=ON`.
- Roles: operator can use Search and Receive; supervisor can use Search and Report; admin can use every page, including Admin.
- The friendly system error text is exactly `System error — please retry or contact admin`.
- The Python `graphviz` package is **not** a dependency, because `st.graphviz_chart` renders DOT strings directly.
- Commit after every task. End each commit message with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## File Map

| File | Responsibility | Task |
|---|---|---|
| `requirements.txt`, `pytest.ini`, `.env.example` | deps, test config, env template | 1 |
| `config.py` | settings, ID regexes, constants | 1 |
| `utils/validators.py` | pure ID/time checks | 1 |
| `utils/dates.py` | now, DB/display formatting | 1 |
| `utils/security.py` | bcrypt hash/verify | 2 |
| `database/database.py` | engine factory, FK pragma, schema init | 2 |
| `sql/schema.sql`, `sql/indexes.sql`, `sql/sample_data.sql` | DB definition + demo data | 2 |
| `scripts/init_db.py` | CLI to create the DB | 2 |
| `tests/conftest.py` | in-memory DB fixture | 2 |
| `utils/logger.py` | rotating file logger | 3 |
| `database/queries.py` | all named SQL (grows per task) | 3–6 |
| `services/audit_service.py` | audit log write/read | 3 |
| `services/traceability_service.py` | CY/COB trace + status rules | 4 |
| `services/receive_service.py` | receive validation + transactional save | 5 |
| `services/auth_service.py` | login, role matrix | 6 |
| `services/master_service.py` | machine/user admin | 6 |
| `services/report_service.py` | report dataset, trace chain text, export audit | 7 |
| `services/export_service.py` | PDF/Excel/CSV bytes | 7 |
| `ui/graph.py` | DOT diagram builder (pure) | 8 |
| `ui/components.py` | role guard + shared result view | 8 |
| `ui/login.py`, `ui/search.py`, `app.py` | login, search page, navigation | 8 |
| `ui/receive.py` | receive page + grid conversion | 9 |
| `ui/report.py`, `ui/admin.py` | report page, admin page | 10 |
| `README.md` | setup + demo script | 11 |

---

### Task 1: Project scaffold, config, validators and dates

**Files:**
- Create: `yarn_traceability/requirements.txt`, `yarn_traceability/pytest.ini`, `yarn_traceability/.env.example`
- Create: `yarn_traceability/config.py`
- Create: `yarn_traceability/utils/__init__.py` (empty), `yarn_traceability/utils/validators.py`, `yarn_traceability/utils/dates.py`
- Test: `yarn_traceability/tests/test_validators.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `config.APP_NAME: str`, `config.APP_VERSION = "1.0"`, `config.REPORT_VERSION = "1.0"`, `config.DATABASE_URL: str`, `config.LOG_LEVEL: str`, `config.LOG_DIR: Path`, `config.SQL_DIR: Path`, `config.TIMEZONE = "Asia/Kolkata"`, `config.CLOCK_SKEW_MINUTES = 5`, `config.BCRYPT_ROUNDS: int`, `config.ID_PATTERNS: dict[str, str]` (keys `CY`, `COB`, `AUTOCONER`, `DRUM`, `SPEEDFRAME`, `SPINDLE`), `config.SYSTEM_ERROR_MSG: str`
  - `utils.validators.normalize_id(value: str | None) -> str`, `is_valid_id(kind: str, value: str | None) -> bool`, `is_future(dt: datetime, now: datetime, skew_minutes: int = 5) -> bool`, `cob_after_cone(cob_dt: datetime, cone_dt: datetime) -> bool`
  - `utils.dates.now_local() -> datetime`, `to_db(dt: datetime) -> str`, `from_db(s: str) -> datetime`, `to_display(dt: datetime | None) -> str`

- [ ] **Step 1: Create the folder, virtualenv and dependency files**

From the repo root, run `mkdir -p yarn_traceability/tests yarn_traceability/utils`, then `cd yarn_traceability`.

`requirements.txt`:
```
streamlit>=1.40
sqlalchemy>=2.0
pandas>=2.1
reportlab>=4.0
openpyxl>=3.1
bcrypt>=4.1
python-dotenv>=1.0
tzdata>=2024.1
pytest>=8.0
```

`pytest.ini`:
```ini
[pytest]
pythonpath = .
testpaths = tests
```

`.env.example`:
```
# Copy to .env and adjust. Leave DATABASE_URL unset to use data/traceability.db
# DATABASE_URL=sqlite:///C:/path/to/traceability.db
LOG_LEVEL=INFO
BCRYPT_ROUNDS=12
```

Run:
```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
```
Expected: the install succeeds.

- [ ] **Step 2: Write the failing tests** (`tests/test_validators.py`)

```python
from datetime import datetime

import pytest

from utils.dates import from_db, to_db, to_display
from utils.validators import cob_after_cone, is_future, is_valid_id, normalize_id


@pytest.mark.parametrize("kind,value", [
    ("CY", "YC006"), ("COB", "COB004"), ("AUTOCONER", "AC-02"), ("DRUM", "D025"),
    ("SPEEDFRAME", "SF-02"), ("SPINDLE", "S128"), ("CY", " yc6 "),
])
def test_valid_ids(kind, value):
    assert is_valid_id(kind, value)


@pytest.mark.parametrize("kind,value", [
    ("CY", ""), ("CY", None), ("CY", "CY006"), ("CY", "YC"), ("COB", "COP004"),
    ("AUTOCONER", "AC02"), ("DRUM", "D-25"), ("SPEEDFRAME", "SF02"),
    ("SPINDLE", "SF-02"), ("SPINDLE", "S12A"),
])
def test_invalid_ids(kind, value):
    assert not is_valid_id(kind, value)


def test_normalize_id():
    assert normalize_id("  cob004 ") == "COB004"
    assert normalize_id(None) == ""


def test_is_future_allows_clock_skew():
    now = datetime(2026, 9, 23, 16, 0, 0)
    assert not is_future(datetime(2026, 9, 23, 16, 4, 59), now)
    assert is_future(datetime(2026, 9, 23, 16, 5, 1), now)


def test_cob_after_cone():
    cone = datetime(2026, 9, 20, 11, 12, 9)
    assert cob_after_cone(datetime(2026, 9, 20, 11, 12, 10), cone)
    assert not cob_after_cone(cone, cone)


def test_date_formats_round_trip():
    dt = datetime(2026, 9, 20, 11, 12, 9)
    assert to_db(dt) == "2026-09-20 11:12:09"
    assert from_db("2026-09-20 11:12:09") == dt
    assert to_display(dt) == "20-09-2026 11:12:09"
    assert to_display(None) == ""
```

- [ ] **Step 3: Run the tests and confirm they fail**

Run: `.venv/Scripts/python -m pytest tests/test_validators.py -v`
Expected: collection fails with `ModuleNotFoundError: No module named 'utils.dates'` (or `'config'`).

- [ ] **Step 4: Implement**

`config.py`:
```python
"""Application settings. Values can be overridden through environment variables or .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

APP_NAME = "Yarn Cone / COB Traceability Dashboard"
APP_VERSION = "1.0"
REPORT_VERSION = "1.0"

DATABASE_URL = os.getenv(
    "DATABASE_URL", f"sqlite:///{(BASE_DIR / 'data' / 'traceability.db').as_posix()}"
)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = BASE_DIR / "logs"
SQL_DIR = BASE_DIR / "sql"

TIMEZONE = "Asia/Kolkata"
CLOCK_SKEW_MINUTES = 5
BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", "12"))

ID_PATTERNS = {
    "CY": r"^YC\d+$",
    "COB": r"^COB\d+$",
    "AUTOCONER": r"^AC-\d+$",
    "DRUM": r"^D\d+$",
    "SPEEDFRAME": r"^SF-\d+$",
    "SPINDLE": r"^S\d+$",
}

SYSTEM_ERROR_MSG = "System error — please retry or contact admin"
```

`utils/validators.py`:
```python
"""Pure validation helpers (no database access)."""
import re
from datetime import datetime, timedelta

import config


def normalize_id(value: str | None) -> str:
    return (value or "").strip().upper()


def is_valid_id(kind: str, value: str | None) -> bool:
    return re.fullmatch(config.ID_PATTERNS[kind], normalize_id(value)) is not None


def is_future(dt: datetime, now: datetime, skew_minutes: int = config.CLOCK_SKEW_MINUTES) -> bool:
    return dt > now + timedelta(minutes=skew_minutes)


def cob_after_cone(cob_dt: datetime, cone_dt: datetime) -> bool:
    return cob_dt > cone_dt
```

`utils/dates.py`:
```python
"""Plant-local time helpers. Datetimes are naive and in config.TIMEZONE."""
from datetime import datetime
from zoneinfo import ZoneInfo

import config

DB_FORMAT = "%Y-%m-%d %H:%M:%S"
DISPLAY_FORMAT = "%d-%m-%Y %H:%M:%S"


def now_local() -> datetime:
    return datetime.now(ZoneInfo(config.TIMEZONE)).replace(tzinfo=None, microsecond=0)


def to_db(dt: datetime) -> str:
    return dt.strftime(DB_FORMAT)


def from_db(value: str) -> datetime:
    return datetime.strptime(value, DB_FORMAT)


def to_display(dt: datetime | None) -> str:
    return dt.strftime(DISPLAY_FORMAT) if dt else ""
```

Also create an empty `utils/__init__.py`.

- [ ] **Step 5: Run the tests and confirm they pass**

Run: `.venv/Scripts/python -m pytest tests/test_validators.py -v`
Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt pytest.ini .env.example config.py utils/ tests/test_validators.py
git commit -m "feat: scaffold project with config, ID validators and date helpers

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Database schema, sample data, engine and init script

**Files:**
- Create: `utils/security.py`
- Create: `database/__init__.py` (empty), `database/database.py`
- Create: `sql/schema.sql`, `sql/indexes.sql`, `sql/sample_data.sql`
- Create: `scripts/init_db.py`
- Create: `tests/conftest.py`
- Test: `tests/test_database.py`

**Interfaces:**
- Consumes: `config.*` (Task 1)
- Produces:
  - `utils.security.hash_password(password: str, rounds: int = config.BCRYPT_ROUNDS) -> str`, `verify_password(password: str, password_hash: str) -> bool`
  - `database.database.make_engine(url: str) -> Engine`, `get_engine() -> Engine` (cached, uses `config.DATABASE_URL`), `sqlite_path(url: str) -> Path | None`, `is_initialized(engine) -> bool`, `init_database(engine, sample_data: bool = True, bcrypt_rounds: int = config.BCRYPT_ROUNDS) -> None`, `DEMO_USERS`
  - Pytest fixture `engine`: an in-memory database with the schema, demo users and sample data
  - Demo users: `(1, "admin", "admin123", "admin")`, `(2, "operator1", "operator123", "operator")`, `(3, "supervisor1", "supervisor123", "supervisor")`
  - Sample data facts that later tests rely on:
    - **YC006:** AC-02 / D025, scanned `2026-09-20 11:12:09`. Its COBs are COB004 (SF-02/S128, `08:05:12`), COB005 (SF-02/S129, `08:06:18`) and COB015 (SF-05/S210, `09:14:33`).
    - **YC007:** a PARTIAL cone with no COBs.
    - **YC008:** an INCONSISTENT cone. COB021 was scanned after the cone.
    - **COB099:** an orphan on S130/SF-02.
    - **Drum ownership:** D011 and D012 belong to AC-01, D025 and D026 to AC-02, and D031 and D032 to AC-03.
    - **Spindle ownership:** S101–S104 belong to SF-01, S128–S131 to SF-02, S150–S153 to SF-03, S170–S173 to SF-04, and S210–S213 to SF-05.

- [ ] **Step 1: Write the failing tests**

`tests/conftest.py`:
```python
import pytest

from database.database import init_database, make_engine


@pytest.fixture
def engine():
    eng = make_engine("sqlite:///:memory:")
    init_database(eng, sample_data=True, bcrypt_rounds=4)
    yield eng
    eng.dispose()
```

`tests/test_database.py`:
```python
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
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `.venv/Scripts/python -m pytest tests/test_database.py -v`
Expected: fails with `ModuleNotFoundError: No module named 'database'`.

- [ ] **Step 3: Implement the SQL files**

`sql/schema.sql`:
```sql
-- Yarn Cone / COB Traceability schema (SQLite). Single source of truth.
CREATE TABLE autoconer (
    autoconer_id  TEXT PRIMARY KEY,
    machine_name  TEXT NOT NULL,
    is_active     INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE drum (
    drum_id       TEXT PRIMARY KEY,
    autoconer_id  TEXT NOT NULL REFERENCES autoconer (autoconer_id)
);

CREATE TABLE speedframe (
    speedframe_id TEXT PRIMARY KEY,
    machine_name  TEXT NOT NULL,
    is_active     INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE spindle (
    spindle_id    TEXT PRIMARY KEY,
    speedframe_id TEXT NOT NULL REFERENCES speedframe (speedframe_id)
);

CREATE TABLE users (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('operator', 'supervisor', 'admin')),
    status        TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'disabled'))
);

CREATE TABLE yarn_cone (
    cy_id              TEXT PRIMARY KEY,
    drum_id            TEXT NOT NULL REFERENCES drum (drum_id),
    cone_scan_datetime TEXT NOT NULL,
    receive_txn_id     TEXT NOT NULL,
    created_by         INTEGER NOT NULL REFERENCES users (user_id),
    created_at         TEXT NOT NULL
);

CREATE TABLE cob (
    cob_id            TEXT PRIMARY KEY,
    spindle_id        TEXT NOT NULL REFERENCES spindle (spindle_id),
    cob_scan_datetime TEXT NOT NULL,
    receive_txn_id    TEXT NOT NULL,
    created_by        INTEGER NOT NULL REFERENCES users (user_id),
    created_at        TEXT NOT NULL
);

-- Many COBs -> exactly one Yarn Cone (UNIQUE cob_id).
CREATE TABLE cob_traceability (
    trace_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    cy_id          TEXT NOT NULL REFERENCES yarn_cone (cy_id),
    cob_id         TEXT NOT NULL UNIQUE REFERENCES cob (cob_id),
    receive_txn_id TEXT NOT NULL,
    created_at     TEXT NOT NULL
);

CREATE TABLE audit_log (
    audit_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER REFERENCES users (user_id),
    action         TEXT NOT NULL CHECK (action IN ('LOGIN', 'SEARCH', 'RECEIVE', 'REPORT', 'EXPORT', 'ADMIN')),
    id_type        TEXT,
    id_value       TEXT,
    result         TEXT NOT NULL,
    detail         TEXT,
    event_datetime TEXT NOT NULL
);
```

`sql/indexes.sql`:
```sql
CREATE INDEX ix_cob_traceability_cy_id ON cob_traceability (cy_id);
CREATE INDEX ix_drum_autoconer_id ON drum (autoconer_id);
CREATE INDEX ix_spindle_speedframe_id ON spindle (speedframe_id);
CREATE INDEX ix_audit_log_event_datetime ON audit_log (event_datetime);
```

`sql/sample_data.sql`. Users are inserted by `init_database` before this file runs, and `created_by = 2` is operator1.
```sql
-- Machine masters
INSERT INTO autoconer (autoconer_id, machine_name) VALUES
    ('AC-01', 'Autoconer 1'), ('AC-02', 'Autoconer 2'), ('AC-03', 'Autoconer 3');

INSERT INTO drum (drum_id, autoconer_id) VALUES
    ('D011', 'AC-01'), ('D012', 'AC-01'),
    ('D025', 'AC-02'), ('D026', 'AC-02'),
    ('D031', 'AC-03'), ('D032', 'AC-03');

INSERT INTO speedframe (speedframe_id, machine_name) VALUES
    ('SF-01', 'Speedframe 1'), ('SF-02', 'Speedframe 2'), ('SF-03', 'Speedframe 3'),
    ('SF-04', 'Speedframe 4'), ('SF-05', 'Speedframe 5');

INSERT INTO spindle (spindle_id, speedframe_id) VALUES
    ('S101', 'SF-01'), ('S102', 'SF-01'), ('S103', 'SF-01'), ('S104', 'SF-01'),
    ('S128', 'SF-02'), ('S129', 'SF-02'), ('S130', 'SF-02'), ('S131', 'SF-02'),
    ('S150', 'SF-03'), ('S151', 'SF-03'), ('S152', 'SF-03'), ('S153', 'SF-03'),
    ('S170', 'SF-04'), ('S171', 'SF-04'), ('S172', 'SF-04'), ('S173', 'SF-04'),
    ('S210', 'SF-05'), ('S211', 'SF-05'), ('S212', 'SF-05'), ('S213', 'SF-05');

-- Yarn cones
INSERT INTO yarn_cone (cy_id, drum_id, cone_scan_datetime, receive_txn_id, created_by, created_at) VALUES
    ('YC001', 'D011', '2026-09-19 10:00:00', 'seed-yc001', 2, '2026-09-19 10:00:00'),
    ('YC002', 'D012', '2026-09-19 14:30:00', 'seed-yc002', 2, '2026-09-19 14:30:00'),
    ('YC006', 'D025', '2026-09-20 11:12:09', 'seed-yc006', 2, '2026-09-20 11:12:09'),  -- example image
    ('YC007', 'D026', '2026-09-21 09:00:00', 'seed-yc007', 2, '2026-09-21 09:00:00'),  -- PARTIAL: no COBs
    ('YC008', 'D031', '2026-09-21 10:00:00', 'seed-yc008', 2, '2026-09-21 10:00:00');  -- INCONSISTENT

-- COBs
INSERT INTO cob (cob_id, spindle_id, cob_scan_datetime, receive_txn_id, created_by, created_at) VALUES
    ('COB001', 'S101', '2026-09-19 07:10:00', 'seed-yc001', 2, '2026-09-19 10:00:00'),
    ('COB002', 'S102', '2026-09-19 07:12:30', 'seed-yc001', 2, '2026-09-19 10:00:00'),
    ('COB003', 'S150', '2026-09-19 12:00:00', 'seed-yc002', 2, '2026-09-19 14:30:00'),
    ('COB004', 'S128', '2026-09-20 08:05:12', 'seed-yc006', 2, '2026-09-20 11:12:09'),
    ('COB005', 'S129', '2026-09-20 08:06:18', 'seed-yc006', 2, '2026-09-20 11:12:09'),
    ('COB015', 'S210', '2026-09-20 09:14:33', 'seed-yc006', 2, '2026-09-20 11:12:09'),
    ('COB020', 'S170', '2026-09-21 09:30:00', 'seed-yc008', 2, '2026-09-21 10:00:00'),
    ('COB021', 'S171', '2026-09-21 10:45:00', 'seed-yc008', 2, '2026-09-21 10:00:00'),  -- after its cone
    ('COB099', 'S130', '2026-09-22 08:00:00', 'seed-orphan', 2, '2026-09-22 08:00:00'); -- orphan

-- COB -> Yarn Cone links
INSERT INTO cob_traceability (cy_id, cob_id, receive_txn_id, created_at) VALUES
    ('YC001', 'COB001', 'seed-yc001', '2026-09-19 10:00:00'),
    ('YC001', 'COB002', 'seed-yc001', '2026-09-19 10:00:00'),
    ('YC002', 'COB003', 'seed-yc002', '2026-09-19 14:30:00'),
    ('YC006', 'COB004', 'seed-yc006', '2026-09-20 11:12:09'),
    ('YC006', 'COB005', 'seed-yc006', '2026-09-20 11:12:09'),
    ('YC006', 'COB015', 'seed-yc006', '2026-09-20 11:12:09'),
    ('YC008', 'COB020', 'seed-yc008', '2026-09-21 10:00:00'),
    ('YC008', 'COB021', 'seed-yc008', '2026-09-21 10:00:00');
```

- [ ] **Step 4: Implement the Python modules**

`utils/security.py`:
```python
"""Password hashing with bcrypt."""
import bcrypt

import config


def hash_password(password: str, rounds: int = config.BCRYPT_ROUNDS) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=rounds)).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except ValueError:
        return False
```

`database/database.py`:
```python
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
```

Also create an empty `database/__init__.py`.

`scripts/init_db.py`:
```python
"""Create the traceability database with schema, indexes, demo users and sample data.

Usage:  python scripts/init_db.py [--reset]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402
from database.database import get_engine, init_database, is_initialized, sqlite_path  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reset", action="store_true", help="delete the existing SQLite database first")
    args = parser.parse_args(argv)

    path = sqlite_path(config.DATABASE_URL)
    if args.reset and path is not None and path.exists():
        path.unlink()

    engine = get_engine()
    if is_initialized(engine):
        print("Database already initialized. Use --reset to recreate it.")
        return 1
    init_database(engine)
    print(f"Database ready: {config.DATABASE_URL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run the tests and confirm they pass**

Run: `.venv/Scripts/python -m pytest tests/ -v`
Expected: all tests PASS, including Task 1's.

- [ ] **Step 6: Smoke-test the init script**

Run: `.venv/Scripts/python scripts/init_db.py --reset`
Expected: prints `Database ready: sqlite:///.../yarn_traceability/data/traceability.db`.
Run it again without `--reset`. Expected: `Database already initialized. Use --reset to recreate it.` and exit code 1.

- [ ] **Step 7: Commit**

```bash
git add utils/security.py database/ sql/ scripts/ tests/conftest.py tests/test_database.py
git commit -m "feat: add SQLite schema, sample data, engine factory and init script

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Logger and audit service

**Files:**
- Create: `utils/logger.py`
- Create: `database/queries.py`
- Create: `services/__init__.py` (empty), `services/audit_service.py`
- Test: `tests/test_audit.py`

**Interfaces:**
- Consumes: `engine` fixture, `utils.dates.now_local/to_db` and `config.LOG_DIR/LOG_LEVEL` (Tasks 1–2)
- Produces:
  - `utils.logger.get_logger(name: str) -> logging.Logger`, which returns a logger named `traceability.<name>`
  - `services.audit_service.ACTIONS: tuple[str, ...]`
  - `services.audit_service.log(engine, user_id: int | None, action: str, result: str, id_type: str | None = None, id_value: str | None = None, detail: str | None = None) -> int | None`. It returns the `audit_id`, or `None` if the write failed. It never raises on a database failure, but raises `ValueError` for an unknown action.
  - `services.audit_service.recent(engine, limit: int = 200, action: str | None = None) -> list[dict]`, where each dict has the keys `audit_id, event_datetime, username, action, id_type, id_value, result, detail`, newest first.
  - `database.queries.INSERT_AUDIT`, `SELECT_RECENT_AUDIT`

- [ ] **Step 1: Write the failing tests** (`tests/test_audit.py`)

```python
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
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `.venv/Scripts/python -m pytest tests/test_audit.py -v`
Expected: fails with `ModuleNotFoundError: No module named 'services'`.

- [ ] **Step 3: Implement**

`utils/logger.py`:
```python
"""Application logging to a rotating file in logs/app.log."""
import logging
from logging.handlers import RotatingFileHandler

import config

_ROOT = "traceability"


def get_logger(name: str) -> logging.Logger:
    root = logging.getLogger(_ROOT)
    if not root.handlers:
        config.LOG_DIR.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            config.LOG_DIR / "app.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        root.addHandler(handler)
        root.setLevel(config.LOG_LEVEL)
    return root.getChild(name)
```

`database/queries.py`:
```python
"""Named, parameterized SQL statements. No SQL lives anywhere else in the application."""
from sqlalchemy import text

# --- audit -------------------------------------------------------------------
INSERT_AUDIT = text("""
    INSERT INTO audit_log (user_id, action, id_type, id_value, result, detail, event_datetime)
    VALUES (:user_id, :action, :id_type, :id_value, :result, :detail, :event_datetime)
""")

SELECT_RECENT_AUDIT = text("""
    SELECT a.audit_id, a.event_datetime, u.username, a.action, a.id_type, a.id_value,
           a.result, a.detail
    FROM audit_log a
    LEFT JOIN users u ON u.user_id = a.user_id
    WHERE (:action IS NULL OR a.action = :action)
    ORDER BY a.audit_id DESC
    LIMIT :limit
""")
```

`services/audit_service.py`:
```python
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
```

Also create an empty `services/__init__.py`.

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `.venv/Scripts/python -m pytest tests/ -v`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add utils/logger.py database/queries.py services/ tests/test_audit.py
git commit -m "feat: add rotating logger and audit service

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Central traceability service

**Files:**
- Modify: `database/queries.py` (append a traceability section)
- Create: `services/traceability_service.py`
- Test: `tests/test_traceability.py`

**Interfaces:**
- Consumes: `audit_service.log`, `audit_service.recent` (Task 3); `normalize_id` (Task 1); `from_db`, `to_display` (Task 1); `config.SYSTEM_ERROR_MSG`
- Produces (`services.traceability_service`):
  - `ConeInfo(cy_id: str, autoconer_id: str, drum_id: str, cone_scan_datetime: datetime)`, a frozen dataclass
  - `CobInfo(cob_id: str, speedframe_id: str, spindle_id: str, cob_scan_datetime: datetime)`, a frozen dataclass
  - `TraceResult(status, searched_type, searched_id, cone: ConeInfo | None = None, cobs: list[CobInfo] = [], exceptions: list[str] = [])`, a dataclass where `status` is one of `FOUND`, `NOT_FOUND`, `PARTIAL`, `INCONSISTENT` or `ERROR`, and `searched_type` is `CY` or `COB`
  - `ID_TYPES = ("CY", "COB")`
  - `get_traceability(engine, id_type: str, id_value: str) -> TraceResult` (does not audit)
  - `search_cy(engine, cy_id) -> TraceResult` and `search_cob(engine, cob_id) -> TraceResult`
  - `search(engine, user_id: int, id_type: str, id_value: str) -> TraceResult`, which is `get_traceability` plus a `SEARCH` audit row
  - Exception message formats:
    - `"Yarn Cone {cy} has no linked COBs"`
    - `"COB {cob} is not linked to any Yarn Cone"`
    - `"COB {cob} scanned at {dd-mm-yyyy HH:MM:SS} after Yarn Cone {cy} scanned at {dd-mm-yyyy HH:MM:SS}"`

- [ ] **Step 1: Write the failing tests** (`tests/test_traceability.py`)

```python
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
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `.venv/Scripts/python -m pytest tests/test_traceability.py -v`
Expected: fails with `ImportError: cannot import name 'traceability_service'`.

- [ ] **Step 3: Append the queries to `database/queries.py`**

```python

# --- traceability ------------------------------------------------------------
SELECT_CONE = text("""
    SELECT yc.cy_id, d.autoconer_id, yc.drum_id, yc.cone_scan_datetime
    FROM yarn_cone yc
    JOIN drum d ON d.drum_id = yc.drum_id
    WHERE yc.cy_id = :cy_id
""")

SELECT_COBS_FOR_CONE = text("""
    SELECT c.cob_id, s.speedframe_id, c.spindle_id, c.cob_scan_datetime
    FROM cob_traceability ct
    JOIN cob c ON c.cob_id = ct.cob_id
    JOIN spindle s ON s.spindle_id = c.spindle_id
    WHERE ct.cy_id = :cy_id
    ORDER BY c.cob_scan_datetime, c.cob_id
""")

SELECT_COB = text("""
    SELECT c.cob_id, s.speedframe_id, c.spindle_id, c.cob_scan_datetime
    FROM cob c
    JOIN spindle s ON s.spindle_id = c.spindle_id
    WHERE c.cob_id = :cob_id
""")

SELECT_CONE_ID_FOR_COB = text("SELECT cy_id FROM cob_traceability WHERE cob_id = :cob_id")
```

- [ ] **Step 4: Implement `services/traceability_service.py`**

```python
"""Central CY/COB traceability retrieval, shared by Search and Report."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from sqlalchemy.exc import SQLAlchemyError

import config
from database import queries as q
from services import audit_service
from utils.dates import from_db, to_display
from utils.logger import get_logger
from utils.validators import normalize_id

logger = get_logger("traceability")

IdType = Literal["CY", "COB"]
Status = Literal["FOUND", "NOT_FOUND", "PARTIAL", "INCONSISTENT", "ERROR"]
ID_TYPES = ("CY", "COB")


@dataclass(frozen=True)
class ConeInfo:
    cy_id: str
    autoconer_id: str
    drum_id: str
    cone_scan_datetime: datetime


@dataclass(frozen=True)
class CobInfo:
    cob_id: str
    speedframe_id: str
    spindle_id: str
    cob_scan_datetime: datetime


@dataclass
class TraceResult:
    status: Status
    searched_type: IdType
    searched_id: str
    cone: ConeInfo | None = None
    cobs: list[CobInfo] = field(default_factory=list)
    exceptions: list[str] = field(default_factory=list)


def get_traceability(engine, id_type: str, id_value: str) -> TraceResult:
    id_type = (id_type or "").upper()
    if id_type not in ID_TYPES:
        raise ValueError(f"id_type must be one of {ID_TYPES}, got {id_type!r}")
    id_value = normalize_id(id_value)
    try:
        with engine.connect() as conn:
            if id_type == "CY":
                return _search_cy(conn, id_value)
            return _search_cob(conn, id_value)
    except SQLAlchemyError:
        logger.exception("Traceability lookup failed for %s %s", id_type, id_value)
        return TraceResult("ERROR", id_type, id_value, exceptions=[config.SYSTEM_ERROR_MSG])


def search_cy(engine, cy_id: str) -> TraceResult:
    return get_traceability(engine, "CY", cy_id)


def search_cob(engine, cob_id: str) -> TraceResult:
    return get_traceability(engine, "COB", cob_id)


def search(engine, user_id: int, id_type: str, id_value: str) -> TraceResult:
    """Search-page entry point: trace, then record a SEARCH audit row."""
    result = get_traceability(engine, id_type, id_value)
    audit_service.log(engine, user_id, "SEARCH", result.status,
                      id_type=result.searched_type, id_value=result.searched_id)
    return result


def _search_cy(conn, cy_id: str) -> TraceResult:
    cone = _load_cone(conn, cy_id)
    if cone is None:
        return TraceResult("NOT_FOUND", "CY", cy_id)
    return _classify("CY", cy_id, cone, _load_cobs(conn, cy_id))


def _search_cob(conn, cob_id: str) -> TraceResult:
    row = conn.execute(q.SELECT_COB, {"cob_id": cob_id}).mappings().first()
    if row is None:
        return TraceResult("NOT_FOUND", "COB", cob_id)
    cy_id = conn.execute(q.SELECT_CONE_ID_FOR_COB, {"cob_id": cob_id}).scalar()
    if cy_id is None:
        return TraceResult("PARTIAL", "COB", cob_id, cone=None, cobs=[_cob_from_row(row)],
                           exceptions=[f"COB {cob_id} is not linked to any Yarn Cone"])
    return _classify("COB", cob_id, _load_cone(conn, cy_id), _load_cobs(conn, cy_id))


def _load_cone(conn, cy_id: str) -> ConeInfo | None:
    row = conn.execute(q.SELECT_CONE, {"cy_id": cy_id}).mappings().first()
    if row is None:
        return None
    return ConeInfo(row["cy_id"], row["autoconer_id"], row["drum_id"], from_db(row["cone_scan_datetime"]))


def _load_cobs(conn, cy_id: str) -> list[CobInfo]:
    return [_cob_from_row(r) for r in conn.execute(q.SELECT_COBS_FOR_CONE, {"cy_id": cy_id}).mappings()]


def _cob_from_row(row) -> CobInfo:
    return CobInfo(row["cob_id"], row["speedframe_id"], row["spindle_id"], from_db(row["cob_scan_datetime"]))


def _classify(id_type: IdType, id_value: str, cone: ConeInfo, cobs: list[CobInfo]) -> TraceResult:
    late = [
        f"COB {c.cob_id} scanned at {to_display(c.cob_scan_datetime)} after Yarn Cone "
        f"{cone.cy_id} scanned at {to_display(cone.cone_scan_datetime)}"
        for c in cobs if c.cob_scan_datetime > cone.cone_scan_datetime
    ]
    if late:
        return TraceResult("INCONSISTENT", id_type, id_value, cone, cobs, late)
    if not cobs:
        return TraceResult("PARTIAL", id_type, id_value, cone, cobs,
                           [f"Yarn Cone {cone.cy_id} has no linked COBs"])
    return TraceResult("FOUND", id_type, id_value, cone, cobs)
```

- [ ] **Step 5: Run the tests and confirm they pass**

Run: `.venv/Scripts/python -m pytest tests/ -v`
Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add database/queries.py services/traceability_service.py tests/test_traceability.py
git commit -m "feat: add central CY/COB traceability service with status rules

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Receive service (validation + transactional save)

**Files:**
- Modify: `database/queries.py` (append a receive section)
- Create: `services/receive_service.py`
- Test: `tests/test_receive.py`

**Interfaces:**
- Consumes: `normalize_id`, `is_valid_id`, `is_future`, `cob_after_cone` (Task 1); `now_local`, `to_db` (Task 1); `audit_service.log` (Task 3); `traceability_service.search_cy` (Task 4, used in tests); `config.SYSTEM_ERROR_MSG`
- Produces (`services.receive_service`):
  - `CobEntry(cob_id: str, speedframe_id: str, spindle_id: str, cob_scan_datetime: datetime | None)`, a dataclass
  - `ReceivePayload(cy_id: str, autoconer_id: str, drum_id: str, cone_scan_datetime: datetime | None, cobs: list[CobEntry])`, a dataclass
  - `ValidationError(field: str, row: int | None, message: str)`, a frozen dataclass. `row` is the 1-based COB row number, or `None` for cone-level errors.
  - `ReceiveRejected(Exception)`, with `.errors: list[ValidationError]`
  - `validate_receive(engine, payload, now: datetime | None = None) -> list[ValidationError]`
  - `save_receive(engine, payload, user_id: int, now: datetime | None = None) -> str`, which returns the `receive_txn_id` or raises `ReceiveRejected`
  - `database.queries`: `EXISTS_CONE`, `EXISTS_COB`, `SELECT_AUTOCONER_ACTIVE`, `SELECT_DRUM_OWNER`, `SELECT_SPEEDFRAME_ACTIVE`, `SELECT_SPINDLE_OWNER`, `INSERT_CONE`, `INSERT_COB`, `INSERT_TRACE`. Task 6 reuses the four `SELECT_*` queries.

- [ ] **Step 1: Write the failing tests** (`tests/test_receive.py`)

```python
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
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `.venv/Scripts/python -m pytest tests/test_receive.py -v`
Expected: fails with `ImportError: cannot import name 'receive_service'`.

- [ ] **Step 3: Append the queries to `database/queries.py`**

```python

# --- receive / master lookups -------------------------------------------------
EXISTS_CONE = text("SELECT 1 FROM yarn_cone WHERE cy_id = :cy_id")
EXISTS_COB = text("SELECT 1 FROM cob WHERE cob_id = :cob_id")
SELECT_AUTOCONER_ACTIVE = text("SELECT is_active FROM autoconer WHERE autoconer_id = :autoconer_id")
SELECT_DRUM_OWNER = text("SELECT autoconer_id FROM drum WHERE drum_id = :drum_id")
SELECT_SPEEDFRAME_ACTIVE = text("SELECT is_active FROM speedframe WHERE speedframe_id = :speedframe_id")
SELECT_SPINDLE_OWNER = text("SELECT speedframe_id FROM spindle WHERE spindle_id = :spindle_id")

INSERT_CONE = text("""
    INSERT INTO yarn_cone (cy_id, drum_id, cone_scan_datetime, receive_txn_id, created_by, created_at)
    VALUES (:cy_id, :drum_id, :cone_scan_datetime, :receive_txn_id, :created_by, :created_at)
""")

INSERT_COB = text("""
    INSERT INTO cob (cob_id, spindle_id, cob_scan_datetime, receive_txn_id, created_by, created_at)
    VALUES (:cob_id, :spindle_id, :cob_scan_datetime, :receive_txn_id, :created_by, :created_at)
""")

INSERT_TRACE = text("""
    INSERT INTO cob_traceability (cy_id, cob_id, receive_txn_id, created_at)
    VALUES (:cy_id, :cob_id, :receive_txn_id, :created_at)
""")
```

- [ ] **Step 4: Implement `services/receive_service.py`**

```python
"""Receive workflow: validate a cone + COBs payload and save it as one transaction."""
import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

import config
from database import queries as q
from services import audit_service
from utils.dates import now_local, to_db
from utils.logger import get_logger
from utils.validators import cob_after_cone, is_future, is_valid_id, normalize_id

logger = get_logger("receive")

DUPLICATE_MSG = ("Could not save: a record already exists or references unknown master data. "
                 "Please re-check and try again.")


@dataclass
class CobEntry:
    cob_id: str
    speedframe_id: str
    spindle_id: str
    cob_scan_datetime: datetime | None


@dataclass
class ReceivePayload:
    cy_id: str
    autoconer_id: str
    drum_id: str
    cone_scan_datetime: datetime | None
    cobs: list[CobEntry]


@dataclass(frozen=True)
class ValidationError:
    field: str
    row: int | None
    message: str


class ReceiveRejected(Exception):
    def __init__(self, errors: list[ValidationError]):
        super().__init__("; ".join(e.message for e in errors))
        self.errors = errors


def validate_receive(engine, payload: ReceivePayload, now: datetime | None = None) -> list[ValidationError]:
    """Check every rule and return all errors (empty list = valid). Never writes."""
    now = now or now_local()
    errors: list[ValidationError] = []
    cy_id = normalize_id(payload.cy_id)
    autoconer_id = normalize_id(payload.autoconer_id)
    drum_id = normalize_id(payload.drum_id)
    cone_dt = payload.cone_scan_datetime

    cy_ok = _check_id(errors, "cy_id", None, "CY", cy_id, "Yarn Cone ID")
    ac_ok = _check_id(errors, "autoconer_id", None, "AUTOCONER", autoconer_id, "Autoconer")
    drum_ok = _check_id(errors, "drum_id", None, "DRUM", drum_id, "Drum")
    _check_time(errors, "cone_scan_datetime", None, cone_dt, "Cone scan time", now)
    if not payload.cobs:
        errors.append(ValidationError("cobs", None, "At least one COB is required"))

    with engine.connect() as conn:
        if cy_ok and conn.execute(q.EXISTS_CONE, {"cy_id": cy_id}).first():
            errors.append(ValidationError("cy_id", None, f"Yarn Cone {cy_id} already exists"))
        if ac_ok and _check_machine(conn, errors, "autoconer_id", None, q.SELECT_AUTOCONER_ACTIVE,
                                    {"autoconer_id": autoconer_id}, f"Autoconer {autoconer_id}") and drum_ok:
            _check_owner(conn, errors, "drum_id", None, q.SELECT_DRUM_OWNER,
                         {"drum_id": drum_id}, f"Drum {drum_id}", autoconer_id)

        seen: set[str] = set()
        for row, cob in enumerate(payload.cobs, start=1):
            cob_id = normalize_id(cob.cob_id)
            speedframe_id = normalize_id(cob.speedframe_id)
            spindle_id = normalize_id(cob.spindle_id)
            if _check_id(errors, "cob_id", row, "COB", cob_id, "COB ID"):
                if cob_id in seen:
                    errors.append(ValidationError("cob_id", row, f"COB {cob_id} is repeated in this form"))
                elif conn.execute(q.EXISTS_COB, {"cob_id": cob_id}).first():
                    errors.append(ValidationError("cob_id", row, f"COB {cob_id} already exists"))
                seen.add(cob_id)
            sf_ok = _check_id(errors, "speedframe_id", row, "SPEEDFRAME", speedframe_id, "Speedframe")
            sp_ok = _check_id(errors, "spindle_id", row, "SPINDLE", spindle_id, "Spindle")
            if sf_ok and _check_machine(conn, errors, "speedframe_id", row, q.SELECT_SPEEDFRAME_ACTIVE,
                                        {"speedframe_id": speedframe_id}, f"Speedframe {speedframe_id}") and sp_ok:
                _check_owner(conn, errors, "spindle_id", row, q.SELECT_SPINDLE_OWNER,
                             {"spindle_id": spindle_id}, f"Spindle {spindle_id}", speedframe_id)
            if (_check_time(errors, "cob_scan_datetime", row, cob.cob_scan_datetime, "COB scan time", now)
                    and cone_dt is not None and cob_after_cone(cob.cob_scan_datetime, cone_dt)):
                errors.append(ValidationError("cob_scan_datetime", row,
                                              "COB scan time must be at or before the cone scan time"))
    return errors


def save_receive(engine, payload: ReceivePayload, user_id: int, now: datetime | None = None) -> str:
    """Validate, then insert cone + COBs + links in one transaction. Returns receive_txn_id."""
    now = now or now_local()
    cy_id = normalize_id(payload.cy_id)
    errors = validate_receive(engine, payload, now)
    if errors:
        _reject(engine, user_id, cy_id, errors)

    txn_id = str(uuid.uuid4())
    created_at = to_db(now)
    try:
        with engine.begin() as conn:
            conn.execute(q.INSERT_CONE, {
                "cy_id": cy_id, "drum_id": normalize_id(payload.drum_id),
                "cone_scan_datetime": to_db(payload.cone_scan_datetime),
                "receive_txn_id": txn_id, "created_by": user_id, "created_at": created_at,
            })
            for cob in payload.cobs:
                conn.execute(q.INSERT_COB, {
                    "cob_id": normalize_id(cob.cob_id), "spindle_id": normalize_id(cob.spindle_id),
                    "cob_scan_datetime": to_db(cob.cob_scan_datetime),
                    "receive_txn_id": txn_id, "created_by": user_id, "created_at": created_at,
                })
            for cob in payload.cobs:
                conn.execute(q.INSERT_TRACE, {
                    "cy_id": cy_id, "cob_id": normalize_id(cob.cob_id),
                    "receive_txn_id": txn_id, "created_at": created_at,
                })
    except IntegrityError:
        logger.warning("Receive integrity failure for %s", cy_id, exc_info=True)
        _reject(engine, user_id, cy_id, [ValidationError("system", None, DUPLICATE_MSG)])
    except SQLAlchemyError:
        logger.exception("Receive save failed for %s", cy_id)
        _reject(engine, user_id, cy_id, [ValidationError("system", None, config.SYSTEM_ERROR_MSG)])

    audit_service.log(engine, user_id, "RECEIVE", "SUCCESS", id_type="CY", id_value=cy_id,
                      detail=f"txn={txn_id}; cobs={len(payload.cobs)}")
    return txn_id


def _reject(engine, user_id: int, cy_id: str, errors: list[ValidationError]) -> None:
    audit_service.log(engine, user_id, "RECEIVE", "FAILED", id_type="CY", id_value=cy_id,
                      detail="; ".join(e.message for e in errors)[:1000])
    raise ReceiveRejected(errors)


def _check_id(errors, field, row, kind, value, label) -> bool:
    if not value:
        errors.append(ValidationError(field, row, f"{label} is required"))
        return False
    if not is_valid_id(kind, value):
        errors.append(ValidationError(field, row, f"{label} '{value}' has an invalid format"))
        return False
    return True


def _check_time(errors, field, row, value, label, now) -> bool:
    if value is None:
        errors.append(ValidationError(field, row, f"{label} is required"))
        return False
    if is_future(value, now):
        errors.append(ValidationError(field, row, f"{label} cannot be in the future"))
        return False
    return True


def _check_machine(conn, errors, field, row, stmt, params, label) -> bool:
    is_active = conn.execute(stmt, params).scalar()
    if is_active is None:
        errors.append(ValidationError(field, row, f"{label} does not exist"))
        return False
    if not is_active:
        errors.append(ValidationError(field, row, f"{label} is inactive"))
        return False
    return True


def _check_owner(conn, errors, field, row, stmt, params, label, expected_parent) -> None:
    owner = conn.execute(stmt, params).scalar()
    if owner is None:
        errors.append(ValidationError(field, row, f"{label} does not exist"))
    elif owner != expected_parent:
        errors.append(ValidationError(field, row, f"{label} belongs to {owner}, not {expected_parent}"))
```

- [ ] **Step 5: Run the tests and confirm they pass**

Run: `.venv/Scripts/python -m pytest tests/ -v`
Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add database/queries.py services/receive_service.py tests/test_receive.py
git commit -m "feat: add receive validation and transactional save

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Auth and master-data services

**Files:**
- Modify: `database/queries.py` (append auth/master section)
- Create: `services/auth_service.py`, `services/master_service.py`
- Test: `tests/test_auth_master.py`

**Interfaces:**
- Consumes: `audit_service.log/recent` (Task 3); `SELECT_AUTOCONER_ACTIVE`, `SELECT_DRUM_OWNER`, `SELECT_SPEEDFRAME_ACTIVE`, `SELECT_SPINDLE_OWNER` (Task 5); `hash_password`, `verify_password` (Task 2); `normalize_id`, `is_valid_id` (Task 1)
- Produces:
  - `services.auth_service.User(user_id: int, username: str, role: str)`, a frozen dataclass
  - `services.auth_service.PAGE_ROLES: dict[str, set[str]]`, keyed by page (`search`, `receive`, `report`, `admin`)
  - `services.auth_service.authenticate(engine, username: str, password: str) -> User | None`
  - `services.auth_service.has_role(user: User | None, page: str) -> bool`
  - `services.master_service.MasterDataError(Exception)` (its message is safe to show users), `ROLES = ("operator", "supervisor", "admin")`, `MIN_PASSWORD_LENGTH = 6`
  - `services.master_service` list functions:
    - `list_autoconers(engine, active_only=True) -> list[dict]`, keys `autoconer_id, machine_name, is_active`
    - `list_drums(engine, autoconer_id=None) -> list[dict]`, keys `drum_id, autoconer_id`
    - `list_speedframes(engine, active_only=True) -> list[dict]`, keys `speedframe_id, machine_name, is_active`
    - `list_spindles(engine, speedframe_id=None) -> list[dict]`, keys `spindle_id, speedframe_id`
    - `list_users(engine) -> list[dict]`, keys `user_id, username, role, status`
  - `services.master_service` write functions, each returning `None` or raising `MasterDataError`:
    - `add_autoconer(engine, admin_id, autoconer_id, machine_name)`
    - `add_drum(engine, admin_id, drum_id, autoconer_id)`
    - `add_speedframe(engine, admin_id, speedframe_id, machine_name)`
    - `add_spindle(engine, admin_id, spindle_id, speedframe_id)`
    - `add_user(engine, admin_id, username, password, role, bcrypt_rounds=config.BCRYPT_ROUNDS)`
    - `disable_user(engine, admin_id, user_id)`

- [ ] **Step 1: Write the failing tests** (`tests/test_auth_master.py`)

```python
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
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `.venv/Scripts/python -m pytest tests/test_auth_master.py -v`
Expected: fails with `ModuleNotFoundError: No module named 'services.auth_service'`.

- [ ] **Step 3: Append the queries to `database/queries.py`**

```python

# --- users / master data ------------------------------------------------------
SELECT_USER_BY_USERNAME = text("""
    SELECT user_id, username, password_hash, role, status FROM users WHERE username = :username
""")
LIST_USERS = text("SELECT user_id, username, role, status FROM users ORDER BY user_id")
INSERT_USER = text("""
    INSERT INTO users (username, password_hash, role) VALUES (:username, :password_hash, :role)
""")
DISABLE_USER = text("UPDATE users SET status = 'disabled' WHERE user_id = :user_id")

LIST_AUTOCONERS = text("""
    SELECT autoconer_id, machine_name, is_active FROM autoconer
    WHERE (:active_only = 0 OR is_active = 1) ORDER BY autoconer_id
""")
LIST_DRUMS = text("""
    SELECT drum_id, autoconer_id FROM drum
    WHERE (:autoconer_id IS NULL OR autoconer_id = :autoconer_id) ORDER BY drum_id
""")
LIST_SPEEDFRAMES = text("""
    SELECT speedframe_id, machine_name, is_active FROM speedframe
    WHERE (:active_only = 0 OR is_active = 1) ORDER BY speedframe_id
""")
LIST_SPINDLES = text("""
    SELECT spindle_id, speedframe_id FROM spindle
    WHERE (:speedframe_id IS NULL OR speedframe_id = :speedframe_id) ORDER BY spindle_id
""")
INSERT_AUTOCONER = text("INSERT INTO autoconer (autoconer_id, machine_name) VALUES (:autoconer_id, :machine_name)")
INSERT_DRUM = text("INSERT INTO drum (drum_id, autoconer_id) VALUES (:drum_id, :autoconer_id)")
INSERT_SPEEDFRAME = text("INSERT INTO speedframe (speedframe_id, machine_name) VALUES (:speedframe_id, :machine_name)")
INSERT_SPINDLE = text("INSERT INTO spindle (spindle_id, speedframe_id) VALUES (:spindle_id, :speedframe_id)")
```

- [ ] **Step 4: Implement `services/auth_service.py`**

```python
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
```

- [ ] **Step 5: Implement `services/master_service.py`**

```python
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
```

- [ ] **Step 6: Run the tests and confirm they pass**

Run: `.venv/Scripts/python -m pytest tests/ -v`
Expected: all tests PASS.

- [ ] **Step 7: Commit**

```bash
git add database/queries.py services/auth_service.py services/master_service.py tests/test_auth_master.py
git commit -m "feat: add login, role matrix and master-data admin services

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Report and export services

**Files:**
- Create: `services/report_service.py`, `services/export_service.py`
- Test: `tests/test_report_export.py`

**Interfaces:**
- Consumes: `get_traceability`, `TraceResult` (Task 4); `audit_service.log/recent` (Task 3); `User` (Task 6); `to_display`, `now_local` (Task 1); `config.APP_NAME/APP_VERSION/REPORT_VERSION`
- Produces:
  - `services.report_service.ReportData(title: str, generated_at: datetime, generated_by: str, reference_no: str, trace: TraceResult)`, a dataclass
  - `services.report_service.generate_report(engine, id_type: str, id_value: str, user: User, now: datetime | None = None) -> ReportData`. It writes a `REPORT` audit row, and `reference_no` is `RPT-<audit_id>`.
  - `services.report_service.trace_chain(trace: TraceResult, arrow: str = "→") -> str`
  - `services.report_service.record_export(engine, user_id: int, report: ReportData, fmt: str) -> None`, which writes an `EXPORT` audit row with `detail` set to `format=<fmt>; ref=<reference_no>`
  - `services.export_service.file_stem(report) -> str`, which returns `traceability_<ID>_<YYYYmmdd_HHMMSS>`
  - `services.export_service.to_csv(report) -> bytes`, `to_excel(report) -> bytes` and `to_pdf(report) -> bytes`
  - `services.export_service.CSV_COLUMNS`, `COB_COLUMNS` and `CONE_COLUMNS`

- [ ] **Step 1: Write the failing tests** (`tests/test_report_export.py`)

```python
import csv
import io
from datetime import datetime

import openpyxl

from services import audit_service
from services import export_service as ex
from services.auth_service import User
from services.report_service import generate_report, record_export, trace_chain
from services.traceability_service import get_traceability

USER = User(3, "supervisor1", "supervisor")
NOW = datetime(2026, 9, 23, 16, 18, 55)


def test_report_matches_search_and_is_audited(engine):
    rpt = generate_report(engine, "CY", "yc006", USER, now=NOW)
    assert rpt.trace == get_traceability(engine, "CY", "YC006")
    assert rpt.title == "Traceability Report - Yarn Cone YC006"
    assert (rpt.generated_by, rpt.generated_at) == ("supervisor1", NOW)
    row = audit_service.recent(engine)[0]
    assert rpt.reference_no == f"RPT-{row['audit_id']}"
    assert (row["action"], row["result"], row["id_value"]) == ("REPORT", "FOUND", "YC006")


def test_trace_chain_text(engine):
    assert trace_chain(get_traceability(engine, "CY", "YC006")) == (
        "YC006 → AC-02 / D025 → COB004 (SF-02/S128), COB005 (SF-02/S129), COB015 (SF-05/S210)"
    )
    assert trace_chain(get_traceability(engine, "CY", "YC006"), arrow="->").startswith("YC006 -> AC-02 / D025 -> ")
    assert trace_chain(get_traceability(engine, "CY", "YC007")) == "YC007 → AC-02 / D026 → no COBs"
    assert trace_chain(get_traceability(engine, "COB", "COB099")) == "COB099 (SF-02/S130) → no Yarn Cone link"
    assert trace_chain(get_traceability(engine, "CY", "YC999")) == "No traceability data"


def test_record_export_is_audited(engine):
    rpt = generate_report(engine, "COB", "COB004", USER, now=NOW)
    record_export(engine, USER.user_id, rpt, "PDF")
    row = audit_service.recent(engine)[0]
    assert (row["action"], row["id_type"], row["id_value"]) == ("EXPORT", "COB", "COB004")
    assert row["detail"] == f"format=PDF; ref={rpt.reference_no}"


def test_file_stem(engine):
    assert ex.file_stem(generate_report(engine, "CY", "YC006", USER, now=NOW)) == "traceability_YC006_20260923_161855"


def test_csv_one_row_per_cob(engine):
    data = ex.to_csv(generate_report(engine, "CY", "YC006", USER, now=NOW))
    rows = list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))
    assert list(rows[0].keys()) == ex.CSV_COLUMNS
    assert [r["COB ID"] for r in rows] == ["COB004", "COB005", "COB015"]
    assert rows[0]["Searched ID"] == "YC006"
    assert rows[0]["Cone Scan Date & Time"] == "20-09-2026 11:12:09"


def test_csv_cone_without_cobs_has_single_row(engine):
    data = ex.to_csv(generate_report(engine, "CY", "YC007", USER, now=NOW))
    rows = list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))
    assert len(rows) == 1
    assert rows[0]["Yarn Cone ID"] == "YC007" and rows[0]["COB ID"] == ""


def test_excel_sheets(engine):
    wb = openpyxl.load_workbook(io.BytesIO(ex.to_excel(generate_report(engine, "CY", "YC006", USER, now=NOW))))
    assert wb.sheetnames == ["Summary", "COBs", "Exceptions"]
    assert wb["COBs"].max_row == 4
    assert wb["COBs"]["B2"].value == "COB004"
    assert wb["Exceptions"]["A2"].value == "None"


def test_pdf_is_generated(engine):
    pdf = ex.to_pdf(generate_report(engine, "CY", "YC008", USER, now=NOW))
    assert pdf.startswith(b"%PDF")
    assert b"YC008" in pdf  # document title metadata
    assert len(pdf) > 1500
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `.venv/Scripts/python -m pytest tests/test_report_export.py -v`
Expected: fails with `ModuleNotFoundError: No module named 'services.export_service'`.

- [ ] **Step 3: Implement `services/report_service.py`**

```python
"""Report dataset preparation. Uses the same traceability service as Search."""
from dataclasses import dataclass
from datetime import datetime

from services import audit_service
from services.auth_service import User
from services.traceability_service import TraceResult, get_traceability
from utils.dates import now_local

ENTITY_LABELS = {"CY": "Yarn Cone", "COB": "COB"}


@dataclass
class ReportData:
    title: str
    generated_at: datetime
    generated_by: str
    reference_no: str
    trace: TraceResult


def generate_report(engine, id_type: str, id_value: str, user: User,
                    now: datetime | None = None) -> ReportData:
    trace = get_traceability(engine, id_type, id_value)
    audit_id = audit_service.log(engine, user.user_id, "REPORT", trace.status,
                                 id_type=trace.searched_type, id_value=trace.searched_id)
    return ReportData(
        title=f"Traceability Report - {ENTITY_LABELS[trace.searched_type]} {trace.searched_id}",
        generated_at=now or now_local(),
        generated_by=user.username,
        reference_no=f"RPT-{audit_id}" if audit_id is not None else "RPT-UNLOGGED",
        trace=trace,
    )


def trace_chain(trace: TraceResult, arrow: str = "→") -> str:
    cobs = ", ".join(f"{c.cob_id} ({c.speedframe_id}/{c.spindle_id})" for c in trace.cobs)
    if trace.cone:
        cone = trace.cone
        return f"{cone.cy_id} {arrow} {cone.autoconer_id} / {cone.drum_id} {arrow} {cobs or 'no COBs'}"
    if trace.cobs:
        return f"{cobs} {arrow} no Yarn Cone link"
    return "No traceability data"


def record_export(engine, user_id: int, report: ReportData, fmt: str) -> None:
    audit_service.log(engine, user_id, "EXPORT", "SUCCESS",
                      id_type=report.trace.searched_type, id_value=report.trace.searched_id,
                      detail=f"format={fmt}; ref={report.reference_no}")
```

- [ ] **Step 4: Implement `services/export_service.py`**

```python
"""PDF, Excel and CSV generation. Every function returns bytes for st.download_button."""
import io
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

import config
from services.report_service import ReportData, trace_chain
from services.traceability_service import TraceResult
from utils.dates import to_display

CONE_COLUMNS = ["Yarn Cone ID", "Autoconer", "Drum", "Cone Scan Date & Time"]
COB_COLUMNS = ["COB ID", "Speedframe", "Spindle", "COB Scan Date & Time"]
CSV_COLUMNS = ["Searched Type", "Searched ID", "Status", *CONE_COLUMNS, *COB_COLUMNS]
HEADER_FILL = colors.HexColor("#dbe7f6")


def file_stem(report: ReportData) -> str:
    return f"traceability_{report.trace.searched_id}_{report.generated_at:%Y%m%d_%H%M%S}"


def _cone_values(trace: TraceResult) -> list[str]:
    c = trace.cone
    return [c.cy_id, c.autoconer_id, c.drum_id, to_display(c.cone_scan_datetime)] if c else [""] * 4


def _cob_rows(trace: TraceResult) -> list[list[str]]:
    return [[c.cob_id, c.speedframe_id, c.spindle_id, to_display(c.cob_scan_datetime)] for c in trace.cobs]


def _header_pairs(report: ReportData) -> list[tuple[str, str]]:
    t = report.trace
    return [
        ("Searched", f"{t.searched_type} {t.searched_id}"),
        ("Status", t.status),
        ("Generated At", to_display(report.generated_at)),
        ("Generated By", report.generated_by),
        ("Reference No", report.reference_no),
    ]


# --- CSV -------------------------------------------------------------------------
def to_csv(report: ReportData) -> bytes:
    t = report.trace
    lead = [t.searched_type, t.searched_id, t.status, *_cone_values(t)]
    rows = [lead + cob for cob in _cob_rows(t)] or [lead + [""] * len(COB_COLUMNS)]
    return pd.DataFrame(rows, columns=CSV_COLUMNS).to_csv(index=False).encode("utf-8-sig")


# --- Excel -----------------------------------------------------------------------
def to_excel(report: ReportData) -> bytes:
    t = report.trace
    summary = [("Report Title", report.title), *_header_pairs(report),
               *zip(CONE_COLUMNS, _cone_values(t)),
               ("Traceability", trace_chain(t)),
               ("System", f"{config.APP_NAME} v{config.APP_VERSION}"),
               ("Report Version", config.REPORT_VERSION)]
    cobs = [[i, *row] for i, row in enumerate(_cob_rows(t), start=1)]
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame(summary, columns=["Field", "Value"]).to_excel(writer, sheet_name="Summary", index=False)
        pd.DataFrame(cobs, columns=["Sl. No.", *COB_COLUMNS]).to_excel(writer, sheet_name="COBs", index=False)
        pd.DataFrame({"Exception": t.exceptions or ["None"]}).to_excel(writer, sheet_name="Exceptions", index=False)
    return buffer.getvalue()


# --- PDF -------------------------------------------------------------------------
def _table(data: list[list[str]], header_row: bool) -> Table:
    table = Table(data, hAlign="LEFT")
    style = [("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
             ("FONTSIZE", (0, 0), (-1, -1), 9),
             ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]
    if header_row:
        style += [("BACKGROUND", (0, 0), (-1, 0), HEADER_FILL), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")]
    else:
        style += [("BACKGROUND", (0, 0), (0, -1), HEADER_FILL), ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold")]
    table.setStyle(TableStyle(style))
    return table


def to_pdf(report: ReportData) -> bytes:
    t = report.trace
    styles = getSampleStyleSheet()
    body, h2 = styles["BodyText"], styles["Heading2"]
    story = [Paragraph(escape(report.title), styles["Title"]),
             _table([list(p) for p in _header_pairs(report)], header_row=False),
             Spacer(1, 6 * mm),
             Paragraph("Cone Information", h2)]
    story.append(_table([CONE_COLUMNS, _cone_values(t)], header_row=True) if t.cone
                 else Paragraph("No linked Yarn Cone.", body))
    story.append(Paragraph("COB Information", h2))
    story.append(_table([["Sl. No.", *COB_COLUMNS]] + [[str(i), *r] for i, r in enumerate(_cob_rows(t), start=1)],
                        header_row=True) if t.cobs else Paragraph("No COBs.", body))
    story.append(Paragraph("Traceability", h2))
    story.append(Paragraph(escape(trace_chain(t, arrow="->")), body))  # Helvetica has no "→" glyph
    story.append(Paragraph("Exceptions", h2))
    story.extend(Paragraph("• " + escape(e), body) for e in t.exceptions)
    if not t.exceptions:
        story.append(Paragraph("None", body))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.drawString(15 * mm, 10 * mm,
                          f"{config.APP_NAME} | Report v{config.REPORT_VERSION} | Ref {report.reference_no}")
        canvas.drawRightString(A4[0] - 15 * mm, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title=report.title, author=report.generated_by,
                            leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm, bottomMargin=20 * mm)
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
```

- [ ] **Step 5: Run the tests and confirm they pass**

Run: `.venv/Scripts/python -m pytest tests/ -v`
Expected: all tests PASS. If `test_pdf_is_generated` fails only on `b"YC008" in pdf`, open the PDF bytes and find how the Info `/Title` is encoded. Change the assertion to match that encoding and leave the implementation alone. Do not weaken the other assertions.

- [ ] **Step 6: Commit**

```bash
git add services/report_service.py services/export_service.py tests/test_report_export.py
git commit -m "feat: add report dataset and PDF/Excel/CSV exports

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: App shell: login, navigation, shared result view, Search page

**Files:**
- Create: `ui/__init__.py` (empty), `ui/graph.py`, `ui/components.py`, `ui/login.py`, `ui/search.py`
- Create: `app.py`
- Test: `tests/test_graph.py`

**Interfaces:**
- Consumes: `get_engine`, `is_initialized` (Task 2); `traceability_service.search`, `TraceResult`, `get_traceability` (Task 4); `authenticate`, `has_role`, `User` (Task 6); `to_display`, `normalize_id` (Task 1)
- Produces:
  - `ui.graph.build_dot(trace: TraceResult, highlight_cob: str | None = None) -> str`, `HIGHLIGHT_FILL = "#ffd54f"`
  - `ui.components.require_role(page: str) -> User`, which stops the page when access is denied
  - `ui.components.render_trace_result(trace: TraceResult, highlight_cob: str | None = None) -> None`
  - `ui.components.ID_TYPE_LABELS = {"CY": "Yarn Cone ID", "COB": "COB ID"}`
  - `ui.login.render()`, `ui.search.render()`
  - `app.PAGES`: a list of `(key, title, icon, render_fn)`. Tasks 9 and 10 append to it.

- [ ] **Step 1: Write the failing tests** (`tests/test_graph.py`)

```python
from services.traceability_service import get_traceability
from ui.graph import HIGHLIGHT_FILL, build_dot


def test_dot_has_cone_and_one_edge_per_cob(engine):
    dot = build_dot(get_traceability(engine, "CY", "YC006"))
    assert dot.startswith("digraph")
    assert "Yarn Cone: YC006" in dot and "Autoconer: AC-02" in dot and "Drum: D025" in dot
    assert dot.count("cone -> cob") == 3
    assert HIGHLIGHT_FILL not in dot


def test_dot_highlights_searched_cob(engine):
    dot = build_dot(get_traceability(engine, "COB", "COB005"), highlight_cob="COB005")
    highlighted = [line for line in dot.splitlines() if HIGHLIGHT_FILL in line]
    assert len(highlighted) == 1 and "COB005" in highlighted[0]


def test_dot_for_orphan_cob_has_no_edges(engine):
    dot = build_dot(get_traceability(engine, "COB", "COB099"), highlight_cob="COB099")
    assert "->" not in dot and "COB099" in dot
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `.venv/Scripts/python -m pytest tests/test_graph.py -v`
Expected: fails with `ModuleNotFoundError: No module named 'ui'`.

- [ ] **Step 3: Implement `ui/graph.py`** (pure; no Streamlit import)

```python
"""Graphviz DOT for the traceability flow (Yarn Cone -> COBs), rendered by st.graphviz_chart."""
from services.traceability_service import TraceResult
from utils.dates import to_display

CONE_FILL = "#d7e6fb"
COB_FILL = "#f3f6fa"
HIGHLIGHT_FILL = "#ffd54f"


def build_dot(trace: TraceResult, highlight_cob: str | None = None) -> str:
    lines = [
        "digraph trace {",
        "  rankdir=TB;",
        '  node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=10];',
    ]
    if trace.cone:
        c = trace.cone
        lines.append(
            f'  cone [label="Yarn Cone: {c.cy_id}\\nAutoconer: {c.autoconer_id}\\nDrum: {c.drum_id}'
            f'\\n{to_display(c.cone_scan_datetime)}", fillcolor="{CONE_FILL}"];'
        )
    for i, cob in enumerate(trace.cobs):
        fill = HIGHLIGHT_FILL if cob.cob_id == highlight_cob else COB_FILL
        lines.append(
            f'  cob{i} [label="{cob.cob_id}\\nSpeedframe: {cob.speedframe_id}\\nSpindle: {cob.spindle_id}'
            f'\\n{to_display(cob.cob_scan_datetime)}", fillcolor="{fill}"];'
        )
        if trace.cone:
            lines.append(f"  cone -> cob{i};")
    lines.append("}")
    return "\n".join(lines)
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `.venv/Scripts/python -m pytest tests/test_graph.py -v`
Expected: PASS.

- [ ] **Step 5: Implement `ui/components.py`**

```python
"""Shared Streamlit pieces: page role guard and the traceability result view."""
import pandas as pd
import streamlit as st

from services.auth_service import User, has_role
from services.traceability_service import TraceResult
from ui.graph import build_dot
from utils.dates import to_display

ID_TYPE_LABELS = {"CY": "Yarn Cone ID", "COB": "COB ID"}
STATUS_BADGES = {
    "FOUND": ("Found", "green"),
    "PARTIAL": ("Partial", "orange"),
    "INCONSISTENT": ("Data Inconsistency", "red"),
    "NOT_FOUND": ("Not Found", "gray"),
    "ERROR": ("Error", "red"),
}
COB_TABLE_COLUMNS = ["Sl. No.", "COB ID", "Speedframe", "Spindle", "COB Scan Date & Time"]


def require_role(page: str) -> User:
    user = st.session_state.get("user")
    if not has_role(user, page):
        st.error("You do not have access to this page.")
        st.stop()
    return user


def _cob_table(trace: TraceResult) -> pd.DataFrame:
    rows = [[i, c.cob_id, c.speedframe_id, c.spindle_id, to_display(c.cob_scan_datetime)]
            for i, c in enumerate(trace.cobs, start=1)]
    return pd.DataFrame(rows, columns=COB_TABLE_COLUMNS)


def _highlighter(cob_id: str | None):
    def style(row):
        colour = "background-color: rgba(255, 193, 7, 0.35)" if row["COB ID"] == cob_id else ""
        return [colour] * len(row)
    return style


def render_trace_result(trace: TraceResult, highlight_cob: str | None = None) -> None:
    label, colour = STATUS_BADGES[trace.status]
    st.markdown(f"Status: :{colour}-background[**{label}**]")
    if trace.status == "NOT_FOUND":
        st.info(f"No record found for {ID_TYPE_LABELS[trace.searched_type]} {trace.searched_id}.")
        return
    if trace.status == "ERROR":
        st.error(trace.exceptions[0])
        return

    left, right = st.columns([3, 2], gap="large")
    with left:
        if trace.cone:
            cone = trace.cone
            st.subheader(f"Traceability result for Yarn Cone: {cone.cy_id}")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Yarn Cone ID", cone.cy_id)
            c2.metric("Produced in Autoconer", cone.autoconer_id)
            c3.metric("Drum ID", cone.drum_id)
            c4.metric("Cone Scan Date & Time", to_display(cone.cone_scan_datetime))
            st.markdown("**COBs used for this Yarn Cone**")
        else:
            st.subheader("No linked Yarn Cone")
            st.markdown("**COB**")
        table = _cob_table(trace)
        if table.empty:
            st.caption("No COBs linked.")
        else:
            st.dataframe(table.style.apply(_highlighter(highlight_cob), axis=1), hide_index=True)
    with right:
        st.markdown("**Traceability flow**")
        st.graphviz_chart(build_dot(trace, highlight_cob))

    if trace.exceptions:
        st.warning("**Exceptions**\n\n" + "\n".join(f"- {e}" for e in trace.exceptions))
```

- [ ] **Step 6: Implement `ui/login.py` and `ui/search.py`**

`ui/login.py`:
```python
"""Login page."""
import streamlit as st

import config
from database.database import get_engine
from services.auth_service import authenticate


def render() -> None:
    st.title(config.APP_NAME)
    _, middle, _ = st.columns([1, 1, 1])
    with middle:
        with st.form("login"):
            st.subheader("Sign in")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log in", type="primary")
        if submitted:
            user = authenticate(get_engine(), username, password)
            if user is None:
                st.error("Invalid username or password, or the account is disabled.")
            else:
                st.session_state.user = user
                st.rerun()
```

`ui/search.py`:
```python
"""SEARCH module: look up a Yarn Cone or COB and show its full traceability."""
import streamlit as st

from database.database import get_engine
from services import traceability_service
from ui.components import ID_TYPE_LABELS, render_trace_result, require_role
from utils.validators import normalize_id


def _clear() -> None:
    st.session_state.pop("search_result", None)
    st.session_state["search_id"] = ""


def render() -> None:
    user = require_role("search")
    st.header("Search")
    with st.form("search_form"):
        id_type = st.radio("Search by", list(ID_TYPE_LABELS), format_func=ID_TYPE_LABELS.get,
                           horizontal=True, key="search_type")
        id_value = st.text_input("ID", placeholder="e.g. YC006 or COB004", key="search_id")
        c1, c2, _ = st.columns([1, 1, 6])
        submitted = c1.form_submit_button("Search", type="primary")
        c2.form_submit_button("Clear", on_click=_clear)

    if submitted:
        if not normalize_id(id_value):
            st.warning("Enter an ID to search.")
        else:
            st.session_state.search_result = traceability_service.search(
                get_engine(), user.user_id, id_type, id_value)

    result = st.session_state.get("search_result")
    if result is not None:
        render_trace_result(result, highlight_cob=result.searched_id if result.searched_type == "COB" else None)
```

- [ ] **Step 7: Implement `app.py`**

```python
"""Streamlit entry point: login gate and role-based navigation.  Run: streamlit run app.py"""
import streamlit as st

import config
from database.database import get_engine, is_initialized
from services.auth_service import has_role
from ui import login, search

st.set_page_config(page_title="Yarn Traceability", page_icon="🧵", layout="wide")

# (page key, title, icon, render function). Order = sidebar order; the first allowed page is the landing page.
PAGES = [
    ("search", "Search", ":material/search:", search.render),
]


def _logout() -> None:
    st.session_state.clear()


def main() -> None:
    if not is_initialized(get_engine()):
        st.error("Database is not initialized. Run `python scripts/init_db.py`, then reload this page.")
        st.stop()

    user = st.session_state.get("user")
    if user is None:
        st.navigation([st.Page(login.render, title="Login", url_path="login")], position="hidden").run()
        return

    allowed = [p for p in PAGES if has_role(user, p[0])]
    pages = [st.Page(fn, title=title, icon=icon, url_path=key, default=(i == 0))
             for i, (key, title, icon, fn) in enumerate(allowed)]
    with st.sidebar:
        st.markdown(f"**{config.APP_NAME}**")
        st.caption(f"Signed in as **{user.username}** ({user.role})")
        st.button("Log out", on_click=_logout)
    st.navigation(pages).run()


main()
```

- [ ] **Step 8: Check the full test suite and run a startup smoke test**

Run: `.venv/Scripts/python -m pytest tests/ -v`
Expected: all tests PASS.

Run `.venv/Scripts/python -m streamlit run app.py --server.headless true --server.port 8599` in the background, then `curl -s http://localhost:8599/_stcore/health`.
Expected: `ok`. Stop the server afterwards.

Manual check for the human reviewer: open http://localhost:8599 and log in as `operator1` / `operator123`.
- Search `YC006`: the status is Found, the cone card shows AC-02 / D025 / 20-09-2026 11:12:09, and the table and diagram show three COBs.
- Search COB `COB005`: the same cone appears and the COB005 row is highlighted.
- Search `YC007`: Partial. `YC008`: Data Inconsistency. `COB099`: Partial. `YC999`: Not Found.
- Click Clear: the input and the result are both cleared.

- [ ] **Step 9: Commit**

```bash
git add ui/ app.py tests/test_graph.py
git commit -m "feat: add login, navigation, shared result view and Search page

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Receive page

**Files:**
- Create: `ui/receive.py`
- Modify: `app.py` (import `receive` and add a `PAGES` entry)
- Test: `tests/test_receive_grid.py`

**Interfaces:**
- Consumes: `CobEntry`, `ReceivePayload`, `ReceiveRejected`, `ValidationError`, `save_receive` (Task 5); `list_autoconers`, `list_drums`, `list_speedframes`, `list_spindles` (Task 6); `require_role` (Task 8); `now_local` (Task 1)
- Produces:
  - `ui.receive.GRID_COLUMNS = ["COB ID", "Speedframe", "Spindle", "Scan date & time"]`
  - `ui.receive.grid_to_entries(df: pd.DataFrame) -> list[CobEntry]`, which skips fully blank rows and turns NaN/NaT into `""`/`None`
  - `ui.receive.format_errors(errors: list[ValidationError]) -> str`, which produces markdown bullets
  - `ui.receive.render()`

- [ ] **Step 1: Write the failing tests** (`tests/test_receive_grid.py`)

```python
from datetime import datetime

import pandas as pd

from services.receive_service import CobEntry, ValidationError
from ui.receive import GRID_COLUMNS, format_errors, grid_to_entries


def test_grid_to_entries_skips_blank_rows_and_converts_times():
    df = pd.DataFrame({
        "COB ID": ["cob900", None],
        "Speedframe": ["SF-01", None],
        "Spindle": ["S101", None],
        "Scan date & time": [pd.Timestamp("2026-09-23 10:00:00.5"), pd.NaT],
    }, columns=GRID_COLUMNS)
    assert grid_to_entries(df) == [CobEntry("cob900", "SF-01", "S101", datetime(2026, 9, 23, 10, 0, 0))]


def test_grid_row_without_time_or_spindle():
    df = pd.DataFrame({"COB ID": ["COB900"], "Speedframe": ["SF-01"], "Spindle": [None],
                       "Scan date & time": [pd.NaT]}, columns=GRID_COLUMNS)
    assert grid_to_entries(df) == [CobEntry("COB900", "SF-01", "", None)]


def test_format_errors_groups_cone_and_rows():
    text = format_errors([
        ValidationError("cy_id", None, "Yarn Cone ID is required"),
        ValidationError("spindle_id", 2, "Spindle S210 belongs to SF-05, not SF-01"),
    ])
    assert text == ("- **Yarn Cone:** Yarn Cone ID is required\n"
                    "- **COB row 2:** Spindle S210 belongs to SF-05, not SF-01")
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `.venv/Scripts/python -m pytest tests/test_receive_grid.py -v`
Expected: fails with `ModuleNotFoundError: No module named 'ui.receive'`.

- [ ] **Step 3: Implement `ui/receive.py`**

```python
"""RECEIVE module: capture a Yarn Cone and its COBs, validate, and save in one transaction."""
from datetime import datetime

import pandas as pd
import streamlit as st

from database.database import get_engine
from services import master_service, receive_service
from services.receive_service import CobEntry, ReceivePayload, ReceiveRejected, ValidationError
from ui.components import require_role
from utils.dates import now_local
from utils.validators import normalize_id

GRID_COLUMNS = ["COB ID", "Speedframe", "Spindle", "Scan date & time"]


def grid_to_entries(df: pd.DataFrame) -> list[CobEntry]:
    entries = []
    for record in df.to_dict("records"):
        values = {k: (None if pd.isna(v) else v) for k, v in record.items()}
        if all(v in (None, "") for v in values.values()):
            continue
        ts = values.get("Scan date & time")
        entries.append(CobEntry(
            cob_id=str(values.get("COB ID") or ""),
            speedframe_id=str(values.get("Speedframe") or ""),
            spindle_id=str(values.get("Spindle") or ""),
            cob_scan_datetime=pd.Timestamp(ts).to_pydatetime().replace(microsecond=0) if ts is not None else None,
        ))
    return entries


def format_errors(errors: list[ValidationError]) -> str:
    return "\n".join(
        f"- **{'Yarn Cone' if e.row is None else f'COB row {e.row}'}:** {e.message}" for e in errors
    )


def _key(name: str) -> str:
    # Bumping receive_form_id after a successful save gives every widget a fresh key, i.e. a clean form.
    return f"{name}_{st.session_state.setdefault('receive_form_id', 0)}"


def render() -> None:
    user = require_role("receive")
    engine = get_engine()
    st.header("Receive")
    if "receive_success" in st.session_state:
        st.success(st.session_state.pop("receive_success"))

    now = now_local()
    autoconers = [a["autoconer_id"] for a in master_service.list_autoconers(engine)]
    speedframes = [s["speedframe_id"] for s in master_service.list_speedframes(engine)]
    spindles = [s["spindle_id"] for s in master_service.list_spindles(engine)]

    st.subheader("Yarn Cone")
    c1, c2, c3 = st.columns(3)
    cy_id = c1.text_input("Yarn Cone ID", placeholder="YC006", key=_key("cy"))
    autoconer = c2.selectbox("Autoconer", autoconers, index=None, placeholder="Select autoconer", key=_key("ac"))
    drums = [d["drum_id"] for d in master_service.list_drums(engine, autoconer)] if autoconer else []
    drum = c3.selectbox("Drum", drums, index=None, placeholder="Select drum", key=_key("drum"),
                        disabled=autoconer is None)
    d1, d2, _ = st.columns(3)
    cone_date = d1.date_input("Cone scan date", value=now.date(), format="DD-MM-YYYY", key=_key("date"))
    cone_time = d2.time_input("Cone scan time", value=now.time(), step=60, key=_key("time"))

    st.subheader("COBs")
    empty = pd.DataFrame({
        "COB ID": pd.Series(dtype="object"), "Speedframe": pd.Series(dtype="object"),
        "Spindle": pd.Series(dtype="object"), "Scan date & time": pd.Series(dtype="datetime64[ns]"),
    }, columns=GRID_COLUMNS)
    grid = st.data_editor(
        empty, num_rows="dynamic", key=_key("cobs"), hide_index=True,
        column_config={
            "COB ID": st.column_config.TextColumn(required=True),
            "Speedframe": st.column_config.SelectboxColumn(options=speedframes, required=True),
            "Spindle": st.column_config.SelectboxColumn(options=spindles, required=True),
            "Scan date & time": st.column_config.DatetimeColumn(format="DD-MM-YYYY HH:mm:ss", step=1,
                                                                required=True),
        },
    )

    if st.button("Validate & Save", type="primary"):
        payload = ReceivePayload(
            cy_id=cy_id, autoconer_id=autoconer or "", drum_id=drum or "",
            cone_scan_datetime=datetime.combine(cone_date, cone_time).replace(microsecond=0),
            cobs=grid_to_entries(grid),
        )
        try:
            txn_id = receive_service.save_receive(engine, payload, user.user_id)
        except ReceiveRejected as rejected:
            st.error("Nothing was saved. Please fix the following:\n\n" + format_errors(rejected.errors))
        else:
            st.session_state.receive_success = (
                f"Saved Yarn Cone {normalize_id(cy_id)} with {len(payload.cobs)} COB(s). "
                f"Transaction ID: {txn_id}")
            st.session_state.receive_form_id += 1
            st.rerun()
```

- [ ] **Step 4: Register the page in `app.py`**

Change the import line `from ui import login, search` to:
```python
from ui import login, receive, search
```
Then change `PAGES` to:
```python
PAGES = [
    ("search", "Search", ":material/search:", search.render),
    ("receive", "Receive", ":material/add_box:", receive.render),
]
```

- [ ] **Step 5: Run the tests and confirm they pass**

Run: `.venv/Scripts/python -m pytest tests/ -v`
Expected: all tests PASS.

Manual check for the human reviewer: start the app as in Task 8 and log in as `operator1`.
- Receive YC901 on AC-01 / D011 with two COB rows: COB901 on SF-01/S101, and COB902 on SF-02/S128. Both times must be earlier than the cone time. Expected: a success message with a transaction ID, and the form clears.
- Search YC901: Found, with two COBs.
- Save YC901 again: "Yarn Cone YC901 already exists".
- Save a row with SF-01 and spindle S210: the error reads "Spindle S210 belongs to SF-05, not SF-01".
- The Receive page is visible to operator1 but not to supervisor1.

- [ ] **Step 6: Commit**

```bash
git add ui/receive.py app.py tests/test_receive_grid.py
git commit -m "feat: add Receive page with COB grid and per-row validation errors

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Report and Admin pages

**Files:**
- Create: `ui/report.py`, `ui/admin.py`
- Modify: `app.py` (imports and two `PAGES` entries)

**Interfaces:**
- Consumes: `generate_report`, `record_export`, `trace_chain`, `ReportData` (Task 7); `to_pdf`, `to_excel`, `to_csv`, `file_stem` (Task 7); `audit_service.recent`, `audit_service.ACTIONS` (Task 3); every `master_service` function, `MasterDataError` and `ROLES` (Task 6); `require_role`, `render_trace_result`, `ID_TYPE_LABELS` (Task 8)
- Produces: `ui.report.render()`, `ui.admin.render()`

There are no new automated tests. Every function these pages call is already tested in Tasks 3, 6 and 7, and the pages themselves are verified manually below.

- [ ] **Step 1: Implement `ui/report.py`**

```python
"""REPORT module: full traceability report for a CY or COB ID, with PDF/Excel/CSV download."""
import streamlit as st

from database.database import get_engine
from services import export_service, report_service
from ui.components import ID_TYPE_LABELS, render_trace_result, require_role
from utils.dates import to_display
from utils.validators import normalize_id

FORMATS = [
    ("PDF", "pdf", "application/pdf", export_service.to_pdf),
    ("Excel", "xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", export_service.to_excel),
    ("CSV", "csv", "text/csv", export_service.to_csv),
]


def render() -> None:
    user = require_role("report")
    engine = get_engine()
    st.header("Report")
    with st.form("report_form"):
        id_type = st.radio("Report for", list(ID_TYPE_LABELS), format_func=ID_TYPE_LABELS.get, horizontal=True)
        id_value = st.text_input("ID", placeholder="e.g. YC006 or COB004")
        generate = st.form_submit_button("Generate report", type="primary")

    if generate:
        if not normalize_id(id_value):
            st.warning("Enter an ID to report on.")
        else:
            st.session_state.report = report_service.generate_report(engine, id_type, id_value, user)

    report = st.session_state.get("report")
    if report is None:
        return
    trace = report.trace
    st.subheader(report.title)
    st.caption(f"{report.reference_no} · Generated {to_display(report.generated_at)} by {report.generated_by}")
    render_trace_result(trace, highlight_cob=trace.searched_id if trace.searched_type == "COB" else None)
    if trace.status in ("NOT_FOUND", "ERROR"):
        return
    st.markdown(f"**Traceability:** {report_service.trace_chain(trace)}")

    stem = export_service.file_stem(report)
    for column, (label, ext, mime, build) in zip(st.columns(len(FORMATS)), FORMATS):
        column.download_button(
            f"Download {label}", data=build(report), file_name=f"{stem}.{ext}", mime=mime,
            on_click=report_service.record_export, args=(engine, user.user_id, report, label),
        )
```

- [ ] **Step 2: Implement `ui/admin.py`**

```python
"""Admin: machine masters, users and the audit log."""
import pandas as pd
import streamlit as st

from database.database import get_engine
from services import audit_service, master_service
from services.master_service import ROLES, MasterDataError
from ui.components import require_role


def _attempt(action, success_message: str) -> None:
    try:
        action()
    except MasterDataError as error:
        st.error(str(error))
    else:
        st.success(success_message)


def render() -> None:
    user = require_role("admin")
    engine = get_engine()
    st.header("Admin")
    machines_tab, users_tab, audit_tab = st.tabs(["Machines", "Users", "Audit Log"])
    with machines_tab:
        _machines(engine, user.user_id)
    with users_tab:
        _users(engine, user.user_id)
    with audit_tab:
        _audit(engine)


def _machines(engine, admin_id: int) -> None:
    left, right = st.columns(2)
    with left:
        with st.form("add_autoconer", clear_on_submit=True):
            st.markdown("**Add Autoconer**")
            autoconer_id = st.text_input("Autoconer ID", placeholder="AC-04")
            name = st.text_input("Machine name", key="ac_name")
            if st.form_submit_button("Add Autoconer"):
                _attempt(lambda: master_service.add_autoconer(engine, admin_id, autoconer_id, name),
                         f"Autoconer {autoconer_id.strip().upper()} added")
        with st.form("add_drum", clear_on_submit=True):
            st.markdown("**Add Drum**")
            drum_id = st.text_input("Drum ID", placeholder="D041")
            parent = st.selectbox("Autoconer", [a["autoconer_id"] for a in
                                                master_service.list_autoconers(engine, active_only=False)])
            if st.form_submit_button("Add Drum"):
                _attempt(lambda: master_service.add_drum(engine, admin_id, drum_id, parent),
                         f"Drum {drum_id.strip().upper()} added")
    with right:
        with st.form("add_speedframe", clear_on_submit=True):
            st.markdown("**Add Speedframe**")
            speedframe_id = st.text_input("Speedframe ID", placeholder="SF-06")
            sf_name = st.text_input("Machine name", key="sf_name")
            if st.form_submit_button("Add Speedframe"):
                _attempt(lambda: master_service.add_speedframe(engine, admin_id, speedframe_id, sf_name),
                         f"Speedframe {speedframe_id.strip().upper()} added")
        with st.form("add_spindle", clear_on_submit=True):
            st.markdown("**Add Spindle**")
            spindle_id = st.text_input("Spindle ID", placeholder="S301")
            sf_parent = st.selectbox("Speedframe", [s["speedframe_id"] for s in
                                                    master_service.list_speedframes(engine, active_only=False)])
            if st.form_submit_button("Add Spindle"):
                _attempt(lambda: master_service.add_spindle(engine, admin_id, spindle_id, sf_parent),
                         f"Spindle {spindle_id.strip().upper()} added")

    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    for column, title, rows in [
        (c1, "Autoconers", master_service.list_autoconers(engine, active_only=False)),
        (c2, "Drums", master_service.list_drums(engine)),
        (c3, "Speedframes", master_service.list_speedframes(engine, active_only=False)),
        (c4, "Spindles", master_service.list_spindles(engine)),
    ]:
        column.markdown(f"**{title}**")
        column.dataframe(pd.DataFrame(rows), hide_index=True)


def _users(engine, admin_id: int) -> None:
    left, right = st.columns(2)
    with left:
        with st.form("add_user", clear_on_submit=True):
            st.markdown("**Add User**")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            role = st.selectbox("Role", ROLES)
            if st.form_submit_button("Add User"):
                _attempt(lambda: master_service.add_user(engine, admin_id, username, password, role),
                         f"User {username.strip()} added")
    with right:
        candidates = [u for u in master_service.list_users(engine)
                      if u["status"] == "active" and u["user_id"] != admin_id]
        with st.form("disable_user"):
            st.markdown("**Disable User**")
            target = st.selectbox("User", candidates, format_func=lambda u: f"{u['username']} ({u['role']})")
            if st.form_submit_button("Disable", disabled=not candidates) and target:
                _attempt(lambda: master_service.disable_user(engine, admin_id, target["user_id"]),
                         f"User {target['username']} disabled")
    st.dataframe(pd.DataFrame(master_service.list_users(engine)), hide_index=True)


def _audit(engine) -> None:
    action = st.selectbox("Action", ["All", *audit_service.ACTIONS])
    rows = audit_service.recent(engine, limit=200, action=None if action == "All" else action)
    st.dataframe(pd.DataFrame(rows), hide_index=True)
```

- [ ] **Step 3: Register both pages in `app.py`**

Change the import line to:
```python
from ui import admin, login, receive, report, search
```
Then change `PAGES` to:
```python
PAGES = [
    ("search", "Search", ":material/search:", search.render),
    ("receive", "Receive", ":material/add_box:", receive.render),
    ("report", "Report", ":material/description:", report.render),
    ("admin", "Admin", ":material/settings:", admin.render),
]
```

- [ ] **Step 4: Check the full suite and run the manual checks**

Run: `.venv/Scripts/python -m pytest tests/ -v`
Expected: all tests PASS.

Manual check for the human reviewer: start the app.
- As `supervisor1` / `supervisor123`: the sidebar shows Search and Report only. Report on YC006 shows the result and a reference number `RPT-n`. Download the PDF, Excel and CSV files and open each one. The PDF footer shows the system name, `Report v1.0` and the reference number. Report on YC008: the exceptions are listed in the PDF.
- As `admin` / `admin123`: all four pages appear.
  - Add AC-04 and then D041. D041 then appears in the Receive drum dropdown when AC-04 is selected.
  - Add user `operator2`, disable them, and confirm the login fails.
  - The Audit Log tab shows LOGIN, SEARCH, RECEIVE, REPORT, EXPORT and ADMIN rows.

- [ ] **Step 5: Commit**

```bash
git add ui/report.py ui/admin.py app.py
git commit -m "feat: add Report page with PDF/Excel/CSV downloads and Admin page

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: README, final verification and publish

**Files:**
- Create: `README.md`

**Interfaces:**
- Consumes: everything above
- Produces: setup and demo documentation

- [ ] **Step 1: Write `README.md`**

````markdown
# Yarn Cone / COB Traceability Dashboard

A Streamlit + SQLite application for Yarn Cone (YC) and COB traceability. It has three modules:
**Search**, **Receive** and **Report**. There is also an Admin page for machine masters, users and the audit log.

Traceability chain: Yarn Cone → Autoconer / Drum → COBs → Spindle / Speedframe.

## Setup (Windows)

```bash
cd yarn_traceability
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
copy .env.example .env            # optional; the defaults work as-is
.venv/Scripts/python scripts/init_db.py          # add --reset to recreate the demo database
.venv/Scripts/python -m streamlit run app.py
```

## Demo accounts

| Username | Password | Role | Pages |
|---|---|---|---|
| operator1 | operator123 | operator | Search, Receive |
| supervisor1 | supervisor123 | supervisor | Search, Report |
| admin | admin123 | admin | all |

These are demo credentials only. Change them before any real use.

## ID formats

Yarn Cone `YC006` · COB `COB004` · Autoconer `AC-02` · Drum `D025` · Speedframe `SF-02` · Spindle `S128`.
Input is trimmed and uppercased automatically.

## Demo script (covers AC-01 … AC-12)

1. Log in as **operator1**. Search Yarn Cone **YC006**. It shows AC-02 / D025 and COB004, COB005 and COB015, with a flow diagram. (AC-01, AC-03)
2. Search COB **COB005**. The same cone appears with COB005 highlighted. (AC-02, AC-04)
3. Search **YC007** (Partial: no COBs), **YC008** (Data Inconsistency: a COB was scanned after the cone), **COB099** (Partial: not linked) and **YC999** (Not Found).
4. Open **Receive**. Enter YC901 on AC-01 / D011 with COB901 (SF-01 / S101) and COB902 (SF-02 / S128), both scanned before the cone. Save, then search YC901. (AC-05, AC-06)
5. Save YC901 again, then try Spindle S210 with Speedframe SF-01. Both are rejected with clear messages. (AC-07)
6. Log out and log in as **supervisor1**. Open **Report**, generate one for YC006, and download the PDF, Excel and CSV files. (AC-08, AC-09)
7. Log in as **admin**. **Admin → Audit Log** lists every login, search, receive, report and export. (AC-10)
8. Only the term "COB" is used throughout. (AC-11)
9. Database errors show a friendly message; see `test_database_error_returns_error_status`. Details go to `logs/app.log`. (AC-12)

## Tests

```bash
.venv/Scripts/python -m pytest -v
```

## Project layout

- `app.py`: entry point and navigation
- `config.py`: settings
- `database/`: engine and SQL queries
- `services/`: business logic, with no UI code
- `ui/`: Streamlit pages
- `utils/`: validators, dates, logging and security
- `sql/`: schema, indexes and sample data
- `scripts/init_db.py`: creates the database
- `tests/`: pytest suite

Design spec: `../docs/superpowers/specs/2026-09-23-yarn-cob-traceability-design.md`.
````

- [ ] **Step 2: Final verification**

Run: `.venv/Scripts/python -m pytest -v`
Expected: all tests PASS. The count should be around 90, because parametrized cases each count as one test.

Run: `grep -rniwE "cops?" --include=*.py --include=*.sql --include=*.md . --exclude-dir=.venv`
Expected: no output. Test inputs such as `COP1` and `COP004` don't match, because a digit follows "COP" and word matching needs a boundary there. Fix any match you do find.

Run: `.venv/Scripts/python scripts/init_db.py --reset`, then start the app and walk through the README demo script from start to finish.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add README with setup, demo accounts and acceptance demo script

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 4: Push (only after the user confirms)**

Ask the user before pushing. Once they confirm:
```bash
git push -u origin main
```
