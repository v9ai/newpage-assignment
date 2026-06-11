"""In-process rate limiter for the chat endpoint.

A single-node compose deployment doesn't need Redis; a sliding-window counter
keyed by client ip is enough to keep one client from hammering the LLM (which
costs money and is the slowest dependency). On limit, raise a 429 with a
`Retry-After` header — a designed error, surfaced cleanly to the UI.

If the app is ever scaled to multiple api replicas this becomes per-replica and
should move to a shared store; that trade-off is documented in the README.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request


class SlidingWindowLimiter:
    """Allow at most `max_requests` per `window_seconds` per key (thread-safe)."""

    def __init__(self, max_requests: int, window_seconds: float) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        """Record a hit for `key`; raise HTTP 429 if the window is full."""
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] < cutoff:
                hits.popleft()
            if len(hits) >= self.max_requests:
                retry_after = max(1, int(hits[0] + self.window_seconds - now) + 1)
                raise HTTPException(
                    status_code=429,
                    detail="Too many chat requests — slow down and retry shortly.",
                    headers={"Retry-After": str(retry_after)},
                )
            hits.append(now)
            # Opportunistic cleanup so idle keys don't accumulate forever.
            if not hits:
                del self._hits[key]


def client_key(request: Request) -> str:
    """Identify the caller by client ip (best-effort; honors no proxy headers)."""
    return request.client.host if request.client else "unknown"


# Default budget for the chat endpoint: 20 messages/minute/client. Tunable here;
# kept conservative because each call fans out to retrieval + an LLM completion.
chat_limiter = SlidingWindowLimiter(max_requests=20, window_seconds=60.0)


def enforce_chat_rate_limit(request: Request) -> None:
    """FastAPI dependency: rate-limit the chat endpoint per client."""
    chat_limiter.check(client_key(request))
