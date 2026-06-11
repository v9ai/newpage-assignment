"""End-to-end: upload a document, wait for ingestion, ask a question, assert a
cited answer streams back.

Runs against the live compose stack. The happy path is driven primarily through
the API contract (stable, documented in specs/units/README.md) with the browser
UI exercised for upload + the rendered cited answer. We intentionally avoid
brittle CSS selectors: the UI is reached by role/text, and the core assertions
(ingestion reaching `ready`, a cited answer with non-empty citations) go through
the API so the test is meaningful the moment the stack is integrated.

Skips cleanly (not fails) if the stack isn't up, so `make test` in a bare
checkout stays green — `make e2e` is the gate that requires the running stack.
"""

from __future__ import annotations

import io
import json
import re
import time

import httpx
import pytest
from playwright.sync_api import expect

# The sample fact must be specific enough that a grounded answer is unambiguous
# and a refusal (no citations) would be obviously wrong.
SAMPLE_FILENAME = "e2e-fixture.md"
SAMPLE_TEXT = (
    "# DocChat E2E Fixture\n\n"
    "The internal codename for the DocChat ingestion pipeline is Project Lighthouse.\n"
    "Project Lighthouse was approved on the seventh of March.\n"
)
QUESTION = "What is the internal codename for the ingestion pipeline?"
EXPECTED_SUBSTRING = "lighthouse"

INGEST_TIMEOUT_S = 60
POLL_INTERVAL_S = 1.0


def _stack_up(api_base_url: str) -> bool:
    try:
        r = httpx.get(f"{api_base_url}/api/health", timeout=3)
        return r.status_code == 200
    except httpx.HTTPError:
        return False


@pytest.fixture(scope="module")
def _require_stack(api_base_url: str) -> None:
    if not _stack_up(api_base_url):
        pytest.skip(
            "compose stack not reachable on the e2e URLs — run `docker compose up` first"
        )


@pytest.fixture(scope="module")
def _require_chat(api_base_url: str) -> None:
    """Skip the chat path until the sessions router is mounted (units 07/08)."""
    try:
        r = httpx.post(f"{api_base_url}/api/sessions", json={}, timeout=5)
    except httpx.HTTPError:
        pytest.skip("compose stack not reachable")
    if r.status_code == 404:
        pytest.skip("chat/sessions endpoints not yet mounted (units 07/08 pending)")


def _upload_and_ingest(api_base_url: str) -> int:
    """Upload the fixture and return its document id once ingestion is `ready`."""
    files = {"file": (SAMPLE_FILENAME, io.BytesIO(SAMPLE_TEXT.encode()), "text/markdown")}
    resp = httpx.post(f"{api_base_url}/api/documents", files=files, timeout=30)
    assert resp.status_code == 201, resp.text
    doc_id = resp.json()["id"]

    deadline = time.monotonic() + INGEST_TIMEOUT_S
    while time.monotonic() < deadline:
        listing = httpx.get(f"{api_base_url}/api/documents", timeout=10).json()
        doc = next((d for d in listing if d["id"] == doc_id), None)
        assert doc is not None, "uploaded document vanished from the listing"
        if doc["status"] == "ready":
            return doc_id
        assert doc["status"] != "failed", f"ingestion failed: {doc.get('failure_reason')}"
        time.sleep(POLL_INTERVAL_S)
    raise AssertionError(f"document {doc_id} did not reach 'ready' within {INGEST_TIMEOUT_S}s")


def _ask_and_collect(api_base_url: str, question: str) -> tuple[str, list[dict]]:
    """Drive one chat turn over SSE; return (answer_text, citations)."""
    session = httpx.post(f"{api_base_url}/api/sessions", json={}, timeout=10).json()
    session_id = session["id"]

    answer_parts: list[str] = []
    citations: list[dict] = []
    with httpx.stream(
        "POST",
        f"{api_base_url}/api/sessions/{session_id}/messages",
        json={"content": question},
        timeout=120,
    ) as r:
        assert r.status_code == 200, r.read().decode()
        event: str | None = None
        for line in r.iter_lines():
            if line.startswith("event:"):
                event = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data = json.loads(line.split(":", 1)[1].strip())
                if event == "token":
                    answer_parts.append(data.get("delta", ""))
                elif event == "citations":
                    citations = data.get("citations", [])
    return "".join(answer_parts), citations


@pytest.mark.usefixtures("_require_stack", "_require_chat")
def test_upload_ingest_ask_cited_answer(api_base_url: str) -> None:
    """The core happy path, asserted through the API contract."""
    _upload_and_ingest(api_base_url)
    answer, citations = _ask_and_collect(api_base_url, QUESTION)

    assert EXPECTED_SUBSTRING in answer.lower(), f"answer was not grounded: {answer!r}"
    assert citations, "a grounded answer must carry at least one citation"
    assert any(SAMPLE_FILENAME in (c.get("filename") or "") for c in citations)


@pytest.mark.usefixtures("_require_stack")
def test_landing_page_loads_in_browser(web_base_url: str, page) -> None:  # type: ignore[no-untyped-def]
    """The SPA loads and shows live service health — smoke check of the web tier."""
    page.goto(web_base_url)
    # Brand is present and the health badge resolved to a non-error state.
    page.wait_for_load_state("networkidle")
    assert "DocChat" in page.content()


@pytest.mark.usefixtures("_require_stack", "_require_chat")
def test_chat_ui_streams_cited_answer(api_base_url: str, web_base_url: str, page) -> None:  # type: ignore[no-untyped-def]
    """The unit-08 browser walkthrough: type a question in the composer, watch
    the grounded answer stream into the DOM, then open a citation's source
    preview and confirm it shows the exact fixture passage."""
    _upload_and_ingest(api_base_url)

    page.goto(web_base_url)
    chat_panel = page.get_by_role("region", name="Chat")
    composer = chat_panel.get_by_label("Message", exact=True)
    # The composer unblocks once the document list confirms an upload exists.
    expect(composer).to_be_enabled(timeout=15_000)
    composer.fill(QUESTION)
    composer.press("Enter")

    # The user bubble renders immediately. Use .first: a persisted prior turn
    # with the same question (DB history is restored on load) can make the text
    # match more than once, which would trip Playwright's strict mode.
    expect(chat_panel.get_by_text(QUESTION).first).to_be_visible()

    # Citation chips appear only after the stream's `citations` event, so their
    # arrival means the turn finished AND was grounded. Generous timeout: the
    # answer comes from the live LLM.
    chip = chat_panel.get_by_role(
        "button", name=re.compile(re.escape(SAMPLE_FILENAME))
    ).first
    expect(chip).to_be_visible(timeout=120_000)
    expect(
        chat_panel.get_by_text(re.compile(EXPECTED_SUBSTRING, re.IGNORECASE)).first
    ).to_be_visible()

    # Chip click -> source preview slide-over with the fixture passage.
    chip.click()
    dialog = page.get_by_role("dialog")
    expect(dialog).to_be_visible()
    expect(dialog).to_contain_text(SAMPLE_FILENAME)
    expect(dialog).to_contain_text(re.compile("lighthouse", re.IGNORECASE))
    page.keyboard.press("Escape")
    expect(dialog).not_to_be_visible()


@pytest.mark.usefixtures("_require_stack", "_require_chat")
def test_reload_restores_session_and_messages(api_base_url: str, web_base_url: str, page) -> None:  # type: ignore[no-untyped-def]
    """Unit-08 done-when: conversations survive reloads. Drive a turn through
    the API (persisting it server-side), then load the UI fresh and expect the
    most recent session's messages — citations included — to be restored."""
    _upload_and_ingest(api_base_url)
    question = "When was Project Lighthouse approved?"
    answer, citations = _ask_and_collect(api_base_url, question)
    assert answer, "the API turn produced no answer to restore"

    page.goto(web_base_url)
    chat_panel = page.get_by_role("region", name="Chat")
    # The newest session is auto-selected; both turns are restored from the DB.
    expect(chat_panel.get_by_text(question)).to_be_visible(timeout=15_000)
    if citations:
        # Persisted citations re-render as chips on the restored answer.
        expect(
            chat_panel.get_by_role(
                "button", name=re.compile(re.escape(SAMPLE_FILENAME))
            ).first
        ).to_be_visible()
