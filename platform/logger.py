#!/usr/bin/env python3
"""
platform/logger.py
==================
Structured dual-output logging for the SSL Certificate Lifecycle Platform.

Outputs:
  - Console: INFO level and above, coloured using rich
  - File: DEBUG level and above, plain text with timestamps

Log files are written to: logs/CERT_LIFECYCLE_YYYYMMDD_HHMMSS.log

Usage:
    from platform.logger import setup_logging, get_logger
    log, log_path = setup_logging()
    log.info("Starting discovery...")
    log.debug("Verbose debug info...")
    log.warning("Something needs attention")
    log.error("Something failed")
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
VERSION = "1.0.0"
LOG_DIR_DEFAULT = "logs"
LOG_FMT = "%(asctime)s %(levelname)-8s %(message)s"
LOG_DATE_FMT = "%Y-%m-%d %H:%M:%S"
CONSOLE_FMT = "%(levelname)-8s %(message)s"

# ANSI colour codes for console output (fallback if rich not available)
COLOURS = {
    "DEBUG":    "\033[36m",   # Cyan
    "INFO":     "\033[32m",   # Green
    "WARNING":  "\033[33m",   # Yellow
    "ERROR":    "\033[31m",   # Red
    "CRITICAL": "\033[35m",   # Magenta
    "RESET":    "\033[0m",
}


class ColouredFormatter(logging.Formatter):
    """Formatter that adds ANSI colour codes based on log level."""

    def format(self, record):
        colour = COLOURS.get(record.levelname, COLOURS["RESET"])
        reset = COLOURS["RESET"]
        record.levelname = f"{colour}{record.levelname}{reset}"
        return super().format(record)


def setup_logging(
    log_dir: str = LOG_DIR_DEFAULT,
    log_level_console: int = logging.INFO,
    log_level_file: int = logging.DEBUG,
    timestamp: str = None,
) -> tuple:
    """
    Configure dual-output logging.

    Args:
        log_dir: Directory for log files (created if not exists)
        log_level_console: Minimum level for console output (default: INFO)
        log_level_file: Minimum level for file output (default: DEBUG)
        timestamp: Timestamp string for log filename (default: auto-generated)

    Returns:
        Tuple of (logger, log_file_path)
    """
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"CERT_LIFECYCLE_{timestamp}.log")

    logger = logging.getLogger("cert_platform")
    logger.setLevel(logging.DEBUG)

    # Remove any existing handlers (avoid duplicate logs on re-init)
    logger.handlers.clear()

    # --- Console Handler ---
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level_console)
    try:
        from rich.logging import RichHandler
        console_handler = RichHandler(
            level=log_level_console,
            show_path=False,
            show_time=True,
            rich_tracebacks=True,
        )
    except ImportError:
        console_handler.setFormatter(ColouredFormatter(CONSOLE_FMT))

    # --- File Handler ---
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(log_level_file)
    file_handler.setFormatter(logging.Formatter(LOG_FMT, LOG_DATE_FMT))

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger, log_path


def get_logger() -> logging.Logger:
    """Get the platform logger (must call setup_logging first)."""
    return logging.getLogger("cert_platform")


def log_banner(logger: logging.Logger, title: str, subtitle: str = ""):
    """Print a formatted banner to the log."""
    width = 70
    logger.info("=" * width)
    logger.info(f"  {title}")
    if subtitle:
        logger.info(f"  {subtitle}")
    logger.info("=" * width)


def log_section(logger: logging.Logger, section: str):
    """Print a section header."""
    logger.info("")
    logger.info(f"--- {section} ---")


def log_pass(logger: logging.Logger, check: str, detail: str = ""):
    """Log a PASS result."""
    msg = f"[PASS] {check}"
    if detail:
        msg += f" — {detail}"
    logger.info(msg)


def log_fail(logger: logging.Logger, check: str, detail: str = ""):
    """Log a FAIL result."""
    msg = f"[FAIL] {check}"
    if detail:
        msg += f" — {detail}"
    logger.error(msg)


def log_warn(logger: logging.Logger, check: str, detail: str = ""):
    """Log a WARNING result."""
    msg = f"[WARN] {check}"
    if detail:
        msg += f" — {detail}"
    logger.warning(msg)


def log_summary(logger: logging.Logger, pass_count: int, fail_count: int, warn_count: int = 0, duration_s: float = 0):
    """Log a validation summary."""
    total = pass_count + fail_count + warn_count
    logger.info("")
    logger.info("=" * 70)
    logger.info("SUMMARY")
    logger.info("=" * 70)
    logger.info(f"  Total checks : {total}")
    logger.info(f"  Passed       : {pass_count}")
    if warn_count:
        logger.info(f"  Warnings     : {warn_count}")
    logger.info(f"  Failed       : {fail_count}")
    if duration_s:
        logger.info(f"  Duration     : {duration_s:.2f}s")
    logger.info("")
    if fail_count > 0:
        logger.error("STATUS: FAILED — Review failed checks above")
    elif warn_count > 0:
        logger.warning("STATUS: PASSED WITH WARNINGS — Review warnings above")
    else:
        logger.info("STATUS: ALL CHECKS PASSED")

