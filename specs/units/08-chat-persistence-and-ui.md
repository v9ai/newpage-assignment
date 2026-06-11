# 08 — Chat Persistence & Chat UI

**Roadmap phases:** 5, 6 · **Integration deps:** 07 · **Teammate:** `frontend` · *(merges old units 14 + 15)*

## Owns (files)
`api/app/sessions.py`, `api/app/chat_models.py`, `api/app/condenser.py`, Alembic migration
`0002` (with `down_revision = "0001"` — fixed ids, no coordination with 02 needed),
`web/src/chat/`, and their tests. Router mount → message the lead.

## Goal
Conversations survive reloads, stay within the model's context budget, and are served through
the polished, demo-ready interface — the "well designed application" rubric item.

## Consumes / provides (contracts)
Provides the chat tables and session endpoints; consumes the SSE stream and `Citation` shape —
all from the [shared contracts](README.md#shared-contracts).

## Scope

### Persistence & context management
- Postgres tables: `chat_sessions`, `chat_messages` (role, content, citations json,
  created_at) — Alembic migration
- Session CRUD: create, list, fetch with messages
- History condensation under a token budget (recent verbatim + older summarized/truncated —
  documented choice)

### Chat UI
- Streaming tokens rendered live; message history; session switcher
- Citation chips on answers → click opens source preview (doc, page, chunk text)
- Empty/loading/error states: no documents yet, thinking, LLM unreachable/rate-limited,
  refusal styling
- Mobile-friendly layout; keyboard ergonomics (Enter to send, focus management)

## Parallel notes
The two halves are independent: persistence codes against the schema contract (no LLM
needed); the UI develops against a scripted mock SSE stream emitting the contract's events
(`token`/`citations`/`error`/`done`), including the refusal and error cases. Only the
end-to-end done-when needs 07.

## Done when
- Reloading the app restores prior sessions and messages
- A long conversation stays under the budget (verified by a unit test on the condenser)
- Upload → ask → streamed cited answer feels smooth end-to-end in the browser
- Citation chip opens the right source passage
- Error and refusal states are designed, not accidental
