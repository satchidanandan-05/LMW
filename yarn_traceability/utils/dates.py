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
