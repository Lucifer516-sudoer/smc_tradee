from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

from .config import LoggingConfig


def configure_logging(config: LoggingConfig) -> None:
    """Configure loguru for console and rotating file output."""
    log_file_parent: Path = config.file_path.parent
    log_file_parent.mkdir(parents=True, exist_ok=True)

    logger.remove()
    logger.add(
        sys.stdout,
        level=config.level,
        backtrace=False,
        diagnose=False,
        enqueue=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | {message}",
    )
    logger.add(
        str(config.file_path),
        level=config.level,
        rotation=config.rotation,
        retention=config.retention,
        enqueue=True,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
    )
