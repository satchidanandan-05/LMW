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

## Checking the database

The database is a single SQLite file, `data/traceability.db`. It is created by `scripts/init_db.py` and is git-ignored.

- **VS Code:** install the **SQLite Viewer** extension (by Florian Klampfer), then click `data/traceability.db` to browse each table.
- **Desktop app:** open the file in [DB Browser for SQLite](https://sqlitebrowser.org/). Use *Browse Data* to view tables and *Execute SQL* to run queries.
- **Terminal (no install needed):** run any query through the project's Python:

  ```bash
  .venv/Scripts/python -c "import sqlite3, pandas as pd; print(pd.read_sql('SELECT * FROM yarn_cone', sqlite3.connect('data/traceability.db')))"
  ```

  To list each cone with its COBs:

  ```sql
  SELECT ct.cy_id, c.cob_id, s.speedframe_id, c.spindle_id, c.cob_scan_datetime
  FROM cob_traceability ct
  JOIN cob c ON c.cob_id = ct.cob_id
  JOIN spindle s ON s.spindle_id = c.spindle_id
  ORDER BY ct.cy_id
  ```

- **In the app:** log in as **admin** and use the **Admin** page to see machines, users and the audit log.

Tables: `yarn_cone`, `cob`, `cob_traceability` (which COB is in which cone), `autoconer`, `drum`, `speedframe`, `spindle`, `users`, `audit_log`. The full definitions are in `sql/schema.sql`.

Close any viewer that has the file open before running `scripts/init_db.py --reset`, because Windows cannot delete a file that is in use.

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
