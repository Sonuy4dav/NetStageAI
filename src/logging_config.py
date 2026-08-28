"""Application logging setup."""

import logging


def configure_logging() -> logging.Logger:
    """Return the application logger with a safe console handler."""
    logger = logging.getLogger("netstage")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger
