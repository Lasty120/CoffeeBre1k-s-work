"""Centralised logging configuration for the entire application.

Call setup_logging() exactly once at application startup (in main.py).
After that, every module obtains its own logger via:

    import logging
    logger = logging.getLogger(__name__)

No module should call basicConfig() or add handlers on its own.
"""

import logging
import sys

from core.config import settings

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging() -> None:
    """Configures the root logger for the application.

    Args:
        None: Reads log level from core.config.settings.DEBUG.

    Returns:
        None: Mutates the root logger in-place.
    """
    level = logging.DEBUG if settings.DEBUG else logging.INFO

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    logging.getLogger("uvicorn.access").propagate = False
