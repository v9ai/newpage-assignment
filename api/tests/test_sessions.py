from collections.abc import Generator, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import chat_models  # noqa: F401  (registers chat tables on Base.metadata)
from app.config import get_settings
from app.db import get_session
from app.main import app
from app.models import Base
from app.sessions import (
    append_message,
    get_session_with_messages,
    list_messages,
)
from app.sessions import router as sessions_router

# The router mount lives in main.py (the lead's file). Ensure my session CRUD
# routes are present for these tests regardless of mount order during parallel
# development. (chat.py already owns /api/sessions/{id}/messages, so guard on the
# exact create route, not a prefix.)
if not any(getattr(r, "path", "") == "/api/sessions" for r in app.routes):
    app.include_router(sessions_router)


@pytest.fixture
def engine():
    eng = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def client(engine, monkeypatch) -> Iterator[TestClient]:
    get_settings.cache_clear()

    def override() -> Generator[Session]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_create_and_list_sessions(client):
    created = client.post("/api/sessions", json={"title": "My chat"})
    assert created.status_code == 201
    body = created.json()
    assert body["title"] == "My chat"
    assert "id" in body and "created_at" in body

    listed = client.get("/api/sessions")
    assert listed.status_code == 200
    assert any(s["id"] == body["id"] for s in listed.json())


def test_create_session_defaults_title(client):
    created = client.post("/api/sessions", json={})
    assert created.status_code == 201
    assert created.json()["title"] == "New chat"


def test_fetch_session_with_messages(client, engine):
    session_id = client.post("/api/sessions", json={}).json()["id"]

    with Session(engine) as db:
        append_message(db, session_id, "user", "What is in the docs?")
        append_message(
            db,
            session_id,
            "assistant",
            "The docs cover X.",
            citations=[
                {
                    "doc_id": 1,
                    "filename": "a.pdf",
                    "page": 2,
                    "chunk_index": 0,
                    "snippet": "X is described here.",
                }
            ],
        )

    resp = client.get(f"/api/sessions/{session_id}")
    assert resp.status_code == 200
    detail = resp.json()
    assert len(detail["messages"]) == 2
    assert detail["messages"][0]["role"] == "user"
    assert detail["messages"][0]["citations"] == []
    assert detail["messages"][1]["citations"][0]["filename"] == "a.pdf"


def test_fetch_missing_session_404(client):
    assert client.get("/api/sessions/99999").status_code == 404


def test_append_message_returns_id_for_done_event(engine):
    with Session(engine) as db:
        from app.sessions import create_session

        session = create_session(db)
        msg = append_message(db, session.id, "assistant", "hi", citations=[])
        # The returned id is what the SSE `done` event reports as message_id.
        assert isinstance(msg.id, int)
        assert msg.id > 0


def test_messages_ordered_chronologically(engine):
    with Session(engine) as db:
        from app.sessions import create_session

        session = create_session(db)
        for i in range(5):
            append_message(db, session.id, "user", f"q{i}")
        msgs = list_messages(db, session.id)
        assert [m.content for m in msgs] == [f"q{i}" for i in range(5)]


def test_get_session_with_messages_relationship(engine):
    with Session(engine) as db:
        from app.sessions import create_session

        session = create_session(db)
        append_message(db, session.id, "user", "hello")
        fetched = get_session_with_messages(db, session.id)
        assert fetched is not None
        assert len(fetched.messages) == 1
        assert fetched.messages[0].content == "hello"
