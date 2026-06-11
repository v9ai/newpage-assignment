# 02 — Config & Env Handling

**Roadmap phase:** 1 · **Depends on:** 01

## Goal
All config flows through one typed settings module; the OpenAI key lives only in `.env.local`.

## Scope
- pydantic-settings module loading `.env` (defaults) then `.env.local` (overrides, wins)
- Vars: `OPENAI_API_KEY` (required), `LLM_BASE_URL`/`LLM_MODEL` (optional overrides, OpenAI-compatible), `EMBED_MODEL` (FastEmbed model id, local), DB/Qdrant URLs
- Fail fast at startup with a clear error if `OPENAI_API_KEY` is missing
- `/api/health` reports `openai: configured` (key presence only — no live API call)
- `.env.example` documenting every variable with placeholders (`OPENAI_API_KEY=sk-...`)
- Key never logged, never sent to the frontend

## Done when
- Starting the api without a key exits immediately with a readable error
- `git ls-files | grep -i env` returns only `.env.example`
- Unit test covers settings precedence (`.env.local` wins)
