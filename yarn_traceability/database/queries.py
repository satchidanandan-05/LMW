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
