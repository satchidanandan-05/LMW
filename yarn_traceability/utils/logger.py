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
