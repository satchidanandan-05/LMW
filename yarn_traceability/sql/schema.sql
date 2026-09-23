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
