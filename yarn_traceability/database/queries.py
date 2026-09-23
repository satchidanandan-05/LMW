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
