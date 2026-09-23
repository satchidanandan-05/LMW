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
