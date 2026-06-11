"""Shared fixtures + config for the Playwright end-to-end test.

The e2e runs against the live compose stack (web on :3000, api on :8000), not a
test harness — it proves the real upload → ingest → ask → cited-answer path. Base
URLs are overridable so the same test can run against a remote deployment.
"""

from __future__ import annotations

import os

import pytest

WEB_BASE_URL = os.environ.get("E2E_WEB_URL", "http://localhost:3000")
API_BASE_URL = os.environ.get("E2E_API_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def web_base_url() -> str:
    return WEB_BASE_URL


@pytest.fixture(scope="session")
def api_base_url() -> str:
    return API_BASE_URL
