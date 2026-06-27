"""Centralized logging configuration.

Configures a single ``zealthy`` logger namespace with a consistent format,
independent of uvicorn's own access logs. Every module gets a child logger via
``get_logger("<area>")`` so log lines are grouped (zealthy.request,
zealthy.auth, zealthy.audit, …) and the whole app's verbosity is one env var.
"""
import logging

from .config import settings

_configured = False


def setup_logging() -> None:
    """Idempotently configure the ``zealthy`` logger from settings.log_level."""
    global _configured
    if _configured:
        return

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)-7s %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    root = logging.getLogger("zealthy")
    root.setLevel(level)
    root.handlers = [handler]
    root.propagate = False  # don't double-log through uvicorn's root handler
    _configured = True


def get_logger(area: str) -> logging.Logger:
    return logging.getLogger(f"zealthy.{area}")
