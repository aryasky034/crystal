# ============================================================
#  CRYSTAL AI - Logger
#  Central logging for all modules
# ============================================================

import logging
import os
from src.utils.config_loader import get


def get_logger(name: str) -> logging.Logger:
    """
    Returns a named logger for any module.
    Usage:
        from src.utils.logger import get_logger
        log = get_logger(__name__)
        log.info("Crystal is starting...")
    """
    level_str = get("logging", "level", "INFO")
    level = getattr(logging, level_str.upper(), logging.INFO)

    logger = logging.getLogger(name)

    if logger.handlers:
        return logger  # Already configured

    logger.setLevel(level)

    # Console handler — always on
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(name)s → %(message)s",
        datefmt="%H:%M:%S"
    ))
    logger.addHandler(console)

    # File handler — optional
    if get("logging", "log_to_file", False):
        log_path = get("logging", "log_path", "data/crystal.log")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(name)s → %(message)s"
        ))
        logger.addHandler(file_handler)

    return logger