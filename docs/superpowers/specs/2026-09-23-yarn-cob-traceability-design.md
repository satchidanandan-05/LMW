# Yarn Cone / COB Traceability Dashboard — Design Spec

- **Date:** 2026-09-23
- **Status:** Approved design, pending implementation plan
- **Source requirements:** `Yarn_Traceability_Dashboard_Project_Specification.md` (v1.0) and the example screen `WhatsApp Image 2026-09-23 at 4.18.55 PM.jpeg`
- **Purpose of build:** Academic / demo project. It runs on a laptop with seeded sample data. It favours clarity and polish over production hardening.

This document resolves the open decisions in §18 of the source requirements and fixes the gaps found between that document and the example image. Where this spec and the source document conflict, this spec wins.

---

## 1. Decisions

| Item | Decision |
|---|---|
| Database | **SQLite** (single file, `data/traceability.db`). SQL Server remains the production target and is reached by changing `DATABASE_URL` only. No SQL Server-specific features are used. |
| Architecture | **SQL-first.** `sql/schema.sql` is the single source of truth for the schema. Queries are named, parameterized SQLAlchemy `text()` statements. There are no ORM models, and `models.py` from the source folder layout is dropped. |
| Terminology | **COB** everywhere: UI, code, DB and reports. The image's "COP" wording is not used. |
| Cardinality | **Many COBs → exactly one Yarn Cone.** A COB can be linked to only one cone, enforced by `UNIQUE(cob_id)` on `cob_traceability`. |
| Receive mode | **One combined form:** the cone plus 1..N COB rows, saved as one transaction. Barcode scanners work as keyboard input and need no special handling. |
| ID formats | Taken from the example image, uppercase, configurable in `config.py` (see §5). |
| Master data | Seeded by `sample_data.sql`, and admins can add more on an Admin page. Receive uses dropdowns constrained by master data. |
| Authentication | Username/password stored as bcrypt hashes in `users`. There are three roles: operator, supervisor and admin. |
| Edit policy | Received records **cannot** be edited or deleted through the UI. |
| Report formats | PDF, Excel and CSV are all required. |
| Time | Plant-local time (Asia/Kolkata), stored as naive ISO-8601 text `YYYY-MM-DD HH:MM:SS` and displayed as `dd-mm-yyyy HH:MM:SS`. |
| Retention / SLA / backup | Not applicable to the demo. The source NFRs are kept as targets only. The ≤ 3 s search target is easily met with SQLite and the indexes in §3.3. |

## 2. Architecture

```
User → Streamlit UI (ui/*) → Services (services/*) → database/queries.py (text SQL)
                                                  → database/database.py (SQLAlchemy engine) → SQLite
```

Rules:
- UI pages contain **no SQL** and call only services.
- Services depend only on `database/`, `utils/` and `config`. Services must not import Streamlit, so they can be tested against in-memory SQLite.
- All SQL that takes user input is parameterized.
- Every connection runs `PRAGMA foreign_keys=ON`. This is done in an engine `connect` event listener.

### 2.1 Folder structure

```
yarn_traceability/
├── app.py                       # login gate + role-based navigation (st.navigation)
├── config.py                    # settings from .env (python-dotenv); ID regexes; TZ; app name/version
├── requirements.txt
├── .env.example                 # DATABASE_URL, LOG_LEVEL (real .env git-ignored)
├── README.md                    # setup, demo accounts, manual demo script
├── database/
│   ├── database.py              # engine factory, FK pragma, transaction context manager
│   └── queries.py               # named parameterized text() queries
├── services/
│   ├── traceability_service.py  # get_traceability / search_cy / search_cob
│   ├── receive_service.py       # validate_receive / save_receive
│   ├── report_service.py        # generate_report
│   ├── export_service.py        # to_pdf / to_excel / to_csv -> bytes
│   ├── audit_service.py         # log()
│   ├── auth_service.py          # authenticate, has_role
│   └── master_service.py        # list/add machines, users (Admin)
├── ui/
│   ├── login.py  search.py  receive.py  report.py  admin.py
│   └── components.py            # shared result view: summary card, COB table, Graphviz diagram
├── utils/
│   ├── validators.py            # pure ID/date/business-rule checks
│   └── logger.py                # rotating file logger → logs/app.log
├── sql/
│   ├── schema.sql  indexes.sql  sample_data.sql
├── scripts/
│   └── init_db.py               # creates DB from the three SQL files (--reset to recreate)
├── data/  logs/                 # runtime, git-ignored
└── tests/
```

### 2.2 Dependencies

`streamlit`, `sqlalchemy>=2`, `pandas`, `graphviz` (Python package; Streamlit renders DOT through `st.graphviz_chart`, so no system binary is needed), `reportlab`, `openpyxl`, `bcrypt`, `python-dotenv`, `pytest`.

## 3. Data Model

### 3.1 Tables (`sql/schema.sql`)

```sql
autoconer  (autoconer_id TEXT PK,             -- 'AC-02'
            machine_name TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1)

drum       (drum_id TEXT PK,                  -- 'D025'
            autoconer_id TEXT NOT NULL FK → autoconer)

speedframe (speedframe_id TEXT PK,            -- 'SF-02'
            machine_name TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1)

spindle    (spindle_id TEXT PK,               -- 'S128' (globally unique)
            speedframe_id TEXT NOT NULL FK → speedframe)

users      (user_id INTEGER PK AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('operator','supervisor','admin')),
            status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','disabled')))

yarn_cone  (cy_id TEXT PK,                    -- 'YC006'
            drum_id TEXT NOT NULL FK → drum,
            cone_scan_datetime TEXT NOT NULL,
            receive_txn_id TEXT NOT NULL,
            created_by INTEGER NOT NULL FK → users,
            created_at TEXT NOT NULL)

cob        (cob_id TEXT PK,                   -- 'COB004'
            spindle_id TEXT NOT NULL FK → spindle,
            cob_scan_datetime TEXT NOT NULL,
            receive_txn_id TEXT NOT NULL,
            created_by INTEGER NOT NULL FK → users,
            created_at TEXT NOT NULL)

cob_traceability
           (trace_id INTEGER PK AUTOINCREMENT,
            cy_id TEXT NOT NULL FK → yarn_cone,
            cob_id TEXT NOT NULL UNIQUE FK → cob,   -- many COBs → one cone
            receive_txn_id TEXT NOT NULL,
            created_at TEXT NOT NULL)

audit_log  (audit_id INTEGER PK AUTOINCREMENT,
            user_id INTEGER FK → users,             -- NULL only for failed logins of unknown users
            action TEXT NOT NULL CHECK (action IN
                   ('LOGIN','SEARCH','RECEIVE','REPORT','EXPORT','ADMIN')),
            id_type TEXT,                           -- 'CY' | 'COB' | NULL
            id_value TEXT,
            result TEXT NOT NULL,                   -- 'SUCCESS' | 'FAILED' | trace status
            detail TEXT,
            event_datetime TEXT NOT NULL)
```

### 3.2 Changes from the source document

- **Machine IDs are stored once and derived by joins.** `yarn_cone` stores only `drum_id`, and the Autoconer is found through `drum.autoconer_id`. `cob` stores only `spindle_id`, and the Speedframe is found through `spindle.speedframe_id`. This removes the redundant `yarn_cone.autoconer_id` and `cob.speedframe_id`, which could otherwise disagree with the masters.
- **Scan times** are stored on the entity rows (`cone_scan_datetime`, `cob_scan_datetime`). `cob_traceability` has no separate scan time.
- **Transaction ID:** every row written by one Receive shares a `receive_txn_id` (UUID4). There is no separate transaction table. The audit log records each attempt and its outcome.
- **Spindle IDs are globally unique**, as the image implies (S128/S129 on SF-02, S210 on SF-05). If real plant data reuses spindle numbers per frame, the key changes to `(speedframe_id, spindle_no)`. That case is out of scope here.

### 3.3 Indexes (`sql/indexes.sql`)

`cob_traceability(cy_id)`, `drum(autoconer_id)`, `spindle(speedframe_id)`, `audit_log(event_datetime)`. Primary keys and `UNIQUE(cob_id)` are indexed implicitly.

## 4. Services

### 4.1 Traceability service (shared by Search and Report)

```python
@dataclass
class ConeInfo:   cy_id, autoconer_id, drum_id, cone_scan_datetime: datetime
@dataclass
class CobInfo:    cob_id, speedframe_id, spindle_id, cob_scan_datetime: datetime
@dataclass
class TraceResult:
    status: Literal['FOUND','NOT_FOUND','PARTIAL','INCONSISTENT','ERROR']
    searched_type: Literal['CY','COB']
    searched_id: str
    cone: ConeInfo | None
    cobs: list[CobInfo]          # ordered by cob_scan_datetime, then cob_id
    exceptions: list[str]        # human-readable reasons for PARTIAL/INCONSISTENT

get_traceability(id_type, id_value) -> TraceResult   # normalizes (trim+upper) then dispatches
search_cy(cy_id) -> TraceResult
search_cob(cob_id) -> TraceResult
```

- **`search_cy` (forward trace):** loads the cone joined to its drum and autoconer, then all linked COBs joined to their spindle and speedframe.
- **`search_cob` (reverse trace):** loads the COB joined to its spindle and speedframe, finds its cone through `cob_traceability`, then loads that cone **and all of its COBs**, including the searched one. The UI highlights the searched COB. Both directions show the same full genealogy.
- **Status rules**, evaluated in this order:
  1. `ERROR`: a database exception. It is logged with a stack trace, `exceptions` is set to `["System error — please retry or contact admin"]`, and `cone` is `None` with `cobs` empty.
  2. `NOT_FOUND`: the ID doesn't exist.
  3. `INCONSISTENT`: at least one COB has `cob_scan_datetime > cone_scan_datetime`. A COB must exist before it is wound into a cone. Each offending COB adds one exception.
  4. `PARTIAL`: the cone has zero COBs, or the searched COB has no cone link. In the second case `cone` is `None` and `cobs` holds just that COB.
  5. `FOUND`: none of the above.
- Missing relationships are reported, never inferred.

### 4.2 Receive service

```python
@dataclass
class CobEntry:       cob_id, speedframe_id, spindle_id, cob_scan_datetime: datetime
@dataclass
class ReceivePayload: cy_id, autoconer_id, drum_id, cone_scan_datetime: datetime, cobs: list[CobEntry]
@dataclass
class ValidationError: field: str, row: int | None, message: str   # row = COB row index (1-based) or None

validate_receive(payload) -> list[ValidationError]        # read-only; collects ALL errors
save_receive(payload, user_id) -> str                     # returns receive_txn_id; raises ReceiveRejected(errors)
```

`validate_receive` runs these checks and returns every error rather than stopping at the first:
1. All IDs are non-blank, and all IDs match their regex (§5). IDs are normalized with trim and uppercase before checking.
2. `cy_id` doesn't already exist in `yarn_cone`.
3. There is at least one COB row.
4. No COB ID is repeated within the form, and no COB ID already exists in `cob`.
5. `autoconer_id` exists and is active, and `drum_id` belongs to that autoconer.
6. For each row, `speedframe_id` exists and is active, and `spindle_id` belongs to that speedframe.
7. No timestamp is in the future. A small clock-skew allowance of 5 minutes is applied.
8. Each `cob_scan_datetime` is at or before `cone_scan_datetime`.

`save_receive` runs `validate_receive` again. If there are no errors, it inserts `yarn_cone`, then every `cob`, then every `cob_traceability` row inside **one transaction** with a new UUID4 `receive_txn_id`. If any exception occurs, the transaction is rolled back. An `IntegrityError` caused by a concurrent duplicate is converted into a `ReceiveRejected` with a duplicate message. Every attempt is audited as `RECEIVE`, with `result` set to `SUCCESS` or `FAILED` and the error summary in `detail`.

### 4.3 Report and export services

- `generate_report(id_type, id_value, user) -> ReportData` calls `get_traceability`, writes a `REPORT` audit row, and returns the `TraceResult` plus header metadata: title, searched ID, generation time, username, and reference number `RPT-<audit_id>`.
- `export_service.to_pdf(report) / to_excel(report) / to_csv(report) -> bytes`:
  - **PDF (ReportLab):** the header, a Cone Information table, a COB Information table, the trace chain as text (for example `YC006 → AC-02 / D025 → COB004 (SF-02/S128), …`), an Exceptions section showing "None" when there are none, and a footer with the system name, report version `1.0` and the reference number.
  - **Excel (pandas + OpenPyXL):** `Summary`, `COBs` and `Exceptions` sheets.
  - **CSV:** one row per COB with the cone columns repeated. A cone with no COBs produces a single row with empty COB columns.
- Each download writes an `EXPORT` audit row with the format in `detail`.

### 4.4 Audit, auth and master services

- `audit_service.log(user_id, action, id_type=None, id_value=None, result, detail=None)`. An audit failure is logged to the file and **never** blocks the user action.
- `auth_service.authenticate(username, password) -> User | None` uses bcrypt, rejects disabled users, and audits `LOGIN` on both success and failure. `has_role(user, page)` uses the matrix in §6.
- `master_service` lists machines for dropdowns and adds an autoconer, drum, speedframe, spindle or user. It can also disable a user. All inputs are validated with the same regexes, and every change is audited as `ADMIN`.

## 5. ID Formats (`config.py`)

| Entity | Regex | Example |
|---|---|---|
| Yarn Cone | `^YC\d+$` | YC006 |
| COB | `^COB\d+$` | COB004 |
| Autoconer | `^AC-\d+$` | AC-02 |
| Drum | `^D\d+$` | D025 |
| Speedframe | `^SF-\d+$` | SF-02 |
| Spindle | `^S\d+$` | S128 |

All input is trimmed and uppercased before matching.

## 6. User Interface (Streamlit)

**Role matrix**

| Page | operator | supervisor | admin |
|---|---|---|---|
| Search | ✓ | ✓ | ✓ |
| Receive | ✓ | | ✓ |
| Report | | ✓ | ✓ |
| Admin | | | ✓ |

The navigation shows only the pages the user's role allows. Each page also checks `has_role` on load, so hiding a page is not the only protection. A logout button sits in the sidebar with the username and role.

**Login:** a username/password form. On success the user is stored in `st.session_state.user`.

**Search:**
- A CY ID / COB ID radio, an ID text input, and Search and Clear buttons.
- Results show a status badge (green FOUND, amber PARTIAL, red INCONSISTENT, grey NOT_FOUND, red ERROR) and a cone summary card with Yarn Cone ID, Autoconer, Drum and Cone Scan Date & Time.
- A COB table follows, with Sl. No., COB ID, Speedframe, Spindle and COB Scan Date & Time. The searched COB is highlighted.
- A **Graphviz traceability diagram** shows: cone node (with Autoconer/Drum) → one node per COB (with Speedframe and Spindle).
- Any exceptions are listed at the end.
- The page reproduces the layout of the example image. Every search is audited.

**Receive:**
- **Cone section:** CY ID text input; Autoconer dropdown (active only); Drum dropdown filtered by the chosen autoconer; scan date and time, defaulting to now.
- **COB section:** an `st.data_editor` grid with dynamic rows and columns COB ID (text), Speedframe (select), Spindle (select from all spindles) and Scan date/time. Whether the spindle belongs to the speedframe is checked during validation.
- **Validate & Save** shows every validation error grouped by row, or a success panel with the transaction ID and the number of COBs saved. After a successful save the form is cleared.

**Report:** a CY/COB radio, an ID input and a Generate button. It renders the same shared result view as Search, plus the header metadata. It then shows three `st.download_button`s (PDF, Excel, CSV) with file names like `traceability_YC006_20260923_161855.pdf`.

**Admin:** tabs for Machines (add an autoconer, drum, speedframe or spindle; list existing ones), Users (add a user with a role, disable a user) and Audit Log (the latest 200 rows, filterable by action).

## 7. Error Handling and Logging

- Services catch `SQLAlchemyError` at their boundary, log the full stack trace to `logs/app.log` (a rotating file, 1 MB × 3), and return an `ERROR` status or raise a domain exception. The UI shows only friendly messages and never raw SQL or stack traces.
- Validation errors are shown per field or row, and nothing is written to the database.
- Unique constraints in the database are the last safeguard against duplicates when two users save at once.
- The database credentials and URL come from `.env`, and nothing is hard-coded. `.env.example` is committed, and `.env` is git-ignored.

## 8. Sample Data (`sql/sample_data.sql`)

- **Machines:** 3 autoconers (AC-01…AC-03), 6 drums (2 per autoconer, including D025 on AC-02), 5 speedframes (SF-01…SF-05) and about 20 spindles (including S128 and S129 on SF-02, and S210 on SF-05).
- **Image scenario, exactly as shown:**
  - YC006 on AC-02 / D025, scanned 20-09-2026 11:12:09.
  - COB004 (SF-02 / S128, 08:05:12), COB005 (SF-02 / S129, 08:06:18) and COB015 (SF-05 / S210, 09:14:33).
- **Status demos:**
  - 2–3 more FOUND cones.
  - One PARTIAL cone with no COBs.
  - One orphan COB with no cone link, for a PARTIAL COB search.
  - One INCONSISTENT cone where a COB's scan time is later than the cone's.
- **Users:** `operator1`, `supervisor1` and `admin`, with bcrypt hashes of demo passwords documented in the README. `scripts/init_db.py` generates the hashes when it seeds, so no plaintext passwords go in the SQL.

## 9. Testing (pytest)

The fixture builds an in-memory SQLite database from `schema.sql`, `indexes.sql` and the sample data, with foreign keys enabled.

| Area | Tests |
|---|---|
| validators | Each regex accepts and rejects the expected IDs; normalization; future time; COB time after cone time |
| traceability | CY search gives YC006 with 3 COBs; COB search for COB005 gives the same cone and all 3 COBs; NOT_FOUND; PARTIAL (cone with no COBs); PARTIAL (orphan COB); INCONSISTENT; ERROR on a simulated DB failure; Search and Report return equal `TraceResult`s |
| receive | Happy path writes 1 cone, N COBs and N links with the same txn ID; duplicate CY; COB duplicated in the form; COB already in the DB; spindle on the wrong speedframe; drum on the wrong autoconer; zero COBs; all errors collected at once; rollback when an insert fails partway through leaves no rows |
| auth | Correct and wrong password; disabled user; role matrix |
| export | PDF, Excel and CSV are non-empty and contain the searched ID; CSV row count equals the COB count |
| audit | SEARCH, RECEIVE (success and failure), REPORT, EXPORT, LOGIN and ADMIN each write one row; an audit failure doesn't raise |

The Streamlit pages have no unit tests. The README includes a step-by-step manual demo script that covers every acceptance criterion.

## 10. Acceptance Criteria Mapping

| AC | Covered by |
|---|---|
| AC-01, AC-02 | Search page with CY/COB selector; `get_traceability` |
| AC-03 | `search_cy` returns autoconer, drum and all COBs |
| AC-04 | `search_cob` returns speedframe, spindle and cone (plus sibling COBs) |
| AC-05, AC-06 | Receive page; `save_receive` transaction |
| AC-07 | `validate_receive` rules 1–8; DB unique constraints |
| AC-08 | Report page; `generate_report` |
| AC-09 | `export_service` PDF / Excel / CSV |
| AC-10 | `audit_service` on every action; Admin audit view |
| AC-11 | COB terminology throughout; no "COP" anywhere |
| AC-12 | §7 error handling |

## 11. Out of Scope

- The source document's out-of-scope items: PLC control, IoT/MES integration, predictive analytics and AI.
- Editing or deleting received records.
- Enterprise SSO.
- Multi-plant setups.
- Spindle numbers that repeat per speedframe.
- A KPI or home dashboard. Search is the landing page.
- Production deployment, backups and retention.
