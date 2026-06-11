"""Chat session persistence + CRUD endpoints (unit 08).

Provides:
  - HTTP routes for session create/list/fetch (POST/GET /api/sessions,
    GET /api/sessions/{id} -> session + messages), per the shared contract.
  - A small persistence interface the chat/SSE engine (unit 07) calls to read
    history and append messages. Kept import-light (no LLM deps) so it can be
    used from either side.

Router mount is the lead's job (message them to add `sessions.router`).
"""

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.chat_models import ChatMessage, ChatSession
from app.condenser import Message, condense_history
from app.config import get_settings
from app.db import get_engine, get_session

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


# ── Schemas (match README: SessionOut, Citation-bearing messages) ───────────


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    citations: list[dict[str, Any]]
    created_at: datetime


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    created_at: datetime


class SessionDetail(SessionOut):
    messages: list[MessageOut]


class CreateSession(BaseModel):
    title: str | None = None


# ── Persistence interface (consumed by unit 07's chat engine) ───────────────


def create_session(db: Session, title: str | None = None) -> ChatSession:
    session = ChatSession(title=title or "New chat")
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session_with_messages(db: Session, session_id: int) -> ChatSession | None:
    """Return the session with its messages eager-ordered, or None."""
    return db.get(ChatSession, session_id)


def list_messages(db: Session, session_id: int) -> list[ChatMessage]:
    return list(
        db.scalars(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at, ChatMessage.id)
        )
    )


def append_message(
    db: Session,
    session_id: int,
    role: str,
    content: str,
    citations: list[dict[str, Any]] | None = None,
) -> ChatMessage:
    """Persist one message and return it.

    The chat engine calls this for the user message before streaming and for the
    assistant message on `done`; the returned `.id` is the SSE `message_id`.
    `citations` is a list of Citation dicts (empty for user turns and refusals).
    """
    message = ChatMessage(
        session_id=session_id,
        role=role,
        content=content,
        citations=citations or [],
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


# ── ChatPersistence implementation (satisfies app.chat.ChatPersistence) ─────
#
# The chat engine (unit 07) depends on a `ChatPersistence` Protocol with str
# session/message ids. This DB-backed class implements that shape on top of the
# integer-keyed ORM, and applies token-budget condensation when serving history.


class DbChatPersistence:
    """Postgres-backed implementation of app.chat.ChatPersistence.

    Opens a short-lived Session per call so it is safe to construct once and
    share (no held connection). Session/message ids are strings at the boundary
    (the chat engine's contract) and integers in the DB.
    """

    def add_user_message(self, session_id: str, content: str) -> str:
        return self._append(session_id, "user", content, [])

    def add_assistant_message(
        self, session_id: str, content: str, citations: list[dict[str, Any]]
    ) -> str:
        return self._append(session_id, "assistant", content, citations)

    def session_history(self, session_id: str) -> list[tuple[str, str]]:
        """Return (role, content) pairs, condensed to the chat token budget."""
        sid = _parse_id(session_id)
        if sid is None:
            return []
        with Session(get_engine()) as db:
            rows = list_messages(db, sid)
        history: list[Message] = [
            {"role": m.role, "content": m.content} for m in rows
        ]
        budget = get_settings().chat_token_budget
        condensed = condense_history(history, budget)
        return [(m["role"], m["content"]) for m in condensed]

    def _append(
        self, session_id: str, role: str, content: str, citations: list[dict[str, Any]]
    ) -> str:
        sid = _parse_id(session_id)
        with Session(get_engine()) as db:
            if sid is None or db.get(ChatSession, sid) is None:
                # The chat engine raises 404 on KeyError for unknown sessions.
                raise KeyError(session_id)
            msg = append_message(db, sid, role, content, citations)
            return str(msg.id)


def _parse_id(session_id: str) -> int | None:
    try:
        return int(session_id)
    except (TypeError, ValueError):
        return None


_db_persistence = DbChatPersistence()


def get_db_persistence() -> DbChatPersistence:
    """Provider the lead wires into app.chat.get_persistence (see main.py)."""
    return _db_persistence


# ── HTTP routes ─────────────────────────────────────────────────────────────


@router.post("", status_code=201, response_model=SessionOut)
def post_session(
    body: CreateSession,
    db: Annotated[Session, Depends(get_session)],
) -> ChatSession:
    return create_session(db, body.title)


@router.get("", response_model=list[SessionOut])
def get_sessions(db: Annotated[Session, Depends(get_session)]) -> list[ChatSession]:
    return list(
        db.scalars(select(ChatSession).order_by(ChatSession.created_at.desc()))
    )


@router.get("/{session_id}", response_model=SessionDetail)
def get_session_detail(
    session_id: int,
    db: Annotated[Session, Depends(get_session)],
) -> SessionDetail:
    session = db.get(ChatSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    messages = list_messages(db, session_id)
    return SessionDetail(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        messages=[MessageOut.model_validate(m) for m in messages],
    )
