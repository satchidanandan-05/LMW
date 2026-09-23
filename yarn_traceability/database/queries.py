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
