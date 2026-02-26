"""
Logging configuration for the trading bot.

Provides a centralized, structured logger with file rotation and
credential sanitization. All modules import `get_logger` from here.
"""

import copy
import logging
import os
from logging.handlers import RotatingFileHandler


# ---------------------------------------------------------------------------
# Credential sanitization
# ---------------------------------------------------------------------------
_SENSITIVE_KEYS = frozenset({
    "api_key", "apikey", "apiKey", "secret", "api_secret",
    "apiSecret", "signature", "password", "token",
})


def sanitize_params(params: dict) -> dict:
    """Return a shallow copy of *params* with sensitive fields redacted."""
    if not isinstance(params, dict):
        return params
    cleaned = copy.copy(params)
    for key in list(cleaned.keys()):
        if key.lower().replace("_", "") in {k.lower().replace("_", "") for k in _SENSITIVE_KEYS}:
            cleaned[key] = "***REDACTED***"
    return cleaned


# ---------------------------------------------------------------------------
# Logger factory
# ---------------------------------------------------------------------------
_LOG_DIR = os.environ.get("LOG_DIR", os.path.join(os.path.dirname(__file__), "logs"))
_LOG_FILE = os.path.join(_LOG_DIR, "trading_bot.log")
_LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] — %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the ``trading_bot`` namespace.

    On first call the root ``trading_bot`` logger is configured with:
    * A **RotatingFileHandler** (DEBUG+, 10 MB, 5 backups)  → ``./logs/trading_bot.log``
    * A **StreamHandler** (WARNING+) → stderr
    """
    global _configured
    if not _configured:
        _setup_root_logger()
        _configured = True
    return logging.getLogger(f"trading_bot.{name}")


def _setup_root_logger() -> None:
    os.makedirs(_LOG_DIR, exist_ok=True)

    root = logging.getLogger("trading_bot")
    root.setLevel(logging.DEBUG)

    # File handler — DEBUG and above
    fh = RotatingFileHandler(
        _LOG_FILE,
        maxBytes=10 * 1024 * 1024,   # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
    root.addHandler(fh)

    # Console handler — WARNING and above
    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    ch.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
    root.addHandler(ch)
