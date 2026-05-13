"""
Structured logging configuration.

This module configures structlog for the application. It produces:
- JSON logs in production (machine-parseable, queryable)
- Pretty colored logs in development (human-readable)

Every log line includes contextual fields automatically:
- timestamp, level, logger name
- service name and version
- environment (development/staging/production)
- correlation ID (when bound via bind_correlation_id)

Usage:
    from app.core.logging import get_logger

    logger = get_logger(__name__)
    logger.info("user_logged_in", user_id=42, ip="192.168.1.1")
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from app.core.config import settings


# ==============================================================================
# Standard Library Logging Bridge
# ==============================================================================
# Many libraries (uvicorn, FastAPI, langchain) use Python's standard logging
# module. We configure standard logging to feed into structlog's processors so
# everything goes through the same pipeline with the same format.


def _configure_stdlib_logging() -> None:
    """Configure Python's standard logging to use structlog's processors."""
    # Remove existing handlers — start clean
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create a single stream handler writing to stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.NOTSET)

    # Use structlog's formatter for stdlib logs
    foreign_pre_chain = _shared_processors()

    if settings.log_format == "json":
        formatter: logging.Formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer(),
            foreign_pre_chain=foreign_pre_chain,
        )
    else:
        formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.dev.ConsoleRenderer(colors=True),
            foreign_pre_chain=foreign_pre_chain,
        )

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.log_level)

    # Silence overly chatty third-party loggers
    for noisy_logger in ["urllib3", "httpx", "asyncio"]:
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)


# ==============================================================================
# Shared Processors
# ==============================================================================
# Processors transform log entries — adding context, formatting timestamps,
# rendering output. The order matters: each processor receives the output of
# the previous one.


def _shared_processors() -> list[Processor]:
    """Return the list of structlog processors used by both stdlib and structlog."""
    return [
        # Merge contextvars (correlation IDs) into the event dict
        structlog.contextvars.merge_contextvars,
        # Add log level as a field
        structlog.stdlib.add_log_level,
        # Add logger name as a field
        structlog.stdlib.add_logger_name,
        # Add ISO 8601 timestamp
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        # Add static service metadata to every log entry
        _add_service_metadata,
        # Convert exceptions to readable strings
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        # Decode any bytes values to strings
        structlog.processors.UnicodeDecoder(),
    ]


def _add_service_metadata(
    logger: Any, method_name: str, event_dict: EventDict
) -> EventDict:
    """Add static service metadata to every log entry."""
    event_dict["service"] = settings.app_name
    event_dict["version"] = settings.app_version
    event_dict["environment"] = settings.app_env
    return event_dict

# ==============================================================================
# Public API
# ==============================================================================


def setup_logging() -> None:
    """
    Configure structlog and standard logging for the application.

    Call this once at application startup, before any other module logs.
    Subsequent calls are idempotent — safe to call multiple times.
    """
    # Configure standard library logging first (the bridge)
    _configure_stdlib_logging()

    # Configure structlog itself
    shared_processors = _shared_processors()

    # The final processor depends on output format
    if settings.log_format == "json":
        final_processor: Processor = structlog.processors.JSONRenderer()
    else:
        final_processor = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            # Render the event dict as the chosen format
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level)
        ),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Return a structlog logger.

    Args:
        name: Logger name, typically `__name__` from the calling module.
              If None, returns the root logger.

    Returns:
        A bound logger that produces structured output.

    Example:
        logger = get_logger(__name__)
        logger.info("user_logged_in", user_id=42)
    """
    return structlog.stdlib.get_logger(name)


# ==============================================================================
# Correlation ID Management
# ==============================================================================
# Correlation IDs link related log entries across services and async boundaries.
# When an HTTP request arrives, the API middleware generates a correlation ID
# and binds it via bind_correlation_id. From that point, every log entry in
# this request's call chain includes the correlation ID automatically.


def bind_correlation_id(correlation_id: str) -> None:
    """
    Bind a correlation ID to the current context.

    All subsequent log entries from this async task / thread will include
    the correlation_id field automatically, until unbind_correlation_id
    is called or the task completes.

    Args:
        correlation_id: A unique identifier for the current request or task.
    """
    structlog.contextvars.bind_contextvars(correlation_id=correlation_id)


def unbind_correlation_id() -> None:
    """Remove the correlation ID from the current context."""
    structlog.contextvars.unbind_contextvars("correlation_id")


def bind_context(**kwargs: Any) -> None:
    """
    Bind arbitrary key-value pairs to the current logging context.

    Useful for adding agent name, task ID, or other contextual information
    that should appear in all subsequent log entries.

    Example:
        bind_context(agent_name="planner", task_id="abc-123")
        logger.info("processing_started")
        # Both agent_name and task_id appear in the log entry automatically
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_context() -> None:
    """Clear all bound context variables from the current context."""
    structlog.contextvars.clear_contextvars()