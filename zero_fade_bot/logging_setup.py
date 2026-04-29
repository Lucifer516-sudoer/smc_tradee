from __future__ import annotations

import logging
import sys
from pathlib import Path

from .config import LoggingConfig


class _ColorFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\x1b[36m",
        "INFO": "\x1b[32m",
        "WARNING": "\x1b[33m",
        "ERROR": "\x1b[31m",
        "CRITICAL": "\x1b[35m",
    }
    RESET = "\x1b[0m"

    def format(self, record: logging.LogRecord) -> str:
        original = record.levelname
        color = self.COLORS.get(original, "")
        if color:
            record.levelname = f"{color}{original}{self.RESET}"
        try:
            return super().format(record)
        finally:
            record.levelname = original


def configure_logging(config: LoggingConfig) -> None:
    """Configure application logging for console and file output."""
    log_file_parent: Path = config.file_path.parent
    log_file_parent.mkdir(parents=True, exist_ok=True)

    level = getattr(logging, config.level.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()

    log_format = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(_ColorFormatter(log_format, datefmt=date_format))

    file_handler = logging.FileHandler(config.file_path, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    logging.getLogger("metatrader5_wrapper").setLevel(level)
