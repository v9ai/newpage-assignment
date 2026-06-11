"""Grounded, cited, streaming chat over retrieved document context.

Pipeline per user turn: retrieve top-k chunks (with the score threshold that
powers the refusal path) -> build a grounded prompt that cites sources inline ->
stream the answer from the configured OpenAI model as Server-Sent Events.

SSE contract (named events, JSON data):
  token     {"delta": "..."}        repeated, the streamed answer text
  citations {"citations": [Citation]} the sources backing the answer
  error     {"message": "..."}       a failure during generation
  done      {"message_id": "...", "usage": {...}}

A refusal ("not in the documents") is a normal token-streamed answer with an
empty citations list on done — no separate event type.
"""

import json
from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Annotated, Any, Protocol

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from app.config import Settings, get_settings
from app.prompts import REFUSAL_TEXT, SYSTEM_PROMPT, ContextChunk, build_user_turn
from app.ratelimit import enforce_chat_rate_limit
from app.retrieval import RetrievedNode, search

log = structlog.get_logger()

router = APIRouter(prefix="/api", tags=["chat"])

# Guardrail: cap question length before it reaches retrieval/the model. Unit 09
# tightens input sanitization; this is the baseline server-side limit.
MAX_QUESTION_CHARS = 4000


class Citation(BaseModel):
    doc_id: str
    filename: str
    page: int | None
    chunk_index: int
    snippet: str


class MessageIn(BaseModel):
    content: str = Field(min_length=1)


# --- Persistence boundary (implemented by unit 08; stubbed here) ---------------


class ChatPersistence(Protocol):
    """How the chat engine records turns and reads history.

    Unit 08 supplies a Postgres-backed implementation; until then the in-memory
    stub below satisfies the same shape so the SSE endpoint is fully testable.
    """

    def add_user_message(self, session_id: str, content: str) -> str: ...

    def add_assistant_message(
        self, session_id: str, content: str, citations: list[dict[str, Any]]
    ) -> str: ...

    def session_history(self, session_id: str) -> list[tuple[str, str]]: ...


class InMemoryPersistence:
    """Process-local stand-in for unit 08's DB persistence.

    Auto-creates a session on first use so the endpoint works against a stub
    session id before unit 08's session routes exist.
    """

    def __init__(self) -> None:
        self._messages: dict[str, list[tuple[str, str, str]]] = {}
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"msg-{self._counter}"

    def add_user_message(self, session_id: str, content: str) -> str:
        mid = self._next_id()
        self._messages.setdefault(session_id, []).append((mid, "user", content))
        return mid

    def add_assistant_message(
        self, session_id: str, content: str, citations: list[dict[str, Any]]
    ) -> str:
        mid = self._next_id()
        self._messages.setdefault(session_id, []).append((mid, "assistant", content))
        return mid

    def session_history(self, session_id: str) -> list[tuple[str, str]]:
        return [(role, content) for _id, role, content in self._messages.get(session_id, [])]


@lru_cache
def _stub_persistence() -> InMemoryPersistence:
    return InMemoryPersistence()


def get_persistence() -> ChatPersistence:
    """FastAPI dependency for the persistence layer.

    Returns unit 08's Postgres-backed DbChatPersistence (which satisfies the
    ChatPersistence Protocol and persists messages + citations). Falls back to
    the in-memory stub only if the sessions module is unavailable, so the chat
    engine still streams in isolation (e.g. unit tests of this module alone).
    """
    try:
        from app.sessions import get_db_persistence
    except Exception:
        return _stub_persistence()
    return get_db_persistence()


# --- Model / citation plumbing -------------------------------------------------


@lru_cache
def _llm(base_url: str, model: str, api_key: str) -> Any:
    from llama_index.llms.openai import OpenAI

    return OpenAI(model=model, api_key=api_key, api_base=base_url)


def get_llm(settings: Settings) -> Any:
    return _llm(settings.llm_base_url, settings.llm_model, settings.openai_api_key)


def _snippet(text: str, limit: int = 300) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def build_citations(nodes: list[RetrievedNode]) -> list[Citation]:
    return [
        Citation(
            doc_id=n.doc_id,
            filename=n.filename,
            page=n.page,
            chunk_index=n.chunk_index,
            snippet=_snippet(n.text),
        )
        for n in nodes
    ]


def context_chunks(nodes: list[RetrievedNode]) -> list[ContextChunk]:
    return [
        ContextChunk(number=i + 1, filename=n.filename, page=n.page, text=n.text)
        for i, n in enumerate(nodes)
    ]


def _sse(event: str, data: dict[str, Any]) -> dict[str, str]:
    return {"event": event, "data": json.dumps(data)}


async def stream_answer(
    session_id: str,
    question: str,
    persistence: ChatPersistence,
    settings: Settings | None = None,
) -> AsyncIterator[dict[str, str]]:
    """Yield SSE events for one user turn: tokens, then citations, then done."""
    settings = settings or get_settings()

    nodes = search(question, apply_threshold=True)
    chunks = context_chunks(nodes)
    citations = build_citations(nodes)

    from llama_index.core.llms import ChatMessage, MessageRole

    # Prior turns for multi-turn context. post_message persists the current user
    # message *before* streaming, so session_history()'s last entry is this same
    # turn — drop it here and re-add it below with its retrieved context attached.
    # session_history already applies the token-budget condensation (unit 08).
    role_map = {"user": MessageRole.USER, "assistant": MessageRole.ASSISTANT}
    history = persistence.session_history(session_id)
    if history and history[-1][0] == "user" and history[-1][1].strip() == question:
        history = history[:-1]

    messages = [ChatMessage(role=MessageRole.SYSTEM, content=SYSTEM_PROMPT)]
    for role, content in history:
        messages.append(
            ChatMessage(role=role_map.get(role, MessageRole.USER), content=content)
        )
    messages.append(
        ChatMessage(role=MessageRole.USER, content=build_user_turn(question, chunks))
    )

    parts: list[str] = []
    try:
        if not nodes:
            # No context cleared the threshold: emit the refusal deterministically
            # rather than spending a model call to (hopefully) say the same thing.
            for piece in (REFUSAL_TEXT,):
                parts.append(piece)
                yield _sse("token", {"delta": piece})
        else:
            llm = get_llm(settings)
            response_gen = await llm.astream_chat(messages)
            async for chunk in response_gen:
                delta = chunk.delta or ""
                if not delta:
                    continue
                parts.append(delta)
                yield _sse("token", {"delta": delta})
    except Exception as exc:  # surface generation failures as an error event
        log.warning("chat_stream_failed", error=str(exc))
        yield _sse("error", {"message": "The assistant failed to generate a response."})
        return

    answer = "".join(parts).strip()
    # A refused answer carries no citations even if low-relevance nodes slipped in.
    refused = not nodes or answer == REFUSAL_TEXT
    final_citations = [] if refused else [c.model_dump() for c in citations]

    yield _sse("citations", {"citations": final_citations})

    message_id = persistence.add_assistant_message(session_id, answer, final_citations)
    usage = {"context_chunks": len(nodes)}
    yield _sse("done", {"message_id": message_id, "usage": usage})


@router.post(
    "/sessions/{session_id}/messages",
    dependencies=[Depends(enforce_chat_rate_limit)],
)
async def post_message(
    session_id: str,
    body: MessageIn,
    persistence: Annotated[ChatPersistence, Depends(get_persistence)],
) -> EventSourceResponse:
    """Accept a user message and stream the grounded answer as SSE.

    Rate-limited per client via enforce_chat_rate_limit (429 when exceeded).
    """
    question = body.content.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Message content is empty.")
    if len(question) > MAX_QUESTION_CHARS:
        raise HTTPException(
            status_code=413,
            detail=f"Message exceeds the {MAX_QUESTION_CHARS}-character limit.",
        )

    try:
        persistence.add_user_message(session_id, question)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Session not found.") from exc

    return EventSourceResponse(stream_answer(session_id, question, persistence))
