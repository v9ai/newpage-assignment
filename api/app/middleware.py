"""Request-scoped observability middleware.

Generates (or honors an inbound `X-Request-ID`) a request id at the edge, binds
it into structlog's contextvars so every log line emitted while handling the
request carries it, echoes it back as a response header, and logs one
`request_completed` record with method, path, status, and latency.

It also converts an unhandled exception into a clean JSON 500 with the request
id, so the client never sees a raw stack trace or a blank screen and an operator
can grep the logs by that id to find the full context.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

log = structlog.get_logger()

REQUEST_ID_HEADER = "X-Request-ID"

# Header name LlamaIndex/OpenAI outbound calls can forward so a request id
# propagates into the provider's trace too (set on the openai client / httpx).
PROPAGATION_HEADER = REQUEST_ID_HEADER


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Bind a request id, time the request, and never leak a raw 500."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        structlog.contextvars.bind_contextvars(request_id=request_id)
        # Expose it to handlers (e.g. to forward to the OpenAI client).
        request.state.request_id = request_id

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            log.exception(
                "request_failed",
                method=request.method,
                path=request.url.path,
                latency_ms=elapsed_ms,
            )
            structlog.contextvars.clear_contextvars()
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error.",
                    "request_id": request_id,
                },
                headers={REQUEST_ID_HEADER: request_id},
            )

        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers[REQUEST_ID_HEADER] = request_id
        log.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            latency_ms=elapsed_ms,
        )
        structlog.contextvars.clear_contextvars()
        return response
