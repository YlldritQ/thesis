"""Structured logging via structlog.

Console format for humans, JSON for prod / aggregation. Every log entry
carries a ``run_id`` so downstream traces can be reconstructed.
"""

from __future__ import annotations

import logging
import sys
import uuid
from datetime import datetime, timezone
from typing import cast

import structlog

from .config import settings


def _new_run_id() -> str:
    return f"run-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:8]}"


_configured = False


def configure() -> None:
    """Configure structlog. Idempotent."""
    global _configured
    if _configured:
        return

    cfg = settings()
    log_level = getattr(logging, cfg.log_level.upper(), logging.INFO)

    renderer: structlog.types.Processor
    if cfg.log_format == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        cache_logger_on_first_use=True,
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
    )

    # Route stdlib logging into structlog renderer too.
    logging.basicConfig(
        format="%(message)s",
        level=log_level,
        stream=sys.stdout,
        force=True,
    )

    # Bind run_id once so every subsequent log line gets it.
    run_id = cfg.pipeline_run_id or _new_run_id()
    structlog.contextvars.bind_contextvars(run_id=run_id)

    _configured = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a structlog BoundLogger. Ensures configure() ran."""
    configure()
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger(name))


def bind(**kwargs: object) -> None:
    """Bind extra context variables that will appear on every later log line."""
    structlog.contextvars.bind_contextvars(**kwargs)


def unbind(*keys: str) -> None:
    structlog.contextvars.unbind_contextvars(*keys)


def get_run_id() -> str:
    """Return the current pipeline run id (creates one if missing)."""
    configure()
    ctx = structlog.contextvars.get_contextvars()
    return cast(str, ctx.get("run_id", _new_run_id()))
