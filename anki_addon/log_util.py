"""Simple logging utility for the add-on.

Provides get_logger() to obtain a configured logger that writes to
`addon.log` next to this file, and a convenience log() function.

Design goals:
- Safe to call multiple times (won't add duplicate handlers).
- Rotates logs (1MB per file, keep 3 backups).
- UTF-8 encoding and human-friendly timestamps.
"""
from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional

_DIR = os.path.dirname(__file__)
_LOG_FILENAME = os.path.join(_DIR, "addon.log")
_MAX_BYTES = 1 * 1024 * 1024  # 1 MB
_BACKUP_COUNT = 3


def _ensure_log_dir():
    # The addon directory should exist; this is defensive.
    if not os.path.isdir(_DIR):
        try:
            os.makedirs(_DIR, exist_ok=True)
        except Exception:
            # If we can't create the directory, let logging attempt to write
            # which will raise a clear error. We swallow here to avoid
            # masking the original error with a secondary one.
            pass


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a module-level logger configured to write to `addon.log`.

    The logger is configured only once per process to avoid duplicate
    handlers when called multiple times.

    Args:
        name: Optional logger name. If not provided, a default name
            'anki_addon' is used.

    Returns:
        logging.Logger: configured logger instance.
    """
    _ensure_log_dir()
    name = name or "anki_addon"
    logger = logging.getLogger(name)

    # Avoid configuring the same logger multiple times in a process.
    if getattr(logger, "_addon_configured", False):
        return logger

    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    try:
        handler = RotatingFileHandler(
            _LOG_FILENAME, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8"
        )
    except Exception:
        # If file handler cannot be created (permission, path), fall back to
        # a NullHandler so callers won't crash; they can still use other
        # logging sinks if configured externally.
        logger.addHandler(logging.NullHandler())
        logger._addon_configured = True
        return logger

    handler.setFormatter(fmt)
    logger.addHandler(handler)

    # Don't propagate to the root logger to avoid duplicate output in other
    # environments that may configure root handlers.
    logger.propagate = False
    logger._addon_configured = True
    return logger


def log(message: str, level: str = "info", name: Optional[str] = None) -> None:
    """Convenience wrapper to write a single message to the addon log.

    Args:
        message: The message to log. Should be a string; other objects will be
            converted with str().
        level: One of 'debug', 'info', 'warning', 'error', 'critical'. Case
            insensitive. Defaults to 'info'.
        name: Optional logger name to use. Defaults to the module default.
    """
    logger = get_logger(name)
    lvl = (level or "info").lower()
    if lvl == "debug":
        logger.debug(message)
    elif lvl in ("warn", "warning"):
        logger.warning(message)
    elif lvl == "error":
        logger.error(message)
    elif lvl == "critical":
        logger.critical(message)
    else:
        logger.info(message)


__all__ = ["get_logger", "log"]