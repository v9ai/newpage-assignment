"""Chat engine + SSE stream tests.

These stub retrieval and the LLM so they run with no Qdrant/OpenAI access — they
exercise the SSE event contract, citation mapping, and the refusal path. The live
ingest -> retrieve -> answer round-trip lives in test_retrieval.py (integration).
"""

import asyncio
import json
from collections.abc import AsyncIterator

import pytest

from app import chat
from app.chat import InMemoryPersistence, build_citations, context_chunks, stream_answer
from app.retrieval import RetrievedNode


def _node(text: str, score: float = 0.9, chunk_index: int = 0) -> RetrievedNode:
    return RetrievedNode(
        text=text,
        score=score,
        doc_id="doc-1",
        filename="handbook.md",
        page=3,
        chunk_index=chunk_index,
    )


class _FakeChunk:
    def __init__(self, delta: str) -> None:
        self.delta = delta


async def _fake_stream(deltas: list[str]) -> AsyncIterator[_FakeChunk]:
    for d in deltas:
        yield _FakeChunk(d)


class _FakeLLM:
    def __init__(self, deltas: list[str]) -> None:
        self._deltas = deltas

    async def astream_chat(self, _messages: object) -> AsyncIterator[_FakeChunk]:
        return _fake_stream(self._deltas)


def _collect(gen: AsyncIterator[dict[str, str]]) -> list[tuple[str, dict]]:
    """Drain an async SSE generator into [(event, data)] synchronously."""

    async def _drain() -> list[tuple[str, dict]]:
        events = []
        async for ev in gen:
            events.append((ev["event"], json.loads(ev["data"])))
        return events

    return asyncio.run(_drain())


def test_build_citations_maps_node_metadata() -> None:
    cites = build_citations([_node("Some retrieved passage about onboarding.")])
    assert len(cites) == 1
    c = cites[0]
    assert c.doc_id == "doc-1"
    assert c.filename == "handbook.md"
    assert c.page == 3
    assert c.chunk_index == 0
    assert "onboarding" in c.snippet


def test_context_chunks_are_one_indexed() -> None:
    chunks = context_chunks([_node("a"), _node("b", chunk_index=1)])
    assert [c.number for c in chunks] == [1, 2]


def test_stream_answer_emits_token_citations_done(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(chat, "search", lambda *a, **k: [_node("Vacation accrues monthly.")])
    deltas = ["Vacation ", "accrues ", "monthly [1]."]
    monkeypatch.setattr(chat, "get_llm", lambda _s: _FakeLLM(deltas))

    persistence = InMemoryPersistence()
    events = _collect(stream_answer("sess-1", "How does vacation accrue?", persistence))

    kinds = [e for e, _ in events]
    assert kinds[0] == "token"
    assert "citations" in kinds
    assert kinds[-1] == "done"

    answer = "".join(d["delta"] for e, d in events if e == "token")
    assert answer == "Vacation accrues monthly [1]."

    cite_event = next(d for e, d in events if e == "citations")
    assert len(cite_event["citations"]) == 1
    assert cite_event["citations"][0]["filename"] == "handbook.md"

    done = next(d for e, d in events if e == "done")
    assert done["message_id"]
    assert done["usage"]["context_chunks"] == 1


def test_refusal_when_no_context(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(chat, "search", lambda *a, **k: [])

    def _no_llm(_s: object) -> object:
        raise AssertionError("LLM must not be called on the refusal path")

    monkeypatch.setattr(chat, "get_llm", _no_llm)

    persistence = InMemoryPersistence()
    events = _collect(stream_answer("sess-1", "What is the capital of Mars?", persistence))

    answer = "".join(d["delta"] for e, d in events if e == "token")
    assert "couldn't find" in answer.lower()

    cite_event = next(d for e, d in events if e == "citations")
    assert cite_event["citations"] == []
    done = next(d for e, d in events if e == "done")
    assert done["usage"]["context_chunks"] == 0


def test_generation_error_emits_error_event(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(chat, "search", lambda *a, **k: [_node("context")])

    class _BoomLLM:
        async def astream_chat(self, _m: object) -> object:
            raise RuntimeError("upstream 500")

    monkeypatch.setattr(chat, "get_llm", lambda _s: _BoomLLM())

    events = _collect(stream_answer("s", "q", InMemoryPersistence()))
    assert events[-1][0] == "error"
    assert "failed" in events[-1][1]["message"].lower()


def test_in_memory_persistence_roundtrip() -> None:
    p = InMemoryPersistence()
    uid = p.add_user_message("s", "hello")
    aid = p.add_assistant_message("s", "hi there", [])
    assert uid != aid
    assert p.session_history("s") == [("user", "hello"), ("assistant", "hi there")]


# --- input limits (guardrails) -------------------------------------------------


def test_message_endpoint_rejects_empty_content() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    # Pydantic min_length=1 catches this at validation: 422.
    resp = client.post("/api/sessions/s1/messages", json={"content": ""})
    assert resp.status_code == 422


def test_message_endpoint_rejects_oversized_content() -> None:
    from fastapi.testclient import TestClient

    from app.chat import MAX_QUESTION_CHARS
    from app.main import app

    client = TestClient(app)
    resp = client.post(
        "/api/sessions/s1/messages",
        json={"content": "x" * (MAX_QUESTION_CHARS + 1)},
    )
    assert resp.status_code == 413
    assert "limit" in resp.json()["detail"].lower()
