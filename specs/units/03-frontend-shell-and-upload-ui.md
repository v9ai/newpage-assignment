# 03 — Frontend Shell & Upload UI

**Roadmap phases:** 1, 2 · **Integration deps:** 05 (live API for done-when) · **Teammate:** `frontend` · *(merges old units 05 + 09)*

## Owns (files)
Everything under `web/` **except** `web/src/chat/` (08), `web/Dockerfile`, and
`web/nginx.conf` (04).

## Goal
A branded React SPA with drag-and-drop upload and a live document list — proving
frontend↔backend wiring end to end.

## Consumes (contracts)
`GET /api/health`, the documents endpoints, `DocumentOut`, and the status enum from the
[shared contracts](README.md#shared-contracts).

## Scope
- Init `web/` with Vite + React + TS (strict) + Tailwind; exact-pinned versions (no `^`)
- Base design tokens (colors, type scale, spacing) — visibly not the Vite default
- Landing page: app name, tagline; fetch and display `/api/health` (green/red indicator)
- Drag-and-drop zone + file picker; client-side type/size pre-check mirroring server rules
- Document list: filename, size, status badge (full enum incl. `ingesting`/`ready`/`failed`
  with reason), delete; polls/refreshes status
- Upload progress + error toasts (unsupported type, too large, server error)

## Parallel notes
Fully parallel with the backend: develop against a mock of the HTTP contracts (MSW or a tiny
stub server replaying the documented JSON shapes, including status transitions). Swap to the
real api only for the done-when checks.

## Done when
- `npm run build` and strict `tsc` pass
- Browser shows the landing page with live health status
- Upload a PDF in the browser → appears in the list, status visibly progresses
- Rejection paths show friendly errors, not console traces
