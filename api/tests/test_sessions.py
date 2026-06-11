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
    # Pop only what this fixture set — clear() would also strip main.py's
    # production wiring (chat get_persistence -> DB) for later tests.
    app.dependency_overrides.pop(get_session, None)
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


def test_db_persistence_round_trip(client, engine, monkeypatch):
    """DbChatPersistence (what the chat engine calls) persists a full turn that
    the session API then reads back — i.e. a browser reload restores it."""
    from app.sessions import DbChatPersistence

    # DbChatPersistence opens its own Session via get_engine(); point it at the
    # test engine (patch both the source and the name imported into sessions).
    monkeypatch.setattr("app.db.get_engine", lambda: engine)
    monkeypatch.setattr("app.sessions.get_engine", lambda: engine)

    session_id = client.post("/api/sessions", json={}).json()["id"]
    persistence = DbChatPersistence()

    # Mirror the SSE endpoint: record the user turn, then the assistant turn.
    user_mid = persistence.add_user_message(str(session_id), "What about revenue?")
    citations = [
        {
            "doc_id": "1",
            "filename": "q3.pdf",
            "page": 4,
            "chunk_index": 2,
            "snippet": "Revenue rose 23%.",
        }
    ]
    asst_mid = persistence.add_assistant_message(
        str(session_id), "Revenue rose 23% YoY.", citations
    )
    assert user_mid != asst_mid  # distinct message ids (the done event's id)

    # History (condensed) reads back in order.
    history = persistence.session_history(str(session_id))
    assert ("user", "What about revenue?") in history
    assert ("assistant", "Revenue rose 23% YoY.") in history

    # And the session API returns the persisted turn with its citations.
    detail = client.get(f"/api/sessions/{session_id}").json()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]
    assert detail["messages"][1]["citations"][0]["filename"] == "q3.pdf"


def test_db_persistence_unknown_session_raises_keyerror(engine, monkeypatch):
    from app.sessions import DbChatPersistence

    monkeypatch.setattr("app.sessions.get_engine", lambda: engine)
    persistence = DbChatPersistence()
    # The chat endpoint maps this KeyError to a 404.
    with pytest.raises(KeyError):
        persistence.add_user_message("999999", "hi")
