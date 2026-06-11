# 11 — Ingestion Status

**Roadmap phase:** 3 · **Depends on:** 09, 10

## Goal
Users can see exactly where each document is in the pipeline.

## Scope
- Status transitions in Postgres: `uploaded → ingesting → ready | failed` (+ failure reason)
- Ingestion triggered on upload completion; runs without blocking the request (background task is fine — no queue infra)
- Document list UI polls/refreshes status; `failed` shows the reason

## Done when
- Upload → status visibly progresses to `ready` in the UI
- A corrupt file shows `failed` + reason without breaking the list
