"""Simple logging configuration."""

import sys
from loguru import logger


def configure_logging(level: str = "INFO") -> None:
    """Configure basic logging."""
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}:{function}:{line}</cyan> | <level>{message}</level>",
        level=level,
        colorize=True,
    )


# Initialize logging on module import
configure_logging()
