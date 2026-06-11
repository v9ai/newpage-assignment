"""Structured JSON logging for the api.

One line of config (`configure_logging`) wires structlog to emit single-line
JSON to stdout — the format compose, Docker, and any log shipper expect. Every
record carries whatever is bound to the contextvar-backed context (the request
id, set by the middleware), so a whole request's logs are greppable by one id.

A redaction processor strips the OpenAI key from any event before it is
rendered, so a stray `log.info("...", api_key=settings.openai_api_key)` or an
exception repr that embeds the key can never leak it to the logs.
"""

from __future__ import annotations

import logging
import re
import sys
from typing import Any

import structlog
from structlog.contextvars import merge_contextvars
from structlog.types import EventDict, WrappedLogger

# Matches an OpenAI-style secret key (`sk-...`, including project keys `sk-proj-...`).
# Used as a defense-in-depth net for keys that slip into log values or tracebacks.
_OPENAI_KEY_RE = re.compile(r"sk-[A-Za-z0-9_-]{8,}")
_REDACTED = "[REDACTED]"

# Field names whose values are always secret regardless of content.
_SECRET_KEYS = {"openai_api_key", "api_key", "authorization", "token"}


def _redact_value(value: Any) -> Any:
    """Recursively replace any embedded OpenAI key in strings/containers."""
    if isinstance(value, str):
        return _OPENAI_KEY_RE.sub(_REDACTED, value)
    if isinstance(value, dict):
        return {k: _redact_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return type(value)(_redact_value(v) for v in value)
    return value


def redact_secrets(
    _logger: WrappedLogger, _method: str, event_dict: EventDict
) -> EventDict:
    """structlog processor: scrub secret fields and any `sk-` token in values."""
    for key in list(event_dict.keys()):
        if key.lower() in _SECRET_KEYS:
            event_dict[key] = _REDACTED
        else:
            event_dict[key] = _redact_value(event_dict[key])
    return event_dict


def configure_logging(level: str = "INFO") -> None:
    """Configure structlog + stdlib logging to emit JSON to stdout.

    Idempotent: safe to call once at startup. Routes uvicorn's stdlib loggers
    through the same JSON renderer so every line in the container is parseable.
    """
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    shared_processors: list[Any] = [
        merge_contextvars,
        structlog.processors.add_log_level,
        timestamper,
        redact_secrets,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    min_level = logging.getLevelNamesMapping().get(level.upper(), logging.INFO)
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(min_level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Bridge stdlib logging (uvicorn, sqlalchemy) into the same JSON output.
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(min_level)
    # uvicorn installs its own handlers; clear them so lines aren't doubled.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers = []
        lg.propagate = True


def get_logger(*args: Any, **kwargs: Any) -> Any:
    """Thin re-export so call sites import from one place."""
    return structlog.get_logger(*args, **kwargs)
