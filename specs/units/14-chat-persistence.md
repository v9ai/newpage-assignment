# 14 — Chat Persistence & Context Management

**Roadmap phase:** 5 · **Depends on:** 13

## Goal
Conversations survive reloads and stay within the model's context budget.

## Scope
- Postgres tables: `chat_sessions`, `chat_messages` (role, content, citations json, created_at) — Alembic migration
- Session CRUD: create, list, fetch with messages
- History condensation under a token budget (recent verbatim + older summarized/truncated — documented choice)

## Done when
- Reloading the app restores prior sessions and messages
- A long conversation stays under the budget (verified by a unit test on the condenser)
