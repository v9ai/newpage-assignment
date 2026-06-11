# 04 — Qdrant Wiring

**Roadmap phase:** 1 · **Depends on:** 01, 02

## Goal
Qdrant reachable from the api and proven by the health endpoint.

## Scope
- `qdrant-client` configured from settings
- Collection bootstrap helper (create-if-missing; name + vector size from config)
- `/api/health` performs a collections call

## Out of scope
- Writing vectors (10)

## Done when
- Health endpoint reports `qdrant: ok`; flips to error when Qdrant is down
