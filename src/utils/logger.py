import sys
from pathlib import Path

from loguru import logger

from src.config import VERBOSE_MODE


def setup_logger():
    """
    Configure loguru logger with file and console outputs.

    - Logs are written to data/bot.log
    - If verbose mode is enabled, additional debug information is included
    """
    # Create data directory if it doesn't exist
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    # Configure loguru
    log_file = data_dir / "bot.log"

    # Remove default handler
    logger.remove()

    # Add file handler
    logger.add(
        log_file,
        rotation="10 MB",  # Rotate when file reaches 10MB
        retention="1 week",  # Keep logs for 1 week
        compression="zip",  # Compress rotated logs
        level="DEBUG" if VERBOSE_MODE else "INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}"
        if VERBOSE_MODE
        else "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    )

    # Add console handler
    logger.add(
        sys.stderr,
        level="DEBUG" if VERBOSE_MODE else "INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}"
        if VERBOSE_MODE
        else "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    )

    logger.info("Logger initialized")
    if VERBOSE_MODE:
        logger.debug("Verbose mode enabled")

    return logger
