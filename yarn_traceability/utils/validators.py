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
