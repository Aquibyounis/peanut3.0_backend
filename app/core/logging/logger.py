"""
Structured logging setup using ``structlog``.

In **development** mode, output is human-friendly coloured console lines.
In **production** mode, output is machine-parseable JSON (one object per line).
"""

from __future__ import annotations

import logging
import sys

import structlog

from app.core.config import settings


def _configure_structlog() -> None:
    """Wire up structlog processors based on the current environment."""

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.ExtraAdder(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    is_production = settings.app_env.lower() == "production"

    if is_production:
        # Machine-readable JSON lines
        shared_processors.append(
            structlog.processors.format_exc_info,
        )
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        # Pretty console output for local development
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Also configure stdlib logging so third-party libraries are formatted
    # consistently.
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                renderer,
            ],
        ),
    )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))


# Run configuration on import
_configure_structlog()


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Return a ``structlog`` bound logger scoped to *name*.

    Usage::

        from app.core.logging.logger import get_logger

        logger = get_logger(__name__)
        logger.info("user registered", user_id="abc-123")
    """
    return structlog.get_logger(name)
