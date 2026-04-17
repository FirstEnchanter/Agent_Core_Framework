"""
Logging Tool  Layer 3: Execution / Logging & Monitoring

Structured logger meeting SH mandatory logging requirements (from CLAUDE.md):

For all meaningful actions, log:
    - What was done
    - When it was done
    - Why it was done
    - What changed

For errors, log:
    - Failure type
    - Attempted fix
    - Final state

Uses structlog for structured, consistent JSON-compatible output.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

import structlog
from structlog.types import FilteringBoundLogger

# 
# Configuration
# 

_configured = False


def _configure_logging() -> None:
    global _configured
    if _configured:
        return

    log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    log_dir = Path(os.environ.get("LOG_DIR", "logs"))

    # Ensure logs directory exists
    log_dir.mkdir(parents=True, exist_ok=True)

    # Shared processors for all log records
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    # Configure structlog
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Console formatter (human-readable)
    console_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer(colors=True),
        foreign_pre_chain=shared_processors,
    )

    # File formatter (JSON for log parsing)
    json_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=shared_processors,
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)

    # File handler (one log file per run, rotated by date)
    from logging.handlers import TimedRotatingFileHandler
    file_handler = TimedRotatingFileHandler(
        filename=log_dir / "agent.log",
        when="midnight",
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.setFormatter(json_formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    _configured = True


def get_logger(name: str) -> FilteringBoundLogger:
    """
    Return a configured structlog logger for the given module name.

    Usage:
        log = get_logger(__name__)
        log.info("action.completed", what="published post", why="directive: publish-bluesky")
    """
    _configure_logging()
    return structlog.get_logger(name)


# 
# Structured action logger helpers
# 

def log_action(
    logger: FilteringBoundLogger,
    *,
    what: str,
    when: str,
    why: str,
    changed: str,
    **extra: Any,
) -> None:
    """
    Log a meaningful action with the 4 mandatory fields.

    Args:
        logger:  structlog logger instance
        what:    What was done
        when:    When it was done (ISO timestamp string)
        why:     Why it was done (directive ID or reason)
        changed: What changed as a result
        **extra: Additional context fields
    """
    logger.info(
        "action.logged",
        what=what,
        when=when,
        why=why,
        changed=changed,
        **extra,
    )


def log_error(
    logger: FilteringBoundLogger,
    *,
    failure_type: str,
    attempted_fix: str,
    final_state: str,
    **extra: Any,
) -> None:
    """
    Log an error with the 3 mandatory error fields.

    Args:
        logger:        structlog logger instance
        failure_type:  Classification of what went wrong
        attempted_fix: What the system tried to do to correct it
        final_state:   The state of the system after the error
        **extra:       Additional context fields
    """
    logger.error(
        "error.logged",
        failure_type=failure_type,
        attempted_fix=attempted_fix,
        final_state=final_state,
        **extra,
    )
