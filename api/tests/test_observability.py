"""Tests for the observability + hardening modules (unit 10).

Covers: secret redaction in logs, request-id propagation + clean 500s in the
middleware, and the sliding-window rate limiter on the chat endpoint.
"""

from __future__ import annotations

import json
import time

import pytest
import structlog
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient

from app.logging import _OPENAI_KEY_RE, redact_secrets
from app.middleware import REQUEST_ID_HEADER, RequestContextMiddleware
from app.ratelimit import SlidingWindowLimiter, enforce_chat_rate_limit


# --- logging: redaction ---------------------------------------------------


def test_redacts_secret_field_names() -> None:
    out = redact_secrets(None, "info", {"openai_api_key": "sk-proj-abc123", "x": 1})
    assert out["openai_api_key"] == "[REDACTED]"
    assert out["x"] == 1


def test_redacts_embedded_key_in_string_value() -> None:
    out = redact_secrets(None, "info", {"msg": "calling with sk-proj-ABCDEFGH1234 now"})
    assert "sk-proj" not in out["msg"]
    assert "[REDACTED]" in out["msg"]


def test_redacts_keys_nested_in_containers() -> None:
    out = redact_secrets(
        None,
        "info",
        {"items": ["ok", "sk-livedeadbeef0000", {"inner": "sk-anotherKEY99999"}]},
    )
    assert "sk-live" not in json.dumps(out)
    assert "sk-another" not in json.dumps(out)


def test_key_regex_ignores_ordinary_text() -> None:
    assert _OPENAI_KEY_RE.search("the quick brown fox") is None


# --- middleware: request id + clean errors --------------------------------


def _app_with_middleware() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)

    @app.get("/ok")
    def ok(request: Request) -> dict[str, str]:
        return {"rid": request.state.request_id}

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("kaboom")

    return app


def test_generates_and_echoes_request_id() -> None:
    client = TestClient(_app_with_middleware())
    resp = client.get("/ok")
    assert resp.status_code == 200
    rid = resp.headers[REQUEST_ID_HEADER]
    assert rid
    # Handler saw the same id that came back on the header.
    assert resp.json()["rid"] == rid


def test_honors_inbound_request_id() -> None:
    client = TestClient(_app_with_middleware())
    resp = client.get("/ok", headers={REQUEST_ID_HEADER: "trace-abc"})
    assert resp.headers[REQUEST_ID_HEADER] == "trace-abc"
    assert resp.json()["rid"] == "trace-abc"


def test_unhandled_error_becomes_clean_500_with_request_id() -> None:
    client = TestClient(_app_with_middleware(), raise_server_exceptions=False)
    resp = client.get("/boom")
    assert resp.status_code == 500
    body = resp.json()
    assert body["detail"] == "Internal server error."
    assert body["request_id"] == resp.headers[REQUEST_ID_HEADER]
    # No stack trace leaked to the client.
    assert "kaboom" not in resp.text


def test_context_cleared_between_requests() -> None:
    client = TestClient(_app_with_middleware())
    r1 = client.get("/ok", headers={REQUEST_ID_HEADER: "first"})
    r2 = client.get("/ok")
    assert r1.headers[REQUEST_ID_HEADER] == "first"
    assert r2.headers[REQUEST_ID_HEADER] != "first"
    # Contextvars must not leak the previous id after the request finished.
    assert structlog.contextvars.get_contextvars().get("request_id") is None


# --- rate limiter ---------------------------------------------------------


def test_limiter_allows_up_to_max_then_blocks() -> None:
    limiter = SlidingWindowLimiter(max_requests=3, window_seconds=60.0)
    for _ in range(3):
        limiter.check("ip-1")
    with pytest.raises(Exception) as exc:
        limiter.check("ip-1")
    assert getattr(exc.value, "status_code", None) == 429
    assert "Retry-After" in getattr(exc.value, "headers", {})


def test_limiter_is_per_key() -> None:
    limiter = SlidingWindowLimiter(max_requests=1, window_seconds=60.0)
    limiter.check("ip-a")
    # Different key has its own budget.
    limiter.check("ip-b")


def test_limiter_window_slides() -> None:
    limiter = SlidingWindowLimiter(max_requests=1, window_seconds=0.2)
    limiter.check("ip-x")
    time.sleep(0.25)
    # Window elapsed — the old hit aged out, so this is allowed again.
    limiter.check("ip-x")


def test_chat_dependency_enforces_limit_via_429() -> None:
    app = FastAPI()

    @app.get("/chat", dependencies=[Depends(enforce_chat_rate_limit)])
    def chat() -> dict[str, bool]:
        return {"ok": True}

    # Shrink the shared limiter so the test is fast and deterministic.
    from app import ratelimit

    ratelimit.chat_limiter = SlidingWindowLimiter(max_requests=2, window_seconds=60.0)

    client = TestClient(app)
    assert client.get("/chat").status_code == 200
    assert client.get("/chat").status_code == 200
    blocked = client.get("/chat")
    assert blocked.status_code == 429
    assert blocked.headers.get("Retry-After")
