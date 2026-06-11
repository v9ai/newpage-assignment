"""Dependency-outage sweep: stop each backing service and prove the api degrades
to a designed, user-readable error — never a blank screen or a raw 500.

This is DESTRUCTIVE to the running stack (it stops/starts containers), so it is
opt-in: it only runs when `RUN_OUTAGE_SWEEP=1` is set. The default `make e2e`
skips it; CI or a manual hardening pass runs it explicitly. Each test restores
the service it stopped in a finally-block so a failure can't leave the stack
wedged.

What "designed error" means here, proven by the middleware + health probes:
- `/api/health` always returns 200 and flips the affected dependency to "error"
  (graceful degradation — the UI can show which dependency is down).
- An endpoint that hard-depends on the downed service returns the middleware's
  clean JSON `{detail, request_id}` (a correlated error an operator can grep),
  not a stack trace.
"""

from __future__ import annotations

import os
import subprocess
import time
from collections.abc import Iterator
from contextlib import contextmanager

import httpx
import pytest

RUN = os.environ.get("RUN_OUTAGE_SWEEP") == "1"
pytestmark = pytest.mark.skipif(
    not RUN, reason="set RUN_OUTAGE_SWEEP=1 to run the destructive outage sweep"
)

COMPOSE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECOVER_TIMEOUT_S = 30


def _compose(*args: str) -> None:
    subprocess.run(
        ["docker", "compose", *args], cwd=COMPOSE_DIR, check=True, capture_output=True
    )


def _health(api_base_url: str) -> dict:
    return httpx.get(f"{api_base_url}/api/health", timeout=5).json()


def _wait_until_ok(api_base_url: str, service: str) -> None:
    deadline = time.monotonic() + RECOVER_TIMEOUT_S
    while time.monotonic() < deadline:
        try:
            if _health(api_base_url)["services"][service] == "ok":
                return
        except httpx.HTTPError:
            pass
        time.sleep(1)
    raise AssertionError(f"{service} did not recover to ok within {RECOVER_TIMEOUT_S}s")


@contextmanager
def _stopped(api_base_url: str, service: str, health_key: str) -> Iterator[None]:
    """Stop `service` for the duration of the block, then restart + wait for ok."""
    _compose("stop", service)
    try:
        # Give the api a moment to observe the dependency drop.
        time.sleep(2)
        yield
    finally:
        _compose("start", service)
        _wait_until_ok(api_base_url, health_key)


@pytest.fixture(scope="module")
def _require_stack(api_base_url: str) -> None:
    try:
        if httpx.get(f"{api_base_url}/api/health", timeout=3).status_code != 200:
            pytest.skip("stack not healthy")
    except httpx.HTTPError:
        pytest.skip("compose stack not reachable — run `docker compose up` first")


@pytest.mark.usefixtures("_require_stack")
def test_qdrant_down_degrades_cleanly(api_base_url: str) -> None:
    with _stopped(api_base_url, "qdrant", "qdrant"):
        health = _health(api_base_url)
        assert health["services"]["qdrant"] == "error"  # health stays 200, flags it
        # An endpoint that needs Qdrant returns a clean, correlated error.
        r = httpx.post(f"{api_base_url}/api/retrieve", json={"query": "x"}, timeout=10)
        assert r.status_code in (500, 503)
        body = r.json()
        assert body.get("detail")  # human-readable
        assert body.get("request_id")  # greppable in logs
        assert "Traceback" not in r.text  # no stack trace leaked


@pytest.mark.usefixtures("_require_stack")
def test_postgres_down_degrades_cleanly(api_base_url: str) -> None:
    with _stopped(api_base_url, "postgres", "postgres"):
        health = _health(api_base_url)
        assert health["services"]["postgres"] == "error"
        # Listing documents needs Postgres — must be a clean error, not a crash.
        r = httpx.get(f"{api_base_url}/api/documents", timeout=10)
        assert r.status_code in (500, 503)
        assert r.json().get("detail")
        assert "Traceback" not in r.text


@pytest.mark.usefixtures("_require_stack")
def test_health_endpoint_survives_any_outage(api_base_url: str) -> None:
    """/api/health itself must never 500, whichever store is down."""
    for service in ("qdrant", "postgres"):
        with _stopped(api_base_url, service, service):
            r = httpx.get(f"{api_base_url}/api/health", timeout=5)
            assert r.status_code == 200, f"health 500'd with {service} down"
            assert r.json()["services"][service] == "error"
