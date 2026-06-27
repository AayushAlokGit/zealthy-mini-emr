import logging

from .config import settings

_configured = False


def setup_logging() -> None:
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
    root.propagate = False
    _configured = True


def get_logger(area: str) -> logging.Logger:
    return logging.getLogger(f"zealthy.{area}")
