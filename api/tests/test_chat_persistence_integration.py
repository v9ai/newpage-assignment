"""HTTP-level integration of the chat engine with DB persistence (units 07+08).

test_chat.py exercises the SSE generator against the in-memory stub and
test_sessions.py exercises DbChatPersistence directly; this file covers the
seam between them as main.py wires it: a POST to the messages endpoint streams
SSE while persisting both turns, the session API reads the turn back, unknown
sessions surface as a clean 404, and history served to the engine respects the
condensation budget. Runs on sqlite — no Postgres/Qdrant/OpenAI needed.
"""

import json
from collections.abc import AsyncIterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import chat
from app import sessions as sessions_mod
from app.chat import get_persistence
from app.db import get_session
from app.main import app
from app.models import Base
from app.retrieval import RetrievedNode
from app.sessions import DbChatPersistence, create_session, get_db_persistence

# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def engine(monkeypatch):
    eng = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(eng)
    # DbChatPersistence opens its own Session via the name imported into
    # app.sessions; route handlers go through the get_session dependency.
    monkeypatch.setattr(sessions_mod, "get_engine", lambda: eng)
    return eng


@pytest.fixture
def client(engine):
    def override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override
    app.dependency_overrides[get_persistence] = lambda: DbChatPersistence()
    yield TestClient(app)
    app.dependency_overrides.pop(get_session, None)
    # Restore main.py's production wiring rather than clearing it away.
    app.dependency_overrides[get_persistence] = get_db_persistence


# ── Stubs (no OpenAI/Qdrant) ────────────────────────────────────────────────


def _node(text: str, chunk_index: int = 0) -> RetrievedNode:
    return RetrievedNode(
        text=text,
        score=0.9,
        doc_id="doc-1",
        filename="handbook.md",
        page=3,
        chunk_index=chunk_index,
    )


class _FakeChunk:
    def __init__(self, delta: str) -> None:
        self.delta = delta


class _FakeLLM:
    def __init__(self, deltas: list[str]) -> None:
        self._deltas = deltas

    async def astream_chat(self, _messages: object) -> AsyncIterator[_FakeChunk]:
        async def _gen() -> AsyncIterator[_FakeChunk]:
            for d in self._deltas:
                yield _FakeChunk(d)

        return _gen()


def _parse_sse(text: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    event: str | None = None
    for line in text.splitlines():
        if line.startswith("event:"):
            event = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            events.append((event or "", json.loads(line.split(":", 1)[1].strip())))
    return events


# ── Tests ───────────────────────────────────────────────────────────────────


def test_main_wires_db_persistence() -> None:
    """main.py must serve chat from Postgres, not chat.py's in-memory stub."""
    assert app.dependency_overrides.get(get_persistence) is get_db_persistence


def test_post_message_streams_and_persists_turn(client, engine, monkeypatch) -> None:
    monkeypatch.setattr(chat, "search", lambda *a, **k: [_node("Vacation accrues monthly.")])
    deltas = ["Vacation ", "accrues ", "monthly [1]."]
    monkeypatch.setattr(chat, "get_llm", lambda _s: _FakeLLM(deltas))

    session_id = client.post("/api/sessions", json={}).json()["id"]
    resp = client.post(
        f"/api/sessions/{session_id}/messages",
        json={"content": "How does vacation accrue?"},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse(resp.text)
    answer = "".join(d["delta"] for e, d in events if e == "token")
    assert answer == "Vacation accrues monthly [1]."
    done = next(d for e, d in events if e == "done")

    # Both turns landed in the DB, and the done event reports the assistant row id.
    detail = client.get(f"/api/sessions/{session_id}").json()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]
    assert detail["messages"][0]["content"] == "How does vacation accrue?"
    assert detail["messages"][1]["content"] == answer
    assert detail["messages"][1]["citations"][0]["filename"] == "handbook.md"
    assert str(detail["messages"][1]["id"]) == done["message_id"]


def test_refusal_turn_persists_without_citations(client, monkeypatch) -> None:
    monkeypatch.setattr(chat, "search", lambda *a, **k: [])

    session_id = client.post("/api/sessions", json={}).json()["id"]
    resp = client.post(
        f"/api/sessions/{session_id}/messages",
        json={"content": "What is the capital of Mars?"},
    )
    events = _parse_sse(resp.text)
    assert next(d for e, d in events if e == "citations")["citations"] == []

    detail = client.get(f"/api/sessions/{session_id}").json()
    assert detail["messages"][1]["citations"] == []
    assert "couldn't find" in detail["messages"][1]["content"].lower()


@pytest.mark.parametrize("session_id", ["424242", "not-a-number"])
def test_post_message_unknown_session_is_404(client, session_id) -> None:
    """KeyError from DbChatPersistence maps to a clean 404, and nothing streams."""
    resp = client.post(f"/api/sessions/{session_id}/messages", json={"content": "hello?"})
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Session not found."


def test_session_history_respects_condensation_budget(engine, monkeypatch) -> None:
    """The history served to the chat engine stays within chat_token_budget:
    newest turns verbatim, older turns folded into one summary message."""

    class _TinyBudget:
        chat_token_budget = 40

    monkeypatch.setattr(sessions_mod, "get_settings", lambda: _TinyBudget())

    with Session(engine) as db:
        session_id = create_session(db).id
    persistence = DbChatPersistence()
    for i in range(10):
        persistence.add_user_message(str(session_id), f"question number {i}, padded out a bit")
        persistence.add_assistant_message(
            str(session_id), f"answer number {i}, padded out a bit", []
        )

    history = persistence.session_history(str(session_id))
    assert len(history) < 20
    roles = [r for r, _ in history]
    assert roles[0] == "system"  # summary stands in for the dropped older turns
    assert "earlier" in history[0][1].lower()
    assert history[-1] == ("assistant", "answer number 9, padded out a bit")


def test_session_history_empty_for_unknown_or_malformed_id(engine) -> None:
    persistence = DbChatPersistence()
    assert persistence.session_history("424242") == []
    assert persistence.session_history("not-a-number") == []
