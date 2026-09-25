"""Logging configuration for Vizzy API.

Sets up structured console logging.
Sensitive values (API keys, JWTs, passwords) are NEVER logged.
"""

import logging
import sys


def configure_logging(debug: bool = False) -> None:
    """Configure root logger for the application.

    Args:
        debug: When True, sets log level to DEBUG; otherwise INFO.
    """
    log_level = logging.DEBUG if debug else logging.INFO

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Avoid duplicate handlers on hot-reload
    if not root_logger.handlers:
        root_logger.addHandler(handler)
    else:
        root_logger.handlers = [handler]

    # Suppress noisy third-party loggers in production
    if not debug:
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger.

    Args:
        name: Module name, typically ``__name__``.

    Returns:
        A configured :class:`logging.Logger` instance.
    """
    return logging.getLogger(name)
